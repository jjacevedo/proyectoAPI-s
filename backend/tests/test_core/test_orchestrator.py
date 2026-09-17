from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.core.critic import CrossCritic
from app.core.disagreement import DisagreementLevel
from app.core.fact_search import FactCheckResult
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.core.reevaluator import Reevaluator
from app.core.router import TaskRouter, TaskType
from app.providers.base import LLMProvider, LLMResponse


class FakeWikipediaClient:
    def __init__(self, results_by_query: dict[str, FactCheckResult]) -> None:
        self.results_by_query = results_by_query
        self.calls: list[str] = []

    async def search_and_summarize(self, query: str) -> FactCheckResult:
        self.calls.append(query)
        return self.results_by_query.get(query, FactCheckResult(query=query, error="no configurado en el fake"))


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


@pytest.fixture
def settings():
    """Cross-critique is disabled here: these tests exercise orchestration
    mechanics (parallelism, degradation, synthesis fallback, routing) which
    predate the critique round and are tested in isolation from it. See
    `settings_with_critique` for the critique-specific tests below.

    `provider_priority` is pinned explicitly (rather than relying on the
    app-wide default) so these mechanics tests stay deterministic regardless
    of which providers `config.py` prioritizes by default."""
    return Settings(
        synthesizer_provider="openai",
        provider_priority="openai,gemini,anthropic",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=False,
    )


@pytest.fixture
def settings_with_critique():
    """Reevaluation is disabled here: these tests exercise the critique round
    in isolation from the reevaluation round added afterwards. See
    `settings_with_reevaluation` for the reevaluation-specific tests."""
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=True,
        enable_reevaluation_round=False,
    )


@pytest.fixture
def settings_with_reevaluation():
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=True,
        enable_reevaluation_round=True,
    )


@pytest.fixture
def settings_with_code_verification():
    """Critique and reevaluation are disabled here so the synthesizer
    provider's call count is predictable (round-1 generation, test-suite
    generation, synthesis — exactly 3 calls) and isolated from those
    other pipeline stages, which have their own fixtures above."""
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=False,
        enable_reevaluation_round=False,
        enable_code_verification=True,
        code_execution_timeout_seconds=2,
    )


@pytest.fixture
def settings_with_calculation_verification():
    """Critique and reevaluation are disabled here so the synthesizer
    provider's call count is predictable (round-1 generation, solver-script
    generation, synthesis — exactly 3 calls), same isolation pattern as
    `settings_with_code_verification`."""
    return Settings(
        synthesizer_provider="openai",
        provider_priority="openai,gemini,anthropic",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=False,
        enable_reevaluation_round=False,
        enable_calculation_verification=True,
        code_execution_timeout_seconds=2,
    )


@pytest.fixture
def settings_with_fact_search():
    """Critique and reevaluation are disabled here so the synthesizer
    provider's call count is predictable (round-1 generation, query
    generation, synthesis — exactly 3 calls), same isolation pattern as
    `settings_with_code_verification`/`settings_with_calculation_verification`."""
    return Settings(
        synthesizer_provider="openai",
        provider_priority="openai,gemini,anthropic",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=False,
        enable_reevaluation_round=False,
        enable_fact_search=True,
        fact_search_max_queries=3,
    )


def _always_high_router() -> TaskRouter:
    """These tests exercise orchestration mechanics (parallelism, degradation,
    synthesis fallback), not routing. Force HIGH complexity so all configured
    providers are used, independent of the router's own tests."""
    return TaskRouter(low_threshold_chars=0, high_threshold_chars=0)


@pytest.mark.asyncio
async def test_orchestrator_three_of_three(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    synth = FakeProvider("openai", LLMResponse(provider="openai", model="openai-model", content="final"))
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="a"),
        LLMResponse(provider="openai", model="openai-model", content="final"),
    ])
    orchestrator = DeliberationOrchestrator(providers, settings, router=_always_high_router())
    result = await orchestrator.run("question")
    assert result.final_answer == "final"
    assert len(result.responses) == 4


@pytest.mark.asyncio
async def test_orchestrator_two_of_three(settings):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", error="down")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="a"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])
    orchestrator = DeliberationOrchestrator(providers, settings, router=_always_high_router())
    result = await orchestrator.run("question")
    assert result.final_answer == "final"
    assert any(item.error == "down" for item in result.responses)


@pytest.mark.asyncio
async def test_orchestrator_zero_of_three(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model="m", error="down"))
        for name in ["openai", "anthropic", "gemini"]
    }
    orchestrator = DeliberationOrchestrator(providers, settings, router=_always_high_router())
    with pytest.raises(AllProvidersFailedError):
        await orchestrator.run("question")


@pytest.mark.asyncio
async def test_orchestrator_falls_back_when_synthesizer_fails_after_succeeding(settings):
    """The synthesizer provider (openai) answers the independent round fine,
    but its second call (the actual synthesis) fails. The orchestrator must
    fall back to the first successful candidate instead of raising or
    returning an empty answer.
    """
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="a"),
        LLMResponse(provider="openai", model="a", error="synthesis boom"),
    ])
    orchestrator = DeliberationOrchestrator(providers, settings, router=_always_high_router())
    result = await orchestrator.run("question")
    assert result.final_answer == "a"
    assert any(item.error == "synthesis boom" for item in result.responses)


@pytest.mark.asyncio
async def test_orchestrator_uses_default_router_to_limit_calls_for_simple_prompts(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    for provider in providers.values():
        provider.generate = AsyncMock(wraps=provider.generate)

    orchestrator = DeliberationOrchestrator(providers, settings)
    result = await orchestrator.run("¿Qué es una API?")

    assert result.routing.provider_count == 1
    assert providers["openai"].generate.await_count == 2  # generation + synthesis
    assert providers["anthropic"].generate.await_count == 0
    assert providers["gemini"].generate.await_count == 0


@pytest.mark.asyncio
async def test_orchestrator_uses_default_router_to_call_all_for_complex_prompts(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    for provider in providers.values():
        provider.generate = AsyncMock(wraps=provider.generate)

    orchestrator = DeliberationOrchestrator(providers, settings)
    prompt = (
        "Analiza esta arquitectura de software, encuentra problemas de "
        "escalabilidad, seguridad y concurrencia y propón una arquitectura "
        "alternativa."
    )
    result = await orchestrator.run(prompt)

    assert result.routing.provider_count == 3
    assert providers["anthropic"].generate.await_count == 1
    assert providers["gemini"].generate.await_count == 1


@pytest.mark.asyncio
async def test_orchestrator_skips_critique_with_single_success(settings_with_critique):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", error="down")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", error="down")),
    }
    critic = CrossCritic(max_tokens=100)
    critic.run = AsyncMock(wraps=critic.run)
    orchestrator = DeliberationOrchestrator(
        providers, settings_with_critique, router=_always_high_router(), critic=critic
    )
    result = await orchestrator.run("question")

    assert result.critiques == []
    assert critic.run.await_count == 0
    assert result.disagreement.level == DisagreementLevel.NOT_APPLICABLE
    assert result.revisions == []


@pytest.mark.asyncio
async def test_orchestrator_runs_one_critique_per_successful_provider(settings_with_critique):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    critic = CrossCritic(max_tokens=100)
    critic.run = AsyncMock(wraps=critic.run)
    orchestrator = DeliberationOrchestrator(
        providers, settings_with_critique, router=_always_high_router(), critic=critic
    )
    result = await orchestrator.run("question")

    assert len(result.critiques) == 3
    assert critic.run.await_count == 3
    for critique in result.critiques:
        reviewed = set(critique.reviewed_providers)
        assert len(reviewed) == 2
        assert f"{critique.response.provider}/{critique.response.model}" not in reviewed
    # The FakeProvider critiques here just echo fixed content with no
    # disagreement keywords, so the detector should report consensus.
    assert result.disagreement.level == DisagreementLevel.CONSENSUS
    # Reevaluation is disabled in this fixture (see settings_with_critique).
    assert result.revisions == []


@pytest.mark.asyncio
async def test_orchestrator_detects_disagreement_from_critique_content(settings_with_critique):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider(
            "anthropic",
            LLMResponse(
                provider="anthropic",
                model="b",
                content="La respuesta de openai contradice la evidencia presentada.",
            ),
        ),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    orchestrator = DeliberationOrchestrator(providers, settings_with_critique, router=_always_high_router())
    result = await orchestrator.run("question")

    assert result.disagreement.level == DisagreementLevel.DISAGREEMENT
    assert any("contradice" in item for item in result.disagreement.evidence)


@pytest.mark.asyncio
async def test_orchestrator_critique_failure_does_not_block_synthesis(settings_with_critique):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="a"),  # initial generation round
        LLMResponse(provider="openai", model="a", content="a"),  # openai's own critique of others
        LLMResponse(provider="openai", model="a", content="final"),  # synthesis
    ])

    real_critic = CrossCritic(max_tokens=100)

    async def flaky_run(provider, original_prompt, own_response, other_responses):
        if own_response.provider == "gemini":
            raise RuntimeError("critique boom")
        return await real_critic.run(provider, original_prompt, own_response, other_responses)

    critic = CrossCritic(max_tokens=100)
    critic.run = AsyncMock(side_effect=flaky_run)

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_critique, router=_always_high_router(), critic=critic
    )
    result = await orchestrator.run("question")

    assert result.final_answer == "final"
    assert len(result.critiques) == 3
    failed = [c for c in result.critiques if not c.succeeded]
    assert len(failed) == 1
    assert "critique boom" in failed[0].response.error


@pytest.mark.asyncio
async def test_orchestrator_enable_cross_critique_false_skips_critique_round(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    critic = CrossCritic(max_tokens=100)
    critic.run = AsyncMock(wraps=critic.run)
    orchestrator = DeliberationOrchestrator(providers, settings, router=_always_high_router(), critic=critic)
    result = await orchestrator.run("question")

    assert result.critiques == []
    assert critic.run.await_count == 0
    assert result.disagreement.level == DisagreementLevel.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_orchestrator_runs_reevaluation_after_successful_critique(settings_with_reevaluation):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    reevaluator = Reevaluator(max_tokens=100)
    reevaluator.run = AsyncMock(wraps=reevaluator.run)
    orchestrator = DeliberationOrchestrator(
        providers, settings_with_reevaluation, router=_always_high_router(), reevaluator=reevaluator
    )
    result = await orchestrator.run("question")

    assert len(result.revisions) == 3
    assert reevaluator.run.await_count == 3
    assert all(revision.succeeded for revision in result.revisions)


@pytest.mark.asyncio
async def test_orchestrator_skips_reevaluation_when_disabled(settings_with_critique):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    reevaluator = Reevaluator(max_tokens=100)
    reevaluator.run = AsyncMock(wraps=reevaluator.run)
    orchestrator = DeliberationOrchestrator(
        providers, settings_with_critique, router=_always_high_router(), reevaluator=reevaluator
    )
    result = await orchestrator.run("question")

    assert result.revisions == []
    assert reevaluator.run.await_count == 0


@pytest.mark.asyncio
async def test_orchestrator_reevaluation_failure_falls_back_to_original_response(settings_with_reevaluation):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="original-a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="original-b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="original-c")),
    }

    real_reevaluator = Reevaluator(max_tokens=100)

    async def flaky_run(provider, original_prompt, own_response, critiques):
        if own_response.provider == "gemini":
            raise RuntimeError("reevaluation boom")
        return await real_reevaluator.run(provider, original_prompt, own_response, critiques)

    reevaluator = Reevaluator(max_tokens=100)
    reevaluator.run = AsyncMock(side_effect=flaky_run)

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_reevaluation, router=_always_high_router(), reevaluator=reevaluator
    )
    result = await orchestrator.run("question")

    assert len(result.revisions) == 3
    failed = [r for r in result.revisions if not r.succeeded]
    assert len(failed) == 1
    assert failed[0].provider == "gemini"
    assert "reevaluation boom" in failed[0].error
    # The final answer must still be produced: gemini's ORIGINAL response
    # (not a revision) should have been used as a synthesis candidate.
    assert result.final_answer


@pytest.mark.asyncio
async def test_orchestrator_runs_code_verification_for_code_task(settings_with_code_verification):
    correct_code = "```python\ndef add(a, b):\n    return a + b\n```"
    wrong_code = "```python\ndef add(a, b):\n    return a - b\n```"
    no_code = "Aquí tienes una explicación sin ningún bloque de código."
    generated_tests = (
        "```python\n"
        "import unittest\n\n"
        "class TestAdd(unittest.TestCase):\n"
        "    def test_basic(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
        "```"
    )

    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="openai-model", content=correct_code)),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="anthropic-model", content=wrong_code)),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="gemini-model", content=no_code)),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content=correct_code),  # round-1 generation
        LLMResponse(provider="openai", model="openai-model", content=generated_tests),  # test-suite generation
        LLMResponse(provider="openai", model="openai-model", content="final synthesis"),  # synthesis
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_code_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Escribe una función en Python que sume dos números.")

    assert result.routing.task_type == TaskType.CODE
    assert providers["openai"].generate.await_count == 3
    assert result.generated_tests is not None
    assert "TestAdd" in result.generated_tests

    verifications_by_provider = {v.provider: v for v in result.code_verifications}
    assert len(verifications_by_provider) == 3
    assert verifications_by_provider["openai"].passed is True
    assert verifications_by_provider["anthropic"].passed is False
    assert verifications_by_provider["anthropic"].tests_failed > 0
    assert verifications_by_provider["gemini"].error is not None
    assert result.final_answer == "final synthesis"


@pytest.mark.asyncio
async def test_orchestrator_skips_code_verification_for_general_task(settings_with_code_verification):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="openai"),
        LLMResponse(provider="openai", model="openai-model", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_code_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Cuéntame sobre el clima de hoy.")

    assert result.routing.task_type == TaskType.GENERAL
    assert result.code_verifications == []
    assert result.generated_tests is None
    # Only round-1 generation + synthesis: no test-suite generation call.
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_enable_code_verification_false_skips_it_even_for_code_task(settings):
    """`settings` has enable_code_verification at its default (True) turned
    off explicitly here to isolate the flag itself from task-type routing,
    which is covered by the test above."""
    disabled_settings = settings.model_copy(update={"enable_code_verification": False})
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="```python\ndef add(a, b):\n    return a + b\n```")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="```python\ndef add(a, b):\n    return a + b\n```"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(providers, disabled_settings, router=_always_high_router())
    result = await orchestrator.run("Escribe una función en Python que sume dos números.")

    assert result.routing.task_type == TaskType.CODE
    assert result.code_verifications == []
    assert result.generated_tests is None
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_test_generation_failure_does_not_block_synthesis(settings_with_code_verification):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="```python\ndef add(a, b):\n    return a + b\n```")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="```python\ndef add(a, b):\n    return a + b\n```"),
        LLMResponse(provider="openai", model="a", error="test generation boom"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_code_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Escribe una función en Python que sume dos números.")

    assert result.generated_tests is None
    assert len(result.code_verifications) == 1
    assert "no se pudo generar el suite de tests" in result.code_verifications[0].error
    assert result.final_answer == "final"


@pytest.mark.asyncio
async def test_orchestrator_runs_calculation_verification_for_math_task(settings_with_calculation_verification):
    solver_script = "```python\nprint('__CALC_RESULT__ 240')\n```"

    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="openai-model", content="El resultado es 240 km.")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="anthropic-model", content="El resultado es 180 km.")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="gemini-model", content="No puedo calcular esto.")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="El resultado es 240 km."),  # round-1
        LLMResponse(provider="openai", model="openai-model", content=solver_script),  # solver script
        LLMResponse(provider="openai", model="openai-model", content="final synthesis"),  # synthesis
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_calculation_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Un tren viaja a 80 km/h durante 3 horas. ¿Cuántos km recorre?")

    assert result.routing.task_type == TaskType.MATH
    assert providers["openai"].generate.await_count == 3
    assert result.reference_calculation is not None

    verifications_by_provider = {v.provider: v for v in result.calculation_verifications}
    assert len(verifications_by_provider) == 3
    assert verifications_by_provider["openai"].passed is True
    assert verifications_by_provider["anthropic"].passed is False
    assert verifications_by_provider["anthropic"].difference == 60.0
    assert verifications_by_provider["gemini"].error is not None
    assert result.final_answer == "final synthesis"


@pytest.mark.asyncio
async def test_orchestrator_skips_calculation_verification_for_general_task(settings_with_calculation_verification):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="openai"),
        LLMResponse(provider="openai", model="openai-model", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_calculation_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Cuéntame sobre el clima de hoy.")

    assert result.routing.task_type == TaskType.GENERAL
    assert result.calculation_verifications == []
    assert result.reference_calculation is None
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_enable_calculation_verification_false_skips_it_even_for_math_task(settings):
    disabled_settings = settings.model_copy(update={"enable_calculation_verification": False})
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="240")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="240"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(providers, disabled_settings, router=_always_high_router())
    result = await orchestrator.run("¿Cuánto es el 15% de 240?")

    assert result.routing.task_type == TaskType.MATH
    assert result.calculation_verifications == []
    assert result.reference_calculation is None
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_solver_generation_failure_does_not_block_synthesis(settings_with_calculation_verification):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="240")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="240"),
        LLMResponse(provider="openai", model="a", error="solver generation boom"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_calculation_verification, router=_always_high_router()
    )
    result = await orchestrator.run("Un tren viaja a 80 km/h durante 3 horas. ¿Cuántos km recorre?")

    assert result.reference_calculation is None
    assert len(result.calculation_verifications) == 1
    assert "no se pudo generar el script de cálculo" in result.calculation_verifications[0].error
    assert result.final_answer == "final"


@pytest.mark.asyncio
async def test_orchestrator_runs_fact_search_for_factual_task(settings_with_fact_search):
    queries_response = "Alan Turing nacimiento\nAlan Turing Enigma"
    fake_wikipedia = FakeWikipediaClient({
        "Alan Turing nacimiento": FactCheckResult(
            query="Alan Turing nacimiento",
            title="Alan Turing",
            extract="Alan Turing nació el 23 de junio de 1912.",
            url="https://es.wikipedia.org/wiki/Alan_Turing",
        ),
        "Alan Turing Enigma": FactCheckResult(
            query="Alan Turing Enigma",
            error="no se encontraron resultados en Wikipedia",
        ),
    })

    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="openai-model", content="Turing nació en 1912.")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="anthropic-model", content="Turing nació en 1905.")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="gemini-model", content="No tengo información.")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="Turing nació en 1912."),  # round-1
        LLMResponse(provider="openai", model="openai-model", content=queries_response),  # query generation
        LLMResponse(provider="openai", model="openai-model", content="final synthesis"),  # synthesis
    ])

    orchestrator = DeliberationOrchestrator(
        providers,
        settings_with_fact_search,
        router=_always_high_router(),
        wikipedia_client=fake_wikipedia,
    )
    result = await orchestrator.run("¿Quién fue Alan Turing?")

    assert result.routing.task_type == TaskType.FACTUAL
    assert providers["openai"].generate.await_count == 3
    assert fake_wikipedia.calls == ["Alan Turing nacimiento", "Alan Turing Enigma"]
    assert len(result.fact_search_results) == 2
    succeeded = {r.query: r for r in result.fact_search_results}
    assert succeeded["Alan Turing nacimiento"].succeeded
    assert succeeded["Alan Turing nacimiento"].extract == "Alan Turing nació el 23 de junio de 1912."
    assert not succeeded["Alan Turing Enigma"].succeeded
    assert result.final_answer == "final synthesis"


@pytest.mark.asyncio
async def test_orchestrator_skips_fact_search_for_general_task(settings_with_fact_search):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model=f"{name}-model", content=name))
        for name in ["openai", "anthropic", "gemini"]
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="openai-model", content="openai"),
        LLMResponse(provider="openai", model="openai-model", content="final"),
    ])
    fake_wikipedia = FakeWikipediaClient({})

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_fact_search, router=_always_high_router(), wikipedia_client=fake_wikipedia
    )
    result = await orchestrator.run("Cuéntame sobre el clima de hoy.")

    assert result.routing.task_type == TaskType.GENERAL
    assert result.fact_search_results == []
    assert fake_wikipedia.calls == []
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_enable_fact_search_false_skips_it_even_for_factual_task(settings):
    disabled_settings = settings.model_copy(update={"enable_fact_search": False})
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="a"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])
    fake_wikipedia = FakeWikipediaClient({})

    orchestrator = DeliberationOrchestrator(
        providers, disabled_settings, router=_always_high_router(), wikipedia_client=fake_wikipedia
    )
    result = await orchestrator.run("¿Quién fue Alan Turing?")

    assert result.routing.task_type == TaskType.FACTUAL
    assert result.fact_search_results == []
    assert fake_wikipedia.calls == []
    assert providers["openai"].generate.await_count == 2


@pytest.mark.asyncio
async def test_orchestrator_query_generation_failure_does_not_block_synthesis(settings_with_fact_search):
    providers = {
        "openai": FakeProvider("openai", LLMResponse(provider="openai", model="a", content="a")),
        "anthropic": FakeProvider("anthropic", LLMResponse(provider="anthropic", model="b", content="b")),
        "gemini": FakeProvider("gemini", LLMResponse(provider="gemini", model="c", content="c")),
    }
    providers["openai"].generate = AsyncMock(side_effect=[
        LLMResponse(provider="openai", model="a", content="a"),
        LLMResponse(provider="openai", model="a", error="query generation boom"),
        LLMResponse(provider="openai", model="a", content="final"),
    ])
    fake_wikipedia = FakeWikipediaClient({})

    orchestrator = DeliberationOrchestrator(
        providers, settings_with_fact_search, router=_always_high_router(), wikipedia_client=fake_wikipedia
    )
    result = await orchestrator.run("¿Quién fue Alan Turing?")

    assert len(result.fact_search_results) == 1
    assert "no se pudieron generar consultas de búsqueda" in result.fact_search_results[0].error
    assert fake_wikipedia.calls == []
    assert result.final_answer == "final"

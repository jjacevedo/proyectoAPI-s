from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.core.critic import CrossCritic
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
from app.core.router import TaskRouter
from app.providers.base import LLMProvider, LLMResponse


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
    `settings_with_critique` for the critique-specific tests below."""
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=False,
    )


@pytest.fixture
def settings_with_critique():
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
        enable_cross_critique=True,
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

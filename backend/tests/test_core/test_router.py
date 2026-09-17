import pytest

from app.core.router import TaskComplexity, TaskRouter


@pytest.fixture
def router() -> TaskRouter:
    return TaskRouter()


def test_classifies_short_simple_question_as_low(router):
    decision = router.classify("¿Qué es una API?")
    assert decision.complexity == TaskComplexity.LOW
    assert decision.provider_count == 1


def test_classifies_complex_architecture_prompt_as_high(router):
    prompt = (
        "Analiza esta arquitectura de software, encuentra problemas de "
        "escalabilidad, seguridad y concurrencia y propón una arquitectura "
        "alternativa."
    )
    decision = router.classify(prompt)
    assert decision.complexity == TaskComplexity.HIGH
    assert decision.provider_count == 3


def test_classifies_moderate_request_as_medium(router):
    decision = router.classify("Escribe una función que valide un email.")
    assert decision.complexity == TaskComplexity.MEDIUM
    assert decision.provider_count == 2


def test_long_prompt_without_keywords_escalates_to_high(router):
    decision = router.classify("hola " * 60)
    assert decision.complexity == TaskComplexity.HIGH


def test_select_providers_respects_priority_order():
    router = TaskRouter()
    providers = {"anthropic": object(), "gemini": object(), "openai": object()}
    decision = router.classify("Escribe una función que valide un email.")  # MEDIUM -> 2
    selected = router.select_providers(providers, decision, priority=["openai", "gemini", "anthropic"])
    assert list(selected.keys()) == ["openai", "gemini"]


def test_select_providers_falls_back_to_available_when_priority_missing():
    router = TaskRouter()
    providers = {"anthropic": object()}
    decision = router.classify("¿Qué es una API?")  # LOW -> 1
    selected = router.select_providers(providers, decision, priority=["openai", "gemini", "anthropic"])
    assert list(selected.keys()) == ["anthropic"]

import pytest

from app.core.router import TaskComplexity, TaskRouter, TaskType


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


def test_classifies_coding_request_as_code_type(router):
    decision = router.classify("Implementa una función en Python que calcule el máximo común divisor.")
    assert decision.task_type == TaskType.CODE


def test_classifies_general_question_as_general_type(router):
    decision = router.classify("¿Qué es una API?")
    assert decision.task_type == TaskType.GENERAL


def test_classifies_arithmetic_request_as_math_type(router):
    decision = router.classify("¿Cuánto es el 15% de 240?")
    assert decision.task_type == TaskType.MATH


def test_classifies_word_problem_as_math_type(router):
    decision = router.classify("Un tren viaja a 80 km/h durante 3 horas. ¿Cuántos km recorre?")
    assert decision.task_type == TaskType.MATH


def test_code_keywords_take_precedence_over_math_keywords(router):
    decision = router.classify("Escribe una función en Python que calcule el promedio de una lista.")
    assert decision.task_type == TaskType.CODE


def test_classifies_named_entity_question_as_factual_type(router):
    decision = router.classify("¿Quién fue Alan Turing?")
    assert decision.task_type == TaskType.FACTUAL


def test_classifies_capital_question_as_factual_type(router):
    decision = router.classify("¿Cuál es la capital de Australia?")
    assert decision.task_type == TaskType.FACTUAL


def test_conceptual_explanation_is_not_classified_as_factual(router):
    decision = router.classify("¿Qué es una API?")
    assert decision.task_type == TaskType.GENERAL

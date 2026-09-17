import pytest

from app.core.evaluator import EvaluationJudge, SingleLLMBaseline, extract_verdict
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


class RaisingProvider(LLMProvider):
    def __init__(self, name: str, exc: Exception):
        self.provider_name = name
        self.model = f"{name}-model"
        self.exc = exc

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        raise self.exc


@pytest.mark.asyncio
async def test_single_llm_baseline_returns_providers_response():
    provider = FakeProvider("openai", LLMResponse(provider="openai", model="gpt", content="baseline answer"))
    baseline = SingleLLMBaseline()
    result = await baseline.run(provider, "original request", max_tokens=100)
    assert result.content == "baseline answer"
    assert result.succeeded


@pytest.mark.asyncio
async def test_single_llm_baseline_degrades_on_exception():
    provider = RaisingProvider("openai", RuntimeError("boom"))
    baseline = SingleLLMBaseline()
    result = await baseline.run(provider, "original request", max_tokens=100)
    assert not result.succeeded
    assert "boom" in result.error


def test_build_prompt_includes_both_answers_and_verdict_instructions():
    judge = EvaluationJudge(max_tokens=200)
    prompt = judge.build_prompt("original request", "answer from single LLM", "answer from deliberation")
    assert "original request" in prompt
    assert "answer from single LLM" in prompt
    assert "answer from deliberation" in prompt
    assert "__VERDICT__ single|multi|tie" in prompt


@pytest.mark.asyncio
async def test_judge_run_returns_providers_generated_content():
    provider = FakeProvider(
        "openai", LLMResponse(provider="openai", model="gpt", content="Reasoning...\n__VERDICT__ multi")
    )
    judge = EvaluationJudge(max_tokens=200)
    response = await judge.run(provider, "request", "single answer", "multi answer")
    assert response.content == "Reasoning...\n__VERDICT__ multi"


def test_extract_verdict_parses_marker_case_insensitively():
    verdict, reasoning = extract_verdict("The multi-LLM answer is more complete.\n__VERDICT__ Multi")
    assert verdict == "multi"
    assert "more complete" in reasoning
    assert "__VERDICT__" not in reasoning


def test_extract_verdict_returns_none_without_marker():
    verdict, reasoning = extract_verdict("no marker here")
    assert verdict is None
    assert reasoning == "no marker here"


def test_extract_verdict_returns_none_for_empty_content():
    verdict, reasoning = extract_verdict(None)
    assert verdict is None
    assert reasoning == ""

import pytest

from app.core.critic import Critique
from app.core.reevaluator import Reevaluator
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


def test_build_prompt_includes_own_previous_answer_and_succeeded_critiques():
    reevaluator = Reevaluator(max_tokens=100)
    own = LLMResponse(provider="openai", model="gpt", content="MY PREVIOUS ANSWER TEXT")
    critiques = [
        Critique(
            response=LLMResponse(provider="anthropic", model="claude", content="GOOD CRITIQUE TEXT"),
            reviewed_providers=["openai/gpt"],
        ),
        Critique(
            response=LLMResponse(provider="gemini", model="flash", error="timeout"),
            reviewed_providers=["openai/gpt"],
        ),
    ]

    prompt = reevaluator.build_prompt("original question", own, critiques)

    assert "MY PREVIOUS ANSWER TEXT" in prompt
    assert "GOOD CRITIQUE TEXT" in prompt
    # The failed critique has no content to leak into the prompt.
    assert "timeout" not in prompt


@pytest.mark.asyncio
async def test_run_returns_providers_generated_revision():
    provider = FakeProvider("openai", LLMResponse(provider="openai", model="gpt", content="revised answer"))
    reevaluator = Reevaluator(max_tokens=100)
    own = LLMResponse(provider="openai", model="gpt", content="previous answer")
    critiques = [
        Critique(
            response=LLMResponse(provider="anthropic", model="claude", content="a critique"),
            reviewed_providers=["openai/gpt"],
        )
    ]

    revision = await reevaluator.run(provider, "question", own, critiques)

    assert revision.content == "revised answer"
    assert revision.succeeded

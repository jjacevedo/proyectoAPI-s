import pytest

from app.core.critic import CrossCritic
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


def test_build_prompt_excludes_own_response_lists_others():
    critic = CrossCritic(max_tokens=100)
    own = LLMResponse(provider="openai", model="gpt", content="MY OWN UNIQUE ANSWER TEXT")
    others = [
        LLMResponse(provider="anthropic", model="claude", content="ANTHROPIC ANSWER TEXT"),
        LLMResponse(provider="gemini", model="flash", content="GEMINI ANSWER TEXT"),
    ]
    prompt = critic.build_prompt("original question", own, others)

    assert "ANTHROPIC ANSWER TEXT" in prompt
    assert "GEMINI ANSWER TEXT" in prompt
    # The own answer appears only under "YOUR OWN ANSWER", never under a "CANDIDATE" label.
    assert "MY OWN UNIQUE ANSWER TEXT" in prompt
    assert "CANDIDATE 1 (anthropic/claude)" in prompt
    assert "CANDIDATE 2 (gemini/flash)" in prompt
    for keyword in ["Errores", "Contradicciones", "supuestos", "Omisiones", "Ventajas", "Limitaciones", "Mejoras"]:
        assert keyword.lower() in prompt.lower()


@pytest.mark.asyncio
async def test_run_returns_critique_with_reviewed_providers():
    provider = FakeProvider("anthropic", LLMResponse(provider="anthropic", model="claude", content="my critique"))
    critic = CrossCritic(max_tokens=100)
    own = LLMResponse(provider="anthropic", model="claude", content="own answer")
    others = [
        LLMResponse(provider="openai", model="gpt", content="a"),
        LLMResponse(provider="gemini", model="flash", content="c"),
    ]

    critique = await critic.run(provider, "question", own, others)

    assert critique.succeeded
    assert critique.response.content == "my critique"
    assert critique.reviewed_providers == ["openai/gpt", "gemini/flash"]


@pytest.mark.asyncio
async def test_run_propagates_provider_error():
    provider = FakeProvider("gemini", LLMResponse(provider="gemini", model="flash", error="boom"))
    critic = CrossCritic(max_tokens=100)
    own = LLMResponse(provider="gemini", model="flash", content="own answer")
    others = [LLMResponse(provider="openai", model="gpt", content="a")]

    critique = await critic.run(provider, "question", own, others)

    assert not critique.succeeded
    assert critique.response.error == "boom"
    assert critique.reviewed_providers == ["openai/gpt"]

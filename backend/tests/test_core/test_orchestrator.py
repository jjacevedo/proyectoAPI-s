from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.core.orchestrator import AllProvidersFailedError, DeliberationOrchestrator
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
    return Settings(
        synthesizer_provider="openai",
        max_tokens_per_request=100,
        provider_timeout_seconds=1,
    )


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
    orchestrator = DeliberationOrchestrator(providers, settings)
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
    orchestrator = DeliberationOrchestrator(providers, settings)
    result = await orchestrator.run("question")
    assert result.final_answer == "final"
    assert any(item.error == "down" for item in result.responses)


@pytest.mark.asyncio
async def test_orchestrator_zero_of_three(settings):
    providers = {
        name: FakeProvider(name, LLMResponse(provider=name, model="m", error="down"))
        for name in ["openai", "anthropic", "gemini"]
    }
    orchestrator = DeliberationOrchestrator(providers, settings)
    with pytest.raises(AllProvidersFailedError):
        await orchestrator.run("question")

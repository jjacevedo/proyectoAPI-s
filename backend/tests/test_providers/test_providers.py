from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_provider_parses_response(monkeypatch):
    provider = OpenAIProvider("key", "gpt-test")
    usage = MagicMock(input_tokens=3, output_tokens=5)
    response = MagicMock(output_text="hello", usage=usage)
    provider.client.responses.create = AsyncMock(return_value=response)
    result = await provider.generate("hi", max_tokens=20)
    assert result.content == "hello"
    assert result.tokens == 8


@pytest.mark.asyncio
async def test_openai_provider_degrades_on_exception():
    provider = OpenAIProvider("key", "gpt-test")
    provider.client.responses.create = AsyncMock(side_effect=RuntimeError("boom"))
    result = await provider.generate("hi", max_tokens=20)
    assert result.content is None
    assert "boom" in (result.error or "")


@pytest.mark.asyncio
async def test_anthropic_provider_parses_response():
    provider = AnthropicProvider("key", "claude-test")
    block = MagicMock(text="hello")
    response = MagicMock(content=[block], usage=MagicMock(input_tokens=2, output_tokens=4))
    provider.client.messages.create = AsyncMock(return_value=response)
    result = await provider.generate("hi", max_tokens=20)
    assert result.content == "hello"
    assert result.tokens == 6


@pytest.mark.asyncio
async def test_gemini_provider_parses_response():
    provider = GeminiProvider("key", "gemini-test")
    response = MagicMock(
        text="hello",
        usage_metadata=MagicMock(prompt_token_count=2, candidates_token_count=4),
    )
    provider.client.aio.models.generate_content = AsyncMock(return_value=response)
    result = await provider.generate("hi", max_tokens=20)
    assert result.content == "hello"
    assert result.tokens == 6

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.cerebras_provider import CerebrasProvider
from app.providers.groq_provider import GroqProvider
from app.providers.nvidia_provider import NvidiaProvider
from app.providers.opencode_provider import OpenCodeProvider
from app.providers.openai_compatible_provider import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_groq_provider_parses_response():
    provider = GroqProvider("key", "llama-test")
    message = MagicMock(content="hello")
    choice = MagicMock(message=message)
    usage = MagicMock(prompt_tokens=3, completion_tokens=5)
    response = MagicMock(choices=[choice], usage=usage)
    provider.client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.generate("hi", max_tokens=20)

    assert result.provider == "groq"
    assert result.content == "hello"
    assert result.tokens == 8
    assert result.error is None


@pytest.mark.asyncio
async def test_groq_provider_degrades_on_exception():
    provider = GroqProvider("key", "llama-test")
    provider.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

    result = await provider.generate("hi", max_tokens=20)

    assert result.content is None
    assert "boom" in (result.error or "")


@pytest.mark.asyncio
async def test_cerebras_provider_parses_response():
    provider = CerebrasProvider("key", "gpt-oss-120b")
    message = MagicMock(content="hello")
    choice = MagicMock(message=message)
    usage = MagicMock(prompt_tokens=2, completion_tokens=4)
    response = MagicMock(choices=[choice], usage=usage)
    provider.client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.generate("hi", max_tokens=20)

    assert result.provider == "cerebras"
    assert result.content == "hello"
    assert result.tokens == 6


@pytest.mark.asyncio
async def test_cerebras_provider_degrades_on_exception():
    provider = CerebrasProvider("key", "gpt-oss-120b")
    provider.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

    result = await provider.generate("hi", max_tokens=20)

    assert result.content is None
    assert "boom" in (result.error or "")


@pytest.mark.asyncio
async def test_nvidia_provider_parses_response():
    provider = NvidiaProvider("key", "meta/llama-3.3-70b-instruct")
    message = MagicMock(content="hello")
    choice = MagicMock(message=message)
    usage = MagicMock(prompt_tokens=2, completion_tokens=4)
    response = MagicMock(choices=[choice], usage=usage)
    provider.client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.generate("hi", max_tokens=20)

    assert result.provider == "nvidia"
    assert result.content == "hello"
    assert result.tokens == 6
    assert result.error is None


@pytest.mark.asyncio
async def test_nvidia_provider_degrades_on_exception():
    provider = NvidiaProvider("key", "meta/llama-3.3-70b-instruct")
    provider.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

    result = await provider.generate("hi", max_tokens=20)

    assert result.content is None
    assert "boom" in (result.error or "")


@pytest.mark.asyncio
async def test_opencode_provider_parses_response():
    provider = OpenCodeProvider("key", "big-pickle")
    message = MagicMock(content="hello")
    choice = MagicMock(message=message)
    usage = MagicMock(prompt_tokens=2, completion_tokens=4)
    response = MagicMock(choices=[choice], usage=usage)
    provider.client.chat.completions.create = AsyncMock(return_value=response)

    result = await provider.generate("hi", max_tokens=20)

    assert result.provider == "opencode"
    assert result.content == "hello"
    assert result.tokens == 6
    assert result.error is None


@pytest.mark.asyncio
async def test_opencode_provider_degrades_on_exception():
    provider = OpenCodeProvider("key", "big-pickle")
    provider.client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))

    result = await provider.generate("hi", max_tokens=20)

    assert result.content is None
    assert "boom" in (result.error or "")


def test_groq_cerebras_nvidia_opencode_share_implementation_but_have_distinct_identity():
    groq = GroqProvider("key", "model-a")
    cerebras = CerebrasProvider("key", "model-b")
    nvidia = NvidiaProvider("key", "model-c")
    opencode = OpenCodeProvider("key", "model-d")

    assert isinstance(groq, OpenAICompatibleProvider)
    assert isinstance(cerebras, OpenAICompatibleProvider)
    assert isinstance(nvidia, OpenAICompatibleProvider)
    assert isinstance(opencode, OpenAICompatibleProvider)
    assert groq.provider_name == "groq"
    assert cerebras.provider_name == "cerebras"
    assert nvidia.provider_name == "nvidia"
    assert opencode.provider_name == "opencode"
    assert str(groq.client.base_url).startswith("https://api.groq.com")
    assert str(cerebras.client.base_url).startswith("https://api.cerebras.ai")
    assert str(nvidia.client.base_url).startswith("https://integrate.api.nvidia.com")
    assert str(opencode.client.base_url).startswith("https://opencode.ai/zen")

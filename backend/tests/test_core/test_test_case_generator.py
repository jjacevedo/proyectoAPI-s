import pytest

from app.core.test_case_generator import TestCaseGenerator
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


def test_build_prompt_includes_original_request_and_asks_for_test_case_only():
    generator = TestCaseGenerator(max_tokens=100)
    prompt = generator.build_prompt("Implementa una función que sume dos números.")
    assert "Implementa una función que sume dos números." in prompt
    assert "unittest.TestCase" in prompt
    assert "do not define them yourself" in prompt


@pytest.mark.asyncio
async def test_run_returns_providers_generated_content():
    provider = FakeProvider(
        "openai", LLMResponse(provider="openai", model="gpt", content="```python\nclass T: pass\n```")
    )
    generator = TestCaseGenerator(max_tokens=100)
    response = await generator.run(provider, "original request")
    assert response.content == "```python\nclass T: pass\n```"

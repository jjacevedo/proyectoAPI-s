import pytest

from app.core.solver_script_generator import SolverScriptGenerator
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


def test_build_prompt_includes_original_request_and_calc_marker_instructions():
    generator = SolverScriptGenerator(max_tokens=100)
    prompt = generator.build_prompt("Un tren viaja a 80 km/h durante 3 horas. ¿Cuántos km recorre?")
    assert "Un tren viaja a 80 km/h durante 3 horas." in prompt
    assert "__CALC_RESULT__" in prompt
    assert "standard library only" in prompt


@pytest.mark.asyncio
async def test_run_returns_providers_generated_content():
    provider = FakeProvider(
        "openai",
        LLMResponse(provider="openai", model="gpt", content="```python\nprint('__CALC_RESULT__ 240')\n```"),
    )
    generator = SolverScriptGenerator(max_tokens=100)
    response = await generator.run(provider, "original request")
    assert response.content == "```python\nprint('__CALC_RESULT__ 240')\n```"

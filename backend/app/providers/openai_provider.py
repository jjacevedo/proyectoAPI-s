import time

from openai import AsyncOpenAI

from app.providers.base import LLMProvider, LLMResponse
from app.providers.pricing import estimate_cost


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        started = time.perf_counter()
        try:
            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
                max_output_tokens=max_tokens,
            )
            usage = response.usage
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                content=response.output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tokens=input_tokens + output_tokens,
                latency_ms=(time.perf_counter() - started) * 1000,
                cost_estimated_usd=estimate_cost(self.model, input_tokens, output_tokens),
            )
        except Exception as exc:
            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
            )

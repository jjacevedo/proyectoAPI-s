import time

from anthropic import AsyncAnthropic

from app.providers.base import LLMProvider, LLMResponse
from app.providers.pricing import estimate_cost


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        started = time.perf_counter()
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "\n".join(block.text for block in response.content if hasattr(block, "text"))
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                content=text,
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

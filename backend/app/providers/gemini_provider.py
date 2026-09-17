import time

from google import genai

from app.providers.base import LLMProvider, LLMResponse
from app.providers.pricing import estimate_cost


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        started = time.perf_counter()
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"max_output_tokens": max_tokens},
            )
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                content=response.text,
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

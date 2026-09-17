import time

from openai import AsyncOpenAI

from app.providers.base import LLMProvider, LLMResponse
from app.providers.pricing import estimate_cost


class OpenAICompatibleProvider(LLMProvider):
    """Base compartida para providers que exponen un endpoint /chat/completions
    compatible con la API de OpenAI (Groq, Cerebras, ...). Usa chat.completions,
    no responses.create: los providers gratuitos compatibles con OpenAI solo
    implementan la forma mas antigua de la API.
    """

    def __init__(self, api_key: str, model: str, *, base_url: str, provider_name: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.provider_name = provider_name

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        started = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            usage = response.usage
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            return LLMResponse(
                provider=self.provider_name,
                model=self.model,
                content=content,
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

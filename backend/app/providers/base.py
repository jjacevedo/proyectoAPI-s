from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    provider: str
    model: str
    content: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tokens: int = 0
    latency_ms: float = 0
    cost_estimated_usd: float | None = None
    error: str | None = None
    raw: Any | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None and bool(self.content)


class LLMProvider(ABC):
    provider_name: str
    model: str

    @abstractmethod
    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        raise NotImplementedError

    async def analyze(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return await self.generate(prompt, max_tokens=max_tokens)

    async def critique(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return await self.generate(prompt, max_tokens=max_tokens)

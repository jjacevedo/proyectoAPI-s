import asyncio
import time

from app.config import Settings
from app.core.synthesizer import Synthesizer
from app.providers.base import LLMProvider, LLMResponse


class AllProvidersFailedError(RuntimeError):
    pass


class DeliberationResult:
    def __init__(self, final_answer: str, responses: list[LLMResponse], latency_ms: float) -> None:
        self.final_answer = final_answer
        self.responses = responses
        self.latency_ms = latency_ms


class DeliberationOrchestrator:
    def __init__(self, providers: dict[str, LLMProvider], settings: Settings) -> None:
        self.providers = providers
        self.settings = settings

    async def _call_provider(self, provider: LLMProvider, prompt: str) -> LLMResponse:
        try:
            return await asyncio.wait_for(
                provider.generate(prompt, max_tokens=self.settings.max_tokens_per_request),
                timeout=self.settings.provider_timeout_seconds,
            )
        except Exception as exc:
            return LLMResponse(
                provider=provider.provider_name,
                model=provider.model,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def run(self, prompt: str) -> DeliberationResult:
        if not self.providers:
            raise AllProvidersFailedError("No LLM providers are configured")

        started = time.perf_counter()
        results = await asyncio.gather(
            *(self._call_provider(provider, prompt) for provider in self.providers.values()),
            return_exceptions=True,
        )
        responses: list[LLMResponse] = []
        for provider, result in zip(self.providers.values(), results, strict=True):
            if isinstance(result, LLMResponse):
                responses.append(result)
            else:
                responses.append(
                    LLMResponse(
                        provider=provider.provider_name,
                        model=provider.model,
                        error=f"{type(result).__name__}: {result}",
                    )
                )

        successful = [response for response in responses if response.succeeded]
        if not successful:
            raise AllProvidersFailedError("All configured LLM providers failed")

        synthesizer_provider = self.providers.get(self.settings.synthesizer_provider)
        if synthesizer_provider is None:
            synthesizer_provider = next(iter(self.providers.values()))

        synthesis = await asyncio.wait_for(
            Synthesizer(synthesizer_provider, self.settings.max_tokens_per_request).run(prompt, successful),
            timeout=self.settings.provider_timeout_seconds,
        )
        if synthesis.succeeded:
            final_answer = synthesis.content or successful[0].content or ""
            responses.append(synthesis)
        else:
            # MVP fallback: return the first successful candidate if synthesis fails.
            final_answer = successful[0].content or ""
            responses.append(synthesis)

        return DeliberationResult(
            final_answer=final_answer,
            responses=responses,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

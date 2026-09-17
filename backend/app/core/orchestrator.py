import asyncio
import time

from app.config import Settings
from app.core.critic import CrossCritic, Critique
from app.core.disagreement import DisagreementAssessment, DisagreementDetector, DisagreementLevel
from app.core.reevaluator import Reevaluator
from app.core.router import RoutingDecision, TaskRouter
from app.core.synthesizer import Synthesizer
from app.providers.base import LLMProvider, LLMResponse


class AllProvidersFailedError(RuntimeError):
    pass


def _default_disagreement_assessment() -> DisagreementAssessment:
    return DisagreementAssessment(
        level=DisagreementLevel.NOT_APPLICABLE,
        reason="No hubo ronda de crítica cruzada (menos de 2 respuestas exitosas o crítica desactivada)",
        evidence=[],
    )


class DeliberationResult:
    def __init__(
        self,
        final_answer: str,
        responses: list[LLMResponse],
        latency_ms: float,
        routing: RoutingDecision,
        critiques: list[Critique] | None = None,
        disagreement: DisagreementAssessment | None = None,
        revisions: list[LLMResponse] | None = None,
    ) -> None:
        self.final_answer = final_answer
        self.responses = responses
        self.latency_ms = latency_ms
        self.routing = routing
        self.critiques = critiques or []
        self.disagreement = disagreement or _default_disagreement_assessment()
        self.revisions = revisions or []


class DeliberationOrchestrator:
    def __init__(
        self,
        providers: dict[str, LLMProvider],
        settings: Settings,
        router: TaskRouter | None = None,
        critic: CrossCritic | None = None,
        disagreement_detector: DisagreementDetector | None = None,
        reevaluator: Reevaluator | None = None,
    ) -> None:
        self.providers = providers
        self.settings = settings
        self.router = router or TaskRouter()
        self.critic = critic or CrossCritic(settings.max_tokens_per_request)
        self.disagreement_detector = disagreement_detector or DisagreementDetector()
        self.reevaluator = reevaluator or Reevaluator(settings.max_tokens_per_request)

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

    async def _run_critique(
        self,
        provider: LLMProvider,
        original_prompt: str,
        own_response: LLMResponse,
        other_responses: list[LLMResponse],
    ) -> Critique:
        try:
            return await asyncio.wait_for(
                self.critic.run(provider, original_prompt, own_response, other_responses),
                timeout=self.settings.provider_timeout_seconds,
            )
        except Exception as exc:
            return Critique(
                response=LLMResponse(
                    provider=provider.provider_name,
                    model=provider.model,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                reviewed_providers=[f"{r.provider}/{r.model}" for r in other_responses],
            )

    async def _run_reevaluation(
        self,
        provider: LLMProvider,
        original_prompt: str,
        own_response: LLMResponse,
        critiques: list[Critique],
    ) -> LLMResponse:
        try:
            return await asyncio.wait_for(
                self.reevaluator.run(provider, original_prompt, own_response, critiques),
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

        decision = self.router.classify(prompt)
        active_providers = self.router.select_providers(
            self.providers, decision, self.settings.provider_priority_list
        )

        started = time.perf_counter()
        results = await asyncio.gather(
            *(self._call_provider(provider, prompt) for provider in active_providers.values()),
            return_exceptions=True,
        )
        responses: list[LLMResponse] = []
        for provider, result in zip(active_providers.values(), results, strict=True):
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

        responses_by_provider_name = {response.provider: response for response in successful}

        critiques: list[Critique] = []
        if self.settings.enable_cross_critique and len(successful) >= 2:
            critique_tasks = []
            critique_providers = []
            for name, own_response in responses_by_provider_name.items():
                provider = active_providers.get(name)
                if provider is None:
                    continue
                others = [
                    response
                    for other_name, response in responses_by_provider_name.items()
                    if other_name != name
                ]
                critique_providers.append(provider)
                critique_tasks.append(self._run_critique(provider, prompt, own_response, others))

            critique_results = await asyncio.gather(*critique_tasks, return_exceptions=True)
            for provider, result in zip(critique_providers, critique_results, strict=True):
                if isinstance(result, Critique):
                    critiques.append(result)
                else:
                    critiques.append(
                        Critique(
                            response=LLMResponse(
                                provider=provider.provider_name,
                                model=provider.model,
                                error=f"{type(result).__name__}: {result}",
                            ),
                            reviewed_providers=[],
                        )
                    )

        disagreement = self.disagreement_detector.assess(critiques)

        revisions: list[LLMResponse] = []
        critiques_available = [critique for critique in critiques if critique.succeeded]
        if self.settings.enable_reevaluation_round and len(successful) >= 2 and critiques_available:
            reevaluation_tasks = []
            reevaluation_providers = []
            for name, own_response in responses_by_provider_name.items():
                provider = active_providers.get(name)
                if provider is None:
                    continue
                reevaluation_providers.append((name, provider))
                reevaluation_tasks.append(
                    self._run_reevaluation(provider, prompt, own_response, critiques)
                )

            reevaluation_results = await asyncio.gather(*reevaluation_tasks, return_exceptions=True)
            revised_by_name: dict[str, LLMResponse] = {}
            for (name, provider), result in zip(reevaluation_providers, reevaluation_results, strict=True):
                if isinstance(result, LLMResponse):
                    revision = result
                else:
                    revision = LLMResponse(
                        provider=provider.provider_name,
                        model=provider.model,
                        error=f"{type(result).__name__}: {result}",
                    )
                revisions.append(revision)
                if revision.succeeded:
                    revised_by_name[name] = revision

            # Use the revised answer where available; fall back to the
            # original round-1 answer for any provider whose revision failed.
            successful = [
                revised_by_name.get(name, response)
                for name, response in responses_by_provider_name.items()
            ]

        synthesizer_provider = active_providers.get(self.settings.synthesizer_provider)
        if synthesizer_provider is None:
            synthesizer_provider = next(iter(active_providers.values()))

        synthesis = await asyncio.wait_for(
            Synthesizer(synthesizer_provider, self.settings.max_tokens_per_request).run(
                prompt, successful, critiques, disagreement
            ),
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
            routing=decision,
            critiques=critiques,
            disagreement=disagreement,
            revisions=revisions,
        )

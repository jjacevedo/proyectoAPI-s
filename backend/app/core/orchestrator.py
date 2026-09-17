import asyncio
import time

from app.config import Settings
from app.core.calculation_verifier import CalculationVerification, CalculationVerifier
from app.core.code_verifier import CodeVerification, CodeVerifier, extract_python_code
from app.core.critic import CrossCritic, Critique
from app.core.disagreement import DisagreementAssessment, DisagreementDetector, DisagreementLevel
from app.core.reevaluator import Reevaluator
from app.core.router import RoutingDecision, TaskRouter, TaskType
from app.core.solver_script_generator import SolverScriptGenerator
from app.core.synthesizer import Synthesizer
from app.core.test_case_generator import TestCaseGenerator
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
        code_verifications: list[CodeVerification] | None = None,
        generated_tests: str | None = None,
        test_generation: LLMResponse | None = None,
        calculation_verifications: list[CalculationVerification] | None = None,
        reference_calculation: str | None = None,
        solver_generation: LLMResponse | None = None,
    ) -> None:
        self.final_answer = final_answer
        self.responses = responses
        self.latency_ms = latency_ms
        self.routing = routing
        self.critiques = critiques or []
        self.disagreement = disagreement or _default_disagreement_assessment()
        self.revisions = revisions or []
        self.code_verifications = code_verifications or []
        self.generated_tests = generated_tests
        self.test_generation = test_generation
        self.calculation_verifications = calculation_verifications or []
        self.reference_calculation = reference_calculation
        self.solver_generation = solver_generation


class DeliberationOrchestrator:
    def __init__(
        self,
        providers: dict[str, LLMProvider],
        settings: Settings,
        router: TaskRouter | None = None,
        critic: CrossCritic | None = None,
        disagreement_detector: DisagreementDetector | None = None,
        reevaluator: Reevaluator | None = None,
        test_case_generator: TestCaseGenerator | None = None,
        code_verifier: CodeVerifier | None = None,
        solver_script_generator: SolverScriptGenerator | None = None,
        calculation_verifier: CalculationVerifier | None = None,
    ) -> None:
        self.providers = providers
        self.settings = settings
        self.router = router or TaskRouter()
        self.critic = critic or CrossCritic(settings.max_tokens_per_request)
        self.disagreement_detector = disagreement_detector or DisagreementDetector()
        self.reevaluator = reevaluator or Reevaluator(settings.max_tokens_per_request)
        self.test_case_generator = test_case_generator or TestCaseGenerator(settings.max_tokens_per_request)
        self.code_verifier = code_verifier or CodeVerifier(
            settings.code_execution_timeout_seconds, settings.code_max_output_chars
        )
        self.solver_script_generator = solver_script_generator or SolverScriptGenerator(
            settings.max_tokens_per_request
        )
        self.calculation_verifier = calculation_verifier or CalculationVerifier(
            settings.code_execution_timeout_seconds,
            settings.code_max_output_chars,
            settings.calculation_tolerance,
        )

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

    async def _run_code_verification(self, candidate_code: str, test_code: str) -> CodeVerification:
        try:
            return await self.code_verifier.verify(candidate_code, test_code)
        except Exception as exc:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout="",
                stderr="",
                error=f"{type(exc).__name__}: {exc}",
            )

    async def _compute_calculation_reference(self, solver_script: str) -> tuple[float | None, str, str, bool]:
        """Devuelve (reference_value, stdout, stderr, timed_out). Nunca
        lanza: cualquier excepcion del sandbox se traduce en reference_value
        None con timed_out=False (tratado como fallo de calculo, no de
        infraestructura, igual que el resto de este metodo)."""
        try:
            value, sandbox_result = await self.calculation_verifier.compute_reference(solver_script)
            return value, sandbox_result.stdout, sandbox_result.stderr, sandbox_result.timed_out
        except Exception as exc:
            return None, "", f"{type(exc).__name__}: {exc}", False

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

        code_verifications: list[CodeVerification] = []
        generated_tests: str | None = None
        test_response: LLMResponse | None = None
        if decision.task_type == TaskType.CODE and self.settings.enable_code_verification and successful:
            try:
                test_response = await asyncio.wait_for(
                    self.test_case_generator.run(synthesizer_provider, prompt),
                    timeout=self.settings.provider_timeout_seconds,
                )
            except Exception as exc:
                test_response = LLMResponse(
                    provider=synthesizer_provider.provider_name,
                    model=synthesizer_provider.model,
                    error=f"{type(exc).__name__}: {exc}",
                )

            test_code = extract_python_code(test_response.content) if test_response.succeeded else None
            if test_response.succeeded and test_code is not None:
                generated_tests = test_code
                verification_tasks = []
                verification_targets = []
                for response in successful:
                    candidate_code = extract_python_code(response.content)
                    if candidate_code is None:
                        code_verifications.append(
                            CodeVerification(
                                provider=response.provider,
                                model=response.model,
                                passed=False,
                                tests_run=0,
                                tests_passed=0,
                                tests_failed=0,
                                stdout="",
                                stderr="",
                                error="no se encontró un bloque de código Python en la respuesta",
                            )
                        )
                        continue
                    verification_targets.append(response)
                    verification_tasks.append(self._run_code_verification(candidate_code, test_code))

                if verification_tasks:
                    verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)
                    for response, result in zip(verification_targets, verification_results, strict=True):
                        if isinstance(result, CodeVerification):
                            result.provider = response.provider
                            result.model = response.model
                            code_verifications.append(result)
                        else:
                            code_verifications.append(
                                CodeVerification(
                                    provider=response.provider,
                                    model=response.model,
                                    passed=False,
                                    tests_run=0,
                                    tests_passed=0,
                                    tests_failed=0,
                                    stdout="",
                                    stderr="",
                                    error=f"{type(result).__name__}: {result}",
                                )
                            )
            elif not test_response.succeeded:
                code_verifications.append(
                    CodeVerification(
                        provider=test_response.provider,
                        model=test_response.model,
                        passed=False,
                        tests_run=0,
                        tests_passed=0,
                        tests_failed=0,
                        stdout="",
                        stderr="",
                        error=f"no se pudo generar el suite de tests: {test_response.error}",
                    )
                )

        calculation_verifications: list[CalculationVerification] = []
        reference_calculation: str | None = None
        solver_response: LLMResponse | None = None
        if decision.task_type == TaskType.MATH and self.settings.enable_calculation_verification and successful:
            try:
                solver_response = await asyncio.wait_for(
                    self.solver_script_generator.run(synthesizer_provider, prompt),
                    timeout=self.settings.provider_timeout_seconds,
                )
            except Exception as exc:
                solver_response = LLMResponse(
                    provider=synthesizer_provider.provider_name,
                    model=synthesizer_provider.model,
                    error=f"{type(exc).__name__}: {exc}",
                )

            solver_code = extract_python_code(solver_response.content) if solver_response.succeeded else None
            if solver_response.succeeded and solver_code is not None:
                reference_value, ref_stdout, ref_stderr, ref_timed_out = await self._compute_calculation_reference(
                    solver_code
                )
                if reference_value is not None:
                    reference_calculation = solver_code
                    for response in successful:
                        calculation_verifications.append(
                            self.calculation_verifier.verify_candidate(
                                response.provider, response.model, response.content, reference_value
                            )
                        )
                else:
                    calculation_verifications.append(
                        CalculationVerification(
                            provider=solver_response.provider,
                            model=solver_response.model,
                            passed=False,
                            error="no se pudo calcular un valor de referencia"
                            + (" (tiempo de ejecución agotado)" if ref_timed_out else f": {ref_stderr[:500]}"),
                            timed_out=ref_timed_out,
                        )
                    )
            elif not solver_response.succeeded:
                calculation_verifications.append(
                    CalculationVerification(
                        provider=solver_response.provider,
                        model=solver_response.model,
                        passed=False,
                        error=f"no se pudo generar el script de cálculo: {solver_response.error}",
                    )
                )

        synthesis = await asyncio.wait_for(
            Synthesizer(synthesizer_provider, self.settings.max_tokens_per_request).run(
                prompt, successful, critiques, disagreement, code_verifications, calculation_verifications
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
            code_verifications=code_verifications,
            generated_tests=generated_tests,
            test_generation=test_response,
            calculation_verifications=calculation_verifications,
            reference_calculation=reference_calculation,
            solver_generation=solver_response,
        )

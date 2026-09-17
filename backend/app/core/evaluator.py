import re
import time

from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse

_VERDICT_RE = re.compile(r"__VERDICT__\s+(single|multi|tie)", re.IGNORECASE)


class SingleLLMBaseline:
    """Corre UNA sola llamada a UN solo provider sobre el prompt original,
    sin router, sin critica cruzada, sin reevaluacion, sin verificacion
    externa ni sintesis — el "1-LLM" de la comparacion 1-LLM vs N-LLM del
    issue #14. Existe para que el framework de evaluacion tenga una
    referencia real contra la que comparar el pipeline de deliberacion
    completo, en vez de asumir que deliberar es mejor.
    """

    async def run(self, provider: LLMProvider, prompt: str, *, max_tokens: int) -> LLMResponse:
        started = time.perf_counter()
        try:
            return await provider.generate(prompt, max_tokens=max_tokens)
        except Exception as exc:
            return LLMResponse(
                provider=provider.provider_name,
                model=provider.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
            )


def extract_verdict(content: str | None) -> tuple[str | None, str]:
    """Parsea el marcador __VERDICT__ single|multi|tie del veredicto del
    juez. Devuelve (verdict, reasoning) — reasoning es el contenido menos
    la linea del marcador. verdict es None si no se pudo parsear."""
    if not content:
        return None, ""
    match = _VERDICT_RE.search(content)
    verdict = match.group(1).lower() if match else None
    reasoning = _VERDICT_RE.sub("", content).strip()
    return verdict, reasoning


class EvaluationJudge:
    """Compara la respuesta de un solo LLM contra la respuesta final del
    pipeline de deliberacion multi-LLM y emite un veredicto (single/multi/
    tie) con una justificacion breve. Es, por construccion, un juicio de
    OTRO LLM — evidencia adicional, no una verdad objetiva como la
    ejecucion de codigo o el motor de calculo (#11/#12); se documenta como
    tal y no se presenta como una metrica de calidad definitiva.
    """

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    def build_prompt(self, original_prompt: str, single_answer: str, multi_answer: str) -> str:
        return "\n".join([
            "You are an impartial evaluator comparing two answers to the same "
            "request: one produced by a single LLM call, the other by a "
            "multi-LLM deliberation pipeline (parallel generation, optional "
            "cross-critique, reevaluation, and external verification before "
            "synthesis).",
            "Judge ONLY correctness, completeness, and usefulness relative to "
            "the request. Do not prefer the longer or more elaborate answer "
            "unless it is genuinely more correct or useful.",
            "\nORIGINAL REQUEST:\n" + original_prompt,
            "\nANSWER A (single LLM):\n" + single_answer,
            "\nANSWER B (multi-LLM deliberation):\n" + multi_answer,
            "\nEnd your response with exactly one line in this format, with no "
            "other text on that line:",
            "__VERDICT__ single|multi|tie",
            "(single = Answer A is better, multi = Answer B is better, tie = "
            "no meaningful difference). Before that line, briefly justify "
            "your verdict in 2-3 sentences.",
        ])

    async def run(self, provider: LLMProvider, original_prompt: str, single_answer: str, multi_answer: str) -> LLMResponse:
        prompt = self.build_prompt(original_prompt, single_answer, multi_answer)
        return await provider.generate(prompt, max_tokens=self.max_tokens)


class EvaluationResult(BaseModel):
    prompt: str
    single_answer: str | None = None
    single_provider: str = ""
    single_model: str = ""
    single_tokens: int = 0
    single_cost_estimated_usd: float | None = None
    single_latency_ms: float = 0
    single_error: str | None = None
    multi_answer: str
    multi_tokens: int = 0
    multi_cost_estimated_usd: float | None = None
    multi_latency_ms: float = 0
    judge_verdict: str | None = None
    judge_reasoning: str | None = None
    judge_error: str | None = None

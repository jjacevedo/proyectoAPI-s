import re

from pydantic import BaseModel

from app.core.sandbox_runner import SandboxResult, run_sandboxed_script

_CALC_RESULT_RE = re.compile(r"__CALC_RESULT__\s+(-?[\d.eE+-]+)")
_NUMBER_RE = re.compile(r"-?\d[\d,.]*\d|-?\d")


def extract_calc_result(stdout: str) -> float | None:
    """Parsea la linea de marcador estructurada (__CALC_RESULT__ <numero>)
    impresa por el script del solver, ejecutado en el sandbox. None si no
    aparece o no es un numero valido."""
    match = _CALC_RESULT_RE.search(stdout)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def extract_final_number(content: str | None) -> float | None:
    """Heuristica: toma el ULTIMO numero que aparece en una respuesta en
    texto libre como la respuesta final del candidato (asumiendo, como el
    resto de las heuristicas del router, que la respuesta final suele
    aparecer al final del texto). Se asume '.' como separador decimal y ','
    como separador de miles (se descarta); no es una interpretacion
    perfecta de todos los formatos numericos posibles, es una aproximacion
    razonable en costo cero (sin llamada adicional a un LLM para extraer el
    numero). None si no hay ningun numero en el texto."""
    if not content:
        return None
    matches = _NUMBER_RE.findall(content)
    if not matches:
        return None
    normalized = matches[-1].replace(",", "")
    try:
        return float(normalized)
    except ValueError:
        return None


class CalculationVerification(BaseModel):
    provider: str = ""
    model: str = ""
    passed: bool
    candidate_value: float | None = None
    reference_value: float | None = None
    difference: float | None = None
    error: str | None = None
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.error is None and not self.timed_out


class CalculationVerifier:
    def __init__(self, timeout_seconds: float, max_output_chars: int, tolerance: float = 1e-6) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars
        self.tolerance = tolerance

    async def compute_reference(self, solver_script: str) -> tuple[float | None, SandboxResult]:
        result = await run_sandboxed_script(
            solver_script, timeout_seconds=self.timeout_seconds, max_output_chars=self.max_output_chars
        )
        if not result.succeeded:
            return None, result
        return extract_calc_result(result.stdout), result

    def verify_candidate(
        self,
        provider: str,
        model: str,
        candidate_content: str | None,
        reference_value: float,
    ) -> CalculationVerification:
        candidate_value = extract_final_number(candidate_content)
        if candidate_value is None:
            return CalculationVerification(
                provider=provider,
                model=model,
                passed=False,
                reference_value=reference_value,
                error="no se encontró un valor numérico final en la respuesta",
            )

        difference = abs(candidate_value - reference_value)
        tolerance_abs = max(1e-9, self.tolerance * abs(reference_value))
        return CalculationVerification(
            provider=provider,
            model=model,
            passed=difference <= tolerance_abs,
            candidate_value=candidate_value,
            reference_value=reference_value,
            difference=difference,
        )

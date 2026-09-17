from dataclasses import dataclass
from enum import Enum

from app.providers.base import LLMProvider


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    CODE = "code"
    GENERAL = "general"


# Palabras clave orientativas, no exhaustivas. El objetivo no es una
# clasificacion perfecta sino evitar gastar los 3 providers en preguntas
# simples (principio de gestion de costos del documento de diseno).
_HIGH_COMPLEXITY_KEYWORDS = (
    "arquitectura", "diseña", "diseno", "diseñar", "analiza", "analizar",
    "compara", "comparar", "optimiza", "optimizar", "algoritmo",
    "escalabilidad", "seguridad", "concurrencia", "refactoriza",
    "demuestra", "demostración", "demostracion", "investiga", "estrategia",
    "propón", "propon",
)
_MEDIUM_COMPLEXITY_KEYWORDS = (
    "explica", "resume", "traduce", "corrige", "mejora", "genera",
    "escribe", "código", "codigo", "función", "funcion", "clase",
    "implementa",
)

# Independiente de la complejidad: si el prompt parece pedir programacion,
# activa la verificacion externa de codigo (issue #11) en vez de depender
# solo de la opinion de otro LLM.
_CODE_KEYWORDS = (
    "código", "codigo", "function", "función", "funcion", "clase ",
    "algoritmo", "algorithm", "script", "programa", "program",
    "implementa", "implement", "debug", "bug ", "python", "javascript",
    "typescript", "def ", "método", "metodo", "compila", "refactoriza",
    "unit test", "test unitario", "programación", "programacion",
)


@dataclass(frozen=True)
class RoutingDecision:
    complexity: TaskComplexity
    provider_count: int
    reason: str
    task_type: TaskType = TaskType.GENERAL


class TaskRouter:
    """Clasifica la complejidad de una solicitud y decide cuantos
    providers usar, sin acoplarse a ningun proveedor concreto (el mismo
    principio de abstraccion que LLMProvider).
    """

    def __init__(self, low_threshold_chars: int = 60, high_threshold_chars: int = 220) -> None:
        self.low_threshold_chars = low_threshold_chars
        self.high_threshold_chars = high_threshold_chars

    def classify(self, prompt: str) -> RoutingDecision:
        normalized = prompt.lower()
        length = len(prompt.strip())
        task_type = TaskType.CODE if any(keyword in normalized for keyword in _CODE_KEYWORDS) else TaskType.GENERAL

        if any(keyword in normalized for keyword in _HIGH_COMPLEXITY_KEYWORDS) or length > self.high_threshold_chars:
            return RoutingDecision(
                complexity=TaskComplexity.HIGH,
                provider_count=3,
                reason="palabra clave de alta complejidad o prompt largo",
                task_type=task_type,
            )
        if any(keyword in normalized for keyword in _MEDIUM_COMPLEXITY_KEYWORDS) or length > self.low_threshold_chars:
            return RoutingDecision(
                complexity=TaskComplexity.MEDIUM,
                provider_count=2,
                reason="palabra clave de complejidad media o prompt moderado",
                task_type=task_type,
            )
        return RoutingDecision(
            complexity=TaskComplexity.LOW,
            provider_count=1,
            reason="prompt corto sin palabras clave de mayor complejidad",
            task_type=task_type,
        )

    def select_providers(
        self,
        providers: dict[str, LLMProvider],
        decision: RoutingDecision,
        priority: list[str],
    ) -> dict[str, LLMProvider]:
        ordered_names = [name for name in priority if name in providers]
        ordered_names += [name for name in providers if name not in ordered_names]
        selected_names = ordered_names[: decision.provider_count]
        return {name: providers[name] for name in selected_names}

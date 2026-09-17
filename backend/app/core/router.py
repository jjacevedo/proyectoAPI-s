from dataclasses import dataclass
from enum import Enum

from app.providers.base import LLMProvider


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskType(str, Enum):
    CODE = "code"
    MATH = "math"
    FACTUAL = "factual"
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

# Independiente de la complejidad y de _CODE_KEYWORDS: si el prompt pide un
# calculo numerico (issue #12), activa el motor de calculo en vez de confiar
# en la aritmetica de un LLM. Se revisa DESPUES de _CODE_KEYWORDS (ver
# classify()) porque "escribe una funcion que calcule..." es una tarea de
# programacion, no una pregunta aritmetica directa.
_MATH_KEYWORDS = (
    "calcula", "cuánto es", "cuanto es", "cuál es el resultado",
    "cual es el resultado", "resuelve la ecuación", "resuelve la ecuacion",
    "ecuación", "ecuacion", "porcentaje", "%", "raíz cuadrada",
    "raiz cuadrada", "cuántos", "cuantos", "promedio", "área de", "area de",
    "perímetro", "perimetro", "matemática", "matematica", "aritmética",
    "aritmetica",
)

# Independiente de complejidad/_CODE_KEYWORDS/_MATH_KEYWORDS: preguntas
# clasicas de busqueda de un hecho puntual sobre una entidad con nombre
# (issue #13), donde una fuente externa (Wikipedia) es evidencia mas fuerte
# que el consenso entre modelos. Deliberadamente NO incluye "qué es"/"qué
# fue" (demasiado amplio: cubriria explicaciones conceptuales/tecnicas que
# ya sirven bien los candidatos sin necesidad de una busqueda externa).
_FACTUAL_KEYWORDS = (
    "quién es", "quien es", "quién fue", "quien fue", "cuándo nació",
    "cuando nacio", "cuándo murió", "cuando murio", "en qué año",
    "en que año", "capital de", "población de", "poblacion de",
    "quién descubrió", "quien descubrio", "quién inventó", "quien invento",
    "quién ganó", "quien gano", "cuántos habitantes tiene",
    "cuantos habitantes tiene", "dónde queda", "donde queda",
    "dónde está ubicad", "donde esta ubicad",
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

    def __init__(
        self,
        low_threshold_chars: int = 60,
        high_threshold_chars: int = 220,
        forced_complexity: TaskComplexity | None = None,
    ) -> None:
        self.low_threshold_chars = low_threshold_chars
        self.high_threshold_chars = high_threshold_chars
        # Usado por los modos "rápido"/"máxima verificación" (issue #16) para
        # saltarse la heurística de longitud/palabras clave y forzar siempre
        # 1 o 3 providers, sin importar el contenido del prompt.
        self.forced_complexity = forced_complexity

    def classify(self, prompt: str) -> RoutingDecision:
        normalized = prompt.lower()
        length = len(prompt.strip())
        if any(keyword in normalized for keyword in _CODE_KEYWORDS):
            task_type = TaskType.CODE
        elif any(keyword in normalized for keyword in _MATH_KEYWORDS):
            task_type = TaskType.MATH
        elif any(keyword in normalized for keyword in _FACTUAL_KEYWORDS):
            task_type = TaskType.FACTUAL
        else:
            task_type = TaskType.GENERAL

        if self.forced_complexity is not None:
            provider_count = {TaskComplexity.LOW: 1, TaskComplexity.MEDIUM: 2, TaskComplexity.HIGH: 3}[
                self.forced_complexity
            ]
            return RoutingDecision(
                complexity=self.forced_complexity,
                provider_count=provider_count,
                reason="complejidad forzada por el modo de conversación",
                task_type=task_type,
            )

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

from enum import Enum

from pydantic import BaseModel

from app.core.critic import Critique


class DisagreementLevel(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    CONSENSUS = "consensus"
    DISAGREEMENT = "disagreement"


class DisagreementAssessment(BaseModel):
    level: DisagreementLevel
    reason: str
    evidence: list[str]


# Palabras clave orientativas (bilingue), no exhaustivas: buscan senales de
# desacuerdo dentro del CONTENIDO de las criticas ya generadas (issue #8),
# no en las respuestas crudas. Las criticas ya son un analisis semantico
# hecho por un LLM, asi que esto es mas fiel al "considerar el significado"
# que comparar el texto de las respuestas originales, y no cuesta ninguna
# llamada extra (misma logica que el heuristico de TaskRouter).
_DISAGREEMENT_KEYWORDS = (
    "contradice", "contradicción", "contradiccion", "contradictorio",
    "incorrecto", "erróneo", "erroneo", "no es correcto", "difiere",
    "diverge", "en desacuerdo", "inconsistente", "no coincide",
    "equivocad",
    "contradicts", "incorrect", "inconsistent", "disagrees", "conflicts",
    "erroneous",
)


class DisagreementDetector:
    def assess(self, critiques: list[Critique]) -> DisagreementAssessment:
        if not critiques:
            return DisagreementAssessment(
                level=DisagreementLevel.NOT_APPLICABLE,
                reason="No hubo ronda de crítica cruzada (menos de 2 respuestas exitosas o crítica desactivada)",
                evidence=[],
            )

        evidence: list[str] = []
        for critique in critiques:
            if not critique.succeeded:
                continue
            content = critique.response.content or ""
            normalized = content.lower()
            if any(keyword in normalized for keyword in _DISAGREEMENT_KEYWORDS):
                evidence.append(content)

        if evidence:
            return DisagreementAssessment(
                level=DisagreementLevel.DISAGREEMENT,
                reason="Al menos una crítica identifica una contradicción o error entre las respuestas",
                evidence=evidence,
            )

        return DisagreementAssessment(
            level=DisagreementLevel.CONSENSUS,
            reason="Las críticas no señalan contradicciones explícitas entre las respuestas",
            evidence=[],
        )

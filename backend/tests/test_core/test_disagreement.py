from app.core.critic import Critique
from app.core.disagreement import DisagreementDetector, DisagreementLevel
from app.providers.base import LLMResponse


def _critique(provider: str, content: str | None = None, error: str | None = None) -> Critique:
    return Critique(
        response=LLMResponse(provider=provider, model=f"{provider}-model", content=content, error=error),
        reviewed_providers=[],
    )


def test_no_critiques_is_not_applicable():
    assessment = DisagreementDetector().assess([])
    assert assessment.level == DisagreementLevel.NOT_APPLICABLE
    assert assessment.evidence == []


def test_critiques_without_keywords_is_consensus():
    critiques = [
        _critique("openai", "Ambas respuestas son claras y bien fundamentadas."),
        _critique("anthropic", "La otra respuesta cubre el tema de forma completa."),
    ]
    assessment = DisagreementDetector().assess(critiques)
    assert assessment.level == DisagreementLevel.CONSENSUS
    assert assessment.evidence == []


def test_critique_with_keyword_is_disagreement():
    critiques = [
        _critique("openai", "Esta respuesta contradice la evidencia presentada por el otro candidato."),
        _critique("anthropic", "Sin observaciones relevantes."),
    ]
    assessment = DisagreementDetector().assess(critiques)
    assert assessment.level == DisagreementLevel.DISAGREEMENT
    assert len(assessment.evidence) == 1
    assert "contradice" in assessment.evidence[0]


def test_failed_critique_is_not_scanned():
    critiques = [_critique("gemini", content=None, error="timeout")]
    assessment = DisagreementDetector().assess(critiques)
    # There IS a critique list (not empty), so the round did run — but the
    # only entry failed, so there is nothing to scan and no disagreement signal.
    assert assessment.level == DisagreementLevel.CONSENSUS
    assert assessment.evidence == []

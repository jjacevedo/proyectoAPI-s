import pytest

from app.core.calculation_verifier import (
    CalculationVerifier,
    extract_calc_result,
    extract_final_number,
)


def test_extract_calc_result_parses_marker_line():
    stdout = "some noise\n__CALC_RESULT__ 42.5\nmore noise"
    assert extract_calc_result(stdout) == 42.5


def test_extract_calc_result_returns_none_without_marker():
    assert extract_calc_result("no marker here") is None


def test_extract_final_number_returns_last_number_in_prose():
    content = "El tren recorre 80 km en la primera hora y 240 km en total."
    assert extract_final_number(content) == 240.0


def test_extract_final_number_handles_thousands_separator():
    content = "El resultado final es 1,234.56 unidades."
    assert extract_final_number(content) == 1234.56


def test_extract_final_number_returns_none_without_digits():
    assert extract_final_number("no hay ningún número aquí") is None


def test_extract_final_number_returns_none_for_empty_content():
    assert extract_final_number(None) is None
    assert extract_final_number("") is None


@pytest.mark.asyncio
async def test_compute_reference_runs_solver_script_for_real():
    verifier = CalculationVerifier(timeout_seconds=5.0, max_output_chars=2000)
    script = "result = 80 * 3\nprint(f'__CALC_RESULT__ {result}')"
    value, sandbox_result = await verifier.compute_reference(script)
    assert value == 240.0
    assert sandbox_result.succeeded


@pytest.mark.asyncio
async def test_compute_reference_handles_solver_script_timeout():
    verifier = CalculationVerifier(timeout_seconds=1.0, max_output_chars=2000)
    script = "while True:\n    pass\n"
    value, sandbox_result = await verifier.compute_reference(script)
    assert value is None
    assert sandbox_result.timed_out
    assert not sandbox_result.succeeded


def test_verify_candidate_passes_when_value_matches_reference():
    verifier = CalculationVerifier(timeout_seconds=5.0, max_output_chars=2000)
    result = verifier.verify_candidate("openai", "gpt", "El resultado es 240 km.", reference_value=240.0)
    assert result.passed
    assert result.candidate_value == 240.0
    assert result.difference == 0.0


def test_verify_candidate_fails_when_value_differs_from_reference():
    verifier = CalculationVerifier(timeout_seconds=5.0, max_output_chars=2000)
    result = verifier.verify_candidate("anthropic", "claude", "El resultado es 180 km.", reference_value=240.0)
    assert not result.passed
    assert result.candidate_value == 180.0
    assert result.difference == 60.0


def test_verify_candidate_fails_when_no_number_found():
    verifier = CalculationVerifier(timeout_seconds=5.0, max_output_chars=2000)
    result = verifier.verify_candidate("gemini", "flash", "No puedo responder esto.", reference_value=240.0)
    assert not result.passed
    assert result.candidate_value is None
    assert result.error is not None


def test_verify_candidate_respects_relative_tolerance_for_small_rounding_differences():
    verifier = CalculationVerifier(timeout_seconds=5.0, max_output_chars=2000, tolerance=1e-3)
    result = verifier.verify_candidate("openai", "gpt", "El resultado es 240.001 km.", reference_value=240.0)
    assert result.passed

import os
import time

import pytest

from app.core.code_verifier import CodeVerifier, extract_python_code

_PASSING_TESTS = (
    "import unittest\n\n"
    "class TestAdd(unittest.TestCase):\n"
    "    def test_basic(self):\n"
    "        self.assertEqual(add(2, 3), 5)\n"
)


def test_extract_python_code_returns_fenced_block():
    content = "Here is the solution:\n```python\ndef foo():\n    return 1\n```\nDone."
    assert extract_python_code(content) == "def foo():\n    return 1"


def test_extract_python_code_returns_none_without_fenced_block():
    assert extract_python_code("just prose, no code here") is None


def test_extract_python_code_concatenates_multiple_blocks():
    content = "```python\nimport math\n```\nand also\n```python\ndef square(x):\n    return x * x\n```"
    result = extract_python_code(content)
    assert "import math" in result
    assert "def square(x):" in result


@pytest.mark.asyncio
async def test_verify_passes_when_implementation_is_correct():
    verifier = CodeVerifier(timeout_seconds=5.0, max_output_chars=2000)
    candidate = "def add(a, b):\n    return a + b\n"
    result = await verifier.verify(candidate, _PASSING_TESTS)
    assert result.passed
    assert result.tests_run == 1
    assert result.tests_failed == 0
    assert result.error is None


@pytest.mark.asyncio
async def test_verify_fails_when_implementation_is_wrong():
    verifier = CodeVerifier(timeout_seconds=5.0, max_output_chars=2000)
    candidate = "def add(a, b):\n    return a - b\n"
    result = await verifier.verify(candidate, _PASSING_TESTS)
    assert not result.passed
    assert result.tests_run == 1
    assert result.tests_failed == 1


@pytest.mark.asyncio
async def test_verify_times_out_on_infinite_loop():
    verifier = CodeVerifier(timeout_seconds=1.0, max_output_chars=2000)
    candidate = "def add(a, b):\n    while True:\n        pass\n"
    started = time.monotonic()
    result = await verifier.verify(candidate, _PASSING_TESTS)
    elapsed = time.monotonic() - started
    assert result.timed_out
    assert not result.passed
    assert elapsed < 10  # must not hang well beyond the configured timeout


@pytest.mark.asyncio
async def test_verify_handles_syntax_error_without_raising():
    verifier = CodeVerifier(timeout_seconds=5.0, max_output_chars=2000)
    candidate = "def add(a, b)\n    return a + b\n"  # missing colon
    result = await verifier.verify(candidate, _PASSING_TESTS)
    assert not result.passed
    assert result.error is not None


@pytest.mark.asyncio
async def test_verify_does_not_leak_backend_environment_variables():
    verifier = CodeVerifier(timeout_seconds=5.0, max_output_chars=2000)
    os.environ["OPENAI_API_KEY"] = "sk-should-never-be-visible-to-candidate-code"
    try:
        leaking_candidate = (
            "import os\n"
            "def add(a, b):\n"
            "    print('LEAKED:', os.environ.get('OPENAI_API_KEY'))\n"
            "    return a + b\n"
        )
        tests_that_call_add = (
            "import unittest\n\n"
            "class TestAdd(unittest.TestCase):\n"
            "    def test_basic(self):\n"
            "        self.assertEqual(add(2, 3), 5)\n"
        )
        result = await verifier.verify(leaking_candidate, tests_that_call_add)
    finally:
        del os.environ["OPENAI_API_KEY"]

    assert "sk-should-never-be-visible" not in result.stdout
    assert "sk-should-never-be-visible" not in result.stderr

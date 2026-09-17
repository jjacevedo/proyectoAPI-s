import re

from pydantic import BaseModel

from app.core.sandbox_runner import run_sandboxed_script

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
_SUMMARY_RE = re.compile(
    r"__VERIFICATION_SUMMARY__ tests_run=(\d+) failures=(\d+) errors=(\d+)(?: setup_error=(.*))?"
)

_SCRIPT_TEMPLATE = '''\
import sys
import unittest

_MARKER = "__VERIFICATION_SUMMARY__"
_CANDIDATE_SOURCE = {candidate!r}
_TEST_SOURCE = {tests!r}


def _main() -> int:
    namespace: dict = {{}}
    try:
        exec(compile(_CANDIDATE_SOURCE, "<candidate>", "exec"), namespace)
    except Exception as exc:
        print(f"{{_MARKER}} tests_run=0 failures=0 errors=1 setup_error={{exc!r}}")
        return 1
    try:
        exec(compile(_TEST_SOURCE, "<tests>", "exec"), namespace)
    except Exception as exc:
        print(f"{{_MARKER}} tests_run=0 failures=0 errors=1 setup_error={{exc!r}}")
        return 1

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for value in list(namespace.values()):
        if isinstance(value, type) and issubclass(value, unittest.TestCase):
            suite.addTests(loader.loadTestsFromTestCase(value))

    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)
    print(
        f"{{_MARKER}} tests_run={{result.testsRun}} "
        f"failures={{len(result.failures)}} errors={{len(result.errors)}}"
    )
    return 0 if result.wasSuccessful() else 1


sys.exit(_main())
'''


def extract_python_code(content: str | None) -> str | None:
    """Extrae y concatena los bloques de codigo Python (```python ... ```
    o ``` ... ```) de una respuesta en texto libre. None si no hay ninguno.
    """
    if not content:
        return None
    blocks = _CODE_BLOCK_RE.findall(content)
    if not blocks:
        return None
    return "\n\n".join(block.strip() for block in blocks)


class CodeVerification(BaseModel):
    provider: str = ""
    model: str = ""
    passed: bool
    tests_run: int
    tests_passed: int
    tests_failed: int
    stdout: str
    stderr: str
    error: str | None = None
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.error is None and not self.timed_out


class CodeVerifier:
    def __init__(self, timeout_seconds: float, max_output_chars: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def verify(self, candidate_code: str, test_code: str) -> CodeVerification:
        script = _SCRIPT_TEMPLATE.format(candidate=candidate_code, tests=test_code)
        try:
            result = await run_sandboxed_script(
                script, timeout_seconds=self.timeout_seconds, max_output_chars=self.max_output_chars
            )
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

        if result.launch_error is not None:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout="",
                stderr="",
                error=result.launch_error,
            )

        if result.timed_out:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout=result.stdout,
                stderr=result.stderr,
                error="execution timed out",
                timed_out=True,
            )

        match = _SUMMARY_RE.search(result.stdout)
        if not match:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout=result.stdout,
                stderr=result.stderr,
                error="no se pudo determinar el resultado de los tests",
            )

        tests_run, failures, errors = int(match.group(1)), int(match.group(2)), int(match.group(3))
        tests_failed = failures + errors
        return CodeVerification(
            passed=tests_run > 0 and tests_failed == 0,
            tests_run=tests_run,
            tests_passed=tests_run - tests_failed,
            tests_failed=tests_failed,
            stdout=result.stdout,
            stderr=result.stderr,
            error=match.group(4),
        )

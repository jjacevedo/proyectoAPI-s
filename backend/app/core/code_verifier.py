import asyncio
import os
import re
import resource
import sys
import tempfile

from pydantic import BaseModel

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


def _limit_resources(cpu_seconds: int, memory_bytes: int) -> None:
    """Ejecutado en el proceso hijo (via preexec_fn), antes de exec(). Baja
    limites de CPU/memoria/procesos/descriptores. Esto NO es aislamiento a
    nivel de kernel: no bloquea acceso a red ni protege contra un exploit
    del propio interprete. Es un nivel de seguridad razonable para un
    proyecto de un solo usuario, no multi-tenant (ver docs/ARQUITECTURA.md).
    """
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


class CodeVerifier:
    def __init__(self, timeout_seconds: float, max_output_chars: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    async def verify(self, candidate_code: str, test_code: str) -> CodeVerification:
        script = _SCRIPT_TEMPLATE.format(candidate=candidate_code, tests=test_code)
        # RLIMIT_CPU is a backstop, not the primary timeout: give it extra
        # headroom over self.timeout_seconds so our own asyncio.wait_for is
        # normally what kills a hung process, keeping `timed_out` accurate.
        cpu_seconds = max(1, int(self.timeout_seconds)) + 5

        with tempfile.TemporaryDirectory(prefix="codeverify-") as tmpdir:
            script_path = os.path.join(tmpdir, "runner.py")
            with open(script_path, "w") as handle:
                handle.write(script)

            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-I",
                    "-S",
                    script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                    # Deliberadamente NO se hereda el entorno del backend:
                    # las API keys de los providers nunca deben llegar al
                    # codigo que se esta verificando.
                    env={"PATH": "/usr/bin:/bin", "HOME": tmpdir, "TMPDIR": tmpdir},
                    preexec_fn=lambda: _limit_resources(cpu_seconds, 256 * 1024 * 1024),
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

            timed_out = False
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                timed_out = True
                try:
                    proc.kill()
                except ProcessLookupError:
                    # The process may have already exited on its own (e.g. a
                    # resource limit such as RLIMIT_CPU killed it) between
                    # the timeout firing and this call.
                    pass
                stdout_bytes, stderr_bytes = await proc.communicate()

        stdout = stdout_bytes.decode("utf-8", errors="replace")[: self.max_output_chars]
        stderr = stderr_bytes.decode("utf-8", errors="replace")[: self.max_output_chars]

        if timed_out:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout=stdout,
                stderr=stderr,
                error="execution timed out",
                timed_out=True,
            )

        match = _SUMMARY_RE.search(stdout)
        if not match:
            return CodeVerification(
                passed=False,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                stdout=stdout,
                stderr=stderr,
                error="no se pudo determinar el resultado de los tests",
            )

        tests_run, failures, errors = int(match.group(1)), int(match.group(2)), int(match.group(3))
        tests_failed = failures + errors
        return CodeVerification(
            passed=tests_run > 0 and tests_failed == 0,
            tests_run=tests_run,
            tests_passed=tests_run - tests_failed,
            tests_failed=tests_failed,
            stdout=stdout,
            stderr=stderr,
            error=match.group(4),
        )

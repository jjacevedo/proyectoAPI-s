import asyncio
import os
import resource
import sys
import tempfile

from pydantic import BaseModel


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


class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    timed_out: bool = False
    launch_error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.launch_error is None and not self.timed_out


async def run_sandboxed_script(
    script: str, *, timeout_seconds: float, max_output_chars: int
) -> SandboxResult:
    """Ejecuta `script` como un archivo Python independiente en un subprocess
    aislado: timeout de pared + limites de recursos (RLIMIT_CPU/AS/NPROC/
    FSIZE/NOFILE), entorno minimo que NO hereda las variables del backend
    (las API keys de los providers nunca deben llegar al codigo ejecutado),
    y flags -I -S (modo aislado, sin site-packages). Usado tanto por la
    verificacion de codigo (backend/app/core/code_verifier.py) como por el
    motor de calculo (backend/app/core/calculation_verifier.py).
    """
    # RLIMIT_CPU es un respaldo, no el timeout principal: le damos margen
    # extra sobre timeout_seconds para que asyncio.wait_for sea normalmente
    # quien mata un proceso colgado, manteniendo `timed_out` preciso.
    cpu_seconds = max(1, int(timeout_seconds)) + 5

    with tempfile.TemporaryDirectory(prefix="sandbox-") as tmpdir:
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
                env={"PATH": "/usr/bin:/bin", "HOME": tmpdir, "TMPDIR": tmpdir},
                preexec_fn=lambda: _limit_resources(cpu_seconds, 256 * 1024 * 1024),
            )
        except Exception as exc:
            return SandboxResult(stdout="", stderr="", launch_error=f"{type(exc).__name__}: {exc}")

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                # The process may have already exited on its own (e.g. a
                # resource limit such as RLIMIT_CPU killed it) between the
                # timeout firing and this call.
                pass
            stdout_bytes, stderr_bytes = await proc.communicate()

    return SandboxResult(
        stdout=stdout_bytes.decode("utf-8", errors="replace")[:max_output_chars],
        stderr=stderr_bytes.decode("utf-8", errors="replace")[:max_output_chars],
        timed_out=timed_out,
    )

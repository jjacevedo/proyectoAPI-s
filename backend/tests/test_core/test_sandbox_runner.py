import time

import pytest

from app.core.sandbox_runner import run_sandboxed_script


@pytest.mark.asyncio
async def test_run_sandboxed_script_captures_stdout():
    result = await run_sandboxed_script(
        "print('hello from sandbox')", timeout_seconds=5.0, max_output_chars=2000
    )
    assert result.succeeded
    assert "hello from sandbox" in result.stdout


@pytest.mark.asyncio
async def test_run_sandboxed_script_captures_stderr_on_uncaught_exception():
    result = await run_sandboxed_script("raise ValueError('boom')", timeout_seconds=5.0, max_output_chars=2000)
    assert not result.timed_out
    assert result.launch_error is None
    assert "ValueError" in result.stderr


@pytest.mark.asyncio
async def test_run_sandboxed_script_times_out_on_infinite_loop():
    started = time.monotonic()
    result = await run_sandboxed_script(
        "while True:\n    pass\n", timeout_seconds=1.0, max_output_chars=2000
    )
    elapsed = time.monotonic() - started
    assert result.timed_out
    assert not result.succeeded
    assert elapsed < 10


@pytest.mark.asyncio
async def test_run_sandboxed_script_does_not_leak_backend_environment_variables():
    import os

    os.environ["OPENAI_API_KEY"] = "sk-should-never-be-visible-to-sandboxed-code"
    try:
        result = await run_sandboxed_script(
            "import os\nprint('LEAKED:', os.environ.get('OPENAI_API_KEY'))",
            timeout_seconds=5.0,
            max_output_chars=2000,
        )
    finally:
        del os.environ["OPENAI_API_KEY"]

    assert "sk-should-never-be-visible" not in result.stdout
    assert "sk-should-never-be-visible" not in result.stderr

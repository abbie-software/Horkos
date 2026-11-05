import json
import os
import secrets
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

IMAGE = "python:3.12-slim"
HARNESS = Path(__file__).resolve().parent.parent / "sandbox" / "harness.py"

MAX_CODE_CHARS = 50_000  # per file
TAIL_BYTES = 64 * 1024  # how much output is kept; the result line is last
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class SandboxResult:
    """status is passed, failed, timeout or error.

    error means the runner could not reach a verdict (for example Docker is
    not running). It says nothing about the work, so it must never release or
    refund money.
    """

    status: str
    passed: int = 0
    failed: int = 0
    total: int = 0
    duration_ms: int = 0
    output_excerpt: str = ""


def docker_command(name: str, workdir: str, image: str = IMAGE) -> list[str]:
    """The locked-down container the work runs in."""
    return [
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", "none",  # no internet
        "--memory", "256m", "--memory-swap", "256m",  # no swap, so memory is a hard limit
        "--cpus", "1",
        "--pids-limit", "64",  # no fork bombs
        "--read-only",  # the container cannot write to its own files
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",  # nobody
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", f"{workdir}:/work:ro",  # the work and tests are read-only
        "-w", "/work",
        image,
        "python", "-I", "/work/harness.py", "/work",
    ]


def stop_container(name: str) -> None:
    """Killing the docker command does not stop the container, so stop it too."""
    try:
        subprocess.run(
            ["docker", "kill", name],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def parse_result(output: bytes, token: str) -> dict | None:
    """The last line that carries our token, or None."""
    prefix = f"HORKOS-RESULT {token} "
    found = None
    for line in output.decode("utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            try:
                found = json.loads(line[len(prefix):])
            except ValueError:
                found = None
    return found if isinstance(found, dict) else None


def clip(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def classify(result: dict | None, returncode: int | None, tail: bytes) -> SandboxResult:
    if result is None:
        if returncode == 137:  # killed from outside, almost always out of memory
            return SandboxResult(
                status="failed",
                output_excerpt="The code used too much memory and was stopped.",
            )
        shown = clip(tail.decode("utf-8", errors="replace"), 200)
        return SandboxResult(
            status="error",
            output_excerpt=clip(f"The test runner could not finish. {shown}"),
        )

    passed = int(result.get("passed", 0))
    failed = int(result.get("failed", 0))
    total = int(result.get("total", 0))
    duration_ms = int(result.get("duration_ms", 0))
    fatal = str(result.get("fatal") or "")

    if fatal:
        return SandboxResult(
            status="failed",
            duration_ms=duration_ms,
            output_excerpt=clip(f"The work could not be loaded: {fatal}"),
        )
    if total == 0:
        return SandboxResult(
            status="error",
            output_excerpt="No tests were found, so nothing could be checked.",
        )
    if failed == 0 and passed == total:
        return SandboxResult(
            status="passed",
            passed=passed,
            total=total,
            duration_ms=duration_ms,
            output_excerpt=f"{passed} passed in {duration_ms / 1000:.2f}s",
        )
    details = "; ".join(result.get("failures") or [])
    return SandboxResult(
        status="failed",
        passed=passed,
        failed=failed,
        total=total,
        duration_ms=duration_ms,
        output_excerpt=clip(f"{failed} failed, {passed} passed. {details}"),
    )


def run_in_sandbox(
    solution_code: str,
    test_code: str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    image: str = IMAGE,
    build=docker_command,
    stop=stop_container,
) -> SandboxResult:
    """Run the seller's work against the tests in a locked-down container.

    Anything unexpected becomes a SandboxResult. This function does not raise
    for problems with the work or with Docker.
    """
    if len(solution_code) > MAX_CODE_CHARS or len(test_code) > MAX_CODE_CHARS:
        return SandboxResult(
            status="failed", output_excerpt="The submitted code is too large."
        )

    token = secrets.token_hex(16)
    name = f"horkos-run-{secrets.token_hex(6)}"
    tail = bytearray()
    lock = threading.Lock()

    def read_output(stream) -> None:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            with lock:
                tail.extend(chunk)
                if len(tail) > TAIL_BYTES:
                    del tail[: len(tail) - TAIL_BYTES]

    with tempfile.TemporaryDirectory(prefix="horkos-") as tmp:
        workdir = Path(tmp)
        os.chmod(workdir, 0o755)  # the container user is "nobody"
        files = {
            "solution.py": solution_code,
            "test_solution.py": test_code,
            "harness.py": HARNESS.read_text(),
        }
        for filename, content in files.items():
            path = workdir / filename
            path.write_text(content)
            os.chmod(path, 0o644)

        started = time.perf_counter()
        try:
            process = subprocess.Popen(
                build(name, str(workdir), image),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except OSError:
            return SandboxResult(
                status="error",
                output_excerpt="Docker is not installed or could not be started.",
            )

        reader = threading.Thread(target=read_output, args=(process.stdout,), daemon=True)
        reader.start()
        try:
            process.stdin.write((token + "\n").encode())
            process.stdin.close()
        except OSError:
            pass  # the container may already have stopped; the result will say so

        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            stop(name)
            process.kill()
            process.wait()
            reader.join(timeout=2)
            return SandboxResult(
                status="timeout",
                duration_ms=int((time.perf_counter() - started) * 1000),
                output_excerpt=(
                    f"The code ran for longer than {timeout_seconds:g} seconds "
                    "and was stopped."
                ),
            )

        reader.join(timeout=2)
        with lock:
            output = bytes(tail)
        return classify(parse_result(output, token), process.returncode, output)
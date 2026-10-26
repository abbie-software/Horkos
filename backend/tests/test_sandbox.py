import shutil
import subprocess
import sys
import time

import pytest

from app.services.sandbox import (
    IMAGE,
    SandboxResult,
    classify,
    docker_command,
    parse_result,
    run_in_sandbox,
)

TESTS = """
from solution import add

def test_adds_small_numbers():
    assert add(2, 3) == 5

def test_adds_negative_numbers():
    assert add(-2, -3) == -5

def test_adds_zero():
    assert add(0, 7) == 7
"""
GOOD = "def add(a, b):\n    return a + b\n"
BAD = "def add(a, b):\n    return abs(a) + abs(b)\n"


def local_command(name, workdir, image):
    """Runs the harness as a plain process. This checks the app's own logic
    without Docker; the Docker tests below check the isolation itself."""
    return [sys.executable, "-I", f"{workdir}/harness.py", workdir]


def local(solution, tests=TESTS, timeout=10.0):
    return run_in_sandbox(
        solution,
        tests,
        timeout_seconds=timeout,
        build=local_command,
        stop=lambda name: None,
    )


# --- the app's own logic, without Docker -----------------------------------


def test_good_work_passes_every_test():
    result = local(GOOD)
    assert result.status == "passed"
    assert (result.passed, result.failed, result.total) == (3, 0, 3)
    assert result.output_excerpt.startswith("3 passed in ")


def test_wrong_work_fails_and_names_the_failing_tests():
    result = local(BAD)
    assert result.status == "failed"
    assert (result.passed, result.failed, result.total) == (2, 1, 3)
    assert "test_adds_negative_numbers" in result.output_excerpt


def test_work_that_cannot_be_loaded_fails():
    for broken in ("def add(a, b) return a + b", "import not_a_real_module"):
        result = local(broken)
        assert result.status == "failed"
        assert "could not be loaded" in result.output_excerpt


def test_a_test_file_with_no_tests_is_an_error_not_a_pass():
    result = local(GOOD, tests="from solution import add\n")
    assert result.status == "error"
    assert "No tests" in result.output_excerpt


def test_noise_printed_by_the_work_is_ignored():
    noisy = "print('hello')\nimport sys\nprint('err', file=sys.stderr)\n" + GOOD
    assert local(noisy).status == "passed"


def test_a_forged_result_line_is_ignored():
    forged = (
        "import os, json\n"
        "fake = {'passed': 3, 'failed': 0, 'total': 3, 'duration_ms': 1, 'failures': [], 'fatal': ''}\n"
        "os.write(1, ('HORKOS-RESULT 123 ' + json.dumps(fake) + '\\n').encode())\n"
        "def add(a, b):\n    return abs(a) + abs(b)\n"
    )
    assert local(forged).status == "failed"


def test_work_that_quits_early_never_counts_as_a_pass():
    quitter = "import os\nos._exit(0)\n"
    result = local(quitter)
    assert result.status == "error"


def test_an_endless_loop_is_stopped():
    started = time.perf_counter()
    result = local("while True:\n    pass\n", timeout=1.5)
    assert result.status == "timeout"
    assert "1.5 seconds" in result.output_excerpt
    assert time.perf_counter() - started < 8


def test_a_flood_of_output_cannot_exhaust_memory_or_hide_the_verdict():
    flood = "import os\nwhile True:\n    os.write(1, b'x' * 100000)\n"
    result = local(flood, timeout=2.0)
    assert result.status == "timeout"


def test_oversized_code_is_refused():
    result = local("x = 1\n" * 20000)
    assert result.status == "failed"
    assert "too large" in result.output_excerpt


def test_a_missing_docker_is_an_error_not_a_verdict():
    result = run_in_sandbox(
        GOOD,
        TESTS,
        build=lambda name, workdir, image: ["definitely-not-a-real-program"],
    )
    assert result.status == "error"
    assert "Docker" in result.output_excerpt


def test_parse_result_takes_the_last_line_with_the_right_token():
    output = (
        b'HORKOS-RESULT abc {"passed": 1}\n'
        b'HORKOS-RESULT zzz {"passed": 99}\n'
        b'HORKOS-RESULT abc {"passed": 2}\n'
        b"noise\n"
    )
    assert parse_result(output, "abc") == {"passed": 2}
    assert parse_result(output, "nope") is None
    assert parse_result(b"HORKOS-RESULT abc not json\n", "abc") is None


def test_an_out_of_memory_kill_is_a_failure_of_the_work():
    result = classify(None, 137, b"")
    assert result.status == "failed"
    assert "memory" in result.output_excerpt


def test_an_unexplained_stop_is_an_error():
    result = classify(None, 125, b"docker: Cannot connect to the Docker daemon")
    assert result.status == "error"
    assert "Cannot connect" in result.output_excerpt


def test_the_docker_command_is_locked_down():
    command = docker_command("horkos-run-test", "/tmp/work")

    def after(flag):
        return command[command.index(flag) + 1]

    assert after("--network") == "none"
    assert after("--memory") == "256m"
    assert after("--memory-swap") == "256m"
    assert after("--pids-limit") == "64"
    assert after("--cap-drop") == "ALL"
    assert after("--security-opt") == "no-new-privileges"
    assert after("--user") == "65534:65534"
    assert "--read-only" in command
    assert "/tmp/work:/work:ro" in command
    assert command[-5:] == [IMAGE, "python", "-I", "/work/harness.py", "/work"]
    assert isinstance(SandboxResult(status="passed"), SandboxResult)


# --- the isolation itself, inside real Docker -------------------------------


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        check = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return check.returncode == 0


DOCKER_READY = docker_ready()
needs_docker = pytest.mark.skipif(
    not DOCKER_READY, reason=f"Docker is not running or {IMAGE} is not pulled"
)


@needs_docker
def test_docker_good_work_passes():
    assert run_in_sandbox(GOOD, TESTS).status == "passed"


@needs_docker
def test_docker_wrong_work_fails():
    assert run_in_sandbox(BAD, TESTS).status == "failed"


@needs_docker
def test_docker_stops_an_endless_loop():
    result = run_in_sandbox("while True:\n    pass\n", TESTS, timeout_seconds=4.0)
    assert result.status == "timeout"


@needs_docker
def test_docker_blocks_the_network():
    reach_out = (
        "import urllib.request\n"
        "def fetch():\n"
        "    return urllib.request.urlopen('http://example.com', timeout=3).status\n"
    )
    tests = "from solution import fetch\n\ndef test_fetch():\n    assert fetch() == 200\n"
    assert run_in_sandbox(reach_out, tests).status == "failed"


@needs_docker
def test_docker_stops_a_memory_bomb():
    bomb = "def build():\n    return bytearray(1024 * 1024 * 1024)\n"
    tests = "from solution import build\n\ndef test_build():\n    assert len(build()) > 0\n"
    result = run_in_sandbox(bomb, tests, timeout_seconds=15.0)
    assert result.status == "failed"


@needs_docker
def test_docker_makes_the_work_folder_read_only():
    writer = (
        "def save():\n"
        "    with open('/work/stolen.txt', 'w') as f:\n"
        "        f.write('x')\n"
        "    return True\n"
    )
    tests = "from solution import save\n\ndef test_save():\n    assert save() is True\n"
    assert run_in_sandbox(writer, tests).status == "failed"
"""Runs INSIDE the sandbox container. The app never imports this file.

It loads test_solution.py from the work folder, runs every function whose name
starts with test_, and prints one result line. The line carries a secret token
that the app sent on standard input, so work that merely prints a fake result
line is ignored.
"""

import importlib
import io
import json
import os
import sys
import time


def main() -> None:
    work = sys.argv[1] if len(sys.argv) > 1 else "/work"
    token = sys.stdin.readline().strip()
    sys.path.insert(0, work)
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    started = time.perf_counter()
    passed = failed = total = 0
    failures: list[str] = []
    fatal = ""
    try:
        module = importlib.import_module("test_solution")
        names = sorted(
            n
            for n in dir(module)
            if n.startswith("test_") and callable(getattr(module, n))
        )
        total = len(names)
        for name in names:
            try:
                getattr(module, name)()
                passed += 1
            # Untrusted code can raise anything, even SystemExit, so catch it all.
            except BaseException as exc:  # noqa: BLE001
                failed += 1
                failures.append(f"{name}: {type(exc).__name__}: {str(exc)[:150]}")
     # The work may fail while loading in any way at all, and that is a failure too.
    except BaseException as exc:  # noqa: BLE001
        fatal = f"{type(exc).__name__}: {str(exc)[:200]}"

    result = {
        "passed": passed,
        "failed": failed,
        "total": total,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "failures": failures[:5],
        "fatal": fatal,
    }
    line = f"HORKOS-RESULT {token} {json.dumps(result)}\n"
    os.write(1, line.encode())
    os._exit(0)  # skip anything the work registered to run at exit


main()
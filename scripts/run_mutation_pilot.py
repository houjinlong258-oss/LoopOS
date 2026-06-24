"""Run the v0.3 mutation testing pilot.

This is a small wrapper around ``mutmut`` that:

1. Hard-codes the venv Python interpreter so mutmut does not
   try to resolve ``python`` against the system PATH (the
   ``shlex.split`` Windows bug in mutmut 2.x mangles absolute
   paths).
2. Restricts the mutation scope to four high-risk modules
   per the P1-5 hardening task: ``budget.py``, ``openai.py``,
   ``agent_bus/bus.py``, ``fusion_router/orchestrator.py``.
3. Restricts the test runner to the test files that exercise
   those modules, so the timing-flaky
   ``test_deep_smoke_global_timeout_names_running_check``
   cannot poison the baseline run.

Usage:

    python scripts/run_mutation_pilot.py <module_path>

Where ``<module_path>`` is one of:

* ``loopos/providers_runtime/budget.py``
* ``loopos/providers_runtime/openai.py``
* ``loopos/agent_bus/bus.py``
* ``loopos/fusion_router/orchestrator.py``

The script returns the mutmut exit code. The mutation report
is captured to ``.mutmut-cache/`` and the human-readable
summary is in ``docs/reports/v0-3-mutation-pilot.md``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


# (module_path, test_argv). The test_argv is the list of pytest
# arguments to use as the runner. We pin to the test files that
# actually exercise the module under mutation so a flaky test
# elsewhere in the suite cannot poison the baseline.
PILOT_TARGETS: dict[str, list[str]] = {
    "loopos/providers_runtime/budget.py": [
        "tests/test_budget_ledger.py",
        "tests/test_providers_runtime.py",
        "tests/test_product.py",
        "tests/test_v0_3_cli.py",
    ],
    "loopos/providers_runtime/openai.py": [
        "tests/test_providers_runtime.py",
        "tests/test_v0_3_live_provider_smoke_http.py",
        "tests/test_v0_3_cli.py",
    ],
    "loopos/agent_bus/bus.py": [
        "tests/test_agent_bus.py",
        "tests/test_adapters_v0_3.py",
    ],
    "loopos/fusion_router/orchestrator.py": [
        "tests/test_fusion_orchestrator.py",
    ],
}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: run_mutation_pilot.py <module_path>")
        return 2
    target = argv[1]
    if target not in PILOT_TARGETS:
        print(
            f"unknown target: {target!r}. Allowed: "
            f"{sorted(PILOT_TARGETS.keys())}"
        )
        return 2

    # Reset cache so the baseline always re-runs. Each module
    # gets its own cache file so the per-module results can be
    # inspected independently after the run. mutmut 2.x writes
    # the cache to ``.mutmut-cache`` in the working directory;
    # we let it do that, then move the file to a per-module
    # location after the run completes.
    import re as _re

    safe_name = _re.sub(r"[^A-Za-z0-9]+", "_", target)
    per_module_cache = REPO_ROOT / f".mutmut-cache.{safe_name}"
    if per_module_cache.exists() or per_module_cache.is_symlink():
        if per_module_cache.is_symlink() or per_module_cache.is_file():
            per_module_cache.unlink()
        else:
            import shutil

            shutil.rmtree(per_module_cache, ignore_errors=True)
    cache_path = REPO_ROOT / ".mutmut-cache"
    if cache_path.exists() or cache_path.is_symlink():
        if cache_path.is_symlink() or cache_path.is_file():
            cache_path.unlink()
        else:
            import shutil

            shutil.rmtree(cache_path, ignore_errors=True)

    test_argv = PILOT_TARGETS[target]
    test_command = (
        f'"{VENV_PYTHON}" -m pytest -x -q ' + " ".join(test_argv)
    )

    cmd = [
        str(VENV_PYTHON),
        "-m",
        "mutmut",
        "run",
        "--paths-to-mutate",
        target,
        "--tests-dir",
        "tests",
        "--runner",
        test_command,
        "--no-backup",
        "--simple-output",
        "--no-progress",
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    # Move the per-run cache to a stable, per-module location so
    # the report can read it without colliding with the next
    # run. Rename so the on-disk file moves instead of being
    # copied or symlinked.
    if cache_path.exists():
        cache_path.rename(per_module_cache)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
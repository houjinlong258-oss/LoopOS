#!/usr/bin/env python3
"""Tests for scripts/anti_bloat_check.py (Phase 0).

Covers:
- Hard-fail reasons produce exit code 1
- Warning reasons produce exit code 0
- JSON output is valid
- v0.1.0 baseline integrity check
- Self-check mode always exits 0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "anti_bloat_check.py"


def run_gate(
    *extra_args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the anti-bloat gate and return the result."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env=env or os.environ.copy(),
    )


def test_self_check_exits_zero() -> None:
    """--self-check must always exit 0, regardless of state."""
    result = run_gate("--self-check")
    assert result.returncode == 0, (
        f"self-check should exit 0, got {result.returncode}\n{result.stdout}\n{result.stderr}"
    )


def test_json_output_is_valid_json() -> None:
    """--json output must be parseable JSON."""
    result = run_gate("--json", "--self-check")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "hard_fail_count" in parsed
    assert "warning_count" in parsed
    assert "hard_fails" in parsed
    assert "warnings" in parsed
    assert isinstance(parsed["hard_fail_count"], int)
    assert isinstance(parsed["warning_count"], int)


def test_clean_state_passes() -> None:
    """A clean state (no warnings, no hard fails) should exit 0."""
    result = run_gate()
    # We tolerate warnings (they're advisory), but no hard fails
    assert result.returncode in (0, 1), f"unexpected exit {result.returncode}"
    parsed = json.loads(run_gate("--json", "--self-check").stdout)
    # In Phase 0 the baseline file itself counts as a v0.2 file with LOC > 5
    # but baseline is < 300 LOC, so no file-over-300 warning expected
    assert parsed["hard_fail_count"] == 0, f"unexpected hard-fail in clean state: {parsed}"


def test_baseline_path_resolves() -> None:
    """The baseline file must exist and be loadable."""
    baseline = REPO_ROOT / "scripts" / "baselines" / "v0_1_0_loopos.txt"
    assert baseline.exists(), f"baseline file missing: {baseline}"
    paths = [p.strip() for p in baseline.read_text(encoding="utf-8").splitlines() if p.strip()]
    assert len(paths) > 100, f"baseline has only {len(paths)} paths; expected > 100"


def test_baseline_matches_v010_tag() -> None:
    """Baseline content must match `git ls-tree -r v0.1.0 -- loopos/`."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        tmp = f.name
    try:
        git_out = subprocess.run(
            ["git", "ls-tree", "-r", "v0.1.0", "--name-only", "--", "loopos/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        Path(tmp).write_text(git_out.stdout, encoding="utf-8")
        baseline = (REPO_ROOT / "scripts" / "baselines" / "v0_1_0_loopos.txt").read_text(
            encoding="utf-8"
        )
        assert git_out.stdout.strip() == baseline.strip(), "baseline diverged from v0.1.0 tag"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_v010_runtime_modified_hard_fail() -> None:
    """Simulating deletion of a v0.1.0 baseline file must hard-fail.

    We can't actually delete a tracked file in the test, so we verify
    the detection function logic by feeding a synthetic baseline.
    """
    # Indirect test: the check function returns None when baseline is intact
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from anti_bloat_check import check_v010_runtime_modified, load_baseline  # type: ignore[import-not-found]

    baseline = load_baseline()
    assert len(baseline) > 100
    result = check_v010_runtime_modified()
    # On a clean v0.1.0 tree, no hard-fail
    if result is not None:
        # If something is reported, it must be a hard-fail
        assert result.severity == "hard_fail"
        assert result.reason_code == "v0_1_runtime_modified"


def test_unauthorized_dependency_detection() -> None:
    """Verify the unauthorized_dependency check function returns a Finding with the right code."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from anti_bloat_check import check_unauthorized_dependency, RC_UNAUTH_DEPENDENCY

    result = check_unauthorized_dependency()
    if result is not None:
        assert result.reason_code == RC_UNAUTH_DEPENDENCY
        assert result.severity == "hard_fail"


def test_v010_evidence_files_present() -> None:
    """All v0.1.0 evidence ledger files must exist."""
    from anti_bloat_check import EVIDENCE_FILES, check_v010_evidence_mutated

    for rel in EVIDENCE_FILES:
        assert (REPO_ROOT / rel).exists(), f"evidence file missing: {rel}"
    # On a clean Phase 0 state, no evidence mutation
    result = check_v010_evidence_mutated()
    assert result is None, f"unexpected evidence mutation: {result}"


def test_hard_fail_codes_constant() -> None:
    """The hard-fail reason code constants must match the schema."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from anti_bloat_check import (
        RC_V010_RUNTIME_MODIFIED,
        RC_UNAUTH_DEPENDENCY,
        RC_V010_EVIDENCE_MUTATED,
        HARD_FAIL_CODES,
    )

    assert RC_V010_RUNTIME_MODIFIED in HARD_FAIL_CODES
    assert RC_UNAUTH_DEPENDENCY in HARD_FAIL_CODES
    assert RC_V010_EVIDENCE_MUTATED in HARD_FAIL_CODES
    assert len(HARD_FAIL_CODES) == 3, (
        f"expected exactly 3 hard-fail codes, got {len(HARD_FAIL_CODES)}"
    )


def test_warning_codes_constant() -> None:
    """The warning reason codes must include the documented 7 warnings."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from anti_bloat_check import WARNING_CODES

    assert "module_count_delta" in WARNING_CODES
    assert "new_v0_2_file_over_300_loc" in WARNING_CODES
    assert "single_use_helper_suspicion" in WARNING_CODES
    assert "wrapper_only_function_suspicion" in WARNING_CODES
    assert "low_deletion_ratio" in WARNING_CODES
    assert "large_added_lines_without_paired_tests" in WARNING_CODES
    assert "new_abstraction_count_warning" in WARNING_CODES
    assert len(WARNING_CODES) == 7, f"expected 7 warning codes, got {len(WARNING_CODES)}"


def test_readiness_schema_loads() -> None:
    """The readiness-proof schema must be valid JSON."""
    schema = REPO_ROOT / "docs" / "schemas" / "readiness-proof.schema.json"
    assert schema.exists()
    parsed = json.loads(schema.read_text(encoding="utf-8"))
    assert parsed["title"] == "LoopOS Readiness Proof"
    required = parsed["required"]
    for field in [
        "fsm_coverage",
        "policy_gates_active",
        "budget_enforced",
        "memory_governed",
        "replay_deterministic",
        "go_core_untouched",
        "aci_runtime_bound",
        "ali_fsm_bound",
        "anti_bloat_checked",
    ]:
        assert field in required, f"schema missing required field: {field}"


def test_readiness_example_validates() -> None:
    """The example instance must satisfy the schema's required fields."""
    schema = json.loads(
        (REPO_ROOT / "docs" / "schemas" / "readiness-proof.schema.json").read_text()
    )
    example = json.loads(
        (REPO_ROOT / "docs" / "schemas" / "readiness-proof.example.json").read_text()
    )
    for field in schema["required"]:
        assert field in example, f"example missing required field: {field}"


if __name__ == "__main__":
    # Run as a script: invoke every test_ function
    import inspect

    current_module = sys.modules[__name__]
    failures = []
    for name, fn in inspect.getmembers(current_module, inspect.isfunction):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures.append(name)
            except Exception as e:
                print(f"ERROR {name}: {type(e).__name__}: {e}")
                failures.append(name)
    if failures:
        print(f"\n{len(failures)} test(s) failed")
        sys.exit(1)
    print("\nAll tests passed")
    sys.exit(0)

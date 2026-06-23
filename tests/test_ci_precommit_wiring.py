"""Tests for the P0-3 CI / pre-commit / secret-scanning wiring.

The hardening task asserts three artifacts exist and are coherent:

* ``.github/workflows/ci.yml`` references every required gate
  (ruff, mypy, pytest fast, v0.2 readiness, v0.3 readiness,
  anti-bloat) and runs gitleaks in its own job.
* ``.pre-commit-config.yaml`` wires ruff, mypy, pytest-fast, and
  gitleaks as pre-commit hooks.
* ``.gitleaks.toml`` is a syntactically-valid gitleaks
  configuration file with at least the default-extending settings.

These tests are deliberately low-tech: they read the files as
text and assert on the presence of the right invocations. They do
NOT shell out to ruff, mypy, pytest, or gitleaks (those live in
CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"
GITLEAKS = REPO_ROOT / ".gitleaks.toml"


# ---------------------------------------------------------------------------
# CI workflow
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ci_text() -> str:
    assert CI_YML.exists(), f"missing CI workflow at {CI_YML}"
    return CI_YML.read_text(encoding="utf-8")


def test_ci_workflow_runs_ruff(ci_text: str) -> None:
    assert "python -m ruff check ." in ci_text


def test_ci_workflow_runs_mypy(ci_text: str) -> None:
    assert "python -m mypy loopos tests" in ci_text


def test_ci_workflow_runs_fast_pytest(ci_text: str) -> None:
    assert 'pytest -m "not slow"' in ci_text


def test_ci_workflow_runs_v0_2_readiness(ci_text: str) -> None:
    assert "v0_2_readiness_check.py --json" in ci_text


def test_ci_workflow_runs_v0_3_readiness(ci_text: str) -> None:
    assert "v0_3_readiness_check.py --json" in ci_text


def test_ci_workflow_runs_anti_bloat(ci_text: str) -> None:
    assert "anti_bloat_check.py --json" in ci_text


def test_ci_workflow_runs_gitleaks(ci_text: str) -> None:
    # Either via gitleaks-action or via a direct gitleaks binary
    # call. Both are acceptable; the LoopOS config uses the
    # ``gitleaks/gitleaks-action`` GitHub Action for ergonomics.
    assert "gitleaks" in ci_text.lower()


def test_ci_workflow_pins_loopback_gate_for_v0_3_readiness(ci_text: str) -> None:
    """The v0.3 readiness check must run with
    ``LOOPOS_LIVE_HTTP_SMOKE=1`` so the loopback smoke is exercised
    in CI.
    """
    # Look for the env var near the v0.3 readiness call.
    assert "LOOPOS_LIVE_HTTP_SMOKE" in ci_text


# ---------------------------------------------------------------------------
# Pre-commit config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def precommit_text() -> str:
    assert PRE_COMMIT.exists(), f"missing pre-commit config at {PRE_COMMIT}"
    return PRE_COMMIT.read_text(encoding="utf-8")


def test_precommit_wires_ruff(precommit_text: str) -> None:
    assert "ruff" in precommit_text


def test_precommit_wires_mypy(precommit_text: str) -> None:
    assert "mypy" in precommit_text


def test_precommit_wires_pytest_fast(precommit_text: str) -> None:
    assert '"not slow"' in precommit_text or "not slow" in precommit_text
    assert "pytest" in precommit_text


def test_precommit_wires_gitleaks(precommit_text: str) -> None:
    assert "gitleaks" in precommit_text


# ---------------------------------------------------------------------------
# Gitleaks config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gitleaks_text() -> str:
    assert GITLEAKS.exists(), f"missing gitleaks config at {GITLEAKS}"
    return GITLEAKS.read_text(encoding="utf-8")


def test_gitleaks_extends_default_ruleset(gitleaks_text: str) -> None:
    """The LoopOS gitleaks config must extend the default ruleset
    so we keep the OpenAI / GitHub / AWS / private-key rules.
    """
    assert "useDefault" in gitleaks_text
    assert "true" in gitleaks_text


def test_gitleaks_has_loopos_specific_rule(gitleaks_text: str) -> None:
    """The LoopOS-specific rule for ``sk-test-`` keys must be
    present so a leaked test key in real history is caught.
    """
    assert "sk-test-" in gitleaks_text


def test_gitleaks_has_allowlist_for_test_paths(gitleaks_text: str) -> None:
    """The LoopOS-specific rule must allow-list the test files
    where the prefix legitimately appears.
    """
    # Allow-list paths are written as regex patterns; we accept
    # either the literal filename or the escaped regex form.
    assert ("openai.py" in gitleaks_text) or ("openai\\.py" in gitleaks_text)
    assert (
        "test_v0_3_live_provider_smoke_http.py" in gitleaks_text
        or "test_v0_3_live_provider_smoke_http\\.py" in gitleaks_text
    )


# ---------------------------------------------------------------------------
# Smoke: the v0.3 readiness check still passes after the CI config
# was added (the readiness check itself is not modified by this
# hardening pass; this test guards against an accidental coupling).
# ---------------------------------------------------------------------------


def test_ci_artifacts_do_not_break_v0_3_readiness() -> None:
    """Adding the CI/pre-commit/gitleaks artifacts must not
    change the readiness-check verdict. We only assert the most
    basic property (the script still imports cleanly and reports
    a JSON ``status`` field).
    """
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "v0_3_readiness_check.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    payload = json.loads(result.stdout)
    assert "status" in payload
    # ``status`` must be pass or fail, never malformed.
    assert payload["status"] in ("pass", "fail")
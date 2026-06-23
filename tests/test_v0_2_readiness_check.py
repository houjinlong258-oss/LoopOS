"""Tests for ``scripts/v0_2_readiness_check.py``.

The tests load the readiness script as a module via importlib
(it lives outside the ``loopos`` package), drive it with the
``--self-check`` mode, and assert the structured payload has
the required shape, content, and pass status.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "v0_2_readiness_check.py"


def _load_module() -> Any:
    """Import the readiness-check script as ``v0_2_readiness_check``."""

    spec = importlib.util.spec_from_file_location(
        "v0_2_readiness_check", str(SCRIPT_PATH),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load readiness-check spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


# Required check names per the master prompt.
REQUIRED_CHECKS: tuple[str, ...] = (
    "provider_registry_bound",
    "aci_runtime_bound",
    "ali_fsm_bound",
    "kernel_loop_integrated",
    "trace_bridge_active",
    "ali_replay_deterministic",
    "fusion_router_available",
    "mad_dog_cli_available",
    "fusion_plan_persistence_available",
    "policy_gates_active",
    "dry_run_no_side_effects",
    "no_live_provider_calls",
    "no_kernel_mutation_in_phase",
    "no_model_kernel_mutation",
    "anti_bloat_checked",
)


class ReadinessCheckShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_module()

    def test_required_top_level_fields(self) -> None:
        payload = self.module.run_checks()
        self.assertEqual(payload["schema_version"], "0.2")
        self.assertIn("status", payload)
        self.assertIn("checks", payload)
        self.assertIn("hard_fail_count", payload)
        self.assertIn("warnings", payload)
        self.assertIn(payload["status"], ("pass", "fail"))

    def test_all_required_checks_present(self) -> None:
        payload = self.module.run_checks()
        checks = payload["checks"]
        for name in REQUIRED_CHECKS:
            self.assertIn(name, checks, f"missing required check: {name}")
            self.assertIn("status", checks[name])
            self.assertIn("detail", checks[name])
            self.assertIsInstance(checks[name]["status"], bool)

    def test_hard_fail_count_matches_failed_hard_checks(self) -> None:
        payload = self.module.run_checks()
        hard_fails = [
            name for name, c in payload["checks"].items()
            if not c["status"] and c.get("severity") == "hard"
        ]
        self.assertEqual(payload["hard_fail_count"], len(hard_fails))

    def test_payload_status_pass_on_clean_repo(self) -> None:
        payload = self.module.run_checks()
        self.assertEqual(
            payload["status"], "pass",
            f"readiness check must pass on a clean Phase 8 repo; "
            f"hard_fail_count={payload['hard_fail_count']}, "
            f"failing checks="
            f"{[n for n, c in payload['checks'].items() if not c['status']]}",
        )


class ReadinessCheckEntryPointTests(unittest.TestCase):
    def test_script_emits_json_to_stdout(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(
            completed.returncode, (0, 1),
            f"unexpected exit code {completed.returncode}: stderr={completed.stderr}",
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                f"stdout is not JSON: {exc}\nstdout: {completed.stdout[:500]}"
            )
        self.assertEqual(payload["schema_version"], "0.2")
        self.assertIn(payload["status"], ("pass", "fail"))
        self.assertIn("checks", payload)

    def test_self_check_exits_zero_even_when_check_fails(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--self-check"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0,
            f"--self-check must exit 0; got {completed.returncode}: "
            f"{completed.stderr}",
        )


class ReadinessCheckSafetyTests(unittest.TestCase):
    """The script must not introduce forbidden imports / live calls."""

    def test_script_source_has_no_live_provider_imports(self) -> None:
        # The script is allowed to invoke ``subprocess.run`` (it
        # is documented as the only side-effecting boundary), but
        # it must not import ``requests``, ``httpx``, or
        # ``urllib.request``.
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        for forbidden in ("import requests", "import httpx", "import urllib3"):
            self.assertNotIn(
                forbidden, text,
                f"readiness check script must not import {forbidden}",
            )


class ReadinessCheckLiveProbeTests(unittest.TestCase):
    """Concrete probes against the repo state."""

    def setUp(self) -> None:
        self.module = _load_module()

    def test_provider_registry_bound_pass(self) -> None:
        finding = self.module.check_provider_registry_bound()
        self.assertTrue(finding.status, finding.detail)

    def test_kernel_loop_integrated_pass(self) -> None:
        finding = self.module.check_kernel_loop_integrated()
        self.assertTrue(finding.status, finding.detail)

    def test_ali_replay_deterministic_pass(self) -> None:
        finding = self.module.check_ali_replay_deterministic()
        self.assertTrue(finding.status, finding.detail)

    def test_fusion_router_available_pass(self) -> None:
        finding = self.module.check_fusion_router_available()
        self.assertTrue(finding.status, finding.detail)

    def test_fusion_plan_persistence_pass(self) -> None:
        finding = self.module.check_fusion_plan_persistence_available()
        self.assertTrue(finding.status, finding.detail)

    def test_policy_gates_active_pass(self) -> None:
        finding = self.module.check_policy_gates_active()
        self.assertTrue(finding.status, finding.detail)

    def test_dry_run_no_side_effects_pass(self) -> None:
        finding = self.module.check_dry_run_no_side_effects()
        self.assertTrue(finding.status, finding.detail)

    def test_no_live_provider_calls_pass(self) -> None:
        finding = self.module.check_no_live_provider_calls()
        self.assertTrue(finding.status, finding.detail)

    def test_no_kernel_mutation_in_phase_pass(self) -> None:
        finding = self.module.check_no_kernel_mutation_in_phase()
        self.assertTrue(finding.status, finding.detail)

    def test_no_model_kernel_mutation_pass(self) -> None:
        finding = self.module.check_no_model_kernel_mutation()
        self.assertTrue(finding.status, finding.detail)

    def test_anti_bloat_checked_pass(self) -> None:
        finding = self.module.check_anti_bloat()
        self.assertTrue(finding.status, finding.detail)


class ReadinessCheckArchiveModeTests(unittest.TestCase):
    """Behaviour when running from an extracted source archive."""

    def setUp(self) -> None:
        self.module = _load_module()

    def test_archive_mode_payload_reports_archive(self) -> None:
        payload = self.module.run_checks(archive_mode=True)
        failing = [n for n, c in payload["checks"].items() if not c["status"]]
        self.assertEqual(payload["mode"], "archive")
        self.assertEqual(payload["status"], "pass",
                         f"archive-mode must pass on a clean repo; "
                         f"hard_fail_count={payload['hard_fail_count']}, "
                         f"failing={failing}")

    def test_archive_mode_skips_git_required_checks(self) -> None:
        payload = self.module.run_checks(archive_mode=True)
        checks = payload["checks"]
        for git_only in (
            "no_kernel_mutation_in_phase",
            "no_model_kernel_mutation",
            "anti_bloat_checked",
            "release_evidence_untouched",
        ):
            self.assertIn(git_only, checks, f"{git_only} missing from payload")
            self.assertTrue(checks[git_only]["status"],
                            f"{git_only} must be skipped (status=True) "
                            f"in archive-mode")
            self.assertEqual(
                checks[git_only]["severity"], "warning",
                f"{git_only} must be severity=warning in archive-mode",
            )
            self.assertIn(
                "archive-mode", checks[git_only]["detail"],
                f"{git_only} detail must mention 'archive-mode'",
            )

    def test_archive_mode_still_runs_code_checks(self) -> None:
        payload = self.module.run_checks(archive_mode=True)
        checks = payload["checks"]
        for code_check in (
            "provider_registry_bound",
            "aci_runtime_bound",
            "ali_fsm_bound",
            "kernel_loop_integrated",
            "trace_bridge_active",
            "ali_replay_deterministic",
            "fusion_router_available",
            "mad_dog_cli_available",
            "fusion_plan_persistence_available",
            "policy_gates_active",
            "dry_run_no_side_effects",
            "no_live_provider_calls",
        ):
            self.assertIn(code_check, checks)
            self.assertEqual(
                checks[code_check]["severity"], "hard",
                f"{code_check} must remain hard in archive-mode",
            )
            self.assertTrue(
                checks[code_check]["status"],
                f"{code_check} must pass in archive-mode: "
                f"{checks[code_check]['detail']}",
            )

    def test_git_checkout_mode_payload_reports_git_checkout(self) -> None:
        payload = self.module.run_checks(archive_mode=False)
        self.assertEqual(payload["mode"], "git-checkout")

    def test_is_git_repo_matches_filesystem(self) -> None:
        self.assertTrue(
            self.module._is_git_repo(),
            "_is_git_repo must return True in this test env (we run "
            "from a git checkout)",
        )

    def test_archive_mode_flag_propagates_through_cli(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--json", "--archive-mode"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode, 0,
            f"--archive-mode must exit 0; got {completed.returncode}: "
            f"stderr={completed.stderr}",
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["mode"], "archive")
        self.assertEqual(payload["status"], "pass")


if __name__ == "__main__":
    unittest.main()
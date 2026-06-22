"""Tests for the Fusion Router CLI helpers (``fusion-router``, ``mad-dog``).

The CLI is exercised via the ``fusion_router_command`` and
``mad_dog_command`` entry points; the optional Typer command
registration is exercised through the CLI registry smoke tests
elsewhere.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

from loopos.cli.commands.fusion_router import (
    fusion_router_command,
)
from loopos.cli.commands.mad_dog import mad_dog_command


_TASK_JSON = json.dumps(
    {
        "title": "refactor the auth module",
        "task_type": "refactor",
        "complexity_score": 8,
        "risk_score": 6,
        "failure_count": 3,
        "affected_files": [
            "src/auth/login.py",
            "src/auth/session.py",
        ],
    },
)


# ---------------------------------------------------------------------------


def _capture(
    callable_: Callable[..., int],
    *args: object,
    **kwargs: object,
) -> tuple[int, str]:
    buffer = io.StringIO()
    err_buffer = io.StringIO()
    with redirect_stdout(buffer):
        import contextlib
        with contextlib.redirect_stderr(err_buffer):
            code = callable_(*args, **kwargs)
    return code, buffer.getvalue() + err_buffer.getvalue()


class FusionRouterCLITests(unittest.TestCase):
    def test_plan_outputs_fusion_plan_json(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="plan",
            task_arg=_TASK_JSON,
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertIn("mode", payload)
        self.assertIn("fusion_score", payload)
        self.assertIn("assignments", payload)
        self.assertIn("recommended_aci_commands", payload)

    def test_explain_outputs_activation_rationale(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="explain",
            task_arg=_TASK_JSON,
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertIn("activation_decision", payload)
        self.assertIn("fusion_score", payload)
        self.assertIn("selected_mode", payload)
        self.assertIn("trigger_reasons", payload)
        self.assertIn("why_single_or_not", payload)

    def test_run_dry_run_outputs_plan(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="run",
            task_arg=_TASK_JSON,
            dry_run=True,
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertIn("recommended_aci_commands", payload)
        self.assertFalse(payload["live_provider_calls_allowed"])

    def test_run_without_dry_run_still_plans(self) -> None:
        # The router is planning-only; ``run`` without ``--dry-run``
        # still produces a FusionPlan (the master prompt defers
        # actual execution to v0.3+).
        code, output = _capture(
            fusion_router_command,
            action="run",
            task_arg=_TASK_JSON,
            dry_run=False,
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], payload["mode"])  # set

    def test_escalate_emits_plan(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="escalate",
            run_id="run-1",
            reason="repeated_failure",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["trigger"]["source"], "kernel")
        self.assertEqual(payload["trigger"]["reason"], "repeated_failure")

    def test_status_returns_not_found_payload(self) -> None:
        # Phase 7: ``fusion-router status`` reads from the local
        # JSON persistence layer. When the plan / verdict is not
        # found, the CLI returns ``not_found`` (not the v0.2
        # ``unsupported`` placeholder). The placeholder is gone.
        code, output = _capture(
            fusion_router_command,
            action="status",
            fusion_id="fusion-not-persisted",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "not_found")
        self.assertEqual(payload["fusion_id"], "fusion-not-persisted")

    def test_plan_reads_task_json_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8",
        ) as handle:
            handle.write(_TASK_JSON)
            path = handle.name
        try:
            code, output = _capture(
                fusion_router_command,
                action="plan",
                task_arg=path,
                json_output=True,
            )
            self.assertEqual(code, 0)
            payload = json.loads(output)
            self.assertIn("mode", payload)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_plan_human_output_emits_summary(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="plan",
            task_arg=_TASK_JSON,
            json_output=False,
        )
        self.assertEqual(code, 0)
        self.assertIn("FusionPlan", output)
        self.assertIn("trigger:", output)
        self.assertIn("recommended ACI commands:", output)


class MadDogCLITests(unittest.TestCase):
    def test_mad_dog_forces_mode_mad_dog(self) -> None:
        code, output = _capture(
            mad_dog_command,
            action="plan",
            task_arg=_TASK_JSON,
            severity="critical",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], "mad_dog")
        self.assertEqual(payload["trigger"]["source"], "user")
        self.assertEqual(
            payload["trigger"]["reason"], "explicit_user_request",
        )
        self.assertEqual(payload["trigger"]["severity"], "critical")

    def test_mad_dog_with_low_severity_still_mad_dog(self) -> None:
        code, output = _capture(
            mad_dog_command,
            action="plan",
            task_arg=_TASK_JSON,
            severity="low",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], "mad_dog")
        self.assertEqual(payload["trigger"]["severity"], "low")

    def test_mad_dog_explain(self) -> None:
        code, output = _capture(
            mad_dog_command,
            action="explain",
            task_arg=_TASK_JSON,
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["selected_mode"], "mad_dog")

    def test_mad_dog_escalate(self) -> None:
        code, output = _capture(
            mad_dog_command,
            action="escalate",
            run_id="run-1",
            reason="release_blocker",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["trigger"]["source"], "kernel")
        self.assertEqual(payload["trigger"]["reason"], "release_blocker")


class FusionCLIErrorTests(unittest.TestCase):
    def test_plan_without_task_returns_error(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="plan",
            task_arg=None,
        )
        self.assertEqual(code, 1)
        self.assertIn("TASK", output)

    def test_escalate_without_run_id_returns_error(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="escalate",
            run_id=None,
        )
        self.assertEqual(code, 1)
        self.assertIn("--run-id", output)

    def test_status_without_fusion_id_returns_error(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="status",
            fusion_id=None,
        )
        self.assertEqual(code, 1)
        self.assertIn("FUSION_ID", output)

    def test_unknown_action_returns_error(self) -> None:
        code, output = _capture(
            fusion_router_command,
            action="bogus",
        )
        self.assertEqual(code, 1)
        self.assertIn("Unknown", output)


if __name__ == "__main__":
    unittest.main()
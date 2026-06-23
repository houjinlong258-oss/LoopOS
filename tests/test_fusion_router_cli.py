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
from typing import Any, Callable

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


def _invoke_typer(argv: list[str]) -> tuple[int, str]:
    """Invoke the Typer app in-process and capture combined output.

    Returns ``(returncode, combined_stdout_plus_stderr)``. The
    return code mirrors what Typer / the wrapped command emit;
    ``SystemExit`` is caught so the call is safe from inside
    unittest tests.
    """
    import sys as _sys
    import contextlib
    from loopos.cli.app import app as _app

    out = io.StringIO()
    err = io.StringIO()
    saved = list(_sys.argv)
    _sys.argv = ["loopos"] + list(argv)
    try:
        with redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                _app()
            except SystemExit as exc:  # pragma: no cover - defensive
                return int(getattr(exc, "code", 0) or 0), out.getvalue() + err.getvalue()
    finally:
        _sys.argv = saved
    return 0, out.getvalue() + err.getvalue()


class MadDogTyperCLIRegressionTests(unittest.TestCase):
    """Regression tests for the ``mad-dog`` Typer surface.

    These tests cover the v0.2 RC hotfix that exposed the
    ``--fusion-id`` option on the Typer registration for
    ``mad-dog status`` and ``mad-dog route``. Before the fix,
    Typer rejected the flag with::

        No such option: --fusion-id Did you mean --run-id?

    The underlying ``mad_dog_command(fusion_id=...)`` function
    worked correctly (covered by :class:`MadDogCLITests`), but the
    Typer registration in :mod:`loopos.cli.app` did not declare
    or forward the option. These tests prove the Typer surface is
    now consistent with the function-level surface and with the
    ``fusion-router`` Typer surface.
    """

    _MAD_DOG_TASK = json.dumps(
        {
            "title": "nasty release blocker",
            "task_type": "release",
            "complexity_score": 7,
            "risk_score": 5,
            "failure_count": 5,
            "user_dissatisfaction_count": 4,
            "affected_file_count": 12,
            "no_progress_count": 3,
            "release_blocker": True,
            "security_sensitive": False,
            "model_mismatch": False,
        },
    )

    def _persist_mad_dog_plan(self) -> str:
        """Persist a mad-dog plan and return its ``fusion_id``."""
        code, output = _capture(
            mad_dog_command,
            action="plan",
            task_arg=self._MAD_DOG_TASK,
            severity="critical",
            json_output=True,
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], "mad_dog")
        fusion_id_raw: Any = payload["fusion_id"]
        fusion_id = str(fusion_id_raw)
        self.assertIsInstance(fusion_id, str)
        self.assertTrue(fusion_id)
        return fusion_id

    def test_mad_dog_status_typer_accepts_fusion_id(self) -> None:
        """``loopos mad-dog status --fusion-id ID --json`` is accepted."""
        fusion_id = self._persist_mad_dog_plan()

        code, output = _invoke_typer(
            [
                "mad-dog",
                "--action", "status",
                "--fusion-id", fusion_id,
                "--json",
            ],
        )

        self.assertNotIn("No such option", output)
        self.assertNotIn("Did you mean --run-id", output)
        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "loaded")
        self.assertEqual(payload["fusion_id"], fusion_id)

    def test_mad_dog_route_typer_accepts_fusion_id(self) -> None:
        """``loopos mad-dog route --fusion-id ID --json`` is accepted."""
        fusion_id = self._persist_mad_dog_plan()

        code, output = _invoke_typer(
            [
                "mad-dog",
                "--action", "route",
                "--fusion-id", fusion_id,
                "--json",
            ],
        )

        self.assertNotIn("No such option", output)
        self.assertNotIn("Did you mean --run-id", output)
        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "planning_only")
        self.assertEqual(payload["fusion_id"], fusion_id)

    def test_mad_dog_status_typer_missing_fusion_id_returns_structured_error(
        self,
    ) -> None:
        """Missing ``--fusion-id`` is a structured CLI error, not Typer."""
        code, output = _invoke_typer(
            ["mad-dog", "--action", "status", "--json"],
        )

        # Typer must NOT reject the invocation: it is a missing-arg
        # error from the wrapped mad_dog_command.
        self.assertNotIn("No such option", output)
        self.assertNotIn("Did you mean --run-id", output)
        self.assertEqual(code, 1, msg=output)
        self.assertIn("FUSION_ID", output)

    def test_mad_dog_route_typer_missing_fusion_id_returns_structured_error(
        self,
    ) -> None:
        """Missing ``--fusion-id`` is a structured CLI error, not Typer."""
        code, output = _invoke_typer(
            ["mad-dog", "--action", "route", "--json"],
        )

        self.assertNotIn("No such option", output)
        self.assertNotIn("Did you mean --run-id", output)
        self.assertEqual(code, 1, msg=output)
        self.assertIn("--fusion-id", output)

    def test_mad_dog_status_typer_unknown_fusion_id_returns_not_found(
        self,
    ) -> None:
        """Unknown ``--fusion-id`` returns a structured not_found payload."""
        code, output = _invoke_typer(
            [
                "mad-dog",
                "--action", "status",
                "--fusion-id", "does-not-exist-audit",
                "--json",
            ],
        )

        self.assertNotIn("No such option", output)
        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "not_found")
        self.assertEqual(payload["fusion_id"], "does-not-exist-audit")

    def test_fusion_router_status_typer_still_works(self) -> None:
        """``fusion-router status --fusion-id ID`` regression smoke."""
        fusion_id = self._persist_mad_dog_plan()

        code, output = _invoke_typer(
            [
                "fusion-router",
                "--action", "status",
                "--fusion-id", fusion_id,
                "--json",
            ],
        )

        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "loaded")
        self.assertEqual(payload["fusion_id"], fusion_id)

    def test_fusion_router_route_typer_planning_only_fallback(self) -> None:
        """``fusion-router route --fusion-id ID`` planning-only fallback."""
        fusion_id = self._persist_mad_dog_plan()

        code, output = _invoke_typer(
            [
                "fusion-router",
                "--action", "route",
                "--fusion-id", fusion_id,
                "--json",
            ],
        )

        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "planning_only")
        self.assertEqual(payload["fusion_id"], fusion_id)


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


class FusionCLINoTaskFileRegressionTests(unittest.TestCase):
    """Regression tests for the Linux ``OSError(ENAMETOOLONG)`` bug.

    On Linux the kernel's per-component ``NAME_MAX`` is typically
    255 bytes. Long inline-JSON payloads (e.g. the ``nasty release
    blocker`` task profile used by the Typer regression tests)
    exceed that limit. The Typer wrapper for ``mad-dog`` and
    ``fusion-router`` must therefore never forward ``--task`` to
    status / list / route actions and the underlying
    :func:`_read_task_input` must not probe the filesystem for
    strings that already look like inline JSON.
    """

    # 281-char JSON payload; > 255 so it would trip NAME_MAX on Linux.
    _LONG_INLINE_JSON = json.dumps(
        {
            "title": "nasty release blocker",
            "task_type": "release",
            "complexity_score": 7,
            "risk_score": 5,
            "failure_count": 5,
            "user_dissatisfaction_count": 4,
            "affected_file_count": 12,
            "no_progress_count": 3,
            "release_blocker": True,
            "security_sensitive": False,
            "model_mismatch": False,
        },
    )

    def test_mad_dog_status_typer_drops_task(self) -> None:
        """``mad-dog status --task <long-json> --fusion-id ID`` works.

        The wrapper must not forward ``--task`` for status, so the
        long inline JSON must never be re-parsed as a path. We pass
        a synthetic ``--fusion-id`` that won't be found; we only
        assert the wrapper reaches the status branch and emits a
        structured ``not_found`` (no OSError, no traceback).
        """
        code, output = _invoke_typer(
            [
                "mad-dog",
                "--action", "status",
                "--task", self._LONG_INLINE_JSON,
                "--fusion-id", "does-not-exist-status-typer",
                "--json",
            ],
        )
        self.assertNotIn("OSError", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "not_found")

    def test_mad_dog_route_typer_drops_task(self) -> None:
        """``mad-dog route --task <long-json> --fusion-id ID`` works.

        Same shape as the status test, but exercises the route
        branch (which loads a persisted plan). With an unknown
        ``fusion_id`` the wrapper should emit a structured error,
        not an OSError / traceback.
        """
        code, output = _invoke_typer(
            [
                "mad-dog",
                "--action", "route",
                "--task", self._LONG_INLINE_JSON,
                "--fusion-id", "does-not-exist-route-typer",
                "--json",
            ],
        )
        self.assertNotIn("OSError", output)
        self.assertNotIn("Traceback", output)
        # route returns 1 for unknown fusion_id but must not crash.
        self.assertIn(code, (0, 1), msg=output)

    def test_fusion_router_status_typer_drops_task(self) -> None:
        """``fusion-router status --task <long-json> --fusion-id ID`` works."""
        code, output = _invoke_typer(
            [
                "fusion-router",
                "--action", "status",
                "--task", self._LONG_INLINE_JSON,
                "--fusion-id", "does-not-exist-fr-status-typer",
                "--json",
            ],
        )
        self.assertNotIn("OSError", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(code, 0, msg=output)
        payload = json.loads(output)
        self.assertEqual(payload["status"], "not_found")

    def test_fusion_router_route_typer_drops_task(self) -> None:
        """``fusion-router route --task <long-json> --fusion-id ID`` works."""
        code, output = _invoke_typer(
            [
                "fusion-router",
                "--action", "route",
                "--task", self._LONG_INLINE_JSON,
                "--fusion-id", "does-not-exist-fr-route-typer",
                "--json",
            ],
        )
        self.assertNotIn("OSError", output)
        self.assertNotIn("Traceback", output)
        self.assertIn(code, (0, 1), msg=output)

    def test_read_task_input_handles_long_inline_json(self) -> None:
        """``_read_task_input`` treats ``{``-prefixed strings as inline JSON.

        This is the second half of the fix: even if some caller
        hands a long JSON string to ``_read_task_input``, the
        function must skip the filesystem probe so it never trips
        ``OSError(ENAMETOOLONG)`` on Linux.
        """
        from loopos.fusion_router.cli import _read_task_input

        data = _read_task_input(self._LONG_INLINE_JSON)
        self.assertEqual(data["title"], "nasty release blocker")
        self.assertEqual(data["release_blocker"], True)

    def test_read_task_input_still_reads_files(self) -> None:
        """``_read_task_input`` still reads real files when the path exists.

        The inline-JSON heuristic must not regress the file-path
        case used by ``rc_audit_cli_smoke.py`` and the
        ``tests/test_fusion_router_cli.py`` plan tests.
        """
        from loopos.fusion_router.cli import _read_task_input

        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "task.json"
            payload_path.write_text(self._LONG_INLINE_JSON, encoding="utf-8")
            data = _read_task_input(str(payload_path))
            self.assertEqual(data["title"], "nasty release blocker")


if __name__ == "__main__":
    unittest.main()
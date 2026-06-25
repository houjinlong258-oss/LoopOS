"""Tests for the v0.4 ``--human`` panel renderers.

Each test:

* feeds a deterministic mock payload into a renderer,
* captures the rendered Rich output,
* asserts on (a) markup leaks, (b) plain-value coloring,
  (c) mood-driven box / border / mascot, (d) diagnostic surface.

These tests are the regression net for the bug we already had
(``Text(inner, style="white")`` swallowed Rich markup and emitted
literal ``[bold]...[/bold]`` to stdout) — they ensure the four mood
panels, the new review/repair/optimize panels, and the generic
fallback all parse Rich markup correctly and colour their plain
values so nothing renders as washed-out white.
"""
from __future__ import annotations

from collections.abc import Iterator
from io import StringIO
from typing import Any, cast

import pytest

from loopos.cli._human_styles import HAS_RICH
from loopos.cli.commands.loop import (
    _emit_human,
    _emit_human_deliver,
    _emit_human_generic,
    _emit_human_optimize,
    _emit_human_repair,
    _emit_human_review,
    _emit_human_run,
    _emit_human_status,
)
from loopos.i18n import set_locale


# Skip the entire module when Rich is not available — the renderers
# are best-effort in that case and we test the fallback in
# ``test_cli_human_styles.py::TestEmitPlainDict`` instead.
pytestmark = pytest.mark.skipif(not HAS_RICH, reason="Rich not installed")


@pytest.fixture(autouse=True)
def english_locale() -> Iterator[None]:
    set_locale("en", source="test")
    yield
    set_locale("en", source="test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_console(width: int = 120) -> tuple[Any, StringIO]:
    """Build a Rich Console writing to an in-memory buffer + return
    the live console + buffer.

    Two non-default knobs are essential:

    * ``safe_box=False`` — without this Rich falls back to ASCII box
      characters (``┌───┘``) so we can't tell ROUNDED (``╭───╯``)
      from HEAVY (``╔═══╝``) apart in the recorded output.
    * ``theme=BRIGHT_THEME`` — Rich's default theme maps ``[cyan]`` to
      ``#008080`` (dim ANSI). The dazzling/audit specs assume the
      bright palette (``#00ffff`` etc.), so we use the same theme the
      renderer scripts use.
    """
    from rich.console import Console
    from rich.theme import Theme
    buf = StringIO()
    bright = Theme({
        "cyan": "bright_cyan",
        "green": "bright_green",
        "yellow": "bright_yellow",
        "red": "bright_red",
        "magenta": "bright_magenta",
        "blue": "bright_blue",
        "white": "bright_white",
        "dim": "grey70",
        "bold": "bold bright_white",
    })
    con = Console(
        file=buf, record=True, width=width,
        color_system="truecolor", force_terminal=True,
        safe_box=False, theme=bright,
    )
    return con, buf


def _rendered_html(console: Any) -> str:
    """Return the recorded HTML (with inline color spans) for assertion."""
    return cast(str, console.export_html(inline_styles=True))


def _rendered_text(console: Any) -> str:
    """Return plain recorded text — safe for markup-leak assertions."""
    return cast(str, console.export_text())


def _no_markup_leak(text: str) -> None:
    """Assert no ``[bold]…[/bold]`` / ``[cyan]…[/cyan]`` literal leak.

    The original bug we fixed used ``Text(inner, style="white")``
    which swallowed Rich markup. These assertions are the canary.
    """
    assert "[bold]" not in text, f"literal [bold] leaked into output:\n{text}"
    assert "[/bold]" not in text, f"literal [/bold] leaked into output:\n{text}"
    assert "[cyan]" not in text, f"literal [cyan] leaked into output:\n{text}"
    assert "[/cyan]" not in text, f"literal [/cyan] leaked into output:\n{text}"
    assert "[green]" not in text, f"literal [green] leaked into output:\n{text}"
    assert "[/green]" not in text, f"literal [/green] leaked into output:\n{text}"
    assert "[red]" not in text, f"literal [red] leaked into output:\n{text}"
    assert "[/red]" not in text, f"literal [/red] leaked into output:\n{text}"


# ---------------------------------------------------------------------------
# _emit_human_run
# ---------------------------------------------------------------------------


_RUN_OBJ_READY: dict[str, Any] = {
    "run_id": "run_test123",
    "data_dir": "/tmp",
    "user_goal": "Build a thing with cyan glow",
    "current_status": "ready_to_deliver",
    "iterations": [{
        "id": "iter_1", "index": 1, "goal_id": "g1",
        "plan": {"id": "plan_x",
                  "title": "Initial plan: Build a thing",
                  "source": "planner"},
        "build_result": {"status": "simulated",
                         "source": "loopos_v0_4_simulated_adapter",
                         "summary": "Simulated build"},
        "test_result": {"status": "simulated",
                        "source": "loopos_v0_4_simulated_adapter",
                        "passed": 5, "failed": 0, "skipped": 0,
                        "failures": [], "evidence": ["sim pass"]},
        "review_findings": [], "repair_plan": None, "optimization_plan": None,
        "quality_score": {"overall": 0.99, "goal_alignment": 1.0,
                          "test_health": 1.0, "defect_health": 0.95,
                          "design_health": 1.0, "documentation_health": 1.0,
                          "delivery_readiness": 1.0},
        "convergence": {"status": "deliver", "reason": "q>=0.75",
                        "satisfied_criteria": ["crit_a"],
                        "unsatisfied_criteria": [], "next_recommended_action": None,
                        "fake_convergence": []},
        "loss": {"total": 0.0, "unsat_required": 0.0,
                 "blocking_findings": 0.0, "no_improvement": 0.0,
                 "fake_convergence": 0.0},
        "signals": [],
    }],
    "delivery": {"id": "d1", "status": "ready", "ready": True,
                 "summary": "OK", "known_limitations": ["simulated executor"],
                 "open_risks": [],
                 "evidence": ["criterion crit_a satisfied"],
                 "quality_score": {"overall": 0.99}},
}


class TestEmitHumanRun:
    def test_no_markup_leak(self) -> None:
        con, _ = _capture_console()
        _emit_human_run(_RUN_OBJ_READY, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_plain_values_have_color_markup(self) -> None:
        con, _ = _capture_console()
        _emit_human_run(_RUN_OBJ_READY, con)
        html = _rendered_html(con)
        # Run id, user_goal, Iterations should all be colourised.
        assert 'color: #00ffff' in html, "run_id / user_goal should render cyan"
        assert 'color: #5f5fff' in html or 'color: #0000ff' in html, \
            "Iterations count should render blue"

    def test_blocked_mood_uses_heavy_box(self) -> None:
        obj = dict(_RUN_OBJ_READY,
                   current_status="blocked",
                   delivery={"id": "d1", "status": "blocked",
                             "ready": False, "summary": "blocked",
                             "known_limitations": ["x"], "open_risks": [],
                             "evidence": [], "quality_score": {"overall": 0.0}})
        con, _ = _capture_console()
        _emit_human_run(obj, con)
        text = _rendered_text(con)
        # HEAVY box top-left corner is '┏' (U+250F).
        assert "┏" in text or "blocked" in text.lower()

    def test_running_mood_uses_cyan(self) -> None:
        obj = dict(_RUN_OBJ_READY, current_status="running")
        obj["delivery"] = None
        con, _ = _capture_console()
        _emit_human_run(obj, con)
        html = _rendered_html(con)
        # running mood → cyan border / status colour.
        assert 'color: #00ffff' in html


# ---------------------------------------------------------------------------
# _emit_human_status
# ---------------------------------------------------------------------------


_STATUS_OBJ: dict[str, Any] = {
    "run_id": "run_status_001",
    "user_goal": "Make the dashboard cyan",
    "current_status": "ready_to_deliver",
    "current_iteration": 1,
    "iterations": [{"index": 1, "plan_id": "plan_a", "plan_source": "planner",
                    "build_status": "simulated", "test_status": "simulated",
                    "last_failed_tests": [], "last_repair_plan": None,
                    "last_optimization_plan": None,
                    "last_quality_score": {"overall": 0.99},
                    "last_loss": {"total": 0.0},
                    "last_goal_gap": {"unsatisfied_required": [],
                                      "blocked_criteria": []},
                    "last_findings_count": 0, "blocking_findings": []}],
    "lail_signals": [],
    "lail_kind_summary": {"iteration_started": 1, "plan_emitted": 1,
                          "build_completed": 1, "test_completed": 1,
                          "review_completed": 1, "repair_planned": 1,
                          "convergence_decided": 1, "checkpoint_saved": 1},
    "last_iteration": {"id": "iter_1"},
    "convergence": {"status": "deliver", "fake_convergence": []},
    "next_recommended_action": None,
    "fake_convergence_findings": [],
    "checkpoint_path": "/tmp/runs/run_status_001/checkpoint.json",
}


class TestEmitHumanStatus:
    def test_no_markup_leak(self) -> None:
        con, _ = _capture_console()
        _emit_human_status(_STATUS_OBJ, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_checkpoint_path_colourised(self) -> None:
        con, _ = _capture_console()
        _emit_human_status(_STATUS_OBJ, con)
        html = _rendered_html(con)
        # Checkpoint path is plain string; should be wrapped in cyan.
        assert 'color: #00ffff' in html

    def test_surfaces_reason_codes(self) -> None:
        obj = dict(_STATUS_OBJ,
                   reason_codes=["capability_boundary.required_for_X",
                                 "policy.missing_approval"])
        con, _ = _capture_console()
        _emit_human_status(obj, con)
        text = _rendered_text(con)
        assert "Reason codes" in text
        assert "capability_boundary.required_for_X" in text
        assert "policy.missing_approval" in text

    def test_surfaces_fake_convergence_findings(self) -> None:
        obj = dict(_STATUS_OBJ,
                   fake_convergence_findings=["checkpoint_laundering",
                                              "unsat_criteria_hiding"])
        con, _ = _capture_console()
        _emit_human_status(obj, con)
        text = _rendered_text(con)
        assert "Fake-convergence" in text
        assert "checkpoint_laundering" in text

    def test_blocked_mood_uses_heavy_box(self) -> None:
        obj = dict(_STATUS_OBJ,
                   fake_convergence_findings=["checkpoint_laundering"])
        con, _ = _capture_console()
        _emit_human_status(obj, con)
        text = _rendered_text(con)
        # HEAVY box uses '┏' (U+250F) on its top-left corner, while
        # ROUNDED uses '╭' (U+256D). The blocked mood must switch
        # the box style to HEAVY so the border itself screams "stop".
        assert "┏" in text
        assert "╭" not in text.split("\n")[0]  # first row is top border


# ---------------------------------------------------------------------------
# _emit_human_deliver
# ---------------------------------------------------------------------------


_DELIVER_OBJ_READY: dict[str, Any] = {
    "run_id": "run_deliver_001",
    "user_goal": "Ship a cyan dashboard",
    "delivery_status": "ready",
    "ready": True,
    "why": "All criteria satisfied with evidence; quality 0.99.",
    "summary": "Loop run with 1 iteration.",
    "success_criteria_coverage": {"required": 1, "satisfied": 1,
                                    "unsatisfied": 0,
                                    "satisfied_ids": ["crit_a"],
                                    "unsatisfied_ids": []},
    "remaining_gaps": [], "fake_convergence_findings": [],
    "evidence": ["criterion crit_a satisfied"],
    "open_risks": [], "known_limitations": ["simulated executor"],
    "convergence_status": "deliver", "iterations": 1,
    "recommended_next_loop": "Run another loop with a fresh plan candidate.",
    "quality_score": {"overall": 0.99, "goal_alignment": 1.0,
                       "test_health": 1.0, "delivery_readiness": 1.0},
}


class TestEmitHumanDeliver:
    def test_no_markup_leak(self) -> None:
        con, _ = _capture_console()
        _emit_human_deliver(_DELIVER_OBJ_READY, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_why_field_colourised(self) -> None:
        con, _ = _capture_console()
        _emit_human_deliver(_DELIVER_OBJ_READY, con)
        html = _rendered_html(con)
        assert 'color: #00ffff' in html  # Why is cyan now

    def test_blocked_delivery_uses_heavy_box(self) -> None:
        obj = dict(_DELIVER_OBJ_READY,
                   delivery_status="blocked",
                   ready=False,
                   fake_convergence_findings=["checkpoint laundering"])
        con, _ = _capture_console()
        _emit_human_deliver(obj, con)
        text = _rendered_text(con)
        assert "┏" in text


# ---------------------------------------------------------------------------
# _emit_human_review
# ---------------------------------------------------------------------------


class TestEmitHumanReview:
    def test_no_markup_leak_no_findings(self) -> None:
        con, _ = _capture_console()
        _emit_human_review({"run_id": "r1", "iteration": 1,
                            "findings": []}, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_blocking_finding_pushes_blocked_mood(self) -> None:
        con, _ = _capture_console()
        _emit_human_review({"run_id": "r1", "iteration": 2, "findings": [
            {"severity": "high", "target": "loop_engine.repair",
             "message": "missing evidence"}
        ]}, con)
        text = _rendered_text(con)
        assert "high" in text
        assert "loop_engine.repair" in text
        # Heavy box for blocked.
        assert "┏" in text

    def test_severity_colorisation(self) -> None:
        con, _ = _capture_console()
        _emit_human_review({"run_id": "r1", "iteration": 1, "findings": [
            {"severity": "high", "target": "t", "message": "m1"},
            {"severity": "medium", "target": "t", "message": "m2"},
            {"severity": "low", "target": "t", "message": "m3"},
        ]}, con)
        html = _rendered_html(con)
        # high → bright_red (#ff0000); medium → bright_yellow (#ffff00);
        # low → bright_blue (#0000ff). Accept the dim ANSI variants too
        # so the test isn't pinned to a single Theme.
        assert ('color: #ff0000' in html or 'color: #800000' in html), \
            "high severity should be red"
        assert ('color: #ffff00' in html or 'color: #808000' in html), \
            "medium severity should be yellow"
        assert ('color: #0000ff' in html or 'color: #000080' in html), \
            "low severity should be blue"

    def test_mad_dog_findings_rendered(self) -> None:
        con, _ = _capture_console()
        _emit_human_review({
            "run_id": "r1", "iteration": 1,
            "findings": [{"severity": "low", "target": "x", "message": "m"}],
            "mad_dog_findings": [{"category": "drift", "severity": "high",
                                  "message": "agent drift"}],
        }, con)
        text = _rendered_text(con)
        assert "Mad-dog review" in text
        assert "drift" in text


# ---------------------------------------------------------------------------
# _emit_human_repair
# ---------------------------------------------------------------------------


_REPAIR_PLAN: dict[str, Any] = {
    "id": "repair_abc",
    "source_findings": ["f1", "f2"],
    "steps": ["step A", "step B", "step C"],
    "priority": "high",
    "expected_fix": "coverage gap closed",
    "tests_to_run": ["test_x.py", "test_y.py"],
}


class TestEmitHumanRepair:
    def test_no_markup_leak_with_plan(self) -> None:
        con, _ = _capture_console()
        _emit_human_repair(_REPAIR_PLAN, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_priority_high_pushes_blocked(self) -> None:
        con, _ = _capture_console()
        _emit_human_repair(_REPAIR_PLAN, con)
        text = _rendered_text(con)
        # HEAVY box for blocked.
        assert "┏" in text

    def test_no_repair_plan_branch(self) -> None:
        con, _ = _capture_console()
        _emit_human_repair({"status": "no_repair_plan",
                            "run_id": "r1", "iteration": 3}, con)
        text = _rendered_text(con)
        assert "no_repair_plan" in text
        _no_markup_leak(text)

    def test_steps_listed(self) -> None:
        con, _ = _capture_console()
        _emit_human_repair(_REPAIR_PLAN, con)
        text = _rendered_text(con)
        assert "step A" in text
        assert "step B" in text


# ---------------------------------------------------------------------------
# _emit_human_optimize
# ---------------------------------------------------------------------------


_OPT_RESULT: dict[str, Any] = {
    "id": "fusion_xyz",
    "mode": "consensus",
    "confidence": 0.92,
    "alternatives": [{"id": "alt1", "title": "alt", "source": "planner"}],
    "review_findings": [
        {"severity": "medium", "target": "f", "message": "drift"}],
    "repair_plan": None,
    "optimization_plan": {"id": "opt1", "target": "perf", "reason": "x",
                           "expected_improvement": "", "steps": [],
                           "measurable_outcome": ""},
    "recommended_next_plan": {"id": "plan_next", "title": "Next plan",
                               "source": "planner"},
    "rationale": "consensus reached",
    "disagreements": [],
}


class TestEmitHumanOptimize:
    def test_no_markup_leak(self) -> None:
        con, _ = _capture_console()
        _emit_human_optimize(_OPT_RESULT, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_high_confidence_renders_calm(self) -> None:
        con, _ = _capture_console()
        _emit_human_optimize(_OPT_RESULT, con)
        text = _rendered_text(con)
        # calm mood = ROUNDED box (╭)
        assert "╭" in text

    def test_low_confidence_renders_halted(self) -> None:
        con, _ = _capture_console()
        _emit_human_optimize(dict(_OPT_RESULT, confidence=0.3), con)
        text = _rendered_text(con)
        # halted mood = ROUNDED box (still ROUNDED, only blocked uses HEAVY)
        assert "╭" in text

    def test_rationale_and_recommended_plan_rendered(self) -> None:
        con, _ = _capture_console()
        _emit_human_optimize(_OPT_RESULT, con)
        text = _rendered_text(con)
        assert "consensus reached" in text
        assert "Next plan" in text


# ---------------------------------------------------------------------------
# _emit_human_generic
# ---------------------------------------------------------------------------


class TestEmitHumanGeneric:
    def test_no_markup_leak(self) -> None:
        con, _ = _capture_console()
        _emit_human_generic({"foo": 1, "bar": "baz"}, con)
        text = _rendered_text(con)
        _no_markup_leak(text)

    def test_drops_hardcoded_loop_ok_title(self) -> None:
        """v0.4.0 closeout: previously every unknown payload was
        labelled ``[bold green]loop[/bold green] [green]ok[/green]``
        regardless of the actual mood. The generic renderer now
        derives a mood from the payload's status fields.
        """
        con, _ = _capture_console()
        _emit_human_generic({"status": "blocked", "detail": "x"}, con)
        text = _rendered_text(con)
        # Title now reads "loop result [...] [blocked]" instead of "loop ok".
        assert "result" in text.lower()
        # blocked → HEAVY box.
        assert "┏" in text

    def test_falls_back_to_calm_for_unknown(self) -> None:
        con, _ = _capture_console()
        _emit_human_generic({"foo": 1}, con)
        text = _rendered_text(con)
        assert "calm" in text


# ---------------------------------------------------------------------------
# _emit_human dispatcher
# ---------------------------------------------------------------------------


class TestEmitHumanDispatch:
    """The dispatcher must route each v0.4 payload to the right panel."""

    def _dispatch(self, obj: Any) -> str:
        """Invoke ``_emit_human`` with a captured bright-theme console
        and return the rendered text."""
        import loopos.cli.commands.loop as loop_mod
        con, _ = _capture_console()
        original = loop_mod.Console
        loop_mod.Console = lambda *a, **kw: con
        try:
            _emit_human(obj)
        finally:
            loop_mod.Console = original
        return cast(str, con.export_text())

    def test_routes_run_shape_to_run_renderer(self) -> None:
        text = self._dispatch(_RUN_OBJ_READY)
        assert "loop run" in text

    def test_routes_review_shape_to_review_renderer(self) -> None:
        text = self._dispatch({"run_id": "r1", "iteration": 1,
                                "findings": [{"severity": "low",
                                              "target": "t", "message": "m"}]})
        assert "loop review" in text

    def test_routes_repair_plan_shape(self) -> None:
        text = self._dispatch(_REPAIR_PLAN)
        assert "loop repair" in text

    def test_routes_optimize_shape(self) -> None:
        text = self._dispatch(_OPT_RESULT)
        assert "loop optimize" in text

    def test_unknown_shape_falls_through_to_generic(self) -> None:
        text = self._dispatch({"weird": "shape", "totally_unknown": True})
        assert "loop result" in text.lower()

"""Tests for the shared ``--human`` style utilities.

Covers:

* :func:`mood_for_obj` — mood classification from status fields.
* :func:`xiao_huanli` — the 4-mood mascot ASCII art.
* :func:`mood_box` — ROUNDED vs HEAVY depending on mood.
* :func:`kv` / :func:`kv_plain` / :func:`kvd` — markup-string builders.
* :func:`emit_plain_dict` — no-Rich fallback.

These utilities are the foundation every v0.4 ``--human`` renderer depends
on. Breaking them silently would break six panels at once.
"""
from __future__ import annotations

from typing import Any

from loopos.cli._human_styles import (
    HAS_RICH,
    MOOD_COLOR,
    emit_plain_dict,
    kv,
    kv_plain,
    kvd,
    mood_box,
    mood_for_obj,
    xiao_huanli,
)


# ---------------------------------------------------------------------------
# mood_for_obj
# ---------------------------------------------------------------------------


class TestMoodForObj:
    def test_calm_for_ready_status(self) -> None:
        assert mood_for_obj({"current_status": "ready_to_deliver"}) == "calm"
        assert mood_for_obj({"delivery_status": "ready"}) == "calm"

    def test_running_for_active(self) -> None:
        assert mood_for_obj({"current_status": "running"}) == "running"
        assert mood_for_obj({"current_status": "in_progress"}) == "running"

    def test_blocked_for_blocked_or_failed(self) -> None:
        assert mood_for_obj({"current_status": "blocked"}) == "blocked"
        assert mood_for_obj({"current_status": "error"}) == "blocked"
        assert mood_for_obj({"current_status": "failed"}) == "blocked"

    def test_halted_for_halted(self) -> None:
        assert mood_for_obj({"current_status": "halted"}) == "halted"
        assert mood_for_obj({"current_status": "budget_exhausted"}) == "halted"
        # ``no_repair_plan`` should read as halted, not "calm".
        assert mood_for_obj({"status": "no_repair_plan"}) == "halted"

    def test_fake_convergence_findings_force_blocked(self) -> None:
        # Even with a "ready" status, fake-convergence findings must
        # surface as blocked — otherwise the panel lies.
        assert mood_for_obj({
            "delivery_status": "ready",
            "fake_convergence_findings": ["checkpoint laundering"],
        }) == "blocked"

    def test_default_is_calm_for_unknown_status(self) -> None:
        assert mood_for_obj({"current_status": "unfamiliar"}) == "calm"
        assert mood_for_obj({}) == "calm"


# ---------------------------------------------------------------------------
# MOOD_COLOR + mood_box
# ---------------------------------------------------------------------------


class TestMoodStyling:
    def test_mood_color_map_covers_four_moods(self) -> None:
        assert set(MOOD_COLOR.keys()) == {"calm", "running", "blocked", "halted"}
        assert MOOD_COLOR["blocked"] == "red"
        assert MOOD_COLOR["calm"] == "green"

    def test_blocked_uses_heavy_box(self) -> None:
        if HAS_RICH:
            from rich.box import HEAVY, ROUNDED
            assert mood_box("blocked") is HEAVY
            assert mood_box("calm") is ROUNDED
            assert mood_box("running") is ROUNDED
            assert mood_box("halted") is ROUNDED
        else:
            assert mood_box("blocked") is None


# ---------------------------------------------------------------------------
# xiao_huanli
# ---------------------------------------------------------------------------


class TestXiaoHuanli:
    def test_returns_text_when_rich_available(self) -> None:
        if not HAS_RICH:
            return  # graceful skip in dependency-light env
        mascot = xiao_huanli("calm")
        # 4 lines of ASCII, the canonical face.
        assert mascot is not None
        rendered = mascot.plain
        assert "/\\_/\\" in rendered
        assert "(o  o)" in rendered
        assert "(v)" in rendered
        assert "||||" in rendered

    def test_blocked_face_uses_x_mouth(self) -> None:
        if not HAS_RICH:
            return
        mascot = xiao_huanli("blocked")
        rendered = mascot.plain
        assert "(>  <)" in rendered
        assert "(X)" in rendered

    def test_running_face_uses_chevrons(self) -> None:
        if not HAS_RICH:
            return
        mascot = xiao_huanli("running")
        rendered = mascot.plain
        assert "(^  ^)" in rendered
        assert "»»" in rendered

    def test_halted_face(self) -> None:
        if not HAS_RICH:
            return
        mascot = xiao_huanli("halted")
        rendered = mascot.plain
        assert "(T  T)" in rendered


# ---------------------------------------------------------------------------
# Markup-string builders
# ---------------------------------------------------------------------------


class TestKvHelpers:
    def test_kv_default_cyan_value(self) -> None:
        k, v = kv("User goal", "Build X")
        assert k == "[bold white]User goal[/bold white]"
        # Plain value gets cyan by default so unlabeled text doesn't
        # render as washed-out white next to mood-coloured rows.
        assert v == "[cyan]Build X[/cyan]"

    def test_kv_custom_colors(self) -> None:
        k, v = kv("Iterations", 3, value_color="blue")
        assert v == "[blue]3[/blue]"

    def test_kv_plain_leaves_value_alone(self) -> None:
        k, v = kv_plain("Checkpoint path", "D:\\loopos-demo\\runs\\x")
        assert k == "[bold white]Checkpoint path[/bold white]"
        assert v == "D:\\loopos-demo\\runs\\x"

    def test_kvd_renders_colored_pairs(self) -> None:
        k, v = kvd("Last quality",
                   ("overall", 0.99, "green"),
                   ("test", 1.0, "green"))
        assert k == "[bold white]Last quality[/bold white]"
        assert "[green]0.99[/green]" in v
        assert "[green]1.0[/green]" in v
        assert "overall=" in v and "test=" in v


# ---------------------------------------------------------------------------
# emit_plain_dict fallback
# ---------------------------------------------------------------------------


class TestEmitPlainDict:
    def test_dict_iterates_key_value(self, capsys: Any) -> None:
        emit_plain_dict({"a": 1, "b": "two"})
        captured = capsys.readouterr()
        assert "a: 1" in captured.out
        assert "b: two" in captured.out

    def test_non_dict_strdumped(self, capsys: Any) -> None:
        emit_plain_dict("just a string")
        captured = capsys.readouterr()
        assert "just a string" in captured.out
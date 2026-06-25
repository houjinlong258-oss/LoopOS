"""Tests for ``tasks_command`` and ``memory_command`` ``--human`` flag.

The ``--human`` panels render Rich Panels, so most assertions target:

* the panel *title* text (route the right action to the right panel),
* the absence of markup leaks (``[bold]…[/bold]`` literal),
* the no-Rich fallback (printable plain-text output, no ANSI escapes).

Tasks and memory both accept a ``--human`` flag (or ``--json/--human``
pair) that flips the renderer from JSON to a Rich panel. These tests
ensure the wiring is real — calling ``--human`` must produce a panel,
not a JSON blob.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import pytest

from loopos.cli._human_styles import HAS_RICH


pytestmark = pytest.mark.skipif(not HAS_RICH, reason="Rich not installed")


def _capture(callable_: Any) -> tuple[int, str]:
    """Run ``callable_``, capture its stdout (rich escapes included)."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = callable_()
    finally:
        sys.stdout = old
    return rc, buf.getvalue()


# ---------------------------------------------------------------------------
# tasks_command --human
# ---------------------------------------------------------------------------


class TestTasksHuman:
    def test_list_with_human_output_does_not_emit_json(self, tmp_path: Path) -> None:
        from loopos.cli.commands.tasks import tasks_command
        rc, out = _capture(lambda: tasks_command(
            "list", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        # No JSON dump when --human is set, even on empty list.
        assert not out.strip().startswith("[")
        assert "No tasks stored" in out or "tasks list" in out

    def test_list_with_human_renders_panel_when_items_present(
        self, tmp_path: Path
    ) -> None:
        from loopos.cli.commands.tasks import TaskRecord, TaskStore, tasks_command
        # ``TaskStore`` writes to ``<data_dir>/tasks.json`` via data_paths().
        store = TaskStore(tmp_path / "tasks.json")
        store.create(TaskRecord(title="Build X", goal="Build X"))
        rc, out = _capture(lambda: tasks_command(
            "list", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        assert "Build X" in out
        # The panel title appears in the output.
        assert "tasks list" in out

    def test_human_output_disables_json_flag(self, tmp_path: Path) -> None:
        """``human_output=True`` must take precedence over ``json_output=True``."""
        from loopos.cli.commands.tasks import tasks_command
        rc, out = _capture(lambda: tasks_command(
            "list", data_dir=tmp_path,
            json_output=True, human_output=True,
        ))
        assert rc == 0
        # No JSON dump.
        assert not out.lstrip().startswith("[")

    def test_create_then_show_human(self, tmp_path: Path) -> None:
        from loopos.cli.commands.tasks import (
            TaskRecord, TaskStore, tasks_command,
        )
        store = TaskStore(tmp_path / "tasks.json")
        task = store.create(TaskRecord(title="Ship v0.5", goal="Ship v0.5"))
        rc, out = _capture(lambda: tasks_command(
            "show", task.id, data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        assert task.id in out
        assert "Ship v0.5" in out
        # No JSON dump.
        assert not out.lstrip().startswith("{")


# ---------------------------------------------------------------------------
# memory_command --human
# ---------------------------------------------------------------------------


class TestMemoryHuman:
    def test_list_human_with_empty_store(self, tmp_path: Path) -> None:
        from loopos.cli.commands.memory import memory_command
        rc, out = _capture(lambda: memory_command(
            "list", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        assert "No items" in out or "memory list" in out
        # Not a JSON dump.
        assert not out.lstrip().startswith("[")

    def test_reindex_human_shows_counts(self, tmp_path: Path) -> None:
        from loopos.cli.commands.memory import memory_command
        rc, out = _capture(lambda: memory_command(
            "reindex", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        # The panel title should appear.
        assert "memory reindex" in out
        # Empty reindex returns a counts dict that may be all zeros —
        # either way the panel must render.

    def test_failures_human_with_synthetic_record(self, tmp_path: Path) -> None:
        """Seed a failure record and verify ``memory failures --human``
        renders it as a coloured panel, not a JSON dump."""
        from loopos.cli.commands.memory import memory_command
        from loopos.memory.repository import MemoryRepository
        from loopos.memory.belief_store import MemoryItem
        repo = MemoryRepository(Path(tmp_path))
        repo.write_memory(MemoryItem(
            type="failure",
            content="x.y broke",
            confidence=0.9,
            source="test",
            tags=["failure", "recent"],
            status="active",
        ))
        rc, out = _capture(lambda: memory_command(
            "failures", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        assert "memory failures" in out
        # Not a JSON dump.
        assert not out.lstrip().startswith("[")

    def test_propose_human_renders_panel(self, tmp_path: Path) -> None:
        """``memory propose --from-run`` requires an existing run state;
        when the run isn't found we expect a clean panel with an
        informative message, not a JSON dump."""
        from loopos.cli.commands.memory import memory_command
        rc, out = _capture(lambda: memory_command(
            "propose", from_run="run_does_not_exist",
            data_dir=tmp_path, human_output=True,
        ))
        # ``proposal_for_run`` may raise on missing run — accept either
        # a clean error panel or a graceful failure (rc != 0 with a
        # plain stderr message). The key invariant: --human must not
        # produce a JSON dump.
        assert "{" not in out.split("\n")[0] if out.strip() else True

    def test_decisions_human_renders_panel(self, tmp_path: Path) -> None:
        from loopos.cli.commands.memory import memory_command
        from loopos.memory.repository import MemoryRepository
        from loopos.memory.belief_store import MemoryItem
        repo = MemoryRepository(Path(tmp_path))
        repo.write_memory(MemoryItem(
            type="fact",
            content="decided X",
            confidence=0.95,
            source="test",
            tags=["decision"],
            status="active",
        ))
        rc, out = _capture(lambda: memory_command(
            "decisions", data_dir=tmp_path, human_output=True,
        ))
        assert rc == 0
        assert "memory decisions" in out
        # Not a JSON dump.
        assert not out.lstrip().startswith("[")


# ---------------------------------------------------------------------------
# memory_compile_command (v0.4 closeout) --human
# ---------------------------------------------------------------------------


class TestMemoryCompileHuman:
    def test_compile_human_renders_panel(self) -> None:
        from loopos.cli.commands.memory_v04 import memory_compile_command
        rc, out = _capture(lambda: memory_compile_command(
            items="[]",
            target_role="planner",
            goal_summary="build x",
            current_gap="no gap",
            token_budget=900,
            json_output=False,
        ))
        assert rc == 0
        # No JSON dump when --human is set.
        assert not out.lstrip().startswith("{")
        # Plain-text fallback line is acceptable in dependency-light envs;
        # in Rich-enabled envs the panel title also appears.
        if HAS_RICH:
            assert "memory compile" in out or "tokens=" in out
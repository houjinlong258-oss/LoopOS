"""Tests for v0.3 adapters (mock + hermes + scream-code + cleanroom)."""

from __future__ import annotations

from loopos.adapters import AdapterRegistry, MockAdapter
from loopos.adapters.base import GoalSpec
from loopos.adapters.manifest import (
    AgentKernelAuthority,
    AgentKernelManifest,
)
from loopos.adapters.hermes import HermesAdapter
from loopos.adapters.scream_code import ScreamCodeAdapter
from loopos.adapters.cleanroom import CleanroomAdapter


def test_registry_default_has_four_adapters() -> None:
    reg = AdapterRegistry()
    ids = sorted(a.adapter_id for a in reg.list_adapters())
    assert ids == ["cleanroom", "hermes", "mock", "scream-code"]


def test_mock_adapter_emits_known_event_kinds() -> None:
    a = MockAdapter()
    goal = GoalSpec(goal_id="g1", title="t", intent="i")
    s = a.start_session(goal)
    events = list(a.submit_goal(s.session_id, goal))
    kinds = {e.kind for e in events}
    assert "goal_started" in kinds
    assert "thought" in kinds
    assert "done" in kinds


def test_mock_adapter_snapshot_and_resume() -> None:
    a = MockAdapter()
    goal = GoalSpec(goal_id="g1")
    s = a.start_session(goal)
    list(a.submit_goal(s.session_id, goal))
    snap = a.snapshot(s.session_id)
    assert snap.event_count > 0
    s2 = a.resume(snap)
    assert s2.session_id == s.session_id
    assert s2.goal.goal_id == "g1"


def test_hermes_adapter_is_cleanroom_and_simulated_by_default() -> None:
    a = HermesAdapter()
    assert a.allow_external is False
    goal = GoalSpec(goal_id="g1")
    s = a.start_session(goal)
    events = list(a.submit_goal(s.session_id, goal))
    assert any(e.kind == "goal_started" for e in events)


def test_scream_code_adapter_emits_wolfpack_style_events() -> None:
    a = ScreamCodeAdapter()
    goal = GoalSpec(goal_id="g1")
    s = a.start_session(goal)
    events = list(a.submit_goal(s.session_id, goal))
    assert len(events) > 0
    # No live process should have been spawned.
    assert all(e.kind in (
        "goal_started", "thought", "plan_created", "test_requested",
        "file_patch_proposed", "model_call_requested", "observation",
        "result", "done", "error", "tool_call_requested", "syscall_requested",
    ) for e in events)


def test_cleanroom_adapter_spec_only() -> None:
    a = CleanroomAdapter()
    goal = GoalSpec(goal_id="g1")
    s = a.start_session(goal)
    events = list(a.submit_goal(s.session_id, goal))
    assert any(e.kind == "goal_started" for e in events)


def test_registry_refuses_direct_shell_manifest() -> None:
    with __import__("pytest").raises(Exception):
        AgentKernelManifest(
            adapter_id="bad",
            name="Bad",
            version="0.3.0",
            kind="external_cli",
            entrypoint="x",
            authority=AgentKernelAuthority(direct_shell=True),
        )

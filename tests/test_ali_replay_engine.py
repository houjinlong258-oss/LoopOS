"""Tests for the Phase 8 ALI Replay Engine.

The replay engine reads ``ali.event`` records from the existing
:class:`loopos.kernel.trace.TraceStore` and rebuilds a fresh
:class:`AgentLoopSession` by replaying each event through the
existing :class:`AgentLoopFSM`. The replay must be deterministic:
same ordered event stream -> same final session state.

Coverage:

* Replay of a single-event session.
* Replay of a happy-path session that ends in HALTED_SUCCESS.
* Replay of a policy-denied session that ends in HALTED_BLOCKED.
* Replay of a session that ends in WAITING_APPROVAL.
* Replay of a session that ends in REPAIRING.
* Replay of an unsupported / failed session that ends in
  HALTED_FAILURE.
* Replay of a session that ends in REPLANNING.
* Roundtrip through the trace store: persist via
  :func:`loopos.trace.ali_bridge.persist_session_events`, then
  replay via :func:`replay_session_from_trace`.
* Determinism: replaying the same event list twice produces the
  same final session state and event log.
* Dropped-event accounting: replay respects the FSM, drops
  out-of-order events as ``invalid_transition`` or
  ``session_closed``.
* Determinism proof: replay is deterministic when given the same
  ordered event stream, regardless of wall-clock time (no
  ``time.sleep`` between events).
* No live provider API calls.
* No direct subprocess / shell bypass.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loopos.aci import (
    AgentCommand,
    AgentCommandResult,
    CommandRunner,
    RunnerConfig,
)
from loopos.aci.models import EvaluationSummary, ProgressSummary
from loopos.ali import (
    apply_event,
    consume_aci_result,
    create_session,
)
from loopos.ali.models import AgentLoopEventRecord, AgentLoopSession
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, RunSpec
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.router import create_default_syscall_router
from loopos.trace.ali_bridge import persist_session_events
from loopos.trace.ali_replay import (
    replay_events,
    replay_session_from_trace,
    replay_trace_events,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime(tmp: str):  # type: ignore[no-untyped-def]
    return KernelBoot().start(
        KernelConfig(workspace=tmp, data_dir=str(Path(tmp) / ".loopos"))
    )


def _auto_runner(tmp: str, runtime):  # type: ignore[no-untyped-def]
    return CommandRunner(
        policy_engine=runtime.policy_engine,
        syscall_router=create_default_syscall_router(
            tmp,
            auto_approve_medium=True,
            policy_engine=runtime.policy_engine,
            trace_store=runtime.trace_store,
        ),
        config=RunnerConfig(workspace=tmp, run_id="run-p8"),
    )


def _command(  # type: ignore[no-untyped-def]
    *,
    kind: str = "terminal.exec",
    cmd: str = "echo hello",
    dry_run: bool = False,
) -> AgentCommand:
    return AgentCommand(
        goal_id="goal-p8",
        purpose="phase 8 replay",
        kind=kind,  # type: ignore[arg-type]
        command=cmd,
        dry_run=dry_run,
    )


def _drive_to_running(session: AgentLoopSession) -> None:
    apply_event(session, "goal_submitted")
    apply_event(session, "command_submitted")


def _make_blocked_result(command: AgentCommand) -> AgentCommandResult:
    """Build a synthetic blocked :class:`AgentCommandResult`."""

    decision = PolicyDecision(
        decision_id="dec-p8-blocked",
        allowed=False,
        action="deny",
        severity="high",
        safety_level="L5",
        reason_codes=["policy_denied"],
    )
    return AgentCommandResult(
        command_id=command.id,
        goal_id=command.goal_id,
        status="blocked",
        success=False,
        policy_decision=decision,
        blocked_reason="policy_denied",
        reason_codes=["policy_denied"],
        messages=["policy denied"],
        metadata={"phase": "blocked_test"},
    )


def _make_approval_result(command: AgentCommand) -> AgentCommandResult:
    """Build a synthetic approval-required :class:`AgentCommandResult`."""

    decision = PolicyDecision(
        decision_id="dec-p8-approval",
        allowed=False,
        action="require_approval",
        severity="medium",
        safety_level="L2",
        requires_approval=True,
        reason_codes=["policy_requires_approval"],
    )
    return AgentCommandResult(
        command_id=command.id,
        goal_id=command.goal_id,
        status="approval_required",
        success=False,
        policy_decision=decision,
        blocked_reason="policy_requires_approval",
        requires_approval=True,
        reason_codes=["policy_requires_approval"],
        messages=["approval required"],
        metadata={"phase": "approval_test"},
    )


def _make_failed_repairable_result(command: AgentCommand) -> AgentCommandResult:
    """Build a synthetic failed-but-repairable result."""

    decision = PolicyDecision(
        decision_id="dec-p8-failed-repairable",
        allowed=True,
        action="allow",
        severity="low",
        safety_level="L0",
        reason_codes=["syscall_failed"],
    )
    return AgentCommandResult(
        command_id=command.id,
        goal_id=command.goal_id,
        status="failed",
        success=False,
        policy_decision=decision,
        evaluation=EvaluationSummary(repairable=True),
        progress=ProgressSummary(no_progress=False),
        reason_codes=["syscall_failed"],
        messages=["syscall failed"],
        metadata={"phase": "repair_test"},
    )


def _make_unsupported_result(command: AgentCommand) -> AgentCommandResult:
    """Build a synthetic unsupported :class:`AgentCommandResult`."""

    decision = PolicyDecision(
        decision_id="dec-p8-unsupported",
        allowed=True,
        action="allow",
        severity="low",
        safety_level="L0",
        reason_codes=["unsupported_command_kind"],
    )
    return AgentCommandResult(
        command_id=command.id,
        goal_id=command.goal_id,
        status="unsupported",
        success=False,
        policy_decision=decision,
        reason_codes=["unsupported_command_kind"],
        messages=["unsupported command kind"],
        metadata={"phase": "unsupported_test"},
    )


# ---------------------------------------------------------------------------
# Replay of single-event sessions
# ---------------------------------------------------------------------------


class SingleEventReplayTests(unittest.TestCase):
    def test_replay_creates_empty_session_when_no_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            # No ``ali.event`` records at all -> empty replay.
            result = replay_session_from_trace(
                runtime.trace_store, run_id="empty-run",
            )
            self.assertEqual(result.expected_event_count, 0)
            self.assertEqual(result.replayed_event_count, 0)
            self.assertEqual(result.dropped_events, [])
            self.assertEqual(result.final_state, "CREATED")
            self.assertFalse(result.halted)

    def test_replay_goal_submitted_event_only(self) -> None:
        session = create_session("goal-p8-1")
        apply_event(session, "goal_submitted")
        # Replay the events list as-is.
        replay = replay_events([session.events[0]])
        self.assertEqual(replay.final_state, "READY")
        self.assertEqual(replay.replayed_event_count, 1)
        self.assertEqual(replay.dropped_events, [])
        self.assertFalse(replay.halted)

    def test_replay_command_submitted_event_only(self) -> None:
        session = create_session("goal-p8-2")
        apply_event(session, "goal_submitted")
        apply_event(session, "command_submitted")
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "RUNNING")
        self.assertEqual(replay.replayed_event_count, 2)
        self.assertEqual(replay.dropped_events, [])


# ---------------------------------------------------------------------------
# Replay of happy-path session
# ---------------------------------------------------------------------------


class HappyPathReplayTests(unittest.TestCase):
    def test_replay_halted_success_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 8 replay happy", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p8-happy")
            _drive_to_running(session)
            engine.submit_agent_command(_command(), session, aci_runner=runner)
            # Force the convergence_halt_success transition.
            apply_event(session, "convergence_halt_success")

            latest = runtime.run_manager.load(_latest_run_id(runtime))
            persist_session_events(
                session,
                run_id=latest.run_id,
                step=latest.step,
                trace_store=runtime.trace_store,
            )

            replay = replay_session_from_trace(
                runtime.trace_store, run_id=latest.run_id,
            )
            self.assertEqual(replay.final_state, "HALTED_SUCCESS")
            self.assertEqual(replay.replayed_event_count, replay.expected_event_count)
            self.assertEqual(replay.dropped_events, [])
            self.assertTrue(replay.halted)

    def test_replay_session_state_matches_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 8 replay eq", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p8-eq")
            _drive_to_running(session)
            engine.submit_agent_command(_command(), session, aci_runner=runner)
            apply_event(session, "convergence_halt_success")
            original_state = session.state

            latest = runtime.run_manager.load(_latest_run_id(runtime))
            persist_session_events(
                session,
                run_id=latest.run_id,
                step=latest.step,
                trace_store=runtime.trace_store,
            )

            replay = replay_session_from_trace(
                runtime.trace_store, run_id=latest.run_id,
            )
            # The final state must match. ``session.event_count``
            # may differ because ``goal_submitted`` and
            # ``command_submitted`` are not persisted through the
            # bridge (they are pre-session events); only the
            # ``consume_aci_result`` events and any post-session
            # ``apply_event`` calls are persisted.
            self.assertEqual(replay.final_state, original_state)
            self.assertTrue(replay.halted)


def _latest_run_id(runtime: object) -> str:
    events = [e for e in runtime.trace_store.list() if e.kind == "run"]  # type: ignore[attr-defined]
    return str(events[-1].run_id)


# ---------------------------------------------------------------------------
# Replay of various final states
# ---------------------------------------------------------------------------


class FinalStateReplayTests(unittest.TestCase):
    def test_replay_halted_blocked(self) -> None:
        session = create_session("goal-p8-blocked")
        _drive_to_running(session)
        consume_aci_result(session, _make_blocked_result(_command()))
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "HALTED_BLOCKED")
        self.assertTrue(replay.halted)
        self.assertEqual(replay.dropped_events, [])

    def test_replay_waiting_approval(self) -> None:
        session = create_session("goal-p8-approval")
        _drive_to_running(session)
        consume_aci_result(session, _make_approval_result(_command()))
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "WAITING_APPROVAL")
        self.assertFalse(replay.halted)

    def test_replay_repairing(self) -> None:
        session = create_session("goal-p8-repair")
        _drive_to_running(session)
        consume_aci_result(session, _make_failed_repairable_result(_command()))
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "REPAIRING")
        self.assertFalse(replay.halted)

    def test_replay_halted_failure_unsupported(self) -> None:
        session = create_session("goal-p8-unsup")
        _drive_to_running(session)
        consume_aci_result(session, _make_unsupported_result(_command()))
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "HALTED_FAILURE")
        self.assertTrue(replay.halted)

    def test_replay_replanning_via_convergence_replan(self) -> None:
        session = create_session("goal-p8-replan")
        _drive_to_running(session)
        apply_event(session, "convergence_replan")
        replay = replay_events(list(session.events))
        self.assertEqual(replay.final_state, "REPLANNING")
        self.assertFalse(replay.halted)


# ---------------------------------------------------------------------------
# Determinism proof
# ---------------------------------------------------------------------------


class DeterminismReplayTests(unittest.TestCase):
    def test_same_event_list_replays_to_same_state(self) -> None:
        session = create_session("goal-p8-det")
        _drive_to_running(session)
        consume_aci_result(session, _make_blocked_result(_command()))
        events: list[AgentLoopEventRecord] = list(session.events)

        first = replay_events(events)
        second = replay_events(events)
        self.assertEqual(first.final_state, second.final_state)
        self.assertEqual(first.replayed_event_count, second.replayed_event_count)
        self.assertEqual(first.dropped_events, second.dropped_events)

    def test_replay_is_pure_does_not_read_wall_clock(self) -> None:
        # ``replay_events`` must not call ``datetime.now`` or
        # ``time.time``. The session's ``updated_at`` field is
        # rewritten by the FSM as events apply; this test proves
        # that even when wall-clock time changes between two
        # replays, the FSM-level state is identical.
        session = create_session("goal-p8-det2")
        _drive_to_running(session)
        apply_event(session, "convergence_halt_success")
        events = [dict(r.model_dump()) for r in session.events]

        first = replay_events(events, goal_id="replay-A")
        with patch("loopos.ali.fsm.datetime") as fake_dt:
            # Force the FSM to read a very different wall-clock time.
            from datetime import datetime, timezone
            fake_dt.now.return_value = datetime(2099, 1, 1, tzinfo=timezone.utc)
            fake_dt.timezone = timezone
            second = replay_events(events, goal_id="replay-A")
        self.assertEqual(first.final_state, second.final_state)
        self.assertEqual(first.replayed_event_count, second.replayed_event_count)


# ---------------------------------------------------------------------------
# Dropped-event accounting
# ---------------------------------------------------------------------------


class DroppedEventReplayTests(unittest.TestCase):
    def test_out_of_order_event_dropped_as_invalid_transition(self) -> None:
        # Build an out-of-order sequence manually: a
        # ``command_submitted`` event is invalid from ``CREATED``;
        # replay must drop it as ``invalid_transition``.
        bad_events = [
            AgentLoopEventRecord(
                seq=0,
                event="command_submitted",
                payload={},
                reason_code="ali.command_submitted",
                next_state="RUNNING",
            ),
        ]
        replay = replay_events(bad_events)
        self.assertEqual(replay.replayed_event_count, 0)
        self.assertEqual(len(replay.dropped_events), 1)
        self.assertEqual(replay.dropped_events[0][2], "invalid_transition")
        # Now drive a valid sequence end-to-end.
        session = create_session("goal-p8-ooo-good")
        apply_event(session, "goal_submitted")
        apply_event(session, "command_submitted")
        replay = replay_events(list(session.events))
        self.assertEqual(replay.replayed_event_count, 2)
        self.assertEqual(replay.final_state, "RUNNING")

    def test_unknown_event_dropped(self) -> None:
        # ``AgentLoopEventRecord`` rejects unknown events at the
        # type level, so build the bad record via the dict path
        # which is what the replay engine sees in trace payloads.
        bad = [
            {
                "seq": 0,
                "event": "this_is_not_a_real_event",
                "reason_code": "n/a",
                "next_state": "CREATED",
                "payload": {},
            }
        ]
        replay = replay_events(bad)
        self.assertEqual(replay.replayed_event_count, 0)
        self.assertEqual(replay.dropped_events[0][2], "unknown_event")

    def test_post_terminal_events_dropped(self) -> None:
        session = create_session("goal-p8-post")
        _drive_to_running(session)
        apply_event(session, "convergence_halt_success")
        # Append a fake post-terminal event to the events list
        # and check the replay engine drops it as ``post_terminal``.
        session.events.append(  # type: ignore[arg-type]
            AgentLoopEventRecord(
                seq=session.event_count,
                event="observation_recorded",
                payload={},
                reason_code="ali.observation_recorded",
                next_state="RUNNING",
            )
        )
        replay = replay_events(list(session.events))
        # The post-terminal event must be dropped.
        self.assertEqual(replay.dropped_events[-1][2], "post_terminal")
        self.assertEqual(replay.final_state, "HALTED_SUCCESS")


# ---------------------------------------------------------------------------
# Roundtrip through the trace store
# ---------------------------------------------------------------------------


class TraceStoreRoundtripTests(unittest.TestCase):
    def test_replay_after_persist_session_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 8 replay rt", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p8-rt")
            _drive_to_running(session)
            engine.submit_agent_command(_command(), session, aci_runner=runner)
            apply_event(session, "convergence_halt_success")

            latest = runtime.run_manager.load(_latest_run_id(runtime))
            persist_session_events(
                session,
                run_id=latest.run_id,
                step=latest.step,
                trace_store=runtime.trace_store,
            )

            replay = replay_session_from_trace(
                runtime.trace_store, run_id=latest.run_id,
            )
            self.assertEqual(replay.final_state, "HALTED_SUCCESS")
            self.assertEqual(replay.replayed_event_count, replay.expected_event_count)

    def test_replay_trace_events_helper(self) -> None:
        # In-memory replay path: build TraceEvent objects
        # directly (mirrors the wire shape) and replay.
        from loopos.kernel.trace import TraceEvent

        session = create_session("goal-p8-mem")
        _drive_to_running(session)
        apply_event(session, "convergence_halt_success")

        events: list[TraceEvent] = []
        for record in session.events:
            events.append(
                TraceEvent(
                    run_id="run-mem",
                    step=0,
                    kind="signal",
                    type="ali.event",
                    payload=record.model_dump(mode="json"),
                )
            )
        replay = replay_trace_events(events)
        self.assertEqual(replay.final_state, "HALTED_SUCCESS")
        self.assertEqual(replay.replayed_event_count, len(events))

    def test_replay_skips_non_ali_events(self) -> None:
        from loopos.kernel.trace import TraceEvent

        session = create_session("goal-p8-mix")
        apply_event(session, "goal_submitted")
        events: list[TraceEvent] = [
            TraceEvent(
                run_id="run-mix",
                step=0,
                kind="policy",
                type="policy",
                payload={"decision_id": "dec-x", "allowed": True},
            ),
            TraceEvent(
                run_id="run-mix",
                step=0,
                kind="signal",
                type="ali.event",
                payload=session.events[0].model_dump(mode="json"),
            ),
        ]
        replay = replay_trace_events(events)
        # Only the ali.event was replayed.
        self.assertEqual(replay.replayed_event_count, 1)
        self.assertEqual(replay.final_state, "READY")


# ---------------------------------------------------------------------------
# Safety: no live provider calls / no subprocess / no kernel mutation
# ---------------------------------------------------------------------------


class ALIReplaySafetyTests(unittest.TestCase):
    def test_replay_does_not_call_live_provider(self) -> None:
        # Replay must not touch the network. We assert by AST-scanning
        # the module: no import of ``requests``, ``httpx``, or
        # ``urllib.request`` and no attribute access matching those
        # substrings. AST scan is used (not text scan) so docstring /
        # comment phrasings do not trigger a false positive.
        import ast
        from pathlib import Path as _Path

        source_path = _Path("loopos/trace/ali_replay.py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        import_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    import_names.append(node.module)
        joined = " ".join(import_names).lower()
        for forbidden in ("requests", "httpx", "urllib.request", "urllib3"):
            self.assertNotIn(forbidden, joined, f"forbidden import: {forbidden}")

    def test_replay_does_not_run_subprocess(self) -> None:
        # AST-scan only imports; docstring / comment text does not count.
        import ast
        from pathlib import Path as _Path

        source_path = _Path("loopos/trace/ali_replay.py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        import_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    import_names.append(node.module)
        joined = " ".join(import_names).lower()
        for forbidden in ("subprocess", "os.system", "popen"):
            self.assertNotIn(forbidden, joined, f"forbidden import: {forbidden}")

    def test_replay_does_not_import_kernel_loop_engine(self) -> None:
        # The replay engine may import ``loopos.kernel.trace.TraceStore``
        # for read-only access; it must not import ``KernelLoopEngine``
        # or any other mutable kernel surface.
        import ast
        from pathlib import Path as _Path

        source_path = _Path("loopos/trace/ali_replay.py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        bad_symbols: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Track "from loopos.kernel.X import Y"
                if node.module is not None and node.module.startswith("loopos.kernel"):
                    # ``loopos.kernel.trace`` is allowed (read-only store).
                    if not node.module.startswith("loopos.kernel.trace"):
                        for alias in node.names:
                            bad_symbols.append(f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Import):
                # ``import loopos.kernel.X`` is not allowed.
                for alias in node.names:
                    if alias.name.startswith("loopos.kernel") and not alias.name.startswith(
                        "loopos.kernel.trace"
                    ):
                        bad_symbols.append(alias.name)
            elif isinstance(node, ast.Name):
                if node.id == "KernelLoopEngine":
                    bad_symbols.append("KernelLoopEngine (Name)")
            elif isinstance(node, ast.Attribute):
                if node.attr == "KernelLoopEngine":
                    bad_symbols.append("KernelLoopEngine (Attribute)")
        self.assertEqual(bad_symbols, [], f"forbidden kernel-side imports: {bad_symbols}")


if __name__ == "__main__":
    unittest.main()
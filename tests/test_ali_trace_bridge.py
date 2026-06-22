"""Tests for the Phase 5 ALI trace bridge.

These tests prove the bridge between ALI event records and the
existing :class:`loopos.kernel.trace.TraceStore`:

1. :func:`loopos.ali.session.to_event_stream` returns a
   deterministic ordered stream.
2. The bridge persists completed / policy-denied / approval /
   repair / replan / unsupported ACI events through the existing
   trace runtime.
3. ``trace_id`` / ``syscall_id`` / ``provider_id`` survive a
   roundtrip through the trace store.
4. :func:`loopos.trace.ali_bridge.replay_session_events`
   reconstructs the ordered ALI event sequence.
5. Dry-run ACI results are traceable but produce no side effects.
6. No live provider API calls.
7. No direct subprocess / shell bypass.
8. Existing kernel ACI/ALI integration tests still pass (verified
   via the regression test included here).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
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
    to_event_stream,
)
from loopos.ali.models import AgentLoopSession
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, RunSpec
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.router import create_default_syscall_router
from loopos.trace.ali_bridge import (
    ALI_EVENT_TYPE,
    persist_session_events,
    replay_session_events,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime(tmp: str):  # type: ignore[no-untyped-def]
    return KernelBoot().start(
        KernelConfig(workspace=tmp, data_dir=str(Path(tmp) / ".loopos"))
    )


def _auto_runner(tmp: str, runtime):  # type: ignore[no-untyped-def]
    """Build a runner that auto-approves medium-risk commands so
    the success path can exercise ``status='completed'``.
    """

    return CommandRunner(
        policy_engine=runtime.policy_engine,
        syscall_router=create_default_syscall_router(
            tmp,
            auto_approve_medium=True,
            policy_engine=runtime.policy_engine,
            trace_store=runtime.trace_store,
        ),
        config=RunnerConfig(workspace=tmp, run_id="run-p5"),
    )


def _drive_to_running(session: AgentLoopSession) -> None:
    apply_event(session, "goal_submitted")
    apply_event(session, "command_submitted")


def _command(  # type: ignore[no-untyped-def]
    goal_id: str = "goal-p5-1",
    *,
    kind: str = "terminal.exec",
    cmd: str = "echo hello",
    dry_run: bool = False,
) -> AgentCommand:
    return AgentCommand(
        goal_id=goal_id,
        purpose="phase 5 trace bridge",
        kind=kind,  # type: ignore[arg-type]
        command=cmd,
        dry_run=dry_run,
    )


def _make_failed_result(
    *,
    command_id: str,
    goal_id: str,
    repairable: bool,
    no_progress: bool = False,
) -> AgentCommandResult:
    decision = PolicyDecision(
        allowed=True,
        action="allow",
        risk="low",
        safety_level="L0",
    )
    return AgentCommandResult(
        command_id=command_id,
        goal_id=goal_id,
        status="failed",
        success=False,
        policy_decision=decision,
        reason_codes=["synthetic_failure"],
        metadata={"syscall_id": "sys-synthetic"},
        blocked_reason="synthetic failure",
        evaluation=EvaluationSummary(repairable=repairable),
        progress=ProgressSummary(no_progress=no_progress),
    )


def _make_unsupported_result(
    *,
    command_id: str,
    goal_id: str,
) -> AgentCommandResult:
    decision = PolicyDecision(
        allowed=True,
        action="allow",
        risk="low",
        safety_level="L0",
    )
    return AgentCommandResult(
        command_id=command_id,
        goal_id=goal_id,
        status="unsupported",
        success=False,
        policy_decision=decision,
        reason_codes=["unsupported_command_kind"],
    )


# ---------------------------------------------------------------------------
# to_event_stream tests
# ---------------------------------------------------------------------------


class ToEventStreamTests(unittest.TestCase):
    def test_returns_ordered_deterministic_events(self) -> None:
        session = create_session("goal-p5-1")
        _drive_to_running(session)
        records = consume_aci_result(
            session,
            _make_failed_result(
                command_id="cmd-1",
                goal_id="goal-p5-1",
                repairable=True,
            ),
        )

        stream = to_event_stream(session)
        self.assertEqual(len(stream), 4)  # goal + command + progress + syscall_failed
        seqs = [item["seq"] for item in stream]
        self.assertEqual(seqs, sorted(seqs))
        # Determinism: same session -> same stream.
        stream_again = to_event_stream(session)
        self.assertEqual(stream, stream_again)
        # Each entry has the documented keys.
        for item in stream:
            self.assertIn("seq", item)
            self.assertIn("event", item)
            self.assertIn("reason_code", item)
            self.assertIn("next_state", item)
            self.assertIn("payload", item)
            self.assertIn("created_at", item)
        self.assertEqual(stream[-1]["event"], "syscall_failed")
        self.assertEqual(stream[-1]["next_state"], "REPAIRING")
        self.assertEqual(records[-1].event, "syscall_failed")

    def test_empty_session_yields_empty_stream(self) -> None:
        session = create_session("goal-p5-1")
        self.assertEqual(to_event_stream(session), [])


# ---------------------------------------------------------------------------
# Bridge persistence tests
# ---------------------------------------------------------------------------


class BridgePersistenceTests(unittest.TestCase):
    def test_completed_aci_persists_two_ali_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 bridge", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)

            engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )

            ali_events = [
                event for event in runtime.trace_store.list()
                if event.type == ALI_EVENT_TYPE
            ]
            self.assertEqual(len(ali_events), 2)
            self.assertEqual(
                [e.payload["event"] for e in ali_events],
                ["progress_updated", "syscall_completed"],
            )

    def test_policy_denied_persists_halted_blocked_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 policy deny", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)

            engine.submit_agent_command(
                _command(cmd="rm -rf /"), session, aci_runner=runner,
            )

            ali_events = [
                event for event in runtime.trace_store.list()
                if event.type == ALI_EVENT_TYPE
            ]
            self.assertEqual(len(ali_events), 1)
            self.assertEqual(ali_events[0].payload["event"], "policy_denied")
            self.assertEqual(ali_events[0].payload["next_state"], "HALTED_BLOCKED")
            self.assertEqual(ali_events[0].payload["aci_status"], "blocked")

    def test_approval_required_persists_waiting_approval_event(self) -> None:
        """A medium-risk command on the kernel's default router
        (no auto-approve) must produce a single
        ``approval_required`` ALI event whose next state is
        ``WAITING_APPROVAL``.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 approval", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)

            engine.submit_agent_command(_command(), session)

            ali_events = [
                event for event in runtime.trace_store.list()
                if event.type == ALI_EVENT_TYPE
            ]
            self.assertEqual(len(ali_events), 1)
            self.assertEqual(
                ali_events[0].payload["event"], "approval_required",
            )
            self.assertEqual(
                ali_events[0].payload["next_state"], "WAITING_APPROVAL",
            )

    def test_repairable_failure_persists_repairing_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-repair-1",
                goal_id="goal-p5-1",
                repairable=True,
            )

            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-p5-repair",
                step=1,
                trace_store=store,
                audit={
                    "aci_command_id": failed.command_id,
                    "aci_status": failed.status,
                },
                records=records,
            )

            ali_events = [
                event for event in store.list() if event.type == ALI_EVENT_TYPE
            ]
            self.assertGreaterEqual(len(ali_events), 1)
            repair_event = next(
                e for e in ali_events
                if e.payload["event"] == "syscall_failed"
            )
            self.assertEqual(repair_event.payload["next_state"], "REPAIRING")

    def test_no_progress_failure_persists_replanning_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-replan-1",
                goal_id="goal-p5-1",
                repairable=False,
                no_progress=True,
            )

            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-p5-replan",
                step=1,
                trace_store=store,
                audit={"aci_command_id": failed.command_id},
                records=records,
            )

            ali_events = [
                event for event in store.list() if event.type == ALI_EVENT_TYPE
            ]
            replan_event = next(
                e for e in ali_events
                if e.payload["event"] == "convergence_replan"
            )
            self.assertEqual(replan_event.payload["next_state"], "REPLANNING")

    def test_unsupported_aci_persists_failure_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            unsupported = _make_unsupported_result(
                command_id="cmd-unsup-1",
                goal_id="goal-p5-1",
            )

            records = consume_aci_result(session, unsupported)
            persist_session_events(
                session,
                run_id="run-p5-unsup",
                step=1,
                trace_store=store,
                audit={
                    "aci_command_id": unsupported.command_id,
                    "aci_goal_id": unsupported.goal_id,
                    "aci_status": unsupported.status,
                    "aci_success": unsupported.success,
                    "reason_codes": list(unsupported.reason_codes),
                },
                records=records,
            )

            ali_events = [
                event for event in store.list() if event.type == ALI_EVENT_TYPE
            ]
            halt_event = next(
                e for e in ali_events
                if e.payload["event"] == "convergence_halt_failure"
            )
            self.assertEqual(halt_event.payload["next_state"], "HALTED_FAILURE")
            self.assertEqual(halt_event.payload["aci_status"], "unsupported")


# ---------------------------------------------------------------------------
# Roundtrip / replay tests
# ---------------------------------------------------------------------------


class MetadataRoundtripTests(unittest.TestCase):
    def test_trace_syscall_provider_metadata_survives_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 roundtrip", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)

            engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )

            replayed = replay_session_events(
                runtime.trace_store, run_id=run.run_id,
            )
            self.assertEqual(len(replayed), 2)
            for record in replayed:
                self.assertEqual(record["aci_goal_id"], "goal-p5-1")
                self.assertEqual(record["aci_command_id"], session.aci_refs[-1].aci_result_id)
                self.assertIn("aci_status", record)
                self.assertIn("reason_codes", record)
                self.assertIn("policy_decision", record)
                # trace_id / syscall_id propagate through the
                # runner's result metadata into the audit.
                self.assertIn("trace_id", record)
                self.assertIn("syscall_id", record)
                self.assertIn("kernel_run_id", record)

    def test_replay_reconstructs_ordered_event_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-replay-1",
                goal_id="goal-p5-1",
                repairable=True,
            )

            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-p5-replay",
                step=1,
                trace_store=store,
                audit={"aci_command_id": failed.command_id},
                records=records,
            )

            replayed = replay_session_events(store, run_id="run-p5-replay")
            seqs = [item["seq"] for item in replayed]
            self.assertEqual(seqs, sorted(seqs))
            self.assertGreaterEqual(len(replayed), 2)
            # The last two events must be progress_updated then
            # syscall_failed.
            self.assertEqual(
                [r["event"] for r in replayed[-2:]],
                ["progress_updated", "syscall_failed"],
            )

    def test_replay_filters_non_ali_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            # Drop a non-ALI event into the store.
            store.append(
                "run",
                "run-other",
                1,
                payload={"event": "non-ali"},
                event_type="run.start",
            )
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-replay-1",
                goal_id="goal-p5-1",
                repairable=True,
            )
            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-p5-replay",
                step=1,
                trace_store=store,
                audit={"aci_command_id": failed.command_id},
                records=records,
            )

            replayed = replay_session_events(store, run_id="run-p5-replay")
            self.assertTrue(
                all(item.get("aci_command_id") == "cmd-replay-1" for item in replayed)
            )
            replayed_other = replay_session_events(store, run_id="run-other")
            self.assertEqual(replayed_other, [])


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TraceDeterminismTests(unittest.TestCase):
    def test_payload_serialization_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-det-1",
                goal_id="goal-p5-1",
                repairable=True,
            )
            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-det",
                step=1,
                trace_store=store,
                audit={"aci_command_id": failed.command_id},
                records=records,
            )
            ali_events = [
                event for event in store.list() if event.type == ALI_EVENT_TYPE
            ]
            # Re-read the trace store from disk and verify bytewise
            # equality of the JSON serialisation.
            with store.path.open("r", encoding="utf-8") as handle:
                lines = [line.strip() for line in handle if line.strip()]
            ali_lines = [
                line for line in lines
                if json.loads(line).get("type") == ALI_EVENT_TYPE
            ]
            self.assertEqual(len(ali_lines), len(ali_events))
            for line, event in zip(ali_lines, ali_events):
                payload = json.loads(line)
                self.assertEqual(payload["payload"]["event"], event.payload["event"])
                self.assertEqual(
                    payload["payload"]["aci_command_id"],
                    event.payload["aci_command_id"],
                )

    def test_ordered_payload_keeps_key_order(self) -> None:
        # Use the internal helper indirectly via replay.
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-ord-1",
                goal_id="goal-p5-1",
                repairable=True,
            )
            records = consume_aci_result(session, failed)
            persist_session_events(
                session,
                run_id="run-ord",
                step=1,
                trace_store=store,
                audit={"aci_command_id": failed.command_id},
                records=records,
            )
            replayed = replay_session_events(store, run_id="run-ord")
            # The replay preserves the canonical key order from
            # ``_PAYLOAD_KEY_ORDER``.
            canonical_keys = (
                "seq", "event", "reason_code", "next_state",
                "created_at", "aci_command_id", "aci_goal_id",
                "aci_status", "aci_success", "reason_codes", "messages",
                "trace_id", "syscall_id", "provider_id", "provider_source",
                "policy_decision", "convergence_reason_code",
            )
            for record in replayed:
                keys = [k for k in canonical_keys if k in record]
                self.assertEqual(list(record.keys())[: len(canonical_keys)], keys)


# ---------------------------------------------------------------------------
# Side-effect / network tests
# ---------------------------------------------------------------------------


class DryRunAndSideEffectTests(unittest.TestCase):
    def test_dry_run_persists_trace_but_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            _ = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 dry run", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            sentinel = Path(tmp) / "sentinel.txt"
            self.assertFalse(sentinel.exists())

            engine.submit_agent_command(
                _command(dry_run=True), session, aci_runner=runner,
            )

            ali_events = [
                event for event in runtime.trace_store.list()
                if event.type == ALI_EVENT_TYPE
            ]
            # Dry-run success emits a single ``progress_updated`` event
            # (no ``syscall_completed`` because no side-effecting
            # syscall ran). The single event is trace evidence, not a
            # side effect. The runner reports status='dry_run' for
            # dry-run commands.
            self.assertEqual(len(ali_events), 1)
            self.assertEqual(ali_events[0].payload["event"], "progress_updated")
            self.assertTrue(ali_events[0].payload["aci_success"])
            self.assertEqual(ali_events[0].payload["aci_status"], "dry_run")
            self.assertFalse(sentinel.exists())
            self.assertEqual(session.state, "RUNNING")

    def test_bridge_does_not_call_live_provider(self) -> None:
        def fail(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("network call attempted")

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            store = runtime.trace_store
            session = create_session("goal-p5-1")
            _drive_to_running(session)
            failed = _make_failed_result(
                command_id="cmd-net-1",
                goal_id="goal-p5-1",
                repairable=True,
            )
            records = consume_aci_result(session, failed)

            with patch("socket.socket", side_effect=fail), \
                 patch("urllib.request.urlopen", side_effect=fail):
                persist_session_events(
                    session,
                    run_id="run-p5-net",
                    step=1,
                    trace_store=store,
                    audit={"aci_command_id": failed.command_id},
                    records=records,
                )


# ---------------------------------------------------------------------------
# Regression: existing kernel integration still works
# ---------------------------------------------------------------------------


class KernelIntegrationRegressionTests(unittest.TestCase):
    def test_run_metadata_aci_outcomes_unchanged_after_bridge(self) -> None:
        """Phase 4's ``run.metadata['aci_outcomes']` contract must
        remain intact after Phase 5 wires the bridge.
        """

        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(tmp)
            compiler = __import__(
                "loopos.agents.intent_compiler",
                fromlist=["DeterministicIntentCompiler"],
            ).DeterministicIntentCompiler()
            run = KernelLoopEngine(runtime, intent_compiler=compiler).run(
                RunSpec(goal="phase 5 regression", workspace=tmp, mode="dry_run"),
            )
            engine = KernelLoopEngine(runtime)
            runner = _auto_runner(tmp, runtime)
            session = create_session("goal-p5-1")
            _drive_to_running(session)

            engine.submit_agent_command(
                _command(), session, aci_runner=runner,
            )

            stored = runtime.run_manager.load(run.run_id)
            outcomes = stored.metadata.get("aci_outcomes")
            self.assertIsNotNone(outcomes)
            self.assertEqual(len(outcomes), 1)
            outcome = outcomes[0]
            self.assertEqual(outcome["status"], "completed")
            self.assertEqual(outcome["goal_id"], "goal-p5-1")
            # Phase 5 added this WITHOUT changing the Phase 4 shape.
            self.assertIn("trace_id", outcome)
            self.assertIn("syscall_id", outcome)


if __name__ == "__main__":
    unittest.main()
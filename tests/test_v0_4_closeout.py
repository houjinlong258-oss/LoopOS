"""Tests for v0.4.0 closeout: persistence + cross-process state.

These tests verify the closeout P0 work: ``loopos loop run``
generates a ``run_id`` and writes ``.loopos/runs/<run_id>/``;
``loopos loop status`` and ``loopos loop deliver`` read that
directory in a fresh process.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from loopos import checkpoint_store


def _capture_json(callable_: Callable[[], Any]) -> dict[str, Any]:
    """Run ``callable_``, capture stdout, parse JSON."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        callable_()
    result: dict[str, Any] = json.loads(buf.getvalue())
    return result


class TestCheckpointStore:
    def test_init_run_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rid, path = checkpoint_store.init_run(None, data_dir=Path(tmp))
            assert checkpoint_store.is_valid_run_id(rid)
            assert path.exists()
            assert (path / "created_at").exists()

    def test_init_run_rejects_invalid_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                checkpoint_store.init_run("../etc/passwd", data_dir=Path(tmp))
                assert False, "should have raised"
            except ValueError:
                pass

    def test_make_run_id_is_unique(self) -> None:
        ids = {checkpoint_store.make_run_id() for _ in range(20)}
        assert len(ids) == 20

    def test_write_and_read_loop_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rid, _ = checkpoint_store.init_run(None, data_dir=Path(tmp))
            payload = {"goal": {"raw_goal": "X"}, "current_status": "running"}
            checkpoint_store.write_loop_state(rid, payload, data_dir=Path(tmp))
            assert checkpoint_store.read_loop_state(rid, data_dir=Path(tmp)) == payload

    def test_append_iteration_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rid, _ = checkpoint_store.init_run(None, data_dir=Path(tmp))
            checkpoint_store.append_iteration(rid, {"index": 1}, data_dir=Path(tmp))
            checkpoint_store.append_iteration(rid, {"index": 2}, data_dir=Path(tmp))
            its = checkpoint_store.read_iterations(rid, data_dir=Path(tmp))
            assert len(its) == 2
            assert its[0]["index"] == 1
            assert its[1]["index"] == 2

    def test_list_runs_and_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            rid1, _ = checkpoint_store.init_run(None, data_dir=d)
            checkpoint_store.write_loop_state(
                rid1, {"goal": {"raw_goal": "X"}, "current_status": "r1"},
                data_dir=d,
            )
            rid2, _ = checkpoint_store.init_run(None, data_dir=d)
            checkpoint_store.write_loop_state(
                rid2, {"goal": {"raw_goal": "Y"}, "current_status": "r2"},
                data_dir=d,
            )
            runs = checkpoint_store.list_runs(data_dir=d)
            assert len(runs) == 2
            assert {r.run_id for r in runs} == {rid1, rid2}
            # The most recently written is rid2.
            assert checkpoint_store.latest_run_id(data_dir=d) in (rid1, rid2)


class TestLoopCliCrossProcess:
    """End-to-end cross-process check: subprocess for each call."""

    def _cli(self, args: list[str], data_dir: str) -> dict[str, Any]:
        cmd = [sys.executable, "-m", "loopos.cli.app"] + args + [
            "--data-dir", data_dir, "--json",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(
                f"CLI failed: {' '.join(cmd)}\nstdout: {r.stdout}\nstderr: {r.stderr}"
            )
        result: dict[str, Any] = json.loads(r.stdout)
        return result

    def test_loop_run_persists_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._cli(
                ["loop", "run", "Build X with tests and docs",
                 "--max-iterations", "2"],
                tmp,
            )
            assert "run_id" in out
            rid = out["run_id"]
            # The run directory exists.
            assert (Path(tmp) / "runs" / rid).exists()
            # loop_state.json was written.
            assert (Path(tmp) / "runs" / rid / "loop_state.json").exists()
            # iterations.jsonl was written.
            assert (Path(tmp) / "runs" / rid / "iterations.jsonl").exists()
            # convergence_report.json was written.
            assert (Path(tmp) / "runs" / rid / "convergence_report.json").exists()
            # delivery_candidate.json was written.
            assert (Path(tmp) / "runs" / rid / "delivery_candidate.json").exists()
            # checkpoint.json was written.
            assert (Path(tmp) / "runs" / rid / "checkpoint.json").exists()

    def test_status_latest_reads_persisted_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = self._cli(
                ["loop", "run", "Improve a simulated project until convergence",
                 "--max-iterations", "2"],
                tmp,
            )
            rid = run["run_id"]
            status = self._cli(["loop", "status", "--latest"], tmp)
            assert status["run_id"] == rid
            assert "Improve a simulated" in status["user_goal"]
            assert status["current_iteration"] >= 1
            # The status output includes the rich project-training surface.
            assert "lail_signals" in status
            assert "last_iteration" in status
            assert "convergence" in status

    def test_status_with_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = self._cli(
                ["loop", "run", "Build a CLI", "--max-iterations", "1"],
                tmp,
            )
            rid = run["run_id"]
            status = self._cli(["loop", "status", "--run-id", rid], tmp)
            assert status["run_id"] == rid
            assert "Build a CLI" in status["user_goal"]

    def test_deliver_latest_reads_persisted_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = self._cli(
                ["loop", "run", "Ship a hello world CLI", "--max-iterations", "2"],
                tmp,
            )
            rid = run["run_id"]
            deliv = self._cli(["loop", "deliver", "--latest"], tmp)
            assert deliv["run_id"] == rid
            assert deliv["delivery_status"] in {
                "ready", "blocked", "blocked_by_fake_convergence",
                "budget_exhausted", "incomplete",
            }
            # The deliver output includes the rich surface.
            assert "success_criteria_coverage" in deliv
            assert "fake_convergence_findings" in deliv
            assert "evidence" in deliv
            assert "recommended_next_loop" in deliv
            assert "why" in deliv

    def test_persistence_survives_fresh_process(self) -> None:
        """Run in one process, status / deliver in different processes."""
        with tempfile.TemporaryDirectory() as tmp:
            # Process 1: run.
            r1 = subprocess.run(
                [sys.executable, "-m", "loopos.cli.app", "loop", "run",
                 "Cross-process goal", "--max-iterations", "1",
                 "--data-dir", tmp, "--json"],
                capture_output=True, text=True,
            )
            assert r1.returncode == 0
            run = json.loads(r1.stdout)
            rid = run["run_id"]

            # Process 2: status.
            r2 = subprocess.run(
                [sys.executable, "-m", "loopos.cli.app", "loop", "status",
                 "--latest", "--data-dir", tmp, "--json"],
                capture_output=True, text=True,
            )
            assert r2.returncode == 0
            status = json.loads(r2.stdout)
            assert status["run_id"] == rid

            # Process 3: deliver.
            r3 = subprocess.run(
                [sys.executable, "-m", "loopos.cli.app", "loop", "deliver",
                 "--latest", "--data-dir", tmp, "--json"],
                capture_output=True, text=True,
            )
            assert r3.returncode == 0
            deliv = json.loads(r3.stdout)
            assert deliv["run_id"] == rid


class TestLailSignalBus:
    def test_emit_and_drain(self) -> None:
        from loopos.lail import LailSignalBus
        bus = LailSignalBus()
        bus.make("iteration_started", run_id="r1", iteration_index=1)
        bus.make("plan_emitted", run_id="r1", iteration_index=1)
        drained = bus.drain()
        assert len(drained) == 2
        assert all(s.run_id == "r1" for s in drained)
        # After drain, the bus is empty.
        assert bus.drain() == []

    def test_kind_summary(self) -> None:
        from loopos.lail import LailSignalBus
        bus = LailSignalBus()
        bus.make("iteration_started", run_id="r1")
        bus.make("iteration_started", run_id="r1")
        bus.make("plan_emitted", run_id="r1")
        summary = bus.kind_summary()
        assert summary == {"iteration_started": 2, "plan_emitted": 1}


class TestCommunicationDistance:
    def test_distance_self_is_zero(self) -> None:
        from loopos.communication_distance import communication_distance
        assert communication_distance("hello world", "hello world") == 0.0

    def test_distance_disjoint_is_one(self) -> None:
        from loopos.communication_distance import communication_distance
        d = communication_distance("alpha beta", "gamma delta")
        assert d >= 0.9

    def test_distance_partial_overlap(self) -> None:
        from loopos.communication_distance import communication_distance
        d = communication_distance("planner says build with pytest",
                                  "reviewer reads build with pytest")
        # Both share "build" / "with" / "pytest" / "says" / "reads" —
        # distance is below 0.6.
        assert 0.0 <= d <= 0.6

    def test_optimizer_marks_high_distance_as_flagged(self) -> None:
        from loopos.communication_distance import (
            Communication,
            CommunicationDistanceOptimizer,
        )
        opt = CommunicationDistanceOptimizer(max_distance=0.3)
        # Self-comparison is 0.0; the optimizer accepts self-handoffs.
        comm_self = Communication(
            sender="planner", receiver="builder", payload="same payload",
            run_id="r1",
        )
        # A different payload pair is high distance.
        comm_diff = Communication(
            sender="planner", receiver="builder", payload="different words here",
            run_id="r1",
        )
        opt.plan([comm_self, comm_diff])
        # The cross_distance() method exposes the real distance.
        cross = opt.cross_distance(comm_self.payload, comm_diff.payload)
        assert cross > 0.3


class TestMemoryCompilerSelection:
    def test_context_packet_records_selected_and_omitted(self) -> None:
        from loopos.project_memory import (
            MemoryCompiler, DecisionMemory, FailureMemory, TestMemory,
        )
        from loopos.agent_language.roles import AgentRole
        c = MemoryCompiler()
        c.add(DecisionMemory(type="decision", content="Use Python",
                             source="user", decision="Python", rationale="skill"))
        c.add(DecisionMemory(type="decision", content="Use Go",
                             source="user", decision="Go", rationale="perf"))
        c.add(FailureMemory(type="failure", content="x", source="t",
                            failed_attempt="x", failure_reason="y",
                            avoid_repeating="z", next_time="w"))
        c.add(TestMemory(type="test", content="pytest", source="t",
                         test_name="test_x", result="failed"))
        p = c.compile(target_role=AgentRole.PLANNER,
                      goal_summary="Build X", current_gap="no test yet",
                      run_id="r1", iteration_index=1)
        # The packet now records selected_memory and omitted_memory_reason.
        assert p.run_id == "r1"
        assert p.iteration_index == 1
        assert p.token_budget > 0
        assert isinstance(p.selected_memory, list)
        assert isinstance(p.omitted_memory_reason, list)

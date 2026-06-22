"""Tests for Fusion Router trace integration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from loopos.fusion_router.models import (
    FusionPlan,
    FusionTaskProfile,
    FusionTrigger,
    ModelCapabilityProfile,
)
from loopos.fusion_router.router import FusionRouter
from loopos.fusion_router.trace import (
    FUSION_PLAN_EVENT_TYPE,
    FUSION_VERDICT_EVENT_TYPE,
    record_fusion_plan,
    record_fusion_verdict,
    replay_fusion_plans,
    replay_fusion_verdicts,
)
from loopos.kernel.trace import TraceStore


def _router() -> FusionRouter:
    return FusionRouter(
        profiles=[
            ModelCapabilityProfile(
                provider_id="local", model_id="local",
                reasoning_score=5, coding_score=5, review_score=5,
            ),
        ],
    )


def _plan() -> "FusionPlan":
    task = FusionTaskProfile(
        title="refactor auth", task_type="refactor", complexity_score=8,
    )
    trigger = FusionTrigger(source="user", reason="large_refactor")
    return _router().plan(task, trigger)


class FusionTracePersistenceTests(unittest.TestCase):
    def test_fusion_plan_recorded_as_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp) / "events.jsonl")
            plan = _plan()
            event = record_fusion_plan(
                plan, run_id="run-p6", step=1, trace_store=store,
            )
            self.assertEqual(event.kind, "signal")
            self.assertEqual(event.type, FUSION_PLAN_EVENT_TYPE)
            self.assertEqual(event.payload["fusion_id"], plan.fusion_id)
            self.assertEqual(event.payload["mode"], plan.mode)
            self.assertEqual(event.payload["fusion_score"], plan.fusion_score)

    def test_fusion_verdict_recorded_as_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp) / "events.jsonl")
            plan = _plan()
            verdict = _router().create_verdict(
                plan, status="accepted", confidence=0.9,
                risks=["model mismatch"], reason_codes=["trace_id"],
                trace_ids=["trace-1"],
            )
            event = record_fusion_verdict(
                verdict, run_id="run-p6", step=2, trace_store=store,
            )
            self.assertEqual(event.type, FUSION_VERDICT_EVENT_TYPE)
            self.assertEqual(event.payload["status"], "accepted")

    def test_replay_reconstructs_fusion_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp) / "events.jsonl")
            plan_a = _plan()
            plan_b = _plan()
            record_fusion_plan(
                plan_a, run_id="run-p6", step=1, trace_store=store,
            )
            record_fusion_plan(
                plan_b, run_id="run-p6", step=2, trace_store=store,
            )
            replayed = replay_fusion_plans(store, run_id="run-p6")
            self.assertEqual(len(replayed), 2)
            self.assertEqual(
                {item["fusion_id"] for item in replayed},
                {plan_a.fusion_id, plan_b.fusion_id},
            )

    def test_replay_filters_non_fusion_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp) / "events.jsonl")
            store.append(
                "signal", run_id="run-p6", step=0,
                payload={"x": 1}, event_type="other.signal",
            )
            plan = _plan()
            record_fusion_plan(
                plan, run_id="run-p6", step=1, trace_store=store,
            )
            replayed = replay_fusion_plans(store, run_id="run-p6")
            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0]["fusion_id"], plan.fusion_id)

    def test_replay_verdicts_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(Path(tmp) / "events.jsonl")
            plan = _plan()
            verdict = _router().create_verdict(
                plan, status="needs_repair", confidence=0.4,
            )
            record_fusion_verdict(
                verdict, run_id="run-p6", step=3, trace_store=store,
            )
            replayed = replay_fusion_verdicts(store, run_id="run-p6")
            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0]["status"], "needs_repair")
            self.assertEqual(replayed[0]["confidence"], 0.4)


if __name__ == "__main__":
    unittest.main()
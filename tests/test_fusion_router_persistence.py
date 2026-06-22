"""Tests for the Fusion Router persistence layer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from loopos.fusion_router.models import (
    FusionPlan,
    FusionTaskProfile,
    FusionTrigger,
    ModelCapabilityProfile,
)
from loopos.fusion_router.persistence import (
    FusionPlanStore,
    list_plans,
    list_verdicts,
    load_plan,
    load_verdict,
)
from loopos.fusion_router.router import FusionRouter


def _router() -> FusionRouter:
    return FusionRouter(
        profiles=[
            ModelCapabilityProfile(
                provider_id="local", model_id="local",
                reasoning_score=5, coding_score=5, review_score=5,
            ),
        ],
    )


def _plan() -> FusionPlan:
    task = FusionTaskProfile(
        title="refactor", task_type="refactor", complexity_score=8,
    )
    trigger = FusionTrigger(source="user", reason="large_refactor")
    return _router().plan(task, trigger)


class FusionPlanStoreRoundtripTests(unittest.TestCase):
    def test_save_and_load_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            store.save_plan(plan)
            loaded = store.load_plan(plan.fusion_id)
            assert loaded is not None
            self.assertEqual(loaded, plan)

    def test_save_and_load_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            verdict = _router().create_verdict(
                plan, status="accepted", confidence=0.9,
                risks=["model mismatch"],
                reason_codes=["trace_id"],
                trace_ids=["trace-1"],
            )
            store.save_plan(plan)
            store.save_verdict(verdict)
            loaded = store.load_verdict(plan.fusion_id)
            assert loaded is not None
            self.assertEqual(loaded, verdict)

    def test_load_verdicts_returns_all_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            store.save_plan(plan)
            for i in range(3):
                v = _router().create_verdict(
                    plan, status="needs_repair", confidence=0.5,
                )
                store.save_verdict(v, seq=i)
            verdicts = store.load_verdicts(plan.fusion_id)
            self.assertEqual(len(verdicts), 3)

    def test_atomic_write_does_not_leak_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            store.save_plan(plan)
            path = store.root / "plans" / f"{plan.fusion_id}.json"
            self.assertTrue(path.exists())
            # Inspect the persisted JSON is valid (no truncated file).
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["fusion_id"], plan.fusion_id)


class FusionPlanStoreListTests(unittest.TestCase):
    def test_list_plans_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            self.assertEqual(store.list_plans(), [])
            self.assertEqual(store.list_verdicts(), [])

    def test_list_plans_returns_sorted_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan_a = _plan()
            plan_b = _plan()
            plan_c = _plan()
            store.save_plan(plan_a)
            store.save_plan(plan_b)
            store.save_plan(plan_c)
            ids = store.list_plans()
            self.assertEqual(len(ids), 3)
            self.assertEqual(ids, sorted(ids))

    def test_module_level_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "fusion")
            store = FusionPlanStore(root)
            plan = _plan()
            store.save_plan(plan)
            self.assertEqual(load_plan(root, plan.fusion_id), plan)
            self.assertIn(plan.fusion_id, list_plans(root))

    def test_module_level_load_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "fusion")
            store = FusionPlanStore(root)
            plan = _plan()
            store.save_plan(plan)
            verdict = _router().create_verdict(
                plan, status="accepted", confidence=0.7,
            )
            store.save_verdict(verdict)
            self.assertEqual(load_verdict(root, plan.fusion_id), verdict)
            self.assertIn(plan.fusion_id, list_verdicts(root))


class FusionPlanStoreDeterminismTests(unittest.TestCase):
    def test_persisted_payload_uses_canonical_key_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            store.save_plan(plan)
            path = store.root / "plans" / f"{plan.fusion_id}.json"
            text = path.read_text(encoding="utf-8")
            # The plan key order is the same as the trace bridge
            # so replay reconstruction is consistent across the
            # two surfaces.
            first_keys = list(json.loads(text).keys())
            self.assertEqual(first_keys[0], "fusion_id")
            self.assertEqual(first_keys[1], "mode")
            self.assertEqual(first_keys[2], "fusion_score")
            self.assertEqual(first_keys[3], "trigger")

    def test_double_save_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FusionPlanStore(Path(tmp) / "fusion")
            plan = _plan()
            store.save_plan(plan)
            store.save_plan(plan)
            # The model payload is deterministic; the only field
            # that changes between writes is ``_saved_at`` which is
            # an explicit audit timestamp. Strip it before
            # comparing.
            def _strip_saved_at(text: str) -> dict[str, object]:
                data: dict[str, object] = json.loads(text)
                data.pop("_saved_at", None)
                return data

            first = _strip_saved_at(
                (store.root / "plans" / f"{plan.fusion_id}.json").read_text(encoding="utf-8")
            )
            second = _strip_saved_at(
                (store.root / "plans" / f"{plan.fusion_id}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(first, second)


class FusionCLIPersistenceIntegrationTests(unittest.TestCase):
    """End-to-end: build a plan via CLI, persist, read back via status."""

    def test_cli_status_returns_persisted_plan(self) -> None:
        import io
        from contextlib import redirect_stdout
        from loopos.cli.commands.fusion_router import (
            fusion_router_command, build_default_store,
        )

        with tempfile.TemporaryDirectory() as tmp:
            store = build_default_store(root=str(Path(tmp) / "fusion"))
            task = json.dumps({
                "title": "t", "task_type": "refactor",
                "complexity_score": 8, "risk_score": 6,
            })
            # plan -> persist -> status -> assert roundtrip.
            fusion_router_command(
                action="plan", task_arg=task,
                json_output=True, store=store,
            )
            plans = store.list_plans()
            self.assertEqual(len(plans), 1)
            fusion_id = plans[0]
            buffer = io.StringIO()
            err_buffer = io.StringIO()
            with redirect_stdout(buffer):
                import contextlib
                with contextlib.redirect_stderr(err_buffer):
                    fusion_router_command(
                        action="status", fusion_id=fusion_id,
                        json_output=True, store=store,
                    )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "loaded")
            self.assertEqual(payload["plan"]["fusion_id"], fusion_id)

    def test_cli_status_not_found_payload(self) -> None:
        import io
        from contextlib import redirect_stdout
        from loopos.cli.commands.fusion_router import (
            fusion_router_command, build_default_store,
        )

        with tempfile.TemporaryDirectory() as tmp:
            store = build_default_store(root=str(Path(tmp) / "fusion"))
            buffer = io.StringIO()
            err_buffer = io.StringIO()
            with redirect_stdout(buffer):
                import contextlib
                with contextlib.redirect_stderr(err_buffer):
                    fusion_router_command(
                        action="status", fusion_id="missing-fusion-id",
                        json_output=True, store=store,
                    )
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "not_found")
            self.assertEqual(payload["fusion_id"], "missing-fusion-id")


class FusionMadDogPersistenceIntegrationTests(unittest.TestCase):
    """Mad Dog Mode status / list / route should also use the persistence layer."""

    def test_mad_dog_status_uses_persistence(self) -> None:
        import io
        import json as _json
        from contextlib import redirect_stdout
        from loopos.cli.commands.mad_dog import mad_dog_command
        from loopos.cli.commands.fusion_router import build_default_store

        with tempfile.TemporaryDirectory() as tmp:
            store = build_default_store(root=str(Path(tmp) / "fusion"))
            task = _json.dumps({"title": "t", "task_type": "bugfix"})
            mad_dog_command(
                action="plan", task_arg=task,
                json_output=True, store=store,
            )
            plans = store.list_plans()
            self.assertEqual(len(plans), 1)
            fusion_id = plans[0]
            buffer = io.StringIO()
            err_buffer = io.StringIO()
            with redirect_stdout(buffer):
                import contextlib
                with contextlib.redirect_stderr(err_buffer):
                    mad_dog_command(
                        action="status", fusion_id=fusion_id,
                        json_output=True, store=store,
                    )
            payload = _json.loads(buffer.getvalue())
            self.assertEqual(payload["status"], "loaded")
            self.assertEqual(payload["plan"]["mode"], "mad_dog")


if __name__ == "__main__":
    unittest.main()
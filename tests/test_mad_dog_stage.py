"""Tests for the v0.4.x Mad Dog stage classification."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loopos.fusion_optimizer.mad_dog import (  # noqa: E402
    MadDogFinding,
    resolve_stage,
)


class TestResolveStage:
    """The pure function: stage = f(blocks_delivery, severity)."""

    def test_block_now_when_blocks_delivery(self) -> None:
        assert resolve_stage(True, "info") == "block_now"
        assert resolve_stage(True, "low") == "block_now"
        assert resolve_stage(True, "critical") == "block_now"

    def test_block_next_iter_when_medium(self) -> None:
        assert resolve_stage(False, "medium") == "block_next_iter"

    def test_block_next_iter_when_high(self) -> None:
        assert resolve_stage(False, "high") == "block_next_iter"

    def test_block_next_iter_when_critical(self) -> None:
        assert resolve_stage(False, "critical") == "block_next_iter"

    def test_informational_when_low(self) -> None:
        assert resolve_stage(False, "low") == "informational"

    def test_informational_when_info(self) -> None:
        assert resolve_stage(False, "info") == "informational"


class TestStageAutoDerived:
    """MadDogFinding auto-derives stage from (blocks_delivery, severity)."""

    def test_blocker_auto_block_now(self) -> None:
        f = MadDogFinding(
            category="implementation_bug",
            severity="high",
            claim="x",
            blocks_delivery=True,
            evidence=["tests.failed > 0"],
        )
        assert f.stage == "block_now"

    def test_non_blocker_medium_auto_block_next_iter(self) -> None:
        f = MadDogFinding(
            category="brittle_flow",
            severity="medium",
            claim="x",
            blocks_delivery=False,
        )
        assert f.stage == "block_next_iter"

    def test_non_blocker_low_auto_informational(self) -> None:
        f = MadDogFinding(
            category="token_waste",
            severity="low",
            claim="x",
            blocks_delivery=False,
        )
        assert f.stage == "informational"

    def test_non_blocker_info_auto_informational(self) -> None:
        f = MadDogFinding(
            category="quality_gap",
            severity="info",
            claim="x",
            blocks_delivery=False,
        )
        assert f.stage == "informational"

    def test_default_severity_is_medium(self) -> None:
        f = MadDogFinding(category="missing_test", claim="x")
        # No severity, no blocks_delivery, no evidence -> stage
        # resolves to block_next_iter (medium is the default).
        assert f.severity == "medium"
        assert f.stage == "block_next_iter"


class TestStageOverride:
    """A caller can supply stage explicitly to override the auto-derive."""

    def test_explicit_stage_wins(self) -> None:
        # The auto-rule would derive "informational" for (low, no
        # block), but the reviewer wants to escalate it.
        f = MadDogFinding(
            category="token_waste",
            severity="low",
            claim="x",
            stage="block_next_iter",
        )
        assert f.stage == "block_next_iter"


class TestEvidenceGateDowngradeReDerivesStage:
    """When the evidence gate strips blocks_delivery, stage must follow."""

    def test_evidence_gate_downgrades_blocks_delivery(self) -> None:
        # No evidence -> gate downgrades blocks_delivery True -> False.
        f = MadDogFinding(
            category="fake_completion",
            severity="high",
            claim="x",
            blocks_delivery=True,
            # no evidence
        )
        # The gate has set blocks_delivery=False; the stage must
        # follow (high + no block -> block_next_iter, NOT block_now).
        assert f.blocks_delivery is False
        assert f.stage == "block_next_iter"

    def test_evidence_gate_with_evidence_keeps_block(self) -> None:
        f = MadDogFinding(
            category="fake_completion",
            severity="high",
            claim="x",
            blocks_delivery=True,
            evidence=["build.status == 'simulated'"],
        )
        assert f.blocks_delivery is True
        assert f.stage == "block_now"


class TestBlocksNextIterationProperty:
    def test_property_true_for_block_next_iter(self) -> None:
        f = MadDogFinding(
            category="brittle_flow", severity="medium",
            claim="x", blocks_delivery=False,
        )
        assert f.blocks_next_iteration is True

    def test_property_false_for_block_now(self) -> None:
        f = MadDogFinding(
            category="implementation_bug", severity="high",
            claim="x", blocks_delivery=True,
            evidence=["tests.failed > 0"],
        )
        assert f.blocks_next_iteration is False

    def test_property_false_for_informational(self) -> None:
        f = MadDogFinding(
            category="token_waste", severity="low",
            claim="x", blocks_delivery=False,
        )
        assert f.blocks_next_iteration is False


class TestStageInAudit:
    """Stage should be persisted in the audit trail / iteration dump."""

    def test_stage_survives_model_dump_round_trip(self) -> None:
        f = MadDogFinding(
            category="weak_design", severity="high",
            claim="x", blocks_delivery=True,
            evidence=["plan.steps is empty"],
        )
        d = f.model_dump()
        # ``stage`` is a property alias; the canonical field on the
        # dump is ``resolved_stage``. Both are observable to consumers.
        assert d["resolved_stage"] == "block_now"
        assert f.stage == "block_now"
        # Round-trip: re-construct from the dict and verify the
        # post-gate stage is consistent.
        f2 = MadDogFinding(
            category=d["category"],
            severity=d["severity"],
            claim=d["claim"],
            blocks_delivery=d["blocks_delivery"],
            evidence=d["evidence"],
        )
        assert f2.resolved_stage == "block_now"
        assert f2.blocks_delivery is True
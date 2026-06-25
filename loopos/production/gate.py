"""Production readiness gate."""

from __future__ import annotations

from loopos.loop_engine.models import LoopState
from loopos.production.models import ProductionReadinessReport


class ProductionReadinessGate:
    """Decide whether a loop run has enough evidence for production delivery."""

    def evaluate(self, state: LoopState) -> ProductionReadinessReport:
        if not state.iterations:
            return ProductionReadinessReport(status="not_ready", blockers=["no_iterations"])
        latest = state.iterations[-1]
        blockers: list[str] = []
        evidence: list[str] = []
        if latest.build_result is None or latest.build_result.status == "simulated":
            blockers.append("no_real_build_evidence")
        else:
            evidence.append(f"build={latest.build_result.status}")
        if latest.test_result is None or latest.test_result.status in {"simulated", "failed", "partial"}:
            blockers.append("no_passing_real_test_evidence")
        else:
            evidence.append(f"tests={latest.test_result.status}")
        if any(f.blocks_delivery for f in latest.review_findings):
            blockers.append("blocking_review_findings")
        status = "ready" if not blockers else "blocked"
        return ProductionReadinessReport(
            status=status,
            evidence=evidence,
            blockers=blockers,
            demo_only_signals=["simulated_evidence"] if blockers else [],
            delivery_reference=latest.id,
        )


__all__ = ["ProductionReadinessGate"]

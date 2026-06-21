"""Maintainability gate — converts a report into a gate decision."""

from __future__ import annotations

from loopos.maintainability.models import (
    MaintainabilityGateDecision,
    MaintainabilityReport,
)


class MaintainabilityGate:
    """Evaluate a MaintainabilityReport and decide whether the change may proceed."""

    def evaluate(self, report: MaintainabilityReport) -> MaintainabilityGateDecision:
        reason_codes: list[str] = []
        required_actions: list[str] = []
        blocks_merge = False
        requires_refactor = False
        requires_human_review = False
        allowed = True

        # Hard blockers
        blockers = [f for f in report.findings if f.severity == "blocker"]
        if blockers:
            blocks_merge = True
            allowed = False
            for b in blockers:
                reason_codes.append(f"blocker:{b.category}")
                required_actions.append(f"Fix blocker: {b.message}")

        # Score-based decisions
        if report.recommendation == "block":
            blocks_merge = True
            allowed = False
            reason_codes.append("score:blocked")
        elif report.recommendation == "refactor_required":
            requires_refactor = True
            allowed = False
            reason_codes.append("score:refactor_required")
            required_actions.append("Refactor before continuing.")
        elif report.recommendation == "request_changes":
            requires_human_review = True
            reason_codes.append("score:request_changes")
            required_actions.append("Address findings before merge.")
        elif report.recommendation == "approve_with_warnings":
            reason_codes.append("score:approve_with_warnings")

        # Policy bypass is always a hard block
        if report.policy_bypass_risk >= 1.0:
            blocks_merge = True
            allowed = False
            if "bypass:policy" not in reason_codes:
                reason_codes.append("bypass:policy")
                required_actions.append("Remove policy/syscall/data/memory bypass.")

        return MaintainabilityGateDecision(
            report_id=report.report_id,
            allowed_to_continue=allowed,
            requires_refactor=requires_refactor,
            requires_human_review=requires_human_review,
            blocks_merge=blocks_merge,
            reason_codes=reason_codes,
            required_actions=required_actions,
        )

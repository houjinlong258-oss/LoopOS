"""Policy adapter for computer-control actions."""

from __future__ import annotations

from loopos.computer_control.models import (
    ComputerActionRequest,
    ComputerControlMode,
    ComputerControlPermissionSet,
    ComputerControlPolicyDecision,
)
from loopos.computer_control.permissions import approval_required, local_control_allowed


class ComputerControlPolicy:
    """Default-deny policy for unsafe local computer control."""

    def evaluate(
        self,
        action: ComputerActionRequest,
        *,
        mode: ComputerControlMode,
        permissions: ComputerControlPermissionSet,
    ) -> ComputerControlPolicyDecision:
        reasons: list[str] = []
        if not local_control_allowed(mode, permissions):
            return ComputerControlPolicyDecision(
                allowed=False,
                reason_codes=["local_control_requires_allow_computer_control"],
                risk_level=action.risk_level,
                requires_approval=True,
            )
        if action.risk_level == "critical" and not permissions.override_critical:
            return ComputerControlPolicyDecision(
                allowed=False,
                reason_codes=["critical_action_blocked_by_default"],
                risk_level=action.risk_level,
                requires_approval=True,
            )
        needs_approval = approval_required(action.risk_level, permissions)
        if needs_approval:
            reasons.append("approval_required")
        if mode in {"observe_only", "dry_run"}:
            reasons.append(f"mode={mode}")
        return ComputerControlPolicyDecision(
            allowed=not needs_approval,
            reason_codes=reasons or ["allowed"],
            risk_level=action.risk_level,
            requires_approval=needs_approval,
        )


__all__ = ["ComputerControlPolicy"]

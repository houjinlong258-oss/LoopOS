"""Computer-control approval helpers."""

from __future__ import annotations

from loopos.computer_control.models import (
    ComputerActionRequest,
    ComputerApprovalRequest,
    ComputerRiskLevel,
)


def build_approval(action: ComputerActionRequest, risk_level: ComputerRiskLevel) -> ComputerApprovalRequest:
    return ComputerApprovalRequest(
        action=action,
        risk_level=risk_level,
        reason="high or critical computer action requires user approval",
    )


__all__ = ["build_approval"]

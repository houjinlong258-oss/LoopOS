"""Permission checks for local computer control."""

from __future__ import annotations

from loopos.computer_control.models import (
    ComputerControlMode,
    ComputerControlPermissionSet,
    ComputerRiskLevel,
)


def local_control_allowed(mode: ComputerControlMode, permissions: ComputerControlPermissionSet) -> bool:
    return mode != "local_control" or permissions.allow_computer_control


def approval_required(risk_level: ComputerRiskLevel, permissions: ComputerControlPermissionSet) -> bool:
    return risk_level in {"high", "critical"} or permissions.approve_each_action


__all__ = ["approval_required", "local_control_allowed"]

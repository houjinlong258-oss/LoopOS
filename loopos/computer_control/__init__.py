"""Consented, replayable Computer Control Runtime."""

from __future__ import annotations

from loopos.computer_control.cli import computer_command
from loopos.computer_control.models import (
    BrowserAction,
    ClipboardAction,
    ComputerActionPlan,
    ComputerActionRequest,
    ComputerActionResult,
    ComputerApprovalRequest,
    ComputerControlCheckpoint,
    ComputerControlMode,
    ComputerControlPermissionSet,
    ComputerControlPolicyDecision,
    ComputerControlSession,
    ComputerControlTrace,
    ComputerObservation,
    ComputerReplayResult,
    ComputerRiskLevel,
    ComputerTask,
    EmergencyStopState,
    FileDialogAction,
    KeyboardAction,
    MouseAction,
    ScreenRegion,
    ScreenSnapshot,
    UIElement,
    WindowAction,
    WindowSnapshot,
)
from loopos.computer_control.policy_adapter import ComputerControlPolicy
from loopos.computer_control.recorder import ComputerTraceRecorder
from loopos.computer_control.replay import ComputerReplay
from loopos.computer_control.session import ComputerController, backend_from_id
from loopos.computer_control.backends import (
    BrowserComputerBackend,
    CodexComputerUseAdapter,
    CuaMcpAdapter,
    FakeComputerBackend,
    LocalOptionalComputerBackend,
)

__all__ = [
    "BrowserAction",
    "BrowserComputerBackend",
    "ClipboardAction",
    "CodexComputerUseAdapter",
    "ComputerActionPlan",
    "ComputerActionRequest",
    "ComputerActionResult",
    "ComputerApprovalRequest",
    "ComputerControlCheckpoint",
    "ComputerControlMode",
    "ComputerControlPermissionSet",
    "ComputerControlPolicy",
    "ComputerControlPolicyDecision",
    "ComputerControlSession",
    "ComputerControlTrace",
    "ComputerController",
    "ComputerObservation",
    "ComputerReplay",
    "ComputerReplayResult",
    "ComputerRiskLevel",
    "ComputerTask",
    "ComputerTraceRecorder",
    "CuaMcpAdapter",
    "EmergencyStopState",
    "FakeComputerBackend",
    "FileDialogAction",
    "KeyboardAction",
    "LocalOptionalComputerBackend",
    "MouseAction",
    "ScreenRegion",
    "ScreenSnapshot",
    "UIElement",
    "WindowAction",
    "WindowSnapshot",
    "backend_from_id",
    "computer_command",
]

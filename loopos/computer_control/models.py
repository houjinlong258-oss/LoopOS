"""Computer Control Runtime models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


ComputerControlMode = Literal["observe_only", "dry_run", "sandbox_control", "local_control"]
ComputerRiskLevel = Literal["low", "medium", "high", "critical"]
ComputerActionStatus = Literal["planned", "executed", "blocked", "dry_run", "failed"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScreenRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = 0
    y: int = 0
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)


class UIElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str = Field(default_factory=lambda: f"ui_{uuid4().hex[:8]}")
    role: str = "unknown"
    label: str = ""
    region: ScreenRegion = Field(default_factory=ScreenRegion)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ScreenSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(default_factory=lambda: f"screen_{uuid4().hex[:8]}")
    width: int = 1280
    height: int = 720
    image_ref: str = "fake://redacted-screen"
    redacted: bool = True
    created_at: str = Field(default_factory=_now)


class WindowSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = "LoopOS Fake Desktop"
    app_name: str = "FakeComputerBackend"
    region: ScreenRegion = Field(default_factory=lambda: ScreenRegion(width=1280, height=720))
    focused: bool = True


class ComputerObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(default_factory=lambda: f"obs_{uuid4().hex[:8]}")
    session_id: str
    snapshot: ScreenSnapshot = Field(default_factory=ScreenSnapshot)
    windows: list[WindowSnapshot] = Field(default_factory=lambda: [WindowSnapshot()])
    ui_elements: list[UIElement] = Field(default_factory=list)
    redacted: bool = True
    created_at: str = Field(default_factory=_now)


class ComputerControlPermissionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_computer_control: bool = False
    approve_each_action: bool = False
    allow_raw_screenshot_persistence: bool = False
    allow_clipboard_read: bool = False
    override_critical: bool = False


class EmergencyStopState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stopped: bool = False
    reason: str = ""
    stopped_at: str | None = None


class ComputerControlSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: f"ccs_{uuid4().hex[:10]}")
    run_id: str
    mode: ComputerControlMode = "observe_only"
    backend: str = "fake"
    permissions: ComputerControlPermissionSet = Field(default_factory=ComputerControlPermissionSet)
    visible_indicator: bool = True
    emergency_stop: EmergencyStopState = Field(default_factory=EmergencyStopState)
    created_at: str = Field(default_factory=_now)


class ComputerTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: f"ctask_{uuid4().hex[:8]}")
    description: str
    expected_result: str = ""
    run_id: str = "run_computer"
    iteration_id: str = "0"


class MouseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    button: Literal["left", "right", "middle"] = "left"
    region: ScreenRegion = Field(default_factory=ScreenRegion)


class KeyboardAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = ""
    hotkey: list[str] = Field(default_factory=list)


class ClipboardAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = ""
    read_requested: bool = False


class WindowAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["focus", "close", "resize"] = "focus"
    title: str = ""


class BrowserAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["open", "navigate", "verify"] = "verify"
    url: str = ""


class FileDialogAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["select", "cancel"] = "cancel"
    path: str = ""


class ComputerActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(default_factory=lambda: f"cact_{uuid4().hex[:8]}")
    session_id: str
    run_id: str
    iteration_id: str
    trace_id: str
    action_type: str
    target_description: str = ""
    target_region: ScreenRegion | None = None
    input_text: str | None = None
    hotkey: list[str] = Field(default_factory=list)
    expected_result: str = ""
    risk_level: ComputerRiskLevel = "low"
    requires_approval: bool = False
    side_effects: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)


class ComputerActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    session_id: str
    run_id: str
    iteration_id: str
    status: ComputerActionStatus
    observed_before: ComputerObservation | None = None
    observed_after: ComputerObservation | None = None
    stdout_or_ui_feedback: str = ""
    error: str | None = None
    screenshot_ref: str = ""
    redacted: bool = True
    duration_ms: int = 0
    evidence: list[str] = Field(default_factory=list)


class ComputerActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(default_factory=lambda: f"cplan_{uuid4().hex[:8]}")
    task_id: str
    actions: list[ComputerActionRequest] = Field(default_factory=list)
    rationale: str = ""


class ComputerApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(default_factory=lambda: f"cappr_{uuid4().hex[:8]}")
    action: ComputerActionRequest
    risk_level: ComputerRiskLevel
    status: Literal["pending", "approved", "denied"] = "pending"
    reason: str = ""


class ComputerControlPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason_codes: list[str] = Field(default_factory=list)
    risk_level: ComputerRiskLevel = "low"
    requires_approval: bool = False


class ComputerControlCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str = Field(default_factory=lambda: f"cckpt_{uuid4().hex[:8]}")
    session_id: str
    run_id: str
    iteration_id: str
    action_id: str | None = None
    observation_id: str | None = None
    status: str = "recorded"
    created_at: str = Field(default_factory=_now)


class ComputerControlTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(default_factory=lambda: f"ctrace_{uuid4().hex[:10]}")
    session_id: str
    run_id: str
    mode: ComputerControlMode
    backend: str
    actions_planned: list[ComputerActionRequest] = Field(default_factory=list)
    actions_executed: list[ComputerActionResult] = Field(default_factory=list)
    actions_blocked: list[ComputerActionRequest] = Field(default_factory=list)
    approvals: list[ComputerApprovalRequest] = Field(default_factory=list)
    observations: list[ComputerObservation] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)
    completed_at: str | None = None
    replayable: bool = True


class ComputerReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    actions_replayed: int = 0
    actions_reexecuted: int = 0
    observations: list[ComputerObservation] = Field(default_factory=list)
    status: Literal["replayed", "not_found"] = "replayed"


__all__ = [
    "BrowserAction",
    "ClipboardAction",
    "ComputerActionPlan",
    "ComputerActionRequest",
    "ComputerActionResult",
    "ComputerApprovalRequest",
    "ComputerControlCheckpoint",
    "ComputerControlMode",
    "ComputerControlPermissionSet",
    "ComputerControlPolicyDecision",
    "ComputerControlSession",
    "ComputerControlTrace",
    "ComputerObservation",
    "ComputerReplayResult",
    "ComputerRiskLevel",
    "ComputerTask",
    "EmergencyStopState",
    "FileDialogAction",
    "KeyboardAction",
    "MouseAction",
    "ScreenRegion",
    "ScreenSnapshot",
    "UIElement",
    "WindowAction",
    "WindowSnapshot",
]

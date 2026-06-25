"""Deterministic fake computer backend for CI."""

from __future__ import annotations

from loopos.computer_control.models import (
    ComputerActionRequest,
    ComputerActionResult,
    ComputerControlSession,
    ComputerObservation,
    ScreenRegion,
    UIElement,
)
from loopos.computer_control.redaction import redacted_screenshot_ref


class FakeComputerBackend:
    """Record actions without touching the host OS."""

    backend_id = "fake"

    def __init__(self) -> None:
        self.actions: list[ComputerActionRequest] = []

    def available(self) -> bool:
        return True

    def observe(self, session: ComputerControlSession) -> ComputerObservation:
        return ComputerObservation(
            session_id=session.session_id,
            ui_elements=[
                UIElement(
                    role="button",
                    label="Run tests",
                    region=ScreenRegion(x=100, y=100, width=120, height=32),
                )
            ],
        )

    def execute(
        self,
        session: ComputerControlSession,
        action: ComputerActionRequest,
    ) -> ComputerActionResult:
        self.actions.append(action)
        before = self.observe(session)
        after = self.observe(session)
        return ComputerActionResult(
            action_id=action.action_id,
            session_id=session.session_id,
            run_id=action.run_id,
            iteration_id=action.iteration_id,
            status="executed",
            observed_before=before,
            observed_after=after,
            stdout_or_ui_feedback="fake backend recorded action; no OS side effect",
            screenshot_ref=redacted_screenshot_ref(action.action_id),
            redacted=True,
            evidence=["fake_backend_no_os_side_effect"],
        )


__all__ = ["FakeComputerBackend"]

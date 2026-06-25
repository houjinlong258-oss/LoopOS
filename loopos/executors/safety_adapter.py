"""Action-boundary adapter for executor side effects."""

from __future__ import annotations

from loopos.boundary import ActionBoundary, ActionBoundaryDecision


class ExecutorSafetyAdapter:
    """Evaluate executor actions before command or patch execution."""

    def __init__(self, boundary: ActionBoundary | None = None) -> None:
        self.boundary = boundary or ActionBoundary()

    def evaluate_patch(self) -> ActionBoundaryDecision:
        return self.boundary.evaluate(
            "apply_patch",
            "file_write",
            required_permissions=["allow_file_write"],
        )

    def evaluate_command(self) -> ActionBoundaryDecision:
        return self.boundary.evaluate(
            "run_command",
            "shell",
            required_permissions=["allow_shell"],
        )


__all__ = ["ExecutorSafetyAdapter"]

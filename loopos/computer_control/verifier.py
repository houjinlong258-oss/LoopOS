"""Computer result verifier."""

from __future__ import annotations

from loopos.computer_control.models import ComputerActionResult


class ComputerResultVerifier:
    """Verify fake/backend feedback in a deterministic way."""

    def verify(self, result: ComputerActionResult, expected: str = "") -> bool:
        if result.status not in {"executed", "dry_run"}:
            return False
        return not expected or expected.lower() in result.stdout_or_ui_feedback.lower()


__all__ = ["ComputerResultVerifier"]

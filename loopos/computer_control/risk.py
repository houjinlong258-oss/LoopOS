"""Risk classification for computer actions."""

from __future__ import annotations

from loopos.computer_control.models import ComputerRiskLevel


HIGH_KEYWORDS = {"submit", "send", "install", "modify real file", "run shell"}
CRITICAL_KEYWORDS = {"payment", "delete", "credential", "account settings", "deploy"}


def classify_action(description: str, side_effects: list[str] | None = None) -> ComputerRiskLevel:
    text = " ".join([description, " ".join(side_effects or [])]).lower()
    if any(word in text for word in CRITICAL_KEYWORDS):
        return "critical"
    if any(word in text for word in HIGH_KEYWORDS):
        return "high"
    if any(word in text for word in {"click", "type", "scroll", "clipboard"}):
        return "medium"
    return "low"


__all__ = ["classify_action"]

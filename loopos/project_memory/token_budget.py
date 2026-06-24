"""Token budget helpers for Project Memory OS."""

from __future__ import annotations

from loopos.project_memory.models import TokenBudgetLedger


def estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


__all__ = ["TokenBudgetLedger", "estimate_tokens"]

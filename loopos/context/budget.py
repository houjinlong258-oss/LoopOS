"""Deterministic context budget helpers."""

from typing import Any


def bounded_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def estimate_tokens(values: list[dict[str, Any]]) -> int:
    """Return a dependency-free conservative text token estimate."""

    characters = sum(len(str(value)) for value in values)
    return max(1, (characters + 3) // 4) if values else 0


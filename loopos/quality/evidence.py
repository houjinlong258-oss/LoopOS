"""Evidence collection: a small helper for the loop's evidence surfaces.

The v0.4.0 evidence surface is intentionally simple. It is a
list-of-strings accumulator with a few convenience methods for
rendering the evidence into CLI / JSON output.
"""

from __future__ import annotations


class EvidenceCollector:
    """Collect evidence strings for a ``DeliveryCandidate``."""

    def __init__(self) -> None:
        self._items: list[str] = []

    def add(self, item: str) -> None:
        if item and item not in self._items:
            self._items.append(item)

    def extend(self, items: list[str]) -> None:
        for it in items:
            self.add(it)

    def items(self) -> list[str]:
        return list(self._items)

    def is_empty(self) -> bool:
        return not self._items

    def render(self) -> str:
        if not self._items:
            return "(no evidence)"
        return "\n".join(f"- {item}" for item in self._items)


__all__ = ["EvidenceCollector"]

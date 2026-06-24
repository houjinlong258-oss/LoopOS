"""Defect tracking across iterations.

The defect tracker is a small, deterministic helper that records
review findings as defects and computes basic counts and severity
distributions. It is used by the delivery engine to populate
``known_limitations`` and ``open_risks``.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from loopos.loop_engine.models import ReviewFinding


class DefectTracker:
    """Track defects (review findings) across iterations."""

    def __init__(self) -> None:
        self._defects: list[ReviewFinding] = []

    def record(self, findings: Iterable[ReviewFinding]) -> None:
        for f in findings:
            self._defects.append(f)

    def all(self) -> list[ReviewFinding]:
        return list(self._defects)

    def open_blocking(self) -> list[ReviewFinding]:
        return [f for f in self._defects if f.blocks_delivery and f.evidence]

    def by_severity(self) -> dict[str, int]:
        return dict(Counter(f.severity for f in self._defects))

    def by_category(self) -> dict[str, int]:
        return dict(Counter(f.category for f in self._defects))

    def count(self) -> int:
        return len(self._defects)


__all__ = ["DefectTracker"]

"""Technical-debt registry for the Maintainability Kernel.

Records debt items the analyzer surfaces so they can be tracked across
patches instead of being lost in one-off reports. Debt items are
append-only JSONL keyed by a stable fingerprint so that a re-run on the
same patch does not duplicate entries.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

from pydantic import BaseModel, Field

from loopos.maintainability.models import MaintainabilityFinding, MaintainabilityReport


DebtStatus = Literal["open", "accepted", "paid"]


class TechnicalDebtItem(BaseModel):
    """A tracked debt item."""

    debt_id: str
    fingerprint: str
    category: str
    severity: str
    file: str | None = None
    line: int | None = None
    message: str
    status: DebtStatus = "open"
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    occurrences: int = 1
    notes: list[str] = Field(default_factory=list)


class TechnicalDebtRegistry:
    """Append-only JSONL registry of technical debt items."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_report(self, report: MaintainabilityReport) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        for finding in report.findings:
            if finding.severity in ("info", "warning") and finding.category in {
                "complexity",
                "duplication",
                "missing_docs",
                "naming",
                "dead_code",
                "over_abstraction",
                "under_abstraction",
                "dependency_risk",
            }:
                items.append(self._upsert(finding))
        return items

    def list(self, *, status: DebtStatus | None = None) -> list[TechnicalDebtItem]:
        if not self.path.exists():
            return []
        items: list[TechnicalDebtItem] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload: dict[str, Any] = json.loads(line)
            item = TechnicalDebtItem.model_validate(payload)
            if status is None or item.status == status:
                items.append(item)
        return items

    def mark_paid(self, fingerprint: str) -> TechnicalDebtItem | None:
        items = {item.fingerprint: item for item in self.list()}
        item = items.get(fingerprint)
        if item is None:
            return None
        item.status = "paid"
        self._rewrite(list(items.values()))
        return item

    def _upsert(self, finding: MaintainabilityFinding) -> TechnicalDebtItem:
        fingerprint = _fingerprint(finding)
        items = {item.fingerprint: item for item in self.list()}
        existing = items.get(fingerprint)
        if existing is None:
            item = TechnicalDebtItem(
                debt_id=fingerprint[:12],
                fingerprint=fingerprint,
                category=finding.category,
                severity=finding.severity,
                file=finding.file,
                line=finding.line,
                message=finding.message,
            )
            items[fingerprint] = item
        else:
            existing.last_seen = datetime.now(timezone.utc)
            existing.occurrences += 1
            items[fingerprint] = existing
        self._rewrite(list(items.values()))
        return items[fingerprint]

    def _rewrite(self, items: Sequence[TechnicalDebtItem]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(item.model_dump_json() + "\n")


def _fingerprint(finding: MaintainabilityFinding) -> str:
    payload = f"{finding.category}|{finding.file or ''}|{finding.line or 0}|{finding.message}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

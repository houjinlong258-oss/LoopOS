"""Policy audit log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopos.core.state import utc_now
from loopos.policy_os.models import PolicyDecision


class PolicyAuditLog:
    """JSONL audit trail for policy decisions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, scope: str, subject: dict[str, Any], decision: PolicyDecision) -> None:
        payload = {
            "created_at": str(utc_now()),
            "scope": scope,
            "subject": subject,
            "decision": decision.model_dump(mode="json"),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def list(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

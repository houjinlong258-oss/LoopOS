"""Kernel checkpoint — snapshot run state for recovery and replay."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from loopos.kernel.models import RunRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KernelCheckpoint(BaseModel):
    """Immutable snapshot of a run's state at a specific step."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    step: int
    status: str
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    event_log_offset: int = 0
    checksum: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    @classmethod
    def from_run(cls, run: RunRecord, *, event_log_offset: int = 0) -> "KernelCheckpoint":
        """Create a checkpoint from a live RunRecord."""
        state = run.model_dump(mode="json")
        raw = json.dumps(state, sort_keys=True, ensure_ascii=False)
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return cls(
            run_id=run.run_id,
            step=run.step,
            status=run.status,
            state_snapshot=state,
            event_log_offset=event_log_offset,
            checksum=checksum,
        )

    def verify(self) -> bool:
        """Verify the checkpoint's checksum against its state_snapshot."""
        raw = json.dumps(self.state_snapshot, sort_keys=True, ensure_ascii=False)
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self.checksum == expected


class CheckpointStore:
    """File-backed checkpoint persistence."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: KernelCheckpoint) -> KernelCheckpoint:
        path = self.directory / f"{checkpoint.run_id}_{checkpoint.step}.json"
        path.write_text(
            checkpoint.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return checkpoint

    def load(self, run_id: str, step: int) -> KernelCheckpoint:
        path = self.directory / f"{run_id}_{step}.json"
        if not path.exists():
            raise KeyError(f"checkpoint not found: {run_id} step {step}")
        return KernelCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, run_id: str) -> list[KernelCheckpoint]:
        checkpoints: list[KernelCheckpoint] = []
        for path in sorted(self.directory.glob(f"{run_id}_*.json")):
            checkpoints.append(
                KernelCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))
            )
        return checkpoints

    def latest(self, run_id: str) -> KernelCheckpoint | None:
        items = self.list(run_id)
        return items[-1] if items else None

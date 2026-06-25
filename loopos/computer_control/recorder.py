"""Trace recorder for computer-control sessions."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.computer_control.models import ComputerControlTrace


class ComputerTraceRecorder:
    """Persist replayable computer-control traces."""

    def __init__(self, root: str | Path = ".loopos/computer_traces") -> None:
        self.root = Path(root)

    def save(self, trace: ComputerControlTrace) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{trace.trace_id}.json"
        path.write_text(
            json.dumps(trace.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load_latest(self) -> ComputerControlTrace | None:
        if not self.root.exists():
            return None
        files = sorted(self.root.glob("ctrace_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return None
        data = json.loads(files[0].read_text(encoding="utf-8"))
        return ComputerControlTrace.model_validate(data)


__all__ = ["ComputerTraceRecorder"]

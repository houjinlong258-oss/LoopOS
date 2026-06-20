"""Versioned run creation and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.core.state import LoopState
from loopos.kernel.models import RunRecord, RunSpec


class RunManager:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(self, spec: RunSpec) -> RunRecord:
        run = RunRecord.from_spec(spec)
        self.save(run)
        return run

    def save(self, run: RunRecord) -> Path:
        path = self.base_dir / f"{run.run_id}.json"
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, run_id: str) -> RunRecord:
        path = self.base_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("schema_version") == 2:
            return RunRecord.model_validate(payload)
        return RunRecord.from_legacy(LoopState.model_validate(payload))

    def list(self) -> list[RunRecord]:
        return [self.load(path.stem) for path in sorted(self.base_dir.glob("*.json"))]

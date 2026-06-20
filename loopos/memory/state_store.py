"""JSON state persistence."""

from __future__ import annotations

from pathlib import Path

from loopos.core.state import LoopState


class StateStore:
    """Store one JSON file per run."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: LoopState) -> Path:
        path = self.base_dir / f"{state.run_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, run_id: str) -> LoopState:
        path = self.base_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        return LoopState.model_validate_json(path.read_text(encoding="utf-8"))

    def list_run_ids(self) -> list[str]:
        return sorted(path.stem for path in self.base_dir.glob("*.json"))

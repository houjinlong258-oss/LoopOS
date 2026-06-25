"""Artifact persistence for raw and compacted executor output."""

from __future__ import annotations

from pathlib import Path


class ExecutionArtifactStore:
    """Write executor artifacts under a run/iteration directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write_text(
        self,
        *,
        run_id: str,
        iteration_id: str,
        name: str,
        text: str,
    ) -> str:
        safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
        path = self.root / run_id / iteration_id / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", errors="replace")
        return str(path)


__all__ = ["ExecutionArtifactStore"]

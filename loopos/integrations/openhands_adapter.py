"""Minimal OpenHands adapter boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from loopos.core.state import Observation
from loopos.execution.terminal import TerminalExecutor


class OpenHandsAdapter:
    """Adapter facade that avoids binding LoopOS to OpenHands internals."""

    def __init__(self, *, workspace: str | Path = ".", terminal: TerminalExecutor | None = None) -> None:
        self.workspace = Path(workspace).resolve()
        self.terminal = terminal or TerminalExecutor(default_cwd=self.workspace)

    def is_available(self) -> bool:
        return importlib.util.find_spec("openhands") is not None

    def execute_command(self, cmd: str, cwd: str | Path | None = None, timeout: int | None = None) -> Observation:
        return self.terminal.execute(cmd, cwd=cwd or self.workspace, timeout_seconds=timeout)

    def read_file(self, path: str | Path) -> Observation:
        target = self._safe_path(path)
        if target is None or not target.exists():
            return Observation(success=False, summary="file unavailable", error="file_not_found")
        return Observation(success=True, summary="file read", data={"content": target.read_text(encoding="utf-8")})

    def write_file(self, path: str | Path, content: str) -> Observation:
        target = self._safe_path(path)
        if target is None:
            return Observation(success=False, summary="path outside workspace", error="blocked")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return Observation(success=True, summary="file written", data={"path": str(target)})

    def apply_patch(self, patch: str) -> Observation:
        return Observation(
            success=False,
            summary="apply_patch delegation is not implemented in the OpenHands adapter MVP",
            error="not_implemented",
            data={"patch_preview": patch[:200]},
        )

    def _safe_path(self, path: str | Path) -> Path | None:
        target = (self.workspace / path).resolve()
        try:
            target.relative_to(self.workspace)
        except ValueError:
            return None
        return target

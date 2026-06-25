"""Unified-diff patch application for sandboxed repos."""

from __future__ import annotations

import subprocess
from pathlib import Path

from loopos.executors.result import ExecutionMode, PatchRequest, PatchResult
from loopos.executors.sandbox import SandboxGuard, SandboxViolation


class PatchApplier:
    """Apply unified diffs after sandbox and action-boundary checks."""

    def __init__(self, mode: ExecutionMode | None = None) -> None:
        self.mode = mode or ExecutionMode()

    def apply(self, request: PatchRequest) -> PatchResult:
        try:
            if self.mode.sandbox:
                SandboxGuard(self.mode.sandbox_root or request.cwd).ensure_inside(request.cwd)
            changed_files = changed_files_from_patch(request.patch)
            guard = SandboxGuard(self.mode.sandbox_root or request.cwd)
            for file_path in changed_files:
                guard.ensure_relative_patch_path(file_path)
        except SandboxViolation as exc:
            return PatchResult(status="failed", error=str(exc))

        if self.mode.dry_run or not self.mode.allow_file_write:
            return PatchResult(
                status="dry_run",
                changed_files=changed_files,
                diff_summary=f"{len(changed_files)} file(s) would change",
                evidence=["dry_run: patch not applied"],
            )

        cwd = Path(request.cwd).resolve()
        check = subprocess.run(
            ["git", "-C", str(cwd), "apply", "--check", "--whitespace=nowarn", "-"],
            input=request.patch,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if check.returncode != 0:
            fallback = _apply_simple_unified_diff(cwd, request.patch)
            if fallback is None:
                return PatchResult(
                    status="failed",
                    changed_files=changed_files,
                    error=(check.stderr or check.stdout).strip(),
                    evidence=["git apply --check failed"],
                )
            return PatchResult(
                status="applied",
                changed_files=changed_files,
                diff_summary=f"{len(changed_files)} file(s) changed",
                evidence=["git apply --check failed", "python unified-diff fallback applied"],
            )
        applied = subprocess.run(
            ["git", "-C", str(cwd), "apply", "--whitespace=nowarn", "-"],
            input=request.patch,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if applied.returncode != 0:
            return PatchResult(
                status="failed",
                changed_files=changed_files,
                error=(applied.stderr or applied.stdout).strip(),
                evidence=["git apply failed"],
            )
        return PatchResult(
            status="applied",
            changed_files=changed_files,
            diff_summary=f"{len(changed_files)} file(s) changed",
            evidence=["git apply --check passed", "git apply completed"],
        )


def changed_files_from_patch(patch: str) -> list[str]:
    """Extract target paths from a unified diff."""

    files: list[str] = []
    for line in patch.splitlines():
        if not line.startswith("+++ "):
            continue
        target = line[4:].strip()
        if target == "/dev/null":
            continue
        if target.startswith("b/"):
            target = target[2:]
        if target and target not in files:
            files.append(target)
    return files


def _apply_simple_unified_diff(cwd: Path, patch: str) -> bool | None:
    """Apply simple replacement hunks when git apply is unavailable/strict.

    This fallback intentionally supports only existing-file line
    replacement hunks. It is enough for deterministic temp-repo repairs
    and refuses ambiguous patches by returning ``None``.
    """

    current_file: str | None = None
    old_lines: list[str] = []
    new_lines: list[str] = []
    applied_any = False

    def flush() -> bool:
        nonlocal old_lines, new_lines, applied_any
        if current_file is None or not old_lines and not new_lines:
            old_lines = []
            new_lines = []
            return True
        path = cwd / current_file
        if not path.exists():
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
        old = "".join(old_lines)
        new = "".join(new_lines)
        if old not in text:
            old_crlf = old.replace("\n", "\r\n")
            new_crlf = new.replace("\n", "\r\n")
            if old_crlf not in text:
                return False
            path.write_text(text.replace(old_crlf, new_crlf, 1), encoding="utf-8", newline="")
        else:
            path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
        applied_any = True
        old_lines = []
        new_lines = []
        return True

    for line in patch.splitlines(keepends=True):
        if line.startswith("+++ "):
            if not flush():
                return None
            target = line[4:].strip()
            current_file = target[2:] if target.startswith("b/") else target
            continue
        if line.startswith(("--- ", "@@")):
            continue
        if line.startswith("-"):
            old_lines.append(line[1:])
        elif line.startswith("+"):
            new_lines.append(line[1:])
        elif line.startswith(" "):
            old_lines.append(line[1:])
            new_lines.append(line[1:])
    if not flush():
        return None
    return applied_any


__all__ = ["PatchApplier", "changed_files_from_patch"]

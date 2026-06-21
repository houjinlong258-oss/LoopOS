"""Release hygiene checker.

Validates that a release-worthy source tree does NOT contain:

  - VCS internals:  ``.git/``
  - Virtualenvs:    ``.venv/``
  - Local state:    ``.loopos/``, ``.loopos-*/``
  - Build caches:   ``__pycache__/``, ``*.pyc``, ``*.pyo``, ``*.pyd``,
                    ``.pytest_cache/``, ``.ruff_cache/``, ``.mypy_cache/``
  - Build artifacts: ``dist/``, ``build/``, ``*.egg-info/``
  - Third-party source snapshots kept locally as architectural references:
    ``OpenHands-*/``, ``langgraph-*/``, ``letta-*/``, ``zep-main/``,
    ``projectmem-*/``, ``hermes-agent-*/``
  - Local-only planning notes: ``task_plan.md``, ``findings.md``,
    ``progress.md`` (these are gitignored).

And validates that the tree DOES contain the top-level governance /
contract files required for an open-source release:

  ``LICENSE``, ``README.md``, ``CHANGELOG.md``, ``AGENTS.md``,
  ``ROADMAP.md``, ``CONTRIBUTING.md``, ``SECURITY.md``,
  ``CODE_OF_CONDUCT.md``, ``pyproject.toml``.

The scanner also walks every text file looking for absolute Windows or
Unix dev paths leaked from the development environment (e.g.
``D:\\\\LoopOS``); these are surfaced as warnings rather than blockers.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterable

__all__ = [
    "BLOCKED_DIRS",
    "BLOCKED_DIR_GLOBS",
    "BLOCKED_FILES",
    "BLOCKED_FILE_GLOBS",
    "REQUIRED_TOP_LEVEL_FILES",
    "LEAKED_PATH_RE",
    "ReleaseFinding",
    "ReleaseReport",
    "check_release_clean",
]


BLOCKED_DIRS: tuple[str, ...] = (
    ".git",
    ".venv",
    ".loopos",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    "dist",
    "build",
    "zep-main",
    ".agents",
    ".codex",
)

BLOCKED_DIR_GLOBS: tuple[str, ...] = (
    ".loopos-*",
    "OpenHands-*",
    "langgraph-*",
    "letta-*",
    "projectmem-*",
    "hermes-agent-*",
    "*.egg-info",
)

BLOCKED_FILES: tuple[str, ...] = (
    "task_plan.md",
    "findings.md",
    "progress.md",
)

BLOCKED_FILE_GLOBS: tuple[str, ...] = (
    "*.pyc",
    "*.pyo",
    "*.pyd",
)

REQUIRED_TOP_LEVEL_FILES: tuple[str, ...] = (
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "pyproject.toml",
)

LEAKED_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\\\?LoopOS|/home/[^/\s]+/LoopOS|/Users/[^/\s]+/LoopOS)"
)


@dataclass(frozen=True)
class ReleaseFinding:
    """One structured finding produced by the hygiene checker."""

    severity: str  # "error" | "warning"
    code: str
    message: str
    path: str = ""


@dataclass
class ReleaseReport:
    """Aggregated report for ``check_release_clean``."""

    source: str
    errors: list[ReleaseFinding] = field(default_factory=list)
    warnings: list[ReleaseFinding] = field(default_factory=list)
    scanned_files: int = 0
    scanned_dirs: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "ok": self.ok,
            "scanned_files": self.scanned_files,
            "scanned_dirs": self.scanned_dirs,
            "errors": [asdict(f) for f in self.errors],
            "warnings": [asdict(f) for f in self.warnings],
        }


def _matches_any_glob(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatchcase(name, pat) for pat in patterns)


def _iter_source_files(root: Path) -> Iterable[tuple[Path, Path]]:
    """Yield ``(relative_path, absolute_path)`` for every file under ``root``.

    Pruning happens in this single pass so the caller does not have to
    materialise the entire tree.  Directories that are themselves blocked
    are NOT descended into (they are flagged separately by the caller).
    """

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(dirnames)
        rel_dir = Path(dirpath).relative_to(root)
        for fname in sorted(filenames):
            full = Path(dirpath) / fname
            rel = rel_dir / fname
            yield rel, full


def check_release_clean(source: str | os.PathLike[str]) -> ReleaseReport:
    """Run the full hygiene check against ``source`` and return the report.

    Never raises on a forbidden-path finding; records the finding and
    continues so the caller gets a complete picture.  I/O errors while
    reading a file are converted to warnings rather than aborting the
    scan.
    """

    root = Path(source).resolve()
    report = ReleaseReport(source=str(root))

    if not root.is_dir():
        report.errors.append(
            ReleaseFinding(
                severity="error",
                code="SOURCE_MISSING",
                message=f"source directory does not exist or is not a directory: {root}",
            )
        )
        return report

    for name in REQUIRED_TOP_LEVEL_FILES:
        if not (root / name).exists():
            report.errors.append(
                ReleaseFinding(
                    severity="error",
                    code="MISSING_REQUIRED_FILE",
                    message=f"required top-level file is missing: {name}",
                    path=name,
                )
            )

    for rel, full in _iter_source_files(root):
        # Directory check FIRST: if a file lives inside a blocked
        # directory, the directory is the primary violation and we do
        # not also want to flood the report with one BLOCKED_DIR per file
        # we happened to encounter inside it.
        blocked_parent = ""
        for parent in rel.parents:
            if parent.name in BLOCKED_DIRS or _matches_any_glob(parent.name, BLOCKED_DIR_GLOBS):
                blocked_parent = parent.name
                break

        if blocked_parent:
            already = any(
                f.code == "BLOCKED_DIR" and f.path.endswith(blocked_parent)
                for f in report.errors
            )
            if not already:
                report.errors.append(
                    ReleaseFinding(
                        severity="error",
                        code="BLOCKED_DIR",
                        message=(
                            f"blocked directory leaked into release: {blocked_parent}"
                        ),
                        path=str(rel.parent),
                    )
                )
            continue

        if _matches_any_glob(full.name, BLOCKED_FILE_GLOBS):
            report.errors.append(
                ReleaseFinding(
                    severity="error",
                    code="BLOCKED_FILE",
                    message=f"blocked build artifact leaked into release: {full.name}",
                    path=str(rel),
                )
            )
            continue

        if full.name in BLOCKED_FILES:
            report.errors.append(
                ReleaseFinding(
                    severity="error",
                    code="BLOCKED_FILE",
                    message=f"blocked local-only file leaked into release: {full.name}",
                    path=str(rel),
                )
            )
            continue

        report.scanned_files += 1

        leaked = _scan_file_for_leaked_paths(full)
        if leaked:
            report.warnings.append(
                ReleaseFinding(
                    severity="warning",
                    code="LEAKED_DEV_PATH",
                    message=(
                        f"absolute development path '{leaked.group(0)}' "
                        "found in source file"
                    ),
                    path=str(rel),
                )
            )

    for child in sorted(root.iterdir()):
        if child.is_dir():
            if child.name in BLOCKED_DIRS or _matches_any_glob(child.name, BLOCKED_DIR_GLOBS):
                already = any(
                    f.code == "BLOCKED_DIR" and f.path == child.name
                    for f in report.errors
                )
                if not already:
                    report.errors.append(
                        ReleaseFinding(
                            severity="error",
                            code="BLOCKED_DIR",
                            message=(
                                f"blocked directory leaked into release: {child.name}"
                            ),
                            path=child.name,
                        )
                    )
            report.scanned_dirs += 1

    return report


def _scan_file_for_leaked_paths(path: Path) -> re.Match[str] | None:
    """Return the first leaked-path match in ``path``, if any.

    Binary files and unreadable files are skipped silently.
    """

    try:
        with path.open("rb") as fh:
            head = fh.read(2048)
        if b"\x00" in head:
            return None
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return LEAKED_PATH_RE.search(text)

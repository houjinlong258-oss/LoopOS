"""Release packaging.

Stages a deterministic copy of the LoopOS source tree into
``<output>/loopos-<version>/`` and optionally zips the staged tree into
``loopos-<version>.zip``.  Two sidecar files are written next to the
staging directory:

  * ``MANIFEST.txt``  — sorted list of every file that was copied in,
    one relative path per line.
  * ``SHA256SUMS``    — ``<sha256>  <relative-path>`` for every file.

Files and directories excluded by ``check_release_clean`` are skipped
here too, by definition.  The packaging step is therefore safe to run
from a working clone that still contains ``.venv`` / ``.git`` / cached
planning notes.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from loopos.release.hygiene import (
    BLOCKED_DIR_GLOBS,
    BLOCKED_DIRS,
    BLOCKED_FILE_GLOBS,
    BLOCKED_FILES,
    ReleaseFinding,
    check_release_clean,
    _matches_any_glob,
)

__all__ = ["PackageReport", "package_release"]


ALLOWED_TOP_LEVEL_DIRS: frozenset[str] = frozenset(
    {
        ".github",
        "benchmarks",
        "docs",
        "examples",
        "loopos",
        "policies",
        "providers",
        "scripts",
        "tests",
    }
)

ALLOWED_TOP_LEVEL_FILES: frozenset[str] = frozenset(
    {
        ".gitattributes",
        ".gitignore",
        "AGENTS.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "LICENSE",
        "MAINTAINERS.md",
        "Makefile",
        "PLUGIN_SPEC.md",
        "README.md",
        "RELEASE_CHECKLIST.md",
        "RFC_PROCESS.md",
        "ROADMAP.md",
        "SECURITY.md",
        "pyproject.toml",
    }
)

# Operational attestations are published beside the archive. Embedding either
# file would make the archive checksum self-referential or immediately stale.
EXCLUDED_RELEASE_METADATA: frozenset[str] = frozenset(
    {
        "docs/release-notes/founding-release.md",
        "docs/reports/latest-test-report.json",
    }
)


@dataclass
class PackageReport:
    """Structured report returned by ``package_release``."""

    version: str
    source: str
    staging_dir: str
    manifest_path: str
    sha256_path: str
    zip_path: str | None = None
    copied_files: int = 0
    skipped_files: int = 0
    skipped_dirs: int = 0
    hygiene_errors: list[ReleaseFinding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _should_skip_dir(name: str) -> bool:
    return name in BLOCKED_DIRS or _matches_any_glob(name, BLOCKED_DIR_GLOBS)


def _should_skip_file(name: str) -> bool:
    return name in BLOCKED_FILES or _matches_any_glob(name, BLOCKED_FILE_GLOBS)


def _iter_source_files(root: Path) -> Iterable[Path]:
    """Yield absolute paths of files that should be included in the release.

    Symmetric with ``hygiene._iter_source_files`` but prunes blocked
    directories before descending so we never even stat their children.
    """

    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        if base == root:
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d in ALLOWED_TOP_LEVEL_DIRS and not _should_skip_dir(d)
            )
            filenames = [
                name for name in filenames if name in ALLOWED_TOP_LEVEL_FILES
            ]
        else:
            dirnames[:] = sorted(d for d in dirnames if not _should_skip_dir(d))
        for fname in sorted(filenames):
            if _should_skip_file(fname):
                continue
            path = base / fname
            if path.relative_to(root).as_posix() in EXCLUDED_RELEASE_METADATA:
                continue
            yield path


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def package_release(
    *,
    version: str,
    source: str | os.PathLike[str],
    output: str | os.PathLike[str],
    make_zip: bool = True,
) -> PackageReport:
    """Stage the release into ``output`` and return a structured report.

    Refuses to overwrite an existing staging directory; the caller must
    delete it first.  This makes packaging failures loud rather than
    silently producing a half-mixed tree.
    """

    src_root = Path(source).resolve()
    out_root = Path(output).resolve()
    staging_name = f"loopos-{version}"
    staging_dir = out_root / staging_name
    manifest_path = out_root / f"{staging_name}.MANIFEST.txt"
    sha256_path = out_root / f"{staging_name}.SHA256SUMS"
    zip_path = out_root / f"{staging_name}.zip"  # built only when make_zip

    report = PackageReport(
        version=version,
        source=str(src_root),
        staging_dir=str(staging_dir),
        manifest_path=str(manifest_path),
        sha256_path=str(sha256_path),
        zip_path=str(zip_path) if make_zip else None,
    )

    if not src_root.is_dir():
        report.errors.append(f"source directory not found: {src_root}")
        return report

    # Pre-flight hygiene check.  We do NOT fail packaging on hygiene
    # errors here — packaging itself prunes blocked paths — but we
    # surface the findings so the caller can correlate.
    hygiene = check_release_clean(src_root)
    report.hygiene_errors = list(hygiene.errors)

    if staging_dir.exists():
        report.errors.append(f"staging directory already exists: {staging_dir}")
        return report

    out_root.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=False)

    manifest_entries: list[str] = []
    sha256_entries: list[str] = []

    for abs_path in _iter_source_files(src_root):
        rel = abs_path.relative_to(src_root)
        dest = staging_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(abs_path, dest)
        except OSError as exc:
            report.errors.append(f"failed to copy {rel}: {exc}")
            continue
        report.copied_files += 1
        rel_posix = rel.as_posix()
        manifest_entries.append(rel_posix)
        sha256_entries.append(f"{_sha256_of(dest)}  {rel_posix}")

    manifest_entries.sort()
    sha256_entries.sort(key=lambda line: line.split("  ", 1)[1])
    manifest_path.write_text("\n".join(manifest_entries) + "\n", encoding="utf-8")
    sha256_path.write_text("\n".join(sha256_entries) + "\n", encoding="utf-8")

    if make_zip:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for sidecar in (manifest_path, sha256_path):
                zf.write(sidecar, sidecar.name)
            for rel_posix in manifest_entries:
                zf.write(staging_dir / rel_posix, f"{staging_name}/{rel_posix}")

    return report

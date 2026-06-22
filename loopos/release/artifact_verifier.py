"""Independent verification for a packaged LoopOS release archive."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from loopos.release.hygiene import check_release_clean
from loopos.release.packaging import package_release


@dataclass
class ArtifactVerificationReport:
    artifact: str
    artifact_sha256: str = ""
    artifact_sha256_file: str = "failed"
    python_zipfile_extract: str = "failed"
    system_unzip_extract: str = "skipped"
    internal_sha256sums: str = "failed"
    no_surrogate_paths: str = "failed"
    no_non_ascii_paths: str = "failed"
    no_non_ascii_under_loopos: str = "failed"
    repackage: str = "failed"
    passed: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def verify_release_artifact(artifact: str | Path) -> ArtifactVerificationReport:
    path = Path(artifact).resolve()
    report = ArtifactVerificationReport(artifact=str(path))
    if not path.is_file():
        report.errors.append(f"artifact not found: {path}")
        return report

    report.artifact_sha256 = _sha256(path)
    sidecar = Path(f"{path}.sha256")
    if sidecar.is_file() and sidecar.read_text(encoding="ascii").split()[:1] == [
        report.artifact_sha256
    ]:
        report.artifact_sha256_file = "passed"
    else:
        report.errors.append("artifact SHA256 sidecar is missing or does not match")

    try:
        with ZipFile(path) as archive:
            names = archive.namelist()
            safe_names = _safe_member_names(names)
            report.no_surrogate_paths = (
                "passed"
                if all(not any(0xD800 <= ord(char) <= 0xDFFF for char in name) for name in names)
                else "failed"
            )
            report.no_non_ascii_paths = "passed" if all(name.isascii() for name in names) else "failed"
            runtime_names = [name for name in names if "/loopos/" in name]
            report.no_non_ascii_under_loopos = (
                "passed" if all(name.isascii() for name in runtime_names) else "failed"
            )
            if not safe_names:
                report.errors.append("archive contains duplicate, absolute, or traversal paths")
            if report.no_surrogate_paths != "passed":
                report.errors.append("archive contains surrogate path characters")
            if report.no_non_ascii_paths != "passed":
                report.errors.append("archive contains non-ASCII paths")

            with tempfile.TemporaryDirectory(prefix="loopos-verify-python-") as temp:
                extracted = Path(temp)
                if safe_names:
                    archive.extractall(extracted)
                    report.python_zipfile_extract = "passed"
                sums = [name for name in names if name.endswith(".SHA256SUMS")]
                if len(sums) == 1:
                    source_name = sums[0].removesuffix(".SHA256SUMS")
                    source_root = extracted / source_name
                    sums_path = extracted / sums[0]
                    if _verify_internal_sums(source_root, sums_path):
                        report.internal_sha256sums = "passed"
                    else:
                        report.errors.append("internal SHA256SUMS verification failed")
                    clean = check_release_clean(source_root)
                    with tempfile.TemporaryDirectory(prefix="loopos-verify-repackage-") as out:
                        package = package_release(
                            version="verification",
                            source=source_root,
                            output=out,
                            make_zip=False,
                        )
                    if clean.ok and not clean.warnings and not package.errors:
                        report.repackage = "passed"
                    else:
                        report.errors.append("extracted source did not pass clean repackage")
                else:
                    report.errors.append("archive must contain exactly one internal SHA256SUMS")
    except (BadZipFile, OSError, UnicodeError) as exc:
        report.errors.append(f"Python zipfile extraction failed: {exc}")

    report.system_unzip_extract = _verify_with_system_unzip(path, report)
    report.passed = all(
        value == "passed"
        for value in (
            report.artifact_sha256_file,
            report.python_zipfile_extract,
            report.internal_sha256sums,
            report.no_surrogate_paths,
            report.no_non_ascii_paths,
            report.no_non_ascii_under_loopos,
            report.repackage,
        )
    ) and report.system_unzip_extract in {"passed", "skipped"}
    return report


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_names(names: list[str]) -> bool:
    if len(names) != len(set(names)):
        return False
    return all(
        not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
        for name in names
    )


def _verify_internal_sums(source_root: Path, sums_path: Path) -> bool:
    try:
        entries = sums_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    expected_paths: set[str] = set()
    for line in entries:
        digest, separator, relative = line.partition("  ")
        relative_path = PurePosixPath(relative)
        if not separator or len(digest) != 64 or relative_path.is_absolute():
            return False
        if ".." in relative_path.parts:
            return False
        target = source_root.joinpath(*relative_path.parts)
        if not target.is_file() or _sha256(target) != digest.lower():
            return False
        expected_paths.add(relative_path.as_posix())
    actual_paths = {
        path.relative_to(source_root).as_posix() for path in source_root.rglob("*") if path.is_file()
    }
    return bool(entries) and expected_paths == actual_paths


def _verify_with_system_unzip(
    artifact: Path,
    report: ArtifactVerificationReport,
) -> str:
    executable = shutil.which("unzip")
    if executable is None:
        return "skipped"
    with tempfile.TemporaryDirectory(prefix="loopos-verify-unzip-") as temp:
        result = subprocess.run(
            [executable, "-qq", str(artifact), "-d", temp],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        if result.returncode == 0:
            return "passed"
        report.errors.append(f"system unzip failed: {(result.stderr or result.stdout)[-500:]}")
        return "failed"

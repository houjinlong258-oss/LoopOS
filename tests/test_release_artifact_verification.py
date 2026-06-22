"""Cross-platform release artifact verification tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from loopos.release.artifact_verifier import verify_release_artifact
from loopos.release.hygiene import REQUIRED_TOP_LEVEL_FILES
from loopos.release.packaging import package_release


def _build_artifact(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    for name in REQUIRED_TOP_LEVEL_FILES:
        (source / name).write_text(f"# {name}\n", encoding="utf-8")
    package = source / "loopos"
    package.mkdir()
    (package / "__init__.py").write_text('"""fixture"""\n', encoding="utf-8")
    report = package_release(
        version="0.1.0",
        source=source,
        output=tmp_path / "dist",
        make_zip=True,
    )
    assert not report.errors and report.zip_path is not None
    artifact = Path(report.zip_path)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    Path(f"{artifact}.sha256").write_text(
        f"{digest}  {artifact.name}\n",
        encoding="ascii",
    )
    return artifact


def _refresh_artifact_sidecar(artifact: Path) -> None:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    Path(f"{artifact}.sha256").write_text(
        f"{digest}  {artifact.name}\n",
        encoding="ascii",
    )


def test_valid_artifact_passes_all_available_verifiers(tmp_path: Path) -> None:
    artifact = _build_artifact(tmp_path)
    report = verify_release_artifact(artifact)
    assert report.passed, report.errors
    assert report.artifact_sha256_file == "passed"
    assert report.python_zipfile_extract == "passed"
    assert report.system_unzip_extract in {"passed", "skipped"}
    assert report.system_extractor in {"unzip", "tar", "unavailable"}
    assert report.internal_sha256sums == "passed"
    assert report.no_surrogate_paths == "passed"
    assert report.no_non_ascii_paths == "passed"
    assert report.no_non_ascii_under_loopos == "passed"
    assert report.repackage == "passed"


def test_internal_checksum_detects_tampered_source_file(tmp_path: Path) -> None:
    artifact = _build_artifact(tmp_path)
    rewritten = tmp_path / "tampered.zip"
    with ZipFile(artifact) as source, ZipFile(rewritten, "w", ZIP_DEFLATED) as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename.endswith("/README.md"):
                content = b"tampered\n"
            target.writestr(info, content)
    artifact.unlink()
    rewritten.replace(artifact)
    _refresh_artifact_sidecar(artifact)
    report = verify_release_artifact(artifact)
    assert report.passed is False
    assert report.internal_sha256sums == "failed"


def test_non_ascii_runtime_path_is_rejected(tmp_path: Path) -> None:
    artifact = _build_artifact(tmp_path)
    with ZipFile(artifact, "a", ZIP_DEFLATED) as archive:
        archive.writestr("loopos-0.1.0/loopos/模块.py", "VALUE = 1\n")
    _refresh_artifact_sidecar(artifact)
    report = verify_release_artifact(artifact)
    assert report.passed is False
    assert report.no_non_ascii_paths == "failed"
    assert report.no_non_ascii_under_loopos == "failed"


def test_verifier_cli_emits_pure_json(tmp_path: Path) -> None:
    artifact = _build_artifact(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts" / "verify_release_artifact.py"),
            str(artifact),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["passed"] is True

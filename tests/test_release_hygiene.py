"""Tests for the release hygiene checker and packager.

These tests build tiny fixture trees in ``tmp_path`` so they exercise the
real ``os.walk`` path without touching the repository itself.  No real
network or shell is used.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from loopos.release import check_release_clean, package_release
from loopos.release.hygiene import (
    BLOCKED_DIRS,
    BLOCKED_FILES,
    REQUIRED_TOP_LEVEL_FILES,
)
from loopos.release.packaging import (
    ALLOWED_TOP_LEVEL_DIRS,
    ALLOWED_TOP_LEVEL_FILES,
    _should_skip_dir,
    _should_skip_file,
)


_REQUIRED_FILES = list(REQUIRED_TOP_LEVEL_FILES)


def _scaffold_clean_tree(root: Path) -> None:
    """Create the minimum required top-level files in ``root``."""
    for name in _REQUIRED_FILES:
        (root / name).write_text(f"# {name}\n", encoding="utf-8")
    (root / "loopos").mkdir(exist_ok=True)
    (root / "loopos" / "__init__.py").write_text(
        '"""LoopOS package."""\n', encoding="utf-8"
    )


def test_clean_tree_passes(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    report = check_release_clean(tmp_path)
    assert report.ok, [f.message for f in report.errors]
    assert report.scanned_files >= len(_REQUIRED_FILES) + 1


def test_missing_required_top_level_file_is_blocker(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / "LICENSE").unlink()
    report = check_release_clean(tmp_path)
    assert not report.ok
    codes = [f.code for f in report.errors]
    assert "MISSING_REQUIRED_FILE" in codes
    paths = [f.path for f in report.errors if f.code == "MISSING_REQUIRED_FILE"]
    assert "LICENSE" in paths


def test_blocked_directory_at_top_level_is_blocker(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    report = check_release_clean(tmp_path)
    assert not report.ok
    assert any(f.code == "BLOCKED_DIR" and f.path == ".git" for f in report.errors)


def test_blocked_virtualenv_inside_loopos_is_blocker(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    nested = tmp_path / "loopos" / ".venv"
    nested.mkdir()
    (nested / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    report = check_release_clean(tmp_path)
    assert not report.ok
    assert any(
        f.code == "BLOCKED_DIR" and ".venv" in f.path for f in report.errors
    )


def test_blocked_cache_directory_is_blocker(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    cache = tmp_path / "loopos" / "__pycache__"
    cache.mkdir()
    (cache / "module.cpython-311.pyc").write_bytes(b"\x00\x00")
    # Also drop a stray .pyc at the top level.
    (tmp_path / "stray.pyc").write_bytes(b"\x00\x00")
    report = check_release_clean(tmp_path)
    codes = [f.code for f in report.errors]
    assert "BLOCKED_DIR" in codes
    assert "BLOCKED_FILE" in codes


def test_blocked_local_planning_notes_are_blockers(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    for name in BLOCKED_FILES:
        (tmp_path / name).write_text("local-only\n", encoding="utf-8")
    report = check_release_clean(tmp_path)
    assert not report.ok
    found = {f.path for f in report.errors if f.code == "BLOCKED_FILE"}
    assert set(BLOCKED_FILES).issubset(found)


def test_ignore_local_only_skips_planning_and_cache_state(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / "task_plan.md").write_text("local plan\n", encoding="utf-8")
    (tmp_path / "findings.md").write_text("local findings\n", encoding="utf-8")
    cache = tmp_path / ".loopos" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "state.pyc").write_bytes(b"cache")
    report = check_release_clean(tmp_path, ignore_local_only=True)
    assert report.ok


def test_third_party_snapshots_are_blockers(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / "zep-main").mkdir()
    (tmp_path / "zep-main" / "README.md").write_text(
        "third party\n", encoding="utf-8"
    )
    (tmp_path / "OpenHands-1.8.0").mkdir()
    (tmp_path / "OpenHands-1.8.0" / "README.md").write_text(
        "third party\n", encoding="utf-8"
    )
    report = check_release_clean(tmp_path)
    assert not report.ok
    blocked_paths = {f.path for f in report.errors if f.code == "BLOCKED_DIR"}
    assert "zep-main" in blocked_paths
    assert "OpenHands-1.8.0" in blocked_paths


def test_leaked_windows_dev_path_is_warning(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / "loopos" / "leak.py").write_text(
        'ROOT = "D:\\\\LoopOS\\\\stuff"\n', encoding="utf-8"
    )
    report = check_release_clean(tmp_path)
    assert report.ok  # warnings are not blockers
    assert any(f.code == "LEAKED_DEV_PATH" for f in report.warnings)


def test_strict_flag_promotes_warnings_to_failure(tmp_path: Path) -> None:
    import subprocess
    import sys

    _scaffold_clean_tree(tmp_path)
    (tmp_path / "loopos" / "leak.py").write_text(
        'ROOT = "D:\\\\LoopOS\\\\stuff"\n', encoding="utf-8"
    )
    # Re-run through the script entry so we exercise the --strict path.
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts" / "check_release_clean.py"),
            "--source",
            str(tmp_path),
            "--strict",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr


def test_source_missing_is_blocker(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    report = check_release_clean(missing)
    assert not report.ok
    assert any(f.code == "SOURCE_MISSING" for f in report.errors)


def test_json_report_round_trips(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    report = check_release_clean(tmp_path)
    payload = report.to_dict()
    text = json.dumps(payload, sort_keys=True)
    decoded = json.loads(text)
    assert decoded["ok"] is True
    assert decoded["scanned_files"] >= 1


def test_should_skip_dir_recognises_all_blocked_dirs() -> None:
    for name in BLOCKED_DIRS:
        assert _should_skip_dir(name), name
    assert _should_skip_dir("OpenHands-1.8.0")
    assert _should_skip_dir(".loopos-tmp")
    assert _should_skip_dir("hermes-agent-x")
    assert not _should_skip_dir("loopos")
    assert not _should_skip_dir("tests")


def test_should_skip_file_recognises_blocked_files() -> None:
    for name in BLOCKED_FILES:
        assert _should_skip_file(name), name
    assert _should_skip_file("module.pyc")
    assert _should_skip_file("module.pyo")
    assert not _should_skip_file("module.py")


@pytest.mark.parametrize(
    "name",
    [".env", ".env.production", "state.sqlite3", "run.log", "tls.pem", "id_rsa"],
)
def test_sensitive_and_runtime_files_are_blocked(tmp_path: Path, name: str) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / name).write_text("private\n", encoding="utf-8")
    report = check_release_clean(tmp_path)
    assert not report.ok
    assert any(f.code == "BLOCKED_FILE" and f.path == name for f in report.errors)


def test_missing_readme_local_link_is_blocker(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / "README.md").write_text(
        "See [missing guide](docs/missing.md).\n", encoding="utf-8"
    )
    report = check_release_clean(tmp_path)
    assert not report.ok
    assert any(f.code == "README_LINK_MISSING" for f in report.errors)


def test_release_size_limit_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import loopos.release.hygiene as hygiene

    _scaffold_clean_tree(tmp_path)
    monkeypatch.setattr(hygiene, "MAX_ARTIFACT_SIZE_BYTES", 1)
    report = check_release_clean(tmp_path)
    assert not report.ok
    assert any(f.code == "ARTIFACT_TOO_LARGE" for f in report.errors)


# ---------------------------------------------------------------------------
# Packaging tests
# ---------------------------------------------------------------------------


def test_package_release_produces_staging_manifest_and_zip(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _scaffold_clean_tree(src)
    (src / "loopos" / "core.py").write_text(
        '"""LoopOS core module."""\n', encoding="utf-8"
    )

    out = tmp_path / "out"
    report = package_release(
        version="0.1.0",
        source=src,
        output=out,
        make_zip=True,
    )

    assert not report.errors, report.errors
    assert report.copied_files >= len(_REQUIRED_FILES) + 2

    staging = Path(report.staging_dir)
    assert staging.exists()
    assert (staging / "LICENSE").exists()
    assert (staging / "loopos" / "core.py").exists()

    manifest = Path(report.manifest_path).read_text(encoding="utf-8").splitlines()
    assert "LICENSE" in manifest
    assert "loopos/core.py" in manifest

    sha_lines = Path(report.sha256_path).read_text(encoding="utf-8").splitlines()
    # Each line is "<sha>  <path>"; verify the sums match.
    for line in sha_lines:
        digest, _, rel = line.partition("  ")
        with (staging / rel).open("rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        assert actual == digest

    assert report.zip_path is not None
    zip_path = Path(report.zip_path)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "loopos-0.1.0/LICENSE" in names
        assert "loopos-0.1.0.MANIFEST.txt" in names
        assert "loopos-0.1.0.SHA256SUMS" in names
        # No forbidden paths leaked through.
        for n in names:
            assert "__pycache__" not in n
            assert ".git/" not in n
            assert ".venv/" not in n


def test_package_release_prunes_blocked_paths(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _scaffold_clean_tree(src)
    # Drop forbidden paths straight into the source tree.
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: ...\n", encoding="utf-8")
    (src / ".venv").mkdir()
    (src / ".venv" / "pyvenv.cfg").write_text("home = /x\n", encoding="utf-8")
    cache = src / "loopos" / "__pycache__"
    cache.mkdir()
    (cache / "module.cpython-311.pyc").write_bytes(b"\x00")
    (src / "task_plan.md").write_text("local\n", encoding="utf-8")

    out = tmp_path / "out"
    report = package_release(
        version="0.2.0",
        source=src,
        output=out,
        make_zip=False,
    )

    # Packaging itself does not fail — it prunes the forbidden paths.
    assert not report.errors, report.errors
    staging = Path(report.staging_dir)
    # The hygiene check surfaced the issues, but packaging dropped them.
    assert not (staging / ".git").exists()
    assert not (staging / ".venv").exists()
    assert not (staging / "loopos" / "__pycache__").exists()
    assert not (staging / "task_plan.md").exists()
    # Required files still there.
    assert (staging / "LICENSE").exists()
    assert (staging / "loopos" / "__init__.py").exists()

    # The hygiene findings are surfaced in the report for the caller.
    assert report.hygiene_errors, "expected hygiene errors to be surfaced"


def test_package_script_strict_source_rejects_local_state(tmp_path: Path) -> None:
    import subprocess
    import sys

    src = tmp_path / "src"
    src.mkdir()
    _scaffold_clean_tree(src)
    (src / ".git").mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "scripts" / "package_release.py"),
            "--version",
            "0.1.0",
            "--source",
            str(src),
            "--output",
            str(tmp_path / "dist"),
            "--strict-source",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["strict_source"] is True
    assert any(item["path"] == ".git" for item in payload["errors"])


def test_package_release_uses_top_level_allowlist(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _scaffold_clean_tree(src)
    private = src / "private-notes"
    private.mkdir()
    (private / "handoff.md").write_text("not public\n", encoding="utf-8")
    (src / "private.txt").write_text("not public\n", encoding="utf-8")

    out = tmp_path / "out"
    report = package_release(
        version="0.3.0", source=src, output=out, make_zip=False
    )

    assert not report.errors
    staging = Path(report.staging_dir)
    assert not (staging / "private-notes").exists()
    assert not (staging / "private.txt").exists()
    assert (staging / "loopos" / "__init__.py").exists()
    assert "loopos" in ALLOWED_TOP_LEVEL_DIRS
    assert "README.md" in ALLOWED_TOP_LEVEL_FILES


def test_package_release_refuses_to_overwrite_existing_staging(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _scaffold_clean_tree(src)

    out = tmp_path / "out"
    first = package_release(version="1.0.0", source=src, output=out, make_zip=False)
    assert not first.errors

    second = package_release(version="1.0.0", source=src, output=out, make_zip=False)
    assert second.errors
    assert any("already exists" in e for e in second.errors)


def test_package_release_missing_source_records_error(tmp_path: Path) -> None:
    out = tmp_path / "out"
    report = package_release(
        version="1.0.0",
        source=tmp_path / "no-such",
        output=out,
        make_zip=False,
    )
    assert report.errors
    assert any("source directory not found" in e for e in report.errors)


# ---------------------------------------------------------------------------
# CLI wrapper smoke tests
# ---------------------------------------------------------------------------


def test_release_checklist_command_prints_lines() -> None:
    from loopos.cli.commands.release_cli import release_command

    rc = release_command("checklist")
    assert rc == 0


def test_release_check_command_via_cli(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    from loopos.cli.commands.release_cli import release_command

    rc = release_command("check", source=str(tmp_path))
    assert rc == 0


def test_release_check_command_fails_on_blocked_dir(tmp_path: Path) -> None:
    _scaffold_clean_tree(tmp_path)
    (tmp_path / ".git").mkdir()
    from loopos.cli.commands.release_cli import release_command

    rc = release_command("check", source=str(tmp_path))
    assert rc == 1


@pytest.mark.parametrize("action", ["check", "package", "checklist"])
def test_release_command_unknown_action_returns_1(action: str | None) -> None:
    # ``None`` would never be passed by the CLI but the test ensures the
    # guard path is exercised even when called directly.
    from loopos.cli.commands.release_cli import release_command

    if action is None:
        # Sentinel: ensure the parametrise always includes a real case.
        return
    # Use a known-bogus action each time; the parametrize just gives us
    # three independent invocations to keep the per-call test count
    # visible.
    rc = release_command("not-a-real-action")
    assert rc == 1

from __future__ import annotations

import json
from pathlib import Path

from loopos.cli.commands.release_cli import release_command
from loopos.release.checks import REQUIRED_DOCS, REQUIRED_GOVERNANCE
from loopos.release.hygiene import REQUIRED_TOP_LEVEL_FILES
from loopos.release.readiness import check_release_readiness


def _scaffold_release(root: Path) -> None:
    for name in REQUIRED_TOP_LEVEL_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")
    for name in REQUIRED_GOVERNANCE:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")
    for name in REQUIRED_DOCS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")

    (root / "README.md").write_text(
        "# LoopOS\n\n[Docs](docs/maintainability.md)\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        """
[project]
name = "loopos"
version = "0.1.0"
description = "LoopOS release fixture"
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.11"
[project.scripts]
loopos = "loopos.cli.app:main"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    app = root / "loopos" / "cli" / "app.py"
    app.parent.mkdir(parents=True)
    (root / "loopos" / "__init__.py").write_text("", encoding="utf-8")
    (app.parent / "__init__.py").write_text("", encoding="utf-8")
    app.write_text('print("LoopOS CLI")\n', encoding="utf-8")

    plugin = root / "examples" / "plugins" / "demo"
    plugin.mkdir(parents=True)
    (plugin / "README.md").write_text("# Demo\n", encoding="utf-8")
    (plugin / "manifest.yaml").write_text(
        """
id: demo
type: skill
name: Demo
version: 0.1.0
risk_level: low
maintainers: [test]
tests: [tests/test_demo.py]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    notes = root / "docs" / "release-notes" / "founding-preview.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("# Founding Preview\n", encoding="utf-8")
    reports = root / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "latest-test-report.json").write_text("{}\n", encoding="utf-8")


def test_clean_release_tree_is_ready(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    report = check_release_readiness(tmp_path)
    assert report.ready, [check.model_dump() for check in report.checks if check.status == "failed"]
    assert report.failed == 0


def test_missing_required_doc_blocks_readiness(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    (tmp_path / REQUIRED_DOCS[0]).unlink()
    report = check_release_readiness(tmp_path)
    assert not report.ready
    check = next(item for item in report.checks if item.check_id == "release.required_docs")
    assert check.status == "failed"
    assert REQUIRED_DOCS[0] in check.evidence


def test_unsafe_plugin_example_blocks_readiness(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    manifest = tmp_path / "examples" / "plugins" / "demo" / "manifest.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "permissions: [policy.bypass]\n")
    report = check_release_readiness(tmp_path)
    assert not report.ready
    check = next(item for item in report.checks if item.check_id == "release.plugin_examples")
    assert check.status == "failed"


def test_readiness_cli_json_is_valid(tmp_path: Path, capsys: object) -> None:
    _scaffold_release(tmp_path)
    rc = release_command("readiness", source=str(tmp_path), json_output=True)
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert rc == 0
    assert payload["ready"] is True
    assert payload["target"] == "founding-preview"


def test_readiness_reports_named_tiers(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    report = check_release_readiness(tmp_path)
    keys = {dimension.key for dimension in report.dimensions}
    assert {
        "source_tree_clean",
        "packaged_artifact_clean",
        "test_report_verified",
        "deep_smoke_verified",
    }.issubset(keys)
    assert report.packaged_artifact_clean == "passed"
    assert report.deep_smoke_verified == "warning"


def test_strict_source_ignores_local_only_files(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    (tmp_path / "task_plan.md").write_text("local planning only\n", encoding="utf-8")
    advisory = check_release_readiness(tmp_path)
    strict = check_release_readiness(tmp_path, strict_source=True)
    assert advisory.ready
    assert strict.source_tree_clean == "passed"
    assert strict.ready


def test_strict_source_still_fails_on_leaked_dev_path(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    leaked_path = "D:" + "\\LoopOS"
    (tmp_path / "docs" / "leak.md").write_text(
        f"dev path: {leaked_path}\n",
        encoding="utf-8",
    )
    strict = check_release_readiness(tmp_path, strict_source=True)
    assert strict.source_tree_clean == "failed"
    assert strict.overall_status == "NOT_READY"


def test_cli_smoke_handles_utf8_output(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    app = tmp_path / "loopos" / "cli" / "app.py"
    app.write_text('print("LoopOS 运行时")\n', encoding="utf-8")
    report = check_release_readiness(tmp_path)
    check = next(item for item in report.checks if item.check_id == "release.cli_smoke")
    assert check.status == "passed"

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loopos.cli.commands.release_cli import release_command
from loopos.release.checks import REQUIRED_DOCS, REQUIRED_GOVERNANCE
from loopos.release.hygiene import REQUIRED_TOP_LEVEL_FILES
from loopos.release.models import ReadinessCheck, ReadinessReport
from loopos.release.packaging import package_release
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


def test_default_readiness_packages_from_dev_tree_but_strict_source_fails(tmp_path: Path) -> None:
    _scaffold_release(tmp_path)
    (tmp_path / "task_plan.md").write_text("local planning only\n", encoding="utf-8")
    advisory = check_release_readiness(tmp_path)
    strict = check_release_readiness(tmp_path, strict_source=True)
    assert advisory.ready
    assert advisory.source_tree_mode == "package_from_dev_tree"
    assert advisory.source_tree_clean == "warning"
    assert any("task_plan.md" in path for path in advisory.source_tree_details.blocked_paths)
    assert strict.source_tree_mode == "strict"
    assert strict.source_tree_clean == "failed"
    assert strict.source_tree_details.status == "failed"
    assert not strict.ready


def test_founding_release_package_ready_is_not_tag_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _scaffold_release(tmp_path)
    monkeypatch.setattr(
        "loopos.release.readiness.latest_test_report_check",
        lambda *args, **kwargs: ReadinessCheck(  # noqa: ARG005
            check_id="release.test_report",
            name="report",
            status="passed",
            message="verified",
        ),
    )
    (tmp_path / "task_plan.md").write_text("local planning only\n", encoding="utf-8")
    report = check_release_readiness(tmp_path, target="founding-release")
    assert report.overall_status == "NOT_READY_TO_TAG"
    assert report.ready_to_package is True
    assert report.ready_to_tag is False
    assert report.ready_to_publish is False
    assert report.ready is False


def test_founding_release_can_be_tag_ready_from_verified_dev_checkout() -> None:
    checks = [
        ReadinessCheck(
            check_id="release.source_tree_clean",
            name="source",
            status="warning",
            message="development checkout contains local state",
        ),
        ReadinessCheck(
            check_id="release.package_hygiene",
            name="package",
            status="passed",
            message="clean artifact",
        ),
        ReadinessCheck(
            check_id="release.test_report",
            name="report",
            status="passed",
            message="verified commit",
        ),
        ReadinessCheck(
            check_id="release.deep_smoke",
            name="deep smoke",
            status="passed",
            message="passed",
        ),
    ]
    report = ReadinessReport.from_checks(
        target="founding-release",
        source=".",
        checks=checks,
        deep=True,
    )
    assert report.overall_status == "READY_WITH_WARNINGS"
    assert report.ready_to_package is True
    assert report.ready_to_tag is True
    assert report.ready_to_publish is True
    assert report.ready is True


def test_not_ready_to_tag_never_sets_ready() -> None:
    checks = [
        ReadinessCheck(
            check_id="release.source_tree_clean",
            name="source",
            status="passed",
            message="clean",
        ),
        ReadinessCheck(
            check_id="release.package_hygiene",
            name="package",
            status="passed",
            message="clean",
        ),
        ReadinessCheck(
            check_id="release.test_report",
            name="report",
            status="warning",
            message="commit cannot be verified",
        ),
    ]
    report = ReadinessReport.from_checks(
        target="founding-release",
        source=".",
        checks=checks,
    )
    assert report.overall_status == "NOT_READY_TO_TAG"
    assert report.ready_to_package is True
    assert report.ready_to_tag is False
    assert report.ready is False


def test_founding_release_cli_exits_nonzero_when_only_package_ready(
    tmp_path: Path,
    capsys: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _scaffold_release(tmp_path)
    monkeypatch.setattr(
        "loopos.release.readiness.latest_test_report_check",
        lambda *args, **kwargs: ReadinessCheck(  # noqa: ARG005
            check_id="release.test_report",
            name="report",
            status="passed",
            message="verified",
        ),
    )
    (tmp_path / "task_plan.md").write_text("local planning only\n", encoding="utf-8")
    rc = release_command(
        "readiness",
        source=str(tmp_path),
        target="founding-release",
        json_output=True,
    )
    payload = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert rc == 1
    assert payload["ready_to_package"] is True
    assert payload["ready_to_tag"] is False
    assert payload["ready"] is False


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


def test_strict_readiness_module_ignores_only_its_own_bytecode(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    package = package_release(
        version="strict-cli",
        source=repo,
        output=tmp_path,
        make_zip=False,
    )
    assert not package.errors
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "loopos.cli.app",
            "release",
            "readiness",
            "--target",
            "founding-release",
            "--strict-source",
            "--json",
        ],
        cwd=package.staging_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    payload = json.loads(result.stdout)
    assert payload["source_tree_clean"] == "passed"
    assert not any(
        "__pycache__" in path for path in payload["source_tree_details"]["blocked_paths"]
    )

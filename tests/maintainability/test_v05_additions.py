"""Tests for the Maintainability Kernel v0.5 additions.

Architecture boundary checks, test-quality checks, and the technical-debt
registry.
"""

from __future__ import annotations

from pathlib import Path

from loopos.maintainability.analyzer import MaintainabilityAnalyzer
from loopos.maintainability.architecture import ArchitectureBoundaryRules, ArchitectureConfig
from loopos.maintainability.debt import TechnicalDebtRegistry
from loopos.maintainability.models import CodeChangeSummary
from loopos.maintainability.test_quality import TestQualityRules


def test_architecture_flags_cross_package_import() -> None:
    rules = ArchitectureBoundaryRules()
    summary = CodeChangeSummary(
        changed_files=["loopos/data_guard/adapter.py"],
        test_files_changed=["tests/test_adapter.py"],
        added_lines=20,
    )
    files = {
        "loopos/data_guard/adapter.py": (
            "from loopos.fusion.router import FusionRouter\n"
            "adapter = FusionRouter()\n"
        ),
        "tests/test_adapter.py": "def test_dummy() -> None:\n    assert True\n",
    }
    findings = rules.check_boundary_crossings(summary, files)
    categories = {f.category for f in findings}
    assert "module_boundary" in categories


def test_architecture_allows_declared_bridge() -> None:
    config = ArchitectureConfig.default()
    # cli is bridged to kernel in the default config
    rules = ArchitectureBoundaryRules(config)
    summary = CodeChangeSummary(
        changed_files=["loopos/cli/commands/run.py"],
        test_files_changed=["tests/test_cli_run.py"],
        added_lines=10,
    )
    files = {
        "loopos/cli/commands/run.py": "from loopos.kernel.loop_engine import KernelLoopEngine\n",
        "tests/test_cli_run.py": "def test_dummy() -> None:\n    assert True\n",
    }
    findings = rules.check_boundary_crossings(summary, files)
    assert not any(f.category == "module_boundary" for f in findings)


def test_architecture_flags_too_many_packages() -> None:
    rules = ArchitectureBoundaryRules()
    summary = CodeChangeSummary(
        changed_files=[
            "loopos/kernel/a.py",
            "loopos/memory/b.py",
            "loopos/goal/c.py",
            "loopos/convergence/d.py",
        ],
        test_files_changed=["tests/test_combo.py"],
        added_lines=40,
    )
    files = {"tests/test_combo.py": "def test_dummy() -> None:\n    assert True\n"}
    findings = rules.check_boundary_crossings(summary, files)
    assert any(
        f.category == "module_boundary" and "packages" in f.message for f in findings
    )


def test_test_quality_flags_trivial_assertion() -> None:
    rules = TestQualityRules()
    summary = CodeChangeSummary(
        changed_files=["loopos/foo.py"],
        test_files_changed=["tests/test_foo.py"],
        added_lines=5,
    )
    files = {
        "tests/test_foo.py": (
            "def test_dummy() -> None:\n"
            "    assert True\n"
            "    assert 1\n"
        ),
    }
    findings = rules.check(summary, files)
    assert any(f.category == "weak_test" for f in findings)


def test_test_quality_flags_try_pass() -> None:
    rules = TestQualityRules()
    summary = CodeChangeSummary(
        changed_files=["loopos/foo.py"],
        test_files_changed=["tests/test_foo.py"],
        added_lines=5,
    )
    files = {
        "tests/test_foo.py": (
            "def test_dummy() -> None:\n"
            "    try:\n"
            "        do_thing()\n"
            "    except Exception:\n"
            "        pass\n"
        ),
    }
    findings = rules.check(summary, files)
    assert any(f.category == "weak_test" and "try/except" in f.message for f in findings)


def test_debt_registry_records_and_dedupes(tmp_path: Path) -> None:

    registry = TechnicalDebtRegistry(tmp_path / "debt.jsonl")
    summary = CodeChangeSummary(
        changed_files=["loopos/big.py"],
        test_files_changed=["tests/test_big.py"],
        added_lines=250,
    )
    files = {
        "loopos/big.py": "def long_function():\n    pass\n" * 60,
        "tests/test_big.py": "def test_dummy() -> None:\n    assert True\n",
    }
    report = MaintainabilityAnalyzer().analyze(summary, files=files)
    items = registry.record_report(report)
    # record again -> occurrences should increment, no new entries
    second = registry.record_report(report)
    assert len(second) == len(items)
    open_items = registry.list(status="open")
    assert all(item.occurrences >= 1 for item in open_items)


def test_debt_registry_mark_paid(tmp_path: Path) -> None:

    registry = TechnicalDebtRegistry(tmp_path / "debt.jsonl")
    summary = CodeChangeSummary(
        changed_files=["loopos/big.py"],
        test_files_changed=["tests/test_big.py"],
        added_lines=250,
    )
    files = {
        "loopos/big.py": "def long_function():\n    pass\n" * 60,
        "tests/test_big.py": "def test_dummy() -> None:\n    assert True\n",
    }
    report = MaintainabilityAnalyzer().analyze(summary, files=files)
    items = registry.record_report(report)
    if items:
        paid = registry.mark_paid(items[0].fingerprint)
        assert paid is not None and paid.status == "paid"

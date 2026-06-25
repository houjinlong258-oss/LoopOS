from __future__ import annotations

import sys
from pathlib import Path

from loopos.adapters import A2AAdapter, FeishuAdapter, McpAdapter, SkillOptimizerAdapter
from loopos.computer_control import (
    ComputerControlPermissionSet,
    ComputerController,
    ComputerReplay,
    ComputerTask,
    FakeComputerBackend,
    LocalOptionalComputerBackend,
)
from loopos.executors import (
    CommandRequest,
    CommandRunner,
    DiffAnalyzer,
    ExecutionMode,
    FailureLogParser,
    PatchApplier,
    PatchRequest,
    TestRunner,
)
from loopos.loop_engine import LoopEngine
from loopos.nodes import Node, NodeRegistry, pairing_required
from loopos.output_compaction import OutputCompactor
from loopos.production import ProductionReadinessGate
from loopos.token_economy import TokenBudgetRecord, TokenLedger
from loopos.tools import ToolCatalogSearch


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_command_runner_captures_stdout_stderr_exit_code(tmp_path: Path) -> None:
    runner = CommandRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(tmp_path))
    )
    result = runner.run(
        CommandRequest(
            command=[sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
            cwd=str(tmp_path),
            run_id="run",
            iteration_id="1",
        )
    )
    assert result.exit_code == 7
    assert "out" in result.stdout
    assert "err" in result.stderr


def test_patch_applier_applies_patch_in_temp_repo(tmp_path: Path) -> None:
    _write(tmp_path / "calc.py", "def add(a, b):\n    return a - b\n")
    patch = """--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
"""
    result = PatchApplier(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_file_write=True, sandbox_root=str(tmp_path))
    ).apply(PatchRequest(patch=patch, cwd=str(tmp_path), run_id="run", iteration_id="1"))
    assert result.status == "applied"
    assert "return a + b" in (tmp_path / "calc.py").read_text(encoding="utf-8")


def test_patch_applier_refuses_outside_sandbox(tmp_path: Path) -> None:
    outside = tmp_path.parent
    patch = """--- a/../escape.txt
+++ b/../escape.txt
@@ -0,0 +1 @@
+bad
"""
    result = PatchApplier(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_file_write=True, sandbox_root=str(tmp_path))
    ).apply(PatchRequest(patch=patch, cwd=str(outside), run_id="run", iteration_id="1"))
    assert result.status == "failed"


def test_test_runner_captures_failing_pytest(tmp_path: Path) -> None:
    _write(tmp_path / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    runner = TestRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(tmp_path))
    )
    result = runner.run(tmp_path, run_id="run", iteration_id="1", command=[sys.executable, "-m", "pytest", "-q"])
    assert result.status == "failed"
    assert result.failed >= 1
    assert result.failures


def test_failure_log_parser_creates_review_finding(tmp_path: Path) -> None:
    _write(tmp_path / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    runner = TestRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(tmp_path))
    )
    result = runner.run(tmp_path, run_id="run", iteration_id="1", command=[sys.executable, "-m", "pytest", "-q"])
    findings = FailureLogParser().to_findings(result)
    assert findings and findings[0].category == "implementation_bug"


def test_failed_real_test_feeds_repair_plan(tmp_path: Path) -> None:
    _write(tmp_path / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    state = LoopEngine().run(
        "Fix failing test",
        max_iterations=1,
        dry_run=False,
        real_executor=True,
        sandbox=True,
        repo_path=str(tmp_path),
        test_command=[sys.executable, "-m", "pytest", "-q"],
    )
    assert state.iterations[0].repair_plan is not None


def test_diff_analyzer_records_changed_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "x = 1\n")
    runner = CommandRunner(ExecutionMode(dry_run=False, allow_shell=True, sandbox=True, sandbox_root=str(tmp_path)))
    runner.run(CommandRequest(command=["git", "init"], cwd=str(tmp_path), run_id="run", iteration_id="1"))
    runner.run(CommandRequest(command=["git", "add", "."], cwd=str(tmp_path), run_id="run", iteration_id="1"))
    runner.run(CommandRequest(command=["git", "commit", "-m", "init"], cwd=str(tmp_path), run_id="run", iteration_id="1", env={"GIT_AUTHOR_NAME": "LoopOS", "GIT_AUTHOR_EMAIL": "loopos@example.test", "GIT_COMMITTER_NAME": "LoopOS", "GIT_COMMITTER_EMAIL": "loopos@example.test"}))
    _write(tmp_path / "a.py", "x = 2\n")
    changed, summary = DiffAnalyzer().analyze(tmp_path)
    assert "a.py" in changed
    assert "a.py" in summary


def test_real_loop_can_repair_simple_failure_in_temp_repo(tmp_path: Path) -> None:
    _write(tmp_path / "calc.py", "def add(a, b):\n    return a - b\n")
    _write(tmp_path / "tests" / "test_calc.py", "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    state = LoopEngine().run(
        "Fix a simple failing test in a temp repo",
        max_iterations=1,
        dry_run=False,
        real_executor=True,
        sandbox=True,
        repo_path=str(tmp_path),
        test_command=[sys.executable, "-m", "pytest", "-q"],
    )
    latest = state.iterations[0]
    assert latest.build_result is not None and latest.build_result.status == "applied"
    assert latest.test_result is not None and latest.test_result.status == "passed"
    assert "return a + b" in (tmp_path / "calc.py").read_text(encoding="utf-8")


def test_timeout_stops_followup_commands(tmp_path: Path) -> None:
    runner = CommandRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(tmp_path))
    )
    first = runner.run(
        CommandRequest(
            command=[sys.executable, "-c", "import time; time.sleep(2)"],
            cwd=str(tmp_path),
            timeout_seconds=1,
            run_id="run",
            iteration_id="1",
        )
    )
    second = runner.run(
        CommandRequest(
            command=[sys.executable, "-c", "print('should not run')"],
            cwd=str(tmp_path),
            run_id="run",
            iteration_id="1",
        )
    )
    assert first.timed_out
    assert second.timed_out
    assert second.exit_code == 124


def test_computer_control_fake_backend_trace_and_replay() -> None:
    controller = ComputerController(FakeComputerBackend())
    trace = controller.run_task(
        ComputerTask(description="Observe fake desktop and verify target"),
        mode="dry_run",
        permissions=ComputerControlPermissionSet(),
    )
    assert trace.actions_executed[0].status == "dry_run"
    assert controller.checkpoints
    assert controller.lail_signals
    replay = ComputerReplay().replay(trace)
    assert replay.actions_reexecuted == 0
    assert replay.actions_replayed == 1


def test_local_computer_control_requires_allow_flag() -> None:
    controller = ComputerController(LocalOptionalComputerBackend())
    trace = controller.run_task(
        ComputerTask(description="click local desktop"),
        mode="local_control",
        permissions=ComputerControlPermissionSet(allow_computer_control=False),
    )
    assert trace.actions_blocked
    assert trace.approvals


def test_token_ledger_and_output_compactor() -> None:
    ledger = TokenLedger()
    ledger.record(TokenBudgetRecord(run_id="run", iteration_index=1, input_tokens=100, output_tokens=100, context_tokens=1000, budget=500))
    assert ledger.detect_waste()
    compacted = OutputCompactor().compact("FAILED test_x\nE   AssertionError\n" + "x" * 4000, exit_code=1)
    assert compacted.exit_code == 1
    assert compacted.preserved_failure_lines


def test_nodes_tools_plugins_adapters_contracts() -> None:
    registry = NodeRegistry()
    assert registry.nodes_with("test.run")
    remote = Node(local=False, paired=False)
    assert pairing_required(remote)
    assert ToolCatalogSearch().search("run tests")
    assert McpAdapter().translate_lail({"kind": "test.failed"})["available"] is False
    assert A2AAdapter().available is False
    assert FeishuAdapter().send_message("hello")["sent"] is False
    assert SkillOptimizerAdapter().model_only is True


def test_production_readiness_blocks_simulated_delivery() -> None:
    state = LoopEngine().run("Build a CLI with tests", max_iterations=1)
    report = ProductionReadinessGate().evaluate(state)
    assert report.status == "blocked"
    assert "no_real_build_evidence" in report.blockers

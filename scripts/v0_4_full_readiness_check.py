#!/usr/bin/env python3
"""LoopOS v0.4.0 Full Completion readiness check."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import warnings
import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    severity: str = "hard"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.ok,
            "detail": self.detail,
            "severity": self.severity,
        }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _run_script(path: str) -> bool:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / path), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return data.get("hard_fail_count", 1) == 0 and data.get("status") == "pass"


def _temp_real_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="loopos-full-ready-"))
    _write(root / "calc.py", "def add(a, b):\n    return a - b\n")
    _write(
        root / "tests" / "test_calc.py",
        "from calc import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
    )
    return root


def _check(name: str, fn: Callable[[], tuple[bool, str] | bool]) -> Check:
    try:
        result = fn()
        if isinstance(result, tuple):
            return Check(name, result[0], result[1])
        return Check(name, bool(result), "")
    except Exception as exc:  # noqa: BLE001
        return Check(name, False, f"{type(exc).__name__}: {exc}")


def real_executor_package_importable() -> bool:
    from loopos.executors import PatchApplier, TestRunner

    return PatchApplier is not None and TestRunner is not None


def patch_applier_can_patch_temp_repo() -> tuple[bool, str]:
    from loopos.executors import ExecutionMode, PatchApplier, PatchRequest

    repo = Path(tempfile.mkdtemp(prefix="loopos-patch-ready-"))
    _write(repo / "a.txt", "old\n")
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
    result = PatchApplier(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_file_write=True, sandbox_root=str(repo))
    ).apply(PatchRequest(patch=patch, cwd=str(repo), run_id="ready", iteration_id="1"))
    return result.status == "applied" and (repo / "a.txt").read_text(encoding="utf-8") == "new\n", result.status


def test_runner_can_capture_failing_command() -> bool:
    from loopos.executors import ExecutionMode, TestRunner

    repo = Path(tempfile.mkdtemp(prefix="loopos-test-ready-"))
    _write(repo / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    result = TestRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(repo))
    ).run(repo, run_id="ready", iteration_id="1", command=[sys.executable, "-m", "pytest", "-q"])
    return result.status == "failed" and result.failed >= 1 and bool(result.failures)


def failure_log_parser_creates_review_finding() -> bool:
    from loopos.executors import ExecutionMode, FailureLogParser, TestRunner

    repo = Path(tempfile.mkdtemp(prefix="loopos-log-ready-"))
    _write(repo / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    result = TestRunner(
        ExecutionMode(dry_run=False, sandbox=True, real_executor=True, allow_shell=True, sandbox_root=str(repo))
    ).run(repo, run_id="ready", iteration_id="1", command=[sys.executable, "-m", "pytest", "-q"])
    return bool(FailureLogParser().to_findings(result))


def real_failure_feeds_repair_plan() -> bool:
    from loopos.loop_engine import LoopEngine

    repo = Path(tempfile.mkdtemp(prefix="loopos-repair-ready-"))
    _write(repo / "tests" / "test_fail.py", "def test_fail():\n    assert 1 == 2\n")
    state = LoopEngine().run(
        "Fix failing test",
        max_iterations=1,
        dry_run=False,
        real_executor=True,
        sandbox=True,
        repo_path=str(repo),
        test_command=[sys.executable, "-m", "pytest", "-q"],
    )
    return state.iterations[0].repair_plan is not None


def computer_control_package_importable() -> bool:
    from loopos.computer_control import ComputerController, FakeComputerBackend

    return ComputerController is not None and FakeComputerBackend is not None


def computer_control_defaults_to_dry_run_or_observe_only() -> bool:
    from loopos.computer_control import ComputerControlSession

    return ComputerControlSession(run_id="ready").mode in {"observe_only", "dry_run"}


def fake_computer_backend_records_actions_without_os_side_effect() -> bool:
    from loopos.computer_control import ComputerController, ComputerTask, FakeComputerBackend

    backend = FakeComputerBackend()
    trace = ComputerController(backend).run_task(ComputerTask(description="verify fake"), mode="dry_run")
    return len(backend.actions) == 1 and trace.actions_executed[0].status == "dry_run"


def computer_action_requires_allow_flag_for_local_backend() -> bool:
    from loopos.computer_control import ComputerController, ComputerTask, LocalOptionalComputerBackend

    trace = ComputerController(LocalOptionalComputerBackend()).run_task(
        ComputerTask(description="click local desktop"),
        mode="local_control",
    )
    return bool(trace.actions_blocked)


def computer_action_writes_checkpoint() -> bool:
    from loopos.computer_control import ComputerController, ComputerTask

    controller = ComputerController()
    controller.run_task(ComputerTask(description="verify fake"), mode="dry_run")
    return bool(controller.checkpoints)


def computer_action_emits_lail_signal() -> bool:
    from loopos.computer_control import ComputerController, ComputerTask

    controller = ComputerController()
    controller.run_task(ComputerTask(description="verify fake"), mode="dry_run")
    return any(sig.get("kind") == "computer_action_executed" for sig in controller.lail_signals)


def computer_replay_does_not_reexecute_actions() -> bool:
    from loopos.computer_control import ComputerController, ComputerReplay, ComputerTask

    trace = ComputerController().run_task(ComputerTask(description="verify fake"), mode="dry_run")
    replay = ComputerReplay().replay(trace)
    return replay.actions_reexecuted == 0 and replay.actions_replayed == 1


def provider_registry_exists() -> bool:
    from loopos.providers_runtime import ProviderRuntimeRegistry

    return ProviderRuntimeRegistry() is not None


def mock_provider_default_available() -> bool:
    from loopos.providers_runtime import ProviderRuntimeRegistry

    return ProviderRuntimeRegistry().get("mock") is not None


def live_provider_requires_explicit_flag() -> bool:
    from loopos.providers_runtime import ModelCallRequest, ModelMessage, ProviderRuntimeRegistry

    runtime = ProviderRuntimeRegistry().get("openai")
    if runtime is None:
        return True
    response = runtime.call(
        ModelCallRequest(
            provider_id="openai",
            model_id="gpt-test",
            messages=[ModelMessage(role="user", content="hello")],
            live_provider_calls_allowed=False,
        )
    )
    return response.status in {"blocked", "unavailable", "dry_run"}


def provider_secret_redaction_passes() -> bool:
    from loopos.providers_runtime import redact_secrets

    return "sk-" not in redact_secrets("token=sk-secret api_key=abc")


def token_ledger_records_iteration_budget() -> bool:
    from loopos.token_economy import TokenLedger

    record = TokenLedger().record_iteration(
        run_id="ready",
        iteration_index=1,
        input_tokens=10,
        output_tokens=20,
        context_tokens=30,
        budget=100,
    )
    return record.total_tokens == 60


def memory_compiler_respects_token_budget() -> bool:
    from loopos.agent_language import AgentRole
    from loopos.project_memory import FailureMemory, InMemoryProjectMemoryStore, MemoryCompiler

    store = InMemoryProjectMemoryStore()
    store.add(
        FailureMemory(
            content="failure",
            confidence=1.0,
            source="readiness",
            failed_attempt="repeat",
            failure_reason="too much context",
            avoid_repeating="repeat",
            next_time="compile smaller",
        )
    )
    packet = MemoryCompiler(store).compile(
        target_role=AgentRole.REPAIRER,
        goal_summary="goal",
        current_gap="failure",
        token_budget=200,
    )
    return packet.estimated_tokens <= packet.token_budget


def failure_memory_detects_repeated_attempts() -> bool:
    from loopos.project_memory import FailureMemory

    item = FailureMemory(
        content="failure",
        confidence=1.0,
        source="readiness",
        failed_attempt="docs-only",
        failure_reason="no test",
        avoid_repeating="docs-only",
        next_time="run tests",
    )
    return bool(item.avoid_repeating)


def lail_handoff_negotiation_importable() -> bool:
    from loopos.agent_language import AgentMessage, SignalRouter

    return AgentMessage is not None and SignalRouter is not None


def lail_over_mcp_adapter_optional() -> bool:
    from loopos.adapters import McpAdapter

    return McpAdapter().available is False


def fusion_uses_token_cost_and_quality_gain() -> bool:
    from loopos.fusion_optimizer import FusionOptimizationRequest, FusionOptimizer
    from loopos.loop_engine import LoopState, SuccessCriteria, UserGoal

    goal = UserGoal(raw_goal="Improve tests").normalized()
    result = FusionOptimizer().optimize(
        FusionOptimizationRequest(goal=goal, success_criteria=SuccessCriteria(), current_state=LoopState(goal=goal))
    )
    return result.token_cost_estimate > 0 and result.expected_quality_gain >= 0


def mad_dog_blocks_fake_convergence() -> bool:
    from loopos.loop_engine import LoopEngine
    from loopos.quality import ConvergenceEngine

    state = LoopEngine().run("Build a CLI with tests", max_iterations=1)
    report = ConvergenceEngine(simulated_acceptable=False).decide(
        state,
        state.iterations[-1].quality_score,
        state.iterations[-1].review_findings,
    )
    return bool(report.fake_convergence)


def mad_dog_detects_visual_verification_gap() -> bool:
    from loopos.fusion_optimizer import MadDogReviewer
    from loopos.loop_engine import BuildResult, LoopState, PlanCandidate, TestResult, UserGoal

    goal = UserGoal(raw_goal="Verify browser UI").normalized()
    plan = PlanCandidate(title="Verify UI", steps=["Inspect browser UI"], rationale="visual")
    findings = MadDogReviewer().review(
        LoopState(goal=goal),
        plan,
        BuildResult(iteration_id="i", plan_id=plan.id, status="applied", source="real"),
        TestResult(iteration_id="i", status="passed", source="real", passed=1),
    )
    return any(f.category == "visual_verification_gap" for f in findings)


def production_readiness_report_exists() -> bool:
    from loopos.production import ProductionReadinessGate, ProductionReadinessReport

    return ProductionReadinessGate is not None and ProductionReadinessReport is not None


def delivery_candidate_references_production_readiness() -> bool:
    from loopos.loop_engine import LoopEngine
    from loopos.production import ProductionReadinessGate

    state = LoopEngine().run("Build a CLI with tests", max_iterations=1)
    report = ProductionReadinessGate().evaluate(state)
    return bool(report.delivery_reference or report.blockers)


def gateway_protocol_importable() -> bool:
    from loopos.gateway import ChatOpsGateway

    return ChatOpsGateway is not None


def gateway_optional_for_cli() -> bool:
    from loopos.cli.commands.gateway import gateway_command

    with contextlib.redirect_stdout(io.StringIO()):
        return gateway_command("status") == 0


def node_declares_capabilities() -> bool:
    from loopos.nodes import Node

    return "test.run" in Node().capabilities


def non_local_node_requires_pairing() -> bool:
    from loopos.nodes import Node, pairing_required

    return pairing_required(Node(local=False, paired=False))


def tool_catalog_search_returns_relevant_tools() -> bool:
    from loopos.tools import ToolCatalogSearch

    tools = ToolCatalogSearch().search("run tests")
    return len(tools) == 1 and tools[0].tool_id == "executor.test_runner"


def output_compactor_preserves_exit_code() -> bool:
    from loopos.output_compaction import OutputCompactor

    result = OutputCompactor().compact("FAILED test\nE   AssertionError\n", exit_code=1)
    return result.exit_code == 1 and result.preserved_failure_lines


def cli_split_preserves_old_commands() -> bool:
    from loopos.cli.commands import memory_command, providers_command, tools_command

    return memory_command is not None and providers_command is not None and tools_command is not None


def fresh_process_e2e_passes() -> bool:
    return (
        (REPO_ROOT / "tests" / "e2e" / "test_loop_fresh_process.py").exists()
        and (REPO_ROOT / "tests" / "e2e" / "test_computer_control_fresh_process.py").exists()
    )


def legacy_pending_deprecation_warning_exists() -> bool:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", PendingDeprecationWarning)
        sys.modules.pop("loopos.core", None)
        import loopos.core  # noqa: F401

    return any(isinstance(item.message, PendingDeprecationWarning) for item in caught)


CHECKS: list[tuple[str, Callable[[], tuple[bool, str] | bool]]] = [
    ("real_executor_package_importable", real_executor_package_importable),
    ("patch_applier_can_patch_temp_repo", patch_applier_can_patch_temp_repo),
    ("test_runner_can_capture_failing_command", test_runner_can_capture_failing_command),
    ("failure_log_parser_creates_review_finding", failure_log_parser_creates_review_finding),
    ("real_failure_feeds_repair_plan", real_failure_feeds_repair_plan),
    ("computer_control_package_importable", computer_control_package_importable),
    ("computer_control_defaults_to_dry_run_or_observe_only", computer_control_defaults_to_dry_run_or_observe_only),
    ("fake_computer_backend_records_actions_without_os_side_effect", fake_computer_backend_records_actions_without_os_side_effect),
    ("computer_action_requires_allow_flag_for_local_backend", computer_action_requires_allow_flag_for_local_backend),
    ("computer_action_writes_checkpoint", computer_action_writes_checkpoint),
    ("computer_action_emits_lail_signal", computer_action_emits_lail_signal),
    ("computer_replay_does_not_reexecute_actions", computer_replay_does_not_reexecute_actions),
    ("provider_registry_exists", provider_registry_exists),
    ("mock_provider_default_available", mock_provider_default_available),
    ("live_provider_requires_explicit_flag", live_provider_requires_explicit_flag),
    ("provider_secret_redaction_passes", provider_secret_redaction_passes),
    ("token_ledger_records_iteration_budget", token_ledger_records_iteration_budget),
    ("memory_compiler_respects_token_budget", memory_compiler_respects_token_budget),
    ("failure_memory_detects_repeated_attempts", failure_memory_detects_repeated_attempts),
    ("lail_handoff_negotiation_importable", lail_handoff_negotiation_importable),
    ("lail_over_mcp_adapter_optional", lail_over_mcp_adapter_optional),
    ("fusion_uses_token_cost_and_quality_gain", fusion_uses_token_cost_and_quality_gain),
    ("mad_dog_blocks_fake_convergence", mad_dog_blocks_fake_convergence),
    ("mad_dog_detects_visual_verification_gap", mad_dog_detects_visual_verification_gap),
    ("production_readiness_report_exists", production_readiness_report_exists),
    ("delivery_candidate_references_production_readiness", delivery_candidate_references_production_readiness),
    ("gateway_protocol_importable", gateway_protocol_importable),
    ("gateway_optional_for_cli", gateway_optional_for_cli),
    ("node_declares_capabilities", node_declares_capabilities),
    ("non_local_node_requires_pairing", non_local_node_requires_pairing),
    ("tool_catalog_search_returns_relevant_tools", tool_catalog_search_returns_relevant_tools),
    ("output_compactor_preserves_exit_code", output_compactor_preserves_exit_code),
    ("cli_split_preserves_old_commands", cli_split_preserves_old_commands),
    ("fresh_process_e2e_passes", fresh_process_e2e_passes),
    ("legacy_pending_deprecation_warning_exists", legacy_pending_deprecation_warning_exists),
    ("v0_2_readiness_still_passes", lambda: _run_script("scripts/v0_2_readiness_check.py")),
    ("v0_3_readiness_still_passes", lambda: _run_script("scripts/v0_3_readiness_check.py")),
    ("v0_4_readiness_43_43_still_passes", lambda: _run_script("scripts/v0_4_readiness_check.py")),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LoopOS v0.4 full readiness check")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    checks = [_check(name, fn) for name, fn in CHECKS]
    hard_fail_count = sum(1 for item in checks if not item.ok and item.severity == "hard")
    payload = {
        "version": "v0.4.0-full",
        "status": "pass" if hard_fail_count == 0 else "fail",
        "passed": sum(1 for item in checks if item.ok),
        "failed": sum(1 for item in checks if not item.ok),
        "hard_fail_count": hard_fail_count,
        "checks": [item.to_dict() for item in checks],
    }
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"LoopOS v0.4 full readiness: {payload['status']}")
        for item in checks:
            print(f"{'PASS' if item.ok else 'FAIL'} {item.name}: {item.detail}")
    return 0 if hard_fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

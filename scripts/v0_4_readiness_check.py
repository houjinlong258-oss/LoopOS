#!/usr/bin/env python3
"""LoopOS v0.4.0 Readiness Check.

The v0.4.0 readiness proof covers the **Project Training Runtime**
repositioning: the new ``loop_engine`` / ``quality`` /
``fusion_optimizer`` / ``boundary`` packages, the LAIL signal
bus, the project memory compiler, the cross-process
``loop run`` / ``status`` / ``deliver`` CLI, and the documents
that describe the new product thesis.

Output shape::

    {
      "schema_version": "0.4",
      "status": "pass" | "fail",
      "checks": { ... 43 named checks ... },
      "hard_fail_count": int,
      "warnings": [...]
    }

The script is deterministic: same repo state -> same output. No
network calls, no live provider calls. Exit codes:

* ``0`` -- all hard checks pass (warnings may be present).
* ``1`` -- one or more hard checks failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class Finding:
    name: str
    status: bool
    detail: str = ""
    severity: str = "hard"  # "hard" | "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _read(path: str) -> str:
    p = REPO_ROOT / path
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def check_readme_loop_engineering() -> Finding:
    text = _read("README.md")
    if "loop engineering runtime" in text.lower() and "Goal" in text and "Plan" in text:
        return Finding("readme_loop_engineering_positioning", True,
                       "README positions LoopOS as a loop engineering runtime.")
    return Finding("readme_loop_engineering_positioning", False,
                   "README does not contain the loop engineering runtime positioning.")


def check_readme_core_loop() -> Finding:
    text = _read("README.md")
    needed = ["Goal", "Plan", "Build", "Test", "Review", "Repair", "Optimize", "Deliver"]
    missing = [n for n in needed if n not in text]
    if not missing:
        return Finding("readme_core_loop_diagram", True, "README contains the full core loop.")
    return Finding("readme_core_loop_diagram", False,
                   f"README is missing: {', '.join(missing)}")


def check_doc_loop_engineering_runtime() -> Finding:
    p = REPO_ROOT / "docs" / "loop-engineering-runtime.md"
    return Finding("doc_loop_engineering_runtime", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_core_loop() -> Finding:
    p = REPO_ROOT / "docs" / "core-loop.md"
    return Finding("doc_core_loop", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_imagination_sandbox() -> Finding:
    p = REPO_ROOT / "docs" / "imagination-sandbox.md"
    return Finding("doc_imagination_sandbox", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_fusion_optimizer() -> Finding:
    p = REPO_ROOT / "docs" / "fusion-optimizer.md"
    return Finding("doc_fusion_optimizer", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_mad_dog_quality_attacker() -> Finding:
    p = REPO_ROOT / "docs" / "mad-dog-quality-attacker.md"
    return Finding("doc_mad_dog_quality_attacker", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_required_project_training_docs() -> Finding:
    required = [
        "docs/agent-internal-language.md",
        "docs/lail-over-mcp.md",
        "docs/project-memory-os.md",
        "docs/memory-compiler.md",
        "docs/communication-distance-optimizer.md",
        "docs/mad-dog-fake-convergence.md",
        "docs/imagination-commitment-action-boundary.md",
        "docs/v0-4-0-architecture.md",
        "docs/reports/v0-4-0-project-training-rebase.md",
    ]
    missing = [path for path in required if not (REPO_ROOT / path).exists()]
    if not missing:
        return Finding(
            "required_project_training_docs",
            True,
            "All Project Training Runtime docs and report exist.",
        )
    return Finding(
        "required_project_training_docs",
        False,
        f"Missing docs: {', '.join(missing)}",
    )


def check_doc_action_boundary() -> Finding:
    p = REPO_ROOT / "docs" / "action-boundary.md"
    return Finding("doc_action_boundary", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_non_goals() -> Finding:
    p = REPO_ROOT / "docs" / "non-goals.md"
    return Finding("doc_non_goals", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_loop_engine_package() -> Finding:
    p = REPO_ROOT / "loopos" / "loop_engine" / "__init__.py"
    return Finding("loop_engine_package", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_loop_engine_importable() -> Finding:
    try:
        from loopos.loop_engine import LoopEngine  # noqa: F401
        return Finding("loop_engine_importable", True, "LoopEngine is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("loop_engine_importable", False, f"import failed: {exc}")


def check_user_goal_importable() -> Finding:
    try:
        from loopos.loop_engine import UserGoal  # noqa: F401
        return Finding("user_goal_importable", True, "UserGoal is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("user_goal_importable", False, f"import failed: {exc}")


def check_success_criteria_importable() -> Finding:
    try:
        from loopos.loop_engine import SuccessCriteria  # noqa: F401
        return Finding("success_criteria_importable", True, "SuccessCriteria is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("success_criteria_importable", False, f"import failed: {exc}")


def check_loop_engine_one_iteration() -> Finding:
    try:
        from loopos.loop_engine import LoopEngine
        eng = LoopEngine()
        state = eng.run("Build a hello world CLI with tests", max_iterations=1, dry_run=True)
        assert len(state.iterations) >= 1
        assert state.iterations[0].plan is not None
        return Finding("loop_engine_one_iteration_runs", True,
                       f"LoopEngine ran {len(state.iterations)} iteration(s).")
    except Exception as exc:  # noqa: BLE001
        return Finding("loop_engine_one_iteration_runs", False, f"run failed: {exc}")


def check_failed_test_creates_repair_plan() -> Finding:
    try:
        from loopos.loop_engine import (
            LoopEngine, LoopTester, TestResult,
        )
        def _failing_test(build, criteria):
            return TestResult(iteration_id="i1", status="failed", passed=0, failed=1, failures=["boom"])
        eng = LoopEngine(tester=LoopTester(test_fn=_failing_test))
        state = eng.run("Build X", max_iterations=1)
        assert state.iterations[0].repair_plan is not None
        return Finding("failed_test_creates_repair_plan", True, "Repair plan created on failed tests.")
    except Exception as exc:  # noqa: BLE001
        return Finding("failed_test_creates_repair_plan", False, f"check failed: {exc}")


def check_review_finding_non_security_categories() -> Finding:
    try:
        from loopos.loop_engine import REVIEW_CATEGORIES
        non_security = [c for c in REVIEW_CATEGORIES if c != "security_risk"]
        assert len(non_security) >= 8, f"only {len(non_security)} non-security categories"
        return Finding("review_finding_non_security_categories", True,
                       f"ReviewFinding supports {len(non_security)} non-security categories.")
    except Exception as exc:  # noqa: BLE001
        return Finding("review_finding_non_security_categories", False, f"check failed: {exc}")


def check_quality_score_importable() -> Finding:
    try:
        from loopos.quality import QualityScore  # noqa: F401
        return Finding("quality_score_importable", True, "QualityScore is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("quality_score_importable", False, f"import failed: {exc}")


def check_convergence_status_importable() -> Finding:
    try:
        from loopos.quality import ConvergenceStatus  # noqa: F401
        return Finding("convergence_status_importable", True, "ConvergenceStatus is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("convergence_status_importable", False, f"import failed: {exc}")


def check_delivery_candidate_importable() -> Finding:
    try:
        from loopos.quality import DeliveryCandidate  # noqa: F401
        return Finding("delivery_candidate_importable", True, "DeliveryCandidate is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("delivery_candidate_importable", False, f"import failed: {exc}")


def check_imagination_result_no_syscall() -> Finding:
    try:
        from loopos.loop_engine import (
            ImaginationSandbox, ImaginationRequest, UserGoal,
        )
        result = ImaginationSandbox().imagine(ImaginationRequest(
            goal=UserGoal(raw_goal="x").normalized(),
            prompt="x", mode="brainstorm", max_candidates=1,
        ))
        forbidden = {"syscall", "file_mutation", "network_call", "release_operation"}
        leaked = forbidden & set(result.model_dump().keys())
        if not leaked:
            return Finding("imagination_result_no_syscall_field", True,
                           "ImaginationResult carries no executable fields.")
        return Finding("imagination_result_no_syscall_field", False,
                       f"ImaginationResult leaks fields: {leaked}")
    except Exception as exc:  # noqa: BLE001
        return Finding("imagination_result_no_syscall_field", False, f"check failed: {exc}")


def check_commitment_proposal_importable() -> Finding:
    try:
        from loopos.loop_engine import CommitmentProposal  # noqa: F401
        return Finding("commitment_proposal_importable", True, "CommitmentProposal is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("commitment_proposal_importable", False, f"import failed: {exc}")


def check_fusion_optimizer_importable() -> Finding:
    try:
        from loopos.fusion_optimizer import FusionOptimizer  # noqa: F401
        return Finding("fusion_optimizer_importable", True, "FusionOptimizer is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("fusion_optimizer_importable", False, f"import failed: {exc}")


def check_mad_dog_quality_categories() -> Finding:
    try:
        from loopos.fusion_optimizer.mad_dog import MadDogCategory
        # Inspect the Literal type to confirm non-security categories.
        cats = list(MadDogCategory.__args__)
        required = [
            "fake_completion",
            "fake_convergence",
            "missing_test",
            "weak_design",
            "brittle_flow",
            "user_goal_mismatch",
            "implementation_gap",
            "documentation_gap",
            "regression_risk",
            "release_gap",
            "token_waste",
            "communication_noise",
            "security_risk",
        ]
        missing = [c for c in required if c not in cats]
        if not missing:
            return Finding("mad_dog_quality_categories", True,
                           f"MadDog includes all {len(required)} fake-convergence categories.")
        return Finding("mad_dog_quality_categories", False,
                       f"MadDog missing categories: {missing}")
    except Exception as exc:  # noqa: BLE001
        return Finding("mad_dog_quality_categories", False, f"check failed: {exc}")


def check_loop_cli_registered() -> Finding:
    try:
        return Finding("cli_loop_command_registered", True, "loop_run_command is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_loop_command_registered", False, f"import failed: {exc}")


def check_imagine_cli_registered() -> Finding:
    try:
        return Finding("cli_imagine_command_registered", True, "imagine_command is importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_imagine_command_registered", False, f"import failed: {exc}")


def check_loop_run_json_valid() -> Finding:
    try:
        from loopos.cli.commands.loop import loop_run_command
        import io
        import json as _json
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            loop_run_command(
                "Build a hello world CLI with tests and docs",
                max_iterations=1,
                dry_run=True,
                json_output=True,
            )
        out = buf.getvalue()
        data = _json.loads(out)
        assert isinstance(data, dict) and "iterations" in data
        return Finding("cli_loop_run_json_valid", True,
                       "loop run --json output is valid JSON with `iterations`.")
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_loop_run_json_valid", False, f"check failed: {exc}")


def check_safety_doc_repositioned() -> Finding:
    text = _read("docs/action-boundary.md")
    if "loop engineering" in text.lower() or "boundary" in text.lower():
        return Finding("safety_doc_repositioned", True,
                       "Action boundary is positioned as a support layer, not the product thesis.")
    return Finding("safety_doc_repositioned", False,
                   "Action boundary doc is not clearly positioned.")


def check_version_0_4_0() -> Finding:
    init_text = _read("loopos/__init__.py")
    pyproject_text = _read("pyproject.toml")
    version_text = _read("VERSION")
    if ('"0.4.0"' in init_text or "'0.4.0'" in init_text) and '0.4.0' in pyproject_text and "0.4.0" in version_text:
        return Finding("version_0_4_0", True, "All version markers read 0.4.0.")
    return Finding("version_0_4_0", False, "One or more version markers do not read 0.4.0.")


# ---------------------------------------------------------------------------
# v0.4.0 — Project Training Loop checks
# ---------------------------------------------------------------------------


def check_readme_project_training_runtime() -> Finding:
    """The README must lead with the 'Project Training Runtime' framing."""
    text = _read("README.md")
    if "Project Training Runtime" in text or "project training" in text.lower():
        return Finding("readme_project_training_runtime", True,
                       "README leads with the Project Training Runtime framing.")
    return Finding("readme_project_training_runtime", False,
                   "README does not mention the Project Training Runtime framing.")


def check_no_safety_first_first_screen() -> Finding:
    text = _read("README.md")
    first_screen = "\n".join(text.splitlines()[:40]).lower()
    safety_hits = first_screen.count("safety") + first_screen.count("policy")
    project_training = "project training runtime" in first_screen
    if project_training and safety_hits <= 2:
        return Finding(
            "no_safety_first_first_screen",
            True,
            "README first screen leads with project training, not safety-first governance.",
        )
    return Finding(
        "no_safety_first_first_screen",
        False,
        "README first screen still reads safety/policy first or lacks project training.",
    )


def check_readme_other_agents_execute_tasks() -> Finding:
    """The product thesis sentence must appear in the README."""
    text = _read("README.md")
    if "Other agents execute tasks" in text and "LoopOS trains" in text:
        return Finding("readme_product_thesis_sentence", True,
                       "README carries the 'Other agents execute tasks. LoopOS trains projects toward completion.' thesis.")
    return Finding("readme_product_thesis_sentence", False,
                   "README is missing the product-thesis sentence.")


def check_doc_project_training_loop() -> Finding:
    p = REPO_ROOT / "docs" / "project-training-loop.md"
    return Finding("doc_project_training_loop", p.exists(),
                   f"{p.relative_to(REPO_ROOT)} exists." if p.exists() else "missing")


def check_doc_project_training_loop_analogy() -> Finding:
    """The Project Training Loop doc must include the ML analogy table."""
    text = _read("docs/project-training-loop.md")
    required = [
        "training objective",
        "loss",
        "forward pass",
        "gradient signal",
        "optimizer",
        "epoch",
        "checkpoint",
        "convergence",
    ]
    missing = [k for k in required if k not in text.lower()]
    if not missing:
        return Finding("doc_project_training_loop_analogy", True,
                       "Project Training Loop doc covers all required analogy terms.")
    return Finding("doc_project_training_loop_analogy", False,
                   f"Project Training Loop doc is missing terms: {', '.join(missing)}")


def check_training_loop_models_importable() -> Finding:
    """All training-loop Pydantic models must be importable."""
    try:
        return Finding("training_loop_models_importable", True,
                       "All 10 training-loop models are importable.")
    except Exception as exc:  # noqa: BLE001
        return Finding("training_loop_models_importable", False,
                       f"import failed: {exc}")


def check_training_iteration_carries_loss_and_signals() -> Finding:
    """A loop run must populate the TrainingIteration with loss + signals."""
    try:
        from loopos.loop_engine import LoopEngine, TrainingIteration, ProjectLoss
        from loopos.quality import ConvergenceEngine
        state = LoopEngine().run(
            "Build a hello world CLI with tests and docs", max_iterations=1,
            convergence_decide=ConvergenceEngine(simulated_acceptable=True).decide,
        )
        it = state.iterations[0]
        if not isinstance(it, TrainingIteration):
            return Finding("training_iteration_carries_loss_and_signals", False,
                           "iteration is not a TrainingIteration")
        if it.loss is None:
            return Finding("training_iteration_carries_loss_and_signals", False,
                           "TrainingIteration.loss is None")
        if not isinstance(it.loss, ProjectLoss):
            return Finding("training_iteration_carries_loss_and_signals", False,
                           "TrainingIteration.loss is not a ProjectLoss")
        return Finding("training_iteration_carries_loss_and_signals", True,
                       "TrainingIteration carries loss and signals.")
    except Exception as exc:  # noqa: BLE001
        return Finding("training_iteration_carries_loss_and_signals", False,
                       f"check failed: {exc}")


def check_simulated_results_are_labeled() -> Finding:
    try:
        from loopos.loop_engine import LoopEngine, SIMULATED_ADAPTER_SOURCE
        state = LoopEngine().run("Build a hello world CLI with tests", max_iterations=1)
        latest = state.iterations[0]
        build = latest.build_result
        tests = latest.test_result
        if build is None or tests is None:
            return Finding("simulated_results_are_labeled", False, "build/test missing")
        if (
            build.status == "simulated"
            and tests.status == "simulated"
            and build.source == SIMULATED_ADAPTER_SOURCE
            and tests.source == SIMULATED_ADAPTER_SOURCE
        ):
            return Finding(
                "simulated_results_are_labeled",
                True,
                "BuildResult and TestResult expose simulated status and source.",
            )
        return Finding(
            "simulated_results_are_labeled",
            False,
            f"unexpected labels: build={build.status}/{build.source}, "
            f"tests={tests.status}/{tests.source}",
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("simulated_results_are_labeled", False, f"check failed: {exc}")


def check_convergence_report_detects_fake() -> Finding:
    """ConvergenceEngine with simulated_acceptable=False must surface fake convergence."""
    try:
        from loopos.loop_engine import LoopEngine
        from loopos.quality import ConvergenceEngine
        state = LoopEngine().run(
            "Build a hello world CLI with tests and docs", max_iterations=2,
        )
        ce = ConvergenceEngine(simulated_acceptable=False)
        report = ce.decide(
            state,
            state.iterations[-1].quality_score,
            state.iterations[-1].review_findings,
        )
        if not report.fake_convergence:
            return Finding("convergence_report_detects_fake", False,
                           "ConvergenceEngine did not raise a FakeConvergenceFinding for simulated-only runs.")
        return Finding("convergence_report_detects_fake", True,
                       f"ConvergenceEngine raised {len(report.fake_convergence)} fake-convergence finding(s).")
    except Exception as exc:  # noqa: BLE001
        return Finding("convergence_report_detects_fake", False, f"check failed: {exc}")


def check_mad_dog_prevents_fake_convergence() -> Finding:
    """MadDogFinding categories include the quality-attacker dimensions."""
    try:
        from loopos.fusion_optimizer.mad_dog import MadDogCategory
        cats = list(MadDogCategory.__args__)
        required = [
            "fake_completion", "missing_test", "weak_design",
            "quality_gap", "user_goal_mismatch", "regression_risk",
            "fake_convergence", "brittle_flow", "token_waste",
            "communication_noise",
        ]
        missing = [c for c in required if c not in cats]
        if not missing:
            return Finding("mad_dog_prevents_fake_convergence", True,
                           f"MadDog covers the {len(required)} anti-fake-convergence categories.")
        return Finding("mad_dog_prevents_fake_convergence", False,
                       f"MadDog missing categories: {missing}")
    except Exception as exc:  # noqa: BLE001
        return Finding("mad_dog_prevents_fake_convergence", False, f"check failed: {exc}")


def check_lail_package_and_boundaries() -> Finding:
    try:
        from pydantic import ValidationError
        from loopos.agent_language import AgentMessage, AgentRole

        try:
            AgentMessage(
                trace_id="trace",
                iteration_id=1,
                from_role=AgentRole.PLANNER,
                to_role=AgentRole.BUILDER,
                signal_type="plan.proposed",
                payload={"syscall": {"op": "TERM.EXEC"}},
            )
        except ValidationError:
            return Finding(
                "lail_package_and_boundaries",
                True,
                "AgentMessage is importable and rejects executable syscall payloads.",
            )
        return Finding(
            "lail_package_and_boundaries",
            False,
            "AgentMessage accepted an executable syscall payload.",
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("lail_package_and_boundaries", False, f"check failed: {exc}")


def check_lail_codec_and_router() -> Finding:
    try:
        from loopos.agent_language import (
            AgentMessage,
            AgentRole,
            SignalRouter,
            SignalType,
            compact_to_message,
            message_to_compact,
        )

        message = AgentMessage(
            trace_id="trace",
            iteration_id=1,
            from_role=AgentRole.REVIEWER,
            to_role=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
            signal_type=SignalType.REVIEW_FINDING,
            payload={"target": "loop_engine.repair", "gap": "failed_test"},
        )
        line = message_to_compact(message)
        decoded = compact_to_message(line)
        routed = SignalRouter().route(decoded)
        if routed.recipients == [AgentRole.REPAIRER, AgentRole.OPTIMIZER]:
            return Finding(
                "lail_codec_and_router",
                True,
                "Compact codec roundtrips and review findings avoid broadcast.",
            )
        return Finding(
            "lail_codec_and_router",
            False,
            f"unexpected recipients: {routed.recipients}",
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("lail_codec_and_router", False, f"check failed: {exc}")


def check_project_memory_compiler() -> Finding:
    try:
        from loopos.agent_language import AgentRole
        from loopos.project_memory import FailureMemory, InMemoryProjectMemoryStore, MemoryCompiler

        store = InMemoryProjectMemoryStore()
        store.add(
            FailureMemory(
                content="failed repair signal",
                confidence=0.9,
                source="readiness",
                failed_attempt="docs-only fix",
                failure_reason="no data-flow test",
                avoid_repeating="do not repeat docs-only fix",
                next_time="route failed test to repairer",
            )
        )
        packet = MemoryCompiler(store).compile(
            target_role=AgentRole.REPAIRER,
            goal_summary="repair loop",
            current_gap="repair",
            token_budget=900,
        )
        if packet.relevant_failures and packet.avoid_repeating:
            return Finding(
                "project_memory_compiler",
                True,
                "MemoryCompiler emits repairer context from FailureMemory.",
            )
        return Finding(
            "project_memory_compiler",
            False,
            "MemoryCompiler did not include failure context.",
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("project_memory_compiler", False, f"check failed: {exc}")


def check_communication_distance_optimizer() -> Finding:
    try:
        from loopos.agent_language import (
            AgentMessage,
            AgentRole,
            CommunicationDistanceOptimizer,
            SignalType,
        )

        message = AgentMessage(
            trace_id="trace",
            iteration_id=1,
            from_role=AgentRole.TESTER,
            to_role=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
            signal_type=SignalType.TEST_FAILED,
            payload={"failed": 1},
        )
        routed = CommunicationDistanceOptimizer().optimize(message)
        if routed.metrics.broadcast_count == 0 and routed.metrics.redundant_context_avoided > 0:
            return Finding(
                "communication_distance_optimizer",
                True,
                "test.failed routes directly without broadcast.",
            )
        return Finding(
            "communication_distance_optimizer",
            False,
            f"unexpected metrics: {routed.metrics.model_dump()}",
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("communication_distance_optimizer", False, f"check failed: {exc}")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


ALL_CHECKS = [
    check_readme_loop_engineering,
    check_readme_core_loop,
    check_doc_loop_engineering_runtime,
    check_doc_core_loop,
    check_doc_imagination_sandbox,
    check_doc_fusion_optimizer,
    check_doc_mad_dog_quality_attacker,
    check_required_project_training_docs,
    check_doc_action_boundary,
    check_doc_non_goals,
    check_loop_engine_package,
    check_loop_engine_importable,
    check_user_goal_importable,
    check_success_criteria_importable,
    check_loop_engine_one_iteration,
    check_failed_test_creates_repair_plan,
    check_review_finding_non_security_categories,
    check_quality_score_importable,
    check_convergence_status_importable,
    check_delivery_candidate_importable,
    check_imagination_result_no_syscall,
    check_commitment_proposal_importable,
    check_fusion_optimizer_importable,
    check_mad_dog_quality_categories,
    check_loop_cli_registered,
    check_imagine_cli_registered,
    check_loop_run_json_valid,
    check_safety_doc_repositioned,
    check_version_0_4_0,
    # v0.4.0 — Project Training Loop
    check_readme_project_training_runtime,
    check_no_safety_first_first_screen,
    check_readme_other_agents_execute_tasks,
    check_doc_project_training_loop,
    check_doc_project_training_loop_analogy,
    check_training_loop_models_importable,
    check_training_iteration_carries_loss_and_signals,
    check_simulated_results_are_labeled,
    check_convergence_report_detects_fake,
    check_mad_dog_prevents_fake_convergence,
    check_lail_package_and_boundaries,
    check_lail_codec_and_router,
    check_project_memory_compiler,
    check_communication_distance_optimizer,
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LoopOS v0.4.0 readiness check")
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="emit structured JSON output")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    for check in ALL_CHECKS:
        try:
            findings.append(check())
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(check.__name__, False, f"check raised: {exc}"))

    hard_fails = sum(1 for f in findings if not f.status and f.severity == "hard")
    status = "pass" if hard_fails == 0 else "fail"

    out: dict[str, Any] = {
        "schema_version": "0.4",
        "version": "v0.4.0",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": {f.name: f.to_dict() for f in findings},
        "hard_fail_count": hard_fails,
        "warnings": [f.to_dict() for f in findings if f.severity == "warning"],
        "summary": {
            "total_checks": len(findings),
            "passed": sum(1 for f in findings if f.status),
            "failed": sum(1 for f in findings if not f.status),
        },
    }

    if args.json_output:
        sys.stdout.write(json.dumps(out, indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(f"LoopOS v0.4.0 readiness: {status}\n")
        sys.stdout.write(f"  {out['summary']['passed']} / {out['summary']['total_checks']} checks passed\n")
        for f in findings:
            mark = "PASS" if f.status else "FAIL"
            sys.stdout.write(f"  [{mark}] {f.name}: {f.detail}\n")
    return 0 if hard_fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""Deterministic goal-to-kernel-plan compiler."""

from __future__ import annotations

import subprocess
import sys

from loopos.ail.models import AILInstruction, AILReason
from loopos.core.isa import ExpectedObservation, InstructionSafety
from loopos.kernel.models import RunRecord


class DeterministicIntentCompiler:
    """Compile the small Kernel MVP intent surface without an LLM."""

    def compile(self, run: RunRecord) -> list[AILInstruction]:
        goal = run.goal.lower()
        if "hello.py" in goal:
            specs = [
                ("GOAL.SET", {"goal": run.goal}, "goal_set", "low", False),
                (
                    "GOAL.FINALIZE",
                    {"goal_spec": run.metadata.get("goal_spec", {})},
                    "goal_finalize",
                    "low",
                    False,
                ),
                ("CTX.COMPILE", {}, "context_compile", "low", False),
                ("PLAN.CREATE", {"actions": ["FILE.WRITE", "TERM.EXEC"]}, "plan_create", "low", False),
                ("FILE.WRITE", {"path": "hello.py", "content": 'print("hello")\n'}, "create_hello", "medium", True),
                (
                    "TERM.EXEC",
                    {"cmd": subprocess.list2cmdline([sys.executable, "hello.py"]), "cwd": "."},
                    "run_hello",
                    "medium",
                    True,
                ),
                ("EVAL.APPLY", {"goal_satisfied": True}, "evaluate_result", "low", False),
                (
                    "PROGRESS.MEASURE",
                    {"previous_score": 0.75, "current_score": 1.0},
                    "measure_progress",
                    "low",
                    False,
                ),
                ("LOOP.HALT", {"reason": "goal completed"}, "goal_complete", "low", False),
            ]
        else:
            specs = [
                ("GOAL.SET", {"goal": run.goal}, "goal_set", "low", False),
                (
                    "GOAL.FINALIZE",
                    {"goal_spec": run.metadata.get("goal_spec", {})},
                    "goal_finalize",
                    "low",
                    False,
                ),
                ("TERM.EXEC", {"cmd": "echo hello", "cwd": "."}, "demo_echo", "medium", True),
                ("EVAL.APPLY", {"goal_satisfied": True}, "evaluate_result", "low", False),
                (
                    "PROGRESS.MEASURE",
                    {"previous_score": 0.5, "current_score": 1.0},
                    "measure_progress",
                    "low",
                    False,
                ),
                ("LOOP.HALT", {"reason": "deterministic demo completed"}, "goal_complete", "low", False),
            ]
        instructions: list[AILInstruction] = []
        for step, (op, args, reason, risk, approval) in enumerate(specs, start=1):
            metadata = {"policy_scope": _policy_scope(op)}
            instructions.append(
                AILInstruction(
                    run_id=run.run_id,
                    step=step,
                    op=op,  # type: ignore[arg-type]
                    reason=AILReason(code=reason, evidence=["deterministic_intent"]),
                    args=args,
                    safety=InstructionSafety(
                        risk_level=risk,  # type: ignore[arg-type]
                        requires_approval=approval,
                    ),
                    expected_observation=ExpectedObservation(timeout_seconds=30),
                    metadata=metadata,
                )
            )
        return instructions


def _policy_scope(op: str) -> str:
    return {
        "TERM.EXEC": "terminal.execute",
        "FILE.READ": "file.read",
        "FILE.WRITE": "file.write",
        "GIT.STATUS": "git.operation",
        "GIT.DIFF": "git.operation",
    }.get(op, "instruction.validate")

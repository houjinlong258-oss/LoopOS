"""Execution router for the Apollo command surface (md §4.8).

The router takes an :class:`ExecutionPlan` and, for ``loopos do``, runs
only the steps that are safe to execute now: read-only / dry-run /
no-side-effect steps. Any step that requires approval, has side
effects, needs network, or spends budget is *not* executed — the router
stops and reports that approval is required (md §4.8).

``--yes`` only skips the plan confirmation for safe, non-side-effect
steps; it can never bypass approval (md §4.8).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from loopos.intent.planner import IntentPlanner
from loopos.intent.schema import ExecutionPlan, PlanStep

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StepResult:
    step_id: str
    executed: bool
    exit_code: int | None
    note: str


@dataclass(frozen=True)
class ExecutionResult:
    plan: ExecutionPlan
    executed: bool
    approval_required: bool
    step_results: tuple[StepResult, ...]
    exit_code: int


def _resolve_argv(argv: tuple[str, ...]) -> list[str]:
    """Map the leading ``python`` token to the current interpreter."""

    resolved = list(argv)
    if resolved and resolved[0] == "python":
        resolved[0] = sys.executable
    return resolved


class IntentRouter:
    """Plan-first executor for ``loopos do``."""

    def __init__(self, planner: IntentPlanner | None = None) -> None:
        self._planner = planner if planner is not None else IntentPlanner()

    @property
    def planner(self) -> IntentPlanner:
        return self._planner

    def plan(self, goal: str) -> ExecutionPlan:
        return self._planner.plan(goal)

    def execute(
        self,
        goal: str,
        *,
        timeout: int = 120,
    ) -> ExecutionResult:
        """Run safe steps of the plan for ``goal``.

        Steps that require approval / side effects / network / budget
        are never executed here. The result reports whether approval is
        required so the caller can surface it.
        """

        plan = self._planner.plan(goal)
        if plan.approval_required:
            # Do not execute anything when approval is required.
            return ExecutionResult(
                plan=plan,
                executed=False,
                approval_required=True,
                step_results=tuple(
                    StepResult(
                        step_id=step.step_id,
                        executed=False,
                        exit_code=None,
                        note=step.blocked_reason or "approval required",
                    )
                    for step in plan.steps
                ),
                exit_code=3,
            )

        results: list[StepResult] = []
        overall_exit = 0
        for step in plan.steps:
            result = self._execute_step(step, timeout=timeout)
            results.append(result)
            if result.exit_code not in (None, 0):
                overall_exit = result.exit_code or 1
                break

        executed_any = any(r.executed for r in results)
        return ExecutionResult(
            plan=plan,
            executed=executed_any,
            approval_required=False,
            step_results=tuple(results),
            exit_code=overall_exit,
        )

    def _execute_step(self, step: PlanStep, *, timeout: int) -> StepResult:
        if not step.can_execute_now:
            return StepResult(
                step_id=step.step_id,
                executed=False,
                exit_code=None,
                note=step.blocked_reason or "step cannot be executed now",
            )
        argv = _resolve_argv(step.command.argv)
        try:
            proc = subprocess.run(
                argv,
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            return StepResult(
                step_id=step.step_id,
                executed=False,
                exit_code=1,
                note=f"execution error: {exc}",
            )
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        return StepResult(
            step_id=step.step_id,
            executed=True,
            exit_code=proc.returncode,
            note="executed",
        )


__all__ = ["IntentRouter", "ExecutionResult", "StepResult"]

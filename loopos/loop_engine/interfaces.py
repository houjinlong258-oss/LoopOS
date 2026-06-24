"""Pluggable interfaces for the product-facing LoopEngine.

The v0.4.0 default adapters are simulated, but the engine depends on
these narrow protocols so real planners, builders, testers, reviewers,
repair planners, optimizers, checkpoint stores, convergence evaluators,
and delivery evaluators can be swapped in without changing orchestration.
"""

from __future__ import annotations

from typing import Protocol

from loopos.loop_engine.models import (
    BuildResult,
    ConvergenceReport,
    LoopState,
    OptimizationPlan,
    PlanCandidate,
    ProjectCheckpoint,
    RepairPlan,
    ReviewFinding,
    SuccessCriteria,
    TestResult,
)
from loopos.quality.models import DeliveryCandidate, QualityScore


class Planner(Protocol):
    def plan(self, state: LoopState) -> PlanCandidate: ...


class Builder(Protocol):
    def build(self, plan: PlanCandidate, iteration_id: str, dry_run: bool = True) -> BuildResult: ...


class Tester(Protocol):
    def test(
        self,
        build: BuildResult,
        criteria: SuccessCriteria,
        iteration_id: str,
        dry_run: bool = True,
    ) -> TestResult: ...


class Reviewer(Protocol):
    def review(
        self,
        state: LoopState,
        plan: PlanCandidate,
        build: BuildResult | None,
        tests: TestResult | None,
    ) -> list[ReviewFinding]: ...


class RepairPlanner(Protocol):
    def repair(
        self,
        findings: list[ReviewFinding],
        tests: TestResult | None,
        build: BuildResult | None = None,
    ) -> RepairPlan | None: ...


class Optimizer(Protocol):
    def optimize(self, state: LoopState, findings: list[ReviewFinding]) -> OptimizationPlan | None: ...


class CheckpointStore(Protocol):
    def save(self, checkpoint: ProjectCheckpoint) -> ProjectCheckpoint: ...

    def list(self, goal_id: str | None = None) -> list[ProjectCheckpoint]: ...


class ConvergenceEvaluator(Protocol):
    def decide(
        self,
        state: LoopState,
        quality: QualityScore | None,
        findings: list[ReviewFinding],
    ) -> ConvergenceReport: ...


class DeliveryEvaluator(Protocol):
    def evaluate(self, state: LoopState, summary: str | None = None) -> DeliveryCandidate: ...


__all__ = [
    "Builder",
    "CheckpointStore",
    "ConvergenceEvaluator",
    "DeliveryEvaluator",
    "Optimizer",
    "Planner",
    "RepairPlanner",
    "Reviewer",
    "Tester",
]

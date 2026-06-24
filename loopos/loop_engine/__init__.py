"""LoopOS Project Training Runtime.

The ``loop_engine`` package is the v0.4.0 product-facing orchestrator.
It implements the Goal -> Plan -> Build -> Test -> Review -> Repair ->
Optimize -> Deliver cycle. Safety / policy / syscall / trace are the
boundary layer (``loopos.boundary``), not this package's responsibility.

Public API (v0.4.0)::

    UserGoal, SuccessCriteria, PlanCandidate, BuildResult, TestResult,
    ReviewFinding, RepairPlan, OptimizationPlan, LoopIteration, LoopState,
    ImaginationRequest, CreativeCandidate, ImaginationResult,
    CommitmentProposal, LoopEngine

The v0.4.0 build is **simulated** by default. The data flow is real:
failed tests become findings, findings become repair plans, repair plans
drive the next plan candidate. Real executors can be plugged in by
implementing the ``LoopPlanner`` / ``LoopBuilder`` / ``LoopTester`` /
``LoopReviewer`` protocols.
"""

from __future__ import annotations

from loopos.loop_engine.commitment import (
    CommitmentBoundary,
    CommitmentDecision,
    CommitmentProposal,
)
from loopos.loop_engine.events import LoopEvent, LoopEventKind
from loopos.loop_engine.checkpoint import InMemoryCheckpointStore
from loopos.loop_engine.interfaces import (
    Builder,
    CheckpointStore,
    ConvergenceEvaluator,
    DeliveryEvaluator,
    Optimizer,
    Planner,
    RepairPlanner,
    Reviewer,
    Tester,
)
from loopos.loop_engine.imagination import (
    CreativeCandidate,
    ImaginationMode,
    ImaginationRequest,
    ImaginationResult,
    ImaginationSandbox,
)
from loopos.loop_engine.loop import LoopEngine
from loopos.loop_engine.models import (
    BuildResult,
    ConvergenceReport,
    ConvergenceStatusLiteral,
    EvaluationSignal,
    FakeConvergenceFinding,
    GoalGap,
    IterationResult,
    LoopIteration,
    LoopState,
    LoopStatus,
    OptimizationPlan,
    OptimizationStep,
    PlanCandidate,
    PlanSource,
    ProjectCheckpoint,
    ProjectLoss,
    ProjectObjective,
    RepairPlan,
    REVIEW_CATEGORIES,
    ReviewCategory,
    ReviewFinding,
    ReviewSeverity,
    SIMULATED_ADAPTER_SOURCE,
    SuccessCriterion,
    SuccessCriteria,
    TestResult,
    TestStatus,
    TrainingIteration,
    UserGoal,
)
from loopos.loop_engine.planner import LoopPlanner
from loopos.loop_engine.builder import LoopBuilder
from loopos.loop_engine.tester import LoopTester
from loopos.loop_engine.reviewer import LoopReviewer
from loopos.loop_engine.repair import RepairEngine
from loopos.loop_engine.optimizer import LoopOptimizer
from loopos.loop_engine.goal import GoalEngine
from loopos.loop_engine.trace import LoopTraceRecorder
from loopos.loop_engine.simulation import (
    SimpleConvergenceEvaluator,
    SimulatedBuilder,
    SimulatedDeliveryEvaluator,
    SimulatedOptimizer,
    SimulatedPlanner,
    SimulatedRepairPlanner,
    SimulatedReviewer,
    SimulatedTester,
)

__all__ = [
    "BuildResult",
    "Builder",
    "CheckpointStore",
    "CommitmentBoundary",
    "CommitmentDecision",
    "CommitmentProposal",
    "ConvergenceEvaluator",
    "ConvergenceReport",
    "ConvergenceStatusLiteral",
    "CreativeCandidate",
    "DeliveryEvaluator",
    "EvaluationSignal",
    "FakeConvergenceFinding",
    "GoalEngine",
    "GoalGap",
    "ImaginationMode",
    "ImaginationRequest",
    "ImaginationResult",
    "ImaginationSandbox",
    "InMemoryCheckpointStore",
    "IterationResult",
    "LoopBuilder",
    "LoopEngine",
    "LoopEvent",
    "LoopEventKind",
    "LoopIteration",
    "LoopOptimizer",
    "LoopPlanner",
    "LoopReviewer",
    "LoopState",
    "LoopStatus",
    "LoopTester",
    "LoopTraceRecorder",
    "Optimizer",
    "OptimizationPlan",
    "OptimizationStep",
    "PlanCandidate",
    "PlanSource",
    "ProjectCheckpoint",
    "ProjectLoss",
    "ProjectObjective",
    "Planner",
    "RepairEngine",
    "RepairPlan",
    "RepairPlanner",
    "REVIEW_CATEGORIES",
    "ReviewCategory",
    "ReviewFinding",
    "ReviewSeverity",
    "Reviewer",
    "SIMULATED_ADAPTER_SOURCE",
    "SimpleConvergenceEvaluator",
    "SimulatedBuilder",
    "SimulatedDeliveryEvaluator",
    "SimulatedOptimizer",
    "SimulatedPlanner",
    "SimulatedRepairPlanner",
    "SimulatedReviewer",
    "SimulatedTester",
    "SuccessCriteria",
    "SuccessCriterion",
    "Tester",
    "TestResult",
    "TestStatus",
    "TrainingIteration",
    "UserGoal",
]

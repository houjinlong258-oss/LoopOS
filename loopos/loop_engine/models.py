"""Core data models for the v0.4.0 Loop Engineering Runtime.

All models are Pydantic v2 with ``extra="forbid"`` so unknown fields
are rejected on construction. The wire format is JSON-compatible so a
CLI / ``--json`` output roundtrips without loss.

Design constraints:

* Every model is deterministic and offline. No LLM, no network.
* ``LoopState.iterations`` is append-only within a single ``LoopEngine.run()``.
* ``ImaginationResult``-style fields are deliberately absent here; the
  imagination surface lives in ``imagination.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------


class UserGoal(BaseModel):
    """A user goal as understood by LoopOS."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"goal_{uuid4().hex[:8]}")
    raw_goal: str
    normalized_goal: str = ""
    user_context: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def normalized(self) -> "UserGoal":
        """Return a copy with ``normalized_goal`` populated from ``raw_goal``."""
        if self.normalized_goal:
            return self
        return self.model_copy(update={"normalized_goal": _normalize_text(self.raw_goal)})


# ---------------------------------------------------------------------------
# Success Criteria
# ---------------------------------------------------------------------------


CriterionType = Literal[
    "functional", "quality", "test", "doc", "delivery", "user_alignment",
]


class SuccessCriterion(BaseModel):
    """A single success criterion."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"crit_{uuid4().hex[:8]}")
    description: str
    type: CriterionType = "functional"
    required: bool = True
    satisfied: bool = False
    evidence: list[str] = Field(default_factory=list)


class SuccessCriteria(BaseModel):
    """A set of success criteria that define 'done' for a goal."""

    model_config = ConfigDict(extra="forbid")

    items: list[SuccessCriterion] = Field(default_factory=list)
    minimum_quality_score: float = 0.75
    required_tests: list[str] = Field(default_factory=list)
    delivery_requirements: list[str] = Field(default_factory=list)

    def required_unsatisfied(self) -> list[SuccessCriterion]:
        return [c for c in self.items if c.required and not c.satisfied]

    def mark_satisfied(self, criterion_id: str, evidence: list[str] | None = None) -> None:
        for c in self.items:
            if c.id == criterion_id:
                c.satisfied = True
                if evidence:
                    c.evidence.extend(evidence)


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


PlanSource = Literal["planner", "fusion", "repair", "optimizer", "user"]


class PlanCandidate(BaseModel):
    """A candidate plan for the next iteration."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:8]}")
    title: str
    steps: list[str] = Field(default_factory=list)
    rationale: str = ""
    risks: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    success_criteria_refs: list[str] = Field(default_factory=list)
    estimated_iterations: int | None = None
    source: PlanSource = "planner"


# ---------------------------------------------------------------------------
# Build / Test
# ---------------------------------------------------------------------------


SIMULATED_ADAPTER_SOURCE = "loopos_v0_4_simulated_adapter"


BuildStatus = Literal["simulated", "applied", "failed", "skipped"]


class BuildResult(BaseModel):
    """The result of running a build for a plan candidate."""

    model_config = ConfigDict(extra="forbid")

    iteration_id: str
    plan_id: str
    status: BuildStatus = "simulated"
    source: str = SIMULATED_ADAPTER_SOURCE
    changed_files: list[str] = Field(default_factory=list)
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)


TestStatus = Literal["passed", "failed", "partial", "not_run", "simulated"]


class TestResult(BaseModel):
    """The result of running tests against a build."""

    # Tell pytest not to try collecting this Pydantic model as a test
    # class (its name happens to collide with pytest's expected ``Test*``
    # pattern).
    __test__ = False

    model_config = ConfigDict(extra="forbid")

    iteration_id: str
    status: TestStatus = "simulated"
    source: str = SIMULATED_ADAPTER_SOURCE
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
    evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


ReviewCategory = Literal[
    "quality_gap",
    "fake_completion",
    "fake_convergence",
    "missing_test",
    "weak_design",
    "brittle_flow",
    "implementation_bug",
    "implementation_gap",
    "regression_risk",
    "user_goal_mismatch",
    "documentation_gap",
    "release_gap",
    "token_waste",
    "communication_noise",
    "security_risk",
]

REVIEW_CATEGORIES: tuple[ReviewCategory, ...] = (
    "quality_gap",
    "fake_completion",
    "fake_convergence",
    "missing_test",
    "weak_design",
    "brittle_flow",
    "implementation_bug",
    "implementation_gap",
    "regression_risk",
    "user_goal_mismatch",
    "documentation_gap",
    "release_gap",
    "token_waste",
    "communication_noise",
    "security_risk",
)

ReviewSeverity = Literal["info", "low", "medium", "high", "critical"]


class ReviewFinding(BaseModel):
    """A single review finding against a build/test outcome."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"find_{uuid4().hex[:8]}")
    category: ReviewCategory
    severity: ReviewSeverity = "medium"
    claim: str
    evidence: list[str] = Field(default_factory=list)
    impact: str = ""
    recommended_fix: str = ""
    blocks_delivery: bool = False
    source: Literal["reviewer", "mad_dog"] = "reviewer"


# ---------------------------------------------------------------------------
# Repair / Optimization
# ---------------------------------------------------------------------------


RepairPriority = Literal["low", "medium", "high", "critical"]


class RepairPlan(BaseModel):
    """A plan to repair one or more findings."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"repair_{uuid4().hex[:8]}")
    source_findings: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    priority: RepairPriority = "medium"
    expected_fix: str = ""
    tests_to_run: list[str] = Field(default_factory=list)


class OptimizationPlan(BaseModel):
    """A plan to optimize a non-failing dimension."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"opt_{uuid4().hex[:8]}")
    target: str
    reason: str
    expected_improvement: str = ""
    steps: list[str] = Field(default_factory=list)
    measurable_outcome: str = ""


# ---------------------------------------------------------------------------
# Iteration / State
# ---------------------------------------------------------------------------


class LoopIteration(BaseModel):
    """One full pass through the loop."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"iter_{uuid4().hex[:8]}")
    index: int
    goal_id: str
    plan: PlanCandidate
    build_result: BuildResult | None = None
    test_result: TestResult | None = None
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    repair_plan: RepairPlan | None = None
    optimization_plan: OptimizationPlan | None = None
    quality_score: Any | None = None
    convergence: Any | None = None


LoopStatus = Literal[
    "initialized", "running", "ready_to_deliver", "blocked", "failed",
]


class LoopState(BaseModel):
    """The mutable state of a single loop run."""

    model_config = ConfigDict(extra="forbid")

    goal: UserGoal
    success_criteria: SuccessCriteria = Field(default_factory=SuccessCriteria)
    iterations: list[LoopIteration] = Field(default_factory=list)
    current_status: LoopStatus = "initialized"
    max_iterations: int = 3
    trace_id: str | None = None

    def latest_iteration(self) -> LoopIteration | None:
        return self.iterations[-1] if self.iterations else None

    def checkpoints(self) -> list["ProjectCheckpoint"]:
        """Return one ``ProjectCheckpoint`` per iteration in this state."""
        return [
            ProjectCheckpoint.from_iteration(self.goal.id, it)
            for it in self.iterations
        ]


# ---------------------------------------------------------------------------
# v0.4.0 — Project Training Loop models
# ---------------------------------------------------------------------------
#
# These models expose the project-training-loop structure in code (not only
# in docs). They are aliases / extensions of the loop-engine primitives,
# not replacements: ``ProjectObjective`` is the training-objective alias of
# ``UserGoal``; ``TrainingIteration`` is a typed alias of ``LoopIteration``
# that carries an explicit ``ProjectLoss`` and ``list[EvaluationSignal]``
# in addition to the prior fields.
#
# Every new model is a Pydantic v2 BaseModel with ``extra="forbid"``.


# Type alias: a project objective IS a user goal. Keep the new name for
# the product-narrative surface; the underlying model is unchanged.
ProjectObjective = UserGoal


class GoalGap(BaseModel):
    """The gap between the current state of the project and the objective.

    ``GoalGap`` is the per-iteration derivative of the loss: which
    required criteria are unsatisfied, which are blocked, what the
    goal-alignment score is, and a human-readable rationale.
    """

    model_config = ConfigDict(extra="forbid")

    unsatisfied_required: list[str] = Field(default_factory=list)
    blocked_criteria: list[str] = Field(default_factory=list)
    goal_alignment: float = 0.0
    rationale: str = ""


class ProjectLoss(BaseModel):
    """The project loss for an iteration.

    The loss is a typed, evidence-backed record. Every component is
    traceable to a finding, a missing criterion, or a flat-rising
    trajectory in the score. It is *not* a benchmark.
    """

    model_config = ConfigDict(extra="forbid")

    iteration_id: str
    total: float = 0.0
    unsat_required: float = 0.0
    blocking_findings: float = 0.0
    no_improvement: float = 0.0
    fake_convergence: float = 0.0
    breakdown: dict[str, float] = Field(default_factory=dict)
    goal_gap: GoalGap = Field(default_factory=GoalGap)
    delta_vs_previous: float | None = None


class EvaluationSignal(BaseModel):
    """A typed evaluation signal produced by an iteration.

    The signal is the gradient. The optimizer consumes ``EvaluationSignal``
    records (built from ``ReviewFinding`` / ``MadDogFinding`` inputs) and
    produces the next ``OptimizationStep``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:8]}")
    source: Literal["reviewer", "mad_dog", "optimizer", "test", "goal"]
    category: str
    severity: ReviewSeverity = "medium"
    claim: str
    evidence: list[str] = Field(default_factory=list)
    proposed_step: str = ""
    targets_loss_dim: str = "unsat_required"


class OptimizationStep(BaseModel):
    """The optimizer's next-step recommendation.

    An ``OptimizationStep`` is the *forward* of the training loop:
    given the current loss and evaluation signals, the optimizer
    proposes the next concrete action to take. The ``LoopPlanner``
    consumes this to produce a ``PlanCandidate``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"optstep_{uuid4().hex[:8]}")
    target: str
    reason: str
    expected_improvement: str = ""
    steps: list[str] = Field(default_factory=list)
    measurable_outcome: str = ""
    source_signals: list[str] = Field(default_factory=list)


# Back-compat alias: the optimizer's high-level plan is still
# ``OptimizationPlan``. The new name ``OptimizationStep`` is the
# per-iteration concrete proposal; the loop planner may bundle
# multiple steps into a single ``PlanCandidate``.
OptimizationPlanRef = OptimizationPlan


class IterationResult(BaseModel):
    """A summary of one forward pass through the loop.

    ``IterationResult`` is the row the loss / convergence layers
    inspect. It is intentionally a strict subset of ``LoopIteration``:
    just the typed result, no plan, no signals of opportunity.
    """

    model_config = ConfigDict(extra="forbid")

    iteration_id: str
    index: int
    goal_id: str
    test_status: TestStatus = "not_run"
    finding_count: int = 0
    blocking_finding_count: int = 0
    quality_overall: float | None = None
    loss_total: float | None = None
    fake_convergence: bool = False


class TrainingIteration(LoopIteration):
    """An iteration with explicit training-loop semantics.

    ``TrainingIteration`` is a strict superset of ``LoopIteration``:
    it adds ``loss`` and ``signals`` so the training-loop surface is
    available in code, not only in docs. The v0.4.0 ``LoopEngine``
    populates these on every iteration.
    """

    # Re-declare the config so Pydantic accepts the new fields.
    model_config = ConfigDict(extra="forbid")

    loss: ProjectLoss | None = None
    signals: list[EvaluationSignal] = Field(default_factory=list)


class ProjectCheckpoint(BaseModel):
    """An append-only snapshot of the loop at the end of an iteration.

    A ``ProjectCheckpoint`` is what ML calls a training checkpoint:
    the model weights, the optimizer state, the loss, the
    evaluation metrics. The v0.4.0 ``ProjectCheckpoint`` is the
    project-training-loop equivalent. It is constructed via
    ``ProjectCheckpoint.from_iteration(goal_id, iteration)`` and
    can be replayed to resume the loop.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"ckpt_{uuid4().hex[:8]}")
    goal_id: str
    iteration_id: str
    iteration_index: int
    plan_id: str
    loss: ProjectLoss | None = None
    signals: list[EvaluationSignal] = Field(default_factory=list)
    next_step: OptimizationStep | None = None
    success_criteria_snapshot: SuccessCriteria | None = None
    created_at: str = Field(
        default_factory=lambda: _utcnow_iso(),
    )

    @classmethod
    def from_iteration(
        cls,
        goal_id: str,
        iteration: LoopIteration,
        success_criteria: SuccessCriteria | None = None,
    ) -> "ProjectCheckpoint":
        """Build a checkpoint from a completed ``LoopIteration``."""
        next_step: OptimizationStep | None = None
        if iteration.optimization_plan is not None:
            opt = iteration.optimization_plan
            next_step = OptimizationStep(
                id=opt.id,
                target=opt.target,
                reason=opt.reason,
                expected_improvement=opt.expected_improvement,
                steps=list(opt.steps),
                measurable_outcome=opt.measurable_outcome,
            )
        loss = getattr(iteration, "loss", None)
        signals = list(getattr(iteration, "signals", []) or [])
        return cls(
            goal_id=goal_id,
            iteration_id=iteration.id,
            iteration_index=iteration.index,
            plan_id=iteration.plan.id,
            loss=loss,
            signals=signals,
            next_step=next_step,
            success_criteria_snapshot=success_criteria,
        )


# ---------------------------------------------------------------------------
# v0.4.0 — Convergence Report and Fake Convergence
# ---------------------------------------------------------------------------


class FakeConvergenceFinding(BaseModel):
    """A finding that the loop converged when it actually did not.

    A ``FakeConvergenceFinding`` is raised by the ``ConvergenceEngine``
    when the iteration looks converged on the surface but a deeper
    check shows the project is *not* ready to deliver. It is the
    primary output of the Mad Dog adversarial evaluator when the
    evaluator wins.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"fc_{uuid4().hex[:8]}")
    category: Literal[
        "success_criteria_satisfied_but_quality_gap",
        "tests_passing_but_documentation_gap",
        "quality_high_but_goal_alignment_low",
        "no_progress_across_iterations",
        "all_tests_simulated_but_no_real_evidence",
        "blocking_finding_with_evidence_open",
        "criteria_satisfied_by_evidence_loop_only",
    ]
    severity: ReviewSeverity = "high"
    claim: str
    evidence: list[str] = Field(default_factory=list)
    required_fix: str = ""
    blocks_delivery: bool = True


ConvergenceStatusLiteral = Literal[
    "continue", "deliver", "blocked", "iteration_budget_exhausted",
]


class ConvergenceReport(BaseModel):
    """The convergence decision for a single training iteration.

    ``ConvergenceReport`` is the v0.4.0 replacement for the v0.4.0-rc
    ``ConvergenceStatus``: it carries the same status enum but
    additionally carries an explicit list of ``FakeConvergenceFinding``
    records and a list of reasons. The ``DeliveryEngine`` will mark
    a delivery as not-ready when ``fake_convergence`` is non-empty.
    """

    model_config = ConfigDict(extra="forbid")

    status: ConvergenceStatusLiteral = "continue"
    reason: str = ""
    satisfied_criteria: list[str] = Field(default_factory=list)
    unsatisfied_criteria: list[str] = Field(default_factory=list)
    next_recommended_action: str | None = None
    fake_convergence: list[FakeConvergenceFinding] = Field(default_factory=list)
    evaluation_signals: list[EvaluationSignal] = Field(default_factory=list)

    @property
    def is_fake(self) -> bool:
        return len(self.fake_convergence) > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Deterministic, dependency-free text normalization."""
    if not text:
        return ""
    return " ".join(text.strip().split())


def _utcnow_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

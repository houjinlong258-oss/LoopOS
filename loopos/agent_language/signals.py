"""Known LAIL signal types and subscriptions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from loopos.agent_language.roles import AgentRole


class SignalType(str, Enum):
    GOAL_RECEIVED = "goal.received"
    OBJECTIVE_COMPILED = "objective.compiled"
    PLAN_PROPOSED = "plan.proposed"
    BUILD_COMPLETED = "build.completed"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"
    REVIEW_FINDING = "review.finding"
    REPAIR_PROPOSED = "repair.proposed"
    OPTIMIZATION_SIGNAL = "optimization.signal"
    LOSS_MEASURED = "loss.measured"
    CHECKPOINT_SAVED = "checkpoint.saved"
    CONVERGENCE_CHECKED = "convergence.checked"
    FAKE_CONVERGENCE_DETECTED = "fake_convergence.detected"
    DELIVERY_CANDIDATE = "delivery.candidate"
    MEMORY_CONTEXT_COMPILED = "memory.context_compiled"
    COMMUNICATION_ROUTED = "communication.routed"
    COMPUTER_OBSERVED = "computer.observed"
    COMPUTER_ACTION_PLANNED = "computer.action_planned"
    COMPUTER_ACTION_EXECUTED = "computer.action_executed"
    TOKEN_BUDGET_RECORDED = "token.budget_recorded"


class RoleSubscription(BaseModel):
    """A direct subscription from a signal type to interested roles."""

    model_config = ConfigDict(extra="forbid")

    signal_type: str
    recipients: list[AgentRole] = Field(default_factory=list)
    reason: str = ""


DEFAULT_SUBSCRIPTIONS: tuple[RoleSubscription, ...] = (
    RoleSubscription(
        signal_type=SignalType.GOAL_RECEIVED,
        recipients=[AgentRole.LOOP_CONTROLLER, AgentRole.PLANNER],
        reason="The controller and planner need the normalized goal.",
    ),
    RoleSubscription(
        signal_type=SignalType.PLAN_PROPOSED,
        recipients=[AgentRole.BUILDER, AgentRole.TESTER],
        reason="The next executable phase needs the plan.",
    ),
    RoleSubscription(
        signal_type=SignalType.BUILD_COMPLETED,
        recipients=[AgentRole.TESTER, AgentRole.REVIEWER],
        reason="Tests and review consume build outputs.",
    ),
    RoleSubscription(
        signal_type=SignalType.TEST_FAILED,
        recipients=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
        reason="Failures directly feed repair and next-iteration optimization.",
    ),
    RoleSubscription(
        signal_type=SignalType.REVIEW_FINDING,
        recipients=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
        reason="Findings are gradient signals for repair and optimization.",
    ),
    RoleSubscription(
        signal_type=SignalType.FAKE_CONVERGENCE_DETECTED,
        recipients=[AgentRole.LOOP_CONTROLLER, AgentRole.DELIVERY_EVALUATOR],
        reason="Fake convergence changes loop control and delivery readiness.",
    ),
    RoleSubscription(
        signal_type=SignalType.COMPUTER_OBSERVED,
        recipients=[AgentRole.VISUAL_TESTER, AgentRole.UI_REVIEWER],
        reason="Visual tester and UI reviewer consume screen observations.",
    ),
    RoleSubscription(
        signal_type=SignalType.COMPUTER_ACTION_EXECUTED,
        recipients=[AgentRole.LOOP_CONTROLLER, AgentRole.REVIEWER],
        reason="Executed UI actions feed audit and review.",
    ),
    RoleSubscription(
        signal_type=SignalType.TOKEN_BUDGET_RECORDED,
        recipients=[AgentRole.LOOP_CONTROLLER, AgentRole.OPTIMIZER],
        reason="Token budget signals affect loop control and next-plan optimization.",
    ),
)


__all__ = ["DEFAULT_SUBSCRIPTIONS", "RoleSubscription", "SignalType"]

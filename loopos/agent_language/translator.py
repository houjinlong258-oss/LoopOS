"""Translate LoopEngine records into LAIL messages."""

from __future__ import annotations

from loopos.agent_language.message import AgentMessage
from loopos.agent_language.protocol import make_signal
from loopos.agent_language.roles import AgentRole
from loopos.agent_language.signals import SignalType
from loopos.loop_engine.models import EvaluationSignal, ReviewFinding, TestResult


def review_finding_to_message(
    finding: ReviewFinding,
    *,
    trace_id: str,
    iteration_id: str | int,
) -> AgentMessage:
    signal_type = (
        SignalType.FAKE_CONVERGENCE_DETECTED
        if finding.category == "fake_convergence"
        else SignalType.REVIEW_FINDING
    )
    return make_signal(
        trace_id=trace_id,
        iteration_id=iteration_id,
        from_role=AgentRole.MAD_DOG if finding.source == "mad_dog" else AgentRole.REVIEWER,
        to_role=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
        signal_type=signal_type,
        payload={
            "finding_id": finding.id,
            "category": finding.category,
            "severity": finding.severity,
            "gap": finding.claim,
            "target": "loop_engine.repair",
        },
        evidence=list(finding.evidence),
    )


def test_result_to_message(
    result: TestResult,
    *,
    trace_id: str,
    iteration_id: str | int,
) -> AgentMessage:
    failed = result.failed > 0
    return make_signal(
        trace_id=trace_id,
        iteration_id=iteration_id,
        from_role=AgentRole.TESTER,
        to_role=[AgentRole.REPAIRER, AgentRole.OPTIMIZER] if failed else AgentRole.REVIEWER,
        signal_type=SignalType.TEST_FAILED if failed else SignalType.TEST_PASSED,
        payload={
            "test_status": result.status,
            "failed": result.failed,
            "passed": result.passed,
            "target": "loop_engine.test",
        },
        evidence=list(result.failures or result.evidence),
    )


def message_to_evaluation_signal(message: AgentMessage) -> EvaluationSignal:
    category = str(message.payload.get("category") or message.signal_type)
    return EvaluationSignal(
        source="test" if message.from_role == AgentRole.TESTER else "reviewer",
        category=category,
        claim=str(message.payload.get("gap") or message.signal_type),
        evidence=list(message.evidence),
        proposed_step=str(message.payload.get("target") or ""),
        targets_loss_dim="fake_convergence"
        if message.signal_type == SignalType.FAKE_CONVERGENCE_DETECTED
        else "unsat_required",
    )


setattr(test_result_to_message, "__test__", False)


__all__ = [
    "message_to_evaluation_signal",
    "review_finding_to_message",
    "test_result_to_message",
]

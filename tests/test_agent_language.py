"""Tests for LAIL and communication distance routing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.agent_language import (
    AgentMessage,
    AgentRole,
    CommunicationDistanceOptimizer,
    LailMcpBridge,
    SignalRouter,
    SignalType,
    compact_to_message,
    json_to_compact,
    message_to_compact,
    review_finding_to_message,
    test_result_to_message,
)
from loopos.loop_engine import ReviewFinding, TestResult


def _message(signal_type: str = "review.finding") -> AgentMessage:
    return AgentMessage(
        trace_id="trace_1",
        iteration_id=4,
        from_role=AgentRole.REVIEWER,
        to_role=[AgentRole.REPAIRER, AgentRole.OPTIMIZER],
        signal_type=signal_type,
        payload={"target": "loop_engine.repair", "gap": "failed_test_to_repair"},
        evidence=["test_failed_feeds_repair"],
        confidence=0.86,
        quality_delta=0.12,
    )


def test_lail_message_has_trace_and_iteration() -> None:
    message = _message()
    assert message.trace_id == "trace_1"
    assert message.iteration_id == 4
    assert message.authority_delta == "none"


def test_lail_signal_does_not_execute_syscall() -> None:
    with pytest.raises(ValidationError):
        AgentMessage(
            trace_id="trace_1",
            iteration_id=1,
            from_role=AgentRole.PLANNER,
            to_role=AgentRole.BUILDER,
            signal_type="plan.proposed",
            payload={"syscall": {"op": "TERM.EXEC"}},
        )


def test_lail_json_to_compact_codec() -> None:
    line = message_to_compact(_message())
    assert line.startswith("review.finding ")
    assert "target=loop_engine.repair" in line
    decoded = compact_to_message(line)
    assert decoded.signal_type == "review.finding"
    assert decoded.payload["target"] == "loop_engine.repair"
    assert decoded.from_role == AgentRole.REVIEWER


def test_lail_compact_to_json_codec() -> None:
    line = json_to_compact(
        {
            "type": "repair.signal",
            "iteration": 4,
            "from": "tester",
            "to": "repairer",
            "target": "loop_engine.repair",
            "gap": "failed_test_to_repair",
            "priority": 0.86,
            "gain": 0.12,
            "requires_commitment": False,
            "authority_delta": "none",
        }
    )
    decoded = compact_to_message(line)
    assert decoded.signal_type == "repair.signal"
    assert decoded.payload["gap"] == "failed_test_to_repair"
    assert decoded.payload["priority"] == 0.86


def test_signal_router_sends_to_relevant_roles_only() -> None:
    routed = SignalRouter().route(_message(SignalType.REVIEW_FINDING))
    assert routed.recipients == [AgentRole.REPAIRER, AgentRole.OPTIMIZER]
    assert routed.metrics.broadcast_count == 0
    assert routed.metrics.redundant_context_avoided > 0


def test_test_failure_routes_to_repairer_and_optimizer() -> None:
    msg = test_result_to_message(
        TestResult(iteration_id="i", status="failed", failed=1, failures=["boom"]),
        trace_id="trace_1",
        iteration_id=1,
    )
    routed = CommunicationDistanceOptimizer().optimize(msg)
    assert routed.recipients == [AgentRole.REPAIRER, AgentRole.OPTIMIZER]
    assert routed.metrics.communication_distance == 1


def test_fake_convergence_routes_to_controller_and_delivery() -> None:
    msg = AgentMessage(
        trace_id="trace_1",
        iteration_id=1,
        from_role=AgentRole.MAD_DOG,
        to_role=AgentRole.LOOP_CONTROLLER,
        signal_type=SignalType.FAKE_CONVERGENCE_DETECTED,
        payload={"category": "fake_convergence"},
        evidence=["simulated only"],
    )
    routed = SignalRouter().route(msg)
    assert routed.recipients == [
        AgentRole.LOOP_CONTROLLER,
        AgentRole.DELIVERY_EVALUATOR,
    ]


def test_memory_context_compiled_routes_to_target_role() -> None:
    msg = AgentMessage(
        trace_id="trace_1",
        iteration_id=1,
        from_role=AgentRole.MEMORY_COMPILER,
        to_role=AgentRole.REPAIRER,
        signal_type=SignalType.MEMORY_CONTEXT_COMPILED,
        payload={"target_role": "repairer"},
    )
    routed = SignalRouter().route(msg)
    assert routed.recipients == [AgentRole.REPAIRER]


def test_review_signal_feeds_optimizer() -> None:
    finding = ReviewFinding(
        category="quality_gap",
        claim="missing evidence",
        recommended_fix="add evidence",
        evidence=["review"],
    )
    msg = review_finding_to_message(finding, trace_id="trace_1", iteration_id=1)
    routed = SignalRouter().route(msg)
    assert AgentRole.OPTIMIZER in routed.recipients
    assert msg.payload["finding_id"] == finding.id


def test_mcp_bridge_is_adapter_not_core_dependency() -> None:
    bridge = LailMcpBridge()
    payload = bridge.to_tool_payload(_message())
    assert payload["core_dependency"] is False
    assert bridge.supports_execution() is False

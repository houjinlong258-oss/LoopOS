"""Tests for Project Memory OS and MemoryCompiler."""

from __future__ import annotations

from loopos.agent_language import AgentRole
from loopos.project_memory import (
    DecisionMemory,
    FailureMemory,
    InMemoryProjectMemoryStore,
    MemoryCompiler,
    TestMemory,
    TokenBudgetLedger,
)


def _compiler() -> MemoryCompiler:
    store = InMemoryProjectMemoryStore()
    store.add(
        FailureMemory(
            content="previous repair repeated the same failing strategy",
            confidence=0.9,
            source="unit-test",
            tags=["repair", "failed_test_to_repair"],
            failed_attempt="patched docs only",
            failure_reason="failed test was not connected to RepairPlan",
            related_files=["loopos/loop_engine/repair.py"],
            related_tests=["test_failed_test_creates_repair_plan"],
            avoid_repeating="do not add docs without data-flow tests",
            next_time="feed TestResult.failures into ReviewFinding and RepairPlan",
        )
    )
    store.add(
        DecisionMemory(
            content="simulated adapters are allowed only when explicitly labeled",
            confidence=0.95,
            source="v0.4 prompt",
            tags=["simulation"],
            decision="status and source must expose simulation",
            rationale="do not pretend simulated execution is real",
        )
    )
    store.add(
        TestMemory(
            content="repair data-flow test",
            confidence=0.8,
            source="tests",
            tags=["repair"],
            test_name="test_failed_test_creates_repair_plan",
            result="passed",
        )
    )
    return MemoryCompiler(store)


def test_memory_compiler_creates_role_specific_context_packet() -> None:
    packet = _compiler().compile(
        target_role=AgentRole.REPAIRER,
        goal_summary="make failed tests feed repair plans",
        current_gap="failed_test_to_repair",
        token_budget=900,
    )
    assert packet.target_role == AgentRole.REPAIRER
    assert packet.relevant_failures
    assert packet.expected_output.startswith("repair plan")


def test_failure_memory_prevents_repeated_failed_attempt() -> None:
    packet = _compiler().compile(
        target_role=AgentRole.REPAIRER,
        goal_summary="repair loop",
        current_gap="repair",
        token_budget=900,
    )
    assert "do not add docs without data-flow tests" in packet.avoid_repeating
    assert any("patched docs only" in item for item in packet.relevant_failures)


def test_decision_memory_included_when_relevant() -> None:
    packet = _compiler().compile(
        target_role=AgentRole.OPTIMIZER,
        goal_summary="simulation honesty",
        current_gap="simulation",
        token_budget=900,
    )
    assert any("status and source" in item for item in packet.relevant_decisions)


def test_context_packet_respects_token_budget() -> None:
    packet = _compiler().compile(
        target_role=AgentRole.REPAIRER,
        goal_summary="x" * 100,
        current_gap="repair",
        token_budget=80,
    )
    assert packet.estimated_tokens <= packet.token_budget or not packet.relevant_failures


def test_memory_is_project_signal_not_chat_history() -> None:
    failure = FailureMemory(
        content="compressed project training signal",
        confidence=0.8,
        source="unit-test",
        failed_attempt="repeated broken patch",
        failure_reason="ignored test evidence",
        avoid_repeating="do not repeat broken patch",
        next_time="route failed test evidence to repairer",
    )
    assert failure.type == "failure"
    assert "chat" not in failure.model_dump_json().lower()


def test_token_budget_ledger_records_saved_tokens() -> None:
    ledger = TokenBudgetLedger.estimate(
        input_text="goal",
        output_text="repair plan",
        context_text="short packet",
        avoided_text="a long repeated history that does not need to be broadcast",
    )
    assert ledger.estimated_input_tokens > 0
    assert ledger.context_packet_tokens > 0
    assert ledger.saved_tokens_estimate > 0

"""MemoryCompiler for role-specific context packets."""

from __future__ import annotations

from collections.abc import Iterable

from loopos.agent_language.roles import AgentRole
from loopos.project_memory.models import (
    ContextPacket,
    DecisionMemory,
    FailureMemory,
    ProjectMemoryItem,
    TestMemory,
    TokenBudgetLedger,
)
from loopos.project_memory.store import InMemoryProjectMemoryStore


class MemoryCompiler:
    """Compile compressed project memory into the smallest useful packet."""

    def __init__(self, store: InMemoryProjectMemoryStore | None = None) -> None:
        self.store = store or InMemoryProjectMemoryStore()

    def compile(
        self,
        *,
        target_role: AgentRole,
        goal_summary: str,
        current_gap: str,
        token_budget: int = 900,
        run_id: str | None = None,
        iteration_index: int = 0,
        trace_id: str | None = None,
    ) -> ContextPacket:
        decisions = [
            item for item in self.store.list(type="decision")
            if isinstance(item, DecisionMemory)
        ]
        failures = [
            item for item in self.store.list(type="failure")
            if isinstance(item, FailureMemory)
        ]
        tests = [
            item for item in self.store.list(type="test")
            if isinstance(item, TestMemory)
        ]

        relevant_failures = _failure_lines(failures, current_gap, target_role)
        relevant_decisions = [d.decision or d.content for d in decisions]
        relevant_tests = [t.test_name or t.content for t in tests]
        relevant_files = _dedupe(file for f in failures for file in f.related_files)
        avoid_repeating = _dedupe(f.avoid_repeating for f in failures if f.avoid_repeating)

        # v0.4.0 closeout — track what was kept (selected_memory) and
        # what was dropped (omitted_memory_reason).
        selected_ids: set[str] = set()
        selected_memory: list[ProjectMemoryItem] = []
        for f in failures:
            if any(line.startswith(f.failed_attempt) for line in relevant_failures):
                if f.id not in selected_ids:
                    selected_ids.add(f.id)
                    selected_memory.append(f)
        for d in decisions:
            if d.id not in selected_ids:
                selected_ids.add(d.id)
                selected_memory.append(d)
        for t in tests:
            if t.id not in selected_ids:
                selected_ids.add(t.id)
                selected_memory.append(t)
        omitted_memory_reason: list[str] = []
        all_ids = {f.id for f in failures} | {d.id for d in decisions} | {t.id for t in tests}
        for omitted in all_ids - selected_ids:
            omitted_memory_reason.append(
                f"{omitted}: not selected by current role / gap / budget"
            )

        packet = ContextPacket(
            target_role=target_role,
            goal_summary=goal_summary,
            current_gap=current_gap,
            relevant_decisions=relevant_decisions,
            relevant_failures=relevant_failures,
            relevant_tests=relevant_tests,
            relevant_files=relevant_files,
            avoid_repeating=avoid_repeating,
            expected_output=_expected_output(target_role),
            token_budget=token_budget,
            selected_memory=selected_memory,
            omitted_memory_reason=omitted_memory_reason,
            run_id=run_id,
            iteration_index=iteration_index,
            trace_id=trace_id,
        )
        return _fit_budget(packet)

    def add(self, item: ProjectMemoryItem) -> ProjectMemoryItem:
        return self.store.add(item)


def _failure_lines(
    failures: list[FailureMemory],
    current_gap: str,
    target_role: AgentRole,
) -> list[str]:
    if target_role not in {AgentRole.REPAIRER, AgentRole.OPTIMIZER, AgentRole.LOOP_CONTROLLER}:
        return []
    gap_words = {part.lower() for part in current_gap.replace("/", " ").split() if part}
    out: list[str] = []
    for failure in failures:
        haystack = " ".join(
            [
                failure.failed_attempt,
                failure.failure_reason,
                failure.content,
                " ".join(failure.tags),
            ]
        ).lower()
        if not gap_words or any(word in haystack for word in gap_words):
            out.append(
                f"{failure.failed_attempt}: {failure.failure_reason}; "
                f"avoid={failure.avoid_repeating}; next={failure.next_time}"
            )
    return out


def _fit_budget(packet: ContextPacket) -> ContextPacket:
    while True:
        context_text = packet.model_dump_json()
        ledger = TokenBudgetLedger.estimate(
            input_text=packet.goal_summary,
            output_text=packet.expected_output,
            context_text=context_text,
            avoided_text="\n".join(packet.avoid_repeating),
        )
        estimated = ledger.context_packet_tokens
        packet = packet.model_copy(
            update={"estimated_tokens": estimated, "ledger": ledger}
        )
        if estimated <= packet.token_budget:
            return packet
        if packet.relevant_failures:
            packet.relevant_failures.pop()
        elif packet.relevant_decisions:
            packet.relevant_decisions.pop()
        elif packet.relevant_tests:
            packet.relevant_tests.pop()
        elif packet.relevant_files:
            packet.relevant_files.pop()
        elif packet.selected_memory:
            omitted = list(packet.omitted_memory_reason)
            omitted.extend(
                f"{item.id}: omitted to satisfy token budget"
                for item in packet.selected_memory
            )
            packet = packet.model_copy(
                update={"selected_memory": [], "omitted_memory_reason": omitted}
            )
        elif packet.omitted_memory_reason and packet.omitted_memory_reason != [
            "memory omitted to satisfy token budget"
        ]:
            packet = packet.model_copy(
                update={"omitted_memory_reason": ["memory omitted to satisfy token budget"]}
            )
        elif packet.avoid_repeating:
            packet.avoid_repeating.pop()
        elif packet.expected_output:
            packet = packet.model_copy(update={"expected_output": ""})
        else:
            return packet


def _expected_output(role: AgentRole) -> str:
    mapping = {
        AgentRole.REPAIRER: "repair plan with tests to run and failures to avoid",
        AgentRole.OPTIMIZER: "next-iteration optimization plan",
        AgentRole.PLANNER: "plan candidate anchored to success criteria",
        AgentRole.TESTER: "minimal relevant test result",
    }
    return mapping.get(role, "role-specific project-training signal")


def _dedupe(items: Iterable[object]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


__all__ = ["MemoryCompiler"]

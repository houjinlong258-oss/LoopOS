"""Adapters between existing AI-ISA models and AIL models."""

from __future__ import annotations

from typing import Any

from loopos.ail.models import AILInstruction, AILState
from loopos.core.isa import ExpectedObservation, Instruction
from loopos.core.state import LoopState


def instruction_to_ail(instruction: Instruction) -> AILInstruction:
    """Convert the existing AI-ISA instruction to canonical AIL."""

    args: dict[str, Any] = dict(instruction.args)
    metadata: dict[str, Any] = dict(instruction.metadata)
    if instruction.op == "EXEC_TERMINAL":
        metadata.setdefault("policy_scope", "terminal.execute")
    if instruction.op == "CALL_TOOL":
        metadata.setdefault("policy_scope", "tool.call")
        metadata.setdefault("routing", {"tool": args.get("tool")})
        args.setdefault("arguments", {})
    return AILInstruction(
        id=instruction.id,
        op=instruction.op,
        created_at=instruction.created_at,
        reason_code=instruction.reason_code,
        args=args,
        safety=instruction.safety,
        expected_observation=instruction.expected_observation or ExpectedObservation(),
        metadata=metadata,
    )


def ail_to_instruction(instruction: AILInstruction) -> Instruction:
    """Convert AIL back to the existing AI-ISA instruction model."""

    return Instruction(
        id=instruction.id,
        op=instruction.op,
        created_at=instruction.created_at,
        reason_code=instruction.reason_code,
        args=dict(instruction.args),
        safety=instruction.safety,
        expected_observation=instruction.expected_observation,
        metadata=dict(instruction.metadata),
    )


def state_to_ail(state: LoopState) -> AILState:
    """Create a compact AIL state view from LoopState."""

    return AILState(
        run_id=state.run_id,
        status=state.status,
        step_index=state.step_index,
        progress_score=state.progress_score,
        current_instruction_id=state.current_instruction.id if state.current_instruction else None,
        memory_refs=list(state.memory_refs),
    )

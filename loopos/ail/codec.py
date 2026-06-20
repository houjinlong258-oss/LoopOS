"""Adapters between existing AI-ISA models and AIL models."""

from __future__ import annotations

from typing import Any, cast

from loopos.ail.models import AILInstruction, AILState, LEGACY_TO_KERNEL_OP
from loopos.core.isa import ExpectedObservation, Instruction, InstructionOp
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

    op: str = instruction.op
    if "." in op:
        reverse = {kernel: legacy for legacy, kernel in LEGACY_TO_KERNEL_OP.items()}
        if op not in reverse:
            raise ValueError(f"kernel operation has no legacy AI-ISA mapping: {op}")
        op = reverse[op]
    return Instruction(
        id=instruction.id,
        op=cast(InstructionOp, op),
        created_at=instruction.created_at,
        reason_code=instruction.reason_code,
        args=dict(instruction.args),
        safety=instruction.safety,
        expected_observation=instruction.expected_observation,
        metadata=dict(instruction.metadata),
    )


def normalize_instruction(instruction: AILInstruction, *, run_id: str, step: int) -> AILInstruction:
    """Return the canonical dotted-operation view used by the kernel."""

    payload = instruction.model_dump(mode="python")
    payload.update({"run_id": run_id, "step": step, "op": instruction.normalized_op})
    return AILInstruction.model_validate(payload)


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

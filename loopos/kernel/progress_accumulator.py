"""Persistent per-run convergence progress accounting."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field

from loopos.ail.models import AILInstruction
from loopos.convergence import EvaluationResult, ProgressDelta
from loopos.kernel.models import RunRecord


class ProgressAccumulatorSnapshot(BaseModel):
    schema_version: int = 1
    previous_score: float = Field(default=0.0, ge=0.0, le=1.0)
    current_score: float = Field(default=0.0, ge=0.0, le=1.0)
    no_progress_count: int = Field(default=0, ge=0)
    repeated_failures: int = Field(default=0, ge=0)
    repeated_actions: int = Field(default=0, ge=0)
    last_action_fingerprint: str | None = None
    last_failure_fingerprint: str | None = None
    last_reason_code: str | None = None


def load_progress_accumulator(run: RunRecord) -> ProgressAccumulatorSnapshot:
    payload = run.metadata.get("progress_accumulator")
    if isinstance(payload, dict):
        return ProgressAccumulatorSnapshot.model_validate(payload)
    return ProgressAccumulatorSnapshot(current_score=run.progress_score)


def save_progress_accumulator(
    run: RunRecord,
    snapshot: ProgressAccumulatorSnapshot,
) -> None:
    run.metadata["progress_accumulator"] = snapshot.model_dump(mode="json")


def update_progress_accumulator(
    *,
    run: RunRecord,
    evaluation: EvaluationResult,
    instruction: AILInstruction | None,
    current_score: float,
    failure_fingerprint: str | None = None,
) -> tuple[ProgressAccumulatorSnapshot, ProgressDelta]:
    snapshot = load_progress_accumulator(run)
    previous = snapshot.current_score
    current = max(0.0, min(1.0, current_score))
    failed = evaluation.failed or evaluation.blocked

    snapshot.repeated_failures = snapshot.repeated_failures + 1 if failed else 0
    snapshot.no_progress_count = snapshot.no_progress_count + 1 if current <= previous else 0

    action_fingerprint = fingerprint_instruction(instruction)
    if action_fingerprint and action_fingerprint == snapshot.last_action_fingerprint:
        snapshot.repeated_actions += 1
    else:
        snapshot.repeated_actions = 0

    if failed:
        snapshot.last_failure_fingerprint = failure_fingerprint or _failure_fingerprint(evaluation)
    snapshot.previous_score = previous
    snapshot.current_score = current
    snapshot.last_action_fingerprint = action_fingerprint
    snapshot.last_reason_code = evaluation.reason_codes[0] if evaluation.reason_codes else None
    save_progress_accumulator(run, snapshot)

    progress = ProgressDelta(
        run_id=run.run_id,
        step_id=instruction.id if instruction is not None else run.current_instruction_id,
        previous_score=previous,
        current_score=current,
        delta=current - previous,
        no_progress_count=snapshot.no_progress_count,
        repeated_failures=snapshot.repeated_failures,
        repeated_actions=snapshot.repeated_actions,
        action_fingerprint=action_fingerprint,
        evidence=list(evaluation.evidence),
    )
    return snapshot, progress


def fingerprint_instruction(instruction: AILInstruction | None) -> str | None:
    if instruction is None:
        return None
    encoded = json.dumps(
        {"op": instruction.op, "args": instruction.args},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _failure_fingerprint(evaluation: EvaluationResult) -> str:
    encoded = json.dumps(
        {
            "failure_type": evaluation.failure_type,
            "reason_codes": evaluation.reason_codes,
            "evidence": evaluation.evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

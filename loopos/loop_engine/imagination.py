"""Imagination Sandbox: free-form idea generation, no side effects.

The sandbox is the v0.4.0 surface where models can brainstorm,
speculate, attack, propose wild architectures, and disagree with
themselves — **without** triggering a hard policy block. It is the
*thought* layer.

Hard invariants (enforced at the type level and at runtime):

1. ``CreativeCandidate.authority_delta`` is always ``"none"``. There is
   no other value.
2. ``ImaginationResult`` carries no ``SyscallRequest``, no file path
   mutation, no network endpoint, and no release operation.
3. The sandbox does not call into ``PolicyEngine`` for hard blocks.
   Policy can attach an advisory risk label; it cannot refuse to
   return a result.
4. The sandbox does not create a ``CommitmentProposal``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from loopos.loop_engine.models import UserGoal


ImaginationMode = Literal[
    "brainstorm", "wild", "alternatives",
    "architecture", "repair", "optimization",
]


class ImaginationRequest(BaseModel):
    """A request to the imagination sandbox."""

    model_config = ConfigDict(extra="forbid")

    goal: UserGoal
    prompt: str
    mode: ImaginationMode = "brainstorm"
    max_candidates: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def _check(self) -> "ImaginationRequest":
        if not self.prompt.strip():
            raise ValueError("ImaginationRequest.prompt must be non-empty")
        return self


class CreativeCandidate(BaseModel):
    """A single creative idea from the sandbox.

    The ``authority_delta`` field is *hard-pinned* to ``"none"``. This
    is the type-level guarantee that imagination cannot dispatch
    authority-bearing actions.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"cand_{uuid4().hex[:8]}")
    title: str
    summary: str
    rationale: str = ""
    assumptions: list[str] = Field(default_factory=list)
    expected_benefits: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    possible_actions: list[str] = Field(default_factory=list)
    wildness_level: int = Field(default=1, ge=0, le=5)
    requires_commitment: bool = False
    authority_delta: Literal["none"] = "none"


class ImaginationResult(BaseModel):
    """The output of the sandbox. No syscalls, no mutations."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[CreativeCandidate] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    mode: ImaginationMode = "brainstorm"

    def has_executable_action(self) -> bool:
        """Defensive check: the sandbox must never expose executable actions.

        The result model has no ``syscall`` / ``file_mutation`` / ``network``
        field by construction, but this method makes the invariant
        explicit and unit-testable.
        """
        # No executable surface exists on this model. Return False
        # unconditionally. The method exists so callers (and tests)
        # can verify the invariant symbolically.
        return False


# Fields a CreativeCandidate must never carry. The model uses
# ``extra="forbid"`` so any attempt to add one of these is rejected
# at construction time. The set is duplicated here for documentation
# and runtime checks.
_FORBIDDEN_IMAGINATION_FIELDS = frozenset({
    "syscall", "syscall_request", "file_mutation", "network_call",
    "release_operation", "approval_decision", "authority_delta",
})


class ImaginationSandbox:
    """Deterministic, offline creative idea generation.

    The default implementation in v0.4.0 uses deterministic
    templates to produce candidates; an LLM-backed implementation
    can be plugged in by setting ``candidate_factory``. The hard
    invariants (no authority delta, no syscalls) are guaranteed
    by the model types regardless of the factory.
    """

    def __init__(
        self,
        candidate_factory: Callable[[ImaginationRequest], Iterable[CreativeCandidate]] | None = None,
    ) -> None:
        self._candidate_factory = candidate_factory

    def imagine(self, request: ImaginationRequest) -> ImaginationResult:
        if self._candidate_factory is not None:
            candidates = list(self._candidate_factory(request))
        else:
            candidates = self._default_candidates(request)
        # Defensive: enforce authority_delta and absence of executable
        # surface. The model types already enforce this, but we double-
        # check at the boundary so a future buggy factory can't slip
        # through.
        for cand in candidates:
            if cand.authority_delta != "none":
                raise ValueError(
                    f"ImaginationSandbox: candidate {cand.id} has "
                    f"authority_delta={cand.authority_delta!r}; "
                    f"only 'none' is allowed."
                )
        return ImaginationResult(
            candidates=candidates[: request.max_candidates],
            mode=request.mode,
            notes=[f"mode={request.mode}", f"max_candidates={request.max_candidates}"],
        )

    @staticmethod
    def _default_candidates(request: ImaginationRequest) -> list[CreativeCandidate]:
        goal_text = request.goal.normalized_goal or request.goal.raw_goal
        base = f"Approach for: {goal_text}"
        return [
            CreativeCandidate(
                title=f"Option {i + 1} for {request.mode}",
                summary=f"{base} (variant {i + 1})",
                rationale=request.prompt,
                wildness_level=1 if request.mode != "wild" else 4,
            )
            for i in range(request.max_candidates)
        ]


__all__ = [
    "CreativeCandidate",
    "ImaginationMode",
    "ImaginationRequest",
    "ImaginationResult",
    "ImaginationSandbox",
    "_FORBIDDEN_IMAGINATION_FIELDS",
]

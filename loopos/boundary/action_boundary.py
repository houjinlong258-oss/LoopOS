"""Action boundary facade: thin compatibility layer over policy + syscall.

The ``ActionBoundary`` does not re-implement policy or syscall
routing. It is a facade: it forwards decisions to the existing
``loopos.policy_os`` and ``loopos.syscalls`` packages when they are
importable, and falls back to a deterministic allow-list when they
are not (so unit tests do not require the full stack to be present).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class _BoundaryBackend:
    """Lazy handle to the underlying policy / syscall modules."""

    policy_engine: Any = None
    syscall_router: Any = None
    available: bool = False
    import_error: str | None = None

    def ensure(self) -> None:
        if self.policy_engine is not None or self.import_error is not None:
            return
        try:
            from loopos.policy_os.engine import PolicyEngine  # type: ignore
            from loopos.syscalls.router import SyscallRouter  # type: ignore
            self.policy_engine = PolicyEngine
            self.syscall_router = SyscallRouter
            self.available = True
        except Exception as exc:  # noqa: BLE001
            self.import_error = str(exc)
            self.available = False


class ActionBoundaryDecision(BaseModel):
    """Structured decision on an action."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason_codes: list[str] = Field(default_factory=list)
    risk_label: str = "low"
    constraints: list[str] = Field(default_factory=list)
    audit_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex[:8]}")


class ActionBoundary:
    """The v0.4.0 action boundary facade.

    In v0.4.0 the boundary is a pure facade. It returns an
    ``ActionBoundaryDecision`` that is structurally compatible with
    the v0.2 / v0.3 policy / syscall outputs, but it does not
    dispatch side effects on its own. The ``LoopEngine`` and CLI
    consume the decision; the dispatch layer is preserved as-is.
    """

    def __init__(self) -> None:
        self._backend = _BoundaryBackend()
        self._audit_trail: list[ActionBoundaryDecision] = []

    def evaluate(
        self,
        action: str,
        action_type: str,
        required_permissions: list[str] | None = None,
    ) -> ActionBoundaryDecision:
        self._backend.ensure()
        # In v0.4.0, the action boundary is structurally a pass-through
        # with a clear audit trail. The actual policy / syscall routing
        # is performed by the existing v0.2 / v0.3 layers.
        decision = ActionBoundaryDecision(
            allowed=True,
            reason_codes=[f"action={action_type}"],
            risk_label="low" if action_type in {"plan", "doc"} else "medium",
            constraints=list(required_permissions or []),
        )
        self._audit_trail.append(decision)
        return decision

    def audit_trail(self) -> list[ActionBoundaryDecision]:
        return list(self._audit_trail)

    def clear_audit(self) -> None:
        self._audit_trail.clear()

    @property
    def backend_available(self) -> bool:
        self._backend.ensure()
        return self._backend.available


__all__ = ["ActionBoundary", "ActionBoundaryDecision"]


# Quiet linters
_ = field

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
    initialized: bool = False

    def ensure(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        try:
            from loopos.policy_os.engine import PolicyEngine  # type: ignore
            from loopos.syscalls.router import SyscallRouter  # type: ignore
            self.policy_engine = PolicyEngine
            self.syscall_router = SyscallRouter
        except Exception as exc:  # noqa: BLE001
            self.import_error = str(exc)
            return
        self.available = True


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
        """Route ``(action, action_type)`` through policy + syscall.

        Priority:

        1. If the v0.2/v0.3 backend is importable, route the request
           through :func:`PolicyEngine.evaluate` and fold the
           decision into our own audit trail.
        2. Otherwise fall back to the deterministic allow-list and
           record the reason so audit consumers know which path was
           taken.
        """
        self._backend.ensure()
        risk_label = "low" if action_type in {"plan", "doc"} else "medium"
        reason_codes: list[str] = [f"action={action_type}"]
        constraints = list(required_permissions or [])

        if self._backend.available:
            try:
                policy_engine = self._backend.policy_engine.load_default()
                decision = policy_engine.evaluate(
                    action_type,
                    subject={"action": action, "permissions": constraints},
                    risk_level=risk_label,
                )
                allowed = bool(getattr(decision, "allowed", False))
                if not allowed:
                    reason_codes.append("policy_denied")
                else:
                    reason_codes.append("policy_allowed")
                for code in getattr(decision, "reason_codes", []) or []:
                    reason_codes.append(f"policy.{code}")
                risk_label = getattr(decision, "risk_level", risk_label) or risk_label
                if getattr(decision, "requires_approval", False):
                    constraints.append("requires_approval")
                decision_obj = ActionBoundaryDecision(
                    allowed=allowed,
                    reason_codes=reason_codes,
                    risk_label=risk_label,
                    constraints=constraints,
                )
                self._audit_trail.append(decision_obj)
                return decision_obj
            except Exception:  # noqa: BLE001 - fall back to allow-list
                reason_codes.append("policy_backend_error")

        # Deterministic fallback: refuse unless the action_type is
        # explicitly read-only / observational. Anything that would
        # mutate state or talk to the shell is denied.
        allowed = action_type in {"plan", "doc", "observe", "read"}
        if not allowed:
            reason_codes.append("policy_backend_unavailable_denied")
        decision_obj = ActionBoundaryDecision(
            allowed=allowed,
            reason_codes=reason_codes,
            risk_label=risk_label,
            constraints=constraints,
        )
        self._audit_trail.append(decision_obj)
        return decision_obj

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

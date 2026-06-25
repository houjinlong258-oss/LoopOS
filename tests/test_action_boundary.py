"""Tests for ``loopos.boundary.ActionBoundary``.

The boundary is the single chokepoint every side-effect goes through
before dispatch. These tests guard the audit trail + the policy /
syscall routing semantics. Critically: a denial must propagate up
to callers — a pass-through that always returns ``allowed=True``
is silently unsafe and would defeat the v0.4 closeout invariant.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from loopos.boundary.action_boundary import (
    ActionBoundary,
    ActionBoundaryDecision,
)


class TestActionBoundaryFallback:
    """When the v0.2/v0.3 backend is not importable (CI / minimal env),
    the boundary must fall back to a deterministic allow-list: read-only
    actions are allowed, mutating actions are denied. This is the
    safety floor — never ``allowed=True`` for everything."""

    def _force_fallback(self, boundary: ActionBoundary) -> None:
        """Disable the lazy backend so ``evaluate`` exercises the
        deterministic allow-list fallback path even when the host
        environment imports policy_os successfully."""
        boundary._backend.initialized = True
        boundary._backend.available = False
        boundary._backend.policy_engine = None
        boundary._backend.syscall_router = None
        boundary._backend.import_error = "forced by test"

    def test_read_only_actions_allowed(self) -> None:
        boundary = ActionBoundary()
        self._force_fallback(boundary)
        assert boundary.evaluate("read_x", "read").allowed is True
        assert boundary.evaluate("summarise", "plan").allowed is True
        assert boundary.evaluate("explain", "doc").allowed is True
        assert boundary.evaluate("watch", "observe").allowed is True

    def test_mutating_actions_denied(self) -> None:
        boundary = ActionBoundary()
        self._force_fallback(boundary)
        decision = boundary.evaluate(
            "apply_patch", "file_write",
            required_permissions=["allow_file_write"],
        )
        assert decision.allowed is False
        assert "policy_backend_unavailable_denied" in decision.reason_codes

    def test_shell_command_denied(self) -> None:
        boundary = ActionBoundary()
        self._force_fallback(boundary)
        decision = boundary.evaluate(
            "run_command", "shell",
            required_permissions=["allow_shell"],
        )
        assert decision.allowed is False
        assert "policy_backend_unavailable_denied" in decision.reason_codes

    def test_required_permissions_become_constraints(self) -> None:
        boundary = ActionBoundary()
        self._force_fallback(boundary)
        decision = boundary.evaluate(
            "apply_patch", "file_write",
            required_permissions=["allow_file_write"],
        )
        assert "allow_file_write" in decision.constraints


class TestActionBoundaryPolicyRouting:
    """When the policy backend is available, the boundary MUST route the
    request through ``PolicyEngine.evaluate`` and propagate the
    decision — not silently overwrite it."""

    def test_policy_allow_propagates(self) -> None:
        boundary = ActionBoundary()

        class _FakeDecision:
            allowed = True
            reason_codes = ["explicit_allow"]
            risk_level = "low"
            requires_approval = False

        class _FakeEngine:
            @staticmethod
            def load_default() -> Any:
                return _FakeEngine

            @staticmethod
            def evaluate(*args: Any, **kwargs: Any) -> _FakeDecision:
                return _FakeDecision()

        with patch.object(boundary._backend, "initialized", True), \
             patch.object(boundary._backend, "available", True), \
             patch.object(boundary._backend, "policy_engine", _FakeEngine):
            decision = boundary.evaluate("inspect", "read")
            assert decision.allowed is True
            assert "policy.allowed" in decision.reason_codes or \
                   "policy.explicit_allow" in decision.reason_codes

    def test_policy_deny_propagates_and_marks_audit(self) -> None:
        boundary = ActionBoundary()
        trail_before = list(boundary.audit_trail())

        class _FakeDecision:
            allowed = False
            reason_codes = ["capability_required", "human_only"]
            risk_level = "high"
            requires_approval = True

        class _FakeEngine:
            @staticmethod
            def load_default() -> Any:
                return _FakeEngine

            @staticmethod
            def evaluate(*args: Any, **kwargs: Any) -> _FakeDecision:
                return _FakeDecision()

        with patch.object(boundary._backend, "initialized", True), \
             patch.object(boundary._backend, "available", True), \
             patch.object(boundary._backend, "policy_engine", _FakeEngine):
            decision = boundary.evaluate(
                "release_tag", "tag",
                required_permissions=["require_human_approval"],
            )
            assert decision.allowed is False
            assert "policy_denied" in decision.reason_codes
            assert "policy.capability_required" in decision.reason_codes
            assert "policy.human_only" in decision.reason_codes
            assert "requires_approval" in decision.constraints
            assert decision.risk_label == "high"

        # The decision must be appended to the audit trail so callers
        # can replay why a side-effect was refused.
        assert len(boundary.audit_trail()) == len(trail_before) + 1


class TestActionBoundaryAuditTrail:
    """Every evaluation must be appended to ``audit_trail`` — denied or
    allowed. ``clear_audit`` resets the buffer."""

    def test_all_decisions_appear_in_trail(self) -> None:
        boundary = ActionBoundary()
        TestActionBoundaryFallback()._force_fallback(boundary)
        for action_type in ("read", "shell", "plan", "doc", "file_write"):
            boundary.evaluate(f"act_{action_type}", action_type)
        trail = boundary.audit_trail()
        assert len(trail) == 5
        assert all(isinstance(d, ActionBoundaryDecision) for d in trail)

    def test_clear_audit_resets(self) -> None:
        boundary = ActionBoundary()
        TestActionBoundaryFallback()._force_fallback(boundary)
        boundary.evaluate("a", "read")
        boundary.evaluate("b", "shell")
        assert len(boundary.audit_trail()) == 2
        boundary.clear_audit()
        assert boundary.audit_trail() == []

    def test_backend_available_reflects_import_state(self) -> None:
        # When the policy / syscall packages are importable the
        # backend property must report True; otherwise False.
        # (We can't assert a fixed value because the import state
        # depends on the host environment.)
        boundary = ActionBoundary()
        assert boundary.backend_available is (
            boundary._backend.policy_engine is not None
        )


class TestActionBoundaryNeverTrivialAllow:
    """The bug we fixed in v0.4 closeout: an empty / no-op ``evaluate``
    that returned ``allowed=True`` for every input. Lock that down so
    the regression cannot return."""

    @pytest.mark.parametrize(
        "action_type",
        ["file_write", "shell", "tag", "release", "send_message",
         "execute", "build", "test"],
    )
    def test_dangerous_action_types_denied_in_fallback(
        self, action_type: str,
    ) -> None:
        boundary = ActionBoundary()
        TestActionBoundaryFallback()._force_fallback(boundary)
        decision = boundary.evaluate(f"x_{action_type}", action_type)
        assert decision.allowed is False, (
            f"boundary.allow=True for dangerous action_type={action_type!r} "
            f"would be a regression of the no-op pass-through bug"
        )

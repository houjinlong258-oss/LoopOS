"""Tests for the extended Kernel Invariants (v0.5)."""

from __future__ import annotations

from loopos.kernel.invariants import KernelInvariantChecker


def test_invariant_data_guard_blocks_migration_without_backup() -> None:
    checker = KernelInvariantChecker()
    events = [
        {
            "kind": "syscall",
            "id": "sc-1",
            "payload": {"name": "database.run_migration"},
        },
    ]
    violations = checker.check_data_guard("run-1", 1, events)
    assert any(v.invariant_id == "I7_DATA_GUARD_BEFORE_DATABASE_ACTION" for v in violations)


def test_invariant_data_guard_passes_with_backup() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "observation", "payload": {"backup_verified": True}},
        {
            "kind": "syscall",
            "id": "sc-1",
            "payload": {"name": "database.run_migration"},
        },
    ]
    violations = checker.check_data_guard("run-1", 1, events)
    assert not violations


def test_invariant_provider_policy_blocks_without_policy() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "syscall", "id": "sc-1", "payload": {"name": "provider.chat"}},
    ]
    violations = checker.check_provider_policy("run-1", 1, events)
    assert any(v.invariant_id == "I8_PROVIDER_POLICY_BEFORE_MODEL_CALL" for v in violations)


def test_invariant_provider_policy_passes_with_policy() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "policy", "payload": {"allowed": True}},
        {"kind": "syscall", "id": "sc-1", "payload": {"name": "provider.chat"}},
    ]
    violations = checker.check_provider_policy("run-1", 1, events)
    assert not violations


def test_invariant_gateway_auth_blocks_without_auth() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "syscall", "id": "sc-1", "payload": {"name": "gateway.send"}},
    ]
    violations = checker.check_gateway_auth("run-1", 1, events)
    assert any(v.invariant_id == "I9_GATEWAY_AUTH_BEFORE_DELIVERY" for v in violations)


def test_invariant_gateway_auth_passes_with_auth() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "observation", "payload": {"auth_allowed": True}},
        {"kind": "syscall", "id": "sc-1", "payload": {"name": "gateway.send"}},
    ]
    violations = checker.check_gateway_auth("run-1", 1, events)
    assert not violations


def test_invariant_skill_governance_blocks_activation_without_governance() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "skill", "id": "sk-1", "payload": {"activated": True}},
    ]
    violations = checker.check_skill_governance("run-1", 1, events)
    assert any(v.invariant_id == "I10_SKILL_GOVERNANCE_BEFORE_ACTIVATION" for v in violations)


def test_invariant_maintainability_gate_blocks_approval_without_report() -> None:
    checker = KernelInvariantChecker()
    events = [
        {
            "kind": "review",
            "id": "rv-1",
            "payload": {"decision": "approve", "maintainability_report_id": None},
        },
    ]
    violations = checker.check_maintainability_gate("run-1", 1, events)
    assert any(v.invariant_id == "I11_MAINTAINABILITY_GATE_BEFORE_REVIEW_APPROVAL" for v in violations)


def test_invariant_maintainability_gate_blocks_when_blocked() -> None:
    checker = KernelInvariantChecker()
    events = [
        {
            "kind": "review",
            "id": "rv-1",
            "payload": {
                "decision": "approve",
                "maintainability_report_id": "rpt-1",
                "maintainability_blocked": True,
            },
        },
    ]
    violations = checker.check_maintainability_gate("run-1", 1, events)
    assert any(v.invariant_id == "I11_MAINTAINABILITY_GATE_BEFORE_REVIEW_APPROVAL" for v in violations)


def test_invariant_review_artifact_blocks_merge_without_artifact() -> None:
    checker = KernelInvariantChecker()
    events = [
        {
            "kind": "transition",
            "id": "tr-1",
            "payload": {"after": {"status": "merged"}},
        },
    ]
    violations = checker.check_review_artifact_before_merge("run-1", 1, events)
    assert any(v.invariant_id == "I12_REVIEW_ARTIFACT_BEFORE_MERGE" for v in violations)


def test_invariant_checkpoint_warns_on_high_risk_without_checkpoint() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "policy", "id": "p-1", "payload": {"safety_level": "L3"}},
    ]
    violations = checker.check_checkpoint_before_high_risk("run-1", 1, events)
    assert any(v.invariant_id == "I13_CHECKPOINT_BEFORE_HIGH_RISK_ACTION" for v in violations)


def test_invariant_checkpoint_passes_with_checkpoint() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "checkpoint", "payload": {"step": 1}},
        {"kind": "policy", "id": "p-1", "payload": {"safety_level": "L3"}},
    ]
    violations = checker.check_checkpoint_before_high_risk("run-1", 1, events)
    assert not violations


def test_invariant_checkpoint_skipped_for_l5_blocked() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "policy", "id": "p-1", "payload": {"safety_level": "L5"}},
    ]
    violations = checker.check_checkpoint_before_high_risk("run-1", 1, events)
    assert not violations


def test_check_all_extended_runs_every_invariant() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "syscall", "id": "sc-1", "payload": {"name": "database.run_migration"}},
    ]
    violations = checker.check_all_extended("run-1", 1, events)
    ids = {v.invariant_id for v in violations}
    assert "I7_DATA_GUARD_BEFORE_DATABASE_ACTION" in ids

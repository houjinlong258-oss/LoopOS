"""Policy OS evaluation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loopos.policy_os.conflict_resolver import resolve_policy_conflicts
from loopos.policy_os.loader import load_policy_packs
from loopos.policy_os.matcher import matches_rule
from loopos.policy_os.models import PolicyContext, PolicyDecision, PolicyRequest, SafetyLevel
from loopos.policy_os.registry import PolicyRegistry


class PolicyEngine:
    """Evaluate structured runtime requests against policy packs."""

    def __init__(self, registry: PolicyRegistry | None = None) -> None:
        self.registry = registry or PolicyRegistry()

    @classmethod
    def from_paths(cls, paths: list[str | Path]) -> "PolicyEngine":
        return cls(PolicyRegistry(load_policy_packs(paths)))

    @classmethod
    def load_default(cls, root: str | Path | None = None) -> "PolicyEngine":
        if root is not None:
            policy_root = Path(root)
        else:
            cwd_root = Path.cwd() / "policies"
            source_root = Path(__file__).resolve().parents[2] / "policies"
            policy_root = cwd_root if cwd_root.exists() else source_root
        return cls.from_paths([policy_root])

    def evaluate(
        self,
        scope: str,
        *,
        subject: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        risk_level: str = "low",
        actor: str = "runtime",
        metadata: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        request = PolicyRequest(
            scope=scope,
            subject=subject or {},
            tags=tags or [],
            risk_level=_normalize_risk(risk_level),
            actor=actor,
            metadata=metadata or {},
        )
        matched = [rule for rule in self.registry.list_rules(scope=scope) if matches_rule(rule, request)]
        decision = resolve_policy_conflicts(matched)
        inferred = _infer_safety_level(request, decision)
        return decision.model_copy(
            update={
                "safety_level": _max_safety(decision.safety_level, inferred),
                "human_only": decision.human_only or inferred == "L4",
                "rollback_required": decision.rollback_required or inferred == "L3",
            }
        )

    def evaluate_context(
        self,
        scope: str,
        context: PolicyContext,
        *,
        tags: list[str] | None = None,
        risk_level: str = "low",
    ) -> PolicyDecision:
        """Evaluate a complete kernel context while preserving the existing API."""

        return self.evaluate(
            scope,
            subject=context.model_dump(mode="json"),
            tags=tags,
            risk_level=risk_level,
            metadata={"phase": context.phase},
        )


def _normalize_risk(value: str) -> str:
    if value in {"low", "medium", "high", "blocked"}:
        return value
    return "low"


def _infer_safety_level(request: PolicyRequest, decision: PolicyDecision) -> SafetyLevel:
    text = str(request.subject).lower()
    if decision.action == "deny" or request.risk_level == "blocked":
        return "L5"
    blocked_markers = ("rm -rf /", "curl", "| bash", "| sh", "mkfs", "dd if=", "exfiltrate")
    if any(marker in text for marker in blocked_markers) and ("|" in text or "rm -rf /" in text or "mkfs" in text or "dd if=" in text):
        return "L5"
    if any(marker in text for marker in ("payment", "credit_card", "raw pii", "customer export")):
        return "L4"
    if request.risk_level == "high" or any(
        marker in text for marker in ("git reset", "git clean", "sudo", "restore", "production")
    ):
        return "L3"
    if decision.requires_approval or request.risk_level == "medium" or any(
        marker in text for marker in ("file.write", "delete", "chmod", "alter table")
    ):
        return "L2"
    if any(marker in text for marker in ("pytest", "test", "temporary", "local")):
        return "L1"
    return "L0"


def _max_safety(left: SafetyLevel, right: SafetyLevel) -> SafetyLevel:
    return left if int(left[1:]) >= int(right[1:]) else right

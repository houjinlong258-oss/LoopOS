"""Policy OS evaluation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loopos.policy_os.conflict_resolver import resolve_policy_conflicts
from loopos.policy_os.loader import load_policy_packs
from loopos.policy_os.matcher import matches_rule
from loopos.policy_os.models import PolicyContext, PolicyDecision, PolicyRequest
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
        return resolve_policy_conflicts(matched)

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

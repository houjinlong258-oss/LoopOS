"""Permission policy for terminal and tool execution."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from loopos.core.safety import CommandRiskAnalyzer, RiskAssessment, RiskLevel
from loopos.policy_os.engine import PolicyEngine


class PermissionDecision(BaseModel):
    """Decision returned by PermissionPolicy."""

    allowed: bool
    risk_level: RiskLevel
    requires_approval: bool
    reasons: list[str] = Field(default_factory=list)
    matched_patterns: list[str] = Field(default_factory=list)
    timeout_seconds: int
    suggested_safe_alternative: str | None = None


class PermissionPolicy:
    """Conservative policy that must approve commands before execution."""

    def __init__(
        self,
        *,
        allowlist_paths: list[str | Path] | None = None,
        denylist_patterns: list[str] | None = None,
        require_approval_patterns: list[str] | None = None,
        max_timeout_seconds: int = 30,
        network_allowed: bool = False,
        non_interactive: bool = True,
        analyzer: CommandRiskAnalyzer | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.allowlist_paths = [Path(path).resolve() for path in (allowlist_paths or [])]
        self.denylist_patterns = denylist_patterns or []
        self.require_approval_patterns = require_approval_patterns or []
        self.max_timeout_seconds = max_timeout_seconds
        self.network_allowed = network_allowed
        self.non_interactive = non_interactive
        self.analyzer = analyzer or CommandRiskAnalyzer()
        self.policy_engine = policy_engine or PolicyEngine.load_default()

    def evaluate(
        self,
        cmd: str,
        *,
        cwd: str | Path | None = None,
        timeout_seconds: int | None = None,
        auto_approve: bool = False,
    ) -> PermissionDecision:
        timeout = timeout_seconds or self.max_timeout_seconds
        reasons: list[str] = []

        if timeout <= 0:
            return self._deny("blocked", True, ["timeout must be positive"], timeout_seconds=timeout)
        if timeout > self.max_timeout_seconds:
            reasons.append(
                f"timeout capped from {timeout} to {self.max_timeout_seconds} seconds"
            )
            timeout = self.max_timeout_seconds

        cwd_path = Path(cwd or ".").resolve()
        if self.allowlist_paths and not self._inside_allowlist(cwd_path):
            return self._deny(
                "blocked",
                True,
                [f"cwd is outside allowlist: {cwd_path}"],
                timeout_seconds=timeout,
            )

        for pattern in self.denylist_patterns:
            if re.search(pattern, cmd, re.IGNORECASE):
                return self._deny(
                    "blocked",
                    True,
                    [f"denylist pattern matched: {pattern}"],
                    matched_patterns=[pattern],
                    timeout_seconds=timeout,
                )

        assessment = self.analyzer.analyze(cmd)
        reasons.extend(assessment.reasons)
        policy_decision = self.policy_engine.evaluate(
            "terminal.execute",
            subject={
                "cmd": cmd,
                "cwd": str(cwd_path),
                "timeout_seconds": timeout,
                "risk_level": assessment.risk_level,
                "requires_approval": assessment.requires_approval,
                "matched_patterns": assessment.matched_patterns,
            },
            tags=["terminal"],
            risk_level=assessment.risk_level,
        )
        if policy_decision.action == "deny":
            return self._from_assessment(
                assessment,
                allowed=False,
                reasons=reasons + [f"policy denied: {', '.join(policy_decision.reason_codes)}"],
                timeout_seconds=timeout,
            )
        if policy_decision.action == "require_approval":
            return PermissionDecision(
                allowed=False,
                risk_level=assessment.risk_level,
                requires_approval=True,
                reasons=reasons
                + [f"policy requires approval: {', '.join(policy_decision.reason_codes)}"],
                matched_patterns=assessment.matched_patterns,
                timeout_seconds=timeout,
                suggested_safe_alternative=assessment.suggested_safe_alternative,
            )

        if not self.network_allowed and re.search(r"\b(curl|wget|scp|sftp|ftp|Invoke-WebRequest)\b", cmd, re.IGNORECASE):
            return self._from_assessment(
                assessment,
                allowed=False,
                reasons=reasons + ["network commands are disabled by policy"],
                timeout_seconds=timeout,
            )

        approval_required = assessment.requires_approval
        matched = list(assessment.matched_patterns)
        for pattern in self.require_approval_patterns:
            if re.search(pattern, cmd, re.IGNORECASE):
                approval_required = True
                matched.append(pattern)
                reasons.append(f"approval pattern matched: {pattern}")

        if assessment.risk_level == "blocked":
            return self._from_assessment(
                assessment,
                allowed=False,
                reasons=reasons,
                timeout_seconds=timeout,
            )

        if assessment.risk_level == "high":
            return self._from_assessment(
                assessment,
                allowed=False,
                reasons=reasons + ["high-risk commands require explicit external approval"],
                timeout_seconds=timeout,
            )

        if approval_required and (self.non_interactive or not auto_approve):
            return PermissionDecision(
                allowed=False,
                risk_level=assessment.risk_level,
                requires_approval=True,
                reasons=reasons + ["approval-required command rejected in non-interactive mode"],
                matched_patterns=matched,
                timeout_seconds=timeout,
                suggested_safe_alternative=assessment.suggested_safe_alternative,
            )

        return PermissionDecision(
            allowed=True,
            risk_level=assessment.risk_level,
            requires_approval=approval_required,
            reasons=reasons,
            matched_patterns=matched,
            timeout_seconds=timeout,
            suggested_safe_alternative=assessment.suggested_safe_alternative,
        )

    def _inside_allowlist(self, cwd: Path) -> bool:
        for root in self.allowlist_paths:
            try:
                cwd.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _deny(
        risk_level: RiskLevel,
        requires_approval: bool,
        reasons: list[str],
        *,
        timeout_seconds: int,
        matched_patterns: list[str] | None = None,
    ) -> PermissionDecision:
        return PermissionDecision(
            allowed=False,
            risk_level=risk_level,
            requires_approval=requires_approval,
            reasons=reasons,
            matched_patterns=matched_patterns or [],
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def _from_assessment(
        assessment: RiskAssessment,
        *,
        allowed: bool,
        reasons: list[str],
        timeout_seconds: int,
    ) -> PermissionDecision:
        return PermissionDecision(
            allowed=allowed,
            risk_level=assessment.risk_level,
            requires_approval=assessment.requires_approval,
            reasons=reasons,
            matched_patterns=assessment.matched_patterns,
            timeout_seconds=timeout_seconds,
            suggested_safe_alternative=assessment.suggested_safe_alternative,
        )

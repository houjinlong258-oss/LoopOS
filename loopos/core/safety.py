"""Command risk analysis used before terminal execution."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "blocked"]


class RiskAssessment(BaseModel):
    """Risk classification for a command."""

    risk_level: RiskLevel
    requires_approval: bool
    reasons: list[str] = Field(default_factory=list)
    matched_patterns: list[str] = Field(default_factory=list)
    suggested_safe_alternative: str | None = None


class CommandRiskAnalyzer:
    """Conservative command string analyzer for the MVP."""

    blocked_patterns: tuple[tuple[str, str], ...] = (
        (r"\brm\s+-rf\s+[/\\]\s*$", "recursive deletion of filesystem root"),
        (r"\bmkfs(\.|)\w*\b", "disk formatting"),
        (r"\bdd\s+if=", "raw disk copy"),
        (r"\bcurl\b.*\|\s*(bash|sh)\b", "downloaded script execution"),
        (r"\bwget\b.*\|\s*(bash|sh)\b", "downloaded script execution"),
        (r"\bsudo\b", "privileged execution"),
        (r"\bkill\s+-9\s+-1\b", "broad process kill"),
        (r"\bgit\s+config\s+--global\b", "global git configuration change"),
        (r"(\.ssh[/\\]id_rsa|\.ssh[/\\]id_ed25519)", "private key access"),
    )
    high_patterns: tuple[tuple[str, str], ...] = (
        (r"\brm\s+-rf\b", "recursive deletion"),
        (r"\bchmod\b.*(-R|/s)\b", "recursive permission change"),
        (r"\bchmod\b.*777\b", "world-writable permission change"),
        (r"\bgit\s+reset\s+--hard\b", "hard reset"),
        (r"\bgit\s+clean\s+-f", "git clean deletion"),
        (r"\bdocker\b.*--privileged\b", "privileged container"),
        (r"\b(curl|wget|scp|sftp)\b.*(-T|--upload-file|put)\b", "network upload"),
    )
    medium_patterns: tuple[tuple[str, str], ...] = (
        (r">\s*\S+", "shell redirection write"),
        (r"\b(Set-Content|Out-File|New-Item|Copy-Item|Move-Item)\b", "filesystem write"),
        (r"\b(git\s+commit|git\s+tag)\b", "git history mutation"),
        (r"\b(pip|uv|poetry|npm|pnpm|yarn|cargo)\b\s+(install|add|update)", "dependency change"),
        (r"\bpytest\b.*(--network|--live)", "test execution with network"),
    )
    low_patterns: tuple[tuple[str, str], ...] = (
        (r"\b(ls|dir|Get-ChildItem)\b", "directory listing"),
        (r"\b(cat|type|Get-Content)\b", "file read"),
        (r"\b(rg|grep|Select-String)\b", "text search"),
        (r"\bgit\s+status\b", "git status"),
        (r"\bpytest\b", "test execution"),
        (r"\becho\b", "echo"),
    )

    def analyze(self, cmd: str) -> RiskAssessment:
        normalized = " ".join(cmd.strip().split())
        lowered = normalized.lower()
        if not normalized:
            return RiskAssessment(
                risk_level="blocked",
                requires_approval=True,
                reasons=["empty command"],
                suggested_safe_alternative="Provide an explicit command.",
            )

        blocked = self._matches(lowered, self.blocked_patterns)
        if blocked:
            return RiskAssessment(
                risk_level="blocked",
                requires_approval=True,
                reasons=[reason for _, reason in blocked],
                matched_patterns=[pattern for pattern, _ in blocked],
                suggested_safe_alternative="Use a narrower, non-destructive command.",
            )

        high = self._matches(lowered, self.high_patterns)
        if high:
            return RiskAssessment(
                risk_level="high",
                requires_approval=True,
                reasons=[reason for _, reason in high],
                matched_patterns=[pattern for pattern, _ in high],
                suggested_safe_alternative="Review the command manually and use a safer scoped operation.",
            )

        medium = self._matches(lowered, self.medium_patterns)
        if medium:
            return RiskAssessment(
                risk_level="medium",
                requires_approval=False,
                reasons=[reason for _, reason in medium],
                matched_patterns=[pattern for pattern, _ in medium],
            )

        low = self._matches(lowered, self.low_patterns)
        return RiskAssessment(
            risk_level="low",
            requires_approval=False,
            reasons=[reason for _, reason in low] or ["no risky pattern matched"],
            matched_patterns=[pattern for pattern, _ in low],
        )

    @staticmethod
    def _matches(command: str, patterns: tuple[tuple[str, str], ...]) -> list[tuple[str, str]]:
        return [(pattern, reason) for pattern, reason in patterns if re.search(pattern, command)]

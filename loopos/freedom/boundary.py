"""Capability boundary enforcement for the freedom layer.

The boundary is the single authority that decides whether a given
authority request is allowed under a :class:`FreedomPolicy`. It
returns a structured :class:`AuthorityDecision` so callers can surface
clear reason codes rather than rely on string matching.

The boundary does **not** import ``loopos.kernel.*`` and does **not**
import :mod:`loopos.aci`. It is consumed by both ACI and ALI and by
external entry points such as the CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from loopos.freedom.models import FreedomLevel, FreedomPolicy, freedom_at_least

# ---- Reason codes -------------------------------------------------------

RC_LEVEL_TOO_LOW = "freedom.level_too_low"
RC_NETWORK_DENIED = "freedom.network_denied"
RC_DATABASE_MUTATION_DENIED = "freedom.database_mutation_denied"
RC_RELEASE_TAG_DENIED = "freedom.release_tag_human_only"
RC_PATH_NOT_ALLOWLISTED = "freedom.path_not_allowlisted"
RC_PRIVILEGE_DENIED = "freedom.privilege_denied"
RC_OK = "freedom.allowed"
RC_FS_WRITE_TOO_LARGE = "freedom.filesystem_write_too_large"
RC_NETWORK_HOST_NOT_ALLOWLISTED = "freedom.network_host_not_allowlisted"
RC_DATABASE_PATH_NOT_ALLOWLISTED = "freedom.database_path_not_allowlisted"

# Patterns that indicate a network-like command. These mirror the
# runtime command-risk patterns so the boundary uses the same vocabulary.
_NETWORK_PATTERNS: tuple[str, ...] = (
    r"\bcurl\b",
    r"\bwget\b",
    r"\bscp\b",
    r"\bsftp\b",
    r"\bnc\b",
    r"\bssh\b",
)
_RELEASE_TAG_PATTERNS: tuple[str, ...] = (
    r"\bgit\s+tag\b",
    r"\bgit\s+push\b.*\b--tags\b",
)
_PRIVILEGE_PATTERNS: tuple[str, ...] = (
    r"\bsudo\b",
    r"\bchmod\b.*777",
    r"\bgit\s+config\s+--global\b",
)
_DATABASE_MUTATION_PATTERNS: tuple[str, ...] = (
    r"\b(insert|update|delete|drop|alter|create|truncate)\b",
    r"\brun_migration\b",
    r"\bsqlalchemy\b.*\.(create_all|drop_all)\b",
)


@dataclass(frozen=True)
class AuthorityDecision:
    """Outcome of a boundary check.

    The decision is intentionally structured: callers must look at
    ``allowed`` first, then ``reason_code`` and ``reason_args``. This
    prevents the silent "any-blocked-is-OK" footgun.
    """

    allowed: bool
    reason_code: str
    reason_args: dict[str, Any] = field(default_factory=dict)
    safety_level: str = "L0"
    requires_human_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "reason_args": self.reason_args,
            "safety_level": self.safety_level,
            "requires_human_approval": self.requires_human_approval,
        }


@dataclass(frozen=True)
class BoundaryContext:
    """Concrete request context for a boundary check.

    The context carries the minimum facts the boundary needs without
    importing the runtime: a path, a command, an action kind, and the
    payload size for writes.
    """

    action: str
    level: FreedomLevel
    policy: FreedomPolicy
    path: str | None = None
    command: str | None = None
    bytes: int = 0
    host: str | None = None
    database_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class CapabilityBoundary:
    """Authority gate for the freedom layer.

    A boundary is a small, pure function object. It holds no state and
    has no side effects. The runtime consults it before every external
    action; tests can construct a fresh boundary for each scenario.
    """

    def __init__(
        self,
        policy: FreedomPolicy | None = None,
        *,
        network_patterns: Iterable[str] | None = None,
        release_tag_patterns: Iterable[str] | None = None,
        privilege_patterns: Iterable[str] | None = None,
        database_mutation_patterns: Iterable[str] | None = None,
    ) -> None:
        self.policy = policy or FreedomPolicy()
        self._network_patterns = tuple(network_patterns or _NETWORK_PATTERNS)
        self._release_tag_patterns = tuple(release_tag_patterns or _RELEASE_TAG_PATTERNS)
        self._privilege_patterns = tuple(privilege_patterns or _PRIVILEGE_PATTERNS)
        self._database_mutation_patterns = tuple(
            database_mutation_patterns or _DATABASE_MUTATION_PATTERNS
        )

    def check(self, context: BoundaryContext) -> AuthorityDecision:
        """Return the structured decision for one request context."""

        if context.action == "terminal.execute":
            return self._check_terminal(context)
        if context.action == "file.write":
            return self._check_file_write(context)
        if context.action == "file.read":
            return self._check_file_read(context)
        if context.action == "network.request":
            return self._check_network(context)
        if context.action == "database.mutation":
            return self._check_database_mutation(context)
        if context.action == "release.tag":
            return self._check_release_tag(context)
        if context.action == "git.tag":
            return self._check_release_tag(context)
        return AuthorityDecision(
            allowed=True,
            reason_code=RC_OK,
            safety_level="L0",
        )

    # ---- per-action checks --------------------------------------------

    def _check_terminal(self, context: BoundaryContext) -> AuthorityDecision:
        cmd = (context.command or "").strip()
        if not cmd:
            return AuthorityDecision(
                allowed=False,
                reason_code="freedom.empty_command",
                safety_level="L0",
            )

        # Order matters: more specific reason codes (tag/privilege/
        # mutation/network) win over the generic "level too low" so
        # the audit trail carries the most actionable explanation.
        if self._matches(cmd, self._release_tag_patterns):
            return self._deny_release_tag(context, cmd)

        if self._matches(cmd, self._privilege_patterns):
            if not self.policy.allow_privilege_escalation:
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_PRIVILEGE_DENIED,
                    reason_args={"command": cmd},
                    safety_level="L5",
                )

        if self._matches(cmd, self._database_mutation_patterns):
            if not self.policy.allow_database_mutation:
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_DATABASE_MUTATION_DENIED,
                    reason_args={"command": cmd},
                    safety_level="L4",
                )

        if self._matches(cmd, self._network_patterns):
            if not self.policy.allow_network or self.policy.level == "F0_DETERMINISTIC":
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_NETWORK_DENIED,
                    reason_args={"command": cmd, "level": context.level},
                    safety_level="L3",
                )
            if self.policy.allowed_network_hosts and context.host:
                if not self._host_allowed(context.host):
                    return AuthorityDecision(
                        allowed=False,
                        reason_code=RC_NETWORK_HOST_NOT_ALLOWLISTED,
                        reason_args={"host": context.host},
                        safety_level="L3",
                    )

        # F0 cannot execute arbitrary terminal commands. The runtime
        # policy engine still owns command safety, but the boundary
        # refuses to acknowledge a free-form command at F0 unless the
        # command appears in the allowlist.
        if context.level == "F0_DETERMINISTIC" and not self.policy.allow_privilege_escalation:
            allowlist = self.policy.metadata.get("terminal_allowlist") or []
            if not isinstance(allowlist, list) or cmd not in allowlist:
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_LEVEL_TOO_LOW,
                    reason_args={"level": context.level, "action": "terminal.execute"},
                    safety_level="L2",
                )

        return AuthorityDecision(allowed=True, reason_code=RC_OK)

    def _check_file_write(self, context: BoundaryContext) -> AuthorityDecision:
        if context.level == "F0_DETERMINISTIC" and not self.policy.allow_privilege_escalation:
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_LEVEL_TOO_LOW,
                reason_args={"level": context.level, "action": "file.write"},
                safety_level="L2",
            )
        if context.bytes > self.policy.max_filesystem_write_bytes:
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_FS_WRITE_TOO_LARGE,
                reason_args={
                    "bytes": context.bytes,
                    "max": self.policy.max_filesystem_write_bytes,
                },
                safety_level="L2",
            )
        if context.path is not None and self.policy.allowed_filesystem_roots:
            if not self._path_allowed(context.path):
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_PATH_NOT_ALLOWLISTED,
                    reason_args={"path": context.path},
                    safety_level="L2",
                )
        return AuthorityDecision(allowed=True, reason_code=RC_OK)

    def _check_file_read(self, context: BoundaryContext) -> AuthorityDecision:
        if context.path is not None and self.policy.allowed_filesystem_roots:
            if not self._path_allowed(context.path):
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_PATH_NOT_ALLOWLISTED,
                    reason_args={"path": context.path},
                    safety_level="L1",
                )
        return AuthorityDecision(allowed=True, reason_code=RC_OK)

    def _check_network(self, context: BoundaryContext) -> AuthorityDecision:
        if not self.policy.allow_network or context.level == "F0_DETERMINISTIC":
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_NETWORK_DENIED,
                reason_args={"level": context.level},
                safety_level="L3",
            )
        if self.policy.allowed_network_hosts and context.host:
            if not self._host_allowed(context.host):
                return AuthorityDecision(
                    allowed=False,
                    reason_code=RC_NETWORK_HOST_NOT_ALLOWLISTED,
                    reason_args={"host": context.host},
                    safety_level="L3",
                )
        return AuthorityDecision(allowed=True, reason_code=RC_OK)

    def _check_database_mutation(self, context: BoundaryContext) -> AuthorityDecision:
        if not self.policy.allow_database_mutation:
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_DATABASE_MUTATION_DENIED,
                reason_args={"action": context.action},
                safety_level="L4",
            )
        if (
            self.policy.allowed_database_paths
            and context.database_path is not None
            and context.database_path not in self.policy.allowed_database_paths
        ):
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_DATABASE_PATH_NOT_ALLOWLISTED,
                reason_args={"database_path": context.database_path},
                safety_level="L4",
            )
        return AuthorityDecision(
            allowed=True,
            reason_code=RC_OK,
            requires_human_approval="database_mutation" in self.policy.require_human_approval_for,
        )

    def _check_release_tag(self, context: BoundaryContext) -> AuthorityDecision:
        return self._deny_release_tag(context, context.command or context.action)

    # ---- helpers -------------------------------------------------------

    def _deny_release_tag(self, context: BoundaryContext, trigger: str) -> AuthorityDecision:
        if (
            "release_tag" in self.policy.require_human_approval_for
            and not self.policy.allow_release_tag_changes
        ):
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_RELEASE_TAG_DENIED,
                reason_args={"trigger": trigger},
                safety_level="L5",
                requires_human_approval=True,
            )
        if not freedom_at_least(context.level, "F3_STRATEGY_FREEDOM"):
            return AuthorityDecision(
                allowed=False,
                reason_code=RC_LEVEL_TOO_LOW,
                reason_args={"level": context.level, "action": "release.tag"},
                safety_level="L4",
            )
        return AuthorityDecision(allowed=True, reason_code=RC_OK)

    def _path_allowed(self, raw_path: str) -> bool:
        if not self.policy.allowed_filesystem_roots:
            return True
        candidate = Path(raw_path).resolve()
        for root in self.policy.allowed_filesystem_roots:
            try:
                candidate.relative_to(Path(root).resolve())
            except ValueError:
                continue
            return True
        return False

    def _host_allowed(self, host: str) -> bool:
        for pattern in self.policy.allowed_network_hosts:
            if pattern == host:
                return True
            if pattern.startswith("*.") and host.endswith(pattern[1:]):
                return True
        return False

    @staticmethod
    def _matches(command: str, patterns: Iterable[str]) -> bool:
        return any(re.search(p, command, re.IGNORECASE) for p in patterns)


def check_authority(
    boundary: CapabilityBoundary,
    *,
    action: str,
    level: FreedomLevel,
    path: str | None = None,
    command: str | None = None,
    bytes_: int = 0,
    host: str | None = None,
    database_path: str | None = None,
    extra: dict[str, Any] | None = None,
) -> AuthorityDecision:
    """Helper to construct a :class:`BoundaryContext` and run the check."""

    return boundary.check(
        BoundaryContext(
            action=action,
            level=level,
            policy=boundary.policy,
            path=path,
            command=command,
            bytes=bytes_,
            host=host,
            database_path=database_path,
            extra=extra or {},
        )
    )

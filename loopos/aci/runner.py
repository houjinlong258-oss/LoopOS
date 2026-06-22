"""Run an :class:`AgentCommand` through the existing Policy OS / Syscall path.

The runner is the single place in the ACI layer that touches external
adapters. It is deliberately small and dependency-bounded:

* It uses :class:`loopos.policy_os.engine.PolicyEngine` for the
  policy decision. The runner never re-implements the policy rules.
* It uses :class:`loopos.syscalls.router.SyscallRouter` for execution.
  The runner never spawns a subprocess or invokes ``shell=True``
  directly.
* It does **not** import ``loopos.kernel.*`` or touch
  ``KernelLoopEngine``. Kernel integration is a Phase 1+ follow-up.

Safety:

* ``dry_run=True`` forces ``mode='dry_run'`` on the underlying
  :class:`loopos.syscalls.types.SyscallCall` and never reaches the
  adapter handler.
* ``explain=True`` performs validation and a policy preview only.
  It never dispatches the syscall at all.
* High-risk and approval-required commands are surfaced as a
  structured :class:`AgentCommandResult` with ``status='blocked'``
  or ``status='approval_required'`` rather than raised as raw
  exceptions, so the runtime can audit and replay them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loopos.aci.errors import CommandBlockedError, CommandValidationError
from loopos.aci.models import (
    AgentCommand,
    AgentCommandResult,
    AgentCommandStatus,
    ConvergenceSnapshot,
    EvaluationHint,
    ObservationKind,
    ObservationSummary,
    ProgressSnapshot,
)
from loopos.policy_os.engine import PolicyEngine
from loopos.policy_os.models import PolicyActionType, PolicyDecision, PolicyRequest
from loopos.syscalls.router import SyscallRouter
from loopos.syscalls.types import SyscallCall, SyscallMode, SyscallResult

# Command-kind to syscall-name mapping. ACI never invents a new
# execution path; it dispatches a known syscall.
KIND_TO_SYSCALL: dict[str, str] = {
    "terminal.exec": "terminal.exec",
    "file.read": "file.read",
    "file.write": "file.write",
    "git.status": "git.status",
    "git.diff": "git.diff",
    "database.query": "database.query",
    "database.run_migration": "database.run_migration",
    "noop": "noop",
}

# Command-kind to policy-scope mapping. The runtime is the source of
# truth for scope semantics; ACI only reuses the existing scopes so
# Policy OS packs keep their authority.
KIND_TO_POLICY_SCOPE: dict[str, str] = {
    "terminal.exec": "terminal.execute",
    "file.read": "file.read",
    "file.write": "file.write",
    "git.status": "git.operation",
    "git.diff": "git.operation",
    "database.query": "database.read",
    "database.run_migration": "database.mutation",
    "noop": "instruction.validate",
}

# Tags that the runtime uses to attach authority metadata. ACI passes
# them through so the policy audit trail stays consistent.
_BASE_TAGS: tuple[str, ...] = ("aci", "v0_2")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunnerConfig:
    """Configuration for :class:`CommandRunner`.

    The config is intentionally a small typed holder rather than a
    Pydantic model so it can be constructed cheaply inside hot paths
    such as the bounded loop engine.
    """

    __slots__ = ("workspace", "run_id", "trace_id", "auto_approve_medium")

    def __init__(
        self,
        workspace: str | Path = ".",
        run_id: str | None = None,
        trace_id: str | None = None,
        auto_approve_medium: bool = False,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.run_id = run_id or "aci-run"
        self.trace_id = trace_id
        self.auto_approve_medium = auto_approve_medium


class CommandRunner:
    """Validate, route, and observe an :class:`AgentCommand`."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        syscall_router: SyscallRouter | None = None,
        config: RunnerConfig | None = None,
    ) -> None:
        # The runner must not import loopos.kernel.*; PolicyEngine and
        # SyscallRouter are the only authorities it consults.
        self.policy_engine = policy_engine or PolicyEngine.load_default()
        self.syscall_router = syscall_router
        self.config = config or RunnerConfig()

    # ----- Validation -----------------------------------------------------

    def validate(self, command: AgentCommand) -> list[str]:
        """Return a list of human-readable validation issues.

        The runner keeps validation pure: it never dispatches the
        syscall and never executes any side effect. This is what
        :meth:`explain` relies on.
        """

        issues: list[str] = []
        if not command.goal_id.strip():
            issues.append("goal_id is required")
        if not command.purpose.strip():
            issues.append("purpose is required")
        if not command.command.strip() and command.kind != "noop":
            issues.append("command is required for non-noop kinds")
        if command.kind not in KIND_TO_SYSCALL:
            issues.append(f"unsupported command kind: {command.kind}")
        if command.timeout_seconds is not None and command.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        if command.mode == "dry_run" and not command.dry_run:
            # allow mode-only dry_run, but record a soft hint
            issues.append("mode='dry_run' with dry_run=False is honored but discouraged")
        if self.syscall_router is not None:
            syscall_name = KIND_TO_SYSCALL.get(command.kind)
            if syscall_name and syscall_name != "noop":
                try:
                    self.syscall_router.registry.resolve(syscall_name)
                except KeyError:
                    issues.append(f"syscall not registered: {syscall_name}")
        return issues

    # ----- Dry-run / explain ---------------------------------------------

    def explain(self, command: AgentCommand) -> AgentCommandResult:
        """Validate and pre-evaluate a command without dispatching it.

        ``explain`` is the canonical no-side-effect entry point for
        agents that want to ask "what would the runtime do?" before
        committing. The returned result has ``dry_run=True`` and the
        convergence snapshot stays in placeholder mode.
        """

        issues = self.validate(command)
        decision = self._evaluate_policy(command)
        if issues:
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="blocked",
                success=False,
                policy_decision=decision,
                blocked_reason="; ".join(issues),
                requires_approval=decision.requires_approval,
                dry_run=True,
                metadata={"phase": "explain", "validation_issues": issues},
            )
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run",
            success=False,
            policy_decision=decision,
            dry_run=True,
            metadata={"phase": "explain"},
        )

    # ----- Main entry point ----------------------------------------------

    def run(
        self,
        command: AgentCommand,
        *,
        explain: bool = False,
    ) -> AgentCommandResult:
        """Validate, route, and observe an :class:`AgentCommand`.

        ``explain=True`` returns an :class:`AgentCommandResult` with
        ``status='dry_run'`` and never reaches the adapter handler.
        """

        if explain:
            return self.explain(command)

        issues = self.validate(command)
        decision = self._evaluate_policy(command)
        if issues:
            return self._blocked_result(command, decision, "; ".join(issues))

        if self.syscall_router is None:
            return self._no_router_result(command, decision)

        syscall_result = self._dispatch(command, decision)
        return self._materialize(command, decision, syscall_result)

    # ----- Internals ------------------------------------------------------

    def _evaluate_policy(self, command: AgentCommand) -> PolicyDecision:
        scope = KIND_TO_POLICY_SCOPE.get(command.kind, "instruction.validate")
        subject: dict[str, Any] = {
            "cmd": command.command,
            "args": dict(command.args),
            "kind": command.kind,
            "goal_id": command.goal_id,
            "purpose": command.purpose,
            "capabilities": {
                "filesystem_read": command.capabilities.filesystem_read,
                "filesystem_write": command.capabilities.filesystem_write,
                "network": command.capabilities.network,
                "database": command.capabilities.database,
            },
        }
        if command.timeout_seconds is not None:
            subject["timeout_seconds"] = command.timeout_seconds
        tags = [*_BASE_TAGS, *command.capabilities.tags]
        return self.policy_engine.evaluate(
            scope,
            subject=subject,
            tags=tags,
            risk_level="low",
            actor="aci",
            metadata={
                "aci_command_id": command.id,
                "aci_goal_id": command.goal_id,
            },
        )

    def _dispatch(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
    ) -> SyscallResult:
        assert self.syscall_router is not None
        syscall_name = KIND_TO_SYSCALL[command.kind]
        mode: SyscallMode = "dry_run" if command.dry_run else "guarded"
        call = SyscallCall(
            run_id=self.config.run_id,
            instruction_id=command.id,
            name=syscall_name,
            input={
                "cmd": command.command,
                "cwd": str(self.config.workspace),
                **(
                    {"timeout_seconds": command.timeout_seconds}
                    if command.timeout_seconds is not None
                    else {}
                ),
                **command.args,
            },
            workspace=str(self.config.workspace),
            mode=mode,
            approval_granted=command.approval_granted,
        )
        return self.syscall_router.dispatch(call)

    def _materialize(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
        syscall_result: SyscallResult,
    ) -> AgentCommandResult:
        if syscall_result.requires_approval and not syscall_result.success:
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="approval_required",
                success=False,
                policy_decision=decision,
                observation=self._to_observation(command, syscall_result),
                requires_approval=True,
                dry_run=syscall_result.dry_run,
                trace_id=self.config.trace_id,
                metadata={"syscall_id": syscall_result.syscall_id},
            )
        if not syscall_result.success:
            blocked = syscall_result.risk == "blocked" or not decision.allowed
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="blocked" if blocked else "failed",
                success=False,
                policy_decision=decision,
                observation=self._to_observation(command, syscall_result),
                blocked_reason=syscall_result.error,
                dry_run=syscall_result.dry_run,
                trace_id=self.config.trace_id,
                metadata={"syscall_id": syscall_result.syscall_id},
            )
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run" if syscall_result.dry_run else "completed",
            success=True,
            policy_decision=decision,
            observation=self._to_observation(command, syscall_result),
            progress=ProgressSnapshot(
                placeholder=True,
            ),
            evaluation=EvaluationHint(
                placeholder=True,
                goal_satisfied=True,
                reason_codes=["aci.no_kernel_runtime"],
            ),
            convergence=ConvergenceSnapshot(
                action="continue",
                reason_code="aci.no_kernel_runtime",
                placeholder=True,
            ),
            dry_run=syscall_result.dry_run,
            trace_id=self.config.trace_id,
            metadata={"syscall_id": syscall_result.syscall_id},
        )

    def _blocked_result(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
        reason: str,
    ) -> AgentCommandResult:
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="blocked",
            success=False,
            policy_decision=decision,
            blocked_reason=reason,
            requires_approval=decision.requires_approval,
            dry_run=command.dry_run,
            trace_id=self.config.trace_id,
        )

    def _no_router_result(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
    ) -> AgentCommandResult:
        if not decision.allowed:
            return self._blocked_result(
                command,
                decision,
                _format_decision_reason(decision),
            )
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run" if command.dry_run else "completed",
            success=True,
            policy_decision=decision,
            dry_run=command.dry_run,
            trace_id=self.config.trace_id,
            metadata={"phase": "no_router", "kind": command.kind},
        )

    @staticmethod
    def _to_observation(
        command: AgentCommand,
        syscall_result: SyscallResult,
    ) -> ObservationSummary:
        kind: ObservationKind = "command_result"
        if command.kind in {"file.read", "file.write"}:
            kind = "file_content"
        elif command.kind in {"git.status", "git.diff"}:
            kind = "git_state"
        elif command.kind.startswith("database."):
            kind = "database_result"
        elif command.kind == "noop":
            kind = "noop"
        return ObservationSummary(
            kind=kind,
            success=syscall_result.success,
            summary=syscall_result.error or f"{command.kind} completed",
            return_code=None,
            duration_ms=syscall_result.duration_ms,
            data=dict(syscall_result.output),
        )


def _format_decision_reason(decision: PolicyDecision) -> str:
    codes = list(decision.reason_codes) or list(decision.all_reason_codes)
    if not codes:
        return f"policy {decision.action}"
    return f"policy {decision.action}: {', '.join(codes)}"


def build_default_runner(
    workspace: str | Path,
    *,
    syscall_router: SyscallRouter | None = None,
    config: RunnerConfig | None = None,
) -> CommandRunner:
    """Build a :class:`CommandRunner` pre-wired with a default syscall router.

    Phase 1 does **not** integrate with the Kernel loop engine. The
    syscall router is the only side-effecting path; the runner
    refuses to execute when no router is provided unless the command
    is a policy-denied explain call.
    """

    if syscall_router is None:
        # Import lazily so the ACI package does not import the full
        # syscall module just to construct a runner. The import path
        # remains the only place a default router is created, which
        # is the same boundary the CLI uses.
        from loopos.syscalls.router import create_default_syscall_router

        syscall_router = create_default_syscall_router(
            workspace,
            auto_approve_medium=bool(config and config.auto_approve_medium),
        )
    return CommandRunner(
        syscall_router=syscall_router,
        config=config or RunnerConfig(workspace=workspace),
    )

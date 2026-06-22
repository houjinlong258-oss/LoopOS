"""Run an :class:`AgentCommand` through the existing Policy OS / Syscall path.

The runner is the single place in the ACI layer that touches external
adapters. It is deliberately small and dependency-bounded:

* It uses :class:`loopos.policy_os.engine.PolicyEngine` for the
  policy decision. The runner never re-implements the policy rules.
* It uses :class:`loopos.syscalls.router.SyscallRouter` for execution.
  The runner never spawns a subprocess or invokes ``shell=True``
  directly.
* It uses :class:`loopos.providers.ProviderRegistry` for metadata-only
  provider resolution. The runner never calls a live provider API.
* It does **not** import ``loopos.kernel.*`` or touch
  ``KernelLoopEngine``. Kernel integration is a Phase 1+ follow-up.

Safety:

* ``dry_run=True`` forces ``mode='dry_run'`` on the underlying
  :class:`loopos.syscalls.types.SyscallCall` and never reaches the
  adapter handler.
* ``explain=True`` performs validation and a policy preview only.
  It never dispatches the syscall at all.
* ``kind='provider_select'`` is metadata-only: the runner resolves
  a :class:`ProviderHint` against the registry, populates
  :class:`ResolvedProvider`, and never dispatches a syscall.
* ``kind='explain_only'`` is equivalent to ``explain=True``: validate
  and preview, no execution.
* Unknown ``kind`` values return ``status='unsupported'`` and never
  reach the policy or syscall layer.
* High-risk and approval-required commands are surfaced as a
  structured :class:`AgentCommandResult` with ``status='blocked'``
  or ``status='approval_required'`` rather than raised as raw
  exceptions, so the runtime can audit and replay them.

Maintainability note (Phase 3.x):

Two helper groups have been split into focused internal modules so
the runner stays focused on dispatch:

* :mod:`loopos.aci.provider_binding` owns the metadata-only
  :class:`ProviderHint` resolution. The runner imports
  ``_resolve_provider_hint`` from there.
* :mod:`loopos.aci.result_builders` owns the small pure helpers
  that extract structured data from a :class:`PolicyDecision`.
  The runner imports ``_format_decision_reason`` and
  ``_policy_reason_code`` from there.

The public surface of this module (``CommandRunner``,
``RunnerConfig``, ``KIND_TO_POLICY_SCOPE``, ``KIND_TO_SYSCALL``,
``build_default_runner``) is unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loopos.aci.errors import (
    ProviderResolutionError,
)
from loopos.aci.models import (
    AgentCommand,
    AgentCommandResult,
    EvaluationSummary,
    ObservationKind,
    ObservationSummary,
    ProgressSummary,
    ProviderHint,
    REASON_DRY_RUN_NO_SIDE_EFFECT,
    REASON_INVALID_COMMAND,
    REASON_NO_KERNEL_RUNTIME,
    REASON_POLICY_DENIED,
    REASON_POLICY_REQUIRES_APPROVAL,
    REASON_PROVIDER_NOT_FOUND,
    REASON_SYSCALL_FAILED,
    REASON_UNSUPPORTED_COMMAND_KIND,
    ResolvedProvider,
    SyscallSummary,
)
from loopos.aci.provider_binding import _resolve_provider_hint
from loopos.aci.result_builders import _format_decision_reason, _policy_reason_code
from loopos.aci.result_models import (
    ConvergenceSummary,
)
from loopos.policy_os.engine import PolicyEngine
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.router import SyscallRouter
from loopos.syscalls.types import SyscallCall, SyscallMode, SyscallResult

# ---------------------------------------------------------------------------
# Kind -> syscall-name mapping
# ---------------------------------------------------------------------------

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

# Kinds handled without a syscall dispatch (metadata or explain-only).
_METADATA_KINDS: frozenset[str] = frozenset({"provider_select"})
_EXPLAIN_ONLY_KINDS: frozenset[str] = frozenset({"explain_only"})

# Command-kind to policy-scope mapping. The runtime is the source of
# truth for scope semantics; ACI only reuses the existing scopes so
# Policy OS packs keep their authority.
KIND_TO_POLICY_SCOPE: dict[str, str] = {
    "terminal.exec": "terminal.execute",
    "file.read": "file.read",
    "file.write": "file.write",
    "file.patch": "file.write",
    "git.status": "git.operation",
    "git.diff": "git.operation",
    "git.commit": "git.operation",
    "database.query": "database.read",
    "database.run_migration": "database.mutation",
    "provider_select": "instruction.validate",
    "explain_only": "instruction.validate",
    "noop": "instruction.validate",
}

# Tags that the runtime uses to attach authority metadata. ACI passes
# them through so the policy audit trail stays consistent.
_BASE_TAGS: tuple[str, ...] = ("aci", "v0_2")


# ---------------------------------------------------------------------------
# Configuration + Runner
# ---------------------------------------------------------------------------


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
    """Validate, route, and observe an :class:`AgentCommand`.

    The runner is the single source of truth for the ACI
    validate / explain / run surface. It does not own the policy
    engine, syscall router, or provider registry; callers inject
    them. The runner also does not import ``loopos.kernel.*``.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        syscall_router: SyscallRouter | None = None,
        provider_registry: "Any | None" = None,
        config: RunnerConfig | None = None,
    ) -> None:
        self.policy_engine = policy_engine or PolicyEngine.load_default()
        self.syscall_router = syscall_router
        self.provider_registry = provider_registry
        self.config = config or RunnerConfig()

    # ----- Validation -----------------------------------------------------

    def validate(self, command: AgentCommand) -> list[str]:
        """Return a list of human-readable validation issues.

        Validation is structural: it checks required fields, command
        shape, and provider_hint requirements. It does NOT check
        whether a syscall is registered for ``kind`` -- that is a
        dispatch-time concern that surfaces as
        ``status='unsupported'`` rather than as a validation error.
        """

        issues: list[str] = []
        if not command.goal_id.strip():
            issues.append("goal_id is required")
        if not command.purpose.strip():
            issues.append("purpose is required")
        if not command.command.strip() and command.kind not in (
            "noop",
            "provider_select",
            "explain_only",
        ):
            issues.append("command is required for non-noop kinds")
        if command.kind in _METADATA_KINDS and command.provider_hint is None:
            issues.append(f"{command.kind!r} requires a provider_hint")
        if command.timeout_seconds is not None and command.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        if command.mode == "dry_run" and not command.dry_run:
            # allow mode-only dry_run, but record a soft hint
            issues.append("mode='dry_run' with dry_run=False is honored but discouraged")
        return issues

    # ----- Dry-run / explain ---------------------------------------------

    def explain(self, command: AgentCommand) -> AgentCommandResult:
        """Validate and pre-evaluate a command without dispatching it.

        ``explain`` is the canonical no-side-effect entry point for
        agents that want to ask "what would the runtime do?" before
        committing. The returned result has ``dry_run=True`` and the
        convergence snapshot stays in placeholder mode.

        ``explain`` also resolves the provider hint (metadata-only)
        when one is supplied so the agent can preview which profile
        would be bound.
        """

        issues = self.validate(command)
        decision = self._evaluate_policy(command)
        resolved = self._resolve_provider_from_command(command)

        if issues:
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="blocked",
                success=False,
                resolved_provider=resolved,
                policy_decision=decision,
                blocked_reason="; ".join(issues),
                requires_approval=decision.requires_approval,
                dry_run=True,
                reason_codes=[REASON_INVALID_COMMAND],
                messages=[f"explain: validation failed: {issues}"],
                metadata={"phase": "explain", "validation_issues": issues},
            )

        # kind == "provider_select" via explain is metadata-only.
        if command.kind in _METADATA_KINDS:
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="completed",
                success=True,
                resolved_provider=resolved,
                policy_decision=decision,
                dry_run=False,
                reason_codes=[],
                messages=[f"explain: {command.kind} resolved (no syscall dispatched)"],
                metadata={"phase": "explain", "kind": command.kind},
            )

        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run",
            success=False,
            resolved_provider=resolved,
            policy_decision=decision,
            dry_run=True,
            reason_codes=[REASON_DRY_RUN_NO_SIDE_EFFECT],
            messages=["explain: dry-run preview, no syscall dispatched"],
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

        Dispatch order:

        1. ``explain=True`` or ``kind in _EXPLAIN_ONLY_KINDS`` ->
           :meth:`explain`.
        2. ``kind in _METADATA_KINDS`` -> :meth:`_run_metadata`
           (provider resolution only).
        3. Structural validation. Issues -> ``status='blocked'``.
        4. Policy evaluation.
        5. **Provider resolution (early).** When a :class:`ProviderHint`
           is supplied and the registry cannot honor it, the runner
           returns ``status='failed'`` with the stable provider
           ``reason_code`` and **never dispatches the syscall** -- the
           command's provider context could not be honored, so the
           command cannot be considered successfully executed.
        6. ``kind not in KIND_TO_SYSCALL`` -> ``status='unsupported'``
           (schema kept; execution deferred).
        7. No router configured -> policy-only verdict.
        8. Syscall dispatch and :meth:`_materialize`.
        """

        if explain or command.kind in _EXPLAIN_ONLY_KINDS:
            return self.explain(command)

        if command.kind in _METADATA_KINDS:
            return self._run_metadata(command)

        issues = self.validate(command)
        decision = self._evaluate_policy(command)
        if issues:
            return self._blocked_result(command, decision, "; ".join(issues))

        # Provider resolution happens BEFORE syscall dispatch.
        # If a hint was supplied and cannot be honored, the run fails
        # immediately -- the runner refuses to execute a command whose
        # declared provider context cannot be established.
        if command.provider_hint is not None:
            resolved_provider, provider_reason, provider_msg = (
                _resolve_provider_hint(
                    command.provider_hint, self.provider_registry,
                )
            )
            if resolved_provider is None:
                return self._provider_failed_result(
                    command, decision,
                    provider_reason or REASON_PROVIDER_NOT_FOUND,
                    provider_msg or "provider resolution failed",
                )

        if command.kind not in KIND_TO_SYSCALL:
            return self._unsupported_result(command, decision)

        syscall_name = KIND_TO_SYSCALL[command.kind]
        if self.syscall_router is None:
            return self._no_router_result(command, decision)
        try:
            self.syscall_router.registry.resolve(syscall_name)
        except KeyError:
            return self._unsupported_result(command, decision)

        syscall_result = self._dispatch(command, decision)
        return self._materialize(command, decision, syscall_result)

    # ----- Provider resolution entry points -----------------------------

    def resolve_provider(self, hint: ProviderHint) -> ResolvedProvider:
        """Resolve a :class:`ProviderHint` against the wired registry.

        Strict variant: raises :class:`ProviderResolutionError` on
        failure. Callers that prefer structured results should use
        :meth:`run` with ``kind='provider_select'``.
        """
        resolved, reason_code, message = _resolve_provider_hint(hint, self.provider_registry)
        if resolved is None:
            raise ProviderResolutionError(reason_code or REASON_PROVIDER_NOT_FOUND, message or "")
        return resolved

    # ----- Internals ------------------------------------------------------

    def _resolve_provider_from_command(
        self, command: AgentCommand,
    ) -> ResolvedProvider | None:
        if command.provider_hint is None:
            return None
        resolved, _reason_code, _message = _resolve_provider_hint(
            command.provider_hint, self.provider_registry,
        )
        return resolved

    def _evaluate_policy(self, command: AgentCommand) -> PolicyDecision:
        scope = KIND_TO_POLICY_SCOPE.get(command.kind, "instruction.validate")
        subject: dict[str, Any] = {
            "cmd": command.command,
            "args": dict(command.args),
            "kind": command.kind,
            "goal_id": command.goal_id,
            "purpose": command.purpose,
            "intent": command.intent,
            "capabilities": {
                "filesystem_read": command.capabilities.filesystem_read,
                "filesystem_write": command.capabilities.filesystem_write,
                "network": command.capabilities.network,
                "database": command.capabilities.database,
            },
        }
        if command.timeout_seconds is not None:
            subject["timeout_seconds"] = command.timeout_seconds
        if command.provider_hint is not None:
            subject["provider_hint"] = {
                "provider_id": command.provider_hint.provider_id,
                "required_capabilities": list(
                    command.provider_hint.required_capabilities
                ),
                "local_only": command.provider_hint.local_only,
                "allow_fallback": command.provider_hint.allow_fallback,
            }
        if command.risk_hint is not None:
            subject["risk_hint"] = {
                "level": command.risk_hint.level,
                "reason": command.risk_hint.reason,
                "tags": list(command.risk_hint.tags),
            }
        tags = [*_BASE_TAGS, *command.capabilities.tags]
        if command.kind in _METADATA_KINDS:
            tags.append("aci.metadata_only")
        return self.policy_engine.evaluate(
            scope,
            subject=subject,
            tags=tags,
            risk_level="low",
            actor="aci",
            metadata={
                "aci_command_id": command.id,
                "aci_goal_id": command.goal_id,
                "aci_kind": command.kind,
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

    def _run_metadata(self, command: AgentCommand) -> AgentCommandResult:
        # Pure-metadata path: resolve provider_hint, return a
        # structured result, never dispatch a syscall.
        decision = self._evaluate_policy(command)
        if not decision.allowed:
            return self._blocked_result(
                command, decision,
                _format_decision_reason(decision),
            )
        resolved, reason_code, message = _resolve_provider_hint(
            command.provider_hint, self.provider_registry,
        ) if command.provider_hint is not None else (None, None, None)
        reason_codes: list[str] = []
        messages: list[str] = []
        if resolved is None and reason_code is not None:
            reason_codes.append(reason_code)
            if message:
                messages.append(f"provider_select: {message}")
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="failed",
                success=False,
                resolved_provider=None,
                policy_decision=decision,
                dry_run=command.dry_run,
                reason_codes=reason_codes,
                messages=messages,
                blocked_reason=message,
                metadata={"phase": "provider_select", "kind": command.kind},
            )
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="completed",
            success=True,
            resolved_provider=resolved,
            policy_decision=decision,
            dry_run=command.dry_run,
            reason_codes=[],
            messages=[
                f"provider_select: resolved provider_id={resolved.provider_id if resolved else '?'}"
            ],
            metadata={"phase": "provider_select", "kind": command.kind},
        )

    def _materialize(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
        syscall_result: SyscallResult,
    ) -> AgentCommandResult:
        syscall_summary = SyscallSummary(
            name=syscall_result.name,
            syscall_id=syscall_result.syscall_id,
            risk=str(syscall_result.risk),
            requires_approval=syscall_result.requires_approval,
            side_effecting=True,  # dispatched syscalls are by definition side-effecting
            success=syscall_result.success,
            dry_run=syscall_result.dry_run,
            duration_ms=syscall_result.duration_ms,
        )
        if syscall_result.requires_approval and not syscall_result.success:
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="approval_required",
                success=False,
                resolved_provider=self._resolve_provider_from_command(command),
                policy_decision=decision,
                syscall=syscall_summary,
                observation=self._to_observation(command, syscall_result),
                requires_approval=True,
                dry_run=syscall_result.dry_run,
                trace_id=self.config.trace_id,
                reason_codes=[REASON_POLICY_REQUIRES_APPROVAL],
                messages=[f"syscall {syscall_result.name} requires approval"],
                metadata={"syscall_id": syscall_result.syscall_id},
            )
        if not syscall_result.success:
            blocked = syscall_result.risk == "blocked" or not decision.allowed
            reason_codes: list[str] = []
            if blocked:
                reason_codes.extend(
                    code for code in decision.reason_codes
                    if code.startswith("policy_") or code.startswith("terminal_")
                    or code.startswith("remote_") or code.startswith("network_")
                    or code.startswith("git_") or code.startswith("release_")
                )
                if not reason_codes:
                    reason_codes.append(REASON_POLICY_DENIED)
            else:
                reason_codes.append(REASON_SYSCALL_FAILED)
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="blocked" if blocked else "failed",
                success=False,
                resolved_provider=self._resolve_provider_from_command(command),
                policy_decision=decision,
                syscall=syscall_summary,
                observation=self._to_observation(command, syscall_result),
                blocked_reason=syscall_result.error,
                dry_run=syscall_result.dry_run,
                trace_id=self.config.trace_id,
                reason_codes=reason_codes,
                messages=[f"syscall {syscall_result.name} failed: {syscall_result.error}"],
                metadata={"syscall_id": syscall_result.syscall_id},
            )
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run" if syscall_result.dry_run else "completed",
            success=True,
            resolved_provider=self._resolve_provider_from_command(command),
            policy_decision=decision,
            syscall=syscall_summary,
            observation=self._to_observation(command, syscall_result),
            progress=ProgressSummary(),
            evaluation=EvaluationSummary(
                goal_satisfied=True,
                reason_codes=[REASON_NO_KERNEL_RUNTIME],
            ),
            convergence=ConvergenceSummary(),
            dry_run=syscall_result.dry_run,
            trace_id=self.config.trace_id,
            reason_codes=[],
            messages=[f"syscall {syscall_result.name} completed"],
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
            resolved_provider=self._resolve_provider_from_command(command),
            policy_decision=decision,
            blocked_reason=reason,
            requires_approval=decision.requires_approval,
            dry_run=command.dry_run,
            trace_id=self.config.trace_id,
            reason_codes=[_policy_reason_code(decision, REASON_POLICY_DENIED)],
            messages=[f"blocked: {reason}"],
        )

    def _unsupported_result(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
    ) -> AgentCommandResult:
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="unsupported",
            success=False,
            policy_decision=decision,
            reason_codes=[REASON_UNSUPPORTED_COMMAND_KIND],
            messages=[f"unsupported command kind: {command.kind!r}"],
            metadata={"phase": "unsupported", "kind": command.kind},
        )

    def _provider_failed_result(
        self,
        command: AgentCommand,
        decision: PolicyDecision,
        reason_code: str,
        message: str,
    ) -> AgentCommandResult:
        return AgentCommandResult(
            command_id=command.id,
            goal_id=command.goal_id,
            status="failed",
            success=False,
            resolved_provider=None,
            policy_decision=decision,
            dry_run=command.dry_run,
            reason_codes=[reason_code],
            messages=[f"provider resolution failed: {message}"],
            blocked_reason=message,
            metadata={"phase": "provider_resolution_failed"},
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
            reason_codes=[],
            messages=[f"no_router: kind={command.kind} returned policy-only verdict"],
            metadata={"phase": "no_router", "kind": command.kind},
        )

    @staticmethod
    def _to_observation(
        command: AgentCommand,
        syscall_result: SyscallResult,
    ) -> ObservationSummary:
        kind: ObservationKind = "command_result"
        if command.kind in {"file.read", "file.write", "file.patch"}:
            kind = "file_content"
        elif command.kind in {"git.status", "git.diff", "git.commit"}:
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


def build_default_runner(
    workspace: str | Path,
    *,
    syscall_router: SyscallRouter | None = None,
    provider_registry: "Any | None" = None,
    config: RunnerConfig | None = None,
) -> CommandRunner:
    """Build a :class:`CommandRunner` pre-wired with default adapters.

    Phase 2 does **not** integrate with the Kernel loop engine.
    The syscall router is the only side-effecting path; the runner
    refuses to execute when no router is provided unless the command
    is a policy-denied explain call. The provider registry is
    optional; without one the runner can still validate and route
    commands but cannot resolve ``provider_hint``s.
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
        provider_registry=provider_registry,
        config=config or RunnerConfig(workspace=workspace),
    )


__all__ = [
    "CommandRunner",
    "RunnerConfig",
    "KIND_TO_POLICY_SCOPE",
    "KIND_TO_SYSCALL",
    "build_default_runner",
]
"""Policy-governed syscall routing and built-in adapters."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from loopos.execution.permissions import PermissionPolicy
from loopos.execution.terminal import TerminalExecutor
from loopos.policy_os.engine import PolicyEngine
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.registry import SyscallRegistry
from loopos.syscalls.builtin import register_database_syscalls
from loopos.syscalls.types import SyscallCall, SyscallResult, SyscallSpec


class SyscallRouter:
    def __init__(
        self,
        registry: SyscallRegistry | None = None,
        *,
        policy_engine: PolicyEngine | None = None,
        trace_store: Any | None = None,
        auto_approve_medium: bool = False,
    ) -> None:
        self.registry = registry or SyscallRegistry()
        self.policy_engine = policy_engine or PolicyEngine.load_default()
        self.trace_store = trace_store
        self.auto_approve_medium = auto_approve_medium

    def dispatch(self, call: SyscallCall, *, step: int = 0) -> SyscallResult:
        try:
            registered = self.registry.resolve(call.name)
        except KeyError as exc:
            return self._error(call, str(exc), _default_deny("syscall.unknown"), step=step)
        spec = registered.spec
        validation_error = _validate_input(spec, call.input)
        if validation_error:
            return self._error(
                call,
                validation_error,
                _default_deny("syscall.invalid_input"),
                spec,
                step=step,
            )

        decision = self.policy_engine.evaluate(
            spec.policy_scope,
            subject={**call.input, "name": call.name, "risk_level": spec.risk},
            tags=["syscall", *spec.tags],
            risk_level=spec.risk,
            metadata={"run_id": call.run_id, "instruction_id": call.instruction_id},
        )
        self._trace_policy(call, step, decision)
        if decision.action == "deny" or spec.risk == "blocked":
            return self._error(call, "blocked by policy", decision, spec, step=step)

        if call.mode == "dry_run":
            result = SyscallResult(
                syscall_id=call.id,
                run_id=call.run_id,
                instruction_id=call.instruction_id,
                name=call.name,
                success=True,
                output={"planned": True, "input": call.input},
                risk=spec.risk,
                requires_approval=spec.requires_approval or decision.requires_approval,
                policy_decision=decision,
                dry_run=True,
            )
            self._trace_result(call, step, result)
            return result

        approval_required = spec.requires_approval or decision.requires_approval
        approved = call.approval_granted or (spec.risk == "medium" and self.auto_approve_medium)
        if approval_required and not approved:
            return self._error(
                call,
                "approval required",
                decision,
                spec,
                requires_approval=True,
                step=step,
            )
        if spec.risk == "high" and not call.approval_granted:
            return self._error(
                call,
                "explicit approval required",
                decision,
                spec,
                requires_approval=True,
                step=step,
            )

        started = time.perf_counter()
        result = registered.handler(call)
        result.policy_decision = decision
        result.risk = spec.risk
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        self._trace_result(call, step, result)
        return result

    def _error(
        self,
        call: SyscallCall,
        error: str,
        decision: PolicyDecision,
        spec: SyscallSpec | None = None,
        *,
        requires_approval: bool = False,
        step: int = 0,
    ) -> SyscallResult:
        result = SyscallResult(
            syscall_id=call.id,
            run_id=call.run_id,
            instruction_id=call.instruction_id,
            name=call.name,
            success=False,
            error=error,
            risk=spec.risk if spec else "blocked",
            requires_approval=requires_approval,
            policy_decision=decision,
        )
        self._trace_result(call, step, result)
        return result

    def _trace_policy(self, call: SyscallCall, step: int, decision: PolicyDecision) -> None:
        if self.trace_store:
            self.trace_store.append(
                "policy",
                call.run_id,
                step,
                decision.model_dump(mode="json"),
                instruction_id=call.instruction_id,
                syscall_id=call.id,
                policy_decision_id=decision.decision_id,
            )

    def _trace_result(self, call: SyscallCall, step: int, result: SyscallResult) -> None:
        if self.trace_store:
            self.trace_store.append(
                "syscall",
                call.run_id,
                step,
                result.model_dump(mode="json"),
                instruction_id=call.instruction_id,
                syscall_id=call.id,
                policy_decision_id=result.policy_decision.decision_id,
            )


def create_default_syscall_router(
    workspace: str | Path,
    *,
    data_dir: str | Path | None = None,
    policy_engine: PolicyEngine | None = None,
    trace_store: Any | None = None,
    auto_approve_medium: bool = False,
) -> SyscallRouter:
    root = Path(workspace).resolve()
    engine = policy_engine or PolicyEngine.load_default()
    registry = SyscallRegistry()
    router = SyscallRouter(
        registry,
        policy_engine=engine,
        trace_store=trace_store,
        auto_approve_medium=auto_approve_medium,
    )
    terminal = TerminalExecutor(
        default_cwd=root,
        auto_approve=auto_approve_medium,
        policy=PermissionPolicy(allowlist_paths=[root], policy_engine=engine),
    )

    def terminal_exec(call: SyscallCall) -> SyscallResult:
        cwd = _safe_path(root, str(call.input.get("cwd", ".")))
        if cwd is None or not cwd.is_dir():
            return _handler_result(call, False, {}, "cwd is outside workspace")
        observation = terminal.execute(
            str(call.input.get("cmd", "")),
            cwd=cwd,
            timeout_seconds=_optional_int(call.input.get("timeout_seconds")),
        )
        return _handler_result(
            call,
            observation.success,
            observation.model_dump(mode="json"),
            observation.error,
        )

    def file_read(call: SyscallCall) -> SyscallResult:
        path = _safe_path(root, call.input.get("path"))
        if path is None:
            return _handler_result(call, False, {}, "path is outside workspace")
        if not path.is_file():
            return _handler_result(call, False, {}, f"file not found: {path}")
        return _handler_result(call, True, {"path": str(path), "content": path.read_text(encoding="utf-8")})

    def file_write(call: SyscallCall) -> SyscallResult:
        path = _safe_path(root, call.input.get("path"))
        if path is None:
            return _handler_result(call, False, {}, "path is outside workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(call.input.get("content", "")), encoding="utf-8")
        return _handler_result(call, True, {"path": str(path)})

    def git_status(call: SyscallCall) -> SyscallResult:
        return _git_result(call, root, ["status", "--short"])

    def git_diff(call: SyscallCall) -> SyscallResult:
        return _git_result(call, root, ["diff", "--", "."])

    specs = [
        (SyscallSpec(name="terminal.exec", description="Execute a guarded command.", input_schema={"required": ["cmd"]}, risk="medium", policy_scope="terminal.execute", tags=["terminal"]), terminal_exec),
        (SyscallSpec(name="file.read", description="Read a workspace file.", input_schema={"required": ["path"]}, policy_scope="file.read", tags=["file"]), file_read),
        (SyscallSpec(name="file.write", description="Write a workspace file.", input_schema={"required": ["path", "content"]}, risk="medium", requires_approval=True, side_effecting=True, policy_scope="file.write", tags=["file"]), file_write),
        (SyscallSpec(name="git.status", description="Read Git status.", policy_scope="git.operation", tags=["git"]), git_status),
        (SyscallSpec(name="git.diff", description="Read Git diff.", policy_scope="git.operation", tags=["git"]), git_diff),
    ]
    for spec, handler in specs:
        registry.register(spec, handler)
    register_database_syscalls(registry, workspace=root, data_dir=data_dir)
    return router


def _handler_result(call: SyscallCall, success: bool, output: dict[str, Any], error: str | None = None) -> SyscallResult:
    return SyscallResult(
        syscall_id=call.id,
        run_id=call.run_id,
        instruction_id=call.instruction_id,
        name=call.name,
        success=success,
        output=output,
        error=error,
        policy_decision=PolicyDecision(allowed=True, action="allow"),
    )


def _git_result(call: SyscallCall, root: Path, args: list[str]) -> SyscallResult:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10
    )
    return _handler_result(
        call,
        completed.returncode == 0,
        {"stdout": completed.stdout, "stderr": completed.stderr},
        None if completed.returncode == 0 else completed.stderr,
    )


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def _validate_input(spec: SyscallSpec, payload: dict[str, Any]) -> str | None:
    required = spec.input_schema.get("required", [])
    if not isinstance(required, list):
        return "invalid syscall schema"
    missing = [str(key) for key in required if key not in payload]
    return f"missing required input: {', '.join(missing)}" if missing else None


def _default_deny(reason: str) -> PolicyDecision:
    return PolicyDecision(allowed=False, action="deny", risk="blocked", reason_codes=[reason])


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None

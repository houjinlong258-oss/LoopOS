"""MCP-like compatibility router backed by Kernel syscalls."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from loopos.execution.terminal import TerminalExecutor
from loopos.mcp.types import RegisteredTool, ToolCall, ToolRegistry, ToolResult, ToolSpec
from loopos.policy_os.engine import PolicyEngine
from loopos.syscalls import SyscallCall, SyscallRouter, create_default_syscall_router


class ToolRouter:
    """Resolve custom MCP-like tools while retaining Policy OS checks."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        auto_approve: bool = False,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.auto_approve = auto_approve
        self.policy_engine = policy_engine or PolicyEngine.load_default()

    def register(self, spec: ToolSpec, handler: Callable[[ToolCall], ToolResult]) -> None:
        self.registry.register(spec, handler)

    def list_tools(self) -> list[ToolSpec]:
        return self.registry.list_tools()

    def resolve(self, name: str) -> RegisteredTool:
        return self.registry.resolve(name)

    def call(self, tool_call: ToolCall) -> ToolResult:
        try:
            registered = self.registry.resolve(tool_call.name)
        except KeyError as exc:
            return ToolResult(success=False, name=tool_call.name, error=str(exc), risk_level="blocked")

        spec = registered.spec
        policy_decision = self.policy_engine.evaluate(
            "tool.call",
            subject={
                "name": tool_call.name,
                "args": tool_call.args,
                "risk_level": spec.risk_level,
                "requires_approval": spec.requires_approval,
                "tags": spec.tags,
            },
            tags=["tool", *spec.tags],
            risk_level=spec.risk_level,
        )
        medium_approved = (
            policy_decision.requires_approval
            and self.auto_approve
            and spec.risk_level == "medium"
        )
        if not policy_decision.allowed and not medium_approved:
            return ToolResult(
                success=False,
                name=tool_call.name,
                error=f"policy {policy_decision.action}: {', '.join(policy_decision.reason_codes)}",
                risk_level=spec.risk_level,
                requires_approval=policy_decision.requires_approval,
            )
        if spec.risk_level in {"high", "blocked"} and not self.auto_approve:
            return ToolResult(
                success=False,
                name=tool_call.name,
                error="tool requires approval",
                risk_level=spec.risk_level,
                requires_approval=True,
            )
        result = registered.handler(tool_call)
        result.risk_level = spec.risk_level
        result.requires_approval = spec.requires_approval
        result.output.setdefault("policy", policy_decision.model_dump(mode="json"))
        return result


def create_default_router(
    *,
    workspace: str | Path = ".",
    terminal: TerminalExecutor | None = None,
    auto_approve: bool = False,
    policy_engine: PolicyEngine | None = None,
) -> ToolRouter:
    """Create the legacy tool facade over the canonical syscall router."""

    del terminal  # Terminal execution is owned by the syscall adapter.
    engine = policy_engine or PolicyEngine.load_default()
    syscalls = create_default_syscall_router(
        workspace,
        policy_engine=engine,
        auto_approve_medium=auto_approve,
    )
    router = ToolRouter(auto_approve=auto_approve, policy_engine=engine)

    for syscall_spec in syscalls.registry.list():
        tool_spec = ToolSpec(
            name=syscall_spec.name,
            description=syscall_spec.description,
            input_schema=syscall_spec.input_schema,
            output_schema=syscall_spec.output_schema,
            risk_level=syscall_spec.risk,
            requires_approval=syscall_spec.requires_approval,
            tags=syscall_spec.tags,
        )
        router.register(tool_spec, _syscall_handler(syscalls, auto_approve))
    return router


def _syscall_handler(syscalls: SyscallRouter, auto_approve: bool) -> Callable[[ToolCall], ToolResult]:
    def handler(call: ToolCall) -> ToolResult:
        result = syscalls.dispatch(
            SyscallCall(
                run_id=str(call.metadata.get("run_id", "mcp-compat")),
                instruction_id=str(call.metadata.get("instruction_id", "mcp-call")),
                name=call.name,
                input=call.args,
                approval_granted=auto_approve,
            )
        )
        return ToolResult(
            success=result.success,
            name=call.name,
            output=result.output,
            error=result.error,
            risk_level=result.risk,
            requires_approval=result.requires_approval,
        )

    return handler

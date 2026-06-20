"""MCP-like tool router."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loopos.execution.permissions import PermissionPolicy
from loopos.execution.terminal import TerminalExecutor
from loopos.mcp.types import RegisteredTool, ToolCall, ToolRegistry, ToolResult, ToolSpec
from loopos.policy_os.engine import PolicyEngine


class ToolRouter:
    """Resolve and invoke registered tools."""

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
        if not policy_decision.allowed:
            return ToolResult(
                success=False,
                name=tool_call.name,
                error=f"policy {policy_decision.action}: {', '.join(policy_decision.reason_codes)}",
                risk_level=spec.risk_level,
                requires_approval=policy_decision.action == "require_approval",
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
    """Create router with MVP built-ins."""

    root = Path(workspace).resolve()
    terminal_executor = terminal or TerminalExecutor(
        default_cwd=root,
        auto_approve=auto_approve,
        policy=PermissionPolicy(allowlist_paths=[root], policy_engine=policy_engine),
    )
    router = ToolRouter(auto_approve=auto_approve, policy_engine=policy_engine)

    def terminal_exec(call: ToolCall) -> ToolResult:
        observation = terminal_executor.execute(
            str(call.args.get("cmd", "")),
            cwd=call.args.get("cwd", root),
            timeout_seconds=call.args.get("timeout_seconds"),
        )
        return ToolResult(
            success=observation.success,
            name=call.name,
            output=observation.model_dump(mode="json"),
            error=observation.error,
        )

    def file_read(call: ToolCall) -> ToolResult:
        path = _safe_path(root, call.args.get("path"))
        if path is None:
            return ToolResult(success=False, name=call.name, error="path is outside workspace")
        if not path.exists():
            return ToolResult(success=False, name=call.name, error=f"file not found: {path}")
        return ToolResult(success=True, name=call.name, output={"content": path.read_text(encoding="utf-8")})

    def file_write(call: ToolCall) -> ToolResult:
        path = _safe_path(root, call.args.get("path"))
        if path is None:
            return ToolResult(success=False, name=call.name, error="path is outside workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(call.args.get("content", "")), encoding="utf-8")
        return ToolResult(success=True, name=call.name, output={"path": str(path)})

    def git_status(call: ToolCall) -> ToolResult:
        completed = subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return ToolResult(
            success=completed.returncode == 0,
            name=call.name,
            output={"stdout": completed.stdout, "stderr": completed.stderr},
            error=None if completed.returncode == 0 else completed.stderr,
        )

    router.register(
        ToolSpec(
            name="terminal.exec",
            description="Execute a permission-gated terminal command.",
            input_schema={"type": "object", "required": ["cmd"]},
            output_schema={"type": "object"},
            risk_level="medium",
            requires_approval=False,
            tags=["terminal"],
        ),
        terminal_exec,
    )
    router.register(
        ToolSpec(
            name="file.read",
            description="Read a UTF-8 workspace file.",
            input_schema={"type": "object", "required": ["path"]},
            output_schema={"type": "object"},
            risk_level="low",
            tags=["file"],
        ),
        file_read,
    )
    router.register(
        ToolSpec(
            name="file.write",
            description="Write a UTF-8 workspace file.",
            input_schema={"type": "object", "required": ["path", "content"]},
            output_schema={"type": "object"},
            risk_level="medium",
            tags=["file"],
        ),
        file_write,
    )
    router.register(
        ToolSpec(
            name="git.status",
            description="Return git short status for the workspace.",
            output_schema={"type": "object"},
            risk_level="low",
            tags=["git"],
        ),
        git_status,
    )
    return router


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path

"""Tool catalog."""

from __future__ import annotations

from loopos.tools.tool import Tool


class ToolCatalog:
    """Small static catalog for project-training actions."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self.tools = tools or [
            Tool(
                tool_id="executor.test_runner",
                name="Run Tests",
                description="Run project tests in a sandbox and capture stdout/stderr.",
                capabilities=["test.run", "shell.exec"],
                schema_tokens_estimate=120,
            ),
            Tool(
                tool_id="executor.patch_applier",
                name="Apply Patch",
                description="Apply a unified diff inside the sandbox.",
                capabilities=["file.patch"],
                schema_tokens_estimate=100,
            ),
            Tool(
                tool_id="computer.fake",
                name="Fake Computer",
                description="Observe and record fake computer actions without OS side effects.",
                capabilities=["computer.observe", "ui.verify"],
                schema_tokens_estimate=90,
            ),
            Tool(
                tool_id="memory.compiler",
                name="Compile Memory",
                description="Compile role-specific project memory under a token budget.",
                capabilities=["memory.retrieve"],
                schema_tokens_estimate=80,
            ),
        ]

    def list(self) -> list[Tool]:
        return list(self.tools)


__all__ = ["ToolCatalog"]

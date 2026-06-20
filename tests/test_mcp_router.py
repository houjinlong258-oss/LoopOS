import tempfile
import unittest
from pathlib import Path

from loopos.mcp.router import ToolRouter, create_default_router
from loopos.mcp.types import ToolCall, ToolResult, ToolSpec


class McpRouterTests(unittest.TestCase):
    def test_register_and_call_tool(self) -> None:
        router = ToolRouter()
        router.register(
            ToolSpec(name="demo", description="demo"),
            lambda call: ToolResult(success=True, name=call.name, output={"ok": True}),
        )
        result = router.call(ToolCall(name="demo"))
        self.assertTrue(result.success)
        self.assertEqual(result.output["ok"], True)

    def test_unknown_tool_fails(self) -> None:
        result = ToolRouter().call(ToolCall(name="missing"))
        self.assertFalse(result.success)

    def test_high_risk_requires_approval(self) -> None:
        router = ToolRouter()
        router.register(
            ToolSpec(name="danger", description="danger", risk_level="high", requires_approval=True),
            lambda call: ToolResult(success=True, name=call.name),
        )
        result = router.call(ToolCall(name="danger"))
        self.assertFalse(result.success)
        self.assertTrue(result.requires_approval)

    def test_default_file_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_router(workspace=tmp, auto_approve=True)
            write = router.call(ToolCall(name="file.write", args={"path": "a.txt", "content": "hello"}))
            self.assertTrue(write.success)
            read = router.call(ToolCall(name="file.read", args={"path": "a.txt"}))
            self.assertTrue(read.success)
            self.assertEqual(read.output["content"], "hello")
            blocked = router.call(ToolCall(name="file.read", args={"path": "../outside.txt"}))
            self.assertFalse(blocked.success)
            self.assertFalse((Path(tmp) / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()

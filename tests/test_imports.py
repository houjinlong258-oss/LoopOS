import importlib
import unittest


class ImportTests(unittest.TestCase):
    def test_core_modules_import(self) -> None:
        modules = [
            "loopos",
            "loopos.cli.app",
            "loopos.core.isa",
            "loopos.core.state",
            "loopos.core.loop_engine",
            "loopos.execution.terminal",
            "loopos.memory.governance",
            "loopos.mcp.router",
            "loopos.integrations.openhands_adapter",
            "loopos.tasks",
            "loopos.triggers",
            "loopos.worktree",
            "loopos.review",
            "loopos.model_kernel",
            "loopos.gateway",
            "loopos.skills",
        ]
        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()

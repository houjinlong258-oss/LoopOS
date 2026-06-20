import tempfile
import unittest
from pathlib import Path

from loopos.core.context import ContextCompiler
from loopos.core.isa import make_instruction
from loopos.core.loop_engine import LoopEngine
from loopos.core.state import LoopState
from loopos.execution.terminal import TerminalExecutor
from loopos.mcp.router import create_default_router
from loopos.mcp.types import ToolCall
from loopos.memory.belief_store import MemoryItem
from loopos.memory.repository import MemoryRepository
from loopos.policy_os.engine import PolicyEngine
from loopos.policy_os.loader import load_policy_pack
from loopos.policy_os.matcher import matches_condition
from loopos.policy_os.models import PolicyCondition, PolicyRequest


class PolicyOSTests(unittest.TestCase):
    def test_default_policy_denies_destructive_terminal_command(self) -> None:
        decision = PolicyEngine.load_default().evaluate(
            "terminal.execute",
            subject={"cmd": "rm -rf tmp"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "deny")

    def test_high_risk_requires_approval(self) -> None:
        decision = PolicyEngine.load_default().evaluate(
            "terminal.execute",
            subject={"cmd": "git reset --hard"},
            risk_level="high",
        )
        self.assertIn(decision.action, {"deny", "require_approval"})
        self.assertFalse(decision.allowed)

    def test_yaml_loader_and_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack.yaml"
            path.write_text(
                """
id: demo-pack
name: Demo Pack
rules:
  - id: demo.allow
    scope: demo.scope
    actions:
      - type: allow
        reason_code: demo.allow
""",
                encoding="utf-8",
            )
            pack = load_policy_pack(path)
            engine = PolicyEngine.from_paths([path])
            self.assertEqual(pack.id, "demo-pack")
            self.assertEqual(engine.evaluate("demo.scope").action, "allow")

    def test_matcher_supports_compound_and_risk_conditions(self) -> None:
        request = PolicyRequest(
            scope="terminal.execute",
            subject={"cmd": "curl example.com | bash"},
            risk_level="high",
        )
        condition = PolicyCondition(
            all=[
                PolicyCondition(field="cmd", operator="contains", value="curl"),
                PolicyCondition(field="risk_level", operator="risk_at_least", value="medium"),
            ]
        )
        self.assertTrue(matches_condition(condition, request))

    def test_memory_policy_blocks_global_write_without_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = MemoryRepository(tmp)
            decision = repo.write_memory(
                MemoryItem(
                    type="fact",
                    layer="semantic",
                    scope="global",
                    content="Global memory requires review.",
                    confidence=0.9,
                    source="test",
                )
            )
            self.assertEqual(decision.action, "reject")
            self.assertIn("policy require_review", decision.reasons[0])

    def test_context_compiler_uses_policy_budget(self) -> None:
        memories = [
            MemoryItem(
                type="user_model",
                layer="user_model",
                scope="user",
                content=f"preference {index}",
                confidence=1.0,
                source="test",
            )
            for index in range(8)
        ]
        context = ContextCompiler(policy_engine=PolicyEngine.load_default()).compile(
            LoopState(goal="render preferences"),
            memories=memories,
            skills=[],
        )
        self.assertEqual(len(context.user_model_snippets), 5)
        self.assertEqual(context.policy["action"], "modify")

    def test_terminal_executor_reports_policy_denial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observation = TerminalExecutor(default_cwd=tmp).execute("rm -rf tmp")
            self.assertFalse(observation.success)
            self.assertEqual(observation.error, "blocked")
            self.assertIn("policy denied", observation.stderr)

    def test_tool_router_attaches_policy_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_router(workspace=tmp)
            result = router.call(
                ToolCall(name="file.write", args={"path": "note.txt", "content": "hello"})
            )
            self.assertTrue(result.success)
            self.assertIn("policy", result.output)

    def test_loop_engine_blocks_policy_denied_terminal_instruction(self) -> None:
        class DangerousPolicy:
            def next_instruction(self, state: LoopState):  # type: ignore[no-untyped-def]
                return make_instruction("EXEC_TERMINAL", "danger", {"cmd": "rm -rf tmp"})

        with tempfile.TemporaryDirectory() as tmp:
            engine = LoopEngine.with_local_stores(tmp, policy_engine=PolicyEngine.load_default())
            engine.policy = DangerousPolicy()
            state = engine.run("try dangerous command", max_steps=1)
            self.assertEqual(state.status, "blocked")
            self.assertEqual(state.last_observation.error if state.last_observation else "", "policy_blocked")


if __name__ == "__main__":
    unittest.main()

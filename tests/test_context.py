import unittest

from loopos.context import ContextCompiler
from loopos.core.context import ContextCompiler as LegacyContextCompiler
from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem
from loopos.memory.skill_store import Skill


class ContextCompilerTests(unittest.TestCase):
    def test_legacy_import_reexports_context_compiler(self) -> None:
        self.assertIs(LegacyContextCompiler, ContextCompiler)

    def test_compile_bounded_context(self) -> None:
        state = LoopState(goal="compile context")
        memories = [
            MemoryItem(
                type="belief",
                content="Use structured state.",
                confidence=0.9,
                source="test",
                tags=["architecture"],
            )
        ]
        skills = [
            Skill(
                name="Run tests",
                description="Run deterministic tests.",
                trigger_tags=["test"],
                steps=[],
            )
        ]
        context = ContextCompiler(max_memory=1, max_skills=1).compile(
            state,
            memories=memories,
            skills=skills,
        )
        self.assertEqual(context.goal, "compile context")
        self.assertEqual(context.memory[0]["content"], "Use structured state.")
        self.assertEqual(context.skills[0]["name"], "Run tests")
        self.assertGreater(context.token_budget_estimate, 0)

    def test_disabled_skills_are_not_injected(self) -> None:
        state = LoopState(goal="compile context")
        disabled = Skill(
            name="Disabled",
            description="Do not use",
            trigger_tags=["test"],
            steps=[{"op": "TERM.EXEC"}],
            status="disabled",
        )
        context = ContextCompiler().compile(state, skills=[disabled], available_tools=["file.read"])
        self.assertEqual(context.skills, [])
        self.assertEqual(context.allowed_tools, ["file.read"])

    def test_compile_layered_context_and_user_model(self) -> None:
        state = LoopState(goal="use memory")
        memories = [
            MemoryItem(
                type="fact",
                layer="episodic",
                content="Previous command failed.",
                confidence=0.8,
                source="test",
                tags=["failure"],
            ),
            MemoryItem(
                type="user_model",
                layer="user_model",
                scope="user",
                content="tone: concise",
                confidence=1.0,
                source="test",
                tags=["tone"],
            ),
        ]
        context = ContextCompiler().compile(state, memories=memories, skills=[])
        self.assertEqual(context.episodic_memories[0]["content"], "Previous command failed.")
        self.assertEqual(context.user_model_snippets[0]["content"], "tone: concise")


if __name__ == "__main__":
    unittest.main()

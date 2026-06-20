import unittest

from loopos.core.context import ContextCompiler
from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem
from loopos.memory.skill_store import Skill


class ContextCompilerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from loopos.core.isa import make_instruction
from loopos.memory.belief_store import BeliefStore, MemoryItem
from loopos.memory.event_log import EventLog
from loopos.memory.governance import MemoryGovernance
from loopos.memory.pre_action_gate import PreActionGate
from loopos.memory.retrieval import MemoryRetriever
from loopos.memory.skill_store import Skill, SkillStore, extract_skill_from_events


class MemoryTests(unittest.TestCase):
    def test_belief_store_and_governance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = BeliefStore(Path(tmp) / "beliefs.jsonl")
            item = MemoryItem(
                type="belief",
                content="Use pytest for tests.",
                confidence=0.8,
                source="test",
                tags=["testing"],
            )
            decision = MemoryGovernance().review(item, existing=[])
            self.assertEqual(decision.action, "allow")
            store.add(item)
            duplicate = MemoryItem(
                type="belief",
                content="Use pytest for tests.",
                confidence=0.9,
                source="test",
                tags=["testing"],
            )
            dup_decision = MemoryGovernance().review(duplicate, existing=store.list())
            self.assertEqual(dup_decision.action, "reject")

    def test_retrieval_ignores_low_confidence(self) -> None:
        items = [
            MemoryItem(type="belief", content="old", confidence=0.2, source="x", tags=["build"]),
            MemoryItem(type="belief", content="new", confidence=0.9, source="x", tags=["build"]),
        ]
        result = MemoryRetriever(items).retrieve(["build"], min_confidence=0.5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].content, "new")

    def test_pre_action_gate_blocks_repeated_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(Path(tmp) / "events.jsonl")
            log.append("observation", "run", 1, {"command": "bad", "success": False})
            log.append("observation", "run", 2, {"command": "bad", "success": False})
            gate = PreActionGate(events=log.list())
            decision = gate.before(make_instruction("EXEC_TERMINAL", "retry", {"cmd": "bad"}))
            self.assertEqual(decision.action, "block")

    def test_pre_action_gate_suggests_skill(self) -> None:
        skill = Skill(
            name="Run tests",
            description="Run project test suite.",
            trigger_tags=["pytest"],
            steps=[],
            confidence=0.8,
        )
        gate = PreActionGate(skills=[skill])
        decision = gate.before(make_instruction("EXEC_TERMINAL", "pytest", {"cmd": "pytest"}))
        self.assertEqual(decision.action, "substitute_skill")
        self.assertEqual(decision.skill_id, skill.id)

    def test_skill_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(Path(tmp) / "events.jsonl")
            log.append("instruction_planned", "run", 0, {"op": "PLAN"})
            skill = extract_skill_from_events(
                log.list(),
                name="plan",
                description="plan step",
                trigger_tags=["plan"],
            )
            self.assertEqual(skill.source_run_id, "run")
            self.assertEqual(len(skill.steps), 1)
            store = SkillStore(Path(tmp) / "skills.jsonl")
            store.add(skill)
            self.assertEqual(len(store.find_by_tags(["plan"])), 1)


if __name__ == "__main__":
    unittest.main()

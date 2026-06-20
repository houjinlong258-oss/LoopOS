import unittest

from loopos.convergence import ConvergenceEngine, EvaluationResult, ProgressDelta
from loopos.goal import GoalNegotiator


class GoalNegotiationTests(unittest.TestCase):
    def test_vague_goal_proposes_five_options(self) -> None:
        proposal = GoalNegotiator().propose("帮我优化这个项目")
        self.assertTrue(proposal.analysis.ambiguous)
        self.assertEqual(len(proposal.options), 5)

    def test_concrete_goal_finalizes_without_question(self) -> None:
        negotiator = GoalNegotiator()
        raw = "创建 hello.py，内容 print('hello')，运行它并确认输出 hello"
        analysis = negotiator.analyze(raw)
        spec = negotiator.finalize(raw)
        self.assertFalse(analysis.ambiguous)
        self.assertEqual(spec.objective, raw)

    def test_ambiguous_goal_requires_selection(self) -> None:
        with self.assertRaises(ValueError):
            GoalNegotiator().finalize("帮我优化这个项目")


class ConvergenceTests(unittest.TestCase):
    def test_success_and_replan_decisions(self) -> None:
        engine = ConvergenceEngine()
        success = engine.decide(
            EvaluationResult(goal_satisfied=True, score=1.0),
            ProgressDelta(previous_score=0.5, current_score=1.0, delta=0.5),
        )
        stalled = engine.decide(
            EvaluationResult(score=0.4),
            ProgressDelta(previous_score=0.4, current_score=0.4, delta=0.0),
        )
        self.assertEqual(success.action, "halt_success")
        self.assertTrue(success.halt.reached)
        self.assertEqual(stalled.action, "replan")

    def test_missing_information_asks_user(self) -> None:
        decision = ConvergenceEngine().decide(
            EvaluationResult(missing_information=True),
            ProgressDelta(previous_score=0.0, current_score=0.0, delta=0.0),
        )
        self.assertEqual(decision.action, "ask_user")


if __name__ == "__main__":
    unittest.main()

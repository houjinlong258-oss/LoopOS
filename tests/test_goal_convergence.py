import unittest

from loopos.convergence import ConvergenceEngine, EvaluationResult, ProgressDelta
from loopos.goal import GoalNegotiator


class GoalNegotiationTests(unittest.TestCase):
    def test_three_ambiguity_modes_and_rich_goal_spec(self) -> None:
        negotiator = GoalNegotiator()
        low = negotiator.analyze("创建 hello.py，运行 pytest 并确认输出 hello")
        medium = negotiator.analyze("为项目增加日志")
        high = negotiator.analyze("帮我优化这个项目")

        self.assertEqual(low.level, "low")
        self.assertEqual(medium.level, "medium")
        self.assertTrue(medium.requires_confirmation)
        self.assertEqual(high.level, "high")
        self.assertTrue(high.requires_negotiation)

        spec = negotiator.finalize("为项目增加日志", confirmed=True)
        self.assertEqual(spec.origin, "confirmed")
        self.assertTrue(spec.scope)
        self.assertTrue(spec.acceptance_criteria)

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

    def test_regression_and_repeated_action_are_deterministic(self) -> None:
        engine = ConvergenceEngine()
        regression = engine.decide(
            EvaluationResult(regression=True, repairable=True, evidence=["test regressed"]),
            ProgressDelta(previous_score=0.8, current_score=0.5, delta=-0.3),
        )
        repeated = engine.decide(
            EvaluationResult(score=0.5),
            ProgressDelta(
                previous_score=0.5,
                current_score=0.5,
                delta=0.0,
                repeated_actions=2,
            ),
        )
        self.assertEqual(regression.action, "repair")
        self.assertEqual(repeated.action, "replan")
        self.assertEqual(repeated.reason_code, "convergence.repeated_action_or_no_progress")


if __name__ == "__main__":
    unittest.main()

import unittest

from loopos.core.safety import CommandRiskAnalyzer


class SafetyTests(unittest.TestCase):
    def test_blocked_patterns(self) -> None:
        assessment = CommandRiskAnalyzer().analyze("rm -rf /")
        self.assertEqual(assessment.risk_level, "blocked")
        self.assertTrue(assessment.requires_approval)

    def test_low_command(self) -> None:
        assessment = CommandRiskAnalyzer().analyze("git status")
        self.assertEqual(assessment.risk_level, "low")
        self.assertFalse(assessment.requires_approval)


if __name__ == "__main__":
    unittest.main()

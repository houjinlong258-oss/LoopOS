"""Tests for freedom-layer models: FreedomLevel, FreedomBudget, FreedomPolicy."""

from __future__ import annotations

import json
import unittest
from typing import get_args

from pydantic import ValidationError

from loopos.freedom import (
    FreedomBudget,
    FreedomLevel,
    FreedomPolicy,
    freedom_at_least,
    freedom_rank,
)
from loopos.freedom.models import FREEDOM_LEVELS


class FreedomLevelTests(unittest.TestCase):
    def test_required_levels_present(self) -> None:
        required = {
            "F0_DETERMINISTIC",
            "F1_TOOL_CHOICE",
            "F2_PLAN_FREEDOM",
            "F3_STRATEGY_FREEDOM",
            "F4_RESEARCH_FREEDOM",
            "F5_AUTONOMOUS_PROJECT",
        }
        self.assertEqual(set(get_args(FreedomLevel)), required)
        self.assertEqual(FREEDOM_LEVELS, tuple(sorted(required)))

    def test_freedom_rank(self) -> None:
        self.assertEqual(freedom_rank("F0_DETERMINISTIC"), 0)
        self.assertEqual(freedom_rank("F5_AUTONOMOUS_PROJECT"), 5)

    def test_freedom_at_least(self) -> None:
        self.assertTrue(freedom_at_least("F3_STRATEGY_FREEDOM", "F2_PLAN_FREEDOM"))
        self.assertFalse(freedom_at_least("F1_TOOL_CHOICE", "F3_STRATEGY_FREEDOM"))


class FreedomBudgetTests(unittest.TestCase):
    def test_default_budget_is_f0_like(self) -> None:
        budget = FreedomBudget()
        self.assertEqual(budget.max_network_calls, 0)
        self.assertEqual(budget.max_database_mutations, 0)

    def test_with_level_tightens_caps(self) -> None:
        budget = FreedomBudget(
            max_network_calls=100,
            max_database_mutations=100,
            max_filesystem_writes=1000,
            max_steps=200,
        )
        f0 = budget.with_level("F0_DETERMINISTIC")
        self.assertEqual(f0.max_network_calls, 0)
        self.assertEqual(f0.max_database_mutations, 0)
        self.assertEqual(f0.max_filesystem_writes, 0)
        self.assertEqual(f0.max_steps, 4)

    def test_with_level_relaxes_caps_under_f5(self) -> None:
        """A higher level raises the *ceiling*; caller caps below it stay."""
        budget = FreedomBudget(
            max_network_calls=100,
            max_database_mutations=100,
            max_filesystem_writes=2000,
            max_steps=200,
        )
        f5 = budget.with_level("F5_AUTONOMOUS_PROJECT")
        # F5 ceiling is 32/64/512/128. Caller caps are above, so the
        # ceiling wins.
        self.assertEqual(f5.max_network_calls, 32)
        self.assertEqual(f5.max_database_mutations, 64)
        self.assertEqual(f5.max_filesystem_writes, 512)
        self.assertEqual(f5.max_steps, 128)

    def test_with_level_keeps_caller_tighter_than_ceiling(self) -> None:
        budget = FreedomBudget(
            max_network_calls=4,
            max_database_mutations=2,
            max_filesystem_writes=8,
            max_steps=3,
        )
        f5 = budget.with_level("F5_AUTONOMOUS_PROJECT")
        # Caller caps are below the F5 ceiling, so they survive.
        self.assertEqual(f5.max_network_calls, 4)
        self.assertEqual(f5.max_database_mutations, 2)
        self.assertEqual(f5.max_filesystem_writes, 8)
        self.assertEqual(f5.max_steps, 3)

    def test_budget_serialization_roundtrip(self) -> None:
        budget = FreedomBudget(max_steps=12, max_tool_calls=4)
        payload = json.loads(budget.model_dump_json())
        rebuilt = FreedomBudget.model_validate(payload)
        self.assertEqual(rebuilt.max_steps, 12)
        self.assertEqual(rebuilt.max_tool_calls, 4)

    def test_invalid_caps_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            FreedomBudget(max_steps=0)


class FreedomPolicyTests(unittest.TestCase):
    def test_default_policy_is_f0(self) -> None:
        policy = FreedomPolicy()
        self.assertEqual(policy.level, "F0_DETERMINISTIC")
        self.assertFalse(policy.allow_network)
        self.assertFalse(policy.allow_database_mutation)
        self.assertFalse(policy.allow_release_tag_changes)
        self.assertFalse(policy.allow_privilege_escalation)
        self.assertEqual(policy.max_filesystem_write_bytes, 0)

    def test_normalize_approval_actions(self) -> None:
        policy = FreedomPolicy(
            require_human_approval_for=[" release_tag ", "", "database_mutation"]
        )
        self.assertEqual(
            policy.require_human_approval_for,
            ["release_tag", "database_mutation"],
        )


if __name__ == "__main__":
    unittest.main()

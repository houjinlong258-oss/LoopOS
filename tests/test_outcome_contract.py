"""Tests for :class:`OutcomeContract` and :class:`OutcomeEvidence`."""

from __future__ import annotations

import unittest
from typing import get_args

from pydantic import ValidationError

from loopos.freedom import (
    AcceptanceCriterion,
    HaltCondition,
    OutcomeContract,
    OutcomeEvidence,
    OutcomeStatus,
)


def _contract() -> OutcomeContract:
    return OutcomeContract(
        title="Ship v0.2",
        description="LoopOS v0.2 governance layer",
        deliverables=["loopos/aci", "loopos/ali", "loopos/freedom"],
        acceptance_criteria=[
            AcceptanceCriterion(description="All tests pass", required=True),
            AcceptanceCriterion(description="Coverage stable", required=True),
            AcceptanceCriterion(description="LSP clean", required=False),
        ],
        halt_conditions=[
            HaltCondition(description="Policy denied tag change"),
        ],
        evidence_kinds=["test_report", "command_output", "review_artifact"],
    )


class OutcomeContractTests(unittest.TestCase):
    def test_contract_round_trip(self) -> None:
        c = _contract()
        rebuilt = OutcomeContract.model_validate_json(c.model_dump_json())
        self.assertEqual(rebuilt.title, c.title)
        self.assertEqual(len(rebuilt.acceptance_criteria), 3)
        self.assertEqual(len(rebuilt.halt_conditions), 1)

    def test_required_evidence_kinds(self) -> None:
        c = _contract()
        self.assertEqual(
            c.required_evidence_kinds(),
            ["test_report", "command_output", "review_artifact"],
        )

    def test_title_required(self) -> None:
        with self.assertRaises(ValidationError):
            OutcomeContract(title="")
        with self.assertRaises(ValidationError):
            OutcomeContract(title="   ")

    def test_outcome_status_is_typed(self) -> None:
        values = set(get_args(OutcomeStatus))
        self.assertEqual(
            values,
            {"pending", "in_progress", "satisfied", "failed", "blocked"},
        )


class OutcomeEvidenceTests(unittest.TestCase):
    def test_evidence_is_complete_only_when_required_kinds_present(self) -> None:
        c = _contract()
        e = OutcomeEvidence(
            contract_id=c.contract_id,
            collected=["test_report", "command_output", "review_artifact"],
            criterion_status={
                c.acceptance_criteria[0].criterion_id: "satisfied",
                c.acceptance_criteria[1].criterion_id: "satisfied",
            },
        )
        self.assertTrue(e.is_complete(c))

    def test_evidence_is_incomplete_when_required_kind_missing(self) -> None:
        c = _contract()
        e = OutcomeEvidence(
            contract_id=c.contract_id,
            collected=["test_report", "command_output"],  # missing review_artifact
            criterion_status={
                c.acceptance_criteria[0].criterion_id: "satisfied",
            },
        )
        self.assertFalse(e.is_complete(c))

    def test_evidence_is_incomplete_when_required_criterion_pending(self) -> None:
        c = _contract()
        e = OutcomeEvidence(
            contract_id=c.contract_id,
            collected=["test_report", "command_output", "review_artifact"],
            criterion_status={
                c.acceptance_criteria[0].criterion_id: "satisfied",
                c.acceptance_criteria[1].criterion_id: "pending",
            },
        )
        self.assertFalse(e.is_complete(c))

    def test_optional_criterion_does_not_block_completion(self) -> None:
        c = _contract()
        e = OutcomeEvidence(
            contract_id=c.contract_id,
            collected=c.required_evidence_kinds(),
            criterion_status={
                c.acceptance_criteria[0].criterion_id: "satisfied",
                c.acceptance_criteria[1].criterion_id: "satisfied",
                # criterion[2] is optional; no entry needed.
            },
        )
        self.assertTrue(e.is_complete(c))


if __name__ == "__main__":
    unittest.main()

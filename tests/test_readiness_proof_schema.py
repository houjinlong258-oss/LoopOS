"""Tests for the readiness-proof schema validator and the example instance."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_readiness_schema import (
    PHASE_VALUES,
    REQUIRED_FIELDS,
    ReadinessSchemaError,
    compare_schema_and_example,
    load_and_validate,
    validate_readiness_proof,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "readiness-proof.schema.json"
EXAMPLE_PATH = REPO_ROOT / "docs" / "schemas" / "readiness-proof.example.json"


def _good_instance() -> dict[str, object]:
    return {
        "schema_version": "0.2",
        "phase": "phase-0",
        "generated_at": "2026-06-22T00:00:00Z",
        "fsm_coverage": True,
        "policy_gates_active": True,
        "budget_enforced": True,
        "memory_governed": True,
        "replay_deterministic": True,
        "go_core_untouched": True,
        "aci_runtime_bound": True,
        "ali_fsm_bound": True,
        "anti_bloat_checked": True,
    }


class ReadinessSchemaValidatorTests(unittest.TestCase):
    def test_good_instance_validates(self) -> None:
        issues = validate_readiness_proof(_good_instance())
        self.assertEqual(issues, [])

    def test_missing_field_detected(self) -> None:
        instance = _good_instance()
        del instance["fsm_coverage"]
        issues = validate_readiness_proof(instance)
        self.assertTrue(any("fsm_coverage" in i for i in issues))

    def test_wrong_type_for_boolean(self) -> None:
        instance = _good_instance()
        instance["aci_runtime_bound"] = "yes"  # type: ignore[assignment]
        issues = validate_readiness_proof(instance)
        self.assertTrue(any("aci_runtime_bound" in i for i in issues))

    def test_invalid_phase_value(self) -> None:
        instance = _good_instance()
        instance["phase"] = "phase-99"
        issues = validate_readiness_proof(instance)
        self.assertTrue(any("phase" in i for i in issues))

    def test_invalid_schema_version(self) -> None:
        instance = _good_instance()
        instance["schema_version"] = "1"
        issues = validate_readiness_proof(instance)
        self.assertTrue(any("schema_version" in i for i in issues))

    def test_non_object_instance_rejected(self) -> None:
        issues = validate_readiness_proof([])  # type: ignore[arg-type]
        self.assertTrue(any("object" in i for i in issues))

    def test_load_and_validate_passes_for_example(self) -> None:
        issues = load_and_validate(EXAMPLE_PATH)
        self.assertEqual(issues, [], f"example failed: {issues}")

    def test_required_fields_constant(self) -> None:
        expected = {
            "schema_version",
            "phase",
            "generated_at",
            "fsm_coverage",
            "policy_gates_active",
            "budget_enforced",
            "memory_governed",
            "replay_deterministic",
            "go_core_untouched",
            "aci_runtime_bound",
            "ali_fsm_bound",
            "anti_bloat_checked",
        }
        self.assertEqual(set(REQUIRED_FIELDS), expected)

    def test_phase_values_constant(self) -> None:
        self.assertEqual(
            PHASE_VALUES,
            frozenset({"phase-0", "phase-1", "phase-2", "release-candidate", "release"}),
        )

    def test_compare_schema_and_example_clean(self) -> None:
        issues = compare_schema_and_example(SCHEMA_PATH, EXAMPLE_PATH)
        self.assertEqual(issues, [], f"drift detected: {issues}")

    def test_compare_schema_and_example_detects_drift(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_schema = Path(tmp) / "schema.json"
            tmp_example = Path(tmp) / "example.json"
            tmp_schema.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "required": ["brand_new_field", "fsm_coverage"],
                    }
                ),
                encoding="utf-8",
            )
            tmp_example.write_text(
                json.dumps({"fsm_coverage": True}),
                encoding="utf-8",
            )
            issues = compare_schema_and_example(tmp_schema, tmp_example)
            self.assertTrue(any("brand_new_field" in i for i in issues))


if __name__ == "__main__":
    unittest.main()

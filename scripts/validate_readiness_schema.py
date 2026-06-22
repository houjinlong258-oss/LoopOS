"""Standalone validation for the LoopOS readiness-proof schema.

This module is intentionally stdlib-only so it can run inside CI
without introducing a new dependency. It performs a minimal
structural validation that mirrors the JSON schema defined at
``docs/schemas/readiness-proof.schema.json``.

The goal is not to be a full JSON-schema implementation: it is to
catch drift between the schema and the example, and to confirm that
the 9 required boolean fields are present and have the right type.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

REQUIRED_FIELDS: tuple[str, ...] = (
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
)

BOOLEAN_FIELDS: tuple[str, ...] = (
    "fsm_coverage",
    "policy_gates_active",
    "budget_enforced",
    "memory_governed",
    "replay_deterministic",
    "go_core_untouched",
    "aci_runtime_bound",
    "ali_fsm_bound",
    "anti_bloat_checked",
)

PHASE_VALUES: frozenset[str] = frozenset(
    {"phase-0", "phase-1", "phase-2", "release-candidate", "release"}
)


class ReadinessSchemaError(ValueError):
    """Raised when a readiness-proof instance fails the minimal check."""


def _require(instance: Any, field: str, expected_type: type) -> None:
    if not isinstance(instance, dict):
        raise ReadinessSchemaError(
            f"readiness-proof must be an object, got {type(instance).__name__}"
        )
    if field not in instance:
        raise ReadinessSchemaError(f"missing required field: {field!r}")
    value = instance[field]
    if not isinstance(value, expected_type):
        raise ReadinessSchemaError(
            f"field {field!r} must be {expected_type.__name__}, got {type(value).__name__}"
        )


def validate_readiness_proof(instance: dict[str, Any]) -> list[str]:
    """Return a list of structural issues; empty list means valid."""

    issues: list[str] = []
    if not isinstance(instance, dict):
        return [f"readiness-proof must be an object, got {type(instance).__name__}"]
    for field in REQUIRED_FIELDS:
        if field not in instance:
            issues.append(f"missing required field: {field!r}")
    for field in BOOLEAN_FIELDS:
        value = instance.get(field)
        if value is not None and not isinstance(value, bool):
            issues.append(f"field {field!r} must be a boolean, got {type(value).__name__}")
    schema_version = instance.get("schema_version")
    if isinstance(schema_version, str) and not _looks_like_version(schema_version):
        issues.append(f"schema_version must look like 'X.Y', got {schema_version!r}")
    phase = instance.get("phase")
    if isinstance(phase, str) and phase not in PHASE_VALUES:
        issues.append(f"phase {phase!r} is not in {sorted(PHASE_VALUES)}")
    generated_at = instance.get("generated_at")
    if isinstance(generated_at, str) and not _looks_like_iso8601(generated_at):
        issues.append(f"generated_at must be an ISO 8601 timestamp, got {generated_at!r}")
    return issues


def _looks_like_version(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 2:
        return False
    return all(part.isdigit() for part in parts)


def _looks_like_iso8601(value: str) -> bool:
    # Minimal: must contain 'T' separator or space, and year prefix.
    return (
        len(value) >= 10 and value[4] == "-" and value[7] == "-" and ("T" in value or " " in value)
    )


def load_and_validate(path: str | Path) -> list[str]:
    """Load a JSON file and return structural issues."""

    text = Path(path).read_text(encoding="utf-8")
    instance = json.loads(text)
    return validate_readiness_proof(instance)


def compare_schema_and_example(
    schema_path: str | Path,
    example_path: str | Path,
) -> list[str]:
    """Compare a JSON schema's ``required`` list with an example file."""

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    example = json.loads(Path(example_path).read_text(encoding="utf-8"))
    required = schema.get("required", [])
    issues: list[str] = []
    if not isinstance(required, Iterable):
        issues.append("schema 'required' must be a list")
        return issues
    for field in required:
        if field not in example:
            issues.append(f"example missing required field: {field!r}")
    return issues

"""Procedure skill helpers."""

from __future__ import annotations

from loopos.skills.skill import ProcedureSkill


def default_test_repair_skill() -> ProcedureSkill:
    return ProcedureSkill(
        skill_id="procedure.test_repair",
        title="Repair failing test",
        steps=["Read failure", "Patch smallest cause", "Re-run focused tests"],
        tags=["repair", "test"],
    )


__all__ = ["default_test_repair_skill"]

"""Procedure skill registry."""

from __future__ import annotations

from loopos.skills.procedure_skill import default_test_repair_skill
from loopos.skills.skill import ProcedureSkill


class SkillRegistry:
    def __init__(self, skills: list[ProcedureSkill] | None = None) -> None:
        self._skills = skills or [default_test_repair_skill()]

    def list(self) -> list[ProcedureSkill]:
        return list(self._skills)


__all__ = ["SkillRegistry"]

from __future__ import annotations

from loopos.skills.registry import SkillRegistry
from loopos.skills.skill import ProcedureSkill


def test_skill_registry_defaults_to_test_repair_skill() -> None:
    skills = SkillRegistry().list()

    assert [skill.skill_id for skill in skills] == ["procedure.test_repair"]


def test_skill_registry_returns_copy() -> None:
    registry = SkillRegistry([ProcedureSkill(skill_id="x", title="X")])
    listed = registry.list()

    listed.clear()

    assert [skill.skill_id for skill in registry.list()] == ["x"]

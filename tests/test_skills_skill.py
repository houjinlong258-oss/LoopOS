from __future__ import annotations

import pytest
from pydantic import ValidationError

from loopos.skills.skill import ProcedureSkill


def test_procedure_skill_defaults_to_empty_steps_and_tags() -> None:
    skill = ProcedureSkill(skill_id="skill-1", title="Skill 1")

    assert skill.steps == []
    assert skill.tags == []


def test_procedure_skill_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProcedureSkill.model_validate(
            {"skill_id": "skill-1", "title": "Skill 1", "extra": True}
        )

from __future__ import annotations

from loopos.skills.procedure_skill import default_test_repair_skill


def test_default_test_repair_skill_has_repair_steps() -> None:
    skill = default_test_repair_skill()

    assert skill.skill_id == "procedure.test_repair"
    assert "test" in skill.tags
    assert skill.steps == ["Read failure", "Patch smallest cause", "Re-run focused tests"]

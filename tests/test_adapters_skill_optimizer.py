from __future__ import annotations

from loopos.adapters.skill_optimizer import SkillOptimizerAdapter


def test_skill_optimizer_adapter_is_model_only_by_default() -> None:
    adapter = SkillOptimizerAdapter()

    assert adapter.adapter_id == "skill_optimizer"
    assert adapter.model_only is True

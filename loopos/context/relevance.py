"""Context relevance filters."""

from loopos.memory.skill_store import Skill


def active_skills(skills: list[Skill]) -> list[Skill]:
    return [skill for skill in skills if skill.status == "active"]


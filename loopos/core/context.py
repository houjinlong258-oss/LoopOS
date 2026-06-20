"""Compact structured context compiler."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem
from loopos.memory.skill_store import Skill


class AgentContext(BaseModel):
    """Structured context passed to planners or renderers."""

    run_id: str
    goal: str
    status: str
    step_index: int
    progress_score: float
    recent_errors: list[str] = Field(default_factory=list)
    memory: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    working_summary: list[dict[str, Any]] = Field(default_factory=list)
    episodic_memories: list[dict[str, Any]] = Field(default_factory=list)
    semantic_memories: list[dict[str, Any]] = Field(default_factory=list)
    belief_memories: list[dict[str, Any]] = Field(default_factory=list)
    reusable_skills: list[dict[str, Any]] = Field(default_factory=list)
    user_model_snippets: list[dict[str, Any]] = Field(default_factory=list)
    recent_failures: list[dict[str, Any]] = Field(default_factory=list)


PolicyContext = AgentContext


class ContextCompiler:
    """Compile bounded context without prompt stuffing."""

    def __init__(
        self,
        *,
        max_memory: int = 5,
        max_skills: int = 5,
        working_budget: int = 3,
        episodic_budget: int = 5,
        semantic_budget: int = 8,
        skill_budget: int = 5,
        user_model_budget: int = 5,
    ) -> None:
        self.max_memory = max_memory
        self.max_skills = max_skills
        self.working_budget = working_budget
        self.episodic_budget = episodic_budget
        self.semantic_budget = semantic_budget
        self.skill_budget = skill_budget
        self.user_model_budget = user_model_budget

    def compile(
        self,
        state: LoopState,
        memories: list[MemoryItem] | None = None,
        skills: list[Skill] | None = None,
    ) -> PolicyContext:
        memory_items = memories or []
        skill_items = skills or []
        working = self._memory_dicts(
            [item for item in memory_items if item.layer == "working"],
            self.working_budget,
        )
        episodic = self._memory_dicts(
            [item for item in memory_items if item.layer == "episodic"],
            self.episodic_budget,
        )
        semantic = self._memory_dicts(
            [item for item in memory_items if item.layer == "semantic"],
            self.semantic_budget,
        )
        beliefs = self._memory_dicts(
            [item for item in memory_items if item.layer == "belief"],
            self.semantic_budget,
        )
        user_model = self._memory_dicts(
            [item for item in memory_items if item.layer == "user_model"],
            self.user_model_budget,
        )
        recent_failures = self._memory_dicts(
            [item for item in memory_items if item.type == "failure"],
            self.episodic_budget,
        )
        reusable_skills = self._skill_dicts(skill_items, self.skill_budget)
        return AgentContext(
            run_id=state.run_id,
            goal=state.goal,
            status=state.status,
            step_index=state.step_index,
            progress_score=state.progress_score,
            recent_errors=state.errors[-3:],
            memory=self._memory_dicts(memory_items, self.max_memory),
            skills=self._skill_dicts(skill_items, self.max_skills),
            working_summary=working,
            episodic_memories=episodic,
            semantic_memories=semantic,
            belief_memories=beliefs,
            reusable_skills=reusable_skills,
            user_model_snippets=user_model,
            recent_failures=recent_failures,
        )

    @staticmethod
    def _memory_dicts(items: list[MemoryItem], limit: int) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "type": item.type,
                "layer": item.layer,
                "scope": item.scope,
                "content": item.content,
                "confidence": item.confidence,
                "tags": item.tags,
            }
            for item in items[:limit]
        ]

    @staticmethod
    def _skill_dicts(skills: list[Skill], limit: int) -> list[dict[str, Any]]:
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "trigger_tags": skill.trigger_tags,
                "confidence": skill.confidence,
            }
            for skill in skills[:limit]
        ]

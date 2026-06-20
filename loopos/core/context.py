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


class ContextCompiler:
    """Compile bounded context without prompt stuffing."""

    def __init__(self, *, max_memory: int = 5, max_skills: int = 5) -> None:
        self.max_memory = max_memory
        self.max_skills = max_skills

    def compile(
        self,
        state: LoopState,
        memories: list[MemoryItem] | None = None,
        skills: list[Skill] | None = None,
    ) -> AgentContext:
        return AgentContext(
            run_id=state.run_id,
            goal=state.goal,
            status=state.status,
            step_index=state.step_index,
            progress_score=state.progress_score,
            recent_errors=state.errors[-3:],
            memory=[
                {
                    "id": item.id,
                    "type": item.type,
                    "content": item.content,
                    "confidence": item.confidence,
                    "tags": item.tags,
                }
                for item in (memories or [])[: self.max_memory]
            ],
            skills=[
                {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "trigger_tags": skill.trigger_tags,
                }
                for skill in (skills or [])[: self.max_skills]
            ],
        )

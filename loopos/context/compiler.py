"""Bounded structured context compiler."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from loopos.context.budget import bounded_int, estimate_tokens
from loopos.context.relevance import active_skills
from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem
from loopos.memory.skill_store import Skill
from loopos.policy_os.engine import PolicyEngine


class AgentContext(BaseModel):
    """Structured context passed to planners and renderers."""

    ctx_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    goal: str
    goal_summary: str
    status: str
    step_index: int
    progress_score: float
    state_summary: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    active_policy_constraints: dict[str, Any] = Field(default_factory=dict)
    token_budget_estimate: int = 0
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
    policy: dict[str, Any] = Field(default_factory=dict)


PolicyContext = AgentContext


class ContextCompiler:
    """Compile references and summaries without full history or raw stdout."""

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
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.max_memory = max_memory
        self.max_skills = max_skills
        self.working_budget = working_budget
        self.episodic_budget = episodic_budget
        self.semantic_budget = semantic_budget
        self.skill_budget = skill_budget
        self.user_model_budget = user_model_budget
        self.policy_engine = policy_engine

    def compile(
        self,
        state: LoopState,
        memories: list[MemoryItem] | None = None,
        skills: list[Skill] | None = None,
        *,
        available_tools: list[str] | None = None,
    ) -> PolicyContext:
        policy_payload: dict[str, Any] = {}
        budgets = {
            "working": self.working_budget,
            "episodic": self.episodic_budget,
            "semantic": self.semantic_budget,
            "skills": self.skill_budget,
            "user_model": self.user_model_budget,
        }
        if self.policy_engine is not None:
            decision = self.policy_engine.evaluate(
                "context.compile",
                subject={
                    "run_id": state.run_id,
                    "goal": state.goal,
                    "status": state.status,
                    "step_index": state.step_index,
                },
                tags=["context", "memory"],
            )
            policy_payload = decision.model_dump(mode="json")
            configured = decision.constraints.get("budgets", {})
            if isinstance(configured, dict):
                for key, fallback in list(budgets.items()):
                    budgets[key] = bounded_int(configured.get(key), fallback)

        memory_items = [item for item in memories or [] if item.status in {"active", "conflicted"}]
        skill_items = active_skills(skills or [])
        working = self._memory_dicts(
            [item for item in memory_items if item.layer == "working"], budgets["working"]
        )
        episodic = self._memory_dicts(
            [item for item in memory_items if item.layer == "episodic"], budgets["episodic"]
        )
        semantic = self._memory_dicts(
            [item for item in memory_items if item.layer == "semantic"], budgets["semantic"]
        )
        beliefs = self._memory_dicts(
            [item for item in memory_items if item.layer == "belief"], budgets["semantic"]
        )
        user_model = self._memory_dicts(
            [item for item in memory_items if item.layer == "user_model"], budgets["user_model"]
        )
        failures = self._memory_dicts(
            [item for item in memory_items if item.type == "failure"], budgets["episodic"]
        )
        reusable = self._skill_dicts(skill_items, budgets["skills"])
        compact_memory = self._memory_dicts(memory_items, self.max_memory)
        compact_skills = self._skill_dicts(skill_items, self.max_skills)
        budget_payload = compact_memory + compact_skills
        return AgentContext(
            run_id=state.run_id,
            goal=state.goal,
            goal_summary=state.goal.strip(),
            status=state.status,
            step_index=state.step_index,
            progress_score=state.progress_score,
            state_summary={
                "status": state.status,
                "step_index": state.step_index,
                "progress_score": state.progress_score,
            },
            constraints=list(policy_payload.get("reason_codes", [])),
            allowed_tools=available_tools or [],
            active_policy_constraints=dict(policy_payload.get("constraints", {})),
            token_budget_estimate=estimate_tokens(budget_payload),
            recent_errors=state.errors[-3:],
            memory=compact_memory,
            skills=compact_skills,
            working_summary=working,
            episodic_memories=episodic,
            semantic_memories=semantic,
            belief_memories=beliefs,
            reusable_skills=reusable,
            user_model_snippets=user_model,
            recent_failures=failures,
            policy=policy_payload,
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
                "conflicts": item.conflicts,
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
                "success_rate": skill.success_rate,
            }
            for skill in skills[:limit]
        ]


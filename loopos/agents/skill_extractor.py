"""Extract reusable structured skills from successful run traces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loopos.memory.skill_proposals import SkillProposal
from loopos.memory.skill_store import Skill

if TYPE_CHECKING:  # pragma: no cover - import-only for static type checkers.
    # These are only used as annotations; ``from __future__ import
    # annotations`` keeps them as strings at runtime, so deferring them
    # breaks a circular import via ``loopos.kernel.__init__`` ->
    # ``loopos.kernel.loop_engine`` -> ``loopos.agents.skill_extractor``
    # -> ``loopos.kernel.models``.
    from loopos.kernel.models import RunRecord
    from loopos.kernel.trace import TraceEvent

ACTION_KINDS = {"syscall", "instruction"}


class SkillExtractor:
    def extract(
        self,
        run: RunRecord,
        events: list[TraceEvent],
        *,
        name: str,
        description: str,
        trigger_tags: list[str],
    ) -> SkillProposal:
        if run.status != "succeeded":
            raise ValueError("skills can only be extracted from successful runs")
        steps: list[dict[str, object]] = []
        source_ids: list[str] = []
        for event in events:
            if event.kind not in ACTION_KINDS:
                continue
            operation = event.payload.get("op") or event.payload.get("name")
            if not isinstance(operation, str):
                continue
            steps.append({"op": operation, "args": event.payload.get("args", event.payload.get("input", {}))})
            source_ids.append(event.id)
        if len(steps) < 2:
            raise ValueError("skill extraction requires at least two structured actions")
        skill = Skill(
            name=name,
            description=description,
            trigger_tags=trigger_tags,
            steps=steps,
            source_run_id=run.run_id,
            source_runs=[run.run_id],
            confidence=0.75,
        )
        return SkillProposal(
            proposed_skill=skill,
            source_run_id=run.run_id,
            source_event_ids=source_ids,
            rationale="Compressed from a successful structured run trace.",
        )

"""Pre-action judgement before executing instructions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from loopos.core.isa import Instruction
from loopos.core.safety import CommandRiskAnalyzer
from loopos.memory.belief_store import MemoryItem
from loopos.memory.event_log import Event
from loopos.memory.skill_store import Skill

GateAction = Literal["allow", "block", "warn", "substitute_skill"]


class GateDecision(BaseModel):
    action: GateAction
    reasons: list[str] = Field(default_factory=list)
    skill_id: str | None = None


class PreActionGate:
    """Check memory and safety before executing an instruction."""

    def __init__(
        self,
        *,
        events: list[Event] | None = None,
        memories: list[MemoryItem] | None = None,
        skills: list[Skill] | None = None,
        analyzer: CommandRiskAnalyzer | None = None,
    ) -> None:
        self.events = events or []
        self.memories = memories or []
        self.skills = skills or []
        self.analyzer = analyzer or CommandRiskAnalyzer()

    def before(self, instruction: Instruction) -> GateDecision:
        if instruction.op != "EXEC_TERMINAL":
            return self._skill_decision(instruction) or GateDecision(action="allow")

        cmd = str(instruction.args.get("cmd", ""))
        risk = self.analyzer.analyze(cmd)
        if risk.risk_level == "blocked":
            return GateDecision(action="block", reasons=risk.reasons)

        repeated_failures = self._failed_command_count(cmd)
        if repeated_failures >= 2:
            return GateDecision(
                action="block",
                reasons=[f"command failed {repeated_failures} times before"],
            )

        for item in self.memories:
            if item.status != "active" or item.confidence < 0.7:
                continue
            if "failed" in item.tags and cmd and cmd.lower() in item.content.lower():
                return GateDecision(action="warn", reasons=["memory says this approach failed"])

        skill_decision = self._skill_decision(instruction)
        if skill_decision:
            return skill_decision
        return GateDecision(action="allow")

    def _failed_command_count(self, cmd: str) -> int:
        count = 0
        for event in self.events:
            payload = event.payload
            if payload.get("command") == cmd and payload.get("success") is False:
                count += 1
        return count

    def _skill_decision(self, instruction: Instruction) -> GateDecision | None:
        haystack = " ".join(
            [
                instruction.reason_code,
                str(instruction.args.get("cmd", "")),
                str(instruction.args.get("tool", "")),
            ]
        ).lower()
        for skill in self.skills:
            if skill.confidence < 0.5:
                continue
            if any(tag.lower() in haystack for tag in skill.trigger_tags):
                return GateDecision(
                    action="substitute_skill",
                    reasons=[f"matching skill available: {skill.name}"],
                    skill_id=skill.id,
                )
        return None

"""Deterministic intent resolver for the Apollo router (md §4.6).

The resolver maps a natural-language goal to a :class:`TaskIntent` and a
ranked set of candidate :class:`CommandIntent` manifests. It is fully
deterministic: same input -> same output, no external model calls
(md §4.6). A :class:`IntentResolverBackend` protocol is defined as the
documented future extension point; the default backend is
:class:`DeterministicIntentResolver`.

Resolution steps (md §4.6):

1. normalize user text
2. match explicit aliases
3. match task-type keywords
4. score candidate manifests
5. generate :class:`TaskIntent`
"""

from __future__ import annotations

import re
from typing import Protocol

from loopos.intent.registry import CommandRegistry, default_registry
from loopos.intent.schema import (
    CommandIntent,
    IntentResolution,
    OrchestrationMode,
    RiskLevel,
    TaskIntent,
    TaskType,
)

# Task-type keyword table. Matched against normalized text. Order does
# not matter; scoring aggregates all hits. Keep lowercase + Chinese.
_TASK_KEYWORDS: dict[TaskType, tuple[str, ...]] = {
    "release_readiness": (
        "release",
        "readiness",
        "ready to release",
        "can i release",
        "ship",
        "发布",
        "能不能发布",
        "能否发布",
        "可以发布",
        "发布检查",
    ),
    "test": ("test", "tests", "pytest", "unit test", "测试", "跑测试", "单元测试"),
    "lint": ("lint", "ruff", "代码检查"),
    "typecheck": ("typecheck", "mypy", "type check", "类型检查"),
    "policy_explain": (
        "explain",
        "why is",
        "dangerous",
        "curl | bash",
        "为什么危险",
        "解释",
        "危险",
    ),
    "model_call": (
        "model call",
        "mock model",
        "mock provider",
        "模型调用",
        "跑一次模型",
    ),
    "workbench": ("workbench", "工作台"),
    "fusion_planning": ("fusion", "融合"),
    "mad_dog_planning": ("mad dog", "mad-dog", "maddog", "疯狗"),
    "status": ("status", "状态"),
    "doctor": ("doctor", "diagnose", "诊断", "环境检查"),
}

# Mad Dog / fusion escalation hints. These do not raise authority; they
# only steer the recommended orchestration mode (md §4.4, §8.1).
_MAD_DOG_HINTS: tuple[str, ...] = (
    "mad dog",
    "mad-dog",
    "maddog",
    "疯狗",
    "修了三次",
    "again and again",
    "repeated failure",
    "还失败",
)
_FUSION_HINTS: tuple[str, ...] = ("fusion", "融合", "multi-model", "多模型")


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, and strip surrounding noise."""

    lowered = text.strip().lower()
    return re.sub(r"\s+", " ", lowered)


class IntentResolverBackend(Protocol):
    """Documented future extension point (md §4.6).

    A future backend may consult an external model. The default backend
    is deterministic and offline.
    """

    def resolve(self, goal: str, registry: CommandRegistry) -> IntentResolution: ...


class DeterministicIntentResolver:
    """Offline, deterministic resolver (default backend)."""

    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self._registry = registry if registry is not None else default_registry()

    @property
    def registry(self) -> CommandRegistry:
        return self._registry

    def resolve(self, goal: str, registry: CommandRegistry | None = None) -> IntentResolution:
        reg = registry if registry is not None else self._registry
        normalized = normalize(goal)

        scored = self._score_commands(normalized, reg)
        task_type, type_reason = self._infer_task_type(normalized, scored)
        primary = scored[0][1] if scored else None
        candidates = tuple(cmd for _, cmd in scored)

        recommended_mode = self._recommend_mode(normalized, primary)
        risk_level = primary.risk_level if primary is not None else "low"
        confidence = self._confidence(scored)

        reason_codes: list[str] = []
        reason_codes.extend(type_reason)
        if primary is not None:
            reason_codes.append(f"matched:{primary.command_id}")
        else:
            reason_codes.append("no_command_matched")
        if recommended_mode in ("fusion", "mad_dog"):
            reason_codes.append(f"escalation_suggested:{recommended_mode}")

        task_intent = TaskIntent(
            raw_text=goal,
            normalized_text=normalized,
            task_type=task_type,
            goal=goal.strip(),
            risk_level=risk_level,
            recommended_mode=recommended_mode,
            confidence=confidence,
            reason_codes=tuple(reason_codes),
        )
        return IntentResolution(
            task_intent=task_intent,
            primary=primary,
            candidates=candidates,
        )

    # -- internal helpers --------------------------------------------------

    def _score_commands(
        self, normalized: str, registry: CommandRegistry
    ) -> list[tuple[int, CommandIntent]]:
        scored: list[tuple[int, int, CommandIntent]] = []
        for index, command in enumerate(registry):
            score = self._score_one(normalized, command)
            if score > 0:
                # Negative index keeps registry order stable for ties.
                scored.append((score, -index, command))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [(score, command) for score, _neg_index, command in scored]

    def _score_one(self, normalized: str, command: CommandIntent) -> int:
        score = 0
        # Exact alias match is the strongest signal.
        for alias in command.aliases:
            alias_norm = normalize(alias)
            if not alias_norm:
                continue
            if alias_norm == normalized:
                score += 100
            elif alias_norm in normalized:
                score += 40
        # Task-type keyword overlap.
        for task_type in command.task_types:
            for keyword in _TASK_KEYWORDS.get(task_type, ()):  # noqa: PERF401
                if normalize(keyword) in normalized:
                    score += 10
        return score

    def _infer_task_type(
        self, normalized: str, scored: list[tuple[int, CommandIntent]]
    ) -> tuple[TaskType, list[str]]:
        if scored:
            command = scored[0][1]
            if command.task_types:
                return command.task_types[0], [f"task_type_from:{command.command_id}"]
        # Fall back to direct keyword inference.
        for task_type, keywords in _TASK_KEYWORDS.items():
            for keyword in keywords:
                if normalize(keyword) in normalized:
                    return task_type, [f"task_type_keyword:{keyword}"]
        return "unknown", ["task_type_unknown"]

    def _recommend_mode(self, normalized: str, primary: CommandIntent | None) -> OrchestrationMode:
        if any(hint in normalized for hint in _MAD_DOG_HINTS):
            return "mad_dog"
        if any(hint in normalized for hint in _FUSION_HINTS):
            return "fusion"
        if primary is not None and primary.command_id == "mad_dog.plan":
            return "mad_dog"
        if primary is not None and primary.command_id == "fusion.plan":
            return "fusion"
        return "single"

    def _confidence(self, scored: list[tuple[int, CommandIntent]]) -> float:
        if not scored:
            return 0.0
        top = scored[0][0]
        if top >= 100:
            return 0.95
        if top >= 40:
            return 0.75
        if top >= 10:
            return 0.5
        return 0.3


__all__ = [
    "normalize",
    "IntentResolverBackend",
    "DeterministicIntentResolver",
    "RiskLevel",
]

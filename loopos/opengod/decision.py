"""OpenGod strategy selection.

The :func:`decide` function consumes an :class:`OpenGodContext` and
returns an :class:`OpenGodDecision`. It is a pure function: same
context → same decision, no I/O.

The selection logic mirrors the v0.3 spec:

* If ``hard_fail_count > 0``           → ``halt``
* If ``readiness_status == "fail"``    → ``halt``
* If ``replay_status == "fail"``       → ``needs_repair``
* If ``fusion_mode == "mad_dog"``      → ``mad_dog``
* If ``fusion_mode in ("pair", "committee")`` → ``fusion_pair`` / ``fusion_committee``
* If an adapter is attached           → ``adapter_agent``
* Otherwise                            → ``single_agent``

The function also surfaces a confidence score and a list of reason
codes so the Workbench can render the decision transparently.
"""

from __future__ import annotations

from typing import Iterable

from loopos.opengod.models import OpenGodContext, OpenGodDecision, OpenGodDecisionKind


# Order of preference — first match wins.
_DEFAULT_RULES: tuple[tuple[str, OpenGodDecisionKind], ...] = (
    ("hard_fail_present", "halt"),
    ("readiness_failed", "halt"),
    ("replay_failed", "needs_repair"),
    ("replay_unknown", "needs_replan"),
    ("fusion_mad_dog", "mad_dog"),
    ("fusion_committee", "fusion_committee"),
    ("fusion_pair", "fusion_pair"),
    ("no_budget", "ask_user"),
    ("adapter_present", "adapter_agent"),
)


def decide(
    context: OpenGodContext,
    *,
    rules: Iterable[tuple[str, OpenGodDecisionKind]] | None = None,
) -> OpenGodDecision:
    """Pick a decision for the given context."""
    active_rules = tuple(rules) if rules is not None else _DEFAULT_RULES
    reason_codes: list[str] = []
    rationale_parts: list[str] = []
    chosen: OpenGodDecisionKind = "single_agent"
    confidence = 0.5

    for rule_id, kind in active_rules:
        if _rule_matches(rule_id, context, reason_codes, rationale_parts):
            chosen = kind
            confidence = _confidence_for(kind, context)
            break
    else:
        rationale_parts.append("no rule matched → default single_agent")

    rationale = "; ".join(rationale_parts) if rationale_parts else "default single_agent"
    return OpenGodDecision(
        goal_id=context.goal_id,
        kind=chosen,
        confidence=confidence,
        reason_codes=reason_codes,
        rationale=rationale,
    )


def _rule_matches(
    rule_id: str,
    context: OpenGodContext,
    reason_codes: list[str],
    rationale_parts: list[str],
) -> bool:
    if rule_id == "hard_fail_present":
        if context.hard_fail_count > 0:
            reason_codes.append("hard_fail_present")
            rationale_parts.append("readiness hard-fail detected")
            return True
        return False
    if rule_id == "readiness_failed":
        if context.readiness_status == "fail":
            reason_codes.append("readiness_failed")
            rationale_parts.append("readiness.status=fail")
            return True
        return False
    if rule_id == "replay_failed":
        if context.replay_status == "fail":
            reason_codes.append("replay_failed")
            rationale_parts.append("replay.status=fail")
            return True
        return False
    if rule_id == "replay_unknown":
        # When replay has been explicitly *skipped* we cannot safely
        # proceed to mutate; ask the planner to replan from a known
        # baseline. We do NOT treat ``unknown`` as a trigger here:
        # ``unknown`` is the default for a fresh context that has
        # not run replay, and the caller has not asked for replay
        # to run. ``fail`` is already handled by ``replay_failed``.
        if context.replay_status == "skipped":
            reason_codes.append("replay_skipped")
            rationale_parts.append("replay.status=skipped")
            return True
        return False
    if rule_id == "no_budget":
        # If the agent wants to spend but no budget is configured
        # at all, we must ask the human for a budget rather than
        # silently go live.
        if context.live_provider_calls and context.budget_max_usd <= 0:
            reason_codes.append("no_budget")
            rationale_parts.append("budget_max_usd<=0 with live_provider_calls")
            return True
        return False
    if rule_id == "fusion_mad_dog":
        if context.fusion_mode == "mad_dog":
            reason_codes.append("fusion_mad_dog")
            rationale_parts.append("fusion.mode=mad_dog")
            return True
        return False
    if rule_id == "fusion_committee":
        if context.fusion_mode == "committee":
            reason_codes.append("fusion_committee")
            rationale_parts.append("fusion.mode=committee")
            return True
        return False
    if rule_id == "fusion_pair":
        if context.fusion_mode == "pair":
            reason_codes.append("fusion_pair")
            rationale_parts.append("fusion.mode=pair")
            return True
        return False
    if rule_id == "adapter_present":
        if context.adapter_id:
            reason_codes.append("adapter_present")
            rationale_parts.append(f"adapter_id={context.adapter_id}")
            return True
        return False
    return False


def _confidence_for(kind: OpenGodDecisionKind, context: OpenGodContext) -> float:
    base = {
        "single_agent": 0.5,
        "adapter_agent": 0.6,
        "fusion_pair": 0.7,
        "fusion_committee": 0.75,
        "mad_dog": 0.9,
        "ask_user": 0.4,
        "halt": 0.95,
        "needs_repair": 0.85,
        "needs_replan": 0.7,
    }.get(kind, 0.5)
    # Penalise confidence when live provider calls are happening.
    if context.live_provider_calls and kind in ("mad_dog", "fusion_committee", "fusion_pair"):
        base -= 0.2
    return max(0.0, min(1.0, base))


__all__ = ["decide"]

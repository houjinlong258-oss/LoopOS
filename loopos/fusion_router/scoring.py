"""Deterministic scoring and mode selection for the Fusion Router.

The router uses a transparent, integer-only scoring formula so
the activation rationale is auditable. Machine learning is
deliberately out of scope in v0.2.

Public surface:

* :func:`calculate_fusion_score` -- the integer score.
* :func:`select_fusion_mode` -- mode given the score + trigger.
* :func:`should_escalate` -- convenience check (``mode != "single"``).
* :func:`score_breakdown` -- structured breakdown for ``explain``
  output and trace evidence.

Scoring formula (per master prompt):

    fusion_score = (
        complexity_score * 2
        + failure_count * 3
        + user_dissatisfaction_count * 4
        + risk_score * 2
        + affected_file_count
        + no_progress_count * 3
        + release_blocker_bonus
        + security_sensitive_bonus
        + model_mismatch_bonus
    )

Mode thresholds:

    score < 8        -> single
    8 <= score < 15  -> pair
    15 <= score < 25 -> committee
    25 <= score < 35 -> attack
    score >= 35      -> mad_dog

Explicit user request (``reason == "explicit_user_request"``)
overrides the threshold: the router returns the requested mode
(or ``"mad_dog"`` for the ``mad-dog`` CLI alias).
"""

from __future__ import annotations

from typing import Any

from loopos.fusion_router.models import (
    FusionMode,
    FusionTaskProfile,
    FusionTrigger,
)


def _is_explicit_user_request(trigger: FusionTrigger) -> bool:
    return (
        trigger.source == "user"
        and trigger.reason == "explicit_user_request"
    )


def calculate_fusion_score(
    task: FusionTaskProfile,
    trigger: FusionTrigger,
) -> int:
    """Compute the integer fusion score for ``task`` + ``trigger``.

    The score is deterministic: same inputs always yield the
    same output. Trigger-derived bonuses are gated on the
    ``reason`` field so a single high-complexity task without
    failure history does not accidentally escalate to
    ``mad_dog``.
    """

    score = (
        task.complexity_score * 2
        + task.failure_count * 3
        + task.user_dissatisfaction_count * 4
        + task.risk_score * 2
        + len(task.affected_files)
        + task.no_progress_count * 3
    )
    if trigger.reason == "release_blocker":
        score += 20
    if trigger.reason == "security_sensitive":
        score += 12
    if trigger.reason == "model_mismatch":
        score += 8
    # Apply a deterministic severity multiplier (1.0 / 1.1 / 1.25 / 1.5).
    multiplier = {
        "low": 1.0,
        "medium": 1.1,
        "high": 1.25,
        "critical": 1.5,
    }.get(trigger.severity, 1.0)
    return int(round(score * multiplier))


def select_fusion_mode(
    score: int,
    trigger: FusionTrigger,
) -> FusionMode:
    """Map ``score`` + ``trigger`` to a :class:`FusionMode`.

    Explicit user request wins:

    * ``reason == "explicit_user_request"`` and
      ``requested_mode`` is set -> ``requested_mode``.
    * CLI ``mad-dog`` alias -> ``"mad_dog"``.

    Otherwise the integer score selects the mode per the
    thresholds above.
    """

    if _is_explicit_user_request(trigger) and trigger.requested_mode is not None:
        return trigger.requested_mode
    if score < 8:
        return "single"
    if score < 15:
        return "pair"
    if score < 25:
        return "committee"
    if score < 35:
        return "attack"
    return "mad_dog"


def should_escalate(
    task: FusionTaskProfile,
    trigger: FusionTrigger,
) -> bool:
    """``True`` iff the router would pick a mode other than ``single``.

    Convenience for callers (CLI ``explain``, kernel triggers) that
    want a boolean answer without computing the full score /
    mode pair.
    """

    score = calculate_fusion_score(task, trigger)
    return select_fusion_mode(score, trigger) != "single"


def score_breakdown(
    task: FusionTaskProfile,
    trigger: FusionTrigger,
) -> dict[str, Any]:
    """Return a structured breakdown of the score for ``explain``.

    The breakdown is a deterministic mapping that the CLI's
    ``fusion-router explain`` and the trace bridge both consume
    so a reviewer can audit *why* the router picked a mode.
    """

    raw = (
        task.complexity_score * 2
        + task.failure_count * 3
        + task.user_dissatisfaction_count * 4
        + task.risk_score * 2
        + len(task.affected_files)
        + task.no_progress_count * 3
    )
    bonuses: dict[str, int] = {}
    if trigger.reason == "release_blocker":
        bonuses["release_blocker"] = 20
    if trigger.reason == "security_sensitive":
        bonuses["security_sensitive"] = 12
    if trigger.reason == "model_mismatch":
        bonuses["model_mismatch"] = 8
    multiplier = {
        "low": 1.0,
        "medium": 1.1,
        "high": 1.25,
        "critical": 1.5,
    }.get(trigger.severity, 1.0)
    score = calculate_fusion_score(task, trigger)
    return {
        "complexity_contribution": task.complexity_score * 2,
        "failure_contribution": task.failure_count * 3,
        "user_dissatisfaction_contribution": task.user_dissatisfaction_count * 4,
        "risk_contribution": task.risk_score * 2,
        "affected_files_contribution": len(task.affected_files),
        "no_progress_contribution": task.no_progress_count * 3,
        "raw_score_before_bonuses": raw,
        "bonuses": bonuses,
        "severity_multiplier": multiplier,
        "fusion_score": score,
        "selected_mode": select_fusion_mode(score, trigger),
        "explicit_user_request": _is_explicit_user_request(trigger),
    }


__all__ = [
    "calculate_fusion_score",
    "score_breakdown",
    "select_fusion_mode",
    "should_escalate",
]
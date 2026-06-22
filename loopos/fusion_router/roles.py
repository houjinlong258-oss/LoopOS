"""Role assignment for the Fusion Router.

The router maps :class:`FusionRole` slots to
:class:`ModelCapabilityProfile` instances through a deterministic
score function. Roles never bypass the existing
:mod:`loopos.providers` registry; the router asks the registry
for a list of provider profiles, derives a
:class:`ModelCapabilityProfile` for each (with conservative
fallback when a registry profile lacks a particular score), and
picks the best candidate per role.

Layering:

* :func:`required_roles_for_mode` -- returns the canonical role
  set for a given (mode, task_type, trigger) triple, with
  task-type adjustments per the master prompt.
* :func:`capability_profile_from_provider` -- builds a
  :class:`ModelCapabilityProfile` from a registry
  :class:`ModelProviderProfile`. Conservative defaults keep
  unknown fields at 5 (out of 10) so the score is never
  undefined.
* :func:`score_role_for_profile` -- per-role deterministic
  score (0.0-1.0) of a capability profile.
* :func:`assign_roles` -- orchestrates the role-to-profile
  matching with deterministic tie-breakers.
"""

from __future__ import annotations

from typing import Any

from loopos.fusion_router.models import (
    FUSION_ROLES,
    FusionMode,
    FusionRole,
    FusionRoleAssignment,
    FusionTaskProfile,
    FusionTrigger,
    FusionTriggerReason,
    ModelCapabilityProfile,
)


# ---------------------------------------------------------------------------
# Mode -> role matrix
# ---------------------------------------------------------------------------

_MODE_ROLES: dict[FusionMode, tuple[FusionRole, ...]] = {
    "single": ("primary",),
    "pair": ("coder", "reviewer"),
    "committee": ("planner", "coder", "reviewer"),
    "attack": (
        "planner",
        "coder",
        "bug_hunter",
        "test_breaker",
        "judge",
    ),
    "mad_dog": (
        "planner",
        "architect",
        "bug_hunter",
        "coder",
        "test_breaker",
        "security_guard",
        "simplifier",
        "reviewer",
        "judge",
        "summarizer",
    ),
}


# Task-type adjustments. The adjustments are additive: the base
# role set is augmented (never replaced) by the task-type-specific
# roles.
_TASK_TYPE_ROLES: dict[str, tuple[FusionRole, ...]] = {
    "security": ("security_guard",),
    "refactor": ("architect", "simplifier"),
    "bugfix": ("bug_hunter", "test_breaker"),
    "debugging": ("bug_hunter", "test_breaker"),
    "release": ("security_guard", "reviewer", "summarizer"),
    "audit": ("reviewer", "judge"),
    "architecture": ("architect", "simplifier"),
    "test_repair": ("test_breaker", "bug_hunter"),
}


# Trigger-driven forced roles.
_TRIGGER_FORCED_ROLES: dict[FusionTriggerReason, tuple[FusionRole, ...]] = {
    "user_dissatisfaction": ("reviewer", "judge", "summarizer"),
    "repeated_failure": ("bug_hunter", "test_breaker"),
    "no_progress": ("reviewer", "judge"),
    "security_sensitive": ("security_guard",),
    "release_blocker": ("security_guard", "reviewer", "judge"),
}


def required_roles_for_mode(
    mode: FusionMode,
    task_type: str | None = None,
    trigger: FusionTrigger | None = None,
) -> tuple[FusionRole, ...]:
    """Return the ordered role set for ``mode`` (with task-type adjustments).

    The result preserves the base mode order first, then appends
    the task-type and trigger-forced roles in declaration order.
    The deduplication preserves first occurrence.
    """

    roles: list[FusionRole] = list(_MODE_ROLES[mode])
    if task_type:
        for role in _TASK_TYPE_ROLES.get(task_type, ()):
            if role not in roles:
                roles.append(role)
    if trigger is not None:
        for role in _TRIGGER_FORCED_ROLES.get(trigger.reason, ()):
            if role not in roles:
                roles.append(role)
    # Validate against the canonical taxonomy so a future task_type
    # string cannot smuggle in an unknown role.
    for role in roles:
        if role not in FUSION_ROLES:
            raise ValueError(f"unknown role: {role!r}")
    return tuple(roles)


# ---------------------------------------------------------------------------
# Capability scoring
# ---------------------------------------------------------------------------


def capability_profile_from_provider(
    profile: Any,
    *,
    model_id: str | None = None,
) -> ModelCapabilityProfile:
    """Derive a :class:`ModelCapabilityProfile` from a registry profile.

    The registry's :class:`loopos.providers.ModelProviderProfile`
    is metadata-only. When a particular score is not available
    on the source profile, the router falls back to conservative
    defaults (5 out of 10 for capability scores, ``False`` for
    feature flags unless the source profile advertises them).
    """

    # Best-effort field reads. The registry profile does not yet
    # carry granular score fields, so the router treats
    # ``capability_hints.capabilities`` as evidence for tools /
    # json / long_context support.
    capabilities = set(getattr(getattr(profile, "capability_hints", None), "capabilities", []) or ())
    supports_tools = bool(capabilities & {"tools", "function_calling", "tool_use"})
    supports_json = bool(capabilities & {"json", "json_mode", "structured_output"})
    supports_long_context = bool(capabilities & {"long_context", "extended_context"})
    return ModelCapabilityProfile(
        provider_id=profile.provider_id,
        model_id=model_id or profile.provider_id,
        reasoning_score=5,
        coding_score=5,
        review_score=5,
        debugging_score=5,
        architecture_score=5,
        security_score=5,
        test_generation_score=5,
        context_score=5,
        speed_score=5,
        cost_score=5,
        reliability_score=5,
        supports_tools=supports_tools,
        supports_json=supports_json,
        supports_long_context=supports_long_context,
        local_only=bool(getattr(profile, "kind", None) == "local_only" or getattr(profile, "local_only", False)),
    )


def score_role_for_profile(
    role: FusionRole,
    profile: ModelCapabilityProfile,
) -> tuple[float, list[str]]:
    """Return ``(score, capability_gaps)`` for ``role`` on ``profile``.

    The score is in ``[0.0, 1.0]``. The capability gaps are the
    list of attribute names the profile lacks for the role (so
    :class:`FusionRoleAssignment` can record them transparently).
    """

    score_table: dict[FusionRole, tuple[str, ...]] = {
        "primary": ("reasoning_score",),
        "planner": ("reasoning_score", "architecture_score"),
        "architect": ("architecture_score", "context_score"),
        "coder": ("coding_score",),
        "bug_hunter": ("debugging_score", "reasoning_score"),
        "test_breaker": ("test_generation_score", "review_score"),
        "reviewer": ("review_score", "reasoning_score"),
        "security_guard": ("security_score", "review_score"),
        "simplifier": ("review_score", "coding_score"),
        "judge": ("reasoning_score", "review_score", "reliability_score"),
        "summarizer": ("speed_score", "coding_score"),
    }
    required = score_table[role]
    gaps: list[str] = []
    total = 0.0
    for attr in required:
        value = getattr(profile, attr, None)
        if value is None or value <= 3:
            gaps.append(attr)
        total += float(value or 0)
    score = (total / (10 * len(required))) if required else 0.0
    # Feature gates: tools / json / long_context are bonuses.
    if role in {"coder", "bug_hunter"} and not profile.supports_tools:
        score -= 0.05
    if role == "reviewer" and not profile.supports_json:
        score -= 0.05
    if role == "architect" and not profile.supports_long_context:
        score -= 0.05
    # Clamp.
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return score, gaps


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


def _deterministic_tie_break_key(
    profile: ModelCapabilityProfile,
) -> tuple[str, str]:
    """Return the deterministic tie-breaker key for ``profile``.

    Lower is better. We sort by ``provider_id`` then ``model_id``
    so identical-score candidates are resolved deterministically
    per the master prompt's tie-breaker rules.
    """

    return (profile.provider_id, profile.model_id)


def assign_roles(
    task: FusionTaskProfile,
    mode: FusionMode,
    profiles: list[ModelCapabilityProfile],
    *,
    trigger: FusionTrigger | None = None,
) -> list[FusionRoleAssignment]:
    """Assign roles for ``mode`` to the supplied capability profiles.

    Roles that the registry cannot honour degrade gracefully:
    the router picks the best available profile and records the
    missing capabilities in ``capability_gaps``. The role set
    never grows beyond the (mode, task_type, trigger) derivation
    in :func:`required_roles_for_mode`.
    """

    roles = required_roles_for_mode(mode, task_type=task.task_type, trigger=trigger)
    assignments: list[FusionRoleAssignment] = []
    used_providers: set[tuple[str, str]] = set()
    # Budget weights: equally distributed, last role gets the
    # remainder so the sum equals 1.0.
    if not roles:
        return assignments
    weight_base = 1.0 / len(roles)
    for index, role in enumerate(roles):
        candidates = [
            (profile, *score_role_for_profile(role, profile))
            for profile in profiles
        ]
        # Sort: highest score first, then deterministic tie-break.
        candidates.sort(
            key=lambda item: (
                -item[1],
                _deterministic_tie_break_key(item[0]),
            ),
        )
        # Prefer a candidate whose (provider_id, model_id) we have
        # not yet used so a single provider can fill multiple roles
        # only when no alternative exists.
        chosen = None
        for profile, score, gaps in candidates:
            key = (profile.provider_id, profile.model_id)
            if key in used_providers:
                continue
            chosen = (profile, score, gaps)
            used_providers.add(key)
            break
        if chosen is None and candidates:
            # Degrade gracefully: reuse the highest-scoring profile.
            profile, score, gaps = candidates[0]
            new_gaps = list(gaps) + ["provider_reused"]
            chosen = (profile, score, new_gaps)
        if chosen is None:
            # No providers at all. Record an empty assignment with
            # ``provider_id=""`` so downstream review can flag the
            # capability gap.
            assignments.append(
                FusionRoleAssignment(
                    role=role,
                    provider_id="",
                    model_id=None,
                    capability_score=0.0,
                    reason="no providers available",
                    budget_weight=weight_base,
                    capability_gaps=["no_providers_available"],
                ),
            )
            continue
        profile, score, gaps = chosen
        weight = weight_base if index < len(roles) - 1 else max(
            0.0, 1.0 - weight_base * (len(roles) - 1)
        )
        assignments.append(
            FusionRoleAssignment(
                role=role,
                provider_id=profile.provider_id,
                model_id=profile.model_id,
                capability_score=round(score, 4),
                reason=f"best score={round(score, 3)} for role={role!r}",
                budget_weight=round(weight, 4),
                capability_gaps=gaps,
            ),
        )
    return assignments


__all__ = [
    "assign_roles",
    "capability_profile_from_provider",
    "required_roles_for_mode",
    "score_role_for_profile",
]
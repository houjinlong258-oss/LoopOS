"""Policy conflict resolution."""

from __future__ import annotations

from loopos.policy_os.models import PolicyActionType, PolicyDecision, PolicyRule, PolicySeverity

ACTION_ORDER: dict[PolicyActionType, int] = {
    "allow": 0,
    "prefer_tool": 1,
    "modify": 2,
    "require_review": 3,
    "require_approval": 4,
    "deny": 5,
}
SEVERITY_ORDER: dict[PolicySeverity, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def resolve_policy_conflicts(matched_rules: list[PolicyRule]) -> PolicyDecision:
    """Resolve matched rules into one deterministic decision."""

    if not matched_rules:
        return PolicyDecision(allowed=True, action="allow", reason_codes=["policy.default_allow"])

    actions = [
        (rule, action)
        for rule in sorted(matched_rules, key=lambda item: item.priority, reverse=True)
        for action in rule.actions
    ]
    if not actions:
        return PolicyDecision(
            allowed=True,
            action="allow",
            severity=_max_severity(matched_rules),
            matched_rules=[rule.id for rule in matched_rules],
            reason_codes=["policy.no_action_allow"],
        )

    primary_rule, primary_action = max(
        actions,
        key=lambda pair: (ACTION_ORDER[pair[1].type], pair[0].priority),
    )
    constraints: dict[str, object] = {}
    tool_preferences: dict[str, object] = {}
    memory_filters: dict[str, object] = {}
    render_hints: dict[str, object] = {}
    reason_codes: list[str] = []
    audit_required = False
    safety_levels: list[str] = []
    human_only = False
    rollback_required = False

    for _, action in actions:
        reason_codes.append(action.reason_code)
        constraints.update(action.constraints)
        tool_preferences.update(action.tool_preferences)
        memory_filters.update(action.memory_filters)
        render_hints.update(action.render_hints)
        audit_required = audit_required or action.audit_required
        if action.safety_level:
            safety_levels.append(action.safety_level)
        human_only = human_only or action.human_only
        rollback_required = rollback_required or action.rollback_required

    action_type = primary_action.type
    return PolicyDecision(
        allowed=action_type in {"allow", "modify", "prefer_tool"},
        action=action_type,
        risk=_risk_for_action(action_type),
        requires_approval=action_type in {"require_approval", "require_review"},
        severity=max(_max_severity(matched_rules), primary_rule.severity, key=lambda value: SEVERITY_ORDER[value]),
        reason_codes=_dedupe(reason_codes),
        constraints=constraints,
        tool_preferences=tool_preferences,
        memory_filters=memory_filters,
        render_hints=render_hints,
        audit_required=audit_required,
        matched_rules=[rule.id for rule in matched_rules],
        safety_level=max(safety_levels, key=_safety_rank, default="L0"),  # type: ignore[arg-type]
        human_only=human_only,
        rollback_required=rollback_required,
    )


def _risk_for_action(action: PolicyActionType) -> str:
    if action == "deny":
        return "blocked"
    if action == "require_approval":
        return "high"
    if action == "require_review":
        return "medium"
    return "low"


def _max_severity(rules: list[PolicyRule]) -> PolicySeverity:
    return max((rule.severity for rule in rules), key=lambda value: SEVERITY_ORDER[value], default="info")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _safety_rank(value: str) -> int:
    return int(value[1:]) if len(value) == 2 and value.startswith("L") else 0

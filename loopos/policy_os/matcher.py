"""Policy matching primitives."""

from __future__ import annotations

import re
from typing import Any

from loopos.policy_os.models import PolicyCondition, PolicyRequest, PolicyRule

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "blocked": 3}


def matches_rule(rule: PolicyRule, request: PolicyRequest) -> bool:
    """Return whether a rule applies to a request."""

    if not rule.enabled or rule.scope != request.scope:
        return False
    return all(matches_condition(condition, request) for condition in rule.conditions)


def matches_condition(condition: PolicyCondition, request: PolicyRequest) -> bool:
    """Evaluate a policy condition."""

    if condition.all:
        return all(matches_condition(child, request) for child in condition.all)
    if condition.any:
        return any(matches_condition(child, request) for child in condition.any)
    if not condition.field:
        return True

    actual = _get_value(request, condition.field)
    expected = condition.value
    operator = condition.operator

    if operator == "exists":
        return actual is not None
    if operator == "equals":
        return bool(actual == expected)
    if operator == "not_equals":
        return bool(actual != expected)
    if operator == "contains":
        if isinstance(actual, str):
            return str(expected) in actual
        if isinstance(actual, (list, tuple, set)):
            return expected in actual
        return False
    if operator == "regex":
        return isinstance(actual, str) and re.search(str(expected), actual, re.IGNORECASE) is not None
    if operator == "in":
        return isinstance(expected, (list, tuple, set)) and actual in expected
    if operator == "risk_at_least":
        return RISK_ORDER.get(str(actual), -1) >= RISK_ORDER.get(str(expected), 99)
    if operator in {"lt", "lte", "gt", "gte"}:
        return _compare_number(actual, expected, operator)
    return False


def _get_value(request: PolicyRequest, field: str) -> Any:
    if field.startswith("subject."):
        field = field.removeprefix("subject.")
        value: Any = request.subject
        for part in field.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value
    if hasattr(request, field):
        return getattr(request, field)
    subject_value: Any = request.subject
    for part in field.split("."):
        if isinstance(subject_value, dict) and part in subject_value:
            subject_value = subject_value[part]
        else:
            return None
    return subject_value


def _compare_number(actual: Any, expected: Any, operator: str) -> bool:
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError):
        return False
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    if operator == "gt":
        return left > right
    return left >= right

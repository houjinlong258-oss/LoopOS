"""Result-builder helpers for the ACI runner.

This module owns the small pure helper functions that the runner
uses to extract structured data from a :class:`PolicyDecision`:

* :func:`format_decision_reason` - format a human-readable
  ``policy <action>: <reason_codes>`` string.
* :func:`policy_reason_code` - return the first stable reason code
  from a :class:`PolicyDecision`, with a caller-supplied fallback.

The helpers are deliberately tiny and pure: they only read fields
off the decision and return plain values. The runner uses them in
both :meth:`CommandRunner._materialize` (which assembles a failure
or approval-required :class:`AgentCommandResult`) and
:meth:`CommandRunner._blocked_result` (which short-circuits a
command before dispatch).

Public name ``format_decision_reason`` / ``policy_reason_code`` are
the canonical entry points; the legacy underscore-prefixed names
remain as backward-compat aliases for callers inside the package.
"""

from __future__ import annotations

from loopos.policy_os.models import PolicyDecision


def format_decision_reason(decision: PolicyDecision) -> str:
    """Return a human-readable summary of a :class:`PolicyDecision`.

    The output is ``"policy <action>"`` when no reason codes are
    available, and ``"policy <action>: <code1>, <code2>, ..."``
    otherwise. The string is suitable for inclusion in
    :attr:`AgentCommandResult.blocked_reason` and in log messages.
    """

    codes = list(decision.reason_codes) or list(decision.all_reason_codes)
    if not codes:
        return f"policy {decision.action}"
    return f"policy {decision.action}: {', '.join(codes)}"


def policy_reason_code(decision: PolicyDecision, fallback: str) -> str:
    """Return the first stable reason code from a :class:`PolicyDecision`.

    Iterates ``decision.reason_codes`` first, then
    ``decision.all_reason_codes``. Returns ``fallback`` when the
    decision carries no codes. Used by the runner to populate the
    top-level :attr:`AgentCommandResult.reason_codes` field.
    """

    for code in decision.reason_codes:
        if code:
            return code
    for code in decision.all_reason_codes:
        if code:
            return code
    return fallback


# ---------------------------------------------------------------------------
# Backward-compat aliases. The original runner used the
# underscore-prefixed private names ``_format_decision_reason`` and
# ``_policy_reason_code``; keep them so internal callers (and tests
# that reach for the private name) keep working unchanged.
# ---------------------------------------------------------------------------

_format_decision_reason = format_decision_reason
_policy_reason_code = policy_reason_code


__all__ = [
    "format_decision_reason",
    "policy_reason_code",
]
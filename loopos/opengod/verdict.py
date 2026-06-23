"""OpenGod verdict builder.

The :func:`build_verdict` function turns a decision into an actionable
verdict. The verdict is a structured read-only object — it contains
*no* commands and *no* side-effect instructions. The next-action
string is human-readable and is meant for the Workbench UI.
"""

from __future__ import annotations

from loopos.opengod.models import (
    OpenGodDecision,
    OpenGodDecisionKind,
    OpenGodVerdict,
    OpenGodVerdictStatus,
)


_NEXT_ACTION: dict[OpenGodDecisionKind, str] = {
    "single_agent": "Run goal through a single native agent session",
    "adapter_agent": "Run goal through the selected adapter session",
    "fusion_pair": "Escalate to fusion_pair (planner + coder)",
    "fusion_committee": "Escalate to fusion_committee (multi-vote)",
    "mad_dog": "Escalate to mad_dog (explicit user request)",
    "ask_user": "Wait for user input; show ask_user prompt",
    "halt": "Stop; do not dispatch further commands",
    "needs_repair": "Submit repair.plan and enter ALI REPAIRING",
    "needs_replan": "Submit goal.replan and enter ALI REPLANNING",
}


_STATUS_FOR: dict[OpenGodDecisionKind, OpenGodVerdictStatus] = {
    "single_agent": "ok",
    "adapter_agent": "ok",
    "fusion_pair": "ok",
    "fusion_committee": "ok",
    "mad_dog": "ok",
    "ask_user": "ask_user",
    "halt": "halted",
    "needs_repair": "needs_repair",
    "needs_replan": "needs_replan",
}


def build_verdict(decision: OpenGodDecision) -> OpenGodVerdict:
    """Wrap an :class:`OpenGodDecision` in an :class:`OpenGodVerdict`."""
    status = _STATUS_FOR.get(decision.kind, "ok")
    blocked = decision.kind in ("halt", "ask_user")
    return OpenGodVerdict(
        status=status,
        decision=decision,
        next_action=_NEXT_ACTION.get(decision.kind, ""),
        blocked=blocked,
        reason_codes=list(decision.reason_codes),
    )


__all__ = ["build_verdict"]

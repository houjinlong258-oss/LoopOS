"""AIL validation helpers."""

from __future__ import annotations

from loopos.ail.models import AILInstruction


def validate_ail_instruction(instruction: AILInstruction) -> list[str]:
    """Return contract violations for an AIL instruction."""

    issues: list[str] = []
    if instruction.expected_observation is None:
        issues.append("expected_observation is required")

    if instruction.op == "EXEC_TERMINAL":
        command = instruction.args.get("cmd")
        if not isinstance(command, str) or not command.strip():
            issues.append("EXEC_TERMINAL requires args.cmd")
        if not instruction.metadata.get("policy_scope") and not instruction.metadata.get("policy_decision"):
            issues.append("EXEC_TERMINAL requires policy metadata")

    if instruction.op == "CALL_TOOL":
        tool = instruction.args.get("tool")
        if not isinstance(tool, str) or not tool.strip():
            issues.append("CALL_TOOL requires args.tool")
        arguments = instruction.args.get("arguments")
        if arguments is not None and not isinstance(arguments, dict):
            issues.append("CALL_TOOL args.arguments must be an object")
        if not instruction.metadata.get("routing") and not instruction.metadata.get("policy_scope"):
            issues.append("CALL_TOOL requires routing or policy metadata")

    if instruction.op == "STORE_MEMORY":
        has_proposal = any(key in instruction.args for key in ("proposal", "proposal_id", "request"))
        if "item" in instruction.args and not has_proposal:
            issues.append("STORE_MEMORY must use a proposal or explicit write request")

    if instruction.safety.risk_level == "blocked" and not instruction.safety.requires_approval:
        issues.append("blocked risk_level requires approval metadata")

    return issues

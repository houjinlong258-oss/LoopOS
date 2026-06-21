"""Human-readable report formatter for MaintainabilityReport."""

from __future__ import annotations

import json

from loopos.maintainability.models import MaintainabilityReport, MaintainabilityGateDecision


def render_report_text(report: MaintainabilityReport) -> str:
    """Render a MaintainabilityReport as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  Maintainability Report")
    lines.append("=" * 60)
    lines.append(f"  Run:            {report.run_id or 'N/A'}")
    lines.append(f"  Changed files:  {len(report.changed_files)}")
    lines.append(f"  Score:          {report.score:.0f} / 100")
    lines.append(f"  Risk:           {report.risk_level.upper()}")
    lines.append(f"  Recommendation: {report.recommendation.replace('_', ' ').upper()}")
    lines.append("-" * 60)

    if report.findings:
        lines.append("  Findings:")
        for finding in report.findings:
            icon = _severity_icon(finding.severity)
            location = ""
            if finding.file:
                location = f" ({finding.file}"
                if finding.line:
                    location += f":{finding.line}"
                location += ")"
            lines.append(f"    {icon} [{finding.category}]{location}")
            lines.append(f"      {finding.message}")
            if finding.suggested_fix:
                lines.append(f"      Fix: {finding.suggested_fix}")
        lines.append("-" * 60)

    lines.append("  Risk breakdown:")
    lines.append(f"    Duplication:     {_bar(report.duplication_risk)}")
    lines.append(f"    Complexity:      {_bar(report.complexity_risk)}")
    lines.append(f"    Boundary:        {_bar(report.boundary_risk)}")
    lines.append(f"    Test quality:    {_bar(report.test_quality_risk)}")
    lines.append(f"    Documentation:   {_bar(report.documentation_risk)}")
    lines.append(f"    Policy bypass:   {_bar(report.policy_bypass_risk)}")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_gate_text(decision: MaintainabilityGateDecision) -> str:
    """Render a MaintainabilityGateDecision as human-readable text."""
    lines: list[str] = []
    status = "ALLOWED" if decision.allowed_to_continue else "BLOCKED"
    lines.append("=" * 60)
    lines.append(f"  Maintainability Gate: {status}")
    lines.append("=" * 60)
    lines.append(f"  Report:          {decision.report_id}")
    lines.append(f"  Allowed:         {decision.allowed_to_continue}")
    lines.append(f"  Blocks merge:    {decision.blocks_merge}")
    lines.append(f"  Needs refactor:  {decision.requires_refactor}")
    lines.append(f"  Human review:    {decision.requires_human_review}")

    if decision.reason_codes:
        lines.append("  Reasons:")
        for code in decision.reason_codes:
            lines.append(f"    - {code}")

    if decision.required_actions:
        lines.append("  Required actions:")
        for action in decision.required_actions:
            lines.append(f"    - {action}")

    lines.append("=" * 60)
    return "\n".join(lines)


def render_report_json(report: MaintainabilityReport) -> str:
    """Render a MaintainabilityReport as machine-readable JSON."""
    return json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)


def render_gate_json(decision: MaintainabilityGateDecision) -> str:
    """Render a MaintainabilityGateDecision as machine-readable JSON."""
    return json.dumps(decision.model_dump(mode="json"), indent=2, ensure_ascii=False)


def _severity_icon(severity: str) -> str:
    return {
        "info": "ℹ",
        "warning": "⚠",
        "error": "✗",
        "blocker": "⛔",
    }.get(severity, "?")


def _bar(value: float) -> str:
    """Render a simple risk bar."""
    filled = int(value * 10)
    return "█" * filled + "░" * (10 - filled) + f" {value:.0%}"

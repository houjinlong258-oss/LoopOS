"""Human-readable report formatter for MaintainabilityReport."""

from __future__ import annotations

import json

from loopos.maintainability.models import (
    MaintainabilityGateDecision,
    MaintainabilityReport,
)


def render_report_text(report: MaintainabilityReport) -> str:
    """Render a MaintainabilityReport as product-quality terminal text."""

    lines: list[str] = [
        "LoopOS Maintainability Review",
        "=" * 72,
        f"Run:             {report.run_id or 'N/A'}",
        f"Changed files:   {len(report.changed_files)}",
        f"Diff parse:      {report.parse_status}",
        f"Score:           {report.score:.0f} / 100",
        f"Risk:            {report.risk_level.upper()}",
        f"Recommendation:  {report.recommendation.replace('_', ' ').upper()}",
        "-" * 72,
    ]

    if report.findings:
        lines.append("Findings")
        for finding in report.findings:
            marker = _severity_marker(finding.severity)
            location = ""
            if finding.file:
                location = f" ({finding.file}"
                if finding.line:
                    location += f":{finding.line}"
                location += ")"
            lines.append(f"  [{marker}] {finding.category}{location}")
            lines.append(f"        {finding.message}")
            if finding.suggested_fix:
                lines.append(f"        Fix: {finding.suggested_fix}")
            if finding.evidence:
                lines.append(f"        Evidence: {', '.join(finding.evidence[:5])}")
        lines.append("-" * 72)

    lines.extend(
        [
            "Risk breakdown",
            f"  Duplication:    {_bar(report.duplication_risk)}",
            f"  Complexity:     {_bar(report.complexity_risk)}",
            f"  Boundary:       {_bar(report.boundary_risk)}",
            f"  Test quality:   {_bar(report.test_quality_risk)}",
            f"  Documentation:  {_bar(report.documentation_risk)}",
            f"  Policy bypass:  {_bar(report.policy_bypass_risk)}",
            "=" * 72,
        ]
    )
    return "\n".join(lines)


def render_gate_text(decision: MaintainabilityGateDecision) -> str:
    """Render a MaintainabilityGateDecision as human-readable text."""

    status = "ALLOWED" if decision.allowed_to_continue else "BLOCKED"
    lines: list[str] = [
        "LoopOS Maintainability Gate",
        "=" * 72,
        f"Status:          {status}",
        f"Report:          {decision.report_id}",
        f"Allowed:         {decision.allowed_to_continue}",
        f"Blocks merge:    {decision.blocks_merge}",
        f"Needs refactor:  {decision.requires_refactor}",
        f"Human review:    {decision.requires_human_review}",
    ]

    if decision.reason_codes:
        lines.append("Reasons")
        for code in decision.reason_codes:
            lines.append(f"  - {code}")

    if decision.required_actions:
        lines.append("Required actions")
        for action in decision.required_actions:
            lines.append(f"  - {action}")

    lines.append("=" * 72)
    return "\n".join(lines)


def render_report_json(report: MaintainabilityReport) -> str:
    """Render a MaintainabilityReport as machine-readable JSON."""

    return json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)


def render_gate_json(decision: MaintainabilityGateDecision) -> str:
    """Render a MaintainabilityGateDecision as machine-readable JSON."""

    return json.dumps(decision.model_dump(mode="json"), indent=2, ensure_ascii=False)


def _severity_marker(severity: str) -> str:
    return {
        "info": "INFO",
        "warning": "WARN",
        "error": "ERROR",
        "blocker": "BLOCK",
    }.get(severity, "INFO")


def _bar(value: float) -> str:
    """Render a simple ASCII risk bar."""

    filled = max(0, min(10, int(round(value * 10))))
    return "[" + "#" * filled + "." * (10 - filled) + f"] {value:.0%}"

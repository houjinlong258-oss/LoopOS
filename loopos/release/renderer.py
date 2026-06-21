"""Terminal renderer for structured readiness reports."""

from __future__ import annotations

from loopos.release.models import ReadinessReport


def render_readiness(report: ReadinessReport) -> str:
    lines = [
        "LoopOS Release Readiness",
        "=" * 72,
        f"Target:        {report.target}",
        f"Overall:       {report.overall_status}",
        f"Ready flag:    {'true' if report.ready else 'false'}",
        f"Source mode:   {'strict' if report.strict_source else 'packaging-safe'}",
        f"Deep smoke:    {'requested' if report.deep else 'not requested'}",
        "",
        "Readiness tiers",
        "-" * 72,
    ]
    for dimension in report.dimensions:
        marker = {"passed": "PASS", "warning": "WARN", "failed": "FAIL"}[
            dimension.status
        ]
        lines.append(f"[{marker}] {dimension.key:<26} {dimension.message}")
    lines.extend(
        [
            "",
            "Checks",
            "-" * 72,
            f"Passed: {report.passed}   Warnings: {report.warnings}   Failed: {report.failed}",
            "",
        ]
    )
    for check in report.checks:
        marker = {"passed": "PASS", "warning": "WARN", "failed": "FAIL"}[check.status]
        required = "required" if check.required_for_release else "advisory"
        lines.append(f"[{marker}] {check.name} ({required})")
        lines.append(f"       {check.message}")
        for item in check.evidence[:8]:
            lines.append(f"       - {item}")
        if len(check.evidence) > 8:
            lines.append(f"       - ... {len(check.evidence) - 8} more")
    return "\n".join(lines)

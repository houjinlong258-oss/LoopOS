"""Single entry point for Founding release readiness."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from loopos.release.checks import (
    REQUIRED_DOCS,
    REQUIRED_GOVERNANCE,
    cli_smoke_check,
    deep_smoke_check,
    latest_test_report_check,
    plugin_examples_check,
    policy_explain_check,
    pyproject_metadata_check,
    release_notes_check,
    required_paths_check,
    source_tree_check,
    staged_hygiene_checks,
)
from loopos.release.hygiene import check_release_clean
from loopos.release.models import ReadinessCheck, ReadinessReport
from loopos.release.packaging import package_release


def check_release_readiness(
    source: str | Path = ".",
    *,
    target: str = "founding-preview",
    strict_source: bool = False,
    deep: bool = False,
) -> ReadinessReport:
    """Build an isolated package and evaluate its public release contracts."""

    root = Path(source).resolve()
    checks: list[ReadinessCheck] = []
    if not root.is_dir():
        checks.append(
            ReadinessCheck(
                check_id="release.source",
                name="Release source",
                status="failed",
                message="release source does not exist",
                evidence=[str(root)],
            )
        )
        return ReadinessReport.from_checks(
            target=target,
            source=str(root),
            checks=checks,
            strict_source=strict_source,
            deep=deep,
        )

    source_report = check_release_clean(root, ignore_local_only=True)
    checks.append(source_tree_check(source_report, strict_source=strict_source))
    with TemporaryDirectory(prefix="loopos-readiness-") as temp:
        package = package_release(
            version="readiness",
            source=root,
            output=temp,
            make_zip=False,
        )
        if package.errors:
            checks.append(
                ReadinessCheck(
                    check_id="release.package",
                    name="Release package",
                    status="failed",
                    message="release package could not be staged",
                    evidence=package.errors,
                )
            )
        else:
            checks.extend(staged_hygiene_checks(check_release_clean(package.staging_dir)))

    checks.extend(
        [
            required_paths_check(
                root, REQUIRED_DOCS, "release.required_docs", "Required documentation"
            ),
            required_paths_check(
                root,
                REQUIRED_GOVERNANCE,
                "release.governance",
                "Governance and security files",
            ),
            plugin_examples_check(root),
            pyproject_metadata_check(root),
            cli_smoke_check(root),
            policy_explain_check(),
            release_notes_check(root),
            latest_test_report_check(root, require_generated=target != "founding-preview"),
            deep_smoke_check(root, enabled=deep),
        ]
    )
    return ReadinessReport.from_checks(
        target=target,
        source=str(root),
        checks=checks,
        strict_source=strict_source,
        deep=deep,
    )

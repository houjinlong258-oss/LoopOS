"""Structured release-readiness contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ReadinessStatus = Literal["passed", "warning", "failed"]
ReadinessDimensionKey = Literal[
    "source_tree_clean",
    "packaged_artifact_clean",
    "test_report_verified",
    "deep_smoke_verified",
]
ReadinessOverallStatus = Literal[
    "READY",
    "READY_WITH_WARNINGS",
    "READY_TO_PACKAGE",
    "NOT_READY_TO_TAG",
    "NOT_READY",
]


class ReadinessCheck(BaseModel):
    """One deterministic release-readiness result."""

    check_id: str
    name: str
    status: ReadinessStatus
    message: str
    evidence: list[str] = Field(default_factory=list)
    required_for_release: bool = True


class ReadinessDimension(BaseModel):
    """Named readiness tier derived from one or more checks."""

    key: ReadinessDimensionKey
    status: ReadinessStatus
    message: str
    check_ids: list[str] = Field(default_factory=list)


class SourceTreeDetails(BaseModel):
    """Structured source-tree evidence alongside the legacy status field."""

    status: ReadinessStatus
    blocked_paths: list[str] = Field(default_factory=list)


class ReadinessReport(BaseModel):
    """Aggregate readiness result for one named release target."""

    schema_version: str = "1.1"
    target: str
    source: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ready: bool
    ready_to_package: bool = False
    ready_to_tag: bool = False
    ready_to_publish: bool = False
    overall_status: ReadinessOverallStatus = "NOT_READY"
    source_tree_clean: ReadinessStatus = "warning"
    packaged_artifact_clean: ReadinessStatus = "failed"
    test_report_verified: ReadinessStatus = "failed"
    deep_smoke_verified: ReadinessStatus = "warning"
    source_tree_mode: Literal["strict", "package_from_dev_tree"] = "package_from_dev_tree"
    source_tree_details: SourceTreeDetails = Field(
        default_factory=lambda: SourceTreeDetails(status="warning")
    )
    strict_source: bool = False
    deep: bool = False
    passed: int
    warnings: int
    failed: int
    dimensions: list[ReadinessDimension] = Field(default_factory=list)
    checks: list[ReadinessCheck] = Field(default_factory=list)

    @classmethod
    def from_checks(
        cls,
        *,
        target: str,
        source: str,
        checks: list[ReadinessCheck],
        strict_source: bool = False,
        deep: bool = False,
    ) -> "ReadinessReport":
        failed_required = any(
            check.status == "failed" and check.required_for_release for check in checks
        )
        dimensions = _build_dimensions(checks)
        status_by_key = {dimension.key: dimension.status for dimension in dimensions}
        source_status = status_by_key.get("source_tree_clean", "warning")
        package_status = status_by_key.get("packaged_artifact_clean", "failed")
        test_status = status_by_key.get("test_report_verified", "failed")
        deep_status = status_by_key.get("deep_smoke_verified", "warning")
        overall_status = _overall_status(
            failed_required=failed_required,
            source_status=source_status,
            package_status=package_status,
            test_status=test_status,
            deep_status=deep_status,
            strict_source=strict_source,
            deep=deep,
            require_deep_for_tag=target != "founding-preview",
            checks=checks,
        )
        package_blockers = [
            check
            for check in checks
            if check.status == "failed"
            and check.required_for_release
            and check.check_id not in {"release.test_report", "release.deep_smoke"}
        ]
        ready_to_package = package_status == "passed" and not package_blockers
        ready_to_tag = (
            not failed_required
            and test_status == "passed"
            and source_status == "passed"
            and (target == "founding-preview" or deep_status == "passed")
        )
        ready_to_publish = ready_to_tag
        ready = ready_to_tag if target != "founding-preview" else not failed_required
        source_check = next(
            (check for check in checks if check.check_id == "release.source_tree_clean"),
            None,
        )
        return cls(
            target=target,
            source=source,
            ready=ready,
            ready_to_package=ready_to_package,
            ready_to_tag=ready_to_tag,
            ready_to_publish=ready_to_publish,
            overall_status=overall_status,
            source_tree_clean=source_status,
            packaged_artifact_clean=package_status,
            test_report_verified=test_status,
            deep_smoke_verified=deep_status,
            source_tree_mode="strict" if strict_source else "package_from_dev_tree",
            source_tree_details=SourceTreeDetails(
                status=source_status,
                blocked_paths=list(source_check.evidence) if source_check is not None else [],
            ),
            strict_source=strict_source,
            deep=deep,
            passed=sum(check.status == "passed" for check in checks),
            warnings=sum(check.status == "warning" for check in checks),
            failed=sum(check.status == "failed" for check in checks),
            dimensions=dimensions,
            checks=checks,
        )


def _build_dimensions(checks: list[ReadinessCheck]) -> list[ReadinessDimension]:
    groups: list[tuple[ReadinessDimensionKey, tuple[str, ...], str]] = [
        (
            "source_tree_clean",
            ("release.source_tree",),
            "source tree is clean enough for the requested release mode",
        ),
        (
            "packaged_artifact_clean",
            (
                "release.package",
                "release.package_hygiene",
                "release.readme_links",
                "release.no_secrets",
            ),
            "packaged artifact excludes local state, secrets, and broken README links",
        ),
        (
            "test_report_verified",
            ("release.test_report",),
            "latest test report is generated and tied to the current commit",
        ),
        (
            "deep_smoke_verified",
            ("release.deep_smoke",),
            "local no-network founding smoke suite has passed",
        ),
    ]
    dimensions: list[ReadinessDimension] = []
    for key, prefixes, default_message in groups:
        matched = [
            check
            for check in checks
            if any(check.check_id.startswith(prefix) for prefix in prefixes)
        ]
        if not matched:
            dimensions.append(
                ReadinessDimension(
                    key=key,
                    status="warning",
                    message="not evaluated",
                    check_ids=[],
                )
            )
            continue
        dimensions.append(
            ReadinessDimension(
                key=key,
                status=_aggregate_status(matched),
                message=_dimension_message(matched, default_message),
                check_ids=[check.check_id for check in matched],
            )
        )
    return dimensions


def _aggregate_status(checks: list[ReadinessCheck]) -> ReadinessStatus:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def _dimension_message(checks: list[ReadinessCheck], default: str) -> str:
    failed = [check for check in checks if check.status == "failed"]
    warnings = [check for check in checks if check.status == "warning"]
    if failed:
        return f"{len(failed)} failing check(s)"
    if warnings:
        return f"{len(warnings)} warning check(s)"
    return default


def _overall_status(
    *,
    failed_required: bool,
    source_status: ReadinessStatus,
    package_status: ReadinessStatus,
    test_status: ReadinessStatus,
    deep_status: ReadinessStatus,
    strict_source: bool,
    deep: bool,
    require_deep_for_tag: bool,
    checks: list[ReadinessCheck],
) -> ReadinessOverallStatus:
    if failed_required:
        return "NOT_READY"
    if strict_source and source_status != "passed":
        return "NOT_READY"
    if package_status == "failed":
        return "NOT_READY"
    if test_status != "passed":
        return "NOT_READY_TO_TAG"
    if source_status != "passed":
        return "READY_TO_PACKAGE"
    if deep and deep_status != "passed":
        return "NOT_READY"
    if require_deep_for_tag and deep_status != "passed":
        return "NOT_READY_TO_TAG"
    if any(check.status == "warning" for check in checks):
        return "READY_WITH_WARNINGS"
    return "READY"

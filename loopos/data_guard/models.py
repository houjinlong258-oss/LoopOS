"""Typed Data Guard contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

DataRisk = Literal["low", "medium", "high", "critical"]
DataOperationType = Literal[
    "schema_migration",
    "data_migration",
    "bulk_update",
    "bulk_delete",
    "backup",
    "restore",
    "sensitive_read",
    "unknown",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DataOperationDetection(BaseModel):
    schema_version: str = "1.0"
    detected: bool = False
    operation_type: DataOperationType = "unknown"
    risk_level: DataRisk = "low"
    requires_backup: bool = False
    requires_shadow_run: bool = False
    requires_human_approval: bool = False
    sensitive_entities: list[str] = Field(default_factory=list)
    matched_patterns: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class BackupPlan(BaseModel):
    schema_version: str = "1.0"
    backup_plan_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    target_kind: Literal["postgres", "mysql", "sqlite", "mongodb", "file", "unknown"] = "unknown"
    target_name: str
    target_environment: Literal["local", "test", "staging", "production", "unknown"] = "unknown"
    backup_scope: Literal["full_database", "selected_tables", "schema_only", "data_only", "files"] = "files"
    tables: list[str] = Field(default_factory=list)
    estimated_risk: DataRisk = "medium"
    backup_commands: list[str] = Field(default_factory=list)
    verify_commands: list[str] = Field(default_factory=list)
    restore_commands: list[str] = Field(default_factory=list)
    backup_location: str
    read_only: bool = True
    requires_approval: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class BackupManifest(BaseModel):
    schema_version: str = "1.0"
    backup_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    source: str
    environment: str = "local"
    files: list[str] = Field(default_factory=list)
    checksums: dict[str, str] = Field(default_factory=dict)
    read_only: bool = True
    verified: bool = False
    verification_report: dict[str, Any] = Field(default_factory=dict)
    restore_plan_path: str = ""
    policy_decision_id: str = ""


class ShadowRunPlan(BaseModel):
    schema_version: str = "1.0"
    shadow_run_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    backup_id: str
    shadow_target: str
    restore_from_backup: bool = True
    migration_commands: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    cleanup_commands: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class DataValidationReport(BaseModel):
    schema_version: str = "1.0"
    validation_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    backup_id: str | None = None
    target: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool = False
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    row_count_before: dict[str, int] = Field(default_factory=dict)
    row_count_after: dict[str, int] = Field(default_factory=dict)
    schema_diff_summary: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RestorePlan(BaseModel):
    schema_version: str = "1.0"
    restore_plan_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    backup_id: str
    target: str
    commands: list[str] = Field(default_factory=list)
    requires_approval: bool = True
    executable: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class RedactedSample(BaseModel):
    schema_version: str = "1.0"
    table: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    redacted_fields: list[str] = Field(default_factory=list)
    policy_decision_id: str = ""

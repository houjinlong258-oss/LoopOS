"""Deterministic database and sensitive-data risk detection."""

from __future__ import annotations

import re

from loopos.data_guard.models import DataOperationDetection

_DB_MARKERS = (
    "database", "migration", "migrate", "schema", "table", "column", "prisma",
    "alembic", "postgres", "mysql", "sqlite", "mongodb", "数据库", "迁移", "表", "字段",
)
_SENSITIVE = (
    "users", "orders", "payments", "auth", "session", "password", "token", "email",
    "phone", "credit_card", "用户", "订单", "支付",
)


def detect_data_operation(text: str) -> DataOperationDetection:
    lowered = text.strip().lower()
    patterns: list[str] = []
    reasons: list[str] = []
    entities = [item for item in _SENSITIVE if item in lowered]
    operation = "unknown"
    risk = "low"
    requires_backup = False
    requires_shadow = False
    requires_approval = False

    if re.search(r"\bdrop\s+(database|table|column)\b|\btruncate\b", lowered):
        operation, risk = "schema_migration", "critical"
        patterns.append("destructive_schema_sql")
    elif re.search(r"\bdelete\s+from\b", lowered):
        operation = "bulk_delete"
        risk = "critical" if not re.search(r"\bwhere\b", lowered) else "high"
        patterns.append("delete_without_where" if risk == "critical" else "bulk_delete")
    elif re.search(r"\bupdate\s+\w+\s+set\b", lowered):
        operation = "bulk_update"
        risk = "critical" if not re.search(r"\bwhere\b", lowered) else "high"
        patterns.append("update_without_where" if risk == "critical" else "bulk_update")
    elif re.search(r"\balter\s+table\b|\b(create|drop)\s+index\b", lowered):
        operation, risk = "schema_migration", "high"
        patterns.append("schema_change")
    elif any(marker in lowered for marker in ("migrate", "migration", "迁移", "prisma", "alembic")):
        operation, risk = "schema_migration", "high"
        patterns.append("migration_command")
    elif "backup" in lowered or "备份" in lowered:
        operation, risk = "backup", "medium"
        patterns.append("backup_operation")
    elif "restore" in lowered or "恢复" in lowered:
        operation, risk = "restore", "high"
        patterns.append("restore_operation")
    elif any(marker in lowered for marker in _DB_MARKERS):
        operation, risk = "unknown", "medium"
        patterns.append("database_goal")

    production_like = bool(re.search(r"(prod(uction)?|生产)[^\s]*|\w+://[^\s:@]+:[^\s@]+@", lowered))
    if production_like:
        risk = "critical"
        patterns.append("production_like_target")
        reasons.append("data.production_or_credential_target")
    detected = bool(patterns)
    if detected and operation not in {"backup"}:
        requires_backup = risk in {"high", "critical"}
        requires_shadow = operation in {"schema_migration", "data_migration", "bulk_update", "bulk_delete"}
        requires_approval = risk in {"high", "critical"}
    if "without_where" in " ".join(patterns):
        reasons.append("data.unbounded_write")
    if entities:
        reasons.append("data.sensitive_entities")
    if detected and not reasons:
        reasons.append("data.operation_detected")
    return DataOperationDetection(
        detected=detected,
        operation_type=operation,  # type: ignore[arg-type]
        risk_level=risk,  # type: ignore[arg-type]
        requires_backup=requires_backup,
        requires_shadow_run=requires_shadow,
        requires_human_approval=requires_approval,
        sensitive_entities=entities,
        matched_patterns=patterns,
        reason_codes=reasons,
    )

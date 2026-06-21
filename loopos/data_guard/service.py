"""Data Guard planning and mock-only orchestration."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from loopos.data_guard.models import (
    BackupPlan,
    DataValidationReport,
    RestorePlan,
    ShadowRunPlan,
)
from loopos.data_guard.vault import BackupVault


class DataGuardService:
    def __init__(self, workspace: str | Path, data_dir: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.data_dir = Path(data_dir).resolve()
        self.vault = BackupVault(self.data_dir / "backups")

    def plan_backup(self, target: str, *, run_id: str | None = None) -> BackupPlan:
        environment = "production" if "prod" in target.lower() or "生产" in target else "local"
        risk = "critical" if environment == "production" else "medium"
        return BackupPlan(
            run_id=run_id or f"data-{uuid4()}",
            target_kind="file",
            target_name=target,
            target_environment=environment,
            estimated_risk=risk,
            backup_location=str(self.data_dir / "backups"),
            backup_commands=["LoopOS local file copy"],
            verify_commands=["sha256 checksum verification"],
            restore_commands=["manual restore only"],
        )

    def safe_source(self, value: str | Path) -> Path:
        path = (self.workspace / value).resolve()
        try:
            path.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("backup source is outside workspace") from exc
        if not path.is_file():
            raise ValueError("backup source must be an existing workspace file")
        return path

    def shadow_plan(self, run_id: str, backup_id: str, migration: str) -> ShadowRunPlan:
        manifest = self.vault.verify(backup_id)
        if not manifest.verified:
            raise ValueError("verified backup is required before shadow run")
        return ShadowRunPlan(
            run_id=run_id,
            backup_id=backup_id,
            shadow_target="workspace-local-mock-shadow",
            migration_commands=[migration],
            validation_commands=["validate manifest", "run project tests"],
            cleanup_commands=["remove mock shadow copy"],
        )

    def validate(self, run_id: str, target: str, backup_id: str | None) -> DataValidationReport:
        verified = bool(backup_id and self.vault.verify(backup_id).verified)
        return DataValidationReport(
            run_id=run_id,
            backup_id=backup_id,
            target=target,
            checks=[{"name": "backup_verified", "passed": verified}],
            passed=verified,
            failures=[] if verified else ["verified backup is required"],
            schema_diff_summary="mock validation; no database connection was opened",
        )

    def restore_plan(self, run_id: str, backup_id: str, target: str) -> RestorePlan:
        if not self.vault.verify(backup_id).verified:
            raise ValueError("verified backup is required")
        return RestorePlan(run_id=run_id, backup_id=backup_id, target=target)

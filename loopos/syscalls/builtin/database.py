"""Mock-only Data Guard syscalls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loopos.data_guard import DataGuardService, detect_data_operation, redact_rows
from loopos.policy_os.models import PolicyDecision
from loopos.syscalls.registry import SyscallRegistry
from loopos.syscalls.types import SyscallCall, SyscallResult, SyscallSpec


def register_database_syscalls(
    registry: SyscallRegistry,
    *,
    workspace: str | Path,
    data_dir: str | Path | None = None,
) -> None:
    root = Path(workspace).resolve()
    service = DataGuardService(root, data_dir or root / ".loopos")

    def inspect(call: SyscallCall) -> SyscallResult:
        result = detect_data_operation(str(call.input.get("cmd", "")))
        return _result(call, True, result.model_dump(mode="json"))

    def backup(call: SyscallCall) -> SyscallResult:
        try:
            source = service.safe_source(str(call.input.get("source", "")))
            manifest = service.vault.create(run_id=call.run_id, source=source)
        except ValueError as exc:
            return _result(call, False, {}, str(exc))
        return _result(call, True, manifest.model_dump(mode="json"))

    def verify_backup(call: SyscallCall) -> SyscallResult:
        try:
            manifest = service.vault.verify(str(call.input.get("backup_id", "")))
        except KeyError as exc:
            return _result(call, False, {}, str(exc))
        return _result(call, manifest.verified, manifest.model_dump(mode="json"), None if manifest.verified else "backup verification failed")

    def restore_shadow(call: SyscallCall) -> SyscallResult:
        try:
            plan = service.shadow_plan(
                call.run_id,
                str(call.input.get("backup_id", "")),
                str(call.input.get("migration", "")),
            )
        except (KeyError, ValueError) as exc:
            return _result(call, False, {}, str(exc))
        return _result(call, True, plan.model_dump(mode="json"))

    def validate(call: SyscallCall) -> SyscallResult:
        try:
            report = service.validate(
                call.run_id,
                str(call.input.get("target", "mock")),
                _optional_text(call.input.get("backup_id")),
            )
        except KeyError as exc:
            return _result(call, False, {}, str(exc))
        return _result(call, report.passed, report.model_dump(mode="json"), None if report.passed else "validation failed")

    def redact(call: SyscallCall) -> SyscallResult:
        rows = call.input.get("rows", [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return _result(call, False, {}, "rows must be a list of objects")
        sample = redact_rows(str(call.input.get("table", "sample")), rows)
        return _result(call, True, sample.model_dump(mode="json"))

    def disabled(call: SyscallCall) -> SyscallResult:
        return _result(call, False, {"planned": True}, "real database execution is disabled in Alpha")

    def diff_schema(call: SyscallCall) -> SyscallResult:
        return _result(
            call,
            True,
            {
                "target": str(call.input.get("target", "mock")),
                "summary": "mock schema diff; no database connection was opened",
            },
        )

    entries = [
        (_spec("database.inspect", "Inspect a data operation.", ["cmd"], "low", "data.inspect"), inspect),
        (_spec("database.backup", "Back up a workspace-local sample.", ["source"], "medium", "data.backup", side_effecting=True), backup),
        (_spec("database.verify_backup", "Verify backup checksums.", ["backup_id"], "low", "data.backup"), verify_backup),
        (_spec("database.restore_shadow", "Create a mock shadow-run plan.", ["backup_id", "migration"], "medium", "data.shadow"), restore_shadow),
        (_spec("database.run_migration", "Production-disabled migration syscall.", ["migration"], "high", "data.migrate", approval=True, side_effecting=True), disabled),
        (_spec("database.validate", "Validate a mock target.", ["target"], "low", "data.validate"), validate),
        (_spec("database.restore", "Production-disabled restore syscall.", ["backup_id", "target"], "high", "data.restore", approval=True, side_effecting=True), disabled),
        (_spec("database.redact_sample", "Redact sensitive sample rows.", ["rows"], "low", "data.read"), redact),
        (_spec("database.diff_schema", "Generate a mock schema diff.", ["target"], "low", "data.inspect"), diff_schema),
    ]
    for spec, handler in entries:
        registry.register(spec, handler)


def _spec(
    name: str,
    description: str,
    required: list[str],
    risk: str,
    scope: str,
    *,
    approval: bool = False,
    side_effecting: bool = False,
) -> SyscallSpec:
    return SyscallSpec(
        name=name,
        description=description,
        input_schema={"required": required},
        risk=risk,  # type: ignore[arg-type]
        requires_approval=approval,
        side_effecting=side_effecting,
        policy_scope=scope,
        tags=["database", "data_guard"],
    )


def _result(
    call: SyscallCall,
    success: bool,
    output: dict[str, Any],
    error: str | None = None,
) -> SyscallResult:
    return SyscallResult(
        syscall_id=call.id,
        run_id=call.run_id,
        instruction_id=call.instruction_id,
        name=call.name,
        success=success,
        output=output,
        error=error,
        policy_decision=PolicyDecision(allowed=True, action="allow"),
    )


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None

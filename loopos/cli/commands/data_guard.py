"""Data Guard CLI commands."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from loopos.data_guard import DataGuardService, detect_data_operation
from loopos.data_guard.sqlite_adapter import SQLiteAdapter
from loopos.syscalls import SyscallCall, create_default_syscall_router


def db_command(
    action: str = "detect",
    arg: str | None = None,
    *,
    cmd: str | None = None,
    target: str | None = None,
    source: str | None = None,
    backup_id: str | None = None,
    migration: str | None = None,
    data_dir: str | Path = ".loopos",
    workspace: str | Path = ".",
    yes: bool = False,
    json_output: bool = False,
) -> int:
    run_id = f"data-{uuid4()}"
    if action == "detect":
        text = cmd or arg
        if not text:
            print("db detect requires --cmd TEXT or an argument", file=sys.stderr)
            return 1
        return _print(detect_data_operation(text).model_dump(mode="json"), json_output)
    if action == "sqlite-demo":
        return _sqlite_demo(data_dir=data_dir, json_output=json_output)
    service = DataGuardService(workspace, data_dir)
    if action == "plan-backup":
        value = target or arg
        if not value:
            print("db plan-backup requires --target TARGET", file=sys.stderr)
            return 1
        return _print(service.plan_backup(value, run_id=run_id).model_dump(mode="json"), json_output)
    if action == "audit":
        manifests = []
        for path in sorted((Path(data_dir) / "backups").glob("*/*/backup_manifest.json")):
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        return _print({"manifests": manifests}, json_output)

    syscall_name, payload = _syscall_payload(
        action,
        arg=arg,
        target=target,
        source=source,
        backup_id=backup_id,
        migration=migration,
    )
    if syscall_name is None:
        print(f"Unknown or incomplete db action: {action}", file=sys.stderr)
        return 1
    router = create_default_syscall_router(
        workspace,
        data_dir=data_dir,
        auto_approve_medium=yes,
    )
    result = router.dispatch(
        SyscallCall(
            run_id=run_id,
            instruction_id=f"db-{action}",
            name=syscall_name,
            input=payload,
            workspace=str(workspace),
            approval_granted=yes,
        )
    )
    _print(result.model_dump(mode="json"), json_output)
    return 0 if result.success else 2


def _sqlite_demo(*, data_dir: str | Path, json_output: bool) -> int:
    """Demonstrate the full SQLite Data Guard flow on a temp database.

    Steps:
      1. Create a temp SQLite database with sample data.
      2. Inspect it (read-only).
      3. Back it up to the Data Guard vault.
      4. Verify the backup checksum.
      5. Restore the backup to a shadow copy.
      6. Validate row counts between original and shadow.
      7. Print a structured report.

    No production database is touched. The temp database is deleted at the
    end; the backup and shadow copy remain under the data dir for inspection.
    """
    adapter = SQLiteAdapter()
    backup_root = Path(data_dir) / "backups" / "sqlite-demo"
    backup_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "demo.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.executemany(
            "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
            [
                (1, "alice", "alice@example.com"),
                (2, "bob", "bob@example.com"),
                (3, "carol", "carol@example.com"),
            ],
        )
        conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL)")
        conn.executemany(
            "INSERT INTO orders (id, user_id, total) VALUES (?, ?, ?)",
            [(1, 1, 19.99), (2, 2, 29.99), (3, 3, 39.99)],
        )
        conn.commit()
        conn.close()

        # Step 2: inspect
        inspection = adapter.inspect(db_path)

        # Step 3: backup
        manifest = adapter.backup(db_path, backup_root, run_id="sqlite-demo")
        backup_path = manifest.files[0]

        # Step 4: verify checksum
        checksum_ok = adapter.verify_checksum(backup_path, manifest.checksums[backup_path])

        # Step 5: restore shadow
        shadow_path = adapter.restore_shadow(backup_path, shadow_dir=backup_root / "shadow")

        # Step 6: validate
        validation = adapter.validate(
            db_path,
            shadow_path,
            run_id="sqlite-demo",
            backup_id=manifest.backup_id,
        )

    report = {
        "flow": "inspect -> backup -> verify -> shadow -> validate",
        "step1_inspection": inspection.model_dump(mode="json"),
        "step2_backup_manifest": manifest.model_dump(mode="json"),
        "step3_checksum_verified": checksum_ok,
        "step4_shadow_path": str(shadow_path),
        "step5_validation": validation.model_dump(mode="json"),
        "vault_location": str(backup_root),
    }
    _print(report, json_output)
    if not validation.passed or not checksum_ok:
        return 2
    return 0


def _syscall_payload(
    action: str,
    *,
    arg: str | None,
    target: str | None,
    source: str | None,
    backup_id: str | None,
    migration: str | None,
) -> tuple[str | None, dict[str, str]]:
    if action == "backup" and (source or arg):
        return "database.backup", {"source": source or arg or ""}
    if action == "verify-backup" and (backup_id or arg):
        return "database.verify_backup", {"backup_id": backup_id or arg or ""}
    if action == "shadow-run" and backup_id and (migration or arg):
        return "database.restore_shadow", {"backup_id": backup_id, "migration": migration or arg or ""}
    if action == "validate" and (target or arg):
        payload = {"target": target or arg or ""}
        if backup_id:
            payload["backup_id"] = backup_id
        return "database.validate", payload
    if action == "restore" and backup_id and (target or arg):
        return "database.restore", {"backup_id": backup_id, "target": target or arg or ""}
    if action == "run-migration" and (migration or arg):
        return "database.run_migration", {"migration": migration or arg or ""}
    if action == "diff-schema" and (target or arg):
        return "database.diff_schema", {"target": target or arg or ""}
    return None, {}


def _print(payload: object, json_output: bool) -> int:
    # Data Guard output remains structured even in the plain renderer.
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

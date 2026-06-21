"""Tests for the SQLite Data Guard demo flow CLI command."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "loopos.cli.app", *args],
        cwd=cwd or str(Path.cwd()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def test_sqlite_demo_produces_full_report() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = _run_cli("db", "sqlite-demo", "--data-dir", str(Path(tmp) / "loopos"))
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["flow"] == "inspect -> backup -> verify -> shadow -> validate"
        assert payload["step1_inspection"]["exists"] is True
        assert "users" in payload["step1_inspection"]["tables"]
        assert "orders" in payload["step1_inspection"]["tables"]
        assert payload["step3_checksum_verified"] is True
        assert payload["step5_validation"]["passed"] is True
        # Row counts should match between original and shadow
        before = payload["step5_validation"]["row_count_before"]
        after = payload["step5_validation"]["row_count_after"]
        assert before["users"] == after["users"] == 3
        assert before["orders"] == after["orders"] == 3


def test_sqlite_demo_leaves_vault_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "loopos"
        result = _run_cli("db", "sqlite-demo", "--data-dir", str(data_dir))
        assert result.returncode == 0
        vault = data_dir / "backups" / "sqlite-demo"
        assert vault.exists()
        # At least one backup file and one shadow file should exist
        backup_files = list(vault.glob("*.sqlite.bak"))
        assert backup_files
        shadow_files = list((vault / "shadow").glob("shadow_*"))
        assert shadow_files

"""Tests for SQLite Data Guard adapter."""

import sqlite3
import tempfile
from pathlib import Path

from loopos.data_guard.sqlite_adapter import SQLiteAdapter


def _create_test_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com')")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 99.99)")
    conn.commit()
    conn.close()


def test_inspect() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)
        adapter = SQLiteAdapter()
        info = adapter.inspect(db)
        assert info.exists
        assert "users" in info.tables
        assert "orders" in info.tables
        assert info.row_counts["users"] == 2
        assert info.row_counts["orders"] == 1
        assert info.checksum


def test_inspect_nonexistent() -> None:
    adapter = SQLiteAdapter()
    info = adapter.inspect("/nonexistent/path.db")
    assert not info.exists


def test_backup_and_verify() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)
        backup_dir = Path(tmpdir) / "backups"

        adapter = SQLiteAdapter()
        manifest = adapter.backup(db, backup_dir, run_id="run-1")

        assert manifest.run_id == "run-1"
        assert len(manifest.files) == 1
        assert manifest.verified

        # Verify checksum
        backup_path = manifest.files[0]
        checksum = list(manifest.checksums.values())[0]
        assert adapter.verify_checksum(backup_path, checksum)


def test_restore_shadow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)
        backup_dir = Path(tmpdir) / "backups"
        shadow_dir = Path(tmpdir) / "shadow"

        adapter = SQLiteAdapter()
        manifest = adapter.backup(db, backup_dir)
        shadow = adapter.restore_shadow(manifest.files[0], shadow_dir)

        assert shadow.exists()
        assert "shadow_" in shadow.name


def test_validate_matching() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)
        backup_dir = Path(tmpdir) / "backups"
        shadow_dir = Path(tmpdir) / "shadow"

        adapter = SQLiteAdapter()
        manifest = adapter.backup(db, backup_dir)
        shadow = adapter.restore_shadow(manifest.files[0], shadow_dir)

        report = adapter.validate(db, shadow, run_id="run-1")
        assert report.passed
        assert len(report.failures) == 0


def test_validate_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)

        # Create a different DB as shadow
        shadow = Path(tmpdir) / "shadow.db"
        conn = sqlite3.connect(str(shadow))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')")
        conn.commit()
        conn.close()

        adapter = SQLiteAdapter()
        report = adapter.validate(db, shadow)
        assert not report.passed
        assert len(report.failures) > 0


def test_redact_sample() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"
        _create_test_db(db)

        adapter = SQLiteAdapter()
        result = adapter.redact_sample(db, "users", sensitive_columns=["email"])

        assert result["table"] == "users"
        assert len(result["rows"]) == 2
        assert "email" in result["redacted_fields"]
        for row in result["rows"]:
            assert row["email"] == "***REDACTED***"
            assert row["name"] in ("Alice", "Bob")

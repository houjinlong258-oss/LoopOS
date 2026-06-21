import tempfile
import unittest
from pathlib import Path

from loopos.data_guard import BackupVault, DataGuardService, detect_data_operation, redact_rows
from loopos.goal import GoalNegotiator
from loopos.syscalls import SyscallCall, create_default_syscall_router


class DataGuardTests(unittest.TestCase):
    def test_detector_classifies_dangerous_sql_and_ignores_pytest(self) -> None:
        drop = detect_data_operation("DROP TABLE users")
        delete = detect_data_operation("DELETE FROM payments")
        safe = detect_data_operation("pytest -q")
        self.assertEqual(drop.risk_level, "critical")
        self.assertTrue(drop.requires_backup)
        self.assertIn("delete_without_where", delete.matched_patterns)
        self.assertFalse(safe.detected)

    def test_redaction_removes_sensitive_values(self) -> None:
        sample = redact_rows(
            "users",
            [{"id": 1, "email": "person@example.com", "token": "secret", "note": "call +8613812345678"}],
        )
        self.assertEqual(sample.rows[0]["email"], "[REDACTED_EMAIL]")
        self.assertEqual(sample.rows[0]["token"], "[REDACTED_SECRET]")
        self.assertNotIn("13812345678", str(sample.rows))

    def test_vault_creates_and_verifies_read_only_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.db"
            source.write_bytes(b"local sample")
            vault = BackupVault(Path(tmp) / "vault")
            manifest = vault.create(run_id="run-data", source=source)
            verified = vault.verify(manifest.backup_id)
            self.assertTrue(verified.verified)
            self.assertTrue(verified.read_only)
            self.assertEqual(len(verified.checksums), 1)

    def test_shadow_plan_requires_verified_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.db"
            source.write_bytes(b"sample")
            service = DataGuardService(tmp, Path(tmp) / "state")
            manifest = service.vault.create(run_id="run-data", source=source)
            plan = service.shadow_plan("run-data", manifest.backup_id, "alembic upgrade head")
            self.assertEqual(plan.backup_id, manifest.backup_id)
            self.assertTrue(plan.restore_from_backup)

    def test_database_syscall_blocks_real_migration_before_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_syscall_router(tmp)
            result = router.dispatch(
                SyscallCall(
                    run_id="run-data",
                    instruction_id="migration",
                    name="database.run_migration",
                    input={"migration": "DROP TABLE users"},
                    workspace=tmp,
                    approval_granted=True,
                )
            )
            self.assertFalse(result.success)
            self.assertEqual(result.policy_decision.safety_level, "L5")
            self.assertEqual(result.error, "blocked by policy")

    def test_database_goal_uses_data_safe_proposals(self) -> None:
        negotiator = GoalNegotiator()
        proposal = negotiator.propose("帮我执行数据库迁移")
        self.assertEqual(len(proposal.options), 3)
        self.assertIn("备份", proposal.options[1].title)
        spec = negotiator.finalize("帮我执行数据库迁移", option_ids=[2])
        self.assertIn("backup verified", spec.acceptance_criteria)


if __name__ == "__main__":
    unittest.main()

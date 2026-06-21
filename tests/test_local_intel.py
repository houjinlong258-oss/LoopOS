import sqlite3
import tempfile
import unittest
from pathlib import Path

from loopos.local_intel import WorkspaceIndexer


class LocalIntelligenceTests(unittest.TestCase):
    def test_index_searches_text_and_excludes_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "app.py").write_text("def webhook_handler():\n    return 'ready'\n", encoding="utf-8")
            (workspace / ".env").write_text("API_KEY=top-secret", encoding="utf-8")
            (workspace / "private.key").write_text("PRIVATE KEY", encoding="utf-8")
            (workspace / "node_modules").mkdir()
            (workspace / "node_modules" / "ignored.js").write_text("webhook secret", encoding="utf-8")
            database = Path(tmp) / "state" / "index.sqlite3"
            indexer = WorkspaceIndexer(workspace, database)
            status = indexer.build()
            results = indexer.search("webhook handler")

            self.assertEqual(status.indexed_files, 1)
            self.assertGreaterEqual(status.blocked_files, 2)
            self.assertEqual(results[0].path, "app.py")
            self.assertEqual(indexer.search("top-secret"), [])

            connection = sqlite3.connect(database)
            try:
                paths = [row[0] for row in connection.execute("SELECT path FROM files")]
            finally:
                connection.close()
            self.assertNotIn(".env", paths)

    def test_indexes_python_symbols_imports_and_explains_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "guard.py").write_text(
                """import sqlite3
from pathlib import Path

class BackupGuard:
    def verify(self) -> bool:
        return True

async def run_guard() -> None:
    pass
""",
                encoding="utf-8",
            )
            indexer = WorkspaceIndexer(workspace, Path(tmp) / "index.sqlite3")
            status = indexer.build()

            symbols = indexer.search_symbols("Guard")
            explanation = indexer.explain_file("guard.py")

            self.assertEqual(status.indexed_symbols, 3)
            self.assertEqual(status.indexed_imports, 2)
            self.assertEqual(
                [item.name for item in symbols], ["BackupGuard", "run_guard", "verify"]
            )
            imports = explanation["imports"]
            self.assertIsInstance(imports, list)
            self.assertEqual(len(imports), 2)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

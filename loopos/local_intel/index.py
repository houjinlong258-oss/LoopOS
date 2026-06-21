"""Deterministic SQLite workspace index."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from loopos.local_intel.models import WorkspaceIndex, WorkspaceSearchResult
from loopos.local_intel.privacy import BLOCKED_DIRS, is_indexable_text, is_private_path


class WorkspaceIndexer:
    def __init__(self, workspace: str | Path, database_path: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap()

    def build(self) -> WorkspaceIndex:
        indexed = skipped = blocked = 0
        rows: list[tuple[str, int, float, str, str]] = []
        for path in self.workspace.rglob("*"):
            if any(part in BLOCKED_DIRS for part in path.relative_to(self.workspace).parts[:-1]):
                continue
            if not path.is_file():
                continue
            if is_private_path(path, self.workspace):
                blocked += 1
                continue
            if not is_indexable_text(path):
                skipped += 1
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue
            relative = path.relative_to(self.workspace).as_posix()
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            stat = path.stat()
            rows.append((relative, stat.st_size, stat.st_mtime, digest, content))
            indexed += 1
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute("DELETE FROM files")
            connection.executemany(
                "INSERT INTO files(path, size, mtime, sha256, content) VALUES (?, ?, ?, ?, ?)", rows
            )
            connection.commit()
        finally:
            connection.close()
        return WorkspaceIndex(
            workspace=str(self.workspace),
            database_path=str(self.database_path),
            status="ready",
            indexed_files=indexed,
            skipped_files=skipped,
            blocked_files=blocked,
        )

    def status(self) -> WorkspaceIndex:
        connection = sqlite3.connect(self.database_path)
        try:
            count = int(connection.execute("SELECT COUNT(*) FROM files").fetchone()[0])
        finally:
            connection.close()
        return WorkspaceIndex(
            workspace=str(self.workspace),
            database_path=str(self.database_path),
            status="ready" if count else "empty",
            indexed_files=count,
        )

    def search(self, query: str, *, limit: int = 20) -> list[WorkspaceSearchResult]:
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return []
        clauses = " OR ".join("LOWER(path) LIKE ? OR LOWER(content) LIKE ?" for _ in terms)
        params = [value for term in terms for value in (f"%{term}%", f"%{term}%")]
        connection = sqlite3.connect(self.database_path)
        try:
            rows = connection.execute(
                f"SELECT path, size, content FROM files WHERE {clauses} ORDER BY path LIMIT ?",  # noqa: S608
                [*params, limit * 3],
            ).fetchall()
        finally:
            connection.close()
        results: list[WorkspaceSearchResult] = []
        for path, size, content in rows:
            lowered = f"{path}\n{content}".lower()
            score = float(sum(lowered.count(term) for term in terms))
            results.append(
                WorkspaceSearchResult(path=path, size=size, score=score, snippet=_snippet(content, terms))
            )
        return sorted(results, key=lambda row: (-row.score, row.path))[:limit]

    def _bootstrap(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    sha256 TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()


def _snippet(content: str, terms: list[str]) -> str:
    lines = content.splitlines()
    for line in lines:
        if any(term in line.lower() for term in terms):
            return line.strip()[:240]
    return content[:240]

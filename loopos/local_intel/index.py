"""Deterministic SQLite workspace index."""

from __future__ import annotations

import ast
import hashlib
import sqlite3
import subprocess
from pathlib import Path

from loopos.local_intel.models import (
    CodeSymbol,
    ImportReference,
    WorkspaceIndex,
    WorkspaceSearchResult,
)
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
        symbols: list[CodeSymbol] = []
        imports: list[ImportReference] = []
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
            if path.suffix.lower() == ".py":
                file_symbols, file_imports = _analyze_python(relative, content)
                symbols.extend(file_symbols)
                imports.extend(file_imports)
            indexed += 1
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute("DELETE FROM files")
            connection.execute("DELETE FROM symbols")
            connection.execute("DELETE FROM imports")
            connection.executemany(
                "INSERT INTO files(path, size, mtime, sha256, content) VALUES (?, ?, ?, ?, ?)", rows
            )
            connection.executemany(
                """
                INSERT INTO symbols(path, name, qualified_name, kind, line, end_line)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.path,
                        item.name,
                        item.qualified_name,
                        item.kind,
                        item.line,
                        item.end_line,
                    )
                    for item in symbols
                ],
            )
            connection.executemany(
                """
                INSERT INTO imports(path, module, name, alias, line)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(item.path, item.module, item.name, item.alias, item.line) for item in imports],
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
            indexed_symbols=len(symbols),
            indexed_imports=len(imports),
        )

    def status(self) -> WorkspaceIndex:
        connection = sqlite3.connect(self.database_path)
        try:
            count = int(connection.execute("SELECT COUNT(*) FROM files").fetchone()[0])
            symbol_count = int(connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0])
            import_count = int(connection.execute("SELECT COUNT(*) FROM imports").fetchone()[0])
        finally:
            connection.close()
        return WorkspaceIndex(
            workspace=str(self.workspace),
            database_path=str(self.database_path),
            status="ready" if count else "empty",
            indexed_files=count,
            indexed_symbols=symbol_count,
            indexed_imports=import_count,
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

    def search_symbols(self, query: str = "", *, limit: int = 50) -> list[CodeSymbol]:
        pattern = f"%{query.strip()}%"
        connection = sqlite3.connect(self.database_path)
        try:
            rows = connection.execute(
                """
                SELECT path, name, qualified_name, kind, line, end_line
                FROM symbols
                WHERE name LIKE ? OR qualified_name LIKE ?
                ORDER BY name, path, line
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
        finally:
            connection.close()
        return [
            CodeSymbol(
                path=row[0],
                name=row[1],
                qualified_name=row[2],
                kind=row[3],
                line=row[4],
                end_line=row[5],
            )
            for row in rows
        ]

    def imports_for(self, path: str) -> list[ImportReference]:
        connection = sqlite3.connect(self.database_path)
        try:
            rows = connection.execute(
                """
                SELECT path, module, name, alias, line
                FROM imports WHERE path = ? ORDER BY line, module, name
                """,
                (Path(path).as_posix(),),
            ).fetchall()
        finally:
            connection.close()
        return [
            ImportReference(path=row[0], module=row[1], name=row[2], alias=row[3], line=row[4])
            for row in rows
        ]

    def import_graph(self, *, limit: int = 200) -> list[dict[str, object]]:
        connection = sqlite3.connect(self.database_path)
        try:
            rows = connection.execute(
                """
                SELECT module, COUNT(*) AS refs, GROUP_CONCAT(path, '|') AS paths
                FROM imports
                GROUP BY module
                ORDER BY refs DESC, module
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "module": row[0],
                "references": row[1],
                "paths": sorted(set(str(row[2] or "").split("|"))) if row[2] else [],
            }
            for row in rows
        ]

    def git_diff_index(self, *, base_ref: str = "HEAD") -> list[dict[str, str]]:
        result = subprocess.run(
            ["git", "diff", "--name-status", base_ref],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            return [{"status": "error", "path": result.stderr.strip()[-400:]}]
        rows: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            path = parts[-1] if len(parts) > 1 else ""
            rows.append({"status": status, "path": path})
        return rows

    def explain_file(self, path: str) -> dict[str, object]:
        normalized = Path(path).as_posix()
        symbols = [item for item in self.search_symbols(limit=1000) if item.path == normalized]
        imports = self.imports_for(normalized)
        return {
            "path": normalized,
            "symbols": [item.model_dump(mode="json") for item in symbols],
            "imports": [item.model_dump(mode="json") for item in imports],
        }

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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS symbols (
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    qualified_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    end_line INTEGER
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS imports (
                    path TEXT NOT NULL,
                    module TEXT NOT NULL,
                    name TEXT,
                    alias TEXT,
                    line INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_imports_path ON imports(path)"
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


def _analyze_python(path: str, content: str) -> tuple[list[CodeSymbol], list[ImportReference]]:
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError:
        return [], []
    symbols: list[CodeSymbol] = []
    imports: list[ImportReference] = []

    def visit(nodes: list[ast.stmt], prefix: str = "") -> None:
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = f"{prefix}.{node.name}" if prefix else node.name
                kind = (
                    "class"
                    if isinstance(node, ast.ClassDef)
                    else "async_function"
                    if isinstance(node, ast.AsyncFunctionDef)
                    else "function"
                )
                symbols.append(
                    CodeSymbol(
                        path=path,
                        name=node.name,
                        qualified_name=qualified,
                        kind=kind,
                        line=node.lineno,
                        end_line=node.end_lineno,
                    )
                )
                visit(node.body, qualified)
            elif isinstance(node, ast.Import):
                imports.extend(
                    ImportReference(
                        path=path,
                        module=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
                    )
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imports.extend(
                    ImportReference(
                        path=path,
                        module="." * node.level + (node.module or ""),
                        name=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
                    )
                    for alias in node.names
                )

    visit(tree.body)
    return symbols, imports

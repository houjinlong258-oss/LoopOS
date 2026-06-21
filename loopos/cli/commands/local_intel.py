"""Local index, search, and file discovery commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.local_intel import WorkspaceIndexer


def index_command(
    action: str = "status",
    *,
    workspace: str | Path = ".",
    data_dir: str | Path = ".loopos",
) -> int:
    indexer = WorkspaceIndexer(workspace, Path(data_dir) / "workspace-index.sqlite3")
    if action == "build":
        payload = indexer.build()
    elif action == "status":
        payload = indexer.status()
    else:
        print(f"Unknown index action: {action}", file=sys.stderr)
        return 1
    print(payload.model_dump_json(indent=2))
    return 0


def search_command(
    query: str,
    *,
    workspace: str | Path = ".",
    data_dir: str | Path = ".loopos",
    limit: int = 20,
) -> int:
    rows = WorkspaceIndexer(workspace, Path(data_dir) / "workspace-index.sqlite3").search(query, limit=limit)
    print(json.dumps([row.model_dump(mode="json") for row in rows], ensure_ascii=False, indent=2))
    return 0


def files_command(
    action: str,
    query: str,
    *,
    workspace: str | Path = ".",
    data_dir: str | Path = ".loopos",
) -> int:
    if action != "find":
        print(f"Unknown files action: {action}", file=sys.stderr)
        return 1
    return search_command(query, workspace=workspace, data_dir=data_dir)

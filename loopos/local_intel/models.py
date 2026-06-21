"""Local workspace index contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceIndex(BaseModel):
    schema_version: str = "1.0"
    workspace: str
    database_path: str
    status: Literal["empty", "ready", "failed"] = "empty"
    indexed_files: int = 0
    skipped_files: int = 0
    blocked_files: int = 0
    indexed_symbols: int = 0
    indexed_imports: int = 0
    updated_at: datetime = Field(default_factory=utc_now)


class WorkspaceSearchResult(BaseModel):
    path: str
    score: float
    snippet: str
    size: int


class CodeSymbol(BaseModel):
    path: str
    name: str
    qualified_name: str
    kind: Literal["class", "function", "async_function"]
    line: int
    end_line: int | None = None


class ImportReference(BaseModel):
    path: str
    module: str
    name: str | None = None
    alias: str | None = None
    line: int

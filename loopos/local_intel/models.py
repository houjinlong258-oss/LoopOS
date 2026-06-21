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
    updated_at: datetime = Field(default_factory=utc_now)


class WorkspaceSearchResult(BaseModel):
    path: str
    score: float
    snippet: str
    size: int

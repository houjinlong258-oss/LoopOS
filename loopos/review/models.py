"""Producer, reviewer, and verifier separation contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


ReviewStatus = Literal["pending", "in_review", "changes_requested", "approved", "rejected"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    producer: str
    verifier: str
    reviewer: str
    status: ReviewStatus = "pending"
    high_risk: bool = False
    findings: list[str] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("task_id", "producer", "verifier", "reviewer")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review fields cannot be empty")
        return value


"""Role separation coordinator for code review workflows."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.review.models import ReviewRecord, ReviewStatus, utc_now
from loopos.tasks import TaskRecord


class ReviewStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, *, status: ReviewStatus | None = None) -> list[ReviewRecord]:
        if not self.path.exists():
            return []
        rows = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        reviews = [ReviewRecord.model_validate(item) for item in rows]
        if status is not None:
            reviews = [review for review in reviews if review.status == status]
        return sorted(reviews, key=lambda item: item.created_at.isoformat())

    def load(self, review_id: str) -> ReviewRecord:
        for review in self.list():
            if review.id == review_id:
                return review
        raise KeyError(f"review not found: {review_id}")

    def save(self, review: ReviewRecord) -> ReviewRecord:
        reviews = {item.id: item for item in self.list()}
        review.updated_at = utc_now()
        reviews[review.id] = review
        self.path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in reviews.values()],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return review


class ReviewCoordinator:
    def __init__(self, store: ReviewStore) -> None:
        self.store = store

    def start(
        self,
        task: TaskRecord,
        *,
        producer: str = "producer",
        verifier: str = "verifier",
        reviewer: str = "reviewer",
    ) -> ReviewRecord:
        high_risk = task.requires_worktree or task.type == "code_change"
        if high_risk and len({producer, verifier, reviewer}) != 3:
            raise ValueError("high-risk work requires separate producer, verifier, and reviewer")
        review = ReviewRecord(
            task_id=task.id,
            producer=producer,
            verifier=verifier,
            reviewer=reviewer,
            status="in_review",
            high_risk=high_risk,
        )
        return self.store.save(review)

    def approve(self, review_id: str, *, actor: str) -> ReviewRecord:
        review = self.store.load(review_id)
        if actor != review.reviewer:
            raise ValueError("only the assigned reviewer can approve")
        if review.high_risk and actor in {review.producer, review.verifier}:
            raise ValueError("producer or verifier cannot approve high-risk work")
        review.status = "approved"
        return self.store.save(review)

    def verify(self, review_id: str, *, actor: str, note: str) -> ReviewRecord:
        review = self.store.load(review_id)
        if actor != review.verifier:
            raise ValueError("only the assigned verifier can record verification")
        review.verification_notes.append(note)
        return self.store.save(review)


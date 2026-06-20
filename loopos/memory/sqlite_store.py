"""SQLite index for LoopOS memory."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loopos.core.state import LoopState
from loopos.memory.belief_store import MemoryItem, MemoryStatus
from loopos.memory.event_log import Event
from loopos.memory.proposals import MemoryProposal, ProposalStatus
from loopos.memory.skill_proposals import SkillProposal, SkillProposalStatus
from loopos.memory.skill_store import Skill

if TYPE_CHECKING:
    from loopos.kernel.trace import TraceEvent


class SQLiteMemoryIndex:
    """SQLite query index for JSON/JSONL memory artifacts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.bootstrap()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def bootstrap(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, step_index);
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content TEXT NOT NULL,
                    normalized_content TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    conflicts TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    decay_score REAL NOT NULL,
                    usage_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    failure_count INTEGER NOT NULL,
                    created_at TEXT,
                    updated_at TEXT,
                    expires_at TEXT,
                    last_used_at TEXT,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memory_filter
                    ON memory_items(status, layer, scope, confidence);
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_tags TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    success_rate REAL NOT NULL DEFAULT 0,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS skill_proposals (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_run_id TEXT NOT NULL,
                    source_event_ids TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    decision_reasons TEXT NOT NULL,
                    proposed_skill_id TEXT NOT NULL,
                    created_at TEXT,
                    decided_at TEXT,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_proposals (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_run_id TEXT,
                    source_event_ids TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    decision_reasons TEXT NOT NULL,
                    proposed_item_id TEXT NOT NULL,
                    created_at TEXT,
                    decided_at TEXT,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_proposals_status ON memory_proposals(status);
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )
            self._ensure_columns(
                conn,
                "events",
                {
                    "schema_version": "INTEGER NOT NULL DEFAULT 1",
                    "kind": "TEXT",
                    "instruction_id": "TEXT",
                    "syscall_id": "TEXT",
                    "policy_decision_id": "TEXT",
                },
            )
            self._ensure_columns(
                conn,
                "skills",
                {
                    "status": "TEXT NOT NULL DEFAULT 'active'",
                    "success_count": "INTEGER NOT NULL DEFAULT 0",
                    "failure_count": "INTEGER NOT NULL DEFAULT 0",
                    "success_rate": "REAL NOT NULL DEFAULT 0",
                },
            )

    def reset_index(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                DELETE FROM runs;
                DELETE FROM events;
                DELETE FROM memory_items;
                DELETE FROM skills;
                DELETE FROM skill_proposals;
                DELETE FROM memory_proposals;
                DELETE FROM user_profile;
                """
            )

    def upsert_run(self, state: LoopState) -> None:
        payload = state.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO runs(id, goal, status, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    goal=excluded.goal,
                    status=excluded.status,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                """,
                (
                    state.run_id,
                    state.goal,
                    state.status,
                    json.dumps(payload, ensure_ascii=False),
                    str(payload.get("created_at", "")),
                    str(payload.get("updated_at", "")),
                ),
            )

    def upsert_event(self, event: Event) -> None:
        payload = event.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events(id, run_id, step_index, type, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.run_id,
                    event.step_index,
                    event.type,
                    json.dumps(payload["payload"], ensure_ascii=False),
                    str(payload.get("created_at", "")),
                ),
            )

    def upsert_trace_event(self, event: TraceEvent) -> None:
        payload = event.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events(
                    id, run_id, step_index, type, payload, created_at,
                    schema_version, kind, instruction_id, syscall_id, policy_decision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.run_id,
                    event.step,
                    event.type or event.kind or "run",
                    json.dumps(payload["payload"], ensure_ascii=False),
                    str(payload.get("created_at", "")),
                    event.schema_version,
                    event.kind,
                    event.instruction_id,
                    event.syscall_id,
                    event.policy_decision_id,
                ),
            )

    def upsert_memory_item(self, item: MemoryItem) -> None:
        payload = item.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_items(
                    id, type, layer, scope, status, content, normalized_content,
                    confidence, source, tags, metadata, conflicts, version, decay_score,
                    usage_count, success_count, failure_count, created_at, updated_at,
                    expires_at, last_used_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.type,
                    item.layer,
                    item.scope,
                    item.status,
                    item.content,
                    self.normalize(item.content),
                    item.confidence,
                    item.source,
                    json.dumps(item.tags, ensure_ascii=False),
                    json.dumps(payload.get("metadata", {}), ensure_ascii=False),
                    json.dumps(item.conflicts, ensure_ascii=False),
                    item.version,
                    item.decay_score,
                    item.usage_count,
                    item.success_count,
                    item.failure_count,
                    str(payload.get("created_at", "")),
                    str(payload.get("updated_at", "")),
                    str(payload.get("expires_at", "") or ""),
                    str(payload.get("last_used_at", "") or ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list_memory(
        self,
        *,
        status: MemoryStatus | None = None,
        layer: str | None = None,
        scope: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if layer is not None:
            clauses.append("layer = ?")
            params.append(layer)
        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope)
        query = "SELECT payload FROM memory_items"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY confidence DESC, updated_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self.connection() as conn:
            return [
                MemoryItem.model_validate(json.loads(row["payload"]))
                for row in conn.execute(query, params)
            ]

    def upsert_skill(self, skill: Skill) -> None:
        payload = skill.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skills(
                    id, name, trigger_tags, confidence, status,
                    success_count, failure_count, success_rate, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill.id,
                    skill.name,
                    json.dumps(skill.trigger_tags, ensure_ascii=False),
                    skill.confidence,
                    skill.status,
                    skill.success_count,
                    skill.failure_count,
                    skill.success_rate,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list_skills(self, *, status: str | None = None) -> list[Skill]:
        query = "SELECT payload FROM skills"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY name ASC"
        with self.connection() as conn:
            return [
                Skill.model_validate(json.loads(row["payload"]))
                for row in conn.execute(query, params)
            ]

    def upsert_skill_proposal(self, proposal: SkillProposal) -> None:
        payload = proposal.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skill_proposals(
                    id, status, source_run_id, source_event_ids, rationale,
                    decision_reasons, proposed_skill_id, created_at, decided_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.id,
                    proposal.status,
                    proposal.source_run_id,
                    json.dumps(proposal.source_event_ids, ensure_ascii=False),
                    proposal.rationale,
                    json.dumps(proposal.decision_reasons, ensure_ascii=False),
                    proposal.proposed_skill.id,
                    str(payload.get("created_at", "")),
                    str(payload.get("decided_at", "") or ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list_skill_proposals(
        self, *, status: SkillProposalStatus | None = None
    ) -> list[SkillProposal]:
        query = "SELECT payload FROM skill_proposals"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at ASC"
        with self.connection() as conn:
            return [
                SkillProposal.model_validate(json.loads(row["payload"]))
                for row in conn.execute(query, params)
            ]

    def get_skill_proposal(self, proposal_id: str) -> SkillProposal:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM skill_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"skill proposal not found: {proposal_id}")
        return SkillProposal.model_validate(json.loads(row["payload"]))

    def upsert_proposal(self, proposal: MemoryProposal) -> None:
        payload = proposal.model_dump(mode="json")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_proposals(
                    id, status, source, source_run_id, source_event_ids, rationale,
                    decision_reasons, proposed_item_id, created_at, decided_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.id,
                    proposal.status,
                    proposal.source,
                    proposal.source_run_id,
                    json.dumps(proposal.source_event_ids, ensure_ascii=False),
                    proposal.rationale,
                    json.dumps(proposal.decision_reasons, ensure_ascii=False),
                    proposal.proposed_item.id,
                    str(payload.get("created_at", "")),
                    str(payload.get("decided_at", "") or ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def get_proposal(self, proposal_id: str) -> MemoryProposal:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM memory_proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"proposal not found: {proposal_id}")
        return MemoryProposal.model_validate(json.loads(row["payload"]))

    def list_proposals(self, *, status: ProposalStatus | None = None) -> list[MemoryProposal]:
        query = "SELECT payload FROM memory_proposals"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at ASC"
        with self.connection() as conn:
            return [
                MemoryProposal.model_validate(json.loads(row["payload"]))
                for row in conn.execute(query, params)
            ]

    def set_profile(self, key: str, value: str, *, updated_at: str) -> None:
        payload = {"key": key, "value": value, "updated_at": updated_at}
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profile(key, value, updated_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at,
                    payload=excluded.payload
                """,
                (key, value, updated_at, json.dumps(payload, ensure_ascii=False)),
            )

    def get_profile(self) -> dict[str, str]:
        with self.connection() as conn:
            return {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM user_profile")}

    @staticmethod
    def _ensure_columns(
        conn: sqlite3.Connection,
        table: str,
        columns: dict[str, str],
    ) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")

    @staticmethod
    def normalize(content: str) -> str:
        return " ".join(content.strip().lower().split())

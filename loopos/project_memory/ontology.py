"""Typed ontology for Project Memory OS.

Zep-inspired entity schema for the v0.4.x Project Memory OS.

Project Memory stores the *signals* that survive across loop runs —
decisions, failures, procedures, deliveries. Without an ontology,
MemoryCompiler treats every item as an opaque ``ProjectMemoryItem`` and
the only ordering axis is ``created_at``. With an ontology:

* MemoryCompiler can budget by entity type ("spend 30% on failures,
  20% on procedures, 50% on the rest"). See
  ``loopos/project_memory/token_budget.py``.
* The Fusion Optimizer can score entities by importance via
  ``EntityImportance`` weights rather than heuristic recency.
* Cross-references between entities (a Failure referencing a Decision,
  a Procedure referencing a Failure) become first-class rather than
  free-form ``tags`` strings.

This module deliberately stays *small* — it adds typed entity records
on top of the existing ``ProjectMemoryItem`` without rewriting the
store or compiler. New entity types are registered in
``ENTITY_TYPES`` and ``ENTITY_IMPORTANCE``.

We use stdlib ``dataclasses`` (not Pydantic) because the ontology is
in-process memory record plumbing, not a wire format; the pydantic
``ProjectMemoryItem`` model in ``loopos.project_memory.models`` is
still the on-disk / wire format.

Inspired by ``zep/ontology/default_ontology.py`` (Geoffrey Huntley's
Zep memory project) and the agent-memory-full-example which uses
typed entities for user / assistant / preference / location / event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, cast
from uuid import uuid4


# ---------------------------------------------------------------------------
# Entity kinds — every entity that can land in Project Memory
# ---------------------------------------------------------------------------


class EntityKind(str, Enum):
    """The closed set of typed entities that can populate Project Memory.

    New kinds must be added here AND to ``ENTITY_TYPES`` AND to
    ``DEFAULT_IMPORTANCE`` so the compiler can budget and the
    optimizer can score them.
    """

    GOAL = "goal"            # A user goal / objective (mirrors UserGoal)
    DECISION = "decision"    # A binding decision made during a loop run
    FAILURE = "failure"      # A repeated or blocking failure
    PROCEDURE = "procedure"  # A promotable workflow / repeatable recipe
    DELIVERY = "delivery"    # A delivery candidate / release surface
    ASSUMPTION = "assumption"  # An explicit assumption (validated or not)
    CONSTRAINT = "constraint"  # A binding constraint (policy / budget)
    TOOL_RESULT = "tool_result"  # A recorded tool run (artifact)
    SIGNAL = "signal"        # A LAIL signal (raw or aggregated)
    NOTE = "note"            # A free-form project note


# Per-entity importance weight (0.0..1.0). Higher = the MemoryCompiler
# should preserve this entity type when budget is tight. Tune per-project.
DEFAULT_IMPORTANCE: dict[EntityKind, float] = {
    EntityKind.GOAL:         0.95,  # always keep the goal
    EntityKind.CONSTRAINT:   0.90,  # constraints are durable
    EntityKind.DECISION:     0.85,  # decisions are durable
    EntityKind.FAILURE:      0.80,  # failures must be visible to repair
    EntityKind.PROCEDURE:    0.75,  # procedures save time
    EntityKind.DELIVERY:     0.70,  # deliveries audit-trail
    EntityKind.ASSUMPTION:   0.60,  # assumptions decay
    EntityKind.TOOL_RESULT:  0.40,  # artifacts are large
    EntityKind.SIGNAL:       0.35,  # signals are noisy
    EntityKind.NOTE:         0.20,  # notes are low-priority
}
"""Default per-kind importance weight used by the MemoryCompiler.

These are the v0.4.x defaults. They can be overridden per project by
passing ``importance_overrides=`` to ``MemoryCompiler.compile()``."""


# Type aliases used elsewhere in the codebase
EntityStatus = Literal["active", "superseded", "rejected", "conflicted"]
EntityConfidence = float  # 0.0..1.0


# ---------------------------------------------------------------------------
# Typed entity records
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Entity:
    """Base class for every typed entity in Project Memory.

    Subclassed below for each EntityKind. Subclasses set the ``kind``
    literal and add kind-specific fields. The base class carries the
    cross-cutting fields every entity needs (id, source, timestamps,
    confidence, status, tags).
    """

    # Required fields first (no defaults).
    content: str = ""
    source: str = ""
    # Then defaulted fields.
    kind: EntityKind = EntityKind.NOTE
    id: str = ""
    confidence: float = 1.0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    version: int = 1
    tags: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    status: EntityStatus = "active"

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(
                self, "id", f"ent_{self.kind.value}_{uuid4().hex[:10]}",
            )


@dataclass
class GoalEntity(Entity):
    """A user goal / objective."""

    user_goal_id: str | None = None
    description: str = ""
    kind: EntityKind = EntityKind.GOAL


@dataclass
class DecisionEntity(Entity):
    """A binding decision made during a loop run."""

    decision: str = ""
    rationale: str = ""
    decided_by: str = "loop"  # loop | user | hookify-rule | repair-plan
    kind: EntityKind = EntityKind.DECISION


@dataclass
class FailureEntity(Entity):
    """A repeated or blocking failure."""

    failure_kind: str = ""  # e.g. implementation_bug, missing_test
    occurrences: int = 1
    last_seen_at: datetime = field(default_factory=_now)
    blocked_iteration: int | None = None
    kind: EntityKind = EntityKind.FAILURE


@dataclass
class ProcedureEntity(Entity):
    """A promotable workflow / repeatable recipe."""

    procedure_id: str | None = None
    steps: list[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    kind: EntityKind = EntityKind.PROCEDURE


@dataclass
class DeliveryEntity(Entity):
    """A delivery candidate / release surface."""

    run_id: str = ""
    delivery_status: str = ""  # ready | blocked | incomplete
    quality_score: float = 0.0
    evidence: list[str] = field(default_factory=list)
    kind: EntityKind = EntityKind.DELIVERY


@dataclass
class AssumptionEntity(Entity):
    """An explicit assumption (validated or not)."""

    assumption: str = ""
    validated: bool = False
    kind: EntityKind = EntityKind.ASSUMPTION


@dataclass
class ConstraintEntity(Entity):
    """A binding constraint (policy / budget)."""

    constraint: str = ""
    enforcement: str = "policy"  # policy | budget | hookify-rule
    kind: EntityKind = EntityKind.CONSTRAINT


@dataclass
class ToolResultEntity(Entity):
    """A recorded tool run (artifact)."""

    tool_name: str = ""
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    kind: EntityKind = EntityKind.TOOL_RESULT


@dataclass
class SignalEntity(Entity):
    """A LAIL signal (raw or aggregated)."""

    lail_kind: str = ""  # iteration_started, plan_emitted, build_completed, ...
    iteration_index: int | None = None
    kind: EntityKind = EntityKind.SIGNAL


@dataclass
class NoteEntity(Entity):
    """A free-form project note."""

    kind: EntityKind = EntityKind.NOTE


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Map from kind to the concrete entity class. Used by ``from_item``
# and the MemoryCompiler's typed dispatch.
ENTITY_TYPES: dict[EntityKind, type[Entity]] = {
    EntityKind.GOAL:         GoalEntity,
    EntityKind.DECISION:     DecisionEntity,
    EntityKind.FAILURE:      FailureEntity,
    EntityKind.PROCEDURE:    ProcedureEntity,
    EntityKind.DELIVERY:     DeliveryEntity,
    EntityKind.ASSUMPTION:   AssumptionEntity,
    EntityKind.CONSTRAINT:   ConstraintEntity,
    EntityKind.TOOL_RESULT:  ToolResultEntity,
    EntityKind.SIGNAL:       SignalEntity,
    EntityKind.NOTE:         NoteEntity,
}
"""Mapping ``EntityKind -> concrete Entity subclass``."""


def importance_for(kind: EntityKind, overrides: dict[EntityKind, float] | None = None) -> float:
    """Return the importance weight for ``kind``.

    ``overrides`` (if provided) takes precedence over
    ``DEFAULT_IMPORTANCE``. Missing kinds default to 0.5.
    """
    if overrides and kind in overrides:
        return float(overrides[kind])
    return DEFAULT_IMPORTANCE.get(kind, 0.5)


def from_item(item: Any) -> Entity:
    """Promote a generic ``ProjectMemoryItem`` to a typed ``Entity``.

    Looks up the item's ``type`` string in ``ENTITY_TYPES``. If the
    type is unknown, falls back to a ``NoteEntity`` carrying the
    original content. This is the safest default: never lose data.

    The original ``ProjectMemoryItem`` may have a ``type`` value that
    the pydantic Literal rejects (e.g. a legacy type from before the
    ontology existed). We bypass that by inspecting the string value
    rather than the validated field. If the string does not match any
    known ``EntityKind``, we degrade to a Note.
    """
    from loopos.project_memory.models import ProjectMemoryItem

    if not isinstance(item, ProjectMemoryItem):
        if isinstance(item, Entity):
            return item
        raise TypeError(f"expected ProjectMemoryItem or Entity, got {type(item).__name__}")

    # ``item.type`` may be a Literal-blessed string. If pydantic
    # accepted it, use the value directly. If we got here with a raw
    # string, treat it as the entity kind name.
    kind_str = str(getattr(item, "type", "") or "")
    try:
        kind = EntityKind(kind_str)
    except ValueError:
        kind = EntityKind.NOTE

    cls = ENTITY_TYPES[kind]
    # Common fields that every Entity carries.
    common = {
        "id": item.id,
        "confidence": item.confidence,
        "source": item.source,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "version": item.version,
        "tags": list(item.tags),
        "conflicts": list(item.conflicts),
        "status": item.status,
    }
    # Kind-specific content slot. We pass ``content=`` (the base class
    # field) for kinds that have no primary field of their own, and a
    # kind-specific primary field for kinds that do. NoteEntity is the
    # default for the fallback ``kind``. The ``cast`` keeps mypy quiet
    # about the ``**common`` spread (mypy can't reconcile the
    # ``dict[str, object]`` type of ``common`` with the strict dataclass
    # field types, but the runtime values match exactly).
    common_typed = cast(dict[str, Any], common)
    if cls is GoalEntity:
        return cls(description=item.content, content=item.content, **common_typed)
    if cls is DecisionEntity:
        return cls(decision=item.content, content=item.content, **common_typed)
    if cls is FailureEntity:
        return cls(failure_kind="unspecified", content=item.content, **common_typed)
    if cls is ProcedureEntity:
        return cls(content=item.content, **common_typed)
    if cls is DeliveryEntity:
        return cls(content=item.content, **common_typed)
    if cls is AssumptionEntity:
        return cls(assumption=item.content, content=item.content, **common_typed)
    if cls is ConstraintEntity:
        return cls(constraint=item.content, content=item.content, **common_typed)
    if cls is ToolResultEntity:
        return cls(content=item.content, **common_typed)
    if cls is SignalEntity:
        return cls(lail_kind=item.content, content=item.content, **common_typed)
    # NoteEntity (or any other kind without a primary content field):
    return cls(content=item.content, **common_typed)


__all__ = [
    "Entity",
    "EntityKind",
    "EntityStatus",
    "EntityConfidence",
    "GoalEntity",
    "DecisionEntity",
    "FailureEntity",
    "ProcedureEntity",
    "DeliveryEntity",
    "AssumptionEntity",
    "ConstraintEntity",
    "ToolResultEntity",
    "SignalEntity",
    "NoteEntity",
    "ENTITY_TYPES",
    "DEFAULT_IMPORTANCE",
    "importance_for",
    "from_item",
]
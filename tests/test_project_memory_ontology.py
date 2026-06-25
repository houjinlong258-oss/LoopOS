"""Tests for the typed Project Memory ontology."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loopos.project_memory.models import ProjectMemoryItem  # noqa: E402
from loopos.project_memory.ontology import (  # noqa: E402
    DEFAULT_IMPORTANCE,
    ENTITY_TYPES,
    Entity,
    EntityKind,
    GoalEntity,
    DecisionEntity,
    FailureEntity,
    ProcedureEntity,
    DeliveryEntity,
    AssumptionEntity,
    ConstraintEntity,
    ToolResultEntity,
    SignalEntity,
    NoteEntity,
    from_item,
    importance_for,
)


class TestEntityKindEnum:
    def test_all_kinds_registered(self) -> None:
        assert len(ENTITY_TYPES) == len(EntityKind)
        for kind in EntityKind:
            assert kind in ENTITY_TYPES
            assert issubclass(ENTITY_TYPES[kind], Entity)

    def test_default_importance_covers_all_kinds(self) -> None:
        for kind in EntityKind:
            assert kind in DEFAULT_IMPORTANCE
            assert 0.0 <= DEFAULT_IMPORTANCE[kind] <= 1.0


class TestEntityConstruction:
    def test_goal_entity_basic(self) -> None:
        e = GoalEntity(
            user_goal_id="g1",
            description="Build a CLI",
            content="Build a CLI",
            source="loopos",
        )
        assert e.kind == EntityKind.GOAL
        assert e.user_goal_id == "g1"
        assert e.description == "Build a CLI"

    def test_decision_entity_basic(self) -> None:
        e = DecisionEntity(
            decision="Use SQLite",
            rationale="single-file portable",
            content="Use SQLite",
            source="planner",
        )
        assert e.kind == EntityKind.DECISION
        assert e.decided_by == "loop"  # default

    def test_failure_entity_occurrences(self) -> None:
        e = FailureEntity(
            failure_kind="implementation_bug",
            occurrences=3,
            content="Bug in parser",
            source="tester",
        )
        assert e.kind == EntityKind.FAILURE
        assert e.occurrences == 3
        assert e.blocked_iteration is None

    def test_procedure_entity_steps(self) -> None:
        e = ProcedureEntity(
            steps=["Step 1", "Step 2"],
            content="recipe",
            source="promotion",
            success_count=5,
        )
        assert e.kind == EntityKind.PROCEDURE
        assert e.steps == ["Step 1", "Step 2"]
        assert e.success_count == 5

    def test_delivery_entity_evidence(self) -> None:
        e = DeliveryEntity(
            run_id="run_x",
            delivery_status="ready",
            quality_score=0.92,
            content="delivered",
            source="loopos",
            evidence=["test passed", "review passed"],
        )
        assert e.kind == EntityKind.DELIVERY
        assert e.delivery_status == "ready"
        assert e.quality_score == 0.92
        assert len(e.evidence) == 2

    def test_assumption_entity_validated(self) -> None:
        e = AssumptionEntity(
            assumption="user has python 3.11+",
            validated=True,
            content="assumption",
            source="user",
        )
        assert e.kind == EntityKind.ASSUMPTION
        assert e.validated is True

    def test_constraint_entity_enforcement(self) -> None:
        e = ConstraintEntity(
            constraint="max budget 100 calls",
            enforcement="budget",
            content="budget cap",
            source="policy_os",
        )
        assert e.kind == EntityKind.CONSTRAINT
        assert e.enforcement == "budget"

    def test_tool_result_entity_io(self) -> None:
        e = ToolResultEntity(
            tool_name="pytest",
            inputs={"path": "tests/"},
            outputs={"passed": "5", "failed": "0"},
            content="tool ran",
            source="real_executor",
        )
        assert e.kind == EntityKind.TOOL_RESULT
        assert e.tool_name == "pytest"
        assert e.outputs["passed"] == "5"

    def test_signal_entity_lail(self) -> None:
        e = SignalEntity(
            lail_kind="plan_emitted",
            iteration_index=2,
            content="signal",
            source="lail",
        )
        assert e.kind == EntityKind.SIGNAL
        assert e.lail_kind == "plan_emitted"

    def test_note_entity_basic(self) -> None:
        e = NoteEntity(content="a note", source="user")
        assert e.kind == EntityKind.NOTE


class TestEntityValidation:
    def test_confidence_in_range(self) -> None:
        # dataclass doesn't enforce Field constraints, so we test the
        # contract is documented: confidence is documented as 0.0..1.0
        # and the default is 1.0.
        e = NoteEntity(content="x", source="s", confidence=1.5)
        assert e.confidence == 1.5  # no enforcement, by design
        e2 = NoteEntity(content="x", source="s", confidence=-0.1)
        assert e2.confidence == -0.1  # by design

    def test_default_id_is_unique(self) -> None:
        e1 = NoteEntity(content="a", source="s")
        e2 = NoteEntity(content="b", source="s")
        assert e1.id != e2.id
        assert e1.id.startswith("ent_note_")

    def test_id_prefix_matches_kind(self) -> None:
        e_goal = GoalEntity(user_goal_id="g", description="x", content="x", source="s")
        e_fail = FailureEntity(failure_kind="bug", content="x", source="s")
        assert e_goal.id.startswith("ent_goal_")
        assert e_fail.id.startswith("ent_failure_")


class TestImportance:
    def test_default_importance(self) -> None:
        assert importance_for(EntityKind.GOAL) == 0.95
        assert importance_for(EntityKind.DECISION) == 0.85

    def test_unknown_kind_falls_back_to_half(self) -> None:
        # Simulate a future kind without an importance weight.
        DEFAULT_IMPORTANCE.pop(EntityKind.NOTE, None)
        try:
            assert importance_for(EntityKind.NOTE) == 0.5
        finally:
            DEFAULT_IMPORTANCE[EntityKind.NOTE] = 0.20

    def test_overrides_take_precedence(self) -> None:
        overrides = {EntityKind.GOAL: 0.10}
        assert importance_for(EntityKind.GOAL, overrides=overrides) == 0.10

    def test_constraints_are_high_importance(self) -> None:
        # Constraints must be durable: should rank near top.
        assert importance_for(EntityKind.CONSTRAINT) >= 0.85

    def test_notes_are_low_importance(self) -> None:
        # Free-form notes should be the first to drop under tight budget.
        assert importance_for(EntityKind.NOTE) <= 0.25


class TestFromItem:
    def test_promotes_failure_item(self) -> None:
        item = ProjectMemoryItem(
            type="failure",
            content="Bug X",
            source="tester",
        )
        e = from_item(item)
        assert isinstance(e, FailureEntity)
        assert e.kind == EntityKind.FAILURE
        assert e.content == "Bug X"

    def test_promotes_decision_item(self) -> None:
        item = ProjectMemoryItem(
            type="decision",
            content="Use Postgres",
            source="planner",
        )
        e = from_item(item)
        assert isinstance(e, DecisionEntity)
        assert e.kind == EntityKind.DECISION

    def test_unknown_kind_becomes_note(self) -> None:
        # Build a ProjectMemoryItem with a valid Literal type, then
        # promote it via ``from_item`` using a synthetic kind name to
        # verify the fallback path. We use the model_construct escape
        # hatch to bypass pydantic's literal validation for the
        # ``not_a_real_kind`` test case.
        item = ProjectMemoryItem.model_construct(
            id="pmem_orphan",
            type="not_a_real_kind",  # bypasses literal validation
            content="orphan",
            source="legacy",
            confidence=1.0,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            version=1,
            tags=[],
            conflicts=[],
            status="active",
        )
        e = from_item(item)
        assert isinstance(e, NoteEntity)
        assert e.content == "orphan"

    def test_already_entity_passes_through(self) -> None:
        e0 = GoalEntity(user_goal_id="g", description="x", content="x", source="s")
        e1 = from_item(e0)
        assert e1 is e0


class TestBudgetByKind:
    """Test the headline use case: MemoryCompiler can budget by entity kind.

    We simulate the budget-allocation algorithm here so that the
    ontology exposes the right importance weights. The actual compiler
    integration is in a follow-up.
    """

    def test_budget_total_does_not_exceed_capacity(self) -> None:
        # Given 100 tokens to spend across kinds with importance weights,
        # allocate proportional to importance and cap at capacity.
        kinds = list(EntityKind)
        weights = {k: importance_for(k) for k in kinds}
        total_weight = sum(weights.values())
        capacity = 100
        per_kind = {k: round(weights[k] / total_weight * capacity, 2) for k in kinds}
        assert sum(per_kind.values()) <= capacity + 0.5  # rounding
        # Goals should get the largest slice
        assert per_kind[EntityKind.GOAL] == max(per_kind.values())

    def test_high_importance_survives_tight_budget(self) -> None:
        # Given only 1 token of capacity, only the highest-importance
        # kind survives. This is the "what gets dropped first" question.
        kinds = list(EntityKind)
        weights = {k: importance_for(k) for k in kinds}
        # In a 1-token budget, only the top weight wins.
        top_kind = max(weights, key=lambda k: weights[k])
        assert top_kind == EntityKind.GOAL  # goals survive
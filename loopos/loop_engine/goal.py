"""Goal normalization and success-criteria generation.

The ``GoalEngine`` is deterministic and offline. It does not call an
LLM. It is a thin wrapper around text normalization and a small
keyword-based rule set for criteria generation. Real LLM-driven
understanding is a v0.4.x pluggable concern.
"""

from __future__ import annotations

import re
from typing import Any

from loopos.loop_engine.models import (
    CriterionType,
    SuccessCriteria,
    SuccessCriterion,
    UserGoal,
)


_KEYWORD_CRITERIA: list[tuple[str, str, CriterionType]] = [
    (r"\btests?\b|\bpytest\b|\bunittest\b", "Test coverage exists for the goal", "test"),
    (r"\bdocs?\b|\bdocumentation\b|\breadme\b", "Documentation covers the change", "doc"),
    (r"\bdesign\b|\barchitecture\b|\bstructure\b", "Design is documented and reviewable", "quality"),
    (r"\bship\b|\bdeliver\b|\brelease\b|\bpublish\b", "Delivery artifact is producible", "delivery"),
    (r"\buser\b|\bcustomer\b|\bgoal\b|\bobjective\b", "User goal is satisfied end-to-end", "user_alignment"),
    (r"\bperformant\b|\bfast\b|\bslow\b|\blatency\b", "Quality is within an acceptable range", "quality"),
    (r"\bsecure\b|\bsecurity\b|\bsafe\b", "Security implications are reviewed", "quality"),
]


class GoalEngine:
    """Normalize a user goal and synthesize a starter set of success criteria."""

    def normalize(self, goal: UserGoal | str) -> UserGoal:
        if isinstance(goal, str):
            goal = UserGoal(raw_goal=goal)
        if not goal.normalized_goal:
            goal = goal.normalized()
        return goal

    def generate_criteria(
        self,
        goal: UserGoal,
        extra: list[SuccessCriterion] | None = None,
    ) -> SuccessCriteria:
        """Produce a ``SuccessCriteria`` set from the goal text.

        A small keyword scan is used; results are deterministic and
        fully explainable. Callers may pass additional ``extra`` criteria
        to extend or override the defaults.
        """
        text = (goal.normalized_goal or goal.raw_goal).lower()
        seen_ids: set[str] = set()
        items: list[SuccessCriterion] = []

        for pattern, description, ctype in _KEYWORD_CRITERIA:
            if re.search(pattern, text):
                cid = f"crit_{ctype}_{len(items)}"
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                items.append(
                    SuccessCriterion(
                        id=cid,
                        description=description,
                        type=ctype,
                        required=(ctype in {"test", "delivery", "user_alignment"}),
                    )
                )

        if not items:
            # Always have at least one functional criterion so the loop
            # has something to converge against.
            items.append(
                SuccessCriterion(
                    id="crit_functional_0",
                    description="Functional goal is satisfied end-to-end",
                    type="functional",
                    required=True,
                )
            )

        if extra:
            items.extend(extra)

        return SuccessCriteria(
            items=items,
            minimum_quality_score=0.75,
            required_tests=[],
            delivery_requirements=[],
        )


__all__ = ["GoalEngine"]


# Re-export to help static analyzers
_ = Any

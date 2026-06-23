"""Provider budget guard and process-level BudgetLedger.

The :class:`ProviderBudget` is the per-scope mutable tracker. The
:class:`BudgetLedger` is the process-level singleton that ensures
the Workbench and the CLI share one accounting path: a request
that flows through both paths cannot double-spend.

Ledger keys are ``(provider_id, model_id, session_id)`` tuples. A
``session_id=None`` means "process-wide" and groups by provider+model
only. When a budget exceeds its ``max_usd``, all subsequent calls
on the same key are blocked until the budget is reset.
"""

from __future__ import annotations

import threading
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BudgetDecision(BaseModel):
    """Structured result of a budget check."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason_codes: list[str] = Field(default_factory=list)
    used_usd: float = 0.0
    requested_estimate_usd: float = 0.0
    max_usd: float = 0.0
    requires_approval: bool = False


class ProviderBudget(BaseModel):
    """Mutable budget tracker for a sequence of provider calls."""

    model_config = ConfigDict(extra="forbid")

    max_usd: float = Field(default=0.0, ge=0.0)
    used_usd: float = Field(default=0.0, ge=0.0)
    max_requests: int | None = Field(default=None, ge=0)
    used_requests: int = Field(default=0, ge=0)
    require_approval_above_usd: float = Field(default=1.0, ge=0.0)

    def check(self, estimated_cost_usd: float, *, approved: bool = False) -> BudgetDecision:
        """Return a :class:`BudgetDecision` for a prospective call."""
        reasons: list[str] = []
        prospective = self.used_usd + max(0.0, estimated_cost_usd)

        if self.max_requests is not None and self.used_requests >= self.max_requests:
            reasons.append("provider_request_count_exceeded")

        if self.max_usd > 0.0 and prospective > self.max_usd:
            reasons.append("provider_budget_exceeded")

        requires_approval = estimated_cost_usd > self.require_approval_above_usd and not approved
        if requires_approval:
            reasons.append("provider_call_requires_approval")

        allowed = not reasons
        return BudgetDecision(
            allowed=allowed,
            reason_codes=reasons,
            used_usd=self.used_usd,
            requested_estimate_usd=estimated_cost_usd,
            max_usd=self.max_usd,
            requires_approval=requires_approval,
        )

    def commit(self, actual_cost_usd: float) -> None:
        """Record a completed call's actual cost."""
        self.used_usd += max(0.0, actual_cost_usd)
        self.used_requests += 1


# ---------------------------------------------------------------------------
# BudgetLedger: process-level shared accounting
# ---------------------------------------------------------------------------


LedgerKey = tuple[str, str, Optional[str]]
"""``(provider_id, model_id, session_id)``.

A ``session_id=None`` means "process-wide"; the ledger still keeps
a per-(provider, model) entry under that key, so the Workbench and
the CLI land on the same accounting path even if neither carries
an explicit session id.
"""


class BudgetLedger:
    """Process-level shared budget accounting.

    Every call site that issues a live provider request goes through
    :meth:`check` then :meth:`commit`. The Workbench and the CLI share
    the *same* ``BudgetLedger`` instance, so spend cannot be
    double-counted across the two paths.

    Thread-safety: a single :class:`threading.Lock` guards all
    mutations. The expected concurrency is low (one operator, one
    CLI), so a single lock is correct and obvious.

    Lifecycle: callers should pass an explicit ``session_id`` when
    they have one (e.g. a goal id). Without it, the ledger groups by
    ``(provider_id, model_id)`` only — still better than the
    pre-hardening per-call ``ProviderBudget`` instances, which were
    not shared at all.
    """

    def __init__(self) -> None:
        self._entries: dict[LedgerKey, ProviderBudget] = {}
        self._lock = threading.Lock()

    # ----- lookups ---------------------------------------------------------

    @staticmethod
    def make_key(
        provider_id: str,
        model_id: str,
        session_id: Optional[str] = None,
    ) -> LedgerKey:
        """Build a normalized ledger key.

        ``provider_id`` and ``model_id`` are stripped and lowercased
        so the same call always resolves to the same key regardless
        of where it came from.
        """
        return (
            (provider_id or "").strip().lower(),
            (model_id or "").strip().lower(),
            (session_id or "").strip() or None,
        )

    def get(self, key: LedgerKey) -> Optional[ProviderBudget]:
        with self._lock:
            return self._entries.get(key)

    def get_or_create(
        self,
        provider_id: str,
        model_id: str,
        session_id: Optional[str],
        max_usd: float,
        max_requests: Optional[int] = None,
    ) -> ProviderBudget:
        """Return the existing :class:`ProviderBudget` for ``key``, or
        create one if absent.

        Once a budget exists for a key, ``max_usd`` is *not*
        overwritten. This is the property that prevents
        double-spending: even if two callers pass different
        ``max_usd`` values, both see the same actual spend.
        """
        key = self.make_key(provider_id, model_id, session_id)
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None:
                return existing
            budget = ProviderBudget(
                max_usd=max_usd,
                used_usd=0.0,
                max_requests=max_requests,
            )
            self._entries[key] = budget
            return budget

    # ----- mutations -------------------------------------------------------

    def check(
        self,
        provider_id: str,
        model_id: str,
        session_id: Optional[str],
        estimated_cost_usd: float,
        *,
        approved: bool = False,
    ) -> BudgetDecision:
        """Run :meth:`ProviderBudget.check` on the ledger entry.

        If no entry exists for the key, returns an *allowed*
        decision with ``used_usd=0`` and ``max_usd=0``. This matches
        the pre-hardening behavior when the caller passes
        ``budget_usd=0`` (no budget). It does not silently create an
        entry: callers that want budget tracking must call
        :meth:`get_or_create` first.
        """
        key = self.make_key(provider_id, model_id, session_id)
        with self._lock:
            budget = self._entries.get(key)
            if budget is None:
                return BudgetDecision(
                    allowed=True,
                    reason_codes=[],
                    used_usd=0.0,
                    requested_estimate_usd=estimated_cost_usd,
                    max_usd=0.0,
                    requires_approval=False,
                )
            return budget.check(estimated_cost_usd, approved=approved)

    def commit(
        self,
        provider_id: str,
        model_id: str,
        session_id: Optional[str],
        actual_cost_usd: float,
    ) -> bool:
        """Record a completed call's cost on the ledger entry.

        Returns ``True`` if the entry exists and the commit landed,
        ``False`` if no entry exists for the key. Callers that pass
        ``budget_usd=0`` and did not call :meth:`get_or_create` get
        ``False`` here; their spend is *not* tracked because they
        opted out of budget tracking. This is intentional: the
        ledger never invents a budget the caller did not ask for.
        """
        key = self.make_key(provider_id, model_id, session_id)
        with self._lock:
            budget = self._entries.get(key)
            if budget is None:
                return False
            budget.commit(actual_cost_usd)
            return True

    def snapshot(self) -> dict[LedgerKey, dict[str, float]]:
        """Return a JSON-serialisable snapshot of every ledger entry."""
        with self._lock:
            return {
                key: {
                    "max_usd": budget.max_usd,
                    "used_usd": budget.used_usd,
                    "used_requests": budget.used_requests,
                }
                for key, budget in self._entries.items()
            }

    def reset(self) -> None:
        """Drop every ledger entry. Intended for tests."""
        with self._lock:
            self._entries.clear()


# ----- process-level singleton ---------------------------------------------

_DEFAULT_LEDGER: Optional[BudgetLedger] = None
_DEFAULT_LEDGER_LOCK = threading.Lock()


def get_default_ledger() -> BudgetLedger:
    """Return the process-wide :class:`BudgetLedger`.

    The default instance is created lazily on first call. Tests that
    need isolation should construct their own :class:`BudgetLedger`
    rather than call this function.
    """
    global _DEFAULT_LEDGER
    with _DEFAULT_LEDGER_LOCK:
        if _DEFAULT_LEDGER is None:
            _DEFAULT_LEDGER = BudgetLedger()
        return _DEFAULT_LEDGER


def reset_default_ledger() -> None:
    """Drop the process-wide ledger. Intended for tests."""
    global _DEFAULT_LEDGER
    with _DEFAULT_LEDGER_LOCK:
        _DEFAULT_LEDGER = None


__all__ = [
    "ProviderBudget",
    "BudgetDecision",
    "BudgetLedger",
    "LedgerKey",
    "get_default_ledger",
    "reset_default_ledger",
]
"""Local JSON-file persistence for Fusion Router plans and verdicts.

This module gives the Fusion Router a minimal durable layer so
``fusion-router status`` and ``mad-dog status`` can return the
persisted plan / verdict instead of the v0.2 ``unsupported``
payload. The persistence layer is intentionally thin:

* one JSON document per ``fusion_id``;
* deterministic serialisation (canonical key order via
  :mod:`loopos.fusion_router.trace`);
* no new dependencies;
* no DB / web UI / TUI / daemon;
* no network or live provider calls.

Layering:

* :class:`FusionPlanStore` -- per-fusion-id JSON document store.
  Each plan is written to ``<root>/plans/<fusion_id>.json``. The
  verdict (if any) is written to ``<root>/verdicts/<fusion_id>.json``.
* :func:`load_plan` / :func:`load_verdict` -- read by fusion_id
  (or by ``fusion_id + verdict_id`` for an explicit verdict).
* :func:`list_plans` / :func:`list_verdicts` -- audit helpers used
  by ``fusion-router status`` to surface the available plans /
  verdicts when the caller does not know the exact id.

The store is the single source of truth for the CLI status
command. The trace bridge (:mod:`loopos.fusion_router.trace`)
remains the durable audit trail for runtime events; this module
persists the structured plan / verdict for review.

The runner (:mod:`loopos.fusion_router.runner`) writes the plan
and verdict it produces via :class:`FusionPlanStore`. The CLI
``status`` command reads them back. The store is deliberately
synchronous and file-based: a DB would be over-engineering for
v0.2.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loopos.fusion_router.models import FusionPlan, FusionVerdict
from loopos.fusion_router.trace import _ordered, _PLAN_KEY_ORDER, _VERDICT_KEY_ORDER


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` atomically so a crash never produces half a file.

    Uses a sibling tempfile + ``os.replace`` so a parallel reader
    either sees the old contents or the new contents, never a
    truncated intermediate.
    """

    _ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, ensure_ascii=False))
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
        return data


# Sentinel keys the store adds on write; the typed models use
# ``extra='forbid'`` so we must strip them before validation.
_META_KEYS = frozenset({"_saved_at", "_schema_version"})


def _strip_meta(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with the store's metadata keys removed."""

    return {key: value for key, value in payload.items() if key not in _META_KEYS}


class FusionPlanStore:
    """File-backed persistence for :class:`FusionPlan` and :class:`FusionVerdict`.

    Directory layout::

        <root>/
          plans/<fusion_id>.json
          verdicts/<fusion_id>.json     # optional verdict
          verdicts/<fusion_id>__<verdict_seq>.json  # multiple verdicts per plan

    ``<root>`` defaults to ``.loopos/fusion`` (relative to the
    current working directory); tests pass a ``tempfile.TemporaryDirectory``
    root for isolation.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(".loopos/fusion")
        _ensure_dir(self.root)
        _ensure_dir(self.root / "plans")
        _ensure_dir(self.root / "verdicts")

    # ------------------------------------------------------------------
    # Plan persistence
    # ------------------------------------------------------------------

    def save_plan(self, plan: FusionPlan) -> Path:
        """Persist ``plan`` to disk and return the path."""

        payload = _ordered(
            plan.model_dump(mode="json"),
            _PLAN_KEY_ORDER,
        )
        payload["_saved_at"] = utc_now().isoformat()
        payload["_schema_version"] = 1
        path = self.root / "plans" / f"{plan.fusion_id}.json"
        _atomic_write_json(path, payload)
        return path

    def load_plan(self, fusion_id: str) -> FusionPlan | None:
        path = self.root / "plans" / f"{fusion_id}.json"
        if not path.exists():
            return None
        return FusionPlan.model_validate(_strip_meta(_read_json(path)))

    def has_plan(self, fusion_id: str) -> bool:
        return (self.root / "plans" / f"{fusion_id}.json").exists()

    def list_plans(self) -> list[str]:
        plans_dir = self.root / "plans"
        if not plans_dir.exists():
            return []
        return sorted(
            path.stem
            for path in plans_dir.glob("*.json")
            if not path.name.startswith("_")
        )

    # ------------------------------------------------------------------
    # Verdict persistence
    # ------------------------------------------------------------------

    def save_verdict(self, verdict: FusionVerdict, *, seq: int | None = None) -> Path:
        """Persist ``verdict`` to disk and return the path.

        A fusion_id may accumulate multiple verdicts
        (``accepted`` followed by ``needs_repair`` etc.). The
        ``seq`` argument disambiguates them; ``None`` writes a
        single canonical verdict (the latest).
        """

        payload = _ordered(
            verdict.model_dump(mode="json"),
            _VERDICT_KEY_ORDER,
        )
        payload["_saved_at"] = utc_now().isoformat()
        payload["_schema_version"] = 1
        if seq is None:
            path = self.root / "verdicts" / f"{verdict.fusion_id}.json"
        else:
            path = (
                self.root / "verdicts"
                / f"{verdict.fusion_id}__{seq:03d}.json"
            )
        _atomic_write_json(path, payload)
        return path

    def load_verdict(self, fusion_id: str) -> FusionVerdict | None:
        path = self.root / "verdicts" / f"{fusion_id}.json"
        if not path.exists():
            return None
        return FusionVerdict.model_validate(_strip_meta(_read_json(path)))

    def load_verdicts(self, fusion_id: str) -> list[FusionVerdict]:
        """Return all verdicts for ``fusion_id`` in order.

        Ordered by sequence suffix (``_001``, ``_002``, ...).
        The single canonical verdict (``fusion_id.json``) is the
        most recent and is appended last when present.
        """

        verdicts_dir = self.root / "verdicts"
        if not verdicts_dir.exists():
            return []
        sequences: list[FusionVerdict] = []
        canonical: FusionVerdict | None = None
        for path in verdicts_dir.glob(f"{fusion_id}*.json"):
            data = _strip_meta(_read_json(path))
            if path.stem == fusion_id:
                canonical = FusionVerdict.model_validate(data)
                continue
            sequences.append(FusionVerdict.model_validate(data))
        sequences.sort(key=lambda v: v.trace_ids and v.trace_ids[0] or "")
        if canonical is not None:
            sequences.append(canonical)
        return sequences

    def has_verdict(self, fusion_id: str) -> bool:
        return (self.root / "verdicts" / f"{fusion_id}.json").exists() or any(
            (self.root / "verdicts").glob(f"{fusion_id}__*.json")
        )

    def list_verdicts(self) -> list[str]:
        verdicts_dir = self.root / "verdicts"
        if not verdicts_dir.exists():
            return []
        return sorted(
            path.stem.split("__")[0]
            for path in verdicts_dir.glob("*.json")
            if not path.name.startswith("_")
        )


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def load_plan(root: str | Path, fusion_id: str) -> FusionPlan | None:
    return FusionPlanStore(root).load_plan(fusion_id)


def load_verdict(root: str | Path, fusion_id: str) -> FusionVerdict | None:
    return FusionPlanStore(root).load_verdict(fusion_id)


def list_plans(root: str | Path) -> list[str]:
    return FusionPlanStore(root).list_plans()


def list_verdicts(root: str | Path) -> list[str]:
    return FusionPlanStore(root).list_verdicts()


__all__ = [
    "FusionPlanStore",
    "load_plan",
    "load_verdict",
    "list_plans",
    "list_verdicts",
]
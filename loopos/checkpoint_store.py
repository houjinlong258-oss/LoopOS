"""Persistent checkpoint store for the Project Training Loop.

The v0.4.0 closeout target is *cross-process* state. ``loopos loop
run`` must produce a run-id, write a directory under
``<data_dir>/runs/<run_id>/``, and let ``loopos loop status`` /
``loopos loop deliver`` read that directory in a fresh process.

Directory layout (all files are JSON unless noted)::

    <data_dir>/runs/<run_id>/
        loop_state.json              full LoopState snapshot
        checkpoint.json              latest ProjectCheckpoint
        iterations.jsonl             one TrainingIteration per line
        lail_signals.jsonl           one LAIL signal per line
        memory_context_packets.jsonl one ContextPacket per line
        quality_scores.jsonl         one QualityScore per line
        convergence_report.json      latest ConvergenceReport
        delivery_candidate.json      latest DeliveryCandidate (or empty)

The store is **append-only** for the per-iteration files
(``iterations.jsonl``, ``lail_signals.jsonl``, ...) and
**overwrite-on-write** for the per-run snapshots
(``loop_state.json``, ``convergence_report.json``, ...). This mirrors
ML training: the per-epoch log is append-only; the latest
checkpoint and the latest metrics are overwritten.

The store is deterministic and offline. There is no network, no
SQL, no async. The on-disk format is plain JSON; the per-iteration
files are JSONL so a single ``open(..., 'a')`` is enough.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# A safe run-id: short, URL-safe, deterministic-prefixed.
_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{4,64}$")


def is_valid_run_id(run_id: str) -> bool:
    return bool(_RUN_ID_RE.match(run_id))


def make_run_id(prefix: str = "run") -> str:
    """Generate a run id of the form ``<prefix>_<hex>``.

    The id is short, URL-safe, and sortable by creation time when
    paired with the on-disk directory's mtime.
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def default_data_dir() -> Path:
    """Return the default ``.loopos`` data directory."""
    return Path(os.environ.get("LOOPOS_DATA_DIR", ".loopos")).resolve()


def runs_root(data_dir: Path | None = None) -> Path:
    """Return the ``runs/`` directory under the given data dir."""
    return (data_dir or default_data_dir()) / "runs"


def run_dir(run_id: str, data_dir: Path | None = None) -> Path:
    """Return the per-run directory. The directory is **not** created."""
    if not is_valid_run_id(run_id):
        raise ValueError(f"invalid run id: {run_id!r}")
    return runs_root(data_dir) / run_id


@dataclass
class RunSummary:
    """A small summary record the CLI uses to list / pick runs."""

    run_id: str
    path: Path
    mtime: float
    goal: str
    status: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write ``payload`` to ``path`` atomically (temp + rename)."""
    _ensure_dir(path.parent)
    text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
    # Windows-friendly atomic write: write to temp, fsync, rename.
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # Some filesystems do not support fsync; ignore.
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, payload: Any) -> None:
    """Append ``payload`` as a single JSON line to ``path``."""
    _ensure_dir(path.parent)
    line = json.dumps(payload, default=str, ensure_ascii=False)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
        f.flush()


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_jsonl(path: Path) -> list[Any]:
    if not path.exists():
        return []
    out: list[Any] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip corrupt lines so a single bad append does not
                # poison the whole log.
                continue
    return out


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------


def init_run(run_id: str | None, data_dir: Path | None = None) -> tuple[str, Path]:
    """Create the run directory and return ``(run_id, path)``.

    If ``run_id`` is ``None`` a new one is generated. The directory
    is created (and is empty apart from a ``created_at`` marker).
    """
    if run_id is None:
        run_id = make_run_id()
    elif not is_valid_run_id(run_id):
        raise ValueError(f"invalid run id: {run_id!r}")
    path = _ensure_dir(run_dir(run_id, data_dir))
    marker = path / "created_at"
    if not marker.exists():
        marker.write_text(
            json.dumps({"run_id": run_id, "created_at": time.time()}),
            encoding="utf-8",
        )
    return run_id, path


def list_runs(data_dir: Path | None = None) -> list[RunSummary]:
    """List known runs in ``data_dir``, newest first."""
    root = runs_root(data_dir)
    if not root.exists():
        return []
    out: list[RunSummary] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if not is_valid_run_id(child.name):
            continue
        mtime = child.stat().st_mtime
        # The loop_state.json holds the goal + status; if missing,
        # we use placeholders so listing still works.
        loop_state_path = child / "loop_state.json"
        goal = "?"
        status = "?"
        if loop_state_path.exists():
            try:
                d = _read_json(loop_state_path)
                goal = d.get("goal", {}).get("raw_goal", "?")
                status = d.get("current_status", "?")
            except Exception:
                pass
        out.append(RunSummary(
            run_id=child.name,
            path=child,
            mtime=mtime,
            goal=goal,
            status=status,
        ))
    out.sort(key=lambda r: r.mtime, reverse=True)
    return out


def latest_run_id(data_dir: Path | None = None) -> str | None:
    runs = list_runs(data_dir)
    return runs[0].run_id if runs else None


# ---------------------------------------------------------------------------
# Per-iteration append-only logs
# ---------------------------------------------------------------------------


def append_iteration(run_id: str, iteration: dict[str, Any], data_dir: Path | None = None) -> Path:
    p = run_dir(run_id, data_dir) / "iterations.jsonl"
    _append_jsonl(p, iteration)
    return p


def append_lail_signal(run_id: str, signal: dict[str, Any], data_dir: Path | None = None) -> Path:
    p = run_dir(run_id, data_dir) / "lail_signals.jsonl"
    _append_jsonl(p, signal)
    return p


def append_memory_packet(
    run_id: str, packet: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "memory_context_packets.jsonl"
    _append_jsonl(p, packet)
    return p


def append_quality_score(
    run_id: str, score: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "quality_scores.jsonl"
    _append_jsonl(p, score)
    return p


# ---------------------------------------------------------------------------
# Per-run snapshots (overwrite-on-write)
# ---------------------------------------------------------------------------


def write_loop_state(
    run_id: str, state: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "loop_state.json"
    _atomic_write_json(p, state)
    return p


def write_checkpoint(
    run_id: str, checkpoint: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "checkpoint.json"
    _atomic_write_json(p, checkpoint)
    return p


def write_convergence_report(
    run_id: str, report: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "convergence_report.json"
    _atomic_write_json(p, report)
    return p


def write_delivery_candidate(
    run_id: str, candidate: dict[str, Any], data_dir: Path | None = None
) -> Path:
    p = run_dir(run_id, data_dir) / "delivery_candidate.json"
    _atomic_write_json(p, candidate)
    return p


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def read_loop_state(run_id: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    p = run_dir(run_id, data_dir) / "loop_state.json"
    if not p.exists():
        return None
    result: dict[str, Any] = _read_json(p)
    return result


def read_checkpoint(run_id: str, data_dir: Path | None = None) -> dict[str, Any] | None:
    p = run_dir(run_id, data_dir) / "checkpoint.json"
    if not p.exists():
        return None
    result: dict[str, Any] = _read_json(p)
    return result


def read_convergence_report(
    run_id: str, data_dir: Path | None = None
) -> dict[str, Any] | None:
    p = run_dir(run_id, data_dir) / "convergence_report.json"
    if not p.exists():
        return None
    result: dict[str, Any] = _read_json(p)
    return result


def read_delivery_candidate(
    run_id: str, data_dir: Path | None = None
) -> dict[str, Any] | None:
    p = run_dir(run_id, data_dir) / "delivery_candidate.json"
    if not p.exists():
        return None
    result: dict[str, Any] = _read_json(p)
    return result


def read_iterations(run_id: str, data_dir: Path | None = None) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir(run_id, data_dir) / "iterations.jsonl")


def read_lail_signals(run_id: str, data_dir: Path | None = None) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir(run_id, data_dir) / "lail_signals.jsonl")


def read_memory_packets(run_id: str, data_dir: Path | None = None) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir(run_id, data_dir) / "memory_context_packets.jsonl")


def read_quality_scores(run_id: str, data_dir: Path | None = None) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir(run_id, data_dir) / "quality_scores.jsonl")


__all__ = [
    "RunSummary",
    "append_iteration",
    "append_lail_signal",
    "append_memory_packet",
    "append_quality_score",
    "default_data_dir",
    "init_run",
    "is_valid_run_id",
    "latest_run_id",
    "list_runs",
    "make_run_id",
    "read_checkpoint",
    "read_convergence_report",
    "read_delivery_candidate",
    "read_iterations",
    "read_lail_signals",
    "read_loop_state",
    "read_memory_packets",
    "read_quality_scores",
    "run_dir",
    "runs_root",
    "write_checkpoint",
    "write_convergence_report",
    "write_delivery_candidate",
    "write_loop_state",
]

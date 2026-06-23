"""v0.3 CLI: ``loopos session`` command.

Three sub-commands:

* ``list``   - list recent sessions from the data dir
* ``status`` - show one session's status
* ``events`` - show one session's events
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.cli.context import data_paths


def session_command(
    action: str = "list",
    session_id: str | None = None,
    *,
    data_dir: str = ".loopos",
    json_output: bool = False,
) -> int:
    paths = data_paths(Path(data_dir))
    if action == "list":
        sessions = _list_sessions(paths)
        if json_output:
            print(json.dumps(sessions, ensure_ascii=False, indent=2))
        else:
            _print_sessions_table(sessions)
        return 0
    if action == "status":
        if not session_id:
            return _emit_error(
                "session_id_required",
                "`session status` requires a session id",
                json_output=json_output,
            )
        info = _session_info(paths, session_id)
        if info is None:
            return _emit_error(
                "session_not_found",
                f"session {session_id!r} not found",
                json_output=json_output,
            )
        if json_output:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            for key, value in info.items():
                print(f"{key}: {value}")
        return 0
    if action == "events":
        if not session_id:
            return _emit_error(
                "session_id_required",
                "`session events` requires a session id",
                json_output=json_output,
            )
        events = _session_events(paths, session_id)
        if json_output:
            print(json.dumps(events, ensure_ascii=False, indent=2))
        else:
            for e in events:
                print(f"- {e}")
        return 0
    return _emit_error(
        "unknown_action",
        f"Unknown session action: {action!r}",
        json_output=json_output,
    )


def _list_sessions(paths: Any) -> list[dict[str, Any]]:
    runs_dir = _runs_dir(paths)
    if not runs_dir.exists():
        return []
    sessions: list[dict[str, Any]] = []
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        run_json = entry / "run.json"
        if not run_json.exists():
            sessions.append(
                {
                    "session_id": entry.name,
                    "state": "unknown",
                    "created_at": "",
                }
            )
            continue
        try:
            data = json.loads(run_json.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            sessions.append({"session_id": entry.name, "state": "corrupt", "created_at": ""})
            continue
        sessions.append(
            {
                "session_id": entry.name,
                "state": data.get("state", "unknown"),
                "created_at": data.get("created_at", ""),
            }
        )
    return sessions


def _session_info(paths: Any, session_id: str) -> dict[str, Any] | None:
    run_path = _runs_dir(paths) / session_id / "run.json"
    if not run_path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(run_path.read_text(encoding="utf-8"))
        return data
    except Exception:  # noqa: BLE001
        return None


def _session_events(paths: Any, session_id: str) -> list[str]:
    run_path = _runs_dir(paths) / session_id / "events.jsonl"
    if not run_path.exists():
        return []
    out: list[str] = []
    for line in run_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            out.append(json.dumps(obj, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            out.append(line)
    return out


def _runs_dir(paths: Any) -> Path:
    """Return the runs directory from the data_paths dict."""
    if hasattr(paths, "runs_dir"):
        result: Path = paths.runs_dir
        return result
    if isinstance(paths, dict):
        return Path(paths.get("base", ".")) / "runs"
    return Path(paths) / "runs"


def _print_sessions_table(sessions: list[dict[str, Any]]) -> None:
    if not sessions:
        print("(no sessions)")
        return
    headers = ("Session", "State", "Created At")
    widths = [max(len(str(s.get(k.lower().replace(' ', '_'), ""))) for s in sessions + [{k: k}]) for k in headers]
    # Use the actual header text
    rows = [
        {
            "Session": s.get("session_id", ""),
            "State": s.get("state", ""),
            "Created At": s.get("created_at", ""),
        }
        for s in sessions
    ]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for r in rows:
        print("  ".join(str(r.get(h, "")).ljust(w) for h, w in zip(headers, widths)))


def _emit_error(code: str, message: str, *, json_output: bool) -> int:
    if json_output:
        print(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "status": "error",
                    "error_code": code,
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        sys.stderr.write(f"ERROR {code}\n{message}\n")
    return 1


__all__ = ["session_command"]

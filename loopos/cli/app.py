"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loopos.core.loop_engine import LoopEngine
from loopos.core.policy import DeterministicDemoPolicy
from loopos.core.state import LoopState
from loopos.memory.belief_store import BeliefStore
from loopos.memory.event_log import EventLog
from loopos.memory.skill_store import SkillStore
from loopos.memory.state_store import StateStore

typer_mod: Any
ConsoleCls: Any
PanelCls: Any
TableCls: Any

try:  # Optional for local bootstrapping.
    import typer as typer_mod
    from rich.console import Console as ConsoleCls
    from rich.panel import Panel as PanelCls
    from rich.table import Table as TableCls

    _HAS_TUI = True
except Exception:  # pragma: no cover - exercised in dependency-light environments.
    typer_mod = None
    ConsoleCls = None
    PanelCls = None
    TableCls = None
    _HAS_TUI = False

if _HAS_TUI:
    app: Any = typer_mod.Typer(help="LoopOS terminal-native AI-ISA runtime.")
    console: Any = ConsoleCls()
else:
    app = None
    console = None


def _paths(data_dir: str | Path) -> dict[str, Path]:
    base = Path(data_dir)
    return {
        "base": base,
        "events": base / "events.jsonl",
        "runs": base / "runs",
        "skills": base / "skills.jsonl",
        "beliefs": base / "beliefs.jsonl",
    }


def _render_state(state: LoopState, *, verbose: bool = False) -> str:
    payload: dict[str, Any] = {
        "run_id": state.run_id,
        "goal": state.goal,
        "status": state.status,
        "step_index": state.step_index,
        "progress_score": state.progress_score,
    }
    if state.last_observation:
        payload["last_observation"] = {
            "summary": state.last_observation.summary,
            "success": state.last_observation.success,
        }
        if verbose:
            payload["last_observation"]["stdout"] = state.last_observation.stdout
            payload["last_observation"]["stderr"] = state.last_observation.stderr
    if state.errors:
        payload["errors"] = state.errors
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _print_state(state: LoopState, *, verbose: bool = False) -> None:
    if _HAS_TUI:
        body = (
            f"Goal: {state.goal}\n"
            f"Status: {state.status}\n"
            f"Steps: {state.step_index}\n"
            f"Progress: {state.progress_score:.2f}"
        )
        console.print(PanelCls(body, title=f"LoopOS Run {state.run_id}"))
        if state.last_observation:
            obs = state.last_observation
            console.print(f"[bold]Last[/bold]: {obs.summary}")
            if verbose and (obs.stdout or obs.stderr):
                console.print(obs.stdout or obs.stderr)
    else:
        print(_render_state(state, verbose=verbose))


def run_command(
    goal: str,
    *,
    max_steps: int = 5,
    dry_run: bool = False,
    yes: bool = False,
    verbose: bool = False,
    data_dir: str | Path = ".loopos",
) -> int:
    if dry_run:
        state = LoopState(goal=goal)
        instruction = DeterministicDemoPolicy().next_instruction(state)
        print(instruction.model_dump_json(indent=2))
        return 0

    paths = _paths(data_dir)
    engine = LoopEngine.with_local_stores(paths["base"])
    state = engine.run(goal, max_steps=max_steps)
    _print_state(state, verbose=verbose)
    return 0 if state.status == "succeeded" else 1


def status_command(run_id: str, *, data_dir: str | Path = ".loopos", verbose: bool = False) -> int:
    try:
        state = StateStore(_paths(data_dir)["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        return 1
    _print_state(state, verbose=verbose)
    return 0


def resume_command(run_id: str, *, data_dir: str | Path = ".loopos", max_steps: int = 5) -> int:
    try:
        state = StateStore(_paths(data_dir)["runs"]).load(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        return 1
    print("Resume is read-only in the MVP. Current state:")
    _print_state(state)
    return 0


def history_command(run_id: str, *, data_dir: str | Path = ".loopos") -> int:
    events = EventLog(_paths(data_dir)["events"]).list(run_id)
    if not events:
        print(f"No events for run: {run_id}")
        return 0
    if _HAS_TUI:
        table = TableCls(title=f"History {run_id}")
        table.add_column("step")
        table.add_column("type")
        table.add_column("payload")
        for event in events:
            table.add_row(str(event.step_index), event.type, json.dumps(event.payload, ensure_ascii=False)[:120])
        console.print(table)
    else:
        print(json.dumps([event.model_dump(mode="json") for event in events], ensure_ascii=False, indent=2))
    return 0


def skills_command(*, data_dir: str | Path = ".loopos") -> int:
    skills = SkillStore(_paths(data_dir)["skills"]).list()
    if not skills:
        print("No skills stored.")
        return 0
    print(json.dumps([skill.model_dump(mode="json") for skill in skills], ensure_ascii=False, indent=2))
    return 0


def memory_command(*, data_dir: str | Path = ".loopos") -> int:
    items = BeliefStore(_paths(data_dir)["beliefs"]).list(status="active")
    if not items:
        print("No active memory.")
        return 0
    print(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
    return 0


def config_command(*, data_dir: str | Path = ".loopos") -> int:
    print(
        json.dumps(
            {
                "data_dir": str(Path(data_dir)),
                "runtime": "python",
                "llm": "mock-only",
                "web_ui": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if _HAS_TUI:

    @app.command("run")
    def _typer_run(
        goal: str,
        max_steps: int = typer_mod.Option(5, "--max-steps"),
        dry_run: bool = typer_mod.Option(False, "--dry-run"),
        yes: bool = typer_mod.Option(False, "--yes"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(
            run_command(
                goal,
                max_steps=max_steps,
                dry_run=dry_run,
                yes=yes,
                verbose=verbose,
                data_dir=data_dir,
            )
        )

    @app.command("resume")
    def _typer_resume(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        max_steps: int = typer_mod.Option(5, "--max-steps"),
    ) -> None:
        raise typer_mod.Exit(resume_command(run_id, data_dir=data_dir, max_steps=max_steps))

    @app.command("status")
    def _typer_status(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(status_command(run_id, data_dir=data_dir, verbose=verbose))

    @app.command("history")
    def _typer_history(
        run_id: str,
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(history_command(run_id, data_dir=data_dir))

    @app.command("skills")
    def _typer_skills(data_dir: str = typer_mod.Option(".loopos", "--data-dir")) -> None:
        raise typer_mod.Exit(skills_command(data_dir=data_dir))

    @app.command("memory")
    def _typer_memory(data_dir: str = typer_mod.Option(".loopos", "--data-dir")) -> None:
        raise typer_mod.Exit(memory_command(data_dir=data_dir))

    @app.command("config")
    def _typer_config(data_dir: str = typer_mod.Option(".loopos", "--data-dir")) -> None:
        raise typer_mod.Exit(config_command(data_dir=data_dir))


def _argparse_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loopos", description="LoopOS terminal-native AI-ISA runtime.")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("goal")
    run_parser.add_argument("--max-steps", type=int, default=5)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--yes", action="store_true")
    run_parser.add_argument("--verbose", action="store_true")
    run_parser.add_argument("--data-dir", default=".loopos")

    resume_parser = sub.add_parser("resume")
    resume_parser.add_argument("run_id")
    resume_parser.add_argument("--max-steps", type=int, default=5)
    resume_parser.add_argument("--data-dir", default=".loopos")

    status_parser = sub.add_parser("status")
    status_parser.add_argument("run_id")
    status_parser.add_argument("--verbose", action="store_true")
    status_parser.add_argument("--data-dir", default=".loopos")

    history_parser = sub.add_parser("history")
    history_parser.add_argument("run_id")
    history_parser.add_argument("--data-dir", default=".loopos")

    skills_parser = sub.add_parser("skills")
    skills_parser.add_argument("--data-dir", default=".loopos")

    memory_parser = sub.add_parser("memory")
    memory_parser.add_argument("--data-dir", default=".loopos")

    config_parser = sub.add_parser("config")
    config_parser.add_argument("--data-dir", default=".loopos")

    args = parser.parse_args(argv)
    if args.command == "run":
        return run_command(
            args.goal,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            yes=args.yes,
            verbose=args.verbose,
            data_dir=args.data_dir,
        )
    if args.command == "resume":
        return resume_command(args.run_id, data_dir=args.data_dir, max_steps=args.max_steps)
    if args.command == "status":
        return status_command(args.run_id, data_dir=args.data_dir, verbose=args.verbose)
    if args.command == "history":
        return history_command(args.run_id, data_dir=args.data_dir)
    if args.command == "skills":
        return skills_command(data_dir=args.data_dir)
    if args.command == "memory":
        return memory_command(data_dir=args.data_dir)
    if args.command == "config":
        return config_command(data_dir=args.data_dir)
    parser.print_help()
    return 0


def main(argv: list[str] | None = None) -> int:
    if _HAS_TUI and argv is None:
        app()
        return 0
    return _argparse_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

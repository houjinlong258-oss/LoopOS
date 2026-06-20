"""LoopOS CLI/FLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from loopos.ail.codec import instruction_to_ail
from loopos.ail.models import AILInstruction
from loopos.core.loop_engine import LoopEngine
from loopos.core.isa import Instruction
from loopos.core.policy import DeterministicDemoPolicy
from loopos.core.state import LoopState
from loopos.llm.providers import LLMProvider, MockLLMProvider, OpenAICompatibleProvider
from loopos.memory.event_log import EventLog
from loopos.memory.repository import MemoryRepository
from loopos.memory.skill_store import SkillStore
from loopos.memory.state_store import StateStore
from loopos.policy_os.audit import PolicyAuditLog
from loopos.policy_os.engine import PolicyEngine

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
        "policy_audit": base / "policy_audit.jsonl",
    }


def _policy_engine() -> PolicyEngine:
    return PolicyEngine.load_default()


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
    memory: str = "on",
    propose_memory: bool = False,
    llm_provider: str = "mock",
) -> int:
    if dry_run:
        state = LoopState(goal=goal)
        instruction = DeterministicDemoPolicy().next_instruction(state)
        print(instruction.model_dump_json(indent=2))
        return 0

    paths = _paths(data_dir)
    if memory == "off":
        engine = LoopEngine(
            event_log=EventLog(paths["events"]),
            state_store=StateStore(paths["runs"]),
        )
    else:
        engine = LoopEngine.with_local_stores(
            paths["base"],
            propose_memory=propose_memory,
            llm_provider=_llm_provider(llm_provider),
        )
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


def memory_command(
    action: str = "list",
    arg: str | None = None,
    *,
    from_run: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
) -> int:
    repo = MemoryRepository(_paths(data_dir)["base"])
    if action == "list":
        items = repo.list_memory(status="active")
        if not items:
            print("No active memory.")
            return 0
        print(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return 0
    if action == "search":
        if not arg:
            print("Search query is required.", file=sys.stderr)
            return 1
        items = repo.retrieve(query_text=arg, tags=arg.split(), limit=10)
        print(json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False, indent=2))
        return 0
    if action == "propose":
        if not from_run:
            print("--from-run RUN_ID is required.", file=sys.stderr)
            return 1
        proposal = repo.proposal_for_run(from_run)
        repo.propose(proposal)
        print(f"Created proposal {proposal.id}")
        if verbose:
            print(proposal.model_dump_json(indent=2))
        return 0
    if action == "review":
        proposals = repo.list_proposals(status="pending")
        if not proposals:
            print("No pending memory proposals.")
            return 0
        print(json.dumps([proposal.model_dump(mode="json") for proposal in proposals], ensure_ascii=False, indent=2))
        return 0
    if action in {"accept", "reject"}:
        if not arg:
            print(f"Proposal id is required for memory {action}.", file=sys.stderr)
            return 1
        try:
            proposal = repo.decide_proposal(
                arg,
                "accepted" if action == "accept" else "rejected",
                reasons=[f"CLI {action}"],
            )
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{proposal.status}: {proposal.id}")
        return 0
    if action == "reindex":
        counts = repo.reindex()
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    print(f"Unknown memory action: {action}", file=sys.stderr)
    return 1


def profile_command(
    action: str = "show",
    key: str | None = None,
    value: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    repo = MemoryRepository(_paths(data_dir)["base"])
    if action == "show":
        profile = repo.get_profile()
        if not profile:
            print("No user profile.")
        else:
            print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if action == "set":
        if not key or value is None:
            print("profile set requires KEY and VALUE.", file=sys.stderr)
            return 1
        repo.set_profile(key, value)
        print(f"Set profile {key}")
        return 0
    print(f"Unknown profile action: {action}", file=sys.stderr)
    return 1


def policy_command(
    action: str = "list",
    policy_id: str | None = None,
    *,
    scope: str | None = None,
    input_json: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
) -> int:
    engine = _policy_engine()
    if action == "list":
        rows = [
            {
                "id": rule.id,
                "scope": rule.scope,
                "priority": rule.priority,
                "severity": rule.severity,
                "actions": [item.type for item in rule.actions],
            }
            for rule in engine.registry.list_rules(scope=scope)
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        if not policy_id:
            print("policy show requires POLICY_ID.", file=sys.stderr)
            return 1
        try:
            try:
                payload = engine.registry.get_rule(policy_id).model_dump(mode="json")
            except KeyError:
                payload = engine.registry.get_pack(policy_id).model_dump(mode="json")
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "check":
        if not scope:
            print("policy check requires --scope SCOPE.", file=sys.stderr)
            return 1
        try:
            subject = json.loads(input_json or "{}")
        except json.JSONDecodeError as exc:
            print(f"--input must be JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(subject, dict):
            print("--input must be a JSON object.", file=sys.stderr)
            return 1
        decision = engine.evaluate(scope, subject=subject)
        if decision.audit_required:
            PolicyAuditLog(_paths(data_dir)["policy_audit"]).append(scope, subject, decision)
        print(decision.model_dump_json(indent=2))
        return 0 if decision.allowed else 2
    if action == "audit":
        rows = PolicyAuditLog(_paths(data_dir)["policy_audit"]).list()
        if not rows:
            print("No policy audit entries.")
            return 0
        print(json.dumps(rows if verbose else rows[-20:], ensure_ascii=False, indent=2))
        return 0
    print(f"Unknown policy action: {action}", file=sys.stderr)
    return 1


def ail_command(action: str = "validate", file: str | None = None, *, verbose: bool = False) -> int:
    if action not in {"validate", "inspect"}:
        print(f"Unknown ail action: {action}", file=sys.stderr)
        return 1
    if not file:
        print(f"ail {action} requires FILE.", file=sys.stderr)
        return 1
    try:
        payload = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read AIL input: {exc}", file=sys.stderr)
        return 1
    try:
        instruction = AILInstruction.model_validate(payload)
    except ValidationError:
        try:
            instruction = instruction_to_ail(Instruction.model_validate(payload))
        except ValidationError as exc:
            print(f"Invalid AIL instruction: {exc}", file=sys.stderr)
            return 1
    if action == "validate":
        print(f"valid AIL instruction: {instruction.id}")
        if verbose:
            print(instruction.model_dump_json(indent=2))
        return 0
    print(instruction.model_dump_json(indent=2))
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


def _llm_provider(name: str) -> LLMProvider:
    if name == "mock":
        return MockLLMProvider()
    if name == "openai-compatible":
        return OpenAICompatibleProvider()
    raise ValueError(f"unknown LLM provider: {name}")


if _HAS_TUI:

    @app.command("run")
    def _typer_run(
        goal: str,
        max_steps: int = typer_mod.Option(5, "--max-steps"),
        dry_run: bool = typer_mod.Option(False, "--dry-run"),
        yes: bool = typer_mod.Option(False, "--yes"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        memory: str = typer_mod.Option("on", "--memory"),
        propose_memory: bool = typer_mod.Option(False, "--propose-memory"),
        llm_provider: str = typer_mod.Option("mock", "--llm-provider"),
    ) -> None:
        raise typer_mod.Exit(
            run_command(
                goal,
                max_steps=max_steps,
                dry_run=dry_run,
                yes=yes,
                verbose=verbose,
                data_dir=data_dir,
                memory=memory,
                propose_memory=propose_memory,
                llm_provider=llm_provider,
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
    def _typer_memory(
        action: str = typer_mod.Argument("list"),
        arg: str | None = typer_mod.Argument(None),
        from_run: str | None = typer_mod.Option(None, "--from-run"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(
            memory_command(action, arg, from_run=from_run, data_dir=data_dir, verbose=verbose)
        )

    @app.command("profile")
    def _typer_profile(
        action: str = typer_mod.Argument("show"),
        key: str | None = typer_mod.Argument(None),
        value: str | None = typer_mod.Argument(None),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
    ) -> None:
        raise typer_mod.Exit(profile_command(action, key, value, data_dir=data_dir))

    @app.command("config")
    def _typer_config(data_dir: str = typer_mod.Option(".loopos", "--data-dir")) -> None:
        raise typer_mod.Exit(config_command(data_dir=data_dir))

    @app.command("policy")
    def _typer_policy(
        action: str = typer_mod.Argument("list"),
        policy_id: str | None = typer_mod.Argument(None),
        scope: str | None = typer_mod.Option(None, "--scope"),
        input_json: str | None = typer_mod.Option(None, "--input"),
        data_dir: str = typer_mod.Option(".loopos", "--data-dir"),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(
            policy_command(
                action,
                policy_id,
                scope=scope,
                input_json=input_json,
                data_dir=data_dir,
                verbose=verbose,
            )
        )

    @app.command("ail")
    def _typer_ail(
        action: str = typer_mod.Argument("validate"),
        file: str | None = typer_mod.Argument(None),
        verbose: bool = typer_mod.Option(False, "--verbose"),
    ) -> None:
        raise typer_mod.Exit(ail_command(action, file, verbose=verbose))


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
    run_parser.add_argument("--memory", choices=["on", "off"], default="on")
    run_parser.add_argument("--propose-memory", action="store_true")
    run_parser.add_argument("--llm-provider", choices=["mock", "openai-compatible"], default="mock")

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
    memory_parser.add_argument("action", nargs="?", default="list")
    memory_parser.add_argument("arg", nargs="?")
    memory_parser.add_argument("--from-run")
    memory_parser.add_argument("--verbose", action="store_true")
    memory_parser.add_argument("--data-dir", default=".loopos")

    profile_parser = sub.add_parser("profile")
    profile_parser.add_argument("action", nargs="?", default="show")
    profile_parser.add_argument("key", nargs="?")
    profile_parser.add_argument("value", nargs="?")
    profile_parser.add_argument("--data-dir", default=".loopos")

    policy_parser = sub.add_parser("policy")
    policy_parser.add_argument("action", nargs="?", default="list")
    policy_parser.add_argument("policy_id", nargs="?")
    policy_parser.add_argument("--scope")
    policy_parser.add_argument("--input", dest="input_json")
    policy_parser.add_argument("--verbose", action="store_true")
    policy_parser.add_argument("--data-dir", default=".loopos")

    ail_parser = sub.add_parser("ail")
    ail_parser.add_argument("action", nargs="?", default="validate")
    ail_parser.add_argument("file", nargs="?")
    ail_parser.add_argument("--verbose", action="store_true")

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
            memory=args.memory,
            propose_memory=args.propose_memory,
            llm_provider=args.llm_provider,
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
        return memory_command(
            args.action,
            args.arg,
            from_run=args.from_run,
            data_dir=args.data_dir,
            verbose=args.verbose,
        )
    if args.command == "profile":
        return profile_command(args.action, args.key, args.value, data_dir=args.data_dir)
    if args.command == "policy":
        return policy_command(
            args.action,
            args.policy_id,
            scope=args.scope,
            input_json=args.input_json,
            data_dir=args.data_dir,
            verbose=args.verbose,
        )
    if args.command == "ail":
        return ail_command(args.action, args.file, verbose=args.verbose)
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

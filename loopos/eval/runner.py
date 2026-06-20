"""Benchmark task runner with a deterministic mock backend."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from loopos.core.context import ContextCompiler
from loopos.core.isa import make_instruction
from loopos.core.loop_engine import LoopEngine
from loopos.core.state import LoopState
from loopos.eval.metrics import EvalMetrics, compute_metrics
from loopos.kernel import KernelBoot, KernelConfig, KernelLoopEngine, ReplayEngine, RunSpec
from loopos.memory.belief_store import MemoryItem
from loopos.memory.pre_action_gate import PreActionGate
from loopos.memory.repository import MemoryRepository
from loopos.memory.skill_store import Skill
from loopos.policy_os.engine import PolicyEngine


class BenchmarkTask(BaseModel):
    id: str
    name: str
    goal: str
    workspace_setup: dict[str, Any] = Field(default_factory=dict)
    expected_files: list[str] = Field(default_factory=list)
    expected_commands: list[str] = Field(default_factory=list)
    success_checks: list[str] = Field(default_factory=list)
    max_steps: int = 5
    tags: list[str] = Field(default_factory=list)

    @field_validator("max_steps")
    @classmethod
    def positive_steps(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_steps must be positive")
        return value


class EvalTaskResult(BaseModel):
    task_id: str
    success: bool
    status: str
    steps: int
    command_count: int
    blocked_dangerous_actions: int = 0
    repeated_failure_count: int = 0
    skill_reuse_count: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class EvalRunner:
    """Run benchmark tasks through the deterministic MVP engine."""

    def load_tasks(self, task_dir: str | Path) -> list[BenchmarkTask]:
        tasks: list[BenchmarkTask] = []
        for path in sorted(Path(task_dir).glob("*.json")):
            tasks.append(BenchmarkTask.model_validate_json(path.read_text(encoding="utf-8")))
        return tasks

    def run_task(self, task: BenchmarkTask) -> EvalTaskResult:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            self._setup_workspace(workspace, task.workspace_setup)
            repo = self._setup_memory(workspace / ".loopos", task.workspace_setup)

            if "memory-recall" in task.tags:
                query = str(task.workspace_setup.get("query", ""))
                retrieved = repo.retrieve(query_text=query, tags=query.split(), limit=5)
                success = any(query.lower() in item.content.lower() for item in retrieved)
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status="succeeded" if success else "failed",
                    steps=0,
                    command_count=0,
                    details={"retrieved": [item.content for item in retrieved]},
                )

            if "repeated-failure" in task.tags:
                command = str(task.workspace_setup.get("command", "bad"))
                gate = PreActionGate(events=repo.events.list())
                decision = gate.before(make_instruction("EXEC_TERMINAL", "benchmark", {"cmd": command}))
                success = decision.action == "block"
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status="succeeded" if success else "failed",
                    steps=0,
                    command_count=0,
                    blocked_dangerous_actions=1 if success else 0,
                    repeated_failure_count=1 if success else 0,
                    details={"gate_action": decision.action, "reasons": decision.reasons},
                )

            if "skill-reuse" in task.tags:
                command = str(task.workspace_setup.get("command", "pytest"))
                gate = PreActionGate(skills=repo.skills.list())
                decision = gate.before(make_instruction("EXEC_TERMINAL", "benchmark", {"cmd": command}))
                success = decision.action == "substitute_skill"
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status="succeeded" if success else "failed",
                    steps=0,
                    command_count=0,
                    skill_reuse_count=1 if success else 0,
                    details={"gate_action": decision.action, "skill_id": decision.skill_id},
                )

            if "user-profile-context" in task.tags:
                context = ContextCompiler().compile(
                    state=LoopState(goal=task.goal),
                    memories=repo.list_memory(layer="user_model"),
                    skills=[],
                )
                expected = str(task.workspace_setup.get("expected", ""))
                success = any(
                    expected.lower() in item["content"].lower()
                    for item in context.user_model_snippets
                )
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status="succeeded" if success else "failed",
                    steps=0,
                    command_count=0,
                    details={"user_model": context.user_model_snippets},
                )

            if "policy-compliance" in task.tags:
                command = str(task.workspace_setup.get("command", "rm -rf tmp"))
                expected_action = str(task.workspace_setup.get("expected_action", "deny"))
                policy_decision = PolicyEngine.load_default().evaluate(
                    "terminal.execute",
                    subject={"cmd": command},
                )
                success = policy_decision.action == expected_action
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status="succeeded" if success else "failed",
                    steps=0,
                    command_count=0,
                    blocked_dangerous_actions=1 if policy_decision.action == "deny" else 0,
                    details={
                        "policy_action": policy_decision.action,
                        "reasons": policy_decision.reason_codes,
                    },
                )

            if "kernel-replay" in task.tags:
                runtime = KernelBoot().start(
                    KernelConfig(
                        workspace=str(workspace),
                        data_dir=str(workspace / ".loopos"),
                    )
                )
                run = KernelLoopEngine(runtime, memory_repository=repo).run(
                    RunSpec(
                        goal=task.goal,
                        workspace=str(workspace),
                        mode="dry_run",
                        max_steps=task.max_steps,
                    )
                )
                replay = ReplayEngine(runtime.trace_store).replay(
                    run.run_id, run.step, durable=run
                )
                success = run.status == "succeeded" and bool(replay.events)
                return EvalTaskResult(
                    task_id=task.id,
                    success=success,
                    status=run.status,
                    steps=run.step,
                    command_count=0,
                    details={
                        "trace_events": len(runtime.trace_store.list(run.run_id)),
                        "replay_differences": replay.differences,
                    },
                )
            engine = LoopEngine.with_local_stores(workspace / ".loopos", memory_repository=repo)
            state = engine.run(task.goal, max_steps=task.max_steps)
            files_ok = all((workspace / expected).exists() for expected in task.expected_files)
            commands = [item.command for item in state.tool_history if item.command]
            command_count = len(commands)
            commands_ok = all(expected in commands for expected in task.expected_commands)
            success = state.status == "succeeded" and files_ok and commands_ok
            return EvalTaskResult(
                task_id=task.id,
                success=success,
                status=state.status,
                steps=state.step_index,
                command_count=command_count,
                details={
                    "files_ok": files_ok,
                    "commands_ok": commands_ok,
                    "commands": commands,
                    "goal": task.goal,
                },
            )

    def run_all(self, tasks: list[BenchmarkTask]) -> dict[str, Any]:
        results = [self.run_task(task) for task in tasks]
        metrics: EvalMetrics = compute_metrics([result.model_dump() for result in results])
        return {
            "results": [result.model_dump(mode="json") for result in results],
            "metrics": metrics.model_dump(mode="json"),
        }

    def write_report(self, report: dict[str, Any], path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def _setup_workspace(workspace: Path, setup: dict[str, Any]) -> None:
        files = setup.get("files", {})
        if isinstance(files, dict):
            for relative_path, content in files.items():
                target = workspace / str(relative_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(content), encoding="utf-8")

    @staticmethod
    def _setup_memory(base_dir: Path, setup: dict[str, Any]) -> MemoryRepository:
        repo = MemoryRepository(base_dir)
        for item_data in setup.get("memory_items", []):
            if isinstance(item_data, dict):
                repo.write_memory(MemoryItem.model_validate(item_data))
        for skill_data in setup.get("skills", []):
            if isinstance(skill_data, dict):
                skill = Skill.model_validate(skill_data)
                repo.skills.add(skill)
                repo.index.upsert_skill(skill)
        for failed in setup.get("failed_events", []):
            if isinstance(failed, dict):
                event = repo.events.append(
                    "observation",
                    str(failed.get("run_id", "benchmark")),
                    int(failed.get("step_index", 0)),
                    {
                        "command": failed.get("command"),
                        "success": False,
                    },
                )
                repo.index.upsert_event(event)
        profile = setup.get("profile", {})
        if isinstance(profile, dict):
            for key, value in profile.items():
                repo.set_profile(str(key), str(value))
        return repo

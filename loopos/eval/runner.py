"""Benchmark task runner with a deterministic mock backend."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from loopos.core.loop_engine import LoopEngine
from loopos.eval.metrics import EvalMetrics, compute_metrics


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
            engine = LoopEngine.with_local_stores(workspace / ".loopos")
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

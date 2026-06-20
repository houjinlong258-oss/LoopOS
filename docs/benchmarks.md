# Benchmarks

LoopOS benchmarks are JSON task definitions that can run against the deterministic MVP engine.

## Task Schema

- `id`
- `name`
- `goal`
- `workspace_setup`
- `expected_files`
- `expected_commands`
- `success_checks`
- `max_steps`
- `tags`

## Current Metrics

- `success_rate`
- `steps_to_success`
- `command_count`
- `blocked_dangerous_actions`
- `repeated_failure_count`
- `skill_reuse_count`
- `token_estimate`

## Current Tasks

- deterministic loop completion
- prepared workspace file presence
- memory recall
- repeated failure avoidance
- skill reuse
- user preference context injection
- policy compliance
- kernel trace replay

## Running from Python

```python
from loopos.eval.runner import EvalRunner

runner = EvalRunner()
tasks = runner.load_tasks("benchmarks/tasks")
report = runner.run_all(tasks)
runner.write_report(report, "benchmarks/report.json")
```

The MVP runner uses deterministic native and Kernel loops. It does not call a real LLM. The kernel replay task verifies the nine-step hello dry-run and side-effect-free replay.

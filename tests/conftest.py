"""Automatic test-layer markers used by local and CI gates."""

from __future__ import annotations

from pathlib import Path

import pytest

_INTEGRATION_MARKERS = (
    "cli",
    "data_guard",
    "gateway",
    "integration",
    "kernel_loop",
    "local_intel",
    "mcp",
    "memory_repository",
    "outer_loop",
    "release",
    "sqlite",
    "webhook",
    "worktree",
)

_SLOW_FILES = {
    "test_alpha_acceptance.py",
    "test_cli.py",
    "test_sqlite_demo_flow.py",
    "test_webhook_flow_demo.py",
}

_SLOW_TESTS = {
    "tests/test_eval_runner.py::EvalRunnerTests::test_load_and_run_tasks",
    "tests/test_terminal_executor.py::TerminalExecutorTests::test_timeout",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.path)).as_posix().lower()
        nodeid = item.nodeid.replace("\\", "/")
        if "/acceptance_founding/" in f"/{path}":
            item.add_marker(pytest.mark.acceptance)
            item.add_marker(pytest.mark.slow)
        elif any(marker in Path(path).name for marker in _INTEGRATION_MARKERS):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
        if Path(path).name in _SLOW_FILES or nodeid in _SLOW_TESTS:
            item.add_marker(pytest.mark.slow)

"""Optional LangGraph backend adapter."""

from __future__ import annotations

import importlib.util
from typing import Any

from loopos.core.graph_loop import create_loop_graph, run_graph
from loopos.core.state import LoopState


class LangGraphAdapter:
    """Detect and use LangGraph when installed."""

    def is_available(self) -> bool:
        return importlib.util.find_spec("langgraph") is not None

    def create_loop_graph(self) -> Any:
        return create_loop_graph()

    def run_graph(self, goal: str, *, max_steps: int = 5) -> LoopState:
        return run_graph(goal, max_steps=max_steps)

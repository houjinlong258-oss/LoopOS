"""Optional graph-loop facade."""

from __future__ import annotations

from typing import Any

from loopos.core.loop_engine import LoopEngine
from loopos.core.state import LoopState

GRAPH_NODES = [
    "compile_context",
    "plan_instruction",
    "execute_instruction",
    "observe",
    "evaluate",
    "govern_memory",
    "extract_skill",
    "decide_next",
]


def create_loop_graph() -> Any:
    """Create a LangGraph graph when available, otherwise return a descriptor."""

    try:
        from langgraph.graph import StateGraph  # type: ignore
    except Exception:
        return {"backend": "native-fallback", "nodes": GRAPH_NODES}

    graph = StateGraph(dict)
    for node in GRAPH_NODES:
        graph.add_node(node, lambda state: state)
    graph.set_entry_point("compile_context")
    graph.add_edge("compile_context", "plan_instruction")
    graph.add_edge("plan_instruction", "execute_instruction")
    graph.add_edge("execute_instruction", "observe")
    graph.add_edge("observe", "evaluate")
    graph.add_edge("evaluate", "govern_memory")
    graph.add_edge("govern_memory", "extract_skill")
    graph.add_edge("extract_skill", "decide_next")
    return graph


def run_graph(goal: str, *, max_steps: int = 5) -> LoopState:
    """Run the graph backend, falling back to the native engine for the MVP."""

    return LoopEngine().run(goal, max_steps=max_steps)

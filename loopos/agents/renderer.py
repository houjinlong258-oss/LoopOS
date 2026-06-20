"""Final output rendering."""

from __future__ import annotations

from loopos.core.state import LoopState


class FinalRenderer:
    """Render compact human-readable run summaries."""

    def render(self, state: LoopState) -> str:
        last = state.last_observation.summary if state.last_observation else "no observation"
        return (
            f"Run {state.run_id}\n"
            f"Goal: {state.goal}\n"
            f"Status: {state.status}\n"
            f"Steps: {state.step_index}\n"
            f"Progress: {state.progress_score:.2f}\n"
            f"Last: {last}"
        )

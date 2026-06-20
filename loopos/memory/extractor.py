"""Extract memory proposals from run traces."""

from __future__ import annotations

import json

from pydantic import ValidationError

from loopos.llm.providers import LLMProvider, MockLLMProvider
from loopos.memory.belief_store import MemoryItem
from loopos.memory.event_log import Event
from loopos.memory.proposals import MemoryProposal


class MemoryProposalExtractor:
    """Convert traces into governed memory proposals."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or MockLLMProvider()

    def extract(
        self,
        *,
        run_id: str,
        events: list[Event],
        user_profile: dict[str, str] | None = None,
    ) -> tuple[list[MemoryProposal], list[str]]:
        prompt = self._build_prompt(run_id=run_id, events=events, user_profile=user_profile or {})
        response = self.provider.complete(prompt)
        if response.error:
            return [], [response.error]
        try:
            raw = json.loads(response.text)
        except json.JSONDecodeError as exc:
            return [], [f"memory proposal JSON parse failed: {exc}"]
        if not isinstance(raw, list):
            return [], ["memory proposal response must be a JSON array"]

        proposals: list[MemoryProposal] = []
        errors: list[str] = []
        event_ids = [event.id for event in events]
        for index, entry in enumerate(raw):
            try:
                item = MemoryItem.model_validate(entry.get("proposed_item", entry))
                proposal = MemoryProposal(
                    proposed_item=item,
                    source=entry.get("source", "llm"),
                    source_run_id=entry.get("source_run_id", run_id),
                    source_event_ids=entry.get("source_event_ids", event_ids),
                    rationale=entry.get("rationale", "LLM proposed memory from run trace."),
                )
            except (AttributeError, ValidationError, TypeError, ValueError) as exc:
                errors.append(f"proposal {index} rejected: {exc}")
                continue
            proposals.append(proposal)
        return proposals, errors

    @staticmethod
    def _build_prompt(
        *,
        run_id: str,
        events: list[Event],
        user_profile: dict[str, str],
    ) -> str:
        compact_events = [
            {
                "id": event.id,
                "step_index": event.step_index,
                "type": event.type,
                "payload": event.payload,
            }
            for event in events[-20:]
        ]
        return json.dumps(
            {
                "task": "Extract durable LoopOS memory proposals from this run trace.",
                "output_schema": [
                    {
                        "proposed_item": {
                            "type": "belief|preference|fact|failure|note|skill|user_model",
                            "layer": "episodic|semantic|belief|skill|user_model",
                            "scope": "run|project|user|global",
                            "content": "short durable memory",
                            "confidence": 0.0,
                            "source": "llm",
                            "tags": ["tag"],
                        },
                        "source": "llm",
                        "source_run_id": run_id,
                        "source_event_ids": [],
                        "rationale": "why this should be remembered",
                    }
                ],
                "run_id": run_id,
                "user_profile": user_profile,
                "events": compact_events,
            },
            ensure_ascii=False,
        )

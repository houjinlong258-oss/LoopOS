"""Mock provider client used by tests and local dry runs."""

from __future__ import annotations

from loopos.model_kernel.models import ModelAssignment


class MockModelClient:
    def complete(self, assignment: ModelAssignment, prompt: str) -> str:
        return f"[{assignment.role}:{assignment.provider_id}] {prompt}"


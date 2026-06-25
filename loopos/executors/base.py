"""Base executor protocols and patch proposal model."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from loopos.executors.result import PatchResult, TestRunResult


class PatchProposal(BaseModel):
    """A proposed code patch produced by a builder or repairer."""

    model_config = ConfigDict(extra="forbid")

    patch: str
    reason: str = ""
    expected_tests: list[str] = Field(default_factory=list)


class PatchExecutor(Protocol):
    def apply_patch(self, proposal: PatchProposal) -> PatchResult:
        ...


class ProjectTestExecutor(Protocol):
    def run_tests(self) -> TestRunResult:
        ...


__all__ = ["PatchExecutor", "PatchProposal", "ProjectTestExecutor"]

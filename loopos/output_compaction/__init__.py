"""Execution output compaction that preserves failure evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CompactedOutput(BaseModel):
    """A compact output view for token-aware loop handoffs."""

    model_config = ConfigDict(extra="forbid")

    exit_code: int
    summary: str
    preserved_failure_lines: list[str] = Field(default_factory=list)
    original_chars: int = 0
    compacted_chars: int = 0


class OutputCompactor:
    """Keep exit code and failure evidence while trimming long logs."""

    def compact(self, text: str, *, exit_code: int, max_chars: int = 1600) -> CompactedOutput:
        lines = text.splitlines()
        failure_lines = [
            line.strip()
            for line in lines
            if line.strip().startswith(("FAILED ", "ERROR ", "E   "))
            or "AssertionError" in line
        ][:12]
        head = "\n".join(lines[:20])
        tail = "\n".join(lines[-20:]) if len(lines) > 20 else ""
        body = "\n".join(part for part in [head, tail] if part)
        if len(body) > max_chars:
            body = body[:max_chars] + "\n...[compacted]"
        summary = f"exit_code={exit_code}\n{body}".strip()
        if failure_lines:
            summary += "\n\npreserved_failure_lines:\n" + "\n".join(failure_lines)
        return CompactedOutput(
            exit_code=exit_code,
            summary=summary,
            preserved_failure_lines=failure_lines,
            original_chars=len(text),
            compacted_chars=len(summary),
        )


__all__ = ["CompactedOutput", "OutputCompactor"]

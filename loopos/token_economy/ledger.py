"""Token ledger with simple JSONL persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from loopos.token_economy.models import TokenBudgetRecord, TokenWasteFinding


class TokenLedger:
    """Record per-iteration token budgets and savings."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self._records: List[TokenBudgetRecord] = []

    def record(self, record: TokenBudgetRecord) -> TokenBudgetRecord:
        self._records.append(record)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")
        return record

    def record_iteration(
        self,
        *,
        run_id: str,
        iteration_index: int,
        input_tokens: int,
        output_tokens: int,
        context_tokens: int,
        saved_tokens: int = 0,
        budget: int = 0,
    ) -> TokenBudgetRecord:
        return self.record(
            TokenBudgetRecord(
                run_id=run_id,
                iteration_index=iteration_index,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                context_tokens=context_tokens,
                saved_tokens=saved_tokens,
                budget=budget,
            )
        )

    def list(self) -> List[TokenBudgetRecord]:
        if self._records:
            return list(self._records)
        if self.path is None or not self.path.exists():
            return []
        records: List[TokenBudgetRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(TokenBudgetRecord.model_validate(json.loads(line)))
        return records

    def detect_waste(self) -> List[TokenWasteFinding]:
        findings: List[TokenWasteFinding] = []
        for record in self.list():
            if record.over_budget:
                findings.append(
                    TokenWasteFinding(
                        reason=f"iteration {record.iteration_index} exceeded token budget",
                        wasted_tokens_estimate=record.total_tokens - record.budget,
                        recommended_fix="compile a smaller role-specific context packet",
                    )
                )
            if record.saved_tokens == 0 and record.context_tokens > 1200:
                findings.append(
                    TokenWasteFinding(
                        reason="large context packet produced no recorded token savings",
                        wasted_tokens_estimate=record.context_tokens,
                        recommended_fix="route only relevant memory and tool schemas",
                    )
                )
        return findings


def estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


__all__ = ["TokenLedger", "estimate_tokens"]

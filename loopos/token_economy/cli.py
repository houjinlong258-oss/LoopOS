"""CLI helpers for token economy."""

from __future__ import annotations

import json
from pathlib import Path

from loopos.token_economy.ledger import TokenLedger


def token_command(
    action: str = "report",
    *,
    latest: bool = False,
    data_dir: str = ".loopos",
    json_output: bool = True,
) -> int:
    ledger = TokenLedger(Path(data_dir) / "token_ledger.jsonl")
    records = [r.model_dump(mode="json") for r in ledger.list()]
    payload = {
        "status": "ok",
        "action": action,
        "latest": latest,
        "records": records,
        "waste_findings": [f.model_dump(mode="json") for f in ledger.detect_waste()],
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0


__all__ = ["token_command"]

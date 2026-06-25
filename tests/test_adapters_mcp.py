from __future__ import annotations

from loopos.adapters.mcp import McpAdapter


def test_mcp_adapter_translates_lail_signal_as_metadata_only() -> None:
    signal: dict[str, object] = {"kind": "token_budget_recorded", "run_id": "run-1"}

    translated = McpAdapter().translate_lail(signal)

    assert translated == {
        "adapter_id": "mcp",
        "available": False,
        "signal": signal,
    }

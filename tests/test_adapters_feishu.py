from __future__ import annotations

from loopos.adapters.feishu import FeishuAdapter


def test_feishu_adapter_dry_run_does_not_record_message() -> None:
    adapter = FeishuAdapter()

    result = adapter.send_message("hello")

    assert result == {"status": "dry_run", "sent": False, "text": "hello"}
    assert adapter.sent_messages == []


def test_feishu_adapter_records_message_only_when_allowed() -> None:
    adapter = FeishuAdapter()

    result = adapter.send_message("hello", allow_send=True)

    assert result["status"] == "sent"
    assert adapter.sent_messages == ["hello"]

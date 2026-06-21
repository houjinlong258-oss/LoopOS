"""Tests for Fusion + Provider integration and trace recording."""

from __future__ import annotations

from pathlib import Path

from loopos.fusion.models import FusionRequest
from loopos.fusion.router import FusionRouter
from loopos.fusion.trace import FusionRunner, is_sensitive_context
from loopos.kernel.trace import TraceStore
from loopos.model_kernel.registry import ProviderRegistry


def test_router_uses_provider_registry_when_supplied() -> None:
    registry = ProviderRegistry()
    router = FusionRouter(registry=registry)
    request = FusionRequest(
        prompt="compare three layouts",
        task_type="research",
        budget="balanced",
        privacy_mode="cloud_allowed",
    )
    panel = router.plan(request)
    assert "source:provider_registry" in panel.routing_reason
    # Panel should contain real provider ids, not mock ids
    mock_ids = {"local-small", "local-medium", "cloud-fast", "cloud-strong", "cloud-best"}
    assert all(model not in mock_ids for model in panel.models)


def test_router_falls_back_to_mock_without_registry() -> None:
    router = FusionRouter()
    request = FusionRequest(prompt="test", budget="cheap", privacy_mode="hybrid")
    panel = router.plan(request)
    assert "source:mock_registry" in panel.routing_reason


def test_sensitive_context_detected() -> None:
    assert is_sensitive_context("the api_key is abc123")
    assert is_sensitive_context("customer data export")
    assert not is_sensitive_context("compare three CLI layouts")


def test_runner_downgrades_cloud_allowed_when_sensitive(tmp_path: Path) -> None:
    trace = TraceStore(tmp_path / "events.jsonl")
    runner = FusionRunner(trace_store=trace)
    request = FusionRequest(
        prompt="summarize this production database customer data export",
        task_type="research",
        budget="balanced",
        privacy_mode="cloud_allowed",
    )
    runner.run(request, run_id="run-sensitive")
    events = trace.list("run-sensitive")
    kinds = [event.type for event in events]
    assert "fusion_panel" in kinds
    assert "fusion_judge" in kinds
    assert "fusion_result" in kinds
    # The panel event should record that sensitive context was detected
    panel_events = [e for e in events if e.type == "fusion_panel"]
    assert panel_events[0].payload["sensitive_context"] is True


def test_runner_records_trace_events(tmp_path: Path) -> None:
    trace = TraceStore(tmp_path / "events.jsonl")
    runner = FusionRunner(trace_store=trace)
    request = FusionRequest(
        prompt="compare three CLI layouts",
        task_type="research",
        budget="cheap",
        privacy_mode="hybrid",
    )
    result = runner.run(request, run_id="run-1")
    events = trace.list("run-1")
    assert len(events) == 3
    assert result.trace_event_ids == [event.id for event in events]
    assert events[0].type == "fusion_panel"
    assert events[1].type == "fusion_judge"
    assert events[2].type == "fusion_result"


def test_runner_without_trace_store_still_works() -> None:
    runner = FusionRunner()
    request = FusionRequest(prompt="test", budget="cheap", privacy_mode="hybrid")
    result = runner.run(request)
    assert result.fusion_result_id
    assert result.judge_report.request_id == request.request_id

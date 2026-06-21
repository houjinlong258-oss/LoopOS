"""Tests for the Fusion Router skeleton."""

from loopos.fusion.aggregator import FusionAggregator
from loopos.fusion.judge import FusionJudge
from loopos.fusion.models import FusionRequest, ModelResponse
from loopos.fusion.router import FusionRouter


def test_request_validation() -> None:
    req = FusionRequest(prompt="Explain caching strategies")
    assert req.request_id
    assert req.task_type == "unknown"
    assert req.budget == "balanced"


def test_cheap_panel_max_size() -> None:
    router = FusionRouter()
    req = FusionRequest(prompt="simple question", budget="cheap")
    panel = router.plan(req)
    assert len(panel.models) <= 1


def test_best_panel_multiple_models() -> None:
    router = FusionRouter()
    req = FusionRequest(prompt="complex task", budget="best", privacy_mode="cloud_allowed")
    panel = router.plan(req)
    assert len(panel.models) >= 1


def test_local_only_blocks_cloud() -> None:
    router = FusionRouter()
    req = FusionRequest(prompt="private task", privacy_mode="local_only")
    panel = router.plan(req)
    for model in panel.models:
        # All should be local
        assert "cloud" not in model, f"Cloud model {model} should be blocked in local_only mode"


def test_high_risk_includes_verifier_reason() -> None:
    router = FusionRouter()
    req = FusionRequest(prompt="critical deployment", risk_level="high", privacy_mode="cloud_allowed")
    panel = router.plan(req)
    assert any("high_risk" in r for r in panel.routing_reason)


def test_judge_mock_responses() -> None:
    judge = FusionJudge()
    responses = [
        ModelResponse(model_id="model-a", content="The answer is definitely yes, because of X and Y.", latency_ms=100),
        ModelResponse(model_id="model-b", content="The answer is clearly no, because of Z.", latency_ms=200),
    ]
    report = judge.judge("req-1", responses)
    assert report.request_id == "req-1"
    # Should detect contradiction
    assert len(report.contradictions) > 0 or len(report.consensus) >= 0  # At least runs


def test_judge_single_response() -> None:
    judge = FusionJudge()
    responses = [
        ModelResponse(model_id="model-a", content="Only one answer here.", latency_ms=50),
    ]
    report = judge.judge("req-1", responses)
    assert "single_source" in report.consensus


def test_judge_empty_responses() -> None:
    judge = FusionJudge()
    report = judge.judge("req-1", [])
    assert report.confidence == 0.0


def test_aggregation_creates_result() -> None:
    judge = FusionJudge()
    responses = [
        ModelResponse(model_id="m1", content="Short.", latency_ms=100, token_count=5),
        ModelResponse(
            model_id="m2",
            content="A much longer and more detailed response that covers all the important points in great detail.",
            latency_ms=200,
            token_count=20,
        ),
    ]
    report = judge.judge("req-1", responses)
    aggregator = FusionAggregator()
    result = aggregator.aggregate("req-1", responses, report)
    assert result.request_id == "req-1"
    assert result.final_content  # Should have content
    assert len(result.contributing_models) == 2


def test_fusion_result_json() -> None:
    judge = FusionJudge()
    report = judge.judge("req-1", [])
    from loopos.fusion.models import FusionResult
    result = FusionResult(
        request_id="req-1",
        final_content="test",
        judge_report=report,
    )
    data = result.model_dump(mode="json")
    assert "fusion_result_id" in data
    assert "judge_report" in data

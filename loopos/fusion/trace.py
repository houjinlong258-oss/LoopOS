"""Fusion trace integration.

Writes FusionPanel selection, JudgeReport, and FusionResult events to a
TraceStore so fusion runs are replayable and auditable. Also enforces
privacy policy: when a FusionRequest carries sensitive context, cloud
providers are excluded from the panel regardless of the privacy_mode.
"""

from __future__ import annotations

from typing import Any

from loopos.fusion.aggregator import FusionAggregator
from loopos.fusion.judge import FusionJudge
from loopos.fusion.models import FusionPanel, FusionRequest, FusionResult, ModelResponse
from loopos.fusion.router import FusionRouter
from loopos.kernel.trace import TraceStore


class FusionPrivacyError(Exception):
    """Raised when a fusion request would leak sensitive context to cloud models."""


_SENSITIVE_MARKERS = (
    "secret", "password", "api_key", "token", "credential", "private key",
    "ssn", "credit_card", "pii", "customer data", "production database",
)


def is_sensitive_context(prompt: str) -> bool:
    lower = prompt.lower()
    return any(marker in lower for marker in _SENSITIVE_MARKERS)


class FusionRunner:
    """Run a fusion request end-to-end with trace recording and privacy enforcement."""

    def __init__(
        self,
        trace_store: TraceStore | None = None,
        *,
        router: FusionRouter | None = None,
    ) -> None:
        self.trace_store = trace_store
        self.router = router or FusionRouter()
        self.judge = FusionJudge()
        self.aggregator = FusionAggregator()

    def run(
        self,
        request: FusionRequest,
        *,
        run_id: str = "fusion-run",
        mock_responses: list[ModelResponse] | None = None,
    ) -> FusionResult:
        """Plan a panel, generate mock responses, judge, aggregate, and trace."""
        # Privacy enforcement: sensitive context forces local_only behavior
        # even if the request asked for cloud_allowed.
        sensitive = is_sensitive_context(request.prompt)
        effective_request = request
        if sensitive and request.privacy_mode == "cloud_allowed":
            effective_request = request.model_copy(update={"privacy_mode": "local_only"})

        panel = self.router.plan(effective_request)
        trace_ids: list[str] = []
        trace_ids.extend(self._trace_panel(run_id, request, panel, sensitive))

        responses = mock_responses or self._mock_responses(panel, request)
        report = self.judge.judge(request.request_id, responses)
        trace_ids.extend(self._trace_judge(run_id, request, report))

        result = self.aggregator.aggregate(request.request_id, responses, report)
        trace_ids.extend(self._trace_result(run_id, request, result))
        return result.model_copy(update={"trace_event_ids": trace_ids})

    def _mock_responses(self, panel: FusionPanel, request: FusionRequest) -> list[ModelResponse]:
        return [
            ModelResponse(
                model_id=model_id,
                content=f"[mock:{model_id}] response to: {request.prompt[:80]}",
                latency_ms=120,
                token_count=64,
            )
            for model_id in panel.models
        ]

    def _trace_panel(
        self,
        run_id: str,
        request: FusionRequest,
        panel: FusionPanel,
        sensitive: bool,
    ) -> list[str]:
        if self.trace_store is None:
            return []
        payload: dict[str, Any] = {
            "request_id": request.request_id,
            "task_type": request.task_type,
            "privacy_mode": request.privacy_mode,
            "effective_privacy_mode": "local_only" if sensitive else request.privacy_mode,
            "sensitive_context": sensitive,
            "selected_models": panel.models,
            "judge_model": panel.judge_model,
            "routing_reason": panel.routing_reason,
            "estimated_cost_class": panel.estimated_cost_class,
        }
        event = self.trace_store.append("decision", run_id, 0, payload, event_type="fusion_panel")
        return [event.id]

    def _trace_judge(self, run_id: str, request: FusionRequest, report: Any) -> list[str]:
        if self.trace_store is None:
            return []
        event = self.trace_store.append(
            "evaluation",
            run_id,
            0,
            report.model_dump(mode="json"),
            event_type="fusion_judge",
        )
        return [event.id]

    def _trace_result(
        self, run_id: str, request: FusionRequest, result: FusionResult
    ) -> list[str]:
        if self.trace_store is None:
            return []
        event = self.trace_store.append(
            "observation",
            run_id,
            0,
            {
                "fusion_result_id": result.fusion_result_id,
                "request_id": request.request_id,
                "contributing_models": result.contributing_models,
                "cost_estimate": result.cost_estimate,
                "latency_ms": result.latency_ms,
            },
            event_type="fusion_result",
        )
        return [event.id]

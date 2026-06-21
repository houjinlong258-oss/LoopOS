"""Fusion aggregator — combine judge report and responses into a FusionResult."""

from __future__ import annotations

from loopos.fusion.models import FusionResult, JudgeReport, ModelResponse


class FusionAggregator:
    """Aggregate multi-model responses using judge analysis."""

    def aggregate(
        self,
        request_id: str,
        responses: list[ModelResponse],
        judge_report: JudgeReport,
    ) -> FusionResult:
        """Produce a final FusionResult from responses and judge analysis."""
        # Select best content based on judge recommendations
        recommended = judge_report.recommended_source_ids
        best_responses = [r for r in responses if r.model_id in recommended]
        if not best_responses:
            best_responses = responses

        # Simple aggregation: pick longest recommended response
        final_content = ""
        if best_responses:
            final_content = max(best_responses, key=lambda r: len(r.content)).content

        total_latency = sum(r.latency_ms for r in responses) if responses else 0
        total_tokens = sum(r.token_count for r in responses) if responses else 0

        return FusionResult(
            request_id=request_id,
            final_content=final_content,
            judge_report=judge_report,
            contributing_models=[r.model_id for r in responses],
            cost_estimate=total_tokens * 0.001 if total_tokens else None,
            latency_ms=total_latency if total_latency else None,
        )

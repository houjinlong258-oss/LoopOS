"""CLI commands for the Fusion Router.

Subcommands:
    loopos fusion plan "<task>" --panel cheap|balanced|best
    loopos fusion run "<task>" --panel cheap|balanced|best
    loopos fusion inspect <fusion_result_id>
"""

from __future__ import annotations

import json
import sys

from loopos.fusion.aggregator import FusionAggregator
from loopos.fusion.judge import FusionJudge
from loopos.fusion.models import FusionRequest, ModelResponse
from loopos.fusion.router import FusionRouter


def fusion_command(
    action: str = "plan",
    prompt: str | None = None,
    *,
    panel: str = "balanced",
    task_type: str = "unknown",
    risk: str = "medium",
    privacy: str = "hybrid",
    json_output: bool = False,
) -> int:
    """Entry point for ``loopos fusion <action>``."""

    if action == "plan":
        return _plan(
            prompt,
            panel=panel,
            task_type=task_type,
            risk=risk,
            privacy=privacy,
            json_output=json_output,
        )
    if action == "run":
        return _run(
            prompt,
            panel=panel,
            task_type=task_type,
            risk=risk,
            privacy=privacy,
            json_output=json_output,
        )
    if action == "inspect":
        if not prompt:
            print("fusion inspect requires FUSION_RESULT_ID.", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {"fusion_result_id": prompt, "note": "inspect by replaying trace"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Unknown fusion action: {action}", file=sys.stderr)
    return 1


def _plan(
    prompt: str | None,
    *,
    panel: str,
    task_type: str,
    risk: str,
    privacy: str,
    json_output: bool,
) -> int:
    if not prompt:
        print("fusion plan requires PROMPT.", file=sys.stderr)
        return 1
    request = _build_request(
        prompt,
        panel=panel,
        task_type=task_type,
        risk=risk,
        privacy=privacy,
    )
    router = FusionRouter()
    fusion_panel = router.plan(request)
    if json_output:
        print(fusion_panel.model_dump_json(indent=2))
    else:
        print(f"Fusion Plan — {request.task_type}")
        print(f"  panel: {', '.join(fusion_panel.models) or '(empty)'}")
        print(f"  judge: {fusion_panel.judge_model}")
        print(f"  cost:  {fusion_panel.estimated_cost_class}")
        print("  reasons:")
        for reason in fusion_panel.routing_reason:
            print(f"    - {reason}")
    return 0


def _run(
    prompt: str | None,
    *,
    panel: str,
    task_type: str,
    risk: str,
    privacy: str,
    json_output: bool,
) -> int:
    if not prompt:
        print("fusion run requires PROMPT.", file=sys.stderr)
        return 1
    request = _build_request(
        prompt,
        panel=panel,
        task_type=task_type,
        risk=risk,
        privacy=privacy,
    )
    router = FusionRouter()
    fusion_panel = router.plan(request)
    responses = [
        ModelResponse(
            model_id=model_id,
            content=f"[mock:{model_id}] response to: {prompt[:80]}",
            latency_ms=120,
            token_count=64,
        )
        for model_id in fusion_panel.models
    ]
    judge = FusionJudge()
    report = judge.judge(request.request_id, responses)
    aggregator = FusionAggregator()
    result = aggregator.aggregate(request.request_id, responses, report)
    if json_output:
        print(result.model_dump_json(indent=2))
    else:
        print(f"Fusion Result — {result.fusion_result_id}")
        print(f"  contributing models: {', '.join(result.contributing_models)}")
        print(f"  confidence:          {report.confidence:.2f}")
        print(f"  consensus:           {len(report.consensus)}")
        print(f"  contradictions:      {len(report.contradictions)}")
        if result.cost_estimate is not None:
            print(f"  cost estimate:       {result.cost_estimate:.4f}")
        print("  final content (truncated):")
        print(f"    {result.final_content[:160]}")
    return 0


def _build_request(
    prompt: str,
    *,
    panel: str,
    task_type: str,
    risk: str,
    privacy: str,
) -> FusionRequest:
    return FusionRequest(
        prompt=prompt,
        task_type=task_type,  # type: ignore[arg-type]
        budget=panel,  # type: ignore[arg-type]
        risk_level=risk,  # type: ignore[arg-type]
        privacy_mode=privacy,  # type: ignore[arg-type]
    )

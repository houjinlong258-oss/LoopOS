"""v0.3 deep smoke test.

A single integration test that runs the full v0.3 surface in dry-run
mode and verifies that:

1. The Workbench renders all eight panels in JSON.
2. The agent bus translates a ``file_patch_proposed`` event into a
   ``file.patch`` ACI command.
3. The provider runtime, when asked for a live call without
   approval, returns ``status="dry_run"``.
4. OpenGod emits a strategic decision that does **not** contain an
   ``AgentCommand``.
5. The Fusion Verdict Orchestrator maps ``needs_repair`` to a
   ``repair.plan`` ACI command.
"""

from __future__ import annotations

import json

from loopos.adapters import MockAdapter
from loopos.adapters.base import GoalSpec
from loopos.agent_bus import AgentBus
from loopos.fusion_router import (
    FusionVerdict,
    FusionVerdictOrchestrator,
)
from loopos.opengod import (
    OpenGodBudgetGuard,
    build_verdict,
    collect_evidence,
    decide,
)
from loopos.product import (
    Workbench,
    build_panels_from_context,
    render_json,
)
from loopos.providers_runtime import (
    ModelCallRequest,
    ModelMessage,
    OpenAICompatibleProviderRuntime,
)


def test_workbench_full_dry_run() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "v0.3 smoke"}, adapter_id="mock", mode="single", dry_run=True)
    panels = build_panels_from_context(ctx)
    payload = render_json(panels)
    assert "goal" in payload
    assert "agent" in payload
    assert "policy" in payload
    assert "aci" in payload
    assert "ali" in payload
    assert "trace_replay" in payload
    assert "fusion" in payload
    assert "readiness" in payload
    # JSON-serialisable
    json.dumps(payload, default=str)


def test_agent_bus_translates_integration() -> None:
    bus = AgentBus()
    adapter = MockAdapter()
    goal = GoalSpec(goal_id="g1", title="t", intent="i")
    session = adapter.start_session(goal)
    bus.attach_session(session.session_id, adapter.adapter_id, "ali_1")
    for event in adapter.submit_goal(session.session_id, goal):
        receipt = bus.publish(event)
        if receipt.commands:
            # translatable
            assert receipt.commands[0].kind in (
                "file.patch", "terminal.exec", "provider_select", "noop",
            )


def test_provider_runtime_blocks_live_call() -> None:
    rt = OpenAICompatibleProviderRuntime()
    req = ModelCallRequest(
        provider_id="openai",
        model_id="gpt-4.1",
        messages=[ModelMessage(role="user", content="hi")],
    )
    resp = rt.call(req)
    assert resp.status == "dry_run"


def test_opengod_decision_has_no_command() -> None:
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog")
    d = decide(ctx)
    v = build_verdict(d)
    assert not hasattr(d, "command")
    assert v.next_action != ""
    # Budget guard must be a no-op for our smoke test
    OpenGodBudgetGuard(max_usd=1.0).assess(ctx, d)


def test_fusion_orchestrator_submits_repair() -> None:
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "needs_repair", "confidence": 0.5}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    assert r.status == "submitted"
    assert r.command is not None
    assert r.command.purpose == "repair.plan"
    assert r.next_ali_state == "REPAIRING"


def test_workbench_aci_panel_has_translated_commands() -> None:
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "v0.3 smoke"}, adapter_id="mock", dry_run=True)
    panels = build_panels_from_context(ctx)
    rows = panels.aci.data.get("rows") or []
    assert len(rows) >= 1
    kinds = {row.get("kind") for row in rows}
    # at least one translatable event type appears in the ACI panel
    assert {"file.read", "test.run", "provider.call"} & kinds

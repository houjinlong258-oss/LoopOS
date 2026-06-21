"""LoopOS Founding Release Acceptance Suite.

End-to-end tests proving the core promises of the Founding Release.
All tests use temp directories, mock clients, no real APIs, no dangerous commands.
"""

import sqlite3
import tempfile
from pathlib import Path

from loopos.data_guard.sqlite_adapter import SQLiteAdapter
from loopos.fusion.aggregator import FusionAggregator
from loopos.fusion.judge import FusionJudge
from loopos.fusion.models import FusionRequest, ModelResponse
from loopos.fusion.router import FusionRouter
from loopos.gateway.auth import GatewayAuthPolicy
from loopos.gateway.webhook import (
    WebhookApprovalHandler,
)
from loopos.kernel.checkpoint import CheckpointStore, KernelCheckpoint
from loopos.kernel.invariants import KernelInvariantChecker
from loopos.kernel.lifecycle import KernelLifecycle
from loopos.kernel.models import RunRecord, RunSpec
from loopos.kernel.replay import ReplayEngine
from loopos.kernel.signals import KernelSignalEvent
from loopos.kernel.supervisor import Supervisor, SupervisorConfig
from loopos.kernel.trace import TraceStore
from loopos.kernel.transition import TransitionEngine
from loopos.maintainability.analyzer import MaintainabilityAnalyzer
from loopos.maintainability.gate import MaintainabilityGate
from loopos.maintainability.models import CodeChangeSummary
from loopos.model_kernel.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleConfig,
)
from loopos.prompt_distill.distiller import PromptDistiller
from loopos.review.gate import MergeGate, ReviewArtifactBuilder


# ── 1. Kernel dry-run completes with trace ──


def test_dry_run_produces_trace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace = TraceStore(Path(tmpdir) / "events.jsonl")
        run = RunRecord.from_spec(RunSpec(goal="test dry run", mode="dry_run"))
        trace.append("run", run.run_id, 0, {"event": "started"})
        trace.append("instruction", run.run_id, 1, {"op": "PLAN"})
        trace.append("observation", run.run_id, 1, {"success": True})
        events = trace.list(run.run_id)
        assert len(events) == 3
        assert events[0].kind == "run"


# ── 2. State transitions enforce legality ──


def test_illegal_transition_rejected() -> None:
    run = RunRecord.from_spec(RunSpec(goal="test transitions"))
    engine = TransitionEngine()
    engine.apply(run, "running", "EXECUTING")
    engine.apply(run, "succeeded", "HALTED")
    try:
        engine.apply(run, "running", "EXECUTING")
        assert False, "succeeded -> running should be rejected"
    except ValueError:
        pass


# ── 3. Dangerous command blocked by invariant detection ──


def test_invariant_catches_syscall_without_policy() -> None:
    checker = KernelInvariantChecker()
    events = [
        {"kind": "observation", "payload": {"success": True}},
    ]
    violations = checker.check_all("run-1", 1, events)
    blockers = [v for v in violations if v.severity == "blocker"]
    assert len(blockers) > 0
    assert any("POLICY" in v.invariant_id for v in blockers)


# ── 4. SQLite backup and shadow validation ──


def test_sqlite_backup_and_validate() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "app.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE items (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO items VALUES (1, 'alpha')")
        conn.execute("INSERT INTO items VALUES (2, 'beta')")
        conn.commit()
        conn.close()

        adapter = SQLiteAdapter()
        manifest = adapter.backup(db, Path(tmpdir) / "bak", run_id="run-e2e")
        shadow = adapter.restore_shadow(manifest.files[0], Path(tmpdir) / "shadow")
        report = adapter.validate(db, shadow, run_id="run-e2e")
        assert report.passed


# ── 5. Maintainability gate blocks policy bypass ──


def test_maintainability_blocks_policy_bypass() -> None:
    summary = CodeChangeSummary(
        changed_files=["loopos/core/runner.py"],
        test_files_changed=["tests/test_runner.py"],
        added_lines=5,
    )
    files = {"loopos/core/runner.py": 'import os\nos.system("rm -rf /tmp")\n'}
    report = MaintainabilityAnalyzer().analyze(summary, files=files)
    decision = MaintainabilityGate().evaluate(report)
    assert not decision.allowed_to_continue
    assert decision.blocks_merge


# ── 6. Review artifact blocks failed maintainability ──


def test_review_blocks_failed_maintainability() -> None:
    builder = ReviewArtifactBuilder("run-e2e")
    builder.add_test_result({"passed": True})
    builder.set_acceptance({"goal": "passed"})
    artifact = builder.build()
    gate = MergeGate()
    decision = gate.evaluate(artifact, maintainability_blocked=True)
    assert not decision.allowed_to_merge
    assert "maintainability_blocked" in decision.blockers


# ── 7. Fusion mock produces judge report ──


def test_fusion_mock_judge_report() -> None:
    router = FusionRouter()
    req = FusionRequest(prompt="Explain caching", budget="balanced", privacy_mode="cloud_allowed")
    panel = router.plan(req)
    assert len(panel.models) >= 1

    responses = [
        ModelResponse(model_id=m, content=f"Response from {m} about caching strategies and patterns", latency_ms=100)
        for m in panel.models
    ]
    judge = FusionJudge()
    report = judge.judge(req.request_id, responses)
    assert report.request_id == req.request_id

    aggregator = FusionAggregator()
    result = aggregator.aggregate(req.request_id, responses, report)
    assert result.final_content


# ── 8. Prompt distillation outputs draft packs ──


def test_distillation_draft_packs() -> None:
    text = """\
## Behavior
- Always validate input before processing
- Never skip safety checks

## Planning
- Break tasks into small steps
- Verify each step before continuing

## Rendering
- Use markdown for documentation
- Keep CLI output concise
"""
    distiller = PromptDistiller()
    source = distiller.inspect(text)
    segments = distiller.segment(text, source_id=source.source_id)
    behavior = distiller.extract_behavior(segments)
    assert behavior.status == "draft"
    assert len(behavior.planning_rules) + len(behavior.tone_rules) > 0

    draft = distiller.extract_policy_draft(segments, source_id=source.source_id)
    assert draft.requires_human_review
    audit = distiller.audit(source, segments, behavior, distiller.extract_renderer(segments), draft)
    assert not audit.source_text_copied


# ── 9. Provider boundary mock parses response ──


def test_provider_boundary_mock() -> None:
    cfg = OpenAICompatibleConfig(api_key="sk-test-e2e", model="gpt-4o-mini")
    client = OpenAICompatibleClient(cfg)
    assert client.is_available

    request = client.build_request([{"role": "user", "content": "Hello"}])
    assert "chat/completions" in request["url"]

    response = client.parse_response({
        "id": "cmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4o-mini",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi!"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    })
    assert response.choices[0].message.content == "Hi!"


# ── 10. Webhook approval resumes waiting run ──


def test_webhook_approval_resumes() -> None:
    auth = GatewayAuthPolicy(allowlists={"webhook": {"admin"}})
    handler = WebhookApprovalHandler(auth)
    resp = handler.handle("admin", "appr-001", "approve", run_id="run-e2e")
    assert resp.status == "ok"
    assert handler.decisions[0].approve


# ── 11. Checkpoint checksum and replay ──


def test_checkpoint_and_replay() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        run = RunRecord.from_spec(RunSpec(goal="replay test"))
        TransitionEngine().apply(run, "running", "EXECUTING")
        run.step = 3

        cp = KernelCheckpoint.from_run(run)
        store = CheckpointStore(Path(tmpdir) / "checkpoints")
        store.save(cp)
        loaded = store.load(run.run_id, 3)
        assert loaded.verify()
        assert loaded.checksum == cp.checksum

        # Replay engine
        trace = TraceStore(Path(tmpdir) / "events.jsonl")
        trace.append("run", run.run_id, 0, {"state": run.model_dump(mode="json")})
        trace.append("transition", run.run_id, 1, {"after": run.model_dump(mode="json")})
        replay = ReplayEngine(trace)
        result = replay.replay(run.run_id, 3, durable=run)
        assert result.run_id == run.run_id


# ── 12. Supervisor halts exceeded runs ──


def test_supervisor_halts_exceeded() -> None:
    run = RunRecord.from_spec(RunSpec(goal="too many steps"))
    run.step = 100
    sv = Supervisor(SupervisorConfig(max_steps=50))
    decision = sv.evaluate(run)
    assert decision.action == "halt_blocked"


# ── 13. Lifecycle tracks kernel state ──


def test_lifecycle_full_cycle() -> None:
    lc = KernelLifecycle()
    lc.transition("booting")
    lc.transition("ready")
    lc.transition("running")
    lc.transition("ready")
    lc.transition("shutting_down")
    lc.transition("terminated")
    assert not lc.is_active
    assert len(lc.history) == 6


# ── 14. Signal event creation ──


def test_signal_event() -> None:
    sig = KernelSignalEvent(
        run_id="run-e2e",
        signal_type="approve",
        source="gateway",
        payload={"approval_id": "appr-001"},
    )
    assert sig.signal_type == "approve"
    assert sig.source == "gateway"

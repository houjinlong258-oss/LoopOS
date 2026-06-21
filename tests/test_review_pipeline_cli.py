from __future__ import annotations

import json
from pathlib import Path

from loopos.cli.commands.review import review_command
from loopos.kernel import RunManager, RunRecord, RunSpec, TraceStore


def test_review_artifact_aggregates_trace_diff_and_maintainability(
    tmp_path: Path, capsys: object
) -> None:
    run = RunRecord.from_spec(RunSpec(goal="review code"))
    run.status = "succeeded"
    run.phase = "HALTED"
    RunManager(tmp_path / "runs").save(run)
    trace = TraceStore(tmp_path / "events.jsonl")
    trace.append("policy", run.run_id, 1, {"allowed": True, "rule": "code.review"})
    trace.append(
        "observation",
        run.run_id,
        2,
        {"success": True, "summary": "pytest passed"},
    )
    diff = tmp_path / "change.diff"
    diff.write_text(
        """--- a/loopos/core/unsafe.py
+++ b/loopos/core/unsafe.py
@@ -0,0 +1,2 @@
+import os
+os.system("echo bypass")
""",
        encoding="utf-8",
    )

    result = review_command(
        "artifact", data_dir=tmp_path, run_id=run.run_id, diff_file=diff
    )
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    artifact = json.loads(captured.out)

    assert result == 0
    assert artifact["diff_summary"]["changed_files"] == ["loopos/core/unsafe.py"]
    assert artifact["tests_run"][0]["passed"] is True
    assert artifact["policy_checks"][0]["rule"] == "code.review"
    assert artifact["maintainability_gate"]["blocks_merge"] is True
    assert artifact["decision"] == "request_changes"

    assert review_command("gate", data_dir=tmp_path, run_id=run.run_id) == 0
    gate_output = capsys.readouterr()  # type: ignore[attr-defined]
    gate = json.loads(gate_output.out)
    assert gate["allowed_to_merge"] is False
    assert "maintainability_blocked" in gate["blockers"]

"""Tiny audit-only CLI smoke test for v0.2 RC.

Verifies the CLI surfaces called out in the master prompt:
  - fusion-router plan / explain / run --dry-run / status / list / route
  - mad-dog plan / status / list / route
  - route planning-only fallback

This is an audit-only helper, NOT a runtime feature.
"""
import json
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

from loopos.cli.app import app


def run(argv: list[str]) -> dict:
    """Run a CLI invocation and parse the JSON output."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    saved_argv = sys.argv
    sys.argv = ["loopos"] + argv
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            app()
    except SystemExit:
        pass
    finally:
        sys.argv = saved_argv
    out = buf_out.getvalue().strip()
    err = buf_err.getvalue().strip()
    if not out:
        return {"_stderr": err, "_empty": True}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"_raw": out, "_stderr": err}


def main() -> int:
    failures: list[str] = []

    # ----- fusion-router surfaces -----
    trivial = json.dumps({
        "task_id": "audit-rc-trivial",
        "task_type": "bugfix",
        "description": "trivial typo fix",
        "complexity_score": 1,
        "failure_count": 0,
        "user_dissatisfaction_count": 0,
        "risk_score": 1,
        "affected_file_count": 1,
        "no_progress_count": 0,
        "release_blocker": False,
        "security_sensitive": False,
        "model_mismatch": False,
    })

    # plan -> returns FusionPlan JSON (no status wrapper)
    plan_resp = run(["fusion-router", "--action", "plan", "--task", trivial, "--json"])
    if "fusion_id" not in plan_resp or plan_resp.get("mode") != "single":
        failures.append(f"fusion-router plan: missing fusion_id or mode != single: {list(plan_resp.keys())[:5]}")
    else:
        fusion_id = plan_resp["fusion_id"]
        print(f"[ok] fusion-router plan -> mode=single fusion_id={fusion_id}")

    # explain -> returns explanation JSON
    explain_resp = run(["fusion-router", "--action", "explain", "--task", trivial, "--json"])
    if "fusion_score" not in explain_resp or "selected_mode" not in explain_resp:
        failures.append(f"fusion-router explain: missing fields: {list(explain_resp.keys())[:5]}")
    else:
        print(f"[ok] fusion-router explain -> score={explain_resp['fusion_score']} mode={explain_resp['selected_mode']}")

    # run --dry-run -> returns run record
    run_resp = run(["fusion-router", "--action", "run", "--task", trivial, "--dry-run", "--json"])
    if "fusion_id" not in run_resp:
        failures.append(f"fusion-router run --dry-run: missing fusion_id: {list(run_resp.keys())[:5]}")
    else:
        print(f"[ok] fusion-router run --dry-run -> fusion_id={run_resp['fusion_id']}")

    # status
    status_resp = run(["fusion-router", "--action", "status", "--fusion-id", fusion_id, "--json"])
    if status_resp.get("status") not in ("loaded", "ok"):
        failures.append(f"fusion-router status: unexpected status: {status_resp}")
    else:
        print(f"[ok] fusion-router status -> status={status_resp.get('status')}")

    # list
    list_resp = run(["fusion-router", "--action", "list", "--json"])
    if "ids" not in list_resp and "plans" not in list_resp:
        failures.append(f"fusion-router list: missing ids/plans: {list(list_resp.keys())[:5]}")
    else:
        ids = list_resp.get("ids") or list_resp.get("plans") or []
        print(f"[ok] fusion-router list -> count={len(ids)}")

    # route (planning-only fallback)
    # The audit harness does not wire a kernel_engine into the
    # FusionRunner, so route correctly returns the structured
    # planning-only fallback. This is the desired audit behavior
    # in v0.2 (Fusion Router is planning-only).
    route_resp = run(["fusion-router", "--action", "route", "--fusion-id", fusion_id, "--json"])
    if (
        route_resp.get("status") not in ("ok", "loaded", "planning_only")
        and "run_mode" not in route_resp
    ):
        failures.append(f"fusion-router route: {route_resp}")
    else:
        print(
            f"[ok] fusion-router route -> status={route_resp.get('status')} "
            f"fallback={route_resp.get('fallback_reason') or '(none)'}"
        )

    # ----- mad-dog surfaces -----
    md_task = json.dumps({
        "task_id": "audit-rc-mad-dog",
        "task_type": "release",
        "description": "nasty release blocker",
        "complexity_score": 7,
        "failure_count": 5,
        "user_dissatisfaction_count": 4,
        "risk_score": 5,
        "affected_file_count": 12,
        "no_progress_count": 3,
        "release_blocker": True,
        "security_sensitive": False,
        "model_mismatch": False,
    })

    # mad-dog plan (explicit_user_request trigger)
    md_plan = run(["mad-dog", "--action", "plan", "--task", md_task, "--json"])
    if md_plan.get("mode") != "mad_dog" or "fusion_id" not in md_plan:
        failures.append(f"mad-dog plan: missing fields: {list(md_plan.keys())[:5]}")
    else:
        md_fusion_id = md_plan["fusion_id"]
        print(f"[ok] mad-dog plan -> mode=mad_dog fusion_id={md_fusion_id}")

        # mad-dog status
        md_status = run(["mad-dog", "--action", "status", "--fusion-id", md_fusion_id, "--json"])
        if md_status.get("status") not in ("loaded", "ok"):
            failures.append(f"mad-dog status: {md_status}")
        else:
            print(f"[ok] mad-dog status -> status={md_status.get('status')}")

        # mad-dog list
        md_list = run(["mad-dog", "--action", "list", "--json"])
        if "ids" not in md_list and "plans" not in md_list:
            failures.append(f"mad-dog list: missing ids/plans: {list(md_list.keys())[:5]}")
        else:
            md_ids = md_list.get("ids") or md_list.get("plans") or []
            print(f"[ok] mad-dog list -> count={len(md_ids)}")

        # mad-dog route (planning-only fallback, see fusion-router route above)
        md_route = run(["mad-dog", "--action", "route", "--fusion-id", md_fusion_id, "--json"])
        if (
            md_route.get("status") not in ("ok", "loaded", "planning_only")
            and "run_mode" not in md_route
        ):
            failures.append(f"mad-dog route: {md_route}")
        else:
            print(
                f"[ok] mad-dog route -> status={md_route.get('status')} "
                f"fallback={md_route.get('fallback_reason') or '(none)'}"
            )

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nALL CLI SURFACES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
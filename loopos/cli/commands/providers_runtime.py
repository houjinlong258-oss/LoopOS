"""v0.3 CLI: ``loopos providers runtime`` and ``loopos model call``.

These commands expose the governed provider runtime. Live calls
require explicit approval (``--allow-live-provider``), a budget
(``--budget-usd``), and confirmation (``--confirm``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.providers_runtime import (
    BudgetLedger,
    ModelCallRequest,
    ModelMessage,
    ProviderRuntimeRegistry,
    get_default_ledger,
    redact_secrets,
)


def providers_runtime_command(
    action: str = "list",
    value: str | None = None,
    *,
    model: str = "mock-model",
    dry_run: bool = True,
    json_output: bool = False,
) -> int:
    registry = ProviderRuntimeRegistry()
    if action == "list":
        rows = [row.model_dump(mode="json") for row in registry.list_runtimes()]
        if json_output:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            _print_providers_table(rows)
        return 0
    if action == "test":
        if not value:
            return _emit_error(
                code="provider_id_required",
                message="`loopos providers runtime test PROVIDER` requires a provider id",
                json_output=json_output,
            )
        runtime = registry.get(value)
        if runtime is None:
            return _emit_error(
                code="provider_not_found",
                message=f"Provider {value!r} is not installed or not configured.",
                json_output=json_output,
            )
        response = runtime.call(
            _build_request(
                provider_id=value,
                model_id=model,
                prompt="smoke",
                allow_live=False,
            )
        )
        payload = response.model_dump(mode="json", exclude_none=True)
        if json_output:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"status: {payload.get('status')}")
            print(f"reason_codes: {payload.get('reason_codes')}")
            print(f"content: {(payload.get('content') or '')[:120]}")
        return 0
    return _emit_error(
        code="unknown_action",
        message=f"Unknown providers runtime action: {action!r}",
        json_output=json_output,
    )


def model_call_command(
    prompt_path: str,
    *,
    provider: str = "mock",
    model: str = "mock-model",
    dry_run: bool = True,
    allow_live_provider: bool = False,
    budget_usd: float = 0.0,
    confirm: bool = False,
    json_output: bool = False,
) -> int:
    """``loopos model call PROMPT_FILE --provider X --model Y ...``"""
    # Required-flag validation per the v0.3 spec.
    # The three flags are required **only when actually going live**
    # (``not dry_run``). A pure dry-run with ``--budget-usd`` is
    # allowed: the budget just bounds what a *future* live call
    # would cost. Likewise, ``--allow-live-provider`` is allowed in
    # a dry-run; the runtime will return ``status="dry_run"`` and
    # never touch the network.
    going_live = not dry_run
    if going_live:
        missing: list[str] = []
        if not allow_live_provider:
            missing.append("--allow-live-provider")
        if budget_usd <= 0:
            missing.append("--budget-usd")
        if not confirm:
            missing.append("--confirm")
        if missing:
            return _emit_blocked(
                missing=missing,
                json_output=json_output,
            )
    # Load prompt from file.
    path = Path(prompt_path)
    if not path.exists():
        return _emit_error(
            code="prompt_file_not_found",
            message=f"Prompt file not found: {prompt_path}",
            json_output=json_output,
        )
    prompt = path.read_text(encoding="utf-8", errors="replace")
    request = _build_request(
        provider_id=provider,
        model_id=model,
        prompt=prompt,
        allow_live=allow_live_provider and not dry_run,
        budget_usd=budget_usd,
    )
    # Apply budget guard via the shared process-level BudgetLedger
    # (only when going live and a budget was set). The ledger is the
    # single accounting path; the Workbench goes through the same
    # ledger so a request that flows through both paths cannot
    # double-spend.
    ledger: BudgetLedger = get_default_ledger()
    ledger_budget_key: tuple[str, str, str | None] | None = None
    if going_live and budget_usd > 0:
        ledger_budget_key = ledger.make_key(provider, model, None)
        # ``get_or_create`` is idempotent: if the Workbench already
        # created the entry on the same key, we land on the same
        # ProviderBudget instance and see its cumulative spend.
        ledger.get_or_create(
            provider_id=provider,
            model_id=model,
            session_id=None,
            max_usd=budget_usd,
        )
        decision = ledger.check(
            provider,
            model,
            None,
            0.01,
            approved=confirm,
        )
        if not decision.allowed:
            payload = {
                "status": "blocked",
                "reason_codes": decision.reason_codes,
                "used_usd": decision.used_usd,
                "requested_estimate_usd": decision.requested_estimate_usd,
                "max_usd": decision.max_usd,
            }
            if json_output:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"ERROR budget_blocked: {payload}")
            return 6
    registry = ProviderRuntimeRegistry()
    runtime = registry.get(provider)
    if runtime is None:
        return _emit_error(
            code="provider_not_found",
            message=f"Provider {provider!r} is not installed or not configured.",
            json_output=json_output,
        )
    response = runtime.call(request)
    # Commit the (estimated) cost when we actually went live and a
    # budget was configured. Dry-run and non-completed responses do
    # NOT commit. A failed call does not commit; the ledger records
    # only the spend that actually happened.
    if (
        ledger_budget_key is not None
        and response.status == "completed"
        and not dry_run
    ):
        ledger.commit(provider, model, None, 0.01)
    payload = response.model_dump(mode="json", exclude_none=True)
    # Defence in depth: redact any leaked secrets in the rendered output.
    payload = _recursive_redact(payload)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"status: {payload.get('status')}")
        print(f"reason_codes: {payload.get('reason_codes')}")
        print(f"content: {redact_secrets((payload.get('content') or ''))[:400]}")
    return 0


def _build_request(
    *,
    provider_id: str,
    model_id: str,
    prompt: str,
    allow_live: bool,
    budget_usd: float = 0.0,
) -> ModelCallRequest:
    return ModelCallRequest(
        provider_id=provider_id,
        model_id=model_id,
        messages=[ModelMessage(role="user", content=prompt)],
        live_provider_calls_allowed=bool(allow_live),
        budget_usd=budget_usd if budget_usd > 0 else None,
    )


def _print_providers_table(rows: list[dict[str, Any]]) -> None:
    try:
        from loopos.cli_ui import get_console, render_providers_view
        con = get_console()
        if con is not None:
            con.print(render_providers_view(rows))
            return
    except Exception:
        pass
    headers = ("Provider", "Status", "Env Key", "Live Calls", "Notes")
    widths = [max(len(str(r.get(k, ""))) for r in rows + [{k: k}]) for k in headers]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for r in rows:
        print("  ".join(str(r.get(k, "")).ljust(w) for k, w in zip(headers, widths)))


def _emit_error(*, code: str, message: str, json_output: bool) -> int:
    if json_output:
        print(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "status": "error",
                    "error_code": code,
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        sys.stderr.write(f"ERROR {code}\n{message}\n")
    return 1


def _emit_blocked(*, missing: list[str], json_output: bool) -> int:
    payload = {
        "schema_version": "0.3",
        "status": "blocked",
        "reason_codes": ["live_provider_requires_explicit_approval"],
        "required_flags": missing,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        sys.stderr.write(
            f"BLOCKED live_provider_requires_explicit_approval\n"
            f"Required flags: {' '.join(missing)}\n"
        )
    return 4


def _recursive_redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {k: _recursive_redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_redact(item) for item in value]
    return value


__all__ = [
    "providers_runtime_command",
    "model_call_command",
]

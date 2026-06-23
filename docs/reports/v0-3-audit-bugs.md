# v0.3 Audit — Bugs Found

## Confirmed bugs

### Critical (data leak / broken behavior)

1. **OpenAI runtime leaks API key via `last_prepared`** —
   `loopos/providers_runtime/openai.py` line 137 masks the key in
   `_build_request` but line 216 re-attaches the real key, then
   `self.last_prepared = prepared` stores it. Any caller that does
   `last_prepared.model_dump_json()` leaks the key.

2. **`AgentBus.dispatch()` is broken** —
   `loopos/agent_bus/bus.py` line 103 calls
   `self._runner.run(command, dry_run=self._dry_run)`, but the
   v0.2 `CommandRunner.run` signature is `(command, *, explain=False)`.
   The kwarg `dry_run` does not exist; the call always raises
   `TypeError`. The bus's `dispatch()` is therefore unusable.
   Tests do not catch this because no test calls `dispatch()`.

3. **Budget guard is a no-op in `Workbench.call_model` and
   `model_call_command`** — every call constructs a fresh
   `ProviderBudget(max_usd=...)` with `used_usd=0.0`, so the budget
   is never tracked across calls. A user can call 100 times with a
   $0.10 budget and every call passes. The `commit()` method exists
   but is never called.

4. **`model_call_command` blocks legitimate dry-runs** — the
   `needs_live_flags = allow_live_provider or budget_usd > 0 or not
   dry_run` logic requires all three flags whenever any one of them
   is set. A user invoking `--dry-run --budget-usd 0.50` without
   `--allow-live-provider` is wrongly blocked, even though the
   dry-run does not actually spend money.

5. **Fusion Verdict Orchestrator has reversed `explain` polarity** —
   `loopos/fusion_router/orchestrator.py` line 132 calls
   `self._runner.run(command, explain=not dry_run)`. The user
   intent is "if dry_run, don't run; else run". But
   `CommandRunner.run(explain=True)` means "don't run, just
   explain". So the orchestrator is permanently stuck in
   dry-run regardless of the caller's intent.

### High (silent data / wrong model fields)

6. **Workbench fusion view shows fake data** —
   `loopos/product/workbench.py::_fusion_summary` uses
   `getattr(plan, "score", 0)`, `getattr(plan, "roles", [])`,
   `getattr(plan, "providers", [])`. None of these fields exist on
   `FusionPlan`; the real fields are `fusion_score`, `assignments`.
   Combined with the broad `except Exception` that silently
   swallows the invalid `task_type="code"` and the invalid
   `FusionTriggerSource.SYSTEM` (and the invalid severity
   `"normal"`), the workbench never actually exercises the
   `FusionRouter.plan()` and always returns hard-coded defaults.
   The result: the **Fusion** panel in the Workbench is theatre.

7. **`FusionTriggerSource.SYSTEM` does not exist** —
   `loopos/product/workbench.py` line 322 passes
   `source=FusionTriggerSource.SYSTEM`. The actual literal is
   `Literal['user', 'ali', 'kernel', 'convergence', 'review',
   'test', 'release']`. The workbench hides the resulting
   `ValidationError` with a broad `except Exception`.

8. **`severity="normal"` is not a valid `FusionTriggerSeverity`** —
   `loopos/product/workbench.py` line 326 uses
   `severity="normal"`. The actual literal is
   `Literal['low', 'medium', 'high', 'critical']`. Hidden by
   the same broad `except Exception`.

9. **`task_type="code"` is not a valid `FusionTaskProfile.task_type`** —
   `loopos/product/workbench.py` line 309. Real values:
   `'bugfix', 'refactor', 'feature', 'audit', 'release',
   'security', 'debugging', 'architecture', 'test_repair'`.
   Hidden by the same broad `except Exception`.

### Medium (missing or wrong behavior)

10. **`OpenGodBudgetGuard` fails to block when reserve >= max** —
    `loopos/opengod/budget.py` line 67-70: when
    `ceiling = max_usd - reserve_usd <= 0`, the chained comparison
    `projected > ceiling > 0` short-circuits and the guard
    silently allows the decision. Should block when there is
    no headroom.

11. **`OpenGod.decide()` cannot produce `ask_user` or
    `needs_replan`** — the decision rules table does not include
    a path to these kinds, even though the spec lists them as
    valid output kinds. They appear in `OpenGodDecisionKind`
    but `decide()` never returns them.

12. **`OpenAICompatibleProviderRuntime._build_request` masked key
    is dead code** — the masking at line 137 is overwritten
    immediately at line 216 in `call()`. If someone uses
    `_build_request(with_auth=True)` directly, they get a
    request with `Authorization: Bearer ***REDACTED***` which
    is useless. Remove the masking, or document that the
    caller must inject the real key after `_build_request`.

13. **`OpenAICompatibleProviderRuntime.stream()` is not a real
    stream** — it just calls `call()` and yields one terminal
    chunk. This is documented but is a smell; the spec says
    "StreamingChunk" which implies incremental delivery.

14. **`session_command` does not emit JSON for errors** — other
    commands emit a structured JSON error on `json_output=True`,
    but `session_command._emit_error` only writes to stderr.
    Inconsistent.

15. **`AgentBus.publish()` claims to "translate + dispatch" but
    only translates** — the receipt contains commands but no
    execution result. The `dispatch()` method exists but is
    broken (bug #2), and even if it worked, `publish()` doesn't
    call it. The function name and docstring lie.

### Low (dead code / cosmetic)

16. **`translate_event()` line 121 `if kind is not None:` is dead
    code** — all translatable event kinds are caught by the
    earlier `if event.kind == "..."` branches and return
    early. Minor.

17. **`MockProviderRuntime.stream()` declared return is
    `Iterable[StreamingChunk]`** but the implementation is a
    generator. `Iterable` doesn't have `__next__`, so callers
    must materialise the generator. Should be `Iterator`.

18. **`Workbench.build_context` calls `self.adapter_registry.get()`
    twice** in lines 110-111. Trivial.

## Plan to fix

* Fix #1 by redacting the Authorization header before storing
  `last_prepared`, or remove `last_prepared` entirely.
* Fix #2 by changing `AgentBus.dispatch()` to use
  `explain=self._dry_run` (matching the v0.2 `CommandRunner.run`
  signature).
* Fix #3, #4, #5 by adding budget commit, fixing the
  `needs_live_flags` logic, and fixing the orchestrator's
  `explain` polarity.
* Fix #6, #7, #8, #9 by replacing the broad `except Exception`
  with specific handling, and fixing the workbench's
  `FusionTaskProfile` / `FusionTrigger` construction to use
  valid literal values and the real field names.
* Fix #10 by inverting the budget check.
* Fix #11 by adding rules for `ask_user` and `needs_replan`
  (e.g. if `budget_max_usd == 0` and `allow_live_provider`,
  choose `ask_user`).
* Fix #12 by removing the dead masking.
* Fix #13 by documenting more clearly (or removing the
  misleading "streaming" labelling).
* Fix #14 by making `session_command._emit_error` honour
  `json_output`.
* Fix #15 by either dispatching in `publish()` (and re-raising
  the broken-runner exception clearly) or by changing the
  docstring to "translate only".
* Fix #16-18 as cleanup.

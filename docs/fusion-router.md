# LoopOS Fusion Router

Fusion Router is the **escalation layer** above LoopOS' default
single-model agent loop. It is *not* the default execution path.
The default remains:

```text
single model -> ACI -> ALI -> Kernel -> Trace
```

Fusion Router activates only when there is evidence that normal
execution is insufficient:

* the user explicitly asks for it (``loopos mad-dog`` or
  ``--reason explicit_user_request``);
* the agent loop is struggling (repeated failure, no progress);
* the task is large, nasty, or high-risk (large refactor, nasty
  bug, release blocker, security-sensitive);
* the user has shown repeated dissatisfaction;
* the current model is weak for the required task type
  (model mismatch).

The slogan:

```text
Mad Dog Mode increases intelligence density, not authority level.
```

Chinese:

```text
疯狗模式只提升智力密度，不提升权限等级。
```

## Scope

Fusion Router v0.2 implements the **planning layer**:

* Fusion models (Pydantic v2 typed contracts).
* Deterministic scoring formula.
* Mode selection (single / pair / committee / attack / mad_dog).
* Role assignment against the metadata-only Provider Registry.
* `FusionPlan` + `FusionVerdict` generation.
* CLI: `fusion-router plan / explain / run / escalate / status`
  plus the `mad-dog` alias.
* Optional trace persistence (`kind="signal"`,
  `type="fusion.plan"` / `type="fusion.verdict"`).
* Recommended (never executed) ACI commands.

Explicitly deferred to v0.3+:

* actual multi-provider parallel calls;
* live provider fanout;
* model debate loops;
* automatic paid API spending;
* real-time TUI / gateway / ACP integration.

Fusion Router is **aggressive in reasoning and review** but
**conservative in authority**. It recommends ACI commands; only
ACI / Kernel / Syscall Router may execute governed commands.

## Architectural Position

```text
User / Kernel / ALI / Convergence
        ↓
FusionTrigger
        ↓
Fusion Router
        ↓
Provider Registry (metadata-only)
        ↓
Role Assignment
        ↓
FusionPlan
        ↓
ACI AgentCommands (recommendations only)
        ↓
Policy OS  →  Syscall Router  →  ALI FSM  →  Trace / Replay
```

Fusion Router never bypasses Policy OS, the Syscall Router, or
the existing trace runtime. It never executes shell / subprocess
directly. It never calls a live provider API.

## CLI

| command | behavior | side effects |
|---|---|---|
| `loopos fusion-router plan task.json --json` | Build a `FusionPlan` from the task JSON | none |
| `loopos fusion-router explain task.json --json` | Return the activation rationale | none |
| `loopos fusion-router run task.json --dry-run --json` | Same as `plan` (router is planning-only) | none |
| `loopos fusion-router run task.json --json` | Same as `plan`; live execution deferred to v0.3+ | none |
| `loopos fusion-router escalate --run-id RUN_ID --reason REASON --json` | Build a plan triggered by `run_id` evidence | none |
| `loopos fusion-router status FUSION_ID --json` | Returns `unsupported` payload (no persistence in v0.2) | none |
| `loopos mad-dog task.json --json` | Force `mode = "mad_dog"`, `reason = "explicit_user_request"` | none |
| `loopos mad-dog explain task.json --json` | Explain under the mad-dog trigger shape | none |
| `loopos mad-dog escalate --run-id RUN_ID --reason REASON --json` | Mad-dog escalation with `severity="critical"` default | none |

The `mad-dog` command is a friendly alias for the explicit
user-force mode. `mad-dog` must still obey Policy OS, the budget
limit, and provider availability. It must not run destructive
commands or live provider calls in v0.2.

## Fusion Modes

| mode | trigger | roles |
|---|---|---|
| `single` | score < 8 (default) | primary |
| `pair` | 8 ≤ score < 15 | coder, reviewer |
| `committee` | 15 ≤ score < 25 | planner, coder, reviewer |
| `attack` | 25 ≤ score < 35 | planner, coder, bug_hunter, test_breaker, judge |
| `mad_dog` | score ≥ 35 or explicit user request | planner, architect, bug_hunter, coder, test_breaker, security_guard, simplifier, reviewer, judge, summarizer |

Task-type adjustments (additive to the base mode):

* `security` → + `security_guard`
* `refactor` → + `architect`, `simplifier`
* `bugfix` / `debugging` → + `bug_hunter`, `test_breaker`
* `release` → + `security_guard`, `reviewer`, `summarizer`
* `audit` → + `reviewer`, `judge`
* `architecture` → + `architect`, `simplifier`
* `test_repair` → + `test_breaker`, `bug_hunter`

Trigger-forced roles:

* `user_dissatisfaction` → + `reviewer`, `judge`, `summarizer`
* `repeated_failure` → + `bug_hunter`, `test_breaker`
* `no_progress` → + `reviewer`, `judge`
* `security_sensitive` → + `security_guard`
* `release_blocker` → + `security_guard`, `reviewer`, `judge`

## Trigger Scoring

Formula:

```python
fusion_score = (
    complexity_score * 2
    + failure_count * 3
    + user_dissatisfaction_count * 4
    + risk_score * 2
    + affected_file_count
    + no_progress_count * 3
    + release_blocker_bonus  # +20
    + security_sensitive_bonus  # +12
    + model_mismatch_bonus  # +8
)
```

A deterministic severity multiplier is applied at the end:

| severity | multiplier |
|---|---|
| `low` | 1.0 |
| `medium` | 1.1 |
| `high` | 1.25 |
| `critical` | 1.5 |

Explicit user request (`reason == "explicit_user_request"` and
`requested_mode` set) overrides the score threshold.

## Provider Selection

The router reads the metadata-only :mod:`loopos.providers`
registry and derives a :class:`ModelCapabilityProfile` for each
provider. Missing scores fall back to conservative defaults (5
out of 10) so a profile is always well-formed.

Deterministic tie-breakers (per master prompt):

1. higher capability score
2. lower cost if scores are close
3. higher reliability
4. provider_id alphabetical
5. model_id alphabetical

The router never calls a live provider API.

## ACI Bridge

Fusion Router recommends ACI commands; it never executes them.
The recommended commands are serialised as plain dicts in
`FusionPlan.recommended_aci_commands` with the following fields:

```python
{
    "sequence": int,
    "kind": str,            # e.g. "file.read", "file.patch", "noop"
    "purpose": str,
    "role": str,            # role in FusionRole taxonomy
    "task_id": str,
    "goal_id": str | None,
    "dry_run": True,
    "execution_owner": "aci",
    "trigger_reason": str,
}
```

Only ACI / Kernel / Syscall Router may execute governed commands.

## Trace Integration

When the runtime exposes a :class:`loopos.kernel.trace.TraceStore`,
the bridge persists each `FusionPlan` as a `signal` event with
`type="fusion.plan"` and each `FusionVerdict` with
`type="fusion.verdict"`. The bridge does **not** introduce a new
`TraceKind`; legacy trace consumers can filter without parsing
payloads.

Payload keys are serialised in a canonical order so a replay
consumer reconstructs the plan deterministically.

## Tests

| file | tests |
|---|---|
| `tests/test_fusion_router_models.py` | 11 |
| `tests/test_fusion_router_scoring.py` | 10 |
| `tests/test_fusion_router_roles.py` | 10 |
| `tests/test_fusion_router_provider_selection.py` | 3 |
| `tests/test_fusion_router_aci_bridge.py` | 7 |
| `tests/test_fusion_router_trace.py` | 5 |
| `tests/test_fusion_router_cli.py` | 13 |

Total: 71 tests covering:

* Models: roundtrip + extra-fields-rejected + score-bounds.
* Scoring: thresholds + explicit override + determinism.
* Roles: mode -> role matrix + task-type adjustments + trigger
  forces + provider reuse degradation + no-provider fallback.
* Provider selection: deterministic role-to-profile matching.
* ACI bridge: planning-only + dry-run + execution_owner=aci +
  no shell/subprocess + no provider transport imports.
* Trace: persistence + replay + roundtrip + filter.
* CLI: plan / explain / dry-run / status / escalate / mad-dog
  + error paths.

## File Layout

| file | purpose |
|---|---|
| `loopos/fusion_router/__init__.py` | package surface |
| `loopos/fusion_router/models.py` | typed contracts |
| `loopos/fusion_router/scoring.py` | deterministic score + mode selection |
| `loopos/fusion_router/roles.py` | role assignment + capability derivation |
| `loopos/fusion_router/router.py` | `FusionRouter` (plan / explain / dry_run / create_verdict) |
| `loopos/fusion_router/trace.py` | `fusion.plan` + `fusion.verdict` trace bridge |
| `loopos/fusion_router/cli.py` | internal CLI helpers |
| `loopos/cli/commands/fusion_router.py` | `loopos fusion-router ...` command |
| `loopos/cli/commands/mad_dog.py` | `loopos mad-dog ...` alias |

`loopos/fusion/` (the panel-based fusion module from earlier
phases) is intentionally untouched. The new escalation router
lives under `loopos/fusion_router/` and registers as
`fusion-router` to avoid the namespace collision.

## Safety Invariants

* no push
* no tag mutation
* no dist mutation
* no release-evidence mutation
* no `loopos/model_kernel/*` diff
* no `loopos/kernel/*` diff
* no live provider calls (asserted by AST scan + monkey-patch
  tests)
* no direct subprocess / shell execution
* no authority escalation (Fusion Router recommends, never
  executes)
* one-way dependency: `kernel -> trace.bridge -> kernel.trace`;
  `fusion_router -> providers` (metadata-only)
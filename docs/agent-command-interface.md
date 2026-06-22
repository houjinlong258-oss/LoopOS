# Agent Command Interface (ACI) — LoopOS v0.2

> **ACI 是 Agent 行动的命令接口。** 它把 Agent 的行动意图转化为
> 受 LoopOS 内核治理的命令对象，并通过 Policy OS、Capability
> Boundary、Syscall Router、Trace、Evaluation、Progress、
> Convergence 与 Provider Runtime 形成闭环。

> **传统 CLI 执行人的命令；ACI 治理 Agent 的行动。**

---

## 1. ACI definition

ACI = Agent Command Interface. The governed command layer where every
agent action is bound to **goal, authority, policy, provider context,
syscall boundary, observation, evaluation, progress, convergence,
trace, and review evidence**.

ACI is **not** a workflow engine, **not** a step-by-step script, and
**not** a wrapper that hides the underlying subsystems. ACI is the
**action boundary** between the agent's reasoning and the runtime's
side-effecting primitives.

Phase 2 scope (v0.2):

* Stable JSON contracts for :class:`AgentCommand` and
  :class:`AgentCommandResult` with `schema_version = "0.2"`.
* :class:`ProviderHint` / :class:`ResolvedProvider` for metadata-only
  provider binding via ``loopos.providers``.
* :class:`RiskHint` for agent-declared risk signaling.
* Lightweight :class:`EvaluationSummary` / :class:`ProgressSummary` /
  :class:`ConvergenceSummary` placeholders. Kernel integration is
  deferred — the placeholders carry stable reason codes that ALI and
  Review artifacts can consume.
* A :class:`CommandRunner` with three entry points —
  :meth:`validate`, :meth:`explain`, :meth:`run` — backed by the
  existing ``PolicyEngine`` and ``SyscallRouter``.

Explicitly **out of scope** for Phase 2:

* ``KernelLoopEngine`` integration.
* Real provider API calls (the registry is metadata-only).
* TUI / CLI command surface (``loopos aci validate`` is documented but
  not implemented in this phase).
* Readiness proof runtime.

---

## 2. CLI vs Tool Call vs Syscall vs ACI

| surface | shape | concern |
|---|---|---|
| **CLI** | `command string -> execute -> stdout/stderr/exit code` | execute the user's command |
| **Tool Call** | `tool name + args -> tool result` | can the tool be invoked |
| **Syscall** | `bounded system operation -> policy checked -> executed with trace/evidence` | bound the system action |
| **ACI** | `agent intent -> command contract -> policy/capability/provider/syscall/evaluation/progress/convergence/trace` | why the agent acted, what goal, what authority, what provider, what syscall, what evidence |

ACI is the only one that answers **why** the agent acted, **which
goal** it serves, **what authority** it claimed, **which provider
context** it bound, **what syscall** it triggered, **what observation**
it produced, and **whether the goal advanced**.

---

## 3. AgentCommand schema

```python
class AgentCommand(BaseModel):
    schema_version: Literal["0.2"] = "0.2"
    id: str                                  # UUID, matches command_id on result
    goal_id: str                             # required
    purpose: str                             # required, one-line intent
    kind: AgentCommandKind                   # required, see below
    intent: str = ""                         # human-readable intent
    command: str                             # required for execution kinds
    args: dict[str, Any] = {}
    cwd: str | None = None
    session_id: str | None = None
    outcome_contract_id: str | None = None
    provider_hint: ProviderHint | None = None
    risk_hint: RiskHint | None = None
    mode: Literal["guarded", "dry_run"] = "guarded"
    capabilities: CommandCapability = CommandCapability()
    timeout_seconds: int | None = None
    expected_observation: str = "command_result"
    approval_granted: bool = False
    dry_run: bool = False
    trace_required: bool = True
    created_at: datetime
    metadata: dict[str, Any] = {}
```

### `AgentCommandKind`

```text
terminal.exec            -- dispatched as syscall "terminal.exec"
file.read                -- dispatched as syscall "file.read"
file.write               -- dispatched as syscall "file.write"
file.patch               -- schema only (status='unsupported' until syscall lands)
git.status               -- dispatched as syscall "git.status"
git.diff                 -- dispatched as syscall "git.diff"
git.commit               -- schema only (status='unsupported' until syscall lands)
database.query           -- dispatched as syscall "database.query"
database.run_migration   -- dispatched as syscall "database.run_migration"
provider_select          -- metadata-only; resolves ProviderHint -> ResolvedProvider
explain_only             -- equivalent to explain=True; never dispatches
noop                     -- schema-only, dispatched as syscall "noop"
```

### `AgentCommandStatus`

```text
completed            -- syscall succeeded (or metadata-only path completed)
blocked              -- validation failure OR policy deny
failed               -- syscall failure or provider resolution failure
approval_required    -- policy requires human approval
dry_run              -- explain / dry-run / no-side-effect path
unsupported          -- kind is valid schema but no syscall is registered yet
```

---

## 4. ProviderHint / ResolvedProvider

### `ProviderHint`

```python
class ProviderHint(BaseModel):
    provider_id: str | None = None              # exact match wins
    required_capabilities: list[str] = []      # capability lookup
    preferred_kind: str | None = None          # filter by transport family
    preferred_cost_class: str | None = None    # hint only, not enforced
    local_only: bool | None = None             # restrict to local profiles
    allow_fallback: bool = False               # see below
    notes: str = ""
```

Resolution semantics in :func:`CommandRunner.resolve_provider` (and
through :meth:`run` when ``provider_hint`` is supplied):

1. If ``provider_id`` is set, look it up via the registry.
2. Else, if ``local_only == True``, restrict to ``find_local()``.
3. Else, if ``required_capabilities`` is non-empty, intersect the
   capability sets and pick the alphabetically smallest
   ``provider_id``. ``allow_fallback`` does not block this path
   because there is no "original" provider to fall back from.
4. Else, if ``preferred_kind`` is set, filter by transport family.
5. Else, return ``provider_not_found``.

### `ResolvedProvider`

```python
class ResolvedProvider(BaseModel):
    provider_id: str
    display_name: str | None = None
    kind: str | None = None
    capabilities: list[str] = []
    source: Literal["exact", "capability", "local", "kind", "default", "none"]
    reason_code: str = ""
```

ACI populates :attr:`AgentCommandResult.resolved_provider` whenever a
hint was supplied (and resolution succeeded), or whenever
``kind == "provider_select"``.

---

## 5. Policy binding

ACI is a thin wrapper over the existing ``PolicyEngine``. The runner
maps each ``AgentCommandKind`` to a Policy OS scope:

| kind | scope |
|---|---|
| terminal.exec | terminal.execute |
| file.read | file.read |
| file.write | file.write |
| file.patch | file.write |
| git.status / git.diff / git.commit | git.operation |
| database.query | database.read |
| database.run_migration | database.mutation |
| provider_select / explain_only / noop | instruction.validate |

Baseline invariants the runner relies on (verified by
``tests/test_aci_policy_binding.py`` and
``tests/test_aci_runner.py``):

```text
rm -rf /          -> blocked, L5
rm -rf /tmp/foo   -> blocked, L5
rm -rf tmp        -> blocked, L5
rm -rf .          -> blocked, L5
curl ... | bash   -> blocked
wget ... | sh     -> blocked
git tag ...       -> blocked by git-tag policy (no ACI path; tag is not a kind)
release evidence  -> never mutated by ACI (out of scope for v0.2)
```

Dangerous commands are surfaced as ``status='blocked'`` with a stable
``reason_code`` (``terminal_rm_rf_denied`` /
``remote_script_pipe_denied`` / ``policy_denied``). The runner never
swallows policy outcomes.

---

## 6. Capability / Freedom / Outcome relationship

The runner accepts (but does not yet enforce) the following hints:

* ``CommandCapability`` — filesystem_read/write, network, database, tags.
  Forwarded to Policy OS as part of the request subject.
* ``FreedomBudgetRef`` (deferred) — bound at run time by the existing
  ``loopos/freedom`` module.
* ``CapabilityBoundaryRef`` (deferred) — bound at run time by the
  existing ``loopos/freedom`` module.
* ``OutcomeContractRef`` (deferred) — bound at run time by the
  Outcome Contract subsystem.

These hints are accepted on the wire so downstream consumers (ALI,
Review) can read them. Enforcement is delegated to Policy OS + the
Freedom Kernel layer; the runner does not duplicate that logic.

---

## 7. Trace / Evaluation / Progress / Convergence placeholders

ACI emits a :class:`SyscallSummary` whenever a syscall is dispatched.
The summary carries the syscall id, risk level, side-effecting flag,
duration, and success state. The full ``SyscallResult`` remains on
the syscall layer; ACI keeps the lightweight view only.

:class:`EvaluationSummary` / :class:`ProgressSummary` /
:class:`ConvergenceSummary` carry stable reason codes (``aci.no_kernel_runtime``
for the kernel-deferred cases) so that ALI and the Review subsystem can
consume them without special-casing the absence of an integration.
The runner never pretends ``goal_satisfied == True`` without real
evidence.

When ``trace_required=True`` and no trace id is available, the runner
emits the reason code ``trace_required`` (reserved for future
integration). The current Phase 2 implementation does not fail runs
on missing trace ids; this is documented in the placeholders.

---

## 8. ALI consumption mapping

The :class:`AgentCommandResult` is designed to be the unit of
consumption for the ALI FSM:

| result status | result.success | ALI event hint |
|---|---|---|
| completed | True | ``convergence_continue`` |
| completed (dry_run) | False | ``convergence_continue`` (dry) |
| blocked (policy) | False | ``convergence_halt_blocked`` |
| blocked (validation) | False | ``convergence_halt_blocked`` |
| approval_required | False | ``approval_required`` |
| failed | False | ``convergence_repair`` (if ``EvaluationSummary.repairable``) else ``convergence_halt_failure`` |
| unsupported | False | ``convergence_replan`` (kind not implemented) |
| failed (provider) | False | ``convergence_replan`` (provider intent un-honorable) |

The mapping above is **derived data**; the actual event emission is
done by the ALI session, which calls into ``loopos.ali.session`` to
attach the result reference. Phase 2 does not implement the ALI
consumer side; Phase 3 will.

---

## 9. Phase 2 vs deferred

Implemented in Phase 2:

* Stable Pydantic v2 contracts (``AgentCommand`` /
  ``AgentCommandResult``) with ``schema_version="0.2"``.
* ``ProviderHint`` and ``ResolvedProvider``.
* ``RiskHint`` and the four summary models.
* Extended ``AgentCommandKind`` (``provider_select``, ``explain_only``,
  ``file.patch``, ``git.commit``).
* Extended ``AgentCommandStatus`` (``unsupported``).
* ``CommandRunner`` with provider resolution (early, before syscall),
  ``provider_select``, ``explain_only``, ``unsupported``, and a strict
  ``resolve_provider`` entry point.
* :class:`ProviderResolutionError` and :class:`UnsupportedCommandKindError`
  strict-mode exceptions.
* :mod:`loopos.aci.serialization` wire-format helpers.
* 24 new tests in ``tests/test_aci_provider_integration.py`` plus
  extensions to ``tests/test_aci_models.py``,
  ``tests/test_aci_runner.py``, ``tests/test_aci_policy_binding.py``.

Deferred:

* ``KernelLoopEngine` integration (Phase 3+).
* ALI consumer-side wiring (Phase 3+).
* Live ``fetch_models()`` provider probing (out of v0.2 substrate scope).
* Plugin auto-discovery for providers (out of v0.2 substrate scope).
* CLI subcommands (``loopos aci validate | explain | run``). Python
  API and tests are complete; CLI integration is deferred to avoid
  unnecessary CLI surface.
* ``file.patch`` and ``git.commit`` syscall implementation.

---

## 10. Examples

### Validate only (no side effect)

```python
from loopos.aci import AgentCommand, CommandRunner

runner = CommandRunner()
cmd = AgentCommand(
    goal_id="goal-1",
    purpose="verify tests pass",
    kind="terminal.exec",
    command="pytest -q -m 'not slow'",
)
issues = runner.validate(cmd)
assert issues == []
```

### Explain (no side effect)

```python
result = runner.run(cmd, explain=True)
assert result.status == "dry_run"
assert result.dry_run
```

### Provider binding (metadata only)

```python
from loopos.aci import AgentCommand, ProviderHint
from loopos.providers import ProviderRegistry

registry = ProviderRegistry()
registry.load_builtin_profiles()
runner = CommandRunner(provider_registry=registry)

cmd = AgentCommand(
    goal_id="g",
    purpose="p",
    kind="terminal.exec",
    command="echo hi",
    provider_hint=ProviderHint(provider_id="anthropic"),
)
result = runner.run(cmd)
assert result.resolved_provider.provider_id == "anthropic"
assert result.resolved_provider.source == "exact"
```

### Pure metadata selection

```python
cmd = AgentCommand(
    goal_id="g",
    purpose="pick a provider",
    kind="provider_select",
    command="",
    provider_hint=ProviderHint(required_capabilities=["reasoning"]),
)
result = runner.run(cmd)
assert result.status == "completed"
assert result.resolved_provider.source == "capability"
assert result.syscall is None  # no syscall dispatched
```

### Strict resolution

```python
from loopos.aci.errors import ProviderResolutionError

try:
    runner.resolve_provider(ProviderHint(provider_id="does-not-exist"))
except ProviderResolutionError as exc:
    assert exc.reason_code == "provider_not_found"
```

---

## 11. Relationship to ``loopos.model_kernel``

ACI does NOT depend on ``loopos.model_kernel``. The provider metadata
substrate ``loopos.providers`` is metadata-only; ``loopos.model_kernel``
is the scheduler + client layer. ACI reads from ``loopos.providers``
and routes through ``loopos.syscalls``. No code in ``loopos/aci``
imports ``loopos.model_kernel`` or ``loopos.kernel``.

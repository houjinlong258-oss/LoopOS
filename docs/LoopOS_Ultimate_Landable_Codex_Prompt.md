# LoopOS Ultimate Landable Codex Prompt

版本：v1.0 Ultimate  
文件建议名：`LoopOS_Ultimate_Landable_Codex_Prompt.md`  
目标：给 Codex / Claude Code / OpenHands / 自建 Coding Agent 使用，直接驱动一个**可落地、可运行、可扩展、可开源生态化**的 LoopOS 项目实现。  
定位：这不是 MVP 提示词，而是完整项目目标提示词；但实现必须按阶段推进、每阶段可测试、可提交、可回滚。

---

## 0. 最终一句话

> **LoopOS 是一个终端原生、策略治理、可审计、可回放、可持续循环运行的开源 Agent Runtime OS。**

英文定位：

> **LoopOS — The open Agent Runtime OS for Loop Engineering.**

中文定位：

> **LoopOS：面向 Loop Engineering 的开源 Agent 运行时操作系统。**

品牌口号：

> **Not another agent. The kernel for running agents.**  
> **不是又一个 Agent，而是运行 Agent 的内核。**

吉祥物：

> **Loopi / 小环狸：住在终端里的 Agent Loop 守护者。**

---

## 1. 给 Codex 的总控身份

把下面这段作为 Codex 的主任务 Prompt。

```text
You are the chief implementation engineer for LoopOS.

LoopOS is an open-source, terminal-native Agent Runtime OS for Loop Engineering.

This is not a chatbot.
This is not a simple CLI wrapper.
This is not a toy autonomous agent.
This is not a web dashboard.
This is not a copy of Claude Code, Codex CLI, Hermes, OpenHands, Devin, Manus, Cursor, Windsurf, or Marvis.

LoopOS is a kernel-style runtime for running agents safely, observably, and repeatedly.

Your job is to implement a landable production-grade project, not a mock demo.

Core requirements:
1. Terminal-native CLI with excellent UX.
2. Structured AIL / AI-ISA internal protocol.
3. Goal Negotiation Kernel for vague goals.
4. Loop Convergence Kernel for measurable progress and stopping.
5. Outer Loop Engineering Kernel for triggers, task queues, worktrees, producer/reviewer/verifier separation.
6. Policy OS as a non-bypassable safety and behavior layer.
7. Syscall / MCP layer for all external actions.
8. Safe Terminal Executor with workspace guard.
9. Memory Governance and Skill Governance.
10. Provider Gateway supporting multiple AI providers through profiles.
11. Multi-Model Scheduler with vision companion and verifier roles.
12. ChatOps / mobile gateway for remote approval and conversation operation.
13. Local Workspace Intelligence with privacy-first indexing.
14. Execution backend abstraction for local, docker, ssh, OpenHands, and future remote backends.
15. Trace replay, audit logs, and explainability.
16. Plugin ecosystem: providers, skills, policies, gateways, execution backends, benchmarks.
17. Strong tests and deterministic behavior.

Hard rules:
- Do not execute ambiguous raw goals directly.
- Do not call tools during goal negotiation.
- Do not bypass Policy OS.
- Do not bypass Memory Governance.
- Do not bypass Syscall Router.
- Do not run dangerous shell commands.
- Do not write long hidden reasoning to logs.
- Do not create WebUI for the first deliverable.
- Do not create desktop GUI for the first deliverable.
- CLI must be terminal-native and beautiful.
- Tests must not call real LLM APIs, real network APIs, or dangerous commands.
- Every phase must leave the repository passing tests.

Start by reading this document and executing Phase 0.
```

---

## 2. 参考对象与吸收策略

LoopOS 不是复制任何一个产品，而是吸收它们的系统模式。

| 参考对象 | 值得吸收 | LoopOS 的升级方式 |
|---|---|---|
| Claude Code | 终端 coding agent、权限确认、MCP、hooks、skills、subagents、worktree 思路 | 吸收 CLI UX 和工程执行体验，但把它内核化为 Policy OS + Syscall + Trace |
| Codex CLI | 本地终端 coding agent、开源 CLI、代码修改/运行命令 | 吸收轻量终端体验，但扩展为多模型、多策略、多 loop runtime |
| OpenHands | 开源软件工程 agent、沙箱、执行环境、云端/本地 agent | 作为 Execution Backend / Engineering Agent Backend |
| Devin / Jules | 任务队列、repo/issue 工作流、PR 风格工程闭环 | 吸收 Outer Loop、worktree、producer/reviewer/verifier 分离 |
| Cursor / Windsurf | 代码库索引、开发者体验、上下文召回 | 吸收 Local Workspace Intelligence，不先做 IDE |
| Hermes | 多 provider、多 gateway、skills、MoA、多平台消息接入 | 吸收生态范围，变成 Provider Gateway + ChatOps Gateway + Skill Registry |
| Marvis | OS-level assistant、本地文件智能、手机远程、端云/本地模式 | 吸收 OS Control、Local-first、ChatOps Remote Approval、Compute Router |
| LangGraph | 状态机、graph workflow、可控 agent loop | 可作为后端之一，但 LoopOS 自身仍要有 Kernel Scheduler |
| CrewAI / AutoGen | 多 agent 角色协作 | 吸收角色设计，但受 Policy OS 与 Trace 约束 |
| Kubernetes / Linux / VS Code | 内核稳定、扩展生态、插件标准 | LoopOS Core 稳定，生态通过插件扩展 |

最终策略：

```text
不要做“又一个 Agent 产品”。
要做“运行 Agent 的开源内核和生态标准”。
```

---

## 3. 最终产品模式

LoopOS 的完整产品形态由四层组成。

```text
Layer 1: LoopOS Core
  AIL, Kernel Scheduler, Policy OS, Syscall Router, Trace, Memory Governance

Layer 2: Runtime Capabilities
  Goal Negotiation, Loop Convergence, Outer Loop, Worktree, Review, Execution Backends

Layer 3: Ecosystem Interfaces
  Provider Gateway, MCP Tools, Skills, Policies, ChatOps Gateway, Connectors, Benchmarks

Layer 4: User Interfaces
  CLI, REPL, Rich Terminal UI, ChatOps Mobile Approval, future TUI/Web/Desktop
```

第一版产品必须完成：

```text
1. 终端 CLI 可用。
2. 目标模糊时能生成方案。
3. 明确目标能生成 GoalSpec。
4. Policy OS 能解释和阻止危险动作。
5. LoopEngine 每轮有评价、进度、决策和停止。
6. Trace 可回放。
7. Memory/Skill 写入受治理。
8. 任务可持久化。
9. 代码任务可要求 worktree。
10. Provider/Gateway/Skill/Policy 插件有标准。
```

---

## 4. 项目核心原则

### 4.1 目标先规格化

错误：

```text
User raw text → Agent executes immediately
```

正确：

```text
Raw Goal → AmbiguityReport → Proposal / Confirmation → GoalSpec → Policy OS → LoopEngine
```

### 4.2 所有动作都是 syscall

错误：

```text
Planner directly runs shell command
```

正确：

```text
Planner emits AILInstruction
→ Policy OS
→ Syscall Router
→ Execution Backend
→ Observation
→ Evaluation
→ EventLog
```

### 4.3 Loop 的核心是收敛

Loop 不是多跑几轮，而是：

```text
Observation
→ EvaluationResult
→ ProgressDelta
→ LoopDecision
→ HaltCondition
```

### 4.4 持续运行必须有 Outer Loop

```text
Trigger
→ Task Queue
→ Worktree
→ Producer
→ Verifier
→ Reviewer
→ PR/Patch/Report
→ State Update
→ Next Trigger
```

### 4.5 生产和验收分离

```text
Producer cannot be final reviewer for high-risk work.
Verifier should be tool/test based where possible.
Reviewer should use separate context/model/role.
```

### 4.6 记忆不是事实

```text
Memory = governed belief / preference / failure pattern / skill signal
```

所有 memory 写入必须经过 governance。

### 4.7 开源生态必须插件化

核心仓库要稳，生态仓库要活。

```text
Core: strict
Plugins: open
Registry: audited
```

---

## 5. 目标仓库结构

Codex 应创建或重构为以下结构。

```text
loopos/
  __init__.py
  version.py

  cli/
    __init__.py
    app.py
    repl.py
    context.py
    options.py
    commands/
      run.py
      status.py
      trace.py
      step.py
      policy.py
      tools.py
      memory.py
      skills.py
      ail.py
      config.py
      goal.py
      tasks.py
      triggers.py
      worktrees.py
      review.py
      models.py
      gateway.py
      index.py
      os_control.py
      registry.py
      accountability.py
    renderers/
      theme.py
      icons.py
      panels.py
      tables.py
      trees.py
      progress.py
      diff.py
      approval.py
      goal_renderer.py
      trace_renderer.py
      task_renderer.py
      json_output.py

  ail/
    __init__.py
    ops.py
    base.py
    goal.py
    state.py
    instruction.py
    syscall.py
    observation.py
    evaluation.py
    event.py
    memory.py
    skill.py
    render.py
    codec.py
    validators.py

  kernel/
    __init__.py
    boot.py
    config.py
    run_manager.py
    process.py
    step.py
    scheduler.py
    loop_engine.py
    state_machine.py
    transition.py
    signals.py
    errors.py

  goal/
    __init__.py
    ambiguity.py
    proposal.py
    goal_spec.py
    negotiation.py
    templates.py
    clarifier.py
    selection.py

  convergence/
    __init__.py
    evaluation.py
    progress.py
    decision.py
    halt.py
    repair.py
    replan.py
    metrics.py

  policy_os/
    __init__.py
    models.py
    loader.py
    registry.py
    matcher.py
    resolver.py
    engine.py
    compiler.py
    audit.py
    explain.py

  syscalls/
    __init__.py
    types.py
    registry.py
    router.py
    result.py
    builtin/
      terminal.py
      file.py
      git.py
      os_control.py
      app.py
      browser.py
      provider.py
      gateway.py

  execution/
    __init__.py
    permissions.py
    terminal.py
    workspace.py
    sandbox.py
    backends/
      __init__.py
      base.py
      mock.py
      local.py
      docker.py
      ssh.py
      openhands.py

  context/
    __init__.py
    compiler.py
    budget.py
    relevance.py
    compression.py
    redaction.py

  memory/
    __init__.py
    event_log.py
    state_store.py
    run_store.py
    belief_store.py
    preference_store.py
    skill_store.py
    governance.py
    retrieval.py
    pre_action_gate.py
    conflict.py

  skills/
    __init__.py
    spec.py
    registry.py
    importer.py
    auditor.py
    project_skill.py
    onboarding.py
    policy.py

  model_kernel/
    __init__.py
    provider_profile.py
    provider_registry.py
    provider_loader.py
    capability.py
    router.py
    client.py
    mock_client.py
    multi_model.py
    vision_companion.py
    aggregator.py
    verifier.py

  gateway/
    __init__.py
    base.py
    message.py
    session.py
    auth.py
    attachment_router.py
    approval_router.py
    delivery_router.py
    progress_stream.py
    platforms/
      webhook.py
      telegram.py
      slack.py
      discord.py
      whatsapp_cloud.py
      email.py
      mock.py

  triggers/
    __init__.py
    base.py
    cron.py
    webhook.py
    git_event.py
    issue_event.py
    chat_event.py
    ci_event.py
    continuous.py
    registry.py

  tasks/
    __init__.py
    task.py
    board.py
    queue.py
    persistence.py
    selector.py
    quick_win.py
    state.py

  worktree/
    __init__.py
    lease.py
    manager.py
    branch.py
    cleanup.py
    conflict.py

  review/
    __init__.py
    roles.py
    producer.py
    reviewer.py
    verifier.py
    acceptance.py
    pr.py

  local_intel/
    __init__.py
    indexer.py
    file_index.py
    code_index.py
    doc_index.py
    image_index.py
    search.py
    privacy_filter.py
    change_watcher.py

  os_control/
    __init__.py
    system_info.py
    process.py
    network.py
    storage.py
    app_launcher.py
    settings.py
    permissions.py

  compute/
    __init__.py
    mode.py
    router.py
    data_policy.py
    cost_policy.py
    capability_policy.py

  knowledge/
    __init__.py
    entry.py
    personal_kb.py
    project_kb.py
    retrieval.py
    provenance.py
    privacy.py

  registry/
    __init__.py
    manifest.py
    installer.py
    auditor.py
    source.py

  connectors/
    __init__.py
    base.py
    github.py
    gitlab.py
    linear.py
    jira.py
    slack.py
    telegram.py
    ci.py
    staging_api.py

  responsibility/
    __init__.py
    accountability.py
    human_review.py
    audit.py

  agents/
    __init__.py
    intent_compiler.py
    planner.py
    critic.py
    memory_writer.py
    skill_extractor.py
    renderer.py
    roles/
      main.py
      file.py
      code.py
      computer.py
      browser.py
      search.py
      reviewer.py
      verifier.py

  integrations/
    __init__.py
    langgraph_adapter.py
    openhands_adapter.py
    letta_adapter.py
    zep_adapter.py
    projectmem_adapter.py
    hermes_import_notes.py

  eval/
    __init__.py
    runner.py
    metrics.py
    tasks.py
    benchmark_pack.py

policies/
  core/
    behavior.yaml
    honesty.yaml
    goal_negotiation.yaml
    loop_convergence.yaml
    outer_loop.yaml
  safety/
    terminal_safety.yaml
    prompt_injection.yaml
    harmful_content.yaml
    privacy.yaml
  tools/
    tool_routing.yaml
    mcp_policy.yaml
    file_policy.yaml
    git_policy.yaml
    os_control_policy.yaml
    worktree_policy.yaml
  memory/
    memory_applicability.yaml
    memory_governance.yaml
    user_preference.yaml
  coding/
    review_separation.yaml
    code_edit_policy.yaml
    pr_policy.yaml
  renderer/
    cli_output.yaml
    markdown.yaml
  optimization/
    context_budget.yaml
    loop_convergence.yaml

docs/
  final-architecture.md
  cli-ui.md
  ail.md
  policy-os.md
  goal-negotiation.md
  loop-convergence.md
  outer-loop-engineering.md
  syscalls.md
  memory-governance.md
  skill-kernel.md
  provider-gateway.md
  multi-model-scheduler.md
  chatops-gateway.md
  local-intelligence.md
  safety-levels.md
  plugin-spec.md
  registry.md
  open-source-governance.md
  brand-loopi.md

tests/
  ail/
  kernel/
  goal/
  convergence/
  policy_os/
  syscalls/
  execution/
  context/
  memory/
  skills/
  model_kernel/
  gateway/
  triggers/
  tasks/
  worktree/
  review/
  local_intel/
  os_control/
  compute/
  knowledge/
  registry/
  cli/
  eval/
```

---

## 6. 技术栈

必须使用：

```text
Python 3.11+
Pydantic v2
Typer
Rich
pytest
ruff
mypy
PyYAML
SQLite or JSONL for persistence
```

建议：

```text
orjson optional
watchdog optional
gitpython optional
pathspec optional
```

不允许首版依赖：

```text
Web UI framework
Desktop GUI framework
真实 LLM API
真实外部平台 API
危险 shell 操作
```

---

## 7. 核心数据模型

### 7.1 AILInstruction

```python
class AILInstruction(BaseModel):
    id: str
    run_id: str
    step: int
    op: str
    args: dict[str, Any]
    reason: dict[str, Any]
    safety: dict[str, Any] = Field(default_factory=dict)
    expect: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
```

校验：

```text
TERM.EXEC requires args.cmd
FILE.READ requires args.path
FILE.WRITE requires args.path and content or patch
TOOL.CALL requires args.tool
GOAL.FINALIZE requires GoalSpec
LOOP.HALT requires reason
```

### 7.2 GoalSpec

```python
class GoalSpec(BaseModel):
    goal_id: str
    original_input: str
    selected_proposal_id: str | None
    final_goal: str
    scope: list[str]
    non_goals: list[str]
    deliverables: list[str]
    acceptance_criteria: list[str]
    constraints: dict[str, Any]
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    created_from: Literal[
        "direct",
        "confirmed",
        "proposal_selected",
        "proposal_merged",
        "manual_edit"
    ]
```

硬约束：

```text
final_goal non-empty
scope non-empty
acceptance_criteria non-empty
Policy OS approval before execution
```

### 7.3 AmbiguityReport

```python
class AmbiguityReport(BaseModel):
    original_input: str
    ambiguity_score: float
    missing_fields: list[str]
    risk_factors: list[str]
    should_negotiate: bool
    should_confirm: bool
    reason_codes: list[str]
```

### 7.4 GoalProposal

```python
class GoalProposal(BaseModel):
    proposal_id: str
    title: str
    summary: str
    scope: list[str]
    non_goals: list[str]
    deliverables: list[str]
    acceptance_criteria: list[str]
    risk_level: Literal["low", "medium", "high"]
    estimated_steps: int
    requires_approval: bool
    recommended: bool = False
    reason_codes: list[str] = []
```

### 7.5 EvaluationResult

```python
class EvaluationResult(BaseModel):
    evaluation_id: str
    run_id: str
    step: int
    goal_satisfied: bool
    acceptance_criteria_status: dict[str, Literal["passed", "failed", "unknown"]]
    score: float
    failure_type: str | None
    repairable: bool
    regression_detected: bool
    evidence: list[str]
    reason_codes: list[str]
```

### 7.6 ProgressDelta

```python
class ProgressDelta(BaseModel):
    progress_id: str
    run_id: str
    step: int
    previous_score: float
    current_score: float
    delta: float
    improved: bool
    no_progress_count: int
    repeated_failure_count: int
    repeated_action_count: int
    regression_detected: bool
    reason_codes: list[str]
```

### 7.7 LoopDecision

```python
class LoopDecision(BaseModel):
    decision_id: str
    run_id: str
    step: int
    next_action: Literal[
        "continue",
        "repair",
        "replan",
        "ask_user",
        "wait_approval",
        "halt_success",
        "halt_failure",
        "halt_blocked"
    ]
    reason_codes: list[str]
    confidence: float
    repair_strategy: str | None = None
    replan_reason: str | None = None
    user_question: str | None = None
```

### 7.8 PolicyDecision

```python
class PolicyDecision(BaseModel):
    decision_id: str
    allowed: bool
    risk: Literal["low", "medium", "high", "blocked"]
    safety_level: Literal["L0", "L1", "L2", "L3", "L4", "L5"]
    requires_approval: bool
    requires_human_only: bool = False
    rollback_required: bool = False
    reason_codes: list[str]
    matched_rules: list[str]
    constraints: dict[str, Any] = Field(default_factory=dict)
    renderer_hints: dict[str, Any] = Field(default_factory=dict)
```

### 7.9 SyscallCall

```python
class SyscallCall(BaseModel):
    syscall_id: str
    run_id: str
    instruction_id: str
    name: str
    input: dict[str, Any]
    policy_decision_id: str
    risk: Literal["low", "medium", "high", "blocked"]
```

### 7.10 AILEvent

```python
class AILEvent(BaseModel):
    event_id: str
    run_id: str
    step: int
    kind: str
    payload: dict[str, Any]
    created_at: datetime
```

### 7.11 MemoryProposal

```python
class MemoryProposal(BaseModel):
    proposal_id: str
    memory_type: Literal[
        "belief",
        "preference",
        "failure_pattern",
        "skill_signal",
        "tool_profile",
        "project_rule"
    ]
    content: dict[str, Any]
    confidence: float
    context_tags: list[str]
    source_event_ids: list[str]
    proposed_by: str
```

### 7.12 SkillSpec

```python
class SkillSpec(BaseModel):
    skill_id: str
    name: str
    source: str
    description: str
    trigger_tags: list[str]
    required_tools: list[str]
    required_providers: list[str]
    risk_level: Literal["low", "medium", "high"]
    steps: list[dict[str, Any]]
    files: list[str]
    provenance: dict[str, Any]
    enabled: bool
    audit_status: Literal["safe", "needs_review", "blocked"]
    tests: list[str]
```

### 7.13 LoopTask

```python
class LoopTask(BaseModel):
    task_id: str
    source_trigger_id: str | None
    title: str
    description: str
    goal_spec_id: str | None
    status: Literal[
        "backlog",
        "ready",
        "running",
        "waiting_review",
        "waiting_human",
        "done",
        "failed",
        "blocked",
        "deferred"
    ]
    priority: Literal["low", "normal", "high", "urgent"]
    tags: list[str]
    acceptance_criteria: list[str]
    assigned_run_id: str | None
    worktree_id: str | None
    review_run_id: str | None
    failure_count: int
    created_at: datetime
    updated_at: datetime
```

### 7.14 WorktreeLease

```python
class WorktreeLease(BaseModel):
    lease_id: str
    task_id: str
    run_id: str
    path: str
    branch: str
    base_branch: str
    status: Literal["active", "released", "failed", "stale"]
    created_at: datetime
    expires_at: datetime | None
```

### 7.15 ProviderProfile

```python
class ProviderProfile(BaseModel):
    id: str
    aliases: list[str]
    base_url: str | None
    auth_type: str
    api_mode: str
    env_vars: list[str]
    capabilities: list[str]
    default_models: list[str]
    cost_class: Literal["low", "medium", "high", "unknown"]
    latency_class: Literal["low", "medium", "high", "unknown"]
    reliability_score: float
```

---

## 8. AIL / AI-ISA 指令集

必须支持以下 ops：

```text
GOAL.SET
GOAL.ANALYZE
GOAL.DETECT_AMBIGUITY
GOAL.PROPOSE_OPTIONS
GOAL.SELECT_OPTION
GOAL.REFINE
GOAL.MERGE_OPTIONS
GOAL.FINALIZE
GOAL.CONFIRM

CTX.COMPILE
PLAN.CREATE
PLAN.UPDATE

SYSCALL.PREPARE
TOOL.CALL
TERM.EXEC
FILE.READ
FILE.WRITE
GIT.STATUS
GIT.DIFF
OS.INFO
OS.PROCESS_LIST
OS.NETWORK_STATUS
OS.STORAGE_USAGE

STATE.PATCH
STATE.SNAPSHOT

EVAL.APPLY
EVAL.SCORE
PROGRESS.MEASURE
LOOP.DECIDE
LOOP.CONTINUE
LOOP.REPAIR
LOOP.REPLAN
LOOP.ASK_USER
LOOP.WAIT_USER_SELECTION
LOOP.WAIT_APPROVAL
LOOP.HALT

MEM.PROPOSE
MEM.COMMIT
SKILL.EXTRACT
SKILL.APPLY

TRIGGER.RECEIVE
TASK.CREATE
TASK.SELECT
TASK.DEFER
TASK.COMPLETE
TASK.FAIL

WORKTREE.CREATE
WORKTREE.RELEASE
WORKTREE.CLEANUP

ROLE.PRODUCER_RUN
ROLE.REVIEWER_RUN
ROLE.VERIFIER_RUN

REVIEW.CREATE
REVIEW.APPROVE
REVIEW.REQUEST_CHANGES
REVIEW.REJECT

PR.CREATE
PR.UPDATE
PR.READY_FOR_HUMAN

STATE.PERSIST
```

---

## 9. CLI UI 终极设计

CLI 是 LoopOS 的第一产品入口，必须做得专业、清晰、可传播。

### 9.1 总体风格

```text
Terminal-native
Rich panels
Clear step stream
Minimal noise by default
Verbose on demand
JSON machine mode
Beautiful but not distracting
```

主题颜色：

```text
Terminal Green: success / active
Loop Amber: approval / warning
Guard Red: blocked / danger
Memory Violet: memory / skill
Kernel Dark: background
```

符号规范：

```text
✓ success
✗ failed
⚠ approval / warning
⛔ blocked
→ next
∞ loop
● running
○ pending
```

### 9.2 全局命令

```bash
loopos --help
loopos run "<goal>"
loopos
loopos status <run_id>
loopos trace <run_id>
loopos step replay <run_id> <step>

loopos goal analyze "<goal>"
loopos goal propose "<goal>"

loopos policy explain --cmd "<cmd>"
loopos policy test <file>

loopos tools list
loopos tools inspect <tool>
loopos memory list
loopos skills list
loopos ail validate <file>

loopos triggers list
loopos triggers fire <name>
loopos tasks list
loopos tasks next --quick-win
loopos worktrees list
loopos review start <task_id>

loopos models list
loopos models inspect <provider>
loopos models route --task coding --input image

loopos gateway serve --platform webhook
loopos index build
loopos search "<query>"
loopos os info
loopos mode set privacy-local
loopos registry search skill
loopos registry install provider deepseek
```

### 9.3 `loopos run` 默认界面

```text
╭──────────────────────────────── LoopOS RUN ────────────────────────────────╮
│ Run ID      run_01HZM9                                                      │
│ Goal        修复当前 repo 的 pytest 失败                                      │
│ Workspace   /Users/dev/project                                               │
│ Mode        guarded / hybrid                                                 │
│ Model       primary: configured, verifier: mock                              │
│ Max Steps   20                                                               │
╰─────────────────────────────────────────────────────────────────────────────╯

[1/20] GOAL.SET
  ✓ goal parsed

[2/20] GOAL.ANALYZE
  ✓ clear enough
  ambiguity: 0.42
  action: confirmation

[3/20] GOAL.FINALIZE
  ✓ GoalSpec created
  acceptance:
    - pytest passes
    - no unrelated files modified
    - trace records all actions

[4/20] CTX.COMPILE
  ✓ context ready
  memories: 3  skills: 2  tools: 5  policies: 9

[5/20] PLAN.CREATE
  ✓ plan generated
  next: run tests

[6/20] TERM.EXEC
  $ pytest -q

  ✗ failed
  2 failed, 40 passed in 1.38s

[7/20] EVAL.APPLY
  score: 0.42
  failure_type: tests_failed
  repairable: true

[8/20] PROGRESS.MEASURE
  delta: +0.00
  no_progress_count: 1

[9/20] LOOP.DECIDE
  → repair
  reason: tests_failed, repairable

[10/20] FILE.READ
  ✓ tests/test_user.py

[11/20] FILE.WRITE
  ⚠ approval required
  file: src/user.py
  risk: medium
  reason: modifies workspace

Approve? [y/N/diff/details] diff

--- src/user.py
+++ src/user.py
@@
- if email:
+ if email is not None:

Approve? [y/N/diff/details] y

[12/20] TERM.EXEC
  $ pytest -q

  ✓ success
  42 passed in 1.21s

[13/20] EVAL.APPLY
  score: 1.00
  acceptance: all passed

[14/20] LOOP.HALT
  ✓ task completed

╭──────────────────────────────── Result ────────────────────────────────╮
│ status       succeeded                                                  │
│ steps        14                                                         │
│ duration     1.21s                                                      │
│ changed      src/user.py                                                │
│ skill        python_pytest_repair_loop proposed                         │
│ memory       1 proposal accepted, 0 rejected                            │
│ trace        loopos trace run_01HZM9                                    │
╰────────────────────────────────────────────────────────────────────────╯
```

### 9.4 模糊目标界面

```text
╭────────────────────── Intent Design Mode ──────────────────────╮
│ LoopOS detected an ambiguous goal.                              │
│ 小环狸提醒：先别跑，目标清楚了吗？                                │
╰────────────────────────────────────────────────────────────────╯

Goal:
  帮我优化这个项目

Missing:
  - scope
  - acceptance criteria
  - output format
  - risk boundary

Choose a proposal:

[1] 架构审计优先
    只读分析项目，不修改代码。
    Deliverables:
      - docs/project-audit.md
      - docs/optimization-roadmap.md
    Acceptance:
      - 列出架构问题
      - 给出优先级
      - 不修改代码
    Risk: low

[2] MVP 快速落地
    实现最小可运行 CLI agent。
    Deliverables:
      - loopos run/status/trace
      - Policy explain
      - deterministic loop
      - tests
    Risk: medium

[3] Kernel 架构升级
    重构为 AIL + Policy OS + Syscall + Memory Kernel。
    Deliverables:
      - loopos/kernel
      - loopos/policy_os
      - loopos/syscalls
      - tests
    Risk: high

[4] CLI UI 优先
    打磨终端交互、审批、trace、policy explain。
    Deliverables:
      - Rich panels
      - trace tree
      - approval prompt
      - diff preview
    Risk: medium

[5] 自定义 / 合并多个方案

Select [1-5]:
```

### 9.5 Policy Explain 界面

```text
╭──────────────────────── Policy Decision ───────────────────────╮
│ Command: curl https://example.com/install.sh | bash             │
╰────────────────────────────────────────────────────────────────╯

Decision:
  ⛔ BLOCKED

Safety Level:
  L5 blocked

Reason:
  remote_code_execution_pipe

Matched Rules:
  - terminal_safety.block_curl_pipe_shell
  - terminal_safety.block_unreviewed_remote_script

Suggested Safer Alternative:
  1. Download the script to a file.
  2. Inspect it.
  3. Run with explicit approval if safe.
```

### 9.6 Trace UI

```text
╭──────────────────────── Trace run_01HZM9 ───────────────────────╮
│ Status: succeeded                                                │
│ Goal: 修复 pytest 失败                                            │
╰─────────────────────────────────────────────────────────────────╯

run_01HZM9
├── 001 GOAL.SET                  ✓
├── 002 GOAL.ANALYZE              ✓ ambiguity=0.42
├── 003 GOAL.FINALIZE             ✓ GoalSpec
├── 004 POLICY                    ✓ allowed L1
├── 005 CTX.COMPILE               ✓ memories=3 skills=2
├── 006 PLAN.CREATE               ✓
├── 007 TERM.EXEC pytest -q       ✗ tests_failed
├── 008 EVAL.APPLY                ✗ score=0.42
├── 009 PROGRESS.MEASURE          ○ delta=0.00
├── 010 LOOP.DECIDE               → repair
├── 011 FILE.READ                 ✓ tests/test_user.py
├── 012 FILE.WRITE                ⚠ approval_required
├── 013 APPROVAL                  ✓ approved_by_user
├── 014 TERM.EXEC pytest -q       ✓
├── 015 EVAL.APPLY                ✓ score=1.00
└── 016 LOOP.HALT                 ✓ success
```

Options:

```bash
loopos trace run_01HZM9 --show-ail
loopos trace run_01HZM9 --show-policy
loopos trace run_01HZM9 --failed-only
loopos trace run_01HZM9 --json
```

### 9.7 Task Board UI

```text
╭──────────────────────── LoopOS Task Board ──────────────────────╮
│ backlog: 12   ready: 4   running: 1   review: 2   done: 38       │
╰────────────────────────────────────────────────────────────────╯

ID        Status          Priority   Risk    Title
task_001  ready           high       low     Fix flaky pytest test
task_002  waiting_review  normal     med     Update CLI trace renderer
task_003  backlog         low        low     Improve docs
task_004  blocked         high       high    Refactor execution backend
```

### 9.8 Review UI

```text
╭──────────────────────── Review Required ───────────────────────╮
│ Task: task_002                                                   │
│ Producer Run: run_02AB                                           │
│ Reviewer: reviewer_agent                                         │
│ Verifier: pytest + policy checks                                 │
╰────────────────────────────────────────────────────────────────╯

Verifier:
  ✓ pytest passed
  ✓ ruff passed
  ✓ dangerous command check passed

Reviewer Findings:
  - Diff is minimal.
  - Acceptance criteria satisfied.
  - No unrelated files modified.

Decision:
  ✓ approved

Next:
  Create PR? [y/N/details]
```

### 9.9 Interactive REPL

```text
LoopOS interactive shell

workspace: /Users/dev/project
mode: guarded
compute: hybrid
policy: enforce
model: primary configured
mascot: Loopi

loopos> 帮我优化这个项目

[Intent Design Mode]
这个目标比较模糊，我先给你几个方案...
```

REPL 命令：

```text
/help
/status
/trace
/policy
/tasks
/mode
/cancel
/exit
```

---

## 10. Safety Levels

实现 L0-L5。

```text
L0 observe:
  只读查看、总结、列目录、状态查询。

L1 low-risk local:
  运行安全测试、读取普通文件、创建临时文件。

L2 hard inquiry:
  修改文件、删除普通文件、修改配置、执行中风险命令。
  必须显示计划并要求确认。

L3 high-risk guarded:
  git reset、批量删除、系统设置修改、外部 API 写操作。
  必须二次确认、rollback plan、trace 记录。

L4 user-only:
  支付、提交敏感表单、发送不可撤销消息、上传隐私数据。
  Agent 只能指导，不能代执行。

L5 blocked:
  破坏性系统命令、泄露 secrets、绕过安全、恶意行为。
```

映射示例：

```text
file.read normal -> L0/L1
pytest -q -> L1
file.write source -> L2
git reset --hard -> L3
submit payment -> L4
rm -rf / -> L5
curl | bash -> L5
```

---

## 11. Policy OS 实现要求

Policy YAML 支持：

```yaml
id: terminal_safety.block_curl_pipe_shell
phase: TERM.EXEC
priority: 100
when:
  all:
    - field: instruction.args.cmd
      regex: "(curl|wget).*(\\||bash|sh)"
then:
  decision: block
  risk: blocked
  safety_level: L5
  reason_codes:
    - remote_code_execution_pipe
```

Matcher 支持：

```text
equals
not_equals
in
contains
regex
exists
lt
lte
gt
gte
all
any
not
```

Resolver：

```text
block overrides allow
higher priority wins
more specific rule wins
approval can downgrade high but not blocked
```

Policy explain 必须输出人能读懂的结果。

---

## 12. Goal Negotiation 实现要求

### 12.1 Ambiguity rules

高模糊词：

```text
优化
升级
改进
整理
自动化
做好
完善
增强
重构
修复一下
处理一下
搞一下
make it better
improve
optimize
upgrade
refactor
fix it
clean up
automate this
```

高模糊目标：

```text
帮我优化这个项目
把系统升级一下
帮我做得更好
整理这些资料
做一个自动化流程
```

中模糊：

```text
帮我修复 pytest 失败
帮我写 README
帮我整理 docs
```

低模糊：

```text
创建 hello.py，内容 print("hello")，运行 python hello.py，确认输出 hello。
```

### 12.2 Proposal templates

对于代码项目的模糊目标，默认生成：

```text
1. Read-only Audit
2. MVP / Direct Implementation
3. Kernel / Architecture Refactor
4. CLI UX / Product Experience
5. Custom / Merge
```

对于文档项目：

```text
1. Summarize
2. Reorganize
3. Rewrite
4. Create deliverable
5. Custom / Merge
```

对于自动化目标：

```text
1. Read-only workflow analysis
2. Local script automation
3. Triggered outer-loop automation
4. ChatOps automation
5. Custom / Merge
```

---

## 13. Loop Convergence 实现要求

每步必须：

```text
1. Execute or skip action.
2. Produce Observation.
3. Apply Evaluation.
4. Measure ProgressDelta.
5. Decide LoopDecision.
6. Append EventLog.
```

Halt 规则：

```text
acceptance_criteria_met -> halt_success
policy_blocked -> halt_blocked
user_denied -> halt_failure
max_steps_reached -> halt_failure
no_progress_count >= 2 -> replan
replan_count >= 2 and no progress -> halt_failure
repeated_action_count >= 2 -> replan
regression_detected -> replan or rollback
missing_required_tool -> ask_user or halt_failure
```

---

## 14. Syscall / MCP 实现要求

MVP syscalls：

```text
terminal.exec
file.read
file.write
git.status
git.diff
os.info
os.process.list
os.network.status
os.storage.usage
provider.chat.mock
gateway.send.mock
```

每个 syscall 必须：

```text
validate input
build PolicyContext
get PolicyDecision
if blocked: return blocked result
if approval required: wait for approval
execute adapter
capture result
normalize Observation
append EventLog
```

---

## 15. Execution Backend 要求

Backends：

```text
mock: tests only
local: actual local safe executor
docker: skeleton
ssh: skeleton
openhands: skeleton
```

Local terminal executor：

```text
cwd must stay inside workspace
timeout required
stdout/stderr captured
return code captured
env sanitized
dangerous command detection before subprocess
no shell=True unless explicitly needed and policy checked
```

测试禁止执行危险命令，只测试 policy 拦截。

---

## 16. Memory Governance 要求

Memory types：

```text
belief
preference
failure_pattern
skill_signal
tool_profile
project_rule
```

Governance：

```text
confidence < 0.4 -> reject
missing source_event_ids -> needs_review
duplicate -> dedupe
conflict -> link conflict, do not overwrite
preference without context -> reject
one-time selected proposal is not global preference
unconfirmed goal proposal is not memory
sensitive memory local-only
```

Store：

```text
.loopos/memory/beliefs.jsonl
.loopos/memory/preferences.jsonl
.loopos/memory/failure_patterns.jsonl
.loopos/memory/skills.jsonl
```

---

## 17. Skill Kernel 要求

Skill 从成功 trace 中提取。

规则：

```text
successful run only
at least 2 meaningful action events
requires acceptance criteria pass
requires governance
default disabled until audited if imported
dangerous skills need review
skill cannot bypass Policy OS
```

Skill examples：

```text
python_pytest_repair_loop
repo_audit_loop
policy_explain_loop
docs_rewrite_loop
```

---

## 18. Outer Loop 实现要求

Outer loop lifecycle：

```text
TriggerEvent
→ Task Intake
→ Goal Negotiation if needed
→ LoopTask ready
→ QuickWinSelector
→ WorktreeManager
→ ProducerRun
→ VerifierRun
→ ReviewerRun
→ PR/Patch/Report
→ Persistent State Update
→ Memory/Skill Governance
→ Next Loop
```

CLI：

```bash
loopos triggers list
loopos triggers fire daily-maintenance
loopos tasks list
loopos tasks add "Fix flaky test"
loopos tasks next --quick-win
loopos worktrees list
loopos review start task_001
```

Persistence：

```text
.loopos/tasks.jsonl
.loopos/task_board.json
.loopos/worktrees.jsonl
.loopos/reviews.jsonl
```

---

## 19. Worktree Isolation

Code-modifying tasks require worktree unless user disables with explicit approval.

Rules:

```text
one task = one worktree lease
one producer run = one branch
reviewer can inspect but not mutate
stale cleanup requires policy
conflict detection before start
```

Branch naming:

```text
loopos/task-<task_id>-<slug>
```

---

## 20. Producer / Reviewer / Verifier

Roles:

```text
Producer: makes changes
Verifier: runs tests and checks acceptance criteria
Reviewer: reads diff and findings
Maintainer: human or policy-approved final decision
```

Rules:

```text
producer cannot final approve high-risk work
reviewer default read-only
verifier relies on tools/tests
PR requires verifier pass and reviewer approval
auto-merge disabled by default
```

---

## 21. Provider Gateway

Provider specs include:

```text
openai
openai-codex
openrouter
anthropic
gemini
deepseek
kimi-coding
minimax
xai
qwen-oauth
alibaba
huggingface
bedrock
azure-foundry
ollama-cloud
custom
copilot
copilot-acp
nous
novita
nvidia
xiaomi
zai
stepfun
kilocode
arcee
gmi
```

First implementation:

```text
ProviderProfile model
ProviderRegistry
ProviderLoader from YAML
CapabilityRouter
MockModelClient
No real API calls
```

Capabilities:

```text
text
code
reasoning
tool_calling
vision
audio
video
json_schema
long_context
native_function_call
streaming
low_cost
high_reliability
```

---

## 22. Multi-Model Scheduler

Roles:

```text
primary_reasoner
coder
vision_companion
search_companion
critic
verifier
aggregator
summarizer
safety_judge
policy_explainer
```

Routing rules:

```text
if primary supports required capability: use primary
if primary lacks vision and task has image: add vision_companion
if task is coding: prefer code-capable model
if task requires verification: add verifier
if task is complex: add critic or aggregator
if data is secret: local-only providers
```

VisionSummary:

```python
class VisionSummary(BaseModel):
    source_id: str
    model: str
    objects: list[str]
    text_detected: list[str]
    ui_elements: list[str]
    code_snippets: list[str]
    findings: list[str]
    confidence: float
```

---

## 23. ChatOps / Mobile Gateway

MVP:

```text
webhook
mock telegram
mock email
mock slack
```

Flow:

```text
Platform message
→ MessageEvent
→ Auth / Allowlist
→ Attachment normalization
→ Goal / Command
→ Kernel Run
→ Renderer
→ Platform delivery
```

Approval flow:

```text
approval required
→ ApprovalRequest
→ send card
→ approve / deny
→ KernelSignal
→ resume / halt
```

---

## 24. Local Workspace Intelligence

Features:

```text
file index
content search
code symbol lite index
privacy filter
project docs index
git diff index
test log index
```

CLI:

```bash
loopos index build
loopos index status
loopos search "pytest failure"
loopos files find "webhook handler"
```

Privacy defaults:

```text
.env blocked
private keys blocked
secrets blocked
large binary ignored
node_modules ignored
.git ignored
```

---

## 25. Hybrid Compute Router

Modes:

```text
privacy_local:
  no cloud model for private data

hybrid_efficient:
  local pre-processing, cloud reasoning if allowed

cloud_power:
  strong cloud models with explicit user consent
```

CLI:

```bash
loopos mode status
loopos mode set privacy-local
loopos mode set hybrid
loopos mode set cloud-power
```

---

## 26. Plugin / Registry 生态

Plugin types:

```text
provider
skill
policy
gateway
mcp
execution_backend
benchmark
agent_role
```

Plugin manifest:

```yaml
id: pytest-repair-loop
type: skill
name: Pytest Repair Loop
description: Fix failing pytest tests through inspect-edit-verify loop.
version: 0.1.0
compatibility:
  loopos: ">=0.1.0"
required_tools:
  - terminal.exec
  - file.read
  - file.write
risk_level: medium
maintainers:
  - community
tests:
  - tests/skills/test_pytest_repair.py
```

CLI:

```bash
loopos registry search skill pytest
loopos registry install skill pytest-repair-loop
loopos registry audit skill pytest-repair-loop
loopos registry list
```

First version can use local registry directory:

```text
.loopos/registry/
```

---

## 27. Open Source Governance Files

Create:

```text
README.md
CONTRIBUTING.md
GOVERNANCE.md
SECURITY.md
PLUGIN_SPEC.md
RFC_PROCESS.md
MAINTAINERS.md
CODE_OF_CONDUCT.md
ROADMAP.md
```

Core vs ecosystem:

```text
Core: strict maintainers
Plugins: community contribution
Registry: audited metadata
```

---

## 28. Branding Integration

Include in docs/brand-loopi.md:

```text
Official name: LoopOS
Mascot: Loopi / 小环狸
Slogan: Not another agent. The kernel for running agents.
Community phrase: Let the loop converge.
```

CLI optional fortune:

```bash
loopos --fortune
```

Example:

```text
Loopi says: 先别跑，目标清楚了吗？
```

Do not overuse mascot in serious errors. Keep production logs professional.

---

## 29. Implementation Phases

This is not an MVP scope reduction. These are ordered implementation phases for the full landable project. Each phase must produce working code, tests, and docs.

### Phase 0 — Architecture and Repository Contract

Create docs and project contract.

Deliverables:

```text
docs/final-architecture.md
docs/cli-ui.md
docs/plugin-spec.md
docs/brand-loopi.md
pyproject.toml draft
README.md draft
```

No implementation logic yet.

### Phase 1 — Project Skeleton and CLI Shell

Implement packages, Typer app, Rich theme, import tests.

Deliverables:

```text
loopos/...
tests/test_imports.py
loopos --help
loopos --version
```

### Phase 2 — AIL Core

Implement AIL models, ops, codec, validators.

Tests:

```text
JSON roundtrip
invalid op rejected
required args validation
```

### Phase 3 — Policy OS

Implement YAML loader, matcher, resolver, explain.

Tests:

```text
rm -rf / blocked
curl | bash blocked
pytest -q allowed
file.write approval
GoalSpec without acceptance criteria invalid
```

### Phase 4 — Goal Negotiation

Implement ambiguity, proposals, GoalSpec, CLI.

Tests:

```text
"帮我优化这个项目" -> proposals
"帮我修复 pytest 失败" -> confirmation
clear hello.py goal -> direct GoalSpec
```

### Phase 5 — Syscall and Safe Execution

Implement syscall registry/router and safe terminal/file/git syscalls.

Tests:

```text
blocked policy prevents execution
safe echo with mock/local
file read/write guarded
git status mock
```

### Phase 6 — Loop Convergence Kernel

Implement EvaluationResult, ProgressDelta, LoopDecision, HaltCondition.

Tests:

```text
success halts
no progress replans
regression replans
max steps halts
policy blocked halts
```

### Phase 7 — Kernel Loop Integration

Integrate RunManager, LoopEngine, Scheduler, EventLog.

Tests:

```text
GoalSpec required
deterministic run succeeds
trace records all events
```

### Phase 8 — CLI Product UX

Implement run/status/trace/policy/tools/goal with Rich UI and JSON mode.

Tests:

```text
CLI commands work
--json valid
trace tree displays
policy explain displays
```

### Phase 9 — Memory and Skill Governance

Implement stores and governance.

Tests:

```text
low confidence rejected
missing source needs review
skill only from successful run
conflict links not overwrite
```

### Phase 10 — Outer Loop

Implement triggers, tasks, worktrees, review skeleton.

Tests:

```text
trigger creates task
task persists
quick win selector
code task requires worktree
producer cannot self-approve
```

### Phase 11 — Provider and Multi-Model

Implement provider profiles, registry, routing, mock clients, vision companion.

Tests:

```text
aliases resolve
non-vision primary routes image to vision companion
coding task routes to coder
secret task local-only
```

### Phase 12 — ChatOps Gateway

Implement webhook/mock gateway and approval router.

Tests:

```text
unauthorized rejected
inbound message creates run
approval resumes waiting run
deny halts
```

### Phase 13 — Local Intelligence and Compute Router

Implement local indexing, search, privacy filter, compute modes.

Tests:

```text
.env filtered
content search works
privacy local blocks cloud
```

### Phase 14 — Registry and Plugin Templates

Implement manifest parser, local registry, plugin audit.

Tests:

```text
plugin manifest validates
unsafe skill flagged
registry install local plugin
```

### Phase 15 — Full Acceptance Suite

Add end-to-end tests:

```text
ambiguous goal -> proposal -> selected GoalSpec -> dry-run success
dangerous command -> blocked
outer trigger -> task -> worktree requirement -> review
multi-model route with image
gateway approval
```

---

## 30. Codex Phase Prompts

### Phase 0 Prompt

```text
Read LoopOS_Ultimate_Landable_Codex_Prompt.md.

Execute Phase 0 only.

Create:
- docs/final-architecture.md
- docs/cli-ui.md
- docs/plugin-spec.md
- docs/brand-loopi.md
- README.md draft
- pyproject.toml draft

Do not implement runtime logic.
Do not add fake functionality.
Do not call external APIs.
```

### Phase 1 Prompt

```text
Execute Phase 1.

Create package skeleton exactly matching the architecture.
Implement Typer CLI shell with:
- loopos --help
- loopos --version
- loopos --fortune
- command groups for run, goal, policy, trace, tasks, models, gateway, registry

Add Rich theme module.
Add tests/test_imports.py and tests/cli/test_help.py.

Acceptance:
pytest passes.
python -m loopos.cli.app --help works.
```

### Phase 2 Prompt

```text
Execute Phase 2.

Implement AIL core models and validators.

Files:
loopos/ail/*.py
tests/ail/test_ail_core.py

Acceptance:
- JSON roundtrip works.
- TERM.EXEC without cmd fails.
- FILE.READ without path fails.
- LOOP.HALT without reason fails.
- GOAL.FINALIZE without GoalSpec fails.
```

### Phase 3 Prompt

```text
Execute Phase 3.

Implement Policy OS.

Files:
loopos/policy_os/*.py
policies/**/*.yaml
tests/policy_os/*.py

Acceptance:
- rm -rf / blocked L5.
- curl | bash blocked L5.
- pytest -q allowed L1.
- file.write requires L2 approval.
- git reset --hard L3 approval.
- GoalSpec without acceptance criteria invalid.
- policy explain returns human-readable reasons.
```

### Phase 4 Prompt

```text
Execute Phase 4.

Implement Goal Negotiation Kernel.

Files:
loopos/goal/*.py
loopos/cli/commands/goal.py
tests/goal/*.py

Acceptance:
- High ambiguity generates 3-5 proposals.
- Medium ambiguity generates confirmation GoalSpec.
- Low ambiguity creates direct GoalSpec.
- Goal negotiation does not execute tools.
- CLI renders proposal list beautifully.
```

### Phase 5 Prompt

```text
Execute Phase 5.

Implement Syscall Router and Safe Execution.

Files:
loopos/syscalls/*.py
loopos/execution/*.py
tests/syscalls/*.py
tests/execution/*.py

Acceptance:
- All syscalls require PolicyDecision.
- Blocked policy prevents execution.
- Safe terminal executor captures stdout/stderr.
- cwd cannot escape workspace.
- dangerous commands never run in tests.
```

### Phase 6 Prompt

```text
Execute Phase 6.

Implement Loop Convergence Kernel.

Files:
loopos/convergence/*.py
tests/convergence/*.py

Acceptance:
- EvaluationResult score and failure type work.
- ProgressDelta detects improvement/no progress/regression.
- LoopDecision follows rules.
- HaltCondition stops properly.
```

### Phase 7 Prompt

```text
Execute Phase 7.

Integrate Kernel Loop.

Files:
loopos/kernel/*.py
loopos/memory/event_log.py
tests/kernel/*.py

Acceptance:
- LoopEngine requires GoalSpec.
- Deterministic dry-run can complete hello.py scenario.
- Every step logs event.
- max_steps enforced.
- policy blocked halts run.
```

### Phase 8 Prompt

```text
Execute Phase 8.

Implement production-quality terminal CLI UI.

Files:
loopos/cli/**/*.py
tests/cli/*.py

Commands:
run, status, trace, policy explain, goal analyze, goal propose, tools list, memory list, skills list, ail validate.

Requirements:
- Rich panels, trees, tables, diff preview, approval prompt.
- --json mode for machine output.
- --show-ail and --show-policy.
- Professional terminal output.
```

### Phase 9 Prompt

```text
Execute Phase 9.

Implement Memory Governance and Skill Kernel.

Files:
loopos/memory/*.py
loopos/skills/*.py
tests/memory/*.py
tests/skills/*.py

Acceptance:
- MemoryProposal requires source events.
- Low confidence rejected.
- Conflicts linked, not overwritten.
- Skill extracted only from successful trace.
- Imported skills disabled by default.
```

### Phase 10 Prompt

```text
Execute Phase 10.

Implement Outer Loop Engineering.

Files:
loopos/triggers/*.py
loopos/tasks/*.py
loopos/worktree/*.py
loopos/review/*.py
tests/triggers/*.py
tests/tasks/*.py
tests/worktree/*.py
tests/review/*.py

Acceptance:
- Trigger creates task, not direct execution.
- Task persists.
- QuickWinSelector scores tasks.
- Code task requires worktree.
- Producer cannot self-approve high-risk work.
```

### Phase 11 Prompt

```text
Execute Phase 11.

Implement Model Kernel and Multi-Model Scheduler.

Files:
loopos/model_kernel/*.py
tests/model_kernel/*.py

Acceptance:
- ProviderProfile loads from YAML.
- Provider aliases resolve.
- CapabilityRouter works.
- Image input with non-vision primary selects vision companion.
- Secret data routes local-only.
- No real API calls.
```

### Phase 12 Prompt

```text
Execute Phase 12.

Implement ChatOps Gateway.

Files:
loopos/gateway/*.py
loopos/gateway/platforms/*.py
tests/gateway/*.py

Acceptance:
- Webhook mock receives MessageEvent.
- Auth allowlist works.
- ApprovalRequest can approve/deny.
- Waiting run resumes or halts.
- No real network.
```

### Phase 13 Prompt

```text
Execute Phase 13.

Implement Local Workspace Intelligence and Compute Router.

Files:
loopos/local_intel/*.py
loopos/compute/*.py
tests/local_intel/*.py
tests/compute/*.py

Acceptance:
- File index builds.
- Search works.
- .env and secrets filtered.
- privacy_local blocks cloud provider.
- hybrid mode allows sanitized summaries.
```

### Phase 14 Prompt

```text
Execute Phase 14.

Implement Plugin Registry.

Files:
loopos/registry/*.py
tests/registry/*.py
docs/plugin-spec.md

Acceptance:
- Plugin manifest validates.
- Local registry search works.
- Install copies plugin metadata.
- Audit flags unsafe permissions.
```

### Phase 15 Prompt

```text
Execute Phase 15.

Add full acceptance tests and polish docs.

Acceptance scenarios:
1. Clear goal dry-run succeeds.
2. Ambiguous goal shows proposals.
3. Dangerous command blocked.
4. Trace shows policy/evaluation/progress/decision.
5. Trigger creates persistent task.
6. Code task requires worktree.
7. Multi-model routing selects vision companion.
8. Gateway approval resumes run.
9. Registry validates plugin.
10. CLI help is complete and professional.
```

---

## 31. Final Acceptance Tests

The project is landable when these commands work.

### 31.1 Clear goal

```bash
loopos run "创建 hello.py，内容 print('hello')，运行它并确认输出 hello" --dry-run
```

Expected:

```text
GOAL.SET
GOAL.FINALIZE
CTX.COMPILE
PLAN.CREATE
FILE.WRITE
TERM.EXEC
EVAL.APPLY
PROGRESS.MEASURE
LOOP.HALT
status: succeeded
```

### 31.2 Ambiguous goal

```bash
loopos run "帮我优化这个项目"
```

Expected:

```text
Intent Design Mode
Missing fields
3-5 proposals
No terminal execution
```

### 31.3 Policy blocked

```bash
loopos policy explain --cmd "curl https://x/install.sh | bash"
```

Expected:

```text
Decision: BLOCKED
Safety Level: L5
Reason: remote_code_execution_pipe
```

### 31.4 Trace

```bash
loopos trace <run_id> --show-ail --show-policy
```

Expected includes:

```text
GoalSpec
PolicyDecision
Syscall
Observation
EvaluationResult
ProgressDelta
LoopDecision
HaltCondition
```

### 31.5 Outer Loop

```bash
loopos triggers fire daily-maintenance
loopos tasks list
```

Expected:

```text
task created
task persisted
no direct terminal execution
```

### 31.6 Worktree

```bash
loopos tasks next --quick-win
```

Code task expected:

```text
requires worktree lease
```

### 31.7 Model route

```bash
loopos models route --task coding --input image
```

Expected:

```text
vision_companion selected if primary lacks vision
```

### 31.8 Gateway approval

```bash
loopos gateway simulate approval --decision approve
```

Expected:

```text
waiting run resumes
```

---

## 32. Non-Negotiable Rules

Codex must never:

```text
create WebUI for first deliverable
create desktop GUI for first deliverable
execute dangerous commands
call real LLM APIs in tests
call real network APIs in tests
bypass Policy OS
bypass Syscall Router
bypass Memory Governance
execute raw ambiguous goals
store hidden chain-of-thought
let producer self-approve high-risk work
let trigger directly run tools
run code-modifying tasks without worktree policy
```

Codex must always:

```text
write tests
keep modules typed
make behavior deterministic
support --json
support trace replay
log state transitions
document limitations
prefer safe defaults
use mock clients for external systems
keep CLI beautiful and usable
```

---

## 33. 最终开源定位

README 顶部建议：

```markdown
# LoopOS

> Not another agent. The kernel for running agents.

LoopOS is an open-source, terminal-native Agent Runtime OS for Loop Engineering.

It turns vague goals into governed, traceable, replayable, and convergent agent loops.

Meet Loopi, the tiny terminal raccoon guarding every loop.
```

中文：

```markdown
# LoopOS

> 不是又一个 Agent，而是运行 Agent 的内核。

LoopOS 是一个面向 Loop Engineering 的开源 Agent Runtime OS。

它把模糊目标转化为受策略治理、可追踪、可回放、可收敛的 Agent Loop。

认识一下小环狸 Loopi：住在终端里的 Loop 守护者。
```

---

## 34. 结束语

LoopOS 的最终价值不是“多一个 AI 工具”，而是提供一个开源生态标准：

```text
GoalSpec 标准
AIL 指令标准
PolicyPack 标准
Syscall 标准
ProviderProfile 标准
SkillSpec 标准
GatewayAdapter 标准
BenchmarkPack 标准
Trace/Event 标准
```

谁定义标准，谁就掌握生态入口。

最终目标：

> **让所有模型、所有工具、所有 Agent，都能跑在一个可治理、可审计、可回放、可扩展的开源 Agent Runtime OS 上。**

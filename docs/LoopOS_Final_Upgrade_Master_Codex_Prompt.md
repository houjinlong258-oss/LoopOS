# LoopOS Final Upgrade Master Codex Prompt

版本：v1.0 Final  
用途：给 Codex / Claude Code / OpenHands / 自建 coding agent 使用的最终总控提示词  
目标：把 LoopOS 构建为 **Terminal-native + Kernel-level + MCP/Syscall + Policy OS + Goal Negotiation + Loop Engineering + Outer Loop + Multi-Model + ChatOps + Memory Governance + Skill Learning** 的 Agent Operating System  
推荐文件名：`LoopOS_Final_Upgrade_Master_Codex_Prompt.md`

---

## 0. 最终定位

你正在构建的不是 chatbot。  
你正在构建的不是普通 CLI agent。  
你正在构建的不是简单 workflow orchestrator。  
你正在构建的不是 Hermes / Claude Code / Codex CLI / OpenHands 的复制品。

你正在构建：

> **LoopOS：一个运行在终端中的 AI Agent Operating System Kernel。**

它应该具备：

```text
1. Terminal-native CLI / REPL
2. AI-ISA / AIL 内部结构化语言
3. Policy OS 安全与行为治理内核
4. MCP / Syscall 工具调用层
5. Goal Negotiation Kernel
6. Loop Convergence Kernel
7. Outer Loop Engineering Kernel
8. Memory Governance Kernel
9. Skill Learning / Skill Cache
10. Multi-Model Scheduler
11. Multimodal Companion Model
12. Provider Gateway
13. ChatOps / Mobile App Gateway
14. Worktree Isolation
15. Producer / Reviewer / Verifier 分离
16. Trace Replay / Audit Log
17. Execution Backend Abstraction
18. Project Skill Onboarding
```

最终系统不应该是：

```text
用户输入一句话 → LLM 自由发挥 → 直接执行
```

而应该是：

```text
Raw User Goal
  ↓
Goal Negotiation Kernel
  ↓
Final GoalSpec
  ↓
Policy OS
  ↓
Context Compiler
  ↓
Kernel Scheduler
  ↓
AIL Instruction
  ↓
Syscall / MCP Tool Call
  ↓
Observation
  ↓
Evaluation Kernel
  ↓
Progress Tracker
  ↓
Loop Decision
  ↓
Memory Governance / Skill Learning
  ↓
Trace / Audit
  ↓
Renderer
```

对于持续运行的外循环，则是：

```text
Trigger
  ↓
Task Queue
  ↓
Goal Negotiation
  ↓
GoalSpec
  ↓
Worktree Isolation
  ↓
Producer Agent
  ↓
Verifier / Reviewer Agent
  ↓
PR / Patch / Report
  ↓
Persistent State
  ↓
Memory Governance / Skill Learning
  ↓
Next Trigger
```

---

# 1. 给 Codex 的总控身份

复制以下内容作为 Codex 的系统级任务说明：

```text
You are the chief systems engineer building LoopOS.

LoopOS is a terminal-native AI Agent Operating System Kernel.

It is NOT a chatbot.
It is NOT a simple CLI wrapper.
It is NOT a web app.
It is NOT a free-form autonomous agent.
It is NOT a prompt-only agent.

LoopOS is a deterministic, policy-governed, syscall-based, memory-governed, traceable, replayable AI runtime.

Your job is to implement LoopOS step by step with production-grade architecture, strict module boundaries, tests, and terminal-native CLI UX.

Core principles:
1. Raw user goals do not directly enter execution.
2. Ambiguous goals go through Goal Negotiation.
3. Only Final GoalSpec enters LoopEngine.
4. All internal actions use AIL / AI-ISA structured instructions.
5. All external actions are syscalls or MCP tool calls.
6. All syscalls pass Policy OS.
7. All terminal commands pass Permission Policy.
8. All long-term memory writes pass Memory Governance.
9. All successful traces may become governed skills.
10. All actions are logged and replayable.
11. All risky work requires independent review or human approval.
12. CLI is terminal-native. No WebUI for MVP.
13. Tests must not call real LLMs, real networks, or dangerous commands.

Implement in phases. Never implement everything at once. Start with docs and skeleton, then typed models, then deterministic MVP, then integrations.
```

---

# 2. LoopOS 的 OS 类比

LoopOS 应按照操作系统思路设计。

| OS 概念 | LoopOS 对应物 |
|---|---|
| Kernel | Loop Engine + Policy OS + Scheduler |
| Process | Agent Run |
| Thread | Agent Step / Subtask / Child Agent |
| Syscall | MCP ToolCall / Terminal ToolCall |
| Scheduler | Loop Scheduler / Multi-Model Scheduler / Outer Loop Scheduler |
| Memory Manager | Context Compiler + Memory Governance |
| Filesystem | Event Log + State Store + Memory Store |
| Device Driver | Tool Adapter / MCP Adapter / Gateway Adapter |
| Security Module | Policy OS + Permission Policy |
| Shell | CLI / REPL / ChatOps Gateway |
| Kernel Trace | Event Log / Trace Replay |
| Page Cache | Skill Cache |
| Signals | Approval / Cancel / Repair / Replan |
| Init System | Boot Sequence |
| Audit Log | Policy Audit + Execution Trace |
| User Space | Skills / Tools / Providers / Connectors |
| Daemon | Trigger Kernel / ChatOps Gateway / Scheduler |

核心目标：

```text
Every action is a syscall.
Every syscall is policy-checked.
Every state transition is logged.
Every memory write is governed.
Every loop is measurable.
Every run is replayable.
Every ambiguous task is clarified before execution.
Every outer-loop task is persisted.
Every code-modifying task is isolated.
Every high-risk result is independently reviewed.
```

---

# 3. Loop Engineering 的最终定义

Loop Engineering 不是简单 while-loop。  
Loop Engineering 是设计一个能持续运行、持续收敛、持续审查、持续记忆的系统。

它包含三层 loop：

## 3.1 Goal Negotiation Loop

解决：

```text
用户目标模糊、不完整、没有验收标准。
```

流程：

```text
Raw Goal
  → Analyze
  → Detect Ambiguity
  → Generate 3-5 Proposals
  → User Select/Edit/Merge
  → Final GoalSpec
```

## 3.2 Inner Convergence Loop

解决：

```text
单个 GoalSpec 如何可验证地完成。
```

流程：

```text
Plan
  → Execute
  → Observe
  → Evaluate
  → Measure Progress
  → Continue / Repair / Replan / Ask / Halt
```

核心：

```text
Convergence = Evaluation + Progress + Halt
```

## 3.3 Outer Loop Engineering

解决：

```text
系统如何持续运转，而不是只完成一次任务。
```

流程：

```text
Trigger
  → Task Queue
  → Worktree
  → Producer Agent
  → Verifier
  → Reviewer
  → PR / Report
  → Persistent State
  → Next Loop
```

---

# 4. 总体架构图

```text
┌───────────────────────────────────────────────────────────────┐
│                        LoopOS CLI / REPL                      │
│  run / status / trace / policy / goal / tasks / review        │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                      ChatOps / Mobile Gateway                  │
│ Telegram / Slack / Discord / WhatsApp / Email / Webhook       │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                         Trigger Kernel                        │
│ cron / webhook / issue / git / CI / chat / continuous goals   │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                    Task Queue / Persistent Board               │
│ backlog / ready / running / review / done / failed / blocked  │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                    Goal Negotiation Kernel                     │
│ ambiguity detection / proposals / selection / GoalSpec         │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                            Policy OS                          │
│ safety / terminal / tools / memory / review / gateway / goal   │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                         Kernel Core                           │
│ RunManager / Scheduler / StateMachine / TransitionEngine       │
└───────────────┬───────────────┬────────────────┬──────────────┘
                │               │                │
┌───────────────▼──────┐ ┌──────▼────────┐ ┌─────▼──────────────┐
│ Context Compiler     │ │ Model Kernel  │ │ Trace/Event Kernel │
│ memory + skills      │ │ provider route│ │ event log + replay │
└───────────────┬──────┘ └──────┬────────┘ └─────┬──────────────┘
                │               │                │
┌───────────────▼───────────────▼────────────────▼──────────────┐
│                           AIL / AI-ISA                         │
│ Goal | State | Instruction | Syscall | Observation | Eval      │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                         Syscall / MCP Layer                    │
│ terminal | file | git | browser | provider | gateway | API     │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                       Execution Runtime                         │
│ local | docker | ssh | modal | daytona | openhands | sandbox   │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                    Evaluation / Progress / Decision             │
│ score | delta | regression | repair | replan | halt             │
└───────────────────────────────┬────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────┐
│                       Memory + Skill Kernel                     │
│ event-sourced memory | governance | skill extraction            │
└────────────────────────────────────────────────────────────────┘
```

---

# 5. 目标仓库结构

Codex 应按以下结构创建或重构项目。

```text
loopos/
  __init__.py

  cli/
    __init__.py
    app.py
    repl.py
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
    renderers/
      panels.py
      tables.py
      trees.py
      json_output.py
      terminal_theme.py
      goal_renderer.py
      trace_renderer.py

  ail/
    __init__.py
    base.py
    ops.py
    goal.py
    state.py
    instruction.py
    observation.py
    evaluation.py
    event.py
    memory.py
    skill.py
    preference.py
    render.py
    syscall.py
    codec.py
    validators.py

  kernel/
    __init__.py
    boot.py
    run_manager.py
    scheduler.py
    process.py
    step.py
    state_machine.py
    transition.py
    loop_engine.py
    signals.py
    errors.py

  goal/
    __init__.py
    ambiguity.py
    proposal.py
    negotiation.py
    goal_spec.py
    clarifier.py
    templates.py
    cli_renderer.py

  convergence/
    __init__.py
    evaluation.py
    progress.py
    decision.py
    halt.py
    repair.py
    replan.py
    metrics.py

  triggers/
    __init__.py
    base.py
    cron.py
    webhook.py
    git_event.py
    issue_event.py
    chat_event.py
    continuous.py
    registry.py

  tasks/
    __init__.py
    task.py
    queue.py
    board.py
    state.py
    selector.py
    quick_win.py
    persistence.py

  worktree/
    __init__.py
    manager.py
    lease.py
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

  policy_os/
    __init__.py
    models.py
    loader.py
    registry.py
    matcher.py
    conflict_resolver.py
    engine.py
    compiler.py
    audit.py

  context/
    __init__.py
    compiler.py
    budget.py
    relevance.py
    compression.py

  syscalls/
    __init__.py
    types.py
    registry.py
    router.py
    result.py

  mcp/
    __init__.py
    types.py
    adapters.py
    client.py
    registry.py

  execution/
    __init__.py
    terminal.py
    permissions.py
    sandbox.py
    workspace.py
    backends/
      __init__.py
      base.py
      local.py
      docker.py
      ssh.py
      modal.py
      daytona.py
      openhands.py

  memory/
    __init__.py
    event_log.py
    state_store.py
    belief_store.py
    skill_store.py
    preference_store.py
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
    skill_loader.py
    onboarding.py
    skill_policy.py

  model_kernel/
    __init__.py
    provider_profile.py
    provider_registry.py
    provider_loader.py
    capability.py
    router.py
    client.py
    multi_model.py
    vision_companion.py
    aggregator.py
    verifier.py

  gateway/
    __init__.py
    base.py
    message.py
    session_router.py
    attachment_router.py
    approval_router.py
    delivery_router.py
    platforms/
      telegram.py
      discord.py
      slack.py
      whatsapp_cloud.py
      email.py
      webhook.py

  connectors/
    __init__.py
    base.py
    github.py
    gitlab.py
    linear.py
    jira.py
    slack.py
    telegram.py
    staging_api.py
    ci.py

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

  integrations/
    __init__.py
    openhands_adapter.py
    langgraph_adapter.py
    letta_adapter.py
    zep_adapter.py
    projectmem_adapter.py
    hermes_adapter_notes.py

  eval/
    __init__.py
    runner.py
    metrics.py
    tasks.py

policies/
  core/
    behavior.yaml
    honesty.yaml
    goal_negotiation.yaml
    outer_loop.yaml
  safety/
    terminal_safety.yaml
    prompt_injection.yaml
    harmful_content.yaml
  tools/
    tool_routing.yaml
    mcp_policy.yaml
    file_policy.yaml
    git_policy.yaml
    worktree_policy.yaml
  memory/
    memory_applicability.yaml
    memory_governance.yaml
    user_preference.yaml
  renderer/
    renderer_style.yaml
    cli_output.yaml
  coding/
    review_separation.yaml
    code_edit_policy.yaml
    git_policy.yaml
  optimization/
    context_budget.yaml
    loop_convergence.yaml

tests/
  ail/
  kernel/
  goal/
  convergence/
  triggers/
  tasks/
  worktree/
  review/
  policy_os/
  context/
  syscalls/
  execution/
  memory/
  skills/
  model_kernel/
  gateway/
  connectors/
  responsibility/
  agents/
  cli/
  integrations/
  eval/

docs/
  architecture-kernel.md
  goal-negotiation.md
  loop-convergence.md
  outer-loop-engineering.md
  ail.md
  policy-os.md
  syscalls.md
  memory-governance.md
  cli-ui.md
  provider-gateway.md
  chatops-gateway.md
  multi-model-scheduler.md
  worktree-isolation.md
  review-separation.md
  safety.md
  benchmarks.md
```

---

# 6. AIL / AI-ISA 指令集

LoopOS 内部执行必须使用结构化 AIL，不使用长自然语言作为内部协议。

## 6.1 基础指令

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
```

## 6.2 Outer Loop 指令

```text
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

## 6.3 AILInstruction Schema

```json
{
  "id": "ins_001",
  "run_id": "run_001",
  "step": 1,
  "op": "TERM.EXEC",
  "args": {
    "cmd": "pytest -q",
    "cwd": "."
  },
  "reason": {
    "code": "VERIFY_TESTS",
    "evidence": ["code_changed", "tests_not_run"],
    "confidence": 0.88
  },
  "safety": {
    "risk": "low",
    "requires_approval": false
  },
  "expect": {
    "success": ["tests_pass"],
    "fail": ["tests_fail", "timeout"],
    "timeout_seconds": 60
  },
  "policy": {
    "decision_id": null,
    "matched_rules": []
  }
}
```

约束：

```text
TERM.EXEC requires args.cmd.
TOOL.CALL requires args.tool.
FILE.READ requires args.path.
FILE.WRITE requires args.path and args.content or patch.
LOOP.HALT requires reason.
GOAL.FINALIZE requires GoalSpec.
GOAL.* negotiation ops cannot execute tools.
```

---

# 7. Goal Negotiation Kernel

## 7.1 目标

用户给出的目标如果模糊、宽泛、风险高、缺少验收标准，则不能直接执行。

正确流程：

```text
Raw Goal
  ↓
AmbiguityReport
  ↓
GoalProposals
  ↓
User Selection / Edit / Merge
  ↓
GoalSpec
  ↓
Policy OS
  ↓
LoopEngine
```

## 7.2 AmbiguityReport

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

规则：

```text
ambiguity_score >= 0.6:
  enter full negotiation

0.3 <= ambiguity_score < 0.6:
  generate inferred GoalSpec and ask confirmation

ambiguity_score < 0.3:
  direct GoalSpec
```

模糊因素：

```text
missing_scope
missing_acceptance_criteria
missing_output_format
missing_constraints
missing_priority
missing_target
broad_verb
high_risk_without_boundary
multi_possible_interpretations
```

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

## 7.3 GoalProposal

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

规则：

```text
模糊目标默认生成 3-5 个 proposals。
每个 proposal 必须有 scope、deliverables、acceptance_criteria。
每个 proposal 必须有 risk_level。
至少一个 proposal 是 low-risk read-only 方案。
至少一个 proposal 是 execution-oriented 方案。
如果目标涉及代码项目，至少一个 proposal 是 MVP implementation 方案。
```

## 7.4 GoalSpec

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

约束：

```text
GoalSpec.acceptance_criteria cannot be empty.
GoalSpec.final_goal cannot be empty.
GoalSpec.scope cannot be empty.
GoalSpec must pass Policy OS before LoopEngine starts.
```

## 7.5 CLI 行为

```bash
loopos goal analyze "帮我优化这个项目"
loopos goal propose "帮我优化这个项目"
loopos run "帮我优化这个项目" --negotiate
loopos run "帮我优化这个项目" --no-negotiate
```

默认：

```text
loopos run "<goal>"
  → auto ambiguity detection
  → high ambiguity: show proposals
  → medium ambiguity: ask confirmation
  → low ambiguity: execute
```

---

# 8. Loop Convergence Kernel

Loop Engineering 的核心不是循环，而是收敛。

```text
Convergence = Evaluation + Progress + Halt
```

每一轮必须产生：

```text
Observation
EvaluationResult
ProgressDelta
LoopDecision
```

## 8.1 EvaluationResult

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

常见 failure_type：

```text
tests_failed
command_failed
policy_blocked
approval_denied
missing_file
invalid_output
tool_unavailable
ambiguous_goal
no_progress
regression
timeout
max_steps
```

## 8.2 ProgressDelta

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

规则：

```text
delta > 0.05 -> improved
abs(delta) <= 0.05 -> no meaningful progress
delta < -0.05 -> regression_detected
same failure_type repeated >= 2 -> repeated_failure_count increment
same command repeated >= 2 without improvement -> repeated_action_count increment
```

## 8.3 LoopDecision

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

决策规则：

```text
if policy blocked:
    halt_blocked

if approval required:
    wait_approval

if goal_satisfied:
    halt_success

if approval denied:
    halt_failure

if ambiguity detected during execution:
    ask_user

if regression_detected:
    replan

if no_progress_count >= 2:
    replan

if repeated_action_count >= 2:
    replan

if max_steps_reached:
    halt_failure

if evaluation.repairable:
    repair

else:
    replan or halt_failure
```

## 8.4 HaltCondition

```python
class HaltCondition(BaseModel):
    name: str
    matched: bool
    reason: str
    severity: Literal["success", "failure", "blocked"]
```

必须支持：

```text
acceptance_criteria_met
policy_blocked
user_denied
max_steps_reached
no_progress_limit
repeated_failure_limit
timeout
unrecoverable_error
missing_required_tool
```

---

# 9. Outer Loop Engineering Kernel

Outer Loop 让 LoopOS 持续运转。

## 9.1 TriggerEvent

```python
class TriggerEvent(BaseModel):
    trigger_id: str
    source: Literal[
        "cron",
        "webhook",
        "git_event",
        "issue_event",
        "chat",
        "ci",
        "continuous"
    ]
    event_type: str
    payload: dict[str, Any]
    received_at: datetime
    dedupe_key: str | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
```

MVP trigger：

```text
manual CLI
cron
webhook
local issue file
CI failure file
```

后续：

```text
GitHub issue
GitLab issue
Linear
Jira
Slack / Telegram command
staging API monitor
test failure monitor
```

规则：

```text
Trigger 只创建任务，不直接执行危险动作。
TriggerEvent 必须进入 Task Intake。
所有外部 webhook 必须认证。
重复事件必须 dedupe。
```

## 9.2 LoopTask

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

MVP persistence：

```text
.loopos/tasks.jsonl
.loopos/task_board.json
```

后续：

```text
SQLite
GitHub Issues
GitLab Issues
Linear
Jira
Todo.md
```

## 9.3 QuickWinScore

```python
class QuickWinScore(BaseModel):
    task_id: str
    score: float
    reason_codes: list[str]
    estimated_effort: Literal["small", "medium", "large"]
    risk_level: Literal["low", "medium", "high"]
```

Quick Win 规则：

```text
small scope
clear acceptance criteria
low risk
existing failing test
localized file change
no external dependency
no architecture-wide refactor
```

## 9.4 WorktreeLease

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

规则：

```text
code-modifying task must have isolated worktree
one task = one worktree lease
one producer run = one branch
reviewer can inspect but not mutate producer worktree unless explicitly allowed
stale worktree cleanup requires policy approval
```

## 9.5 Producer / Reviewer / Verifier 分离

角色：

```text
producer:
  生成方案、改代码、创建 patch

reviewer:
  审查 diff、检查需求、找 bug

verifier:
  运行测试、执行验收标准

maintainer:
  人类最终决策者或自动策略允许的合并者
```

ReviewRun：

```python
class ReviewRun(BaseModel):
    review_id: str
    task_id: str
    producer_run_id: str
    reviewer_model: str | None
    status: Literal["pending", "approved", "changes_requested", "rejected"]
    findings: list[str]
    required_changes: list[str]
    evidence: list[str]
```

规则：

```text
Producer cannot self-approve high-risk work.
Reviewer should use a separate model or separate context where possible.
Verifier should rely on tests, static checks, policy checks, and acceptance criteria.
PR is created only if review and verification pass.
Human approval required for high-risk changes.
```

---

# 10. Policy OS

Policy OS 是不可绕过的内核安全层。

## 10.1 PolicyContext

```python
class PolicyContext(BaseModel):
    phase: str
    task: dict[str, Any] = {}
    state: dict[str, Any] = {}
    instruction: dict[str, Any] = {}
    syscall: dict[str, Any] = {}
    memory: dict[str, Any] = {}
    runtime: dict[str, Any] = {}
```

## 10.2 PolicyDecision

```python
class PolicyDecision(BaseModel):
    decision_id: str
    allowed: bool
    risk: Literal["low", "medium", "high", "blocked"]
    requires_approval: bool
    reason_codes: list[str]
    matched_rules: list[str]
    constraints: dict[str, Any]
    renderer_hints: dict[str, Any]
```

## 10.3 硬规则

```text
blocked -> never execute
high -> explicit approval
medium -> --yes or approval
low -> auto execute
```

## 10.4 危险命令阻止

```text
rm -rf /
curl | bash
wget | sh
mkfs
dd if=
sudo without approval
reading private keys
git reset --hard without approval
git clean -fd without approval
chmod -R 777
kill -9 -1
```

## 10.5 新增 Policy Phase

```text
GOAL.NEGOTIATION
GOAL.FINALIZE
LOOP.DECISION
EVAL.RESULT
PROGRESS.DELTA

TRIGGER.RECEIVE
TASK.CREATE
TASK.SELECT
WORKTREE.CREATE
PRODUCER.RUN
REVIEW.START
REVIEW.ACCEPT
PR.CREATE
PR.MERGE
STATE.UPDATE
```

## 10.6 新增规则

```text
1. Goal negotiation cannot call terminal/syscalls.
2. No execution without GoalSpec.
3. GoalSpec without acceptance criteria is invalid.
4. High-risk GoalSpec requires approval.
5. Loop decision cannot continue after halt condition.
6. Trigger cannot execute tools directly.
7. Task without acceptance criteria cannot be selected for autonomous execution.
8. Code-modifying task requires worktree.
9. Producer cannot self-approve high-risk work.
10. PR merge requires independent review.
11. Auto-merge disabled by default.
12. Repeated failed task should be deferred or escalated.
13. Human approval required for production/staging mutation.
```

---

# 11. Syscall / MCP Layer

所有外部动作都是 syscall。

## 11.1 Syscall Schema

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

## 11.2 MVP Syscalls

```text
terminal.exec
file.read
file.write
git.status
git.diff
```

## 11.3 Future Syscalls

```text
browser.search
api.call
db.query
github.issue
gitlab.issue
linear.task
calendar.create
email.draft
gateway.send_message
openhands.exec
provider.chat
provider.vision
provider.embed
```

## 11.4 规则

```text
validate input
check policy
execute adapter
normalize result
emit observation
append event
```

---

# 12. Model Kernel / Hermes 能力吸收

Hermes 的价值不是直接复制 runtime，而是吸收：

```text
Provider 插件化
Platform Gateway
Skills 生态
子 agent 并行
MoA 聚合
多模态降级路由
执行后端抽象
Cron + 消息投递
Approval UX
上下文压缩
```

LoopOS 应内核化这些能力。

## 12.1 ProviderProfile

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

## 12.2 Capabilities

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
native_reasoning
streaming
low_cost
high_reliability
```

## 12.3 Providers to Support

LoopOS 应支持 Hermes 支持的 provider 范围，并把 OpenAI 做成一等 provider。

```text
openai
openai-responses
openai-chat-completions
openai-codex

openrouter
nous
novita
nvidia
xiaomi
zai
kimi-coding
kimi-coding-cn
minimax
minimax-cn
minimax-oauth
huggingface
gemini
google-gemini-cli
anthropic
deepseek
alibaba
alibaba-coding-plan
qwen-oauth
stepfun
xai
copilot
copilot-acp
opencode-zen
opencode-go
kilocode
arcee
gmi
bedrock
azure-foundry
ollama-cloud
custom
```

## 12.4 Multi-Model Scheduler

角色：

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

MultiModelPlan：

```python
class MultiModelPlan(BaseModel):
    primary_model: str
    companion_models: list[str]
    verifier_model: str | None
    aggregator_model: str | None
    routing_reason: list[str]
```

规则：

```text
1. If primary model supports required capability, use primary.
2. If primary lacks vision and task has images, route image to vision_companion.
3. Vision companion outputs structured VisionSummary.
4. Primary model consumes VisionSummary, not raw image.
5. If task is coding, prefer code-capable model.
6. If task needs verification, use verifier model or tool-based verifier.
7. If multiple models are requested, use aggregator.
```

## 12.5 VisionSummary

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

# 13. ChatOps / Mobile Gateway

LoopOS 需要支持手机聊天 app 操作。

## 13.1 Gateway Flow

```text
Chat Platform Message
  → Gateway MessageEvent
  → Auth / Allowlist
  → Attachment Normalizer
  → AILGoal
  → Kernel Run
  → Renderer
  → Platform Formatter
  → Send Message
```

## 13.2 MessageEvent

```python
class MessageEvent(BaseModel):
    platform: str
    chat_id: str
    user_id: str
    text: str | None
    attachments: list[dict[str, Any]]
    message_id: str
    thread_id: str | None
    timestamp: datetime
```

## 13.3 GatewaySession

```python
class GatewaySession(BaseModel):
    session_id: str
    platform: str
    chat_id: str
    user_id: str
    current_run_id: str | None
```

## 13.4 BasePlatformAdapter

```python
class BasePlatformAdapter:
    def connect(self): ...
    def disconnect(self): ...
    def send_text(self, chat_id: str, text: str): ...
    def send_markdown(self, chat_id: str, markdown: str): ...
    def send_file(self, chat_id: str, path: str): ...
    def send_image(self, chat_id: str, path: str): ...
    def send_typing(self, chat_id: str): ...
    def send_approval(self, request): ...
```

## 13.5 Platforms

MVP：

```text
webhook
telegram
email
slack
discord
whatsapp_cloud
```

后续：

```text
WhatsApp
Signal
Matrix
Mattermost
SMS
DingTalk
Feishu
WeCom
Weixin
QQBot
iMessage / BlueBubbles / Photon
Google Chat
Microsoft Teams
LINE
IRC
ntfy
SimpleX
Home Assistant
```

## 13.6 Mobile Approval

危险 syscall 应能在手机 app 中审批：

```text
ApprovalRequest
  → send_approval
  → Approve / Deny
  → KernelSignal
  → resume waiting run
```

ApprovalRequest：

```python
class ApprovalRequest(BaseModel):
    approval_id: str
    run_id: str
    step_id: str
    command: str | None
    risk: Literal["medium", "high"]
    reason: str
    expires_at: datetime | None
```

---

# 14. Memory Governance

长期记忆不能直接写入。

```text
MemoryProposal
  → MemoryGovernor
  → GovernanceDecision
  → Store
```

## 14.1 MemoryProposal

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

## 14.2 Governance Rules

```text
confidence < 0.4 -> reject
no source events -> needs_review
duplicate -> dedupe
conflict -> conflict link, not overwrite
preference without context -> reject
high-impact memory -> needs_review
one-time choice is not global preference
unconfirmed proposal is not active memory
```

---

# 15. Skill Kernel

Skill 是成功轨迹的结构化压缩，不是 prompt dump。

## 15.1 SkillSpec

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

规则：

```text
imported skills default enabled=false
dangerous commands require review
skills cannot bypass Policy OS
skill text is data, not system prompt
skill execution emits AIL instructions
duplicate skill updates stats
skill commit goes through governance
```

---

# 16. Execution Backends

终端执行应支持多后端。

```text
local
docker
ssh
singularity
modal
daytona
openhands
```

接口：

```python
class ExecutionBackend:
    def start(self): ...
    def exec(self, cmd: str, cwd: str, timeout: int): ...
    def read_file(self, path: str): ...
    def write_file(self, path: str, content: str): ...
    def sync(self): ...
    def stop(self): ...
```

MVP：

```text
local
mock
```

Alpha：

```text
docker
openhands
```

Beta：

```text
ssh
modal
daytona
```

---

# 17. CLI / Terminal UI

CLI 是主要入口，不是 GUI。

## 17.1 Commands

```bash
loopos run "<goal>"
loopos
loopos status <run_id>
loopos trace <run_id>
loopos step replay <run_id> <step>

loopos goal analyze "<goal>"
loopos goal propose "<goal>"

loopos policy explain --cmd "<cmd>"
loopos tools list
loopos memory list
loopos skills list
loopos ail validate <file>

loopos triggers list
loopos triggers fire <name>
loopos tasks list
loopos tasks next --quick-win
loopos worktrees list
loopos review start <task_id>
loopos accountability report

loopos models list
loopos models inspect <provider>
loopos models route --task coding

loopos gateway serve --platform webhook
```

## 17.2 Run Output

```text
LoopOS v0.1

Run ID: run_01HZM9
Goal: 修复当前 repo 的 pytest 失败
Workspace: /Users/dev/project
Mode: guarded
Max Steps: 20

[1/20] GOAL.SET
  ✓ goal parsed

[2/20] CTX.COMPILE
  ✓ context compiled
  memories: 3  skills: 2  tools: 5  policies: 7

[3/20] PLAN.CREATE
  ✓ plan generated
  next: run tests

[4/20] TERM.EXEC
  $ pytest -q

  ✗ failed
  2 failed, 40 passed in 1.38s

[5/20] FILE.READ
  ✓ tests/test_user.py

[6/20] FILE.WRITE
  ⚠ approval required
  file: src/user.py
  reason: modifies workspace
  risk: medium

Approve? [y/N/diff] y

[7/20] TERM.EXEC
  $ pytest -q

  ✓ success
  42 passed in 1.21s

[8/20] EVAL.APPLY
  score: 1.0
  acceptance criteria: passed

[9/20] LOOP.HALT
  ✓ task completed

Result:
  status: succeeded
  steps: 9
  skill proposed: python_pytest_repair_loop
  memory: 1 proposal accepted
```

## 17.3 Ambiguous Goal Output

```text
LoopOS detected an ambiguous goal.

Goal:
  帮我优化这个项目

Missing:
  - scope
  - acceptance criteria
  - output format
  - risk boundary

请选择一个执行方案：

[1] 架构审计优先
    只读分析项目，不修改代码。
    输出：docs/project-audit.md, docs/optimization-roadmap.md
    风险：low

[2] MVP 快速落地
    实现最小可运行 CLI agent。
    输出：loopos run/status/trace, mock loop, tests
    风险：medium

[3] Kernel 架构升级
    重构为 AIL + Policy OS + Syscall + Memory Kernel。
    输出：核心模块骨架和测试。
    风险：medium-high

[4] CLI UI 优先
    打磨终端交互、审批、trace、policy explain。
    输出：Rich CLI UI。
    风险：low-medium

[5] 自定义 / 合并多个方案

Select [1-5]:
```

## 17.4 Trace Output

```text
run_01HZM9
├── 001 GOAL.SET              success
├── 002 GOAL.ANALYZE          success
├── 003 GOAL.FINALIZE         success
├── 004 CTX.COMPILE           success
├── 005 PLAN.CREATE           success
├── 006 TERM.EXEC pytest -q   failed
├── 007 EVAL.APPLY            failed
├── 008 PROGRESS.MEASURE      no_progress
├── 009 LOOP.DECIDE           repair
├── 010 FILE.READ             success
├── 011 FILE.WRITE            success
├── 012 TERM.EXEC pytest -q   success
├── 013 EVAL.APPLY            success
└── 014 LOOP.HALT             success
```

## 17.5 UI Rules

```text
Use Typer.
Use Rich.
Support --json.
No WebUI.
No GUI.
No desktop windows.
Default output is concise terminal stream.
--verbose includes stdout/stderr summaries.
--show-ail includes AIL JSON.
--show-policy includes PolicyDecision.
--json emits machine-readable output only.
```

---

# 18. Trace / Audit

每一步都要写 EventLog。

```python
class AILEvent(BaseModel):
    event_id: str
    run_id: str
    step: int
    kind: Literal[
        "goal_analysis",
        "goal_proposals",
        "goal_selection",
        "goal_spec",
        "instruction",
        "policy",
        "syscall",
        "observation",
        "evaluation",
        "progress_delta",
        "loop_decision",
        "halt_condition",
        "memory",
        "skill",
        "trigger",
        "task",
        "worktree",
        "review"
    ]
    payload: dict[str, Any]
    created_at: datetime
```

Trace 必须解释：

```text
为什么执行
为什么阻止
用了什么工具
输出是什么
如何评价
是否有进展
为什么修复/重规划/停止
是否写入 memory
是否生成 skill
谁审查了结果
```

---

# 19. Human Responsibility / Anti Cognitive Surrender

LoopOS 必须防止：

```text
Cognitive surrender:
  人类长期不看代码，只看 agent 结果。

Responsibility diffusion:
  自动循环出错后无人负责。
```

系统防护：

```text
1. 高风险变更必须人类审批。
2. PR 必须包含 trace summary。
3. Reviewer findings 必须显示。
4. 自动合并默认关闭。
5. 定期生成复盘报告。
6. CLI 提醒用户抽查代码。
7. 重大失败进入 incident log。
8. 生产和验收分离。
```

CLI：

```bash
loopos accountability report
loopos audit weekly
loopos review random-sample --limit 5
```

---

# 20. Testing Requirements

所有模块必须有测试。

测试目录：

```text
tests/ail
tests/kernel
tests/goal
tests/convergence
tests/triggers
tests/tasks
tests/worktree
tests/review
tests/policy_os
tests/syscalls
tests/execution
tests/memory
tests/skills
tests/model_kernel
tests/gateway
tests/cli
```

必须测试：

```text
ambiguous goal enters negotiation
medium ambiguous goal asks confirmation
clear goal executes directly
GoalSpec requires acceptance criteria
dangerous command blocked
low risk command allowed
policy explain works
AIL JSON roundtrip
loop halts on success
loop stops at max_steps
no progress triggers replan
repeated command triggers replan
memory proposal rejected when low confidence
skill extracted only on success
trace replay deterministic
trigger creates task not direct execution
task persists after restart
code task requires worktree
producer cannot self-approve high-risk work
non-vision primary routes image to vision companion
gateway unauthorized user rejected
```

测试约束：

```text
no real network
no real API keys
no dangerous commands
mock LLM
mock external tools unless explicitly testing safe executor
```

---

# 21. Implementation Phases

Codex 必须按阶段实现，不要一次性实现全部。

## Phase 0: Final Architecture Docs

```text
Create docs/final-loopos-architecture.md.

Include:
- kernel architecture
- goal negotiation
- loop convergence
- outer loop engineering
- policy os
- syscall/mcp
- memory governance
- skill kernel
- model kernel
- chatops gateway
- cli ux
- implementation phases
- test plan

Do not implement code yet.
```

## Phase 1: Project Skeleton

```text
Create module structure.
Add pyproject.toml.
Add README.
Add tests/test_imports.py.

No complex logic.
No real shell execution.
```

## Phase 2: AIL Core

```text
Implement AIL models:
AILGoal
AILState
AILInstruction
AILSyscall
AILObservation
AILEvaluation
AILEvent
AILMemory
AILSkill
RenderSpec

Add validators and JSON roundtrip.
```

## Phase 3: Policy OS

```text
Implement:
YAML policy loader
rule matcher
priority resolver
PolicyDecision
audit log

Add policies:
terminal_safety
goal_negotiation
loop_convergence
outer_loop
memory_governance
tool_routing
review_separation
```

## Phase 4: Goal Negotiation Kernel

```text
Implement:
AmbiguityReport
GoalProposal
GoalSpec
NegotiationEngine
ProposalTemplates

CLI:
loopos goal analyze
loopos goal propose

Integrate into loopos run.
```

## Phase 5: Loop Convergence Kernel

```text
Implement:
EvaluationResult
ProgressDelta
LoopDecision
HaltCondition
RepairStrategy
ReplanStrategy

Integrate into LoopEngine.
```

## Phase 6: Syscall / MCP Layer

```text
Implement:
SyscallSpec
SyscallCall
SyscallResult
SyscallRegistry
SyscallRouter

MVP syscalls:
terminal.exec
file.read
file.write
git.status
git.diff
```

## Phase 7: Safe Execution Runtime

```text
Implement:
PermissionPolicy
TerminalExecutor
WorkspaceGuard
LocalBackend
MockBackend

Block dangerous commands.
```

## Phase 8: Kernel Loop

```text
Implement:
RunManager
LoopScheduler
LoopEngine
StateMachine
TransitionEngine
KernelSignal

Use deterministic planner for MVP.
```

## Phase 9: Memory Governance

```text
Implement:
EventLog
StateStore
BeliefStore
PreferenceStore
SkillStore
MemoryGovernor
MemoryRetriever
PreActionGate
```

## Phase 10: CLI Shell

```text
Implement terminal-native CLI:
run
status
trace
policy explain
tools list
memory list
skills list
ail validate

Use Typer + Rich.
Support --json.
```

## Phase 11: Outer Loop Engineering

```text
Implement:
TriggerEvent
LoopTask
TaskBoard
QuickWinSelector
WorktreeManager
Producer/Reviewer/Verifier models

Add CLI:
triggers
tasks
worktrees
review
```

## Phase 12: Model Kernel

```text
Implement:
ProviderProfile
ProviderRegistry
CapabilityRouter
MultiModelPlan
VisionCompanion
Aggregator
Verifier

No real API calls in tests.
```

## Phase 13: ChatOps Gateway

```text
Implement:
MessageEvent
GatewaySession
BasePlatformAdapter
WebhookAdapter
MockTelegramAdapter
ApprovalRouter

No real network in tests.
```

## Phase 14: Skill Kernel

```text
Implement:
SkillSpec
SkillRegistry
SkillImporter
SkillAuditor
ProjectSkillOnboarding

Imported skills disabled by default.
```

## Phase 15: Execution Backends

```text
Add:
DockerBackend skeleton
OpenHandsAdapter skeleton
SSHBackend skeleton

Only local/mock enabled by default.
```

## Phase 16: Benchmarks

```text
Add benchmark tasks:
file creation
safe terminal blocking
pytest repair mock
goal negotiation
loop convergence
outer loop task selection
worktree requirement
model routing
```

## Phase 17: Documentation and Release

```text
Create docs:
quickstart
architecture
cli-ui
policy-os
goal-negotiation
loop-convergence
outer-loop
provider-gateway
chatops-gateway
memory-governance
safety
benchmarks
contributing
```

---

# 22. Phase Prompts for Codex

## Phase 0 Prompt

```text
You are LoopOS final architecture engineer.

Task:
Create docs/final-loopos-architecture.md.

Do not implement code.

The document must describe:
1. LoopOS as terminal-native AI Agent OS Kernel.
2. OS analogy.
3. AIL / AI-ISA.
4. Goal Negotiation Kernel.
5. Loop Convergence Kernel.
6. Outer Loop Engineering Kernel.
7. Policy OS.
8. Syscall / MCP Layer.
9. Memory Governance.
10. Skill Kernel.
11. Model Kernel and multi-model routing.
12. ChatOps / mobile gateway.
13. Worktree isolation.
14. Producer / Reviewer / Verifier separation.
15. CLI UX.
16. Test strategy.
17. Implementation phases.

Do not modify code.
```

## Phase 1 Prompt

```text
You are LoopOS Python systems engineer.

Create project skeleton according to docs/final-loopos-architecture.md.

Use:
- Python 3.11+
- Pydantic v2
- Typer
- Rich
- pytest
- ruff
- mypy

Create all package directories and __init__.py files.
Create tests/test_imports.py.
Create pyproject.toml.

Acceptance:
pytest passes.
python -m loopos.cli.app --help works.

No real LLM.
No real shell execution.
```

## Phase 2 Prompt

```text
Implement AIL core models.

Files:
loopos/ail/*.py
tests/ail/test_ail_core.py

Implement:
AILGoal
AILState
AILInstruction
AILSyscall
AILObservation
AILEvaluation
AILEvent
AILMemory
AILSkill
RenderSpec

Support:
JSON roundtrip
op validation
required args validation
risk validation

No LLM.
No shell.
```

## Phase 3 Prompt

```text
Implement Policy OS.

Files:
loopos/policy_os/*.py
policies/**/*.yaml
tests/policy_os/*.py

Support:
YAML loading
rule matching
all/any/not
equals/in/regex/exists/lt/gt
priority resolution
block overrides allow
PolicyDecision output
audit events

Test:
rm -rf / blocked
curl | bash blocked
pytest -q low risk
git reset --hard approval required
GOAL.NEGOTIATION cannot call terminal
GoalSpec without acceptance criteria invalid
producer cannot self-approve high-risk work
```

## Phase 4 Prompt

```text
Implement Goal Negotiation Kernel.

Files:
loopos/goal/*.py
tests/goal/*.py
loopos/cli/commands/goal.py

Implement:
AmbiguityReport
GoalProposal
GoalSpec
NegotiationEngine
ProposalTemplates
Goal CLI renderer

Rules:
- high ambiguity generates 3-5 proposals
- medium ambiguity asks confirmation
- low ambiguity creates direct GoalSpec
- no tools or terminal during negotiation
- GoalSpec requires acceptance criteria

CLI:
loopos goal analyze "<goal>"
loopos goal propose "<goal>"
```

## Phase 5 Prompt

```text
Implement Loop Convergence Kernel.

Files:
loopos/convergence/*.py
tests/convergence/*.py

Implement:
EvaluationResult
ProgressDelta
LoopDecision
HaltCondition
RepairStrategy
ReplanStrategy

Rules:
- goal_satisfied requires acceptance criteria pass
- no_progress_count >= 2 triggers replan
- regression triggers replan
- policy blocked triggers halt_blocked
- max_steps triggers halt_failure
```

## Phase 6 Prompt

```text
Implement Syscall Layer.

Files:
loopos/syscalls/*.py
tests/syscalls/*.py

Implement:
SyscallSpec
SyscallCall
SyscallResult
SyscallRegistry
SyscallRouter

MVP syscalls:
terminal.exec
file.read
file.write
git.status
git.diff

All syscalls require PolicyDecision.
Blocked decision prevents execution.
```

## Phase 7 Prompt

```text
Implement safe execution runtime.

Files:
loopos/execution/*.py
loopos/execution/backends/*.py
tests/execution/*.py

Implement:
PermissionPolicy
TerminalExecutor
WorkspaceGuard
LocalBackend
MockBackend

Rules:
blocked commands never run
cwd must stay inside workspace
timeout required
stdout/stderr captured
dangerous commands blocked

No dangerous command execution in tests.
```

## Phase 8 Prompt

```text
Implement Kernel Loop.

Files:
loopos/kernel/*.py
tests/kernel/*.py

Implement:
RunManager
LoopScheduler
LoopEngine
StateMachine
TransitionEngine
KernelSignal

LoopEngine requires GoalSpec, not raw string.
Every step emits:
Observation
EvaluationResult
ProgressDelta
LoopDecision
EventLog event

Use deterministic planner for MVP.
```

## Phase 9 Prompt

```text
Implement Memory Governance.

Files:
loopos/memory/*.py
tests/memory/*.py

Implement:
EventLog JSONL
StateStore JSON
BeliefStore
PreferenceStore
SkillStore
MemoryGovernor
MemoryRetriever
PreActionGate

Rules:
append-only
confidence bounds
conflict links
no direct commit without governance
one-time choice is not global preference
```

## Phase 10 Prompt

```text
Implement terminal-native CLI.

Files:
loopos/cli/app.py
loopos/cli/commands/*.py
loopos/cli/renderers/*.py
tests/cli/*.py

Commands:
loopos run "<goal>"
loopos status RUN_ID
loopos trace RUN_ID
loopos step replay RUN_ID STEP
loopos policy explain --cmd "<cmd>"
loopos tools list
loopos memory list
loopos skills list
loopos ail validate FILE
loopos goal analyze "<goal>"
loopos goal propose "<goal>"

Use Typer + Rich.
No GUI.
No WebUI.
Support --json.
```

## Phase 11 Prompt

```text
Implement Outer Loop Engineering Kernel.

Files:
loopos/triggers/*.py
loopos/tasks/*.py
loopos/worktree/*.py
loopos/review/*.py
tests/triggers/*.py
tests/tasks/*.py
tests/worktree/*.py
tests/review/*.py

Implement:
TriggerEvent
TriggerRegistry
LoopTask
TaskBoard
QuickWinSelector
WorktreeLease
WorktreeManager
ReviewRun
Producer/Reviewer/Verifier role models

Rules:
trigger creates task, not direct execution
task state persists
code-modifying task requires worktree
producer cannot self-approve high-risk work
```

## Phase 12 Prompt

```text
Implement Model Kernel.

Files:
loopos/model_kernel/*.py
tests/model_kernel/*.py

Implement:
ProviderProfile
ProviderRegistry
CapabilityRouter
MultiModelPlan
VisionSummary
VisionCompanion
Aggregator
Verifier

Provider specs:
openai
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

No real API calls in tests.
```

## Phase 13 Prompt

```text
Implement ChatOps Gateway skeleton.

Files:
loopos/gateway/*.py
loopos/gateway/platforms/*.py
tests/gateway/*.py

Implement:
MessageEvent
GatewaySession
BasePlatformAdapter
ApprovalRequest
ApprovalRouter
WebhookAdapter
MockTelegramAdapter
MockEmailAdapter

Rules:
unauthorized user rejected
inbound message can create kernel run
approval decision resumes waiting run
no real network in tests
```

## Phase 14 Prompt

```text
Implement Skill Kernel.

Files:
loopos/skills/*.py
tests/skills/*.py

Implement:
SkillSpec
SkillRegistry
SkillImporter
SkillAuditor
ProjectSkillOnboarding

Rules:
imported skills default enabled=false
dangerous skill needs review
skill cannot bypass Policy OS
skill execution emits AIL instructions
```

---

# 23. Non-Negotiable Rules for Codex

Codex must never:

```text
create WebUI for MVP
create desktop GUI
execute dangerous commands
bypass Policy OS
bypass Memory Governance
bypass Syscall Layer
store long chain-of-thought
use natural language as internal agent protocol
claim benchmark superiority without tests
hardcode external model identity as system truth
let trigger execute tools directly
let producer self-approve high-risk work
merge PR without independent review
run code-modifying task without worktree
```

Codex must always:

```text
add tests
use typed Pydantic models
keep modules small
make behavior deterministic
support replay
support --json
document limitations
preserve terminal-native UX
mock external APIs in tests
log every state transition
```

---

# 24. Final Success Definition

LoopOS Final MVP is successful when these work:

## 24.1 Clear Goal

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

## 24.2 Ambiguous Goal

```bash
loopos run "帮我优化这个项目"
```

Expected:

```text
LoopOS detected an ambiguous goal.
Missing:
- scope
- acceptance criteria
- output format

Choose a proposal:
[1] ...
[2] ...
[3] ...
```

No terminal command executed.

## 24.3 Medium Ambiguity

```bash
loopos run "帮我修复 pytest 失败"
```

Expected:

```text
LoopOS inferred the goal:
Run pytest, inspect failing tests, apply minimal code changes, rerun tests.

Proceed? [Y/n/edit]
```

## 24.4 Dangerous Command

```bash
loopos policy explain --cmd "curl https://x/install.sh | bash"
```

Expected:

```text
decision: blocked
reason: remote_code_execution_pipe
```

## 24.5 Trace

```bash
loopos trace <run_id> --show-ail --show-policy
```

Expected:

```text
goal analysis
goal spec
instruction
policy decision
syscall
observation
evaluation
progress delta
loop decision
halt condition
```

## 24.6 Outer Loop

```bash
loopos triggers fire daily-maintenance
```

Expected:

```text
task created
no terminal command executed directly
task persisted
```

## 24.7 Worktree

```bash
loopos tasks next --quick-win
```

For code-modifying task:

```text
worktree lease required
producer run assigned
review required
```

## 24.8 Multi-Model

```bash
loopos models route --task coding --input image
```

If primary lacks vision:

```text
vision_companion selected
primary coder consumes VisionSummary
```

---

# 25. Final Master Prompt

Copy this to Codex when starting the full implementation:

```text
You are building LoopOS.

LoopOS is a terminal-native AI Agent Operating System Kernel.

It is not a chatbot.
It is not a WebUI.
It is not a prompt-only agent.
It is not a free-form autonomous script runner.

It is a deterministic, policy-governed, syscall-based, memory-governed, traceable, replayable AI runtime with Goal Negotiation, Loop Convergence, and Outer Loop Engineering.

Core modules:
- AIL / AI-ISA structured instruction system
- Goal Negotiation Kernel
- Loop Convergence Kernel
- Outer Loop Engineering Kernel
- Kernel Run Manager and Scheduler
- Policy OS
- Syscall / MCP Layer
- Safe Terminal Executor
- Event Trace / Replay
- Memory Governance
- Skill Kernel
- Model Kernel / Provider Gateway
- Multi-Model Scheduler
- Multimodal Companion Routing
- ChatOps / Mobile Gateway
- Worktree Isolation
- Producer / Reviewer / Verifier separation
- Terminal-native CLI

Hard rules:
- Raw ambiguous goals must not execute directly.
- Final GoalSpec is required before LoopEngine.
- Every step must produce Observation, EvaluationResult, ProgressDelta, and LoopDecision.
- All execution must pass Policy OS.
- All tools are syscalls.
- All memory writes pass governance.
- All code-modifying tasks require worktree isolation.
- Producer cannot self-approve high-risk work.
- Triggers create tasks, not direct tool execution.
- All actions are logged and replayable.
- No WebUI for MVP.
- No dangerous shell execution.
- No real LLM or network in tests.

Implement step by step.

Start with Phase 0 only:
Create docs/final-loopos-architecture.md.
Do not implement code yet.
```

---

# 26. Final Note

LoopOS 的最终竞争力不是 prompt，而是：

```text
内核化
结构化
可治理
可审计
可回放
可学习
可触发
可分工
可验收
终端原生
```

最终你要得到的不是一个“会说话的 AI”，而是一个：

> **能在安全策略下调用世界、持续接收任务、主动澄清目标、隔离执行、独立验收、积累经验、复用技能、并能被人类审计和负责的 AI Runtime Kernel。**

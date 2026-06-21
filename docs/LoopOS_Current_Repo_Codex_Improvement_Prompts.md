# LoopOS Current Repo Improvement Codex Prompt Pack

版本：v0.1  
用途：给 Codex / Claude Code / OpenHands 使用，基于当前 LoopOS 仓库进行**针对性改进**。  
目标：不是从 0 重写，而是在现有代码基础上，把当前 MVP+ / Early Alpha 项目推进到 **开源 Alpha / 可试用落地版**。  
适用上下文：当前项目已经有 AIL、Policy OS、Kernel Loop、Syscall、Execution、Memory、Goal、Convergence、Outer Loop、Provider/Gateway skeleton、CLI 和测试。  
核心原则：**不要横向继续堆概念，先纵向打穿关键闭环。**

---

## 0. 给 Codex 的总控提示词

```text
You are improving the existing LoopOS repository.

Do not start from scratch.
Do not rewrite the whole project.
Do not delete existing modules without a clear migration.
Do not remove working tests.
Do not introduce real LLM calls or real network calls in tests.
Do not execute dangerous shell commands.
Do not build WebUI or desktop GUI.

Your job is to upgrade the current MVP+/Early Alpha codebase toward an open-source Alpha release.

Focus on the biggest current gaps:
1. Product-grade CLI UI and CLI modularization.
2. Goal Negotiation v1.
3. Loop Convergence v1.
4. Policy OS Safety Levels L0-L5.
5. Local Workspace Intelligence v0.
6. Plugin Manifest / Registry v0.
7. Provider Profiles v1.
8. Webhook Gateway v0.
9. Worktree / Review flow hardening.
10. Open-source governance and Loopi branding files.

The existing project already has many modules:
- loopos/ail
- loopos/kernel
- loopos/policy_os
- loopos/syscalls
- loopos/execution
- loopos/memory
- loopos/goal
- loopos/convergence
- loopos/tasks
- loopos/triggers
- loopos/worktree
- loopos/review
- loopos/model_kernel
- loopos/gateway
- loopos/context
- loopos/eval
- loopos/cli

Improve these modules incrementally.
Every phase must:
- preserve current behavior
- add or update tests
- keep CLI working
- keep pytest passing
- avoid real external APIs
- avoid dangerous commands
- include clear docs or comments where appropriate

Start with Phase 0: create an improvement plan document based on current repository state.
```

---

# 1. 当前项目改进优先级

从审计结果看，当前项目已经有较完整骨架，但短板集中在：

```text
1. CLI 产品体验不足
2. Goal Negotiation 过于简单
3. Loop Convergence 过于轻量
4. Policy OS 缺 Safety Levels
5. Outer Loop / Worktree / Review 仍偏 skeleton
6. Provider / Gateway 仍偏 mock
7. Local Intelligence / Registry / Open-source governance 尚未落地
```

所以本 Prompt Pack 按以下优先级推进：

```text
Phase 0  改进计划文档
Phase 1  CLI app.py 拆分
Phase 2  产品级 CLI UI
Phase 3  Goal Negotiation v1
Phase 4  Loop Convergence v1
Phase 5  Policy OS Safety Levels
Phase 6  Local Workspace Intelligence v0
Phase 7  Plugin Manifest / Registry v0
Phase 8  Provider Profiles v1
Phase 9  Webhook Gateway v0
Phase 10 Worktree / Review Flow Hardening
Phase 11 Open-source Governance + Loopi Branding
Phase 12 Acceptance Suite
```

---

# 2. Phase 0 — 当前仓库改进计划

## 目标

先让 Codex 读当前项目，输出一份具体改进路线，不直接改代码逻辑。

## Codex Prompt

```text
You are improving the existing LoopOS repository.

Task:
Create docs/current-repo-improvement-plan.md.

Do not implement runtime code in this phase.

Inspect the current repository and document:
1. Existing module map.
2. Current CLI structure.
3. Current Goal Negotiation implementation.
4. Current Loop Convergence implementation.
5. Current Policy OS implementation.
6. Current Syscall/Execution implementation.
7. Current Memory/Skill implementation.
8. Current Outer Loop / Task / Worktree / Review skeleton.
9. Current Provider/Gateway skeleton.
10. Test coverage summary.
11. Top 15 concrete improvement tasks.

The plan must focus on upgrading the existing codebase, not rewriting from scratch.

Output format:
- Current State
- Gaps
- Risks
- Ordered Improvement Plan
- Test Plan
- Acceptance Criteria

Acceptance:
- docs/current-repo-improvement-plan.md exists.
- No runtime code modified.
- pytest still passes.
```

---

# 3. Phase 1 — CLI app.py 拆分与命令模块化

## 背景

当前 CLI 功能很多，但入口文件过大，逻辑和渲染混在一起。  
这会影响维护、测试和产品 UI 打磨。

## 目标

把 CLI 拆成：

```text
loopos/cli/app.py              只负责 Typer app 注册
loopos/cli/commands/*.py       每组命令独立
loopos/cli/renderers/*.py      UI 渲染独立
loopos/cli/options.py          通用参数
loopos/cli/context.py          CLI runtime context
```

## 目标结构

```text
loopos/cli/
  app.py
  context.py
  options.py
  commands/
    __init__.py
    run.py
    status.py
    trace.py
    policy.py
    goal.py
    tools.py
    memory.py
    skills.py
    tasks.py
    triggers.py
    worktrees.py
    review.py
    models.py
    gateway.py
    registry.py
    index.py
  renderers/
    __init__.py
    theme.py
    panels.py
    tables.py
    trees.py
    progress.py
    diff.py
    approval.py
    goal_renderer.py
    trace_renderer.py
    policy_renderer.py
    task_renderer.py
    json_output.py
```

## Codex Prompt

```text
You are refactoring the existing LoopOS CLI.

Goal:
Split the large CLI app into command modules and renderer modules without changing user-facing command behavior.

Rules:
- Do not remove existing CLI commands.
- Do not break current tests.
- Preserve existing command names and options.
- Move rendering code into loopos/cli/renderers.
- Keep loopos/cli/app.py small, preferably under 300 lines.
- Add tests for command registration and --help output.

Tasks:
1. Create loopos/cli/commands package.
2. Move run/status/trace/policy/goal/tools/memory/skills/tasks/triggers/worktrees/review/model/gateway commands into separate files where applicable.
3. Create loopos/cli/renderers package.
4. Move Rich Panel/Table/Tree helpers into renderers.
5. Add loopos/cli/context.py for shared paths/config/context.
6. Add loopos/cli/options.py for common CLI options such as --json, --verbose, --show-ail, --show-policy.
7. Ensure `python -m loopos.cli.app --help` still works.
8. Ensure existing CLI tests pass.
9. Add tests/cli/test_command_registration.py.

Acceptance:
- app.py is mostly Typer wiring.
- All existing commands still appear in --help.
- pytest passes.
- No runtime logic changed beyond module relocation.
```

---

# 4. Phase 2 — 产品级 CLI UI 升级

## 背景

LoopOS 的开源第一印象很大程度取决于 CLI。  
必须让用户运行 `loopos run`、`loopos trace`、`loopos policy explain` 时觉得专业、清晰、可信。

## 目标

实现以下渲染器：

```text
RunHeaderRenderer
StepStreamRenderer
GoalProposalRenderer
PolicyDecisionRenderer
TraceTreeRenderer
ApprovalRenderer
DiffRenderer
TaskBoardRenderer
ReviewRenderer
ResultSummaryRenderer
```

## CLI UI 规范

### 4.1 Run Header

```text
╭──────────────────────────────── LoopOS RUN ────────────────────────────────╮
│ Run ID      run_01HZM9                                                      │
│ Goal        修复当前 repo 的 pytest 失败                                      │
│ Workspace   /Users/dev/project                                               │
│ Mode        guarded                                                          │
│ Max Steps   20                                                               │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### 4.2 Step Stream

```text
[1/20] GOAL.SET
  ✓ goal parsed

[2/20] CTX.COMPILE
  ✓ context ready
  memories: 3  skills: 2  tools: 5  policies: 9

[3/20] TERM.EXEC
  $ pytest -q
  ✗ failed
  2 failed, 40 passed in 1.38s

[4/20] EVAL.APPLY
  score: 0.42
  failure_type: tests_failed
  repairable: true

[5/20] LOOP.DECIDE
  → repair
  reason: tests_failed, repairable
```

### 4.3 Policy Explain

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

Suggested Safer Alternative:
  Download the script, inspect it, then run with explicit approval.
```

### 4.4 Goal Proposal

```text
╭────────────────────── Intent Design Mode ──────────────────────╮
│ LoopOS detected an ambiguous goal.                              │
│ Loopi says: 先别跑，目标清楚了吗？                                │
╰────────────────────────────────────────────────────────────────╯

Goal:
  帮我优化这个项目

Missing:
  - scope
  - acceptance criteria
  - output format

Choose a proposal:
[1] 架构审计优先
[2] MVP 快速落地
[3] Kernel 架构升级
[4] CLI UI 优先
[5] 自定义 / 合并多个方案
```

## Codex Prompt

```text
You are upgrading LoopOS terminal UI.

Goal:
Make the CLI feel like a polished developer tool.

Implement renderers:
- RunHeaderRenderer
- StepStreamRenderer
- GoalProposalRenderer
- PolicyDecisionRenderer
- TraceTreeRenderer
- ApprovalRenderer
- DiffRenderer
- TaskBoardRenderer
- ReviewRenderer
- ResultSummaryRenderer

Rules:
- Use Rich.
- Keep --json output plain and machine-readable.
- Do not mix rendering logic with command/business logic.
- Do not change core runtime behavior.
- Keep terminal output concise by default.
- Use --verbose for details.
- Use --show-ail and --show-policy for debug output.
- Add snapshot-style tests using plain text assertions.

Acceptance:
- `loopos run ... --dry-run` displays Run Header, Step Stream, Result Summary.
- ambiguous goal displays Intent Design Mode.
- `loopos policy explain --cmd "curl x | bash"` displays blocked panel.
- `loopos trace <run_id>` displays tree-style trace.
- `--json` returns valid JSON without Rich markup.
- tests pass.
```

---

# 5. Phase 3 — Goal Negotiation v1

## 当前问题

当前 goal negotiation 已经存在，但偏简单：

```text
vague phrases
fixed proposals
limited GoalSpec
```

## 目标

升级成完整的：

```text
AmbiguityReport
GoalProposal
GoalSpec
GoalNegotiationEngine
ProposalSelection
GoalSpecPolicyCheck
```

## 数据模型

### AmbiguityReport

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

### GoalProposal

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

### GoalSpec

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
    created_from: Literal["direct", "confirmed", "proposal_selected", "proposal_merged", "manual_edit"]
```

## 行为规则

```text
ambiguity_score >= 0.6:
  generate 3-5 proposals and wait user selection

0.3 <= ambiguity_score < 0.6:
  generate inferred GoalSpec and ask confirmation

ambiguity_score < 0.3:
  create direct GoalSpec
```

高模糊必须包含：

```text
missing_scope
missing_acceptance_criteria
missing_output_format
```

## Codex Prompt

```text
You are upgrading LoopOS Goal Negotiation to v1.

Goal:
Replace the simple vague-goal detection with structured AmbiguityReport, GoalProposal, and GoalSpec.

Do not remove existing user-facing behavior. Extend it.

Tasks:
1. Update or create loopos/goal/ambiguity.py.
2. Update or create loopos/goal/proposal.py.
3. Update or create loopos/goal/goal_spec.py.
4. Update negotiation engine to produce:
   - AmbiguityReport
   - list[GoalProposal]
   - GoalSpec
5. Support three modes:
   - high ambiguity -> proposals
   - medium ambiguity -> confirmation
   - low ambiguity -> direct GoalSpec
6. Add proposal templates:
   - read-only audit
   - direct implementation
   - kernel architecture upgrade
   - CLI UX improvement
   - custom/merge
7. Ensure GoalSpec requires final_goal, scope, and acceptance_criteria.
8. Integrate with Policy OS: GoalSpec without acceptance criteria is invalid.
9. Update CLI rendering to use GoalProposalRenderer.
10. Add tests.

Tests:
- "帮我优化这个项目" -> should_negotiate true and 3-5 proposals.
- "帮我修复 pytest 失败" -> should_confirm true.
- "创建 hello.py，内容 print('hello')，运行它" -> direct GoalSpec.
- Proposal selection creates GoalSpec.
- GoalSpec without acceptance criteria fails validation.
- Goal negotiation never executes terminal or tools.

Acceptance:
pytest passes.
CLI shows improved proposals.
Existing dry-run behavior still works.
```

---

# 6. Phase 4 — Loop Convergence v1

## 当前问题

当前 convergence 有基础，但缺少足够强的评估、进度判断和停止机制。

## 目标

升级成：

```text
EvaluationResult
ProgressDelta
LoopDecision
HaltCondition
RepairStrategy
ReplanStrategy
```

## 新字段要求

### EvaluationResult

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

### ProgressDelta

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

### LoopDecision

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

## Codex Prompt

```text
You are upgrading LoopOS Loop Convergence to v1.

Goal:
Make each loop iteration measurable, explainable, and stoppable.

Tasks:
1. Update loopos/convergence/evaluation.py.
2. Update loopos/convergence/progress.py.
3. Update loopos/convergence/decision.py.
4. Add loopos/convergence/halt.py if missing.
5. Integrate convergence models into kernel loop.
6. Each step should produce:
   - Observation
   - EvaluationResult
   - ProgressDelta
   - LoopDecision
7. Add event kinds for evaluation/progress_delta/loop_decision/halt_condition.
8. Update trace renderer to show these fields.

Decision rules:
- policy blocked -> halt_blocked
- approval required -> wait_approval
- goal_satisfied -> halt_success
- approval denied -> halt_failure
- regression_detected -> replan
- no_progress_count >= 2 -> replan
- repeated_action_count >= 2 -> replan
- max_steps_reached -> halt_failure
- evaluation.repairable -> repair
- otherwise -> replan or halt_failure

Tests:
- Success score 1.0 halts success.
- Policy blocked halts blocked.
- No progress twice triggers replan.
- Regression triggers replan.
- Repeated action triggers replan.
- Max steps triggers halt failure.
- Trace includes EvaluationResult, ProgressDelta, LoopDecision.

Acceptance:
pytest passes.
loopos trace shows evaluation/progress/decision.
LoopEngine remains deterministic in tests.
```

---

# 7. Phase 5 — Policy OS Safety Levels L0-L5

## 目标

把 Policy OS 从简单 allow/block/approval 升级为安全等级系统。

## Safety Levels

```text
L0 observe:
  只读查看、总结、状态查询

L1 low-risk local:
  运行安全测试、读取普通文件、创建临时文件

L2 hard inquiry:
  修改文件、删除普通文件、修改配置、中风险命令

L3 high-risk guarded:
  git reset、批量删除、系统设置修改、外部 API 写操作

L4 user-only:
  支付、提交敏感表单、发送不可撤销消息、上传隐私数据

L5 blocked:
  破坏性系统命令、泄露 secrets、绕过安全、恶意行为
```

## PolicyDecision 扩展

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
    constraints: dict[str, Any]
    renderer_hints: dict[str, Any]
```

## Codex Prompt

```text
You are upgrading LoopOS Policy OS with Safety Levels.

Goal:
Add L0-L5 safety classification while preserving existing policy behavior.

Tasks:
1. Update PolicyDecision model.
2. Add safety_level to policy YAML action schema.
3. Update policy resolver to infer safety_level if missing.
4. Update terminal_safety policies:
   - file read normal -> L0/L1
   - pytest -q -> L1
   - file.write -> L2
   - git reset --hard -> L3
   - payment/credential action -> L4 if applicable
   - rm -rf / -> L5
   - curl | bash -> L5
5. Update PolicyDecisionRenderer to show Safety Level.
6. Update policy explain CLI.
7. Add tests.

Rules:
- L5 is always blocked.
- L4 is user-only; agent cannot execute, only guide.
- L3 requires explicit approval and rollback plan if mutation.
- L2 requires hard inquiry approval.
- L0/L1 may auto-allow if no other rule blocks.

Tests:
- rm -rf / -> L5 blocked.
- curl | bash -> L5 blocked.
- pytest -q -> L1 allowed.
- file.write -> L2 approval required.
- git reset --hard -> L3 approval required.
- L4 user-only action cannot execute.

Acceptance:
pytest passes.
policy explain shows safety level.
existing policies still load.
```

---

# 8. Phase 6 — Local Workspace Intelligence v0

## 目标

实现本地文件索引、内容搜索和隐私过滤，为后续 Marvis-like 本地智能做基础。

## 模块

```text
loopos/local_intel/
  __init__.py
  file_index.py
  search.py
  privacy_filter.py
  indexer.py
```

## 功能

```text
1. 扫描 workspace 文件。
2. 忽略 .git、node_modules、venv、__pycache__、dist、build。
3. 默认过滤 .env、private key、secret 文件。
4. 支持文件名搜索。
5. 支持文本文件内容搜索。
6. 保存索引到 .loopos/index/files.jsonl。
```

## CLI

```bash
loopos index build
loopos index status
loopos search "pytest"
```

## Codex Prompt

```text
You are implementing Local Workspace Intelligence v0 for LoopOS.

Goal:
Add safe local indexing and search.

Tasks:
1. Create loopos/local_intel package.
2. Implement PrivacyFilter:
   - blocks .env
   - blocks private key files
   - blocks files with secret-like names
   - ignores .git, node_modules, venv, __pycache__, dist, build
3. Implement FileIndexEntry:
   - path
   - size
   - modified_at
   - extension
   - text_preview
   - indexed_at
   - privacy_level
4. Implement FileIndexer:
   - build index
   - save to .loopos/index/files.jsonl
   - load index
5. Implement SearchEngine:
   - filename search
   - simple content search
6. Add CLI:
   - loopos index build
   - loopos index status
   - loopos search "<query>"
7. Add tests with temp workspace.

Rules:
- Do not upload files.
- Do not read binary files deeply.
- Do not index secrets.
- Keep index local.

Tests:
- index builds on sample workspace.
- .env is filtered.
- private key is filtered.
- search finds text file content.
- search finds filename.
- status shows count.

Acceptance:
pytest passes.
CLI commands work.
```

---

# 9. Phase 7 — Plugin Manifest / Registry v0

## 目标

为开源生态做入口：先实现本地 registry 和 plugin manifest 校验。

## Plugin Types

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

## Manifest 示例

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

## Codex Prompt

```text
You are implementing LoopOS Plugin Manifest and Local Registry v0.

Goal:
Create the foundation for open-source ecosystem contributions.

Tasks:
1. Create loopos/registry/manifest.py.
2. Create loopos/registry/source.py.
3. Create loopos/registry/auditor.py.
4. Create loopos/registry/installer.py.
5. Define PluginManifest model:
   - id
   - type
   - name
   - description
   - version
   - compatibility
   - required_tools
   - required_providers
   - risk_level
   - maintainers
   - tests
   - permissions
6. Implement local registry directory:
   .loopos/registry/
7. Add CLI:
   - loopos registry list
   - loopos registry search <query>
   - loopos registry audit <path>
   - loopos registry install <path>
8. Create docs/plugin-spec.md.
9. Add sample manifests under examples/plugins/.

Rules:
- Install only local manifest metadata in v0.
- Do not execute plugin code.
- Unsafe permissions should be flagged.
- Missing maintainers should warn.

Tests:
- valid manifest loads.
- invalid manifest fails.
- unsafe plugin flagged.
- local install copies manifest metadata.
- registry list works.

Acceptance:
pytest passes.
docs/plugin-spec.md exists.
```

---

# 10. Phase 8 — Provider Profiles v1

## 目标

当前 provider gateway 已有骨架，升级成可扩展 profiles。

## Providers

先支持 profile，不一定真实调用：

```text
openai
openai-codex
openrouter
anthropic
gemini
deepseek
kimi-coding
qwen
minimax
xai
alibaba
huggingface
bedrock
azure-foundry
ollama-cloud
custom
```

## Provider YAML

```yaml
id: deepseek
aliases:
  - deepseek
api_mode: openai_compatible
auth_type: api_key
base_url: https://api.deepseek.com/v1
env_vars:
  - DEEPSEEK_API_KEY
capabilities:
  - text
  - code
  - reasoning
  - json_schema
default_models:
  - deepseek-chat
  - deepseek-reasoner
cost_class: low
latency_class: medium
reliability_score: 0.8
```

## Codex Prompt

```text
You are upgrading LoopOS Provider Gateway to Provider Profiles v1.

Goal:
Make provider support extensible through YAML profiles and capability routing.

Tasks:
1. Update ProviderProfile model.
2. Add provider YAML directory:
   providers/
3. Add profiles for:
   openai
   openrouter
   anthropic
   gemini
   deepseek
   kimi-coding
   qwen
   minimax
   xai
   alibaba
   huggingface
   bedrock
   azure-foundry
   ollama-cloud
   custom
4. Implement ProviderLoader.
5. Implement alias resolution.
6. Implement CapabilityRouter:
   - choose provider by required capabilities
   - local-only filtering if privacy required
   - fallback if provider unavailable
7. Keep MockModelClient for tests.
8. Add CLI:
   - loopos models list
   - loopos models inspect <provider>
   - loopos models route --task coding
9. Add tests.

Rules:
- No real API calls.
- Do not require API keys in tests.
- Missing env vars should mark provider unavailable, not crash.
- custom provider must be supported.

Tests:
- provider profiles load.
- aliases resolve.
- coding task selects code-capable provider.
- image input selects vision provider if needed.
- privacy local blocks cloud provider.
- missing API key marks unavailable.

Acceptance:
pytest passes.
CLI displays providers.
```

---

# 11. Phase 9 — Webhook Gateway v0

## 目标

把 mock gateway 升级成可本地接入的 webhook gateway。

## 功能

```text
POST /message
POST /approval
GET /health
```

可以先实现 framework-independent handler，不一定开真实 server；但 CLI 可以模拟。

## Codex Prompt

```text
You are implementing Webhook Gateway v0 for LoopOS.

Goal:
Allow external systems or mobile/chat bridges to send messages and approval decisions to LoopOS through a local webhook interface.

Tasks:
1. Update loopos/gateway/message.py if needed.
2. Implement loopos/gateway/platforms/webhook.py.
3. Implement WebhookMessageHandler:
   - parse inbound message
   - validate token/allowlist
   - create MessageEvent
   - route to ChatOpsGateway
4. Implement WebhookApprovalHandler:
   - parse approval_id
   - decision approve/deny
   - resume or halt waiting run
5. Add CLI simulation:
   - loopos gateway simulate message "..."
   - loopos gateway simulate approval --approval-id ... --decision approve
6. Add tests.

Rules:
- No real network required in tests.
- Token auth must exist even if simple.
- Unauthorized user rejected.
- Approval decision must be logged.
- Gateway must not bypass Policy OS.

Tests:
- authorized message creates event.
- unauthorized rejected.
- approval approve resumes waiting run.
- approval deny halts or marks denied.
- malformed payload rejected.

Acceptance:
pytest passes.
gateway simulate commands work.
```

---

# 12. Phase 10 — Worktree / Review Flow Hardening

## 当前问题

已有 skeleton，但需要更真实的任务和审查流程。

## 目标

增强：

```text
Task lifecycle
Worktree lease
ReviewRun
VerifierRun
Review artifact
```

## Codex Prompt

```text
You are hardening LoopOS Outer Loop worktree and review flow.

Goal:
Make task -> worktree -> producer -> verifier -> reviewer flow more concrete and testable.

Tasks:
1. Improve LoopTask status transitions:
   backlog -> ready -> running -> waiting_review -> done/failed/deferred/blocked.
2. Improve WorktreeLease:
   - lease_id
   - task_id
   - run_id
   - path
   - branch
   - base_branch
   - status
   - created_at
   - expires_at
3. Implement WorktreeManager with dry-run/materialization modes:
   - dry-run returns plan
   - materialize can be mocked in tests
4. Implement ReviewRun:
   - review_id
   - task_id
   - producer_run_id
   - verifier_status
   - reviewer_status
   - findings
   - required_changes
   - decision
5. Implement ReviewArtifact:
   - diff_summary
   - tests_run
   - policy_checks
   - acceptance_status
6. Update CLI:
   - loopos tasks show TASK_ID
   - loopos review start TASK_ID
   - loopos review show REVIEW_ID
7. Add tests.

Rules:
- Code-modifying task requires worktree unless explicit policy approval.
- Producer cannot self-approve high-risk task.
- Reviewer default read-only.
- Verifier should rely on tests/checks where available.
- No real git destructive operations in tests.

Tests:
- task transitions valid.
- invalid transition rejected.
- code task requires worktree.
- worktree dry-run plan generated.
- review artifact created.
- producer cannot approve own high-risk work.
- review approve requires verifier success.

Acceptance:
pytest passes.
CLI task/review commands show useful output.
```

---

# 13. Phase 11 — 开源治理与 Loopi 品牌落地

## 目标

让项目看起来像一个可以吸引贡献者的开源项目，而不是私人原型。

## 文件

```text
LICENSE
CONTRIBUTING.md
GOVERNANCE.md
SECURITY.md
PLUGIN_SPEC.md
RFC_PROCESS.md
MAINTAINERS.md
CODE_OF_CONDUCT.md
ROADMAP.md
docs/brand-loopi.md
assets/mascot/README.md
```

## README 改进

README 开头建议：

```markdown
# LoopOS

> Not another agent. The kernel for running agents.

LoopOS is an open-source, terminal-native Agent Runtime OS for Loop Engineering.

It turns vague goals into governed, traceable, replayable, and convergent agent loops.

Meet Loopi / 小环狸, the tiny terminal raccoon guarding every loop.
```

## Codex Prompt

```text
You are preparing LoopOS for open-source Alpha.

Goal:
Add governance, contribution, security, plugin, roadmap, and branding files.

Tasks:
1. Add or update LICENSE. If no license is specified by project owner, create docs/license-options.md instead and do not pick one unilaterally.
2. Add CONTRIBUTING.md.
3. Add GOVERNANCE.md.
4. Add SECURITY.md.
5. Add PLUGIN_SPEC.md or update docs/plugin-spec.md.
6. Add RFC_PROCESS.md.
7. Add MAINTAINERS.md template.
8. Add CODE_OF_CONDUCT.md.
9. Add ROADMAP.md.
10. Add docs/brand-loopi.md describing:
    - LoopOS
    - Loopi / 小环狸
    - slogan
    - mascot usage
    - community tone
11. Add assets/mascot/README.md.
12. Update README introduction with clear current status:
    - what works now
    - what is planned
    - safe defaults
    - quickstart
    - contribution paths

Rules:
- Do not overclaim production readiness.
- Be honest about current status.
- Make contribution paths clear:
  Core
  Provider plugins
  Skill packs
  Policy packs
  Gateway adapters
  Benchmarks
  Docs
- Keep brand professional but memorable.

Acceptance:
- Governance files exist.
- README has strong positioning.
- docs/brand-loopi.md exists.
- No false claims.
```

---

# 14. Phase 12 — Acceptance Suite

## 目标

建立一组端到端测试和 CLI 验收脚本，证明项目不是架构空壳。

## 场景

```text
1. clear goal dry-run succeeds
2. ambiguous goal shows proposals
3. dangerous command blocked
4. trace includes evaluation/progress/decision
5. trigger creates persistent task
6. code task requires worktree
7. provider routing selects correct capability
8. gateway approval resumes waiting run
9. registry validates plugin
10. local index filters secrets
```

## Codex Prompt

```text
You are creating LoopOS Alpha Acceptance Suite.

Goal:
Add end-to-end tests that validate the key product promises.

Create tests/acceptance/ with:
1. test_clear_goal_dry_run.py
2. test_ambiguous_goal_negotiation.py
3. test_policy_blocked_command.py
4. test_trace_includes_convergence.py
5. test_trigger_creates_task.py
6. test_worktree_required_for_code_task.py
7. test_provider_routing.py
8. test_gateway_approval.py
9. test_registry_manifest.py
10. test_local_index_privacy.py

Rules:
- Use temp directories.
- Use mock clients.
- No real network.
- No real dangerous shell commands.
- Prefer CLI runner tests where possible.
- Assertions should validate user-facing behavior and structured JSON.

Acceptance:
- pytest tests/acceptance passes.
- Full pytest passes.
- Makefile or docs includes acceptance command.
```

---

# 15. 单次任务模板

当你给 Codex 单独执行一个任务时，使用这个模板。

```text
You are improving the existing LoopOS repository.

Task:
<具体任务>

Scope:
<允许修改的文件/目录>

Do not:
- rewrite unrelated modules
- remove existing tests
- call real APIs
- execute dangerous commands
- change public CLI behavior unless specified

Required:
- add or update tests
- keep pytest passing
- update docs if behavior changes
- preserve terminal-native UX
- use typed Pydantic models where applicable

Acceptance:
<明确验收标准>
```

---

# 16. Code Review Prompt

```text
Review the current changes for LoopOS.

Focus on:
1. Does this preserve existing behavior?
2. Are tests sufficient?
3. Does it bypass Policy OS, Syscall Router, or Memory Governance?
4. Does it introduce real API/network calls in tests?
5. Does it execute risky shell commands?
6. Is CLI output still readable?
7. Are models typed and validated?
8. Is error handling clear?
9. Is the implementation over-engineered?
10. Is the module boundary clean?

Output:
- Summary
- Risks
- Required fixes
- Suggested improvements
- Test gaps
```

---

# 17. Debug Prompt

```text
You are debugging LoopOS.

Problem:
<粘贴错误>

Steps:
1. Reproduce with the smallest command/test.
2. Identify failing module.
3. Explain root cause.
4. Fix minimal code.
5. Add regression test.
6. Run relevant tests.
7. Summarize.

Constraints:
- Do not rewrite large unrelated modules.
- Do not hide failures.
- Do not delete tests to pass.
- Do not call real APIs.
```

---

# 18. 最终建议执行顺序

我建议你把 Codex 按这个顺序推进：

```text
1. Phase 0  current-repo-improvement-plan
2. Phase 1  CLI split
3. Phase 2  CLI UI
4. Phase 3  Goal Negotiation v1
5. Phase 4  Loop Convergence v1
6. Phase 5  Safety Levels
7. Phase 12 Acceptance Suite 的前 4 个测试
8. Phase 6  Local Intelligence
9. Phase 7  Registry
10. Phase 8 Provider Profiles
11. Phase 9 Webhook Gateway
12. Phase 10 Worktree/Review
13. Phase 11 Governance/Brand
14. Phase 12 完整 Acceptance Suite
```

最关键的原则：

```text
先把用户能看到、能相信、能复盘的闭环打磨好。
然后再扩 provider、gateway、registry 和生态。
```

---

# 19. 开源 Alpha 达标标准

完成以下能力后，可以考虑开源 Alpha：

```text
1. README 专业且诚实。
2. CLI UI 足够漂亮。
3. loopos run clear goal 可 dry-run 成功。
4. ambiguous goal 能展示方案。
5. policy explain 能阻止危险命令。
6. trace 能显示 evaluation/progress/decision。
7. local index 能搜索且过滤 secrets。
8. registry manifest 能校验。
9. provider profiles 能 list/route。
10. webhook/mock gateway 能 approval。
11. task/worktree/review skeleton 可演示。
12. pytest 全部通过。
13. 有 CONTRIBUTING / SECURITY / GOVERNANCE / PLUGIN_SPEC。
14. 有 Loopi 品牌文档和 assets 目录。
```

---

# 20. 最后提醒

当前项目最大问题不是“没有想法”，而是：

```text
概念很完整，产品感和真实可用链路还要补。
```

所以 Codex 改进方向必须克制：

```text
不要继续加新大模块。
不要一口气接真实平台。
不要先做 GUI。
不要先做云服务。
不要先做复杂 daemon。
```

先把这条链路做稳：

```text
Goal Negotiation
→ GoalSpec
→ Policy OS
→ Syscall
→ Loop Evaluation
→ Progress
→ Decision
→ Trace
→ CLI UI
```

这条链路打穿，LoopOS 的开源 Alpha 就有说服力。

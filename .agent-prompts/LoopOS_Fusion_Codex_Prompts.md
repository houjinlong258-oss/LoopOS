# LoopOS 融合版 Codex 提示词手册

版本：v0.2  
目标：把 LoopOS、AIL Agent 内部语言、MCP 工具通信、Policy OS、Memory Governance、Skill Learning、OpenHands/LangGraph/Letta/Zep/projectmem 的可借鉴能力，融合成一套 **可直接交给 Codex 执行的分阶段工程提示词**。  
推荐保存路径：`docs/LoopOS_Fusion_Codex_Prompts.md`

---

## 0. 本文档解决什么问题

你现在要做的不是普通 agent，也不是 Claude Code / Codex CLI / OpenHands / Hermes / 小龙虾的简单复刻，而是一个更底层的系统：

> **LoopOS：一个由 AI-ISA 状态机驱动，通过 MCP 调用工具，通过 Terminal 执行世界，通过 Policy OS 治理行为，通过 Memory Governance 学习经验的 Agent Runtime。**

这份文档把此前讨论的全部核心想法融合为可执行开发任务：

```text
AIL / Agent 内部语言
  + MCP Tool Hub
  + Terminal-native Loop
  + Policy OS
  + Memory Governance
  + Skill Learning
  + Context Compiler
  + User Preference Model
  + OpenHands / LangGraph / Letta / Zep / projectmem 可借鉴实现
  = LoopOS Core
```

这份文档不是概念说明，而是给 Codex 的开发提示词集合。每个阶段都包含目标、允许修改文件、禁止事项、验收标准和测试要求。

---

## 1. 总体架构融合

LoopOS 最终架构建议如下：

```text
Human Input
  ↓
Intent Compiler
  ↓
AIL Goal / Task
  ↓
Context Compiler
  ↓
Policy OS
  ↓
AI-ISA Instruction Generator
  ↓
Instruction Validator
  ↓
MCP Tool Router
  ↓
Terminal / File / Git / Browser / OpenHands Sandbox
  ↓
Observation Normalizer
  ↓
Evaluator / Critic
  ↓
State Transition
  ↓
Memory Governance
  ↓
Skill Learning
  ↓
Loop Decision
  ↓
Renderer
  ↓
Human Output
```

其中：

```text
AIL = Agent 内部通信语言
MCP = 工具协议和工具路由层
Policy OS = 行为、工具、安全、记忆、输出规则系统
Memory Governance = 长期记忆写入审批和冲突处理
Skill Learning = 从成功执行轨迹中提取可复用能力
Context Compiler = 减少 token 和上下文污染的核心压缩器
```

---

## 2. 最重要的设计原则

### 2.1 不做聊天机器人

LoopOS 内部不是自然语言聊天，而是状态机执行。

错误方向：

```text
Planner 用自然语言告诉 Executor 应该做什么。
Executor 用自然语言解释自己做了什么。
Critic 再用自然语言评论。
```

正确方向：

```json
{
  "kind": "instruction",
  "op": "TERM.EXEC",
  "args": {
    "cmd": "pytest -q",
    "cwd": "."
  },
  "reason": {
    "code": "VERIFY_TESTS",
    "confidence": 0.86
  },
  "expect": {
    "success": ["tests_pass"],
    "fail": ["tests_fail", "timeout"]
  }
}
```

### 2.2 LLM 只做三件事

```text
1. Intent Compiler：把用户自然语言编译成结构化目标。
2. Policy/Planner：在状态约束下生成下一条 AI-ISA 指令。
3. Renderer：把最终结构化结果渲染成人类语言。
```

LLM 不应该直接执行工具，不应该直接写长期记忆，不应该绕过 Policy OS。

### 2.3 所有工具通过 MCP-like 接口

即使 MVP 先不完整实现真实 MCP，也要保持接口可替换：

```text
AIL TOOL.CALL
  ↓
MCP ToolCall
  ↓
ToolResult
  ↓
AIL Observation
```

### 2.4 所有长期记忆都必须经过治理

```text
MemoryProposal
  ↓
MemoryGovernor
  ↓
accepted / rejected / needs_review / conflict
  ↓
MemoryStore
```

### 2.5 所有风险操作必须通过 Policy OS

```text
Instruction
  ↓
PolicyContext
  ↓
PolicyEngine
  ↓
PolicyDecision
  ↓
Executor
```

---

## 3. 推荐项目结构

```text
loopos/
  ail/
    __init__.py
    base.py
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
    codec.py
    validators.py

  core/
    __init__.py
    loop_engine.py
    transition.py
    context_compiler.py
    policy.py
    graph_loop.py

  agents/
    __init__.py
    intent_compiler.py
    planner.py
    executor_agent.py
    critic.py
    memory_writer.py
    skill_extractor.py
    renderer.py

  mcp/
    __init__.py
    types.py
    registry.py
    router.py
    adapters.py

  execution/
    __init__.py
    terminal.py
    permissions.py
    sandbox.py

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

  policies/
    core/
    tools/
    memory/
    renderer/
    safety/
    coding/
    optimization/

  integrations/
    __init__.py
    openhands_adapter.py
    langgraph_adapter.py
    letta_adapter.py
    zep_adapter.py
    projectmem_adapter.py

  cli/
    __init__.py
    app.py

  eval/
    runner.py
    metrics.py

tests/
  ail/
  core/
  mcp/
  execution/
  memory/
  policy_os/
  integrations/
  cli/
  eval/
```

---

## 4. 总控 AGENTS.md

把下面内容放到仓库根目录 `AGENTS.md`。

```markdown
# AGENTS.md — LoopOS Development Rules

You are working on LoopOS, a terminal-native, MCP-compatible, AI-ISA-driven, Policy-OS-governed, self-improving agent runtime.

## Project Identity

LoopOS is not a chatbot.

LoopOS is a state-machine runtime where:
- natural language is only used at user input and final output boundaries;
- internal communication uses AIL: structured Goal, State, Instruction, Observation, Evaluation, Event, Memory, Skill, RenderSpec;
- all tools are called through an MCP-like Tool Hub;
- all terminal commands pass through Permission Policy and Policy OS;
- all long-term memory writes pass through Memory Governance;
- successful traces can become reusable Skills;
- Context Compiler reduces token cost and prevents context pollution.

## Primary Implementation

MVP is Python-first:
- Python 3.11+
- Pydantic v2
- Typer
- Rich
- pytest
- ruff
- mypy

Later:
- TypeScript for MCP gateway / event service.
- Rust for hardened sandbox execution.

## Architecture Boundaries

Do not build a giant system prompt.

Do not embed long external model prompts directly into the runtime.

If useful prompt rules are found, distill them into Policy Packs:
- behavior
- tool routing
- terminal safety
- memory applicability
- memory governance
- renderer style
- context budget
- loop convergence
- prompt injection defense

## Internal Communication

Internal messages must be structured.

Allowed internal objects:
- AILGoal
- AILState
- AILInstruction
- AILObservation
- AILEvaluation
- AILEvent
- MemoryProposal
- GovernanceDecision
- SkillProposal
- RenderSpec

Avoid long natural-language internal messages.

## Minimum AI-ISA Operations

- GOAL.SET
- CTX.COMPILE
- PLAN.CREATE
- PLAN.UPDATE
- TOOL.CALL
- TERM.EXEC
- STATE.PATCH
- EVAL.SCORE
- MEM.PROPOSE
- MEM.COMMIT
- SKILL.EXTRACT
- SKILL.APPLY
- LOOP.CONTINUE
- LOOP.REPAIR
- LOOP.REPLAN
- LOOP.HALT

## MCP Rules

All tools must be registered with:
- name
- description
- input_schema
- output_schema
- risk_level
- requires_approval
- handler

MVP tools:
- terminal.exec
- file.read
- file.write
- git.status
- git.diff

## Policy OS Rules

All instructions must pass through PolicyEngine before execution.

Blocking policy decisions must stop execution.

Approval policy decisions must not execute in non-interactive mode unless explicitly permitted.

## Terminal Safety

Never run destructive commands without policy evaluation.

Blocked examples:
- rm -rf /
- curl | bash
- wget | sh
- mkfs
- dd if=
- reading private keys
- sudo without approval
- git reset --hard without approval
- git clean -fd without approval

## Memory Rules

Do not write long-term memory directly.

Use:
MemoryProposal → MemoryGovernor → GovernanceDecision → MemoryStore

Every memory must include:
- id
- type
- content
- confidence
- context_tags
- source_event_ids
- conflicts
- version
- status
- created_at
- updated_at

## Testing Rules

Every new module must have tests.

Do not require real API keys.

Do not perform real network calls in tests.

Mock LLM calls.

Mock shell execution except when testing terminal executor.

Run:
- pytest
- ruff check .
- mypy .

## Output After Each Task

After completing any task, report:
1. changed files
2. tests run
3. limitations
4. next smallest step
```

---

# 5. 分阶段 Codex 提示词

以下 prompt 按顺序执行。不要一次性全部喂给 Codex。每次只执行一个阶段。

---

## Phase 0：仓库审计与融合路线

```text
你是 LoopOS 项目的首席架构师。请先不要改业务代码。

背景：
我已经拉取了 OpenHands、LangGraph、Letta、Zep、projectmem 等源码或文档。当前目标不是复制这些项目，而是抽取它们适合 LoopOS 的能力，并通过 adapter、Policy OS、AIL、MCP Tool Hub 融合。

任务：
审计当前仓库，生成 LoopOS 最短可实现路线。

请执行：

1. 浏览根目录结构。
2. 找出第三方源码目录：
   - OpenHands
   - LangGraph
   - Letta
   - Zep
   - projectmem
   - 其他 agent 框架
3. 判断每个目录：
   - 语言
   - 入口
   - 核心能力
   - 可复用模块
   - 不建议复用的部分
4. 找出已有配置：
   - pyproject.toml
   - package.json
   - Cargo.toml
   - Makefile
   - docker-compose.yml
5. 找出可复用能力：
   - terminal / sandbox execution
   - agent loop
   - graph / state machine
   - memory
   - MCP / tool protocol
   - event log
   - code editing
6. 生成 `docs/repo-audit.md`。

只允许创建或更新：
- docs/repo-audit.md

输出结构：

# Repo Audit

## Directory Map
## Detected Third-party Projects
## Runtime and Language Summary
## Reusable Components
## Risks
## Recommended Fusion Strategy
## Shortest MVP Path
## First 15 Implementation Tasks

不要修改业务代码。
```

---

## Phase 1：Open Source 能力抽取

```text
你是开源 agent 框架分析专家。请基于当前仓库中的 OpenHands、LangGraph、Letta、Zep、projectmem 源码或文档，提取可用于 LoopOS 的架构模式。

要求：
不要复制大段第三方代码。只提取模式、接口设计、可复用点和 adapter 策略。

请分别分析：

1. OpenHands：
   - sandbox / terminal execution
   - action / observation model
   - workspace / file editing
   - agent runtime
   - code editing workflow

2. LangGraph：
   - state graph
   - node / edge
   - checkpoint
   - long-running stateful loop
   - graph backend 适配方式

3. Letta：
   - working memory
   - archival memory
   - agent state
   - tool calling
   - long-term memory pattern

4. Zep：
   - temporal memory
   - context graph
   - user/session memory
   - retrieval ranking

5. projectmem：
   - event-sourced memory
   - judgement layer
   - pre-action gate
   - compact context injection
   - repeated failure prevention

请创建：
- docs/source-extraction.md

输出结构：

# Source Extraction for LoopOS

## OpenHands
### Reusable Ideas
### Adapter Strategy
### Risks

## LangGraph
...

## Unified Fusion Recommendation
## What LoopOS Should Build Itself
## What LoopOS Should Wrap via Adapter
## What LoopOS Should Avoid
```

---

## Phase 2：LoopOS 融合架构设计

```text
你是 LoopOS 的系统架构师。请基于 docs/repo-audit.md 和 docs/source-extraction.md，设计 LoopOS 的融合版 MVP 架构。

必须融合以下核心概念：

1. AIL：Agent Internal Language
2. AI-ISA：结构化指令集
3. MCP Tool Hub：工具注册、路由、调用
4. Policy OS：行为、工具、安全、记忆、输出策略
5. Terminal-native Execution
6. Memory Governance
7. Skill Learning
8. Context Compiler
9. OpenHands Adapter
10. LangGraph Optional Backend
11. Letta / Zep / projectmem Memory Ideas

约束：

- MVP Python-first。
- 不做 WebUI。
- CLI/FLI 为主。
- 不真实调用 LLM。
- 不真实调用网络。
- 不执行危险命令。
- 先实现 mock policy / mock executor。
- 所有数据结构 Pydantic 化。
- 所有核心逻辑可测试。

请创建：
- docs/architecture-fusion-mvp.md

内容必须包括：

1. Goals / Non-goals
2. System Overview
3. Module Structure
4. AIL Object Model
5. AI-ISA Instruction Set
6. MCP Tool Hub Design
7. Policy OS Design
8. Memory Governance Design
9. Context Compiler Design
10. Skill Learning Design
11. Loop Lifecycle
12. Terminal Safety
13. Adapter Strategy
14. Testing Strategy
15. MVP Milestones
16. Alpha Milestones
17. Risks and Mitigations

不要改业务代码。
```

---

## Phase 3：创建融合版代码骨架

```text
你是 Python 工程师。请基于 docs/architecture-fusion-mvp.md 创建 LoopOS 融合版代码骨架。

要求：
- 只创建结构、模型占位、接口和 TODO。
- 不实现复杂逻辑。
- Python 3.11+。
- Pydantic v2。
- CLI 用 Typer。
- 输出用 Rich。
- 测试用 pytest。
- 预留 ruff / mypy。

请创建或更新：

loopos/
  ail/
    __init__.py
    base.py
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
    codec.py
    validators.py

  core/
    __init__.py
    loop_engine.py
    transition.py
    context_compiler.py
    policy.py
    graph_loop.py

  agents/
    __init__.py
    intent_compiler.py
    planner.py
    executor_agent.py
    critic.py
    memory_writer.py
    skill_extractor.py
    renderer.py

  mcp/
    __init__.py
    types.py
    registry.py
    router.py
    adapters.py

  execution/
    __init__.py
    terminal.py
    permissions.py
    sandbox.py

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

  integrations/
    __init__.py
    openhands_adapter.py
    langgraph_adapter.py
    letta_adapter.py
    zep_adapter.py
    projectmem_adapter.py

  cli/
    __init__.py
    app.py

tests/
  test_imports.py

pyproject.toml
README.md

完成标准：
1. `python -m loopos.cli.app --help` 可运行。
2. `pytest` 通过。
3. 所有模块可 import。
4. README 说明 LoopOS 是 AIL + MCP + Policy OS + Terminal Loop。

不要接入真实 LLM。
不要执行真实 shell。
```

---

## Phase 4：实现 AIL 核心对象

```text
你是编译器和虚拟机架构师。请实现 LoopOS 的 AIL 核心对象模型。

目标文件：
- loopos/ail/base.py
- loopos/ail/goal.py
- loopos/ail/state.py
- loopos/ail/instruction.py
- loopos/ail/observation.py
- loopos/ail/evaluation.py
- loopos/ail/event.py
- loopos/ail/memory.py
- loopos/ail/skill.py
- loopos/ail/preference.py
- loopos/ail/render.py
- loopos/ail/codec.py
- loopos/ail/validators.py
- tests/ail/test_ail_core.py

要求：
使用 Pydantic v2。

必须实现：

1. AILGoal
2. AILState
3. AILInstruction
4. AILObservation
5. AILEvaluation
6. AILEvent
7. AILMemory
8. AILSkill
9. AILPreference
10. RenderSpec

AI-ISA op 至少支持：

- GOAL.SET
- CTX.COMPILE
- PLAN.CREATE
- PLAN.UPDATE
- TOOL.CALL
- TERM.EXEC
- STATE.PATCH
- EVAL.SCORE
- MEM.PROPOSE
- MEM.COMMIT
- SKILL.EXTRACT
- SKILL.APPLY
- LOOP.CONTINUE
- LOOP.REPAIR
- LOOP.REPLAN
- LOOP.HALT

每条 AILInstruction 必须包含：

- id
- run_id
- op
- args
- reason
- safety
- expect
- policy
- created_at

Reason:
- code
- evidence
- confidence

Safety:
- risk: low/medium/high/blocked
- requires_approval
- blocked_patterns

Expectation:
- success
- fail
- timeout_seconds

实现：
- to_json
- from_json
- validate_instruction
- json roundtrip

测试：
- 合法 instruction 通过
- 非法 op 失败
- TERM.EXEC 必须有 cmd
- TOOL.CALL 必须有 tool
- LOOP.HALT 必须有 reason
- JSON roundtrip
- blocked risk 必须 requires_approval 或直接 blocked

不要接入 LLM。
不要执行 shell。
```

---

## Phase 5：实现 Policy OS MVP

```text
你是 LoopOS Policy OS 工程师。请实现 Policy OS MVP。

目标：
实现一个可加载 YAML Policy Pack、匹配 PolicyContext、输出 PolicyDecision 的策略引擎。

创建或更新：

loopos/policy_os/
  models.py
  loader.py
  registry.py
  matcher.py
  conflict_resolver.py
  engine.py
  compiler.py
  audit.py

policies/
  core/behavior.yaml
  tools/terminal_safety.yaml
  tools/tool_routing.yaml
  tools/mcp_policy.yaml
  memory/memory_governance.yaml
  memory/memory_applicability.yaml
  renderer/renderer_style.yaml
  optimization/context_budget.yaml
  optimization/loop_convergence.yaml
  safety/prompt_injection.yaml

tests/policy_os/
  test_loader.py
  test_matcher.py
  test_engine_terminal.py
  test_engine_memory.py
  test_engine_tool_routing.py
  test_policy_compiler.py

要求：
1. 使用 Pydantic v2。
2. YAML 用 PyYAML。
3. 支持 condition:
   - all
   - any
   - not
   - field
   - equals
   - in
   - regex
   - exists
   - lt
   - gt
4. 支持 action:
   - allow
   - block
   - require_approval
   - prefer_tool
   - prefer_tools
   - forbid_tool
   - inject_constraint
   - add_renderer_hint
   - exclude_memory
   - reject_memory
   - mark_needs_review
   - force_replan
   - terminate
5. block 优先级最高。
6. safety 高于 user preference。
7. 输出 PolicyDecision。
8. 每次 decision 可写 audit event。
9. 不调用 LLM。
10. 不执行真实 terminal。

验收：
- 输入 cmd="rm -rf /" 输出 allowed=false。
- 输入 cmd="pytest -q" 输出 allowed=true 或 low risk。
- 输入 memory proposal confidence=0.2 输出 reject。
- 输入 task.domain=codebase 输出 preferred_tools 包含 git.status 或 repo.inspect。
```

---

## Phase 6：实现 MCP-like Tool Hub

```text
你是 MCP / Tool Protocol 工程师。请实现 LoopOS 的 MCP-like Tool Hub MVP。

目标：
所有工具都通过统一 ToolSpec、ToolCall、ToolResult、ToolRouter 调用。MVP 不要求真实 MCP 协议，但接口必须可替换为真实 MCP SDK。

目标文件：
- loopos/mcp/types.py
- loopos/mcp/registry.py
- loopos/mcp/router.py
- loopos/mcp/adapters.py
- tests/mcp/test_tool_registry.py
- tests/mcp/test_tool_router.py

实现：

ToolSpec:
- name
- description
- input_schema
- output_schema
- risk_level
- requires_approval
- tags
- handler_name

ToolCall:
- call_id
- tool
- input
- instruction_id
- policy_decision_id

ToolResult:
- call_id
- tool
- ok
- output
- error
- artifacts
- raw_ref
- created_at

ToolRegistry:
- register
- list_tools
- get
- has

ToolRouter:
- route(Instruction, PolicyDecision)
- call(ToolCall)
- normalize_result

内置 mock tools:
- terminal.exec
- file.read
- file.write
- git.status
- git.diff

要求：
1. ToolRouter 调用前必须检查 PolicyDecision。
2. blocked decision 不允许调用。
3. high risk 且未 approval 不允许调用。
4. ToolResult 必须可转成 AILObservation。
5. 测试不能执行真实危险命令。
```

---

## Phase 7：实现 Terminal Executor 与权限策略

```text
你是安全执行系统工程师。请实现 Terminal Executor 和 Permission Policy。

目标文件：
- loopos/execution/terminal.py
- loopos/execution/permissions.py
- loopos/execution/sandbox.py
- tests/execution/test_terminal.py
- tests/execution/test_permissions.py

TerminalExecutor.execute 返回：
- stdout
- stderr
- return_code
- duration_ms
- timed_out
- blocked
- risk_level
- reason_codes
- command
- cwd

PermissionPolicy:
- allowlist_paths
- denylist_patterns
- require_approval_patterns
- max_timeout_seconds
- network_allowed
- non_interactive

默认阻止：
- rm -rf /
- curl | bash
- wget | sh
- mkfs
- dd if=
- reading ~/.ssh/private keys
- sudo without approval
- chmod -R 777
- kill -9 -1
- git config --global

高风险需要 approval：
- git reset --hard
- git clean -fd
- rm -rf relative path
- chmod recursive
- package install
- docker privileged

低风险：
- ls
- pwd
- git status
- git diff
- pytest
- rg
- grep
- cat workspace file

要求：
1. 所有命令先过 PermissionPolicy。
2. blocked 永不执行。
3. high risk 在 non_interactive 模式下不执行。
4. 支持 timeout。
5. cwd 必须在 workspace 内。
6. stdout/stderr 捕获。
7. 输出转换为 AILObservation。

测试：
- echo hello 成功
- pytest --version 可 mock 或安全执行
- rm -rf / 被阻止
- curl | bash 被阻止
- timeout 生效
- cwd escape 被阻止
```

---

## Phase 8：实现 State Machine Loop Engine

```text
你是 runtime engineer。请实现 LoopOS 的状态机 LoopEngine。

目标文件：
- loopos/core/loop_engine.py
- loopos/core/transition.py
- loopos/core/policy.py
- tests/core/test_loop_engine.py

LoopEngine 每轮流程：

1. ContextCompiler.compile(state)
2. Planner.next_instruction(context)
3. AIL validators validate instruction
4. PolicyEngine.evaluate(PolicyContext)
5. PreActionGate.check
6. ToolRouter.route
7. ToolRouter.call
8. ObservationNormalizer
9. Critic.evaluate
10. StateTransition.apply
11. EventLog.append
12. MemoryWriter.propose
13. MemoryGovernor.evaluate
14. SkillExtractor.extract if success
15. LoopDecision decide continue / repair / replan / halt

MVP 中：
- Planner 用 DeterministicDemoPlanner。
- ToolRouter 用 mock tools。
- Critic 用规则评估。
- MemoryWriter 可先返回空。
- SkillExtractor 可先返回空。

必须支持：
- max_steps
- no_progress guard
- repeated command guard
- blocked command guard
- resume state 预留

测试：
1. deterministic loop 成功结束。
2. max_steps 触发失败。
3. blocked command 不执行。
4. repeated command 触发 replan 或 halt。
5. 每轮写 event log。
```

---

## Phase 9：实现 Memory OS

```text
你是长期记忆系统工程师。请实现 LoopOS Memory OS MVP。

目标文件：
- loopos/memory/event_log.py
- loopos/memory/state_store.py
- loopos/memory/belief_store.py
- loopos/memory/skill_store.py
- loopos/memory/preference_store.py
- tests/memory/test_event_log.py
- tests/memory/test_state_store.py
- tests/memory/test_belief_store.py
- tests/memory/test_skill_store.py
- tests/memory/test_preference_store.py

存储：
- MVP 使用 `.loopos/`。
- EventLog 用 JSONL。
- StateStore 用 JSON。
- Belief/Skill/Preference 用 JSONL 或 SQLite，优先简单可测。

Event:
- event_id
- run_id
- step
- kind
- payload
- created_at

Belief:
- id
- content
- confidence
- context_tags
- source_event_ids
- conflicts
- version
- status
- created_at
- updated_at

Skill:
- id
- name
- trigger
- steps
- success_count
- failure_count
- success_rate
- source_event_ids
- created_at
- updated_at

Preference:
- id
- category
- value
- confidence
- context_tags
- source_event_ids
- status
- created_at
- updated_at

实现：
- append_event
- load_events
- save_state/load_state
- add/list/update belief
- add/list/update skill
- add/list/update preference

测试：
- JSON roundtrip
- 写入读取
- confidence 范围
- skill success_rate
- event order
```

---

## Phase 10：实现 Memory Governance

```text
你是 Memory Governance 架构师。请实现长期记忆写入治理。

目标文件：
- loopos/memory/governance.py
- tests/memory/test_governance.py

实现：

MemoryProposal:
- proposal_id
- memory_type: belief/skill/preference/failure_pattern/tool_profile
- content
- confidence
- source_event_ids
- context_tags
- evidence
- proposed_by
- created_at

GovernanceDecision:
- decision_id
- accepted
- status: active/rejected/needs_review/conflict
- confidence_adjustment
- reason_codes
- conflicts
- normalized_content
- write_as

MemoryGovernor:
- evaluate_proposal(proposal, existing_memories)
- normalize_content
- detect_duplicate
- detect_conflict
- adjust_confidence

规则：
1. confidence < 0.4 rejected。
2. 没有 source_event_ids needs_review。
3. duplicate similarity > 0.85 dedupe。
4. conflict 不覆盖旧 memory，而是创建 conflict link。
5. preference 必须有 context_tags。
6. 自动写入 confidence 上限 0.9。
7. 敏感或高影响记忆默认 needs_review。

测试：
- low confidence reject
- missing evidence needs_review
- duplicate detected
- conflict detected
- preference without context rejected
- accepted normalized
```

---

## Phase 11：实现 Context Compiler

```text
你是 Context Compiler 设计师。请实现 LoopOS 的上下文编译器。

目标文件：
- loopos/core/context_compiler.py
- tests/core/test_context_compiler.py

目标：
把 state + relevant memories + skills + preferences + active policies 编译成短小结构化 AgentContext，避免上下文污染。

AgentContext:
- ctx_id
- goal_summary
- current_status
- constraints
- relevant_beliefs
- relevant_skills
- user_preferences
- recent_errors
- allowed_tools
- active_policy_constraints
- next_step_hints
- token_budget_estimate

实现：
- rank_by_relevance(memory, task_tags)
- rank_by_confidence
- rank_by_recency
- include top-k
- raw outputs by reference
- full history excluded by default
- conflicting memories marked not deleted
- policy constraints included as compact dict

要求：
1. 不输出长自然语言。
2. 不包含 full raw stdout。
3. 不包含所有历史。
4. token_budget 超限时丢弃低置信/低相关内容。
5. 输出可 JSON 序列化。

测试：
- relevance ranking
- token budget truncation
- conflict memory marked
- low confidence excluded
- skill reference included
```

---

## Phase 12：实现 Skill Learning

```text
你是 Skill Learning 系统工程师。请实现从成功执行轨迹中提取 Skill 的 MVP。

目标文件：
- loopos/agents/skill_extractor.py
- loopos/memory/skill_store.py
- tests/agents/test_skill_extractor.py

输入：
- run_id
- goal
- event sequence
- final evaluation

输出：
SkillProposal:
- name
- trigger
- steps
- source_event_ids
- success_signal
- limitations
- confidence

规则：
1. 只有 final evaluation succeeded 才提取 skill。
2. 至少 2 个有效 action event。
3. steps 必须是结构化动作，不是自然语言长段落。
4. trigger 来自 goal tags、task tags 或 error pattern。
5. skill 写入前必须经过 MemoryGovernor。
6. 相似 skill 应更新 stats，不重复创建。

测试：
- 成功 trace 提取 skill
- 失败 trace 不提取
- 单步 trace 不提取
- skill proposal 经过 governance
- duplicate skill update stats
```

---

## Phase 13：实现 PreActionGate

```text
你是 projectmem-style judgement layer 工程师。请实现 PreActionGate。

目标文件：
- loopos/memory/pre_action_gate.py
- tests/memory/test_pre_action_gate.py

目标：
在执行 instruction 前，根据事件历史、失败模式、技能库和 Policy OS 决策进行预判。

PreActionGate 输入：
- state
- instruction
- recent_events
- relevant_beliefs
- relevant_skills
- policy_decision

GateDecision:
- allow
- block
- warn
- substitute_skill
- require_replan
- reason_codes

规则：
1. 如果 policy_decision blocked，则 block。
2. 如果同一命令失败 2 次，则 require_replan。
3. 如果 memory 表示此方法在类似上下文失败过，则 warn 或 require_replan。
4. 如果存在高成功率 skill 匹配当前任务，则 suggest substitute_skill。
5. blocked terminal 命令不能重试。

测试：
- policy blocked → gate block
- repeated failed command → require_replan
- relevant skill → substitute_skill suggested
- low confidence memory ignored
- safe action allowed
```

---

## Phase 14：实现 Renderer 与用户偏好

```text
你是 Renderer 和个性化输出工程师。请实现 LoopOS 的最终输出渲染层。

目标文件：
- loopos/agents/renderer.py
- loopos/ail/render.py
- loopos/memory/preference_store.py
- tests/agents/test_renderer.py

Renderer 输入：
- final state
- evaluation
- artifacts
- render_spec
- user_preferences
- policy_decision.renderer_hints

RenderSpec:
- language
- format
- verbosity
- sections
- code_blocks
- tables
- tone

要求：
1. Renderer 是唯一允许输出长自然语言的模块。
2. 内部 agent 不输出面向用户的长文本。
3. 用户明确要求优先于偏好。
4. 偏好必须 context-aware。
5. 技术方案默认支持 markdown。
6. 如果创建文件，输出文件路径/链接。
7. 不暴露 memory 检索机制。
8. 不暴露内部 chain-of-thought。
9. 可以输出执行摘要、限制、下一步。

测试：
- technical_plan 输出 markdown sections
- simple_status 输出简洁
- explicit user instruction overrides preference
- memory mechanics phrases removed
- artifact created includes link hint
```

---

## Phase 15：实现 CLI / FLI

```text
你是 CLI 产品工程师。请实现 LoopOS 的 FLI/CLI MVP。

目标文件：
- loopos/cli/app.py
- tests/cli/test_cli.py

技术：
- Typer
- Rich

命令：

1. loopos run "goal"
   - 启动新任务

2. loopos resume RUN_ID
   - 恢复任务

3. loopos status RUN_ID
   - 查看状态

4. loopos history RUN_ID
   - 查看事件

5. loopos skills
   - 列出 skills

6. loopos memory
   - 列出 active beliefs/preferences

7. loopos policy list
   - 列出 policy packs

8. loopos policy explain --phase TERM.EXEC --cmd "rm -rf /"
   - 解释 policy decision

9. loopos tools
   - 列出 MCP tools

参数：
- --dry-run
- --max-steps
- --yes
- --verbose
- --workspace

UI 要求：
- Rich panel 显示 run_id、goal、status、progress。
- 每一步显示 op、tool、result summary、policy decision。
- 默认不展示长 stdout。
- --verbose 展示详细输出。
- blocked 命令显示 reason_codes。
- high risk 命令在 non-interactive 下不执行。

测试：
- help
- run dry-run
- policy explain dangerous command
- status nonexistent run
- tools list
```

---

## Phase 16：OpenHands Adapter

```text
你是 OpenHands 集成工程师。请为 LoopOS 实现 OpenHands Adapter。

目标：
LoopOS 不直接耦合 OpenHands 内部实现，而是通过 adapter 调用 sandbox/runtime 能力。

目标文件：
- loopos/integrations/openhands_adapter.py
- tests/integrations/test_openhands_adapter.py
- docs/integrations-openhands.md

任务：
1. 查找当前仓库中 OpenHands 的 SDK 或 runtime 入口。
2. 分析它如何执行 command、读写文件、应用 patch、管理 workspace。
3. 实现 OpenHandsAdapter：
   - is_available()
   - execute_command(cmd, cwd, timeout)
   - read_file(path)
   - write_file(path, content)
   - apply_patch(patch)
4. 如果不可用，实现 graceful fallback。
5. Adapter 输出统一 ToolResult 或 AILObservation。
6. 不复制大段 OpenHands 代码。
7. 文档说明如何启用 adapter。

测试：
- unavailable 时不崩溃
- fallback mock works
- interface returns normalized observation
```

---

## Phase 17：LangGraph Backend

```text
你是 LangGraph 集成工程师。请为 LoopOS 增加可选 LangGraph backend。

目标文件：
- loopos/integrations/langgraph_adapter.py
- loopos/core/graph_loop.py
- tests/integrations/test_langgraph_adapter.py
- docs/integrations-langgraph.md

目标：
将 LoopOS loop 表达为 state graph：

Nodes:
- compile_context
- plan_instruction
- policy_check
- pre_action_gate
- route_tool
- execute_tool
- normalize_observation
- evaluate
- transition_state
- govern_memory
- extract_skill
- decide_next

Edges:
- continue -> plan_instruction
- repair -> plan_instruction with repair flag
- replan -> compile_context
- blocked -> halt or approval
- success -> halt

要求：
1. LangGraph 是 optional dependency。
2. 未安装时测试 skip，不影响核心。
3. State schema 与 LoopEngine 兼容。
4. docs 说明 LoopEngine 和 GraphLoop 的区别。

测试：
- optional import
- deterministic graph 可跑通
```

---

## Phase 18：Letta / Zep / projectmem Memory Enhancement

```text
你是 agent memory 架构师。请基于 Letta、Zep、projectmem 的可借鉴模式增强 LoopOS Memory OS。

不要复制大段第三方代码。

目标文件：
- loopos/memory/retrieval.py
- loopos/memory/pre_action_gate.py
- docs/memory-fusion-design.md
- tests/memory/test_retrieval.py
- tests/memory/test_pre_action_gate.py

设计吸收：

Letta：
- working memory vs archival memory
- memory block
- agent state

Zep：
- temporal memory
- context graph
- session/user scoped memory

projectmem：
- event-sourced memory
- pre-action judgement
- compact context injection
- repeated failure prevention

实现：
MemoryRetriever:
- retrieve(query_tags, limit, min_confidence)
- rank by confidence + recency + tag overlap
- conflict-aware output

PreActionGate:
- repeated failure detection
- skill suggestion
- memory-based warning
- policy blocked passthrough

测试：
- low confidence ignored
- recency affects rank
- tag overlap affects rank
- conflicting memory marked
- repeated failure blocked
```

---

## Phase 19：Benchmark 与评测

```text
你是 AI agent benchmark engineer。请为 LoopOS 建立 benchmark 任务集。

目标文件：
- benchmarks/tasks/*.json
- loopos/eval/runner.py
- loopos/eval/metrics.py
- docs/benchmarks.md
- tests/eval/test_runner.py
- tests/eval/test_metrics.py

任务类型：
1. file creation
2. simple script execution
3. safe terminal blocking
4. bug fix
5. test repair
6. git workflow
7. memory recall
8. repeated failure avoidance
9. skill reuse
10. policy routing

Task schema:
- id
- name
- goal
- workspace_setup
- expected_files
- expected_events
- success_checks
- max_steps
- tags

Metrics:
- success_rate
- steps_to_success
- command_count
- blocked_dangerous_actions
- repeated_failure_count
- skill_reuse_count
- policy_block_accuracy
- token_estimate optional

要求：
- 可用 mock backend 跑。
- 不依赖真实 LLM。
- 输出 JSON report。
- docs 说明如何添加 benchmark。
```

---

## Phase 20：Prompt Distiller

```text
你是 Prompt Distiller 工程师。请实现一个把大型模型系统提示词蒸馏成 LoopOS Policy Pack 的工具原型。

背景：
我们不把大型提示词原样嵌入 LoopOS，而是提取可泛化规则，生成 Policy YAML 草稿。

目标文件：
- tools/prompt_distiller/__init__.py
- tools/prompt_distiller/section_parser.py
- tools/prompt_distiller/rule_candidate.py
- tools/prompt_distiller/classifier.py
- tools/prompt_distiller/yaml_writer.py
- tools/prompt_distiller/cli.py
- tests/prompt_distiller/test_section_parser.py
- tests/prompt_distiller/test_classifier.py
- tests/prompt_distiller/test_yaml_writer.py
- docs/prompt-distiller.md

功能：
1. 读取 markdown/txt prompt。
2. 按 XML-like tags、markdown headings、空行分 section。
3. 提取规则候选。
4. 分类：
   - behavior
   - tool_routing
   - mcp_policy
   - memory_applicability
   - memory_governance
   - safety
   - terminal_safety
   - file_policy
   - renderer_style
   - context_budget
   - ignore
5. 删除 ignore 类：
   - 外部模型身份
   - 外部产品介绍
   - 平台专属路径
   - 不可泛化工具
6. 输出 YAML policy pack 草稿。
7. 输出 distillation report。

要求：
- MVP 不调用 LLM。
- 规则基于关键词和 section 分类。
- 输出必须标记 source_section。
- 草稿需要人工 review。
```

---

## Phase 21：测试体系

```text
你是测试架构师。请为 LoopOS 建立完整测试体系。

目标文件：
- pyproject.toml
- Makefile 或 justfile
- .github/workflows/ci.yml
- docs/testing.md
- tests/fixtures/
- tests/golden/

测试层级：
1. unit tests
2. integration tests
3. golden trace tests
4. policy tests
5. safety tests
6. CLI smoke tests
7. benchmark tests

实现：
- deterministic mock planner
- mock terminal executor
- temporary workspace fixture
- golden event log comparison
- policy decision snapshots
- no real API key
- no real network

命令：
- make test
- make lint
- make typecheck
- make ci

CI：
- Python 3.11 / 3.12
- pytest
- ruff
- mypy

要求：
- 所有核心模块都有测试。
- 所有危险操作测试不能真实执行。
```

---

## Phase 22：重构审查

```text
你是资深 Python 架构师。请审查 LoopOS 当前代码并提出最小重构。

任务：
1. 找出循环依赖。
2. 找出过大的模块。
3. 找出没有测试的核心路径。
4. 找出类型不清晰的 API。
5. 找出安全风险。
6. 找出绕过 Policy OS 的路径。
7. 找出绕过 Memory Governance 的路径。
8. 找出内部自然语言污染路径。
9. 找出 AGENTS.md 不一致处。

请先生成：
- docs/refactor-review.md

然后只做低风险重构：
- 不改变公开 CLI 行为。
- 不改变 AIL schema。
- 不改变存储格式。
- 不删除测试。
- 不引入大型依赖。

完成后运行：
- pytest
- ruff
- mypy

输出：
- changed files
- why changed
- tests run
- remaining risks
```

---

## Phase 23：开源发布文档

```text
你是开源项目维护者。请为 LoopOS 准备开源发布文档。

目标文件：
- README.md
- docs/quickstart.md
- docs/architecture.md
- docs/ail.md
- docs/policy-os.md
- docs/mcp-tool-hub.md
- docs/memory-governance.md
- docs/safety.md
- docs/benchmarks.md
- docs/contributing.md
- CHANGELOG.md

README 必须包含：
1. What is LoopOS
2. Why state-machine agent
3. Why AIL
4. Why Policy OS
5. Why MCP Tool Hub
6. Installation
7. Quickstart
8. Example
9. Architecture
10. Safety model
11. Roadmap
12. Inspired by
13. Contributing

注意：
- 不要声称超过 Claude Code / Codex / OpenHands / Hermes / 小龙虾，除非有 benchmark。
- 使用 “inspired by”。
- 标明第三方 license 需要人工确认。
- 不要包含外部模型身份声明。
```

---

# 6. 快速总控 Prompt

如果你想让 Codex 从现在开始按阶段执行，用这个总控 prompt：

```text
你是 LoopOS 项目的首席 AI 工程师。

目标：
从当前仓库构建一个 Terminal-native、MCP-compatible、AIL-driven、Policy-OS-governed、Memory-governed、Self-improving 的 CLI Agent Runtime。

我已经准备了这些设计：
- AIL：Agent 内部结构化语言
- MCP Tool Hub：工具注册与调用协议
- Policy OS：行为、工具、安全、记忆、输出治理层
- Memory Governance：长期记忆写入审批
- Skill Learning：从成功轨迹提取可复用技能
- Context Compiler：压缩上下文，降低 token 和污染
- OpenHands / LangGraph / Letta / Zep / projectmem：只作为可借鉴和可 adapter 化的开源底座

核心原则：
1. 不做 chatbot。
2. 内部不用长自然语言交流。
3. 内部使用 AIL：Goal / State / Instruction / Observation / Evaluation / Event / Memory / Skill / RenderSpec。
4. 所有工具调用走 MCP-like Tool Hub。
5. 所有 terminal 命令走 Policy OS + Permission Policy。
6. 所有长期记忆写入走 Memory Governance。
7. 所有输出由 Renderer 统一渲染。
8. MVP Python-first，不做 WebUI。
9. 测试不依赖真实 API key。
10. 不真实执行危险命令。

工作方式：
每次只做一个最小阶段。
每次先说明计划，再改代码。
每次添加测试。
每次输出 changed files、tests run、limitations、next step。

现在执行 Phase 0：仓库审计。不要改业务代码，只创建 docs/repo-audit.md。
```

---

# 7. 单次任务模板

每次让 Codex 做具体任务，可以套这个：

```text
你是 LoopOS 项目的 coding agent。

任务名称：
[填写任务名]

背景：
LoopOS 是 AIL + MCP + Policy OS + Memory Governance 的 Terminal-native Agent Runtime。
本任务属于 [AIL / MCP / Policy OS / Memory / Loop Engine / CLI / Integration] 模块。

允许修改：
- [文件或目录]

禁止修改：
- [文件或目录]

具体要求：
1. ...
2. ...
3. ...

完成标准：
1. ...
2. ...
3. ...

测试命令：
pytest [具体测试文件]
ruff check .
mypy loopos

限制：
- 不要接入真实 LLM。
- 不要真实调用网络。
- 不要执行危险命令。
- 不要绕过 Policy OS。
- 不要绕过 Memory Governance。
- 不要把长自然语言作为内部 agent message。

输出：
1. 修改摘要
2. 测试结果
3. 已知限制
4. 下一步建议

请先简短说明实现计划，然后再修改代码。
```

---

# 8. Debug Prompt

```text
你是 LoopOS debugging expert。当前出现错误，请最小修复。

错误信息：
[粘贴 traceback / pytest output]

要求：
1. 定位根因。
2. 不重构无关代码。
3. 添加回归测试。
4. 不改变公开 API，除非错误来自 API 设计。
5. 修复后运行相关测试。

重点检查：
- 是否违反 AIL schema
- 是否绕过 Policy OS
- 是否绕过 Memory Governance
- 是否执行了真实危险命令
- 是否把自然语言塞进内部状态

允许修改：
[列文件]

禁止修改：
[列文件]

输出：
- root cause
- changed files
- tests run
- why fix is safe
```

---

# 9. Code Review Prompt

```text
你是严格的 LoopOS 代码审查员。请审查当前 diff，不要改代码。

重点检查：
1. 是否违反 AGENTS.md。
2. 是否绕过 AIL。
3. 是否绕过 Policy OS。
4. 是否绕过 Memory Governance。
5. 是否绕过 MCP Tool Hub。
6. 是否引入不安全 terminal execution。
7. 是否让 LLM 自由文本直接驱动 runtime。
8. 是否缺测试。
9. 是否引入大型依赖。
10. 是否破坏 schema 兼容性。
11. 是否有 license 风险。
12. 是否有上下文污染风险。

输出：
- docs/reviews/review-[date].md

格式：
# Review

## Summary
## Blocking Issues
## Non-blocking Issues
## Safety Concerns
## Memory Concerns
## Policy OS Concerns
## AIL Concerns
## Test Gaps
## Suggested Fixes
```

---

# 10. 最短实现路线

如果目标是 7-14 天出 MVP，顺序应该是：

```text
Day 1:
- AGENTS.md
- repo audit
- source extraction
- architecture-fusion-mvp.md

Day 2:
- code skeleton
- AIL core models

Day 3:
- Policy OS MVP
- terminal_safety policy

Day 4:
- MCP Tool Hub mock
- Terminal Executor safe mode

Day 5:
- LoopEngine deterministic demo
- EventLog + StateStore

Day 6:
- Memory Governance
- Context Compiler

Day 7:
- CLI run/status/history/policy explain
- tests and README

Day 8-10:
- Skill Learning
- PreActionGate
- Tool Routing policy
- Renderer policy

Day 11-14:
- OpenHands adapter
- LangGraph optional backend
- Letta/Zep/projectmem memory enhancements
- benchmark
```

---

# 11. 判断 MVP 是否成立

MVP 不需要很强模型，但必须能跑通：

```bash
loopos run "创建 hello.py，运行它，并确认输出 hello" --dry-run
```

预期内部流程：

```text
Goal
→ AILGoal
→ AgentContext
→ Policy OS
→ AILInstruction file.write
→ ToolResult
→ Observation
→ State patch
→ AILInstruction terminal.exec
→ Policy OS terminal safety
→ ToolResult
→ Evaluation success
→ EventLog
→ SkillProposal
→ MemoryGovernance
→ Renderer
```

MVP 成立的标准：

```text
1. 内部没有长自然语言 agent-to-agent 通信。
2. 工具调用经过 MCP Tool Hub。
3. terminal 命令经过 Policy OS。
4. 长期记忆写入经过 Memory Governance。
5. event log 可回放。
6. CLI 能显示每一步。
7. pytest 通过。
8. 危险命令被阻止。
```

---

# 12. 最终目标

最终 LoopOS 应该从“一个会自动执行任务的 CLI agent”变成：

```text
一个可治理、可测试、可审计、可扩展、可学习的 AI Runtime。
```

它的核心差异不是更长 prompt，而是：

```text
AIL 内部语言
+ MCP 工具协议
+ Policy OS 策略内核
+ Memory Governance 记忆治理
+ Skill Learning 自我增强
+ Context Compiler 上下文压缩
+ Terminal-native 执行
```

这就是比单纯 prompt engineering、普通 AutoGPT loop、普通 workflow agent 更强的地方。

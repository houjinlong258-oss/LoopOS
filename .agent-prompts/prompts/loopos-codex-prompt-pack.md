# LoopOS / AI-ISA Agent OS — Codex 提示词包（从 0 到 MVP 到 Alpha）

> 适用场景：你已经拉下 OpenHands、LangGraph、Letta、Zep、projectmem 等源码，希望用 Codex/Claude Code/Cursor 等 coding agent 辅助快速搭建一个 Terminal-native + MCP + AI-ISA + Memory Governance + Self-improving Loop Agent。
>
> 推荐用法：
>
> 1. 将本文件放入 `docs/codex-prompts.md`。
> 2. 将「00_AGENTS.md 全局项目指令」复制到仓库根目录 `AGENTS.md`。
> 3. 每个阶段单独复制对应 Prompt 给 Codex。
> 4. 每次只让 Codex 做一个边界清晰的任务，不要一次要求它写完整系统。
> 5. 所有实现都要求 Codex：先审计、再计划、再小步修改、再测试、再总结。

---

## 目录

- [0. 总体原则](#0-总体原则)
- [1. 00_AGENTS.md 全局项目指令](#1-00_agentsmd-全局项目指令)
- [2. 01_仓库审计 Prompt](#2-01_仓库审计-prompt)
- [3. 02_开源项目能力抽取 Prompt](#3-02_开源项目能力抽取-prompt)
- [4. 03_目标架构设计 Prompt](#4-03_目标架构设计-prompt)
- [5. 04_创建 LoopOS Core 骨架 Prompt](#5-04_创建-loopos-core-骨架-prompt)
- [6. 05_AI-ISA 指令集实现 Prompt](#6-05_ai-isa-指令集实现-prompt)
- [7. 06_State Machine Loop 实现 Prompt](#7-06_state-machine-loop-实现-prompt)
- [8. 07_Terminal Executor 实现 Prompt](#8-07_terminal-executor-实现-prompt)
- [9. 08_MCP Tool Hub 实现 Prompt](#9-08_mcp-tool-hub-实现-prompt)
- [10. 09_Memory OS 实现 Prompt](#10-09_memory-os-实现-prompt)
- [11. 10_Memory Governance 实现 Prompt](#11-10_memory-governance-实现-prompt)
- [12. 11_Skill Learning 实现 Prompt](#12-11_skill-learning-实现-prompt)
- [13. 12_Context Compiler 实现 Prompt](#13-12_context-compiler-实现-prompt)
- [14. 13_User Preference Model 实现 Prompt](#14-13_user-preference-model-实现-prompt)
- [15. 14_CLI/FLI UI 实现 Prompt](#15-14_clifli-ui-实现-prompt)
- [16. 15_安全与权限模型 Prompt](#16-15_安全与权限模型-prompt)
- [17. 16_集成 OpenHands Prompt](#17-16_集成-openhands-prompt)
- [18. 17_集成 LangGraph Prompt](#18-17_集成-langgraph-prompt)
- [19. 18_借鉴 Letta/Zep/projectmem Prompt](#19-18_借鉴-lettazepprojectmem-prompt)
- [20. 19_测试体系 Prompt](#20-19_测试体系-prompt)
- [21. 20_基准任务与评测 Prompt](#21-20_基准任务与评测-prompt)
- [22. 21_重构与质量提升 Prompt](#22-21_重构与质量提升-prompt)
- [23. 22_文档与开源发布 Prompt](#23-22_文档与开源发布-prompt)
- [24. 23_每日开发循环 Prompt](#24-23_每日开发循环-prompt)
- [25. 24_单次 Codex 任务模板](#25-24_单次-codex-任务模板)
- [26. 25_故障修复 Prompt](#26-25_故障修复-prompt)
- [27. 26_代码审查 Prompt](#27-26_代码审查-prompt)
- [28. 27_PR 描述生成 Prompt](#28-27_pr-描述生成-prompt)
- [29. 28_推荐执行顺序](#29-28_推荐执行顺序)

---

# 0. 总体原则

## 0.1 对 Codex 的任务约束

每次给 Codex 的任务必须满足：

```text
1. 任务边界清晰。
2. 明确输入文件/目录。
3. 明确不允许改哪些东西。
4. 明确完成标准。
5. 明确测试命令。
6. 明确输出格式。
```

不要这样写：

```text
帮我做一个 LoopOS。
```

要这样写：

```text
请在 core/isa.py 中实现 AI-ISA 的 Pydantic 模型，支持 PLAN、CALL_TOOL、OBSERVE、EVALUATE、UPDATE_STATE、STORE_MEMORY、EXTRACT_SKILL、TERMINATE 8 个指令。不要实现 LLM 调用。添加 tests/test_isa.py，运行 pytest。
```

---

## 0.2 项目核心哲学

LoopOS 不是普通聊天 agent，而是：

```text
Natural Language Input
  → Intent Compiler
  → AI-ISA Instruction
  → State Machine
  → MCP / Terminal Tool Call
  → Observation
  → Evaluation
  → Memory Governance
  → Skill Extraction
  → Next Instruction
  → Final Renderer
```

核心目标：

```text
语言只在输入/输出边界存在。
内部尽量使用结构化状态、指令、事件、记忆对象。
```

---

## 0.3 开发顺序

推荐顺序：

```text
1. AGENTS.md
2. repo audit
3. project skeleton
4. AI-ISA schema
5. state manager
6. terminal executor
7. loop engine
8. critic/evaluator
9. event log
10. skill memory
11. memory governance
12. MCP adapter
13. OpenHands integration
14. LangGraph integration
15. Letta/Zep/projectmem style memory upgrades
16. FLI UI polish
17. sandbox/security
18. benchmark
```

---

# 1. 00_AGENTS.md 全局项目指令

将下面内容复制到仓库根目录 `AGENTS.md`。

```markdown
# AGENTS.md — LoopOS Coding Agent Instructions

## Project Identity

You are working on **LoopOS**, a terminal-native, state-machine-driven, self-improving AI agent runtime.

LoopOS combines:
- AI-ISA: a structured instruction set for agent actions.
- State Machine Loop: deterministic execution of instructions.
- MCP Tool Hub: all external tools are accessed through a protocol-like interface.
- Terminal Runtime: shell execution is a first-class tool.
- Memory OS: state, events, beliefs, skills, and user preferences.
- Memory Governance: memory writes must be validated, deduplicated, versioned, and confidence-scored.
- Skill Learning: successful execution traces can be compressed into reusable skills.
- FLI/CLI: no Web UI in MVP.

## Core Principle

Do not build a chatbot.

Build a state-driven runtime.

Natural language may appear at the input/output boundary, but internal agent-to-agent and agent-to-runtime communication must use structured data.

Prefer:
- Pydantic models
- JSON schemas
- typed events
- explicit state transitions
- small deterministic functions

Avoid:
- large prompt blobs embedded in logic
- hidden global state
- unbounded loops
- direct shell execution without permission checks
- memory writes without governance metadata

## Language Choices

Primary implementation:
- Python for core agent loop, AI-ISA, memory, CLI.
- TypeScript later for MCP gateway/event server.
- Rust later for hardened sandbox execution.

MVP must be Python-only unless explicitly requested.

## Architecture Rules

The MVP structure should follow:

```text
loopos/
  cli/
  core/
  agents/
  execution/
  memory/
  mcp/
  integrations/
  tests/
```

The core loop should follow:

```text
Goal
→ Compile/plan next AI-ISA instruction
→ Execute instruction
→ Observe output
→ Evaluate progress
→ Update state
→ Write governed memory/event
→ Continue or terminate
```

## AI-ISA Minimum Instructions

Implement these as typed models:

- PLAN
- CALL_TOOL
- EXEC_TERMINAL
- OBSERVE
- EVALUATE
- UPDATE_STATE
- STORE_MEMORY
- EXTRACT_SKILL
- TERMINATE

Every instruction must include:
- op
- id
- timestamp
- reason_code
- args
- safety
- expected_observation

## Safety Rules

Never add code that executes destructive shell commands without an explicit permission gate.

Dangerous examples:
- rm -rf
- sudo
- chmod -R 777
- curl | bash
- disk formatting
- killing broad process groups
- changing global git config
- network exfiltration

All terminal commands must pass through a permission policy.

## Memory Rules

Memory is not raw text.

Every memory item must include:
- id
- type
- content
- confidence
- source
- created_at
- updated_at
- version
- tags
- conflicts
- status

Global memory writes must go through Memory Governance.

## Testing Rules

For every new module:
- add unit tests
- keep tests deterministic
- avoid real network calls
- mock LLM calls
- mock shell execution unless testing the executor itself

Run:
```bash
pytest
ruff check .
mypy .
```

If tools are missing, document the missing dependency and add it to project config.

## Coding Style

- Prefer small modules.
- Prefer pure functions where possible.
- Use Pydantic for schemas.
- Use pathlib over raw string paths.
- Use structured logging.
- Avoid premature abstractions.
- Keep MVP simple.

## Output Behavior

When completing a task:
1. Summarize changed files.
2. Summarize tests run.
3. List known limitations.
4. Suggest next smallest step.
```

---

# 2. 01_仓库审计 Prompt

用途：让 Codex 先理解当前你拉下来的源码和你的仓库状态。

```text
你是资深架构师和 coding agent。请先不要改代码。

任务：审计当前仓库，判断它是否已经包含 OpenHands、LangGraph、Letta、Zep、projectmem 等源码或子目录，并为 LoopOS 项目制定最短改造路径。

请执行：

1. 浏览根目录结构。
2. 找出所有可能是第三方源码的目录。
3. 判断每个目录的语言、主要入口、核心能力。
4. 找出是否已有 pyproject.toml、package.json、Cargo.toml、Makefile、docker-compose.yml。
5. 找出测试框架。
6. 找出可复用模块：
   - terminal/sandbox execution
   - agent loop
   - graph/state machine
   - memory
   - MCP/tool protocol
   - event/log system
7. 生成一份 `docs/repo-audit.md`。

不要修改业务代码。只允许创建/更新：
- docs/repo-audit.md

输出文档结构：

# Repo Audit

## Directory Map
## Detected Projects
## Language/Runtime Summary
## Reusable Components
## Risk Areas
## Recommended MVP Path
## First 10 Implementation Tasks
```

---

# 3. 02_开源项目能力抽取 Prompt

用途：让 Codex 从 OpenHands、LangGraph、Letta、Zep、projectmem 中抽能力，而不是盲目复制。

```text
你是开源 agent 框架架构分析专家。请分析本仓库中已拉取的 OpenHands、LangGraph、Letta、Zep、projectmem 源码或文档，并提取可复用能力。

重点不是复制代码，而是找到 LoopOS 可以借鉴的架构模式。

请分别分析：

1. OpenHands：
   - agent runtime
   - sandbox/terminal execution
   - file editing
   - tool abstraction
   - event/action/observation model

2. LangGraph：
   - state graph
   - node/edge
   - checkpoint
   - long-running stateful agent pattern

3. Letta：
   - memory model
   - agent state
   - archival/working memory
   - tool calling

4. Zep：
   - memory retrieval
   - temporal/context graph
   - user/session memory design

5. projectmem：
   - event-sourced memory
   - pre-action gate
   - judgement layer
   - compact context injection

请生成：
- `docs/source-extraction.md`

输出格式：

# Source Extraction for LoopOS

## OpenHands
### What to Reuse
### What Not to Reuse
### Integration Strategy

## LangGraph
...

## Unified Design Recommendation
## Shortest Path to MVP
## Components to Build Ourselves
```

不要改代码。
```

---

# 4. 03_目标架构设计 Prompt

用途：让 Codex 基于审计结果形成工程架构文档。

```text
你是 LoopOS 的首席架构师。基于当前仓库和 docs/repo-audit.md、docs/source-extraction.md，设计 LoopOS 的 MVP 架构。

约束：
- MVP 先用 Python。
- 不做 WebUI。
- CLI/FLI 为主。
- 终端执行必须经过 permission policy。
- LLM 调用必须可 mock。
- Memory 先用 SQLite + JSONL，不上复杂服务。
- MCP 先做接口抽象，不要求真实完整协议。
- AI-ISA 是核心，LLM 输出必须被解析为结构化 instruction。

请创建：
- docs/architecture-mvp.md

内容必须包含：

1. Goals / Non-goals
2. System Overview
3. Module Structure
4. AI-ISA Design
5. State Schema
6. Event Log Schema
7. Memory Schema
8. Loop Lifecycle
9. Terminal Execution Safety
10. MCP Abstraction
11. Testing Strategy
12. Milestone Plan
13. Risks and Mitigations

不要改业务代码。
```

---

# 5. 04_创建 LoopOS Core 骨架 Prompt

用途：创建项目结构。

```text
你是 Python 工程师。请基于 docs/architecture-mvp.md 创建 LoopOS MVP 的代码骨架。

要求：
- 不实现复杂逻辑。
- 先创建模块、类、接口、空实现和 TODO。
- 使用 Python 3.11+。
- 使用 Pydantic v2。
- CLI 用 Typer。
- 输出用 Rich。
- 测试用 pytest。
- 格式化/静态检查预留 ruff/mypy。

请创建或更新：

loopos/
  __init__.py
  cli/
    __init__.py
    app.py
  core/
    __init__.py
    isa.py
    state.py
    loop_engine.py
    policy.py
  agents/
    __init__.py
    planner.py
    critic.py
    renderer.py
  execution/
    __init__.py
    terminal.py
    permissions.py
  memory/
    __init__.py
    event_log.py
    state_store.py
    belief_store.py
    skill_store.py
    governance.py
  mcp/
    __init__.py
    types.py
    router.py
  integrations/
    __init__.py
    openhands_adapter.py
    langgraph_adapter.py
    letta_adapter.py
    zep_adapter.py
    projectmem_adapter.py
tests/
  test_imports.py
pyproject.toml
README.md

完成标准：
1. `python -m loopos.cli.app --help` 可运行。
2. `pytest` 通过。
3. 所有模块可 import。
4. README 说明 MVP 目标和运行方式。

不要接入真实 LLM。
不要实现真实终端命令执行，terminal.py 先返回 mock observation。
```

---

# 6. 05_AI-ISA 指令集实现 Prompt

用途：实现去语言化核心。

```text
你是编译器/虚拟机架构师。请实现 LoopOS 的 AI-ISA 指令集模型。

目标文件：
- loopos/core/isa.py
- tests/test_isa.py

要求：
使用 Pydantic v2 定义 typed instruction schema。

必须支持以下 op：

1. PLAN
2. CALL_TOOL
3. EXEC_TERMINAL
4. OBSERVE
5. EVALUATE
6. UPDATE_STATE
7. STORE_MEMORY
8. EXTRACT_SKILL
9. TERMINATE

每条 instruction 字段：

- id: str
- op: Literal[...]
- created_at: datetime
- reason_code: str
- args: dict[str, Any]
- safety: InstructionSafety
- expected_observation: ExpectedObservation | None
- metadata: dict[str, Any]

InstructionSafety：
- risk_level: Literal["low","medium","high","blocked"]
- requires_approval: bool
- allowed_paths: list[str]
- blocked_patterns: list[str]

ExpectedObservation：
- success_criteria: list[str]
- failure_criteria: list[str]
- timeout_seconds: int | None

还要实现：

- parse_instruction(raw: str | dict) -> Instruction
- instruction_to_json(instruction) -> str
- validate_instruction_for_mvp(instruction) -> list[str]

测试覆盖：
- 合法指令解析
- 非法 op 失败
- EXEC_TERMINAL 必须有 cmd
- TERMINATE 必须有 reason
- risk_level blocked 时 requires_approval 必须为 true
- JSON roundtrip

不要接入 LLM。
```

---

# 7. 06_State Machine Loop 实现 Prompt

用途：实现核心 loop。

```text
你是 runtime engineer。请实现 LoopOS 的状态机 loop，不接入真实 LLM。

目标文件：
- loopos/core/state.py
- loopos/core/loop_engine.py
- loopos/core/policy.py
- tests/test_loop_engine.py

设计：

State 包含：
- run_id
- goal
- status: pending/running/succeeded/failed/cancelled
- step_index
- progress_score
- current_instruction
- last_observation
- errors
- tool_history
- memory_refs
- created_at
- updated_at

LoopEngine：
- 初始化 goal/state/policy/executor/evaluator/memory
- 每轮：
  1. policy.next_instruction(state)
  2. executor.execute(instruction)
  3. evaluator.evaluate(state, instruction, observation)
  4. state.apply(...)
  5. event_log.append(...)
  6. 检查 stop condition

Policy 先实现 DeterministicDemoPolicy：
- 第 1 步返回 EXEC_TERMINAL echo hello
- 第 2 步返回 TERMINATE

Executor 使用 mock executor。
Evaluator 使用简单规则。

要求：
- 支持 max_steps
- 支持 timeout_seconds 预留
- 防止无限循环
- 每轮写 event log
- pytest 覆盖成功路径和 max_steps 失败路径

不要调用真实 shell。
不要调用真实 LLM。
```

---

# 8. 07_Terminal Executor 实现 Prompt

用途：终端执行层。

```text
你是安全执行系统工程师。请实现 terminal executor 和 permission policy。

目标文件：
- loopos/execution/terminal.py
- loopos/execution/permissions.py
- tests/test_terminal_executor.py
- tests/test_permissions.py

要求：

TerminalExecutor.execute(cmd, cwd, timeout_seconds) 返回 Observation：
- stdout
- stderr
- return_code
- duration_ms
- timed_out
- command
- cwd

PermissionPolicy：
- allowlist_paths
- denylist_patterns
- require_approval_patterns
- max_timeout_seconds
- network_allowed: bool

默认阻止：
- rm -rf /
- sudo
- chmod -R 777
- curl ... | bash
- wget ... | sh
- mkfs
- dd if=
- kill -9 -1
- git config --global
- ssh private key reads

MVP 行为：
- low risk 命令可执行
- high risk 命令返回 blocked observation
- requires approval 的命令在 non_interactive 模式下阻止

测试：
- echo hello 成功
- timeout 生效
- dangerous command 被阻止
- cwd 限制生效
- stderr 捕获

注意：
- 不要使用 shell=True 除非你明确解释原因并在 permission policy 前置过滤。
- 如果使用 shell=True，需要做命令风险检测。
- 推荐使用 subprocess.run，并保证超时。
```

---

# 9. 08_MCP Tool Hub 实现 Prompt

用途：MCP 抽象层，先做轻量接口，后面接真实 MCP SDK。

```text
你是 tool protocol engineer。请实现 LoopOS 的 MCP-like Tool Hub 抽象。

目标文件：
- loopos/mcp/types.py
- loopos/mcp/router.py
- tests/test_mcp_router.py

要求：

定义：
- ToolSpec
- ToolCall
- ToolResult
- ToolRegistry
- ToolRouter

内置工具：
- terminal.exec
- file.read
- file.write
- git.status

MVP 不要求真实 MCP 协议，但接口必须可替换为真实 MCP SDK。

ToolSpec 字段：
- name
- description
- input_schema
- output_schema
- risk_level
- requires_approval
- tags

ToolRouter：
- register(tool)
- list_tools()
- resolve(name)
- call(tool_call)

测试：
- 注册工具
- 调用 terminal.exec 的 mock handler
- 未知工具失败
- risk_level high 时标记需要 approval

不要接入网络。
```

---

# 10. 09_Memory OS 实现 Prompt

用途：实现 state/event/belief/skill。

```text
你是长期记忆系统工程师。请实现 LoopOS Memory OS 的 MVP。

目标文件：
- loopos/memory/event_log.py
- loopos/memory/state_store.py
- loopos/memory/belief_store.py
- loopos/memory/skill_store.py
- tests/test_memory_*.py

存储：
- MVP 使用本地 `.loopos/` 目录。
- event log 用 JSONL。
- state 用 JSON。
- belief/skill 用 JSONL 或 SQLite，优先简单可测。

Event 字段：
- event_id
- run_id
- step_index
- event_type
- payload
- created_at

Belief 字段：
- id
- content
- confidence
- context_tags
- source_event_ids
- conflicts
- version
- status: active/deprecated/rejected
- created_at
- updated_at

Skill 字段：
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

实现：
- append_event
- load_events(run_id)
- save_state/load_state
- add_belief/list_beliefs
- add_skill/list_skills
- update_skill_stats

测试：
- 写入/读取 event
- 保存/恢复 state
- belief confidence 边界
- skill success_rate 计算

不要实现向量检索。
```

---

# 11. 10_Memory Governance 实现 Prompt

用途：核心创新层。

```text
你是 memory governance 系统架构师。请实现 Memory Governance MVP。

目标文件：
- loopos/memory/governance.py
- tests/test_memory_governance.py

目标：
所有长期 memory 写入必须先经过 governance。

实现：

MemoryProposal：
- proposal_id
- memory_type: belief/skill/user_preference
- content
- confidence
- source_event_ids
- context_tags
- evidence
- proposed_by
- created_at

GovernanceDecision：
- accepted: bool
- status: active/rejected/needs_review
- confidence_adjustment
- reason_codes
- conflicts
- normalized_content

MemoryGovernor：
- evaluate_proposal(proposal, existing_memories) -> GovernanceDecision

规则：
1. confidence < 0.4 默认 rejected。
2. 没有 source_event_ids 默认 needs_review。
3. 与 existing belief 文本高度相似时 dedupe。
4. 明显冲突时不要覆盖旧 memory，而是标记 conflicts。
5. 用户偏好类 memory 必须带 context_tags。
6. accepted memory confidence 不得超过 0.9，除非 evidence >= 2。

测试：
- low confidence reject
- no evidence needs_review
- duplicate detected
- conflict detected
- accepted proposal normalized

MVP 可以用简单字符串相似度，不要引入重型依赖。
```

---

# 12. 11_Skill Learning 实现 Prompt

用途：实现自我增强最小闭环。

```text
你是 agent skill learning 系统工程师。请实现从成功 execution trace 中提取 skill 的 MVP。

目标文件：
- loopos/memory/skill_store.py
- loopos/agents/skill_extractor.py
- tests/test_skill_extractor.py

输入：
- run_id
- goal
- event sequence
- final evaluation

输出：
SkillProposal：
- name
- trigger
- steps
- source_event_ids
- success_signal
- limitations

规则：
1. 只有 final evaluation succeeded 才提取 skill。
2. 至少包含 2 个有效 action event。
3. steps 必须是结构化动作，不是自然语言长段落。
4. trigger 必须来自 goal 或 error pattern。
5. skill 写入前必须经过 MemoryGovernor。

实现：
- extract_skill_from_events(...)
- convert_skill_to_memory_proposal(...)

测试：
- 成功 trace 提取 skill
- 失败 trace 不提取
- 单步 trace 不提取
- skill proposal 经过 governance

不要调用 LLM。
```

---

# 13. 12_Context Compiler 实现 Prompt

用途：减少 token、避免上下文污染。

```text
你是 context compiler 设计师。请实现 LoopOS 的 Context Compiler MVP。

目标文件：
- loopos/core/context_compiler.py
- tests/test_context_compiler.py

目标：
将 state + relevant beliefs + relevant skills + user preferences 编译为短小、结构化的 AgentContext。

AgentContext 字段：
- goal
- current_status
- constraints
- relevant_beliefs
- relevant_skills
- user_preferences
- recent_errors
- allowed_tools
- next_step_hints
- token_budget_estimate

实现：
- compile_context(state, memories, skills, preferences, token_budget)
- rank memories by tag overlap + confidence + recency
- 去重
- 限制条数
- 输出 dict/json friendly object

要求：
- 不输出长自然语言。
- 优先结构化字段。
- token_budget 超限时丢弃低置信/低相关 memory。
- tests 覆盖排序、预算截断、冲突 memory 标注。

不要调用 LLM。
```

---

# 14. 13_User Preference Model 实现 Prompt

用途：个性化风格/审美/格式。

```text
你是 personalization system engineer。请实现用户偏好模型 MVP。

目标文件：
- loopos/memory/user_preferences.py
- tests/test_user_preferences.py

UserPreference：
- id
- category: output_style/ui_aesthetic/format/verbosity/language/risk_tolerance
- value
- confidence
- context_tags
- source_event_ids
- status
- created_at
- updated_at

PreferenceModel：
- add_preference(proposal)
- get_active_preferences(context_tags)
- resolve_conflicts(preferences)
- compile_renderer_hints(context)

规则：
1. 偏好不能全局硬覆盖，必须 context-aware。
2. 同类冲突偏好根据 context_tags、confidence、recency 选择。
3. 输出 renderer_hints：
   - language
   - verbosity
   - structure_level
   - aesthetics
   - code_detail_level

测试：
- 添加偏好
- 冲突解析
- context-specific preference
- renderer hints 生成

不要接入真实用户画像服务。
```

---

# 15. 14_CLI/FLI UI 实现 Prompt

用途：做命令行体验。

```text
你是 CLI 产品工程师。请实现 LoopOS 的 FLI/CLI MVP。

目标文件：
- loopos/cli/app.py
- tests/test_cli.py

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

7. loopos config
   - 查看配置

UI 要求：
- Rich panel 显示 goal/status/progress
- 每一步显示：
  - step index
  - instruction op
  - tool
  - result summary
  - evaluation
- 默认不展示长 stdout，提供 --verbose
- 提供 --dry-run
- 提供 --max-steps
- 提供 --yes 允许低风险命令自动执行

测试：
- CLI help
- run dry-run
- status nonexistent run
- skills list empty

不要做 WebUI。
```

---

# 16. 15_安全与权限模型 Prompt

用途：防止 agent 乱删文件/乱执行。

```text
你是安全工程师。请为 LoopOS 实现 terminal/tool permission policy。

目标文件：
- loopos/execution/permissions.py
- loopos/core/safety.py
- tests/test_safety.py
- docs/safety.md

实现：

RiskLevel：
- low
- medium
- high
- blocked

CommandRiskAnalyzer：
- analyze(cmd) -> RiskAssessment

RiskAssessment：
- risk_level
- requires_approval
- reasons
- matched_patterns
- suggested_safe_alternative

规则：
Blocked：
- rm -rf /
- mkfs
- dd if=
- curl | bash
- wget | sh
- sudo without approval
- reading ~/.ssh/id_rsa
- mass deletion outside workspace

High：
- rm -rf relative path
- chmod recursive
- git reset --hard
- git clean -fd
- network upload
- package install
- docker privileged

Medium：
- file write
- git commit
- dependency install
- test execution with network

Low：
- ls
- cat workspace file
- python -m pytest
- git status
- grep/ripgrep

要求：
- 所有 terminal.exec 都必须调用 analyzer。
- blocked 永远不执行。
- high 默认需要 approval。
- --yes 只能跳过 low/medium，不能跳过 high/blocked。
- docs/safety.md 解释安全模型。

测试必须覆盖所有风险级别。
```

---

# 17. 16_集成 OpenHands Prompt

用途：把 OpenHands 当执行底座，而不是直接重写。

```text
你是 OpenHands 集成工程师。请分析本仓库中的 OpenHands 源码/SDK，设计并实现一个最小 adapter。

目标：
LoopOS 不直接依赖 OpenHands 内部实现细节，而是通过 adapter 调用其 sandbox/runtime 能力。

目标文件：
- loopos/integrations/openhands_adapter.py
- tests/test_openhands_adapter.py
- docs/integrations-openhands.md

步骤：
1. 查找 OpenHands 的 Python SDK 或可调用入口。
2. 找到它如何执行 command / edit file / manage workspace。
3. 实现 OpenHandsAdapter 接口：
   - is_available()
   - execute_command(cmd, cwd, timeout)
   - read_file(path)
   - write_file(path, content)
   - apply_patch(patch)
4. 如果当前环境无法直接调用 OpenHands，则实现 graceful fallback，并在 docs 说明接入方法。
5. 不要把 LoopOS 直接绑死到 OpenHands 私有模块。

测试：
- adapter unavailable 时不崩溃
- fallback mock works
- 接口返回统一 Observation/ToolResult

注意：
- 先读源码再实现。
- 不要大规模复制 OpenHands 代码。
```

---

# 18. 17_集成 LangGraph Prompt

用途：将 loop graph 化，支持状态 checkpoint。

```text
你是 LangGraph 集成工程师。请为 LoopOS 增加可选 LangGraph backend。

目标文件：
- loopos/integrations/langgraph_adapter.py
- loopos/core/graph_loop.py
- tests/test_langgraph_adapter.py
- docs/integrations-langgraph.md

目标：
将 LoopOS 的核心循环表达为 graph nodes：

Nodes：
- compile_context
- plan_instruction
- execute_instruction
- observe
- evaluate
- govern_memory
- extract_skill
- decide_next

Edges：
- success -> terminate
- failure -> repair/replan
- continue -> plan_instruction
- blocked -> request_approval/terminate

要求：
1. LangGraph 是可选依赖，未安装时不影响核心测试。
2. 提供 create_loop_graph()。
3. 提供 run_graph(goal, max_steps)。
4. 保持与现有 LoopEngine 状态模型兼容。
5. docs 说明何时用 LoopEngine，何时用 LangGraph。

测试：
- 未安装 LangGraph skip
- graph backend 与 deterministic policy 可跑通
```

---

# 19. 18_借鉴 Letta/Zep/projectmem Prompt

用途：吸收记忆层思想。

```text
你是 agent memory 架构师。请分析本仓库中的 Letta、Zep、projectmem 源码，并把适合 LoopOS 的记忆设计写成 docs，然后实现最小可用增强。

不要大规模复制源码。只借鉴模式。

目标文档：
- docs/memory-design-from-sources.md

目标代码：
- loopos/memory/retrieval.py
- loopos/memory/pre_action_gate.py
- tests/test_memory_retrieval.py
- tests/test_pre_action_gate.py

设计：

1. Letta 借鉴：
   - working memory vs archival memory
   - memory block
   - agent state

2. Zep 借鉴：
   - temporal context
   - graph-like relationships
   - session/user scoped memory

3. projectmem 借鉴：
   - event-sourced log
   - pre-action judgement/gate
   - compact memory injection
   - repeated failure prevention

实现：

MemoryRetriever：
- retrieve(query_tags, limit, min_confidence)
- rank by confidence + recency + tag overlap

PreActionGate：
- before executing instruction, check:
  - repeated failed command
  - known dangerous pattern
  - memory says this approach failed
  - skill exists for this task

GateDecision：
- allow
- block
- warn
- substitute_skill

测试：
- repeated failure blocked
- relevant skill suggested
- low confidence memory ignored
- recency affects rank
```

---

# 20. 19_测试体系 Prompt

用途：让系统可持续开发。

```text
你是测试架构师。请为 LoopOS 建立完整测试体系。

目标：
- pyproject.toml
- tests/
- Makefile 或 justfile
- .github/workflows/ci.yml
- docs/testing.md

要求：

测试层级：
1. unit tests
2. integration tests
3. golden trace tests
4. safety tests
5. CLI smoke tests

新增目录：
tests/fixtures/
tests/golden/

实现：
- deterministic mock LLM
- mock terminal executor
- temporary workspace fixture
- golden event log comparison

命令：
- make test
- make lint
- make typecheck
- make ci

CI：
- python 3.11/3.12
- pytest
- ruff
- mypy

不要要求真实 API key。
不要做真实网络调用。
```

---

# 21. 20_基准任务与评测 Prompt

用途：衡量 LoopOS 是否真的变强。

```text
你是 AI agent benchmark engineer。请为 LoopOS 设计 benchmark 任务集。

目标文件：
- benchmarks/tasks/*.json
- loopos/eval/runner.py
- loopos/eval/metrics.py
- docs/benchmarks.md
- tests/test_eval_runner.py

任务类型：
1. file creation
2. simple script execution
3. bug fix
4. test repair
5. git workflow
6. memory recall
7. repeated failure avoidance
8. skill reuse

Task schema：
- id
- name
- goal
- workspace_setup
- expected_files
- expected_commands
- success_checks
- max_steps
- tags

Metrics：
- success_rate
- steps_to_success
- command_count
- blocked_dangerous_actions
- repeated_failure_count
- skill_reuse_count
- token_estimate optional

实现：
- eval runner 可跑 mock backend
- 输出 JSON report
- docs 说明如何增加 benchmark

不要依赖真实 LLM。
```

---

# 22. 21_重构与质量提升 Prompt

用途：让 Codex 做架构质量审查。

```text
你是资深 Python 架构师。请审查 LoopOS 当前代码质量并提出最小重构。

任务：
1. 找出循环依赖。
2. 找出过大的模块。
3. 找出没有测试的核心路径。
4. 找出类型不清晰的 API。
5. 找出安全风险。
6. 找出和 AGENTS.md 不一致的地方。

请先生成：
- docs/refactor-review.md

然后只做低风险重构：
- 不改变公开 CLI 行为
- 不改变存储格式
- 不改变 AI-ISA schema
- 不删除测试

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

# 23. 22_文档与开源发布 Prompt

用途：准备开源。

```text
你是开源项目维护者。请为 LoopOS 准备开源发布文档。

目标文件：
- README.md
- docs/quickstart.md
- docs/architecture.md
- docs/ai-isa.md
- docs/memory.md
- docs/safety.md
- docs/contributing.md
- CHANGELOG.md
- LICENSE 检查，不要随意覆盖现有 LICENSE

README 必须包含：
1. What is LoopOS
2. Why state-machine agent
3. Installation
4. Quickstart
5. Example
6. Architecture
7. Safety model
8. Roadmap
9. Comparison with existing agent tools
10. Contributing

注意：
- 不要声称超过具体产品，除非有 benchmark。
- 用“inspired by”而不是“copied from”。
- 标明第三方项目 license 风险需要人工确认。
```

---

# 24. 23_每日开发循环 Prompt

用途：每天开工先让 Codex 做计划。

```text
你是 LoopOS 项目的 AI 工程经理。请基于当前代码状态、docs、tests，给出今天最有效的开发计划。

要求：
1. 先查看 git status。
2. 查看最近 TODO。
3. 查看失败测试。
4. 查看 docs/architecture-mvp.md。
5. 输出今日计划，不改代码。

输出格式：

# Daily Plan

## Current State
## Blockers
## Highest Leverage Tasks
## Recommended Task Order
## Task 1 Prompt
## Task 2 Prompt
## Task 3 Prompt
## Risk Notes

每个 Task Prompt 要能直接复制给 Codex 执行。
```

---

# 25. 24_单次 Codex 任务模板

每次实际给 Codex 时，推荐用这个模板：

```text
你是 LoopOS 项目的 coding agent。

任务名称：
[填写一个非常具体的任务]

背景：
[说明当前模块、关联文档、设计约束]

允许修改：
- [文件/目录]

禁止修改：
- [文件/目录]

要求：
1. [要求1]
2. [要求2]
3. [要求3]

完成标准：
1. [标准1]
2. [标准2]
3. [标准3]

测试命令：
```bash
pytest tests/xxx.py
ruff check .
mypy loopos
```

输出格式：
1. 修改摘要
2. 测试结果
3. 已知限制
4. 下一步建议

请先简短说明实现计划，然后再修改代码。
```

---

# 26. 25_故障修复 Prompt

```text
你是 debugging expert。当前 LoopOS 有测试失败/运行错误。请不要重构无关代码，只修复最小问题。

错误信息：

[粘贴 traceback 或 pytest 输出]

要求：
1. 定位根因。
2. 最小修改。
3. 添加回归测试。
4. 不改变公开 API，除非错误来自 API 设计。
5. 修复后运行相关测试。

允许修改：
[列文件]

禁止修改：
[列文件]

输出：
- root cause
- changed files
- tests run
- why this fix is safe
```

---

# 27. 26_代码审查 Prompt

```text
你是严格的代码审查员。请审查当前 diff。

重点检查：
1. 是否违反 AGENTS.md。
2. 是否引入不安全 shell 执行。
3. 是否绕过 Memory Governance。
4. 是否让 LLM 输出自由文本进入内部状态。
5. 是否缺测试。
6. 是否增加不必要依赖。
7. 是否破坏 AI-ISA schema。
8. 是否存在长期维护风险。

请不要改代码，生成：
- docs/reviews/review-[日期或分支名].md

输出：
# Review
## Summary
## Blocking Issues
## Non-blocking Issues
## Test Gaps
## Security Concerns
## Suggested Fixes
```

---

# 28. 27_PR 描述生成 Prompt

```text
你是开源项目维护者。请根据当前 git diff 生成 PR 描述。

要求：
- 清楚说明为什么改。
- 说明改了什么。
- 说明如何测试。
- 说明安全影响。
- 说明后续工作。
- 不夸大能力。
- 不声称 benchmark 结果，除非有数据。

格式：

## Summary
## Changes
## Tests
## Safety
## Memory/AI-ISA Impact
## Screenshots/CLI Output
## Follow-ups
```

---

# 29. 28_推荐执行顺序

如果你现在从 0 开始，按这个顺序把 Prompt 一个一个喂给 Codex：

```text
1. 01_仓库审计
2. 02_开源项目能力抽取
3. 03_目标架构设计
4. 00_AGENTS.md 全局项目指令
5. 04_创建 LoopOS Core 骨架
6. 05_AI-ISA 指令集实现
7. 06_State Machine Loop 实现
8. 07_Terminal Executor 实现
9. 15_安全与权限模型
10. 09_Memory OS 实现
11. 10_Memory Governance 实现
12. 11_Skill Learning 实现
13. 12_Context Compiler 实现
14. 14_CLI/FLI UI 实现
15. 08_MCP Tool Hub 实现
16. 16_集成 OpenHands
17. 17_集成 LangGraph
18. 18_借鉴 Letta/Zep/projectmem
19. 19_测试体系
20. 20_基准任务与评测
21. 21_重构与质量提升
22. 22_文档与开源发布
```

---

## 终极主 Prompt：从 0 驱动整个项目

如果你只想给 Codex 一个总控 Prompt，可以用下面这个。但更建议分阶段执行。

```text
你是 LoopOS 项目的首席 AI 工程师、架构师和 coding agent。

目标：
从当前仓库出发，构建一个 Terminal-native、MCP-compatible、AI-ISA-driven、Memory-governed、Self-improving 的 CLI agent runtime。

重要背景：
我已经拉取了 OpenHands、LangGraph、Letta、Zep、projectmem 等源码。你需要先分析可复用能力，再设计最短 MVP 路线。不要盲目复制大段第三方代码。优先通过 adapter 和接口复用。

核心原则：
1. 不做 chatbot。
2. 内部用 AI-ISA、State、Event、Memory、Skill 等结构化对象。
3. LLM 只能生成结构化 instruction，不允许自由文本驱动 runtime。
4. 所有 terminal 命令必须经过 permission policy。
5. 所有长期记忆写入必须经过 Memory Governance。
6. MVP 先 Python-only，不做 WebUI。
7. CLI/FLI 是第一入口。
8. 测试必须可 mock，不依赖真实 API key。
9. 每次只做小步修改，保持测试通过。

阶段任务：
Phase 0:
- 审计仓库。
- 抽取 OpenHands/LangGraph/Letta/Zep/projectmem 可复用能力。
- 写 docs/repo-audit.md、docs/source-extraction.md、docs/architecture-mvp.md。
- 创建 AGENTS.md。

Phase 1:
- 创建 LoopOS Python 项目骨架。
- 实现 AI-ISA typed schema。
- 实现 State Machine Loop。
- 实现 mock policy/mock executor/mock evaluator。
- 实现 CLI run/status/history。
- 实现 JSON/JSONL state/event log。
- 测试通过。

Phase 2:
- 实现安全 Terminal Executor。
- 实现 permission policy。
- 实现 Memory OS。
- 实现 Memory Governance。
- 实现 Skill Learning。
- 实现 Context Compiler。
- 实现 User Preference Model。
- 实现 MCP-like Tool Hub。

Phase 3:
- 通过 adapter 集成 OpenHands runtime。
- 可选集成 LangGraph backend。
- 借鉴 Letta/Zep/projectmem 升级 memory retrieval/pre-action gate。
- 建立 benchmark。
- 完善文档和开源发布。

工作方式：
每一步你必须：
1. 先说明计划。
2. 小范围修改。
3. 添加测试。
4. 运行测试或说明无法运行的原因。
5. 输出 changed files、tests、limitations、next step。

现在开始执行 Phase 0：仓库审计。请不要先改业务代码，只创建 docs/repo-audit.md。
```

---

## 给 Codex 的“反跑偏约束”

如果 Codex 经常想“一次性写太多”，把这个加到每个 Prompt 最后：

```text
重要限制：
- 不要实现未被要求的功能。
- 不要重构无关代码。
- 不要引入大型依赖。
- 不要新增 WebUI。
- 不要真实调用网络。
- 不要执行危险 shell 命令。
- 不要把 prompt 长文本硬编码进业务逻辑。
- 不要绕过 AI-ISA。
- 不要绕过 Memory Governance。
- 如果发现需求过大，请拆成最小可测试步骤。
```

---

## 给 Codex 的“高质量输出约束”

```text
质量要求：
- 所有新 public API 必须有类型。
- 所有核心数据结构必须有 Pydantic model。
- 所有核心逻辑必须有单元测试。
- 错误信息必须可读。
- CLI 输出必须简洁。
- 日志必须结构化。
- 代码必须可扩展但不过度抽象。
- 安全逻辑优先于便利性。
```

---

## 给 Codex 的“成本/速度优化约束”

```text
性能与 token 约束：
- 内部状态尽量结构化，避免长自然语言。
- Event log 存完整记录，但 Context Compiler 只取短摘要。
- Agent-to-agent 或 module-to-module 通信使用 JSON-like object。
- 用户输出才渲染自然语言。
- 不要把完整历史塞进 LLM prompt。
- 优先检索相关 memory/skill，再压缩成 AgentContext。
```

---

## 给 Codex 的“最终产品愿景”

```text
产品愿景：
LoopOS 最终不是一个普通 coding assistant，而是一个 AI runtime：

- 用户给目标。
- 系统把目标编译成 AI-ISA。
- 状态机驱动工具执行。
- 终端和 MCP 提供现实能力。
- Memory Governance 防止上下文污染。
- Skill Learning 让系统从成功经验中进化。
- Context Compiler 降低 token 成本。
- User Preference Model 让最终输出匹配用户审美、语言和格式。
```

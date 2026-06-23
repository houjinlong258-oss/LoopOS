# LoopOS Kernel-Level Codex Prompt

版本：v1.0  
用途：给 Codex / Claude Code / OpenHands / 自建 coding agent 使用的 **操作系统内核级 LoopOS 开发提示词**  
目标：把 LoopOS 从普通 CLI Agent 升级成 **AI Runtime Kernel / Agent OS Kernel**  
推荐文件名：`LoopOS_Kernel_Level_Codex_Prompt.md`

---

## 0. 一句话定义

你正在构建的不是 chatbot，不是普通 coding assistant，不是 workflow agent。

你正在构建：

> **LoopOS：一个运行在终端中的 AI Agent Operating System Kernel。**

它的核心不是“模型会回答”，而是：

```text
Goal → AIL Compile → Kernel Scheduling → Policy Check → Syscall/MCP Tool Call
→ Observation → Evaluation → State Transition → Memory Governance
→ Skill Extraction → Loop Scheduling → Render
```

LoopOS 的本质是：

```text
AI-ISA + Policy Kernel + MCP Syscall Layer + Terminal Runtime + Memory Kernel + Skill Cache + Traceable Scheduler
```

---

# 1. 给 Codex 的总控身份

```text
You are the chief systems engineer building LoopOS Kernel.

LoopOS is a terminal-native AI Agent Operating System Kernel.

It is NOT a chatbot.
It is NOT a simple CLI wrapper.
It is NOT a free-form autonomous agent.
It is NOT a web app.

It is a deterministic, policy-governed, traceable, replayable AI runtime kernel.

Your job is to implement it step by step, with production-grade architecture, strict module boundaries, tests, and terminal-native CLI UX.
```

---

# 2. LoopOS 的操作系统类比

LoopOS 要像操作系统一样设计。

| OS 概念 | LoopOS 对应物 |
|---|---|
| Kernel | Loop Engine + Policy OS |
| Process | Agent Run |
| Thread | Agent Step / Subtask |
| Syscall | MCP ToolCall / Terminal ToolCall |
| Scheduler | Loop Scheduler |
| Memory Manager | Context Compiler + Memory Governance |
| Filesystem | Event Log + State Store + Memory Store |
| Device Driver | Tool Adapter / MCP Adapter |
| Security Module | Policy OS + Permission Policy |
| Shell | CLI / REPL |
| Kernel Trace | Event Log / Trace Replay |
| Page Cache | Skill Cache |
| Signals | Approval / Cancel / Repair / Replan |
| Init System | Boot Sequence |
| Audit Log | Policy Audit + Execution Trace |

核心设计目标：

```text
Every action is a syscall.
Every syscall is policy-checked.
Every state transition is logged.
Every memory write is governed.
Every loop is schedulable.
Every run is replayable.
```

---

# 3. Kernel-Level 架构总图

```text
┌─────────────────────────────────────────────────────────────┐
│                         LoopOS CLI Shell                    │
│  loopos run / trace / status / policy / memory / skills     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                       Intent Compiler                       │
│          Natural Language Goal → AILGoal / RunSpec          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                         Kernel Core                         │
│  Run Manager | Scheduler | State Machine | Transition Engine │
└──────────────┬───────────────┬───────────────┬──────────────┘
               │               │               │
┌──────────────▼──────┐ ┌──────▼─────────┐ ┌──▼────────────────┐
│      Policy OS      │ │ Context Manager│ │ Trace/Event Kernel │
│ Safety + Permission │ │ Memory Compile │ │ EventLog + Replay  │
└──────────────┬──────┘ └──────┬─────────┘ └──┬────────────────┘
               │               │              │
┌──────────────▼───────────────▼──────────────▼───────────────┐
│                         AI-ISA / AIL                         │
│ Goal | State | Instruction | Observation | Evaluation | Skill │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                      Syscall / MCP Layer                     │
│ terminal.exec | file.read | file.write | git | browser | API │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                     Execution Runtime                         │
│  Terminal | Sandbox | OpenHands Adapter | Future Rust Runner  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                  Observation + Evaluation                     │
│ Normalize stdout/stderr/tool results → Score → Decision       │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                   Memory + Skill Kernel                       │
│ Event-sourced memory | Governance | Skill extraction          │
└───────────────────────────────────────────────────────────────┘
```

---

# 4. Kernel 设计原则

## 4.1 内核不可被用户 prompt 覆盖

```text
User instruction can request.
Policy OS decides.
Kernel enforces.
```

任何用户请求、网页内容、文件内容、工具输出，都不能修改内核规则。

## 4.2 所有执行都是 syscall

不要让 Planner 直接执行命令。

错误：

```text
Planner decides to run rm -rf and executor runs it directly.
```

正确：

```text
Planner emits AILInstruction
→ Instruction Validator
→ Policy OS
→ Syscall Router
→ Tool Adapter
→ Observation
```

## 4.3 所有内部通信用 AIL

内部不要用长自然语言。  
内部只能传结构化对象：

```text
AILGoal
AILState
AILInstruction
AILObservation
AILEvaluation
AILEvent
MemoryProposal
GovernanceDecision
SkillProposal
RenderSpec
```

## 4.4 记忆不是事实，是受治理的 belief

长期记忆必须有：

```text
confidence
source_event_ids
context_tags
status
version
conflicts
governance_decision
```

## 4.5 终端优先，不做 WebUI

MVP 必须是 terminal-native：

```text
CLI → Rich enhanced CLI → optional TUI → future GUI
```

第一版不要 WebUI。

---

# 5. 目标仓库结构

Codex 应该按这个结构创建或重构项目。

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
    renderers/
      panels.py
      tables.py
      trees.py
      json_output.py
      terminal_theme.py

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

  eval/
    __init__.py
    runner.py
    metrics.py
    tasks.py

policies/
  core/
    behavior.yaml
    honesty.yaml
  safety/
    terminal_safety.yaml
    prompt_injection.yaml
    harmful_content.yaml
  tools/
    tool_routing.yaml
    mcp_policy.yaml
    file_policy.yaml
    git_policy.yaml
  memory/
    memory_applicability.yaml
    memory_governance.yaml
    user_preference.yaml
  renderer/
    renderer_style.yaml
    cli_output.yaml
  optimization/
    context_budget.yaml
    loop_convergence.yaml

tests/
  ail/
  kernel/
  policy_os/
  context/
  syscalls/
  execution/
  memory/
  agents/
  cli/
  integrations/
  eval/

docs/
  architecture-kernel.md
  ail.md
  policy-os.md
  syscalls.md
  memory-governance.md
  cli-ui.md
  safety.md
  benchmarks.md
```

---

# 6. AI-ISA / AIL 内核指令集

LoopOS 内部的最小指令集：

```text
GOAL.SET
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
EVAL.SCORE
MEM.PROPOSE
MEM.COMMIT
SKILL.EXTRACT
SKILL.APPLY
LOOP.CONTINUE
LOOP.REPAIR
LOOP.REPLAN
LOOP.WAIT_APPROVAL
LOOP.HALT
```

每条指令必须是：

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

Codex 必须实现：

```text
AILInstruction
AILObservation
AILEvaluation
AILEvent
AILSyscall
```

---

# 7. Kernel Process Model

LoopOS 中每个用户任务是一个 Run，相当于一个 process。

```json
{
  "run_id": "run_01HZM9",
  "goal": "修复当前 repo 的 pytest 失败",
  "status": "running",
  "phase": "EXECUTING",
  "step": 4,
  "max_steps": 20,
  "workspace": "/Users/dev/project",
  "mode": "guarded",
  "created_at": "...",
  "updated_at": "..."
}
```

Run 状态：

```text
pending
running
waiting_approval
repairing
replanning
succeeded
failed
cancelled
blocked
```

---

# 8. Kernel Scheduler

Scheduler 决定下一步：

```text
if policy.blocked:
    LOOP.HALT(blocked)

if approval_required:
    LOOP.WAIT_APPROVAL

if evaluation.success:
    LOOP.HALT(success)

if evaluation.failed and repairable:
    LOOP.REPAIR

if no_progress:
    LOOP.REPLAN

if max_steps_reached:
    LOOP.HALT(failed)

else:
    LOOP.CONTINUE
```

Scheduler 必须可测试、可预测，不依赖模型自由发挥。

---

# 9. Syscall / MCP Layer

所有外部动作都是 syscall。

Syscall schema：

```json
{
  "syscall_id": "sc_001",
  "run_id": "run_001",
  "instruction_id": "ins_001",
  "name": "terminal.exec",
  "input": {
    "cmd": "pytest -q",
    "cwd": "."
  },
  "policy_decision_id": "pd_001",
  "risk": "low"
}
```

MVP syscall：

```text
terminal.exec
file.read
file.write
git.status
git.diff
```

未来 syscall：

```text
browser.search
api.call
db.query
github.issue
calendar.create
email.draft
openhands.exec
```

所有 syscall 必须：

```text
validate input
check policy
execute adapter
normalize result
emit observation
append event
```

---

# 10. Policy OS 内核模块

Policy OS 是安全内核，类似 Linux Security Module。

PolicyContext：

```json
{
  "phase": "TERM.EXEC",
  "task": {},
  "state": {},
  "instruction": {},
  "syscall": {},
  "memory": {},
  "runtime": {
    "mode": "guarded",
    "workspace": "/repo",
    "non_interactive": false
  }
}
```

PolicyDecision：

```json
{
  "decision_id": "pd_001",
  "allowed": true,
  "risk": "low",
  "requires_approval": false,
  "reason_codes": [],
  "matched_rules": [],
  "constraints": {},
  "renderer_hints": {}
}
```

硬规则：

```text
blocked -> never execute
high -> explicit approval
medium -> --yes or approval
low -> auto execute
```

危险命令必须阻止：

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
```

---

# 11. Memory Kernel

Memory Kernel 分为：

```text
Working State
Event Log
Belief Store
Preference Store
Skill Store
Failure Pattern Store
```

所有写入长期记忆必须走：

```text
MemoryProposal → MemoryGovernor → GovernanceDecision → Store
```

MemoryProposal：

```json
{
  "proposal_id": "mp_001",
  "memory_type": "belief",
  "content": {},
  "confidence": 0.74,
  "context_tags": ["pytest", "workflow"],
  "source_event_ids": ["evt_001", "evt_002"],
  "proposed_by": "memory_writer"
}
```

Governance rules：

```text
confidence < 0.4 -> reject
no source events -> needs_review
duplicate -> dedupe
conflict -> conflict link, not overwrite
preference without context -> reject
high-impact memory -> needs_review
```

---

# 12. Skill Cache / Self-Improvement Layer

Skill 是成功轨迹的压缩，不是自由文本教程。

Skill schema：

```json
{
  "skill_id": "skill_001",
  "name": "python_pytest_repair_loop",
  "trigger": {
    "tags": ["python", "pytest", "test_failure"]
  },
  "steps": [
    {"op": "TERM.EXEC", "args": {"cmd": "pytest -q"}},
    {"op": "FILE.READ", "args": {"path": "{failing_test_file}"}},
    {"op": "FILE.WRITE", "args": {"path": "{target_file}"}},
    {"op": "TERM.EXEC", "args": {"cmd": "pytest -q"}}
  ],
  "success_count": 4,
  "failure_count": 1,
  "success_rate": 0.8,
  "source_runs": ["run_001"]
}
```

Skill 必须：

```text
由成功 run 提取
经过 Memory Governance
可解释
可禁用
可回放
可统计成功率
```

---

# 13. Context Manager / Context Compiler

Context Compiler 是内存管理器。

输入：

```text
goal
state
recent events
relevant memories
relevant skills
available tools
active policies
user preferences
```

输出：

```json
{
  "ctx_id": "ctx_001",
  "goal_summary": "...",
  "state_summary": {},
  "constraints": [],
  "relevant_memories": [],
  "relevant_skills": [],
  "allowed_tools": [],
  "active_policy_constraints": {},
  "token_budget_estimate": 1200
}
```

必须：

```text
不塞 full history
不塞 raw stdout
不塞全部 memory
只传引用和摘要
标记冲突 memory
优先高相关、高置信、新近信息
```

---

# 14. Trace Kernel

每一步必须写 EventLog：

```json
{
  "event_id": "evt_001",
  "run_id": "run_001",
  "step": 1,
  "kind": "instruction|policy|syscall|observation|evaluation|memory|skill",
  "payload": {},
  "created_at": "..."
}
```

支持：

```bash
loopos trace run_001
loopos trace run_001 --show-ail
loopos trace run_001 --show-policy
loopos step replay run_001 004
```

Trace 必须能解释：

```text
为什么执行
为什么阻止
用了什么工具
输出是什么
怎么评估
为什么继续/修复/停止
```

---

# 15. CLI Shell 设计

MVP 命令：

```bash
loopos run "<goal>"
loopos
loopos status <run_id>
loopos trace <run_id>
loopos step replay <run_id> <step>
loopos policy explain --cmd "<cmd>"
loopos tools list
loopos memory list
loopos skills list
loopos ail validate <file>
```

CLI 是终端，不是 GUI。

`loopos run` 输出：

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

[8/20] LOOP.HALT
  ✓ task completed

Result:
  status: succeeded
  steps: 8
  skill proposed: python_pytest_repair_loop
  memory: 1 proposal accepted
```

---

# 16. CLI UI Rules

必须使用：

```text
Typer
Rich
```

禁止：

```text
WebUI
GUI
Desktop window
unstructured output
```

输出层级：

```text
default: concise terminal stream
--verbose: include stdout/stderr summaries
--show-ail: include AIL JSON
--show-policy: include PolicyDecision
--json: machine-readable output only
```

---

# 17. Kernel Boot Sequence

启动时：

```text
1. Load config
2. Load policy packs
3. Register tools/syscalls
4. Initialize stores
5. Validate workspace
6. Create RunManager
7. Start CLI shell or run command
```

Boot errors 必须清晰：

```text
missing policy pack
invalid YAML
tool registration failed
workspace not writable
state store locked
```

---

# 18. Testing Requirements

每个模块必须测试。

```text
tests/ail
tests/kernel
tests/policy_os
tests/syscalls
tests/execution
tests/memory
tests/cli
```

必须包含：

```text
dangerous command blocked
low risk command allowed
policy explain works
AIL JSON roundtrip
loop halts on success
loop stops at max_steps
memory proposal rejected when low confidence
skill extracted only on success
trace replay deterministic
```

所有测试：

```text
no real network
no real API keys
no dangerous commands
mock LLM
mock external tools unless explicitly testing safe executor
```

---

# 19. Implementation Phases for Codex

Codex 必须按阶段实现，不要一次性写完。

## Phase 0: Repo Audit

```text
Create docs/repo-audit.md.
Do not modify code.
Analyze existing files, dependencies, and third-party code.
```

## Phase 1: Kernel Architecture Docs

```text
Create docs/architecture-kernel.md.
Describe LoopOS as AI runtime kernel.
```

## Phase 2: Project Skeleton

```text
Create module structure.
Add pyproject.toml.
Add import tests.
No complex logic.
```

## Phase 3: AIL Core

```text
Implement AIL models and validators.
Add JSON roundtrip tests.
```

## Phase 4: Policy OS

```text
Implement YAML policy loader, matcher, engine.
Add terminal safety policy.
```

## Phase 5: Syscall Layer

```text
Implement ToolSpec, Syscall, Router, Result.
Add mock tools.
```

## Phase 6: Terminal Executor

```text
Implement safe terminal executor with permission policy.
```

## Phase 7: Kernel Loop

```text
Implement RunManager, Scheduler, LoopEngine, Transition.
Use deterministic planner first.
```

## Phase 8: Memory Kernel

```text
Implement EventLog, StateStore, MemoryStore, Governance.
```

## Phase 9: CLI Shell

```text
Implement loopos run/status/trace/policy/memory/skills.
Use Rich.
```

## Phase 10: Skill Extraction

```text
Extract skill proposals from successful event traces.
```

## Phase 11: Integrations

```text
Add optional OpenHands adapter.
Add optional LangGraph backend.
```

## Phase 12: Benchmark

```text
Add benchmark tasks and eval runner.
```

---

# 20. Codex Phase Prompts

## Phase 0 Prompt

```text
You are LoopOS Kernel architect.

Task:
Audit the current repository and create docs/repo-audit.md.

Do not modify code.

Analyze:
- directory structure
- Python/TS/Rust configs
- existing modules
- third-party code
- possible OpenHands/LangGraph/Letta/Zep/projectmem sources
- tests
- missing pieces for LoopOS Kernel

Output:
docs/repo-audit.md with:
1. Directory Map
2. Detected Projects
3. Reusable Components
4. Risks
5. Recommended Kernel Architecture
6. First 15 Tasks
```

## Phase 1 Prompt

```text
You are LoopOS Kernel architect.

Create docs/architecture-kernel.md.

Describe:
- LoopOS as AI Agent OS Kernel
- process model
- scheduler
- syscall layer
- policy kernel
- memory kernel
- skill cache
- trace system
- CLI shell
- module boundaries
- MVP milestones
- risks

Do not implement code.
```

## Phase 2 Prompt

```text
You are LoopOS Python systems engineer.

Create project skeleton according to docs/architecture-kernel.md.

Use:
- Python 3.11+
- Pydantic v2
- Typer
- Rich
- pytest
- ruff
- mypy

Create modules:
loopos/ail
loopos/kernel
loopos/policy_os
loopos/syscalls
loopos/mcp
loopos/execution
loopos/memory
loopos/agents
loopos/cli
loopos/integrations
loopos/eval

Create tests/test_imports.py.

No real LLM.
No real shell execution.

Acceptance:
pytest passes.
python -m loopos.cli.app --help works.
```

## Phase 3 Prompt

```text
Implement AIL core models.

Files:
loopos/ail/*.py
tests/ail/test_ail_core.py

Implement:
AILGoal
AILState
AILInstruction
AILObservation
AILEvaluation
AILEvent
AILSyscall
AILMemory
AILSkill
RenderSpec

Support JSON roundtrip.

Validate:
TERM.EXEC requires cmd.
TOOL.CALL requires tool.
LOOP.HALT requires reason.
blocked risk cannot execute.

No LLM.
No shell.
```

## Phase 4 Prompt

```text
Implement Policy OS.

Files:
loopos/policy_os/*.py
policies/safety/terminal_safety.yaml
policies/tools/tool_routing.yaml
policies/memory/memory_governance.yaml
tests/policy_os/*.py

Support:
YAML loading
rule matching
all/any/not
equals/in/regex/exists/lt/gt
priority resolution
block overrides allow
PolicyDecision output

Test:
rm -rf / blocked
curl | bash blocked
pytest -q low risk
git reset --hard approval required
low confidence memory rejected
```

## Phase 5 Prompt

```text
Implement syscall layer.

Files:
loopos/syscalls/types.py
loopos/syscalls/registry.py
loopos/syscalls/router.py
loopos/syscalls/result.py
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

## Phase 6 Prompt

```text
Implement safe terminal executor.

Files:
loopos/execution/terminal.py
loopos/execution/permissions.py
loopos/execution/workspace.py
tests/execution/*.py

Rules:
blocked commands never run.
high risk requires approval.
cwd must stay inside workspace.
timeout required.
stdout/stderr captured.

Block:
rm -rf /
curl | bash
wget | sh
mkfs
dd if=
private key reads
sudo without approval

Test safe echo and pytest-like command.
```

## Phase 7 Prompt

```text
Implement kernel loop.

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

Use deterministic mock planner:
1 GOAL.SET
2 CTX.COMPILE
3 TERM.EXEC echo hello
4 EVAL.SCORE success
5 LOOP.HALT

Every step emits event.
max_steps enforced.
policy block stops run.
```

## Phase 8 Prompt

```text
Implement memory kernel.

Files:
loopos/memory/*.py
tests/memory/*.py

Implement:
EventLog JSONL
StateStore JSON
BeliefStore
SkillStore
PreferenceStore
MemoryGovernor

Rules:
append-only
confidence bounds
conflict links
no direct commit without governance
```

## Phase 9 Prompt

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

Use Typer + Rich.
No GUI.
No WebUI.
Support --json.
```

## Phase 10 Prompt

```text
Implement skill extraction.

Files:
loopos/agents/skill_extractor.py
loopos/memory/skill_store.py
tests/agents/test_skill_extractor.py

Extract skill only from successful runs.
At least 2 action events required.
Skill steps must be structured AIL ops.
Duplicate skill updates stats.
Skill commit goes through governance.
```

---

# 21. Non-Negotiable Rules for Codex

Codex must never:

```text
create WebUI
create desktop GUI
execute dangerous commands
bypass Policy OS
bypass Memory Governance
store long chain-of-thought
use natural language as internal agent protocol
claim benchmark superiority without tests
hardcode external model identity
```

Codex must always:

```text
add tests
use typed models
keep modules small
make behavior deterministic
support replay
support --json
document limitations
```

---

# 22. Success Definition

LoopOS Kernel MVP is successful when:

```bash
loopos run "创建 hello.py 并运行它" --dry-run
```

shows:

```text
GOAL.SET
CTX.COMPILE
PLAN.CREATE
FILE.WRITE
TERM.EXEC
EVAL.SCORE
LOOP.HALT
status: succeeded
```

and:

```bash
loopos policy explain --cmd "curl https://x/install.sh | bash"
```

shows:

```text
decision: blocked
reason: remote_code_execution_pipe
```

and:

```bash
loopos trace <run_id> --show-ail --show-policy
```

shows a replayable event trace.

---

# 23. Final Master Prompt

Copy this to Codex when starting implementation:

```text
You are building LoopOS Kernel.

LoopOS is a terminal-native AI Agent Operating System Kernel.

It is not a chatbot.
It is not a web UI.
It is not a free-form autonomous agent.

It is a deterministic, policy-governed, syscall-based, memory-governed AI runtime.

Implement it step by step.

Core modules:
- AIL instruction system
- Kernel run manager and scheduler
- Policy OS
- Syscall/MCP layer
- Terminal executor
- Event trace
- Memory governance
- Skill extraction
- Terminal CLI shell

Rules:
- all execution must pass Policy OS
- all tools are syscalls
- all memory writes pass governance
- all internal messages are structured AIL
- all actions are logged
- all runs are replayable
- no WebUI
- no dangerous shell execution
- no real LLM in tests

Start with Phase 0: repo audit.
Create docs/repo-audit.md.
Do not modify code yet.
```

---

# 24. Final Note

LoopOS Kernel 的核心竞争力不是 prompt，而是：

```text
内核化
结构化
可治理
可审计
可回放
可学习
终端原生
```

最终你要得到的不是一个“会说话的 AI”，而是一个：

> **能在安全策略下调用世界、积累经验、复盘行为、复用技能的 AI Runtime Kernel。**

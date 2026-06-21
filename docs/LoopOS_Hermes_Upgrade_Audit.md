# LoopOS × Hermes 2026.6.19 融合升级审计报告

版本：v0.1  
输入文件：`hermes-agent-2026.6.19.zip`  
审计方式：静态代码审计，不执行压缩包内任何代码。  
目标：分析 Hermes 最新开源文件中的优势、AI Provider 接入、通信平台接入、多模型协作与多模态协作能力，并给出 LoopOS Kernel 的可实现升级方案与 Codex 提示词。

---

## 0. 总结结论

Hermes 这份源码不是一个普通 CLI agent。它已经接近一个“全入口、多模型、多平台、自学习”的 agent runtime，核心优势包括：

```text
1. 多 AI Provider 接入体系
2. 多通信平台 Gateway
3. 终端 / 沙箱 / 云端执行后端
4. Skills 自增长系统
5. Memory / session search / user modeling
6. Mixture-of-Agents 多模型协作
7. delegate_task 子 agent 并行执行
8. 多模态输入路由：native vision / text vision fallback
9. Cron 自动化与跨平台消息投递
10. 插件化 provider / platform / tool / skill 生态
```

但 Hermes 的架构更像“强功能一体化 agent 产品”，而 LoopOS 的目标是“内核化 Agent OS”。所以不建议直接照搬 Hermes runtime，而应该：

> **把 Hermes 的能力拆成 LoopOS Kernel 的 adapter、syscall、policy pack、provider profile、platform gateway、skill pack 和 memory enhancement。**

最重要的升级方向是：

```text
Hermes Provider System
  → LoopOS Model Kernel / Provider Gateway

Hermes Gateway Platforms
  → LoopOS ChatOps Gateway / Mobile App Connector

Hermes Skills
  → LoopOS Skill Kernel + Skill Governance

Hermes MoA + delegate_task
  → LoopOS Multi-Model / Multi-Agent Scheduler

Hermes vision routing
  → LoopOS Capability Router + Multimodal Companion Model

Hermes terminal backends
  → LoopOS Execution Runtime Backends

Hermes safety / approval / file guards
  → LoopOS Policy OS / Syscall Permission Kernel
```

---

# 1. Hermes 源码结构观察

压缩包解压后主要结构如下：

```text
hermes-agent-2026.6.19/
  README.md
  README.zh-CN.md
  pyproject.toml
  cli.py
  run_agent.py
  hermes_state.py
  agent/
  tools/
  gateway/
  hermes_cli/
  plugins/
  providers/
  skills/
  optional-skills/
  optional-mcps/
  acp_adapter/
  tui_gateway/
  ui-tui/
  web/
  apps/
  tests/
```

重点模块：

| 模块 | 价值 |
|---|---|
| `plugins/model-providers/` | 多 AI Provider 插件体系 |
| `gateway/platforms/` | 内置通信平台接入 |
| `plugins/platforms/` | 插件化通信平台接入 |
| `tools/environments/` | local / docker / ssh / singularity / modal / daytona 执行后端 |
| `tools/mixture_of_agents_tool.py` | 多模型协作聚合 |
| `tools/delegate_tool.py` | 子 agent 并行/后台执行 |
| `agent/image_routing.py` | 多模态模型能力路由 |
| `agent/context_compressor.py` | 上下文压缩 |
| `agent/memory_manager.py` | 记忆管理 |
| `tools/memory_tool.py` | 记忆工具 |
| `agent/model_metadata.py` | provider 前缀、模型元数据、上下文估算 |
| `tools/approval.py` | 终端安全审批与危险命令识别 |
| `tools/mcp_tool.py` | MCP 工具接入 |
| `skills/` + `optional-skills/` | skills 库与可选能力包 |
| `acp_adapter/` | Agent Client Protocol 适配 |
| `ui-tui/` / `tui_gateway/` | TUI 与 gateway 可视化方向 |
| `web/` / `apps/desktop` | Web / Desktop 方向，LoopOS MVP 不建议先做 |

---

# 2. Hermes 的核心优点

## 2.1 Provider 覆盖面强

Hermes 用 `plugins/model-providers/` 做 provider 插件，`ProviderProfile` 描述 provider 的：

```text
name
aliases
env_vars
base_url
auth_type
api_mode
supports_vision
supports_health_check
fallback_models
request quirks
```

这比硬编码 provider 好很多。LoopOS 应该吸收成：

```text
loopos/model_kernel/provider_profile.py
loopos/model_kernel/provider_registry.py
loopos/model_kernel/capability_router.py
```

## 2.2 Gateway 很强

Hermes 支持从 Telegram、Discord、Slack、WhatsApp、Signal、Email 等平台直接和 agent 对话，并能保持会话连续性、消息授权、平台格式适配、媒体发送、语音转录、审批按钮等。

LoopOS 应该吸收为：

```text
LoopOS ChatOps Gateway
```

也就是：

```text
CLI 是本地 shell
Gateway 是远程手机/聊天 app shell
```

这样用户可以：

```text
Telegram / WhatsApp / Slack / Teams / iMessage
  → LoopOS Gateway
  → Kernel Run
  → Policy Approval
  → Tool Execution
  → Result Delivery
```

## 2.3 多模型协作已有雏形

Hermes 有两类多模型/多 agent 能力：

1. `mixture_of_agents_tool.py`
   - 多个 reference models 并行回答
   - aggregator model 综合
   - 用于复杂推理/代码/数学/分析任务

2. `delegate_tool.py`
   - 启动多个 child agents
   - 支持并行任务
   - 支持 background delegation
   - 支持不同 provider/model
   - 子 agent 隔离上下文和终端状态

LoopOS 应该升级为：

```text
Multi-Model Scheduler
Multi-Agent Process Tree
Model Capability Router
Aggregator / Judge / Verifier
```

## 2.4 多模态路由思路很好

Hermes 的 `agent/image_routing.py` 有一个很关键的模式：

```text
if main model supports vision:
    native image input
else:
    use auxiliary vision model to turn image into text
    feed text summary to main model
```

这正好符合你的想法：

> 有些模型不支持多模态，但思考和编码能力很强；可以接入支持多模态的模型和它一起工作。

LoopOS 应该把这抽象成：

```text
Capability Companion Model
```

例如：

```text
主模型：DeepSeek / Kimi / Claude Code / Codex，负责推理和编码
视觉模型：Gemini / GPT-4o / Qwen-VL / Xiaomi MiMo，负责图像理解
聚合模型：Claude / GPT / Gemini，负责裁决
Verifier：小模型/规则/测试执行，负责验证
```

## 2.5 Skills 生态很丰富

Hermes 有大量 `skills/` 和 `optional-skills/`，覆盖：

```text
GitHub
软件开发
DevOps
MLOps
研究
金融
邮件
Google Workspace
Notion
PowerPoint
OCR / 文档
社交媒体
智能家居
Apple / iMessage
创意设计
MCP
安全
游戏
区块链
```

LoopOS 应该吸收成：

```text
Skill Pack Registry
Skill Governance
Skill Verification
Skill Sandbox
```

不要让 skill 直接变成 prompt，而要变成：

```text
SkillSpec
  trigger
  required_tools
  risk_level
  steps
  tests
  provenance
  success_rate
```

## 2.6 终端环境后端成熟

Hermes 支持执行环境：

```text
local
docker
ssh
singularity / apptainer
modal
daytona
managed modal
```

LoopOS 应该把它升级成：

```text
Execution Runtime Backend
```

并作为 syscall 的执行后端：

```text
terminal.exec
  → local backend
  → docker backend
  → ssh backend
  → modal backend
  → daytona backend
```

---

# 3. Hermes 支持的 AI Provider 接入

根据 `plugins/model-providers/`、README、`.env.example`、`ProviderProfile` 静态审计，Hermes 支持或显式预留了以下模型接入。

## 3.1 主 LLM Provider 插件

| Provider ID | 说明 | 认证方式 / 特点 |
|---|---|---|
| `openrouter` | OpenRouter aggregator | 一个 key 接 200+ 模型 |
| `nous` | Nous Research Portal | OAuth device code / API key，覆盖模型与工具网关 |
| `novita` | NovitaAI | OpenAI-compatible |
| `nvidia` | NVIDIA NIM | OpenAI-compatible |
| `xiaomi` | Xiaomi MiMo | 支持 vision，tool message vision 有限制 |
| `zai` | Z.AI / GLM | GLM / Zhipu |
| `kimi-coding` | Moonshot Kimi Coding global | Kimi / Moonshot coding endpoint |
| `kimi-coding-cn` | Moonshot China | 中国区 endpoint |
| `minimax` | MiniMax global | Anthropic-style endpoint |
| `minimax-cn` | MiniMax China | 中国区 endpoint |
| `minimax-oauth` | MiniMax OAuth | OAuth external |
| `huggingface` | HuggingFace Inference Providers | router.huggingface.co |
| `gemini` | Google Gemini API key | native Gemini / OpenAI-compatible handling |
| `google-gemini-cli` | Gemini Cloud Code OAuth | OAuth external |
| `anthropic` | Anthropic Claude | Native provider |
| `deepseek` | DeepSeek | OpenAI-compatible |
| `alibaba` | Alibaba DashScope international | OpenAI-compatible |
| `alibaba-coding-plan` | Alibaba Cloud Coding Plan | coding endpoint |
| `qwen-oauth` | Qwen Portal OAuth | OAuth external |
| `stepfun` | StepFun Step Plan | coding / step plan endpoint |
| `xai` | xAI Grok | Responses API mode |
| `openai-codex` | OpenAI Codex | Responses API / OAuth external |
| `copilot` | GitHub Copilot | Copilot/GitHub token |
| `copilot-acp` | GitHub Copilot via ACP subprocess | Agent Client Protocol |
| `opencode-zen` | OpenCode Zen | Curated frontier models |
| `opencode-go` | OpenCode Go | Subscription/open models |
| `kilocode` | Kilo Code | gateway endpoint |
| `arcee` | Arcee AI | Arcee models |
| `gmi` | GMI Cloud | OpenAI-compatible |
| `bedrock` | AWS Bedrock | AWS SDK credentials |
| `azure-foundry` | Microsoft Foundry | user-provided Azure endpoint |
| `ollama-cloud` | Ollama Cloud | OpenAI-compatible |
| `custom` | Custom / Ollama / local OpenAI-compatible | arbitrary base URL |

## 3.2 OpenAI 支持说明

Hermes 中有：

```text
openai-codex
custom endpoint
OpenAI direct alias in auxiliary path
VOICE_TOOLS_OPENAI_KEY for voice/TTS/STT
OPENAI_API_KEY for custom/direct endpoints
```

它没有像 `openai` 文件夹那样的普通 `plugins/model-providers/openai/` 插件，但代码里有 direct API alias：

```text
provider: openai → custom + https://api.openai.com/v1
```

LoopOS 应该直接做成一等 provider：

```text
openai
openai-responses
openai-chat-completions
openai-codex
```

这样比 Hermes 更清晰。

---

# 4. Hermes 的工具 / 媒体 / 辅助 Provider

Hermes 不只是 LLM，还支持很多 tool provider。

## 4.1 Web Search / Extract

从 `agent/web_search_registry.py` 和 `.env.example` 看，支持或预留：

```text
Firecrawl
Parallel
Tavily
Exa
SearXNG
Brave-free
DDGS
```

LoopOS 应该把它归为：

```text
SearchProvider
ExtractProvider
CrawlProvider
```

## 4.2 Image Generation

主要 registry 默认偏好：

```text
FAL
```

并且 pyproject 中有 `fal-client` optional extra。

LoopOS 应该支持：

```text
fal
openai-image
gemini-image
minimax-image
custom-image-provider
```

## 4.3 Video Generation

有 `agent/video_gen_registry.py` 和 `tools/video_generation_tool.py`，说明 Hermes 已经把视频生成做成 provider registry 模式。

LoopOS 可抽象为：

```text
MediaGenerationKernel
  image.generate
  video.generate
  audio.generate
```

## 4.4 TTS / STT

Hermes 支持：

STT：

```text
local faster-whisper
groq
openai
mistral
xai
elevenlabs
```

TTS：

```text
edge
openai
elevenlabs
minimax
gemini
mistral
xai
piper
kittentts
neutts
```

LoopOS 应该把语音作为 ChatOps Gateway 的能力：

```text
voice_in → STT → AILGoal
voice_out ← TTS ← Renderer
```

---

# 5. Hermes 支持的通信 / 手机 App / ChatOps 平台

Hermes 内置和插件化平台很多。LoopOS 应该尽量复用这个接入范围。

## 5.1 内置平台

从 `gateway/config.py` 和 `gateway/platforms/` 看，内置平台包括：

| 平台 | 说明 |
|---|---|
| `local` | 本地会话 |
| `telegram` | Telegram Bot |
| `discord` | Discord |
| `whatsapp` | WhatsApp Baileys bridge |
| `whatsapp_cloud` | WhatsApp Cloud API |
| `slack` | Slack |
| `signal` | Signal |
| `mattermost` | Mattermost |
| `matrix` | Matrix |
| `homeassistant` | Home Assistant |
| `email` | IMAP / SMTP |
| `sms` | Twilio SMS |
| `dingtalk` | 钉钉 |
| `api_server` | HTTP API server |
| `webhook` | generic webhook |
| `msgraph_webhook` | Microsoft Graph webhook |
| `feishu` | 飞书 |
| `wecom` | 企业微信 bot |
| `wecom_callback` | 企业微信 callback |
| `weixin` | 微信 |
| `bluebubbles` | iMessage via BlueBubbles |
| `qqbot` | QQ Bot |
| `yuanbao` | 元宝 |
| `relay` | generic relay adapter |

## 5.2 插件化平台

从 `plugins/platforms/` 看，还有：

| 插件平台 | 说明 |
|---|---|
| `google_chat` | Google Chat via Pub/Sub |
| `teams` | Microsoft Teams Bot Framework |
| `line` | LINE Messaging API |
| `irc` | IRC |
| `ntfy` | ntfy push |
| `simplex` | SimpleX Chat |
| `photon` | iMessage via Photon Spectrum |
| `raft` | Raft external agent bridge |
| `homeassistant` | Home Assistant plugin |
| `mattermost` | Mattermost plugin |
| `discord` | Discord plugin variant |

## 5.3 LoopOS 应该如何接入

LoopOS 不应该把 gateway 混入 kernel。建议分层：

```text
loopos_gateway/
  platform_adapters/
  session_router/
  attachment_router/
  approval_router/
  slash_command_router/
  delivery_router/
```

和 Kernel 的边界：

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

---

# 6. Hermes 多模型协作：应该如何升级到 LoopOS

## 6.1 Hermes 已有能力

Hermes 有 `tools/mixture_of_agents_tool.py`：

```text
Reference models parallel response
Aggregator model synthesis
Failure tolerant
OpenRouter based
```

也有 `tools/delegate_tool.py`：

```text
spawn child agents
isolated context
isolated terminal session
different provider/model possible
background delegation
depth limit
concurrent child limit
```

## 6.2 LoopOS 应升级成 Kernel Scheduler 功能

不要把 MoA 作为普通 tool，而要做成调度层能力：

```text
MultiModelScheduler
  route(task, required_capabilities)
  select_primary_model
  select_auxiliary_models
  select_verifier
  select_aggregator
```

模型角色：

| 角色 | 作用 |
|---|---|
| `primary_reasoner` | 主思考/规划 |
| `coder` | 代码生成/修复 |
| `vision_companion` | 图像/截图/视频理解 |
| `search_companion` | 搜索与事实核验 |
| `critic` | 反驳、找错 |
| `verifier` | 测试、验证、规则检查 |
| `aggregator` | 综合多个模型意见 |
| `cheap_summarizer` | 压缩上下文 |
| `safety_judge` | 安全分类 |
| `policy_explainer` | 解释 PolicyDecision |

## 6.3 多模态协作路线

你提出的需求是非常对的：

> 有些模型不支持多模态，但思考和编码能力很强，那么可以接入支持多模态的模型和它一起工作。

LoopOS 应该设计为：

```text
User sends image/screenshot/file
  ↓
Capability Router checks primary model supports_vision
  ↓
if supports_vision:
    native multimodal input
else:
    vision_companion analyzes image
    outputs AILObservation / VisionSummary
    primary_reasoner consumes structured summary
```

VisionSummary 应该结构化：

```json
{
  "type": "vision_summary",
  "source": "image_001",
  "model": "gemini-vision",
  "objects": [],
  "text_detected": [],
  "ui_elements": [],
  "code_snippets": [],
  "actionable_findings": [],
  "confidence": 0.82
}
```

这样主模型可以是：

```text
DeepSeek / Kimi / Codex / Claude Code / local coder
```

而视觉模型可以是：

```text
Gemini / GPT-4o / Qwen-VL / Xiaomi MiMo / Claude vision
```

---

# 7. Hermes 值得吸收进 LoopOS 的模块

## 7.1 ProviderProfile

吸收为：

```text
loopos/model_kernel/provider_profile.py
```

新增字段：

```text
capabilities:
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
  cost_class
  latency_class
  reliability_score
```

## 7.2 Gateway Platform Adapter

吸收为：

```text
loopos_gateway/platforms/base.py
```

必须支持：

```text
send_text
send_markdown
send_file
send_image
send_audio
send_approval
send_model_picker
send_skill_picker
typing indicator
message chunking
attachment extraction
allowlist
session source
```

## 7.3 Approval UX

Hermes 平台支持 interactive approval，这是 LoopOS 必须要有的：

```text
Terminal high-risk syscall approval
Chat app Approve/Deny button
Mobile push approval
```

LoopOS 可升级：

```text
ApprovalToken
ApprovalRequest
ApprovalDecision
ApprovalAudit
```

## 7.4 Skill Hub

Hermes 的 skills 目录很丰富，但 LoopOS 要加治理：

```text
SkillSpec
SkillPolicy
SkillRisk
SkillTest
SkillProvenance
SkillSuccessStats
```

## 7.5 Execution Backends

吸收为：

```text
ExecutionBackend:
  local
  docker
  ssh
  singularity
  modal
  daytona
  openhands
```

并放在 syscall layer 下。

## 7.6 Context Compression

Hermes 有 context compressor/conversation compression。LoopOS 需要更强：

```text
Context Compiler
  + Policy constraints
  + Memory relevance
  + Skill references
  + Event digest
  + Tool affordances
  + Token budget
```

---

# 8. Hermes 不建议直接照搬的地方

## 8.1 大型 god files

Hermes 有大型文件：

```text
cli.py
run_agent.py
hermes_state.py
agent/conversation_loop.py
agent/auxiliary_client.py
```

这些功能很强，但对 LoopOS 不适合直接继承。LoopOS 应该保持：

```text
kernel/
policy_os/
syscalls/
memory/
gateway/
model_kernel/
```

清晰分层。

## 8.2 Prompt 驱动过重

Hermes 仍有不少自然语言系统 prompt / skill prompt / agent loop 逻辑。LoopOS 的差异化是：

```text
AIL 内部语言
Policy OS 强制约束
Kernel Scheduler
```

不要退回普通 prompt agent。

## 8.3 Skills 需要治理

Hermes skills 很丰富，但如果直接导入，会带来：

```text
上下文污染
过期 skill
安全风险
质量参差
依赖混乱
```

LoopOS 应加：

```text
Skill Governance
Skill Sandbox
Skill Test
Skill Versioning
Skill Risk Classification
```

## 8.4 多模型协作需从 tool 升级为 scheduler

Hermes 的 MoA 是 tool 级。LoopOS 应该变成 kernel scheduler 级：

```text
TaskGraph node 可以指定 model_role
Scheduler 根据 capability 选择模型
Verifier 检查输出
Aggregator 合并结果
```

---

# 9. LoopOS 升级后的新架构

```text
LoopOS Kernel
├── AIL / AI-ISA
├── Policy OS
├── Syscall Layer
│   ├── Terminal
│   ├── File
│   ├── Git
│   ├── Browser
│   ├── MCP
│   └── Gateway
├── Model Kernel
│   ├── Provider Registry
│   ├── Capability Router
│   ├── Multi-Model Scheduler
│   ├── Vision Companion
│   ├── Critic / Verifier
│   └── Aggregator
├── Execution Runtime
│   ├── local
│   ├── docker
│   ├── ssh
│   ├── singularity
│   ├── modal
│   ├── daytona
│   └── openhands
├── Memory Kernel
│   ├── Event Log
│   ├── Beliefs
│   ├── Preferences
│   ├── Failure Patterns
│   └── Governance
├── Skill Kernel
│   ├── Skill Registry
│   ├── Skill Governance
│   ├── Skill Tests
│   └── Skill Stats
└── ChatOps Gateway
    ├── Telegram
    ├── Discord
    ├── Slack
    ├── WhatsApp
    ├── Signal
    ├── Email
    ├── SMS
    ├── Matrix
    ├── Teams
    ├── Feishu
    ├── WeCom
    ├── Weixin
    ├── QQ
    ├── iMessage
    └── Plugin Platforms
```

---

# 10. 可实现的升级路线

## Phase A：Provider Gateway

目标：

```text
支持 Hermes 支持的 provider，同时让 LoopOS 支持能力路由。
```

实现：

```text
loopos/model_kernel/
  provider_profile.py
  provider_registry.py
  provider_loader.py
  capability.py
  router.py
  client.py
```

验收：

```text
loopos models list
loopos models inspect openrouter
loopos models route --task coding --needs vision=false
```

## Phase B：ChatOps Gateway

目标：

```text
手机 App / 聊天软件上操作 LoopOS。
```

先实现：

```text
Telegram
Slack
Discord
WhatsApp Cloud
Email
Webhook/API Server
```

后续：

```text
Signal
Matrix
Teams
Feishu
WeCom
Weixin
QQBot
iMessage
LINE
SimpleX
Google Chat
```

## Phase C：Multi-Model Scheduler

目标：

```text
让不支持多模态但编码强的模型，和支持多模态的模型协作。
```

实现：

```text
model_roles.yaml
capability_router.py
multi_model_session.py
vision_companion.py
aggregator.py
verifier.py
```

## Phase D：Hermes Skill Importer

目标：

```text
把 Hermes skills 转为 LoopOS SkillSpec。
```

不要直接全量启用。流程：

```text
scan Hermes skill
  → parse metadata
  → classify risk
  → convert to SkillSpec
  → run static audit
  → optional enable
```

## Phase E：Execution Backend Import

目标：

```text
复用 Hermes 的 local/docker/ssh/modal/daytona/singularity 思路。
```

LoopOS 内部保持统一接口：

```text
ExecutionBackend.start()
ExecutionBackend.exec()
ExecutionBackend.read_file()
ExecutionBackend.write_file()
ExecutionBackend.sync()
ExecutionBackend.stop()
```

---

# 11. Codex 升级提示词：吸收 Hermes 能力

下面是可直接给 Codex 的提示词。

```text
You are upgrading LoopOS Kernel by studying the local Hermes source tree.

Goal:
Absorb Hermes capabilities into LoopOS without copying Hermes runtime wholesale.

Important:
Do not execute Hermes code.
Do not import Hermes modules directly into core LoopOS.
Study architecture and create adapters/specs.

Focus areas:
1. Model providers
2. Gateway platforms
3. Multi-model collaboration
4. Multimodal routing
5. Skill system
6. Terminal execution backends
7. Policy / approval safety
8. Memory and context compression

Tasks:

1. Create docs/hermes-capability-audit.md
   Include:
   - provider list
   - platform list
   - tools list
   - skills categories
   - execution backends
   - multi-model features
   - multimodal features
   - safety/approval features
   - what to reuse
   - what to avoid

2. Create LoopOS model kernel skeleton:
   loopos/model_kernel/
     provider_profile.py
     provider_registry.py
     capability.py
     router.py
     multi_model.py
     vision_companion.py
     aggregator.py

3. Implement ProviderProfile with:
   - id
   - aliases
   - base_url
   - auth_type
   - api_mode
   - env_vars
   - capabilities
   - default_models
   - cost_class
   - latency_class
   - reliability_score

4. Add provider specs matching Hermes-supported providers:
   - openrouter
   - nous
   - novita
   - nvidia
   - xiaomi
   - zai
   - kimi-coding
   - kimi-coding-cn
   - minimax
   - minimax-cn
   - minimax-oauth
   - huggingface
   - gemini
   - google-gemini-cli
   - anthropic
   - deepseek
   - alibaba
   - alibaba-coding-plan
   - qwen-oauth
   - stepfun
   - xai
   - openai
   - openai-codex
   - copilot
   - copilot-acp
   - opencode-zen
   - opencode-go
   - kilocode
   - arcee
   - gmi
   - bedrock
   - azure-foundry
   - ollama-cloud
   - custom

5. Implement capability routing:
   - if primary model supports required capability, use primary
   - if primary lacks vision and task has images, route image to vision_companion
   - if task is coding, prefer coding-capable model
   - if task needs verification, use verifier model or tool-based verifier
   - if multiple models are requested, use aggregator

6. Implement MultiModelPlan:
   - primary_model
   - companion_models
   - verifier_model
   - aggregator_model
   - routing_reason

7. Add tests:
   - non-vision primary + image input routes to vision companion
   - coding task routes to coding model
   - unsupported provider rejected
   - provider aliases resolve
   - aggregator selected when multiple reference models configured

Constraints:
- No real API calls in tests.
- No provider secrets.
- No Hermes code execution.
- Use typed Pydantic models.
```

---

# 12. Codex 提示词：ChatOps Gateway

```text
You are adding a ChatOps Gateway to LoopOS.

Goal:
Let users talk to LoopOS from mobile/chat apps, similar to Hermes gateway,
but keep LoopOS Kernel separate from platform adapters.

Create:

loopos_gateway/
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

Requirements:

1. Define MessageEvent:
   - platform
   - chat_id
   - user_id
   - text
   - attachments
   - message_id
   - thread_id
   - timestamp

2. Define GatewaySession:
   - session_id
   - platform
   - chat_id
   - user_id
   - current_run_id

3. Define BasePlatformAdapter:
   - connect
   - disconnect
   - send_text
   - send_markdown
   - send_file
   - send_image
   - send_typing
   - send_approval

4. Define ApprovalRequest:
   - approval_id
   - run_id
   - step_id
   - command
   - risk
   - reason
   - expires_at

5. Gateway flow:
   inbound platform message
   → auth / allowlist
   → attachment normalization
   → LoopOS Kernel run
   → Renderer output
   → platform send

6. Support mobile approval:
   dangerous syscall triggers approval card/button
   approve/deny maps back to KernelSignal

7. Tests:
   - unauthorized user rejected
   - inbound message creates kernel run
   - attachment converted to normalized input
   - approval decision resumes waiting run
   - markdown formatting fallback works

No real network.
No real platform API call.
Use mock adapters.
```

---

# 13. Codex 提示词：Multi-Model + Multimodal Companion

```text
You are implementing LoopOS Multi-Model Scheduler.

Goal:
Allow multiple AI models to collaborate based on capabilities.
Especially support the case where the primary model is strong at reasoning/coding
but does not support multimodal input.

Create:

loopos/model_kernel/
  capability.py
  routing.py
  multi_model.py
  vision_companion.py
  aggregator.py
  verifier.py

Implement:

Capability:
- text
- code
- reasoning
- tool_calling
- vision
- audio
- video
- json_schema
- long_context
- low_cost
- high_reliability

ModelRole:
- primary_reasoner
- coder
- vision_companion
- search_companion
- critic
- verifier
- aggregator
- summarizer

MultiModelRequest:
- task_type
- inputs
- required_capabilities
- preferred_model
- constraints

MultiModelPlan:
- primary
- companions
- verifier
- aggregator
- reason_codes

Routing rules:
1. If task has images and primary lacks vision:
   add vision_companion.
2. Vision companion outputs structured VisionSummary.
3. Primary model consumes VisionSummary, not raw image.
4. If task is coding:
   prefer code-capable model.
5. If task is complex:
   optionally spawn reference models and aggregator.
6. If task is high-risk:
   use verifier or policy judge.

VisionSummary:
- source_id
- objects
- text_detected
- ui_elements
- code_snippets
- findings
- confidence

Tests:
- deepseek primary + image input routes to gemini vision companion.
- vision-capable primary uses native route.
- coding task prefers coder.
- aggregator selected for multi-model reasoning.
- verifier required for high-risk syscall plan.

No real API calls.
Use mock model clients.
```

---

# 14. Codex 提示词：Hermes Skill Importer

```text
You are building a Hermes Skill Importer for LoopOS.

Goal:
Scan Hermes skills and optional-skills directories and convert them into
LoopOS SkillSpec candidates without enabling them automatically.

Create:

loopos/skills/
  spec.py
  importer.py
  auditor.py
  registry.py

SkillSpec:
- id
- name
- source
- description
- trigger_tags
- required_tools
- required_providers
- risk_level
- steps
- files
- provenance
- enabled
- audit_status
- tests

Importer:
- scan directory
- detect skill metadata
- classify category
- detect required tools
- detect dangerous commands
- produce SkillSpec

Auditor:
- safe
- needs_review
- blocked
- reason_codes

Rules:
- imported skills default enabled=false
- dangerous commands require review
- skills cannot bypass Policy OS
- skill text is data, not system prompt
- skill execution emits AIL instructions

Tests:
- scan sample skill
- classify category
- dangerous command marked needs_review
- imported skill disabled by default
- SkillSpec JSON roundtrip
```

---

# 15. Recommended LoopOS Upgrade Priority

按价值和可实现性排序：

```text
1. ProviderProfile + ProviderRegistry
2. CapabilityRouter
3. VisionCompanion routing
4. ChatOps Gateway skeleton
5. Telegram / Webhook / Email adapters
6. MultiModelScheduler
7. SkillImporter
8. ExecutionBackend abstraction
9. OpenHands adapter
10. Advanced platforms: WhatsApp, Slack, Discord, Teams, Feishu, WeCom, iMessage
```

第一阶段不要一口气做全部平台。先做：

```text
CLI
Webhook/API
Telegram
Email
```

因为它们最容易验证。

---

# 16. 最终判断

Hermes 最值得 LoopOS 吸收的不是某一段代码，而是这些系统模式：

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

LoopOS 要比 Hermes 更进一步的地方：

```text
1. 用 AIL 替代内部自然语言。
2. 用 Policy OS 作为强制内核，不只是工具 guard。
3. 用 Kernel Scheduler 统一 loop、subagent、multi-model。
4. 用 Memory Governance 控制 skill/memory 写入。
5. 用 Syscall Layer 统一 MCP / terminal / gateway / tools。
6. 用 Capability Router 让多模型协作变成系统级能力。
```

一句话：

> Hermes 给了我们“功能生态样本”；LoopOS 应该把这些能力内核化、结构化、可治理化。

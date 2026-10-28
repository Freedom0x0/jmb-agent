# 宿主选型调研（2026-10-13 第三轮）

本轮只答一个问题：**现成宿主能不能承接；不能的话自研要写什么。**
标注：`VERIFIED` = 本轮取到一手页面/源码；`NOT FOUND` = 没找到；`SECONDARY` = 二手。
本轮网络受限说明：部分子代理的 `WebFetch`/Bash DNS 被拦，走的是内置浏览器与 Node REPL 实际取页，均注明出处。

## 一、最重要的一条：我们的端点砍掉了 Anthropic 的现成能力

DeepSeek `/anthropic` 端点的官方兼容性表（VERIFIED https://api-docs.deepseek.com/guides/anthropic_api）：

| 能力 | 状态 |
|---|---|
| `tools`（name/input_schema/description） | Fully Supported |
| `tool_choice` none/auto/any/tool | 支持；`disable_parallel_tool_use` **被忽略** |
| `stream` / `system` / `temperature(0–2)` | Fully Supported |
| `thinking` | Supported，但 **`budget_tokens` 被忽略** |
| `redacted_thinking` / `document` / `search_result` / `mcp_*` 块 | **Not Supported** |
| `citations` / `tool_result.is_error` | **Ignored** |
| `anthropic-version` / **`anthropic-beta`** | **Ignored for /messages** |
| **`cache_control`** | **Ignored everywhere** |

由此得到四条硬结论：

1. **Anthropic 的服务端 context editing 用不了**——它要 beta 头 `context-management-2025-06-27`（VERIFIED platform docs），而 `anthropic-beta` 在我们的端点上被忽略。**长会话裁剪必须自己做。**
2. **Anthropic 的官方 memory tool（`memory_20250818`，`/memories` 目录 + view/create/str_replace/insert/delete/rename）也是 beta 门** ⇒ 同样不可用。**记忆的增删改接口必须自己写。**（VERIFIED 文档存在性与参数名）
3. **`cache_control` 被忽略 ⇒ 官方提示缓存的计费倍率（5 分钟写 1.25x / 1 小时写 2x / 命中 0.1x，最小可缓存前缀 512–4096 token，默认 TTL 5 分钟）我们一分钱都拿不到**（VERIFIED https://platform.claude.com/docs/en/build-with-claude/prompt-caching）。
4. **`tool_result.is_error` 被忽略** ⇒ 我们往工具结果里标的"这次失败了"这个信号，模型收不到。这是做工具循环时的真实功能损失，需要在正文里重复表达错误。

**上一轮我提的冲突就此改写**：原本我说"周期性重注入人格卡会打爆 DeepSeek 的 KV 缓存"（OpenClaw issue #96773 实测命中率在 20%/99% 摆动，一次会话浪费约 1500 万输入 token）。现在的准确说法是：**官方 `cache_control` 显式断点在这台端点上确定无效；DeepSeek 自家的自动前缀缓存是 OpenAI-API 那条路径上的特性，它在 `/anthropic` 路径上到底生不生效，本轮无法从文档判定 ⇒ 必须本机实测。** 也就是说：先别按"能省"设计，也别按"一定贵"设计。

**另两条端点事实（VERIFIED DeepSeek 官方文档）**：
- **DeepSeek 没有 embeddings 接口**，API Reference 只有 `Create chat completion`。⇒ 想要向量检索只能本地嵌入或换第三方付费嵌入服务。
- 它自己的文档里模型名写的是 **`deepseek-flash[1m]`（小写 m）**，而本机 `~/.claude/settings.json` 记的是 `[1M]`。OpenClaw 源码里 `[1M]` 大写处理 NOT FOUND。这条取值差异要靠实测确认。
- 认证：官方 `/anthropic` 页说凭据走 **`x-api-key`**；但它的 Claude Code 集成页用的是 **`ANTHROPIC_AUTH_TOKEN=<key>`**（Bearer）。本机会话环境正是 `ANTHROPIC_AUTH_TOKEN` ⇒ 两种模式都要能切，首次连接实测。

## 二、SDK 侧事实（VERIFIED，读 `anthropics/anthropic-sdk-python` 源码 + 官方 SDK 页）

- 客户端参数 `base_url` / `api_key` / `auth_token`；环境变量 `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`；默认 `https://api.anthropic.com`。头部就是 `{"X-Api-Key": api_key}` 或 `{"Authorization": "Bearer <auth_token>"}`。**注意**：`auth_token` 在官方文档页上 NOT FOUND，但源码里有——这是一处文档落后于实现的差异，不能当"不存在"处理。
- **SDK 现在用 `httpx2`（httpx 的 API 兼容分支）**，传普通 `httpx` 客户端会 `TypeError`；自定义 transport 走 `http_client=DefaultHttpxClient(transport=...)`。
- 打测试桩：官方 SDK 仓库自己用 OpenAPI spec 生成的 mock server + `inline-snapshot` + `--http-record` 录制回放；文档明确提醒 `respx`/`pytest-httpx` 默认看不见 SDK 的请求，要先调一次 `httpx2.alias_httpx()`。
- 花钱前的闸门有官方工具：`client.messages.count_tokens(model, system=..., tools=[...], messages=...)` 会把系统提示和工具定义计入输入 token（工具定义**确实**算输入 token）。文档警告这是估算，且 Claude 4.7+ 的新分词器多约 30%。**"persona+工具+索引一轮多少 token"这种通用数字：NOT FOUND** —— 只能用 count_tokens 自己量。

## 三、你硬盘上已经有一个几乎对口的宿主：hermes-agent

逐行核过（VERIFIED，读本地 clone）：

- **它是通用 agent 运行时，不是编程专用**：`tools/` 里有 browser、homeassistant、image_generation、`cronjob_tools.py`、computer_use、discord。MIT，Copyright (c) 2025 Nous Research，版本 0.18.0。
- **它对我们要用的那个端点有专门适配**：`agent/anthropic_adapter.py:504-528` 有个 `_is_deepseek_anthropic_endpoint()`，匹配 host `api.deepseek.com` + path `/anthropic`，用在 `:2264` 处理 unsigned thinking 的往返。另外 `agent/agent_init.py:347-351`：**任何以 `/anthropic` 结尾的 base URL 自动切到 Messages 协议**；`agent_init.py:655,695` → `anthropic_adapter.py:666-697` 把 base_url 一路传到 `Anthropic(base_url=…)`。1M 上下文映射在 `agent/model_metadata.py:253-257`。
- **人格/用户模型/记忆三件套就是上一轮调研的那套 markdown 形状**：`SOUL.md`（`agent/prompt_builder.py:1796-1823`，在 `agent/system_prompt.py:12` 作为 identity 注入）、`memories/MEMORY.md` + `USER.md`（`tools/memory_tool.py:57,188-189`）、跨会话 `state.db` SQLite **FTS5**（`hermes_state.py:123`）。
- **它会自己写技能**：`tools/skill_manager_tool.py:776` `_create_skill`，加上 `agent/background_review.py`（后台复盘分叉）和 `agent/learning_graph.py:201`。**这正是"根据经历改变行为"的实现。**
- 原生 Windows 有路径：`hermes_constants.py:117` ⇒ `%LOCALAPPDATA%\hermes`。Python 要求 `>=3.11,<3.14`（本机 3.13.15 ✓）。入口 `hermes` / `hermes-agent` / `hermes-acp`。还有个精灵子系统 `agent/pet/`。
- **阻塞事实（不能忽略）**：这是 `guoshaoran/hermes-agent` 的**个人 fork**，停在 `fix/projects-enabled-gate-58588` 分支，最后提交 2026-07-09；工作区脏，有 4 个 `plugins/*/dashboard/dist/*` 被删；7,960 个文件；上游是 Nous 的研究运行时。**它没有"陪伴/情感"模式**，只有 persona + 用户建模。
- 好消息：`origin` 指向个人 fork，而 `git remote -v` 说明上游可拉；本机有 `.venv/`（是否可用待查）。

## 四、OpenClaw 能干，但代价被量化了

VERIFIED（官方 docs 逐页 + GitHub API）：

- 事实：MIT，copyright "OpenClaw Foundation"，无附加条款；`pushed_at 2026-10-13`；最新 release `v2026.10.2`（2026-10-12）；未归档；391,822★；**top-12 贡献者里 `steipete` 一人占 60,012 commits ≈ 67%**；仓库 size 约 9 GB。
- Windows：官方支持，有 **原生 Windows Hub 应用** + PowerShell 安装器 `iwr -useb https://openclaw.ai/install.ps1 | iex`，也提供 WSL2 Gateway。**但 `package.json` 的 `engines.node` 是 `">=24.16.0 <25 || >=26.1.0"`**，Node 22/23/25 明确不支持（原因是 `node:sqlite` 的 WAL 损坏 + TEXT-NUL 截断 bug）。**本机 nvm 当前链的是 22.22.0 ⇒ 必须先升 Node。** Bun 1.4.0+ 是文档化的替代运行时，Tauri 应用自带私有 Bun。
- 需要常驻：**是**。Gateway 监听 `--port 18789`，Windows 上的托管启动方式是**计划任务（S4U，boot+logon 触发）**——注意这和上一轮说的 `schtasks` 是同一条路，他们已经铺好了。
- **自定义端点：能。** 官方向导明写支持 "OpenAI-compatible、OpenAI Responses-compatible、**Anthropic-compatible**"，flag 为 `--custom-base-url` / `--custom-model-id` / `--custom-api-key` / `--custom-provider-id` / `--custom-compatibility <openai|openai-responses|anthropic>` / `--custom-image-input`。配置键：`models.mode:"merge"`、`models.providers.<id>.baseUrl/.apiKey`（支持 `${ENV_VAR}`）/`.api:"anthropic-messages"`/`.headers`/`.timeoutSeconds`、`agents.defaults.model.primary`、`params.context1m: true`。**并且它有一条专门给代理端点加固的行为**：非 `api.anthropic.com` 的 `anthropic-messages` 路由上，OpenClaw **主动抑制隐式 beta 头**（`claude-code-20250219`、`interleaved-thinking-2025-05-14`）——正好对上我们的端点会忽略 beta 头这件事。
- **`ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN` 这些环境变量在它的文档里 NOT FOUND**（它只认 `ANTHROPIC_API_KEY`）⇒ 本机那份 env 需要重映射，不能直接继承。
- **记忆是可插拔的独占槽**，这是本轮最关键的架构发现：`api.registerMemoryCapability(capability)`（文档原话"the exclusive memory-plugin API"）、`api.registerContextEngine(id, factory)`（同时只能有一个生效）、`api.registerEmbeddingProvider(...)`，还有 pre-compaction flush 的 `flushPlanResolver` 带 **tools arm**（`persistenceToolNames`/`lookupToolNames`）——意思是**插件可以用自己的工具做持久化，而不是被它的文件契约绑住**。槽选择键 `plugins.slots.memory`。另有 typed hooks（`before_model_resolve`、`before_tool_call`、`agent:bootstrap`、`session:compact:before/after`、`cron_reconciled`）和 MCP 客户端支持（`mcp.servers`，stdio/streamable-http/SSE）。**⇒ 你的 Context Forge 可以去占这个记忆槽，而不必被它的 markdown 布局替换掉。**
- **上一轮我那句话要修正**：我说做梦机制的准入门是"三个确定性阈值"。事实是——门确实存在（`minScore`/`minRecallCount`/`minUniqueQueries` 三者全过），但**文档明写这三个是 internal、不面向用户**；信号权重被写死为 `0.30/0.24/0.15/0.15/0.10/0.06`。可配的只有：`enabled`（默认 true）、`frequency`（默认 cron `0 3 * * *`）、`timezone`、`model`（需 `subagent.allowModelOverride: true`）、`phases.deep.maxPromotedSnippetTokens`（160）、`phases.deep.maxPriorEntryLossFraction`（**0.25**）。撤销有 `/dreaming on|off|status`、`memory promote --apply`、`rem-backfill --rollback`。Workshop 侧可配 `skills.workshop.autonomous.mode`（默认 `"auto"`）、`maxSkillBytes` 40000、`restore --version`。
- 默认嵌入用的是 **OpenAI `text-embedding-3-small`**，provider 列表含 `lmstudio|local(llama.cpp)`；**没配 provider 时只做关键词检索**（这与我们"DeepSeek 无 embeddings 接口"的现状吻合，不是阻塞项）。
- **成本默认值（都是文档化的）**：心跳每 **30 分钟**一整轮 agent（只有当解析到 Anthropic OAuth/token 且未显式设 `heartbeat.every` 时才自动降到 1 小时）；`0m` 关闭；事件唤醒有 30 秒最小间隔和 5 次/60 秒防洪。做梦每 agent 每天一次 cron（`0 3 * * *`），每次两遍补全（日记 + 深度整合）。自学每 **10 次模型迭代**排一次后台复盘。压缩阈值驱动，`memoryFlush.softThresholdTokens: 6000`、`forceFlushTranscriptBytes: "2mb"`。**⇒ 常驻心跳就是 48 次/天的模型调用，这是我们唯一确定要花大钱的一格。**
- 风险量化：**158 个 Windows 标题相关的未关 issue**，其中 #143524（SQLite WAL 涨到 1.4–2.8 GB **阻塞 gateway 启动**）、#168955（2026.10.1 启动回归约 1030 秒）、#146860（更新交接卡住）、#157812（自动更新失败）、#162585（插件源码 staging 不收敛，612 MB）、#167652（升级后挂起）、#140010（睡眠/唤醒后 WebSocket 重连）。文档还提示杀软干扰，以及 WSL≥2.6.1 空闲回收的绕法。
- 附带一条**已经有人踩过同一个端点**：issue #151861（已关）就是"模型端点为 Anthropic 兼容接口"，上游报错原样吐出 "supported API model names are deepseek-flash, deepseek-v4-pro"。**注意这里出现的第二个模型名是 `deepseek-v4-pro`，不是本机配置里记的那个。**
- 另一条相关实测：#96773 —— 每轮注入 `SOUL.md`/`IDENTITY.md`/`USER.md` 打爆 **DeepSeek** 的 KV 缓存，命中率在 20%/99% 摆动，一次会话约 1500 万输入 token 白烧。**注意这条是"该端点自带前缀缓存存在但极不稳"的间接证据，和"cache_control 被忽略"并不矛盾：一个是显式断点无效，一个是自动前缀缓存不稳。**

## 五、Letta 已经换形态：Python 服务端没了，但新版更对口

VERIFIED（GitHub API + 官方 docs）：

- README 原话（VERIFIED）："Letta (f.k.a. MemGPT) is actively developed. **The current source code lives in `letta-ai/letta-code`**"。`letta-ai/letta` 只剩 7 个文件（无 Python 包），25,122★，最后 push 2026-09-10。新仓库 **Apache-2.0，TypeScript，3,593★，最后 push 2026-10-13，v0.34.13（10 月 13 日）**。
- **`~/.letta/lc-local-backend/memfs/<agent-id>/memory`**，可用 `LETTA_LOCAL_BACKEND_DIR` 覆盖，"no Letta account is required"，**"The CLI runs agents in-process"** ⇒ **不需要常驻服务**（可选：`letta server --backend local --listen ws://127.0.0.1:4500`）。
- **MemFS = git-backed 记忆文件系统**，条目"projected as **Markdown with YAML frontmatter**"，"a real checkout the agent reads and edits with ordinary file tools" ⇒ 可外部播种、可外部编辑、自带版本。
- **检索默认不带语义/向量索引**（文档原话 "does not include a semantic or vector index by default"），要语义搜索得装外部 indexer。**这条正好绕开"DeepSeek 没有 embeddings 接口"。**
- 自我改写：后台进程"consolidate useful lessons"，触发是"完成一定步数后"或"上下文被压缩时"，`/sleeptime` / Dream 设置可调，写入可用 **"Agent reviews before applying"** 闸门；权限走 `.letta/settings.json` 的 `deny`，且**别的 agent 的记忆目录受保护**。README 记了 `LETTA_ENABLE_WINDOWS_AUTO_REFLECTION=1`。
- 人格：`letta --new-agent --personality tutorial`，有持久身份。**mood/relationship：NOT FOUND。**
- **阻塞事实**：自定义 provider 的官方路径只文档化 **OpenAI-compatible Chat Completions + tool calling**（`/connect` 填 base URL + key）；**Anthropic-compatible 自定义 base URL：NOT FOUND** ⇒ 走 `api.deepseek.com/v1`，不是 `/anthropic`。Node 22.19+（本机 22.22 ✓）。cron 只在"CLI 或 server 进程开着"时触发 ⇒ 主动性要另外解决。Windows 相关 issue 89 个，含 #4967（桌面版卡在 "Connecting"）、#3885（长路径）、#4159（Bash 超时）、#4651（dream + Windows timeout safeguards）。
- 商业面：文档 pricing 记 free = 3 个 stateful agents、Pro/API $20/mo、$0.10/active agent（照抄页面，未验价）。

## 六、其他宿主/组件（一次性列完）

- **deepseek-harness（`dsh`，你已 clone，MIT，DeepSeek 官方）**：协议三选一 `openai-completions | openai-responses | anthropic-messages`（`packages/llm/llm-pi-ai/src/provider.ts:48-52`），自定义 `baseURL`+`apiKeyEnv` 一路传到请求（`catalog.ts:502-532`）⇒ **`api.deepseek.com/anthropic` 在这里是一行配置**。有一等公民的 persona 槽（`packages/preset/persona`，`complete: true` 时独占整个 system prompt）、会话持久化 sqlite/jsonl、`$DSH_HOME/AGENTS.md` 指令、文件系统 skills。阻塞事实：**`node_modules` 全缺 ⇒ 现在什么都跑不起来**；内置 DeepSeek 插件是 chat/completions 且纯文本（`llm-deepseek/src/adapter.ts:335`），Anthropic 路线要手写；**完全没有记忆/学习包**（`find packages -iname "*memor*"` 零命中）⇒ 行为改变要自己作为插件加。
- **Agent Zero**（MIT，19,448★，v2.13 2026-09-23，pushed 2026-10-12）：LiteLLM 多 provider（`conf/model_providers.yaml` 里 `kwargs.api_base` 可指 Anthropic 兼容端点——**这是从键名推断的路径，没有 DeepSeek 现成例子**）；嵌入可以本地免费（`lm_studio`/`ollama` api_base）。记忆四区 `MAIN/FRAGMENTS/SOLUTIONS` + `SKILL.md`，但**FAISS 向量索引锁死**，手改文件后索引要不要重建：文档无保证（NOT FOUND）。巩固配置 `memory_memorize_enabled`、`memory_memorize_consolidation: true`、`memory_recall_interval: 3`；**是否定时/手动：UNVERIFIED**（读不到 `memory_consolidation.py` 正文）。Windows 侧 Docker 优先，且 open issue **#1821：Windows x64 安装器触发 Defender 木马告警**。
- **SillyTavern**（**AGPL-3.0**，2,026-10-08 push，23,719 KB，23,133★）：角色卡 V2 全字段 + `character_book.entries`（`keys/secondary_keys/content/constant/selective/position/priority/insertion_order/enabled`）；World Info 关键词触发 + 可选语义触发带 token 预算；后端明确列了 **Claude (by Anthropic)** 和 **DeepSeek**。**阻塞事实：文档明说"only an interface"，headless/programmatic 用法 NOT FOUND**，且是常驻 Node 服务。人格/lorebook 这套分层设计可以直接抄，代码不要接（AGPL）。
- **RisuAI**（GPL-3.0，1,725★）：HypaMemoryV2/V3 记忆压缩、SupaMemory 上下文管理、可重排提示/条件/变量。同样偏 UI。
- ** AnythingLLM Desktop**（MIT，67,003★）：**"AnythingLLM Native Embedder" 进程内嵌 + LanceDB** ⇒ 想要向量又不想起服务、不想再付一份 API，这是唯一现成解。没有 persona/关系层，记忆按 workspace/chat 作用域。
- **FieriA**（MIT，Python，**1,925 KB**，1★，pushed 2026-08-04）：README 原话——记忆就是 `fieria_home` 里的 markdown，含 `MEMORY.md` 和 daily logs，"a scheduled loop handles tasks like daily journals at midnight"，provider 为 Gemini/OpenAI/Ollama。**这是"最小可抄形状"最贴的一个**，但 1★、无 Anthropic 兼容 provider、文档日文。
- **engram**（MIT，Go，35,864 KB，**7,160★**，pushed 2026-10-13）：一个二进制 + **SQLite FTS5** 全文检索，暴露 CLI/HTTP/MCP/TUI。**证明"纯关键词的个人长期记忆"是被广泛采用的正规做法，不是妥协。** 同类更小的：`fellowgeek/mcp-memory`（MIT，73 KB，217★，SQLite FTS5）、`sessiongrep`、`remindb`。官方依据 sqlite.org/fts5.html 的 `bm25()`。
- **WinClaw / Khoom / Luciduz / pygpt**：全部 NOT FOUND 或低信任克隆（`WinClaw` 是 10 个蹭名仓库，其中 `kfmdmteam/winclaw` 自称 Go 单二进制 125 KB，0★）。`pygpt` 仓库与账号都 404。
- **codex-pets（你已 clone，openai/codex，Apache-2.0，clean）**：稀疏检出只含 `codex-rs/tui` + skills；`codex-rs/tui/src/pets/{ambient,asset_pack,catalog,frames,image_protocol,model,picker,preview,sixel}.rs`，上游提交 `feat(tui): add ambient terminal pets (#21206)`。**这是终端 Sixel/iTerm2 精灵，不是常驻桌面陪伴**，但"素材包/帧模型"这套如果要视觉在场值得抄。本机另有 `~/.codex/pets/ikun.codex-pet/`。
- 死路（本轮逐行确认）：**my-harness**（`src-tauri/src/agent_runtime.rs:59-62` 明确只接受 `openai-compatible/openai`，且只会拼 `/chat/completions`，无工具调用、`stream:false`）；**peaks-loop**（reviewer 端点 `providers/anthropic.ts:9` 硬编码 `https://api.anthropic.com/v1/messages`，无法改指）；**how-to-build-a-coding-agent**（协议对但是 Go，且 `chat.go:132` 硬编码 `ModelClaudeOpus4_6`，无 LICENSE 文件）；jcode/SkillAbout/knowledge 无运行时。

## 七、`schtasks` 这条主动性路径

- 微软文档（VERIFIED）：`schtasks /create /sc {MINUTE|HOURLY|DAILY|ONCE|ONSTART} /tn /tr [/mo /st /rl /f /xml <xmlfile>]`，`/it` = 只在"运行该任务的用户已登录"时执行 ⇒ 陪伴类想要的语义。
- **但没有任何主流 OSS 陪伴 agent 用它**（repo 搜索 `schtasks` 出来的基本都是安全 PoC）。已核到的三种真实做法：**OpenClaw = 计划任务托管 gateway（S4U）**、**Khoj = 自己 server 内的 Automation**、**FieriA = 进程内定时循环**。⇒ 我们不是"选一条标准路"，是"这三条里挑一条再自己写"。

## 八、本轮"明确不采纳"

1. **Anthropic 官方 memory tool / server-side context editing / compaction** —— 三者都依赖 beta 头或 `cache_control`，我们的端点忽略。
2. **SillyTavern / Agent Zero / Open WebUI / Cherry Studio 作为宿主** —— AGPL 或 Docker-first 或纯 UI；`headless NOT FOUND`。
3. **本地推理（ollama / LM Studio / koboldcpp）** —— 本机没有，且他的既定偏好是不装。
4. **把 Context Forge 换成 OpenClaw 的 markdown 记忆** —— 它的记忆槽是独占可插拔的，插件可以用自己的工具持久化，不必替换内核。
5. **把 OpenClaw 的心跳按默认 30 分钟直接用** —— 48 次/天的整轮模型调用，在有缓存也救不了的情况下要先算账（见下节未验项）。

## 九、本轮结束后仍未定的四件事（都不是文档能答的）

1. **DeepSeek `/anthropic` 上自动前缀缓存到底生效吗** ⇒ 只有同一前缀打两次、比对 usage 才能定。这条决定"人格/记忆每轮注入"的单价。
2. **本机那份 `~/.context-forge` 的 `all-MiniLM-L6-v2` 权重在不在**（它的嵌入是 `HF_HUB_OFFLINE=1`，缺权重就静默退回 BM25）⇒ 决定要不要接受"永久关键词检索"。
3. **`hermes-agent` 那个 fork 现在能不能起**（`.venv` 是否可用、被删的 `plugins/*/dashboard/dist` 是否致命）。
4. **模型名 `[1m]` 与 `[1M]`、`auth_token` 与 `api_key` 这两组取值，哪个被端点接受**（issue #151861 里吐出的可选名是 `deepseek-flash, deepseek-v4-pro`）。

以上四条我能在本机验，第 1 和第 4 条会产生真实模型调用费用 ⇒ 等他点头再跑。

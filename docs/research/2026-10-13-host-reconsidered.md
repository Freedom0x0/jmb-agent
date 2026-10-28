# 宿主/入口重查（2026-10-13 第六轮）

起因：用户提出"能不能别自研，直接在 Claude Code 上写"，随后补一句"我推荐 CC 是因为我只用过 CC，或许有更好的选择，你去调研，不要盲目听我的建议"。
本轮同时查：CC 当宿主实际给什么、CC 之外有什么、以及**用他自己的数据验证"学习发生在 CC"这个前提**。

## 一、他的前提"我大部分学习都在 Claude Code 里"——**一半不成立**（用他本机数据量的）

先读这份，因为它会改变整个设计的落点。

**成立的那半**：
- CC 确实是他最大的 AI 面。`~/.claude/projects` = **314,378,767 B（约 300 MiB）/ 189 个会话 / 21 个项目目录**。对照 `~/.codex` = 163,559,729 B / 122 JSONL，`~/.qoder-cn/projects` = 118,959,268 B / 74 JSONL。
- 内容确实是计算机、确实要写代码。最大的几个仓：`my-agent` 84.3M/43、Context Forge 54.5M/43、`my-harness` 23.7M、`qoder-harness` 21.8M/29、MyBlog 14.6M、`code-mentor` 11.9M。

**不成立的那半（学习不在 CC）**：
1. **学习词 : 交付词 = 1 : 7**（出现次数 5,037 vs 35,134）。拆开看：`测试` 14,637、`组件` 6,157、`接口` 5,528、`提交` 4,256、`需求` 3,365、`部署` 1,191，而 `解释` 2,939（工程常用词，不算学习）、`学习` 1,847、`什么是` 111、`教程` 69、`练习` 69、**`怎么理解` 1、`复习` 1**。文件级命中 121/189 只因"解释/测试"是普通工程词，不具判别力。
2. **他那个记忆库里，学习相关条目是 0。** Context Forge 314 条记忆的标题扫描：`学习 0`、`教程 0`、`练习 0`、`复习 0`、`概念 0`、`课程 0`、`笔记 0`、`理解 0`、`什么是 0`、`解释 4`。全部是代码工作记忆（TypeScript 62、React 62、Ant Design 43、umi 35、Zustand 25；domains：auth 44/form 38/api 38/memory 32/routing 30）。个人向只有 `goal 10`、`habit 1`，`health/sleep/emotion/interest 0`。
3. **学习痕迹在 CC 之外**：`Desktop\xj\JavaScript高级程序设计（第4版）.pdf` **14,750,250 B**；Obsidian 两个库——`Documents\Obsidian Vault`（22 个 md / 385 KB，分"前端知识 6 / 工作经验 5 / ai coding 相关 3 / 服务器相关 2 / agent 2 / blog 1"，**最近还在 2026-10-13 编辑**）和 `Desktop\konwledge_base`（567 个 md，但其中 context-forge 文档 549 + code-mentor 17，那是产品文档不是学习笔记）。
4. **浏览器才是查资料的地方**：Chrome `User Data/Default/History`（21.5 MB，6,882 条 URL / 28,282 次访问，最新 2026-10-14）里 github 752 条/1,840 次、google 456（其中 search 303）、feishu 395、csdn 61、zhihu 38、bilibili 29、runoob 14、juejin 11、youtube 8、MDN 2、wikipedia 2、arxiv 4。**notebooklm 0、notion 0。**
5. **作息是工作日型，不是晚自习型**：`history.jsonl` 5,152 条带时间戳的提问（2026-07-01→2026-10-14，81 个活跃日）按本地小时分布：09→369、10→525、11→477、12→172、13→386、14→559、15→614、16→579、17→647、18→327，然后 19→121、20→160、21→62、22→38、23→53，**02:00–08:59 全空**。
6. **一条很说明问题的旧伤**：`~/.claude/knowledge/config.json`（86 B）把 vault 路径写成 `D:/Obsidian base/personal knowledge base`，而**这台机器只有 C: 盘** ⇒ 他早就试过一条"知识/笔记"通路，因为一个不存在的路径从没跑起来过。

**⇒ 结论**：CC 是他的**工作现场**，不是学习现场。陪伴体若住在 CC 里，它到达的是"干活"，而"读资料 + 记笔记 + 啃那本 PDF"这三处**现在没有任何 agent 在场**。

## 二、CC 当宿主的实测得失（读官方文档 + 本机实测）

**能用的三件**：
- **人格槽确实存在**：`claude --help` 有 `--system-prompt`（官方 `cli-reference.md` 原话 "**Replace** the entire system prompt with custom text"）和 `--append-system-prompt`（只追加到默认末尾）。另外 **output styles 是那个"去掉编程指令但保留工具"的位置**——文档原话：full system prompt 上，自定义 output style **leave out** Claude Code 那段 built-in software engineering instructions，除非 `keep-coding-instructions: true`。
- **挂点齐全**：官方 `hooks.md` 实测列出 **32 个事件**，其中 `UserPromptSubmit` "fires when a prompt is submitted, before Claude processes it"，支持 `decision: "block"` + `reason`，并且能注入 `additionalContext`。⇒ 采集学习事件 + 拦截记忆写入这两个需求，CC 的钩子都给得了。
- **会话持久化确实有**：`-c/--continue`、`-r/--resume`、`--session-id`、`--fork-session`；转录在 `~/.claude/projects/<cwd-slug>/<uuid>.jsonl`。`cleanupPeriodDays` 默认 30，且**记忆文件不在清扫范围内**。
- **一个真实可用的隔离杠杆**：官方 `memory.md` 上确认存在 `autoMemoryEnabled` / `autoMemoryDirectory` / `CLAUDE_CODE_DISABLE_AUTO_MEMORY` / `claudeMdExcludes` / `cleanupPeriodDays`（grep 命中 4/3/2/6/2 次；注意这些只写在 `memory.md`，`settings.md`/`settings-reference.md` 上 0 命中）。他 `settings.json` 顶层只有 7 个键 ⇒ **全部处于默认**，也就是 auto-memory 正在默认位置跑。

**否决它的实测理由（六条，都很硬）**：
1. **默认提示词明写是给编程的**。文档原话：默认样式下 "Claude works from Claude Code's standard system prompt, **which is written for software engineering tasks**"。
2. **把提示词换掉会砍坏宿主**。`--system-prompt` 丢掉 CC 的工具使用段落，且 `--exclude-dynamic-system-prompt-sections` 在与 `--system-prompt` 同用时被忽略。
3. **每轮都背着一堆不相干的东西**（本机实测字节）：用户技能 **159 个 SKILL.md、frontmatter 共 54,153 B** + 插件技能 **363 个、249,204 B** ⇒ **约 303 KB 的技能描述**；内置工具 **48 个**（官方 `tools.md` 数出来的）；MCP 用户 1 个 + 插件声明 4 个。一句"今天过得怎么样"要为 `NotebookEdit`、`vitest-testing`、`migrate-radix-to-base` 付钱。`--bare`/`--tools ""` 存在，但 **`--bare` 会连他的 Context Forge 钩子和 CLAUDE.md 发现一起跳过**。
4. **subagent 不是聊天载体**（这条直接否掉我上一屏给的"②subagent"选项）。文档原话："Each subagent starts with a **fresh, isolated context window**. It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read." 用户直接对 subagent 说话要"type into its transcript to resume it yourself"——不是陪伴级的界面。
5. **按 cwd 的记忆污染已经发生，不是风险**。`~/.claude/projects/*/memory/` 下实测 **79 个 auto-memory `.md`**，其中公司主仓 `…platform-web-platform-web-main/memory` 有 **9 个**、`…prompt-prompt-project/memory` 有 **13 个**。若陪伴会话的 cwd 落在工作仓，它的"情感笔记"就写进同一个按仓作用域的库；而 `claudeMdExcludes` **不排除 auto-memory**，`claude purge` 会把转录和记忆**一起删**。
6. **指令位已经很挤**：他有 21 个项目目录、15 个 `AGENTS.md`、一个 **114,575 B 的 `xj/my-harness/CLAUDE.md`**、一个 `~/.claude/CLAUDE.md`（806 B，内容只是"优先用 CodeGraph 而不是 grep"），还有一个 `output-styles/peaks-skill-swarm.md`（6,945 B）**归 peaks-cli 所有、按它自己的横幅说明"下次升级会覆盖"**。一份陪伴人格的 CLAUDE.md 要在同一个位里和公司仓的策略竞争。
- 补一条：钩子链也挤。`claude-mem@thedotmack` 已占 `UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop, SessionStart, SessionEnd, PreCompact, Setup`；`ecc@ecc` 占 `PreToolUse, PostToolUse, PostToolUseFailure, Stop, SessionStart, SessionEnd, PreCompact`；Context Forge 自己占 `PreCompact/SessionEnd/SessionStart` 三个点。
- 权限模型也是编程概念：可选 `acceptEdits/auto/bypassPermissions/manual/dontAsk/plan`，而陪伴体需要往记忆目录写文件，正是这些模式别扭地拦的东西。

## 三、"要不要自建"的诚实基线：现成产品今天给到什么（官方页今日取）

- **Claude Projects**：官方说法是"self-contained workspaces with their own chat histories and knowledge bases"，可上传文档/文本/代码，每个项目有自己的 project instructions（含角色/人格框架）。免费版限 **5 个项目**。（support.claude.com/9517075）
- **Claude 记忆**：**默认开启**；账号级合成"每 24 小时更新"，且**明确不包含 project 里的对话**；"Each project has its own separate memory space and dedicated project summary"；可在 Settings > Capabilities 查看/编辑，可用铅笔图标写自定义记忆指令；可"Reset memory"（永久）；incognito 排除；**"All memory data is included in data exports"**；搜历史对话是付费档。（support.claude.com/11817273）
- **ChatGPT 的官方名字确认了：dreaming**。官方页（openai.com/index/chatgpt-memory-dreaming/，2026-06-04）原话：2024-04 上线 saved memories，**2025-04 引入 "dreaming — a method for ChatGPT to automatically curate memories in the background by referencing chat history"**，本次新架构建立在 dreaming 之上，演进序列写作 Saved memories (2024) → Saved memories + Dreaming V0 (2025) → **Dreaming V3 (2026)**；合成记忆在 "memory summary page" 可看可改。
  ⇒ 修正上一轮：我当时写"是否有独立 emotional reliance 章节未核实"，dreaming 这个名字本轮**已核实**（但 ChatGPT Projects / 记忆导出 / 记忆 API 仍 NOT FOUND，help.openai.com 对本环境一律 403）。
- **Gemini Gems / NotebookLM**：support.google.com、gemini.google.com、ai.google.dev、blog.google、notebooklm.google 从这台机器**全部连不上**（不是 403，是连接失败）。⇒ 任何关于它们的说法都当"未验"处理。顺带一条检索命中的标题暗示 Gems 正被"skills"取代——不可验证，但本身就是供应商摆动信号。

**代价（都取自官方页）**：
- 陪伴住在聊天应用里，**不在键盘旁边**：没有文档化的记忆 API，读不到 `~/.claude/projects`，项目记忆按项目围栏 ⇒ **它看不见他真正写的代码**。
- 存储是单向的：官方导出文档原话 "**Exported data can't be imported into another personal Claude account**"；删对话不删派生记忆（"related memory entries generated from it won't be removed"）；legacy memory 的导出选项有 **2026-09-09** 的过期日。
- 地基会被换掉：供应商自己承认旧记忆"stale/incorrect"并重构过两次。用户对人格被撤的反应，本轮只有二手来源（change.org / garanteprivacy.it / char.ai 站全部不可达），所以 #Keep4o、Replika ERP、Character.AI 未成年限制这三条**降为 SECONDARY**——上一轮我引过的 Keep4o/Replika 一手页本轮没再取到，如实标注。
- 若开 "Model Improvement"，聊天与"custom styles or conversation preferences"都可入训练；**connector 与本地/远程 MCP 服务器的原始内容被排除**；点赞点踩反馈保留至多 5 年。

## 四、"读编码会话当记忆源"已经是商品（都是已核实存在的仓库）

| 项目 | 许可证/星 | 实际机制 |
|---|---|---|
| **claude-mem** | Apache-2.0，**100,462★**，pushed 2026-10-13 | 生命周期钩子 → 每用户端口的 HTTP worker → SQLite + FTS5（+可选 Chroma）→ SessionStart 注入上轮上下文；对外是 **3 个 MCP 工具** `search/timeline/get_observations`；文档给了 3 层 token 模式（50–100 vs 500–1,000/条）。有 `CLAUDE_MEM_SESSION_START_INCLUDE_ALL_SOURCES` 把所有 harness 喂进同一上下文；**还有"Claude Desktop Skill"= 在聊天客户端里查同一个库**。默认 provider 是托管的 CMEM Pro |
| **engram** | MIT，**7,176★**，pushed 2026-10-14 | Go 单二进制，`~/.engram/engram.db`（SQLite+FTS5），**CLI / HTTP API / MCP stdio（26 个工具）/ TUI 四种出口**；按项目作用域读；Git Sync 导出可移植分块 |
| **sessiongrep** | Apache-2.0，38★ | **直接从盘上读** `~/.claude/projects`、`~/.codex/sessions`、`~/.cursor/projects`；**只索引 prompt + reply，故意排除工具输出和注入上下文**；一个 SQLite+FTS5 缓存；CLI/TUI + `sessiongrep-mcp`（`search_sessions`/`get_session`）；文档说"想要就删了重建"。**Windows 无预编译包**（只有 macOS/Linux） |
| context-mode | **ELv2（非 OSI）**，28,291★ | 钩子 + 11 个 MCP 工具，SQLite/FTS5 会话连续事件，压缩时用 BM25 召回 |
| mcp-memory-service | Apache-2.0，2,013★ | 官方原话 "Memory is shared across all agents and runs"，SQLite 本地单用户后端，客户端覆盖 Claude Desktop / Claude Code / Codex / Gemini / VS Code / Cursor / Zed |

⇒ **"把一个 agent 的会话喂进共享记忆库，再让别的客户端查它"不用写**。真正没人做的是**人格与情感连续性**——上面五个没有一个文档化了人格文件或陪伴语气。

## 五、"自研最小 loop"这件事我上一轮也说重了——有现成薄客户端

- **`simonw/llm`**（Apache-2.0，**12,621★**，pushed 2026-10-13）官方 usage 页实测：
  - 可对**任意 OpenAI 兼容 Chat Completions 端点**跑对话：`uvx llm openai endpoint http://… -m … --chat`（`--key`）
  - `-s/--system '…'` **放人格**；prompts/responses 存在它自己的 SQLite 里；`llm -c` / `llm chat -c` **续上一次对话**；templates/fragments 可把人格存成文件
  - MCP 工具要靠 **`simonw/llm-mcp-client`**（Apache-2.0，仅 15★）"Expose the tools from an MCP server as LLM tools"
  ⇒ 这是最贴近"薄 loop + 人格文件 + 共享 MCP 库"的现成件，**我不该自己写那个 loop**。
  **但两处必须本机验才能进设计**：① 它能否指我们的 `api.deepseek.com/anthropic`（文档实测到的是 **OpenAI 兼容**那条；否则要退到 `/v1`，而 `/v1` 我们**没实测过**）；② `llm-mcp-client` 只有 15★，MCP 客户端这条路成不成没验。
- **Crush**（charmbracelet，**FSL-1.1-MIT，非 OSI**，28,628★）：TUI，README 实测支持 "OpenAI- 或 **Anthropic-compatible** APIs"、session-based 多会话、MCP（`http`/`stdio`/`sse`），且有**全局人格文件 `~/.config/crush/CRUSH.md` 与 `~/.config/AGENTS.md` 注入 system prompt**。提示词能否整体替换：NOT FOUND。
- aichat（Apache-2.0，10,497★）：Role = "a prompt and model configuration"（每档 system prompt）+ Session 连续，但 **MCP 只在 README 出现一次、无文档**，且最后 push **2026-02-23**。mods 已**归档**（2026-03-09 官方停更，转投 Crush）。
- 其他宿主候选（一票否决项都记着）：**LibreChat**（MIT，要 Node **v24.16.0** + MongoDB，文档明说**不是原生 Windows 应用**）；**Open WebUI**（自定义许可/NOASSERTION，v0.12.0，Anthropic 连接可填自定义 URL、每模型 System prompt、SQLite `chat`/`chat_message` 落盘，但**MCP 仅管理员**、quick start 要 Python **3.11/3.12**）；**Cherry Studio**（AGPL-3.0，**原生 Windows 安装器**，支持 OpenAI/Gemini/**Anthropic 规范**第三方服务商，MCP，自定义助手）；**SillyTavern**（AGPL-3.0，`Start.bat` 原生 Windows，Node≥20，有 Persona 角色卡 World Info 全套陪伴 UX，**MCP NOT FOUND** ⇒ 人格够不到工具和代码）；**AnythingLLM**（MIT，桌面版 Mac/Win/Linux 一键，"Automatic & User Managed Memories" + MCP-compatibility，但字段级文档今日 403 ⇒ 只能 SECONDARY）；Jan（离线定位，远端 URL/每助手提示 NOT FOUND）；LobeChat（**LobeHub Community License**，非 OSI）；ChatWise（无源码，闭源）。Codex CLI 的 `config.schema.json` 实测 `ModelProviderInfo.base_url` 注释是 "provider's **OpenAI**-compatible API" 且 `WireApi` 只有 `"responses"` ⇒ **说不了我们的 `/anthropic`**；Gemini CLI 无 Anthropic/OpenAI 兼容 base URL 与提示替换（NOT FOUND）；OpenCode（MIT，自定义 provider 走 `@ai-sdk/openai-compatible` + agent prompt 可整替 `"prompt": "{file:./prompts/x.txt}"`，`--continue/--session` 有，但 **Anthropic 格式自定义 URL NOT FOUND ⇒ 也是走 `/v1`**，Windows 需 `OPENCODE_GIT_BASH_PATH`）。

## 六、MCP 规范给的一条硬约束（决定后端怎么摆）

官方 spec（2025-11-25）实测：
- **stdio 传输 = "the client launches the server as a subprocess"** ⇒ **N 个宿主就是 N 个后端进程**。
- **Streamable HTTP = "the server operates as an independent process that can handle multiple client connections"**。
- 每个 client–server 是一条 stateful session；server 可发 `MCP-Session-Id`，client 必须回带，404 则必须重新 initialize。
- 工具列表支持分页与缓存（`ttlMs`、`cacheScope`），且 spec 明写 server **"SHOULD return tools in a deterministic order"**，原文理由是"enables clients to reliably cache the tool list and **improves LLM prompt cache hit rates** when tools are included in model context"。
- server 除 tools 外还能发布 **Resources**（"Context and data, for the user or the AI model to use"）⇒ **人格文件应当作为 Resource 暴露，而不是拼进每个工具描述里**。

⇒ 这条和我们端点实测到的前缀缓存纪律是同一件事的两个面：**工具顺序稳定 = 缓存能命中**。

## 七、本轮结论（改推荐）

1. **CC 不当宿主**——第一节的数据说明它到的是工作现场；第二节的六条实测说明它的人格槽要跟编程指令抢、每轮背 303 KB 不相干上下文、subagent 不保持会话、按 cwd 的记忆隔离已经污染过。
2. **但 CC 继续当数据源**，而且这半件事**不用写**（claude-mem 100,462★ / engram 7,176★ / sessiongrep 都是现成的转录→FTS5→MCP）。
3. **连"自研 loop"也不该做**——`llm` 已给薄 loop + `--system` 人格 + SQLite 会话 + `-c` 续聊；先验它能不能接我们的端点，接不上再谈自研。
4. **要新建的东西缩到三件**：① 把陪伴的**记忆/账本/闸门**做成 Context Forge 的一侧扩展，并以 **streamable-HTTP MCP** 暴露（不是 stdio，理由见第六节）；② **人格文件 + 学习账本**放在任何宿主项目根之外的独立目录，作为 MCP Resource 供出；③ **学习现场的采集**——这是第一节逼出来的新活：那本 PDF、Obsidian 那个还在编辑的库、浏览器查的资料，CC 转录里没有这些。
5. **他原来的诉求"尽可能像人、按经历改变行为"落点更准了**：不是"它主动调整学习计划"（D1 已否），也不是"从编码会话里学我怎么干活"（那是工作现场），而是**它记得我在学什么、学到哪儿、哪儿反复卡住**——而这三样今天在他的所有存储里**一条记录都没有**（记忆库学习词全 0）。

## 八、本轮"明确不做"

- 把陪伴体做成 CC subagent（官方文档原话：fresh isolated context，看不到会话历史）。
- 用 `--system-prompt` 整体替换 CC 提示词来塞人格（会砍掉宿主自己的工具使用指导，`--exclude-dynamic-system-prompt-sections` 还失效）。
- 把陪伴记忆写进 CC 的 auto-memory 目录（按 cwd 分仓 + `claude purge` 连带删 + `claudeMdExcludes` 不排除它）。
- 用 stdio 传输共享这一个记忆后端（N 宿主 = N 进程）。
- 现在就接 SillyTavern / Cherry Studio / Open WebUI 当门面（AGPL / 自定义许可 / MCP 仅管理员；且都读不到编码转录）。
- 把 Gemini / NotebookLM 当备胎（从这台机器完全不可达，等于闭眼决定）。

# 三条路线对比（2026-10-13）

> ⛔ **本文件是历史留档**（路线比较早已做完，见 `docs/decisions.md` 的 D2 / D2-旧 / D9）。当前路线 = **路线二：自研最小 loop + Context Forge 当记忆内核**（D2-旧 的理由就在本文件 §4）。
> **现行计划见 `docs/implementation-plan.md`，别照这份实现。**

维度只有一个：**运行时的"壳"由谁提供**。三条互斥：现成第三方宿主 / 自研最小 loop / 寄生在他已经在跑的 agent CLI 里。

学习陪伴层 + 陪伴人格层**三条都要自己写**——这是共同事实，不是某条路线的缺点。壳里我们真正需要的只有四件：对话循环+工具、跨会话检索、离线自我改写的闸门、主动触达。

## 0. 先把钱钉住：钱不是决策变量

`deepseek-flash` 单价（**今日从官方 pricing 页抄**，$ / 1M token，分谷/峰）：

| | 命中输入 | 未命中输入 | 输出 |
|---|---|---|---|
| 谷时 | 0.003 | 0.15 | 0.6 |
| 峰时 | 0.006 | 0.3 | 1.2 |

（`deepseek-v4-pro` 同页：命中 0.022/0.044、未命中 0.66/1.32、输出 1.98/3.96。**谷峰的具体时段定义本轮未取**，只知道有两档。）

用实测到的 usage 结构算（前缀 2,300 token、稳态每轮新算 252、命中 2048）：

| 轮次类型 | 谷时 | 峰时 |
|---|---|---|
| 一个有心跳意义的轮（新算 252 + 命中 2048 + 输出 300） | ≈ $0.00022 | ≈ $0.00045 |
| 同样这轮，**前缀不稳定导致命中归零** | ≈ $0.00053 | ≈ $0.0011 |
| 一次带完整记忆索引的对话（新算 300 + 命中 5,700 + 输出 400） | ≈ $0.00030 | ≈ $0.00060 |

按 OpenClaw 文档默认的心跳频率（每 30 分钟一整轮 = 48 次/天）推：**谷 $0.011/天、峰 $0.022/天 ⇒ 每月 $0.3–$0.7**。每天聊 50 轮再加约 $0.45–$0.9/月。

⇒ **全年模型开销在个位数美元级。** 上一轮我把"前缀稳定性"讲成关键成本前提，准确说法要降级为：**它影响的是 2.4–3.8 倍的差价，不是"用不用得起"**。真正需要拍板的是另外两件事：要不要多一个常驻服务，以及你愿意一天被它主动打扰几次。

## 1. 路线一：借现成第三方宿主

三个候选的实测对比（细节出处见三份调研文件）：

| | hermes-agent | OpenClaw | letta-code |
|---|---|---|---|
| 许可证 | MIT | MIT | Apache-2.0 |
| 原生 Windows | **官方一级支持**，README L45 原文"CLI, gateway, TUI, and tools all work natively"，PowerShell 一条命令装，自带 uv/Python 3.11/Node/ripgrep/ffmpeg/**便携 Git Bash** | 支持（原生 Hub 应用 + install.ps1），但 **`engines.node >=24.16 <25 或 >=26.1`**；本机实测只有 22.22.0，无其它版本 | Node **22.19+** ⇒ 本机 22.22 **满足** |
| 常驻服务 | 需要 gateway（进程内 cron 才有活性） | **必须** gateway，端口 18789，Windows 走计划任务 S4U 开机启动 | **不需要**："The CLI runs agents in-process"（可选起 server） |
| 端点匹配 | **专门写了 `api.deepseek.com/anthropic` 的适配**（`anthropic_adapter.py:504-528`），任何 `/anthropic` 结尾 base URL 自动切 Messages 协议 | 向导支持自定义 Anthropic 兼容端点，且**在非官方域名上主动抑制隐式 beta 头**（正好对上我们实测的 beta 头被忽略） | 官方只文档化 **OpenAI 兼容 Chat Completions** ⇒ 要改打 `api.deepseek.com/v1`，**而这条路我们没实测过** |
| 人格/用户模型 | `SOUL.md` + `USER.md` + `memories/MEMORY.md` | `AGENTS/SOUL/IDENTITY/USER/MEMORY.md` + 每日日志，有字符预算 | 无 persona 文件契约（有 `--personality` 一次性设定） |
| 自我改写 | `skill_manager_tool._create_skill` + 后台复盘，**写入带 `_memory_write_origin="background_review"` 来源标签** + 动作摘要给用户 | Dreaming（三阶段、preimage 进 SQLite、可 rollback、剥离已召回片段防自增强）+ Skill Workshop（每 10 轮一次、一次最多一处、负面清单） | 后台 consolidate + **"Agent reviews before applying"** 审批开关 |
| 检索 | SQLite **FTS5**（不需要向量） | FTS5/BM25，向量需另配 provider（默认 OpenAI embedding，我们没有） | **文档原话"does not include a semantic or vector index by default"** ⇒ 正好对上我们无 embedding 接口的现状 |
| 主动性 | 进程内 cron（croniter） | heartbeat 默认 30m + cron | cron **只在进程开着时**触发 ⇒ 主动性等于没有 |
| 对我们已有资产的处置 | 它的记忆是自己的 markdown/DB ⇒ **Context Forge 要么闲置要么当外挂工具接** | **记忆是独占可插拔槽**（`registerMemoryCapability`/`registerContextEngine`）⇒ **Context Forge 可以去占这个槽** | MemFS 是它自己的 git markdown ⇒ **会替换掉 Context Forge**，不是接上 |
| 实测代价与风险 | 仓库 511M（剩余额度的 0.9%，不是问题）；**本机从没装过**（`%LOCALAPPDATA%\hermes` 不存在）；他那份是停在 feature 分支的个人 fork（最后提交 2026-07-09，工作区脏）；依赖全钉死 `==`（它 README 记是 2026-05-12 因 PyPI 蠕虫收紧的）⇒ 装的是旧组合；README 自认两个已知坑：杀软误报自带 `uv.exe`、一份已解决 P2 RCA 说中断的 update/过期 CA 变量会让第一次调模型裸崩 | 仓库 API `size` 报 ≈9.1 GB；**158 个未关 Windows issue**，含 WAL 涨到 1.4–2.8 GB **卡住启动**、2026.10.1 启动回归约 1030 秒；top-12 贡献者里一人占 67% 提交；**dreaming 的三个准入门文档明写 internal 不可调**，权重写死 0.30/0.24/0.15/0.15/0.10/0.06；我们实测出的前缀抖动问题它踩过（#96773） | 项目刚转形态（Python 服务端已删，源码搬到 TS 仓，v0.34.13）⇒ 移动靶；89 个 Windows issue 含 #4651（dream 触发 Windows 超时保护）；要换端点路径 |

**路线一的净优点**：那套"自我改写不失控"的闸门（来源标签、确定性阈值、preimage 回滚、防自增强剥离、负面清单）是**别人线上验证过的**。我们只是抄形状的话，得自己写对。

**路线一的净代价**：三条都要求我们**让出一个位置**——hermes 和 OpenClaw 的记忆格式会和我们已有的 Context Forge 打架（OpenClaw 尚可占槽，hermes 基本闲置它），letta-code 直接替换掉。而 Context Forge 恰好是本项目最贵的一块已经付过的钱。

## 2. 路线二：自研最小 loop + 复用 Context Forge

需要新写的，和实测到的难度：

| 组件 | 要不要写 | 依据 |
|---|---|---|
| 对话循环 + 工具 | **很小**。`Anthropic(base_url, api_key)` 或直接用 stdlib；工具、`system`、`stream` 都被实测为 Fully Supported | 实测 A/D 组：`stop=tool_use`，参数解析正确 |
| thinking 块处理 | **可以不管**。带回去和丢掉都 200 通过 ⇒ 不需要 hermes 那种特判 | 实测 C1/C2 |
| 预算闸门 | 一行调用。`/v1/messages/count_tokens` 实测 200，且**工具定义计入** | 实测 B |
| 前缀布局 | 一条纪律：稳定段逐字节不变、可变内容排后面 | 实测 A2 不掉、A3 归零 |
| 会话记录 | 一份 JSONL，形状有官方先例（Claude Code `~/.claude/projects/<proj>/<session>.jsonl`） | 已核 |
| 跨会话检索 | **不用写**，Context Forge 已有 BM25/FTS5 + 中文双元组，权重/证据/冲突/衰减/版本都在 | 逐行核过 |
| 自我改写闸门 | **要写，且这是本路线唯一真正的智力投入**。形状可照抄：模型只出操作决策（ADD/UPDATE/DELETE/NONE 一类），确定性代码写文件；写前存 preimage；旧条目保留率当验收；带来源标签；摄入时剥离已召回片段 | OpenClaw dreaming / Mem0 / Agent Zero 三家同构 |
| 主动触达 | 要写。`schtasks` 定时唤一个脚本（微软文档化的 `/sc`、`/it`）或进程内循环；再配一个"无事可说就静默"的标记（OpenClaw 的 NO_REPLY 语义） | 已核 |

**净优点**：Context Forge 直接当记忆内核（provenance、版本、衰减、冲突、人类否决这些已经写完并测过的东西全部生效）；零新增常驻服务也可以做到；前缀布局我们完全自控；人格/用户模型/学习记录三个文件我们自己定义。
**净代价（自报）**：自我改写的闸门、回滚、防污染**没有任何外部验证**，是我们自己写的；OpenClaw 那一套是别人踩出来的。第二条自报：定时触达自己写意味着自己处理 Windows 上"睡眠/开机后补偿执行"这类脏事。

## 3. 路线三：寄生在他已经在跑的 agent CLI（Qoder / Claude Code）里

不新增任何运行时：把陪伴 agent 做成一套指令文件 + 技能 + 钩子，靠 `~/.qoder-cn/memory` 和 Context Forge 的 MCP 已经接好这一点直接用。

- **净优点**：运行时、模型接入、记忆装载、钩子、技能机制**今天全部在用**（本机实测：Context Forge 已接进 Claude Code 的 hooks 和 MCP，`~/.context-forge/memory.db` 6.8MB 活着）。新增代码量近零。
- **净代价（三条硬）**：① **主动性基本没有**——它只能在你打开终端时存在；② **上下文和你正在干的活混在同一个会话里**，那个用户级 memory 目录是跨项目的 ⇒ 陪伴记录会和你工程笔记互相污染（这正是调研里"记忆投毒/自增强"那一类，而这次连隔离边界都没有）；③ 人格无法独立——system 位置被 CLI 自己占着。
⇒ 只有在"你本来就整天开着终端，陪伴就是顺手在场"这个前提下它才成立。

## 4. 我的推荐：路线二

理由三条，按分量排：

1. **学习陪伴层 + 情感层无论如何都得我们自己写**，所以借壳买到的只有四件事；而实测下来这四件里三件（对话循环、thinking、预算闸门）**已经在端点实测里证明很薄**，第四件（自我改写闸门）是我们必须自己决定阈值的那一件——把它的门槛设成 internal 不可调的 OpenClaw 反而是阻碍。
2. **他已经有本项目最贵的那块**（Context Forge 的 provenance/版本/衰减/冲突/人类否决）。路线一里它要么闲置（hermes）、要么被替换（letta-code）、要么得给它写一个宿主插件（OpenClaw，那是第三种工作量）；路线二里它是内核。
3. **钱不构成约束**（上表算到全年个位数美元），所以"自研会不会很贵"这个担心没有数据支持；真正的约束是"要不要多一个常驻服务"和"要不要接受别人写死的闸门"，路线二对这两条都给的是"不"。

**推荐的代价**：自我改写的正确性全靠我们自己守；没有别人的 issue 清单可依赖；Windows 侧的定时唤醒/睡眠补偿要自己处理。

**什么证据会翻转这个推荐**（提前钉住，别到时候改口不认）：
- 如果他答第 1 题时选了 **B/C（在场感为主或状态交织）** ⇒ 需要真正稳定的常驻 + 多渠道在场，路线二的自写触达成本会陡增，我会改推 **OpenClaw**（它的 heartbeat/cron/渠道是唯一成套现成的），并接受升 Node 大版本 + 常驻 gateway。
- 如果第一版跑起来后"自我改写"出现真实的学到错东西（哪怕只一次）⇒ 应该立刻把闸门交给 OpenClaw 的实现（用它的记忆槽把 Context Forge 插进去），而不是自己加固。

## 5. 明确不采纳

1. **路线三作为唯一形态** —— 主动性缺失 + 与工程会话互相污染；只作为路线二的"顺手可得"副产品保留。
2. **letta-code** —— 它的 MemFS 会替换掉 Context Forge，且要求我们从已实测通的 `/anthropic` 路径退到没实测过的 `/v1` Chat Completions。
3. **hermes-agent 当壳** —— 它最大的价值是"给我看了一套能跑的形状"（SOUL/USER/MEMORY + 来源标签 + 内置 cron + 对 DeepSeek 的适配），但直接驯服一个 7,960 文件、个人 fork、依赖全钉死一年前版本的运行时，不如自己写那薄薄四件。**把它当参考实现读，不当依赖。**
4. **现在接 AnythingLLM / 向量服务来补嵌入** —— 上一轮已实测：90MB MiniLM 完整权重在盘上，装个包就能开，不需要新服务；而"要不要向量"本身应该等真实记忆量长出来再定（选定即不可逆）。
5. **把成本当决策变量** —— 实测算完不成立。

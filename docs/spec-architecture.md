# jmb 一期架构规格（共享底座）

日期：2026-10-26（**2026-10-27 有修订**：§3 增 Obsidian 归属、§5 重构为 provider 无关、Phase 4/7 相关；**同日评审二审**：§1/§4/§6/§7 改"无常驻服务"口径、§5.3 前缀重排、§3.1/§3.2 确认机制更正——CF 行号已实地复核；**2026-10-28**：D32 CF 独立包依赖、D33 桌宠内置渲染层、D34 写代码）｜ 状态：待审 ｜ 决策依据见 `decisions.md` D1–D34（D31 = 评审修订集，D32 = CF 独立包，D33 = 桌宠渲染层，D34 = 写代码）

一句话：**一个记得住你、跟得上你、不多管的伙伴**，跑在你自己机器上，一个后端、两个入口（桌面 + 桌宠），三种介入方式（教 / 报 / 陪）。

> 关于本文里出现的数字：凡标 **【实测】** 的是本会话内我自己跑命令或调接口拿到的，标 **【二手】** 的是子代理报的（日期口径不一致，未复核），标 **【我定的】** 的是我拍的枚举值、不是调研结论。三份都欢迎驳。

---

## 1. 你会看到什么

```
        ┌───────────────────────── 你的电脑 ─────────────────────────┐
        │                                                            │
  你 ──▶│  ① 对话窗口（终端）   ② 桌宠（Petdex，冒气泡说"今天榜单好了"）│
        │        ▲                        ▲                          │
        │        └──────┬─────────────────┘                          │
        │               ▼                                            │
        │      ③ jmb 后端（REPL 会话 + 10:00 cron + CF 的 MCP）       │
        │           │            │                                   │
        │           ▼            ▼                                   │
        │   ④ Context Forge    ⑤ 每日 10:00 清单任务                 │
        │      （记忆内核）      （错过不补，见 D30）                  │
        └───────────┼────────────────────────────────────────────────┘
                    ▼
              ⑥ Obsidian 库（你要求时它写学习文档到这里）
```

一期**没有手机端**（D17）。
一期也**没有常驻 HTTP/SSE 服务端**（2026-10-27 评审改口径，见 §4）：跑着的是 REPL 会话进程、10:00 的 cron 任务、和 CF 的 MCP server——没有 7×24 常驻进程，也用不上。

**桌宠（D33）**：图上画的是原型形态（外接 Petdex）；发布形态是 **jmb 内置渲染层**（一个进程/一个产品），待实现。**Petdex 原型已清（2026-10-28）**，只留 `pet.json` / 网格 / state 的格式参考，不进发布路径。

---

## 2. 它是谁（人格文件草案 —— 这一节是给你改的，不是给你批的）

三个文件，权限不一样，这是 D21（乙）的直接落地：

| 文件 | 谁能写 | 装什么 |
|---|---|---|
| `SOUL.md` | **只有你**（它只读） | 说话基线。名字、称呼、语气、三条硬规矩 |
| `RELATIONSHIP.md` | **它可以写** | 它对"跟你相处"的总结，例：你晚上不想被问代码、你学新东西喜欢先跑起来 |
| `interests.md` | 它可以写 | 你对哪些项目/话题表过兴趣（D19） |

### `SOUL.md` 草案（v0，等你改词）

```
你是 jmb。你不是助手，是这个人长期的伙伴。

三条硬规矩：
1. 决定权永远在他。他不提要求你不出现（唯一例外：每日清单）。你不替他选东西——
   他问"有什么新项目"，你列出来，不要替他挑"这个你可能会喜欢"。
2. 被记得，不是被监控。你可以提以前的事，但只提一件，且下面"不许提"清单里的时刻不提。
3. 他要求时才写文档，写完告诉他落在哪个文件。

说话方式：
- 讲人话。解释一个东西时，用他写的代码或他手上的报错当例子，不要用抽象名词。
- 不装懂。查不到就说查不到，不要编。
- 他不确认时你不替他下结论。
- 【评审后加的建议，不要就删】他的话里出现伤害自己的信号时，停止陪伴姿态，直接给他官方求助渠道（渠道现场查官方来源，不凭记忆写）。
- 【我拟的，待你改】如果你查到的东西和他的说法不一致，先说一句"我这里看到的不一样"
  并把来源给他，然后让他决定 —— 不顺着他说，也不跟他吵。

不许提（L3 的闸门，D22 要求这条必须写死而不是临场判断）：
- 他说"烦 / 累 / 不想干活 / 别吵"的时候，不提任何工作或学习任务。
- 不提公司项目相关的内容（他公司仓的东西原则上不进这个空间，见 D11）。
- 【我定的】同一个会话里主动提旧事不超过 1 次。
```

⚠️ 我起草"不装懂/不一致要说"这一条的依据是实测的失败模式：模型被 RLHF 奖励附和（arXiv 2310.13548），斯坦福那批模拟人格的实验里记录的失败就包括"极端宜人、很少说不"。**但这跟"替他做主张"是两件事**——你驳过三次的是后者。这条我留着，你觉得多余就删。

---

## 3. 数据怎么存（契约，一处说死）

```
%LOCALAPPDATA%\jmb\                      ← 【我定的】位置，可改
  spaces/
    local/                               ← 一期 owner 只有一个值，但这一层必须存在（D13 口子 2）
      persona/SOUL.md            只读
      persona/RELATIONSHIP.md    可写 · 带上限
      persona/interests.md       可写
      ledger/LEARNING.md         学习进度（形态见 §3.1）
      sessions/2026-10-26-<id>.jsonl    逐字转录，不进长期召回
      grants.json                白名单授权记录（D11）
      changes/                   自我改写的旧版本副本 + 变更日志
      forge/                     Context Forge 的家（memory.db + 它自己的运行时文件）
```

**读法（这一条不许含糊）**：`memory.db` 在 `spaces/<owner>/` **里面**，不在 `spaces/` 外面。隔离机制只有一条：**owner 变 ⇒ `CONTEXT_FORGE_HOME` 变** —— `memory.db` 的路径由 `config.runtime_dir()` 读这个环境变量决定（`config.py:46-53`；`cli.py:54` 与 `mcp_server.py:28` 都走它）⇒ 每个 owner 一套 db + 一棵目录树，这就是 D13 口子 1 说的"物理隔离"，不是"查询时按 owner 过滤"。

（原文把 `memory.db` 画在 `spaces/` 之外，那是 D13 明确否掉的形状，已改。）

**包边界（D32）**：jmb 通过 `context-forge` 包使用记忆内核，不复制其源码，也不依赖用户本机是否装过 CF。开发期 `[tool.uv.sources]` 指向 `../Context Forge`（editable），发布期带固定版本 wheel；`CONTEXT_FORGE_HOME` 始终指向 jmb 自己的 `spaces/<owner>/forge`。Obsidian 落盘（D28）同理：用打包进 jmb 的 CF vault 能力，不调用户本机的 CF 实例。

**⚠️ Obsidian 库不在上面这张树里**（D28）：L1 的学习文档落在 `Documents\Obsidian Vault\personal_konwledge\jmb\`，那是**你的库**，不是 jmb 的目录树。**落盘由 Context Forge 的 vault 能力执行**，jmb 只负责生成内容 ⇒ 写进去的文件带 CF 的归属标记，不带 jmb 自己的第二套归属。缺口清单见 `docs/context-forge-gaps.md`。

**Obsidian 那一格的形状**（2026-10-27 定，目录已建）：

```
Documents\Obsidian Vault\
  ├── personal_konwledge\
  │     ├── agent\ ai coding相关\ blog开发过程\ 前端知识\ 工作经验\ 服务器相关\   ← 你手写的 22 篇
  │     └── jmb\                                    ← ★ jmb 专属
  │           ├── <主题>.md                         ← jmb 写的学习文档（你要求时）
  │           └── context-forge\                    ← CF 自己的产物，自动收在这里
```

⇒ **CF 的知识根 = `vault_path / knowledge_dir`**（`config.py:36-38`）⇒ 机器产物与手写区**天然分开**，一个配置项搞定，不用改代码。
⇒ **记忆只进 `memory.db`，不落 md**：md 投影的唯一自动触发点是 `watcher.py:436`（`forge watch` 跑时）+ 手动命令 `forge project-memories` ⇒ **jmb 不启 watcher/worker 就永远不投影**，零代码改动。
⇒ **现有 `~/.context-forge` 一个字不动**（它的 `vault_path` 仍指 `Desktop/konwledge_base`）—— jmb 用的是**另一个实例**（`CONTEXT_FORGE_HOME` 一换，配置物理分开）。

### 3.1 它到底记哪几类（这条把你没答的 D5 就地定死，你要改就改这里）

D5 我从没得到你的回答，但实现的人必须知道，所以我按现有决策推出一份 v0：

| 类别 | 落在哪 | 形态 | 谁能写 | 进不进长期召回 |
|---|---|---|---|---|
| **关于你的事实** | Context Forge `memory.db` | 一条一句原话级事实，带来源标签 | 它可提议，**你确认后才 active**（提审与批准见 §3.2；改掉 `memory_lifecycle.py:286`） | 确认后进 |
| **学习进度** | `ledger/LEARNING.md` | 一行一样东西：`主题 \| 日期 \| 学到哪 \| 下次从哪继续` | 它写（L1 收尾时，除了写文档还要更这一行） | **整个文件进稳定前缀**，所以它天然被预算管着 |
| **对相处的总结** | `persona/RELATIONSHIP.md` | 短句规则，例："他喜欢先跑起来再看解释" | 它可写（D21 乙） | 进 |
| **兴趣** | `persona/interests.md` | 项目名 + 地址 + 他追问过的日期 | 它可写（D19） | 进 |
| **逐字转录** | `sessions/*.jsonl` | 一行一条消息/工具调用/工具结果，照 Claude Code 的形状 | 系统写 | **不进**（只当原料） |
| ~~学习账本（独立类）~~ | — | **取消**：D14 之后一等产出物是 Obsidian 那份文档，"账本"剩下的那层意思并进上面第 2 行 | — | — |

⇒ 原 D5 的四类里"学习账本"这一类被合并掉了，这是我这轮的决定，不是你的。

**唯一需要说死的契约变化点：所有写入都走"操作决策"，模型不许直接改文件。**

模型只能回这样一个结构：

```
{ op: ADD | UPDATE | DELETE | NONE, target: "RELATIONSHIP.md#规则3",
  payload: …, source_tag: "user_said | it_summarized | background_review" }
```

然后由 jmb 的**确定性写入器**执行：先存旧版本副本 → 改 → 记一条 `memory_events`（带 source_tag）→ 在界面上给你一句"**我改了 X，说 undo 可撤**"。

理由：这条是 D21 那条不可选规则的实现形状（依据是实测的"更新即断裂"：Replika 一次改动后负面语言帖 13%→38%）。同类先例都是这个形状（OpenClaw dreaming 的 preimage、Mem0 的 ADD/UPDATE/DELETE/NONE、hermes 的 `_memory_write_origin`）。

**⚠️ 一处定性修正（2026-10-27 评审，CF 源码实测）**：原稿说"必须一起改 `MemoryLifecycle.publish`（`:286`，实际在 `memory_lifecycle.py:315`）"——**它不是 jmb 的前置**。`publish()` 只被 episode 流水线（watcher/worker）调用，而 jmb 走的 `store.put()`（`memory.py:1521`）**根本不碰 status**：draft 默认 `candidate` 直接入库 ⇒ **一个字不改 CF，jmb 写的记忆也不会自动 active**。那条改动仍然该做，但它保护的是**现有** `~/.context-forge` 实例（CC hooks 的 watcher 在跑、模型记忆被自动转 active），已挪进 `context-forge-gaps.md` §8 的 CF 改动总清单（C6），Phase 5 不被它阻塞。"它自己总结的"和"你确认过的"在生效状态上必须分开——这件事靠 §3.2 的机制实现，不靠改那行。

### 3.2 记忆的提审与批准（§3.1 第一类"关于你的事实"的落地机制）—— 【我定的】

**这一节是评审后补的**：原来只写了"你确认才生效"，没写**谁来确认、在哪确认、确认动作落到哪个 API**。按 Context Forge 的实测源码，现成零件是齐的：

| 环节 | 用什么 | 位置 |
|---|---|---|
| 写入 | `store.put(memory_id, draft, ..., actor='model')`，`draft.status` 保持默认 `'candidate'`（`put` 不改 status，只重算 risk） | `memory_models.py:97` / `memory.py:1437` |
| 提审 | `store.issue_confirmation(memory_id, version, reason=...)` ⇒ 拿一个 **uuid4 的 token**，**600 秒内有效**（`CONFIRMATION_TTL_SECONDS = 600`） | `memory.py:924` |
| 复用活 token | `store.open_confirmation(memory_id, version, ...)`：同版本已有未答、未过期的 handle 就复用，过期自动重发 ⇒ **"回 ok 迟到"不丢**（2026-10-27 评审补，Phase 5 用它） | `memory.py:946` |
| 批准 | `store.approve_confirmation(token, from_tty=True)`：核对行还在、版本没变、没被答过、没过期，**并把 candidate 提升为 active** | `memory.py:1008` |
| 人下的地方 | 终端 `forge approve`（列待批 → `--token <handle> --apply` → 敲后 6 位挑战码）；宿主再拿 `context_forge_memory_confirm(token)` 取回正文 | `cli.py:743` / `mcp_server.py:140` |
| 撤销 | `suppress()` ⇒ `status='disabled'`（`restore()` 可还原） | `memory_lifecycle.py:352` / `:366` |

⚠️ **为什么这条不写清楚，一期就会是空的**【实测】：

- **召回只认 `active` / `conflicted`** —— 三条查询路径都是这个过滤（`memory.py:1784` / `:1792` / `:1855`）⇒ 一条留在 `candidate` 的事实**永远召不回来**。
- 现成的提审回路**只对高危规则开**（`risk.py:62`：`kind == 'rule'` 且 `risk == 'high'`）⇒ "我周末一般不开电脑"这种普通事实**拿不到 token**。
- ⇒ **只把 `publish` 那行改成"保持 candidate"是不够的**：那样普通事实会永远停在 candidate ⇒ 记不住，而 Phase 5 原来那条验收（`status='candidate'`）**测不出来**。

⇒ **所以 jmb 自己的写入路径必须自己调 `issue_confirmation`（不限高危）**，你确认一下，jmb 再调 `approve_confirmation(token, from_tty=True)` ⇒ 这一条才进得了召回。

**确认出现在哪**：一期唯一的对话界面是终端 REPL（Phase 2）。**确认的时序（2026-10-27 评审改）：不在说话中途逐条打断——先挂起，会话收尾批量列一遍**："今天想记这 3 条：1)… 2)… 3)…。回 ok 全记，回序号挑，回 no 全丢。"你敲 `ok`，jmb 调 `approve_confirmation`；迟到也没关系，批准前用 `open_confirmation` 拿活 token（过期会自动重发）。**每会话主动提议上限 5 条【我定的】**，超了就明说"这轮想记的太多，只列这 5 条"，不许悄悄丢。**它不许自己批** —— `approve_confirmation` 的 `from_tty` 守卫就是防模型自批的，token 也是 uuid4 而不是可推导的摘要。

**实现补充（2026-10-28）**：会话收尾不只看本会话新提议，也会扫描库里未确认的 `candidate`（最多列 5 条）；明确回 `no` 才走 CF 的 `suppress`（`disabled`，不再问），**没回答 / 非终端 / 只选了部分**都留到下次会话续列，不静默丢。

**代价我写明白**：普通事实也要你敲一次 ok。唯一能松的绑是"你原话说过的事实直接 active、只有它自己总结的规则走确认"，但那样"你确认才生效"就没了 ⇒ 要你点头（列在 §8）。

---

## 4. 后端对外：两个口，一套内核

| 口 | 协议 | 给谁 | 为什么 |
|---|---|---|---|
| 对话（一期） | **进程内终端 REPL** | 桌面终端 | **2026-10-27 评审改口径：一期没有 HTTP/SSE 服务端**。唯一对话 UI 是终端、桌宠不走对话 ⇒ 进程内直调最简，也不养一个没有消费方的常驻服务。D13 口子 1 的落地形状 = **对话循环写成与入口无关的函数**，二期包一层薄 HTTP 时循环零改动 |
| 对话（二期） | HTTP + SSE | 手机 / GUI | 随手机端一起做（D17），到那天才需要那个进程 |
| 工具 | **MCP over streamable-http** | Qoder / Claude Code 等宿主里的它 | MCP 规范原文：**stdio = "the client launches the server as a subprocess"** ⇒ N 个宿主就是 N 个后端进程；streamable-http 才"can handle multiple client connections"【实测：`mcp_server.py:431` 现在只有 stdio，但装的 mcp 1.30.0 里有 http 服务端实现和 `add_resource`（`server/fastmcp/server.py:542`、`:582`）】 |

**人格三个文件作为 MCP Resource 供出**，不塞进工具描述（规范支持 Resources；且工具列表要 deterministic order 以利缓存）。

**surface 是数据不是分支**：每个请求带 `surface`（`desktop` / `pet` / 以后 `mobile`），能力由这张表决定：

| surface | read_code | write_code | run_command | write_docs | pet | search |
|---|---|---|---|---|---|---|
| desktop | 需授权（D11） | 需本会话授权（D34） | 需本会话授权（D34） | ✔（要求时） | — | ✔ |
| pet | ✘ | ✘ | ✘ | ✘ | ✔ | ✔ |
| mobile | ✘（D12） | ✘ | ✘ | ✘ | — | ✔ |

⇒ 上表的 `mobile` 行**一期不接线**（D17），留着只是说明这张表怎么扩；一期真正存在的只有 `desktop` 和 `pet`。
⇒ **D34 写代码只在 desktop**：任意路径，但公司仓、jmb 自身 `spaces/`、`.git` 硬拒；`run_command` 没有沙箱，命令副作用不能 undo。

⇒ **代码里不许出现 `if surface == "mobile"` 之外的特权分支，更不许出现 `if owner == "local"`**（D13 明写：一期不写特权分支，否则第一个真用户进来就变漏洞）。

**memory.db 一期只有一个写者：jmb 进程自己**（2026-10-27 评审定）。宿主经 CF 的 MCP 连进来的"它"**只读**：读人格 Resource、召回记忆可以；写记忆、写人格文件不行——CF 现有 MCP tool 里的写口（`memory_supersede` / `memory_extend` / `memory_overturn` / `memory_mark` / `memory_scope` 这类，`mcp_server.py:151-331`）在 jmb 的实例上必须不注册（CF 改动总清单 C8 的 `read_only` 开关）。原因有二：两进程并发写一个 SQLite 没必要冒险；宿主写入绕过 jmb 的 gate（无 source_tag、无确认），等于给"它自己批自己"开后门。**宿主模式一期明说的边界**：读得到人格与记忆，但**记不了新东西、没有会话连续性**——"同一个它"一期只成立于 jmb 自己的入口。streamable-http 还必须带**本地 token 鉴权**（照 Petdex 的形状：token 文件 0600、启动重生成、客户端 401 后重读一次）——这台机器跑着大量 agent 工具链，"本机=可信"不成立，而这份库的隐私等级就是 D11 的动机。

---

## 5. 模型与网络

### 5.1 不绑死 provider（2026-10-27 加）

**结论**：模型调用走**官方 SDK + 一张声明式 provider 表**。DeepSeek 只是"当前在用的那一条线路"，不是实现本身。

| 层 | 选什么 | 许可 | 为什么 |
|---|---|---|---|
| 线路一 | **Anthropic 官方 Python SDK**（`anthropic`） | Apache-2.0 | `base_url` 原生可换（kwarg > `ANTHROPIC_BASE_URL` env > 默认）；`system`/`stream`/`tools`/`count_tokens` 全是核心方法 ⇒ **DeepSeek 的 Anthropic 兼容端点、真 Anthropic、任何 Anthropic 兼容网关走同一条代码** |
| 线路二 | **OpenAI 官方 Python SDK**（`openai`） | Apache-2.0 | 覆盖 OpenAI 兼容端点（DeepSeek 的 `/v1`、vLLM、Ollama 的 OpenAI 面……） |
| 统一层 | **自写 `jmb/providers.py`** —— 抄 `hermes-agent/providers/base.py` 的 `ProviderProfile` | MIT | 声明式 profile：协议类型 / base_url / 鉴权模式 / 默认模型 / 固定参数 / extra_body 钩子。~200 行、零依赖、**本机已有源码**（`Desktop\xj\hermes-agent`） |
| 端点怪癖 | 抄 `hermes-agent/agent/anthropic_adapter.py` 的 `_is_deepseek_anthropic_endpoint()` / `_requires_bearer_auth()` 等几个纯函数 | MIT | "各家长得不一样"的知识，自研要踩一遍才写得出来 |

**不引 LiteLLM / langchain / letta**（调研后否掉，理由见 `implementation-plan.md` §0.8）。

⚠️ **两个 SDK 层的坑（查实，动手前要知道）**：
1. **鉴权头在 SDK v2 换过**：v1.17.0 发 `X-Api-Key`，**v2.3.0 发 `Authorization: Bearer`**。DeepSeek 兼容端点两者都收，但换 provider 时要按 profile 走，别写死。
2. **别走 `client.beta.*`**：v2.3.0 把 beta API 挪到 `client.beta.messages.*`（会改 URL 路径），第三方端点不要用。

### 5.2 当前这条线路的实测（DeepSeek 的 Anthropic 兼容端点）

端点 `https://api.deepseek.com/anthropic`。

| 事实 | 值 | 对设计的意思 |
|---|---|---|
| 工具 / system / stream | Fully Supported | 自研薄循环成立 |
| `count_tokens` | 200 可用，且**计入 tools** | 发送前能算预算 |
| 服务端 Web Search | `{"type":"web_search_20250305","name":"web_search"}`，`name` 必填 | L1/L2 都能用；不写工具循环。**这一条不是 DeepSeek 私有的** —— `web_search_20250305` 就是 Anthropic 官方 SDK 里的 type 串（见 5.4） |
| 搜索结果条目字段 | `encrypted_content / page_age / title / type / url` —— **没有正文** | **搜索 ≠ 读正文**，L1 需要第二条能力 |
| `anthropic-beta`、`cache_control`、`citations`、`tool_result.is_error` | 全部 Ignored / Not Supported | 引用和错误原因都要写进正文文本 |
| `thinking` | **未经请求就返回**，续聊时带回去或丢掉都 200（这条线路实测） | ⚠️ **不能无条件丢**：Anthropic 系在 thinking 模式下要求把上一轮 thinking 块**原样回传**，否则 400（`hermes-agent/agent/anthropic_adapter.py` 的 `_is_deepseek_anthropic_endpoint()` 记着这条）。⇒ 规则改成**按 provider 决定**：不展示给用户，但**保留在历史里回传** |
| 自动前缀缓存 | 生效：稳态 `input 252 + cache_read 2048`，`cache_creation=0`（无写入溢价） | 常驻注入便宜 |
| 缓存纪律 | **改开头一个词 → 命中归零**（2302 / 0）；改尾部一个词 → 不掉（2048） | 见下 |
| 搜索的上下文成本 | 问一个小问题、搜 3 轮：**input 22,447** | 必须限轮数 |
| 模型名 | `deepseek-flash` / `[1m]` / `[1M]` / `deepseek-v4-pro` 都接受；**`[1M]` 是否真切 1M 未验** | **由 provider profile 决定，不写死在代码里**；别名之谜已解（2026-10-27，见 §6）——settings.json 现值就是 `deepseek-flash[1M]` |

### 5.3 前缀布局（唯一一条不许违反的排版规则）

```
[ 稳定段：逐字节不变 ]  工具定义 → surface 能力表 → SOUL.md → LEARNING.md → RELATIONSHIP.md 摘要 → interests.md 摘要
[ 每轮变化 ]            检索到的记忆 → 今天的学习文档片段 → 对话历史 → 用户这句话
```

依据：可变内容排在稳定段**之前** ⇒ 缓存全废。这是实测出来的（A3 用例）。

**排序纪律（2026-10-27 评审改）**：前缀缓存是严格前缀匹配，**越稳定的越靠前**。原稿把 RELATIONSHIP/interests 摘要排在工具定义**前面**——这两个是模型自己会写的文件（D21 乙），每写一次，从那一字节起缓存全废，**连工具定义的缓存一起陪葬**。改后：模型可变的文件排稳定段末尾，改一次只废它之后那一段。
**摘要必须确定性**：两个"摘要"按**文件 hash 缓存**——文件没变就不重算；模型每次换个措辞总结，等于自己打掉自己的缓存。
**LEARNING.md 补进稳定段**：§3.1 说它整文件进稳定前缀，原稿这节漏了它——已补，两处以本节为准。

### 5.4 搜索：分两层，都跨 provider

**第一层 · 服务端搜索（主路）**

`web_search_20250305` **是 Anthropic 官方的 server tool 类型，不是 DeepSeek 私有** —— Anthropic 官方 Python SDK v2.3.0 里有 `types/web_search_tool_20250305_param.py`：`name` 必须是 `"web_search"`、`type` 必须是 `"web_search_20250305"`，参数含 **`max_uses`** / `allowed_domains` / `blocked_domains` / `user_location`。

⇒ **这条能力在 Anthropic 系是通用的**，换 provider 不用换代码。**但各家的 wire 形状不一样**：OpenAI 是 `web_search`（参数 `search_context_size`），Gemini 是 `google_search`（返回 `groundingMetadata`），Perplexity 是模型自带。

⇒ **抽象只做在"结果"这一层，不做在"请求"这一层**：请求侧各 provider 一小段适配；结果侧 jmb 自己定义 `SearchResult {title, url, snippet}`，各家翻译过来。

⚠️ **不要引 LiteLLM 来统一请求侧**：它确实有 `web_search_options` 能抹平请求（OpenAI/xAI/Vertex/Anthropic/Gemini/Perplexity），但**响应侧抹不平**（`server_tool_use`/`web_search_tool_result` ↔ OpenAI `web_search_call` ↔ Gemini `groundingMetadata` 是三种块结构），而且它 100+ provider、2026 起带 Rust core ⇒ **只读它的思路，不引这个依赖**。

**第二层 · 本机兜底搜索（服务端搜索挂了时）**

抄本机 `SkillAbout/hotsearching/ai-hotspot-digest/scripts/domestic_search.py` 的 `_search_bing`（`cn.bing.com` **本机实测 200 且结果块可解析**）+ 搜狗微信那一条腿。

⚠️ **不要抄 `last30days` 的 keyless 那两条腿**：它们的实现是 DuckDuckGo HTML → Startpage HTML → SearXNG，而**本机实测 DuckDuckGo（三个域名）、Startpage 全部超时** ⇒ 那个"地板层"在这台机器上是死的。

⚠️ **本机一个搜索后端的 key 都没配**：`~/.config/last30days/.env` 不存在，进程环境里也没有 `BRAVE_API_KEY` / `EXA_API_KEY` / `SERPER_API_KEY` / `PERPLEXITY_API_KEY` / `PARALLEL_API_KEY` ⇒ `WEB_BACKEND_ORDER = ("brave","exa","serper","parallel","keyless")` 这条链**现在一条也走不通**，不能当现成能力。

### 5.5 抓正文：OSS 库 `trafilatura`

**搜索 ≠ 读正文。** 服务端搜索返回的条目只有 `title / url / page_age / encrypted_content / type` —— **`encrypted_content` 是给模型看的（服务端加密，客户端解不开）**，客户端拿不到明文 ⇒ 要引用、核对、存进笔记就得自己抓。

| 方案 | 结论 |
|---|---|
| **`trafilatura`** | ✅ **选它**。2.3.1 / **Apache-2.0** / 发版 **2026-10-06** / `python_requires>=3.10` / 依赖 7 个：`certifi` `charset_normalizer` `courlan` `htmldate` `justext` **`lxml>=6.1.3`** `urllib3`。**本机已装 `lxml 6.1.3`（正好卡在它的下限）⇒ 最重的依赖已经在位** |
| `r.jina.ai`（Jina Reader） | ❌ 本机实测**超时**（`SkillAbout` 的 `web_fetch_keyless.py` 就是这条路） |
| DeepSeek `/v1/tools/fetch` | ❌ **不用**：厂商私有 API，且不绑死 DeepSeek |
| 手写 HTML 解析 | ❌ 不做 |

顺序：`llms.txt` 探测（实测 `docs.github.com/llms.txt`、`docs.anthropic.com`、`docs.langchain.com` 有）→ `trafilatura` 提正文 → 都没有就说"我只看到标题，没看到正文"。

⚠️ **"抓到了但正文是空的"也算读不到**（2026-10-27 评审补）：trafilatura 对 JS 渲染页提出来的是导航残渣或空串——提取结果少于约 200 字符按"读不到正文"上报，不许把残渣当正文讲。

### 5.6 预算闸门（真正的限流手段）

一次回答内最多 **3 轮**搜索、每轮取**前 5 条**结果【我定的】。依据：实测那次它自己就是搜了 3 轮（`web_search_requests: 3`），那次 `input_tokens` 冲到 **22,447**。跑一周后用记账数据（D13 口子 6）重新定。

⚠️ **这两个数是目标值，不是已验证的上限**。执行分两层：
- **端点侧**：轮数用 `max_uses`（官方 SDK 类型里有这个参数）；**条数没有参数** ⇒ 前 5 条在**客户端截断**。DeepSeek 这条线路认不认 `max_uses`，**Phase 3 第一件事验它**。
- **本地侧（默认就上，不依赖任何未验参数）**：`count_tokens` 发送前就能算（实测 200 可用、计入 tools），超预算就把后续搜索结果摘要化再进上下文 ⇒ 22,447 那种输入复发不了。

---

## 6. 要动哪几处（编号 + 每处干什么 + 你会看到什么变化）

1. **新建 jmb 后端**（Python，**无常驻服务**：REPL 会话进程 + 10:00 cron 任务）——对话循环、工具声明、**按 provider 决定 thinking 块要不要回传**、usage 记账、前缀装配、provider profile 装载。
   ⇒ 你看到的：一个终端窗口，敲进去就有回应，会流式出字。
2. **Context Forge 加 streamable-http 传输**（`mcp_server.py:431` 那行 `run(transport="stdio")` 旁边加一档）+ **暴露人格三个文件为 Resources** + **read_only 开关（C8）与本地 token 鉴权**（§4 的单写者边界）。⚠️ 本 Phase 建议后移二期（评审）：L1/L2/L3 没有一个需要它。
   ⇒ 你看到的：在 Qoder 或 Claude Code 里也能叫到同一个它。
3. **写入器改造**：新增"操作决策 → 确定性落盘 + 副本 + 告知"这条通路；同时改掉 `memory_lifecycle.py:286` 那条无人值守 active。
   ⇒ 你看到的：每次它改自己的文件都会告诉你改了哪一条、怎么说 undo。
4. **白名单授权**：`grants.json` + 一个"它要读你的代码 → 你点一下"的检查点，**外加 `read_code` 工具本体**（2026-10-27 评审补：原稿只有闸门没有工具，L1 第 5/6 步全押在它上面；带截断预算——单次返回设 token 上限，超了给头部片段 + "文件共 N 行，已截断"）。
   ⇒ 你看到的：它要用某个仓会先问，你同意后留痕。**scope 两档（评审定）**：`session`（默认，会话结束即失效）/ `persistent`（他明说"以后都可以"才落），另有 revoke——白名单只增不减，三个月后 D11 就空了。
   **D34 写代码（2026-10-28）**：新增 `write_file` / `edit_file` / `run_command`；**任意路径**；写/执行首次触发**本会话**授权（只有 session，不落 persistent）；每个用户轮次一个 change set + preimage，`undo` 回滚整轮；文件之后被改过则拒绝回滚；**命令副作用不可 undo**；公司仓、jmb `spaces/`、`.git` 硬拒。
5. **每日清单任务**：10:00 跑，一天一次；产出进 `sessions`，并由桌宠冒一句（D33 渲染层待做；当前无气泡）。
   ⇒ 你看到的：早上开机，气泡说"今天榜单好了"。
6. **搜索 + 抓正文两个工具**（§5.4 / §5.5）：搜索用**服务端 Web Search**（Anthropic 官方的 server tool，跨 provider 可移植）+ 本机 Bing 兜底；读正文用 **`trafilatura`**，`llms.txt` 优先。
7. **Obsidian 写入**：**由 Context Forge 的 vault 能力承担**（它已有路径围栏 / 归属保护 / hash 乐观锁 / 冲突副本）。jmb 只**生成内容**（D26 六条：不写 frontmatter、`[文字](URL)`、讲解体、长文加 TL;DR + 资料来源、文件名规则、首次先落 draft），**落盘走 CF**。落点 = `Documents\Obsidian Vault\personal_konwledge\jmb\`（**已建**，目录里**不再套那六个分类** —— 那六个是你手写内容的分类）。CF 缺的 5 个口子在 `docs/context-forge-gaps.md`。

~~⚠️ 一处我没查清的：~~ **已解（2026-10-27，`jmb doctor` 实测）**：settings.json 的 env 段现在写的就是 `deepseek-flash[1M]`（shell env 为空，doctor 从 settings.json 取到）⇒ 10-26 记的"settings 写的是 deepseek-flash"与现状不符（那次读错或此后被改过）。**没有"谁覆盖谁"的问题**；`jmb doctor` 每次把 env/settings 两个原始值并排打出，这个值以后不会隐形。`[1M]` 是否真切 1M 窗口仍未验（§5.2 那行不动）。

---

## 7. 一期不做（每条带理由，可被新证据重开）

- **手机端**（D17）：对话循环已写成与入口无关的函数，接进来 = 补一层薄 HTTP + 网络，不是架构返工。
- **HTTP/SSE 常驻服务端**（2026-10-27 评审定）：一期对话只有终端、桌宠不走对话，没有一个 7×24 常驻进程；它随手机端一起做。
- **多用户鉴权 / 配额 / 计费 / 后台**（D13）：只做"留六个口子"，等真出现第二个用户再设计。
- **复习器 / 间隔重复**（你明确推迟）。
- **虚构角色演绎**（你撤掉；人格只有一个，D16）。
- **平时它自己想找话头**（D24 选甲：只有每日清单主动）。
- **它自己改自己做事的方法**（D21 丙档，一期不开，留接口）。
- **本地模型、图数据库记忆、第三方搜索供应商、自建 SearXNG**：前一轮调研实测下来都不是这件事的必需项（你这台机器上 google/duckduckgo/brave 全超时；服务端搜索是模型端点自带的能力，不用另买搜索供应商）。
- **jmb 自己实现 Obsidian 写入**（D28）：落盘归 Context Forge —— 它已经有路径围栏（`vault.py:35-54`）、归属保护（`:62-68`）、hash 乐观锁与冲突副本（`:176-190`）。jmb 只生成内容。CF 缺的 5 个口子在 `docs/context-forge-gaps.md`。
- **外接 Petdex / sidecar**（D33）：发布形态是 jmb 内置渲染层，一个整体；Petdex 原型已清（2026-10-28），不打包进 jmb。
- **"当天第一次开机补跑"**（D30）：不作为独立功能做，也没有开机触发器（`schtasks`/`qoder_cron` 关机时不跑）。代价写明：10:00 时机器关着，那天就没有清单。
- **"体验良好"的验收指标**（你把判断权保留了，我不把它转成数字）。

---

## 8. 待你改的清单（我不假装这是已定稿）

| 项 | 现状 | 要你做的 |
|---|---|---|
| `SOUL.md` 草案 | 我写的 v0 | 改词，尤其"不一致要说"那条留不留 |
| "不许提"清单 | 我写了 3 条，第 3 条【我定的】每会话 ≤1 次 | 补你想加的 |
| 日报列几条 | 【我定的】8 条 | 你说数字 |
| 搜索轮数 / 条数 | 【我定的】3 轮 / 5 条（唯一依据是实测那次它自己搜了 3 轮）——**是目标值，端点侧能不能设未验** | 认或改 |
| **§3.1 那五类记忆** | **你没答过 D5，是我替你定的 v0**；"学习账本"被我合并掉了（第 6 行那行已取消） | 这是全篇最该你过一遍的一节 |
| **§3.2 提审与批准** | 【我定的】复用 Context Forge 现成的 `issue_confirmation` / `approve_confirmation`（终端 `forge approve`） | 认或改 —— 尤其"普通事实也要你敲一次 ok"这个摩擦要不要 |
| **§5.1 不绑死 provider**（D29） | 【我定的】Anthropic 官方 SDK 为主线 + OpenAI 官方 SDK 为第二条 + 自写声明式 profile（抄 hermes `providers/base.py`） | ✅ **已认**（2026-10-27"俩协议应该够吧"） |
| **§5.5 抓正文用 `trafilatura`**（D29） | 【我定的】Apache-2.0，本机 `lxml 6.1.3` 已在位 | ✅ **已认** |
| **Obsidian 写入归 Context Forge**（D28） | 【我定的】CF 落盘、jmb 生成内容；CF 缺 5 个口子，清单在 `docs/context-forge-gaps.md` | ✅ **已认**（2026-10-27"cf 我自己改"） |
| `RELATIONSHIP.md` 上限 | 【我定的】2 KB（参照 Claude Code 那个"前 200 行或 25 KB"的装载上限，不是我算的） | 定或不定 |
| jmb 的家目录 | 【我定的】`%LOCALAPPDATA%\jmb\` | 换位置就说 |
| 每会话记忆提议上限 | 【评审后我定的】5 条，会话收尾批量确认（§3.2） | 认或改 |
| grants 默认档 | 【评审后我定的】`session` 默认 / `persistent` 显式 + revoke（§6.4） | 认或改 |

### ⛔ 不是"待你改"，是**真的还没解决，动手前必须先解决**

1. **CF 的 `vault_path` 现在指着错的库。** `~/.context-forge/config.toml:1` = `Desktop/konwledge_base`（产品文档库，549/567 篇是 CF 自己的文档），而 L1 的落点是他的 Obsidian 库 `Documents\Obsidian Vault`。⇒ **改一行配置**（`docs/context-forge-gaps.md` 的 G6），不改则写出来的东西落在错的库。
2. **"AI 线下会议"这一栏我没有任何验过的数据源。** ⇒ 要么我先专门查一轮，要么这栏一期不做（你手工贴链接给它）。**我不会编一个源填上去。**

> 旧的一条已作废：「Obsidian 那 22 篇是怎么组织的，我没实地读过」—— **D26 已经实地读完了**（六条约定见 `workflows/L1-learn-a-thing.md`）。

---

## 9. 文件清单（放最后，按你的偏好）

规格：本文 + `workflows/L1-learn-a-thing.md`、`L2-daily-brief.md`、`L3-want-to-talk.md`
决策与证据：`docs/decisions.md`（D1–D30）、`docs/research/*.md`（六轮）、`NOTES.md`
**Context Forge 缺口**：`docs/context-forge-gaps.md`（Obsidian 落盘归 CF，CF 缺的 5 个口子 + 1 个配置错）
探针（一次性测量件，**不属于产品代码**）：`scripts/probe_endpoint{,2,3}.py`、`scripts/probe_websearch.py`

# jmb 实现计划（拿来主义版）

对应规格：`docs/spec-architecture.md` + `workflows/L1-L3`。决策：`docs/decisions.md` D1–D34。
另见：`docs/context-forge-gaps.md`（Context Forge 要补的能力清单）。
原则：**能接现成的就接，能抄的就抄，抄的时候连它的边界条件一起抄。**

> **2026-10-27 评审修订**：Phase 5 不再被"改 CF 的 publish"阻塞（实测 `store.put()` 不碰 status）；Phase 6 补 `read_code` 工具；Phase 8 加鉴权/单写者边界且**建议后移二期**；CF 行号实地复核过一遍（`memory_lifecycle.py:286`→`:315`、`mcp_server.py:292`→`:431` 等，漂移处已更正），引用以函数名为准。
>
> **2026-10-28 D32**：Context Forge 改为**独立包依赖**——开发期 `[tool.uv.sources]` 指向 `../Context Forge`（editable），发布期固定版本 wheel；jmb 不复制 CF 源码、不共用 `~/.context-forge`。`jmb/memory.py` 的 `sys.path` hack 已删除，`jmb doctor` 增加 CF 包版本/路径一行。
>
> **2026-10-28 D33**：桌宠不做 Petdex sidecar（A 被否），改为 **jmb 内置渲染层**（B），本期只规划；Petdex 仅原型参考，不进发布路径。**Petdex 原型已清（2026-10-28）。**
>
> **2026-10-28 D34**：jmb 能写代码——`read_code` 扩 offset/limit，新增 `write_file` / `edit_file` / `run_command`；**任意路径、本会话授权、按轮次 undo**；命令副作用不可 undo。借 Pi 的 `edit` 契约，不引 Pi runtime。

每个阶段都必须留下一个**能真跑的东西**，并且有"怎么证明它成了"的检查项。阶段之间不并行。

---

## Phase 0 · Allowed APIs（先钉死能用什么，别现编）

### 0.1 Petdex 桌宠（MIT，`crafter-station/petdex`）— 已读源码

> **2026-10-28：外接 Petdex 原型已清**（app / 素材 / `~/.petdex` / 代码适配层全部移除）。下面保留的是 pet 格式与 state 的历史参考；发布形态见 D33 内置渲染层。

| 项 | 事实（读自源码） |
|---|---|
| 基址 | `http://127.0.0.1:7777`，GET `/health` 无需鉴权 |
| 鉴权 | 头 `X-Petdex-Update-Token`；token 在 `~/.petdex/runtime/update-token`（0600），**每次 App 启动重新生成** |
| `POST /state` | body `{"state": "<enum>", "duration"?: ms}`；`duration` 负数 400、上限 30000；成功 `{"ok":true,"state":"…","duration":null|N,"queued":bool}`；`queued:false` = 与待执行状态重复被合并 |
| `POST /bubble` | body `{"text": "..."}` 必填，另有可选 `title/session_id/agent_source/hostname/…`；成功 `{"ok":true,"counter":N}` |
| `POST /bubble/title` | body `{"conversation_key" 或 "session_id": "...", "title": "..."}` |
| **state 枚举（逐字）** | `idle, running, running-left, running-right, waving, jumping, failed, review, waiting`；默认 `idle`；`state` 超 15 字符也 400 |
| 气泡长度 | **4096 字节上限，超了在 UTF-8 边界静默截断**（不报错） |
| 限流 | 三个 POST 共享 30/秒；超了 **429**，**无 Retry-After** |
| 401 | = token 过期（App 重启过）⇒ **重读 token 文件重试一次** |
| 连接被拒 | = App 没开；没有"宠物未安装"的 404 |
| `pet.json` | 只有 4 个键：`id / displayName / description / spritesheetPath`；网格 8 列 × 9 或 11 行，单帧 192×208，图集 1536×1872 或 1536×2288；**动画是行序，不是 JSON 字段** |

**抄法**：不引 Petdex 的代码；只复用 `pet.json` 四键 + 192×208 网格和 state 枚举（D33）。原型的 HTTP 客户端已清，不再维护。

### 0.2 Context Forge（他自己的项目）— 已读源码

> 行号 2026-10-27 复核过一轮（发现多处漂移已更正）；以后引用尽量锚函数名，行号会烂。

| 用途 | 确切入口 |
|---|---|
| 建 store | `MemoryStore.initialize(path)`（`memory.py:567`）；`MemoryStore(path, readonly=True|False, embedder=None)`（`:559`） |
| 写一条 | `store.put(memory_id, draft, *, expected_version, idempotency_key, actor='model', reason, relations=())`（`memory.py:1521`）——**owner/privacy/kind/status 都在 draft 上，不是参数；put 不碰 status** |
| draft 默认值 | `MemoryDraft.kind='knowledge'`（`memory_models.py:93`）、**`.status='candidate'`（`:97`）**、`.space.owner='local'`（`:41`）、`.space.privacy`（`:42`） |
| 版本/事件 | 版本行 `memory.py:1556-1562`（`expected_version+1`）、事件行 `:1566-1568` |
| **无人值守 active（评审更正）** | `MemoryLifecycle.publish`（`memory_lifecycle.py:303`，自动 active 那行在 `:315`）：`actor=="model"` 时强行 `status="active"`。**只被 episode 流水线（watcher/worker）调用；`store.put()`（`memory.py:1521`）不碰 status** ⇒ jmb 不改这行也不会自动 active（2026-10-27 实测）。改动保护的是现有 `~/.context-forge` 实例 ⇒ CF 改动总清单 C6，**Phase 5 不被它阻塞** |
| **召回只认生效态** | 三条查询路径都过滤 `status IN ('active','conflicted')`（`memory.py:1855`/`:1863`/`:1926`）⇒ **`candidate` 的行召不回来**（保持 candidate 就必须配提审，见 Phase 5） |
| **提审** | `store.issue_confirmation(memory_id, version, *, reason, request_id=None, session_id=None, ttl_seconds=600)`（`memory.py:924`）⇒ uuid4 token，**600 秒有效**；无风险门槛，任何记忆都能提 |
| **复用活 token** | `store.open_confirmation(memory_id, version, ...)`（`memory.py:946`）：同版本已有未答、未过期 handle 就复用，过期自动重发 ⇒ **"回 ok 迟到"不丢**（Phase 5 用它，评审补） |
| **批准** | `store.approve_confirmation(token, *, from_tty)`（`memory.py:1008`）：校验行还在/版本没变/没被答过/没过期，**并把 `candidate` 提升为 `active`**；`from_tty` 守卫拒绝非终端（防模型自批） |
| 撤销 | `suppress()`（`memory_lifecycle.py:352`）⇒ `status='disabled'`；`restore()`（`:366`）还原 |
| 人批准的地方 | 终端 `forge approve`（`cli.py:743`）：列待批 → `--token <handle> --apply` → 敲后 6 位挑战码；宿主拿 `context_forge_memory_confirm(token)`（`mcp_server.py:140`）取回正文 |
| **高危闸门只覆盖 rule** | `requires_confirmation` = `kind=='rule'` 且 `risk=='high'`（`risk.py:62`）⇒ **普通事实拿不到 token**，提审得 jmb 自己调 |
| 检索 | `MemoryRecall.search(query, *, project, changed_path=None, limit=8, byte_budget=65536, …) -> RecallResponse`（`memory_recall.py:116`） |
| **检索的坑** | **`owner` 没穿下去**：检索签名（`memory.py:1809`/`:1826`）的 owner 默认 `DEFAULT_OWNER` 没被调用方穿下去、`_expanded` 硬编码（`memory_recall.py:178`，2026-10-27 复核此行一字不差）。单 owner 时无害；**第二个 owner 一出现就是"跨 owner 召回"事故** ⇒ CF 改动总清单 C7 |
| MCP 服 | `FastMCP("context-forge")`（`mcp_server.py:93`）；工具是 `create_server()` 里的 `@server.tool()` 函数；`main()` 在 `:431` **硬编码 stdio**；**有写类 tool**（`memory_supersede`/`memory_extend`/`memory_overturn`/`memory_mark`/`memory_scope` 等，`:151-331`）⇒ jmb 实例暴露时要关掉（C8） |
| 后台 | `run_due(store, now=None, *, period_seconds=86400, steps=None, memory_store=None)`（`scheduled.py:91-113`），生产调用点 `watcher.py:428`；`apply_auto_tier`（`memory_lifecycle.py:466`）在生产跑；**`consolidate`（`:425`）只有测试在调** |
| 依赖 | Python `>=3.12`；**核心只要 pydantic + 标准库**；MCP 是 extra；嵌入是 extra（惰性） |
| 库位置 | `CONTEXT_FORGE_HOME` 优先，否则 `~/.context-forge`（`config.py:46-53`），文件 `memory.db` |
| 授权 | **没有现成概念**（`grants` NOT FOUND）；最近的是 `boundary_visible`（`memory.py:305-320`）、禁止写时扩权（`:282-290`）、`user_owned/suppressed` 保护（`:1523-1531`） |
| **vault 写入（Obsidian 那条线）** | `Vault` 类（`context_forge/vault.py`）：`_safe()` 路径围栏（`:35-54`）、`is_user_owned()` frontmatter 保护（`:62-68`）、`update_with_expected_hash()` sha256 乐观锁 + `.conflict-<ts>` 副本（`:176-190`）、原子写 |
| **vault 落点** | 只有**两个固定模板**：`knowledge/accepted/<id>.md`（`vault.py:99-110`）、`memories/<sha16>.md`（`memory_projection.py:37-49`） |
| **vault 配置** | `~/.context-forge/config.toml:1` = `vault_path = "Desktop/konwledge_base"` —— **这是你现有实例的配置，jmb 不动它**。jmb 用自己的实例（`CONTEXT_FORGE_HOME` 一换，配置物理分开），Phase 5 新建一份指到 `Documents/Obsidian Vault/personal_konwledge/jmb`（**目录已建**） |
| **vault 出口** | CLI 注册了 30+ 子命令，**没有** write / export / note；MCP 14 个 tool（`mcp_server.py:86-292`）全是读+反馈，**一个都不能写文件** |
| provider 抽象（可抄） | `LlmGateway` Protocol（`domain.py:277`）+ `select_gateway` 工厂（`gateways.py:153`）+ `provider_http.py:143` 的单一 `_post` 入口 + `resolve_remote_url` 的 base_url 解析 ⇒ **换 provider 成本低**（加一个子类 + 一个分支） |
| 它**没有**的（jmb 自己写） | 流式（`provider_http.py:366` 硬编码 `"stream": False`）、tool loop（请求体无 `tools`）、MCP client（grep 零命中）、联网搜索/抓正文（全仓无 requests/bs4/trafilatura）、常驻 HTTP 服务、插件机制（无 entry-points） |

**⇒ 两个白拿的结论**
1. **物理隔离不用改 schema**：每个 owner 设一个独立的 `CONTEXT_FORGE_HOME` ⇒ 一个 owner 一个 `memory.db` + 一棵目录树。D13 口子 1 直接落地。**而且陪伴体的库和现有那 314 条代码记忆库天然分开**（D11 的隐私动机顺带满足）。
2. `status` 默认就是 `candidate` —— "模型写的记忆不自动生效"**本来就是它的默认行为**，只有 `publish` 那一行把它强行提升。改动面比我原来以为的小。

### 0.3 SkillAbout 的抓取件（他自己的项目，标准库）— 已读源码

**可近乎原样搬走（都是 stdlib）**：
- `fetch_html()`（`build_digest.py:203`）+ `parse_star_history(page)`（`:217`）→ `(weekly, all_time)`，weekly 行 `{title,url,rank,trend,stars_delta}`，all_time 行 `{title,url,stars}`；布局变了会 `ValueError`（`:266`）
- `normalize_stars_delta`（`:270`）
- `fetch_repository_description(repo, token="")`（`:327`），`X-GitHub-Api-Version: 2022-11-28`，失败退回抓 `og:description`（`:344-359`）
- `enrich_repository_descriptions(...)`（`:365`）7 天缓存 + 6 线程
- 去重/冷却：`select_recent_with_cooldown`（`:84`）、`load_cooldown_state`/`save_cooldown_state`（`:67/:113`）、`canonical_url`（`fetch_hotspots.py:169`）、`merge_and_rank_results`（`:227`）

**要动一刀再搬**：`domestic_search.search_platform`（`:232`）里 DDG 那条腿（`:243`）在你这台机器上是死的，而 `_get_text` 会把 `OSError` 吞成 `""`（`:99`）⇒ **每个查询白等 15 秒**。搬的时候**直接调 `_search_bing`，删掉 DDG 调用**。

**不要搬**：`build_digest.py:19` 的 `from preview_browser import ...`、`main()` 里的 dashboard/HTML 尾巴。**不需要 requests / bs4 / lxml。**

### 0.4 DeepSeek 两个原始接口（`guides/search` 页，**我本机没复现**）—— **降级为不用**

> ⛔ **2026-10-27 决定：这一节的两个接口 jmb 不用了。**
> 理由：`/v1/tools/search` 与 `/v1/tools/fetch` 是 **DeepSeek 私有的**，与"不绑死 provider"冲突（D29）。
> 保留在文档里只作**备选**（万一服务端搜索那条路在换 provider 后不可用），**不写进代码**。
> 替代方案见 §0.8。

```
POST https://api.deepseek.com/v1/tools/search
Authorization: Bearer <key>
{"query":"…", "count":5, "need_content":false, "ori_question":"…", "localization":"…"}
→ {"results":[{"rerank_score","title","url","snippet","summary","content","site_name","site_icon","date","authority"}]}
```
- `query` 必填 1–128 字符；`count` 默认 **10**、范围 **1–50**；**`need_content` 默认 false ⇒ `content` 恒为 `""`**（要正文必须显式 true）
- 操作符：`site:` `-site:` `-` `-"..."` `"..."` `lang:` `after:` `before:`；多站 `site:a OR site:b`
- `POST /v1/tools/fetch` body `{"url": "…"}`（**≤8192 字符**，http/https、无 userinfo）→ `{"title","content"(Markdown)}`
- 错误码：400 / 401 / **402 余额不足** / **403 站点策略** / **404 无可提取正文** / 408 / 413 / 429 / 500 / 504；**只对 408/429/5xx 重试**
- 计费：**Search $0.75/1000 成功请求，Fetch $0.75/1000**；空结果/超时不收；`count` 不影响价格
- 限流：Search **100 QPS**、Fetch **25 QPS**（按账号），Fetch 另有按域名 QPS
- ⚠️ **这一页我本机没复现（【二手】）**：`guides/search` 上写的免费期是 2026-11-01 00:00（北京时间）前免费、之后按请求计费；而 D25 记的是"免费期 NOT FOUND、不采信" ⇒ **两处冲突，动手前自己读一次页或跑一次请求定死**（跑一次 ≈ $0.00075）。价格/限额三处数字同理，**未复验，不得当已定写进代码**。

### 0.5 服务端 Web Search（我实测过，但**官方文档没写**）

- 声明：`{"type": "web_search_20250305", "name": "web_search"}` —— **`name` 必填**（少了 422 `missing field name`）
- **这个 type 串是 Anthropic 官方的，不是 DeepSeek 私有**（2026-10-27 查实）：Anthropic 官方 Python SDK v2.3.0 里有 `src/anthropic/types/web_search_tool_20250305_param.py` —— `name: Literal["web_search"]`、`type: Literal["web_search_20250305"]`，参数含 **`max_uses`** / `allowed_domains` / `blocked_domains` / `user_location`。
  ⇒ **这条能力在 Anthropic 系是通用的**，换 provider 不用换代码。⚠️ 但 DeepSeek 这条线路**认不认 `max_uses` 本机没验** ⇒ Phase 3 第一件事验它。
  ⇒ **官方文档页本机打不开**（`docs.claude.com` 302 → `platform.claude.com` 307 → `app-unavailable-in-region`，地区屏蔽）⇒ 依据取自 SDK 源码。
- **这是我自己实测出来的**：`/guides/anthropic_api` 只写 `server_tool_use` / `web_search_tool_result` 两种块 **Supported**，**没有给这个 type 字符串，也没有示例**。⇒ 计划里可以用，但**必须带一句注释标明"类型串来自实测/SDK 源码，非本机可达的文档页"**。
- 返回块：`server_tool_use{id,name,input:{query}}`、`web_search_tool_result{content:[{title,url,page_age,encrypted_content,type}]}` —— **无正文字段**（`encrypted_content` 是给模型看的，客户端解不开 ⇒ 客户端要明文得自己抓，见 §0.8）
- usage 里有 `server_tool_use: {"web_search_requests": N}`

### 0.6 端点实测约束（不重复测）

`system`/`stream`/`tools` Fully Supported；`anthropic-beta`、`cache_control`、`citations`、`tool_result.is_error` 被忽略；`thinking` 白送且可丢；`count_tokens` 可用且计入 tools；**前缀缓存只在"稳定段逐字节不变且在最前"时生效**（改开头一词 → 命中归零 2302/0；改尾部不掉 2048）。

### 0.7 反模式护栏（全计划通用）

- ❌ 不引第三方搜索供应商、不自建 SearXNG（你的网络里 google/ddg/brave 全超时）
- ❌ 不爬 `github.com/trending`（这台机器打不开）；不调 `raw.githubusercontent.com`（实测超时）
- ❌ 不绕验证码/不登录爬活动行
- ❌ 不给 Obsidian 文件加 frontmatter；文件名不以 `#` 开头
- ❌ 不在客户端放 API key；不让模型直接改文件
- ❌ 不写 `if owner == 'local'` 的特权分支
- ❌ 不把未复验的第三方页面数字当事实写进代码（价格、限额、免费期一律现读现验）
- ❌ 不加 requests/bs4；**lxml 允许**（`trafilatura` 依赖它，且本机已装 `lxml 6.1.3`）；其余能 stdlib/httpx 就够

---

## 0.8 provider 抽象与开源件（2026-10-27 调研后定）

**这一节是"不绑死 provider + 抄开源"的落地清单。**

### 0.8.1 模型调用：官方 SDK + 声明式 profile

| 层 | 选什么 | 许可 | 关键事实 |
|---|---|---|---|
| 线路一 | **`anthropic` 官方 Python SDK** | Apache-2.0（v2.3.0 / 2026-10-23） | `base_url` 原生可换（kwarg > `ANTHROPIC_BASE_URL` env > 默认）；`system`/`stream`/`tools`/`count_tokens` 全在核心方法里 ⇒ **DeepSeek 兼容端点 / 真 Anthropic / 任何 Anthropic 兼容网关走同一条代码** |
| 线路二 | **`openai` 官方 Python SDK** | Apache-2.0（v3.39.0 / 2026-10-26） | 覆盖 OpenAI 兼容端点（DeepSeek 的 `/v1`、vLLM、Ollama 的 OpenAI 面） |
| 统一层 | **自写 `jmb/providers.py`** —— 抄 `hermes-agent/providers/base.py` 的 `ProviderProfile` | MIT | 声明式 profile：协议类型 / base_url / 鉴权模式 / 默认模型 / 固定参数 / extra_body 钩子。~200 行、零依赖、**本机就有源码**（`Desktop\xj\hermes-agent`） |
| 端点怪癖 | 抄 `hermes-agent/agent/anthropic_adapter.py` 的 `_is_deepseek_anthropic_endpoint()` / `_requires_bearer_auth()` / `_normalize_base_url_text` 等纯函数 | MIT | **只抽这几个纯函数**，别整文件搬（它耦合 `utils.py` / `hermes_constants.py` / `tools.lazy_deps`） |

**两个必须知道的 SDK 坑**
1. **鉴权头在 v2 换过**：v1.17.0 发 `X-Api-Key`，**v2.3.0 发 `Authorization: Bearer`**。DeepSeek 兼容端点两者都收；换 provider 时按 profile 走，别写死。
2. **别用 `client.beta.*`**：v2.3.0 把 beta API 挪到 `client.beta.messages.*`（会改 URL 路径），第三方端点不要用。

**被否掉的三个**

| 方案 | 否的理由 |
|---|---|
| LiteLLM（MIT） | 100+ provider、2026 起带 Rust core，依赖体积换不回东西。**只读它 `web_search_options` 的归一化思路**（它能把**请求侧**抹平：OpenAI/xAI/Vertex/Anthropic/Gemini/Perplexity），但**响应侧抹不平**（`server_tool_use`/`web_search_tool_result` ↔ OpenAI `web_search_call` ↔ Gemini `groundingMetadata` 三种块结构）⇒ **不引这个依赖** |
| langchain（MIT） | 抽象层厚度对不上一个本地陪伴 agent，拉起整个 langchain-core |
| letta / letta-code（Apache-2.0） | 状态化 agent 平台 + DB，对一期超配 |

### 0.8.2 抓正文：`trafilatura`

| 项 | 值（PyPI JSON 实读，2026-10-27） |
|---|---|
| 版本 / 发版 | **2.3.1 / 2026-10-06** |
| 许可 / Python | **Apache-2.0** / `>=3.10` |
| 依赖 | `certifi` `charset_normalizer>=3.5.2` `courlan>=1.4.0` `htmldate>=1.11.0` `justext>=3.0.2` **`lxml>=6.1.3`** `urllib3<3,>=2.8.0` |
| 仓库 | `github.com/adbar/trafilatura` |
| 本机 | **已装 `lxml 6.1.3`（正好卡在它下限）** ⇒ 最重的依赖已经在位 |

**被否的**：`r.jina.ai`（本机实测超时）、DeepSeek `/v1/tools/fetch`（私有 API）、手写 HTML 解析。

### 0.8.3 本机兜底搜索：抄 SkillAbout，**别抄 last30days 的 keyless**

- ✅ **抄** `SkillAbout/hotsearching/ai-hotspot-digest/scripts/domestic_search.py` 的 `_search_bing`（`cn.bing.com` **本机实测 200 且结果块可解析**）+ 搜狗微信那条腿。
- ❌ **不抄** `last30days/scripts/lib/web_search_keyless.py` 的三条腿：DDG HTML（**本机实测超时**）→ Startpage HTML（**超时**）→ SearXNG（要自己起实例）。
- ❌ **不抄** `last30days/scripts/lib/web_fetch_keyless.py`：它走 `r.jina.ai`，**本机实测超时**。
- ⚠️ `last30days` 的 `WEB_BACKEND_ORDER = ("brave","exa","serper","parallel","keyless")` **现在一条也走不通** —— `~/.config/last30days/.env` 不存在，环境里 `BRAVE_API_KEY` / `EXA_API_KEY` / `SERPER_API_KEY` / `PERPLEXITY_API_KEY` / `PARALLEL_API_KEY` 全没有。

### 0.8.4 抄开源时连边界条件一起抄

hermes 那两块也要抄：
- **`thinking` 块要回传**：Anthropic 系在 thinking 模式下要求把上一轮 thinking 块**原样回传**，否则 400（`_is_deepseek_anthropic_endpoint()`）。⇒ 我原方案写的"一律丢弃"是**错的**，改成"不展示给用户，但**保留在历史里回传**"。
- **清洗未知内容块**：`hermes-agent/agent/message_sanitization.py`。

---

## Phase 1 · 骨架与体检（半天）

**要建**：`jmb/` 包（uv 管）、`jmb/config.py`、`jmb/cli.py` 的 `doctor` 子命令。

- 凭据来源顺序照抄既有实践：先读 env，缺则读 `~/.claude/settings.json` 的 `env` 段（**只报长度，不回显**）。这在 `scripts/probe_websearch.py` 里已经验证过一次能跑（第一次全 401 就是没回退造成的）。
- `doctor` 打印：端点 / 模型名 / token 长度 / `CONTEXT_FORGE_HOME` 是否就绪 / CF 包版本与路径 / 今天日报是否已跑。

**验收**
1. `jmb doctor` 在**新开的 shell**里也能跑通（这一条专门防 P1 那个坑）。
2. 打印里不出现任何 key 明文（自己 `grep -c` 一下输出）。

**护栏**：不要在这阶段就接 MCP / 不要建数据库。

---

## Phase 2 · 最小对话循环（1 天）

**要建**：`jmb/chat.py`（终端 REPL）+ `jmb/prefix.py`（稳定前缀装配）+ `jmb/transcript.py`（JSONL 记账）+ **`jmb/providers.py`（声明式 provider profile）**。

- **传输用官方 SDK，不用裸 httpx**（D29，§0.8.1）：线路一 `anthropic` 官方 SDK（Apache-2.0，v2.3.0），线路二 `openai` 官方 SDK。**它们的 `base_url` 原生可换** ⇒ DeepSeek 兼容端点、真 Anthropic、任何 Anthropic 兼容网关走**同一条代码**，换 provider 只改 profile 不改循环。
  ⚠️ 别用 `client.beta.*`（v2.3.0 会改 URL 路径）；鉴权头按 profile 走（SDK v2 发 `Authorization: Bearer`，v1 发 `X-Api-Key`）。
- **SSE**：先做非流式（好定位错误），通了就在**同一个 Phase 内**把流式接上（spec §4 承诺 HTTP+SSE、§6.1 承诺"会流式出字"）。SDK 自带 `client.messages.stream(...)`。
- **前缀布局严格按规格 §5（2026-10-27 评审重排）**：工具定义 → surface 能力表 → `SOUL.md` → `LEARNING.md` → `RELATIONSHIP.md` 摘要 → `interests.md` 摘要；**其后才是**检索结果 / 对话历史 / 用户这句。两个"摘要"按**文件 hash 缓存**，文件没变不重算（模型可变文件殿后，自改一次只废自己之后那段缓存）。
- **`thinking` 块：不展示给用户，但保留在历史里回传**（§0.8.4）—— 这条线路实测带回去/丢掉都 200，但 Anthropic 系在 thinking 模式下**要求回传**否则 400 ⇒ 按 provider profile 决定，别写死"一律丢弃"。
- 每轮把 `usage`（`input_tokens / cache_read_input_tokens / output_tokens`）写进 JSONL —— 这是 D13 口子 6 的按用户计量，现在免费拿到。

**文档引用**：`docs/research/2026-10-13-endpoint-measured.md` 的 A/B/C 组（**只取实测结论，请求形状以官方 SDK 为准**）+ `scripts/probe_endpoint.py`（已验证可跑的最小请求形状）。

**验收**
1. 连问 3 轮，第 2、3 轮 `cache_read_input_tokens` 明显 > 0（对齐实测的 2048 形态）。
2. 故意往 `SOUL.md` 开头加一个字符，命中应归零 —— **验证这条纪律确实被执行了**（这是唯一能证明前缀布局没被实现写歪的测试）。
3. `sessions/*.jsonl` 每行都有 usage 字段。
4. 切到 SSE 后逐字出字（不等整段生成完再吐）。
5. **只改 profile 里的 `base_url` + 模型名，就能切到另一个 provider，循环代码零改动**（这是"不绑死"的可验收形态）。
   ⚠️ 没有第二个真端点时的验收办法（评审补）：写一个几十行的假 OpenAI 兼容端点（不接模型、回固定 SSE chunk），把"切 profile 零改动"做实——别让这条永远停留在理论上。

**护栏**：不在这阶段做工具、不做记忆写入。

---

## Phase 3 · 搜索 + 读正文（1 天）

**要建**：`jmb/tools/web.py`，两个工具：
1. `search(query)` → 走服务端 `web_search_20250305`（**注释标明类型串来自实测 + Anthropic 官方 SDK 源码**）。这是 **Anthropic 官方的 server tool**，不是 DeepSeek 私有 ⇒ 换 provider 时换声明那一小段即可（§0.8.1）。
2. `fetch_page(url)` → 顺序：`llms.txt` 探测 → **`trafilatura` 提正文**（§0.8.2）。404/403 是正常结果，要当"读不到"上报，不是异常。

⚠️ **工具签名**：**不写 `count`** —— 那是 DeepSeek `/v1/tools/search` 的参数，而那条路已经不走了；服务端 `web_search_20250305` **没有条数参数** ⇒ **前 5 条在客户端截断**。**轮数**用官方的 `max_uses`（SDK 类型里有），但**这条线路认不认未验** ⇒ 这个 Phase 第一件事就是验。

**兜底**（服务端搜索不可用时）：抄 SkillAbout 的 `_search_bing`（`cn.bing.com` 本机实测 200）+ 搜狗微信那条腿。❌ **不抄** `last30days` 的 keyless 三条腿（DDG / Startpage 本机实测超时，SearXNG 要自己起实例）；❌ **不抄** `web_fetch_keyless.py`（`r.jina.ai` 本机实测超时）。

**约束**：一轮回答最多 **3 轮**搜索、每轮取 **前 5 条**（规格 §5 的【我定的】**目标值**）。
**这两条的执行机制分两层**（评审后补）：

- **端点侧**：服务端 web_search 工具认不认 `max_uses` / 条数参数，**没验过** ⇒ **这个 Phase 的第一件事就是验它**（一次请求的事）。认 ⇒ 3 轮写进工具声明；不认 ⇒ 落下面这道。
- **本地侧（不依赖任何未验参数，默认就上）**：发送前用 `count_tokens` 算预算（【实测】200 可用、计入 tools），超预算就把后续搜索结果摘要化再进上下文 ⇒ 实测那次 22,447 input 复发不了。

**验收**
1. 问一个必须查的问题（类似探针里那句"mcp 包最新版"），`usage.server_tool_use.web_search_requests` ≥ 1。
2. 问一个文档类问题并让它读正文：产出里能引用页面里的具体句子，而不是只有标题。
3. `fetch_page` 对一个 404 页面返回"读不到 + 原因"，不是抛栈。
4. **上限真的生效**：连续追问到触发上限，`input_tokens` 停在预算内（是本地闸门截的，不是碰巧）。
5. 端点侧认不认 `max_uses`，**这个 Phase 里出结论并写进注释**。
6. **`trafilatura` 对一个真实文档页能提出正文**（拿 `docs.github.com/llms.txt` 或任一 tech doc 页当样本）。
7. **"抓到了但正文是空的"也算读不到**（评审补）：对一个 JS 渲染页（或提取结果 < 200 字符的页），`fetch_page` 上报"读不到正文"，不把导航残渣当正文。

**护栏**：不要把搜索当读正文用（结果里没有明文正文，`encrypted_content` 客户端解不开）；不要把 `/v1/tools/search` 的 `count` 调大（那条路已经不走）；**不要手写 HTML 解析**。

---

## Phase 4 · Obsidian 落盘（1 天）— L1 闭环到这里才通 ｜ **落盘归 Context Forge（D28）**

**分工线（这一条不许含糊）**
- **内容生成 = jmb**：把一个话题写成讲解体 markdown，遵守 D26 六条。
- **落盘 = Context Forge**：路径围栏、归属标记、hash 乐观锁、冲突副本、draft → 正式。

**要建**：`jmb/obsidian.py` —— 但**只做"生成内容 + 拼相对路径 + 调 CF"，不做文件写入**。

⚠️ **CF 的写入 API 缺失时，这里不自己写一套顶上** —— 那就是两套写入器、两套归属语义，将来必打架。⇒ **本 Phase 的第一件事是确认 CF 那 5 个口子（G1–G5）谁补**，清单在 `docs/context-forge-gaps.md`。**这是一个真实的前置依赖，不是可以绕过去的排期细节。**

**jmb 侧生成内容的六条（D26）**
1. 拼相对路径 `<主题>.md`（落在 `personal_konwledge/jmb/` 下，**不再套那六个分类** —— 那六个是**他手写内容**的分类，jmb 另立一区；**落点由 CF 的围栏校验，jmb 只拼相对路径，不拼绝对路径**）
2. **不写 frontmatter**
3. 链接用 `[文字](URL)`
4. 形状照 `前端知识/babel.md` 的讲解体（直接开讲 / `##` `###` 分节 / `**大白话解释：**` 标签 / 可跑例子）
5. 长文加 `> 资料来源：…` + `## TL;DR`（照 `ai coding相关/trellis分享.md`）
6. 文件名中文描述性、不以 `#` 开头、可含空格

**归属**：不再用 jmb 自己维护的 `obsidian-owned.json` —— **归属标记由 CF 写**（缺口 G4：`jmb_owned` / `owner: jmb`）⇒ CF 的 `is_user_owned` 与 jmb 的"只写自己写过的"共用一套语义。

**draft**：先落 `<主题>.draft.md`，形状对了再改名到正式路径（G5）。

**⚠️ 先决条件**：CF 的 `vault_path` 现在指向 `Desktop/konwledge_base`（**错的库**）⇒ **改成 `Documents\Obsidian Vault`**（G6，改一行配置，零代码，**几分钟**）。

**验收**
1. 让它把一个真实话题写成 draft，人工比对形状与 `babel.md` 是否同族。
2. 连续写两次同一主题：第二次应该是**改**而不是**新建**。
3. 全库 `find . -name "*.draft.md"` 在确认后应为 0。
4. **库位正确**：写出来的文件落在 `Documents\Obsidian Vault\personal_konwledge\…`，**不是** `Desktop\konwledge_base`。
5. **归属标记在文件里**（`owner: jmb` 之类），且 jmb 第二次写同一篇**不会**被 CF 的 `is_user_owned` 拦下。

**护栏**：不动库里任何非它写的文件；不重命名别人的文件；不要顺手"整理"这个库；**不要在 jmb 里另写一套文件写入器**。

---

## Phase 5 · 记忆闸门（2 天）

**要建**：`jmb/gate.py` —— 模型只返回操作决策，代码落盘：

```
{op: ADD|UPDATE|DELETE|NONE, target: "RELATIONSHIP.md#规则3", payload, source_tag}
```
落盘顺序照 OpenClaw dreaming 的形状抄：**存 preimage → 写 → 记事件（带 source_tag）→ 界面上说一句"我改了 X，说 undo 可撤"**。

**不需要改 CF 就能开工（2026-10-27 评审实测更正）**：`store.put()`（`memory.py:1521`）**不碰 status**——draft 默认 `candidate`（`memory_models.py:97`）直接入库；自动转 active 只在 `MemoryLifecycle.publish`（`memory_lifecycle.py:315`），而 publish 只被 episode 流水线（watcher/worker）调用，jmb 不启 watcher 就走不到。原稿"要改 Context Forge 一处"是**错的定性**：那条改动（C6，见 `context-forge-gaps.md` §8 总清单）保护的是现有 `~/.context-forge` 实例（它的 watcher 在跑、模型记忆被自动转 active），与 Phase 5 无依赖，可并行做。

⚠️ **只改这一行不够，记忆会永远召不回来**（评审后补，实测）：

- 召回只认 `status IN ('active','conflicted')`（`memory.py:1784`/`:1792`/`:1855`）⇒ `candidate` 的行**召不回来**。
- Context Forge 自带的提审回路**只对高危 rule 开**（`risk.py:62`）⇒ 普通事实（"我周末一般不开电脑"）**拿不到 token**。
- ⇒ 只拆那个越权，普通事实会**永远停在 candidate** ⇒ 记不住，**而验收 2 还照样通过**（它只测"没自动生效"，测不出"永远不生效"）。

**提审与批准（spec §3.2 的实现，`jmb/gate.py` 里做）**：

1. **写入**：`store.put(memory_id, draft, ..., actor='model')`，`draft.status='candidate'`。
2. **提审**：`store.issue_confirmation(memory_id, version, reason=...)`（`memory.py:924`）⇒ uuid4 token（**600 秒有效**）⇒ jmb 把 token 与"要记的原文"挂起。**不逐条打断（评审改）**：挂到会话收尾批量列一遍——"今天想记这 3 条…回 ok 全记 / 回序号挑 / 回 no 全丢"，每会话上限 5 条【我定的】；你迟到回 `ok` 也行，批准前用 `open_confirmation`（`memory.py:946`，同版本复用活 handle、过期自动重发）拿活 token。**实现补充（2026-10-28）**：收尾会扫库里未确认的 candidate（最多 5 条）；明确 `no` 才 `suppress`，没回答/非终端/只选部分都留到下次续列。
3. **给你看**：REPL 里说一句"要记一条：<你的原话>。回 ok 记下" —— **它不许自己批**。
4. **批准**：你敲 `ok` ⇒ jmb 调 `store.approve_confirmation(token, from_tty=True)` ⇒ 该行 `candidate → active` ⇒ 进得了召回。
5. **撤销**：`store.suppress(...)` ⇒ `status='disabled'`（`memory_lifecycle.py:322`）。
   （`forge approve` 那条 CLI 通道留给高危 rule：终端里敲后 6 位挑战码才批；`mcp_server.py:138` 的 `context_forge_memory_confirm(token)` 取回正文。）

**初始化**：`CONTEXT_FORGE_HOME=%LOCALAPPDATA%\jmb\spaces\local\forge` ⇒ 陪伴体的库和现有 `~/.context-forge`（314 条代码记忆）**物理分开**。CF 本身通过 `context-forge` 包依赖进入 jmb（D32）：开发期 editable，发布期 wheel；不依赖用户本机的 CF 源码目录。

**jmb 这个 CF 实例的 `config.toml`**（**新建在 `CONTEXT_FORGE_HOME` 里，`~/.context-forge/config.toml` 一个字不动**）：

```toml
vault_path = "C:/Users/15532/Documents/Obsidian Vault/personal_konwledge/jmb"
knowledge_dir = "context-forge"     # 保持默认 ⇒ CF 自己的产物收进 jmb/context-forge/
```

⇒ CF 的知识根 = `vault_path / knowledge_dir`（`config.py:36-38`）⇒ **机器产物与手写区天然分开**。
⇒ **记忆只进 `memory.db`，不落 md**：md 投影的唯一自动触发点是 `watcher.py:436`（`forge watch` 跑时）+ 手动命令 `forge project-memories` ⇒ **jmb 只用 `MemoryStore` / `MemoryRecall`，不启 watcher/worker，就永远不投影**（零代码改动）。

**验收**
1. 让它写一条 `RELATIONSHIP.md` 规则 → 出现 preimage 副本 → 说 `undo` → 文件逐字节回到改前。
2. 让它写一条记忆 → `memory.db` 里 `status='candidate'`，不是 `active`。
3. **回 `ok` 之后，同一句 query 能召回这条**（`status` 变 `active`）—— 这条才是 Phase 5 真正的验收点。
4. `~/.context-forge/memory.db` 的 mtime **不变**（证明没污染旧库）。

**护栏**：`SOUL.md` 永远只读（`chmod`-级检查 + 写入器里硬拒）；不走 `consolidate()`（它只有测试调过，没在生产跑过）。

---

## Phase 6 · 白名单授权（1 天）

**要建**：`jmb/grants.py` + **`read_code` 工具本体**（2026-10-27 评审补：原稿只建闸门没建工具，而 L1 第 5/6 步全押在它上面）+ 会话内检查点。

- **`read_code(path)`**：列目录 / 读文件两个动作；先过 grants 校验再读；**响应必须截断**（D20 引的"工具响应要截断/分页"）——单次返回设 token 预算，超了给头部片段 + "文件共 N 行，已截断，要哪一段说一声"。
- `grants.json` 形状：`{owner, path, granted_at, scope, source_tag}` —— **是记录不是配置**（D13 口子 3）。**scope 两档（评审定）**：`session`（默认，会话结束即失效）/ `persistent`（他明说"以后都可以"才落）；配一条 revoke（`jmb grants revoke <path>`）——白名单只增不减，三个月后 D11 就空了。
- 路径校验：默认拒绝；`REALPATH` 归一后再比对（防 `..`）；**默认拒绝清单**里直接写死 `Desktop\platform-group-projects\**`。
- 同一次会话内已授权的仓不重复问。

**验收**
1. 让它读 `Context Forge` → 弹一次授权 → 允许 → 读到。
2. 让它读 `platform-web` → 拒绝且**不再追问**，而是说清"这个仓不在白名单"。
3. 授权后再读同一仓不重复弹。
4. `grants.json` 里每条都有 `granted_at`。
5. 读一个几千行的文件，返回在预算内且带"已截断"提示（评审补——没有截断，一次 `read_code` 就能把上下文打爆）。
6. `session` 授权新开会话后失效；`persistent` 授权可被 revoke（评审补）。

**护栏**：不要在代码里 `if 'platform-group' in path: allow` 这种隐式白名单；一切靠配置 + 记录。

---

## Phase 6.5 · 写代码（D34，2026-10-28）

**要建**：`jmb/code.py`（`write_file` / `edit_file` / `run_command` + `CodeSession`）、`jmb/search.py`（只读 `grep` / `find`）、`grants` 的写/执行会话授权、`chat` 的工具路由、`tests/test_code_tools.py` + `tests/test_search_tools.py` + `tests/test_sandbox.py` + `tests/test_webfetch.py`。

**规则**：
- **任意路径**；硬拒公司仓、jmb 自身 `spaces/`、`.git` 目录。
- 写/执行首次触发**本会话**授权，之后本会话放行；不做 persistent write/exec。
- `edit_file`：精确优先、唯一、不重叠、模糊归一、保留 BOM/CRLF、返回 diff；`write_file` 只用于新建/完整重写。
- 每个用户轮次一个 change set + preimage；`undo` 回滚整轮；文件之后被改过则拒绝回滚。
- **命令默认 Docker 沙箱**：`JMB_SANDBOX_IMAGE`（默认 `python:3.13-slim`）、`--network none`、只读根、cap-drop、2g/2c；只有 `JMB_SANDBOX=host` 才显式关闭。`fetch_page` 拒绝 localhost/内网/回环/保留地址，重定向也检查。
- **命令副作用不可 undo**；命令输出截断 20KB/800 行，完整输出落盘。
- 借 Pi 的 `edit`/`read`/`bash`/`truncate` 边界条件，不引 Pi 的 TypeScript runtime/session tree/skills。

**验收**：`python -m unittest discover -s tests` 39 项通过；在临时目录让 jmb 新建/改文件 → 看 diff → `undo` 复原；跑命令 → 退出码/截断/超时；公司仓/spaces/.git 拒写；Docker 启动后跑一条容器命令（本机 daemon 未运行，待验收时补）。

---

## Phase 7 · 每日清单 + 桌宠（1 天）

**要建**：`jmb/brief.py` + 定时。（桌宠原型已清；发布形态见 D33 内置渲染层）

- **三源**：
  - GitHub：`api.github.com/search/repositories?q=created:>N天+stars:>X&sort=stars`（**没有官方 trending API**；认证 30 次/分钟）
  - 技术热点：搬 SkillAbout 的 `fetch_html` / `parse_star_history` / `fetch_repository_description`（**删掉 DDG 腿**）
  - 会议：`ccfddl/ccf-deadlines` 的 `date`+`place`（走 `api.github.com` 取 contents + base64 解码）+ Meetup `POST https://www.meetup.com/gql2`（港澳/新加坡）+ GDG 的 `__NEXT_DATA__`
- 输出：**8 条**【我定的】，字段 = 序号 / 名称 / 地址 / 一句话介绍；**一句话介绍一律来自现成字段**（repo description / og:description / 榜单自带摘要），没有就写"（无介绍）"——**brief 全程零 LLM 调用**（评审定：无人值守场景少一个故障面，也符合 D18"不许凭模型记忆写"）；**会议那段开头必须带固定免责句**（"大陆同城的活动我拿不到…"）
- 触发：**10:00 每天一次**（D30：**不做"当天第一次开机补跑"**，也不配开机触发器）。实现**优先 `schtasks`，`qoder_cron` 作退路**（评审改：qoder_cron 要 Qoder 开着才跑，schtasks 只要登录着就跑——10:00 他机器大概率开着且已登录）。**只挂 10:00 那一条，不挂 ONLOGON/ONSTART**。
  ⚠️ **代价写明**：10:00 时机器关着 ⇒ **那天就没有清单**。这是 D30 明确接受的代价，不是待修的 bug。
- 桌宠：`POST /state` + `POST /bubble`，**token 401 时重读一次**（原型期；发布形态见 D33 内置渲染层）

**验收**
1. 手动触发一次，输出 8 条 + 三段来源标注齐全，会议段有那句免责说明。
2. 同一天再触发一次 → **不重跑**（幂等）。
3. **过了 10:00 但机器一直关着 ⇒ 那天确实没有清单**（D30 接受的代价；这条验收是为了把行为钉死，别以后有人"顺手"把它补回来）。**静态检查（评审补）**：`schtasks /query` 输出里没有 ONLOGON/ONSTART 条目——把"没人补回来"变成可 grep 的。
4. ~~Petdex 气泡验收~~ 原型已清（2026-10-28）；待 D33 内置渲染层落地后再验。

**护栏**：不绕验证码；不把 Meetup 当唯一依赖；不把自由文本日期解析成"还剩几天"；不在没有内容时也弹气泡。

---

## Phase 8 · MCP 暴露与多宿主（1 天）— spec §6.2 那一格 ｜ ⚠️ **建议后移二期（评审）**：L1/L2/L3 没有一个需要它；做它之前必须先有下面两条硬前置（鉴权 + 单写者）

**要建**：`mcp_server.py` 加一档 transport（`run(transport="stdio")` 旁边，`:431`）+ 把人格三个文件作为 **MCP Resource** 供出。

- 传输：`streamable-http`（mcp 1.30.0 里服务端实现已在，`server/fastmcp/server.py` 有 `streamable_http`）。
- **鉴权（评审补，硬前置）**：streamable-http 起来后任何本机进程都能连——这台机器跑着大量 agent 工具链，"本机=可信"不成立，而这份库的隐私等级就是 D11 的动机。照 Petdex 的形状：token 文件 0600、每次启动重生成、客户端 401 后重读一次。
- **单写者边界（评审补，硬前置）**：memory.db 一期只有 jmb 进程一个写者。宿主侧**只读**——CF 现有 MCP tool 里的写口（`memory_supersede` / `memory_extend` / `memory_overturn` / `memory_mark` / `memory_scope` 等，`mcp_server.py:151-331`）在 jmb 的实例上必须不注册（CF 改动总清单 C8 的 `read_only` 开关）：宿主写入既绕过 jmb 的 gate（无 source_tag、无确认），又引入两进程并发写 SQLite。
- **明说的边界（评审补）**：宿主里的"它"读得到人格与记忆，但**记不了新东西、没有会话连续性**；"同一个它"一期只成立于 jmb 自己的入口。
- Resources：`add_resource`（`server/fastmcp/server.py:542`）/ `list_resources`（`:364`）—— Context Forge 现在**一个 resource 都没暴露**（grep 零命中），这三条是要写的。
- 为什么必须做：stdio = "the client launches the server as a subprocess" ⇒ N 个宿主 = N 个后端进程，一个它就变成了 N 个它。
- 人格三文件当 Resource 供出，**不塞进工具描述**（工具列表要 deterministic order 以利缓存）。

**验收**

1. 同一个后端同时被两个宿主连上（Qoder + Claude Code），两边看到的是**同一份** `SOUL.md` / `RELATIONSHIP.md` / `interests.md`。
2. `list_resources` 能列出这三条，内容与磁盘一致。
3. 宿主里问一句，它的语气与 `SOUL.md` 一致（`surface` 决定**能力**，不决定**人格**）。
4. 无 token 的连接被 401；宿主侧看不到任何写类工具（评审补）。

**护栏**：不改 Context Forge 的 schema；`surface` 进请求参数，不进 `if` 分支。

---

## Phase 9 · 收口与验证（半天）

1. **全链路**：从"我想搞懂 X"开始，走到 Obsidian draft 落盘 → 确认 → 正式落盘 → 记忆闸门说一句"我改了 X" → `undo` 回滚。
2. **反模式 grep**：
   - `grep -rn "requests\|bs4" jmb/` 应为 0（**lxml 允许** —— `trafilatura` 依赖它）
   - `grep -rn "if owner ==" jmb/` 应为 0
   - `grep -rn "raw.githubusercontent" jmb/` 应为 0
   - `grep -rn "frontmatter\|---$" jmb/obsidian.py` 应为 0（frontmatter 由 CF 写，不由 jmb 写）
   - `grep -rn "issue_confirmation\|approve_confirmation" jmb/` 应 **> 0**（没有提审就没有生效路径 ⇒ 记忆写了也召不回来）
   - `grep -rn "deepseek" jmb/` **应只出现在 provider profile 的默认值里**（不许散落在业务代码里）
3. **不污染检查**：`~/.context-forge/memory.db` 的 mtime 与 Phase 5 开始时一致。
4. **成本记账**：把这几天的 `sessions/*.jsonl` 汇总，给出"每天实际花了多少 token、多少新算、多少命中"，据此**重新定 Phase 3 的 3 轮/5 条**。

---

## app 壳 + 内置桌宠渲染层（D33/D35，v1 已落地）

**2026-10-29 v1**：`jmb app` = Tkinter 聊天窗口 + `PetWindow` Canvas 占位；和终端共用 `ChatSession`；GUI 授权走主窗口确认框；44 tests。PySide6 安装卡住，按 D33 回退 Tkinter；spritesheet/托盘/严格穿透/PySide6 仍待做。

**产品形状**：桌宠是 jmb 自己的一个窗口，不是外接 Petdex，也不是 sidecar；用户只装 jmb。

**先验证的技术点**（不写业务代码）：
1. **事件循环**：GUI 主线程 + chat REPL 工作线程 + 线程安全事件队列；Ctrl+C 和退出要能走完 `confirm_pending`。若 jmb 以后有 GUI 壳，桌宠作为壳里一个窗口。
2. **框架**：PySide6 vs pywebview vs Tkinter 做一个最小透明置顶窗口 + 精灵动画 + 点击穿透的 spike，按"透明/置顶/穿透/多屏/体积"打分；PySide6 是默认候选。
3. **pet 格式**：复用 `pet.json` + 8×9/8×11 网格、192×208 帧；行序抄 Petdex 源码；素材用 jmb 自有形象（boba 无 license，不随产品分发）。
4. **状态映射**：idle / thinking / searching / working / waiting / failed / waving；chat/brief 只发事件，不碰 UI。
5. **打包**：PySide6 LGPL 合规、代码签名、Windows 优先；pet 资源随包。

**验收**：不装 Petdex 的干净机器上，jmb 启动出现桌宠；聊天/搜索/日报能切状态和冒泡；透明区点击穿透；拖拽/多屏/DPI 正常；关 jmb 桌宠一起退出。

**不做**：不打包 Petdex、不做 sidecar、不复制它的 App、不先写业务适配层。

---

## 拿来的清单（谁给了我们什么，别重复造）

| 来源 | 许可 | 拿什么 | 不拿什么 |
|---|---|---|---|
| **Anthropic 官方 Python SDK** | Apache-2.0 | 线路一的全部实现：`base_url` 可换、`messages.create/stream/count_tokens`、`web_search_20250305` 的类型定义 | 不用 `client.beta.*` |
| **OpenAI 官方 Python SDK** | Apache-2.0 | 线路二的全部实现 | 不引它的 agent 层 |
| **trafilatura** | Apache-2.0 | 抓正文的全部实现（2.3.1 / 2026-10-06） | 不手写 HTML 解析 |
| Petdex | MIT | 只抄 pet 格式（pet.json + 网格）、state 枚举、气泡限长经验 | 不嵌它的 App；渲染层自写（D33）；boba 素材无 license，不随产品分发 |
| Pi coding agent | MIT | `edit` 契约（唯一/不重叠/模糊/BOM/CRLF/diff）、`read` 的 offset/limit 与截断、`bash` 的超时/杀进程树/输出落盘 | 不引 TypeScript runtime、session tree、skills、extensions；不照搬“无审批/无沙箱” |
| Context Forge | 他自己的 | 记忆内核（provenance/版本/衰减/冲突/FTS5 中文分词）+ `CONTEXT_FORGE_HOME` 做物理隔离 + **提审与批准**（`issue_confirmation` / `open_confirmation` / `approve_confirmation` / `pending_confirmations`）+ **vault 写入四件套**（路径围栏 / 归属保护 / hash 乐观锁 / 冲突副本）+ `LlmGateway` 抽象 + `resolve_remote_url` 的 base_url 解析 | 不改 schema；不接 embedding（一期不需要） |
| SkillAbout | 他自己的 | `fetch_html` / `parse_star_history` / `fetch_repository_description` / 冷却去重 + **`_search_bing`（本机唯一实测通的搜索腿）/ 搜狗微信** | 不要 dashboard、不要 DDG 腿 |
| ccfddl | MIT | AI 会议 `date`+`place`（走 api.github.com） | 不做投稿截止日 |
| DeepSeek | 商业 API | **只当"当前这条线路的 provider"** —— base_url + 模型名写在 profile 默认值里 | **不用它的 `/v1/tools/search` 与 `/v1/tools/fetch`**（私有 API，与"不绑死 provider"冲突） |
| Qoder `qoder_cron` | 宿主能力 | 10:00 定时 | 不用它的 `location=cloud`（不继承本地环境）；**不挂开机补跑触发器** |
| hermes-agent | MIT | `SOUL/USER/MEMORY` 三文件约定 + `_memory_write_origin` 来源标签 + 复盘"我改了哪些"摘要 + **`providers/base.py` 的 `ProviderProfile` 声明式 provider 表** + **`anthropic_adapter.py` 的端点怪癖纯函数** + **`message_sanitization.py` 的未知块清洗** | 不采用它的运行时；不整文件搬 `anthropic_adapter.py` |
| OpenClaw 文档 | MIT | dreaming 的"模型只出操作决策 + 确定性写入 + preimage + 旧条目保留率"形状 | 不采用它的 gateway |
| 我的探针 | — | `scripts/probe_*.py` 里已验证的请求形状与凭据回退逻辑 | 它们不是产品代码 |

---

## 待他确认的四件事（会改计划）

1. **§3.1 五类记忆**（我替他定的 v0）—— 改了会影响 Phase 5 的落盘目录。
2. **SOUL.md 词**——改了只影响 Phase 2 的前缀内容，不影响结构。
3. **`%LOCALAPPDATA%\jmb\` 这个家目录**——改了影响 Phase 5/6 的路径常量。
4. **§3.2 提审与批准**（我落的机制）—— 普通事实也要你敲一次 `ok` 才生效；松绑（你原话说过的事实直接 active、只有它自己总结的规则走确认）会让"你确认才生效"这条失效。**这条只影响 Phase 5 的第 3 步，不影响结构。**
   **评审后补（2026-10-27）**：确认从"逐条打断"改成会话收尾批量列一遍，迟到用 `open_confirmation` 兜底，摩擦已小很多；每会话提议上限 5 条【我定的】。

**已确认的两件（2026-10-27）**
- ✅ **Obsidian 落盘归 Context Forge（D28）** —— **CF 那 5 个口子由他自己改**，缺口清单在 `docs/context-forge-gaps.md`。**jmb 侧不写文件写入器，等 CF 补完再开 Phase 4。**
- ✅ **两条 provider 协议够（D29）** —— Anthropic 协议 + OpenAI 协议；抓正文用 `trafilatura`。

**已确认的第三件（2026-10-28，D32）**
- ✅ **CF 以独立包被 jmb 依赖** —— 开发期 editable 指向 `../Context Forge`，发布期固定版本 wheel；数据各一套，不共享 `~/.context-forge`，也不把 CF 源码复制进 jmb。

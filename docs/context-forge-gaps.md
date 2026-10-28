# Context Forge 不足点清单 · Obsidian 写入这一格

日期：2026-10-27（**同日修订一次**：形状从"CF 库根"改成"jmb 专属目录"，见 §0）｜ 状态：**待他裁定**（"你改 CF" / "别人改 CF" / "CF 不用改，jmb 另写"）
来源：读 `Desktop\xj\Context Forge` 源码 + 读 `~/.context-forge/config.toml` + 读 `hermes-agent` 源码 + 查 PyPI 实际元数据

---

## 0. 形状（2026-10-27 改）

**新目录已建**：`Documents\Obsidian Vault\personal_konwledge\jmb\`

```
Documents\Obsidian Vault\
  ├── personal_konwledge\
  │     ├── agent\  ai coding相关\  blog开发过程\  前端知识\  工作经验\  服务器相关\   ← 你手写的 22 篇
  │     └── jmb\                                    ← ★ 新建，jmb 专属
  │           ├── <主题>.md                         ← jmb 写的学习文档（你要求时）
  │           └── context-forge\                    ← CF 自己的产物，自动收在这里
  │                 ├── memories\<sha16>.md
  │                 ├── knowledge\accepted\<id>.md
  │                 └── index.md
  ├── nginx灰度发布.md / 给GitLab…_投稿稿.md / 几张 html+docx   ← 根目录零散产物
```

**分工线**
- **内容生成 = jmb**：把话题写成讲解体 markdown（D26 六条里除落点外的五条）
- **落盘 = Context Forge**：路径围栏、归属标记、hash 乐观锁、冲突副本、draft → 正式

**三个由此而来的结论**

| 结论 | 依据 | 代价 |
|---|---|---|
| ✅ **记忆只进 `memory.db`，不落 md —— 零代码改动** | md 投影的**唯一自动触发点**是 `watcher.py:436`（`forge watch` 跑的时候调 `MemoryProjector`）；另一个是手动命令 `forge project-memories`（`cli.py:127`）⇒ **jmb 只用 `MemoryStore` / `MemoryRecall`，不启 watcher/worker，就永远不投影** | jmb 不能依赖 CF 的 `forge watch` 做任何事（它本来也不需要） |
| ✅ **机器产物隔离不用改代码** | CF 的知识根是 **`vault_path / knowledge_dir`**（`config.py:36-38` `Settings.root`），`knowledge_dir` 默认 `"context-forge"` ⇒ 产物自动落在 `<vault_path>/context-forge/` | `vault_path` 要指到 jmb 专属目录，`knowledge_dir` 保持默认 |
| ✅ **现有 CF 一个字不用动** | `~/.context-forge/config.toml` 保持 `vault_path = "Desktop/konwledge_base"` 不变；**jmb 用的是另一个实例**（`CONTEXT_FORGE_HOME=%LOCALAPPDATA%\jmb\spaces\local\forge`，`config.py:46-53`）⇒ 两边配置物理分开 | jmb 实例要新建一份 `config.toml`（Phase 5 的事） |

⇒ **原来那条"CF 的 `vault_path` 指错库"的问题不存在了** —— 它指的是**你现有的** CF 实例，而那个实例跟 jmb 无关，不该被牵动。改成：**jmb 实例建的时候配对**（见 §5）。

---

## 1. CF 现在已经有的（可直接复用，不要重写）

| 能力 | 位置 | 说明 |
|---|---|---|
| **vault 落点隔离** | `config.py:36-38` `Settings.root` = `vault_path / knowledge_dir` | **机器产物与手写区天然分开**，一个配置项搞定 |
| **路径围栏** | `context_forge/vault.py:35-54` `_safe()` | 目标必须落在 vault 根下，否则 `ValueError: path escapes vault root`；**子目录是放行的** |
| **归属保护** | `vault.py:62-68` `is_user_owned()` | 读 frontmatter 的 `user_owned: true`；`vault.py:99-110` 命中就 `FileExistsError` 跳过 |
| **hash 乐观锁 + 冲突副本** | `vault.py:176-190` `update_with_expected_hash()` | sha256 不匹配时写 `.conflict-<ts>` 副本，**不覆盖**用户改动 |
| **原子写** | `vault.py:41-52` `_atomic_write` | 临时文件 + `os.replace`；`__init__` 里 `mkdir(parents=True)` |
| **vault 根自动创建** | `vault.py:33` | `Vault(root)` 会把根和子目录建出来 |
| 记忆 → vault 投影 | `context_forge/memory_projection.py:37-49` | 落 `memories/<sha16>.md` —— **jmb 不启用**（§0） |
| 索引生成 | `context_forge/index.py:226` | 生成 `index.md`（落在 vault 根下） |
| 反向导入 | `context_forge/cli.py:215-231` `sync` | **单向** vault → `memory.db`；jmb 不跑 |

⇒ 这套东西我在 spec §3.1 里**自己重新设计过一遍**（"只写自己写过的文件" + "改前存副本" + "冲突不覆盖"）——**CF 已经有了，我那套是重复造**。

---

## 2. CF 缺的（不足点清单 —— 比第一版少一条）

### 2.1 必须补（不补则 jmb 写不了 Obsidian）

| # | 缺什么 | 现状证据 | jmb 侧的需要 |
|---|---|---|---|
| **G1** | **任意相对路径 + 自定义文件名的写入口** | 现有落点只有两个**固定模板**：`knowledge/accepted/<knowledge.id>.md`（`vault.py:99-110`）、`memories/<sha16>.md`（`memory_projection.py:37-49`） | 落 `personal_konwledge/jmb/<主题>.md`（文件名是中文主题、可含空格）—— **注意：相对路径是相对 `vault_path`，不是相对 `knowledge_dir`** |
| **G2** | **CLI 子命令** | `cli.py` 注册了 30+ 个子命令（`init`/`install-hook`/`worker`/`sync`/`mcp-install`/`approve`/`retag-vault`/`search`/`watch`/`doctor`…），**没有 `write` / `export` / `note`** | `forge write-note --path <相对路径> --stdin --owner <标签> [--draft]` |
| **G3** | **MCP 写 tool** | `mcp_server.py:86-292` 注册了 14 个 `@server.tool()`：search / memory_search / memory_get / memory_confirm / memory_mark / memory_feedback / memory_apply / memory_report / memory_effectiveness / memory_hygiene / get / match_rules / recent_knowledge / recent_rules / record_feedback —— **全部是读或反馈，一个都不能写文件** | jmb 是 MCP client，要能远程写；`context_forge_vault_write(path, content, owner, draft=False)` |
| **G4** | **写入者归属标签** | CF 现有归属语义是**单向的**：`user_owned: true` = "这是你的文件，别碰" | jmb 要的是**双向的**："这是 **jmb 写的**文件，可以改"（否则 jmb 第二次写同一篇就撞上 `is_user_owned` 或被当成别人的文件） |
| **G5** | **draft → 正式 的两段写** | CF 没有 draft 概念 | jmb 第一次写新文档先落 `<主题>.draft.md`，形状对了再改名到正式路径 |

### 2.2 已解决（第一版里列为缺口，现在不用做了）

| 原缺口 | 为什么不用了 |
|---|---|
| ~~G6 `vault_path` 指错库~~ | 指的是**你现有的** CF 实例（`Desktop/konwledge_base`），与 jmb 无关 ⇒ **不动它**。jmb 用自己的实例，配成 `vault_path = "Documents/Obsidian Vault/personal_konwledge/jmb"` |
| ~~机器产物落点可配~~ | **`knowledge_dir` 已经是配置项**（`config.py:36-38`）⇒ 机器产物自动收进 `jmb/context-forge/`，**不用改代码** |
| ~~关掉 md 投影~~ | **jmb 不启 `forge watch` 就没有投影**（`watcher.py:436` 是唯一自动触发点）⇒ **不用改代码** |

---

## 3. 归属语义的对齐（这条要他裁，因为两种语义都成立）

CF 的 `user_owned` 与 jmb 想要的"只写自己写过的文件"**方向相反但可以共存**，需要 CF 支持**第三个值**：

| frontmatter 标记 | 含义 | 谁写 |
|---|---|---|
| `user_owned: true` | 你的文件，**谁都不许改**（CF 已有） | 他手写 |
| `jmb_owned: true`（或通用 `owner: jmb`） | **jmb 写的**，jmb 可以改，别人要问 | jmb |
| 无标记 | 中立：只新增，不覆盖 | — |

对齐后，jmb 侧的"只新增或改它自己写过的文件"就变成"**只碰 `jmb_owned` 的**"，不用 jmb 自己再维护一份 `obsidian-owned.json`。

### G4 的两种实现，代价不同（**要选一个**）

| 方案 | 好处 | 代价 |
|---|---|---|
| **A · 沿用 frontmatter**（`jmb_owned: true`） | 跟 CF 现有的 `user_owned` 一套机制，改动最小 | **jmb 写的文件会多一个 frontmatter 块** —— 而 D26 第 2 条说"不写 frontmatter"（那 22 篇里 0 篇用）。⇒ 库会出现两种风格 |
| **B · CF 侧另记一张表**（`vault_ownership` 表：path → owner） | **文件保持干净**，严格符合 D26 第 2 条 | CF 要多一张表 + 一套增删改 |

⇒ **建议 B**：D26 那条"不写 frontmatter"是照着他 22 篇的现状定的，值得为它多一张表。
⇒ 但这是 CF 内部实现选择，**只有改 CF 的人能定**；jmb 侧不依赖它 —— jmb 只要求"CF 能区分"这三种归属。

---

## 4. jmb 侧要留给 CF 的契约（不管谁改 CF，契约先定死）

```
写入：  forge write-note --path "<相对 vault_path 的路径>" --stdin --owner jmb [--draft]
       或  MCP: context_forge_vault_write(path, content, owner, draft=False)
返回：  { ok, written_path, sha256, skipped_reason? }

必须保证的五条：
  1. 路径围栏：不能逃出 vault 根（CF 已有 _safe）；相对路径的基准是 vault_path，不是 vault_path/knowledge_dir
  2. 归属：owner 标记 + 不覆盖非本 owner 的文件
  3. 冲突：hash 不匹配时写 .conflict-<ts> 副本，不静默覆盖（CF 已有）
  4. 原子写（CF 已有）
  5. draft 模式：先落 .draft.md，改名到正式路径要一个显式动作
```

**内容层不归 CF**：讲解体形状、`## TL;DR`、`> 资料来源：`、`[文字](URL)`、不写 frontmatter、文件名中文描述性 —— 这几条是**jmb 生成内容**时遵守的，CF 不该管内容长什么样。

**⚠️ 一条必须说清的边界**：CF 的 `knowledge_dir` 默认是 `"context-forge"`，而 `Vault` 的 root 是 `vault_path/knowledge_dir`。⇒ **jmb 要写的 `personal_konwledge/jmb/<主题>.md` 相对 `vault_path`，但相对 CF 的 vault root 它是"外面"** ⇒ **G1 必须支持"相对 vault_path 的路径"，不能只支持"相对 vault root 的路径"**。这一条不定死，jmb 写不进那个目录。

---

## 5. jmb 侧要做的（不是 CF 的活）

| 活 | 落点 | 什么时候 |
|---|---|---|
| 建 jmb 专属目录 | `Documents\Obsidian Vault\personal_konwledge\jmb\` | ✅ **已建**（2026-10-27） |
| 建 jmb 的 CF 实例 + 配 `config.toml` | `%LOCALAPPDATA%\jmb\spaces\local\forge\config.toml`：`vault_path = ".../personal_konwledge/jmb"`、`knowledge_dir = "context-forge"` | ✅ **已建**（2026-10-28） |
| CF 的代码怎么到达 jmb | 通过 `context-forge` 包依赖（D32）：开发期 editable，发布期 wheel | 全程 |
| 不启 `forge watch` / 不跑 `forge project-memories` | —— | 全程 |
| 只用 `MemoryStore` / `MemoryRecall` | —— | Phase 5 |

---

## 6. 不用 CF 补的（CF 缺，但 jmb 自己写就行，别塞给 CF）

| 能力 | CF 现状 | 归谁 |
|---|---|---|
| 流式 SSE | **没有**（`provider_http.py:366` 硬编码 `"stream": False`） | jmb 自己写循环 |
| tool loop | **没有**（请求体无 `tools`） | jmb 自己写循环 |
| MCP client | **没有**（全仓 grep `stdio_client`/`ClientSession` 零命中） | jmb 自己写 |
| 联网搜索 / 抓正文 | **没有**（全仓无 requests/bs4/trafilatura） | jmb 自己写（用 OSS 库，见 spec §5） |
| 常驻 HTTP 服务 | **没有**（无 fastapi/uvicorn/http.server） | jmb 自己写 |
| 插件机制 | **没有**（无 `[project.entry-points]`） | 一期不需要 |

⇒ **CF 现在已有的、jmb 直接白拿的**：`MemoryStore` / `MemoryDraft` / `put` / `issue_confirmation` / `approve_confirmation` / `suppress` / `MemoryRecall.search` / `LlmGateway` 抽象（`domain.py:277`）/ `provider_http.py:143` 的集中 `_post` / `resolve_remote_url` 的 base_url 解析 / `scheduled.run_due` 幂等台账（`scheduled.py:91`）/ `autostart.py` 的 Windows 开机自启形状 / FastMCP 骨架。

---

## 7. 时间账

- **G1 / G2 / G4 / G5**：都在 `vault.py` 上加一层，估计**半天**；**G3** 是 `mcp_server.py` 加一个 tool，**一两小时**。
- **G1 里最要紧的是"相对路径基准是 vault_path"**（§4 最后一条）—— 这条不定死，Phase 4 写出来的东西会落在 `jmb/context-forge/` 里面。
- **jmb 侧**：Phase 4 改成"等 CF 补 + 定契约"。**若 CF 短期没人改，jmb 的 L1 第 7 步就落不了地** —— 这是排期上的真实依赖，不是可以绕过去的。

⇒ **建议**：jmb 侧先把 Phase 1–3、5–7 做掉（它们不依赖 CF 补），**Phase 4 等 CF**。

---

## 8. CF 改动总清单（2026-10-27 评审归拢 —— "cf 我自己改"的完整范围）

G1–G5 只覆盖 Obsidian 写入这一格。评审把散在 spec / implementation-plan 里的**其余 CF 改动**归到这里，一次手术做完：

| # | 改什么 | 在哪 | 为什么 | jmb 依赖它吗 |
|---|---|---|---|---|
| G1–G5 | 见 §2.1（任意相对路径写入口 / CLI / MCP 写 tool / 写入者归属 / draft 两段写） | `vault.py` `cli.py` `mcp_server.py` | L1 的 Obsidian 落盘 | **是**（Phase 4 的前置） |
| **C6** | `publish` 的无人值守 active 改成走策略（`actor=="model"` 不再强行 active，保持 candidate + 走 issue/approve，与 spec §3.2 同一套） | `memory_lifecycle.py:315`（publish 在 `:303`） | 保护**现有** `~/.context-forge` 实例：CC hooks 的 watcher 在跑，模型写的记忆被自动转 active。⚠️ **jmb 不依赖它**——`store.put()`（`memory.py:1521`）不碰 status，draft 默认 candidate 直接入库；原稿把这条错标成 Phase 5 的前置，已更正 | **否**（jmb 不启 watcher） |
| **C7** | owner 穿参：检索路径硬编码 `DEFAULT_OWNER`（`memory_recall.py:178`；`memory.py:1809`/`:1826` 的 owner 默认值没被调用方穿下去） | `memory_recall.py` `memory.py` | 单 owner 时无害；第二个 owner 一出现就是"跨 owner 召回"事故（D13 警告的形状）。现在改是一小时，将来是数据事故 | **否**（一期单 owner，顺手修） |
| **C8** | `create_server(read_only=True)` 开关：jmb 实例经 streamable-http 暴露时，不注册写类 tool（`memory_supersede` / `memory_extend` / `memory_overturn` / `memory_mark` / `memory_scope` 等，`mcp_server.py:151-331`） | `mcp_server.py` | memory.db 一期单写者（jmb 进程）；宿主写入绕过 jmb 的 gate（无 source_tag、无确认）⇒ 宿主侧只读 | **是**（Phase 8 的前置；Phase 8 本身建议后移二期） |

**时间账补**：C6 半天（"策略"的最小形状 = 保持 candidate + issue/approve 通路，现有零件都在）；C7、C8 各约一小时。

**jmb 侧依赖图更新**：Phase 1–3、5–7 照做（依赖 G1–G5 的只有 Phase 4）；**Phase 8 = C8 + 本地 token 鉴权，建议后移二期**。CF 的改动通过包版本进入 jmb（D32），不再 sys.path 挂源码目录。

# 决策记录

格式：每条含【决定】【为什么】【已知短板】【依赖】【状态】。被否决项的理由一并留下。
进度看板：✅ 已定 ⏳ 待定 ⬜ 未开始

### 看板（2026-10-27 评审整理；详情与被否理由在正文）

| D | 一句话 | 状态 |
|---|---|---|
| D1 | 驱动权归用户 | ✅（"唯一主动=日报"由 D23/D24 修订） |
| D2/D9 | 壳自研（薄 loop） | ⏳ spec 已按此写，待正式点头 |
| D3 | 不做学习/聊天模式系统 | ✅ |
| D4' | 入口形态 | 最终形状 = 终端 REPL + 桌宠 + CF MCP（spec §1/§4） |
| D5 | 记哪几类 | ⏳ spec §3.1 v0 代答（五类），等他点头 |
| D6 | 它能改哪些文件 | ✅（D21 定为乙） |
| D7 | 学习动作清单 | ⛔ 被 D14 取代 |
| D10 | 需求清单作废重问 | ✅（过程条目） |
| D11 | 代码可见性 = 白名单 | ✅ |
| D12 | 多端功能分层 | ✅ |
| D13 | 多用户 = 甲，一期留口子 | ✅（HTTP 口子表述 2026-10-27 评审更正） |
| D14 | L1 流程定形 | ✅ |
| D15 | 学习文档落 Obsidian | ✅ |
| D16 | 人格只有一个 | ⏳ 三次无异议，待最终点头 |
| D17 | 一期不做手机端 | ✅ |
| D18 | L2 列清单不给观点 | ✅ |
| D19 | 兴趣记录 | ✅ |
| D20 | 联网选型 | ✅（被 D25/D29 两度修正，现行 = 服务端搜索 + trafilatura） |
| D21 | 自我改写 = 乙 | ✅ |
| D22 | L3 提旧事 = 乙 | ✅ |
| D23 | 09:00 日报 | ⚠️ 被 D24/D30 覆盖 |
| D24 | 10:00 + 主动性=甲 | ✅ |
| D25 | 服务端 Web Search | ✅ |
| D26 | Obsidian 六条写法 | ✅ |
| D27 | 会议源降级保留 | ✅ |
| D28 | Obsidian 落盘归 CF | ✅ |
| D29 | 不绑 provider + 开源件 | ✅ |
| D30 | 取消补跑 | ✅ |
| D31 | 评审修订集 | ⏳ 已写进文档，等他过目 |
| D32 | CF 独立包依赖、不共用记忆、jmb 独立打包 | ✅（2026-10-28 他定的） |
| D33 | 桌宠渲染层内置 jmb，不用 Petdex 外接/sidecar | ✅ 方向已定，实现后做 |
| D34 | 写代码：任意路径 / 本会话授权 / 按轮次 undo | ✅（2026-10-28 他定的） |
| D35 | app 壳 v1 = Tkinter 聊天窗口 + 内置桌宠；PySide6 后换 | ✅ v1 已落地，待验收 |
| D36 | 每日清单投递面（Windows toast + app 内消息）+ 定时任务壳修复 | ✅ 已落地，待验收 |
| D37 | 每日清单北京活动栏：活动行 + GDG + lianpu 补充 | ✅ 已落地，待验收 |
| D38 | 上下文压缩：按模型预算 + 观察遮蔽 + LLM 结构化摘要 | ✅ 代码已落地，待重启验证 |
| D39 | SOUL 换成江慕白（英文压缩版 506 words，回复仍用中文） | ✅ 已落地，待重启生效 |
| D40 | app 壳 + pet 视觉 v2：圆角气泡聊天 + 薄荷状态桌宠 | ✅ 已落地，待重启验收 |
| D41 | 启动延迟：anthropic 延迟导入 | ✅ 已落地 |

> ⚠️ **日期标签更正**：本文件与 `docs/research/*.md` 里所有写着"2026-10-13"的条目，**实际都产出于 2026-10-26**（10-13 是我一开始误抄的日期，一路沿用到 D24）。内容和数字本身不受影响，但别拿"10-13"当时间线索引。新条目一律标 10-26。

---

## D1 主动性的归属 ✅（2026-10-13）

【决定】**驱动权归用户。** 他想学时陪他学，他想聊时陪他聊；agent 不发起学习、不主动出现、不根据情绪状态调整他的任务量。

【为什么】用户原话："也不是学习推进器，就是我想学习的时候陪我学，想聊天的时候聊天。"

【被否决的三个选项及理由】
- **A 学习推进器为主**（agent 管计划→提问→复盘记账）——被否。理由：不是他要的东西。他不要被推进，要被陪伴。
- **B 在场感为主**（agent 每天主动出现、跟踪连续性）——被否。理由：主动性不是他要的诉求。
- **C 状态交织**（根据当天状态调整学习量）——被否。理由同上，且这条另有一层独立问题：它需要"当前情绪"这个输入，而情绪判断是这类系统目前最不可靠的一环，放进控制回路会连带污染学习记录的可信度。
- 同时说明：我给出这三个选项的**框架本身是错的**——三项都默认"由 agent 驱动"，而他的答案把驱动权放在用户侧。这是选项结构缺陷，不是他挑了一格。

【本条消掉的东西（有实测数字）】
- **不需要常驻 gateway / heartbeat / 定时唤醒**。OpenClaw 文档默认心跳是每 30 分钟一整轮 = **48 次/天**，按实测 usage 结构折算是每月 $0.3–$0.7；这一格现在**归零**。
- **不需要为主动性引入一个进程**。Windows 侧"睡眠/开机后补偿执行"这类脏活不再是本项目职责。
- 我此前为路线二钉的**翻转条件 ①（若答 B/C 就改推 OpenClaw）不触发**。

【本条没有消掉的东西（关键，别误读）】
- **跨会话连续性仍然是核心诉求。**"像人"的来源是被记得，不是被打扰。实测依据：Generative Agents 的消融实验里去掉反思/规划各掉 TrueSkill 29.89→26.88→21.21；MATE（N=82）显示联结取决于披露深度对等而非最大热情。
- **"根据经历改变自己行为"这一条诉求仍然有效**，只是落点变了：不再是"它主动调整你的计划"，而是**它对你的了解、它的语气和判断在长**——记得你说过的事、记得你的偏好、记得上次聊到哪。这个落点更轻也更可测。

【依赖】无前置。

---

## D2 运行时的壳选哪条 ⏳ 重开（2026-10-13，被新证据推翻）

> **原决定"路线二：自研最小 loop"已被用户的一条事实推翻**："我大部分学习都是在 claude code 里，我学的内容大部分是计算机的，需要写代码。"
> 这不是他改主意，是我原方案的前提错了。以下为重开后的状态。

【新推荐（等确认）】**路线四：Claude Code 当宿主；陪伴体 = 一个专职目录 + 人格文件；Context Forge 当记忆与闸门层。** 自研对话循环不做。

【支持它的本机实测】
- Claude Code **2.1.296** 在 PATH（`/c/nvm4w/nodejs/claude`）。
- `~/.claude/agents/*.md` 已有 5 个 subagent 定义，frontmatter 实测支持 `name / description / tools / mcpServers / permissionMode / skills` ⇒ **人格确实有独立位置**。我原先否决路线三的理由之一"人格没有独立位置"**作废**。
- Context Forge 的钩子已挂在 CC 的 **`SessionStart` / `SessionEnd` / `PreCompact`** 三个点上（`~/.claude/settings.json` 的 hooks 段，命令 `python -m context_forge.hooks.claude_code`）。
- **采集回路是活的**：`~/.context-forge/queue.db` 里 `session_episodes` 28 行，全部 `host='claude_code'`，最近一条 `last_activity_at = 2026-10-13T13:00`（今天）。

【两个必须先修的实测坏消息】
1. **提炼没在跑**：`session_episodes` 的 state 是 `finalizing` 14 + `open` 14（**没有一个完成态**）；`finalization_operations` **0 行**；`jobs` **0 行**。库里 314 条记忆中只有 **6 条**带 `model`（`deepseek-v4-flash`），其余 308 条为空。
2. **反馈回路从没记过数**：`retrieval_events` **0 行**、`memory_applications` **0 行** ⇒ "根据经历改变行为"目前**一条数据都没有**，这条与选哪条路线无关，都得补。

【一条具体化的风险（原来是抽象说法，现在有证据）】
我原来否决路线三说的是"跨项目 memory 目录会互相污染"。实测更直接：`session_episodes.project` 里就有 **`C:\Users\15532\Desktop\platform-group-projects\platform-web\platform-web-main`**（他的公司主仓）以及 `Context Forge`、`qoder-harness`、`my-harness`。⇒ **陪伴体若共用这套采集，会收到他不打算给它看的内容。隔离必须在 D5/D6 里定成机制，不是"以后注意"。**

【待补的一个疑点】`queue.db` 报 **133.7 MB / 32,642 页 / 空闲页 0**，但我数到的所有表加起来约 130 行，且 `session_episodes` 只存 `transcript_path` 不存正文。⇒ **这 127 MB 是谁占的，本轮没查出来，不能解释成"转录内容在里面"。**

【D4 被这格替代】入口不再是"REPL / 精灵 / 网页"三选一，而是"你在 CC 里怎么切到它"。D5 / D6 / D7 的推荐仍然有效，但 D6 要多加一条：与工程仓库隔离的作用域边界。

---

## D2-旧 路线二的原决定（保留作历史，勿当现状）

【决定】**路线二：自研最小对话循环 + Context Forge 当记忆内核。** 用户原话："按你推荐，挺好的。"

【为什么】见 `options-3-routes.md` §4 的三条：陪伴/学习层反正都得自己写，借壳只买到四件事而其中三件实测很薄；Context Forge 是本项目最贵的一块已付成本，路线一里它要么闲置要么被替换要么要写宿主插件；实测算完钱不构成决策变量。
D1 定案后支撑更强：主动性需求被拆掉，我曾为路线二钉的翻转条件①（答 B/C 就改推 OpenClaw）不触发。

【已知短板 / 自报代价】自我改写闸口的正确性全靠我们自己守，没有别人的 issue 清单可依赖；Windows 侧定时唤醒/睡眠补偿要自己处理（本条因 D1 而暂不需要，但保留）。
【翻转条件】若第一版真出现一次"它学到了错东西"⇒ 立刻把闸门换成 OpenClaw 的实现（通过它的记忆槽把 Context Forge 插进去），而不是自己加固。

【被否决的两条及理由】
- 路线一（借宿主）：hermes 让 Context Forge 闲置、letta-code 替换掉它、OpenClaw 要为它写宿主插件（第三种工作量）；且要常驻 gateway + 升 Node 大版本（本机实测只有 22.22.0，OpenClaw 要 ≥24.16）。
- 路线三（寄生在现有 CLI）：陪伴记录会与工程笔记在同一个跨项目 memory 目录里互相污染，且人格没有独立位置。只作为路线二顺手可得的副产品保留。

【"当参考实现读、不当依赖"】hermes-agent 的 `SOUL.md`/`USER.md`/`MEMORY.md` 三件套、`_memory_write_origin` 来源标签、内置 cron、DeepSeek 端点适配 —— 作形状来源，不作依赖。

---

## D3 「学习」和「聊天」要不要做成两个模式 ✅（2026-10-13）

【决定】**不做模式系统。** 稳定前缀里只写一句"他随时可能在学和聊之间切换，按他此刻说的话决定怎么陪"，行为交给模型判断。

【为什么】①②两个选项都预设"存在两个模式"，而这个前提本身不成立——陪学和聊天在同一句话里是混着的；一个称职的伙伴看到能反问的话题自然会反问，这是模型本来就会的事，不需要状态机。

【被否决的两个选项及理由】
- ① 显式双入口：它永远知道自己在哪档，但每次切换都要动命令，而用户说的是"想…的时候"，那是随手的事。
- ② 单入口自动推断：最贴近原话，但推断错的表现是"我在聊天它突然考我"，这种误伤最烦人。

【已知短板 / 自报代价】如果将来要上间隔回收（到某时间隔地把学过的东西考一遍），那时需要的是**一份账本**（今天学了什么、哪些还没回收），不是**一个模式**。本决定不排斥账本，只是现在不做（见 D6）。

---

## D4' 入口贴在哪里 ✅（2026-10-13，取代原 D4"REPL/精灵/网页 三选一"）〔**已被下面 128 行的重开覆盖，此处仅留档**〕

【决定】**乙：一个随时能说话的独立窗口**，靠读他各处的记录来知道他在学什么；**不常驻任何工作/学习现场**。用户回复："乙"。

【为什么】与 D1（驱动权在他、不要主动出现）自洽；乙只需要"读记录"，不需要"接界面"。甲（贴 Obsidian/书本/浏览器）要为采集单独开发，成本大得多。
【已知短板】那本 PDF 和 Obsidian 里的学习痕迹，乙只能"事后读到"，不能"当场在场"。
【依赖】D8（读哪些源的隐私边界）须先定。

---

## D9 入口这个壳自己写还是复用现成客户端 ⏳

【背景：这是本项目第三次改路线，逐次原因留下，便于审计我是不是在摇摆】
1. 原推荐路线二（自研薄 loop）——基于"借壳只买到四件事，其中三件实测很薄"。
2. 改推荐路线四（CC 当宿主）——基于用户给的事实"我的学习都在 CC 里"。
3. 现改回推荐自研薄壳——基于本轮三条新证据（下列）。

【本轮新证据】
- **"学习在 CC 里"这个前提被他的数据打回**：学习词 : 交付词 = 1 : 7（5,037 : 35,134）；`怎么理解` 1 次、`复习` 1 次；Context Forge 的 314 条记忆里 `学习/课程/概念/笔记/练习/复习` **全 0 命中**。学习痕迹在 CC 之外（14.7 MB 的 JS 书 PDF、10-13 还在编辑的 Obsidian 库、浏览器 28,282 次查阅）。
- **CC 当宿主的三条硬伤**：每轮背约 **303 KB** 技能描述 + **48 个内置工具**；subagent 官方原话 "fresh, isolated context window"（不能当聊天载体）；auto-memory 按 cwd 分仓，**公司主仓下已存 9 条**，且 `claude purge` 会把转录和记忆一起删。
- **现成薄客户端接不上我们的端点**（实测）：`llm` 文档确认的只有 **OpenAI 兼容**端点 + `llm chat -t`/`-s` + SQLite 会话 + `llm -c` 续聊；`llm-anthropic` 在目录里存在但**文档无自定义 base URL / `-o` 端点选项**（NOT FOUND）；MCP 客户端只有第三方 `llm-mcp-client`（15★），无内建。而能接我们端点的现成件（Crush / OpenCode / Codex / CC）**都是编程 agent 的壳**，会把上面三条包袱重新引进来。

【当前推荐】**自己写这个薄壳**。理由：壳只需要 5 件事且**全部已实测通过**（`stop=tool_use` 工具循环、`system`、`stream`、`count_tokens` 可用、thinking 可丢弃）。写它不是造框架，是省掉 303 KB 的别人上下文。
【代价自报】会话存储、中断恢复、终端渲染这些琐事也得自己长出来。
【可推翻条件】若 `api.deepseek.com/v1`（OpenAI 兼容那条，**至今没实测**）实测可用，`llm` 立刻成为可用现成件，本条应改回复用 ⇒ 这是一格需要他点头的付费实测。

---

## 本轮新增的两条后端事实（免费实测，直接进设计）

- Context Forge 的 MCP server **当前只有 stdio**：`context_forge/mcp_server.py:292` `create_server().run(transport="stdio")`。
- 但它装的 `mcp 1.30.0` 里 **streamable-http 服务端实现存在**（`mcp/server/fastmcp/server.py` 命中 `streamable_http`），且 FastMCP **有 resource API**（`add_resource` `:542`、`@server.resource(...)` 示例 `:582-595`、`list_resources` `:364`）。
- ⇒ "人格与账本作为 MCP Resource 供出"和"改 HTTP 传输让多宿主共用一个后端"**在这台机器上有现成地基**，不是新造的轮子。未确认：`run()` 接受的 transport 确切取值（本机起一次即可验，零成本）。
- 另：Context Forge 的 MCP server **现在没有暴露任何 resource**（grep 零命中）⇒ 这一格是要写的。

---

## D4' 入口贴在哪里 ⏳ 重开（2026-10-13，被用户新需求清单作废）

> 原决定"乙：一个随时能说话的独立窗口"只活了一轮。用户随后给出四条需求：**桌面/手机端应用+桌宠、交互式会话+联网搜索、情感陪伴+用户给背景设定做文字演绎、学习同伴（陪写代码+总结归纳+联网搜索给信息）**。⇒ 入口不是一个窗口，是多入口 + 需要常驻服务。拆分与顺序见 `scope-decomposition.md`。
> 原【为什么】（与 D1 自洽、只需读记录不需接界面）仍然成立，但被新需求覆盖。⚠️ 特别注意：需求 4 的"**AI 陪同写代码**"把"要贴工作现场"这块又拉回来了 —— 我上一轮据他数据判"CC 是工作现场不是学习现场"没有错，但**他要的其中一种学习方式就发生在那个现场**，所以 SP4 不能砍，只能排后并解决 D8 的隔离冲突。

【已定的旧版本，留档】乙：独立窗口，靠读记录知道他在学什么，不常驻任何现场（用户回复"乙"，2026-10-13）。

---

## D10 需求清单作废，回到"一个类似机器人的 agent" ⏳（2026-10-13）

【决定】用户原话："推翻重来，我重新说下我的需求，我要做的就是一个类似机器人的agent，**不需要文字演绎**。我不知道如何描述我的需求，你引导我想一下。"
⇒ 上一轮那份四条需求清单（桌面/手机端+桌宠、会话+联网搜索、情感陪伴+文字演绎、学习同伴）**整体作废**，`scope-decomposition.md` 里的 SP1–SP5 拆分随之作废，其中 **SP5 文字演绎被明确撤掉**。
⇒ 用户要求切换模式：从"我给选项"改为"**我引导他把需求想清楚**"。因此 D1（主动性归属）、D4'（入口形态）都重新打开待问，不再当作已定。
【保留不变】D3（不做学习/聊天模式切换）暂时保留；六轮调研与实测的**事实**不作废（它们是证据不是决策），尤其：端点实测、本机能力清单、宿主选型的实测结论。
【状态】进入引导式追问，逐题重新定。

---

## D11 代码可见性用白名单机制 ✅（2026-10-13）

【决定】**丙：白名单 / 当场授权。** 默认任何代码仓都不可读；要读哪个仓由他逐次点头。用户原话："听你的，就用白名单机制保护隐私。"

【为什么】L1 要求"读我写的代码讲解"，L3 要求情感私密，两者方向相反。裁定成本不对称：**漏读**顶多帮不上忙，**误读**是把公司代码（实测 `platform-web-main` 63.5 MB / 29 个会话）变成它记忆里"你"的一部分，且记忆一旦落库不可逆。所以决定权留在他手上。

【被否决的两项及理由】
- 甲（只读个人仓）：如果他要学的东西就在公司项目里，它直接帮不上——而他 69 MB 的公司仓活跃度说明这种情况不少。
- 乙（全读 + 写入时自动分层）：技术上做得到（路径是现成判据，Context Forge 已有 `ApplicabilityScope` 与 projects/host 字段），但它把"什么算工作、什么算陪伴"交给了**我们写的自动规则**，判错一次即污染。

【顺带的收益】"这次允许读 X"本身就成了一条可记的事实——它能长出"你一般在什么场景下需要我读代码"的认知，这正好是他最初要的"根据经历改变行为"的一个廉价来源。

【已知短板】摩擦：每次开工要多说一句/多点一次。折中方案（默认读个人仓 + 公司仓临时授权）他**没有选**，所以一期不做默认放行。

---

## D12 多端与功能分层 ✅（2026-10-13，附一处措辞修正）

【用户原话】"如果项目我自己体验良好，后续可能上线，所以得留口子。需要同一个后端，但是手机端的app和电脑端的功能做区分就好了。目前先把看代码的功能只做到电脑端，手机端只支持聊天。这么合理不合理"

【认定的三条】
1. **同一个后端**：✅ 合理。它是"两个设备上是同一个它"的技术前提。
2. **功能分层：读代码只在电脑端，手机端只聊天**：✅ 合理，且成本低。依据：需要读代码的时刻天然发生在写代码的地方（电脑）；手机侧问的从来是"它之前读过的东西"，那只依赖记忆，不依赖实时读盘。
3. **"为上线留口子"**：⚠️ **措辞要改**——这条把**多端（devices）**和**多用户（tenants）**混成一件事。多端是**一期就真实存在**的需求；多用户目前只是"可能"。为"可能"预付多用户成本是最贵的错法。

【一个实测到的好消息：多用户的口子他自己已经留了】
- `context_forge/memory_models.py:13` `DEFAULT_OWNER = 'local'` ⇒ 是**默认值**，不是硬编码常量。
- `owner: str = DEFAULT_OWNER` 出现在写入与检索签名上：`memory.py:604`、`:1727`、`:1744`、`:2025`，以及 `memory_import.py:82`、`:161`。
- 边界判定**已经按 owner 走**：`memory.py:305` `def boundary_visible(view, *, owner, ctx)`，在 `:1875` 被调用。
- 还有 `privacy: Literal['shared','private'] = 'shared'`（`memory_models.py:42`）与 `MemorySpace(owner=owner, privacy=privacy)`（`:209`）、`BoundarySplit`（`:201`）。
⇒ **"给别人各养一只"在他的存储层已经能表达**；要做的只是在 API 上把 owner 传出来。所以"留口子"在这一层几乎是零成本——也正因此，为它现在就搭多租户是过度设计。

【"上线"真正贵的四件事，都不是代码结构，留口子绕不过去】
1. **谁付模型钱**：实测算过单人 **每月 $0.3–0.7**（峰谷两档，按 48 次心跳/天 + 每天 50 轮聊天的形状）。那是**一个人**。给别人用 = 他的 DeepSeek key 替所有人付费。⇒ 这是商业决定，不是技术决定。
2. **陪伴类产品的合规义务**：加州 **SB 243 Companion Chatbot Protocols Act** 要求运营方维护"防止产出自杀/自伤内容"的协议、给"清晰显眼的非人类告知"、对未成年人每三小时提示（律所摘要，SECONDARY）。意大利数据保护机构处罚过 Replika（EDPB 通稿，一手）。另有纵向研究把陪伴使用与孤独/抑郁/自杀意念相关语言的增加关联起来（arXiv 2509.22505，一手摘要）。
3. **"它会变"一旦对外就是别人的朋友**：Harvard / Nature Human Behaviour 实测——模型更新被用户体验为人际断裂，Replika 更新后负面语言帖 **从 13% 升到 38%**。他的核心卖点正是"根据经历改变行为" ⇒ 上线版**必须**有版本、回滚、用户否决权，这不是可选装饰。
4. **私密性的形状会变**：D11 白名单防的是"公司代码进记忆"；多人版要防的是"A 的记忆漏给 B"。同一个 owner/privacy 机制，但一旦上线，泄露面从假设变成真实。

【一期真正该留的三个口子（成本几乎为零）】
1. 后端对外是 **HTTP/SSE** 而不是进程内函数调用——这条本来就有，因为一期就有两个设备。（⚠️ 2026-10-27 评审更正：一期没有 HTTP 服务端；此口子落地 = **对话循环与入口解耦**，二期包 HTTP 时零改动。）
2. API 签名里带 **owner** 与 **surface**（不传就用默认 `'local'` / 默认入口）。
3. **"能不能读代码"做成设备能力声明**，不要写成 `if 手机 then 禁`。

【一期明确不留】鉴权系统、多租户隔离层、配额计费、后台管理。等真有第二个用户再说。

【待确认】他说的"上线"是哪一种：甲 别人各养一只 / 乙 别人共用他这一只 / 丙 只是"别把代码写死成单用户"。

---

## D13 "上线"的形状定为甲：多用户，每人各养一只 ✅（推迟到后续迭代，一期只留口子）

【用户原话】"我需要做成多用户，别人各养一只自己的，但这个是后续迭代需要做的，现在留口子就行"

⇒ 上一题的三选一选了**甲**，但明确**不在一期做**。所以下面这张"口子清单"就是"留口子"的具体含义——**不是抽象的"设计得通用一点"**。

### 一期必须留的六个口子（现在几乎免费，以后要迁移）

1. **物理隔离，而不是查询时过滤**。Context Forge 现在的边界判定是查询时按 owner 过滤（`memory.py:305` `boundary_visible(view, *, owner, ctx)`，`:1875` 调用）。对**情感陪伴数据**来说，"一个 where 条件写错 = 跨用户泄露"。⇒ 一期就用 **每个 owner 一套独立存储**（一个 db 文件 + 一棵目录树），owner 只有一个值时成本为零。
2. **所有新产物都带 owner，不只是数据库行**。我们要新建的东西里有一堆是**文件**：人格文件、学习账本、会话 JSONL、角色/场景设定、白名单授权。⇒ 目录形状现在就写成 `spaces/<owner>/…`，将来不是迁移而是加一行配置。
3. **白名单（D11）必须是"带 owner 的记录"，不是配置文件里的一行**。配置文件形状在多用户下要拆成表。而做成记录还顺带白拿两个好处：每次授权本身成了可学习的历史，也天然可审计。
4. **`surface`（哪个入口）进 API，能力差异靠 surface 声明**。一期就要（两个设备）；顺手让"哪些能力属于哪个入口"变成数据而不是 `if 手机`。
5. **模型 key 只留在后端，客户端永远不碰**。这条不是洁癖：浏览器/客户端直连要 CORS，Anthropic 为此造的 flag 字面就叫 `anthropic-dangerous-direct-browser-access`（名字就是警告），而 DeepSeek 那个端点是否回 CORS 头我们**没验到**。将来接第二个用户时，若 key 在客户端，等于要么泄 key 要么替他付钱。
6. **每次调用记 (owner, surface, input/output/cache_read tokens)**。端点的 usage 里这些字段实测都有，写进会话日志就是**免费的按用户计量**。将来做配额直接读它；没有它，上线第一天就得补一层计账。

### 一条容易被忽略的坑：**一期不要写 `if owner == 'local'` 的特权分支**

他自己在一期既是用户也是开发者，默认 owner 就是 `'local'`（`memory_models.py:13`）。如果一期让"local"承载任何特权（比如"只有 local 能读公司仓"、"只有 local 的私密不可见"），那 v2 第一个真用户进来时这些特权要么变成**权限漏洞**要么变成**迁移工作**。⇒ 特权只通过 **capability / 配置**表达，不通过"你是谁"表达。

### 一期明确不做（甲需要的，但不是现在）

鉴权与登录、多租户路由、配额与计费界面、后台管理、内容安全审核流水线、以及**"谁付模型钱"这个商业决定**。
理由：这些没有一件能靠"留口子"提前完成，都得等第一个真实第二个用户出现时才设计得对——现在做只会做猜错的那版。

---

## D14 L1（学习循环）的交互流程定形 ✅（2026-10-13）

【用户给的实际流程，原话整理】

1. 他："想搞懂 LangGraph 的检查点到底怎么存东西。"
2. 它：**自己去 websearch，根据官方文档回答**；**如果需要实际代码，向他请求授权**。
3. 它：回答问题。
4. 他："我写代码实操一下，你帮我看看代码。"
5. 它：看代码。
6. 他："行，我学会了，形成文档落到 xxx。"
7. 它：**写文档**。

【由这条流程定下的四件事】

- **先答，再要代码**：它不是一上来就要读他的仓。它先据公开资料回答，**只有它判断"这个回答需要他的实际代码"时**才发起授权请求 ⇒ 白名单（D11）不是一条静态规则，而是一个**由它主动发起、由他批准的动作**。这比我上一轮写的更精确。
- **"看代码"发生在两个时点**：① 它需要真实上下文时（它开口要）；② **他写完之后再让它看**（"你帮我看看代码"）。
- **学习的一等产出物是一份文档**，不是记忆条目。收尾那句"形成文档落到 xxx"是显式指令 ⇒ 文档是**他要求才写**的，不是每轮自动生成。
- **讲解的锚点是他的代码**（上一轮定的），这一轮的"你帮我看看"说明他也接受**轻度的检查**，但落点是"看完说情况"，不是"判断你这样写是错的"。我上一轮把"解释 vs 纠错"做成二选一，**这个区分过硬**——实际两者都要，差别在**时点**（他写完之后再来看），不在有没有。

【⚠️ 我自己的两处更正，带原因链】

1. **"搜索 API 降级为可选"这条错了，现撤回。** 上一轮我根据"翻译官网资料 = 抓他给的链接"推断出不需要搜索。他的流程里第 2 步是**它自己去 websearch 找官方文档** ⇒ **联网搜索恢复为一期必需项**。而那一轮负责搜索选型的调研子代理中途失败未回 ⇒ **这一格现在是真空**，且它在关键路径上。
2. 上一轮我说"它不先讲定义，先管你要代码或链接"——**错**，他要么给链接要么让它自己搜，顺序是"先答后取上下文"。

---

## D15 学习文档的落点 = Obsidian 主库 ✅（2026-10-13）

【决定】**甲：`Documents\Obsidian Vault`。** 用户回复："甲"。
L1 收尾"形成文档落到 xxx"的那个 xxx 就是这里。

【为什么】那是唯一一个**他本人在往里写**的地方：22 篇 / 385 KB，分类是"前端知识 6 / ai coding 相关 3 / 工作经验 5 / 服务器相关 2 / agent 2 / blog 1"，**最近一次编辑 2026-10-13**。对照被否掉的候选：`Desktop\konwledge_base` 那 567 篇里 549 是 Context Forge 文档、17 是 code-mentor 文档 ⇒ 那是产品文档不是他的知识；`jmb/docs/` 是项目文档位，不是知识位。

【被否决项的理由】
- 乙（`konwledge_base`）：性质不对，会把他的学习心得倒进产品文档堆里。
- 丙（`jmb/docs/`）：那是项目产物目录，他要的产出物是"我以后还会回来看"的东西。
- 丁（修那条死配置）：**没有否，是并进甲** —— `~/.claude/knowledge/config.json` 现在写的是 `D:/Obsidian base/personal knowledge base`，而这台机器只有 C: 盘 ⇒ 他早就试过一条知识沉淀通路，死在一个不存在的路径上。改指向甲的库即可，**不再新建第五个库**。

【已知代价与约束】
- Obsidian 是别人 App 的目录 ⇒ 写入要守它的约定（文件夹组织、`[[wikilink]]` 相对链接、别破坏它的索引）。
- 这个路径**必须是 per-owner**，正好落进 D13 第 2 条口子：`spaces/<owner>/…`，不能把 vault 路径写死成常量。
- ⚠️ 一条未验风险：他的 vault 里已有内容是他手写的 ⇒ **它写文档的规则（命名、放哪个子目录、要不要双链）必须先看现有 22 篇怎么组织的**，否则会长出一个混排的库。这一格留到设计阶段实地读那个库再定。

## D16 人格数量：只有一个，不换皮（按三次无异议锁定）⏳

【内容】他撤掉了"文字演绎"，但要求"它此时扮演我的朋友/伴侣"。我连续三次给出同一条读法——**撤掉的是"给他一个虚构设定去演"，留下的是"它以自己的身份当朋友"**——他未反驳。⇒ 按假设定案写入规格：**人格文件只有一份，L1/L2/L3 是同一个它的三种介入方式，不换人格、不换称呼、不换语气基线。**
【为什么需要单独记】这是最容易被实现悄悄改掉的一条（"给每个场景配一个 system prompt"看起来更工程化），一旦那样做就变成三个聊天机器人，正是他说的"类似机器人的 agent"的反面。
【状态】⏳ 待他在规格评审时最终点头。

---

## D17 一期不做手机端 ✅（2026-10-13）

【决定】**丙：一期只在桌面。** 用户回复："选丙，一期先不做手机端"。

【为什么】他选了"手机只聊天"之后，后端必须在他拿手机的时刻活着；而实测他的机器活动是 **02:00–08:59 全空、19 点后从峰值 647 掉到 121** ⇒ 夜里那台机器大概率是关着的。剩下的两条路（甲：让电脑常开 + 手机装 Tailscale；乙：后端上云）都有真实代价，而乙与 D11 白名单的动机正面相反（一个记着情绪、代码习惯、学习卡点的库离开本机）。
⇒ 决定不做的底气来自 **D13 第 1 条口子**：一期就把后端做成 **HTTP/SSE**，所以"手机什么时候接进来"只是网络问题，不是架构返工。等他自己验证"我到底会不会在晚上找它说话"，再在甲乙之间挑。
（⚠️ **2026-10-27 评审更正**："一期后端已是 HTTP"不成立——一期对话只有终端 REPL、无常驻服务端。口子的真实落地形状 = **对话循环写成与入口无关的函数**，二期接手机 = 包一层薄 HTTP + 网络，仍不是架构返工。见 spec §4 修订。）

【明说的代价】**"手机端"这条需求在一期没有可验收的东西**，它退回"以后再说"。他上一轮对多用户用的是同一个办法。

---

## D7 学习动作一期做哪几件 —— ⛔ 被 D14 取代（2026-10-13）

我原推荐的两件是"开场反问上次的错题 + 收尾一句话入账本"。**他给的实际流程（D14）把这两件都改了**：
- 开场不是反问，是**他提题 → 它自己去搜官方文档回答**；
- 收尾不是"记一笔卡在哪"，是**他要求时写一份文档落到 Obsidian（D15）**。
⇒ 本条作废，不再作为需求。**"开场反问"作为复习器的一部分，本就在 D14 之前被他明确推迟过**（"复习器暂时不需要"），现在彻底移出范围。

## D5（记哪四类）：⏳ 仍未定 ‖ D6（它能改哪些文件）：✅ 已由 D21 定案为乙

这两格原本绑在一屏里问他，他一路没回。**D6 后来由 D21 单独回答了（选乙）**，所以这里只剩 **D5** 未决。
D5 当时的四类草案：① 关于你的事实 ② 学习账本 ③ 相处痕迹（只记他原话级事实，不推断情绪数值）④ 逐字转录（只当原料，不进长期召回）。
⚠️ **D14/D15 之后这条必须重问一次**：原来叫"学习账本"的那个东西已经变形——学习的一等产出物现在是**落到 Obsidian 的文档**（他要求才写），"账本"是否还需要作为独立一类、还是并进文档，未定。

⚠️ **更新（2026-10-27，评审后）**：`docs/spec-architecture.md` §3.1 已按现有决策推出 **v0 —— 活着的五类**：关于你的事实 / 学习进度 / 对相处的总结 / 兴趣 / 逐字转录；"学习账本"并进了"学习进度"（第 6 行那行已取消）⇒ **实现照 spec §3.1 走**。本条仍未拿到他的回答，他点头后改为 ✅。配套："你确认才生效"的落地机制在 spec §3.2，实现步骤在 `implementation-plan.md` Phase 5。

---

## D18 L2（聊今天的新东西）的形状 ✅（2026-10-13）

【决定】**列清单，不发表观点。** 用户原话（对 A/B 二选一选了 A）："**直接列出来项目名称，地址，大致介绍，我感兴趣的话我会详细追问**"

【条目字段就三项】项目名 · 地址 · 大致介绍。
【被否掉的东西及理由】我推荐的是 B（它挑一个 + 给理由 + 先问要不要去读）。**驳回。** ⇒ "它替我判断我会喜欢什么"**不是需求**；"要不要先去读一下那个项目"**也不是需求**，他要读会自己追问。
【我又一次猜错，记下来】这是我这轮第三次把"更像人"理解成"更有主张"。他的取向始终一致：**决定权在他**（D1 不主动出现 → D11 代码逐个授权 → 本条不替他筛口味）。所以"像人"对他来说不是有主见，是**记得住、跟得上、不多管**。这条要写进人格文件，否则实现的人会照着"聪明助手"的直觉把它做成长舌的。

【一条省事的推论】他会"详细追问" ⇒ 那时它要能读那个项目的 README / 首页 ⇒ **这和 L1 第 2 步"抓一个已知的官方文档页"是同一条能力**，不用做两件事。

【未定】清单从哪来、多久更新一次、一次列几条 —— 这三条属于实现细节，等后台那路搜索/榜单调研回来一起定。

---

## D19 L2 会留下"兴趣"这一条记录 ✅（2026-10-13）

【决定】**要**。用户回复："要"。
⇒ 聊完榜单之后，它记下"你对 X 项目表过兴趣"。以后他学到相关内容时它能提一句"你之前看过这个"。
⇒ L2 不是无状态播报：它有一类产出物，就是**他的兴趣**。
【边界】只记"他对什么感兴趣"这一件事实，**不由此推断他的水平、性格或情绪**。
【L2 仍未定】清单来源、更新频率、一次列几条 —— 等后台那路搜索/榜单调研回来定。

---

## D20 联网能力的选型 ✅（2026-10-13，后台调研补回）

【结论】**不用选型、不用第三方 key、不用自建 SearXNG。** DeepSeek 自己就有 Search 和 Fetch，用的就是他已经在付的那份凭据。

【实测到的接口（官方 guides/search 页今日取）】
- 搜索：`POST https://api.deepseek.com/v1/tools/search`；参数 `query`（1–128 字符）、`count`（1–50，默认 10）、`need_content`、`ori_question`、`localization`；支持操作符 `site:` / `-site:` / `"..."` / `lang:` / `after:` / `before:`；返回 `title, url, snippet, summary, content, site_name, rerank_score, authority, date`。
- 抓正文：`POST https://api.deepseek.com/v1/tools/fetch`，`url` ≤8192 字符，**返回 Markdown 正文**；402 余额不足 / 403 站点策略拦截 / 404 无可用正文 / 429 限流。
- 计费：**每个成功请求 $0.75/1000**（中文页写"5元"），**失败、空结果、超时不计费**，`count` 不影响价格。限额 Search 100 QPS、Fetch 25 QPS（账号级，Fetch 还有按域名 QPS）。鉴权与 DeepSeek API 同一个 bearer。**注意 base 是 `api.deepseek.com`，不是 `/anthropic`。**

【⚠️ 更正我自己：我上一轮的推断错了，而且是往好处错】
我之前依据兼容表里"`search_result` 块 Not Supported"推出"Anthropic 的服务端 web search 在我们端点不可用"。**官方 `guides/anthropic_api` 页今日实读：`type="server_tool_use"` = Supported，`type="web_search_tool_result"` = Supported**（`search_result` 与 `document` 才是不支持，`citations` 被忽略）。而 `quick_start/agent_integrations/claude_code` 原话："**The DeepSeek API natively supports the Web Search feature in Claude Code**"。
⇒ 所以他现在在 Claude Code / Qoder 里用的搜索，就是这个能力。**免费窗口到 2026-11-01 00:00（北京时间）为止**，之后按每请求计费——离现在 6 天。

【L1/L2 分别要的那一半，答案不一样】
- **L1「把官方文档讲成人话」= 可能根本不需要搜索。** `llms.txt` 是真的：今日实测 `docs.github.com/llms.txt`（28 KB，`text/markdown`）存在，`docs.anthropic.com`、`docs.langchain.com`、`mintlify.com/docs`、`sentry.io` 也有；GitHub 文档还提供 `docs.github.com/api/search/v1` + `/api/article/body` 直接返回 Markdown、**无需 key**。规范在 `llmstxt.org`（v2），原文称"OpenAI、Anthropic、Gemini 都发了自己的 llms.txt"。**但 `api-docs.deepseek.com` 没有**（返回 SPA 的 HTML）。
- **L2「今天有什么新东西」= 这才需要发现 URL。** 用上面的 Search（`site:` / `after:` 正好用来查"最近新建的高星仓"）。

【一条他机器特有的硬约束，实测过】从这台 PC 直接出网：**google / duckduckgo（三个域名全试）/ brave / startpage / r.jina.ai / github.com 的 HTML 页面 全部超时**；**通的**：`cn.bing.com`（今天返回 200 且能解析出结果块）、mojeek 200、ecosia 301、yandex 302、`api.github.com` 200、`star-history.com` 200、搜狗微信 200。
⇒ 所以"自建 SearXNG / 装 `ddgs`（MIT，3,031★，昨天还在推）"这类零成本方案，**在他网络上只剩 bing/mojeek/yandex/wikipedia 几条腿能用**；`Bing Search API` 官方已 **2025-08-11 退役**（微软生命周期页）。⇒ **第三方搜索这条路在本机是半死的，DeepSeek Search 反而是最通的那条。**

【L2 的 GitHub 榜单：没有官方 API，已正面查证】`docs.github.com/llms.txt` 与 412 KB 的 REST 文档里 "trending" **0 命中**。文档承认的做法是 Search API：`api.github.com/search/repositories?q=created:>…&stars:>…&sort=stars`，认证后搜索 **30 次/分钟**（未认证 10/分钟），REST 未认证 60/小时、认证 5,000/小时。
⇒ 加上 "`github.com/trending` 的 HTML 从这台机器打不开"这一条 ⇒ **榜单不能靠爬 trending 页**，要用 Search API 造一个"最近新建、星数上升"的查询；他自己的 `SkillAbout` 已经在用 `star-history.com` + `api.github.com/repos/{repo}` 这个组合，正好是能接的形状。

【一期据此定的三条规则】
1. **搜索/抓取只走 DeepSeek 的两个 tools 接口**，不引第三方供应商，不自建 SearXNG。
2. **工具别多**：照 Anthropic 官方《writing tools for agents》的原话——"**More tools don't always lead to better outcomes**"，常见错误是"tools that merely wrap existing … API endpoints"；且**工具返回必须做截断/分页**（他们自己在 Claude Code 里把工具响应限到 25,000 token）。⇒ 我们对外只给 `search` 和 `fetch` 两个工具，`count` 给小值、正文带截断。
3. **`citations` 在我们端点被忽略** ⇒ 引用要自己写进正文文本，别指望结构化字段（与已实测的 `tool_result.is_error` 被忽略是同一类问题）。

---

## D21 自我改写的边界 = 乙 ✅（2026-10-13）

【决定】**乙：它能写"关于你的事"+"它对你们相处的总结"；性格基线文件它自己不许碰。** 用户回复："乙"。

三档的定义：甲 = 只写关于你的事；乙 = 再加相处总结（例："你晚上不想被问代码"、"你学新东西喜欢先跑起来再看解释"）；丙 = 再加"自己改自己做事的方法"（自学出流程）。

【为什么乙】你最开始的诉求是"**它会根据经历改变自己的行为**"：甲做不到那句话；丙风险最高（调研记录里"学到错误一课"与"agent 把自己指令改坏"都发生在丙档，Letta 生产上报告过两次 agent 删掉自己）；乙正好是那句话**最小可信的实现**——变的是它对你们俩的了解，不变的是它跟你说话的样子。

【被否决的两档】甲（否掉你原始诉求的一半）；丙（一期不做，**留接口不留实现**：它要用的话，得先有"改动前存档 + 可撤销 + 可见告知"三件套，这三件套本身就在下面这条规则里）。

【一条不可选的规则：它的每次自我改写都必须可见、带时间线、能撤销】
依据是实测，不是偏好：Replika 一次更新之后，用户帖子里负面语言占比**从 13% 升到 38%**，ChatGPT 那次**从 20% 升到 33%**——人把模型更新体验成"我朋友变了"；另有论文发现**认为变化可逆的用户会陷入"修复循环"**。
⇒ 落到设计上就是三件现成形状：① 写入带**来源标签**（他自己写的 / 它总结的 / 后台复盘写的）；② 改前存**旧版本副本**，可一键回退；③ 改完**不可压制的告知**（"我把这条改了，说 undo 可撤"）。这三件在他现有资产里都有先例：Context Forge 已有 `actor` 五值 + `memory_versions` + 只追加的 `memory_events`（实测），缺的是"改前存副本 + 告知"这条回路。

【⚠️ 一处必须一起改的代码】D21 成立之后，Context Forge 的 `MemoryLifecycle.publish` 会把模型写的记忆**无人值守置为 active**（`memory_lifecycle.py:286`，实测）——"它自己写的"和"你确认过的"在生效层面目前没区别。这条要在设计里定成显式规则。

⚠️ **但只改这一行不够（2026-10-27 评审实测）**：召回只认 `status IN ('active','conflicted')`（`memory.py:1784`/`:1792`/`:1855`），而 Context Forge 自带的提审回路**只对高危 rule 开**（`risk.py:62`）⇒ 普通事实若只是改成"保持 candidate"，会**永远停在 candidate、永远召不回来**，而且一条验收也测不出来。落地机制（提审 → 你在终端确认 → 提升为 active → 才进召回）见 `spec-architecture.md` §3.2 与 `implementation-plan.md` Phase 5。

---

## D22 L3 的记忆使用方式 = 乙 ✅（2026-10-13）

【决定】**乙：它可以主动提一件以前的事**，像朋友那样（"你昨天说那个 checkpoint 还没搞明白"）。用户回复："乙"。
【附带条件（我当时说清的）】选乙之后，"**什么时候不许提**"必须写成人格文件里的显式规则，不能交给它临场判断——因为"提多了/在你正烦的时候提工作"会从"被记得"变成"被监控"。
【状态】规则的具体条目由我起草，标着"我定的、待他改"。

---

## D23 新增硬性规矩：每天 09:00 跑一次清单，主动交给他 ⚠️（2026-10-13）**这条推翻了 D1**

【用户原话】"还有一个，**ai要主动找我聊天**。硬性规矩是**每天九点跑一遍 github 榜单，技术热点，ai 相关技术相关的线下会议。然后列给我。**"

⇒ **D1（驱动权完全归用户、不要主动出现）被这条覆盖。** 他不需要铺垫理由，按新证据重开即可。
⇒ 但注意这条本身是**一个定时任务**，不是"情感陪伴的主动性"：有固定时间、固定内容、固定产出（列给他）。所以"主动"这个词在这条里指的是**它先开口交东西**，不等于"它随时想找话头"。

【三个数据源的可信度差别很大，别当一件事做】
- **GitHub 榜单**：✅ 有形状。官方**没有 trending API**（正面查证：`docs.github.com/llms.txt` 与 412 KB REST 文档里 "trending" 0 命中），可用的是 `api.github.com/search/repositories?q=created:>…&stars:>…&sort=stars`（认证 30 次/分钟）。且 **`github.com/trending` 的 HTML 从这台机器打不开**（实测超时）⇒ 不能爬 trending 页。
- **技术热点**：✅ 他本机已有现成的。`Desktop\xj\SkillAbout` 的 `build_digest.py` 抓 `star-history.com`（实测可达 200）并用 `api.github.com/repos/{repo}` 取事实；`domestic_search.py` 抓搜狗 + `cn.bing.com`（**可达**）+ `html.duckduckgo.com`（**当前在这台机器上超时**）。DeepSeek 的 `/v1/tools/search` 也能补。
- **AI 相关线下会议**：⛔ **我没有任何验过的数据源。** 前面七轮调研和那路搜索选型都没覆盖这一项，城市/主办站/API 情况一概不知。**不许写进一期规格当成已解决**，要单独查一轮，或者一期先由他手工贴链接。

【一条真实的作息冲突，得他拍】
定时在 09:00，但实测他的机器活动是 **02:00–08:59 完全为空**，09 点这一小时才第一次出现（369 条提问，10 点 525 条）。
⇒ 也就是说 **09:00 那一刻电脑很可能还没开机**。`schtasks`（微软文档实测有 `/sc DAILY /st 09:00 /it`）和 Qoder 自带的 `qoder_cron`（实测 schedule 支持 `at`/`every`/`cron` + IANA `timeZone`）在**机器关机时都不会跑**；关机错过的任务要么不补，要么靠"错过后运行"策略补，而这需要显式配置。
⇒ 两条走法：**(甲)** 坚持 09:00 定时 ⇒ 电脑那时刻必须开着，否则那天就没有清单；**(乙)** 把触发改成"**你每天早上第一次打开电脑那一下跑一次，每天只跑一次**" ⇒ 时间不精确，但清单一定在你面前。这是事件触发通常优于时间触发的典型例子。

【桌宠第一次真的有用上】清单跑完 ⇒ `petdex_show_bubble` 冒一句"今天榜单好了"（实测 Petdex Desktop 有 `/bubble` 与三个 MCP 工具，Windows 有原生 exe）。这是"主动找他"最低摩擦的形状。

---

## D24 日报时间改 10:00，主动性范围 = 甲 ✅（2026-10-13）

【用户原话】"那就十点.....，websearch这块，你去看deepseek如何做的，我觉得没那么难。**第一期先做甲**"

【三条定案】
1. **日报时间：10:00**（覆盖 D23 里的 09:00）。他的直觉被我的实测支持：本地小时分布 **09→382、10→560、11→520**（`~/.claude/history.jsonl` 本轮取到 **5,373 条带时间戳记录**，注意与上一轮子代理报的 5,152 不同口径：**我这次是按行解析成功数计，口径变了，以本次为准**）。
2. **主动性范围 = 甲**：一期只有这份日报会主动开口，**不做"平时它自己想找话头"**。（我推荐的理由他接受：乙没有判据、容易变骚扰，且会废掉 D22 那条"什么时候不许提"的规则。）
3. **websearch 走 DeepSeek 的服务端搜索**，见下面 D25 的更正。

【一条残留风险，我自己按默认值写，他要改就说】
**周六 10 点从来没开过机**：按星期几拆 10 点那一格 = 周一 110 / 周二 58 / 周三 100 / 周四 161 / 周五 105 / **周六 0** / 周日 26；87 个有活动日里，10 点当小时有提问的只有 64 天。
⇒ ~~**默认写法：错过就补跑**（当天第一次开机时补上今天那份，每天仍只跑一次）~~ **⛔ 已被 D30 推翻（2026-10-27 他明确要求去掉）**：不做补跑，也不配开机触发器。**代价：10:00 时机器关着 ⇒ 那天没有清单。**

---

## D25 websearch 的实现方式：服务端搜索，不用自己造 ✅（2026-10-13，我自己取的一手页）

【结论】**他的判断对：没那么难。** DeepSeek 在它的 Anthropic 兼容端点上**原生支持 Web Search 工具**——搜索由 DeepSeek 服务端执行，结果以 Anthropic 形态的内容块回给你。⇒ **一期不需要接第三方搜索供应商，不需要自建 SearXNG，不需要写 `/v1/tools/search` 那套原始 JSON 调用。**

【本轮我自己 fetch 到的兼容表原文（`guides/anthropic_api`）】
```
system: Fully Supported          stream: Fully Supported
server_tool_use: Supported       web_search_tool_result: Supported
search_result: Not Supported     document: Not Supported
thinking: Supported              redacted_thinking: Not Supported
citations: Ignored               tool_result.is_error: Ignored
anthropic-version: Ignored       anthropic-beta: Ignored for /messages
cache_control: Ignored
```
⇒ 要处理的是 **`web_search_tool_result`** 这个块类型（Supported），而 `search_result` 那个块确实不支持——我上一轮把两者混成一句话说了"服务端搜索不可用"，**那是错的，本条更正**。
⇒ `citations: Ignored` ⇒ 引用必须自己写进正文文本（与 D20 第 3 条规则一致）。

【Claude Code 集成页（`quick_start/agent_integrations/claude_code`）本轮实读】
- 需要的环境变量就是他现在这三个：`ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_MODEL`。
- 搜索是"Web Search tool"，执行方"through the API provided by DeepSeek"。
- 费用原话："**additional model token costs will be incurred**"。
- 支持模型：`deepseek-flash` / `deepseek-v4-pro`。
- **免费期：NOT FOUND**。⚠️ 上一轮子代理报过一个"计费从 2026-11-01 00:00 北京时间开始、之前免费"的说法，**我这次在同一主题的两个官方页上都没取到这个日期，也不在这张表里 ⇒ 那条不采信，除非能从计费页重新取到。**

【实测完成（本轮，`scripts/probe_websearch.py`，用户点头后跑的 5 次真实调用）】

**① 声明字符串钉死了**：`{"type": "web_search_20250305", "name": "web_search"}` ⇒ HTTP 200，真的查了。
- **`name` 是必填**：只给 `type` 不给 `name` ⇒ **HTTP 422** `tools[0]: missing field name`。
- **beta 头可有可无**：带 `anthropic-beta: web-search-2025-03-05` 同样 200，行为一致 ⇒ 与已实测的"beta 被忽略"吻合。**规格里写：不带头。**

**② 搜索在服务端跑完，我们不用写工具循环**（一次请求内出结果）：
- A 组块序列：`thinking → server_tool_use → web_search_tool_result → thinking → server_tool_use → web_search_tool_result → thinking → server_tool_use → web_search_tool_result → thinking → text`，`stop_reason=end_turn`。
- usage 里明写 **`server_tool_use: {"web_search_requests": 3}`** —— 一个"mcp 包最新版是多少"的问题，它**自己查了三轮**才答。

**③ ⚠️ 意外发现（直接改 L1 设计）：搜索结果里没有正文。**
每条结果的键是 **`['encrypted_content', 'page_age', 'title', 'type', 'url']`**，**没有 `content` / `description`**（我脚本取了，是空串）。
⇒ 搜索只给"链接 + 标题 + 时间戳 + 一份加密内容"。⇒ **L1 的"把官网资料讲成人话"不能只靠 Web Search**：拿到 URL 之后仍然要**真的把那一页抓下来**。所以一期需要两条能力，不是一条：
  - 发现 URL / 拿到"有没有这东西"的答案 ⇒ **服务端 Web Search**（本轮实测通）。
  - 读正文 ⇒ **另抓**：`llms.txt`（实测 docs.github.com / docs.anthropic.com / docs.langchain.com 有）或 DeepSeek 的 `POST /v1/tools/fetch`（官方称返回 Markdown 正文，**本轮未实测**）。

**④ ⚠️ 成本与上下文膨胀是真风险**（同一次运行内的数字）：
- A 组（搜 3 轮）：**`input_tokens=22447`**，`cache_read=13568`，`output=569`。
- C 组（搜 2 轮）：`input=10437`，`cache_read=512`，`output=610`。
- D 组（**不声明工具**做对照）：`input=52`，`output=512`，`stop_reason=max_tokens`，块只有 `['thinking']` —— 它光想就写满 512，**一个字也没查**。
⇒ 两点结论：**(a)** 默认 `count=10` 条结果会整批塞回上下文，一个简单问题就能吃掉 2 万 input token ⇒ **规格必须限轮数和条数**（正对 Anthropic 官方《writing tools for agents》那句"对可能大量占上下文的工具响应做截断/分页"，他们自己在 Claude Code 里把工具响应限到 25,000 token）；**(b)** 不声明工具时它会凭记忆瞎答 ⇒ 学习场景必须默认带上搜索，否则他拿到的可能是过期答案。

**⑤ 一条配置不一致，本轮新发现，尚未查清**：本次脚本实际用的模型名是 **`deepseek-flash[1M]`**，而 `~/.claude/settings.json` 的 env 段里 `ANTHROPIC_MODEL = deepseek-flash`（本轮打印过）。⇒ 这个 shell 的 `ANTHROPIC_MODEL` 与 settings.json 不一致（且同一 shell 里 `ANTHROPIC_AUTH_TOKEN` 为空、要靠文件回退才能跑）。**具体是哪一层覆盖哪一层，本轮没查清，不许当已解决**；而 `[1M]` 是否真切到 1M 窗口也仍是未验项（见 D 组之外那批探针：三个 flash 变体 input 都是 38）。

【D25 的三条规则改成】
1. 一期主路径 = **服务端 Web Search**（`type=web_search_20250305` + `name=web_search`，不带 beta 头），**且必须配"最多 N 轮 / 每轮最多 M 条"的上限**。N、M 的值等我自己的日报跑起来量过 token 再定，现在写死就是猜。
2. **"读正文"单独立一条能力**（`llms.txt` 优先，抓不到再走 `/v1/tools/fetch`）——这是 L1 的另一半，不能被搜索代替。
3. 引用要自己写进正文文本（`citations: Ignored` 已实测）。
4. **不声明搜索时它会凭记忆瞎答**（D 组实测）⇒ 学习/榜单场景默认开搜索。

【一处我自己承认的错误】上一轮我把 `search_result: Not Supported` 直接推成"Anthropic 服务端 web search 在我们端点不可用"，并据此在 D20 里定了"只用 `/v1/tools/search` + `/v1/tools/fetch`"。**现在看：两条路都通，而服务端那条更省事**（不用自己管检索质量、不用第二个 API 面）。⇒ D20 的"三条规则"里第 1 条要改：**一期主路径 = 服务端 Web Search 工具；`/v1/tools/search`+`fetch` 留作日报批量抓取用的备用**（日报要一次拉很多页，走服务端搜索会把对话上下文塞满）。

⚠️ **⚠️ 更新（2026-10-27，D29）**：这条里的"DeepSeek 的服务端搜索"要改成"**任意 provider 的**服务端搜索" —— `web_search_20250305` 是 **Anthropic 官方的 server tool 类型**（官方 SDK v2.3.0 的 `types/web_search_tool_20250305_param.py` 里有这个 type 和 `max_uses` 等参数），不是 DeepSeek 私有。
⇒ **第 2 条的"抓不到再走 `/v1/tools/fetch`"改成"抓不到再走 `trafilatura`"**（DeepSeek 那两个私有接口降级为不写进代码）。
⇒ 第 1 条的"每轮最多 M 条"**没有端点参数**（服务端只有 `max_uses` 控轮数）⇒ M 在**客户端截断**。

---

## D26 Obsidian 写入约定（实地读完，阻塞解除）✅（2026-10-26）

【实地读到的结构】`C:\Users\15532\Documents\Obsidian Vault`，22 篇 md。
- 目录：**2 层是主流（16 篇）**，主目录 `personal_konwledge/` 下有 6 个分类：`agent`、`ai coding相关`、`blog开发过程`、`前端知识`、`工作经验`、`服务器相关`；`前端知识/微前端/` 是唯一一个第三层（3 篇）；另有 2 篇散在根目录（含一篇 170 KB 的 `nginx灰度发布.md`）。
- **frontmatter：22 篇里 0 篇用。**（`.obsidian/core-plugins.json` 里 `properties: true` 开着，但一篇没写）⇒ **我们也不写 YAML**，别自创。
- **链接以标准 markdown 为主**：`](…)` 32 处，`[[…]]` 6 处，行内 `#tag` 4 处 ⇒ **用 `[文字](URL)`**。
- 标题：12 篇有 H1、10 篇没有 ⇒ 没有硬规矩。
- 文件名：17 篇含中文、6 篇含空格；**1 篇以 `#` 开头**（`# 手把手：给 GitLab 仓库接入 AI 自动代码评审.md`）——这个会破坏按文件名建链接，我们**不模仿**；**1 篇 0 字节**（`agent/表格agent-从0到1创建agent实践.md`，是个空占位）。
- `daily-notes` 与 `templates` 两个核心插件**开着但没有配置文件**（无 `daily-notes.json` / `templates.json`）⇒ **不要假设有模板变量或日记命名规则**。

【最重要的一条：文档形状不用我发明】
`前端知识/babel.md` 的开头原文是"**好的，我们开始从Babel的官方文档首页从头讲起**"，正文用 `### 第一段：…` 分节，关键处用 `> **大白话解释**` 这样的标签，夹 `*   **大白话解释**：**Babel是一个JavaScript编译器。你可以把它想象成一个极其聪明的…**`。
⇒ **这就是他说的"讲通俗易懂 + 边手操边学"要的那种文档，而且是他自己已经攒过的形状。** L1 第 7 步照它写，不要另创风格。

【写死了的写入规则（进 L1 规格）】
1. ~~落点：`personal_konwledge/<分类>/<主题>.md`；分类优先复用现有 6 个，新分类要先问他。~~ ⚠️ **这条已被 D28 改写（2026-10-27）**：落点改成 **jmb 专属目录 `personal_konwledge/jmb/<主题>.md`**，**不再套那 6 个分类** —— 那 6 个是他**手写内容**的分类，jmb 的产出另立一区。下面第 2–6 条照旧。
2. **不写 frontmatter**；用 `[文字](URL)`；不写行内 tag。
3. 默认照 `babel.md` 的"讲解体"：直接开讲、`##/###` 分节、`**大白话解释：**` 标签、给可跑的例子。
4. 长文（超过约 200 行）额外加两样，照 `trellis分享.md` 的形状：开头 `> 资料来源：<URL 列表>`，正文前 `## TL;DR`。
5. 文件名：中文描述性、不以 `#` 开头；**不复用 `#` 开头的那个先例**。
6. **不许改别人的文件**：只新增或改它自己写过的（要有记录能认出哪些是它写的）。⚠️ **归属标记改由 CF 写**（D28 / 缺口 G4），jmb 不自己维护 `obsidian-owned.json`。

【仍未做】没有实际跑一次写入。第一次真写时先写进一个临时文件名给他看，确认形状对了再落正式位置 —— 这条也进 L1 规格。

---

## D27 "AI 线下会议"这一栏：部分可自动，大陆同城拿不到 ✅（2026-10-26）

【实测结论】**"我附近有什么线下活动"这件事，在中国大陆没有可靠的可自动数据源。** 但"值得专门去的大会"和"港澳/新加坡的真实活动"能拿到。

【逐源实测（本会话从本机探的）】
- **活动行**（唯一真正的大陆活动列表站）：`/events` 返回 200、227 KB 服务端渲染 HTML、28 个 `/event/<id>` 链接，城市用子域（`bj.`/`sh.`/`gz.`…），robots 明确 `Allow: /events`、`/event/`。**但约 4 次请求后开始 302 到 Geetest 验证码**（`/gt3` 本身是 robots 禁止的），活动详情页 302 到 `/login`。无 RSS/ICS。`api.huodongxing.com` 只有一个占位页。⇒ **不可用。**
- **百格活动**：HTML 只有，robots `Disallow: /api/`，无 API/feed。
- 掘金 `/events`、机器之心 `/events` = **JS 空壳**（2.4 KB / 3.4 KB）；InfoQ 中国 `/events` = **HTTP 451**（法律屏蔽）；量子位 = 403；阿里云/腾讯云/华为云活动页 = SPA；CCF `/Activities/` = **403**；`linuxfoundation.cn` = 连不上。
- **Linux 基金会全球站**可达（WordPress），有 "AI Events (8)" 分类带真实日期（"Nov 4–5, 2026"），**但无 ICS**（`?ical=1` 返回 HTML），`/feed/` 是新闻稿不是活动。
- **GDG China**：`gdg.community.dev/gdg-{beijing,shanghai,shenzhen,guangzhou,hangzhou,chengdu,xian}/` 全部 200，页面里有 `<script id="__NEXT_DATA__">`，内含 `{title, start_date(ISO), url}`（例："2026 DevFest Beijing"，`2026-11-22T01:00:00Z`）。**可解析**，robots 只禁 `/api/`、`/gql/`。但**每个城市只有约 5 个活动、多为已过期**。
- **Meetup**：文档化的 REST v2 `api.meetup.com/2/events` = **404 已死**；但 `POST https://www.meetup.com/gql2`（GraphQL）**匿名可用、无需 token**，`EventSearchFilter` 支持 `lat/lon/radius/eventType:PHYSICAL/startDateRange/city/country/topicCategoryId`，返回 `title/dateTime/eventUrl/venue{city}/group/going{totalCount}`。⚠️ **未文档化的内部端点，且 ToS 页 404 ⇒ 合规状态不明确、随时可能变。**
  **但大陆供给几乎为零**：北京全部物理活动池约 **7 个**，且 query 词被忽略（"AI"、"大模型"、"机器学习"、"yoga"、"blockchain" 返回同一批，全属同一个 group）。香港 11 个、新加坡 19 个（有真实的 "AI NETWORKING DRINKS"、"AgentCon Singapore 2026"、"DevFest Singapore 2026"）。
- **ccfddl/ccf-deadlines**：MIT、**9,482★**、**今天还在 push**。关键：**它不只做投稿截止日期**——每场会有 `date` 和 `place`（例：ICLR 2027 = "April 26-30, 2027" / "San Francisco"；NeurIPS 2026 = "December 8-10 (Sydney), December 9-11 (Atlanta and Paris)"）。⇒ **这是"参会视角"能用的源**。缺点：日期是自由文本、不是结构化时间。
  走 `api.github.com/repos/ccfddl/ccf-deadlines/contents/conference/AI/iclr.yml`（base64 解码）——**别走 raw.githubusercontent.com**（本机实测两次超时，而 api.github.com 正常）。
- 已死/不可用的同类：`paperswithcode/ai-deadlines` 停在 2024-09；`huggingface/ai-deadlines` 只做截止日期；`papercopilot/paperlists` 是论文数据不是活动。

【本期决定：这栏降级但保留，写成两段，标注清楚】
1. **值得专门去的会**：`ccfddl` 的 `date` + `place`（MIT，每日 push，走 api.github.com）。**这是这一栏的主内容。**
2. **港澳 / 新加坡的真实活动**：Meetup `gql2` 匿名查询（香港 11 / 新加坡 19 个池子里有真 AI 活动）。
3. **中国 GDG 城市活动**：解析 `__NEXT_DATA__`（量少，但真实、有日期）。

并且**必须在清单里写一句诚实的话**：*"大陆同城活动我拿不到——活动行有验证码和登录墙，中文科技媒体的活动页是空壳或被拦。"* 让他知道这不是漏抓。

【明确不做的】
- **不绕验证码、不登录爬活动行**（那是绕过技术保护措施，且 robots 明禁 `/gt3`）。
- **不把 Meetup 的 `gql2` 当唯一依赖**（未文档化 + ToS 不明）⇒ 它挂了这一栏只少第 2 段，其余照常。
- **不自己猜会议日期**：ccfddl 给的是自由文本，原样展示，不解析成"还剩几天"。

---

## D28 Obsidian 落盘归 Context Forge，jmb 只生成内容 ✅（2026-10-27，**我定的，等他点头**）

【用户原话】"**写 obsidian 应该是 context forge 的事情，你只需要告诉我不足的点**，我会考虑让你改还是让别人去改 context forge"

【决定】
- **分工线**：**内容生成 = jmb**（把话题写成讲解体 markdown，遵守 D26 六条）；**落盘 = Context Forge**（路径围栏、归属标记、hash 乐观锁、冲突副本、draft → 正式）。
- **jmb 不再自己写 `jmb/obsidian.py` 的文件写入部分**；也不自己维护 `obsidian-owned.json`（归属标记由 CF 写）。
- **落点 = `Documents\Obsidian Vault\personal_konwledge\jmb\`**（2026-10-27 他定的"给 jmb 建专属目录"，**目录已建**）。里面**不再套那六个分类** —— 那六个是他**手写内容**的分类，jmb 另立一区。
- **不足点清单**独立成文：[`docs/context-forge-gaps.md`](context-forge-gaps.md)。

【⚠️ 形状变了以后，三个原本要改 CF 的点变成零改动】（2026-10-27 同日修订）
1. **记忆只进 `memory.db`，不落 md —— 零代码**：md 投影的唯一自动触发点是 `watcher.py:436`（`forge watch` 跑时调 `MemoryProjector`），另一个是手动命令 `forge project-memories`（`cli.py:127`）⇒ **jmb 只用 `MemoryStore` / `MemoryRecall`，不启 watcher/worker，就永远不投影**。
2. **机器产物隔离 —— 零代码**：CF 的知识根是 **`vault_path / knowledge_dir`**（`config.py:36-38` `Settings.root`），`knowledge_dir` 默认 `"context-forge"` ⇒ CF 的产物自动落在 `jmb/context-forge/`，**与手写区天然分开**。
3. **"现有 CF 的 `vault_path` 指错库"这条不成立**：它指的是**他现有的** CF 实例（`~/.context-forge`，`vault_path = Desktop/konwledge_base`），跟 jmb 无关 ⇒ **一个字都不动**。jmb 用自己的实例（`CONTEXT_FORGE_HOME` 一换，`config.py:46-53`，配置物理分开），Phase 5 里新建一份 `config.toml` 指到 jmb 专属目录。

【为什么这条成立 —— 有硬证据，不是我的偏好】
CF 读源码发现它**本来就有整套 Obsidian 写入零件**：
- `vault.py:35-54` `_safe()` 路径围栏（不许逃出 vault 根，子目录放行）
- `vault.py:62-68` `is_user_owned()` frontmatter 归属保护；`:99-110` 命中就跳过
- `vault.py:176-190` `update_with_expected_hash()` sha256 乐观锁 + `.conflict-<ts>` 副本（**不覆盖**用户改动）
- 原子写（`:41-52`）；`__init__` 里 `mkdir(parents=True)`（`:33`）
- `README.md:76` 明说 `vault_path` 就是用户的 Obsidian vault

⇒ **我在 spec §3.1 里自己设计的"只写自己写过的文件 / 改前存副本 / 冲突不覆盖"，CF 全都有** ⇒ 我那套是重复造。

【CF 真正缺的五个口子】
| # | 缺什么 |
|---|---|
| G1 | 任意相对路径 + 自定义文件名的写入口（现在只有 `knowledge/accepted/<id>.md` 与 `memories/<sha16>.md` 两个固定模板）。⚠️ **相对路径的基准必须是 `vault_path`，不是 `vault_path/knowledge_dir`** —— 这条不定死，jmb 写不进那个目录 |
| G2 | CLI 子命令（`cli.py` 30+ 个子命令里没有 write/export/note） |
| G3 | MCP 写 tool（`mcp_server.py` 14 个 tool 全是读+反馈，一个都不能写文件） |
| G4 | 写入者归属标签（现有 `user_owned` 是单向的："别碰我的"，缺"这是 jmb 写的、可以改"） |
| G5 | draft → 正式 的两段写 |

【已知短板 / 自报代价】
- **Phase 4 有真实前置依赖**：CF 那 5 个口子不补，L1 第 7 步就落不了地。**不许用"jmb 自己写一套顶上"来绕** ⇒ 那是两套写入器、两套归属语义，将来必打架。
- G4 有两种实现，代价不同：frontmatter 标记（jmb 写的文件会多一个 frontmatter 块，与库里另外 22 篇不一致）vs CF 侧另记一张表（文件干净但多一张表）。**这个由他/改 CF 的人选**。
- 建议 **B（另记一张表）**：D26 那条"不写 frontmatter"是照着他 22 篇的现状定的，值得为它多一张表。

【依赖】D15（落点 = Obsidian 主库）、D26（六条写法约定，落点那条已被本条改写）。
【状态】✅ **归属与分工已定**（2026-10-27 他回"**cf 我自己改**"）⇒ CF 那 5 个口子**由他本人改**，缺口清单在 [`docs/context-forge-gaps.md`](context-forge-gaps.md)，可直接照着做。**jmb 侧不写任何文件写入器，等 CF 补完再开 Phase 4。**

---

## D29 模型接入不绑死 provider；工具用成熟开源件 ✅（2026-10-27，**我定的，等他点头**）

【用户原话】"**我不一定用 deepseek 的 api，关于 sdk 和工具，你还是找开源代码抄而不是直接用 deepseek 的吧**"

【决定】
- **模型调用走官方 SDK + 一张声明式 provider 表**，DeepSeek 只是"当前在用的那一条线路"，不是实现本身。
  - 线路一：**Anthropic 官方 Python SDK**（Apache-2.0，v2.3.0 / 2026-10-23）—— `base_url` 原生可换，`system`/`stream`/`tools`/`count_tokens` 全是核心方法。
  - 线路二：**OpenAI 官方 Python SDK**（Apache-2.0，v3.39.0 / 2026-10-26）。
  - 统一层：自写 `jmb/providers.py`，**抄 `hermes-agent/providers/base.py` 的 `ProviderProfile`**（MIT，~200 行零依赖，本机就有源码）。
  - 端点怪癖：抄 `hermes-agent/agent/anthropic_adapter.py` 的 `_is_deepseek_anthropic_endpoint()` / `_requires_bearer_auth()` 等纯函数。
- **不用 DeepSeek 的私有接口**：`/v1/tools/search` 与 `/v1/tools/fetch` **降级为备选，不写进代码**（D25 那条要跟着改）。
- **抓正文用 `trafilatura`**（Apache-2.0，2.3.1 / 2026-10-06）—— 本机已装 `lxml 6.1.3`（正好是它的下限），最重的依赖已在位。
- **不引 LiteLLM / langchain / letta**：LiteLLM 能把**请求侧**抹平（`web_search_options`），但**响应侧抹不平**（三种块结构），且 100+ provider + Rust core 对一个本地陪伴 agent 太重。

【为什么这条成立 —— 三条查实的事实】
1. **`web_search_20250305` 不是 DeepSeek 私有的，是 Anthropic 官方的 server tool 类型**（官方 SDK v2.3.0 的 `types/web_search_tool_20250305_param.py` 里有这个 type 和 `max_uses` 等参数）⇒ **这条能力在 Anthropic 系是通用的**，换 provider 不用换代码。⚠️ 官方文档页本机打不开（地区屏蔽），依据取自 SDK 源码。
2. **本机实测的"地板层"是死的**：`SkillAbout/last30days` 的 keyless 搜索三条腿（DDG / Startpage / SearXNG）里前两条**本机超时**；`web_fetch_keyless.py` 走的 `r.jina.ai` **也超时**。⇒ 抄它没用。
3. **本机一个搜索后端的 key 都没配**：`~/.config/last30days/.env` 不存在，环境里 `BRAVE_API_KEY`/`EXA_API_KEY`/`SERPER_API_KEY`/`PERPLEXITY_API_KEY`/`PARALLEL_API_KEY` 全没有 ⇒ `WEB_BACKEND_ORDER` 那条链现在一条也走不通。

【顺带修掉我自己一个错】
原 spec 写"thinking 块白送 ⇒ 一律丢弃"。**错**：`hermes-agent` 的 `_is_deepseek_anthropic_endpoint()` 记着 Anthropic 系在 thinking 模式下**要求把上一轮 thinking 块原样回传**，否则 400。⇒ 规则改成"**不展示给用户，但保留在历史里回传**"，按 provider profile 决定。

【已知短板 / 自报代价】
- 多一条线路就多一层抽象（协议类型 / 鉴权模式 / extra_body 钩子）⇒ 一期只有 Anthropic + OpenAI 两条，profile 表别写太泛。
- **Anthropic SDK v2 把鉴权头从 `X-Api-Key` 换成了 `Authorization: Bearer`**（v1.17.0 还是前者）⇒ 换 provider 时按 profile 走，别写死。
- 服务端搜索的**条数没有参数**（只有 `max_uses` 控轮数）⇒ "前 5 条"在客户端截断。
- DeepSeek 这条线路**认不认 `max_uses` 本机没验** ⇒ 验它，且本地 `count_tokens` 预算闸门默认就上（不依赖任何未验参数）。

【依赖】D25（服务端搜索这条路）—— D25 的"不走 `/v1/tools/search`"那半条仍然成立，但"用 DeepSeek 的服务端搜索"要改成"用**任意 provider 的**服务端搜索"。
【状态】✅ **两条线路（Anthropic 协议 / OpenAI 协议）他确认够了**（2026-10-27 原话"俩协议应该够吧"），`trafilatura` 同批确认。⇒ **D29 整条已定。**

---

## D30 取消"当天第一次开机补跑" ✅（2026-10-27，**他定的**）

【用户原话】"**不用做当天第一次开机补跑**"

【决定】
- 每日清单**只在 10:00 跑一次**。**不配开机触发器**（`schtasks` 的 ONLOGON/ONSTART、`qoder_cron` 都不挂），**不做补跑逻辑**，也不做"当天任意时刻检查是否漏跑"。
- 覆盖 D24 里那段"默认写法：错过就补跑"。

【代价，写明白】
- **10:00 时机器关着 ⇒ 那天没有清单。** 这条代价按他的决定接受，Phase 7 的验收 3 就是把它钉死，别以后有人"顺手"补回来。

【为什么不需要补跑机制】
- 补跑本来就不是独立需求，是我为了让 D23 那条"每天硬性跑一遍"真能落地而加的中间件。他直接砍掉 ⇒ 那条规矩按字面执行。

【状态】✅ 已定。

---

## D32 Context Forge 以独立包被 jmb 依赖，不共用记忆，jmb 按独立 app 打包 ✅（2026-10-28，**他定的**）

【用户原话】"我想做的是用 context forge 的机制，但是不和 context forge 共用一套记忆。我之后可能将 jmb 独立为一个 app 上线，所以该应用应该是独立的。" / "可以，按a来，这算是把cf打包然后jmb导入包是吧"

【决定】
- **代码复用、数据分家**：CF 作为 `context-forge` 独立包被 jmb 依赖，jmb 不复制 CF 源码；两边的 `memory.db` 始终各用各的。
- **开发期**：`pyproject.toml` 的 `[tool.uv.sources]` 指向 `../Context Forge`（editable）⇒ 他改 CF，jmb 立刻跟到。
- **发布期**：构建固定版本的 `context_forge-<ver>-py3-none-any.whl`，打 app 时一起收进产物；不要求用户本机装过 CF，也不 import 他的源码目录。
- **数据路径**：`CONTEXT_FORGE_HOME=%LOCALAPPDATA%\jmb\spaces\<owner>\forge`；多用户时每个 owner 一个实例（D13 口子 1）。jmb 启动时先钉这个环境变量，再 import CF（`runtime_dir()` 惰性读）。
- **导入方式**：删除 `jmb/memory.py` 的 `sys.path.insert` / `JMB_CF_SOURCE`，改成正常 `import context_forge`；doctor 增加"CF 包版本 + 解析路径"一行。

【验证（2026-10-28）】
- `context-forge 1.0.0` 已装入 jmb 的 venv，解析到 `C:\Users\15532\Desktop\xj\Context Forge\context_forge\__init__.py`（editable）。
- 临时 `JMB_HOME` 跑通 `propose → candidate → open_confirmation → approve_confirmation → active → recall`，没碰真实库。
- `uv build --wheel` 产出 `context_forge-1.0.0-py3-none-any.whl`（约 182 KB）；干净 venv 从 wheel 安装后 `import context_forge.memory` 成功，不依赖源码目录。
- `jmb doctor`：CF 家目录 [就绪]、CF 包 [OK]；`~/.context-forge/memory.db` mtime 未变。

【边界 / 不做】
- 不把 `~/.context-forge` 的数据迁进 jmb，不共享它的 `memory.db`。
- 不为 jmb 改 CF 的 schema；不 fork 整个 CF。
- 不做 `if owner == 'local'` 特权分支。
- Obsidian 落盘仍归 CF（D28），但走"打包进 jmb 的 CF"，不是"调用户本机的 CF"；G1–G5 仍由他改。
- MCP 暴露（Phase 8）仍后移二期。

【已知短板】
- 发布包会带 CF 的代码和 CLI（`forge`/`forge-mcp` 入口）；如果将来要求"包里不出现 CF 代码"，才切到 vendor（B 路线）。
- 开发期 editable 依赖要求 `../Context Forge` 在本机；发布期必须换成 wheel，不能把这个相对路径带出去。
- 完整 `uv sync` 因运行中的 `jmb chat` 占用 `jmb.exe` 暂未收尾；当前依赖已用 `uv pip install -e` 装入，editable 生效。关掉那个会话后补跑一次 `uv sync`。

【依赖】D28（Obsidian 落盘归 CF）、D13（多用户口子）、D29（不绑 provider）。
【状态】✅ 已定并落地包依赖；确认回路与 Obsidian 落盘待后续。

---

## D33 桌宠渲染层内置到 jmb，不用 Petdex 外接/sidecar ✅（2026-10-28，**他定的**）

【用户原话】"我不建议a，a的话不就是应用+应用，不是一个整体吧。 渲染层可以规划下之后一起做"

【决定】
- **否决 A**（把 `Petdex.exe` 作为 sidecar 打进 jmb 安装包）：那仍是两个应用、两个进程，只是装在同一个包里，不是"一个整体"。
- **选 B**：jmb 自己渲染桌宠（透明置顶窗口 + 精灵图动画），一个进程、一个产品。**本期只规划，不实现**，之后与 app/渲染层一起做。
- **Petdex 只作原型参考**：可以抄 `pet.json` + 8×9/8×11 网格、192×208 帧、state 枚举和气泡经验；**不打包、不依赖、不复制它的 App**。
- 原型 HTTP 客户端（原 `jmb/pet.py`）**已随原型清掉**（2026-10-28，备份在临时目录）；渲染层落地时新建 in-process backend（`set_state` / `bubble` / `show` / `hide`），chat/brief 的调用点再按需接回。
- **pet 素材必须 jmb 自有**：boba 的 `pet.json` 没有 license 字段，不能随产品分发；做 jmb 专属形象，或首次运行时让用户自己装。

【规划要点】
- **事件循环**：GUI 主线程 + chat REPL 工作线程 + 线程安全事件队列；Ctrl+C/退出必须能走完 fact 确认。若未来 jmb 有自己的 GUI 壳，桌宠作为该壳的一个窗口，冲突更小。
- **技术选型**：PySide6（LGPL，透明/置顶/托盘/动画/多屏控制最稳，体积大）优先；pywebview（轻，但 per-pixel click-through 风险）和 Tkinter（零依赖，透明/跨平台弱）作备选。先做技术验证再定。
- **交互**：透明、无边框、置顶、不进任务栏、可拖拽、透明区点击穿透、托盘、气泡（换行/自动消失）、多屏/DPI。
- **状态映射**：idle / thinking / searching / working / waiting / failed / waving；行序抄 Petdex 源码，不抄代码。
- **打包**：pet 资源随包；PySide6 LGPL 合规；代码签名；Windows 优先，mac/linux 后。
- **代价写明**：桌宠生命周期跟 jmb 走——jmb 不跑，桌宠不出现。要"关掉 jmb 还留着"就是另一个形状（A 或托盘后台），不选。

【依赖】D32（jmb 独立 app）、D4'（入口形态）、D24（每日清单主动冒泡）。
【状态】✅ 方向已定；v1 Tkinter app 壳 + jmb 自有 sprite 桌宠已落地（D35）；PySide6/托盘/严格穿透后做。

---

## D34 jmb 能写代码：任意路径 + 本会话授权 + 按轮次 undo ✅（2026-10-28，**他定的**）

【用户原话】"任意路径   不分版本一次做完  本会话 按轮次"（回答四问）

【决定】
- **工具**：`read_code` 扩 `offset/limit`；新增 `grep` / `find`（只读，走 read 授权，不占 exec）与 `write_file` / `edit_file` / `run_command`。
- **写范围**：**任意路径**；保留硬拒：`platform-group-projects`（D11）、jmb 自身 `spaces/`、`.git` 目录。
- **授权**：读沿用 D11 白名单；写/执行首次触发**本会话**授权，之后本会话放行；**不做 persistent write/exec**。
- **执行沙箱**：`run_command` 默认 Docker（`JMB_SANDBOX_IMAGE` 默认 `python:3.13-slim`；`--network none`、只读根、cap-drop、2g/2c）；只有 `JMB_SANDBOX=host` 才显式关闭。`fetch_page` 拒绝 localhost/内网/回环/保留地址，重定向也检查。
- **撤销**：每个用户轮次一个 change set（`changes/code/<turn_id>/manifest.json` + preimage）；`undo` 回滚整轮；文件之后被改过则拒绝回滚；**命令副作用不能 undo**。
- **编辑语义**：参考 Pi coding agent（MIT）的 `edit` 契约——精确优先、唯一、不重叠、模糊归一、保留 BOM/CRLF、返回 diff；**不引 Pi runtime**。
- **输出**：命令输出截断 20KB/800 行，完整输出落盘；diff 截断 5000 字符。
- **定位**：coding 能力，不改人格/记忆主线；不做第二个 Claude Code。

【验证】`tests/test_code_tools.py` + `tests/test_search_tools.py` + `tests/test_sandbox.py` + `tests/test_webfetch.py` **39 项通过**：CRLF/BOM、重复/重叠/无变化、模糊、按轮次 undo、外部改动拒回滚、公司仓/spaces/.git 拒写、会话授权、read offset/limit、grep/find 只读、命令/截断/超时、Docker argv/缺 docker、SSRF/重定向、chat 工具路由。

【已知短板】
- **Docker daemon 本机未运行**，容器路径未 runtime 测试；默认镜像不含项目依赖，跑测试要设 `JMB_SANDBOX_IMAGE`。
- `fetch_page` 防 SSRF 但 DNS rebinding 未彻底解决（校验后 urllib 会再解析一次）。
- `run_command` 的 `JMB_SANDBOX=host` 模式仍是 OS 用户权限；默认 docker 才是沙箱。
- 任意路径 + 本会话 exec 权限很大；命令副作用不能 undo。
- 项目上下文/compaction 未做；OpenAI 线工具结果顺序仍是已知问题（本轮未修）。

【状态】✅ 已落地；测试见 `tests/test_code_tools.py`、`tests/test_search_tools.py`、`tests/test_sandbox.py`、`tests/test_webfetch.py`。Docker 容器路径待启动 Docker 后验收。

---

## D35 app 壳 v1：Tkinter 聊天窗口 + 内置桌宠 ✅（2026-10-29，**按他"下一步做app壳和渲染层"落地**）

【用户原话】"下一步做app壳和渲染层"

【决定】
- `jmb app` 打开 Tkinter 聊天窗口 + 透明置顶 `PetWindow`；终端 `jmb chat` 保留；两者共用 `ChatSession`（模型/工具/记忆/代码改动一份）。
- 框架先 **Tkinter**（stdlib、零安装）。PySide6 在这台机器上安装卡住（下载/解包十几分钟未进 venv；磁盘 8.6GB、可用内存 0.53GB），按 D33 备选回退；PySide6 后换。
- 渲染 v1：**jmb 自有 `pet.json` + 8×9 网格 spritesheet（192×208 帧）**，Pillow 加载、Canvas 兜底；idle/thinking/searching/working/failed/waving + 气泡 + 拖拽；暂未做托盘、严格点击穿透。
- 授权：GUI 读/写/执行走 worker→主窗口 `messagebox` 回调（`grants.set_prompt_handler`），不再依赖 stdin。
- 撤销：GUI 有「撤销」按钮/顶部菜单，走同一 `ChatSession.undo`（代码整轮 / 自我改写）。撤销后会向**下一轮上下文**注入 `[系统事件]`：模型知道这次改动是用户撤的，之前的写入/编辑结果不再代表当前文件，需要重新 `read_code` 确认。
- 记忆收尾：GUI 关闭时弹「全部记 / 全部不要」确认；不做逐条勾选。
- 分支 `feat/app-shell-renderer` 合并了 `feat/code-search-sandbox`（#6），所以 app 里直接有 grep/find 和 Docker 沙箱。

【验证】46 项测试通过：app smoke、sprite 加载、ChatWorker ready/stop、GUI permission handler、记忆 ask 回调、撤销事件注入、grep/find、沙箱/SSRF、code tools。

【已知短板】Tkinter 视觉/点击穿透弱；无托盘；PySide6 未装；记忆确认只有全记/全丢，不能逐条选；sprite 是 jmb 自有的占位形象（不是 Petdex 画廊素材）。

【状态】✅ v1 已落地，待验收；PySide6/真实 sprite 后续。

---

## D36 每日清单的投递面 + 定时任务壳修复 ✅（2026-10-29）

【背景】Petdex 随 D33 清掉后，`brief.py` 的冒泡调用点没了：10:00 任务即使跑成功也没有任何可见提示。2026-10-29 那次实际是**跑了但失败**（`LastTaskResult=2`，没有生成 `brief-2026-10-29`）：`scripts/brief-task.cmd` 存成 UTF-8 且在 `rem` 注释里写中文，cmd.exe 按 OEM 代码页把批处理切坏（手跑时能看到 `'（schtasks' 不是内部或外部命令`），计划任务下直接退出 2，没跑到 uv。

【决定】
- 任务壳改为**纯 ASCII + CRLF**；stdout/stderr 追加到 `%LOCALAPPDATA%\jmb\logs\brief-task.log`，start/exit 码显式落日志；计划任务动作改为 `cmd.exe /c "…\brief-task.cmd"`。
- 任务设置只改两条：`DisallowStartIfOnBatteries=false`、`StopIfGoingOnBatteries=false`（用电池也跑）。**不动 D30 的"不补跑"**：`StartWhenAvailable` 保持 false，不挂 ONLOGON/ONSTART。
- 投递面（两道）：①清单**新生成**时 `brief.py` 发一条 Windows 通知（PowerShell WinRT toast，AUMID=`jmb`，本机实测可用；app 关着也能收到）；②app 壳每 60 秒检查今天的 `brief-YYYY-MM-DD.json`，未提醒过就在**聊天窗口里留一条 `jmb>` 消息** + 冒一次桌宠气泡，并写 `brief-seen.json`（同一天不重复）；菜单「文件 → 今日清单」用默认程序打开 md。
- app 没开：只有 toast；下次打开 app 会对当天未提醒过的清单补一条聊天消息（只是提醒，不重跑数据）。
- 可点性：**单击桌宠恢复/聚焦聊天窗口**（拖动阈值 4px，不会误触）；**清单气泡可点**，直接打开全文——避免"菜单在最小化的窗口里、桌宠上找不到"。
- 通知只在**新生成**时发；幂等命中（"今天已跑过"）不重复打扰。

【代价】toast 受 Windows 通知设置/专注助手影响，可能被折叠；app 内消息需要 app 开着（杀进程/重启后是新的 Tk 窗口，旧滚动内容不保留，但 transcript 在磁盘上）。

【验证】计划任务 `schtasks /run` 后 `LastTaskResult=0`，日志出现 `[brief-task] start/exit 0`；toast 经 PowerShell 实测成功、helper 单测覆盖；48 项测试通过（新增「清单只提醒一次」「toast 调用」）。

【状态】✅ 已落地，待验收。

---

## D37 每日清单的北京活动栏：活动行 + GDG + lianpu 补充 ✅（2026-10-29）

【用户原话】“只需要抓北京的近期可报名的软件 ai 相关的免费会议”；“去搜各家社区的活动页和主办方自己的页面，lianpu 只当补充”。

【本机实测（2026-10-29）】
- **活动行北京列表页**服务端渲染（标题/时间/商圈/主办方可解析），**详情页** `var ativityJson` 里有 `IsFree`、`Start`（`/Date(ms)/`）、`City/Address` ⇒ 免费可确认；GDG 的报名页也挂在这里。
- **GDG 北京**主办方页的 `__NEXT_DATA__.prerenderData.upcomingEvents` 直接有 upcoming（DevFest 2026-11-22）；报名外链到活动行，继续用 `IsFree` 确认（实测免费）。
- **lianpu** 北京/AI 分类卡片有明确“免费”标签 + 时间/地点 ⇒ 只当补充。
- 排除：Meetup 北京技术组（Kong/大数据等）upcoming 全是线上；SegmentFault 近期无北京场；PyCon China / GOSIM / 昇腾 / CCF 当前没有可解析的近期北京活动。

【决定】
- 来源 = **GDG 北京（主办方页）+ 活动行北京（详情页确认免费）+ lianpu（补充，只认免费标签）**。
- 过滤：**未来 45 天、北京线下、免费、AI/软件相关**；营销/获客/变现/增长/训练营/对接会/生态伙伴等非技术向词剔除。
- 去重：同标题，或同时间段 + 长公共子串（跨源同一场只留一条，优先 GDG/活动行）。
- 每条列日期时间、标题、地点、免费、来源、链接；末尾一行写各源抓取结果（失败如实写，不编）。
- 全程零模型调用；活动行只抓关键词命中的候选详情（≤5 条），请求间隔 0.8s；遇“访问太快”等 6s 重试一次，仍限流就在源状态里写明（不静默、不硬凑）。

【代价】页面结构变了会抓不到（末尾源状态会显示 0，不会静默）；活动行详情需要逐条抓，单日多几秒到几十秒；连续手动重跑会触发活动行限流（定时任务每天只跑一次，正常不会）。

【验证】抓取成功时 2026-10-29 得到 4 场（活动行 2、GDG 1、lianpu 1：快手技术沙龙、非凡大赏 AI 创造者大会、DevFest、数创新境）；6 个解析单测；全量测试通过。

【状态】✅ 已落地，待验收。

---

## D38 上下文压缩：按模型预算 + 观察遮蔽 + LLM 结构化摘要 ✅（2026-10-29）

【背景】30k 固定预算对 1M 模型过于保守；旧闸门只会丢 thinking/搜索结果，老细节直接没了。用户定了前两步（旧工具占位 + 结构化摘要），第三步（旧对话检索）先不做。

【决定】
- **预算按 provider**：`ProviderProfile.context_window / input_budget`；1M 模型 = 1,000,000 / 120,000（80% 触发压缩），其他 = 128,000 / 30,000；`JMB_CONTEXT_WINDOW` / `JMB_INPUT_BUDGET` 可覆盖。1M 窗口不当 1M 工作区用（context rot）。
- **第一层：观察遮蔽**（`_mask_old_tool_results`）：超过最近 10 条、内容 ≥400 字符的可重取工具结果（read_code/grep/find/fetch_page/search_web/today_brief）换成占位符；`run_command` 不遮蔽（副作用不能重跑）。
- **第二层：LLM 结构化摘要**（`compact.py`）：上一轮 usage ≥80% 预算且历史 ≥14 条时触发；独立 system、无工具、流式补全，按 40k 字分块合并；摘要必须保留目标、决定/约束、文件路径与状态、命令/exit code/关键错误、未解决/下一步、失败尝试、禁区；作为带标记的 user 消息放回，切在 assistant 边界，保留最近 8 条、不拆工具对；失败/空摘要 → 3 轮冷却 + 现有裁剪兜底。
- **计数**：用 `turn.usage.input_tokens` 作为触发依据，不依赖当前 404 的 `count_tokens`。
- **CF 仍只管事实记忆**（remember_fact → 确认 → 召回 6 条），不存 transcript；第三步的原始检索暂不做。

【代价】摘要本身有损（路径/决定靠模板硬保）；摘要调用多一次 API（约 16k input + 1k output，几秒）；如果 provider 不支持非流式/流式补全，会回退到只遮蔽，并在 UI 写“压缩失败”。

【验证】8 个压缩/预算单测（遮蔽、切点、角色交替、空摘要回退、1M 预算）；全量测试通过。真实 provider 的摘要调用未跑（用户未批准），首次长会话需观察。

【状态】✅ 代码已落地，待重启验证。

---

## D39 SOUL 换成江慕白（英文压缩版）✅（2026-10-30，**他定的**）

【用户原话】“soul改为这个 但是需要精简一下，作为每个回话都注入的前缀，尽可能让模型更好识别，更省上下文，如果英文更好那就翻译成英文”。

【决定】
- 把用户给的江慕白人设压成英文指令版（518 words / 3299 chars），保留中文名字和 3 条中文语气示例；首行固定 “Reply in Chinese unless he writes another language”。
- 结构：Look / Core / Background / With him / Voice / Rules；六条底线不变（决定权、每日清单例外、公司项目、文档、SOUL 只读、不冒充真人）。
- 用英文是因为同内容 token 密度通常更高（具体以 provider tokenizer 为准）；前缀缓存只在 SOUL 改动时失效一次。
- 同步写入 live SOUL 和 `seeds.py` 的 `SOUL_V0`（新装默认），旧版备份在 `SOUL.md.bak-20261030-0043`。

【验证】live/seed 逐字一致；`prefix.build_system()` 加载 3785 chars；全量测试通过。

【状态】✅ 已落地，重启 app 后生效。

---

## D40 app 壳 + pet 视觉 v2：圆角气泡聊天 + 薄荷状态桌宠 ✅（2026-10-30，**按他“美化app壳和pet”落地**）

【调研】桌面宠物的共同形状：透明置顶、可拖拽、状态气泡、不抢焦点（Petdex / dsh-pet / open-tui-pet）；Tkinter 原生控件没有圆角，可靠做法是 Canvas 画圆角 + 事件绑定；现代聊天界面用圆角气泡、低对比边框、单一强调色。决定沿用 pet 的薄荷色做强调色，app 用深墨底，不再混用蓝按钮。

【实现】
- 新 `theme.py`：色板/字体/圆角/圆形头像（Pillow 合成，避免 Tk 透明像素发黑）/ Windows 11 深色标题栏 + 圆角（DWM，属性实测 1/2）。
- 新 `widgets.py`：`RoundedButton`（Canvas 圆角、hover/press/disabled）、`InputBar`（圆角槽 + Entry + 占位符随焦点/忙碌切换）、`ChatBubble`（按字符测量换行、圆角气泡）、`ChatView`（头像 + 名字 + 左右气泡 + meta 竖条 + 空状态 + 流式气泡 + 自绘细滚动条 + 鼠标滚轮；只在底部时自动跟随，翻旧消息不会被拽回）、`ask_yes_no/show_message`（深色模态授权/记忆/错误弹窗）、`CodeBubble`（代码围栏独立等宽面板，语言标签，超过 22 行折叠）。
- `main.py`：深墨底、头部头像/名字/在线副标题、「清单」+「···」按钮（替代原生菜单）、底部圆角输入 + 发送/撤销、状态栏 usage；保留 worker/授权弹窗/撤销/清单/压缩事件全部行为；气泡/系统行右键可复制，「···」菜单可复制最后一条回复；真实 app 记住聊天窗口/pet 位置（`state/ui.json`）并做 180ms 启动淡入，预览/测试不写状态。
- `pet.py`：桌宠窗口加状态胶囊（江慕白 · 在线/在想/搜索中/工作中/出错）、hover 细环 + 小星光、点击回弹 + 星光、状态切换回弹、右键菜单（打开聊天/今日清单/切换置顶/退出）、圆形奶油气泡（薄荷侧条 + 下指尾巴 + 点击回调）；拖动时气泡跟随。
- 只在 UI 层改；`ChatSession`/工具/沙箱/记忆/压缩不动。

【代价/边界】Tkinter 无真正透明阴影/模糊；原生标题栏深色由 DWM 提供（PrintWindow 截图仍显示浅色 chrome，实际窗口属性已是深色）；无托盘；窗口缩放时已有气泡不重排（新气泡按 600px 上限）。

【验证】app 测试 12 项（流式、代码围栏、输入占位、只贴底滚动、位置恢复）+ 全量 75 项通过；PrintWindow 截图检查空状态、短会话/代码面板、长会话滚动条、pet（含星光）、气泡（锁屏下用 PrintWindow，未动用户锁屏）。

【状态】✅ 已落地，待重启验收。

---

## D41 启动延迟：anthropic 延迟导入 ✅（2026-10-30）

【背景】app 测试里 worker 启动超时；单独跑只要 11s，同进程跑 UI 测试后 >90s。根因之一是 `ChatSession.__init__` 同步 `import anthropic`（本机 10s+，内存紧张时更久）。

【决定】
- `ChatSession` 不再在初始化时导入 anthropic；`count_fn` 第一次真正需要计数时才导入并创建 client。
- 测试里 worker 启动测试排到 UI 测试之前（Tk/PhotoImage 的跨线程清理会拖慢后续线程，这是测试隔离问题，不是产品路径）。

【效果】全量 72 项测试 16s（之前 86s–335s）；app 窗口 ready 不再等 SDK 导入。代价：第一条消息仍要付一次导入（约 10s），之后正常；暂不做后台预热。

【状态】✅ 已落地。

---

## 悬置的技术前提（已实测，直接引用，不再重复调研）

- **前缀纪律**：稳定段逐字节不变且排在一切可变内容之前。实测：改尾部一个词命中不掉（cache_read=2048）；改开头一个词命中归零（input 2302 / cache_read=0）；稳定前缀 + 每轮换中文用户话，新算只有 255–258 token。
- **工具循环可用**：实测 `stop_reason=tool_use` 且参数解析正确；`/v1/messages/count_tokens` 返回 200 并计入工具定义 ⇒ 预算闸门可做。
- **`thinking` 块白送但不强制回传**：带回去和丢掉都 200 通过 ⇒ 自己写循环可以直接丢弃。
  ⚠️ **但这条只对当前这条线路成立**（D29）：Anthropic 系在 thinking 模式下**要求回传**（`hermes-agent` 源码 `_is_deepseek_anthropic_endpoint()`）⇒ 规则改成"不展示给用户，但保留在历史里回传"，按 provider profile 决定。
- **未定**：`[1M]` 是否真切换 1M 窗口（三个 flash 变体 input 都是 38，判不出）；缓存存活上限；命中粒度（只见 2048/256，疑为 256 块）；`tool_result.is_error` 到底读标志还是读文本（对照组不干净）。设计结论不依赖这三条。
- **`is_error` 已定的纪律**：工具失败原因必须写进 `content` 文本，不能只设标志位。

## 已定不做（跨路线，均带理由，可被新证据重开）

代码/权重自改流派（ADAS/DGM/SICA/AlphaEvolve/SEAL，没有自动评测器就不能定义"更好"，且 DGM 记录到攻击自己的奖励函数）；Anthropic 官方 memory tool 与服务端上下文压缩（实测 `anthropic-beta` 被忽略）；情绪数值量表（NOT FOUND 任何 shipped 且公开规格的实现）；图数据库记忆（Neo4j/FalkorDB 运维成本）；本地模型推理（本机无，且用户既定不装）；多渠道桥（Telegram/WhatsApp，第一期不碰）；把"以教代学/AI 问责伙伴"当效果承诺（一手证据未取到）。

---

## D31 一轮设计评审的修订集（2026-10-27，**评审定的，待他点头**）

【背景】对 spec + implementation-plan 做了一轮评审（含对 Context Forge 源码的实地复核——内容全部属实，4 处行号漂移已更正），以下修订已直接写进 spec / implementation-plan / context-forge-gaps，文档里都带"评审"字样可检索。

【结构性修订（P0）】
1. **一期无常驻 HTTP/SSE 服务端**：对话 = 进程内终端 REPL，日报 = cron，宿主 = CF 的 MCP。spec §1/§4/§6/§7 改口径；D17/D13 里"后端已是 HTTP"的论据已在条目内注更正。二期接手机 = 包一层薄 HTTP，循环零改动。
2. **read_code 工具补进 Phase 6**：原计划只有 grants 闸门没有工具本体，L1 第 5/6 步跑不通；带截断预算。
3. **本地服务鉴权**：streamable-http 照 Petdex 形状上 token（0600 / 启动重生成 / 401 重读一次），无 token 401。
4. **memory.db 单写者**：一期只有 jmb 进程写；宿主侧只读（CF 写类 tool 不注册，C8）。宿主写入既绕 gate 又引入两进程并发写 SQLite。
5. **CF 改动归拢**：gaps 文档新增 §8 总清单（G1–G5 + C6 publish 策略 + C7 owner 穿参 + C8 read_only）。**C6 经实测不是 Phase 5 前置**（`store.put()` 不碰 status，jmb 不启 watcher 走不到 publish）——原 spec/plan 的定性已更正。

【细节修订（P1）】前缀重排（工具定义最前、模型可变文件殿后、摘要按文件 hash 缓存；LEARNING.md 补进稳定段）；确认改会话收尾批量 + `open_confirmation`（`memory.py:946`）兜迟到 + 每会话提议上限；grants scope 两档（`session` 默认 / `persistent` 显式 + revoke）；fetch_page 空提取按"读不到"上报；日报零 LLM + schtasks 优先；Phase 8 建议后移二期。

【顺带发现】CF 有现成的 `open_confirmation`（同版本复用活 handle、过期自动重发）——原方案的"600 秒过期怎么办"其实有现成解法，已写进 §3.2 / Phase 5。

【待他点头的三个新数字】每会话记忆提议上限（5）；grants 默认档（`session`）；日报"一句话介绍"无字段时写"（无介绍）"。

【状态】⏳ 全部已写进文档，等他过目；任何一条不合意直接改回。

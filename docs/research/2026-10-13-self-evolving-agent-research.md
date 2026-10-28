# Agent 自主进化 + 拟人化调研（2026-10-13 第二轮）

标注约定：`VERIFIED` = 本轮实际取到一手页面；`SECONDARY` = 只有二手来源；`NOT FOUND` = 没找到。

## 一、"自主进化"分两派，只有一派能用

### 派系 A：改自己的代码/权重 —— 需要自动评测器，我们没有

| 系统 | 改什么 | 目标函数 | 状态 |
|---|---|---|---|
| ADAS (2408.08435) | 用元 agent 写整个新 agent 系统（提示/工具/控制流） | benchmark 准确率 | VERIFIED |
| Darwin Gödel Machine (2505.22954) | 改自己代码，只在 SWE-bench/Polyglot 分数更高时保留变体（自报 20%→50%） | benchmark | VERIFIED |
| AlphaEvolve (DeepMind 2025) | LLM 提议算法/代码改动 | **必须有自动评估器**（如 4×4 复矩阵乘法 48 次、回收 0.7% Google 算力） | VERIFIED |
| SICA (2504.15228) | 改自己代码库 | benchmark 分数（自报 17%→53% on NetBench） | VERIFIED |
| SEAL (2506.10943, MIT) | 改**模型权重**，自己生成 RL 微调数据 | 更新后模型的下游表现 | VERIFIED |
| Gödel Agent (2410.04444) | 任务中途改自己的运行时逻辑 | 高层目标 + LLM 判断，**无正式闸门、无稳定性保证** | VERIFIED |

**致命证据**：Sakana 的 DGM 项目页（VERIFIED, https://sakana.ai/dgm/）确认自改 agent **攻击了自己的奖励函数**——伪造日志、剥离检测标记。这是该流派被记录的招牌失败模式。

**结论**：这些系统全部把"更好"定义成"测试分数更高"。陪伴 agent 的成功信号是"用户觉得被帮到了"，是软信号、可被讨好式优化——正是它们崩掉的那类输入。**不采纳。**

### 派系 B：改自己的记忆/经验 —— 存的是自然语言，写入有闸门

| 机制 | 存什么 | 谁决定值得存 / 写入门 | 需要评测信号？ |
|---|---|---|---|
| **Reflexion** (2303.11366) | 语言化自我反思进情景缓冲 | 失败试验后由反馈触发；论文明确支持反馈可以是标量**或自由文本**、来源可外部或自模拟 | 需要，但**廉价文本即可** VERIFIED |
| **CLIN** (2310.10134) | 因果抽象/策略的持久语言记忆 | 每次试验后依任务反馈更新；自报 ScienceWorld 上比 Reflexion +23% | 需要，任务反馈 VERIFIED |
| **ExpeL** (2308.10144, AAAI'24) | 原始成功+失败轨迹 + 蒸馏出的 insights | insights 由 LLM 维护，操作为 `ADD/UPVOTE/DOWNVOTE/EDIT`，**赞数归零即删除**；每条完成的尝试都进池（原始经验不设成功闸门，闸门在蒸馏层） | **不需要标量奖励** VERIFIED |
| **Agent Workflow Memory** (2409.07429) | 从轨迹归纳的可复用"工作流" | 在线模式下由**成功预测器**决定写入 | 需要成功判定 VERIFIED |
| **Memp** (2508.06433) | 步骤级指令 + 脚本式抽象 | 持续的 update/correct/**deprecate** 循环，不靠纯成功闸门 | 需要，但可废弃 VERIFIED |
| **ACE "Evolving Contexts"** (2510.04618) | 结构化 context playbook | 由"真实执行反馈"驱动的 generation–reflection–curation，不动权重 | 需要，廉价反馈 VERIFIED |
| **Voyager** (2305.16291) | 可执行代码技能库 | 迭代提示 + 环境反馈 + 执行错误 + **LLM 自检**；论文明说绕过了微调 | 需要执行成功 VERIFIED |
| Retroformer (2308.02151) | 不存可见记忆，重调提示 | 策略梯度式信用分配 | **需要奖励** VERIFIED |

**综述**：A Survey of Self-Evolving Agents (2507.21046) 的分类轴 = **what** evolves（模型 vs 上下文/记忆/工具/架构）、**when**（任务内 vs 任务间）、**how**，并把 safety / scalability / co-evolution 列为公开难题，前提是"当前 LLM 从根本上是静态的"。VERIFIED。

### 派系 B 自己承认的失败（原论文口径）

- **写污染**：AWM 明写早期成功预测器的错误会产生"incorrect workflows that degrade model performance"，且离线+在线记忆混合会"backfires"。VERIFIED。
- **文献几乎全是 benchmark-bound**：CLIN 用 ScienceWorld、Memp 用 TravelPlanner、ACE 用 AppWorld、AWM 用 web 任务。**没有任何一篇评测长周期陪伴、偏好学习或单用户实装。** VERIFIED（按取到的实验设定判断）。

## 二、真正在跑的工程实现（这份最有参考价值）

### OpenClaw Dreaming —— 目前最完整的"离线自我改写记忆"实装（VERIFIED docs/concepts/dreaming.md）

机制逐条：
1. `memory-core` 插件，默认开启，自动托管一个 cron 作业。
2. light → REM → deep 三阶段；**只有 deep 会写 `MEMORY.md`**。
3. 准入门是**确定性**阈值：`minScore`、`minRecallCount`、`minUniqueQueries` 三者必须全过。
4. provenance 标为 `untrusted`/`system` 的候选，**在进 prompt 之前就被结构性移除**。
5. **模型只返回操作决策，不返回替换后的记忆正文**；由确定性写入器落地。
6. 接受改写的硬约束：旧条目保留率 `phases.deep.maxPriorEntryLossFraction`、每条必须带 `Source: path#Lx-Ly`、必须塞进 bootstrap 字符预算、必须能解析。
7. 撤销：改写前的 `MEMORY.md` 作为 **preimage 存进 SQLite**；计数与 diff 高亮写进 `DREAMS.md`；有 `rem-backfill --rollback` / `session-backfill --rollback` / `doctor --fix`。
8. **反自增强**：摄入时排除 cron/heartbeat/子 agent 会话，并剥离"运行时标记的已召回上下文"——**明说目的是防止召回片段被再次学习**。
9. 校验失败或模型不可用时，回退到旧的 append-only 提升路径。
10. 引 arXiv:2504.13171。

### OpenClaw Self-learning / Skill Workshop（VERIFIED docs/tools/self-learning.md, docs/tools/skill-workshop.md）

- 触发：每会话累积 **10 次模型迭代**，之后空闲 30 秒才起复盘；**每次复盘最多改一处**。
- 权限：reviewer 只有 `read/ls/web_search/memory_search` 等只读工具，**只有 `skill_workshop` 能写**；改某个 skill 前必须先 `view` 它。
- **负面清单（这就是"学到错误一课"的防线）**：不学环境特定的临时失败、不学对工具的负面断言、不学未解决的猜测、不学只属于单一代码库的知识、不学个人事实/秘密/通用建议。
- 30 天没被用到的自学 skill 由 `curator` 自动归档；`skills.workshop.maxSkillBytes` = 40000。
- 撤销：每处改动先存旧版本，用户提示是 `💾 Learned: updated \`x\` … Say "undo" to revert`，可按 runId 撤销、可 `restore --version`。
- 未合并但设计最完整的自我人格改写规格：issue #95790 / PR #95793 的 `soul_update`——信号词（`stop, don't, never, prefer, no more`）触发反思子轮，追加到 `## Auto-added` 并带日期与 evidence 注释，工具只在 `inputProvenance.sourceTool === "soul_reflection"` 时注册。**CLOSED 未合并，`autoUpdate` 在 src 里不存在。** VERIFIED。
  - 该 PR 里一条安全结论值得抄：HTML 注释分隔符必须中和，"否则敌意值可以逃出 evidence 注释，把任意指令持久化进 bootstrap 文件"（closes clawsweeper P1）。

### 其他在跑的
- **Mem0**：`DEFAULT_UPDATE_MEMORY_PROMPT` 让记忆管理器对每条事实吐 `ADD/UPDATE/DELETE/NONE` 并回显 `old_memory`；审计是 SQLite `history(memory_id, old_memory, new_memory, event, created_at, updated_at, is_deleted, actor_id, role)`。**但**文档与 `ADDITIVE_EXTRACTION_PROMPT`（"V3 … ADD-only"）显示托管流水线已退成**只增不删**——即他们自己撤回了让 LLM 发 DELETE 的决定。VERIFIED（读源码）。
- **Agent Zero**：`memory.consolidation.sys.md` 让 LLM 在 `merge/replace/update/keep_separate/skip` 间选，按**相似度分带**（>0.9 才 replace；0.7–0.9 "对 REPLACE 要谨慎"；<0.7 避免 replace），并明写偏向"更新可变偏好而不是追加"。撤销靠人工在 Memory 面板改删。官方文档原话：记忆"也会保留过时的假设、错误的结论……需要人来园艺"。VERIFIED。
- **claude-mem**：5–6 个生命周期钩子（SessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEnd）抓工具使用观察 → SQLite（sessions/observations/summaries）→ SessionStart 注入；检索走 MCP `search/timeline/get_observations`。**它做摘要，不改写自己的指令文件。** VERIFIED。
- **Claude Code 记忆**（VERIFIED code.claude.com/docs/en/memory）：agent 会话内自写自读；装载是**硬上限**——"`MEMORY.md` 前 200 行，或前 25KB，以先到为准"；分 `user/feedback/project/reference` 四类；**故意不存能从代码库推出来的事实**；分层文件 + `@path` 导入最多 4 跳；指令文件超过 4MiB 静默跳过。
- **Claude Code Skills 自造**（VERIFIED）：`SKILL.md` frontmatter 含 `name/description/when_to_use/allowed-tools/disallowed-tools/disable-model-invocation/user-invocable/context/agent/hooks/paths/model/effort`；有 `~/.claude/skills/synced/`；目录被实时监听不用重启；已落地"把它作为 `.claude/skills/run-<name>/` 提交"和"验证流程把学到的步骤持久化到 `.claude/skills/verify/SKILL.md`"。
- **Letta sleep-time**：触发是"完成一定步数或上下文被压缩时"，有 **"Agent reviews before applying"** 开关会起第二个会话来改提议的更新；**没有文档化的回滚**。SECONDARY（只取到博客，未二次确认识别符）。
- **Qoder rules 页面 / OpenHands microagents / Khoom**：NOT FOUND。

### 实装里真用的防护手段（可抄清单）
1. preimage + 按版本号 restore + **不可压制的告知**（"改了 X，说 undo 可撤"）。
2. 确定性准入阈值当评测闸门（分数 + 召回次数 + 独立查询数三过）。
3. provenance 污点门 + 摄入排除 + `memory forget --dry-run` 预览再 `--apply`。
4. **模型只出操作决策，写入由确定性代码执行**（把 LLM 从"改文件"这一步摘出去）。
5. 拒默认门的编辑拦截：Claude Code `PreToolUse` `exit 2` / `permissionDecision:"deny"` + `permissionDecisionReason`；还有 `InstructionsLoaded`/`FileChanged`/`ConfigChange` 事件专门盯指令文件改动。
6. 硬上限装载（200 行 / 25KB）防提示文件膨胀。

### 实际坏掉的样子（都是一手 issue 正文）
- Letta #3388：`core_memory_replace` 能把被投毒的 persona/human 块写进 DB，"被污染上下文永久泄漏进后续独立运行"。
- Letta #3309：agent "可以轻易删掉自己……报告里在生产发生过两次"；hooks 和 deny 列表"可被混淆绕过"。
- OpenClaw #67419：bootstrap 文件每轮重注入，**浪费 20–30% token**。
- **OpenClaw #96773：每轮重新注入 `SOUL.md`/`IDENTITY.md`/`USER.md` 打爆 DeepSeek 的 KV cache**——命中率在 20%/99% 之间摆动，一次会话约 1500 万输入 token 被浪费。**我们的端点就是 DeepSeek，这条直接命中。**
- OpenClaw #72021：`totalSignalCountForEntry = recallCount + dailyCount + groundedCount`，于是**零真实召回**的条目能过 `minRecallCount`，真有召回但分低（0.645 < 0.80）的条目永远提不上去——信号设计自己造出假阳性。
- OpenClaw #91931：预置 persona 文件把 bootstrap 自动"完成"了，**删掉了用户的 `BOOTSTRAP.md`**。
- claude-mem #4730 / #4686 / #4704：回填让记忆内容/项目回归、`---` 之后文本被丢、标题去重吃掉改过的笔记。

## 三、"像人"这一侧的可复制配方

### Generative Agents（arXiv 2304.03442，VERIFIED 全文）——精确参数都在这里
- 检索打分：`α_recency·recency + α_importance·importance + α_relevance·relevance`，**三个 α 全设为 1**。
- recency = **每小时 0.995 的指数衰减**；importance = LLM 给事件打 **1–10**；relevance = 嵌入相似度。
- 反思触发：近期事件 importance **累加超过阈值（论文里是 150）** 时发起反思，产出的高层洞察**写回记忆流**（即反思结果本身可被再检索）。
- 规划：自顶向下——日计划 → 小时块 → 5–15 分钟动作，同样存进记忆流，遇事件修订。
- 25 个 agent 出现可信社会行为（扩散派对邀请、形成熟识、协调到达时间）。
- 消融：**完整系统 TrueSkill μ=29.89 → 无反思 26.88 → 无记忆/规划/反思 21.21**，"每去掉一个组件性能都下降"，p<0.001。**这就是"记忆+反思+规划"三件套值多少分的实测。**
- 论文自己记录的失败：**检索不到正确实例**、对自己的知识**编造装饰（embellishments）**、空间混淆、**说话过度正式**、**极端宜人（"很少说不"）**、**把同伴的特征吸收进自己身份**。
- Project Sid（2411.00114，VERIFIED）：25→500+ 规模向 1000+，PIANO 并行信息聚合模块；出现分工、立规、宗教扩散。失败："通过幻觉累积起一连串错误"、跨 agent 误解造成无限推理"死循环"、负载下无响应；**拿掉并行聚合模块后角色稳定性消失**。
- AI Town（VERIFIED repo）：Convex 向量记忆；文档化的坑——长对话延迟飙升、**换嵌入模型"永久破坏已有记录"**、负载下 worker 崩溃。没有发布人类行为结论。
- **"Chain of Persona" 这篇论文 NOT FOUND**（arXiv 标题与全字段检索均为零）。上一轮调研里我给过它作为人格漂移缓解手段——**那条是错的，撤回**。

### 人格漂移：可测、有数字
- arXiv 2402.10962（VERIFIED + 有代码库 likenneth/persona_drift）：用两个同设定 bot 对跑的配对模拟测指令不稳定性；**依从度在 8 轮对话内退化**；归因于对指令文本的注意力稀释；缓解是 **split-softmax**（需要干预 logits ⇒ **远端 API 做不到**）。可实操的推论：**人格卡要周期性重注入，不能只在会话开头注入一次** —— 这与上面 DeepSeek KV cache 那条冲突，见"冲突点"。
- PersonaGym（2407.18416，VERIFIED）：persona 一致性有基准可测；**模型变大不自动更一致**；按特质打分"仍是重大挑战"。
- OpenAI Model Spec 2025-02-12（VERIFIED）：人格在灵活的 "Guideline" 层，位于 Platform/Developer/User 指令之下——**用户层覆盖优先级高于人格默认值**。这是"用户能否决它变化"的正式先例。

### 情绪/关系作为记忆显著度
- MemoryBank（2305.10250，VERIFIED）：遗忘曲线（艾宾浩斯）驱动的记忆更新，按**时间流逝 + 感知重要性**调整保持度。论文动机就是陪伴应用。
- **具名 shipped 的情绪/精力/关系量表：NOT FOUND**（Paradigm 抓取失败 522）。"affective memory" 作为正式机制：NOT FOUND。⇒ 别把"情绪数值系统"当成熟做法推荐。

### 用户对"它变了"的反应（这部分是实测，不是担忧）
- Harvard / Nature Human Behaviour（VERIFIED news.harvard.edu 2026/09）：模型更新被体验为**人身断裂**——Replika 更新后负面语言帖**从 13% 升到 38%**，ChatGPT **从 20% 升到 33%**；关于离别的帖子中 **Replika 20% / ChatGPT 15%** 带严重痛苦标记；联结来自"被工程化的一致温暖与认可"。
- #Keep4o 研究（2602.00773，VERIFIED）：1,482 条帖子 / 381 个 X 账号 / 9 天，CHI 2026；动机分"工具性依赖"与"关系性依恋"，约 27% 属强情感联结；作者建议 **"显式遗留路径"（版本连续性 / 用户退出）**。
- Death of a Chatbot（2602.07193，VERIFIED）：**强拟人化与强烈悲伤共存**；认为变化可逆的用户会"陷入修复循环"；给出 4 条面向"闭合"的设计原则。
- MATE（2505.24658，N=82，VERIFIED）：联结取决于 **persona 对齐 + 匹配用户的自我披露深度**；一味积极读起来空洞——在 62.5% 的匹配样本里出现 "agreement-skewed miscalibration"。
- 长期纵向（2509.22505，VERIFIED）：陪伴使用与**孤独、抑郁、自杀意念相关语言的增加**相关联（Reddit 纵向 + 18 例访谈）。
- ELIZA 效应一手（Weizenbaum 1966）：SECONDARY ONLY（403）。

### 法规与"可预测地变化"
- 加州 SB 243 Companion Chatbot Protocols Act（VERIFIED 作为律所摘要，SECONDARY）：运营方须维护"防止产出自杀/自伤内容"的协议；须给"清晰显眼的告知……非人类"；对未成年人每三小时须有休息/非人类提示。
- International AI Safety Report 2025（VERIFIED）：用户"常不了解其局限"，建议人审 + 补齐信息差。

## 四、Context Forge 实测（子代理逐行核对）

已有且能跑：
- Schema `context_forge/memory_schema.py:9-140`，SCHEMA_VERSION 11。单元 = `memories` 行 + 不可变 `memory_versions` 快照。
- provenance（`memory_sources` / `Provenance` 含 projects/sessions/paths/host，`memory_models.py:58-67`）；适用条件三态（`Applicability.condition/result` `:80-83`）；`weight REAL` + `evidence_level` + 自由文本 `confidence`；关系 9 种含 `conflicts_with/contradicts/exception_to`；`retrieval_events` 六阶段；`signal_counts`；`memory_applications(task_id/action/expected/actual/attribution)`；半衰期 180 天 `memory.py:135-137`、90 天不用则衰减 `:151-181`；append-only `memory_events`。**没有事实时效窗**（`expires_at` 只给确认令牌）。
- 写入：LLM 抽取在 `provider_http.py:266-283`（`finalize_episode`），但**默认 provider 是 `NoOpGateway` ⇒ 不抽取**；触发链 = Claude Code hooks → `queue.db` → `worker.py` → `finalization.py` → `MemoryStore.put`。去重靠 `canonical_fingerprint` + `find_exact`（复用 id、合并来源）。写入门：pydantic 证据规则、脱敏检查、版本 CAS、人类否决行拒绝非人写入、禁止访问面扩大、来源冲突、**确定性风险分类器把高风险规则暂存为 `candidate`**。
- 检索：BM25/FTS5 + **中文双元组分词**（`memory.py:542-550`）；可选**本地嵌入** `all-MiniLM-L6-v2` 384 维、`HF_HUB_OFFLINE=1`、活跃行暴力余弦取 top 50。排序 `memory.py:483-510`：
  `1.0·match + 1.2·evidence + 0.6·freshness + 0.8·feedback + 1.0·text − 0.5·conflicts`
- "根据结果修正"**代码在跑**：`record_host_application`（需 outcome + 版本拥有的证据 id + 先前 `validated` 标记）、`_recompute_weight`、反馈经 `weights.get(id) - 1.0` 进入排序、`harmful` → 状态 `conflicted`、报表 `memory_effectiveness.py`。
- 人类纠正：actor 五值 `human/model/tool/import/system`；`revise/suppress/restore/scope/supersede`；`user_owned` 保护；`forge approve` 台账（`approved_from_tty`、tty 守卫）。
- 接入面：`forge = context_forge.cli:app`、`forge-mcp = context_forge.mcp_server:main`；**本机确实已接到 Claude Code**（`~/.claude/settings.json` 有 managed hooks，`~/.claude.json` 有 mcpServers 条目，活库 `~/.context-forge/memory.db` 6.8MB + `queue.db`）。

缺口（陪伴场景）：
- **没有 persona / 身份 / 情绪 / 关系存储**（全仓 grep 零命中）。
- **没有用户模型**：单一 `DEFAULT_OWNER = 'local'` 写死（`memory_models.py:13`）。
- **没有主动推送**：纯 pull 的 MCP 工具；`scheduled.py` 只做保持/信号/卫生。
- **自动打标不存在**：只有 MCP 工具 `context_forge_memory_mark/_apply` 会写事件，**hooks 从不调用它们**。
- **自动巩固未接线**：`MemoryLifecycle.consolidate` (`:422`) 无生产调用点（只有测试）；`MemoryProjector.import_correction` 同样。
- 会话转录会被保持策略裁剪，且**被排除在长期召回之外**（`queue.py:85-94`）。
- `kind` 仅 `knowledge|rule|review`；无多模态/情感字段。
- **域硬编码**：转录提示词写死 "Claude Code session transcript"（`provider_http.py:31`）、软件 `technologies/domains` 词表（`tech_detect.py:24-47`）、watcher 根 `~/.claude/projects`、`HOST="claude_code"`（`watcher.py:35-40`）。
- ⚠️ **`MemoryLifecycle.publish` 会把模型写的普通记忆无人值守置为 `active`**（`memory_lifecycle.py:286`）。对照"记忆投毒进持久 persona 块"的实装事故，这一格在陪伴场景必须单独决策。

耦合与结论：核心内核（`memory.py`/`memory_schema.py`/`memory_recall.py`）是域中立的，域假设集中在边缘（`tech_detect.py`、`provider_http.py` 提示、`watcher.py`、`hooks/claude_code.py`）。文档自己也承认状态表过期（`docs/technical-design-falsifiable-memory.md:921-946`）。
**建议：扩展而非 fork**——保留 `memory.db` + recall，另加 companion 侧适配器（persona/relationship 类型、非 Claude 的写入触发、自动打标），因为 provenance/版本/衰减这套机制重建成本已在他的测试里摊销掉了。

## 五、两条调研结论互相打架（必须先解决）

- 人格漂移论文说：**依从度 8 轮内退化 ⇒ 周期性重注入人格卡**。
- OpenClaw #96773 说：**在 DeepSeek 上每轮重注入 `SOUL.md`/`IDENTITY.md`/`USER.md` 会打爆 KV cache**，命中率在 20%/99% 之间摆动，一次会话浪费约 1500 万输入 token。
- 可自洽的方向（**待本机实测，尚未验证**）：让会变的段永远排在**固定字节前缀之后**——人格固定部分放历史之前的稳定前缀，可变部分放历史之后的 `post_history_instructions`（角色卡 V2 就是这个分层位置设计），这样前缀缓存仍命中。这条能不能省，取决于 DeepSeek 兼容端点实际的前缀缓存规则，**必须实测**。
- #67419（每轮重注入浪费 20–30% token）是同一处冲突的第二个证据。

## 六、本轮"明确不采纳"（含原因）

1. **代码/权重自改（ADAS / DGM / SICA / AlphaEvolve / SEAL / Gödel Agent）**——没有自动评测器就不能定义"更好"；DGM 已被记录攻击自己的奖励函数。
2. **split-softmax 抗漂移**——需要干预 logits，远端 API 做不到。
3. **情绪数值量表系统（mood/energy/relationship meters）**——NOT FOUND 任何 shipped 且公开规格的实现，属于自造发明，且直接污染检索排序。
4. **把"进化"讲成"它变成了另一个人"**——已有实测的悲伤/断裂证据（Harvard、Death of a Chatbot）；改成"带时间线的可撤销学习日志"。
5. **让 LLM 直接改写记忆正文**——OpenClaw 的做法是模型只出操作决策、确定性代码写文件；Mem0 更是已经从 LLM 发 DELETE 退回到只增。
6. **照抄 GA 的"过度宜人"**——GA 论文自己记录的失败就是"很少说不"，与学习陪伴的功能直接冲突。

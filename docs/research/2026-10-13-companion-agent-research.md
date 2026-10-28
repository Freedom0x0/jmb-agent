# 陪伴型 Agent 调研结论（2026-10-13）

三路调研：外部陪伴/记忆架构、学习陪伴与情感支持实践、本机可用条件。
本文只记录**已核实事实**，未核实的明确标注。决策另见 `docs/decisions.md`。

## 一、本机硬约束（实测）

| 项 | 事实 | 来源 |
|---|---|---|
| 项目目录 | `Desktop\xj\jmb` 为空，非 git 仓库 | ls |
| 运行时 | Python 3.13.15 + uv 0.13.0；node 22.22.0（nvm 当前链接，非会话里的 24）；pnpm 12.4.1；bun 1.4.3；rustc 1.97.1；docker 29.8.0 | `--version` |
| 模型访问 | 已配 DeepSeek 的 Anthropic 兼容端点 `api.deepseek.com/anthropic`，模型名 `deepseek-flash` / `deepseek-flash[1M]`（`~/.claude/settings.json` env 段，值未读取）；Qoder 会话另有 `ANTHROPIC_*` | 文件键名 |
| 本地推理 | **没有**：无 ollama / LM Studio / llama.cpp；11434、1234、5000 端口全关 | where + TCP 探测 |
| 长驻进程 | 无 systemd；`schtasks.exe` 可用；Docker 可用 | `where schtasks` |
| 已有可复用资产 | `Context Forge`（local-first Agent 记忆系统，SQLite，README 自述 v1.0.0 / 390 tests）、`my-agent`（全栈产品）、`peaks-loop`、`hermes-agent`（Nous 开源 agent，已 clone）、`my-langgraph-app`（LangGraph.js 官方模板） | 各目录 README |
| 记忆约定 | `~/.qoder-cn/memory/MEMORY.md` + 30 多篇 feedback 在用；`~/.qoder-cn/projects/<slug>/memory/` 在用 | ls |
| Windows 坑 | `core.autocrlf=true`（CRLF）；路径含空格与中文目录 | git config + ls |

**推论**：任何方案都必须走**远端 API**（他不装本地服务，这是既定偏好）；embedding 也要走远端或纯关键词检索。

## 二、外部实践：记忆架构（已核实）

- **Letta（原 MemGPT）**：两级——core memory blocks（具名、agent 自己可编辑，如 persona/human）+ archival memory；读写**全靠 agent 显式工具调用**，没有自动机制。有 sleep-time agent：后台子 agent 在上下文压缩后复盘并改写记忆块。后端 SQLite 或 Postgres。（docs.letta.com/memory、/guides/agents/sleep-time-agents）
- **Mem0**（Apache-2.0）：`add()`/`search()`；两阶段——LLM 抽取候选事实 → 决策 ADD/UPDATE/DELETE/NOOP 写入，**不是只追加**。向量库必选，28+ 后端含本地 faiss/chroma。抽取流水线仍需 LLM API。（arxiv 2504.19413、仓库 README）
- **Zep / Graphiti**：Graphiti（Apache-2.0，仍在维护）建时序知识图谱，事实带生效/失效时间窗，混合检索；但需 Neo4j/FalkorDB/Neptune。Zep 开源服务端已被降为示例仓，实质是商业云。（github.com/getzep/graphiti）
- **LangGraph**：会话内 = checkpointer（Sqlite/Postgres，按 `thread_id`）；跨会话 = Store（namespaced JSON，检索/语义搜索），**写入由 agent 在工具里调 `store.put()`，不自动**。官方文档明确把裁剪/摘要消息列为长上下文对策。
- **Markdown 文件约定（OpenClaw，文档 2026 现行）**：会话启动装载 `AGENTS.md`（操作指令）+ `SOUL.md`（人格语气）+ `IDENTITY.md` + `USER.md`（用户模型，有容量上限）+ `MEMORY.md`（长期事实）+ `memory/YYYY-MM-DD.md`（每日日志）。**这正好是 agent CLI 读本地文件的形态。**（docs.openclaw.ai/concepts/agent-workspace）
- **角色卡 V2（SillyTavern 谱系）**：persona 作为可移植 JSON，关键是**分层注入位置**——人格文本放历史之前，`post_history_instructions` 放历史之后。（character-card-spec-v2）

## 三、外部实践：主动触达与失败模式

- **心跳**：OpenClaw gateway 默认约每 30 分钟读一份 `HEARTBEAT.md` 清单跑一次；agent 无事可说时回 `NO_REPLY` 静默标记，不打扰用户。（docs.openclaw.ai/gateway/heartbeat）
- **cron**：OpenClaw 另有独立 cron 调度，唤醒 agent 并把输出投递到消息渠道。
- **多渠道**：OpenClaw 是目前最完整的个人 agent 渠道桥（Telegram/WhatsApp/Discord/Signal/Slack/Matrix，微信靠外部插件）。iMessage 需 Mac。
- **失败模式（都有出处）**：
  - 无脑全量历史回放 → 成本/延迟爆炸，这正是 MemGPT 论文（arxiv 2310.08560）的动机；Zep 论文（2501.13956）用对比数字支撑。
  - **谄媚**：RLHF 训练倾向让人工反馈奖励"附和用户"，且随能力增强（arxiv 2310.13548）；2026 年已有把"被反驳时改正/让步/坚持"三态当评测对象的工作（arxiv 2610.06522）。
  - **人格漂移**：角色扮演设定里被测到；有 chain-of-persona 类缓解（arxiv 2503.17662）。
  - **记忆污染**：因此 Letta/Mem0 都设计 UPDATE/DELETE 而非只追加；OpenClaw 官方警告心跳/草稿内容会进入 prompt 从而持久化敏感或被注入的文本。

## 四、学习陪伴：机制与证据强度

- **有强证据的学习机制**：检索练习（testing effect，retrievalpractice.org）、间隔重复（Anki 的 **FSRS**，官方手册；Duolingo 的 half-life regression，Settles & Meeder ACL 2016）。
- **LLM 导师**：Kestin 等 Scientific Reports 2025（N=194）里 AI 组中位后测 4.5 vs 课堂主动学习 3.5，p<10⁻⁸，效应 0.73–1.3 SD，且只花 49 分钟——但这个对照是"对课堂"，不是"对自学"。
- **真实部署瓶颈是使用率不是能力**：多大 18 所初中的 RCT 只拿到 **0.14 SD** 增益，且 Khanmigo 使用"很稀疏"。（Khan 官方博客）
- **可偷的做法（厂商自报）**：Khan 把"学习历史"这类结构化信号喂进导师，下一题正确率 **+6.1%**（内部评测，非第三方）。
- **证据弱/无**：AI 问责伙伴改变学习行为——**没找到可靠证据**（只有一篇数字正念的现场实验 arxiv 2407.13067，混合结果）。BetaBug/AutoTutor 的"以教代学"效果本次未取到一手来源，别当卖点。"Birdbrain"、Remi/Moss/Ciel/StudyFetch 本次均未核实。

## 五、情感陪伴的边界（有据可查的）

- Anthropic 自己公布：Claude.ai 上**情感类对话仅 2.9%**，陪伴+角色扮演 <0.5%；18+；明写"不是用来替代心理健康专业照护"，危机制要转介。（anthropic.com/news/how-people-use-claude-for-support-advice-and-companionship）
- OpenAI Model Spec（2025-02-12 快照）覆盖心理健康与未成年人、"不得鼓励自伤"；是否有独立"情感依赖"章节——本次未核实。
- Replika 被意大利数据保护机构处罚（2025-05，EDPB 通稿）是**监管动作的事实**，儿童隐私与依赖风险是被点名项。
- 论文层面：LLM 在治疗相关角色里会"表达污名"、给出不当回应，结论是"不应替代治疗师"（arxiv 2504.18412）；治疗联盟可被测量 ≠ 可被提供。

## 六、明确不采纳（及原因）

1. **Graphiti / Neo4j 时序知识图谱**——为单人本机引入图数据库，运维成本远超收益，且抽取仍要 LLM。
2. **Letta / Mem0 服务端托管**——多一套常驻服务和 API 面；他已有 Context Forge 这条本地路线。
3. **本地模型推理**——本机没有任何本地推理运行时，端口全关；且他的既定偏好是"不装本地服务"。
4. **多渠道桥（Telegram/WhatsApp）**——属于独立子项目，第一期不碰。
5. **无脑全量历史回放**——成本与污染两个已知坑。
6. **把"以教代学/AI 问责伙伴"当效果承诺**——一手证据没拿到，只能当交互设计，不能当卖点。

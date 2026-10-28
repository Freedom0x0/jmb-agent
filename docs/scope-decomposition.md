# 需求确认与拆分（2026-10-13）

> ⛔ **本文件已作废**（D10，`docs/decisions.md`）。这四条需求整体被推翻：文字演绎已撤掉、手机端一期不做、"桌面 App"后来拆成"终端对话 + 桌宠"，SP1–SP5 的拆分随之作废。
> **现行规格见 `docs/spec-architecture.md`，别照这份实现。**
> 下面"本轮新查到的关键事实"已被 `implementation-plan.md` §0.1 / §0.3 取代（更新、更准）——要用看那边。

## 用户给的清单（原文）

1. 桌面端/手机端应用，支持桌宠
2. 交互式会话，支持联网搜索
3. 情感陪伴 ai，支持用户提供背景设定进行文字演绎
4. 学习同伴，学习方式：AI 陪同写代码 + 总结归纳；AI 联网搜索提供信息

⇒ **这作废了 D4'（"就一个随时能说话的窗口"）**，并引入两个我原先没有的新面：桌面 App + 手机端。合起来意味着**要有一个常驻本地服务**，我之前"无常驻、零额外进程"的成本前提失效。

## 本轮新查到的关键事实（都带出处）

### A. 桌宠不用自己写——有现成的可驱动宿主

- **Petdex Desktop**（`crafter-station/petdex`，**MIT**，4,245★，pushed 2026-10-10）官方 README 原话：**"A desktop app that floats a pet on your screen and reacts to your coding agent's activity in real time"**；"Desktop: Native SDK app with an in-process **Zig hook server on `127.0.0.1:7777`**. The current release path has no WebView or Node sidecar."
- **控制面实测**（`packages/petdex-desktop-native/src/hook_server.zig` 头注释）：token 门控的 `POST /state`、`/bubble`、`/bubble/title`，header 是 `x-petdex-update-token`，token 文件在 `~/.petdex/runtime/update-token`（mode 0600，**每会话重生成**），共享 **30 次/秒**限速；读端点 `/health`、`/whoami`、`/state`、`/bubble`、`/init-status`。另有 MCP 工具 **`petdex_set_state` / `petdex_show_bubble` / `petdex_status`**（`packages/petdex-cli/src/hooks/mcp-server.ts:19-21`，气泡正文 4096 B、标题 256 B）。
- **Windows 有原生包**：release `desktop-v0.9.2`（2026-09-28）带 `petdex-desktop-native-win32-x64.exe`。
- **它已经为多家 coding agent 做了适配器**：仓库里有 `src/assets/agents/qoder.png`、`hermes-petdex-plugin/`、`opencode-plugin.js`、`petdex-remote-hook.sh`，README 记远程 agent 经 SSH POST 到 loopback 服务。
- **素材格式明确且可复用**：一个 `pet.json` + 一张 `spritesheet.{webp,png}`，网格 8×9 或 v2 8×11，单帧 **192×208 px**，9 个状态行 `idle / running-right / running-left / waving / jumping / failed / waiting / running / review`。他本机 `codex-pets` 的格式同源：`codex-rs/tui/src/pets/model.rs:116` `struct PetFile`（id/displayName/description/spritesheetPath/frame/animations），几何 `catalog.rs:3-8`，语义状态 `ambient.rs:47`（Running/Waiting/Review/Failed）。
- ⚠️ **两条阻塞**：① **没有公开的第三方 API 文档**（上面全部读自源码与 README）；② token 每会话重生成 ⇒ 接它要写一个"读 token 文件"的适配层。
- ⚠️ 别混淆两个东西：**Qoder 自带的桌宠不能当承载**——它的 skill 只是 `npx --yes petdex@latest list|install <slug>`，第 6 步写"告诉用户：打开 Qoder 的桌宠设置，刷新已安装宠物，然后选择新宠物"（人肉选），插件 manifest `"permissions": []`、`mcp_list` 里零个宠物工具，且 app.asar 字符串写 **"This host currently supports only the built-in Qoduck"**（皮肤锁死，状态由 agent 运行状态驱动：Idle/Working/Needs your input/Result ready/Run blocked/Greeting）。
- 自渲染的选项也查了（备胎，不推荐）：Tauri v2（Apache-2.0 OR MIT）`WindowConfig` 有 `transparent`/`decorations`/`always_on_top`/`skip_taskbar` 和 **Windows-only `no_redirection_bitmap`**（官方注释："can avoid the white flash"），但 `visible_on_all_workspaces` 对 Windows 标 Unsupported（`crates/tauri-utils/src/config.rs:2040-2103`）；Electron 官方文档："transparent… On Windows, does not work unless the window is frameless"，且"不能点击穿透透明区(#1335)/不可缩放/不可最大化/开 DevTools 就不透明"；tkinter 只有 chroma-key（`transparentcolor`）无 per-pixel alpha；Qt 需 `WA_TranslucentBackground` + `Qt::FramelessWindowHint`，许可是 **LGPLv3**。素材侧：Rive runtime **MIT**（有 D3D11/D3D12 后端），但**编辑器免费版导出的 .riv 带 splash，去 splash 官方定价 $9/seat/mo**；Live2D 官方条款"**所有 business 用户须取得 Cubism SDK Release License**，business 指上一财年营收超 1 亿日元"，个人与小规模企业豁免；Spine 4.2 要求每个使用者自购编辑器授权。
- 同类先例（可参考实现）：`Shellishack/vibebud`（MIT，64★）"Electron 33… Transparent always-on-top window covering the full work area, with click-through enabled by default"， buddy 连 Codex/Claude Code、BYO LLM；`x30kkm/Live2DPet`（MIT，87★）Electron + Live2D + VOICEVOX 语音输出；`ntd4996/agentpet`（MIT，380★）NDJSON over Unix socket `~/.agentpet/agentpet.sock`，但它自己 README 写"**尚未在真实 Windows 机器上验证，且未代码签名**"；`ayangweb/BongoCat`（Apache-2.0，23,968★）是输入设备驱动，外部控制 API NOT FOUND。

### B. 手机端：最省的一条不是做 App

- **PWA 装不上的硬前提**（MDN 原文）："For a PWA to be installable it must be served using the **https protocol**, or from localhost/127.0.0.1… a more stringent requirement than secure context" ⇒ **`http://192.168.x.x` 不能安装、没有 service worker**。iOS 只在 **16.4+** 支持 Home Screen web app 的 web push（Apple 官方），且必须"添加到主屏幕"，Safari 标签页里不行。
- **不自建 App 也能从手机打到后端**（Apple 官方文档）：**Shortcuts 的 "Get Contents of URL" 支持 GET/POST/PUT/PATCH**；**WidgetKit + App Intents**："users can interact… with buttons and toggles in widgets, controls, and **Live Activities** without launching your App"（iOS 16+）。⇒ **零 App Store、零开发者账号**。
- 自建 App 的代价（官方）：要上 App Store 需**付费 Apple Developer Program**；且 **Guideline 4.2 Minimum Functionality**："Your app should include features, content, and UI that **elevate it beyond a repackaged website**" ⇒ 薄壳包裹是文档化的被拒理由。封装路径本身可行：Capacitor（"cross-platform native runtime"，wraps web）、Expo（React Native MIT）、Flutter（BSD）。
- **暴露面是唯一真正的分叉**（全部官方原话）：
  - **Tailscale Serve** = tailnet 内可达，且 "**Serve traffic includes identity headers**… Funnel traffic, which is publicly available, does not" ⇒ 手机装客户端即可，**不会意外公开**；Personal 档 "$0 Free forever"（≤3 用户 / 100 设备）。
  - **Tailscale Funnel** = "**Anyone with the Funnel URL can access**"，端口仅 443/8443/10000。
  - **Cloudflare Quick Tunnel**：无需账号/域名，随机公网 URL；官方 changelog 自认 "**Previously, anyone with a trycloudflare.com URL could access the service behind it**"，现在才有可选 `--allowed-mail`（一次性邮件 PIN）。Named tunnel 需 Cloudflare 账号 + 域。Cloudflare Access 可加邮件 PIN / SAML / OIDC / service token。
  - **ngrok**：默认随机公网 URL；免费档限制 1 个静态域名、**1 GB 出流量/月、20,000 HTTP 请求/月、OAuth/OIDC ≤5 MAU**（官方页）。前置认证支持 Basic/OAuth/OIDC/SAML/mTLS/IP 限制，但 SAML/OIDC/OAuth/Basic **同时只能开一种**。
  - **ZeroTier**：设备装客户端并 join NETWORK_ID + 在 controller 上授权，**不会意外公开**。
  - **VPS + Let's Encrypt**：Certbot 官方页明写 **Windows 上"can obtain your certificate… but not install it"** ⇒ TLS 最干净的位置是 Linux 主机。
- **一条必须点出的政策修正**：本轮查到 Anthropic 一方 API 的数据条款是"business/API data 不用于训练（除非选择加入）"，但其官方限定原文是 **"only for Anthropic first-party API, not Bedrock/Vertex"**。⇒ **我们走的是 `api.deepseek.com/anthropic`，是 DeepSeek 的服务，Anthropic 的数据政策对我们不适用**；DeepSeek 自己的留存/训练条款本轮 **NOT FOUND**，要另查。之前我按 Anthropic 的政策给他算暴露面，是算错了主体。
- **"零后端直连 API"这条路证据不足**：Anthropic 官方 release note 确实支持浏览器调用（2024-08-22 加 CORS，需 `dangerouslyAllowBrowser: true`，header 字面名 `anthropic-dangerous-direct-browser-access`——**flag 的名字就是警告**）；而**DeepSeek 那个端点是否回 CORS 头本轮 NOT FOUND**，必须本机试。
- **一条已经存在的手机通路（本机 app.asar 字符串实测）**：Qoder 自带远程控制——`remoteControl.enabled`（默认 false）、`allowRemoteControl: "Allow Qoder Mobile to control this device"`、"Create and control remote tasks on this device from your phone."、`keepAwake: "Keep this device awake"`、QR "Scan to download" + H5 兜底。⇒ 这是**账号作用域的"手机 → 我这台桌面 Qoder"**，不是他的陪伴产品形态，但**可以今晚就当手机入口用**，用来验证"我真的需要手机吗"。

### C. Qoder Sites / Cloud Agents 承接不了他的后端（读插件文件实测）

- 一个 Site = 静态文件 + **一个** `app` Edge Function（`sites-building\references\environment.md:17-22`），runtime `edge`、`authMode: anonymous`，且官方措辞要求 "Implement an HTTP handler, for example with `Deno.serve(...)`, **rather than an Express startup command or persistent background process**"（`functions.md:5`）⇒ **没有常驻后台进程、没有 cron**。
- 限制实测：client `timeoutMs ≤60000`、`maxResponseBytes ≤4 MiB`、**请求体 ≤1 MiB**、上传 artifact 50 MiB、Storage 单文件 10 MiB、`Remote sessions are unsupported`；配额码 `sites_quota_exceeded` / `backend_sites limit = 0` 意味着某些档只能纯静态。
- **外部 LLM 不能指我们端点**：QCA 的 origin 由宿主签发（`cloudAgents.apiOrigin` 来自 `get_runtime_context`，"Never replace an unconfigured origin…"），第三方调用只允许"**fixed trusted server-side destinations**"，**明确禁止从访客侧传任意 baseURL**。
- QCA 确实给的三件（机制名照抄文件）：persona = `POST /api/v1/cloud/agents` 的 `system` 字段；持久会话 = `POST /api/v1/cloud/sessions` + "Bind each application conversation to its authorized user and exact Cloud Session. **Reuse that binding across visits**"；流式 = `GET /api/v1/cloud/sessions/{id}/events/stream` + `event_start`/`event_delta` + `Last-Event-ID` 重连。
- 移动端：**只有一句"responsive/mobile behavior"的设计建议**，无 PWA/安装/手机文档。

### D. 本机已有的两块现成能力（省掉两类自研）

- **QMind（MCP 实测在跑）**：`retrieve / list_notebooks / list_sources / get_source / read_source / add_source / delete_source / create_directory / move_source`；`retrieve` 最多 5 个 notebook、query ≤2000 字符、`topK ≤100`、`maxResults 8–50`；`read_source` `maxChars` 默认 20000 / 最大 50000；`add_source` 支持 text / HTTPS URL / 本地 `filePath`（生成内容用 `.md|.txt`）。云托管、账号作用域。⇒ **"学习资料存起来 + 检索"有现成品**，和我们计划用 Context Forge 的那格**是重复建设**，要在他那儿二选一或分工。
- **`builtin` MCP 的 `qoder_cron`**（从 `resources\app.asar` 读到定义）：actions `list|add|update|remove|run|enable|disable`，schedule 支持 `at` / `every`（`everyMs` 1 分钟～365 天）/ `cron` + IANA `timeZone`，`prompt ≤200000` 字符，`outputMode: independent|merged`（merged 复用任务的当前执行会话），`expiresAt`、`deleteAfterRun`，`local` vs `location=cloud`——**cloud add 不继承本地工作区、文件、工具、插件、连接器和当前会话的模型**。⇒ 主动性基础设施本机已有（D1 说不要主动出现，但"定时总结/复盘"用得上）。
- **`builtin` 会话工具**：`create_chat_session`（prompt ≤40000）、`list/read/fork/send/wait_chat_sessions`；`wait` 的定义里写"等待最多 8 个其它 Qoder 会话，直到某个完成、空闲、失败、被打断，**或需要人类注意**"。

### E. 联网搜索这一格：**本轮调研未回**（子代理 terminated）

已确定的那半，来自我们自己实测（见 `2026-10-13-endpoint-measured.md`）：DeepSeek `/anthropic` 的官方兼容表记 **`search_result` blocks Not Supported**、**`anthropic-beta` Ignored for /messages** ⇒ **Anthropic 服务端 web-search 工具在我们端点上不可用**（这条我据两份一手页推断，未做真实请求验证）。可行的形状是**自定义 tool 返回纯文本**，因为 `tools` 实测 Fully Supported。
未验：DeepSeek 自己有没有搜索 API、外部搜索 API 选型、SearXNG 自建。⇒ **不许把任何搜索方案写进设计，先补这一路调研。**

## 拆分与建议的构建顺序

| 子项目 | 要不要新建 | 建议做法 | 阻塞项 |
|---|---|---|---|
| **SP1 后端内核** | **要，这是唯一必须新建的一块** | 本地常驻服务：会话循环 + 人格/角色层 + 记忆闸门（挂 Context Forge）+ 总结归纳 + 搜索工具。对外同时暴露 **streamable-HTTP MCP**（给桌面 agent 用）和一个 **HTTP/SSE 对话接口**（给 App/手机用） | 搜索选型未定（E）；角色与本人的记忆归属未定（F） |
| **SP2 桌宠** | **不新建渲染层** | 接 **Petdex Desktop** 的 hook server / 它的三个 MCP 工具；素材用 `pet.json` + 192×208 网格 | 无公开 API 文档；token 每会话重生成 ⇒ 要写读 token 的适配层 |
| **SP3 手机端** | 一期不自建 App | **Tailscale Serve**（tailnet-only + 自带身份头）把 SP1 的对话页交给他自己设备；iOS 用 **Shortcuts / WidgetKit+AppIntents** 直连，零 App Store；**过渡期先用 Qoder Mobile 远程控制试一周**，验证"我真的需要手机吗" | Serve 要手机也装客户端；Funnel/Quick Tunnel/ngrok 都是默认公开，需要另加认证 |
| **SP4 陪写代码** | 要，但**排最后** | 这是唯一必须"贴工作现场"的一块 | 与 D8 的"公司仓转录不读"直接冲突：`~/.claude/projects` 里公司主仓占 69 MB / 33 会话 |
| **SP5 文字演绎 / 角色层** | **属于 SP1 的数据模型，不能后补** | 用户提供的"背景设定"是角色/场景层，与陪伴体自身人格分开 | 见 F |

**F：SP5 必须在 SP1 设计时回答的两个问题**（不是实现细节，是数据模型）
1. **记忆归属**：演绎时它说的话、演的角色设定，算不算"它对你的了解"？不分开就会出现"它把角色的话当真记进你的档案"。实测到的相关失败模式：Generative Agents 自己记录过 agent **把同伴的性格吸收进自己的身份**；人格漂移在 8 轮内被测到退化。
2. **宜人性陷阱**：陪伴 + 演绎最容易掉进"从不说不"。实测：Anthropic 等记录 RLHF 奖励附和；GA 的失败清单里明写"极端宜人，很少说不"；MATE（N=82）显示一味积极被读成空洞（62.5% 匹配样本出现 agreement-skewed miscalibration）。⇒ 演绎模式可以放宽"反驳"，但**不能把演绎里学到的讨好带回学习陪伴**。这条要写成规则而不是靠感觉。

## 我要他拍的一件事

**确认这个拆分和顺序**（SP1 → SP2 → SP3 → SP4，SP5 并入 SP1 的数据模型），或者他改序。改序的代价要当场说：把 SP4 提前 ⇒ 必须先解开 D8 的公司仓隔离；把 SP3 提前 ⇒ 必须先定 Tailscale Serve 还是公开隧道，因为这决定 SP1 的认证层怎么写。

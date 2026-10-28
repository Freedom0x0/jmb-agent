# 本机实测（2026-10-13 第四轮）

本轮全部为零成本、零网络写入的本地检查（除一条 401 未鉴权探测）。每条都记"跑什么命令 / 亲眼看到的输出"。

## 1. hermes-agent：能不能起来 —— 我上一轮的判断错了半边

跑的命令与看到的原文：

- `ls hermes-agent/.venv` → 存在。
- `cat .venv/pyvenv.cfg` → `home = C:\Users\15532\AppData\Local\Programs\Python\Python312`，`version = 3.12.10`，`command = ...Python312\python.exe -m venv C:\Users\15532\Desktop\hermes-agent\.venv`
  ⇒ **这个 venv 是在项目被挪进 `xj\` 之前建的**（绑的是 `Desktop\hermes-agent`）。
- `ls .venv/Lib/site-packages | grep dist-info` → 只有 **9 个**：colorama、dotenv(0.9.9 + python_dotenv-1.2.2 两份)、iniconfig、packaging-26.2、pip-25.0.1、pluggy、pygments、pytest-9.1.1、pyyaml。总数 `wc -l` = 23。
  ⇒ **`hermes` 自己没装进这个 venv**，也没有 `openai`/`anthropic`/`rich`/`httpx` 等直接依赖。这就是子代理说"7960 文件的 fork，.venv 看着在但没装"的实测根据。
- `ls /c/Users/15532/Desktop/hermes-agent` → **不存在**（项目已移动，venv 的创建路径成孤儿）。
- `ls /c/Users/15532/AppData/Local/hermes` → **不存在** ⇒ **他从没在这台机器上跑过 Hermes**。
- `grep -inE "windows|install" hermes-agent/README.md` → **决定性的一条**：
  - L43 `### Windows (native, PowerShell)`
  - L45 原文："Native Windows runs Hermes without WSL — **CLI, gateway, TUI, and tools all work natively.**"
  - L50 安装命令：`iex (irm https://hermes-agent.nousresearch.com/install.ps1)`
  - L53 原文：安装器负责 "uv, Python 3.11, Node.js, ripgrep, ffmpeg, **and a portable Git Bash**（MinGit，解到 `%LOCALAPPDATA%\hermes\git`，不需要管理员）"；已有 Git 则复用系统 Git。
  - L59 原文：native Windows 安装在 `%LOCALAPPDATA%\hermes`；WSL2 装在 `~/.hermes`。
  - L70-97 **已知坑**：Windows Defender / 杀软会把 Hermes 自带的 `uv.exe` 判为恶意软件，README 说是 ML 引擎对"未签名的 Rust 二进制 + 会下载包装包"的误报，给了校验和加白名单的路径（`Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\hermes\bin"`）。
- `grep -rn "croniter" --include=*.py -l` → `./cron/jobs.py`、`./hermes_cli/doctor.py` + 三个 cron 测试。另有 `docs/chronos-managed-cron-contract.md`。
  ⇒ **cron 调度是它进程内的功能**，不需要 `schtasks`。代价：进程得活着（gateway）。
- `grep -rn "background_review" --include=*.py`（排除 tests）→ 关键行：
  - `agent/background_review.py:4` `spawn_background_review_thread` "fire off a daemon thread that replays"
  - `:24/:52/:625` 可把复盘用的模型换成另一个具体模型（`auxiliary.background_review.{provider,model}`）
  - **`:663-664` `review_agent._memory_write_origin = "background_review"` / `_memory_write_context = "background_review"`**
    ⇒ **记忆写入带"来源"标签，后台复盘写的和用户写的能区分。** 这正是上一轮调研里 OpenClaw 靠 provenance 污点门实现的那道防线，Hermes 已经有了。
  - `:363 summarize_background_review_actions` ⇒ 复盘完会生成"我做了哪些改动"的摘要 = 用户可见告知。
- `docs/rca-ssl-cacert-post-git-pull.md` 原文（这是一份已解决（resolved）的 P2 RCA，**Hermes 自己承认的真实故障面**）：
  - Summary：一次被中断的 `hermes update`、venv 修复不完整、或过期的 CA bundle 环境变量，会让 Python TLS 指向一个不存在/空/不可加载的 CA 路径，第一次对外 HTTPS 就崩。报错形如裸的 `FileNotFoundError: [Errno 2] No such file or directory` 或不点名 CA 路径的底层 SSL 错误。
  - Root cause 涉及的环境变量：`HERMES_CA_BUNDLE`、`SSL_CERT_FILE`、`REQUESTS_CA_BUNDLE`、`CURL_CA_BUNDLE`，以及自带 `certifi` 的 `cacert.pem`。
  - **本机现状**：上述四个 env **全部未设置**（`env | grep` 空输出）⇒ 这个陷阱现在没上膛，但只要以后设过任何一个再挪动 venv 就会复发。
- `pyproject.toml` 依赖段原文要点：**每个直接依赖都钉死 `==X.Y.Z`**，注释写明理由（"ranges allow PyPI to ship a fresh version of a transitive at any time"），并记录 **"2026-05-12 因 Mini Shai-Hulud 蠕虫命中 mistralai 2.4.6 而收紧"**；`anthropic`、`firecrawl-py`、`exa-py`、`edge-tts` 等 provider 专属依赖被挪进 extras，用户选了那个后端才用 `tools/lazy_deps.py` 懒装。`croniter==6.0.0` 在核心依赖里。
  ⇒ 供应链纪律很好，但**钉死版本意味着他这个 fork 装的是一周年的旧组合**，且换端点/换模型可能要动锁文件。
- 后台 `du` 尚未回（见文末待补）。

**结论修正**：我上一轮说 hermes 的阻塞是"fork 停在 feature 分支、工作区脏、venv 可疑"。**"跑不起来"这半句是错的**——它对原生 Windows 有官方一级支持，且自带便携 Git Bash 和 cron 调度；真正的阻塞只有两条：① 本机那份从未安装（`%LOCALAPPDATA%\hermes` 不存在），② 它**没有陪伴/情感/学习这一层**（只有 `SOUL.md` 人格 + `USER.md` 用户模型 + 会自己写技能）。

## 2. Context Forge 的本地嵌入：权重是齐的，缺的只是包 —— 我上一轮读错了

| 检查 | 输出 |
|---|---|
| `ls ~/.cache/huggingface/hub/` | `models--sentence-transformers--all-MiniLM-L6-v2/` 存在，另有 `xet/` |
| `du -sh <该模型目录>` | **771K** ← 我把这个数当成了"权重没下全" |
| `ls -la <snapshots/1110a24.../>` | `model.safetensors -> ../../blobs/53aa5117...`（**是符号链接**，du 不跟随，所以 771K 是假读数） |
| `stat -L -c "%s" <model.safetensors>` | **90,868,376 bytes** ⇒ **权重完整在盘上** |
| `ls ~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/` | `model.onnx` = **90,387,606** + `tokenizer.json` + `vocab.txt`；同目录还有 `onnx.tar.gz` 83,178,821 |
| `grep -iE "sentence\|torch\|onnx" <Context Forge venv 的 site-packages>` | **无 sentence-transformers、无 torch、无 onnxruntime**（该 venv 只有 context_forge-1.0.0、mcp-1.30.0、typer、uvicorn、watchdog、httpx、pydantic 这类） |
| **用它自己的 venv 调它自己的 embedder** | `EMBED FAIL: EmbeddingError sentence-transformers is not installed` |
| 全局 Python 3.13（`find_spec`） | `sentence_transformers OK`、`torch OK`、`onnxruntime MISSING`、`anthropic MISSING`、`openai MISSING` |
| 全局 Python 3.12 | `sentence_transformers MISSING`、`torch MISSING`、`onnxruntime MISSING` |

**结论修正**：上一轮我写"DeepSeek 没有 embeddings 接口 ⇒ 可能永久只有纯关键词记忆"。现在准确说法是：**本机已经有一套能跑的本地嵌入栈**（Py3.13 里 sentence-transformers + torch 已装，MiniLM 完整权重 90MB 已在 HF 缓存，另一个 chroma 的 ONNX 副本 86MiB 也在盘上）。

- `Context Forge/embedding.py:1-6` 的文档原话就把这个设计写死了：provider 是刻意惰性的，"Callers can treat a missing provider as lexical-only mode"；`:62-74` 先 import `sentence_transformers`，失败即 `EmbeddingError("sentence-transformers is not installed")`；`:68-70` 强制 `HF_HUB_OFFLINE=1`。
- ⇒ 把向量打开只需往它 venv 装 `sentence-transformers`（会拖 torch 那份重依赖；torch 已在 3.13 装过，可复用），**不需要网络、不需要第二份 API、不需要装本地服务**。
- 更轻的一条路：ONNX 副本已在盘上，只缺 `onnxruntime`（单包，无 torch）。
- **一条必须记住的代价**：AI Town 官方文档原话是换嵌入模型"永久破坏已有记录"。Context Forge 有 `model_identity()`（`embedding.py:43-44`，返回 `sentence-transformers:all-MiniLM-L6-v2:384`）当指纹，但这只是"能识别"，不等于"能迁移"。⇒ 嵌入模型一旦选定并写库，就是一次不可逆选型，要在设计里当决策点，不是当参数。

## 3. Node / Bun

- `nvm list` → 只有一个：`* 22.22.0 (Currently using 64-bit executable)`。nvm 根 `C:\nvm4w\nodejs -> AppData\Local\nvm\v22.22.0`。
- ⇒ **OpenClaw 的 `engines.node ">=24.16.0 <25 || >=26.1.0"` 不满足**，且机器上没有别的 Node 版本可切。要采纳它就必须 `nvm install 24`（或 26）。
- `bun --version` → **1.4.3**，满足 OpenClaw 文档化的 "Bun 1.4.0+ 显式 opt-in 替代运行时"。**但这条替代路径我们没实测过 gateway 是否在 Bun 上跑通。**

## 4. 一条改变"谁能装东西"的事实

上一轮有子代理报告"Bash 无外网、DNS 解析失败"。**那是它自己的会话限制，不是这台机器的限制**：

- `curl https://api.deepseek.com/models` → **HTTP 401**（未带凭据的正常应答，说明网络通、DNS 通、TLS 通；注意：这是一次未鉴权的探测，没有任何模型调用、不产生费用）
- `curl https://pypi.org/simple/` → **200**（一次大包读取在 6 秒超时内收了 5.5MB，说明带宽也够）

⇒ 需要装依赖时我可以自己装，不必都写成"你去跑这条命令"。但装包会改他的环境、体积大 ⇒ **按他的规矩，动之前单独问。**

## 5. 本轮的净效果：三个"以为是阻塞"的都不是阻塞

1. hermes 装不起来 → **假**（官方原生 Windows + 自带工具链）。
2. 永久只能关键词检索 → **假**（本地嵌入栈已在盘上，只差一个包）。
3. Bash 不能装东西 → **假**（有外网）。

真正剩下的约束变成四条，且都是"要他拍板"的那种，不是技术不可行：
- 装 hermes 会引入一个**常驻 gateway 进程** + 一套它自己的运行时（uv/Python 3.11/Node 的独立安装），与他"少装东西"的偏好相抵。
- 采纳 OpenClaw 需要**换 Node 大版本**，且默认心跳 30 分钟 = 一天 48 次整轮模型调用。
- 这两个宿主**都没有陪伴/学习/情感层**，那一层无论选谁都归我们写。
- 嵌入模型一旦选了就**不可逆**。

## 待补 → 已补齐

后台 `du` 回来了：

- `du -sh` → **hermes-agent = 511M**（含那个 30M 的空壳 `.venv`）、`deepseek-harness`、`Context Forge` 的数在同一个后台任务里但因单次命令超时被截，未取到。
- `df -h /c` → `475G total / 420G used / 56G avail / 89%`。

⇒ 体积这一格重算：**hermes 的 511M 是剩余额度的 0.9%，不是阻塞项**；真正要掂量的是 OpenClaw 那种 9.1 GB 量级的仓库，加上它若跑起来会自己长出来的 SQLite WAL（它自己有个 issue 就是 WAL 涨到 1.4–2.8 GB 卡住启动）。
⇒ 上一条的出处：OpenClaw 的 GitHub API `size` 字段报 9,155,980 KB ≈ 9.1 GB（这是仓库体积计数、含历史；`git clone` 实下载会因传输压缩而小于它，但同数量级，本轮未实测 clone）。这台机器只有 C: 一块盘，56 GB 余量还要同时容下开发工具链、WSL 和未来的 agent 数据。（本轮未枚举其它大项占用，只报实测到的总数。）

## 还没跑的两条（要花真钱，等他点头）

1. **自动前缀缓存在 `/anthropic` 路径上生不生效**：同一份固定前缀打两次，比对两次 usage 里有没有 `cache_read_input_tokens` 之类的读数。这条决定"每轮注入人格+记忆索引"的真实单价。
2. **模型名与认证模式**：`deepseek-flash[1m]` / `[1M]` / `deepseek-flash` 哪个被接受，`x-api-key` 与 `Bearer` 哪种通。issue #151861 里端点吐回的可选项是 `deepseek-flash, deepseek-v4-pro`。

两条各花不到一次最小请求的钱，跑完就把"设计前提"变成"实测数字"。

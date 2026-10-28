# 端点实测结果（2026-10-13 第五轮）

目标端点：`https://api.deepseek.com/anthropic`（会话 env `ANTHROPIC_BASE_URL` 亲测指向它，`ANTHROPIC_MODEL=deepseek-flash`）。
探针脚本留在 `jmb/scripts/probe_endpoint{,2,3}.py`，是一次性测量件，不属于产品代码。
发送内容全是合成文本（伪造的"学习陪伴"人格段和一条假的 `record_session` 调用），**没有发任何用户数据**。
每一次调用的 usage 数字都按"哪一次运行"标注，便于复核。

## 1. 我上一轮的推论错了：自动前缀缓存是生效的

上一轮我从 DeepSeek 官方兼容表读到 `cache_control` = Ignored，推出"提示缓存一分钱拿不到"。**实测推翻后半句。**

`probe_endpoint.py` 第一次运行，同一份 10,705 字符前缀连打三次：

| 次序 | input_tokens | cache_read_input_tokens | cache_creation_input_tokens |
|---|---|---|---|
| #1 | 2300 | 0 | 0 |
| #2 | 252 | **2048** | 0 |
| #3 | 252 | **2048** | 0 |

`probe_endpoint2.py`（另一进程，间隔数分钟）：

| 用例 | 结果 |
|---|---|
| A1 完全稳定的前缀，第 1 次打 | input=252 **cache_read=2048**（跨进程、隔了几分钟仍命中） |
| A1 第 2 次 | input=252 cache_read=2048 |
| A2 **只改结尾一个词** | cache_read=2048 **不掉**，input 252→253 |
| A3 **只改开头一个词**，第 1 次 | input=**2302**，**cache_read=0** ⇒ 命中归零 |
| A3 第 2 次（同一串 mutated） | cache_read 回到 2048 |

`probe_endpoint3.py`（第三批）——**这才是真实用法**：稳定 system 前缀 + 每轮换一句不同的中文用户话：

| 用户话 | input_tokens | cache_read |
|---|---|---|
| 今天学了什么？ | 255 | 2048 |
| 帮我出两道复习题 | 256 | 2048 |
| 我有点累，少安排点 | 258 | 2048 |

### 四条可直接进设计的规则

1. **`cache_control` 显式断点无效，但服务端自动前缀缓存在跑，而且用量报在 Anthropic 形态的 `usage.cache_read_input_tokens` 里。** ⇒ 我们能白拿缓存，不需要也无法请求。
2. **`cache_creation_input_tokens` 全程为 0** ⇒ 没有 Anthropic 那套 1.25x / 2x 写入溢价。
3. **稳定段必须逐字节稳定，且一切可变内容排在它之后。** 改尾部一个词不掉命中；改开头一个词命中立刻归零。
4. **每轮重注入"人格 + 用户模型 + 记忆索引"是便宜的**：一份约 2,300 token 的常驻前缀，稳态下每轮只有 **250 token 级**是新算的。

### 这几条推翻/修正了什么

- **修正**：上一轮"上下文很贵，所以常驻注入要分档省着给"的成本前提**不成立**。设计里可以允许一个大得多的稳定前缀。
- **解释了 OpenClaw 那个 issue**：#96773 报"每轮注入 SOUL/IDENTITY/USER 打爆 DeepSeek 缓存，命中率在 20%/99% 摆动"——按 A3 的机制看，那是**它每轮重建的文件内容不稳定**造成的，不是"注入本身必然贵"。#67419（浪费 20–30% token）同源。⇒ 解法是**我们自己控制前缀布局**，不是砍掉注入；也说明照抄 OpenClaw 的注入实现会连带继承它的抖动。
- **两条未定**：① 缓存存活时长（我只测到"跨两次脚本、间隔几分钟仍命中"，没测上限，也没测 Anthropic 那种 5 分钟/1 小时 TTL 语义）；② 命中粒度只出现 2048 与 256 两个数（都是 256 的整数倍，疑似 256-token 块），样本太少**不定论**。

## 2. 模型名与认证：都不是问题，但有一格没验

`probe_endpoint.py` 第一次运行，全部 HTTP 200：

| 请求的 model | 响应回显的 model | input_tokens |
|---|---|---|
| `deepseek-flash` | `deepseek-flash` | 38 |
| `deepseek-flash[1m]` | `deepseek-flash[1m]` | 38 |
| `deepseek-flash[1M]` | `deepseek-flash[1M]` | 38 |
| `deepseek-v4-pro` | `deepseek-v4-pro` | **91** |
| `deepseek-flash` + **`x-api-key`** 头 | `deepseek-flash` | 38 |

- **`[1m]` / `[1M]` / 裸名三种都被接受并原样回显**，大写不是问题（他 `settings.json` 里那批 `[1M]` 别名是在用的）。
- **`Bearer` 和 `x-api-key` 两种认证都通** ⇒ 不必二选一，两个都能配。
- **但 `[1M]` 是否真的切换到了 1M 上下文窗口，这批数据判不出来**：三个 flash 变体的 `input_tokens` 完全相同（38），说明后缀不影响分词；要证明窗口差异得构造超长请求。**这条留作未验**，不能当设计前提。
- 顺带一条：同一请求在 `deepseek-v4-pro` 上是 91 token、在 `deepseek-flash` 上是 38 token ⇒ 两者是**不同模型/不同分词**，不是别名。

## 3. count_tokens 存在 ⇒ 可以做花钱前的预算闸门

- `POST /v1/messages/count_tokens` 带完整 body（`model` + `system` + `messages` + `tools`）→ **HTTP 200，返回 `{"input_tokens": 2573}`**。
- 只带 `model` + `max_tokens`、不带 `messages` → **HTTP 422** `missing field messages`。

⇒ 上一轮调研里"发出去之前先量一次"的官方端点在我们端点上**可用**，且 **tools 定义被计入**（同一前缀：带 tools 2573 vs 不带约 2300）。这条让"记忆索引注入前先算预算"从设想变成一行调用。

## 4. 工具循环能用，但有一个必须处理的怪癖

`probe_endpoint.py` 第一次运行 + `probe_endpoint2/3.py`：

- 工具调用**完全可用**：`stop_reason=tool_use`，`tool_use name=record_session input={"topic": "recursion", "minutes": 25}` —— 参数解析正确、类型正确。
- **它会未经请求就返回 `thinking` 块**（键：`signature` / `thinking` / `type`，那次内容长度 135 字符）。这不是我们要求的，它默认给。
- 多轮续聊两种都通过：
  - 把 `thinking` **原样带回去** → HTTP 200，`stop=end_turn`，output=13。
  - **丢掉 `thinking`** → HTTP 200，`stop=end_turn`，output=9。
  ⇒ 这个端点**不执行** Anthropic 那条"工具续聊必须保留 thinking 块"的规则。**这正是 hermes-agent 里那个 `_is_deepseek_anthropic_endpoint()` 特判所处理的坑，但在我们实测里它不构成阻塞**——自己写循环时可以简单地丢掉 thinking。
- 工具定义的真实成本：一次带单个小工具的请求 input=325（对照无工具同构请求 38）⇒ **一个工具的 schema 约几百 token 级**，且因为它落在稳定前缀里，稳态下可被缓存吸收。

### `tool_result.is_error`：没判出来，但结论不受影响

- 带 `is_error: true` 的那次，模型明确说了："I wasn't able to log the session — the recording tool returned *disk full*"（HTTP 200，`stop=end_turn`，output=285）。
- 对照组（同样的 `content: "disk full"` 文本、不带该标志）那次 300 token 全被 thinking 吃掉、`stop=max_tokens`、**没有文本产出** ⇒ **对照组不干净，所以无法区分它是读标志还是读那句文本。**
- 官方文档说 `is_error` 是 Ignored，我这里既没证实也没证伪。
- **设计结论不变且不依赖这一格**：工具失败必须同时把原因写进 `content` 文本，不能只设标志位。

## 5. 一句话给设计的总账

这台机器 + 这个端点上，**"每轮把人格、用户模型、记忆索引全部重注入"是可以负担的**，代价只在于我们必须遵守一条纪律：**那段内容逐字节稳定、并且排在任何会写的东西之前**。实测数字是稳态每轮 250 token 级新输入，对照一份约 2,300 token 的常驻前缀。

上一轮那三条"真阻塞"里，"缓存拿不到"这条**作废**；剩下仍然成立的只有：装宿主会引入常驻进程、两个候选宿主都没有陪伴/学习层、嵌入模型选定即不可逆。

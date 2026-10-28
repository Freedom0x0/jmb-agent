# L2 · 每日清单 + 聊一个项目

决策依据：D23（硬性规矩）、D24（10:00、一期只做"甲"）、D18（只列清单不给观点）、D19（记兴趣）。

**这是整个系统里唯一被允许主动开口的一条。**（D24 你选了甲：不做"平时它自己想找话头"。）

## 你看到的一次

```
早上 ~10:00，你开机。
桌宠冒一个气泡：「今天榜单好了，8 条」

你打开对话窗口，看到的是：

  1) <项目名>  https://github.com/…  一句话它做了什么
     ↑ 今天新增 312 星
  2) …
  3) …

你说：第 2 个展开讲讲
它：[去读那个 repo 的 README / 首页] → 讲，然后你不问它就不扩展
```

**它不评价、不替你挑。** 你原话是"直接列出来项目名称，地址，大致介绍，我感兴趣的话我会详细追问"——所以"这个你可能会喜欢"这类话禁止出现（D18）。

## 触发（两条，都算这一条 workflow）

| 触发 | 条件 | 说明 |
|---|---|---|
| **时间表** | 每天 **10:00**，**每天只跑一次** | 【实测支持】本地小时分布 09→382、**10→560**、11→520 |
| 事件 | 你直接问"今天有什么新项目" | 未跑则现跑，已跑则读当天结果 |

⛔ **不做"当天第一次开机补跑"（D30，2026-10-27 他明确要求去掉）**：不配开机触发器（`schtasks` / `qoder_cron` 在关机时本来就不跑）。
**代价**：10:00 时机器关着 ⇒ **那天就没有清单**。这条代价按他的决定接受，不再是待办。

用什么跑：**`qoder_cron`**（本机 MCP 实测支持 `at` / `every` / `cron` + IANA `timeZone`）或 Windows `schtasks`。二选一由实现阶段定，**只挂 10:00 这一条，不挂 ONLOGON/ONSTART**（D30）。**注意 `qoder_cron` 的 `location=cloud` 那条不继承本地工作区/文件/工具/插件/连接器/权限/会话模型**【实测原文】——所以必须跑在本地。

## 三个数据源：不是一个东西，可信度差别很大

| 源 | 状态 | 形状 |
|---|---|---|
| **GitHub 榜单** | ⚠️ **没有官方 trending API**【实测：GitHub REST 文档 412 KB + `llms.txt` 里 "trending" 0 命中】；且 `github.com/trending` 的 HTML **从这台机器打不开**【实测超时】 ⇒ 不能爬 trending 页 | 用 `api.github.com/search/repositories?q=created:>N天&stars:>X&sort=stars`（实测：认证 30 次/分钟，未认证 10；REST 未认证 60/小时）。 ⇒ 语义变成"**最近新建且星数高**"，不是真的 trending。这条差异要写进文档，别让他以为拿到的是榜单 |
| **技术热点** | ✅ 本机已有现成的 | `Desktop\xj\SkillAbout`：`build_digest.py` 抓 `star-history.com`（实测可达）+ `api.github.com/repos/{repo}` 取事实；`domestic_search.py` 抓搜狗 + `cn.bing.com`（**可达**）+ `html.duckduckgo.com`（**当前在你机器上超时**）⇒ 复用它的抓取面，DDG 那条腿要换掉 |
| **AI 相关线下会议** | ⚠️ **已查完（D27）：大陆同城拿不到，但有三段能拿** | ① **值得专门去的会**：`ccfddl/ccf-deadlines`（MIT、今日仍在 push）每场会的 `date` + `place`，走 `api.github.com`（**别走 raw.githubusercontent.com，本机实测超时**）——**这是这栏的主内容**；② **港澳/新加坡真实活动**：`POST https://www.meetup.com/gql2` 匿名 GraphQL（香港池 11、新加坡 19，有真 AI 活动；⚠️ 未文档化内部端点、ToS 页 404 ⇒ 随时可能变，**不许当唯一依赖**）；③ **中国 GDG**：解析 `gdg.community.dev/gdg-<city>/` 里的 `__NEXT_DATA__`（量少但真实、带 ISO 日期）|

另外可用的兜底：DeepSeek 自己的 `/v1/tools/search`（官方 `guides/search` 页【二手，子代理取】写 `POST https://api.deepseek.com/v1/tools/search`，参数 `query`(1–128 字符)、`count`(1–50)、支持 `site:` / `after:` / `lang:`；计费 $0.75/1000 成功请求。**我自己这次没复现那页，所以价格与免费期数字标【待复验】**）。

## 输出格式（定死三字段）

```
序号) 名称  地址  一句话介绍
```
- **【我定的】一次列 8 条**。你改数字。理由仅一条：你说过"我感兴趣会详细追问"，超过一屏就不追了。这条不是调研结论。
- 排序**按发现顺序，不按"它觉得有意思的程度"**——那属于被 D18 否决的"替他筛"。
- 每条的介绍必须来自它实际看到的标题/摘要，**不许凭模型记忆写**。
- **会议那一段开头必须带一句固定说明**：*"大陆同城的活动我拿不到（活动行有验证码和登录墙，中文科技媒体的活动页是空壳或被拦）。以下是能确认时间地点的会和港澳/新加坡的活动。"* —— 让他知道这不是漏抓，别让他以为"今天没有会"。

## 检查点

**没有。** 这条 workflow 完全自主跑（除了"线下会议"那栏在源没定之前是人工贴）。跑完只在桌宠上冒一句。

## 桌宠（一期唯一"主动找你"的可见形态）

接 **Petdex Desktop**（MIT，实测有 `desktop-v0.9.2` 的 `petdex-desktop-native-win32-x64.exe`）：
- 控制面【实测读源码】：本机 `127.0.0.1:7777`，token 门控的 `POST /state`、`POST /bubble`、`/bubble/title`；header `x-petdex-update-token`；token 文件 `~/.petdex/runtime/update-token`（0600，**每会话重生成**）；共享 30 次/秒限速；也有 MCP 工具 `petdex_set_state` / `petdex_show_bubble` / `petdex_status`（正文 4096 B、标题 256 B）。
- 素材：`pet.json` + 一张 spritesheet（8×9 或 v2 8×11 网格，单帧 192×208），9 个状态行 idle/running-right/running-left/waving/jumping/failed/waiting/running/review。
- ⚠️ **两条阻塞**：① 没有公开的第三方 API 文档（上面全部读自源码/README）；② token 每会话重生成 ⇒ 要写一个"读 token 文件"的适配层，且它可能在你不知情时变（宠物 App 重启后）。
- ⚠️ 别和 Qoder 自带桌宠混淆：那个的 skill 只是 `npx petdex install` + **人工在设置里选**，且 app.asar 里写"只支持内置的 Qoduck"（皮肤锁死）。

## 写什么

跑完之后**只写一类东西**：`interests.md` 里"他对 X 表过兴趣"——条件是他**追问过**那个项目（D19）。他不问就不记。
**边界**：只记"他对什么感兴趣"这一件事实，**不由此推断他的水平、性格或情绪**。

## 一期不做

不定时提醒、不推送、不替他挑、不给评价、不把清单内容写进长期记忆（清单是一次性的，只有"兴趣"留下来）。

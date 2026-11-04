# 变更日志

每次修改简要记一行（规矩写在 `AGENTS.md`）。背景与理由看 `docs/decisions.md` 对应的 D 条目。

## 2026-11-03

- 移动端首切片（D50）：`jmb serve` 薄后端（stdlib HTTP+SSE，surface=mobile 只聊天+搜索+记事实）+ 浏览器单页壳 `jmb/server_static/index.html`；模型 key 留后端，配对 token 换 HttpOnly cookie；桌面 app/终端零改动。
- 移动会话历史持久化（D51）：`state/mobile-history.json` 双份（模型上下文 + 渲染），turn_end 原子落盘，新连接 ready 后收 history 帧恢复气泡。真机排查补记：活体复现普通轮+工具轮均正确落盘；他没生效是连了旧代码进程/桌面入口。同批加固：persist 异常打 stderr 不杀会话、`/` 加 no-store 防手机缓存旧页面、PWA 加搜索框（客户端过滤）+ 发送失败提示。
- 滚动会话同步（D53）：`state/conversation.json` 单文件权威（D51 的手机专用文件被它取代），同步+落盘挂在 ChatSession.send（循环侧），桌面 app 启动渲染历史、手机/终端自动同源；113 项测试通过。
- 设置页加上下文窗口/输入预算（D52）：落 config.json，profile 链 env > config > 模型表 > 默认；手机新会话即生效。
- 能力表落地：`chat.py` 加 `SURFACE_TOOLS`、`prefix.build_system(surface)` 按入口裁剪工具散文；`ChatSession(emit, surface=...)`。
- 109 项测试通过（含跨连接历史持久化 + 预算三层链）；真实 deepseek 调用端到端冒烟通过。
- 能力表落地：`chat.py` 加 `SURFACE_TOOLS`、`prefix.build_system(surface)` 按入口裁剪工具散文；`ChatSession(emit, surface=...)`。
- 106 项测试通过（新增 `tests/test_server.py`）；真实进程 + 真实 deepseek 调用端到端冒烟通过。

## 2026-11-02

- 模型/端点/key 的唯一出处改为 jmb 自己的 `config.json`：不读环境变量、不碰 Claude Code 的 `settings.json`；聊天窗「··· → 模型设置…」填写，重启 app 生效（D49）。
- 桌宠去掉 hover 圆环描边；右键菜单加「隐藏桌宠」，聊天窗「···」可切换显示/隐藏，隐藏状态随 `ui.json` 持久化（D48）。
- 顺带修复：恢复窗口状态时先落位再隐藏，隐藏重启后桌宠位置不再丢回默认底部（D48）。

"""jmb 命令行：doctor（体检）/ chat（REPL）/ brief（每日清单）。"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

from . import config

EXIT_OK = 0
EXIT_PROBLEM = 1


def _mark(ok: bool) -> str:
    return "OK " if ok else "MISS"


def cmd_doctor(_args: argparse.Namespace) -> int:
    problems = 0

    home = config.jmb_home()
    print(f"家目录    {home}  [{_mark(home.is_dir())}]")

    base = config.resolve_base_url()
    print(f"端点      {base.value}  （来源 {base.source}）")

    try:
        from . import providers as _providers
        profile = _providers.load_profile()
        print(f"线路      {profile.name}（{profile.protocol}）→ {profile.model}")
    except Exception:  # noqa: BLE001
        print("线路      [WARN] provider profile 解析失败")

    model = config.resolve_model()
    env_model, settings_model = config.raw_model_values()
    print(f"模型名    生效={model.value}  （env={env_model or '<空>'} / settings={settings_model or '<空>'}；来源 {model.source}）")

    token = config.resolve_token()
    if token.value:
        print(f"token     长度 {len(token.value)}  （来源 {token.source}；只报长度，不回显）")
    else:
        print("token     [MISS] env 和 ~/.claude/settings.json 的 env 段里都没有")
        problems += 1

    forge = config.forge_home()
    ready = forge.is_dir() and (forge / "config.toml").is_file()
    state = "就绪" if ready else "未就绪（Phase 5 建：目录 + config.toml）"
    print(f"CF 家目录 {forge}  [{state}]")
    ambient = os.environ.get("CONTEXT_FORGE_HOME")
    if ambient and Path(ambient) != forge:
        print(f"          [WARN] 环境里设了 CONTEXT_FORGE_HOME={ambient}——它会劫持 CF 的 runtime_dir()；"
              f"jmb 进程内必须显式覆盖成上面这个路径，否则记忆库指到别家")
        problems += 1

    try:
        import context_forge
        cf_pkg = Path(context_forge.__file__).parent
        print(f"CF 包      context-forge {context_forge.__version__}  {cf_pkg}  [OK]")
    except Exception:  # noqa: BLE001
        print("CF 包      [MISS] context-forge 未安装（uv sync）")
        problems += 1

    from . import code as code_tools
    sandbox = code_tools.sandbox_summary(check_daemon=True)
    print(f"沙箱      {sandbox}")
    if (sandbox.startswith("host") or "找不到 docker" in sandbox
            or "daemon=未运行" in sandbox):
        problems += 1

    brief = config.brief_state_path(_dt.date.today())
    if brief.is_file():
        print(f"今日日报  已跑（{brief.name}）")
    else:
        print(f"今日日报  未跑（{brief} 不存在；brief 属 Phase 7，未建成属正常）")

    if not config.CLAUDE_SETTINGS_PATH.is_file():
        print(f"[WARN] {config.CLAUDE_SETTINGS_PATH} 不存在——凭据回退只剩 env 一层")
        problems += 1

    print(f"Python    {sys.version.split()[0]}")
    print("体检结论  " + ("有标 [WARN]/[MISS] 的项要看一眼" if problems else "干净"))
    return EXIT_OK if not problems else EXIT_PROBLEM


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="jmb", description="一个记得住你、跟得上你、不多管的伙伴")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor", help="体检：家目录/端点/模型名/token 长度/CF 家目录/今日日报")
    sub.add_parser("chat", help="对话：流式、SOUL 人格、服务端搜索、读正文、记忆、白名单读码")
    sub.add_parser("brief", help="每日清单（三源、零模型调用、幂等；10:00 定时跑同一命令）")
    sub.add_parser("app", help="桌面 app：聊天窗口 + 内置桌宠（Tkinter）")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "chat":
        from . import chat  # 惰性导入：doctor 不该为 anthropic SDK 买单
        return chat.run()
    if args.command == "brief":
        from . import brief
        return brief.run()
    if args.command == "app":
        try:
            from .app.main import run as run_app
        except Exception as exc:  # noqa: BLE001
            print(f"app 启动失败：{type(exc).__name__}: {exc}")
            return 1
        return run_app()
    parser.print_help()
    return 0 if args.command else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""命令行：chartkit render / demo / types / themes。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .api import Chart, available_themes, available_types


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chartkit", description="自动生成学术/商务图表")
    sub = parser.add_subparsers(dest="cmd", required=False)

    render_p = sub.add_parser("render", help="根据 YAML/JSON 配置出图")
    render_p.add_argument("config", help="配置文件路径")
    render_p.add_argument("-o", "--output", help="输出路径，默认 output/<配置名>.png")
    render_p.add_argument("--dpi", type=int, default=None)

    batch_p = sub.add_parser("batch", help="批量渲染一个目录下的全部配置")
    batch_p.add_argument("folder")
    batch_p.add_argument("-o", "--output", default="output")

    demo_p = sub.add_parser("demo", help="生成内置示例图到 output/")
    demo_p.add_argument("-o", "--output", default="output")

    serve_p = sub.add_parser("serve", help="打开本地网页，可视化出图")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8765)
    serve_p.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")

    sub.add_parser("desktop", help="打开桌面窗口，给不会代码的人用")

    sub.add_parser("types", help="列出支持的图表类型")
    sub.add_parser("themes", help="列出内置主题")

    args = parser.parse_args(argv)
    if not args.cmd:
        args.cmd = "serve"
        args.host = "127.0.0.1"
        args.port = 8765
        args.no_browser = False

    if args.cmd == "types":
        print("\n".join(available_types()))
        return 0
    if args.cmd == "themes":
        print("\n".join(available_themes()))
        return 0
    if args.cmd == "render":
        chart = Chart.from_file(args.config)
        output = Path(args.output) if args.output else Path("output") / (Path(args.config).stem + ".png")
        path = chart.save(output, dpi=args.dpi)
        print(path)
        return 0
    if args.cmd == "batch":
        paths = Chart.batch(args.folder, args.output)
        for path in paths:
            print(path)
        return 0
    if args.cmd == "demo":
        from .demo import generate_demos

        paths = generate_demos(args.output)
        for path in paths:
            print(path)
        return 0
    if args.cmd == "serve":
        try:
            from .web import serve
        except ImportError as exc:
            print("启动网页需要 Flask，请先执行: pip install flask")
            print(exc)
            return 1
        serve(host=args.host, port=args.port, open_browser=not args.no_browser)
        return 0
    if args.cmd == "desktop":
        from .desktop import main as desktop_main

        desktop_main()
        return 0
    return 1

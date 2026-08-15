"""支持两种启动方式：

- 正确：python -m chartkit demo
- 也能：直接运行本文件（IDE 点 Run）
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_sys_path() -> None:
    # 直接 python __main__.py 时没有父包，相对导入会失败
    if __package__ not in {None, ""}:
        return
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_sys_path()

if __package__ in {None, ""}:
    from chartkit.cli import main
else:
    from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

"""项目根目录启动入口，方便在 IDE 里直接点 Run。"""

from __future__ import annotations

import sys
from pathlib import Path

src = Path(__file__).resolve().parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from chartkit.cli import main

if __name__ == "__main__":
    # 没传参数时打开网页出图台
    argv = sys.argv[1:] or ["serve"]
    raise SystemExit(main(argv))

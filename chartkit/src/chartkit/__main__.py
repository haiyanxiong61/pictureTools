"""支持两种启动方式：

- 正确：python -m chartkit
- 也能：在 PyCharm / Cursor 里直接点 Run 运行本文件
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _in_project_venv(root: Path) -> bool:
    venv = (root / ".venv").resolve()
    try:
        prefix = Path(sys.prefix).resolve()
        exe = Path(sys.executable).resolve()
    except OSError:
        return False
    return prefix == venv or venv in exe.parents


def _switch_to_project_venv() -> None:
    """PyCharm 常会用错别的项目解释器，这里自动切回本项目 .venv。"""
    root = _project_root()
    python = _venv_python(root)
    if not python.exists():
        print("还没准备本项目环境。请在终端执行：")
        print(f"  cd {root}")
        print("  python3 -m venv .venv")
        if os.name == "nt":
            print("  .venv\\Scripts\\activate")
        else:
            print("  source .venv/bin/activate")
        print("  pip install -e .")
        raise SystemExit(1)
    if _in_project_venv(root):
        return
    print("当前 Python 不是本项目环境，正在改用 chartkit/.venv …")
    print(f"  {python}")
    os.execv(str(python), [str(python), *sys.argv])


def _rerun_as_package() -> None:
    """当 IDE 直接运行本文件时，改成按包启动，避免相对导入失败。"""
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    import runpy

    runpy.run_module("chartkit", run_name="__main__")


if __name__ == "__main__":
    _switch_to_project_venv()
    if __package__ in {None, ""}:
        _rerun_as_package()
        raise SystemExit(0)

from .cli import main

if __name__ == "__main__":
    argv = sys.argv[1:] or ["serve"]
    raise SystemExit(main(argv))

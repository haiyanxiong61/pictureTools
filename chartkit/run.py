"""打开做图表 / 做词云。

在 Cursor 里：打开本文件，点右上角 ▶ Run，或按 F5。
浏览器会打开 http://127.0.0.1:8765
关掉这个运行窗口，网页也会一起关掉。
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _in_project_venv() -> bool:
    venv = (ROOT / ".venv").resolve()
    try:
        prefix = Path(sys.prefix).resolve()
        exe = Path(sys.executable).resolve()
    except OSError:
        return False
    return prefix == venv or venv in exe.parents


def _switch_to_project_venv() -> None:
    if not VENV_PY.exists():
        print("还没准备本项目环境。请在终端执行：")
        print(f"  cd {ROOT}")
        print("  python3 -m venv .venv")
        print("  source .venv/bin/activate" if os.name != "nt" else "  .venv\\Scripts\\activate")
        print("  pip install -e .")
        raise SystemExit(1)
    if _in_project_venv():
        return
    print("当前 Python 不是本项目环境，正在改用 chartkit/.venv …")
    print(f"  {VENV_PY}")
    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


_switch_to_project_venv()
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _page_ok() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=0.8) as res:
            return 200 <= res.status < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _port_busy() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, PORT)) == 0


def _free_port() -> None:
    try:
        if sys.platform == "win32":
            raw = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            pids = set()
            for line in raw.splitlines():
                if f"{HOST}:{PORT}" not in line and f"0.0.0.0:{PORT}" not in line:
                    continue
                pid = line.split()[-1]
                if pid.isdigit() and int(pid) not in {0, os.getpid()}:
                    pids.add(pid)
            for pid in pids:
                subprocess.run(
                    ["taskkill", "/PID", pid, "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            return
        raw = subprocess.check_output(["lsof", "-ti", f":{PORT}"], text=True)
        for pid in raw.split():
            if pid.isdigit() and int(pid) != os.getpid():
                os.kill(int(pid), 9)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, PermissionError):
        return


def main() -> int:
    os.chdir(ROOT)
    if _page_ok():
        print(f"已经在运行，正在打开：{URL}")
        webbrowser.open(URL)
        print("如果还要重新启动，先停掉上一次运行，再点一次 Run。")
        return 0
    if _port_busy():
        print("端口被卡住了，正在重新启动…")
        _free_port()

    print("正在打开做图表 / 做词云…")
    print(f"浏览器地址：{URL}")
    from chartkit.web import serve

    serve(host=HOST, port=PORT, open_browser=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

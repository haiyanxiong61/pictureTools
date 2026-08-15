"""桌面窗口：小白双击即可，不必碰命令行。"""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_ready(url: str, seconds: float = 8) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.4)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(0.15)
    raise RuntimeError("软件启动超时，请再打开一次")


def _keep_browser_window(url: str) -> None:
    import tkinter as tk

    webbrowser.open(url)
    root = tk.Tk()
    root.title("做图表")
    root.geometry("420x180")
    root.resizable(False, False)
    message = tk.Label(
        root,
        text="做图表已经打开。\n请不要关掉这个小窗口。\n关掉后软件会退出。",
        font=("Microsoft YaHei", 13),
        justify="center",
    )
    message.pack(expand=True)
    root.mainloop()


def main() -> None:
    from .web import create_app

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    app = create_app()
    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    _wait_ready(url)

    try:
        import webview

        webview.create_window("做图表", url, width=1320, height=860, min_size=(960, 640))
        webview.start()
        return
    except Exception:
        _keep_browser_window(url)


if __name__ == "__main__":
    main()

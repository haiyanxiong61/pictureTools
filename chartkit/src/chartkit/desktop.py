"""桌面窗口：小白双击即可，不必碰命令行。"""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


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


def _dialog_save(filename: str, data: bytes, fmt: str) -> dict:
    from .web import initial_save_dir, remember_dir, reveal_file

    import webview

    window = webview.windows[0] if webview.windows else None
    dest = None
    if window:
        dest = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=str(initial_save_dir()),
            save_filename=filename,
            file_types=(f"{fmt.upper()} 文件 (*.{fmt})", "所有文件 (*.*)"),
        )
    if isinstance(dest, (list, tuple)):
        dest = dest[0] if dest else None
    if not dest:
        return {"cancelled": True}
    path = Path(dest)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".zip"}:
        path = path.with_suffix(f".{fmt}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    remember_dir(path)
    reveal_file(path)
    return {"path": str(path), "folder": str(path.parent), "name": path.name}


class DesktopApi:
    def save_chart(self, payload: dict) -> dict:
        from .web import render_image, safe_filename

        data = dict(payload or {})
        title = str(data.pop("filename", "") or data.get("title") or "我的图表")
        image, fmt, label = render_image(data)
        return _dialog_save(safe_filename(f"{title}_{label}", fmt), image, fmt)

    def save_file(self, filename: str, data_b64: str, fmt: str = "png") -> dict:
        import base64

        raw = base64.b64decode(str(data_b64).split(",")[-1])
        suffix = Path(filename).suffix.lstrip(".") or fmt
        return _dialog_save(filename, raw, suffix)

    def save_wordcloud(self, payload: dict) -> dict:
        from .clouds import render_wordcloud
        from .web import safe_filename

        data = dict(payload or {})
        if data.get("data"):
            return self.save_file(str(data.get("filename") or "我的词云.png"), str(data["data"]), str(data.get("format") or "png"))
        title = str(data.get("filename") or data.get("title") or "我的词云")
        image, fmt, label = render_wordcloud(data)
        return _dialog_save(safe_filename(f"{title}_{label}", fmt), image, fmt)


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

        webview.create_window(
            "做图表",
            url,
            width=1320,
            height=860,
            min_size=(960, 640),
            js_api=DesktopApi(),
        )
        webview.start()
        return
    except Exception:
        _keep_browser_window(url)


if __name__ == "__main__":
    main()

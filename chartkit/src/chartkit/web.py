"""本地网页：选类型、改数据、预览和下载。"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from flask import Flask, jsonify, request, send_file, send_from_directory

from .api import Chart, available_themes, available_types
from .config import dump_yaml, parse_any
from .paths import webapp_dir
from .presets import PRESETS, THEME_LABELS, TYPE_HINTS, TYPE_LABELS

WEBAPP = webapp_dir()
MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}


def default_save_dir() -> Path:
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "桌面",
        Path(os.environ.get("USERPROFILE", str(home))) / "Desktop",
    ]
    for item in candidates:
        if item.is_dir():
            return item
    if sys.platform == "win32":
        try:
            import ctypes

            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf)
            path = Path(buf.value)
            if path.is_dir():
                return path
        except Exception:
            pass
    fallback = home / "Pictures" / "pictureTools"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def safe_filename(name: str, ext: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|\r\n]+', "", name).strip() or "我的图表"
    ext = ext.lstrip(".").lower() or "png"
    return f"{stem}.{ext}"


def unique_path(folder: Path, filename: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for index in range(2, 200):
        candidate = folder / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    return folder / f"{stem}_{os.getpid()}{suffix}"


def _last_dir_file() -> Path:
    return Path.home() / ".pictureTools_lastdir"


def initial_save_dir() -> Path:
    try:
        folder = Path(_last_dir_file().read_text(encoding="utf-8").strip())
        if folder.is_dir():
            return folder
    except Exception:
        pass
    return default_save_dir()


def remember_dir(path: Path) -> None:
    try:
        folder = path.parent if path.suffix else path
        _last_dir_file().write_text(str(folder), encoding="utf-8")
    except Exception:
        pass


def choose_save_path(filename: str) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    suffix = Path(filename).suffix.lower() or ".png"
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.asksaveasfilename(
        title="保存图片",
        initialdir=str(initial_save_dir()),
        initialfile=filename,
        defaultextension=suffix,
        filetypes=[
            ("PNG 图片", "*.png"),
            ("JPG 图片", "*.jpg"),
            ("ZIP 压缩包", "*.zip"),
            ("所有文件", "*.*"),
        ],
    )
    root.destroy()
    if not selected:
        return None
    return Path(selected)


def write_bytes(image: bytes, filename: str, fmt: str) -> dict:
    dest = choose_save_path(filename)
    if dest is None:
        return {"cancelled": True}
    if dest.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".zip"}:
        dest = dest.with_suffix(f".{fmt}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(image)
    remember_dir(dest)
    reveal_file(dest)
    return {"path": str(dest), "folder": str(dest.parent), "name": dest.name}


def gallery_dir() -> Path:
    pictures = Path.home() / "Pictures"
    base = pictures if pictures.is_dir() else default_save_dir()
    folder = base / "pictureTools" / "词云图库"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def gallery_file(name: str) -> Path:
    path = (gallery_dir() / Path(name).name).resolve()
    if path.parent != gallery_dir().resolve() or not path.is_file():
        raise FileNotFoundError("图库里没有这张图")
    return path


def list_gallery() -> list[dict]:
    items = []
    folder = gallery_dir()
    files = [p for p in folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[:40]:
        items.append({"id": path.name, "name": path.name, "url": f"/api/wordcloud/gallery/{path.name}"})
    return items


def add_to_gallery(image: bytes, fmt: str, label: str, shape: str) -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = safe_filename(f"{stamp}_{label}_{shape}", fmt)
    path = unique_path(gallery_dir(), filename)
    path.write_bytes(image)
    extras = sorted(gallery_dir().glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in extras[40:]:
        if old.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            try:
                old.unlink()
            except OSError:
                pass
    return {"id": path.name, "name": path.name, "url": f"/api/wordcloud/gallery/{path.name}"}


def gallery_zip_bytes() -> bytes:
    items = list_gallery()
    if not items:
        raise ValueError("图库还是空的。先导出或点「放入图库」")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            path = gallery_file(item["id"])
            zf.write(path, arcname=path.name)
    return buf.getvalue()


def write_chart(payload: dict) -> dict:
    title = str(payload.pop("filename", "") or payload.get("title") or "我的图表")
    image, fmt, label = render_image(payload)
    return write_bytes(image, safe_filename(f"{title}_{label}", fmt), fmt)


def write_wordcloud(payload: dict) -> dict:
    from .clouds import render_wordcloud

    title = str(payload.get("filename") or payload.get("title") or "我的词云")
    image, fmt, label = render_wordcloud(payload)
    return write_bytes(image, safe_filename(f"{title}_{label}", fmt), fmt)


def reveal_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception:
        pass


def render_image(payload: dict) -> tuple[bytes, str, str]:
    fmt = str(payload.pop("format", None) or "png").lower()
    bg = str(payload.pop("background_mode", None) or "").lower()
    if fmt not in MIME:
        raise ValueError(f"不支持的格式 {fmt}，可选: {', '.join(MIME)}")
    chart = Chart.from_mapping(payload)
    if bg == "transparent":
        if fmt in {"jpg", "jpeg"}:
            fmt = "png"
        return chart.to_bytes(fmt, transparent=True), fmt, "透明底"
    if bg == "white":
        return chart.to_bytes(fmt, background="white"), fmt, "白底"
    return chart.to_bytes(fmt), fmt, "图"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(WEBAPP / "static"),
        static_url_path="/static",
    )

    @app.get("/")
    def index():
        return send_from_directory(WEBAPP, "index.html")

    @app.get("/wordcloud")
    def wordcloud_page():
        return send_from_directory(WEBAPP, "wordcloud.html")

    @app.get("/api/wordcloud/meta")
    def wordcloud_meta():
        from .clouds import meta as cloud_meta

        return jsonify(cloud_meta())

    @app.post("/api/wordcloud/analyze")
    def wordcloud_analyze():
        from .clouds import analyze

        payload = request.get_json(silent=True) or {}
        if "file" in request.files:
            upload = request.files["file"]
            text = upload.read().decode("utf-8-sig", errors="ignore")
            payload["text"] = text
            name = (upload.filename or "").lower()
            if name.endswith((".csv", ".tsv")):
                payload["mode"] = "words"
            elif "mode" not in payload:
                payload["mode"] = "article"
        try:
            return jsonify(analyze(payload))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/wordcloud/render")
    def wordcloud_render():
        from .clouds import render_wordcloud

        payload = request.get_json(silent=True) or {}
        try:
            image, fmt, label = render_wordcloud(payload)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(io.BytesIO(image), mimetype=MIME[fmt], download_name=f"wordcloud_{label}.{fmt}")

    @app.post("/api/wordcloud/save")
    def wordcloud_save():
        payload = request.get_json(silent=True) or {}
        try:
            if payload.get("data"):
                import base64

                raw = base64.b64decode(str(payload["data"]).split(",")[-1])
                title = str(payload.get("filename") or "我的词云")
                fmt = str(payload.get("format") or "png").lower()
                shape = str(payload.get("shape") or "ring")
                label = "透明底" if payload.get("background_mode") == "transparent" else "白底"
                if payload.get("keep", True):
                    add_to_gallery(raw, fmt, label, shape)
                result = write_bytes(raw, safe_filename(title, fmt), fmt)
            else:
                result = write_wordcloud(payload)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/api/wordcloud/keep")
    def wordcloud_keep():
        payload = request.get_json(silent=True) or {}
        try:
            import base64

            raw = base64.b64decode(str(payload.get("data") or "").split(",")[-1])
            fmt = str(payload.get("format") or "png").lower()
            shape = str(payload.get("shape") or "ring")
            label = "透明底" if payload.get("background_mode") == "transparent" else "白底"
            item = add_to_gallery(raw, fmt, label, shape)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(item)

    @app.delete("/api/wordcloud/gallery/<name>")
    def wordcloud_gallery_delete(name: str):
        try:
            gallery_file(name).unlink()
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify({"ok": True})

    @app.get("/api/wordcloud/gallery")
    def wordcloud_gallery():
        return jsonify({"items": list_gallery(), "folder": str(gallery_dir())})

    @app.get("/api/wordcloud/gallery/zip")
    def wordcloud_gallery_zip():
        try:
            data = gallery_zip_bytes()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(
            io.BytesIO(data),
            mimetype="application/zip",
            download_name="词云图库.zip",
            as_attachment=True,
        )

    @app.post("/api/wordcloud/gallery/zip-save")
    def wordcloud_gallery_zip_save():
        try:
            data = gallery_zip_bytes()
            result = write_bytes(data, "词云图库.zip", "zip")
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/api/wordcloud/gallery/open")
    def wordcloud_gallery_open():
        folder = gallery_dir()
        reveal_file(folder)
        return jsonify({"folder": str(folder)})

    @app.get("/api/wordcloud/gallery/<name>")
    def wordcloud_gallery_item(name: str):
        try:
            path = gallery_file(name)
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        fmt = path.suffix.lower().lstrip(".")
        if fmt == "jpeg":
            fmt = "jpg"
        return send_file(path, mimetype=MIME.get(fmt, "image/png"), download_name=path.name, as_attachment="download" in request.args)

    @app.post("/api/wordcloud/gallery/<name>/save")
    def wordcloud_gallery_item_save(name: str):
        try:
            path = gallery_file(name)
            fmt = path.suffix.lower().lstrip(".") or "png"
            result = write_bytes(path.read_bytes(), path.name, fmt)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.get("/api/meta")
    def meta():
        return jsonify(
            {
                "types": [
                    {"id": item, "name": TYPE_LABELS.get(item, item), "hint": TYPE_HINTS.get(item, "")}
                    for item in available_types()
                ],
                "themes": [{"id": item, "name": THEME_LABELS.get(item, item)} for item in available_themes()],
                "presets": list(PRESETS.values()),
                "formats": ["png", "svg", "pdf", "jpg"],
            }
        )

    @app.post("/api/render")
    def render_chart():
        payload = request.get_json(silent=True) or {}
        if request.args.get("fmt") and "format" not in payload:
            payload["format"] = request.args.get("fmt")
        if request.args.get("bg") and "background_mode" not in payload:
            payload["background_mode"] = request.args.get("bg")
        try:
            image, fmt, label = render_image(payload)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(io.BytesIO(image), mimetype=MIME[fmt], download_name=f"chart_{label}.{fmt}")

    @app.post("/api/save")
    def save_chart():
        payload = request.get_json(silent=True) or {}
        try:
            result = write_chart(payload)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/api/import")
    def import_data():
        try:
            if "file" in request.files:
                upload = request.files["file"]
                text = upload.read().decode("utf-8-sig")
                data = parse_any(text, filename=upload.filename or "")
            else:
                body = request.get_json(silent=True) or {}
                data = parse_any(str(body.get("text") or ""), filename=str(body.get("filename") or ""))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(data)

    @app.post("/api/export")
    def export_data():
        payload = request.get_json(silent=True) or {}
        fmt = str(payload.pop("format", "json")).lower()
        try:
            data = Chart.from_mapping(payload).to_dict()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        if fmt == "yaml":
            text = dump_yaml(data)
            return send_file(io.BytesIO(text.encode("utf-8")), mimetype="text/yaml", download_name="chart.yaml")
        raw = json.dumps(data, ensure_ascii=False, indent=2)
        return send_file(io.BytesIO(raw.encode("utf-8")), mimetype="application/json", download_name="chart.json")

    return app


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    app = create_app()
    url = f"http://{host}:{port}"
    print(f"chartkit 网页已启动：{url}")
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)

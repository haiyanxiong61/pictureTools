"""本地网页：选类型、改数据、预览和下载。"""

from __future__ import annotations

import io
import json
import threading
import webbrowser
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


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(WEBAPP / "static"),
        static_url_path="/static",
    )

    @app.get("/")
    def index():
        return send_from_directory(WEBAPP, "index.html")

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
        fmt = str(payload.pop("format", None) or request.args.get("fmt") or "png").lower()
        bg = str(payload.pop("background_mode", None) or request.args.get("bg") or "").lower()
        if fmt not in MIME:
            return jsonify({"error": f"不支持的格式 {fmt}，可选: {', '.join(MIME)}"}), 400
        try:
            chart = Chart.from_mapping(payload)
            if bg == "transparent":
                if fmt in {"jpg", "jpeg"}:
                    fmt = "png"
                image = chart.to_bytes(fmt, transparent=True)
                name = f"chart_transparent.{fmt}"
            elif bg == "white":
                image = chart.to_bytes(fmt, background="white")
                name = f"chart_white.{fmt}"
            else:
                image = chart.to_bytes(fmt)
                name = f"chart.{fmt}"
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(io.BytesIO(image), mimetype=MIME[fmt], download_name=name)

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

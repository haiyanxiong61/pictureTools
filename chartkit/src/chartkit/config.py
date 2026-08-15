"""从 YAML / JSON / CSV 读取或导出图表配置。"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import yaml

from .spec import coerce_number


def load_config(path: str | Path) -> dict[str, Any]:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"找不到配置文件: {file}")
    return parse_any(file.read_text(encoding="utf-8-sig"), filename=file.name)


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def parse_any(text: str, filename: str = "") -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise ValueError("内容为空")
    suffix = Path(filename).suffix.lower()
    if suffix in {".yaml", ".yml"} or (raw[0] not in "{[" and ":" in raw.splitlines()[0] and "," not in raw.splitlines()[0]):
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("YAML 顶层必须是对象")
        return data
    if suffix == ".json" or raw[0] in "{[":
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON 顶层必须是对象")
        return data
    return parse_csv(raw)


def parse_csv(text: str) -> dict[str, Any]:
    sample = text[:400]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    rows = [row for row in csv.reader(io.StringIO(text), dialect) if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("CSV 没有有效行")

    header = [cell.strip() for cell in rows[0]]
    named = header[0] in {"", "名称", "系列", "分类", "name", "系列名"}
    if named:
        categories = header[1:]
        series: dict[str, list] = {}
        for row in rows[1:]:
            if not row or not str(row[0]).strip():
                continue
            values = [coerce_number(cell) for cell in row[1 : 1 + len(categories)]]
            while len(values) < len(categories):
                values.append(0)
            series[str(row[0]).strip()] = values
        return {"categories": categories, "series": series}

    categories = header
    series = {}
    for index, row in enumerate(rows[1:], start=1):
        values = [coerce_number(cell) for cell in row[: len(categories)]]
        while len(values) < len(categories):
            values.append(0)
        series[f"系列{index}"] = values
    if not series:
        series = {"值": [0] * len(categories)}
    return {"categories": categories, "series": series}

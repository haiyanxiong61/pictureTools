"""图表数据与样式规格，统一各类图表的输入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


Number = int | float
SeriesMap = dict[str, list[Number]]
META_KEYS = {"id", "name"}


def coerce_number(value: Any) -> Number:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if value is None or value == "":
        return 0
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1]
    if text in {"", "-", "—"}:
        return 0
    if "." in text or "e" in text.lower():
        return float(text)
    return int(text)


def as_list(values: Sequence[Any] | Number) -> list[Number]:
    if isinstance(values, (int, float)) and not isinstance(values, bool):
        return [values]
    if isinstance(values, str):
        parts = [part.strip() for part in values.replace("，", ",").split(",") if part.strip()]
        return [coerce_number(part) for part in parts]
    return [coerce_number(item) for item in values]


def coerce_series(series: Mapping[str, Any] | None) -> SeriesMap:
    if not series:
        return {}
    return {str(name): as_list(vals) for name, vals in series.items()}


def align_series(categories: list[str], series: SeriesMap) -> tuple[list[str], SeriesMap]:
    width = max([len(categories), *(len(vals) for vals in series.values())], default=0)
    cats = list(categories) + [f"列{i + 1}" for i in range(len(categories), width)]
    if not cats and width:
        cats = [str(i + 1) for i in range(width)]
    aligned = {name: list(vals) + [0] * (len(cats) - len(vals)) for name, vals in series.items()}
    return cats, aligned


def normalize_series(
    categories: Sequence[str] | None = None,
    values: Sequence[Number] | None = None,
    series: Mapping[str, Sequence[Number]] | None = None,
) -> tuple[list[str], SeriesMap]:
    if series:
        names = list(series)
        length = len(as_list(series[names[0]]))
        cats = list(categories) if categories else [str(i + 1) for i in range(length)]
        mapped = {name: as_list(series[name]) for name in names}
        for name, vals in mapped.items():
            if len(vals) != len(cats):
                raise ValueError(f"系列 {name!r} 长度 {len(vals)} 与分类数 {len(cats)} 不一致")
        return cats, mapped

    if values is None:
        raise ValueError("请提供 values 或 series")
    vals = as_list(values)
    cats = list(categories) if categories else [str(i + 1) for i in range(len(vals))]
    if len(cats) != len(vals):
        raise ValueError("categories 与 values 长度不一致")
    return cats, {"系列1": vals}


def from_dataframe(
    df: Any,
    x: str,
    y: str | Sequence[str],
    hue: str | None = None,
) -> tuple[list[str], SeriesMap]:
    if hue:
        seen: list[str] = []
        for cat in df[x].astype(str).tolist():
            if cat not in seen:
                seen.append(cat)
        mapped: SeriesMap = {}
        for key, group in df.groupby(hue, sort=False):
            lookup = {str(row): val for row, val in zip(group[x].astype(str), group[y])}
            mapped[str(key)] = [lookup.get(cat, 0) for cat in seen]
        return seen, mapped

    categories = [str(v) for v in df[x].tolist()]
    if isinstance(y, (list, tuple)):
        return categories, {col: as_list(df[col].tolist()) for col in y}
    return categories, {str(y): as_list(df[y].tolist())}


@dataclass
class ChartSpec:
    kind: str = "bar"
    categories: list[str] = field(default_factory=list)
    series: SeriesMap = field(default_factory=dict)
    lines: SeriesMap = field(default_factory=dict)
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    y2label: str = ""
    theme: str = "academic"
    figsize: tuple[float, float] = (10.5, 6.4)
    dpi: int = 200
    colors: list[str] | None = None
    line_colors: list[str] | None = None
    background: str | None = None
    bar_mode: str = "grouped"  # grouped | stacked | percent
    show_bar_labels: bool = True
    show_line_labels: bool = True
    show_counts: bool = True
    label_fmt: str = "{:.0f}"
    line_label_fmt: str = "{:.2f}"
    y_lim: tuple[float, float] | None = None
    y2_lim: tuple[float, float] | None = None
    grid: bool = True
    legend: bool = True
    legend_loc: str | None = None
    rotate_xticks: float = 0
    hole: float = 0.55  # donut
    bins: int = 20
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ChartSpec":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = dict(data)
        if "type" in payload and "kind" not in payload:
            payload["kind"] = payload.pop("type")
        if "bars" in payload and "series" not in payload:
            payload["series"] = payload.pop("bars")
        extra = payload.pop("extra", {})
        for key in META_KEYS:
            payload.pop(key, None)
        for key in ("figsize", "y_lim", "y2_lim"):
            value = payload.get(key)
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                payload[key] = tuple(value)
        if "series" in payload:
            payload["series"] = coerce_series(payload.get("series"))
        if "lines" in payload:
            payload["lines"] = coerce_series(payload.get("lines"))
        fields = {k: v for k, v in payload.items() if k in known}
        leftover = {k: v for k, v in payload.items() if k not in known}
        extra.update(leftover)
        spec = cls(**fields)
        spec.extra = extra
        if spec.kind not in {"histogram", "box", "gauge", "scatter"}:
            spec.categories, spec.series = align_series(spec.categories, spec.series)
            if spec.lines:
                _, spec.lines = align_series(spec.categories, spec.lines)
        elif spec.series and not spec.categories:
            first = next(iter(spec.series.values()))
            spec.categories = [str(i + 1) for i in range(len(first))]
        return spec

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "theme": self.theme,
            "title": self.title,
            "xlabel": self.xlabel,
            "ylabel": self.ylabel,
            "y2label": self.y2label,
            "figsize": list(self.figsize),
            "dpi": self.dpi,
            "bar_mode": self.bar_mode,
            "show_bar_labels": self.show_bar_labels,
            "show_line_labels": self.show_line_labels,
            "show_counts": self.show_counts,
            "label_fmt": self.label_fmt,
            "line_label_fmt": self.line_label_fmt,
            "grid": self.grid,
            "legend": self.legend,
            "rotate_xticks": self.rotate_xticks,
            "hole": self.hole,
            "bins": self.bins,
            "categories": self.categories,
            "series": self.series,
        }
        if self.lines:
            data["lines"] = self.lines
        if self.colors:
            data["colors"] = self.colors
        if self.background:
            data["background"] = self.background
        if self.y_lim:
            data["y_lim"] = list(self.y_lim)
        if self.y2_lim:
            data["y2_lim"] = list(self.y2_lim)
        if self.legend_loc:
            data["legend_loc"] = self.legend_loc
        return data

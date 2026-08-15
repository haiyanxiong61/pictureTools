"""对外的流畅 API：一行出图，也能链式改主题、标题、尺寸。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from matplotlib.figure import Figure

from .render import CHART_TYPES, render, save_figure
from .spec import ChartSpec, Number, from_dataframe, normalize_series
from .themes import list_themes


class Chart:
    """图表构建器。

    常用写法::

        Chart.combo(categories, bars=..., lines=...).theme("academic").save("a.png")
        Chart.bar(["Q1", "Q2"], [10, 18]).title("销量").save("b.png")
        Chart.from_file("chart.yaml").save("c.png")
    """

    def __init__(self, spec: ChartSpec | None = None, **kwargs: Any) -> None:
        self.spec = spec or ChartSpec.from_mapping(kwargs)

    def __repr__(self) -> str:
        return f"Chart(kind={self.spec.kind!r}, categories={len(self.spec.categories)})"

    # ----- 链式配置 -----
    def theme(self, name: str) -> "Chart":
        self.spec.theme = name
        return self

    def title(self, text: str) -> "Chart":
        self.spec.title = text
        return self

    def labels(self, xlabel: str = "", ylabel: str = "", y2label: str = "") -> "Chart":
        if xlabel:
            self.spec.xlabel = xlabel
        if ylabel:
            self.spec.ylabel = ylabel
        if y2label:
            self.spec.y2label = y2label
        return self

    def size(self, width: float, height: float) -> "Chart":
        self.spec.figsize = (width, height)
        return self

    def dpi(self, value: int) -> "Chart":
        self.spec.dpi = value
        return self

    def colors(self, *colors: str) -> "Chart":
        self.spec.colors = list(colors)
        return self

    def line_colors(self, *colors: str) -> "Chart":
        self.spec.line_colors = list(colors)
        return self

    def bg(self, color: str) -> "Chart":
        self.spec.background = color
        return self

    def ylim(self, low: float, high: float) -> "Chart":
        self.spec.y_lim = (low, high)
        return self

    def y2lim(self, low: float, high: float) -> "Chart":
        self.spec.y2_lim = (low, high)
        return self

    def rotate(self, degrees: float) -> "Chart":
        self.spec.rotate_xticks = degrees
        return self

    def hide_legend(self) -> "Chart":
        self.spec.legend = False
        return self

    def hide_labels(self) -> "Chart":
        self.spec.show_bar_labels = False
        self.spec.show_line_labels = False
        return self

    def option(self, **kwargs: Any) -> "Chart":
        for key, value in kwargs.items():
            if hasattr(self.spec, key):
                setattr(self.spec, key, value)
            else:
                self.spec.extra[key] = value
        return self

    # ----- 输出 -----
    def figure(self) -> Figure:
        return render(self.spec)

    def save(self, path: str | Path, dpi: int | None = None, transparent: bool = False) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fig = self.figure()
        save_figure(fig, str(target), dpi=dpi or self.spec.dpi, transparent=transparent)
        return target.resolve()

    def show(self) -> None:
        import matplotlib.pyplot as plt

        self.figure()
        plt.show()

    def to_bytes(self, fmt: str = "png", *, transparent: bool = False, background: str | None = None) -> bytes:
        import io

        import matplotlib.pyplot as plt

        fmt = "jpeg" if fmt == "jpg" else fmt
        if transparent and fmt == "jpeg":
            fmt = "png"
        fig = self.figure()
        if transparent:
            fig.patch.set_alpha(0)
            fig.patch.set_facecolor("none")
            for ax in fig.axes:
                ax.set_facecolor("none")
                ax.patch.set_alpha(0)
        elif background:
            fig.patch.set_alpha(1)
            fig.patch.set_facecolor(background)
            for ax in fig.axes:
                ax.set_facecolor(background)
                ax.patch.set_alpha(1)
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format=fmt,
            bbox_inches="tight",
            facecolor="none" if transparent else (background or fig.get_facecolor()),
            transparent=transparent,
            dpi=self.spec.dpi,
        )
        plt.close(fig)
        return buf.getvalue()

    def to_dict(self) -> dict[str, Any]:
        return self.spec.to_dict()

    # ----- 工厂方法 -----
    @classmethod
    def bar(
        cls,
        categories: Sequence[str] | None = None,
        values: Sequence[Number] | None = None,
        series: Mapping[str, Sequence[Number]] | None = None,
        mode: str = "grouped",
        **kwargs: Any,
    ) -> "Chart":
        cats, mapped = normalize_series(categories, values, series)
        return cls(ChartSpec(kind="bar", categories=cats, series=mapped, bar_mode=mode, **kwargs))

    @classmethod
    def stacked_bar(
        cls,
        categories: Sequence[str],
        series: Mapping[str, Sequence[Number]],
        percent: bool = False,
        **kwargs: Any,
    ) -> "Chart":
        mode = "percent" if percent else "stacked"
        return cls.bar(categories, series=series, mode=mode, **kwargs)

    @classmethod
    def hbar(
        cls,
        categories: Sequence[str] | None = None,
        values: Sequence[Number] | None = None,
        series: Mapping[str, Sequence[Number]] | None = None,
        mode: str = "grouped",
        **kwargs: Any,
    ) -> "Chart":
        cats, mapped = normalize_series(categories, values, series)
        return cls(ChartSpec(kind="hbar", categories=cats, series=mapped, bar_mode=mode, **kwargs))

    @classmethod
    def line(
        cls,
        categories: Sequence[str] | None = None,
        values: Sequence[Number] | None = None,
        series: Mapping[str, Sequence[Number]] | None = None,
        **kwargs: Any,
    ) -> "Chart":
        cats, mapped = normalize_series(categories, values, series)
        return cls(ChartSpec(kind="line", categories=cats, series=mapped, **kwargs))

    @classmethod
    def area(
        cls,
        categories: Sequence[str],
        series: Mapping[str, Sequence[Number]] | None = None,
        values: Sequence[Number] | None = None,
        stacked: bool = True,
        **kwargs: Any,
    ) -> "Chart":
        cats, mapped = normalize_series(categories, values, series)
        return cls(ChartSpec(kind="area", categories=cats, series=mapped, bar_mode="stacked" if stacked else "grouped", **kwargs))

    @classmethod
    def combo(
        cls,
        categories: Sequence[str],
        bars: Mapping[str, Sequence[Number]],
        lines: Mapping[str, Sequence[Number]] | None = None,
        bar_mode: str = "percent",
        **kwargs: Any,
    ) -> "Chart":
        """堆叠柱 + 双轴折线，适合情感分布、构成比 + 均值这类论文图。"""
        cats, mapped = normalize_series(categories, series=bars)
        return cls(
            ChartSpec(
                kind="combo",
                categories=cats,
                series=mapped,
                lines=dict(lines or {}),
                bar_mode=bar_mode,
                **kwargs,
            )
        )

    @classmethod
    def pie(
        cls,
        labels: Sequence[str],
        values: Sequence[Number],
        donut: bool = False,
        **kwargs: Any,
    ) -> "Chart":
        kind = "donut" if donut else "pie"
        return cls(ChartSpec(kind=kind, categories=list(labels), series={"值": list(values)}, **kwargs))

    @classmethod
    def donut(cls, labels: Sequence[str], values: Sequence[Number], **kwargs: Any) -> "Chart":
        return cls.pie(labels, values, donut=True, **kwargs)

    @classmethod
    def scatter(
        cls,
        x: Sequence[Number],
        y: Sequence[Number] | Mapping[str, Sequence[Number]],
        **kwargs: Any,
    ) -> "Chart":
        if isinstance(y, Mapping):
            series = {"x": list(x), **{k: list(v) for k, v in y.items()}}
        else:
            series = {"x": list(x), "y": list(y)}
        return cls(ChartSpec(kind="scatter", series=series, **kwargs))

    @classmethod
    def radar(
        cls,
        categories: Sequence[str],
        series: Mapping[str, Sequence[Number]],
        **kwargs: Any,
    ) -> "Chart":
        return cls(ChartSpec(kind="radar", categories=list(categories), series=dict(series), **kwargs))

    @classmethod
    def heatmap(
        cls,
        rows: Sequence[str],
        columns: Sequence[str],
        values: Sequence[Sequence[Number]],
        **kwargs: Any,
    ) -> "Chart":
        series = {row: list(vals) for row, vals in zip(rows, values)}
        return cls(ChartSpec(kind="heatmap", categories=list(columns), series=series, **kwargs))

    @classmethod
    def box(cls, series: Mapping[str, Sequence[Number]], **kwargs: Any) -> "Chart":
        return cls(ChartSpec(kind="box", series=dict(series), **kwargs))

    @classmethod
    def histogram(
        cls,
        values: Sequence[Number] | Mapping[str, Sequence[Number]],
        bins: int = 20,
        **kwargs: Any,
    ) -> "Chart":
        series = dict(values) if isinstance(values, Mapping) else {"分布": list(values)}
        return cls(ChartSpec(kind="histogram", series=series, bins=bins, **kwargs))

    @classmethod
    def waterfall(
        cls,
        categories: Sequence[str],
        values: Sequence[Number],
        last_is_total: bool = True,
        **kwargs: Any,
    ) -> "Chart":
        return cls(
            ChartSpec(
                kind="waterfall",
                categories=list(categories),
                series={"变动": list(values)},
                extra={"last_is_total": last_is_total},
                **kwargs,
            )
        )

    @classmethod
    def funnel(cls, stages: Sequence[str], values: Sequence[Number], **kwargs: Any) -> "Chart":
        return cls(ChartSpec(kind="funnel", categories=list(stages), series={"漏斗": list(values)}, **kwargs))

    @classmethod
    def gauge(cls, value: Number, low: float = 0, high: float = 100, **kwargs: Any) -> "Chart":
        return cls(ChartSpec(kind="gauge", series={"值": [value]}, y_lim=(low, high), **kwargs))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Chart":
        return cls(ChartSpec.from_mapping(data))

    @classmethod
    def from_file(cls, path: str | Path) -> "Chart":
        from .config import load_config

        return cls.from_mapping(load_config(path))

    @classmethod
    def from_dataframe(
        cls,
        df: Any,
        kind: str = "bar",
        x: str = "",
        y: str | Sequence[str] = "",
        hue: str | None = None,
        **kwargs: Any,
    ) -> "Chart":
        cats, series = from_dataframe(df, x=x, y=y, hue=hue)
        return cls(ChartSpec(kind=kind, categories=cats, series=series, **kwargs))

    @classmethod
    def batch(cls, config_dir: str | Path, output_dir: str | Path = "output") -> list[Path]:
        from .config import load_config

        folder = Path(config_dir)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for file in sorted(folder.glob("*.yaml")) + sorted(folder.glob("*.yml")) + sorted(folder.glob("*.json")):
            chart = cls.from_mapping(load_config(file))
            suffix = file.stem + ".png"
            saved.append(chart.save(out / suffix))
        return saved


def available_types() -> list[str]:
    return list(CHART_TYPES)


def available_themes() -> list[str]:
    return list_themes()

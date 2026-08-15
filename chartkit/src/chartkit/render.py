"""把 ChartSpec 画成 matplotlib 图。"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from .fonts import apply_chinese_font
from .spec import ChartSpec
from .themes import Theme, get_theme

CHART_TYPES = [
    "bar",
    "hbar",
    "line",
    "area",
    "combo",
    "pie",
    "donut",
    "scatter",
    "radar",
    "heatmap",
    "box",
    "histogram",
    "waterfall",
    "funnel",
    "gauge",
]


def render(spec: ChartSpec, theme: Theme | None = None) -> Figure:
    apply_chinese_font()
    theme = theme or get_theme(
        spec.theme,
        background=spec.background,
        bar_colors=spec.colors or None,
        line_colors=spec.line_colors or None,
        legend_loc=spec.legend_loc,
    )
    if spec.colors:
        theme = theme.override(bar_colors=spec.colors)
    if spec.line_colors:
        theme = theme.override(line_colors=spec.line_colors)
    if spec.background:
        theme = theme.override(background=spec.background, axes_facecolor=spec.background)

    fig, ax = _make_axes(spec, theme)
    drawer = {
        "bar": _draw_bar,
        "hbar": _draw_hbar,
        "line": _draw_line,
        "area": _draw_area,
        "combo": _draw_combo,
        "pie": _draw_pie,
        "donut": _draw_pie,
        "scatter": _draw_scatter,
        "radar": _draw_radar,
        "heatmap": _draw_heatmap,
        "box": _draw_box,
        "histogram": _draw_histogram,
        "waterfall": _draw_waterfall,
        "funnel": _draw_funnel,
        "gauge": _draw_gauge,
    }.get(spec.kind)
    if drawer is None:
        raise ValueError(f"不支持的图表类型 {spec.kind!r}，可选: {', '.join(CHART_TYPES)}")
    drawer(fig, ax, spec, theme)
    _apply_common(fig, ax, spec, theme)
    fig.tight_layout()
    if spec.legend and spec.kind not in {"pie", "donut", "gauge", "funnel", "heatmap"}:
        _place_legend(fig, ax, spec, theme)
    return fig


def _make_axes(spec: ChartSpec, theme: Theme) -> tuple[Figure, Axes]:
    if spec.kind == "radar":
        fig = plt.figure(figsize=spec.figsize, dpi=spec.dpi, facecolor=theme.background)
        ax = fig.add_subplot(111, polar=True)
    else:
        fig, ax = plt.subplots(figsize=spec.figsize, dpi=spec.dpi)
    fig.patch.set_facecolor(theme.background)
    ax.set_facecolor(theme.axes_facecolor)
    for spine in ax.spines.values():
        spine.set_color(theme.spine_color)
        spine.set_linewidth(0.9)
    ax.tick_params(colors=theme.text_color, labelsize=theme.tick_size)
    return fig, ax


def _palette(colors: list[str], n: int) -> list[str]:
    if not colors:
        colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2"]
    if n <= len(colors):
        return colors[:n]
    reps = math.ceil(n / len(colors))
    return (colors * reps)[:n]


def _annotate_box(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    theme: Theme,
    italic: bool = True,
    offset: tuple[float, float] = (0, 8),
    ha: str = "center",
) -> None:
    ax.annotate(
        text,
        xy=(x, y),
        xytext=offset,
        textcoords="offset points",
        ha=ha,
        va="center" if offset[0] else "bottom",
        fontsize=9,
        color=theme.text_color,
        fontstyle="italic" if italic else "normal",
        bbox=dict(boxstyle="square,pad=0.18", facecolor="white", edgecolor="#222222", linewidth=0.7),
        zorder=6,
    )


def _bar_label(ax: Axes, x: float, y: float, text: str, theme: Theme, horizontal: bool = False) -> None:
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        color=theme.text_color,
        fontsize=9,
        zorder=5,
    )


def _draw_bar(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    names = list(spec.series)
    colors = _palette(theme.bar_colors, len(names))
    x = np.arange(len(cats), dtype=float)
    mode = spec.bar_mode
    totals = np.zeros(len(cats), dtype=float)
    for vals in spec.series.values():
        totals += np.array(vals, dtype=float)

    if mode == "grouped" and len(names) > 1:
        width = 0.8 / len(names)
        for i, name in enumerate(names):
            vals = np.array(spec.series[name], dtype=float)
            offset = (i - (len(names) - 1) / 2) * width
            bars = ax.bar(
                x + offset,
                vals,
                width=width * 0.92,
                color=colors[i],
                edgecolor=theme.bar_edgecolor,
                linewidth=theme.bar_linewidth,
                label=name,
                zorder=3,
            )
            if spec.show_bar_labels:
                for bar, val in zip(bars, vals):
                    if val == 0:
                        continue
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(),
                        spec.label_fmt.format(val),
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color=theme.text_color,
                    )
    else:
        bottoms = np.zeros(len(cats), dtype=float)
        for i, name in enumerate(names):
            raw = np.array(spec.series[name], dtype=float)
            heights = raw.copy()
            if mode == "percent":
                heights = np.divide(raw, totals, out=np.zeros_like(raw), where=totals != 0) * 100
            bars = ax.bar(
                x,
                heights,
                bottom=bottoms,
                color=colors[i],
                edgecolor=theme.bar_edgecolor,
                linewidth=theme.bar_linewidth,
                label=name,
                width=0.68 if spec.kind == "combo" else 0.62,
                zorder=3,
            )
            if spec.show_bar_labels or spec.show_counts:
                for xi, height, raw_v, bottom in zip(x, heights, raw, bottoms):
                    if raw_v == 0:
                        continue
                    # 很薄的分段仍然标数字，和论文图一致
                    if height < 0.8:
                        continue
                    text = spec.label_fmt.format(raw_v if spec.show_counts else height)
                    _bar_label(ax, xi, bottom + height / 2, text, theme)
            bottoms += heights

    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    if mode == "percent":
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_locator(MultipleLocator(10))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        if spec.y_lim:
            ax.set_ylim(*spec.y_lim)
    elif spec.y_lim:
        ax.set_ylim(*spec.y_lim)
    if spec.grid:
        ax.yaxis.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha, zorder=0)
        ax.set_axisbelow(True)


def _draw_hbar(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    names = list(spec.series)
    colors = _palette(theme.bar_colors, len(names))
    y = np.arange(len(cats), dtype=float)
    if spec.bar_mode == "grouped" and len(names) > 1:
        height = 0.8 / len(names)
        for i, name in enumerate(names):
            vals = np.array(spec.series[name], dtype=float)
            offset = (i - (len(names) - 1) / 2) * height
            ax.barh(
                y + offset,
                vals,
                height=height * 0.92,
                color=colors[i],
                edgecolor=theme.bar_edgecolor,
                label=name,
                zorder=3,
            )
    else:
        lefts = np.zeros(len(cats), dtype=float)
        totals = sum(np.array(v, dtype=float) for v in spec.series.values())
        for i, name in enumerate(names):
            raw = np.array(spec.series[name], dtype=float)
            widths = raw / totals * 100 if spec.bar_mode == "percent" else raw
            ax.barh(
                y,
                widths,
                left=lefts,
                color=colors[i],
                edgecolor=theme.bar_edgecolor,
                label=name,
                height=0.62,
                zorder=3,
            )
            if spec.show_bar_labels:
                for yi, w, left, raw_v in zip(y, widths, lefts, raw):
                    if raw_v == 0:
                        continue
                    ax.text(left + w / 2, yi, spec.label_fmt.format(raw_v), ha="center", va="center", fontsize=9)
            lefts += widths
    ax.set_yticks(y)
    ax.set_yticklabels(cats)
    if spec.grid:
        ax.xaxis.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha, zorder=0)
        ax.set_axisbelow(True)


def _draw_line(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    names = list(spec.series)
    colors = _palette(theme.line_colors or theme.bar_colors, len(names))
    x = np.arange(len(cats), dtype=float)
    for i, name in enumerate(names):
        vals = np.array(spec.series[name], dtype=float)
        marker = theme.line_markers[i % len(theme.line_markers)]
        ax.plot(
            x,
            vals,
            color=colors[i],
            marker=marker,
            linewidth=2.0,
            markersize=7,
            label=name,
            zorder=4,
        )
        if spec.show_line_labels:
            for xi, yi in zip(x, vals):
                _annotate_box(ax, xi, yi, spec.line_label_fmt.format(yi), theme)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    if spec.y_lim:
        ax.set_ylim(*spec.y_lim)
    if spec.grid:
        ax.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha, zorder=0)


def _draw_area(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    names = list(spec.series)
    colors = _palette(theme.bar_colors, len(names))
    x = np.arange(len(cats), dtype=float)
    stack = spec.bar_mode in {"stacked", "percent"}
    if stack:
        arrays = [np.array(spec.series[n], dtype=float) for n in names]
        if spec.bar_mode == "percent":
            totals = np.sum(arrays, axis=0)
            arrays = [np.divide(a, totals, out=np.zeros_like(a), where=totals != 0) * 100 for a in arrays]
        ax.stackplot(x, *arrays, labels=names, colors=colors, alpha=0.85)
    else:
        for i, name in enumerate(names):
            vals = np.array(spec.series[name], dtype=float)
            ax.fill_between(x, vals, color=colors[i], alpha=0.35, label=name)
            ax.plot(x, vals, color=colors[i], linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    if spec.grid:
        ax.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha, zorder=0)


def _draw_combo(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    _draw_bar(fig, ax, spec, theme)
    if not spec.lines:
        return

    ax2 = ax.twinx()
    ax2.set_facecolor("none")
    names = list(spec.lines)
    colors = _palette(theme.line_colors, len(names))
    x = np.arange(len(spec.categories), dtype=float)
    for i, name in enumerate(names):
        vals = np.array(spec.lines[name], dtype=float)
        marker = theme.line_markers[i % len(theme.line_markers)]
        ax2.plot(
            x,
            vals,
            color=colors[i],
            marker=marker,
            linewidth=1.8,
            markersize=8,
            label=name,
            zorder=5,
        )
        if spec.show_line_labels:
            # 标在点右侧，避免挡住柱内计数
            side = 16 if i % 2 == 0 else -16
            ha = "left" if side > 0 else "right"
            for xi, yi in zip(x, vals):
                _annotate_box(
                    ax2,
                    xi,
                    yi,
                    spec.line_label_fmt.format(yi),
                    theme,
                    offset=(side, 0),
                    ha=ha,
                )
    y2 = spec.y2_lim or (0.0, 1.0)
    ax2.set_ylim(*y2)
    ax2.yaxis.set_major_locator(MultipleLocator(0.1))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax2.tick_params(colors=theme.text_color, labelsize=theme.tick_size)
    for spine in ax2.spines.values():
        spine.set_color(theme.spine_color)
    if spec.y2label:
        ax2.set_ylabel(spec.y2label, color=theme.text_color, fontsize=theme.label_size)
    # 把折线图例项挂到主轴，方便统一放置
    ax._chartkit_twin = ax2  # type: ignore[attr-defined]


def _draw_pie(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = list(spec.series)
    if len(names) == 1:
        labels = spec.categories
        values = list(spec.series[names[0]])
    else:
        labels = names
        values = [sum(spec.series[n]) for n in names]
    colors = _palette(theme.bar_colors, len(values))
    explode = spec.extra.get("explode")
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        startangle=90,
        pctdistance=0.72,
        explode=explode,
        wedgeprops=dict(width=1 - spec.hole if spec.kind == "donut" else 1, edgecolor=theme.background, linewidth=1.5),
        textprops=dict(color=theme.text_color, fontsize=10),
    )
    for text in autotexts:
        text.set_color("#111111")
    ax.set_aspect("equal")
    if spec.legend:
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)


def _draw_scatter(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = list(spec.series)
    colors = _palette(theme.bar_colors, max(1, len(names) // 2 or 1))
    if "x" in spec.series and "y" in spec.series:
        ax.scatter(spec.series["x"], spec.series["y"], s=46, color=colors[0], alpha=0.85, label="散点")
    else:
        # 每个系列是 y，x 用 categories 或 0..n
        x = spec.series.get("x")
        idx = 0
        for name, vals in spec.series.items():
            if name == "x":
                continue
            xs = x if x is not None else list(range(len(vals)))
            ax.scatter(xs, vals, s=46, color=colors[idx % len(colors)], alpha=0.85, label=name)
            idx += 1
    if spec.grid:
        ax.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha)


def _draw_radar(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    names = list(spec.series)
    colors = _palette(theme.bar_colors, len(names))
    angles = np.linspace(0, 2 * np.pi, len(cats), endpoint=False).tolist()
    angles += angles[:1]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), cats)
    for i, name in enumerate(names):
        vals = list(spec.series[name])
        vals += vals[:1]
        ax.plot(angles, vals, color=colors[i], linewidth=2, marker="o", label=name)
        ax.fill(angles, vals, color=colors[i], alpha=0.18)
    ax.tick_params(colors=theme.text_color)
    if spec.y_lim:
        ax.set_ylim(*spec.y_lim)


def _draw_heatmap(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = list(spec.series)
    matrix = np.array([spec.series[n] for n in names], dtype=float)
    cmap = spec.extra.get("cmap", "YlGnBu" if theme.name != "dark" else "magma")
    im = ax.imshow(matrix, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(spec.categories)))
    ax.set_xticklabels(spec.categories)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    if spec.show_bar_labels:
        vmax = matrix.max() if matrix.size else 1
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                color = "white" if matrix[i, j] > vmax * 0.65 else theme.text_color
                ax.text(j, i, spec.label_fmt.format(matrix[i, j]), ha="center", va="center", color=color, fontsize=9)


def _draw_box(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = list(spec.series)
    data = [spec.series[n] for n in names]
    colors = _palette(theme.bar_colors, len(names))
    result = ax.boxplot(data, tick_labels=names, patch_artist=True, medianprops=dict(color="#222222"))
    for patch, color in zip(result["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
    if spec.grid:
        ax.yaxis.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha)


def _draw_histogram(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = list(spec.series)
    colors = _palette(theme.bar_colors, len(names))
    for i, name in enumerate(names):
        ax.hist(
            spec.series[name],
            bins=spec.bins,
            color=colors[i],
            alpha=0.7 if len(names) > 1 else 0.9,
            label=name,
            edgecolor=theme.bar_edgecolor,
        )
    if spec.grid:
        ax.yaxis.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha)


def _draw_waterfall(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    cats = spec.categories
    values = np.array(next(iter(spec.series.values())), dtype=float)
    colors = theme.bar_colors
    pos_c, neg_c, total_c = colors[2] if len(colors) > 2 else "#70ad47", colors[0], colors[1] if len(colors) > 1 else "#8a8a8a"
    running = 0.0
    bottoms = []
    heights = []
    fills = []
    for i, val in enumerate(values):
        is_total = spec.extra.get("total_index") == i or (
            spec.extra.get("last_is_total", True) and i == len(values) - 1
        ) or (spec.extra.get("first_is_total", True) and i == 0)
        if is_total:
            bottoms.append(0)
            heights.append(val)
            fills.append(total_c)
            running = val
        else:
            bottoms.append(running if val >= 0 else running + val)
            heights.append(abs(val))
            fills.append(pos_c if val >= 0 else neg_c)
            running += val
    bars = ax.bar(cats, heights, bottom=bottoms, color=fills, edgecolor=theme.bar_edgecolor, width=0.62, zorder=3)
    connector_x = []
    connector_y = []
    cursor = 0.0
    for i, val in enumerate(values[:-1]):
        is_total = spec.extra.get("total_index") == i or (
            spec.extra.get("first_is_total", True) and i == 0
        )
        cursor = values[i] if is_total else cursor + val
        connector_x += [i + 0.31, i + 0.69, None]
        connector_y += [cursor, cursor, None]
    ax.plot(connector_x, connector_y, color=theme.spine_color, linewidth=0.8, linestyle="--")
    if spec.show_bar_labels:
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + bar.get_height() + max(heights) * 0.02,
                spec.label_fmt.format(val),
                ha="center",
                va="bottom",
                fontsize=9,
            )
    if spec.grid:
        ax.yaxis.grid(True, linestyle="--", color=theme.grid_color, alpha=theme.grid_alpha, zorder=0)


def _draw_funnel(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    names = spec.categories
    values = np.array(next(iter(spec.series.values())), dtype=float)
    colors = _palette(theme.bar_colors, len(values))
    max_v = max(values) if len(values) else 1
    y = np.arange(len(values))[::-1]
    widths = values / max_v
    ax.barh(y, widths, color=colors, height=0.7, left=(1 - widths) / 2, edgecolor=theme.bar_edgecolor)
    for yi, name, val, w in zip(y, names, values, widths):
        ax.text(0.5, yi, f"{name}  {spec.label_fmt.format(val)}", ha="center", va="center", color=theme.text_color, fontsize=10)
    ax.set_xlim(0, 1)
    ax.axis("off")


def _draw_gauge(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    value = float(next(iter(spec.series.values()))[0])
    vmin, vmax = spec.y_lim or (0, 100)
    ratio = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    colors = theme.bar_colors
    ax.pie(
        [ratio, 1 - ratio],
        startangle=180,
        counterclock=False,
        colors=[colors[0], "#d9d9d9" if theme.name != "dark" else "#444444"],
        wedgeprops=dict(width=0.28, edgecolor=theme.background),
    )
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.15, 1.2)
    ax.text(0, 0.08, spec.label_fmt.format(value) if spec.label_fmt != "{:.0f}" else f"{value:.0f}", ha="center", va="center", fontsize=22, color=theme.text_color)
    if spec.title:
        ax.text(0, -0.05, spec.title, ha="center", va="top", fontsize=12, color=theme.text_color)
        spec.title = ""
    ax.axis("off")


def _apply_common(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    if spec.title and spec.kind != "gauge":
        ax.set_title(spec.title, color=theme.text_color, fontsize=theme.title_size, pad=12)
    if spec.xlabel:
        ax.set_xlabel(spec.xlabel, color=theme.text_color, fontsize=theme.label_size)
    if spec.ylabel:
        ax.set_ylabel(spec.ylabel, color=theme.text_color, fontsize=theme.label_size)
    if spec.rotate_xticks:
        for label in ax.get_xticklabels():
            label.set_rotation(spec.rotate_xticks)
            label.set_horizontalalignment("right")


def _place_legend(fig: Figure, ax: Axes, spec: ChartSpec, theme: Theme) -> None:
    handles, labels = ax.get_legend_handles_labels()
    twin = getattr(ax, "_chartkit_twin", None)
    if twin is not None:
        h2, l2 = twin.get_legend_handles_labels()
        handles += h2
        labels += l2
    if not handles:
        return
    loc = spec.legend_loc or theme.legend_loc
    ncol = theme.legend_ncol or min(len(handles), 5)
    if loc == "lower center":
        ax.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=ncol,
            frameon=False,
            fontsize=theme.legend_size,
        )
        fig.subplots_adjust(bottom=0.18)
    else:
        ax.legend(handles, labels, loc=loc, frameon=False, fontsize=theme.legend_size, ncol=ncol)


def save_figure(fig: Figure, path: str, dpi: int | None = None, transparent: bool = False) -> str:
    fig.savefig(path, dpi=dpi or fig.dpi, bbox_inches="tight", facecolor=fig.get_facecolor(), transparent=transparent)
    plt.close(fig)
    return path

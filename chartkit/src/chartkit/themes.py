"""内置主题：学术灰绿、论文白底、彩色、柔和、深色、商务。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass
class Theme:
    name: str
    background: str = "#ffffff"
    axes_facecolor: str = "#ffffff"
    text_color: str = "#222222"
    spine_color: str = "#222222"
    grid_color: str = "#d0d0d0"
    grid_alpha: float = 0.7
    bar_colors: list[str] = field(default_factory=list)
    line_colors: list[str] = field(default_factory=list)
    line_markers: list[str] = field(default_factory=lambda: ["o", "s", "D", "^", "v", "P"])
    annotation_box: bool = True
    legend_loc: str = "lower center"
    legend_ncol: int | None = None
    title_size: int = 15
    label_size: int = 11
    tick_size: int = 10
    legend_size: int = 10
    bar_edgecolor: str = "#333333"
    bar_linewidth: float = 0.6

    def override(self, **kwargs) -> "Theme":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


THEMES: dict[str, Theme] = {
    "academic": Theme(
        name="academic",
        background="#c8e0c4",
        axes_facecolor="#c8e0c4",
        text_color="#111111",
        spine_color="#111111",
        grid_color="#9cbc98",
        grid_alpha=0.55,
        bar_colors=["#4d4d4d", "#8a8a8a", "#c8c8c8", "#6e6e6e", "#a8a8a8"],
        line_colors=["#2b2b2b", "#5a5a5a", "#7a7a7a"],
        line_markers=["s", "D", "o"],
        legend_loc="lower center",
    ),
    "paper": Theme(
        name="paper",
        background="#ffffff",
        axes_facecolor="#ffffff",
        bar_colors=["#4a4a4a", "#7d7d7d", "#b0b0b0", "#6a6a6a", "#949494"],
        line_colors=["#222222", "#555555", "#888888"],
        line_markers=["s", "D", "o"],
        grid_color="#e6e6e6",
    ),
    "colorful": Theme(
        name="colorful",
        background="#ffffff",
        axes_facecolor="#fafafa",
        bar_colors=["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2"],
        line_colors=["#4c78a8", "#e45756", "#54a24b", "#f58518"],
        grid_color="#e8e8e8",
        bar_edgecolor="#ffffff",
        bar_linewidth=0.4,
    ),
    "pastel": Theme(
        name="pastel",
        background="#f7f4ef",
        axes_facecolor="#f7f4ef",
        bar_colors=["#8da0cb", "#fc8d62", "#66c2a5", "#e78ac3", "#a6d854", "#ffd92f"],
        line_colors=["#5c6b8a", "#c46a4a", "#3f8f76"],
        grid_color="#e4ddd2",
        bar_edgecolor="#d8d0c4",
    ),
    "dark": Theme(
        name="dark",
        background="#1e1e1e",
        axes_facecolor="#252526",
        text_color="#f0f0f0",
        spine_color="#888888",
        grid_color="#3c3c3c",
        bar_colors=["#5b9bd5", "#ed7d31", "#70ad47", "#ffc000", "#9b59b6", "#1abc9c"],
        line_colors=["#5b9bd5", "#ed7d31", "#70ad47"],
        bar_edgecolor="#1e1e1e",
    ),
    "business": Theme(
        name="business",
        background="#ffffff",
        axes_facecolor="#ffffff",
        bar_colors=["#1f4e79", "#2e75b6", "#5b9bd5", "#9dc3e6", "#c00000"],
        line_colors=["#c00000", "#1f4e79", "#548235"],
        grid_color="#eeeeee",
        bar_edgecolor="#1f4e79",
        bar_linewidth=0.3,
    ),
}

DEFAULT_THEME = "academic"


def get_theme(name: str | Theme | None = None, **overrides) -> Theme:
    if isinstance(name, Theme):
        theme = name
    else:
        key = (name or DEFAULT_THEME).lower()
        if key not in THEMES:
            known = ", ".join(THEMES)
            raise ValueError(f"未知主题 {name!r}，可选: {known}")
        theme = THEMES[key]
    return theme.override(**overrides) if overrides else theme


def list_themes() -> list[str]:
    return list(THEMES)

"""自动探测并注册中文字体，避免图表中文变成方框。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from matplotlib import font_manager

PREFERRED_FONTS = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Songti SC",
    "STHeiti",
    "Arial Unicode MS",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Micro Hei",
]

FONT_FILES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("C:/Windows/Fonts/msyh.ttf"),
]


def _register_system_files() -> None:
    for path in FONT_FILES:
        if path.exists():
            try:
                font_manager.fontManager.addfont(str(path))
            except (ValueError, OSError):
                continue


@lru_cache(maxsize=1)
def find_chinese_font() -> str:
    _register_system_files()
    available = {item.name for item in font_manager.fontManager.ttflist}
    for name in PREFERRED_FONTS:
        if name in available:
            return name

    for item in font_manager.fontManager.ttflist:
        lowered = item.name.lower()
        if any(key in lowered for key in ("cjk", "hei", "song", "pingfang", "yahei", "gothic")):
            return item.name
    return "DejaVu Sans"


def apply_chinese_font(family: str | None = None) -> str:
    import matplotlib as mpl

    resolved = family or find_chinese_font()
    mpl.rcParams["font.family"] = [resolved, "DejaVu Sans", "sans-serif"]
    mpl.rcParams["axes.unicode_minus"] = False
    return resolved


@lru_cache(maxsize=1)
def find_chinese_font_path() -> str:
    for path in FONT_FILES:
        if path.exists():
            return str(path)
    name = find_chinese_font()
    for item in font_manager.fontManager.ttflist:
        if item.name == name and Path(item.fname).exists():
            return item.fname
    return font_manager.findfont(name)

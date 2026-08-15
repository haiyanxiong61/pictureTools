"""chartkit：自动生成柱状、折线、组合、饼图等各类图表。"""

from .api import Chart, available_themes, available_types
from .spec import ChartSpec
from .themes import Theme, get_theme, list_themes

__all__ = [
    "Chart",
    "ChartSpec",
    "Theme",
    "available_themes",
    "available_types",
    "get_theme",
    "list_themes",
]
__version__ = "0.1.0"

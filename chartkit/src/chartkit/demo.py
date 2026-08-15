"""内置示例数据，一键生成图库。"""

from __future__ import annotations

from pathlib import Path

from .api import Chart


def sentiment_combo() -> Chart:
    """复现论文里常见的情感构成（柱）+ 均值（线）组合图。"""
    return (
        Chart.combo(
            categories=["人物", "叙述角度", "情节"],
            bars={
                "neg": [187, 3, 84],
                "neu": [12, 0, 9],
                "pos": [409, 184, 301],
            },
            lines={
                "pos_average": [0.63, 0.91, 0.79],
                "neg_average": [0.37, 0.09, 0.21],
            },
            bar_mode="percent",
            show_counts=True,
        )
        .theme("academic")
        .size(9.6, 6.2)
        .dpi(220)
        .y2lim(0, 1)
    )


def generate_demos(output_dir: str | Path = "output") -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    charts: list[tuple[str, Chart]] = [
        ("01_sentiment_combo.png", sentiment_combo()),
        (
            "02_grouped_bar.png",
            Chart.bar(
                ["一季度", "二季度", "三季度", "四季度"],
                series={"产品A": [32, 40, 38, 51], "产品B": [22, 28, 35, 30], "产品C": [14, 18, 16, 24]},
            )
            .theme("colorful")
            .title("季度销量对比")
            .labels(ylabel="销量"),
        ),
        (
            "03_line.png",
            Chart.line(
                ["1月", "2月", "3月", "4月", "5月", "6月"],
                series={"完成率": [0.62, 0.68, 0.71, 0.77, 0.80, 0.86], "目标": [0.70, 0.70, 0.72, 0.75, 0.78, 0.80]},
                line_label_fmt="{:.2f}",
            )
            .theme("business")
            .title("月度完成率")
            .ylim(0.5, 1.0),
        ),
        (
            "04_donut.png",
            Chart.donut(["正面", "中性", "负面"], [694, 21, 274]).theme("pastel").title("整体情感占比"),
        ),
        (
            "05_radar.png",
            Chart.radar(
                ["人物", "情节", "语言", "结构", "主题"],
                {"作品A": [0.82, 0.76, 0.69, 0.74, 0.88], "作品B": [0.70, 0.84, 0.80, 0.66, 0.72]},
            )
            .theme("colorful")
            .title("作品维度对比")
            .ylim(0, 1),
        ),
        (
            "06_heatmap.png",
            Chart.heatmap(
                ["人物", "叙述角度", "情节"],
                ["neg", "neu", "pos"],
                [[187, 12, 409], [3, 0, 184], [84, 9, 301]],
            )
            .theme("paper")
            .title("情感频数热力图"),
        ),
        (
            "07_waterfall.png",
            Chart.waterfall(
                ["期初", "新增", "回流", "流失", "期末"],
                [120, 45, 18, -32, 151],
            )
            .theme("business")
            .title("用户增减拆解"),
        ),
        (
            "08_funnel.png",
            Chart.funnel(["访问", "注册", "试用", "付费"], [1200, 540, 210, 86]).theme("colorful").title("转化漏斗"),
        ),
        (
            "09_gauge.png",
            Chart.gauge(79, title="综合得分").theme("business"),
        ),
        (
            "10_area.png",
            Chart.area(
                ["周一", "周二", "周三", "周四", "周五"],
                {"正面": [40, 48, 52, 47, 60], "负面": [18, 15, 20, 16, 12]},
            )
            .theme("pastel")
            .title("一周情感趋势"),
        ),
        (
            "11_histogram.png",
            Chart.histogram({"正面分": [0.62, 0.71, 0.80, 0.74, 0.88, 0.91, 0.67, 0.83, 0.77, 0.69]}, bins=8)
            .theme("paper")
            .title("正面分分布"),
        ),
        (
            "12_hbar.png",
            Chart.hbar(["人物", "叙述角度", "情节"], [608, 187, 394])
            .theme("academic")
            .title("各维度评述数量"),
        ),
    ]

    saved: list[Path] = []
    for name, chart in charts:
        saved.append(chart.save(out / name))
    return saved

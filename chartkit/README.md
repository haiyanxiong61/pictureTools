# chartkit

在 Python 里自动生成论文/报告常用图表。默认带中文字体探测，支持堆叠柱 + 双轴折线组合图，也能用 YAML 批量出图。

## 安装

```bash
cd chartkit
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 网页出图台

```bash
cd chartkit
source .venv/bin/activate
python -m chartkit serve
```

浏览器会打开 `http://127.0.0.1:8765`。也可以直接运行项目根目录的 `run.py`。

## 打包成 Windows 桌面软件

必须在 Windows 电脑上打包（Mac 打不出 exe）。完整步骤见 `打包成Windows软件.txt`。

1. 把整个 `chartkit` 文件夹拷到 Windows
2. 安装 Python 3.10+，勾选 Add python.exe to PATH
3. 双击 `packaging/windows/build.bat`
4. 把 `dist/pictureTools.zip` 发给对方
5. 对方解压后双击 `pictureTools.exe`，不用装 Python

页面上可以：

- 切换 15 种图表类型（保留当前数据并立刻重画）
- 切换主题、改标题/坐标轴、分组/堆叠/百分比
- 编辑表格，删除列/行；直方图和箱线图用逗号分隔原始数据
- 导入 CSV / JSON / YAML，或粘贴 Excel 表格
- 导出 JSON / YAML 配置
- 下载 PNG / SVG / PDF / JPG
- 高级选项：尺寸、DPI、坐标范围、旋转、图例、网格、自动出图
- 本地会记住上次编辑的数据

## 怎么运行（不要直接点开 `__main__.py`）

`src/chartkit/__main__.py` 是给 `python -m chartkit` 用的包入口。在 IDE 里对这个文件点 Run，Python 会把它当成普通脚本，相对导入就会报错。

请用下面任一方式：

```bash
# 打开网页
python -m chartkit serve

# 命令行出示例图
python -m chartkit demo -o output

# 或运行示例脚本
python examples/generate_all.py
python examples/quickstart.py
```

## 30 秒上手

```python
from chartkit import Chart

# 你给的那种情感构成 + 均值组合图
Chart.combo(
    categories=["人物", "叙述角度", "情节"],
    bars={"neg": [187, 3, 84], "neu": [12, 0, 9], "pos": [409, 184, 301]},
    lines={"pos_average": [0.63, 0.91, 0.79], "neg_average": [0.37, 0.09, 0.21]},
).theme("academic").save("output/sentiment.png")
```

链式改样式：

```python
(
    Chart.bar(["Q1", "Q2", "Q3"], [12, 18, 15])
    .theme("colorful")
    .title("季度销量")
    .labels(ylabel="件数")
    .size(8, 5)
    .dpi(300)
    .save("output/bar.png")
)
```

## 支持的图表

| 方法 | 类型 |
| --- | --- |
| `Chart.bar` / `Chart.stacked_bar` / `Chart.hbar` | 柱状 / 堆叠 / 百分比堆叠 / 条形 |
| `Chart.line` / `Chart.area` | 折线 / 面积 |
| `Chart.combo` | 柱 + 折线双轴（论文情感图） |
| `Chart.pie` / `Chart.donut` | 饼图 / 环形图 |
| `Chart.scatter` / `Chart.radar` / `Chart.heatmap` | 散点 / 雷达 / 热力 |
| `Chart.box` / `Chart.histogram` | 箱线 / 直方图 |
| `Chart.waterfall` / `Chart.funnel` / `Chart.gauge` | 瀑布 / 漏斗 / 仪表盘 |

## 主题

`academic`（灰绿学术风，默认）、`paper`、`colorful`、`pastel`、`dark`、`business`

## 用配置文件出图

```yaml
# examples/configs/sentiment_combo.yaml
type: combo
theme: academic
bar_mode: percent
categories: [人物, 叙述角度, 情节]
bars:
  neg: [187, 3, 84]
  neu: [12, 0, 9]
  pos: [409, 184, 301]
lines:
  pos_average: [0.63, 0.91, 0.79]
  neg_average: [0.37, 0.09, 0.21]
```

```bash
chartkit render examples/configs/sentiment_combo.yaml -o output/sentiment.png
chartkit batch examples/configs -o output
chartkit demo -o output
```

Python 里同样可以：

```python
Chart.from_file("examples/configs/sentiment_combo.yaml").save("output/sentiment.png")
Chart.batch("examples/configs", "output")
```

## 从 DataFrame 出图

```python
import pandas as pd
from chartkit import Chart

df = pd.DataFrame({
    "维度": ["人物", "人物", "情节", "情节"],
    "情感": ["pos", "neg", "pos", "neg"],
    "数量": [409, 187, 301, 84],
})
Chart.from_dataframe(df, kind="bar", x="维度", y="数量", hue="情感").theme("paper").save("a.png")
```

需要先 `pip install pandas`。

## 命令行

```bash
chartkit serve
chartkit types
chartkit themes
chartkit demo -o output
```

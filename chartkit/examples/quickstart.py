from pathlib import Path
import sys

src = Path(__file__).resolve().parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from chartkit import Chart

output = Path(__file__).resolve().parents[1] / "output"
output.mkdir(exist_ok=True)

Chart.combo(
    categories=["人物", "叙述角度", "情节"],
    bars={"neg": [187, 3, 84], "neu": [12, 0, 9], "pos": [409, 184, 301]},
    lines={"pos_average": [0.63, 0.91, 0.79], "neg_average": [0.37, 0.09, 0.21]},
).theme("academic").save(output / "sentiment_combo.png")

print("已生成", output / "sentiment_combo.png")

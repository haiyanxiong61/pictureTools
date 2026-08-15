"""生成全部示例图到 ../output/"""

from pathlib import Path
import sys

# 允许在未 pip install 时，直接用 IDE 运行本文件
src = Path(__file__).resolve().parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from chartkit.demo import generate_demos

if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "output"
    for path in generate_demos(output):
        print(path)

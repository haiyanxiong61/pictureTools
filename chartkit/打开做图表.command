#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "第一次使用，正在准备，请稍等…"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
else
  source .venv/bin/activate
fi
echo "浏览器马上会打开。关掉这个窗口，网页也会一起关掉。"
python -m chartkit serve

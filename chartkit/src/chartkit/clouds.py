from __future__ import annotations

import io
import math
import random
import re
from collections import Counter
from typing import Any

import numpy as np

from .fonts import find_chinese_font_path

STOPWORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很",
    "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    "我们", "你们", "他们", "这是", "这个", "那个", "什么", "可以", "因为", "所以", "如果", "但是",
    "还是", "或者", "以及", "然后", "已经", "为了", "不是", "真的", "这样", "那样", "这么", "那么",
    "一些", "还有", "就是", "只是", "而且", "并且", "虽然", "不过", "因此", "其中", "通过", "进行",
    "同时", "之后", "之前", "现在", "目前", "方面", "问题", "工作", "能够", "开始", "这些",
    "那些", "一样", "比较", "非常", "可能", "需要", "应该", "觉得", "知道", "出来", "起来", "下来",
    "怎么", "哪个", "哪些", "关于", "对于", "作为", "根据", "由于", "另外", "此外", "首先", "其次",
    "最后", "一直", "不断", "分别", "各种", "所有", "每个", "本次", "此次", "以上", "以下", "左右",
    "之间", "等等", "其实", "当然", "比如", "例如", "包括", "相关", "出现", "发生", "成为", "使用",
    "一场", "一位", "一项", "一种",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "be",
}

SKIP_POS = {
    "x", "w", "p", "c", "u", "uj", "ul", "ug", "ud", "uv", "uz", "y", "e", "o", "r", "zg",
}

USER_WORDS = [
    "小米", "雷军", "SU7", "小米汽车", "发布会", "造车", "新能源汽车", "智能驾驶",
    "自动驾驶", "工程师", "第一次", "三年", "研发", "电池", "测试", "上市",
]

PALETTES = {
    "colorful": ["#1f4e79", "#2e75b6", "#5b9bd5", "#548235", "#70ad47", "#c6a000", "#ffc000", "#7b4b94", "#5b2c6f", "#ed7d31"],
    "bluegreen": ["#1f4e79", "#2e75b6", "#5b9bd5", "#385723", "#548235", "#70ad47", "#a9d08e"],
    "ocean": ["#0b3d5c", "#1a6b9a", "#2e86ab", "#48a9a6", "#7dd3c7", "#1565c0"],
    "sunset": ["#6d1a36", "#c0392b", "#e67e22", "#f39c12", "#f7dc6f", "#8e3b1f"],
    "business": ["#1f4e79", "#2e75b6", "#5b9bd5", "#c00000", "#833c0c"],
    "academic": ["#222222", "#4d4d4d", "#6e6e6e", "#8a8a8a", "#3f6b46", "#5a7d5c"],
    "pastel": ["#8da0cb", "#fc8d62", "#66c2a5", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494"],
    "ink": ["#111111", "#333333", "#555555", "#1f4e79", "#2e75b6"],
}

SHAPES = [
    {"id": "circle", "name": "圆形"},
    {"id": "oval", "name": "椭圆"},
    {"id": "ring", "name": "环形"},
    {"id": "heart", "name": "心形"},
    {"id": "square", "name": "方形"},
    {"id": "rect", "name": "矩形"},
    {"id": "diamond", "name": "菱形"},
    {"id": "star", "name": "星形"},
    {"id": "cloud", "name": "云朵"},
]

PALETTE_META = [
    {"id": "colorful", "name": "彩色"},
    {"id": "bluegreen", "name": "蓝绿"},
    {"id": "ocean", "name": "海蓝"},
    {"id": "sunset", "name": "暖色"},
    {"id": "business", "name": "商务"},
    {"id": "academic", "name": "灰绿"},
    {"id": "pastel", "name": "柔和"},
    {"id": "ink", "name": "墨色"},
]

SAMPLE_WORDS = """小米 36
汽车 32
造车 28
SU7 18
赛车 16
雷军 14
勇气 13
三年 12
团队 12
电池 11
测试 11
发布会 10
工程师 10
第一次 10
研发 9
产品 9
上市 9
朋友 8
同事 8
行业 8
高管 7
轿车 7
投入 7
时间 7
评论 6
专门 6
巨大 6
甚至 6
一定 6
用户 6
体验 6
质量 6
安全 6
智能 6
驾驶 5
设计 5
技术 5
创新 5
梦想 5
挑战 5
坚持 5
努力 5
成功 5
未来 5
"""

SAMPLE_TEXT = """小米正式发布SU7，雷军说造车是一场巨大的挑战。团队用三年时间做测试、做电池、做研发。
发布会上，工程师、同事、朋友和高管都在。这是第一次造轿车，也是第一次把赛车的勇气带到汽车行业。
上市之后，用户关注驾驶、安全、智能和体验。小米造车投入了巨大时间，也带来了新的产品和技术。"""


def _require_wordcloud():
    try:
        from PIL import Image
        from wordcloud import WordCloud
    except ImportError as exc:
        raise RuntimeError("词云还没装好。请先执行：pip install wordcloud jieba pillow") from extra_exc
    return WordCloud, Image


def parse_word_lines(text: str) -> dict[str, float]:
    freq: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        match = re.match(r"^(.*?)(?:[,，\s\t:：]+)(\d+(?:\.\d+)?)\s*$", line)
        if match:
            word = match.group(1).strip()
            weight = float(match.group(2))
        else:
            word, weight = line, 1.0
        if word:
            freq[word] = freq.get(word, 0) + weight
    return freq


def rows_to_freq(rows: list[Any] | None) -> dict[str, float]:
    freq: dict[str, float] = {}
    for row in rows or []:
        if isinstance(row, dict):
            word = str(row.get("word") or row.get("name") or "").strip()
            count = row.get("count", row.get("value", 1))
        elif isinstance(row, (list, tuple)) and row:
            word = str(row[0]).strip()
            count = row[1] if len(row) > 1 else 1
        else:
            continue
        if not word:
            continue
        try:
            weight = float(count)
        except (TypeError, ValueError):
            weight = 1.0
        if weight <= 0:
            continue
        freq[word] = freq.get(word, 0) + weight
    return freq


def freq_to_rows(freq: dict[str, float]) -> list[dict[str, Any]]:
    items = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
    rows = []
    for word, count in items:
        value: int | float = int(count) if float(count).is_integer() else round(count, 2)
        rows.append({"word": word, "count": value})
    return rows


def keep_word_list(payload: dict[str, Any]) -> list[str]:
    extra = str(payload.get("keep_words") or payload.get("user_words") or "")
    parts = re.split(r"[,，、\s]+", extra)
    words = [item.strip() for item in parts if item.strip()]
    seen: list[str] = []
    for word in USER_WORDS + words:
        if word not in seen:
            seen.append(word)
    return seen


def apply_user_dict(words: list[str]) -> None:
    import jieba

    for word in words:
        jieba.add_word(word, freq=8000, tag="nz")


def cut_article(text: str, extra_stop: set[str] | None = None, keep_words: list[str] | None = None) -> dict[str, float]:
    try:
        import jieba.posseg as pseg
    except ImportError as extra_exc:
        raise RuntimeError("拆中文词还没装好。请先执行：pip install jieba") from extra_exc
    apply_user_dict(keep_words or USER_WORDS)
    stops = STOPWORDS | {item.strip() for item in (extra_stop or set()) if item.strip()}
    counts: Counter[str] = Counter()
    cleaned = re.sub(r"\s+", " ", text)
    for token in pseg.cut(cleaned, HMM=True):
        word = token.word.strip()
        flag = token.flag or ""
        if not word or word in stops:
            continue
        if flag in SKIP_POS:
            continue
        if re.fullmatch(r"[\W_]+", word, flags=re.UNICODE):
            continue
        if re.fullmatch(r"\d+", word):
            continue
        if len(word) == 1 and not re.search(r"[A-Za-z0-9]", word):
            continue
        counts[word] += 1
    return dict(counts)


def extra_stopwords(payload: dict[str, Any]) -> set[str]:
    return {part.strip() for part in str(payload.get("stopwords") or "").replace("，", ",").split(",") if part.strip()}


def looks_like_word_list(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    if len(text) >= 60 and any(mark in text for mark in ("。", "！", "？", "；", "，")):
        return False
    numbered = sum(1 for line in lines if re.search(r"[,，\s\t:：]\s*\d+(\.\d+)?\s*$", line))
    return numbered >= max(3, len(lines) * 0.7)


def frequencies_from_payload(payload: dict[str, Any]) -> dict[str, float]:
    extra = extra_stopwords(payload)
    keep = keep_word_list(payload)
    if payload.get("rows"):
        freq = rows_to_freq(payload.get("rows"))
    elif isinstance(payload.get("words"), dict) and payload.get("words"):
        freq = {str(key).strip(): float(val) for key, val in payload["words"].items() if str(key).strip()}
    else:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("请先把词或文章粘贴到左边")
        mode = str(payload.get("mode") or "auto")
        if mode == "auto":
            mode = "words" if looks_like_word_list(text) else "article"
        freq = cut_article(text, extra, keep) if mode == "article" else parse_word_lines(text)
    freq = {word: weight for word, weight in freq.items() if word not in extra}
    if not freq:
        raise ValueError("没有找出可用的词。可以多贴一点文字，或一行一个词")
    return freq


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    text = str(data.get("text") or "").strip()
    if not data.get("rows") and not data.get("words"):
        if not data.get("mode") or data.get("mode") == "auto":
            data["mode"] = "words" if looks_like_word_list(text) else "article"
    freq = frequencies_from_payload(data)
    rows = freq_to_rows(freq)
    return {
        "rows": rows,
        "total": len(rows),
        "sum": round(sum(item["count"] for item in rows), 2),
        "mode": data.get("mode") or "article",
    }


def make_mask(shape: str, size: int = 1400) -> np.ndarray | None:
    from PIL import Image, ImageDraw

    name = (shape or "").strip().lower()
    if name in {"square", "rect", ""}:
        return None

    if name == "heart":
        yy, xx = np.ogrid[:size, :size]
        center = (size - 1) / 2.0
        mask = np.full((size, size), 255, dtype=np.uint8)
        x = (xx - center) / (size * 0.38)
        y = (center - yy) / (size * 0.38) - 0.18
        heart = (x * x + y * y - 1) ** 3 - (x * x) * (y ** 3)
        mask[heart <= 0] = 0
        return mask

    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2.0
    pad = size * 0.05

    if name == "oval":
        rx, ry = size * 0.46, size * 0.34
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=0)
    elif name == "ring":
        outer, inner = size * 0.48, size * 0.18
        draw.ellipse([cx - outer, cy - outer, cx + outer, cy + outer], fill=0)
        draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=255)
    elif name == "diamond":
        draw.polygon([(cx, pad), (size - pad, cy), (cx, size - pad), (pad, cy)], fill=0)
    elif name == "star":
        pts = []
        outer, inner = size * 0.46, size * 0.20
        for i in range(10):
            radius = outer if i % 2 == 0 else inner
            ang = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
        draw.polygon(pts, fill=0)
    elif name == "cloud":
        s = float(size)
        draw.ellipse([s * 0.14, s * 0.46, s * 0.86, s * 0.88], fill=0)
        draw.ellipse([s * 0.10, s * 0.38, s * 0.42, s * 0.72], fill=0)
        draw.ellipse([s * 0.28, s * 0.22, s * 0.62, s * 0.62], fill=0)
        draw.ellipse([s * 0.50, s * 0.26, s * 0.82, s * 0.64], fill=0)
        draw.ellipse([s * 0.68, s * 0.40, s * 0.92, s * 0.76], fill=0)
    else:
        draw.ellipse([pad, pad, size - pad, size - pad], fill=0)
    return np.array(img)


def color_func(palette: list[str], rng: random.Random):
    def _color(*_args, **_kwargs) -> str:
        return rng.choice(palette)

    return _color


def render_wordcloud(payload: dict[str, Any]) -> tuple[bytes, str, str]:
    WordCloud, Image = _require_wordcloud()
    fmt = str(payload.get("format") or "png").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    bg = str(payload.get("background_mode") or "white").lower()
    if bg == "transparent" and fmt == "jpg":
        fmt = "png"
    shape = str(payload.get("shape") or "circle")
    palette_name = str(payload.get("palette") or "colorful")
    palette = list(PALETTES.get(palette_name, PALETTES["colorful"]))
    max_words = int(payload.get("max_words") or 80)
    seed = int(payload.get("seed") or 7)
    scale = float(payload.get("scale") or 1.4)
    size = int(1000 * max(0.8, min(scale, 2.2)))
    prefer = float(payload.get("prefer_horizontal") or 0.65)
    freq = frequencies_from_payload(payload)
    font_path = find_chinese_font_path()
    if shape == "rect":
        width, height = int(size * 1.55), int(size * 0.72)
        mask = None
    elif shape == "square":
        width, height = size, size
        mask = None
    else:
        mask = make_mask(shape, size=size)
        width, height = size, size
    rng = random.Random(seed)
    background = None if bg == "transparent" else "#ffffff"
    cloud = WordCloud(
        font_path=font_path,
        width=width,
        height=height,
        background_color=background,
        mode="RGBA" if bg == "transparent" else "RGB",
        mask=mask,
        max_words=max(8, min(max_words, 400)),
        prefer_horizontal=max(0.0, min(prefer, 1.0)),
        relative_scaling=0.5,
        collocations=False,
        min_font_size=8,
        max_font_size=max(40, int(size * 0.16)),
        random_state=seed,
        color_func=color_func(palette, rng),
        contour_width=0,
        margin=4,
    )
    image = cloud.generate_from_frequencies(freq).to_image()
    if fmt == "jpg":
        rgb = Image.new("RGB", image.size, "#ffffff")
        rgb.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = rgb
        save_fmt = "JPEG"
    else:
        save_fmt = "PNG"
    buf = io.BytesIO()
    image.save(buf, format=save_fmt, quality=95)
    label = "透明底" if bg == "transparent" else "白底"
    return buf.getvalue(), ("jpg" if fmt == "jpg" else "png"), label


def meta() -> dict[str, Any]:
    palettes = []
    for item in PALETTE_META:
        colors = PALETTES.get(item["id"], PALETTES["colorful"])
        palettes.append({**item, "colors": colors[:5]})
    return {
        "palettes": palettes,
        "shapes": SHAPES,
        "sample_words": SAMPLE_WORDS.strip(),
        "sample_text": SAMPLE_TEXT.strip(),
    }

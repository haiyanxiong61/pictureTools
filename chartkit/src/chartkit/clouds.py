from __future__ import annotations

import io
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
    "没有", "还是", "不是", "一个", "我们", "他们", "你们", "自己", "什么", "怎么", "哪个", "哪些",
    "这个", "那个", "这样", "那样", "因为", "所以", "如果", "虽然", "但是", "而且", "或者", "以及",
    "进行", "通过", "关于", "对于", "作为", "根据", "由于", "另外", "此外", "首先", "其次", "最后",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "be",
}

PALETTES = {
    "colorful": ["#1f4e79", "#2e75b6", "#5b9bd5", "#548235", "#70ad47", "#c6a000", "#ffc000", "#7b4b94", "#5b2c6f", "#ed7d31"],
    "bluegreen": ["#1f4e79", "#2e75b6", "#5b9bd5", "#385723", "#548235", "#70ad47", "#a9d08e"],
    "academic": ["#222222", "#4d4d4d", "#6e6e6e", "#8a8a8a", "#3f6b46", "#5a7d5c"],
    "business": ["#1f4e79", "#2e75b6", "#5b9bd5", "#c00000", "#833c0c"],
    "pastel": ["#8da0cb", "#fc8d62", "#66c2a5", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494"],
}

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
        raise RuntimeError("词云还没装好。请先执行：pip install wordcloud jieba pillow") from exc
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


def cut_article(text: str, extra_stop: set[str] | None = None) -> dict[str, float]:
    try:
        import jieba
    except ImportError as exc:
        raise RuntimeError("拆中文词还没装好。请先执行：pip install jieba") from exc
    stops = STOPWORDS | {item.strip() for item in (extra_stop or set()) if item.strip()}
    counts: Counter[str] = Counter()
    for token in jieba.lcut(text):
        word = token.strip()
        if not word or word in stops:
            continue
        if re.fullmatch(r"[\W_]+", word, flags=re.UNICODE):
            continue
        if len(word) == 1 and not re.search(r"[A-Za-z0-9]", word):
            continue
        counts[word] += 1
    return dict(counts)


def extra_stopwords(payload: dict[str, Any]) -> set[str]:
    return {part.strip() for part in str(payload.get("stopwords") or "").replace("，", ",").split(",") if part.strip()}


def frequencies_from_payload(payload: dict[str, Any]) -> dict[str, float]:
    extra = extra_stopwords(payload)
    if payload.get("rows"):
        freq = rows_to_freq(payload.get("rows"))
    elif isinstance(payload.get("words"), dict) and payload.get("words"):
        freq = {str(key).strip(): float(val) for key, val in payload["words"].items() if str(key).strip()}
    else:
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("请先填词，或粘贴一段文字后点「拆成词表」")
        mode = str(payload.get("mode") or "words")
        freq = cut_article(text, extra) if mode == "article" else parse_word_lines(text)
    freq = {word: weight for word, weight in freq.items() if word not in extra}
    if not freq:
        raise ValueError("没有找出可用的词。可以换一段更长的文字，或在词表里加词")
    return freq


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    if not data.get("rows") and not data.get("words"):
        data["mode"] = data.get("mode") or "article"
    freq = frequencies_from_payload(data)
    rows = freq_to_rows(freq)
    return {"rows": rows, "total": len(rows), "sum": round(sum(freq.values()), 2)}


def make_mask(shape: str, size: int = 1400) -> np.ndarray | None:
    if shape in {"square", "rect", ""}:
        return None
    yy, xx = np.ogrid[:size, :size]
    center = (size - 1) / 2.0
    mask = np.full((size, size), 255, dtype=np.uint8)
    if shape == "oval":
        rx, ry = size * 0.46, size * 0.34
        oval = ((xx - center) / rx) ** 2 + ((yy - center) / ry) ** 2
        mask[oval <= 1] = 0
        return mask
    if shape == "heart":
        x = (xx - center) / (size * 0.38)
        y = (center - yy) / (size * 0.38) - 0.18
        heart = (x * x + y * y - 1) ** 3 - (x * x) * (y ** 3)
        mask[heart <= 0] = 0
        return mask
    radius = size * 0.48
    dist = (xx - center) ** 2 + (yy - center) ** 2
    if shape == "ring":
        inner = radius * 0.32
        mask[(dist <= radius ** 2) & (dist >= inner ** 2)] = 0
    else:
        mask[dist <= radius ** 2] = 0
    return mask


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
    shape = str(payload.get("shape") or "ring")
    palette_name = str(payload.get("palette") or "colorful")
    palette = list(PALETTES.get(palette_name, PALETTES["colorful"]))
    max_words = int(payload.get("max_words") or 80)
    seed = int(payload.get("seed") or 7)
    scale = float(payload.get("scale") or 1.4)
    size = int(1000 * max(0.8, min(scale, 2.2)))
    prefer = float(payload.get("prefer_horizontal") or 0.65)
    freq = frequencies_from_payload(payload)
    font_path = find_chinese_font_path()
    mask = make_mask(shape, size=size)
    width, height = (size, size) if mask is not None else (int(size * 1.2), int(size * 0.78))
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
    return {
        "palettes": [
            {"id": "colorful", "name": "彩色"},
            {"id": "bluegreen", "name": "蓝绿"},
            {"id": "pastel", "name": "柔和"},
            {"id": "academic", "name": "学术灰绿"},
            {"id": "business", "name": "商务蓝"},
        ],
        "shapes": [
            {"id": "ring", "name": "环形"},
            {"id": "circle", "name": "圆形"},
            {"id": "oval", "name": "椭圆"},
            {"id": "square", "name": "方形"},
            {"id": "heart", "name": "心形"},
        ],
        "layouts": [
            {"id": "0.95", "name": "几乎都横着"},
            {"id": "0.65", "name": "有横有竖"},
            {"id": "0.35", "name": "多一些竖着"},
        ],
        "sample_words": SAMPLE_WORDS.strip(),
        "sample_text": SAMPLE_TEXT.strip(),
        "sample_rows": freq_to_rows(parse_word_lines(SAMPLE_WORDS)),
    }
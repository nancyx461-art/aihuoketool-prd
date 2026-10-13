import re
from pathlib import Path

from PIL import ImageFont

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]

MAX_CHARS = 13


def find_font(custom=None):
    for p in ([custom] if custom else []) + FONT_CANDIDATES:
        if p and Path(p).exists():
            return str(p)
    raise RuntimeError("找不到中文字体，请在 config.yaml 的 video.subtitle_font 里填一个 .ttf/.ttc 路径")


def load_font(path, size):
    return ImageFont.truetype(path, size)


def _split(text):
    """按标点把一句话拆成不超过 MAX_CHARS 的字幕块，标点不显示。"""
    parts = [p for p in re.split(r"[，。！？；、,.!?;：:…\s]+", text) if p]
    out = []
    for p in parts:
        while len(p) > MAX_CHARS:
            cut = MAX_CHARS if len(p) - MAX_CHARS >= 4 else len(p) // 2
            out.append(p[:cut])
            p = p[cut:]
        if out and len(out[-1]) + len(p) <= 7:
            out[-1] += " " + p
        else:
            out.append(p)
    return out or [text]


def build_cues(lines, spans):
    """返回字幕块：[(开始, 结束, 文本, 所属台词序号)]，时长按字数分配。"""
    cues = []
    for idx, (line, (start, end)) in enumerate(zip(lines, spans)):
        pieces = _split(line["text"])
        total = sum(len(p) for p in pieces)
        t = start
        for p in pieces:
            d = (end - start) * len(p) / total
            cues.append((t, t + d, p, idx))
            t += d
    return cues


def _ts(sec):
    ms = int(round(sec * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(cues, path):
    rows = []
    for i, (s, e, text, _) in enumerate(cues, 1):
        rows += [str(i), f"{_ts(s)} --> {_ts(e)}", text, ""]
    Path(path).write_text("\n".join(rows), encoding="utf-8")

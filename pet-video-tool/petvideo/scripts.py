import copy
import datetime as dt
import json
import random
import re
import urllib.request

from .config import ROOT
from .script_bank import SCRIPTS

EMOTIONS = ("calm", "happy", "sad", "shock", "angry")
HISTORY_FILE = ROOT / "output" / "history.json"

PROMPT = """你是一个短视频编剧，为宠物 IP 写一条 30~50 秒的竖屏口播脚本，由宠物用第一人称对着镜头说。

【宠物 IP】
名字：{name}（{species}）
人设：{persona}
口头禅：{catchphrase}

【受众】职场打工人。
【今天的主题】{theme}

【要求】
1. 内容围绕职场：有趣的职场梗、职场小故事或打工人日常，口语化、有画面感，可以玩梗。
2. 结构：开头 1 句强钩子（3 秒内抓人）→ 2~4 句吐槽/讲故事（制造共鸣）→ 1 句反转或洞察，透露一点道理 → 1 句温暖的安慰 → 结尾 1 句互动或口头禅。
3. 最重要的是让打工人有共鸣、被理解、得到情绪上的安慰；道理点到为止，不说教，不鸡汤堆砌。
4. 每句不超过 25 个字，总字数 150~230 字，共 7~10 句。
5. 每句标注宠物的情绪 emotion，只能是：calm / happy / sad / shock / angry。
6. 把最能戳中人、透露道理的那一句标记 "highlight": true（只标一句）。
7. 不要和这些已经发过的标题重复：{recent}

【只输出 JSON，不要任何解释】格式：
{{"title": "12字以内的封面标题", "theme": "{theme}", "lines": [{{"text": "...", "emotion": "calm"}}, ...], "caption": "发布时的一句话文案", "tags": ["职场", "..."]}}
"""


def _load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def record_history(script):
    history = _load_history()
    history.append({"date": dt.date.today().isoformat(), "title": script["title"], "theme": script.get("theme")})
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history[-200:], ensure_ascii=False, indent=2), encoding="utf-8")


def _fill(text, pet):
    return text.replace("{name}", pet["name"]).replace("{catchphrase}", pet.get("catchphrase", ""))


def _normalize(script, pet):
    lines = []
    for line in script.get("lines", []):
        text = _fill(str(line.get("text", "")).strip(), pet)
        if not text:
            continue
        emotion = line.get("emotion", "calm")
        lines.append({
            "text": text,
            "emotion": emotion if emotion in EMOTIONS else "calm",
            "highlight": bool(line.get("highlight")),
        })
    if not lines:
        raise ValueError("脚本没有任何台词")
    script["lines"] = lines
    script["title"] = _fill(script.get("title") or lines[0]["text"][:12], pet)
    script.setdefault("caption", "")
    script.setdefault("tags", ["职场", "打工人"])
    return script


def _call_llm(llm, prompt):
    body = json.dumps({
        "model": llm["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": llm.get("temperature", 1.0),
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        llm["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {llm['api_key']}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    match = re.search(r"\{.*\}", content, re.S)
    return json.loads(match.group(0) if match else content)


def _from_bank(theme, date):
    used = {h["title"] for h in _load_history()}
    if theme:
        for s in SCRIPTS:
            if theme in s["theme"] or s["theme"] in theme:
                return copy.deepcopy(s)
    fresh = [s for s in SCRIPTS if s["title"] not in used] or SCRIPTS
    return copy.deepcopy(fresh[date.toordinal() % len(fresh)])


def generate_script(cfg, theme=None, date=None):
    """返回 (script, source)。有 LLM_API_KEY 时调用大模型，否则使用内置脚本库。"""
    date = date or dt.date.today()
    pet, llm = cfg["pet"], cfg["llm"]

    if llm.get("api_key"):
        themes = llm.get("themes") or ["打工人的日常"]
        theme = theme or random.Random(date.toordinal()).choice(themes)
        recent = "、".join(h["title"] for h in _load_history()[-30:]) or "无"
        prompt = PROMPT.format(
            name=pet["name"], species=pet.get("species", "宠物"), persona=pet.get("persona", ""),
            catchphrase=pet.get("catchphrase", ""), theme=theme, recent=recent,
        )
        try:
            script = _call_llm(llm, prompt)
            script.setdefault("theme", theme)
            return _normalize(script, pet), f"llm:{llm['model']}"
        except Exception as e:  # noqa: BLE001
            print(f"[脚本] 大模型调用失败，改用内置脚本库：{e}")

    return _normalize(_from_bank(theme, date), pet), "builtin"


def script_to_markdown(script, pet):
    rows = [f"# {script['title']}", "", f"- 主题：{script.get('theme', '')}", f"- 出镜：{pet['name']}", ""]
    rows.append("| # | 情绪 | 台词 |")
    rows.append("|---|---|---|")
    for i, line in enumerate(script["lines"], 1):
        text = f"**{line['text']}**" if line.get("highlight") else line["text"]
        rows.append(f"| {i} | {line['emotion']} | {text} |")
    rows += ["", f"**发布文案**：{script.get('caption', '')}", "",
             "**话题**：" + " ".join("#" + t for t in script.get("tags", []))]
    return "\n".join(rows) + "\n"

"""剧情模式的分镜素材：优先用你放进 shots/ 的素材，其次调用火山方舟 Seedance 用 IP 参考图生成视频。"""

import base64
import io
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .config import resolve

MEDIA_EXT = (".mp4", ".mov", ".m4v", ".webm", ".png", ".jpg", ".jpeg", ".webp")
DEFAULT_STYLE = ("写实摄影风格，电影感自然光，温暖治愈，浅景深，竖屏构图。"
                 "宠物像人一样站立或坐着，动作可爱拟人；画面中的人类只拍身体或背影，不露正脸；画面里不要出现任何文字和字幕。")


def shot_prompt(line, pet, media_cfg):
    parts = [
        f"主角：{pet.get('appearance') or pet.get('species', '一只宠物')}，全程保持和参考图完全一致的外形。",
        f"场景：{line.get('scene', '')}。" if line.get("scene") else "",
        f"动作：{line.get('action', '')}。" if line.get("action") else "",
        f"镜头：{line.get('camera', '')}。" if line.get("camera") else "",
        f"情绪：{line['emotion']}，对应这句旁白：「{line['text']}」。",
        media_cfg.get("style") or DEFAULT_STYLE,
    ]
    return "".join(p for p in parts if p)


def write_shot_list(script, pet, media_cfg, path):
    rows = [f"# 《{script['title']}》分镜表", "",
            "把每个镜头生成好的视频/图片命名为 `shot_01.mp4`、`shot_02.png`……放进同目录的 `shots/` 文件夹，",
            "然后运行 `python make_video.py --from-script <本目录>/script.json` 重新合成。", ""]
    for i, line in enumerate(script["lines"], 1):
        rows += [f"## 镜头 {i:02d}", f"- 旁白：{line['text']}",
                 f"- 场景：{line.get('scene', '')}　动作：{line.get('action', '')}　镜头：{line.get('camera', '')}",
                 "- 提示词（可直接粘贴到即梦/可灵，并上传 IP 参考图）：", "", f"> {shot_prompt(line, pet, media_cfg)}", ""]
    Path(path).write_text("\n".join(rows), encoding="utf-8")


def _existing(shots_dir, i):
    for ext in MEDIA_EXT:
        p = shots_dir / f"shot_{i:02d}{ext}"
        if p.exists():
            return p
    return None


EMOTION_WORDS = {
    "calm": ("平静", "认真", "温柔"), "happy": ("开心", "笑", "高兴"), "sad": ("难过", "累", "叹气"),
    "shock": ("吃惊", "惊讶", "震惊"), "angry": ("生气", "崩溃", "抓狂"),
}


def library_items(media_cfg):
    """素材库：文件名就是标签，用 _ 分隔，例如 `工位_打字_认真.mp4`、`雨夜街头_挥手_开心.png`。"""
    root = resolve(media_cfg.get("library"))
    if not root or not root.is_dir():
        return []
    return [(p, [t for t in re.split(r"[_\-\s，,]+", p.stem) if t])
            for p in sorted(root.rglob("*")) if p.suffix.lower() in MEDIA_EXT]


def _pick_from_library(lines, items):
    """按台词的场景/动作/情绪给每个素材打分，选最贴合的，并避免相邻镜头重复。台词里写了 shot（素材文件名）就直接用它。"""
    picks, used = [], {}
    by_name = {path.stem: path for path, _ in items}
    for line in lines:
        if line.get("shot") in by_name:
            picks.append(by_name[line["shot"]])
            used[picks[-1]] = used.get(picks[-1], 0) + 1
            continue
        text = "".join(line.get(k, "") for k in ("scene", "action", "text"))
        emo = EMOTION_WORDS.get(line["emotion"], ())
        best, best_score = None, 2.5
        for path, tags in items:
            score = 0.0
            for t in tags:
                if t in emo or t == line["emotion"]:
                    score += 1.5
                elif t in text:
                    score += len(t)
                else:
                    score += 0.8 * sum(t[k:k + 2] in text for k in range(len(t) - 1))
            score -= 2.0 * used.get(path, 0) + (3.0 if picks and picks[-1] == path else 0.0)
            if score > best_score:
                best, best_score = path, score
        picks.append(best)
        if best:
            used[best] = used.get(best, 0) + 1
    return picks


def _data_uri(path, max_side=1536):
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


class ArkVideo:
    """火山方舟 Seedance：文字 + IP 参考图 → 视频。"""

    def __init__(self, cfg):
        self.key = os.environ["ARK_API_KEY"]
        self.base = os.environ.get("ARK_BASE_URL", cfg.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")).rstrip("/")
        self.model = os.environ.get("ARK_VIDEO_MODEL", cfg.get("model", "doubao-seedance-2-0-260128"))
        self.cfg = cfg

    def _req(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def generate(self, prompt, ref_uris, out_path):
        role = self.cfg.get("image_role", "reference_image")
        refs = ref_uris if role == "reference_image" else ref_uris[:1]
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": u}, "role": role} for u in refs]
        task = self._req("POST", "/contents/generations/tasks", {
            "model": self.model, "content": content,
            "ratio": "9:16", "duration": self.cfg.get("duration", 5),
            "resolution": self.cfg.get("resolution", "720p"),
            "generate_audio": False, "watermark": False,
        })
        deadline = time.time() + self.cfg.get("timeout_minutes", 20) * 60
        while time.time() < deadline:
            time.sleep(10)
            res = self._req("GET", f"/contents/generations/tasks/{task['id']}")
            status = res.get("status")
            if status == "succeeded":
                urllib.request.urlretrieve(res["content"]["video_url"], out_path)
                return out_path
            if status in ("failed", "expired", "cancelled"):
                raise RuntimeError(f"{status}: {res.get('error')}")
        raise TimeoutError("生成超时")


class ArkImage:
    """火山方舟 Seedream：文字 + IP 参考图 → 一张新镜头图片。"""

    def __init__(self, cfg):
        self.key = os.environ["ARK_API_KEY"]
        self.base = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        self.model = os.environ.get("ARK_IMAGE_MODEL") or cfg.get("model", "doubao-seedream-4-0-250828")
        self.size = cfg.get("size", "1440x2560")

    def generate(self, prompt, ref_uris, out_path):
        body = {"model": self.model, "prompt": prompt, "image": ref_uris, "size": self.size,
                "response_format": "b64_json", "watermark": False, "sequential_image_generation": "disabled"}
        req = urllib.request.Request(self.base + "/images/generations", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())["data"][0]
        img = Image.open(io.BytesIO(base64.b64decode(data["b64_json"]))).convert("RGB")
        img.thumbnail((1080, 1920))
        img.save(out_path, "JPEG", quality=88)
        return out_path


def _shot_name(line):
    name = (line.get("new_shot") or {}).get("name") or "_".join(
        x for x in (line.get("scene"), line.get("action"), EMOTION_WORDS.get(line["emotion"], ("",))[0]) if x)
    parts = [re.sub(r"[^\w]", "", t) for t in re.split(r"[_\-\s，,、。；;]+", name)]
    return "_".join(t[:8] for t in parts if t)[:40]


def create_new_shots(script, pet, media_cfg):
    """给剧本里设计了新场景（new_shot）或素材库匹配不到的句子补拍镜头，存进素材库，返回新镜头文件名。"""
    ncfg = media_cfg.get("new_shots") or {}
    limit = ncfg.get("max_per_video", 2)
    if not ncfg.get("enabled") or not limit:
        return []
    lines = script["lines"]
    picks = _pick_from_library(lines, library_items(media_cfg))
    wanted = [i for i, l in enumerate(lines) if l.get("new_shot")]
    wanted += [i for i, p in enumerate(picks) if p is None and i not in wanted]
    if not wanted:
        return []
    if not os.environ.get("ARK_API_KEY"):
        print(f"[新镜头] 有 {len(wanted)} 句想用新场景，但没有设置 ARK_API_KEY，改用素材库现有镜头")
        return []
    refs = [resolve(p) for p in (pet.get("reference_images") or [pet.get("image")])]
    refs = [_data_uri(p) for p in refs if p and p.exists()]
    if not refs:
        print("[新镜头] 没有找到 IP 参考图（pet.image），跳过")
        return []
    root = resolve(media_cfg.get("library", "assets/library"))
    have = {p.stem for p, _ in library_items(media_cfg)}
    gen, created = ArkImage(ncfg), []
    for i in wanted[:limit]:
        line, name = lines[i], _shot_name(lines[i])
        if not name:
            continue
        if name not in have:
            desc = (line.get("new_shot") or {}).get("prompt") or shot_prompt(line, pet, media_cfg)
            prompt = (f"参考图里的这只{pet.get('species', '宠物')}就是主角，脸型、毛色、眼睛颜色、体型必须和参考图完全一致。"
                      f"外形：{pet.get('appearance', '')}。画面：{desc}。{media_cfg.get('style') or DEFAULT_STYLE}")
            try:
                gen.generate(prompt, refs, root / f"{name}.jpg")
            except Exception as e:  # noqa: BLE001
                print(f"[新镜头] {name} 生成失败：{e}")
                continue
            have.add(name)
            created.append(name)
            print(f"[新镜头] {name}")
        line["shot"] = name
        line.pop("new_shot", None)
    return created


def prepare_shots(script, pet, cfg, out_dir):
    """返回每句台词对应的素材路径（None 表示用本地宠物动画兜底）。"""
    media_cfg = cfg.get("media", {})
    shots_dir = out_dir / "shots"
    shots_dir.mkdir(exist_ok=True)
    created = create_new_shots(script, pet, media_cfg)
    (out_dir / "new_shots.txt").write_text("\n".join(created), encoding="utf-8")
    write_shot_list(script, pet, media_cfg, out_dir / "shots.md")
    sources = [_existing(shots_dir, i) for i in range(1, len(script["lines"]) + 1)]

    items = library_items(media_cfg)
    if items:
        picks = _pick_from_library(script["lines"], items)
        hits = 0
        for i, path in enumerate(picks):
            if sources[i] is None and path is not None:
                sources[i] = path
                hits += 1
        print(f"[分镜] 素材库匹配到 {hits} 个镜头（共 {len(items)} 个素材）")

    missing = [i for i, s in enumerate(sources) if s is None]
    budget = media_cfg.get("max_generated_per_video")
    if budget is not None and len(missing) > budget:
        first = [i for i in missing if i == 0 or script["lines"][i].get("highlight")]
        missing = (first + [i for i in missing if i not in first])[:budget]
    if missing and media_cfg.get("provider") == "ark":
        if not os.environ.get("ARK_API_KEY"):
            print("[分镜] 已选择火山方舟生成，但没有设置 ARK_API_KEY，跳过自动生成")
        else:
            refs = [resolve(p) for p in (pet.get("reference_images") or [pet.get("image")])]
            refs = [_data_uri(p) for p in refs if p and p.exists()]
            if not refs:
                print("[分镜] 没有找到 IP 参考图（pet.image / pet.reference_images），跳过自动生成")
            else:
                ark = ArkVideo(media_cfg)
                print(f"[分镜] 用 {ark.model} 生成 {len(missing)} 个镜头，通常要几分钟……")

                def job(i):
                    out = shots_dir / f"shot_{i + 1:02d}.mp4"
                    try:
                        ark.generate(shot_prompt(script["lines"][i], pet, media_cfg), refs, out)
                        print(f"[分镜] 镜头 {i + 1:02d} 完成")
                        return i, out
                    except Exception as e:  # noqa: BLE001
                        print(f"[分镜] 镜头 {i + 1:02d} 生成失败：{e}")
                        return i, None

                with ThreadPoolExecutor(max_workers=media_cfg.get("concurrency", 3)) as pool:
                    for i, path in pool.map(job, missing):
                        sources[i] = path

    ready = sum(s is not None for s in sources)
    print(f"[分镜] {ready}/{len(sources)} 个镜头有素材；分镜表和提示词见 {out_dir / 'shots.md'}")
    return sources


LIBRARY_PLAN = [
    ("卧室_闹钟_起床_难过", "清晨的出租屋卧室", "缩在被子里伸爪按掉闹钟，不情愿地探出头"),
    ("卧室_床边_发呆_累", "卧室床边", "坐在床边发呆，毛有点乱，眼睛半睁"),
    ("地铁_通勤_拥挤_生气", "早高峰地铁车厢，周围是人腿和背包", "被人群夹在中间，脸贴着扶手杆"),
    ("街头_上班路上_走路_平静", "清晨写字楼前的人行道", "背着小挎包往前走，偶尔抬头看楼"),
    ("电梯_按按钮_平静", "写字楼电梯里", "踮脚按电梯按钮，抬头看楼层数字"),
    ("工位_打字_认真", "开放式办公室工位", "坐在椅子上用两只爪子认真敲键盘"),
    ("工位_看屏幕_吃惊", "工位", "盯着电脑屏幕，眼睛突然睁大，耳朵竖起"),
    ("工位_趴桌_累_难过", "工位", "趴在桌上叹气，耳朵耷拉"),
    ("工位_捂脸_崩溃_生气", "工位", "两只爪子捂住脸，从指缝里偷看屏幕"),
    ("工位_看手机_开心_工资", "工位", "捧着手机看，尾巴摇起来，眼睛弯成月牙"),
    ("工位_喝咖啡_平静", "工位", "双爪捧着咖啡杯小口喝，看向窗外"),
    ("会议室_开会_发呆_累", "会议室，人类同事只露出身体", "坐在会议桌边，眼神放空"),
    ("会议室_举手_认真", "会议室", "认真地举起一只爪子发言"),
    ("茶水间_摸鱼_开心", "公司茶水间", "躲在冰箱旁边偷偷吃零食"),
    ("工位_同事_拍肩_温柔", "工位，同事只露出手", "被同事的手轻轻拍了拍头，抬头看"),
    ("窗边_夕阳_看窗外_温柔", "傍晚的办公室窗边", "站在窗边看夕阳，表情慢慢变温柔"),
    ("工位_收拾包_下班_开心", "傍晚的工位", "从椅子上跳下来，把小挎包背好"),
    ("夜晚街头_下班_走路_平静", "夜晚的街头，霓虹灯和车流", "背着小挎包走在人行道上"),
    ("雨夜街头_挥手_开心", "下雨的夜晚街头", "站在路边回头对镜头挥爪"),
    ("奶茶店_买奶茶_开心", "街边奶茶店柜台", "踮脚递手机扫码，接过奶茶"),
    ("长椅_喝奶茶_温柔", "傍晚的街边长椅", "坐在长椅上抱着奶茶小口吸"),
    ("厨房_做饭_认真", "出租屋小厨房", "站在小板凳上搅拌锅里的面"),
    ("沙发_躺平_放松_开心", "出租屋沙发", "四脚朝天躺在沙发上，抱着抱枕"),
    ("镜头前_歪头_眨眼_开心", "温暖的室内背景虚化", "对着镜头歪头眨眼，挥挥爪子"),
]


def write_library_plan(pet, media_cfg, path):
    rows = ["# 通用镜头素材库清单", "",
            "这些是职场日常最常用的镜头。每个只需生成一次（用即梦/可灵的免费额度，或付费生成一次），",
            f"下载后按「建议文件名」放进 `{media_cfg.get('library', 'assets/library')}/`，之后每天的视频会按标签自动复用。", "",
            "| # | 建议文件名 | 提示词（上传 IP 参考图后粘贴） |", "|---|---|---|"]
    for i, (name, scene, action) in enumerate(LIBRARY_PLAN, 1):
        prompt = shot_prompt({"scene": scene, "action": action, "camera": "中景，轻微推近", "emotion": "calm",
                              "text": action}, pet, media_cfg).split("情绪：")[0]
        prompt += media_cfg.get("style") or DEFAULT_STYLE
        rows.append(f"| {i} | `{name}.mp4` | {prompt} |")
    Path(path).write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_library(pet, media_cfg):
    root = resolve(media_cfg.get("library", "assets/library"))
    root.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("ARK_API_KEY"):
        print("没有设置 ARK_API_KEY：请按清单手动生成素材后放进", root)
        return
    refs = [resolve(p) for p in (pet.get("reference_images") or [pet.get("image")])]
    refs = [_data_uri(p) for p in refs if p and p.exists()]
    if not refs:
        print("没有找到 IP 参考图（pet.image / pet.reference_images）")
        return
    have = {p.stem for p, _ in library_items(media_cfg)}
    todo = [item for item in LIBRARY_PLAN if item[0] not in have]
    ark = ArkVideo(media_cfg)
    print(f"[素材库] 需要生成 {len(todo)} 个镜头（已有 {len(have)} 个）")

    def job(item):
        name, scene, action = item
        prompt = shot_prompt({"scene": scene, "action": action, "camera": "中景，轻微推近",
                              "emotion": "calm", "text": action}, pet, media_cfg).split("情绪：")[0]
        try:
            ark.generate(prompt + (media_cfg.get("style") or DEFAULT_STYLE), refs, root / f"{name}.mp4")
            print(f"[素材库] {name} 完成")
        except Exception as e:  # noqa: BLE001
            print(f"[素材库] {name} 失败：{e}")

    with ThreadPoolExecutor(max_workers=media_cfg.get("concurrency", 3)) as pool:
        list(pool.map(job, todo))

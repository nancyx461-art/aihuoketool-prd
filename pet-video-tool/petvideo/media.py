"""剧情模式的分镜素材：优先用你放进 shots/ 的素材，其次调用火山方舟 Seedance 用 IP 参考图生成视频。"""

import base64
import io
import json
import os
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


def prepare_shots(script, pet, cfg, out_dir):
    """返回每句台词对应的素材路径（None 表示用本地宠物动画兜底）。"""
    media_cfg = cfg.get("media", {})
    shots_dir = out_dir / "shots"
    shots_dir.mkdir(exist_ok=True)
    write_shot_list(script, pet, media_cfg, out_dir / "shots.md")
    sources = [_existing(shots_dir, i) for i in range(1, len(script["lines"]) + 1)]

    missing = [i for i, s in enumerate(sources) if s is None]
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

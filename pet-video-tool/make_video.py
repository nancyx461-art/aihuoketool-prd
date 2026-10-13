"""宠物 IP 职场口播视频：一键 写脚本 → 配音 → 宠物动起来 → 字幕 → 成片 + 剪映草稿。

用法：
  python make_video.py                    # 生成今天的视频
  python make_video.py --topic 开不完的会   # 指定主题
  python make_video.py --days 7           # 一次生成未来 7 天的视频
  python make_video.py --script-only      # 只出脚本，不剪辑
  python make_video.py --from-script output/xxx/script.json   # 用你改过的脚本重新剪
  python make_video.py --mark             # 输出带网格的 IP 图，帮你量嘴巴/眼睛坐标
  python make_video.py --mode talking     # 临时切换口播模式（默认读 config.yaml 的 mode）
  python make_video.py --library-plan     # 输出通用镜头素材库清单（做一次，每天复用）
"""

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from petvideo import demo_pet
from petvideo.animate import ImageAnimator, LineTimeline, ShotAnimator
from petvideo.media import build_library, prepare_shots, write_library_plan, write_shot_list
from petvideo.config import ROOT, load_config, resolve
from petvideo.render import Overlay, render
from petvideo.scripts import generate_script, record_history, script_to_markdown
from petvideo.subtitles import build_cues, find_font, write_srt
from petvideo.tts import envelope, synthesize


def pet_image(cfg):
    """返回 (图片路径, 嘴巴, 眼睛)。没有图片时生成示例橘猫。"""
    path = resolve(cfg["pet"].get("image"))
    if path and path.exists():
        return path, None, None
    demo = ROOT / "assets" / "demo_pet.png"
    demo.parent.mkdir(exist_ok=True)
    mouth, eyes = demo_pet.draw(demo)
    print(f"[形象] 没找到 {path}，先用示例橘猫跑流程。把你的 IP 图放到 {path} 即可替换。")
    return demo, mouth, eyes


def mark_grid(cfg):
    path, _, _ = pet_image(cfg)
    img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(img)
    for i in range(1, 20):
        for (x0, y0, x1, y1) in [(img.width * i / 20, 0, img.width * i / 20, img.height),
                                 (0, img.height * i / 20, img.width, img.height * i / 20)]:
            d.line([(x0, y0), (x1, y1)], fill=(255, 0, 0) if i % 5 == 0 else (255, 160, 160), width=2 if i % 5 else 4)
        d.text((img.width * i / 20 + 3, 3), f"{i / 20:.2f}", fill=(255, 0, 0))
        d.text((3, img.height * i / 20 + 3), f"{i / 20:.2f}", fill=(255, 0, 0))
    out = ROOT / "output" / "pet_grid.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(f"已生成 {out}：横线/竖线上的数字就是相对坐标，用来填写 config.yaml 里的 mouth / eyes。")


def build_animator(cfg, script, out, W, H, fps):
    pet, vcfg = cfg["pet"], cfg["video"]

    def local():
        image, mouth, eyes = pet_image(cfg)
        return ImageAnimator(image, {**pet, "_background": vcfg.get("background", "blur")}, W, H, fps, mouth, eyes)

    if cfg.get("mode") == "story":
        sources = prepare_shots(script, pet, cfg, out)
        return ShotAnimator(sources, W, H, fps, local() if None in sources else None)

    clips = {k: resolve(v) for k, v in (pet.get("motion_clips") or {}).items() if v and resolve(v).exists()}
    if not clips:
        return local()
    print(f"[动作] 使用动作片段：{', '.join(clips)}")
    default = clips.get("calm") or next(iter(clips.values()))
    return ShotAnimator([clips.get(line["emotion"], default) for line in script["lines"]], W, H, fps)


def make_one(cfg, date, topic=None, script_path=None, script_only=False):
    pet, vcfg = cfg["pet"], cfg["video"]
    if script_path:
        script, source = json.loads(Path(script_path).read_text(encoding="utf-8")), "file"
    else:
        script, source = generate_script(cfg, topic, date)
    slug = re.sub(r"[\\/:*?\"<>|\s]+", "", script["title"])[:16]
    if script_path and Path(script_path).name == "script.json":
        out = Path(script_path).resolve().parent
    else:
        out = resolve(cfg.get("output_dir", "output")) / f"{date.isoformat()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "script.md").write_text(script_to_markdown(script, pet), encoding="utf-8")
    print(f"\n[脚本] 《{script['title']}》（来源：{source}）→ {out / 'script.md'}")
    for line in script["lines"]:
        print(f"   [{line['emotion']:>5}] {line['text']}")
    if not script_path:
        record_history(script)
    if script_only:
        if cfg.get("mode") == "story":
            write_shot_list(script, pet, cfg.get("media", {}), out / "shots.md")
            print(f"[分镜] 分镜表和提示词：{out / 'shots.md'}")
        return out

    W, H, fps = vcfg["width"], vcfg["height"], vcfg["fps"]
    wav = out / "voice.wav"
    spans, duration, engine = synthesize(script["lines"], cfg["tts"], wav)
    print(f"[配音] {engine}，时长 {duration:.1f}s")

    cues = build_cues(script["lines"], spans)
    srt = out / "subtitles.srt"
    write_srt(cues, srt)

    n_frames = math.ceil(duration * fps)
    env = envelope(wav, fps)
    timeline = LineTimeline(script["lines"], spans)
    animator = build_animator(cfg, script, out, W, H, fps)

    hi = next((i for i, l in enumerate(script["lines"]) if l.get("highlight")), 0)
    cover_t = (spans[hi][0] + spans[hi][1]) / 2
    overlay = Overlay(find_font(vcfg.get("subtitle_font")), W, H, script["title"], cues, script["lines"],
                      vcfg.get("show_title", True))
    bgm = resolve(vcfg.get("bgm"))
    final, clean = out / "final.mp4", out / "clean_no_subtitles.mp4"
    render(animator.frames(timeline, env, n_frames), overlay, n_frames, fps, W, H, wav, final, clean,
           bgm if bgm and bgm.exists() else None, vcfg.get("bgm_volume", 0.12),
           cover_path=out / "cover.jpg", cover_frame=int(cover_t * fps))
    print(f"[成片] {final}")

    if cfg.get("jianying", {}).get("enabled", True):
        try:
            from petvideo.jianying import make_draft
            path, in_app = make_draft(f"{date.isoformat()}_{slug}", out, clean, wav, srt, script["title"],
                                      duration, W, H, fps, cfg)
            print(f"[剪映] 草稿已生成：{path}" + ("（打开剪映首页即可看到）" if in_app else
                  "\n       没找到本机剪映草稿目录；把这个文件夹复制到剪映草稿目录即可，或在 config.yaml 填 jianying.draft_folder"))
        except Exception as e:  # noqa: BLE001
            print(f"[剪映] 草稿生成失败（不影响成片）：{e}")
    return out


def main():
    ap = argparse.ArgumentParser(description="宠物 IP 职场口播视频自动生成")
    ap.add_argument("--config")
    ap.add_argument("--topic", help="指定今天的主题")
    ap.add_argument("--days", type=int, default=1, help="从今天开始连续生成几天")
    ap.add_argument("--date", help="指定日期 YYYY-MM-DD")
    ap.add_argument("--mode", choices=["story", "talking"], help="story=剧情分镜（对标小斗下班啦），talking=口播")
    ap.add_argument("--script-only", action="store_true")
    ap.add_argument("--from-script", help="用已有/手改过的 script.json 剪辑")
    ap.add_argument("--mark", action="store_true", help="输出带坐标网格的 IP 图")
    ap.add_argument("--library-plan", action="store_true", help="输出通用镜头素材库清单和提示词")
    ap.add_argument("--build-library", action="store_true", help="用火山方舟一次性生成素材库里缺的镜头")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.mode:
        cfg["mode"] = args.mode
    if args.mark:
        return mark_grid(cfg)
    if args.library_plan or args.build_library:
        out = ROOT / "output" / "library_plan.md"
        out.parent.mkdir(exist_ok=True)
        write_library_plan(cfg["pet"], cfg.get("media", {}), out)
        print(f"素材库清单：{out}")
        if args.build_library:
            build_library(cfg["pet"], cfg.get("media", {}))
        return
    if not cfg["llm"].get("api_key") and not args.from_script:
        print("[提示] 没有设置 LLM_API_KEY，使用内置职场脚本库。设置后每天都会由大模型写新脚本。")

    start = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    for i in range(args.days):
        make_one(cfg, start + dt.timedelta(days=i), args.topic, args.from_script, args.script_only)


if __name__ == "__main__":
    sys.exit(main())

"""生成剪映草稿：打开剪映即可看到，包含 视频轨 + 配音轨 + 字幕轨 + 标题，可继续手动精修后导出。"""

import os
from pathlib import Path

from .config import resolve

DRAFT_SUBDIR = "User Data/Projects/com.lveditor.draft"
DEFAULT_DIRS = [
    Path.home() / "AppData/Local/JianyingPro" / DRAFT_SUBDIR,
    Path.home() / "Movies/JianyingPro" / DRAFT_SUBDIR,
    Path.home() / "Movies/CapCut" / DRAFT_SUBDIR,
]
if os.environ.get("LOCALAPPDATA"):
    DEFAULT_DIRS.insert(0, Path(os.environ["LOCALAPPDATA"]) / "JianyingPro" / DRAFT_SUBDIR)


def find_draft_folder(custom):
    if custom:
        return resolve(custom)
    return next((d for d in DEFAULT_DIRS if d.is_dir()), None)


def make_draft(name, out_dir, clean_video, voice_wav, srt, title, duration, W, H, fps, cfg):
    import pyJianYingDraft as draft
    from pyJianYingDraft import ClipSettings, TextStyle, TrackSpec, TrackType, trange

    root = find_draft_folder(cfg.get("jianying", {}).get("draft_folder"))
    in_app = root is not None
    if not in_app:
        root = out_dir / "jianying_drafts"
        root.mkdir(exist_ok=True)

    script = draft.DraftFolder(str(root)).create_draft(name, W, H, fps, allow_replace=True)
    script.append_tracks([
        TrackSpec(TrackType.video, "宠物"),
        TrackSpec(TrackType.audio, "配音"),
        TrackSpec(TrackType.text, "标题"),
    ])
    video = draft.VideoMaterial(str(clean_video.resolve()))
    voice = draft.AudioMaterial(str(voice_wav.resolve()))
    total = min(video.duration, voice.duration)
    script.add_segment(draft.VideoSegment(video, trange(0, total), volume=0.0), "宠物")
    script.add_segment(draft.AudioSegment(voice, trange(0, total)), "配音")

    bgm = resolve(cfg["video"].get("bgm"))
    if bgm and bgm.exists():
        script.append_track(TrackSpec(TrackType.audio, "背景音乐"))
        music = draft.AudioMaterial(str(bgm.resolve()))
        start = 0
        while start < total:
            length = min(music.duration, total - start)
            script.add_segment(draft.AudioSegment(music, trange(start, length),
                                                  volume=cfg["video"].get("bgm_volume", 0.25)), "背景音乐")
            start += length

    script.add_segment(draft.TextSegment(title, trange(0, total),
                                         style=TextStyle(size=9, bold=True, align=1, color=(1.0, 0.85, 0.3)),
                                         clip_settings=ClipSettings(transform_y=0.82)), "标题")
    script.import_srt(str(srt), "字幕", text_style=TextStyle(size=8, bold=True, align=1, auto_wrapping=True),
                      clip_settings=ClipSettings(transform_y=-0.56))
    script.save()
    return root / name, in_app

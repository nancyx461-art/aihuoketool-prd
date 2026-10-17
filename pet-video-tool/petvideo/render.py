import subprocess
import time

from PIL import Image, ImageDraw

from .subtitles import load_font


def _text_image(text, font, fill, stroke=(30, 20, 20), stroke_w=8, bg=None, pad=(36, 18)):
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = probe.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    w, h = r - l + pad[0] * 2, b - t + pad[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bg:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=bg)
    d.text((pad[0] - l, pad[1] - t), text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke)
    return img


class Overlay:
    def __init__(self, font_path, W, H, title, cues, lines, show_title=True):
        self.W, self.H = W, H
        self.cues, self.lines = cues, lines
        sub_font = load_font(font_path, int(W * 0.068))
        hi_font = load_font(font_path, int(W * 0.078))
        self.cue_imgs = []
        for _, _, text, idx in cues:
            if lines[idx].get("highlight"):
                self.cue_imgs.append(_text_image(text, hi_font, (255, 222, 60), stroke_w=10))
            else:
                self.cue_imgs.append(_text_image(text, sub_font, (255, 255, 255)))
        self.title = None
        if show_title and title:
            self.title = _text_image(title, load_font(font_path, int(W * 0.062)), (60, 35, 20),
                                     stroke=(255, 255, 255), stroke_w=0, bg=(255, 214, 90, 235), pad=(48, 26))

    def apply(self, frame, t):
        frame = frame.convert("RGBA") if frame.mode != "RGBA" else frame
        if self.title:
            frame.alpha_composite(self.title, ((self.W - self.title.width) // 2, int(self.H * 0.075)))
        for (s, e, _, _), img in zip(self.cues, self.cue_imgs):
            if s <= t < e:
                k = min(1.0, (t - s) / 0.12)
                scale = 0.82 + 0.18 * k
                if scale < 0.999:
                    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
                frame.alpha_composite(img, ((self.W - img.width) // 2, int(self.H * 0.78 - img.height / 2)))
                break
        return frame.convert("RGB")


def _encoder(path, W, H, fps, wav, bgm=None, bgm_volume=0.12):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-i", str(wav)]
    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm), "-filter_complex",
                f"[2:a]volume={bgm_volume}[b];[1:a][b]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render(frames, overlay, n_frames, fps, W, H, wav, final_path, clean_path, bgm=None, bgm_volume=0.12,
           cover_path=None, cover_frame=0):
    """同时输出带字幕的成片和不带字幕的素材（给剪映草稿用），并截一帧做封面。"""
    final = _encoder(final_path, W, H, fps, wav, bgm, bgm_volume)
    clean = _encoder(clean_path, W, H, fps, wav)
    start = time.time()
    for i, frame in enumerate(frames):
        if i >= n_frames:
            break
        composed = overlay.apply(frame, i / fps)
        clean.stdin.write(frame.convert("RGB").tobytes())
        final.stdin.write(composed.tobytes())
        if cover_path and i == cover_frame:
            composed.save(cover_path, quality=92)
        if i % (fps * 5) == 0:
            print(f"\r[剪辑] 渲染 {i}/{n_frames} 帧，用时 {time.time() - start:.0f}s", end="", flush=True)
    for p in (final, clean):
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("ffmpeg 编码失败")
    print(f"\r[剪辑] 渲染完成 {n_frames} 帧，用时 {time.time() - start:.0f}s        ")

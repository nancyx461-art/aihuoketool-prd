"""让宠物 IP 动起来：本地动画（呼吸/说话弹跳/张嘴/眨眼/情绪动作）或复用 AI 生成的动作片段。"""

import math
import random
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

EMOTION_STYLE = {
    #          弹跳  摇摆(度) 下沉(px) 抖动(px) 体型
    "calm":  (0.35, 1.2, 0, 0, 1.00),
    "happy": (1.00, 2.5, -10, 0, 1.03),
    "sad":   (0.15, 0.6, 28, 0, 0.96),
    "shock": (0.50, 0.8, -20, 8, 1.06),
    "angry": (0.60, 0.5, 0, 5, 1.05),
}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _background(src, W, H, mode):
    if mode and mode != "blur":
        return Image.new("RGB", (W, H), _hex(mode))
    img = Image.alpha_composite(Image.new("RGBA", src.size, (250, 236, 214, 255)), src).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1))
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = img.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(6)).resize((W, H))
    return Image.blend(img, Image.new("RGB", (W, H), (250, 240, 228)), 0.35)


class LineTimeline:
    def __init__(self, lines, spans):
        self.lines, self.spans = lines, spans

    def at(self, t):
        """返回 (当前台词序号, 是否正在说, 本句已开始多久)。"""
        cur = 0
        for i, (s, e) in enumerate(self.spans):
            if t >= s:
                cur = i
        s, e = self.spans[cur]
        return cur, s <= t <= e, max(0.0, t - s)


class ImageAnimator:
    def __init__(self, image_path, pet_cfg, W, H, fps, mouth=None, eyes=None):
        src = Image.open(image_path).convert("RGBA")
        self.W, self.H, self.fps = W, H, fps
        alpha = np.asarray(src)[..., 3]
        self.cutout = alpha.min() < 250
        self.bg = _background(src, W, H, pet_cfg.get("_background", "blur"))

        if self.cutout:
            s = min(W * 0.86 / src.width, H * 0.56 / src.height)
            self.anchor = (W / 2, H * 0.70)
        else:
            s = W / src.width
            self.anchor = (W / 2, H * 0.47 + src.height * s / 2)
        self.pet = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
        pw, ph = self.pet.size

        def box(b):
            return (b[0] * pw, b[1] * ph, b[2] * pw, b[3] * ph)

        mouth = mouth if mouth is not None else pet_cfg.get("mouth")
        eyes = eyes if eyes is not None else pet_cfg.get("eyes")
        self.mouth = box(mouth) if mouth else None
        self.eyes = [box(e) for e in (eyes or [])]
        self.mouth_color = _hex(pet_cfg.get("mouth_color", "#3a1f1f"))
        self.lid_colors = [self._sample_lid(e) for e in self.eyes]
        self.rng = random.Random(7)
        self.next_blink = 1.2
        self.state = np.array([0.0, 0.0, 0.0, 0.0, 1.0])

    def _sample_lid(self, e):
        cx, cy, w, h = e
        strip = np.asarray(self.pet.crop((int(cx - w / 2), int(cy - h * 1.3), int(cx + w / 2), int(cy - h * 0.7))))
        strip = strip.reshape(-1, 4)
        strip = strip[strip[:, 3] > 200] if (strip[:, 3] > 200).any() else strip
        return tuple(int(v) for v in np.median(strip[:, :3], axis=0))

    def _face(self, open_amt, blink):
        if not self.mouth and not self.eyes:
            return self.pet
        pet = self.pet.copy()
        if self.mouth and open_amt > 0.08:
            cx, cy, w, h = self.mouth
            oh = h * 1.6 * open_amt
            ow = w * (0.18 + 0.22 * open_amt)
            drop = int(oh * 0.6)
            jaw_box = (int(cx - w * 0.8), int(cy - h * 0.1), int(cx + w * 0.8), int(cy + h * 1.4))
            jaw = pet.crop(jaw_box)
            mask = Image.new("L", jaw.size, 0)
            ImageDraw.Draw(mask).ellipse([jaw.width * 0.04, -jaw.height * 0.5, jaw.width * 0.96, jaw.height * 0.85], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(max(2, w * 0.06)))
            skin = tuple(int(v) for v in np.median(np.asarray(jaw.convert("RGB")).reshape(-1, 3), axis=0))
            pet.paste(Image.new("RGBA", jaw.size, skin + (255,)), jaw_box[:2], mask)
            pet.paste(jaw, (jaw_box[0], jaw_box[1] + drop), mask)
            d = ImageDraw.Draw(pet)
            bottom = cy + drop + h * 0.3
            d.ellipse([cx - ow, cy - h * 0.05, cx + ow, bottom], fill=self.mouth_color + (255,))
            d.chord([cx - ow * 0.6, bottom - (bottom - cy) * 0.45, cx + ow * 0.6, bottom + (bottom - cy) * 0.2],
                    180, 360, fill=(225, 110, 120, 255))
        if blink > 0.05:
            for (cx, cy, w, h), color in zip(self.eyes, self.lid_colors):
                box = [int(cx - w * 0.62), int(cy - h * 0.62), int(cx + w * 0.62), int(cy + h * 0.62)]
                bw, bh = box[2] - box[0], box[3] - box[1]
                lid = int(bh * min(1.0, blink * 1.15))
                mask = Image.new("L", (bw, bh), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, bw - 1, bh - 1], fill=255)
                ImageDraw.Draw(mask).rectangle([0, lid, bw, bh], fill=0)
                pet.paste(Image.new("RGBA", (bw, bh), color + (255,)), box[:2], mask)
                if blink > 0.6:
                    ImageDraw.Draw(pet).arc([cx - w * 0.5, cy - h * 0.45, cx + w * 0.5, cy + h * 0.25], 15, 165,
                                            fill=(50, 35, 30, 255), width=max(3, int(h * 0.1)))
        return pet

    def _blink(self, t):
        if t > self.next_blink + 0.2:
            self.next_blink = t + self.rng.uniform(2.2, 4.8)
        p = (t - self.next_blink) / 0.2
        return math.sin(p * math.pi) if 0 <= p <= 1 else 0.0

    def frames(self, timeline, env, n_frames):
        W, H, fps = self.W, self.H, self.fps
        for f in range(n_frames):
            t = f / fps
            idx, speaking, since = timeline.at(t)
            line = timeline.lines[idx]
            bounce, sway, sink, shake, size = EMOTION_STYLE[line["emotion"]]
            e = float(env[min(f, len(env) - 1)]) if speaking else 0.0

            target = np.array([bounce, sway, sink, shake, size])
            self.state += (target - self.state) * 0.12
            bounce, sway, sink, shake, size = self.state

            pop = 0.0
            if line["emotion"] == "shock" and since < 0.45:
                pop = math.sin(since / 0.45 * math.pi)
            push = 0.04 * min(1.0, since / 2.5) if line.get("highlight") else 0.0

            breath = math.sin(2 * math.pi * t / 3.2)
            sy = size * (1 + 0.012 * breath + 0.045 * e * bounce + 0.06 * pop) + push
            sx = size * (1 - 0.006 * breath - 0.02 * e * bounce + 0.03 * pop) + push
            rot = sway * math.sin(2 * math.pi * t / 3.6) + (2.5 * e * math.sin(2 * math.pi * t * 1.3) if line["emotion"] == "happy" else 0)
            dy = sink - 26 * e * bounce - 45 * pop
            dx = 0.0
            if shake:
                decay = 1.0 if line["emotion"] == "angry" else max(0.0, 1 - since / 0.6)
                dx = shake * decay * math.sin(t * 90)
                dy += shake * 0.5 * decay * math.sin(t * 70)
            if not self.cutout:
                rot *= 0.25
                sx = sy = 1 + (sx + sy - 2) * 0.5

            pet = self._face(e, self._blink(t))
            yield self._place(pet, sx, sy, rot, dx, dy)

    def _place(self, pet, sx, sy, rot, dx, dy):
        """以宠物底部中心为锚点做缩放（挤压拉伸）+ 旋转 + 位移。"""
        frame = self.bg.copy()
        pw, ph = pet.size
        ax, ay = self.anchor[0] + dx, self.anchor[1] + dy
        r = math.radians(rot)
        cos, sin = math.cos(r), math.sin(r)
        a, b, d, e = cos / sx, sin / sx, -sin / sy, cos / sy
        c = pw / 2 - (a * ax + b * ay)
        f = ph - (d * ax + e * ay)
        layer = pet.transform((self.W, self.H), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BILINEAR)
        frame.paste(layer, (0, 0), layer)
        return frame


class ClipAnimator:
    """复用提前用即梦/可灵等生成的动作视频片段，按每句台词的情绪切换。"""

    def __init__(self, clips, W, H, fps):
        self.clips, self.W, self.H, self.fps = clips, W, H, fps

    def _stream(self, path, seconds):
        W, H = self.W, self.H
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={self.fps}"
        proc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", str(path), "-t", f"{seconds:.3f}",
             "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        size = W * H * 3
        try:
            while True:
                buf = proc.stdout.read(size)
                if len(buf) < size:
                    break
                yield Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)
        finally:
            proc.kill()
            proc.wait()

    def frames(self, timeline, env, n_frames):
        bounds = [s for s, _ in timeline.spans] + [n_frames / self.fps]
        bounds[0] = 0.0
        produced = 0
        for i, line in enumerate(timeline.lines):
            end_frame = n_frames if i == len(timeline.lines) - 1 else round(bounds[i + 1] * self.fps)
            count = end_frame - produced
            if count <= 0:
                continue
            clip = self.clips.get(line["emotion"]) or self.clips.get("calm") or next(iter(self.clips.values()))
            last = None
            for frame in self._stream(clip, count / self.fps + 0.2):
                if count <= 0:
                    break
                last = frame
                produced += 1
                count -= 1
                yield frame
            while count > 0 and last is not None:
                produced += 1
                count -= 1
                yield last

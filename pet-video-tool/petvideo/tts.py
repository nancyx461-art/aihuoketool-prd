import asyncio
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 24000


def _decode(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def _trim_silence(x, thresh=0.01):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(0.03 * SR)
    return x[max(0, idx[0] - pad): idx[-1] + pad]


async def _edge(text, out, voice, rate, pitch):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(out))


def _gtts(text, out, speed, pitch):
    from gtts import gTTS
    raw = Path(out).with_suffix(".raw.mp3")
    gTTS(text, lang="zh-CN").save(str(raw))
    af = f"asetrate={SR}*{pitch},aresample={SR},atempo={speed / pitch:.4f}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ar", str(SR), "-af", af, str(out)],
                   check=True, capture_output=True)


def _espeak(text, out, rate, pitch):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("没有可用的离线配音引擎，请安装 espeak-ng 或使用 edge 配音")
    speed = int(175 * (1 + int(rate.strip("%+") or 0) / 100))
    subprocess.run([exe, "-v", "cmn", "-s", str(speed), "-p", "70", "-w", str(out), text],
                   check=True, capture_output=True)


def synthesize(lines, tts_cfg, out_wav):
    """逐句配音并拼接，返回每句的 (开始秒, 结束秒)。"""
    engine = tts_cfg.get("engine", "edge")
    voice = tts_cfg.get("voice", "zh-CN-XiaoyiNeural")
    rate, pitch = tts_cfg.get("rate", "+0%"), tts_cfg.get("pitch", "+0Hz")
    gap = np.zeros(int(tts_cfg.get("gap", 0.22) * SR), dtype=np.float32)

    chunks, spans, t = [np.zeros(int(0.3 * SR), dtype=np.float32)], [], 0.3
    with tempfile.TemporaryDirectory() as tmp:
        for i, line in enumerate(lines):
            path = Path(tmp) / f"{i}.mp3"
            if engine == "edge":
                try:
                    asyncio.run(_edge(line["text"], path, voice, rate, pitch))
                except Exception as e:  # noqa: BLE001
                    print(f"[配音] edge-tts 不可用（{e.__class__.__name__}），改用谷歌语音 gTTS")
                    engine = "gtts"
            if engine == "gtts":
                path = path.with_suffix(".wav")
                try:
                    _gtts(line["text"], path, tts_cfg.get("gtts_speed", 1.25), tts_cfg.get("gtts_pitch", 1.1))
                except Exception as e:  # noqa: BLE001
                    print(f"[配音] gTTS 不可用（{e.__class__.__name__}），改用离线 espeak-ng")
                    engine = "espeak"
            if engine == "espeak":
                path = path.with_suffix(".wav")
                _espeak(line["text"], path, rate, pitch)
            audio = _trim_silence(_decode(path))
            spans.append((t, t + len(audio) / SR))
            chunks += [audio, gap]
            t += (len(audio) + len(gap)) / SR
    chunks.append(np.zeros(int(0.5 * SR), dtype=np.float32))

    audio = np.concatenate(chunks)
    peak = np.max(np.abs(audio)) or 1.0
    pcm = (audio / peak * 0.9 * 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return spans, len(audio) / SR, engine


def envelope(wav_path, fps):
    """每帧的音量包络（0~1），用来驱动嘴巴和身体动作。"""
    x = _decode(wav_path)
    hop = SR // fps
    n = len(x) // hop + 1
    x = np.pad(x, (0, n * hop - len(x)))
    rms = np.sqrt((x.reshape(n, hop) ** 2).mean(axis=1))
    rms /= np.percentile(rms, 95) or 1.0
    env, out = 0.0, np.zeros(n, dtype=np.float32)
    for i, v in enumerate(np.clip(rms, 0, 1.2)):
        env += (v - env) * (0.6 if v > env else 0.25)
        out[i] = env
    return np.clip(out, 0, 1)

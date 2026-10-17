"""程序合成的轻快小调（拨弦和弦 + 钟琴旋律），无版权问题，作为默认背景音乐。"""

import wave

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM

CHORDS = [  # C - G - Am - F
    [60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60],
]
MELODY = [  # (半音, 拍数)，每小节 4 拍
    (72, 1), (76, 1), (79, 1.5), (76, 0.5),
    (74, 1), (71, 1), (74, 2),
    (72, 1), (76, 1), (81, 1.5), (79, 0.5),
    (77, 1), (76, 0.5), (74, 0.5), (72, 2),
]


def _freq(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _pluck(freq, dur, rng):
    n, period = int(SR * dur), max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.497 * (buf[i % period] + buf[(i + 1) % period])
    return out


def _bell(freq, dur):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 4.5)
    return env * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 8))


def make_bgm(path, bars=8):
    rng = np.random.default_rng(3)
    total = int(SR * BEAT * 4 * bars)
    mix = np.zeros(total + SR * 2)
    for bar in range(bars):
        chord = CHORDS[bar % 4]
        for beat in range(4):
            start = int(SR * BEAT * (bar * 4 + beat))
            notes = chord if beat % 2 == 0 else chord[1:]
            for k, note in enumerate(notes):
                s = start + int(SR * 0.012 * k)
                tone = _pluck(_freq(note), BEAT * 1.6, rng) * (0.5 if beat % 2 else 0.7)
                mix[s:s + len(tone)] += tone * 0.35
        root = _pluck(_freq(chord[0] - 12), BEAT * 4, rng)
        s = int(SR * BEAT * bar * 4)
        mix[s:s + len(root)] += root * 0.4
    t = 0.0
    for _ in range(bars // 4):
        for note, beats in MELODY:
            s = int(SR * BEAT * t)
            tone = _bell(_freq(note), BEAT * beats + 0.6)
            mix[s:s + len(tone)] += tone * 0.22
            t += beats
    mix = mix[:total]
    fade = int(SR * 0.05)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / np.max(np.abs(mix)) * 0.8
    pcm = (np.repeat(mix[:, None], 2, axis=1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path

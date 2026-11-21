#!/usr/bin/env python3
"""audio.py: synthesize a beat-synced music bed + SFX for a motion graphics edit.

usage: python3 -I audio.py spec.json out.wav

spec (all optional except duration):
{
  "duration": 10, "bpm": 120, "start": 0.0,   # start = seconds before beat 1 (music offset)
  "master": 0.85, "swing": 0,
  "kick":  "x...x...x...x...",                # 16th-note steps per bar, looped
  "clap":  "....x.......x...",
  "hat":   "..x...x...x...x.",
  "bass":  "x..x..x.x..x..x.", "bassNotes": ["A1","A1","F1","G1"],   # one note per bar
  "pad":   [["A3","C4","E4"],["F3","A3","C4"]],                      # one chord per bar
  "musicFrom": 0, "musicTo": null,           # mute the music bed outside this window
  "events": [ {"t": 1.0, "type": "whoosh", "dur": 0.35},
              {"t": 2.0, "type": "impact"}, {"t": 0.0, "type": "riser", "dur": 2.0},
              {"t": 3.0, "type": "click"}, {"t": 3.1, "type": "pop"},
              {"t": 4.0, "type": "shimmer"}, {"t": 5.0, "type": "sub"}, {"t": 6, "type": "glitch"} ]
}
"""
import json
import sys
import wave

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def env(n, a=0.002, d=0.2, curve=6.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    return att * np.exp(-curve * np.maximum(t - a, 0) / max(d, 1e-4))


def lowpass(x, cutoff):
    # one-pole, cutoff may be array
    a = np.exp(-2 * np.pi * np.asarray(cutoff) / SR) * np.ones_like(x)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def bandnoise(n, lo_hz, hi_hz):
    w = RNG.standard_normal(n)
    f = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    f[(freqs < lo_hz) | (freqs > hi_hz)] = 0
    return np.fft.irfft(f, n) / 3


def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 120 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.6 * np.sin(ph) * env(n, 0.001, 0.32, 5)) * 0.9 + bandnoise(n, 2000, 8000) * env(n, 0.0005, 0.01, 8) * 0.5


def clap():
    n = int(0.3 * SR); x = bandnoise(n, 900, 6000) * 2.2
    e = env(n, 0.001, 0.16, 6)
    for k in (0.011, 0.022):
        i = int(k * SR); e[i:] += env(n - i, 0.0005, 0.012, 6) * 0.6
    return x * e * 0.6


def hat():
    n = int(0.08 * SR)
    return bandnoise(n, 7000, 16000) * env(n, 0.0005, 0.05, 6) * 0.9


def bass(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    saw = 2 * ((t * freq) % 1) - 1
    sub = np.sin(2 * np.pi * freq * t)
    x = lowpass(0.5 * saw + 0.8 * sub, 180 + 900 * np.exp(-t * 14))
    return np.tanh(1.5 * x) * env(n, 0.004, dur * 0.9, 3) * 0.55


def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):
            x += 2 * ((t * f * (1 + det / 100)) % 1) - 1
    x = lowpass(x / (len(freqs) * 3), 1400)
    a = np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return x * a * 0.22


def whoosh(dur=0.4):
    n = int(dur * SR); t = np.arange(n) / SR
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    x = bandnoise(n, 200, 9000)
    x = lowpass(x, 400 + 7000 * shape)
    return x * shape * 2.2


def impact():
    n = int(1.6 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t * 9)) / SR) * env(n, 0.001, 1.1, 4)
    crack = bandnoise(n, 1500, 12000) * env(n, 0.0005, 0.08, 7)
    return np.tanh(1.8 * boom) * 0.9 + crack * 0.7


def riser(dur=2.0):
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    x = bandnoise(n, 300, 14000)
    x = lowpass(x, 300 + 9000 * k ** 2) * k ** 2
    tone = np.sin(2 * np.pi * np.cumsum(220 + 1400 * k ** 3) / SR) * 0.12 * k ** 2
    return (x * 1.4 + tone)


def click():
    n = int(0.03 * SR)
    return bandnoise(n, 3000, 12000) * env(n, 0.0002, 0.006, 6) * 1.2


def pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 30) + 300) / SR) * env(n, 0.001, 0.06, 6) * 0.6


def shimmer():
    n = int(1.4 * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for i, f in enumerate([1760, 2217, 2637, 3520]):
        d = int(i * 0.05 * SR)
        x[d:] += np.sin(2 * np.pi * f * t[: n - d]) * env(n - d, 0.002, 0.8, 4)
    return x * 0.12


def sub():
    n = int(1.2 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(55 * np.exp(-t * 1.2)) / SR) * env(n, 0.005, 1.0, 3) * 0.8


def glitch():
    n = int(0.22 * SR)
    x = np.repeat(RNG.standard_normal(n // 120 + 1), 120)[:n]
    sq = np.sign(np.sin(2 * np.pi * 180 * np.arange(n) / SR))
    return (x * 0.4 + sq * 0.25) * env(n, 0.001, 0.2, 2)


SFX = {"whoosh": whoosh, "impact": impact, "riser": riser, "click": click, "pop": pop, "shimmer": shimmer, "sub": sub, "glitch": glitch}


def hit(spec, key, s):
    """True if the 16-step pattern `key` has an 'x' at step s (empty/missing pattern = off)."""
    pat = spec.get(key) or ""
    return bool(pat) and pat[s % len(pat)] == "x"


def place(buf, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    if i < 0:
        x = x[-i:]; i = 0
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m] * gain


def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    dur = float(spec["duration"])
    n = int(dur * SR) + SR
    music = np.zeros(n); sfx = np.zeros(n); duck = np.ones(n)
    bpm = spec.get("bpm")
    if bpm:
        step = 60.0 / bpm / 4; bar = step * 16; start = float(spec.get("start", 0))
        k_, c_, h_ = kick(), clap(), hat()
        bars = int(np.ceil((dur - start) / bar)) + 1
        for b in range(bars):
            t_bar = start + b * bar
            for s in range(16):
                t = t_bar + s * step + (spec.get("swing", 0) * step if s % 2 else 0)
                if t >= dur: break
                if hit(spec, "kick", s):
                    place(music, k_, t)
                    i = int(t * SR); m = min(int(0.25 * SR), n - i)
                    if m > 0: duck[i:i + m] = np.minimum(duck[i:i + m], 1 - 0.6 * np.exp(-np.arange(m) / SR * 14))
                if hit(spec, "clap", s): place(music, c_, t, 0.8)
                if hit(spec, "hat", s): place(music, h_, t, 0.35 + 0.15 * (s % 4 == 2))
                notes = spec.get("bassNotes")
                if notes and hit(spec, "bass", s):
                    place(music, bass(hz(notes[b % len(notes)]), step * 2.2), t, 0.9 * 1.0)
            chords = spec.get("pad")
            if chords:
                place(music, pad([hz(c) for c in chords[b % len(chords)]], bar), t_bar, 1.0)
    mf, mt = spec.get("musicFrom", 0), spec.get("musicTo")
    gate = np.ones(n); tt = np.arange(n) / SR
    gate *= np.clip((tt - mf) / 0.01, 0, 1)
    if mt is not None: gate *= np.clip((mt - tt) / 0.05, 0, 1)
    for e in spec.get("events", []):
        fn = SFX[e["type"]]
        x = fn(e["dur"]) if "dur" in e and e["type"] in ("whoosh", "riser") else fn()
        # risers END at t (they lead into the hit); whooshes are centered on t; others start at t
        t = e["t"] - (len(x) / SR if e["type"] == "riser" else (len(x) / SR / 2 if e["type"] == "whoosh" else 0))
        place(sfx, x, t, e.get("gain", 1.0))
    mixed = music * duck * gate * 0.8 + sfx * 0.75
    a, b = spec.get("from", 0), spec.get("to", dur)
    mixed = mixed[int(a * SR):int(b * SR)]
    fade = int(0.02 * SR); mixed[:fade] *= np.linspace(0, 1, fade); mixed[-fade * 5:] *= np.linspace(1, 0, fade * 5)
    peak = np.max(np.abs(mixed)) + 1e-9
    mixed = np.tanh(mixed / peak * 1.3) * float(spec.get("master", 0.85)) / np.tanh(1.3)
    pcm = (np.stack([mixed, mixed], 1) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()

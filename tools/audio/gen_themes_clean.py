"""Темы «Путника», чистая версия (25.11): ни одного шумового слоя — только чистые тона.

Чем отличается от gen_themes.py:
- все инструменты собраны из гармоник (аддитивный синтез), а не из пилы и шума: нет зеркальных призвуков
  и шипения на верхах; гармоники выше 9 кГц не генерируются;
- убраны ветер, море, дыхание вистла, шорох смычка, шумовой удар бубна, «жужжание» лиры;
- реверберация мягче и темнее, на выходе срез выше 11 кГц и ниже 35 Гц, без перегруза.
Мелодии — свои, оригинальные (стиль: славянский фолк-эпос / северная колыбельная / пастораль).

По 3 варианта каждой темы:
  prologue_1 — как было, но чисто; prologue_2 — камерно: виолончель, гусли и бубен; prologue_3 — хор и струнные.
  spirits_1 — голос и арфа; spirits_2 — флейта и колокольчики; spirits_3 — только хор и арфа, совсем тихо.
  finale_1 — вистл, арфа, струнные; finale_2 — гусли и виолончель, проще и теплее; finale_3 — торжественно: хор,
  струнные и колокола.
Запуск: python3 tools/audio/gen_themes_clean.py [папка] [имена…]
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfiltfilt

SR = 44100
rng = np.random.default_rng(2512)
FMAX = 9000.0


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def filt(x, kind, f, o=4):
    return sosfiltfilt(butter(o, f, kind, fs=SR, output="sos"), x)


def env(n, a, r, hold=1.0):
    e = np.full(n, hold)
    A, R = min(n, int(a * SR)), min(n, int(r * SR))
    if A:
        e[:A] = np.linspace(0, hold, A) ** 1.5
    if R:
        e[-R:] *= np.linspace(1, 0, R) ** 1.5
    return e


def vib(t, rate=5.2, depth=0.005, delay=0.3):
    return 1 + depth * np.clip((t - delay) / 0.5, 0, 1) * np.sin(2 * np.pi * rate * t + rng.random() * 6)


def additive(f, dur, amps, vibrato=True, decay=None):
    """Тон из гармоник: amps[k-1] — громкость k-й; decay[k-1] — затухание (для щипковых)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    fr = f * vib(t) if vibrato else np.full(n, f)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        if a <= 0 or f * k > FMAX:
            continue
        part = a * np.sin(k * ph + rng.random() * 6)
        if decay is not None:
            part *= np.exp(-t * decay[k - 1])
        x += part
    return x


def formant_gain(freq, peaks):
    return sum(g * np.exp(-((freq - p) / (p * 0.18)) ** 2) for p, g in peaks) + 0.05


# ------------------------------------------------------------------ чистые инструменты
def cello(f, dur):
    peaks = [(250, 1.0), (500, 0.7), (1100, 0.35)]
    amps = [formant_gain(f * k, peaks) / k ** 0.8 for k in range(1, 17)]
    return additive(f, dur, amps) * env(int(dur * SR), 0.15, 0.3) * 0.5


def fiddle(f, dur):
    peaks = [(300, 0.7), (1100, 1.0), (2600, 0.6)]
    amps = [formant_gain(f * k, peaks) / k ** 0.7 for k in range(1, 17)]
    return additive(f, dur, amps) * env(int(dur * SR), 0.1, 0.25) * 0.4


def lyre(f, dur):
    """Колёсная лира без жужжания: носовой тембр, ровная атака."""
    peaks = [(350, 0.8), (900, 1.0), (1800, 0.7), (3000, 0.3)]
    amps = [formant_gain(f * k, peaks) / k ** 0.6 for k in range(1, 15)]
    return additive(f, dur, amps, vibrato=False) * env(int(dur * SR), 0.08, 0.2) * 0.4


def voice(f, dur, vowel="u", a=0.35, r=0.6):
    peaks = {"a": [(800, 1.0), (1150, 0.5)], "o": [(450, 1.0), (800, 0.45)], "u": [(330, 1.0), (700, 0.3)]}[vowel]
    amps = [formant_gain(f * k, peaks) / k ** 0.5 for k in range(1, 13)]
    return additive(f, dur, amps) * env(int(dur * SR), a, r) * 0.45


def choir(freqs, dur, vowel="a", a=2.0, r=2.5):
    n = int(dur * SR)
    x = np.zeros(n)
    for f in freqs:
        for d in (-0.004, 0.0, 0.004):
            x += voice(f * (1 + d), dur, vowel, a, r)
    return x / (len(freqs) * 2.2)


def strings(freqs, dur, a=2.0, r=2.5, bright=0.6):
    n = int(dur * SR)
    x = np.zeros(n)
    amps = [1 / k ** (1.6 - bright * 0.6) for k in range(1, 11)]
    for f in freqs:
        for d in (-0.004, 0.0, 0.005):
            x += additive(f * (1 + d), dur, amps)
    return x * env(n, a, r) / (len(freqs) * 4)


def harp(f, dur=3.0):
    amps = [1 / k ** 1.4 for k in range(1, 11)]
    dec = [0.8 + 0.9 * k for k in range(1, 11)]
    x = additive(f, dur, amps, vibrato=False, decay=dec)
    x[:900] *= np.linspace(0, 1, 900)  # 20 мс — щипок без щелчка
    return x * 0.4


def gusli(f, dur=2.5):
    amps = [1 / k ** 1.1 for k in range(1, 13)]
    dec = [1.0 + 1.3 * k for k in range(1, 13)]
    x = additive(f * 1.0015, dur, amps, False, dec) * 0.5 + additive(f, dur, amps, False, dec) * 0.5
    x[:900] *= np.linspace(0, 1, 900)
    return x * 0.36


def flute(f, dur):
    amps = [1.0, 0.25, 0.1, 0.04]
    return additive(f, dur, amps) * env(int(dur * SR), 0.06, 0.2) * 0.55


def whistle(f, dur, grace=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    fr = np.full(n, f) * vib(t, 5.8, 0.004, 0.3)
    if grace:
        g = int(0.045 * SR)
        fr[:g] = grace
    ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.sin(ph) + 0.1 * np.sin(2 * ph) + 0.03 * np.sin(3 * ph)
    return x * env(n, 0.03, 0.12) * 0.55


def bell(f, dur=5.0):
    t = np.arange(int(dur * SR)) / SR
    parts = [(1.0, 1.0, 1.0), (2.0, 0.45, 1.6), (2.76, 0.3, 2.2), (5.4, 0.1, 3.5)]
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d / dur * 3) for m, a, d in parts if f * m < FMAX)
    x[:1800] *= np.linspace(0, 1, 1800)  # 40 мс — колокол «вплывает», а не бьёт
    return x * 0.28


def drum(big=True):
    """Бубен без шума: только тон с падением высоты — мягкий глухой удар."""
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    f = (52 if big else 80) + 45 * np.exp(-t * 22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (4.5 if big else 8))
    x[:600] *= np.linspace(0, 1, 600)
    return x * 0.45


def drone(f, dur):
    amps = [1.0, 0.5, 0.3, 0.15]
    return (additive(f, dur, amps, False) + 0.6 * additive(f * 1.5, dur, amps, False)) * env(int(dur * SR), 3, 3) * 0.35


# ------------------------------------------------------------------ сборка
def track(dur):
    return np.zeros((int(dur * SR), 2))


def put(out, sig, t, pan=0.0, gain=1.0):
    s = int(t * SR)
    if s >= len(out) or s < 0:
        return
    sig = sig[: len(out) - s] * gain
    out[s:s + len(sig), 0] += sig * np.cos((pan + 1) * np.pi / 4)
    out[s:s + len(sig), 1] += sig * np.sin((pan + 1) * np.pi / 4)


def melody(out, inst, notes, t0, beat, pan=0.0, gain=1.0, legato=1.05, **kw):
    t = t0
    for m, d in notes:
        if m is not None:
            put(out, inst(midi(m), d * beat * legato, **kw), t, pan, gain)
        t += d * beat
    return t


def hall(x, secs=3.0, wet=0.3):
    """Тёмный мягкий зал: хвост из сглаженного шума, отрезанного выше 3 кГц, — сам он не шипит."""
    L = int(secs * SR)
    t = np.arange(L) / SR
    y = np.empty_like(x)
    for ch in range(2):
        ir = filt(rng.standard_normal(L), "low", 3000) * np.exp(-t * 6.0 / secs)
        ir[: int(0.025 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        y[:, ch] = x[:, ch] * (1 - wet) + fftconvolve(x[:, ch], ir)[: len(x)] * wet * 1.3
    return y


def level_ride(x, target=0.06, strength=0.75, win=1.6):
    """Медленный «звукорежиссёр»: где тихо — чуть громче, где громко — тише (без резких скачков)."""
    mono = np.abs(x).mean(axis=1)
    w = int(win * SR)
    kern = np.hanning(w) / np.hanning(w).sum()
    rms = np.sqrt(np.maximum(fftconvolve(mono ** 2, kern, mode="same"), 0)) + 1e-4
    gain = np.clip((target / rms) ** strength, 0.35, 3.0)
    gain = fftconvolve(gain, kern, mode="same")
    return x * gain[:, None]


def softclip_peaks(x, ceiling=0.45):
    """Пики выше потолка плавно поджимаются — ничего не «режет ухо»."""
    a = np.abs(x)
    over = a > ceiling * 0.7
    y = x.copy()
    k = ceiling * 0.7
    y[over] = np.sign(x[over]) * (k + (ceiling - k) * np.tanh((a[over] - k) / (ceiling - k)))
    return y


def master(x, fade_in=1.0, fade_out=4.0, loop=False):
    for ch in range(2):
        x[:, ch] = filt(filt(x[:, ch], "low", 8500), "high", 40)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.06
    x = level_ride(x)
    if loop:
        f = int(4.0 * SR)
        w = np.linspace(0, 1, f)[:, None]
        y = x[:-f].copy()
        y[:f] = x[:f] * w + x[-f:] * (1 - w)
        x = y
    else:
        x = x * env(len(x), max(fade_in, 3.0), fade_out)[:, None]
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.05  # общий уровень около −26 дБ: тихий фон
    return softclip_peaks(x, 0.4)


# ------------------------------------------------------------------ мелодии (свои)
PRO_THEME = [(62, 1), (65, 1), (67, 1.5), (69, 0.5), (70, 2), (69, 1), (67, 1), (65, 1.5), (64, 0.5), (62, 3), (None, 1),
             (60, 1), (62, 1), (65, 1.5), (67, 0.5), (69, 2), (67, 1), (65, 1), (64, 1.5), (61, 0.5), (62, 3), (None, 1)]
LULLABY = [(69, 2), (72, 1), (74, 1), (76, 3), (74, 1), (72, 2), (71, 1), (69, 1), (71, 4),
           (69, 2), (67, 1), (66, 1), (67, 2), (69, 2), (64, 4), (None, 2)]
TUNE = [(74, 1, 76), (76, 1, None), (78, 2, 79), (76, 1, None), (74, 1, None), (71, 2, 73), (69, 2, None),
        (71, 1, None), (74, 1, 76), (76, 2, None), (78, 1, 79), (81, 1, None), (79, 2, None), (78, 4, 79),
        (74, 1, 76), (76, 1, None), (78, 2, None), (81, 2, 83), (79, 1, None), (78, 1, None), (76, 2, None),
        (74, 6, 76)]


def octave(notes, k):
    return [(m + 12 * k if m else None, d) for m, d in notes]


# ------------------------------------------------------------------ пролог
def prologue(v):
    x = track(52)
    beat = 0.62
    put(x, drone(midi(38), 50), 1.0, 0, 0.6)
    if v in (1, 2):
        for t in [3, 6.5, 10]:
            put(x, drum(True), t, 0, 0.6)
        for i, t in enumerate(np.arange(12, 47, beat * 2)):
            put(x, drum(i % 4 == 0), t, 0.05, 0.55 if i % 4 == 0 else 0.3)
    if v == 1:
        melody(x, lyre, PRO_THEME, 12, beat, pan=-0.15, gain=0.6)
        put(x, choir([midi(50), midi(57), midi(62)], 14, "a"), 26, 0.1, 0.5)
        put(x, choir([midi(46), midi(53), midi(58), midi(62)], 8, "a"), 38, 0.1, 0.5)
        melody(x, fiddle, octave(PRO_THEME[11:], 1), 28.9, beat, pan=0.25, gain=0.45)
    elif v == 2:
        melody(x, cello, octave(PRO_THEME, -1), 12, beat, pan=-0.1, gain=0.8)
        t = 12
        for m, d in PRO_THEME:  # гусли отвечают на сильные доли
            if m and d >= 1.5:
                put(x, gusli(midi(m)), t, 0.3, 0.5)
            t += d * beat
    else:
        put(x, strings([midi(38), midi(45), midi(50)], 12, 3, 3), 2, 0, 0.6)
        melody(x, voice, PRO_THEME, 12, beat, pan=0.0, gain=0.8, vowel="a")
        put(x, choir([midi(50), midi(57), midi(62)], 14, "a"), 24, -0.1, 0.55)
        put(x, choir([midi(46), midi(53), midi(58), midi(62)], 8, "o"), 37, 0.1, 0.55)
        put(x, strings([midi(46), midi(53), midi(58)], 8, 2, 3), 37, 0, 0.5)
    put(x, strings([midi(38), midi(45), midi(50)], 8, 1.0, 4.0), 44, 0, 0.6)
    return master(hall(x, 3.5, 0.32), 2.0, 5.0)


# ------------------------------------------------------------------ духи (петля)
def spirits(v):
    x = track(44)
    beat = 0.9
    put(x, drone(midi(33), 44), 0, 0, 0.5)
    chords = [[57, 60, 64, 69], [55, 59, 62, 67], [57, 60, 64, 69], [52, 55, 59, 66]]
    t = 0.5
    while t < 40:
        for c in chords:
            for k, m in enumerate(c + [c[2]]):
                put(x, harp(midi(m)), t + k * beat * 0.5, pan=-0.35 + k * 0.15, gain=0.3 if v != 3 else 0.22)
            t += beat * 4
            if t >= 40:
                break
    if v == 1:
        melody(x, voice, LULLABY, 4.0, beat, pan=0.1, gain=0.7, vowel="u")
        melody(x, voice, octave(LULLABY[:9], -1), 26.0, beat, pan=-0.2, gain=0.4, vowel="o")
    elif v == 2:
        melody(x, flute, octave(LULLABY, 1), 4.0, beat, pan=0.15, gain=0.45)
        for i in range(10):
            put(x, bell(midi([81, 84, 88, 93][i % 4]), 4), 3 + i * 3.7, pan=np.sin(i) * 0.6, gain=0.12)
    else:
        put(x, choir([midi(57), midi(64)], 20, "u", 4, 5), 2, 0, 0.45)
        put(x, choir([midi(55), midi(62)], 20, "u", 4, 5), 21, 0, 0.45)
    for t in np.arange(2, 42, 3.6):
        put(x, drum(True), t, 0, 0.15)
    return master(hall(x, 4.0, 0.36), loop=True)


# ------------------------------------------------------------------ финал
def finale(v):
    x = track(62)
    beat = 0.55
    put(x, strings([midi(47), midi(54), midi(59), midi(62)], 9, 2.5, 2.5), 0.5, 0, 0.55)
    put(x, strings([midi(43), midi(50), midi(55), midi(59)], 7, 2.0, 2.5), 8.5, 0, 0.55)
    sad = [(66, 3), (64, 1), (62, 2), (61, 2), (59, 4), (None, 1), (62, 2), (64, 2), (66, 4)]
    melody(x, cello if v == 2 else fiddle, octave(sad, -1) if v == 2 else sad, 1.5, beat * 1.4, pan=0.2,
           gain=0.6 if v == 2 else 0.45)
    D, G, Bm, A = [50, 57, 62, 66], [55, 59, 62, 67], [47, 54, 59, 62], [57, 61, 64, 69]
    t = 15.5
    pl = gusli if v == 2 else harp
    for c in [D, G, Bm, A, D, G, A]:
        put(x, strings([midi(m) for m in c], beat * 8.5, 1.2, 1.5, 0.7), t, 0, 0.45)
        for k in range(8):
            put(x, pl(midi(c[k % 4] + (12 if k >= 4 else 0))), t + k * beat, pan=-0.4 + k * 0.1, gain=0.25)
        t += beat * 8
    home = t
    tt = 15.5 + beat * 4
    for m, d, g in TUNE:
        if v == 1:
            put(x, whistle(midi(m), d * beat * 1.02, midi(g) if g else None), tt, 0.15, 0.5)
        elif v == 2:
            put(x, cello(midi(m - 12), d * beat * 1.05), tt, 0.1, 0.6)
        else:
            put(x, voice(midi(m - 12), d * beat * 1.05, "a"), tt, 0.0, 0.65)
        tt += d * beat
    if v == 3:
        put(x, choir([midi(62), midi(66), midi(69)], 10, "o", 3, 3), 30, 0, 0.3)
    put(x, strings([midi(38), midi(50), midi(57), midi(62), midi(66), midi(69)], 14, 1.0, 6.0, 0.8), home, 0, 0.6)
    if v != 2:
        put(x, choir([midi(62), midi(66), midi(69)], 13, "o", 1.5, 6.0), home + 0.3, 0, 0.45 if v == 1 else 0.6)
    for i, m in enumerate([74, 78, 81, 86, 81, 86]):
        put(x, bell(midi(m), 6), home + 0.8 + i * 1.3, pan=-0.5 + i * 0.2, gain=0.22 if v != 3 else 0.32)
    return master(hall(x, 3.2, 0.3), 2.0, 6.0)


TRACKS = {f"{name}_{v}": (fn, v) for name, fn in [("prologue", prologue), ("spirits", spirits), ("finale", finale)]
          for v in (1, 2, 3)}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for name in (sys.argv[2:] or list(TRACKS)):
        fn, v = TRACKS[name]
        x = fn(v)
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, round(len(x) / SR, 1), "с")

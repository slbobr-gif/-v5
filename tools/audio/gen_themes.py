"""Темы «Путника» (25.11): пролог, духи, финал. Мелодии свои, оригинальные; чужих мелодий и записей нет.

Ориентиры по настроению (только стиль — лад, инструменты, темп; ни одной чужой ноты):
- пролог — тёмный славянский фолк-эпос: колёсная лира и бурдон, бубен, хор «а-а», ре эолийский;
- духи — северная колыбельная: тихий «женский» голос без слов, арфа, море и низкий бурдон, ля дорийский, петля;
- финал — пасторальный: вистл с форшлагами, арфа, тёплые струнные; начинается в си миноре (трудный путь)
  и выходит в ре мажор (дошёл), в конце колокола.
Запуск: python3 tools/audio/gen_themes.py [папка] → prologue.wav, spirits.wav, finale.wav
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
rng = np.random.default_rng(2511)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def filt(x, kind, f, o=2):
    return sosfilt(butter(o, f, kind, fs=SR, output="sos"), x)


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain)
    A, R = min(n, int(a * SR)), min(n, int(r * SR))
    if A:
        e[:A] = np.linspace(0, sustain, A)
    if R:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def saw(f, t, ph=0.0):
    return ((f * t + ph) % 1.0) * 2 - 1


def vib(t, rate=5.3, depth=0.006, delay=0.25):
    ramp = np.clip((t - delay) / 0.4, 0, 1)
    return 1 + depth * ramp * np.sin(2 * np.pi * rate * t + rng.random() * 6)


def formant(x, peaks):
    return sum(g * filt(x, "band", [f * 0.88, f * 1.12]) for f, g in peaks)


# ------------------------------------------------------------------ инструменты
def bowed(f, dur, bright=1.0):
    """Смычковая (скрипка/лира): пила с вибрато, корпус — форманты, немного шума смычка."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = np.cumsum(f * vib(t)) / SR
    x = (ph % 1.0) * 2 - 1
    body = formant(x, [(280, 1.0), (520, 0.8), (1150 * bright, 0.6), (2800 * bright, 0.35)])
    bow = filt(rng.standard_normal(n), "band", [f * 2, min(f * 8, 12000)]) * 0.05
    return (body + bow) * env(n, 0.12, 0.25)


def hurdy(f, dur):
    """Колёсная лира: смычковая + жужжание (выпрямленный сигнал) — колючий фолковый тембр."""
    x = bowed(f, dur, 0.9)
    buzz = filt(np.abs(x) - np.mean(np.abs(x)), "band", [900, 4000]) * 0.5
    return x + buzz


def choir(freqs, dur, vowel="a", a=2.0, r=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    peaks = {"a": [(800, 1.0), (1150, 0.6), (2900, 0.25)],
             "o": [(450, 1.0), (800, 0.6), (2830, 0.15)],
             "u": [(325, 1.0), (700, 0.4), (2530, 0.1)]}[vowel]
    x = np.zeros(n)
    for f in freqs:
        for _ in range(4):  # четыре голоса на ноту, чуть вразнобой
            ph = np.cumsum(f * (1 + rng.uniform(-0.004, 0.004)) * vib(t, rng.uniform(4.6, 5.6), 0.005, 0.5)) / SR
            x += ((ph + rng.random()) % 1.0) * 2 - 1
    x = formant(x, peaks) + 0.04 * filt(rng.standard_normal(n), "band", [peaks[0][0], 6000])
    return x * env(n, a, r) / (len(freqs) * 4)


def voice(f, dur, vowel="u"):
    """Один тихий голос без слов: колыбельная."""
    return choir([f], dur, vowel, a=0.35, r=0.6) * 2.2


def harp(f, dur=3.0, bright=0.7):
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = filt(rng.standard_normal(p), "low", 2500 + 7000 * bright)
    chunks, total = [], 0
    while total < n:
        chunks.append(buf.copy())
        total += p
        buf = 0.997 * 0.5 * (buf + np.roll(buf, -1))
    x = np.concatenate(chunks)[:n]
    return x * np.exp(-np.arange(n) / SR * 0.9)


def whistle(f, dur, grace=None):
    """Вистл: чистый тон + дыхание; форшлаг — короткая верхняя нота перед основной."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    fr = np.full(n, f)
    if grace:
        g = int(0.045 * SR)
        fr[:g] = grace
    ph = 2 * np.pi * np.cumsum(fr * vib(t, 5.8, 0.004, 0.3)) / SR
    x = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    breath = filt(rng.standard_normal(n), "band", [f * 1.5, min(f * 6, 15000)]) * 0.05
    return (x + breath) * env(n, 0.03, 0.12) * 0.7


def strings(freqs, dur, a=2.0, r=2.5, cutoff=2200):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for d in (-0.005, 0.0, 0.006):
            x += saw(f * (1 + d), t, rng.random()) * vib(t, 5.0, 0.003, 0.0)
    x = filt(x, "low", cutoff)
    return x * env(n, a, r) / (len(freqs) * 3)


def drum(big=True):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = (55 if big else 85) + 50 * np.exp(-t * 25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (5 if big else 9))
    x += filt(rng.standard_normal(n), "band", [120, 900]) * np.exp(-t * 30) * 0.4
    return x


def bell(f, dur=5.0):
    t = np.arange(int(dur * SR)) / SR
    parts = [(1.0, 1.0, 1.0), (2.0, 0.5, 1.6), (2.76, 0.35, 2.2), (5.4, 0.15, 3.5), (8.9, 0.07, 5)]
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d / dur * 3) for m, a, d in parts)
    x[:150] *= np.linspace(0, 1, 150)
    return x * 0.5


def sea(n, level=1.0):
    x = filt(filt(np.cumsum(rng.standard_normal(n)) * 0.02, "high", 40), "low", 700)
    sw = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / 9.5) ** 2
    return x / (np.max(np.abs(x)) + 1e-9) * sw * level


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
    """notes: [(midi | None, доли)], None — пауза. Возвращает время конца."""
    t = t0
    for m, d in notes:
        if m is not None:
            put(out, inst(midi(m), d * beat * legato, **kw), t, pan, gain)
        t += d * beat
    return t


def hall(x, secs=3.2, wet=0.38, damp=5500):
    L = int(secs * SR)
    t = np.arange(L) / SR
    y = np.empty_like(x)
    for ch in range(2):
        ir = rng.standard_normal(L) * np.exp(-t * 5.5 / secs)
        ir = filt(ir, "low", damp)
        ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))  # предзадержка — «большой зал»
        ir /= np.sqrt(np.sum(ir ** 2))
        y[:, ch] = x[:, ch] * (1 - wet) + fftconvolve(x[:, ch], ir)[: len(x)] * wet * 1.5
    return y


def master(x, fade_in=1.0, fade_out=4.0, loop=False):
    if loop:
        f = int(4.0 * SR)
        w = np.linspace(0, 1, f)[:, None]
        y = x[:-f].copy()
        y[:f] = x[:f] * w + x[-f:] * (1 - w)
        x = y
    else:
        x = x * env(len(x), fade_in, fade_out)[:, None]
    x = x - x.mean(axis=0)
    x = x / (np.percentile(np.abs(x), 99.9) + 1e-9) * 0.75
    return np.tanh(x * 1.15) / 1.15


# ------------------------------------------------------------------ пролог: тёмный фолк-эпос, ре эолийский
def prologue():
    x = track(52)
    beat = 0.62
    # бурдон лиры D2–A2 на всё время, ветер
    put(x, hurdy(midi(38), 50) * 0.35 + hurdy(midi(45), 50) * 0.25, 1.0, 0, 0.55)
    wind = filt(rng.standard_normal(len(x)), "band", [200, 1200]) * (0.4 + 0.6 * np.linspace(1, 0.2, len(x)))
    x[:, 0] += wind * 0.03
    x[:, 1] += wind * 0.03
    # бубен: редко в начале, потом ровный шаг
    for t in [3, 6.5, 10]:
        put(x, drum(True), t, 0, 0.7)
    for i, t in enumerate(np.arange(12, 47, beat * 2)):
        put(x, drum(i % 4 == 0), t, 0.05, 0.6 if i % 4 == 0 else 0.35)
    # тема на лире — своя мелодия
    theme = [(62, 1), (65, 1), (67, 1.5), (69, 0.5), (70, 2), (69, 1), (67, 1), (65, 1.5), (64, 0.5), (62, 3), (None, 1),
             (60, 1), (62, 1), (65, 1.5), (67, 0.5), (69, 2), (67, 1), (65, 1), (64, 1.5), (61, 0.5), (62, 3), (None, 1)]
    melody(x, hurdy, theme, 12, beat, pan=-0.15, gain=0.5)
    # хор вступает на повторе, тема уходит октавой выше на скрипке
    put(x, choir([midi(50), midi(57), midi(62)], 14, "a"), 26, 0.1, 0.55)
    put(x, choir([midi(46), midi(53), midi(58), midi(62)], 8, "a"), 38, 0.1, 0.55)
    put(x, choir([midi(45), midi(52), midi(57), midi(61)], 7, "o"), 44, 0.1, 0.5)
    melody(x, bowed, [(m + 12 if m else None, d) for m, d in theme[11:]], 28.9, beat, pan=0.25, gain=0.32)
    # финальная открытая квинта
    put(x, strings([midi(38), midi(45), midi(50)], 8, 1.0, 4.0, 1200), 44, 0, 0.6)
    return master(hall(x, 3.8, 0.42), 2.0, 5.0)


# ------------------------------------------------------------------ духи: северная колыбельная, ля дорийский, петля
def spirits():
    x = track(44)
    beat = 0.9
    n = len(x)
    s = sea(n, 0.25)
    x[:, 0] += s
    x[:, 1] += s * 0.9
    put(x, strings([midi(33), midi(40)], 44, 4, 4, 600), 0, 0, 0.55)  # глубокий бурдон
    # арфа: медленные арпеджио Am — G — Am — Em(dorian F#)
    chords = [[57, 60, 64, 69], [55, 59, 62, 67], [57, 60, 64, 69], [52, 55, 59, 66]]
    t = 0.5
    for rep in range(3):
        for c in chords:
            for k, m in enumerate(c + [c[2]]):
                put(x, harp(midi(m), 3.0, 0.6), t + k * beat * 0.5, pan=-0.35 + k * 0.15, gain=0.28)
            t += beat * 4
            if t > 40:
                break
    # голос без слов — своя колыбельная, «у» и «о»
    lull = [(69, 2), (72, 1), (74, 1), (76, 3), (74, 1), (72, 2), (71, 1), (69, 1), (71, 4),
            (69, 2), (67, 1), (66, 1), (67, 2), (69, 2), (64, 4), (None, 2)]
    melody(x, voice, lull, 4.0, beat, pan=0.1, gain=0.55, vowel="u")
    melody(x, voice, [(m - 12 if m else None, d) for m, d in lull[:9]], 26.0, beat, pan=-0.2, gain=0.3, vowel="o")
    # редкий тихий удар, как далёкое сердце
    for t in np.arange(2, 42, 3.6):
        put(x, drum(True), t, 0, 0.18)
    return master(hall(x, 5.0, 0.5, 4500), loop=True)


# ------------------------------------------------------------------ финал: пастораль, си минор → ре мажор
def finale():
    x = track(62)
    beat = 0.55
    # 1. Трудный путь: струнные в си миноре, медленно
    put(x, strings([midi(47), midi(54), midi(59), midi(62)], 9, 2.5, 2.5, 1400), 0.5, 0, 0.55)
    put(x, strings([midi(43), midi(50), midi(55), midi(59)], 7, 2.0, 2.5, 1400), 8.5, 0, 0.55)
    melody(x, bowed, [(66, 3), (64, 1), (62, 2), (61, 2), (59, 4), (None, 1), (62, 2), (64, 2), (66, 4)], 1.5, beat * 1.4,
           pan=0.2, gain=0.3)
    # 2. Рассвет: арфа в ре мажоре, струнные расправляются (I–IV–vi–V)
    D, G, Bm, A = [50, 57, 62, 66], [55, 59, 62, 67], [47, 54, 59, 62], [57, 61, 64, 69]
    t = 15.5
    for c in [D, G, Bm, A, D, G, A]:  # последний — A: доминанта ведёт домой, в ре мажор
        put(x, strings([midi(m) for m in c], beat * 8.5, 1.2, 1.5, 2600), t, 0, 0.45)
        for k in range(8):
            put(x, harp(midi(c[k % 4] + (12 if k >= 4 else 0)), 2.5, 0.7), t + k * beat, pan=-0.4 + k * 0.1, gain=0.22)
        t += beat * 8
    home = t
    # 3. Вистл — своя пасторальная мелодия с форшлагами
    tune = [(74, 1, 76), (76, 1, None), (78, 2, 79), (76, 1, None), (74, 1, None), (71, 2, 73), (69, 2, None),
            (71, 1, None), (74, 1, 76), (76, 2, None), (78, 1, 79), (81, 1, None), (79, 2, None), (78, 4, 79),
            (74, 1, 76), (76, 1, None), (78, 2, None), (81, 2, 83), (79, 1, None), (78, 1, None), (76, 2, None),
            (74, 6, 76)]
    tt = 15.5 + beat * 4
    for m, d, g in tune:
        put(x, whistle(midi(m), d * beat * 1.02, midi(g) if g else None), tt, 0.15, 0.42)
        tt += d * beat
    # 4. Дома: большой ре мажор, хор «о», колокола
    put(x, strings([midi(38), midi(50), midi(57), midi(62), midi(66), midi(69)], 14, 1.0, 6.0, 3000), home, 0, 0.6)
    put(x, choir([midi(62), midi(66), midi(69)], 13, "o", 1.5, 6.0), home + 0.3, 0, 0.45)
    for i, m in enumerate([74, 78, 81, 86, 81, 86]):
        put(x, bell(midi(m), 6), home + 0.8 + i * 1.3, pan=-0.5 + i * 0.2, gain=0.25)
    return master(hall(x, 3.5, 0.4), 2.0, 6.0)


TRACKS = {"prologue": prologue, "spirits": spirits, "finale": finale}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for name in (sys.argv[2:] or list(TRACKS)):
        x = TRACKS[name]()
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, round(len(x) / SR, 1), "с")

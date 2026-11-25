"""Музыкальные темы с нуля (25.11): начало пути, встречи с духами, финал — по 3 варианта на выбор.

Всё синтезируется из простых волн и шума — чужих записей и семплов нет, права полностью наши.
Инструменты: колокол (неровные обертоны), гусли (щипок Карплуса — Стронга), варган (импульсы через
плывущий формантный фильтр), пэд (расстроенные пилы через фильтр), птицы (свисты), шаги (шорох гравия),
кит (медленные глиссандо с обертонами), шёпот (шум через гласные-форманты), большой зал (реверберация).
Запуск: python3 tools/audio/gen_music.py [папка] → intro_a…c, spirit_a…c, finale_a…c (.wav).
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
rng = np.random.default_rng(1125)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def filt(x, kind, f, o=2):
    return sosfilt(butter(o, f, kind, fs=SR, output="sos"), x)


def env_adsr(n, a, r):
    e = np.ones(n)
    A, R = int(a * SR), int(r * SR)
    if A:
        e[:A] = np.linspace(0, 1, A)
    if R:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def place(out, sig, t, pan=0.0, gain=1.0):
    s = int(t * SR)
    if s >= len(out):
        return
    sig = sig[: len(out) - s] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    out[s:s + len(sig), 0] += sig * l
    out[s:s + len(sig), 1] += sig * r


def hall(x, secs=2.8, wet=0.35):
    L = int(secs * SR)
    t = np.arange(L) / SR
    y = np.empty_like(x)
    for ch in range(2):
        ir = rng.standard_normal(L) * np.exp(-t * 5.5 / secs)
        ir = filt(ir, "low", 6000)
        ir /= np.sqrt(np.sum(ir ** 2))
        y[:, ch] = x[:, ch] * (1 - wet) + fftconvolve(x[:, ch], ir)[: len(x)] * wet * 1.4
    return y


# ------------------------------------------------------------------ инструменты
def bell(f, dur=6.0, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    parts = [(0.5, 1.0, 1.2), (1.0, 0.9, 1.0), (1.19, 0.5, 1.6), (1.5, 0.45, 2.0), (2.0, 0.4, 2.4),
             (2.52, 0.25 * bright, 3.2), (3.0, 0.2 * bright, 4.0), (4.07, 0.12 * bright, 5.5)]
    x = sum(a * np.sin(2 * np.pi * f * m * t + rng.random() * 6) * np.exp(-t * d / dur * 3) for m, a, d in parts)
    x[:200] *= np.linspace(0, 1, 200)
    return x / 3


def pluck(f, dur=2.5, bright=0.5):
    """Гусли: щипок Карплуса — Стронга с мягким затуханием."""
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = filt(rng.standard_normal(p), "low", 2000 + 6000 * bright)
    k = 0.996
    chunks = []
    total = 0
    while total < n:  # по периоду за раз: выход = буфер, буфер = сглаженный буфер (вектором, быстро)
        chunks.append(buf.copy())
        total += p
        buf = k * 0.5 * (buf + np.roll(buf, -1))
    out = np.concatenate(chunks)[:n]
    return out * np.exp(-np.arange(n) / SR * 0.8)


def pad(freqs, dur, cutoff=1400, a=2.5, r=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.006, 0.0, 0.007):
            ph = rng.random()
            x += ((f * (1 + det) * t + ph) % 1.0) * 2 - 1
    x = filt(x, "low", cutoff, o=2)
    return x * env_adsr(n, a, r) / (len(freqs) * 3)


def drone(f, dur, beat=0.15):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * (f + beat) * t) + 0.35 * np.sin(2 * np.pi * 1.5 * f * t)
    x += 0.2 * np.sin(2 * np.pi * 2 * (f - beat) * t)
    return x / 2.2 * env_adsr(len(t), 3, 3)


def bird(t0_dur=0.25):
    n = int(t0_dur * SR)
    t = np.arange(n) / SR
    f0 = rng.uniform(2500, 4500)
    f = f0 + rng.uniform(-1500, 1500) * np.sin(2 * np.pi * rng.uniform(6, 18) * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) ** 2
    return x


def step(gravel=True):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    x = filt(rng.standard_normal(n), "band", [300, 4000 if gravel else 1500]) * np.exp(-t * 28)
    grains = np.zeros(n)
    for _ in range(rng.integers(8, 20)):
        i = rng.integers(0, n - 200)
        grains[i:i + 60] += rng.standard_normal(60) * np.exp(-np.linspace(0, 5, 60)) * 0.6
    return x + filt(grains, "high", 2000)


def jaw_harp(f0, dur, sweep_hz):
    """Варган: узкие импульсы на f0 через формантный фильтр, центр которого плывёт (рот играющего)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    pulse = (np.sin(2 * np.pi * f0 * t) > 0.97).astype(float)
    pulse = filt(pulse, "high", 80)
    centre = 700 + 900 * (0.5 + 0.5 * np.sin(2 * np.pi * sweep_hz * t))
    out = np.zeros(n)
    blk = 2048
    for s in range(0, n, blk):
        c = centre[s]
        seg = pulse[max(0, s - 512):s + blk]
        y = filt(seg, "band", [c * 0.85, c * 1.15], o=2)
        out[s:s + blk] += y[len(seg) - len(pulse[s:s + blk]):]
    return out * np.exp(-t * 1.2) * 4


def whale(dur=6.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    a, b = rng.uniform(120, 220), rng.uniform(260, 520)
    curve = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / dur * rng.uniform(1, 1.6), 0, 1))
    f = a + (b - a) * curve + 6 * np.sin(2 * np.pi * 5 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    return x * np.sin(np.pi * t / dur) ** 1.5 * 0.5


def whisper(dur=1.2):
    """Шёпот: шум через две форманты гласной, слоги с паузами — без слов."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vowels = [(300, 2300), (500, 1500), (700, 1100), (400, 800)]
    f1, f2 = vowels[rng.integers(0, 4)]
    nz = rng.standard_normal(n)
    x = filt(nz, "band", [f1 * 0.8, f1 * 1.2]) + 0.7 * filt(nz, "band", [f2 * 0.85, f2 * 1.15])
    x += 0.3 * filt(nz, "band", [4000, 8000])
    syll = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(3, 6) * t)
    return x * syll * np.sin(np.pi * t / dur) ** 2 * 0.6


# ------------------------------------------------------------------ сборка
def track(dur):
    return np.zeros((int(dur * SR), 2))


def finish(x, fade_in=1.5, fade_out=3.0, loop=False):
    if loop:
        f = int(3.0 * SR)
        w = np.linspace(0, 1, f)[:, None]
        y = x[:-f].copy()
        y[:f] = x[:f] * w + x[-f:] * (1 - w)
        x = y
    else:
        e = env_adsr(len(x), fade_in, fade_out)[:, None]
        x = x * e
    x = x - x.mean(axis=0)
    x = x / (np.percentile(np.abs(x), 99.95) + 1e-9) * 0.8
    return np.tanh(x * 1.1) / 1.1


D_DORIAN = [62, 64, 65, 67, 69, 71, 72, 74]  # ре дорийский — северная, «былинная» окраска


def intro_a():  # Колокола
    x = track(34)
    for i, t in enumerate(np.arange(0.5, 28, 4.0)):
        place(x, bell(midi(38 if i % 2 == 0 else 45), 9, 0.7), t, pan=-0.2 + 0.4 * (i % 2), gain=0.9)
    for t in np.arange(2.5, 30, 2.0):
        place(x, bell(midi(rng.choice([69, 74, 76, 81])), 4, 1.2), t + rng.uniform(-0.2, 0.2), pan=rng.uniform(-0.6, 0.6), gain=0.25)
    place(x, pad([midi(50), midi(57), midi(62), midi(65)], 16, 900), 2, gain=0.5)
    place(x, pad([midi(53), midi(57), midi(60), midi(65)], 16, 1200), 16, gain=0.55)
    hum = filt(rng.standard_normal(len(x)), "low", 200) * np.linspace(0.6, 0.05, len(x))
    x[:, 0] += hum * 0.25
    x[:, 1] += hum * 0.25
    return finish(hall(x, 3.5, 0.4))


def intro_b():  # Утро в дорогу: птицы и гусли
    x = track(34)
    melody = [62, 65, 67, 69, 67, 65, 64, 62, 69, 72, 71, 69, 67, 65, 64, 62]
    t = 3.0
    for i, m in enumerate(melody):
        place(x, pluck(midi(m), 2.4, 0.5), t, pan=-0.2, gain=0.55)
        if i % 4 == 0:
            place(x, pluck(midi(m - 12), 3.0, 0.3), t, pan=0.2, gain=0.35)
        t += 0.75 if i % 4 != 3 else 1.5
    place(x, pad([midi(50), midi(57), midi(62)], 30, 1000), 1, gain=0.35)
    for _ in range(40):
        place(x, bird(rng.uniform(0.1, 0.35)), rng.uniform(0, 32), pan=rng.uniform(-0.9, 0.9), gain=rng.uniform(0.04, 0.12))
    return finish(hall(x, 2.2, 0.3))


def intro_c():  # Первые шаги
    x = track(34)
    for i, t in enumerate(np.arange(4.0, 32, 0.56)):
        place(x, step(), t + rng.uniform(-0.02, 0.02), pan=-0.15 if i % 2 else 0.15, gain=0.35)
    chords = [[50, 57, 62, 65], [48, 55, 60, 64], [46, 53, 58, 62], [45, 52, 57, 61]]
    for i, c in enumerate(chords * 2):
        place(x, pad([midi(n) for n in c], 5.5, 1100, 1.5, 2.0), 1 + i * 4, gain=0.45)
    for i, m in enumerate([74, 72, 69, 74, 76, 74, 72, 69]):
        place(x, bell(midi(m), 3, 1.4), 6 + i * 3.2, pan=0.4, gain=0.2)
    return finish(hall(x, 2.0, 0.28))


def spirit_a():  # Лесной морок
    x = track(36)
    place(x, drone(midi(38), 36, 0.18), 0, gain=0.7)
    place(x, drone(midi(45), 36, 0.11), 0, pan=0.3, gain=0.4)
    for _ in range(9):  # скрип ствола: медленный низкий свист с шумом
        n = int(rng.uniform(0.8, 1.8) * SR)
        tt = np.arange(n) / SR
        f = rng.uniform(90, 180) * (1 + 0.4 * tt / tt[-1])
        cr = np.sin(2 * np.pi * np.cumsum(f) / SR) * (np.sin(2 * np.pi * 30 * tt) > 0.3) * np.sin(np.pi * tt / tt[-1])
        place(x, filt(cr, "band", [100, 1500]), rng.uniform(1, 33), pan=rng.uniform(-0.8, 0.8), gain=0.18)
    breath = filt(rng.standard_normal(len(x)), "band", [200, 900]) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.12 * np.arange(len(x)) / SR))
    x[:, 0] += breath * 0.06
    x[:, 1] += breath * 0.06
    return finish(hall(x, 4.0, 0.45), loop=True)


def spirit_b():  # Шёпот
    x = track(36)
    place(x, pad([midi(74), midi(81), midi(86)], 36, 5000, 4, 4), 0, gain=0.2)
    t = 1.0
    while t < 34:
        place(x, whisper(rng.uniform(0.6, 1.6)), t, pan=rng.uniform(-1, 1), gain=0.35)
        t += rng.uniform(0.8, 2.6)
    for _ in range(14):  # стеклянные блики
        place(x, bell(midi(rng.choice([86, 89, 93, 98])), 3, 1.6), rng.uniform(0, 34), pan=rng.uniform(-0.7, 0.7), gain=0.08)
    place(x, drone(midi(33), 36, 0.07), 0, gain=0.35)
    return finish(hall(x, 4.5, 0.5), loop=True)


def spirit_c():  # Варган и бубен
    x = track(36)
    for i, t in enumerate(np.arange(0.5, 35, 1.6)):
        place(x, jaw_harp(midi(38), 1.5, rng.choice([1.5, 2.5, 3.5])), t, pan=-0.1, gain=0.5)
    for t in np.arange(0.5, 35, 0.8):  # бубен: глухой удар
        n = int(0.35 * SR)
        tt = np.arange(n) / SR
        drum = np.sin(2 * np.pi * (70 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
        drum += filt(rng.standard_normal(n), "band", [150, 1200]) * np.exp(-tt * 25) * 0.3
        place(x, drum, t, gain=0.5 if int(t / 0.8) % 2 == 0 else 0.3)
    place(x, drone(midi(26), 36, 0.05), 0, gain=0.3)
    return finish(hall(x, 2.5, 0.3), loop=True)


def finale_a():  # Киты
    x = track(42)
    sea = filt(np.cumsum(rng.standard_normal(len(x))) * 0.02, "high", 30)
    sea = filt(sea, "low", 600) * (0.6 + 0.4 * np.sin(2 * np.pi * np.arange(len(x)) / SR / 9.0) ** 2)
    x[:, 0] += sea * 0.5
    x[:, 1] += sea * 0.5
    for t in [3, 9, 16, 22, 29, 34]:
        place(x, whale(rng.uniform(4, 7)), t, pan=rng.uniform(-0.5, 0.5), gain=0.6)
    place(x, pad([midi(50), midi(57), midi(62), midi(66)], 38, 900, 6, 6), 2, gain=0.35)
    return finish(hall(x, 5.0, 0.5), 3, 5)


def finale_b():  # Сияние
    x = track(42)
    place(x, pad([midi(50), midi(57), midi(62), midi(66), midi(69)], 40, 2500, 5, 6), 0.5, gain=0.5)
    arp = [62, 66, 69, 74, 78, 74, 69, 66]
    for i in range(36):
        place(x, bell(midi(arp[i % len(arp)] + (12 if i > 20 else 0)), 4, 1.3), 3 + i * 0.95, pan=np.sin(i) * 0.6, gain=0.22)
    for _ in range(60):
        place(x, bell(midi(rng.choice([86, 90, 93, 98])), 1.5, 2.0), rng.uniform(5, 38), pan=rng.uniform(-1, 1), gain=0.05)
    return finish(hall(x, 5.0, 0.55), 3, 6)


def finale_c():  # Домой
    x = track(42)
    melody = [62, 65, 67, 69, 72, 71, 69, 67, 69, 74, 72, 71, 69, 67, 66, 62]
    t = 2.0
    for i, m in enumerate(melody):
        place(x, pluck(midi(m), 3.0, 0.45), t, pan=-0.15, gain=0.5)
        if i % 4 == 0:
            place(x, pluck(midi(m - 12), 3.5, 0.3), t, pan=0.25, gain=0.35)
        t += 0.9 if i % 4 != 3 else 1.8
    place(x, pad([midi(50), midi(57), midi(62)], 18, 1000), 1, gain=0.35)
    place(x, pad([midi(50), midi(57), midi(62), midi(66)], 20, 1400), 19, gain=0.45)  # к мажору — дома
    for i, tb in enumerate([20, 24, 28, 32]):
        place(x, bell(midi([74, 78, 81, 86][i]), 6, 1.0), tb, pan=0.3, gain=0.3)
    sea = filt(rng.standard_normal(len(x)), "low", 500) * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(len(x)) / SR / 10) ** 2)
    x[:, 0] += sea * 0.08
    x[:, 1] += sea * 0.08
    return finish(hall(x, 3.5, 0.4), 2, 6)


TRACKS = {
    "intro_a": intro_a, "intro_b": intro_b, "intro_c": intro_c,
    "spirit_a": spirit_a, "spirit_b": spirit_b, "spirit_c": spirit_c,
    "finale_a": finale_a, "finale_b": finale_b, "finale_c": finale_c,
}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    only = sys.argv[2:] or list(TRACKS)
    for name in only:
        x = TRACKS[name]()
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, round(len(x) / SR, 1), "с")

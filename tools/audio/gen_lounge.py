"""Темы «Путника» в стиле лаундж-фэнтези (25.11): пролог, духи, финал. Мелодии и гармонии — свои.

Лаундж: медленный мягкий бит (~72–80 уд/мин), электропиано, тёплые аккорды с септимами и нонами,
глубокий мягкий бас. Фэнтези: челеста, арфа, воздушный хор, колокольчики.
Чисто и тихо: только тоны (без шумовых хэтов и шипения), мастеринг из gen_themes_clean.py — ровная
громкость, около −27 дБ, мягкие пики.
Запуск: python3 tools/audio/gen_lounge.py [папка] → lounge_prologue.wav, lounge_spirits.wav, lounge_finale.wav
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_themes_clean as B  # noqa: E402

SR = B.SR
rng = np.random.default_rng(3011)
midi, env, put, additive, hall, master, track = B.midi, B.env, B.put, B.additive, B.hall, B.master, B.track


# ------------------------------------------------------------------ лаундж-инструменты
def epiano(f, dur, vel=1.0):
    """Электропиано: тёплый тон + короткий «стеклянный» призвук язычка, затухание, лёгкое тремоло."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = additive(f, dur, [1.0, 0.35, 0.12, 0.05], vibrato=False, decay=[0.9, 1.6, 2.4, 3.0])
    tine = np.sin(2 * np.pi * f * 7.02 * t) * np.exp(-t * 18) * 0.08 if f * 7 < 9000 else 0
    x = (body + tine) * (1 + 0.12 * np.sin(2 * np.pi * 4.2 * t))
    x[:700] *= np.linspace(0, 1, 700)
    return x * env(n, 0.0, 0.35) * 0.35 * vel


def celesta(f, dur=2.5):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.25 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 6)
    x[:900] *= np.linspace(0, 1, 900)
    return x * 0.22


def pad(freqs, dur, a=2.5, r=3.0):
    n = int(dur * SR)
    x = np.zeros(n)
    for f in freqs:
        for d in (-0.005, 0.0, 0.006):
            x += additive(f * (1 + d), dur, [1 / k ** 1.9 for k in range(1, 8)])
    return x * env(n, a, r) / (len(freqs) * 3) * 0.8


def air(freqs, dur):
    """Воздушный хор «у-у» поверх — фэнтези."""
    return B.choir(freqs, dur, "u", 3.0, 3.0) * 0.8


def bass(f, dur):
    n = int(dur * SR)
    x = additive(f, dur, [1.0, 0.2], vibrato=False)
    return x * env(n, 0.04, 0.25) * 0.5


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 40 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    x[:400] *= np.linspace(0, 1, 400)
    return x * 0.5


def tok():
    """Мягкий «ток» вместо малого барабана: тон, без шума."""
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 190 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 26)
    x[:300] *= np.linspace(0, 1, 300)
    return x * 0.22


def tick():
    """Тихий «тик» вместо хэта: короткий чистый тон, не шипит."""
    n = int(0.04 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 120)
    x[:60] *= np.linspace(0, 1, 60)
    return x * 0.05


def groove(out, t0, bars, beat, half=False):
    for b in range(bars):
        tb = t0 + b * 4 * beat
        put(out, kick(), tb, 0, 0.9)
        put(out, kick(), tb + 2.5 * beat, 0, 0.55)
        if not half:
            put(out, tok(), tb + beat, 0.1, 1.0)
            put(out, tok(), tb + 3 * beat, 0.1, 1.0)
        for e in range(8):
            put(out, tick(), tb + e * beat / 2 + (0.03 if e % 2 else 0.0), 0.35, 1.0 if e % 2 == 0 else 0.6)


def comp(out, chords, t0, beat, vel=1.0, rhythm=(0, 1.5, 2.5)):
    """Электропиано: аккорд на «раз», лёгкие подхваты — лаунджевый комп."""
    for i, c in enumerate(chords):
        tb = t0 + i * 4 * beat
        for k, r in enumerate(rhythm):
            for j, m in enumerate(c):
                put(out, epiano(midi(m), 1.6 if k == 0 else 0.9, vel * (1.0 if k == 0 else 0.6)), tb + r * beat + j * 0.012,
                    pan=-0.3 + 0.2 * j, gain=0.5)


def basses(out, roots, t0, beat):
    for i, r in enumerate(roots):
        tb = t0 + i * 4 * beat
        put(out, bass(midi(r), 2.2 * beat), tb, 0, 0.9)
        put(out, bass(midi(r + 7), 0.9 * beat), tb + 2.5 * beat, 0, 0.6)
        put(out, bass(midi(r), 0.9 * beat), tb + 3.5 * beat, 0, 0.5)


def pads(out, chords, t0, beat, gain=0.5):
    for i, c in enumerate(chords):
        put(out, pad([midi(m) for m in c], 4 * beat + 1.5, 1.2, 1.5), t0 + i * 4 * beat, 0, gain)


def lead(out, inst, notes, t0, beat, pan=0.15, gain=0.5):
    t = t0
    for m, d in notes:
        if m is not None:
            put(out, inst(midi(m), d * beat * 1.1), t, pan, gain)
        t += d * beat


# ------------------------------------------------------------------ пролог: начало пути, загадочно-тёпло, ре дорийский
def prologue():
    beat = 60 / 74
    x = track(56)
    prog = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 64], [53, 57, 60, 64, 67], [48, 55, 59, 62, 64]]  # Dm9 Bbmaj9 Fmaj9 Cmaj9
    roots = [38, 34, 41, 36]
    t0 = 2.0
    pads(x, prog * 4, t0, beat, 0.45)
    for c in range(4):  # челеста-арпеджио открывает
        for k, m in enumerate(prog[c % 4][1:] + [prog[c % 4][2] + 12]):
            put(x, celesta(midi(m + 12)), t0 + c * 4 * beat + k * beat * 0.75, pan=-0.4 + 0.2 * k, gain=0.6)
    comp(x, prog * 3, t0 + 16 * beat, beat, 0.9)
    basses(x, roots * 3, t0 + 16 * beat, beat)
    groove(x, t0 + 16 * beat, 12, beat)
    motif = [(69, 1.5), (72, 0.5), (74, 2), (None, 0.5), (72, 0.5), (69, 1), (67, 2), (None, 1),
             (65, 1.5), (67, 0.5), (69, 2), (72, 1), (69, 1), (64, 3), (None, 1)]
    lead(x, epiano, motif, t0 + 20 * beat, beat, 0.2, 0.7)
    lead(x, celesta, [(m + 12 if m else None, d) for m, d in motif], t0 + 36 * beat, beat, -0.2, 0.55)
    put(x, air([midi(62), midi(69)], 16), t0 + 34 * beat, 0, 0.5)
    return master(hall(x, 3.0, 0.3), 3.0, 6.0)


# ------------------------------------------------------------------ духи: таинственно и спокойно, ля минор, петля без барабанов
def spirits():
    beat = 60 / 70
    x = track(46)
    prog = [[45, 52, 59, 60, 64], [41, 48, 55, 57, 59], [40, 47, 55, 59, 62], [38, 45, 53, 57, 60]]  # Am(add9) Fmaj7#11 Em7 Dm9
    t0 = 0.5
    pads(x, prog * 3, t0, beat, 0.5)
    put(x, air([midi(57), midi(64)], 22), 1, 0, 0.45)
    put(x, air([midi(55), midi(62)], 22), 23, 0, 0.45)
    for i, c in enumerate(prog * 3):
        tb = t0 + i * 4 * beat
        put(x, bass(midi(c[0] - 12), 3.6 * beat), tb, 0, 0.7)
        for k, m in enumerate([c[1], c[3], c[4], c[3] + 12]):  # арфа/челеста: медленные переливы
            put(x, B.harp(midi(m)), tb + k * beat, pan=-0.3 + 0.2 * k, gain=0.5)
        put(x, epiano(midi(c[2]), 2.5, 0.6), tb + 2.5 * beat, 0.25, 0.35)
    for i, m in enumerate([76, 79, 81, 84, 83, 79, 76, 74]):
        put(x, celesta(midi(m), 3.0), 6 + i * 4.2, pan=np.sin(i) * 0.6, gain=0.5)
    return master(hall(x, 4.0, 0.34), loop=True)


# ------------------------------------------------------------------ финал: тёплый успех, ре мажор
def finale():
    beat = 60 / 80
    x = track(64)
    hard = [[47, 54, 57, 61, 62], [43, 50, 54, 57, 59], [45, 52, 55, 59, 61], [42, 49, 52, 57, 59]]  # Bm9 Gmaj9 A6 F#m7 — путь
    sweet = [[50, 57, 61, 64, 66], [47, 54, 57, 61, 62], [43, 50, 54, 57, 59], [45, 52, 57, 59, 64]]  # Dmaj9 Bm9 Gmaj9 A6/9
    t0 = 2.0
    pads(x, hard * 2, t0, beat, 0.45)
    comp(x, hard * 2, t0, beat, 0.6, rhythm=(0, 2.5))
    basses(x, [35, 31, 33, 30] * 2, t0, beat)
    groove(x, t0 + 8 * beat * 2, 4, beat, half=True)
    t1 = t0 + 32 * beat
    pads(x, sweet * 3, t1, beat, 0.5)
    comp(x, sweet * 3, t1, beat, 1.0)
    basses(x, [38, 35, 31, 33] * 3, t1, beat)
    groove(x, t1, 12, beat)
    tune = [(74, 1), (76, 1), (78, 2), (81, 1.5), (78, 0.5), (76, 2), (74, 1), (73, 1), (71, 2), (73, 1), (74, 1),
            (76, 3), (None, 1), (78, 1), (81, 1), (83, 2), (81, 1.5), (78, 0.5), (76, 2), (78, 1), (76, 1), (74, 4)]
    lead(x, epiano, tune, t1 + 4 * beat, beat, 0.2, 0.75)
    lead(x, celesta, [(m + 12 if m else None, d) for m, d in tune[12:]], t1 + 20 * beat + 4 * beat, beat, -0.25, 0.5)
    put(x, air([midi(62), midi(66), midi(69)], 18), t1 + 28 * beat, 0, 0.55)
    for i, m in enumerate([74, 78, 81, 86, 81, 86]):
        put(x, B.bell(midi(m), 6), t1 + 44 * beat + 1.0 + i * 1.2, pan=-0.5 + i * 0.2, gain=0.6)
    return master(hall(x, 3.0, 0.3), 3.0, 7.0)


TRACKS = {"lounge_prologue": prologue, "lounge_spirits": spirits, "lounge_finale": finale}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for name in (sys.argv[2:] or list(TRACKS)):
        x = TRACKS[name]()
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, round(len(x) / SR, 1), "с")

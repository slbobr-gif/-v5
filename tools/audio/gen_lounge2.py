"""Лаундж-фэнтези, вторая версия (25.11): по 3 варианта каждой темы. Мелодии и гармонии — свои.

Пролог — с грустью: минор, медленнее, нисходящие «вздохи», виолончель/флейта/голос.
Духи — с мистикой: фригийский лад над гулом, целотонные «плывущие» аккорды, хроматические медианты;
стеклянная гармоника, обратные переливы челесты, скользящие «голоса духов».
Финал — от трудного пути к тёплому мажору, три разных прочтения.
Чисто и тихо: только тоны, мастеринг gen_themes_clean.master (около −27 дБ, мягкие пики).
Запуск: python3 tools/audio/gen_lounge2.py [папка] [имена…]
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_themes_clean as B  # noqa: E402
import gen_lounge as L  # noqa: E402

SR = B.SR
midi, env, put, hall, master, track = B.midi, B.env, B.put, B.hall, B.master, B.track
rng = np.random.default_rng(2511)


# ------------------------------------------------------------------ новые звуки
def glass(f, dur):
    """Стеклянная гармоника: чистый тон с медленным биением, мягкая атака."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.0025 * t) + 0.12 * np.sin(2 * np.pi * 2 * f * t)
    if f * 3 < 8000:
        x += 0.04 * np.sin(2 * np.pi * 3.01 * f * t)
    return x * env(n, min(0.6, dur / 3), min(1.2, dur / 2)) * 0.16


def rev_celesta(f, dur=2.2):
    """Перелив наоборот: звук нарастает и обрывается мягко — «вдох» перед аккордом."""
    y = L.celesta(f, dur)[::-1].copy()
    k = int(0.06 * SR)
    y[-k:] *= np.linspace(1, 0, k)
    return y


def ghost(f1, f2, dur):
    """Голос духа: тихий тон, скользящий от f1 к f2."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = t / dur
    fr = f1 * (f2 / f1) ** (s * s * (3 - 2 * s)) * B.vib(t, 4.5, 0.004, 0.5)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    return x * env(n, dur * 0.3, dur * 0.4) * 0.16


def sad_groove(out, t0, bars, beat, snare=True):
    """Медленный бит: бочка на «раз», мягкий «ток» на «три», тихие тики по четвертям."""
    for b in range(bars):
        tb = t0 + b * 4 * beat
        put(out, L.kick(), tb, 0, 0.8)
        if snare:
            put(out, L.tok(), tb + 2 * beat, 0.1, 0.7)
        for k in range(4):
            put(out, L.tick(), tb + k * beat, 0.35, 0.5)


def chords(x, prog, roots, t0, beat, comp=True, bass=True, pad_gain=0.45, vel=0.8, rhythm=(0, 2.5)):
    L.pads(x, prog, t0, beat, pad_gain)
    if comp:
        L.comp(x, prog, t0, beat, vel, rhythm=rhythm)
    if bass:
        L.basses(x, roots, t0, beat)


def seq(x, inst, notes, t0, pan=0.0, gain=0.5):
    """Ноты в секундах: [(midi|None, сек)]."""
    t = t0
    for m, d in notes:
        if m is not None:
            put(x, inst(midi(m), d * 1.15), t, pan, gain)
        t += d


def tr(notes, k):
    return [(m + k if m else None, d) for m, d in notes]


# ================================================================== ПРОЛОГ — с грустью
def prologue_1():
    """«Прощание»: ре минор, 66 уд/мин, нисходящая мелодия электропиано, виолончель в конце."""
    beat = 60 / 66
    x = track(68)
    prog = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 65], [43, 50, 53, 57, 58], [45, 52, 55, 57, 62]]  # Dm9 Bbmaj7 Gm9 A7sus4
    roots = [38, 34, 31, 33]
    t0 = 2.0
    L.pads(x, prog * 4 + prog[:1], t0, beat, 0.45)
    cel = [[81, 77, 76, 74], [77, 74, 72, 70], [74, 70, 69, 67], [69, 67, 64, 62]]
    for c in range(4):
        for k, m in enumerate(cel[c]):
            put(x, L.celesta(midi(m), 3.0), t0 + c * 4 * beat + k * beat, pan=-0.3 + 0.2 * k, gain=0.5)
    t1 = t0 + 16 * beat
    L.comp(x, prog * 3, t1, beat, 0.7, rhythm=(0, 2.5))
    L.basses(x, roots * 3, t1, beat)
    sad_groove(x, t1, 12, beat)
    mel = [(77, 2), (76, 1), (74, 1), (74, 1.5), (72, 0.5), (70, 2), (70, 1), (69, 1), (67, 2), (69, 3), (None, 1),
           (65, 1), (67, 1), (69, 2), (70, 1.5), (69, 0.5), (67, 2), (65, 1), (64, 1), (62, 2), (64, 4), (62, 4)]
    L.lead(x, L.epiano, mel, t1, beat, 0.2, 0.7)
    put(x, B.choir([midi(62), midi(69)], 30, "o", 4, 5), t1 + 16 * beat, 0, 0.35)
    cello = [(62, 2), (60, 2), (58, 2), (57, 2), (57, 2), (55, 2), (50, 6)]
    L.lead(x, B.cello, cello, t1 + 36 * beat, beat, -0.2, 0.6)
    put(x, L.celesta(midi(74), 4.0), t1 + 48 * beat + beat, 0.3, 0.5)
    return master(hall(x, 3.2, 0.32), 3.0, 7.0)


def prologue_2():
    """«Дождь в окне»: ми минор, 70 уд/мин, флейта поверх тихого бита, хор «о»."""
    beat = 60 / 70
    x = track(64)
    prog = [[40, 47, 50, 54, 55], [36, 48, 52, 55, 59], [45, 52, 55, 59, 60], [47, 54, 57, 62, 66]]  # Em9 Cmaj7 Am9 Bm7
    roots = [40, 36, 33, 35]
    t0 = 2.0
    L.pads(x, prog[:2], t0, beat, 0.4)
    L.comp(x, prog[:2], t0, beat, 0.6, rhythm=(0, 2))
    body = (prog * 5)[2:17]  # такты 2..16
    L.pads(x, body, t0 + 8 * beat, beat, 0.45)
    L.comp(x, body[:-1], t0 + 8 * beat, beat, 0.7)
    L.basses(x, (roots * 5)[2:16], t0 + 8 * beat, beat)
    sad_groove(x, t0 + 16 * beat, 12, beat)
    fl = [(71, 3), (69, 0.5), (67, 0.5), (64, 2), (67, 1), (71, 1), (72, 3), (71, 1), (69, 2), (66, 2),
          (67, 1), (66, 1), (64, 2), (67, 1.5), (71, 0.5), (72, 2), (71, 1), (69, 1), (67, 1), (64, 1), (66, 3), (62, 1), (64, 4)]
    L.lead(x, B.flute, fl, t0 + 16 * beat, beat, 0.15, 0.75)
    L.lead(x, L.celesta, tr(fl[:10], 12), t0 + 48 * beat, beat, -0.25, 0.45)
    put(x, B.choir([midi(59), midi(64)], 26, "o", 4, 5), t0 + 44 * beat, 0, 0.4)
    return master(hall(x, 3.2, 0.32), 3.0, 7.0)


def prologue_3():
    """«Колыбельная дороге»: ля минор, 62 уд/мин, без малого барабана; в конце поёт одинокий голос."""
    beat = 60 / 62
    x = track(62)
    prog = [[45, 52, 55, 59, 60], [41, 48, 52, 57, 60], [38, 45, 48, 52, 53], [40, 47, 50, 52, 57]]  # Am9 Fmaj7 Dm9 E7sus4
    roots = [33, 29, 38, 40]
    t0 = 2.0
    L.pads(x, prog * 3 + prog[:3], t0, beat, 0.5)
    L.comp(x, prog * 3, t0 + 8 * beat, beat, 0.6, rhythm=(0, 2))
    L.basses(x, roots * 3, t0 + 8 * beat, beat)
    sad_groove(x, t0 + 8 * beat, 12, beat, snare=False)
    ph1 = [(76, 2), (72, 1), (71, 1), (72, 2), (69, 2), (69, 1), (65, 1), (64, 1), (62, 1), (64, 4)]
    ph2 = [(76, 1), (77, 1), (76, 1), (72, 1), (74, 2), (72, 2), (69, 2), (65, 2), (64, 2), (62, 2)]
    L.lead(x, L.celesta, ph1, t0 + 8 * beat, beat, -0.2, 0.55)
    L.lead(x, L.epiano, ph1, t0 + 8 * beat, beat, 0.2, 0.55)
    L.lead(x, L.epiano, ph2 + [(69, 4)], t0 + 24 * beat, beat, 0.2, 0.65)
    L.lead(x, lambda f, d: B.voice(f, d, "a", 0.4, 0.8), tr(ph1, -12), t0 + 40 * beat, beat, 0.0, 0.75)
    put(x, L.celesta(midi(69), 4.0), t0 + 57 * beat, 0.3, 0.45)
    return master(hall(x, 3.4, 0.33), 3.0, 7.0)


# ================================================================== ДУХИ — с мистикой (петли без барабанов)
def spirits_1():
    """«Фригийский туман»: гул ми, аккорды Em(add9) ↔ F/E (полутон сверху — тайна), стеклянная мелодия."""
    x = track(46)
    step = 5.5
    put(x, B.drone(midi(40), 46), 0, 0, 0.45)
    chs = [[52, 59, 66, 67], [53, 57, 60, 64]] * 4
    for i, c in enumerate(chs):
        t = 0.3 + i * step
        put(x, L.pad([midi(m) for m in c], step + 2.0, 1.5, 2.0), t, 0, 0.5)
        put(x, rev_celesta(midi(c[-1] + 12)), max(0, t - 2.2 + 0.05), pan=0.4 if i % 2 else -0.4, gain=0.45)
        for k in range(3):
            m = c[int(rng.integers(len(c)))] + 12
            put(x, B.harp(midi(m)), t + 1.4 + k * 1.3, pan=float(rng.uniform(-0.6, 0.6)), gain=0.35)
    mel = [(76, 2.2), (77, 2.2), (79, 3.3), (77, 2.2), (76, 4.4), (None, 2.2), (74, 2.2), (72, 2.2), (71, 3.3), (72, 2.2), (71, 4.4)]
    seq(x, glass, mel, 4.0, 0.15, 0.8)
    put(x, ghost(midi(64), midi(65), 6.0), 13, -0.3, 0.6)
    put(x, ghost(midi(71), midi(72), 6.0), 31, 0.3, 0.6)
    put(x, B.choir([midi(52), midi(59)], 18, "o", 4, 5), 20, 0, 0.45)
    return master(hall(x, 4.5, 0.4), loop=True)


def spirits_2():
    """«Плывущий мир»: целотонные аккорды до ↔ ре, арфа по целотонной гамме, голоса духов скользят."""
    x = track(46)
    step = 5.75
    put(x, L.pad([midi(36), midi(48)], 46, 3, 3), 0, 0, 0.45)
    chs = [[60, 64, 68, 74], [62, 66, 70, 76]] * 4
    wt = [72, 74, 76, 78, 80, 82, 84]
    for i, c in enumerate(chs):
        t = 0.3 + i * step
        put(x, L.pad([midi(m) for m in c], step + 2.0, 1.8, 2.2), t, 0, 0.45)
        put(x, rev_celesta(midi(c[-1] + 12)), max(0, t - 2.2 + 0.05), pan=-0.4 if i % 2 else 0.4, gain=0.4)
        notes = wt if i % 2 == 0 else wt[::-1]
        for k, m in enumerate(notes):
            put(x, B.harp(midi(m - (0 if i % 2 == 0 else 2))), t + 0.8 + k * 0.42, pan=-0.5 + k * 0.16, gain=0.28)
    for t, m in [(3, 84), (14.5, 86), (26, 88), (37.5, 86)]:
        put(x, glass(midi(m), 6.0), t, 0.2, 0.55)
    put(x, ghost(midi(76), midi(78), 7.0), 8, -0.3, 0.6)
    put(x, ghost(midi(80), midi(78), 7.0), 22, 0.3, 0.6)
    put(x, ghost(midi(74), midi(72), 7.0), 35, -0.2, 0.55)
    return master(hall(x, 5.0, 0.42), loop=True)


def spirits_3():
    """«Сияние»: хроматические медианты Em9 → Cmaj7#11 → Abmaj7#11 → B7sus4, колокольчики и стекло."""
    x = track(46)
    step = 5.5
    chs = [[40, 52, 55, 59, 66], [36, 52, 55, 59, 66], [44, 51, 55, 60, 62], [35, 52, 54, 57, 59]] * 2
    for i, c in enumerate(chs):
        t = 0.3 + i * step
        put(x, L.bass(midi(c[0]), step + 0.5), t, 0, 0.7)
        put(x, L.pad([midi(m) for m in c[1:]], step + 2.0, 1.5, 2.0), t, 0, 0.35)
        for k, m in enumerate(c[1:]):
            put(x, glass(midi(m + 12), step + 1.0), t + k * 0.15, pan=-0.4 + 0.25 * k, gain=0.35)
        put(x, rev_celesta(midi(c[2] + 24)), max(0, t - 2.2 + 0.05), pan=0.3, gain=0.4)
        for k, m in enumerate([c[1], c[3], c[4], c[2] + 12]):
            put(x, B.harp(midi(m + 12)), t + 2.0 + k * 0.7, pan=0.5 - 0.3 * k, gain=0.3)
    for t, m in [(4, 88), (10, 83), (21, 87), (27, 86), (38, 83)]:
        put(x, B.bell(midi(m), 5), t, pan=float(rng.uniform(-0.6, 0.6)), gain=0.4)
    put(x, ghost(midi(67), midi(66), 7.0), 9, -0.3, 0.55)
    put(x, ghost(midi(63), midi(64), 7.0), 30, 0.3, 0.55)
    put(x, B.choir([midi(52), midi(59)], 16, "u", 4, 5), 16, 0, 0.4)
    return master(hall(x, 5.0, 0.42), loop=True)


# ================================================================== ФИНАЛ
def finale_1():
    """Прежний финал: си минор → ре мажор, электропиано и колокольчики."""
    return L.finale()


def finale_2():
    """«Дом у моря»: ми минор → соль мажор, 76 уд/мин, флейта, струнные, хор на кульминации."""
    beat = 60 / 76
    x = track(70)
    hard = [[40, 52, 55, 59, 62], [36, 52, 55, 59, 62], [45, 52, 55, 59, 60], [38, 50, 55, 57, 59]]  # Em7 Cmaj9 Am9 D6sus4
    sweet = [[43, 54, 57, 59, 62], [40, 54, 55, 59, 62], [36, 52, 55, 59, 62], [38, 54, 57, 59, 64]]  # Gmaj9 Em9 Cmaj9 D6/9
    t0 = 2.0
    chords(x, hard * 2, [40, 36, 33, 38] * 2, t0, beat, vel=0.6)
    sad_groove(x, t0 + 16 * beat, 4, beat)
    fh = [(71, 2), (74, 2), (72, 3), (71, 1), (69, 2), (67, 1), (64, 1), (67, 4)]
    L.lead(x, B.flute, fh, t0 + 8 * beat, beat, 0.15, 0.65)
    t1 = t0 + 32 * beat
    chords(x, sweet * 3, [43, 40, 36, 38] * 3, t1, beat, vel=0.9, rhythm=(0, 1.5, 2.5))
    L.groove(x, t1, 12, beat)
    for i, c in enumerate(sweet * 2):
        put(x, B.strings([midi(m + 12) for m in c[1:]], 4 * beat + 1.5, 1.5, 1.5), t1 + 16 * beat + i * 4 * beat, 0, 0.35)
    tune = [(74, 1), (78, 1), (79, 2), (78, 1.5), (76, 0.5), (74, 2), (76, 1), (79, 1), (83, 2), (81, 4),
            (79, 1), (78, 1), (74, 2), (76, 2), (71, 2), (72, 1), (74, 1), (76, 2), (78, 2), (76, 2), (79, 4)]
    L.lead(x, B.flute, tune, t1 + 4 * beat, beat, 0.15, 0.8)
    L.lead(x, L.epiano, tr(tune[:10], -12), t1 + 4 * beat, beat, -0.2, 0.4)
    put(x, B.choir([midi(62), midi(67), midi(71)], 16, "a", 4, 5), t1 + 32 * beat, 0, 0.5)
    for i, m in enumerate([79, 83, 86, 91, 86, 91]):
        put(x, B.bell(midi(m - 12), 6), t1 + 44 * beat + 0.5 + i * 1.1, pan=-0.5 + i * 0.2, gain=0.55)
    return master(hall(x, 3.0, 0.3), 3.0, 7.0)


def finale_3():
    """«Рассвет»: ре минор → фа мажор → подъём в соль мажор, электропиано, струнные, колокола."""
    beat = 60 / 72
    x = track(74)
    hard = [[50, 57, 60, 64, 65], [46, 53, 57, 60, 62], [43, 50, 53, 57, 58], [48, 55, 58, 62, 65]]  # Dm9 Bbmaj9 Gm9 C9sus4
    sweet = [[41, 52, 57, 60, 67], [38, 53, 57, 60, 64], [46, 53, 57, 60, 62], [36, 52, 57, 62, 64]]  # Fmaj9 Dm9 Bbmaj9 C6/9
    t0 = 2.0
    L.pads(x, hard * 2, t0, beat, 0.45)
    L.comp(x, hard * 2, t0, beat, 0.55, rhythm=(0,))
    L.basses(x, [38, 34, 31, 36], t0 + 16 * beat, beat)
    sad_groove(x, t0 + 16 * beat, 4, beat, snare=False)
    ph = [(69, 2), (65, 1), (67, 1), (69, 2), (72, 2), (70, 1.5), (69, 0.5), (67, 2), (65, 4)]
    L.lead(x, L.epiano, ph, t0 + 4 * beat, beat, 0.2, 0.6)
    L.lead(x, B.cello, tr(ph, -12), t0 + 20 * beat, beat, -0.2, 0.5)
    t1 = t0 + 32 * beat
    tune = [(72, 1), (74, 1), (76, 2), (77, 1.5), (76, 0.5), (74, 2), (72, 1), (74, 1), (77, 2), (76, 4),
            (81, 2), (79, 1), (77, 1), (76, 2), (74, 2), (77, 1), (76, 1), (74, 2), (72, 4)]
    chords(x, sweet, [41, 38, 34, 36], t1, beat, vel=0.85, rhythm=(0, 1.5, 2.5))
    L.groove(x, t1, 4, beat)
    L.lead(x, L.epiano, tune[:10], t1, beat, 0.2, 0.75)
    t2 = t1 + 16 * beat  # подъём на тон — «рассвет»
    up = [[m + 2 for m in c] for c in sweet]
    chords(x, up * 2, [43, 40, 36, 38] * 2, t2, beat, vel=0.95, rhythm=(0, 1.5, 2.5))
    L.groove(x, t2, 8, beat)
    for i, c in enumerate(up * 2):
        put(x, B.strings([midi(m + 12) for m in c[1:]], 4 * beat + 1.5, 1.5, 1.5), t2 + i * 4 * beat, 0, 0.3)
    L.lead(x, L.epiano, tr(tune, 2), t2, beat, 0.2, 0.8)
    L.lead(x, L.celesta, tr(tune[10:], 14), t2 + 16 * beat, beat, -0.25, 0.45)
    put(x, B.choir([midi(62), midi(67), midi(71)], 14, "a", 4, 5), t2 + 20 * beat, 0, 0.5)
    for i, m in enumerate([79, 83, 86, 91, 86]):
        put(x, B.bell(midi(m - 12), 6), t2 + 32 * beat + 0.3 + i * 1.2, pan=-0.5 + i * 0.25, gain=0.55)
    return master(hall(x, 3.0, 0.3), 3.0, 7.0)


TRACKS = {f"lounge2_{k}": v for k, v in {
    "prologue_1": prologue_1, "prologue_2": prologue_2, "prologue_3": prologue_3,
    "spirits_1": spirits_1, "spirits_2": spirits_2, "spirits_3": spirits_3,
    "finale_1": finale_1, "finale_2": finale_2, "finale_3": finale_3}.items()}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for name in (sys.argv[2:] or list(TRACKS)):
        x = TRACKS[name]()
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, round(len(x) / SR, 1), "с")

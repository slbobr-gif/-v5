"""Звуки населённых мест с нуля (27.11): город ×3, рынок ×3, посёлок ×3. Ни одной чужой записи.

Как устроено (тот же подход, что в gen_ambience.py — стерео, 40 с, бесшовные петли):
- машина: шины (розовый шум, высокие частоты только вблизи) + мотор (гармоники с эффектом Доплера),
  громкость по закону расстояния, проезд слева направо или наоборот;
- голоса: синтетическая речь без слов — пилообразный «голос» с мелодикой фразы, гласные через форманты,
  слоги ~5 в секунду, согласные — короткие шумовые всплески; десятки голосов дают гул толпы,
  а разобрать в нём слова невозможно, потому что их там нет;
- стройка, трамвай, звон, шорох пакетов, монеты, шаги, воробьи, голуби, вороны, чайки, собака — банки
  с вариантами, у каждого события своя громкость и место в стерео.
Запуск: python3 tools/audio/gen_ambience_town.py [папка] [имена…] → city_1..3, market_1..3, village_1..3 (.wav)
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_ambience as A  # noqa: E402

SR, N = A.SR, A.N
rng = np.random.default_rng(2711)
filt, pink, brown, lfo, norm01, reverb = A.filt, A.pink, A.brown, A.lfo, A.norm01, A.reverb


def st():
    return np.zeros((N, 2))


def pan_gains(p):
    p = np.clip(p, -1, 1)
    return np.sqrt((1 - p) / 2), np.sqrt((1 + p) / 2)


def place(out, sig, t, pan=0.0, gain=1.0):
    """Положить моно- или стереосигнал; хвост, вышедший за конец, заворачивается в начало (петля)."""
    i = int(t * SR) % N
    if sig.ndim == 1:
        l, r = pan_gains(pan)
        sig = np.stack([sig * l, sig * r], axis=1)
    sig = sig * gain
    n = len(sig)
    end = min(N, i + n)
    out[i:end] += sig[: end - i]
    if i + n > N:
        rest = sig[end - i:][: N]
        out[: len(rest)] += rest


def far(x, cutoff):
    """Отдалить: срезать верх."""
    if x.ndim == 1:
        return filt(x, "low", cutoff)
    return np.stack([filt(x[:, c], "low", cutoff) for c in range(2)], axis=1)


def echo(x, delay=0.22, gain=0.25):
    d = int(delay * SR)
    y = x.copy()
    y[d:] += x[:-d] * gain
    return y


def saw(f_t):
    ph = np.cumsum(f_t) / SR
    return 2 * (ph % 1.0) - 1


# ------------------------------------------------------------------ транспорт
def passby(dur, f_engine=35.0, speed=1.0, tyre=1.0, direction=1, truck=False):
    n = int(dur * SR)
    t = np.arange(n) / SR
    c, w = dur / 2, dur / 5 / speed
    near = 1 / (1 + ((t - c) / w) ** 2)
    noise = pink(n)
    lo = filt(noise, "low", 600)
    hi = filt(noise, "band", [600, 4500])
    tyres = norm01(lo) * near ** 1.1 + norm01(hi) * near ** 2.2 * 0.6
    dop = 1 + 0.035 * speed * np.tanh(-(t - c) / (w * 0.6))
    eng = filt(saw(f_engine * dop * (1 + 0.02 * lfo(n, 2, 2))), "low", 380 if truck else 520)
    x = tyres * tyre + norm01(eng) * near ** 1.4 * (0.9 if truck else 0.45)
    x *= np.minimum(1, np.minimum(t, dur - t) / 0.5)
    p = np.tanh((t - c) / w * 0.8) * direction
    l, r = pan_gains(p * 0.9)
    return np.stack([x * l, x * r], axis=1)


def traffic(out, per_min, gain=1.0, trucks=0.15, speed=(0.8, 1.3), cutoff=None):
    count = max(1, int(per_min * N / SR / 60))
    for _ in range(count):
        truck = rng.random() < trucks
        dur = rng.uniform(5, 9) if not truck else rng.uniform(7, 11)
        x = passby(dur, rng.uniform(18, 26) if truck else rng.uniform(28, 48), rng.uniform(*speed),
                   1.0, 1 if rng.random() < 0.5 else -1, truck)
        if cutoff:
            x = far(x, cutoff)
        place(out, x, rng.uniform(0, N / SR), 0, gain * rng.lognormal(0, 0.2) * (1.2 if truck else 1.0))


def traffic_bed(level_hz=220):
    def ch():
        hum = filt(brown(N), "low", level_hz) * (0.7 + 0.3 * lfo(N, 0.08, 3))
        swish = filt(pink(N), "band", [250, 1600]) * (0.6 + 0.4 * lfo(N, 0.15, 3))
        return norm01(hum) + norm01(swish) * 0.35
    return A.stereo(ch)


def horn(f=420.0):
    n = int(rng.uniform(0.25, 0.45) * SR)
    t = np.arange(n) / SR
    x = saw(np.full(n, f)) + saw(np.full(n, f * 1.25)) * 0.8
    x = filt(x, "low", 1200) * np.minimum(1, np.minimum(t, t[-1] - t) / 0.04)
    return x


def tram(dur=12.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    c, w = dur / 2, dur / 5
    near = 1 / (1 + ((t - c) / w) ** 2)
    body = norm01(filt(brown(n), "low", 160)) * near
    hum = norm01(filt(saw(np.full(n, 100.0) * (1 + 0.01 * np.tanh(-(t - c)))), "low", 400)) * near ** 1.5 * 0.25
    clack = np.zeros(n)  # стыки рельсов: двойной стук тележек
    period = 0.9
    for k in np.arange(0.3, dur, period):
        for off in (0.0, 0.11):
            i = int((k + off) * SR)
            if i < n - 2000:
                tk = np.arange(2000) / SR
                clack[i:i + 2000] += np.sin(2 * np.pi * 160 * tk) * np.exp(-tk * 60)
    x = body + hum + filt(clack, "low", 1500) * near ** 1.5 * 0.5
    p = np.tanh((t - c) / w)
    l, r = pan_gains(p * 0.8)
    return np.stack([x * l, x * r], axis=1)


def bell_ding(f=1250.0):
    t = np.arange(int(1.4 * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d) for m, a, d in [(1, 1, 3.5), (2.0, 0.4, 5), (2.9, 0.25, 7)])
    x[:300] *= np.linspace(0, 1, 300)
    return x * 0.5


# ------------------------------------------------------------------ голоса без слов
VOWELS = [(750, 1200), (500, 900), (350, 750), (520, 1800), (300, 2250), (650, 1500)]


def voice(n, f0, density=0.6, call=False, female=False):
    """Речь без слов: фразы, слоги, гласные через форманты, согласные — шумовые всплески."""
    t_env = np.zeros(n)
    f_t = np.full(n, f0)
    vowel_idx = np.zeros(n, dtype=int)
    cons = np.zeros(n)
    t = rng.uniform(0, 2.0)
    while t < n / SR - 0.5:
        plen = rng.uniform(1.0, 1.8) if call else rng.uniform(0.8, 3.0)
        a, b = int(t * SR), min(n, int((t + plen) * SR))
        tt = np.linspace(0, 1, b - a)
        base = f0 * rng.uniform(0.9, 1.12)
        if call:
            contour = base * 1.35 * (1 + 0.25 * np.sin(np.pi * tt))
        else:
            contour = base * (1.08 - 0.18 * tt + 0.07 * np.sin(2 * np.pi * tt * rng.uniform(0.6, 1.6)))
        f_t[a:b] = contour
        s = a  # слоги
        while s < b:
            sl = int(rng.uniform(0.35, 0.6) * SR) if call else int(rng.uniform(0.12, 0.26) * SR)
            e = min(b, s + sl)
            k = e - s
            if k > 400:
                ramp = np.minimum(1, np.minimum(np.arange(k), k - np.arange(k)) / (0.03 * SR))
                t_env[s:e] = np.maximum(t_env[s:e], ramp * rng.uniform(0.6, 1.0))
                vowel_idx[s:e] = rng.integers(len(VOWELS))
                if rng.random() < 0.45 and not call:
                    cl = min(int(0.05 * SR), k)
                    cons[s:s + cl] += np.hanning(cl) * rng.uniform(0.2, 0.5)
            s = e + int(rng.uniform(0.01, 0.05) * SR)
        t += plen + (rng.uniform(1.5, 4.0) if call else rng.uniform(0.3, 2.5) / max(density, 0.1))
    f_t *= 1 + 0.01 * np.sin(2 * np.pi * 5.5 * np.arange(n) / SR)
    # источник как у живого голоса: спад −12 дБ/окт (пила −6 и ещё −6), верх срезан круто — без «жужжания»
    src = filt(filt(saw(f_t), "low", 3400, 8), "low", 700, 1)
    y = np.zeros(n)
    k = int(0.02 * SR)
    for vi, (f1, f2) in enumerate(VOWELS):
        mask = (vowel_idx == vi).astype(float)
        if mask.sum() == 0:
            continue
        mask = np.convolve(mask, np.ones(k) / k, mode="same")
        sc = 1.18 if female else 1.0
        v = filt(src, "band", [f1 * sc * 0.85, f1 * sc * 1.15]) + 0.6 * filt(src, "band", [f2 * sc * 0.9, f2 * sc * 1.1])
        y += v * mask
    noise = filt(rng.standard_normal(n), "band", [2500, 6500]) * cons
    return norm01(y * t_env) + norm01(noise) * 0.12


def crowd(voices, cutoff=3000, density=0.6, spread=0.9):
    out = st()
    for _ in range(voices):
        fem = rng.random() < 0.5
        f0 = rng.uniform(170, 250) if fem else rng.uniform(95, 150)
        v = voice(N, f0, density, False, fem)
        place(out, filt(v, "low", cutoff * rng.uniform(0.7, 1.1), 4), 0, rng.uniform(-spread, spread), rng.lognormal(0, 0.4))
    return out


def callers(count, cutoff=3500):
    out = st()
    for _ in range(count):
        fem = rng.random() < 0.5
        v = voice(N, rng.uniform(200, 260) if fem else rng.uniform(120, 160), 0.3, True, fem)
        place(out, filt(v, "low", cutoff, 4), 0, rng.uniform(-0.8, 0.8), rng.uniform(0.7, 1.0))
    return out


# ------------------------------------------------------------------ банки мелких событий
def clink_bank(k=40):
    bank = []
    for _ in range(k):
        f = rng.uniform(1500, 3600)
        t = np.arange(int(0.25 * SR)) / SR
        d = rng.uniform(18, 40)
        x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d * m ** 0.5) for m, a in [(1, 1), (2.76, 0.4), (5.4, 0.15)] if f * m < 12000)
        x[:60] *= np.linspace(0, 1, 60)
        bank.append(x * 0.5)
    return bank


def rustle_bank(k=30):
    bank = []
    for _ in range(k):
        n = int(rng.uniform(0.15, 0.5) * SR)
        x = filt(rng.standard_normal(n), "band", [1500, 7000]) * (0.5 + 0.5 * np.abs(filt(rng.standard_normal(n), "low", 30)))
        bank.append(norm01(x) * np.hanning(n) * 0.3)
    return bank


def step_bank(k=24):
    bank = []
    for _ in range(k):
        n = int(0.06 * SR)
        t = np.arange(n) / SR
        x = filt(rng.standard_normal(n), "band", [200, 1400]) * np.exp(-t * 90) + np.sin(2 * np.pi * rng.uniform(70, 110) * t) * np.exp(-t * 60) * 0.6
        x[:130] *= np.linspace(0, 1, 130)  # 3 мс — без щелчка
        bank.append(norm01(x) * 0.4)
    return bank


def steps(rate=6.0, cutoff=1500):
    x = A.stereo(lambda: A.scatter(N, rate / 2, step_bank(), 0.5))
    return np.stack([filt(x[:, c], "low", cutoff, 6) for c in range(2)], axis=1)


def clank():
    """Удар молотка по металлу на стройке."""
    f = rng.uniform(380, 900)
    t = np.arange(int(0.6 * SR)) / SR
    d = rng.uniform(5, 12)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d * m ** 0.4) for m, a in [(1, 1), (2.4, 0.6), (3.9, 0.35), (6.1, 0.15)])
    x[:200] = x[:200] * np.linspace(0, 1, 200) + filt(rng.standard_normal(200), "band", [1500, 4000]) * np.hanning(200) * 0.15
    return x * 0.4


def thump():
    t = np.arange(int(0.5 * SR)) / SR
    x = np.sin(2 * np.pi * (45 + 30 * np.exp(-t * 20)) * t) * np.exp(-t * 9) + filt(rng.standard_normal(len(t)), "low", 400) * np.exp(-t * 30) * 0.3
    return x * 0.6


def drill(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = filt(rng.standard_normal(n), "band", [500, 1400]) * (0.6 + 0.4 * np.sin(2 * np.pi * 28 * t))
    x += 0.3 * filt(saw(np.full(n, 210.0)), "low", 900)
    return norm01(x) * np.minimum(1, np.minimum(t, dur - t) / 0.3)


def chirp_seq():
    """Воробей: «чик-чирик» — серия коротких частотных взмахов."""
    parts = []
    for _ in range(rng.integers(2, 6)):
        n = int(rng.uniform(0.03, 0.08) * SR)
        tt = np.linspace(0, 1, n)
        f = rng.uniform(3200, 5200) * (1 + rng.uniform(-0.3, 0.3) * tt)
        parts.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt) ** 2)
        parts.append(np.zeros(int(rng.uniform(0.04, 0.12) * SR)))
    return np.concatenate(parts) * 0.25


def coo():
    """Голубь: «гу-ру-ру»."""
    n = int(rng.uniform(0.7, 1.1) * SR)
    t = np.arange(n) / SR
    f = rng.uniform(330, 420) * (1 + 0.08 * np.sin(2 * np.pi * 1.2 * t)) * (1 + 0.012 * np.sin(2 * np.pi * 22 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    am = (0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t - np.pi / 2)) ** 1.5
    return x * am * np.hanning(n) * 0.25


def caw():
    parts = []
    for _ in range(rng.integers(2, 4)):
        n = int(rng.uniform(0.22, 0.32) * SR)
        tt = np.linspace(0, 1, n)
        f = rng.uniform(320, 420) * (1 - 0.15 * tt)
        x = filt(saw(f), "band", [700, 2200]) + 0.3 * filt(rng.standard_normal(n), "band", [900, 2500])
        parts.append(norm01(x) * np.sin(np.pi * tt) ** 0.7)
        parts.append(np.zeros(int(rng.uniform(0.25, 0.45) * SR)))
    return np.concatenate(parts) * 0.3


def gull():
    parts = []
    for i in range(rng.integers(3, 7)):
        n = int(rng.uniform(0.18, 0.3) * SR)
        tt = np.linspace(0, 1, n)
        f = rng.uniform(1100, 1500) * (1 - 0.35 * tt ** 0.7)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * (1 + 0.3 * np.sin(2 * np.pi * 55 * tt * n / SR))
        parts.append(x * np.sin(np.pi * tt) ** 0.8)
        parts.append(np.zeros(int(rng.uniform(0.08, 0.2) * SR)))
    return np.concatenate(parts) * 0.22


def bark():
    parts = []
    for _ in range(rng.integers(1, 4)):
        n = int(rng.uniform(0.12, 0.2) * SR)
        tt = np.linspace(0, 1, n)
        f = rng.uniform(280, 420) * (1 + 0.3 * np.sin(np.pi * tt))
        x = filt(saw(f), "band", [500, 1800]) + 0.5 * filt(rng.standard_normal(n), "band", [600, 2000])
        parts.append(norm01(x) * np.sin(np.pi * tt) ** 0.5)
        parts.append(np.zeros(int(rng.uniform(0.2, 0.4) * SR)))
    return np.concatenate(parts) * 0.35


def scatter_events(out, maker, count, gain, cutoff=None, pan=0.8, verb=None):
    for _ in range(count):
        x = maker()
        if cutoff:
            x = filt(x, "low", cutoff)
        place(out, x, rng.uniform(0, N / SR), rng.uniform(-pan, pan), gain * rng.lognormal(0, 0.3))


def light_wind(level=1.0):
    def ch():
        g = 0.4 + 0.6 * lfo(N, 0.1, 4)
        return norm01(filt(filt(pink(N), "high", 80), "low", 900) * g)
    return A.stereo(ch) * level


def boat(f=38.0):
    t = np.arange(N) / SR
    x = filt(saw(np.full(N, f) * (1 + 0.01 * lfo(N, 0.2))), "low", 260) * (0.75 + 0.25 * np.sin(2 * np.pi * 6.5 * t))
    return np.stack([x, x * 0.8], axis=1) * (0.5 + 0.5 * lfo(N, 0.05, 3))[:, None]


def active_rms(x):
    """Громкость «пока звучит»: RMS только по участкам, где сигнал есть (окна по 50 мс)."""
    m = np.abs(x).mean(axis=1) if x.ndim == 2 else np.abs(x)
    w = int(0.05 * SR)
    k = len(m) // w
    r = np.sqrt((m[: k * w].reshape(k, w) ** 2).mean(1))
    act = r[r > 0.1 * r.max()]
    return np.sqrt(np.mean(act ** 2)) + 1e-9


def mix(*parts):
    """Вес = громкость звука, пока он звучит: гул 1.0, редкий гудок 0.1 — и гудок не выпрыгивает."""
    out = st()
    for x, g in parts:
        out += x / active_rms(x) * g
    return out


# ================================================================== ГОРОД
def city_1():
    """Проспект: плотный поток, тротуар с людьми, голуби, редкий далёкий гудок."""
    cars = st()
    traffic(cars, 44, 1.0, 0.2)
    honks = st()
    for _ in range(2):
        place(honks, reverb(np.stack([horn(rng.uniform(380, 460))] * 2, axis=1), 1.4, 0.5), rng.uniform(0, 40), 0, 1.0)
    pig = st()
    scatter_events(pig, coo, 5, 1.0, 3000)
    x = mix((traffic_bed(), 0.7), (cars, 0.75), (crowd(14, 2600, 0.5), 0.35), (steps(7), 0.06), (far(honks, 1500), 0.1), (pig, 0.1))
    return echo(reverb(x, 1.1, 0.16), 0.18, 0.12)


def city_2():
    """Стройка рядом: удары по металлу, сваебой вдали, редкая дрель, поток машин за забором."""
    cars = st()
    traffic(cars, 16, 1.0, 0.3, cutoff=3500)
    site = st()
    t = 0.5
    while t < 40:  # серии ударов молотка
        for k in range(rng.integers(3, 9)):
            place(site, clank(), t + k * rng.uniform(0.38, 0.55), rng.uniform(-0.3, 0.1), rng.uniform(0.6, 1.0))
        t += rng.uniform(4, 8)
    piles = st()
    t0 = rng.uniform(5, 12)
    for k in range(9):
        place(piles, thump(), t0 + k * 1.45, 0.5, 1.0)
    dr = st()
    for _ in range(2):
        place(dr, drill(rng.uniform(2, 3.5)), rng.uniform(0, 36), -0.5, 1.0)
    workers = crowd(4, 2200, 0.35, 0.5)
    x = mix((traffic_bed(180), 0.5), (cars, 0.5), (far(echo(site, 0.25, 0.3), 4000), 0.3), (far(piles, 900), 0.3),
            (far(dr, 1800), 0.12), (workers, 0.2), (light_wind(), 0.1))
    return reverb(x, 1.0, 0.18)


def city_3():
    """Вечерний центр: трамвай со звонком, разговоры за столиками кафе, звон посуды, машины подальше."""
    cars = st()
    traffic(cars, 14, 1.0, 0.05, cutoff=2500)
    tr = st()
    tt = rng.uniform(6, 14)
    place(tr, tram(13.0), tt, 0, 1.0)
    ding = st()
    for k in range(2):
        place(ding, bell_ding(), tt + 4.5 + k * 0.32, -0.2, 1.0)
    cafe = crowd(9, 3200, 0.7, 0.7)
    cl = A.stereo(lambda: A.scatter(N, 0.6, clink_bank(), 0.6))
    x = mix((traffic_bed(160), 0.35), (cars, 0.4), (tr, 0.55), (ding, 0.15), (cafe, 0.5), (far(cl, 6000), 0.1), (steps(4), 0.05))
    return reverb(x, 1.2, 0.18)


# ================================================================== РЫНОК
def market_1():
    """Крытый рынок: плотный гул под крышей, зазывалы, звон, шорох пакетов, монеты."""
    cl = A.stereo(lambda: A.scatter(N, 1.2, clink_bank(), 0.6))
    rs = A.stereo(lambda: A.scatter(N, 1.0, rustle_bank(), 0.5))
    x = mix((crowd(26, 3000, 0.75), 1.0), (callers(4), 0.45), (far(cl, 6000), 0.14), (rs, 0.1), (steps(5), 0.06))
    return echo(reverb(x, 1.9, 0.32), 0.12, 0.15)


def market_2():
    """Уличный базар: шумно и живо на открытом воздухе, телеги, голуби, машины в стороне."""
    cars = st()
    traffic(cars, 8, 1.0, 0.2, cutoff=2200)
    carts = st()
    for _ in range(3):
        n = int(rng.uniform(3, 5) * SR)
        x = filt(brown(n), "low", 300) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 3.5 * np.arange(n) / SR))) * np.hanning(n)
        place(carts, x, rng.uniform(0, 38), rng.uniform(-0.6, 0.6), 1.0)
    pig = st()
    scatter_events(pig, coo, 4, 1.0, 3000)
    rs = A.stereo(lambda: A.scatter(N, 0.8, rustle_bank(), 0.5))
    x = mix((crowd(22, 3200, 0.7), 1.0), (callers(5), 0.5), (cars, 0.25), (traffic_bed(150), 0.12), (carts, 0.15), (pig, 0.12), (rs, 0.09),
            (steps(5), 0.06))
    return reverb(x, 0.9, 0.15)


def market_3():
    """Северный рынок у пристани: голоса реже, чайки, мотор катера вдали, море."""
    gl = st()
    scatter_events(gl, gull, 5, 1.0, 4500, 0.9)
    thuds = st()
    for _ in range(6):
        t = np.arange(int(0.25 * SR)) / SR
        x = filt(rng.standard_normal(len(t)), "low", 500) * np.exp(-t * 25) + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 30) * 0.5
        place(thuds, x, rng.uniform(0, 40), rng.uniform(-0.5, 0.5), 1.0)
    sea = A.waves()
    x = mix((crowd(12, 2800, 0.6), 1.0), (callers(3), 0.45), (gl, 0.28), (boat(), 0.12), (sea, 0.35), (thuds, 0.12), (light_wind(), 0.15))
    return reverb(x, 1.0, 0.15)


# ================================================================== ПОСЁЛОК
def village_1():
    """Деревня днём: воробьи, вороны, собака вдали, кто-то стучит молотком, редкая машина."""
    cars = st()
    traffic(cars, 2.5, 1.0, 0.0, speed=(0.6, 0.9), cutoff=3000)
    birds = st()
    scatter_events(birds, chirp_seq, 22, 1.0, 7000, 0.9)
    crows = st()
    scatter_events(crows, caw, 3, 1.0, 3500)
    dog = st()
    scatter_events(dog, bark, 2, 1.0, 2200, 0.9)
    ham = st()
    t = rng.uniform(4, 10)
    for _ in range(3):
        for k in range(rng.integers(3, 6)):
            place(ham, filt(clank(), "low", 2000) * 0.7, t + k * 0.6, 0.6, 1.0)
        t += rng.uniform(8, 13)
    x = mix((light_wind(), 0.35), (birds, 0.3), (crows, 0.18), (dog, 0.14), (ham, 0.12), (cars, 0.28), (crowd(2, 2000, 0.25, 0.6), 0.08))
    return reverb(x, 0.8, 0.14)


def village_2():
    """Посёлок у трассы: изредка грузовики вдали, мопед, соседи разговаривают, воробьи, калитка."""
    cars = st()
    traffic(cars, 5, 1.0, 0.45, speed=(0.7, 1.0), cutoff=2000)
    moped = st()
    n_dur = 8.0
    m = passby(n_dur, 95.0, 0.8, 0.3, 1, False)
    place(moped, far(m, 2500), rng.uniform(10, 25), 0, 1.0)
    birds = st()
    scatter_events(birds, chirp_seq, 14, 1.0, 7000)
    gate = st()
    n = int(0.9 * SR)
    tt = np.linspace(0, 1, n)
    creak = filt(saw(600 + 250 * tt + 40 * np.sin(2 * np.pi * 9 * tt)), "band", [700, 2500]) * np.sin(np.pi * tt)
    place(gate, norm01(creak) * 0.5, rng.uniform(5, 35), 0.4, 1.0)
    x = mix((light_wind(), 0.3), (cars, 0.35), (traffic_bed(120), 0.1), (moped, 0.22), (birds, 0.26), (crowd(3, 2400, 0.45, 0.5), 0.16),
            (gate, 0.07), (steps(1.5), 0.04))
    return reverb(x, 0.8, 0.14)


def village_3():
    """Северный посёлок: ветер, чайки, далёкий мотор лодки, одна машина за всё время, собака, море за домами."""
    cars = st()
    place(cars, far(passby(9.0, 30.0, 0.7, 0.8, -1, False), 2500), rng.uniform(8, 25), 0, 1.0)
    gl = st()
    scatter_events(gl, gull, 4, 1.0, 4000)
    dog = st()
    scatter_events(dog, bark, 2, 1.0, 2000)
    sea = far(A.waves(), 1200)
    x = mix((light_wind(), 0.45), (sea, 0.3), (gl, 0.2), (boat(30.0), 0.06), (cars, 0.22), (dog, 0.12))
    return reverb(x, 0.9, 0.12)


TRACKS = {"city_1": city_1, "city_2": city_2, "city_3": city_3, "market_1": market_1, "market_2": market_2, "market_3": market_3,
          "village_1": village_1, "village_2": village_2, "village_3": village_3}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for name in (sys.argv[2:] or list(TRACKS)):
        x = A.master(A.loop(TRACKS[name]()), -22.0)
        wavfile.write(str(out / f"{name}.wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        print("ok", name, flush=True)

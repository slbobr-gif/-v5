"""Звуки природы с нуля (25.11), v2: стерео, 40 с, бесшовные петли. Права — полностью наши: ни одной чужой записи.

Принципы реализма:
- никаких одинаковых событий: каждая капля/пузырёк/щелчок — из банка в 96 вариантов, со случайной громкостью
  (логнормально) и случайным местом в стерео;
- мелких событий тысячи в секунду, и они тонут в «подложке» — так слух собирает их в шум воды, а не в щелчки;
- у пузырька физика Миннарта: затухающий синус, частота чуть растёт к концу;
- общая лёгкая реверберация (короткий хвост) — звук в пространстве, а не в наушнике.
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
D = 40
N = SR * D
rng = np.random.default_rng(2611)


def filt(x, kind, f, o=2):
    return sosfilt(butter(o, f, kind, fs=SR, output="sos"), x)


def pink(n):
    w = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    return np.fft.irfft(w / np.sqrt(f), n)


def brown(n):
    w = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    return np.fft.irfft(w / f, n)


def lfo(n, rate, smooth=3):
    """Медленная случайная кривая 0..1 (сглаженный шум с частотой ~rate Гц)."""
    k = max(4, int(n * rate / SR) + 4)
    pts = rng.random(k)
    for _ in range(smooth):
        pts = np.convolve(pts, [0.25, 0.5, 0.25], mode="same")
    pts = (pts - pts.min()) / (np.ptp(pts) + 1e-9)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)


def norm01(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def scatter(n, rate_per_s, bank, amp_sigma=0.8, density_env=None):
    """Разбросать события из банка: пуассоновский поток, логнормальная громкость, свой вариант на каждое."""
    out = np.zeros(n + max(len(k) for k in bank))
    count = int(rate_per_s * n / SR)
    pos = np.sort(rng.integers(0, n, count))
    if density_env is not None:  # прореживание по огибающей
        keep = rng.random(count) < density_env[pos]
        pos = pos[keep]
    amps = rng.lognormal(0, amp_sigma, len(pos))
    amps /= np.percentile(amps, 99)
    which = rng.integers(0, len(bank), len(pos))
    for b in range(len(bank)):
        sel = which == b
        if not sel.any():
            continue
        imp = np.zeros(n)
        np.add.at(imp, pos[sel], amps[sel])
        out[: n + len(bank[b]) - 1] += fftconvolve(imp, bank[b])
    return out[:n]


def stereo(fn):
    """Два канала: половина событий общая (центр), половина — свои у каждого уха."""
    common = fn()
    return np.stack([common + fn(), common + fn()], axis=1) * 0.5


def reverb(x, secs=0.9, wet=0.18):
    L = int(secs * SR)
    t = np.arange(L) / SR
    out = np.empty_like(x)
    for ch in range(x.shape[1]):
        ir = rng.standard_normal(L) * np.exp(-t * 6.0 / secs)
        ir = filt(ir, "low", 5000)
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = x[:, ch] * (1 - wet) + fftconvolve(x[:, ch], ir)[: len(x)] * wet * 1.6
    return out


def loop(x, fade=4.0):
    f = int(fade * SR)
    w = np.linspace(0, 1, f)[:, None]
    y = x[:-f].copy()
    y[:f] = x[:f] * w + x[-f:] * (1 - w)
    return y


def master(x, rms_db=-21.0):
    x = x - x.mean(axis=0)
    rms = np.sqrt(np.mean(x ** 2))
    peak = np.percentile(np.abs(x), 99.95)
    x = x * min(10 ** (rms_db / 20) / (rms + 1e-12), 0.85 / (peak + 1e-12))  # редкие щелчки не давим лимитером
    return np.tanh(x * 1.2) / 1.2  # мягкий лимитер вместо жёсткого среза


def save(name, x):
    x = master(loop(x))
    wavfile.write(name + ".wav", SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


# ------------------------------------------------------------------ банки событий
def drop_bank(n_var, f_lo, f_hi, dur_ms, noise_mix):
    """Капля: короткий шумовой удар + затухающий тон, у каждой свой тон, длина и окраска."""
    bank = []
    for _ in range(n_var):
        L = int(SR * rng.uniform(*dur_ms) / 1000)
        t = np.arange(L) / SR
        f0 = rng.uniform(f_lo, f_hi)
        tau = L / SR / rng.uniform(3, 6)
        tone = np.sin(2 * np.pi * f0 * t * (1 + rng.uniform(0, 0.15) * t / t[-1])) * np.exp(-t / tau)
        nz = filt(rng.standard_normal(L), "band", [f0 * 0.7, min(f0 * 2.5, 18000)]) * np.exp(-t / (tau * 0.4))
        k = tone * (1 - noise_mix) + norm01(nz) * noise_mix
        k[: min(20, L)] *= np.linspace(0, 1, min(20, L))  # мягкая атака — без цифрового щелчка
        bank.append(k / (np.max(np.abs(k)) + 1e-9))
    return bank


def bubble_bank(n_var, f_lo, f_hi):
    """Пузырёк по Миннарту: синус с затуханием, частота растёт к концу на 10–40 %."""
    bank = []
    for _ in range(n_var):
        f0 = rng.uniform(f_lo, f_hi)
        tau = rng.uniform(0.004, 0.02) * (900 / f0) ** 0.5
        L = int(SR * tau * 6)
        t = np.arange(L) / SR
        f = f0 * (1 + rng.uniform(0.1, 0.4) * t / t[-1])
        k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)
        k[: min(30, L)] *= np.linspace(0, 1, min(30, L))
        bank.append(k)
    return bank


def pop_bank(n_var):
    """Щелчок полена: 1–5 микро-хлопков за 2–25 мс, каждый — отфильтрованный шум своей окраски."""
    bank = []
    for _ in range(n_var):
        L = int(SR * 0.04)
        k = np.zeros(L)
        for _ in range(rng.integers(1, 6)):
            s = rng.integers(0, int(SR * 0.025))
            m = int(SR * rng.uniform(0.0003, 0.002))
            fc = rng.uniform(1200, 7000)
            burst = filt(rng.standard_normal(m + 64), "band", [fc * 0.6, min(fc * 1.8, 19000)])[:m]
            burst *= np.exp(-np.linspace(0, 5, m)) * rng.lognormal(0, 0.5)
            k[s:s + m] += burst[: max(0, min(m, L - s))]
        bank.append(k / (np.max(np.abs(k)) + 1e-9))
    return bank


# ------------------------------------------------------------------ дождь
def rain():
    def ch():
        inten = 0.75 + 0.25 * lfo(N, 0.05)
        bed = filt(filt(pink(N), "high", 500), "low", 9000) * inten
        fine = scatter(N, 2500, drop_bank(96, 3000, 9000, (1, 3), 0.85), 0.6, inten)
        leaf = scatter(N, 35, drop_bank(96, 900, 2600, (8, 25), 0.55), 0.9, inten)
        heavy = scatter(N, 1.2, drop_bank(48, 350, 800, (25, 60), 0.4), 0.6)
        return norm01(bed) * 1.0 + norm01(fine) * 0.35 + norm01(leaf) * 0.18 + norm01(heavy) * 0.12
    return reverb(stereo(ch), 0.7, 0.15)


# ------------------------------------------------------------------ ручей
def stream():
    def ch():
        flutter = 0.6 + 0.4 * lfo(N, 2.0, 1)
        bed = filt(filt(pink(N) * 0.6 + brown(N) * 0.4, "high", 120), "low", 3500) * flutter
        bubbles = scatter(N, 220, bubble_bank(96, 500, 2400), 0.7)
        gurgle = scatter(N, 12, bubble_bank(48, 180, 450), 0.6)
        splash = scatter(N, 60, drop_bank(64, 2000, 7000, (2, 6), 0.9), 0.7)
        return norm01(bed) * 1.0 + norm01(bubbles) * 0.22 + norm01(gurgle) * 0.18 + norm01(splash) * 0.1
    return reverb(stereo(ch), 0.8, 0.2)


# ------------------------------------------------------------------ ветер
def wind():
    gust = lfo(N, 0.12, 4) ** 1.5
    def ch():
        g = 0.25 + 0.75 * np.clip(gust + 0.08 * lfo(N, 0.6, 2), 0, 1)
        body = filt(filt(pink(N), "high", 60), "low", 1200) * g
        # свист: узкая полоса, центр медленно плывёт, громкость — квадрат порыва
        # свист: несколько узких полос, порыв плавно перекладывает громкость с низких на высокие
        whistle = np.zeros(N)
        bands = [430, 560, 720, 900]
        for i, fc in enumerate(bands):
            part = filt(rng.standard_normal(N), "band", [fc * 0.975, fc * 1.025], o=2)
            centre = i / (len(bands) - 1)
            weight = np.exp(-((gust - centre) ** 2) / 0.08)
            whistle += norm01(part) * weight
        whistle = filt(whistle, "low", 1500) * g ** 2.5
        rustle = filt(rng.standard_normal(N), "high", 2500) * np.clip(np.gradient(filt(gust, "low", 2)) * SR * 0.6, 0, 1)
        return norm01(body) * 1.0 + norm01(whistle) * 0.16 + norm01(rustle) * 0.12
    return reverb(stereo(ch), 1.2, 0.12)


# ------------------------------------------------------------------ море: прибой и откат по гальке
def waves():
    def ch():
        x = 0.35 * norm01(filt(brown(N), "low", 180))  # далёкий гул
        pos = rng.uniform(0, 3)
        while pos < D:
            per = rng.uniform(8, 12)
            s = int(pos * SR)
            L = min(N - s, int(per * SR))
            if L <= 0:
                break
            t = np.arange(L) / SR
            rise = np.clip(t / (per * 0.35), 0, 1) ** 2
            crash_t = per * 0.38
            body = filt(brown(L), "low", 500) * rise * np.exp(-np.clip(t - crash_t, 0, None) * 0.9)
            crash = filt(pink(L), "band", [400, 5000]) * np.exp(-np.abs(t - crash_t) * 3.0)
            back = filt(rng.standard_normal(L), "band", [2500, 11000]) * \
                np.clip((t - crash_t) / 0.6, 0, 1) * np.exp(-np.clip(t - crash_t, 0, None) * 0.55)
            pebbles = scatter(L, 900, drop_bank(48, 2500, 8000, (1, 2), 0.95), 0.5) * \
                np.clip((t - crash_t - 0.8) / 0.8, 0, 1) * np.exp(-np.clip(t - crash_t, 0, None) * 0.5)
            x[s:s + L] += norm01(body) * 0.9 + norm01(crash) * 0.55 + norm01(back) * 0.3 + norm01(pebbles) * 0.12
            pos += per * rng.uniform(0.75, 0.95)
        return x
    return reverb(stereo(ch), 1.6, 0.2)


# ------------------------------------------------------------------ костёр
def campfire():
    def ch():
        flick = 0.55 + 0.45 * lfo(N, 1.5, 2)
        roar = filt(brown(N), "low", 220) * flick
        hiss = filt(pink(N), "band", [1800, 7000]) * (0.5 + 0.5 * lfo(N, 0.3))
        crackle = scatter(N, 9, pop_bank(96), 0.9, 0.4 + 0.6 * lfo(N, 0.2))
        snaps = scatter(N, 0.35, drop_bank(32, 250, 900, (40, 90), 0.75), 0.4)
        return norm01(roar) * 0.3 + norm01(hiss) * 0.05 + norm01(crackle) * 1.0 + norm01(snaps) * 0.45
    return reverb(stereo(ch), 0.6, 0.12)


if __name__ == "__main__":
    for name, fn in [("rain", rain), ("stream", stream), ("wind", wind), ("waves", waves), ("campfire", campfire)]:
        save(name + "2", fn())
        print("ok", name)

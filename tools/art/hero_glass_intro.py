"""Заставки-витражи перед прологом (360×240): intro/intro_1_city … intro_6_sea.

Рисуется кодом поверх hero_glass_lib (осколки Вороного, свинцовые контуры, подсветка).
Запуск целиком — через hero_glass.py.
"""
import math
import random

from hero_glass_lib import *  # noqa: F401,F403
import hero_glass as hg
from hero_glass import point_in

W, H = 360, 240
REG = rect_poly(6, 6, 348, 228)
NIGHT_SEQ = ['#0B1244', '#101C5A', '#16296B', '#1B3A86', '#24408F', '#2B3E9E']
AUR = ['#2FD0A0', '#1F9E6B', '#38D9B0', '#2BC4BA']
GROUND = ['#145A52', '#0F4A4A', '#17695A', '#124A5E']


def new(prefix, light=(180, 90), lw=1.8):
    g = Glass(W, H, prefix, prec=0, lw=lw, light=light)
    g.gmin = 700
    return g


def frame_lead(g, lw=5.0):
    """Свинцовая рама: полосы поверх свечения + внутренний контур."""
    g.flush()
    for r in [(0, 0, 360, 6), (0, 234, 360, 6), (0, 0, 6, 240), (354, 0, 6, 240)]:
        g.rects(LEAD, [r])
    g.lead_line(rect_poly(6, 6, 348, 228), lw=lw, closed=True)


def sky_mosaic(g, region, box, colorfn, seed, rfun, accept=None):
    seeds = poisson(box, rfun, seed, 4000, accept=accept)
    return g.mosaic(region, seeds, colorfn, lw=1.5)


def sheen(g, region):
    """Диагональные блики стекла (общий градиент, дёшево)."""
    gr = g.linear([(0, '#FFFFFF', 0.0), (0.5, '#FFFFFF', 0.10), (1, '#FFFFFF', 0.0)], 0, 0, 1, 1)
    for (x0, x1) in [(40, 120), (210, 260), (300, 340)]:
        c = clip_convex([(x0, 0), (x0 + 22, 0), (x1 + 22, 240), (x1, 240)], region)
        if len(c) >= 3:
            g.shard(c, gr, lw=0, grad=False, nolead=True)


def fir(g, x, yb, h, w, c1, c2, lw=1.4, tiers=3):
    """Ель из двух половин (светлая/тёмная грань)."""
    right, left = [], []
    top = (x, yb - h)
    for k in range(1, tiers + 1):
        t = k / tiers
        yk = yb - h + h * t
        hw = w / 2 * (0.3 + 0.7 * t)
        notch = hw * 0.55
        right += [(x + hw, yk), (x + notch, yk - h / tiers * 0.28)] if k < tiers else [(x + hw, yk)]
        left += [(x - hw, yk), (x - notch, yk - h / tiers * 0.28)] if k < tiers else [(x - hw, yk)]
    base = (x, yb)
    g.shard([top] + left + [base], c1, lw=lw, grad=False)
    g.shard([top] + right + [base], c2, lw=lw, grad=False)


def star5(cx, cy, r, rot=-math.pi / 2):
    p = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = rot + math.pi * i / 5
        p.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return p


def smooth_pts(pts, k=6):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else p2
        for j in range(k):
            t = j / k
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(pts[-1])
    return out


# ---------------------------------------------------------------- 1. город
def intro_1_city():
    g = new('c1', light=(250, 120))
    hy = 186
    ya = lambda x: 52 + 14 * math.sin(x / 38.0)

    def sky_col(x, y, i):
        r2 = random.Random(int(x * 5 + y * 11))
        if abs(y - ya(x)) < 15 and x > 80:
            return r2.choice(AUR)
        t = max(0, min(1, y / hy))
        return NIGHT_SEQ[min(5, int(t * 3.4 + r2.random() * 1.6))]

    sky_mosaic(g, clip_half(REG, 0, hy, 0, 1), (6, 6, 354, hy), sky_col, 3, lambda x, y: 31 + (y / hy) * 5)
    g.glow(190, 170, 130, '#6D5BD0', 0.35)
    g.glow(250, 120, 90, '#7FE8DD', 0.28)
    g.lead_flush()
    # сияние-«мечта» над городом: узкие лучи
    for (x, hh) in [(124, 18), (258, 22), (300, 16)]:
        g.shard([(x, ya(x) + 4), (x + 4, ya(x) + 4), (x + 2.5, ya(x) - hh), (x + 1, ya(x) - hh + 2)], '#8FF0E6', lw=0.8, grad=False, op=0.6)
    # город
    rnd = random.Random(8)
    cols = ['#18266A', '#1C2E78', '#22307A', '#2A2F7A', '#1B3A86', '#26286E']
    x = 6
    wins = {'#F0A24A': [], '#7FE8DD': [], '#EDE6D2': []}
    kre = 186
    while x < 354:
        w = rnd.randint(20, 34)
        w = min(w, 354 - x)
        if x < kre + 14 and x + w > kre - 34:   # место под Кремль
            x = kre + 16
            continue
        hgt = rnd.randint(44, 92)
        top = hy - hgt
        g.shard([(x, hy), (x, top), (x + w, top - (rnd.randint(0, 6) if rnd.random() < 0.3 else 0)), (x + w, hy)], rnd.choice(cols), lw=1.5)
        for yy in range(top + 6, hy - 6, 9):
            for xx in range(x + 4, x + w - 5, 8):
                if rnd.random() < 0.21:
                    wins[rnd.choice(['#F0A24A'] * 6 + ['#7FE8DD'] + ['#EDE6D2'])].append((xx, yy, 3, 4))
        x += w
    # Кремль: стена с зубцами, башня с часами, шатёр, звезда
    wall = [(kre - 34, hy), (kre - 34, hy - 20)]
    for i in range(9):
        xx = kre - 34 + i * 4
        wall += [(xx, hy - 24), (xx + 2, hy - 24), (xx + 2, hy - 20), (xx + 4, hy - 20)]
    wall += [(kre - 34 + 36, hy)]
    g.shard([(kre - 34, hy), (kre - 34, hy - 20), (kre - 34 + 36, hy - 20), (kre - 34 + 36, hy)], '#7A2E46', lw=1.4)
    g.shard([(kre + 14, hy), (kre + 14, hy - 20), (kre + 52, hy - 20), (kre + 52, hy)], '#7A2E46', lw=1.4)
    for sx in (kre - 34, kre + 14):
        g.rects('#7A2E46', [(sx + i * 4.5, hy - 24, 2.5, 4) for i in range(8)])
    g.shard([(kre - 9, hy), (kre - 9, hy - 70), (kre + 9, hy - 70), (kre + 9, hy)], '#9A3A52', lw=1.6)
    g.shard([(kre - 9, hy - 70), (kre - 12, hy - 74), (kre + 12, hy - 74), (kre + 9, hy - 70)], '#C8454F', lw=1.4)
    g.shard([(kre - 7, hy - 74), (kre - 7, hy - 90), (kre + 7, hy - 90), (kre + 7, hy - 74)], '#B03C50', lw=1.4)
    g.shard([(kre - 8, hy - 90), (kre, hy - 118), (kre + 8, hy - 90)], '#C8454F', lw=1.5)
    g.shard(star5(kre, hy - 124, 7.5), '#E85A62', lw=1.2, grad=False)
    g.circle(kre, hy - 55, 5.2, MILK, lw=1.2)
    g.rects('#F0A24A', [(kre - 3, hy - 36, 6, 9), (kre - 3, hy - 84, 6, 5)])
    g.rects('#F0A24A', wins['#F0A24A'])
    g.rects('#7FE8DD', wins['#7FE8DD'])
    g.rects('#EDE6D2', wins['#EDE6D2'])
    g.lead_flush()
    # улица
    gr = clip_half(REG, 0, hy, 0, -1)
    gs = poisson((6, hy, 354, 234), lambda x, y: 27, 5, 900, accept=lambda x, y: y > hy + 3)
    g.mosaic(gr, gs, lambda x, y, i: ['#1B2C6E', '#16245A', '#22307A', '#1B3A86'][i % 4], lw=1.5)
    # отражения окон на мокром асфальте
    for (x0, c) in [(70, '#F0A24A'), (150, '#7FE8DD'), (212, '#F0A24A'), (320, '#F0A24A')]:
        g.shard([(x0, hy + 4), (x0 + 6, hy + 4), (x0 + 4, 232), (x0 + 2, 232)], c, lw=0, grad=False, op=0.35, nolead=True)
    # фонарь
    g.shard([(236, 232), (236, 150), (239, 150), (239, 232)], '#0E1536', lw=1.2, grad=False)
    g.glow(238, 150, 34, '#F0A24A', 0.5)
    g.shard([(231, 148), (238, 141), (245, 148), (242, 153), (234, 153)], '#F0A24A', lw=1.3, grad=False)
    # выход из метро (светящаяся арка), знак «М» и Сергей
    g.glow(326, 206, 50, '#7FE8DD', 0.5)
    g.lead_flush()
    g.shard([(304, 234), (304, 202), (312, 188), (326, 183), (340, 188), (348, 202), (348, 234)], '#2BC4BA', lw=2.2)
    g.shard([(312, 234), (312, 204), (326, 192), (340, 204), (340, 234)], '#BDF4EE', lw=1.4)
    g.shard([(326, 192), (340, 204), (326, 214), (312, 204)], '#EAFDFB', lw=1.0)
    g.shard([(318, 176), (318, 160), (320, 160), (320, 176)], '#0E1536', lw=1.0, grad=False)
    mx, my = 313, 148
    g.shard([(mx, my + 12), (mx, my), (mx + 6, my + 7), (mx + 12, my), (mx + 12, my + 12), (mx + 9, my + 12), (mx + 9, my + 7), (mx + 6, my + 11), (mx + 3, my + 7), (mx + 3, my + 12)], '#E85A62', lw=1.1, grad=False)
    g.lead_flush()
    g.prec = 1
    g.light = (320, 120)
    hg.walker_profile(g, 270, 229, 0.6, 'mid', lw=1.2, lw_face=0.8, rim=False)
    g.lead_flush()
    g.prec = 0
    sheen(g, REG)
    frame_lead(g, 5.0)
    g.lead_flush()
    for (x, y, r) in [(40, 30, 2.2), (96, 18, 1.8), (330, 28, 2.2), (60, 82, 1.6)]:
        g.spark(x, y, r, MILK, 0.9)
    return g.render()


# ---------------------------------------------------------------- 2. шаги -> путь
def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def intro_2_steps():
    g = new('c2', light=(300, 120))
    hy = 132
    gx, gy = 304, 128
    ya = lambda x: 44 + 12 * math.sin(x / 40.0 + 1.0)

    def sky_col(x, y, i):
        r2 = random.Random(int(x * 5 + y * 11))
        d = math.hypot(x - gx, (y - gy) * 1.3)
        if d < 52:
            return ['#D7F9F4', '#A9EFE7', '#74E0D6'][min(2, int(d / 52 * 3))]
        if d < 76:
            return r2.choice(['#2BC4BA', '#34D4C8', '#1F9E9A'])
        if abs(y - ya(x)) < 13 and x < 260:
            return r2.choice(AUR)
        t = max(0, min(1, y / hy))
        return NIGHT_SEQ[min(5, int(t * 3.4 + r2.random() * 1.5))]

    sky_mosaic(g, clip_half(REG, 0, hy + 2, 0, 1), (6, 6, 354, hy), sky_col, 7, lambda x, y: 29 + (y / hy) * 3)
    g.glow(gx, gy, 110, '#9FF5EA', 0.45)
    g.lead_flush()
    # дальние горы-грани
    for (x0, xp, yp, x1) in [(6, 50, 104, 120), (96, 150, 94, 214), (230, 262, 106, 330), (300, 340, 100, 354)]:
        lit = clip_convex([(x0, hy + 2), (xp, yp), (xp + 6, hy + 2)], REG)
        dark = clip_convex([(xp, yp), (min(x1, 354), hy + 2), (xp + 6, hy + 2)], REG)
        if len(lit) >= 3:
            g.shard(lit, '#1E8296', lw=1.5)
        if len(dark) >= 3:
            g.shard(dark, '#165B78', lw=1.5)
    gr = clip_half(REG, 0, hy + 2, 0, -1)
    gs = poisson((6, hy, 354, 234), lambda x, y: 30, 4, 900, accept=lambda x, y: y > hy + 4)
    g.mosaic(gr, gs, lambda x, y, i: ['#0F4A4A', '#0E3F44', '#124A5E', '#0F5240'][i % 4], lw=1.6)
    # тропа
    P0, P1, P2, P3 = (-6, 250), (140, 238), (214, 170), (gx, gy + 2)
    ts = [0, 0.16, 0.30, 0.42, 0.53, 0.63, 0.72, 0.80, 0.88, 0.94, 1.0]
    wd = lambda t: 130 * (1 - t) ** 1.45 + 5
    pts_ = []
    for t in ts:
        p = bez(P0, P1, P2, P3, t)
        q = bez(P0, P1, P2, P3, min(1, t + 0.01)) if t < 1 else p
        q0 = bez(P0, P1, P2, P3, max(0, t - 0.01))
        dx, dy = q[0] - q0[0], q[1] - q0[1]
        L = math.hypot(dx, dy) or 1
        pts_.append((p, (-dy / L, dx / L), wd(t), (dx / L, dy / L)))
    pal = ['#3A52C2', '#4A64D4', '#2F46B0', '#3E5ACB']
    for k in range(len(pts_) - 1):
        (pa, na, wa, _), (pb, nb, wb, _) = pts_[k], pts_[k + 1]
        m = 3 if wa > 60 else (2 if wa > 22 else 1)
        for i in range(m):
            f0, f1 = -0.5 + i / m, -0.5 + (i + 1) / m
            q = [(pa[0] + na[0] * wa * f0, pa[1] + na[1] * wa * f0), (pa[0] + na[0] * wa * f1, pa[1] + na[1] * wa * f1),
                 (pb[0] + nb[0] * wb * f1, pb[1] + nb[1] * wb * f1), (pb[0] + nb[0] * wb * f0, pb[1] + nb[1] * wb * f0)]
            c = clip_convex(q, REG)
            if len(c) >= 3:
                g.shard(c, pal[(i + k) % 4], lw=1.4)
    g.lead_flush()
    # отпечатки-осколки: цепочка бирюзовых шагов (передняя часть стопы + пятка)
    for k, t in enumerate([0.10, 0.22, 0.33, 0.43, 0.52, 0.60, 0.67, 0.74, 0.80, 0.86]):
        p = bez(P0, P1, P2, P3, t)
        q0 = bez(P0, P1, P2, P3, t - 0.01)
        q1 = bez(P0, P1, P2, P3, t + 0.01)
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux
        w = wd(t)
        side = 1 if k % 2 == 0 else -1
        cx, cy = p[0] + nx * w * 0.2 * side, p[1] + ny * w * 0.2 * side
        u = max(7.0, w * 0.36)
        rot = math.atan2(dy, dx)
        fore = ellipse_poly(cx + ux * u * 0.45, cy + uy * u * 0.45, u * 0.5, u * 0.34, 8, rot)
        heel = ellipse_poly(cx - ux * u * 0.55, cy - uy * u * 0.55, u * 0.27, u * 0.23, 8, rot)
        g.glow(cx, cy, u * 1.5, '#7FEDE3', 0.35)
        g.shard(fore, ['#7FEDE3', '#5FE8DC'][k % 2], lw=1.3, grad=False)
        g.shard(heel, '#2BC4BA', lw=1.2, grad=False)
    g.lead_flush()
    # шаги -> осколки: парящие ромбы
    rnd = random.Random(21)
    for k in range(16):
        t = 0.15 + 0.8 * rnd.random()
        p = bez(P0, P1, P2, P3, t)
        off = (20 + 60 * (1 - t)) * (1 if rnd.random() < 0.5 else -1)
        x, y = p[0] + off * 0.7, p[1] - 14 - 40 * rnd.random() * (1 - t) - 8
        r = 4 + 6 * (1 - t) * rnd.random()
        a = rnd.uniform(-0.6, 0.6)
        pts4 = [(x + r * math.sin(a), y - r * math.cos(a)), (x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)),
                (x - r * math.sin(a), y + r * math.cos(a)), (x - r * 0.55 * math.cos(a), y - r * 0.55 * math.sin(a))]
        if 12 < x < 348 and 14 < y < 230:
            g.shard(pts4, ['#7FEDE3', '#BDF4EE', '#2BC4BA'][k % 3], lw=1.1, grad=False)
    g.lead_flush()
    sheen(g, REG)
    frame_lead(g)
    g.lead_flush()
    for (x, y, r) in [(40, 26, 2.2), (120, 16, 1.8), (330, 22, 2.4), (200, 70, 1.6)]:
        g.spark(x, y, r, MILK, 0.9)
    return g.render()


# ---------------------------------------------------------------- 3. маршрут-карта
def intro_3_route():
    g = new('c3', light=(200, 40))
    # море (весь фон)
    def sea_col(x, y, i):
        r2 = random.Random(int(x * 3 + y * 7))
        d = math.hypot(x - 258, y - 38)
        if d < 36:
            return r2.choice(['#2BC4BA', '#1F9E9A', '#5FD6CB'])
        return r2.choice(['#1B3A86', '#1B4F8C', '#14407E', '#24408F', '#1A5A9A'])
    sky_mosaic(g, REG, (6, 6, 354, 234), sea_col, 3, lambda x, y: 38)
    g.glow(258, 40, 70, '#7FE8DD', 0.3)
    g.lead_flush()
    land_cols = ['#1F9E6B', '#17805A', '#2B9E7E', '#1A7C6E', '#3A8E5E', '#1F8A7A']
    L1 = [(70, 232), (56, 160), (96, 128), (190, 112), (300, 124), (336, 172), (326, 232)]
    L2 = [(98, 132), (110, 74), (150, 54), (210, 38), (264, 42), (272, 72), (238, 98), (190, 112)]
    for reg, seed, rr in ((L1, 11, 27), (L2, 12, 23)):
        sd = poisson((50, 30, 340, 234), lambda x, y: rr, seed, 3000, accept=lambda x, y, reg=reg: point_in(reg, x, y))
        g.mosaic(reg, sd, lambda x, y, i: land_cols[(i * 5 + int(y)) % 6], lw=1.6)
    # Белое море
    g.shard([(240, 98), (258, 84), (276, 76), (296, 90), (300, 110), (280, 116), (256, 112)], '#1B4F8C', lw=1.8)
    g.shard([(276, 76), (296, 90), (300, 110), (286, 100)], '#2B7BC0', lw=1.2, grad=False)
    g.shard([(108, 118), (122, 112), (130, 126), (120, 140), (108, 134)], '#2B7BC0', lw=1.4, grad=False)
    g.shard([(146, 100), (153, 94), (158, 112), (150, 124), (144, 112)], '#2B7BC0', lw=1.4, grad=False)
    g.lead_flush()
    # красная нить пути: Москва -> север -> Териберка
    route = [(138, 212), (156, 196), (178, 184), (190, 162), (176, 136), (186, 112), (206, 86), (226, 64), (252, 46)]
    sm = smooth_pts(route, 6)
    g.lead_line(sm, lw=7.2)
    g.lead_flush()
    g.blik(sm, color='#E85A62', w=3.6, op=1)
    g.blik(sm, color='#FF9AA0', w=1.0, op=0.8)
    g.flush_post()
    # города — цветные стёклышки
    cities = [((138, 212), 8.5, '#C8454F'), ((166, 190), 5, '#F0A24A'), ((190, 162), 5.2, '#2BC4BA'), ((176, 136), 5, '#7A5BD0'),
              ((186, 112), 4.8, '#F0A24A'), ((206, 86), 5, '#2BC4BA'), ((226, 64), 5.2, '#7A5BD0'), ((252, 46), 8, '#7FEDE3')]
    for (x, y), r, col in cities:
        g.shard([(x, y - r), (x + r * 0.85, y), (x, y + r), (x - r * 0.85, y)], col, lw=1.6, grad=False)
    g.shard(star5(138, 212, 4), '#FFD9A0', lw=0.6, grad=False, nolead=True)
    g.lead_flush()
    # кит в Баренцевом море
    hg.whale_tail(g, 322, 54, 1.0, lw=1.4)
    # роза ветров
    cx, cy = 44, 202
    g.shard([(cx, cy - 22), (cx + 5, cy - 5), (cx + 22, cy), (cx + 5, cy + 5), (cx, cy + 22), (cx - 5, cy + 5), (cx - 22, cy), (cx - 5, cy - 5)], '#EDE6D2', lw=1.6, grad=False)
    g.shard([(cx, cy - 22), (cx + 5, cy - 5), (cx - 5, cy - 5)], '#2BC4BA', lw=1.2, grad=False)
    g.lead_flush()
    g.spark(300, 150, 2, MILK, 0.8)
    sheen(g, REG)
    frame_lead(g)
    g.lead_flush()
    return g.render()


# ---------------------------------------------------------------- 4. духи леса
def eyes(g, x, y, col='#F0A24A', r=2.8, gap=7, glow_r=14):
    g.glow(x, y, glow_r, col, 0.45)
    g.flush()
    for dx in (-gap / 2, gap / 2):
        g.shard(ellipse_poly(x + dx, y, r, r * 0.72, 8), col, lw=0.9, grad=False)
        g.circle(x + dx + 0.5, y, r * 0.38, '#2A1A1E', lw=0, nolead=True, grad=False)


def intro_4_spirits():
    g = new('c4', light=(290, 50))
    hy = 138

    def sky_col(x, y, i):
        r2 = random.Random(int(x * 5 + y * 11))
        d = math.hypot(x - 290, y - 52)
        if d < 40:
            return r2.choice(['#2A5E8E', '#2F6E9C', '#24527E'])
        seq = ['#0B1244', '#0E1E4A', '#102C52', '#133B58', '#17495E']
        return seq[min(4, int(y / hy * 3.2 + r2.random() * 1.4))]

    sky_mosaic(g, clip_half(REG, 0, hy + 6, 0, 1), (6, 6, 354, hy + 6), sky_col, 5, lambda x, y: 36)
    g.glow(290, 52, 90, '#9FD8F0', 0.2)
    g.lead_flush()
    g.circle(290, 52, 15, MILK, lw=1.8, grad=False)
    g.circle(285, 48, 3, '#CFC8B0', lw=0, nolead=True, grad=False)
    g.circle(295, 58, 2, '#CFC8B0', lw=0, nolead=True, grad=False)
    # дальний лес
    rnd = random.Random(4)
    x = 8
    while x < 356:
        h = rnd.uniform(34, 52)
        fir(g, x, hy + 6, h, h * 0.55, '#17495E', '#123A52', lw=1.1)
        x += rnd.uniform(20, 28)
    # земля
    gs = poisson((6, hy, 354, 234), lambda x, y: 36, 6, 900, accept=lambda x, y: y > hy + 8)
    g.mosaic(clip_half(REG, 0, hy + 6, 0, -1), gs, lambda x, y, i: ['#0E3A3E', '#0F4A4A', '#0B2F3E', '#124A5E'][i % 4], lw=1.6)
    # средний лес
    for (xx, hh) in [(74, 66), (130, 74), (190, 60), (300, 70)]:
        fir(g, xx, hy + 22, hh, hh * 0.52, '#0F3A48', '#0B2F3E', lw=1.4)
    # тропа к избушке
    P0, P1, P2, P3 = (150, 246), (130, 200), (250, 190), (240, 154)
    ts = [0, 0.2, 0.38, 0.54, 0.68, 0.8, 0.9, 1.0]
    for k in range(len(ts) - 1):
        pa, pb = bez(P0, P1, P2, P3, ts[k]), bez(P0, P1, P2, P3, ts[k + 1])
        wa, wb = 54 * (1 - ts[k]) ** 1.2 + 5, 54 * (1 - ts[k + 1]) ** 1.2 + 5
        for (p0, p1, w0, w1) in [(pa, pb, wa, wb)]:
            q = [(p0[0] - w0 / 2, p0[1]), (p0[0] + w0 / 2, p0[1]), (p1[0] + w1 / 2, p1[1]), (p1[0] - w1 / 2, p1[1])]
            c = clip_convex(q, REG)
            if len(c) >= 3:
                g.shard(c, ['#7FD9D2', '#A5E8E0', '#5FC9C4', '#BDF2EC'][k % 4], lw=1.4)
    g.lead_flush()
    # избушка на ножках (вдали)
    hx_, hy_ = 240, 152
    g.glow(hx_, hy_ - 10, 34, '#F0A24A', 0.4)
    g.lead_flush()
    for dx in (-7, 5):
        g.shard([(hx_ + dx, hy_ + 2), (hx_ + dx + 3, hy_ + 2), (hx_ + dx + 3.5, hy_ + 12), (hx_ + dx + 7, hy_ + 14), (hx_ + dx - 2, hy_ + 14), (hx_ + dx - 0.5, hy_ + 12)], '#3A2A4E', lw=1.0, grad=False)
    g.shard([(hx_ - 14, hy_ + 2), (hx_ - 14, hy_ - 16), (hx_ + 14, hy_ - 16), (hx_ + 14, hy_ + 2)], '#5A3A55', lw=1.5)
    g.shard([(hx_ - 18, hy_ - 15), (hx_, hy_ - 33), (hx_ + 18, hy_ - 15)], '#3A2660', lw=1.5)
    g.shard([(hx_ - 5, hy_ - 12), (hx_ + 5, hy_ - 12), (hx_ + 5, hy_ - 3), (hx_ - 5, hy_ - 3)], '#F0A24A', lw=1.2, grad=False)
    g.shard([(hx_ + 9, hy_ - 33), (hx_ + 9, hy_ - 40), (hx_ + 13, hy_ - 40), (hx_ + 13, hy_ - 29)], '#3A2660', lw=1.0, grad=False)
    g.lead_flush()
    # леший: тёмная фигура с мшистой бородой, добрые глаза
    lx = 92
    g.shard([(lx - 24, 236), (lx - 28, 170), (lx - 20, 128), (lx - 8, 100), (lx, 94), (lx + 8, 100), (lx + 20, 128), (lx + 28, 170), (lx + 24, 236)], '#0C2E34', lw=1.8)
    g.shard([(lx - 20, 128), (lx - 8, 100), (lx, 94), (lx + 8, 100), (lx + 20, 128), (lx + 12, 136), (lx - 12, 136)], '#134452', lw=1.4)
    g.shard([(lx - 16, 138), (lx + 16, 138), (lx + 20, 164), (lx, 190), (lx - 20, 164)], '#2F7D55', lw=1.4)
    g.shard([(lx - 8, 150), (lx + 8, 150), (lx, 178)], '#4FA070', lw=1.0, grad=False)
    for (dx, up) in [(-6, 22), (6, 26)]:
        g.shard([(lx + dx - 1.5, 100), (lx + dx * 2.2, 100 - up), (lx + dx * 2.2 + 2, 100 - up), (lx + dx + 1.5, 100)], '#134452', lw=1.0, grad=False)
    g.lead_flush()
    eyes(g, lx, 122, '#F0A24A', 2.6, 11, 18)
    # огромные ели по краям с глазами в чаще
    fir(g, 26, 236, 210, 96, '#050D17', '#0A1A2A', lw=1.8, tiers=6)
    fir(g, 338, 236, 220, 100, '#0A1A2A', '#050D17', lw=1.8, tiers=6)
    g.lead_flush()
    eyes(g, 24, 168, '#F0A24A', 2.2, 9, 14)
    eyes(g, 40, 202, '#7FEDE3', 2.0, 8, 12)
    eyes(g, 338, 150, '#7FEDE3', 2.2, 9, 14)
    eyes(g, 322, 196, '#F0A24A', 2.0, 8, 12)
    eyes(g, 188, 150, '#F0A24A', 1.5, 6, 10)
    g.lead_flush()
    # грибы и светлячки
    for (mx, my) in [(176, 214), (196, 226), (122, 224)]:
        g.shard([(mx - 5, my), (mx - 4, my - 4), (mx, my - 6), (mx + 4, my - 4), (mx + 5, my)], '#E85A62', lw=1.0, grad=False)
        g.shard([(mx - 1.2, my), (mx + 1.2, my), (mx + 1.2, my + 4), (mx - 1.2, my + 4)], '#EDE6D2', lw=0.8, grad=False)
    g.lead_flush()
    for (x, y, r) in [(160, 120, 2.4), (200, 100, 2), (140, 176, 2.2), (206, 188, 2), (262, 120, 2.2), (60, 100, 2)]:
        g.glow(x, y, 9, '#7FEDE3', 0.5)
        g.spark(x, y, r, '#BDF4EE', 0.95)
    sheen(g, REG)
    frame_lead(g)
    g.lead_flush()
    return g.render()


# ---------------------------------------------------------------- 5. три сосуда
def vessel(g, cx, base_y, liquid, liquid_hi, level_y, pict):
    n = [(-11, 90), (11, 90), (14, 86), (-14, 86)]
    body = [(-10, 90), (10, 90), (11, 108), (30, 124), (38, 150), (34, 176), (22, 192), (-22, 192), (-34, 176), (-38, 150), (-30, 124), (-11, 108)]
    T = lambda pts: [(cx + x, base_y - 196 + y) for x, y in pts]
    bd = T(body)
    # стекло сосуда (бледное) и жидкость
    g.shard(bd, '#BDE3F0', lw=2.2, grad=False, op=0.30)
    liq = clip_half(bd, 0, base_y - 196 + level_y, 0, -1)
    liq = clip_half(bd, 0, base_y - 196 + level_y, 0, 1)
    g.shard(liq, liquid, lw=1.6)
    g.shard(clip_half(liq, cx - 14, 0, 1, 0)[:], liquid_hi, lw=0, grad=False, op=0.5, nolead=True)
    g.shard(T([(-14, 86), (14, 86), (12, 91), (-12, 91)]), '#E8F6FA', lw=1.6, grad=False)
    g.shard(T([(-12, 78), (12, 78), (14, 86), (-14, 86)]), '#8A5A3A', lw=1.6, grad=False)
    pict(g, cx, base_y - 196 + 152)
    g.blik(T([(-28, 132), (-33, 148), (-33, 160)]), color='#FFFFFF', w=1.6, op=0.7)


def pic_bread(g, cx, cy):
    g.shard(ellipse_poly(cx, cy, 20, 12, 12), '#D8934A', lw=1.4)
    for dx in (-9, 0, 9):
        g.shard([(cx + dx - 3, cy - 8), (cx + dx + 2, cy - 8), (cx + dx + 4, cy + 3), (cx + dx - 1, cy + 3)], '#F0C27A', lw=1.0, grad=False)


def pic_drop(g, cx, cy):
    g.shard([(cx, cy - 22), (cx + 10, cy - 4), (cx + 13, cy + 6), (cx + 8, cy + 15), (cx, cy + 18), (cx - 8, cy + 15), (cx - 13, cy + 6), (cx - 10, cy - 4)], '#9BE3FA', lw=1.5)
    g.shard([(cx - 4, cy - 2), (cx - 9, cy + 8), (cx - 5, cy + 13), (cx - 2, cy + 6)], '#EAFBFF', lw=0.9, grad=False)


def pic_flame(g, cx, cy):
    g.shard([(cx, cy - 24), (cx + 9, cy - 8), (cx + 14, cy + 4), (cx + 8, cy + 16), (cx, cy + 19), (cx - 8, cy + 16), (cx - 14, cy + 4), (cx - 8, cy - 6), (cx - 3, cy - 10)], '#F0A24A', lw=1.5)
    g.shard([(cx, cy - 8), (cx + 6, cy + 4), (cx + 4, cy + 13), (cx, cy + 15), (cx - 4, cy + 13), (cx - 6, cy + 4)], '#FFD9A0', lw=1.1, grad=False)


def intro_5_stats():
    g = new('c5', light=(180, 70))

    def bg(x, y, i):
        r2 = random.Random(int(x * 5 + y * 11))
        return ['#0F1A4B', '#16296B', '#1B3A86', '#24408F', '#2B3E9E', '#33307F'][r2.randint(0, 5)]
    sky_mosaic(g, REG, (6, 6, 354, 234), bg, 8, lambda x, y: 30)
    for cx, col in ((70, '#D9645A'), (180, '#2B7BC0'), (290, '#E0505F')):
        g.glow(cx, 140, 80, col, 0.38)
    g.lead_flush()
    # три ниши-арки
    for cx, glass in ((70, '#3A2A6E'), (180, '#1B4F8C'), (290, '#4A2A66')):
        P = arch_params(cx - 54, cx + 54, 84, 18, 214, R=62)
        o = arch_poly(P, 0, n=6, side=2)
        g.shard(o, glass, lw=2.4)
    g.lead_flush()
    for cx, col in ((70, '#D9645A'), (180, '#2B7BC0'), (290, '#E0505F')):
        g.glow(cx, 140, 56, col, 0.45)
    g.lead_flush()
    vessel(g, 70, 212, '#D9645A', '#F2907A', 126, pic_bread)
    vessel(g, 180, 212, '#2B7BC0', '#7FD3F2', 118, pic_drop)
    vessel(g, 290, 212, '#C8454F', '#F2707A', 122, pic_flame)
    g.lead_flush()
    # полка
    g.shard([(6, 212), (354, 212), (354, 234), (6, 234)], '#0F1A4B', lw=2.2)
    g.shard([(6, 212), (354, 212), (354, 218), (6, 218)], '#2BC4BA', lw=1.4)
    g.lead_flush()
    for (x, y, r) in [(30, 36, 2.4), (126, 30, 2), (234, 28, 2), (330, 36, 2.4)]:
        g.spark(x, y, r, MILK, 0.9)
    sheen(g, REG)
    frame_lead(g)
    g.lead_flush()
    return g.render()


# ---------------------------------------------------------------- 6. Териберка: море, кит, сияние
def intro_6_sea():
    g = new('c6', light=(190, 60))
    hy = 128
    ya1 = lambda x: 52 + 20 * math.sin(x / 52.0)
    ya2 = lambda x: 88 + 12 * math.sin(x / 38.0 + 2)

    def sky_col(x, y, i):
        r2 = random.Random(int(x * 5 + y * 11))
        if abs(y - ya1(x)) < 17:
            return r2.choice(['#2FD0A0', '#1F9E6B', '#38D9B0', '#2BC4BA', '#7FEDE3'])
        if abs(y - ya2(x)) < 10:
            return r2.choice(['#1F9E6B', '#1A8F85', '#2BC4BA'])
        seq = ['#0B1244', '#101C5A', '#16296B', '#1B3A86', '#2B3E9E']
        return seq[min(4, int(y / hy * 3.0 + r2.random() * 1.5))]
    sky_mosaic(g, clip_half(REG, 0, hy + 4, 0, 1), (6, 6, 354, hy + 4), sky_col, 6, lambda x, y: 29)
    g.glow(190, 70, 140, '#7FEDE3', 0.22)
    g.lead_flush()
    # сопки у горизонта
    for (x0, xp, yp, x1) in [(6, 40, 100, 120), (90, 150, 92, 230), (210, 262, 104, 330), (300, 336, 96, 354)]:
        lit = clip_convex([(x0, hy + 4), (xp, yp), (xp + 6, hy + 4)], REG)
        dark = clip_convex([(xp, yp), (min(x1, 354), hy + 4), (xp + 6, hy + 4)], REG)
        if len(lit) >= 3:
            g.shard(lit, '#2A4A9A', lw=1.5)
        if len(dark) >= 3:
            g.shard(dark, '#1B3478', lw=1.5)
    # море
    def sea_col(x, y, i):
        r2 = random.Random(int(x * 3 + y * 7))
        t = (y - hy) / (234 - hy)
        if 80 < x < 280 and r2.random() < 0.5 - 0.35 * t:
            return r2.choice(['#1F9E9A', '#2BC4BA', '#1A8F85'])
        seq = ['#1B5A9A', '#1B4F8C', '#14407E', '#103468']
        return seq[min(3, int(t * 2.4 + r2.random() * 1.3))]
    sd = poisson((6, hy, 354, 234), lambda x, y: 24 + (y - hy) * 0.1, 3, 1200, accept=lambda x, y: y > hy + 3)
    g.mosaic(clip_half(REG, 0, hy + 4, 0, -1), sd, sea_col, lw=1.5)
    g.glow(190, 150, 100, '#7FEDE3', 0.18)
    g.lead_flush()
    # кит: нырок — спина дугой, хвост поднят, брызги
    g.glow(190, 150, 70, '#BDF4EE', 0.22)
    g.lead_flush()
    g.shard([(116, 180), (132, 164), (156, 154), (184, 152), (208, 160), (222, 174), (226, 182), (160, 186)], '#0A1C4F', lw=2.0)
    g.shard([(132, 164), (156, 154), (184, 152), (170, 164), (146, 170)], '#2A4FB0', lw=1.3)
    g.shard([(150, 184), (200, 178), (226, 182), (160, 186)], '#7FA6E0', lw=1.0, grad=False)
    g.shard([(202, 168), (214, 168), (240, 124), (232, 120)], '#0F2A78', lw=1.8)
    g.shard([(236, 123), (206, 108), (204, 118), (214, 124), (230, 130)], '#14308A', lw=1.8)
    g.shard([(236, 123), (266, 106), (268, 116), (258, 124), (242, 130)], '#2A4FB0', lw=1.8)
    for (a_, b_) in [(-36, 6), (-16, 0), (30, 2), (50, 8), (6, 10), (-26, 12), (22, 13)]:
        x0, y0 = 196 + a_, 176 + b_
        g.shard([(x0 - 6, y0), (x0 - 2, y0 - 8), (x0 + 3, y0 - 6), (x0 + 6, y0 + 1), (x0, y0 + 4)], '#DDF8F4', lw=1.1, grad=False)
    g.lead_flush()
    # скалы переднего плана
    g.shard([(6, 234), (6, 192), (34, 182), (66, 190), (96, 212), (112, 234)], '#16245A', lw=2.0)
    g.shard([(6, 192), (34, 182), (44, 200), (20, 222), (6, 218)], '#22307A', lw=1.5)
    g.shard([(300, 234), (318, 206), (346, 198), (354, 204), (354, 234)], '#16245A', lw=2.0)
    g.shard([(318, 206), (346, 198), (340, 218), (322, 226)], '#22307A', lw=1.5)
    g.lead_flush()
    # Сергей со спины на скале, смотрит на кита
    g.prec = 1
    g.light = (200, 80)
    hg.walker_back(g, 52, 190, 0.5, lw=1.1, lw_face=0.7, pole=True, rim=True)
    g.lead_flush()
    g.prec = 0
    for (x, y, r) in [(40, 26, 2.2), (300, 18, 2.4), (160, 24, 1.8), (336, 70, 1.8)]:
        g.spark(x, y, r, MILK, 0.9)
    sheen(g, REG)
    frame_lead(g)
    g.lead_flush()
    return g.render()


INTRO = dict(intro_1_city=intro_1_city, intro_2_steps=intro_2_steps, intro_3_route=intro_3_route,
             intro_4_spirits=intro_4_spirits, intro_5_stats=intro_5_stats, intro_6_sea=intro_6_sea)


def collect():
    return {f'intro/{k}.svg': fn() for k, fn in INTRO.items()}

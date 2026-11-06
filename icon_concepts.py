#!/usr/bin/env python3
"""10 концепций иконки «Путника» (витраж «фреска из стекла»), 512×512, фон на весь квадрат.

python3 tools/art/icon_concepts.py [outdir]   (по умолчанию /home/claude/out/icons)

Только элементы flutter_svg (path/circle/rect/g/градиенты). Инструменты — hero_glass_lib.Glass.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_glass_lib import *  # noqa: F401,F403
from hero_glass import marker_figure, point_in, glory  # noqa: E402

W = 512
SQ = rect_poly(0, 0, W, W)
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/out/icons'

NIGHT_SEQ = ['#0D1650', '#111D5C', '#152668', '#1A3278', '#203C88']
AUR = ['#2FD0A0', '#1F9E6B', '#38D9B0', '#2BC4BA']
GROUND = ['#145A52', '#0F4A4A', '#17695A', '#124A5E']
ROADC = ['#E4FBF6', '#9AEAE1', '#C4F3ED', '#7FDCD3']


def new(prefix, light=(256, 200)):
    return Glass(W, W, prefix, prec=0, lw=4.5, light=light, bg=LEAD)


def rnd(x, y, s=0):
    return random.Random(int(x * 7.1 + y * 13.3 + s * 101))


def sky_mosaic(g, seed, r=74, region=SQ, ybot=512, aur=None, glow=None, seq=NIGHT_SEQ, lw=3.0, span=420):
    """Фон-мозаика: ночь сверху светлеет книзу; aur — функция x->(y, полутолщина) ленты сияния."""
    def col(x, y, i):
        R = rnd(x, y, seed)
        if glow:
            gx, gy, gr, gseq = glow
            d = math.hypot(x - gx, y - gy)
            if d < gr:
                return gseq[min(len(gseq) - 1, int(d / gr * len(gseq) * 0.85 + R.random() * 0.8))]
        if aur:
            for f in aur:
                ya, h = f(x)
                if abs(y - ya) < h:
                    return R.choice(AUR)
        t = max(0.0, min(1.0, y / span))
        return seq[min(len(seq) - 1, int(t * (len(seq) - 1.2) + R.random() * 1.4))]
    seeds = poisson((0, 0, W, ybot), lambda x, y: r, seed, 5000, accept=lambda x, y: point_in(region, x, y))
    g.mosaic(clip_half(region, 0, ybot, 0, 1) if ybot < 512 else region, seeds, col, lw=lw)


def ribbon(g, pts, widths, cols, region=SQ, lw=4.5, grad=True):
    quads, _ = chain_quads(pts, widths)
    for i, q in enumerate(quads):
        c = clip_convex(q, region)
        if len(c) >= 3:
            g.shard(c, cols[i % len(cols)], lw=lw, grad=grad)
    return quads


def road(g, region, vx, vy, ybot, wbot, rows=5, m=2, cols=ROADC, lw=4.5, pw=1.7):
    ys = [vy + (ybot - vy) * ((k / rows) ** pw) for k in range(rows + 1)]
    ys[0] = vy
    for k in range(rows):
        ya, yb = ys[k], ys[k + 1]
        wa = 1.5 + (ya - vy) / (ybot - vy) * wbot
        wb = 1.5 + (yb - vy) / (ybot - vy) * wbot
        mm = 1 if k == 0 else m
        for i in range(mm):
            q = [(vx - wa + 2 * wa * i / mm, ya), (vx - wa + 2 * wa * (i + 1) / mm, ya),
                 (vx - wb + 2 * wb * (i + 1) / mm, yb), (vx - wb + 2 * wb * i / mm, yb)]
            q = clip_convex(q, region)
            if len(q) >= 3 and area(q) > 4:
                g.shard(q, cols[(i + k) % len(cols)], lw=lw)


def bez(ps, n=16):
    """Кубическая/квадратичная Безье по контрольным точкам."""
    out = []
    for i in range(n + 1):
        t = i / n
        pts_ = list(ps)
        while len(pts_) > 1:
            pts_ = [lerp(pts_[j], pts_[j + 1], t) for j in range(len(pts_) - 1)]
        out.append(pts_[0])
    return out


def stars(g, pts, col=MILK):
    for (x, y, r) in pts:
        g.spark(x, y, r, col, 0.92)


class TX:
    """Прокси Glass с переносом/масштабом координат (для marker_figure)."""
    def __init__(self, g, ox, oy, k, lk):
        self.g, self.ox, self.oy, self.k, self.lk = g, ox, oy, k, lk

    def _p(self, p):
        return [(self.ox + x * self.k, self.oy + y * self.k) for x, y in p]

    def shard(self, p, c, lw=None, grad=True, **kw):
        self.g.shard(self._p(p), c, lw=(lw or 1) * self.lk, grad=grad, **kw)

    def circle(self, cx, cy, r, c, lw=None, **kw):
        self.g.circle(self.ox + cx * self.k, self.oy + cy * self.k, r * self.k, c, lw=(lw or 1) * self.lk, **kw)


def rot_pts(p, a, c):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in p]


def finish_ground_glow(g):
    g.glow_e(256, 520, 300, 120, '#2BC4BA', 0.25)


# =============================================================================
# 1. Мипл-путник в шаге на фоне сияния
# =============================================================================
def ic_walker():
    g = new('a', light=(300, 180))
    sky_mosaic(g, 1, r=114, aur=[lambda x: (96 + 30 * math.sin(x / 70.0), 30)], span=400)
    g.glow(256, 250, 250, '#2BC4BA', 0.30, mid=0.6)
    g.lead_flush()
    # светлый диск-ореол за героем: лучи
    disk = circle_poly(256, 262, 168, 40)
    glory(g, 262, 300, disk, n=10, rot=-0.2, cols=['#BDF4EE', '#5FD9D0', '#8DEDE2', '#2BC4BA', '#A9EFE7', '#3ECDC3'])
    g.glow(262, 270, 175, '#E8FFFB', 0.45)
    g.lead_flush()
    g.lead_circle(256, 262, 168, lw=9)
    # земля и тропа
    gr = clip_half(SQ, 0, 418, 0, -1)
    gs = poisson((0, 420, 512, 512), lambda x, y: 70, 3, 800)
    g.mosaic(gr, gs, lambda x, y, i: GROUND[i % 4], lw=4.5)
    band = clip_convex([(0, 432), (512, 424), (512, 470), (0, 478)], SQ)
    for i, (xa, xb) in enumerate([(0, 150), (150, 270), (270, 390), (390, 512)]):
        c = clip_convex(band, [(xa, 400), (xb, 400), (xb, 512), (xa, 512)])
        g.shard(c, ROADC[i], lw=4.5)
    g.lead_flush()
    g.lead_line([(0, 418), (512, 418)], lw=7)
    # герой (мипл): bbox x14.4–36.4, y5.6–38.6 в 48-коробке
    k = 9.3
    marker_figure(TX(g, 254 - 25.6 * k, 440 - 38.6 * k, k, 6.6), lw=1.0)
    g.lead_flush()
    stars(g, [(96, 82, 9), (418, 92, 7), (70, 300, 6), (446, 320, 6)])
    return g.render()


# =============================================================================
# 2. След ботинка, внутри дорога к северу
# =============================================================================
def ic_footprint():
    """Отпечаток подошвы из поперечных «протекторов»-стёкол; сквозь них — дорога к горизонту и сияние."""
    g = new('b', light=(256, 120))
    sky_mosaic(g, 2, r=114, seq=['#0D1650', '#111D5C', '#152668', '#111D5C'], span=512)
    g.glow(256, 250, 250, '#2B3E9E', 0.4)
    g.lead_flush()
    C = (256, 262)
    A = 14
    R = lambda p: rot_pts(p, A, C)
    # полуширины подошвы (левый/правый край) вдоль длины y: носок сверху, пятка снизу
    def edges(y):
        # носок: 70..250, свод 250..330 (узко), пятка 340..450
        if y < 250:
            t = (y - 66) / 184.0
            t = max(0.0, min(1.0, t))
            w = 112 * math.sqrt(max(0.0, 1 - (1 - t) ** 2 * 1.0))
            off = -10 * (1 - t)        # большой палец смещён влево (внутрь)
            return 256 + off - w, 256 + off + w * 0.94
        if y < 336:
            t = (y - 250) / 86.0
            wl = 112 - 30 * math.sin(math.pi * t) - 26 * t
            wr = 105 - 44 * math.sin(math.pi * t) - 20 * t
            return 256 - wl, 256 + wr
        t = (y - 336) / 116.0
        t = max(0.0, min(1.0, t))
        w = 84 * math.sqrt(max(0.0, 1 - t ** 2))
        return 256 - w * 1.02, 256 + w
    hz = 222
    vx = 256
    strips = [(66, 106), (114, 150), (158, 192), (200, hz), (hz, 254), (262, 296), (304, 336), (352, 392), (400, 452)]
    rays = ['#2FD0A0', '#2BC4BA', '#8DEDE2', '#BDF4EE', '#8DEDE2', '#2BC4BA', '#1F9E6B', '#38D9B0']
    for si, (ya, yb) in enumerate(strips):
        ys = [ya + (yb - ya) * j / 4 for j in range(5)]
        L = [(edges(y)[0], y) for y in ys]
        Rr = [(edges(y)[1], y) for y in reversed(ys)]
        strip = clean(list(reversed(L + Rr)), 0.8)
        if len(strip) < 3:
            continue
        if yb <= hz:
            # небо: лучи из точки горизонта
            for i in range(8):
                a0 = math.pi + math.pi * i / 8
                a1 = math.pi + math.pi * (i + 1) / 8
                w = [(vx, hz), (vx + 400 * math.cos(a0), hz + 400 * math.sin(a0)), (vx + 400 * math.cos(a1), hz + 400 * math.sin(a1))]
                c = clip_convex(w, strip)
                if len(c) >= 3 and area(c) > 20:
                    g.shard(R(c), rays[i], lw=4.5)
        else:
            def rw(y):
                return 3 + (y - hz) * 0.40
            qa, qb = rw(ya), rw(yb)
            rd = [(vx - qa, ya), (vx + qa, ya), (vx + qb, yb), (vx - qb, yb)]
            lft = [(0, ya), (vx - qa, ya), (vx - qb, yb), (0, yb)]
            rgt = [(vx + qa, ya), (512, ya), (512, yb), (vx + qb, yb)]
            for poly, col in ((lft, '#17695A'), (rgt, '#0F4A4A'), (rd, ROADC[si % 4])):
                c = clip_convex(poly, strip)
                if len(c) >= 3 and area(c) > 20:
                    g.shard(R(c), col, lw=4.5)
        g.lead_line(R(strip), lw=9, closed=True)
    g.glow(*R([(vx, hz)])[0], 80, '#E8FFFB', 0.55)
    g.lead_flush()
    sp = R([(vx, 150)])[0]
    g.spark(sp[0], sp[1], 14, '#FFFFFF', 0.95)
    stars(g, [(92, 96, 8), (424, 108, 7), (436, 420, 6), (76, 380, 6)])
    return g.render()


# =============================================================================
# 3. Хвост кита над морем и лунная тропа
# =============================================================================
def ic_whale():
    g = new('c', light=(256, 230))
    hz = 330
    skyr = clip_half(SQ, 0, hz, 0, 1)
    glory(g, 256, hz - 10, skyr, n=16, rot=0.05, cols=['#8FF0E6', '#2BC4BA', '#1F9E6B', '#1B8FB5', '#2B3E9E', '#34D4B0', '#1B4F8C', '#5FD9D0'])
    g.flush()
    nt = g.linear([(0, '#0B1424', 0.9), (0.5, '#0B1424', 0.3), (1, '#0B1424', 0)], 0, 0, 0, 1)
    g.shard(clip_half(SQ, 0, 230, 0, 1), nt, lw=0, grad=False, nolead=True)
    g.glow(256, 240, 210, '#E8FFFB', 0.55)
    g.lead_flush()
    # море
    sea_rows = [hz, 356, 390, 436, 512]
    for k in range(len(sea_rows) - 1):
        ya, yb = sea_rows[k], sea_rows[k + 1]
        xs = [0, 140 - k * 20, 372 + k * 20, 512]
        for i in range(3):
            q = [(xs[i], ya), (xs[i + 1], ya), (xs[i + 1] + (i - 1) * 10, yb), (xs[i] + (i - 1) * 10, yb)]
            q = clip_convex(q, SQ)
            g.shard(q, ['#14407E', '#1B4F8C', '#123A73', '#1B3A86'][(i + k) % 4], lw=4.5)
    g.lead_flush()
    # лунная тропа по воде (светлые осколки, к хвосту)
    for k, (ya, yb, wa, wb) in enumerate([(338, 360, 18, 30), (366, 396, 36, 52), (404, 444, 60, 82), (452, 512, 92, 128)]):
        g.shard([(256 - wa, ya), (256 + wa, ya), (256 + wb, yb), (256 - wb, yb)], ROADC[k % 4], lw=4.5)
    g.lead_flush()
    # хвост (масштаб 1.15 вокруг (256, 300))
    S = lambda pts: [(256 + (x - 256) * 1.15, 300 + (y - 300) * 1.15) for x, y in pts]
    left = [(250, 270), (222, 258), (186, 240), (152, 212), (126, 176), (110, 128),
            (136, 146), (168, 166), (204, 182), (236, 194), (256, 204)]
    right = [(512 - x, y) for x, y in reversed(left)]
    cut = [(110, 128), (176, 190)]  # разрез на две грани
    lf_out = [(152, 212), (126, 176), (110, 128), (136, 146), (168, 166), (190, 177)]
    lf_in = [(256, 270), (222, 258), (186, 240), (152, 212), (190, 177), (204, 182), (236, 194), (256, 204)]
    g.shard(S(lf_out), '#2B3E9E', lw=7)
    g.shard(S(lf_in), '#1B2F7A', lw=7)
    g.shard(S([(512 - x, y) for x, y in lf_out]), '#2B5FA8', lw=7)
    g.shard(S([(512 - x, y) for x, y in lf_in]), '#1B4F8C', lw=7)
    g.shard([(220, hz + 8), (292, hz + 8), (274, 268), (238, 268)], '#14306A', lw=7)
    g.lead_line(S(left + right[1:]), lw=10, closed=True)
    g.lead_flush()
    g.blik(S([(118, 140), (140, 154), (170, 170)]), color='#CFFBF5', w=4, op=0.7)
    g.blik(S([(394, 140), (372, 154), (342, 170)]), color='#CFFBF5', w=4, op=0.7)
    # капли с лопастей
    for (x, y, r) in [(96, 152, 7), (104, 194, 6), (416, 152, 7), (408, 194, 6), (212, 334, 6), (300, 336, 6)]:
        g.circle(x, y, r, '#DDF8F4', lw=0, nolead=True)
    g.lead_flush()
    stars(g, [(90, 70, 8), (420, 72, 8), (256, 66, 7)])
    return g.render()


# =============================================================================
# 4. Стрельчатое окно-витраж с дорогой к горизонту
# =============================================================================
def ic_arch():
    g = new('d', light=(256, 300))
    # стена: тёмные камни
    seeds = poisson((0, 0, 512, 512), lambda x, y: 96, 4, 3000)
    g.mosaic(SQ, seeds, lambda x, y, i: ['#1E1A4A', '#252060', '#1C1E4C', '#272668', '#1A2250'][i % 5], lw=3.0)
    g.glow(256, 300, 260, '#5B3FA0', 0.30)
    g.lead_flush()
    P = arch_params(112, 400, 250, 60, 452, R=226)
    outer = arch_poly(P, 0, n=9, side=3)
    inner = arch_poly(P, 30, n=9, side=3)
    keep = g.light
    g.light = None
    cols = ['#2BC4BA', '#1B4F8C', '#1F9E6B', '#2B3E9E', '#5FD9D0', '#1B7E96']
    for k in range(len(outer)):
        k2 = (k + 1) % len(outer)
        if outer[k][1] >= 451 and outer[k2][1] >= 451:
            continue
        g.shard([outer[k], outer[k2], inner[k2], inner[k]], cols[k % len(cols)], lw=6, grad=False)
    g.light = keep
    hz = 316
    sky = clip_half(inner, 0, hz, 0, 1)
    # ночь + сияние-занавес
    seeds = poisson((112, 60, 400, hz), lambda x, y: 46, 7, 3000, accept=lambda x, y: point_in(sky, x, y))

    def sc(x, y, i):
        R = rnd(x, y, 4)
        ya = 176 + 30 * math.sin(x / 40.0)
        if abs(y - ya) < 30:
            return R.choice(['#2FD0A0', '#38D9B0', '#2BC4BA'])
        if y > 262:
            return R.choice(['#5FD9D0', '#8DEDE2', '#BDF4EE'])
        return R.choice(['#101C5A', '#16296B', '#1B3A86', '#5B3FA0'])
    g.mosaic(sky, seeds, sc, lw=5)
    g.glow(256, hz, 120, '#E8FFFB', 0.55)
    g.lead_flush()
    gr = clip_half(inner, 0, hz, 0, -1)
    for side in (-1, 1):
        c = clip_half(gr, 256, 0, -side, 0)
        g.shard(c, '#17695A' if side < 0 else '#0F4A4A', lw=5)
    road(g, gr, 256, hz, 452, 120, rows=4, m=2, lw=5)
    g.lead_flush()
    g.spark(256, hz - 2, 16, '#FFE2CF', 0.95)       # рассветная искра (персик)
    g.lead_line(outer, lw=10, closed=True)
    g.lead_line(inner, lw=7, closed=True)
    g.lead_flush()
    stars(g, [(196, 112, 7), (318, 120, 6), (256, 92, 6)])
    return g.render()


# =============================================================================
# 5. Компас / роза ветров со стрелкой на север и сиянием
# =============================================================================
def ic_compass():
    g = new('e', light=(256, 80))
    sky_mosaic(g, 5, r=98, aur=[lambda x: (60 + 20 * math.sin(x / 60.0), 40)], span=520)
    g.glow(256, 80, 200, '#2BC4BA', 0.45)
    g.lead_flush()
    cx, cy = 256, 270
    # кольцо
    n = 8
    for i in range(n):
        seg = ring_seg_poly(cx, cy, 150, 182, 360 * i / n - 90, 360 * (i + 1) / n - 90)
        g.shard(seg, ['#1B4F8C', '#2B3E9E'][i % 2], lw=5)
    disk = circle_poly(cx, cy, 150, 40)
    glory(g, cx, cy, disk, n=8, rot=0.39, cols=['#0F2A5C', '#132F66'])
    g.glow(cx, cy, 150, '#2BC4BA', 0.25)
    g.lead_flush()

    def ray(ang, L, wb, cl, cd, lw=7):
        a = math.radians(ang)
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        nx, ny = -math.sin(a), math.cos(a)
        bl = (cx + wb * nx, cy + wb * ny)
        br = (cx - wb * nx, cy - wb * ny)
        g.shard([(cx, cy), tip, bl], cl, lw=lw)
        g.shard([(cx, cy), br, tip], cd, lw=lw)
    for ang in (-45, 45, 135, 225):
        ray(ang, 108, 30, '#5FD9D0', '#1F8FA8', 6)
    ray(90, 152, 46, '#C4F3ED', '#5FB9B4')
    ray(0, 152, 46, '#C4F3ED', '#5FB9B4')
    ray(180, 152, 46, '#C4F3ED', '#5FB9B4')
    ray(-90, 206, 52, '#F78F97', '#C8454F', 8)
    g.circle(cx, cy, 24, MILK, lw=7)
    g.lead_flush()
    g.lead_circle(cx, cy, 183, lw=10)
    g.lead_flush()
    g.spark(cx, cy - 214, 16, '#FFFFFF', 0.95)
    stars(g, [(80, 120, 8), (440, 110, 8), (70, 450, 6), (444, 452, 6)])
    return g.render()


def ring_seg_poly(cx, cy, r0, r1, a0, a1, n=6):
    o = [(cx + r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    i_ = [(cx + r0 * math.cos(math.radians(a1 - (a1 - a0) * i / n)), cy + r0 * math.sin(math.radians(a1 - (a1 - a0) * i / n))) for i in range(n + 1)]
    return o + i_


def rrect(x, y, w, h, r, k=6):
    out = []
    for (cx, cy, a0) in [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)]:
        for j in range(k + 1):
            a = math.radians(a0 + 90 * j / k)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


# =============================================================================
# 6. Рюкзак со скаткой
# =============================================================================
def ic_backpack():
    g = new('f', light=(200, 120))
    sky_mosaic(g, 6, r=98, glow=(256, 250, 230, ['#5FD9D0', '#2BC4BA', '#1F8FA8', '#1B7E96', '#15626E']),
               seq=['#0B2A3A', '#0F3A4A', '#15626E', '#0F3A4A'], span=512)
    g.glow(256, 260, 240, '#8DEDE2', 0.35)
    g.lead_flush()
    # лямки за спиной (по бокам)
    g.shard([(140, 210), (164, 200), (170, 400), (146, 410)], '#2B2048', lw=6)
    g.shard([(372, 210), (348, 200), (342, 400), (366, 410)], '#2B2048', lw=6)
    # корпус
    body = rrect(158, 176, 196, 262, 44)
    top = clip_half(body, 0, 262, 0, 1)
    bot = clip_half(body, 0, 262, 0, -1)
    g.shard(clip_half(top, 256, 0, 1, 0), '#E8706A', lw=7)
    g.shard(clip_half(top, 256, 0, -1, 0), '#DC5E60', lw=7)
    g.shard(clip_half(bot, 256, 0, 1, 0), '#B8404E', lw=7)
    g.shard(clip_half(bot, 256, 0, -1, 0), '#A23547', lw=7)
    # клапан
    flap = [(166, 200), (190, 180), (322, 180), (346, 200), (346, 252), (300, 268), (212, 268), (166, 252)]
    g.shard(flap, '#F07E7E', lw=7)
    # карман
    pk = rrect(192, 316, 128, 100, 22)
    g.shard(clip_half(pk, 256, 0, 1, 0), '#932F46', lw=6)
    g.shard(clip_half(pk, 256, 0, -1, 0), '#7E2633', lw=6)
    g.shard([(214, 316), (298, 316), (298, 336), (214, 336)], '#C8454F', lw=5)
    # ремешки клапана с пряжками
    for x in (214, 298):
        g.shard([(x - 9, 240), (x + 9, 240), (x + 9, 300), (x - 9, 300)], '#2B2048', lw=5, grad=False)
        g.shard([(x - 13, 266), (x + 13, 266), (x + 13, 282), (x - 13, 282)], '#BFCBEA', lw=4, grad=False)
    # скатка
    g.shard(rrect(136, 112, 240, 70, 34), '#34D1C6', lw=7)
    g.shard([(150, 142), (362, 142), (362, 152), (150, 152)], '#1FA7A2', lw=4, grad=False, nolead=True)
    for x in (196, 316):
        g.shard([(x - 9, 108), (x + 9, 108), (x + 9, 186), (x - 9, 186)], '#2B2048', lw=5, grad=False)
    g.shard(ellipse_poly(370, 147, 14, 33, 20), '#8DF1E9', lw=6)
    g.shard(ellipse_poly(370, 147, 6, 14, 14), '#1FA7A2', lw=3)
    # ручка
    g.lead_line([(232, 112), (240, 88), (272, 88), (280, 112)], lw=9)
    g.lead_flush()
    g.lead_line(body, lw=10, closed=True)
    g.lead_flush()
    g.blik([(176, 230), (176, 300), (182, 380)], color='#FFE0DA', w=5, op=0.55)
    g.blik([(160, 130), (210, 120), (260, 118)], color='#E8FFFB', w=5, op=0.7)
    stars(g, [(90, 90, 9), (430, 84, 8), (440, 300, 6), (70, 330, 6)])
    return g.render()


# =============================================================================
# 7. Спасская башня -> маяк: путь от одного к другому
# =============================================================================
def ic_tower_light():
    g = new('g', light=(380, 140))
    sky_mosaic(g, 7, r=98, aur=[lambda x: (100 + 0.18 * (x - 256) + 26 * math.sin(x / 55.0), 30)], span=440)
    g.lead_flush()
    # земля / море
    gr = clip_half(SQ, 0, 392, 0, -1)
    g.shard(clip_half(gr, 300, 0, 1, 0), '#145A52', lw=5)
    g.shard(clip_half(gr, 300, 0, -1, 0), '#14407E', lw=5)
    g.lead_flush()
    # маршрут: пунктир-дуга от башни к маяку
    pts = []
    for i in range(13):
        t = i / 12
        x = 168 + (372 - 168) * t
        y = 428 + 40 * math.sin(math.pi * t) - 46 * t
        pts.append((x, y))
    for i in range(0, 12, 2):
        q, _ = chain_quads([pts[i], pts[i + 1]], [22, 22])
        g.shard(q[0], ROADC[(i // 2) % 4], lw=4)
    # Спасская башня (рубин): основание, ярусы, шатёр, звезда
    T = [
        ([(96, 438), (200, 438), (200, 300), (96, 300)], '#A23547'),
        ([(106, 300), (190, 300), (190, 238), (106, 238)], '#C8454F'),
        ([(116, 238), (180, 238), (180, 196), (116, 196)], '#B8404E'),
        ([(122, 196), (174, 196), (148, 92)], '#2B8F6B'),
    ]
    for p, c in T:
        g.shard(p, c, lw=7)
    g.circle(148, 266, 18, MILK, lw=5)
    g.shard([(132, 438), (164, 438), (164, 392), (148, 378), (132, 392)], '#2B2048', lw=5, grad=False)
    g.shard([(148, 64), (156, 80), (172, 82), (160, 92), (164, 108), (148, 99), (132, 108), (136, 92), (124, 82), (140, 80)], '#F07E7E', lw=4)
    # маяк (молочный с бирюзовыми полосами)
    lx = 380
    sh = [(lx - 30, 386), (lx + 30, 386), (lx + 20, 214), (lx - 20, 214)]
    bands = [386, 330, 274, 214]
    for k in range(3):
        ya, yb = bands[k], bands[k + 1]
        wa = 30 - (386 - ya) * 10 / 172
        wb = 30 - (386 - yb) * 10 / 172
        g.shard([(lx - wa, ya), (lx + wa, ya), (lx + wb, yb), (lx - wb, yb)], [MILK, '#2BC4BA', MILK][k], lw=7)
    g.shard([(lx - 26, 214), (lx + 26, 214), (lx + 26, 202), (lx - 26, 202)], '#2B2048', lw=5, grad=False)
    g.shard([(lx - 16, 202), (lx + 16, 202), (lx + 16, 172), (lx - 16, 172)], '#FFD7B0', lw=6)
    g.shard([(lx - 22, 172), (lx + 22, 172), (lx, 146)], '#C8454F', lw=6)
    g.lead_flush()
    g.glow(lx, 187, 80, '#FFE2CF', 0.5)
    g.lead_flush()
    stars(g, [(256, 80, 8), (440, 70, 7), (60, 180, 6)])
    return g.render()


# =============================================================================
# 8. Клубок Бабы-яги: нить становится дорогой
# =============================================================================
def ic_ball():
    g = new('h', light=(300, 160))
    sky_mosaic(g, 8, r=98, aur=[lambda x: (110 + 30 * math.sin(x / 64.0 + 1), 32)], seq=['#0B1244', '#16296B', '#2A2266', '#3A2C80'], span=360)
    hz = 214
    for (x0, xp, yp, x1, c1, c2) in [(216, 290, 168, 372, '#1E8296', '#165B78'), (380, 446, 156, 512, '#1B7E96', '#14566F')]:
        g.shard([(x0, hz), (xp, yp), (xp + 6, hz)], c1, lw=5)
        g.shard([(xp, yp), (x1, hz), (xp + 6, hz)], c2, lw=5)
    gr = clip_half(SQ, 0, hz, 0, -1)
    gs = poisson((0, hz, 512, 512), lambda x, y: 70 + (y - hz) * 0.3, 8, 1200)
    g.mosaic(gr, gs, lambda x, y, i: ['#124A4A', '#0F4046', '#145450', '#11444E'][i % 4], lw=4.5)
    g.glow(372, hz, 120, '#E8FFFB', 0.55)
    g.lead_flush()
    # нить-дорога: от клубка к горизонту
    pts = bez([(296, 384), (420, 410), (446, 300), (372, hz + 2)], 12)
    wid = [(18 + 22 * i / 3) if i <= 3 else (40 - 37 * ((i - 3) / 9) ** 0.8) for i in range(13)]
    ribbon(g, pts, wid, ['#C4F3ED', '#5FD9D0', '#E4FBF6', '#8DEDE2'], lw=5)
    g.lead_line(pts, lw=0)
    g.lead_flush()
    # клубок
    cx, cy, r = 196, 336, 118
    ang = math.radians(-34)

    def T(u, v):
        return (cx + u * math.cos(ang) - v * math.sin(ang), cy + u * math.sin(ang) + v * math.cos(ang))

    def curve(v0, bow=0.0022, n=18):
        return [T(-r - 6 + 2 * (r + 6) * i / n, v0 + bow * (-r - 6 + 2 * (r + 6) * i / n) ** 2) for i in range(n + 1)]
    edges = [-170, -110, -66, -26, 12, 52, 96, 160]
    cols = ['#E0556B', '#C8454F', '#F07E7E', '#A23547', '#E0556B', '#B8404E', '#8C2A3C']
    circ = circle_poly(cx, cy, r, 48)
    for i in range(len(edges) - 1):
        band = curve(edges[i]) + list(reversed(curve(edges[i + 1])))
        c = clip_convex(band, circ)
        if len(c) >= 3:
            g.shard(c, cols[i], lw=6)
    g.lead_flush()
    g.lead_circle(cx, cy, r, lw=11)
    g.lead_flush()
    g.blik([(110, 300), (128, 258), (160, 232)], color='#FFE6E6', w=7, op=0.6)
    stars(g, [(80, 70, 9), (300, 64, 7), (452, 96, 8)])
    return g.render()


# =============================================================================
# 9. Монограмма «П»: витражная арка, внутри дорога
# =============================================================================
def ic_monogram():
    g = new('i', light=(256, 300))
    sky_mosaic(g, 9, r=102, seq=['#0B1244', '#101C5A', '#16296B', '#101C5A'], span=512)
    g.glow(256, 260, 250, '#2B3E9E', 0.4)
    g.lead_flush()
    x0, x1, xi0, xi1, yt, yb = 114, 398, 194, 318, 88, 430
    P = arch_params(xi0, xi1, 206, 140, yb, R=96)
    inner = arch_poly(P, 0, n=8, side=3)
    hz = 322
    # внутри: небо с сиянием, дорога
    sky = clip_half(inner, 0, hz, 0, 1)
    seeds = poisson((xi0, 100, xi1, hz), lambda x, y: 40, 9, 3000, accept=lambda x, y: point_in(sky, x, y))

    def sc(x, y, i):
        R = rnd(x, y, 9)
        if y > 270:
            return R.choice(['#8DEDE2', '#BDF4EE', '#5FD9D0'])
        if y > 200:
            return R.choice(['#2FD0A0', '#38D9B0', '#2BC4BA'])
        return R.choice(['#1F9E6B', '#5B3FA0', '#2B3E9E'])
    g.mosaic(sky, seeds, sc, lw=5)
    g.glow(256, hz, 90, '#E8FFFB', 0.6)
    g.lead_flush()
    gr = clip_half(inner, 0, hz, 0, -1)
    for side in (-1, 1):
        g.shard(clip_half(gr, 256, 0, -side, 0), '#17695A' if side < 0 else '#0F4A4A', lw=5)
    road(g, gr, 256, hz, yb, 60, rows=3, m=1, lw=5)
    g.lead_flush()
    # дорога выходит из арки вниз, до края
    g.shard([(256 - 61.5, yb), (256 + 61.5, yb), (256 + 92, 512), (256 - 92, 512)], '#C4F3ED', lw=7)
    g.lead_flush()
    # тело буквы — молочное/бирюзовое стекло
    arc = [p for p in inner if p[1] <= 206.5]
    larc = [p for p in arc if p[0] <= 256.01]
    rarc = [p for p in arc if p[0] >= 255.99]
    larc.sort(key=lambda p: p[0])
    rarc.sort(key=lambda p: p[0])
    LC = ['#EDE6D2', '#C4F3ED', '#8DEDE2', '#EDE6D2']
    ov = 26
    g.shard([(x0 - ov, yt), (256, yt), (256, larc[-1][1])] + list(reversed(larc)) + [(xi0, 206), (x0, 206), (x0, 168), (x0 - ov, 168)], '#EDE6D2', lw=7)
    g.shard([(256, yt), (x1 + ov, yt), (x1 + ov, 168), (x1, 168), (x1, 206), (xi1, 206)] + list(reversed(rarc)) + [(256, rarc[0][1])], '#DDF6F1', lw=7)
    g.shard([(x0, 206), (xi0, 206), (xi0, 318), (x0, 318)], '#8DEDE2', lw=7)
    g.shard([(x0, 318), (xi0, 318), (xi0, yb), (x0, yb)], '#5FD9D0', lw=7)
    g.shard([(xi1, 206), (x1, 206), (x1, 318), (xi1, 318)], '#EDE6D2', lw=7)
    g.shard([(xi1, 318), (x1, 318), (x1, yb), (xi1, yb)], '#8DEDE2', lw=7)
    g.lead_flush()
    outline = [(x0, yt), (x1, yt), (x1, yb), (xi1, yb)] + [p for p in reversed(inner)][1:-1] + [(xi0, yb), (x0, yb)]
    g.lead_line([(x0 - ov, 168), (x0 - ov, yt), (x1 + ov, yt), (x1 + ov, 168), (x1, 168), (x1, yb), (xi1, yb)], lw=12)
    g.lead_line([(x0 - ov, 168), (x0, 168), (x0, yb), (xi0, yb)], lw=12)
    g.lead_line(inner, lw=10, closed=True)
    g.lead_flush()
    g.blik([(120, 300), (120, 190)], color='#FFFFFF', w=5, op=0.6)
    g.blik([(96, 150), (96, 104), (240, 100)], color='#FFFFFF', w=5, op=0.6)
    stars(g, [(256, 238, 8)])
    stars(g, [(64, 64, 8), (452, 64, 8), (60, 470, 6), (452, 470, 6)])
    return g.render()


# =============================================================================
# 10. Сияние-тропа от костра над избой
# =============================================================================
def ic_izba():
    g = new('j', light=(260, 140))
    sky_mosaic(g, 10, r=98, seq=['#0B1244', '#101C5A', '#16296B', '#1B3A86'], span=480)
    g.lead_flush()
    # снег
    gr = clip_half(SQ, 0, 408, 0, -1)
    gs = poisson((0, 410, 512, 512), lambda x, y: 70, 10, 800)
    g.mosaic(gr, gs, lambda x, y, i: ['#9AB5CE', '#C9DCEC', '#7F97AD', '#B5CCE0'][i % 4], lw=4.5)
    g.lead_flush()
    # сияние-тропа: из костра вверх и вдаль
    pts = bez([(372, 400), (430, 300), (330, 196), (200, 168), (90, 70)], 12)
    wid = [36 + 54 * math.sin(math.pi * min(1, i / 8)) ** 0.7 if i < 4 else 90 - 82 * ((i - 4) / 8) for i in range(13)]
    quads = ribbon(g, pts, wid, ['#1F9E6B', '#2BC4BA', '#2FD0A0', '#38D9B0', '#1F9E6B', '#2BC4BA', '#5B3FA0'], lw=5)
    for i in range(1, 11, 2):
        q, _ = chain_quads([pts[i], lerp(pts[i], pts[i + 1], 0.6)], [wid[i] * 0.16, wid[i + 1] * 0.16])
        g.shard(q[0], '#E4FBF6', lw=3)
    g.glow(330, 240, 150, '#8DEDE2', 0.25)
    g.lead_flush()
    # изба
    g.shard([(110, 418), (270, 418), (270, 300), (110, 300)], '#2B2A72', lw=7)
    for y in (330, 360, 390):
        g.lead_line([(110, y), (270, y)], lw=4)
    g.shard([(166, 330), (214, 330), (214, 384), (166, 384)], '#F0A24A', lw=6)
    g.lead_line([(190, 330), (190, 384)], lw=5)
    g.lead_line([(166, 357), (214, 357)], lw=5)
    g.shard([(94, 306), (190, 214), (190, 306)], '#8C2A3C', lw=7)
    g.shard([(190, 214), (286, 306), (190, 306)], '#A23547', lw=7)
    g.shard([(88, 304), (190, 206), (190, 222), (104, 306)], '#EDE6D2', lw=5)
    g.shard([(292, 304), (190, 206), (190, 222), (276, 306)], '#DDE8F2', lw=5)
    g.lead_flush()
    g.glow(190, 357, 70, '#F0A24A', 0.35)
    g.glow(370, 400, 80, '#F0957A', 0.5)
    g.lead_flush()
    # костёр
    g.shard([(326, 426), (414, 426), (408, 440), (332, 440)], '#4B3A5E', lw=5)
    g.shard([(336, 426), (352, 384), (366, 404), (372, 352), (392, 400), (400, 388), (404, 426)], '#E0556B', lw=5)
    g.shard([(354, 426), (366, 400), (372, 384), (380, 404), (388, 426)], '#FFB79B', lw=4)
    g.lead_flush()
    stars(g, [(436, 90, 8), (300, 72, 7), (460, 200, 6), (60, 220, 6)])
    return g.render()


ICONS = [
    ('01', 'walker', ic_walker),
    ('02', 'footprint', ic_footprint),
    ('03', 'whale', ic_whale),
    ('04', 'arch', ic_arch),
    ('05', 'compass', ic_compass),
    ('06', 'backpack', ic_backpack),
    ('07', 'tower_lighthouse', ic_tower_light),
    ('08', 'ball', ic_ball),
    ('09', 'monogram', ic_monogram),
    ('10', 'aurora_izba', ic_izba),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    for num_, slug, fn in ICONS:
        if only and num_ not in only:
            continue
        svg = fn()
        name = f'icon_{num_}_{slug}.svg'
        size, probs = check_svg(name, svg, limit=40 * 1024)
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            fh.write(svg)
        print(f'{name}: {size} B', 'OK' if not probs else probs)


if __name__ == '__main__':
    main()

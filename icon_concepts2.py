#!/usr/bin/env python3
"""20 комбинированных концепций иконки «Путника» (11–30): роза ветров, сияние, костёр, хвост кита, маяк.

python3 tools/art/icon_concepts2.py [outdir] [11,12,...]   (по умолчанию /home/claude/out/icons2)

512×512, фон на весь квадрат, главный силуэт — в центральных 66% (x, y ∈ [87, 425]).
Только элементы flutter_svg. Инструменты — hero_glass_lib.Glass и icon_concepts.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv
sys.argv = sys.argv[:1]
from icon_concepts import (new, sky_mosaic, ribbon, bez, stars, ring_seg_poly, rnd, SQ, AUR, ROADC)  # noqa: E402
sys.argv = _argv
from hero_glass_lib import *  # noqa: F401,F403,E402
from hero_glass import glory, point_in  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1][0].isdigit() else '/home/claude/out/icons2'
SAFE = (87, 425)

TAILC = ('#2B3E9E', '#1B2F7A', '#2B5FA8', '#1B4F8C', '#14306A')
LH_MILK = '#ECE6D6'
LH_RED = '#C8454F'
LAMP = '#FFD9BE'


# ---------------------------------------------------------------- примитивы
def quad(p0, p1, w0, w1=None):
    w1 = w0 if w1 is None else w1
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    return [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
            (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]


def tail_geom(cx, yb, s):
    """Хвост кита: s — полуразмах (px), yb — уровень воды. Верх ≈ yb − 1.38·s."""
    P = lambda pts: [(cx + (x - 256) / 146 * s, yb + (y - 330) / 146 * s) for x, y in pts]
    left = [(250, 270), (222, 258), (186, 240), (152, 212), (126, 176), (110, 128),
            (136, 146), (168, 166), (204, 182), (236, 194), (256, 204)]
    right = [(512 - x, y) for x, y in reversed(left)]
    lo = [(152, 212), (126, 176), (110, 128), (136, 146), (168, 166), (190, 177)]
    li = [(256, 272), (222, 258), (186, 240), (152, 212), (190, 177), (204, 182), (236, 194), (256, 204)]
    ro = [(512 - x, y) for x, y in lo]
    ri = [(512 - x, y) for x, y in li]
    stalk = [(220, 338), (292, 338), (274, 266), (238, 266)]
    outline = left + right[1:]
    return dict(lo=P(lo), li=P(li), ro=P(ro), ri=P(ri), stalk=P(stalk), outline=P(outline),
                blikL=P([(118, 140), (140, 154), (170, 170)]), blikR=P([(394, 140), (372, 154), (342, 170)]),
                tipL=P([(108, 150)])[0], tipR=P([(404, 150)])[0])


def draw_tail(g, cx, yb, s, cols=TAILC, lw=7, olw=10, blik=True, drops=True):
    t = tail_geom(cx, yb, s)
    g.shard(t['lo'], cols[0], lw=lw)
    g.shard(t['li'], cols[1], lw=lw)
    g.shard(t['ro'], cols[2], lw=lw)
    g.shard(t['ri'], cols[3], lw=lw)
    g.shard(t['stalk'], cols[4], lw=lw)
    g.lead_line(t['outline'], lw=olw, closed=True)
    g.lead_flush()
    if blik:
        g.blik(t['blikL'], color='#CFFBF5', w=max(2, s / 30), op=0.7)
        g.blik(t['blikR'], color='#CFFBF5', w=max(2, s / 30), op=0.7)
    if drops:
        k = s / 146
        for (x, y) in (t['tipL'], t['tipR']):
            g.circle(x, y + 14 * k, 6 * k, '#DDF8F4', lw=0, nolead=True)
            g.circle(x + (4 if x > cx else -4) * k, y + 44 * k, 5 * k, '#DDF8F4', lw=0, nolead=True)
    return t


def lighthouse(g, x, yb, yt, wb, wt, bands=4, cols=(LH_MILK, LH_RED), lw=7, lamp=LAMP, roof='#8C2A3C', glow=True):
    """Маяк: башня с полосами, галерея, фонарь, крыша. Возвращает центр фонаря."""
    H = yb - yt
    yg = yt + H * 0.30
    for k in range(bands):
        ya = yb - (yb - yg) * k / bands
        yb2 = yb - (yb - yg) * (k + 1) / bands
        wa = wb + (wt - wb) * (yb - ya) / (yb - yg)
        wc = wb + (wt - wb) * (yb - yb2) / (yb - yg)
        q = [(x - wa / 2, ya), (x + wa / 2, ya), (x + wc / 2, yb2), (x - wc / 2, yb2)]
        g.shard(clip_half(q, x, 0, 1, 0), cols[k % 2], lw=lw)
        g.shard(clip_half(q, x, 0, -1, 0), darken(cols[k % 2], 0.12), lw=lw)
    gw = wt * 1.45
    gh = H * 0.045
    g.shard([(x - gw / 2, yg), (x + gw / 2, yg), (x + gw / 2, yg - gh), (x - gw / 2, yg - gh)], '#2B2048', lw=lw * 0.8, grad=False)
    lw_ = wt * 0.78
    ly0, ly1 = yg - gh, yt + H * 0.10
    g.shard([(x - lw_ / 2, ly0), (x + lw_ / 2, ly0), (x + lw_ / 2, ly1), (x - lw_ / 2, ly1)], lamp, lw=lw * 0.8, grad=False)
    g.lead_line([(x, ly0), (x, ly1)], lw=lw * 0.55)
    rw = wt * 1.05
    g.shard([(x - rw / 2, ly1), (x + rw / 2, ly1), (x, yt)], roof, lw=lw * 0.8)
    g.lead_flush()
    lc = (x, (ly0 + ly1) / 2)
    if glow:
        g.glow(lc[0], lc[1], H * 0.42, '#FFE6D6', 0.55)
        g.lead_flush()
    return lc


def beam(g, src, ang, length, spread, color='#E8FFFB', op=0.32):
    a0, a1 = math.radians(ang - spread / 2), math.radians(ang + spread / 2)
    p = [src, (src[0] + length * math.cos(a0), src[1] + length * math.sin(a0)),
         (src[0] + length * math.cos(a1), src[1] + length * math.sin(a1))]
    c = clip_convex(p, SQ)
    g.flush()
    gr = g.linear([(0, color, op), (1, color, 0.02)], 0, 0, 1, 0) if math.cos(math.radians(ang)) >= 0 else g.linear([(0, color, 0.02), (1, color, op)], 0, 0, 1, 0)
    g.shard(c, gr, lw=0, grad=False, nolead=True)


FLAME = [(-0.42, 0), (-0.47, -0.28), (-0.31, -0.50), (-0.27, -0.73), (-0.12, -0.60), (0.0, -1.0),
         (0.14, -0.64), (0.27, -0.80), (0.31, -0.52), (0.45, -0.30), (0.42, 0)]


def campfire(g, cx, yb, h, lw=6, logs=True):
    """Костёр: h — высота пламени."""
    w = h * 0.95
    F = lambda pts, k, dy=0: [(cx + x * w * k, yb + dy + y * h * k) for x, y in pts]
    g.glow(cx, yb - h * 0.4, h * 1.25, '#F0957A', 0.5)
    g.lead_flush()
    outer = F(FLAME, 1.0)
    g.shard(clip_half(outer, cx, 0, 1, 0), '#E0556B', lw=lw)
    g.shard(clip_half(outer, cx, 0, -1, 0), '#C8454F', lw=lw)
    g.shard(F(FLAME, 0.66), '#F07E7E', lw=lw * 0.8)
    g.shard(F([(-0.30, 0), (-0.22, -0.40), (0, -0.85), (0.22, -0.40), (0.30, 0)], 0.62), '#FFC2A8', lw=lw * 0.7)
    if logs:
        g.shard(quad((cx - w * 0.62, yb + h * 0.10), (cx + w * 0.58, yb - h * 0.02), h * 0.13), '#4B3A5E', lw=lw)
        g.shard(quad((cx + w * 0.62, yb + h * 0.10), (cx - w * 0.58, yb - h * 0.02), h * 0.13), '#3A2C50', lw=lw)
    g.lead_flush()
    for (dx, dy, r) in [(-0.55, -0.95, 0.035), (0.6, -1.05, 0.03), (0.2, -1.25, 0.025)]:
        g.spark(cx + dx * w, yb + dy * h, r * h * 2, '#FFC9A8', 0.95)


def rose(g, cx, cy, rN, rC, rD, wN, wC, wD, colN=('#F78F97', '#C8454F'), colC=('#C4F3ED', '#5FB9B4'),
         colD=('#5FD9D0', '#1F8FA8'), lw=7, south=True, west=True, east=True, center=True):
    def ray(ang, L, wb, cl, cd, lw_):
        a = math.radians(ang)
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        nx, ny = -math.sin(a), math.cos(a)
        bl = (cx + wb * nx, cy + wb * ny)
        br = (cx - wb * nx, cy - wb * ny)
        g.shard([(cx, cy), tip, bl], cl, lw=lw_)
        g.shard([(cx, cy), br, tip], cd, lw=lw_)
    if rD:
        for ang in (-45, 45, 135, 225):
            ray(ang, rD, wD, colD[0], colD[1], lw * 0.85)
    if south:
        ray(90, rC, wC, *colC, lw)
    if east:
        ray(0, rC, wC, *colC, lw)
    if west:
        ray(180, rC, wC, *colC, lw)
    ray(-90, rN, wN, *colN, lw)
    if center:
        g.circle(cx, cy, max(10, wC * 0.5), MILK, lw=lw)
    g.lead_flush()


def ring(g, cx, cy, r0, r1, n, cols, lw=5, rot=-90):
    for i in range(n):
        g.shard(ring_seg_poly(cx, cy, r0, r1, rot + 360 * i / n, rot + 360 * (i + 1) / n), cols[i % len(cols)], lw=lw)


def sea(g, hz, region=SQ, ybot=512, cols=('#14407E', '#1B4F8C', '#123A73', '#1B3A86'), rows=None, lw=4.5):
    rows = rows or [hz, hz + (ybot - hz) * 0.22, hz + (ybot - hz) * 0.5, ybot]
    for k in range(len(rows) - 1):
        ya, yb = rows[k], rows[k + 1]
        xs = [-10, 150 - k * 26, 362 + k * 26, 522]
        for i in range(3):
            q = [(xs[i], ya), (xs[i + 1], ya), (xs[i + 1] + (i - 1) * 12, yb), (xs[i] + (i - 1) * 12, yb)]
            q = clip_convex(q, region)
            if len(q) >= 3 and area(q) > 10:
                g.shard(q, cols[(i + k) % len(cols)], lw=lw)


def night(g, seed, aur=None, glow=None, seq=None, r=110, span=440):
    kw = dict(r=r, aur=aur, glow=glow, span=span)
    if seq:
        kw['seq'] = seq
    sky_mosaic(g, seed, **kw)


def dim_top(g, y1=240, op=0.9):
    g.flush()
    nt = g.linear([(0, '#0B1424', op), (0.55, '#0B1424', op * 0.35), (1, '#0B1424', 0)], 0, 0, 0, 1)
    g.shard(rect_poly(0, 0, 512, y1), nt, lw=0, grad=False, nolead=True)


def aur_wave(y0, amp, per, h, ph=0.0):
    return lambda x: (y0 + amp * math.sin(x / per + ph), h)


# ======================================================================== 11–30
def ic11():  # кит + маяк на мысу
    g = new('k', light=(200, 160))
    night(g, 11, aur=[aur_wave(96, 26, 60, 30)])
    hz = 336
    sea(g, hz)
    g.lead_flush()
    beam(g, (186, 170), -12, 360, 22)
    beam(g, (186, 170), 192, 260, 18, op=0.22)
    g.shard([(70, hz + 6), (110, 316), (170, 300), (240, 306), (282, 330), (300, hz + 30), (60, hz + 40)], '#1F2A5E', lw=7)
    g.shard([(110, 316), (170, 300), (200, 318), (130, 330)], '#2B3E9E', lw=5)
    g.lead_flush()
    lighthouse(g, 186, 312, 104, 74, 46, bands=4)
    draw_tail(g, 356, hz + 4, 66)
    for k, (ya, yb, wa, wb) in enumerate([(hz + 18, hz + 40, 16, 26), (hz + 48, hz + 84, 32, 46), (hz + 94, 512, 56, 86)]):
        g.shard([(356 - wa, ya), (356 + wa, ya), (356 + wb, yb), (356 - wb, yb)], ROADC[k % 4], lw=4.5)
    g.lead_flush()
    stars(g, [(430, 70, 8), (300, 64, 6), (70, 200, 6)])
    return g.render()


def ic12():  # роза ветров, в центре хвост кита
    g = new('l', light=(256, 200))
    night(g, 12, aur=[aur_wave(60, 18, 60, 36)], span=520)
    cx, cy = 256, 262
    g.glow(cx, cy, 200, '#2BC4BA', 0.3)
    g.lead_flush()
    for ang, L, hw, col in [(-90, 172, 30, ('#F78F97', '#C8454F')), (0, 164, 24, ('#C4F3ED', '#5FB9B4')), (90, 164, 24, ('#C4F3ED', '#5FB9B4')),
                            (180, 164, 24, ('#C4F3ED', '#5FB9B4'))] + [(a, 154, 16, ('#5FD9D0', '#1F8FA8')) for a in (-45, 45, 135, 225)]:
        a = math.radians(ang)
        nx, ny = -math.sin(a), math.cos(a)
        b = (cx + 128 * math.cos(a), cy + 128 * math.sin(a))
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        g.shard([(b[0] + hw * nx, b[1] + hw * ny), tip, b], col[0], lw=6)
        g.shard([b, tip, (b[0] - hw * nx, b[1] - hw * ny)], col[1], lw=6)
    g.lead_flush()
    disk = circle_poly(cx, cy, 112, 44)
    glory(g, cx, cy + 40, clip_half(disk, 0, cy + 40, 0, 1), n=10, rot=0.1, cols=['#BDF4EE', '#5FD9D0', '#8DEDE2', '#2BC4BA'])
    g.glow(cx, cy + 20, 110, '#E8FFFB', 0.5)
    sea(g, cy + 40, region=disk, cols=('#14407E', '#1B4F8C', '#123A73'), rows=[cy + 40, cy + 70, cy + 120])
    g.lead_flush()
    ring(g, cx, cy, 112, 134, 8, ['#1B4F8C', '#2B3E9E'], lw=6)
    g.lead_flush()
    draw_tail(g, cx, cy + 44, 80, olw=9)
    g.lead_circle(cx, cy, 135, lw=10)
    g.lead_circle(cx, cy, 112, lw=7)
    g.lead_flush()
    stars(g, [(80, 120, 8), (440, 110, 8), (70, 440, 6), (444, 446, 6)])
    return g.render()


def ic13():  # маяк, луч которого становится сиянием
    g = new('m', light=(300, 160))
    night(g, 13, seq=['#0B1244', '#101C5A', '#152668', '#1A3278'])
    hz = 404
    sea(g, hz)
    g.shard([(40, 520), (60, 420), (120, 396), (220, 400), (260, 430), (280, 520)], '#1F2A5E', lw=7)
    g.lead_flush()
    lc = (168, 176)
    pts = bez([(lc[0] + 20, lc[1]), (290, 140), (360, 220), (420, 130), (410, 84)], 12)
    wid = [14 + 5.5 * i for i in range(13)]
    ribbon(g, pts, wid, ['#E4FBF6', '#BDF4EE', '#8DEDE2', '#38D9B0', '#2BC4BA', '#2FD0A0', '#1F9E6B', '#5B3FA0'], lw=5)
    g.glow(300, 160, 150, '#8DEDE2', 0.22)
    g.lead_flush()
    lighthouse(g, 168, 410, 120, 80, 48, bands=4)
    stars(g, [(80, 80, 8), (250, 70, 6), (460, 260, 6)])
    return g.render()


def ic14():  # костёр на берегу, сияние, кит в море
    g = new('n', light=(256, 300))
    night(g, 14, aur=[aur_wave(110, 30, 58, 34), aur_wave(176, 16, 44, 14, 1.2)], span=330)
    hz = 300
    sea(g, hz, ybot=400, rows=[hz, 330, 370, 400])
    g.lead_flush()
    draw_tail(g, 370, hz + 4, 50, olw=8, lw=6)
    gs = poisson((0, 392, 512, 512), lambda x, y: 80, 14, 800)
    g.mosaic(clip_half(SQ, 0, 392, 0, -1), gs, lambda x, y, i: ['#9AB5CE', '#C9DCEC', '#7F97AD', '#B5CCE0'][i % 4], lw=4)
    g.lead_line([(0, 392), (512, 392)], lw=7)
    g.lead_flush()
    campfire(g, 214, 404, 170, lw=7)
    stars(g, [(80, 70, 8), (430, 60, 7), (300, 240, 5)])
    return g.render()


def ic15():  # роза ветров-иллюминатор, внутри маяк
    g = new('o', light=(256, 200))
    night(g, 15, seq=['#0D1650', '#111D5C', '#152668', '#111D5C'], span=512)
    cx, cy = 256, 262
    g.glow(cx, cy, 220, '#2B3E9E', 0.4)
    g.lead_flush()
    disk = circle_poly(cx, cy, 124, 48)
    seeds = poisson((132, 138, 380, 320), lambda x, y: 44, 15, 3000, accept=lambda x, y: point_in(disk, x, y) and y < 318)

    def sc(x, y, i):
        R = rnd(x, y, 15)
        ya = 200 + 18 * math.sin(x / 30.0)
        if abs(y - ya) < 26:
            return R.choice(['#2FD0A0', '#38D9B0', '#2BC4BA'])
        return R.choice(['#101C5A', '#16296B', '#1B3A86'])
    g.mosaic(clip_half(disk, 0, 320, 0, 1), seeds, sc, lw=4)
    sea(g, 320, region=disk, rows=[320, 345, 400])
    g.lead_flush()
    lc = lighthouse(g, cx, 352, 160, 50, 32, bands=4, lw=6, glow=False)
    beam(g, lc, -8, 140, 20, op=0.45)
    beam(g, lc, 188, 140, 20, op=0.45)
    g.glow(lc[0], lc[1], 60, '#FFE6D6', 0.6)
    g.lead_flush()
    ring(g, cx, cy, 124, 156, 16, ['#5FB9B4', '#1F8FA8'], lw=5)
    for ang, L, col in [(-90, 172, ('#F78F97', '#C8454F')), (0, 166, ('#C4F3ED', '#5FB9B4')), (90, 166, ('#C4F3ED', '#5FB9B4')), (180, 166, ('#C4F3ED', '#5FB9B4'))]:
        a = math.radians(ang)
        nx, ny = -math.sin(a), math.cos(a)
        b = (cx + 140 * math.cos(a), cy + 140 * math.sin(a))
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        g.shard([(b[0] + 22 * nx, b[1] + 22 * ny), tip, b], col[0], lw=6)
        g.shard([b, tip, (b[0] - 22 * nx, b[1] - 22 * ny)], col[1], lw=6)
    g.lead_flush()
    g.lead_circle(cx, cy, 157, lw=10)
    g.lead_circle(cx, cy, 124, lw=8)
    g.lead_flush()
    stars(g, [(70, 70, 8), (446, 72, 8), (70, 450, 6), (444, 450, 6)])
    return g.render()


def ic16():  # стрелка компаса-маяк
    g = new('p', light=(256, 140))
    night(g, 16, aur=[aur_wave(80, 24, 64, 34)], span=520)
    cx, cy = 256, 270
    g.glow(cx, 150, 200, '#2BC4BA', 0.3)
    g.lead_flush()
    ring(g, cx, cy, 144, 160, 24, ['#1B4F8C', '#2B3E9E'], lw=4)
    g.lead_circle(cx, cy, 161, lw=8)
    g.lead_circle(cx, cy, 144, lw=6)
    g.lead_flush()
    beam(g, (cx, 142), -10, 260, 18, op=0.4)
    beam(g, (cx, 142), 190, 260, 18, op=0.4)
    # южная половина
    g.shard([(cx - 46, cy), (cx, cy), (cx, 420)], "#C4F3ED", lw=7)
    g.shard([(cx, cy), (cx + 46, cy), (cx, 420)], "#5FB9B4", lw=7)
    # северная половина — маяк
    lighthouse(g, cx, cy, 92, 92, 52, bands=3, lw=8)
    g.circle(cx, cy, 15, MILK, lw=6)
    g.lead_flush()
    stars(g, [(80, 120, 8), (436, 120, 8), (80, 440, 6), (436, 440, 6)])
    return g.render()


def ic17():  # хвост кита из языков сияния
    g = new('q', light=(256, 200))
    night(g, 17, seq=['#0B1244', '#0E1850', '#121F5C', '#16296B'], span=480)
    hz = 380
    g.glow(256, 280, 220, '#2BC4BA', 0.28)
    g.lead_flush()
    sea(g, hz, cols=('#123A73', '#14407E', '#0F2C5C', '#1B3A86'))
    g.lead_flush()
    t = tail_geom(256, hz + 4, 150)
    top = t['outline']
    ymin = min(y for _, y in top)
    layers = [(ymin - 5, ymin + 34, '#F78F97'), (ymin + 34, ymin + 80, '#BDF4EE'), (ymin + 80, ymin + 130, '#38D9B0'),
              (ymin + 130, ymin + 180, '#2FD0A0'), (ymin + 180, 520, '#1F9E6B')]
    for part in ('lo', 'li', 'ri', 'ro', 'stalk'):
        poly = t[part]
        for (y0, y1, cl) in layers:
            c = clip_convex(poly, [(0, y0), (512, y0 + 30), (512, y1 + 30), (0, y1)] if part in ('ro', 'ri') else [(0, y0 + 30), (512, y0), (512, y1), (0, y1 + 30)])
            if len(c) >= 3 and area(c) > 12:
                g.shard(c, cl if part not in ('li', 'ri') else darken(cl, 0.12), lw=4.5)
    g.lead_line(t['outline'], lw=10, closed=True)
    g.lead_flush()
    for x, y, r in [(150, 330, 6), (362, 330, 6)]:
        g.circle(x, y, r, '#DDF8F4', lw=0, nolead=True)
    g.glow(256, 260, 160, '#E8FFFB', 0.18)
    g.lead_flush()
    stars(g, [(80, 80, 8), (430, 80, 8), (256, 70, 6), (70, 250, 5), (446, 250, 5)])
    return g.render()


def ic18():  # чистая роза ветров
    g = new('r', light=(256, 120))
    night(g, 18, aur=[aur_wave(70, 18, 70, 44)], span=520)
    cx, cy = 256, 266
    g.glow(cx, 90, 220, '#2BC4BA', 0.4)
    g.lead_flush()
    disk = circle_poly(cx, cy, 118, 44)
    g.shard(disk, '#132F66', lw=0, grad=False)
    g.glow(cx, cy, 118, '#2BC4BA', 0.25)
    g.lead_flush()
    g.lead_circle(cx, cy, 118, lw=9)
    g.lead_flush()
    rose(g, cx, cy, 172, 156, 96, 54, 46, 28, lw=8)
    g.lead_flush()
    stars(g, [(86, 110, 8), (430, 110, 8), (74, 440, 6), (440, 444, 6)])
    return g.render()


def ic19():  # чистый маяк
    g = new('s', light=(256, 150))
    night(g, 19, aur=[aur_wave(118, 20, 56, 26)])
    hz = 396
    sea(g, hz)
    g.lead_flush()
    beam(g, (256, 150), -14, 300, 22, op=0.38)
    beam(g, (256, 150), 194, 300, 22, op=0.38)
    g.shard([(150, 520), (170, 424), (220, 408), (300, 410), (344, 430), (360, 520)], '#1F2A5E', lw=7)
    g.shard([(170, 424), (220, 408), (240, 430), (196, 446)], '#2B3E9E', lw=5)
    g.lead_flush()
    lighthouse(g, 256, 420, 92, 100, 62, bands=4, lw=8)
    stars(g, [(80, 70, 8), (440, 70, 8), (70, 300, 6), (446, 300, 6)])
    return g.render()


def ic20():  # чистый хвост кита (крупнее и в безопасной зоне)
    g = new('t', light=(256, 230))
    hz = 352
    skyr = clip_half(SQ, 0, hz, 0, 1)
    glory(g, 256, hz - 20, skyr, n=12, rot=0.1, cols=['#8FF0E6', '#2BC4BA', '#1F9E6B', '#5FD9D0', '#1B8FB5', '#34D4B0'])
    dim_top(g, 220, 0.85)
    g.glow(256, 250, 200, '#E8FFFB', 0.55)
    g.lead_flush()
    sea(g, hz, rows=[hz, 380, 430, 512])
    g.lead_flush()
    for k, (ya, yb, wa, wb) in enumerate([(hz + 14, 376, 26, 36), (386, 424, 44, 62), (434, 512, 74, 110)]):
        g.shard([(256 - wa, ya), (256 + wa, ya), (256 + wb, yb), (256 - wb, yb)], ROADC[k % 4], lw=5)
    g.lead_flush()
    draw_tail(g, 256, hz + 2, 160, olw=12, lw=8)
    stars(g, [(90, 70, 8), (422, 70, 8)])
    return g.render()


def ic21():  # костёр, дым которого становится сиянием
    g = new('u', light=(256, 300))
    night(g, 21, seq=['#0B1244', '#101C5A', '#152668', '#1A3278'], span=480)
    gs = poisson((0, 410, 512, 512), lambda x, y: 80, 21, 800)
    g.mosaic(clip_half(SQ, 0, 410, 0, -1), gs, lambda x, y, i: ['#9AB5CE', '#C9DCEC', '#7F97AD', '#B5CCE0'][i % 4], lw=4)
    g.lead_line([(0, 410), (512, 410)], lw=7)
    g.lead_flush()
    pts = bez([(256, 270), (230, 200), (300, 170), (420, 160), (430, 80)], 12)
    wid = [16 + 9 * i for i in range(13)]
    ribbon(g, pts, wid, ['#8DEDE2', '#2BC4BA', '#38D9B0', '#1F9E6B', '#2FD0A0', '#2BC4BA', '#5B3FA0'], lw=5)
    pts2 = bez([(256, 270), (290, 210), (200, 180), (110, 150), (90, 90)], 12)
    ribbon(g, pts2, [12 + 6 * i for i in range(13)], ['#2BC4BA', '#1F9E6B', '#38D9B0', '#5B3FA0'], lw=5)
    g.lead_flush()
    campfire(g, 256, 406, 160, lw=7)
    stars(g, [(80, 250, 7), (440, 250, 7), (256, 60, 7)])
    return g.render()


def ic22():  # маяк, лучи которого образуют розу ветров
    g = new('v', light=(256, 160))
    night(g, 22, seq=['#0D1650', '#111D5C', '#152668', '#1A3278'], span=480)
    hz = 404
    sea(g, hz)
    g.lead_flush()
    lc = (256, 166)
    g.glow(lc[0], lc[1], 180, '#2BC4BA', 0.35)
    g.lead_flush()
    rose(g, lc[0], lc[1], 76, 168, 120, 22, 22, 14, south=False, center=False, lw=6,
         colC=('#E4FBF6', '#8DEDE2'), colD=('#5FD9D0', '#1F8FA8'))
    g.shard([(150, 520), (176, 420), (230, 404), (290, 404), (336, 420), (362, 520)], '#1F2A5E', lw=7)
    g.lead_flush()
    lighthouse(g, 256, 416, 110, 84, 50, bands=4, lw=7)
    stars(g, [(80, 300, 7), (440, 300, 7), (80, 70, 7), (436, 70, 7)])
    return g.render()


def ic23():  # медальон: хвост кита и маяк на мысу
    g = new('w', light=(300, 220))
    night(g, 23, seq=['#0D1650', '#111D5C', '#152668', '#111D5C'], span=512)
    cx, cy, R = 256, 262, 166
    disk = circle_poly(cx, cy, R, 56)
    hz = 316
    sky = clip_half(disk, 0, hz, 0, 1)
    glory(g, 300, hz - 6, sky, n=12, rot=0.2, cols=['#8FF0E6', '#2BC4BA', '#1F9E6B', '#5FD9D0', '#1B8FB5', '#34D4B0'])
    g.glow(300, 250, 150, '#E8FFFB', 0.5)
    g.lead_flush()
    sea(g, hz, region=disk, rows=[hz, 350, 390, 440])
    g.lead_flush()
    cape = clip_convex([(80, hz + 30), (110, 296), (150, 290), (190, 312), (200, hz + 30)], disk)
    g.shard(cape, '#1F2A5E', lw=6)
    g.lead_flush()
    lighthouse(g, 148, 296, 200, 30, 20, bands=3, lw=5, glow=False)
    draw_tail(g, 300, hz + 4, 96, olw=10)
    g.lead_circle(cx, cy, R, lw=14)
    g.lead_flush()
    stars(g, [(60, 60, 8), (452, 60, 8), (60, 460, 6), (452, 460, 6)])
    return g.render()


def ic24():  # пламя костра в форме хвоста кита
    g = new('x', light=(256, 300))
    night(g, 24, aur=[aur_wave(80, 20, 60, 26)], seq=['#0B1244', '#101C5A', '#152668', '#1A3278'], span=480)
    gs = poisson((0, 420, 512, 512), lambda x, y: 80, 24, 800)
    g.mosaic(clip_half(SQ, 0, 420, 0, -1), gs, lambda x, y, i: ['#123A73', '#14407E', '#0F2C5C', '#1B3A86'][i % 4], lw=4)
    g.lead_line([(0, 420), (512, 420)], lw=7)
    g.glow(256, 300, 200, '#F0957A', 0.45)
    g.lead_flush()
    draw_tail(g, 256, 404, 150, cols=('#F07E7E', '#C8454F', '#FFB79B', '#E0556B', '#A23547'), olw=11, drops=False, blik=False)
    t = tail_geom(256, 404, 150)
    g.blik(t['blikL'], color='#FFF1EA', w=5, op=0.75)
    g.blik(t['blikR'], color='#FFF1EA', w=5, op=0.75)
    g.shard(quad((150, 430), (360, 408), 22), '#4B3A5E', lw=6)
    g.shard(quad((362, 430), (152, 408), 22), '#3A2C50', lw=6)
    g.lead_flush()
    for (x, y, r) in [(120, 170, 9), (396, 168, 9), (256, 150, 8), (180, 120, 6), (330, 116, 6)]:
        g.spark(x, y, r, '#FFC9A8', 0.95)
    return g.render()


def ic25():  # северный луч розы переходит в сияние
    g = new('y', light=(256, 200))
    night(g, 25, seq=['#0B1244', '#101C5A', '#152668', '#1A3278'], span=480)
    cx, cy = 224, 304
    pts = bez([(cx, cy - 120), (cx, 150), (300, 100), (440, 120), (450, 60)], 12)
    ribbon(g, pts, [44 + 6 * i for i in range(13)], ['#F78F97', '#F0A3A3', '#BDF4EE', '#8DEDE2', '#38D9B0', '#2BC4BA', '#2FD0A0', '#1F9E6B', '#5B3FA0'], lw=5)
    g.glow(320, 120, 140, '#8DEDE2', 0.2)
    g.lead_flush()
    disk = circle_poly(cx, cy, 82, 40)
    glory(g, cx, cy, disk, n=8, rot=0.39, cols=['#0F2A5C', '#16336E'])
    g.lead_circle(cx, cy, 82, lw=8)
    g.lead_flush()
    rose(g, cx, cy, 126, 116, 70, 40, 36, 20, lw=8)
    stars(g, [(80, 90, 8), (120, 200, 6), (440, 300, 7), (420, 440, 6)])
    return g.render()


def ic26():  # кольцо сияния вокруг хвоста кита
    g = new('z', light=(256, 220))
    night(g, 26, seq=['#0B1244', '#0E1850', '#121F5C', '#16296B'], span=480)
    cx, cy = 256, 256
    g.glow(cx, cy, 200, '#2BC4BA', 0.3)
    g.lead_flush()
    disk = circle_poly(cx, cy, 118, 48)
    hz = 300
    glory(g, cx, hz - 10, clip_half(disk, 0, hz, 0, 1), n=10, rot=0.1, cols=['#1B4F8C', '#2B3E9E', '#1B3A86', '#16296B'])
    g.glow(cx, 250, 110, '#8DEDE2', 0.4)
    sea(g, hz, region=disk, rows=[hz, 330, 376])
    g.lead_flush()
    n = 18
    cols = ['#2FD0A0', '#2BC4BA', '#8DEDE2', '#1F9E6B', '#38D9B0', '#5B3FA0']
    for i in range(n):
        a0, a1 = -90 + 360 * i / n, -90 + 360 * (i + 1) / n
        th = 22 + 16 * math.cos(math.radians((a0 + a1) / 2 + 90))
        g.shard(ring_seg_poly(cx, cy, 118, 118 + max(14, th), a0 + 1, a1 - 1, 4), cols[i % len(cols)], lw=5)
    g.lead_circle(cx, cy, 118, lw=8)
    g.lead_flush()
    draw_tail(g, cx, hz + 4, 88, olw=10)
    stars(g, [(70, 70, 8), (446, 70, 8), (70, 446, 6), (446, 446, 6)])
    return g.render()


def ic27():  # иллюминатор-роза, за стеклом кит под водой
    g = new('A', light=(256, 120))
    night(g, 27, seq=['#0D1650', '#111D5C', '#152668', '#111D5C'], span=512)
    cx, cy = 256, 262
    disk = circle_poly(cx, cy, 126, 48)
    # подводный свет: лучи сверху
    glory(g, cx, 60, disk, n=18, rot=0.0, cols=['#1B4F8C', '#1F6FA8', '#14407E', '#2B5FA8', '#123A73'])
    g.glow(cx, 160, 140, '#8DEDE2', 0.35)
    g.lead_flush()
    # кит: тело-линза, хвост, плавник
    body = []
    for i in range(25):
        t = i / 24
        x = 150 + 200 * t
        body.append((x, 270 - 46 * math.sin(math.pi * t) ** 0.8))
    for i in range(24, -1, -1):
        t = i / 24
        x = 150 + 200 * t
        body.append((x, 270 + 30 * math.sin(math.pi * t) ** 0.9))
    body = clean(body, 1)
    g.shard(clip_half(body, 0, 262, 0, 1), '#2B3E9E', lw=7)
    g.shard(clip_half(body, 0, 262, 0, -1), '#C4D8EE', lw=7)
    g.shard([(160, 266), (126, 236), (118, 250), (136, 274), (118, 298), (128, 306), (160, 276)], '#1B2F7A', lw=7)
    g.shard([(256, 292), (232, 334), (246, 336), (280, 296)], '#1B4F8C', lw=6)
    g.circle(318, 260, 5, '#0B1424', lw=0, nolead=True)
    g.lead_flush()
    ring(g, cx, cy, 126, 156, 8, ['#5FB9B4', '#1F8FA8'], lw=5, rot=-90 + 22.5)
    for k in range(8):
        a = math.radians(-90 + 22.5 + 45 * k)
        g.circle(cx + 141 * math.cos(a), cy + 141 * math.sin(a), 7, MILK, lw=4)
    tip, b = (cx, cy - 172), (cx, cy - 130)
    g.shard([(cx - 24, b[1]), tip, b], '#F78F97', lw=6)
    g.shard([b, tip, (cx + 24, b[1])], '#C8454F', lw=6)
    g.lead_flush()
    g.lead_circle(cx, cy, 157, lw=10)
    g.lead_circle(cx, cy, 126, lw=8)
    g.lead_flush()
    for (x, y, r) in [(200, 200, 5), (214, 176, 4), (330, 196, 4)]:
        g.circle(x, y, r, '#BDF4EE', lw=2)
    g.lead_flush()
    stars(g, [(70, 70, 8), (446, 72, 8), (70, 450, 6), (444, 450, 6)])
    return g.render()


def ic28():  # роза ветров восходит над морем, перед ней хвост кита
    g = new('B', light=(256, 300))
    night(g, 28, aur=[aur_wave(70, 16, 60, 30)], span=500)
    hz, cx, cy = 364, 256, 290
    g.glow(cx, cy, 230, '#2BC4BA', 0.45)
    g.lead_flush()
    rose(g, cx, cy, 196, 168, 150, 40, 34, 26, center=False, lw=7,
         colC=('#E4FBF6', '#8DEDE2'), colD=('#8DEDE2', '#2BC4BA'))
    g.glow(cx, cy, 110, '#E8FFFB', 0.45)
    g.lead_flush()
    sea(g, hz, rows=[hz, 396, 440, 512])
    g.lead_flush()
    draw_tail(g, cx, hz + 4, 92, olw=10)
    stars(g, [(70, 120, 7), (446, 120, 7)])
    return g.render()


def ic29():  # стрелка компаса, северный конец — хвост кита
    g = new('C', light=(256, 160))
    night(g, 29, aur=[aur_wave(70, 20, 64, 32)], span=520)
    cx, cy = 256, 276
    g.glow(cx, 180, 200, '#2BC4BA', 0.3)
    g.lead_flush()
    ring(g, cx, cy, 136, 152, 24, ['#1B4F8C', '#2B3E9E'], lw=4)
    g.lead_circle(cx, cy, 153, lw=8)
    g.lead_circle(cx, cy, 136, lw=6)
    g.lead_flush()
    g.shard([(cx - 34, cy), (cx, cy), (cx, 424)], '#C4F3ED', lw=7)
    g.shard([(cx, cy), (cx + 34, cy), (cx, 424)], '#5FB9B4', lw=7)
    draw_tail(g, cx, cy + 2, 118, cols=('#F78F97', '#C8454F', '#F07E7E', '#E0556B', '#A23547'), olw=10, drops=False)
    g.circle(cx, cy + 2, 16, MILK, lw=6)
    g.lead_flush()
    stars(g, [(80, 140, 8), (436, 140, 8), (80, 440, 6), (436, 440, 6)])
    return g.render()


def ic30():  # маяк с костром в фонаре, дым-сияние
    g = new('D', light=(256, 160))
    night(g, 30, seq=['#0B1244', '#101C5A', '#152668', '#1A3278'], span=480)
    hz = 410
    sea(g, hz)
    g.lead_flush()
    pts = bez([(256, 134), (250, 80), (340, 110), (420, 70)], 10)
    ribbon(g, pts, [20 + 8 * i for i in range(11)], ['#8DEDE2', '#38D9B0', '#2BC4BA', '#1F9E6B', '#5B3FA0'], lw=5)
    pts = bez([(256, 134), (266, 84), (180, 100), (96, 76)], 10)
    ribbon(g, pts, [16 + 6 * i for i in range(11)], ['#2BC4BA', '#1F9E6B', '#38D9B0', '#5B3FA0'], lw=5)
    g.lead_flush()
    g.shard([(150, 520), (176, 426), (230, 412), (290, 412), (336, 426), (362, 520)], '#1F2A5E', lw=7)
    g.lead_flush()
    x, yb, yt, wb, wt = 256, 424, 160, 96, 66
    H = yb - yt
    yg = yt + H * 0.42
    for k in range(3):
        ya = yb - (yb - yg) * k / 3
        y2 = yb - (yb - yg) * (k + 1) / 3
        wa = wb + (wt - wb) * (yb - ya) / (yb - yg)
        wc = wb + (wt - wb) * (yb - y2) / (yb - yg)
        q = [(x - wa / 2, ya), (x + wa / 2, ya), (x + wc / 2, y2), (x - wc / 2, y2)]
        c = (LH_MILK, LH_RED)[k % 2]
        g.shard(clip_half(q, x, 0, 1, 0), c, lw=8)
        g.shard(clip_half(q, x, 0, -1, 0), darken(c, 0.12), lw=8)
    g.shard([(x - 52, yg), (x + 52, yg), (x + 52, yg - 12), (x - 52, yg - 12)], '#2B2048', lw=6, grad=False)
    ly0, ly1 = yg - 12, yt + 18
    g.shard([(x - 40, ly0), (x + 40, ly0), (x + 40, ly1), (x - 40, ly1)], '#3A2C50', lw=7, grad=False)
    g.shard([(x - 44, ly1), (x + 44, ly1), (x, yt - 26)], '#8C2A3C', lw=7)
    g.lead_flush()
    campfire(g, x, ly0 - 4, 76, lw=5, logs=False)
    g.lead_line([(x - 40, ly0), (x - 40, ly1), (x + 40, ly1), (x + 40, ly0)], lw=7)
    g.lead_flush()
    stars(g, [(80, 200, 7), (440, 200, 7), (70, 330, 6), (446, 330, 6)])
    return g.render()


ICONS = [
    ('11', 'whale_lighthouse', ic11), ('12', 'compass_whale', ic12), ('13', 'beam_aurora', ic13),
    ('14', 'shore_fire_whale', ic14), ('15', 'porthole_lighthouse', ic15), ('16', 'needle_lighthouse', ic16),
    ('17', 'aurora_tail', ic17), ('18', 'pure_compass', ic18), ('19', 'pure_lighthouse', ic19),
    ('20', 'pure_whale', ic20), ('21', 'fire_aurora', ic21), ('22', 'lighthouse_rose', ic22),
    ('23', 'tail_medallion', ic23), ('24', 'fire_tail', ic24), ('25', 'compass_aurora_ray', ic25),
    ('26', 'aurora_ring_whale', ic26), ('27', 'porthole_whale', ic27), ('28', 'rose_sunrise_whale', ic28),
    ('29', 'tail_needle', ic29), ('30', 'lighthouse_flame', ic30),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = None
    for a in sys.argv[1:]:
        if a[0].isdigit():
            only = a.split(',')
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

#!/usr/bin/env python3
"""Витражные портреты духов (часть A): leshy, domovoy, bannik, poludnitsa, vodyanoy.

python3 tools/art/spirits_glass_a.py [--sheet /tmp/spirits_a_sheet.png] [only_id ...]

Пишет app/assets/art/spirits/<id>_<mood>.svg (360x200, mood = neutral|kind|cunning|angry).
Одна композиция-основа на существо; меняются лицо, цвет, поза, фон/свет.
Только path/circle/rect/g/defs/gradients (flutter_svg), свинец #070B10, файл <= 20 КБ.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_glass_lib import *  # noqa: F401,F403
from hero_glass_lib import check_svg

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'app', 'assets', 'art', 'spirits')
W, HH = 360, 200
LIMIT = 20 * 1024
DARK = '#1A0E18'
MOUTH = '#6E1E34'

# ---- настроения ---------------------------------------------------------------------
MOODS = {
    'neutral': dict(
        tint='#4F9BC0', tk=0.06, glow=TURQ, gop=0.45, iris='#5FE3C8',
        bg=['#08153A', '#1C4284', '#1B4F8C', '#15626E', '#2B3E9E', '#2B9FB0', '#4284CF'],
        lead=1.5),
    'kind': dict(
        tint=AMBER, tk=0.13, glow='#FFB866', gop=0.62, iris='#3CC48C',
        bg=['#05271D', '#136A47', '#17664A', '#1F9E6B', '#17959C', '#2BC4BA', '#6BE0A9'],
        lead=1.4),
    'cunning': dict(
        tint='#7E5CC8', tk=0.24, glow='#A27CF0', gop=0.5, iris='#C58CF0',
        bg=['#150E36', '#2A1F5C', '#432C86', '#5B3FA0', '#2B3E9E', '#17959C', '#8466D0'],
        lead=1.8),
    'angry': dict(
        tint=CORAL, tk=0.30, glow='#FF5A4D', gop=0.6, iris='#FF4A3D',
        bg=['#0B1424', '#1A0A1A', '#4A1428', '#8C2A3C', '#C8454F', '#E8715C'],
        lead=2.4),
}

# ---- позы ------------------------------------------------------------------------------
POSE = {
    'neutral': dict(tilt=0, hx=0, hy=0, shl=0, shr=0, tx=0,
                    L=((104, 166), (110, 188)), R=((256, 166), (250, 188)), fl=False, fr=False),
    'kind': dict(tilt=-4, hx=0, hy=-1, shl=0, shr=0, tx=0,
                 L=((92, 170), (80, 152)), R=((262, 168), (252, 190)), fl=False, fr=False),
    'cunning': dict(tilt=8, hx=7, hy=0, shl=-6, shr=5, tx=7,
                    L=((98, 158), (92, 128)), R=((262, 168), (252, 190)), fl=False, fr=False),
    'angry': dict(tilt=-3, hx=0, hy=9, shl=-14, shr=-14, tx=0,
                  L=((88, 152), (84, 110)), R=((272, 152), (276, 110)), fl=True, fr=True),
}


def T(M, c):
    return mix(c, M['tint'], M['tk'])


def rotp(p, a, c):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    return (c[0] + (p[0] - c[0]) * ca - (p[1] - c[1]) * sa, c[1] + (p[0] - c[0]) * sa + (p[1] - c[1]) * ca)


class Head:
    def __init__(self, cx, cy, ang=0.0, sc=1.0):
        self.cx, self.cy, self.ang, self.sc = cx, cy, ang, sc
        self.c, self.s = math.cos(math.radians(ang)), math.sin(math.radians(ang))

    def p(self, pts):
        return [(self.cx + self.sc * (x * self.c - y * self.s), self.cy + self.sc * (x * self.s + y * self.c)) for x, y in pts]

    def q(self, x, y):
        return self.p([(x, y)])[0]


# ---- общие детали ---------------------------------------------------------------------------
def almond(cx, cy, w, h, up=None, lo=None):
    up = h if up is None else up
    lo = h if lo is None else lo
    return [(cx - w, cy), (cx - w * 0.5, cy - up), (cx + w * 0.5, cy - up), (cx + w, cy), (cx + w * 0.5, cy + lo), (cx - w * 0.5, cy + lo)]


def brow(g, H, pts, t, col, lw=0.7):
    P = H.p(pts)
    ws = [t * 0.6, t, t * 0.55][:len(P)] if len(P) == 3 else [t] * len(P)
    quads, _ = chain_quads(P, ws)
    for q in quads:
        g.shard(q, col, lw=lw, grad=False)


def eye_dot(g, H, x, y, r, col):
    X, Y = H.q(x, y)
    g.circle(X, Y, r * H.sc, col, lw=0.6, grad=False)


def face(g, H, M, mood, skin, brow_col, **kw):
    g.prec = 1
    _face(g, H, M, mood, skin, brow_col, **kw)
    g.prec = 0


def _face(g, H, M, mood, skin, brow_col, tx=0, ey=-4, ex=12, my=18, es=1.0, bt=3.6):
    iris = M['iris']
    S = lambda pts, col, lw=0.7, op=None, nl=False: g.shard(H.p(pts), col, lw=lw, grad=False, op=op, nolead=nl)
    LX, RX = -ex + tx, ex + tx
    # нос
    S([(tx - 1.5, -8), (tx - 6, 8), (tx, 11), (tx + 6.5, 8)], darken(skin, 0.18), lw=0.7)
    S([(tx - 0.5, -8), (tx + 3, 7), (tx, 10), (tx - 3, 8)], lighten(skin, 0.18), lw=0.5)
    if mood == 'neutral':
        for X in (LX, RX):
            S(almond(X, ey, 6.8 * es, 4.4 * es), MILK)
            eye_dot(g, H, X + 0.8, ey, 3.1 * es, iris)
            eye_dot(g, H, X + 0.8, ey, 1.5 * es, DARK)
        brow(g, H, [(LX - 8, ey - 9), (LX, ey - 12), (LX + 8, ey - 9.5)], bt, brow_col)
        brow(g, H, [(RX - 8, ey - 10.5), (RX, ey - 13.5), (RX + 8, ey - 10)], bt, brow_col)
        S([(tx - 6, my - 0.5), (tx, my + 1), (tx + 6, my - 0.5), (tx, my + 2.5)], MOUTH, lw=0.6)
    elif mood == 'kind':
        for X in (LX, RX):
            outer = [(X - 6.8, ey + 3), (X - 4.2, ey - 1.5), (X, ey - 3.8), (X + 4.2, ey - 1.5), (X + 6.8, ey + 3)]
            inner = [(X + 4.4, ey + 0.4), (X, ey - 1.2), (X - 4.4, ey + 0.4)]
            S(outer + inner, DARK, lw=0.4)
        brow(g, H, [(LX - 8, ey - 8), (LX, ey - 13), (LX + 8, ey - 10.5)], bt, brow_col)
        brow(g, H, [(RX - 8, ey - 10.5), (RX, ey - 13), (RX + 8, ey - 8)], bt, brow_col)
        for sx in (-1, 1):
            S(ellipse_poly(sx * (ex + 6) + tx, ey + 10, 5.5, 3.2, n=8), '#F0707A', lw=0.4, op=0.6, nl=True)
        S([(tx - 12, my - 2), (tx - 6, my + 3.5), (tx, my + 6), (tx + 6, my + 3.5), (tx + 12, my - 2), (tx, my - 0.5)], MOUTH, lw=0.7)
        S([(tx - 8, my - 0.5), (tx, my + 0.3), (tx + 8, my - 0.5), (tx + 5, my + 2.4), (tx - 5, my + 2.4)], MILK, lw=0.4)
    elif mood == 'cunning':
        # левый глаз — прищур, правый — широкий с бликом
        S([(LX - 7, ey + 0.5), (LX - 2, ey - 2.2), (LX + 6, ey - 1.6), (LX + 7.4, ey + 0.4), (LX, ey + 2.4)], MILK)
        eye_dot(g, H, LX + 1.5, ey + 0.2, 2.2, iris)
        S([(LX - 8, ey - 0.4), (LX - 2, ey - 3.3), (LX + 7, ey - 2.6), (LX + 8, ey - 1.2), (LX + 1, ey - 1.8)], DARK, lw=0.4)
        S(almond(RX, ey - 1, 7.4 * es, 5.8 * es), MILK)
        eye_dot(g, H, RX + 1.3, ey - 0.6, 3.5 * es, iris)
        eye_dot(g, H, RX + 1.3, ey - 0.6, 1.5 * es, DARK)
        brow(g, H, [(LX - 8, ey - 7.5), (LX + 1, ey - 8.5), (LX + 8, ey - 5.5)], bt + 0.4, brow_col)
        brow(g, H, [(RX - 8, ey - 13), (RX + 1, ey - 19.5), (RX + 9, ey - 15)], bt, brow_col)
        # ухмылка: левый угол низко, правый высоко
        S([(tx - 8, my + 1.5), (tx - 2, my + 3), (tx + 6, my + 1), (tx + 12, my - 4.5), (tx + 7, my - 0.5), (tx, my + 0.8), (tx - 7, my - 0.2)], MOUTH, lw=0.6)
        S([(tx + 5.5, my + 0.8), (tx + 10, my - 3.2), (tx + 9, my + 2.4)], MILK, lw=0.4)
        S([(tx + 11, my - 5), (tx + 14.5, my - 8), (tx + 13, my - 3)], darken(skin, 0.2), lw=0.4)
        g.spark(*H.q(RX + 3.6, ey - 2.4), 2.4 * H.sc, color='#FFFFFF', op=0.95)
    else:  # angry
        g.glow(*H.q(LX, ey), 14 * H.sc, '#FF4A3D', op=0.55)
        g.glow(*H.q(RX, ey), 14 * H.sc, '#FF4A3D', op=0.55)
        # верхнее веко скошено к переносице
        S([(LX - 7, ey - 3.6), (LX + 7, ey), (LX + 6, ey + 3.4), (LX - 4, ey + 4)], MILK)
        S([(RX + 7, ey - 3.6), (RX - 7, ey), (RX - 6, ey + 3.4), (RX + 4, ey + 4)], MILK)
        eye_dot(g, H, LX + 2.2, ey + 1.2, 2.9, iris)
        eye_dot(g, H, RX - 2.2, ey + 1.2, 2.9, iris)
        eye_dot(g, H, LX + 2.2, ey + 1.2, 1.2, DARK)
        eye_dot(g, H, RX - 2.2, ey + 1.2, 1.2, DARK)
        brow(g, H, [(LX - 10, ey - 11), (LX, ey - 7.5), (LX + 9.5, ey - 1)], bt + 2.0, brow_col, lw=0.9)
        brow(g, H, [(RX + 10, ey - 11), (RX, ey - 7.5), (RX - 9.5, ey - 1)], bt + 2.0, brow_col, lw=0.9)
        S([(tx - 11, my + 1), (tx - 6, my - 2), (tx, my - 1), (tx + 6, my - 2), (tx + 11, my + 1), (tx + 8, my + 7), (tx, my + 9), (tx - 8, my + 7)], DARK, lw=0.7)
        for i in range(4):
            x0 = tx - 9 + i * 4.6
            S([(x0, my - 1.6), (x0 + 4.4, my - 1.6), (x0 + 2.2, my + 3.6)], MILK, lw=0.4)
        S([(tx - 6, my + 7.4), (tx - 3, my + 3.2), (tx - 1, my + 7.8)], MILK, lw=0.4)
        S([(tx + 1, my + 7.8), (tx + 3, my + 3.2), (tx + 6, my + 7.4)], MILK, lw=0.4)
        S([(tx - 3, my + 3), (tx, my + 5), (tx + 3, my + 3), (tx, my + 8)], '#C8454F', lw=0.3, nl=True)
        # морщины у носа
        g.lead_line(H.p([(tx - 5, -3), (tx - 9, 4)]), 0.9)
        g.lead_line(H.p([(tx + 5, -3), (tx + 9, 4)]), 0.9)


def head_base(g, H, M, skin, poly, seeds, lw=0.9):
    P = H.p(poly)
    S = H.p(seeds)
    cols = [lighten(skin, 0.16), skin, skin, darken(skin, 0.14), lighten(skin, 0.08), darken(skin, 0.06)]

    def cf(x, y, i):
        return cols[i % len(cols)]
    g.mosaic(P, S, cf, lw=lw, grad=False)
    g.lead_flush()


HEAD_B = [(-26, -22), (-18, -34), (0, -37), (18, -34), (26, -22), (27, 0), (25, 9), (14, 14), (0, 13), (-14, 14), (-25, 9), (-27, 0)]
HEAD_F = [(-26, -22), (-18, -34), (0, -37), (18, -34), (26, -22), (27, 0), (22, 20), (10, 32), (0, 35), (-10, 32), (-22, 20), (-27, 0)]
SEEDS_B = [(-14, -20), (14, -20), (-16, 4), (16, 4), (0, 8)]
SEEDS_F = [(-14, -20), (14, -20), (-15, 6), (15, 6), (0, 26)]


def beard(g, H, cols, rnd, w=28, L=62, n=7, top=-4, jag=10, layers=2):
    for ly in range(layers):
        ww = w + (6 if ly == 0 else 0)
        LL = L + (10 if ly == 0 else -4)
        n_ = n + (0 if ly == 0 else -1)
        xs = [-ww + 2 * ww * i / n_ for i in range(n_ + 1)]
        tips = []
        for i, x in enumerate(xs):
            tl = LL * (1 - 0.55 * (abs(x) / ww) ** 2) + (jag if i % 2 else -jag * 0.5) * (0.5 + rnd.random() * 0.8)
            tips.append((x * (0.85 if ly else 0.95), top + tl))
        for i in range(n_):
            a = (xs[i], top)
            b = (xs[i + 1], top)
            mid = ((tips[i][0] + tips[i + 1][0]) / 2, (tips[i][1] + tips[i + 1][1]) / 2 + 4)
            poly = [a, b, tips[i + 1], mid, tips[i]] if (i % 2 == 0) else [a, b, tips[i + 1], tips[i]]
            col = cols[(i + ly * 2) % len(cols)]
            if ly == 0:
                col = darken(col, 0.18)
            g.shard(H.p(poly), col, lw=0.9)
    g.lead_flush()


def mustache(g, H, col, tx=0, my=18):
    for s in (-1, 1):
        g.shard(H.p([(tx + s * 1, 11), (tx + s * 17, 13), (tx + s * 23, 24), (tx + s * 9, 22), (tx + s * 2, my - 2)]), col, lw=0.8)


def antlers(g, H, cols, spread=1.0, rnd=None):
    for s in (-1, 1):
        base = (s * 15, -33)
        joints = [base, (s * 25 * spread, -48), (s * 31 * spread, -64), (s * 27 * spread, -80)]
        quads, _ = chain_quads(H.p(joints), [9, 6.5, 5, 2.5])
        for i, q in enumerate(quads):
            g.shard(q, cols[i % len(cols)], lw=1.1)
        # ветки
        for k, (j, tip) in enumerate([(1, (s * 44 * spread, -62)), (2, (s * 47 * spread, -84)), (1, (s * 15, -70))]):
            jt = joints[j]
            quads, _ = chain_quads(H.p([jt, ((jt[0] + tip[0]) / 2, (jt[1] + tip[1]) / 2 - 2), tip]), [5, 3.6, 1.6])
            for q in quads:
                g.shard(q, cols[(k + 1) % len(cols)], lw=0.9)


def torso(g, M, cols, rnd, shl, shr, by=130, x0=92, x1=268, n=9, lw=1.3):
    reg = [(x0, 204), (x0 + 6, by + 34 + shl), (x0 + 30, by + 6 + shl), (150, by - 6), (210, by - 6), (x1 - 30, by + 6 + shr), (x1 - 6, by + 34 + shr), (x1, 204)]
    seeds = poisson((x0, by - 6, x1, 204), lambda x, y: 20, rnd.randint(1, 999), tries=600)[:n]
    seeds = seeds or [(180, 160)]
    g.mosaic(reg, seeds, lambda x, y, i: T(M, cols[(i + int(x // 30)) % len(cols)]), lw=lw, grad=True)
    g.lead_flush()
    return reg


def hand(g, pos, skin, fist=False, lw=1.1):
    x, y = pos
    g.shard(circle_poly(x, y, 10 if fist else 8.5, n=8, rot=0.3), skin, lw=lw)
    if fist:
        for k in (-4, 0, 4):
            g.lead_line([(x + k, y - 7), (x + k, y - 1)], 0.8)
    else:
        g.lead_line([(x - 3, y - 7), (x - 3, y - 1)], 0.7)
        g.lead_line([(x + 3, y - 7), (x + 3, y - 1)], 0.7)


def arm(g, M, sh, el, hd, sleeve, skin, fist=False, wid=(18, 15, 12)):
    quads, _ = chain_quads([sh, el, hd], list(wid))
    for i, q in enumerate(quads):
        g.shard(q, T(M, sleeve[i % len(sleeve)]), lw=1.3)
    hand(g, hd, skin, fist)
    g.lead_flush()


# ---- подарки / «подвохи» --------------------------------------------------------------------------
def orb_light(g, x, y, r, col, op=0.7):
    g.glow(x, y, r, col, op=op)


def prop(g, M, cid, kind, x, y):
    """kind: gift|trick, (x, y) — ладонь."""
    if kind == 'gift':
        orb_light(g, x, y - 16, 34, '#FFB866', 0.55)
    if cid == 'leshy':
        if kind == 'gift':   # светящийся гриб
            g.shard([(x - 2, y - 7), (x + 2, y - 7), (x + 3, y - 18), (x - 3, y - 18)], MILK, lw=0.8, grad=False)
            g.shard([(x - 13, y - 17), (x - 7, y - 26), (x + 7, y - 26), (x + 13, y - 17), (x, y - 14)], '#E8625E', lw=1.0)
            g.shard([(x - 6, y - 20), (x - 3, y - 24), (x, y - 20)], MILK, lw=0.4, grad=False)
        else:   # блуждающий огонёк-приманка
            orb_light(g, x, y - 16, 22, '#7AF0E0', 0.7)
            g.shard([(x, y - 30), (x + 7, y - 17), (x + 3, y - 8), (x - 4, y - 8), (x - 7, y - 17)], '#66E6D8', lw=1.0)
            g.shard([(x, y - 25), (x + 3, y - 17), (x, y - 12), (x - 3, y - 17)], MILK, lw=0.5, grad=False)
    elif cid == 'domovoy':
        if kind == 'gift':   # каравай на полотенце
            g.shard([(x - 18, y - 6), (x + 18, y - 6), (x + 14, y - 1), (x - 14, y - 1)], '#C8454F', lw=0.9)
            g.shard([(x - 14, y - 7), (x - 10, y - 17), (x + 10, y - 17), (x + 14, y - 7)], '#C98A4E', lw=1.0)
            g.lead_line([(x - 6, y - 16), (x - 4, y - 8)], 0.7)
            g.lead_line([(x + 5, y - 16), (x + 4, y - 8)], 0.7)
        else:   # железный ключ
            g.shard(circle_poly(x - 5, y - 24, 6, n=8), '#9AB5CE', lw=1.1)
            g.shard([(x - 3, y - 20), (x + 3, y - 20), (x + 6, y - 2), (x, y - 1)], '#7F97AD', lw=1.0)
            g.shard([(x + 2, y - 6), (x + 9, y - 6), (x + 9, y - 3), (x + 4, y - 3)], '#9AB5CE', lw=0.8, grad=False)
            g.shard(circle_poly(x - 5, y - 24, 2.4, n=6), '#0B1424', lw=0.4, grad=False)
    elif cid == 'bannik':
        if kind == 'gift':   # кусочек мыла и ковш с водой
            g.shard([(x - 14, y - 4), (x + 14, y - 4), (x + 10, y - 14), (x - 10, y - 14)], '#9A6A3E', lw=1.0)
            g.shard([(x - 12, y - 14), (x + 12, y - 14), (x + 9, y - 18), (x - 9, y - 18)], '#5BB5E8', lw=0.8)
            g.shard([(x + 8, y - 12), (x + 24, y - 8), (x + 24, y - 5), (x + 9, y - 6)], '#7A3F24', lw=0.8)
        else:    # раскалённый уголёк
            orb_light(g, x, y - 12, 24, '#FF6A3D', 0.65)
            g.shard([(x - 9, y - 4), (x - 7, y - 15), (x + 2, y - 19), (x + 9, y - 11), (x + 7, y - 3)], '#2A1218', lw=1.0)
            g.shard([(x - 5, y - 10), (x, y - 15), (x + 5, y - 9), (x, y - 6)], '#F0653D', lw=0.6)
            g.shard([(x - 1, y - 12), (x + 2, y - 10), (x, y - 8)], AMBER, lw=0.3, grad=False)
    elif cid == 'poludnitsa':
        if kind == 'gift':   # колосья и васильки
            for k in (-7, -2, 4, 9):
                g.shard([(x + k - 1.2, y - 4), (x + k + 1.2, y - 4), (x + k * 1.4 + 1.2, y - 28), (x + k * 1.4 - 1.2, y - 28)], '#7C9A4A', lw=0.5, grad=False)
                g.shard(ellipse_poly(x + k * 1.4, y - 29, 2.6, 6, n=6), '#E0B35E', lw=0.7)
            for (a, b) in ((-9, -12), (8, -16)):
                g.shard(circle_poly(x + a, y + b, 4.2, n=7), '#3E6FD8', lw=0.8)
        else:    # серп
            g.shard([(x - 2, y - 4), (x + 2, y - 4), (x + 3, y - 14), (x - 1, y - 14)], '#7A3F24', lw=0.9)
            g.shard([(x, y - 14), (x + 16, y - 22), (x + 22, y - 36), (x + 9, y - 33), (x - 4, y - 26)], '#C9D6E0', lw=1.0)
            g.blik([(x + 3, y - 20), (x + 14, y - 28)], '#FFFFFF', 1.0, 0.8)
    elif cid == 'vodyanoy':
        if kind == 'gift':   # жемчужина в раковине
            g.shard([(x - 14, y - 4), (x - 10, y - 15), (x, y - 17), (x + 10, y - 15), (x + 14, y - 4)], '#2BC4BA', lw=1.0)
            g.shard([(x - 12, y - 14), (x - 10, y - 24), (x, y - 27), (x + 10, y - 24), (x + 12, y - 14), (x, y - 12)], '#8DF1E9', lw=1.0)
            g.circle(x, y - 16, 5.2, MILK, lw=0.8)
            g.spark(x - 1.5, y - 17.5, 2.4, color='#FFFFFF')
        else:    # крючок с монеткой
            g.lead_line([(x - 5, y - 44), (x - 5, y - 12)], 0.9)
            g.shard([(x - 7, y - 12), (x - 3, y - 12), (x - 3, y - 3), (x + 4, y - 3), (x + 4, y - 9), (x + 7, y - 9), (x + 7, y), (x - 7, y)], '#B7C9D9', lw=0.9, grad=False)
            g.shard(circle_poly(x - 5, y - 30, 7, n=8), '#F0A24A', lw=1.1)
            g.shard(circle_poly(x - 5, y - 30, 3, n=6), '#C98A4E', lw=0.5, grad=False)
            g.spark(x - 8, y - 33, 2.6, color='#FFFFFF')


# ---- фон ---------------------------------------------------------------------------------------------------
FOCUS = {'leshy': (180, 82), 'domovoy': (180, 100), 'bannik': (180, 92), 'poludnitsa': (180, 76), 'vodyanoy': (180, 92)}


def bg_layer(g, M, mood, rnd, cid):
    fx, fy = FOCUS[cid]
    cols = [T(M, c) if mood != 'angry' else c for c in M['bg']]
    n = len(cols)
    region = rect_poly(0, 0, W, HH)
    dmax = 230.0

    def pick(x, y, i, jit=1.1):
        d = math.hypot((x - fx) * 0.8, y - fy)
        t = max(0.0, 1 - d / dmax)
        idx = int(round(t * (n - 1) + rnd.uniform(-jit, jit)))
        return cols[max(0, min(n - 1, idx))]

    if mood == 'angry':
        # осколки-лучи от точки удара
        K = 10
        ang = [(-math.pi + 2 * math.pi * i / K + rnd.uniform(-0.12, 0.12)) for i in range(K)]
        rings = [34, 78, 130, 420]
        V = []
        for k, r in enumerate(rings):
            V.append([(fx + (r * (1 + rnd.uniform(-0.12, 0.12))) * math.cos(a), fy + (r * (1 + rnd.uniform(-0.12, 0.12))) * 0.85 * math.sin(a)) for a in ang])
        for k in range(len(rings) - 1):
            for i in range(K):
                j = (i + 1) % K
                poly = [V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]]
                poly = clip_convex(poly, region)
                if len(poly) < 3:
                    continue
                t = 1 - k / (len(rings) - 1)
                idx = int(round(t * (n - 1) + rnd.uniform(-1.4, 1.0)))
                g.shard(poly, cols[max(0, min(n - 1, idx))], lw=None)
    else:
        if mood == 'cunning':
            a = math.radians(-28)
            ca, sa = math.cos(a), math.sin(a)
            kx = 2.3
            fw = lambda x, y: (((x - 180) * ca - (y - 100) * sa) / kx, (x - 180) * sa + (y - 100) * ca)
            bw = lambda u, v: (180 + u * kx * ca + v * sa * -1 * -1 * 0 + (-v * sa), 0)

            def inv(u, v):
                uu = u * kx
                return (180 + uu * ca + v * sa, 100 - uu * sa + v * ca)
            reg_uv = [fw(x, y) for x, y in region]
            xs = [p[0] for p in reg_uv]
            ys = [p[1] for p in reg_uv]
            seeds_uv = poisson((min(xs), min(ys), max(xs), max(ys)), lambda x, y: 34, rnd.randint(1, 9999), tries=2500)
            cells = voronoi(reg_uv, seeds_uv, 0.8)
            for c in cells:
                poly = clip_convex([inv(u, v) for u, v in c], region)
                if len(poly) >= 3:
                    cx_, cy_ = centroid(poly)
                    g.shard(poly, pick(cx_, cy_, 0, 1.3), lw=None)
        else:
            seeds = poisson((-8, -8, W + 8, HH + 8), lambda x, y: 38 + 0.1 * math.hypot(x - fx, y - fy), rnd.randint(1, 9999), tries=3500)
            g.mosaic(region, seeds, lambda x, y, i: pick(x, y, i), lw=None)
    g.glow_e(fx, fy, 190, 120, M['glow'], op=M['gop'], mid=0.5)
    g.lead_flush()


def mood_fx_back(g, M, mood, rnd, cid):
    """Свет настроения — за сценой."""
    fx, fy = FOCUS[cid]
    if mood == 'kind':
        for i in range(9):
            a = math.radians(-160 + i * 20 + rnd.uniform(-4, 4))
            r1, r2 = 400, 400
            wd = math.radians(2.8)
            g.shard([(fx, fy), (fx + r1 * math.cos(a - wd), fy + r1 * math.sin(a - wd)), (fx + r2 * math.cos(a + wd), fy + r2 * math.sin(a + wd))],
                    '#FFE6B0', lw=0, grad=False, op=0.10, nolead=True)
    g.flush()


def mood_fx_front(g, M, mood, rnd, cid):
    fx, fy = FOCUS[cid]
    if mood == 'kind':
        for i in range(7):
            x, y = rnd.uniform(18, 342), rnd.uniform(14, 186)
            if abs(x - fx) < 50 and abs(y - fy) < 60:
                continue
            g.spark(x, y, rnd.uniform(2.2, 4.2), color='#FFE9B8', op=0.9)
    elif mood == 'cunning':
        for i in range(8):
            x, y = rnd.uniform(18, 342), rnd.uniform(14, 186)
            if abs(x - fx) < 50 and abs(y - fy) < 60:
                continue
            g.spark(x, y, rnd.uniform(1.8, 3.4), color='#B9F0EC', op=0.8)
    elif mood == 'angry':
        # молнии
        g.glow(300, 40, 55, '#FF7A66', 0.45)
        g.shard([(296, 0), (316, 0), (293, 34), (309, 34), (268, 96), (282, 52), (266, 52)], '#F7E9E4', lw=0.9, grad=False)
        g.glow(52, 34, 45, '#FF7A66', 0.4)
        g.shard([(50, 0), (66, 0), (46, 28), (60, 28), (30, 78), (38, 40), (26, 40)], '#F7E9E4', lw=0.9, grad=False)
        # угловые «клыки» рамы
        for pts in ([(0, 200), (0, 160), (30, 200)], [(360, 200), (326, 200), (360, 158)]):
            g.shard(pts, '#0B1424', lw=1.2, grad=False)
    g.lead_flush()


# ---- сцены ----------------------------------------------------------------------------------------------------
def trunk(g, M, x, w, c1, c2, lean=0.0, lw=1.4):
    j = [(x, -4), (x + lean * 0.3, 55), (x + lean * 0.6, 130), (x + lean, 206)]
    quads, _ = chain_quads(j, [w * 0.8, w, w * 1.1, w * 1.3])
    for i, q in enumerate(quads):
        g.shard(q, T(M, (c1, c2)[i % 2]), lw=lw)


def scene_leshy(g, M, mood, rnd):
    for x, w, l in ((22, 30, 6), (78, 22, -4), (292, 24, 5), (340, 32, -6)):
        trunk(g, M, x, w, '#0F3A3A', '#16475A', l)
    # крона
    cols = ['#136A47', '#1F9E6B', '#0F4A35', '#2E8A5A']
    x = -20
    while x < 370:
        wd = rnd.uniform(38, 54)
        g.shard([(x, -6), (x + wd, -6), (x + wd * 0.8, rnd.uniform(14, 26)), (x + wd * 0.45, rnd.uniform(26, 38)), (x + wd * 0.05, rnd.uniform(12, 24))], T(M, cols[int(x) % 4]), lw=1.2)
        x += wd * 0.8
    # папоротники
    for x in (10, 56, 300, 342):
        for k in range(4):
            a = math.radians(-100 + k * 40 + rnd.uniform(-6, 6))
            L = rnd.uniform(26, 38)
            g.shard([(x, 204), (x + 9 * math.cos(a + 1.6), 204 + 9 * math.sin(a + 1.6) * 0.0), (x + L * math.cos(a), 204 + L * math.sin(a)), (x - 8, 204)],
                    T(M, ('#1F9E6B', '#136A47')[k % 2]), lw=1.1)
    if mood == 'angry':
        for pts in ([(0, 70), (46, 96), (0, 108)], [(360, 80), (306, 108), (360, 118)], [(0, 140), (40, 154), (0, 166)], [(360, 30), (320, 54), (360, 62)]):
            g.shard(pts, '#1A0A1A', lw=1.4, grad=False)
        for (x, y) in ((44, 118), (320, 136)):
            g.glow(x, y, 16, '#FF4A3D', 0.6)
            g.circle(x - 4, y, 2.2, '#FF6A5D', lw=0.4, grad=False)
            g.circle(x + 4, y, 2.2, '#FF6A5D', lw=0.4, grad=False)
    elif mood == 'cunning':
        for (x, y, rx) in ((60, 150, 40), (300, 120, 46)):
            g.shard(ellipse_poly(x, y, rx, 9, n=9), '#8466D0', lw=0.8, op=0.45)
    g.lead_flush()


def scene_domovoy(g, M, mood, rnd):
    # окно с ночным небом, слева
    g.shard(rect_poly(24, 22, 74, 76), '#070B10', lw=0, grad=False, nolead=True)
    wcol = {'neutral': '#1C4284', 'kind': '#17959C', 'cunning': '#2A1F5C', 'angry': '#2A0F22'}[mood]
    for (x, y, w, h) in ((29, 27, 31, 31), (64, 27, 29, 31), (29, 62, 31, 31), (64, 62, 29, 31)):
        g.shard(rect_poly(x, y, w, h), wcol, lw=0, grad=True)
    g.glow(60, 56, 38, T(M, '#8DF1E9') if mood != 'angry' else '#FF7A66', 0.4)
    g.shard(circle_poly(74, 42, 7, n=8), '#EDE6D2' if mood != 'angry' else '#E86A5A', lw=0.7, grad=False)
    g.lead_line([(24, 22), (98, 22), (98, 98), (24, 98)], 3.2, closed=True)
    g.lead_line([(61, 22), (61, 98)], 2.6)
    g.lead_line([(24, 60), (98, 60)], 2.6)
    # печь справа
    reg = [(244, 204), (244, 96), (262, 62), (302, 52), (336, 66), (352, 96), (352, 204)]
    bricks = [(256 + 20 * (i % 4) + 10 * (i // 4 % 2), 70 + 24 * (i // 4)) for i in range(16)]
    stone = ['#9CB2C4', '#C9D6E0', '#7F97AD', '#B7C9D9']
    g.mosaic(reg, [(x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3)) for x, y in bricks if x < 350], lambda x, y, i: T(M, stone[(i + int(y // 20)) % 4]), lw=1.2)
    mouth = [(268, 204), (268, 138), (278, 118), (306, 112), (326, 120), (332, 138), (332, 204)]
    fcol = {'neutral': ('#F0A24A', '#E0652E'), 'kind': ('#FFC772', '#F0A24A'), 'cunning': ('#B88CF0', '#6E48C0'), 'angry': ('#FF5A3D', '#C8302F')}[mood]
    g.shard(mouth, '#12080C', lw=2.0, grad=False)
    hf = 38 if mood == 'angry' else 30
    g.glow(300, 168, 56, fcol[0], 0.55)
    g.shard([(276, 204), (282, 176), (292, 192), (300, 168 - hf * 0.0), (310, 188), (322, 172), (326, 204)], fcol[1], lw=1.0)
    g.shard([(288, 204), (296, 182), (303, 196), (312, 180), (318, 204)], fcol[0], lw=0.8)
    g.shard([(300, 204), (305, 190), (310, 204)], MILK if mood != 'cunning' else '#E6D6FF', lw=0.5, grad=False)
    g.lead_flush()
    # половик
    cols = ['#C8454F', '#2BC4BA', '#EDE6D2', '#2B3E9E', '#C8454F', '#1F9E6B', '#EDE6D2']
    for i in range(14):
        x0 = -10 + i * 28
        g.shard([(x0, 204), (x0 + 28, 204), (x0 + 24, 184), (x0 - 4, 184)], T(M, cols[i % 7]), lw=1.0)
    if mood == 'angry':
        # искры из печи и дым
        for (x, y, r) in ((286, 90, 6), (322, 78, 5), (306, 60, 7)):
            g.shard(ellipse_poly(x, y, r * 2, r, n=8), '#2A1218', lw=0.8, op=0.7)
    g.lead_flush()


def scene_bannik(g, M, mood, rnd):
    # бревенчатая стена
    for i in range(8):
        y0 = -4 + i * 27
        c = ['#512717', '#7A3F24', '#6B351E', '#8A4A2B'][i % 4]
        g.shard([(-4, y0), (364, y0), (364, y0 + 27), (-4, y0 + 27)], T(M, c), lw=1.8, op=0.82)
    # окошко
    g.shard(rect_poly(274, 24, 56, 44), '#070B10', lw=0, grad=False, nolead=True)
    wc = {'neutral': '#2B3E9E', 'kind': '#2BC4BA', 'cunning': '#5B3FA0', 'angry': '#4A1428'}[mood]
    g.shard(rect_poly(278, 28, 48, 36), wc, lw=0)
    g.lead_line([(278, 28), (326, 28), (326, 64), (278, 64)], 3.0, closed=True)
    g.lead_line([(302, 28), (302, 64)], 2.2)
    # каменка с камнями
    for i, (x, y, r) in enumerate(((30, 180, 22), (64, 184, 20), (46, 160, 18), (86, 170, 14))):
        g.shard(ellipse_poly(x, y, r * 1.2, r * 0.8, n=9, rot=i), T(M, ['#3B4A5A', '#2A3644', '#506478'][i % 3]), lw=1.4)
    hc = {'neutral': '#E0652E', 'kind': '#F0A24A', 'cunning': '#9B5BE0', 'angry': '#FF3D2E'}[mood]
    g.glow(50, 172, 44, hc, 0.6)
    g.shard([(36, 178), (46, 172), (54, 180), (44, 186)], hc, lw=0.6)
    g.lead_flush()
    # пар
    sc = {'neutral': '#CFE6EE', 'kind': '#D8FFF4', 'cunning': '#C6B2F0', 'angry': '#FF9A86'}[mood]
    for (x, y, rx, ry) in ((60, 120, 38, 14), (100, 76, 30, 12), (300, 120, 42, 14), (320, 90, 26, 10), (90, 40, 34, 11), (250, 38, 28, 10)):
        n_ = 7 if mood == 'angry' else 10
        pl = ellipse_poly(x, y, rx, ry, n=n_, rot=rnd.random())
        if mood == 'angry':
            pl = [(px, py) if i % 2 == 0 else (x + (px - x) * 0.7, y + (py - y) * 0.7) for i, (px, py) in enumerate(pl)]
        g.shard(pl, sc, lw=0.8, op=0.38, grad=False)
    g.lead_flush()


def scene_poludnitsa(g, M, mood, rnd):
    # далёкие холмы
    hc = {'neutral': ('#15626E', '#1C4284'), 'kind': ('#17959C', '#1F9E6B'), 'cunning': ('#432C86', '#2A1F5C'), 'angry': ('#5A1A2E', '#3A1020')}[mood]
    g.shard([(-4, 130), (60, 112), (130, 126), (210, 108), (290, 122), (364, 106), (364, 204), (-4, 204)], hc[0], lw=1.4)
    g.shard([(-4, 150), (90, 138), (180, 152), (270, 136), (364, 148), (364, 204), (-4, 204)], hc[1], lw=1.4)
    # солнце
    sx, sy = 318, 38
    sun = {'neutral': '#F0C26A', 'kind': '#FFC772', 'cunning': '#D9B0F0', 'angry': '#FF6A4D'}[mood]
    rr = 21 if mood != 'angry' else 27
    g.glow(sx, sy, 70 if mood != 'angry' else 90, sun, 0.6 if mood != 'angry' else 0.75)
    g.shard(circle_poly(sx, sy, rr, n=12), sun, lw=1.6, grad=True)
    for k in range(10):
        a = math.radians(k * 36 + 10)
        L = (rr + 16) if k % 2 else (rr + 9)
        wd = math.radians(5)
        g.shard([(sx + (rr + 3) * math.cos(a - wd), sy + (rr + 3) * math.sin(a - wd)), (sx + L * math.cos(a), sy + L * math.sin(a)), (sx + (rr + 3) * math.cos(a + wd), sy + (rr + 3) * math.sin(a + wd))], sun, lw=0.9, grad=False, op=0.9)
    g.lead_flush()
    # рожь
    cs = ['#5E8A3E', '#7C9A4A', '#9A9A4A', '#4E7A3A']
    ear = '#D8A850' if mood != 'cunning' else '#C8A06A'
    for i in range(18):
        x = rnd.uniform(-6, 366)
        if 70 < x < 290 and rnd.random() < 0.55:
            continue
        h = rnd.uniform(60, 98)
        bend = rnd.uniform(-8, 8) * (1.6 if mood == 'angry' else 1)
        top = (x + bend, 204 - h)
        g.shard([(x - 2.6, 206), (x + 2.6, 206), (top[0] + 1.2, top[1]), (top[0] - 1.2, top[1])], T(M, cs[i % 4]), lw=0.8, grad=False)
        g.shard(ellipse_poly(top[0], top[1] - 6, 3.2, 8, n=6, rot=0), T(M, ear), lw=0.9, grad=False)
    if mood == 'kind':
        for (x, y) in ((40, 160), (96, 176), (262, 168), (330, 172), (20, 120)):
            g.shard(circle_poly(x, y, 4.2, n=7), '#3E6FD8', lw=0.8, grad=False)
            g.circle(x, y, 1.1, MILK, lw=0.3, grad=False)
    g.lead_flush()


def scene_vodyanoy(g, M, mood, rnd):
    wr = {'neutral': '#15626E', 'kind': '#17959C', 'cunning': '#432C86', 'angry': '#4A1428'}[mood]
    # мельничное колесо слева
    cx, cy, R = 56, 96, 62
    rim = T(M, '#512717')
    ring = []
    N = 10
    for i in range(N):
        a0, a1 = 2 * math.pi * i / N, 2 * math.pi * (i + 1) / N
        pl = [(cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1)),
              (cx + (R - 11) * math.cos(a1), cy + (R - 11) * math.sin(a1)), (cx + (R - 11) * math.cos(a0), cy + (R - 11) * math.sin(a0))]
        g.shard(pl, T(M, ['#7A3F24', '#512717', '#8A4A2B'][i % 3]), lw=1.4)
    for i in range(8):
        a = 2 * math.pi * i / 8 + 0.2
        quads, _ = chain_quads([(cx, cy), (cx + (R - 10) * math.cos(a), cy + (R - 10) * math.sin(a))], [7, 6])
        g.shard(quads[0], T(M, '#6B351E'), lw=1.2)
        # лопасти
        pa = a
        g.shard([(cx + (R - 2) * math.cos(pa - 0.12), cy + (R - 2) * math.sin(pa - 0.12)), (cx + (R + 9) * math.cos(pa - 0.05), cy + (R + 9) * math.sin(pa - 0.05)),
                 (cx + (R + 9) * math.cos(pa + 0.16), cy + (R + 9) * math.sin(pa + 0.16)), (cx + (R - 2) * math.cos(pa + 0.12), cy + (R - 2) * math.sin(pa + 0.12))], T(M, '#8A4A2B'), lw=1.0)
    g.shard(circle_poly(cx, cy, 9, n=8), T(M, '#3B4A5A'), lw=1.4)
    g.lead_flush()
    # камыши справа
    for x in (318, 336, 348):
        h = rnd.uniform(70, 110)
        g.shard([(x - 2, 206), (x + 2, 206), (x + 3, 206 - h), (x, 206 - h - 6), (x - 2, 206 - h)], T(M, '#1F9E6B'), lw=0.9, grad=False)
        g.shard(ellipse_poly(x, 206 - h - 12, 3.4, 9, n=6), T(M, '#7A3F24'), lw=0.9, grad=False)
    # вода
    for i in range(4):
        y0 = 150 + i * 14
        pts_ = [(-4, y0)]
        for k in range(1, 10):
            pts_.append((-4 + k * 41, y0 + (-4 if k % 2 else 3) * (2 if mood == 'angry' else 1)))
        pts_ += [(364, 206), (-4, 206)]
        g.shard(pts_, T(M, mix(wr, '#2BC4BA', 0.18 * (i % 3))), lw=1.2, op=0.9)
    g.lead_flush()


SCENES = {'leshy': scene_leshy, 'domovoy': scene_domovoy, 'bannik': scene_bannik, 'poludnitsa': scene_poludnitsa, 'vodyanoy': scene_vodyanoy}


# ---- фигуры --------------------------------------------------------------------------------------------------------
def figure(cid, g, M, mood, rnd):
    P = POSE[mood]
    sh = (122, 142 + P['shl'])
    sr = (238, 142 + P['shr'])
    tx = P['tx']
    if cid == 'leshy':
        skin = T(M, '#6E9A74')
        sleeve = ['#1F6B4A', '#136A47']
        torso(g, M, ['#1F6B4A', '#136A47', '#2E7A4A', '#0F4A35'], rnd, P['shl'], P['shr'], by=132)
        arm(g, M, sh, *P['L'], sleeve, skin, P['fl'])
        arm(g, M, sr, *P['R'], sleeve, skin, P['fr'])
        H = Head(180 + P['hx'], 92 + P['hy'], P['tilt'], 1.0)
        # мшистый воротник
        for k in range(6):
            x = 126 + k * 22
            g.shard([(x, 150 + (P['shl'] if x < 180 else P['shr'])), (x + 24, 150 + (P['shl'] if x < 180 else P['shr'])), (x + 12, 178)], T(M, ['#2E8A5A', '#1F9E6B', '#136A47'][k % 3]), lw=1.0)
        g.lead_flush()
        antlers(g, H, [T(M, '#7A3F24'), T(M, '#512717'), T(M, '#8A4A2B')], 1.0 + (0.25 if mood == 'angry' else 0), rnd)
        # мох-шапка
        for k in range(5):
            xs = -30 + k * 15
            g.shard(H.p([(xs, -20), (xs + 15, -20), (xs + 12, -42), (xs + 3, -38)]), T(M, ['#136A47', '#1F9E6B', '#2E8A5A'][k % 3]), lw=0.9)
        # шея
        g.shard(H.p([(-12, 24), (12, 24), (18, 48), (-18, 48)]), darken(skin, 0.25), lw=0.8, grad=False)
        beard(g, H, ['#136A47', '#1F9E6B', '#2E8A5A', '#6BC18A', '#0F5A3B'], rnd, w=29, L=66, jag=11)
        head_base(g, H, M, skin, HEAD_B, SEEDS_B)
        mustache(g, H, T(M, '#2E8A5A'), tx)
        g.shard(H.p([(-4 + tx, 15), (4 + tx, 15), (6 + tx, 28), (-6 + tx, 28)]), '#0F3A2A', lw=0.5, grad=False)
        face(g, H, M, mood, skin, T(M, '#1F6B4A'), tx=tx, my=19, bt=4.2)
        # уши
        for s in (-1, 1):
            g.shard(H.p([(s * 26, -6), (s * 38, -12), (s * 34, 4), (s * 26, 4)]), darken(skin, 0.1), lw=0.8)
        # подбородочные локоны перед грудью
        if mood in ('kind', 'cunning'):
            prop(g, M, cid, 'gift' if mood == 'kind' else 'trick', *(P['L'][1][0], P['L'][1][1]))
    elif cid == 'domovoy':
        skin = T(M, '#E7AD84')
        shirt = ['#C8454F', '#B8404E', '#932F46']
        torso(g, M, shirt, rnd, P['shl'], P['shr'], by=140, x0=100, x1=260)
        # пояс с узором
        g.shard([(104, 178), (256, 178), (258, 190), (102, 190)], T(M, '#2BC4BA'), lw=1.2)
        for i in range(9):
            g.shard([(114 + i * 16, 180), (122 + i * 16, 184), (114 + i * 16, 188), (108 + i * 16, 184)], T(M, '#EDE6D2'), lw=0.5, grad=False)
        arm(g, M, (126, 150 + P['shl']), *P['L'], shirt, skin, P['fl'], wid=(17, 14, 11))
        arm(g, M, (234, 150 + P['shr']), *P['R'], shirt, skin, P['fr'], wid=(17, 14, 11))
        H = Head(180 + P['hx'], 104 + P['hy'], P['tilt'], 0.92)
        g.shard(H.p([(-12, 24), (12, 24), (18, 44), (-18, 44)]), darken(skin, 0.25), lw=0.8, grad=False)
        # воротник-стойка
        g.shard([(158, 146 + P['shl']), (202, 146 + P['shr']), (206, 160), (154, 160)], T(M, '#EDE6D2'), lw=1.0)
        # волосы по бокам
        gray = [MILK, '#CBD5DC', '#9FB2C2', '#E6EDF2']
        for s in (-1, 1):
            g.shard(H.p([(s * 24, -26), (s * 36, -14), (s * 36, 10), (s * 26, 6), (s * 24, -10)]), T(M, '#CBD5DC'), lw=0.9)
        beard(g, H, gray, rnd, w=27, L=52, jag=8)
        head_base(g, H, M, skin, HEAD_B, SEEDS_B)
        # лысина с хохолком
        g.shard(H.p([(-20, -30), (0, -40), (20, -30), (14, -36), (0, -42), (-14, -36)]), T(M, '#CBD5DC'), lw=0.8)
        for k in range(3):
            g.shard(H.p([(-10 + k * 9, -36), (-5 + k * 9, -52), (-1 + k * 9, -36)]), T(M, gray[k]), lw=0.8)
        mustache(g, H, T(M, '#E6EDF2'), tx)
        g.shard(H.p([(-4 + tx, 15), (4 + tx, 15), (6 + tx, 27), (-6 + tx, 27)]), '#2A1820', lw=0.5, grad=False)
        # нос — картошкой
        face(g, H, M, mood, skin, T(M, '#E6EDF2'), tx=tx, my=19, bt=4.4, ey=-6)
        for s in (-1, 1):
            g.shard(H.p([(s * 26, -6), (s * 33, -9), (s * 31, 3), (s * 26, 3)]), darken(skin, 0.1), lw=0.8)
        if mood in ('kind', 'cunning'):
            prop(g, M, cid, 'gift' if mood == 'kind' else 'trick', *(P['L'][1][0], P['L'][1][1]))
    elif cid == 'bannik':
        skin = T(M, '#E0866A')
        torso(g, M, ['#E0866A', '#D0745C', '#C8644E', '#E69077'], rnd, P['shl'], P['shr'], by=132)
        # полотенце на плечах
        g.shard([(100, 160 + P['shl']), (150, 134 + P['shl']), (172, 160), (132, 204), (96, 204)], T(M, '#EDE6D2'), lw=1.4)
        g.shard([(260, 160 + P['shr']), (210, 134 + P['shr']), (188, 160), (228, 204), (264, 204)], T(M, '#C9D6E0'), lw=1.4)
        for k in range(4):
            g.shard([(108 + k * 6, 170 + k * 10), (120 + k * 6, 164 + k * 10), (122 + k * 6, 168 + k * 10), (110 + k * 6, 174 + k * 10)], T(M, '#2BC4BA'), lw=0.5, grad=False)
        sleeve = ['#E0866A', '#D0745C']
        arm(g, M, sh, *P['L'], sleeve, skin, P['fl'])
        # правая рука с веником
        Rel, Rhd = P['R']
        if mood == 'angry':
            Rel, Rhd = (278, 150), (290, 108)
        arm(g, M, sr, Rel, Rhd, sleeve, skin, P['fr'])
        ang = -12 if mood != 'angry' else -30
        base = Rhd
        tip = rotp((base[0], base[1] - 54), ang, base)
        quads, _ = chain_quads([(base[0], base[1] + 10), base, tip], [7, 6, 5])
        # ручка
        for q in quads:
            g.shard(q, T(M, '#7A3F24'), lw=1.0)
        # листва
        for k in range(7):
            a = ang + (-50 + k * 16.7)
            t0 = rotp((tip[0], tip[1]), 0, tip)
            tp = rotp((tip[0], tip[1] - 46 - (k % 2) * 6), a, tip)
            l = rotp((tip[0] - 6, tip[1] - 6), a, tip)
            r = rotp((tip[0] + 6, tip[1] - 6), a, tip)
            g.shard([l, tp, r], T(M, ['#1F9E6B', '#5FA84A', '#136A47', '#2E8A5A'][k % 4]), lw=0.9)
        g.lead_flush()
        H = Head(180 + P['hx'], 92 + P['hy'], P['tilt'], 1.0)
        g.shard(H.p([(-12, 24), (12, 24), (18, 46), (-18, 46)]), darken(skin, 0.25), lw=0.8, grad=False)
        # мокрые волосы вздыбились
        hcols = ['#8FA6BA', '#C9D6E0', '#6C86A0', '#A9BDCF']
        for k in range(7):
            x = -28 + k * 9.3
            g.shard(H.p([(x, -22), (x + 11, -22), (x + 5 + (k - 3) * 2.2, -52 - (k % 2) * 8)]), T(M, hcols[k % 4]), lw=0.9)
        beard(g, H, hcols, rnd, w=27, L=58, jag=9)
        head_base(g, H, M, skin, HEAD_B, SEEDS_B)
        mustache(g, H, T(M, '#C9D6E0'), tx)
        g.shard(H.p([(-4 + tx, 15), (4 + tx, 15), (6 + tx, 27), (-6 + tx, 27)]), '#2A1820', lw=0.5, grad=False)
        face(g, H, M, mood, skin, T(M, '#A9BDCF'), tx=tx, my=19, bt=4.2)
        for s in (-1, 1):
            g.shard(H.p([(s * 26, -6), (s * 35, -10), (s * 32, 4), (s * 26, 4)]), darken(skin, 0.1), lw=0.8)
        if mood in ('kind', 'cunning'):
            prop(g, M, cid, 'gift' if mood == 'kind' else 'trick', *(P['L'][1][0], P['L'][1][1]))
    elif cid == 'poludnitsa':
        skin = T(M, '#F2D2B8')
        dcols = ['#EDE6D2', '#DCE8F0', '#FFFBF0', '#C9D6E0']
        reg = [(70, 206), (110, 160), (146, 116 + P['shl']), (160, 108), (200, 108), (214, 116 + P['shr']), (250, 160), (290, 206)]
        seeds = [(106, 188), (148, 178), (180, 150), (212, 178), (256, 188), (130, 140), (230, 140), (180, 195), (168, 120), (194, 124)]
        g.mosaic(reg, seeds, lambda x, y, i: T(M, dcols[i % 4]), lw=1.3, grad=True)
        # вышивка / пояс
        g.shard([(120, 158), (240, 158), (248, 172), (112, 172)], T(M, '#C8454F'), lw=1.2)
        for i in range(6):
            g.shard([(130 + i * 20, 160), (138 + i * 20, 165), (130 + i * 20, 170), (124 + i * 20, 165)], T(M, '#EDE6D2'), lw=0.5, grad=False)
        shs = (148, 120 + P['shl'])
        shr_ = (212, 120 + P['shr'])
        slv = ['#EDE6D2', '#DCE8F0']
        arm(g, M, shs, *P['L'], slv, skin, P['fl'], wid=(15, 12, 10))
        arm(g, M, shr_, *P['R'], slv, skin, P['fr'], wid=(15, 12, 10))
        H = Head(180 + P['hx'], 70 + P['hy'], P['tilt'], 0.9)
        # длинные волосы
        hair = ['#2A1F3A', '#3A2A52', '#1A1226', '#4A3470']
        for s in (-1, 1):
            for k in range(3):
                g.shard(H.p([(s * (22 + k * 4), -28 + k * 4), (s * (36 + k * 3), -10), (s * (40 + k * 5), 40 + k * 8), (s * (24 + k * 3), 50 + k * 10), (s * 20, 6)]), T(M, hair[(k + (s > 0)) % 4]), lw=0.9)
        g.shard(H.p([(-12, 20), (12, 20), (16, 44), (-16, 44)]), darken(skin, 0.22), lw=0.8, grad=False)
        head_base(g, H, M, skin, [(-23, -22), (-16, -33), (0, -36), (16, -33), (23, -22), (23, 0), (18, 20), (8, 31), (0, 33), (-8, 31), (-18, 20), (-23, 0)],
                  [(-12, -18), (12, -18), (-12, 8), (12, 8), (0, 24)])
        # челка и венок
        for k in range(5):
            x = -22 + k * 9
            g.shard(H.p([(x, -22), (x + 10, -22), (x + 6 + (2 - k) * 1.5, -6 - (k % 2) * 4), (x - 1, -12)]), T(M, hair[k % 4]), lw=0.8)
        for k, x in enumerate(range(-22, 26, 8)):
            col = '#3E6FD8' if k % 2 == 0 else '#E0B35E'
            g.shard(circle_poly(*H.q(x, -33 + abs(x) * 0.12), 4.0 * H.sc, n=7), T(M, col), lw=0.8, grad=False)
        # лицо: чуть уже
        face(g, H, M, mood, skin, T(M, '#3A2A52'), tx=tx, ey=-2, ex=10, my=19, bt=3.0)
        if mood in ('kind', 'cunning'):
            prop(g, M, cid, 'gift' if mood == 'kind' else 'trick', *(P['L'][1][0], P['L'][1][1]))
    elif cid == 'vodyanoy':
        skin = T(M, '#4FA39A')
        scale = ['#1F9E6B', '#17959C', '#136A47', '#2BC4BA']
        torso(g, M, scale, rnd, P['shl'], P['shr'], by=136, n=12)
        # чешуя на груди
        for r in range(2):
            for c in range(6):
                x = 140 + c * 16 + (r % 2) * 8
                y = 158 + r * 14
                g.shard([(x - 7, y), (x, y - 6), (x + 7, y), (x, y + 8)], T(M, scale[(r + c) % 4]), lw=0.9)
        sleeve = ['#17959C', '#136A47']
        arm(g, M, sh, *P['L'], sleeve, skin, P['fl'])
        arm(g, M, sr, *P['R'], sleeve, skin, P['fr'])
        H = Head(180 + P['hx'], 90 + P['hy'], P['tilt'], 1.0)
        g.shard(H.p([(-12, 24), (12, 24), (20, 46), (-20, 46)]), darken(skin, 0.25), lw=0.8, grad=False)
        # перепончатые уши-плавники
        for s in (-1, 1):
            for k in range(3):
                g.shard(H.p([(s * 26, -8 + k * 3), (s * (46 - k * 2), -26 + k * 12), (s * (44 - k * 2), -6 + k * 12), (s * 27, 2 + k * 3)]), T(M, ['#2BC4BA', '#17959C', '#1F9E6B'][k]), lw=0.9)
        # волосы-водоросли и кувшинка
        al = ['#136A47', '#1F9E6B', '#2E8A5A', '#6BC18A', '#0F5A3B']
        for k in range(7):
            x = -28 + k * 9.3
            g.shard(H.p([(x, -22), (x + 11, -22), (x + 4 + (k - 3) * 3, -50 - (k % 2) * 9)]), T(M, al[k % 5]), lw=0.9)
        g.shard(ellipse_poly(*H.q(8, -48), 18 * H.sc, 7 * H.sc, n=9), T(M, '#1F9E6B'), lw=1.0)
        g.shard(circle_poly(*H.q(10, -53), 5.4 * H.sc, n=7), T(M, '#F7A8C0'), lw=0.8, grad=False)
        beard(g, H, al, rnd, w=29, L=70, n=8, jag=14)
        head_base(g, H, M, skin, HEAD_B, SEEDS_B)
        mustache(g, H, T(M, '#2E8A5A'), tx)
        g.shard(H.p([(-4 + tx, 15), (4 + tx, 15), (6 + tx, 28), (-6 + tx, 28)]), '#0B2A22', lw=0.5, grad=False)
        face(g, H, M, mood, skin, T(M, '#136A47'), tx=tx, my=19, bt=4.2, es=1.2, ex=13)
        if mood in ('kind', 'cunning'):
            prop(g, M, cid, 'gift' if mood == 'kind' else 'trick', *(P['L'][1][0], P['L'][1][1]))
    g.lead_flush()


# ---- сборка -------------------------------------------------------------------------------------------------------
def frame(g, M, mood):
    g.flush()
    vg = g.radial([(0.0, '#04070C', 0.0), (0.62, '#04070C', 0.0), (1.0, '#04070C', 0.62 if mood != 'angry' else 0.72)], 0.5, 0.5, 0.74)
    g.body.append(f'<rect width="{W}" height="{HH}" fill="{vg}"/>')
    g.body.append(f'<rect x="3" y="3" width="{W - 6}" height="{HH - 6}" fill="none" stroke="{LEAD}" stroke-width="6.5"/>')
    g.body.append(f'<rect x="7.5" y="7.5" width="{W - 15}" height="{HH - 15}" fill="none" stroke="{LEAD}" stroke-width="1.6" opacity="0.85"/>')
    g.body.append(f'<rect x="0.8" y="0.8" width="{W - 1.6}" height="{HH - 1.6}" fill="none" stroke="#2B3E55" stroke-width="0.8" opacity="0.8"/>')


def make(cid, mood, seed=7):
    M = MOODS[mood]
    rnd = random.Random(hash((cid, mood)) % 100000 if False else (sum(map(ord, cid)) * 31 + sum(map(ord, mood)) * 7 + seed))
    g = Glass(W, HH, 'g', prec=0, lw=M['lead'] * 0.8, light=FOCUS[cid])
    g.gmin = 10 ** 9
    g.gamt = 0.28
    bg_layer(g, M, mood, rnd, cid)
    mood_fx_back(g, M, mood, rnd, cid)
    g.lw = M['lead'] * 0.75
    SCENES[cid](g, M, mood, rnd)
    mood_fx_front(g, M, mood, rnd, cid)
    g.lw = M['lead'] * 0.7
    g.gmin = 1500
    g.prec = 0
    figure(cid, g, M, mood, rnd)
    g.prec = 0
    frame(g, M, mood)
    return g.render()


CREATURES = ['leshy', 'domovoy', 'bannik', 'poludnitsa', 'vodyanoy']
MOOD_LIST = ['neutral', 'kind', 'cunning', 'angry']


def sheet(files, path):
    from playwright.sync_api import sync_playwright
    cells = ''.join(f'<img src="file://{f}" width="360" height="200" style="margin:3px">' for f in files)
    html = f'<html><body style="margin:0;background:#222;width:{4 * 366}px">{cells}</body></html>'
    tmp = '/tmp/spirits_a_sheet.html'
    open(tmp, 'w').write(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 4 * 366, 'height': 5 * 206})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(300)
        pg.screenshot(path=path, full_page=True)
        b.close()


def main():
    args = sys.argv[1:]
    sheet_path = '/tmp/spirits_a_sheet.png'
    if '--sheet' in args:
        i = args.index('--sheet')
        sheet_path = args[i + 1]
        del args[i:i + 2]
    only = [a for a in args if a in CREATURES] or CREATURES
    os.makedirs(OUT, exist_ok=True)
    files = []
    for cid in only:
        for mood in MOOD_LIST:
            svg = make(cid, mood)
            size, problems = check_svg(f'{cid}_{mood}', svg, LIMIT)
            path = os.path.join(OUT, f'{cid}_{mood}.svg')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(svg)
            files.append(path)
            print(f'{cid}_{mood}.svg {size} B', '; '.join(problems))
    sheet(files, sheet_path)
    print('sheet', sheet_path)


if __name__ == '__main__':
    main()

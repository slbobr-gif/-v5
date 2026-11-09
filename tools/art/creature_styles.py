"""Пять вариантов стиля существ для «Путника»: леший (neutral, angry) и домовой (kind).

python3 creature_styles.py  ->  /home/claude/out/creature_styles/<style>_<creature>_<mood>.svg
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import (Svg, P, smooth, sym, mir, taper, tf, ell, drop, leaf, leaf_pts, spiral, lerp, mix, lt, dk,
                    LEAD, TURQ, CORAL, DANGER, PARCH, check, CX)

OUT = '/home/claude/out/creature_styles'

# ============================================================ общая анатомия
# Леший: голова (180, 78), борода до низа, рога-ветви.
L_FACE = sym([(180, 44), (166, 46), (155, 55), (150, 70), (151, 88), (157, 103), (168, 112), (180, 115)])
L_BEARD = sym([(180, 96), (163, 97), (151, 104), (146, 122), (143, 150), (140, 178), (136, 200), (180, 200)])
L_SHOULD = sym([(180, 116), (152, 120), (118, 130), (94, 146), (80, 170), (74, 200), (180, 200)])


def l_antler(side=1, spread=1.0):
    """Ветвистый рог: список (ломаная, w0, w1). side=1 — левый."""
    def pt(x, y):
        dx = (x - CX) * spread
        return (CX + dx * side, y) if side == 1 else (CX - dx, y)

    def pl(seq):
        return [pt(x, y) for x, y in seq]

    return [
        (pl([(166, 52), (160, 38), (152, 24), (147, 10), (145, 2)]), 7, 2),
        (pl([(158, 34), (146, 30), (134, 22), (126, 12)]), 4.5, 1.5),
        (pl([(151, 21), (158, 12), (161, 4)]), 3.5, 1.2),
        (pl([(140, 27), (134, 32), (124, 33)]), 3, 1),
    ]


def l_hair_leaves():
    """Листья-волосы вокруг головы: (x, y, угол, длина, ширина)."""
    out = []
    for i, a in enumerate([-160, -140, -118, -96, -84, -62, -40, -20]):
        r = 30 if i in (3, 4) else 32
        ang = math.radians(a)
        x, y = 180 + 26 * math.cos(ang), 74 + 34 * math.sin(ang)
        out.append((x, y, ang, 20 + (i % 2) * 4, 11))
    for side in (-1, 1):
        for j, (yy, a) in enumerate([(84, 160), (98, 150), (110, 140)]):
            ang = math.radians(a if side < 0 else 180 - a)
            out.append((180 + side * 25, yy, ang, 18 - j * 2, 9))
    return out


def l_arm(side, raise_=1.0):
    """Поднятая когтистая рука: рукав, кисть-сучья. side=-1 слева."""
    sh = (180 + side * 74, 140)
    el = (180 + side * 100, 120 - 6 * raise_)
    hd = (180 + side * 92, 84 - 8 * raise_)
    return sh, el, hd


L_NOSE = [(180, 68), (178.5, 78), (177, 88), (172.5, 95), (174, 101), (180, 103), (186, 101), (187.5, 95), (183, 88), (181.5, 78)]

# Домовой: голова (180, 98), большая борода, малое тело.
D_HAIR = sym([(180, 50), (168, 51), (158, 55), (149, 62), (143, 72), (139, 84), (138, 98), (141, 110), (180, 110)])
D_FACE = sym([(180, 78), (166, 80), (158, 88), (156, 100), (160, 110), (180, 114)])
D_BEARD = sym([(180, 104), (164, 105), (150, 112), (140, 126), (136, 144), (140, 162), (152, 176), (166, 183), (180, 185)])
D_BODY = sym([(180, 124), (156, 128), (134, 138), (120, 156), (114, 200), (180, 200)])


def bl(x, y, mood, side, w=14):
    """Бровь: внутренний конец -> внешний. side: -1 левый глаз (x<180), +1 правый."""
    ix = x - side * w * .45  # к переносице
    ox = x + side * w * .55  # наружу
    if mood == 'angry':
        return [(ix, y + 4.5), (x, y - 1), (ox, y - 6)]
    if mood == 'kind':
        return [(ix, y), (x, y - 4), (ox, y - 1.5)]
    return [(ix, y - .5), (x, y - 2), (ox, y)]


def ae(x, y, mood, side, w=11, h=6.5):
    """Глаз: белок-контур и центр радужки. side: -1 левый, +1 правый."""
    if mood == 'angry':
        ix, ox = x - side * w / 2, x + side * w / 2
        pts = [(ix, y - .5), (x - side * w * .1, y - h * .05), (ox, y - h * .55), (ox + side * .5, y + h * .05),
               (x + side * w * .1, y + h * .45), (x - side * w * .25, y + h * .4)]
        return pts, (x - side * .8, y + .6)
    up = [(x - w / 2 + w * i / 8, y - h / 2 * math.sin(math.pi * i / 8)) for i in range(9)]
    lo = [(x + w / 2 - w * i / 8, y + h / 2 * .85 * math.sin(math.pi * i / 8)) for i in range(1, 8)]
    return up + lo, (x, y + .2)


def happy_eye(x, y, w=11, h=5):
    return [(x - w / 2, y + 1.5), (x - w / 4, y - h * .55), (x, y - h * .7), (x + w / 4, y - h * .55), (x + w / 2, y + 1.5)]


# ============================================================ 1. ЧИСТЫЙ ВИТРАЖ
class Glass:
    key = 'glass'
    LW = 2.3

    def __init__(s):
        s.cache = {}

    def gl(s, S, c, ang=1):
        k = (id(S), c, ang)
        if k not in s.cache:
            s.cache[k] = S.lin([(0, lt(c, .2)), (.55, c), (1, dk(c, .22))], 0, 0, .3 * ang, 1) if ang else c
        return s.cache[k]

    def pane(s, S, p, c, sm_=False, lw=None, ang=1):
        d = smooth(p) if sm_ else P(p)
        S.path(d, fill=s.gl(S, c, ang), stroke=LEAD, stroke_width=lw or s.LW, stroke_linejoin='round')

    def sunburst(s, S, cx, cy, cols, n=14, r=300, rot=0.0):
        for i in range(n):
            a0 = rot + 2 * math.pi * i / n
            a1 = rot + 2 * math.pi * (i + 1) / n
            p = [(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))]
            S.path(P(p), fill=cols[i % len(cols)], stroke=LEAD, stroke_width=s.LW)

    def ring(s, S, cx, cy, r, col, op=.9):
        g = S.rad([(0, lt(col, .45), op), (.7, col, op * .7), (1, dk(col, .2), op * .6)], .5, .5, .5)
        S.el('circle', cx=cx, cy=cy, r=r, fill=g, stroke=LEAD, stroke_width=s.LW)

    def frame(s, S):
        S.el('rect', x=1.5, y=1.5, width=357, height=197, fill='none', stroke=LEAD, stroke_width=5, rx=3)
        g = S.rad([(0, '#000000', 0), (.7, '#000000', 0), (1, '#04070C', .55)], .5, .5, .72)
        S.el('rect', width=360, height=200, fill=g)

    def face(s, S, mood, ey, ex, skin, iris, brow_c, bw=15, ew=12, eh=7):
        for side in (-1, 1):
            x = 180 + side * ex
            if mood == 'kind':
                S.line(happy_eye(x, ey, ew, 6), LEAD, 2.6, smooth_=True)
            else:
                pts, (ix, iy) = ae(x, ey, mood, side, ew, eh)
                S.path(smooth(pts) if mood != 'angry' else P(pts), fill='#EDE6D2' if mood != 'angry' else '#2A0E12',
                       stroke=LEAD, stroke_width=1.6, stroke_linejoin='round')
                if mood == 'angry':
                    S.glow(ix, iy, 9, DANGER, .55)
                    S.el('circle', cx=ix, cy=iy, r=2.4, fill='#FFB3A8')
                else:
                    S.el('circle', cx=ix, cy=iy, r=2.9, fill=iris, stroke=LEAD, stroke_width=1)
                    S.el('circle', cx=ix, cy=iy, r=1.2, fill=LEAD)
            b = bl(x, ey - 7.5, mood, side, bw)
            S.path(P(taper(b, 3.5, 5.5 if mood != 'angry' else 6, None)), fill=s.gl(S, brow_c, 0), stroke=LEAD,
                   stroke_width=1.6, stroke_linejoin='round')

    # -------------------------------- леший
    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        S.el('rect', width=360, height=200, fill=LEAD)
        cols = ['#5A1A24', '#8E2E34', '#3E1219'] if A else ['#0F3B4C', '#155A6B', '#0C2C3C']
        s.sunburst(S, 180, 66, cols, 16, rot=.1)
        # стволы
        for x, w, lean in ((26, 22, 6), (62, 14, -3), (334, 22, -6), (298, 14, 3)):
            c = '#2A1418' if A else '#0B2430'
            s.pane(S, [(x - w / 2, 200), (x - w / 2 + lean, 0), (x + w / 2 + lean, 0), (x + w / 2, 200)], c, ang=0)
        s.ring(S, 180, 66, 60, CORAL if A else TURQ, .75)
        # рога
        bark = '#7A4A30' if A else '#6B5038'
        for side in (-1, 1):
            for line, w0, w1 in l_antler(1, 1.12 if A else 1.0):
                pts = line if side == -1 else mir(line)
                s.pane(S, taper(pts, w0 + 1.5, w1 + 1), bark, lw=2)
        # руки (злой)
        if A:
            for side in (-1, 1):
                sh, el, hd = l_arm(side)
                s.pane(S, taper([sh, el, hd], 26, 15), '#2E5A40')
                for k, a in enumerate((-.9, -.45, 0, .45)):
                    ang = -math.pi / 2 + side * .25 + a * .9
                    tip = (hd[0] + 22 * math.cos(ang), hd[1] + 22 * math.sin(ang))
                    mid = (hd[0] + 12 * math.cos(ang - side * .25), hd[1] + 12 * math.sin(ang - side * .25))
                    s.pane(S, taper([hd, mid, tip], 6, 1.2), '#7A4A30', lw=1.8)
                s.pane(S, ell(hd[0], hd[1] + 3, 9, 8, 10), '#6B5038', lw=1.8)
        # плечи / кафтан
        s.pane(S, L_SHOULD, '#244A38' if not A else '#2B3F33')
        # запах: левая пола поверх правой
        s.pane(S, [(150, 121), (196, 200), (232, 200), (172, 118)], '#3B6B4E' if not A else '#3D5A44')
        s.pane(S, [(118, 130), (128, 165), (110, 200), (76, 200), (80, 168), (94, 146)], '#1C3A2C', ang=0)
        s.pane(S, mir([(118, 130), (128, 165), (110, 200), (76, 200), (80, 168), (94, 146)]), '#1C3A2C', ang=0)
        # листья-волосы
        leafc = ['#2F8A55', '#46A86A', '#257048'] if not A else ['#7C3A2A', '#A04A30', '#5E3326']
        for i, (x, y, a, L, w) in enumerate(l_hair_leaves()):
            s.pane(S, tf(leaf_pts(L * (1.15 if A else 1), w / 2 * (0.8 if A else 1)), x, y, a), leafc[i % 3], lw=1.8)
        # лицо
        skin = '#7E9470' if not A else '#8A8A66'
        s.pane(S, L_FACE, skin, sm_=True)
        # нос
        s.pane(S, L_NOSE, lt(skin, .1), sm_=True, lw=1.8)
        s.face(S, mood, 77, 13, skin, TURQ, '#2D5C3E' if not A else '#3A2A20', bw=16)
        # рот (злой) — под усами
        if A:
            m = [(160, 103), (180, 99), (200, 103), (196, 116), (180, 121), (164, 116)]
            S.path(P(m), fill='#2A0E12', stroke=LEAD, stroke_width=2)
            for tx in (166, 174, 186, 194):
                S.path(P([(tx - 3, 104), (tx + 3, 104), (tx, 110)]), fill='#EDE6D2', stroke=LEAD, stroke_width=1)
            for tx in (170, 190):
                S.path(P([(tx - 3, 118), (tx + 3, 118), (tx, 112)]), fill='#EDE6D2', stroke=LEAD, stroke_width=1)
        # борода: крупные пряди
        bc = ['#2E7A50', '#3E9462', '#256846', '#4AA36E', '#2A7049'] if not A else ['#2E6A4A', '#3E7A56', '#24583E', '#4A8660', '#2A6046']
        strands = [(-30, 26), (-16, 22), (0, 22), (16, 22), (30, 26)]
        top = 118 if A else 104
        for i, (dx, w) in enumerate(strands):
            sp = 1.35 if A else 1.0
            line = [(180 + dx * .6, top), (180 + dx * .9 * sp, 150), (180 + dx * 1.05 * sp + (4 if A else 0) * (i - 2), 200)]
            s.pane(S, taper(line, w * .9, w * 1.15, w * 1.05), bc[i])
        # усы
        for side in (-1, 1):
            m = [(180, 99), (180 + side * 10, 98), (180 + side * 22, 104), (180 + side * 30, 116 if not A else 108),
                 (180 + side * 20, 110), (180 + side * 8, 106)]
            s.pane(S, m, '#3E9462' if not A else '#4A8660', lw=1.8)
        s.frame(S)
        return S

    # -------------------------------- домовой
    def domovoy(s, mood):
        S = Svg()
        S.el('rect', width=360, height=200, fill=LEAD)
        # бревенчатая стена — крупные горизонтальные стёкла
        for i, y in enumerate(range(0, 200, 34)):
            c = ['#3A2A2E', '#4A3236', '#342428'][i % 3]
            s.pane(S, [(0, y), (360, y + (4 if i % 2 else -2)), (360, y + 34 + (4 if i % 2 else -2)), (0, y + 34)], c, ang=0)
        # окно с луной
        s.pane(S, [(44, 26), (106, 26), (106, 92), (44, 92)], '#1B3F6E')
        S.glow(86, 46, 22, '#BFF5EE', .5)
        S.el('circle', cx=86, cy=46, r=9, fill='#DDF7F2', stroke=LEAD, stroke_width=2)
        S.line([(75, 26), (75, 92)], LEAD, 4)
        S.line([(44, 59), (106, 59)], LEAD, 4)
        # печь
        s.pane(S, [(244, 40), (330, 40), (330, 200), (244, 200)], '#C9BFAE', ang=1)
        for y in (70, 102, 134):
            S.line([(244, y), (330, y)], LEAD, 2)
        s.pane(S, [(256, 200), (256, 150), (262, 136), (287, 128), (312, 136), (318, 150), (318, 200)], '#3A1E1A', ang=0)
        S.glow(287, 182, 44, CORAL, .75)
        for k, (x, h) in enumerate(((272, 26), (287, 36), (302, 24))):
            s.pane(S, [(x - 9, 200), (x - 3, 200 - h * .6), (x, 200 - h), (x + 4, 200 - h * .5), (x + 9, 200)],
                   ['#E07A5F', '#F29B72', '#C8554F'][k], lw=1.6)
        # тёплый ореол
        s.ring(S, 180, 100, 62, '#E89A6E', .55)
        # тело
        s.pane(S, D_BODY, '#B2453F')
        s.pane(S, [(118, 172), (242, 172), (243, 182), (117, 182)], TURQ, ang=0)
        # руки + хлеб
        for side in (-1, 1):
            s.pane(S, taper([(180 + side * 52, 140), (180 + side * 54, 162), (180 + side * 32, 176)], 18, 14), '#B2453F')
            s.pane(S, ell(180 + side * 28, 176, 7, 6, 10), '#E3A98A', lw=1.8)
        # волосы
        hair = [(180, 48)]
        hp = sym([(180, 47), (170, 50), (162, 49), (156, 56), (148, 58), (146, 66), (139, 70), (140, 80), (134, 86),
                  (138, 96), (133, 104), (140, 112), (180, 112)])
        s.pane(S, hp, '#B9C2C9')
        s.pane(S, D_FACE, '#E3A98A', sm_=True)
        # щёки
        for side in (-1, 1):
            S.el('circle', cx=180 + side * 15, cy=104, r=5, fill='#E07A5F', fill_opacity=.6)
        s.face(S, mood, 96, 11, '#E3A98A', '#5BB5E8', '#EDF1F3', bw=14, ew=10, eh=6)
        # нос-картошка
        S.el('circle', cx=180, cy=103, r=5.5, fill=s.gl(S, '#D88F6E'), stroke=LEAD, stroke_width=1.8)
        # борода: 5 крупных стёкол
        bcol = ['#C7CED3', '#E4E8EA', '#D4DADE', '#E4E8EA', '#C7CED3']
        for i, dx in enumerate((-30, -15, 0, 15, 30)):
            line = [(180 + dx * .5, 108), (180 + dx * 1.15, 140), (180 + dx * .75, 182)]
            s.pane(S, taper(line, 14, 6, 24 - abs(dx) * .15), bcol[i])
        # улыбка в бороде
        if mood == 'kind':
            S.path(smooth([(168, 112), (174, 118), (180, 119.5), (186, 118), (192, 112), (180, 114)]), fill='#7A2E2A',
                   stroke=LEAD, stroke_width=1.8)
        # усы
        for side in (-1, 1):
            s.pane(S, [(180, 108), (180 + side * 12, 106), (180 + side * 24, 112), (180 + side * 14, 114), (180 + side * 4, 112)],
                   '#EEF1F3', lw=1.8)
        # хлеб
        s.pane(S, ell(180, 180, 22, 11, 14), '#B4683C')
        for x in (170, 180, 190):
            S.line([(x - 3, 175), (x + 3, 182)], LEAD, 1.6)
        s.frame(S)
        return S



# ============================================================ общие помощники 2–5
def scallops(a, b, n, depth, out=1):
    """Фестоны от a к b: n дуг, выпуклых по нормали (out=1 — влево от направления)."""
    pts = []
    dx, dy = b[0] - a[0], b[1] - a[1]
    h = math.hypot(dx, dy) or 1
    nx, ny = -dy / h * out, dx / h * out
    for i in range(n):
        for j in range(6):
            t = (i + j / 6) / n
            k = math.sin(math.pi * j / 6) * depth
            pts.append((a[0] + dx * t + nx * k, a[1] + dy * t + ny * k))
    pts.append(b)
    return pts


def wavy(a, b, amp, n, ph=0.0):
    pts = []
    dx, dy = b[0] - a[0], b[1] - a[1]
    h = math.hypot(dx, dy) or 1
    nx, ny = -dy / h, dx / h
    for i in range(n * 4 + 1):
        t = i / (n * 4)
        k = math.sin(t * n * 2 * math.pi + ph) * amp
        pts.append((a[0] + dx * t + nx * k, a[1] + dy * t + ny * k))
    return pts


def pine(x, yb, h, w, tiers=4):
    """Силуэт ели: ярусы-треугольники."""
    pts = [(x, yb - h)]
    for i in range(tiers):
        t1 = (i + 1) / tiers
        y = yb - h + h * t1
        ww = w * (.35 + .65 * t1)
        pts.append((x - ww / 2, y))
        if i < tiers - 1:
            pts.append((x - ww * .22, y - h / tiers * .15))
    left = pts
    right = [(2 * x - px, py) for px, py in reversed(left[1:])]
    return left + [(x - w * .06, yb), (x + w * .06, yb)][::1] + right if False else left + right


# ============================================================ 2. ЛУБОК
class Lubok:
    key = 'lubok'
    K = '#0B0F14'
    LW = 2.0

    def f_(s, S, p, c, lw=None, sm_=False):
        S.path(smooth(p) if sm_ else P(p), fill=c, stroke=s.K, stroke_width=lw or s.LW, stroke_linejoin='round')

    def hatch(s, S, x0, y0, x1, y1, step, col, ang=.6, w=1.2, inside=None):
        """Короткие косые штрихи в прямоугольнике (гравюрная штриховка)."""
        y = y0
        row = 0
        segs = []
        while y < y1:
            x = x0 + (row % 2) * step / 2
            while x < x1:
                if inside is None or inside(x, y):
                    segs.append([(x, y), (x + 4 * math.cos(ang), y + 4 * math.sin(ang))])
                x += step
            y += step * .8
            row += 1
        S.lines(segs, col, w)

    def band(s, S, y, h, A):
        base = '#2A1C22' if A else '#1A2638'
        S.el('rect', x=0, y=y, width=360, height=h, fill=base)
        S.line([(0, y), (360, y)], s.K, 2)
        S.line([(0, y + h), (360, y + h)], s.K, 2)
        dia = [[(i, y + h / 2), (i + 9, y + 2.5), (i + 18, y + h / 2), (i + 9, y + h - 2.5), (i, y + h / 2)] for i in range(0, 361, 18)]
        S.lines(dia, PARCH, 1.1, stroke_opacity=.55)
        for k, c in enumerate((CORAL, TURQ)):
            S.path(''.join(P(ell(i + 9, y + h / 2, 2.2, 2.2, 6)) for i in range(k * 18, 361, 36)), fill=c)

    def tulip(s, S, x, y, c, sc=1.0):
        S.line([(x, y), (x + 1, y - 14 * sc)], '#2E7A50', 2.2)
        s.f_(S, tf([(0, 0), (-7, -4), (-6, -12), (-3, -8), (0, -14), (3, -8), (6, -12), (7, -4)], x + 1, y - 13 * sc, 0, sc), c, 1.4)
        s.f_(S, tf(leaf_pts(10, 3), x, y - 4 * sc, -2.4, sc), '#3E9462', 1.2)
        s.f_(S, tf(leaf_pts(10, 3), x + 1, y - 5 * sc, -.7, sc), '#3E9462', 1.2)

    def tree(s, S, x, yb, h, w, A, bend=0.0):
        s.f_(S, taper([(x, yb), (x + bend * .3, yb - h * .4), (x + bend, yb - h)], 9, 4), '#5A3A2A', 1.6)
        crown = '#1F5A3E' if not A else '#3E2A24'
        for i in range(3):
            yy = yb - h * .32 - i * h * .24
            ww = w * (1 - i * .24)
            xx = x + bend * (.4 + i * .25)
            pts = scallops((xx + ww / 2, yy), (xx - ww / 2, yy), 4 - (i > 1), 7 - i, out=1)
            s.f_(S, pts + [(xx, yy - h * .34)], crown, 1.6)
            for j in range(3 - (i > 1)):
                S.el('circle', cx=xx - ww * .25 + j * ww * .25, cy=yy - 5, r=1.8, fill=CORAL if not A else '#FF8A6E')

    def face_lub(s, S, mood, ey, ex, er=6.5, cheek=True, brow_c=None, iris='#1A2638'):
        K = s.K
        for side in (-1, 1):
            x = 180 + side * ex
            if mood == 'kind':
                S.line(happy_eye(x, ey, 12, 6), K, 2.6, smooth_=True)
            elif mood == 'angry':
                pts, (ix, iy) = ae(x, ey, mood, side, 14, 9)
                S.path(P(pts), fill=PARCH, stroke=K, stroke_width=2, stroke_linejoin='round')
                S.el('circle', cx=ix, cy=iy, r=3, fill=CORAL, stroke=K, stroke_width=1)
                S.el('circle', cx=ix, cy=iy, r=1.2, fill=K)
            else:
                S.el('circle', cx=x, cy=ey, r=er, fill=PARCH, stroke=K, stroke_width=2)
                S.el('circle', cx=x + side * -1, cy=ey + .5, r=3.2, fill=iris)
                S.el('circle', cx=x + side * -1 - 1, cy=ey - .6, r=1, fill=PARCH)
            b = bl(x, ey - 10, mood, side, 17)
            S.path(P(taper(b, 3, 5.5)), fill=brow_c or K, stroke=K, stroke_width=1)
            if cheek and mood != 'angry':
                S.el('circle', cx=180 + side * (ex + 5), cy=ey + 15, r=5.5, fill=CORAL, fill_opacity=.85)

    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        K = s.K
        S.el('rect', width=360, height=200, fill='#141C2B' if not A else '#2A1216')
        # звёздочки-розетки
        for x, y in ((92, 44), (268, 40), (118, 92), (244, 96)):
            for k in range(4):
                a = k * math.pi / 2 + .4
                S.path(leaf(x, y, a, 7, 3.5), fill=TURQ if not A else CORAL, fill_opacity=.55)
        # земля
        S.path(P([(0, 168), (90, 162), (180, 166), (270, 160), (360, 166), (360, 200), (0, 200)]), fill='#1F4A36' if not A else '#3A2420',
               stroke=K, stroke_width=2)
        s.tree(S, 52, 176, 128, 58, A, bend=-10 if A else 0)
        s.tree(S, 308, 176, 128, 58, A, bend=10 if A else 0)
        for x, c in ((88, CORAL), (104, TURQ), (258, TURQ), (274, CORAL)):
            s.tulip(S, x, 182, c)
        if A:
            for (x, y, sg) in ((96, 60, 1), (266, 56, -1), (110, 132, 1), (250, 128, -1)):
                S.line(spiral(x, y, 1, 11, 1.4, 0, 14, sg), CORAL, 2.4, smooth_=True)
        # рога с листьями
        for side in (-1, 1):
            for line, w0, w1 in l_antler(1, 1.15 if A else 1.0):
                pts = line if side == -1 else mir(line)
                s.f_(S, taper(pts, w0 + 1, w1 + .8), '#7A5236', 1.6)
            for (x, y, a) in ((128, 12, -2.5), (160, 4, -1.2), (124, 33, 2.9)):
                xx = x if side == -1 else 360 - x
                aa = a if side == -1 else math.pi - a
                s.f_(S, tf(leaf_pts(11, 4), xx, y, aa), '#3E9462' if not A else '#A04A30', 1.3)
        # руки (злой)
        if A:
            for side in (-1, 1):
                sh, el, hd = l_arm(side)
                s.f_(S, taper([sh, el, hd], 24, 14), '#B2453F')
                for a in (-.95, -.5, -.05, .4):
                    ang = -math.pi / 2 + side * .25 + a * .9
                    tip = (hd[0] + 20 * math.cos(ang), hd[1] + 20 * math.sin(ang))
                    s.f_(S, taper([hd, tip], 5, 1.2), '#7A5236', 1.4)
                S.el('circle', cx=hd[0], cy=hd[1] + 2, r=7.5, fill='#9DB08A', stroke=K, stroke_width=2)
        # кафтан
        coat = '#B2453F'
        s.f_(S, L_SHOULD, coat)
        s.hatch(S, 80, 132, 280, 200, 10, dk(coat, .45), inside=lambda x, y: abs(x - 180) > 52 + (200 - y) * .1)
        # оторочка-узор по запаху
        tr = [(150, 121), (200, 200), (222, 200), (170, 118)]
        s.f_(S, tr, PARCH, 1.6)
        for t in (.25, .45, .65, .85):
            p = lerp((160, 120), (211, 200), t)
            S.path(P([(p[0], p[1] - 4), (p[0] + 4, p[1]), (p[0], p[1] + 4), (p[0] - 4, p[1])]), fill=CORAL, stroke=K, stroke_width=1)
        # волосы — лопасти
        hairc = '#2E7A50' if not A else '#5E3326'
        for i, (x, y, a, L, w) in enumerate(l_hair_leaves()):
            s.f_(S, tf(leaf_pts(L * (1.2 if A else 1.05), w / 2 * (.75 if A else 1.05)), x, y, a), hairc if i % 2 else lt(hairc, .18), 1.6)
        # лицо
        skin = '#A9B78E' if not A else '#B4A27E'
        s.f_(S, L_FACE, skin, sm_=True)
        s.f_(S, L_NOSE, lt(skin, .12), 1.6, sm_=True)
        s.face_lub(S, mood, 77, 14, brow_c='#1F3A2A')
        # борода — фестоны
        bc = '#2E7A50' if not A else '#2E6A4A'
        bh = sym([(180, 98), (162, 98), (150, 106), (144, 128), (140, 160), (134, 186)] + [(180, 186)])
        bottom = scallops((226, 186), (134, 186), 5, 9, out=1)
        poly = bh[:6] + bottom + bh[6:]
        bpts = [(180, 98), (162, 98), (150, 106), (144, 128), (140, 160), (134, 186)]
        outline = bpts + scallops((134, 186), (226, 186), 5, 9, out=-1)[1:-1] + mir(bpts)[::-1][:-1]
        if A:
            outline = [(x + (x - 180) * .2, y) for x, y in outline]
        s.f_(S, outline, bc)
        for k, dx in enumerate((-28, -14, 0, 14, 28)):
            dx2 = dx * (1.2 if A else 1)
            S.line(wavy((180 + dx * .5, 108), (180 + dx2 * 1.2, 182), 2.2, 3, k), lt(bc, .35), 1.6, smooth_=True)
        # рот
        if A:
            m = [(160, 102), (180, 98), (200, 102), (196, 118), (180, 124), (164, 118)]
            s.f_(S, m, '#4A1418')
            for tx in (166, 174, 186, 194):
                S.path(P([(tx - 3, 103), (tx + 3, 103), (tx, 110)]), fill=PARCH, stroke=K, stroke_width=1)
        # усы
        for side in (-1, 1):
            m = [(180, 98), (180 + side * 12, 97), (180 + side * 24, 104), (180 + side * 30, 112 if not A else 104),
                 (180 + side * 18, 108), (180 + side * 6, 105)]
            s.f_(S, m, lt(bc, .15), 1.6, sm_=True)
        s.band(S, 0, 14, A)
        S.el('rect', x=1, y=1, width=358, height=198, fill='none', stroke=K, stroke_width=3)
        return S

    def domovoy(s, mood):
        S = Svg()
        K = s.K
        S.el('rect', width=360, height=200, fill='#1A1F33')
        # стена с росписью-ромбами
        for x in range(10, 360, 30):
            for y in range(28, 160, 30):
                S.path(P([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]), fill=TURQ if (x // 30 + y // 30) % 2 else CORAL,
                       fill_opacity=.35)
        # окошко
        s.f_(S, [(46, 30), (104, 30), (104, 90), (46, 90)], '#24467A', 3)
        S.el('circle', cx=88, cy=48, r=8, fill=PARCH, stroke=K, stroke_width=1.6)
        S.line([(75, 30), (75, 90)], K, 3)
        S.line([(46, 60), (104, 60)], K, 3)
        s.f_(S, [(40, 90), (110, 90), (114, 98), (36, 98)], '#7A5236', 1.8)
        # печь с изразцами
        s.f_(S, [(240, 34), (334, 34), (334, 200), (240, 200)], '#D9CCB0', 2.4)
        for r in range(4):
            for c in range(3):
                x, y = 248 + c * 28, 40 + r * 24
                if r >= 2 and c == 1:
                    continue
                s.f_(S, [(x, y), (x + 22, y), (x + 22, y + 18), (x, y + 18)], '#E9DFC8', 1.2)
                S.path(leaf(x + 11, y + 15, -math.pi / 2, 11, 6), fill=TURQ if (r + c) % 2 else CORAL, stroke=K, stroke_width=.8)
        s.f_(S, [(258, 200), (258, 150), (264, 138), (287, 132), (310, 138), (316, 150), (316, 200)], '#3A1E1A', 2.4)
        for k, (x, h, c) in enumerate(((274, 26, CORAL), (287, 38, '#F29B72'), (300, 24, CORAL))):
            s.f_(S, [(x - 8, 198), (x - 4, 198 - h * .5), (x, 198 - h), (x + 5, 198 - h * .45), (x + 8, 198)], c, 1.4)
        # пол
        S.path(P([(0, 186), (240, 186), (240, 200), (0, 200)]), fill='#5A3A2A', stroke=K, stroke_width=2)
        # тело
        s.f_(S, D_BODY, '#B2453F')
        s.hatch(S, 114, 132, 246, 200, 8, dk('#B2453F', .45), inside=lambda x, y: abs(x - 180) > 44)
        s.f_(S, [(116, 170), (244, 170), (245, 179), (115, 179)], TURQ, 1.6)
        for x in range(124, 240, 12):
            S.path(P([(x, 171.5), (x + 4, 174.5), (x, 177.5), (x - 4, 174.5)]), fill=CORAL)
        for side in (-1, 1):
            s.f_(S, taper([(180 + side * 52, 140), (180 + side * 54, 160), (180 + side * 32, 174)], 18, 14), '#B2453F')
        # волосы-лохмы
        hp = sym([(180, 47), (170, 50), (162, 48), (156, 56), (148, 57), (146, 66), (138, 70), (140, 80), (133, 86),
                  (138, 96), (132, 104), (140, 112), (180, 112)])
        s.f_(S, hp, '#C9CFD3')
        for k in range(5):
            x = 152 + k * 14
            S.line(wavy((x, 58), (x + (k - 2) * 3, 76), 1.5, 2), '#8E979E', 1.4, smooth_=True)
        s.f_(S, D_FACE, '#E8B08E', sm_=True)
        s.face_lub(S, mood, 96, 11, er=5, cheek=True, brow_c='#F2F2EE')
        S.el('circle', cx=180, cy=103, r=5.5, fill='#E08C70', stroke=K, stroke_width=1.6)
        # борода-фестоны
        bp = [(180, 106), (164, 106), (150, 112), (140, 126), (136, 144), (140, 162)]
        outline = bp + scallops((140, 162), (220, 162), 4, 12, out=-1)[1:-1] + mir(bp)[::-1][:-1]
        s.f_(S, outline, '#ECEFF0')
        for k, dx in enumerate((-22, -8, 8, 22)):
            S.line(wavy((180 + dx * .6, 118), (180 + dx, 166), 2, 3, k), '#A9B2B8', 1.4, smooth_=True)
        if mood == 'kind':
            S.path(smooth([(168, 112), (174, 118), (180, 119.5), (186, 118), (192, 112), (180, 114)]), fill='#8A2E2A', stroke=K,
                   stroke_width=1.6)
        for side in (-1, 1):
            s.f_(S, [(180, 108), (180 + side * 12, 106), (180 + side * 24, 112), (180 + side * 14, 115), (180 + side * 4, 112)], PARCH,
                 1.5, sm_=True)
        # руки и каравай
        for side in (-1, 1):
            S.el('circle', cx=180 + side * 28, cy=174, r=6.5, fill='#E8B08E', stroke=K, stroke_width=1.8)
        s.f_(S, ell(180, 178, 22, 10, 16), '#B4683C')
        for x in (170, 180, 190):
            S.line([(x - 3, 173), (x + 3, 181)], K, 1.5)
        s.band(S, 0, 14, False)
        S.el('rect', x=1, y=1, width=358, height=198, fill='none', stroke=K, stroke_width=3)
        return S


# ============================================================ 3. СИЛУЭТ С СИЯНИЕМ
class Silhouette:
    key = 'silhouette'
    BLK = '#04070A'

    def sky(s, S, top, bot):
        S.el('rect', width=360, height=200, fill=S.lin([(0, top), (1, bot)]))

    def mist(s, S, y, col, op):
        S.path(smooth([(-20, y), (60, y - 6), (140, y + 2), (220, y - 5), (300, y + 3), (380, y - 4), (380, y + 30), (-20, y + 30)]),
               fill=col, fill_opacity=op)

    def pines(s, S, xs, yb, hs, col):
        for x, h in zip(xs, hs):
            S.path(P(pine(x, yb, h, h * .42, 5)), fill=col)

    def sil(s, S, shapes, rim, rw=2.6, rop=.75):
        for d in shapes:
            S.path(d, fill='none', stroke=rim, stroke_width=rw, stroke_opacity=rop, stroke_linejoin='round')
        for d in shapes:
            S.path(d, fill=s.BLK)

    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        if A:
            s.sky(S, '#1A070B', '#4A1418')
            moon, glowc, far, near = '#FFB09A', DANGER, '#3A0F16', '#22080D'
        else:
            s.sky(S, '#061019', '#0F3A44')
            moon, glowc, far, near = '#D8FFF8', TURQ, '#0D2B35', '#081A22'
        S.glow(180, 72, 150, glowc, .45, .3)
        S.el('circle', cx=180, cy=72, r=54, fill=S.rad([(0, moon), (.8, mix(moon, glowc, .4)), (1, glowc)], .5, .5, .5))
        s.pines(S, [20, 52, 84, 276, 308, 340], 170, [120, 96, 70, 74, 100, 124], far)
        s.mist(S, 140, glowc, .16)
        s.pines(S, [6, 40, 322, 356], 200, [150, 120, 126, 156], near)
        # силуэт
        shapes = []
        for side in (-1, 1):
            for line, w0, w1 in l_antler(1, 1.2 if A else 1.0):
                pts = line if side == -1 else mir(line)
                shapes.append(P(taper(pts, w0 + .5, w1 + .3)))
        for i, (x, y, a, L, w) in enumerate(l_hair_leaves()):
            shapes.append(leaf(x, y, a, L * (1.25 if A else 1.05), w * (.7 if A else .95)))
        if A:
            for side in (-1, 1):
                sh, el, hd = l_arm(side, 1.3)
                shapes.append(P(taper([sh, el, hd], 22, 10)))
                for a in (-1.0, -.55, -.1, .35):
                    ang = -math.pi / 2 + side * .3 + a * .9
                    mid = (hd[0] + 12 * math.cos(ang - side * .3), hd[1] + 12 * math.sin(ang - side * .3))
                    tip = (hd[0] + 26 * math.cos(ang), hd[1] + 26 * math.sin(ang))
                    shapes.append(P(taper([hd, mid, tip], 6, .6)))
        shapes.append(smooth(L_FACE))
        shapes.append(P(L_SHOULD))
        # борода с рваным краем
        bp = [(180, 96), (162, 97), (150, 104), (145, 124), (142, 152), (138, 182)]
        jag = []
        for k in range(9):
            x = 138 + k * 10.5
            jag += [(x, 182 + (k % 2) * 4), (x + 5, 196 + (k % 3) * 2)]
        outline = bp + jag + mir(bp)[::-1][:-1]
        if A:
            outline = [(x + (x - 180) * .22, y) for x, y in outline]
        shapes.append(P(outline))
        s.sil(S, shapes, moon if not A else '#FF9A86', 2.6, .6)
        # глаза
        ec = TURQ if not A else DANGER
        for side in (-1, 1):
            x = 180 + side * 13
            pts, (ix, iy) = ae(x, 77, mood, side, 14 if A else 13, 7 if A else 7.5)
            S.glow(x, 77, 16, ec, .55)
            S.path(smooth(pts) if not A else P(pts), fill=lt(ec, .45))
            if not A:
                S.el('circle', cx=ix, cy=iy, r=1.8, fill=s.BLK)
            b = bl(x, 69, mood, side, 16)
            if A:
                S.path(P(taper(b, 2.5, 3.5)), fill=lt(ec, .2), fill_opacity=.8)
        if A:
            m = [(164, 104), (172, 101), (180, 103), (188, 101), (196, 104), (192, 116), (180, 122), (168, 116)]
            S.glow(180, 110, 22, DANGER, .45)
            S.path(P(m), fill='#FF8A7A')
            for tx in (168, 176, 184, 192):
                S.path(P([(tx - 3, 102), (tx + 3, 102), (tx, 109)]), fill=s.BLK)
            for tx in (172, 188):
                S.path(P([(tx - 3, 121), (tx + 3, 121), (tx, 114)]), fill=s.BLK)
            # летящие листья
            for (x, y, a) in ((60, 40, .5), (300, 60, 2.4), (84, 110, -.4), (282, 120, 3.4), (120, 20, 1.2), (250, 16, 2.0)):
                S.path(leaf(x, y, a, 9, 4), fill=s.BLK, stroke='#FF9A86', stroke_width=.8, stroke_opacity=.7)
        else:
            # светлячки
            for (x, y) in ((70, 120), (96, 92), (284, 104), (258, 132), (300, 70)):
                S.glow(x, y, 7, TURQ, .7)
                S.el('circle', cx=x, cy=y, r=1.3, fill='#DFFFFB')
        s.mist(S, 176, glowc, .14)
        return S

    def domovoy(s, mood):
        S = Svg()
        s.sky(S, '#0A0F17', '#141A26')
        # большое окно в лунном свете позади
        S.glow(180, 84, 140, TURQ, .3, .3)
        S.path(P([(112, 16), (248, 16), (248, 150), (112, 150)]), fill=S.lin([(0, '#BFF5EE'), (1, '#2E8C8A')]))
        S.el('circle', cx=222, cy=40, r=11, fill='#F2FFFD')
        S.glow(222, 40, 26, '#F2FFFD', .5)
        for x in (156, 204):
            S.path(P([(x - 2.5, 16), (x + 2.5, 16), (x + 2.5, 150), (x - 2.5, 150)]), fill=s.BLK)
        S.path(P([(112, 80), (248, 80), (248, 85), (112, 85)]), fill=s.BLK)
        # тёплая печь справа: силуэт с трубой и устьем
        S.glow(310, 172, 100, CORAL, .5, .35)
        S.path(P([(266, 200), (266, 70), (276, 60), (330, 60), (330, 30), (346, 30), (346, 60), (360, 60), (360, 200)]), fill=s.BLK)
        S.path(P([(284, 200), (284, 164), (290, 152), (308, 146), (326, 152), (332, 164), (332, 200)]),
               fill=S.lin([(0, '#FFC9A8'), (.5, '#F08A6E'), (1, '#B2453F')]))
        for x, h in ((298, 22), (308, 32), (318, 20)):
            S.path(P([(x - 6, 200), (x, 200 - h), (x + 6, 200)]), fill='#FFE2D2', fill_opacity=.8)
        # подоконник, стол слева, кот
        S.path(P([(100, 150), (260, 150), (260, 158), (100, 158)]), fill=s.BLK)
        S.path(P([(0, 186), (360, 186), (360, 200), (0, 200)]), fill=s.BLK)
        # кот на подоконнике
        cat = [(120, 150), (118, 138), (122, 126), (126, 120), (124, 112), (128, 115), (133, 114), (136, 111), (137, 120),
               (140, 132), (144, 150)]
        S.path(smooth(cat), fill=s.BLK)
        S.line([(144, 148), (152, 146), (156, 138)], s.BLK, 3, smooth_=True)
        # домовой
        shapes = []
        hp = sym([(180, 46), (171, 50), (163, 47), (157, 55), (148, 56), (146, 65), (137, 69), (139, 80), (132, 86),
                  (137, 96), (131, 104), (139, 112), (180, 112)])
        shapes.append(P(hp))
        bp = [(180, 104), (164, 105), (150, 112), (140, 126), (136, 144), (140, 162)]
        shapes.append(P(bp + scallops((140, 162), (220, 162), 5, 8, out=-1)[1:-1] + mir(bp)[::-1][:-1]))
        shapes.append(P(D_BODY))
        for side in (-1, 1):
            shapes.append(P(taper([(180 + side * 52, 140), (180 + side * 54, 160), (180 + side * 30, 172)], 18, 14)))
        s.sil(S, shapes, '#DFFFFB', 2.8, .75)
        # контур бороды поверх тела — тонкий свет
        S.path(P(bp + scallops((140, 162), (220, 162), 5, 8, out=-1)[1:-1] + mir(bp)[::-1][:-1]), fill='none',
               stroke='#DFFFFB', stroke_width=1.2, stroke_opacity=.35)
        # свеча в ладонях: тёплый свет снизу
        S.glow(180, 160, 46, '#FFB08A', .55)
        S.path(P([(172, 186), (172, 166), (188, 166), (188, 186)]), fill='#F4E6DA')
        S.path(drop(180, 166, -math.pi / 2, 14, 7), fill='#FFE7D6')
        for side in (-1, 1):
            S.path(smooth(ell(180 + side * 13, 180, 8, 7, 10)), fill=s.BLK)
        # глаза-дуги, светятся
        for side in (-1, 1):
            x = 180 + side * 11
            S.glow(x, 95, 12, '#FFC2A0', .5)
            S.line(happy_eye(x, 96, 11, 6), '#FFE2D2', 2.6, smooth_=True)
        S.glow(180, 112, 10, CORAL, .35)
        S.path(smooth([(170, 110), (175, 115), (180, 116.5), (185, 115), (190, 110), (180, 112)]), fill='#FFB09A')
        return S


# ============================================================ 4. РОСПИСЬ (гжель-ночь / жостово)
class Rospis:
    key = 'rospis'

    def setup(s, S, A):
        s.gz = S.rad([(0, '#F4F8FF'), (.45, '#7FA8E8'), (1, '#1D4398')], .3, .3, .85)
        s.gt = S.rad([(0, '#E8FFFC'), (.45, '#5FE0D5'), (1, '#127A78')], .3, .3, .85)
        s.gc = S.rad([(0, '#FFE6DC'), (.45, '#F08A6E'), (1, '#9E2F35')], .3, .3, .85)
        s.gw = S.rad([(0, '#FFFFFF'), (.55, '#DCE6F5'), (1, '#6F8FC8')], .3, .3, .85)

    def bg(s, S, A):
        c0, c1 = ('#14294A', '#060B16') if not A else ('#3A1220', '#0E0509')
        S.el('rect', width=360, height=200, fill=S.rad([(0, c0), (1, c1)], .5, .45, .75))
        # кайма-«травка» сверху и снизу
        segs = []
        for x in range(6, 360, 14):
            segs.append([(x, 8), (x + 4, 3), (x + 9, 5)])
            segs.append([(x, 192), (x + 4, 197), (x + 9, 195)])
        S.lines(segs, TURQ if not A else CORAL, 1.3, stroke_opacity=.7)
        S.el('rect', x=4, y=11, width=352, height=178, rx=10, fill='none', stroke=TURQ if not A else CORAL, stroke_width=1,
             stroke_opacity=.45)

    def berries(s, S, x, y, n=3, r=4.2, g=None):
        for k in range(n):
            a = -math.pi / 2 + (k - (n - 1) / 2) * 1.1
            bx, by = x + r * 1.3 * math.cos(a), y + r * 1.3 * math.sin(a) + r
            S.el('circle', cx=bx, cy=by, r=r, fill=g or s.gc)
            S.el('circle', cx=bx - r * .35, cy=by - r * .35, r=r * .28, fill='#FFF4EE')

    def spray(s, S, x0, y0, side, A, scale=1.0):
        """Ветка с каплями-листьями и ягодами из нижнего угла, side=1 — вправо."""
        stem = [(x0, y0), (x0 + side * 18 * scale, y0 - 40 * scale), (x0 + side * 8 * scale, y0 - 80 * scale),
                (x0 + side * 26 * scale, y0 - 112 * scale)]
        S.path(P(taper(stem, 4, 1.2)), fill=TURQ if not A else '#C8554F')
        sp = spiral(stem[-1][0] + side * 6, stem[-1][1] + 2, 7, 1.5, 1.1, math.pi, 14, side)
        S.line(sp, TURQ if not A else '#C8554F', 1.6, smooth_=True)
        for i in range(1, 7):
            t = i / 7
            seg = min(int(t * 3), 2)
            p = lerp(stem[seg], stem[seg + 1], t * 3 - seg)
            for sgn in (-1, 1):
                a = -math.pi / 2 + sgn * (1.0 + .2 * (i % 2)) + side * .15
                S.path(drop(p[0], p[1], a, 16 * scale, 7 * scale), fill=s.gt if (i + sgn) % 2 else s.gz)
        if A:
            for k, (dx, dy) in enumerate(((side * 22, -54), (side * 4, -96), (side * 34, -24))):
                S.path(drop(x0 + dx, y0 + dy, -math.pi / 2, 18, 9), fill=s.gc)
                S.path(drop(x0 + dx - 5, y0 + dy + 2, -math.pi / 2 - .3, 11, 6), fill=s.gc)
        else:
            s.berries(S, x0 + side * 24, y0 - 60 * scale, 3)
            s.berries(S, x0 + side * 4, y0 - 100 * scale, 2, 3.4)
            s.berries(S, x0 + side * 36, y0 - 28 * scale, 3, 3.6)

    def eyes(s, S, mood, ey, ex, ew=13, eh=7.5):
        for side in (-1, 1):
            x = 180 + side * ex
            if mood == 'kind':
                S.line(happy_eye(x, ey, 12, 6), '#1D4398', 2.8, smooth_=True)
            else:
                pts, (ix, iy) = ae(x, ey, mood, side, ew, eh)
                S.path(smooth(pts) if mood != 'angry' else P(pts), fill='#FFFFFF', stroke='#1D4398', stroke_width=1.6,
                       stroke_linejoin='round')
                ic = '#1D4398' if mood != 'angry' else '#C8323F'
                S.el('circle', cx=ix, cy=iy, r=3, fill=ic)
                S.el('circle', cx=ix - .8, cy=iy - .8, r=.9, fill='#FFFFFF')
            b = bl(x, ey - 8.5, mood, side, 16)
            # бровь-мазок: хвост наружу, голова к переносице
            a = math.atan2(b[0][1] - b[-1][1], b[0][0] - b[-1][0])
            S.path(drop(b[-1][0], b[-1][1], a, 17, 5.5), fill='#1D4398' if mood != 'angry' else '#9E2F35')

    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        s.setup(S, A)
        s.bg(S, A)
        s.spray(S, 40, 190, 1, A)
        s.spray(S, 320, 190, -1, A)
        # рога — тонкие стебли с завитками
        stc = '#BFD3F2' if not A else '#E8A090'
        for side in (-1, 1):
            for line, w0, w1 in l_antler(1, 1.15 if A else 1.0):
                pts = line if side == -1 else mir(line)
                S.path(P(taper(pts, w0 * .7, w1 * .5)), fill=stc)
            tip = (145, 2) if side == -1 else (215, 2)
            for (x, y, a) in ((130, 14, -2.2), (122, 32, 2.8), (160, 6, -1.2)):
                xx, aa = (x, a) if side == -1 else (360 - x, math.pi - a)
                S.path(drop(xx + 6 * math.cos(aa + math.pi), y + 6 * math.sin(aa + math.pi), aa, 13, 6), fill=s.gt if not A else s.gc)
        # руки
        if A:
            for side in (-1, 1):
                sh, el, hd = l_arm(side, 1.1)
                S.path(P(taper([sh, el, hd], 22, 12)), fill='#1A2C55')
                S.path(P(taper([sh, el, hd], 22, 12)), fill='none', stroke='#E8A090', stroke_width=1.2)
                for a in (-.95, -.5, -.05, .4):
                    ang = -math.pi / 2 + side * .25 + a * .9
                    S.path(drop(hd[0], hd[1], ang, 22, 6), fill=s.gc)
        # плечи — тёмный кафтан с росписью
        coat = '#13264A' if not A else '#2A1430'
        S.path(P(L_SHOULD), fill=coat, stroke='#7FA8E8' if not A else '#E8A090', stroke_width=1.4)
        for t in range(9):
            p = lerp((96, 150), (126, 128), t / 8) if t < 5 else lerp((126, 128), (150, 121), (t - 4) / 4)
            pass
        for side in (-1, 1):
            for k in range(5):
                x = 180 + side * (50 + k * 13)
                y = 126 + k * 7.5
                a = math.atan2(7.5, side * 13)
                S.path(drop(x, y, a, 13, 6.5), fill=s.gz if k % 2 else s.gw)
            s.berries(S, 180 + side * 92, 170, 3, 4, s.gc)
        # волосы — капли наружу
        for i, (x, y, a, L, w) in enumerate(l_hair_leaves()):
            S.path(drop(x - 6 * math.cos(a), y - 6 * math.sin(a), a, L * (1.2 if A else 1.1), w * (1.0 if A else 1.1)),
                   fill=(s.gt if i % 2 else s.gz) if not A else (s.gc if i % 2 else s.gz))
        # лицо — эмаль
        S.path(smooth(L_FACE), fill=S.rad([(0, '#F2F7EE'), (.6, '#CFE3D2'), (1, '#7FAE96')], .45, .4, .62))
        S.line([(180, 74), (177, 86), (175, 96)], '#1D4398', 2.2, smooth_=True)
        S.line([(172, 97), (176, 100), (180, 99)], '#1D4398', 2, smooth_=True)
        s.eyes(S, mood, 77, 13)
        for side in (-1, 1):
            if not A:
                S.el('circle', cx=180 + side * 19, cy=92, r=4.5, fill='#F08A6E', fill_opacity=.6)
        if A:
            m = [(162, 103), (180, 99), (198, 103), (194, 116), (180, 122), (166, 116)]
            S.path(P(m), fill='#3A0E16', stroke='#9E2F35', stroke_width=1.6)
            for tx in (167, 175, 185, 193):
                S.path(P([(tx - 3, 104), (tx + 3, 104), (tx, 110)]), fill='#FFFFFF')
        # борода — висящие капли
        n = 9
        top = 118 if A else 104
        for k in range(n):
            t = (k - (n - 1) / 2) / ((n - 1) / 2)
            x = 180 + t * 22
            a = math.pi / 2 - t * (.42 if A else .3)
            L = 86 - abs(t) * 20
            S.path(drop(x, top, a, L, 20 - abs(t) * 4), fill=(s.gt if k % 2 else s.gz) if not A else (s.gc if k in (0, 8, 4) else (s.gt if k % 2 else s.gz)))
        # усы
        for side in (-1, 1):
            S.path(drop(180, 101, math.pi / 2 - side * (1.25 if not A else .9), 30, 10), fill=s.gw)
        return S

    def domovoy(s, mood):
        S = Svg()
        s.setup(S, False)
        s.bg(S, False)
        s.spray(S, 40, 190, 1, False, .85)
        s.spray(S, 320, 190, -1, False, .85)
        # жостовские розы
        for (x, y, sc) in ((68, 52, 1.0), (292, 52, 1.0)):
            for k in range(7):
                a = k * 2 * math.pi / 7
                S.path(drop(x, y, a + .4, 20 * sc, 12 * sc), fill=s.gt if k % 2 else s.gz)
            for k in range(6):
                a = k * 2 * math.pi / 6
                S.path(drop(x + 4 * sc * math.cos(a), y + 4 * sc * math.sin(a), a, 13 * sc, 11 * sc), fill=s.gc)
            S.el('circle', cx=x, cy=y, r=6 * sc, fill=s.gc)
            S.line(ell(x, y, 4.5 * sc, 4 * sc, 10, 3.6, 7.8), '#FFF4EE', 1.4 * sc, smooth_=True)
        # тело-рубаха
        S.path(P(D_BODY), fill=S.lin([(0, '#D2584C'), (1, '#8E2E34')]))
        for x in (132, 228):
            s.berries(S, x, 186, 3, 3.6, s.gw)
        for side in (-1, 1):
            S.path(P(taper([(180 + side * 52, 140), (180 + side * 54, 160), (180 + side * 34, 172)], 18, 14)),
                   fill=S.lin([(0, '#D2584C'), (1, '#8E2E34')]))
        # волосы — белые капли вверх
        for k in range(13):
            a = math.pi + k * math.pi / 12
            x, y = 180 + 22 * math.cos(a), 92 + 26 * math.sin(a)
            S.path(drop(x, y, a, 22, 13), fill=s.gw if k % 2 else s.gz)
        for side in (-1, 1):
            for k in range(3):
                S.path(drop(180 + side * 20, 90 + k * 8, math.pi / 2 - side * (1.3 - k * .2), 18, 11), fill=s.gw if k % 2 else s.gz)
        S.path(smooth(D_FACE), fill=S.rad([(0, '#FFF1E8'), (.7, '#F3D2BE'), (1, '#D9A88E')], .45, .4, .6))
        s.eyes(S, mood, 96, 11)
        for side in (-1, 1):
            S.el('circle', cx=180 + side * 15, cy=104, r=4.5, fill='#F08A6E', fill_opacity=.75)
        S.el('circle', cx=180, cy=103, r=4.6, fill=s.gc)
        # борода — белая гжель
        n = 9
        for k in range(n):
            t = (k - (n - 1) / 2) / ((n - 1) / 2)
            S.path(drop(180 + t * 18, 108, math.pi / 2 - t * .6, 64 - abs(t) * 12, 20 - abs(t) * 4), fill=s.gw if k % 2 == 0 else s.gz)
        S.path(smooth([(170, 112), (175, 117), (180, 118.5), (185, 117), (190, 112), (180, 114)]), fill='#9E2F35')
        for side in (-1, 1):
            S.path(drop(180, 108, math.pi / 2 - side * 1.25, 24, 9), fill=s.gw)
        # чайник-гжель в руках
        for side in (-1, 1):
            S.el('circle', cx=180 + side * 30, cy=170, r=6.5, fill='#F3D2BE')
        S.path(P(taper([(203, 168), (214, 160), (222, 150)], 6, 2.5)), fill='#E6ECF5')
        S.el('ellipse', cx=180, cy=172, rx=22, ry=16, fill=S.rad([(0, '#FFFFFF'), (.7, '#E6ECF5'), (1, '#9FB6DD')], .4, .35, .7))
        S.el('ellipse', cx=180, cy=157, rx=10, ry=3.5, fill='#1D4398')
        S.el('circle', cx=180, cy=152, r=3, fill='#1D4398')
        for k in range(4):
            a = k * math.pi / 2 + .3
            S.path(drop(180, 173, a, 10, 6), fill='#2A5BC0')
        return S


# ============================================================ 5. КНИЖНАЯ ИЛЛЮСТРАЦИЯ (медальон)
def circ_below(cx, cy, r, y0, n=40):
    """Сегмент круга ниже y0 (многоугольник)."""
    pts = []
    h = max(-r, min(r, y0 - cy))
    a0 = math.asin(h / r)
    for i in range(n + 1):
        a = a0 + (math.pi - 2 * a0) * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class Book:
    key = 'book'
    K = '#0A0E12'
    MX, MY, MR = 180, 100, 90

    def fr(s, S, p, c, lw=1.1, sm_=False):
        S.path(smooth(p) if sm_ else P(p), fill=c, stroke=s.K, stroke_width=lw, stroke_linejoin='round')

    def frame(s, S, A):
        acc = TURQ if not A else CORAL
        S.el('rect', width=360, height=200, fill='#0D141D')
        # угловые завитки (видны в полном кадре)
        for (x, y, sx, sy) in ((14, 14, 1, 1), (346, 14, -1, 1), (14, 186, 1, -1), (346, 186, -1, -1)):
            S.line(spiral(x + sx * 14, y + sy * 14, 2, 12, 1.2, 0, 9, sx * sy), '#2C4458', 1.4, smooth_=True)
        # боковые стебли с цветами — орнамент вне медальона
        for side in (-1, 1):
            x0 = 180 + side * 122
            stem = [(x0, 194), (x0 - side * 6, 150), (x0 + side * 4, 100), (x0 - side * 4, 50), (x0, 18)]
            S.line(stem, '#3E6A58', 1.6, smooth_=True)
            for k, (yy, a) in enumerate(((160, .4), (128, -.5), (92, .5), (60, -.4), (34, .5))):
                aa = (-math.pi / 2 + (1.0 if k % 2 else -1.0) * 1.0) if side < 0 else (-math.pi / 2 - (1.0 if k % 2 else -1.0) * 1.0)
                px = x0 + (side * 3 if k % 2 else -side * 3)
                S.path(leaf(px, yy, aa, 18, 8), fill='#1F4A3A', stroke=s.K, stroke_width=.8)
            for yy, c in ((112, acc), (44, CORAL if not A else '#FF9A86')):
                for k in range(5):
                    a = -math.pi / 2 + (k - 2) * .45
                    S.path(leaf(x0, yy, a, 12, 6), fill=c, stroke=s.K, stroke_width=.7)
                S.el('circle', cx=x0, cy=yy, r=2.4, fill=PARCH)
        # двойная рамка
        S.el('rect', x=3, y=3, width=354, height=194, fill='none', stroke='#CDBF9E', stroke_width=1, stroke_opacity=.7)
        S.el('rect', x=7, y=7, width=346, height=186, fill='none', stroke='#CDBF9E', stroke_width=.6, stroke_opacity=.45)

    def ring(s, S, A):
        acc = TURQ if not A else CORAL
        S.el('circle', cx=s.MX, cy=s.MY, r=s.MR + 4, fill='none', stroke='#1A2A36', stroke_width=8)
        S.el('circle', cx=s.MX, cy=s.MY, r=s.MR + 8, fill='none', stroke='#CDBF9E', stroke_width=1)
        S.el('circle', cx=s.MX, cy=s.MY, r=s.MR, fill='none', stroke='#CDBF9E', stroke_width=1.2)
        d = ''
        for k in range(40):
            a = k * 2 * math.pi / 40
            x, y = s.MX + (s.MR + 4) * math.cos(a), s.MY + (s.MR + 4) * math.sin(a)
            d += P([(x, y - 2), (x + 2, y), (x, y + 2), (x - 2, y)])
        S.path(d, fill=acc)

    def fir(s, S, x, yb, h, w, col, lean=0.0):
        """Ель «книжная»: ярусы опущенных лап с тонким контуром."""
        S.path(P(taper([(x, yb), (x + lean, yb - h)], 4, 1.5)), fill='#3A2A22')
        tiers = 6
        for i in range(tiers):
            t = i / tiers
            y = yb - h * .15 - h * .8 * t
            ww = w * (1 - t * .8)
            xx = x + lean * (.15 + .8 * t)
            p = [(xx, y - h * .2), (xx - ww * .2, y - h * .08), (xx - ww / 2, y + 3), (xx - ww * .3, y + 1), (xx, y + 4),
                 (xx + ww * .3, y + 1), (xx + ww / 2, y + 3), (xx + ww * .2, y - h * .08)]
            s.fr(S, p, col, .9)

    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        s.frame(S, A)
        MX, MY, MR = s.MX, s.MY, s.MR
        sky = [(0, '#0E2A36'), (.6, '#1B5A62'), (1, '#3FA8A0')] if not A else [(0, '#1A060A'), (.6, '#6A1E26'), (1, '#E07A5F')]
        S.el('circle', cx=MX, cy=MY, r=MR, fill=S.lin(sky))
        # луна/солнце
        S.el('circle', cx=MX + 50, cy=MY - 46, r=11, fill='#E9F7F2' if not A else '#FFB09A', stroke=s.K, stroke_width=.8)
        # ели внутри медальона
        fc = '#123A30' if not A else '#2A1418'
        for (x, h, w, ln) in ((112, 110, 40, -4), (248, 110, 40, 4), (132, 80, 30, -2), (228, 80, 30, 2)):
            s.fir(S, x, 168, h, w, fc if h > 90 else lt(fc, .08), ln * (3 if A else 1))
        S.path(P(circ_below(MX, MY, MR, 164)), fill='#173828' if not A else '#2A1216', stroke=s.K, stroke_width=1)
        if A:
            for (x, y, sg) in ((120, 40, 1), (240, 70, -1), (110, 120, 1)):
                S.line(spiral(x, y, 1, 10, 1.3, 0, 16, sg), '#FFB09A', 1.4, smooth_=True)
        s.ring(S, A)
        # фигура (выходит за медальон снизу и рогами сверху)
        S.g(transform='translate(180 200) scale(.92) translate(-180 -200)')
        K = s.K
        bark = '#6B4A35'
        for side in (-1, 1):
            for line, w0, w1 in l_antler(1, 1.12 if A else 1.0):
                pts = line if side == -1 else mir(line)
                s.fr(S, taper(pts, w0, w1 * .8), S.lin([(0, lt(bark, .2)), (1, dk(bark, .2))]) if False else bark, .9)
        if A:
            for side in (-1, 1):
                sh, el, hd = l_arm(side)
                s.fr(S, taper([sh, el, hd], 22, 13), '#2E4A6A')
                for a in (-.95, -.5, -.05, .4):
                    ang = -math.pi / 2 + side * .25 + a * .9
                    tip = (hd[0] + 20 * math.cos(ang), hd[1] + 20 * math.sin(ang))
                    mid = (hd[0] + 11 * math.cos(ang - side * .3), hd[1] + 11 * math.sin(ang - side * .3))
                    s.fr(S, taper([hd, mid, tip], 5, .8), bark, .8)
                s.fr(S, ell(hd[0], hd[1] + 2, 7, 7, 10), '#8A9C78', .9)
        coat = '#2E4A6A'
        s.fr(S, L_SHOULD, S.lin([(0, lt(coat, .12)), (1, dk(coat, .3))]), 1.2)
        # кайма кафтана — орнамент
        for side in (-1, 1):
            hem = [(180 + side * 20, 200), (180 + side * 60, 200), (180 + side * 52, 150), (180 + side * 34, 124), (180 + side * 22, 122)]
            s.fr(S, hem, '#8E2E34', .9)
            for k in range(4):
                p = lerp((180 + side * 40, 196), (180 + side * 34, 140), k / 3)
                S.path(P([(p[0], p[1] - 4), (p[0] + 3, p[1]), (p[0], p[1] + 4), (p[0] - 3, p[1])]), fill='#CDBF9E')
        leafc = '#2F6A48' if not A else '#6A3A28'
        for i, (x, y, a, L, w) in enumerate(l_hair_leaves()):
            S.path(leaf(x, y, a, L * (1.15 if A else 1), w * (.75 if A else .95)), fill=leafc if i % 2 else lt(leafc, .15),
                   stroke=K, stroke_width=.8)
            S.line([(x, y), (x + L * .8 * math.cos(a), y + L * .8 * math.sin(a))], K, .5, stroke_opacity=.6)
        skin = '#9CAE86' if not A else '#A8A07A'
        s.fr(S, L_FACE, S.rad([(0, lt(skin, .2)), (1, dk(skin, .2))], .45, .4, .65), 1.2, sm_=True)
        # морщины-кора
        S.lines([[(165, 58), (172, 56), (180, 58)], [(180, 58), (188, 56), (195, 58)], [(158, 90), (161, 96)], [(202, 90), (199, 96)],
                 [(170, 64), (180, 63), (190, 64)]], dk(skin, .45), .8)
        s.fr(S, L_NOSE, lt(skin, .12), .9, sm_=True)
        for side in (-1, 1):
            x = 180 + side * 13
            pts, (ix, iy) = ae(x, 77, mood, side, 11, 6.5)
            S.path(smooth(pts) if not A else P(pts), fill='#EDE6D2', stroke=K, stroke_width=1)
            S.el('circle', cx=ix, cy=iy, r=2.5, fill=TURQ if not A else DANGER, stroke=K, stroke_width=.6)
            S.el('circle', cx=ix, cy=iy, r=1, fill=K)
            b = bl(x, 69.5, mood, side, 15)
            S.path(P(taper(b, 2.4, 4)), fill='#2A4A34', stroke=K, stroke_width=.8)
        if A:
            m = [(162, 103), (180, 99), (198, 103), (194, 117), (180, 122), (166, 117)]
            s.fr(S, m, '#2A0E12', 1)
            for tx in (167, 175, 185, 193):
                S.path(P([(tx - 3, 104), (tx + 3, 104), (tx, 110)]), fill='#EDE6D2', stroke=K, stroke_width=.6)
        # борода с тонкими прядями
        bc = '#3E8A5C'
        top = 116 if A else 98
        bp = [(180, top), (163, top + 1), (151, top + 8), (146, 124), (142, 152), (137, 178), (132, 200)]
        outline = bp + mir(bp)[::-1]
        if A:
            outline = [(x + (x - 180) * .2, y) for x, y in outline]
        s.fr(S, outline, S.lin([(0, lt(bc, .1)), (1, dk(bc, .35))]), 1.2, sm_=False)
        segs = []
        for k in range(-4, 5):
            dx = k * 8.5
            segs.append(wavy((180 + dx * .55, top + 8), (180 + dx * (1.25 if A else 1.05), 198), 1.6, 3, k))
        S.lines(segs, dk(bc, .45), .8)
        S.lines([wavy((180 + k * 7 * .55 + 3, top + 14), (180 + k * 7 * (1.25 if A else 1.05) + 3, 194), 1.2, 3, k + 1) for k in range(-4, 5, 2)],
                lt(bc, .35), .7)
        for side in (-1, 1):
            m = [(180, 98), (180 + side * 10, 97), (180 + side * 22, 103), (180 + side * 30, 114 if not A else 106),
                 (180 + side * 18, 108), (180 + side * 6, 105)]
            s.fr(S, m, lt(bc, .12), .9, sm_=True)
        S.end()
        return S

    def domovoy(s, mood):
        S = Svg()
        s.frame(S, False)
        MX, MY, MR = s.MX, s.MY, s.MR
        S.el('circle', cx=MX, cy=MY, r=MR, fill='#3A2A26')
        # брёвна внутри медальона
        for k, y in enumerate(range(18, 190, 16)):
            h = math.sqrt(max(0, MR ** 2 - (y + 8 - MY) ** 2))
            if h < 8:
                continue
            S.path(smooth([(MX - h, y + 1), (MX + h, y + 1), (MX + h, y + 15), (MX - h, y + 15)]) if False else
                   P([(MX - h, y + 1), (MX + h, y + 1), (MX + h, y + 15), (MX - h, y + 15)]),
                   fill=S.lin([(0, '#6A4A38'), (.5, '#54382C'), (1, '#3A2620')]) if k == 0 else '#4E3428', stroke=s.K, stroke_width=.8)
        # окно
        s.fr(S, [(104, 50), (146, 50), (146, 96), (104, 96)], S.lin([(0, '#1B3F6E'), (1, '#2E7C8C')]), 1.4)
        S.el('circle', cx=134, cy=62, r=6, fill='#E9F7F2', stroke=s.K, stroke_width=.6)
        S.lines([[(125, 50), (125, 96)], [(104, 73), (146, 73)]], s.K, 2)
        s.fr(S, [(100, 96), (150, 96), (152, 101), (98, 101)], '#8A6A4A', .9)
        # печь с изразцами
        s.fr(S, [(214, 38), (264, 38), (264, 180), (214, 180)], '#D9CCB0', 1.2)
        for r in range(4):
            for c in range(2):
                x, y = 218 + c * 23, 44 + r * 22
                s.fr(S, [(x, y), (x + 19, y), (x + 19, y + 18), (x, y + 18)], '#EDE4CC', .7)
                S.path(leaf(x + 9.5, y + 15, -math.pi / 2, 12, 7), fill=TURQ if (r + c) % 2 else CORAL, stroke=s.K, stroke_width=.6)
        S.glow(239, 168, 30, CORAL, .7)
        S.path(P(circ_below(MX, MY, MR, 180)), fill='#2A1C18', stroke=s.K, stroke_width=1)
        s.ring(S, False)
        S.g(transform='translate(180 200) scale(.95) translate(-180 -200)')
        K = s.K
        body = S.lin([(0, '#C8554F'), (1, '#7E2A2E')])
        s.fr(S, D_BODY, body, 1.2)
        for side in (-1, 1):
            s.fr(S, taper([(180 + side * 52, 140), (180 + side * 54, 160), (180 + side * 32, 174)], 18, 14), body)
        s.fr(S, [(116, 170), (244, 170), (245, 178), (115, 178)], TURQ, .9)
        hp = sym([(180, 47), (170, 50), (162, 48), (156, 56), (148, 57), (146, 66), (138, 70), (140, 80), (133, 86),
                  (138, 96), (132, 104), (140, 112), (180, 112)])
        s.fr(S, hp, S.lin([(0, '#DDE2E5'), (1, '#9AA4AB')]), 1.1, sm_=True)
        S.lines([wavy((150 + k * 10, 56 + abs(k - 3) * 2), (148 + k * 10 + (k - 3) * 3, 78), 1.2, 2, k) for k in range(7)], '#7A848C', .7)
        s.fr(S, D_FACE, S.rad([(0, '#F3C3A0'), (1, '#C98B6A')], .45, .4, .65), 1.1, sm_=True)
        for side in (-1, 1):
            x = 180 + side * 11
            S.line(happy_eye(x, 96, 10, 5.5), K, 1.8, smooth_=True)
            S.lines([[(x + side * 6, 95), (x + side * 8, 92)], [(x + side * 6, 97), (x + side * 8.5, 97)]], K, .6)
            b = bl(x, 88, 'kind', side, 14)
            S.path(P(taper(b, 3, 5)), fill='#F2F2EE', stroke=K, stroke_width=.7)
            S.el('circle', cx=180 + side * 15, cy=104, r=4.5, fill=CORAL, fill_opacity=.55)
        s.fr(S, ell(180, 103, 5, 4.6, 14), '#D88F6E', .9)
        bp = [(180, 106), (164, 106), (150, 112), (140, 126), (136, 144), (142, 162), (156, 176), (180, 184)]
        s.fr(S, bp + mir(bp)[::-1][1:-1], S.lin([(0, '#F4F6F7'), (1, '#AEB8BF')]), 1.2, sm_=True)
        S.lines([wavy((180 + k * 6 * .5, 116), (180 + k * 6, 178 - abs(k) * 3), 1.3, 3, k) for k in range(-5, 6)], '#8E979E', .6)
        S.path(smooth([(170, 112), (175, 117), (180, 118.5), (185, 117), (190, 112), (180, 114)]), fill='#7A2E2A', stroke=K, stroke_width=.8)
        for side in (-1, 1):
            s.fr(S, [(180, 108), (180 + side * 12, 106), (180 + side * 24, 112), (180 + side * 14, 115), (180 + side * 4, 112)], '#F4F6F7', .8,
                 sm_=True)
            S.el('circle', cx=180 + side * 28, cy=174, r=6.5, fill='#E3A98A', stroke=K, stroke_width=1)
        s.fr(S, ell(180, 178, 22, 10, 16), S.lin([(0, '#C8804C'), (1, '#8A4A28')]), 1.1, sm_=True)
        S.lines([[(x - 3, 173), (x + 3, 181)] for x in (170, 180, 190)], K, 1)
        S.end()
        return S


STYLES = [Glass(), Lubok(), Silhouette(), Rospis(), Book()]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for st in STYLES:
        if only and st.key not in only:
            continue
        for cr, mood in (('leshy', 'neutral'), ('leshy', 'angry'), ('domovoy', 'kind')):
            S = getattr(st, cr)(mood)
            svg = S.render()
            n = check(f'{st.key}_{cr}_{mood}', svg)
            with open(f'{OUT}/{st.key}_{cr}_{mood}.svg', 'w') as fh:
                fh.write(svg)
            print(f'{st.key}_{cr}_{mood}.svg {n / 1024:.1f} KB')


if __name__ == '__main__':
    main()

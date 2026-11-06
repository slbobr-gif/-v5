"""Три варианта на основе стиля «Планы с сиянием»: dusk (сумерки-градиент), glass (витражный силуэт),
etch (северная гравюра / контражур). Сцены city / village / north + леший neutral, angry + домовой kind.

python3 silhouette_variants.py [variant ...] -> /home/claude/out/silhouette_styles/<variant>_<name>.svg
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import Svg, P, smooth, mir, taper, tf, ell, drop, leaf, lerp, mix, lt, dk, LEAD, TURQ, CORAL, DANGER, check
from creature_styles import (l_antler, l_hair_leaves, l_arm, L_FACE, L_SHOULD, D_BODY, ae, bl, happy_eye, scallops, pine,
                             sym)
from location_styles import forest_profile, hill, windows, WARM, VIOL

OUT = '/home/claude/out/silhouette_styles'
BLK = '#04070A'


# ============================================================ общая геометрия
def hatch_poly(pts, step, y0=0, y1=200, dx=0.0):
    """Горизонтальные штрихи внутри многоугольника (скан-линии), dx — наклон на 100 px высоты."""
    segs = []
    n = len(pts)
    y = y0 + step / 2
    while y < y1:
        xs = []
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            if xs[k + 1] - xs[k] > 2:
                segs.append([(xs[k] + 1, y), (xs[k + 1] - 1, y + dx)])
        y += step
    return segs


def leshy_shapes(A):
    sh = []
    for side in (-1, 1):
        for line, w0, w1 in l_antler(1, 1.2 if A else 1.0):
            pts = line if side == -1 else mir(line)
            sh.append(P(taper(pts, w0 + .5, w1 + .3)))
    for (x, y, a, L, w) in l_hair_leaves():
        sh.append(leaf(x, y, a, L * (1.25 if A else 1.05), w * (.7 if A else .95)))
    if A:
        for side in (-1, 1):
            s_, el, hd = l_arm(side, 1.3)
            sh.append(P(taper([s_, el, hd], 22, 10)))
            for a in (-1.0, -.55, -.1, .35):
                ang = -math.pi / 2 + side * .3 + a * .9
                mid = (hd[0] + 12 * math.cos(ang - side * .3), hd[1] + 12 * math.sin(ang - side * .3))
                tip = (hd[0] + 26 * math.cos(ang), hd[1] + 26 * math.sin(ang))
                sh.append(P(taper([hd, mid, tip], 6, .6)))
    sh.append(smooth(L_FACE))
    sh.append(P(L_SHOULD))
    bp = [(180, 96), (162, 97), (150, 104), (145, 124), (142, 152), (138, 182)]
    jag = []
    for k in range(9):
        x = 138 + k * 10.5
        jag += [(x, 182 + (k % 2) * 4), (x + 5, 196 + (k % 3) * 2)]
    out = bp + jag + mir(bp)[::-1][:-1]
    if A:
        out = [(x + (x - 180) * .22, y) for x, y in out]
    sh.append(P(out))
    return sh


def leshy_face(S, A, ec, blk=BLK, glow=True):
    for side in (-1, 1):
        x = 180 + side * 13
        pts, (ix, iy) = ae(x, 77, 'angry' if A else 'neutral', side, 14 if A else 13, 7 if A else 7.5)
        if glow:
            S.glow(x, 77, 16, ec, .55)
        S.path(smooth(pts) if not A else P(pts), fill=lt(ec, .45))
        if not A:
            S.el('circle', cx=ix, cy=iy, r=1.8, fill=blk)
        else:
            S.path(P(taper(bl(x, 69, 'angry', side, 16), 2.5, 3.5)), fill=lt(ec, .2), fill_opacity=.8)
    if A:
        m = [(164, 104), (172, 101), (180, 103), (188, 101), (196, 104), (192, 116), (180, 122), (168, 116)]
        if glow:
            S.glow(180, 110, 22, DANGER, .45)
        S.path(P(m), fill='#FF8A7A')
        for tx in (168, 176, 184, 192):
            S.path(P([(tx - 3, 102), (tx + 3, 102), (tx, 109)]), fill=blk)
        for tx in (172, 188):
            S.path(P([(tx - 3, 121), (tx + 3, 121), (tx, 114)]), fill=blk)


D_HAIR = sym([(180, 46), (171, 50), (163, 47), (157, 55), (148, 56), (146, 65), (137, 69), (139, 80), (132, 86),
              (137, 96), (131, 104), (139, 112), (180, 112)])
D_BP = [(180, 104), (164, 105), (150, 112), (140, 126), (136, 144), (140, 162)]
D_BEARD = D_BP + scallops((140, 162), (220, 162), 5, 8, out=-1)[1:-1] + mir(D_BP)[::-1][:-1]


def domovoy_shapes():
    sh = [P(D_HAIR), P(D_BEARD), P(D_BODY)]
    for side in (-1, 1):
        sh.append(P(taper([(180 + side * 52, 140), (180 + side * 54, 160), (180 + side * 30, 172)], 18, 14)))
    return sh


def domovoy_face(S, eye='#FFE2D2', glowc='#FFC2A0', blk=BLK):
    S.glow(180, 160, 46, '#FFB08A', .55)
    S.path(P([(172, 186), (172, 166), (188, 166), (188, 186)]), fill='#F4E6DA')
    S.path(drop(180, 166, -math.pi / 2, 14, 7), fill='#FFE7D6')
    for side in (-1, 1):
        S.path(smooth(ell(180 + side * 13, 180, 8, 7, 10)), fill=blk)
    for side in (-1, 1):
        x = 180 + side * 11
        S.glow(x, 95, 12, glowc, .5)
        S.line(happy_eye(x, 96, 11, 6), eye, 2.6, smooth_=True)
    S.path(smooth([(170, 110), (175, 115), (180, 116.5), (185, 115), (190, 110), (180, 112)]), fill='#FFB09A')


def meeple(S, x, y, body=BLK, rim=TURQ, glow=TURQ, sc=1.25):
    S.g(transform=f'translate({x} {y}) scale({sc}) translate({-x} {-y})')
    S.el('ellipse', cx=x, cy=y + 1, rx=9, ry=2.4, fill='#000000', fill_opacity=.35)
    S.glow(x, y - 10, 16, glow, .4)
    kw = dict(stroke=rim, stroke_width=.9, stroke_linejoin='round')
    S.path(P(taper([(x - .5, y - 12), (x - 4, y - 5), (x - 6, y)], 3, 2.4)), fill=body, **kw)
    S.path(P(taper([(x + .5, y - 12), (x + 3, y - 5), (x + 5.5, y)], 3, 2.4)), fill=body, **kw)
    S.path(P([(x - 6, y - 19), (x - 2, y - 20), (x - 1, y - 11), (x - 6, y - 11)]), fill=body, **kw)
    S.path(P(taper([(x, y - 20), (x + .5, y - 11)], 6.5, 5.5)), fill=body, **kw)
    S.el('circle', cx=x + .5, cy=y - 23, r=3, fill=body, **kw)
    S.line([(x + 6, y - 22), (x + 7.5, y + .5)], rim, 1.2)
    S.end()


CITY_SKY = [(0, 200), (0, 104), (40, 104), (40, 96), (60, 96), (60, 104), (128, 104), (128, 82), (140, 82), (140, 104),
            (198, 104), (198, 52), (204, 46), (206, 30), (208, 46), (214, 52), (214, 104), (300, 104), (300, 92), (320, 92),
            (320, 104), (360, 104), (360, 200)]


def onion(x, y, r):
    return [(x, y - r * 2.4), (x, y - r * 1.9), (x - r * .3, y - r * 1.3), (x - r, y - r * .4), (x - r * .8, y + r * .3),
            (x + r * .8, y + r * .3), (x + r, y - r * .4), (x + r * .3, y - r * 1.3), (x, y - r * 1.9)]


def roofs_row(y, seed):
    rnd = random.Random(seed)
    pts = [(0, 200), (0, y)]
    x = 0
    while x < 360:
        w = rnd.uniform(18, 34)
        h = rnd.uniform(4, 14)
        if rnd.random() < .5:
            pts += [(x, y - h), (x + w / 2, y - h - w * .3), (x + w, y - h)]
        else:
            pts += [(x, y - h), (x + w, y - h)]
        x += w
        pts.append((x, y - rnd.uniform(0, 4)))
    pts += [(360, y), (360, 200)]
    return pts


HOUSES = [(26, 66, 66, 'gable', 2, 3), (94, 64, 50, 'flat', 2, 3), (160, 50, 72, 'gable', 3, 2), (212, 70, 56, 'flat', 2, 4),
          (284, 64, 64, 'gable', 2, 3)]


def house_pts(x, yb, w, h, roof):
    top = yb - h
    if roof == 'gable':
        return [(x, yb), (x, top), (x - 3, top), (x + w / 2, top - w * .32), (x + w + 3, top), (x + w, top), (x + w, yb)]
    return [(x, yb), (x, top), (x - 2, top), (x - 2, top - 5), (x + w + 2, top - 5), (x + w + 2, top), (x + w, top), (x + w, yb)]


def izba_pts(x, yb, w):
    h = 44
    return [(x + 6, yb), (x + 6, yb - h), (x - 4, yb - h + 2), (x + w / 2, yb - h - 36), (x + w + 4, yb - h + 2),
            (x + w - 6, yb - h), (x + w - 6, yb)]


def fence_d(x0, x1, y, h):
    d = P([(x0, y - h * .6), (x1, y - h * .6), (x1, y - h * .4), (x0, y - h * .4)])
    x = x0
    while x <= x1:
        d += P([(x - 2, y), (x - 2, y - h), (x, y - h - 3), (x + 2, y - h), (x + 2, y)])
        x += 9
    return d


AURORA = [[(-10, 60), (60, 34), (130, 50), (200, 22), (270, 38), (370, 16)],
          [(-10, 82), (80, 58), (150, 72), (230, 48), (300, 60), (370, 40)]]


# ============================================================ базовый вариант
class Var:
    key = 'v'

    # --- переопределяемое
    def sky(s, S, sc, mood='neutral'):
        pass

    def plane(s, S, pts, t, sc, sm=False, rim=True):
        pass

    def light_window(s, S, x, y, w, h, t):
        pass

    def lamp(s, S, x, yb, h, t):
        pass

    def fire(s, S, x, y):
        S.glow(x, y - 6, 44, CORAL, .6)
        for dx, h, c in ((-5, 14, CORAL), (0, 24, '#FFC2A0'), (5, 12, CORAL)):
            S.path(P([(x + dx - 5, y), (x + dx, y - h), (x + dx + 5, y)]), fill=c)

    def water(s, S, y0, y1, refl):
        pass

    def celestial(s, S, sc, mood='neutral'):
        pass

    def foreground(s, S, sc):
        pass

    def creature_bg(s, S, mood):
        pass

    def creature_rim(s, mood):
        return (TURQ, 2.4, .6) if mood != 'angry' else ('#FF9A86', 2.4, .7)

    def finish(s, S):
        pass

    def tcol(s, t, sc):
        return BLK

    # --- сцены
    def city(s):
        S = Svg()
        s.sky(S, 'city')
        s.celestial(S, 'city')
        s.plane(S, CITY_SKY, .12, 'city')
        for (x, y, r) in ((134, 76, 8), (160, 92, 10), (310, 88, 6)):
            s.plane(S, onion(x, y, r), .12, 'city', rim=False)
        s.plane(S, roofs_row(124, 3), .34, 'city')
        rnd = random.Random(4)
        for k in range(10):
            x = 14 + k * 34 + rnd.uniform(-4, 4)
            s.light_window(S, x, 112 + rnd.uniform(0, 6), 3, 3, .34)
        for i, (x, w, h, roof, rows, cols) in enumerate(HOUSES):
            s.plane(S, house_pts(x, 150, w, h, roof), .6 + .04 * (i % 2), 'city')
            for (wx, wy, ww, wh, lit) in windows(x, 150, w, h, rows, cols, i + 3):
                if lit:
                    s.light_window(S, wx, wy, ww, wh, .6)
        s.plane(S, [(0, 200), (0, 150), (360, 150), (360, 200)], .85, 'city', rim=False)
        s.street(S)
        s.lamp(S, 72, 186, 74, .85)
        s.lamp(S, 262, 186, 74, .85)
        meeple(S, 150, 180, *s.meeple_cols())
        # перила набережной — передний план
        d = P([(0, 188), (360, 188), (360, 191), (0, 191)])
        for x in range(4, 360, 16):
            d += P([(x, 200), (x, 189), (x + 3, 189), (x + 3, 200)])
        S.path(d, fill=BLK)
        s.foreground(S, 'city')
        s.finish(S)
        return S

    def street(s, S):
        pass

    def village(s):
        S = Svg()
        s.sky(S, 'village')
        s.celestial(S, 'village')
        s.plane(S, forest_profile(-10, 370, 110, 8, 18, 12, 5), .1, 'village')
        s.plane(S, forest_profile(-10, 370, 120, 10, 24, 14, 6), .26, 'village')
        s.plane(S, hill(-10, 370, 134, 10, 5, .4), .45, 'village', sm=False)
        s.plane(S, pine(300, 160, 70, 30, 5), .62, 'village')
        s.plane(S, izba_pts(52, 152, 104), .7, 'village')
        s.plane(S, [(126, 108), (126, 92), (136, 92), (136, 116)], .7, 'village', rim=False)
        s.light_window(S, 88, 120, 18, 16, .7)
        s.smoke(S, [(131, 88), (127, 72), (135, 58), (129, 42)])
        s.plane(S, hill(-10, 370, 150, 4, 4, .2), .82, 'village')
        s.road(S, [(140, 200), (166, 168), (176, 154), (184, 146), (190, 146), (196, 154), (206, 168), (236, 200)])
        S.path(fence_d(34, 150, 166, 14), fill=s.tcol(.9, 'village'))
        S.path(fence_d(226, 300, 168, 14), fill=s.tcol(.9, 'village'))
        s.fire(S, 262, 184)
        s.plane(S, pine(22, 200, 140, 58, 6), 1, 'village')
        s.plane(S, pine(338, 200, 120, 50, 6), 1, 'village')
        meeple(S, 198, 188, *s.meeple_cols())
        s.foreground(S, 'village')
        s.finish(S)
        return S

    def smoke(s, S, pts):
        S.line(pts, '#C9D3E0', 4, smooth_=True, stroke_opacity=.25)

    def road(s, S, pts):
        S.path(P(pts), fill=S.lin([(0, mix(s.tcol(.5, 'village'), CORAL, .35)), (1, s.tcol(.95, 'village'))]))

    def north(s):
        S = Svg()
        s.sky(S, 'north')
        s.celestial(S, 'north')
        s.plane(S, hill(-10, 370, 104, 12, 4, .3, 130), .08, 'north')
        f1 = forest_profile(-10, 130, 116, 10, 28, 12, 9) + [(130, 200)]
        f2 = forest_profile(226, 370, 116, 10, 28, 12, 11)
        s.plane(S, f1, .26, 'north')
        s.plane(S, f2, .26, 'north')
        refl = []
        for f in (f1, f2):
            top = [(x, y) for x, y in f if y < 116]
            refl.append([(top[0][0], 116)] + [(x, 232 - y) for x, y in top] + [(top[-1][0], 116)])
        s.water(S, 116, 172, refl)
        s.plane(S, [(-10, 200), (-10, 168), (60, 172), (130, 178), (200, 176), (260, 170), (370, 166), (370, 200)], .75, 'north')
        for (x, y, r) in ((92, 176, 9), (238, 172, 7), (268, 178, 11)):
            s.plane(S, [(x - r, y + 3), (x - r * .7, y - r * .5), (x, y - r * .8), (x + r * .8, y - r * .3), (x + r, y + 3)], .85, 'north',
                    rim=False)
        s.plane(S, pine(62, 186, 120, 50, 6), .9, 'north')
        s.plane(S, pine(300, 184, 104, 44, 6), .9, 'north')
        s.plane(S, pine(28, 200, 176, 74, 7), 1, 'north')
        s.plane(S, pine(334, 200, 166, 70, 7), 1, 'north')
        meeple(S, 162, 190, *s.meeple_cols())
        s.foreground(S, 'north')
        s.finish(S)
        return S

    def meeple_cols(s):
        return (BLK, TURQ, TURQ)

    # --- существа
    def leshy(s, mood):
        S = Svg()
        A = mood == 'angry'
        s.creature_bg(S, mood)
        rim, rw, rop = s.creature_rim(mood)
        sh = leshy_shapes(A)
        s.figure(S, sh, rim, rw, rop)
        leshy_face(S, A, DANGER if A else TURQ)
        s.creature_fx(S, mood)
        s.finish(S)
        return S

    def figure(s, S, sh, rim, rw, rop):
        for d in sh:
            S.path(d, fill='none', stroke=rim, stroke_width=rw, stroke_opacity=rop, stroke_linejoin='round')
        for d in sh:
            S.path(d, fill=BLK)

    def creature_fx(s, S, mood):
        pass

    def domovoy(s, mood='kind'):
        S = Svg()
        s.domovoy_bg(S)
        s.figure(S, domovoy_shapes(), '#FFD2B4', 2.6, .7)
        S.path(P(D_BEARD), fill='none', stroke='#FFD2B4', stroke_width=1.1, stroke_opacity=.35)
        domovoy_face(S)
        s.finish(S)
        return S

    def stove(s, S):
        S.glow(310, 172, 100, CORAL, .5, .35)
        S.path(P([(266, 200), (266, 70), (276, 60), (330, 60), (330, 30), (346, 30), (346, 60), (360, 60), (360, 200)]), fill=BLK)
        S.path(P([(284, 200), (284, 164), (290, 152), (308, 146), (326, 152), (332, 164), (332, 200)]),
               fill=S.lin([(0, '#FFC9A8'), (.5, '#F08A6E'), (1, '#B2453F')]))
        for x, h in ((298, 22), (308, 32), (318, 20)):
            S.path(P([(x - 6, 200), (x, 200 - h), (x + 6, 200)]), fill='#FFE2D2', fill_opacity=.8)

    def cat_sill(s, S):
        S.path(P([(100, 150), (260, 150), (260, 158), (100, 158)]), fill=BLK)
        S.path(P([(0, 186), (360, 186), (360, 200), (0, 200)]), fill=BLK)
        cat = [(120, 150), (118, 138), (122, 126), (126, 120), (124, 112), (128, 115), (133, 114), (136, 111), (137, 120),
               (140, 132), (144, 150)]
        S.path(smooth(cat), fill=BLK)
        S.line([(144, 148), (152, 146), (156, 138)], BLK, 3, smooth_=True)


# ============================================================ А. СУМЕРКИ-ГРАДИЕНТ
class Dusk(Var):
    key = 'dusk'
    SKY = {'city': ['#141038', '#3A2266', '#8A3A6A', '#E07A5F', '#F2A272'],
           'village': ['#0C1430', '#24305E', '#5A3A6E', '#B8586A', '#E88A6E'],
           'north': ['#030816', '#0A1A3A', '#10305A', '#16566A', '#2A8A86']}
    HOR = {'city': '#B85A6A', 'village': '#9A4A66', 'north': '#2A6A7A'}

    def tcol(s, t, sc):
        return mix(mix(s.HOR[sc], s.SKY[sc][1], .35), BLK, min(1, t ** .75 * 1.05))

    def sky(s, S, sc, mood='neutral'):
        c = s.SKY[sc]
        S.el('rect', width=360, height=200, fill=S.lin([(0, c[0]), (.3, c[1]), (.5, c[2]), (.62, c[3]), (.72, c[4])]))
        rnd = random.Random(7)
        d = ''
        for k in range(26):
            x, y = rnd.uniform(4, 356), rnd.uniform(4, 60 if sc != 'north' else 100) ** 1.0
            r = rnd.choice((.7, .9, 1.2))
            d += P([(x, y - r * 2), (x + r * .5, y), (x, y + r * 2), (x - r * .5, y)]) + P([(x - r * 2, y), (x, y - r * .5), (x + r * 2, y), (x, y + r * .5)])
        S.path(d, fill='#F2FFFD', fill_opacity=.75)

    def celestial(s, S, sc, mood='neutral'):
        if sc == 'city':
            S.glow(250, 104, 120, '#FFB08A', .55, .35)
            S.el('circle', cx=250, cy=100, r=18, fill=S.lin([(0, '#FFE2CC'), (1, '#F08A6E')]))
            S.el('circle', cx=74, cy=34, r=7, fill='#F2FFFD')
        elif sc == 'village':
            S.glow(290, 40, 34, '#F2FFFD', .45)
            S.el('circle', cx=290, cy=40, r=9, fill='#F2FFFD')
            S.glow(180, 128, 160, '#E88A6E', .3)
        else:
            for i, b in enumerate(AURORA):
                c = TURQ if i == 0 else VIOL
                top = [(x, y - 34) for x, y in b]
                S.path(smooth(b + top[::-1]), fill=S.lin([(0, c, 0), (.65, c, .5), (1, lt(c, .35), .9)]))
                # лучи сияния
                S.lines([[(x, y - 30 + k), (x + 2, y + 24)] for k, (x, y) in enumerate(b[1:-1])], lt(c, .3), 3, stroke_opacity=.25)

    def mist(s, S, y, sc, op=.16):
        S.path(smooth([(-20, y), (80, y - 5), (170, y + 3), (260, y - 4), (380, y + 2), (380, y + 14), (-20, y + 14)]),
               fill=s.HOR[sc], fill_opacity=op)

    def plane(s, S, pts, t, sc, sm=False, rim=True):
        S.path(smooth(pts) if sm else P(pts), fill=s.tcol(t, sc))
        if rim and t < .5:
            top = min(y for _, y in pts)
            s.mist(S, top + 8, sc, .18 - t * .2)

    def light_window(s, S, x, y, w, h, t):
        if w > 6:
            # луч света из окна вниз-вперёд
            S.path(P([(x, y + h), (x + w, y + h), (x + w * 2.2, y + h + 34), (x - w * 1.2, y + h + 34)]),
                   fill=S.lin([(0, WARM, .22), (1, WARM, 0)]))
            S.glow(x + w / 2, y + h / 2, w * 2, WARM, .4)
        S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill='#FFD8BE')

    def lamp(s, S, x, yb, h, t):
        S.path(P([(x - 4, yb - h + 4), (x + 4, yb - h + 4), (x + 30, yb), (x - 30, yb)]), fill=S.lin([(0, WARM, .4), (1, WARM, .05)]))
        S.glow(x, yb - h, 40, WARM, .55)
        S.path(P([(x - 1.6, yb), (x - 1.6, yb - h), (x + 1.6, yb - h), (x + 1.6, yb)]), fill=BLK)
        S.path(P([(x - 5, yb - h - 2), (x + 5, yb - h - 2), (x + 3, yb - h + 6), (x - 3, yb - h + 6)]), fill='#FFE2CC')

    def street(s, S):
        # мокрая мостовая: отражения окон и фонарей
        for x in (72, 262):
            S.el('ellipse', cx=x, cy=172, rx=4, ry=14, fill=WARM, fill_opacity=.35)
        for x in (60, 120, 186, 240, 300):
            S.el('ellipse', cx=x, cy=160, rx=2.5, ry=6, fill=WARM, fill_opacity=.22)

    def water(s, S, y0, y1, refl):
        S.path(P([(-10, y0), (370, y0), (370, y1), (-10, y1)]), fill=S.lin([(0, '#1E6A74'), (.5, '#0C2E44'), (1, '#04101A')]))
        for i, b in enumerate(AURORA):
            c = TURQ if i == 0 else VIOL
            r = [(x, y0 + (y0 - y) * .5 + 6) for x, y in b]
            S.path(smooth(r + [(x, y + 7) for x, y in r[::-1]]), fill=c, fill_opacity=.3)
        for f in refl:
            S.path(P(f), fill=s.tcol(.45, 'north'), fill_opacity=.6)
        S.lines([[(40 + k * 9, y), (320 - k * 11, y)] for k, y in enumerate(range(int(y0) + 4, int(y1), 5))], '#BFF5EE', .7,
                stroke_opacity=.25)

    def finish(s, S):
        S.el('rect', width=360, height=200, fill=S.rad([(0, '#000000', 0), (.75, '#000000', 0), (1, '#02040A', .45)], .5, .5, .75))

    # существа: закат за спиной, планы холмов
    def creature_bg(s, S, mood):
        A = mood == 'angry'
        c = ['#140A20', '#3A1430', '#8A2A3A', '#E0555F', '#FF9A86'] if A else ['#060E24', '#142A50', '#1E4E6A', '#2A8A86', '#7FE0D2']
        S.el('rect', width=360, height=200, fill=S.lin([(0, c[0]), (.35, c[1]), (.55, c[2]), (.7, c[3]), (.8, c[4])]))
        S.glow(180, 132, 170, c[4], .45)
        mc = '#FFC2A8' if A else '#DFFFF8'
        S.glow(180, 74, 90, mc, .35)
        S.el('circle', cx=180, cy=74, r=48, fill=S.rad([(0, mc), (.75, mix(mc, c[3], .35)), (1, c[3])], .5, .5, .5), fill_opacity=.9)
        rnd = random.Random(2)
        S.path(''.join(P(ell(rnd.uniform(4, 356), rnd.uniform(4, 70), .9, .9, 4)) for _ in range(22)), fill='#F2FFFD', fill_opacity=.7)
        hor = c[3]
        for k, (y, amp, ph) in enumerate(((128, 14, .2), (140, 16, 1.3), (152, 12, 2.1), (166, 10, .7))):
            t = .15 + k * .22
            S.path(P(hill(-10, 370, y, amp, 6, ph)), fill=mix(mix(hor, c[1], .4), BLK, t ** .7))
            S.path(smooth([(-20, y + 4), (100, y), (200, y + 6), (380, y + 2), (380, y + 14), (-20, y + 14)]), fill=hor, fill_opacity=.12)
        for x, h in ((24, 110), (58, 84), (304, 90), (338, 116)):
            S.path(P(pine(x, 200, h, h * .42, 6)), fill=mix(c[1], BLK, .7))

    def creature_fx(s, S, mood):
        if mood != 'angry':
            for (x, y) in ((70, 120), (96, 92), (284, 104), (258, 132), (300, 70)):
                S.glow(x, y, 7, TURQ, .7)
                S.el('circle', cx=x, cy=y, r=1.3, fill='#DFFFFB')

    def domovoy_bg(s, S):
        S.el('rect', width=360, height=200, fill='#0A0F17')
        # окно: за ним сумеречные планы
        S.path(P([(112, 16), (248, 16), (248, 150), (112, 150)]),
               fill=S.lin([(0, '#142A50'), (.5, '#5A3A6E'), (.8, '#E88A6E')]))
        for k, (y, amp) in enumerate(((112, 8), (124, 10), (138, 6))):
            S.path(P(hill(112, 248, y, amp, 4, k * .9, 150)), fill=mix('#7A4A6A', BLK, .3 + k * .25))
        S.el('circle', cx=222, cy=38, r=8, fill='#F2FFFD')
        S.glow(180, 84, 150, '#E88A6E', .25)
        for x in (156, 204):
            S.path(P([(x - 2.5, 16), (x + 2.5, 16), (x + 2.5, 150), (x - 2.5, 150)]), fill=BLK)
        S.path(P([(112, 80), (248, 80), (248, 85), (112, 85)]), fill=BLK)
        S.path(P([(106, 10), (254, 10), (254, 16), (106, 16)]) + P([(106, 10), (112, 10), (112, 156), (106, 156)])
               + P([(248, 10), (254, 10), (254, 156), (248, 156)]), fill=BLK)
        s.stove(S)
        s.cat_sill(S)


# ============================================================ Б. ВИТРАЖНЫЙ СИЛУЭТ
class GlassSil(Var):
    key = 'glass'
    LW = 1.3
    SKY = {'city': ['#1A1A4A', '#2E2A6A', '#4A3A7A', '#7A4A7A'], 'village': ['#0E1A36', '#1E3456', '#3A3A62', '#7A4A5E'],
           'north': ['#06102A', '#0C2244', '#0F3A52', '#165A62']}

    def tcol(s, t, sc):
        if t >= .55:
            return BLK
        return mix(s.SKY[sc][2], BLK, .55 + t * .7)

    def gl(s, S, c):
        if not hasattr(s, 'cache') or s.cache[0] is not S:
            s.cache = (S, {})
        d = s.cache[1]
        if c not in d:
            d[c] = S.lin([(0, lt(c, .18)), (.6, c), (1, dk(c, .18))], 0, 0, .25, 1)
        return d[c]

    def sky(s, S, sc, mood='neutral'):
        S.el('rect', width=360, height=200, fill=LEAD)
        cols = s.SKY[sc]
        rnd = random.Random(len(sc) * 3)
        ys = [0, 30, 62, 96, 140]
        for i in range(4):
            y0, y1 = ys[i], ys[i + 1]
            xs = [-30]
            while xs[-1] < 370:
                xs.append(xs[-1] + rnd.uniform(60, 110))
            sk = [rnd.uniform(-16, 16) for _ in xs]
            for k in range(len(xs) - 1):
                c = mix(cols[i], cols[min(i + 1, 3)], rnd.uniform(0, .6))
                S.path(P([(xs[k] + sk[k], y0), (xs[k + 1] + sk[k + 1], y0), (xs[k + 1] - sk[k + 1] * .4, y1), (xs[k] - sk[k] * .4, y1)]),
                       fill=s.gl(S, c), stroke=LEAD, stroke_width=s.LW)
        for (x, y) in ((30, 20), (110, 14), (150, 40), (250, 18), (300, 46), (330, 12), (200, 10)):
            S.path(P([(x, y - 3.5), (x + 1, y - 1), (x + 3.5, y), (x + 1, y + 1), (x, y + 3.5), (x - 1, y + 1), (x - 3.5, y), (x - 1, y - 1)]),
                   fill='#DFF7F2', stroke=LEAD, stroke_width=.6)

    def glass_moon(s, S, x, y, r, col='#DFF7F2'):
        S.glow(x, y, r * 3.4, col, .45)
        for k in range(6):
            a0, a1 = k * math.pi / 3, (k + 1) * math.pi / 3
            S.path(P([(x, y), (x + r * math.cos(a0), y + r * math.sin(a0)), (x + r * math.cos((a0 + a1) / 2) * 1.02,
                                                                             y + r * math.sin((a0 + a1) / 2) * 1.02),
                      (x + r * math.cos(a1), y + r * math.sin(a1))]), fill=lt(col, .1 * (k % 2)) if k % 2 else col,
                   stroke=LEAD, stroke_width=s.LW)

    def celestial(s, S, sc, mood='neutral'):
        if sc == 'north':
            for i, b in enumerate(AURORA):
                c = TURQ if i == 0 else VIOL
                for k in range(len(b) - 1):
                    a, bb = b[k], b[k + 1]
                    S.path(P([a, bb, (bb[0], bb[1] - 24), (a[0], a[1] - 24)]), fill=S.lin([(0, lt(c, .35), .95), (1, dk(c, .3), .8)], 0, 1, 0, 0),
                           stroke=LEAD, stroke_width=s.LW)
        else:
            s.glass_moon(S, 72 if sc == 'city' else 290, 38, 11)

    def plane(s, S, pts, t, sc, sm=False, rim=True):
        d = smooth(pts) if sm else P(pts)
        if t < .55:
            S.path(d, fill=s.gl(S, s.tcol(t, sc)), stroke=LEAD, stroke_width=s.LW, stroke_linejoin='round')
        else:
            S.path(d, fill=BLK)

    def light_window(s, S, x, y, w, h, t):
        if w > 6:
            S.glow(x + w / 2, y + h / 2, w * 2, WARM, .4)
            cols = [WARM, '#FFC9A8', CORAL, '#7FE0D2']
            c = cols[int(x + y) % 4]
            S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill=S.lin([(0, lt(c, .3)), (1, c)]), stroke=LEAD, stroke_width=1)
            S.lines([[(x + w / 2, y), (x + w / 2, y + h)], [(x, y + h / 2), (x + w, y + h / 2)]], LEAD, 1)
        else:
            S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill=WARM)

    def lamp(s, S, x, yb, h, t):
        S.glow(x, yb - h, 44, WARM, .55)
        S.el('ellipse', cx=x, cy=yb, rx=30, ry=5, fill=WARM, fill_opacity=.2)
        S.path(P([(x - 1.6, yb), (x - 1.6, yb - h), (x + 1.6, yb - h), (x + 1.6, yb)]), fill=BLK)
        S.path(P([(x - 6, yb - h - 3), (x + 6, yb - h - 3), (x + 4, yb - h + 7), (x - 4, yb - h + 7)]), fill=S.lin([(0, '#FFE6D2'), (1, WARM)]),
               stroke=LEAD, stroke_width=1.2)
        S.line([(x, yb - h - 3), (x, yb - h + 7)], LEAD, .9)

    def fire(s, S, x, y):
        S.glow(x, y - 6, 44, CORAL, .6)
        for dx, h, c in ((-6, 15, CORAL), (0, 25, '#FFC2A0'), (6, 13, '#F08A6E')):
            S.path(P([(x + dx - 6, y), (x + dx, y - h), (x + dx + 6, y)]), fill=c, stroke=LEAD, stroke_width=1)

    def road(s, S, pts):
        S.path(P(pts), fill=s.gl(S, '#3A2A36'), stroke=LEAD, stroke_width=s.LW)

    def water(s, S, y0, y1, refl):
        rows = [(y0, y0 + 16), (y0 + 16, y0 + 34), (y0 + 34, y1)]
        for i, (a, b) in enumerate(rows):
            xs = [-10, 100, 190, 270, 370]
            for k in range(4):
                c = mix('#0C2A3E', TURQ if (i + k) % 2 == 0 else VIOL, .38 - i * .1)
                S.path(P([(xs[k] + i * 6, a), (xs[k + 1] + i * 6, a), (xs[k + 1] + i * 6 + 6, b), (xs[k] + i * 6 + 6, b)]), fill=s.gl(S, c),
                       stroke=LEAD, stroke_width=s.LW)
        for f in refl:
            S.path(P(f), fill=BLK, fill_opacity=.45)

    def smoke(s, S, pts):
        S.line(pts, '#C9D3E0', 4, smooth_=True, stroke_opacity=.3)

    def finish(s, S):
        S.el('rect', x=1.5, y=1.5, width=357, height=197, fill='none', stroke=LEAD, stroke_width=5, rx=3)

    def creature_rim(s, mood):
        return (LEAD, 3.4, 1) if mood != 'angry' else (LEAD, 3.4, 1)

    def creature_bg(s, S, mood):
        A = mood == 'angry'
        S.el('rect', width=360, height=200, fill=LEAD)
        cols = ['#5A1A24', '#8E2E34', '#3E1219', '#B2453F'] if A else ['#0F3B4C', '#155A6B', '#0C2C3C', '#1E6A78']
        n = 16
        for i in range(n):
            a0, a1 = .1 + 2 * math.pi * i / n, .1 + 2 * math.pi * (i + 1) / n
            S.path(P([(180, 70), (180 + 300 * math.cos(a0), 70 + 300 * math.sin(a0)), (180 + 300 * math.cos(a1), 70 + 300 * math.sin(a1))]),
                   fill=s.gl(S, cols[i % 4]), stroke=LEAD, stroke_width=s.LW)
        s.glass_moon(S, 180, 70, 56, '#FF9A86' if A else '#7FE0D2')
        for x, h in ((20, 120), (52, 96), (84, 70), (276, 74), (308, 100), (340, 124)):
            S.path(P(pine(x, 176, h, h * .42, 5)), fill=s.gl(S, dk(cols[2], .3)), stroke=LEAD, stroke_width=s.LW)
        for x, h in ((6, 150), (40, 120), (322, 126), (356, 156)):
            S.path(P(pine(x, 200, h, h * .42, 5)), fill=BLK)

    def creature_fx(s, S, mood):
        pass

    def domovoy_bg(s, S):
        S.el('rect', width=360, height=200, fill='#0A0F17')
        cols = ['#7FE0D2', '#5FC8C0', '#9FEDE4', '#4AB0AA']
        k = 0
        for (x0, x1) in ((112, 156), (156, 204), (204, 248)):
            for (y0, y1) in ((16, 48), (48, 80), (80, 116), (116, 150)):
                S.path(P([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), fill=s.gl(S, cols[k % 4]), stroke=LEAD, stroke_width=s.LW)
                k += 1
        s.glass_moon(S, 222, 38, 9, '#F2FFFD')
        S.glow(180, 84, 140, TURQ, .3)
        for x in (156, 204):
            S.path(P([(x - 2.5, 16), (x + 2.5, 16), (x + 2.5, 150), (x - 2.5, 150)]), fill=BLK)
        S.path(P([(112, 80), (248, 80), (248, 85), (112, 85)]), fill=BLK)
        s.stove(S)
        s.cat_sill(S)

    def domovoy(s, mood='kind'):
        S = Svg()
        s.domovoy_bg(S)
        s.figure(S, domovoy_shapes(), LEAD, 3.4, 1)
        S.path(P(D_BEARD), fill='none', stroke='#FFD2B4', stroke_width=1.1, stroke_opacity=.3)
        domovoy_face(S)
        s.finish(S)
        return S


# ============================================================ В. СЕВЕРНАЯ ГРАВЮРА / КОНТРАЖУР
class Etch(Var):
    key = 'etch'
    BACK = {'city': CORAL, 'village': CORAL, 'north': TURQ}
    LINE = {'city': TURQ, 'village': TURQ, 'north': '#7FE0D2'}

    def tcol(s, t, sc):
        return BLK if t >= .5 else '#0A1018'

    def sky(s, S, sc, mood='neutral'):
        b = s.BACK[sc]
        top = '#06101A' if sc == 'north' else '#0A1222'
        S.el('rect', width=360, height=200, fill=S.lin([(0, top), (.5, mix(top, b, .25)), (.62, mix(top, b, .7)), (.66, lt(b, .25))]))
        # штрихи неба: тонкие горизонтали, гуще к зениту
        segs = []
        y = 4
        while y < 92:
            segs.append([(8, y), (352, y)])
            y += 3 + y * .06
        S.lines(segs, s.LINE[sc], .5, stroke_opacity=.22)

    def celestial(s, S, sc, mood='neutral'):
        b = s.BACK[sc]
        if sc == 'north':
            for i, bb in enumerate(AURORA):
                c = TURQ if i == 0 else VIOL
                S.lines([[(x, y), (x + 3, y - 34)] for k in range(len(bb) - 1) for t in range(8)
                         for (x, y) in [lerp(bb[k], bb[k + 1], t / 8)]], lt(c, .2), 1.2, stroke_opacity=.75)
                S.line(bb, lt(c, .4), 1.6, smooth_=True, stroke_opacity=.9)
            cx, cy = 180, 116
        else:
            cx, cy = (250, 104) if sc == 'city' else (180, 134)
        # контровой диск у горизонта и лучи
        S.glow(cx, cy, 130, b, .55, .35)
        S.el('circle', cx=cx, cy=cy, r=22, fill=lt(b, .45))
        S.lines([[(cx + 28 * math.cos(a), cy + 28 * math.sin(a)), (cx + 190 * math.cos(a), cy + 190 * math.sin(a))]
                 for a in [math.pi + k * math.pi / 18 for k in range(1, 18)]], lt(b, .3), .8, stroke_opacity=.35)

    def plane(s, S, pts, t, sc, sm=False, rim=True):
        if t < .5:
            S.path(P(pts), fill='#0A1018', fill_opacity=.55 + t)
            step = 4.5 - t * 4
            S.lines(hatch_poly(pts, max(1.8, step)), s.LINE[sc] if t < .3 else s.BACK[sc], .7, stroke_opacity=.75 - t)
        else:
            S.path(P(pts), fill=BLK)
            if rim:
                top = [q for q in pts if q[1] < 199]
                S.line(top, lt(s.BACK[sc], .2), 1.1, stroke_opacity=.85)

    def light_window(s, S, x, y, w, h, t):
        if w > 6:
            S.glow(x + w / 2, y + h / 2, w * 1.6, WARM, .35)
        S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill='#FFD8BE')

    def lamp(s, S, x, yb, h, t):
        S.glow(x, yb - h, 36, WARM, .5)
        S.lines([[(x, yb - h), (x + 36 * math.cos(a), yb - h + 36 * math.sin(a))] for a in [k * math.pi / 8 for k in range(16)]], WARM, .6,
                stroke_opacity=.5)
        S.path(P([(x - 1.6, yb), (x - 1.6, yb - h), (x + 1.6, yb - h), (x + 1.6, yb)]), fill=BLK)
        S.path(P([(x - 5, yb - h - 2), (x + 5, yb - h - 2), (x + 3, yb - h + 6), (x - 3, yb - h + 6)]), fill='#FFE2CC')

    def road(s, S, pts):
        S.path(P(pts), fill=BLK)
        S.lines(hatch_poly(pts, 3.2), CORAL, .7, stroke_opacity=.55)

    def water(s, S, y0, y1, refl):
        S.path(P([(-10, y0), (370, y0), (370, y1), (-10, y1)]), fill='#050C14')
        segs = []
        for k, y in enumerate(range(int(y0) + 2, int(y1), 3)):
            w = 150 - k * 6
            segs.append([(180 - w, y), (180 + w, y)])
        S.lines(segs, TURQ, .8, stroke_opacity=.6)
        S.lines([[(180 - 26 + k, y0 + 2 + k * 3), (180 + 26 - k, y0 + 2 + k * 3)] for k in range(14)], lt(TURQ, .5), 1.4, stroke_opacity=.7)
        for f in refl:
            S.path(P(f), fill=BLK, fill_opacity=.8)

    def smoke(s, S, pts):
        S.line(pts, CORAL, 1, smooth_=True, stroke_opacity=.6)
        S.line([(x + 3, y) for x, y in pts], CORAL, .6, smooth_=True, stroke_opacity=.4)

    def foreground(s, S, sc):
        # рамка переднего плана: еловая лапа сверху-слева, трава снизу
        br = [(-6, 6), (40, 14), (90, 18), (130, 16)]
        S.path(P(taper(br, 5, 1.5)), fill=BLK)
        d = ''
        for i in range(1, 16):
            p = lerp(br[0], br[-1], i / 16)
            p = (p[0], p[1] + 2 + 6 * math.sin(i / 16 * math.pi))
            L = 16 - i * .7
            for sg in (-1, 1):
                d += P([p, (p[0] + 4, p[1] + sg * 1.2), (p[0] + 6 + L * .3, p[1] + sg * L)], True)
        S.path(d, fill=BLK)
        rnd = random.Random(sc)
        d = ''
        for k in range(46):
            x = rnd.uniform(-4, 364)
            if 120 < x < 250 and rnd.random() < .7:
                continue
            h = rnd.uniform(8, 22)
            lean = rnd.uniform(-6, 6)
            d += P([(x - 1.6, 201), (x + lean, 200 - h), (x + 1.6, 201)])
        S.path(d, fill=BLK)

    def meeple_cols(s):
        return (BLK, lt(CORAL, .2), CORAL)

    def creature_rim(s, mood):
        return (lt(TURQ, .3), 2.2, .9) if mood != 'angry' else (lt(CORAL, .3), 2.2, .95)

    def creature_bg(s, S, mood):
        A = mood == 'angry'
        b = CORAL if A else TURQ
        S.el('rect', width=360, height=200, fill=S.lin([(0, '#06101A'), (.4, mix('#06101A', b, .25)), (.7, mix('#06101A', b, .6))]))
        S.glow(180, 76, 170, b, .6, .35)
        S.el('circle', cx=180, cy=76, r=58, fill=lt(b, .45))
        S.lines([[(180 + 64 * math.cos(a), 76 + 64 * math.sin(a)), (180 + 260 * math.cos(a), 76 + 260 * math.sin(a))]
                 for a in [k * math.pi / 20 for k in range(40)]], lt(b, .3), .8, stroke_opacity=.35)
        for k, (y, amp, ph) in enumerate(((140, 14, .2), (156, 12, 1.4))):
            pts = hill(-10, 370, y, amp, 6, ph)
            S.path(P(pts), fill='#0A1018', fill_opacity=.6 + k * .2)
            S.lines(hatch_poly(pts, 3.4 - k), lt(b, .1) if k == 0 else b, .7, stroke_opacity=.6 - k * .15)
        for x, h in ((22, 140), (60, 104), (300, 108), (340, 146)):
            S.path(P(pine(x, 200, h, h * .42, 6)), fill=BLK)
        s.foreground(S, 'creature')

    def creature_fx(s, S, mood):
        pass

    def domovoy_bg(s, S):
        S.el('rect', width=360, height=200, fill='#0A0F17')
        # окно: северная ночь штрихами
        win = [(112, 16), (248, 16), (248, 150), (112, 150)]
        S.path(P(win), fill='#0C2230')
        S.lines(hatch_poly(win, 3.2), TURQ, .7, stroke_opacity=.5)
        S.el('circle', cx=222, cy=38, r=9, fill='#DFFFFB')
        for x in (156, 204):
            S.path(P([(x - 2.5, 16), (x + 2.5, 16), (x + 2.5, 150), (x - 2.5, 150)]), fill=BLK)
        S.path(P([(112, 80), (248, 80), (248, 85), (112, 85)]), fill=BLK)
        # контровой жар печи: лучи по стене
        S.glow(306, 176, 150, CORAL, .55, .4)
        S.lines([[(306 + 30 * math.cos(a), 176 + 30 * math.sin(a)), (306 + 240 * math.cos(a), 176 + 240 * math.sin(a))]
                 for a in [math.pi + k * math.pi / 16 for k in range(1, 12)]], lt(CORAL, .3), .8, stroke_opacity=.35)
        s.stove(S)
        s.cat_sill(S)

    def domovoy(s, mood='kind'):
        S = Svg()
        s.domovoy_bg(S)
        s.figure(S, domovoy_shapes(), lt(CORAL, .3), 2.4, .95)
        S.path(P(D_BEARD), fill='none', stroke=lt(CORAL, .3), stroke_width=1, stroke_opacity=.45)
        domovoy_face(S)
        s.finish(S)
        return S


VARS = [Dusk(), GlassSil(), Etch()]
ITEMS = [('city', lambda v: v.city()), ('village', lambda v: v.village()), ('north', lambda v: v.north()),
         ('leshy_neutral', lambda v: v.leshy('neutral')), ('leshy_angry', lambda v: v.leshy('angry')),
         ('domovoy_kind', lambda v: v.domovoy('kind'))]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for v in VARS:
        if only and v.key not in only:
            continue
        for name, fn in ITEMS:
            svg = fn(v).render()
            n = check(f'{v.key}_{name}', svg)
            with open(f'{OUT}/{v.key}_{name}.svg', 'w') as fh:
                fh.write(svg)
            print(f'{v.key}_{name} {n / 1024:.1f}', end='  ')
        print()


if __name__ == '__main__':
    main()

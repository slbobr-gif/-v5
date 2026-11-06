"""Пять вариантов стиля ЛОКАЦИЙ «Путника» (шапки событий 360×200), согласованные со стилями существ.

Сцены одинаковые по сюжету во всех стилях: city (Тверь вечером), village (изба, забор, дорога, костёр),
north (карельский лес и озеро под сиянием). В каждой — мипл Сергея на дороге.

python3 location_styles.py [style ...]  ->  /home/claude/out/location_styles/<style>_<scene>.svg
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import (Svg, P, smooth, mir, taper, tf, ell, drop, leaf, spiral, lerp, mix, lt, dk,
                    LEAD, TURQ, CORAL, PARCH, check)
from creature_styles import scallops, wavy

OUT = '/home/claude/out/location_styles'
WARM = '#F2A272'      # свет окон: персик, не жёлтый
VIOL = '#7B6CE0'

# ============================================================ сюжеты (общая геометрия)
PAL = {
    'city': dict(sky0='#0A1030', sky1='#2A2B62', hor='#3E7E8A', far='#1C2A50', mid='#24375A', wall='#2E4466',
                 wall2='#3A3E66', roof='#18233C', ground='#151D2C', road='#1C2638', near='#0C121C'),
    'village': dict(sky0='#0A1424', sky1='#24486A', hor='#B8665A', far='#12303E', mid='#16402F', wall='#6A4A38',
                    wall2='#5A3E30', roof='#33262A', ground='#1A3428', road='#4A3A30', near='#0E1E18'),
    'north': dict(sky0='#040A18', sky1='#0E2440', hor='#165A5E', far='#163050', mid='#0E2636', wall='#3A2A26',
                  wall2='#3A2A26', roof='#222', ground='#142A26', road='#2A3A3A', near='#08141A', water='#0C2A3E'),
}


def forest_profile(x0, x1, yb, hmin, hmax, step, seed):
    """Зубчатый верх ельника: многоугольник от x0 до x1 над линией yb."""
    rnd = random.Random(seed)
    pts = [(x0, yb + 40)]
    x = x0
    while x < x1:
        h = rnd.uniform(hmin, hmax)
        w = step * rnd.uniform(.7, 1.2)
        pts += [(x, yb - h * .35), (x + w / 2, yb - h), (x + w, yb - h * .35)]
        x += w * .8
    pts.append((x1, yb + 40))
    return pts


def hill(x0, x1, y, amp, n=6, ph=0.0, bottom=200):
    pts = [(x0 + (x1 - x0) * i / n, y - amp * math.sin(math.pi * i / n + ph) ** 2) for i in range(n + 1)]
    return [(x0, bottom)] + pts + [(x1, bottom)]


def windows(x, yb, w, h, rows, cols, seed, lit=.6):
    rnd = random.Random(seed)
    out = []
    ww, wh = w / (cols * 2 + 1), min(10, h / (rows * 2 + 1.4))
    for r in range(rows):
        for c in range(cols):
            wx = x + ww * (1 + c * 2)
            wy = yb - h + wh * (1.2 + r * 2)
            out.append((wx, wy, ww, wh, rnd.random() < lit))
    return out


def scene_city(st):
    S = Svg()
    p = PAL['city']
    st.begin(S, 'city')
    st.sky(S, p)
    st.stars(S, [(30, 20), (110, 14), (150, 34), (250, 18), (300, 40), (330, 12), (200, 10)])
    st.moon(S, 72, 38, 11)
    # дальний силуэт: кремлёвская стена, колокольня, купола
    sk = [(0, 200), (0, 104), (40, 104), (40, 96), (60, 96), (60, 104), (128, 104), (128, 82), (140, 82), (140, 104),
          (198, 104), (198, 52), (204, 46), (206, 30), (208, 46), (214, 52), (214, 104), (300, 104), (300, 92), (320, 92),
          (320, 104), (360, 104), (360, 200)]
    st.band(S, sk, 0, 'skyline', p)
    st.dome(S, 134, 76, 8, 0, p)
    st.dome(S, 160, 92, 10, 0, p)
    st.dome(S, 160, 92, 10, 0, p, only_cross=True)
    st.dome(S, 310, 88, 6, 0, p)
    # дома улицы
    houses = [(26, 66, 66, 'gable', 2, 3), (94, 64, 50, 'flat', 2, 3), (160, 50, 72, 'gable', 3, 2), (212, 70, 56, 'flat', 2, 4),
              (284, 64, 64, 'gable', 2, 3)]
    for i, (x, w, h, roof, rows, cols) in enumerate(houses):
        st.building(S, x, 150, w, h, roof, windows(x, 150, w, h, rows, cols, i + 3), 1, p, i)
    st.band(S, [(0, 200), (0, 150), (360, 150), (360, 200)], 2, 'road', p)
    st.band(S, [(0, 158), (360, 158), (360, 161), (0, 161)], 2, 'kerb', p)
    st.lamp(S, 262, 186, 74, p)
    st.lamp(S, 72, 186, 74, p)
    st.meeple(S, 150, 186)
    return st.finish(S, 'city')


def scene_village(st):
    S = Svg()
    p = PAL['village']
    st.begin(S, 'village')
    st.sky(S, p)
    st.stars(S, [(40, 18), (120, 12), (200, 24), (240, 10), (330, 30), (160, 40)])
    st.moon(S, 290, 36, 10)
    st.band(S, forest_profile(-10, 370, 118, 10, 26, 14, 5), 0, 'forest', p)
    st.band(S, hill(-10, 370, 132, 10, 5, .4), 1, 'hill', p)
    st.road(S, [(140, 200), (166, 168), (176, 146), (184, 132), (190, 132), (196, 146), (206, 168), (236, 200)], p)
    st.house(S, 52, 152, 104, p)
    st.smoke(S, [(132, 72), (128, 58), (136, 44), (130, 30)], p)
    st.pine(S, 22, 180, 120, 2, p)
    st.pine(S, 326, 182, 110, 2, p)
    st.pine(S, 300, 160, 70, 1, p)
    st.fence(S, 34, 150, 164, 14, p)
    st.fence(S, 226, 300, 166, 14, p)
    st.fire(S, 262, 182, p)
    st.meeple(S, 196, 186)
    return st.finish(S, 'village')


def scene_north(st):
    S = Svg()
    p = PAL['north']
    st.begin(S, 'north')
    st.sky(S, p)
    st.stars(S, [(20, 14), (60, 70), (100, 10), (150, 64), (220, 12), (270, 70), (320, 18), (346, 56), (180, 30)])
    bands = [[(-10, 60), (60, 34), (130, 50), (200, 22), (270, 38), (370, 16)],
             [(-10, 82), (80, 58), (150, 72), (230, 48), (300, 60), (370, 40)]]
    st.aurora(S, bands, p)
    st.band(S, hill(-10, 370, 106, 12, 4, .3, 130), 0, 'hill', p)
    st.band(S, forest_profile(-10, 120, 118, 12, 30, 12, 9) + [(120, 200)], 1, 'forest', p)
    st.band(S, forest_profile(236, 370, 118, 12, 30, 12, 11), 1, 'forest', p)
    st.water(S, 118, 172, bands, p)
    st.band(S, [(-10, 200), (-10, 168), (60, 172), (130, 178), (200, 176), (260, 170), (370, 166), (370, 200)], 2, 'shore', p)
    for (x, y, r) in ((92, 176, 9), (238, 172, 7), (268, 178, 11)):
        st.rock(S, x, y, r, p)
    st.pine(S, 30, 196, 170, 3, p)
    st.pine(S, 62, 186, 120, 2, p)
    st.pine(S, 332, 196, 160, 3, p)
    st.pine(S, 300, 184, 104, 2, p)
    st.meeple(S, 160, 190)
    return st.finish(S, 'north')


SCENES = [('city', scene_city), ('village', scene_village), ('north', scene_north)]


# ============================================================ базовый рисовальщик
class Base:
    key = 'base'
    stroke = None
    lw = 0

    def begin(s, S, sc):
        s.sc = sc

    def fill(s, S, pts, col, sm=False, lw=None, **a):
        d = smooth(pts) if sm else P(pts)
        if s.stroke:
            S.path(d, fill=col, stroke=s.stroke, stroke_width=lw or s.lw, stroke_linejoin='round', **a)
        else:
            S.path(d, fill=col, **a)

    def depthc(s, p, depth, kind):
        return [p['far'], p['mid'], p['ground'], p['near']][depth]

    def sky(s, S, p):
        S.el('rect', width=360, height=200, fill=S.lin([(0, p['sky0']), (.7, p['sky1']), (1, p['hor'])]))

    def stars(s, S, pts):
        for x, y in pts:
            S.el('circle', cx=x, cy=y, r=1.1, fill=PARCH, fill_opacity=.8)

    def moon(s, S, x, y, r):
        S.glow(x, y, r * 3.2, '#DFF7F2', .35)
        S.el('circle', cx=x, cy=y, r=r, fill='#EAF7F3')

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            top = [(x, y - 26) for x, y in b]
            S.path(smooth(b + top[::-1]), fill=S.lin([(0, c, 0), (.6, c, .35), (1, c, .7)]))

    def band(s, S, pts, depth, kind, p):
        s.fill(S, pts, s.depthc(p, depth, kind))

    def dome(s, S, x, y, r, depth, p, only_cross=False):
        if only_cross:
            return
        pts = [(x, y - r * 1.9), (x - r * .3, y - r * 1.3), (x - r, y - r * .4), (x - r * .8, y + r * .3), (x + r * .8, y + r * .3),
               (x + r, y - r * .4), (x + r * .3, y - r * 1.3)]
        s.fill(S, pts, s.depthc(p, depth, 'dome'), sm=False)
        S.path(P([(x, y - r * 1.9), (x, y - r * 2.6)], False), stroke=s.depthc(p, depth, 'dome'), stroke_width=1.2)

    def roof_pts(s, x, yb, w, h, roof):
        top = yb - h
        if roof == 'gable':
            return [(x - 3, top), (x + w / 2, top - w * .32), (x + w + 3, top)]
        return [(x - 2, top), (x - 2, top - 5), (x + w + 2, top - 5), (x + w + 2, top)]

    def building(s, S, x, yb, w, h, roof, wins, depth, p, i):
        s.fill(S, [(x, yb), (x, yb - h), (x + w, yb - h), (x + w, yb)], p['wall'] if i % 2 else p['wall2'])
        s.fill(S, s.roof_pts(x, yb, w, h, roof), p['roof'])
        for (wx, wy, ww, wh, lit) in wins:
            s.window(S, wx, wy, ww, wh, lit, p)

    def window(s, S, x, y, w, h, lit, p):
        if lit:
            S.glow(x + w / 2, y + h / 2, w * 1.6, WARM, .35)
        s.fill(S, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], WARM if lit else dk(p['wall'], .4), lw=1)

    def house(s, S, x, yb, w, p):
        """Изба: сруб, двускатная крыша, окно с наличником, труба."""
        h = 44
        s.fill(S, [(x + 6, yb), (x + 6, yb - h), (x + w - 6, yb - h), (x + w - 6, yb)], p['wall'])
        s.fill(S, [(x - 4, yb - h + 2), (x + w / 2, yb - h - 36), (x + w + 4, yb - h + 2)], p['roof'])
        s.fill(S, [(x + 74, yb - h - 18), (x + 74, yb - h - 34), (x + 84, yb - h - 34), (x + 84, yb - h - 10)], dk(p['wall'], .2))
        s.window(S, x + 36, yb - 32, 18, 16, True, p)
        s.fill(S, [(x + w / 2 - 7, yb - h - 18), (x + w / 2 + 7, yb - h - 18), (x + w / 2 + 7, yb - h - 8), (x + w / 2 - 7, yb - h - 8)],
               WARM, lw=1)

    def smoke(s, S, pts, p):
        S.line(pts, '#9FB0C0', 4, smooth_=True, stroke_opacity=.3)

    def road(s, S, pts, p):
        s.fill(S, pts, p['road'])

    def fence(s, S, x0, x1, y, h, p):
        c = dk(p['wall'], .1)
        s.fill(S, [(x0, y - h * .6), (x1, y - h * .6), (x1, y - h * .4), (x0, y - h * .4)], c, lw=1)
        x = x0
        while x <= x1:
            s.fill(S, [(x - 2, y), (x - 2, y - h), (x, y - h - 3), (x + 2, y - h), (x + 2, y)], c, lw=1)
            x += 9

    def pine(s, S, x, yb, h, depth, p):
        from creature_styles import pine as pine_pts
        s.fill(S, pine_pts(x, yb, h, h * .42, 5), s.depthc(p, depth, 'tree'))

    def fire(s, S, x, y, p):
        S.glow(x, y - 6, 40, CORAL, .55)
        for dx, h, c in ((-5, 14, CORAL), (0, 22, '#F7B08A'), (5, 12, CORAL)):
            s.fill(S, [(x + dx - 5, y), (x + dx, y - h), (x + dx + 5, y)], c, lw=1)
        s.fill(S, [(x - 10, y + 2), (x + 10, y - 2), (x + 10, y + 1), (x - 10, y + 5)], '#4A3028', lw=1)

    def lamp(s, S, x, yb, h, p):
        S.glow(x, yb - h, 40, WARM, .5)
        S.el('ellipse', cx=x, cy=yb, rx=26, ry=5, fill=WARM, fill_opacity=.18)
        s.fill(S, [(x - 1.6, yb), (x - 1.6, yb - h), (x + 1.6, yb - h), (x + 1.6, yb)], '#0B1018', lw=1)
        s.fill(S, [(x - 5, yb - h - 2), (x + 5, yb - h - 2), (x + 3, yb - h + 6), (x - 3, yb - h + 6)], WARM, lw=1)

    def water(s, S, y0, y1, bands, p):
        s.fill(S, [(-10, y0), (370, y0), (370, y1), (-10, y1)], p['water'])
        for k, y in enumerate(range(int(y0) + 6, int(y1), 7)):
            S.line([(40 + k * 7, y), (320 - k * 9, y)], TURQ if k % 2 == 0 else VIOL, 1.4, stroke_opacity=.35 - k * .03)

    def rock(s, S, x, y, r, p):
        s.fill(S, [(x - r, y + 3), (x - r * .7, y - r * .5), (x, y - r * .8), (x + r * .8, y - r * .3), (x + r, y + 3)], '#2A3A44')

    def meeple(s, S, x, y, col=TURQ, ink=LEAD, lw=1.0):
        """Сергей-мипл: голова, тело в шаге, рюкзак, посох. ~22 px."""
        S.g(transform=f'translate({x} {y}) scale(1.25) translate({-x} {-y})')
        S.el('ellipse', cx=x, cy=y + 1, rx=9, ry=2.4, fill='#000000', fill_opacity=.35)
        S.glow(x, y - 8, 15, col, .35)
        S.path(P(taper([(x - .5, y - 12), (x - 4, y - 5), (x - 6, y)], 3, 2.4)), fill=dk(col, .25), stroke=ink, stroke_width=lw * .8)
        S.path(P(taper([(x + .5, y - 12), (x + 3, y - 5), (x + 5.5, y)], 3, 2.4)), fill=col, stroke=ink, stroke_width=lw * .8)
        S.path(P([(x - 6, y - 19), (x - 2, y - 20), (x - 1, y - 11), (x - 6, y - 11)]), fill=dk(col, .45), stroke=ink, stroke_width=lw * .8)
        S.path(P(taper([(x, y - 20), (x + .5, y - 11)], 6.5, 5.5)), fill=col, stroke=ink, stroke_width=lw)
        S.el('circle', cx=x + .5, cy=y - 23, r=3, fill=col, stroke=ink, stroke_width=lw)
        S.line([(x + 6, y - 22), (x + 7.5, y + .5)], ink, 1.3)
        S.end()

    def finish(s, S, sc):
        return S


# ============================================================ 1. ЧИСТЫЙ ВИТРАЖ
class Glass(Base):
    key = 'glass'
    stroke = LEAD
    lw = 2.2

    def begin(s, S, sc):
        s.sc = sc
        s.cache = {}

    def g(s, S, c):
        if c not in s.cache:
            s.cache[c] = S.lin([(0, lt(c, .16)), (.6, c), (1, dk(c, .2))], 0, 0, .25, 1)
        return s.cache[c]

    def fill(s, S, pts, col, sm=False, lw=None, **a):
        if col.startswith('#') and len(col) == 7 and col not in (WARM,):
            col = s.g(S, col)
        Base.fill(s, S, pts, col, sm, lw, **a)

    def depthc(s, p, depth, kind):
        return [p['far'], p['mid'], p['ground'], p['near']][depth] if kind not in ('road', 'kerb') else (
            p['road'] if kind == 'road' else lt(p['road'], .15))

    def sky(s, S, p):
        S.el('rect', width=360, height=200, fill=LEAD)
        # крупные стёкла неба: 3 пояса, разрезанные редкими косыми швами
        ys = [0, 34, 70, 120]
        cols = [p['sky0'], mix(p['sky0'], p['sky1'], .5), p['sky1'], mix(p['sky1'], p['hor'], .6)]
        rnd = random.Random(len(s.sc))
        for i in range(3):
            y0, y1 = ys[i], ys[i + 1]
            xs = [-30]
            while xs[-1] < 370:
                xs.append(xs[-1] + rnd.uniform(70, 120))
            sk = [rnd.uniform(-14, 14) for _ in xs]
            for k in range(len(xs) - 1):
                c = mix(cols[i], cols[i + 1], rnd.uniform(.1, .7))
                S.path(P([(xs[k] + sk[k], y0), (xs[k + 1] + sk[k + 1], y0), (xs[k + 1] - sk[k + 1] * .5, y1), (xs[k] - sk[k] * .5, y1)]),
                       fill=s.g(S, c), stroke=LEAD, stroke_width=s.lw)

    def stars(s, S, pts):
        for x, y in pts:
            S.path(P([(x, y - 3.5), (x + 1, y - 1), (x + 3.5, y), (x + 1, y + 1), (x, y + 3.5), (x - 1, y + 1), (x - 3.5, y), (x - 1, y - 1)]),
                   fill='#DFF7F2', stroke=LEAD, stroke_width=.8)

    def moon(s, S, x, y, r):
        S.glow(x, y, r * 3.4, '#BFF5EE', .45)
        S.el('circle', cx=x, cy=y, r=r, fill=S.rad([(0, '#FFFFFF'), (1, '#BFE9E2')], .4, .4, .6), stroke=LEAD, stroke_width=2)

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            for k in range(len(b) - 1):
                a, bb = b[k], b[k + 1]
                q = [a, bb, (bb[0], bb[1] - 24), (a[0], a[1] - 24)]
                S.path(P(q), fill=S.lin([(0, lt(c, .3), .9), (1, dk(c, .3), .75)], 0, 1, 0, 0), stroke=LEAD, stroke_width=s.lw)

    def window(s, S, x, y, w, h, lit, p):
        if lit:
            S.glow(x + w / 2, y + h / 2, w * 1.8, WARM, .4)
        Base.fill(s, S, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], S.lin([(0, '#FFD6B8'), (1, CORAL)]) if lit else dk(p['wall'], .45),
                  lw=1.6)

    def water(s, S, y0, y1, bands, p):
        rows = [(y0, y0 + 14), (y0 + 14, y0 + 30), (y0 + 30, y1)]
        for i, (a, b) in enumerate(rows):
            for k, (x0, x1) in enumerate(((-10, 110), (110, 230), (230, 370))):
                c = mix(p['water'], TURQ if (i + k) % 2 == 0 else VIOL, .35 - i * .1)
                sh = [0, 8, -4, 4][i], [0, 8, -4, 4][i + 1]
                Base.fill(s, S, [(x0 + sh[0], a), (x1 + sh[0], a), (x1 + sh[1], b), (x0 + sh[1], b)], s.g(S, c))

    def fence(s, S, x0, x1, y, h, p):
        Base.fence(s, S, x0, x1, y, h, p)

    def finish(s, S, sc):
        S.el('rect', x=1.5, y=1.5, width=357, height=197, fill='none', stroke=LEAD, stroke_width=5, rx=3)
        S.el('rect', width=360, height=200, fill=S.rad([(0, '#000000', 0), (.7, '#000000', 0), (1, '#04070C', .5)], .5, .5, .72))
        return S


# ============================================================ 2. ЛУБОК
class Lubok(Base):
    key = 'lubok'
    stroke = '#0B0F14'
    lw = 1.8

    def depthc(s, p, depth, kind):
        if kind == 'road':
            return '#3A3046'
        if kind == 'kerb':
            return PARCH
        return {'city': ['#26305A', '#2E4466', '#1E2A40', '#141C2B'], 'village': ['#1F4A36', '#2E6A48', '#1F4A36', '#16301F'],
                'north': ['#24386A', '#1F4A36', '#2A4A3A', '#16301F']}[s.sc][depth]

    def sky(s, S, p):
        S.el('rect', width=360, height=200, fill={'city': '#1A1E3A', 'village': '#141C2B', 'north': '#0F1426'}[s.sc])
        # нижняя часть неба — тёплая полоса, как подкраска на гравюре
        S.path(P([(0, 70), (360, 70), (360, 130), (0, 130)]), fill={'city': '#2A2A55', 'village': '#3A2630', 'north': '#14283A'}[s.sc])

    def stars(s, S, pts):
        for i, (x, y) in enumerate(pts):
            for k in range(4):
                S.path(leaf(x, y, k * math.pi / 2 + .4, 6, 3), fill=TURQ if i % 2 else CORAL, fill_opacity=.7)

    def moon(s, S, x, y, r):
        S.el('circle', cx=x, cy=y, r=r + 5, fill='none', stroke=PARCH, stroke_width=1.2, stroke_dasharray=None, stroke_opacity=.5)
        S.path(P(ell(x, y, r, r, 18)), fill=PARCH, stroke=s.stroke, stroke_width=1.8)
        S.el('circle', cx=x - 3, cy=y - 1, r=1.6, fill=s.stroke)
        S.el('circle', cx=x + 3, cy=y - 1, r=1.6, fill=s.stroke)
        S.line([(x - 3, y + 4), (x, y + 5.5), (x + 3, y + 4)], s.stroke, 1.2)
        S.el('circle', cx=x - 5, cy=y + 3, r=1.8, fill=CORAL, fill_opacity=.8)

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            top = [(x, y - 18) for x, y in b]
            s.fill(S, b + top[::-1], c, sm=False)
            S.lines([[(x0 + t * (x1 - x0), y0 + t * (y1 - y0) - 2), (x0 + t * (x1 - x0) + 2, y0 + t * (y1 - y0) - 15)]
                     for (x0, y0), (x1, y1) in zip(b, b[1:]) for t in (.2, .45, .7)], dk(c, .4), 1.4)

    def band(s, S, pts, depth, kind, p):
        s.fill(S, pts, s.depthc(p, depth, kind))
        if kind in ('road', 'shore', 'hill') and depth >= 1:
            ys = min(y for _, y in pts) + 8
            segs = [[(x, y), (x + 4, y + 2.5)] for y in range(int(ys), 200, 9) for x in range(6 + (y % 2) * 5, 356, 13)]
            S.lines(segs, dk(s.depthc(p, depth, kind), .45), 1.1)

    def pine(s, S, x, yb, h, depth, p):
        s.fill(S, taper([(x, yb), (x, yb - h * .5)], 6, 3), '#5A3A2A')
        crown = s.depthc(p, min(depth + 1, 3) if s.sc == 'north' else 1, 'tree')
        tiers = 4
        for i in range(tiers):
            t = i / tiers
            y = yb - h * .22 - h * .2 * i
            w = h * .5 * (1 - t * .7)
            pts = scallops((x + w / 2, y), (x - w / 2, y), 3, 4, out=1) + [(x, y - h * .3)]
            s.fill(S, pts, crown if i % 2 else lt(crown, .1))
        S.el('circle', cx=x, cy=yb - h * .95, r=2.2, fill=CORAL)

    def window(s, S, x, y, w, h, lit, p):
        s.fill(S, [(x - 2, y - 2), (x + w + 2, y - 2), (x + w + 2, y + h + 2), (x - 2, y + h + 2)], PARCH, lw=1.2)
        Base.fill(s, S, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], WARM if lit else '#1A2638', lw=1)

    def building(s, S, x, yb, w, h, roof, wins, depth, p, i):
        Base.building(s, S, x, yb, w, h, roof, wins, depth, p, i)
        # орнамент-подзор под крышей
        S.lines([[(x + k, yb - h + 3), (x + k + 3, yb - h + 6), (x + k + 6, yb - h + 3)] for k in range(2, int(w) - 6, 6)], PARCH, 1)

    def house(s, S, x, yb, w, p):
        Base.house(s, S, x, yb, w, p)
        # брёвна-штрихи и резной фронтон
        S.lines([[(x + 8, y), (x + w - 8, y)] for y in range(yb - 40, yb, 7)], dk(p['wall'], .45), 1.1)
        S.lines([[(x + w / 2 - 20 + k * 8, yb - 50), (x + w / 2 - 16 + k * 8, yb - 46)] for k in range(6)], PARCH, 1.2)
        s.fill(S, [(x + 32, yb - 36), (x + 58, yb - 36), (x + 54, yb - 40), (x + 45, yb - 44), (x + 36, yb - 40)], PARCH, lw=1.2)

    def fire(s, S, x, y, p):
        Base.fire(s, S, x, y, p)
        S.line(spiral(x - 16, y - 26, 1, 6, 1.2, 0, 10, 1), CORAL, 1.6, smooth_=True)
        S.line(spiral(x + 16, y - 30, 1, 6, 1.2, 0, 10, -1), CORAL, 1.6, smooth_=True)

    def smoke(s, S, pts, p):
        for k, (x, y) in enumerate(pts[1:]):
            S.line(spiral(x, y, 1, 5 + k, 1.1, 0, 10, 1 if k % 2 else -1), '#9FB0C0', 1.6, smooth_=True, stroke_opacity=.7)

    def water(s, S, y0, y1, bands, p):
        s.fill(S, [(-10, y0), (370, y0), (370, y1), (-10, y1)], '#1F3A6A')
        segs = []
        for k, y in enumerate(range(int(y0) + 6, int(y1) - 2, 8)):
            segs += [wavy((10 + (k % 2) * 20 + j * 60, y), (40 + (k % 2) * 20 + j * 60, y), 1.5, 1) for j in range(6)]
        S.lines(segs, TURQ, 1.3, stroke_opacity=.75)

    def finish(s, S, sc):
        y, h = 0, 12
        S.el('rect', x=0, y=y, width=360, height=h, fill='#1A2638')
        S.lines([[(0, h), (360, h)]], s.stroke, 2)
        S.lines([[(i, y + h / 2), (i + 9, y + 2), (i + 18, y + h / 2), (i + 9, y + h - 2), (i, y + h / 2)] for i in range(0, 361, 18)], PARCH, 1,
                stroke_opacity=.55)
        for k, c in enumerate((CORAL, TURQ)):
            S.path(''.join(P(ell(i + 9, y + h / 2, 2, 2, 6)) for i in range(k * 18, 361, 36)), fill=c)
        S.el('rect', x=1, y=1, width=358, height=198, fill='none', stroke=s.stroke, stroke_width=3)
        return S


# ============================================================ 3. ПЛАНЫ С СИЯНИЕМ (силуэт + воздушная перспектива)
class Planes(Base):
    key = 'silhouette'
    BLK = '#04070A'

    def glowc(s):
        return {'city': '#9C7BE0', 'village': CORAL, 'north': TURQ}[s.sc]

    def depthc(s, p, depth, kind):
        if kind == 'kerb':
            return '#0A0F16'
        g = s.glowc()
        base = {'city': '#2A2A5A', 'village': '#3A3048', 'north': '#16405A'}[s.sc]
        return [mix(base, g, .25), dk(base, .35), dk(base, .7), s.BLK][depth] if kind != 'road' else dk(base, .75)

    def sky(s, S, p):
        g = s.glowc()
        top = {'city': '#0A0C22', 'village': '#0B1220', 'north': '#03070F'}[s.sc]
        mid = {'city': '#2E2660', 'village': '#3A2840', 'north': '#0C2A3A'}[s.sc]
        S.el('rect', width=360, height=200, fill=S.lin([(0, top), (.6, mid), (1, mix(mid, g, .5))]))
        S.glow(180, 118, 200, g, .35, .35)

    def moon(s, S, x, y, r):
        S.glow(x, y, r * 4, '#E8FFFB', .4)
        S.el('circle', cx=x, cy=y, r=r, fill='#F2FFFD')

    def mist(s, S, y, op=.18):
        S.path(smooth([(-20, y), (80, y - 5), (170, y + 3), (260, y - 4), (380, y + 2), (380, y + 18), (-20, y + 18)]), fill=s.glowc(), fill_opacity=op)

    def band(s, S, pts, depth, kind, p):
        Base.band(s, S, pts, depth, kind, p)
        if depth == 0:
            s.mist(S, max(y for _, y in pts if y < 199) - 12 if any(y < 199 for _, y in pts) else 120, .14)

    def building(s, S, x, yb, w, h, roof, wins, depth, p, i):
        c = dk(s.depthc(p, 1, 'b'), .2 * (i % 2))
        s.fill(S, [(x, yb), (x, yb - h), (x + w, yb - h), (x + w, yb)], c)
        s.fill(S, s.roof_pts(x, yb, w, h, roof), c)
        for (wx, wy, ww, wh, lit) in wins:
            if lit:
                s.window(S, wx, wy, ww, wh, lit, p)

    def window(s, S, x, y, w, h, lit, p):
        S.glow(x + w / 2, y + h / 2, w * 2, WARM, .35)
        S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill='#FFD2B4')

    def house(s, S, x, yb, w, p):
        c = s.BLK
        h = 44
        S.path(P([(x + 6, yb), (x + 6, yb - h), (x - 4, yb - h + 2), (x + w / 2, yb - h - 36), (x + w + 4, yb - h + 2),
                  (x + w - 6, yb - h), (x + w - 6, yb)]), fill=c)
        S.path(P([(x + 74, yb - h - 18), (x + 74, yb - h - 34), (x + 84, yb - h - 34), (x + 84, yb - h - 10)]), fill=c)
        s.window(S, x + 36, yb - 32, 18, 16, True, p)
        S.path(P([(x + 44, yb - 32), (x + 46, yb - 32), (x + 46, yb - 16), (x + 44, yb - 16)]), fill=c)
        S.path(P([(x + 36, yb - 25), (x + 54, yb - 25), (x + 54, yb - 23), (x + 36, yb - 23)]), fill=c)

    def fence(s, S, x0, x1, y, h, p):
        d = P([(x0, y - h * .6), (x1, y - h * .6), (x1, y - h * .4), (x0, y - h * .4)])
        x = x0
        while x <= x1:
            d += P([(x - 2, y), (x - 2, y - h), (x, y - h - 3), (x + 2, y - h), (x + 2, y)])
            x += 9
        S.path(d, fill=s.BLK)

    def pine(s, S, x, yb, h, depth, p):
        from creature_styles import pine as pine_pts
        S.path(P(pine_pts(x, yb, h, h * .42, 6)), fill=s.depthc(p, depth, 'tree'))

    def road(s, S, pts, p):
        S.path(P(pts), fill=S.lin([(0, mix('#3A3048', CORAL, .35)), (1, '#120E16')]))

    def water(s, S, y0, y1, bands, p):
        S.path(P([(-10, y0), (370, y0), (370, y1), (-10, y1)]), fill=S.lin([(0, '#1E6A70'), (1, '#04121A')]))
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            refl = [(x, y0 + (y0 - y) * .45 + 4) for x, y in b]
            S.path(smooth(refl + [(x, y + 8) for x, y in refl[::-1]]), fill=c, fill_opacity=.28)
        S.lines([[(60 + k * 11, y), (300 - k * 13, y)] for k, y in enumerate(range(int(y0) + 5, int(y1), 6))], '#BFF5EE', .8, stroke_opacity=.3)

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            top = [(x, y - 34) for x, y in b]
            S.path(smooth(b + top[::-1]), fill=S.lin([(0, c, 0), (.65, c, .45), (1, lt(c, .3), .85)]))

    def rock(s, S, x, y, r, p):
        S.path(P([(x - r, y + 3), (x - r * .7, y - r * .5), (x, y - r * .8), (x + r * .8, y - r * .3), (x + r, y + 3)]), fill=s.BLK)

    def lamp(s, S, x, yb, h, p):
        S.glow(x, yb - h, 52, WARM, .55)
        S.el('ellipse', cx=x, cy=yb, rx=34, ry=6, fill=WARM, fill_opacity=.22)
        S.path(P([(x - 1.6, yb), (x - 1.6, yb - h), (x + 1.6, yb - h), (x + 1.6, yb)]), fill=s.BLK)
        S.path(P([(x - 5, yb - h - 2), (x + 5, yb - h - 2), (x + 3, yb - h + 6), (x - 3, yb - h + 6)]), fill='#FFE2CC')

    def meeple(s, S, x, y, col=TURQ, ink=None, lw=1.0):
        Base.meeple(s, S, x, y, s.BLK, lt(TURQ, .2), 1.1)

    def finish(s, S, sc):
        s.mist(S, 182, .1)
        return S


# ============================================================ 4. РОСПИСЬ
class Rospis(Base):
    key = 'rospis'

    def begin(s, S, sc):
        s.sc = sc
        s.gz = S.rad([(0, '#F4F8FF'), (.45, '#7FA8E8'), (1, '#1D4398')], .3, .3, .85)
        s.gt = S.rad([(0, '#E8FFFC'), (.45, '#5FE0D5'), (1, '#127A78')], .3, .3, .85)
        s.gc = S.rad([(0, '#FFE6DC'), (.45, '#F08A6E'), (1, '#9E2F35')], .3, .3, .85)
        s.gw = S.rad([(0, '#FFFFFF'), (.55, '#DCE6F5'), (1, '#6F8FC8')], .3, .3, .85)
        s.ge = S.lin([(0, '#FFFFFF'), (1, '#9FB6DD')])

    def depthc(s, p, depth, kind):
        if kind == 'road':
            return '#1A2C55'
        return ['#24508A', '#145058', '#0E3040', '#081226'][depth]

    def sky(s, S, p):
        S.el('rect', width=360, height=200, fill=S.rad([(0, '#14294A'), (1, '#060B16')], .5, .55, .8))

    def stars(s, S, pts):
        for i, (x, y) in enumerate(pts):
            for k in range(5):
                S.path(drop(x, y, k * 2 * math.pi / 5 - math.pi / 2, 5.5, 3), fill=s.gw)

    def moon(s, S, x, y, r):
        S.glow(x, y, r * 3, '#DCE6F5', .3)
        S.el('circle', cx=x, cy=y, r=r, fill=s.gw)
        for k in range(10):
            a = k * 2 * math.pi / 10
            S.path(drop(x + (r + 2) * math.cos(a), y + (r + 2) * math.sin(a), a, 7, 3.5), fill=s.gt if k % 2 else s.gz)

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            g = s.gt if i == 0 else S.rad([(0, '#F2EEFF'), (.45, '#A99BF0'), (1, '#4A3AA8')], .3, .3, .85)
            for k in range(len(b) - 1):
                a0, a1 = b[k], b[k + 1]
                ang = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
                L = math.hypot(a1[0] - a0[0], a1[1] - a0[1])
                S.path(drop(a0[0], a0[1] - 8, ang, L * .95, 13), fill=g, fill_opacity=.85)
                S.path(drop(a0[0] + 10, a0[1] - 22, ang, L * .6, 7), fill=g, fill_opacity=.5)

    def band(s, S, pts, depth, kind, p):
        S.path(P(pts), fill=s.depthc(p, depth, kind))
        if kind == 'kerb':
            return
        top = sorted(pts, key=lambda q: q[1])
        # «травка» по верхнему краю: мазки-капли
        if kind in ('hill', 'shore', 'road') and depth >= 1:
            edge = [q for q in pts if q[1] < 199]
            for q in edge[::2]:
                S.path(drop(q[0], q[1] + 1, -math.pi / 2 - .5, 9, 4), fill=s.gt)
                S.path(drop(q[0] + 3, q[1] + 1, -math.pi / 2 + .5, 8, 4), fill=s.gz)

    def pine(s, S, x, yb, h, depth, p):
        S.path(P(taper([(x, yb), (x, yb - h)], 3.2, 1)), fill='#9FB6DD')
        n = 5 if h < 140 else 6
        for i in range(n):
            t = i / n
            y = yb - h * .18 - h * .78 * t
            L = h * .3 * (1 - t * .75) + 4
            for sg in (-1, 1):
                S.path(drop(x, y, math.pi / 2 + sg * 1.05, L, L * .45), fill=s.gt if (i + (sg > 0)) % 2 else s.gz)
        S.path(drop(x, yb - h * .96, -math.pi / 2, 10, 5), fill=s.gt)

    def building(s, S, x, yb, w, h, roof, wins, depth, p, i):
        S.path(P([(x, yb), (x, yb - h), (x + w, yb - h), (x + w, yb)]), fill=s.ge if i % 2 == 0 else '#C9D6EE')
        rp = s.roof_pts(x, yb, w, h, roof)
        S.path(P(rp), fill='#1D4398')
        for (wx, wy, ww, wh, lit) in wins:
            s.window(S, wx, wy, ww, wh, lit, p)
        # кобальтовый мазок-узор по фасаду
        for k in range(int(w // 14)):
            S.path(drop(x + 7 + k * 14, yb - 3, -math.pi / 2, 9, 4.5), fill=s.gz)

    def window(s, S, x, y, w, h, lit, p):
        if lit:
            S.glow(x + w / 2, y + h / 2, w * 1.6, WARM, .45)
        S.path(P([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill=s.gc if lit else '#1D4398')

    def dome(s, S, x, y, r, depth, p, only_cross=False):
        if only_cross:
            return
        S.path(drop(x, y - r * 2.4, math.pi / 2, r * 2.6, r * 2), fill=s.gt)
        S.line([(x, y - r * 2.4), (x, y - r * 3)], '#DCE6F5', 1.2)

    def house(s, S, x, yb, w, p):
        h = 44
        S.path(P([(x + 6, yb), (x + 6, yb - h), (x + w - 6, yb - h), (x + w - 6, yb)]), fill=S.lin([(0, '#D2584C'), (1, '#8E2E34')]))
        S.path(P([(x - 4, yb - h + 2), (x + w / 2, yb - h - 36), (x + w + 4, yb - h + 2)]), fill='#1D4398')
        for k in range(7):
            S.path(drop(x + w / 2 - 36 + k * 12, yb - h + 2, math.pi / 2, 9, 5), fill=s.gw)
        S.path(P([(x + 74, yb - h - 18), (x + 74, yb - h - 34), (x + 84, yb - h - 34), (x + 84, yb - h - 10)]), fill='#C9D6EE')
        s.window(S, x + 36, yb - 32, 18, 16, True, p)
        for sg in (-1, 1):
            S.path(drop(x + 45, yb - 38, -math.pi / 2 + sg * 1.2, 12, 5), fill=s.gw)
        for k in range(3):
            S.path(drop(x + 20 + k * 30, yb - 6, -math.pi / 2, 10, 6), fill=s.gt)

    def smoke(s, S, pts, p):
        for k, (x, y) in enumerate(pts[1:]):
            S.path(drop(x, y + 6, -math.pi / 2 + (.4 if k % 2 else -.4), 12, 6), fill=s.gw, fill_opacity=.6)

    def road(s, S, pts, p):
        S.path(P(pts), fill='#1A2C55')
        for t in (.2, .45, .7):
            q = lerp((188, 132), (188, 200), t)
            S.path(drop(q[0], q[1], math.pi / 2, 6 + t * 10, 3 + t * 4), fill=s.gw, fill_opacity=.6)

    def fence(s, S, x0, x1, y, h, p):
        x = x0
        while x <= x1:
            S.path(drop(x, y, -math.pi / 2, h + 2, 4.5), fill=s.gw)
            x += 9
        S.line([(x0, y - h * .5), (x1, y - h * .5)], '#9FB6DD', 1.6)

    def fire(s, S, x, y, p):
        S.glow(x, y - 6, 40, CORAL, .6)
        for a, L in ((-1.9, 16), (-1.57, 24), (-1.25, 16), (-2.3, 10), (-.85, 10)):
            S.path(drop(x, y, a, L, L * .5), fill=s.gc)
        S.path(drop(x, y, -1.57, 12, 5), fill='#FFF0E6')

    def lamp(s, S, x, yb, h, p):
        S.glow(x, yb - h, 40, WARM, .55)
        S.path(P(taper([(x, yb), (x, yb - h)], 3, 2)), fill='#9FB6DD')
        for k in range(6):
            a = k * math.pi / 3
            S.path(drop(x, yb - h, a, 8, 4), fill=s.gc)
        S.el('circle', cx=x, cy=yb - h, r=3.5, fill='#FFF0E6')

    def water(s, S, y0, y1, bands, p):
        S.path(P([(-10, y0), (370, y0), (370, y1), (-10, y1)]), fill='#0C2448')
        for k, y in enumerate(range(int(y0) + 8, int(y1) - 4, 10)):
            for j in range(4):
                xx = 40 + j * 80 + (k % 2) * 40
                S.path(drop(xx, y, 0, 26, 4), fill=s.gt if (j + k) % 2 else s.gz, fill_opacity=.7)

    def rock(s, S, x, y, r, p):
        S.path(drop(x - r, y + 2, -.3, r * 2, r * 1.2), fill=s.gz)

    def meeple(s, S, x, y, col=TURQ, ink='#0B1A34', lw=.8):
        Base.meeple(s, S, x, y, col, ink, lw)

    def finish(s, S, sc):
        segs = []
        for x in range(6, 360, 14):
            segs.append([(x, 8), (x + 4, 3), (x + 9, 5)])
            segs.append([(x, 192), (x + 4, 197), (x + 9, 195)])
        S.lines(segs, TURQ, 1.3, stroke_opacity=.7)
        S.el('rect', x=4, y=11, width=352, height=178, rx=10, fill='none', stroke=TURQ, stroke_width=1, stroke_opacity=.45)
        return S


# ============================================================ 5. КНИЖНАЯ ИЛЛЮСТРАЦИЯ
class Book(Base):
    key = 'book'
    stroke = '#0A0E12'
    lw = .9

    def begin(s, S, sc):
        s.sc = sc
        s.cache = {}

    def gr(s, S, c):
        if c not in s.cache:
            s.cache[c] = S.lin([(0, lt(c, .12)), (1, dk(c, .3))])
        return s.cache[c]

    def fill(s, S, pts, col, sm=False, lw=None, **a):
        if col.startswith('#') and len(col) == 7 and col != WARM:
            col = s.gr(S, col)
        Base.fill(s, S, pts, col, sm, lw, **a)

    def depthc(s, p, depth, kind):
        if kind == 'road':
            return p['road']
        if kind == 'kerb':
            return '#CDBF9E'
        return {'city': ['#2A3A66', '#24375A', '#1E2A40', '#141C2B'], 'village': ['#1F4A40', '#2A5A3E', '#244A32', '#16301F'],
                'north': ['#2A4A70', '#173A34', '#2A3A30', '#122A22']}[s.sc][depth]

    def sky(s, S, p):
        S.el('rect', width=360, height=200, fill=S.lin([(0, p['sky0']), (.65, p['sky1']), (1, p['hor'])]))
        # тонкая гравюрная штриховка неба
        S.lines([[(14, y), (346, y)] for y in range(16, 90, 6)], '#CDBF9E', .4, stroke_opacity=.18)

    def stars(s, S, pts):
        for x, y in pts:
            S.lines([[(x - 3, y), (x + 3, y)], [(x, y - 3), (x, y + 3)]], '#E9DFC8', .8, stroke_opacity=.8)

    def moon(s, S, x, y, r):
        S.glow(x, y, r * 3, '#E9F7F2', .3)
        S.el('circle', cx=x, cy=y, r=r, fill='#E9F7F2', stroke=s.stroke, stroke_width=.8)
        S.el('circle', cx=x, cy=y, r=r + 4, fill='none', stroke='#CDBF9E', stroke_width=.6, stroke_opacity=.6)

    def aurora(s, S, bands, p):
        for i, b in enumerate(bands):
            c = TURQ if i == 0 else VIOL
            top = [(x, y - 26) for x, y in b]
            S.path(smooth(b + top[::-1]), fill=S.lin([(0, c, .1), (1, c, .7)]), stroke=s.stroke, stroke_width=.6)
            S.lines([[lerp(q, (q[0], q[1] - 26), .1), lerp(q, (q[0] + 4, q[1] - 26), .9)] for k in range(len(b) - 1)
                     for q in [lerp(b[k], b[k + 1], t) for t in (.1, .35, .6, .85)]], lt(c, .4), .7, stroke_opacity=.7)

    def pine(s, S, x, yb, h, depth, p):
        Base.fill(s, S, taper([(x, yb), (x, yb - h)], 4, 1.5), '#3A2A22')
        col = s.depthc(p, min(depth, 3), 'tree')
        tiers = 6
        for i in range(tiers):
            t = i / tiers
            y = yb - h * .15 - h * .8 * t
            ww = h * .5 * (1 - t * .8)
            pts = [(x, y - h * .2), (x - ww * .2, y - h * .08), (x - ww / 2, y + 3), (x - ww * .3, y + 1), (x, y + 4),
                   (x + ww * .3, y + 1), (x + ww / 2, y + 3), (x + ww * .2, y - h * .08)]
            s.fill(S, pts, col)

    def window(s, S, x, y, w, h, lit, p):
        if lit:
            S.glow(x + w / 2, y + h / 2, w * 1.5, WARM, .35)
        Base.fill(s, S, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], WARM if lit else '#1A2638', lw=.8)
        # наличник
        Base.fill(s, S, [(x - 2, y - 1), (x + w / 2, y - 5), (x + w + 2, y - 1)], '#CDBF9E', lw=.6)

    def house(s, S, x, yb, w, p):
        Base.house(s, S, x, yb, w, p)
        S.lines([[(x + 8, y), (x + w - 8, y)] for y in range(yb - 40, yb, 5)], dk(p['wall'], .5), .6)
        S.lines([[(x + w / 2, yb - 80), (x + w / 2, yb - 44)], [(x + 6, yb - 44), (x + w - 6, yb - 44)]], '#CDBF9E', .8)

    def water(s, S, y0, y1, bands, p):
        Base.fill(s, S, [(-10, y0), (370, y0), (370, y1), (-10, y1)], S.lin([(0, '#1E4E6A'), (1, '#0A1A2A')]))
        S.lines([[(30 + (k % 3) * 20, y), (330 - (k % 2) * 30, y)] for k, y in enumerate(range(int(y0) + 4, int(y1), 4))], TURQ, .5,
                stroke_opacity=.35)

    def finish(s, S, sc):
        acc = TURQ
        S.el('rect', x=3, y=3, width=354, height=194, fill='none', stroke='#0D141D', stroke_width=8)
        S.el('rect', x=3, y=3, width=354, height=194, fill='none', stroke='#CDBF9E', stroke_width=1, stroke_opacity=.75)
        S.el('rect', x=8, y=8, width=344, height=184, fill='none', stroke='#CDBF9E', stroke_width=.6, stroke_opacity=.55)
        # угловые розетки
        for (x, y) in ((8, 8), (352, 8), (8, 192), (352, 192)):
            S.el('circle', cx=x, cy=y, r=5, fill='#0D141D', stroke='#CDBF9E', stroke_width=.8)
            S.el('circle', cx=x, cy=y, r=2, fill=acc)
        # верхняя орнаментальная планка
        S.path(P([(130, 3), (230, 3), (222, 13), (138, 13)]), fill='#0D141D', stroke='#CDBF9E', stroke_width=.8)
        for k in range(5):
            S.path(leaf(156 + k * 12, 8, 0, 8, 4), fill=acc if k % 2 else CORAL, stroke=s.stroke, stroke_width=.5)
        return S


STYLES = [Glass(), Lubok(), Planes(), Rospis(), Book()]


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for st in STYLES:
        if only and st.key not in only:
            continue
        for name, fn in SCENES:
            svg = fn(st).render()
            n = check(f'{st.key}_{name}', svg)
            with open(f'{OUT}/{st.key}_{name}.svg', 'w') as fh:
                fh.write(svg)
            print(f'{st.key}_{name}.svg {n / 1024:.1f} KB')


if __name__ == '__main__':
    main()

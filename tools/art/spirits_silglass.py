"""Духи «Путника» в стиле «Витражный силуэт» (выбор владельца, ноябрь 2026).

Чёрные силуэты существ; небо, луна/солнце, сияние, свет, вода и глаза — крупные стёкла со свинцом.
9 существ × 4 настроения (neutral, kind, cunning, angry) -> app/assets/art/spirits/<creature>_<mood>.svg (360×200)
+ эмблемы-медальоны 120×120 -> app/assets/art/creatures/<creature>.svg

python3 tools/art/spirits_silglass.py [--sheet PATH] [creature ...]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import Svg, P, smooth, mir, taper, tf, ell, drop, leaf, lerp, mix, lt, dk, LEAD, TURQ, CORAL, DANGER
from creature_styles import l_antler, l_hair_leaves, L_FACE, L_SHOULD, D_BODY, ae, happy_eye, scallops, pine, sym

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SPIRITS = os.path.join(ROOT, 'app/assets/art/spirits')
EMBLEMS = os.path.join(ROOT, 'app/assets/art/creatures')
BLK = '#04070A'
LW = 1.3
MAX = 25 * 1024

MOODS = {
    'neutral': dict(panes=['#0F3B4C', '#155A6B', '#0C2C3C', '#1E6A78'], light='#9FEDE4', eye=TURQ, deep='#0A2230'),
    'kind': dict(panes=['#1F6A4E', '#2E8A5E', '#7A4A3A', '#C8785A'], light='#FFC9A8', eye='#FFD2B4', deep='#1A3A2C'),
    'cunning': dict(panes=['#2A1A5A', '#3E2A7A', '#1E1444', '#5B3FA0'], light='#C9A8FF', eye='#C9A8FF', deep='#160E36'),
    'angry': dict(panes=['#5A1A24', '#8E2E34', '#3E1219', '#B2453F'], light='#FF9A86', eye=DANGER, deep='#2A0A10'),
}
MOOD_ORDER = ['neutral', 'kind', 'cunning', 'angry']


class C:
    """Контекст рисования одной картинки."""

    def __init__(s, mood, w=360, h=200):
        s.S = Svg(w, h)
        s.mood = mood
        s.m = MOODS[mood]
        s.cache = {}

    def gl(s, c, ang=1):
        k = (c, ang)
        if k not in s.cache:
            s.cache[k] = s.S.lin([(0, lt(c, .2)), (.6, c), (1, dk(c, .2))], 0, 0, .25 * ang, 1)
        return s.cache[k]

    def pane(s, pts, c, lw=LW, sm=False, op=None):
        s.S.path(smooth(pts) if sm else P(pts), fill=s.gl(c), stroke=LEAD, stroke_width=lw, stroke_linejoin='round', fill_opacity=op)

    def sil(s, d, lw=2.4):
        s.S.path(d, fill=BLK, stroke=LEAD, stroke_width=lw, stroke_linejoin='round')

    def bg(s, cx=180, cy=70, n=16, rot=.1):
        S = s.S
        S.el('rect', width=360, height=200, fill=LEAD)
        cols = s.m['panes']
        for i in range(n):
            a0, a1 = rot + 2 * math.pi * i / n, rot + 2 * math.pi * (i + 1) / n
            S.path(P([(cx, cy), (cx + 420 * math.cos(a0), cy + 420 * math.sin(a0)), (cx + 420 * math.cos(a1), cy + 420 * math.sin(a1))]),
                   fill=s.gl(cols[i % 4]), stroke=LEAD, stroke_width=LW)

    def disc(s, x, y, r, col=None, seg=6, glow=True):
        col = col or s.m['light']
        if glow:
            s.S.glow(x, y, r * 2.6, col, .45)
        for k in range(seg):
            a0, a1 = k * 2 * math.pi / seg + .3, (k + 1) * 2 * math.pi / seg + .3
            pts = [(x, y)] + [(x + r * math.cos(a0 + (a1 - a0) * t / 3), y + r * math.sin(a0 + (a1 - a0) * t / 3)) for t in range(4)]
            s.pane(pts, lt(col, .12) if k % 2 else col)

    def grid(s, x0, y0, x1, y1, nx, ny, cols, mull=3.5):
        S = s.S
        k = 0
        for i in range(nx):
            for j in range(ny):
                a, b = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
                c, d = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
                s.pane([(a, c), (b, c), (b, d), (a, d)], cols[k % len(cols)])
                k += 1
        S.path(P([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), fill='none', stroke=BLK, stroke_width=mull)

    def water(s, y0, y1=200, tint=None):
        tint = tint or s.m['panes'][3]
        rows = [(y0, y0 + (y1 - y0) * .35), (y0 + (y1 - y0) * .35, y0 + (y1 - y0) * .7), (y0 + (y1 - y0) * .7, y1 + 2)]
        for i, (a, b) in enumerate(rows):
            xs = [-10, 70, 150, 230, 300, 370]
            for k in range(5):
                c = mix(tint, s.m['light'] if (i + k) % 2 == 0 else s.m['panes'][2], .35 - i * .1)
                sh = i * 7
                s.pane([(xs[k] + sh, a), (xs[k + 1] + sh, a), (xs[k + 1] + sh + 7, b), (xs[k] + sh + 7, b)], c)

    def stars(s, pts):
        d = ''.join(P([(x, y - 3), (x + .9, y - .9), (x + 3, y), (x + .9, y + .9), (x, y + 3), (x - .9, y + .9), (x - 3, y), (x - .9, y - .9)])
                    for x, y in pts)
        s.S.path(d, fill='#E8FFFB', stroke=LEAD, stroke_width=.5)

    def frame(s):
        s.S.el('rect', x=1.5, y=1.5, width=357, height=197, fill='none', stroke=LEAD, stroke_width=5, rx=3)

    # --- лицо
    def eyes(s, cx, ey, ex, ew=12, eh=7, kind='almond', far=1.0):
        """kind: almond | round (лягушачьи) | cat. far — масштаб дальнего (правого) глаза для 3/4."""
        S, mood, ec = s.S, s.mood, s.m['eye']
        for side in (-1, 1):
            x = cx + side * ex
            sc = far if side > 0 else 1.0
            w, h = ew * sc, eh * sc
            if mood == 'kind':
                arc = happy_eye(x, ey, w, h * .9)
                S.line(arc, LEAD, 5, smooth_=True)
                S.line(arc, ec, 2.8, smooth_=True)
                S.glow(x, ey, w * 1.2, ec, .35)
                continue
            S.glow(x, ey, w * 1.3, ec, .5)
            if mood == 'angry':
                pts, (ix, iy) = ae(x, ey, 'angry', side, w * 1.1, h)
                S.path(P(pts), fill=s.gl(lt(ec, .25)), stroke=LEAD, stroke_width=1.1)
                S.el('circle', cx=ix, cy=iy, r=1.6 * sc, fill='#FFE6E0')
                S.path(P(taper([(x - side * w * .55, ey - h * .25), (x + side * w * .6, ey - h * 1.25)], 2.6, 1.6)), fill=s.gl(ec))
                continue
            if mood == 'cunning' and side < 0:
                hh = h * .32
            elif mood == 'cunning':
                hh = h * .8
            else:
                hh = h
            if kind == 'round' and mood != 'cunning':
                S.el('circle', cx=x, cy=ey, r=w / 2, fill=s.gl(lt(ec, .3)), stroke=LEAD, stroke_width=1.1)
                S.el('circle', cx=x, cy=ey + .5, r=w * .18, fill=BLK)
                continue
            up = [(x - w / 2 + w * i / 8, ey - hh / 2 * math.sin(math.pi * i / 8)) for i in range(9)]
            lo = [(x + w / 2 - w * i / 8, ey + hh / 2 * .85 * math.sin(math.pi * i / 8)) for i in range(1, 8)]
            if kind == 'cat':
                up = [(x - w / 2, ey + hh * .1), (x - w * .1, ey - hh / 2), (x + w / 2, ey - hh * .25)]
                lo = [(x + w * .2, ey + hh / 2)]
                if side > 0:
                    up, lo = [(2 * x - a, b) for a, b in up], [(2 * x - a, b) for a, b in lo]
            S.path(smooth(up + lo) if kind != 'cat' else P(up + lo), fill=s.gl(lt(ec, .3)), stroke=LEAD, stroke_width=1.1)
            if kind == 'cat':
                S.el('ellipse', cx=x, cy=ey, rx=.9 * sc, ry=hh * .42, fill=BLK)
            elif hh > 3:
                S.el('circle', cx=x, cy=ey + .4, r=min(hh, w) * .22, fill=BLK)
            if mood == 'cunning' and side > 0:
                S.path(P(taper([(x - w * .5, ey - h * .9), (x, ey - h * 1.5), (x + w * .6, ey - h * 1.2)], 2.2, 1.4)), fill=s.gl(ec))

    def mouth(s, x, y, w=22):
        S, mood = s.S, s.mood
        if mood == 'kind':
            S.path(smooth([(x - w / 2, y - 1), (x - w / 4, y + 3.5), (x, y + 4.5), (x + w / 4, y + 3.5), (x + w / 2, y - 1), (x, y + 1.2)]),
                   fill=s.gl('#FFB09A'), stroke=LEAD, stroke_width=1)
        elif mood == 'cunning':
            S.path(smooth([(x - w * .45, y + 1.5), (x - w * .1, y + 3), (x + w * .3, y + 1), (x + w * .55, y - 4), (x + w * .25, y - .5),
                           (x - w * .1, y + .6)]), fill=s.gl(s.m['light']), stroke=LEAD, stroke_width=1)
            S.path(P([(x + w * .18, y + 1.2), (x + w * .26, y + 5), (x + w * .32, y + .6)]), fill='#F2EEFF')
        elif mood == 'angry':
            m = [(x - w * .7, y), (x - w * .35, y - 3), (x, y - 1.5), (x + w * .35, y - 3), (x + w * .7, y), (x + w * .5, y + 11),
                 (x, y + 16), (x - w * .5, y + 11)]
            S.glow(x, y + 6, w * 1.1, DANGER, .45)
            S.path(P(m), fill=s.gl('#FF8A7A'), stroke=LEAD, stroke_width=1.1)
            d = ''
            for k in range(4):
                tx = x - w * .45 + k * w * .3
                d += P([(tx - 2.6, y - 1.5), (tx + 2.6, y - 1.5), (tx, y + 5.5)])
            for tx in (x - w * .25, x + w * .25):
                d += P([(tx - 2.6, y + 13), (tx + 2.6, y + 13), (tx, y + 7)])
            S.path(d, fill=BLK)

    # --- руки
    def hand(s, x, y, ang, claws=False, beckon=False):
        S = s.S
        s.sil(P(ell(x, y, 7, 6.5, 10)), 1.8)
        if claws:
            for a in (-.9, -.45, 0, .45, .9):
                aa = ang + a
                mid = (x + 9 * math.cos(aa + .25), y + 9 * math.sin(aa + .25))
                tip = (x + 19 * math.cos(aa), y + 19 * math.sin(aa))
                s.sil(P(taper([(x, y), mid, tip], 4.5, .6)), 1.4)
        elif beckon:
            tip = (x + 15 * math.cos(ang), y + 15 * math.sin(ang))
            hook = (tip[0] + 5 * math.cos(ang + 1.6), tip[1] + 5 * math.sin(ang + 1.6))
            s.sil(P(taper([(x, y), tip, hook], 4, 2.2)), 1.4)
            for a in (.9, 1.3, 1.7):
                s.sil(P(taper([(x, y), (x + 9 * math.cos(ang + a), y + 9 * math.sin(ang + a))], 4, 3)), 1.2)

    def arms(s, L, R, gift=None, reach=1.0):
        """Позы по настроению. L, R — плечи (x, y). gift(c, x, y) рисует дар над правой рукой."""
        mood = s.mood
        if mood == 'angry':
            for (x, y), side in ((L, -1), (R, 1)):
                el = (x + side * 26, y - 22)
                hd = (x + side * 18 * reach, y - 60)
                s.sil(P(taper([(x, y), el, hd], 20, 11)))
                s.hand(hd[0], hd[1], -math.pi / 2 + side * .35, claws=True)
        elif mood == 'kind':
            x, y = R
            el = (x + 30, y + 4)
            hd = (x + 52 * reach, y - 16)
            s.sil(P(taper([(x, y), el, hd], 18, 11)))
            s.hand(hd[0], hd[1], -math.pi / 2)
            if gift:
                gift(s, hd[0] + 2, hd[1] - 10)
        elif mood == 'cunning':
            x, y = L
            el = (x - 30, y + 2)
            hd = (x - 26 * reach, y - 44)
            s.sil(P(taper([(x, y), el, hd], 18, 11)))
            s.hand(hd[0], hd[1], -math.pi / 2 + .5, beckon=True)


# ============================================================ дары (стекло)
def g_branch(c, x, y):
    S = c.S
    S.glow(x, y - 6, 26, '#7FE0B0', .5)
    c.pane(taper([(x, y + 4), (x + 4, y - 22)], 3, 1.5), '#6B4A35')
    for k in range(5):
        t = k / 5
        p = lerp((x, y + 2), (x + 4, y - 20), t)
        for sg in (-1, 1):
            c.pane(taper([p, (p[0] + sg * 11 * (1 - t * .5), p[1] + 4)], 3.5, 1), '#2E9A62', lw=.9)
    c.pane(ell(x + 6, y - 8, 4, 6, 8), '#B4683C', lw=1)


def g_candle(c, x, y):
    S = c.S
    S.glow(x, y - 12, 30, '#FFB08A', .6)
    c.pane([(x - 5, y + 4), (x - 5, y - 10), (x + 5, y - 10), (x + 5, y + 4)], '#F4E6DA')
    c.pane([(x, y - 26), (x + 4, y - 15), (x, y - 11), (x - 4, y - 15)], '#FFC9A8', lw=1)


def g_ladle(c, x, y):
    S = c.S
    S.glow(x, y - 6, 26, '#FFC9A8', .45)
    c.pane([(x - 12, y - 6), (x + 10, y - 6), (x + 6, y + 4), (x - 8, y + 4)], '#B4683C')
    c.pane(taper([(x + 9, y - 5), (x + 22, y - 14)], 3, 2.4), '#8A4A28', lw=1)
    for k, dx in enumerate((-6, 0, 6)):
        S.line([(x + dx, y - 9), (x + dx - 3, y - 16), (x + dx + 2, y - 22), (x + dx - 1, y - 28)], lt('#FFE6D8', .2), 2.2, smooth_=True,
               stroke_opacity=.75)


def g_fish(c, x, y):
    c.S.glow(x, y - 4, 26, '#9FEDE4', .5)
    body = [(x - 16, y - 4), (x - 6, y - 11), (x + 8, y - 9), (x + 14, y - 4), (x + 8, y + 1), (x - 6, y + 2)]
    c.pane(body, '#7FC4EE', sm=True)
    c.pane([(x - 15, y - 4), (x - 24, y - 11), (x - 22, y - 4), (x - 24, y + 3)], '#5BB5E8', lw=1)
    c.S.el('circle', cx=x + 8, cy=y - 5.5, r=1.4, fill=BLK)


def g_wheat(c, x, y):
    c.S.glow(x, y - 12, 28, '#FFC9A8', .5)
    for k, a in enumerate((-.35, 0, .35)):
        top = (x + 26 * math.sin(a), y - 26 * math.cos(a))
        c.S.line([(x, y + 4), top], '#C8785A', 1.6)
        for j in range(4):
            p = lerp((x, y + 4), top, .55 + j * .12)
            for sg in (-1, 1):
                c.pane(tf([(0, 0), (3, 1.8), (6, 0), (3, -1.8)], p[0], p[1], -math.pi / 2 + a + sg * .5), '#F2B48A', lw=.7)


def g_wreath(c, x, y):
    c.S.glow(x, y - 6, 26, c.m['light'], .5)
    for k in range(8):
        a = k * math.pi / 4
        px, py = x + 10 * math.cos(a), y - 6 + 6 * math.sin(a)
        c.pane(ell(px, py, 3.6, 3.6, 7), ['#F2EEFF', '#FFC9A8', '#9FEDE4'][k % 3], lw=.8)


def g_ball(c, x, y):
    c.S.glow(x, y - 6, 26, TURQ, .55)
    c.pane(ell(x, y - 7, 9, 9, 14), '#5FE0D5')
    c.S.lines([[(x - 7, y - 11), (x + 6, y - 2)], [(x - 8, y - 6), (x + 3, y + 1)], [(x - 3, y - 15), (x + 8, y - 7)]], LEAD, .9)
    c.S.line([(x + 8, y - 3), (x + 16, y + 6), (x + 12, y + 14)], '#9FEDE4', 1.4, smooth_=True)


def g_spindle(c, x, y):
    c.S.glow(x, y - 8, 26, '#C9F2E4', .5)
    c.pane(taper([(x, y + 6), (x, y - 26)], 2.2, 1), '#B4683C', lw=.8)
    c.pane(ell(x, y - 8, 6, 9, 12), '#E6F2EE')
    c.S.line([(x + 1, y - 26), (x + 14, y - 30), (x + 20, y - 22)], '#E6F2EE', 1.2, smooth_=True)


def g_ember(c, x, y):
    c.S.glow(x, y - 6, 30, CORAL, .7)
    c.pane([(x - 9, y - 2), (x - 4, y - 12), (x + 6, y - 13), (x + 10, y - 4), (x + 3, y + 2)], '#F08A6E')
    c.pane([(x - 4, y - 12), (x + 1, y - 7), (x + 6, y - 13)], '#FFC9A8', lw=.9)


# ============================================================ существа
def leshy(c):
    A = c.mood == 'angry'
    c.bg(180, 70)
    c.disc(180, 70, 54)
    c.stars([(40, 22), (110, 12), (300, 18), (330, 60)])
    for x, h in ((20, 120), (52, 96), (84, 70), (276, 74), (308, 100), (340, 124)):
        c.pane(pine(x, 178, h, h * .42, 5), dk(c.m['panes'][2], .35))
    shapes = []
    for side in (-1, 1):
        for line, w0, w1 in l_antler(1, 1.15 if A else 1.0):
            shapes.append(P(taper(line if side == -1 else mir(line), w0 + .5, w1 + .3)))
    for (x, y, a, L, w) in l_hair_leaves():
        shapes.append(leaf(x, y, a, L * (1.2 if A else 1.05), w * (.75 if A else .95)))
    shapes += [smooth(L_FACE), P(L_SHOULD + [(74, 215), (286, 215)][::-1][:0])]
    bp = [(180, 96), (162, 97), (150, 104), (145, 124), (142, 152), (138, 182)]
    jag = []
    for k in range(9):
        x = 138 + k * 10.5
        jag += [(x, 182 + (k % 2) * 4), (x + 5, 196 + (k % 3) * 2)]
    shapes.append(P(bp + jag + mir(bp)[::-1][:-1]))
    return dict(shapes=shapes, face=(180, 77, 13, 13, 7.5, 'almond'), mouth=(180, 104, 22), anchors=((108, 140), (252, 140)),
                gift=g_branch, front=lambda c: [c.pane(pine(x, 204, h, h * .42, 5), BLK) for x, h in ((8, 150), (352, 156))])


def domovoy(c):
    c.S.el('rect', width=360, height=200, fill=LEAD)
    c.bg(180, 80, 12)
    cols = [c.m['light'], lt(c.m['panes'][3], .2), c.m['panes'][1], lt(c.m['light'], .15)]
    c.grid(112, 16, 248, 150, 3, 4, cols, 5)
    c.disc(222, 36, 9, '#F2FFFD', glow=True)
    # печь
    c.sil(P([(266, 210), (266, 70), (276, 60), (330, 60), (330, 30), (346, 30), (346, 60), (362, 60), (362, 210)]))
    c.S.glow(308, 176, 70, CORAL, .55)
    c.pane([(284, 202), (284, 164), (290, 152), (308, 146), (326, 152), (332, 164), (332, 202)], '#3A1E1A')
    for k, (x, h) in enumerate(((298, 24), (308, 34), (318, 22))):
        c.pane([(x - 7, 202), (x - 2, 202 - h * .6), (x, 202 - h), (x + 3, 202 - h * .5), (x + 7, 202)], ['#F08A6E', '#FFC9A8', '#E0555F'][k], lw=1)
    c.sil(P([(98, 150), (262, 150), (262, 158), (98, 158)]))
    c.sil(P([(-4, 186), (364, 186), (364, 204), (-4, 204)]))
    hp = sym([(180, 46), (171, 50), (163, 47), (157, 55), (148, 56), (146, 65), (137, 69), (139, 80), (132, 86),
              (137, 96), (131, 104), (139, 112), (180, 112)])
    bp = [(180, 104), (164, 105), (150, 112), (140, 126), (136, 144), (140, 162)]
    beard = bp + scallops((140, 162), (220, 162), 5, 8, out=-1)[1:-1] + mir(bp)[::-1][:-1]
    body = sym([(180, 124), (156, 128), (134, 138), (120, 156), (114, 210), (180, 210)])
    return dict(shapes=[P(hp), P(body), P(beard)], face=(180, 96, 11, 11, 6.5, 'almond'), mouth=(180, 112, 18),
                anchors=((130, 142), (230, 142)), gift=g_candle, beard_line=beard)


def bannik(c):
    c.bg(70, 40, 14, .3)
    c.grid(40, 18, 100, 64, 2, 2, [c.m['light'], c.m['panes'][3]], 4)
    # каменка с раскалёнными камнями
    c.sil(P([(250, 210), (250, 120), (330, 120), (330, 210)]))
    c.S.glow(290, 112, 54, CORAL, .55)
    for k, (x, y, r) in enumerate(((266, 116, 9), (284, 110, 11), (304, 114, 10), (322, 118, 8), (276, 124, 8), (296, 124, 9))):
        c.pane(ell(x, y, r, r * .75, 8), ['#F08A6E', '#E0555F', '#FFC9A8'][k % 3], lw=1.2)
    # пар — молочные стёкла
    for (x, y, r) in ((240, 50, 22), (270, 30, 16), (300, 60, 20), (120, 40, 16), (150, 20, 12), (330, 30, 14)):
        c.S.path(smooth(ell(x, y, r, r * .7, 10)), fill=c.gl('#EDF4F2'), fill_opacity=.45, stroke=LEAD, stroke_width=.8)
    # полок
    c.sil(P([(-4, 168), (110, 168), (110, 176), (-4, 176)]))
    c.sil(P([(-4, 186), (130, 186), (130, 194), (-4, 194)]))
    for x in (20, 90):
        c.sil(P([(x, 176), (x + 6, 176), (x + 6, 210), (x, 210)]))
    head = ell(180, 80, 21, 26, 22)
    hair = []
    for side in (-1, 1):
        for k, (dy, L, out) in enumerate(((-14, 30, 30), (-4, 40, 26), (6, 44, 18), (14, 40, 10))):
            x0 = 180 + side * 18
            hair.append(P(taper([(x0, 76 + dy), (x0 + side * out * .7, 88 + dy), (x0 + side * out, 76 + dy + L)], 5, .8)))
    beard = [(166, 102), (194, 102), (190, 130), (184, 158), (180, 176), (176, 158), (170, 130)]
    body = sym([(180, 112), (164, 116), (138, 124), (116, 140), (108, 210), (180, 210)])
    # веник
    broom = []
    if c.mood in ('neutral', 'cunning'):
        bx = 262
        broom.append(P(taper([(bx, 198), (bx - 10, 138)], 4.5, 3.5)))
        for k in range(9):
            a = -math.pi / 2 - .55 + k * .14
            broom.append(leaf(bx - 10, 140, a, 34 + (k % 3) * 6, 7))
    return dict(shapes=[P(body)] + hair + [P(head), P(beard)] + broom, face=(180, 82, 11, 11, 6.5, 'almond'), mouth=(180, 102, 16),
                anchors=((120, 136), (240, 136)), gift=g_ladle)


def vodyanoy(c):
    c.bg(286, 40, 16)
    c.disc(286, 40, 20)
    c.stars([(30, 20), (120, 14), (200, 26)])
    # мельничное колесо
    cx, cy, r = 62, 116, 54
    d = ''
    for k in range(10):
        a = k * math.pi / 5
        d += P(taper([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], 4, 3))
        pa = (cx + r * math.cos(a), cy + r * math.sin(a))
        d += P(tf([(-2, -8), (12, -8), (12, 8), (-2, 8)], pa[0], pa[1], a))
    ring = ell(cx, cy, r, r, 30)
    inner = ell(cx, cy, r - 6, r - 6, 30)[::-1]
    c.S.path(d + P(ring) + P(inner), fill=BLK, stroke=LEAD, stroke_width=1.6, fill_rule='evenodd')
    c.S.el('circle', cx=cx, cy=cy, r=8, fill=BLK)
    # камыш
    for x, h in ((300, 70), (312, 84), (326, 62), (340, 78), (122, 50)):
        c.sil(P(taper([(x, 176), (x + 2, 176 - h)], 2.6, 1.6)), 1)
        c.sil(P(ell(x + 2, 176 - h + 10, 3, 9, 8)), 1)
    head = sym([(180, 58), (168, 60), (158, 54), (148, 56), (144, 66), (146, 76), (138, 88), (142, 104), (154, 112), (180, 114)])
    crown = []
    for k, (x, h) in enumerate(((166, 18), (176, 24), (186, 22), (196, 16))):
        crown.append(P(taper([(x, 62), (x + (k - 1.5) * 3, 62 - h)], 3, 1)))
    beard = []
    for k in range(9):
        x = 150 + k * 7.5
        beard.append(P(taper([(x, 106), (x + math.sin(k) * 6, 140), (x - math.sin(k) * 4, 176)], 7, 2.5, 8)))
    body = sym([(180, 110), (150, 112), (120, 120), (98, 136), (88, 160), (84, 210), (180, 210)])
    return dict(shapes=[P(body)] + beard + crown + [P(head)], face=(180, 66, 16, 13, 11, 'round'), mouth=(180, 98, 34),
                anchors=((104, 140), (256, 140)), gift=g_fish, front=lambda c: c.water(166))


def poludnitsa(c):
    sun = '#FFD8C0' if c.mood in ('neutral', 'kind') else c.m['light']
    c.bg(180, 62, 20, .05)
    c.disc(180, 62, 50, sun, seg=8)
    for k in range(12):
        a = k * math.pi / 6 + .26
        p0 = (180 + 56 * math.cos(a), 62 + 56 * math.sin(a))
        c.pane(tf([(0, -4), (14, 0), (0, 4)], p0[0], p0[1], a), lt(sun, .1), lw=1)
    head = ell(180, 70, 15, 19, 18)
    hair = [P(sym([(180, 50), (164, 54), (156, 70), (152, 96), (146, 128), (180, 128)]))]
    # венок из колосьев на голове
    crown = []
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * .32
        base = (180 + 16 * math.cos(a), 66 + 18 * math.sin(a))
        tip = (180 + 32 * math.cos(a), 66 + 34 * math.sin(a))
        crown.append(P(taper([base, tip], 3, 1)))
        crown.append(P(ell(tip[0], tip[1], 3, 3, 6)))
    body = sym([(180, 90), (166, 94), (148, 102), (132, 118), (122, 160), (112, 210), (180, 210)])
    # серп
    sx, sy = (262, 132) if c.mood != 'angry' else (0, 0)
    sickle = []
    if c.mood in ('neutral', 'cunning'):
        sickle.append(P(taper([(240, 150), (248, 168)], 4, 3)))
        out = ell(250, 128, 22, 22, 14, math.pi * .55, math.pi * 1.95)
        inn = ell(254, 126, 17, 16, 14, math.pi * .6, math.pi * 1.9)[::-1]
        sickle.append(P(out + inn))
    # колосья спереди
    def front(c):
        d = ''
        rnd = random.Random(3)
        for k in range(26):
            x = rnd.uniform(-4, 364)
            if 112 < x < 248:
                continue
            h = rnd.uniform(30, 64)
            lean = rnd.uniform(-6, 6)
            d += P(taper([(x, 204), (x + lean, 204 - h)], 2.4, 1))
            for j in range(4):
                p = (x + lean * (1 - j * .06), 204 - h + j * 5)
                d += P(tf([(0, 0), (3, 2), (7, 0), (3, -2)], p[0], p[1], -math.pi / 2 - .5)) + P(tf([(0, 0), (3, 2), (7, 0), (3, -2)], p[0], p[1], -math.pi / 2 + .5))
        c.S.path(d, fill=BLK, stroke=LEAD, stroke_width=.8)
    return dict(shapes=hair + [P(body)] + crown + [P(head)] + sickle, face=(180, 70, 7, 8, 5, 'almond'), mouth=(180, 80, 10),
                anchors=((134, 116), (226, 116)), gift=g_wheat, front=front)


def rusalka(c):
    c.bg(100, 44, 16, .2)
    c.disc(100, 44, 22)
    c.stars([(200, 16), (250, 40), (320, 20), (40, 70)])
    # ветви ивы сверху
    d = ''
    rnd = random.Random(5)
    for k in range(18):
        x = rnd.uniform(-10, 370)
        if 140 < x < 220:
            continue
        L = rnd.uniform(40, 110)
        pts = [(x, -4), (x + 4, L * .4), (x - 2, L)]
        d += P(taper(pts, 2.4, .8))
        for j in range(5):
            p = lerp(pts[1], pts[2], j / 5)
            d += leaf(p[0], p[1], math.pi / 2 + (.5 if j % 2 else -.5), 9, 3)
    c.S.path(d, fill=BLK, stroke=LEAD, stroke_width=.7)
    head = ell(180, 76, 14, 18, 18)
    hair = sym([(180, 54), (164, 58), (156, 74), (150, 100), (140, 130), (134, 160), (126, 190), (120, 210), (180, 210)])
    hair = [(x + 6 * math.sin(y / 14) * (abs(x - 180) / 60), y) for x, y in hair]
    body = sym([(180, 96), (166, 100), (152, 108), (146, 130), (144, 210), (180, 210)])
    flowers = []
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * .38
        flowers.append((180 + 17 * math.cos(a), 72 + 20 * math.sin(a)))

    def front(c):
        c.water(168)
        # отражение луны
        for k in range(4):
            y = 172 + k * 7
            c.pane([(90 - 14 + k * 3, y), (110 + 14 - k * 3, y), (108 + 10 - k * 3, y + 4), (92 - 10 + k * 3, y + 4)], c.m['light'], lw=.9)
        for k, (x, y) in enumerate(flowers):
            c.pane(ell(x, y, 3.6, 3.6, 7), ['#F2EEFF', '#FFC9A8', '#9FEDE4'][k % 3], lw=.9)
    return dict(shapes=[P(hair), P(body), P(head)], face=(180, 78, 6.5, 8, 5, 'almond'), mouth=(180, 88, 9),
                anchors=((150, 120), (210, 120)), gift=g_wreath, front=front)


def baba_yaga(c):
    c.bg(240, 50, 16)
    c.disc(240, 50, 26)
    c.stars([(40, 20), (90, 40), (150, 14), (330, 24)])
    # избушка на курьих ножках
    hut = [(276, 120), (276, 82), (270, 82), (302, 58), (334, 82), (328, 82), (328, 120)]
    c.sil(P(hut))
    for x0 in (290, 314):
        c.sil(P(taper([(x0, 120), (x0 - 4, 140), (x0 + 2, 160), (x0, 180)], 5, 3)), 1.4)
        for a in (-.5, 0, .5):
            c.sil(P(taper([(x0, 180), (x0 + 12 * math.sin(a) + 6 * (a == 0), 186)], 3, 1)), 1)
    c.S.glow(302, 98, 22, '#FFB08A', .6)
    c.grid(294, 90, 310, 106, 2, 2, ['#FFC9A8', '#F08A6E'], 2)
    # ступа
    c.sil(P([(30, 210), (36, 156), (84, 156), (90, 210)]))
    c.sil(P(taper([(64, 156), (52, 96)], 4, 3)))
    # фигура: голова 3/4, платок, нос, горб
    head = [(184, 54), (170, 56), (158, 66), (154, 76), (146, 82), (130, 92), (122, 104), (128, 104), (140, 98), (150, 100),
            (146, 108), (138, 118), (152, 116), (170, 116), (186, 112), (196, 100), (200, 84), (196, 66)]
    scarf = [(186, 46), (164, 50), (150, 66), (146, 86), (156, 76), (166, 64), (186, 60), (202, 74), (204, 96), (198, 114),
             (214, 128), (222, 104), (216, 70), (204, 52)]
    knot = [(186, 112), (178, 128), (192, 132), (198, 118)]
    body = [(160, 110), (140, 122), (124, 142), (114, 170), (110, 210), (262, 210), (254, 168), (244, 136), (230, 112), (210, 100),
            (196, 108)]
    staff = [P(taper([(112, 204), (104, 84)], 4.5, 3.5)), P(taper([(104, 86), (98, 72), (106, 64), (114, 70)], 4, 3))]
    return dict(shapes=[P(body), P(scarf), P(head), P(knot)] + staff, face=(178, 84, 9, 10, 6.5, 'almond', .8), mouth=(168, 104, 14),
                anchors=((128, 140), (240, 132)), gift=g_ball)


def kikimora(c):
    c.bg(180, 70, 16, .1)
    c.disc(240, 34, 13)
    c.stars([(40, 22), (100, 50), (300, 60), (150, 14)])
    # блуждающие огоньки
    for (x, y) in ((60, 110), (300, 100), (96, 70), (330, 130)):
        c.S.glow(x, y, 12, c.m['light'], .6)
        c.pane(ell(x, y, 3.5, 4.5, 8), c.m['light'], lw=.8)
    # рогоз
    d = ''
    for x, h in ((20, 120), (36, 96), (52, 130), (300, 110), (318, 132), (338, 100), (352, 120)):
        d += P(taper([(x, 200), (x + 3, 200 - h)], 2.6, 1.4)) + P(ell(x + 3, 200 - h + 14, 3.5, 11, 8))
        d += leaf(x, 200, -math.pi / 2 - .4, h * .6, 4)
    c.S.path(d, fill=BLK, stroke=LEAD, stroke_width=.8)
    # прялка с куделью
    c.sil(P([(104, 210), (104, 196), (140, 196), (140, 210)]))
    c.sil(P(taper([(122, 198), (126, 66)], 6, 4)))
    c.S.path(smooth(ell(124, 74, 16, 22, 12)), fill=c.gl('#E6F2EE'), fill_opacity=.85, stroke=LEAD, stroke_width=1.2)
    c.S.line([(126, 96), (150, 120), (168, 134)], '#E6F2EE', 1.2, smooth_=True)
    head = ell(184, 94, 22, 24, 22)
    nose = [(166, 100), (150, 108), (168, 108)]
    hair = []
    for k in range(11):
        a = math.pi + k * math.pi / 10
        base = (184 + 20 * math.cos(a), 92 + 22 * math.sin(a))
        tip = (184 + 40 * math.cos(a + .15), 90 + 44 * math.sin(a + .15))
        hair.append(P(taper([base, tip], 5, 1)))
    body = [(184, 116), (170, 120), (160, 134), (156, 150), (150, 200), (146, 210), (222, 210), (216, 196), (210, 150), (204, 132), (196, 120)]
    return dict(shapes=hair + [P(body), P(head), P(nose)], face=(186, 92, 9, 10, 9, 'round'), mouth=(186, 108, 14),
                anchors=((166, 130), (204, 130)), gift=g_spindle, front=lambda c: c.water(184), reach=1.1)


def ovinnik(c):
    c.bg(180, 70, 16, .15)
    c.disc(300, 38, 14)
    c.stars([(40, 20), (100, 46), (240, 16)])
    # овин
    c.sil(P([(20, 210), (20, 104), (10, 104), (66, 52), (122, 104), (112, 104), (112, 210)]))
    c.sil(P([(70, 60), (70, 40), (80, 40), (80, 70)]))
    # снопы
    for x, h in ((276, 64), (306, 70), (336, 60)):
        c.sil(P([(x - 14, 202), (x - 6, 202 - h * .5), (x - 12, 202 - h), (x, 202 - h * 1.08), (x + 12, 202 - h), (x + 6, 202 - h * .5),
                 (x + 14, 202)]), 1.6)
        c.S.line([(x - 7, 202 - h * .5), (x + 7, 202 - h * .5)], c.m['light'], 1.2, stroke_opacity=.45)
    # угли у ног
    c.S.glow(180, 196, 90, CORAL, .55)
    rnd = random.Random(8)
    for k in range(9):
        x = 110 + k * 18 + rnd.uniform(-4, 4)
        c.pane([(x - 7, 204), (x - 4, 194 - rnd.uniform(0, 4)), (x + 4, 193), (x + 8, 204)], ['#F08A6E', '#E0555F', '#FFC9A8'][k % 3], lw=1)
    # шерсть: зубчатый контур
    def fur(cx, cy, rx, ry, n, a0, a1, j):
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            r = 1 + (j if i % 2 else 0)
            pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
        return pts
    A = c.mood == 'angry'
    head = fur(180, 92, 34, 30, 28, 0, 2 * math.pi, .12)
    ears = [P([(152, 74), (144, 38 - 8 * A), (170, 62)]), P([(208, 74), (216, 38 - 8 * A), (190, 62)])]
    body = [(70, 210)] + fur(180, 170, 104 + 10 * A, 64, 22, math.pi, 2 * math.pi, .1) + [(290, 210)]
    return dict(shapes=[P(body)] + ears + [P(head)], face=(180, 92, 14, 15, 9, 'cat'), mouth=(180, 108, 16),
                anchors=((126, 140), (234, 140)), gift=g_ember, front=None)


CREATURES = {'leshy': leshy, 'domovoy': domovoy, 'bannik': bannik, 'vodyanoy': vodyanoy, 'poludnitsa': poludnitsa,
             'rusalka': rusalka, 'baba_yaga': baba_yaga, 'kikimora': kikimora, 'ovinnik': ovinnik}
EMBLEM_MOOD = {'leshy': 'neutral', 'domovoy': 'kind', 'bannik': 'angry', 'vodyanoy': 'neutral', 'poludnitsa': 'kind',
               'rusalka': 'cunning', 'baba_yaga': 'cunning', 'kikimora': 'cunning', 'ovinnik': 'angry'}
# эмблема: центр головы и масштаб
EMBLEM_FIT = {'leshy': (180, 82, .55), 'domovoy': (180, 100, .6), 'bannik': (180, 96, .6), 'vodyanoy': (180, 90, .55),
              'poludnitsa': (180, 84, .6), 'rusalka': (180, 96, .6), 'baba_yaga': (178, 92, .6), 'kikimora': (182, 100, .6),
              'ovinnik': (180, 100, .55)}


def figure(c, spec, tilt=True):
    S = c.S
    cun = c.mood == 'cunning' and tilt
    if cun:
        S.g(transform='rotate(-6 180 200)')
    if c.mood in ('kind', 'cunning', 'angry'):
        c.arms(*spec['anchors'], gift=spec.get('gift'), reach=spec.get('reach', 1.0))
    for d in spec['shapes']:
        c.sil(d)
    if spec.get('beard_line'):
        S.path(P(spec['beard_line']), fill='none', stroke=c.m['light'], stroke_width=1, stroke_opacity=.3)
    f = spec['face']
    c.eyes(f[0], f[1], f[2], f[3], f[4], f[5], f[6] if len(f) > 6 else 1.0)
    mx, my, mw = spec['mouth']
    c.mouth(mx, my, mw)
    if c.mood == 'kind' and spec.get('gift') is g_candle:
        pass
    if cun:
        S.end()


def spirit(cid, mood):
    c = C(mood)
    spec = CREATURES[cid](c)
    figure(c, spec)
    if spec.get('front'):
        spec['front'](c)
    c.frame()
    return c.S


def emblem(cid):
    mood = 'neutral'
    c = C(mood, 120, 120)
    S = c.S
    # фон медальона: клинья по кругу
    cols = MOODS[EMBLEM_MOOD[cid]]['panes']
    S.el('circle', cx=60, cy=60, r=57, fill=LEAD)
    n = 12
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n + .2, 2 * math.pi * (i + 1) / n + .2
        pts = [(60, 40)] + [(60 + 56 * math.cos(a0 + (a1 - a0) * t / 4), 60 + 56 * math.sin(a0 + (a1 - a0) * t / 4)) for t in range(5)]
        S.path(P(pts), fill=c.gl(cols[i % 4]), stroke=LEAD, stroke_width=1.1)
    light = MOODS[EMBLEM_MOOD[cid]]['light']
    S.glow(60, 40, 40, light, .5)
    c.m = dict(MOODS['neutral'])
    c.m['eye'] = MOODS[EMBLEM_MOOD[cid]]['eye'] if EMBLEM_MOOD[cid] != 'kind' else TURQ
    # фигура в масштабе (без фоновой сцены: рисуем спеку в отдельный холст и переносим только силуэт)
    tmp = C(mood)
    spec = CREATURES[cid](tmp)
    hx, hy, sc = EMBLEM_FIT[cid]
    S.g(transform=f'translate(60 {60 + 8}) scale({sc}) translate({-hx} {-hy})')
    for d in spec['shapes']:
        S.path(d, fill=BLK, stroke=LEAD, stroke_width=2.4 / sc * .6, stroke_linejoin='round')
    f = spec['face']
    c.eyes(f[0], f[1], f[2], f[3], f[4], f[5], f[6] if len(f) > 6 else 1.0)
    S.end()
    # углы вне круга — свинец, кольцо
    sq = 'M-1,-1 121,-1 121,121 -1,121Z'
    S.path(sq + P(ell(60, 60, 56, 56, 48)), fill=LEAD, fill_rule='evenodd')
    S.el('circle', cx=60, cy=60, r=56, fill='none', stroke=LEAD, stroke_width=4)
    S.el('circle', cx=60, cy=60, r=53.5, fill='none', stroke=lt(light, .1), stroke_width=1, stroke_opacity=.6)
    return S


def render_app(S):
    svg = S.render()
    return svg.replace(f' width="{S.w}" height="{S.h}"', '')


def sheet(path, files):
    from playwright.sync_api import sync_playwright
    import base64
    rows = ''
    for cid in CREATURES:
        cells = ''.join(f'<img class=s src="data:image/svg+xml;base64,{base64.b64encode(open(f"{SPIRITS}/{cid}_{m}.svg", "rb").read()).decode()}">'
                        for m in MOOD_ORDER)
        em = base64.b64encode(open(f'{EMBLEMS}/{cid}.svg', 'rb').read()).decode()
        rows += f'<div class=r><div class=n>{cid}</div>{cells}<img class=e src="data:image/svg+xml;base64,{em}"></div>'
    head = ''.join(f'<div class=h>{m}</div>' for m in MOOD_ORDER)
    html = f'''<html><head><meta charset="utf-8"><style>body{{margin:0;background:#0E1621;color:#E9DFC8;font:700 15px 'PT Serif',Georgia,serif;padding:12px}}
.r{{display:flex;gap:8px;align-items:center;margin-bottom:8px}}.n{{width:96px}}.s{{width:288px;height:160px;border-radius:6px}}.e{{width:120px;height:120px}}
.hd{{display:flex;gap:8px;margin:0 0 6px 104px}}.h{{width:288px;color:#3FD6CC;font:700 13px sans-serif;letter-spacing:.12em;text-transform:uppercase}}</style></head>
<body><div class=hd>{head}<div class=h style="width:120px">эмблема</div></div>{rows}</body></html>'''
    tmp = path + '.html'
    open(tmp, 'w').write(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1430, 'height': 800})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(500)
        pg.screenshot(path=path, full_page=True)
        b.close()
    os.remove(tmp)


def main():
    args = sys.argv[1:]
    sheet_path = None
    if '--sheet' in args:
        i = args.index('--sheet')
        sheet_path = args[i + 1]
        del args[i:i + 2]
    only = set(args)
    import xml.etree.ElementTree as ET
    allowed = {'svg', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'g', 'linearGradient', 'radialGradient', 'stop', 'defs'}
    sizes = []
    for cid in CREATURES:
        if only and cid not in only:
            continue
        outs = [(f'{SPIRITS}/{cid}_{m}.svg', spirit(cid, m)) for m in MOOD_ORDER] + [(f'{EMBLEMS}/{cid}.svg', emblem(cid))]
        for path, S in outs:
            svg = render_app(S)
            root = ET.fromstring(svg)
            bad = {e.tag.split('}')[1] for e in root.iter()} - allowed
            assert not bad, (path, bad)
            assert len(svg.encode()) <= MAX, (path, len(svg.encode()))
            open(path, 'w').write(svg)
            sizes.append((os.path.basename(path), len(svg.encode())))
    print(' '.join(f'{n}:{b // 1024}K' for n, b in sizes))
    if sheet_path:
        sheet(sheet_path, None)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Иконки «Путника» в витражном стиле («фреска из стекла»), v5.3.

python3 tools/art/items_glass.py [--sheet /tmp/items_sheet.png] [--big]

Пишет app/assets/art/items/*.svg (предметы и показатели, 96x96),
app/assets/art/zones/*.svg (зоны, 64x64) и tools/art/items_glass_manifest.md.
Каждая иконка: свинцовый кабошон (#070B10), стеклянный фон с подсветкой
сзади, 4-9 крупных осколков со свинцовой пайкой и градиентом «стекло
просвечивает», тонкие блики. Только path/rect/circle/ellipse/polygon/polyline/g/
linearGradient/radialGradient/stop/defs (flutter_svg), viewBox обязателен.
Зависит только от artlib.py (Doc, f, pts, clip_circle, clip_convex, sparkle).
"""
import base64
import math
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from artlib import Doc, f, pts, clip_circle, clip_convex, sparkle, sample  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ITEMS_DIR = os.path.join(ROOT, 'app', 'assets', 'art', 'items')
ZONES_DIR = os.path.join(ROOT, 'app', 'assets', 'art', 'zones')
MANIFEST = os.path.join(ROOT, 'tools', 'art', 'items_glass_manifest.md')

LEAD = '#070B10'
MAX_BYTES = 6 * 1024
ALLOWED = {'svg', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'g',
           'linearGradient', 'radialGradient', 'stop', 'defs'}

# ---- стекло: (основной тон, светлый край) ---------------------------------
FAM = {
    'turq':   ('#2BC4BA', '#8DF1E9'),
    'blue':   ('#1B4F8C', '#4E93DA'),
    'ultra':  ('#2B3E9E', '#6F86EC'),
    'emer':   ('#1F9E6B', '#6BE0A9'),
    'emerD':  ('#136A47', '#33B282'),
    'viol':   ('#5B3FA0', '#A98CEC'),
    'ruby':   ('#C8454F', '#F78F97'),
    'rubyD':  ('#8C2A3C', '#D25B6D'),
    'amber':  ('#F0A24A', '#FFD79B'),
    'milk':   ('#EDE6D2', '#FFFBF0'),
    'night':  ('#0B1424', '#2A4068'),
    'steel':  ('#7F97AD', '#D6E5F1'),
    'steelD': ('#4B6580', '#9AB5CE'),
    'umber':  ('#7A3F24', '#C07846'),
    'umberD': ('#512717', '#8A4A2B'),
    'toast':  ('#C98A4E', '#F2C08A'),
    'copper': ('#B5622E', '#F0A065'),
    'coral':  ('#E07A5F', '#FBB6A2'),
    'sky':    ('#5BB5E8', '#B0E1FB'),
    'rose':   ('#E0556B', '#FB9AAA'),
    'ice':    ('#9AD7F2', '#E8F8FF'),
}

# ---- стеклянный фон: (центр подсветки, середина, край) -----------------------
BG = {
    'teal':    ('#33B3B0', '#15626E', '#06202B'),
    'blue':    ('#4284CF', '#1C4284', '#08153A'),
    'indigo':  ('#5362D0', '#27337F', '#0A0E36'),
    'violet':  ('#8466D0', '#432C86', '#150E36'),
    'emerald': ('#3CBA88', '#17664A', '#05271D'),
    'ruby':    ('#CC5F78', '#722441', '#260A1B'),
    'wine':    ('#C9604E', '#6A2A2E', '#240D12'),
    'sea':     ('#4FB9EE', '#1B5E94', '#07203F'),
    'slate':   ('#5C8399', '#274256', '#0A1823'),
    'turqz':   ('#3FDACE', '#17959C', '#094A58'),
}


# ---- геометрия -------------------------------------------------------------

def rot(ps, a, c=(48, 48)):
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in ps]


def xf(ps, a=0.0, sc=1.0, c=(48, 48), d=(0, 0)):
    """Поворот на a градусов, масштаб sc вокруг c, сдвиг d."""
    r = rot(ps, a, c)
    return [(c[0] + (x - c[0]) * sc + d[0], c[1] + (y - c[1]) * sc + d[1]) for x, y in r]


def mv(ps, dx, dy):
    return [(x + dx, y + dy) for x, y in ps]


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def bar(p0, p1, w0, w1=None):
    w1 = w0 if w1 is None else w1
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    return [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
            (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]


def lens(p0, p1, w, n=6):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        ww = w / 2 * math.sin(math.pi * t) ** 0.85
        cx, cy = p0[0] + dx * t, p0[1] + dy * t
        top.append((cx + nx * ww, cy + ny * ww))
        bot.append((cx - nx * ww, cy - ny * ww))
    return top + bot[n - 1:0:-1]


def ellp(cx, cy, rx, ry, n=28, a0=0.0, a1=360.0):
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    if abs(a1 - a0) >= 360:
        out.pop()
    return out


def ring_seg(cx, cy, r0, r1, a0, a1, n=8):
    outer = ellp(cx, cy, r1, r1, n, a0, a1)
    inner = ellp(cx, cy, r0, r0, n, a1, a0)
    return outer + inner


def teardrop(cx, cy, hh, w, m=1.35, n=30):
    """Капля: центр (cx, cy), полувысота hh, множитель ширины w. Остриё сверху."""
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = math.sin(t) * (math.sin(t / 2) ** m)
        y = math.cos(t)
        out.append((cx + w * x, cy - hh * y))
    return out


def cr_closed(p, t=1 / 6):
    n = len(p)
    d = f'M{f(p[0][0])},{f(p[0][1])}'
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) * t, p1[1] + (p2[1] - p0[1]) * t)
        c2 = (p2[0] - (p3[0] - p1[0]) * t, p2[1] - (p3[1] - p1[1]) * t)
        d += f'C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d + 'Z'


def _clip_seg(x0, y0, x1, y1, cx=48.0, cy=48.0, r=41.0):
    """Отрезок ∩ круг (параметрически); None, если снаружи."""
    dx, dy = x1 - x0, y1 - y0
    fx, fy = x0 - cx, y0 - cy
    a = dx * dx + dy * dy
    if a == 0:
        return None
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc <= 0:
        return None
    sq = math.sqrt(disc)
    t0, t1 = max(0.0, (-b - sq) / (2 * a)), min(1.0, (-b + sq) / (2 * a))
    if t0 >= t1:
        return None
    return (x0 + dx * t0, y0 + dy * t0, x0 + dx * t1, y0 + dy * t1)


def clipE(poly, cx, cy, rx, ry, n=44):
    return clip_convex(poly, ellp(cx, cy, rx, ry, n))


# ---- кабошон ----------------------------------------------------------------

class G:
    """Один витраж. Рисуем в 96-пространстве, на выходе масштабируем в size."""

    def __init__(self, name, size=96, bg='teal', seed=1, glow=None, hub=15, wcols=None,
                 lead=1.6, nwedge=6):
        self.name, self.size, self.bgk, self.seed = name, size, bg, seed
        self.k = size / 96.0
        self.doc = Doc(f'0 0 {size} {size}', 'g')
        self.lw = max(1.15, lead * self.k)
        self.hub, self.nwedge = hub, nwedge
        self.wcols = wcols
        self.glows = []
        self.shards = []
        self.hls = []
        self.tops = []   # поверх бликов: искры
        self.nbig = 0
        self.nsmall = 0
        if glow:
            self.add_glow(*glow)

    # -- масштабирование
    def sc(self, ps):
        return [(x * self.k, y * self.k) for x, y in ps]

    def _grab(self, lst, fn, *a, **kw):
        n = len(self.doc.body)
        fn(*a, **kw)
        lst.extend(self.doc.body[n:])
        del self.doc.body[n:]

    # -- краска осколка
    def paint(self, fam, st):
        base, light = FAM[fam]
        d = self.doc
        if st == 'r':
            return d.rad([(0, base), (1, light)], 0.5, 0.5, 0.78)
        if st == 'd':
            return d.lin([(0, light), (1, base)], 0, 0, 1, 1)
        if st == 'D':
            return d.lin([(0, base), (1, light)], 0, 0, 1, 1)
        if st == 'v':
            return d.lin([(0, light), (1, base)], 0, 0, 0, 1)
        if st == 'V':
            return d.lin([(0, base), (1, light)], 0, 0, 0, 1)
        if st == 'h':
            return d.lin([(0, light), (1, base)], 0, 0, 1, 0)
        if st == 'H':
            return d.lin([(0, base), (1, light)], 0, 0, 1, 0)
        raise ValueError(st)

    # -- осколки
    def _count(self, w, h):
        if w * h >= 90:
            self.nbig += 1
        else:
            self.nsmall += 1

    def p(self, points, fam, st='r', clip=False, **kw):
        if clip:
            points = clip_circle(points, 48, 48, 41.2, 40)
            if len(points) < 3:
                return
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        self._count(max(xs) - min(xs), max(ys) - min(ys))
        self._grab(self.shards, self.doc.poly, self.sc(points), fill=self.paint(fam, st), **kw)

    def s(self, points, fam, st='r', clip=False, **kw):
        """Гладкий замкнутый осколок (Catmull-Rom); clip — обрезать по кабошону."""
        if clip:
            self.p(sample(points + [points[0]], 6)[:-1], fam, st, clip=True, **kw)
            return
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        self._count(max(xs) - min(xs), max(ys) - min(ys))
        self._grab(self.shards, self.doc.path, cr_closed(self.sc(points)), fill=self.paint(fam, st), **kw)

    def c(self, cx, cy, r, fam, st='r', **kw):
        self._count(2 * r, 2 * r)
        self._grab(self.shards, self.doc.circle, cx * self.k, cy * self.k, r * self.k, fill=self.paint(fam, st), **kw)

    def e(self, cx, cy, rx, ry, fam, st='r', **kw):
        self._count(2 * rx, 2 * ry)
        self._grab(self.shards, self.doc.ellipse, cx * self.k, cy * self.k, rx * self.k, ry * self.k,
                   fill=self.paint(fam, st), **kw)

    # -- свинцовая нить (линия со свинцовой обводкой и стеклянной серединкой)
    def thread(self, points, fam, w=2.6, smooth=False):
        base = FAM[fam][0]
        if smooth:
            points = sample(points, 6)
        self._grab(self.shards, self.doc.line, self.sc(points), stroke=LEAD,
                   stroke_width=(w + 2 * self.lw) * self.k, stroke_linecap='round',
                   stroke_linejoin='round')
        self._grab(self.shards, self.doc.line, self.sc(points), stroke=base,
                   stroke_width=w * self.k, stroke_linecap='round', stroke_linejoin='round')

    # -- блики и подсветка
    def hl(self, points, w=1.15, op=0.6, col='#FFFFFF'):
        self._grab(self.hls, self.doc.line, self.sc(points), stroke=col, stroke_width=max(0.8, w * self.k),
                   opacity=op, stroke_linecap='round', stroke_linejoin='round')

    def lines(self, segs, w=1.15, op=0.6, col='#FFFFFF'):
        """Несколько отрезков одним path (экономит байты)."""
        segs = [q for q in (_clip_seg(*sg) for sg in segs) if q]
        d = ''.join(f'M{f(a * self.k)},{f(b * self.k)}L{f(c * self.k)},{f(e * self.k)}' for a, b, c, e in segs)
        self._grab(self.hls, self.doc.path, d, fill='none', stroke=col, stroke_width=max(0.8, w * self.k),
                   opacity=op, stroke_linecap='round')

    def dot(self, cx, cy, r, col='#FFFFFF', op=0.8):
        self._grab(self.hls, self.doc.circle, cx * self.k, cy * self.k, r * self.k, fill=col, opacity=op)

    def spark(self, x, y, r, op=0.9, col='#FFFFFF'):
        self._grab(self.tops, sparkle, self.doc, x * self.k, y * self.k, r * self.k, fill=col, opacity=op)

    def add_glow(self, cx, cy, r, col, op=0.6):
        gr = self.doc.rad([(0, col, op), (0.5, col, op * 0.4), (1, col, 0)])
        self._grab(self.glows, self.doc.circle, cx * self.k, cy * self.k, r * self.k, fill=gr)

    def raw(self, svg):
        self.hls.append(svg)

    # -- сборка
    def render(self):
        d, k = self.doc, self.k
        body = []
        c = self.size / 2
        # свинцовый кабошон
        self._grab(body, d.circle, c, c, 47.6 * k, fill=LEAD)
        c1, c2, c3 = BG[self.bgk]
        bg = d.rad([(0, c1), (0.55, c2), (1, c3)], 0.5, 0.46, 0.62)
        self._grab(body, d.circle, c, c, 43.4 * k, fill=bg)
        # клинья фона (стёкла вокруг предмета)
        rnd = random.Random(self.seed * 7919 + 3)
        n = self.nwedge
        base = rnd.uniform(0, 360 / n)
        angs = [base + i * 360 / n + rnd.uniform(-11, 11) for i in range(n)]
        tint = self.wcols or (('#000000', 0.24), ('#FFFFFF', 0.07))
        hub = self.hub

        def at(a, r):
            return (48 + r * math.cos(math.radians(a)), 48 + r * math.sin(math.radians(a)))

        R_ = 43.4
        for i in range(n):
            a, b = angs[i], angs[(i + 1) % n] + (360 if i == n - 1 else 0)
            ha, hb, ra, rb = at(a, hub), at(b, hub), at(a, R_), at(b, R_)
            dd = (f'M{f(ha[0] * k)},{f(ha[1] * k)}L{f(ra[0] * k)},{f(ra[1] * k)}'
                  f'A{f(R_ * k)},{f(R_ * k)} 0 0 1 {f(rb[0] * k)},{f(rb[1] * k)}L{f(hb[0] * k)},{f(hb[1] * k)}Z')
            col, op = tint[i % 2]
            self._grab(body, d.path, dd, fill=col, opacity=op, stroke=LEAD,
                       stroke_width=self.lw * 0.75, stroke_linejoin='round')
        body += self.glows
        # предмет
        body.append(f'<g stroke="{LEAD}" stroke-width="{f(self.lw)}" stroke-linejoin="round">')
        body += self.shards
        body.append('</g>')
        body += self.hls
        # общий блик купола + ободок
        sh = d.rad([(0, '#FFFFFF', 0.20), (1, '#FFFFFF', 0)])
        self._grab(body, d.circle, 35 * k, 31 * k, 21 * k, fill=sh)
        body += self.tops
        self._grab(body, d.circle, c, c, 45.5 * k, fill='none', stroke=LEAD, stroke_width=4.4 * k)
        a0, a1 = math.radians(196), math.radians(262)
        r = 40.6
        x0, y0 = 48 + r * math.cos(a0), 48 + r * math.sin(a0)
        x1, y1 = 48 + r * math.cos(a1), 48 + r * math.sin(a1)
        self._grab(body, d.path, f'M{f(x0 * k)},{f(y0 * k)}A{f(r * k)},{f(r * k)} 0 0 1 {f(x1 * k)},{f(y1 * k)}',
                   fill='none', stroke='#FFFFFF', stroke_width=max(0.9, 1.1 * k), opacity=0.32,
                   stroke_linecap='round')
        d.body = body
        return d.render()


# =============================================================================
# ПРЕДМЕТЫ: еда и питьё
# =============================================================================

def bread(g):
    X = lambda ps: xf(ps, 0, 0.92, (48, 52), (0, 0))
    # купол из трёх стёкол, низ-подпуск отдельным стеклом
    g.p(X([(8, 63), (9, 54), (13, 45), (20, 37), (30, 31), (33, 62), (24, 64)]), 'umber', 'd')
    g.p(X([(30, 31), (40, 28), (56, 28), (66, 31), (63, 62), (48, 66), (33, 62)]), 'copper', 'D')
    g.p(X([(66, 31), (76, 37), (83, 45), (87, 54), (88, 63), (72, 64), (63, 62)]), 'umberD', 'r')
    g.p(X([(8, 63), (24, 64), (33, 62), (48, 66), (63, 62), (72, 64), (88, 63), (87, 72), (80, 77), (48, 79), (16, 77), (9, 72)]), 'umber', 'v')
    # три надреза молочным стеклом, все в одну сторону
    g.p(X(lens((37, 56), (45, 37), 6.4)), 'milk', 'r')
    g.p(X(lens((47, 57), (55, 38), 6.4)), 'milk', 'r')
    g.p(X(lens((57, 56), (65, 38), 6.4)), 'milk', 'r')
    g.hl(X([(11, 54), (15, 45), (22, 38), (31, 33)]), op=0.55)
    g.hl(X([(68, 70), (78, 71)]), op=0.35, w=1.0)
    g.spark(76, 26, 3.6)


def stew(g):
    cx = 48
    # верхняя полоса, нижняя полоса, этикетка
    g.p([(26, 34), (70, 34), (70, 44), (62, 46), (48, 47), (34, 46), (26, 44)], 'steel', 'v')
    g.p([(26, 64), (34, 66), (48, 67), (62, 66), (70, 64), (70, 72), (62, 76), (48, 78), (34, 76), (26, 72)], 'steelD', 'v')
    g.p([(26, 44), (34, 46), (47, 47), (47, 67), (34, 66), (26, 64)], 'ruby', 'h')
    g.p([(47, 47), (62, 46), (70, 44), (70, 64), (62, 66), (47, 67)], 'rubyD', 'H')
    # крышка (эллипс)
    g.e(cx, 34, 22, 7, 'steel', 'r')
    g.e(cx, 34, 12, 3.4, 'steelD', 'D')
    # эмблема на этикетке
    g.c(47, 56.5, 6.4, 'milk', 'r')
    g.p([(47, 52.4), (48.6, 55.5), (51.8, 55.7), (49.4, 57.8), (50.2, 61), (47, 59.2), (43.8, 61), (44.6, 57.8), (42.2, 55.7), (45.4, 55.5)], 'amber', 'r', stroke_width=0.9)
    g.hl([(29, 38), (29, 60)], op=0.5)
    g.hl([(36, 32), (46, 30)], op=0.55, w=1.0)
    g.spark(74, 24, 3.4)


def water(g):
    # крышка, горлышко, плечи, воздух, вода
    g.p([(42, 11), (54, 11), (55, 20), (41, 20)], 'turq', 'v')
    g.p([(43, 20), (53, 20), (53, 29), (43, 29)], 'ice', 'v')
    g.p([(43, 29), (53, 29), (60, 32), (66, 40), (67, 48), (29, 48), (30, 40), (36, 32)], 'ice', 'd')
    g.p([(29, 48), (67, 48), (67, 57), (58, 54), (48, 58), (38, 54), (29, 57)], 'sky', 'V')
    g.p([(29, 57), (38, 54), (48, 58), (48, 80), (33, 80), (29, 75)], 'sky', 'D')
    g.p([(48, 58), (58, 54), (67, 57), (67, 75), (63, 80), (48, 80)], 'blue', 'D')
    g.c(40, 66, 2.8, 'milk', 'r', stroke_width=0.9)
    g.c(57, 70, 2.2, 'milk', 'r', stroke_width=0.9)
    g.hl([(33, 40), (33, 50)], op=0.7)
    g.hl([(33, 66), (33, 73)], op=0.5)
    g.hl([(45, 22), (45, 27)], op=0.7, w=1.0)
    g.spark(72, 30, 3.6)


def tea(g):
    X = lambda ps: xf(ps, 0, 0.9, (48, 50), (-1, 3))
    # крышка-чашка
    g.p(X([(30, 18), (48, 17), (48, 30), (31, 30)]), 'rose', 'h')
    g.p(X([(48, 17), (66, 18), (65, 30), (48, 30)]), 'rubyD', 'H')
    g.p(X([(31, 30), (65, 30), (63, 35), (33, 35)]), 'steel', 'v')
    # корпус: верх, полоса, низ
    g.p(X([(33, 35), (63, 35), (63, 54), (33, 54)]), 'ultra', 'h')
    g.p(X([(33, 54), (63, 54), (63, 61), (33, 61)]), 'milk', 'v')
    g.p(X([(33, 61), (63, 61), (63, 76), (60, 80), (36, 80), (33, 76)]), 'blue', 'd')
    # ручка-ремешок
    g.thread(X([(63, 41), (73, 44), (73, 60), (63, 64)]), 'umber', 4.0)
    # янтарный огонёк — «горячее»
    g.p(X([(48, 52), (52.5, 57.5), (48, 63), (43.5, 57.5)]), 'amber', 'r', stroke_width=0.9)
    # пар
    g.p(X(lens((43, 14), (40, 6), 4.6, 4)), 'milk', 'r')
    g.p(X(lens((53, 14), (56, 5), 4.6, 4)), 'milk', 'r')
    g.hl(X([(36, 39), (36, 51)]), op=0.55)
    g.hl(X([(36, 66), (36, 75)]), op=0.45)
    g.spark(74, 28, 3.2)


def chocolate(g):
    cols = [['umberD', 'umber', 'umberD'], ['umber', 'umberD', 'umber']]
    sts = ['d', 'r', 'D']
    cs, gap = 19, 2.2
    x0, y0 = 48 - 1.5 * cs - gap, 30
    rows = []
    for r in range(2):
        for c in range(3):
            x = x0 + c * (cs + gap)
            y = y0 + r * (cs + gap)
            rows.append(([(x, y), (x + cs, y), (x + cs, y + cs), (x, y + cs)], cols[r][c], sts[(r + c) % 3]))
    a = -18
    for poly, fam, st in rows:
        g.p(rot(poly, a, (48, 52)), fam, st)
    # фольга — зигзагом по нижней трети
    yf = y0 + 2 * (cs + gap) - 5
    foil = [(x0 - 3, yf + 6), (x0 + 8, yf), (x0 + 19, yf + 6), (x0 + 30, yf), (x0 + 41, yf + 6), (x0 + 52, yf),
            (x0 + 63, yf + 6), (x0 + 63, yf + 36), (x0 - 3, yf + 36)]
    g.p(rot(foil, a, (48, 52)), 'turq', 'd', clip=True)
    for r in range(2):
        for c in range(3):
            x = x0 + c * (cs + gap)
            y = y0 + r * (cs + gap)
            g.hl(rot([(x + 3, y + cs - 3), (x + 3, y + 3), (x + cs - 3, y + 3)], a, (48, 52)), w=0.9, op=0.38)
    g.hl(rot([(x0 + 6, yf + 14), (x0 + 28, yf + 12)], a, (48, 52)), op=0.6)
    g.spark(76, 26, 3.4)


def berries(g):
    # листья и черенок
    g.p(lens((47, 28), (30, 17), 11), 'emer', 'd')
    g.p(lens((49, 28), (67, 17), 11), 'emerD', 'D')
    g.p(bar((48, 36), (48, 25), 3.4), 'umberD', 'r')
    # ягоды
    g.c(34, 57, 14, 'ruby', 'r')
    g.c(62, 55, 14.5, 'ultra', 'r')
    g.c(48, 40, 12.5, 'rubyD', 'r')
    for (x, y, r) in [(34, 57, 14), (62, 55, 14.5), (48, 40, 12.5)]:
        g.hl([(x - r * 0.62, y - r * 0.15), (x - r * 0.35, y - r * 0.6), (x + r * 0.05, y - r * 0.72)], op=0.65, w=1.3)
    # чашелистики
    g.p([(34, 49), (31, 53), (34, 52), (37, 53)], 'emer', 'r', stroke_width=0.8)
    g.p([(62, 46.5), (59, 51), (62, 50), (65, 51)], 'emer', 'r', stroke_width=0.8)
    g.p([(48, 33.5), (45.6, 37), (48, 36), (50.4, 37)], 'emer', 'r', stroke_width=0.8)
    g.spark(77, 34, 3.4)


def fish(g):
    R = lambda ps: xf(ps, -14, 0.87, (48, 50), (-2, 1))
    g.p(R([(74, 49), (86, 33), (91, 42), (85, 50), (91, 58), (86, 67), (74, 52)]), 'umber', 'd')
    g.p(R([(38, 33), (50, 21), (63, 30), (60, 35)]), 'copper', 'v')
    g.p(R([(44, 66), (50, 77), (59, 68)]), 'umberD', 'r')
    g.p(R([(10, 50), (14, 44), (22, 38), (28, 35.5), (28, 62.5), (22, 60), (14, 56)]), 'copper', 'D')
    g.p(R([(28, 35.5), (34, 33), (48, 31), (52, 31.8), (52, 66.3), (48, 67), (34, 65), (28, 62.5)]), 'toast', 'v')
    g.p(R([(52, 31.8), (60, 34), (70, 40), (76, 47), (78, 50), (76, 53), (70, 60), (60, 65), (52, 66.3)]), 'umber', 'd')
    ex, ey = R([(19, 47.5)])[0]
    g.c(ex, ey, 3.2, 'milk', 'r', stroke_width=1.0)
    g.dot(ex, ey, 1.3, col='#0B1424', op=1)
    g.hl(R([(32, 40), (44, 37), (50, 37)]), op=0.6)
    g.hl(R([(56, 42), (68, 44)]), op=0.45, w=1.0)
    g.hl(R([(34, 60), (46, 62)]), op=0.35, w=1.0)
    g.spark(76, 24, 3.2)


def pie(g):
    cx, cy, rx, ry = 48, 44, 35, 18.5
    side_l = ellp(cx, cy, rx, ry, 10, 90, 180) + mv(ellp(cx, cy, rx, ry, 10, 180, 90), 0, 17)
    side_r = ellp(cx, cy, rx, ry, 10, 0, 90) + mv(ellp(cx, cy, rx, ry, 10, 90, 0), 0, 17)
    g.p(side_l, 'umber', 'h')
    g.p(side_r, 'umberD', 'H')
    g.e(cx, cy, rx, ry, 'toast', 'r')
    g.e(cx, cy, 25, 12.5, 'ruby', 'r')
    # решётка из теста
    for off in (-10, 10):
        s1 = bar((cx + off - 18, cy + 18), (cx + off + 18, cy - 18), 4.6)
        s2 = bar((cx + off - 18, cy - 18), (cx + off + 18, cy + 18), 4.6)
        for s in (s1, s2):
            q = clipE(s, cx, cy, 25.5, 13)
            if len(q) >= 3:
                g.p(q, 'toast', 'd')
    # цветок-пар на тесте и листик
    g.p(lens((70, 30), (80, 21), 7), 'emer', 'd')
    g.hl([(20, 42), (26, 34), (38, 29)], op=0.6)
    g.hl([(16, 52), (16, 58)], op=0.4)
    g.spark(22, 26, 3.4)


def kvass(g):
    g.p([(44, 11), (52, 11), (53, 20), (43, 20)], 'ruby', 'v')
    g.p([(43, 20), (53, 20), (53, 32), (62, 36), (68, 46), (68, 52), (28, 52), (28, 46), (34, 36), (43, 32)], 'umber', 'd')
    g.p([(28, 52), (68, 52), (68, 78), (62, 83), (34, 83), (28, 78)], 'umberD', 'r')
    # этикетка и колосок ржи
    g.p([(28, 54), (68, 54), (68, 70), (28, 70)], 'milk', 'v')
    g.p(lens((48, 68), (48, 56), 3.2, 4), 'emer', 'r', stroke_width=0.9)
    g.p(lens((48, 62), (42, 55.5), 3.6, 4), 'emerD', 'r', stroke_width=0.9)
    g.p(lens((48, 62), (54, 55.5), 3.6, 4), 'emerD', 'r', stroke_width=0.9)
    g.hl([(31, 44), (33, 38), (38, 34)], op=0.6)
    g.hl([(46, 24), (46, 30)], op=0.5, w=1.0)
    g.hl([(31, 74), (31, 79)], op=0.4)
    g.hl([(60, 40), (65, 47)], op=0.35, w=1.0)
    g.spark(72, 28, 3.4)


def gas(g):
    g.p([(42, 20), (54, 20), (54, 30), (42, 30)], 'steelD', 'h')
    g.p([(36, 30), (60, 30), (60, 36), (36, 36)], 'turq', 'v')
    g.p([(32, 36), (64, 36), (68, 44), (68, 48), (28, 48), (28, 44)], 'steel', 'v')
    g.p([(28, 48), (48, 48), (48, 70), (48, 80), (33, 80), (28, 76)], 'blue', 'h')
    g.p([(48, 48), (68, 48), (68, 76), (63, 80), (48, 80)], 'ultra', 'H')
    g.p([(28, 70), (68, 70), (68, 76), (63, 80), (33, 80), (28, 76)], 'steelD', 'v')
    # вентиль
    g.p([(36, 15), (60, 15), (60, 20), (36, 20)], 'turq', 'v')
    # язычок пламени на баллоне
    g.p([(48, 52), (54, 62), (52, 68), (44, 68), (42, 62)], 'ruby', 'r', stroke_width=1.0)
    g.p([(48, 58), (51, 64), (50, 67), (46, 67), (45, 64)], 'amber', 'r', stroke_width=0.8)
    g.hl([(31, 51), (31, 66)], op=0.55)
    g.hl([(33, 41), (40, 38)], op=0.55, w=1.0)
    g.spark(72, 30, 3.4)


def matches(g):
    R = lambda ps: xf(ps, -12, 0.82, (48, 62), (0, -1))
    # спички (за коробком)
    g.p(R(bar((32, 63), (30, 26), 5.6)), 'toast', 'h')
    g.p(R(bar((48, 63), (48, 22), 5.6)), 'toast', 'h')
    g.p(R(bar((64, 63), (68, 28), 5.6)), 'toast', 'h')
    for (hx, hy, fam) in [(30, 24, 'ruby'), (48, 20, 'rubyD'), (68, 26, 'ruby')]:
        x, y = R([(hx, hy)])[0]
        g.c(x, y, 4.4, fam, 'r')
    # коробок
    g.p(R([(21, 62), (75, 62), (75, 82), (21, 82)]), 'viol', 'd')
    g.p(R([(21, 62), (75, 62), (75, 68), (21, 68)]), 'steelD', 'v')
    g.p(R([(30, 72), (66, 72), (66, 79), (30, 79)]), 'milk', 'v')
    # огонёк на средней спичке
    fx, fy = R([(48, 12)])[0]
    g.s([(fx, fy - 9), (fx + 5.2, fy - 1.5), (fx + 3.4, fy + 3.4), (fx - 3.4, fy + 3.4), (fx - 5.2, fy - 1.5)], 'amber', 'r')
    g.s([(fx, fy - 3.5), (fx + 2.4, fy), (fx + 1.6, fy + 2.4), (fx - 1.6, fy + 2.4), (fx - 2.4, fy)], 'ruby', 'r', stroke_width=0.8)
    g.hl(R([(24, 65), (72, 65)]), op=0.4, w=1.0)
    g.hl(R([(25, 74), (25, 80)]), op=0.5)
    g.spark(18, 42, 3.2)
    g.glows.clear()
    g.add_glow(fx, fy - 2, 20, FAM['amber'][0], 0.55)


# =============================================================================
# СНАРЯЖЕНИЕ
# =============================================================================

def socks(g):
    R = lambda ps: xf(ps, 6, 0.93, (48, 48), (-2, 1))
    g.p(R([(32, 11), (56, 11), (56, 24), (32, 24)]), 'ruby', 'h')
    g.p(R([(32, 24), (56, 24), (56, 31), (32, 31)]), 'milk', 'v')
    g.p(R([(32, 31), (56, 31), (56, 52), (44, 53), (32, 54)]), 'blue', 'd')
    g.p(R([(32, 54), (44, 53), (47, 66), (42, 80), (34, 79), (28, 72), (28, 60)]), 'turq', 'D')
    g.p(R([(44, 53), (56, 52), (64, 56), (72, 57), (72, 80), (42, 80), (47, 66)]), 'ultra', 'd')
    g.p(R([(72, 57), (79, 61), (83, 69), (80, 77), (72, 80)]), 'ruby', 'D')
    # вязаный узор
    g.hl(R([(36, 36), (41, 41), (36, 46), (41, 51)]), op=0.5, w=1.1)
    g.hl(R([(46, 36), (51, 41), (46, 46)]), op=0.5, w=1.1)
    g.hl(R([(50, 64), (55, 69), (50, 74), (55, 78), (61, 73), (66, 78)]), op=0.45, w=1.0)
    g.hl(R([(35, 15), (53, 15)]), op=0.5, w=1.0)
    g.spark(76, 26, 3.4)


def raincoat(g):
    X = lambda ps: xf(ps, 0, 0.9, (48, 50), (0, 2))
    # капюшон
    g.p(X([(48, 9), (40, 12), (35, 22), (35, 31), (48, 31)]), 'viol', 'd')
    g.p(X([(48, 9), (56, 12), (61, 22), (61, 31), (48, 31)]), 'ultra', 'D')
    g.p(X([(41, 31), (43, 21), (48, 18), (53, 21), (55, 31)]), 'night', 'v')
    # рукава
    g.p(X([(35, 31), (28, 34), (16, 64), (25, 68), (37, 46)]), 'blue', 'd')
    g.p(X([(61, 31), (68, 34), (80, 64), (71, 68), (59, 46)]), 'blue', 'D')
    # корпус
    g.p(X([(35, 31), (48, 31), (48, 72), (28, 72), (33, 52)]), 'turq', 'd')
    g.p(X([(48, 31), (61, 31), (63, 52), (68, 72), (48, 72)]), 'emer', 'D')
    # подол
    g.p(X([(28, 72), (68, 72), (71, 81), (25, 81)]), 'ultra', 'v')
    for yy in (44, 56):
        bx, by = X([(44.4, yy)])[0]
        g.c(bx, by, 1.7, 'milk', 'r', stroke_width=0.8)
    # капли дождя
    for (x, y, sc) in [(15, 30, 1.0), (82, 34, 0.9), (12, 54, 0.75)]:
        g.p([(x, y - 7 * sc), (x + 4.4 * sc, y + 1.5 * sc), (x, y + 5 * sc), (x - 4.4 * sc, y + 1.5 * sc)], 'sky', 'r', stroke_width=1.0)
    g.hl(X([(38, 20), (41, 14)]), op=0.6)
    g.hl(X([(21, 60), (28, 42)]), op=0.5)
    g.spark(66, 14, 3.2)


def trekking_poles(g):
    Xp = lambda q: xf([q], 0, 0.88, (48, 50), (0, 1))[0]
    def pole(p0, p1, grip_fam, shaft_a, shaft_b, ring):
        p0, p1 = Xp(p0), Xp(p1)
        n = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        u = ((p1[0] - p0[0]) / n, (p1[1] - p0[1]) / n)
        P = lambda t: (p0[0] + u[0] * n * t, p0[1] + u[1] * n * t)
        g.p(bar(P(0.0), P(0.22), 9, 8), grip_fam, 'r')
        g.p(bar(P(0.22), P(0.62), 4.4, 4.2), shaft_a, 'h')
        g.p(bar(P(0.62), P(0.93), 4.0, 3.2), shaft_b, 'h')
        g.p(bar(P(0.93), P(1.0), 3.2, 1.6), 'steelD', 'r')
        b = P(0.80)
        g.p(ellp(b[0], b[1], 7.6, 3.3, 12), ring, 'r')
    # задняя палка, потом передняя
    pole((28, 12), (64, 84), 'ruby', 'steel', 'turq', 'emer')
    pole((68, 12), (32, 84), 'rose', 'steel', 'turq', 'turq')
    # темляк (ремешок)
    g.hl([(26, 24), (20, 31), (25, 38)], col='#F78F97', op=0.9, w=1.4)
    g.hl([(70, 24), (76, 31), (71, 38)], col='#8DF1E9', op=0.9, w=1.4)
    g.hl([(46, 44), (50, 52)], op=0.4, w=1.0)
    g.spark(48, 14, 3.4)


def gas_stove(g):
    # баллон
    g.p([(32, 60), (48, 60), (48, 83), (36, 83), (32, 79)], 'blue', 'h')
    g.p([(48, 60), (64, 60), (64, 79), (60, 83), (48, 83)], 'ultra', 'H')
    g.p([(32, 60), (64, 60), (64, 66), (32, 66)], 'steel', 'v')
    # стойки
    g.p(bar((38, 48), (19, 34), 5, 3.4), 'steel', 'd')
    g.p(bar((58, 48), (77, 34), 5, 3.4), 'steel', 'd')
    # горелка
    g.p([(44, 52), (52, 52), (53, 60), (43, 60)], 'steelD', 'h')
    g.p([(33, 46), (63, 46), (60, 52), (36, 52)], 'steel', 'v')
    # пламя
    g.s([(48, 14), (55, 26), (59, 37), (56, 46), (40, 46), (37, 37), (41, 27)], 'rose', 'r')
    g.s([(48, 26), (53, 35), (53, 45), (43, 45), (43, 35)], 'amber', 'r', stroke_width=1.1)
    g.s([(48, 36), (50.6, 41), (48, 45), (45.4, 41)], 'milk', 'r', stroke_width=0.8)
    g.hl([(35, 62), (35, 76)], op=0.5)
    g.hl([(37, 49), (50, 48)], op=0.5, w=1.0)
    g.glows.clear()
    g.add_glow(48, 36, 34, FAM['amber'][0], 0.6)


def sleeping_bag(g):
    # локальные координаты вдоль мешка: u 0..78, полуширина hw(u)
    def hw(u):
        pts_ = [(0, 9), (7, 15), (16, 21), (34, 20), (52, 16), (68, 11), (78, 7)]
        for (u0, w0), (u1, w1) in zip(pts_, pts_[1:]):
            if u0 <= u <= u1:
                return w0 + (w1 - w0) * (u - u0) / (u1 - u0)
        return pts_[-1][1]

    def edge(u, v):          # граница секции выпуклая (строчка стёганого мешка)
        return u + 3.2 * (1 - (v / max(hw(u), 1)) ** 2)

    def band(u0, u1, n=6):
        vs = [-1 + 2 * i / n for i in range(n + 1)]
        a = [(edge(u0, v * hw(u0)), v * hw(u0)) for v in vs]
        b = [(edge(u1, v * hw(u1)), v * hw(u1)) for v in reversed(vs)]
        return a + b

    ang = math.radians(-33)

    def T(ps):
        return [(48 + (u - 39) * math.cos(ang) - v * math.sin(ang),
                 50 + (u - 39) * math.sin(ang) + v * math.cos(ang)) for u, v in ps]
    bands = [(0, 17, 'turq', 'd'), (17, 33, 'ultra', 'r'), (33, 48, 'viol', 'r'), (48, 63, 'ultra', 'r'), (63, 78, 'blue', 'D')]
    for u0, u1, fam, st in bands:
        g.p(T(band(u0, u1)), fam, st)
    g.p(T([(2.5, -4), (7, -9), (13.5, -9), (13.5, 9), (7, 9), (2.5, 4)]), 'night', 'v')
    g.hl(T([(18, 0), (34, 0), (48, 0), (63, 0), (76, 0)]), col='#D6E5F1', op=0.85, w=1.5)
    g.hl(T([(24, -9), (24, -16)]), op=0.5, w=1.0)
    g.hl(T([(40, -9), (40, -14)]), op=0.4, w=1.0)
    g.hl(T([(24, 9), (24, 16)]), op=0.4, w=1.0)
    g.spark(74, 22, 3.4)


def first_aid(g):
    # ручка
    g.p([(36, 36), (36, 27), (40, 22), (56, 22), (60, 27), (60, 36), (54, 36), (54, 29), (42, 29), (42, 36)], 'steel', 'v')
    # крышка и корпус
    g.p([(24, 36), (72, 36), (76, 44), (20, 44)], 'turq', 'v')
    g.p([(20, 44), (48, 44), (48, 76), (25, 76), (20, 70)], 'blue', 'h')
    g.p([(48, 44), (76, 44), (76, 70), (71, 76), (48, 76)], 'ultra', 'H')
    # замки
    g.p([(29, 41), (35, 41), (35, 48), (29, 48)], 'steel', 'r', stroke_width=1.0)
    g.p([(61, 41), (67, 41), (67, 48), (61, 48)], 'steel', 'r', stroke_width=1.0)
    # крест
    cx, cy, h, t = 48, 60, 12, 4.4
    g.p([(cx - t, cy - h), (cx + t, cy - h), (cx + t, cy - t), (cx + h, cy - t), (cx + h, cy + t), (cx + t, cy + t),
         (cx + t, cy + h), (cx - t, cy + h), (cx - t, cy + t), (cx - h, cy + t), (cx - h, cy - t), (cx - t, cy - t)], 'milk', 'r')
    g.hl([(24, 40), (60, 40)], op=0.5, w=1.0)
    g.hl([(23, 50), (23, 66)], op=0.45)
    g.hl([(42, 25), (54, 25)], op=0.6, w=1.0)
    g.spark(72, 24, 3.4)


def flask(g):
    a = 12
    R = lambda ps: rot(ps, a, (48, 52))
    g.p(R([(40, 10), (56, 10), (57, 21), (39, 21)]), 'turq', 'v')
    g.p(R([(42, 21), (54, 21), (54, 28), (42, 28)]), 'steelD', 'h')
    g.p(R([(42, 28), (54, 28), (61, 33), (66, 42), (30, 42), (35, 33)]), 'steel', 'v')
    g.p(R([(30, 42), (48, 42), (48, 82), (35, 82), (29, 76), (29, 47)]), 'steel', 'h')
    g.p(R([(48, 42), (66, 42), (67, 47), (67, 76), (61, 82), (48, 82)]), 'steelD', 'H')
    g.p(R([(29, 66), (67, 66), (67, 76), (61, 82), (35, 82), (29, 76)]), 'umber', 'v')
    # эмблема-ромб
    ex, ey = R([(48, 54)])[0]
    g.p([(ex, ey - 9), (ex + 7.5, ey), (ex, ey + 9), (ex - 7.5, ey)], 'turq', 'r')
    # цепочка крышки
    g.hl(R([(40, 15), (31, 17), (28, 26), (32, 34)]), col='#D6E5F1', op=0.9, w=1.4)
    g.hl(R([(33, 46), (33, 62)]), op=0.55)
    g.spark(74, 26, 3.4)


def compass(g):
    cx, cy = 48, 52
    g.p([(44, 9), (52, 9), (52, 17), (44, 17)], 'steelD', 'h')
    g.c(cx, cy, 37, 'steelD', 'r')
    for i, (fam, st) in enumerate([('steel', 'd'), ('turq', 'D'), ('steel', 'd'), ('turq', 'D')]):
        a0 = -45 + 90 * i + 8
        g.p(ring_seg(cx, cy, 28, 37, a0, a0 + 90, 8), fam, st)
    g.c(cx, cy, 28, 'night', 'r')
    for a in (0, 90, 180, 270):
        x, y = cx + 22.5 * math.cos(math.radians(a - 90)), cy + 22.5 * math.sin(math.radians(a - 90))
        g.p(rot([(x, y - 3), (x + 2.2, y), (x, y + 3), (x - 2.2, y)], 0, (x, y)), 'turq', 'r', stroke_width=0.8)
    A = 38
    N_ = [(cx, cy - 25), (cx + 7, cy), (cx - 7, cy)]
    S_ = [(cx, cy + 25), (cx + 7, cy), (cx - 7, cy)]
    g.p(rot(N_, A, (cx, cy)), 'ruby', 'v')
    g.p(rot(S_, A, (cx, cy)), 'milk', 'v')
    g.c(cx, cy, 3.6, 'amber', 'r', stroke_width=1.0)
    g.hl([(24, 40), (30, 30), (40, 25)], op=0.55)
    g.spark(74, 76, 3.2)


def amulet_leshy(g):
    g.glows.clear()
    g.add_glow(50, 46, 40, '#7DF3B8', 0.75)
    g.add_glow(50, 46, 24, '#D9FFE9', 0.45)
    # сучок: ствол и конец
    g.p(bar((18, 78), (46, 49), 11, 9), 'umber', 'd')
    g.p(bar((46, 49), (70, 24), 9, 6), 'umberD', 'd')
    # ветки в стороны
    g.p(bar((55, 41), (80, 48), 6.5, 4.0), 'umber', 'r')
    g.p(bar((32, 63), (19, 52), 5.5, 3.2), 'umberD', 'r')
    # листочки
    g.p(lens((76, 47), (88, 38), 9), 'emer', 'd')
    g.p(lens((20, 53), (12, 42), 8), 'emer', 'D')
    # нитяная обмотка рубиновая
    for t in (0.0, 1.0, 2.0):
        c0 = lerp((37, 58), (46, 49), t / 2)
        g.p(bar((c0[0] - 4.6, c0[1] + 5.4), (c0[0] + 5.4, c0[1] - 4.6), 3.4), 'ruby', 'r')
    # хвосты нитки и бусины
    g.thread([(42, 54), (38, 66), (40, 74)], 'ruby', 1.6, smooth=True)
    g.c(40, 79, 4.4, 'turq', 'r')
    g.thread([(47, 53), (54, 63), (53, 70)], 'ruby', 1.6, smooth=True)
    g.c(53, 74, 3.2, 'milk', 'r', stroke_width=1.0)
    g.hl([(22, 72), (38, 55)], op=0.55)
    g.hl([(52, 40), (66, 27)], op=0.5, w=1.0)
    g.spark(28, 26, 3.6, col='#EFFFF6')


def ball_yaga(g):
    cx, cy, r = 44, 46, 28
    ang = math.radians(-38)

    def T(u, v):
        return (cx + u * math.cos(ang) - v * math.sin(ang), cy + u * math.sin(ang) + v * math.cos(ang))

    def curve(v0, bow=0.018, n=14):
        out = []
        for i in range(n + 1):
            u = -r - 3 + 2 * (r + 3) * i / n
            out.append(T(u, v0 + bow * u * u))
        return out
    edges = [-46, -33, -22, -11, 0, 10, 21, 34]
    cols = [('viol', 'd'), ('rose', 'r'), ('turq', 'D'), ('ultra', 'd'), ('ruby', 'r'), ('viol', 'D'), ('turq', 'r')]
    for i, (fam, st) in enumerate(cols):
        top = curve(edges[i])
        bot = list(reversed(curve(edges[i + 1])))
        cp = clip_circle(top + bot, cx, cy, r, 40)
        if len(cp) >= 3:
            g.p(cp, fam, st)
    # свободный конец нити
    g.thread([(54, 62), (62, 71), (68, 77), (74, 75), (73, 69)], 'rose', 2.4, smooth=True)
    g.hl([(24, 40), (29, 30), (39, 23)], op=0.65, w=1.3)
    g.hl([(30, 63), (41, 70)], op=0.35, w=1.0)
    g.spark(74, 22, 3.4)


# =============================================================================
# ПОКАЗАТЕЛИ
# =============================================================================

def stat_satiety(g):
    a = 10
    R = lambda ps: rot(ps, a, (48, 50))
    # стебель
    g.thread(R([(48, 86), (48, 40)]), 'milk', 2.6)
    # листья у основания
    g.p(R(lens((48, 74), (31, 63), 8)), 'emerD', 'd')
    g.p(R(lens((48, 70), (65, 58), 8)), 'emer', 'D')
    # зёрна парами
    for k, y in enumerate((52, 40, 28)):
        sz = 19 - k * 1.2
        L = lens((48, y + 6), (48 - 13, y - 9), 8.5 - k * 0.6)
        Rr = lens((48, y + 6), (48 + 13, y - 9), 8.5 - k * 0.6)
        g.p(R(L), 'coral', 'd' if k % 2 == 0 else 'r')
        g.p(R(Rr), 'coral', 'D' if k % 2 == 0 else 'r')
    g.p(R(lens((48, 25), (48, 7), 9)), 'coral', 'v')
    g.hl(R([(41, 44), (37, 38)]), op=0.7, w=1.2)
    g.hl(R([(55, 32), (59, 27)]), op=0.55, w=1.1)
    g.hl(R([(46, 18), (47, 11)]), op=0.7, w=1.2)
    g.spark(76, 74, 3.2)


def stat_water(g):
    cx, cy, hh, w = 48, 51, 37, 36
    dr = teardrop(cx, cy, hh, w, 1.05, 44)
    cuts = [
        ([(cx, cy - hh - 3), (cx - 50, cy - 6), (cx - 50, cy + 4), (cx - 6, cy + 4), (cx - 2, cy - 14)], 'ice', 'd'),
        ([(cx, cy - hh - 3), (cx - 2, cy - 14), (cx - 6, cy + 4), (cx + 6, cy + 10), (cx + 50, cy + 4), (cx + 50, cy - 6)], 'sky', 'D'),
        ([(cx - 50, cy + 4), (cx - 6, cy + 4), (cx + 6, cy + 10), (cx - 8, cy + 50), (cx - 50, cy + 50)], 'sky', 'r'),
        ([(cx + 6, cy + 10), (cx + 50, cy + 4), (cx + 50, cy + 50), (cx - 8, cy + 50)], 'blue', 'D'),
    ]
    for poly, fam, st in cuts:
        q = clip_convex(poly, dr)
        if len(q) >= 3:
            g.p(q, fam, st)
    # яркий осколок-блик внутри капли
    g.p(lens((cx - 17, cy + 10), (cx - 10, cy + 28), 8.5, 5), 'ice', 'r')
    g.hl([(cx - 22, cy - 2), (cx - 24, cy + 10), (cx - 20, cy + 22)], op=0.7, w=1.4)
    g.hl([(cx - 6, cy - 24), (cx - 4, cy - 17)], op=0.7, w=1.1)
    g.spark(76, 26, 3.4)


def stat_warmth(g):
    # внешнее пламя
    outer = [(48, 8), (56, 22), (68, 34), (74, 50), (69, 66), (58, 77), (48, 81), (38, 77), (27, 66), (22, 50), (28, 36), (38, 26), (42, 16)]
    g.s([(48, 8), (58, 24), (70, 38), (73, 54), (66, 70), (48, 80), (30, 70), (23, 54), (26, 40), (38, 30), (42, 17)], 'rose', 'r')
    # боковой язык
    g.s([(66, 36), (72, 46), (72, 58), (66, 56), (62, 46)], 'coral', 'd')
    g.s([(32, 40), (28, 52), (31, 62), (38, 54), (37, 46)], 'ruby', 'd')
    # внутреннее пламя
    g.s([(48, 30), (57, 44), (60, 58), (54, 72), (42, 72), (36, 58), (39, 44)], 'coral', 'r')
    g.s([(48, 46), (54, 58), (53, 70), (43, 70), (42, 58)], 'amber', 'r', stroke_width=1.1)
    g.s([(48, 58), (51, 65), (48, 70), (45, 65)], 'milk', 'r', stroke_width=0.8)
    g.glows.clear()
    g.add_glow(48, 60, 32, FAM['amber'][0], 0.55)
    g.hl([(30, 62), (27, 52), (30, 44)], op=0.5, w=1.2)
    g.hl([(44, 20), (52, 28)], op=0.6, w=1.1)
    g.spark(74, 24, 3.2)


# =============================================================================
# ЗОНЫ (64x64, бирюзовые кабошоны)
# =============================================================================

def zone_city(g):
    g.add_glow(60, 30, 26, '#EFFFFB', 0.6)
    g.c(60, 28, 8.5, 'milk', 'r')
    # башни (в 96-пространстве; обрезаются по кабошону)
    g.p([(14, 54), (26, 54), (26, 40), (30, 34), (30, 54), (34, 54), (34, 90), (14, 90)], 'ultra', 'd', clip=True)
    g.p([(33, 90), (33, 34), (36, 30), (36, 14), (38, 14), (38, 30), (41, 34), (51, 34), (51, 90)], 'blue', 'd', clip=True)
    g.p([(50, 90), (50, 44), (54, 40), (66, 40), (70, 44), (70, 90)], 'night', 'd', clip=True)
    g.p([(69, 90), (69, 56), (74, 52), (84, 52), (84, 90)], 'viol', 'd', clip=True)
    g.p([(10, 90), (10, 70), (22, 66), (34, 70), (34, 90)], 'night', 'v', clip=True)
    # окна — малые янтарные осколки
    for (x, y) in [(40, 42), (45, 54), (58, 50), (58, 62), (74, 62), (20, 62), (42, 70)]:
        g.p([(x, y), (x + 5, y), (x + 5, y + 6), (x, y + 6)], 'amber', 'r', stroke_width=0.9)
    g.hl([(17, 56), (17, 66)], op=0.5, w=1.3)
    g.hl([(36, 36), (36, 62)], op=0.5, w=1.3)
    g.spark(26, 24, 4)


def zone_suburb(g):
    g.add_glow(34, 40, 30, '#EFFFFB', 0.4)
    # дерево справа
    g.p(bar((76, 80), (76, 54), 6, 5), 'umberD', 'h', clip=True)
    g.c(75, 42, 15, 'emerD', 'r')
    g.c(67, 50, 10, 'emer', 'r')
    # домик
    g.p([(13, 46), (45, 46), (45, 78), (13, 78)], 'milk', 'v', clip=True)
    g.p([(8, 48), (29, 24), (50, 48)], 'rubyD', 'd', clip=True)
    g.p([(37, 27), (43, 27), (43, 40), (37, 36)], 'night', 'r')
    g.p([(17, 52), (27, 52), (27, 62), (17, 62)], 'amber', 'r', stroke_width=0.9)
    g.p([(32, 56), (41, 56), (41, 78), (32, 78)], 'umber', 'h')
    # земля
    g.s([(0, 77), (30, 75), (60, 77), (96, 74), (96, 98), (0, 98)], 'emerD', 'v', clip=True)
    # штакетник: светлые рейки с зубцами сверху
    fence = []
    x = 6
    for i in range(10):
        fence += [(x, 74), (x + 3, 70.5), (x + 6, 74)]
        x += 8
    fence += [(x - 2, 88), (6, 88)]
    g.p(fence, 'ice', 'v', clip=True)
    g.lines([(fx, 74, fx, 88) for fx in range(12, 80, 8)] + [(8, 79, 84, 79)], col=LEAD, op=1, w=1.3)
    g.hl([(16, 50), (16, 74)], op=0.5, w=1.2)
    g.spark(60, 20, 3.6)


def zone_wild(g):
    g.add_glow(62, 26, 24, '#EFFFFB', 0.5)
    g.c(63, 26, 7.5, 'milk', 'r')
    # холмы
    g.s([(2, 66), (20, 54), (48, 52), (72, 58), (98, 68), (98, 96), (2, 96)], 'viol', 'v', clip=True)
    g.s([(2, 78), (22, 70), (46, 72), (70, 68), (98, 78), (98, 96), (2, 96)], 'blue', 'v', clip=True)
    # ели
    def fir(x, yb, h, w, fam, st):
        tiers = 3
        right, left = [], []
        for k in range(1, tiers + 1):
            t = k / tiers
            yk = yb - h + h * t
            hw_ = w / 2 * (0.3 + 0.7 * t)
            if k < tiers:
                right += [(x + hw_, yk), (x + hw_ * 0.45, yk - h / tiers * 0.28)]
                left += [(x - hw_, yk), (x - hw_ * 0.45, yk - h / tiers * 0.28)]
            else:
                right += [(x + hw_, yk)]
                left += [(x - hw_, yk)]
        g.p([(x, yb - h)] + right + list(reversed(left)), fam, st, clip=True)
    fir(30, 76, 52, 30, 'emerD', 'd')
    fir(52, 80, 62, 36, 'night', 'd')
    fir(70, 78, 40, 24, 'emer', 'D')
    g.hl([(27, 36), (24, 48)], op=0.5, w=1.2)
    g.hl([(48, 28), (44, 44)], op=0.5, w=1.2)
    g.spark(22, 26, 3.8)


# =============================================================================
# РЕЕСТР: id, группа, строитель, фон, зерно, описание
# =============================================================================
# (id, kind, builder, bg, seed, size, подсветка (cx, cy, r, цвет, непрозр.) | None, что нарисовано)
ICONS = [
    ('bread', 'food', bread, 'teal', 3, 96, (48, 52, 34, '#7FE3D8', 0.45), 'Бородинский хлеб: купол из трёх коричневых стёкол, нижний подпуск, три молочных надреза на корке'),
    ('stew', 'food', stew, 'indigo', 11, 96, (48, 52, 34, '#9AA8FF', 0.4), 'Банка тушёнки: стальная крышка, рубиновая этикетка с молочным медальоном и звёздочкой'),
    ('water', 'food', water, 'violet', 5, 96, (48, 56, 34, '#B7A6FF', 0.4), 'Бутылка воды: бирюзовая крышка, ледяные плечи, синяя вода с пузырьками'),
    ('tea', 'food', tea, 'emerald', 7, 96, (48, 50, 36, '#8DF5C3', 0.45), 'Термос чая: рубиновая чашка-крышка, синий корпус, ручка-ремешок, пар молочным стеклом'),
    ('chocolate', 'food', chocolate, 'teal', 9, 96, (48, 52, 34, '#7FE3D8', 0.45), 'Плитка шоколада, наклонённая: дольки коричневым стеклом, бирюзовая фольга зигзагом'),
    ('berries', 'food', berries, 'emerald', 2, 96, (48, 50, 34, '#8DF5C3', 0.45), 'Горсть ягод: рубиновые и ультрамариновая ягода, зелёные листья и чашелистики'),
    ('fish', 'food', fish, 'indigo', 4, 96, (46, 50, 34, '#9AA8FF', 0.4), 'Копчёная рыба: голова, спинка и хвост золотисто-медными стёклами, молочный глаз'),
    ('pie', 'food', pie, 'teal', 6, 96, (48, 46, 36, '#7FE3D8', 0.45), 'Пирог с решёткой: тёплая корочка, рубиновая начинка, боковины, листик теста'),
    ('kvass', 'food', kvass, 'emerald', 8, 96, (48, 54, 34, '#8DF5C3', 0.4), 'Бутылка кваса: тёмное стекло, молочная этикетка с колоском, рубиновая крышка'),
    ('gas', 'food', gas, 'violet', 12, 96, (48, 52, 34, '#B7A6FF', 0.4), 'Газовый баллон: синие половинки, стальные пояса, бирюзовый вентиль, язычок пламени на боку'),
    ('matches', 'food', matches, 'violet', 14, 96, None, 'Коробок спичек: фиолетовый коробок с чиркашом и молочной этикеткой, три спички, у средней янтарный огонёк'),
    ('socks', 'gear', socks, 'teal', 15, 96, (48, 50, 34, '#7FE3D8', 0.45), 'Шерстяной носок: рубиновый манжет, молочная полоса, бирюзовая пятка, синее голенище, рубиновый носок'),
    ('raincoat', 'gear', raincoat, 'indigo', 16, 96, (48, 52, 36, '#9AA8FF', 0.4), 'Дождевик с капюшоном и рукавами: бирюзово-изумрудные половины, синие рукава, ультрамариновый подол, капли дождя'),
    ('trekking_poles', 'gear', trekking_poles, 'emerald', 17, 96, (48, 50, 36, '#8DF5C3', 0.45), 'Две трекинговые палки крест-накрест: рубиновые рукояти, стальные трубки, бирюзовые секции, кружки-ограничители'),
    ('gas_stove', 'gear', gas_stove, 'wine', 18, 96, None, 'Горелка с баллоном: синий баллон, стальная головка и стойки, огонёк роза/янтарь/молоко'),
    ('sleeping_bag', 'gear', sleeping_bag, 'teal', 19, 96, (48, 50, 36, '#7FE3D8', 0.4), 'Спальник-кокон по диагонали: 5 секций разных синих, фиолет, капюшон с чёрным вырезом, молния'),
    ('first_aid', 'gear', first_aid, 'emerald', 20, 96, (48, 56, 36, '#8DF5C3', 0.45), 'Аптечка: синий чемоданчик с бирюзовой крышкой, ручка, замки, молочный крест (без красного)'),
    ('flask', 'gear', flask, 'violet', 21, 96, (48, 52, 34, '#B7A6FF', 0.4), 'Фляга: стальной плоский корпус в кожаной обвязке, бирюзовая крышка на цепочке, ромб-эмблема'),
    ('compass', 'gear', compass, 'indigo', 22, 96, (48, 52, 36, '#9AA8FF', 0.45), 'Компас: кольцо из 4 секторов, ночное поле, рубиновый север и молочный юг, янтарная ось'),
    ('amulet_leshy', 'gear', amulet_leshy, 'emerald', 23, 96, None, 'Оберег лешего: сучок с веткой и листочками, рубиновая обмотка и нитки с бусинами, зелёное свечение'),
    ('ball_yaga', 'gear', ball_yaga, 'teal', 24, 96, (46, 48, 34, '#7FE3D8', 0.4), 'Клубок шерсти: 7 витков нити (фиолет, роза, бирюза, ультрамарин, рубин), свободный конец нити'),
    ('stat_satiety', 'stat', stat_satiety, 'wine', 25, 96, (48, 46, 34, '#FF9C84', 0.5), 'Сытость (коралл #E07A5F): колос с 7 зёрнами и листьями'),
    ('stat_water', 'stat', stat_water, 'sea', 26, 96, (48, 50, 34, '#7ACBFF', 0.5), 'Вода (голубой #5BB5E8): граненая капля, круги на воде'),
    ('stat_warmth', 'stat', stat_warmth, 'ruby', 27, 96, None, 'Тепло (красно-розовый #E0556B): огонёк с янтарным ядром'),
    ('city', 'zone', zone_city, 'turqz', 28, 64, None, 'Город: силуэты башен ультрамарин/синий/ночь, молочная луна, малые янтарные окна'),
    ('suburb', 'zone', zone_suburb, 'turqz', 29, 64, None, 'Пригород: домик с рубиновой крышей и янтарным окном, светлый штакетник, дерево, изумрудная земля'),
    ('wild', 'zone', zone_wild, 'turqz', 30, 64, None, 'Окрестности: ели на холмах, молочная луна'),
]


COUNTS = {}


def build(entry):
    ident, kind, fn, bg, seed, size, glow, desc = entry
    g = G(ident, size=size, bg=bg, seed=seed, glow=glow, lead=1.7 if size == 96 else 1.7)
    fn(g)
    svg = g.render()
    COUNTS[ident] = (g.nbig, g.nsmall)
    return svg


def check(ident, svg):
    root = ET.fromstring(svg)
    bad = sorted({el.tag.split('}')[-1] for el in root.iter() if el.tag.split('}')[-1] not in ALLOWED})
    problems = []
    if bad:
        problems.append('теги: ' + ','.join(bad))
    if 'viewBox' not in svg[:200]:
        problems.append('нет viewBox')
    if re.search(r'\sstyle=|\sclip-path=|\sfilter=|\smask=|\swidth="\d+px', svg):
        problems.append('запрещённый атрибут')
    n = len(svg.encode())
    if n > MAX_BYTES:
        problems.append(f'{n} Б > {MAX_BYTES}')
    return n, problems


def count_shards(svg):
    root = ET.fromstring(svg)
    n = 0
    for el in root.iter():
        if el.tag.split('}')[-1] == 'g':
            n = len([c for c in el if c.tag.split('}')[-1] in ('polygon', 'path', 'circle', 'ellipse')])
    return n


def write_all():
    os.makedirs(ITEMS_DIR, exist_ok=True)
    os.makedirs(ZONES_DIR, exist_ok=True)
    out = {}
    for entry in ICONS:
        ident, kind = entry[0], entry[1]
        svg = build(entry)
        n, problems = check(ident, svg)
        folder = ZONES_DIR if kind == 'zone' else ITEMS_DIR
        with open(os.path.join(folder, f'{ident}.svg'), 'w', encoding='utf-8') as fh:
            fh.write(svg)
        out[ident] = (kind, svg, n, problems)
    return out


# ---- контактный лист -------------------------------------------------------

def sheet(files, path, big=False):
    from playwright.sync_api import sync_playwright
    cells = []
    for ident, (kind, svg, n, problems) in files.items():
        b = base64.b64encode(svg.encode()).decode()
        s = 64 if kind == 'zone' else 96
        z = 3 if big else 2
        src = f'data:image/svg+xml;base64,{b}'
        small = ''.join(f'<img src="{src}" width="{px}" height="{px}">' for px in (56, 48, 40))
        flag = ' <b style="color:#E0556B">!</b>' if problems else ''
        cells.append(
            f'<figure><img src="{src}" width="{s*z}" height="{s*z}"><div class="sm">{small}</div>'
            f'<figcaption>{ident} · {n/1024:.1f} КБ{flag}</figcaption></figure>')
    html = ('<html><body style="margin:0;background:#0E1621;font:11px sans-serif;color:#9BA7B4">'
            '<div style="display:flex;flex-wrap:wrap;gap:14px 12px;padding:12px;width:%dpx">' % (1300 if not big else 1500)
            + ''.join(cells) + '</div><style>figure{margin:0;width:%dpx}.sm{display:flex;gap:6px;align-items:center;margin-top:4px}</style></body></html>' % (200 if not big else 300))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1320 if not big else 1520, 'height': 800})
        pg.set_content(html)
        pg.wait_for_timeout(400)
        pg.screenshot(path=path, full_page=True)
        b.close()


# ---- манифест --------------------------------------------------------------

def write_manifest(files):
    rows = []
    groups = [('food', 'Еда и питьё (96×96)'), ('gear', 'Снаряжение и находки (96×96)'),
              ('stat', 'Показатели (96×96)'), ('zone', 'Зоны (64×64)')]
    out = ['# Иконки «Путника» в витражном стиле (v5.3) — манифест для UI',
           '',
           'Файлы генерирует `python3 tools/art/items_glass.py` (пишет SVG, манифест и контактный лист `/tmp/items_sheet.png`). '
           'Пути относительно `app/assets/art/`. Имя файла = id предмета (`items.json` / `balance.json → items`). '
           'Кабошон круглый: внутри вписанный круг диаметра ~91 % от viewBox, поля прозрачные, '
           'фон иконки НЕ рисуйте поверх — свинец уже в SVG. Читается на 40–56 px.',
           '',
           'Показатели используют цвета заказа: сытость коралл `#E07A5F`, вода голубой `#5BB5E8`, тепло красно-розовый `#E0556B`.',
           '']
    for key, title in groups:
        out += [f'## {title}', '', '| id | файл | viewBox | КБ | стёкол (крупных+мелких) | что нарисовано |', '|---|---|---|---|---|---|']
        for entry in ICONS:
            ident, kind, _, bg, _, size, _, desc = entry
            if kind != key:
                continue
            folder = 'zones' if kind == 'zone' else 'items'
            _, svg, n, _ = files[ident]
            nb, ns = COUNTS[ident]
            out.append(f'| `{ident}` | `{folder}/{ident}.svg` | 0 0 {size} {size} | {n/1024:.1f} | {nb}+{ns} | {desc} |')
        out.append('')
    out += ['## Заметки для UI-разработчика', '',
            '* Подключать как `SvgPicture.asset(...)` без `colorFilter`: цвет задан стеклом, фон-кабошон уже в файле (круг, свинец `#070B10`, поля прозрачные). Подкладку под иконку не рисовать.',
            '* Читается на 40–56 px (проверено контактным листом); рекомендуемые размеры: показатели 40–56, предметы 48–72, зоны 40–64.',
            '* Показатели: `items/stat_satiety.svg`, `items/stat_water.svg`, `items/stat_warmth.svg`; зоны: `zones/city.svg`, `zones/suburb.svg`, `zones/wild.svg` (id = значение поля `zone` события).',
            '* Для id предмета без файла показывать плашку без иконки (специальной «заглушки» не рисовали).',
            '* Крест аптечки молочный (без красного). Янтарные осколки только у огня/света (горелка, спичка, тепло, окна, ось компаса, этикетка термоса); коричневое стекло хлеба, рыбы, пирога, шоколада, кваса — цвет еды, не фон.',
            '* «Мелкие» осколки — акценты (пуговицы, капли, окна, бусины); «крупных» в каждой иконке 4–9.',
            '']
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))


if __name__ == '__main__':
    files = write_all()
    bad = False
    for ident, (kind, svg, n, problems) in files.items():
        mark = ''
        if problems:
            mark = '  <-- ' + '; '.join(problems)
            bad = True
        print(f'{ident:16s} {kind:5s} {n:5d} Б  крупных {COUNTS[ident][0]}, мелких {COUNTS[ident][1]}{mark}')
    args = sys.argv[1:]
    out = '/tmp/items_sheet.png'
    if '--sheet' in args:
        out = args[args.index('--sheet') + 1]
    sheet(files, out, big='--big' in args)
    write_manifest(files)
    print('лист:', out)
    sys.exit(1 if bad else 0)

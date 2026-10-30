"""Общая палитра и примитивы для векторной графики «Путника».

Все SVG собираются только из базовых элементов (совместимость с flutter_svg):
path, rect, circle, ellipse, polygon, polyline, g, linearGradient,
radialGradient, stop, defs. Цвета — только атрибутами.
"""
import math
import random

# ---- Палитра «Атлас» -------------------------------------------------------
INK = '#0E1621'      # фон-чернила
R1 = '#16222F'       # приподнятая плоскость
R2 = '#1F3043'       # приподнятая плоскость 2
PARCH = '#E9DFC8'    # пергамент
SEC = '#9BA7B4'      # вторичный
GOLD = '#D9B35B'     # свет, акценты
TEAL = '#4FA3A5'     # вода, линии
WARM = '#E8A15A'     # огонь, окна
AU1 = '#8FE6B8'      # сияние: светлый край
AU2 = '#4FC9A4'      # сияние: середина
AU3 = '#2E8C86'      # сияние: глубина
# Производные тона для планов глубины (смешение палитры, не новые оттенки)
FAR = '#2A4157'      # дальний план (воздушная перспектива)
MID = '#1F3043'      # средний план
NEAR = '#132030'     # ближний план
FORE = '#0A111A'     # передний план
DEEP = '#0B1219'
MOSS = '#2F5E57'     # мох / хвоя в эмблемах (бирюза в тени)
BARK = '#3A3A3C'


def f(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    if s == '-0':
        s = '0'
    return s


def pts(points):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in points)


def attrs(**kw):
    out = []
    for k, v in kw.items():
        if v is None:
            continue
        k = k.rstrip('_').replace('_', '-')
        if isinstance(v, float):
            v = f(v)
        out.append(f'{k}="{v}"')
    return (' ' + ' '.join(out)) if out else ''


class Doc:
    def __init__(self, vb, prefix):
        self.vb = vb
        self.prefix = prefix
        self.defs = []
        self.body = []
        self.n = 0
        self.cache = {}

    # ---- defs
    def _id(self):
        self.n += 1
        return f'{self.prefix}{self.n}'

    def lin(self, stops, x1=0, y1=0, x2=0, y2=1, units=None):
        key = ('l', tuple(map(tuple, stops)), x1, y1, x2, y2, units)
        if key in self.cache:
            return self.cache[key]
        gid = self._id()
        self.cache[key] = f'url(#{gid})'
        st = ''.join(self._stop(s) for s in stops)
        u = f' gradientUnits="userSpaceOnUse"' if units else ''
        self.defs.append(f'<linearGradient id="{gid}" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}"{u}>{st}</linearGradient>')
        return f'url(#{gid})'

    def rad(self, stops, cx=0.5, cy=0.5, r=0.5, units=None, fx=None, fy=None):
        key = ('r', tuple(map(tuple, stops)), cx, cy, r, units, fx, fy)
        if key in self.cache:
            return self.cache[key]
        gid = self._id()
        self.cache[key] = f'url(#{gid})'
        st = ''.join(self._stop(s) for s in stops)
        u = f' gradientUnits="userSpaceOnUse"' if units else ''
        fo = ''
        if fx is not None:
            fo = f' fx="{f(fx)}" fy="{f(fy)}"'
        self.defs.append(f'<radialGradient id="{gid}" cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"{fo}{u}>{st}</radialGradient>')
        return f'url(#{gid})'

    @staticmethod
    def _stop(s):
        off, col = s[0], s[1]
        op = s[2] if len(s) > 2 else 1
        o = f' stop-opacity="{f(op) if op != 1 else 1}"' if op != 1 else ''
        return f'<stop offset="{f(off)}" stop-color="{col}"{o}/>'

    # ---- elements
    def add(self, s):
        self.body.append(s)

    def path(self, d, **kw):
        self.add(f'<path d="{d}"{attrs(**kw)}/>')

    def rect(self, x, y, w, h, **kw):
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"{attrs(**kw)}/>')

    def circle(self, cx, cy, r, **kw):
        self.add(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"{attrs(**kw)}/>')

    def ellipse(self, cx, cy, rx, ry, **kw):
        self.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}"{attrs(**kw)}/>')

    def poly(self, points, **kw):
        self.add(f'<polygon points="{pts(points)}"{attrs(**kw)}/>')

    def line(self, points, **kw):
        kw.setdefault('fill', 'none')
        self.add(f'<polyline points="{pts(points)}"{attrs(**kw)}/>')

    def g_open(self, **kw):
        self.add(f'<g{attrs(**kw)}>')

    def g_close(self):
        self.add('</g>')

    def render(self):
        d = f'<defs>{"".join(self.defs)}</defs>' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{self.vb}">'
                + d + ''.join(self.body) + '</svg>\n')


# ---- геометрия -------------------------------------------------------------

def smooth(points, closed=False):
    """Catmull-Rom → кубические Безье. Возвращает d без замыкания."""
    p = points
    d = f'M{f(p[0][0])},{f(p[0][1])}'
    n = len(p)
    for i in range(n - 1):
        p0 = p[i - 1] if i > 0 else p[i]
        p1, p2 = p[i], p[i + 1]
        p3 = p[i + 2] if i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f'C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d


def ridge(x0, x1, y, amp, seed, n=8, bottom=None, sharp=False):
    rnd = random.Random(seed)
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    ps = [(x, y - amp * (0.3 + 0.7 * rnd.random())) for x in xs]
    if sharp:
        d = f'M{f(ps[0][0])},{f(ps[0][1])}' + ''.join(f'L{f(a)},{f(b)}' for a, b in ps[1:])
    else:
        d = smooth(ps)
    bottom = bottom if bottom is not None else y + 400
    d += f'L{f(x1)},{f(bottom)}L{f(x0)},{f(bottom)}Z'
    return d


def fir_pts(x, yb, h, w, tiers=4, seed=0):
    """Ель: многоярусный силуэт. yb — основание кроны."""
    rnd = random.Random(seed)
    top = (x, yb - h)
    right, left = [], []
    for k in range(1, tiers + 1):
        t = k / tiers
        yk = yb - h + h * t
        hw = w / 2 * (0.25 + 0.75 * t) * (0.9 + 0.2 * rnd.random())
        inner = hw * 0.5
        yin = yk - h / tiers * 0.35
        if k < tiers:
            right += [(x + hw, yk), (x + inner, yin + h / tiers * 0.05)]
            left += [(x - hw * (0.92 + 0.16 * rnd.random()), yk), (x - inner, yin + h / tiers * 0.05)]
        else:
            right += [(x + hw, yk)]
            left += [(x - hw, yk)]
    return [top] + right + list(reversed(left))


def fir(doc, x, yb, h, w, fill, seed=0, tiers=4, trunk=True, **kw):
    if trunk:
        doc.rect(x - w * 0.05, yb - 2, w * 0.1, h * 0.12 + 2, fill=fill)
    doc.poly(fir_pts(x, yb, h, w, tiers, seed), fill=fill, **kw)


def fir_row(doc, x0, x1, ybase, hmin, hmax, fill, seed, step=9, jitter=4, tiers=3):
    rnd = random.Random(seed)
    x = x0
    out = []
    while x < x1:
        h = rnd.uniform(hmin, hmax)
        yb = ybase + rnd.uniform(-jitter, jitter) * 0.3
        out.append(f'M{pts(fir_pts(x, yb, h, h * 0.42, tiers, rnd.random()))}Z')
        x += step * rnd.uniform(0.7, 1.3)
    doc.path(''.join(out).replace(' ', 'L'), fill=fill)


def pine(doc, x, yb, h, fill, seed=0):
    rnd = random.Random(seed)
    doc.path(f'M{f(x-1.2)},{f(yb)}L{f(x-0.6)},{f(yb-h*0.8)}L{f(x+0.6)},{f(yb-h*0.8)}L{f(x+1.2)},{f(yb)}Z', fill=fill)
    for i in range(3):
        cx = x + rnd.uniform(-h * 0.18, h * 0.18)
        cy = yb - h * (0.78 + 0.08 * i)
        doc.ellipse(cx, cy, h * rnd.uniform(0.14, 0.22), h * 0.07, fill=fill)
    doc.path(f'M{f(x)},{f(yb-h*0.55)}L{f(x+h*0.15)},{f(yb-h*0.7)}', stroke=fill, stroke_width=1.2, fill='none')


def stars(doc, x0, y0, x1, y1, n, seed, color=PARCH, rmin=0.35, rmax=1.0, omin=0.25, omax=0.9):
    rnd = random.Random(seed)
    for _ in range(n):
        doc.circle(rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(rmin, rmax),
                   fill=color, opacity=round(rnd.uniform(omin, omax), 2))


def sparkle(doc, x, y, r, fill=GOLD, **kw):
    a = r * 0.22
    d = (f'M{f(x)},{f(y-r)}Q{f(x+a)},{f(y-a)} {f(x+r)},{f(y)}Q{f(x+a)},{f(y+a)} {f(x)},{f(y+r)}'
         f'Q{f(x-a)},{f(y+a)} {f(x-r)},{f(y)}Q{f(x-a)},{f(y-a)} {f(x)},{f(y-r)}Z')
    doc.path(d, fill=fill, **kw)


def glow(doc, cx, cy, r, color=GOLD, op=0.5):
    g = doc.rad([(0, color, op), (0.4, color, op * 0.35), (1, color, 0)])
    doc.circle(cx, cy, r, fill=g)


def moon(doc, cx, cy, r, halo=3.2, crescent=False, bg=INK):
    glow(doc, cx, cy, r * halo, PARCH, 0.22)
    doc.circle(cx, cy, r, fill=PARCH)
    doc.circle(cx - r * 0.3, cy - r * 0.15, r * 0.18, fill=SEC, opacity=0.25)
    doc.circle(cx + r * 0.25, cy + r * 0.3, r * 0.12, fill=SEC, opacity=0.2)
    if crescent:
        doc.circle(cx + r * 0.45, cy - r * 0.2, r * 0.92, fill=bg)


def sky(doc, w, h, top=INK, bottom=R2, mid=None):
    stops = [(0, top)]
    if mid:
        stops.append((0.55, mid))
    stops.append((1, bottom))
    doc.rect(0, 0, w, h, fill=doc.lin(stops))


def aurora(doc, x0, x1, y, amp, height, seed, op=0.55, n=7, rays=18, colors=(AU1, AU2, AU3)):
    """Лента сияния: волнистая полоса с вертикальным градиентом + лучи."""
    rnd = random.Random(seed)
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    lower = [(x, y + amp * math.sin(i * 1.3 + rnd.random())) for i, x in enumerate(xs)]
    upper = [(x + rnd.uniform(-6, 6), py - height * (0.6 + 0.6 * rnd.random()) * (0.15 + 0.85 * math.sin(math.pi * i / n) ** 0.6))
             for i, (x, py) in enumerate(lower)]
    g = doc.lin([(0, colors[2], 0), (0.45, colors[1], op * 0.55), (0.9, colors[0], op), (1, colors[0], 0)])
    d = smooth(lower) + 'L' + smooth(list(reversed(upper)))[1:] + 'Z'
    doc.path(d, fill=g)
    gr = doc.lin([(0, colors[1], 0), (0.7, colors[0], op * 0.45), (1, colors[0], 0)])
    for _ in range(rays):
        i = rnd.random() * n
        k = int(i)
        t = i - k
        k = min(k, n - 1)
        x = lower[k][0] * (1 - t) + lower[k + 1][0] * t
        yl = lower[k][1] * (1 - t) + lower[k + 1][1] * t
        hh = height * rnd.uniform(0.7, 1.5) * (0.2 + 0.8 * math.sin(math.pi * i / n) ** 0.6)
        ww = rnd.uniform(0.8, 3.0)
        doc.rect(x, yl - hh, ww, hh + 2, fill=gr, opacity=round(rnd.uniform(0.3, 0.9), 2))


def water(doc, x, y, w, h, top=R2, bottom=INK, seed=1, lines=14, color=TEAL, op=0.35):
    doc.rect(x, y, w, h, fill=doc.lin([(0, top), (1, bottom)]))
    rnd = random.Random(seed)
    for _ in range(lines):
        yy = y + 2 + (h - 4) * rnd.random() ** 1.3
        ll = rnd.uniform(6, 26) * (0.4 + (yy - y) / h)
        xx = rnd.uniform(x, x + w - ll)
        doc.path(f'M{f(xx)},{f(yy)}h{f(ll)}', stroke=color, stroke_width=0.7,
                 opacity=round(op * rnd.uniform(0.4, 1), 2), stroke_linecap='round')


def reflection(doc, cx, y0, y1, color=GOLD, width=10, seed=3, op=0.6):
    rnd = random.Random(seed)
    yy = y0 + 1.5
    while yy < y1:
        t = (yy - y0) / max(1, (y1 - y0))
        ww = width * (0.4 + 0.9 * rnd.random()) * (1 + t * 0.8)
        doc.path(f'M{f(cx-ww/2+rnd.uniform(-2,2))},{f(yy)}h{f(ww)}', stroke=color, stroke_width=1.1,
                 opacity=round(op * (1 - t * 0.7), 2), stroke_linecap='round')
        yy += 2.2 + t * 2.5


def fog(doc, cx, cy, rx, ry, color=SEC, op=0.18):
    g = doc.rad([(0, color, op), (0.6, color, op * 0.5), (1, color, 0)])
    doc.ellipse(cx, cy, rx, ry, fill=g)


def hatch(doc, x0, y0, x1, y1, step=3.5, angle=-35, color=SEC, op=0.08, sw=0.5):
    """Гравюрные штрихи в прямоугольнике."""
    t = math.tan(math.radians(angle))
    d = []
    h = y1 - y0
    x = x0 - abs(h * t)
    while x < x1:
        xa, xb = x, x + h * -t
        d.append(f'M{f(xa)},{f(y1)}L{f(xb)},{f(y0)}')
        x += step
    doc.path(''.join(d), stroke=color, stroke_width=sw, opacity=op, fill='none')


def hatch_h(doc, x0, y0, x1, y1, step=4, color=SEC, op=0.1, sw=0.5):
    d = ''.join(f'M{f(x0)},{f(y)}H{f(x1)}' for y in frange(y0, y1, step))
    doc.path(d, stroke=color, stroke_width=sw, opacity=op, fill='none')


def frange(a, b, s):
    while a < b:
        yield a
        a += s


def hatch_lines(doc, lines, color=SEC, op=0.12, sw=0.5):
    d = ''.join(f'M{f(a)},{f(b)}L{f(c)},{f(e)}' for a, b, c, e in lines)
    doc.path(d, stroke=color, stroke_width=sw, opacity=op, fill='none', stroke_linecap='round')


def window(doc, x, y, w, h, frame=FORE, light=WARM, glow_r=None):
    if glow_r:
        glow(doc, x + w / 2, y + h / 2, glow_r, light, 0.35)
    doc.rect(x, y, w, h, fill=light)
    doc.rect(x, y + h * 0.42, w, h * 0.14, fill=frame, opacity=0.8)
    doc.rect(x + w * 0.44, y, w * 0.12, h, fill=frame, opacity=0.8)


def izba(doc, x, yb, w, h, body=NEAR, roof=FORE, trim=GOLD, lit=True, chimney=True, seed=0):
    """Изба фасадом-фронтоном. x — левый край, yb — земля."""
    rh = h * 0.55
    doc.rect(x, yb - h, w, h, fill=body)
    # бревна
    d = ''.join(f'M{f(x)},{f(yb - h + i * h / 6)}h{f(w)}' for i in range(1, 6))
    doc.path(d, stroke=INK, stroke_width=0.6, opacity=0.5)
    if chimney:
        doc.rect(x + w * 0.68, yb - h - rh * 0.85, w * 0.1, rh * 0.6, fill=roof)
    doc.poly([(x - w * 0.12, yb - h + 1), (x + w / 2, yb - h - rh), (x + w * 1.12, yb - h + 1)], fill=roof)
    # причелины — тонкий золотой резной кант
    doc.line([(x - w * 0.08, yb - h - 1), (x + w / 2, yb - h - rh + 3), (x + w * 1.08, yb - h - 1)],
             stroke=trim, stroke_width=0.8, opacity=0.55)
    doc.circle(x + w / 2, yb - h - rh * 0.45, w * 0.07, fill=trim, opacity=0.35)
    ww, wh = w * 0.26, h * 0.36
    if lit:
        window(doc, x + w / 2 - ww / 2, yb - h * 0.72, ww, wh, frame=body, glow_r=w * 0.6)
    else:
        doc.rect(x + w / 2 - ww / 2, yb - h * 0.72, ww, wh, fill=INK)
    doc.rect(x + w / 2 - ww / 2 - 1.2, yb - h * 0.72 + wh, ww + 2.4, 1.4, fill=trim, opacity=0.5)


def onion(doc, cx, yb, w, h, fill, cross=GOLD):
    """Луковичная главка: основание yb, ширина w, высота h."""
    d = (f'M{f(cx - w*0.32)},{f(yb)}C{f(cx - w*0.62)},{f(yb - h*0.35)} {f(cx - w*0.5)},{f(yb - h*0.62)} {f(cx)},{f(yb - h)}'
         f'C{f(cx + w*0.5)},{f(yb - h*0.62)} {f(cx + w*0.62)},{f(yb - h*0.35)} {f(cx + w*0.32)},{f(yb)}Z')
    doc.path(d, fill=fill)
    if cross:
        doc.path(f'M{f(cx)},{f(yb-h)}v{f(-h*0.55)}M{f(cx-w*0.17)},{f(yb-h-h*0.38)}h{f(w*0.34)}',
                 stroke=cross, stroke_width=max(0.6, w * 0.05), fill='none')


def church(doc, cx, yb, s, body=MID, dome=GOLD, roof=NEAR):
    """Небольшой храм: четверик, барабан, луковица."""
    doc.rect(cx - 9 * s, yb - 14 * s, 18 * s, 14 * s, fill=body)
    doc.poly([(cx - 10 * s, yb - 14 * s), (cx, yb - 19 * s), (cx + 10 * s, yb - 14 * s)], fill=roof)
    doc.rect(cx - 3.2 * s, yb - 25 * s, 6.4 * s, 8 * s, fill=body)
    onion(doc, cx, yb - 25 * s, 7 * s, 8 * s, dome)
    doc.rect(cx + 9 * s, yb - 10 * s, 8 * s, 10 * s, fill=body)
    doc.poly([(cx + 9 * s, yb - 10 * s), (cx + 13 * s, yb - 13 * s), (cx + 17 * s, yb - 10 * s)], fill=roof)
    doc.rect(cx - 1.2 * s, yb - 11 * s, 2.4 * s, 4 * s, fill=WARM, opacity=0.8)


def birch(doc, x, yb, h, seed=0, lean=0, crown=True):
    rnd = random.Random(seed)
    w = h * 0.035
    doc.path(f'M{f(x-w)},{f(yb)}L{f(x+lean-w*0.5)},{f(yb-h)}L{f(x+lean+w*0.5)},{f(yb-h)}L{f(x+w)},{f(yb)}Z',
             fill=PARCH, opacity=0.85)
    d = ''
    for i in range(int(h / 7)):
        t = rnd.uniform(0.05, 0.95)
        yy = yb - h * t
        xx = x + lean * t
        d += f'M{f(xx - w*rnd.uniform(0.2,1))},{f(yy)}h{f(w*rnd.uniform(0.5,1.2))}'
    doc.path(d, stroke=INK, stroke_width=1.1, opacity=0.8)
    if crown:
        for _ in range(9):
            t = rnd.uniform(0.6, 1.05)
            cx = x + lean * t + rnd.uniform(-h * 0.18, h * 0.18)
            doc.ellipse(cx, yb - h * t, h * rnd.uniform(0.07, 0.12), h * rnd.uniform(0.05, 0.08),
                        fill=MOSS, opacity=round(rnd.uniform(0.5, 0.8), 2))


def reeds(doc, x0, x1, yb, hmin, hmax, n, seed, color=FORE, heads=True, head_color='#3A2E25'):
    rnd = random.Random(seed)
    d = ''
    hd = []
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        h = rnd.uniform(hmin, hmax)
        bend = rnd.uniform(-h * 0.2, h * 0.2)
        d += f'M{f(x)},{f(yb)}Q{f(x + bend * 0.2)},{f(yb - h * 0.6)} {f(x + bend)},{f(yb - h)}'
        if heads and rnd.random() < 0.35:
            hd.append((x + bend * 0.85, yb - h * 0.88, h))
    doc.path(d, stroke=color, stroke_width=1, fill='none', stroke_linecap='round')
    for x, y, h in hd:
        doc.ellipse(x, y, 1.3, h * 0.08, fill=head_color)


def grass(doc, x0, x1, yb, h, n, seed, color=FORE, sw=0.8, op=1):
    rnd = random.Random(seed)
    d = ''
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        hh = h * rnd.uniform(0.4, 1)
        b = rnd.uniform(-hh * 0.5, hh * 0.5)
        d += f'M{f(x)},{f(yb)}q{f(b*0.2)},{f(-hh*0.6)} {f(b)},{f(-hh)}'
    doc.path(d, stroke=color, stroke_width=sw, fill='none', opacity=op, stroke_linecap='round')


def frame_circle(doc, cx=60, cy=60, r=56, inner=None):
    """Рамка-медальон для эмблем существ."""
    bg = doc.rad([(0, R2), (0.75, R1), (1, INK)], cx=0.5, cy=0.42, r=0.6)
    doc.circle(cx, cy, r, fill=bg)
    return bg


def frame_ring(doc, cx=60, cy=60, r=56):
    doc.circle(cx, cy, r, fill='none', stroke=GOLD, stroke_width=1.6)
    doc.circle(cx, cy, r - 3.2, fill='none', stroke=GOLD, stroke_width=0.5, opacity=0.45)
    for a in (0, 90, 180, 270):
        x = cx + (r) * math.cos(math.radians(a - 90))
        y = cy + (r) * math.sin(math.radians(a - 90))
        sparkle(doc, x, y, 3.4, fill=GOLD)
    for a in (45, 135, 225, 315):
        x = cx + (r - 1.6) * math.cos(math.radians(a - 90))
        y = cy + (r - 1.6) * math.sin(math.radians(a - 90))
        doc.circle(x, y, 0.9, fill=GOLD, opacity=0.7)


def circle_ground(doc, cx, cy, r, y, fill, **kw):
    """Сегмент круга ниже y (земля внутри медальона)."""
    dy = y - cy
    if abs(dy) >= r:
        return
    dx = math.sqrt(r * r - dy * dy)
    large = 1 if dy < 0 else 0
    doc.path(f'M{f(cx - dx)},{f(y)}L{f(cx + dx)},{f(y)}A{f(r)},{f(r)} 0 {large} 1 {f(cx - dx)},{f(y)}Z', fill=fill, **kw)


def circle_ground_curve(doc, cx, cy, r, y, bulge, fill, **kw):
    """Сегмент с выпуклой верхней кромкой (холм внутри круга)."""
    dy = y - cy
    dx = math.sqrt(r * r - dy * dy)
    large = 1 if dy < 0 else 0
    doc.path(f'M{f(cx - dx)},{f(y)}Q{f(cx)},{f(y - bulge)} {f(cx + dx)},{f(y)}A{f(r)},{f(r)} 0 {large} 1 {f(cx - dx)},{f(y)}Z',
             fill=fill, **kw)


# ---- обрезка по медальону (без clipPath) -----------------------------------

def clip_circle(poly, cx=60, cy=60, r=55, n=120):
    """Многоугольник ∩ круг (выпуклый 120-угольник)."""
    clip = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return clip_convex(poly, clip)


def round_rect_poly(x, y, w, h, r, k=10):
    pts_ = []
    for (cx, cy, a0) in [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)]:
        for j in range(k + 1):
            a = math.radians(a0 + 90 * j / k)
            pts_.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts_


def clip_convex(poly, clip):
    """Sutherland–Hodgman: многоугольник ∩ выпуклый многоугольник (по часовой в экранных осях)."""
    n = len(clip)

    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def inter(p, q, a, b):
        x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    out = list(poly)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        inp, out = out, []
        if not inp:
            break
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    out.append(inter(s, e, a, b))
                out.append(e)
            elif inside(s, a, b):
                out.append(inter(s, e, a, b))
            s = e
    # прореживание почти совпадающих точек
    res = []
    for p in out:
        if not res or abs(p[0] - res[-1][0]) + abs(p[1] - res[-1][1]) > 0.25:
            res.append(p)
    return res


def cpoly(doc, poly, cx=60, cy=60, r=55, **kw):
    p = clip_circle(poly, cx, cy, r)
    if len(p) >= 3:
        doc.poly(p, **kw)


def sample(points, k=6):
    """Сглаженная Catmull-Rom кривая → ломаная (для обрезки)."""
    out = []
    n = len(points)
    for i in range(n - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < n else p2
        for j in range(k):
            t = j / k
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(points[-1])
    return out


def chord(y, cx=60, cy=60, r=55):
    dy = y - cy
    if abs(dy) >= r:
        return None
    dx = math.sqrt(r * r - dy * dy)
    return cx - dx, cx + dx


def chords(doc, ys, inset=0, **kw):
    d = ''
    for y in ys:
        c = chord(y)
        if c:
            d += f'M{f(c[0] + inset)},{f(y)}H{f(c[1] - inset)}'
    doc.path(d, **kw)


def in_circle_stars(doc, n, seed, ymax=60, cx=60, cy=60, r=50, rmax=0.9):
    rnd = random.Random(seed)
    k = 0
    while k < n:
        x, y = rnd.uniform(cx - r, cx + r), rnd.uniform(cy - r, ymax)
        if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
            doc.circle(x, y, rnd.uniform(0.35, rmax), fill=PARCH, opacity=round(rnd.uniform(0.3, 0.9), 2))
            k += 1

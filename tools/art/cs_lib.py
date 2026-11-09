"""Мини-библиотека для вариантов стиля существ «Путника» (flutter_svg-совместимый SVG).

Разрешено только: path, rect, circle, ellipse, polygon, polyline, g, defs, linearGradient, radialGradient, stop.
"""
import math

LEAD = '#070B10'
INK = '#0E1621'
PARCH = '#E9DFC8'
TURQ = '#3FD6CC'
CORAL = '#E07A5F'
DANGER = '#FF6B7A'
CX = 180


def f(v):
    s = f'{v:.1f}'
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def lt(c, t=.3):
    return mix(c, '#FFFFFF', t)


def dk(c, t=.3):
    return mix(c, '#04070C', t)


# ---------------------------------------------------------------- геометрия
def P(p, closed=True, prec=1):
    if prec == 0:
        s = 'M' + ' '.join(f'{round(x)},{round(y)}' for x, y in p)
        return s + ('Z' if closed else '')
    s = 'M' + ' '.join(f'{f(x)},{f(y)}' for x, y in p)
    return s + ('Z' if closed else '')


def smooth(p, closed=True, k=1 / 6):
    n = len(p)
    if n < 3:
        return P(p, closed)
    d = [f'M{f(p[0][0])},{f(p[0][1])}']
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = p[(i - 1) % n] if (closed or i > 0) else p[i]
        p1 = p[i]
        p2 = p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k)
        c2 = (p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k)
        d.append(f'C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}')
    return ''.join(d) + ('Z' if closed else '')


def mir(p, cx=CX):
    return [(2 * cx - x, y) for x, y in p]


def sym(half, cx=CX):
    """half идёт от верхней точки на оси по левой стороне вниз до нижней точки на оси."""
    return half + mir(half[::-1][1:-1], cx)


def taper(line, w0, w1, wm=None):
    """Полоса переменной ширины вдоль ломаной -> многоугольник."""
    n = len(line)
    L, R = [], []
    for i, (x, y) in enumerate(line):
        a = line[max(i - 1, 0)]
        b = line[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        h = math.hypot(dx, dy) or 1
        nx, ny = -dy / h, dx / h
        t = i / (n - 1)
        if wm is None:
            w = w0 + (w1 - w0) * t
        else:
            w = (w0 + (wm - w0) * t * 2) if t < .5 else (wm + (w1 - wm) * (t - .5) * 2)
        L.append((x + nx * w / 2, y + ny * w / 2))
        R.append((x - nx * w / 2, y - ny * w / 2))
    return L + R[::-1]


def tf(p, x, y, ang=0.0, s=1.0, sx=None):
    ca, sa = math.cos(ang), math.sin(ang)
    sx = s if sx is None else sx
    return [(x + (px * sx) * ca - (py * s) * sa, y + (px * sx) * sa + (py * s) * ca) for px, py in p]


def ell(cx, cy, rx, ry, n=24, a0=0.0, a1=2 * math.pi, rot=0.0):
    out = []
    for i in range(n):
        t = a0 + (a1 - a0) * i / (n - (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1))
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def drop_pts(L, w):
    """Капля-мазок в локальных координатах: хвост в (0,0), голова в сторону +x."""
    return [(0, 0), (.3 * L, .1 * w), (.55 * L, .38 * w), (.78 * L, .5 * w), (.95 * L, .38 * w), (L, 0),
            (.95 * L, -.38 * w), (.78 * L, -.5 * w), (.55 * L, -.38 * w), (.3 * L, -.1 * w)]


def drop(x, y, ang, L, w):
    """Капля-мазок: хвост в (x,y), круглая голова по направлению ang. Три кубики."""
    q = [(.35 * L, .14 * w), (.56 * L, .5 * w), (.8 * L, .5 * w), (1.07 * L, .5 * w), (1.07 * L, -.5 * w), (.8 * L, -.5 * w),
         (.56 * L, -.5 * w), (.35 * L, -.14 * w)]
    q = tf(q, x, y, ang)
    c = [f'{f(a)},{f(b)}' for a, b in q]
    return f'M{f(x)},{f(y)}C{c[0]} {c[1]} {c[2]}C{c[3]} {c[4]} {c[5]}C{c[6]} {c[7]} {f(x)},{f(y)}Z'


def leaf_pts(L, w, n=7):
    up = [(L * i / n, w * math.sin(math.pi * i / n) * (1 - .25 * i / n)) for i in range(n + 1)]
    lo = [(L * i / n, -w * math.sin(math.pi * i / n) * (1 - .25 * i / n)) for i in range(n - 1, 0, -1)]
    return up + lo


def leaf(x, y, ang, L, w):
    """Лист: две квадратичные дуги от (x,y) до кончика."""
    c1, tip, c2 = tf([(L * .45, w), (L, 0), (L * .45, -w)], x, y, ang)
    return f'M{f(x)},{f(y)}Q{f(c1[0])},{f(c1[1])} {f(tip[0])},{f(tip[1])}Q{f(c2[0])},{f(c2[1])} {f(x)},{f(y)}Z'


def spiral(cx, cy, r0, r1, turns, a0=0.0, n=30, sgn=1):
    out = []
    for i in range(n + 1):
        t = i / n
        a = a0 + sgn * t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


# ---------------------------------------------------------------- SVG
class Svg:
    def __init__(s, w=360, h=200):
        s.w, s.h = w, h
        s.defs, s.out, s.k = [], [], 0

    def _id(s):
        s.k += 1
        return f'g{s.k}'

    @staticmethod
    def _stops(stops):
        o = []
        for st in stops:
            off, col = st[0], st[1]
            op = '' if len(st) < 3 or st[2] >= 1 else f' stop-opacity="{f(st[2]) if st[2] >= .1 else "%.2f" % st[2]}"'
            o.append(f'<stop offset="{f(off) if off not in (0, 1) else int(off)}" stop-color="{col}"{op}/>')
        return ''.join(o)

    def lin(s, stops, x1=0, y1=0, x2=0, y2=1, user=False):
        i = s._id()
        u = ' gradientUnits="userSpaceOnUse"' if user else ''
        s.defs.append(f'<linearGradient id="{i}" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}"{u}>'
                      + s._stops(stops) + '</linearGradient>')
        return f'url(#{i})'

    def rad(s, stops, cx=.5, cy=.5, r=.5, user=False):
        i = s._id()
        u = ' gradientUnits="userSpaceOnUse"' if user else ''
        s.defs.append(f'<radialGradient id="{i}" cx="{f(cx) if user else cx}" cy="{f(cy) if user else cy}" r="{f(r) if user else r}"{u}>'
                      + s._stops(stops) + '</radialGradient>')
        return f'url(#{i})'

    def glow(s, x, y, r, col, op=.6, mid=.35):
        g = s.rad([(0, col, op), (.5, col, op * mid), (1, col, 0)], x, y, r, user=True)
        s.el('circle', cx=x, cy=y, r=r, fill=g)

    def el(s, tag, **a):
        parts = []
        for k, v in a.items():
            if v is None:
                continue
            k = k.rstrip('_').replace('_', '-')
            if isinstance(v, float):
                v = f(v) if abs(v) >= .1 or v == 0 else ('%.2f' % v)
            parts.append(f'{k}="{v}"')
        s.out.append(f'<{tag} ' + ' '.join(parts) + '/>')

    def path(s, d, fill='none', **a):
        s.el('path', d=d, fill=fill, **a)

    def poly(s, p, fill, **a):
        s.el('path', d=P(p), fill=fill, **a)

    def sm(s, p, fill, closed=True, **a):
        s.el('path', d=smooth(p, closed), fill=fill, **a)

    def line(s, p, col, w, smooth_=False, **a):
        d = smooth(p, False) if smooth_ else P(p, False)
        s.el('path', d=d, fill='none', stroke=col, stroke_width=w, stroke_linecap='round', stroke_linejoin='round', **a)

    def lines(s, segs, col, w, **a):
        if segs:
            s.el('path', d=''.join(P(q, False, 0) for q in segs), fill='none', stroke=col, stroke_width=w,
                 stroke_linecap='round', stroke_linejoin='round', **a)

    def g(s, **a):
        parts = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
        s.out.append(f'<g {parts}>' if parts else '<g>')

    def end(s):
        s.out.append('</g>')

    def render(s):
        d = ('<defs>' + ''.join(s.defs) + '</defs>') if s.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" width="{s.w}" height="{s.h}">'
                + d + ''.join(s.out) + '</svg>')


ALLOWED = {'svg', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'g', 'linearGradient',
           'radialGradient', 'stop', 'defs'}


def check(name, svg, limit=30 * 1024):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg)
    bad = {e.tag.split('}')[1] for e in root.iter()} - ALLOWED
    assert not bad, f'{name}: запрещённые теги {bad}'
    assert root.get('viewBox'), name
    assert len(svg.encode()) <= limit, f'{name}: {len(svg.encode())} байт'
    return len(svg.encode())

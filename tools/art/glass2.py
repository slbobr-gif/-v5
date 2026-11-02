"""Витраж v2: «настоящее» стекло — свинец по форме, роспись по стеклу (гризайль).

Только элементы, которые понимает flutter_svg: path, rect, circle, ellipse, polygon,
g, linearGradient, radialGradient, stop, defs. Без filter/mask/clipPath/style.

Приёмы:
* piece()  — стекло: заливка «антикварным» градиентом (полосы/свечение) + свинцовая обводка;
* paint()  — роспись: полупрозрачная заливка (тени-«матировка», блики);
* line()   — роспись кистью: сужающийся мазок (залитый контур, а не stroke);
* dots()   — точечная роспись (щетина, крапины);
* smooth() — замкнутый/открытый сплайн Катмулла — Рома через точки; (x, y, 1) — острый угол.
"""
import math

LEAD = '#070B10'


def f(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    if s.startswith('0.'):
        s = s[1:]
    elif s.startswith('-0.'):
        s = '-' + s[2:]
    return s


def hx(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(a, b, t):
    A, B = hx(a), hx(b)
    return to_hex(tuple(A[i] + (B[i] - A[i]) * t for i in range(3)))


def light(c, k):
    return mix(c, '#FFFFFF', k)


def dark(c, k):
    return mix(c, '#000000', k)


def _pts(spec):
    out = []
    for p in spec:
        out.append((float(p[0]), float(p[1]), len(p) > 2 and bool(p[2])))
    return out


def smooth(spec, closed=True, t=1.0):
    """Путь через точки; точка (x, y, 1) — острый угол."""
    P = _pts(spec)
    n = len(P)
    if n < 2:
        return ''
    d = [f'M{f(P[0][0])} {f(P[0][1])}']
    segs = n if closed else n - 1
    for i in range(segs):
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else p2
        if p1[2]:
            c1 = (p1[0], p1[1])
        else:
            c1 = (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
        if p2[2]:
            c2 = (p2[0], p2[1])
        else:
            c2 = (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
        if p1[2] and p2[2]:
            d.append(f'L{f(p2[0])} {f(p2[1])}')
        else:
            d.append(f'C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}')
    if closed:
        d.append('Z')
    return ''.join(d)


def poly(pts, closed=True):
    s = 'M' + ' '.join(f'{f(x)} {f(y)}' for x, y in pts)
    return s + ('Z' if closed else '')


def sample(spec, closed=False, per=8, t=1.0):
    """Точки сплайна (для мазков и разбиения)."""
    P = _pts(spec)
    n = len(P)
    out = []
    segs = n if closed else n - 1
    for i in range(segs):
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0], p1[1]) if p1[2] else (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
        c2 = (p2[0], p2[1]) if p2[2] else (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
        for k in range(per):
            u = k / per
            a = (1 - u) ** 3
            b = 3 * (1 - u) ** 2 * u
            c = 3 * (1 - u) * u * u
            e = u ** 3
            out.append((a * p1[0] + b * c1[0] + c * c2[0] + e * p2[0], a * p1[1] + b * c1[1] + c * c2[1] + e * p2[1]))
    if not closed:
        out.append((P[-1][0], P[-1][1]))
    return out


class Glass:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.defs = []
        self.body = []
        self.gid = {}

    # ---------- градиенты «стекла» ----------
    def grad(self, c, var='r'):
        q = 6
        c = '#%02X%02X%02X' % tuple(min(255, int(round(v / q) * q)) for v in hx(c))
        key = (c, var)
        if key in self.gid:
            return self.gid[key]
        gid = 'g%d' % len(self.gid)
        self.gid[key] = gid
        if var == 'r':      # свечение изнутри: светлее у центра-сверху
            self.defs.append(f'<radialGradient id="{gid}" cx=".42" cy=".36" r=".75">'
                             f'<stop offset="0" stop-color="{light(c, .30)}"/><stop offset=".55" stop-color="{c}"/>'
                             f'<stop offset="1" stop-color="{dark(c, .22)}"/></radialGradient>')
        elif var == 'R':    # сильное свечение (у солнца, у ореола)
            self.defs.append(f'<radialGradient id="{gid}" cx=".5" cy=".5" r=".7">'
                             f'<stop offset="0" stop-color="{light(c, .55)}"/><stop offset=".6" stop-color="{c}"/>'
                             f'<stop offset="1" stop-color="{dark(c, .12)}"/></radialGradient>')
        elif var in ('a', 'b', 'v', 'h'):   # «антикварное» стекло с полосами
            x1, y1, x2, y2 = {'a': (0, 0, 1, 1), 'b': (1, 0, 0, 1), 'v': (0, 0, 0, 1), 'h': (0, 0, 1, 0)}[var]
            self.defs.append(f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
                             f'<stop offset="0" stop-color="{dark(c, .18)}"/><stop offset=".3" stop-color="{c}"/>'
                             f'<stop offset=".48" stop-color="{light(c, .18)}"/><stop offset=".62" stop-color="{c}"/>'
                             f'<stop offset=".85" stop-color="{light(c, .08)}"/><stop offset="1" stop-color="{dark(c, .2)}"/></linearGradient>')
        elif var == 's':    # мягкий переход сверху вниз (кожа, лицо)
            self.defs.append(f'<linearGradient id="{gid}" x1=".1" y1="0" x2=".9" y2="1">'
                             f'<stop offset="0" stop-color="{light(c, .22)}"/><stop offset=".5" stop-color="{c}"/>'
                             f'<stop offset="1" stop-color="{dark(c, .14)}"/></linearGradient>')
        return gid

    def lingrad(self, stops, x1=0, y1=0, x2=0, y2=1, units=None):
        gid = 'g%d' % (len(self.gid))
        self.gid[('custom', gid)] = gid
        u = f' gradientUnits="userSpaceOnUse"' if units else ''
        s = ''.join(f'<stop offset="{f(o)}" stop-color="{c}"' + (f' stop-opacity="{f(a)}"' if a is not None and a < 1 else '') + '/>'
                    for o, c, a in [(st + (None,))[:3] for st in stops])
        self.defs.append(f'<linearGradient id="{gid}" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}"{u}>{s}</linearGradient>')
        return gid

    def radgrad(self, stops, cx=.5, cy=.5, r=.5, units=None):
        gid = 'g%d' % (len(self.gid))
        self.gid[('custom', gid)] = gid
        u = f' gradientUnits="userSpaceOnUse"' if units else ''
        s = ''.join(f'<stop offset="{f(o)}" stop-color="{c}"' + (f' stop-opacity="{f(a)}"' if a is not None and a < 1 else '') + '/>'
                    for o, c, a in [(st + (None,))[:3] for st in stops])
        self.defs.append(f'<radialGradient id="{gid}" cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"{u}>{s}</radialGradient>')
        return gid

    # ---------- элементы ----------
    def piece(self, d, c, var='r', lead=3.0):
        fill = f'url(#{self.grad(c, var)})' if var else c
        st = f' stroke="{LEAD}" stroke-width="{f(lead)}" stroke-linejoin="round"' if lead else ''
        self.body.append(f'<path d="{d}" fill="{fill}"{st}/>')

    def flat(self, d, c, op=None, lead=0.0):
        o = f' opacity="{f(op)}"' if op is not None and op < 1 else ''
        st = f' stroke="{LEAD}" stroke-width="{f(lead)}" stroke-linejoin="round"' if lead else ''
        self.body.append(f'<path d="{d}" fill="{c}"{o}{st}/>')

    def gfill(self, d, gid, op=None):
        o = f' opacity="{f(op)}"' if op is not None and op < 1 else ''
        self.body.append(f'<path d="{d}" fill="url(#{gid})"{o}/>')

    def leadline(self, d, w=3.0, c=LEAD, op=None):
        o = f' opacity="{f(op)}"' if op is not None and op < 1 else ''
        self.body.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{f(w)}" stroke-linecap="round" stroke-linejoin="round"{o}/>')

    def paint(self, d, c='#2A160C', op=.25):
        self.flat(d, c, op)

    def line(self, spec, w=2.0, c='#1E120B', op=.85, w0=.15, per=6, p=.8, t=1.0):
        """Сужающийся мазок по центральной линии spec."""
        pts = sample(spec, closed=False, per=per, t=t)
        n = len(pts)
        if n < 2:
            return
        L, R = [], []
        for i, (x, y) in enumerate(pts):
            a = pts[max(0, i - 1)]
            b = pts[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1
            nx, ny = -dy / ln, dx / ln
            u = i / (n - 1)
            wd = w * (w0 + (1 - w0) * (math.sin(math.pi * u) ** p)) / 2
            L.append((x + nx * wd, y + ny * wd))
            R.append((x - nx * wd, y - ny * wd))
        self.flat(poly(L + R[::-1]), c, op)

    def soft(self, cx, cy, rx, ry, c, op, rot=0, core=0.0):
        """Мягкое пятно росписи (матировка/блик): радиальный градиент к прозрачности."""
        key = ('soft', c, round(op, 2), core)
        if key not in self.gid:
            gid = 'g%d' % len(self.gid)
            self.gid[key] = gid
            self.defs.append(f'<radialGradient id="{gid}"><stop offset="{f(core)}" stop-color="{c}" stop-opacity="{f(op)}"/>'
                             f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
        tr = f' transform="rotate({f(rot)} {f(cx)} {f(cy)})"' if rot else ''
        self.body.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="url(#{self.gid[key]})"{tr}/>')

    def fade(self, d, c, op, x1=0, y1=0, x2=1, y2=0):
        """Заливка с растушёвкой: от прозрачного (x1,y1) к op (x2,y2) в рамке фигуры."""
        key = ('fade', c, round(op, 2), x1, y1, x2, y2)
        if key not in self.gid:
            gid = 'g%d' % len(self.gid)
            self.gid[key] = gid
            self.defs.append(f'<linearGradient id="{gid}" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}">'
                             f'<stop offset="0" stop-color="{c}" stop-opacity="0"/><stop offset="1" stop-color="{c}" stop-opacity="{f(op)}"/></linearGradient>')
        self.body.append(f'<path d="{d}" fill="url(#{self.gid[key]})"/>')

    def dots(self, pts, r=.7, c='#2A160C', op=.4):
        d = ''.join(f'M{f(x)} {f(y)}h.1' for x, y in pts)
        o = f' opacity="{f(op)}"' if op < 1 else ''
        self.body.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{f(r * 2)}" stroke-linecap="round"{o}/>')

    def raw(self, s):
        self.body.append(s)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}">'
                f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')


FORBIDDEN = ('<filter', '<mask', '<clipPath', '<pattern', '<text', '<image', '<use', 'style=', '<style', 'foreignObject')


def check(svg):
    bad = [t for t in FORBIDDEN if t in svg]
    return bad

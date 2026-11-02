"""Витражная библиотека «Путника»: осколки, свинец, подсветка, мозаика Вороного.

Только элементы flutter_svg: path, circle, ellipse, g, linearGradient, radialGradient, stop, defs.
Свинец — отдельные контуры, выводимые ПОСЛЕ заливок слоя (lead_flush), поэтому подсветка
(радиальные свечения) лежит под свинцом, а свинец остаётся тёмным.
"""
import math
import random

LEAD = '#070B10'

# ---- палитра витража (docs/v5/07 «Витражный стиль») ---------------------------------
TURQ = '#2BC4BA'
BLUE = '#1B4F8C'
ULTRA = '#2B3E9E'
EMER = '#1F9E6B'
VIOL = '#5B3FA0'
CORAL = '#C8454F'
AMBER = '#F0A24A'
MILK = '#EDE6D2'
NIGHT = '#0B1424'
HAIR = '#B58A52'
HAIR_HI = '#D2AA6E'
SKIN = '#E7AD84'
SKIN_SH = '#C98B62'
SKIN_HI = '#F2C79E'


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def lighten(c, t=0.3):
    return mix(c, '#E8FFFB', t)


def darken(c, t=0.3):
    return mix(c, '#04070C', t)


def num(v, prec=0):
    s = f'{v:.{prec}f}'
    if prec and '.' in s:
        s = s.rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s


# ---- геометрия --------------------------------------------------------------------
def centroid(p):
    return sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p)


def clip_half(poly, px, py, nx, ny):
    """Оставить точки с (x-px)*nx + (y-py)*ny <= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da = (a[0] - px) * nx + (a[1] - py) * ny
        db = (b[0] - px) * nx + (b[1] - py) * ny
        if da <= 0:
            out.append(a)
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def clean(poly, eps=0.6):
    res = []
    for p in poly:
        if not res or abs(p[0] - res[-1][0]) + abs(p[1] - res[-1][1]) > eps:
            res.append(p)
    if len(res) > 1 and abs(res[0][0] - res[-1][0]) + abs(res[0][1] - res[-1][1]) <= eps:
        res.pop()
    return res


def voronoi(region, seeds, eps=0.8):
    cells = []
    for i, (sx, sy) in enumerate(seeds):
        poly = list(region)
        order = sorted(range(len(seeds)), key=lambda j: (seeds[j][0] - sx) ** 2 + (seeds[j][1] - sy) ** 2)
        for j in order:
            if j == i:
                continue
            tx, ty = seeds[j]
            poly = clip_half(poly, (sx + tx) / 2, (sy + ty) / 2, tx - sx, ty - sy)
            if len(poly) < 3:
                break
        poly = clean(poly, eps)
        if len(poly) >= 3:
            cells.append(poly)
    return cells


def poisson(bbox, rfun, seed, tries=4000, accept=None, extra=()):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = bbox
    pts_ = list(extra)
    for _ in range(tries):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if accept and not accept(x, y):
            continue
        r = rfun(x, y)
        if all((x - a) ** 2 + (y - b) ** 2 >= r * r for a, b in pts_):
            pts_.append((x, y))
    return pts_[len(extra):]


def circle_poly(cx, cy, r, n=28, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * i / n), cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def ellipse_poly(cx, cy, rx, ry, n=28, rot=0.0):
    return [(cx + rx * math.cos(rot + 2 * math.pi * i / n), cy + ry * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def rect_poly(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def arch_params(x0, x1, ysp, yapex, ybot, R=None):
    W = x1 - x0
    if R is None:
        R = W * 0.7
    return dict(x0=x0, x1=x1, ysp=ysp, ybot=ybot, R=R, W=W)


def arch_poly(P, inset=0.0, n=12, side=4):
    """Корректная реализация арки (замкнутый многоугольник). Левая дуга — центр справа
    от левой пяты, правая — зеркальная."""
    x0, x1, ysp, ybot, R, W = P['x0'], P['x1'], P['ysp'], P['ybot'], P['R'], P['W']
    cl = (x0 + R, ysp)
    cr = (x1 - R, ysp)
    r = R - inset
    a_apex = math.acos(max(-1.0, min(1.0, (W / 2 - R) / r)))  # угол от +x к вершине (против часовой, вверх)
    out = []
    for i in range(side):
        out.append((x0 + inset, ybot - inset - (ybot - inset - ysp) * i / side))
    for i in range(n + 1):
        a = math.pi - (math.pi - a_apex) * i / n
        out.append((cl[0] + r * math.cos(a), cl[1] - r * math.sin(a)))
    # правая дуга зеркальна левой
    left_arc = out[side:]
    mirror = [((x0 + x1) - x, y) for x, y in reversed(left_arc[:-1])]
    out += mirror
    for i in range(side):
        out.append((x1 - inset, ysp + (ybot - inset - ysp) * (i + 1) / side))
    return out


def clip_convex(poly, clip):
    """Многоугольник ∩ выпуклый многоугольник (обход по часовой в экранных осях)."""
    out = list(poly)
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        # оставляем точки справа от ребра a->b (по часовой): cross >= 0
        nx, ny = (b[1] - a[1]), -(b[0] - a[0])  # нормаль наружу
        out = clip_half(out, a[0], a[1], nx, ny)
        if len(out) < 3:
            return []
    return clean(out, 0.4)


def chain_quads(joints, widths):
    """Четырёхугольные звенья вдоль ломаной с общими (биссекторными) срезами.
    Возвращает список (quad, left_edge_pts, right_edge_pts)."""
    n = len(joints)
    dirs = []
    for i in range(n - 1):
        dx, dy = joints[i + 1][0] - joints[i][0], joints[i + 1][1] - joints[i][1]
        L = math.hypot(dx, dy) or 1
        dirs.append((dx / L, dy / L))
    sides = []
    for i in range(n):
        if i == 0:
            d = dirs[0]
        elif i == n - 1:
            d = dirs[-1]
        else:
            d = (dirs[i - 1][0] + dirs[i][0], dirs[i - 1][1] + dirs[i][1])
            L = math.hypot(*d) or 1
            d = (d[0] / L, d[1] / L)
        nx, ny = -d[1], d[0]
        k = 1.0
        if 0 < i < n - 1:
            c = d[0] * dirs[i][0] + d[1] * dirs[i][1]
            k = 1 / max(0.6, c)
        h = widths[i] / 2 * k
        sides.append(((joints[i][0] + nx * h, joints[i][1] + ny * h), (joints[i][0] - nx * h, joints[i][1] - ny * h)))
    quads = []
    for i in range(n - 1):
        a1, b1 = sides[i]
        a2, b2 = sides[i + 1]
        quads.append([a1, a2, b2, b1])
    return quads, sides


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


class Glass:
    def __init__(self, w, h, prefix='g', prec=0, lw=1.6, light=None, bg=LEAD):
        self.w, self.h = w, h
        self.prefix = prefix
        self.prec = prec
        self.lw = lw
        self.light = light
        self.defs = []
        self.body = []
        self.cache = {}
        self.n = 0
        self.leads = {}
        self.post = []
        self._pend = None
        self.gamt = 0.30
        self.gmin = 90
        if bg:
            self.body.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')

    # ---- форматирование
    def N(self, v):
        return num(v, self.prec)

    def P(self, p):
        return ' '.join(f'{self.N(x)},{self.N(y)}' for x, y in p)

    def D(self, p):
        return 'M' + self.P(p) + 'Z'

    def _gid(self):
        self.n += 1
        return f'{self.prefix}{self.n}'

    # ---- градиенты
    def grad(self, base, d):
        key = ('l', base, d)
        if key in self.cache:
            return self.cache[key]
        gid = self._gid()
        ux, uy = d
        x1, y1, x2, y2 = 0.5 - ux / 2, 0.5 - uy / 2, 0.5 + ux / 2, 0.5 + uy / 2
        self.defs.append(
            f'<linearGradient id="{gid}" x1="{num(x1, 1)}" y1="{num(y1, 1)}" x2="{num(x2, 1)}" y2="{num(y2, 1)}">'
            f'<stop offset="0" stop-color="{darken(base, 0.10)}"/><stop offset="1" stop-color="{lighten(base, self.gamt)}"/></linearGradient>')
        self.cache[key] = f'url(#{gid})'
        return self.cache[key]

    def radial(self, stops, cx=0.5, cy=0.5, r=0.5):
        key = ('r', tuple(stops), cx, cy, r)
        if key in self.cache:
            return self.cache[key]
        gid = self._gid()
        st = ''
        for s in stops:
            op = '' if len(s) < 3 or s[2] >= 1 else f' stop-opacity="{num(s[2], 2)}"'
            st += f'<stop offset="{num(s[0], 2)}" stop-color="{s[1]}"{op}/>'
        self.defs.append(f'<radialGradient id="{gid}" cx="{num(cx, 2)}" cy="{num(cy, 2)}" r="{num(r, 2)}">{st}</radialGradient>')
        self.cache[key] = f'url(#{gid})'
        return self.cache[key]

    def linear(self, stops, x1=0, y1=0, x2=0, y2=1):
        key = ('L', tuple(stops), x1, y1, x2, y2)
        if key in self.cache:
            return self.cache[key]
        gid = self._gid()
        st = ''
        for s in stops:
            op = '' if len(s) < 3 or s[2] >= 1 else f' stop-opacity="{num(s[2], 2)}"'
            st += f'<stop offset="{num(s[0], 2)}" stop-color="{s[1]}"{op}/>'
        self.defs.append(f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{st}</linearGradient>')
        self.cache[key] = f'url(#{gid})'
        return self.cache[key]

    def _dir(self, c):
        """Четыре диагонали: светлая сторона осколка смотрит на источник света."""
        if not self.light:
            return (1, -1)
        vx, vy = self.light[0] - c[0], self.light[1] - c[1]
        return (1 if vx >= 0 else -1, 1 if vy >= 0 else -1)

    # ---- вывод
    def _emit(self, fill, d, op=None):
        key = (fill, op)
        if self._pend and self._pend[0] == key:
            self._pend[1].append(d)
            return
        self.flush()
        self._pend = (key, [d])

    def flush(self):
        if self._pend:
            (fill, op), ds = self._pend
            o = f' opacity="{num(op, 2)}"' if op is not None else ''
            self.body.append(f'<path fill="{fill}"{o} d="{"".join(ds)}"/>')
            self._pend = None

    def lead_add(self, d, lw):
        if lw:
            self.leads.setdefault(lw, []).append(d)

    def shard(self, p, color, lw=None, grad=True, d=None, op=None, nolead=False):
        """Осколок-многоугольник. grad: линейный градиент к источнику света."""
        lw = self.lw if lw is None else lw
        p = list(p)
        if grad and (self.light is not None or d) and area(p) >= self.gmin:
            fill = self.grad(color, d or self._dir(centroid(p)))
        else:
            fill = color
        dd = self.D(p)
        self._emit(fill, dd, op)
        if not nolead:
            self.lead_add(dd, lw)

    def rects(self, color, items, op=None):
        """Много мелких прямоугольников одного цвета одним path (окошки). items: (x, y, w, h)."""
        n = self.N
        d = ''.join(f'M{n(x)},{n(y)}h{n(w)}v{n(h)}h{n(-w)}z' for x, y, w, h in items)
        self._emit(color, d, op)

    def circle(self, cx, cy, r, color, lw=None, grad=True, d=None, op=None, nolead=False):
        self.flush()
        lw = self.lw if lw is None else lw
        fill = self.grad(color, d or self._dir((cx, cy))) if grad and (self.light or d) else color
        o = f' opacity="{num(op, 2)}"' if op is not None else ''
        self.body.append(f'<circle cx="{self.N(cx)}" cy="{self.N(cy)}" r="{self.N(r)}" fill="{fill}"{o}/>')
        if not nolead:
            self.lead_add(self._cd(cx, cy, r), lw)

    def _cd(self, cx, cy, r):
        n = self.N
        return f'M{n(cx - r)},{n(cy)}a{n(r)},{n(r)} 0 1,0 {n(2 * r)},0a{n(r)},{n(r)} 0 1,0 {n(-2 * r)},0Z'

    def lead_circle(self, cx, cy, r, lw=None):
        self.lead_add(self._cd(cx, cy, r), self.lw if lw is None else lw)

    def lead_line(self, p, lw=None, closed=False):
        d = 'M' + self.P(p) + ('Z' if closed else '')
        self.lead_add(d, self.lw if lw is None else lw)

    def glow(self, cx, cy, r, color, op=0.5, mid=0.45):
        self.flush()
        gr = self.radial([(0, color, op), (0.55, color, round(op * mid, 2)), (1, color, 0)])
        self.body.append(f'<circle cx="{self.N(cx)}" cy="{self.N(cy)}" r="{self.N(r)}" fill="{gr}"/>')

    def glow_e(self, cx, cy, rx, ry, color, op=0.5, mid=0.45):
        self.flush()
        gr = self.radial([(0, color, op), (0.55, color, round(op * mid, 2)), (1, color, 0)])
        self.body.append(f'<ellipse cx="{self.N(cx)}" cy="{self.N(cy)}" rx="{self.N(rx)}" ry="{self.N(ry)}" fill="{gr}"/>')

    # ---- после свинца: блики, искры, огоньки
    def blik(self, p, color='#E8FFFB', w=0.9, op=0.55):
        self.post.append((color, w, op, 'M' + self.P(p)))

    def flush_post(self):
        by = {}
        for color, w, op, d in self.post:
            by.setdefault((color, w, op), []).append(d)
        for (color, w, op), ds in by.items():
            self.body.append(f'<path d="{"".join(ds)}" fill="none" stroke="{color}" stroke-width="{num(w, 1)}" opacity="{num(op, 2)}" stroke-linecap="round" stroke-linejoin="round"/>')
        self.post = []

    def spark(self, x, y, r, color=MILK, op=0.9):
        """Ромб-блик после свинца (малая искра)."""
        self.flush()
        self._post_fill(color, op, [(x, y - r), (x + r * 0.45, y), (x, y + r), (x - r * 0.45, y)])

    def _post_fill(self, color, op, p):
        self.post_fills = getattr(self, 'post_fills', [])
        self.post_fills.append((color, op, self.D(p)))

    def lead_flush(self):
        self.flush()
        for lw, ds in self.leads.items():
            self.body.append(f'<path d="{"".join(ds)}" fill="none" stroke="{LEAD}" stroke-width="{num(lw, 1)}" stroke-linejoin="round" stroke-linecap="round"/>')
        self.leads = {}
        pf = getattr(self, 'post_fills', [])
        by = {}
        for color, op, d in pf:
            by.setdefault((color, op), []).append(d)
        for (color, op), ds in by.items():
            self.body.append(f'<path fill="{color}" opacity="{num(op, 2)}" d="{"".join(ds)}"/>')
        self.post_fills = []
        self.flush_post()

    # ---- мозаика
    def mosaic(self, region, seeds, colorfn, lw=None, grad=True, eps=0.8):
        cells = voronoi(region, seeds, eps)
        for i, c in enumerate(cells):
            cx, cy = centroid(c)
            col = colorfn(cx, cy, i)
            if col:
                self.shard(c, col, lw=lw, grad=grad)
        return cells

    def render(self):
        self.lead_flush()
        d = f'<defs>{"".join(self.defs)}</defs>' if self.defs else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}">'
                + d + ''.join(self.body) + '</svg>\n')


# ---- проверка запретов flutter_svg -----------------------------------------------
import re

FORBIDDEN = re.compile(
    r'<(filter|mask|clipPath|pattern|text|image|foreignObject|style|use|symbol|tspan)\b|\sstyle=|\swidth="\d+px|\sclip-path=|\sfilter=|\smask=',
    re.I)
ALLOWED = {'svg', 'defs', 'g', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'linearGradient', 'radialGradient', 'stop'}


def check_svg(name, svg, limit=25 * 1024):
    problems = []
    m = FORBIDDEN.search(svg)
    if m:
        problems.append(f'запрещено: {m.group(0)}')
    tags = set(re.findall(r'<([A-Za-z]+)', svg))
    extra = tags - ALLOWED
    if extra:
        problems.append(f'неразрешённые теги: {sorted(extra)}')
    if 'viewBox' not in svg[:300]:
        problems.append('нет viewBox')
    size = len(svg.encode('utf-8'))
    if size > limit:
        problems.append(f'размер {size} > {limit}')
    return size, problems

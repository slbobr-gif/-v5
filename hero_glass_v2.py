"""Сергей v2 — витраж «как в соборе»: свинец по форме, роспись лица, окно-кокошник.

Слева — дом: рассвет над Кремлём, берёза. Справа — Север: сияние, море, хвост кита.
Дорога от ног героя уходит к морю. За головой — ореол-компас.

Запуск: python3 tools/art/hero_glass_v2.py [out.svg]
"""
import math
import random
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from glass2 import Glass, smooth, poly, sample, mix, light, dark, f, LEAD, check

W, H = 600, 720
g = Glass(W, H)
rng = random.Random(7)

# ---------------------------------------------------------------- палитра
AMBER = '#F4B860'
CORAL = '#EE8A5C'
ROSE = '#D9607A'
MAUVE = '#A8589C'
VIOLET = '#6A4AA8'
INDIGO = '#3A3C96'
DEEP = '#24307A'
NIGHT = '#162050'
SKY_RAMP = [AMBER, CORAL, ROSE, MAUVE, VIOLET, INDIGO, DEEP, NIGHT]

TURQ = '#2BC4BA'
MEADOW = '#2FB57C'
MILK = '#EDE6D2'
RUBY = '#C8303E'
COBALT = '#1F4FA8'

SKIN = '#EDB58F'
SKIN_L = '#F6CDA8'
SKIN_D = '#D3906C'
HAIR = '#B58A52'
HAIR_L = '#D6AE72'
HAIR_D = '#8E6A3E'
HAIR_DD = '#6E4E2C'
JACK_L = '#5CD0DE'
JACK = '#31B4CC'
JACK_M = '#2592BE'
JACK_D = '#1B72AA'
JACK_DD = '#145890'
PACK = '#DC5E60'
PACK_D = '#A83E50'
STRAP = '#8A2E40'
ROLL = '#34D1C6'
PANTS = '#2B3E9E'
PANTS_L = '#3E56BC'
STEEL = '#C9D3DD'
SEPIA = '#22140C'
BROWN = '#7A3E26'
WARM_RIM = '#FFD9A8'
COOL_RIM = '#9FF2E6'


def ramp(t):
    t = max(0.0, min(1.0, t))
    x = t * (len(SKY_RAMP) - 1)
    i = min(int(x), len(SKY_RAMP) - 2)
    return mix(SKY_RAMP[i], SKY_RAMP[i + 1], x - i)


# ---------------------------------------------------------------- окно-кокошник
def arch_half(i, per=24):
    """Левая половина арки с отступом i: от низа слева вверх до вершины."""
    L, B = i, H - i
    ys = 262.0
    ay = i + 6.0
    P0 = (L, ys)
    A = (300.0, ay)
    P1 = (L + .5 * (300 - L), ys - .58 * (ys - ay))
    dx, dy = 1.0, -.58
    ln = math.hypot(dx, dy)
    dx, dy = dx / ln, dy / ln
    k1 = .55 * (ys - P1[1])
    k2 = .42 * (P1[0] - L)
    k3 = .42 * (300 - P1[0])
    k4 = .5 * (P1[1] - ay)
    c1 = [P0, (P0[0], P0[1] - k1), (P1[0] - dx * k2, P1[1] - dy * k2), P1]
    c2 = [P1, (P1[0] + dx * k3, P1[1] + dy * k3), (A[0], A[1] + k4), A]
    pts = [(L, B)]
    for k in range(1, 9):
        pts.append((L, B + (ys - B) * k / 8))
    for c in (c1, c2):
        for k in range(1, per + 1):
            u = k / per
            a, b, cc, e = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u ** 3
            pts.append((a * c[0][0] + b * c[1][0] + cc * c[2][0] + e * c[3][0],
                        a * c[0][1] + b * c[1][1] + cc * c[2][1] + e * c[3][1]))
    return pts


def arch_full(i):
    left = arch_half(i)
    right = [(W - x, y) for x, y in reversed(left)]
    return left + right[1:]


def arch_path(i):
    return poly(arch_full(i))


def resample(pts, n):
    """Равномерно по длине."""
    seg = [math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1)]
    tot = sum(seg)
    out = [pts[0]]
    acc, k = 0.0, 0
    for j in range(1, n):
        target = tot * j / n
        while acc + seg[k] < target:
            acc += seg[k]
            k += 1
        u = (target - acc) / seg[k]
        out.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * u, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * u))
    out.append(pts[-1])
    return out


WIN = 52  # внутренняя граница окна


# ---------------------------------------------------------------- небо: веер рассвета
SUN = (166.0, 446.0)


def sky():
    g.flat(f'M0 0H{W}V{H}H0Z', LEAD)
    radii = [34, 74, 128, 200, 300, 440, 760]
    n_rays = 17
    a0, a1 = math.radians(-196), math.radians(4)
    for ri in range(len(radii) - 1):
        r0, r1 = radii[ri], radii[ri + 1]
        for k in range(n_rays):
            t0 = a0 + (a1 - a0) * k / n_rays
            t1 = a0 + (a1 - a0) * (k + 1) / n_rays
            pts = []
            for s in range(4):
                a = t0 + (t1 - t0) * s / 3
                pts.append((SUN[0] + r0 * math.cos(a), SUN[1] + r0 * math.sin(a)))
            for s in range(4):
                a = t1 - (t1 - t0) * s / 3
                pts.append((SUN[0] + r1 * math.cos(a), SUN[1] + r1 * math.sin(a)))
            ang = (k + .5) / n_rays           # 0 — слева, 1 — справа
            rr = (r0 + r1) / 2
            t = .02 + rr / 520 * .5 + ang * .6
            t += (.05 if (k + ri) % 2 else -.035)
            c = ramp(t)
            var = 'R' if ri == 0 else ('a' if (k + ri) % 3 == 0 else ('b' if (k + ri) % 3 == 1 else 'r'))
            g.piece(poly(pts), c, var, 2.4)
    # солнце
    g.piece(smooth([(SUN[0] + 34 * math.cos(a), SUN[1] + 34 * math.sin(a))
                    for a in [math.radians(x) for x in range(0, 360, 30)]]), '#FFE6B8', 'R', 2.8)


def aurora():
    """Сияние справа: волнистые занавеси из узких лучей разной высоты."""
    curtains = [
        # x0, x1, низ занавеси y(x), высота лучей, лучей
        (414, 560, lambda x: 262 - (x - 414) * .52 + 16 * math.sin((x - 414) / 21), 118, 12),
        (432, 560, lambda x: 336 - (x - 432) * .28 + 9 * math.sin((x - 432) / 17 + 1), 62, 9),
    ]
    for ci, (x0, x1, base, hgt, n) in enumerate(curtains):
        xs = [x0]
        for k in range(n):
            xs.append(xs[-1] + (x1 - x0) / n * rng.uniform(.75, 1.25))
        xs[-1] = x1
        for k in range(n):
            xa, xb = xs[k], xs[k + 1]
            ya, yb = base(xa), base(xb)
            h = hgt * rng.uniform(.72, 1.15) * (1 - .2 * ci)
            lean = h * .16
            m1, m2 = rng.uniform(.26, .34), rng.uniform(.58, .7)

            def at(y0, frac, x):
                return (x + lean * frac, y0 - h * frac)
            a1, b1 = at(ya, m1, xa), at(yb, m1, xb)
            a2, b2 = at(ya, m2, xa), at(yb, m2, xb)
            ta, tb = at(ya, 1, xa), at(yb, rng.uniform(.88, 1.04), xb)
            tip = ((ta[0] + tb[0]) / 2 + 2, min(ta[1], tb[1]) - h * .1)
            g.piece(poly([(xa, ya), (xb, yb), b1, a1]), mix('#7AF5C0', '#3FD8B0', rng.uniform(0, .5)), 'v', 2)
            g.piece(poly([a1, b1, b2, a2]), mix('#2BC4BA', '#3F9CD0', rng.uniform(0, .5)), 'v', 2)
            g.piece(poly([a2, b2, tb, tip, ta]), mix('#7A5BD0', '#4A4AA8', rng.uniform(0, .6)), 'v', 2)
            ma = a1[1]
            g.line([(xa + (xb - xa) * .4, ya - 3), (xa + (xb - xa) * .45, ma + 4)], 1.6, '#E8FFF4', .35, w0=.2)


def star(x, y, r, c=MILK):
    pts = []
    for k in range(8):
        a = math.radians(-90 + k * 45)
        rr = r if k % 2 == 0 else r * .38
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    g.piece(poly(pts), c, 'R', 1.5)


def stars():
    for x, y, r in [(474, 88, 7), (528, 132, 5), (456, 344, 5), (536, 372, 6), (512, 226, 4.5),
                    (236, 78, 5), (360, 74, 4.5)]:
        star(x, y, r)


# ---------------------------------------------------------------- Москва: Кремль
def kremlin():
    base = 472
    wall = [(40, base), (40, 446)]
    x = 40
    while x < 196:
        wall += [(x, 446), (x + 3, 438), (x + 6, 443), (x + 9, 438), (x + 12, 446)]
        x += 16
    wall += [(196, 446), (196, base)]
    g.piece(poly(wall), '#8E2A36', 'h', 2.4)
    tx = 118
    g.piece(poly([(tx - 19, base), (tx - 19, 398), (tx + 19, 398), (tx + 19, base)]), '#A3303C', 'v', 2.6)
    g.piece(poly([(tx - 21, 398), (tx + 21, 398), (tx + 16, 388), (tx - 16, 388)]), MILK, 'h', 2)
    g.piece(poly([(tx - 14, 388), (tx + 14, 388), (tx + 14, 362), (tx - 14, 362)]), '#B33A44', 'v', 2.4)
    g.piece(smooth([(tx, 366), (tx + 8, 374), (tx, 382), (tx - 8, 374)]), '#F3E2BE', 'R', 1.8)
    g.leadline(f'M{tx} 374V369M{tx} 374h4', 1.2)
    g.piece(poly([(tx - 11, 362), (tx + 11, 362), (tx + 9, 350), (tx - 9, 350)]), MILK, 'h', 1.8)
    g.piece(poly([(tx - 9, 350), (tx + 9, 350), (tx + 2, 306), (tx - 2, 306)]), '#1D7A5A', 'a', 2.2)
    g.piece(poly([(tx - 1.6, 306), (tx + 1.6, 306), (tx + 1.6, 297), (tx - 1.6, 297)]), STEEL, None, 1.2)
    star(tx, 290, 8.5, '#E8323E')
    g.piece(smooth([(tx - 8, base, 1), (tx - 8, 446), (tx, 436), (tx + 8, 446), (tx + 8, base, 1)]), '#3A1220', 'v', 2)
    for wx in (84, 152):   # окна-бойницы со светом
        g.piece(smooth([(wx - 3, 462, 1), (wx - 3, 455), (wx, 451), (wx + 3, 455), (wx + 3, 462, 1)]), '#F6B45A', 'R', 1.4)


# ---------------------------------------------------------------- Север: море, кит, сопки
def north():
    hz = 474
    g.piece(smooth([(372, hz, 1), (398, 446), (426, 426), (452, 420), (478, 432), (506, 410), (532, 402), (560, 414), (560, hz, 1)]),
            '#3B3F8E', 'a', 2.4)
    g.piece(smooth([(380, hz, 1), (414, 454), (446, 446), (470, 458), (500, hz, 1)]), '#2C3478', 'b', 2.2)
    for spec in ([(436, 423, 1), (452, 420), (466, 425, 1), (458, 429), (452, 426), (444, 430)],
                 [(516, 405, 1), (532, 402), (548, 407, 1), (540, 411), (532, 408), (523, 412)]):
        g.piece(smooth(spec), '#CFCBEA', 'r', 1.6)
    bands = [(474, 492, '#1D5A9C'), (492, 512, '#2470B2'), (512, 536, '#1B4F8C')]
    for k, (y0, y1, c) in enumerate(bands):
        xs = [372, 412, 452, 492, 532, 572]
        for j in range(len(xs) - 1):
            xa, xb = xs[j] + (6 if k % 2 else 0), xs[j + 1] + (6 if k % 2 else 0)
            pts = [(xa, y0 + 2 * math.sin(xa / 9)), (xb, y0 + 2 * math.sin(xb / 9)),
                   (xb, y1 + 2 * math.sin(xb / 7)), (xa, y1 + 2 * math.sin(xa / 7))]
            g.piece(poly(pts), mix(c, TURQ, .12 * ((j + k) % 3)), 'h', 2)
    # хвост кита
    kx, ky = 490, 477
    g.piece(smooth([(kx - 7, ky + 2, 1), (kx - 5, ky - 18), (kx - 14, ky - 30), (kx - 36, ky - 38, 1),
                    (kx - 20, ky - 41), (kx - 4, ky - 34), (kx, ky - 28, 1), (kx + 4, ky - 34), (kx + 20, ky - 41),
                    (kx + 36, ky - 38, 1), (kx + 14, ky - 30), (kx + 5, ky - 18), (kx + 7, ky + 2, 1)]), '#33456A', 'a', 2.4)
    g.line([(kx - 30, ky - 38), (kx - 12, ky - 34), (kx - 2, ky - 27)], 2.2, '#C8D8E8', .55)
    g.line([(kx + 30, ky - 38), (kx + 12, ky - 34), (kx + 2, ky - 27)], 2.2, '#C8D8E8', .3)
    for x, y, r in [(kx - 42, ky - 47, 3), (kx + 44, ky - 48, 2.6), (kx - 26, ky - 53, 2), (kx + 31, ky - 56, 2.2)]:
        g.piece(smooth([(x, y - r * 1.4), (x + r, y), (x, y + r), (x - r, y)]), '#BFEFF0', 'R', 1.2)


# ---------------------------------------------------------------- луг, дорога, берёза
def ground():
    hz = 472
    g.piece(smooth([(40, hz, 1), (196, hz), (300, 476), (372, hz), (560, hz, 1), (560, 520, 1), (40, 520, 1)]), '#2B8F68', 'h', 2.4)
    # луг полосами — левая сторона
    left_bands = [
        ([(40, 492), (110, 488), (190, 496), (300, 504)], '#2E9E70'),
        ([(40, 540), (120, 530), (200, 540), (300, 552)], '#36AE78'),
        ([(40, 600), (110, 590), (200, 604), (300, 616)], '#3DBA80'),
    ]
    prev = [(40, hz), (196, hz), (300, 478)]
    for edge, c in left_bands:
        top = prev
        pts = [(x, y, 1) if i in (0, len(top) - 1) else (x, y) for i, (x, y) in enumerate(top)]
        bot = [(x, y, 1) if i in (0, len(edge) - 1) else (x, y) for i, (x, y) in enumerate(edge)]
        g.piece(smooth(pts + bot[::-1]), c, 'h', 2.4)
        prev = edge
    g.piece(smooth([(40, 600, 1), (110, 590), (200, 604), (300, 616, 1), (300, 700, 1), (40, 700, 1)]), '#46C488', 'a', 2.4)
    # правая сторона
    right_bands = [
        ([(300, 504), (372, 494), (450, 488), (560, 484)], '#2A9A6E'),
        ([(300, 552), (380, 538), (470, 530), (560, 526)], '#32A874'),
        ([(300, 616), (390, 598), (480, 590), (560, 586)], '#38B47C'),
    ]
    prev = [(300, 478), (372, hz), (560, hz)]
    for edge, c in right_bands:
        pts = [(x, y, 1) if i in (0, len(prev) - 1) else (x, y) for i, (x, y) in enumerate(prev)]
        bot = [(x, y, 1) if i in (0, len(edge) - 1) else (x, y) for i, (x, y) in enumerate(edge)]
        g.piece(smooth(pts + bot[::-1]), c, 'h', 2.4)
        prev = edge
    g.piece(smooth([(300, 616, 1), (390, 598), (480, 590), (560, 586, 1), (560, 700, 1), (300, 700, 1)]), '#40BE84', 'b', 2.4)
    # дорога к морю
    rd = smooth([(338, 700, 1), (404, 618), (430, 558), (424, 520), (440, 494), (466, 479, 1), (474, 481, 1),
                 (458, 498), (452, 524), (466, 566), (472, 624), (480, 700, 1)])
    g.piece(rd, '#E3D3AE', 'v', 2.6)
    for spec in ([(392, 640), (474, 642)], [(414, 596), (468, 598)], [(428, 556), (462, 556)], [(428, 524), (452, 526)], [(442, 500), (458, 500)]):
        g.leadline(smooth(spec, closed=False), 2)
    # травинки и цветы мая
    for x0, y0, x1, y1 in [(70, 690, 64, 640), (82, 690, 92, 650), (118, 690, 112, 662), (520, 690, 528, 646),
                           (534, 690, 526, 656), (504, 690, 500, 666), (250, 690, 244, 664), (266, 690, 272, 670)]:
        g.line([(x0, y0), ((x0 + x1) / 2 + 2, (y0 + y1) / 2), (x1, y1)], 3, '#0E5A3E', .7, w0=.2, p=.4)
    for x, y, c in [(62, 528, COBALT), (100, 566, '#F2E6D0'), (152, 520, RUBY), (90, 616, '#E85A6A'),
                    (140, 640, '#F2E6D0'), (500, 548, '#F2E6D0'), (536, 604, RUBY), (494, 640, COBALT),
                    (528, 506, '#E85A6A'), (390, 520, COBALT), (250, 636, '#F2E6D0')]:
        g.piece(smooth([(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)]), c, 'R', 1.6)
    # берёза слева
    tr = smooth([(58, 700, 1), (62, 520), (68, 380), (74, 250), (78, 130), (82, 60, 1), (96, 60, 1), (94, 140),
                 (90, 260), (86, 390), (84, 530), (86, 700, 1)])
    g.piece(tr, '#F1EBDC', 'v', 2.8)
    for y, x in [(262, 77), (300, 75), (340, 73), (384, 71), (430, 70), (478, 68), (528, 67), (580, 66), (636, 66)]:
        g.flat(smooth([(x - 1, y), (x + 9, y - 3), (x + 16, y + 1), (x + 7, y + 4)]), '#121418', .9)
    g.line([(80, 268), (92, 256), (112, 246)], 3, '#2A2620', .95, w0=.4, p=.5)
    g.line([(88, 300), (104, 296), (112, 304)], 2.4, '#2A2620', .9, w0=.3, p=.5)
    leaves = [(104, 236, 10, '#7CCB5A'), (122, 244, 9, '#4FAE4A'), (92, 226, 9, '#5FBE52'), (64, 232, 9, '#86D468'),
              (114, 262, 8, '#3E9A44'), (70, 256, 8, '#4FAE4A'), (106, 296, 7, '#7CCB5A'), (120, 308, 6, '#9BDC72'),
              (134, 256, 7, '#5FBE52')]
    for x, y, r, c in leaves:
        a = rng.uniform(-.7, .7)
        p0 = (x + r * math.cos(a + math.pi / 2) * .95, y + r * math.sin(a + math.pi / 2) * .95, 1)
        p1 = (x + r * math.cos(a) * .55, y + r * math.sin(a) * .55)
        p2 = (x - r * math.cos(a + math.pi / 2) * .95, y - r * math.sin(a + math.pi / 2) * .95, 1)
        p3 = (x - r * math.cos(a) * .55, y - r * math.sin(a) * .55)
        g.piece(smooth([p0, p1, p2, p3]), c, 'r', 1.8)


# ---------------------------------------------------------------- ореол-компас
HALO = (300.0, 226.0)


def halo():
    cx, cy = HALO
    R0, R1, R2 = 92, 110, 117
    n = 16
    for k in range(n):
        a0 = 2 * math.pi * k / n - math.pi / 2
        a1 = 2 * math.pi * (k + 1) / n - math.pi / 2
        pts = [(cx, cy)] + [(cx + R0 * math.cos(a0 + (a1 - a0) * s / 4), cy + R0 * math.sin(a0 + (a1 - a0) * s / 4)) for s in range(5)]
        c = ['#D9F4EE', '#C9EEEA', '#E2F4E8', '#D2F0F2'][k % 4]
        g.piece(poly(pts), c, 'r', 1.6)
    m = 24
    for k in range(m):
        a0 = 2 * math.pi * k / m - math.pi / 2 + math.pi / m
        a1 = 2 * math.pi * (k + 1) / m - math.pi / 2 + math.pi / m
        pts = [(cx + R0 * math.cos(a0 + (a1 - a0) * s / 3), cy + R0 * math.sin(a0 + (a1 - a0) * s / 3)) for s in range(4)]
        pts += [(cx + R1 * math.cos(a1 - (a1 - a0) * s / 3), cy + R1 * math.sin(a1 - (a1 - a0) * s / 3)) for s in range(4)]
        g.piece(poly(pts), TURQ if k % 2 == 0 else '#1F7FA8', 'r', 2.2)
    pts = [(cx + R1 * math.cos(a), cy + R1 * math.sin(a)) for a in [2 * math.pi * s / 48 for s in range(48)]]
    pts2 = [(cx + R2 * math.cos(a), cy + R2 * math.sin(a)) for a in [2 * math.pi * s / 48 for s in range(48)]]
    g.flat(poly(pts2) + poly(pts[::-1]), '#EBCB92', None, 2.2)
    for a, c in [(-90, RUBY), (0, TURQ), (180, TURQ), (90, RUBY)]:
        x, y = cx + (R1 + R2) / 2 * math.cos(math.radians(a)), cy + (R1 + R2) / 2 * math.sin(math.radians(a))
        g.piece(smooth([(x, y - 9), (x + 7, y), (x, y + 9), (x - 7, y)]), c, 'R', 1.8)
    g.soft(cx, cy - 6, 96, 96, '#FFFFFF', .3, core=.15)


def swallow(x, y, s, flip=1):
    pts = [(x - 10 * s * flip, y - 7 * s, 1), (x - 3 * s * flip, y - 1 * s), (x + 2 * s * flip, y - 2.4 * s, 1), (x + 6 * s * flip, y - 1 * s),
           (x + 11 * s * flip, y - 6 * s, 1), (x + 6 * s * flip, y + 1.6 * s), (x + 1 * s * flip, y + 2.6 * s), (x - 4 * s * flip, y + 4.6 * s, 1),
           (x - 3 * s * flip, y + 1.6 * s)]
    g.piece(smooth(pts), '#1E2C5E', None, 1.4)
    g.flat(smooth([(x - 1 * s * flip, y + .4 * s), (x + 3 * s * flip, y + .2 * s), (x + 1 * s * flip, y + 2 * s)]), '#F4ECE0', .9)


def swallows():
    swallow(150, 206, 1.25)
    swallow(176, 182, .95)


def blooms():
    """Свет сквозь стекло: тёплое солнце слева, холодное сияние справа."""
    g.soft(SUN[0], SUN[1] - 6, 150, 130, '#FFD49A', .55, core=.05)
    g.soft(486, 190, 100, 90, '#9FF5D8', .22)


# ---------------------------------------------------------------- рама
def frame():
    outer = f'M0 0H{W}V{H}H0Z'
    g.raw(f'<path d="{outer}{arch_path(WIN)}" fill="{LEAD}" fill-rule="evenodd"/>')
    band(44, WIN, 14, ['#E0B36A', '#C98E52'], 'h', 2)
    band(16, 44, 46, None, None, 2.4)


def band(i_out, i_in, n, colors, var, lead):
    outer = resample(arch_full(i_out), n * 2)
    inner = resample(arch_full(i_in), n * 2)
    m = len(outer) - 1
    for k in range(m):
        pts = [inner[k], inner[k + 1], outer[k + 1], outer[k]]
        if colors:
            g.piece(poly(pts), colors[k % len(colors)], var, lead)
        else:
            if k % 4 == 1:
                c, v = RUBY, 'R'
            elif k % 4 == 3:
                c, v = '#E7DCC4', 'r'
            else:
                c, v = (COBALT if (k // 2) % 2 == 0 else '#24307A'), 'a'
            g.piece(poly(pts), c, v, lead)
            if k % 4 == 1:
                mx = sum(p[0] for p in pts) / 4
                my = sum(p[1] for p in pts) / 4
                g.piece(smooth([(mx, my - 5), (mx + 5, my), (mx, my + 5), (mx - 5, my)]), TURQ, 'R', 1.4)
    y0, y1 = H - i_out, H - i_in
    xs = [i_out + (W - 2 * i_out) * k / (n // 2) for k in range(n // 2 + 1)]
    for k in range(len(xs) - 1):
        pts = [(xs[k], y1), (xs[k + 1], y1), (xs[k + 1], y0), (xs[k], y0)]
        if colors:
            g.piece(poly(pts), colors[k % len(colors)], var, lead)
        else:
            c = RUBY if k % 3 == 1 else (COBALT if k % 2 == 0 else '#24307A')
            g.piece(poly(pts), c, 'a', lead)
            if k % 3 == 1:
                mx, my = (xs[k] + xs[k + 1]) / 2, (y0 + y1) / 2
                g.piece(smooth([(mx, my - 5), (mx + 5, my), (mx, my + 5), (mx - 5, my)]), TURQ, 'R', 1.4)


# ================================================================ ГЕРОЙ
def band_poly(center, w, per=6):
    """Полоса (лямка) заданной ширины вдоль центральной линии."""
    pts = sample(center, closed=False, per=per)
    L, R = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        L.append((x + nx * w / 2, y + ny * w / 2))
        R.append((x - nx * w / 2, y - ny * w / 2))
    return poly(L + R[::-1])


def glint(spec, w=2.2, op=.45, c='#FFFFFF'):
    g.line(spec, w, c, op, w0=.1)


def backpack():
    g.piece(smooth([(214, 330, 1), (388, 330, 1), (404, 420), (406, 520), (396, 572), (300, 584), (206, 572), (198, 520), (200, 420)]),
            PACK_D, 'r', 3)
    g.piece(smooth([(204, 470, 1), (232, 468, 1), (236, 566, 1), (210, 566), (200, 520)]), PACK, 'a', 2.4)
    g.piece(smooth([(370, 468, 1), (404, 470, 1), (404, 520), (394, 566), (366, 566, 1)]), PACK_D, 'b', 2.4)
    glint([(208, 482), (206, 520), (210, 552)], 2.2, .4)
    # скатка-коврик
    y0, y1 = 288, 330
    xs = [190, 214, 248, 284, 318, 352, 386, 410]
    for k in range(len(xs) - 1):
        xa, xb = xs[k], xs[k + 1]
        c = [mix(ROLL, '#FFFFFF', .22), ROLL, mix(ROLL, '#FFFFFF', .1), '#22A9A6'][k % 4]
        g.piece(poly([(xa, y0), (xb, y0), (xb, y1), (xa, y1)]), c, 'v', 2.4)
    g.line([(196, 294), (250, 293), (290, 293)], 2.4, '#FFFFFF', .45, w0=.1)
    for cx, c in ((190, mix(ROLL, '#FFFFFF', .38)), (410, mix(ROLL, '#000000', .05))):
        g.piece(smooth([(cx, 287), (cx + 9, 297), (cx + 10, 309), (cx + 9, 321), (cx, 331), (cx - 9, 321), (cx - 10, 309), (cx - 9, 297)]),
                c, 'R', 2.6)
        g.line([(cx - 1, 309), (cx + 4, 304), (cx + 5, 312), (cx - 3, 316), (cx - 6, 306), (cx + 1, 298), (cx + 8, 302)], 1.4, '#0E4E4C', .6, w0=.6)
    for x in (232, 368):
        g.piece(poly([(x - 5, 284), (x + 5, 284), (x + 5, 334), (x - 5, 334)]), STRAP, 'v', 2)


def legs():
    g.piece(smooth([(230, 584, 1), (300, 592, 1), (300, 700, 1), (232, 700, 1), (230, 640)]), PANTS_L, 'a', 3)
    g.piece(smooth([(300, 592, 1), (372, 584, 1), (372, 640), (370, 700, 1), (300, 700, 1)]), PANTS, 'b', 3)
    for spec, op in [([(250, 612), (262, 640), (258, 668)], .35), ([(282, 606), (290, 630)], .3),
                     ([(338, 610), (346, 640), (350, 668)], .35), ([(318, 606), (312, 628)], .3)]:
        g.line(spec, 2.4, '#0E1650', op)
    glint([(240, 600), (244, 640), (246, 668)], 2.4, .3)


def torso():
    jacket = [(282, 302), (250, 312), (222, 326), (210, 340, 1), (214, 380), (226, 420), (234, 470), (236, 520),
              (232, 560), (230, 592, 1), (266, 597), (300, 599), (336, 597), (372, 592, 1), (368, 560), (366, 520),
              (370, 470), (378, 420), (388, 380), (392, 340, 1), (380, 326), (352, 312), (318, 302)]
    g.piece(smooth(jacket), JACK_M, 'r', 3.2)
    g.piece(smooth([(300, 330, 1), (300, 456, 1), (238, 456, 1), (230, 420), (222, 380), (216, 342), (236, 328), (262, 316, 1), (286, 318)]),
            JACK_L, 'a', 2.4)
    g.piece(smooth([(300, 330, 1), (314, 318), (338, 316, 1), (364, 328), (384, 342), (378, 380), (372, 420), (366, 456, 1), (300, 456, 1)]),
            JACK_D, 'b', 2.4)
    g.piece(smooth([(238, 456, 1), (300, 456, 1), (300, 580, 1), (234, 584, 1), (236, 520)]), JACK, 'r', 2.4)
    g.piece(smooth([(300, 456, 1), (366, 456, 1), (366, 520), (370, 584, 1), (300, 580, 1)]), JACK_DD, 'r', 2.4)
    # кокетка — отдельные стёкла на плечах
    g.piece(smooth([(300, 330, 1), (300, 374, 1), (224, 380, 1), (218, 352), (236, 328), (262, 316, 1), (286, 318)]), light(JACK_L, .14), 'b', 2.4)
    g.piece(smooth([(300, 330, 1), (314, 318), (338, 316, 1), (364, 328), (383, 346), (378, 380, 1), (300, 374, 1)]), JACK_M, 'a', 2.4)
    g.piece(smooth([(232, 576, 1), (300, 582, 1), (300, 600, 1), (230, 594, 1)]), JACK_D, 'h', 2.2)
    g.piece(smooth([(300, 582, 1), (370, 576, 1), (372, 594, 1), (300, 600, 1)]), dark(JACK_DD, .1), 'h', 2.2)
    glint([(232, 350), (244, 340), (262, 334)], 2.6, .45)
    glint([(246, 468), (244, 520)], 2.4, .3)
    # нагрудный карман и Ильин рисунок кита
    g.piece(smooth([(270, 406, 1), (296, 404, 1), (296, 446, 1), (270, 446, 1)]), mix(JACK_L, JACK, .5), 'v', 2.2)
    g.piece(smooth([(273, 388, 1), (293, 384, 1), (295, 406, 1), (273, 408, 1)]), '#F4EEE0', 'v', 1.8)
    g.flat(smooth([(277, 397), (281, 393), (287, 394), (290, 397, 1), (293, 394.5), (292.5, 399.5), (287, 401), (280, 400)]), '#2B6FC0', .9)
    g.line([(283.5, 392.5), (282.5, 388.5), (279.5, 386.5)], 1.1, '#2B6FC0', .8, w0=.5)
    g.line([(283.5, 392.5), (285.5, 388.5), (288.5, 387.5)], 1.1, '#2B6FC0', .8, w0=.5)
    g.piece(smooth([(268, 404, 1), (298, 402, 1), (298, 414, 1), (268, 416, 1)]), JACK_D, 'h', 2)
    # молния
    g.leadline(smooth([(300, 330), (300, 460), (301, 598)], closed=False), 3)
    g.line([(300, 334), (300, 460), (301, 596)], 1.2, '#D8E4EC', .35, w0=.8)
    g.piece(smooth([(296.5, 344, 1), (303.5, 344, 1), (303.5, 360, 1), (296.5, 360, 1)]), STEEL, 'v', 1.4)


def collar_neck():
    neck = smooth([(279, 260), (276, 300), (286, 314, 1), (314, 314, 1), (324, 300), (321, 260)])
    g.piece(neck, SKIN, 's', 3)
    g.fade(neck, BROWN, .55, 0, 1, 0, 0)
    g.piece(poly([(284, 302), (316, 302), (300, 332)]), MILK, 'r', 2.2)
    g.piece(smooth([(262, 300), (272, 286, 1), (284, 290), (294, 312), (300, 333, 1), (284, 328), (270, 314)]), JACK, 'a', 2.6)
    g.piece(smooth([(338, 300), (328, 286, 1), (316, 290), (306, 312), (300, 333, 1), (316, 328), (330, 314)]), JACK_D, 'b', 2.6)
    glint([(268, 298), (276, 290)], 2, .5)


def straps():
    L = [(264, 300), (252, 352), (244, 404), (240, 452), (238, 482)]
    R = [(336, 300), (348, 352), (356, 404), (360, 452), (362, 482)]
    g.piece(band_poly(L, 22), mix(STRAP, '#FFFFFF', .12), 'v', 2.6)
    g.piece(band_poly(R, 22), dark(STRAP, .08), 'v', 2.6)
    g.line([(258, 316), (248, 360), (242, 404), (239, 448)], 1.1, '#F0B0A0', .45, w0=1)
    g.line([(342, 316), (352, 360), (358, 404), (360, 448)], 1.1, '#F0B0A0', .3, w0=1)
    # нагрудная стяжка
    g.piece(smooth([(246, 440, 1), (354, 440, 1), (355, 450, 1), (245, 450, 1)]), STRAP, 'h', 2.2)
    g.piece(smooth([(292, 436), (308, 436), (311, 445), (308, 454), (292, 454), (289, 445)]), STEEL, 'v', 2)
    g.flat(smooth([(296, 441, 1), (304, 441, 1), (304, 449, 1), (296, 449, 1)]), '#4A5666', .85)
    # поясной ремень
    g.piece(smooth([(234, 548, 1), (368, 548, 1), (368, 564, 1), (234, 564, 1)]), STRAP, 'h', 2.4)
    g.piece(smooth([(289, 544), (313, 544), (316, 556), (313, 568), (289, 568), (286, 556)]), STEEL, 'v', 2)
    g.flat(smooth([(294, 550, 1), (308, 550, 1), (308, 562, 1), (294, 562, 1)]), '#4A5666', .85)
    # значок-кит на лямке
    g.piece(smooth([(242, 380), (247, 374), (256, 373.5), (262, 377, 1), (268, 371, 1), (267.5, 380, 1), (262, 381), (253, 385.5), (245, 384.5)]),
            '#2B78C8', 'R', 1.6)
    g.flat(smooth([(246, 377.5), (247.5, 376.5), (248.5, 378), (247, 379)]), '#FFFFFF', .9)


def arms():
    g.piece(smooth([(212, 336), (198, 350), (190, 392), (188, 432), (186, 468, 1), (220, 470, 1), (224, 432), (228, 396), (230, 360)]),
            JACK_L, 'a', 3)
    g.piece(smooth([(186, 466, 1), (220, 470, 1), (218, 500), (216, 528, 1), (186, 528, 1), (184, 498)]), JACK, 'v', 2.6)
    g.piece(smooth([(185, 522, 1), (217, 524, 1), (216, 538, 1), (185, 536, 1)]), JACK_D, 'h', 2.2)
    g.piece(smooth([(388, 336), (402, 352), (410, 392), (413, 430), (414, 462, 1), (388, 470, 1), (382, 432), (378, 396), (374, 360)]),
            JACK_D, 'b', 3)
    g.piece(smooth([(414, 458, 1), (378, 414, 1), (362, 428, 1), (390, 474), (404, 480)]), JACK_M, 'a', 2.6)
    g.piece(smooth([(382, 418, 1), (372, 408, 1), (356, 424, 1), (366, 434, 1)]), JACK_DD, 'h', 2.2)
    for spec in ([(200, 440), (212, 452)], [(196, 410), (206, 420)], [(398, 430), (408, 448)], [(392, 452), (404, 466)]):
        g.line(spec, 2.2, '#0B3A60', .4)
    glint([(198, 356), (193, 400), (191, 440)], 2.6, .4)
    glint([(192, 476), (190, 510)], 2.2, .3)


def pole():
    g.piece(poly([(201, 540), (207, 540), (212, 700), (205, 700)]), STEEL, 'h', 2.2)
    g.piece(smooth([(195, 486, 1), (207, 486, 1), (208, 540, 1), (196, 540, 1)]), '#2A2330', 'h', 2.2)
    g.piece(smooth([(194, 480, 1), (208, 480, 1), (208, 488, 1), (194, 488, 1)]), '#5A6676', 'h', 1.8)
    g.line([(198, 484), (186, 500), (186, 522)], 2.2, STRAP, .9, w0=1)
    g.line([(204, 484), (214, 504), (214, 524)], 2.2, STRAP, .9, w0=1)


def hands():
    # кулак на палке
    g.piece(smooth([(186, 532), (198, 528), (212, 530), (220, 540), (219, 556), (212, 566), (196, 568), (184, 562), (181, 548)]), SKIN, 's', 2.6)
    for y in (541, 549, 557):
        g.line([(186, y), (198, y + 1.5), (213, y)], 1.4, SEPIA, .5, w0=.4)
    g.piece(smooth([(212, 531), (221, 535), (225, 545), (220, 551), (214, 545)]), SKIN_L, 's', 2)
    g.soft(196, 538, 8, 4, '#FFFFFF', .35)
    # кулак на лямке — большой палец под лямкой, пальцы снаружи
    g.piece(smooth([(338, 404), (344, 397.5), (351, 399), (358, 396.5), (365, 398.5), (372, 404), (374, 416), (369, 426), (355, 431), (342, 429),
                    (335, 418)]), SKIN, 's', 2.6)
    for spec in ([(348, 400), (347, 412), (344, 425)], [(355, 399), (355, 413), (353, 428)], [(362, 400), (363, 413), (362, 427)]):
        g.line(spec, 1.3, SEPIA, .5, w0=.3)
    g.line([(339, 418), (348, 422), (360, 424), (370, 420)], 1.1, BROWN, .4, w0=.3)
    g.soft(352, 403, 12, 4, '#FFFFFF', .4)


FACE = [(262, 196), (257, 216), (257, 236), (260, 254), (266.5, 270), (278, 283), (290, 290.5), (301, 293), (312, 290.5),
        (324, 283), (334.5, 270), (340, 254), (343, 236), (343, 216), (338, 196), (320, 182), (300, 178), (280, 182)]
EAR_L = [(259, 222), (250, 221), (245, 232), (246, 246), (252, 257), (260, 256)]
EAR_R = [(341, 222), (350, 221), (355, 232), (354, 246), (348, 257), (340, 256)]
HAIR_MASS = [(256, 224, 1), (251, 204), (252, 182), (262, 164), (280, 151), (301, 146), (323, 148), (340, 157), (350, 172),
             (354, 190), (350, 210), (344, 224, 1), (342, 206), (336, 196), (322, 188), (300, 184), (278, 186), (266, 196), (260, 210)]
HAIR_TOP = [(276, 186, 1), (281, 168), (294, 156), (314, 150), (334, 155), (349, 167), (356, 182), (351, 194), (342, 189),
            (330, 183), (314, 180), (297, 182)]
HAIR_SIDE = [(254, 208), (252, 188), (260, 172), (274, 161), (282, 168, 1), (277, 186, 1), (266, 194), (258, 206)]
HAIR_LOCK = [(297, 183), (312, 185.5), (326, 191), (336, 202, 1), (342, 192), (336, 184), (322, 178), (306, 178)]
HAIR_R = [(342, 196), (351, 191), (355, 202), (350, 215), (344, 224, 1), (342, 208)]


def head():
    for pts, c, sx in ((EAR_L, SKIN, -1), (EAR_R, SKIN_D, 1)):
        g.piece(smooth(pts), c, 's', 2.6)
        g.line([(300 + sx * 49, 228), (300 + sx * 51, 238), (300 + sx * 47, 250)], 1.4, BROWN, .55)
        g.soft(300 + sx * 48, 240, 4, 9, BROWN, .3)
    g.piece(smooth(FACE), SKIN, 's', 3.2)


def eye(ex, ey, look=.9, outer=-1):
    """Серый глаз с прищуром. outer=-1 — внешний угол слева."""
    hw, up, dn = 8.6, 3.5, 2.3

    def top(x):
        u = (x - ex) / hw
        return ey - up * (1 - u * u) - .45 * u * outer

    def bot(x):
        u = (x - ex) / hw
        return ey + dn * (1 - u * u) + .3 - .45 * u * outer

    xs = [ex - hw + 2 * hw * k / 12 for k in range(13)]
    lens = [(x, top(x)) for x in xs] + [(x, bot(x)) for x in reversed(xs)]
    g.flat(poly(lens), '#F4ECE4')
    g.soft(ex, ey - 1.2, hw, 2.2, BROWN, .35)        # тень века на белке

    def disc(cx, cy, r, n=20):
        out = []
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            x = max(ex - hw + .5, min(ex + hw - .5, x))
            y = max(top(x) + .2, min(bot(x) - .2, y))
            out.append((x, y))
        return poly(out)

    ix, iy = ex + look, ey + .2
    gid = g.radgrad([(0, '#B7C8D2'), (.6, '#7E95A6'), (1, '#4C6070')], .5, .5, .5)
    g.raw(f'<path d="{disc(ix, iy, 3.7)}" fill="url(#{gid})"/>')
    g.flat(disc(ix, iy, 1.6), '#141820')
    g.flat(smooth([(ix + 1.2, iy - 2.2), (ix + 2.4, iy - 1.9), (ix + 2.1, iy - .8), (ix + 1, iy - 1.1)]), '#FFFFFF', .95)
    # верхнее веко — толще к внешнему углу, с «ресничным» хвостиком
    lid = [(x, top(x) - .2) for x in xs[::2]]
    oc = lid[0] if outer < 0 else lid[-1]
    tail = (oc[0] + outer * 2.2, oc[1] - .4)
    spec = ([tail] + lid) if outer < 0 else (lid + [tail])
    g.line(spec, 2.5, SEPIA, .92, w0=.25, p=.6)
    # складка века и нижнее веко, «мешочек» улыбки
    g.line([(ex - 6.5, top(ex - 6.5) - 3.2), (ex, top(ex) - 3.4), (ex + 6.5, top(ex + 6.5) - 3.2)], 1.1, BROWN, .45, w0=.3)
    g.line([(ex - 6.5, bot(ex - 6.5) + .2), (ex, bot(ex) + .3), (ex + 6.5, bot(ex + 6.5) + .2)], 1, BROWN, .5, w0=.3)
    g.line([(ex - 5, bot(ex - 5) + 3), (ex, bot(ex) + 3.6), (ex + 5, bot(ex + 5) + 3)], .9, BROWN, .3, w0=.3)
    # «гусиные лапки»
    ox = ex + outer * (hw + 1.5)
    g.line([(ox, ey + .5), (ox + outer * 4, ey + 1.6)], 1, BROWN, .4)
    g.line([(ox, ey + 2.6), (ox + outer * 3.4, ey + 5.2)], 1, BROWN, .32)


def face_paint():
    # матировка: правая сторона в тени, тень от волос, глазницы
    g.fade(smooth([(303, 180), (320, 182), (338, 196), (343, 216), (343, 236), (340, 254), (335, 268), (326, 280), (313, 289), (302, 292),
                   (308, 262), (310, 232), (308, 200)]), '#8A4A2E', .42, 0, 0, 1, 0)
    g.soft(306, 190, 34, 7, BROWN, .3)
    g.soft(330, 200, 10, 7, BROWN, .25)
    g.soft(282, 229, 13, 6.5, BROWN, .28)
    g.soft(319, 229, 13, 6.5, BROWN, .34)
    g.soft(306.5, 244, 3.6, 10, BROWN, .32)
    g.soft(301, 263.5, 9, 3.2, '#5A2A1A', .4)
    g.soft(301, 280, 9, 3.4, BROWN, .3)
    # щетина
    g.soft(301, 276, 40, 18, '#6B4630', .2, core=.35)
    zone = [(258, 238), (262, 256), (270, 273), (283, 287), (301, 293.5), (319, 287), (332, 273), (340, 256), (343, 238),
            (337, 249), (327, 257), (317, 262.5), (309, 261.5), (301, 261), (293, 261.5), (285, 262.5), (275, 257), (264, 249)]

    def inside(x, y, P=zone):
        c = False
        j = len(P) - 1
        for i in range(len(P)):
            xi, yi = P[i]
            xj, yj = P[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                c = not c
            j = i
        return c

    pts = []
    while len(pts) < 520:
        x, y = rng.uniform(256, 346), rng.uniform(236, 295)
        if not inside(x, y):
            continue
        if abs(x - 301) < 14 and 265.5 < y < 276:
            continue
        pts.append((x, y))
    g.dots(pts, .38, '#4A2E1C', .26)
    # румянец и блики
    g.soft(275, 253, 10, 6, '#E36E5E', .2)
    g.soft(326, 253, 9, 6, '#E36E5E', .16)
    g.soft(284, 202, 15, 8, '#FFF4E6', .5)
    g.soft(272, 244, 9, 6, '#FFF4E6', .45)
    g.soft(297.5, 241, 2.4, 10, '#FFF4E6', .6)
    g.soft(296, 285, 6, 2.6, '#FFF4E6', .3)
    # брови
    g.line([(268.5, 225.5), (277, 219.5), (288, 219), (294.5, 222.5)], 4, '#6E4C2C', .92, w0=.3, p=.5)
    g.line([(305.5, 222.5), (312.5, 219), (323.5, 219.5), (332.5, 224.5)], 4, '#5E4026', .92, w0=.3, p=.5)
    g.line([(272, 222), (280, 219.5)], 1, '#D2AA6E', .45)
    g.line([(314, 220), (322, 219.8)], 1, '#C69A62', .35)
    eye(282, 234, look=1.1, outer=-1)
    eye(319, 234, look=1.1, outer=1)
    # нос
    g.line([(304.5, 229), (306.5, 243), (309, 252)], 1.3, BROWN, .5, w0=.3)
    g.line([(294.5, 256.5), (298, 259), (302, 259.6), (306, 258.8), (308.5, 256.5)], 1.4, '#5A2A1A', .55, w0=.3)
    g.line([(293, 251.5), (292.2, 255.5), (295, 258.5)], 1.3, '#5A2A1A', .55, w0=.35)
    g.line([(309.5, 251.5), (310.5, 255.5), (307.5, 258.5)], 1.3, '#5A2A1A', .6, w0=.35)
    g.flat(smooth([(295.5, 257.6), (297.8, 257), (298.6, 258.4), (296.4, 258.9)]), '#3A1A10', .55)
    g.flat(smooth([(304.6, 258.4), (305.4, 257), (307.6, 257.6), (306.6, 258.9)]), '#3A1A10', .6)
    # рот — спокойная улыбка
    g.soft(301, 268.6, 12, 2.2, '#9A4A3A', .32)
    g.line([(287.5, 268.2), (294.5, 271.2), (301, 271.8), (307.5, 271.2), (314.5, 268.2)], 2.1, '#4A1E16', .85, w0=.2, p=.6)
    g.line([(285.8, 266.2), (287.6, 269)], 1, '#5A2A1A', .45)
    g.line([(316.2, 266.2), (314.4, 269)], 1, '#5A2A1A', .45)
    g.soft(301, 274.4, 6.5, 1.7, '#FFE6D8', .4)
    # носогубные складки
    g.line([(290.5, 257.5), (286.8, 263.5), (285.6, 269.5)], 1, BROWN, .3, w0=.3)
    g.line([(311.5, 257.5), (315.2, 263.5), (316.4, 269.5)], 1, BROWN, .38, w0=.3)


def hair():
    g.piece(smooth(HAIR_MASS), HAIR_D, 'r', 3)
    g.piece(smooth(HAIR_SIDE), HAIR, 'b', 2.4)
    g.piece(smooth(HAIR_TOP), HAIR_L, 'a', 2.4)
    g.piece(smooth(HAIR_LOCK), mix(HAIR, HAIR_L, .45), 'b', 2.2)
    g.piece(smooth(HAIR_R), HAIR_DD, 'r', 2.2)
    for spec, c, op, w in [
        ([(284, 172), (302, 160), (326, 158), (348, 172)], '#F6DDAA', .62, 2.2),
        ([(290, 178), (310, 168), (332, 168), (350, 180)], '#F6DDAA', .4, 1.5),
        ([(296, 162), (316, 155), (336, 160)], '#FFF0CC', .45, 1.3),
        ([(286, 180), (300, 174), (318, 174)], '#7A5630', .4, 1.4),
        ([(326, 176), (340, 178), (352, 188)], '#7A5630', .45, 1.4),
        ([(304, 182), (320, 186), (333, 197)], '#5A3E22', .5, 1.5),
        ([(308, 180), (324, 182), (338, 191)], '#F6DDAA', .45, 1.2),
        ([(277, 166), (268, 174), (259, 190)], '#5A3E22', .45, 1.5),
        ([(272, 168), (262, 180), (256, 196)], '#E2BE84', .35, 1.3),
        ([(258, 212), (259.5, 222), (259, 231)], '#6E4E2C', .55, 2.2),
        ([(342, 212), (341, 222), (341.5, 231)], '#5A3E22', .55, 2.2),
    ]:
        g.line(spec, w, c, op)


def rim_light():
    """Контровой свет: тёплый от солнца слева, холодный от сияния справа."""
    g.line([(256.5, 208), (253, 190), (257, 174), (268, 160)], 2.6, WARM_RIM, .75, w0=.2)
    g.line([(213, 342), (200, 354), (193, 392), (190, 432), (188.5, 462)], 2.8, WARM_RIM, .55, w0=.2)
    g.line([(259, 222), (258.5, 240), (262, 256), (270, 272)], 1.8, WARM_RIM, .4, w0=.2)
    g.line([(352, 176), (353.5, 194), (349, 211)], 2.2, COOL_RIM, .55, w0=.2)
    g.line([(392, 344), (404, 356), (410, 392), (412, 430)], 2.4, COOL_RIM, .45, w0=.2)
    g.line([(342, 222), (342.5, 240), (338, 258)], 1.6, COOL_RIM, .35, w0=.2)


def silhouette():
    """Подложка-контур: фигура отделена от фона широким свинцом."""
    shapes = [
        smooth([(214, 330, 1), (388, 330, 1), (404, 420), (406, 520), (396, 572), (300, 584), (206, 572), (198, 520), (200, 420)]),
        poly([(184, 286), (416, 286), (416, 334), (184, 334)]),
        smooth([(212, 336), (198, 350), (190, 392), (188, 432), (184, 498), (181, 548), (186, 566), (212, 568), (226, 546), (228, 396)]),
        smooth([(388, 336), (402, 352), (410, 392), (414, 462), (404, 480), (390, 474), (370, 428), (338, 430), (334, 400), (374, 360)]),
        smooth(HAIR_MASS), smooth(HAIR_TOP), smooth(HAIR_R), smooth(FACE), smooth(EAR_L), smooth(EAR_R),
        smooth([(230, 584, 1), (372, 584, 1), (372, 700, 1), (232, 700, 1)]),
    ]
    for d in shapes:
        g.raw(f'<path d="{d}" fill="{LEAD}" stroke="{LEAD}" stroke-width="8" stroke-linejoin="round"/>')


def hero():
    silhouette()
    backpack()
    legs()
    torso()
    straps()
    pole()
    arms()
    hands()
    collar_neck()
    head()
    face_paint()
    hair()
    rim_light()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/hero2/sergey_v2.svg'
    sky()
    aurora()
    stars()
    blooms()
    swallows()
    kremlin()
    north()
    ground()
    halo()
    hero()
    frame()
    s = g.svg()
    bad = check(s)
    open(out, 'w', encoding='utf-8').write(s)
    print('ok', out, len(s), 'байт', 'запрещено:' if bad else '', bad or '')


if __name__ == '__main__':
    main()

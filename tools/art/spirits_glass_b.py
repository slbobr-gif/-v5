"""Витражные портреты духов (часть B): кикимора, русалка, баба-яга, овинник.

Запуск: python3 tools/art/spirits_glass_b.py [--sheet /tmp/spirits_b_sheet.png]
Пишет app/assets/art/spirits/<id>_<mood>.svg (360x200; neutral|kind|cunning|angry)
и контактный лист. Библиотека примитивов: hero_glass_lib.py (не меняется).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hero_glass_lib import *  # noqa: F401,F403

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'app', 'assets', 'art', 'spirits')
W, H = 360, 200
MOODS = ['neutral', 'kind', 'cunning', 'angry']
DARK = '#1B1030'


# ---- общие помощники ---------------------------------------------------------------
def rot(pts, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def limb(g, joints, widths, color, lw=1.2, col2=None):
    qs, _ = chain_quads(joints, widths)
    for i, q in enumerate(qs):
        g.shard(q, col2 if (col2 and i % 2) else color, lw=lw)


def spikes(g, c, rx, ry, n, l0, l1, colors, seed, a0, a1, wid=0.11, lw=1.0, rot0=0.0):
    rnd = random.Random(seed)
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * (i + rnd.uniform(-.25, .25)) / max(1, n - 1))
        L = rnd.uniform(l0, l1)
        w = wid * rnd.uniform(.8, 1.3)
        bx, by = c[0] + rx * math.cos(a), c[1] + ry * math.sin(a)
        tx = c[0] + (rx + L) * math.cos(a + rot0 * rnd.uniform(.4, 1)); ty = c[1] + (ry + L) * math.sin(a + rot0 * rnd.uniform(.4, 1))
        p1 = (c[0] + rx * .85 * math.cos(a - w), c[1] + ry * .85 * math.sin(a - w))
        p2 = (c[0] + rx * .85 * math.cos(a + w), c[1] + ry * .85 * math.sin(a + w))
        g.shard([p1, (tx, ty), p2], rnd.choice(colors), lw=lw)


def claws(g, p, ang, n, L, color='#E8E6F0', lw=0.6):
    for i in range(n):
        a = ang + (i - (n - 1) / 2) * 0.42
        b = (p[0] + 4 * math.cos(a), p[1] + 4 * math.sin(a))
        t = (p[0] + (4 + L) * math.cos(a), p[1] + (4 + L) * math.sin(a))
        s1 = (b[0] + 1.6 * math.cos(a + 1.57), b[1] + 1.6 * math.sin(a + 1.57))
        s2 = (b[0] - 1.6 * math.cos(a + 1.57), b[1] - 1.6 * math.sin(a + 1.57))
        g.shard([s1, t, s2], color, lw=lw, grad=False)


def hand(g, p, r, color, ncl=0, ang=0, ccol='#E8E6F0', L=5):
    g.circle(p[0], p[1], r, color, lw=1.0)
    if ncl:
        claws(g, p, ang, ncl, L, ccol)


def band(g, y0, y1, color, op, seed, x0=0, x1=W, amp=5):
    """Полупрозрачная полоса тумана/дымки, без свинца."""
    rnd = random.Random(seed)
    top = [(x, y0 + rnd.uniform(-amp, amp)) for x in range(x0, x1 + 1, 40)]
    bot = [(x, y1 + rnd.uniform(-amp, amp)) for x in range(x1, x0 - 1, -40)]
    g.shard(top + bot, color, grad=False, op=op, nolead=True)


def make_bg(g, mood, seed, horizon, pals, light, rr=25, region=None, bias=None):
    """Мозаика фона. pals: dict sky/ground/near -> списки цветов."""
    rnd = random.Random(seed)
    region = region or rect_poly(0, 0, W, H)
    pts = poisson((0, 0, W, H), lambda x, y: rr, seed, tries=5000)
    lx, ly = light

    def cf(x, y, i):
        base = pals['sky'] if y < horizon else pals['ground']
        col = rnd.choice(base)
        d = math.hypot(x - lx, y - ly)
        if d < pals.get('lr', 70):
            col = rnd.choice(pals['near'])
        return col
    g.mosaic(region, pts, cf, lw=1.5)


def frame(g, w=W, h=H):
    g.lead_line([(0, 0), (w, 0), (w, h), (0, h)], lw=7, closed=True)
    g.lead_line([(5, 5), (w - 5, 5), (w - 5, h - 5), (5, h - 5)], lw=1.2, closed=True)


def head(g, c, rx, ry, a, cols, seed=1):
    poly = rot(ellipse_poly(c[0], c[1], rx, ry, 22), c, a)
    rnd = random.Random(seed)
    seeds = [(c[0] + rnd.uniform(-rx, rx) * .55, c[1] + rnd.uniform(-ry, ry) * .55) for _ in range(3)]
    g.mosaic(poly, seeds, lambda x, y, i: cols[i % len(cols)], lw=.7)
    return poly


def face(g, c, s, mood, a=0.0, look=0.0, skin=None, tooth=MILK, eye_hot=False):
    """Лицо в локальных координатах (единица = s). a — наклон головы."""
    g.prec = 1
    ca, sa = math.cos(a), math.sin(a)
    T = lambda p: (c[0] + (p[0] * ca - p[1] * sa) * s, c[1] + (p[0] * sa + p[1] * ca) * s)
    TL = lambda pts: [T(p) for p in pts]
    lwl = max(.9, s * .075)
    skin = skin or '#8DB8A0'
    ex, ey = .42, -.05
    dk = darken(skin, .75)
    for side in (-1, 1):
        cx = side * ex
        if mood == 'neutral':
            g.shard(TL(ellipse_poly(cx, ey, .21, .24, 14)), MILK, lw=.6, grad=False)
            g.circle(*T((cx + look * .05, ey + .02)), .11 * s, DARK, grad=False, nolead=True)
            g.shard(TL([(cx - .08, ey - .08), (cx - .03, ey - .12), (cx - .02, ey - .06)]), '#FFFFFF', grad=False, nolead=True, lw=0)
            g.shard(TL([(side * .2, -.45), (side * .46, -.58), (side * .7, -.47), (side * .7, -.41), (side * .46, -.51), (side * .2, -.38)]), dk, lw=.5, grad=False)
        elif mood == 'kind':
            pts = [(cx + .22 * math.cos(t), ey + .08 - .16 * math.sin(t)) for t in [i * math.pi / 6 for i in range(7)]]
            g.lead_line(TL(pts), lw=lwl * 1.3)
            g.circle(*T((side * .6, .32)), .17 * s, CORAL, grad=False, nolead=True, op=.5)
            g.shard(TL([(side * .2, -.5), (side * .45, -.64), (side * .7, -.5), (side * .7, -.45), (side * .45, -.57), (side * .2, -.43)]), dk, lw=.5, grad=False)
        elif mood == 'cunning':
            nar = .15 if side == -1 else .11
            g.shard(TL(ellipse_poly(cx, ey + .04, .23, nar, 14)), '#F1EBD6', lw=.6, grad=False)
            g.circle(*T((cx + (look if look else .06) * .8 * -side * -1, ey + .05)), .1 * s, DARK, grad=False, nolead=True)
            # веко
            g.shard(TL([(cx - .26, ey + .04), (cx - .1, ey - .09 - (0 if side == -1 else .02)), (cx + .12, ey - .09), (cx + .26, ey + .04), (cx + .2, ey - .02), (cx - .2, ey - .02)]), dk, lw=.4, grad=False)
            if side == -1:
                g.shard(TL([(-.62, -.5), (-.4, -.78), (-.2, -.5), (-.24, -.46), (-.4, -.68), (-.58, -.44)]), dk, lw=.5, grad=False)  # высоко поднятая бровь
            else:
                g.shard(TL([(.18, -.28), (.5, -.4), (.72, -.32), (.72, -.24), (.5, -.32), (.2, -.2)]), dk, lw=.5, grad=False)  # нахмуренная
            if side == 1:
                g.spark(*T((cx + .08, ey + .0)), .17 * s, '#FFFFFF', .95)
        else:  # angry
            g.shard(TL([(side * .16, ey - .1), (side * .66, ey - .0), (side * .62, ey + .14), (side * .26, ey + .16)]), '#FFD9C6' if not eye_hot else '#FF9A5A', lw=.6, grad=False)
            g.circle(*T((side * .42, ey + .06)), .1 * s, '#B0182A', grad=False, nolead=True)
            g.shard(TL([(side * .1, -.26), (side * .72, -.66), (side * .76, -.5), (side * .2, -.12)]), dk, lw=.5, grad=False)
    # нос
    if mood != 'cunning':
        g.lead_line(TL([(0, .02), (-.07, .24), (.08, .26)]), lw=lwl * .7)
    else:
        g.lead_line(TL([(.02, .0), (-.04, .22), (.1, .24)]), lw=lwl * .7)
    # рот
    if mood == 'neutral':
        g.lead_line(TL([(-.24, .56), (0, .6), (.24, .55)]), lw=lwl)
    elif mood == 'kind':
        g.shard(TL([(-.42, .4), (-.2, .6), (0, .68), (.2, .6), (.42, .4), (.2, .48), (0, .5), (-.2, .48)]), '#8A2A44', lw=.7, grad=False)
        g.shard(TL([(-.2, .48), (0, .5), (.2, .48), (.12, .54), (-.12, .54)]), tooth, lw=0, grad=False, nolead=True)
    elif mood == 'cunning':
        g.lead_line(TL([(-.32, .58), (-.05, .62), (.28, .52), (.46, .32)]), lw=lwl)
        g.shard(TL([(.12, .56), (.22, .56), (.18, .66)]), tooth, lw=.4, grad=False)
    else:
        g.shard(TL([(-.46, .5), (-.22, .4), (0, .46), (.22, .4), (.46, .5), (.34, .82), (0, .9), (-.34, .82)]), '#2A0A14', lw=.8, grad=False)
        for k, x in enumerate((-.3, -.1, .1, .3)):
            g.shard(TL([(x - .08, .43 + (.02 if k % 2 else 0)), (x, .62), (x + .08, .43 + (.02 if k % 2 else 0))]), tooth, lw=.4, grad=False)
        g.shard(TL([(-.12, .86), (0, .7), (.12, .86)]), '#C8454F', lw=.4, grad=False)
    g.prec = 0


# ---- палитры настроений -----------------------------------------------------------
def moodpal(mood):
    if mood == 'neutral':
        return dict(sky=[BLUE, ULTRA, '#2A5FA0', '#1F3B78', '#27508F'], ground=['#14604A', '#1A7A5A', '#0F4A55', '#1F5A6E'],
                    near=['#3F8FB8', '#2BA8B8', '#3A7FC0'], lr=70, glow=TURQ)
    if mood == 'kind':
        return dict(sky=['#1FA39A', TURQ, '#2FBF93', '#1B8CA8', '#35C9A8'], ground=[EMER, '#1B8A5E', '#2BB385', '#168366'],
                    near=['#8FEDD6', '#6BE0C8', '#B6F2DE'], lr=85, glow='#CFFFEF')
    if mood == 'cunning':
        return dict(sky=[VIOL, '#3E2E80', '#2C6E86', '#1F8F95', '#4A3A94'], ground=['#2B2A6A', '#1F6F73', '#3A2E78', '#1B5A70'],
                    near=['#7C5CC8', '#35B5B0', '#9A78DC'], lr=70, glow='#9A78DC')
    return dict(sky=[NIGHT, '#2A0E26', '#6E1E36', '#3A1230', '#8E2A3A', '#1A1030'], ground=['#2A0E1E', '#4A1428', '#14101E', '#5A1A2A'],
                near=['#C8454F', '#E0665A', '#A02840'], lr=60, glow=CORAL)


def lightning(g, pts, w=3):
    q, _ = chain_quads(pts, [w, w * .7] + [w * .5] * (len(pts) - 2))
    for qq in q:
        g.shard(qq, '#FFE9DC', lw=.6, grad=False)


def two_dirs(g):
    g._dir = lambda c: (1 if (g.light[0] - c[0]) >= 0 else -1, -1)


def finish(name, g):
    frame(g)
    return g.render()


# ---- КИКИМОРА ---------------------------------------------------------------------
def kikimora(mood):
    P = moodpal(mood)
    ang = mood == 'angry'
    g = Glass(W, H, prefix='k', prec=0, lw=1.5, light=(250, 80) if mood != 'angry' else (180, 20))
    g.gmin = 330
    two_dirs(g)
    make_bg(g, mood, {'neutral': 11, 'kind': 12, 'cunning': 13, 'angry': 14}[mood], 125, P, (250, 70) if not ang else (180, 10), rr=40)
    g.glow(250 if not ang else 180, 80 if not ang else 20, 130, P['glow'], .45 if mood != 'neutral' else .35)
    g.prec = 0
    # камыш
    rc = {'neutral': ('#2F6B48', '#4B8A4F'), 'kind': ('#1B8A5E', '#3FB37A'), 'cunning': ('#1F5A6E', '#35808C'), 'angry': ('#241226', '#4A1A30')}[mood]
    for x, h0, lean in ((18, 62, 6), (38, 80, -4), (326, 70, -6), (344, 56, 4), (300, 92, 5), (62, 104, 3)):
        top = (x + lean * (2 if ang else 1) * 3, h0)
        q, _ = chain_quads([(x, 176), (x + lean, (176 + h0) / 2 + 8), top], [4.4, 3.4, 2])
        for k, qq in enumerate(q):
            g.shard(qq, rc[k % 2], lw=1.0)
        if x in (38, 326, 300):
            g.shard(ellipse_poly(top[0], top[1] + 7, 3.2, 9, 8), '#6B4A38' if not ang else '#8A2A3A', lw=.8)
    # кочка
    g.shard(ellipse_poly(180, 184, 112, 26, 22), '#23513A' if mood != 'angry' else '#2A1020', lw=1.4)
    g.shard([(98, 178), (120, 166), (150, 170), (140, 186), (110, 190)], '#3E7A4A' if mood != 'cunning' else '#2F6C72', lw=1.2)
    g.shard([(208, 170), (236, 164), (262, 176), (240, 190), (214, 188)], '#3E7A4A' if mood != 'cunning' else '#2F6C72', lw=1.2)
    g.shard([(150, 170), (180, 164), (214, 170), (214, 188), (150, 188)], '#2D6140' if mood != 'angry' else '#3A1426', lw=1.2)
    # туман
    fogc = {'neutral': '#CFEFF0', 'kind': '#E4FFF3', 'cunning': '#C9B6F0', 'angry': '#7A2A3A'}[mood]
    band(g, 138, 156, fogc, .22 if not ang else .28, 3)
    band(g, 160, 172, fogc, .18, 4)
    g.lead_flush()
    # волосы сзади
    hc = (180, 98)
    skin = {'neutral': '#8DB8A0', 'kind': '#A6E0BE', 'cunning': '#A6A8D0', 'angry': '#8FA48C'}[mood]
    hair = {'neutral': ['#2F5D3C', '#3E7A4A', '#244A38', '#5A8F57'], 'kind': ['#2F9A63', '#46B87A', '#1E7F58', '#7AD9A0'],
            'cunning': ['#2B3E7A', '#3E7A8A', '#4A3A94', '#2F6C72'], 'angry': ['#1A1030', '#4A1A30', '#7A1E36', '#2A0E26']}[mood]
    tilt = {'neutral': 0, 'kind': -.06, 'cunning': -.22, 'angry': .04}[mood]
    nsp = {'neutral': 15, 'kind': 12, 'cunning': 15, 'angry': 20}[mood]
    l0, l1 = {'neutral': (14, 28), 'kind': (11, 21), 'cunning': (15, 30), 'angry': (26, 52)}[mood]
    spikes(g, hc, 27, 24, nsp, l0, l1, hair, 5, 150 if not ang else 130, 390 if not ang else 410, wid=.13, lw=1.0, rot0=.22 if not ang else -.1)
    # тело (лохмотья)
    cloth = {'neutral': ['#3C6B4E', '#2F5A44', '#4C7A55'], 'kind': ['#2FA67A', '#238A68', '#5ACB9A'],
             'cunning': ['#4A3A94', '#35808C', '#5A4AA8'], 'angry': ['#4A1428', '#2A1020', '#6E1E36']}[mood]
    dx = 8 if mood == 'cunning' else 0
    g.shard([(148 + dx, 178), (150 + dx, 140), (170 + dx, 120), (176, 178)], cloth[0], lw=1.3)
    g.shard([(170 + dx, 120), (198 + dx, 118), (192, 178), (176, 178)], cloth[1], lw=1.3)
    g.shard([(198 + dx, 118), (214 + dx, 140), (216, 178), (192, 178)], cloth[2], lw=1.3)
    for x in range(150, 214, 16):
        g.shard([(x, 176), (x + 8, 190), (x + 16, 176)], cloth[(x // 16) % 3], lw=1.0)
    # руки
    sk2 = darken(skin, .18)
    sh_l, sh_r = (158 + dx, 130), (206 + dx, 130)
    if mood == 'neutral':
        limb(g, [sh_l, (146, 152), (150, 170)], [8, 7, 5], skin)
        limb(g, [sh_r, (218, 150), (212, 170)], [8, 7, 5], skin)
        hand(g, (150, 172), 5, skin, 3, 1.5)
        hand(g, (212, 172), 5, skin, 3, 1.5)
        g.circle(262, 96, 9, '#3FD0E0', lw=1.0)           # болотный огонёк
        g.glow(262, 96, 36, '#7FF0F0', .5)
    elif mood == 'kind':
        limb(g, [sh_l, (146, 152), (150, 170)], [8, 7, 5], skin)
        hand(g, (150, 172), 5, skin, 3, 1.5)
        limb(g, [sh_r, (236, 134), (256, 120)], [8, 7, 5], skin)
        hand(g, (258, 118), 6, skin, 3, -.5)
        g.glow(262, 108, 44, '#FFF3C0', .55)
        g.circle(264, 106, 9, TURQ, lw=1.2)               # подаренная блестящая бусина
        g.shard([(264, 98), (270, 106), (264, 114), (258, 106)], '#BFFAF0', lw=.7, grad=False)
        for fx, fy in ((120, 90), (96, 120), (292, 70), (310, 130), (80, 70)):
            g.circle(fx, fy, 2.6, AMBER, grad=False, nolead=True)
            g.glow(fx, fy, 10, AMBER, .5)
    elif mood == 'cunning':
        limb(g, [sh_l, (144, 150), (166, 156)], [8, 7, 5], skin)   # рука спрятана за спиной
        limb(g, [sh_r, (232, 116), (244, 90)], [8, 7, 5], skin)
        hand(g, (245, 87), 5.5, skin, 2, -1.2)
        q, _ = chain_quads([(245, 92), (252, 64), (256, 44)], [3, 2.6, 2])   # шест с приманкой
        for qq in q:
            g.shard(qq, '#5A3A2A', lw=.8)
        g.glow(258, 36, 40, '#A8F0F0', .7)
        g.circle(258, 36, 11, '#6FE8E0', lw=1.2)           # ложный огонёк-приманка
        g.circle(258, 36, 4.5, '#F2FFFF', lw=.6, grad=False)
        g.shard([(300, 140), (312, 134), (316, 148), (304, 152)], '#6A4A9A', lw=1.0)  # ложная «тропа» из кочек
        g.shard([(322, 158), (334, 152), (338, 164), (326, 168)], '#6A4A9A', lw=1.0)
    else:
        limb(g, [sh_l, (136, 110), (124, 84)], [9, 7, 5], skin)
        limb(g, [sh_r, (228, 110), (240, 84)], [9, 7, 5], skin)
        hand(g, (122, 80), 6, skin, 4, -2.2, L=8)
        hand(g, (242, 80), 6, skin, 4, -.9, L=8)
        lightning(g, [(300, 4), (288, 34), (304, 40), (284, 78), (296, 84), (272, 124)], 4)
        lightning(g, [(66, 6), (76, 28), (62, 34), (74, 56)], 3)
    # голова
    head(g, hc, 27, 24, tilt, [skin, lighten(skin, .22), sk2, skin, lighten(skin, .1)], seed=7)
    for sgn in (-1, 1):  # уши
        g.shard(rot([(hc[0] + sgn * 24, hc[1] - 6), (hc[0] + sgn * 42, hc[1] - 14), (hc[0] + sgn * 26, hc[1] + 6)], hc, tilt), sk2, lw=1.0)
    # лицо
    face(g, (hc[0], hc[1] + 2), 21, mood, tilt, look=.5 if mood == 'cunning' else 0, skin=skin, eye_hot=ang)
    # чёлка
    spikes(g, (hc[0], hc[1] - 4), 24, 17, 6, 8, 16, hair, 9, 215, 325, wid=.16, lw=.9)
    # цветок/ожерелье из бусин у доброй
    if mood == 'kind':
        for k in range(4):
            g.circle(136 + k * 9, 82 - k * 3, 3.5, [CORAL, AMBER, '#E8FFFB', VIOL][k], lw=.8)
    if mood == 'cunning':
        band(g, 150, 162, fogc, .16, 8)
    g.spark(262 if mood in ('neutral',) else 300, 96 if mood == 'neutral' else 60, 5, MILK, .8)
    g.blik([(170, 112), (178, 108)], w=.9, op=.6)
    return finish('k', g)


# ---- РУСАЛКА ----------------------------------------------------------------------
def rusalka(mood):
    P = moodpal(mood)
    ang = mood == 'angry'
    mx, my = (268, 56) if not ang else (262, 50)
    g = Glass(W, H, prefix='r', prec=0, lw=1.5, light=(mx, my))
    g.gmin = 330
    two_dirs(g)
    P['sky'] = P['sky']
    make_bg(g, mood, {'neutral': 21, 'kind': 22, 'cunning': 23, 'angry': 24}[mood], 140, P, (mx, my), rr=46)
    moon = {'neutral': '#DDEBFF', 'kind': '#F4FFF6', 'cunning': '#E6DAFF', 'angry': '#FF9C8A'}[mood]
    g.glow(mx, my, 90, moon, .5)
    g.prec = 0
    g.circle(mx, my, 22, moon, lw=1.8, grad=False)
    g.shard([(mx - 8, my - 14), (mx + 8, my - 16), (mx + 4, my - 4), (mx - 10, my - 2)], lighten(moon, .5), lw=.8, grad=False)
    if mood != 'angry':
        g.shard(ellipse_poly(mx + 6, my + 4, 10, 9, 8), mix(moon, '#9CB4E0', .45), lw=.7, grad=False)
    if ang:
        lightning(g, [(40, 4), (52, 32), (36, 40), (54, 72), (44, 80), (60, 112)], 4)
        lightning(g, [(330, 4), (318, 24), (330, 30)], 3)
    # ива: ветви с листьями
    leaf = {'neutral': ['#1F9E6B', '#2BB385', '#137A57'], 'kind': ['#3FD0A0', '#2BC4BA', '#7AE8B8'],
            'cunning': ['#2B8A8A', '#4A6AC0', '#1F6F73'], 'angry': ['#3A1A2A', '#5A1E34', '#241226']}[mood]
    sway = 14 if ang else 5
    for sx, ln, d in ((14, 96, 1), (40, 124, 1), (66, 80, 1), (332, 104, -1), (308, 130, -1), (350, 80, -1)):
        jts = [(sx, -4), (sx + d * sway * .4, ln * .3), (sx + d * sway, ln * .6), (sx + d * sway * 1.4, ln)]
        q, _ = chain_quads(jts, [3, 2.6, 2.2, 1.6])
        for k, qq in enumerate(q):
            g.shard(qq, leaf[k % 3], lw=.9)
            ax, ay = jts[k + 1]
            g.shard([(ax, ay - 3), (ax + d * 9, ay + 5), (ax, ay + 12), (ax - d * 5, ay + 4)], leaf[(k + 1) % 3], lw=.8)
    # вода
    wcol = {'neutral': ['#1B4F8C', '#2B3E9E', '#1F6FA8', '#14405E'], 'kind': ['#1FA39A', '#2BC4BA', '#1B8CA8', '#35C9A8'],
            'cunning': ['#3E2E80', '#2C6E86', '#1F5A9E', '#4A3A94'], 'angry': ['#14101E', '#2A0E26', '#4A1428', '#1A1030']}[mood]
    rw = random.Random(31 + len(mood))
    wpts = poisson((0, 140, W, H), lambda x, y: 38, 77, tries=3000)
    g.mosaic(rect_poly(0, 140, W, 60), wpts, lambda x, y, i: rw.choice(wcol), lw=1.4)
    g.glow_e(mx, 150, 24, 55, moon, .55)
    for k in range(0):
        g.shard([(mx - 7 + k * 2, 144 + k * 10), (mx + 7 - k * 2, 144 + k * 10), (mx + 5 - k * 2, 150 + k * 10), (mx - 5 + k * 2, 150 + k * 10)], mix(moon, wcol[1], .35), lw=.8, grad=False)
    g.lead_flush()
    # волосы сзади
    skin = {'neutral': '#D5E8E8', 'kind': '#F4E4D8', 'cunning': '#D6D2F0', 'angry': '#B8D4C0'}[mood]
    hairc = {'neutral': ['#1F8A7E', '#0E5E6B', '#27A89A'], 'kind': ['#27B08E', '#1F9E86', '#49D0A8'],
             'cunning': ['#3A4AA8', '#1F6F8A', '#5A3FA0'], 'angry': ['#0E3A3E', '#1A5A52', '#241226']}[mood]
    tilt = {'neutral': 0, 'kind': .05, 'cunning': -.2, 'angry': 0}[mood]
    hc = (170, 80)
    if not ang:
        g.shard([(150, 64), (136, 88), (126, 124), (134, 148), (156, 148), (152, 100)], hairc[0], lw=1.2)
        g.shard([(190, 64), (204, 88), (214, 124), (206, 148), (184, 148), (188, 100)], hairc[0], lw=1.2)
        g.shard([(136, 88), (126, 124), (134, 148), (140, 120)], hairc[1], lw=1.0)
        g.shard([(204, 88), (214, 124), (206, 148), (200, 120)], hairc[1], lw=1.0)
    else:
        spikes(g, (170, 78), 20, 22, 12, 34, 62, hairc, 6, 150, 390, wid=.14, lw=1.0, rot0=.35)
        g.shard([(150, 64), (140, 100), (138, 148), (156, 148), (152, 100)], hairc[2], lw=1.2)
        g.shard([(190, 64), (200, 100), (202, 148), (184, 148), (188, 100)], hairc[2], lw=1.2)
    # тело
    g.shard([(148, 146), (150, 116), (164, 104), (178, 104), (192, 116), (194, 146)], skin, lw=1.3)
    top = {'neutral': ['#7FC8D8', '#5AA8C8'], 'kind': ['#8FE8CF', '#5AD0B0'], 'cunning': ['#8A6AD0', '#5A4AA8'], 'angry': ['#5A8A7A', '#3A6A5A']}[mood]
    g.shard([(150, 124), (164, 112), (178, 112), (192, 124), (194, 146), (148, 146)], top[0], lw=1.2)
    g.shard([(160, 130), (170, 118), (180, 130), (176, 146), (164, 146)], top[1], lw=1.0)
    g.shard([(166, 98), (176, 98), (178, 106), (164, 106)], darken(skin, .15), lw=1.0)   # шея
    # руки
    sk2 = darken(skin, .15)
    if mood == 'neutral':
        limb(g, [(150, 118), (140, 134), (156, 142)], [7, 6, 5], skin)
        limb(g, [(192, 118), (202, 134), (186, 142)], [7, 6, 5], skin)
        hand(g, (162, 143), 4, skin); hand(g, (180, 143), 4, skin)
    elif mood == 'kind':
        limb(g, [(150, 118), (140, 134), (150, 140)], [7, 6, 5], skin)
        limb(g, [(192, 118), (218, 118), (240, 104)], [7, 6, 5], skin)
        hand(g, (242, 102), 5, skin)
        g.glow(246, 94, 40, '#FFFFFF', .6)
        g.circle(246, 94, 8, '#F4FFF6', lw=1.2)            # дар: жемчужина
        g.shard([(243, 90), (248, 89), (247, 93)], '#FFFFFF', lw=0, grad=False, nolead=True)
        for k in range(3):
            g.circle(100 + k * 14, 150 - k * 6, 2.5, '#EAFFF8', grad=False, nolead=True)
    elif mood == 'cunning':
        limb(g, [(192, 118), (216, 108), (228, 88)], [7, 6, 5], skin)   # манящая рука
        hand(g, (230, 84), 4.5, skin)
        g.lead_line([(230, 80), (236, 72), (232, 66)], lw=2.0)         # палец крючком
        limb(g, [(150, 118), (138, 134), (150, 146)], [7, 6, 5], skin)
        # ленточная петля-ловушка за спиной
        lp = [(128, 140), (112, 128), (106, 108), (116, 96), (130, 104), (126, 122)]
        for k in range(len(lp) - 1):
            q, _ = chain_quads([lp[k], lp[k + 1]], [4, 4])
            g.shard(q[0], CORAL if k % 2 == 0 else '#E0665A', lw=.9)
        g.glow(116, 110, 22, '#B8A0FF', .4)
    else:
        limb(g, [(150, 118), (130, 98), (118, 70)], [8, 7, 5], skin)
        limb(g, [(192, 118), (212, 98), (224, 70)], [8, 7, 5], skin)
        hand(g, (116, 66), 5, skin, 4, -2.0, L=8)
        hand(g, (226, 66), 5, skin, 4, -1.1, L=8)
    # лента-подарок, плывёт по воде / в волосах
    rib = [(CORAL, '#E87A6A'), (TURQ, '#7AE0D8')]
    for ri, (sx, sy, pts) in enumerate(((140, 136, [(140, 136), (118, 144), (96, 140), (80, 150)]), (200, 136, [(200, 136), (224, 146), (246, 142), (268, 152)]))):
        if mood == 'angry' and ri == 1:
            pts = [(200, 136), (216, 120), (210, 100), (228, 88)]
        q, _ = chain_quads(pts, [6, 5, 4, 3])
        for k, qq in enumerate(q):
            g.shard(qq, rib[ri][k % 2], lw=.9)
    # голова
    head(g, hc, 18, 21, tilt, [skin, lighten(skin, .3), darken(skin, .08), skin, lighten(skin, .15)], seed=3)
    face(g, (hc[0], hc[1] + 2), 17, mood, tilt, look=.5 if mood == 'cunning' else 0, skin=skin, eye_hot=ang)
    # чёлка и венок
    g.shard(rot([(152, 72), (160, 56), (176, 54), (188, 66), (190, 72), (178, 64), (164, 66)], hc, tilt), hairc[0], lw=1.0)
    for k, cc in enumerate(['#E87A9A', TURQ, MILK, CORAL, '#8FE0A0'] if mood != 'angry' else ['#7A1E36', '#3A1A2A', '#8E2A3A', '#241226', '#7A1E36']):
        p = rot([(154 + k * 8, 62 - (3 if 0 < k < 4 else 0))], hc, tilt)[0]
        g.circle(p[0], p[1], 3.6, cc, lw=.8)
    # кольца на воде
    for rx_, ry_ in ((50, 7), (80, 11)):
        g.lead_line(ellipse_poly(170, 150, rx_ + 20, ry_, 20)[:14], lw=.9)
    g.blik([(146, 150), (200, 152)], w=.9, op=.5)
    g.blik([(70, 168), (110, 166)], w=.9, op=.4)
    g.spark(mx - 8, my - 8, 4, '#FFFFFF', .9)
    return finish('r', g)


# ---- БАБА-ЯГА ---------------------------------------------------------------------
def baba_yaga(mood):
    P = moodpal(mood)
    ang = mood == 'angry'
    lt = (300, 92)
    g = Glass(W, H, prefix='y', prec=0, lw=1.5, light=lt if not ang else (180, 20))
    g.gmin = 330
    two_dirs(g)
    make_bg(g, mood, {'neutral': 31, 'kind': 32, 'cunning': 33, 'angry': 34}[mood], 118, P, lt if not ang else (180, 10), rr=46)
    g.glow(*(lt if not ang else (180, 10)), 120, P['glow'], .4)
    g.prec = 0
    # ель
    sp = {'neutral': ['#0F4A55', '#145A4A', '#1B6A5E'], 'kind': ['#16745A', '#1F9E6B', '#2BB385'],
          'cunning': ['#1F3A6A', '#2B3E7A', '#2F5A8A'], 'angry': ['#14101E', '#1E1428', '#2A0E1E']}[mood]
    for x, h0, w0 in ((20, 40, 30), (62, 64, 26), (106, 48, 22), (330, 54, 28), (356, 30, 24), (212, 70, 20)):
        for lvl in range(3):
            y = 120 - lvl * (120 - h0) / 3
            g.shard([(x - w0 * (1 - lvl * .22), y), (x, y - (120 - h0) / 2.2), (x + w0 * (1 - lvl * .22), y)], sp[(lvl + x // 10) % 3], lw=1.1)
        g.shard([(x - 2.5, 120), (x + 2.5, 120), (x + 2.5, 134), (x - 2.5, 134)], '#2A1A30', lw=1.0)
    if ang:
        lightning(g, [(262, 2), (250, 28), (266, 34), (248, 66), (258, 72)], 4)
        lightning(g, [(20, 4), (30, 24), (18, 30)], 3)
    # земля
    gr = {'neutral': ['#14604A', '#1A7A5A'], 'kind': ['#1B8A5E', '#2BB385'], 'cunning': ['#1F5A70', '#2B2A6A'], 'angry': ['#2A1020', '#3A1426']}[mood]
    g.shard([(0, 160), (80, 150), (200, 156), (360, 148), (360, 200), (0, 200)], gr[0], lw=1.4)
    g.shard([(0, 180), (120, 170), (250, 176), (360, 168), (360, 200), (0, 200)], gr[1], lw=1.3)
    # ИЗБУШКА на курьих ножках
    ix = 276
    lean = {'neutral': 0, 'kind': 0, 'cunning': .05, 'angry': -.09}[mood]
    wood = {'neutral': ['#6E4636', '#8A5A42', '#54332E'], 'kind': ['#8A5A42', '#A8704E', '#6E4636'],
            'cunning': ['#4A3A6A', '#5A4A7A', '#3A2E58'], 'angry': ['#3A1A24', '#4A2230', '#2A1220']}[mood]
    roof = {'neutral': [ULTRA, '#3A52B0'], 'kind': ['#1B8CA8', TURQ], 'cunning': [VIOL, '#7C5CC8'], 'angry': ['#6E1E36', '#8E2A3A']}[mood]
    cen = (ix, 100)
    R = lambda pts: rot(pts, (ix, 128), lean)
    for k in range(4):
        g.shard(R([(ix - 38, 78 + k * 11), (ix + 38, 78 + k * 11), (ix + 38, 89 + k * 11), (ix - 38, 89 + k * 11)]), wood[k % 3], lw=1.0)
    g.shard(R([(ix - 48, 78), (ix, 40), (ix + 48, 78)]), roof[0], lw=1.5)
    g.shard(R([(ix, 40), (ix + 48, 78), (ix + 10, 78)]), roof[1], lw=1.2)
    g.shard(R([(ix - 48, 78), (ix - 22, 78), (ix - 6, 54), (ix, 40)]), darken(roof[0], .2), lw=1.0)
    wc = {'neutral': AMBER, 'kind': AMBER, 'cunning': '#9A78DC', 'angry': '#E0443A'}[mood]
    g.glow(ix - 2, 103, 38 if mood != 'kind' else 52, wc, .6 if mood != 'cunning' else .45)
    g.shard(R([(ix - 12, 92), (ix + 12, 92), (ix + 12, 114), (ix - 12, 114)]), wc, lw=1.4, grad=False)
    g.lead_line(R([(ix, 92), (ix, 114)]), lw=1.0); g.lead_line(R([(ix - 12, 103), (ix + 12, 103)]), lw=1.0)
    # куриные ножки
    for lx, sgn in ((ix - 20, -1), (ix + 20, 1)):
        jts = [(lx, 122), (lx + sgn * 3, 140), (lx + sgn * (14 if mood != 'angry' else 6), 156)]
        if ang and sgn == 1:
            jts = [(lx, 122), (lx + 14, 134), (lx + 30, 128)]
        q, _ = chain_quads(R(jts), [5, 4, 3])
        for qq in q:
            g.shard(qq, '#C9863A' if mood != 'cunning' else '#A8782E', lw=1.0)
        tx, ty = R([jts[-1]])[0]
        for k in (-1, 0, 1):
            g.shard([(tx - 2, ty - 1), (tx + k * 8 + sgn * 4, ty + 6 - abs(k) * 1), (tx + 2, ty + 1)], '#C9863A', lw=.8)
    if mood == 'kind':   # дымок
        for k in range(3):
            g.circle(ix + 24 + k * 6, 28 - k * 9, 4 + k, '#DFFAF0', grad=False, nolead=True, op=.35 - k * .07)
    # СТУПА
    sc = {'neutral': '#6E4636', 'kind': '#8A5A42', 'cunning': '#4A3A6A', 'angry': '#3A1A24'}[mood]
    g.shard([(18, 140), (62, 140), (56, 184), (24, 184)], sc, lw=1.6)
    g.shard([(18, 140), (40, 140), (36, 184), (24, 184)], darken(sc, .2), lw=1.0)
    g.shard([(16, 136), (64, 136), (62, 144), (18, 144)], '#8E7A9A' if mood != 'kind' else '#B8E0D0', lw=1.2)
    q, _ = chain_quads([(40, 140), (46, 118), (54, 100)], [5, 5, 4])
    for qq in q:
        g.shard(qq, '#5A3A2A', lw=1.0)
    g.lead_flush()
    # ЯГА
    hc = (118, 78)
    tilt = {'neutral': 0, 'kind': .04, 'cunning': -.2, 'angry': .06}[mood]
    skin = {'neutral': '#C9B8A0', 'kind': '#E4C8A8', 'cunning': '#BFB0C8', 'angry': '#B8A890'}[mood]
    dress = {'neutral': ['#5B3FA0', '#4A3490', '#6A4FB0'], 'kind': ['#2FA67A', '#238A68', '#4CC49A'],
             'cunning': ['#3E2E80', '#35808C', '#4A3A94'], 'angry': ['#4A1428', '#6E1E36', '#2A1020']}[mood]
    kc = {'neutral': CORAL, 'kind': '#F07A6A', 'cunning': '#C8454F', 'angry': '#8E2A3A'}[mood]
    gray = {'neutral': '#B8C0D0', 'kind': '#E4ECF4', 'cunning': '#A8B0D8', 'angry': '#8A90A8'}[mood]
    # седые пряди сзади
    spikes(g, hc, 20, 23, 9, 8, 20 if not ang else 32, [gray, darken(gray, .2)], 4, 150, 390, wid=.15, lw=.9, rot0=.3)
    # тело
    g.shard([(88, 184), (94, 132), (112, 110), (130, 110)], dress[0], lw=1.4)
    g.shard([(130, 110), (150, 120), (160, 184), (88, 184)], dress[1], lw=1.4)
    g.shard([(106, 120), (130, 120), (136, 184), (100, 184)], dress[2], lw=1.2)
    g.shard([(98, 150), (150, 150), (152, 160), (96, 160)], kc, lw=1.1)                # пояс
    for x in range(90, 150, 20):
        g.shard([(x, 182), (x + 10, 196), (x + 20, 182)], dress[(x // 20) % 3], lw=1.0)
    # руки и КЛУБОК
    kb = {'neutral': (124, 148, 17), 'kind': (172, 130, 21), 'cunning': (84, 122, 16), 'angry': (126, 146, 17)}[mood]
    kx, ky, kr = kb
    sk2 = darken(skin, .15)
    kcol = '#2BC4BA' if mood != 'angry' else '#E0665A'
    if mood == 'cunning':
        limb(g, [(98, 126), (88, 130), (80, 122)], [7, 6, 5], skin)
        limb(g, [(140, 126), (164, 126), (190, 120)], [7, 6, 5], skin)
        hand(g, (194, 118), 4.5, skin, 3, -.3, L=5)
        # нить-петля (подвох)
        q, _ = chain_quads([(kx + 10, ky + 12), (150, 160), (186, 168), (226, 172), (238, 160)], [2.2] * 5)
        for qq in q:
            g.shard(qq, '#BFF5EE', lw=.5, grad=False)
        g.lead_line(ellipse_poly(238, 160, 9, 7, 10)[:9], lw=1.4)
    elif mood == 'kind':
        limb(g, [(100, 126), (116, 144), (150, 142)], [7, 6, 5], skin)
        limb(g, [(140, 126), (150, 142), (160, 142)], [7, 6, 5], skin)
        hand(g, (152, 142), 4.5, skin); hand(g, (160, 138), 4.5, skin)
    elif mood == 'neutral':
        limb(g, [(98, 126), (100, 146), (112, 152)], [7, 6, 5], skin)
        limb(g, [(140, 126), (146, 146), (136, 152)], [7, 6, 5], skin)
    else:
        limb(g, [(98, 126), (100, 146), (112, 152)], [7, 6, 5], skin)
        limb(g, [(140, 126), (170, 116), (200, 104)], [7, 6, 5], skin)       # палец-указка
        hand(g, (203, 102), 5, skin, 1, -.4, L=10)
    g.glow(kx, ky, kr * 2.2, '#C8FFF4' if mood != 'angry' else '#FF9A6A', .6 if mood == 'kind' else .35)
    g.circle(kx, ky, kr, kcol, lw=1.7)
    # нити клубка
    for k in range(4):
        a0 = -1.0 + k * .55
        pts = [(kx + kr * .95 * math.cos(a0 + t * .5) * (1 if k % 2 == 0 else .8), ky + kr * (-.7 + k * .45 + math.sin(t) * .12)) for t in (0, 1, 2, 3)]
    for k in range(4):
        y0 = ky - kr * .7 + k * kr * .45
        wdt = math.sqrt(max(0, kr * kr - (y0 - ky) ** 2))
        g.blik([(kx - wdt * .9, y0 + 2), (kx, y0 + 5), (kx + wdt * .9, y0 - 1)], color='#E8FFFB', w=1.0, op=.85)
    g.lead_line([(kx - kr * .8, ky - kr * .4), (kx - kr * .1, ky + kr * .7)], lw=1.1)
    g.lead_line([(kx + kr * .8, ky - kr * .3), (kx + kr * .1, ky + kr * .7)], lw=1.1)
    if mood != 'cunning':
        q, _ = chain_quads([(kx + kr * .5, ky + kr * .8), (kx + kr + 12, ky + kr + 12), (kx + kr + 44, ky + kr + 18)], [2.4, 2.2, 2])
        for qq in q:
            g.shard(qq, '#BFF5EE', lw=.5, grad=False)
    hand(g, (kx - kr * .95, ky + 2), 4.5, skin, 3 if ang else 0, 2.6) if mood != 'cunning' and mood != 'kind' else None
    if mood == 'cunning':
        hand(g, (kx - kr * .8, ky + 4), 4.5, skin, 2, 2.6)
    # голова
    head(g, hc, 20, 23, tilt, [skin, lighten(skin, .2), sk2, skin], seed=5)
    face(g, (hc[0], hc[1] + 3), 18, mood, tilt, look=.5 if mood == 'cunning' else 0, skin=skin, eye_hot=ang)
    # нос крючком
    nx, ny = rot([(hc[0], hc[1] + 6)], hc, tilt)[0]
    g.shard([(nx - 4, ny - 4), (nx + 5, ny - 4), (nx + 1, ny + 12), (nx - 5, ny + 8)], sk2, lw=1.0)
    # платок
    g.shard(rot([(97, 74), (104, 52), (126, 46), (140, 58), (140, 70), (124, 58), (108, 62)], hc, tilt), kc, lw=1.3)
    g.shard(rot([(100, 66), (96, 88), (106, 74)], hc, tilt), darken(kc, .2), lw=1.0)
    g.shard(rot([(138, 62), (146, 82), (134, 72)], hc, tilt), darken(kc, .2), lw=1.0)
    for k in range(3):
        g.circle(112 + k * 9, 56 - k % 2 * 2, 2, MILK, grad=False, nolead=True)
    g.spark(kx - 6, ky - 8, 4, '#FFFFFF', .9)
    return finish('y', g)


# ---- ОВИННИК ----------------------------------------------------------------------
def ovinnik(mood):
    P = moodpal(mood)
    ang = mood == 'angry'
    lt = (270, 70)
    g = Glass(W, H, prefix='o', prec=0, lw=1.5, light=lt)
    g.gmin = 330
    two_dirs(g)
    pal = {'neutral': dict(sky=['#2A3A66', '#1F2A55', '#34406A', '#2B3E7A'], ground=['#4A3A44', '#3A2E48', '#54422E'], near=['#6A5A7A', '#8A6A5A'], lr=60, glow=AMBER),
           'kind': dict(sky=['#1B8CA8', '#1F9E86', '#2BA8B8', '#3A9ABF'], ground=['#2F7A5A', '#8A5A3A', '#3A8A6A'], near=['#8FEDD6', '#B6F2DE'], lr=70, glow='#CFFFEF'),
           'cunning': dict(sky=['#3E2E80', '#2C4A86', '#4A3A94', '#2B3E7A'], ground=['#2B2A6A', '#4A3A5A', '#3A2E48'], near=['#7C5CC8', '#35B5B0'], lr=60, glow='#9A78DC'),
           'angry': dict(sky=['#2A0E26', '#4A1428', '#14101E', '#6E1E36'], ground=['#2A1020', '#4A1428', '#3A1426'], near=['#C8454F', '#E0665A', '#E8844A'], lr=80, glow=CORAL)}[mood]
    make_bg(g, mood, {'neutral': 41, 'kind': 42, 'cunning': 43, 'angry': 44}[mood], 130, pal, (180, 120) if ang else lt, rr=46)
    g.glow(*((180, 110) if ang else lt), 130, pal['glow'], .5 if ang else .35)
    g.prec = 0
    # стена овина: вертикальные доски по краям
    wd = {'neutral': ['#4A3A44', '#5A4A4E', '#3A2E3A'], 'kind': ['#5A7A62', '#6A8A6E', '#4A6A56'], 'cunning': ['#3A3A6A', '#4A4A7A', '#2E2E58'], 'angry': ['#2A1220', '#3A1A28', '#1E0E1A']}[mood]
    for side in (0, 1):
        for k in range(5):
            x0 = (k * 17) if side == 0 else (360 - 85 + k * 17)
            ln = 0 if side == 0 else 0
            g.shard([(x0, 0), (x0 + 17, 0), (x0 + 17, 200), (x0, 200)], wd[(k + side) % 3], lw=1.3)
    # окно-сушилка с огнём малыми осколками
    wc = {'neutral': AMBER, 'kind': AMBER, 'cunning': '#9A78DC', 'angry': '#E0443A'}[mood]
    g.shard([(244, 36), (300, 36), (300, 92), (244, 92)], '#1B1020' if mood != 'kind' else '#235A4A', lw=1.6)
    for (x, y, w_, h_) in ((250, 70, 14, 16), (268, 62, 12, 24), (282, 74, 12, 12)):
        g.shard(rect_poly(x, y, w_, h_), wc, lw=1.1, grad=False)
    g.glow(272, 80, 38, wc, .55)
    # пол: солома
    sc = {'neutral': ['#8A6A3A', '#6E4E2E', '#A87A3A'], 'kind': ['#8FB36A', '#6E9A52', '#A8C27A'], 'cunning': ['#6A5A8A', '#5A4A7A', '#7A6AA0'], 'angry': ['#4A1A24', '#6E2430', '#2A1020']}[mood]
    g.shard([(0, 170), (90, 160), (180, 168), (270, 160), (360, 168), (360, 200), (0, 200)], sc[0], lw=1.4)
    g.shard([(0, 188), (100, 178), (200, 186), (300, 178), (360, 184), (360, 200), (0, 200)], sc[1], lw=1.2)
    # СНОП слева
    sh = {'neutral': ['#D9A04A', '#B9782E', '#8A5A2A'], 'kind': ['#E8B85A', '#C98A3A', '#9A6A2E'], 'cunning': ['#B8984A', '#8A6A3A', '#6E5A8A'], 'angry': ['#B8643A', '#8A3A2A', '#5A2430']}[mood]
    bx, by = 66, 178
    for k in range(9):
        tx = 28 + k * 11
        ty = 100 + abs(k - 4) * 6
        g.shard([(bx - 12 + k * 3, by), (tx - 3, ty), (tx + 4, ty + 2), (bx - 8 + k * 3 + 6, by)], sh[k % 3], lw=.9)
    g.shard([(bx - 26, 140), (bx + 26, 140), (bx + 24, 150), (bx - 24, 150)], '#C8454F' if mood != 'angry' else '#3A1A2A', lw=1.2)
    g.lead_flush()
    # КОТ
    fur = {'neutral': ['#1C2236', '#26304A', '#141A2C'], 'kind': ['#1C2A46', '#2A4468', '#162038'], 'cunning': ['#1E1A3A', '#2E2A5A', '#14102A'], 'angry': ['#14101A', '#2A1424', '#0E0A12']}[mood]
    hi = {'neutral': '#4A5C8A', 'kind': '#4FB8C8', 'cunning': '#7C5CC8', 'angry': '#E0665A'}[mood]
    cx, cyb = 190, 142
    tilt = {'neutral': 0, 'kind': .05, 'cunning': -.14, 'angry': 0}[mood]
    # хвост
    tj = {'neutral': [(226, 170), (262, 168), (284, 146), (280, 118)], 'kind': [(226, 170), (252, 176), (232, 182), (150, 184)],
          'cunning': [(226, 170), (262, 170), (290, 150), (296, 120)], 'angry': [(226, 166), (252, 150), (252, 118), (270, 92)]}[mood]
    q, _ = chain_quads(tj, [18, 15, 12, 9])
    for k, qq in enumerate(q):
        g.shard(qq, fur[k % 3], lw=1.3)
    # туловище
    bw = 46 if not ang else 50
    body = [(cx - bw, 178), (cx - bw + 6, 140), (cx - 24, 112), (cx + 24, 112), (cx + bw - 6, 140), (cx + bw, 178)]
    g.shard(body, fur[0], lw=1.6)
    g.shard([(cx - 24, 112), (cx + 24, 112), (cx + 30, 150), (cx, 178), (cx - 30, 150)], fur[1], lw=1.2)
    g.shard([(cx - 12, 120), (cx + 12, 120), (cx + 14, 168), (cx - 14, 168)], hi if mood != 'neutral' else fur[1], lw=1.0, op=.5 if mood != 'neutral' else None)
    # шерсть-шипы по контуру
    nsp, l0, l1 = {'neutral': (10, 6, 12), 'kind': (9, 5, 10), 'cunning': (10, 7, 13), 'angry': (18, 14, 26)}[mood]
    spikes(g, (cx, 150), bw - 4, 36, nsp, l0, l1, fur, 8, 180, 360, wid=.1, lw=1.0)
    # лапы
    for px in (cx - 20, cx + 20):
        g.shard(ellipse_poly(px, 177, 14, 9, 12), fur[1], lw=1.3)
        for k in (-1, 0, 1):
            g.lead_line([(px + k * 5, 180), (px + k * 5, 184)], lw=.8)
    # лапа с подарком/подвохом
    if mood == 'kind':
        limb(g, [(cx + 30, 130), (cx + 56, 128), (cx + 78, 112)], [14, 12, 10], fur[0])
        g.circle(cx + 80, cx - 90 + 0, 0.1, fur[0], nolead=True)
        g.shard(ellipse_poly(cx + 82, 110, 8, 7, 10), fur[1], lw=1.1)
        # колос в дар
        g.glow(cx + 90, 96, 30, '#FFF3C0', .5)
        q, _ = chain_quads([(cx + 84, 108), (cx + 90, 92), (cx + 94, 74)], [2.2, 2, 1.6])
        for qq in q:
            g.shard(qq, '#E8B85A', lw=.7, grad=False)
        for k in range(4):
            yy = 70 + k * 6
            g.shard([(cx + 92, yy), (cx + 100, yy - 5), (cx + 98, yy + 3)], '#E8B85A', lw=.7, grad=False)
            g.shard([(cx + 92, yy + 2), (cx + 85, yy - 3), (cx + 88, yy + 5)], '#C98A3A', lw=.7, grad=False)
    elif mood == 'cunning':
        limb(g, [(cx + 30, 130), (cx + 52, 120), (cx + 62, 98)], [14, 12, 10], fur[0])
        g.shard(ellipse_poly(cx + 64, 94, 8, 7, 10), fur[1], lw=1.1)
        for k in (-1, 0, 1):
            g.shard([(cx + 64 + k * 4, 88), (cx + 64 + k * 5, 80), (cx + 66 + k * 4, 88)], '#E8E6F0', lw=.5, grad=False)
        g.glow(cx + 64, 78, 26, '#FF9A4A', .7)
        g.circle(cx + 64, 76, 6, '#E0443A', lw=1.2, grad=False)          # уголёк-подвох
        g.circle(cx + 64, 76, 2.8, '#FFD08A', lw=.5, grad=False)
    elif mood == 'angry':
        limb(g, [(cx + 36, 130), (cx + 62, 114), (cx + 74, 84)], [15, 12, 10], fur[0])
        limb(g, [(cx - 36, 130), (cx - 62, 114), (cx - 74, 84)], [15, 12, 10], fur[0])
        for sg in (-1, 1):
            g.shard(ellipse_poly(cx + sg * 75, 80, 9, 8, 10), fur[1], lw=1.1)
            claws(g, (cx + sg * 75, 78), -1.57 + sg * .3, 4, 9, '#F4EEDC')
    # голова
    hc = (cx, 86)
    hw, hh = 32, 27
    poly = rot(ellipse_poly(hc[0], hc[1], hw, hh, 22), hc, tilt)
    seeds = [(hc[0] + dx_, hc[1] + dy_) for dx_, dy_ in ((-16, -6), (16, -6), (0, 10), (0, -12), (-22, 8), (22, 8))]
    g.mosaic(poly, seeds, lambda x, y, i: fur[i % 3], lw=.8)
    # уши
    for sg in (-1, 1):
        g.shard(rot([(hc[0] + sg * 14, hc[1] - 20), (hc[0] + sg * 32, hc[1] - 46 - (6 if ang else 0)), (hc[0] + sg * 34, hc[1] - 12)], hc, tilt), fur[0], lw=1.4)
        g.shard(rot([(hc[0] + sg * 20, hc[1] - 22), (hc[0] + sg * 30, hc[1] - 38), (hc[0] + sg * 31, hc[1] - 18)], hc, tilt), '#C8454F' if mood != 'angry' else '#E0443A', lw=.9)
    spikes(g, hc, hw - 2, hh - 2, 7 if not ang else 11, 5, 9 if not ang else 17, fur, 12, 150, 390, wid=.13, lw=.9)
    # глаза-угольки
    ecol = {'neutral': '#FF8A3A', 'kind': '#FFC66A', 'cunning': '#FF9A4A', 'angry': '#FF3A2A'}[mood]
    lwl = 1.6
    TT = lambda p: rot([(hc[0] + p[0], hc[1] + p[1])], hc, tilt)[0]
    for sg in (-1, 1):
        ec = TT((sg * 15, -3))
        if mood == 'neutral':
            g.glow(ec[0], ec[1], 18, ecol, .6)
            g.circle(ec[0], ec[1], 8, ecol, lw=1.0, grad=False)
            g.shard([(ec[0] - 1.8, ec[1] - 7), (ec[0] + 1.8, ec[1] - 7), (ec[0] + 1.8, ec[1] + 7), (ec[0] - 1.8, ec[1] + 7)], '#1B0A10', lw=0, grad=False, nolead=True)
        elif mood == 'kind':
            g.glow(ec[0], ec[1], 14, ecol, .5)
            g.lead_line([(ec[0] + 8 * math.cos(t), ec[1] + 3 - 7 * math.sin(t)) for t in [i * math.pi / 6 for i in range(7)]], lw=2.4)
        elif mood == 'cunning':
            g.glow(ec[0], ec[1], 16, ecol, .6)
            g.shard(ellipse_poly(ec[0], ec[1] + 1, 9, 5 if sg == -1 else 4, 12), ecol, lw=1.0, grad=False)
            g.shard([(ec[0] - 9, ec[1] + 1), (ec[0] - 4, ec[1] - 5), (ec[0] + 4, ec[1] - 5), (ec[0] + 9, ec[1] + 1), (ec[0] + 6, ec[1] - 1), (ec[0] - 6, ec[1] - 1)], fur[2], lw=.5, grad=False)
            g.shard([(ec[0] - 1.2, ec[1] - 3), (ec[0] + 1.2, ec[1] - 3), (ec[0] + 1.2, ec[1] + 4), (ec[0] - 1.2, ec[1] + 4)], '#1B0A10', lw=0, grad=False, nolead=True)
        else:
            g.glow(ec[0], ec[1], 20, ecol, .8)
            g.shard([(ec[0] - sg * 9, ec[1] - 4), (ec[0] + sg * 9, ec[1] - 9), (ec[0] + sg * 8, ec[1] + 5), (ec[0] - sg * 6, ec[1] + 7)], ecol, lw=1.0, grad=False)
            g.shard([(ec[0] - 1.4, ec[1] - 6), (ec[0] + 1.4, ec[1] - 6), (ec[0] + 1.4, ec[1] + 5), (ec[0] - 1.4, ec[1] + 5)], '#1B0A10', lw=0, grad=False, nolead=True)
    # брови
    for sg in (-1, 1):
        if mood == 'angry':
            g.shard([TT((sg * 4, -12)), TT((sg * 26, -26)), TT((sg * 27, -20)), TT((sg * 8, -7))], fur[2], lw=.6, grad=False)
        elif mood == 'cunning':
            if sg == -1:
                g.lead_line([TT((-24, -20)), TT((-14, -26)), TT((-4, -19))], lw=2.0)
            else:
                g.lead_line([TT((4, -13)), TT((24, -17))], lw=2.0)
    # нос, рот, усы
    nb = TT((0, 8))
    g.shard([(nb[0] - 4, nb[1] - 2), (nb[0] + 4, nb[1] - 2), (nb[0], nb[1] + 4)], '#E87A9A' if mood != 'angry' else '#C8454F', lw=.8, grad=False)
    if mood == 'neutral':
        g.lead_line([TT((-8, 16)), TT((0, 12)), TT((8, 16))], lw=1.2)
    elif mood == 'kind':
        g.shard([TT((-12, 12)), TT((0, 20)), TT((12, 12)), TT((0, 15))], '#8A2A44', lw=.8, grad=False)
        g.lead_line([TT((0, 8)), TT((0, 13))], lw=1.0)
    elif mood == 'cunning':
        g.lead_line([TT((-14, 14)), TT((-3, 19)), TT((14, 14)), TT((20, 7))], lw=1.4)
        g.shard([TT((6, 16)), TT((11, 15)), TT((9, 22))], '#F4EEDC', lw=.4, grad=False)
        g.shard([TT((-7, 17)), TT((-2, 18)), TT((-5, 24))], '#F4EEDC', lw=.4, grad=False)
    else:
        g.shard([TT((-14, 13)), TT((-6, 11)), TT((0, 13)), TT((6, 11)), TT((14, 13)), TT((10, 25)), TT((0, 28)), TT((-10, 25))], '#2A0A14', lw=.8, grad=False)
        for xx in (-9, -3, 3, 9):
            g.shard([TT((xx - 2.5, 12)), TT((xx, 19)), TT((xx + 2.5, 12))], '#F4EEDC', lw=.4, grad=False)
    for sg in (-1, 1):
        for k, dy_ in enumerate((-3, 3, 9)):
            g.blik([TT((sg * 10, 13 + dy_ * .4)), TT((sg * 36, 8 + dy_ * 1.5))], color='#E8F4FF', w=.8, op=.7)
    if ang:   # пламя овина за спиной
        for k, (fx, fy, fh) in enumerate(((118, 170, 40), (150, 176, 30), (230, 172, 36), (262, 176, 46), (100, 178, 24))):
            g.shard([(fx - 12, fy), (fx - 4, fy - fh * .6), (fx - 2, fy - fh), (fx + 4, fy - fh * .5), (fx + 12, fy)], ['#E0443A', '#E8844A', '#C8454F'][k % 3], lw=1.0)
            g.shard([(fx - 5, fy), (fx, fy - fh * .55), (fx + 5, fy)], '#F0A24A', lw=.8, grad=False)
    g.spark(cx - 8 if mood != 'cunning' else cx + 64, 70 if mood != 'cunning' else 76, 4, '#FFFFFF', .9)
    return finish('o', g)


CREATURES = {'kikimora': kikimora, 'rusalka': rusalka, 'baba_yaga': baba_yaga, 'ovinnik': ovinnik}


def make_sheet(path, files):
    from playwright.sync_api import sync_playwright
    cells = []
    for cid in CREATURES:
        for m in MOODS:
            cells.append(f'<div><img src="file://{OUT}/{cid}_{m}.svg" width="360" height="200"><span>{cid}_{m}</span></div>')
    html = ('<html><body style="margin:0;background:#222;display:grid;grid-template-columns:repeat(4,360px);gap:4px;font:11px sans-serif;color:#ccc">'
            + ''.join(cells) + '</body></html>')
    tmp = '/tmp/spirits_b_sheet.html'
    open(tmp, 'w').write(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1452, 'height': 820})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(500)
        pg.screenshot(path=path, full_page=True)
        if os.environ.get('BIG'):
            for cid in os.environ['BIG'].split(','):
                pg2 = b.new_page(viewport={'width': 1440, 'height': 800})
                open('/tmp/_big.html', 'w').write('<body style="margin:0">' + ''.join(f'<img src="file://{OUT}/{cid}_{m}.svg" width="720" height="400" style="display:inline-block">' for m in MOODS))
                pg2.goto('file:///tmp/_big.html')
                pg2.wait_for_timeout(400)
                pg2.screenshot(path=f'/tmp/big_{cid}.png')
        b.close()


def main():
    sheet = '/tmp/spirits_b_sheet.png'
    if '--sheet' in sys.argv:
        sheet = sys.argv[sys.argv.index('--sheet') + 1]
    os.makedirs(OUT, exist_ok=True)
    bad = False
    for cid, fn in CREATURES.items():
        for m in MOODS:
            svg = fn(m)
            size, probs = check_svg(f'{cid}_{m}', svg, limit=20 * 1024)
            open(os.path.join(OUT, f'{cid}_{m}.svg'), 'w').write(svg)
            print(f'{cid}_{m}.svg {size} B', probs or '')
            bad = bad or bool(probs)
    make_sheet(sheet, None)
    print('sheet', sheet, 'PROBLEMS' if bad else 'ok')


if __name__ == '__main__':
    main()

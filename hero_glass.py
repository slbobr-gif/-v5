"""Сергей, мипл, иконка и заставки в стиле «фреска из стекла» (витраж).

Запуск (сам, build.py не нужен):
    python3 tools/art/hero_glass.py [--sheet /tmp/glass_sheet.png] [--no-icons]

Пишет:
  app/assets/art/hero/sergey.svg, sergey_back.svg, sergey_marker.svg
  app/assets/art/icon/icon.svg + android-overlay/res/mipmap-*/ic_launcher*.png + drawable/ic_stat_putnik.xml
  app/assets/art/intro/intro_1..6_*.svg   (модуль hero_glass_intro.py)
Всё рисуется кодом, внешних изображений нет. Проверяет запреты flutter_svg и размер ≤ 25 КБ.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hero_glass_lib import *  # noqa: F401,F403
from hero_glass_lib import _rgb, _hex  # noqa: F401

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ART = os.path.join(ROOT, 'app', 'assets', 'art')
RES = os.path.join(ROOT, 'app', 'android-overlay', 'res')

# ---- палитра героя ----------------------------------------------------------------
JK = ('#31B4CC', '#1F93BC', '#1B72AA')      # куртка: плечи / корпус / низ
JK_DK = ('#1B8CA8', '#17719A', '#155A8C')   # куртка в тени
PANTS = '#2B3E9E'
PANTS_FAR = '#222F7E'
BOOT = '#43305F'
BOOT_FAR = '#33254B'
PACK = ('#DC5E60', '#B8404E', '#932F46')
STRAP = '#2B2048'
ROLL = ('#34D1C6', '#1FA7A2')
POLE = '#BFCBEA'


def _scale(p, c, k):
    return [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in p]


def walker_profile(g, ox, oy, s, detail='full', fat=1.0, headk=1.0, lw=1.5, lw_face=0.8, pole=True, rim=True, pal=None):
    """Сергей в профиль, идёт вправо. (ox, oy) — точка земли под центром фигуры, s — масштаб (рост = 100 ед.).
    detail: 'full' — лицо, много осколков; 'mid' — голова без мелочей; 'mini' — минимум осколков.
    Ноги: передняя (дальняя от зрителя) вперёд, стопа смотрит вправо; задняя (ближняя) отталкивается
    носком (пятка приподнята), стопа тоже смотрит вправо. Рука с палкой — вперёд."""
    T = lambda p: (ox + p[0] * s, oy + p[1] * s)
    TL = lambda pts: [T(p) for p in pts]
    pal = pal or {}
    jk = pal.get('jk', JK)
    full = detail == 'full'
    mini = detail == 'mini'
    hip = (1, -50)

    def part(pts, color, w=None, grad=True, nolead=False):
        g.shard(TL(pts), color, lw=lw if w is None else w, grad=grad, nolead=nolead)

    # --- дальняя (передняя по ходу) нога
    knee_f, ank_f = (11, -27), (17.5, -4.5)
    q, _ = chain_quads([hip, knee_f, ank_f], [9.5 * fat, 7.6 * fat, 5.8 * fat])
    part(q[0], PANTS_FAR)
    part(q[1], '#26359A')
    part([(14.2, -3.4), (20.8, -5.8), (27.5, -4.8), (28.4, -1.9), (13.6, 0.3), (12.2, -1.9)], BOOT_FAR)
    if not mini:
        part([(13.6, 0.3), (28.4, -1.9), (28.2, -3.2), (13.1, -1.0)], '#17102A', w=lw * 0.5, grad=False)

    # --- рюкзак (за спиной) и скатка
    part([(-8, -83.5), (-17, -85), (-24, -80.5), (-25.5, -72), (-8, -71)], PACK[0])
    part([(-8, -71), (-25.5, -72), (-27, -62), (-25.5, -52), (-20.5, -48.5), (-8, -49.5)], PACK[1])
    if not mini:
        part([(-26.6, -62), (-15.5, -61), (-15, -51.8), (-20.5, -49), (-25.4, -52.2)], PACK[2])
    rc = (-15, -91)
    g.circle(*T(rc), 5.4 * s, ROLL[0], lw=lw)
    if not mini:
        g.circle(*T(rc), 2.5 * s, ROLL[1], lw=lw * 0.6)

    # --- ближняя (задняя) нога: отталкивание
    knee_n, ank_n = (-4, -28), (-13.5, -10)
    q2, _ = chain_quads([hip, knee_n, ank_n], [9.8 * fat, 7.8 * fat, 5.9 * fat])
    part(q2[0], PANTS)
    part(q2[1], '#3550B8')
    part([(-16, -11.4), (-10.9, -8.6), (-3.5, -3.6), (-0.4, -0.4), (-1.6, 0.4), (-5.2, 0.4), (-17.6, -6), (-18.6, -9.6)], BOOT)
    if not mini:
        part([(-17.6, -6), (-5.2, 0.4), (-1.6, 0.4), (-2.6, -0.9), (-6.4, -1.0), (-17.9, -7.6)], '#17102A', w=lw * 0.5, grad=False)

    # --- корпус (куртка) с лёгким наклоном вперёд
    lean = lambda p: (p[0] + (-(p[1] + 50)) * 0.055, p[1])
    LJ = lambda pts: [lean(p) for p in pts]
    if mini:
        part(LJ([(-4.5, -85), (3, -87.2), (8.2, -83), (10, -75), (9.4, -60), (8.8, -47.2), (-7.8, -47.2), (-8.8, -72)]), jk[1])
    else:
        part(LJ([(-4.5, -85), (3, -87.2), (8.2, -83), (10, -75), (8.8, -68.5), (-8.2, -70.5), (-9, -78)]), jk[1])
        part(LJ([(-8.2, -70.5), (8.8, -68.5), (9.4, -60.5), (9, -55), (-8.8, -55)]), jk[2])
        part(LJ([(-8.8, -55), (9, -55), (8.8, -47.2), (-7.8, -47.2)]), '#1A63A0')
    # шея и воротник
    part([(0.2, -92), (6.8, -91.4), (7.6, -86.2), (-0.8, -85.8)], '#C38660', nolead=True)
    part(LJ([(-4.6, -85.4), (-0.6, -87.4), (3.4, -87.9), (7.2, -87.0), (9.4, -84.2), (-4.8, -82.4)]), '#7AE0DB' if not mini else jk[0], w=lw * 0.8)

    # --- ближняя рука с палкой (рукав: плечо+локоть, предплечье)
    if pole:
        part([(15.4, -59.5), (16.8, -59.5), (33.6, 0.4), (32.2, 0.4)], POLE, w=lw * 0.5, grad=False)
    arm1, arm2 = pal.get('arm', ('#38BFD6', '#2AA6C6'))
    part([(-0.4, -78.6), (0.4, -82.8), (3.6, -85), (7.6, -82.4), (13.7, -66.9), (7.5, -64.1)], arm1)
    part([(13.7, -66.9), (17.96, -55.5), (13.64, -53.5), (7.5, -64.1)], arm2)
    if not mini:
        part([(17.96, -55.5), (13.64, -53.5), (13.3, -51.9), (18.4, -53.8)], '#1B6FA0', w=lw * 0.6)
        part([(13.8, -60.6), (17.4, -59.4), (18.0, -52.6), (14.6, -52.0)], '#E0706A', w=lw * 0.6)
    g.circle(*T((16.9, -52.0)), 2.8 * s, SKIN, lw=lw * 0.7)

    # --- голова
    hc = (3.4, -94.2)
    HL = lambda pts: [T((hc[0] + x * headk, hc[1] + y * headk)) for x, y in pts]

    def hp(pts, color, w=None, grad=True):
        g.shard(HL(pts), color, lw=(lw_face if w is None else w), grad=grad)

    if full:
        hp([(-7.4, 1), (-7, -3.4), (-2.2, -2.8), (-3.2, 0.4), (-3.6, 3.8), (-6.3, 4.4)], '#9C7444')
        hp([(-7, -3.4), (-4.8, -7.2), (0, -8.8), (-1.6, -5.4), (-2.2, -2.8)], HAIR)
        hp([(0, -8.8), (5, -7.4), (7.2, -4.0), (7.0, -2.6), (3.6, -3.6), (-1.6, -5.4)], HAIR_HI)
        hp([(-3.6, -2.0), (-1.4, -2.4), (-1.0, 1.2), (-2.8, 1.8), (-3.8, -0.2)], SKIN_SH)
        hp([(7.0, -2.6), (3.6, -3.6), (-1.6, -5.4), (-2.2, -2.8), (-3.2, 0.4), (2.6, 1.9), (7.0, 0.6), (7.4, -1.0)], SKIN)
        hp([(-3.2, 0.4), (2.6, 1.9), (7.0, 0.6), (7.6, 3.0), (8.0, 4.2), (4.8, 4.9), (1.8, 4.4), (-1.2, 2.9)], SKIN_HI)
        hp([(-1.2, 2.9), (1.8, 4.4), (4.8, 4.9), (8.0, 4.2), (7.4, 6.0), (5.6, 7.4), (1.6, 6.4), (-3.6, 3.8)], '#B27C5C')
        hp([(7.0, 0.6), (10.2, 2.7), (7.6, 3.1)], SKIN_HI)
        g.blik(HL([(2.7, -0.9), (3.3, -1.9), (4.3, -2.4), (5.3, -2.0), (5.9, -1.0)]), color='#2A1A1E', w=0.45 * s + 0.2, op=0.95)    # прищур-улыбка
        g.blik(HL([(2.2, -3.9), (4.4, -4.5), (6.6, -4.3)]), color='#7A5430', w=0.45 * s + 0.2, op=0.95)                 # бровь
        g.blik(HL([(5.0, 4.2), (6.2, 5.0), (7.4, 4.5), (7.9, 3.9)]), color='#7A3F3A', w=0.35 * s + 0.2, op=0.9)        # улыбка
        g.blik(HL([(3.6, 2.6), (4.2, 3.6)]), color='#B27C5C', w=0.3 * s + 0.2, op=0.8)                                 # складка щеки
    else:
        hp([(-7.4, 1), (-7, -3.4), (-2.2, -2.8), (-3.6, 3.8), (-6.3, 4.4)], '#9C7444', w=lw * 0.7)
        hp([(-7, -3.4), (-4.8, -7.2), (0, -8.8), (-1.6, -5.4), (-2.2, -2.8)], HAIR, w=lw * 0.7)
        hp([(0, -8.8), (5, -7.4), (7.2, -4.0), (7.0, -2.6), (3.6, -3.6), (-1.6, -5.4)], HAIR_HI, w=lw * 0.7)
        hp([(7.0, -2.6), (3.6, -3.6), (-1.6, -5.4), (-2.2, -2.8), (-3.6, 3.8), (1.6, 6.8), (5.6, 7.4), (7.8, 5.8), (8.0, 4.2), (7.6, 3.1), (10.2, 2.7), (7.2, 0.5)], SKIN, w=lw * 0.7)
        if not mini:
            g.blik(HL([(2.7, -0.9), (3.3, -1.9), (4.3, -2.4), (5.3, -2.0), (5.9, -1.0)]), color='#2A1A1E', w=0.45 * s + 0.2, op=0.95)

    if rim:
        r = '#D8FFF8'
        g.blik(TL([(9.4, -80), (10.4, -72), (9.6, -62)]), color=r, w=0.9, op=0.5)
        g.blik(TL([(16, -27.5), (20.8, -6)]), color=r, w=0.8, op=0.4)


def walker_back(g, ox, oy, s, lw=1.5, lw_face=0.8, pole=True, rim=True, detail='full'):
    """Сергей со спины, идёт от зрителя. (ox, oy) — земля под центром, s — масштаб (рост ≈ 103 ед.).
    Левая (для зрителя) нога отталкивается (пятка поднята, видна подошва), правая — на земле."""
    T = lambda p: (ox + p[0] * s, oy + p[1] * s)
    TL = lambda pts: [T(p) for p in pts]

    def part(pts, color, w=None, grad=True, nolead=False):
        g.shard(TL(pts), color, lw=lw if w is None else w, grad=grad, nolead=nolead)

    # ноги
    ql, _ = chain_quads([(-5.4, -50), (-7.6, -28), (-9.4, -10.5)], [10.5, 8.2, 6.4])
    part(ql[0], PANTS)
    part(ql[1], '#3550B8')
    part([(-12.4, -12.4), (-6.4, -9.2), (-6.0, -3.0), (-12.4, -4.2)], BOOT)                 # пятка приподнята
    part([(-12.4, -4.2), (-6.0, -3.0), (-5.6, -0.4), (-12.6, -0.8)], '#17102A', w=lw * 0.5, grad=False)   # подошва
    qr, _ = chain_quads([(5.4, -50), (6.6, -27), (7.8, -5.5)], [10.5, 8.4, 6.6])
    part(qr[0], '#263A9C')
    part(qr[1], PANTS_FAR if False else '#2B3E9E')
    part([(4.2, -8), (11.4, -8), (12.8, -1.6), (3.4, -1.6)], BOOT)
    part([(3.4, -1.6), (12.8, -1.6), (13.4, 0.5), (3.0, 0.5)], '#17102A', w=lw * 0.5, grad=False)
    # руки
    if pole:
        part([(21.2, -58), (22.4, -58), (28.2, 0), (26.8, 0)], POLE, w=lw * 0.5, grad=False)
    ala, _ = chain_quads([(-15.8, -81), (-19.2, -66), (-18.4, -53.5)], [8.4, 7.2, 5.8])
    part(ala[0], '#2AA6C6')
    part(ala[1], '#1F93BC')
    g.circle(*T((-18.2, -51.2)), 2.8 * s, SKIN, lw=lw * 0.7)
    ara, _ = chain_quads([(15.8, -81), (19.6, -66), (21.2, -55)], [8.4, 7.2, 5.8])
    part(ara[0], '#38BFD6')
    part(ara[1], '#2AA6C6')
    g.circle(*T((21.8, -52.6)), 2.8 * s, SKIN, lw=lw * 0.7)
    # куртка-подол и плечи (по бокам от рюкзака)
    part([(-17.5, -83), (-9, -86), (9, -86), (17.5, -83), (18, -75), (13, -50), (-13, -50), (-18, -75)], '#1F93BC')
    # рюкзак
    part([(-12.6, -87), (12.6, -87), (14, -74), (-14, -74)], PACK[0])
    part([(-14, -74), (14, -74), (13.6, -52), (-13.6, -52)], PACK[1])
    part([(-8, -66), (8, -66), (8, -54), (-8, -54)], PACK[2])
    part([(-14, -70.5), (14, -70.5), (14, -68.5), (-14, -68.5)], STRAP, w=lw * 0.5, grad=False)
    # скатка наверху (цилиндр, вид с торца-спины)
    part([(-14.6, -89.6), (14.6, -89.6), (14.6, -81.2), (-14.6, -81.2)], ROLL[0], w=lw)
    part([(-14.6, -85.4), (14.6, -85.4), (14.6, -84.6), (-14.6, -84.6)], ROLL[1], w=lw * 0.5, grad=False)
    g.blik(TL([(-10, -87.8), (10, -87.8)]), color='#CFFBF5', w=0.8, op=0.6)
    # шея и голова (русые волосы, затылок)
    part([(-3, -93), (3, -93), (3.6, -86.5), (-3.6, -86.5)], '#C38660', nolead=True)
    part([(-7.2, -96.5), (-6.6, -92), (-7.6, -92), (-8.2, -96)], SKIN_SH, w=lw_face)
    part([(7.2, -96.5), (6.6, -92), (7.6, -92), (8.2, -96)], SKIN_SH, w=lw_face)
    hc = (0, -96.4)
    HL = lambda pts: [T((hc[0] + x, hc[1] + y)) for x, y in pts]

    def hp(pts, color, w=None):
        g.shard(HL(pts), color, lw=(lw_face if w is None else w))
    hp([(-7.4, -1.5), (-6.8, -5.5), (-3.6, -8.6), (0, -9.4), (-1.2, -2.5)], HAIR)
    hp([(0, -9.4), (3.6, -8.6), (6.8, -5.5), (7.4, -1.5), (1.2, -2.5)], HAIR_HI)
    hp([(-7.4, -1.5), (-1.2, -2.5), (0, 4.6), (-3.2, 5.8), (-6.4, 3.4)], '#9C7444')
    hp([(7.4, -1.5), (1.2, -2.5), (0, 4.6), (3.2, 5.8), (6.4, 3.4)], HAIR)
    hp([(-1.2, -2.5), (1.2, -2.5), (0, 4.6)], '#8A6234')
    if rim:
        r = '#E8FFFB'
        g.blik(HL([(-6.6, -5), (-3.6, -8.4), (0, -9.2), (3.6, -8.4), (6.6, -5)]), color=r, w=1.0, op=0.7)
        g.blik(TL([(-17.4, -82), (-9, -85.6)]), color=r, w=0.9, op=0.55)
        g.blik(TL([(17.4, -82), (9, -85.6)]), color=r, w=0.9, op=0.55)
        g.blik(TL([(-13.8, -74), (-13.4, -53)]), color=r, w=0.8, op=0.4)
        g.blik(TL([(13.8, -74), (13.4, -53)]), color=r, w=0.8, op=0.4)


# ============================================================================
#  sergey.svg
# ============================================================================
def arch_frame(g, P, width, cols, lw=2.0):
    """Рамка-арка из осколков-кирпичиков. Возвращает внутренний контур."""
    outer = arch_poly(P, 0, n=9, side=3)
    inner = arch_poly(P, width, n=9, side=3)
    keep = g.light
    g.light = None
    for k in range(len(outer)):
        k2 = (k + 1) % len(outer)
        g.shard([outer[k], outer[k2], inner[k2], inner[k]], cols[k % len(cols)], lw=lw, grad=False)
    g.light = keep
    return inner


def sergey():
    g = Glass(200, 240, 'sg', prec=0, lw=1.7, light=(104, 118))
    P = arch_params(8, 192, 135, 8, 234, R=130)
    inner = arch_frame(g, P, 11, [BLUE, '#24408F', '#1F6E92', '#33307F', '#1B5F7C'])
    hx, hy = 102, 120

    def sky_col(x, y, i):
        d = math.hypot(x - hx, (y - hy) * 0.95)
        r2 = random.Random(int(x * 7 + y * 13))
        if d < 46:  # сияющий ореол за героем
            seq = ['#D7F9F4', '#A9EFE7', '#74E0D6', '#3ECDC3']
            return seq[min(3, int(d / 46 * 3.2 + r2.random() * 0.9))]
        if d < 54:
            return r2.choice(['#2BC4BA', '#1F9E9A', '#34D4C8'])
        ya = 46 + 14 * math.sin(x / 26.0)
        yb = 86 + 10 * math.sin(x / 21.0 + 1.5)
        if abs(y - ya) < 13:
            return r2.choice(['#2FD0A0', '#1F9E6B', '#38D9B0', '#2BC4BA'])
        if abs(y - yb) < 8 and x > 20:
            return r2.choice(['#1F9E6B', '#1A8F85', '#2BC4BA'])
        t = max(0, min(1, y / 175))
        seq = ['#0B1244', '#101C5A', '#16296B', '#1B3A86', '#2B3E9E', '#4A3A9E']
        return seq[min(5, int(t * 3.6 + r2.random() * 1.6))]

    def rf(x, y):
        d = math.hypot(x - hx, y - hy)
        return 20 + 0.06 * d + (3 if y < 50 else 0)

    seeds = poisson((8, 8, 192, 234), rf, 11, 6000, accept=lambda x, y: point_in(inner, x, y))
    sk = [p for p in seeds if p[1] < 190]
    g.mosaic(clip_half(inner, 0, 190, 0, 1), sk, sky_col, lw=1.6)
    g.glow(hx, hy, 80, '#9FF5EA', 0.42)
    g.glow(hx, hy + 4, 44, '#E8FFFB', 0.34)
    g.lead_flush()
    # дальние горы-грани (свет/тень)
    peaks = [(8, 186, 30, 164, 58, 186), (44, 186, 80, 170, 118, 186), (104, 186, 140, 158, 178, 186), (150, 186, 176, 168, 192, 186)]
    for (x0, y0, xp, yp, x1, y1) in peaks:
        lit = clip_convex([(x0, y0), (xp, yp), (xp + 4, y0)], inner)
        dark = clip_convex([(xp, yp), (x1, y1), (xp + 4, y0)], inner)
        if len(lit) >= 3:
            g.shard(lit, '#1E8296', lw=1.6)
        if len(dark) >= 3:
            g.shard(dark, '#165B78', lw=1.6)
    # земля: изумрудно-бирюзовые тёмные осколки
    gr = clip_half(inner, 0, 186, 0, -1)
    gs = [p for p in poisson((8, 186, 192, 234), lambda x, y: 22, 3, 800, accept=lambda x, y: point_in(inner, x, y)) if p[1] > 188]
    g.mosaic(gr, gs, lambda x, y, i: ['#145A52', '#0F4A4A', '#17695A', '#124A5E'][i % 4], lw=1.7)
    g.lead_flush()
    # тропа: светлое стекло под ногами
    path = clip_convex([(8, 217), (192, 212), (192, 236), (8, 236)], inner)
    ps = poisson((8, 212, 192, 236), lambda x, y: 12, 5, 700, accept=lambda x, y: point_in(path, x, y))
    g.mosaic(path, ps, lambda x, y, i: ['#7FD9D2', '#A5E8E0', '#5FC9C4', '#C9F2EC'][i % 4], lw=1.5)
    g.lead_flush()
    # герой
    g.prec = 1
    g.light = (60, 40)
    walker_profile(g, 98, 224, 1.84, 'full', lw=1.5)
    g.lead_flush()
    g.prec = 0
    for (x, y, r) in [(34, 40, 3), (160, 46, 2.4), (152, 88, 2), (28, 100, 2)]:
        g.spark(x, y, r, MILK, 0.85)
    return g.render()


def glory(g, cx, cy, region, n=16, rot=0.0, cols=None, R=400, light=None):
    """Сияющие лучи-клинья (витражная «слава») из точки (cx, cy), обрезаны выпуклой областью."""
    cols = cols or ['#BDF4EE', '#5FD9D0']
    for i in range(n):
        a0 = rot + 2 * math.pi * i / n
        a1 = rot + 2 * math.pi * (i + 1) / n
        w = [(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos((a0 + a1) / 2), cy + R * math.sin((a0 + a1) / 2)), (cx + R * math.cos(a1), cy + R * math.sin(a1))]
        c = clip_convex(w, region)
        if len(c) >= 3:
            g.shard(c, cols[i % len(cols)], grad=True)


def sergey_back():
    g = Glass(200, 240, 'sb', prec=0, lw=1.7, light=(100, 120))
    P = arch_params(8, 192, 135, 8, 234, R=130)
    inner = arch_frame(g, P, 11, [BLUE, '#33307F', '#1B5F7C', '#24408F', '#1F6E92'])
    hx, hy = 100, 122
    sky_r = clip_half(inner, 0, 172, 0, 1)
    # лучи «славы» за героем
    glory(g, hx, hy + 18, sky_r, n=18, rot=0.1, cols=['#9FEFE7', '#2FB6B6', '#1F8FA8', '#2B6FB0'])
    # сияние-ленты по небу (поверх лучей, у краёв)
    g.glow(hx, hy + 10, 70, '#E8FFFB', 0.50)
    g.glow(hx, hy + 18, 34, '#FFFFFF', 0.35)
    g.lead_flush()
    # горы-грани у горизонта
    for (x0, xp, yp, x1) in [(8, 36, 156, 80), (60, 92, 164, 140), (118, 150, 150, 192)]:
        lit = clip_convex([(x0, 176), (xp, yp), (xp + 4, 176)], inner)
        dark = clip_convex([(xp, yp), (x1, 176), (xp + 4, 176)], inner)
        if len(lit) >= 3:
            g.shard(lit, '#1B7E96', lw=1.6)
        if len(dark) >= 3:
            g.shard(dark, '#14566F', lw=1.6)
    gr = clip_half(inner, 0, 172, 0, -1)
    gs = [p for p in poisson((8, 172, 192, 234), lambda x, y: 20, 9, 700, accept=lambda x, y: point_in(inner, x, y)) if p[1] > 174]
    g.mosaic(gr, gs, lambda x, y, i: ['#145A52', '#0F4A4A', '#17695A', '#124A5E'][i % 4], lw=1.7)
    # дорога в перспективе к свету (светлое стекло)
    vx, vy = 100, 171
    rows = [171, 176, 183, 192, 203, 217, 236]
    m = 3
    for k in range(len(rows) - 1):
        ya, yb = rows[k], rows[k + 1]
        wa, wb = (ya - vy) * 1.15 + 1.5, (yb - vy) * 1.15 + 1.5
        for i in range(m):
            q = [(vx - wa + 2 * wa * i / m, ya), (vx - wa + 2 * wa * (i + 1) / m, ya), (vx - wb + 2 * wb * (i + 1) / m, yb), (vx - wb + 2 * wb * i / m, yb)]
            q = clip_convex(q, inner)
            if len(q) >= 3:
                g.shard(q, ['#CFF7F1', '#8FE6DE', '#B5EFE9', '#6FD8D0'][(i + k) % 4], lw=1.4)
    g.lead_flush()
    g.prec = 1
    g.light = (100, 60)
    walker_back(g, 100, 224, 1.8, lw=1.5)
    g.lead_flush()
    g.prec = 0
    for (x, y, r) in [(38, 40, 3), (164, 50, 2.4), (32, 100, 2), (170, 104, 2)]:
        g.spark(x, y, r, MILK, 0.85)
    return g.render()


def marker_figure(g, lw=1.0):
    """Упрощённая крупная фигурка Сергея для 48×48 (читается на 24 px): профиль вправо,
    передняя нога вперёд, задняя назад, обе стопы смотрят вправо."""
    L = lw
    # задняя нога (отталкивание)
    q, _ = chain_quads([(23.4, 25), (20.4, 31.0), (16.8, 35.0)], [4.0, 3.5, 3.0])
    g.shard(q[0], '#2B3FA8', lw=L)
    g.shard(q[1], '#3A52C2', lw=L)
    g.shard([(15.6, 33.8), (19.0, 34.2), (22.0, 37.2), (22.8, 38.6), (19.4, 38.6), (14.8, 36.0)], '#3A2660', lw=L)
    # передняя нога
    q, _ = chain_quads([(25.0, 25), (28.8, 31.4), (30.4, 36.0)], [4.2, 3.6, 3.0])
    g.shard(q[0], '#1E2F86', lw=L)
    g.shard(q[1], '#26389A', lw=L)
    g.shard([(28.6, 35.0), (31.8, 35.4), (34.4, 36.6), (34.4, 38.6), (28.2, 38.6)], '#2B1E4A', lw=L)
    # рюкзак и скатка
    g.shard([(15.4, 15.2), (21.6, 15.6), (21.6, 25.2), (16.6, 25.6), (14.4, 21.4)], '#DC5E60', lw=L)
    g.circle(17.4, 13.2, 2.5, '#0E8E94', lw=L)
    # корпус
    g.shard([(22.2, 15.4), (27.8, 15.0), (29.0, 21.4), (28.4, 26.2), (21.6, 26.2), (21.0, 19.4)], '#1B5FA6', lw=L)
    # рука и палка
    g.shard([(31.0, 22.4), (36.4, 38.4), (35.0, 38.6), (29.8, 23.0)], '#E8EEFF', lw=0.7, grad=False)
    g.shard([(23.6, 16.2), (27.0, 16.0), (31.2, 22.0), (28.6, 23.6)], '#3C8FD0', lw=L)
    g.circle(30.2, 23.0, 1.7, SKIN, lw=0.8)
    # голова
    g.shard([(21.4, 11.0), (22.0, 7.6), (24.8, 5.6), (28.2, 6.2), (29.6, 9.0), (26.8, 8.8), (24.0, 9.6)], HAIR, lw=L)
    g.shard([(26.8, 8.8), (29.6, 9.0), (28.6, 7.0)], HAIR_HI, lw=0.6)
    g.shard([(21.4, 11.0), (24.0, 9.6), (23.8, 13.6), (21.8, 13.4)], '#9C7444', lw=0.8)
    g.shard([(24.0, 9.6), (26.8, 8.8), (29.6, 9.0), (31.2, 11.6), (29.4, 12.2), (28.6, 14.4), (25.6, 15.2), (23.8, 13.6)], SKIN, lw=L)


def marker():
    """Мипл на карте: свинцовый медальон, бирюзовое стекло, Сергей в профиль идёт вправо."""
    g = Glass(48, 48, 'mk', prec=1, lw=1.3, light=(24, 10), bg=None)
    g.glow(24, 24, 24, '#2BC4BA', 0.55, mid=0.6)
    g.lead_flush()
    reg = circle_poly(24, 24, 20.4, 36)
    cols = ['#8DEDE2', '#2BC4BA', '#6FDDD2']
    n = 3
    for i in range(n):
        a0 = 0.35 + 2 * math.pi * i / n
        a1 = 0.35 + 2 * math.pi * (i + 1) / n
        R = 40
        c = clip_convex([(24, 21), (24 + R * math.cos(a0), 21 + R * math.sin(a0)), (24 + R * math.cos((a0 + a1) / 2), 21 + R * math.sin((a0 + a1) / 2)), (24 + R * math.cos(a1), 21 + R * math.sin(a1))], reg)
        if len(c) >= 3:
            g.shard(c, cols[i % len(cols)], lw=0.9)
    g.shard(clip_half(reg, 0, 38.0, 0, -1), '#0F5E6E', lw=0.9)
    g.glow(24, 22, 17, '#E8FFFB', 0.30)
    g.lead_flush()
    marker_figure(g, lw=0.95)
    g.lead_flush()
    g.lead_circle(24, 24, 20.9, lw=3.0)
    g.lead_flush()
    g.spark(39, 10, 1.7, MILK, 0.9)
    return g.render()


def rrect_poly(x, y, w, h, r, k=10):
    out = []
    for (cx, cy, a0) in [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)]:
        for j in range(k + 1):
            a = math.radians(a0 + 90 * j / k)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def whale_tail(g, x, y, k, color='#0F2C5C', lw=1.6):
    """Хвост кита над водой (витражные осколки)."""
    g.shard([(x - 2.2 * k, y), (x + 2.2 * k, y), (x + 1.6 * k, y - 13 * k), (x - 1.6 * k, y - 13 * k)], '#1B4F8C', lw=lw)
    g.shard([(x - 1.6 * k, y - 12.5 * k), (x - 15 * k, y - 24 * k), (x - 12.5 * k, y - 15 * k), (x - 4 * k, y - 10.5 * k)], color, lw=lw)
    g.shard([(x + 1.6 * k, y - 12.5 * k), (x + 15 * k, y - 24 * k), (x + 12.5 * k, y - 15 * k), (x + 4 * k, y - 10.5 * k)], '#2B5FA8', lw=lw)


def icon():
    # v5.3: иконка выбрана владельцем — «Хвост кита» (tools/art/app_icon.svg)
    return open(os.path.join(os.path.dirname(__file__), 'app_icon.svg'), encoding='utf-8').read()


def icon_old():
    """512×512, скругление 112: стрельчатое витражное окошко ночного неба с сиянием, тропа, Сергей, хвост кита."""
    g = Glass(512, 512, 'ic', prec=0, lw=5.0, light=(330, 330), bg=None)
    plate = rrect_poly(0, 0, 512, 512, 112, 12)
    g.shard(plate, '#0B1424', lw=0, grad=False)
    g.glow(256, 262, 262, '#2BC4BA', 0.34, mid=0.7)
    g.lead_flush()
    g.lead_line(rrect_poly(12, 12, 488, 488, 100, 12), lw=16, closed=True)
    g.lead_flush()
    P = arch_params(60, 452, 318, 40, 466, R=292)
    inner = arch_frame(g, P, 26, ['#1B4F8C', '#2B3E9E', '#1F8FA8', '#5B3FA0', '#1B7E96'], lw=6)
    vx, vy = 330, 338
    sky = clip_half(inner, 0, 345, 0, 1)
    glory(g, vx, vy, sky, n=15, rot=-0.15, cols=['#8FF0E6', '#2BC4BA', '#1F9E6B', '#1B8FB5', '#2B3E9E', '#34D4B0'])
    # ночь сверху: полупрозрачный градиент поверх лучей
    g.flush()
    nt = g.linear([(0, '#0B1424', 0.92), (0.55, '#0B1424', 0.35), (1, '#0B1424', 0)], 0, 0, 0, 1)
    top = clip_half(inner, 0, 250, 0, 1)
    g.shard(top, nt, lw=0, grad=False, nolead=True)
    g.glow(vx, vy, 150, '#E8FFFB', 0.55)
    g.lead_flush()
    # море и хвост кита у горизонта
    sea = clip_convex([(60, 346), (452, 346), (452, 382), (60, 382)], inner)
    g.shard(sea, '#14407E', lw=5)
    whale_tail(g, 398, 352, 2.3, lw=4)
    for (a, b, c) in [(380, 330, 3), (418, 326, 2.4), (404, 316, 2)]:
        g.circle(a, b, c, '#BDF4EE', lw=0, nolead=True)
    # горы-грани
    for (x0, xp, yp, x1) in [(86, 124, 314, 190)]:
        lit = clip_convex([(x0, 372), (xp, yp), (xp + 8, 372)], inner)
        dark = clip_convex([(xp, yp), (x1, 372), (xp + 8, 372)], inner)
        if len(lit) >= 3:
            g.shard(lit, '#1E8296', lw=5)
        if len(dark) >= 3:
            g.shard(dark, '#165B78', lw=5)
    # земля
    gr = clip_half(inner, 0, 374, 0, -1)
    gs = [p for p in poisson((60, 374, 452, 440), lambda x, y: 56, 4, 500, accept=lambda x, y: point_in(inner, x, y)) if p[1] > 380]
    g.mosaic(gr, gs, lambda x, y, i: ['#145A52', '#0F4A4A', '#17695A', '#124A5E'][i % 4], lw=5)
    # тропа под ногами (светлое стекло)
    band = clip_convex([(60, 410), (452, 404), (452, 446), (60, 450)], inner)
    for i, (xa, xb) in enumerate([(60, 160), (160, 250), (250, 345), (345, 452)]):
        c = clip_convex(band, [(xa, 400), (xb, 400), (xb, 480), (xa, 480)])
        if len(c) >= 3:
            g.shard(c, ['#D5F8F2', '#9AEAE1', '#BDF2EC', '#78DDD4'][i], lw=5)
    g.lead_flush()
    # свет за героем и сам герой
    g.glow(228, 316, 150, '#E8FFFB', 0.5)
    g.lead_flush()
    g.light = (330, 200)
    walker_profile(g, 226, 426, 2.3, 'mid', fat=1.3, headk=1.2, lw=5.2, lw_face=3.2, rim=False)
    g.lead_flush()
    for (x, y, r) in [(120, 120, 9), (372, 108, 7), (96, 232, 6), (428, 230, 6), (240, 96, 7)]:
        g.spark(x, y, r, MILK, 0.9)
    return g.render()


def stat_icon_xml():
    return '''<?xml version="1.0" encoding="utf-8"?>
<!-- Монохромный значок уведомления: путник в шаге вправо (передняя нога вперёд, задняя назад, стопы смотрят по ходу), с рюкзаком и палкой. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M14.2,1.4a2.2,2.2 0,1 0,0.01 0z" />
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M7,7.6L11,6.8L10.6,13.2L7.4,13Z M7.4,4.6a1.4,1.4 0,1 0,2.8 0a1.4,1.4 0,1 0,-2.8 0z" />
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M15.2,20.6L17.8,20.4L19.8,21.6L19.8,22.8L15,22.8Z M5.4,19.4L7.8,19.6L10,21.8L10.6,22.8L7.6,22.8L5,21Z" />
    <path
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="3.6"
        android:strokeLineCap="round"
        android:pathData="M13.2,7.8L11.6,13" />
    <path
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="2.8"
        android:strokeLineCap="round"
        android:strokeLineJoin="round"
        android:pathData="M12.4,13.6L15,17.8L16.2,20.8 M11.4,13.6L9.6,17.6L6.9,19.6" />
    <path
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="2.2"
        android:strokeLineCap="round"
        android:pathData="M13.4,8.8L16.6,12.2" />
    <path
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="1.2"
        android:strokeLineCap="round"
        android:pathData="M17,11.2L20.4,22.4" />
</vector>
'''


def point_in(poly, x, y):
    c = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            c = not c
        j = i
    return c


def clip_convex_safe(poly, clip):
    r = clip_convex(poly, clip)
    return r


def intro_files():
    import hero_glass_intro as hi
    return hi.collect()


def collect(with_intro=True):
    out = {}
    out['hero/sergey.svg'] = sergey()
    out['hero/sergey_back.svg'] = sergey_back()
    out['hero/sergey_marker.svg'] = marker()
    out['icon/icon.svg'] = icon()
    if with_intro:
        out.update(intro_files())
    return out


def write(files):
    bad = []
    for rel, svg in files.items():
        p = os.path.join(ART, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(svg)
        size, probs = check_svg(rel, svg)
        print(f'{rel}: {size} B', 'OK' if not probs else probs)
        if probs:
            bad.append((rel, probs))
    return bad


def render_png(svg, size, path, bg=None):
    import base64
    from playwright.sync_api import sync_playwright
    b64 = base64.b64encode(svg.encode()).decode()
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': size, 'height': size})
        pg.set_content(f'<html><body style="margin:0;background:{bg or "transparent"}">'
                       f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" style="display:block"></body></html>')
        pg.wait_for_timeout(120)
        pg.screenshot(path=path, omit_background=bg is None)
        br.close()


def write_android(icon_svg):
    import app_icon
    app_icon.main()   # mipmap-иконки (обычная, круглая, adaptive) — из tools/art/app_icon.svg
    dr = os.path.join(RES, 'drawable')
    os.makedirs(dr, exist_ok=True)
    with open(os.path.join(dr, 'ic_stat_putnik.xml'), 'w', encoding='utf-8') as fh:
        fh.write(stat_icon_xml())
    print('android: mipmap-*/ic_launcher.png, drawable/ic_stat_putnik.xml')


def contact_sheet(files, out):
    import base64
    import re as _re
    from playwright.sync_api import sync_playwright
    cells = []
    def cell(rel, svg, scale):
        b = base64.b64encode(svg.encode()).decode()
        vb = _re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        w, h_ = int(vb.group(1)), int(vb.group(2))
        cells.append(f'<figure style="margin:0"><img src="data:image/svg+xml;base64,{b}" width="{int(w*scale)}" height="{int(h_*scale)}">'
                     f'<figcaption>{rel} {len(svg)//1024+1}K x{scale}</figcaption></figure>')
    for rel in ('hero/sergey.svg', 'hero/sergey_back.svg'):
        cell(rel, files[rel], 1.5)
    cell('icon/icon.svg', files['icon/icon.svg'], 0.6)
    mk = files['hero/sergey_marker.svg']
    for sc in (3, 1, 0.667, 0.5):
        cell('marker', mk, sc)
    ic = files['icon/icon.svg']
    for sc in (0.375, 0.1875):
        cell('icon@' + str(int(512 * sc)), ic, sc)
    for rel in sorted(k for k in files if k.startswith('intro/')):
        cell(rel, files[rel], 1.0)
    html = ('<html><body style="margin:0;background:#05090e;font:11px sans-serif;color:#9BA7B4">'
            '<div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px;width:1520px;align-items:flex-start">'
            + ''.join(cells) + '</div></body></html>')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1540, 'height': 800})
        pg.set_content(html)
        pg.wait_for_timeout(300)
        pg.screenshot(path=out, full_page=True)
        b.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    files = collect(with_intro='--no-intro' not in args)
    bad = write(files)
    if '--no-icons' not in args:
        write_android(files['icon/icon.svg'])
    if '--sheet' in args:
        contact_sheet(files, args[args.index('--sheet') + 1])
        print('sheet:', args[args.index('--sheet') + 1])
    if bad:
        print('PROBLEMS:', bad)
        sys.exit(1)

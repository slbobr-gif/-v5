"""Онбординг, финал и иконка."""
import random
from artlib import *
from hero import walker, hiker_back


# ---------------------------------------------------------------- onboarding
def routine():
    d = Doc('0 0 320 240', 'or')
    d.rect(0, 0, 320, 240, fill=d.lin([(0, '#142030'), (1, R1)]))
    hatch(d, 0, 0, 320, 204, step=6, angle=0, color=INK, op=0.25, sw=0.6)
    # окно офиса
    wx, wy, ww, wh = 22, 34, 132, 132
    d.rect(wx - 4, wy - 4, ww + 8, wh + 8, fill='#22344A')
    d.rect(wx, wy, ww, wh, fill=d.lin([(0, '#0A111A'), (1, '#1A2A3C')]))
    stars(d, wx + 4, wy + 30, wx + ww - 4, wy + 70, 10, 2, rmax=0.7)
    d.circle(wx + 104, wy + 46, 6, fill=PARCH, opacity=0.8)
    rnd = random.Random(5)
    x = wx
    while x < wx + ww:
        bw = rnd.uniform(12, 24)
        bh = rnd.uniform(36, 90)
        bw = min(bw, wx + ww - x)
        d.rect(x, wy + wh - bh, bw, bh, fill=rnd.choice(['#16243A', '#1A2A40', '#132034']))
        for yy in range(int(wy + wh - bh + 4), int(wy + wh - 3), 6):
            for xx in range(int(x + 2), int(x + bw - 3), 5):
                if rnd.random() < 0.28:
                    d.rect(xx, yy, 2.2, 2.6, fill=rnd.choice([WARM, GOLD, SEC]), opacity=round(rnd.uniform(0.4, 0.9), 2))
        x += bw
    # жалюзи
    for i in range(7):
        d.rect(wx, wy + i * 4.2, ww, 3, fill='#2A3E54')
    d.line([(wx + 18, wy + 30), (wx + 18, wy + 44)], stroke=SEC, stroke_width=0.6)
    d.rect(wx + ww / 2 - 2, wy, 4, wh, fill='#22344A')
    d.rect(wx, wy + 70, ww, 3, fill='#22344A')
    # часы 22:40
    cx, cy = 178, 52
    d.circle(cx, cy, 12, fill=PARCH, opacity=0.9)
    d.circle(cx, cy, 12, fill='none', stroke=GOLD, stroke_width=1.4)
    for i in range(12):
        a = math.radians(i * 30)
        d.path(f'M{f(cx+9.5*math.sin(a))},{f(cy-9.5*math.cos(a))}L{f(cx+10.8*math.sin(a))},{f(cy-10.8*math.cos(a))}', stroke=INK, stroke_width=0.8)
    ah, am = math.radians(10 * 30 + 20), math.radians(240)
    d.path(f'M{cx},{cy}L{f(cx+5.5*math.sin(ah))},{f(cy-5.5*math.cos(ah))}M{cx},{cy}L{f(cx+8.5*math.sin(am))},{f(cy-8.5*math.cos(am))}',
           stroke=INK, stroke_width=1.3, stroke_linecap='round')
    # пол
    d.rect(0, 204, 320, 36, fill='#101924')
    d.path('M0,214H320M0,226H320', stroke=INK, stroke_width=0.8, opacity=0.7)
    # стол с монитором
    glow(d, 92, 132, 70, TEAL, 0.25)
    d.rect(10, 170, 160, 6, fill='#2A3E54')
    d.rect(16, 176, 4, 28, fill='#1A2838')
    d.rect(160, 176, 4, 28, fill='#1A2838')
    d.rect(58, 112, 66, 46, fill='#0A111A', rx=2)
    d.rect(61, 115, 60, 40, fill=d.lin([(0, '#2E6E78'), (1, '#1C4652')]))
    grid = ''.join(f'M61,{y}H121' for y in range(121, 155, 5)) + ''.join(f'M{x},115V155' for x in range(73, 121, 12))
    d.path(grid, stroke=PARCH, stroke_width=0.4, opacity=0.4)
    d.rect(61, 115, 60, 5, fill=TEAL, opacity=0.5)
    d.rect(87, 158, 8, 8, fill='#1A2838')
    d.rect(80, 166, 22, 4, fill='#1A2838')
    # кружка и листок
    d.rect(134, 158, 10, 12, fill=PARCH, opacity=0.85, rx=1.5)
    d.path('M144,161c4,0 4,6 0,6', stroke=PARCH, stroke_width=1.4, fill='none', opacity=0.85)
    d.path('M137,154c-2,-4 2,-6 0,-10M141,154c-2,-3 2,-5 0,-8', stroke=PARCH, stroke_width=0.8, opacity=0.35, fill='none')
    d.rect(24, 164, 22, 6, fill=PARCH, opacity=0.5)
    # кресло
    d.path('M36,140C34,160 36,176 44,184L74,184C80,176 80,160 78,140C70,136 44,136 36,140Z', fill='#0B131C')
    d.rect(55, 184, 4, 14, fill='#0B131C')
    d.path('M40,202h34', stroke='#0B131C', stroke_width=3, stroke_linecap='round')
    # дверь в лес
    dx0, dy0, dx1, dy1 = 206, 50, 284, 204
    d.rect(dx0 - 5, dy0 - 5, dx1 - dx0 + 10, dy1 - dy0 + 5, fill='#2A3E54')
    d.rect(dx0, dy0, dx1 - dx0, dy1 - dy0, fill=d.lin([(0, '#0E1A28'), (0.6, '#1C3A48'), (1, '#2E5A5A')]))
    stars(d, dx0 + 3, dy0 + 3, dx1 - 3, dy0 + 60, 12, 6, rmax=0.8)
    aurora(d, dx0 - 4, dx1 + 4, dy0 + 40, 4, 26, 7, op=0.6, n=4, rays=8)
    d.path(ridge(dx0, dx1, dy0 + 98, 6, 3, 4, bottom=dy1), fill='#1F3A4A')
    fir_row(d, dx0, dx1, dy0 + 100, 10, 22, '#173040', 4, step=6)
    d.rect(dx0, dy0 + 100, dx1 - dx0, dy1 - dy0 - 100, fill=d.lin([(0, '#173040'), (1, '#10202C')]))
    d.path(f'M{dx0+30},{dy1}C{dx0+40},{dy1-20} {dx0+52},{dy1-30} {dx0+40},{dy0+104}L{dx0+44},{dy0+104}C{dx0+60},{dy1-30} {dx0+62},{dy1-20} {dx0+66},{dy1}Z',
           fill=d.lin([(0, GOLD, 0.15), (1, GOLD, 0.75)]))
    fir(d, dx0 + 10, dy1, 70, 28, '#0C1A24', seed=1, tiers=5)
    fir(d, dx1 - 8, dy1, 80, 30, '#0C1A24', seed=2, tiers=5)
    # створка открыта к нам
    d.poly([(dx1, dy0), (dx1 + 22, dy0 - 8), (dx1 + 22, dy1 + 14), (dx1, dy1)], fill='#2C4258')
    d.poly([(dx1 + 4, dy0 + 10), (dx1 + 18, dy0 + 5), (dx1 + 18, dy0 + 70), (dx1 + 4, dy0 + 72)], fill='#22344A')
    d.circle(dx1 + 18, dy0 + 82, 1.8, fill=GOLD)
    # свет из двери на пол
    d.poly([(dx0, dy1), (dx1, dy1), (dx1 + 30, 240), (dx0 - 40, 240)], fill=d.lin([(0, GOLD, 0.3), (1, GOLD, 0.02)]))
    glow(d, (dx0 + dx1) / 2, dy1 - 40, 70, AU2, 0.18)
    # листья влетают
    for x, y, c in [(196, 120, GOLD), (186, 140, TEAL), (174, 110, AU2), (200, 160, GOLD)]:
        d.path(f'M{x},{y}c3,-3 7,-3 8,0c-3,3 -7,3 -8,0Z', fill=c, opacity=0.85)
    # ботинки из коробки
    d.path('M168,204l2,-12h26l2,12Z', fill='#3A4C60')
    d.path('M168,192l-6,-6h26l8,6Z', fill='#4A5E74')
    for bx in (174, 188):
        d.path(f'M{bx},204v-14c0,-2 6,-2 6,0v6c4,1 8,3 8,8Z', fill='#6A5442')
        d.path(f'M{bx+1},193h4M{bx+1},196h4', stroke=GOLD, stroke_width=0.6)
    return d.render()


def count():
    d = Doc('0 0 320 240', 'oc')
    sky(d, 320, 240, INK, '#2E4058', mid='#182839')
    d.rect(0, 80, 320, 60, fill=d.lin([(0, GOLD, 0), (1, GOLD, 0.25)]))
    stars(d, 0, 0, 320, 90, 40, 9)
    glow(d, 238, 124, 50, GOLD, 0.5)
    d.path(ridge(-10, 330, 126, 12, 3, 8), fill=FAR)
    fir_row(d, -10, 330, 128, 8, 18, '#22364B', 6, step=6)
    d.path(ridge(-10, 330, 146, 8, 5, 6), fill=MID)
    d.rect(0, 150, 320, 90, fill=d.lin([(0, MID), (1, NEAR)]))
    # тропа, в которую превращаются следы
    trail = d.lin([(0, GOLD, 0.85), (1, GOLD, 0.15)], 0, 0, 0, 1)
    d.path('M236,126C232,134 214,140 216,148C220,156 246,158 240,170C236,176 220,180 212,184L196,184C206,178 224,174 226,168C230,158 204,154 204,146C204,138 226,134 232,126Z', fill=trail)
    # следы: от кроссовка к тропе
    steps = [(140, 206, 1.0, -8), (162, 196, 0.92, -14), (176, 186, 0.82, -20), (196, 180, 0.74, -20), (206, 172, 0.66, -30)]
    for i, (x, y, s, a) in enumerate(steps):
        side = 1 if i % 2 else -1
        y += side * 3 * s
        d.g_open(transform=f'rotate({a} {f(x)} {f(y)})')
        d.ellipse(x + 3 * s, y, 6 * s, 3.2 * s, fill=GOLD, opacity=0.55 + 0.08 * i)
        d.ellipse(x - 6.5 * s, y, 3 * s, 2.6 * s, fill=GOLD, opacity=0.55 + 0.08 * i)
        d.g_close()
        sparkle(d, x + 4, y - 10 * s, 2.2 * s, PARCH, opacity=0.6)
    # кроссовок
    sole = d.lin([(0, PARCH), (1, '#C9BFA8')])
    upper = d.lin([(0, '#3A6680'), (1, '#22405A')])
    d.path('M24,214C22,204 30,196 40,196L128,198C140,200 146,206 144,214C142,220 132,222 120,222L36,222C28,222 24,220 24,214Z', fill=sole)
    d.path('M28,214H142', stroke=SEC, stroke_width=1.2, opacity=0.8)
    d.path(''.join(f'M{x},216v5' for x in range(38, 136, 8)), stroke=SEC, stroke_width=1.4, opacity=0.6)
    d.path('M30,200C28,182 36,166 50,162L66,160C74,168 86,174 100,178C118,182 134,188 140,198C141,202 140,204 136,204L36,202Z', fill=upper)
    d.path('M60,160C58,150 64,144 72,146L78,170Z', fill='#2E5470')
    d.path('M36,180C60,186 92,184 120,190', stroke=GOLD, stroke_width=3, fill='none', stroke_linecap='round')
    d.path('M120,190C128,192 134,196 138,200', stroke=TEAL, stroke_width=2, fill='none', opacity=0.6)
    d.path('M116,186C124,186 132,190 138,198L136,202L114,200Z', fill='#2E5470', opacity=0.8)
    for i in range(5):
        x = 72 + i * 7
        y = 164 + i * 3.2
        d.path(f'M{x-3},{y+2}L{x+3},{y-2}M{x-3},{y-2}L{x+3},{y+2}', stroke=PARCH, stroke_width=1.2, stroke_linecap='round')
    d.path('M40,170C44,166 50,164 56,164', stroke=PARCH, stroke_width=1, opacity=0.4, fill='none')
    d.rect(30, 180, 8, 14, fill=GOLD, rx=2, opacity=0.9)
    # ступеньки-деления счёта
    for i in range(6):
        d.circle(196 + i * 18, 222, 2 if i % 5 else 3, fill=GOLD, opacity=0.35 + i * 0.1)
    grass(d, 0, 320, 240, 8, 50, 4, FORE)
    return d.render()


def world():
    d = Doc('0 0 320 240', 'ow')
    sky(d, 320, 240, INK, '#1E3A48', mid='#142234')
    stars(d, 0, 0, 320, 80, 40, 12)
    moon(d, 160, 48, 12, halo=4)
    d.path(ridge(-10, 330, 120, 14, 8, 8), fill=FAR)
    fir_row(d, -10, 330, 124, 16, 34, '#21354A', 5, step=8)
    fir_row(d, -10, 330, 150, 34, 60, MID, 6, step=14, tiers=4)
    d.rect(0, 148, 320, 92, fill=d.lin([(0, NEAR), (1, FORE)]))
    # светящаяся тропа
    tr = d.lin([(0, GOLD, 0.1), (0.5, GOLD, 0.45), (1, PARCH, 0.7)])
    d.path('M156,148C166,160 140,170 146,186C152,202 196,212 190,240L124,240C132,214 112,198 120,180C128,164 150,158 150,148Z', fill=tr)
    glow(d, 160, 196, 70, GOLD, 0.2)
    # глаза за деревьями
    def eyes(x, y, s=1.0, c=GOLD, happy=False):
        for k in (-1, 1):
            ex = x + k * 4.2 * s
            glow(d, ex, y, 7 * s, c, 0.45)
            if happy:
                d.path(f'M{f(ex-2.6*s)},{f(y+0.8*s)}C{f(ex-1.4*s)},{f(y-2.2*s)} {f(ex+1.4*s)},{f(y-2.2*s)} {f(ex+2.6*s)},{f(y+0.8*s)}',
                       stroke=c, stroke_width=1.3 * s, fill='none', stroke_linecap='round')
            else:
                d.ellipse(ex, y, 2.2 * s, 1.8 * s, fill=c)
                d.circle(ex + 0.4 * s, y, 0.8 * s, fill=INK)
    eyes(58, 168, 1.1)
    eyes(262, 160, 1.2, happy=True)
    eyes(104, 140, 0.8, TEAL)
    eyes(222, 136, 0.8, happy=True)
    eyes(292, 196, 1.0, AU1)
    eyes(30, 206, 1.0, happy=True)
    # большие стволы-кулисы
    d.path('M0,0H22C20,80 24,160 30,240H0Z', fill='#0A121B')
    d.path('M320,0H298C300,80 296,160 290,240H320Z', fill='#0A121B')
    fir(d, 44, 240, 120, 54, '#0C151F', seed=4, tiers=6)
    fir(d, 278, 240, 130, 56, '#0C151F', seed=5, tiers=6)
    eyes(46, 188, 1.0, GOLD, happy=False)
    # леший-силуэт: рожки над елью
    d.path('M272,110C268,100 266,94 260,90M268,102C270,96 274,94 276,90M284,110C288,100 292,96 298,94', stroke='#0C151F', stroke_width=2.2, fill='none', stroke_linecap='round')
    eyes(278, 122, 1.0, GOLD, happy=True)
    # грибы и светлячки
    for x, y in [(96, 214), (104, 218), (230, 222)]:
        d.path(f'M{x-4},{y}c0,-5 8,-5 8,0Z', fill=WARM, opacity=0.9)
        d.rect(x - 1, y, 2, 4, fill=PARCH)
    rnd = random.Random(3)
    for _ in range(14):
        x, y = rnd.uniform(70, 250), rnd.uniform(110, 210)
        glow(d, x, y, 5, GOLD, 0.6)
        d.circle(x, y, 0.9, fill=GOLD)
    grass(d, 0, 320, 240, 10, 60, 5, '#070C12')
    return d.render()


def meet():
    d = Doc('0 0 320 240', 'om')
    sky(d, 320, 240, INK, '#24405A', mid='#152436')
    stars(d, 0, 0, 320, 100, 40, 21)
    aurora(d, -10, 330, 64, 10, 46, 2, op=0.6, rays=24)
    aurora(d, 40, 290, 86, 6, 26, 8, op=0.35, n=5, rays=10)
    sparkle(d, 160, 30, 4, PARCH)
    glow(d, 160, 30, 12, PARCH, 0.3)
    hz = 132
    d.path(ridge(-10, 330, hz, 8, 4, 8), fill=FAR)
    fir_row(d, -10, 330, hz + 2, 6, 14, '#22364B', 3, step=5)
    d.rect(0, hz, 320, 108, fill=d.lin([(0, MID), (1, NEAR)]))
    # дорога на север
    d.poly([(158, hz), (162, hz), (214, 240), (106, 240)], fill='#1A2736')
    d.line([(158, hz), (106, 240)], stroke=SEC, stroke_width=0.8, opacity=0.4)
    d.line([(162, hz), (214, 240)], stroke=SEC, stroke_width=0.8, opacity=0.4)
    dd = ''
    for i in range(8):
        t0, t1 = (i / 8) ** 1.7, ((i + 0.5) / 8) ** 1.7
        y0, y1 = hz + (240 - hz) * t0, hz + (240 - hz) * t1
        w0, w1 = 0.3 + 2.4 * t0, 0.3 + 2.4 * t1
        dd += f'M{f(160-w0/2)},{f(y0)}L{f(160+w0/2)},{f(y0)}L{f(160+w1/2)},{f(y1)}L{f(160-w1/2)},{f(y1)}Z'
    d.path(dd, fill=GOLD, opacity=0.7)
    # кремлёвская стена с зубцами-«ласточкиными хвостами» по краям
    for side in (-1, 1):
        x0 = 0 if side < 0 else 320
        xe = 96 if side < 0 else 224
        d.poly([(x0, 186), (xe, 176), (xe, 240), (x0, 240)], fill='#1A2433')
        mer = ''
        steps = 8
        for i in range(steps):
            t = i / steps
            x = x0 + (xe - x0) * t
            y = 186 + (176 - 186) * t
            w = 8 * (1 - t * 0.4)
            mer += f'M{f(x)},{f(y)}v{f(-w)}l{f(w*0.3*-side)},{f(w*0.3)}l{f(w*0.3*-side)},{f(-w*0.3)}v{f(w)}Z'
        d.path(mer, fill='#1A2433')
        hatch_h(d, min(x0, xe), 192, max(x0, xe), 240, step=6, color=INK, op=0.35)
    # башня с шатром
    tx = 34
    d.rect(tx - 12, 130, 24, 60, fill='#1A2433')
    d.poly([(tx - 14, 130), (tx, 92), (tx + 14, 130)], fill='#162030')
    d.rect(tx - 5, 140, 10, 12, fill=WARM, opacity=0.35)
    sparkle(d, tx, 86, 5, GOLD)
    glow(d, tx, 86, 12, GOLD, 0.4)
    # брусчатка и нулевой километр
    d.ellipse(160, 222, 120, 24, fill='#1D2836')
    stones = ''
    for r in range(1, 6):
        for k in range(0, 360, 14):
            a = math.radians(k + r * 7)
            stones += f'M{f(160+r*22*math.cos(a))},{f(222+r*4.4*math.sin(a))}h3'
    d.path(stones, stroke=SEC, stroke_width=0.6, opacity=0.25)
    d.ellipse(160, 222, 34, 7.4, fill=GOLD, opacity=0.9)
    d.ellipse(160, 222, 28, 6, fill='#8A6E30')
    rays = ''
    for k in range(16):
        a = math.radians(k * 22.5)
        r = 26 if k % 2 == 0 else 18
        rays += f'M160,222L{f(160+r*math.cos(a))},{f(222+r*0.21*math.sin(a))}'
    d.path(rays, stroke=GOLD, stroke_width=1.1)
    d.ellipse(160, 222, 6, 1.3, fill=GOLD)
    glow(d, 160, 222, 50, GOLD, 0.25)
    # Сергей со спины
    hiker_back(d, 160, 222, 66)
    return d.render()


ONBOARDING = dict(routine=routine, count=count, world=world, meet=meet)


# ---------------------------------------------------------------- finale
def teriberka():
    d = Doc('0 0 360 240', 'tb')
    sky(d, 360, 240, '#0A111A', '#2A4A5A', mid='#13233A')
    stars(d, 0, 0, 360, 110, 40, 31)
    aurora(d, -10, 370, 70, 14, 56, 11, op=0.7, n=8, rays=22)
    aurora(d, 60, 330, 100, 8, 36, 12, op=0.4, n=6, rays=14)
    aurora(d, 180, 380, 40, 6, 24, 13, op=0.3, n=4, rays=8, colors=(AU1, AU2, '#3A6A8A'))
    hz = 140
    # скалистый мыс слева
    d.path('M-5,140L-5,104C10,100 22,98 34,102C46,92 60,90 72,100C86,104 100,112 120,124C132,130 146,136 160,140Z', fill='#1A2C3E')
    d.path('M-5,140L-5,118C20,114 40,118 60,124C80,128 100,134 110,140Z', fill='#14222F')
    hatch_lines(d, [(30, 106, 40, 120), (50, 98, 56, 116), (70, 104, 74, 118), (90, 110, 92, 124)], SEC, 0.15)
    # море
    water(d, 0, hz, 360, 68, '#2B5266', '#10202C', seed=21, lines=28, op=0.5)
    d.rect(40, hz, 280, 30, fill=d.lin([(0, AU2, 0.22), (1, AU2, 0)]))
    # кит: спина с плавником и фонтан
    wy = hz + 22
    d.ellipse(198, wy + 1, 60, 3.5, fill=PARCH, opacity=0.12)
    d.path(f'M150,{wy}C162,{wy-11} 190,{wy-16} 214,{wy-14}C228,{wy-13} 236,{wy-10} 240,{wy-9}C242,{wy-12} 244,{wy-16} 247,{wy-17}C247,{wy-13} 248,{wy-9} 250,{wy-7}C254,{wy-5} 257,{wy-2} 258,{wy}Z', fill='#16242F')
    d.path(f'M156,{wy-3}C168,{wy-11} 190,{wy-15} 214,{wy-13}C228,{wy-12} 235,{wy-9.5} 240,{wy-8.6}', stroke=AU1, stroke_width=1.1, opacity=0.5, fill='none', stroke_linecap='round')
    d.path(f'M142,{wy}h124', stroke=PARCH, stroke_width=1.3, opacity=0.55, stroke_linecap='round')
    d.path(f'M146,{wy+3}h20M236,{wy+3}h26', stroke=PARCH, stroke_width=0.8, opacity=0.35, stroke_linecap='round')
    sx, sy = 160, wy - 9
    mist = d.rad([(0, PARCH, 0.55), (0.5, PARCH, 0.25), (1, PARCH, 0)])
    for x, y, rx, ry in [(sx, sy - 4, 4, 6), (sx - 5, sy - 14, 7, 8), (sx + 5, sy - 14, 7, 8), (sx - 10, sy - 26, 11, 9),
                         (sx + 10, sy - 26, 11, 9), (sx, sy - 32, 14, 9)]:
        d.ellipse(x, y, rx, ry, fill=mist)
    rnd = random.Random(2)
    for _ in range(12):
        d.circle(sx + rnd.uniform(-20, 20), sy - rnd.uniform(6, 38), rnd.uniform(0.5, 1.1), fill=PARCH, opacity=0.6)
    # хвост второго кита вдали
    d.path('M300,156C301,151 302,147 300,143C294,142 286,138 280,133C288,134 295,136 301,139C307,136 314,134 322,133C316,138 309,142 304,143C303,147 304,151 306,156Z', fill='#16242F')
    d.path('M280,133C288,134 295,136 301,139C307,136 314,134 322,133', stroke=AU1, stroke_width=0.8, opacity=0.5, fill='none')
    d.path('M284,135v6M318,135v5M290,137v4', stroke=PARCH, stroke_width=0.6, opacity=0.5)
    d.path('M290,156h28', stroke=PARCH, stroke_width=0.9, opacity=0.55, stroke_linecap='round')
    # прибой
    d.path(smooth([(0, 206), (60, 202), (120, 208), (180, 203), (240, 208), (300, 202), (360, 206)]), stroke=PARCH, stroke_width=1.4, opacity=0.5, fill='none')
    d.path(smooth([(0, 200), (80, 197), (160, 201), (260, 197), (360, 200)]), stroke=PARCH, stroke_width=0.8, opacity=0.25, fill='none')
    # берег из круглых камней
    d.path('M-5,240L-5,208C80,204 200,210 365,206L365,240Z', fill='#121E2A')
    rnd = random.Random(7)
    stones = []
    for _ in range(26):
        x = rnd.uniform(-10, 370)
        y = rnd.uniform(212, 236)
        r = rnd.uniform(6, 15) * (0.6 + (y - 206) / 40)
        stones.append((y, x, r))
    for y, x, r in sorted(stones):
        g = d.rad([(0, '#4A6070'), (0.6, '#24364A'), (1, '#16222F')], cx=0.38, cy=0.3, r=0.75)
        d.ellipse(x, y, r * 1.25, r, fill=g)
        d.path(f'M{f(x-r*0.7)},{f(y-r*0.62)}C{f(x-r*0.2)},{f(y-r*0.98)} {f(x+r*0.4)},{f(y-r*0.95)} {f(x+r*0.8)},{f(y-r*0.55)}', stroke=AU1, stroke_width=0.6, opacity=0.35, fill='none')
    # Сергей на камнях
    hiker_back(d, 306, 214, 40, body='#0A111A', rim=AU1, rim_op=0.7)
    return d.render()


# ---------------------------------------------------------------- icon
def icon():
    d = Doc('0 0 512 512', 'ic')
    bg = d.lin([(0, '#0A111A'), (0.55, INK), (1, '#1C3248')])
    d.rect(0, 0, 512, 512, rx=112, fill=bg)
    # сияние
    aurora(d, 20, 492, 186, 22, 110, 3, op=0.95, n=6, rays=26)
    aurora(d, 70, 450, 226, 12, 70, 5, op=0.5, n=5, rays=12)
    for x, y, r in [(108, 96, 9), (386, 120, 7), (300, 70, 5), (180, 150, 4), (440, 220, 4)]:
        glow(d, x, y, r * 2.4, PARCH, 0.3)
        sparkle(d, x, y, r, PARCH)
    # горизонт
    hz = 330
    glow(d, 256, hz, 150, GOLD, 0.45)
    rr = round_rect_poly(0, 0, 512, 512, 112)
    far = sample([(-10, hz + 4), (60, hz - 8), (130, hz - 26), (200, hz - 10), (256, hz - 22), (320, hz - 12), (400, hz - 30), (470, hz - 10), (522, hz)]) + [(522, 520), (-10, 520)]
    d.poly(clip_convex(far, rr), fill='#1A2C40')
    near = sample([(-10, hz + 22), (120, hz + 8), (256, hz + 4), (392, hz + 8), (522, hz + 22)]) + [(522, 520), (-10, 520)]
    d.poly(clip_convex(near, rr), fill='#122030')
    # тропа
    tr = d.lin([(0, GOLD, 0.95), (1, '#B88A3A', 0.9)])
    d.path(f'M250,{hz+14}C246,{hz+40} 220,{hz+56} 224,{hz+80}C228,{hz+108} 300,{hz+124} 300,{hz+182}L196,{hz+182}C206,{hz+130} 180,{hz+110} 194,{hz+76}C204,{hz+52} 246,{hz+40} 262,{hz+14}Z', fill=tr)
        # путник
    walker(d, 238, hz + 108, 4.7, body=PARCH, pack=GOLD, stick=GOLD, sw=1.1, mat=TEAL, outline=INK, ow=1.0)
    # обводка-кайма
    d.rect(12, 12, 488, 488, rx=100, fill='none', stroke=GOLD, stroke_width=3, opacity=0.35)
    return d.render()

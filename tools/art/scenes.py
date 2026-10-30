"""Сцены для шапок карточек событий, viewBox 0 0 360 200."""
import random
from artlib import *

W, H = 360, 200


def new(name):
    return Doc(f'0 0 {W} {H}', name[:2])


def forest():
    d = new('fo')
    sky(d, W, H, INK, '#24405A', mid='#152334')
    stars(d, 0, 0, W, 90, 34, 11)
    moon(d, 292, 34, 9, crescent=True, bg='#132030')
    fog(d, 180, 112, 220, 26, TEAL, 0.16)
    d.path(ridge(-10, 370, 112, 18, 3, 9), fill=FAR)
    fir_row(d, -10, 370, 116, 14, 26, '#22364B', 5, step=7)
    fir_row(d, -10, 370, 132, 26, 44, MID, 6, step=11)
    d.rect(0, 130, W, 70, fill=NEAR)
    # тропа
    path_g = d.lin([(0, GOLD, 0.05), (0.6, GOLD, 0.22), (1, PARCH, 0.4)])
    d.path('M168,131C176,140 150,150 156,162C162,176 214,182 206,200L132,200C144,186 122,170 132,158C142,146 160,140 162,131Z', fill=path_g)
    hatch_lines(d, [(140, 192, 152, 188), (196, 194, 206, 190), (138, 170, 146, 167), (176, 166, 186, 164)], PARCH, 0.25)
    fir_row(d, -20, 120, 150, 50, 70, '#0F1A26', 7, step=16, tiers=4)
    fir_row(d, 230, 380, 150, 50, 72, '#0F1A26', 8, step=16, tiers=4)
    d.rect(0, 148, W, 52, fill=d.lin([(0, NEAR, 0), (0.25, NEAR), (1, FORE)]))
    d.path('M150,148C160,160 132,168 140,182C146,192 196,190 200,200L128,200C120,190 114,178 124,166C132,156 150,154 150,148Z', fill=path_g, opacity=0.9)
    fir(d, 24, 196, 150, 70, FORE, seed=2, tiers=6)
    fir(d, 338, 196, 160, 74, FORE, seed=4, tiers=6)
    fir(d, 300, 200, 100, 46, '#0C141E', seed=9, tiers=5)
    # светлячки
    rnd = random.Random(4)
    for _ in range(9):
        x, y = rnd.uniform(110, 250), rnd.uniform(120, 175)
        glow(d, x, y, 5, GOLD, 0.5)
        d.circle(x, y, 0.9, fill=GOLD)
    grass(d, 0, W, 200, 9, 46, 3, FORE, 0.9)
    return d.render()


def field():
    d = new('fi')
    sky(d, W, H, INK, '#5A5146', mid='#22344A')
    d.rect(0, 70, W, 60, fill=d.lin([(0, GOLD, 0), (1, GOLD, 0.35)]))
    stars(d, 0, 0, W, 60, 30, 21, omax=0.7)
    glow(d, 110, 118, 70, GOLD, 0.45)
    d.circle(110, 118, 16, fill=GOLD, opacity=0.95)
    d.circle(110, 118, 16, fill=WARM, opacity=0.25)
    # дальний лес
    d.path(ridge(-10, 370, 120, 6, 4, 14), fill='#34485C')
    fir_row(d, -10, 370, 122, 5, 11, '#2B3E52', 9, step=4)
    # поле
    d.rect(0, 121, W, 79, fill=d.lin([(0, '#3D4049'), (0.4, '#2A3240'), (1, NEAR)]))
    d.rect(0, 121, W, 30, fill=d.lin([(0, GOLD, 0.35), (1, GOLD, 0)]))
    # борозды-волны
    rnd = random.Random(7)
    dd = ''
    for i in range(10):
        y = 126 + i * i * 0.75
        dd += smooth([(x, y + 1.2 * math.sin(x / 26 + i)) for x in range(-10, 400, 46)])
    d.path(dd, stroke=GOLD, stroke_width=0.6, opacity=0.22, fill='none')
    # одинокое дерево на бугре
    d.path('M220,128C240,118 290,116 330,126L330,132L220,132Z', fill='#2A3240')
    d.path('M276,121C275,110 276,100 271,92M276,112C281,106 287,103 292,101M275,105C268,101 262,99 256,99',
           stroke=FORE, stroke_width=2.4, fill='none', stroke_linecap='round')
    d.path('M276,122L274,108L278,108Z', fill=FORE)
    for cx, cy, rx, ry in [(270, 86, 20, 12), (256, 94, 13, 9), (290, 95, 15, 9), (282, 82, 14, 10), (262, 82, 12, 8), (276, 76, 12, 8)]:
        d.ellipse(cx, cy, rx, ry, fill='#152131')
    d.ellipse(272, 79, 9, 4, fill=GOLD, opacity=0.18)
    # птицы
    for x, y, s in [(170, 64, 1), (182, 58, 0.8), (190, 66, 0.7)]:
        d.path(f'M{f(x-4*s)},{f(y)}q{f(2*s)},{f(-2*s)} {f(4*s)},0q{f(2*s)},{f(-2*s)} {f(4*s)},0', stroke=FORE, stroke_width=0.9, fill='none')
    # рожь на переднем плане
    rnd = random.Random(12)
    stalks = ''
    heads = []
    for _ in range(56):
        x = rnd.uniform(-5, 365)
        yb = 200
        h = rnd.uniform(28, 62) * (0.6 if 120 < x < 240 else 1)
        b = rnd.uniform(-5, 9)
        stalks += f'M{f(x)},{f(yb)}q{f(b*0.3)},{f(-h*0.6)} {f(b)},{f(-h)}'
        heads.append((x + b, yb - h, rnd.random()))
    d.path(stalks, stroke='#3B3A34', stroke_width=0.8, fill='none')
    hd = ''
    for x, y, r in heads:
        hd += f'M{f(x)},{f(y)}c-1.6,2.4 -1.4,6 .4,8c1.6,-2 1.4,-5.6 -.4,-8Z'
    d.path(hd, fill=GOLD, opacity=0.75)
    d.path(''.join(f'M{f(x)},{f(y)}l{f(1.5)},{f(-6)}' for x, y, r in heads[::2]), stroke=GOLD, stroke_width=0.4, opacity=0.6)
    return d.render()


def river():
    d = new('ri')
    sky(d, W, H, INK, '#2A4560', mid='#17273A')
    stars(d, 0, 0, W, 80, 35, 31)
    moon(d, 210, 38, 10)
    d.path(ridge(-10, 370, 104, 12, 8, 8), fill=FAR)
    fir_row(d, 140, 370, 106, 12, 22, '#22374C', 3, step=6)
    fir_row(d, -10, 150, 108, 8, 14, '#24394E', 4, step=6)
    # река
    water(d, 0, 104, W, 96, '#2B4A63', '#0F1B27', seed=4, lines=22, op=0.45)
    reflection(d, 210, 106, 170, PARCH, 12, op=0.55)
    fog(d, 120, 108, 160, 8, PARCH, 0.12)
    # дальний берег отражение
    d.rect(0, 104, W, 6, fill=FAR, opacity=0.5)
    # ближний берег слева с ивами
    d.path('M-5,150C30,140 70,142 110,160C130,170 150,190 160,200L-5,200Z', fill=NEAR)
    d.path('M-5,166C40,158 90,168 120,200L-5,200Z', fill=FORE)
    # ивы
    def willow(x, yb, h, seed):
        rnd = random.Random(seed)
        d.path(f'M{f(x-3)},{f(yb)}C{f(x-2)},{f(yb-h*0.4)} {f(x+4)},{f(yb-h*0.6)} {f(x+2)},{f(yb-h*0.8)}L{f(x+5)},{f(yb-h*0.8)}C{f(x+6)},{f(yb-h*0.5)} {f(x+2)},{f(yb-h*0.3)} {f(x+3)},{f(yb)}Z', fill=FORE)
        d.ellipse(x + 3, yb - h * 0.85, h * 0.38, h * 0.2, fill='#14222F')
        dd = ''
        for i in range(22):
            sx = x + 3 + rnd.uniform(-h * 0.42, h * 0.42)
            sy = yb - h * (0.85 + rnd.uniform(-0.12, 0.08))
            ln = h * rnd.uniform(0.3, 0.75)
            dd += f'M{f(sx)},{f(sy)}q{f(rnd.uniform(-3,3))},{f(ln*0.5)} {f(rnd.uniform(1,5))},{f(ln)}'
        d.path(dd, stroke='#1E3644', stroke_width=1.1, fill='none', stroke_linecap='round')
        d.path(dd, stroke=TEAL, stroke_width=0.4, fill='none', opacity=0.35)
    willow(30, 150, 110, 1)
    willow(92, 160, 80, 2)
    # мостки справа
    d.path('M236,200L262,152L300,152L300,200Z', fill='#1A2735', opacity=0.0)
    planks = d.lin([(0, '#2A3A4C'), (1, '#15212E')], 0, 0, 0, 1)
    d.poly([(232, 200), (268, 148), (290, 148), (300, 200)], fill=planks)
    dd = ''
    for i in range(1, 12):
        t = i / 12
        y = 148 + 52 * t ** 1.4
        xl = 268 + (232 - 268) * (y - 148) / 52
        xr = 290 + (300 - 290) * (y - 148) / 52
        dd += f'M{f(xl)},{f(y)}L{f(xr)},{f(y)}'
    d.path(dd, stroke=INK, stroke_width=0.7, opacity=0.7)
    for x, y, h in [(268, 148, 14), (290, 148, 14), (252, 172, 20), (298, 172, 20)]:
        d.rect(x - 1.2, y - 4, 2.4, h, fill=FORE)
        d.path(f'M{f(x)},{f(y+h-2)}h{f(5)}', stroke=TEAL, stroke_width=0.6, opacity=0.5)
    d.line([(268, 144), (252, 168)], stroke=FORE, stroke_width=1.6)
    # фонарь-банка на мостках
    glow(d, 284, 156, 12, WARM, 0.6)
    d.rect(282, 153, 4, 5, fill=WARM, rx=1)
    reeds(d, 300, 365, 200, 14, 34, 30, 6)
    reeds(d, 110, 160, 200, 10, 24, 14, 7)
    return d.render()


def lake():
    d = new('la')
    sky(d, W, H, INK, '#2F5068', mid='#18293B')
    stars(d, 0, 0, W, 70, 40, 41)
    aurora(d, 20, 340, 60, 8, 34, 5, op=0.35, rays=14)
    moon(d, 70, 30, 7)
    # дальние берега
    d.path(ridge(-10, 120, 104, 6, 2, 5), fill='#2B4359')
    d.path(ridge(250, 370, 104, 8, 3, 5), fill='#2B4359')
    water(d, 0, 104, W, 96, '#2D4E66', '#0E1924', seed=7, lines=36, op=0.4)
    # отражение сияния
    d.rect(20, 106, 320, 30, fill=d.lin([(0, AU2, 0.18), (1, AU2, 0)]))
    # остров с храмом
    d.path('M140,104C150,94 170,92 186,92C204,92 222,98 236,104Z', fill='#1C2E40')
    fir_row(d, 146, 166, 100, 8, 14, '#1C2E40', 2, step=5)
    fir_row(d, 212, 232, 103, 6, 12, '#1C2E40', 3, step=5)
    church(d, 190, 95, 0.95, body='#22374C', dome=GOLD, roof='#1A2B3C')
    # отражение острова
    d.path('M140,104C150,112 170,114 186,114C204,114 222,110 236,104Z', fill='#1C2E40', opacity=0.6)
    d.rect(187, 104, 6, 16, fill=GOLD, opacity=0.18)
    reflection(d, 190, 105, 140, GOLD, 5, seed=8, op=0.35)
    reflection(d, 70, 106, 160, PARCH, 6, seed=9, op=0.35)
    # передний берег: камни и лодка
    d.path('M-5,176C40,168 80,172 120,184C140,190 150,196 154,200L-5,200Z', fill=NEAR)
    d.ellipse(40, 180, 16, 7, fill='#1B2938')
    d.ellipse(70, 186, 10, 5, fill='#1B2938')
    d.path('M60,170C70,176 110,176 122,170L118,176C108,180 72,180 64,176Z', fill='#2A3A4A')
    d.path('M60,170C70,176 110,176 122,170', stroke=GOLD, stroke_width=0.6, opacity=0.5, fill='none')
    d.line([(96, 176), (120, 192)], stroke=FORE, stroke_width=1.2)
    reeds(d, 280, 370, 200, 16, 38, 34, 8)
    reeds(d, -5, 30, 200, 10, 24, 12, 9)
    return d.render()


def village():
    d = new('vi')
    sky(d, W, H, INK, '#2A4058', mid='#172638')
    stars(d, 0, 0, W, 90, 50, 51)
    moon(d, 300, 32, 11)
    d.path(ridge(-10, 370, 118, 10, 6, 6), fill=FAR)
    fir_row(d, -10, 370, 120, 8, 16, '#24384D', 6, step=6)
    d.path('M-5,130C80,120 200,124 365,134L365,200L-5,200Z', fill=MID)
    # дальние избы
    izba(d, 196, 132, 22, 15, body='#1B2A3B', roof='#15212E', chimney=False)
    izba(d, 236, 134, 20, 13, body='#1B2A3B', roof='#15212E', lit=False, chimney=False)
    d.path('M-5,150C90,140 230,146 365,156L365,200L-5,200Z', fill=NEAR)
    # дым
    d.path('M131,82C126,72 138,66 132,56C127,47 138,40 134,30', stroke=SEC, stroke_width=3, opacity=0.18, fill='none', stroke_linecap='round')
    izba(d, 100, 158, 52, 40, body='#1A2838', roof=FORE)
    izba(d, 30, 150, 38, 28, body='#182535', roof=FORE, chimney=False)
    # колодец-журавль
    d.rect(250, 140, 3, 24, fill=FORE)
    d.line([(236, 166), (300, 104)], stroke=FORE, stroke_width=2)
    d.line([(300, 104), (300, 136)], stroke=FORE, stroke_width=0.8)
    d.rect(297, 136, 6, 6, fill=FORE)
    d.rect(282, 150, 20, 10, fill='#1C2A39')
    d.rect(280, 148, 24, 3, fill=FORE)
    d.ellipse(242, 162, 5, 3, fill=FORE)
    # забор из жердей и штакетника
    d.rect(0, 166, W, 34, fill=d.lin([(0, NEAR), (1, FORE)]))
    rnd = random.Random(3)
    pick = ''
    for i in range(46):
        x = 160 + i * 4.6
        if x > 372:
            break
        h = 20 + rnd.uniform(-2, 2)
        pick += f'M{f(x)},{f(184)}v{f(-h)}l1.4,-2l1.4,2v{f(h)}Z'
    d.path(pick, fill='#0B131C')
    d.line([(158, 170), (365, 172)], stroke='#0B131C', stroke_width=1.6)
    d.line([(0, 178), (100, 176), (160, 178)], stroke='#0B131C', stroke_width=1.8)
    d.line([(0, 186), (100, 184), (160, 186)], stroke='#0B131C', stroke_width=1.8)
    for x in (10, 60, 110, 156):
        d.rect(x, 170, 2.4, 24, fill='#0B131C')
    # подсолнух у забора
    d.line([(216, 186), (214, 150)], stroke='#0B131C', stroke_width=1.2)
    d.circle(214, 148, 4, fill=GOLD, opacity=0.6)
    d.circle(214, 148, 2, fill=FORE)
    grass(d, 0, W, 200, 10, 80, 4, FORE)
    # кот на заборе
    d.path('M330,162c2,-5 8,-5 10,0l1,-3l1,3c1,1 1,3 0,4h-12Z', fill='#0B131C')
    d.path('M330,166c-4,0 -6,4 -9,2', stroke='#0B131C', stroke_width=1.2, fill='none')
    d.circle(338, 161, 0.6, fill=GOLD)
    d.circle(340.2, 161, 0.6, fill=GOLD)
    return d.render()


def town():
    d = new('to')
    sky(d, W, H, INK, '#33445A', mid='#1A293B')
    d.rect(0, 80, W, 60, fill=d.lin([(0, WARM, 0), (1, WARM, 0.12)]))
    stars(d, 0, 0, W, 70, 35, 61)
    moon(d, 52, 30, 8, crescent=True, bg='#111C28')
    d.path(ridge(-10, 370, 124, 10, 9, 6), fill=FAR)
    # силуэт города: дальний ряд
    rnd = random.Random(8)
    x = -4
    dd = ''
    lights = []
    while x < 364:
        w = rnd.uniform(14, 26)
        h = rnd.uniform(12, 22)
        y = 140 - h
        dd += f'M{f(x)},140V{f(y)}L{f(x+w/2)},{f(y-rnd.uniform(4,8))}L{f(x+w)},{f(y)}V140Z'
        for k in range(int(w // 6)):
            if rnd.random() < 0.5:
                lights.append((x + 3 + k * 6, y + rnd.uniform(3, h - 4)))
        x += w + rnd.uniform(-2, 2)
    d.path(dd, fill='#22354A')
    for lx, ly in lights:
        d.rect(lx, ly, 2, 2.4, fill=WARM, opacity=round(rnd.uniform(0.4, 0.9), 2))
    # колокольня
    bx = 178
    d.rect(bx - 9, 74, 18, 66, fill=MID)
    d.rect(bx - 7, 60, 14, 16, fill=MID)
    d.rect(bx - 4, 64, 8, 9, fill=WARM, opacity=0.25)
    d.path(f'M{bx-3},73v-6a3,3 0 0 1 6,0v6Z', fill=INK)
    d.rect(bx - 5, 46, 10, 15, fill=MID)
    d.poly([(bx - 6, 47), (bx, 24), (bx + 6, 47)], fill='#1A2B3D')
    onion(d, bx, 26, 6, 7, GOLD)
    for yy in (84, 104):
        d.path(f'M{bx-3},{yy+8}v-5a3,3 0 0 1 6,0v5Z', fill=WARM, opacity=0.7)
    d.path(f'M{bx-10},74h20M{bx-8},60h16M{bx-6},46h12', stroke=GOLD, stroke_width=0.7, opacity=0.5)
    # собор справа
    church(d, 248, 140, 1.5, body=MID, dome=GOLD, roof='#1A2B3D')
    onion(d, 236, 118, 6, 7, '#B8954A')
    onion(d, 260, 118, 6, 7, '#B8954A')
    d.rect(233, 118, 6, 1, fill=MID)
    # ближние дома
    d.rect(0, 140, W, 60, fill=NEAR)
    for (x, w, h, rf) in [(-4, 46, 30, 1), (46, 40, 24, 0), (92, 34, 32, 1), (208, 36, 22, 0), (282, 42, 30, 1), (328, 36, 24, 0)]:
        y = 160 - h
        d.rect(x, y, w, h + 40, fill='#152232')
        if rf:
            d.poly([(x - 2, y), (x + w / 2, y - 10), (x + w + 2, y)], fill='#101A26')
        else:
            d.poly([(x - 2, y), (x + 4, y - 6), (x + w - 4, y - 6), (x + w + 2, y)], fill='#101A26')
        for k in range(int(w // 12)):
            wx = x + 5 + k * 12
            if (k + x) % 3 != 1:
                window(d, wx, y + 7, 5, 7, frame='#152232', glow_r=9)
            else:
                d.rect(wx, y + 7, 5, 7, fill=INK)
    # мостовая и фонари
    d.rect(0, 178, W, 22, fill=FORE)
    hatch_lines(d, [(x, 186 + (x % 3) * 4, x + 8, 186 + (x % 3) * 4) for x in range(0, 360, 14)], SEC, 0.15)
    for lx in (140, 310):
        d.rect(lx - 0.8, 150, 1.6, 30, fill='#0B131C')
        glow(d, lx, 148, 16, WARM, 0.6)
        d.poly([(lx - 3, 146), (lx + 3, 146), (lx + 2, 151), (lx - 2, 151)], fill=WARM)
        d.ellipse(lx, 182, 18, 2.5, fill=WARM, opacity=0.18)
    return d.render()


def road():
    d = new('ro')
    sky(d, W, H, INK, '#4A4E55', mid='#1E3043')
    d.rect(0, 90, W, 30, fill=d.lin([(0, WARM, 0), (1, GOLD, 0.25)]))
    stars(d, 0, 0, W, 60, 30, 71, omax=0.7)
    vx, vy = 196, 112
    d.path(ridge(-10, 370, 114, 8, 2, 7), fill=FAR)
    fir_row(d, -10, 170, 116, 8, 18, '#22364A', 1, step=6)
    fir_row(d, 222, 370, 116, 8, 20, '#22364A', 2, step=6)
    d.rect(0, 114, W, 86, fill=d.lin([(0, MID), (1, NEAR)]))
    # трасса
    d.poly([(vx - 3, vy + 2), (vx + 3, vy + 2), (300, 200), (60, 200)], fill='#1A2533')
    d.poly([(vx - 3, vy + 2), (vx + 3, vy + 2), (vx + 8, vy + 18), (vx - 10, vy + 18)], fill='#1E2A38')
    d.line([(vx - 3, vy + 2), (60, 200)], stroke=SEC, stroke_width=0.8, opacity=0.45)
    d.line([(vx + 3, vy + 2), (300, 200)], stroke=SEC, stroke_width=0.8, opacity=0.45)
    # разметка
    dd = ''
    for i in range(9):
        t0 = (i / 9) ** 1.8
        t1 = ((i + 0.45) / 9) ** 1.8
        y0 = vy + 2 + (200 - vy - 2) * t0
        y1 = vy + 2 + (200 - vy - 2) * t1
        x0 = vx + (180 - vx) * t0
        x1 = vx + (180 - vx) * t1
        w0, w1 = 0.3 + 3 * t0, 0.3 + 3 * t1
        dd += f'M{f(x0-w0/2)},{f(y0)}L{f(x0+w0/2)},{f(y0)}L{f(x1+w1/2)},{f(y1)}L{f(x1-w1/2)},{f(y1)}Z'
    d.path(dd, fill=PARCH, opacity=0.6)
    # столбы с проводами
    poles = []
    for i in range(7):
        t = (i + 0.6) / 7.2
        t = t ** 2.2
        x = vx + 10 + (330 - vx - 10) * t
        yb = vy + 2 + (200 - vy) * t
        h = 6 + 90 * t
        poles.append((x, yb, h))
        d.rect(x - 0.3 - t * 1.5, yb - h, 0.6 + t * 3, h, fill='#0D151F')
        d.rect(x - 1 - 9 * t, yb - h + 4 * t + 1, 2 + 18 * t, 0.5 + 2 * t, fill='#0D151F')
    for k in (-1, 1):
        dd = ''
        for (x0, y0, h0), (x1, y1, h1) in zip(poles, poles[1:]):
            a = (x0 + k * (1 + 8 * (h0 - 6) / 90), y0 - h0 + 1.5 + 4 * (h0 - 6) / 90)
            b = (x1 + k * (1 + 8 * (h1 - 6) / 90), y1 - h1 + 1.5 + 4 * (h1 - 6) / 90)
            sag = 2 + (b[0] - a[0]) * 0.12
            dd += f'M{f(a[0])},{f(a[1])}Q{f((a[0]+b[0])/2)},{f((a[1]+b[1])/2+sag)} {f(b[0])},{f(b[1])}'
        d.path(dd, stroke='#0D151F', stroke_width=0.6, fill='none')
    # фура вдали
    tx, ty = vx - 1, vy + 6
    d.rect(tx - 4, ty - 6, 8, 5.2, fill='#2E3C4C')
    d.rect(tx - 3, ty - 9, 6, 3.4, fill='#26333F')
    glow(d, tx - 2.4, ty - 1.4, 7, WARM, 0.6)
    glow(d, tx + 2.4, ty - 1.4, 7, WARM, 0.6)
    d.circle(tx - 2.4, ty - 1.4, 0.9, fill=PARCH)
    d.circle(tx + 2.4, ty - 1.4, 0.9, fill=PARCH)
    d.path(f'M{f(tx-3)},{f(ty)}L{f(tx-14)},{f(ty+30)}L{f(tx+12)},{f(ty+30)}L{f(tx+3)},{f(ty)}Z', fill=d.lin([(0, PARCH, 0.25), (1, PARCH, 0)]))
    # обочина и знак
    d.path('M0,166C20,160 40,170 60,200L0,200Z', fill=FORE)
    d.path('M300,200C320,176 340,170 365,170L365,200Z', fill=FORE)
    d.rect(42, 150, 1.6, 30, fill='#0B131C')
    d.rect(34, 140, 18, 11, fill=TEAL, opacity=0.85, rx=1)
    d.path('M37,144h12M37,147.5h8', stroke=PARCH, stroke_width=1, opacity=0.8)
    grass(d, 0, 70, 200, 12, 30, 5, FORE)
    grass(d, 290, 365, 200, 12, 30, 6, FORE)
    return d.render()


def night():
    d = new('ni')
    sky(d, W, H, '#0A111A', '#1E3550', mid=INK)
    # млечный путь
    d.g_open(transform='rotate(16 180 90)')
    mw = d.rad([(0, SEC, 0.16), (0.5, SEC, 0.07), (1, SEC, 0)])
    d.ellipse(180, 80, 240, 26, fill=mw)
    d.ellipse(150, 82, 120, 10, fill=mw)
    d.g_close()
    rnd = random.Random(5)
    for _ in range(80):
        t = rnd.random()
        x = -10 + 380 * t
        y = 60 + 70 * t * t + rnd.gauss(0, 10)
        d.circle(x, y - 10, rnd.uniform(0.25, 0.6), fill=PARCH, opacity=round(rnd.uniform(0.2, 0.7), 2))
    stars(d, 0, 0, W, 150, 70, 81, rmax=1.1)
    for x, y, r in [(46, 30, 4), (140, 18, 3), (318, 70, 3.4), (230, 40, 2.6)]:
        glow(d, x, y, r * 2.5, PARCH, 0.3)
        sparkle(d, x, y, r, PARCH)
    # ковш
    dip = [(70, 64), (86, 58), (100, 62), (112, 70), (128, 66), (134, 80), (116, 84)]
    d.line(dip[:5] + [(134, 80), (116, 84), (112, 70)], stroke=GOLD, stroke_width=0.4, opacity=0.35)
    for x, y in dip:
        d.circle(x, y, 1.3, fill=GOLD)
    moon(d, 262, 52, 18, halo=3.4)
    d.path(ridge(-10, 370, 160, 14, 4, 8), fill='#16273A')
    fir_row(d, -10, 370, 166, 22, 40, '#0F1A27', 12, step=9)
    d.rect(0, 164, W, 36, fill=FORE)
    fir(d, 330, 200, 100, 40, '#080E15', seed=1, tiers=6)
    fir(d, 14, 200, 80, 34, '#080E15', seed=2, tiers=5)
    # сова на ветке
    d.path('M300,140L346,132', stroke='#080E15', stroke_width=2, fill='none')
    d.ellipse(318, 130, 5.5, 8, fill='#080E15')
    d.path('M313.5,124l1.5,-4l2,3.4M322.5,124l-1.5,-4l-2,3.4', fill='#080E15')
    d.circle(316, 126.5, 1.3, fill=GOLD)
    d.circle(320, 126.5, 1.3, fill=GOLD)
    return d.render()


def rain():
    d = new('ra')
    sky(d, W, H, '#121C27', '#2A3B4C', mid='#1C2938')
    # тучи
    for cx, cy, rx, ry, c in [(60, 20, 90, 26, '#253446'), (220, 14, 120, 30, '#22303F'), (330, 30, 70, 24, '#283748'),
                              (140, 40, 80, 16, '#1E2B3A'), (290, 50, 80, 14, '#1E2B3A')]:
        d.ellipse(cx, cy, rx, ry, fill=c)
    d.path(ridge(-10, 370, 128, 12, 3, 7), fill='#24364A')
    fir_row(d, -10, 370, 130, 10, 22, '#1D2E40', 7, step=8)
    # асфальт, мокрый
    d.rect(0, 130, W, 70, fill=d.lin([(0, '#1A2735'), (1, FORE)]))
    d.rect(0, 150, W, 2, fill=SEC, opacity=0.2)
    # остановка
    sx, sy = 150, 160
    d.rect(sx - 4, sy - 54, 112, 6, fill='#2A3A4C')
    d.rect(sx - 4, sy - 48, 112, 1.2, fill=GOLD, opacity=0.6)
    d.rect(sx, sy - 48, 3, 48, fill='#0F1A26')
    d.rect(sx + 101, sy - 48, 3, 48, fill='#0F1A26')
    d.rect(sx + 4, sy - 46, 96, 34, fill=TEAL, opacity=0.12)
    d.rect(sx + 4, sy - 46, 96, 34, fill='none', stroke=TEAL, stroke_width=0.6, opacity=0.4)
    d.path(f'M{sx+52},{sy-46}v34', stroke=TEAL, stroke_width=0.6, opacity=0.4)
    # лампа под навесом
    glow(d, sx + 52, sy - 44, 50, WARM, 0.35)
    d.rect(sx + 46, sy - 48, 12, 2, fill=PARCH)
    d.poly([(sx + 46, sy - 46), (sx + 58, sy - 46), (sx + 84, sy), (sx + 20, sy)], fill=d.lin([(0, WARM, 0.25), (1, WARM, 0.02)]))
    # скамья
    d.rect(sx + 20, sy - 16, 66, 3, fill='#0F1A26')
    d.rect(sx + 24, sy - 13, 2, 13, fill='#0F1A26')
    d.rect(sx + 80, sy - 13, 2, 13, fill='#0F1A26')
    # табличка
    d.rect(sx - 26, sy - 40, 1.8, 40, fill='#0F1A26')
    d.circle(sx - 25, sy - 44, 7, fill=PARCH, opacity=0.85)
    d.path(f'M{sx-29},{sy-44}h8M{sx-25},{sy-48}v8', stroke=TEAL, stroke_width=1.6)
    # силуэт кота под лавкой и зонт-трость
    d.path(f'M{sx+60},{sy}c0,-6 8,-6 10,-3l1,-3l1,3c1,1 1,3 0,3Z', fill=FORE)
    # отражения в луже
    d.ellipse(sx + 50, 184, 70, 6, fill=TEAL, opacity=0.08)
    reflection(d, sx + 52, 168, 196, WARM, 14, seed=4, op=0.45)
    reflection(d, sx - 25, 168, 186, PARCH, 6, seed=5, op=0.25)
    # дождь
    rnd = random.Random(9)
    dd = ''
    for _ in range(200):
        x = rnd.uniform(-20, 380)
        y = rnd.uniform(-10, 200)
        l = rnd.uniform(6, 14)
        dd += f'M{f(x)},{f(y)}l{f(-l*0.35)},{f(l)}'
    d.path(dd, stroke=SEC, stroke_width=0.6, opacity=0.4, stroke_linecap='round')
    dd = ''
    for _ in range(26):
        x, y = rnd.uniform(0, 360), rnd.uniform(160, 198)
        dd += f'M{f(x-3)},{f(y)}a3,1 0 1 0 6,0'
    d.path(dd, stroke=SEC, stroke_width=0.5, opacity=0.35, fill='none')
    return d.render()


def swamp():
    d = new('sw')
    sky(d, W, H, INK, '#2A4A55', mid='#172A36')
    stars(d, 0, 0, W, 70, 30, 91, omax=0.6)
    moon(d, 96, 40, 9, halo=4)
    d.path(ridge(-10, 370, 112, 8, 2, 6), fill='#2A4653')
    # сухостой дальний
    for x, h in [(40, 30), (210, 40), (300, 26)]:
        d.path(f'M{x},{112}L{x+1},{112-h}M{x+0.5},{112-h*0.6}l6,-6M{x+0.6},{112-h*0.4}l-5,-4', stroke='#22394A', stroke_width=1.2, fill='none')
    water(d, 0, 112, W, 88, '#2A4652', '#0E1A22', seed=11, lines=20, op=0.3)
    reflection(d, 96, 114, 160, PARCH, 8, op=0.3)
    fog(d, 120, 118, 200, 14, PARCH, 0.2)
    fog(d, 280, 130, 150, 12, PARCH, 0.18)
    # кочки
    rnd = random.Random(4)
    for cx, cy, rx in [(60, 140, 22), (150, 132, 16), (240, 142, 26), (330, 136, 18), (110, 166, 30), (280, 176, 34), (190, 158, 14)]:
        d.ellipse(cx, cy + 2, rx * 1.1, 3, fill=TEAL, opacity=0.1)
        d.path(f'M{f(cx-rx)},{f(cy)}C{f(cx-rx*0.6)},{f(cy-rx*0.45)} {f(cx+rx*0.6)},{f(cy-rx*0.45)} {f(cx+rx)},{f(cy)}Z', fill='#152430')
        grass(d, cx - rx * 0.8, cx + rx * 0.8, cy - rx * 0.12, rx * 0.7, int(rx * 1.2), int(cx), '#1F3A40', 0.8)
        grass(d, cx - rx * 0.6, cx + rx * 0.6, cy - rx * 0.15, rx * 0.5, int(rx * 0.5), int(cx) + 1, GOLD, 0.5, 0.3)
    fog(d, 200, 160, 220, 16, SEC, 0.14)
    # блуждающие огоньки
    for x, y in [(206, 120), (224, 112), (176, 126)]:
        glow(d, x, y, 10, AU1, 0.5)
        d.circle(x, y, 1.4, fill=AU1)
    # камыш
    reeds(d, -5, 60, 200, 30, 70, 30, 3, FORE)
    reeds(d, 310, 365, 200, 30, 64, 26, 4, FORE)
    d.path('M40,200C20,190 0,188 -5,190L-5,200Z', fill=FORE)
    # сухое дерево с вороной
    d.path('M340,200L336,110M337,140l14,-14M337,126l-10,-12M336,110l6,-10', stroke=FORE, stroke_width=2.2, fill='none', stroke_linecap='round')
    # кувшинки
    for x, y in [(160, 186), (178, 190), (230, 194)]:
        d.ellipse(x, y, 6, 1.8, fill=MOSS)
        d.circle(x + 1, y - 1, 1.4, fill=PARCH, opacity=0.9)
    return d.render()


def bathhouse():
    d = new('ba')
    sky(d, W, H, INK, '#2B465C', mid='#182839')
    stars(d, 0, 0, W, 80, 40, 101)
    moon(d, 70, 36, 10)
    d.path(ridge(-10, 370, 108, 10, 5, 7), fill=FAR)
    fir_row(d, -10, 370, 110, 10, 20, '#22364B', 3, step=6)
    water(d, 0, 110, 230, 90, '#2A4760', '#0E1A25', seed=3, lines=22, op=0.4)
    reflection(d, 70, 112, 160, PARCH, 10, op=0.45)
    # берег справа
    d.path('M150,200C170,150 200,128 260,122L365,118L365,200Z', fill=NEAR)
    d.path('M200,200C220,170 260,160 365,156L365,200Z', fill=FORE)
    # банька — сруб боком
    bx, by = 236, 150
    logs = d.lin([(0, '#2A3A4A'), (1, '#1A2836')])
    d.rect(bx, by - 30, 64, 30, fill=logs)
    d.path(''.join(f'M{bx},{by-30+i*5}h64' for i in range(1, 6)), stroke=INK, stroke_width=0.7, opacity=0.6)
    for i in range(6):
        d.circle(bx - 1, by - 27.5 + i * 5, 2.3, fill='#33465A')
        d.circle(bx + 65, by - 27.5 + i * 5, 2.3, fill='#33465A')
    d.poly([(bx - 6, by - 29), (bx + 32, by - 50), (bx + 70, by - 29)], fill=FORE)
    d.line([(bx - 4, by - 30), (bx + 32, by - 49), (bx + 68, by - 30)], stroke=GOLD, stroke_width=0.7, opacity=0.5)
    d.rect(bx + 46, by - 58, 6, 14, fill='#1B2733')
    window(d, bx + 10, by - 22, 9, 8, frame='#1A2836', glow_r=24)
    d.rect(bx + 34, by - 26, 14, 26, fill=FORE)
    d.rect(bx + 34, by - 26, 7, 26, fill=WARM, opacity=0.3)
    # пар из трубы и двери
    steam = ''
    for i, (sx, sy) in enumerate([(bx + 49, by - 60), (bx + 40, by - 28)]):
        steam += f'M{sx},{sy}C{sx-8},{sy-10} {sx+8},{sy-18} {sx},{sy-28}C{sx-8},{sy-36} {sx+6},{sy-44} {sx-2},{sy-54}'
    d.path(steam, stroke=PARCH, stroke_width=6, opacity=0.1, fill='none', stroke_linecap='round')
    d.path(steam, stroke=PARCH, stroke_width=2.5, opacity=0.18, fill='none', stroke_linecap='round')
    for cx, cy, r in [(bx + 46, by - 92, 9), (bx + 58, by - 100, 6), (bx + 34, by - 84, 5)]:
        d.circle(cx, cy, r, fill=PARCH, opacity=0.08)
    # мостки в воду
    d.poly([(150, 160), (232, 152), (236, 158), (148, 168)], fill='#2A3A4C')
    d.path(''.join(f'M{150+i*8},{f(160-i*0.75)}l-2,8' for i in range(1, 11)), stroke=INK, stroke_width=0.6, opacity=0.7)
    for x in (156, 186, 216):
        d.rect(x, 162, 2, 14, fill=FORE)
    # ведро и веник
    d.path('M196,154l1,-6h8l1,6Z', fill='#3A4A5C')
    d.ellipse(201, 148, 4, 1, fill=TEAL, opacity=0.6)
    d.path('M210,152l8,-10', stroke=FORE, stroke_width=1.2)
    d.ellipse(219, 140, 4, 2.5, fill=MOSS)
    birch(d, 320, 150, 80, seed=4, lean=-6)
    birch(d, 344, 156, 64, seed=5, lean=4)
    reeds(d, 120, 170, 200, 10, 30, 18, 5)
    return d.render()


def hut():
    d = new('hu')
    sky(d, W, H, INK, '#2A4458', mid='#172739')
    stars(d, 0, 0, W, 90, 45, 111)
    aurora(d, 180, 380, 56, 6, 26, 9, op=0.25, rays=8)
    moon(d, 70, 34, 12, crescent=True, bg='#111C29')
    d.path(ridge(-10, 370, 120, 12, 7, 7), fill=FAR)
    fir_row(d, -10, 370, 124, 16, 30, '#21354A', 8, step=7)
    d.rect(0, 136, W, 64, fill=d.lin([(0, NEAR), (1, FORE)]))
    fog(d, 190, 140, 200, 14, TEAL, 0.2)
    # избушка на курьих ножках
    hx, hy = 150, 104
    # курьи ножки
    for lx in (166, 192):
        d.path(f'M{lx-6},{hy+26}C{lx-8},{hy+36} {lx-4},{hy+44} {lx+4},{hy+44}C{lx+10},{hy+42} {lx+10},{hy+32} {lx+6},{hy+26}Z', fill='#1A2735')
        d.path(f'M{lx-5},{hy+36}q3,3 5,0q3,3 5,0M{lx-3},{hy+41}q3,3 5,0q2,2 4,-1', stroke=SEC, stroke_width=0.6, opacity=0.4, fill='none')
        fx, fy = lx - 3, hy + 64
        d.path(f'M{lx+4},{hy+42}L{fx},{fy}', stroke='#8A7650', stroke_width=3.2, stroke_linecap='round')
        d.path(f'M{lx+2.6},{hy+48}h2.4M{lx+1.4},{hy+53}h2.4M{lx},{hy+58}h2.4', stroke='#5A4A30', stroke_width=0.7)
        d.path(f'M{fx},{fy}l10,1.4M{fx},{fy}l8,4.4M{fx},{fy}l2.6,5M{fx},{fy}l-6,1', stroke='#8A7650', stroke_width=1.8, stroke_linecap='round')
    # оперение у основания
    d.path(f'M{hx+4},{hy+28}q4,6 8,2q4,6 8,1q4,6 8,1q4,6 8,1q4,6 8,1q4,6 8,-1q3,5 6,-1Z', fill='#1A2735')
    # сруб
    logs = d.lin([(0, '#2C3D4F'), (1, '#1A2836')])
    d.rect(hx, hy, 56, 28, fill=logs)
    d.path(''.join(f'M{hx},{hy+i*4.6}h56' for i in range(1, 6)), stroke=INK, stroke_width=0.7, opacity=0.6)
    for i in range(6):
        d.circle(hx - 1, hy + 2.3 + i * 4.6, 2.2, fill='#36495D')
        d.circle(hx + 57, hy + 2.3 + i * 4.6, 2.2, fill='#36495D')
    d.path(f'M{hx-8},{hy+1}L{hx+22},{hy-26}L{hx+64},{hy+1}Z', fill=FORE)
    d.path(f'M{hx-6},{hy}L{hx+22},{hy-24}L{hx+62},{hy}', stroke=GOLD, stroke_width=0.8, opacity=0.5, fill='none')
    d.path(f'M{hx+22},{hy-26}l-3,-6l3,2l3,-2Z', fill=GOLD, opacity=0.8)  # конёк-петушок
    d.rect(hx + 38, hy - 22, 6, 12, fill='#1A2735')
    d.path(f'M{hx+41},{hy-24}C{hx+36},{hy-34} {hx+48},{hy-40} {hx+42},{hy-52}C{hx+38},{hy-60} {hx+48},{hy-66} {hx+46},{hy-74}', stroke=SEC, stroke_width=3, opacity=0.18, fill='none', stroke_linecap='round')
    window(d, hx + 12, hy + 8, 12, 10, frame='#1F2E3E', glow_r=34)
    d.rect(hx + 10, hy + 18, 16, 1.6, fill=GOLD, opacity=0.6)
    d.path(f'M{hx+10},{hy+8}l8,-4l8,4', stroke=GOLD, stroke_width=0.8, opacity=0.6, fill='none')
    # дверь
    d.rect(hx + 34, hy + 6, 12, 22, fill=FORE)
    # фонарь на шесте и тропа
    d.path('M168,200C176,186 190,178 186,166L194,166C202,178 206,188 230,200Z', fill=GOLD, opacity=0.14)
    d.rect(232, 132, 1.6, 36, fill=FORE)
    d.path('M233,132q6,0 8,4', stroke=FORE, stroke_width=1.2, fill='none')
    glow(d, 241, 140, 16, WARM, 0.6)
    d.rect(239, 137, 4, 6, fill=WARM, rx=1)
    # черепа — нет: вместо них горшки на кольях забора
    for x in (80, 96, 112):
        d.rect(x, 150, 2, 22, fill=FORE)
        d.ellipse(x + 1, 148, 4, 3.5, fill='#2E3F52')
        d.rect(x - 2, 144, 6, 1.6, fill='#2E3F52')
    d.line([(76, 158), (120, 160)], stroke=FORE, stroke_width=1.4)
    # кот
    d.path('M262,176c0,-8 10,-9 12,-3l1,-4l1.4,4c1.4,1 1.4,4 0,5h-14Z', fill='#080E15')
    d.path('M262,177c-6,0 -8,-6 -4,-8', stroke='#080E15', stroke_width=1.4, fill='none')
    d.circle(271.6, 172, 0.7, fill=GOLD)
    d.circle(274.2, 172, 0.7, fill=GOLD)
    fir(d, 22, 200, 150, 64, '#080E15', seed=3, tiers=6)
    fir(d, 330, 200, 160, 70, '#080E15', seed=6, tiers=6)
    fir(d, 296, 200, 90, 40, '#0A121B', seed=7, tiers=5)
    grass(d, 0, W, 200, 9, 60, 7, FORE)
    return d.render()


def campfire():
    d = new('ca')
    sky(d, W, H, '#0A111A', '#1C2C3E', mid=INK)
    stars(d, 0, 0, W, 110, 60, 121)
    aurora(d, -10, 200, 50, 6, 26, 3, op=0.22, rays=8)
    d.path(ridge(-10, 370, 118, 12, 3, 8), fill='#172739')
    fir_row(d, -10, 370, 124, 26, 50, '#101B28', 4, step=10, tiers=4)
    d.rect(0, 122, W, 78, fill=d.lin([(0, '#121D29'), (1, FORE)]))
    cx, cy = 176, 172
    # тёплый свет на земле и деревьях
    d.ellipse(cx, cy + 4, 150, 34, fill=d.rad([(0, WARM, 0.35), (0.5, WARM, 0.12), (1, WARM, 0)]))
    glow(d, cx, cy - 16, 90, WARM, 0.32)
    # бревно-сиденье
    d.path('M60,176C70,170 120,168 130,172L130,182C120,186 70,186 60,182Z', fill='#22303E')
    d.ellipse(130, 177, 3.4, 5, fill='#3A4A5A')
    d.path('M66,174h56', stroke=WARM, stroke_width=0.8, opacity=0.4)
    # рюкзак
    rx, ry = 248, 150
    d.path(f'M{rx},{ry+30}C{rx-2},{ry+10} {rx+2},{ry} {rx+14},{ry-2}C{rx+28},{ry} {rx+32},{ry+12} {rx+30},{ry+30}Z', fill='#2A3E52')
    d.path(f'M{rx+4},{ry+8}C{rx+10},{ry+2} {rx+24},{ry+2} {rx+28},{ry+8}L{rx+28},{ry+12}C{rx+20},{ry+8} {rx+10},{ry+8} {rx+4},{ry+12}Z', fill='#22344A')
    d.rect(rx + 8, ry + 16, 16, 10, fill='#22344A', rx=2)
    d.path(f'M{rx+6},{ry+2}C{rx+8},{ry-10} {rx+22},{ry-10} {rx+24},{ry+2}', stroke='#1A2836', stroke_width=2, fill='none')
    d.path(f'M{rx},{ry+14}C{rx+10},{ry+12} {rx+24},{ry+12} {rx+32},{ry+16}', stroke=WARM, stroke_width=0.8, opacity=0.5, fill='none')
    d.rect(rx - 2, ry + 26, 36, 6, fill=TEAL, opacity=0.7, rx=3)  # пенка
    d.path(f'M{rx},{ry+29}h32', stroke=INK, stroke_width=0.5, opacity=0.5)
    # котелок на треноге
    d.path(f'M{cx-26},{cy+6}L{cx},{cy-46}L{cx+26},{cy+6}M{cx},{cy-46}L{cx+4},{cy+8}', stroke='#0B131C', stroke_width=1.6, fill='none')
    d.line([(cx, cy - 46), (cx, cy - 34)], stroke='#0B131C', stroke_width=0.6)
    d.path(f'M{cx-8},{cy-34}h16l-2,10c-1,2 -11,2 -12,0Z', fill='#2A3644')
    d.path(f'M{cx-8},{cy-34}h16', stroke=WARM, stroke_width=0.8, opacity=0.7)
    d.path(f'M{cx-2},{cy-36}c-4,-6 4,-8 0,-14M{cx+3},{cy-36}c-3,-5 3,-7 0,-12', stroke=PARCH, stroke_width=1.2, opacity=0.25, fill='none')
    # дрова
    d.path(f'M{cx-22},{cy+6}L{cx+18},{cy-4}', stroke='#2A2522', stroke_width=5, stroke_linecap='round')
    d.path(f'M{cx+22},{cy+6}L{cx-18},{cy-4}', stroke='#332B26', stroke_width=5, stroke_linecap='round')
    # пламя
    d.path(f'M{cx-16},{cy}C{cx-20},{cy-14} {cx-8},{cy-20} {cx-6},{cy-34}C{cx},{cy-22} {cx+4},{cy-30} {cx+2},{cy-44}C{cx+12},{cy-30} {cx+20},{cy-16} {cx+16},{cy}Z', fill=WARM)
    d.path(f'M{cx-10},{cy}C{cx-12},{cy-10} {cx-4},{cy-14} {cx-2},{cy-24}C{cx+2},{cy-16} {cx+6},{cy-20} {cx+6},{cy-30}C{cx+12},{cy-18} {cx+14},{cy-8} {cx+10},{cy}Z', fill=GOLD)
    d.path(f'M{cx-5},{cy}C{cx-6},{cy-6} {cx},{cy-10} {cx+2},{cy-16}C{cx+6},{cy-8} {cx+8},{cy-4} {cx+5},{cy}Z', fill=PARCH)
    # камни очага
    for i in range(7):
        a = math.pi * (0.05 + i * 0.15)
        d.ellipse(cx + 24 * math.cos(a) * -1, cy + 3 + 4 * math.sin(a), 5, 3, fill='#2A3746')
        d.ellipse(cx + 24 * math.cos(a) * -1, cy + 2 + 4 * math.sin(a), 4, 1.2, fill=WARM, opacity=0.3)
    # искры
    rnd = random.Random(6)
    for _ in range(22):
        x = cx + rnd.gauss(0, 14)
        y = cy - 40 - rnd.random() ** 0.8 * 90
        d.circle(x, y, rnd.uniform(0.5, 1.4), fill=rnd.choice([GOLD, WARM, PARCH]), opacity=round(rnd.uniform(0.5, 1), 2))
    # кружка
    d.rect(232, 176, 7, 8, fill=SEC, opacity=0.8, rx=1)
    d.path('M239,178c3,0 3,4 0,4', stroke=SEC, stroke_width=1, fill='none', opacity=0.8)
    fir(d, 18, 200, 140, 60, '#070C12', seed=2, tiers=6)
    fir(d, 344, 200, 150, 64, '#070C12', seed=3, tiers=6)
    grass(d, 0, W, 200, 8, 50, 8, '#070C12')
    return d.render()


def station():
    d = new('st')
    sky(d, W, H, INK, '#2C4258', mid='#182839')
    stars(d, 0, 0, W, 70, 30, 131)
    moon(d, 70, 30, 8)
    d.path(ridge(-10, 370, 112, 8, 9, 7), fill=FAR)
    fir_row(d, -10, 370, 116, 10, 24, '#22364B', 6, step=7)
    d.rect(0, 114, W, 30, fill=MID)
    # контактный провод и опоры
    d.path('M0,86Q90,90 180,86Q270,90 360,86', stroke='#0B131C', stroke_width=0.8, fill='none')
    for x in (20, 180, 340):
        d.rect(x - 1.2, 80, 2.4, 52, fill='#0F1A26')
        d.path(f'M{x},{84}h10', stroke='#0F1A26', stroke_width=1.4)
    # электричка
    tx = 150
    body = d.lin([(0, '#3A6A6E'), (1, '#24474C')])
    d.path(f'M{tx},132L{tx},108C{tx},100 {tx+6},94 {tx+18},94L370,94L370,132Z', fill=body)
    d.rect(tx, 118, 220, 3, fill=WARM, opacity=0.85)
    d.path(f'M{tx+2},{106}C{tx+2},{100} {tx+6},{97} {tx+14},{97}L{tx+16},{110}L{tx+2},{110}Z', fill='#0E1A24')
    d.path(f'M{tx+5},{101}l6,-2', stroke=TEAL, stroke_width=1, opacity=0.7)
    glow(d, tx + 5, 126, 16, PARCH, 0.55)
    d.circle(tx + 5, 126, 2, fill=PARCH)
    for i in range(12):
        x = tx + 26 + i * 15
        if i in (4, 9):
            d.rect(x - 2, 99, 10, 32, fill='#1B3438')
            d.rect(x, 101, 6, 10, fill=GOLD, opacity=0.6)
            continue
        d.rect(x, 101, 9, 10, fill=GOLD, opacity=0.9)
        d.rect(x, 101, 9, 2, fill=PARCH, opacity=0.4)
    d.path(f'M{tx+120},94l8,-8l8,8M{tx+122},86h12', stroke='#0F1A26', stroke_width=1, fill='none')
    d.rect(tx + 4, 94, 216, 1.4, fill=PARCH, opacity=0.25)
    # платформа
    d.poly([(0, 138), (W, 138), (W, 166), (0, 166)], fill=d.lin([(0, '#2C3C4E'), (1, '#1C2938')]))
    d.rect(0, 137, W, 1.6, fill=PARCH, opacity=0.35)
    d.path('M0,142.5H360', stroke=GOLD, stroke_width=1.6, opacity=0.6, stroke_dasharray='8 5')
    hatch_lines(d, [(x, 148, x + 10, 148) for x in range(4, 360, 26)] + [(x, 156, x + 12, 156) for x in range(16, 360, 30)], SEC, 0.12)
    d.rect(0, 166, W, 34, fill=d.lin([(0, '#121C28'), (1, FORE)]))
    # фонарь
    lx = 96
    d.poly([(lx + 8, 72), (lx + 20, 72), (lx + 52, 160), (lx - 26, 160)], fill=d.lin([(0, WARM, 0.32), (1, WARM, 0.03)]))
    d.ellipse(lx + 13, 156, 40, 6, fill=WARM, opacity=0.18)
    d.rect(lx - 1.6, 70, 3.2, 92, fill='#0B131C')
    d.path(f'M{lx},{72}q8,-6 15,0', stroke='#0B131C', stroke_width=2.2, fill='none')
    glow(d, lx + 14, 74, 28, WARM, 0.6)
    d.poly([(lx + 9, 72), (lx + 19, 72), (lx + 17, 77), (lx + 11, 77)], fill=PARCH)
    # табличка станции (знаки вместо букв)
    d.rect(209, 122, 1.8, 40, fill='#0B131C')
    d.rect(259, 122, 1.8, 40, fill='#0B131C')
    d.rect(202, 112, 66, 14, fill=TEAL, rx=1.5)
    d.path('M210,117h30M210,121h20', stroke=PARCH, stroke_width=1.4, opacity=0.85)
    d.circle(258, 119, 3.4, fill=PARCH, opacity=0.85)
    # скамья и рюкзак
    d.rect(20, 148, 56, 3, fill='#0B131C')
    d.rect(20, 140, 56, 2.4, fill='#0B131C')
    d.rect(24, 140, 2, 22, fill='#0B131C')
    d.rect(70, 140, 2, 22, fill='#0B131C')
    d.path('M50,148c-1,-10 2,-14 8,-14s9,4 8,14Z', fill='#2A3E52')
    d.rect(50, 132, 16, 4, fill=TEAL, opacity=0.8, rx=2)
    d.path('M53,140h10', stroke=GOLD, stroke_width=0.8, opacity=0.6)
    # голубь
    d.path('M300,160c0,-4 4,-6 8,-4l3,-2l-1,3c1,2 0,4 -3,4Z', fill='#0B131C')
    grass(d, 0, W, 200, 6, 30, 3, '#0B131C')
    return d.render()


SCENES = dict(forest=forest, field=field, river=river, lake=lake, village=village, town=town,
              road=road, night=night, rain=rain, swamp=swamp, bathhouse=bathhouse, hut=hut,
              campfire=campfire, station=station)

"""Эмблемы существ в медальоне, viewBox 0 0 120 120."""
import random
from artlib import *

C = 60
R = 56


def new(p):
    d = Doc('0 0 120 120', p)
    frame_circle(d)
    return d


def finish(d):
    frame_ring(d)
    return d.render()


def leshy():
    d = new('le')
    in_circle_stars(d, 14, 1, ymax=50)
    # дальний лес по дуге
    circle_ground_curve(d, C, C, R - 1, 84, 10, '#1A2D3A')
    fir_row(d, 14, 106, 84, 8, 16, '#1A2D3A', 3, step=6, tiers=3)
    circle_ground(d, C, C, R - 1, 96, '#122029')
    # рога-ветви
    br = '#4A4F4F'
    d.path('M48,44C44,34 40,28 30,24M40,31C38,26 38,22 40,18M34,26C30,26 26,28 24,32'
           'M72,44C76,34 80,28 90,24M80,31C82,26 82,22 80,18M86,26C90,26 94,28 96,32'
           'M56,40C54,32 52,28 50,22M64,40C66,32 70,28 70,22',
           stroke=br, stroke_width=2.6, fill='none', stroke_linecap='round')
    d.path('M48,44C44,34 40,28 30,24M72,44C76,34 80,28 90,24', stroke=GOLD, stroke_width=0.6, fill='none', opacity=0.35)
    rnd = random.Random(3)
    for x, y in [(30, 24), (40, 18), (24, 32), (90, 24), (80, 18), (96, 32), (50, 22), (70, 22), (36, 28), (84, 28)]:
        for _ in range(2):
            d.ellipse(x + rnd.uniform(-2.5, 2.5), y + rnd.uniform(-2, 2), 2.6, 1.5, fill=rnd.choice([MOSS, '#3E7A6C', TEAL]), opacity=0.9)
    # голова-пень во мху
    head = d.lin([(0, '#3D7268'), (0.5, MOSS), (1, '#1C3A38')])
    d.path('M38,70C36,54 44,42 60,42C76,42 84,54 82,70C84,84 76,92 60,92C44,92 36,84 38,70Z', fill=head)
    # кора-штрихи
    d.path('M44,52c3,-3 6,-4 10,-4M66,48c4,0 8,2 10,5M42,62c-1,4 -1,8 0,12M78,62c1,4 1,8 0,12',
           stroke=PARCH, stroke_width=0.6, fill='none', opacity=0.3, stroke_linecap='round')
    # брови-сучки
    d.ellipse(46, 72, 4, 2.2, fill=WARM, opacity=0.25)
    d.ellipse(74, 72, 4, 2.2, fill=WARM, opacity=0.25)
    d.path('M45,57C48,53 53,53 57,55M63,55C67,53 72,53 75,57', stroke='#1A2C2C', stroke_width=2.6, fill='none', stroke_linecap='round')
    # глаза — добрые, прищур
    for ex in (51, 69):
        glow(d, ex, 64, 8, GOLD, 0.45)
        d.path(f'M{ex-5},{65}C{ex-3},{60} {ex+3},{60} {ex+5},{65}C{ex+3},{66.5} {ex-3},{66.5} {ex-5},{65}Z', fill=GOLD)
        d.circle(ex + 0.5, 63.6, 1.4, fill=INK)
    # нос-сучок
    d.path('M60,62C58,68 57,72 54,76C58,77 62,76 63,74C62,70 62,66 60,62Z', fill='#4A5550')
    # улыбка
    d.path('M53,80C57,83 63,83 67,80', stroke='#132626', stroke_width=1.4, fill='none', stroke_linecap='round')
    # борода из мха
    beard = d.lin([(0, '#3E7A6C'), (1, '#1E4440')])
    d.path('M42,80C40,92 46,100 48,108C52,100 54,104 56,110C58,102 60,104 62,111C64,104 66,102 70,108C72,100 80,94 78,80C72,88 66,90 60,90C54,90 48,88 42,80Z', fill=beard)
    grass(d, 46, 74, 104, 10, 14, 4, AU1, 0.5, 0.35)
    # гриб и ягоды у бороды
    d.path('M86,98c0,-5 8,-5 8,0Z', fill=WARM)
    d.rect(89, 98, 2, 5, fill=PARCH)
    d.circle(88, 96.8, 0.7, fill=PARCH)
    d.circle(91.4, 96.4, 0.6, fill=PARCH)
    for x, y in [(30, 96), (33, 98), (31, 99.5)]:
        d.circle(x, y, 1.3, fill='#C0504D', opacity=0.9)
    # птичка на ветке
    d.path('M86,23c1,-3 4,-4 6,-2l3,-1l-2,2c0,3 -3,4 -6,3l-3,1Z', fill=INK)
    d.circle(90.5, 21.6, 0.5, fill=GOLD)
    return finish(d)


def domovoy():
    d = new('do')
    # стена-сруб
    chords(d, range(22, 100, 9), stroke=INK, stroke_width=0.8, opacity=0.6)
    # печь справа
    pech = d.lin([(0, '#5E6670'), (1, '#3A4552')], 0, 0, 1, 0)
    cpoly(d, [(70, 98), (70, 44), (72, 41), (75, 40), (118, 40), (118, 98)], fill=pech)
    d.path('M70,46h40', stroke=PARCH, stroke_width=0.8, opacity=0.3)
    d.path('M76,98V78C76,68 96,68 96,78V98Z', fill=INK)
    glow(d, 86, 86, 22, WARM, 0.6)
    d.path('M80,98C79,92 83,90 84,84C86,88 88,86 88,82C91,88 93,92 92,98Z', fill=WARM)
    d.path('M83,98C83,94 86,92 86,89C88,92 89,94 89,98Z', fill=GOLD)
    d.rect(82, 30, 10, 12, fill='#4A5460')
    # пол
    circle_ground(d, C, C, R - 1, 98, '#2A2420')
    chords(d, (104, 110), 1, stroke=INK, stroke_width=0.6, opacity=0.5)
    # тёплый отсвет на полу
    d.ellipse(70, 100, 40, 6, fill=WARM, opacity=0.15)
    # домовой
    body = d.lin([(0, '#3B5266'), (1, '#24384A')], 0, 0, 1, 0)
    d.path('M30,98C28,84 32,72 46,70C60,72 64,84 62,98Z', fill=body)
    d.path('M31,90H61', stroke=GOLD, stroke_width=1.6)
    # лапти
    d.ellipse(38, 99, 6, 3, fill='#8A7650')
    d.ellipse(54, 99, 6, 3, fill='#8A7650')
    d.path('M34,98l8,2M50,98l8,2', stroke='#5A4A30', stroke_width=0.6)
    # руки с кружкой
    d.path('M34,80C30,84 34,90 40,88', stroke='#24384A', stroke_width=5, fill='none', stroke_linecap='round')
    d.rect(39, 82, 7, 8, fill=PARCH, rx=1)
    d.path('M39,84h7', stroke=TEAL, stroke_width=1)
    d.path('M41,80c-1,-3 1,-4 0,-7M44,80c-1,-3 1,-4 0,-6', stroke=PARCH, stroke_width=0.6, opacity=0.4, fill='none')
    # голова: копна волос
    hair = '#6A6A6E'
    d.path('M30,60C28,46 38,38 46,38C56,38 64,46 62,60C64,64 60,66 58,64L34,64C32,66 28,64 30,60Z', fill=hair)
    d.path('M34,46c3,-4 8,-6 12,-6M50,40c4,1 8,4 9,8', stroke=PARCH, stroke_width=0.6, opacity=0.35, fill='none')
    # лицо
    d.ellipse(46, 58, 11, 9, fill='#C9A88A')
    # борода
    d.path('M34,58C32,70 38,82 46,86C54,82 60,70 58,58C54,62 50,64 46,64C42,64 38,62 34,58Z', fill=PARCH)
    d.path('M40,66c1,6 3,10 6,14M46,66v16M52,66c-1,6 -3,10 -6,14', stroke=SEC, stroke_width=0.6, fill='none', opacity=0.6)
    # чёлка на глаза
    d.path('M34,54C38,48 54,48 58,54C54,52 50,53 46,51C42,53 38,52 34,54Z', fill=hair)
    d.circle(41, 56, 1.3, fill=INK)
    d.circle(51, 56, 1.3, fill=INK)
    d.circle(41.4, 55.6, 0.4, fill=PARCH)
    d.circle(51.4, 55.6, 0.4, fill=PARCH)
    d.ellipse(46, 60.5, 3, 2.4, fill='#D98C6A')
    # кот на печи
    d.path('M92,40c0,-6 6,-8 10,-4l2,-4l1,5c2,1 2,3 0,3Z', fill=INK)
    d.circle(101, 37, 0.6, fill=GOLD)
    return finish(d)


def bannik():
    d = new('bn')
    # тёмный сруб бани
    chords(d, range(20, 100, 8), stroke=INK, stroke_width=0.8, opacity=0.6)
    d.rect(80, 26, 16, 12, fill=WARM, opacity=0.5)
    d.path('M88,26v12M80,32h16', stroke=R1, stroke_width=1.4)
    glow(d, 88, 32, 18, WARM, 0.3)
    # полок
    cpoly(d, [(0, 88), (120, 88), (120, 94), (0, 94)], fill='#4A3E34')
    chords(d, (88,), 0.5, stroke=GOLD, stroke_width=0.6, opacity=0.4)
    d.rect(34, 94, 4, 12, fill='#3A3029')
    d.rect(82, 94, 4, 12, fill='#3A3029')
    circle_ground(d, C, C, R - 1, 106, '#241E1A')
    # шайка
    d.path('M70,88L72,76H92L94,88Z', fill='#6A5442')
    d.path('M71,82h22', stroke='#3A2E25', stroke_width=1.2)
    d.ellipse(82, 76, 10, 2, fill=TEAL, opacity=0.8)
    d.rect(90, 70, 2, 6, fill='#6A5442')
    # веник
    d.path('M24,86L40,80', stroke='#6A5442', stroke_width=2, stroke_linecap='round')
    rnd = random.Random(2)
    for _ in range(14):
        d.ellipse(40 + rnd.uniform(0, 12), 78 + rnd.uniform(-5, 4), 3, 1.6, fill=rnd.choice([MOSS, '#3E7A6C', '#5A8A5A']))
    # пар-банник
    cloud = [(60, 52, 20), (44, 58, 13), (76, 58, 13), (52, 40, 12), (68, 40, 12), (60, 32, 10),
             (40, 70, 9), (80, 70, 9), (60, 70, 14)]
    for x, y, r in cloud:
        d.circle(x, y, r + 3, fill=PARCH, opacity=0.08)
    for x, y, r in cloud:
        d.circle(x, y, r, fill=PARCH, opacity=0.22)
    for x, y, r in cloud[:6]:
        d.circle(x - r * 0.2, y - r * 0.25, r * 0.6, fill=PARCH, opacity=0.18)
    # завитки
    d.path('M30,60c-6,-2 -8,-8 -4,-12c3,-3 7,0 5,3M90,60c6,-2 8,-8 4,-12c-3,-3 -7,0 -5,3M60,22c-3,-4 0,-8 4,-7',
           stroke=PARCH, stroke_width=1.4, opacity=0.4, fill='none', stroke_linecap='round')
    # лицо из пара
    for ex in (52, 68):
        d.ellipse(ex, 52, 3.2, 4.2, fill=INK)
        d.circle(ex + 1, 50.6, 1.1, fill=GOLD)
    d.path('M50,45c2,-2 4,-2 6,-1M64,44c2,-1 4,-1 6,1', stroke=INK, stroke_width=1.2, fill='none', stroke_linecap='round')
    d.path('M55,62c3,2 7,2 10,0', stroke=INK, stroke_width=1.4, fill='none', stroke_linecap='round')
    d.ellipse(46, 59, 3, 1.6, fill=WARM, opacity=0.35)
    d.ellipse(74, 59, 3, 1.6, fill=WARM, opacity=0.35)
    # капли
    for x, y in [(30, 40), (92, 46), (36, 30)]:
        d.path(f'M{x},{y}c-1.5,2.5 -1.5,4 0,4c1.5,0 1.5,-1.5 0,-4Z', fill=TEAL, opacity=0.8)
    return finish(d)


def poludnitsa():
    d = new('po')
    # зной: тёплое небо внутри медальона
    d.circle(C, C, R - 1, fill=d.rad([(0, GOLD, 0.35), (0.6, WARM, 0.12), (1, WARM, 0)], cy=0.35))
    glow(d, 60, 40, 36, GOLD, 0.55)
    d.circle(60, 40, 20, fill=GOLD)
    rays = ''
    for i in range(24):
        a = math.radians(i * 15)
        r0, r1 = 23, 28 if i % 2 else 32
        rays += f'M{f(60+r0*math.cos(a))},{f(40+r0*math.sin(a))}L{f(60+r1*math.cos(a))},{f(40+r1*math.sin(a))}'
    d.path(rays, stroke=GOLD, stroke_width=1.2, opacity=0.7, stroke_linecap='round')
    d.circle(60, 40, 16.5, fill='none', stroke=PARCH, stroke_width=0.6, opacity=0.5)
    # поле
    circle_ground_curve(d, C, C, R - 1, 96, 6, '#3D3A2E')
    rnd = random.Random(5)
    st, hd = '', ''
    for _ in range(46):
        x = rnd.uniform(12, 108)
        h = rnd.uniform(12, 26)
        b = rnd.uniform(-3, 4)
        if abs(x - 60) < 22:
            h *= 0.6
        y0 = 60 + math.sqrt(max(0, 54 ** 2 - (x - 60) ** 2)) - 2
        h = min(h, y0 - 80)
        st += f'M{f(x)},{f(y0)}q{f(b*0.3)},{f(-h*0.6)} {f(b)},{f(-h)}'
        hd += f'M{f(x+b)},{f(y0-h)}c-1.2,1.8 -1.1,4.4 0.3,6c1.2,-1.6 1.1,-4.2 -0.3,-6Z'
    # фигура
    dress = d.lin([(0, PARCH), (1, '#C9BFA8')], 0, 0, 1, 0)
    d.path('M53,46C50,48 48,52 48,58L42,104C52,108 68,108 78,104L72,58C72,52 70,48 67,46Z', fill=dress)
    d.path('M56,60L52,104M60,60V106M64,60L68,104', stroke=SEC, stroke_width=0.6, opacity=0.6, fill='none')
    d.path('M48,58C54,60 66,60 72,58', stroke=GOLD, stroke_width=1, fill='none')
    # волосы до пояса
    d.path('M53,32C50,40 50,52 52,62L56,60L56,40ZM67,32C70,40 70,52 68,62L64,60L64,40Z', fill='#B89A5E')
    # голова и венок
    d.ellipse(60, 34, 6.5, 7.5, fill='#E3D3B8')
    d.path('M53.5,32C54,26 66,26 66.5,32C64,30 56,30 53.5,32Z', fill='#B89A5E')
    for i, x in enumerate(range(52, 70, 3)):
        d.circle(x, 28.5 + abs(x - 60) * 0.12, 1.6, fill=TEAL if i % 2 else PARCH)
    d.path('M57,35c1,0.8 2,0.8 3,0M61,35c1,0.8 2,0.8 3,0', stroke='#8A7660', stroke_width=0.6, fill='none')
    # рука с серпом
    d.path('M70,50C76,48 80,42 82,36', stroke='#E3D3B8', stroke_width=3.4, fill='none', stroke_linecap='round')
    d.path('M70,50C76,48 80,42 82,36', stroke=PARCH, stroke_width=3, fill='none', stroke_linecap='round')
    d.rect(81, 33, 3, 7, fill='#6A5442', rx=1)
    d.path('M83,33C80,23 85,17 93,19C88,21 85,25 86,32Z', fill=PARCH)
    d.path('M83,33C80,23 85,17 93,19', stroke=SEC, stroke_width=0.6, fill='none')
    sparkle(d, 92, 20, 2.6, PARCH)
    d.path('M50,52C46,62 46,72 48,78', stroke=PARCH, stroke_width=3, fill='none', stroke_linecap='round')
    # рожь поверх подола
    d.path(st, stroke='#6A5E40', stroke_width=0.7, fill='none')
    d.path(hd, fill=GOLD)
    # васильки
    for x, y in [(30, 96), (88, 98), (40, 104)]:
        d.circle(x, y, 1.8, fill=TEAL)
        d.circle(x, y, 0.6, fill=INK)
    return finish(d)


def vodyanoy():
    d = new('vo')
    in_circle_stars(d, 10, 6, ymax=40)
    moon(d, 84, 28, 5, halo=2.4)
    # вода
    wl = 62
    circle_ground(d, C, C, R - 1, wl, d.lin([(0, '#2C5566'), (1, '#0E1C26')]))
    # голова
    head = d.lin([(0, '#4E8C7E'), (1, '#24504A')])
    d.path(f'M34,{wl}C32,40 44,28 60,28C76,28 88,40 86,{wl}Z', fill=head)
    # шапка из камыша
    d.path('M40,40C42,26 50,18 52,12M48,34C50,24 56,16 60,10M60,30C62,22 66,16 70,12M72,36C74,28 78,22 84,18',
           stroke='#3E6E58', stroke_width=1.6, fill='none', stroke_linecap='round')
    for x, y in [(52, 12), (60, 10), (70, 12)]:
        d.ellipse(x, y + 3, 1.6, 4, fill='#5A4636')
    # брови и глаза
    d.path('M42,44C46,40 52,40 55,43M65,43C68,40 74,40 78,44', stroke='#183632', stroke_width=2.4, fill='none', stroke_linecap='round')
    for ex in (49, 71):
        d.ellipse(ex, 49, 5, 4.4, fill=PARCH)
        d.circle(ex + 0.8, 49.5, 2.4, fill=INK)
        d.circle(ex + 1.6, 48.4, 0.8, fill=PARCH)
        d.path(f'M{ex-5},{48}C{ex-3},{44.5} {ex+3},{44.5} {ex+5},{48}', fill='#2E625A')
    d.ellipse(60, 56, 4.4, 3.4, fill='#3D7A6E')
    d.ellipse(45, 56, 3, 1.6, fill=WARM, opacity=0.3)
    d.ellipse(75, 56, 3, 1.6, fill=WARM, opacity=0.3)
    # борода-волны
    beard = d.lin([(0, '#3A7A72'), (1, '#1E4A50')])
    d.path(f'M34,{wl-6}C36,{wl+8} 26,74 18,82C30,84 38,80 42,86C48,82 52,90 60,94C68,90 72,82 78,86C82,80 90,84 102,82C94,74 84,{wl+8} 86,{wl-6}C78,{wl+2} 70,{wl+4} 60,{wl+4}C50,{wl+4} 42,{wl+2} 34,{wl-6}Z', fill=beard)
    curls = ''
    for x, y, s in [(28, 78, 1), (40, 76, 1), (52, 82, 1), (64, 82, -1), (76, 76, -1), (90, 78, -1), (46, 68, 1), (72, 68, -1), (58, 72, 1)]:
        curls += f'M{x-6*s},{y}c{2*s},-5 {8*s},-6 {10*s},-1c{1*s},3 -{2*s},5 -{4*s},3'
    d.path(curls, stroke=TEAL, stroke_width=1.2, fill='none', stroke_linecap='round')
    d.path(curls, stroke=PARCH, stroke_width=0.5, fill='none', opacity=0.4, stroke_linecap='round')
    # улыбка
    d.path('M53,61c4,3 10,3 14,0', stroke='#132a2a', stroke_width=1.4, fill='none', stroke_linecap='round')
    # кувшинки
    for x, y, s in [(34, 90, 1), (84, 92, 0.9), (60, 102, 1.1), (98, 74, 0.7)]:
        d.ellipse(x + 3 * s, y + 2 * s, 9 * s, 2.8 * s, fill='#2F6B4E')
        for k in range(-2, 3):
            d.path(f'M{f(x)},{f(y)}C{f(x+k*2.6*s-2*s)},{f(y-4*s)} {f(x+k*2.6*s+2*s)},{f(y-4*s)} {f(x)},{f(y)}Z', fill=PARCH)
        d.circle(x, y - 1.4 * s, 1.4 * s, fill=GOLD)
    chords(d, (106, 110), 10, stroke=TEAL, stroke_width=0.6, opacity=0.4)
    d.path('M76,104c3,-2 6,-2 8,0c-2,2 -5,2 -8,0l-3,2v-4Z', fill=GOLD, opacity=0.8)
    return finish(d)


def kikimora():
    d = new('ki')
    in_circle_stars(d, 12, 7, ymax=44)
    moon(d, 34, 32, 6, halo=2.4, crescent=True, bg='#1A2A3A')
    reeds(d, 22, 98, 98, 26, 58, 30, 2, '#1E3A3A', head_color='#5A4636')
    circle_ground_curve(d, C, C, R - 1, 96, 6, '#152430')
    circle_ground(d, C, C, R - 1, 100, d.lin([(0, '#1E3644'), (1, '#0E1A24')]))
    chords(d, (104, 108), 8, stroke=TEAL, stroke_width=0.6, opacity=0.4)
    # кочка
    d.path('M30,98C34,88 70,86 80,98Z', fill='#2A4A44')
    grass(d, 32, 78, 96, 6, 14, 4, '#3E7A6C', 0.7)
    # прялка: донце + лопасть
    d.path('M40,96L72,96L72,93L46,93Z', fill='#6A5442')
    d.rect(66, 52, 3, 42, fill='#6A5442')
    d.path('M60,52H76L74,40C72,34 64,34 62,40Z', fill='#7A6450')
    d.path('M63,44h10M64,48h8', stroke=GOLD, stroke_width=0.6, opacity=0.6)
    d.circle(68, 38, 1.4, fill=GOLD, opacity=0.8)
    # кудель
    for x, y, r in [(68, 56, 5), (72, 60, 4), (64, 60, 4), (68, 64, 4)]:
        d.circle(x, y, r, fill=PARCH, opacity=0.75)
    # кикимора сидит на донце
    body = d.lin([(0, '#3E6A6A'), (1, '#24444A')])
    d.path('M44,94C40,84 42,72 50,70C56,70 58,78 58,94Z', fill=body)
    # платок
    d.path('M42,66C40,56 46,50 51,50C57,50 60,56 58,66C56,72 44,72 42,66Z', fill='#7A3E3A')
    d.path('M44,60c2,-1 4,-1 6,0M47,55c2,-1 4,0 5,1', stroke=GOLD, stroke_width=0.6, opacity=0.7, fill='none')
    d.path('M42,66L36,74L44,70Z', fill='#7A3E3A')
    # лицо
    d.ellipse(52, 62, 5, 5.4, fill='#9CB08A')
    d.path('M56,61C60,62 63,63 64,65C61,65.5 58,65 56,64Z', fill='#8AA078')
    d.circle(51, 60.5, 1.2, fill=GOLD)
    d.circle(54.4, 60.5, 1.2, fill=GOLD)
    d.circle(51.2, 60.3, 0.5, fill=INK)
    d.circle(54.6, 60.3, 0.5, fill=INK)
    d.path('M51,65.5c1,0.8 2,0.8 3,0', stroke=INK, stroke_width=0.6, fill='none')
    # руки и нить с веретеном
    d.path('M54,76C58,74 60,70 62,66', stroke='#9CB08A', stroke_width=1.6, fill='none', stroke_linecap='round')
    d.path('M48,78C50,84 54,86 56,84', stroke='#9CB08A', stroke_width=1.6, fill='none', stroke_linecap='round')
    d.path('M64,62C60,70 58,78 57,84', stroke=PARCH, stroke_width=0.5, opacity=0.9, fill='none')
    d.path('M57,82l-1,10M54.5,86c1.5,-1 3.5,-1 5,0c-1,3 -4,3 -5,0Z', stroke='#6A5442', stroke_width=0.8, fill='#8A7056')
    # лягушка
    d.ellipse(84, 98, 4, 2.6, fill='#3E7A6C')
    d.circle(82.6, 96, 1, fill='#3E7A6C')
    d.circle(85.4, 96, 1, fill='#3E7A6C')
    d.circle(82.6, 95.8, 0.4, fill=GOLD)
    d.circle(85.4, 95.8, 0.4, fill=GOLD)
    reeds(d, 24, 40, 104, 20, 40, 10, 9, '#122422', head_color='#4A3A2E')
    reeds(d, 86, 96, 104, 18, 36, 8, 10, '#122422', head_color='#4A3A2E')
    return finish(d)


def rusalka():
    d = new('ru')
    in_circle_stars(d, 12, 8, ymax=44)
    moon(d, 84, 34, 8, halo=2.2)
    # дальний берег
    circle_ground(d, C, C, R - 1, 70, '#1E3448')
    fir_row(d, 50, 108, 72, 4, 10, '#1A2D40', 5, step=4)
    circle_ground(d, C, C, R - 1, 70, d.lin([(0, '#2B4A62'), (1, '#0E1A24')]))
    reflection(d, 84, 72, 104, PARCH, 6, op=0.5)
    chords(d, (80, 88, 96, 104), 22, stroke=TEAL, stroke_width=0.6, opacity=0.35)
    # ближний берег
    cpoly(d, sample([(0, 92), (20, 84), (50, 84), (70, 96), (80, 108), (84, 120)]) + [(0, 120)], fill='#152430')
    # береза
    birch(d, 26, 94, 76, seed=3, lean=4, crown=False)
    d.path('M28,40C36,34 44,34 50,38M28,52C20,46 14,46 10,50M29,32C30,26 34,22 38,20',
           stroke=PARCH, stroke_width=1, fill='none', opacity=0.8)
    rnd = random.Random(5)
    for _ in range(26):
        lx, ly = rnd.uniform(12, 52), rnd.uniform(20, 56)
        if (lx - 60) ** 2 + (ly - 60) ** 2 > 50 ** 2:
            continue
        d.ellipse(lx, ly, 2.2, 1.3, fill=rnd.choice([MOSS, '#3E7A6C', '#5A9A7A']), opacity=0.9)
    # ленты на ветке
    d.path('M42,36C44,44 40,50 44,58C46,62 44,66 46,70', stroke=WARM, stroke_width=1.6, fill='none', stroke_linecap='round')
    d.path('M45,37C49,44 47,50 52,56', stroke='#C0504D', stroke_width=1.4, fill='none', stroke_linecap='round')
    d.circle(43.5, 36.5, 1.4, fill=WARM)
    # русалка сидит на берегу, вполоборота
    dress = d.lin([(0, PARCH), (1, '#BFB49C')])
    d.path('M44,90C44,80 48,72 54,70C60,70 62,78 62,86L70,92C66,96 50,96 44,94Z', fill=dress)
    # волосы струятся до воды
    hair = d.lin([(0, '#3E7A7A'), (0.6, TEAL), (1, '#4FA3A5', 0.3)])
    d.path('M50,58C46,64 44,74 46,84C48,92 54,96 60,104C64,108 68,108 72,104C66,100 62,94 62,86C60,78 60,68 58,60Z', fill=hair)
    d.path('M51,64c-2,8 -2,16 2,24M55,64c0,8 2,18 8,26', stroke=PARCH, stroke_width=0.5, opacity=0.4, fill='none')
    d.ellipse(55, 58, 5, 6, fill='#E3D3B8')
    d.path('M50,57C50,51 60,50 60,56C58,54 54,54 50,57Z', fill='#3E7A7A')
    # венок
    for x in (50, 52.5, 55, 57.5, 60):
        d.circle(x, 52.5 - (2 - abs(x - 55) / 2.5), 1.3, fill=PARCH if x != 55 else GOLD)
    d.path('M57,58c0.8,0.6 1.6,0.6 2.4,0', stroke='#8A7660', stroke_width=0.5, fill='none')
    # рука к воде
    d.path('M58,72C64,78 68,84 72,88', stroke='#E3D3B8', stroke_width=2, fill='none', stroke_linecap='round')
    d.ellipse(73, 90, 5, 1.2, fill='none', stroke=PARCH, stroke_width=0.5, opacity=0.6)
    d.ellipse(73, 90, 9, 2.2, fill='none', stroke=PARCH, stroke_width=0.4, opacity=0.35)
    grass(d, 12, 44, 96, 8, 16, 6, '#2A4A44', 0.8)
    return finish(d)


def baba_yaga():
    d = new('by')
    in_circle_stars(d, 20, 9, ymax=60)
    moon(d, 70, 44, 20, halo=2.2)
    # лес и избушка внизу
    circle_ground_curve(d, C, C, R - 1, 94, 6, '#16273A')
    fir_row(d, 18, 102, 94, 10, 20, '#16273A', 4, step=6)
    circle_ground(d, C, C, R - 1, 100, FORE)
    d.rect(78, 82, 14, 9, fill='#2A3A4C')
    d.poly([(76, 83), (85, 76), (94, 83)], fill=FORE)
    d.rect(82, 84, 3, 3, fill=WARM)
    glow(d, 83.5, 85.5, 6, WARM, 0.5)
    d.path('M81,91l-2,6l-2,1M89,91l2,6l2,1', stroke=FORE, stroke_width=1.2, fill='none')
    # след метлы — искры
    rnd = random.Random(3)
    for i in range(14):
        t = i / 14
        d.circle(14 + 30 * t + rnd.uniform(-2, 2), 70 - 16 * t + rnd.uniform(-3, 3), rnd.uniform(0.5, 1.2), fill=GOLD, opacity=round(0.3 + 0.6 * t, 2))
    # метла
    d.path('M30,68L50,56', stroke='#7A6450', stroke_width=1.8, stroke_linecap='round')
    d.path('M32,67L18,76L16,70L20,66Z', fill='#8A7056')
    d.path('M30,68L16,74M30,68L17,71M30,68L18,77', stroke='#5A4636', stroke_width=0.6)
    # ступа
    st = d.lin([(0, '#6A5442'), (1, '#3E3028')], 0, 0, 1, 0)
    d.path('M48,52L80,52L76,78C74,82 54,82 52,78Z', fill=st)
    d.ellipse(64, 52, 16, 3, fill='#4A3A2E')
    d.path('M49,58H79M51,72H77', stroke=GOLD, stroke_width=1, opacity=0.7)
    d.path('M60,58v14M70,58v14', stroke='#2A2018', stroke_width=0.6, opacity=0.6)
    # бабушка
    d.path('M54,52C54,42 58,36 64,36C70,36 72,42 72,52Z', fill='#3A4E62')
    d.path('M56,34C54,26 58,20 64,20C70,20 74,26 72,34C70,38 58,38 56,34Z', fill='#7A3E3A')
    d.path('M58,24c3,-2 7,-2 10,0M57,29c4,-1 9,-1 13,0', stroke=GOLD, stroke_width=0.6, opacity=0.8, fill='none')
    d.circle(60, 32, 1.3, fill=GOLD, opacity=0.8)
    d.circle(66, 30, 1.3, fill=GOLD, opacity=0.8)
    d.ellipse(68, 30, 5, 5.4, fill='#C9A88A')
    d.path('M72,29C76,30 79,32 80,34C77,34.5 74,34 72,33Z', fill='#B8967A')
    d.circle(69.5, 28.5, 0.9, fill=INK)
    d.path('M67,33c1.5,1.2 3,1.2 4.4,0.2', stroke=INK, stroke_width=0.6, fill='none')
    d.path('M54,34L48,44L58,38Z', fill='#7A3E3A')
    # пест-весло
    d.path('M74,44L90,28', stroke='#8A7056', stroke_width=2, stroke_linecap='round')
    d.ellipse(91, 26.5, 2.4, 3.6, fill='#8A7056')
    d.path('M70,46C72,44 74,42 76,42', stroke='#C9A88A', stroke_width=2.2, fill='none', stroke_linecap='round')
    # кот в ступе
    d.path('M74,52c0,-4 4,-5 5,-2l1,-3l1,3l0,2Z', fill=INK)
    d.circle(78.5, 50, 0.5, fill=GOLD)
    return finish(d)


def ovinnik():
    d = new('ov')
    in_circle_stars(d, 14, 10, ymax=40)
    circle_ground(d, C, C, R - 1, 100, '#2A2420')
    # овин
    wall = d.lin([(0, '#33465A'), (1, '#1E2C3A')])
    d.path('M22,100V58L60,30L98,58V100Z', fill=wall)
    d.path(''.join(f'M22,{y}H98' for y in range(64, 100, 6)), stroke=INK, stroke_width=0.7, opacity=0.6)
    # соломенная крыша
    d.path('M14,62L60,22L106,62L98,64L60,32L22,64Z', fill='#8A7650')
    hatch_lines(d, [(60 - 4 * i, 26 + 3.4 * i, 60 - 4 * i - 3, 30 + 3.4 * i) for i in range(1, 11)] +
                [(60 + 4 * i, 26 + 3.4 * i, 60 + 4 * i + 3, 30 + 3.4 * i) for i in range(1, 11)], '#3A3020', 0.8, 0.8)
    d.path('M16,62L60,24L104,62', stroke=GOLD, stroke_width=0.8, fill='none', opacity=0.5)
    # открытые ворота
    d.path('M40,100V66C40,58 80,58 80,66V100Z', fill=FORE)
    glow(d, 60, 84, 34, WARM, 0.6)
    d.path('M40,100V66L30,70V104Z', fill='#2A3A4A')
    d.path('M80,100V66L90,70V104Z', fill='#2A3A4A')
    # снопы внутри
    for x in (46, 74):
        d.path(f'M{x-4},100L{x-2},84L{x+2},84L{x+4},100Z', fill='#8A7650')
        d.path(f'M{x-3},84C{x-4},78 {x+4},78 {x+3},84', fill='#B89A5E')
        d.rect(x - 3, 88, 6, 1.4, fill='#5A4A30')
    # огонёк с глазами
    cx, cy = 60, 90
    d.path(f'M{cx-9},{cy+8}C{cx-14},{cy} {cx-8},{cy-8} {cx-4},{cy-16}C{cx-2},{cy-10} {cx+1},{cy-12} {cx+2},{cy-22}C{cx+8},{cy-12} {cx+14},{cy-2} {cx+9},{cy+8}Z', fill=WARM)
    d.path(f'M{cx-6},{cy+8}C{cx-9},{cy+2} {cx-4},{cy-4} {cx-1},{cy-8}C{cx+1},{cy-4} {cx+3},{cy-6} {cx+4},{cy-12}C{cx+8},{cy-4} {cx+9},{cy+2} {cx+6},{cy+8}Z', fill=GOLD)
    for ex in (cx - 3.4, cx + 3.4):
        d.ellipse(ex, cy, 2.2, 2.8, fill=INK)
        d.circle(ex + 0.7, cy - 0.9, 0.8, fill=PARCH)
    d.path(f'M{cx-2},{cy+4.4}c1.2,1 2.8,1 4,0', stroke=INK, stroke_width=0.8, fill='none', stroke_linecap='round')
    # искорки
    for x, y in [(52, 70), (68, 66), (60, 62), (72, 74)]:
        d.circle(x, y, 0.8, fill=GOLD)
    # свет на земле
    cpoly(d, [(40, 100), (80, 100), (96, 120), (24, 120)], fill=WARM, opacity=0.2)
    # ведро с водой — напоминание об осторожности
    d.path('M84,104l1,-7h8l1,7Z', fill='#4A5A6A')
    d.ellipse(89, 97, 4, 1, fill=TEAL)
    return finish(d)


CREATURES = dict(leshy=leshy, domovoy=domovoy, bannik=bannik, poludnitsa=poludnitsa, vodyanoy=vodyanoy,
                 kikimora=kikimora, rusalka=rusalka, baba_yaga=baba_yaga, ovinnik=ovinnik)

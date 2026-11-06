"""Сергей: портрет и значок для карты. Плюс общие фигурки путника."""
from artlib import *

SKIN_SH = '#3A4452'
SKIN_LT = '#A88C72'
HAIR = '#141E2A'


def walker(d, x, y, s, body=PARCH, pack=GOLD, stick=GOLD, sw=1.0, mat=TEAL, outline=None, ow=0):
    """Идущий путник в профиль (вправо). (x, y) — точка у ног, рост ≈ 40*s.
    outline — цвет подложки-обводки толщиной ow (в единицах фигуры)."""
    if outline:
        _walker(d, x, y, s, outline, outline, outline, sw, outline, ow, 1)
    _walker(d, x, y, s, body, pack, stick, sw, mat, 0, 0.75)


def _walker(d, x, y, s, body, pack, stick, sw, mat, ow, back_op):
    def P(dx, dy):
        return f'{f(x + dx * s)},{f(y + dy * s)}'
    w = sw * s
    o = 2 * ow * s
    lk = dict(stroke_linecap='round', stroke_linejoin='round', fill='none')
    d.path(f'M{P(-1,-17)}L{P(-4.5,-9)}L{P(-8.5,-1.5)}l{f(-2.5*s)},{f(0.4*s)}', stroke=body, stroke_width=4 * w + o, opacity=back_op, **lk)
    pk = f'M{P(-3,-31)}L{P(-9.5,-30)}C{P(-11.5,-29.5)} {P(-11.5,-21)} {P(-10.5,-19)}L{P(-2.5,-19.5)}Z'
    if ow:
        d.path(pk, fill=pack, stroke=pack, stroke_width=o, stroke_linejoin='round')
    else:
        d.path(pk, fill=pack)
    d.path(f'M{P(-11,-33.5)}L{P(-4,-33.5)}', stroke=mat, stroke_width=3.2 * w + o, stroke_linecap='round')
    d.path(f'M{P(0.8,-28.5)}L{P(-1,-17.5)}', stroke=body, stroke_width=5.6 * w + o, stroke_linecap='round')
    d.path(f'M{P(-1,-17)}L{P(3.5,-9.5)}L{P(5,-1.5)}l{f(3*s)},0', stroke=body, stroke_width=4 * w + o, **lk)
    d.path(f'M{P(9.5,-22)}L{P(12.5,0)}', stroke=stick, stroke_width=1.6 * w + o, stroke_linecap='round')
    d.path(f'M{P(1.2,-27)}L{P(5,-21.5)}L{P(9.8,-19.5)}', stroke=body, stroke_width=3.2 * w + o, **lk)
    d.circle(x + 2 * s, y - 34.5 * s, 4 * s + o / 2, fill=body)


def hiker_back(d, x, yb, h, body=FORE, pack='#24384C', mat=TEAL, rim=GOLD, rim_op=0.6):
    """Путник со спины, стоит. h — рост."""
    k = h / 60

    def P(dx, dy):
        return f'{f(x + dx * k)},{f(yb + dy * k)}'
    # ноги
    d.path(f'M{P(-6,-26)}L{P(-6.5,0)}L{P(-1.5,0)}L{P(-0.8,-24)}L{P(0.8,-24)}L{P(1.5,0)}L{P(6.5,0)}L{P(6,-26)}Z', fill=body)
    # корпус
    d.path(f'M{P(-9,-46)}C{P(-11,-40)} {P(-9,-30)} {P(-7,-24)}L{P(7,-24)}C{P(9,-30)} {P(11,-40)} {P(9,-46)}C{P(5,-50)} {P(-5,-50)} {P(-9,-46)}Z', fill=body)
    # руки
    d.path(f'M{P(-9,-45)}C{P(-12,-38)} {P(-12,-32)} {P(-11,-27)}M{P(9,-45)}C{P(12,-38)} {P(12,-32)} {P(11,-27)}', stroke=body, stroke_width=3.4 * k, fill='none', stroke_linecap='round')
    # голова
    d.ellipse(x, yb - 54 * k, 4.6 * k, 5.4 * k, fill=body)
    # рюкзак
    d.path(f'M{P(-7.5,-47)}C{P(-8,-49)} {P(8,-49)} {P(7.5,-47)}L{P(8,-29)}C{P(8,-27)} {P(-8,-27)} {P(-8,-29)}Z', fill=pack)
    d.path(f'M{P(-5.5,-38)}L{P(5.5,-38)}L{P(5.5,-31)}L{P(-5.5,-31)}Z', fill=body, opacity=0.35)
    d.path(f'M{P(-9,-49)}L{P(9,-49)}', stroke=mat, stroke_width=3.2 * k, stroke_linecap='round')
    if rim:
        d.path(f'M{P(-4,-59)}C{P(-1,-60.5)} {P(2,-60.5)} {P(4,-58)}M{P(-8,-49.5)}L{P(8,-49.5)}', stroke=rim, stroke_width=0.8 * k, fill='none', opacity=rim_op)


def sergey():
    d = Doc('0 0 200 240', 'se')
    d.rect(0, 0, 200, 240, fill=d.lin([(0, INK), (0.6, '#17273A'), (1, R2)]))
    stars(d, 0, 0, 200, 120, 26, 3)
    aurora(d, 60, 220, 52, 6, 40, 4, op=0.45, rays=12)
    glow(d, 120, 96, 92, GOLD, 0.22)
    d.circle(112, 104, 80, fill='none', stroke=GOLD, stroke_width=0.8, opacity=0.35)
    d.circle(112, 104, 84, fill='none', stroke=GOLD, stroke_width=0.4, opacity=0.2)
    # дальние холмы и лес
    d.path(ridge(-10, 210, 186, 10, 4, 6), fill=FAR)
    fir_row(d, -10, 210, 188, 8, 18, '#22364B', 5, step=6)
    d.path(ridge(-10, 210, 204, 6, 6, 5), fill=MID)
    # рюкзак за спиной
    pk = d.lin([(0, '#2E4660'), (1, '#1A2A3C')], 0, 0, 1, 0)
    d.path('M40,240L38,150C38,130 50,120 68,120L88,122L92,240Z', fill=pk)
    d.path('M44,160C52,156 72,156 84,160', stroke=INK, stroke_width=1.2, opacity=0.6, fill='none')
    d.path('M44,196h40v18c0,4 -40,4 -40,0Z', fill='#1A2A3C')
    d.path('M42,150L40,240', stroke=GOLD, stroke_width=0.8, opacity=0.25)
    # пенка-скатка
    d.rect(34, 106, 58, 16, rx=8, fill=d.lin([(0, '#6FC0BE'), (1, '#2E7A7A')]))
    d.ellipse(36, 114, 5, 8, fill='#2E6A6A')
    d.path('M36,114m-2,0a2,3 0 1 1 4,0a3.5,5 0 1 1 -7,0', stroke=TEAL, stroke_width=0.8, fill='none')
    d.path('M54,106v16M76,106v16', stroke=INK, stroke_width=2, opacity=0.7)
    # корпус: куртка
    jk = d.lin([(0, '#2C4760'), (0.7, '#203448'), (1, '#18283A')], 1, 0, 0, 0.6)
    d.path('M58,240L60,178C60,160 72,150 88,146L100,142L120,142C136,146 154,152 162,168C168,182 170,212 172,240Z', fill=jk)
    # складки
    d.path('M70,190C72,206 72,222 70,240M150,182C154,200 156,220 156,240', stroke=INK, stroke_width=1, opacity=0.45, fill='none')
    # шея
    d.path('M100,120L100,146L120,146L119,124Z', fill=d.lin([(0, SKIN_SH), (1, '#6A5A4C')], 0, 0, 1, 0))
    # воротник-стойка
    d.path('M92,148C94,136 122,132 130,144L126,156C116,150 102,150 96,158Z', fill='#34536E')
    d.path('M96,146C104,140 118,138 128,144', stroke=GOLD, stroke_width=0.8, opacity=0.5, fill='none')
    d.path('M112,152C111,180 109,210 108,240', stroke=TEAL, stroke_width=1.2, opacity=0.6, fill='none')
    # лямки рюкзака
    d.path('M84,146C94,170 96,204 94,240', stroke='#132030', stroke_width=11, fill='none')
    d.path('M134,148C146,172 148,206 146,240', stroke='#132030', stroke_width=10, fill='none')
    d.rect(88, 196, 12, 7, fill=GOLD, rx=1.5, opacity=0.9)
    d.rect(140, 196, 11, 7, fill=GOLD, rx=1.5, opacity=0.9)
    d.path('M100,200H140', stroke='#132030', stroke_width=3)
    # контровой свет по плечу
    d.path('M122,142C138,146 154,152 162,168C168,182 170,212 172,240', stroke=GOLD, stroke_width=1.4, opacity=0.55, fill='none')
    # голова
    face = d.lin([(0, SKIN_SH), (0.55, '#77644F'), (1, SKIN_LT)], 0, 0, 1, 0)
    head = ('M84,78C86,62 100,54 114,56C126,58 132,68 132,80C132,85 133,88 134,90L140,101'
            'C140.5,103 139,105 135,105C135,108 136,110 135,112C134,114 135,116 134,118'
            'C134,124 130,130 122,132C112,134 102,130 96,124C90,118 86,110 85,100C82,94 82,86 84,78Z')
    d.path(head, fill=face)
    # щетина
    d.path('M96,116C102,126 112,132 122,132C130,130 134,124 134,118C132,121 128,121 126,119C118,121 106,120 96,110Z', fill=HAIR, opacity=0.4)
    d.path('M126,108C129,107 133,107 135,108', stroke=HAIR, stroke_width=1.6, opacity=0.5, fill='none')
    # волосы
    d.path('M84,102C78,80 86,56 110,54C126,53 136,62 134,76C130,70 124,68 118,70C112,72 106,74 102,79C99,85 99,92 98,98C96,101 92,104 88,108Z', fill=HAIR)
    d.path('M92,66C98,60 108,57 118,58M88,78C92,70 98,66 106,64', stroke=SEC, stroke_width=0.6, opacity=0.35, fill='none')
    # ухо
    d.ellipse(98, 99, 4, 6, fill='#5A5046')
    d.path('M97,95c2,1 2,6 0,8', stroke=SKIN_SH, stroke_width=0.8, fill='none')
    # бровь и глаз — взгляд вдаль
    d.path('M118,84C122,82 126,82 130,84.5', stroke=HAIR, stroke_width=1.8, fill='none', stroke_linecap='round')
    d.path('M120,90C122,88 126,88 129,90C126,91.2 122,91.2 120,90Z', fill=INK)
    d.circle(127, 89.4, 0.7, fill=GOLD)
    d.path('M121,93C123,94 126,94 128,93', stroke=SKIN_SH, stroke_width=0.6, opacity=0.6, fill='none')
    # рот: лёгкая улыбка
    d.path('M129,114.5C131,115 133,114.6 134.4,113.6', stroke='#4A3A30', stroke_width=1, fill='none', stroke_linecap='round')
    # тёплый свет на щеке
    d.ellipse(124, 102, 6, 4, fill=WARM, opacity=0.18)
    # контровой свет по профилю
    d.path('M118,57C128,60 132,70 132,80C132,85 133,88 134,90L140,101C140.5,103 139,105 135,105C135,108 136,110 135,112'
           'C134,114 135,116 134,118C134,124 130,130 122,132', stroke=GOLD, stroke_width=1.3, opacity=0.85, fill='none', stroke_linejoin='round')
    # искры сияния
    sparkle(d, 170, 40, 3, PARCH)
    sparkle(d, 30, 60, 2.2, GOLD)
    return d.render()


def marker():
    d = Doc('0 0 48 48', 'mk')
    glow(d, 24, 24, 24, GOLD, 0.35)
    d.circle(24, 24, 20, fill=d.rad([(0, R2), (1, INK)]))
    d.circle(24, 24, 20, fill='none', stroke=GOLD, stroke_width=2)
    d.circle(24, 24, 17.2, fill='none', stroke=GOLD, stroke_width=0.5, opacity=0.5)
    walker(d, 22.5, 38.5, 0.72, body=PARCH, pack=GOLD, stick=GOLD, sw=1.15, outline=INK, ow=0.8)
    return d.render()

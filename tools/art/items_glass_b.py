#!/usr/bin/env python3
"""Иконки «Путника», вторая партия (v5.3, каталог 22 → 59): витраж «фреска из стекла».

python3 tools/art/items_glass_b.py [--sheet /tmp/items_b_sheet.png] [--big] [--only id,id]

Пишет app/assets/art/items/<id>.svg (64x64) для новых id из docs/v5/items-new-manifest.md
и отсутствовавшего `thermos`, плюс tools/art/items_glass_b_manifest.md. Существующие
иконки (items_glass.py) не трогает: берёт оттуда кабошон G, палитру, геометрию,
проверку и контактный лист. Рисуем в 96-пространстве, G масштабирует в 64.
Дары духов — на «глубоком» фоне: ночь в центре, цвет духа по краю.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import items_glass as IG  # noqa: E402
from items_glass import (G, FAM, BG, LEAD, xf, rot, mv, lerp, bar, lens, ellp,  # noqa: E402
                         ring_seg, teardrop, clipE, check, sheet)
from artlib import clip_convex, clip_circle  # noqa: E402

ROOT = IG.ROOT
ITEMS_DIR = IG.ITEMS_DIR
ITEMS_JSON = os.path.join(ROOT, 'app', 'assets', 'content', 'items.json')
MANIFEST = os.path.join(ROOT, 'tools', 'art', 'items_glass_b_manifest.md')
MAX_BYTES = 8 * 1024

# ---- дополнительные стёкла (только в этом скрипте) ---------------------------
FAM.update({
    'graph':  ('#3A4654', '#7D8B9A'),   # графит
    'swamp':  ('#3E7A3A', '#8CC46E'),   # болотное
    'pearl':  ('#C9DEEA', '#FBFEFF'),   # перламутр с голубым
    'lilac':  ('#B04FB8', '#EBA2F0'),   # кипрей
    'corn':   ('#3F6FE0', '#9DB8FF'),   # василёк
    'leaf':   ('#4FA94E', '#AEE88E'),   # светлая зелень
    'orange': ('#E06A3C', '#FFB27E'),   # морошка (оранжево-коралловая, не жёлтая)
    'peach':  ('#E8957A', '#FFD2C0'),   # светлый коралл
    'gray':   ('#8B939C', '#D7DCE1'),   # серая шерсть
})

# ---- «глубокие» фоны даров: (центр, середина, край) ---------------------------
SPIRIT = {
    'leshy':      ('#1F9E6B', '#8DF5C3'),
    'yaga':       ('#7A55C8', '#C9B2FF'),
    'vodyanoy':   ('#2F6FC0', '#8CC4FF'),
    'domovoy':    ('#C0703A', '#FFC08A'),
    'bannik':     ('#D0506A', '#FF9DB0'),
    'kikimora':   ('#4E8A3A', '#A6E08A'),
    'poludnitsa': ('#3F6FE0', '#A9C2FF'),
    'rusalka':    ('#2BC4BA', '#9FF4EC'),
    'ovinnik':    ('#C8454F', '#FF9C84'),
}
for _k, (_edge, _) in SPIRIT.items():
    BG['sp_' + _k] = ('#1D2C48', '#0B1424', _edge)


def W(g, cx, cy, hh, w, fam, st='r', m=1.35):
    """Капля-осколок (остриё вверх)."""
    g.p(teardrop(cx, cy, hh, w, m, 14), fam, st, stroke_width=0.9)


def small_fish(L, W_, c, a):
    """Рыбка вдоль оси: голова в +x; возвращает (спинка, брюшко, хвост) в мировых координатах."""
    n = 8
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        w = W_ / 2 * math.sin(math.pi * (0.08 + 0.92 * t)) ** 0.7
        x = -L / 2 + L * t
        top.append((x, -w))
        bot.append((x, w * 0.9))
    back = top + [(L / 2, 0), (-L / 2, 0)]
    belly = [(-L / 2, 0), (L / 2, 0)] + bot[::-1]
    tail = [(-L / 2 + 1, 0), (-L / 2 - L * 0.28, -W_ * 0.42), (-L / 2 - L * 0.2, 0), (-L / 2 - L * 0.28, W_ * 0.42)]
    T = lambda ps: rot([(c[0] + x, c[1] + y) for x, y in ps], a, c)
    return T(back), T(belly), T(tail)


# =============================================================================
# СНАРЯЖЕНИЕ
# =============================================================================

def thermos(g):
    # стальной термос с голубой крышкой и каплей: «вода», не «чай»
    g.p([(38, 12), (58, 12), (59, 24), (37, 24)], 'sky', 'v')
    g.p([(35, 24), (61, 24), (61, 30), (35, 30)], 'steelD', 'v')
    g.p([(35, 30), (48, 30), (48, 82), (38, 82), (35, 78)], 'steel', 'h')
    g.p([(48, 30), (61, 30), (61, 78), (58, 82), (48, 82)], 'steelD', 'H')
    g.p([(35, 70), (61, 70), (61, 78), (58, 82), (38, 82), (35, 78)], 'blue', 'v')
    g.p(teardrop(48, 52, 10, 9, 1.35, 16), 'sky', 'r')
    g.hl([(39, 34), (39, 66)], op=0.6, w=1.4)
    g.hl([(41, 15), (41, 21)], op=0.6)
    g.spark(72, 28, 3.6)


def oatmeal(g):
    c = (48, 84)
    sachet = [(36, 26), (60, 26), (62, 78), (34, 78)]
    g.p(rot(sachet, -24, c), 'milk', 'd')
    g.p(rot(sachet, 22, c), 'coral', 'D')
    g.p([(33, 22), (63, 22), (65, 80), (31, 80)], 'turq', 'd')
    g.p([(33, 22), (63, 22), (63.4, 29), (32.6, 29)], 'steelD', 'v')
    # миска с горкой каши и пар
    g.s([(36, 54), (48, 41), (60, 54)], 'milk', 'r')
    g.p(ellp(48, 54, 15, 4, 12, 0, 180) + [(63, 53)], 'blue', 'v')
    g.p([(33, 53), (63, 53), (58, 64), (52, 67), (44, 67), (38, 64)], 'ultra', 'v')
    g.p(lens((46, 40), (43, 30), 4.2, 4), 'milk', 'r', stroke_width=0.9)
    g.p(lens((51, 40), (54, 31), 4.2, 4), 'milk', 'r', stroke_width=0.9)
    g.hl([(36, 33), (37, 50)], op=0.55, w=1.3)
    g.spark(74, 24, 3.4)


def space_blanket(g):
    # конверт плёнки, слегка повёрнут: 4 грани + отогнутый уголок, складки-блики
    R = lambda ps: rot(ps, -12, (48, 50))
    A, B, C, D, O = (18, 30), (78, 30), (78, 70), (18, 70), (50, 48)
    g.p(R([A, B, O]), 'steel', 'v')
    g.p(R([B, C, O]), 'turq', 'D')
    g.p(R([C, D, O]), 'steelD', 'V')
    g.p(R([D, A, O]), 'milk', 'h')
    g.p(R([(78, 70), (64, 70), (78, 57)]), 'night', 'r', stroke_width=1.0)
    g.p(R([(64, 70), (78, 57), (70, 78)]), 'pearl', 'd', stroke_width=1.0)
    g.hl(R([(24, 34), (36, 42), (44, 40)]), op=0.6, w=1.3)
    g.hl(R([(73, 38), (70, 46), (73, 54)]), op=0.8, w=1.4)
    g.hl(R([(24, 62), (32, 56), (30, 50)]), op=0.5, w=1.1)
    g.spark(28, 22, 3.4)
    g.spark(72, 22, 2.4, op=0.7)


def hand_warmers(g):
    pad = [(26, 50), (58, 50), (58, 80), (26, 80)]
    g.p(rot(pad, -16, (42, 65)), 'blue', 'd')
    g.p(rot([(29, 60), (55, 60), (55, 65), (29, 65)], -16, (42, 65)), 'milk', 'v', stroke_width=1.0)
    pad2 = mv(pad, 14, 0)
    g.p(rot(pad2, 12, (56, 65)), 'turq', 'D')
    g.p(rot([(43, 60), (69, 60), (69, 65), (43, 65)], 12, (56, 65)), 'milk', 'v', stroke_width=1.0)
    # тепло: три розовые волны над грелками
    for x in (36, 48, 60):
        g.thread([(x, 44), (x - 4, 37), (x + 1, 30), (x - 3, 23), (x + 1, 16)], 'rose', 2.4, smooth=True)
    g.hl(rot([(29, 70), (29, 78)], -16, (42, 65)), op=0.5)
    g.spark(78, 30, 3.0)
    g.glows.clear()
    g.add_glow(48, 32, 28, FAM['rose'][0], 0.55)


def valdai_bell(g):
    # ушко и лента
    g.p(lens((47, 21), (32, 15), 8, 4), 'blue', 'd')
    g.p(lens((49, 21), (64, 15), 8, 4), 'ultra', 'D')
    g.p(ring_seg(48, 20, 3, 7, 180, 360, 6), 'steel', 'v')
    # купол
    g.p([(48, 25), (40, 27), (35, 34), (33, 48), (30, 62), (24, 70), (48, 70)], 'copper', 'd')
    g.p([(48, 25), (56, 27), (61, 34), (63, 48), (66, 62), (72, 70), (48, 70)], 'rubyD', 'D')
    g.p([(24, 70), (72, 70), (73, 76), (23, 76)], 'steel', 'v')
    g.p([(34, 44), (62, 44), (63, 50), (33, 50)], 'steel', 'v', stroke_width=1.1)
    # язычок
    g.p(bar((48, 74), (48, 80), 3), 'steelD', 'r', stroke_width=0.9)
    g.c(48, 82, 3.8, 'steelD', 'r')
    # звон
    g.thread([(17, 52), (14, 60), (17, 68)], 'milk', 1.6, smooth=True)
    g.thread([(79, 52), (82, 60), (79, 68)], 'milk', 1.6, smooth=True)
    g.hl([(38, 34), (36, 42)], op=0.6, w=1.3)
    g.hl([(36, 54), (33, 64)], op=0.5)
    g.spark(72, 28, 3.2)


def compass_ded(g):
    # откинутая крышка с вмятиной
    g.p([(26, 14), (70, 14), (72, 18), (72, 36), (24, 36), (24, 18)], 'emerD', 'd')
    g.p([(30, 18), (66, 18), (66, 32), (30, 32)], 'emer', 'r', stroke_width=1.1)
    g.hl([(33, 22), (41, 27), (47, 23), (55, 28), (62, 25)], col=LEAD, op=1, w=1.6)
    g.p([(42, 36), (54, 36), (54, 41), (42, 41)], 'steelD', 'v', stroke_width=1.0)
    # ремешок
    g.p([(14, 58), (24, 56), (24, 66), (14, 68)], 'umber', 'h')
    g.p([(72, 56), (82, 58), (82, 68), (72, 66)], 'umberD', 'H')
    # корпус и циферблат
    g.c(48, 61, 24, 'emerD', 'r')
    g.c(48, 61, 18, 'night', 'r')
    for a in (0, 90, 180, 270):
        x, y = 48 + 14.5 * math.cos(math.radians(a - 90)), 61 + 14.5 * math.sin(math.radians(a - 90))
        g.dot(x, y, 1.4, col='#8DF1E9', op=0.9)
    A = -28
    g.p(rot([(48, 45), (52.5, 61), (43.5, 61)], A, (48, 61)), 'ruby', 'v')
    g.p(rot([(48, 77), (52.5, 61), (43.5, 61)], A, (48, 61)), 'milk', 'v')
    g.c(48, 61, 2.6, 'steel', 'r', stroke_width=0.9)
    g.hl([(31, 52), (36, 44), (44, 40)], op=0.55, w=1.2)
    g.spark(76, 40, 3.0)


# =============================================================================
# РЕГИОНАЛЬНЫЕ ПРОДУКТЫ
# =============================================================================

def pozharsky(g):
    g.e(48, 60, 38, 19, 'ice', 'r')
    g.e(48, 60, 29, 13, 'milk', 'r')
    g.s(xf(ellp(36, 54, 15, 10, 10), -12, 1, (36, 54)), 'umber', 'd')
    g.s(xf(ellp(60, 60, 15, 10, 10), 10, 1, (60, 60)), 'copper', 'D')
    for (x, y, fam) in [(31, 50, 'toast'), (39, 54, 'toast'), (34, 58, 'umberD'), (55, 57, 'toast'), (63, 61, 'toast'), (59, 64, 'umber')]:
        g.p([(x - 2, y - 1.4), (x + 1.8, y - 2), (x + 2.2, y + 1.4), (x - 1.4, y + 2)], fam, 'r', stroke_width=0.7)
    g.p(lens((66, 46), (80, 36), 7, 4), 'emer', 'd')
    g.p(lens((68, 46), (76, 30), 6, 4), 'leaf', 'D')
    g.hl([(17, 56), (24, 49)], op=0.6, w=1.3)
    g.spark(24, 32, 3.4)


def tver_pryanik(g):
    x0, y0, x1, y1 = 20, 26, 76, 72
    t = 6.5
    g.p([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'umberD', 'r')
    # глазурная рамка — 4 трапеции
    g.p([(x0 + 3, y0 + 3), (x1 - 3, y0 + 3), (x1 - 3 - t, y0 + 3 + t), (x0 + 3 + t, y0 + 3 + t)], 'turq', 'v')
    g.p([(x1 - 3, y0 + 3), (x1 - 3, y1 - 3), (x1 - 3 - t, y1 - 3 - t), (x1 - 3 - t, y0 + 3 + t)], 'milk', 'H')
    g.p([(x1 - 3, y1 - 3), (x0 + 3, y1 - 3), (x0 + 3 + t, y1 - 3 - t), (x1 - 3 - t, y1 - 3 - t)], 'turq', 'V')
    g.p([(x0 + 3, y1 - 3), (x0 + 3, y0 + 3), (x0 + 3 + t, y0 + 3 + t), (x0 + 3 + t, y1 - 3 - t)], 'milk', 'h')
    g.p([(x0 + 3 + t, y0 + 3 + t), (x1 - 3 - t, y0 + 3 + t), (x1 - 3 - t, y1 - 3 - t), (x0 + 3 + t, y1 - 3 - t)], 'copper', 'r')
    # птица
    # птица: хвост веером, тело, головка с клювом, крыло
    g.p([(38, 52), (29, 44), (28, 52), (30, 60)], 'milk', 'h', stroke_width=1.0)
    g.s([(36, 54), (44, 46), (54, 46), (60, 52), (54, 60), (42, 60)], 'milk', 'r')
    g.c(58, 43, 4.6, 'milk', 'r', stroke_width=1.0)
    g.p([(62, 42), (67, 44), (62, 45)], 'turq', 'r', stroke_width=0.7)
    g.p([(42, 52), (52, 48), (50, 56)], 'turq', 'r', stroke_width=0.9)
    g.dot(59, 42, 0.9, col='#0B1424', op=1)
    g.hl([(23, 30), (73, 30)], op=0.5, w=1.0)
    g.spark(76, 20, 3.2)


def valdai_baranki(g):
    # бечёвка
    g.thread([(48, 14), (34, 32)], 'ruby', 1.8)
    g.thread([(48, 14), (62, 32)], 'ruby', 1.8)
    g.thread([(48, 14), (44, 54)], 'ruby', 1.8)
    g.thread([(48, 14), (54, 54)], 'ruby', 1.8)
    g.c(48, 14, 2.8, 'rubyD', 'r', stroke_width=0.9)
    rings = [(33, 44), (63, 44), (40, 66), (58, 67)]
    fams = [('toast', 'copper'), ('copper', 'toast'), ('toast', 'umber'), ('copper', 'toast')]
    for (x, y), (fa, fb) in zip(rings, fams):
        g.p(ring_seg(x, y, 5.2, 13, 180, 360, 6), fa, 'v')
        g.p(ring_seg(x, y, 5.2, 13, 0, 180, 6), fb, 'V')
    for (x, y) in rings:
        for a in (200, 245, 290, 335):
            g.dot(x + 9 * math.cos(math.radians(a)), y + 9 * math.sin(math.radians(a)), 0.95, col='#FFFBF0', op=0.95)
        g.hl([(x - 11, y + 3), (x - 9, y - 6)], op=0.45, w=1.0)
    g.spark(78, 66, 3.0)


def birch_sap(g):
    g.p([(34, 14), (62, 14), (62, 22), (34, 22)], 'steel', 'v')
    g.p([(36, 22), (60, 22), (60, 27), (36, 27)], 'ice', 'v')
    g.p([(36, 27), (60, 27), (70, 34), (72, 42), (24, 42), (26, 34)], 'ice', 'd')
    g.p([(24, 42), (48, 42), (48, 82), (30, 82), (24, 76)], 'sky', 'd')
    g.p([(48, 42), (72, 42), (72, 76), (66, 82), (48, 82)], 'ice', 'D')
    # берёста
    g.p([(24, 52), (72, 52), (72, 64), (24, 64)], 'milk', 'v')
    g.lines([(30, 55, 37, 55), (44, 60, 52, 60), (58, 56, 66, 56), (34, 61, 39, 61), (62, 61, 68, 61)], col=LEAD, op=1, w=1.5)
    g.hl([(28, 44), (28, 50)], op=0.7, w=1.4)
    g.hl([(28, 67), (28, 77)], op=0.6, w=1.4)
    g.spark(74, 26, 3.4)


def dried_fish(g):
    # газета
    g.p([(14, 40), (78, 30), (84, 70), (20, 82)], 'milk', 'v')
    g.lines([(20, 47, 40, 44), (21, 53, 36, 51), (24, 74, 44, 70), (60, 70, 78, 66), (58, 38, 74, 35), (25, 79, 36, 77)],
            col='#7F97AD', op=0.9, w=1.4)
    # лещ: высокое тело, хвост вверх-вправо
    c, a = (44, 60), -45
    T = lambda ps: rot([(c[0] + x, c[1] + y) for x, y in ps], a, c)
    g.p(T([(22, 0), (34, -11), (31, 0), (34, 11)]), 'umberD', 'd')
    g.p(T([(-2, -15), (6, -24), (14, -12)]), 'umber', 'r', stroke_width=1.0)
    top = ellp(0, 0, 24, 15, 12, 180, 360)
    bot = ellp(0, 0, 24, 13, 12, 0, 180)
    g.p(T(top), 'umber', 'd')
    g.p(T(bot), 'steel', 'D')
    g.p(T([(-24, 0), (-21, -7), (-14, -12), (-12, 0), (-14, 10), (-21, 6)]), 'steelD', 'r')
    ex, ey = T([(-18, -3)])[0]
    g.c(ex, ey, 2.3, 'milk', 'r', stroke_width=0.8)
    g.dot(ex, ey, 0.9, col='#0B1424', op=1)
    g.hl(T([(-6, -10), (10, -10)]), op=0.55)
    g.hl(T([(-4, 6), (12, 6)]), op=0.5, w=1.0)
    g.spark(74, 20, 3.2)


def ryapushka(g):
    # дымок
    g.s([(28, 24), (36, 16), (46, 20), (54, 14), (64, 20), (58, 27), (46, 26), (36, 30)], 'viol', 'r')
    for i, (cx, cy) in enumerate([(50, 44), (46, 58), (52, 72)]):
        back, belly, tail = small_fish(44, 13, (cx, cy), 180 - 14)
        g.p(tail, 'umberD', 'r')
        g.p(back, ('copper', 'umber', 'copper')[i], 'd')
        g.p(belly, 'milk', 'v')
        hx, hy = rot([(cx + 16, cy - 1.5)], 180 - 14, (cx, cy))[0]
        g.dot(hx, hy, 1.4, col='#0B1424', op=1)
    g.hl([(32, 19), (40, 16)], op=0.5, w=1.0)
    g.spark(80, 56, 3.0)


def _kalitka(g, filling):
    c, a = (48, 52), -10

    def oval(rx, ry, crimp=0.0, n=40):
        out = []
        for i in range(n):
            t = 2 * math.pi * i / n
            # лодочка: концы острее, края волной
            k = 1 + crimp * math.cos(14 * t)
            x = rx * math.cos(t) * k
            y = ry * math.sin(t) * k * (0.78 + 0.22 * math.sin(t) ** 2)
            out.append((c[0] + x, c[1] + y))
        return rot(out, a, c)
    outer = oval(37, 22, 0.05, 56)
    g.p(outer[:28] + [c], 'umber', 'd')
    g.p(outer[28:] + outer[:1] + [c], 'umberD', 'D')
    inner = oval(25, 13)
    filling(g, inner, c, a)
    g.hl(rot([(16, 46), (24, 37), (36, 33)], a, c), op=0.55, w=1.2)


def kalitka_potato(g):
    def fill(g, inner, c, a):
        g.p(inner, 'milk', 'r')
        g.s(rot([(46, 47), (55, 46), (58, 52), (50, 56), (43, 53)], a, c), 'coral', 'r')
        g.hl(rot([(30, 54), (40, 58)], a, c), op=0.5, w=1.0, col='#FFFFFF')
    _kalitka(g, fill)
    g.spark(76, 24, 3.4)


def kalitka_millet(g):
    def fill(g, inner, c, a):
        g.p(inner, 'peach', 'r')
        k = 0
        for row, (yy, xs) in enumerate([(46, (34, 41, 48, 55, 62)), (52, (30, 37, 44, 51, 58, 65)), (58, (36, 43, 50, 57))]):
            for xx in xs:
                p = rot([(xx, yy)], a, c)[0]
                g.c(p[0], p[1], 2.7, ('coral', 'peach', 'orange')[k % 3], 'r', stroke_width=0.8)
                k += 1
    _kalitka(g, fill)
    g.spark(76, 24, 3.4)


def kalitka_berry(g):
    def fill(g, inner, c, a):
        g.p(inner, 'viol', 'r')
        for i, (xx, yy, r) in enumerate([(34, 50, 4.6), (44, 46, 4.8), (54, 47, 4.4), (63, 51, 4.2), (39, 57, 4.4), (50, 56, 5), (60, 58, 4)]):
            p = rot([(xx, yy)], a, c)[0]
            g.c(p[0], p[1], r, ('ultra', 'blue', 'corn')[i % 3], 'r', stroke_width=1.0)
            g.dot(p[0] - r * 0.35, p[1] - r * 0.35, 0.9, op=0.75)
    _kalitka(g, fill)
    # потёки сока по краю
    g.p(rot([(30, 66), (34, 66), (33, 74), (31, 74)], -10, (48, 52)), 'viol', 'v', stroke_width=1.0)
    g.p(rot([(58, 69), (62, 68), (61, 78), (59, 78)], -10, (48, 52)), 'viol', 'v', stroke_width=1.0)
    g.spark(76, 24, 3.4)


def rybnik(g):
    # голова и хвост рыбы
    g.p([(14, 54), (22, 44), (30, 46), (30, 62), (22, 63)], 'steel', 'd')
    g.p([(66, 52), (82, 40), (86, 46), (80, 55), (86, 64), (82, 69), (66, 58)], 'steelD', 'D')
    # пирог
    g.p(ellp(48, 55, 24, 18, 14, 180, 360) + [(72, 56)], 'toast', 'v')
    g.p(ellp(48, 55, 24, 18, 14, 0, 180), 'umber', 'V')
    g.p(lens((34, 46), (62, 46), 9, 6), 'umberD', 'r')
    g.p(lens((38, 46), (58, 46), 4, 4), 'steel', 'r', stroke_width=0.9)
    g.c(20, 51, 2.0, 'milk', 'r', stroke_width=0.7)
    g.hl([(29, 42), (38, 38), (50, 37)], op=0.6, w=1.2)
    g.hl([(34, 64), (46, 68)], op=0.4, w=1.0)
    g.spark(74, 26, 3.4)


def lingon_mors(g):
    # бутылка прозрачного стекла с рубиновым морсом
    g.p([(42, 13), (54, 13), (54, 30), (42, 30)], 'ice', 'h')
    g.p([(42, 30), (54, 30), (64, 38), (66, 46), (30, 46), (32, 38)], 'ice', 'd')
    g.p([(30, 46), (48, 46), (48, 82), (35, 82), (30, 77)], 'ruby', 'd')
    g.p([(48, 46), (66, 46), (66, 77), (61, 82), (48, 82)], 'rubyD', 'D')
    # веточка брусники на горлышке
    g.p(lens((54, 24), (70, 18), 7, 4), 'emer', 'd')
    g.p(lens((54, 26), (68, 32), 6.4, 4), 'emerD', 'D')
    g.c(62, 26, 3.4, 'ruby', 'r', stroke_width=1.0)
    g.c(68, 25, 3.0, 'rose', 'r', stroke_width=1.0)
    g.c(65, 30.5, 2.8, 'ruby', 'r', stroke_width=1.0)
    g.hl([(34, 50), (34, 74)], op=0.6, w=1.4)
    g.hl([(45, 16), (45, 27)], op=0.6, w=1.0)
    g.spark(24, 30, 3.4)


def cloudberry(g):
    # банка
    g.p([(30, 46), (48, 46), (48, 80), (34, 80), (30, 76)], 'ice', 'd')
    g.p([(48, 46), (66, 46), (66, 76), (62, 80), (48, 80)], 'ice', 'D')
    g.p([(31, 56), (65, 56), (65, 75), (61, 78), (35, 78), (31, 75)], 'orange', 'r')
    # ткань-крышка
    g.p([(25, 40), (71, 40), (68, 52), (62, 49), (56, 54), (48, 50), (40, 54), (34, 49), (28, 52)], 'turq', 'v')
    g.thread([(30, 46), (66, 46)], 'ruby', 1.4)
    # горка ягод: многодольные (зёрна)
    for (bx, by) in [(36, 32), (60, 32), (48, 25)]:
        for (dx, dy) in [(0, 0), (-4.4, 1), (4.4, 1), (-2.4, -3.8), (2.4, -3.8), (-2.4, 4.4), (2.4, 4.4)]:
            g.c(bx + dx, by + dy, 2.6, 'orange' if (dx + dy) % 2 else 'peach', 'r', stroke_width=0.7)
    g.hl([(34, 60), (34, 72)], op=0.5, w=1.2)
    g.spark(76, 64, 3.0)


def ivan_chai(g):
    # кипрей
    g.thread([(26, 82), (26, 22)], 'emerD', 2.2)
    g.p(lens((26, 60), (16, 52), 5, 4), 'emer', 'd', stroke_width=0.9)
    for i, (y, side) in enumerate([(22, 0), (28, -1), (33, 1), (39, -1), (45, 1)]):
        x = 26 + side * 4.5
        g.e(x, y, 3.8 - i * 0.2, 3.0, 'lilac' if i % 2 == 0 else 'rose', 'r', stroke_width=0.9)
    # кружка
    g.thread([(70, 52), (80, 55), (80, 66), (70, 70)], 'blue', 3.2)
    g.p([(36, 46), (53, 46), (53, 80), (40, 80), (36, 76)], 'blue', 'd')
    g.p([(53, 46), (70, 46), (70, 76), (66, 80), (53, 80)], 'ultra', 'D')
    g.e(53, 46, 17, 4.6, 'milk', 'r')
    g.e(53, 46.5, 13.5, 3.0, 'rubyD', 'r', stroke_width=1.0)
    # пар
    g.p(lens((48, 40), (45, 28), 4.4, 4), 'milk', 'r', stroke_width=0.9)
    g.p(lens((58, 40), (62, 27), 4.4, 4), 'milk', 'r', stroke_width=0.9)
    g.hl([(40, 52), (40, 74)], op=0.5, w=1.3)
    g.spark(76, 28, 3.2)


def cod(g):
    # гребень волны снизу
    g.s([(4, 72), (22, 64), (40, 70), (58, 62), (76, 68), (96, 62), (96, 98), (4, 98)], 'blue', 'v', clip=True)
    g.s([(14, 70), (24, 66), (30, 70), (26, 74)], 'ice', 'r', stroke_width=0.9)
    # ломоть трески: пласты
    body = [(18, 48), (30, 30), (52, 24), (74, 30), (80, 44), (72, 60), (50, 66), (26, 62)]
    A = [(18, 48), (30, 30), (40, 27), (38, 64), (26, 62)]
    B = [(40, 27), (52, 24), (58, 25), (56, 66), (38, 64)]
    Cc = [(58, 25), (74, 30), (76, 36), (70, 60), (56, 66)]
    g.p(A, 'milk', 'd')
    g.p(B, 'pearl', 'v')
    g.p(Cc, 'milk', 'D')
    # кожа сбоку
    g.p([(74, 30), (80, 44), (72, 60), (66, 63), (70, 60), (76, 36)], 'copper', 'D')
    g.p([(76, 36), (82, 44), (75, 58), (70, 60)], 'copper', 'd')
    g.hl([(24, 46), (32, 34)], op=0.5, w=1.2)
    g.hl([(44, 32), (43, 56)], col='#C9DEEA', op=0.9, w=1.0)
    g.spark(24, 24, 3.4)


def reindeer_tongue(g):
    # низкая широкая банка
    g.p([(20, 38), (76, 38), (76, 46), (20, 46)], 'steel', 'v')
    g.p([(20, 46), (76, 46), (76, 70), (20, 70)], 'blue', 'd')
    g.p([(20, 70), (76, 70), (76, 76), (70, 80), (26, 80), (20, 76)], 'steelD', 'v')
    g.e(48, 38, 28, 7, 'steel', 'r')
    g.e(48, 38, 18, 3.6, 'steelD', 'D')
    # молочные рога
    for s in (-1, 1):
        g.thread([(48 + s * 2, 66), (48 + s * 8, 58), (48 + s * 12, 50)], 'milk', 2.2, smooth=True)
        g.thread([(48 + s * 7, 60), (48 + s * 16, 58)], 'milk', 1.8)
        g.thread([(48 + s * 10, 54), (48 + s * 17, 51)], 'milk', 1.6)
    g.hl([(24, 50), (24, 66)], op=0.5, w=1.3)
    g.spark(76, 24, 3.4)


# =============================================================================
# ДАРЫ ДУХОВ
# =============================================================================

def twig_leshy(g):
    # рогатка: ствол и две ветви вверх-вправо
    g.p(bar((28, 82), (42, 54), 9, 8), 'umberD', 'd')
    g.p(bar((42, 54), (40, 24), 7.5, 5), 'umber', 'd')
    g.p(bar((42, 54), (70, 36), 7.5, 5), 'umber', 'D')
    # мох
    for (x, y, fam) in [(36, 56, 'emer'), (46, 52, 'emerD'), (41, 61, 'emer')]:
        g.c(x, y, 3.4, fam, 'r', stroke_width=0.9)
    # бирюзовый след-стрелка
    g.thread([(48, 46), (58, 38), (68, 24), (76, 18)], 'turq', 1.8, smooth=True)
    g.p([(80, 13), (78, 24), (70, 18)], 'turq', 'r', stroke_width=0.9)
    g.hl([(31, 76), (39, 58)], op=0.5, w=1.2)
    g.spark(26, 30, 3.2, col='#EFFFF6')


def spruce_leshy(g):
    a = -40
    c = (48, 50)
    R = lambda ps: rot(ps, a, c)
    g.thread(R([(48, 82), (48, 14)]), 'umber', 2.6)
    for i, y in enumerate([24, 34, 44, 54, 64]):
        L = 15 - i * 0.6 if i else 12
        g.p(R(lens((48, y + 6), (48 - L, y - 4), 6.2, 4)), 'emer' if i % 2 else 'emerD', 'd', stroke_width=1.1)
        g.p(R(lens((48, y + 6), (48 + L, y - 4), 6.2, 4)), 'emerD' if i % 2 else 'emer', 'D', stroke_width=1.1)
    g.p(R(lens((48, 22), (48, 8), 6, 4)), 'leaf', 'r', stroke_width=1.1)
    # перевязка
    for dy in (0, 4):
        g.p(R(bar((43, 72 + dy), (53, 70 + dy), 2.8)), 'ruby', 'r', stroke_width=0.9)
    g.spark(72, 72, 3.2, col='#EFFFF6')


def thread_yaga(g):
    g.c(48, 50, 28, 'milk', 'r')
    pts_ = []
    for i in range(41):
        t = 2 * math.pi * i / 40
        pts_.append((48 + 21 * math.sin(t), 50 + 11 * math.sin(2 * t)))
    pts_ = rot(pts_, -28, (48, 50))
    g.thread(pts_[:21], 'viol', 3.2)
    g.thread(pts_[20:38], 'rose', 3.2)
    end = pts_[37]
    g.thread([end, (end[0] + 6, end[1] + 10), (end[0] + 2, end[1] + 20), (end[0] + 8, end[1] + 27)], 'rose', 2.4, smooth=True)
    for q in (pts_[10], pts_[30]):
        g.c(q[0], q[1], 3.0, 'rubyD', 'r', stroke_width=0.9)
    g.hl([(26, 40), (32, 30)], op=0.5, w=1.2)
    g.spark(76, 26, 3.2)


def shell_vodyanoy(g):
    # перловица: вытянутый овал, полосы роста — эллипсы, сходящиеся к макушке
    u = (34, 40)
    a = -14
    bands = [(1.0, 'blue', 'd'), (0.84, 'pearl', 'r'), (0.78, 'ultra', 'D'), (0.58, 'turq', 'r'), (0.52, 'blue', 'd'), (0.3, 'pearl', 'r')]
    for k, fam, st in bands:
        cx, cy = u[0] + (50 - u[0]) * k, u[1] + (54 - u[1]) * k
        g.p(rot(ellp(cx, cy, 30 * k, 18 * k, 22), a, (50, 54)), fam, st, stroke_width=1.1)
    g.hl(rot([(26, 58), (30, 46), (40, 40)], a, (50, 54)), op=0.6, w=1.2)
    for (x, y, s) in [(20, 28, 1.0), (78, 30, 0.85), (78, 76, 0.75)]:
        g.p([(x, y - 6 * s), (x + 3.8 * s, y + 1.5 * s), (x, y + 4.6 * s), (x - 3.8 * s, y + 1.5 * s)], 'sky', 'r', stroke_width=0.9)


def hook_vodyanoy(g):
    # леска петлёй
    g.thread([(56, 20), (62, 10), (70, 14), (66, 22), (56, 20)], 'turq', 1.8, smooth=True)
    # ушко
    g.p(ring_seg(54, 22, 2.6, 6, 0, 360, 10)[:11] + ring_seg(54, 22, 2.6, 6, 0, 360, 10)[11:], 'steel', 'r', stroke_width=1.0)
    # цевьё и изгиб
    g.p(bar((54, 27), (54, 58), 7), 'copper', 'h')
    g.p(ring_seg(42, 58, 8.5, 15.5, 0, 90, 6), 'copper', 'V')
    g.p(ring_seg(42, 58, 8.5, 15.5, 90, 180, 6), 'ruby', 'd')
    # остриё с бородкой
    g.p([(26.5, 58), (33.5, 58), (34, 44), (30, 34), (27, 46), (24, 47)], 'ruby', 'D')
    # волны
    g.thread([(18, 80), (26, 75), (34, 80), (42, 75), (50, 80)], 'blue', 2.4, smooth=True)
    g.thread([(46, 84), (54, 79), (62, 84), (70, 79), (78, 84)], 'sky', 2.4, smooth=True)
    g.hl([(52, 32), (52, 54)], op=0.65, w=1.3)
    g.spark(76, 40, 3.0)


def ember_domovoy(g):
    # крышка откинута назад
    g.p(xf(ellp(48, 36, 20, 5, 16), -16, 1, (48, 36)), 'steelD', 'r')
    # жар внутри
    g.e(48, 48, 18, 5, 'night', 'r')
    for (x, y, r, fam) in [(40, 48, 5, 'ruby'), (49, 46, 5.6, 'rose'), (57, 48.5, 4.4, 'rubyD')]:
        g.c(x, y, r, fam, 'r', stroke_width=1.0)
    # банка
    g.p([(30, 48), (48, 52), (48, 78), (32, 76)], 'steel', 'h')
    g.p([(48, 52), (66, 48), (64, 76), (48, 78)], 'steelD', 'H')
    g.p([(30, 48), (48, 52), (66, 48), (66, 53), (48, 57), (30, 53)], 'graph', 'v')
    # искра
    g.p([(52, 18), (55, 24), (52, 30), (49, 24)], 'amber', 'r', stroke_width=0.9)
    g.hl([(34, 58), (35, 72)], op=0.5, w=1.2)
    g.glows.clear()
    g.add_glow(48, 40, 28, FAM['ruby'][0], 0.6)
    g.add_glow(52, 24, 12, FAM['amber'][0], 0.6)
    g.spark(24, 30, 2.8, op=0.7)


def lapot_domovoy(g):
    # лапоть в профиль: носок вправо, задник слева
    shoe = [(16, 60), (18, 50), (26, 47), (40, 50), (56, 50), (70, 47), (80, 50), (84, 58), (80, 68), (64, 72), (40, 72), (22, 70)]
    # клетки лыка: ромбы по диагонали, обрезанные по силуэту лаптя
    cells = []
    for i in range(-6, 7):
        for j in range(-4, 5):
            cx_, cy_ = 48 + (i - j) * 6.4, 60 + (i + j) * 6.4
            cell = [(cx_, cy_ - 6.4), (cx_ + 6.4, cy_), (cx_, cy_ + 6.4), (cx_ - 6.4, cy_)]
            q = _clip_poly(shoe, cell)
            if len(q) >= 3:
                cells.append((q, ('toast', 'milk')[(i + j) % 2]))
    for q, fam in cells:
        g.p(q, fam, 'r', stroke_width=1.0)
    # проём с домовым
    g.e(46, 50, 20, 6, 'night', 'r')
    g.s([(36, 50), (40, 40), (48, 36), (56, 40), (58, 50)], 'umberD', 'r')
    g.c(43, 44, 2.0, 'turq', 'r', stroke_width=0.8)
    g.c(52, 44, 2.0, 'turq', 'r', stroke_width=0.8)
    g.dot(43.6, 43.4, 0.7, op=0.9)
    g.dot(52.6, 43.4, 0.7, op=0.9)
    g.s([(40, 49), (47.5, 46), (55, 49), (50, 56), (45, 56)], 'gray', 'v', stroke_width=1.0)
    g.glows.clear()
    g.add_glow(48, 48, 30, '#FFC08A', 0.35)
    g.spark(76, 30, 3.0)


def _clip_poly(subject, cell):
    """Пересечение произвольного многоугольника с выпуклой ячейкой (ориентацию подбираем)."""
    q = clip_convex(subject, cell)
    if len(q) < 3:
        q = clip_convex(subject, cell[::-1])
    return q


def venik_bannik(g):
    c = (40, 62)
    # пар
    g.thread([(66, 26), (62, 18), (68, 12), (64, 6)], 'milk', 2.2, smooth=True)
    g.thread([(76, 34), (73, 26), (78, 20)], 'milk', 1.8, smooth=True)
    # листья веером
    leaves = [(-75, 'emer', 28), (-58, 'leaf', 32), (-42, 'emerD', 33), (-26, 'emer', 32), (-10, 'leaf', 28), (-90, 'emerD', 24), (5, 'emerD', 22)]
    for ang, fam, L in leaves:
        a = math.radians(ang)
        p0 = (c[0] + 8 * math.cos(a), c[1] + 8 * math.sin(a))
        p1 = (c[0] + L * math.cos(a), c[1] + L * math.sin(a))
        g.p(lens(p0, p1, 11, 6), fam, 'd')
    # рукоять и нитка
    g.p(bar((22, 82), (40, 62), 9, 8), 'umber', 'd')
    g.p(bar((27, 72), (34, 79), 3), 'ruby', 'r', stroke_width=0.9)
    g.p(bar((31, 68), (38, 75), 3), 'ruby', 'r', stroke_width=0.9)
    g.spark(22, 34, 3.0)
    g.hl([(52, 46), (60, 40)], op=0.4, w=1.0)


def stone_bannik(g):
    g.thread([(36, 30), (32, 22), (38, 16), (34, 9)], 'milk', 2.2, smooth=True)
    g.thread([(58, 30), (62, 22), (56, 16), (60, 10)], 'milk', 2.2, smooth=True)
    left = [(16, 62), (22, 44), (36, 36), (46, 36), (44, 46), (50, 54), (44, 64), (48, 76), (30, 76), (19, 72)]
    right = [(46, 36), (60, 36), (74, 42), (82, 56), (78, 70), (64, 77), (48, 76), (52, 66), (46, 58), (52, 50), (49, 44)]
    g.p(left, 'graph', 'd')
    g.p(right, 'steelD', 'D')
    # трещина с жаром
    crack = [(46, 36), (49, 44), (52, 50), (46, 58), (52, 66), (48, 76), (44, 64), (50, 54), (44, 46)]
    g.p(crack, 'rose', 'r', stroke_width=1.0)
    g.hl([(22, 52), (28, 44), (36, 40)], op=0.5, w=1.2)
    g.glows.clear()
    g.add_glow(48, 56, 24, FAM['rose'][0], 0.6)
    g.spark(76, 30, 3.0)


def bead_kikimora(g):
    g.thread([(10, 60), (28, 54)], 'milk', 1.8)
    g.thread([(68, 42), (86, 36)], 'milk', 1.8)
    g.c(48, 48, 22, 'swamp', 'r')
    g.s([(48, 38), (55, 47), (48, 58), (41, 47)], 'turq', 'r', stroke_width=1.0)
    g.c(48, 48, 3, 'ice', 'r', stroke_width=0.8)
    g.hl([(31, 44), (35, 35), (43, 29)], op=0.7, w=1.4)
    for (x, y, r) in [(20, 30, 4.4), (76, 66, 3.8), (26, 74, 3.4)]:
        g.p([(x, y - r), (x + r * 0.55, y), (x, y + r), (x - r * 0.55, y)], 'viol', 'r', stroke_width=0.8)
    g.glows.clear()
    g.add_glow(48, 48, 32, '#7FFFE0', 0.5)
    g.spark(60, 34, 2.6)


def kudel_kikimora(g):
    # кудель: вытянутый пушистый пучок прядей, справа сужается в нить
    fams = ['milk', 'gray', 'pearl', 'steel', 'milk', 'gray', 'pearl']
    for i in range(7):
        y0 = 34 + i * 5.2
        p0 = (16 + (i % 2) * 4, y0 + (i - 3) * 1.8)
        p1 = (66, 52 + (i - 3) * 1.2)
        g.p(lens(p0, p1, 11 - abs(i - 3) * 1.2, 6), fams[i], 'd' if i % 2 else 'D')
    g.p(lens((20, 46), (58, 50), 7, 6), 'pearl', 'r')
    g.thread([(64, 52), (70, 56), (74, 52), (78, 58), (82, 54)], 'milk', 2.6, smooth=True)
    g.hl([(22, 38), (40, 40)], op=0.5, w=1.0)
    g.hl([(24, 60), (44, 58)], op=0.4, w=1.0)
    g.spark(72, 28, 3.0)


def ear_poludnitsa(g):
    # стебель
    g.thread([(48, 82), (48, 30)], 'peach', 2.2)
    # косичка: пары зёрен, наклонённые в разные стороны
    for i, y in enumerate([30, 38, 46, 54, 62]):
        s = 1 if i % 2 else -1
        g.p(lens((48, y + 6), (48 + s * 9, y - 4), 7.4, 4), 'milk' if i % 2 else 'peach', 'r', stroke_width=1.1)
        g.p(lens((48, y + 6), (48 - s * 8, y - 2), 7.0, 4), 'peach' if i % 2 else 'milk', 'r', stroke_width=1.1)
    g.p(lens((48, 28), (48, 16), 6.4, 4), 'milk', 'r', stroke_width=1.1)
    # ость
    g.lines([(42, 26, 36, 10), (54, 26, 60, 10), (48, 18, 48, 6), (38, 36, 28, 22), (58, 36, 68, 22)], col='#FBB6A2', op=0.85, w=1.0)
    # василёк у основания
    cx, cy = 60, 74
    for k in range(6):
        a = math.radians(k * 60 + 15)
        g.p(lens((cx, cy), (cx + 9 * math.cos(a), cy + 9 * math.sin(a)), 4.6, 4), 'corn', 'r', stroke_width=0.9)
    g.c(cx, cy, 2.6, 'viol', 'r', stroke_width=0.8)
    g.spark(26, 60, 3.0)


def wreath_poludnitsa(g):
    R = 24
    g.p(ring_seg(48, 48, R - 5, R + 5, 0, 180, 12), 'emerD', 'v')
    g.p(ring_seg(48, 48, R - 5, R + 5, 180, 360, 12), 'emerD', 'V')
    for k in range(6):
        la = math.radians(k * 60 + 30)
        lx, ly = 48 + R * math.cos(la), 48 + R * math.sin(la)
        t = (-math.sin(la), math.cos(la))
        g.p(lens((lx - t[0] * 7, ly - t[1] * 7), (lx + t[0] * 7, ly + t[1] * 7), 6.4, 4), 'emer', 'd', stroke_width=1.0)
    for k in range(6):
        a = math.radians(k * 60)
        fx, fy = 48 + R * math.cos(a), 48 + R * math.sin(a)
        star = []
        for j in range(14):
            b = math.radians(j * 360 / 14 + k * 11)
            r = 10 if j % 2 == 0 else 5
            star.append((fx + r * math.cos(b), fy + r * math.sin(b)))
        g.p(star, 'corn' if k % 2 else 'ultra', 'r', stroke_width=1.0)
        g.c(fx, fy, 2.6, 'viol', 'r', stroke_width=0.8)
    g.spark(48, 48, 3.6, op=0.8)


def ribbon_rusalka(g):
    # лента волной «S»: гладкие края, 4 стекла (свет/тень перекрута), косые концы
    def P(t):
        return (22 + 52 * t, 50 - 20 * math.sin(2 * math.pi * t))
    hw = 7.5
    N = 32
    L_, R_ = [], []
    for i in range(N + 1):
        t = 0.03 + 0.94 * i / N
        x, y = P(t)
        x2, y2 = P(t + 0.005)
        d = math.hypot(x2 - x, y2 - y)
        nx, ny = -(y2 - y) / d, (x2 - x) / d
        L_.append((x + nx * hw, y + ny * hw))
        R_.append((x - nx * hw, y - ny * hw))
    L_[0] = (L_[0][0] - 3, L_[0][1] + 7)
    R_[-1] = (R_[-1][0] + 3, R_[-1][1] - 7)
    cuts = [0, 8, 16, 24, 32]
    for k in range(4):
        a, b = cuts[k], cuts[k + 1]
        g.p(L_[a:b + 1] + R_[a:b + 1][::-1], ('emer', 'emerD', 'emer', 'emerD')[k], ('d', 'D', 'd', 'D')[k])
    zz = []
    for i in range(37):
        t = 0.06 + 0.88 * i / 36
        x, y = P(t)
        x2, y2 = P(t + 0.005)
        d = math.hypot(x2 - x, y2 - y)
        nx, ny = -(y2 - y) / d, (x2 - x) / d
        sft = 2.2 if i % 2 else -2.2
        zz.append((x + nx * sft, y + ny * sft))
    g.hl(zz[:19], col='#8DF1E9', op=0.95, w=1.3)
    g.hl(zz[18:], col='#FFFBF0', op=0.9, w=1.3)
    g.spark(76, 76, 3.0)
    g.spark(22, 24, 2.6, op=0.7)


def pearl_rusalka(g):
    # раскрытая створка-веер
    cx, cy = 48, 70
    k = 6
    for i in range(k):
        a0 = 180 + i * 180 / k
        g.p(ring_seg(cx, cy, 6, 32, a0, a0 + 180 / k, 3), ('blue', 'ultra', 'night')[i % 3] if i % 3 != 2 else 'blue', 'r' if i % 2 else 'D')
    g.p(ring_seg(cx, cy, 0.01, 6, 180, 360, 6)[:7] + [(cx, cy)], 'night', 'r')
    g.p([(16, 70), (80, 70), (74, 78), (22, 78)], 'night', 'v')
    # жемчужина
    g.c(48, 54, 15, 'pearl', 'r')
    g.dot(42, 48, 3.4, op=0.85)
    g.hl([(37, 58), (40, 64)], col='#B0E1FB', op=0.8, w=1.4)
    g.glows.clear()
    g.add_glow(48, 54, 28, '#CFF6FF', 0.5)
    g.spark(72, 28, 3.2)


def key_ovinnik(g):
    a = 40
    c = (48, 48)
    R = lambda ps: rot(ps, a, c)
    # свечение из бородки
    bx, by = R([(80, 50)])[0]
    g.glows.clear()
    g.add_glow(bx, by, 22, FAM['rose'][0], 0.65)
    g.add_glow(bx, by, 11, FAM['amber'][0], 0.6)
    # кольцо-ушко
    rc = R([(20, 48)])[0]
    g.p(ring_seg(rc[0], rc[1], 5.5, 12, 0, 180, 8), 'steel', 'v')
    g.p(ring_seg(rc[0], rc[1], 5.5, 12, 180, 360, 8), 'steelD', 'V')
    # стержень
    g.p(R([(32, 45), (78, 45), (78, 51), (32, 51)]), 'steel', 'v')
    g.p(R([(32, 43), (36, 43), (36, 53), (32, 53)]), 'steelD', 'r', stroke_width=1.0)
    # бородка
    g.p(R([(64, 51), (78, 51), (78, 64), (73, 64), (73, 58), (69, 58), (69, 64), (64, 64)]), 'steelD', 'd')
    # язычки невидимого огня
    for (dx, dy, fam, s) in [(70, 70, 'rose', 1.0), (78, 68, 'amber', 0.75)]:
        x, y = R([(dx, dy)])[0]
        g.p(teardrop(x, y, 5.4 * s, 4 * s, 1.35, 12), fam, 'r', stroke_width=0.9)
    g.hl(R([(40, 46.5), (60, 46.5)]), op=0.6, w=1.2)
    g.spark(76, 26, 3.0)


def sheaf_ovinnik(g):
    g.glows.clear()
    g.add_glow(48, 76, 26, FAM['ruby'][0], 0.6)
    c = (48, 56)
    # нижние стебли расходятся вниз
    for i, x in enumerate([30, 38, 46, 54, 62]):
        g.p([(c[0] - 6 + i * 3, c[1]), (c[0] - 3 + i * 3, c[1]), (x + 4, 82), (x - 2, 82)], ('toast', 'milk')[i % 2], 'v')
    # верхние стебли и колосья
    for i, ang in enumerate([-122, -106, -90, -74, -58]):
        a = math.radians(ang)
        p0 = (c[0] - 6 + i * 3, c[1])
        p1 = (c[0] + 26 * math.cos(a), c[1] + 26 * math.sin(a))
        g.p(bar(p0, p1, 3.4, 4.2), ('milk', 'toast')[i % 2], 'v', stroke_width=1.0)
        p2 = (c[0] + 38 * math.cos(a), c[1] + 38 * math.sin(a))
        g.p(lens(p1, p2, 6.6, 4), ('toast', 'peach')[i % 2], 'r', stroke_width=1.0)
    # жгут
    g.p([(34, 52), (62, 52), (62, 60), (34, 60)], 'umber', 'v')
    g.lines([(40, 52, 37, 60), (47, 52, 44, 60), (54, 52, 51, 60), (61, 52, 58, 60)], col=LEAD, op=1, w=1.0)
    g.spark(76, 30, 3.0)


# =============================================================================
# РЕЕСТР: (id, kind, builder, bg, seed, подсветка | None, что нарисовано)
# =============================================================================
def sg(sp):
    return (48, 50, 34, SPIRIT[sp][1], 0.45)


ICONS = [
    ('thermos', 'gear', thermos, 'sea', 31, (48, 52, 34, '#7ACBFF', 0.45), 'Термос воды: стальной корпус, голубая крышка, голубая капля, синий низ'),
    ('oatmeal', 'food', oatmeal, 'violet', 32, (48, 52, 34, '#B7A6FF', 0.4), 'Овсянка-минутка: три пакетика веером (молочный, коралловый, бирюзовый), миска с горкой каши и пар'),
    ('space_blanket', 'gear', space_blanket, 'indigo', 33, (48, 50, 34, '#9AA8FF', 0.45), 'Спасательное одеяло: конверт из 4 граней (сталь, молоко, бирюза), отогнутый уголок'),
    ('hand_warmers', 'gear', hand_warmers, 'violet', 34, None, 'Грелки для рук: синий и бирюзовый пакетики внахлёст с молочными полосками, розовое облачко тепла'),
    ('valdai_bell', 'gear', valdai_bell, 'teal', 35, (48, 50, 34, '#7FE3D8', 0.45), 'Валдайский колокольчик: медно-рубиновый купол, стальной пояс и язычок, синий бант, молочные дуги звона'),
    ('compass_ded', 'quest', compass_ded, 'slate', 36, (48, 56, 34, '#9FD8E8', 0.4), 'Дедов компас: открытая тёмно-зелёная крышка с кривым швом-вмятиной, ночной циферблат, стрелка рубин/молоко, ремешок'),
    ('pozharsky', 'food', pozharsky, 'indigo', 37, (48, 56, 34, '#9AA8FF', 0.4), 'Пожарские котлеты: две котлеты в панировке на молочной тарелке, веточка зелени'),
    ('tver_pryanik', 'food', tver_pryanik, 'emerald', 38, (48, 50, 34, '#8DF5C3', 0.4), 'Печатный пряник: коричневый, глазурная рамка бирюза/молоко, молочная птица в центре'),
    ('valdai_baranki', 'food', valdai_baranki, 'violet', 39, (48, 52, 34, '#B7A6FF', 0.4), 'Валдайские баранки: 4 кольца на рубиновой бечёвке, посыпка молочными точками'),
    ('birch_sap', 'food', birch_sap, 'emerald', 40, (48, 52, 34, '#8DF5C3', 0.45), 'Берёзовый сок: трёхлитровая банка голубого стекла, полоса бересты с чёрными штрихами, стальная крышка'),
    ('dried_fish', 'food', dried_fish, 'slate', 41, (48, 54, 34, '#9FD8E8', 0.4), 'Вяленая рыба: лещ сталь/коричневый хвостом вверх на газете с серыми строками'),
    ('ryapushka', 'food', ryapushka, 'teal', 42, (48, 50, 34, '#7FE3D8', 0.4), 'Копчёная ряпушка: три рыбки веером, бронзовые спинки, молочные брюшки, фиолетовый дымок'),
    ('kalitka_potato', 'food', kalitka_potato, 'indigo', 43, (48, 52, 34, '#9AA8FF', 0.4), 'Калитка с картошкой: ржаная лодочка с защипом, молочное пюре с коралловым румянцем'),
    ('kalitka_millet', 'food', kalitka_millet, 'teal', 44, (48, 52, 34, '#7FE3D8', 0.4), 'Калитка с пшёнкой: ржаная лодочка, начинка зёрнами светлого коралла'),
    ('kalitka_berry', 'food', kalitka_berry, 'wine', 45, (48, 52, 34, '#FF9C84', 0.35), 'Калитка с черникой: ржаная лодочка, синие ягоды-кружки, фиолетовые потёки сока'),
    ('rybnik', 'food', rybnik, 'sea', 46, (48, 54, 34, '#7ACBFF', 0.4), 'Карельский рыбник: овальный пирог, стальные голова и хвост рыбы, надрез сверху'),
    ('lingon_mors', 'food', lingon_mors, 'emerald', 47, (48, 52, 34, '#8DF5C3', 0.4), 'Брусничный морс: бутылка с рубиновым морсом, веточка брусники на горлышке'),
    ('cloudberry', 'food', cloudberry, 'indigo', 48, (48, 52, 34, '#9AA8FF', 0.4), 'Морошка: банка под бирюзовой тканью, сверху три оранжево-коралловые многодольные ягоды'),
    ('ivan_chai', 'food', ivan_chai, 'teal', 49, (48, 52, 34, '#7FE3D8', 0.4), 'Иван-чай: синяя эмалированная кружка с тёмным чаем, стебель кипрея с розово-лиловыми цветками, пар'),
    ('cod', 'food', cod, 'blue', 50, (48, 46, 34, '#8CC4FF', 0.4), 'Треска горячего копчения: молочный ломоть пластами, бронзовая кожа сбоку, синий гребень волны'),
    ('reindeer_tongue', 'food', reindeer_tongue, 'emerald', 51, (48, 56, 34, '#8DF5C3', 0.4), 'Олений язык: низкая стальная банка с синей этикеткой и молочными рогами'),
    ('twig_leshy', 'gift', twig_leshy, 'sp_leshy', 52, sg('leshy'), 'Сучок-провожатый (леший): сучок-рогатка, мох у развилки, бирюзовый след-стрелка'),
    ('spruce_leshy', 'gift', spruce_leshy, 'sp_leshy', 53, sg('leshy'), 'Еловая лапка (леший): веточка по диагонали, 11 игл-осколков, рубиновая перевязка'),
    ('thread_yaga', 'gift', thread_yaga, 'sp_yaga', 54, sg('yaga'), 'Нитка из клубка (Яга): восьмёрка фиолет/роза на молочном диске, два узелка, оборванный конец'),
    ('shell_vodyanoy', 'gift', shell_vodyanoy, 'sp_vodyanoy', 55, sg('vodyanoy'), 'Ракушка-пропуск (водяной): перловица синяя/ультрамарин, перламутровые полосы роста, 3 капли'),
    ('hook_vodyanoy', 'gift', hook_vodyanoy, 'sp_vodyanoy', 56, sg('vodyanoy'), 'Медный крючок (водяной): медно-рубиновый крючок, бирюзовая петля лески, две волны'),
    ('ember_domovoy', 'gift', ember_domovoy, 'sp_domovoy', 57, None, 'Уголёк из печи (домовой): жестяная баночка с откинутой крышкой, угли рубин/роза, янтарная искра'),
    ('lapot_domovoy', 'gift', lapot_domovoy, 'sp_domovoy', 58, None, 'Лапоть с домовым: плетёный лапоть клеткой лыка, бирюзовые глаза и серая борода из проёма'),
    ('venik_bannik', 'gift', venik_bannik, 'sp_bannik', 59, sg('bannik'), 'Берёзовый веник (банник): веер листьев, рукоять с рубиновой ниткой, молочный пар'),
    ('stone_bannik', 'gift', stone_bannik, 'sp_bannik', 60, None, 'Камешек с каменки (банник): графитовый булыжник с розовым жаром в трещине, две струйки пара'),
    ('bead_kikimora', 'gift', bead_kikimora, 'sp_kikimora', 61, None, 'Бусина-морок (кикимора): болотная бусина с бирюзовым огоньком, нитка насквозь, фиолетовые искры'),
    ('kudel_kikimora', 'gift', kudel_kikimora, 'sp_kikimora', 62, sg('kikimora'), 'Кудель кикиморы: пушистый пучок серо-молочных прядей, конец скручен в нить'),
    ('ear_poludnitsa', 'gift', ear_poludnitsa, 'sp_poludnitsa', 63, sg('poludnitsa'), 'Колосок-оберег (полудница): колос-косичка молоко/светлый коралл, ость, синий василёк'),
    ('wreath_poludnitsa', 'gift', wreath_poludnitsa, 'sp_poludnitsa', 64, sg('poludnitsa'), 'Васильковый венок (полудница): 6 васильков и листья по кольцу, центр ночной'),
    ('ribbon_rusalka', 'gift', ribbon_rusalka, 'sp_rusalka', 65, sg('rusalka'), 'Речная лента (русалка): зелёная S-лента с косыми концами, вышивка бирюза/молоко'),
    ('pearl_rusalka', 'gift', pearl_rusalka, 'sp_rusalka', 66, None, 'Речная жемчужина (русалка): молочно-голубая жемчужина в тёмно-синей створке'),
    ('key_ovinnik', 'gift', key_ovinnik, 'sp_ovinnik', 67, None, 'Ключ от овина (овинник): стальной ключ по диагонали, из бородки розово-янтарный «невидимый огонь»'),
    ('sheaf_ovinnik', 'gift', sheaf_ovinnik, 'sp_ovinnik', 68, None, 'Сноп из старого овина: стебли молоко/светло-коричневый, жгут, колосья, рубиновый отсвет снизу'),
]


COUNTS = {}


def build(entry):
    ident, kind, fn, bg, seed, glow, desc = entry
    g = G(ident, size=64, bg=bg, seed=seed, glow=glow, lead=1.7)
    fn(g)
    COUNTS[ident] = (g.nbig, g.nsmall)
    return g.render()


def write_manifest(files):
    groups = [('gift', 'Дары духов (глубокий фон: ночь, цвет духа по краю)'), ('quest', 'Квест'),
              ('gear', 'Снаряжение'), ('food', 'Еда и региональные продукты')]
    out = ['# Иконки «Путника», вторая партия (v5.3) — манифест для UI', '',
           'Генерирует `python3 tools/art/items_glass_b.py` (SVG, этот манифест, лист `/tmp/items_b_sheet.png`). '
           'Стиль, кабошон и правила — как в `items_glass_manifest.md`; размер 64×64. Имя файла = id в `items.json`.', '']
    for key, title in groups:
        out += [f'## {title}', '', '| id | файл | КБ | стёкол (крупных+мелких) | что нарисовано |', '|---|---|---|---|---|']
        for ident, kind, _, _, _, _, desc in ICONS:
            if kind == key:
                n = files[ident][2]
                nb, ns = COUNTS[ident]
                out.append(f'| `{ident}` | `items/{ident}.svg` | {n/1024:.1f} | {nb}+{ns} | {desc} |')
        out.append('')
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))


if __name__ == '__main__':
    args = sys.argv[1:]
    only = set(args[args.index('--only') + 1].split(',')) if '--only' in args else None
    items = json.load(open(ITEMS_JSON, encoding='utf-8'))
    ids = [i['id'] for i in items]
    existing = {fn[:-4] for fn in os.listdir(ITEMS_DIR) if fn.endswith('.svg')}
    mine = [e[0] for e in ICONS]
    assert not (set(mine) & {e[0] for e in IG.ICONS}), 'пересечение с items_glass.py'
    unknown = [i for i in mine if i not in ids]
    files, bad = {}, bool(unknown)
    for entry in ICONS:
        if only and entry[0] not in only:
            continue
        svg = build(entry)
        n, problems = check(entry[0], svg)
        if n > MAX_BYTES:
            problems.append(f'{n} Б > {MAX_BYTES}')
        problems = [p for p in problems if not p.endswith(f'> {IG.MAX_BYTES}')]
        with open(os.path.join(ITEMS_DIR, f'{entry[0]}.svg'), 'w', encoding='utf-8') as fh:
            fh.write(svg)
        files[entry[0]] = ('item', svg, n, problems)
        bad |= bool(problems)
        print(f'{entry[0]:18s} {n:5d} Б  крупных {COUNTS[entry[0]][0]}, мелких {COUNTS[entry[0]][1]}'
              + ('  <-- ' + '; '.join(problems) if problems else ''))
    now = existing | set(files)
    print('нет в items.json:', unknown, '| без иконки:', [i for i in ids if i not in now and i not in mine])
    out = args[args.index('--sheet') + 1] if '--sheet' in args else '/tmp/items_b_sheet.png'
    # для сравнения — пара старых иконок в начале листа
    ref = {}
    for r in ('tea', 'fish', 'amulet_leshy'):
        s = open(os.path.join(ITEMS_DIR, r + '.svg'), encoding='utf-8').read()
        ref['(старый) ' + r] = ('item', s, len(s.encode()), [])
    sheet({**ref, **files}, out, big='--big' in args)
    if not only:
        write_manifest(files)
    print('лист:', out)
    sys.exit(1 if bad else 0)

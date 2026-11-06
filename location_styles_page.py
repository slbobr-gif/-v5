"""Страница сравнения 5 стилей локаций + контактный лист (Playwright)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from creature_styles_page import CSS, uri, kb

OUT = '/home/claude/out'
SRC = f'{OUT}/location_styles'
CRE = f'{OUT}/creature_styles'
CUR = '/home/claude/putnik/app/assets/art/scenes'
HTML = f'{OUT}/Путник — стили локаций.html'
PNG = f'{OUT}/Путник — стили локаций.png'

SC = [('city', 'Город вечером', 'town'), ('village', 'Деревня: изба, забор, костёр', 'village'),
      ('north', 'Карелия: лес, озеро, сияние', 'lake')]

STYLES = [
    dict(key='glass', n='1', name='Чистый витраж',
         lead='Крупные стёкла неба поясами, свинец только по формам, свет окон и фонарей — подсветка под свинцом.',
         good=['Один язык с интерфейсом и витражными иконками.', 'Читается на 320 px: крупные планы, мало осколков.',
               'Можно перевести 14 нынешних сцен почти механически — сюжеты те же.'],
         risk=['Мало отличается от нынешнего — эффект «то же самое, только крупнее».',
               'Свинцовые швы неба спорят с текстом заголовка, если карточку затемнить.'],
         effort='Низкая', note='общие примитивы (небо-пояса, ель, дом, вода) + свой сюжет на сцену'),
    dict(key='lubok', n='2', name='Лубок',
         lead='Плоские цвета, контур, штриховка земли, резные подзоры и наличники, луна с лицом, кайма-орнамент сверху.',
         good=['Пара к лубочным существам: одна рука на всю игру.',
               'Сразу «русская дорога»: избы, наличники, ели-фестоны, тюльпаны.',
               'Тёплые окна и костёр читаются, мипл виден.'],
         risk=['Город выходит пёстрым — нужна дисциплина по количеству окон и узоров.',
               'Луна с лицом и завитки — на грани детскости; для тревожных сцен убирать.'],
         effort='Средняя', note='те же примитивы, плюс штриховка и орнамент; ~22 КБ на сцену'),
    dict(key='silhouette', n='3', name='Планы с сиянием (силуэт + воздушная перспектива)',
         lead='Замена «силуэта» под пейзаж: плоские планы светлеют к горизонту, туман между ними, свет — только окна, фонари, костёр, сияние.',
         good=['Лучшая атмосфера и глубина; сразу понятно, где мы и какое время суток.',
               'Самые лёгкие файлы (8–13 КБ) и самый быстрый стиль в работе.',
               'Не спорит с текстом и существами — работает как фон-шапка.'],
         risk=['Мало деталей: Тверь и Торжок, Карелия и Валдай похожи — различать придётся силуэтами ориентиров.',
               'Рядом с лубочными или витражными существами — другой язык (нужна связка: та же кайма или рамка).'],
         effort='Низкая', note='3–5 планов + свет; уникальный силуэт-ориентир на каждую сцену'),
    dict(key='rospis', n='4', name='Роспись: гжель-ночь',
         lead='Пейзаж из мазков-капель: ели и сияние из капель, гжельские дома с кобальтовыми крышами, травка по краю холмов.',
         good=['Очень нарядно и самобытно — ни на что в сторах не похоже.',
               'Города (белые дома, синие крыши, купола-капли) выглядят лучше всего в этом стиле.'],
         risk=['Природа шумит: ели и сияние из капель сливаются в узор, сцена теряет глубину.',
               'Ближе всех к лимиту (23–25 КБ), каждая капля — отдельный путь.'],
         effort='Средняя–высокая', note='много ручной расстановки мазков, иначе всё выглядит одинаково'),
    dict(key='book', n='5', name='Книжная иллюстрация',
         lead='Тонкий контур, градиенты, гравюрная штриховка неба, наличники, рамка с розетками и орнаментальной планкой.',
         good=['Самый «книжный» и спокойный: хорошо держит длинный текст события под собой.',
               'Пара к медальонным существам; рамка единая для всех сцен.'],
         risk=['Тонкие линии и рамка теряются на 320 px, боковые поля рамки обрезаются.',
               'Ближе к открытке, чем к игре — меньше «света» и драмы.'],
         effort='Средняя', note='детали (штрих, наличники) — на каждую сцену, рамка общая'),
]
STAR = 'lubok'

CARD_TXT = {
    'city': ('ДОРОГА', 'Вечер в Твери', 'Фонари зажглись разом, как по команде. Сергей идёт по набережной, и окна смотрят ему вслед.',
             ['Зайти погреться в чайную', 'Идти дальше, пока светло от фонарей']),
    'village': ('СЛУЧАЙ', 'Костёр у околицы', 'У крайней избы кто-то жжёт ботву. Дым стелется по дороге, пахнет картошкой и осенью.',
                ['Подойти к костру и поздороваться', 'Обойти стороной — уже темнеет']),
    'north': ('ИСТОРИЯ', 'Сполохи над озером', 'Над Онегой встаёт сияние. Вода повторяет его так точно, что непонятно, где небо.',
              ['Остановиться и смотреть', 'Поставить палатку у берега']),
}

EXTRA = """
.cmp{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.duo{display:flex;gap:16px;overflow-x:auto;padding-bottom:6px}
.duo .phone .body{padding:10px 14px 12px}
.duo .cap{font-size:13px;color:var(--dim)}
@media (max-width:820px){.cmp{grid-template-columns:1fr}}
"""


def phone(img, k, title, text, chs):
    c = ''.join(f'<span class="ch">{x}</span>' for x in chs)
    return (f'<div class="phone"><div class="art"><img src="{img}" alt=""></div><div class="body"><div class="k">{k}</div>'
            f'<h4>{title}</h4><p>{text}</p>{c}</div></div>')


def mini(img, cap):
    return f'<div class="phone"><div class="art"><img src="{img}" alt=""></div><div class="body"><div class="cap">{cap}</div></div></div>'


def build():
    secs = []
    for st in STYLES:
        k = st['key']
        figs = ''.join(f'<figure><img src="{uri(f"{SRC}/{k}_{s}.svg")}" alt="{t}" width="360" height="200">'
                       f'<figcaption><b>{t}</b> · {kb(f"{SRC}/{k}_{s}.svg")} КБ</figcaption></figure>' for s, t, _ in SC)
        cards = ''.join(phone(uri(f'{SRC}/{k}_{s}.svg'), *CARD_TXT[s]) for s, _, _ in SC)
        duo = (mini(uri(f'{SRC}/{k}_village.svg'), 'Шаг 1 · сцена «Деревня»') + mini(uri(f'{CRE}/{k}_leshy_neutral.svg'), 'Шаг 2 · леший, спокоен')
               + mini(uri(f'{SRC}/{k}_north.svg'), 'Шаг 3 · сцена «Карелия»') + mini(uri(f'{CRE}/{k}_leshy_angry.svg'), 'Шаг 4 · леший, гневается'))
        good = ''.join(f'<li>{x}</li>' for x in st['good'])
        risk = ''.join(f'<li>{x}</li>' for x in st['risk'])
        star = k == STAR
        secs.append(f'''
<section class="sec" id="{k}"><div class="wrap">
 <div class="sec-h"><span class="num">{st["n"]}</span><h2>{st["name"]}</h2>{'<span class="badge">★ рекомендую</span>' if star else ''}</div>
 <p class="lead">{st["lead"]}</p>
 <div class="cmp">{figs}</div>
 <h3 class="sub">В карточке события (320 px, обрезка по ширине)</h3>
 <div class="cards">{cards}</div>
 <h3 class="sub">В связке с существом того же стиля: так шапки идут подряд по маршруту</h3>
 <div class="duo">{duo}</div>
 <div class="eval">
  <div class="box g"><b class="t">Чем хорош</b><ul>{good}</ul></div>
  <div class="box r"><b class="t">Чем рискован</b><ul>{risk}</ul></div>
  <div class="box"><b class="t">Трудоёмкость: ≈14 сцен</b><div class="eff">{st["effort"]}</div>{st["note"]}.
   <div class="meta">Чистый SVG для flutter_svg, ≤ 30 КБ. Мипл Сергея — бирюзовый, на дороге в каждой сцене.</div></div>
 </div>
</div></section>''')
    nav = ''.join(f'<a href="#{s["key"]}"{" class=star" if s["key"] == STAR else ""}><b>{s["n"]}</b> {s["name"].split(" (")[0]}{" ★" if s["key"] == STAR else ""}</a>'
                  for s in STYLES)
    cur = ''.join(f'<figure><img src="{uri(f"{CUR}/{c}.svg")}" alt="" width="360" height="200"><figcaption><b>{t}</b> · сейчас: {c}.svg</figcaption></figure>'
                  for _, t, c in SC)
    html = f'''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Путник — стили локаций</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&family=PT+Serif:wght@400;700&display=swap">
<style>{CSS}{EXTRA}</style></head><body>
<header class="hero"><div class="wrap">
 <div class="kick">Путник · арт локаций</div>
 <h1>Пять стилей для дороги</h1>
 <p class="lead">Сцены-шапки событий в пяти стилях, парных к стилям существ. Сюжеты везде одни и те же:
 город вечером, деревня с костром, карельское озеро под сиянием. Мипл Сергея стоит на дороге в каждой — по нему видно масштаб и как читается мелочь.</p>
 <nav class="nav">{nav}</nav>
 <div class="cur"><h2>Сейчас: витраж-мозаика</h2><p>Ближайшие по сюжету нынешние сцены. Мозаика ровная по всему кадру, поэтому планы и свет сливаются.</p>
 <div class="cmp">{cur}</div></div>
</div></header>
{''.join(secs)}
<div class="wrap"><div class="verdict"><h2>★ Рекомендация: лубок — вместе с лубочными существами</h2>
<p>Если существа будут лубочными, сцены стоит делать в том же стиле: контур, плоский цвет и орнамент дают одну руку на всю игру,
а избы с наличниками и ели-фестоны сразу говорят «русская дорога». На 320 px читаются окна, костёр и мипл.</p>
<p>Сильная альтернатива для пейзажей — <b>планы с сиянием</b>: самые атмосферные, лёгкие и быстрые в работе. Если владельцу ближе ночная атмосфера,
чем народная картинка, берите их в паре с силуэтными существами — так тоже получится одна рука.</p></div></div>
<footer><div class="wrap">Файлы: /home/claude/out/location_styles/&lt;стиль&gt;_&lt;сцена&gt;.svg · генератор: tools/art/location_styles.py</div></footer>
</body></html>'''
    open(HTML, 'w').write(html)


def sheet():
    from playwright.sync_api import sync_playwright
    rows = [('Сейчас: мозаика', [f'{CUR}/{c}.svg' for _, _, c in SC])]
    for st in STYLES:
        rows.append((f'{st["n"]}. {st["name"].split(" (")[0]}{" ★" if st["key"] == STAR else ""}', [f'{SRC}/{st["key"]}_{s}.svg' for s, _, _ in SC]
                     + [f'{CRE}/{st["key"]}_leshy_neutral.svg']))
    body = ''
    for name, fs in rows:
        cells = ''.join(f'<img src="{uri(x)}">' for x in fs) + ('<div class="e"></div>' if len(fs) < 4 else '')
        body += f'<div class="row"><div class="n">{name}</div>{cells}</div>'
    h = f'''<html><head><meta charset="utf-8"><style>body{{margin:0;background:#0E1621;color:#E9DFC8;font:700 17px 'PT Serif',Georgia,serif;padding:14px}}
.row{{display:flex;gap:10px;align-items:center;margin-bottom:10px}}.n{{width:150px;flex:none}}
img,.e{{width:360px;height:200px;border-radius:8px}}.e{{background:#121c28}}img:nth-of-type(4){{outline:2px solid #3FD6CC55}}</style></head><body>{body}</body></html>'''
    tmp = f'{OUT}/.sheet_tmp.html'
    open(tmp, 'w').write(h)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1648, 'height': 800})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(400)
        pg.screenshot(path=PNG, full_page=True)
        b.close()
    os.remove(tmp)


if __name__ == '__main__':
    build()
    sheet()
    print('ok')

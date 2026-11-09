"""Страница «Планы с сиянием, варианты» + контактный лист."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from creature_styles_page import CSS, uri, kb
from location_styles_page import EXTRA, CARD_TXT, phone, mini

OUT = '/home/claude/out'
SRC = f'{OUT}/silhouette_styles'
BASE_L = f'{OUT}/location_styles/silhouette_'
BASE_C = f'{OUT}/creature_styles/silhouette_'
HTML = f'{OUT}/Путник — планы с сиянием, варианты.html'
PNG = f'{OUT}/Путник — планы с сиянием, варианты.png'

SCN = [('city', 'Город вечером'), ('village', 'Деревня'), ('north', 'Карелия')]
CRS = [('leshy_neutral', 'Леший, спокоен'), ('leshy_angry', 'Леший, гневается'), ('domovoy_kind', 'Домовой, добр')]
CR_TXT = {
    'leshy_neutral': ('СУЩЕСТВО', 'Первая тишина', 'За Зеленоградом шум трассы обрывается, будто кто-то выключил звук. Сосны, мох, дятел наверху.',
                      ['Поздороваться с лесом и оставить хлеб', 'Вернуться к трассе']),
    'leshy_angry': ('СУЩЕСТВО', 'Лес обиделся', 'Лес встаёт стеной, и трасса пропадает. Деревья смыкаются за спиной.',
                    ['Поклониться и попросить прощения', 'Вывернуть одежду и искать дорогу']),
    'domovoy_kind': ('СУЩЕСТВО', 'Новоселье', 'Новый дом пахнет стружкой. В печи потрескивает уголёк из старой жестянки.',
                     ['Поблагодарить дом', 'Спросить, можно ли взять уголёк']),
}

VARS = [
    dict(key='dusk', n='А', name='Сумерки-градиент',
         lead='Небо меняется по времени суток: закатный коралл → лиловый → индиго; 5–7 планов светлеют к горизонту, туман между ними, '
              'мягкие лучи от окон и фонарей, отражения на мокрой мостовой и в озере, звёзды.',
         good=['Прямое развитие того, что понравилось: та же простота, но глубже и богаче цветом.',
               'Небо само рассказывает время суток — можно связать с часом, когда игрок шагает.',
               'Лёгкие файлы (8–22 КБ), читается на 320 px, текст под шапкой не спорит.'],
         risk=['Самый «мягкий»: без резких акцентов сцены могут сливаться в одну красивую открытку.',
               'Градиенты-лучи в flutter_svg рисуются, но на слабых телефонах прозрачности стоит проверить.'],
         effort='Низкая', note='планы и небо параметрические: на сцену — свой силуэт-ориентир и цвет часа'),
    dict(key='glass', n='Б', name='Витражный силуэт',
         lead='Те же чёрные планы, но небо, луна, сияние, вода и окна собраны из крупных стёкол с тонким свинцом; окна — цветные стёклышки с переплётом.',
         good=['Мост к витражному интерфейсу: силуэт + стекло выглядят одной системой с иконками.',
               'Свет (окна, фонари, луна) ощущается «просвеченным стеклом» — очень по-витражному.'],
         risk=['Свинцовые швы неба шумят на 320 px и тянут внимание от существа.',
               'Ближе к старой мозаике — владелец может увидеть шаг назад.', 'Город — самый тяжёлый файл (≈27 КБ).'],
         effort='Средняя', note='раскладка стёкол неба и воды для каждой сцены вручную, иначе выглядит случайно'),
    dict(key='etch', n='В', name='Северная гравюра / контражур',
         lead='Двухцветно: бирюза и коралл. Дальние планы — штрихи, ближние — чёрные с контровой кромкой; низкий диск света и лучи; '
              'передний план-рамка: еловая лапа и трава.',
         good=['Самый выразительный и узнаваемый — ни на что не похож, сразу «стиль Путника».',
               'Контровой свет делает гнев и угрозу очень сильными; рамка из лапника даёт глубину.'],
         risk=['Тонкие штрихи мельчат и могут рябить (муар) на маленьких экранах и при масштабировании.',
               'Строгий двухцвет: тёплые сцены (деревня, дом) получаются суровее, чем по тексту.'],
         effort='Средняя', note='штрихи генерируются кодом, но плотность и кромки надо подбирать по сцене'),
]
STAR = 'dusk'


def build():
    secs = []
    for v in VARS:
        k = v['key']
        scen = ''.join(f'<figure><img src="{uri(f"{SRC}/{k}_{s}.svg")}" alt="{t}" width="360" height="200"><figcaption><b>{t}</b> · '
                       f'{kb(f"{SRC}/{k}_{s}.svg")} КБ</figcaption></figure>' for s, t in SCN)
        crs = ''.join(f'<figure><img src="{uri(f"{SRC}/{k}_{s}.svg")}" alt="{t}" width="360" height="200"><figcaption><b>{t}</b> · '
                      f'{kb(f"{SRC}/{k}_{s}.svg")} КБ</figcaption></figure>' for s, t in CRS)
        cards = ''.join(phone(uri(f'{SRC}/{k}_{s}.svg'), *CARD_TXT[s]) for s, _ in SCN) + phone(uri(f'{SRC}/{k}_leshy_angry.svg'), *CR_TXT['leshy_angry'])
        duo = (mini(uri(f'{SRC}/{k}_village.svg'), 'Шаг 1 · деревня') + mini(uri(f'{SRC}/{k}_domovoy_kind.svg'), 'Шаг 2 · домовой, добр')
               + mini(uri(f'{SRC}/{k}_north.svg'), 'Шаг 3 · Карелия') + mini(uri(f'{SRC}/{k}_leshy_neutral.svg'), 'Шаг 4 · леший, спокоен')
               + mini(uri(f'{SRC}/{k}_leshy_angry.svg'), 'Шаг 5 · леший, гневается'))
        good = ''.join(f'<li>{x}</li>' for x in v['good'])
        risk = ''.join(f'<li>{x}</li>' for x in v['risk'])
        star = k == STAR
        secs.append(f'''
<section class="sec" id="{k}"><div class="wrap">
 <div class="sec-h"><span class="num">{v["n"]}</span><h2>{v["name"]}</h2>{'<span class="badge">★ рекомендую</span>' if star else ''}</div>
 <p class="lead">{v["lead"]}</p>
 <div class="cmp">{scen}</div>
 <div class="cmp" style="margin-top:12px">{crs}</div>
 <h3 class="sub">В карточке события (320 px, обрезка по ширине)</h3>
 <div class="cards">{cards}</div>
 <h3 class="sub">В связке: сцена и существо подряд по маршруту</h3>
 <div class="duo">{duo}</div>
 <div class="eval">
  <div class="box g"><b class="t">Чем хорош</b><ul>{good}</ul></div>
  <div class="box r"><b class="t">Чем рискован</b><ul>{risk}</ul></div>
  <div class="box"><b class="t">Трудоёмкость: ≈14 сцен + 9 существ × 4 настроения</b><div class="eff">{v["effort"]}</div>{v["note"]}.
   <div class="meta">Силуэты существ общие для всех вариантов — меняются фон, свет и кромка. Чистый SVG для flutter_svg, ≤ 30 КБ.</div></div>
 </div>
</div></section>''')
    nav = ''.join(f'<a href="#{v["key"]}"{" class=star" if v["key"] == STAR else ""}><b>{v["n"]}</b> {v["name"]}{" ★" if v["key"] == STAR else ""}</a>'
                  for v in VARS)
    base = ''.join(f'<figure><img src="{uri(f"{BASE_L}{s}.svg")}" alt="" width="360" height="200"><figcaption><b>{t}</b></figcaption></figure>' for s, t in SCN)
    base += ''.join(f'<figure><img src="{uri(f"{BASE_C}{s}.svg")}" alt="" width="360" height="200"><figcaption><b>{t}</b></figcaption></figure>' for s, t in CRS)
    html = f'''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Путник — планы с сиянием, варианты</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&family=PT+Serif:wght@400;700&display=swap">
<style>{CSS}{EXTRA}</style></head><body>
<header class="hero"><div class="wrap">
 <div class="kick">Путник · планы с сиянием</div>
 <h1>Три пути от понравившегося стиля</h1>
 <p class="lead">Основа — силуэтные планы с воздушной перспективой. Ниже три разных развития: больше цвета и глубины,
 мост к витражу и двухцветная гравюра в контровом свете. В каждом — те же три сцены, леший спокойный и гневный, добрый домовой; мипл Сергея на дороге.</p>
 <nav class="nav">{nav}</nav>
 <div class="cur"><h2>Исходный стиль 3 «Планы с сиянием»</h2><p>То, что понравилось владельцу, — для сравнения.</p>
 <div class="cmp">{base}</div></div>
</div></header>
{''.join(secs)}
<div class="wrap"><div class="verdict"><h2>★ Рекомендация: А «Сумерки-градиент»</h2>
<p>Он сохраняет всё, за что выбрали стиль 3 — простые силуэты, светящиеся глаза и окна, лёгкие файлы, — и добавляет то, чего не хватало:
глубину (5–7 планов), цвет времени суток и живой свет (лучи, отражения). На 320 px читается лучше всех, работы меньше всех.</p>
<p>Из В стоит взять два приёма для отдельных сцен: передний план-рамку (лапник, трава) и коралловый контровой свет для гнева.
Б оставить как запасной, если захочется плотнее связать картинки с витражным интерфейсом.</p></div></div>
<footer><div class="wrap">Файлы: /home/claude/out/silhouette_styles/&lt;вариант&gt;_&lt;сцена|существо&gt;.svg · генератор: tools/art/silhouette_variants.py</div></footer>
</body></html>'''
    open(HTML, 'w').write(html)


def sheet():
    from playwright.sync_api import sync_playwright
    rows = [('Исходный стиль 3', [f'{BASE_L}{s}.svg' for s, _ in SCN] + [f'{BASE_C}{s}.svg' for s, _ in CRS])]
    for v in VARS:
        rows.append((f'{v["n"]}. {v["name"]}{" ★" if v["key"] == STAR else ""}', [f'{SRC}/{v["key"]}_{s}.svg' for s, _ in SCN + CRS]))
    body = ''.join(f'<div class="row"><div class="n">{n}</div>' + ''.join(f'<img src="{uri(x)}">' for x in fs) + '</div>' for n, fs in rows)
    h = f'''<html><head><meta charset="utf-8"><style>body{{margin:0;background:#0E1621;color:#E9DFC8;font:700 16px 'PT Serif',Georgia,serif;padding:12px}}
.row{{display:flex;gap:8px;align-items:center;margin-bottom:8px}}.n{{width:130px;flex:none}}
img{{width:288px;height:160px;border-radius:7px}}</style></head><body>{body}</body></html>'''
    tmp = f'{OUT}/.sheet_tmp.html'
    open(tmp, 'w').write(h)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1922, 'height': 700})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(400)
        pg.screenshot(path=PNG, full_page=True)
        b.close()
    os.remove(tmp)


if __name__ == '__main__':
    build()
    sheet()
    print('ok')

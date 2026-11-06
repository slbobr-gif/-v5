"""Страница сравнения 5 стилей существ + контактный лист (Playwright)."""
import base64
import os

OUT = '/home/claude/out'
SRC = f'{OUT}/creature_styles'
CUR = '/home/claude/putnik/app/assets/art/spirits'
HTML = f'{OUT}/Путник — стили существ.html'
PNG = f'{OUT}/Путник — стили существ.png'


def uri(path):
    return 'data:image/svg+xml;base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def kb(path):
    return f'{os.path.getsize(path) / 1024:.1f}'


STYLES = [
    dict(key='glass', n='1', name='Чистый витраж',
         lead='Развитие текущего: крупные стёкла, свинец только по форме, лучи-ореол за головой вместо мелкой мозаики.',
         good=['Роднее всего витражному интерфейсу — один язык на всех экранах.',
               'Силуэт и эмоция читаются: крупные куски, чёткие брови и глаза.',
               'Есть готовая база (скрипты витража), фон-лучи меняет цвет по настроению.'],
         risk=['Мало нового: владелец может не почувствовать «другой» стиль.',
               'Плоские стёкла без мозаики иногда выглядят «векторным клипартом».'],
         effort='Низкая–средняя', effort_note='общий скелет фигуры + лучи; новое — лицо и 1–2 предмета на существо'),
    dict(key='lubok', n='2', name='Лубок / народная гравюра',
         lead='Плоские цвета, жирный контур, штриховка, фестоны и тюльпаны, кайма-орнамент; палитра тёмная, акценты бирюза и коралл.',
         good=['Самый «русский» и узнаваемый — сразу фольклор, без пояснений.',
               'Чёрный контур рифмуется со свинцом витража, плоская заливка легко масштабируется.',
               'Эмоции крупные и простые: круглые глаза, румянец, оскал — читаются на 320 px.'],
         risk=['Может уйти в «детскую книжку» — нужно держать тёмный фон и сдержанный румянец.',
               'Штриховка и фестоны съедают байты (злой леший — 27 КБ из 30).'],
         effort='Средняя', effort_note='набор примитивов (фестоны, штрих, тюльпан, ель) переиспользуется на всех'),
    dict(key='silhouette', n='3', name='Силуэт с сиянием',
         lead='Чёрный силуэт на светящемся фоне: луна, туман, окно; только глаза и рот светятся. Настроение — цветом сияния.',
         good=['Самый сильный по атмосфере и самый дешёвый: деталей почти нет.',
               'Эмоция читается мгновенно — глаза светятся, гнев = коралловая луна.',
               'Файлы лёгкие (8–19 КБ), идеально контрастирует с витражным интерфейсом.'],
         risk=['Существа держатся только на контуре: русалка/полудница/кикимора — все «женская фигура», их легко спутать.',
               'Добрые и хитрые настроения хуже, чем злые: в темноте всё немного жутко.'],
         effort='Низкая', effort_note='силуэт + фон-сцена; но на каждое существо нужен свой узнаваемый контур'),
    dict(key='rospis', n='4', name='Роспись: гжель-ночь / жостово',
         lead='Существо собрано из кистевых мазков-капель: кобальт и бирюза с белым бликом, ягоды-коралл, ветки-травка на чёрной эмали.',
         good=['Самый необычный и декоративный — выглядит как подарочная роспись.',
               'Палитра совпадает с акцентами приложения, без жёлтого золота.',
               'Мазок-капля один на всё — код компактный.'],
         risk=['Существа становятся похожи друг на друга («всё из капель»), лицо-маска холодное.',
               'Злой режим получается скорее нарядным, чем страшным.'],
         effort='Средняя–высокая', effort_note='легко нарисовать, трудно сделать 9 существ различимыми'),
    dict(key='book', n='5', name='Книжная иллюстрация: медальон',
         lead='Тонкий контур, медальон-окно с пейзажем, рамка с орнаментом и стеблями; фигура выходит за край медальона.',
         good=['Самый «дорогой» вид, сказочная книга; рамка-медальон перекликается с витражными арками.',
               'Каждое существо получает свой пейзаж в медальоне — легко различать.',
               'Тонкие пряди и морщины дают характер без мозаики.'],
         risk=['На 320 px тонкие линии мельчат, поля рамки обрезаются на экране события.',
               'Ближе всех к лимиту 30 КБ (злой леший — 28 КБ).'],
         effort='Высокая', effort_note='медальон-сцена на каждое существо + штрих; 36 картинок — больше всего работы'),
]
STAR = 'lubok'

EVENTS = [
    ('leshy', 'neutral', 'Первая тишина',
     'За Зеленоградом Сергей сворачивает с обочины на просеку. Через двести шагов шум трассы обрывается, будто кто-то выключил звук.',
     [('Поздороваться с лесом и оставить хлеб на пне', 0), ('Вернуться к трассе — в лесу не по себе', 0)]),
    ('leshy', 'angry', 'Лес обиделся',
     'За Торжком лес встаёт стеной, и трасса вдруг пропадает. Только что гудели фуры — и тишина, как в погребе.',
     [('Поклониться вслед и честно попросить прощения', 0), ('Вывернуть одежду и искать дорогу самому', 1)]),
    ('domovoy', 'kind', 'Новоселье',
     'На окраине Вышнего Волочка стоит новый дом из светлого бруса, ещё пахнущий стружкой. Ольга открывает дверь с малышом на руках.',
     [('Закрыть жестянку и поблагодарить дом', 0), ('Спросить Ольгу, можно ли взять уголёк', 0)]),
]
MOODS = {'neutral': 'спокоен', 'angry': 'гневается', 'kind': 'добр'}
CRE = {'leshy': 'Леший', 'domovoy': 'Домовой'}

CSS = """
:root{color-scheme:dark;--ink:#0E1621;--raised:#16222F;--high:#1F3043;--parch:#E9DFC8;--dim:#9BA7B4;--turq:#3FD6CC;
--coral:#E07A5F;--danger:#FF6B7A;--line:#25384C}
*{box-sizing:border-box}
html{background:#0E1621;-webkit-text-size-adjust:100%}
body{margin:0;background:#0E1621;color:#E9DFC8;font:16px/1.55 'PT Sans','Liberation Sans','Segoe UI',Roboto,Arial,sans-serif;
 background-image:radial-gradient(900px 500px at 12% -5%,rgba(43,196,186,.10),transparent 60%),radial-gradient(800px 500px at 100% 0,rgba(91,63,160,.14),transparent 60%)}
h1,h2,h3{font-family:'PT Serif',Georgia,'Liberation Serif',serif;font-weight:700;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px}
.hero{padding:40px 0 10px}
.kick{color:var(--turq);font-size:13px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
.hero h1{font-size:clamp(30px,5.2vw,48px);line-height:1.08;margin:8px 0 12px}
.lead{max-width:780px;color:#CFC8B3;font-size:17px;margin:0 0 14px}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.nav a{padding:7px 13px;border-radius:999px;border:1px solid #2c4560;background:rgba(22,34,47,.8);color:var(--parch);text-decoration:none;font-size:14.5px}
.nav a b{color:var(--turq)} .nav a:hover{border-color:var(--turq)}
.nav a.star{border-color:var(--turq)}
.cur{background:rgba(22,34,47,.7);border:1px solid var(--line);border-radius:18px;padding:16px;margin:22px 0 6px}
.cur h2{font-size:21px;margin-bottom:4px} .cur p{margin:0 0 12px;color:var(--dim);font-size:14.5px}
.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
figure{margin:0} figure img{width:100%;height:auto;display:block;border-radius:12px;background:#070B10}
figcaption{font-size:13.5px;color:var(--dim);margin-top:5px}
figcaption b{color:var(--parch);font-weight:700}
section.sec{padding:34px 0 8px;border-top:1px solid #1b2a3a;margin-top:26px}
.sec-h{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.num{font-family:'PT Serif',Georgia,serif;color:var(--turq);font-size:30px;font-weight:700}
.sec-h h2{font-size:clamp(23px,3.4vw,30px)}
.badge{display:inline-flex;align-items:center;gap:6px;background:rgba(63,214,204,.14);border:1px solid var(--turq);color:var(--turq);
 border-radius:999px;padding:3px 11px;font-size:14px;font-weight:700}
.sec .lead{font-size:15.5px;margin-bottom:14px}
.three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.big{display:grid;grid-template-columns:1fr;gap:12px}
.big figure:first-child{grid-column:1/-1}
.row2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
h3.sub{font-size:17px;margin:22px 0 10px;color:#CFC8B3}
.cards{display:flex;gap:16px;overflow-x:auto;padding-bottom:6px}
.phone{flex:none;width:320px;background:#0E1621;border:1px solid var(--line);border-radius:22px;overflow:hidden}
.phone .art{width:320px;height:220px;overflow:hidden;position:relative}
.phone .art img{position:absolute;left:-38px;top:0;width:396px;height:220px;max-width:none;border-radius:0}
.phone .body{padding:14px 16px 16px}
.phone .k{color:var(--turq);font-size:12px;letter-spacing:.15em;font-weight:700}
.phone h4{font-family:'PT Serif',Georgia,serif;font-size:21px;margin:3px 0 8px;line-height:1.2}
.phone p{font-size:14.5px;color:#CFC8B3;margin:0 0 12px;line-height:1.5}
.ch{display:block;border:1px solid #2c4560;background:#16222F;border-radius:12px;padding:10px 12px;font-size:14.5px;margin-top:8px}
.ch.r{border-color:rgba(224,122,95,.6)} .ch.r::after{content:' · риск';color:var(--coral);font-size:13px}
.eval{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}
.box{background:rgba(22,34,47,.78);border:1px solid var(--line);border-radius:14px;padding:12px 14px;font-size:14.5px;color:#CFC8B3}
.box b.t{display:block;color:var(--parch);font-size:15px;margin-bottom:4px}
.box ul{margin:0;padding-left:18px} .box li{margin:3px 0}
.box.g b.t{color:var(--turq)} .box.r b.t{color:var(--coral)}
.eff{font-size:20px;font-family:'PT Serif',Georgia,serif;color:var(--parch);margin:2px 0 4px}
.meta{font-size:13px;color:var(--dim);margin-top:8px}
.verdict{background:linear-gradient(135deg,rgba(63,214,204,.13),rgba(22,34,47,.85));border:1px solid var(--turq);border-radius:18px;padding:18px;margin:34px 0 10px}
.verdict h2{font-size:24px;margin-bottom:6px} .verdict p{margin:6px 0;color:#CFC8B3}
footer{color:var(--dim);font-size:13px;padding:26px 0 40px;overflow-wrap:anywhere}
@media (max-width:820px){.three,.eval{grid-template-columns:1fr}.pair,.row2{grid-template-columns:1fr}}
"""


def build():
    st_html = []
    for st in STYLES:
        k = st['key']
        f = {e: f'{SRC}/{k}_{e}.svg' for e in ('leshy_neutral', 'leshy_angry', 'domovoy_kind')}
        star = k == STAR
        figs = ''.join(
            f'<figure><img src="{uri(f[e])}" alt="{CRE[e.split("_")[0]]}, {MOODS[e.split("_")[1]]}" width="360" height="200">'
            f'<figcaption><b>{CRE[e.split("_")[0]]}</b> · {MOODS[e.split("_")[1]]} · {kb(f[e])} КБ</figcaption></figure>'
            for e in f)
        cards = ''
        for cr, mood, title, text, ch in EVENTS:
            img = uri(f'{SRC}/{k}_{cr}_{mood}.svg')
            chs = ''.join(f'<span class="ch{" r" if r else ""}">{c}</span>' for c, r in ch)
            cards += (f'<div class="phone"><div class="art"><img src="{img}" alt=""></div><div class="body">'
                      f'<div class="k">СУЩЕСТВО</div><h4>{title}</h4><p>{text}</p>{chs}</div></div>')
        good = ''.join(f'<li>{x}</li>' for x in st['good'])
        risk = ''.join(f'<li>{x}</li>' for x in st['risk'])
        st_html.append(f'''
<section class="sec" id="{k}"><div class="wrap">
 <div class="sec-h"><span class="num">{st["n"]}</span><h2>{st["name"]}</h2>{'<span class="badge">★ рекомендую</span>' if star else ''}</div>
 <p class="lead">{st["lead"]}</p>
 <div class="three">{figs}</div>
 <h3 class="sub">Как будет на экране события (320 px, обрезка по ширине)</h3>
 <div class="cards">{cards}</div>
 <div class="eval">
  <div class="box g"><b class="t">Чем хорош</b><ul>{good}</ul></div>
  <div class="box r"><b class="t">Чем рискован</b><ul>{risk}</ul></div>
  <div class="box"><b class="t">Трудоёмкость: 9 существ × 4 настроения</b><div class="eff">{st["effort"]}</div>{st["effort_note"]}.
   <div class="meta">36 картинок; все — чистый SVG для flutter_svg, ≤ 30 КБ.</div></div>
 </div>
</div></section>''')

    nav = ''.join(f'<a href="#{s["key"]}"{" class=star" if s["key"] == STAR else ""}><b>{s["n"]}</b> {s["name"]}{" ★" if s["key"] == STAR else ""}</a>'
                  for s in STYLES)
    cur = ''.join(f'<figure><img src="{uri(f"{CUR}/leshy_{m}.svg")}" alt="" width="360" height="200"><figcaption><b>Леший</b> · {MOODS[m]} · сейчас</figcaption></figure>'
                  for m in ('neutral', 'angry'))
    html = f'''<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Путник — стили существ</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&family=PT+Serif:wght@400;700&display=swap">
<style>{CSS}</style></head><body>
<header class="hero"><div class="wrap">
 <div class="kick">Путник · арт существ</div>
 <h1>Пять стилей для духов</h1>
 <p class="lead">Интерфейс остаётся витражным, а существ выбираем заново. Каждый стиль показан на одних и тех же сценах:
 леший спокойный и гневный, домовой добрый. Все картинки — 360×200, рисуются кодом и подходят для flutter_svg.</p>
 <nav class="nav">{nav}</nav>
 <div class="cur"><h2>Сейчас: витраж-мозаика</h2><p>Для сравнения — текущий леший. Мелкие осколки дробят лицо, на 320 px эмоция теряется.</p>
 <div class="pair">{cur}</div></div>
</div></header>
{''.join(st_html)}
<div class="wrap"><div class="verdict"><h2>★ Рекомендация: лубок</h2>
<p>Лубок лучше всех держит три вещи сразу: существо узнаётся с первого взгляда, эмоция читается на 320 px,
а жирный контур рифмуется со свинцом витражного интерфейса, поэтому экраны выглядят одной игрой. Стиль заметно отличается от нынешней мозаики,
но остаётся тёмным и «нашим»: бирюза, коралл, никакого жёлтого.</p>
<p>Запасной вариант — <b>книжный медальон</b>: он самый красивый, но дороже в работе и мельчит на телефоне.
<b>Силуэт</b> хорош для редких страшных сцен (гнев, ночь), но на нём одном 9 существ не различить.</p></div></div>
<footer><div class="wrap">Файлы: /home/claude/out/creature_styles/&lt;стиль&gt;_&lt;существо&gt;_&lt;настроение&gt;.svg ·
генератор: tools/art/creature_styles.py</div></footer>
</body></html>'''
    open(HTML, 'w').write(html)


def sheet():
    from playwright.sync_api import sync_playwright
    rows = []
    rows.append(('Сейчас: мозаика', [f'{CUR}/leshy_neutral.svg', f'{CUR}/leshy_angry.svg', None]))
    for st in STYLES:
        rows.append((f'{st["n"]}. {st["name"]}{" ★" if st["key"] == STAR else ""}',
                     [f'{SRC}/{st["key"]}_{e}.svg' for e in ('leshy_neutral', 'leshy_angry', 'domovoy_kind')]))
    body = ''
    for name, fs in rows:
        cells = ''.join(f'<img src="{uri(x)}">' if x else '<div class="e"></div>' for x in fs)
        body += f'<div class="row"><div class="n">{name}</div>{cells}</div>'
    h = f'''<html><head><meta charset="utf-8"><style>body{{margin:0;background:#0E1621;color:#E9DFC8;font:700 17px 'PT Serif',Georgia,serif;padding:14px}}
.row{{display:flex;gap:10px;align-items:center;margin-bottom:10px}}.n{{width:150px;flex:none}}
img,.e{{width:360px;height:200px;border-radius:8px}}.e{{background:#121c28}}</style></head><body>{body}</body></html>'''
    tmp = f'{OUT}/.sheet_tmp.html'
    open(tmp, 'w').write(h)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1278, 'height': 800})
        pg.goto('file://' + tmp)
        pg.wait_for_timeout(400)
        pg.screenshot(path=PNG, full_page=True)
        b.close()
    os.remove(tmp)


if __name__ == '__main__':
    build()
    sheet()
    print('ok')

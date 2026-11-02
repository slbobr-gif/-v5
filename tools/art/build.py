"""Сборка всей графики MVP «Путника».

python3 tools/art/build.py [--glass [--glass-only имя,имя]] [--sheet OUT.png] [--icons] [--flat-hero]
Пишет SVG в app/assets/art/, проверяет запреты flutter_svg и размер,
рендерит контактный лист и PNG-иконки через Chromium (playwright).

--glass — витражный конвертер (tools/art/glassify.py) над сценами, существами,
финалом и онбордингом: «сырьё» (плоские рисунки scenes.py/creatures.py/extras.py)
пишется в tools/art/raw/, результат — в app/assets/art/. Без --glass эти
картинки не трогаются (берутся готовые с диска). Герой/иконка/маркер/предметы/заставки
ведут свои скрипты (hero_glass.py, items_glass.py); build.py их не перезаписывает.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ART = os.path.join(ROOT, 'app', 'assets', 'art')
MIPMAP = os.path.join(ROOT, 'app', 'android-overlay', 'res')

FORBIDDEN = re.compile(r'<(filter|mask|clipPath|pattern|text|image|foreignObject|style|use|symbol|tspan)\b|\sstyle=|\swidth="\d+px|\sclip-path=|\sfilter=|\smask=', re.I)
MAX = 25 * 1024


def collect(flat_hero=False):
    """Герой/иконка/маркер ведёт hero_glass.py (витражи, свой запуск) — здесь по умолчанию НЕ трогаем.
    Старые плоские hero.py/extras.icon() включаются флагом --flat-hero (только для отладки)."""
    out = {}
    if flat_hero:
        import hero, extras
        out['hero/sergey.svg'] = hero.sergey()
        out['hero/sergey_marker.svg'] = hero.marker()
        out['icon/icon.svg'] = extras.icon()
    return out


def disk_files():
    """Все SVG из app/assets/art (в порядке показа на контактном листе)."""
    order = ['scenes', 'creatures', 'finale', 'onboarding', 'intro', 'hero', 'icon', 'items']
    out = {}
    for grp in order:
        d = os.path.join(ART, grp)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.svg'):
                with open(os.path.join(d, fn), encoding='utf-8') as fh:
                    out[f'{grp}/{fn}'] = fh.read()
    return out


def check(files):
    """Запрещённые элементы flutter_svg, размер ≤ 25 КБ, viewBox — для всех SVG на диске."""
    bad = []
    for rel, svg in files.items():
        size = len(svg.encode())
        m = FORBIDDEN.search(svg)
        if m or size > MAX or 'viewBox' not in svg[:200]:
            bad.append((rel, size, m.group(0) if m else ''))
    return bad


def write(files):
    bad = []
    for rel, svg in files.items():
        p = os.path.join(ART, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(svg)
        size = len(svg.encode())
        m = FORBIDDEN.search(svg)
        if m or size > MAX or 'viewBox' not in svg[:200]:
            bad.append((rel, size, m.group(0) if m else ''))
    return bad


def sheet(files, out, zoom=1.0):
    from playwright.sync_api import sync_playwright
    cells = []
    for rel, svg in files.items():
        b = base64.b64encode(svg.encode()).decode()
        vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        w, h = int(vb.group(1)), int(vb.group(2))
        scale = 1.0 if w >= 300 else (1.6 if w >= 100 else 2.2)
        if w == 512:
            scale = 0.45
        if w == 48:
            scale = 3
        scale *= zoom
        cells.append(f'<figure><img src="data:image/svg+xml;base64,{b}" width="{int(w*scale)}" height="{int(h*scale)}"><figcaption>{rel} · {len(svg)//1024 + 1}K</figcaption></figure>')
    html = ('<html><body style="margin:0;background:#05090e;font:11px sans-serif;color:#9BA7B4">'
            '<div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px;width:1540px;align-items:flex-start">'
            + ''.join(cells) + '</div><style>figure{margin:0}</style></body></html>')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1560, 'height': 800})
        pg.set_content(html)
        pg.wait_for_timeout(300)
        pg.screenshot(path=out, full_page=True)
        b.close()


def subset_sheet(files, prefix, out):
    sheet({k: v for k, v in files.items() if k.startswith(prefix)}, out)


def icons(svg):
    from playwright.sync_api import sync_playwright
    sizes = dict(mdpi=48, hdpi=72, xhdpi=96, xxhdpi=144, xxxhdpi=192)
    b64 = base64.b64encode(svg.encode()).decode()
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, s in sizes.items():
            pg = br.new_page(viewport={'width': s, 'height': s})
            pg.set_content(f'<html><body style="margin:0;background:transparent">'
                           f'<img src="data:image/svg+xml;base64,{b64}" width="{s}" height="{s}" style="display:block"></body></html>')
            pg.wait_for_timeout(100)
            d = os.path.join(MIPMAP, f'mipmap-{name}')
            os.makedirs(d, exist_ok=True)
            pg.screenshot(path=os.path.join(d, 'ic_launcher.png'), omit_background=True)
            pg.close()
        br.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    files = collect('--flat-hero' in args)
    if '--glass' in args:
        import glass_build
        only = None
        if '--glass-only' in args:
            only = args[args.index('--glass-only') + 1].split(',')
        files.update(glass_build.build(only))
    bad = write(files)
    disk = disk_files()
    for rel, size, why in check(disk):
        if (rel, size, why) not in bad:
            bad.append((rel, size, why))
    for rel, size, why in bad:
        print('BAD', rel, size, why)
    sizes = [len(v.encode()) for v in disk.values()]
    glass = [len(v.encode()) for k, v in disk.items() if k.split('/')[0] in ('scenes', 'creatures', 'finale', 'onboarding')]
    print(f'{len(disk)} files on disk, max {max(sizes)} bytes; glass {len(glass)} files, '
          f'max {max(glass) if glass else 0}, avg {sum(glass) // max(1, len(glass))} bytes')
    if '--sheet' in args:
        out = args[args.index('--sheet') + 1]
        pref = args[args.index('--only') + 1] if '--only' in args else ''
        subset_sheet(disk, pref, out)
    if '--icons' in args:
        import app_icon; app_icon.main()

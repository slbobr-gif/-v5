"""Сборка всей графики MVP «Путника».

python3 tools/art/build.py [--sheet OUT.png] [--icons]
Пишет SVG в app/assets/art/, проверяет запреты flutter_svg и размер,
рендерит контактный лист и PNG-иконки через Chromium (playwright).
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


def collect():
    import scenes, creatures, hero, extras
    out = {}
    for k, fn in scenes.SCENES.items():
        out[f'scenes/{k}.svg'] = fn()
    for k, fn in creatures.CREATURES.items():
        out[f'creatures/{k}.svg'] = fn()
    out['hero/sergey.svg'] = hero.sergey()
    out['hero/sergey_marker.svg'] = hero.marker()
    for k, fn in extras.ONBOARDING.items():
        out[f'onboarding/{k}.svg'] = fn()
    out['finale/teriberka.svg'] = extras.teriberka()
    out['icon/icon.svg'] = extras.icon()
    return out


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
    files = collect()
    bad = write(files)
    for rel, size, why in bad:
        print('BAD', rel, size, why)
    print(f'{len(files)} files, max {max(len(v.encode()) for v in files.values())} bytes')
    args = sys.argv[1:]
    if '--sheet' in args:
        out = args[args.index('--sheet') + 1]
        pref = args[args.index('--only') + 1] if '--only' in args else ''
        subset_sheet(files, pref, out)
    if '--icons' in args:
        icons(files['icon/icon.svg'])

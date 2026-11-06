"""Иконка приложения v5.3: «Хвост кита» (выбор владельца, вариант 20).
Источник — tools/art/app_icon.svg (512×512, на весь квадрат, главный силуэт в центральных 66 %).
Пишет: app/assets/art/icon/icon.svg; android-overlay/res/mipmap-*/ic_launcher.png (скруглённый квадрат),
ic_launcher_round.png (круг), ic_launcher_foreground.png (adaptive, 108 dp), mipmap-anydpi-v26/ic_launcher(.xml,_round.xml),
values/ic_launcher_colors.xml.
Запуск: python3 tools/art/app_icon.py
"""
import base64, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'tools', 'art', 'app_icon.svg')
RES = os.path.join(ROOT, 'app', 'android-overlay', 'res')
BG = '#1B2A6B'
LEGACY = dict(mdpi=48, hdpi=72, xhdpi=96, xxhdpi=144, xxxhdpi=192)
FG = dict(mdpi=108, hdpi=162, xhdpi=216, xxhdpi=324, xxxhdpi=432)

def main():
    from playwright.sync_api import sync_playwright
    svg = open(SRC, encoding='utf-8').read()
    os.makedirs(os.path.join(ROOT, 'app/assets/art/icon'), exist_ok=True)
    open(os.path.join(ROOT, 'app/assets/art/icon/icon.svg'), 'w', encoding='utf-8').write(svg)
    b64 = base64.b64encode(svg.encode()).decode()
    with sync_playwright() as p:
        br = p.chromium.launch()
        def shot(size, path, radius):
            pg = br.new_page(viewport={'width': size, 'height': size})
            pg.set_content(f'<html><body style="margin:0;background:transparent"><div style="width:{size}px;height:{size}px;'
                           f'border-radius:{radius};overflow:hidden"><img src="data:image/svg+xml;base64,{b64}" '
                           f'width="{size}" height="{size}" style="display:block"></div></body></html>')
            pg.wait_for_timeout(120)
            pg.screenshot(path=path, omit_background=True); pg.close()
        for name in LEGACY:
            d = os.path.join(RES, f'mipmap-{name}'); os.makedirs(d, exist_ok=True)
            shot(LEGACY[name], os.path.join(d, 'ic_launcher.png'), '22%')
            shot(LEGACY[name], os.path.join(d, 'ic_launcher_round.png'), '50%')
            shot(FG[name], os.path.join(d, 'ic_launcher_foreground.png'), '0')
        br.close()
    any_ = os.path.join(RES, 'mipmap-anydpi-v26'); os.makedirs(any_, exist_ok=True)
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
           '    <background android:drawable="@color/ic_launcher_background"/>\n'
           '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n</adaptive-icon>\n')
    for n in ('ic_launcher.xml', 'ic_launcher_round.xml'):
        open(os.path.join(any_, n), 'w').write(xml)
    open(os.path.join(RES, 'values', 'ic_launcher_colors.xml'), 'w').write(
        f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">{BG}</color>\n</resources>\n')
    print('app icon ok')

if __name__ == '__main__':
    main()

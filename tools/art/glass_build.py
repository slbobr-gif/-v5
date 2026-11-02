"""Сборка витражей (сцены, существа, финал, онбординг): «сырьё» → glassify → app/assets/art.

Вызывается из build.py --glass. Сырые SVG (прежние плоские рисунки) пишутся в tools/art/raw/,
чтобы конвертацию можно было перезапускать отдельно: python3 tools/art/glassify.py [имя ...]
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')


def collect_raw():
    import scenes, creatures, extras
    out = {}
    for k, fn in scenes.SCENES.items():
        out[f'scenes/{k}.svg'] = fn()
    creatures.RING = False
    try:
        for k, fn in creatures.CREATURES.items():
            out[f'creatures/{k}.svg'] = fn()
    finally:
        creatures.RING = True
    for k, fn in extras.ONBOARDING.items():
        out[f'onboarding/{k}.svg'] = fn()
    out['finale/teriberka.svg'] = extras.teriberka()
    return out


def write_raw(raws):
    for rel, svg in raws.items():
        p = os.path.join(RAW, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(svg)


def build(only=None):
    """Возвращает dict rel -> витражный SVG (и обновляет tools/art/raw)."""
    import glassify
    raws = collect_raw()
    write_raw(raws)
    return glassify.run(raws, only)

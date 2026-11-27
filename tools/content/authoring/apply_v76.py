"""V5-76 (28.11): дописанные тексты случайных событий + правки этнографа + свои правки + теги ночных событий + «Рыба».
Порядок: expand_v76/batch_1..4.json → ethno.json → own.json (последний побеждает). Служебные поля (id, zone, tags,
kind, wild, creature, art) всегда берутся из текущего файла. Якорные правки этнографа — ethno_anchored.json.
Запуск из корня:  python3 tools/content/authoring/apply_v76.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / 'app' / 'assets' / 'content'
D = Path(__file__).resolve().parent / 'expand_v76'
KEEP = ('id', 'zone', 'tags', 'kind', 'wild', 'creature', 'art', 'chapter', 'anchor', 'line', 'who')


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def dump(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def merge(events, patches):
    by = {e['id']: i for i, e in enumerate(events)}
    n = 0
    for name, patch in patches:
        k = 0
        for eid, new in patch.items():
            if eid not in by:
                continue
            old = events[by[eid]]
            m = {**new, **{f: old[f] for f in KEEP if f in old}}
            if m != old:
                events[by[eid]] = m
                k += 1
        print(f'{name}: {k}')
        n += k
    return n


rnd = load(C / 'events_random.json')
patches = [(p.name, load(p)) for p in sorted(D.glob('batch_*.json'))]
for extra in ('ethno.json', 'own.json'):
    if (D / extra).exists():
        patches.append((extra, load(D / extra)))
print('случайные, изменено всего:', merge(rnd, patches))

# Ночные события «любой главы» не выпадают в белые ночи (главы 3–4)
for e in rnd:
    if 'night' in e['tags'] and 'any' in e['tags']:
        e['tags'] = [t for t in e['tags'] if t != 'any'] + ['ch1', 'ch2', 'ch5', 'ch6']
        print('ночь без белых ночей:', e['id'])
dump(C / 'events_random.json', rnd)

if (D / 'ethno_anchored.json').exists():
    ea = load(D / 'ethno_anchored.json')
    for ch in range(1, 7):
        f = C / f'events_ch{ch}.json'
        evs = load(f)
        if merge(evs, [(f'ethno_anchored → ch{ch}', ea)]):
            dump(f, evs)

# «Копчёная рыба» → «Рыба»: события дают и свежий улов, и копчёную
t = (C / 'items.json').read_text(encoding='utf-8')
old = '{"id": "fish", "name": "Копчёная рыба", "desc": "Подарок с реки."}'
if old in t:
    t = t.replace(old, '{"id": "fish", "name": "Рыба", "desc": "Свежая с реки или копчёная у рыбаков — всё одно еда."}')
    (C / 'items.json').write_text(t, encoding='utf-8')
    print('рыба переименована')

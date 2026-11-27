"""Ревью случайных событий (V5-75, 27.11): правки агентов-квест-архитекторов → events_random.json.
Правки лежат в review_v75/batch_<n>.json как {id: полное исправленное событие}. Поля, которые
не должны меняться при ревью (id, zone, tags, kind, wild, creature, art), берутся из оригинала.
Запуск из корня репозитория:  python3 tools/content/authoring/apply_review_v75.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / 'app' / 'assets' / 'content' / 'events_random.json'
R = Path(__file__).resolve().parent / 'review_v75'
KEEP = ('id', 'zone', 'tags', 'kind', 'wild', 'creature', 'art')

ev = json.loads(F.read_text(encoding='utf-8'))
by = {e['id']: i for i, e in enumerate(ev)}
total = 0
for b in sorted(R.glob('batch_*.json')):
    patch = json.loads(b.read_text(encoding='utf-8'))
    n = 0
    for eid, new in patch.items():
        if eid not in by:
            print(f'{b.name}: нет события {eid} — пропущено')
            continue
        old = ev[by[eid]]
        merged = {**new, **{k: old[k] for k in KEEP if k in old}}
        if merged != old:
            ev[by[eid]] = merged
            n += 1
    print(f'{b.name}: изменено {n}')
    total += n
F.write_text(json.dumps(ev, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('всего изменено:', total)

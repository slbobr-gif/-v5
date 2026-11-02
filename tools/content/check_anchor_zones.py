"""Проверка зон якорных событий и шагов квестов (docs/v5/07-change-request-v5.3.md, «Зоны пути»).

Запуск из корня репозитория:  python3 tools/content/check_anchor_zones.py [--errors-only]

Печатает таблицу  id | км | зона по карте | заявленная зона | запас | OK/ОШИБКА.
* Якорное событие: км = placeDistances[after]/1000 + anchor.km (zones.anchor_km).
* Шаг квеста (и каждая ветка финала): км = км якорного события, которое запускает квест
  (effects.quest_start), + at_km шага — так же считает движок (startPos + at_km).
* detour_only — конец ответвления, на маршруте не стоит; печатается для справки (зона по якорю),
  но ошибкой не считается (так же, как в validate.py).
* «запас» — сколько км до ближайшей смены зоны по маршруту: если < 0,5 км, правка радиусов в
  balance.json легко перевернёт зону — печатается пометка «у границы».
Код выхода 1, если есть хоть одна ОШИБКА. Внизу — сводка: сколько событий в каждой зоне.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zones import ZONES, LABELS, anchor_km, zone_at  # noqa: E402

C = HERE.parents[1] / 'app' / 'assets' / 'content'
ERRORS_ONLY = '--errors-only' in sys.argv


def load(name):
    return json.loads((C / name).read_text(encoding='utf-8'))


def quest_starts(e):
    for c in e.get('choices', []):
        for o in c.get('outcomes', []):
            q = (o.get('effects') or {}).get('quest_start')
            if q:
                yield q


def margin_km(km, zone, reach=3.0, step=0.05):
    """Расстояние до ближайшей точки маршрута с другой зоной (не дальше reach км)."""
    k = step
    while k <= reach + 1e-9:
        if zone_at(km - k) != zone or zone_at(km + k) != zone:
            return k
        k += step
    return reach


rows = []  # (км, id, откуда, зона по карте, заявленная, считать ли ошибкой)
starts = {}
for f in load('index.json')['anchored']:
    for e in load(f):
        km = anchor_km(e['anchor'])
        for q in set(quest_starts(e)):  # квест может запускаться из нескольких исходов одного события
            starts.setdefault(q, []).append((km, e['id']))
        rows.append((km, e['id'], f + (' (ответвление)' if e.get('detour_only') else ''),
                     zone_at(km), e.get('zone'), not e.get('detour_only')))

problems = []
for q in load('quests.json'):
    st = starts.get(q['id'])
    if not st:
        problems.append(f"квест {q['id']}: его не запускает ни одно якорное событие — позицию шагов не посчитать")
        continue
    for skm, sid in st:
        for s in q['steps']:
            km = skm + s['at_km']
            evs = [s['event']] if 'event' in s else [b['event'] for b in s.get('branches', [])]
            for ev in evs:
                rows.append((km, ev['id'], f"{q['id']}/{s['id']} (старт {sid}, +{s['at_km']} км)",
                             zone_at(km), ev.get('zone'), True))

rows.sort(key=lambda r: r[0])
n_err = 0
counts = {z: 0 for z in ZONES}
counts_anchor = {z: 0 for z in ZONES}
lines = []
for km, eid, where, real, declared, strict in rows:
    ok = declared == real
    m = margin_km(km, real)
    status = 'OK' if ok else ('ОШИБКА' if strict else 'справка')
    if not ok and strict:
        n_err += 1
    if declared in counts:
        counts[declared] += 1
        if '/' not in where:
            counts_anchor[declared] += 1
    note = ' · у границы' if m < 0.5 else ''
    if ERRORS_ONLY and status == 'OK':
        continue
    lines.append(f"{eid:<30} | {km:7.1f} | {real:<6} | {str(declared):<6} | {m:4.2f} км{note:<13} | {status:<7} | {where}")

print(f"{'id':<30} | {'км':>7} | {'карта':<6} | {'заявл.':<6} | {'запас':<20} | {'итог':<7} | где")
print('-' * 120)
print('\n'.join(lines))
for p in problems:
    print('ОШИБКА:', p)
    n_err += 1
print('-' * 120)
print('Якорные события по зонам:  ' + ' · '.join(f"{LABELS[z]} {counts_anchor[z]}" for z in ZONES))
print('Вместе с шагами квестов:   ' + ' · '.join(f"{LABELS[z]} {counts[z]}" for z in ZONES))
print(f"Ошибок: {n_err}")
sys.exit(1 if n_err else 0)

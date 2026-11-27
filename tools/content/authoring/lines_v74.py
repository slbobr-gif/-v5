"""Три сквозные линии (V5-74, 27.11): родители, Саша, раздумья. Запуск из корня репозитория:
    python3 tools/content/authoring/lines_v74.py

Что делает (идемпотентно — повторный запуск даёт тот же результат):
* сцены линий — якорные события в events_ch1..6.json с полем "line": parents | sasha | life;
  место на маршруте подбирается автоматически: нужная зона (zones.py), ≥ GAP км от соседних событий,
  ≥ 0,6 км до границы зоны; переписанные старые семейные события сохраняют id и якорь;
* открытый ответ ставит флаг bond_mama_* / bond_papa_* / care_sasha_* — из них приложение считает
  скрытые счётчики (близость с мамой и папой, понимание с Сашей) и выбирает финальные страницы эпилога;
* раздумья — kind "reflection": один вариант «Идти дальше», его исход = выделенная мысль-ориентир;
* финальные страницы — chapters.json[6].lineEpilogue {parents: [...], sasha: [...]}, у каждой min по счётчику;
* слова-маркеры зон в воспоминаниях и разговорах по телефону → zone_note (это не место действия).
Канон и концепт — док «Путник — три сквозные линии: концепт», docs/00-decisions.md V5-74.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / 'app' / 'assets' / 'content'
sys.path.insert(0, str(ROOT / 'tools' / 'content'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zones import anchor_km, zone_at, _DIST  # noqa: E402
from check_random_zones import load_words  # noqa: E402

import lines_parents  # noqa: E402
import lines_sasha  # noqa: E402
import lines_life  # noqa: E402

GAP = 4.0
NOTE = 'Слова-маркеры здесь — в воспоминании или в разговоре по телефону, а не место действия.'


def load(name):
    return json.loads((C / name).read_text(encoding='utf-8'))


def save(name, data):
    (C / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


places = load('places.json')
P = places if isinstance(places, list) else places['places']
PLACE_KM = sorted((_DIST[p['id']] / 1000.0, p['id'], p.get('chapter')) for p in P if p['id'] in _DIST)
CH_START = {1: 0.0}
for ch in range(2, 7):
    CH_START[ch] = max(k for k, _, c in PLACE_KM if c == ch - 1)
CH_END = {ch: max(k for k, _, c in PLACE_KM if c == ch) for ch in range(1, 7)}

WORDS, _, _ = load_words()


def markers(e):
    txt = ' '.join([e['title'], e['text']] + [c['text'] for c in e['choices']] +
                   [o['text'] for c in e['choices'] for o in c['outcomes']]).lower()
    return sorted({m for m in WORDS.get(e['zone'], []) if re.search(r'(?<![а-яёa-z])' + re.escape(m), txt)})


def margin(km, zone, reach=1.0, step=0.1):
    k = step
    while k <= reach:
        if zone_at(km - k) != zone or zone_at(km + k) != zone:
            return k
        k += step
    return reach


ALT = {'suburb': ['city'], 'city': ['suburb'], 'wild': []}


def find_spot(ch, target, zone, taken):
    """Ближайшая к target точка главы в зоне zone (или соседней городской), свободная от событий на GAP км.
    Возвращает (anchor, км, зона). Если тесно — зазор уменьшается до 2,5 км."""
    for gap in (GAP, 3.0, 2.5):
        for z in [zone] + ALT[zone]:
            r = _find(ch, target, z, taken, gap)
            if r:
                return (*r, z)
    raise SystemExit(f'нет места: глава {ch}, около {target} км, зона {zone}')


def _find(ch, target, zone, taken, gap):
    lo, hi = CH_START[ch] + 3, CH_END[ch] - 3
    best = None
    for i in range(0, 130):
        for sgn in (1, -1):
            km = round((target + sgn * i * 0.5) * 2) / 2
            if not lo <= km <= hi:
                continue
            if zone_at(km) != zone or margin(km, zone) < 0.6:
                continue
            if any(abs(km - t) < gap for t in taken) or abs(km - target) > 60:
                continue
            best = km
            break
        if best is not None:
            break
    if best is None:
        return None
    after = max((k, pid) for k, pid, _ in PLACE_KM if k <= best)
    off = round(best - after[0], 1)
    if off > 200:
        raise SystemExit(f'якорь дальше 200 км от {after[1]}')
    return {'after': after[1], 'km': off}, best


def build_event(sc, anchor, zone):
    e = {
        'id': sc['id'], 'kind': sc.get('kind', 'regional'), 'chapter': sc['ch'], 'anchor': anchor, 'zone': zone,
        'once': True, 'art': sc['art'], 'creature': None, 'line': sc['line'],
        'title': sc['title'], 'text': sc['text'].strip(),
    }
    if sc['line'] == 'life':
        e['kind'] = 'reflection'
        e['choices'] = [{'id': 'go', 'text': 'Идти дальше', 'risk': 'none',
                         'outcomes': [{'weight': 1, 'text': sc['thought'].strip(), 'effects': {}}]}]
    else:
        e['who'] = sc.get('who', 'sasha')
        e['choices'] = []
        for cid, text, out, flag in sc['choices']:
            eff = {'flag': flag} if flag else {}
            e['choices'].append({'id': cid, 'text': text, 'risk': 'none',
                                 'outcomes': [{'weight': 1, 'text': out.strip(), 'effects': eff}]})
    m = markers(e)
    if m:
        e['zone_note'] = NOTE
    return e


def main():
    files = {ch: f'events_ch{ch}.json' for ch in range(1, 7)}
    data = {ch: load(f) for ch, f in files.items()}
    # чистый прогон: убрать сцены прошлых запусков (новые id линий), переписанные старые заменятся по id
    new_ids = set()
    scenes = lines_parents.SCENES + lines_sasha.SCENES + lines_life.SCENES
    ids = [s['id'] for s in scenes]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit(f'повтор id: {dup}')
    for ch in data:
        data[ch] = [e for e in data[ch] if not (e.get('line') and not e.get('rewritten'))]
    taken = []
    for ch, evs in data.items():
        taken += [anchor_km(e['anchor']) for e in evs]
    for f in ('events_ch1_quests.json', 'events_ch2_quests.json'):
        taken += [anchor_km(e['anchor']) for e in load(f)]
    stats = {}
    for sc in scenes:
        ch = sc['ch']
        old = next((e for e in data[ch] if e['id'] == sc['id']), None)
        if old is not None:  # переписываем старое событие: якорь, зона и картинка — прежние
            anchor, zone = old['anchor'], old['zone']
            sc = {**sc, 'art': sc.get('art') or old['art']}
            e = build_event(sc, anchor, zone)
            e['rewritten'] = True
            data[ch][data[ch].index(old)] = e
        else:
            anchor, km, zone = find_spot(ch, sc['km'], sc['zone'], taken)
            taken.append(km)
            e = build_event(sc, anchor, zone)
            data[ch].append(e)
            new_ids.add(sc['id'])
        stats.setdefault((ch, sc['line']), 0)
        stats[(ch, sc['line'])] += 1
    for ch, evs in data.items():
        evs.sort(key=lambda e: anchor_km(e['anchor']))
        save(files[ch], evs)
    # финальные страницы эпилога
    chs = load('chapters.json')
    lst = chs if isinstance(chs, list) else chs['chapters']
    lst[-1]['lineEpilogue'] = {'parents': lines_parents.EPILOGUE, 'sasha': lines_sasha.EPILOGUE}
    save('chapters.json', chs)
    # случайное «Прогноз от мамы» — в тон линии (не раньше главы 3)
    rnd = load('events_random.json')
    for e in rnd:
        if e['id'] in lines_parents.RANDOM_REWRITE:
            e.update(lines_parents.RANDOM_REWRITE[e['id']])
    save('events_random.json', rnd)
    for (ch, line), n in sorted(stats.items()):
        print(f'глава {ch}: {line} — {n}')
    print('всего сцен:', len(scenes), '| новых:', len(new_ids))


if __name__ == '__main__':
    main()

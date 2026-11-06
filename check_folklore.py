"""Проверка фольклорных линий (quests.json, kind "folklore"; docs/v5/07-change-request-v5.3.md, п. 24).

Запуск из корня репозитория:  python3 tools/content/check_folklore.py

Для каждой линии перебирает ВСЕ комбинации «вариант × исход» по шагам-заданиям, считает итоговый
quest_var favor и смотрит, какая ветка финала выиграет (первая подходящая, как в движке).
Печатает долю каждого исхода (kind / cunning / angry) двумя способами:
  * по комбинациям — каждая комбинация вариантов и исходов равновесна;
  * по вероятности — варианты выбираются поровну, исходы — по weight (исходы со смертью не считаются).
Ошибка, если: ветка недостижима или < 20 % хотя бы одним способом; финал не из трёх веток
kind/cunning/angry (mood) с запасной последней; у шага нет creature/mood или creature чужая;
mood шага не neutral; в стартовом (не квестовом) событии стоит quest_var favor — движок применил бы
его ко всем активным квестам сразу; дар (give в финале, кроме обычных предметов каталога) не описан в docs/v5/folklore-gifts.md.
"""
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'app' / 'assets' / 'content'
DOC = ROOT / 'docs' / 'v5' / 'folklore-gifts.md'
MIN_SHARE = 0.2
load = lambda n: json.loads((C / n).read_text(encoding='utf-8'))
errors = []


def cond(v, c):
    m = re.fullmatch(r'(>=|<=|==|>|<)(-?\d+)', c)
    op, n = m.group(1), int(m.group(2))
    return {'>=': v >= n, '<=': v <= n, '==': v == n, '>': v > n, '<': v < n}[op]


known_items = {i['id'] for i in load('items.json')}
doc_ids = set(re.findall(r'^\|\s*`([a-z_]+)`', DOC.read_text(encoding='utf-8'), re.M)) if DOC.exists() else set()
if not DOC.exists():
    errors.append('нет docs/v5/folklore-gifts.md')

for f in load('index.json')['anchored']:
    for e in load(f):
        for c in e.get('choices', []):
            for o in c.get('outcomes', []):
                if 'favor' in ((o.get('effects') or {}).get('quest_var') or {}):
                    errors.append(f"{f}:{e['id']}: quest_var favor в обычном событии — попадёт во все активные квесты")

for q in load('quests.json'):
    if q.get('kind') != 'folklore':
        continue
    qid, cr = q['id'], q.get('creature')
    tasks = [s['event'] for s in q['steps'] if 'event' in s]
    final = q['steps'][-1]
    br = final.get('branches', [])
    moods = [b['event'].get('mood') for b in br]
    if moods != ['kind', 'cunning', 'angry'] or (br and br[-1].get('if') != {}):
        errors.append(f"{qid}: финал должен быть [kind, cunning, angry] с запасной последней, есть {moods}")
    for ev in tasks + [b['event'] for b in br]:
        if ev.get('creature') != cr:
            errors.append(f"{qid}:{ev['id']}: creature {ev.get('creature')!r}, а линия {cr!r}")
    for ev in tasks:
        if ev.get('mood') != 'neutral':
            errors.append(f"{qid}:{ev['id']}: у шага-задания mood должен быть neutral")
    for b in br:
        for c in b['event']['choices']:
            for o in c['outcomes']:
                for it in (o['effects'].get('give') or {}):
                    if it not in doc_ids and (it not in known_items or it == 'ball_yaga'):
                        errors.append(f"{qid}:{b['event']['id']}: дар {it} не описан в folklore-gifts.md")
    per = []
    for ev in tasks:
        opts = []
        for c in ev['choices']:
            tw = sum(o['weight'] for o in c['outcomes'])
            for o in c['outcomes']:
                if not o['effects'].get('death'):
                    opts.append(((o['effects'].get('quest_var') or {}).get('favor', 0), o['weight'] / tw / len(ev['choices'])))
        per.append(opts)
    combos = list(itertools.product(*per))
    cnt = {m: 0.0 for m in ('kind', 'cunning', 'angry')}
    prob = dict(cnt)
    lo, hi = 10 ** 9, -10 ** 9
    for cb in combos:
        fv = sum(x for x, _ in cb)
        lo, hi = min(lo, fv), max(hi, fv)
        p = 1.0
        for _, w in cb:
            p *= w
        win = next(b for b in br if all(cond(fv, c) for c in b['if'].values()))['event'].get('mood')
        cnt[win] += 1.0 / len(combos)
        prob[win] += p
    tp = sum(prob.values())
    for m in prob:
        prob[m] /= tp
    conds = ' · '.join(f"{b['event'].get('mood')}: {b['if'].get('favor', 'иначе')}" for b in br)
    print(f"{qid:<13} заданий {len(tasks)}, комбинаций {len(combos):>4}, favor {lo}..{hi} | {conds}")
    print(f"{'':13} по комбинациям " + ' '.join(f"{m} {cnt[m] * 100:3.0f}%" for m in cnt) +
          " | по вероятности " + ' '.join(f"{m} {prob[m] * 100:3.0f}%" for m in prob))
    for m in cnt:
        if cnt[m] < MIN_SHARE or prob[m] < MIN_SHARE:
            errors.append(f"{qid}: исход {m} — {cnt[m] * 100:.0f}% комбинаций / {prob[m] * 100:.0f}% вероятности (< {MIN_SHARE * 100:.0f}%)")

for e in errors:
    print('ОШИБКА:', e)
print(f"Ошибок: {len(errors)}")
sys.exit(1 if errors else 0)

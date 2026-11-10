#!/usr/bin/env python3
"""Проверка пулов случайных событий по зонам (docs/v5/07-change-request-v5.3.md, «Зоны пути»).

Запуск из корня репозитория:  python3 tools/content/check_random_zones.py [--quiet]

Печатает размеры пулов по зонам и главам, найденные слова-маркеры (tools/content/zone_words.json)
и возвращает код 1, если есть нарушения:
  * у события нет зоны или она не city/suburb/wild;
  * в пуле зоны меньше событий, чем нужно (город 14, пригород 16, окрестности 16), или меньше 4 событий с тегом any;
  * в зоне больше 2 событий с существами, доступных в одной главе (тег главы или any), или больше 1 события с риском смерти (risk: fatal);
  * id вида rnd_city_*/rnd_sub_*/rnd_wild_* не совпадает с зоной;
  * в тексте события зоны есть запрещённая для неё основа слова, а поля zone_note нет
    (при zone_note маркеры только перечисляются; если маркеров нет — предупреждение «лишний zone_note»);
  * слов-маркеров в списках *_forbidden и city/suburb/wild (их читает validate.py) разное содержимое;
  * семья героя (Александра/Саша, Илья, Честер) упомянута больше чем в MAX_FAMILY событиях, доступных в одной главе;
  * в тексте есть конкретный топоним (TOPONYMS) или северные реалии без тега ch3+ (NORTH);
  * предмет gas выдаётся больше чем в 3 событиях или стоит в requires.
Предупреждения (не ломают сборку): текст события вне 500–900 знаков, устаревшие теги village/town,
в главе меньше 8 событий в зоне (пул быстро «выедается»).

Из других скриптов:  from check_random_zones import find_markers
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / 'app' / 'assets' / 'content' / 'events_random.json'
WORDS = ROOT / 'tools' / 'content' / 'zone_words.json'
ZONES = ('city', 'suburb', 'wild')
LABEL = {'city': 'Город', 'suburb': 'Пригород', 'wild': 'Окрестности'}
MIN_POOL = {'city': 32, 'suburb': 38, 'wild': 40}
MIN_ANY = 8
MAX_CREATURE = 3  # V5-53: на севере духов больше
MAX_FATAL = 2
MAX_FAMILY = 10
CHS = ('ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6')
MAX_GAS = 6
CHAPTER_WARN = 12
PREFIX = {'rnd_city_': 'city', 'rnd_sub_': 'suburb', 'rnd_wild_': 'wild'}
# Случайные события выпадают где угодно, поэтому конкретных мест в них нет (жалоба владельца 04.11:
# «Свадьба на мосту над Волгой» сразу после Москвы). Корни топонимов, регистр не важен, совпадение
# с начала слова. Териберка (цель пути) и направление «на север» разрешены — они верны везде.
TOPONYMS = re.compile(r'(?<![а-яё])(' + '|'.join([
    'москв', 'кремл', 'мкад', 'подмоск', 'зеленоград', 'химк', 'солнечногор', 'клин(?![а-яё])', 'клину', 'клина(?![а-яё])',
    'ленинград', 'питер', 'петербург', 'тверь', 'твери(?![а-яё])', 'тверск', 'тверц', 'торжк', 'торжок', 'вышн[а-яё]* волоч',
    'волг[аиеуой](?![а-яё])', 'волгой', 'ок[аеиу](?![а-яё])', 'окой', 'мст[аеуы](?![а-яё])', 'мстой', 'нев[аеуы](?![а-яё])', 'невой', 'свир',
    'валда', 'ильмен', 'ладог', 'ладож', 'онег', 'онеж', 'селигер', 'сенеж', 'московск', 'новгород', 'борович', 'окуловк',
    'карел', 'кольск', 'мурманск', 'кандалакш', 'беломор', 'хибин', 'байкал', 'столиц',
    'м-10', 'м-11', 'р-21', 'e-105', 'е-105',
]) + r')', re.I)
# Северные реалии — только в событиях с тегом северных глав (ch3+).
NORTH = re.compile(r'(?<![а-яё])(сияни|северн[а-яё]* сияни|белы[ехм] ноч|бел[ао]й ноч|тундр|морошк|полярн)', re.I)
NORTH_TAGS = {'ch3', 'ch4', 'ch5', 'ch6'}
FAMILY = re.compile(r'(?<![а-яё])(александр|саш[аиеуой]|илья|илью|илье|ильи|честер)', re.I)


def load_words():
    data = json.loads(WORDS.read_text(encoding='utf-8'))
    note = data.get('allow_note_field', 'zone_note')
    words = {z: [w.strip().lower() for w in data.get(z + '_forbidden', []) if w.strip()] for z in ZONES}
    mirror = {z: [w.strip().lower() for w in data.get(z, []) if isinstance(w, str) and w.strip()] for z in ZONES}
    return words, mirror, note


def event_text(e):
    parts = [e.get('title', ''), e.get('text', '')]
    for c in e.get('choices', []):
        parts.append(c.get('text', ''))
        for o in c.get('outcomes', []):
            parts.append(o.get('text', ''))
    return ' \n '.join(parts).lower()


def find_markers(e, words):
    """Основы слов, запрещённые для зоны события и встреченные в его тексте (с начала слова)."""
    z = e.get('zone')
    txt = event_text(e)
    return sorted({m for m in words.get(z, []) if re.search(r'(?<![а-яёa-z])' + re.escape(m), txt)})


def main():
    quiet = '--quiet' in sys.argv
    words, mirror, note_field = load_words()
    events = json.loads(EVENTS.read_text(encoding='utf-8'))
    bad, warn, info = [], [], []

    for z in ZONES:
        if words[z] != mirror[z]:
            bad.append(f'zone_words.json: списки {z}_forbidden и {z} расходятся (validate.py читает «{z}»)')

    pool = {z: [] for z in ZONES}
    for e in events:
        z = e.get('zone')
        if z not in ZONES:
            bad.append(f"{e.get('id')}: нет зоны или неверная зона {z!r}")
            continue
        pool[z].append(e)
        for pre, pz in PREFIX.items():
            if e['id'].startswith(pre) and pz != z:
                bad.append(f"{e['id']}: id говорит о зоне {pz}, а zone = {z}")
        tags = e.get('tags', [])
        if 'any' not in tags and not any(t in ('ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6') for t in tags):
            bad.append(f"{e['id']}: нет ни тега any, ни тега главы — событие нигде не выпадет")
        for t in ('village', 'town'):
            if t in tags:
                warn.append(f"{e['id']}: устаревший тег {t} (за место отвечает zone)")
        n = len(e.get('text', ''))
        if not 500 <= n <= 900:
            warn.append(f"{e['id']}: текст {n} знаков (цель 500–900)")
        flat = event_text(e).replace('\n', ' ')
        topo = sorted({m.group(0) for m in TOPONYMS.finditer(flat)})
        if topo:
            bad.append(f"{e['id']}: конкретные места в случайном событии: {', '.join(topo)} — замените на «река», «трасса», «городок»")
        north = sorted({m.group(0) for m in NORTH.finditer(flat)})
        if north and not NORTH_TAGS & set(tags):
            bad.append(f"{e['id']}: северные реалии ({', '.join(north)}) без тега северной главы")
        found = find_markers(e, words)
        has_note = isinstance(e.get(note_field), str) and e[note_field].strip()
        if found and not has_note:
            bad.append(f"{e['id']} [{z}]: маркеры {', '.join(found)} — перепишите или добавьте {note_field}")
        elif found and has_note:
            info.append(f"{e['id']} [{z}]: маркеры {', '.join(found)} разрешены ({note_field}: {e[note_field]})")
        elif has_note:
            warn.append(f"{e['id']}: лишний {note_field} — маркеров в тексте нет")

    print('Пулы случайных событий по зонам')
    print(f"{'зона':<12}{'всего':>6}{'any':>5}{'только ch1':>11}{'только ch2':>11}{'доступно ch1':>14}{'доступно ch2':>14}{'risk':>6}{'существа':>10}{'смерть':>8}")
    for z in ZONES:
        p = pool[z]
        n_any = sum('any' in e['tags'] for e in p)
        only = lambda ch: sum(ch in e['tags'] and 'any' not in e['tags'] for e in p)
        avail = lambda ch: sum(ch in e['tags'] or 'any' in e['tags'] for e in p)
        risk = sum('risk' in e['tags'] for e in p)
        crea = [e['id'] for e in p if e.get('creature')]
        crea_ch = {ch: [e['id'] for e in p if e.get('creature') and (ch in e['tags'] or 'any' in e['tags'])] for ch in CHS}
        fatal = [e['id'] for e in p if any(c.get('risk') == 'fatal' for c in e['choices'])]
        print(f"{LABEL[z]:<12}{len(p):>6}{n_any:>5}{only('ch1'):>11}{only('ch2'):>11}{avail('ch1'):>14}{avail('ch2'):>14}{risk:>6}{len(crea):>10}{len(fatal):>8}")
        if len(p) < MIN_POOL[z]:
            bad.append(f'зона {z}: событий {len(p)} < {MIN_POOL[z]}')
        if n_any < MIN_ANY:
            bad.append(f'зона {z}: событий с тегом any {n_any} < {MIN_ANY}')
        for ch, ids in crea_ch.items():
            if len(ids) > MAX_CREATURE:
                bad.append(f"зона {z}, глава {ch[2]}: событий с существами {len(ids)} > {MAX_CREATURE} ({', '.join(ids)})")
        if len(fatal) > MAX_FATAL:
            bad.append(f"зона {z}: событий с риском смерти {len(fatal)} > {MAX_FATAL} ({', '.join(fatal)})")
        print('            ' + '  '.join(f'гл.{ch[2]}: {avail(ch)}' for ch in CHS))
        for ch in CHS:
            if avail(ch) < CHAPTER_WARN:
                warn.append(f'зона {z}, глава {ch[2]}: доступно только {avail(ch)} событий (< {CHAPTER_WARN})')
        if crea and not quiet:
            info.append(f"существа в зоне {z}: {', '.join(crea)}")
        if fatal and not quiet:
            info.append(f"смерть в зоне {z}: {', '.join(fatal)}")

    fam = [e for e in events if FAMILY.search(event_text(e).replace('\n', ' '))]
    print(f'Семья героя упомянута в {len(fam)} событиях: {", ".join(e["id"] for e in fam)}')
    for ch in CHS:
        n = sum(ch in e['tags'] or 'any' in e['tags'] for e in fam)
        if n > MAX_FAMILY:
            bad.append(f'глава {ch[2]}: семья героя упомянута в {n} доступных событиях > {MAX_FAMILY}')
    gas = [e['id'] for e in events if any('gas' in (o.get('effects', {}).get('give') or {})
                                          for c in e['choices'] for o in c['outcomes'])]
    print(f'Выдают gas ({len(gas)}): {", ".join(gas)}')
    if len(gas) > MAX_GAS:
        bad.append(f'gas выдаётся в {len(gas)} событиях > {MAX_GAS}')
    for e in events:
        for c in e['choices']:
            if (c.get('requires') or {}).get('item') == 'gas':
                bad.append(f"{e['id']}/{c['id']}: gas в requires не используем")

    if not quiet:
        for s in info:
            print('  инфо:', s)
        for s in warn:
            print('  предупреждение:', s)
    else:
        print(f'  предупреждений: {len(warn)}')
    for s in bad:
        print('НАРУШЕНИЕ:', s)
    print(f'Всего событий: {len(events)}; нарушений: {len(bad)}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

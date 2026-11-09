"""Сборка контента глав 3–6: короткие конструкторы событий + запись JSON и проверка зон."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'content'))
import zones as Z  # noqa: E402

C_DIR = ROOT / 'app' / 'assets' / 'content'


def O(w, text, **eff):
    return {'weight': w, 'text': text, 'effects': eff}


def C(cid, text, outs, risk='none', requires=None):
    c = {'id': cid, 'text': text, 'risk': risk, 'outcomes': outs}
    if requires:
        c['requires'] = requires
    return c


def E(eid, ch, after, km, art, title, text, choices, kind='regional', creature=None, mood=None, zone_note=None):
    zone = Z.anchor_zone({'after': after, 'km': km})
    zone = zone[0] if isinstance(zone, tuple) else zone
    e = {'id': eid, 'kind': kind, 'chapter': ch, 'anchor': {'after': after, 'km': km}, 'zone': zone, 'once': True,
         'art': art, 'creature': creature}
    if mood:
        e['mood'] = mood
    if zone_note:
        e['zone_note'] = zone_note
    e.update({'title': title, 'text': text, 'choices': choices})
    return e


def R(eid, zone, tags, art, title, text, choices, creature=None, mood=None):
    e = {'id': eid, 'kind': 'random', 'zone': zone, 'tags': tags, 'once': False, 'art': art, 'creature': creature}
    if mood:
        e['mood'] = mood
    e.update({'title': title, 'text': text, 'choices': choices})
    return e


def write_anchored(name, events):
    (C_DIR / name).write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(name, len(events), [(e['id'], e['zone']) for e in events])

"""Встречи с дикими зверями (V5-64): 30 событий с "wild": true в events_random.json.

Движок выбирает их отдельно от обычных случайных: вне города, не больше двух за главу, каждый зверь раз за путь,
сначала те, кого игрок не встречал в прошлых путях. Запуск: python3 tools/content/authoring/content_wild.py
(перезаписывает все события wild_* в events_random.json, остальные не трогает)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from content_wild_a import EVENTS_A  # noqa: E402
from content_wild_b import EVENTS_B  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PATH = os.path.join(ROOT, "app", "assets", "content", "events_random.json")


def W(eid, zone, tags, art, title, text, choices):
    out = []
    for ch in choices:
        cid, ctext, risk, outs = ch[:4]
        c = {"id": cid, "text": ctext}
        if len(ch) > 4:
            c["requires"] = ch[4]
        c["risk"] = risk
        c["outcomes"] = [{"weight": w, "text": t, "effects": eff} for (w, t, eff) in outs]
        out.append(c)
    return {
        "id": eid, "kind": "random", "wild": True, "zone": zone, "tags": tags, "once": False, "art": art,
        "creature": None, "title": title, "text": text, "choices": out,
    }


def main():
    events = [W(*e) for e in EVENTS_A + EVENTS_B]
    ids = [e["id"] for e in events]
    assert len(ids) == len(set(ids)) == 30, len(ids)
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    data = [e for e in data if not e["id"].startswith("wild_")] + events
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"wild: {len(events)} событий, всего случайных {len(data)}")


if __name__ == "__main__":
    main()

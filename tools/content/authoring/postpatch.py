"""Правки поверх сгенерированного контента. Запускать ПОСЛЕ всех content_*.py (они перезаписывают JSON).
Идемпотентно: повторный запуск ничего не меняет.

V5-61: в вариантах, где Сергей отдаёт одну монету («бросить монету», «оставить монетку»),
плата — 1 монета (уровень `coin`), а не 5 (`small`).
"""
import json
import re
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[3] / "app" / "assets" / "content"
ONE_COIN = re.compile(r"монет(у|ку|кой|ой)\b|монетк", re.I)
FILES = ["events_ch1.json", "events_ch2.json", "events_ch3.json", "events_ch4.json", "events_ch5.json",
         "events_ch6.json", "events_random.json", "events_ch1_quests.json", "events_ch2_quests.json",
         "quests.json"]


def events_in(data):
    """Все события файла, включая шаги и ветки квестов."""
    for x in data:
        if "steps" in x:
            for s in x["steps"]:
                if "event" in s:
                    yield s["event"]
                for b in s.get("branches", []):
                    yield b["event"]
        else:
            yield x


def one_coin(ev) -> int:
    n = 0
    for c in ev.get("choices", []):
        if not ONE_COIN.search(c.get("text", "")):
            continue
        req = c.get("requires") or {}
        if req.get("coins") == "small":
            req["coins"] = "coin"
            n += 1
        for o in c.get("outcomes", []):
            if o.get("effects", {}).get("coins") == "-small":
                o["effects"]["coins"] = "-coin"
                n += 1
    return n


def main():
    total = 0
    for fn in FILES:
        p = CONTENT / fn
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        n = sum(one_coin(e) for e in events_in(data))
        if n:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        total += n
        print(f"{fn}: {n} правок «одна монета»")
    print("всего", total)


if __name__ == "__main__":
    main()

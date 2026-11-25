"""25.11: 80 случайных событий севера (главы 3–6): по 25 на главы 3–5 и 5 на главу 6.

Только своих глав (без тега any), чтобы с правилом «в одном пути без повторов» север не пустел.
Идемпотентно: события с этими id заменяются. Запуск после content_north_more.py, перед postpatch.py.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import north80_ch3  # noqa: E402
import north80_ch4  # noqa: E402
import north80_ch5  # noqa: E402
import north80_ch6  # noqa: E402

F = Path(__file__).resolve().parents[3] / "app" / "assets" / "content" / "events_random.json"
EVENTS = north80_ch3.EVENTS + north80_ch4.EVENTS + north80_ch5.EVENTS + north80_ch6.EVENTS


def main():
    ids = [e["id"] for e in EVENTS]
    assert len(ids) == len(set(ids)), "повтор id"
    data = json.loads(F.read_text())
    have = set(ids)
    data = [e for e in data if e["id"] not in have] + EVENTS
    F.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("северных событий:", len(EVENTS), dict(Counter(e["tags"][0] for e in EVENTS)), "| всего случайных:", len(data))


if __name__ == "__main__":
    main()

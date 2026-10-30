"""Эталонный сценарий для теста совпадения движков (Python ↔ Dart).

Пишет app/test/fixtures/parity.json. Dart-тест app/test/engine_parity_test.dart прогоняет тот же
сценарий и сверяет каждый день. Перегенерировать после любой правки контента или баланса:
    python3 tools/sim/make_parity_fixture.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, load_world, new_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
T0 = 1777622400000  # 2026-05-01 08:00 UTC — фиксированное время, не зависит от часового пояса
DAY = 24 * 3600 * 1000
STEPS = [6000, 9000, 4000, 12000, 0, 7000, 8000, 15000, 3000, 7000,
         9000, 11000, 2000, 7000, 7000, 13000, 0, 9000, 8000, 10000]


def act(e: Engine, now: int):
    """Детерминированный игрок: первый доступный вариант, хлеб на привале."""
    for _ in range(60):
        st = e.s["stop"]
        if not st or st["type"] == "finish":
            return
        if st["type"] == "event":
            ev = e.current_event()
            ch = next(c for c in ev["choices"] if e.choice_available(c))
            e.choose(ch["id"], now)
        elif st["type"] in ("place", "chapter_end"):
            if any(i == "bread" for i, _ in e.market()) and e.s["inv"].get("bread", 0) < 2:
                e.buy("bread", now)
            e.continue_journey(now)
        elif st["type"] == "death":
            e.s["stop"] = None
        e.advance(now)


def main():
    w = load_world(ROOT)
    days = [f"2026-05-{d:02d}" for d in range(1, 32)]
    s = new_state(w, 12345, T0, days[0], 500)
    e = Engine(w, s)
    out = []
    for i, steps in enumerate(STEPS):
        now = T0 + i * DAY + 10 * 3600 * 1000
        e.sync_steps({days[i]: 500 + steps if i == 0 else steps}, now)
        e.claim_login(days[i], now)
        e.advance(now)
        act(e, now)
        out.append({
            "day": days[i],
            "pos": round(s["pos"], 2),
            "buffer": round(s["buffer"], 2),
            "coins": s["coins"],
            "stats": {k: round(v, 3) for k, v in s["stats"].items()},
            "inv": dict(sorted(s["inv"].items())),
            "stop": (s["stop"] or {}).get("type"),
            "deaths": s["deaths"],
            "seen": len(s["seen"]),
            "journal": len(s["journal"]),
            "rng": s["rng"],
        })
    fx = {"t0": T0, "seed": 12345, "baseline": 500, "steps": STEPS, "days": days[:len(STEPS)],
          "routeLengthM": round(w.length, 1), "expected": out}
    p = ROOT / "app" / "test" / "fixtures" / "parity.json"
    p.write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
    last = out[-1]
    print(f"parity: {len(out)} дней, итог {last['pos']/1000:.1f} км, монет {last['coins']}, событий {last['seen']}, смертей {last['deaths']}")


if __name__ == "__main__":
    main()

"""Симулятор баланса «Путника» (Геймдизайнер).

Прогоняет эталонный движок на типичных игроках и печатает, как часто они голодают, гибнут,
сколько копят монет и сколько остановок в день видят.

    python3 tools/sim/simulate.py            # 60 дней, все профили, 30 прогонов на профиль
    python3 tools/sim/simulate.py --days 28 --runs 50
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, load_world, new_state, STATS, MS_HOUR  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# Профили: средние шаги в день, разброс, доля дней без ходьбы, сколько раз в день открывает приложение
PROFILES = {
    "ленивый 3k":    dict(mean=3000, sd=1200, idle=0.15, opens=2),
    "обычный 7k":    dict(mean=7000, sd=2000, idle=0.07, opens=3),
    "активный 12k":  dict(mean=12000, sd=3000, idle=0.05, opens=4),
    "рывками":       dict(mean=6000, sd=5000, idle=0.30, opens=2),
    "забывчивый 7k": dict(mean=7000, sd=2000, idle=0.07, opens=1),
}


class Player:
    """Разумный, но не идеальный игрок."""

    def __init__(self, rnd: random.Random):
        self.r = rnd

    def act(self, eng: Engine, now: int):
        for _ in range(40):
            st = eng.s["stop"]
            if not st:
                return
            t = st["type"]
            if t == "event":
                ev = eng.current_event()
                if ev is None:
                    eng.s["stop"] = None
                    continue
                choices = [c for c in ev["choices"] if eng.choice_available(c)]
                safe = [c for c in choices if eng.choice_risk(c) != "fatal"]
                # 4% импульсивных рискованных решений
                pool = choices if (not safe or self.r.random() < 0.04) else safe
                c = self.r.choice(pool)
                eng.choose(c["id"], now)
            elif t in ("place", "chapter_end"):
                self.shop(eng, now)
                eng.continue_journey(now)
            elif t == "death":
                eng.s["stop"] = None
            elif t == "finish":
                return
            eng.advance(now)

    def shop(self, eng: Engine, now: int):
        prices = dict(eng.market())
        if not prices:
            return
        want = [("stew", 1), ("bread", 2), ("water", 3), ("tea", 1)]
        for item, n in want:
            for _ in range(4):
                have = eng.s["inv"].get(item, 0)
                if have >= n or item not in prices:
                    break
                if eng.s["coins"] - prices[item] < 5 and item not in ("water", "bread"):
                    break
                if not eng.buy(item, now):
                    break
        for gear in ("socks", "raincoat"):
            if gear in prices and eng.s["inv"].get(gear, 0) == 0 and eng.s["coins"] >= prices[gear] + 30:
                eng.buy(gear, now)


def run(profile: dict, days: int, seed: int, world) -> dict:
    rnd = random.Random(seed)
    t0 = int(dt.datetime(2026, 5, 1, 8, 0).timestamp() * 1000)
    day0 = dt.date(2026, 5, 1)
    s = new_state(world, seed, t0, day0.isoformat())
    eng = Engine(world, s)
    player = Player(rnd)
    danger_ticks = ticks = 0
    stops_per_day = []
    min_coins = s["coins"]
    for d in range(days):
        day = (day0 + dt.timedelta(days=d)).isoformat()
        steps_today = 0 if rnd.random() < profile["idle"] else max(0, int(rnd.gauss(profile["mean"], profile["sd"])))
        opens = sorted(rnd.uniform(8, 23) for _ in range(profile["opens"])) if profile["opens"] else []
        stops_before = len(s["journal"])
        walked = 0
        for h in opens:
            now = t0 + int((d * 24 + (h - 8)) * MS_HOUR)
            walked = int(steps_today * min(1.0, (h - 7) / 15))
            eng.sync_steps({day: walked}, now)
            eng.claim_login(day, now)
            eng.advance(now)
            player.act(eng, now)
            ticks += 1
            if min(s["stats"].values()) < world.b["stats"]["dangerBelow"]:
                danger_ticks += 1
            min_coins = min(min_coins, s["coins"])
        # остаток шагов дня приходит со следующим заходом
        end = t0 + int((d * 24 + 15.9) * MS_HOUR)
        eng.sync_steps({day: steps_today}, end)
        stops_per_day.append(sum(1 for j in s["journal"][stops_before:] if j["kind"] in ("event", "place")))
        if s["finished"]:
            break
    return {
        "km": s["pos"] / 1000,
        "deaths": s["deaths"],
        "coins": s["coins"],
        "min_coins": min_coins,
        "danger": danger_ticks / max(1, ticks),
        "stops": statistics.mean(stops_per_day) if stops_per_day else 0,
        "buffer_km": s["buffer"] / 1000,
        "chapter": world.chapter_at(s["pos"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--runs", type=int, default=30)
    args = ap.parse_args()
    world = load_world(ROOT)
    print(f"Маршрут {world.length/1000:.0f} км, авторских событий {len(world.anchored)}, случайных {len(world.randoms)}, квестов {len(world.quests)}")
    print(f"{'профиль':<15}{'км':>7}{'глава':>6}{'смертей':>8}{'монет':>7}{'мин.мон':>8}{'опасн.%':>8}{'стоп/д':>7}{'буфер':>7}")
    for name, prof in PROFILES.items():
        rs = [run(prof, args.days, 1000 + i, world) for i in range(args.runs)]
        avg = lambda k: statistics.mean(r[k] for r in rs)  # noqa: E731
        print(f"{name:<15}{avg('km'):7.0f}{avg('chapter'):6.1f}{avg('deaths'):8.2f}{avg('coins'):7.0f}"
              f"{avg('min_coins'):8.0f}{avg('danger')*100:8.1f}{avg('stops'):7.1f}{avg('buffer_km'):7.1f}")


if __name__ == "__main__":
    main()

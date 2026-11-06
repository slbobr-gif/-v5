"""Симулятор баланса «Путника» (Геймдизайнер).

Прогоняет эталонный движок на типичных игроках и печатает, как часто они голодают, гибнут,
сколько копят монет и сколько остановок в день видят.

    python3 tools/sim/simulate.py                    # 60 дней, все профили, осторожный и небрежный игрок
    python3 tools/sim/simulate.py --days 28 --runs 50
    python3 tools/sim/simulate.py --perks            # влияние каждого перка снаряжения (запас хода + смерти)
    python3 tools/sim/simulate.py --gifts            # влияние каждого дара духа (выдан на старте) — §13

Политики игрока (v5.3):
  осторожный — безопасные варианты (4 % импульсивных), закупается на каждом рынке, греет воду/чай, когда
               тепло < 50, переполнение решает по правилам ниже; дарами пользуется: спрашивает клубок/подсказку
               духа и обходит «наказание»/«смертельно», «Бусиной» отменяет заметный вред, «Сучком» — крюк и
               задержку, на привале парится/ночует в овине/рыбачит, когда это что-то даёт, продаёт жемчужину;
  небрежный  — 30 % решений наобум (в т. ч. смертельные), заходит в магазин на 60 % привалов и держит
               только 1 хлеб + 1 воду, горелкой не пользуется, всё лишнее выбрасывает.
Старт-набор и переполнение решаются детерминированно (без случайностей), чтобы прогон повторялся.
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import CONSUMABLE, Engine, MS_HOUR, STATS, load_world, new_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# Профили: средние шаги в день, разброс, доля дней без ходьбы, сколько раз в день открывает приложение
PROFILES = {
    "ленивый 3k":    dict(mean=3000, sd=1200, idle=0.15, opens=2),
    "обычный 7k":    dict(mean=7000, sd=2000, idle=0.07, opens=3),
    "ровно 7k":      dict(mean=7000, sd=0, idle=0.0, opens=3),
    "активный 12k":  dict(mean=12000, sd=3000, idle=0.05, opens=4),
    "рывками":       dict(mean=6000, sd=5000, idle=0.30, opens=2),
    "забывчивый 7k": dict(mean=7000, sd=2000, idle=0.07, opens=1),
}

# Порядок ценности снаряжения для экрана «Что взять с собой» (детерминированная политика)
GEAR_PRIORITY = ["first_aid", "ribbon_rusalka", "shell_vodyanoy", "twig_leshy", "ember_domovoy", "gas_stove",
                 "ear_poludnitsa", "trekking_poles", "socks", "raincoat", "lapot_domovoy", "amulet_leshy",
                 "wreath_poludnitsa", "valdai_bell", "flask", "sleeping_bag", "compass_ded", "compass", "space_blanket"]
# Какой нагреваемый предмет пить/есть горячим и при каком запасе показателя (не больше порога)
HEAT_ORDER = [("water", "water", 60), ("tea", "water", 90), ("stew", "satiety", 45), ("pie", "satiety", 60)]


def item_value(w, item: str) -> int:
    it = w.items[item]
    return sum(int(it.get(k, 0)) for k in STATS) + int(it.get("heat", 0))


def keep_gear(cands: list[str], slots: int) -> list[str]:
    rank = {g: i for i, g in enumerate(GEAR_PRIORITY)}
    return sorted(cands, key=lambda g: (rank.get(g, 99), g))[:slots]


class Player:
    """Осторожный игрок."""

    impulse = 0.04
    careless = False

    def __init__(self, rnd: random.Random, loadout: tuple[list[str], dict[str, int]] | None = None):
        self.r = rnd
        self.loadout = loadout
        self.heats = 0
        self.gifts_used = 0
        self.overflows = {"backpack": 0, "gear": 0}

    # --- старт и переполнение — без случайностей
    def start(self, eng: Engine, now: int):
        if self.loadout is not None:
            err = eng.start_loadout(self.loadout[0], self.loadout[1], now)
            assert err is None, err
        else:
            d = eng.b["loadout"]["default"]
            eng.start_loadout(list(d["gear"]), dict(d["pack"]), now)

    def resolve_overflow(self, eng: Engine, now: int):
        guard = 0
        while eng.s["overflow"] and guard < 50:
            guard += 1
            o = eng.s["overflow"][0]
            self.overflows[o["kind"]] += 1
            if o["kind"] == "gear":
                plain = [g for g in eng.s["gear"] if not eng.w.is_gift(g)]  # дары ячеек не занимают (V5-43)
                cands = plain + [o["item"]]
                keep = plain if self.careless else keep_gear(cands, eng.gear_slots())
                assert eng.resolve_overflow_gear(keep) is None
                continue
            if self.careless:
                eng.resolve_overflow_backpack("drop", None, now)
                continue
            it = o["item"]
            spec = eng.w.items[it]
            fits = all(eng.s["stats"][k] + spec.get(k, 0) <= eng.b["stats"]["max"] for k in STATS)
            if fits:
                eng.resolve_overflow_backpack("use", None, now)
                continue
            # меняем только «еду на еду» и «питьё на питьё», иначе рюкзак зарастает пирогами и нечем запить
            t = eng.w.item_type(it)
            inv = sorted((k for k, n in eng.s["inv"].items() if n > 0 and eng.w.item_type(k) == t),
                         key=lambda k: (item_value(eng.w, k), k))
            if inv and item_value(eng.w, inv[0]) < item_value(eng.w, it):
                assert eng.resolve_overflow_backpack("stash", {"action": "drop", "item": inv[0]}, now) is None
            else:
                eng.resolve_overflow_backpack("drop", None, now)

    def maybe_heat(self, eng: Engine, now: int):
        if self.careless or eng.s["stats"]["warmth"] >= 50:
            return
        pick = None
        for item, stat, limit in HEAT_ORDER:
            if eng.s["inv"].get(item, 0) > 0 and eng.s["stats"][stat] <= limit:
                pick = item
                break
        if pick is None or eng.heat_status(now) not in ("ready", "on"):
            return
        if eng.heat(now) == "heated":
            self.heats += 1
        eng.use_item(pick, now)

    # --- остановки
    def choose(self, eng: Engine, ev: dict, now: int):
        choices = [c for c in ev["choices"] if eng.choice_available(c)]
        safe = [c for c in choices if eng.choice_risk(c) != "fatal"]
        pool = choices if (not safe or self.r.random() < self.impulse) else safe
        if not self.careless and eng.clew_status(now) == "ready":
            tones = eng.ask_clew(now)
            self.gifts_used += 1
            calm = [c for c in pool if tones.get(c["id"]) not in ("death", "penalty")]
            good = [c for c in calm if tones.get(c["id"]) in ("reward", "mixed")]
            pool = good or calm or pool
        eng.choose(self.r.choice(pool)["id"], now)
        if not self.careless:
            self.after_outcome(eng, now)

    def _gifts(self, eng: Engine, kind: str) -> list[str]:
        return [i for i in eng.held_items() if (eng.w.items.get(i, {}).get("ability") or {}).get("kind") == kind]

    def _try(self, eng: Engine, item: str, now: int) -> bool:
        if eng.gift_status(item, now) == "ready" and eng.use_gift(item, now) == "ok":
            self.gifts_used += 1
            return True
        return False

    def after_outcome(self, eng: Engine, now: int):
        u = eng.s["undo"]
        if not u:
            return
        big = (sum((u.get("stats") or {}).values()) >= 20 or u.get("removed") or u.get("removedGear")
               or u.get("coins", 0) >= 12 or "detour" in u)
        if big:
            for it in self._gifts(eng, "mirage"):
                if self._try(eng, it, now):
                    return
        if "delay" in u or "detour" in u:
            for it in self._gifts(eng, "guide"):
                if self._try(eng, it, now):
                    return

    def camp_gifts(self, eng: Engine, now: int):
        for it in self._gifts(eng, "action"):
            eff = eng.w.items[it]["ability"].get("effect") or {}
            warm = eff.get("warmth", 0) or (35 if eff.get("warmthToMax") else 0)
            if warm and eng.s["stats"]["warmth"] > 100 - min(warm, 40):
                continue  # не тратить заряд почти впустую
            if eff.get("give") and eng.consumables_count() >= eng.backpack_slots():
                continue
            self._try(eng, it, now)
        for it, _ in eng.sell_offers():
            if eng.sell(it, now):
                self.gifts_used += 1

    def pocket_gifts(self, eng: Engine, now: int):
        """В дороге: «Согреться» камешком/грелкой, если совсем зябко."""
        if self.careless or eng.s["stats"]["warmth"] >= 35:
            return
        for it in self._gifts(eng, "action"):
            if eng.w.items[it]["ability"].get("at", "any") == "any" and self._try(eng, it, now):
                return

    def act(self, eng: Engine, now: int):
        for _ in range(40):
            self.resolve_overflow(eng, now)
            self.maybe_heat(eng, now)
            self.pocket_gifts(eng, now)
            st = eng.s["stop"]
            if not st:
                return
            t = st["type"]
            if t == "event":
                ev = eng.current_event()
                if ev is None:
                    eng.s["stop"] = None
                    continue
                self.choose(eng, ev, now)
                self.resolve_overflow(eng, now)
            elif t in ("place", "chapter_end"):
                if not self.careless:
                    self.camp_gifts(eng, now)
                self.resolve_overflow(eng, now)
                self.shop(eng, now)
                eng.continue_journey(now)
            elif t == "night":
                eng.continue_journey(now)  # ночёвка (V5-45): «Дальше» — и тем же буфером в путь
            elif t == "death":
                eng.s["stop"] = None
            elif t == "finish":
                return
            eng.advance(now)

    def shop(self, eng: Engine, now: int):
        prices = dict(eng.market())
        if not prices:
            return
        # рюкзак забит едой, а питья меньше двух — съесть самое дешёвое, чтобы освободить ячейку под воду
        for _ in range(2):
            drinks = sum(n for k, n in eng.s["inv"].items() if eng.w.item_type(k) == "drink")
            if eng.consumables_count() < eng.backpack_slots() or drinks >= 2 or "water" not in prices:
                break
            foods = sorted((k for k, n in eng.s["inv"].items() if n > 0 and eng.w.item_type(k) == "food"),
                           key=lambda k: (item_value(eng.w, k), k))
            if not foods:
                break
            eng.use_item(foods[0], now)
        want = [("water", 2), ("bread", 2), ("stew", 1), ("water", 3), ("tea", 1)]
        for item, n in want:
            for _ in range(4):
                have = eng.s["inv"].get(item, 0)
                if have >= n or item not in prices:
                    break
                if eng.s["coins"] - prices[item] < 5 and item not in ("water", "bread"):
                    break
                if not eng.buy(item, now):
                    break
        if "gas" in prices and "gas_stove" in eng.s["gear"] and eng.gear_uses("gas_stove") <= 3 \
                and eng.s["coins"] >= prices["gas"] + 20:
            eng.buy("gas", now)
        for gear in ("socks", "raincoat"):
            if gear in prices and eng.buy_blocker(gear) is None and eng.s["coins"] >= prices[gear] + 30:
                eng.buy(gear, now)


class CarelessPlayer(Player):
    """Небрежный игрок."""

    impulse = 0.30
    careless = True
    shop_chance = 0.6

    def shop(self, eng: Engine, now: int):
        if self.r.random() >= self.shop_chance:
            return
        prices = dict(eng.market())
        for item in ("bread", "water"):
            for _ in range(3):
                if item not in prices or eng.s["inv"].get(item, 0) >= 1 or not eng.buy(item, now):
                    break


POLICIES = {"осторожный": Player, "небрежный": CarelessPlayer}


def run(profile: dict, days: int, seed: int, world, policy=Player, loadout=None, gift=None) -> dict:
    rnd = random.Random(seed)
    t0 = int(dt.datetime(2026, 5, 1, 8, 0).timestamp() * 1000)
    day0 = dt.date(2026, 5, 1)
    s = new_state(world, seed, t0, day0.isoformat())
    eng = Engine(world, s)
    player = policy(rnd, loadout)
    player.start(eng, t0)
    if gift:
        eng.give_items({gift: 1}, "sim_gift")
        player.resolve_overflow(eng, t0)
    ch2_end = world.pos_of[next(c for c in world.chapters if c["id"] == 2)["to"]]
    ch2_day = None
    danger_ticks = ticks = 0
    stops_per_day, rnd_per_day, steps_per_day = [], [], []
    rand_ids = {e["id"] for e in world.randoms}
    min_coins = s["coins"]
    for d in range(days):
        day = (day0 + dt.timedelta(days=d)).isoformat()
        steps_today = 0 if rnd.random() < profile["idle"] else max(0, int(rnd.gauss(profile["mean"], profile["sd"])))
        opens = sorted(rnd.uniform(8, 23) for _ in range(profile["opens"])) if profile["opens"] else []
        stops_before = len(s["journal"])
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
        rnd_per_day.append(sum(1 for j in s["journal"][stops_before:] if j["kind"] == "event" and j.get("event") in rand_ids))
        steps_per_day.append(steps_today)
        if ch2_day is None and s["maxPos"] >= ch2_end:
            ch2_day = d + 1
        if s["finished"]:
            break
    kinds = [j["kind"] for j in s["journal"]]
    return {
        "km": s["pos"] / 1000,
        "deaths": s["deaths"],
        "coins": s["coins"],
        "min_coins": min_coins,
        "danger": danger_ticks / max(1, ticks),
        "stops": statistics.mean(stops_per_day) if stops_per_day else 0,
        "buffer_km": s["buffer"] / 1000,
        "chapter": world.chapter_at(s["pos"]),
        "ch2_day": ch2_day,
        "heats": player.heats,
        "gifts": player.gifts_used,
        "aid": kinds.count("first_aid"),
        "ovf": player.overflows["backpack"] + player.overflows["gear"],
        "fallback": kinds.count("zone_fallback"),
        # случайных событий на 8 000 шагов (середина целевого коридора 6–10 тыс.)
        "rnd8k": sum(rnd_per_day) / max(1, sum(steps_per_day)) * 8000,
    }


def table(world, days: int, runs: int, policy, loadout=None, profiles=PROFILES):
    print(f"{'профиль':<15}{'км':>6}{'глава':>6}{'смертей':>8}{'монет':>6}{'мин':>5}{'опасн%':>7}{'стоп/д':>7}"
          f"{'буфер':>6}{'гл2,д':>6}{'нагр':>5}{'апт':>5}{'перепол':>8}{'сл/8k':>6}{'запас':>6}")
    out = {}
    for name, prof in profiles.items():
        rs = [run(prof, days, 1000 + i, world, policy, loadout) for i in range(runs)]
        avg = lambda k: statistics.mean(r[k] for r in rs)  # noqa: E731
        ch2 = [r["ch2_day"] for r in rs if r["ch2_day"]]
        ch2s = f"{statistics.mean(ch2):.1f}" if len(ch2) * 2 >= len(rs) else "—"
        print(f"{name:<15}{avg('km'):6.0f}{avg('chapter'):6.1f}{avg('deaths'):8.2f}{avg('coins'):6.0f}"
              f"{avg('min_coins'):5.0f}{avg('danger')*100:7.1f}{avg('stops'):7.1f}{avg('buffer_km'):6.1f}"
              f"{ch2s:>6}{avg('heats'):5.1f}{avg('aid'):5.2f}{avg('ovf'):8.1f}{avg('rnd8k'):6.2f}{avg('fallback'):6.1f}")
        out[name] = rs
    return out


# ---------------------------------------------------------------- влияние перков
def walk_range(world, gear: list[str], seeds: int = 40, stat_start: float = 80.0, start_pos: float = 0.0) -> dict:
    """Запас хода: сколько км герой проходит от 80/80/80 без еды, пока показатель не упадёт до 0.
    Погода и холод — как на маршруте с позиции start_pos (позиция растёт), остановок и привалов нет."""
    res = {k: [] for k in STATS}
    for sd in range(seeds):
        s = new_state(world, 5000 + sd, 0, "2026-05-01")
        e = Engine(world, s)
        e.start_loadout(gear, {}, 0)
        s["pos"] = start_pos
        for k in STATS:
            s["stats"][k] = stat_start
        done = {}
        km = 0.0
        while len(done) < 3 and km < 400:
            e._drain_walk(0.25)
            s["pos"] += 250.0
            km += 0.25
            for k in STATS:
                if k not in done and s["stats"][k] <= 0:
                    done[k] = km
        for k in STATS:
            res[k].append(done.get(k, 400.0))
    return {k: statistics.mean(v) for k, v in res.items()}


def perks_report(world, days: int, runs: int):
    starter = world.starter_gear()
    for title, ch in (("глава 1", 1), ("глава 5 (холод ×1.25, ветер)", 5)):
        sp = world.chapter_start_pos(ch)
        base = walk_range(world, [], start_pos=sp)
        print(f"Запас хода без еды от 80/80/80, {title} (км до нуля): " + ", ".join(f"{k} {v:.1f}" for k, v in base.items()))
        print(f"{'снаряжение':<16}" + "".join(f"{k:>16}" for k in STATS))
        for g in starter:
            r = walk_range(world, [g], start_pos=sp)
            cells = []
            for k in STATS:
                d = r[k] - base[k]
                cells.append(f"{r[k]:6.1f} ({d / base[k] * 100:+4.0f}%)" if abs(d) > 0.05 else f"{r[k]:6.1f}        ")
            print(f"{g:<16}" + "".join(f"{c:>16}" for c in cells))
    b = world.b
    hrs = b["drainPerHour"]["warmth"]
    print(f"Покой: тепло −{hrs} в час; спальный мешок ×{world.items['sleeping_bag']['idleWarmthMult']} → "
          f"экономит {hrs * (1 - world.items['sleeping_bag']['idleWarmthMult']) * 24:.1f} тепла за сутки простоя "
          f"(носки ещё ×{world.items['socks']['warmthDrainMult']}).")
    dk = b["drainPerKm"]["warmth"]
    for it in ("water", "tea", "stew", "pie"):
        h = world.items[it].get("heat", 0)
        print(f"Горелка: горячий {it} +{h} тепла ≈ {h / dk:.0f} км пути по теплу (облачно, глава 1); "
              f"10 зарядов ≈ {10 * h / dk:.0f} км")
    ra = world.items["first_aid"]["rescueTo"]
    print(f"Аптечка: {world.items['first_aid']['uses']} заряда × подъём до {ra}: сытость +{ra / b['drainPerKm']['satiety']:.0f} км, "
          f"вода +{ra / b['drainPerKm']['water']:.0f} км, тепло +{ra / dk:.0f} км на заряд")
    L = b["levels"]
    cm = world.items["compass"]
    print("Компас: задержки " + ", ".join(f"{k} {v}→{max(1, round(v * cm['delayMult']))} ч" for k, v in L["delayHours"].items())
          + "; крюки " + ", ".join(f"{k} {v}→{max(1, round(v * cm['detourMult']))} км" for k, v in L["detourKm"].items()))
    f = 1 - world.items["amulet_leshy"]["riskReduce"]
    print("Оберег: смерть в вариантах fatal " + ", ".join(
        f"1/{n} → {f * 100:.0f}/{f * 100 + (n - 1) * 100:.0f} = {f / (f + n - 1) * 100:.1f}%" for n in (4, 6, 8)))
    print()
    prof = PROFILES["обычный 7k"]
    pack = dict(b["loadout"]["default"]["pack"])
    for pol_name, pol in POLICIES.items():
        print(f"Смерти за {days} дн., {pol_name} 7k, рюкзак по умолчанию, {runs} прогонов:")
        none = statistics.mean(run(prof, days, 1000 + i, world, pol, ([], pack))["deaths"] for i in range(runs))
        line = [f"без снаряжения {none:.2f}"]
        for g in starter:
            d = statistics.mean(run(prof, days, 1000 + i, world, pol, ([g], pack))["deaths"] for i in range(runs))
            line.append(f"{g} {d:.2f}")
        dflt = statistics.mean(run(prof, days, 1000 + i, world, pol)["deaths"] for i in range(runs))
        line.append(f"по умолчанию {dflt:.2f}")
        print("  " + "; ".join(line))


GIFTS = ["twig_leshy", "spruce_leshy", "ball_yaga", "thread_yaga", "shell_vodyanoy", "hook_vodyanoy", "ember_domovoy",
         "lapot_domovoy", "venik_bannik", "stone_bannik", "bead_kikimora", "kudel_kikimora", "ear_poludnitsa",
         "wreath_poludnitsa", "ribbon_rusalka", "pearl_rusalka", "key_ovinnik", "sheaf_ovinnik", "amulet_leshy",
         "compass_ded", "valdai_bell", "space_blanket", "hand_warmers"]


def gifts_report(world, days: int, runs: int):
    """Каждый дар выдан на старте (поверх набора бывалого): смерти, опасность, запас, путь, монеты.
    Дар из квеста приходит позже (км 100–560), так что это верхняя оценка его пользы."""
    for pol_name, pol in POLICIES.items():
        for prof_name in (("обычный 7k", "активный 12k") if pol is Player else ("обычный 7k",)):
            prof = PROFILES[prof_name]
            print(f"\n== дары: {pol_name}, {prof_name}, {days} дн., {runs} прогонов ==")
            print(f"{'дар':<18}{'смертей':>8}{'Δ':>7}{'опасн%':>8}{'км':>7}{'монет':>7}{'исп.':>6}")
            base = None
            for g in [None] + GIFTS:
                rs = [run(prof, days, 1000 + i, world, pol, gift=g) for i in range(runs)]
                avg = lambda k: statistics.mean(r[k] for r in rs)  # noqa: E731
                if base is None:
                    base = avg("deaths")
                print(f"{g or '— без дара':<18}{avg('deaths'):8.2f}{avg('deaths') - base:+7.2f}{avg('danger')*100:8.1f}"
                      f"{avg('km'):7.0f}{avg('coins'):7.0f}{avg('gifts'):6.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--perks", action="store_true", help="отчёт о влиянии перков")
    ap.add_argument("--gifts", action="store_true", help="отчёт о влиянии даров духов (§13)")
    args = ap.parse_args()
    world = load_world(ROOT)
    print(f"Маршрут {world.length/1000:.0f} км, авторских событий {len(world.anchored)}, случайных {len(world.randoms)}, "
          f"квестов {len(world.quests)}; конец главы 2 — {world.pos_of[world.chapters[1]['to']]/1000:.0f} км")
    if args.perks:
        perks_report(world, args.days, args.runs)
        return
    if args.gifts:
        gifts_report(world, args.days, args.runs)
        return
    for name, pol in POLICIES.items():
        print(f"\n== {name} игрок, старт-набор по умолчанию ==")
        table(world, args.days, args.runs, pol)


if __name__ == "__main__":
    main()

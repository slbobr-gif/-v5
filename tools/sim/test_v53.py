"""Тесты правил v5.3 эталонного движка (зоны, перки, заряды, «Нагреть», переполнение, аптечка, оберег, компас).

    python3 tools/sim/test_v53.py          (или python3 -m unittest tools/sim/test_v53.py)

Мир синтетический (свой маршрут и события), баланс — настоящий app/assets/balance.json: тесты не зависят от
контента, который пишут параллельно, но ловят изменение чисел баланса (ожидания считаются из баланса).
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "content"))
from engine import MS_DAY, MS_HOUR, STATS, Engine, World, load_world, migrate_state, new_state, py_round  # noqa: E402

BAL = json.loads((ROOT / "app" / "assets" / "balance.json").read_text(encoding="utf-8"))
T0 = 1777622400000  # 2026-05-01 08:00 UTC = 11:00 МСК


def ev(eid, zone, choices=None, tags=("ch1",), **kw):
    e = {"id": eid, "kind": "random", "zone": zone, "tags": list(tags), "title": eid, "text": "t",
         "choices": choices or [{"id": "ok", "text": "ок", "risk": "none",
                                 "outcomes": [{"weight": 1, "text": "x", "effects": {}}]}]}
    e.update(kw)
    return e


PLACES = [
    {"id": "a", "name": "А", "kind": "start", "market": "city", "chapter": 1},
    {"id": "b", "name": "Б", "kind": "town", "market": "town", "chapter": 1},
    {"id": "c", "name": "В", "kind": "village", "market": "village", "chapter": 1},
    {"id": "d", "name": "Г", "kind": "city", "market": "city", "chapter": 1},
]
POS = {"a": 0.0, "b": 30000.0, "c": 60000.0, "d": 150000.0}
CHAPTERS = [{"id": 1, "from": "a", "to": "d", "title": "Глава"}]


def make_world(balance=None, randoms=None, anchored=None) -> World:
    content = {"places": copy.deepcopy(PLACES), "chapters": CHAPTERS, "quests": [],
               "events_random": randoms if randoms is not None else
               [ev("r_city", "city"), ev("r_sub", "suburb"), ev("r_wild", "wild")],
               "events_anchored": anchored or []}
    return World(copy.deepcopy(balance or BAL), content, dict(POS), 200000.0)


def fresh(world=None, gear=(), pack=None, seed=7):
    w = world or make_world()
    s = new_state(w, seed, T0, "2026-05-01")
    e = Engine(w, s)
    assert e.start_loadout(list(gear), dict(pack or {}), T0) is None
    s["journal"].clear()
    return w, s, e


class Zones(unittest.TestCase):
    def test_zone_at_radii_and_roadside(self):
        w = make_world()
        Z = BAL["zones"]["byKind"]
        start_u, start_o = Z["start"]["urban"], Z["start"]["urban"] + Z["start"]["suburb"]
        self.assertEqual(w.zone_at(0.0), "city")
        self.assertEqual(w.zone_at(start_u * 1000.0), "city")
        self.assertEqual(w.zone_at(start_u * 1000.0 + 1), "suburb")
        self.assertEqual(w.zone_at(start_o * 1000.0 + 1), "wild" if start_o * 1000 + 1 < 30000 - (Z["town"]["urban"] + Z["town"]["suburb"]) * 1000 else w.zone_at(start_o * 1000.0 + 1))
        self.assertEqual(w.zone_at(30000.0), "city")  # посёлок: urban > 0
        # деревня: urban = 0 → в самой точке не «город», а пригород
        self.assertEqual(w.zone_at(60000.0), "suburb")
        # придорожные точки между В (60 км) и Г (150 км): отрезок 90 км > maxGapKm 42 → 2 точки (90 и 120 км)
        rs = sorted(w.pos_of[p["id"]] for p in w.places if p["kind"] == "roadside")
        self.assertEqual(len(rs), int(90000.0 // (BAL["roadside"]["maxGapKm"] * 1000.0)))
        self.assertEqual(w.zone_at(rs[0]), "suburb" if Z["roadside"]["suburb"] > 0 else "wild")
        self.assertEqual(w.zone_at(rs[0] + (Z["roadside"]["suburb"] + 0.5) * 1000.0), "wild")

    def test_random_pick_by_zone_and_fallback(self):
        w, s, e = fresh()
        s["pos"] = 1000.0  # город
        self.assertEqual(e._pick_random(T0)["id"], "r_city")
        s["recentRandom"] = []
        s["pos"] = 45000.0  # окрестности между Б и В
        self.assertEqual(w.zone_at(45000.0), "wild")
        self.assertEqual(e._pick_random(T0)["id"], "r_wild")
        self.assertFalse([j for j in s["journal"] if j["kind"] == "zone_fallback"])
        # пул зоны исчерпан (недавние) → запасной выбор из всех зон + пометка в журнале
        s["recentRandom"] = ["r_wild"]
        got = e._pick_random(T0)
        self.assertIn(got["id"], ("r_city", "r_sub"))
        self.assertEqual([j["zone"] for j in s["journal"] if j["kind"] == "zone_fallback"], ["wild"])

    def test_chapter_filter_still_applies(self):
        w = make_world(randoms=[ev("r2", "city", tags=("ch2",)), ev("r_any", "city", tags=("any",))])
        _, s, e = fresh(w)
        s["pos"] = 1000.0
        for _ in range(5):
            s["recentRandom"] = []
            self.assertEqual(e._pick_random(T0)["id"], "r_any")

    def test_validator_zones_match_engine_on_real_route(self):
        import zones as Z
        real = load_world(ROOT)
        for km in range(0, int(real.length // 1000), 3):
            self.assertEqual(Z.zone_at(km), real.zone_at(km * 1000.0), f"{km} км")
        for p in real.places:
            pm = real.pos_of[p["id"]]
            self.assertEqual(Z.zone_at_m(pm), real.zone_at(pm), p["id"])


class Loadout(unittest.TestCase):
    def test_default_and_rules(self):
        w = make_world()
        s = new_state(w, 1, T0, "2026-05-01")
        d = BAL["loadout"]["default"]
        self.assertEqual(s["gear"], d["gear"])
        self.assertEqual(s["inv"], d["pack"])
        self.assertEqual(s["gearUses"], {g: BAL["items"][g]["uses"] for g in d["gear"] if "uses" in BAL["items"][g]})
        self.assertFalse(s["loadoutDone"])
        e = Engine(w, s)
        self.assertEqual(e.start_loadout(["socks", "flask", "compass", "first_aid"], {}, T0), "gear_too_many")
        self.assertEqual(e.start_loadout(["socks", "socks"], {}, T0), "gear_duplicate")
        self.assertEqual(e.start_loadout(["amulet_leshy"], {}, T0), "gear_not_starter")
        self.assertEqual(e.start_loadout([], {"pie": 1}, T0), "pack_not_starter")
        self.assertEqual(e.start_loadout([], {"bread": 0}, T0), "pack_bad_count")
        self.assertEqual(e.start_loadout([], {"bread": 4}, T0), "pack_kind_limit")
        self.assertEqual(e.start_loadout([], {"bread": 3, "water": 3}, T0), "pack_too_many")
        self.assertIsNone(e.start_loadout(["first_aid", "flask"], {"bread": 3, "water": 2}, T0))
        self.assertEqual(s["gear"], ["first_aid", "flask"])
        self.assertEqual(s["gearUses"], {"first_aid": 2})
        self.assertEqual(s["inv"], {"bread": 3, "water": 2})
        self.assertEqual(s["journal"][-1]["kind"], "loadout")
        self.assertEqual(e.start_loadout([], {}, T0), "already_done")

    def test_catalog(self):
        w = make_world()
        self.assertEqual(w.starter_gear(), ["socks", "raincoat", "trekking_poles", "gas_stove", "sleeping_bag",
                                            "first_aid", "flask", "compass"])
        self.assertNotIn("amulet_leshy", w.starter_gear())
        self.assertIn({"key": "warmthDrain", "value": 15}, w.item_perks("socks"))
        self.assertEqual(w.item_perks("compass"), [{"key": "delay", "value": 25}, {"key": "detour", "value": 25}])
        self.assertIn({"key": "heat", "value": 25}, w.item_perks("water"))
        self.assertEqual(w.item_perks("gas"), [{"key": "refill", "value": 10}, {"key": "refillMax", "value": 30}])


class Perks(unittest.TestCase):
    def drain(self, gear, weather=None, km=1.0, stats=50.0):
        w, s, e = fresh(gear=gear)
        if weather:
            w.weather_at = lambda seed, pos: weather
        for k in STATS:
            s["stats"][k] = stats
        e._drain_walk(km)
        return {k: stats - s["stats"][k] for k in STATS}

    def test_walk_drain_multipliers(self):
        dk = BAL["drainPerKm"]
        it = BAL["items"]
        wx = BAL["weather"]["types"]["cloudy"]
        base = self.drain([], "cloudy")
        self.assertAlmostEqual(base["satiety"], dk["satiety"] * wx.get("satiety", 1.0), places=9)
        socks = self.drain(["socks"], "cloudy")
        self.assertAlmostEqual(socks["warmth"], base["warmth"] * it["socks"]["warmthDrainMult"], places=9)
        poles = self.drain(["trekking_poles"], "cloudy")
        self.assertAlmostEqual(poles["satiety"], base["satiety"] * it["trekking_poles"]["drainKmMult"]["satiety"], places=9)
        self.assertAlmostEqual(poles["water"], base["water"] * it["trekking_poles"]["drainKmMult"]["water"], places=9)
        both = self.drain(["trekking_poles", "flask"], "cloudy")
        self.assertAlmostEqual(both["water"], base["water"] * it["trekking_poles"]["drainKmMult"]["water"]
                               * it["flask"]["waterDrainMult"], places=9)

    def test_raincoat_only_bad_weather(self):
        it = BAL["items"]["raincoat"]["weatherWarmthMult"]
        rain = BAL["weather"]["types"]["rain"]["warmth"]
        base = self.drain([], "rain")
        coat = self.drain(["raincoat"], "rain")
        self.assertAlmostEqual(coat["warmth"] / base["warmth"], (1.0 + (rain - 1.0) * it) / rain, places=9)
        self.assertEqual(self.drain(["raincoat"], "clear")["warmth"], self.drain([], "clear")["warmth"])

    def test_idle_sleeping_bag(self):
        for gear, mult in (([], 1.0), (["sleeping_bag"], BAL["items"]["sleeping_bag"]["idleWarmthMult"]),
                           (["socks", "sleeping_bag"], BAL["items"]["socks"]["warmthDrainMult"] * BAL["items"]["sleeping_bag"]["idleWarmthMult"])):
            _, s, e = fresh(gear=gear)
            s["stats"] = {"satiety": 90.0, "water": 90.0, "warmth": 90.0}
            e.apply_time(T0 + 10 * MS_HOUR)
            self.assertAlmostEqual(90.0 - s["stats"]["warmth"], BAL["drainPerHour"]["warmth"] * mult * 10, places=9)
            self.assertAlmostEqual(90.0 - s["stats"]["water"], BAL["drainPerHour"]["water"] * 10, places=9)

    def test_compass_rounding(self):
        L = BAL["levels"]
        m = BAL["items"]["compass"]
        _, s, e = fresh(gear=["compass"])
        for lvl, h in L["delayHours"].items():
            e._apply_effects({"delay": lvl}, T0, None)
            self.assertEqual(s["delayUntil"] - T0, max(1, py_round(h * m["delayMult"])) * MS_HOUR)
        for lvl, km in L["detourKm"].items():
            e._apply_effects({"detour": lvl}, T0, None)
            self.assertEqual(s["detour"]["total"], max(1, py_round(km * m["detourMult"])) * 1000.0)
        # конкретные числа при 0.75: середина — к чётному
        if m["delayMult"] == 0.75 and L["delayHours"] == {"short": 2, "medium": 6, "long": 12}:
            e._apply_effects({"delay": "short"}, T0, None)
            self.assertEqual(s["delayUntil"] - T0, 2 * MS_HOUR)  # 1.5 → 2
            e._apply_effects({"delay": "medium"}, T0, None)
            self.assertEqual(s["delayUntil"] - T0, 4 * MS_HOUR)  # 4.5 → 4

    def test_amulet_weights(self):
        choice = {"id": "x", "risk": "fatal", "outcomes": [
            {"weight": 3, "effects": {}}, {"weight": 1, "effects": {"death": True}},
            {"weight": 2, "effects": {"warmth": "-large"}}, {"weight": 1, "effects": {"warmth": "-medium"}}]}
        _, s, e = fresh()
        self.assertEqual(e.outcome_weights(choice), [3, 1, 2, 1])
        s["gear"].append("amulet_leshy")
        f = 1.0 - BAL["items"]["amulet_leshy"]["riskReduce"]
        sc = BAL["riskReduce"]["weightScale"]
        self.assertEqual(e.outcome_weights(choice), [3 * sc, py_round(sc * f), py_round(2 * sc * f), sc])
        safe = dict(choice, risk="none")
        self.assertEqual(e.outcome_weights(safe), [3, 1, 2, 1])
        all_bad = {"id": "y", "risk": "high", "outcomes": [{"weight": 1, "effects": {"death": True}}]}
        self.assertEqual(e.outcome_weights(all_bad), [1])

    def test_amulet_lowers_death_rate(self):
        choice = {"id": "x", "risk": "fatal", "outcomes": [{"weight": 1, "effects": {"death": True}},
                                                           {"weight": 3, "effects": {}}]}
        hits = {}
        for gear in ([], ["amulet_leshy"]):
            n = 0
            _, s, e = fresh()
            s["gear"] = list(gear)
            for _ in range(20000):
                if e.rng.pick_weighted(e.outcome_weights(choice)) == 0:
                    n += 1
            hits[len(gear)] = n / 20000
        self.assertAlmostEqual(hits[0], 0.25, delta=0.02)
        f = 1.0 - BAL["items"]["amulet_leshy"]["riskReduce"]
        self.assertAlmostEqual(hits[1], f / (f + 3), delta=0.02)


class ChargesAndHeat(unittest.TestCase):
    def test_heat_cycle(self):
        it = BAL["items"]
        _, s, e = fresh(gear=["gas_stove"], pack={"water": 2, "bread": 1})
        uses = it["gas_stove"]["uses"]
        self.assertEqual(e.heat_status(T0), "ready")
        self.assertEqual(e.heat(T0), "heated")
        self.assertEqual(s["gearUses"]["gas_stove"], uses - 1)
        self.assertTrue(s["heated"])
        self.assertEqual(e.heat(T0), "on")  # повторно — без заряда
        self.assertEqual(s["gearUses"]["gas_stove"], uses - 1)
        s["stats"] = {"satiety": 50.0, "water": 50.0, "warmth": 50.0}
        e.use_item("bread", T0)  # хлеб не нагревается — горелка остаётся включённой
        self.assertTrue(s["heated"])
        e.use_item("water", T0)
        self.assertEqual(s["stats"]["warmth"], 50.0 + it["water"]["heat"])
        self.assertEqual(s["stats"]["water"], 50.0 + it["water"]["water"])
        self.assertFalse(s["heated"])
        e.use_item("water", T0)  # вторая бутылка уже холодная
        self.assertEqual(s["stats"]["warmth"], 50.0 + it["water"]["heat"])

    def test_heat_status_codes(self):
        _, s, e = fresh(gear=[], pack={"water": 1})
        self.assertEqual(e.heat(T0), "no_stove")
        _, s, e = fresh(gear=["gas_stove"], pack={"bread": 1})
        self.assertEqual(e.heat(T0), "nothing")
        s["gearUses"]["gas_stove"] = 0
        s["inv"]["water"] = 1
        self.assertEqual(e.heat(T0), "no_gas")
        self.assertIn("gas_stove", s["gear"])  # пустая горелка остаётся в снаряжении

    def test_heat_expires_on_new_game_day_and_death(self):
        _, s, e = fresh(gear=["gas_stove"], pack={"water": 2})
        e.heat(T0)
        off = BAL["gameDay"]["utcOffsetHours"] * MS_HOUR
        midnight = ((T0 + off) // MS_DAY + 1) * MS_DAY - off  # полночь по МСК
        self.assertTrue(e.is_heated(midnight - 1))
        self.assertFalse(e.is_heated(midnight))
        e.apply_time(midnight + 1)
        self.assertFalse(s["heated"])
        e.heat(midnight + 2)
        self.assertTrue(s["heated"])
        e._die(midnight + 3, "stats")
        self.assertFalse(s["heated"])

    def test_auto_consume_prefers_hot_drink_for_warmth(self):
        _, s, e = fresh(gear=["gas_stove"], pack={"water": 1})
        e.heat(T0)
        s["stats"] = {"satiety": 80.0, "water": 50.0, "warmth": 20.0}
        e._auto_consume(T0)
        self.assertEqual(s["inv"].get("water", 0), 0)
        self.assertEqual(s["stats"]["warmth"], 20.0 + BAL["items"]["water"]["heat"])
        self.assertFalse(s["heated"])

    def test_gas_refill_buy_and_find(self):
        it = BAL["items"]
        w = make_world()
        _, s, e = fresh(w, gear=["gas_stove"])
        s["stop"] = {"type": "place", "place": "d"}
        s["coins"] = 100
        s["gearUses"]["gas_stove"] = 25
        self.assertIsNone(e.buy_blocker("gas"))
        self.assertTrue(e.buy("gas", T0))
        self.assertEqual(s["gearUses"]["gas_stove"], it["gas_stove"]["maxUses"])
        self.assertEqual(e.buy_blocker("gas"), "gas_full")
        self.assertEqual(s["inv"].get("gas", 0), 0)  # ячейку не занимает
        # находка в полную горелку и без горелки → монеты по цене баллона
        c = s["coins"]
        e.give_items({"gas": 1}, "t")
        self.assertEqual(s["coins"], c + it["gas"]["price"])
        _, s2, e2 = fresh(w, gear=[])
        s2["stop"] = {"type": "place", "place": "d"}
        self.assertEqual(e2.buy_blocker("gas"), "no_stove")
        c = s2["coins"]
        e2.give_items({"gas": 2}, "t")
        self.assertEqual(s2["coins"], c + 2 * it["gas"]["price"])
        # village: газа нет
        self.assertNotIn("gas", BAL["economy"]["markets"]["village"]["items"])


class FirstAid(unittest.TestCase):
    def test_rescue_once_per_stop(self):
        w = make_world(randoms=[])
        _, s, e = fresh(w, gear=["first_aid"], pack={})
        s["nextRandomAt"] = 1e12
        s["stats"] = {"satiety": 1.0, "water": 90.0, "warmth": 90.0}
        rescue = BAL["items"]["first_aid"]["rescueTo"]
        ok = e._walk(2000.0, T0, on_route=True)  # сытость падает до 0 → аптечка
        self.assertTrue(ok)
        self.assertEqual(s["gearUses"]["first_aid"], BAL["items"]["first_aid"]["uses"] - 1)
        self.assertTrue(s["aidLock"])
        self.assertEqual([j["kind"] for j in s["journal"]].count("first_aid"), 1)
        # второй ноль до следующей остановки — смерть, заряд не тратится
        s["stats"]["satiety"] = 0.5
        ok = e._walk(1000.0, T0, on_route=True)
        self.assertFalse(ok)
        self.assertEqual(s["deaths"], 1)
        self.assertEqual(s["gearUses"]["first_aid"], BAL["items"]["first_aid"]["uses"] - 1)
        self.assertFalse(s["aidLock"])  # смерть снимает блокировку
        self.assertGreater(rescue, 0)

    def test_lock_resets_on_arrival_and_event_zero(self):
        _, s, e = fresh(gear=["first_aid"])
        s["aidLock"] = True
        e._arrive("place", e.w.place_by_id["b"], T0)
        self.assertFalse(s["aidLock"])
        s["stop"] = None
        s["stats"]["warmth"] = 5.0
        died = e._apply_effects({"warmth": "-large"}, T0, None)
        self.assertFalse(died)
        self.assertEqual(s["stats"]["warmth"], float(BAL["items"]["first_aid"]["rescueTo"]))
        died = e._apply_effects({"death": True}, T0, None)  # явная смерть аптечкой не лечится
        self.assertTrue(died)


class Overflow(unittest.TestCase):
    def test_backpack_overflow_actions(self):
        slots = BAL["economy"]["backpackSlots"]
        _, s, e = fresh(pack={"bread": 3, "water": 2})
        s["inv"]["chocolate"] = slots - 5
        s["stop"] = {"type": "place", "place": "b"}
        e.give_items({"pie": 3}, "ev1")
        self.assertEqual(s["overflow"], [{"kind": "backpack", "item": "pie", "n": 3, "source": "ev1"}])
        self.assertFalse(e.continue_journey(T0))
        s["stop"] = None
        s["buffer"] = 5000.0
        e.advance(T0)
        self.assertEqual(s["pos"], 0.0)  # стоит, пока есть решение
        s["stats"] = {"satiety": 40.0, "water": 50.0, "warmth": 50.0}
        self.assertIsNone(e.resolve_overflow_backpack("use", None, T0))
        self.assertEqual(s["stats"]["satiety"], 40.0 + BAL["items"]["pie"]["satiety"])
        self.assertIsNone(e.resolve_overflow_backpack("drop", None, T0))
        self.assertEqual(e.resolve_overflow_backpack("stash", None, T0), "need_swap")
        self.assertEqual(e.resolve_overflow_backpack("stash", {"action": "drop", "item": "pie"}, T0), "bad_swap")
        self.assertIsNone(e.resolve_overflow_backpack("stash", {"action": "use", "item": "water"}, T0))
        self.assertEqual(s["inv"]["pie"], 1)
        self.assertEqual(s["inv"]["water"], 1)
        self.assertEqual(s["overflow"], [])
        self.assertEqual(e.consumables_count(), slots)
        e.advance(T0)
        self.assertGreater(s["pos"], 0.0)

    def test_backpack_overflow_use_hot(self):
        _, s, e = fresh(gear=["gas_stove"], pack={"bread": 3, "tea": 2})
        s["inv"]["chocolate"] = BAL["economy"]["backpackSlots"] - 5
        e.heat(T0)
        e.give_items({"water": 1}, "ev")
        s["stats"]["warmth"] = 30.0
        e.resolve_overflow_backpack("use", None, T0)
        self.assertEqual(s["stats"]["warmth"], 30.0 + BAL["items"]["water"]["heat"])
        self.assertFalse(s["heated"])

    def test_gear_overflow(self):
        _, s, e = fresh(gear=["socks", "raincoat", "gas_stove"])
        e.give_items({"first_aid": 1}, "q")  # 4-я ячейка свободна
        self.assertEqual(s["gear"], ["socks", "raincoat", "gas_stove", "first_aid"])
        self.assertEqual(s["gearUses"]["first_aid"], BAL["items"]["first_aid"]["uses"])
        e.give_items({"compass": 1}, "q2")
        self.assertEqual(s["overflow"], [{"kind": "gear", "item": "compass", "n": 1, "source": "q2"}])
        self.assertEqual(e.resolve_overflow_gear(["socks", "raincoat", "gas_stove"]), "bad_keep")
        self.assertEqual(e.resolve_overflow_gear(["socks", "raincoat", "gas_stove", "flask"]), "bad_keep")
        self.assertIsNone(e.resolve_overflow_gear(["socks", "raincoat", "compass", "first_aid"]))
        self.assertEqual(s["gear"], ["socks", "raincoat", "first_aid", "compass"])
        self.assertNotIn("gas_stove", s["gearUses"])
        # «Оставить как есть» = выбросить новую
        e.give_items({"flask": 1}, "q3")
        self.assertIsNone(e.resolve_overflow_gear(list(s["gear"])))
        self.assertNotIn("flask", s["gear"])
        self.assertEqual(s["overflow"], [])

    # --- V5-43: дары духов не занимают ячейки снаряжения
    def test_gifts_do_not_take_gear_slots(self):
        _, s, e = fresh(gear=["socks", "raincoat", "gas_stove"])
        e.give_items({"first_aid": 1, "amulet_leshy": 1, "twig_leshy": 1, "ember_domovoy": 1}, "q")
        self.assertEqual(s["gear"], ["socks", "raincoat", "gas_stove", "first_aid", "amulet_leshy", "twig_leshy",
                                     "ember_domovoy"])
        self.assertEqual(s["overflow"], [])
        self.assertEqual(e.gear_used(), 4)
        # перки даров действуют как у снаряжения
        self.assertAlmostEqual(e.risk_factor(), 1.0 - BAL["items"]["amulet_leshy"]["riskReduce"])
        self.assertEqual(e.gear_mult("idleWarmthMult"), BAL["items"]["ember_domovoy"]["idleWarmthMult"])
        # обычная вещь при 4 занятых ячейках — переполнение; в выборе только обычное снаряжение, дары на местах
        e.give_items({"compass": 1}, "q2")
        self.assertEqual(len(s["overflow"]), 1)
        self.assertEqual(e.resolve_overflow_gear(["socks", "raincoat", "gas_stove", "first_aid", "amulet_leshy"]),
                         "bad_keep")
        self.assertIsNone(e.resolve_overflow_gear(["socks", "raincoat", "first_aid", "compass"]))
        self.assertEqual(s["gear"], ["socks", "raincoat", "first_aid", "amulet_leshy", "twig_leshy", "ember_domovoy",
                                     "compass"])
        # повтор дара не стакается: монеты-компенсация по цене дара (0) — фактически игнор
        coins = s["coins"]
        e.give_items({"twig_leshy": 1}, "q3")
        self.assertEqual(s["gear"].count("twig_leshy"), 1)
        self.assertEqual(s["coins"], coins)
        self.assertEqual(s["overflow"], [])

    def test_gift_in_old_overflow_is_taken(self):
        _, s, e = fresh(gear=["socks", "raincoat", "gas_stove"])
        e.give_items({"flask": 1}, "q")
        s["overflow"].append({"kind": "gear", "item": "ribbon_rusalka", "n": 1, "source": "old"})
        self.assertIsNone(e.resolve_overflow_gear([]))
        self.assertIn("ribbon_rusalka", s["gear"])
        self.assertEqual(s["overflow"], [])

    def test_drop_item(self):
        _, s, e = fresh(gear=["socks", "gas_stove"], pack={"bread": 2})
        e.give_items({"twig_leshy": 1, "pearl_rusalka": 1, "matches": 1}, "q")
        self.assertEqual(e.drop_item("twig_leshy"), "gift")
        self.assertEqual(e.drop_item("pearl_rusalka"), "gift")
        self.assertIn("twig_leshy", s["gear"])
        self.assertIsNone(e.drop_item("gas_stove"))
        self.assertNotIn("gas_stove", s["gear"])
        self.assertNotIn("gas_stove", s["gearUses"])
        self.assertIsNone(e.drop_item("bread"))
        self.assertEqual(s["inv"]["bread"], 1)
        self.assertIsNone(e.drop_item("matches"))
        self.assertNotIn("matches", s["inv"])
        self.assertEqual(e.drop_item("compass"), "no_item")

    def test_duplicates_and_remove(self):
        it = BAL["items"]
        _, s, e = fresh(gear=["socks", "first_aid"])
        c = s["coins"]
        e.give_items({"socks": 1}, "x")
        self.assertEqual(s["coins"], c + int(it["socks"]["price"] * BAL["economy"]["duplicateGearShare"]))
        s["gearUses"]["first_aid"] = 0
        e.give_items({"first_aid": 1}, "x")
        self.assertEqual(s["gearUses"]["first_aid"], it["first_aid"]["uses"])
        e._apply_effects({"remove": {"socks": 1}}, T0, None)
        self.assertEqual(s["gear"], ["first_aid"])
        self.assertTrue(e.choice_available({"requires": {"item": "first_aid"}}))
        self.assertFalse(e.choice_available({"requires": {"item": "socks"}}))

    def test_buy_blocked_when_full(self):
        _, s, e = fresh(gear=["socks", "raincoat", "gas_stove"], pack={"bread": 3, "water": 2})
        s["gear"].append("flask")  # 4-я ячейка — находка в пути
        s["inv"].update({"water": 3, "tea": 1})
        s["stop"] = {"type": "place", "place": "d"}
        s["coins"] = 500
        self.assertEqual(e.buy_blocker("bread"), "backpack_full")
        self.assertEqual(e.buy_blocker("compass"), "gear_full")
        self.assertEqual(e.buy_blocker("socks"), "have_gear")
        self.assertFalse(e.buy("compass", T0))
        self.assertEqual(s["overflow"], [])

    def test_death_clears_overflow_keeps_gear(self):
        _, s, e = fresh(gear=["socks", "raincoat", "gas_stove"], pack={"bread": 3, "water": 2})
        s["gear"].append("flask")
        s["inv"].update({"water": 3, "tea": 1})
        e.give_items({"pie": 1, "compass": 1}, "x")
        self.assertEqual(len(s["overflow"]), 2)
        e._die(T0, "event")
        self.assertEqual(s["overflow"], [])
        self.assertEqual(s["gear"], ["socks", "raincoat", "gas_stove", "flask"])


class Saves(unittest.TestCase):
    def test_roundtrip_and_migration(self):
        w, s, e = fresh(gear=["gas_stove"], pack={"water": 1})
        e.heat(T0)
        e.give_items({"pie": 9}, "x")
        back = json.loads(json.dumps(s))
        self.assertEqual(back, s)
        old = {"v": 1, "coins": 10, "inv": {"bread": 2, "socks": 2, "raincoat": 1, "matches": 1}}
        m = migrate_state(w, old)
        self.assertEqual(m["v"], 2)
        self.assertEqual(m["gear"], ["socks", "raincoat"])
        self.assertEqual(m["inv"], {"bread": 2, "matches": 1})
        self.assertEqual(m["coins"], 10 + int(BAL["items"]["socks"]["price"] * BAL["economy"]["duplicateGearShare"]))
        self.assertTrue(m["loadoutDone"])
        self.assertEqual(m["overflow"], [])


class AddendumA(unittest.TestCase):
    def test_portions(self):
        it = BAL["items"]["thermos"]
        n = it["portions"]
        _, s, e = fresh(gear=["gas_stove"], pack={"thermos": 2})
        self.assertEqual(e.portions_total("thermos"), 2 * n)
        s["stats"] = {"satiety": 50.0, "water": 10.0, "warmth": 30.0}
        e.heat(T0)
        e.use_item("thermos", T0)  # горячая порция: бонус heat и сброс heated
        self.assertEqual(s["stats"]["water"], 10.0 + it["water"])
        self.assertEqual(s["stats"]["warmth"], 30.0 + it["heat"])
        self.assertFalse(s["heated"])
        self.assertEqual(s["inv"]["thermos"], 2)
        self.assertEqual(s["portionsLeft"]["thermos"], n - 1)
        for _ in range(n - 1):
            e.use_item("thermos", T0)
        self.assertEqual(s["inv"]["thermos"], 1)
        self.assertNotIn("thermos", s["portionsLeft"])
        self.assertEqual(e.portions_total("thermos"), n)
        self.assertEqual(e.consumables_count(), 1)  # одна ячейка, не n

    def test_portions_swap_and_overflow(self):
        _, s, e = fresh(pack={"thermos": 1, "bread": 3})
        s["inv"]["water"] = BAL["economy"]["backpackSlots"] - 4
        e.give_items({"thermos": 1}, "x")
        self.assertEqual(s["overflow"][0]["item"], "thermos")
        self.assertEqual(e.resolve_overflow_backpack("stash", {"action": "use", "item": "thermos"}, T0), "swap_not_free")
        self.assertIsNone(e.resolve_overflow_backpack("stash", {"action": "drop", "item": "bread"}, T0))
        self.assertEqual(s["inv"]["thermos"], 2)  # пришёл целым

    def test_clew(self):
        cd = BAL["items"]["ball_yaga"]["ability"]["cooldownDays"]
        choices = [
            {"id": "a", "risk": "none", "outcomes": [{"weight": 1, "effects": {"coins": "small"}}, {"weight": 1, "effects": {}}]},
            {"id": "b", "risk": "low", "outcomes": [{"weight": 1, "effects": {"coins": "small"}}, {"weight": 1, "effects": {"warmth": "-small"}}]},
            {"id": "c", "risk": "fatal", "outcomes": [{"weight": 3, "effects": {}}, {"weight": 1, "effects": {"death": True}}]},
            {"id": "d", "risk": "none", "outcomes": [{"weight": 1, "effects": {"remove": {"bread": 1}, "give": {"pie": 1}}}]},
            {"id": "f", "risk": "none", "outcomes": [{"weight": 1, "effects": {"delay": "short"}}]},
        ]
        w = make_world(randoms=[ev("r", "city", choices=choices)])
        _, s, e = fresh(w)
        s["stop"] = {"type": "event", "event": "r", "random": True}
        self.assertEqual(e.clew_status(T0), "no_item")
        s["inv"]["ball_yaga"] = 1
        self.assertEqual(e.clew_status(T0), "ready")
        rng0 = s["rng"]
        self.assertEqual(e.ask_clew(T0), {"a": "reward", "b": "risk", "c": "death", "d": "mixed", "f": "penalty"})
        self.assertEqual(s["rng"], rng0)
        self.assertEqual(e.clew_status(T0), "cooldown")
        self.assertEqual(e.ability_cooldown_days("ball_yaga", T0), cd)
        self.assertIsNone(e.ask_clew(T0))
        self.assertEqual(e.clew_status(T0 + cd * MS_DAY), "ready")
        s["stop"] = None
        self.assertEqual(e.clew_status(T0 + cd * MS_DAY), "no_event")

    def test_regional_market(self):
        b = copy.deepcopy(BAL)
        b["economy"]["markets"]["regional"] = {"b": ["pie", "bread"]}
        w = make_world(balance=b)
        _, s, e = fresh(w)
        s["stop"] = {"type": "place", "place": "b"}
        ids = [i for i, _ in e.market()]
        self.assertEqual(ids[-1], "pie")
        self.assertEqual(ids.count("bread"), 1)
        s["stop"] = {"type": "place", "place": "c"}
        self.assertNotIn("pie", [i for i, _ in e.market()])

    def test_recent_per_zone(self):
        rnd = [ev(f"c{i}", "city") for i in range(4)] + [ev(f"w{i}", "wild") for i in range(10)]
        w = make_world(randoms=rnd)
        _, s, e = fresh(w)
        s["pos"] = 1000.0
        seen = [e._pick_random(T0)["id"] for _ in range(6)]
        # пул города 4 → недавними считаются последние 2 городских: подряд одинаковых и «через одно» нет
        for a, b2, c in zip(seen, seen[1:], seen[2:]):
            self.assertNotIn(a, (b2, c))
        self.assertFalse([j for j in s["journal"] if j["kind"] == "zone_fallback"])
        self.assertLessEqual(len(s["recentRandom"]), BAL["randomEvents"]["recentKeep"])


def choice(cid, eff, risk="none", weight=1, more=()):
    return {"id": cid, "text": cid, "risk": risk,
            "outcomes": [{"weight": weight, "text": "x", "effects": eff}] + list(more)}


def gifts_world(randoms=None, water_places=("b",)):
    b = copy.deepcopy(BAL)
    b["gifts"]["waterPlaces"] = list(water_places)
    return make_world(balance=b, randoms=randoms)


def at_event(s, eid):
    s["stop"] = {"type": "event", "event": eid, "random": True}


class Gifts(unittest.TestCase):
    """v5.3-§13: дары духов, условные перки, привал, лапоть, венок, продажа, новое снаряжение."""

    def test_all_folklore_gifts_present_and_poputchik(self):
        import re
        doc = (ROOT / "docs" / "v5" / "folklore-gifts.md").read_text(encoding="utf-8")
        ids = set(re.findall(r"^\| `([a-z_]+)` \|", doc, re.M))
        self.assertGreaterEqual(len(ids), 18)
        for i in ids:
            self.assertIn(i, BAL["items"], i)
        self.assertTrue(50 <= len(BAL["items"]) <= 60, len(BAL["items"]))
        q = json.loads((ROOT / "app" / "assets" / "content" / "quests.json").read_text(encoding="utf-8"))
        pop = json.dumps(next(x for x in q if x["id"] == "q_poputchik"), ensure_ascii=False)
        self.assertNotIn("ball_yaga", pop)
        self.assertIn("compass_ded", pop)

    def test_thread_spent_before_ball_then_vanishes(self):
        w = gifts_world(randoms=[ev("e", "wild", choices=[choice("a", {"coins": "small"}), choice("b", {"warmth": "-small"})], art="road")])
        _, s, e = fresh(w)
        e.give_items({"ball_yaga": 1, "thread_yaga": 1}, "t")
        self.assertEqual(s["gearUses"]["thread_yaga"], BAL["items"]["thread_yaga"]["uses"])
        at_event(s, "e")
        for left in range(BAL["items"]["thread_yaga"]["uses"] - 1, -1, -1):
            self.assertEqual(e.clew_item(T0), "thread_yaga")
            self.assertEqual(e.ask_clew(T0), {"a": "reward", "b": "penalty"})
        self.assertNotIn("thread_yaga", s["inv"])
        self.assertNotIn("thread_yaga", s["gearUses"])
        self.assertEqual(e.clew_item(T0), "ball_yaga")
        e.ask_clew(T0)
        self.assertEqual(e.clew_status(T0), "cooldown")

    def test_spirit_hint_only_in_own_events(self):
        cs = [choice("a", {}), choice("b", {"death": True}, risk="fatal", more=[{"weight": 1, "text": "y", "effects": {}}])]
        w = gifts_world(randoms=[ev("forest", "wild", choices=cs, art="forest"), ev("town", "city", choices=cs, art="town")])
        _, s, e = fresh(w)
        e.give_items({"twig_leshy": 1}, "t")
        at_event(s, "town")
        self.assertEqual(e.clew_status(T0), "not_here")
        self.assertIsNone(e.ask_clew(T0))
        at_event(s, "forest")
        self.assertEqual(e.clew_status(T0), "ready")
        self.assertEqual(e.ask_clew(T0), {"a": "neutral", "b": "death"})
        cd = BAL["items"]["twig_leshy"]["hint"]["cooldownDays"]
        self.assertEqual(e.ability_cooldown_days("twig_leshy:hint", T0), cd)
        self.assertEqual(e.clew_status(T0), "cooldown")
        # клубок есть — подсказка духа тратится первой, клубок остаётся готовым
        _, s, e = fresh(w)
        e.give_items({"twig_leshy": 1, "ball_yaga": 1}, "t")
        at_event(s, "forest")
        self.assertEqual(e.clew_item(T0), "twig_leshy")
        e.ask_clew(T0)
        self.assertEqual(e.clew_item(T0), "ball_yaga")
        at_event(s, "town")
        self.assertEqual(e.clew_item(T0), "ball_yaga")

    def test_guide_cancels_delay_and_detour_only(self):
        w = gifts_world(randoms=[ev("e", "wild", choices=[choice("go", {"delay": "medium", "detour": "short", "warmth": "-small"}),
                                                          choice("no", {})], art="road")])
        _, s, e = fresh(w)
        e.give_items({"twig_leshy": 1}, "t")
        self.assertEqual(e.gift_status("twig_leshy", T0), "nothing")
        at_event(s, "e")
        s["stats"]["warmth"] = 60.0
        self.assertTrue(e.choose("go", T0)["ok"])
        self.assertGreater(s["delayUntil"], T0)
        self.assertIsNotNone(s["detour"])
        self.assertEqual(e.gift_status("twig_leshy", T0), "ready")
        self.assertEqual(e.use_gift("twig_leshy", T0), "ok")
        self.assertEqual(s["delayUntil"], 0)
        self.assertIsNone(s["detour"])
        self.assertEqual(s["stats"]["warmth"], 60.0 - BAL["levels"]["stat"]["small"])  # остальное остаётся
        self.assertIsNotNone(s["undo"])  # минус тепла ещё можно снять «Бусиной»
        self.assertEqual(e.gift_status("twig_leshy", T0), "cooldown")
        self.assertEqual(e.gift_status("twig_leshy", T0 + MS_DAY), "nothing")
        e.advance(T0)
        self.assertIsNone(s["undo"])  # кнопка живёт только до «Идти дальше»
        # еловая лапка: 3 заряда без перезарядки, потом исчезает
        _, s, e = fresh(w)
        e.give_items({"spruce_leshy": 1}, "t")
        for _ in range(BAL["items"]["spruce_leshy"]["uses"]):
            at_event(s, "e")
            e.choose("go", T0)
            self.assertEqual(e.use_gift("spruce_leshy", T0), "ok")
        self.assertFalse(e.has_item("spruce_leshy"))

    def test_mirage_undoes_all_harm_keeps_gains(self):
        eff = {"coins": "-medium", "satiety": "-large", "water": "small", "remove": {"bread": 1, "socks": 1},
               "give": {"berries": 1}, "bonus_reset": True, "delay": "short", "flag": "f1"}
        w = gifts_world(randoms=[ev("e", "wild", choices=[choice("bad", eff), choice("ok", {})], art="swamp")])
        _, s, e = fresh(w, gear=["socks"], pack={"bread": 2})
        e.give_items({"bead_kikimora": 1}, "t")
        s["coins"], s["bonusKm"] = 50, 33.0
        s["stats"] = {"satiety": 80.0, "water": 50.0, "warmth": 50.0}
        at_event(s, "e")
        e.choose("bad", T0)
        self.assertEqual(s["coins"], 50 - BAL["levels"]["coins"]["medium"])
        self.assertNotIn("socks", s["gear"])
        self.assertEqual(e.use_gift("bead_kikimora", T0), "ok")
        self.assertEqual(s["coins"], 50)
        self.assertEqual(s["stats"]["satiety"], 80.0)
        self.assertEqual(s["stats"]["water"], 50.0 + BAL["levels"]["stat"]["small"])  # плюс остаётся
        self.assertEqual(s["inv"]["bread"], 2)
        self.assertEqual(s["inv"]["berries"], 1)
        self.assertIn("socks", s["gear"])
        self.assertEqual((s["bonusKm"], s["delayUntil"]), (33.0, 0))
        self.assertIn("f1", s["flags"])
        self.assertEqual(e.ability_cooldown_days("bead_kikimora", T0), BAL["items"]["bead_kikimora"]["ability"]["cooldownDays"])
        self.assertEqual([j["kind"] for j in s["journal"]][-1], "gift")

    def test_mirage_not_after_death(self):
        dead = choice("die", {"death": True}, risk="fatal")
        w = gifts_world(randoms=[ev("e", "wild", choices=[dead, choice("ok", {})], art="swamp")])
        _, s, e = fresh(w)
        e.give_items({"kudel_kikimora": 1}, "t")
        at_event(s, "e")
        self.assertTrue(e.choose("die", T0)["died"])
        self.assertIsNone(s["undo"])
        self.assertEqual(e.gift_status("kudel_kikimora", T0), "nothing")

    def test_actions_where_and_charges(self):
        w = gifts_world()
        _, s, e = fresh(w)
        e.give_items({"venik_bannik": 1, "stone_bannik": 1, "hook_vodyanoy": 1, "key_ovinnik": 1, "sheaf_ovinnik": 1}, "t")
        s["stats"]["warmth"] = 40.0
        self.assertEqual(e.gift_status("venik_bannik", T0), "not_here")  # не на привале
        self.assertEqual(e.use_gift("stone_bannik", T0), "ok")  # камешек — где угодно
        self.assertEqual(s["stats"]["warmth"], 60.0)
        s["stop"] = {"type": "place", "place": "b"}  # посёлок у воды: зона city
        s["pos"] = w.pos_of["b"]
        self.assertEqual(e.use_gift("venik_bannik", T0), "ok")
        self.assertEqual(s["stats"]["warmth"], 90.0)
        self.assertEqual(e.gift_status("venik_bannik", T0), "cooldown")
        self.assertEqual(e.gift_status("key_ovinnik", T0), "not_here")  # овин — только в пригороде
        n = BAL["items"]["hook_vodyanoy"]["uses"]
        for d in range(n):
            self.assertEqual(e.use_gift("hook_vodyanoy", T0 + d * MS_DAY), "ok")
            self.assertEqual(e.gift_status("hook_vodyanoy", T0 + d * MS_DAY) if d < n - 1 else "cooldown", "cooldown")
        self.assertEqual(s["inv"]["fish"], n)
        self.assertFalse(e.has_item("hook_vodyanoy"))
        s["stop"] = {"type": "place", "place": "c"}  # деревня, не у воды, пригород
        s["pos"] = w.pos_of["c"]
        s["stats"]["warmth"] = 30.0
        self.assertEqual(e.use_gift("key_ovinnik", T0), "ok")
        self.assertEqual(s["stats"]["warmth"], float(BAL["stats"]["max"]))
        self.assertEqual(e.gift_status("sheaf_ovinnik", T0), "nothing")  # тепло полное — заряд не тратим
        self.assertEqual(e.ability_cooldown_days("key_ovinnik", T0), BAL["items"]["key_ovinnik"]["ability"]["cooldownDays"])

    def test_shell_free_toll_and_camp_water(self):
        w = gifts_world(randoms=[ev("river", "wild", choices=[choice("pay", {"coins": "-small"}), choice("no", {})], art="river"),
                                 ev("road", "wild", choices=[choice("pay", {"coins": "-small"}), choice("no", {})], art="road")])
        _, s, e = fresh(w)
        e.give_items({"shell_vodyanoy": 1}, "t")
        s["coins"] = 30
        at_event(s, "river")
        e.choose("pay", T0)
        self.assertEqual(s["coins"], 30)
        self.assertIsNone(s["undo"])
        at_event(s, "road")
        e.choose("pay", T0)
        self.assertEqual(s["coins"], 30 - BAL["levels"]["coins"]["small"])
        s["stats"]["water"] = 10.0
        tb = BAL["town"]
        e._arrive("place", w.place_by_id["b"], T0)
        self.assertEqual(s["stats"]["water"], 10.0 + tb["waterRefill"] + 10)
        e._arrive("place", w.place_by_id["b"], T0)  # раз в игровой день
        self.assertEqual(s["stats"]["water"], 10.0 + 2 * tb["waterRefill"] + 10)
        e._arrive("place", w.place_by_id["c"], T0 + MS_DAY)  # не у воды
        self.assertEqual(s["stats"]["water"], 10.0 + 3 * tb["waterRefill"] + 10)

    def test_ribbon_water_risk_and_fish(self):
        ch = {"id": "x", "risk": "fatal", "outcomes": [{"weight": 3, "effects": {}}, {"weight": 1, "effects": {"death": True}}]}
        _, s, e = fresh(gifts_world())
        e.give_items({"ribbon_rusalka": 1}, "t")
        sc = BAL["riskReduce"]["weightScale"]
        self.assertEqual(e.outcome_weights(ch), [3, 1])
        self.assertEqual(e.outcome_weights(ch, ["water"]), [3 * sc, py_round(sc * (1 - 0.25))])
        s["stats"]["satiety"] = 10.0
        s["inv"]["fish"] = 1
        e.use_item("fish", T0)
        self.assertEqual(s["stats"]["satiety"], 10.0 + py_round(BAL["items"]["fish"]["satiety"] * 1.5))  # 52.5 → 52

    def test_ear_midday_and_heat(self):
        w = gifts_world()
        _, s, e = fresh(w)
        e.give_items({"ear_poludnitsa": 1}, "t")
        w.weather_at = lambda seed, pos: "cloudy"
        dk = BAL["drainPerKm"]

        def water_loss(now):
            s["stats"] = {"satiety": 50.0, "water": 50.0, "warmth": 50.0}
            e._drain_walk(1.0, now)
            return 50.0 - s["stats"]["water"], 50.0 - s["stats"]["satiety"]

        noon, night = T0 + 2 * MS_HOUR, T0 + 10 * MS_HOUR  # 13:00 и 21:00 МСК
        self.assertTrue(e.is_midday(noon))
        self.assertFalse(e.is_midday(night))
        self.assertAlmostEqual(water_loss(night)[0], dk["water"], places=9)
        self.assertAlmostEqual(water_loss(noon)[0], dk["water"] * 0.7, places=9)
        self.assertAlmostEqual(water_loss(night)[1], dk["satiety"] * 0.92, places=9)
        w.weather_at = lambda seed, pos: "heat"
        self.assertAlmostEqual(water_loss(night)[0], dk["water"] * BAL["weather"]["types"]["heat"]["water"] * 0.7, places=9)

    def test_lapot_upkeep_and_wreath_expiry(self):
        _, s, e = fresh(gifts_world(), pack={"bread": 1, "water": 1})
        e.give_items({"pie": 1, "lapot_domovoy": 1, "wreath_poludnitsa": 1}, "t")
        self.assertTrue(s["fed"]["lapot_domovoy"])
        self.assertAlmostEqual(e.gear_mult("warmthDrainMult"), 0.9)
        e.apply_time(T0 + MS_DAY)
        self.assertNotIn("bread", s["inv"])  # хлеб первым
        self.assertTrue(s["fed"]["lapot_domovoy"])
        e.apply_time(T0 + 2 * MS_DAY)  # осталась одна еда — последнюю домовой не берёт
        self.assertEqual(s["inv"]["pie"], 1)
        self.assertFalse(s["fed"]["lapot_domovoy"])
        self.assertEqual(e.gear_mult("warmthDrainMult"), 1.0)
        self.assertIn("wreath_poludnitsa", s["gear"])
        e.apply_time(T0 + 3 * MS_DAY)
        self.assertNotIn("wreath_poludnitsa", s["gear"])
        self.assertNotIn("wreath_poludnitsa", s["expires"])
        self.assertIn("wilt", [j["kind"] for j in s["journal"]])

    def test_camp_sleeping_bag_and_idle_floor(self):
        w = gifts_world(water_places=())
        _, s, e = fresh(w, gear=["sleeping_bag"])
        s["stats"]["warmth"] = 20.0
        e._arrive("place", w.place_by_id["c"], T0)
        self.assertEqual(s["stats"]["warmth"], 20.0 + BAL["town"]["warmthRestore"] + 15)
        e.give_items({"ember_domovoy": 1}, "t")
        s["stats"] = {"satiety": 90.0, "water": 90.0, "warmth": 90.0}
        s["lastTick"] = T0
        e.apply_time(T0 + 10 * MS_HOUR)
        self.assertAlmostEqual(90.0 - s["stats"]["warmth"], BAL["drainPerHour"]["warmth"] * 0.35 * 10, places=9)

    def test_sell_pearl(self):
        _, s, e = fresh(gifts_world())
        e.give_items({"pearl_rusalka": 1}, "t")
        self.assertEqual(e.sell_blocker("pearl_rusalka"), "no_market")
        s["stop"] = {"type": "place", "place": "c"}
        self.assertEqual(e.sell_offers(), [("pearl_rusalka", 40)])
        c0 = s["coins"]
        self.assertTrue(e.sell("pearl_rusalka", T0))
        self.assertEqual(s["coins"], c0 + 40)
        self.assertFalse(e.has_item("pearl_rusalka"))
        self.assertEqual(e.sell_blocker("bread"), "no_item")

    def test_space_blanket_only_for_cold(self):
        _, s, e = fresh(gifts_world())
        e.give_items({"space_blanket": 1}, "t")
        s["stats"] = {"satiety": 50.0, "water": 0.0, "warmth": 50.0}
        self.assertFalse(e._try_rescue(T0))
        s["stats"] = {"satiety": 50.0, "water": 50.0, "warmth": 0.0}
        self.assertTrue(e._try_rescue(T0))
        self.assertEqual(s["stats"]["warmth"], 30.0)
        self.assertEqual(s["gearUses"]["space_blanket"], 0)

    def test_new_perk_keys(self):
        w = make_world()
        keys = lambda i: [p["key"] for p in w.item_perks(i)]  # noqa: E731
        self.assertEqual(keys("twig_leshy"), ["ability_guide", "hint"])
        self.assertEqual(keys("shell_vodyanoy"), ["hint", "campWaterAtWater", "noCoinLossAtWater"])
        self.assertEqual(w.item_perks("ear_poludnitsa"), [{"key": "satietyDrain", "value": 8},
                                                          {"key": "waterDrainAtMiddayHeat", "value": 30}])
        self.assertEqual(keys("ribbon_rusalka"), ["riskAtWater", "boostFishSatiety"])
        self.assertEqual(keys("sleeping_bag"), ["idleWarmth", "campWarmth"])
        self.assertEqual(keys("hook_vodyanoy"), ["uses", "ability_action", "actionGive_fish"])
        self.assertEqual(keys("space_blanket"), ["rescueWarmth", "uses"])
        self.assertEqual(keys("lapot_domovoy"), ["warmthDrain", "idleWarmth", "upkeep"])
        self.assertEqual(keys("pearl_rusalka"), ["sell"])
        self.assertEqual(keys("valdai_baranki"), ["satiety", "portions"])

    def test_regional_markets_real_places(self):
        real = load_world(ROOT)
        reg = BAL["economy"]["markets"]["regional"]
        for pid, lst in reg.items():
            self.assertIn(pid, real.place_by_id)
            for i in lst:
                self.assertIn(i, BAL["items"])
        s = new_state(real, 1, T0, "2026-05-01")
        e = Engine(real, s)
        s["stop"] = {"type": "place", "place": "petrozavodsk"}
        ids = [i for i, _ in e.market()]
        self.assertIn("kalitka_potato", ids)
        self.assertIn("rybnik", ids)


if __name__ == "__main__":
    unittest.main(verbosity=1)

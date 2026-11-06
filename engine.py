"""Эталонный движок «Путника» (Python). Dart-версия — app/lib/engine/ — повторяет его правило в правило.

Используется симулятором баланса (tools/sim/simulate.py), фикстурой совпадения (make_parity_fixture.py)
и тестами правил (test_v53.py). Все числа — из balance.json, все тексты — из content/*.json.
Контракт для Dart и интерфейса — docs/v5/08-engine-api-v5.3.md (v5.3: зоны, снаряжение, заряды,
«Нагреть», переполнение, стартовый набор; §13 — дары духов: guide/mirage/action/hint, условные перки,
привал, лапоть, венок, продажа).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

STATS = ("satiety", "water", "warmth")
CONSUMABLE = ("food", "drink")
MS_HOUR = 3_600_000
MS_DAY = 86_400_000
STATE_VERSION = 2
_RANK = {"city": 2, "suburb": 1, "wild": 0}


# ---------------------------------------------------------------- RNG
class Rng:
    """32-битный LCG — одинаков в Python и Dart."""

    def __init__(self, state: int):
        self.state = state & 0xFFFFFFFF

    def next_u32(self) -> int:
        self.state = (self.state * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.state

    def next_float(self) -> float:
        return self.next_u32() / 4294967296.0

    def pick_weighted(self, weights: list[int]) -> int:
        total = sum(weights)
        r = self.next_u32() % total
        acc = 0
        for i, w in enumerate(weights):
            acc += w
            if r < acc:
                return i
        return len(weights) - 1


def hash32(*parts: int) -> int:
    """Детерминированный хэш для погоды (не трогает основной RNG)."""
    h = 2166136261
    for p in parts:
        for b in (p & 0xFFFFFFFF).to_bytes(4, "little"):
            h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def py_round(x: float) -> int:
    """round() Python: к ближайшему, середина — к чётному (в Dart — pyRound из world.dart)."""
    return int(round(x))


# ---------------------------------------------------------------- World (контент + маршрут)
class World:
    def __init__(self, balance: dict, content: dict, place_positions: dict[str, float], total_length_m: float):
        self.b = balance
        self.places = content["places"]
        self.place_by_id = {p["id"]: p for p in self.places}
        self.pos_of = place_positions  # id -> метры от старта
        self.length = total_length_m
        self.chapters = content["chapters"]
        self.items = balance["items"]
        self.quests = {q["id"]: q for q in content.get("quests", [])}
        self.randoms = content.get("events_random", [])
        self.events_by_id: dict[str, dict] = {}
        self.anchored: list[tuple[float, dict]] = []
        for e in content.get("events_anchored", []):
            self.events_by_id[e["id"]] = e
            if e.get("detour_only"):
                continue
            a = e["anchor"]
            self.anchored.append((self.pos_of[a["after"]] + a["km"] * 1000.0, e))
        for e in self.randoms:
            self.events_by_id[e["id"]] = e
        self.anchored.sort(key=lambda t: t[0])
        # Придорожные точки (кафе, АЗС) — добавляются в длинные пустые отрезки, чтобы не было «голодных» перегонов
        self._add_roadside()
        # Остановки-точки (по порядку)
        self.stops_places = sorted(((self.pos_of[p["id"]], p) for p in self.places if p["kind"] != "start"),
                                   key=lambda t: t[0])
        self.chapter_end = {c["to"]: c for c in self.chapters}
        # Зоны: (позиция, радиус города, радиус пригорода) в метрах — по всем местам, включая придорожные
        by_kind = self.b["zones"]["byKind"]
        self.zone_points: list[tuple[float, float, float]] = []
        for p in self.places:
            r = by_kind.get(p["kind"])
            if r is None:
                continue  # вид места без зоны (например, landmark) не влияет
            self.zone_points.append((self.pos_of[p["id"]], r["urban"] * 1000.0, (r["urban"] + r["suburb"]) * 1000.0))
        self._zone_pool: dict[str, int] = {}
        for e in self.randoms:
            if e.get("zone"):
                self._zone_pool[e["zone"]] = self._zone_pool.get(e["zone"], 0) + 1

    def _add_roadside(self):
        rs = self.b["roadside"]
        gap_max = rs["maxGapKm"] * 1000.0
        names = rs["names"]
        ordered = sorted(self.places, key=lambda p: self.pos_of[p["id"]])
        extra, k = [], 0
        for a, b in zip(ordered, ordered[1:]):
            pa, pb = self.pos_of[a["id"]], self.pos_of[b["id"]]
            n = int((pb - pa) // gap_max)
            for i in range(1, n + 1):
                pos = pa + (pb - pa) * i / (n + 1)
                pid = f"rs_{k}"
                extra.append({"id": pid, "name": names[k % len(names)], "kind": "roadside", "market": "village",
                              "chapter": b["chapter"], "desc": "", "virtual": True})
                self.pos_of[pid] = pos
                k += 1
        self.places = sorted(self.places + extra, key=lambda p: self.pos_of[p["id"]])
        self.place_by_id = {p["id"]: p for p in self.places}

    # ------------------------------------------------ зоны пути
    def zone_at(self, pos: float) -> str:
        """Зона точки пути (м от старта): самая «городская» из зон всех мест, в радиус которых она попадает.
        Радиус 0 — такой зоны у места нет (у деревни нет «города» даже в её точке)."""
        best = "wild"
        for ppos, urban, outer in self.zone_points:
            d = abs(pos - ppos)
            z = "city" if urban > 0 and d <= urban else "suburb" if outer > 0 and d <= outer else "wild"
            if _RANK[z] > _RANK[best]:
                best = z
        return best

    def zone_pool_size(self, zone: str) -> int:
        return self._zone_pool.get(zone, 0)

    def event_zone(self, eid: str) -> str | None:
        e = self.events_by_id.get(eid)
        return e.get("zone") if e else None

    # ------------------------------------------------ каталог
    def item_type(self, item: str) -> str:
        return self.items.get(item, {}).get("type", "tool")

    def starter_gear(self) -> list[str]:
        return [k for k, v in self.items.items() if v.get("starter") and v.get("type") == "gear"]

    def starter_pack(self) -> list[str]:
        return [k for k, v in self.items.items() if v.get("starter") and v.get("type") in CONSUMABLE]

    def loadout_error(self, gear: list[str], pack: dict[str, int]) -> str | None:
        """Проверка старт-набора без состояния (экран «Собери рюкзак» до создания героя). None — годится."""
        lo = self.b["loadout"]
        if len(gear) > lo["maxGear"]:
            return "gear_too_many"
        if len(set(gear)) != len(gear):
            return "gear_duplicate"
        starter_gear = set(self.starter_gear())
        if any(g not in starter_gear for g in gear):
            return "gear_not_starter"
        starter_pack = set(self.starter_pack())
        if any(k not in starter_pack for k in pack):
            return "pack_not_starter"
        if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in pack.values()):
            return "pack_bad_count"
        if any(n > lo["maxPerKind"] for n in pack.values()):
            return "pack_kind_limit"
        if sum(pack.values()) > lo["maxPackSlots"]:
            return "pack_too_many"
        return None

    def heatable(self, item: str) -> bool:
        return self.items.get(item, {}).get("heat", 0) > 0

    def item_perks(self, item: str) -> list[dict]:
        """Перки предмета для экрана снаряжения: [{key, value}] — порядок фиксирован (см. API-док, §6)."""
        it = self.items.get(item, {})
        out: list[dict] = []

        def pct(mult: float) -> int:
            return py_round((1.0 - mult) * 100.0)

        for stat in STATS:
            if it.get("type") in CONSUMABLE and it.get(stat, 0) > 0:
                out.append({"key": stat, "value": int(it[stat])})
        if it.get("heat", 0) > 0:
            out.append({"key": "heat", "value": int(it["heat"])})
        if "warmthDrainMult" in it:
            out.append({"key": "warmthDrain", "value": pct(it["warmthDrainMult"])})
        if "weatherWarmthMult" in it:
            out.append({"key": "weatherCold", "value": pct(it["weatherWarmthMult"])})
        dk = it.get("drainKmMult") or {}
        if "satiety" in dk:
            out.append({"key": "satietyDrain", "value": pct(dk["satiety"])})
        if "water" in dk:
            out.append({"key": "waterDrain", "value": pct(dk["water"])})
        if "waterDrainMult" in it:
            out.append({"key": "waterDrain", "value": pct(it["waterDrainMult"])})
        if "idleWarmthMult" in it:
            out.append({"key": "idleWarmth", "value": pct(it["idleWarmthMult"])})
        if "delayMult" in it:
            out.append({"key": "delay", "value": pct(it["delayMult"])})
        if "detourMult" in it:
            out.append({"key": "detour", "value": pct(it["detourMult"])})
        if "riskReduce" in it:
            out.append({"key": "risk", "value": py_round(it["riskReduce"] * 100.0)})
        if "rescueTo" in it:
            rs = it.get("rescueStats")
            key = "rescue" + "".join(x.capitalize() for x in rs) if rs else "rescue"
            out.append({"key": key, "value": int(it["rescueTo"])})
        if it.get("stove"):
            out.append({"key": "stove", "value": 0})
        if "refill" in it:
            tgt = self.items.get(it["refill"], {})
            out.append({"key": "refill", "value": int(it["amount"])})
            out.append({"key": "refillMax", "value": int(tgt.get("maxUses", tgt.get("uses", 0)))})
        if "uses" in it:
            out.append({"key": "uses", "value": int(it["uses"])})
        if int(it.get("portions", 1)) > 1:
            out.append({"key": "portions", "value": int(it["portions"])})
        ab = it.get("ability")
        if ab:
            out.append({"key": "ability_" + ab["kind"], "value": int(ab["cooldownDays"])})
            eff = ab.get("effect") or {}
            for stat in STATS:
                if eff.get(stat):
                    out.append({"key": "action" + stat.capitalize(), "value": int(eff[stat])})
            if eff.get("warmthToMax"):
                out.append({"key": "actionWarmthMax", "value": 0})
            for gi, gn in (eff.get("give") or {}).items():
                out.append({"key": "actionGive_" + gi, "value": int(gn)})
        if it.get("hint"):
            out.append({"key": "hint", "value": int(it["hint"]["cooldownDays"])})
        camp = it.get("camp")
        if camp:
            for stat in STATS:
                if camp.get(stat):
                    out.append({"key": "camp" + stat.capitalize() + ("AtWater" if camp.get("waterPlace") else ""),
                                "value": int(camp[stat])})
        cond = it.get("cond")
        if cond:
            suf = "At" + "".join(x.capitalize() for x in cond["any"])
            cdk = cond.get("drainKmMult") or {}
            if "waterDrainMult" in cond:
                out.append({"key": "waterDrain" + suf, "value": pct(cond["waterDrainMult"])})
            if "satiety" in cdk:
                out.append({"key": "satietyDrain" + suf, "value": pct(cdk["satiety"])})
            if "water" in cdk:
                out.append({"key": "waterDrain" + suf, "value": pct(cdk["water"])})
            if "riskReduce" in cond:
                out.append({"key": "risk" + suf, "value": py_round(cond["riskReduce"] * 100.0)})
            if cond.get("noCoinLoss"):
                out.append({"key": "noCoinLoss" + suf, "value": 0})
        fb = it.get("foodBoost")
        if fb:
            for stat in STATS:
                if stat in fb:
                    out.append({"key": "boost" + fb["tag"].capitalize() + stat.capitalize(),
                                "value": py_round((fb[stat] - 1.0) * 100.0)})
        if it.get("upkeep"):
            out.append({"key": "upkeep", "value": 1})
        if "expiresDays" in it:
            out.append({"key": "expires", "value": int(it["expiresDays"])})
        if "sellPrice" in it:
            out.append({"key": "sell", "value": int(it["sellPrice"])})
        return out

    def is_gift(self, item: str) -> bool:
        """Дар духа (items.<id>.gift): действует как снаряжение, но ячейку снаряжения не занимает и
        переполнения не вызывает; выбросить нельзя (V5-43)."""
        return bool(self.items.get(item, {}).get("gift"))

    def has_tag(self, item: str, tag: str) -> bool:
        return tag in (self.items.get(item, {}).get("tags") or [])

    def gifts(self) -> dict:
        return self.b.get("gifts", {})

    # ------------------------------------------------ главы, места, погода
    def chapter_at(self, pos: float) -> int:
        for c in self.chapters:
            if pos < self.pos_of[c["to"]]:
                return c["id"]
        return self.chapters[-1]["id"]

    def chapter_start_pos(self, ch: int) -> float:
        c = next(x for x in self.chapters if x["id"] == ch)
        return self.pos_of[c["from"]]

    def last_place_before(self, pos: float) -> dict:
        best = self.places[0]
        for p in self.places:
            if self.pos_of[p["id"]] <= pos + 1e-6:
                best = p
        return best

    def weather_at(self, seed: int, pos: float) -> str:
        seg = int(pos // (self.b["weather"]["segmentKm"] * 1000))
        weights = self.b["weather"]["byChapter"][str(self.chapter_at(pos))]
        names = list(weights)  # порядок ключей из JSON — одинаков в Dart (LinkedHashMap)
        total = sum(weights.values())
        r = hash32(seed, seg) % total
        acc = 0
        for n in names:
            acc += weights[n]
            if r < acc:
                return n
        return names[-1]


# ---------------------------------------------------------------- State
def _loadout_into(world: World, s: dict, gear: list[str], pack: dict[str, int]):
    s["gear"] = list(gear)
    s["gearUses"] = {g: int(world.items[g]["uses"]) for g in gear if "uses" in world.items[g]}
    s["inv"] = {k: int(n) for k, n in pack.items() if n > 0}
    s["heated"] = False
    s["heatedDay"] = 0
    s["overflow"] = []
    s["aidLock"] = False
    s["portionsLeft"] = {}
    s["undo"] = None
    s["fed"] = {}
    s["expires"] = {}


def new_state(world: World, seed: int, now_ms: int, today: str, today_steps: int = 0) -> dict:
    """Новый путь. Снаряжение и рюкзак — набор по умолчанию (balance.loadout.default);
    экран «Собери рюкзак» заменяет его вызовом Engine.start_loadout()."""
    b = world.b
    s = {
        "v": STATE_VERSION,
        "seed": seed & 0xFFFFFFFF,
        "rng": seed & 0xFFFFFFFF,
        "startedAt": now_ms,
        "startDay": today,
        "pos": 0.0,
        "maxPos": 0.0,
        "buffer": 0.0,
        "detour": None,
        "stats": {k: float(v) for k, v in b["stats"]["start"].items()},
        "coins": b["economy"]["startCoins"],
        "inv": {},
        "gear": [],
        "gearUses": {},
        "heated": False,
        "heatedDay": 0,
        "overflow": [],
        "aidLock": False,
        "loadoutDone": False,
        "portionsLeft": {},
        "abilityReady": {},
        "undo": None,
        "fed": {},
        "expires": {},
        "dayMark": (now_ms + int(b["gameDay"]["utcOffsetHours"] * MS_HOUR)) // MS_DAY,
        "stop": None,
        "delayUntil": 0,
        "flags": [],
        "seen": [],
        "recentRandom": [],
        "quests": {},
        "nextRandomAt": b["randomEvents"]["firstAfterKm"] * 1000.0,
        "nextNightAt": first_night_after(b, -1.0),
        "bonusKm": 0.0,
        "lastTick": now_ms,
        "counted": {today: today_steps},
        "daySteps": {today: 0},
        "claimed": {},
        "deaths": 0,
        "journal": [],
        "finished": False,
    }
    d = b["loadout"]["default"]
    _loadout_into(world, s, d["gear"], d["pack"])
    return s


def migrate_state(world: World, s: dict) -> dict:
    """Сохранение v1 (до v5.3) → v2. Снаряжение переезжает из inv в gear (не больше gearSlots, по порядку ключей inv);
    лишние экземпляры и то, что не влезло, превращаются в монеты как дубликаты. Еда и инструменты остаются в inv."""
    if s.get("v", 1) >= STATE_VERSION:
        return s
    slots = world.b["economy"]["gearSlots"]
    gear, uses = [], {}
    for k in list(s.get("inv", {})):
        if world.item_type(k) == "gear":
            n = s["inv"].pop(k)
            if len(gear) < slots:
                gear.append(k)
                if "uses" in world.items[k]:
                    uses[k] = int(world.items[k]["uses"])
                n -= 1
            if n > 0:
                s["coins"] += n * math.floor(world.items[k].get("price", 0) * world.b["economy"]["duplicateGearShare"])
    s.update({"v": STATE_VERSION, "gear": gear, "gearUses": uses, "heated": False, "heatedDay": 0,
              "overflow": [], "aidLock": False, "loadoutDone": True, "portionsLeft": {}, "abilityReady": {}})
    return s


def night_len(b: dict) -> float:
    """Шаг ночёвок, м: movement.dayLengthKm (та же длина «суток пути», что и dayPhase в интерфейсе)."""
    return b["movement"]["dayLengthKm"] * 1000.0


def first_night_after(b: dict, x: float) -> float:
    """Первая точка ночёвки (м) строго дальше x: atPhase·L, затем +L (повторным сложением — бит в бит с Dart)."""
    n = b.get("night")
    if not n:
        return 0.0
    length = night_len(b)
    at = n["atPhase"] * b["movement"]["dayLengthKm"] * 1000.0
    while at <= x + 1e-6:
        at += length
    return at


# Поля v5.3-§13 (дары духов): у старых сохранений v2 их нет — читаются с умолчаниями (Dart: fromJson ?? …)
STATE_DEFAULTS_13 = {"undo": None, "fed": {}, "expires": {}, "dayMark": 0}


class Engine:
    def __init__(self, world: World, state: dict):
        self.w = world
        self.s = state
        self.b = world.b
        self.rng = Rng(state["rng"])
        for k, v in STATE_DEFAULTS_13.items():
            if k not in state:
                state[k] = dict(v) if isinstance(v, dict) else v
        if "nextNightAt" not in state:  # сохранение до V5-45: первая ночёвка — дальше уже пройденного
            state["nextNightAt"] = first_night_after(world.b, state["maxPos"])
        self._harm: dict | None = None

    # ------------------------------------------------ утилиты
    def _save_rng(self):
        self.s["rng"] = self.rng.state

    def _log(self, now: int, kind: str, text: str, **extra):
        # pos — где это случилось, м (в Dart — pyRound(s.pos)); extra может передать свой pos
        self.s["journal"].append({"t": now, "kind": kind, "text": text, "pos": py_round(self.s["pos"]), **extra})
        if len(self.s["journal"]) > 400:
            del self.s["journal"][:-400]

    def game_m_per_step(self) -> float:
        m = self.b["movement"]
        return m["stepLengthM"] * m["gameMultiplier"]

    def consumables_count(self) -> int:
        return sum(n for k, n in self.s["inv"].items() if self.w.item_type(k) in CONSUMABLE)

    def backpack_slots(self) -> int:
        return self.b["economy"]["backpackSlots"]

    def gear_slots(self) -> int:
        return self.b["economy"]["gearSlots"]

    def gear_used(self) -> int:
        """Занятые ячейки снаряжения: дары духов (gift) не считаются (V5-43)."""
        return sum(1 for g in self.s["gear"] if not self.w.is_gift(g))

    def has_item(self, item: str) -> bool:
        """Есть ли предмет: в рюкзаке/инструментах (inv) или в снаряжении (gear)."""
        return self.s["inv"].get(item, 0) > 0 or item in self.s["gear"]

    def in_bonus(self) -> bool:
        st, bb = self.s["stats"], self.b["bonus"]
        return st["satiety"] >= bb["satietyAtLeast"] and st["water"] >= bb["waterAtLeast"]

    def noticed(self) -> bool:
        return self.s["bonusKm"] >= self.b["bonus"]["noticeAfterKm"]

    def _clamp_stats(self):
        mx = self.b["stats"]["max"]
        for k in STATS:
            self.s["stats"][k] = max(0.0, min(float(mx), self.s["stats"][k]))

    def zone_here(self) -> str:
        return self.w.zone_at(self.s["pos"])

    # ------------------------------------------------ перки снаряжения
    def perk_on(self, g: str) -> bool:
        """Перки снаряжения действуют, если у предмета нет upkeep (лапоть) или сегодня он «накормлен»."""
        return "upkeep" not in self.w.items.get(g, {}) or bool(self.s["fed"].get(g, False))

    @staticmethod
    def _cond_on(spec: dict, ctx) -> dict | None:
        c = spec.get("cond")
        if c and ctx and any(x in ctx for x in c["any"]):
            return c
        return None

    def gear_mult(self, key: str, sub: str | None = None, ctx=()) -> float:
        """Произведение множителя key (или key.sub) по снаряжению — в порядке списка gear.
        ctx — активные условия ('midday', 'heat', 'water'): у предмета с cond, чьё any пересекается с ctx,
        множитель cond[key] умножается сразу после базового (§13.3)."""
        m = 1.0
        for g in self.s["gear"]:
            spec = self.w.items.get(g, {})
            if not self.perk_on(g):
                continue
            for src in (spec, self._cond_on(spec, ctx)):
                if src is None:
                    continue
                v = src.get(key)
                if isinstance(v, dict):
                    v = v.get(sub)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    m = m * v
        return m

    def gear_flag(self, key: str, ctx=()) -> bool:
        """Логический перк (noCoinLoss) у снаряжения — базовый или условный."""
        for g in self.s["gear"]:
            spec = self.w.items.get(g, {})
            if not self.perk_on(g):
                continue
            c = self._cond_on(spec, ctx)
            if spec.get(key) is True or (c is not None and c.get(key) is True):
                return True
        return False

    def risk_factor(self, ctx=()) -> float:
        """Π (1 − riskReduce) по снаряжению (базовый, затем условный у того же предмета); 1.0 — оберега нет."""
        f = 1.0
        for g in self.s["gear"]:
            spec = self.w.items.get(g, {})
            if not self.perk_on(g):
                continue
            for src in (spec, self._cond_on(spec, ctx)):
                if src is None:
                    continue
                r = src.get("riskReduce")
                if r:
                    f = f * (1.0 - r)
        return f

    def event_ctx(self, ev: dict | None) -> list[str]:
        """Условия события для условных перков: ['water'], если art события — вода (gifts.waterArts)."""
        if ev and ev.get("art") in self.w.gifts().get("waterArts", []):
            return ["water"]
        return []

    def is_midday(self, now: int) -> bool:
        """Полдень по времени маршрута (МСК): from ≤ час < to, gifts.middayHours."""
        mh = self.w.gifts().get("middayHours")
        if not mh:
            return False
        h = ((now + int(self.b["gameDay"]["utcOffsetHours"] * MS_HOUR)) % MS_DAY) / MS_HOUR
        return mh[0] <= h < mh[1]

    def at_water_place(self) -> bool:
        st = self.s["stop"]
        return bool(st) and st.get("type") in ("place", "chapter_end") and \
            st.get("place") in self.w.gifts().get("waterPlaces", [])

    def gear_uses(self, item: str) -> int:
        return self.s["gearUses"].get(item, 0)

    def _max_uses(self, item: str) -> int:
        it = self.w.items[item]
        return int(it.get("maxUses", it.get("uses", 0)))

    # ------------------------------------------------ игровая дата (для «Нагреть»)
    def game_day(self, now: int) -> int:
        """Номер игровой даты: сутки по времени маршрута (UTC+3, весь путь Москва → Териберка — в МСК)."""
        return (now + int(self.b["gameDay"]["utcOffsetHours"] * MS_HOUR)) // MS_DAY

    def _expire_heat(self, now: int):
        if self.s["heated"] and self.game_day(now) != self.s["heatedDay"]:
            self.s["heated"] = False
            self.s["heatedDay"] = 0

    def is_heated(self, now: int) -> bool:
        return self.s["heated"] and self.game_day(now) == self.s["heatedDay"]

    # ------------------------------------------------ шаги и монеты
    def sync_steps(self, day_steps: dict[str, int], now: int) -> int:
        """Принимает {день: шагов за день}. Возвращает прирост реальных шагов."""
        added = 0
        for day in sorted(day_steps):
            if day < self.s["startDay"]:
                continue
            steps = int(day_steps[day])
            prev = self.s["counted"].get(day, 0)
            if steps <= prev:
                continue
            self.s["counted"][day] = steps
            delta = steps - prev
            added += delta
            self.s["daySteps"][day] = self.s["daySteps"].get(day, 0) + delta
            self._award_tiers(day, now)
        if added:
            self.s["buffer"] += added * self.game_m_per_step()
        return added

    def _award_tiers(self, day: str, now: int):
        got = self.s["claimed"].setdefault(day, {"tiers": [], "login": False})
        for i, t in enumerate(self.b["dailyGoals"]["tiers"]):
            if self.s["daySteps"].get(day, 0) >= t["steps"] and i not in got["tiers"]:
                got["tiers"].append(i)
                self.s["coins"] += t["coins"]
                self._log(now, "goal", f"Цель дня {t['steps']} шагов: +{t['coins']} монет", coins=t["coins"])

    def can_claim_login(self, today: str) -> bool:
        return not self.s["claimed"].get(today, {}).get("login", False)

    def claim_login(self, today: str, now: int) -> int:
        if not self.can_claim_login(today):
            return 0
        self.s["claimed"].setdefault(today, {"tiers": [], "login": False})["login"] = True
        c = self.b["dailyGoals"]["loginCoins"]
        self.s["coins"] += c
        self._log(now, "login", f"Монеты за заход: +{c}", coins=c)
        return c

    # ------------------------------------------------ стартовый набор
    def start_loadout(self, gear: list[str], pack: dict[str, int], now: int) -> str | None:
        """Экран «Собери рюкзак». None — принято; иначе код ошибки (набор не меняется)."""
        if self.s["loadoutDone"]:
            return "already_done"
        if self.s["maxPos"] > 0:
            return "already_walking"
        err = self.w.loadout_error(gear, pack)
        if err:
            return err
        _loadout_into(self.w, self.s, gear, pack)
        self.s["loadoutDone"] = True
        self._log(now, "loadout", "Сергей собрал рюкзак", gear=list(gear), pack=dict(pack))
        self._save_rng()
        return None

    # ------------------------------------------------ время
    def apply_time(self, now: int):
        hours = max(0.0, (now - self.s["lastTick"]) / MS_HOUR)
        self.s["lastTick"] = now
        self._expire_heat(now)
        self._day_roll(now)
        if hours <= 0:
            return
        floor = self.b["idleFloor"]
        for k in STATS:
            cur = self.s["stats"][k]
            rate = self.b["drainPerHour"][k]
            if k == "warmth":
                idle = max(float(self.w.gifts().get("idleWarmthMin", 0.0)), self.gear_mult("idleWarmthMult"))
                rate = rate * self.gear_mult("warmthDrainMult") * idle
            nxt = cur - rate * hours
            self.s["stats"][k] = max(nxt, min(cur, floor))
        self._auto_consume(now)

    # ------------------------------------------------ еда из рюкзака
    def stat_gain(self, item: str, stat: str) -> int:
        """Прибавка показателя за порцию с учётом foodBoost снаряжения (речная лента: рыба ×1.5, pyRound)."""
        v = self.w.items[item].get(stat, 0)
        if not v:
            return v
        for g in self.s["gear"]:
            fb = self.w.items.get(g, {}).get("foodBoost")
            if fb and stat in fb and self.perk_on(g) and self.w.has_tag(item, fb["tag"]):
                v = py_round(v * fb[stat])
        return v

    def _item_gain(self, item: str, stat: str) -> float:
        g = float(self.stat_gain(item, stat))
        if stat == "warmth" and self.s["heated"]:
            g = g + self.w.items[item].get("heat", 0)
        return g

    def _auto_consume(self, now: int):
        thr = self.b["stats"]["autoConsumeBelow"]
        for stat in STATS:
            for _ in range(4):
                if self.s["stats"][stat] >= thr:
                    break
                cands = [k for k, n in self.s["inv"].items() if n > 0
                         and self.w.item_type(k) in CONSUMABLE and self._item_gain(k, stat) > 0]
                if not cands:
                    break
                gap = self.b["stats"]["max"] - self.s["stats"][stat]
                fitting = [k for k in cands if self._item_gain(k, stat) <= gap]
                pool = fitting or cands
                pick = (max if fitting else min)(sorted(pool), key=lambda k: self._item_gain(k, stat))
                self._use_one(pick, now)
                self._log(now, "eat", f"Сергей использовал: {pick}", item=pick)

    def _take_inv(self, item: str, n: int):
        """Вынуть n ЦЕЛЫХ единиц (ячеек). Кончились — забываем и остаток порций."""
        left = self.s["inv"].get(item, 0) - n
        if left > 0:
            self.s["inv"][item] = left
        else:
            self.s["inv"].pop(item, None)
            self.s["portionsLeft"].pop(item, None)

    def portions(self, item: str) -> int:
        return max(1, int(self.w.items.get(item, {}).get("portions", 1)))

    def portions_open(self, item: str) -> int:
        """Сколько порций осталось в начатой единице (у предметов без portions — 1)."""
        return self.s["portionsLeft"].get(item, self.portions(item))

    def portions_total(self, item: str) -> int:
        """Всего порций предмета в рюкзаке: «Термос воды ×4»."""
        n = self.s["inv"].get(item, 0)
        if n <= 0:
            return 0
        return (n - 1) * self.portions(item) + self.portions_open(item)

    def _use_one(self, item: str, now: int) -> bool:
        """Съесть/выпить ОДНУ порцию из рюкзака: многоразовый предмет теряет порцию, на 0 — исчезает ячейка."""
        self._spend_portion(item)
        return self._consume(item, now)

    def _spend_portion(self, item: str):
        """Вынуть одну порцию без употребления (общая часть _use_one и платы лаптю)."""
        if self.portions(item) > 1:
            left = self.portions_open(item) - 1
            if left <= 0:
                self._take_inv(item, 1)
                self.s["portionsLeft"].pop(item, None)
            else:
                self.s["portionsLeft"][item] = left
        else:
            self._take_inv(item, 1)

    def _consume(self, item: str, now: int) -> bool:
        """Применить еду/питьё (предмет уже вынут из рюкзака). Возвращает True, если сработал бонус горелки."""
        self._expire_heat(now)
        it = self.w.items[item]
        for k in STATS:
            self.s["stats"][k] += self.stat_gain(item, k)
        hot = False
        if self.s["heated"] and it.get("heat", 0) > 0:
            self.s["stats"]["warmth"] += it["heat"]
            self.s["heated"] = False
            self.s["heatedDay"] = 0
            hot = True
        self._clamp_stats()
        return hot

    def use_item(self, item: str, now: int) -> bool:
        """Кнопка «Использовать» на вкладке «Герой»."""
        if self.s["inv"].get(item, 0) <= 0 or self.w.item_type(item) not in CONSUMABLE:
            return False
        self._use_one(item, now)
        self._save_rng()
        return True

    # ------------------------------------------------ горелка: «Нагреть»
    def _stove(self) -> str | None:
        for g in self.s["gear"]:
            if self.w.items.get(g, {}).get("stove"):
                return g
        return None

    def _has_heatable(self) -> bool:
        if any(n > 0 and self.w.heatable(k) for k, n in self.s["inv"].items()):
            return True
        return any(o["kind"] == "backpack" and self.w.heatable(o["item"]) for o in self.s["overflow"])

    def heat_status(self, now: int) -> str:
        """ready | on | no_stove | no_gas | nothing — для кнопки «Нагреть»."""
        st = self._stove()
        if st is None:
            return "no_stove"
        if self.is_heated(now):
            return "on"
        if self.gear_uses(st) <= 0:
            return "no_gas"
        if not self._has_heatable():
            return "nothing"
        return "ready"

    def heat(self, now: int) -> str:
        """«Нагреть»: heated — потрачен 1 заряд; on — уже горячо, заряд не тратится; иначе код отказа."""
        self._expire_heat(now)
        status = self.heat_status(now)
        if status != "ready":
            return status
        st = self._stove()
        self.s["gearUses"][st] = self.gear_uses(st) - 1
        self.s["heated"] = True
        self.s["heatedDay"] = self.game_day(now)
        self._log(now, "heat", "Сергей разжёг горелку", item=st, left=self.s["gearUses"][st])
        self._save_rng()
        return "heated"

    # ------------------------------------------------ дары духов: способности предметов
    def held_items(self) -> list[str]:
        """Всё, что у героя есть: снаряжение по порядку, затем inv (n > 0) по алфавиту."""
        return list(self.s["gear"]) + sorted(k for k, n in self.s["inv"].items() if n > 0)

    def ability_item(self, kind: str) -> str | None:
        """Первый предмет с ability.kind == kind у героя (снаряжение по порядку, затем inv по ключам)."""
        for it in self.held_items():
            ab = self.w.items.get(it, {}).get("ability")
            if ab and ab.get("kind") == kind:
                return it
        return None

    def ability_cooldown_days(self, item: str, now: int) -> int:
        """Сколько игровых дней ждать до готовности (0 — готово). item — ключ abilityReady
        (id предмета; у подсказки духа — 'id:hint', у привала — 'id:camp')."""
        return max(0, self.s["abilityReady"].get(item, 0) - self.game_day(now))

    def _charged(self, item: str) -> bool:
        """Есть ли заряд у предмета с uses (у бесконечного — всегда)."""
        return "uses" not in self.w.items.get(item, {}) or self.gear_uses(item) > 0

    def _spend_charge(self, item: str):
        """−1 заряд; у инструмента (tool) на 0 предмет исчезает (лапка, нитка, кудель, камешек, сноп, крючок)."""
        if "uses" not in self.w.items.get(item, {}):
            return
        left = self.gear_uses(item) - 1
        self.s["gearUses"][item] = left
        if left <= 0 and self.w.item_type(item) == "tool":
            self.s["inv"].pop(item, None)
            self.s["gearUses"].pop(item, None)

    # --- «Спросить клубок» и подсказки духов (hint)
    def _clew_sources(self) -> list[tuple[str, str, dict | None]]:
        """Чем можно подсветить исходы, в порядке траты: (предмет, ключ abilityReady, hint|None).
        1) подсказки духов (hint) — снаряжение по порядку, затем inv по алфавиту; 2) clew с зарядами (нитка);
        3) clew с перезарядкой (клубок)."""
        held = self.held_items()
        hints = [(i, i + ":hint", self.w.items[i]["hint"]) for i in held if self.w.items.get(i, {}).get("hint")]
        clews = [i for i in held if (self.w.items.get(i, {}).get("ability") or {}).get("kind") == "clew"]
        charged = [(i, i, None) for i in clews if "uses" in self.w.items[i]]
        timed = [(i, i, None) for i in clews if "uses" not in self.w.items[i]]
        return hints + charged + timed

    @staticmethod
    def hint_matches(h: dict, ev: dict) -> bool:
        return (not h.get("art") or ev.get("art") in h["art"]) and (not h.get("zone") or ev.get("zone") in h["zone"])

    def _source_ready(self, src, now: int) -> bool:
        item, key, _ = src
        return self.ability_cooldown_days(key, now) == 0 and self._charged(item)

    def _clew_pick(self, now: int):
        ev = self.current_event()
        if ev is None:
            return None
        for src in self._clew_sources():
            if self._source_ready(src, now) and (src[2] is None or self.hint_matches(src[2], ev)):
                return src
        return None

    def clew_status(self, now: int) -> str:
        """ready | cooldown | not_here | no_item | no_event — кнопка «Спросить клубок» (или сучок, ракушку…).
        not_here — готова только подсказка духа, а событие не его (не лес у лешего и т. п.)."""
        srcs = self._clew_sources()
        if not srcs:
            return "no_item"
        any_ready = any(self._source_ready(x, now) for x in srcs)
        if self.current_event() is None:
            return "no_event" if any_ready else "cooldown"
        if self._clew_pick(now) is not None:
            return "ready"
        return "not_here" if any_ready else "cooldown"

    def clew_item(self, now: int) -> str | None:
        """Какой предмет подскажет сейчас (для подписи кнопки: «Спросить клубок» / «Спросить сучок»)."""
        src = self._clew_pick(now)
        return src[0] if src else None

    def clew_cooldown_days(self, now: int) -> int:
        """Сколько дней до ближайшей готовой подсказки (0 — есть готовая)."""
        srcs = self._clew_sources()
        if not srcs:
            return 0
        return min(self.ability_cooldown_days(k, now) if self._charged(i) else 999 for i, k, _ in srcs)

    def outcome_tone(self, o: dict) -> str:
        """good | bad | mixed | neutral | death — по эффектам одного исхода."""
        eff = o.get("effects", {})
        if eff.get("death"):
            return "death"
        good = bad = False
        for k in ("coins", "satiety", "water", "warmth"):
            v = eff.get(k)
            if isinstance(v, str):
                if v.startswith("-"):
                    bad = True
                else:
                    good = True
        if eff.get("give") or eff.get("shortcut"):
            good = True
        if eff.get("remove") or eff.get("delay") or eff.get("detour") or eff.get("bonus_reset"):
            bad = True
        return "mixed" if good and bad else "good" if good else "bad" if bad else "neutral"

    def choice_tone(self, choice: dict) -> str:
        """Тон варианта для клубка: death | reward | penalty | risk | mixed | neutral."""
        tones = {self.outcome_tone(o) for o in choice.get("outcomes", [])}
        if "death" in tones:
            return "death"
        if "good" in tones and "bad" in tones:
            return "risk"
        if "mixed" in tones:
            return "mixed"
        if "good" in tones:
            return "reward"
        if "bad" in tones:
            return "penalty"
        return "neutral"

    def ask_clew(self, now: int) -> dict | None:
        """«Спросить клубок»: {choice_id: тон} для текущего события; ставит перезарядку cooldownDays игровых дней
        (у подсказки духа — hint.cooldownDays по ключу 'id:hint'), у нитки тратит заряд.
        None — нельзя (см. clew_status). RNG не трогает."""
        if self.clew_status(now) != "ready":
            return None
        it, key, h = self._clew_pick(now)
        ev = self.current_event()
        out = {c["id"]: self.choice_tone(c) for c in ev["choices"]}
        cd = int(h["cooldownDays"]) if h is not None else int(self.w.items[it]["ability"]["cooldownDays"])
        self.s["abilityReady"][key] = self.game_day(now) + cd
        if h is None:
            self._spend_charge(it)
        self._log(now, "ability", "Клубок подсказал дорогу", item=it, event=ev["id"])
        self._save_rng()
        return out

    # --- дары-действия: guide (сучок, лапка), mirage (бусина, кудель), action (веник, камешек, ключ, сноп, крючок…)
    def gift_status(self, item: str, now: int) -> str:
        """ready | no_item | bad_kind | no_charges | cooldown | nothing | not_here — кнопка дара (§13.4)."""
        if not self.has_item(item):
            return "no_item"
        spec = self.w.items.get(item, {})
        ab = spec.get("ability") or {}
        kind = ab.get("kind")
        if kind not in ("guide", "mirage", "action"):
            return "bad_kind"
        if not self._charged(item):
            return "no_charges"
        if self.ability_cooldown_days(item, now) > 0:
            return "cooldown"
        u = self.s["undo"]
        if kind == "guide":
            return "ready" if u and ("delay" in u or "detour" in u) else "nothing"
        if kind == "mirage":
            return "ready" if u else "nothing"
        at = ab.get("at", "any")
        st = self.s["stop"]
        if at == "place" and not (st and st.get("type") in ("place", "chapter_end")):
            return "not_here"
        if ab.get("zones") and self.zone_here() not in ab["zones"]:
            return "not_here"
        if ab.get("water") and not self.at_water_place():
            return "not_here"
        eff = ab.get("effect") or {}
        mx = self.b["stats"]["max"]
        if not eff.get("give") and all(self.s["stats"][k] >= mx for k in STATS
                                       if eff.get(k) or (k == "warmth" and eff.get("warmthToMax"))):
            return "nothing"
        return "ready"

    def use_gift(self, item: str, now: int) -> str:
        """Нажать кнопку дара. 'ok' — сработал (заряд/перезарядка потрачены); иначе код gift_status."""
        st = self.gift_status(item, now)
        if st != "ready":
            return st
        ab = self.w.items[item]["ability"]
        kind = ab["kind"]
        ev_id = ""
        if kind in ("guide", "mirage"):
            ev_id = self.s["undo"].get("event", "")
            self._undo(kind)
        else:
            eff = ab.get("effect") or {}
            for k in STATS:
                if eff.get(k):
                    self.s["stats"][k] += eff[k]
            if eff.get("warmthToMax"):
                self.s["stats"]["warmth"] = float(self.b["stats"]["max"])
            self._clamp_stats()
            if eff.get("give"):
                self.give_items(dict(eff["give"]), item)
        cd = int(ab.get("cooldownDays", 0))
        if cd:
            self.s["abilityReady"][item] = self.game_day(now) + cd
        self._spend_charge(item)
        self._log(now, "gift", "Дар духа помог Сергею", item=item, ability=kind, event=ev_id)
        self._save_rng()
        return "ok"

    def _undo(self, kind: str):
        """Отмена вреда последнего исхода (state.undo): guide — только задержка и крюк; mirage — всё плохое."""
        u = self.s["undo"]
        if "delay" in u:
            self.s["delayUntil"] = u.pop("delay")
        if "detour" in u:
            u.pop("detour")
            self.s["detour"] = u.pop("prevDetour", None)
        if kind == "mirage":
            if u.get("coins"):
                self.s["coins"] += u["coins"]
            for k, lost in (u.get("stats") or {}).items():
                self.s["stats"][k] += lost
            self._clamp_stats()
            for it, r in (u.get("removed") or {}).items():
                if self.w.item_type(it) in CONSUMABLE:
                    self.give_items({it: r["n"]}, "mirage")
                    if r.get("portions") is not None and self.s["inv"].get(it, 0) > 0 and it not in self.s["portionsLeft"]:
                        self.s["portionsLeft"][it] = r["portions"]
                else:
                    self.s["inv"][it] = self.s["inv"].get(it, 0) + r["n"]
                    if r.get("uses") is not None:
                        self.s["gearUses"][it] = r["uses"]
            for r in u.get("removedGear") or []:
                g = r["item"]
                if g in self.s["gear"]:
                    continue
                if self.w.is_gift(g) or self.gear_used() < self.gear_slots():
                    self.s["gear"].append(g)
                    for fld, key in (("uses", "gearUses"), ("expires", "expires"), ("fed", "fed")):
                        if r.get(fld) is not None:
                            self.s[key][g] = r[fld]
                else:
                    self.s["overflow"].append({"kind": "gear", "item": g, "n": 1, "source": "mirage"})
            if "bonusKm" in u:
                self.s["bonusKm"] = u["bonusKm"]
            self.s["undo"] = None
            return
        rest = {k: v for k, v in u.items() if k != "event"}
        if not rest:
            self.s["undo"] = None

    # --- смена игровой даты: лапоть ест, венок вянет
    def _day_roll(self, now: int):
        d = self.game_day(now)
        if self.s["dayMark"] == d:
            return
        self.s["dayMark"] = d
        for g in list(self.s["gear"]):
            exp = self.s["expires"].get(g)
            if exp is not None and d >= exp:
                self.s["gear"].remove(g)
                self._on_gear_removed(g)
                self._log(now, "wilt", "Дар завял", item=g)
        for g in list(self.s["gear"]):
            up = self.w.items.get(g, {}).get("upkeep")
            if not up:
                continue
            food = self._upkeep_food(up)
            if food:
                self._spend_portion(food)
            self.s["fed"][g] = food is not None
            self._log(now, "upkeep", "Домовой в лапте поужинал" if food else "Домовому нечего есть", item=g, food=food)

    def _upkeep_food(self, order: list[str]) -> str | None:
        """Что съест домовой: первый из order, затем прочая еда по алфавиту. Последнюю единицу еды не берёт
        (в рюкзаке < 2 единиц типа food → None, перк сегодня не действует)."""
        inv = self.s["inv"]
        if sum(n for k, n in inv.items() if n > 0 and self.w.item_type(k) == "food") < 2:
            return None
        for it in order:
            if inv.get(it, 0) > 0 and self.w.item_type(it) == "food":
                return it
        for it in sorted(inv):
            if inv[it] > 0 and self.w.item_type(it) == "food":
                return it
        return None

    def _on_gear_added(self, g: str):
        spec = self.w.items.get(g, {})
        if "uses" in spec:
            self.s["gearUses"][g] = int(spec["uses"])
        if "expiresDays" in spec:
            self.s["expires"][g] = self.game_day(self.s["lastTick"]) + int(spec["expiresDays"])
        if spec.get("upkeep"):
            self.s["fed"][g] = True  # плата отдана при получении — в этот день перк уже работает

    def _on_gear_removed(self, g: str):
        self.s["gearUses"].pop(g, None)
        self.s["expires"].pop(g, None)
        self.s["fed"].pop(g, None)

    # --- привал: спальник, уголёк, ракушка (camp)
    def _camp(self, place: dict, now: int):
        got = []
        water = place["id"] in self.w.gifts().get("waterPlaces", [])
        for g in self.s["gear"]:
            c = self.w.items.get(g, {}).get("camp")
            if not c or not self.perk_on(g):
                continue
            if c.get("waterPlace") and not water:
                continue
            cd = int(c.get("cooldownDays", 0))
            key = g + ":camp"
            if cd and self.ability_cooldown_days(key, now) > 0:
                continue
            for k in STATS:
                if c.get(k):
                    self.s["stats"][k] += c[k]
            if cd:
                self.s["abilityReady"][key] = self.game_day(now) + cd
            got.append(g)
        if got:
            self._clamp_stats()
            self._log(now, "camp", "Привал с добрыми вещами", items=got)

    # --- продажа (речная жемчужина)
    def sell_offers(self) -> list[tuple[str, int]]:
        """Что можно продать на этом рынке: предметы inv с sellPrice (цена без наценки рынка)."""
        if not self.market():
            return []
        return [(k, int(self.w.items[k]["sellPrice"])) for k in sorted(self.s["inv"])
                if self.s["inv"][k] > 0 and "sellPrice" in self.w.items.get(k, {})]

    def sell_blocker(self, item: str) -> str | None:
        if not self.market():
            return "no_market"
        if self.s["inv"].get(item, 0) <= 0:
            return "no_item"
        if "sellPrice" not in self.w.items.get(item, {}):
            return "not_sellable"
        return None

    def sell(self, item: str, now: int) -> bool:
        if self.sell_blocker(item) is not None:
            return False
        price = int(self.w.items[item]["sellPrice"])
        self._take_inv(item, 1)
        self.s["coins"] += price
        self._log(now, "sell", item, item=item, price=price)
        self._save_rng()
        return True

    # ------------------------------------------------ аптечка
    def _try_rescue(self, now: int) -> bool:
        """Показатель упал до 0: аптечка с зарядом поднимает все нулевые показатели до rescueTo.
        Не чаще раза между остановками (aidLock снимается при прибытии на остановку)."""
        if self.s["aidLock"]:
            return False
        zero = [k for k in STATS if self.s["stats"][k] <= 0]
        for g in self.s["gear"]:
            to = self.w.items.get(g, {}).get("rescueTo")
            allowed = self.w.items.get(g, {}).get("rescueStats") or STATS
            if to and self.gear_uses(g) > 0 and all(k in allowed for k in zero):
                self.s["gearUses"][g] = self.gear_uses(g) - 1
                saved = zero
                for k in saved:
                    self.s["stats"][k] = float(to)
                self.s["aidLock"] = True
                self._log(now, "first_aid", "Аптечка спасла Сергея", item=g, stats=saved, left=self.s["gearUses"][g])
                return True
        return False

    # ------------------------------------------------ движение
    def _drain_walk(self, km: float, now: int | None = None):
        st = self.s["stats"]
        dk = self.b["drainPerKm"]
        bonus = self.in_bonus()
        mult = self.b["bonus"]["drainMultiplier"] if bonus else 1.0
        pos = self.s["pos"]
        wname = self.w.weather_at(self.s["seed"], pos)
        wx = self.b["weather"]["types"][wname]
        cold = self.b["chapterCold"][str(self.w.chapter_at(pos))]
        ctx = []  # условия для cond-перков (колосок): жара по погоде, полдень по времени маршрута
        if wname == "heat":
            ctx.append("heat")
        if now is not None and self.is_midday(now):
            ctx.append("midday")
        sat_m = self.gear_mult("drainKmMult", "satiety", ctx=ctx)
        wat_m = self.gear_mult("drainKmMult", "water", ctx=ctx) * self.gear_mult("waterDrainMult", ctx=ctx)
        warm_m = self.gear_mult("warmthDrainMult", ctx=ctx)
        rain_m = self.gear_mult("weatherWarmthMult", ctx=ctx)
        weather_warm = wx.get("warmth", 1.0)
        if weather_warm > 1.0 and rain_m != 1.0:
            weather_warm = 1.0 + (weather_warm - 1.0) * rain_m
        st["satiety"] -= dk["satiety"] * km * mult * sat_m
        st["water"] -= dk["water"] * km * wx.get("water", 1.0) * mult * wat_m
        st["warmth"] -= dk["warmth"] * km * cold * weather_warm * warm_m * mult
        if bonus:
            self.s["bonusKm"] += km
        else:
            self.s["bonusKm"] = 0.0

    def _next_stop(self) -> tuple[float, str, object]:
        """Ближайшая остановка впереди: (позиция, тип, данные)."""
        pos = self.s["pos"]
        best = (self.w.length, "finish", None)
        for p_pos, p in self.w.stops_places:
            if p_pos > pos + 1e-6:
                if p_pos < best[0]:
                    best = (p_pos, "place", p)
                break
        for a_pos, e in self.w.anchored:
            if a_pos > pos + 1e-6 and e["id"] not in self.s["seen"]:
                if a_pos < best[0]:
                    best = (a_pos, "event", {"event": e["id"]})
                break
        for qid, q in self.s["quests"].items():
            quest = self.w.quests[qid]
            if q["step"] < len(quest["steps"]):
                q_pos = q["startPos"] + quest["steps"][q["step"]]["at_km"] * 1000.0
                if q_pos <= pos + 1e-6:
                    q_pos = pos + 1.0
                if q_pos < best[0]:
                    best = (q_pos, "quest", {"quest": qid})
        if self.s["nextRandomAt"] > pos + 1e-6 and self.s["nextRandomAt"] < best[0] and self.s["pos"] >= self.s["maxPos"] - 1e-6:
            best = (self.s["nextRandomAt"], "random", None)
        nn = self.s["nextNightAt"]
        if self.b.get("night") and nn > pos + 1e-6 and nn < best[0] and self.s["pos"] >= self.s["maxPos"] - 1e-6:
            best = (nn, "night", None)
        return best

    def advance(self, now: int) -> list[dict]:
        """Двигает героя на накопленный буфер. Возвращает события для интерфейса.
        Пока есть overflow (ожидающее решение), герой стоит."""
        out: list[dict] = []
        self.s["undo"] = None  # кнопки «Сучок»/«Бусина» — только на экране исхода, до «Идти дальше»
        self.apply_time(now)
        guard = 0
        while self.s["buffer"] > 0.5 and not self.s["stop"] and not self.s["overflow"] and not self.s["finished"]:
            guard += 1
            if guard > 10000:
                break
            if self.s["delayUntil"] > now:
                break
            if self.s["detour"]:
                d = self.s["detour"]
                step = min(self.s["buffer"], d["remaining"])
                if not self._walk(step, now, on_route=False):
                    out.append({"type": "death"})
                    break
                d["remaining"] -= step
                self.s["buffer"] -= step
                if d["remaining"] <= 0.5:
                    end = d.get("end")
                    self.s["detour"] = None
                    self._log(now, "detour", "Сергей вернулся на основной путь")
                    if end and end in self.w.events_by_id:
                        self.s["stop"] = {"type": "event", "event": end}
                        self.s["aidLock"] = False
                        out.append({"type": "stop", "stop": self.s["stop"]})
                continue
            target, kind, data = self._next_stop()
            step = min(self.s["buffer"], target - self.s["pos"])
            if step > 0:
                if not self._walk(step, now, on_route=True):
                    out.append({"type": "death"})
                    break
                self.s["buffer"] -= step
            if self.s["pos"] >= target - 0.5:
                self.s["pos"] = max(self.s["pos"], target)
                self.s["maxPos"] = max(self.s["maxPos"], self.s["pos"])
                self._arrive(kind, data, now)
                if self.s["stop"]:
                    out.append({"type": "stop", "stop": self.s["stop"]})
        self._save_rng()
        return out

    def _walk(self, dist: float, now: int, on_route: bool) -> bool:
        """Идёт кусками по 250 м. Возвращает False, если герой погиб."""
        left = dist
        while left > 1e-6:
            chunk = min(250.0, left)
            self._drain_walk(chunk / 1000.0, now)
            self._auto_consume(now)
            self._clamp_stats()
            if on_route:
                self.s["pos"] += chunk
                self.s["maxPos"] = max(self.s["maxPos"], self.s["pos"])
            left -= chunk
            if min(self.s["stats"].values()) <= 0:
                if self._try_rescue(now):
                    continue
                self._die(now, "stats")
                return False
        return True

    def _arrive(self, kind: str, data, now: int):
        self.s["aidLock"] = False  # новая остановка — аптечка снова может сработать
        if kind == "finish":
            self.s["finished"] = True
            self.s["stop"] = {"type": "finish"}
            self._log(now, "finish", "Сергей дошёл до Териберки")
            return
        if kind == "place":
            p = data
            tb = self.b["town"]
            self.s["stats"]["warmth"] += tb["warmthRestore"]
            self.s["stats"]["water"] += tb["waterRefill"]
            self._clamp_stats()
            self._log(now, "place", p["name"], place=p["id"])
            self._camp(p, now)
            nb = self.b.get("night")
            if nb and 0 <= self.s["nextNightAt"] - self.s["pos"] <= nb["skipNearPlaceKm"] * 1000.0:
                # ночёвка рядом с местом — ночуют в месте (это и есть привал), отдельной остановки нет
                self.s["nextNightAt"] = first_night_after(self.b, self.s["pos"] + nb["skipNearPlaceKm"] * 1000.0)
            if p["kind"] == "finish":
                self.s["finished"] = True
                self.s["stop"] = {"type": "finish", "place": p["id"]}
            elif p["id"] in self.w.chapter_end and f"chapter_end:{p['id']}" not in self.s["seen"]:
                # финал главы показывается один раз — после смерти с откатом город будет обычным привалом
                self.s["seen"].append(f"chapter_end:{p['id']}")
                self.s["stop"] = {"type": "chapter_end", "place": p["id"], "chapter": self.w.chapter_end[p["id"]]["id"]}
            else:
                self.s["stop"] = {"type": "place", "place": p["id"]}
            return
        if kind == "event":
            self.s["stop"] = {"type": "event", "event": data["event"]}
            return
        if kind == "quest":
            qid = data["quest"]
            q = self.s["quests"][qid]
            self.s["stop"] = {"type": "event", "quest": qid, "step": q["step"], "event": self._quest_event(qid)["id"]}
            return
        if kind == "night":
            self._night(now)
            return
        if kind == "random":
            e = self._pick_random(now)
            sp = self.b["randomEvents"]["spacingKm"]
            gap = (sp[0] + (sp[1] - sp[0]) * self.rng.next_float()) * 1000.0
            if self.in_bonus():
                gap /= self.b["bonus"]["eventMultiplier"]
            nxt = self.s["pos"] + gap
            # не ставим случайное вплотную к авторскому
            min_gap = self.b["randomEvents"]["minGapToAnchoredKm"] * 1000.0
            for a_pos, ev in self.w.anchored:
                if a_pos > self.s["pos"] and ev["id"] not in self.s["seen"] and abs(a_pos - nxt) < min_gap:
                    nxt = a_pos + min_gap
            self.s["nextRandomAt"] = nxt
            if e:
                self.s["stop"] = {"type": "event", "event": e["id"], "random": True}

    def _night(self, now: int):
        """Ночёвка в пути (V5-45): +тепло, утренний бонус по весам (тратит RNG), camp-перки снаряжения.
        Остановка как привал: «Дальше» — и герой идёт теми же шагами, ждать следующего дня не нужно."""
        nb = self.b["night"]
        morning = nb.get("morning") or []
        mo = morning[self.rng.pick_weighted([int(m["weight"]) for m in morning])] if morning else {}
        gain = {"warmth": int(nb.get("warmth", 0))}
        for k in STATS:
            if mo.get(k):
                gain[k] = gain.get(k, 0) + int(mo[k])
        for k, v in gain.items():
            self.s["stats"][k] += v
        self._clamp_stats()
        mid = mo.get("id", "")
        self._log(now, "night", "Сергей заночевал в пути", morning=mid, gain=dict(gain))
        self._camp({"id": ""}, now)
        self.s["stop"] = {"type": "night", "morning": mid, "gain": gain}
        self.s["nextNightAt"] = first_night_after(self.b, self.s["pos"])

    def _pick_random(self, now: int):
        ch = f"ch{self.w.chapter_at(self.s['pos'])}"
        recent = self.s["recentRandom"]
        zone = self.w.zone_at(self.s["pos"])
        # недавние — отдельно по зоне: последние keep_z событий этой зоны, keep_z = min(12, пул_зоны // 2)
        keep_z = max(1, min(12, self.w.zone_pool_size(zone) // 2))
        recent_z = [r for r in recent if self.w.event_zone(r) == zone][-keep_z:]
        recent_all = recent[-max(1, min(12, len(self.w.randoms) // 2)):]
        in_ch = [e for e in self.w.randoms if ch in e.get("tags", []) or "any" in e.get("tags", [])]
        pool = [e for e in in_ch if e.get("zone") == zone and e["id"] not in recent_z]
        base = [e for e in in_ch if e["id"] not in recent_all]
        if not pool:
            pool = base  # запасной выбор: из всех зон (пул зоны пуст или весь недавно был)
            if pool:
                self._log(now, "zone_fallback", f"Нет случайных событий зоны {zone}", zone=zone)
        if not pool:
            return None
        if self.noticed() and self.rng.next_float() < self.b["bonus"]["noticeRiskChance"]:
            risky = [e for e in pool if "risk" in e.get("tags", [])]
            if risky:
                pool = risky
        e = pool[self.rng.next_u32() % len(pool)]
        self.s["recentRandom"].append(e["id"])
        self.s["recentRandom"] = self.s["recentRandom"][-self.b["randomEvents"]["recentKeep"]:]
        return e

    def _quest_event(self, qid: str) -> dict:
        q = self.s["quests"][qid]
        step = self.w.quests[qid]["steps"][q["step"]]
        if "event" in step:
            return step["event"]
        for br in step["branches"]:
            if all(_cond(q["vars"].get(var, 0), c) for var, c in br["if"].items()):
                return br["event"]
        return step["branches"][-1]["event"]

    # ------------------------------------------------ события
    def current_event(self) -> dict | None:
        st = self.s["stop"]
        if not st or st.get("type") != "event":
            return None
        if "quest" in st:
            if st["quest"] not in self.s["quests"]:
                return None
            return self._quest_event(st["quest"])
        return self.w.events_by_id.get(st["event"])

    def choice_available(self, choice: dict) -> bool:
        req = choice.get("requires") or {}
        if "item" in req and not self.has_item(req["item"]):
            return False
        if "coins" in req and self.s["coins"] < self.b["levels"]["coins"][req["coins"]]:
            return False
        if "flag" in req and req["flag"] not in self.s["flags"]:
            return False
        return True

    def choice_risk(self, choice: dict) -> str:
        """Статический риск или «fatal», если исход может обнулить показатель прямо сейчас."""
        risk = choice.get("risk", "none")
        for o in choice.get("outcomes", []):
            eff = o.get("effects", {})
            for k in STATS:
                v = eff.get(k)
                if isinstance(v, str) and v.startswith("-"):
                    if self.s["stats"][k] - self.b["levels"]["stat"][v[1:]] <= 0:
                        return "fatal"
        return risk

    def _is_bad_outcome(self, o: dict) -> bool:
        eff = o.get("effects", {})
        if eff.get("death"):
            return True
        bad = "-" + self.b["riskReduce"]["badLevel"]
        return any(eff.get(k) == bad for k in ("satiety", "water", "warmth", "coins"))

    def outcome_weights(self, choice: dict, ctx=()) -> list[int]:
        """Веса исходов с учётом оберега (riskReduce). Без оберега, у безопасного варианта (risk none)
        или если плохие исходы — все/ни одного, веса не меняются."""
        outs = choice["outcomes"]
        ws = [o["weight"] for o in outs]
        f = self.risk_factor(ctx)
        if f == 1.0 or choice.get("risk", "none") == "none":
            return ws
        bad = [self._is_bad_outcome(o) for o in outs]
        if not any(bad) or all(bad):
            return ws
        scale = self.b["riskReduce"]["weightScale"]
        return [max(1, py_round(w * scale * f)) if b else w * scale for w, b in zip(ws, bad)]

    def choose(self, choice_id: str, now: int) -> dict:
        ev = self.current_event()
        st = self.s["stop"]
        if ev is None:
            return {"ok": False}
        choice = next((c for c in ev["choices"] if c["id"] == choice_id), None)
        if choice is None or not self.choice_available(choice):
            return {"ok": False}
        outs = choice["outcomes"]
        ctx = self.event_ctx(ev)
        oi = self.rng.pick_weighted(self.outcome_weights(choice, ctx))
        o = outs[oi]
        pos0 = py_round(self.s["pos"])
        qid0 = st.get("quest")
        step0 = self.s["quests"][qid0]["step"] if qid0 in self.s["quests"] else None
        self.s["undo"] = None
        died = self._apply_effects(o.get("effects", {}), now, st, source=ev["id"], ctx=ctx)
        if not died and self._harm:
            self.s["undo"] = dict(self._harm, event=ev["id"])
        if ev.get("once", True) and not st.get("random"):
            if ev["id"] not in self.s["seen"]:
                self.s["seen"].append(ev["id"])
        if "quest" in st:
            qid = st["quest"]
            if qid in self.s["quests"]:
                self.s["quests"][qid]["step"] += 1
                if self.s["quests"][qid]["step"] >= len(self.w.quests[qid]["steps"]):
                    del self.s["quests"][qid]
                    self._log(now, "quest", f"Квест завершён: {self.w.quests[qid]['title']}")
        qx = {"quest": qid0} if qid0 is not None else {}
        if step0 is not None:
            qx["step"] = step0
        self._log(now, "event", ev["title"], event=ev["id"], choice=choice_id, outcome=o.get("text", ""),
                  cid=choice_id, oi=oi, pos=pos0, **qx)
        if not died:
            self.s["stop"] = None
        self._save_rng()
        return {"ok": True, "outcome": o, "died": died}

    # ------------------------------------------------ получение предметов
    def give_items(self, give: dict[str, int], source: str):
        """Выдать предметы (эффект give, награда, находка). Не помещается — в очередь overflow, без потерь."""
        for it, n in give.items():
            t = self.w.item_type(it)
            if t in CONSUMABLE:
                room = max(0, self.backpack_slots() - self.consumables_count())
                put = min(n, room)
                if put:
                    self.s["inv"][it] = self.s["inv"].get(it, 0) + put
                if n - put > 0:
                    self.s["overflow"].append({"kind": "backpack", "item": it, "n": n - put, "source": source})
            elif t == "gear":
                for _ in range(n):
                    self._gain_gear(it, source)
            elif t == "refill":
                for _ in range(n):
                    self._gain_refill(it)
            elif n and "uses" in self.w.items.get(it, {}):
                # инструмент с зарядами — одна ячейка-экземпляр; повтор пополняет заряды (до maxUses)
                spec = self.w.items[it]
                if self.s["inv"].get(it, 0) > 0:
                    self.s["gearUses"][it] = min(self._max_uses(it), self.gear_uses(it) + int(spec["uses"]) * n)
                else:
                    self.s["inv"][it] = 1
                    self.s["gearUses"][it] = min(self._max_uses(it), int(spec["uses"]) * n)
            elif n:
                self.s["inv"][it] = self.s["inv"].get(it, 0) + n

    def _gain_gear(self, it: str, source: str):
        pending = any(o["kind"] == "gear" and o["item"] == it for o in self.s["overflow"])
        if it in self.s["gear"] or pending:
            # дубликат: пополняет заряды своего экземпляра, иначе — монеты (половина цены)
            if it in self.s["gear"] and "uses" in self.w.items[it] and self.gear_uses(it) < self._max_uses(it):
                self.s["gearUses"][it] = min(self._max_uses(it), self.gear_uses(it) + int(self.w.items[it]["uses"]))
            else:
                self.s["coins"] += math.floor(self.w.items[it].get("price", 0) * self.b["economy"]["duplicateGearShare"])
            return
        if self.w.is_gift(it) or self.gear_used() < self.gear_slots():
            self.s["gear"].append(it)  # дар духа ячейку не занимает — сразу в снаряжение
            self._on_gear_added(it)
            return
        self.s["overflow"].append({"kind": "gear", "item": it, "n": 1, "source": source})

    def _gain_refill(self, it: str) -> bool:
        """Баллон: +amount зарядов предмету refill (до maxUses). Нет горелки или полна — монеты (цена баллона)."""
        spec = self.w.items[it]
        tgt = spec["refill"]
        if tgt in self.s["gear"] and self.gear_uses(tgt) < self._max_uses(tgt):
            self.s["gearUses"][tgt] = min(self._max_uses(tgt), self.gear_uses(tgt) + int(spec["amount"]))
            return True
        self.s["coins"] += int(spec.get("price", 0))
        return False

    def _remove_items(self, remove: dict[str, int]) -> tuple[dict, list]:
        """Эффект remove. Возвращает, что реально пропало (для «Бусины-морока»): ({id: {n, portions, uses}}, [gear…])."""
        lost, lost_gear = {}, []
        for it, n in remove.items():
            if it in self.s["gear"]:
                lost_gear.append({"item": it, "uses": self.s["gearUses"].get(it), "expires": self.s["expires"].get(it),
                                  "fed": self.s["fed"].get(it)})
                self.s["gear"].remove(it)
                self._on_gear_removed(it)
                continue
            have = self.s["inv"].get(it, 0)
            left = max(0, have - n)
            if have > 0:
                lost[it] = {"n": have - left, "portions": self.s["portionsLeft"].get(it), "uses": self.s["gearUses"].get(it)}
            if left:
                self.s["inv"][it] = left
            elif it in self.s["inv"]:
                del self.s["inv"][it]
                self.s["portionsLeft"].pop(it, None)
                if self.w.item_type(it) == "tool":
                    self.s["gearUses"].pop(it, None)
        return lost, lost_gear

    # ------------------------------------------------ переполнение
    def resolve_overflow_gear(self, keep: list[str]) -> str | None:
        """Экран «Что взять с собой»: keep — ровно min(gearSlots, текущие+новая) id из текущих и новой."""
        ov = self.s["overflow"]
        if not ov or ov[0]["kind"] != "gear":
            return "no_gear_overflow"
        new = ov[0]["item"]
        if self.w.is_gift(new):  # старое сохранение: дар в очереди — просто взять (ячейку не занимает)
            if new not in self.s["gear"]:
                self.s["gear"].append(new)
                self._on_gear_added(new)
            ov.pop(0)
            self._save_rng()
            return None
        # выбирают только среди обычного снаряжения; дары остаются на своих местах
        cands = [g for g in self.s["gear"] if not self.w.is_gift(g)] + [new]
        need = min(self.gear_slots(), len(cands))
        if len(keep) != need or len(set(keep)) != len(keep) or any(k not in cands for k in keep):
            return "bad_keep"
        for c in cands:
            if c not in keep and c != new:
                self._on_gear_removed(c)
        self.s["gear"] = [g for g in self.s["gear"] if self.w.is_gift(g) or g in keep] + ([new] if new in keep else [])
        if new in keep:
            self._on_gear_added(new)
        ov.pop(0)
        self._save_rng()
        return None

    def resolve_overflow_backpack(self, action: str, swap: dict | None, now: int) -> str | None:
        """Вещь не лезет в рюкзак: use — использовать сразу; drop — выбросить; stash — положить
        (если рюкзак полон, swap = {"action": "use"|"drop", "item": id из рюкзака} освобождает ячейку).
        Решает ОДНУ единицу первой записи очереди."""
        ov = self.s["overflow"]
        if not ov or ov[0]["kind"] != "backpack":
            return "no_backpack_overflow"
        it = ov[0]["item"]
        if action == "use":
            self._consume(it, now)
        elif action == "drop":
            pass
        elif action == "stash":
            if self.consumables_count() >= self.backpack_slots():
                if not swap:
                    return "need_swap"
                si, sa = swap.get("item"), swap.get("action")
                if sa not in ("use", "drop") or self.s["inv"].get(si, 0) <= 0 or self.w.item_type(si) not in CONSUMABLE:
                    return "bad_swap"
                if sa == "use":
                    if self.portions(si) > 1 and self.portions_open(si) > 1:
                        return "swap_not_free"  # порция не освобождает ячейку
                    self._use_one(si, now)
                else:
                    self._take_inv(si, 1)
            self.s["inv"][it] = self.s["inv"].get(it, 0) + 1
        else:
            return "bad_action"
        ov[0]["n"] -= 1
        if ov[0]["n"] <= 0:
            ov.pop(0)
        self._save_rng()
        return None

    # ------------------------------------------------ эффекты исхода
    def _apply_effects(self, eff: dict, now: int, stop: dict, source: str = "", ctx=()) -> bool:
        """Применить эффекты исхода. Вред (минусы, remove, delay, detour, bonus_reset) записывается в self._harm —
        choose() кладёт его в state.undo для «Сучка»/«Бусины» (§13.4)."""
        L = self.b["levels"]
        harm: dict = {}
        if "coins" in eff:
            v = eff["coins"]
            amt = L["coins"][v.lstrip("-")]
            if v.startswith("-") and self.gear_flag("noCoinLoss", ctx):
                amt = 0  # ракушка-пропуск: у воды водяной денег не берёт
            before = self.s["coins"]
            self.s["coins"] = max(0, self.s["coins"] + (-amt if v.startswith("-") else amt))
            if before > self.s["coins"]:
                harm["coins"] = before - self.s["coins"]
        pre = dict(self.s["stats"])
        neg = []
        for k in STATS:
            if k in eff:
                v = eff[k]
                amt = L["stat"][v.lstrip("-")]
                self.s["stats"][k] += -amt if v.startswith("-") else amt
                if v.startswith("-"):
                    neg.append(k)
        self._clamp_stats()
        lost_stats = {k: pre[k] - self.s["stats"][k] for k in neg if pre[k] - self.s["stats"][k] > 0}
        if lost_stats:
            harm["stats"] = lost_stats
        lost, lost_gear = self._remove_items(eff.get("remove") or {})
        if lost:
            harm["removed"] = lost
        if lost_gear:
            harm["removedGear"] = lost_gear
        self.give_items(eff.get("give") or {}, source)
        if "flag" in eff:
            for f in ([eff["flag"]] if isinstance(eff["flag"], str) else eff["flag"]):
                if f not in self.s["flags"]:
                    self.s["flags"].append(f)
        if "quest_start" in eff and eff["quest_start"] not in self.s["quests"] and eff["quest_start"] in self.w.quests:
            self.s["quests"][eff["quest_start"]] = {"startPos": self.s["pos"], "step": 0, "vars": {}}
        if "quest_var" in eff:
            targets = [stop["quest"]] if stop and "quest" in stop and stop["quest"] in self.s["quests"] else list(self.s["quests"])
            for qid in targets:
                for var, d in eff["quest_var"].items():
                    vars_ = self.s["quests"][qid]["vars"]
                    vars_[var] = vars_.get(var, 0) + d
        if eff.get("bonus_reset"):
            harm["bonusKm"] = self.s["bonusKm"]
            self.s["bonusKm"] = 0.0
        if "delay" in eff:
            harm["delay"] = self.s["delayUntil"]
            h = L["delayHours"][eff["delay"]]
            m = self.gear_mult("delayMult")
            if m != 1.0:
                h = max(1, py_round(h * m))
            self.s["delayUntil"] = now + int(h * MS_HOUR)
        if "detour" in eff:
            km = L["detourKm"][eff["detour"]]
            m = self.gear_mult("detourMult")
            if m != 1.0:
                km = max(1, py_round(km * m))
            dm = km * 1000.0
            if not eff.get("detour_end"):  # ответвление с концом-событием — сюжет, его дары не отменяют
                harm["detour"] = True
                harm["prevDetour"] = self.s["detour"]
            self.s["detour"] = {"remaining": dm, "total": dm, "end": eff.get("detour_end")}
        if "shortcut" in eff:
            jump = L["shortcutKm"][eff["shortcut"]] * 1000.0
            self.s["stop"] = None
            target, _, _ = self._next_stop()
            self.s["pos"] = min(self.s["pos"] + jump, target - 1.0)
            self.s["maxPos"] = max(self.s["maxPos"], self.s["pos"])
        self._harm = harm or None
        if eff.get("death"):
            self._die(now, "event")
            return True
        if min(self.s["stats"].values()) <= 0:
            if self._try_rescue(now):
                return False
            self._die(now, "event")
            return True
        return False

    # ------------------------------------------------ смерть
    def avg_daily_game_m(self, today: str | None = None) -> float:
        days = sorted(self.s["daySteps"])[-self.b["death"]["rollbackDaysWindow"]:]
        if not days:
            return 0.0
        return sum(self.s["daySteps"][d] for d in days) / len(days) * self.game_m_per_step()

    def _die(self, now: int, cause: str):
        d = self.b["death"]
        active = [self.s["daySteps"][k] for k in sorted(self.s["daySteps"]) if self.s["daySteps"][k] > 0][-d["rollbackDaysWindow"]:]
        per_day = (sum(active) / len(active) * self.game_m_per_step()) if active else 0.0
        back = max(d["rollbackMinKm"] * 1000.0, min(d["rollbackMaxKm"] * 1000.0, per_day))
        old = self.s["pos"]
        self.s["pos"] = max(0.0, old - back)
        for k in list(self.s["inv"]):
            if self.w.item_type(k) in CONSUMABLE:
                keep = math.floor(self.s["inv"][k] * d["keepConsumablesShare"])
                if keep:
                    self.s["inv"][k] = keep
                else:
                    del self.s["inv"][k]
                    self.s["portionsLeft"].pop(k, None)
        lost = math.floor(self.s["coins"] * d["coinLossShare"])
        self.s["coins"] -= lost
        for k in STATS:
            self.s["stats"][k] = float(self.b["stats"]["respawn"])
        self.s["detour"] = None
        self.s["delayUntil"] = 0
        self.s["bonusKm"] = 0.0
        self.s["heated"] = False
        self.s["heatedDay"] = 0
        self.s["overflow"] = []
        self.s["aidLock"] = False
        self.s["undo"] = None
        for qid in [q for q in self.s["quests"] if self.w.quests[q].get("kind") == "companion"]:
            del self.s["quests"][qid]
        self.s["nextRandomAt"] = max(self.s["nextRandomAt"], self.s["maxPos"] + self.b["randomEvents"]["firstAfterKm"] * 1000.0)
        self.s["deaths"] += 1
        place = self.w.last_place_before(self.s["pos"])
        self.s["stop"] = {"type": "death", "cause": cause, "back": round((old - self.s["pos"]) / 1000.0, 1),
                          "place": place["id"], "coinsLost": lost}
        self._log(now, "death", f"Сергей погиб и очнулся у {place['name']}", cause=cause)

    # ------------------------------------------------ рынок и остановки
    def market(self) -> list[tuple[str, int]]:
        st = self.s["stop"]
        if not st or st.get("type") not in ("place", "chapter_end"):
            return []
        p = self.w.place_by_id[st["place"]]
        markets = self.b["economy"]["markets"]
        m = markets.get(p.get("market", "none")) if p.get("market") != "regional" else None
        if not m:
            return []
        ids = list(m["items"])
        for i in (markets.get("regional") or {}).get(p["id"], []):
            if i not in ids:
                ids.append(i)  # региональные товары места — в конец списка, по наценке рынка места
        return [(i, int(round(self.w.items[i]["price"] * m["priceMult"]))) for i in ids]

    def buy_blocker(self, item: str) -> str | None:
        """None — можно купить; иначе код причины для интерфейса."""
        prices = dict(self.market())
        if item not in prices:
            return "not_sold"
        if self.s["coins"] < prices[item]:
            return "no_coins"
        t = self.w.item_type(item)
        if t in CONSUMABLE and self.consumables_count() >= self.backpack_slots():
            return "backpack_full"
        if t == "gear":
            if item in self.s["gear"]:
                return "have_gear"
            if not self.w.is_gift(item) and self.gear_used() >= self.gear_slots():
                return "gear_full"
        if t == "refill":
            tgt = self.w.items[item]["refill"]
            if tgt not in self.s["gear"]:
                return "no_stove"
            if self.gear_uses(tgt) >= self._max_uses(tgt):
                return "gas_full"
        return None

    def buy(self, item: str, now: int) -> bool:
        if self.buy_blocker(item) is not None:
            return False
        price = dict(self.market())[item]
        self.s["coins"] -= price
        t = self.w.item_type(item)
        if t == "gear":
            self._gain_gear(item, "market")
        elif t == "refill":
            self._gain_refill(item)
        else:
            self.s["inv"][item] = self.s["inv"].get(item, 0) + 1
        self._log(now, "buy", item, item=item, price=price)
        return True

    def drop_item(self, item: str) -> str | None:
        """Выбросить 1 шт.: из снаряжения — предмет целиком (с зарядами), из рюкзака/инструментов — одну единицу.
        None — выброшено; gift — дар духа выбросить нельзя; no_item — нечего выбрасывать."""
        if self.w.is_gift(item) and self.has_item(item):
            return "gift"
        if item in self.s["gear"]:
            self.s["gear"].remove(item)
            self._on_gear_removed(item)
        elif self.s["inv"].get(item, 0) > 0:
            self._take_inv(item, 1)
            if item not in self.s["inv"] and self.w.item_type(item) == "tool":
                self.s["gearUses"].pop(item, None)
        else:
            return "no_item"
        self._save_rng()
        return None

    def continue_journey(self, now: int) -> bool:
        """«Идти дальше». False — отказ (событие закрывается только выбором; есть overflow; финиш)."""
        st = self.s["stop"]
        if self.s["overflow"]:
            return False
        if not st or st["type"] == "finish":
            return False
        if st["type"] == "event":
            return False  # событие закрывается только выбором
        if st["type"] == "chapter_end":
            self.s["stop"] = {"type": "place", "place": st["place"]}
            return True
        self.s["stop"] = None
        return True

    # ------------------------------------------------ для интерфейса
    def days_left(self) -> int | None:
        per_day = self.avg_daily_game_m()
        if per_day <= 0:
            return None
        return math.ceil(max(0.0, self.w.length - self.s["pos"]) / per_day)


def _cond(value: int, cond: str) -> bool:
    for op in (">=", "<=", "==", ">", "<"):
        if cond.startswith(op):
            n = int(cond[len(op):])
            return {">=": value >= n, "<=": value <= n, "==": value == n, ">": value > n, "<": value < n}[op]
    return False


# ---------------------------------------------------------------- загрузка
def load_world(root: Path, map_json: dict | None = None, balance: dict | None = None) -> World:
    a = root / "app" / "assets"
    b = balance if balance is not None else json.loads((a / "balance.json").read_text(encoding="utf-8"))
    c = a / "content"

    def j(name, default):
        p = c / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    content = {
        "places": j("places.json", []),
        "chapters": j("chapters.json", []),
        "quests": j("quests.json", []),
        "events_random": j("events_random.json", []),
        "events_anchored": [e for f in sorted(c.glob("events_ch*.json")) for e in j(f.name, [])],
    }
    if map_json is None and (a / "map" / "map.json").exists():
        map_json = json.loads((a / "map" / "map.json").read_text(encoding="utf-8"))
    if map_json:
        pos = {k: float(v) for k, v in map_json["placeDistances"].items()}
        length = float(map_json["routeLengthM"])
    else:  # грубая оценка до появления карты
        pos, cum = {}, 0.0
        P = content["places"]
        for i, p in enumerate(P):
            if i:
                cum += _hv(P[i - 1], p) * 1.12
            pos[p["id"]] = cum
        length = cum
    return World(b, content, pos, length)


def _hv(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

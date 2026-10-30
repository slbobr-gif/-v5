"""Эталонный движок «Путника» (Python). Dart-версия — app/lib/engine/ — повторяет его правило в правило.

Используется симулятором баланса (tools/sim/simulate.py) и тестами правил.
Все числа — из balance.json, все тексты — из content/*.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

STATS = ("satiety", "water", "warmth")
MS_HOUR = 3_600_000


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
def new_state(world: World, seed: int, now_ms: int, today: str, today_steps: int = 0) -> dict:
    b = world.b
    return {
        "v": 1,
        "seed": seed & 0xFFFFFFFF,
        "rng": seed & 0xFFFFFFFF,
        "startedAt": now_ms,
        "startDay": today,
        "pos": 0.0,
        "maxPos": 0.0,
        "buffer": 0.0,
        "detour": None,
        "stats": dict(b["stats"]["start"]),
        "coins": b["economy"]["startCoins"],
        "inv": dict(b["economy"]["startItems"]),
        "stop": None,
        "delayUntil": 0,
        "flags": [],
        "seen": [],
        "recentRandom": [],
        "quests": {},
        "nextRandomAt": b["randomEvents"]["firstAfterKm"] * 1000.0,
        "bonusKm": 0.0,
        "lastTick": now_ms,
        "counted": {today: today_steps},
        "daySteps": {today: 0},
        "claimed": {},
        "deaths": 0,
        "journal": [],
        "finished": False,
    }


class Engine:
    def __init__(self, world: World, state: dict):
        self.w = world
        self.s = state
        self.b = world.b
        self.rng = Rng(state["rng"])

    # ------------------------------------------------ утилиты
    def _save_rng(self):
        self.s["rng"] = self.rng.state

    def _log(self, now: int, kind: str, text: str, **extra):
        self.s["journal"].append({"t": now, "kind": kind, "text": text, **extra})
        if len(self.s["journal"]) > 400:
            del self.s["journal"][:-400]

    def game_m_per_step(self) -> float:
        m = self.b["movement"]
        return m["stepLengthM"] * m["gameMultiplier"]

    def consumables_count(self) -> int:
        return sum(n for k, n in self.s["inv"].items() if self.w.items[k]["type"] in ("food", "drink"))

    def in_bonus(self) -> bool:
        st, bb = self.s["stats"], self.b["bonus"]
        return st["satiety"] >= bb["satietyAtLeast"] and st["water"] >= bb["waterAtLeast"]

    def noticed(self) -> bool:
        return self.s["bonusKm"] >= self.b["bonus"]["noticeAfterKm"]

    def _clamp_stats(self):
        mx = self.b["stats"]["max"]
        for k in STATS:
            self.s["stats"][k] = max(0.0, min(float(mx), self.s["stats"][k]))

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

    # ------------------------------------------------ время
    def apply_time(self, now: int):
        hours = max(0.0, (now - self.s["lastTick"]) / MS_HOUR)
        self.s["lastTick"] = now
        if hours <= 0:
            return
        floor = self.b["idleFloor"]
        for k in STATS:
            cur = self.s["stats"][k]
            nxt = cur - self.b["drainPerHour"][k] * hours
            self.s["stats"][k] = max(nxt, min(cur, floor))
        self._auto_consume(now)

    # ------------------------------------------------ еда из рюкзака
    def _item_gain(self, item: str, stat: str) -> float:
        return float(self.w.items[item].get(stat, 0))

    def _auto_consume(self, now: int):
        thr = self.b["stats"]["autoConsumeBelow"]
        for stat in STATS:
            for _ in range(4):
                if self.s["stats"][stat] >= thr:
                    break
                cands = [k for k, n in self.s["inv"].items() if n > 0
                         and self.w.items[k]["type"] in ("food", "drink") and self._item_gain(k, stat) > 0]
                if not cands:
                    break
                gap = self.b["stats"]["max"] - self.s["stats"][stat]
                fitting = [k for k in cands if self._item_gain(k, stat) <= gap]
                pool = fitting or cands
                pick = (max if fitting else min)(sorted(pool), key=lambda k: self._item_gain(k, stat))
                self._use_item(pick, now, auto=True)

    def _use_item(self, item: str, now: int, auto: bool = False):
        self.s["inv"][item] -= 1
        if self.s["inv"][item] <= 0:
            del self.s["inv"][item]
        for k in STATS:
            self.s["stats"][k] += self.w.items[item].get(k, 0)
        self._clamp_stats()
        if auto:
            self._log(now, "eat", f"Сергей использовал: {item}", item=item)

    def use_item(self, item: str, now: int) -> bool:
        if self.s["inv"].get(item, 0) <= 0 or self.w.items[item]["type"] not in ("food", "drink"):
            return False
        self._use_item(item, now)
        self._save_rng()
        return True

    # ------------------------------------------------ движение
    def _drain_walk(self, km: float):
        st = self.s["stats"]
        dk = self.b["drainPerKm"]
        bonus = self.in_bonus()
        mult = self.b["bonus"]["drainMultiplier"] if bonus else 1.0
        pos = self.s["pos"]
        wx = self.b["weather"]["types"][self.w.weather_at(self.s["seed"], pos)]
        cold = self.b["chapterCold"][str(self.w.chapter_at(pos))]
        gear = 1.0
        if self.s["inv"].get("socks", 0) > 0:
            gear *= self.w.items["socks"]["warmthDrainMult"]
        weather_warm = wx.get("warmth", 1.0)
        if self.s["inv"].get("raincoat", 0) > 0 and weather_warm > 1.0:
            weather_warm = 1.0 + (weather_warm - 1.0) * self.w.items["raincoat"]["weatherWarmthMult"]
        st["satiety"] -= dk["satiety"] * km * mult
        st["water"] -= dk["water"] * km * wx.get("water", 1.0) * mult
        st["warmth"] -= dk["warmth"] * km * cold * weather_warm * gear * mult
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
        return best

    def advance(self, now: int) -> list[dict]:
        """Двигает героя на накопленный буфер. Возвращает события для интерфейса."""
        out: list[dict] = []
        self.apply_time(now)
        guard = 0
        while self.s["buffer"] > 0.5 and not self.s["stop"] and not self.s["finished"]:
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
            self._drain_walk(chunk / 1000.0)
            self._auto_consume(now)
            self._clamp_stats()
            if on_route:
                self.s["pos"] += chunk
                self.s["maxPos"] = max(self.s["maxPos"], self.s["pos"])
            left -= chunk
            if min(self.s["stats"].values()) <= 0:
                if not on_route:
                    pass
                self._die(now, "stats")
                return False
        return True

    def _arrive(self, kind: str, data, now: int):
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
            step = self.w.quests[qid]["steps"][q["step"]]
            self.s["stop"] = {"type": "event", "quest": qid, "step": q["step"], "event": self._quest_event(qid)["id"]}
            return
        if kind == "random":
            e = self._pick_random()
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

    def _pick_random(self):
        ch = f"ch{self.w.chapter_at(self.s['pos'])}"
        pool = [e for e in self.w.randoms if (ch in e.get("tags", []) or "any" in e.get("tags", []))
                and e["id"] not in self.s["recentRandom"]]
        if not pool:
            return None
        if self.noticed() and self.rng.next_float() < self.b["bonus"]["noticeRiskChance"]:
            risky = [e for e in pool if "risk" in e.get("tags", [])]
            if risky:
                pool = risky
        e = pool[self.rng.next_u32() % len(pool)]
        self.s["recentRandom"].append(e["id"])
        keep = max(1, min(12, len(self.w.randoms) // 2))
        self.s["recentRandom"] = self.s["recentRandom"][-keep:]
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
            return self._quest_event(st["quest"])
        return self.w.events_by_id.get(st["event"])

    def choice_available(self, choice: dict) -> bool:
        req = choice.get("requires") or {}
        if "item" in req and self.s["inv"].get(req["item"], 0) <= 0:
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

    def choose(self, choice_id: str, now: int) -> dict:
        ev = self.current_event()
        st = self.s["stop"]
        choice = next(c for c in ev["choices"] if c["id"] == choice_id)
        if not self.choice_available(choice):
            return {"ok": False}
        outs = choice["outcomes"]
        o = outs[self.rng.pick_weighted([x["weight"] for x in outs])]
        died = self._apply_effects(o.get("effects", {}), now, st)
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
        self._log(now, "event", ev["title"], event=ev["id"], choice=choice_id, outcome=o.get("text", ""))
        if not died:
            self.s["stop"] = None
        self._save_rng()
        return {"ok": True, "outcome": o, "died": died}

    def _apply_effects(self, eff: dict, now: int, stop: dict) -> bool:
        L = self.b["levels"]
        if "coins" in eff:
            v = eff["coins"]
            amt = L["coins"][v.lstrip("-")]
            self.s["coins"] = max(0, self.s["coins"] + (-amt if v.startswith("-") else amt))
        for k in STATS:
            if k in eff:
                v = eff[k]
                amt = L["stat"][v.lstrip("-")]
                self.s["stats"][k] += -amt if v.startswith("-") else amt
        self._clamp_stats()
        for it, n in (eff.get("remove") or {}).items():
            have = self.s["inv"].get(it, 0)
            left = max(0, have - n)
            if left:
                self.s["inv"][it] = left
            elif it in self.s["inv"]:
                del self.s["inv"][it]
        for it, n in (eff.get("give") or {}).items():
            if self.w.items[it]["type"] in ("food", "drink"):
                room = self.b["economy"]["backpackSlots"] - self.consumables_count()
                n = max(0, min(n, room))
            if n:
                self.s["inv"][it] = self.s["inv"].get(it, 0) + n
        if "flag" in eff:
            for f in ([eff["flag"]] if isinstance(eff["flag"], str) else eff["flag"]):
                if f not in self.s["flags"]:
                    self.s["flags"].append(f)
        if "quest_start" in eff and eff["quest_start"] not in self.s["quests"]:
            self.s["quests"][eff["quest_start"]] = {"startPos": self.s["pos"], "step": 0, "vars": {}}
        if "quest_var" in eff:
            targets = [stop["quest"]] if stop and "quest" in stop and stop["quest"] in self.s["quests"] else list(self.s["quests"])
            for qid in targets:
                for var, d in eff["quest_var"].items():
                    vars_ = self.s["quests"][qid]["vars"]
                    vars_[var] = vars_.get(var, 0) + d
        if eff.get("bonus_reset"):
            self.s["bonusKm"] = 0.0
        if "delay" in eff:
            self.s["delayUntil"] = now + int(L["delayHours"][eff["delay"]] * MS_HOUR)
        if "detour" in eff:
            m = L["detourKm"][eff["detour"]] * 1000.0
            self.s["detour"] = {"remaining": m, "total": m, "end": eff.get("detour_end")}
        if "shortcut" in eff:
            jump = L["shortcutKm"][eff["shortcut"]] * 1000.0
            self.s["stop"] = None
            target, _, _ = self._next_stop()
            self.s["pos"] = min(self.s["pos"] + jump, target - 1.0)
            self.s["maxPos"] = max(self.s["maxPos"], self.s["pos"])
        if eff.get("death") or min(self.s["stats"].values()) <= 0:
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
            if self.w.items[k]["type"] in ("food", "drink"):
                keep = math.floor(self.s["inv"][k] * d["keepConsumablesShare"])
                if keep:
                    self.s["inv"][k] = keep
                else:
                    del self.s["inv"][k]
        lost = math.floor(self.s["coins"] * d["coinLossShare"])
        self.s["coins"] -= lost
        for k in STATS:
            self.s["stats"][k] = float(self.b["stats"]["respawn"])
        self.s["detour"] = None
        self.s["delayUntil"] = 0
        self.s["bonusKm"] = 0.0
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
        m = self.b["economy"]["markets"].get(p.get("market", "none"))
        if not m:
            return []
        return [(i, int(round(self.w.items[i]["price"] * m["priceMult"]))) for i in m["items"]]

    def buy(self, item: str, now: int) -> bool:
        prices = dict(self.market())
        if item not in prices or self.s["coins"] < prices[item]:
            return False
        t = self.w.items[item]["type"]
        if t in ("food", "drink") and self.consumables_count() >= self.b["economy"]["backpackSlots"]:
            return False
        if t == "gear" and self.s["inv"].get(item, 0) > 0:
            return False
        self.s["coins"] -= prices[item]
        self.s["inv"][item] = self.s["inv"].get(item, 0) + 1
        self._log(now, "buy", item, item=item, price=prices[item])
        return True

    def continue_journey(self, now: int):
        st = self.s["stop"]
        if not st or st["type"] == "finish":
            return
        if st["type"] == "event":
            return  # событие закрывается только выбором
        if st["type"] == "chapter_end":
            self.s["stop"] = {"type": "place", "place": st["place"]}
            return
        self.s["stop"] = None

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
def load_world(root: Path, map_json: dict | None = None) -> World:
    a = root / "app" / "assets"
    b = json.loads((a / "balance.json").read_text(encoding="utf-8"))
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

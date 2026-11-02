"""Эталонный сценарий для теста совпадения движков (Python ↔ Dart), формат v2 (v5.3).

Пишет app/test/fixtures/parity.json. Детерминированный «игрок» ниже играет 20 дней: собирает старт-набор,
греет воду, получает по переполнению каждого вида (рюкзак и снаряжение), ходит по зонам. КАЖДЫЙ вызов
движка записывается в days[i].ops (имя метода как в Dart + аргументы + результат), так что Dart-тест не
повторяет политику игрока, а просто проигрывает ops по порядку и сверяет результаты и снимок дня.
Формат описан в docs/v5/08-engine-api-v5.3.md, §9. Перегенерировать после любой правки контента/баланса/правил:
    python3 tools/sim/make_parity_fixture.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import CONSUMABLE, Engine, load_world, new_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
T0 = 1777622400000  # 2026-05-01 08:00 UTC — фиксированное время, не зависит от часового пояса
DAY = 24 * 3600 * 1000
SEED = 12345
BASELINE = 500
STEPS = [6000, 9000, 4000, 12000, 0, 7000, 8000, 15000, 3000, 7000,
         9000, 11000, 2000, 7000, 7000, 13000, 0, 9000, 8000, 10000]
LOADOUT_GEAR = ["gas_stove", "first_aid", "trekking_poles"]
LOADOUT_PACK = {"bread": 2, "water": 1, "thermos": 1, "tea": 1}
FORCED = {  # день (индекс) → выдать предметы после обычного хода дня: по одному переполнению каждого вида
    1: {"ball_yaga": 1},  # клубок: дальше бот спрашивает его на событиях, когда готов
    2: {"pie": 7},
    5: {"compass": 1, "amulet_leshy": 1},
    # §13: дары духов — бусина/сучок (отмена вреда), крючок и камешек (действия), жемчужина (продажа),
    # лапоть (ест в смену даты), венок (вянет через 3 дня), лента и ракушка (условные перки у воды)
    6: {"bead_kikimora": 1, "twig_leshy": 1, "hook_vodyanoy": 1, "pearl_rusalka": 1},
    # дары ячеек не занимают (V5-43): переполнение снаряжения даёт обычная вещь — носки при 4 занятых ячейках
    8: {"lapot_domovoy": 1, "stone_bannik": 1, "sheaf_ovinnik": 1, "socks": 1},
    10: {"wreath_poludnitsa": 1},  # вянет на 4-й игровой день — ячейка освобождается под ракушку
    14: {"shell_vodyanoy": 1, "thread_yaga": 1},
}
# дни (индекс), когда бот выбирает ПОСЛЕДНИЙ доступный вариант (обычно рискованный) — ради смертей и аптечки
BOLD_DAYS = {4, 5, 6, 7, 8}  # после V5-43 (дары без ячеек) этот отрезок даёт и смерть, и аптечку
# день (индекс) → «Нагреть»: (сколько раз нажать, выпить/съесть ли горячее). День 4: греет и не пьёт —
# к следующему дню (новая игровая дата) горелка остывает без траты заряда.
HEAT_DAYS = {0: (2, True), 3: (1, False), 6: (1, True), 10: (1, True)}


class Rec:
    """Обёртка над Engine: вызывает метод и пишет op в текущий день."""

    def __init__(self, e: Engine):
        self.e = e
        self.ops: list[dict] = []

    def _op(self, name, ret, **args):
        self.ops.append({"op": name, **args, "ret": ret})
        return ret

    def sync_steps(self, days, now):
        return self._op("syncSteps", self.e.sync_steps(days, now), days=days, now=now)

    def claim_login(self, day, now):
        return self._op("claimLogin", self.e.claim_login(day, now), day=day, now=now)

    def advance(self, now):
        return self._op("advance", len(self.e.advance(now)), now=now)

    def start_loadout(self, gear, pack, now):
        return self._op("startLoadout", self.e.start_loadout(gear, pack, now), gear=gear, pack=pack, now=now)

    def choose(self, choice, now):
        r = self.e.choose(choice, now)
        return self._op("choose", {"ok": r["ok"], "died": r.get("died", False)}, choice=choice, now=now)

    def buy(self, item, now):
        return self._op("buy", self.e.buy(item, now), item=item, now=now)

    def continue_journey(self, now):
        return self._op("continueJourney", self.e.continue_journey(now), now=now)

    def heat(self, now):
        return self._op("heat", self.e.heat(now), now=now)

    def use_item(self, item, now):
        return self._op("useItem", self.e.use_item(item, now), item=item, now=now)

    def give_items(self, items, source):
        self.e.give_items(items, source)
        return self._op("giveItems", None, items=items, source=source)

    def resolve_gear(self, keep):
        return self._op("resolveGearOverflow", self.e.resolve_overflow_gear(keep), keep=keep)

    def resolve_backpack(self, action, swap, now):
        return self._op("resolveBackpackOverflow", self.e.resolve_overflow_backpack(action, swap, now),
                        action=action, swapAction=(swap or {}).get("action"), swapItem=(swap or {}).get("item"), now=now)

    def ask_clew(self, now):
        return self._op("askClew", self.e.ask_clew(now), now=now)

    def use_gift(self, item, now):
        return self._op("useGift", self.e.use_gift(item, now), item=item, now=now)

    def sell(self, item, now):
        return self._op("sell", self.e.sell(item, now), item=item, now=now)

    def drop_item(self, item):
        return self._op("dropItem", self.e.drop_item(item), item=item)

    def dismiss_death(self):
        self.e.s["stop"] = None
        return self._op("dismissDeath", None)


class Bot:
    """Детерминированный игрок: первый доступный вариант, хлеб и газ на привале, греет, переполнение — по кругу."""

    def __init__(self, r: Rec):
        self.r = r
        self.k = 0
        self.bold = False

    def gifts(self, kinds, now):
        """Нажать первый готовый дар нужного вида (порядок held_items)."""
        e = self.r.e
        for it in e.held_items():
            if (e.w.items.get(it, {}).get("ability") or {}).get("kind") in kinds and e.gift_status(it, now) == "ready":
                self.r.use_gift(it, now)
                return

    def resolve(self, now):
        e = self.r.e
        while e.s["overflow"]:
            o = e.s["overflow"][0]
            if o["kind"] == "gear":
                slots = [g for g in e.s["gear"] if not e.w.is_gift(g)]  # дары в выборе не участвуют
                keep = slots[:-1] + [o["item"]]  # новая вместо последней
                self.r.resolve_gear(keep)
                continue
            act = ("use", "drop", "stash")[self.k % 3]
            self.k += 1
            swap = None
            if act == "stash" and e.consumables_count() >= e.backpack_slots():
                first = sorted(k for k, n in e.s["inv"].items() if n > 0 and e.w.item_type(k) in CONSUMABLE)[0]
                swap = {"action": "drop", "item": first}
            self.r.resolve_backpack(act, swap, now)

    def warm_up(self, day_index, now):
        e = self.r.e
        presses, drink = HEAT_DAYS.get(day_index, (0, False))
        if e.s["stats"]["warmth"] < 60 and not presses:
            presses, drink = 1, True
        if not presses or e.heat_status(now) not in ("ready", "on"):
            return
        for _ in range(presses):
            self.r.heat(now)
        hot = sorted(k for k, n in e.s["inv"].items() if n > 0 and e.w.heatable(k))
        if drink and hot:
            self.r.use_item(hot[0], now)

    def act(self, now):
        e = self.r.e
        for _ in range(60):
            self.resolve(now)
            st = e.s["stop"]
            if not st or st["type"] == "finish":
                return
            if st["type"] == "event":
                ev = e.current_event()
                if e.clew_status(now) == "ready":
                    self.r.ask_clew(now)
                avail = [c for c in ev["choices"] if e.choice_available(c)]
                ch = avail[-1] if self.bold else avail[0]
                self.r.choose(ch["id"], now)
                if e.s["undo"]:
                    self.gifts(("mirage",) if "delay" not in e.s["undo"] else ("guide", "mirage"), now)
                self.resolve(now)
            elif st["type"] in ("place", "chapter_end"):
                sold = {i for i, _ in e.market()}
                if "bread" in sold and e.s["inv"].get("bread", 0) < 2:
                    self.r.buy("bread", now)
                if "gas" in sold and e.buy_blocker("gas") is None and e.gear_uses("gas_stove") <= 7:
                    self.r.buy("gas", now)
                self.gifts(("action",), now)
                for it, _ in e.sell_offers():
                    self.r.sell(it, now)
                self.resolve(now)
                self.r.continue_journey(now)
            elif st["type"] == "death":
                self.r.dismiss_death()
            self.r.advance(now)


def snapshot(w, s, e):
    return {
        "pos": round(s["pos"], 2),
        "buffer": round(s["buffer"], 2),
        "coins": s["coins"],
        "stats": {k: round(v, 3) for k, v in s["stats"].items()},
        "inv": dict(sorted(s["inv"].items())),
        "gear": list(s["gear"]),
        "gearUses": dict(sorted(s["gearUses"].items())),
        "heated": s["heated"],
        "heatedDay": s["heatedDay"],
        "overflow": [dict(o) for o in s["overflow"]],
        "aidLock": s["aidLock"],
        "portionsLeft": dict(sorted(s["portionsLeft"].items())),
        "abilityReady": dict(sorted(s["abilityReady"].items())),
        "fed": dict(sorted(s["fed"].items())),
        "expires": dict(sorted(s["expires"].items())),
        "dayMark": s["dayMark"],
        "undoKeys": sorted(s["undo"]) if s["undo"] else None,
        "stop": (s["stop"] or {}).get("type"),
        "deaths": s["deaths"],
        "seen": len(s["seen"]),
        "journal": len(s["journal"]),
        "journalTail": [j["kind"] for j in s["journal"][-4:]],
        "journalPos": [j["pos"] for j in s["journal"][-4:]],
        "lastEvent": next(({"event": j["event"], "cid": j["cid"], "oi": j["oi"], "pos": j["pos"],
                            "quest": j.get("quest"), "step": j.get("step")}
                           for j in reversed(s["journal"]) if j["kind"] == "event"), None),
        "rng": s["rng"],
        "zone": w.zone_at(s["pos"]),
        "delayUntil": s["delayUntil"],
        "nextRandomAt": round(s["nextRandomAt"], 2),
    }


def main():
    w = load_world(ROOT)
    days = [f"2026-05-{d:02d}" for d in range(1, 32)][:len(STEPS)]
    s = new_state(w, SEED, T0, days[0], BASELINE)
    e = Engine(w, s)
    rec = Rec(e)
    bot = Bot(rec)
    rec.start_loadout(LOADOUT_GEAR, LOADOUT_PACK, T0)
    setup_ops = rec.ops
    out = []
    for i, steps in enumerate(STEPS):
        rec.ops = []
        now = T0 + i * DAY + 10 * 3600 * 1000
        rec.sync_steps({days[i]: BASELINE + steps if i == 0 else steps}, now)
        rec.claim_login(days[i], now)
        bot.bold = i in BOLD_DAYS
        rec.advance(now)
        bot.act(now)
        bot.warm_up(i, now)
        if i == 1 and s["inv"].get("thermos"):
            rec.use_item("thermos", now)  # порция из термоса: ячейка остаётся, portionsLeft = portions − 1
        if i in FORCED:
            rec.give_items(FORCED[i], f"fixture_day{i + 1}")
            bot.act(now)
            bot.resolve(now)
        if i == 9:
            # «Выбросить»: дар — отказ gift; обычное снаряжение — целиком; еда — одна единица; чужое — no_item
            gifts = [g for g in s["gear"] if w.is_gift(g)]
            plain = [g for g in s["gear"] if not w.is_gift(g)]
            for it in gifts[:1] + plain[-1:] + ["bread", "no_such_item"]:
                rec.drop_item(it)
        out.append({"day": days[i], "ops": rec.ops, "expected": snapshot(w, s, e)})
    kinds = {}
    for d in out:
        for o in d["ops"]:
            kinds[o["op"]] = kinds.get(o["op"], 0) + 1
    probe = sorted({round(w.pos_of[p["id"]] + dx, 1) for p in w.places for dx in (-3500.0, -500.0, 0.0, 500.0, 3500.0)
                    if 0 <= w.pos_of[p["id"]] + dx <= w.length})
    fx = {
        "format": 2,
        "t0": T0, "seed": SEED, "baseline": BASELINE, "steps": STEPS, "startDay": days[0],
        "routeLengthM": round(w.length, 1),
        "setup": setup_ops,
        "days": out,
        "zoneProbe": [[p, w.zone_at(p)] for p in probe],
        "itemPerks": {k: w.item_perks(k) for k in w.items},
        "starterGear": w.starter_gear(),
        "starterPack": w.starter_pack(),
    }
    p = ROOT / "app" / "test" / "fixtures" / "parity.json"
    p.write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
    last = out[-1]["expected"]
    used = {k: kinds.get(k, 0) for k in ("heat", "useItem", "askClew", "useGift", "sell", "dropItem", "resolveBackpackOverflow",
                                         "resolveGearOverflow", "choose", "buy")}
    jk = {}
    for j in s["journal"]:
        jk[j["kind"]] = jk.get(j["kind"], 0) + 1
    print("журнал:", {k: jk[k] for k in sorted(jk) if k in ("first_aid", "death", "gift", "ability", "camp", "upkeep", "wilt", "sell")})
    print(f"parity v2: {len(out)} дней, итог {last['pos']/1000:.1f} км, монет {last['coins']}, событий {last['seen']}, "
          f"смертей {last['deaths']}, снаряжение {last['gear']}, заряды {last['gearUses']}; вызовы {used}")
    zones = {}
    for d in out:
        zones[d["expected"]["zone"]] = zones.get(d["expected"]["zone"], 0) + 1
    print(f"зоны в конце дней: {zones}; проб зоны: {len(fx['zoneProbe'])}")


if __name__ == "__main__":
    main()

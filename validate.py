"""Валидатор контента «Путника» (docs/v5/02-content-schema.md, docs/v5/07-change-request-v5.3.md).

Запуск из корня репозитория: python3 tools/content/validate.py [--strict]
--strict требует полный объём MVP (число событий, мыслей, квестов, размеры пулов зон, слова-маркеры).

Зоны (v5.3): у каждого события (якорного, квестового, случайного) обязательно "zone": city|suburb|wild;
якорное событие обязано лежать в своей зоне (tools/content/zones.py, по anchor; кроме detour_only — это
конец ответвления, он не на маршруте); пулы случайных событий: city ≥ 12, suburb ≥ 14, wild ≥ 14 и в
каждой зоне ≥ 3 с тегом any. Слова-маркеры — tools/content/zone_words.json (если файла нет — проверка
пропускается): {"city": ["забор", "дач", ...], "suburb": [...], "wild": [...]} — основы слов, которые
НЕЛЬЗЯ встречать в событиях этой зоны (также понимается {"city": {"forbid": [...]}} и
{"forbidden": {"city": [...]}}). Совпадение — с начала слова, без учёта регистра, по заголовку, тексту,
вариантам и исходам. Исключение — непустое поле события "zone_note": "почему здесь можно".
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zones as Z  # noqa: E402
C = ROOT / "app" / "assets" / "content"
B = json.loads((ROOT / "app" / "assets" / "balance.json").read_text(encoding="utf-8"))
STRICT = "--strict" in sys.argv
errors, warns = [], []


def load(name, default=None):
    p = C / name
    if not p.exists():
        if default is None:
            errors.append(f"нет файла {name}")
        return default if default is not None else []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{name}: битый JSON: {e}")
        return default if default is not None else []


places = {p["id"]: p for p in load("places.json")}
items_list = load("items.json")
items = {i["id"] for i in items_list}
creatures = {c["id"] for c in load("creatures.json")}
chapters = {c["id"]: c for c in load("chapters.json")}
quests = load("quests.json", [])
quest_ids = {q.get("id") for q in quests}

LEVELS = set(B["levels"]["coins"])
STATS = ("satiety", "water", "warmth")
KINDS = {"random", "regional", "chapter", "creature", "companion"}
ARTS = {"forest", "field", "river", "lake", "village", "town", "road", "night", "rain", "swamp",
        "bathhouse", "hut", "campfire", "station"}
RISKS = {"none", "low", "high", "fatal"}
EFFECT_KEYS = {"coins", "satiety", "water", "warmth", "give", "remove", "delay", "detour", "detour_end",
               "shortcut", "flag", "quest_start", "quest_var", "death", "bonus_reset"}
TAGS = {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "forest", "road", "village", "water", "night", "rain", "fog", "heat",
        "field", "town", "swamp", "any", "risk"}
all_event_ids = {}
flags_set, flags_needed = set(), []
detour_ends = []
ZONE_MIN = {"city": 32, "suburb": 38, "wild": 40}
ZONE_ANY_MIN = 8
zoned_events = []  # (где, событие) — для слов-маркеров


def load_zone_words():
    p = ROOT / "tools" / "content" / "zone_words.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"zone_words.json: битый JSON: {e}")
        return None
    out = {}
    for z in Z.ZONES:
        v = data.get(z) if isinstance(data, dict) else None
        if isinstance(v, dict):
            v = next((v[k] for k in ("forbid", "forbidden", "deny", "not", "words", "markers") if isinstance(v.get(k), list)), None)
        if v is None and isinstance(data, dict):
            for k in ("forbid", "forbidden", "deny", "markers"):
                if isinstance(data.get(k), dict) and isinstance(data[k].get(z), list):
                    v = data[k][z]
        if isinstance(v, list):
            out[z] = [w.strip().lower() for w in v if isinstance(w, str) and w.strip()]
    if not out:
        warns.append("zone_words.json: не понял формат — ожидаю {\"city\": [основы слов], ...}; проверка маркеров пропущена")
        return None
    return out


def event_texts(e):
    parts = [e.get("title", ""), e.get("text", "")]
    for c in e.get("choices", []):
        parts.append(c.get("text", ""))
        for o in c.get("outcomes", []):
            parts.append(o.get("text", ""))
    return " \n ".join(parts).lower()


def signed_level(v):
    return isinstance(v, str) and v.lstrip("-") in LEVELS


def check_effects(where, eff, risk):
    if not isinstance(eff, dict):
        errors.append(f"{where}: effects должен быть объектом")
        return
    for k, v in eff.items():
        if k not in EFFECT_KEYS:
            errors.append(f"{where}: неизвестный эффект {k}")
        elif k in ("coins",) + STATS and not signed_level(v):
            errors.append(f"{where}: {k} = {v!r}, нужен уровень small/medium/large (со знаком -)")
        elif k in ("give", "remove"):
            if not isinstance(v, dict):
                errors.append(f"{where}: {k} должен быть объектом")
            else:
                for it, n in v.items():
                    if it not in items:
                        errors.append(f"{where}: нет предмета {it}")
                    if not isinstance(n, int) or not 1 <= n <= 5:
                        errors.append(f"{where}: {k}.{it} = {n}, нужно 1..5")
        elif k == "delay" and v not in B["levels"]["delayHours"]:
            errors.append(f"{where}: delay = {v!r}")
        elif k == "detour" and v not in B["levels"]["detourKm"]:
            errors.append(f"{where}: detour = {v!r}")
        elif k == "shortcut" and v not in B["levels"]["shortcutKm"]:
            errors.append(f"{where}: shortcut = {v!r}")
        elif k == "detour_end":
            detour_ends.append((where, v))
        elif k == "flag":
            for f in ([v] if isinstance(v, str) else v):
                flags_set.add(f)
        elif k == "quest_start":
            if v not in quest_ids:
                errors.append(f"{where}: quest_start {v} не найден в quests.json")
        elif k == "quest_var":
            if not isinstance(v, dict) or not all(isinstance(x, int) for x in v.values()):
                errors.append(f"{where}: quest_var должен быть {{имя: целое}}")
        elif k in ("death", "bonus_reset") and v is not True:
            errors.append(f"{where}: {k} допускает только true")
    if eff.get("death") and risk != "fatal":
        errors.append(f"{where}: смерть возможна только у варианта с risk: fatal")
    if "detour_end" in eff and "detour" not in eff:
        errors.append(f"{where}: detour_end без detour")


def check_event(where, e, anchored_ok=True, need_anchor=False):
    eid = e.get("id")
    if not eid or not re.fullmatch(r"[a-z0-9_]{3,60}", eid):
        errors.append(f"{where}: плохой id {eid!r}")
    if eid in all_event_ids:
        errors.append(f"{where}: повтор id {eid} (уже в {all_event_ids[eid]})")
    all_event_ids[eid] = where
    w = f"{where}:{eid}"
    if e.get("zone") not in Z.ZONES:
        errors.append(f"{w}: нет зоны или неверная zone {e.get('zone')!r} (city/suburb/wild)")
    if "zone_note" in e and not (isinstance(e["zone_note"], str) and e["zone_note"].strip()):
        errors.append(f"{w}: zone_note должен быть непустой строкой")
    zoned_events.append((w, e))
    if "mood" in e and e["mood"] not in ("neutral", "kind", "cunning", "angry"):
        errors.append(f"{w}: mood {e['mood']!r} (neutral/kind/cunning/angry)")
    if e.get("kind") not in KINDS:
        errors.append(f"{w}: kind {e.get('kind')!r}")
    if e.get("art") not in ARTS:
        errors.append(f"{w}: art {e.get('art')!r}")
    if e.get("creature") not in (None, *creatures):
        errors.append(f"{w}: нет существа {e.get('creature')}")
    if e.get("kind") == "creature" and not e.get("creature"):
        errors.append(f"{w}: kind creature без поля creature")
    for fld, lo, hi in (("title", 3, 60), ("text", 200, 900)):
        t = e.get(fld, "")
        if not lo <= len(t) <= hi:
            (errors if STRICT else warns).append(f"{w}: {fld} длина {len(t)} вне {lo}..{hi}")
    a = e.get("anchor")
    if need_anchor:
        if not a or a.get("after") not in places or not isinstance(a.get("km"), (int, float)) or not 0 <= a["km"] <= 200:
            errors.append(f"{w}: нужен anchor {{after: id точки, km: 0..200}}, есть {a}")
    elif a:
        errors.append(f"{w}: у этого события не должно быть anchor")
    ch = e.get("choices", [])
    if ch and all(c.get("requires") for c in ch):
        errors.append(f"{w}: у всех вариантов есть requires — игрок может застрять; нужен хотя бы один без требований")
    if not 2 <= len(ch) <= 3:
        errors.append(f"{w}: вариантов {len(ch)}, нужно 2–3")
    cids = set()
    for c in ch:
        cw = f"{w}/{c.get('id')}"
        if c.get("id") in cids:
            errors.append(f"{cw}: повтор id варианта")
        cids.add(c.get("id"))
        if not 2 <= len(c.get("text", "")) <= 80:
            errors.append(f"{cw}: текст варианта {len(c.get('text', ''))} знаков (2..80)")
        if c.get("risk") not in RISKS:
            errors.append(f"{cw}: risk {c.get('risk')!r}")
        req = c.get("requires")
        if req:
            for k, v in req.items():
                if k == "item" and v not in items:
                    errors.append(f"{cw}: requires нет предмета {v}")
                elif k == "coins" and v not in LEVELS:
                    errors.append(f"{cw}: requires coins {v!r}")
                elif k == "flag":
                    flags_needed.append((cw, v))
                elif k not in ("item", "coins", "flag"):
                    errors.append(f"{cw}: requires {k}")
        outs = c.get("outcomes", [])
        if not outs:
            errors.append(f"{cw}: нет исходов")
        has_death = False
        for i, o in enumerate(outs):
            if not isinstance(o.get("weight"), int) or o["weight"] < 1:
                errors.append(f"{cw}#{i}: weight должен быть целым ≥ 1")
            if not 40 <= len(o.get("text", "")) <= 500:
                (errors if STRICT else warns).append(f"{cw}#{i}: текст исхода {len(o.get('text', ''))} знаков (40..500)")
            check_effects(f"{cw}#{i}", o.get("effects", {}), c.get("risk"))
            has_death = has_death or bool(o.get("effects", {}).get("death"))
        if c.get("risk") == "fatal" and not has_death:
            errors.append(f"{cw}: risk fatal без исхода со смертью")
        if has_death and len(outs) < 2:
            errors.append(f"{cw}: смерть не может быть единственным исходом")


# --- авторские и случайные события
index = load("index.json", {"anchored": []})
listed = set(index.get("anchored", []))
present = {p.name for p in C.glob("events_ch*.json")}
for missing in sorted(present - listed):
    errors.append(f"index.json: файл {missing} не указан в anchored — приложение его не загрузит")
for ghost in sorted(listed - present):
    warns.append(f"index.json: {ghost} указан, но файла нет")
anchored = []
for name in sorted(p.name for p in C.glob("events_ch*.json")):
    for e in load(name):
        check_event(name, e, need_anchor=True)
        anchored.append(e)
        a = e.get("anchor") or {}
        if a.get("after") in places and places[a["after"]].get("chapter") != e.get("chapter"):
            errors.append(f"{name}:{e.get('id')}: точка {a['after']} из главы {places[a['after']].get('chapter')}, а событие главы {e.get('chapter')}")
        if (not e.get("detour_only") and e.get("zone") in Z.ZONES and a.get("after") in places
                and isinstance(a.get("km"), (int, float))):
            real = Z.anchor_zone(a)
            if real != e["zone"]:
                errors.append(f"{name}:{e.get('id')}: zone {e['zone']}, а якорь {a['after']}+{a['km']} км "
                              f"({Z.anchor_km(a):.1f} км от Кремля) — в зоне {real}; меняйте якорь или текст, не зону")
randoms = load("events_random.json", [])
from check_random_zones import TOPONYMS, NORTH, NORTH_TAGS  # noqa: E402  (корни топонимов — там)
for e in randoms:
    check_event("events_random.json", e)
    _flat = event_texts(e).replace("\n", " ")
    _topo = sorted({m.group(0) for m in TOPONYMS.finditer(_flat)})
    if _topo:
        errors.append(f"events_random.json:{e.get('id')}: конкретные места в случайном событии: {', '.join(_topo)}")
    if NORTH.search(_flat) and not NORTH_TAGS & set(e.get("tags", [])):
        errors.append(f"events_random.json:{e.get('id')}: северные реалии без тега северной главы (ch3+)")
    if e.get("kind") != "random":
        errors.append(f"events_random.json:{e.get('id')}: kind должен быть random")
    bad = set(e.get("tags", [])) - TAGS
    if not e.get("tags") or bad:
        errors.append(f"events_random.json:{e.get('id')}: теги {e.get('tags')} (лишние {bad})")

# --- квесты
for q in quests:
    qw = f"quests.json:{q.get('id')}"
    steps = q.get("steps", [])
    min_steps = 2 if q.get("kind") == "folklore" else 3  # фольклорная линия: ≥ 1 задание + финал (п. 24)
    if len(steps) < min_steps:
        errors.append(f"{qw}: шагов {len(steps)}, нужно ≥ {min_steps}")
    prev = -1
    for s in steps:
        if not isinstance(s.get("at_km"), (int, float)) or s["at_km"] <= prev:
            errors.append(f"{qw}/{s.get('id')}: at_km должен расти")
        prev = s.get("at_km", prev)
        if "event" in s:
            check_event(qw, s["event"])
        elif "branches" in s:
            br = s["branches"]
            if not br or br[-1].get("if") != {}:
                errors.append(f"{qw}/{s.get('id')}: последняя ветка должна быть запасной (if: {{}})")
            for b in br:
                for var, cond in b.get("if", {}).items():
                    if not re.fullmatch(r"(>=|<=|==|>|<)-?\d+", str(cond)):
                        errors.append(f"{qw}/{s.get('id')}: условие {var}: {cond!r}")
                check_event(qw, b.get("event", {}))
        else:
            errors.append(f"{qw}/{s.get('id')}: нужен event или branches")

# --- ссылки
for w, target in detour_ends:
    if target not in all_event_ids:
        errors.append(f"{w}: detour_end {target} не найден")
for w, f in flags_needed:
    if f not in flags_set:
        errors.append(f"{w}: требуется флаг {f}, но его нигде не ставят")

# --- зоны: пулы случайных событий и слова-маркеры
pool = {z: 0 for z in Z.ZONES}
pool_any = {z: 0 for z in Z.ZONES}
for e in randoms:
    z = e.get("zone")
    if z in pool:
        pool[z] += 1
        if "any" in e.get("tags", []):
            pool_any[z] += 1
for z in Z.ZONES:
    if pool[z] < ZONE_MIN[z]:
        (errors if STRICT else warns).append(f"зоны: случайных событий зоны {z} {pool[z]} < {ZONE_MIN[z]}")
    if pool_any[z] < ZONE_ANY_MIN:
        (errors if STRICT else warns).append(f"зоны: в зоне {z} событий с тегом any {pool_any[z]} < {ZONE_ANY_MIN} (пул может опустеть)")
zone_words = load_zone_words()
if zone_words:
    for w, e in zoned_events:
        z = e.get("zone")
        if z not in zone_words or (isinstance(e.get("zone_note"), str) and e["zone_note"].strip()):
            continue
        txt = event_texts(e)
        hits = sorted({m for m in zone_words[z] if re.search(r"(?<![а-яёa-z])" + re.escape(m), txt)})
        if hits:
            (errors if STRICT else warns).append(f"{w}: зона {z}, но в тексте маркеры {', '.join(hits)} "
                                                 f"(поправьте текст/зону или добавьте zone_note)")

# --- предметы и стартовый набор (balance.json ↔ items.json)
BI = B["items"]
ITEM_TYPES = {"food", "drink", "gear", "tool", "refill"}
MULTS = ("warmthDrainMult", "weatherWarmthMult", "waterDrainMult", "idleWarmthMult", "delayMult", "detourMult")
for it in items_list:
    iw = f"items.json:{it.get('id')}"
    if re.search(r"(?<![а-яё])(жёлт|желт|золот|янтар)", (it.get("name", "") + " " + it.get("desc", "")).lower()):
        errors.append(f"{iw}: жёлтый/золотой/янтарный в тексте предмета (заказ п. 5 — без жёлтого)")
    if it.get("id") not in BI:
        errors.append(f"{iw}: нет в balance.json → items")
    if not 2 <= len(it.get("name", "")) <= 40:
        errors.append(f"{iw}: name {len(it.get('name', ''))} знаков (2..40)")
    if not 10 <= len(it.get("desc", "")) <= 160:
        errors.append(f"{iw}: desc {len(it.get('desc', ''))} знаков (10..160)")
for k, v in BI.items():
    bw = f"balance.items.{k}"
    if k not in items:
        errors.append(f"{bw}: нет названия в items.json")
    t = v.get("type")
    if t not in ITEM_TYPES:
        errors.append(f"{bw}: type {t!r}")
    for m in MULTS:
        if m in v and not (isinstance(v[m], (int, float)) and 0 < v[m] <= 1):
            errors.append(f"{bw}: {m} = {v[m]!r}, нужно (0..1]")
    if "drainKmMult" in v:
        dk = v["drainKmMult"]
        if not isinstance(dk, dict) or any(x not in ("satiety", "water") or not 0 < y <= 1 for x, y in dk.items()):
            errors.append(f"{bw}: drainKmMult должен быть {{satiety|water: (0..1]}}")
    if "riskReduce" in v and not 0 < v["riskReduce"] < 1:
        errors.append(f"{bw}: riskReduce вне (0..1)")
    if "uses" in v and not (isinstance(v["uses"], int) and v["uses"] >= 1):
        errors.append(f"{bw}: uses должен быть целым ≥ 1")
    if "maxUses" in v and not (isinstance(v["maxUses"], int) and v["maxUses"] >= v.get("uses", 1)):
        errors.append(f"{bw}: maxUses < uses")
    if "rescueTo" in v and not (isinstance(v["rescueTo"], int) and 1 <= v["rescueTo"] <= B["stats"]["max"]):
        errors.append(f"{bw}: rescueTo вне 1..max")
    if "heat" in v and (t not in ("food", "drink") or not isinstance(v["heat"], int) or v["heat"] < 0):
        errors.append(f"{bw}: heat — только у еды/питья, целое ≥ 0")
    if (any(x in v for x in MULTS + ("drainKmMult", "riskReduce", "rescueTo", "stove", "cond", "camp", "foodBoost",
                                      "upkeep", "expiresDays", "rescueStats")) and t != "gear"):
        errors.append(f"{bw}: перки снаряжения у предмета типа {t}")
    if "uses" in v and t not in ("gear", "tool"):
        errors.append(f"{bw}: uses — только у снаряжения и инструментов")
    if "uses" in v and t == "tool" and not v.get("ability"):
        errors.append(f"{bw}: заряды у инструмента без способности ability")
    if "cond" in v:
        c = v["cond"]
        perks = [k for k in c if k != "any"]
        if (not isinstance(c.get("any"), list) or not c["any"] or any(x not in ("midday", "heat", "water") for x in c["any"])
                or not perks or any(k not in ("waterDrainMult", "drainKmMult", "riskReduce", "noCoinLoss") for k in perks)):
            errors.append(f"{bw}: cond {{any: [midday|heat|water], waterDrainMult|drainKmMult|riskReduce|noCoinLoss}}")
        if "waterDrainMult" in c and not 0 < c["waterDrainMult"] <= 1 or "riskReduce" in c and not 0 < c["riskReduce"] < 1:
            errors.append(f"{bw}: cond — множители вне (0..1]")
    if "camp" in v and (not isinstance(v["camp"], dict) or not any(isinstance(v["camp"].get(s), int) and v["camp"][s] > 0 for s in STATS)):
        errors.append(f"{bw}: camp {{satiety|water|warmth: целое > 0, waterPlace?, cooldownDays?}}")
    if "foodBoost" in v and (not isinstance(v["foodBoost"].get("tag"), str)
                             or not any(s in v["foodBoost"] and v["foodBoost"][s] > 1 for s in STATS)):
        errors.append(f"{bw}: foodBoost {{tag, stat: множитель > 1}}")
    if "upkeep" in v and (not isinstance(v["upkeep"], list) or any(BI.get(x, {}).get("type") != "food" for x in v["upkeep"])):
        errors.append(f"{bw}: upkeep — список еды")
    if "expiresDays" in v and not (isinstance(v["expiresDays"], int) and v["expiresDays"] >= 1):
        errors.append(f"{bw}: expiresDays — целое ≥ 1")
    if "sellPrice" in v and not (isinstance(v["sellPrice"], int) and v["sellPrice"] > 0):
        errors.append(f"{bw}: sellPrice — целое > 0")
    if "rescueStats" in v and (not v.get("rescueTo") or any(s not in STATS for s in v["rescueStats"])):
        errors.append(f"{bw}: rescueStats — подмножество показателей, нужен rescueTo")
    if "tags" in v and not (isinstance(v["tags"], list) and all(isinstance(x, str) for x in v["tags"])):
        errors.append(f"{bw}: tags — список строк")
    if "hint" in v:
        h = v["hint"]
        if (not isinstance(h, dict) or not isinstance(h.get("cooldownDays"), int) or h["cooldownDays"] < 1
                or not (h.get("art") or h.get("zone")) or any(a not in ARTS for a in h.get("art", []))
                or any(z not in Z.ZONES for z in h.get("zone", []))):
            errors.append(f"{bw}: hint {{cooldownDays ≥ 1, art: [{'|'.join(sorted(ARTS))}] и/или zone}}")
    if "portions" in v and (t not in ("food", "drink") or not isinstance(v["portions"], int) or v["portions"] < 1):
        errors.append(f"{bw}: portions — только у еды/питья, целое ≥ 1")
    if "ability" in v:
        ab = v["ability"]
        if (not isinstance(ab, dict) or not isinstance(ab.get("kind"), str) or not isinstance(ab.get("cooldownDays"), int)
                or ab["cooldownDays"] < 0 or (ab["cooldownDays"] == 0 and "uses" not in v)):
            errors.append(f"{bw}: ability должен быть {{kind, cooldownDays: целое ≥ 1 (0 — только у предмета с uses)}}")
        elif ab["kind"] not in ("clew", "guide", "mirage", "action"):
            errors.append(f"{bw}: ability.kind {ab['kind']!r} движок не знает (clew, guide, mirage, action)")
        elif ab["kind"] == "action":
            eff = ab.get("effect") or {}
            if (ab.get("at", "any") not in ("any", "place") or any(z not in Z.ZONES for z in ab.get("zones", []))
                    or not eff or any(k not in STATS + ("warmthToMax", "give") for k in eff)
                    or any(i not in BI for i in (eff.get("give") or {}))):
                errors.append(f"{bw}: ability action {{at: any|place, zones?, water?, effect: {{stat: n | warmthToMax | give}}}}")
            if ab.get("water") and ab.get("at") != "place":
                errors.append(f"{bw}: ability.water — только при at: place (места из gifts.waterPlaces)")
        elif any(k in ab for k in ("effect", "at", "zones", "water")):
            errors.append(f"{bw}: effect/at/zones/water — только у ability action")
    if "region" in v and not isinstance(v["region"], str):
        errors.append(f"{bw}: region должен быть строкой")
    if t == "refill":
        tgt = BI.get(v.get("refill"), {})
        if tgt.get("type") != "gear" or "uses" not in tgt:
            errors.append(f"{bw}: refill → {v.get('refill')!r} должен быть снаряжением с uses")
        if not isinstance(v.get("amount"), int) or v["amount"] < 1:
            errors.append(f"{bw}: amount должен быть целым ≥ 1")
    if v.get("starter") and (t not in ("gear", "food", "drink") or v.get("price", 0) <= 0):
        errors.append(f"{bw}: starter — только снаряжение/еда с ценой > 0")
for mk, m in B["economy"]["markets"].items():
    if mk.startswith("_"):
        continue
    if mk == "regional":
        for pid, lst in (m or {}).items():
            if pid not in places:
                errors.append(f"balance.economy.markets.regional: нет места {pid}")
            for i in lst:
                if i not in BI:
                    errors.append(f"balance.economy.markets.regional.{pid}: нет предмета {i}")
        continue
    for i in m["items"]:
        if i not in BI:
            errors.append(f"balance.economy.markets.{mk}: нет предмета {i}")
G = B.get("gifts", {})
for pid in G.get("waterPlaces", []):
    if pid not in places:
        errors.append(f"balance.gifts.waterPlaces: нет места {pid}")
if any(a not in ARTS for a in G.get("waterArts", [])):
    errors.append("balance.gifts.waterArts: неизвестный art")
mh = G.get("middayHours")
if mh is not None and not (isinstance(mh, list) and len(mh) == 2 and 0 <= mh[0] < mh[1] <= 24):
    errors.append("balance.gifts.middayHours — [from, to), 0 ≤ from < to ≤ 24")
if "idleWarmthMin" in G and not 0 <= G["idleWarmthMin"] <= 1:
    errors.append("balance.gifts.idleWarmthMin вне [0..1]")
# дары духов из folklore-gifts.md должны быть заведены
gifts_doc = ROOT / "docs" / "v5" / "folklore-gifts.md"
if gifts_doc.exists():
    for gid in sorted(set(re.findall(r"^\| `([a-z_]+)` \|", gifts_doc.read_text(encoding="utf-8"), re.M))):
        if gid not in BI:
            errors.append(f"folklore-gifts.md: дар {gid} не заведён в balance.json → items")
# каталог в коридоре 50–60 (заказ, Дополнение A, п. 27)
if STRICT and not 50 <= len(BI) <= 60:
    errors.append(f"каталог: предметов {len(BI)}, нужно 50–60")
LO = B.get("loadout", {})
if not LO:
    errors.append("balance.json: нет раздела loadout")
else:
    dg, dp = LO["default"]["gear"], LO["default"]["pack"]
    if len(dg) > LO["maxGear"] or len(set(dg)) != len(dg) or any(not BI.get(g, {}).get("starter") or BI[g]["type"] != "gear" for g in dg):
        errors.append(f"loadout.default.gear {dg} нарушает правила старта")
    if (sum(dp.values()) > LO["maxPackSlots"] or any(n > LO["maxPerKind"] or n < 1 for n in dp.values())
            or any(not BI.get(k, {}).get("starter") or BI[k]["type"] not in ("food", "drink") for k in dp)):
        errors.append(f"loadout.default.pack {dp} нарушает правила старта")
    if LO["maxGear"] > B["economy"]["gearSlots"] or LO["maxPackSlots"] > B["economy"]["backpackSlots"]:
        errors.append("loadout: стартовый набор больше вместимости")

# --- утренние мысли
thoughts = load("thoughts.json", [])
days = set()
for t in thoughts:
    tw = f"thoughts.json:{t.get('id')}"
    for fld in ("quote", "author", "source", "license", "text"):
        if not t.get(fld):
            errors.append(f"{tw}: нет поля {fld}")
    words = len(t.get("text", "").split())
    if not 90 <= words <= 220:
        (errors if STRICT else warns).append(f"{tw}: {words} слов (100–200)")
    if t.get("ending") not in ("open", "closed"):
        errors.append(f"{tw}: ending {t.get('ending')!r}")
    if t.get("ending") == "open" and not t.get("question"):
        errors.append(f"{tw}: открытая мысль без вопроса")
    for ph in re.findall(r"\{(\w+)\}", t.get("text", "")):
        if ph not in ("place", "chapter", "km_left", "weather"):
            errors.append(f"{tw}: неизвестная подстановка {{{ph}}}")
    if t.get("day") in days:
        errors.append(f"{tw}: повтор дня {t.get('day')}")
    days.add(t.get("day"))
if thoughts:
    opened = sum(t.get("ending") == "open" for t in thoughts)
    if opened * 3 < len(thoughts):
        errors.append(f"thoughts.json: открытых {opened} из {len(thoughts)}, нужно ≥ трети")

# --- объём MVP
stats = {
    "авторских событий гл.1": sum(e.get("chapter") == 1 for e in anchored),
    "авторских событий гл.2": sum(e.get("chapter") == 2 for e in anchored),
    "случайных событий": len(randoms),
    "встреч с существами": sum(1 for e in list(anchored) + randoms if e.get("creature")),
    "квестов": len(quests),
    "утренних мыслей": len(thoughts),
    "пулы зон": "/".join(f"{z} {pool[z]} (any {pool_any[z]})" for z in Z.ZONES),
}
if STRICT:
    need = {"авторских событий гл.1": 12, "авторских событий гл.2": 16, "случайных событий": 16,
            "встреч с существами": 6, "квестов": 3, "утренних мыслей": 30}
    for k, n in need.items():
        if stats[k] < n:
            errors.append(f"объём: {k} {stats[k]} < {n}")
    total = stats["авторских событий гл.1"] + stats["авторских событий гл.2"] + stats["случайных событий"]
    if total < 40:
        errors.append(f"объём: событий всего {total} < 40")

for w in warns:
    print("предупреждение:", w)
for e in errors:
    print("ОШИБКА:", e)
print("; ".join(f"{k}: {v}" for k, v in stats.items()))
if errors:
    sys.exit(1)
print("content ok")

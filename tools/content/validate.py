"""Валидатор контента «Путника» (docs/v5/02-content-schema.md).

Запуск из корня репозитория: python3 tools/content/validate.py [--strict]
--strict требует полный объём MVP (число событий, мыслей, квестов).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
items = {i["id"] for i in load("items.json")}
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
TAGS = {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "forest", "road", "village", "water", "night", "rain",
        "field", "town", "swamp", "any", "risk"}
all_event_ids = {}
flags_set, flags_needed = set(), []
detour_ends = []


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
randoms = load("events_random.json", [])
for e in randoms:
    check_event("events_random.json", e)
    if e.get("kind") != "random":
        errors.append(f"events_random.json:{e.get('id')}: kind должен быть random")
    bad = set(e.get("tags", [])) - TAGS
    if not e.get("tags") or bad:
        errors.append(f"events_random.json:{e.get('id')}: теги {e.get('tags')} (лишние {bad})")

# --- квесты
for q in quests:
    qw = f"quests.json:{q.get('id')}"
    steps = q.get("steps", [])
    if len(steps) < 3:
        errors.append(f"{qw}: шагов {len(steps)}, нужно ≥ 3")
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

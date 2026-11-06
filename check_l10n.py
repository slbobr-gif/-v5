"""Проверка локализации: одинаковые ключи в трёх .arb, совпадающие плейсхолдеры,
и ни одной пользовательской строки, зашитой в код.

Запуск из корня репозитория: python3 tools/check_l10n.py
"""
import json
import re
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "app" / "lib"
LOCALES = sorted(p.stem.split("_", 1)[1] for p in (LIB / "l10n").glob("app_*.arb"))
LOCALES = ["ru"] + [x for x in LOCALES if x != "ru"]
errors = []

arbs = {}
for loc in LOCALES:
    arbs[loc] = json.loads((LIB / "l10n" / f"app_{loc}.arb").read_text(encoding="utf-8"))
keys = {loc: {k for k in a if not k.startswith("@")} for loc, a in arbs.items()}
base = keys["ru"]
for loc in LOCALES[1:]:
    for k in sorted(base - keys[loc]):
        errors.append(f"app_{loc}.arb: нет ключа {k}")
    for k in sorted(keys[loc] - base):
        errors.append(f"app_{loc}.arb: лишний ключ {k}")


def placeholders(text: str) -> set:
    # имена в {name} и {name, plural, ...}; внутри plural-веток — только вложенные {name}
    return set(re.findall(r"\{(\w+)(?:,|\})", text))


for k in sorted(base):
    ref = placeholders(arbs["ru"][k])
    for loc in LOCALES[1:]:
        if k in keys[loc] and placeholders(arbs[loc][k]) != ref:
            errors.append(f"{k}: плейсхолдеры {loc} {sorted(placeholders(arbs[loc][k]))} ≠ ru {sorted(ref)}")
    meta = arbs["ru"].get("@" + k, {}).get("placeholders", {})
    if ref - {"plural"} != set(meta) and (ref or meta):
        # plural/select — ключевые слова ICU, не плейсхолдеры
        declared = set(meta)
        found = ref - {"plural", "select"}
        if found != declared:
            errors.append(f"{k}: в тексте {sorted(found)}, в @{k} объявлены {sorted(declared)}")

# Пользовательские строки в коде. Каталоги l10n/ и demo/ (контент) исключены.
cyr = re.compile(r"[А-Яа-яЁё一-鿿]")
lit = re.compile(r"""\b(?:Text|SnackBar|Tooltip)\(\s*(?:const\s+)?['"]([^'"$]*[A-Za-zА-Яа-я][^'"$]*)['"]""")
for f in sorted(LIB.rglob("*.dart")):
    rel = f.relative_to(LIB).as_posix()
    if rel.startswith(("l10n/",)):
        continue
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("//")[0]
        if cyr.search(code):
            errors.append(f"{rel}:{n}: кириллица/иероглифы в коде")
        m = lit.search(code)
        if m:
            errors.append(f"{rel}:{n}: строка в коде: {m.group(1)!r}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"l10n ok: {len(base)} ключей × {len(LOCALES)} яз., зашитых строк нет")

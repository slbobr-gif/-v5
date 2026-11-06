"""Проверка слоёв: движок (lib/engine) — чистый Dart без Flutter и без других слоёв;
экраны (lib/ui) не ходят в хранилище и платформу напрямую — только через lib/app.

Запуск из корня репозитория: python3 tools/check_layers.py
"""
import re
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "app" / "lib"
imp = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.M)
errors = []
for f in sorted(LIB.rglob("*.dart")):
    rel = f.relative_to(LIB).as_posix()
    if rel.startswith("l10n/"):
        continue
    for target in imp.findall(f.read_text(encoding="utf-8")):
        if rel.startswith("engine/"):
            if not (target.startswith("dart:") and target != "dart:ui") and "/" in target or target.startswith("package:"):
                if target.startswith("package:") or target.startswith("../"):
                    errors.append(f"{rel}: движок импортирует {target}")
        if rel.startswith("ui/") and any(x in target for x in ("shared_preferences", "/platform/", "/data/storage", "appmetrica")):
            errors.append(f"{rel}: экран обращается к {target} напрямую")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("layers ok: движок — чистый Dart, экраны работают через lib/app")

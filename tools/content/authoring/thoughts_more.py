"""Утренние мысли 31–365 (V5-66): дописывает thoughts.json до 365.

Каждая мысль — собственное переложение стоика (Сенека, Марк Аврелий, Эпиктет, Музоний Руф; оригиналы —
общественное достояние) и запись Сергея в тетради, 70–220 слов. Мысль с вопросом читателю — открытая.
Части лежат в thoughts_pNN.py (список ITEMS из T(...)). Запуск: python3 tools/content/authoring/thoughts_more.py
"""

import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PATH = os.path.join(ROOT, "app", "assets", "content", "thoughts.json")
LICENSE = "собственное переложение; оригинал — общественное достояние"
PARTS = [f"thoughts_p{i:02d}" for i in range(1, 13)]


def main():
    base = [t for t in json.load(open(PATH, encoding="utf-8")) if t["day"] <= 30]
    items = []
    for name in PARTS:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        items += mod.ITEMS
    out = list(base)
    for i, (author, source, quote, text, question) in enumerate(items):
        day = 31 + i
        t = {"id": f"t{day:03d}" if day >= 100 else f"t{day:02d}", "day": day, "quote": quote, "author": author,
             "source": source, "license": LICENSE, "text": text.strip(), "ending": "open" if question else "closed"}
        if question:
            t["question"] = question
        out.append(t)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    short = [(t["id"], len(t["text"].split())) for t in out if not 70 <= len(t["text"].split()) <= 220]
    opened = sum(t["ending"] == "open" for t in out)
    print(f"мыслей: {len(out)}, открытых: {opened}, вне 70–220 слов: {short}")


if __name__ == "__main__":
    main()

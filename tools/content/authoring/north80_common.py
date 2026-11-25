"""25.11: общие помощники для 80 северных случайных событий (north80_ch3..ch6.py).

Событие — только своей главы (тег chN, без any). Запуск всех частей: python3 tools/content/authoring/north80_all.py
"""


def ev(id_, zone, ch, art, title, text, choices, extra_tags=(), when=None):
    e = {"id": id_, "kind": "random", "zone": zone, "tags": [f"ch{ch}", *extra_tags], "once": False, "art": art,
         "creature": None, "title": title, "text": text, "choices": choices}
    if when:
        e["whenHas"] = when
    return e


def c(id_, text, risk, *outs, req=None):
    ch = {"id": id_, "text": text, "risk": risk,
          "outcomes": [{"weight": w, "text": t, "effects": e} for w, t, e in outs]}
    if req:
        ch["requires"] = req
    return ch


def go(text="Пройти мимо", out="Сергей идёт дальше своей дорогой."):
    """Нейтральный вариант «пройти мимо»."""
    if len(out) < 40:
        out = out.rstrip(".") + ". Дорога ведёт дальше, на север."
    return c("go", text, "none", (1, out, {}))

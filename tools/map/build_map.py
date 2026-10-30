"""Строит app/assets/map/map.json — линию маршрута и слои карты.

Онлайн (в GitHub Actions):  python3 tools/map/build_map.py --online
  * линия маршрута — OSRM (данные © участники OpenStreetMap, ODbL) через точки places.json;
  * море, озёра, реки, границы — Natural Earth 1:10m (общественное достояние).
Офлайн (резерв):            python3 tools/map/build_map.py
  * упрощённые контуры из tools/map/fallback_geo.json и прямые между точками × 1,12.
Если онлайн-шаг упал, остаётся предыдущий map.json — сборка не ломается.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLACES = ROOT / "app" / "assets" / "content" / "places.json"
OUT = ROOT / "app" / "assets" / "map" / "map.json"
FALLBACK = Path(__file__).with_name("fallback_geo.json")
BBOX = (28.5, 54.8, 41.5, 70.3)  # minLon, minLat, maxLon, maxLat
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
OSRM = "https://router.project-osrm.org/route/v1/driving/{}?overview=full&geometries=geojson&steps=false"
UA = {"User-Agent": "putnik-map-builder/1.0 (test build; contact via repository)"}


# ---------------------------------------------------------------- геометрия
def hav(a, b) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dl = math.radians(b[0] - a[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def simplify(pts, tol):
    """Дуглас — Пекер (итеративный)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        best, idx = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            if L == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
                d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > best:
                best, idx = d, k
        if idx >= 0 and best > tol * tol:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [p for p, k in zip(pts, keep) if k]


def clip_polygon(ring, bbox):
    """Сазерленд — Ходжман по прямоугольнику."""
    minx, miny, maxx, maxy = bbox
    edges = [
        (lambda p: p[0] >= minx, lambda a, b: _ix(a, b, x=minx)),
        (lambda p: p[0] <= maxx, lambda a, b: _ix(a, b, x=maxx)),
        (lambda p: p[1] >= miny, lambda a, b: _ix(a, b, y=miny)),
        (lambda p: p[1] <= maxy, lambda a, b: _ix(a, b, y=maxy)),
    ]
    out = ring
    for inside, inter in edges:
        if not out:
            break
        inp, out = out, []
        prev = inp[-1]
        for cur in inp:
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
            prev = cur
    return out


def _ix(a, b, x=None, y=None):
    if x is not None:
        t = (x - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0
        return [x, a[1] + t * (b[1] - a[1])]
    t = (y - a[1]) / (b[1] - a[1]) if b[1] != a[1] else 0
    return [a[0] + t * (b[0] - a[0]), y]


def clip_line(line, bbox):
    minx, miny, maxx, maxy = bbox
    parts, cur = [], []
    for p in line:
        if minx <= p[0] <= maxx and miny <= p[1] <= maxy:
            cur.append(p)
        elif cur:
            parts.append(cur)
            cur = []
    if cur:
        parts.append(cur)
    return [c for c in parts if len(c) >= 2]


def rnd(pts, nd=3):
    return [[round(x, nd), round(y, nd)] for x, y in pts]


# ---------------------------------------------------------------- источники
def fetch_json(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ne_layer(name, kind, tol, min_area=0.0):
    data = fetch_json(NE.format(name), timeout=300)
    out = []
    for f in data["features"]:
        g = f.get("geometry") or {}
        t, coords = g.get("type"), g.get("coordinates")
        if kind == "poly":
            polys = coords if t == "MultiPolygon" else [coords] if t == "Polygon" else []
            for poly in polys:
                ring = clip_polygon([list(p[:2]) for p in poly[0]], BBOX)
                if len(ring) >= 4 and _area(ring) >= min_area:
                    out.append(rnd(simplify(ring, tol)))
        else:
            lines = coords if t == "MultiLineString" else [coords] if t == "LineString" else []
            for ln in lines:
                for part in clip_line([list(p[:2]) for p in ln], BBOX):
                    s = simplify(part, tol)
                    if len(s) >= 2:
                        out.append(rnd(s))
    return out


def _area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))) / 2


def osrm_route(places):
    coords = ";".join(f"{p['lon']},{p['lat']}" for p in places)
    data = fetch_json(OSRM.format(coords), timeout=180)
    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM: {data.get('code')} {data.get('message')}")
    r = data["routes"][0]
    line = [list(p) for p in r["geometry"]["coordinates"]]
    legs = [leg["distance"] for leg in r["legs"]]
    return line, legs


# ---------------------------------------------------------------- сборка
def build(online: bool) -> dict:
    places = json.loads(PLACES.read_text(encoding="utf-8"))
    if online:
        line, legs = osrm_route(places)
        dist = {places[0]["id"]: 0.0}
        acc = 0.0
        for p, d in zip(places[1:], legs):
            acc += d
            dist[p["id"]] = round(acc, 1)
        length = acc
        layers = {
            # Суша, а не океан: в ne_10m_ocean материки — «дыры» внутри мирового полигона,
            # а у суши внешний контур — это береговая линия. Приложение рисует фон морем, сушу поверх.
            "land": ne_layer("ne_10m_land", "poly", 0.015, min_area=0.002),
            "lakes": ne_layer("ne_10m_lakes", "poly", 0.01, min_area=0.004),
            "rivers": ne_layer("ne_10m_rivers_lake_centerlines", "line", 0.01),
            "borders": ne_layer("ne_10m_admin_0_boundary_lines_land", "line", 0.02),
        }
        route = rnd(simplify(line, 0.004), 4)
        source = "OpenStreetMap (OSRM) + Natural Earth"
    else:
        fb = json.loads(FALLBACK.read_text(encoding="utf-8"))
        route = [[p["lon"], p["lat"]] for p in places]
        scale = 1.12  # прямые короче дорог
        dist, acc = {places[0]["id"]: 0.0}, 0.0
        for a, b in zip(places, places[1:]):
            acc += hav([a["lon"], a["lat"]], [b["lon"], b["lat"]]) * scale
            dist[b["id"]] = round(acc, 1)
        length = acc
        layers = {k: fb[k] for k in ("sea", "lakes", "rivers", "borders")}  # резерв: фон — суша, море поверх
        source = "fallback"
    # монотонность (на всякий случай)
    prev = -1.0
    for p in places:
        if dist[p["id"]] <= prev:
            dist[p["id"]] = prev + 1.0
        prev = dist[p["id"]]
    return {
        "version": 1,
        "source": source,
        "attribution": "© участники OpenStreetMap; Natural Earth" if online else "упрощённая карта",
        "bbox": list(BBOX),
        "route": route,
        "routeLengthM": round(length, 1),
        "placeDistances": dist,
        "layers": layers,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true")
    args = ap.parse_args()
    try:
        data = build(args.online)
    except Exception as e:  # noqa: BLE001
        print(f"карта: онлайн-сборка не удалась ({e}); оставляю текущий map.json", file=sys.stderr)
        if OUT.exists():
            return 0
        data = build(False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = sum(len(v) for v in data["layers"].values())
    print(f"карта: {data['source']}, маршрут {data['routeLengthM']/1000:.0f} км, {len(data['route'])} точек линии, "
          f"{n} объектов, {OUT.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())

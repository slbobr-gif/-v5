"""Зоны пути: city / suburb / wild.

Единый источник правды — app/assets/balance.json → "zones" и app/assets/map/map.json → placeDistances.
Правило (то же, что World.zone_at в tools/sim/engine.py и в Dart): зона точки пути = самая «городская»
из зон всех мест, в радиус которых она попадает; места — из places.json ПЛЮС виртуальные придорожные
точки (kind "roadside", balance.roadside — в отрезках длиннее maxGapKm), радиусы — zones.byKind[kind]:
  city   — расстояние вдоль маршрута до места ≤ urban
  suburb — ≤ urban + suburb
  wild   — всё остальное: леса, поля, пустоши, дорога между селениями
Вид места без записи в byKind (например, landmark) на зону не влияет; радиус 0 — такой зоны у места нет.
Внутри всё считается в метрах, как в движке, чтобы на границах валидатор и игра совпадали.

Использование:  python3 tools/content/zones.py          — профиль зон по главам
                from zones import zone_at, ZONES        — в других скриптах (km — км от Кремля)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'app' / 'assets'
ZONES = ('city', 'suburb', 'wild')
_RANK = {'city': 2, 'suburb': 1, 'wild': 0}
_BAL = json.loads((ROOT / 'balance.json').read_text(encoding='utf-8'))
_B = _BAL['zones']
_PLACES = json.loads((ROOT / 'content' / 'places.json').read_text(encoding='utf-8'))
_DIST = {k: float(v) for k, v in json.loads((ROOT / 'map' / 'map.json').read_text(encoding='utf-8'))['placeDistances'].items()}
LABELS = _B['labels']


def _roadside_points():
    """Придорожные точки — та же формула, что World._add_roadside в движке."""
    gap_max = _BAL['roadside']['maxGapKm'] * 1000.0
    ordered = sorted((p for p in _PLACES if p['id'] in _DIST), key=lambda p: _DIST[p['id']])
    out = []
    for a, b in zip(ordered, ordered[1:]):
        pa, pb = _DIST[a['id']], _DIST[b['id']]
        n = int((pb - pa) // gap_max)
        for i in range(1, n + 1):
            out.append(pa + (pb - pa) * i / (n + 1))
    return out


def _build_points():
    pts = []
    for p in _PLACES:
        r = _B['byKind'].get(p['kind'])
        if r is None or p['id'] not in _DIST:
            continue
        pts.append((_DIST[p['id']], r['urban'] * 1000.0, (r['urban'] + r['suburb']) * 1000.0))
    r = _B['byKind'].get('roadside')
    if r is not None:
        for pos in _roadside_points():
            pts.append((pos, r['urban'] * 1000.0, (r['urban'] + r['suburb']) * 1000.0))
    return pts


_POINTS = _build_points()
ROADSIDE_KM = [round(p / 1000.0, 2) for p in _roadside_points()]


def zone_at_m(pos_m: float) -> str:
    best = 'wild'
    for ppos, urban, outer in _POINTS:
        d = abs(pos_m - ppos)
        z = 'city' if urban > 0 and d <= urban else 'suburb' if outer > 0 and d <= outer else 'wild'
        if _RANK[z] > _RANK[best]:
            best = z
    return best


def zone_at(km: float) -> str:
    return zone_at_m(km * 1000.0)


def anchor_pos_m(a: dict) -> float:
    """anchor {"after": place_id, "km": x} → метры от Кремля (как в движке: placeDistances[after] + km·1000)"""
    return _DIST[a['after']] + a['km'] * 1000.0


def anchor_km(a: dict) -> float:
    """anchor {"after": place_id, "km": x} → км от Кремля"""
    return anchor_pos_m(a) / 1000.0


def anchor_zone(a: dict) -> str:
    return zone_at_m(anchor_pos_m(a))


def profile(km0: float, km1: float, step: float = 0.25) -> dict:
    out = {z: 0.0 for z in ZONES}
    k = km0
    while k < km1:
        out[zone_at(k)] += step
        k += step
    return out


def segments(km0: float, km1: float, step: float = 0.25):
    """[(от, до, зона)] — для карт и отчётов"""
    res, k, cur, start = [], km0, None, km0
    while k < km1:
        z = zone_at(k)
        if z != cur:
            if cur is not None:
                res.append((round(start, 2), round(k, 2), cur))
            cur, start = z, k
        k += step
    res.append((round(start, 2), round(km1, 2), cur))
    return res


if __name__ == '__main__':
    chs = json.loads((ROOT / 'content' / 'chapters.json').read_text(encoding='utf-8'))
    for c in chs:
        a, b = _DIST[c['from']] / 1000.0, _DIST[c['to']] / 1000.0
        pr = profile(a, b)
        tot = sum(pr.values())
        print(f"Глава {c['id']} {c['title']}: {a:.0f}–{b:.0f} км · " +
              ' · '.join(f"{LABELS[z]} {pr[z]:.0f} км ({100 * pr[z] / tot:.0f}%)" for z in ZONES))
    print('Придорожные точки, км:', ROADSIDE_KM)
    print('Первые 60 км:', segments(0, 60))

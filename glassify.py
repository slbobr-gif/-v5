"""Конвертер «фреска из стекла» (витраж), v5.3.

Берёт «сырой» SVG-рисунок (tools/art/raw/*.svg), растрирует его через Chromium,
режет на осколки, привязанные к границам форм (SLIC-суперпиксели → иерархическое
слияние по Уорду → планарная карта с общими рёбрами), красит каждый осколок
ювелирным стеклом (палитра витража, радиальный градиент «светлее к краю»),
рисует свинцовые контуры, раму, заднюю подсветку и блики.

Выход — SVG только из path/rect/circle/g/linearGradient/radialGradient/stop/defs,
без clipPath/filter/mask/use/style, ≤ 25 КБ.

Запуск отдельно: python3 tools/art/glassify.py [имя ...]   (читает tools/art/raw)
Обычно — через build.py --glass.
"""
import base64
import heapq
import io
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RAW = os.path.join(HERE, 'raw')
ART = os.path.join(ROOT, 'app', 'assets', 'art')

LEAD = '#070B10'
MAX_BYTES = 25 * 1024 - 400

# ---- ювелирная палитра (документ 07, «Витражный стиль») ---------------------
JEWELS = dict(
    turquoise='#2BC4BA', blue='#1B4F8C', ultra='#2B3E9E', emerald='#1F9E6B',
    violet='#5B3FA0', coral='#C8454F', amber='#F0A24A', milk='#EDE6D2', night='#0B1424',
)


# =============================================================================
# 1. растеризация
# =============================================================================
def viewbox(svg):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    return int(m.group(1)), int(m.group(2))


ID_JS = r"""
() => {
  const svg = document.querySelector('svg');
  svg.style.shapeRendering = 'crispEdges';
  const defs = {};
  svg.querySelectorAll('linearGradient,radialGradient').forEach(g => {
    let mo = 1;
    g.querySelectorAll('stop').forEach(st => {
      const o = st.getAttribute('stop-opacity');
      mo = Math.min(mo, o === null ? 1 : parseFloat(o));
    });
    defs[g.id] = mo;
  });
  svg.querySelectorAll('g').forEach(g => { g.setAttribute('opacity', '1'); });
  const els = Array.from(svg.querySelectorAll('path,rect,circle,ellipse,polygon,polyline'));
  let k = 0;
  const info = [];
  for (const el of els) {
    if (el.closest('defs')) continue;
    const cs = getComputedStyle(el);
    let ok = cs.fill !== 'none';
    const op = parseFloat(cs.fillOpacity) * parseFloat(el.getAttribute('opacity') === null ? 1 : el.getAttribute('opacity'));
    if (ok && cs.fill.startsWith('url')) {
      const m = cs.fill.match(/#([^")]+)/);
      if (m && (defs[m[1]] === undefined ? 1 : defs[m[1]]) < MINSTOP) ok = false;
    }
    if (op < MINOP) ok = false;
    if (!ok) { el.style.display = 'none'; continue; }
    k += 1;
    el.setAttribute('fill', 'rgb(' + ((k >> 16) & 255) + ',' + ((k >> 8) & 255) + ',' + (k & 255) + ')');
    el.setAttribute('fill-opacity', '1');
    el.setAttribute('opacity', '1');
    el.setAttribute('stroke', 'none');
    el.style.stroke = 'none';
  }
  return k;
}
"""


STROKE_JS = r"""
() => {
  const svg = document.querySelector('svg');
  const out = [];
  const all = Array.from(svg.querySelectorAll('path,rect,circle,ellipse,polygon,polyline,line'));
  svg.querySelectorAll('path,polyline,line').forEach(el => {
    if (el.closest('defs')) return;
    const cs = getComputedStyle(el);
    if (cs.stroke === 'none' || cs.stroke.startsWith('url')) return;
    if (el.tagName !== 'line' && cs.fill !== 'none') return;
    let d;
    if (el.tagName === 'path') d = el.getAttribute('d');
    else if (el.tagName === 'polyline') {
      const p = el.getAttribute('points').trim().split(/[\s,]+/);
      d = 'M' + p[0] + ',' + p[1];
      for (let i = 2; i + 1 < p.length; i += 2) d += 'L' + p[i] + ',' + p[i + 1];
    } else d = 'M' + el.getAttribute('x1') + ',' + el.getAttribute('y1') + 'L' + el.getAttribute('x2') + ',' + el.getAttribute('y2');
    const oa = el.getAttribute('opacity');
    const op = parseFloat(cs.strokeOpacity) * (oa === null ? 1 : parseFloat(oa));
    let len = 0;
    try { len = el.getTotalLength(); } catch (e) { return; }
    if (len < 6) return;
    // видимость: не перекрыт ли путь более поздними непрозрачными формами
    let vis = 0, tot = 0;
    for (let k = 0; k < 7; k++) {
      let pt;
      try { pt = el.getPointAtLength(len * (k + 0.5) / 7); } catch (e) { continue; }
      if (pt.x < 0 || pt.y < 0) continue;
      const stack = document.elementsFromPoint(pt.x, pt.y);
      let ok = true;
      for (const e of stack) {
        if (e === el) break;
        const c2 = getComputedStyle(e);
        const o2 = e.getAttribute('opacity');
        const op2 = parseFloat(c2.fillOpacity) * (o2 === null ? 1 : parseFloat(o2));
        if (c2.fill !== 'none' && !c2.fill.startsWith('url') && op2 > 0.8) { ok = false; break; }
        if (c2.fill.startsWith('url') && op2 > 0.8) {
          const m = c2.fill.match(/#([^")]+)/);
          const g = m && svg.getElementById(m[1]);
          let mo = 1;
          if (g) g.querySelectorAll('stop').forEach(st => { const o = st.getAttribute('stop-opacity'); mo = Math.min(mo, o === null ? 1 : parseFloat(o)); });
          if (mo > 0.9) { ok = false; break; }
        }
      }
      tot++; if (ok) vis++;
    }
    if (tot === 0 || vis / tot < 0.6) return;
    out.push({d: d, stroke: cs.stroke, sw: parseFloat(cs.strokeWidth), op: op, len: len});
  });
  return out;
}
"""


def rasterize(svgs, scale, ids=False, min_stop=0.75, min_op=0.45):
    """dict имя -> svg  →  dict имя -> RGB uint8 (H*scale, W*scale, 3) [и карта id примитивов]."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, svg in svgs.items():
            w, h = viewbox(svg)
            pg = br.new_page(viewport={'width': w, 'height': h}, device_scale_factor=scale)
            b64 = base64.b64encode(svg.encode()).decode()
            pg.set_content('<html><body style="margin:0;background:#000">'
                           f'<img src="data:image/svg+xml;base64,{b64}" width="{w}" height="{h}" style="display:block"></body></html>')
            pg.wait_for_timeout(60)
            rgb = np.array(Image.open(io.BytesIO(pg.screenshot())).convert('RGB'))
            if not ids:
                pg.close()
                out[name] = rgb
                continue
            inline = re.sub(r'<svg ', f'<svg width="{w}" height="{h}" ', svg, count=1)
            pg.set_content(f'<html><body style="margin:0;background:#000">{inline}</body></html>')
            strokes = pg.evaluate(STROKE_JS)
            js = ID_JS.replace('MINSTOP', str(min_stop)).replace('MINOP', str(min_op))
            pg.evaluate(js)
            pg.wait_for_timeout(60)
            idm = np.array(Image.open(io.BytesIO(pg.screenshot())).convert('RGB')).astype(np.int64)
            pg.close()
            ids_ = (idm[..., 0] << 16) | (idm[..., 1] << 8) | idm[..., 2]
            out[name] = (rgb, ids_, strokes)
        br.close()
    return out


# =============================================================================
# 2. цвет
# =============================================================================
def srgb2lab(rgb):
    from skimage import color
    a = np.asarray(rgb, dtype=np.float64) / 255.0
    return color.rgb2lab(a.reshape(-1, 1, 3)).reshape(a.shape)


def lab2srgb(lab):
    from skimage import color
    a = np.asarray(lab, dtype=np.float64)
    rgb = color.lab2rgb(a.reshape(-1, 1, 3)).reshape(a.shape)
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return '#%02x%02x%02x' % tuple(int(v) for v in c)


def lab2lch(lab):
    L, a, b = lab
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def lch2lab(L, C, h):
    return np.array([L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))])


def lab_of_hex(h):
    return srgb2lab(np.array(hex2rgb(h), dtype=np.float64).reshape(1, 3))[0]


def in_gamut(L, C, h):
    """Уменьшаем насыщенность, пока цвет помещается в sRGB."""
    for _ in range(30):
        lab = lch2lab(L, C, h)
        from skimage import color
        rgb = color.lab2rgb(lab.reshape(1, 1, 3)).reshape(3)
        # lab2rgb клиппит; проверим точность обратным преобразованием
        back = color.rgb2lab(np.clip(rgb, 0, 1).reshape(1, 1, 3)).reshape(3)
        if np.linalg.norm(back - lab) < 2.5:
            return lab
        C *= 0.93
    return lch2lab(L, C, h)


# Рампа стекла: оттенки из документа × ступени яркости × насыщенность.
def build_ramp():
    ramp = []   # (name, lab, hex)
    jew_h = {
        'turquoise': 188, 'teal': 172, 'emerald': 155, 'blue': 255, 'ultra': 272,
        'violet': 300, 'rose': 350, 'coral': 22, 'amber': 68,
    }
    steps = [(12, 46), (20, 58), (29, 66), (40, 68), (53, 66), (68, 58), (82, 38)]
    for L, C in [(60, 74), (68, 78), (76, 68)]:
        ramp.append((f'amberx{L}', in_gamut(L, C, 66)))
    for name, h in jew_h.items():
        for L, C in steps:
            if name == 'amber':
                continue
            if name == 'coral' and L > 70:
                continue
            if name in ('emerald', 'teal', 'turquoise') and L > 75:
                C = C * 0.8
            if name in ('violet', 'ultra', 'blue') and L > 72:
                C = C * 0.8
            lab = in_gamut(L, C, h)
            ramp.append((f'{name}{L}', lab))
            if name in ('blue', 'turquoise') and L in (42, 55):       # дымчатое стекло — редко
                ramp.append((f'{name}{L}s', in_gamut(L, C * 0.55, h)))
    # молочное стекло и ночное
    for L, C, h in [(93, 9, 92), (84, 8, 92), (72, 7, 95), (60, 6, 100)]:
        ramp.append((f'milk{L}', in_gamut(L, C, h)))
    for L, C, h in [(7, 8, 258), (11, 12, 258), (17, 14, 262)]:
        ramp.append((f'night{L}', in_gamut(L, C, h)))
    # точные цвета из документа тоже в рампе
    for k, hx in JEWELS.items():
        ramp.append((f'doc_{k}', lab_of_hex(hx)))
    return ramp


_RAMP = None


def ramp():
    global _RAMP
    if _RAMP is None:
        r = build_ramp()
        _RAMP = (np.array([x[1] for x in r]), [x[0] for x in r])
    return _RAMP


def hue_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


HUE_ANCHORS = [  # куда подтягиваем исходные оттенки: (входной h, выходной h)
    (0, 355), (25, 22), (60, 68), (92, 96), (108, 142), (135, 152), (160, 160), (185, 188),
    (215, 235), (245, 258), (275, 275), (305, 300), (335, 350), (360, 355 + 360),
]


def warp_hue(h):
    for (a0, b0), (a1, b1) in zip(HUE_ANCHORS[:-1], HUE_ANCHORS[1:]):
        if a0 <= h <= a1:
            t = (h - a0) / (a1 - a0)
            return (b0 + (b1 - b0) * t) % 360
    return h


def wrap_dh(a, b):
    return (a - b + 180) % 360 - 180


def jewelize(lab, share, ctx):
    """Исходный Lab осколка → «ювелирный» Lab (градиентная карта по рангу яркости).

    ctx: cy — положение по вертикали (доля кадра); rank — ранг яркости области 0..1;
    rng; h0 — преобладающий исходный оттенок."""
    L, C, h = lab2lch(lab)
    rng = ctx['rng']
    cy = ctx['cy']
    rank = ctx['rank']
    Lp = ctx['lo'] + ctx['span'] * rank + ctx['top'] * max(0.0, (L - ctx['L90']) / max(1.0, 100.0 - ctx['L90']))
    Lp = min(96.0, max(8.0, Lp + ctx['dL'] + rng.uniform(-ctx['Ljit'], ctx['Ljit'])))
    if (C < 7 and L > 55) or (L > 72 and C < 28):             # молочное стекло (луна, пар, снег)
        return lch2lab(min(95, 72 + 0.25 * L), 9, 92)
    strong_warm = 22 <= h <= 98 and C > 20 and (L > 36 or share > 0.02)
    if strong_warm:
        if share > 0.012:                                     # большие тёплые плоскости: рубин / коралл
            return in_gamut(max(34, min(50, Lp + 2)), 54, rng.choice([8, 18, 28, 345]))
        return in_gamut(max(Lp, 74), 66, 66)                  # малые: янтарное стекло (окна, огонь)
    # --- градиентная карта: глубокая ночь → ультрамарин → синий → бирюза → молоко
    if Lp < 23:
        base = ctx['ground_h'] if cy > ctx['ground_y'] else 278
    elif Lp < 35:
        base = 272 - (Lp - 23) * 1.1
    elif Lp < 48:
        base = 259 - (Lp - 35) * 2.6
    elif Lp < 64:
        base = 225 - (Lp - 48) * 1.9
    else:
        base = 192
    dh = wrap_dh(h, ctx['h0']) * ctx['hue_gain'] * min(1.0, C / 18.0)
    dh = max(-55.0, min(55.0, dh))
    hue = (base + dh + rng.uniform(-ctx['jit'], ctx['jit'])) % 360
    if rng.rand() < ctx['alt_p'] and 24 < Lp < 66:             # редкие вкрапления другого стекла
        hue = rng.choice([296, 160, 270])
    if C > 26 and not (22 <= h <= 98):
        hue = warp_hue(h)
    Cn = 62 if 20 < Lp < 72 else 44
    Cn = Cn * (0.92 + 0.16 * min(1.0, C / 14.0)) + rng.uniform(-3, 3)
    return in_gamut(Lp, Cn, hue)


def snap_to_ramp(lab):
    lab_r, names = ramp()
    d = ((lab_r - lab) ** 2).sum(1)
    h = lab2lch(lab)[2]
    if not (50 <= h <= 85):                      # янтарь — только для настоящего тёплого света
        for k, nm in enumerate(names):
            if nm.startswith('amberx'):
                d[k] = 1e9
    i = int(np.argmin(d))
    return i, math.sqrt(d[i])


# =============================================================================
# 3. сегментация
# =============================================================================
def superpixels(rgb, n_init, compactness, mask=None):
    import cv2
    from skimage import segmentation
    sm = cv2.bilateralFilter(rgb, 7, 26, 7)
    sm = cv2.bilateralFilter(sm, 7, 26, 7)
    sp = segmentation.slic(sm, n_segments=n_init, compactness=compactness, sigma=0.8, start_label=0,
                           enforce_connectivity=True, min_size_factor=0.2, convert2lab=True,
                           mask=mask)
    return sp, sm


def ward_merge(sp, lab, n_target, lam, area_cap, valid=None, sal=None):
    """Иерархическое слияние соседних суперпикселей по Уорду (цвет + положение)."""
    H, W = sp.shape
    labels = sp.copy()
    if valid is not None:
        labels = np.where(valid, labels, -1)
    ids = np.unique(labels[labels >= 0])
    remap = -np.ones(labels.max() + 2, dtype=np.int64)
    remap[ids] = np.arange(len(ids))
    lbl = np.where(labels >= 0, remap[np.maximum(labels, 0)], -1)
    N = len(ids)
    flat = lbl.ravel()
    ok = flat >= 0
    ys, xs = np.mgrid[:H, :W]
    cnt = np.bincount(flat[ok], minlength=N).astype(np.float64)
    mu = np.stack([np.bincount(flat[ok], weights=lab[..., k].ravel()[ok], minlength=N) / cnt for k in range(3)], 1)
    cx = np.bincount(flat[ok], weights=xs.ravel()[ok], minlength=N) / cnt
    cy = np.bincount(flat[ok], weights=ys.ravel()[ok], minlength=N) / cnt
    wgt = cnt.copy()
    if sal is not None:
        s = np.bincount(flat[ok], weights=sal.ravel()[ok], minlength=N) / cnt
        wgt = cnt * (1 + s)
    # смежность
    pairs = set()
    for a, b in ((lbl[:, :-1], lbl[:, 1:]), (lbl[:-1, :], lbl[1:, :])):
        m = (a != b) & (a >= 0) & (b >= 0)
        aa, bb = a[m], b[m]
        lo, hi = np.minimum(aa, bb), np.maximum(aa, bb)
        for x, y in set(zip(lo.tolist(), hi.tolist())):
            pairs.add((x, y))
    feat = np.concatenate([mu, lam * cx[:, None], lam * cy[:, None]], 1)
    nodes = {}
    for i in range(N):
        nodes[i] = [cnt[i], wgt[i], feat[i].copy(), set()]
    for a, b in pairs:
        nodes[a][3].add(b)
        nodes[b][3].add(a)

    def cost(a, b):
        na, wa, fa, _ = nodes[a]
        nb, wb, fb, _ = nodes[b]
        if na + nb > area_cap:
            return None
        d = fa - fb
        return wa * wb / (wa + wb) * float(d @ d)

    heap = []
    for a, b in pairs:
        c = cost(a, b)
        if c is not None:
            heap.append((c, a, b))
    heapq.heapify(heap)
    parent = list(range(N))
    alive = N
    nxt = N
    while alive > n_target and heap:
        c, a, b = heapq.heappop(heap)
        if a not in nodes or b not in nodes:
            continue
        na, wa, fa, adja = nodes.pop(a)
        nb, wb, fb, adjb = nodes.pop(b)
        n = na + nb
        w = wa + wb
        f = (fa * wa + fb * wb) / w
        adj = (adja | adjb) - {a, b}
        m = nxt
        nxt += 1
        nodes[m] = [n, w, f, adj]
        parent.extend([m])
        parent[a] = m
        parent[b] = m
        for t in adj:
            nodes[t][3].discard(a)
            nodes[t][3].discard(b)
            nodes[t][3].add(m)
            cc = cost(m, t)
            if cc is not None:
                heapq.heappush(heap, (cc, m, t))
        alive -= 1
    # корни
    root = np.arange(len(parent))
    for i in range(len(parent) - 1, -1, -1):
        pass
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    final = np.array([find(i) for i in range(N)])
    uniq, inv = np.unique(final, return_inverse=True)
    out = np.where(lbl >= 0, inv[np.maximum(lbl, 0)], -1)
    return out.astype(np.int32), len(uniq)


def subdivide(lbl, n_total, rng, power=0.75, stretch=0.7):
    """Крупные формы делим на ячейки (k-means по координатам) — граненое стекло.

    Число ячеек растёт медленнее площади (power<1): большое небо остаётся крупными осколками.
    stretch<1 вытягивает ячейки по горизонтали."""
    from scipy.spatial import cKDTree
    from sklearn.cluster import KMeans
    from skimage import measure
    n = lbl.max() + 1
    cnt = np.bincount(lbl[lbl >= 0], minlength=n).astype(np.float64)

    def ks(a0):
        return [max(1, int(round((c / a0) ** power))) for c in cnt]

    lo, hi = 8.0, float(cnt.sum())
    for _ in range(50):
        mid = math.sqrt(lo * hi)
        if sum(ks(mid)) > n_total:
            lo = mid
        else:
            hi = mid
    kk = ks(hi)
    out = -np.ones_like(lbl)
    nxt = 0
    for i in range(n):
        ys, xs = np.nonzero(lbl == i)
        if len(ys) == 0:
            continue
        k = kk[i]
        if k == 1:
            out[ys, xs] = nxt
            nxt += 1
            continue
        pts = np.c_[xs * stretch, ys].astype(np.float64)
        sub = pts[rng.choice(len(pts), min(len(pts), 1500), replace=False)]
        km = KMeans(k, n_init=1, max_iter=3, random_state=int(rng.randint(1 << 30))).fit(sub)
        cl = cKDTree(km.cluster_centers_).query(pts)[1]
        out[ys, xs] = nxt + cl
        nxt += k
    cc = measure.label(out, background=-1, connectivity=1)
    return (cc - 1).astype(np.int32)


def absorb_small(lbl, min_area):
    """Склеиваем мелкие осколки с соседом по длиннейшей общей границе."""
    changed = True
    while changed:
        changed = False
        n = lbl.max() + 1
        cnt = np.bincount(lbl[lbl >= 0], minlength=n)
        small = [i for i in range(n) if 0 < cnt[i] < min_area]
        if not small:
            break
        for s in small:
            m = lbl == s
            dil = np.zeros_like(m)
            dil[1:, :] |= m[:-1, :]
            dil[:-1, :] |= m[1:, :]
            dil[:, 1:] |= m[:, :-1]
            dil[:, :-1] |= m[:, 1:]
            nb = lbl[dil & ~m]
            nb = nb[nb >= 0]
            if len(nb) == 0:
                continue
            t = np.bincount(nb).argmax()
            lbl[m] = t
            changed = True
    uniq = np.unique(lbl[lbl >= 0])
    remap = -np.ones(lbl.max() + 2, dtype=np.int64)
    remap[uniq] = np.arange(len(uniq))
    return np.where(lbl >= 0, remap[np.maximum(lbl, 0)], -1).astype(np.int32)


# =============================================================================
# 4. планарная карта: цепочки границ с общими вершинами
# =============================================================================
def planar_chains(lbl):
    """Возвращает список цепочек (left, right, pts[np.ndarray (n,2) x,y], closed)."""
    H, W = lbl.shape
    P = np.pad(lbl, 1, constant_values=-1)
    V = W + 1
    out = {}      # вершина -> список (сосед, left, right, crack_id)
    cracks = []   # (u, v)
    hm = P[:-1, 1:-1] != P[1:, 1:-1]
    ys, xs = np.nonzero(hm)
    for y, x in zip(ys.tolist(), xs.tolist()):
        u, v = y * V + x, y * V + x + 1
        L, R = int(P[y, x + 1]), int(P[y + 1, x + 1])
        c = len(cracks)
        cracks.append((u, v))
        out.setdefault(u, []).append((v, L, R, c))
        out.setdefault(v, []).append((u, R, L, c))
    vm = P[1:-1, :-1] != P[1:-1, 1:]
    ys, xs = np.nonzero(vm)
    for y, x in zip(ys.tolist(), xs.tolist()):
        u, v = y * V + x, (y + 1) * V + x
        L, R = int(P[y + 1, x + 1]), int(P[y + 1, x])
        c = len(cracks)
        cracks.append((u, v))
        out.setdefault(u, []).append((v, L, R, c))
        out.setdefault(v, []).append((u, R, L, c))
    used = [False] * len(cracks)
    chains = []

    def coord(v):
        return (v % V, v // V)

    def trace(start, first):
        w, L, R, c = first
        used[c] = True
        pts = [coord(start), coord(w)]
        cur = w
        while len(out[cur]) == 2 and cur != start:
            nxt = None
            for e in out[cur]:
                if e[3] != c:
                    nxt = e
            if nxt is None:
                break
            w2, L2, R2, c2 = nxt
            if used[c2]:
                break
            used[c2] = True
            c = c2
            cur = w2
            pts.append(coord(cur))
        return L, R, pts, (cur == start)

    for v, lst in out.items():
        if len(lst) >= 3:
            for e in lst:
                if not used[e[3]]:
                    L, R, pts, closed = trace(v, e)
                    chains.append((L, R, np.array(pts, dtype=np.float64), closed, v, None))
    for v, lst in out.items():     # замкнутые петли без развилок
        for e in lst:
            if not used[e[3]]:
                L, R, pts, closed = trace(v, e)
                chains.append((L, R, np.array(pts, dtype=np.float64), closed, v, None))
    return chains


def smooth_open(pts, it=1):
    p = pts.copy()
    if len(p) < 4:
        return p
    for _ in range(it):
        q = p.copy()
        q[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
        p = q
    return p


def dp(pts, tol):
    """Дуглас–Пекер для открытой ломаной; возвращает индексы."""
    n = len(pts)
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        seg = pts[i + 1:j] - a
        L = math.hypot(ab[0], ab[1])
        if L < 1e-9:
            d = np.hypot(seg[:, 0], seg[:, 1])
        else:
            d = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return np.nonzero(keep)[0]


def simplify_chain(pts, closed, tol):
    p = smooth_open(pts) if not closed else pts
    if closed:
        # замкнутая петля: разрезаем в самой дальней точке
        n = len(p) - 1
        d = np.hypot(*(p[:-1] - p[0]).T)
        k = int(np.argmax(d))
        a = p[:k + 1]
        b = p[k:]
        a = smooth_open(a)
        b = smooth_open(b)
        ia, ib = dp(a, tol), dp(b, tol)
        return np.vstack([a[ia], b[ib][1:]])
    idx = dp(p, tol)
    return p[idx]


def round_pts(p, q):
    return np.round(p / q) * q


def region_rings(chains, n_regions):
    """Для каждой области — кольца точек (последовательность цепочек, область слева)."""
    per = {}
    for ci, (L, R, pts, closed, v0, _) in enumerate(chains):
        if L >= 0:
            per.setdefault(L, []).append((ci, False))
        if R >= 0:
            per.setdefault(R, []).append((ci, True))
    rings = {}
    for reg, lst in per.items():
        items = []
        for ci, rev in lst:
            pts = chains[ci][2]
            if rev:
                pts = pts[::-1]
            items.append(pts)
        starts = {}
        for k, pts in enumerate(items):
            starts.setdefault((round(pts[0][0] * 1000), round(pts[0][1] * 1000)), []).append(k)
        usedk = set()
        rr = []
        for k0 in range(len(items)):
            if k0 in usedk:
                continue
            ring = []
            k = k0
            guard = 0
            while True:
                usedk.add(k)
                ring.extend(items[k][:-1].tolist())
                e = items[k][-1]
                key = (round(e[0] * 1000), round(e[1] * 1000))
                nxt = [t for t in starts.get(key, []) if t not in usedk]
                if not nxt:
                    break
                k = nxt[0]
                guard += 1
                if guard > 5000:
                    break
            if len(ring) >= 3:
                rr.append(np.array(ring))
        rings[reg] = rr
    return rings


def poly_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


# =============================================================================
# 5. вывод SVG
# =============================================================================
def num(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    if s == '-0':
        s = '0'
    if s.startswith('0.'):
        s = s[1:]
    elif s.startswith('-0.'):
        s = '-' + s[2:]
    return s


def join_nums(vals):
    out = []
    for i, v in enumerate(vals):
        s = num(v)
        if i and not s.startswith('-'):
            out.append(' ')
        out.append(s)
    return ''.join(out)


def d_abs(p, close=True):
    p = np.asarray(p)
    d = 'M' + join_nums([p[0][0], p[0][1]])
    if len(p) > 1:
        rel = np.diff(p, axis=0).ravel()
        d += 'l' + join_nums(rel)
    return d + ('z' if close else '')


# =============================================================================
# 6. основной конвейер
# =============================================================================
DEFAULT = dict(
    scale=2, n=150, n_init=3200, compactness=7.0, lam=0.25, cap=0.2, tol=1.5, q=1.0,
    lead=1.4, lead_major=2.6, frame=4.0, kind='scene', alpha=0.88, hi_prob=0.55,
    lights=None, min_area=14,
)



def neighbor_mean(lbl, vals):
    """Средневзвешенное (по длине границы) значение соседей каждой области."""
    n = len(vals)
    num_ = np.zeros(n)
    den = np.zeros(n)
    for a, b in ((lbl[:, :-1], lbl[:, 1:]), (lbl[:-1, :], lbl[1:, :])):
        m = (a != b) & (a >= 0) & (b >= 0)
        aa, bb = a[m], b[m]
        np.add.at(num_, aa, vals[bb])
        np.add.at(den, aa, 1)
        np.add.at(num_, bb, vals[aa])
        np.add.at(den, bb, 1)
    return np.where(den > 0, num_ / np.maximum(den, 1), vals)


def region_stats(lbl, rgb, n):
    """Средний Lab и RGB по внутренним пикселям каждой области."""
    from scipy import ndimage as ndi
    lab = srgb2lab(rgb)
    mx = ndi.maximum_filter(lbl, size=3)
    mn = ndi.minimum_filter(lbl, size=3)
    inner = (mx == mn) & (lbl >= 0)
    flat = lbl.ravel()
    res_lab = np.zeros((n, 3))
    cnt_all = np.bincount(flat[flat >= 0], minlength=n).astype(np.float64)
    cnt_in = np.bincount(flat[inner.ravel()], minlength=n).astype(np.float64)
    for k in range(3):
        s_all = np.bincount(flat[flat >= 0], weights=lab[..., k].ravel()[flat >= 0], minlength=n)
        s_in = np.bincount(flat[inner.ravel()], weights=lab[..., k].ravel()[inner.ravel()], minlength=n)
        use_in = cnt_in >= 6
        res_lab[:, k] = np.where(use_in, s_in / np.maximum(cnt_in, 1), s_all / np.maximum(cnt_all, 1))
    return res_lab, cnt_all


def detect_stars(rgb, mask=None, scale=2):
    """Мелкие светлые точки на тёмном (звёзды) → [(x, y, size, strength)] в координатах 1x."""
    from scipy import ndimage as ndi
    lab = srgb2lab(rgb)
    L = lab[..., 0]
    med = ndi.median_filter(L, size=int(3 * scale + 4) | 1)
    d = L - med
    m = d > 11
    if mask is not None:
        m &= mask
    lbl, n = ndi.label(m)
    if n == 0:
        return []
    out = []
    objs = ndi.find_objects(lbl)
    for i, sl in enumerate(objs, 1):
        area = int((lbl[sl] == i).sum())
        if area > 18 * scale * scale / 4:
            continue
        ys, xs = np.nonzero(lbl[sl] == i)
        cy = ys.mean() + sl[0].start + 0.5
        cx = xs.mean() + sl[1].start + 0.5
        peak = float(d[sl][lbl[sl] == i].max())
        out.append((cx / scale, cy / scale, peak, area))
    return out


def detect_lights(rgb, scale, n_max=4, mask=None):
    """Светлые источники (луна, окна, костёр, сияние) для задней подсветки."""
    from scipy import ndimage as ndi
    from skimage.feature import peak_local_max
    lab = srgb2lab(rgb)
    L = lab[..., 0].copy()
    if mask is not None:
        L[~mask] = 0
    sig = 4.0 * scale
    Lb = ndi.gaussian_filter(L, sig)
    pk = peak_local_max(Lb, min_distance=int(28 * scale), threshold_abs=34, num_peaks=n_max, exclude_border=False)
    res = []
    for y, x in pk:
        r = int(6 * scale)
        patch = rgb[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].reshape(-1, 3).mean(0)
        res.append((x / scale, y / scale, float(Lb[y, x]), patch))
    return res


def build_svg(name, svg, rgb, cfg, idmap=None, strokes=None):
    S = cfg['scale']
    W, H = viewbox(svg)
    q = cfg['q']
    circle = cfg['kind'] == 'circle'
    mask = None
    if circle:
        yy, xx = np.mgrid[:H * S, :W * S]
        cx, cy, r = W * S / 2, H * S / 2, cfg.get('r', 56.8) * S
        mask = (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r
    seg_src = (rgb.astype(np.float64) / 255.0) ** cfg.get('seg_gamma', 0.5)
    seg_src = (seg_src * 255).astype(np.uint8)
    if idmap is not None:
        from scipy import ndimage as ndi
        from skimage import measure
        idl = idmap.copy()
        if mask is not None:
            idl[~mask] = 0
        none = idl == 0
        if none.any():
            ind = ndi.distance_transform_edt(none, return_distances=False, return_indices=True)
            idl = idl[ind[0], ind[1]]
        cc = measure.label(idl, background=-1, connectivity=1) - 1
        cc = absorb_small(cc.astype(np.int32), int(cfg.get('id_min_area', 10) * S * S))
        if mask is not None:
            cc = np.where(mask, cc, -1)
        sp = cc
        lab_sm = srgb2lab(seg_src)
    else:
        sp, sm = superpixels(seg_src, int(cfg['n_init'] * (W * H) / 72000.0), cfg['compactness'], mask)
        lab_sm = srgb2lab(sm)
    nf = int(cfg['n'] * cfg.get('form_frac', 0.62))
    lbl, n = ward_merge(sp, lab_sm, nf, cfg['lam'], cfg['cap'] * (H * S) * (W * S), valid=mask)
    srng = np.random.RandomState(cfg.get('seed', 7))
    lbl_forms = lbl.copy()
    lbl = subdivide(lbl, cfg['n'], srng, cfg.get('sub_power', 0.75), cfg.get('stretch', 0.7))
    lbl = absorb_small(lbl, int(cfg['min_area'] * S * S))
    n = lbl.max() + 1
    tol = cfg['tol'] * S
    chains = planar_chains(lbl)
    new_chains = []
    for (L, R, pts, closed, v0, _) in chains:
        sp_ = simplify_chain(pts, closed, tol)
        sp_ = round_pts(sp_ / S, q)
        # убираем подряд идущие дубликаты
        keep = [0]
        for i in range(1, len(sp_)):
            if (sp_[i] != sp_[keep[-1]]).any():
                keep.append(i)
        sp_ = sp_[keep]
        if closed and len(sp_) > 1 and (sp_[0] != sp_[-1]).any():
            sp_ = np.vstack([sp_, sp_[:1]])
        new_chains.append((L, R, sp_, closed, v0, None))
    chains = new_chains
    rings = region_rings(chains, n)

    # --- цвета осколков
    lab_reg, cnt = region_stats(lbl, rgb, n)
    lab_raw_reg = lab_reg
    share = cnt / float(max(1, (lbl >= 0).sum()))
    # контекст цвета: центры областей, оттенок кадра, нижний порог яркости
    yy, xx = np.mgrid[:lbl.shape[0], :lbl.shape[1]]
    okm = lbl >= 0
    fl = lbl[okm]
    cxr = np.bincount(fl, weights=xx[okm], minlength=n) / np.maximum(cnt, 1) / lbl.shape[1]
    cyr = np.bincount(fl, weights=yy[okm], minlength=n) / np.maximum(cnt, 1) / lbl.shape[0]
    Lall = srgb2lab(rgb)
    Lv = Lall[..., 0][okm]
    Cv = np.hypot(Lall[..., 1][okm], Lall[..., 2][okm])
    hv = np.degrees(np.arctan2(Lall[..., 2][okm], Lall[..., 1][okm])) % 360
    wv = np.minimum(Cv, 20)
    h0 = math.degrees(math.atan2((np.sin(np.radians(hv)) * wv).sum(), (np.cos(np.radians(hv)) * wv).sum())) % 360
    rng = np.random.RandomState(cfg.get('seed', 7))
    Lsorted = np.sort(Lv)
    ranks = np.searchsorted(Lsorted, lab_reg[:, 0]) / float(len(Lsorted))
    Lp0 = cfg.get('lo', 11.0) + cfg.get('span', 50.0) * ranks
    dLs = np.clip(cfg.get('edge_k', 0.7) * (Lp0 - neighbor_mean(lbl, Lp0)), -cfg.get('edge_cap', 13.0), cfg.get('edge_cap', 13.0))
    ctx = dict(rng=rng, h0=h0, lo=cfg.get('lo', 11.0), span=cfg.get('span', 50.0), top=cfg.get('top', 42.0),
               L90=float(np.percentile(Lv, 92)), Ljit=cfg.get('Ljit', 2.5), ground_h=cfg.get('ground_h', 168),
               ground_y=cfg.get('ground_y', 0.6), hue_gain=cfg.get('hue_gain', 1.4), jit=cfg.get('jit', 9),
               alt_p=cfg.get('alt_p', 0.05))
    fcnt = np.bincount(lbl_forms[lbl_forms >= 0], minlength=lbl_forms.max() + 1).astype(np.float64)
    fshare = fcnt / float(max(1, (lbl_forms >= 0).sum()))
    cell_form = np.zeros(n)
    for i in range(n):
        yc = min(lbl.shape[0] - 1, int(cyr[i] * lbl.shape[0]))
        xc = min(lbl.shape[1] - 1, int(cxr[i] * lbl.shape[1]))
        pm = lbl == i
        ys_, xs_ = np.nonzero(pm)
        k_ = int(len(ys_) // 2)
        fl_ = lbl_forms[ys_[k_], xs_[k_]]
        cell_form[i] = fshare[fl_] if fl_ >= 0 else 0.0
    jew = []
    for i in range(n):
        ctx['cx'], ctx['cy'], ctx['rank'], ctx['dL'] = cxr[i], cyr[i], ranks[i], dLs[i]
        jew.append(jewelize(lab_reg[i], max(share[i], cell_form[i]), ctx))
    jew = np.array(jew)
    idx = np.array([snap_to_ramp(j)[0] for j in jew])
    # ограничиваем число цветов (по площади), мелкие уходят к ближайшему оставленному
    ramp_lab, ramp_names = ramp()
    use = {}
    for i in range(n):
        use[idx[i]] = use.get(idx[i], 0) + cnt[i]
    order = sorted(use, key=lambda k: -use[k])
    K = cfg.get('K', 24)
    keep_idx = order[:K]
    # яркие мелкие (окна, огонь) не теряем
    for k in order[K:]:
        if ramp_lab[k][0] > 62 and lab2lch(ramp_lab[k])[1] > 40 and len(keep_idx) < K + 6:
            keep_idx.append(k)
    keep_arr = ramp_lab[keep_idx]
    final = np.zeros(n, dtype=int)
    for i in range(n):
        if idx[i] in keep_idx:
            final[i] = idx[i]
        else:
            d = ((keep_arr - ramp_lab[idx[i]]) ** 2).sum(1)
            final[i] = keep_idx[int(np.argmin(d))]
    reg_lab = ramp_lab[final]
    lab_raw_reg = reg_lab

    # --- SVG
    gid = {}
    gdefs = []
    a = cfg['alpha']
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def grad(k):
        if k in gid:
            return gid[k]
        g = letters[len(gid)]
        gid[k] = g
        Lc, a_, b_ = ramp_lab[k]
        L_, C_, h_ = lab2lch(ramp_lab[k])
        c0 = rgb2hex(lab2srgb(lch2lab(max(8, L_ - 2), C_, h_)))
        c1 = rgb2hex(lab2srgb(in_gamut(min(97, L_ + 6 + (3 if L_ < 30 else 0)), C_ * 0.95, h_)))
        gdefs.append(f'<radialGradient id="{g}" r=".78"><stop offset="0" stop-color="{c0}" stop-opacity="{num(a)}"/>'
                     f'<stop offset="1" stop-color="{c1}" stop-opacity="{num(min(1, a + .08))}"/></radialGradient>')
        return g

    body = []
    # задняя подсветка
    body.append(f'<rect width="{W}" height="{H}" fill="{LEAD}"/>' if not circle else
                f'<circle cx="{num(W / 2)}" cy="{num(H / 2)}" r="{num(cfg.get("r", 56.8))}" fill="{LEAD}"/>')
    lights = cfg.get('lights')
    if lights is None:
        lights = []
        cand_l = []
        for i in range(n):
            Lr, Cr, hr = lab2lch(reg_lab[i])
            a1 = cnt[i] / float(S * S)
            if 54 <= hr <= 80 and Lr > 58 and Cr > 40:
                cand_l.append((a1 * 3 + 40, i, '#F0A24A', 0.62))
            elif Lr > 86:
                cand_l.append((a1 * 2 + 30, i, '#EDE6D2', 0.42))
        cand_l.sort(reverse=True)
        for sc_, i, col, op in cand_l[:cfg.get('n_lights', 8)]:
            a1 = cnt[i] / float(S * S)
            rad = min(58, 2.4 * math.sqrt(a1 / math.pi) + 16) * cfg.get('light_r', 1.0)
            lights.append((cxr[i] * W, cyr[i] * H, rad, col, op * cfg.get('light_op', 1.0)))
    glow_defs = []
    glow_els = []
    bloom_els = []
    gcache = {}
    for (x, y, rad, gcol, op) in lights:
        if circle:      # свет не должен выходить за кольцо медальона
            rad = min(rad, cfg.get('r', 56.8) - math.hypot(x - W / 2, y - H / 2) - 1)
            if rad < 7:
                continue
        if gcol not in gcache:
            gname = 'g' + str(len(gcache))
            gcache[gcol] = gname
            glow_defs.append(f'<radialGradient id="{gname}"><stop offset="0" stop-color="{gcol}"/>'
                             f'<stop offset=".5" stop-color="{gcol}" stop-opacity=".4"/>'
                             f'<stop offset="1" stop-color="{gcol}" stop-opacity="0"/></radialGradient>')
        gname = gcache[gcol]
        glow_els.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(rad)}" fill="url(#{gname})" opacity="{num(min(1, op * 1.5))}"/>')
        bloom_els.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(rad * 0.85)}" fill="url(#{gname})" opacity="{num(op * 0.5)}"/>')
    body.extend(glow_els)

    # осколки: по цветам
    groups = {}
    order_regs = sorted(range(n), key=lambda i: -cnt[i])
    for i in order_regs:
        rr_ = rings.get(i)
        if not rr_:
            continue
        d = ''
        for ring in rr_:
            ring = np.asarray(ring)
            # убрать подряд-дубликаты
            if len(ring) < 3:
                continue
            if abs(poly_area(ring)) < 0.5:
                continue
            d += d_abs(ring)
        if not d:
            continue
        groups.setdefault(final[i], []).append((i, d))
    lead_w = cfg['lead']
    shard_els = []
    for k in sorted(groups, key=lambda k: -sum(cnt[i] for i, _ in groups[k])):
        g = grad(k)
        shard_els.append(f'<g fill="url(#{g})">' + ''.join(f'<path d="{d}"/>' for _, d in groups[k]) + '</g>')
    body.append(f'<g stroke="{LEAD}" stroke-width="{num(lead_w)}" stroke-linejoin="round">' + ''.join(shard_els) + '</g>')

    # блики
    hi = []
    rng = np.random.RandomState(abs(hash(name)) % (2 ** 31))
    for i in range(n):
        if cfg['hi_prob'] <= 0:
            break
        for ring in rings.get(i, [])[:1]:
            if len(ring) < 3 or abs(poly_area(ring)) < 90 * (q if q < 1 else 1) or rng.rand() > cfg['hi_prob']:
                continue
            tri = highlight(ring, rng)
            if tri is not None:
                hi.append(tri)
    if hi:
        body.append('<g fill="#fff" fill-opacity=".16">' + ''.join(f'<path d="{d}"/>' for d in hi) + '</g>')

    # звёзды
    st = detect_stars(rgb, mask, S) if cfg.get('stars', True) else []
    if st:
        sd = ''
        for (x, y, peak, area) in st[:cfg.get('max_stars', 60)]:
            s = 0.9 + min(1.6, peak / 40.0)
            sd += d_abs(np.array([(x, y - s), (x + s * 0.45, y), (x, y + s), (x - s * 0.45, y)]).round(1))
        body.append(f'<path d="{sd}" fill="#EDE6D2" fill-opacity=".85"/>')

    # толстый свинец: границы крупных форм (верхняя четверть контрастов по длине)
    cand = []
    for (L, R, pts, closed, v0, _) in chains:
        if L < 0 or R < 0 or len(pts) < 2:
            continue
        dE = float(np.linalg.norm(lab_raw_reg[L] - lab_raw_reg[R]))
        length = float(np.hypot(*np.diff(pts, axis=0).T).sum())
        if length >= cfg.get('major_len', 7):
            cand.append((dE, length, pts))
    major = []
    if cand:
        dEs = np.array([c[0] for c in cand])
        ws = np.array([c[1] for c in cand])
        o = np.argsort(dEs)
        cw = np.cumsum(ws[o]) / ws.sum()
        thr = dEs[o][min(len(o) - 1, int(np.searchsorted(cw, cfg.get('major_q', 0.72))))]
        for dE, length, pts in cand:
            if dE >= thr:
                major.append(d_abs(pts, close=False))
    if major:
        body.append(f'<path d="{"".join(major)}" fill="none" stroke="{LEAD}" stroke-width="{num(cfg["lead_major"])}" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>')

    if strokes and cfg.get('gris', True):
        body.append(grisaille(strokes, W, H, cfg.get('gris_budget', 3000)))
    body.extend(bloom_els)

    # рама
    fw = cfg['frame']
    if circle:
        rr = cfg.get('r', 56.8) + 0.4
        body.append(f'<circle cx="{num(W / 2)}" cy="{num(H / 2)}" r="{num(rr)}" fill="none" stroke="{LEAD}" stroke-width="{num(fw)}"/>')
        body.append(f'<circle cx="{num(W / 2)}" cy="{num(H / 2)}" r="{num(rr - fw / 2 - 0.5)}" fill="none" stroke="#9fb4c4" stroke-width=".5" stroke-opacity=".35"/>')
    else:
        h = fw / 2
        body.append(f'<rect x="{num(h)}" y="{num(h)}" width="{num(W - fw)}" height="{num(H - fw)}" fill="none" stroke="{LEAD}" stroke-width="{num(fw)}"/>')
        o = fw + 0.5
        body.append(f'<rect x="{num(o)}" y="{num(o)}" width="{num(W - 2 * o)}" height="{num(H - 2 * o)}" fill="none" stroke="#9fb4c4" stroke-width=".5" stroke-opacity=".3"/>')

    defs = ''.join(glow_defs) + ''.join(gdefs)
    svg_out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><defs>{defs}</defs>'
               + ''.join(body) + '</svg>\n')
    return svg_out, dict(n=n, colors=len(gid))



NUM_RE = re.compile(r'-?\d*\.?\d+(?:e-?\d+)?')


def round_d(d, prec=1):
    def rep(m):
        v = float(m.group(0))
        return num(round(v, prec))
    d = NUM_RE.sub(rep, d)
    d = re.sub(r'\s+', ' ', d).strip()
    d = re.sub(r' ?([MmLlHhVvCcSsQqTtAaZz]) ?', r'\1', d)
    d = re.sub(r',(?=-)', '', d)
    return d


def grisaille(strokes, W, H, budget, circle_r=None):
    """Тонкие линии сырья (стебли, провода, столбы, дождь) → свинцовая «роспись» поверх стекла."""
    if not strokes:
        return ''
    groups = {}
    items = []
    for st in strokes:
        m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', st['stroke'])
        if not m:
            continue
        rgb_ = [int(m.group(i)) for i in (1, 2, 3)]
        Lc = srgb2lab(np.array([rgb_], dtype=np.float64))[0][0]
        op = st['op']
        sw = st['sw']
        if Lc < 24 and op >= 0.5 and sw >= 0.7:
            kind = ('d', min(2.2, max(1.0, sw * 1.05)), 1)
        elif Lc > 60 and op >= 0.25 and sw >= 0.5 and st['len'] > 8:
            kind = ('l', 0.8 if sw < 1.2 else 1.2, 0.3 if op < 0.5 else 0.5)
        else:
            continue
        items.append((st['len'] * (1.5 if kind[0] == 'd' else 0.7), kind, st['d']))
    items.sort(key=lambda t: -t[0])
    used = 0
    for sc, kind, d in items:
        dd = round_d(d)
        if used + len(dd) > budget:
            continue
        used += len(dd)
        groups.setdefault(kind, []).append(dd)
    out = []
    for (k, w, op), ds in groups.items():
        col = LEAD if k == 'd' else '#EDE6D2'
        extra = '' if op == 1 else f' stroke-opacity="{num(op)}"'
        out.append(f'<path d="{"".join(ds)}" fill="none" stroke="{col}" stroke-width="{num(w)}"{extra} stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(out)


def highlight(ring, rng):
    """Тонкий светлый треугольник вдоль длинной грани, обращённой к свету (слева сверху)."""
    p = np.asarray(ring)
    n = len(p)
    area = poly_area(p)
    sgn = 1.0 if area > 0 else -1.0
    best = None
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        e = b - a
        Ln = math.hypot(e[0], e[1])
        if Ln < 9:
            continue
        # внутренняя нормаль (область слева от обхода при положительной ориентации в экранных осях)
        nin = np.array([e[1], -e[0]]) / Ln * sgn * -1
        # проверим, что внутрь действительно внутрь
        mid = (a + b) / 2
        if not point_in_poly(mid + nin * 1.5, p):
            nin = -nin
            if not point_in_poly(mid + nin * 1.5, p):
                continue
        facing = -(nin[0] * -0.55 + nin[1] * -0.83)    # внешняя нормаль к свету (-0.55,-0.83)
        if facing < 0.35:
            continue
        sc = Ln * facing
        if best is None or sc > best[0]:
            best = (sc, a, b, nin, Ln)
    if best is None:
        return None
    _, a, b, nin, Ln = best
    u = (b - a) / Ln
    off = 1.5
    t = min(3.2, 0.14 * Ln)
    p1 = a + u * Ln * 0.14 + nin * off
    p2 = a + u * Ln * 0.62 + nin * off
    p3 = a + u * Ln * 0.14 + nin * (off + t)
    for pt in (p1, p2, p3, (p1 + p2) / 2 + nin * 0.5, (p1 + p3) / 2, (p2 + p3) / 2):
        if not point_in_poly(pt, p):
            return None
    tri = np.array([p1, p2, p3]).round(1)
    return d_abs(tri)


# =============================================================================
# 7. пакетная обработка
# =============================================================================
CONFIG = {
    'scenes': dict(n=150, scale=2),
    'creatures': dict(n=92, scale=5, kind='circle', lead=1.0, lead_major=1.9, frame=3.0, q=0.5, tol=0.5,
                      n_init=1500, cap=0.09, min_area=6, hi_prob=0.5, major_dE=18),
    'finale': dict(n=160, scale=2),
    'onboarding': dict(n=150, scale=2),
}


def group_of(rel):
    return rel.split('/')[0]


def glassify_one(rel, svg, rgb, over=None, idmap=None, strokes=None):
    cfg = dict(DEFAULT)
    cfg.update(CONFIG.get(group_of(rel), {}))
    cfg.update((over or {}).get(rel, {}))
    cfg.update(CONFIG_OVERRIDE.get(rel, {}))
    # подбор числа осколков под лимит размера
    n = cfg['n']
    while True:
        cfg['n'] = n
        out, info = build_svg(rel, svg, rgb, cfg, idmap, strokes)
        size = len(out.encode())
        if size <= MAX_BYTES or n < 40:
            break
        n = int(n * (0.9 if size < MAX_BYTES * 1.25 else 0.8))
    info['size'] = size
    info['n_req'] = n
    return out, info


CONFIG_OVERRIDE = {}
USE_IDS = True


def run(raws, only=None, verbose=True):
    """raws: dict rel -> svg (сырьё). Возвращает dict rel -> витражный SVG."""
    res = {}
    by_scale = {}
    for rel, svg in raws.items():
        if only and not any(o in rel for o in only):
            continue
        s = dict(DEFAULT)
        s.update(CONFIG.get(group_of(rel), {}))
        s.update(CONFIG_OVERRIDE.get(rel, {}))
        by_scale.setdefault(s['scale'], {})[rel] = svg
    for scale, items in by_scale.items():
        rast = rasterize(items, scale, ids=True)
        for rel, svg in items.items():
            rgb, idm, strokes = rast[rel]
            out, info = glassify_one(rel, svg, rgb, idmap=idm if USE_IDS else None, strokes=strokes)
            res[rel] = out
            if verbose:
                print(f'  glass {rel}: {info["size"]} B, shards {info["n"]}, colors {info["colors"]}', flush=True)
    return res


if __name__ == '__main__':
    names = sys.argv[1:]
    raws = {}
    for root, _, files in os.walk(RAW):
        for fn in files:
            if fn.endswith('.svg'):
                rel = os.path.relpath(os.path.join(root, fn), RAW)
                raws[rel] = open(os.path.join(root, fn), encoding='utf-8').read()
    out = run(raws, names or None)
    for rel, svg in out.items():
        p = os.path.join(ART, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(svg)

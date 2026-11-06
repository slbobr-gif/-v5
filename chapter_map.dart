// Карта главы (вариант 5 «Глава крупно + мини-карта + слои», docs/v5/04-art-style.md → «Карта»).
// Геометрия считается один раз: линия всего пути — на контент, осколки витража и пути зон — на главу.
// Painter только рисует готовые Path/Picture; подписи и значки — дети Flow, их двигает матрица
// InteractiveViewer без перестройки виджетов. Тап по значку ищется по экранным координатам.

import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../data/content_repository.dart';
import '../../engine/world.dart';
import '../theme/tokens.dart';
import 'common.dart';
import 'glass_paint.dart';
import 'route_map.dart' show MapProjection;
import 'route_ribbon.dart' show RibbonChapter, RibbonSeg;

/// Цвет [c] долей [t] поверх [base] (как mix() в генераторе макетов).
Color mixColor(Color c, double t, [Color base = Palette.ink]) => Color.lerp(base, c, t.clamp(0.0, 1.0).toDouble())!;

// ---------------------------------------------------------------- линия всего пути

/// Линия маршрута по реальным местам в единицах карты (MapProjection) и слои воды.
/// Одна на контент: строится при первом обращении.
class RouteLine {
  RouteLine._(this.content, this.proj, this.pos, this.pts, this.water, this.land, this.rivers, this.bounds);

  final GameContent content;
  final MapProjection proj;

  /// Игровые метры мест по порядку (строго возрастают) и их точки на карте.
  final List<double> pos;
  final List<Offset> pts;

  /// Море и озёра (замкнутые), суша (если карта её даёт), реки.
  final List<Path> water;
  final List<Path> land;
  final List<Path> rivers;

  /// Рамка всего маршрута.
  final Rect bounds;

  final Map<int, Path> _chapterPaths = <int, Path>{};
  final Map<int, Rect> _chapterRects = <int, Rect>{};

  static RouteLine? _cache;

  static RouteLine of(GameContent c) {
    final hit = _cache;
    if (hit != null && identical(hit.content, c)) return hit;
    final made = _build(c);
    _cache = made;
    return made;
  }

  static Path _poly(MapProjection proj, List<List<double>> src, bool close) {
    final p = Path();
    var first = true;
    for (final pt in src) {
      if (pt.length < 2) continue;
      final o = proj.project(pt[0], pt[1]);
      if (first) {
        p.moveTo(o.dx, o.dy);
        first = false;
      } else {
        p.lineTo(o.dx, o.dy);
      }
    }
    if (close) p.close();
    return p;
  }

  static RouteLine _build(GameContent c) {
    final proj = MapProjection(c.map.bbox);
    final w = c.world;
    final pos = <double>[];
    final pts = <Offset>[];
    for (final p in w.places) {
      if (p['virtual'] == true) continue;
      final at = w.posOf['${p['id']}'];
      if (at == null) continue;
      if (pos.isNotEmpty && at <= pos.last) continue;
      pos.add(at);
      pts.add(proj.project(toD(p['lon']), toD(p['lat'])));
    }
    final layers = c.map.layers;
    const none = <List<List<double>>>[];
    final water = <Path>[
      for (final k in const ['sea', 'lakes'])
        for (final s in layers[k] ?? none)
          if (s.length > 2) _poly(proj, s, true),
    ];
    final land = <Path>[
      for (final s in layers['land'] ?? none)
        if (s.length > 2) _poly(proj, s, true),
    ];
    final rivers = <Path>[
      for (final s in layers['rivers'] ?? none)
        if (s.length > 1) _poly(proj, s, false),
    ];
    var b = pts.isEmpty ? Rect.zero : Rect.fromPoints(pts.first, pts.first);
    for (final o in pts) {
      b = b.expandToInclude(Rect.fromPoints(o, o));
    }
    return RouteLine._(c, proj, pos, pts, water, land, rivers, b);
  }

  /// Точка линии для игровой позиции (линейно между соседними местами).
  Offset at(double p) {
    if (pts.isEmpty) return Offset.zero;
    if (p <= pos.first) return pts.first;
    for (var i = 1; i < pos.length; i++) {
      if (pos[i] >= p) {
        final span = pos[i] - pos[i - 1];
        final t = span <= 0 ? 0.0 : (p - pos[i - 1]) / span;
        return Offset.lerp(pts[i - 1], pts[i], t)!;
      }
    }
    return pts.last;
  }

  /// Единичный вектор направления пути (по 4 км назад и вперёд — излом на месте не дёргает).
  Offset dirAt(double p) {
    final d = at(p + 4000) - at(p - 4000);
    final len = d.distance;
    if (len < 1e-9) return const Offset(0, -1);
    return d / len;
  }

  /// Точки участка линии от [a] до [b] (игровые метры).
  List<Offset> subPts(double a, double b) {
    final out = <Offset>[at(a)];
    for (var i = 0; i < pos.length; i++) {
      if (pos[i] > a && pos[i] < b) out.add(pts[i]);
    }
    out.add(at(b));
    return out;
  }

  Path subPath(double a, double b) {
    final pp = subPts(a, b);
    final p = Path()..moveTo(pp.first.dx, pp.first.dy);
    for (var i = 1; i < pp.length; i++) {
      p.lineTo(pp[i].dx, pp[i].dy);
    }
    return p;
  }

  /// Ближайшая к [q] точка линии: (расстояние в единицах карты, игровая позиция).
  (double, double) nearest(Offset q) {
    var bestD = double.infinity;
    var bestP = 0.0;
    for (var i = 1; i < pts.length; i++) {
      final a = pts[i - 1];
      final ab = pts[i] - a;
      final l2 = ab.dx * ab.dx + ab.dy * ab.dy;
      var t = l2 <= 1e-12 ? 0.0 : ((q.dx - a.dx) * ab.dx + (q.dy - a.dy) * ab.dy) / l2;
      t = t.clamp(0.0, 1.0).toDouble();
      final c = Offset(a.dx + ab.dx * t, a.dy + ab.dy * t);
      final d = (q - c).distance;
      if (d < bestD) {
        bestD = d;
        bestP = pos[i - 1] + (pos[i] - pos[i - 1]) * t;
      }
    }
    return (bestD, bestP);
  }

  Path chapterPath(World w, int ch) =>
      _chapterPaths.putIfAbsent(ch, () => subPath(w.chapterStartPos(ch), w.chapterEndPos(ch)));

  Rect chapterRect(World w, int ch) => _chapterRects.putIfAbsent(ch, () {
        final pp = subPts(w.chapterStartPos(ch), w.chapterEndPos(ch));
        var r = Rect.fromPoints(pp.first, pp.first);
        for (final o in pp) {
          r = r.expandToInclude(Rect.fromPoints(o, o));
        }
        return r;
      });
}

// ---------------------------------------------------------------- глава: осколки и зоны

class _Shard {
  const _Shard(this.path, this.base, this.zone, this.near, this.pos, this.k);
  final Path path;
  final Color base;
  final Color zone;
  final bool near;
  final double pos;
  final double k;
}

/// Тёмные стёкла фона (pal_far макета).
const _farGlass = <Color>[
  Color(0xFF122033),
  Color(0xFF132235),
  Color(0xFF111D2D),
  Color(0xFF152438),
  Color(0xFF101B2A),
  Color(0xFF14223A),
];

/// Неизменная геометрия главы: рамка, линия, отрезки зон и осколки витража (Вороной по сетке).
class ChapterGeo {
  ChapterGeo._(this.ch, this.start, this.end, this.bounds, this.route, this.segs, this.segPaths, this.shards, this.step);

  final int ch;
  final double start;
  final double end;
  final Rect bounds;
  final Path route;
  final List<RibbonSeg> segs;
  final List<Path> segPaths;
  final List<_Shard> shards;
  final double step;

  ui.Picture? _pic;
  int _picSig = -1;

  static GameContent? _for;
  static final Map<int, ChapterGeo> _cache = <int, ChapterGeo>{};

  static ChapterGeo of(GameContent c, int ch) {
    if (!identical(_for, c)) {
      _for = c;
      _cache.clear();
    }
    return _cache.putIfAbsent(ch, () => _build(c, ch));
  }

  static ChapterGeo _build(GameContent c, int ch) {
    final w = c.world;
    final line = RouteLine.of(c);
    final start = w.chapterStartPos(ch);
    final end = w.chapterEndPos(ch);
    final bounds = line.chapterRect(w, ch);
    final segs = RibbonChapter.of(w, ch).segs;
    final segPaths = <Path>[for (final s in segs) line.subPath(s.a, s.b)];
    final dim = math.max(10.0, math.max(bounds.width, bounds.height));
    final step = dim / 9;
    final area = Rect.fromCenter(center: bounds.center, width: dim * 2.8, height: dim * 2.8);
    final shards = _shardsFor(w, line, area, step, 21 + ch);
    return ChapterGeo._(ch, start, end, bounds, line.chapterPath(w, ch), segs, segPaths, shards, step);
  }

  /// Ячейки Вороного вокруг узлов сетки с дрожанием: каждая ячейка — квадрат, обрезанный
  /// серединными перпендикулярами к соседям (в радиусе двух шагов сетки).
  static List<_Shard> _shardsFor(World w, RouteLine line, Rect area, double step, int seed) {
    final rnd = math.Random(seed);
    final cols = (area.width / step).ceil() + 1;
    final rows = (area.height / step).ceil() + 1;
    final sites = List<Offset>.filled(cols * rows, Offset.zero);
    for (var gy = 0; gy < rows; gy++) {
      for (var gx = 0; gx < cols; gx++) {
        final jx = (rnd.nextDouble() - 0.5) * 0.9 * step;
        final jy = (rnd.nextDouble() - 0.5) * 0.9 * step;
        sites[gy * cols + gx] = Offset(
          area.left + gx * step + (gy.isOdd ? step / 2 : 0) + jx,
          area.top + gy * step + jy,
        );
      }
    }
    final out = <_Shard>[];
    final r = step * 0.9;
    final big = step * 2;
    for (var gy = 0; gy < rows; gy++) {
      for (var gx = 0; gx < cols; gx++) {
        final s = sites[gy * cols + gx];
        var poly = <Offset>[
          s + Offset(-big, -big),
          s + Offset(big, -big),
          s + Offset(big, big),
          s + Offset(-big, big),
        ];
        for (var ny = gy - 2; ny <= gy + 2 && poly.length >= 3; ny++) {
          if (ny < 0 || ny >= rows) continue;
          for (var nx = gx - 2; nx <= gx + 2 && poly.length >= 3; nx++) {
            if (nx < 0 || nx >= cols || (nx == gx && ny == gy)) continue;
            poly = _clipHalf(poly, s, sites[ny * cols + nx]);
          }
        }
        if (poly.length < 3) continue;
        var cx = 0.0;
        var cy = 0.0;
        for (final o in poly) {
          cx += o.dx;
          cy += o.dy;
        }
        final centroid = Offset(cx / poly.length, cy / poly.length);
        final (d, pos) = line.nearest(centroid);
        final base = _farGlass[rnd.nextInt(_farGlass.length)];
        final near = d < r;
        final path = Path()..moveTo(poly.first.dx, poly.first.dy);
        for (var i = 1; i < poly.length; i++) {
          path.lineTo(poly[i].dx, poly[i].dy);
        }
        path.close();
        out.add(_Shard(path, base, Palette.zone(w.zoneAt(pos)), near, pos, near ? 1 - d / (2 * r) : 0.0));
      }
    }
    return out;
  }

  /// Оставляет часть многоугольника, которая ближе к [s], чем к [o] (Сазерленд — Ходжмен).
  static List<Offset> _clipHalf(List<Offset> poly, Offset s, Offset o) {
    final n = o - s;
    final m = Offset((s.dx + o.dx) / 2, (s.dy + o.dy) / 2);
    double f(Offset q) => (q.dx - m.dx) * n.dx + (q.dy - m.dy) * n.dy;
    final out = <Offset>[];
    for (var i = 0; i < poly.length; i++) {
      final a = poly[(i + poly.length - 1) % poly.length];
      final b = poly[i];
      final fa = f(a);
      final fb = f(b);
      if (fb <= 0) {
        if (fa > 0) out.add(Offset.lerp(a, b, fa / (fa - fb))!);
        out.add(b);
      } else if (fa <= 0) {
        out.add(Offset.lerp(a, b, fa / (fa - fb))!);
      }
    }
    return out;
  }

  /// Записанный рисунок осколков. У пути стекло окрашено зоной: пройденное ярче.
  /// Перезаписывается, только когда меняется число «пройденных» осколков.
  ui.Picture pictureFor(double heroPos) {
    var sig = 0;
    for (final s in shards) {
      if (s.near && s.pos <= heroPos) sig++;
    }
    final cached = _pic;
    if (cached != null && sig == _picSig) return cached;
    final rec = ui.PictureRecorder();
    final canvas = Canvas(rec);
    final lead = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = step * 0.03
      ..strokeJoin = StrokeJoin.round
      ..color = const Color(0xFF0A1018);
    final fill = Paint();
    for (final s in shards) {
      fill.color = s.near ? mixColor(s.zone, (s.pos <= heroPos ? 0.62 : 0.26) * 0.55 * s.k, s.base) : s.base;
      canvas.drawPath(s.path, fill);
      canvas.drawPath(s.path, lead);
    }
    final pic = rec.endRecording();
    _pic = pic;
    _picSig = sig;
    return pic;
  }
}

// ---------------------------------------------------------------- значки поверх карты

/// Значок или подпись поверх карты. [at] — точка в единицах карты, [shift] — сдвиг в экранных
/// пикселях, [align] — какой точкой ребёнок встаёт на место (center, centerLeft, …).
/// [leader] — тонкая пунктирная выноска от [at] к значку. [tappable] — тап открывает карточку.
class MapMark {
  const MapMark({
    required this.id,
    required this.at,
    required this.child,
    this.shift = Offset.zero,
    this.align = Alignment.center,
    this.tappable = false,
    this.leader = false,
  });

  final String id;
  final Offset at;
  final Widget child;
  final Offset shift;
  final Alignment align;
  final bool tappable;
  final bool leader;
}

class _MarksFlow extends FlowDelegate {
  _MarksFlow(this.ctrl, this.marks, this.origin) : super(repaint: ctrl);

  final TransformationController ctrl;
  final List<MapMark> marks;
  final Offset origin;

  @override
  BoxConstraints getConstraintsForChild(int i, BoxConstraints constraints) => BoxConstraints.loose(constraints.biggest);

  @override
  void paintChildren(FlowPaintingContext context) {
    final m = ctrl.value;
    final n = math.min(marks.length, context.childCount);
    final vp = context.size;
    for (var i = 0; i < n; i++) {
      final mk = marks[i];
      final p = MatrixUtils.transformPoint(m, mk.at - origin) + mk.shift;
      final sz = context.getChildSize(i) ?? Size.zero;
      final x = p.dx - (mk.align.x + 1) / 2 * sz.width;
      final y = p.dy - (mk.align.y + 1) / 2 * sz.height;
      // за краем экрана не рисуем
      if (x > vp.width || y > vp.height || x + sz.width < 0 || y + sz.height < 0) continue;
      context.paintChild(i, transform: Matrix4.translationValues(x, y, 0));
    }
  }

  @override
  bool shouldRepaint(_MarksFlow oldDelegate) =>
      !identical(oldDelegate.marks, marks) || oldDelegate.origin != origin || oldDelegate.ctrl != ctrl;

  @override
  bool shouldRelayout(_MarksFlow oldDelegate) => false;
}

// ---------------------------------------------------------------- painter главы

class _Jewel {
  const _Jewel(this.at, this.big, this.reached);
  final Offset at;
  final bool big;
  final bool reached;
}

/// Всё, что зависит от героя: рисунок осколков, пройденные отрезки, точка героя.
class _Frame {
  _Frame(this.hero, this.shards, this.walkedSegs, this.walked, this.heroPt, this.heroNormal, this.heroHere);
  final double hero;
  final ui.Picture shards;
  final List<(Path, Color)> walkedSegs;
  final Path? walked;
  final Offset heroPt;
  final Offset heroNormal;
  final bool heroHere;
}

const _skyGlass = <Color>[Color(0x8CA2DAF9), Color(0x8C5BB5E8), Color(0x8C3585BA)];
const _turqJewel = <Color>[Color(0xFF9CF5EF), Color(0xFF3FD6CC), Color(0xFF1FA39B)];
const _nightJewel = <Color>[Color(0xFF3A4E66), Color(0xFF1F2E40), Color(0xFF0B1424)];

class _ChapterPainter extends CustomPainter {
  _ChapterPainter({
    required this.line,
    required this.geo,
    required this.frame,
    required this.jewels,
    required this.leaders,
    required this.origin,
    required this.ctrl,
    required this.night,
    required this.selected,
  }) : super(repaint: ctrl);

  final RouteLine line;
  final ChapterGeo geo;
  final _Frame frame;
  final List<_Jewel> jewels;
  final List<MapMark> leaders;
  final Offset origin;
  final TransformationController ctrl;
  final double night;
  final Offset? selected;

  static const _hero = 22.0;

  @override
  void paint(Canvas canvas, Size size) {
    final scale = ctrl.value.getMaxScaleOnAxis();
    // Единиц карты в одном логическом пикселе: линии и значки не раздуваются при приближении.
    final px = scale > 1e-6 ? 1.0 / scale : 1.0;
    final view = origin & size;
    canvas.save();
    canvas.translate(-origin.dx, -origin.dy);

    // фон и витраж суши
    canvas.drawRect(view, solid(Palette.ink));
    if (line.land.isNotEmpty) {
      canvas.drawRect(view, solid(Palette.sea));
      for (final p in line.land) {
        canvas.save();
        canvas.clipPath(p);
        canvas.drawPicture(frame.shards);
        canvas.restore();
      }
    } else {
      canvas.drawPicture(frame.shards);
    }

    // вода стеклом: небо с прозрачностью, свинцовая кромка
    final waterFill = linearFill(view.topCenter, view.bottomCenter, _skyGlass, Glass.stops3);
    final waterEdge = stroke(2.0 * px);
    for (final p in line.water) {
      canvas.drawPath(p, waterFill);
      canvas.drawPath(p, waterEdge);
    }
    final r1 = stroke(6 * px);
    final r2 = stroke(3.4 * px, const Color(0xFF3C7FB0));
    final r3 = stroke(1 * px, const Color(0xFF9FD6F5), 0.5);
    for (final p in line.rivers) {
      canvas.drawPath(p, r1);
      canvas.drawPath(p, r2);
      canvas.drawPath(p, r3);
    }

    // лента пути по зонам: свинцовая подложка, впереди — приглушённое стекло, позади — яркое
    canvas.drawPath(geo.route, stroke(10 * px));
    for (var i = 0; i < geo.segs.length && i < geo.segPaths.length; i++) {
      canvas.drawPath(geo.segPaths[i], stroke(6 * px, mixColor(Palette.zone(geo.segs[i].zone), 0.42)));
    }
    for (final (p, c) in frame.walkedSegs) {
      canvas.drawPath(p, stroke(6 * px, c));
    }
    final walked = frame.walked;
    if (walked != null) {
      canvas.drawPath(walked, stroke(11.2 * px, Palette.accent, 0.13));
      canvas.drawPath(walked, stroke(6.4 * px, Palette.accent, 0.28));
      canvas.drawPath(walked, stroke(1.8 * px, Palette.accent));
    }

    // выноски значков
    final leaderPaint = stroke(1 * px, Palette.parchmentDim, 0.55);
    for (final mk in leaders) {
      final len = mk.shift.distance;
      if (len < 1) continue;
      final dir = mk.shift / len;
      for (var d = 0.0; d < len - 8; d += 4) {
        final a = mk.at + dir * (d * px);
        final b = mk.at + dir * (math.min(d + 2, len) * px);
        canvas.drawLine(a, b, leaderPaint);
      }
    }

    // места главы — стеклянные кабошоны
    for (final j in jewels) {
      final r = (j.big ? 6.0 : 4.4) * px;
      canvas.drawCircle(j.at, r + 2 * px, solid(Glass.lead));
      final hl = j.at + Offset(-r * 0.3, -r * 0.35);
      canvas.drawCircle(j.at, r, radialFill(hl, r * 1.6, j.reached ? _turqJewel : _nightJewel, Glass.stops3));
      if (!j.reached) canvas.drawCircle(j.at, r - 0.5 * px, stroke(1.2 * px, Palette.parchmentDim, 0.7));
      canvas.drawCircle(hl, r * 0.28, solid(Colors.white, 0.55));
    }

    final sel = selected;
    if (sel != null) canvas.drawCircle(sel, 13 * px, stroke(2 * px, Palette.accent));

    // герой: точка на линии и связь с миплом
    if (frame.heroHere) {
      final a = frame.heroPt;
      final c = a + frame.heroNormal * (_hero * px);
      canvas.drawLine(a, c, stroke(1.5 * px, Palette.accent));
      canvas.drawCircle(a, 5 * px, solid(Palette.ink));
      canvas.drawCircle(a, 3.5 * px, solid(Palette.accent));
    }

    canvas.restore();
    if (night > 0) {
      canvas.drawRect(Offset.zero & size, solid(const Color(0xFF050A12), night * 0.35));
    }
  }

  @override
  bool shouldRepaint(_ChapterPainter old) =>
      !identical(old.frame, frame) ||
      !identical(old.jewels, jewels) ||
      !identical(old.leaders, leaders) ||
      old.origin != origin ||
      old.night != night ||
      old.selected != selected ||
      old.ctrl != ctrl;
}

// ---------------------------------------------------------------- виджет карты главы

class _View {
  const _View(this.scale, this.rect);
  final double scale;
  final Rect rect;
}

/// Карта одной главы: витраж, вода, лента зон, места, герой и значки слоёв.
/// Жесты — только в пределах главы. [fitTick] — показать главу целиком, [heroTick] — к герою.
/// [popupBuilder] строит содержимое карточки выбранного значка (рамку и стрелку рисует карта).
class ChapterMapView extends StatefulWidget {
  const ChapterMapView({
    super.key,
    required this.content,
    required this.ch,
    required this.heroPos,
    required this.marks,
    required this.selectedId,
    required this.onSelect,
    required this.popupBuilder,
    this.night = 0,
    this.fitTick = 0,
    this.heroTick = 0,
    this.focusHeroOnStart = false,
    this.topInset = 72,
    this.bottomInset = 64,
  });

  final GameContent content;
  final int ch;
  final double heroPos;
  final List<MapMark> marks;
  final String? selectedId;
  final ValueChanged<String?> onSelect;
  final Widget? Function(BuildContext context, String id) popupBuilder;
  final double night;
  final int fitTick;
  final int heroTick;

  /// Первый показ — сразу у героя (кнопка «К герою» из другой главы), иначе вся глава.
  final bool focusHeroOnStart;
  final double topInset;
  final double bottomInset;

  @override
  State<ChapterMapView> createState() => _ChapterMapViewState();
}

class _ChapterMapViewState extends State<ChapterMapView> {
  static const _markerSize = 34.0;
  final _ctrl = TransformationController();
  Size? _vp;
  int? _lastFit;
  int? _lastHero;
  bool _ready = false;

  _Frame? _frame;
  List<_Jewel>? _jewels;
  double? _jewelsHero;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  RouteLine get _line => RouteLine.of(widget.content);
  ChapterGeo get _geo => ChapterGeo.of(widget.content, widget.ch);

  _View _viewFor(Size vp) {
    final b = _geo.bounds;
    final freeW = math.max(40.0, vp.width - 56);
    final freeH = math.max(40.0, vp.height - widget.topInset - widget.bottomInset - 24);
    final bw = math.max(b.width, 1.0);
    final bh = math.max(b.height, 1.0);
    final s = math.min(freeW / bw, freeH / bh);
    final left = b.center.dx - vp.width / 2 / s;
    final top = b.center.dy - (widget.topInset + 12 + freeH / 2) / s;
    return _View(s, Rect.fromLTWH(left, top, vp.width / s, vp.height / s));
  }

  void _setMatrix(double s, double tx, double ty) {
    _ctrl.value = Matrix4.identity()
      ..setEntry(0, 0, s)
      ..setEntry(1, 1, s)
      ..setEntry(2, 2, s)
      ..setEntry(0, 3, tx)
      ..setEntry(1, 3, ty);
  }

  void _fit(_View v) => _setMatrix(v.scale, 0, 0);

  void _toHero(_View v, Size vp) {
    final cur = _ctrl.value.getMaxScaleOnAxis();
    final sh = math.min(v.scale * 7, math.max(v.scale * 2.4, cur));
    final hp = _line.at(widget.heroPos) - v.rect.topLeft;
    final w = v.rect.width * sh;
    final h = v.rect.height * sh;
    final tx = (vp.width / 2 - hp.dx * sh).clamp(math.min(0.0, vp.width - w), 0.0).toDouble();
    final ty = (vp.height / 2 - hp.dy * sh).clamp(math.min(0.0, vp.height - h), 0.0).toDouble();
    _setMatrix(sh, tx, ty);
  }

  bool get _heroHere {
    final g = _geo;
    return widget.heroPos >= g.start - 1 && widget.heroPos <= g.end + 1;
  }

  _Frame _frameFor() {
    final f = _frame;
    if (f != null && f.hero == widget.heroPos) return f;
    final g = _geo;
    final line = _line;
    final hp = widget.heroPos.clamp(g.start, g.end).toDouble();
    final segs = <(Path, Color)>[];
    for (var i = 0; i < g.segs.length && i < g.segPaths.length; i++) {
      final s = g.segs[i];
      if (s.b <= hp) {
        segs.add((g.segPaths[i], Palette.zone(s.zone)));
      } else if (s.a < hp) {
        segs.add((line.subPath(s.a, hp), Palette.zone(s.zone)));
      }
    }
    final dir = line.dirAt(widget.heroPos);
    final made = _Frame(
      widget.heroPos,
      g.pictureFor(widget.heroPos),
      segs,
      hp > g.start + 1 ? line.subPath(g.start, hp) : null,
      line.at(widget.heroPos),
      Offset(dir.dy, -dir.dx),
      _heroHere,
    );
    _frame = made;
    return made;
  }

  List<_Jewel> _jewelsFor() {
    final j = _jewels;
    if (j != null && _jewelsHero == widget.heroPos) return j;
    final w = widget.content.world;
    final g = _geo;
    final line = _line;
    final out = <_Jewel>[];
    for (final p in w.places) {
      if (p['virtual'] == true) continue;
      final at = w.posOf['${p['id']}'];
      if (at == null || at < g.start - 1 || at > g.end + 1) continue;
      final kind = p['kind'];
      out.add(_Jewel(line.at(at), kind == 'city' || kind == 'start' || kind == 'finish', at <= widget.heroPos + 1));
    }
    _jewels = out;
    _jewelsHero = widget.heroPos;
    return out;
  }

  Offset _screenOf(MapMark mk, Offset origin) => MatrixUtils.transformPoint(_ctrl.value, mk.at - origin) + mk.shift;

  void _onTap(TapUpDetails d, Offset origin) {
    final screen = MatrixUtils.transformPoint(_ctrl.value, d.localPosition);
    String? best;
    var bestD = 24.0;
    for (final mk in widget.marks) {
      if (!mk.tappable) continue;
      final dd = (_screenOf(mk, origin) - screen).distance;
      if (dd < bestD) {
        bestD = dd;
        best = mk.id;
      }
    }
    widget.onSelect(best);
  }

  MapMark? get _selectedMark {
    final id = widget.selectedId;
    if (id == null) return null;
    for (final mk in widget.marks) {
      if (mk.id == id) return mk;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      // В неограниченной оси (ListView, Column без Expanded) вид получил бы бесконечный размер
      // и масштаб NaN — карта пустая. Берём ширину экрана / запасную высоту и задаём размер явно.
      final vp = Size(
        c.hasBoundedWidth ? c.maxWidth : MediaQuery.sizeOf(context).width,
        c.hasBoundedHeight ? c.maxHeight : 320,
      );
      final v = _viewFor(vp);
      final origin = v.rect.topLeft;
      final changed = _vp != vp || _lastFit != widget.fitTick || _lastHero != widget.heroTick;
      if (changed) {
        final heroOnly = _vp == null ? widget.focusHeroOnStart : (_vp == vp && _lastFit == widget.fitTick);
        _vp = vp;
        _lastFit = widget.fitTick;
        _lastHero = widget.heroTick;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          if (heroOnly && _heroHere) {
            _toHero(v, vp);
          } else {
            _fit(v);
          }
          if (!_ready) setState(() => _ready = true);
        });
      }
      final frame = _frameFor();
      final sel = _selectedMark;
      final leaders = <MapMark>[for (final mk in widget.marks) if (mk.leader) mk];
      final heroMark = MapMark(
        id: '_hero',
        at: frame.heroPt,
        shift: frame.heroNormal * _ChapterPainter._hero,
        child: const Art('assets/art/hero/sergey_marker.svg',
            width: _markerSize, height: _markerSize, fit: BoxFit.contain),
      );
      final marks = <MapMark>[...widget.marks, if (frame.heroHere) heroMark];
      return SizedBox.fromSize(
        size: vp,
        child: ClipRect(
          child: Opacity(
            opacity: _ready ? 1 : 0,
            child: Stack(
              children: [
                Positioned.fill(
                  child: InteractiveViewer(
                    transformationController: _ctrl,
                    constrained: false,
                    minScale: v.scale,
                    maxScale: v.scale * 7,
                    boundaryMargin: EdgeInsets.zero,
                    onInteractionStart: (_) {
                      if (widget.selectedId != null) widget.onSelect(null);
                    },
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTapUp: (d) => _onTap(d, origin),
                      child: SizedBox(
                        width: v.rect.width,
                        height: v.rect.height,
                        child: RepaintBoundary(
                          child: CustomPaint(
                            painter: _ChapterPainter(
                              line: _line,
                              geo: _geo,
                              frame: frame,
                              jewels: _jewelsFor(),
                              leaders: leaders,
                              origin: origin,
                              ctrl: _ctrl,
                              night: widget.night,
                              // кольцо — только у значков прямо на точке (место, ночёвка)
                              selected: (sel == null || sel.shift != Offset.zero) ? null : sel.at,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: Flow(
                      delegate: _MarksFlow(_ctrl, marks, origin),
                      children: [for (final mk in marks) mk.child],
                    ),
                  ),
                ),
                if (sel != null)
                  Positioned.fill(
                    child: ValueListenableBuilder<Matrix4>(
                      valueListenable: _ctrl,
                      builder: (context, m, _) => _popup(context, sel, origin, vp),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    });
  }

  Widget _popup(BuildContext context, MapMark sel, Offset origin, Size vp) {
    final body = widget.popupBuilder(context, sel.id);
    if (body == null) return const SizedBox.shrink();
    final p = _screenOf(sel, origin);
    final width = math.min(220.0, vp.width - 16);
    final left = (p.dx - width / 2).clamp(8.0, math.max(8.0, vp.width - 8 - width)).toDouble();
    final above = p.dy > vp.height * 0.45;
    final ax = (p.dx - left).clamp(16.0, width - 16).toDouble();
    final card = _PopCard(arrowX: ax, arrowDown: above, child: body);
    // Карточка в Stack поверх всего экрана карты: тап мимо неё уходит в карту и закрывает её.
    return Stack(
      clipBehavior: Clip.none,
      children: [
        if (above)
          Positioned(left: left, width: width, bottom: vp.height - p.dy + 16, child: card)
        else
          Positioned(left: left, width: width, top: p.dy + 16, child: card),
      ],
    );
  }
}

/// Всплывающая карточка: #16222F, рамка #2C4560, радиус 14, стрелка к значку.
class _PopCard extends StatelessWidget {
  const _PopCard({required this.arrowX, required this.arrowDown, required this.child});

  final double arrowX;
  final bool arrowDown;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    const side = BorderSide(color: Palette.chipLine);
    final arrow = Transform.rotate(
      angle: math.pi / 4,
      child: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: Palette.inkRaised,
          border: arrowDown ? const Border(right: side, bottom: side) : const Border(left: side, top: side),
        ),
      ),
    );
    return GestureDetector(
      onTap: () {},
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(11, 10, 11, 10),
            decoration: BoxDecoration(
              color: Palette.inkRaised,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Palette.chipLine),
              boxShadow: const [BoxShadow(color: Color(0x99000000), blurRadius: 28, offset: Offset(0, 12))],
            ),
            child: child,
          ),
          if (arrowDown)
            Positioned(left: arrowX - 6, bottom: -6, child: arrow)
          else
            Positioned(left: arrowX - 6, top: -6, child: arrow),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- мини-карта всего пути

class _MiniFit {
  _MiniFit(Rect b, Size size) : bounds = b {
    const pad = 7.0;
    final w = size.width - pad * 2;
    final h = size.height - pad - 18;
    k = math.min(w / math.max(b.width, 1e-6), h / math.max(b.height, 1e-6));
    ox = pad + (w - b.width * k) / 2;
    oy = pad + (h - b.height * k) / 2;
  }

  final Rect bounds;
  late final double k;
  late final double ox;
  late final double oy;

  Offset toUnits(Offset s) => Offset(bounds.left + (s.dx - ox) / k, bounds.top + (s.dy - oy) / k);
}

const _miniSize = Size(74, 112);
const _miniOther = Color(0xFF56677A);

/// Мини-карта всего пути: маршрут по главам, рамка открытой главы, точка героя и финиш.
/// Тап выбирает главу по ближайшему месту маршрута.
class MiniRouteMap extends StatelessWidget {
  const MiniRouteMap({
    super.key,
    required this.content,
    required this.viewCh,
    required this.heroPos,
    required this.label,
    required this.semanticsLabel,
    required this.onPick,
  });

  final GameContent content;
  final int viewCh;
  final double heroPos;
  final String label;
  final String semanticsLabel;
  final ValueChanged<int> onPick;

  @override
  Widget build(BuildContext context) {
    final line = RouteLine.of(content);
    return Semantics(
      button: true,
      label: semanticsLabel,
      excludeSemantics: true,
      child: GestureDetector(
        onTapUp: (d) {
          final u = _MiniFit(line.bounds, _miniSize).toUnits(d.localPosition);
          final (_, pos) = line.nearest(u);
          onPick(content.world.chapterAt(pos));
        },
        child: Container(
          width: _miniSize.width,
          height: _miniSize.height,
          decoration: BoxDecoration(
            color: const Color(0xF00E1621),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Palette.chipLine),
            boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 16, offset: Offset(0, 6))],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(11),
            child: Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _MiniPainter(line: line, world: content.world, viewCh: viewCh, heroPos: heroPos),
                  ),
                ),
                Positioned(
                  left: 2,
                  right: 2,
                  bottom: 4,
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.fade,
                    softWrap: false,
                    style: const TextStyle(fontSize: 9, color: Palette.parchmentDim),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MiniPainter extends CustomPainter {
  _MiniPainter({required this.line, required this.world, required this.viewCh, required this.heroPos});

  final RouteLine line;
  final World world;
  final int viewCh;
  final double heroPos;

  @override
  void paint(Canvas canvas, Size size) {
    final f = _MiniFit(line.bounds, size);
    final k = f.k;
    canvas.save();
    canvas.translate(f.ox - line.bounds.left * k, f.oy - line.bounds.top * k);
    canvas.scale(k, k);
    final water = solid(const Color(0xFF1D4A66), 0.8);
    for (final p in line.water) {
      canvas.drawPath(p, water);
    }
    for (final c in world.chapters) {
      final id = toI(c['id']);
      if (id == viewCh) continue;
      canvas.drawPath(line.chapterPath(world, id), stroke(1.6 / k, _miniOther));
    }
    canvas.drawPath(line.chapterPath(world, viewCh), stroke(2.6 / k, Palette.accent));
    final r = line.chapterRect(world, viewCh).inflate(3 / k);
    canvas.drawRect(r, stroke(1 / k, Palette.parchment)..strokeJoin = StrokeJoin.miter);
    final fin = line.pts.isEmpty ? Offset.zero : line.pts.last;
    canvas.drawCircle(fin, 2.4 / k, solid(Palette.parchment));
    final h = line.at(heroPos);
    canvas.drawCircle(h, 2.6 / k, solid(Palette.accent));
    canvas.drawCircle(h, 2.6 / k, stroke(1 / k));
    canvas.restore();
  }

  @override
  bool shouldRepaint(_MiniPainter old) =>
      !identical(old.line, line) || old.viewCh != viewCh || old.heroPos != heroPos;
}

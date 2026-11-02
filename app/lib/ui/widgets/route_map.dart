// Своя иллюстрированная карта: море, озёра, реки, границы, линия маршрута и герой.
// Пройденный участок — бирюзовая линия со свечением, оставшийся — приглушённый серый пунктир;
// граница между ними — позиция героя. Иконка героя рисуется поверх карты и не меняет размер
// при масштабировании: она сдвинута в сторону от линии, чтобы не закрывать путь.

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../data/content_repository.dart';
import '../../engine/world.dart';
import '../theme/tokens.dart';
import 'common.dart';

/// Проекция Меркатора в «единицы карты» шириной [width].
class MapProjection {
  MapProjection(this.bbox, {this.width = 1000}) {
    _y0 = _merc(bbox[1]);
    _y1 = _merc(bbox[3]);
    final lonSpan = (bbox[2] - bbox[0]) * math.pi / 180;
    height = width * (_y1 - _y0) / lonSpan;
  }

  final List<double> bbox;
  final double width;
  late final double height;
  late final double _y0;
  late final double _y1;

  static double _merc(double lat) => math.log(math.tan(math.pi / 4 + lat * math.pi / 360));

  Offset project(double lon, double lat) => Offset(
        (lon - bbox[0]) / (bbox[2] - bbox[0]) * width,
        (1 - (_merc(lat) - _y0) / (_y1 - _y0)) * height,
      );
}

/// Положение героя на линии маршрута по игровым метрам.
class RouteGeometry {
  RouteGeometry(this.content, this.proj) {
    final route = content.map.route;
    points = [for (final p in route) proj.project(p[0], p[1])];
    cum = [0];
    for (var i = 1; i < route.length; i++) {
      cum.add(cum.last + _hav(route[i - 1], route[i]));
    }
    // Привязка реальных точек маршрута к вершинам линии (по порядку)
    var from = 0;
    for (final p in content.world.places) {
      if (p['virtual'] == true) continue;
      final lon = toD(p['lon']);
      final lat = toD(p['lat']);
      var best = from;
      var bestD = double.infinity;
      for (var i = from; i < route.length; i++) {
        final d = (route[i][0] - lon) * (route[i][0] - lon) + (route[i][1] - lat) * (route[i][1] - lat);
        if (d < bestD) {
          bestD = d;
          best = i;
        }
      }
      anchors.add((content.world.posOf[p['id']]!, best));
      from = best;
    }
  }

  final GameContent content;
  final MapProjection proj;
  late final List<Offset> points;
  late final List<double> cum;
  final List<(double, int)> anchors = [];

  static double _hav(List<double> a, List<double> b) {
    const r = 6371000.0;
    final p1 = a[1] * math.pi / 180;
    final p2 = b[1] * math.pi / 180;
    final dl = (b[0] - a[0]) * math.pi / 180;
    final h = math.pow(math.sin((p2 - p1) / 2), 2) + math.cos(p1) * math.cos(p2) * math.pow(math.sin(dl / 2), 2);
    return 2 * r * math.asin(math.sqrt(h));
  }

  /// Длина линии (в её собственных метрах), соответствующая игровой позиции.
  double lineMetersAt(double pos) {
    if (anchors.isEmpty) return 0;
    for (var i = 0; i + 1 < anchors.length; i++) {
      final (pa, ia) = anchors[i];
      final (pb, ib) = anchors[i + 1];
      if (pos <= pb || i + 2 == anchors.length) {
        final t = pb == pa ? 0.0 : ((pos - pa) / (pb - pa)).clamp(0.0, 1.0);
        return cum[ia] + (cum[ib] - cum[ia]) * t;
      }
    }
    return cum.last;
  }

  Offset pointAtLine(double m) {
    if (points.length < 2) return points.isEmpty ? Offset.zero : points.first;
    if (m <= 0) return points.first;
    for (var i = 1; i < points.length; i++) {
      if (cum[i] >= m) {
        final seg = cum[i] - cum[i - 1];
        final f = seg == 0 ? 0.0 : (m - cum[i - 1]) / seg;
        return Offset.lerp(points[i - 1], points[i], f)!;
      }
    }
    return points.last;
  }

  Offset heroPoint(double pos) => pointAtLine(lineMetersAt(pos));

  /// Единичный вектор направления пути (в единицах карты) в точке линии [m]:
  /// берётся отрезок чуть позади и чуть впереди, чтобы излом на вершине не дёргал направление.
  Offset directionAtLine(double m) {
    if (points.length < 2) return const Offset(1, 0);
    final span = cum.last * 0.01;
    final a = pointAtLine(m - span);
    final b = pointAtLine(m + span);
    final d = b - a;
    final len = d.distance;
    if (len < 1e-6) return const Offset(1, 0);
    return d / len;
  }
}

class _MapPainter extends CustomPainter {
  _MapPainter(this.content, this.geo, this.heroPos, this.night, this.ctrl) : super(repaint: ctrl);

  final GameContent content;
  final RouteGeometry geo;
  final double heroPos;
  final double night; // 0..1 затемнение по времени суток
  final TransformationController ctrl;

  Path _path(List<List<double>> pts, {bool close = false}) {
    final p = Path();
    for (var i = 0; i < pts.length; i++) {
      final o = geo.proj.project(pts[i][0], pts[i][1]);
      if (i == 0) {
        p.moveTo(o.dx, o.dy);
      } else {
        p.lineTo(o.dx, o.dy);
      }
    }
    if (close) p.close();
    return p;
  }

  /// Пунктир вдоль [src]: штрих [dash] и промежуток [gap] (в единицах карты).
  /// Число штрихов ограничено, чтобы при сильном приближении рисунок не тормозил.
  Path _dashed(Path src, double dash, double gap) {
    final out = Path();
    for (final metric in src.computeMetrics()) {
      final len = metric.length;
      final period = math.max(dash + gap, len / 1500);
      final on = period * dash / (dash + gap);
      var d = 0.0;
      while (d < len) {
        out.addPath(metric.extractPath(d, math.min(d + on, len)), Offset.zero);
        d += period;
      }
    }
    return out;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final scale = ctrl.value.getMaxScaleOnAxis();
    // Единиц карты в одном логическом пикселе экрана: линии и подписи не раздуваются при приближении.
    final px = scale > 0.0001 ? 1.0 / scale : 1.0;

    final layers = content.map.layers;
    final seaFill = Paint()..color = Palette.sea;
    final shore = Paint()
      ..color = Palette.teal.withAlpha(90)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2 * px;
    // Онлайн-карта даёт сушу (фон — море), резервная — море (фон — суша)
    final land = layers['land'] ?? const <List<List<double>>>[];
    canvas.drawRect(Offset.zero & size, Paint()..color = land.isNotEmpty ? Palette.sea : Palette.land);
    for (final poly in land) {
      final p = _path(poly, close: true);
      canvas.drawPath(p, Paint()..color = Palette.land);
      canvas.drawPath(p, shore);
    }
    for (final poly in layers['sea'] ?? const <List<List<double>>>[]) {
      final p = _path(poly, close: true);
      canvas.drawPath(p, seaFill);
      canvas.drawPath(p, shore);
    }
    for (final poly in layers['lakes'] ?? const <List<List<double>>>[]) {
      final p = _path(poly, close: true);
      canvas.drawPath(p, seaFill);
      canvas.drawPath(p, shore);
    }
    final river = Paint()
      ..color = Palette.teal.withAlpha(120)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0 * px;
    for (final line in layers['rivers'] ?? const <List<List<double>>>[]) {
      canvas.drawPath(_path(line), river);
    }
    final border = Paint()
      ..color = Palette.parchmentDim.withAlpha(60)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0 * px;
    for (final line in layers['borders'] ?? const <List<List<double>>>[]) {
      canvas.drawPath(_path(line), border);
    }

    // Граница пройденного и оставшегося — позиция героя (по доле пройденного пути)
    final walkedM = geo.lineMetersAt(heroPos);
    final heroPt = geo.pointAtLine(walkedM);

    // Оставшийся путь: от героя до финиша — приглушённый серый пунктир
    final rest = Path()..moveTo(heroPt.dx, heroPt.dy);
    for (var i = 0; i < geo.points.length; i++) {
      if (geo.cum[i] <= walkedM) continue;
      rest.lineTo(geo.points[i].dx, geo.points[i].dy);
    }
    canvas.drawPath(
      _dashed(rest, 6 * px, 5 * px),
      Paint()
        ..color = Palette.parchmentDim.withAlpha(170)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.8 * px,
    );

    // Пройденный путь: бирюзовая линия с мягким свечением (три слоя, без размытия)
    final walked = Path();
    var started = false;
    for (var i = 0; i < geo.points.length; i++) {
      if (geo.cum[i] > walkedM) break;
      final o = geo.points[i];
      if (!started) {
        walked.moveTo(o.dx, o.dy);
        started = true;
      } else {
        walked.lineTo(o.dx, o.dy);
      }
    }
    if (started) {
      walked.lineTo(heroPt.dx, heroPt.dy);
      Paint glow(double width, int alpha) => Paint()
        ..color = Palette.accent.withAlpha(alpha)
        ..style = PaintingStyle.stroke
        ..strokeWidth = width * px
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;
      canvas.drawPath(walked, glow(9, 34));
      canvas.drawPath(walked, glow(5.5, 70));
      canvas.drawPath(walked, glow(2.6, 255));
    }

    // Точки маршрута
    for (final p in content.world.places) {
      if (p['virtual'] == true) continue;
      final o = geo.proj.project(toD(p['lon']), toD(p['lat']));
      final reached = content.world.posOf[p['id']]! <= heroPos + 1;
      final kind = p['kind'];
      final big = kind == 'city' || kind == 'start' || kind == 'finish';
      final r = (big ? 4.5 : 3.0) * px;
      canvas.drawCircle(o, r + 1.5 * px, Paint()..color = Palette.ink);
      canvas.drawCircle(o, r, Paint()..color = reached ? Palette.accent : Palette.parchmentDim);
      // На общем плане подписаны только крупные города: мелкие слились бы в кашу
      if (kind != 'village' && (big || scale >= 0.6)) {
        final tp = TextPainter(
          text: TextSpan(
            text: '${p['name']}',
            style: TextStyle(
              color: reached ? Palette.parchment : Palette.parchmentDim,
              fontSize: (big ? 11 : 9) * px,
              shadows: [Shadow(color: Palette.ink, blurRadius: 3 * px)],
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, o + Offset(6 * px, -6 * px));
      }
    }

    // Ночь — мягкое затемнение
    if (night > 0) {
      canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xFF050A12).withAlpha((night * 90).round()));
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.heroPos != heroPos || old.night != night || old.ctrl != ctrl;
}

/// Выноска: точка на линии пути и тонкая связь с иконкой героя (в экранных пикселях).
class _PinPainter extends CustomPainter {
  _PinPainter(this.anchor, this.center);

  final Offset anchor;
  final Offset center;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawLine(
      anchor,
      center,
      Paint()
        ..color = Palette.accent
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
    canvas.drawCircle(anchor, 5, Paint()..color = Palette.ink);
    canvas.drawCircle(anchor, 3.5, Paint()..color = Palette.accent);
  }

  @override
  bool shouldRepaint(_PinPainter old) => old.anchor != anchor || old.center != center;
}

/// Карта с героем. [near] — крупный план вокруг героя, иначе весь путь.
/// [recenterTick] — при увеличении карта возвращается к герою.
class RouteMap extends StatefulWidget {
  const RouteMap({
    super.key,
    required this.content,
    required this.heroPos,
    required this.near,
    this.night = 0,
    this.recenterTick = 0,
  });

  final GameContent content;
  final double heroPos;
  final bool near;
  final double night;
  final int recenterTick;

  @override
  State<RouteMap> createState() => _RouteMapState();
}

class _RouteMapState extends State<RouteMap> {
  // Иконка героя: размер и сдвиг от линии — в логических пикселях экрана, не зависят от масштаба.
  static const double _markerSize = 32;
  static const double _markerOffset = 16;
  // Масштаб «Рядом»: чем дальше соседние места, тем мельче, но не крупнее _maxNearScale.
  static const double _minNearScale = 0.9;
  static const double _maxNearScale = 2.3;

  late final MapProjection _proj = MapProjection(widget.content.map.bbox);
  late final RouteGeometry _geo = RouteGeometry(widget.content, _proj);
  final _ctrl = TransformationController();
  Size? _viewport;
  bool? _lastNear;
  double? _lastPos;
  int? _lastTick;
  bool _userMoved = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  /// Прямоугольник, в который попадают предыдущее место, герой и следующее место (в единицах карты).
  Rect _nearRect(Offset hero) {
    final world = widget.content.world;
    final pos = widget.heroPos;
    Offset? prev;
    Offset? next;
    for (final p in world.places) {
      if (p['virtual'] == true) continue;
      final at = world.posOf[p['id']];
      if (at == null) continue;
      final o = _proj.project(toD(p['lon']), toD(p['lat']));
      if (at <= pos + 1) {
        prev = o;
      } else {
        next = o;
        break;
      }
    }
    var rect = Rect.fromPoints(hero, hero);
    if (prev != null) rect = rect.expandToInclude(Rect.fromPoints(prev, prev));
    if (next != null) rect = rect.expandToInclude(Rect.fromPoints(next, next));
    return rect;
  }

  void _focus(Size vp) {
    final hero = _geo.heroPoint(widget.heroPos);
    double s;
    Offset center;
    if (widget.near) {
      // Участок между двумя соседними местами и немного вокруг
      final r = _nearRect(hero);
      const pad = 22.0;
      final fit = math.min(vp.width / (r.width + pad * 2), vp.height / (r.height + pad * 2));
      s = math.max(_minNearScale, math.min(_maxNearScale, fit));
      center = r.center;
    } else {
      // весь маршрут по высоте видимой области
      final ys = _geo.points.map((p) => p.dy);
      final xs = _geo.points.map((p) => p.dx);
      final minY = ys.reduce(math.min) - 30;
      final maxY = ys.reduce(math.max) + 30;
      final minX = xs.reduce(math.min) - 60;
      final maxX = xs.reduce(math.max) + 60;
      s = math.min(vp.height / (maxY - minY), vp.width / (maxX - minX));
      center = Offset((minX + maxX) / 2, (minY + maxY) / 2);
    }
    final tx = vp.width / 2 - center.dx * s;
    final ty = vp.height / 2 - center.dy * s;
    _ctrl.value = Matrix4.identity()
      ..setEntry(0, 0, s)
      ..setEntry(1, 1, s)
      ..setEntry(0, 3, tx)
      ..setEntry(1, 3, ty);
  }

  /// Иконка героя и выноска поверх карты. Положение берётся из текущего преобразования карты,
  /// поэтому размер иконки и сдвиг (по нормали к направлению пути) постоянны при любом масштабе.
  Widget _heroOverlay(Matrix4 m) {
    final walkedM = _geo.lineMetersAt(widget.heroPos);
    final anchor = MatrixUtils.transformPoint(m, _geo.pointAtLine(walkedM));
    final dir = _geo.directionAtLine(walkedM);
    // Нормаль слева от направления движения (экранные оси: y вниз)
    final normal = Offset(dir.dy, -dir.dx);
    final center = anchor + normal * _markerOffset;
    return Stack(
      children: [
        Positioned.fill(child: CustomPaint(painter: _PinPainter(anchor, center))),
        Positioned(
          left: center.dx - _markerSize / 2,
          top: center.dy - _markerSize / 2,
          width: _markerSize,
          height: _markerSize,
          child: const Art('assets/art/hero/sergey_marker.svg', width: _markerSize, height: _markerSize, fit: BoxFit.contain),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final vp = Size(c.maxWidth, c.maxHeight);
      final sizeChanged = _viewport != vp || _lastNear != widget.near || _lastTick != widget.recenterTick;
      // Пока игрок сам двигал карту, она не прыгает за героем; кнопка «К герою» возвращает вид.
      final moved = _lastPos == null || (widget.near && !_userMoved && (widget.heroPos - _lastPos!).abs() > 300);
      if (sizeChanged || moved) {
        if (sizeChanged) _userMoved = false;
        _viewport = vp;
        _lastNear = widget.near;
        _lastTick = widget.recenterTick;
        _lastPos = widget.heroPos;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _focus(vp);
        });
      }
      return ClipRect(
        child: Stack(
          children: [
            Positioned.fill(
              child: InteractiveViewer(
                transformationController: _ctrl,
                constrained: false,
                minScale: 0.05,
                maxScale: 12,
                boundaryMargin: const EdgeInsets.all(400),
                onInteractionStart: (_) {
                  _userMoved = true;
                },
                child: SizedBox(
                  width: _proj.width,
                  height: _proj.height,
                  child: RepaintBoundary(
                    child: CustomPaint(
                      painter: _MapPainter(widget.content, _geo, widget.heroPos, widget.night, _ctrl),
                    ),
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: IgnorePointer(
                child: ValueListenableBuilder<Matrix4>(
                  valueListenable: _ctrl,
                  builder: (context, m, _) => _heroOverlay(m),
                ),
              ),
            ),
          ],
        ),
      );
    });
  }
}

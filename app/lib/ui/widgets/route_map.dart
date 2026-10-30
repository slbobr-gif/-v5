// Своя иллюстрированная карта: море, озёра, реки, границы, линия маршрута и герой.

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
}

class _MapPainter extends CustomPainter {
  _MapPainter(this.content, this.geo, this.heroPos, this.night);

  final GameContent content;
  final RouteGeometry geo;
  final double heroPos;
  final double night; // 0..1 затемнение по времени суток

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

  @override
  void paint(Canvas canvas, Size size) {
    final layers = content.map.layers;
    final seaFill = Paint()..color = Palette.sea;
    final shore = Paint()
      ..color = Palette.teal.withAlpha(90)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
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
      ..strokeWidth = 1.0;
    for (final line in layers['rivers'] ?? const <List<List<double>>>[]) {
      canvas.drawPath(_path(line), river);
    }
    final border = Paint()
      ..color = Palette.parchmentDim.withAlpha(60)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    for (final line in layers['borders'] ?? const <List<List<double>>>[]) {
      canvas.drawPath(_path(line), border);
    }

    // Линия маршрута: вся — пунктиром пергамента, пройденная — золотом
    final all = Path();
    for (var i = 0; i < geo.points.length; i++) {
      final o = geo.points[i];
      if (i == 0) {
        all.moveTo(o.dx, o.dy);
      } else {
        all.lineTo(o.dx, o.dy);
      }
    }
    canvas.drawPath(
      all,
      Paint()
        ..color = Palette.parchment.withAlpha(70)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
    final walkedM = geo.lineMetersAt(heroPos);
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
    final hero = geo.pointAtLine(walkedM);
    if (started) walked.lineTo(hero.dx, hero.dy);
    canvas.drawPath(
      walked,
      Paint()
        ..color = Palette.gold
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.2
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );

    // Точки маршрута
    for (final p in content.world.places) {
      if (p['virtual'] == true) continue;
      final o = geo.proj.project(toD(p['lon']), toD(p['lat']));
      final reached = content.world.posOf[p['id']]! <= heroPos + 1;
      final kind = p['kind'];
      final r = (kind == 'city' || kind == 'start' || kind == 'finish') ? 4.5 : 3.0;
      canvas.drawCircle(o, r + 1.5, Paint()..color = Palette.ink);
      canvas.drawCircle(o, r, Paint()..color = reached ? Palette.gold : Palette.parchmentDim);
      if (kind != 'village') {
        final tp = TextPainter(
          text: TextSpan(
            text: '${p['name']}',
            style: TextStyle(
              color: reached ? Palette.parchment : Palette.parchmentDim,
              fontSize: kind == 'city' || kind == 'finish' ? 11 : 9,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, o + const Offset(6, -6));
      }
    }

    // Ночь — мягкое затемнение
    if (night > 0) {
      canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xFF050A12).withAlpha((night * 90).round()));
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.heroPos != heroPos || old.night != night;
}

/// Карта с героем. [near] — крупный план вокруг героя, иначе весь путь.
class RouteMap extends StatefulWidget {
  const RouteMap({super.key, required this.content, required this.heroPos, required this.near, this.night = 0});

  final GameContent content;
  final double heroPos;
  final bool near;
  final double night;

  @override
  State<RouteMap> createState() => _RouteMapState();
}

class _RouteMapState extends State<RouteMap> {
  late final MapProjection _proj = MapProjection(widget.content.map.bbox);
  late final RouteGeometry _geo = RouteGeometry(widget.content, _proj);
  final _ctrl = TransformationController();
  Size? _viewport;
  bool? _lastNear;
  double? _lastPos;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _focus(Size vp) {
    final hero = _geo.heroPoint(widget.heroPos);
    double s;
    Offset center;
    if (widget.near) {
      s = 3.2;
      center = hero;
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

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final vp = Size(c.maxWidth, c.maxHeight);
      final moved = _lastPos == null || (widget.near && (widget.heroPos - _lastPos!).abs() > 300);
      if (_viewport != vp || _lastNear != widget.near || moved) {
        _viewport = vp;
        _lastNear = widget.near;
        _lastPos = widget.heroPos;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _focus(vp);
        });
      }
      final hero = _geo.heroPoint(widget.heroPos);
      return ClipRect(
        child: InteractiveViewer(
          transformationController: _ctrl,
          constrained: false,
          minScale: 0.05,
          maxScale: 12,
          boundaryMargin: const EdgeInsets.all(400),
          child: SizedBox(
            width: _proj.width,
            height: _proj.height,
            child: Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(painter: _MapPainter(widget.content, _geo, widget.heroPos, widget.night)),
                ),
                Positioned(
                  left: hero.dx - 9,
                  top: hero.dy - 18,
                  child: const IgnorePointer(
                    child: Art('assets/art/hero/sergey_marker.svg', width: 18, height: 18, fit: BoxFit.contain),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}

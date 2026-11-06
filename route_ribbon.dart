// Карточка «Витражная лента» (заказ v5.3, вариант 14·1): маршрут текущей главы одной полосой стекла.
// Сегменты — зоны пути по реальным расстояниям (balance.json → zones через World.zoneAt),
// пройденное горит, впереди — тёмное стекло, над лентой — места главы и фишка героя.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import 'coach_tour.dart';
import 'common.dart';
import 'glass_paint.dart';
import 'item_icon.dart' show zoneName;

final _num = NumberFormat.decimalPattern('ru');

/// Километры для подписи: до 10 км — с десятыми, дальше — целые с пробелом тысяч.
String ribbonKm(double km) => km < 10 ? km.toStringAsFixed(1).replaceAll('.', ',') : _num.format(km.round());

/// «Москва, Кремль» → «Кремль»: на ленте нужна короткая подпись.
String shortPlaceName(String name) {
  final i = name.lastIndexOf(', ');
  return i >= 0 ? name.substring(i + 2) : name;
}

class RibbonSeg {
  const RibbonSeg(this.a, this.b, this.zone);
  final double a; // м
  final double b; // м
  final String zone;
}

class RibbonPlace {
  const RibbonPlace(this.pos, this.name);
  final double pos; // м
  final String name;
}

/// Данные ленты одной главы (не зависят от героя — считаются один раз на главу).
class RibbonChapter {
  RibbonChapter(this.ch, this.start, this.end, this.segs, this.places);
  final int ch;
  final double start;
  final double end;
  final List<RibbonSeg> segs;
  final List<RibbonPlace> places;

  static World? _world;
  static final Map<int, RibbonChapter> _cache = <int, RibbonChapter>{};

  static RibbonChapter of(World w, int ch) {
    if (!identical(_world, w)) {
      _world = w;
      _cache.clear();
    }
    final hit = _cache[ch];
    if (hit != null) return hit;
    final made = _build(w, ch);
    _cache[ch] = made;
    return made;
  }

  static RibbonChapter _build(World w, int ch) {
    final s = w.chapterStartPos(ch);
    final e = w.chapterEndPos(ch);
    // Границы зон — точные: края радиусов всех мест, попавшие внутрь главы.
    final cuts = <double>[s, e];
    for (final z in w.zonePoints) {
      for (final r in <double>[z.urban, z.outer]) {
        if (r <= 0) continue;
        for (final x in <double>[z.pos - r, z.pos + r]) {
          if (x > s && x < e) cuts.add(x);
        }
      }
    }
    cuts.sort();
    final segs = <RibbonSeg>[];
    for (var i = 0; i + 1 < cuts.length; i++) {
      final a = cuts[i];
      final b = cuts[i + 1];
      if (b - a < 1.0) continue;
      final zone = w.zoneAt((a + b) / 2);
      if (segs.isNotEmpty && segs.last.zone == zone) {
        final last = segs.removeLast();
        segs.add(RibbonSeg(last.a, b, zone));
      } else {
        segs.add(RibbonSeg(a, b, zone));
      }
    }
    final places = <RibbonPlace>[];
    for (final p in w.places) {
      if (p['virtual'] == true) continue;
      final at = w.posOf[p['id']];
      if (at == null || at < s - 1 || at > e + 1) continue;
      places.add(RibbonPlace(at, shortPlaceName('${p['name']}')));
    }
    return RibbonChapter(ch, s, e, segs, places);
  }
}

/// Карточка маршрута главы. [onMap] — открыть полноэкранную карту.
class RouteRibbonCard extends StatelessWidget {
  const RouteRibbonCard({
    super.key,
    required this.world,
    required this.heroPos,
    required this.zone,
    required this.onMap,
  });

  final World world;
  final double heroPos;
  final String zone;
  final VoidCallback onMap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final w = world;
    final ch = w.chapterAt(heroPos);
    final chapter = w.chapterById(ch);
    final data = RibbonChapter.of(w, ch);
    final hero = heroPos.clamp(data.start, data.end).toDouble();
    final toId = '${chapter['to']}';
    final fromName = shortPlaceName('${w.placeById['${chapter['from']}']?['name'] ?? ''}');
    final toName = shortPlaceName('${w.placeById[toId]?['name'] ?? ''}');
    final kmToEnd = math.max(0.0, data.end - hero) / 1000.0;

    RibbonPlace? next;
    RibbonPlace? prev;
    for (final p in data.places) {
      if (p.pos > hero + 1) {
        next ??= p;
      } else {
        prev = p;
      }
    }
    final nextName = next?.name ?? toName;
    final nextKm = ((next?.pos ?? data.end) - hero) / 1000.0;

    final totalKm = w.length / 1000.0;
    final doneKm = math.min(totalKm, math.max(0.0, heroPos) / 1000.0);
    final chapterBounds = <double>[for (final c in w.chapters) w.posOf['${c['to']}'] ?? w.length];

    return Container(
      decoration: cardDecoration(),
      padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l.homeRouteEyebrow(ch, fromName, toName),
                      style: const TextStyle(fontSize: 12, color: Palette.parchmentDim),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text.rich(
                      TextSpan(children: [
                        TextSpan(
                          text: l.homeNextKm(ribbonKm(kmToEnd)),
                          style: const TextStyle(color: Palette.accent),
                        ),
                        const TextSpan(text: ' '),
                        TextSpan(text: l.homeRouteTo(toId)),
                      ]),
                      style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w700, height: 1.15),
                    ),
                    const SizedBox(height: 6),
                    TourAnchor(id: 'zone', child: SwatchChip(label: zoneName(l, zone), color: Palette.zone(zone))),
                    const SizedBox(height: 6),
                    TourAnchor(
                      id: 'next',
                      child: Text(
                        l.homeRouteNextIn(nextName, ribbonKm(math.max(0.0, nextKm))),
                        style: const TextStyle(fontSize: 13, color: Palette.parchmentDim),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: Gap.s),
              AccentChipButton(label: l.tabMap, icon: Icons.map_outlined, onTap: onMap),
            ],
          ),
          const SizedBox(height: 10),
          Semantics(
            label: l.homeRouteA11y(
              ch,
              _num.format(((hero - data.start) / 1000).round()),
              _num.format(((data.end - data.start) / 1000).round()),
              nextName,
            ),
            child: ExcludeSemantics(
              child: SizedBox(
                height: 108,
                child: CustomPaint(
                  size: Size.infinite,
                  painter: _RibbonPainter(
                    data: data,
                    hero: hero,
                    prevName: (prev != null && prev.pos > data.start + 1) ? prev.name : null,
                    startName: data.places.isNotEmpty ? data.places.first.name : fromName,
                    endName: toName,
                    endKmLabel: l.homeNextKm(ribbonKm(kmToEnd)),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 10,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (final z in const ['city', 'suburb', 'wild']) _LegendDot(label: zoneName(l, z), color: Palette.zone(z)),
            ],
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Padding(
              padding: const EdgeInsets.only(top: 2, right: 2),
              child: Text(
                l.homeRouteBright,
                style: const TextStyle(fontSize: 11, color: Palette.parchmentDim, fontStyle: FontStyle.italic),
              ),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 14,
            child: CustomPaint(
              size: Size.infinite,
              painter: _WholePainter(bounds: chapterBounds, length: w.length, hero: heroPos),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  l.homeRouteWhole(_num.format(doneKm.round()), _num.format(totalKm.round())),
                  style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim),
                ),
              ),
              Text(
                l.homeRouteRest(_num.format((totalKm - doneKm).round())),
                style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
            border: Border.all(color: Palette.lead),
          ),
        ),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim)),
      ],
    );
  }
}

// ---------------------------------------------------------------- лента главы

const _darkCity = Color(0xFF141E3A);
const _darkSuburb = Color(0xFF113130);
const _darkWild = Color(0xFF1D1E3A);
const _markerGrey = Color(0xFF7F8CA0);
const _turqGlow = <Color>[Color(0xB33FD6CC), Color(0x383FD6CC), Color(0x003FD6CC)];
// То же свечение с прозрачностью 0.55 (под героем на ленте).
const _turqGlowSoft = <Color>[Color(0x623FD6CC), Color(0x1F3FD6CC), Color(0x003FD6CC)];

List<Color> _litGlass(String zone) => switch (zone) {
      'city' => Glass.indigo,
      'suburb' => Glass.emerald,
      _ => Glass.violet,
    };

Color _darkGlass(String zone) => switch (zone) {
      'city' => _darkCity,
      'suburb' => _darkSuburb,
      _ => _darkWild,
    };

class _RibbonPainter extends CustomPainter {
  _RibbonPainter({
    required this.data,
    required this.hero,
    required this.prevName,
    required this.startName,
    required this.endName,
    required this.endKmLabel,
  });

  final RibbonChapter data;
  final double hero;
  final String? prevName;
  final String startName;
  final String endName;
  final String endKmLabel;

  static const _top = 36.0;
  static const _bot = 60.0;

  @override
  void paint(Canvas canvas, Size size) {
    final wd = size.width;
    final span = math.max(1.0, data.end - data.start);
    double xOf(double pos) => ((pos - data.start) / span).clamp(0.0, 1.0) * wd;
    final hx = xOf(hero);
    const band = Rect.fromLTRB(0, _top, 0, _bot);

    // свечение под героем
    canvas.drawCircle(Offset(hx, 48), 26, radialFill(Offset(hx, 48), 26, _turqGlowSoft, const [0, .55, 1]));

    // стёкла зон: до героя — яркие, после — тёмные
    for (final s in data.segs) {
      final a = xOf(s.a);
      final b = xOf(s.b);
      if (hx > a) _pane(canvas, a, math.min(b, hx), band, lit: true, zone: s.zone);
      if (hx < b) _pane(canvas, math.max(a, hx), b, band, lit: false, zone: s.zone);
    }
    // блик по пройденному
    if (hx > 0) canvas.drawRect(Rect.fromLTWH(0, _top, hx, 3.5), solid(Colors.white, 0.18));

    // места главы
    final places = data.places;
    for (var i = 0; i < places.length; i++) {
      final p = places[i];
      final x = xOf(p.pos);
      final passed = p.pos <= hero + 1;
      final isStart = i == 0 && (p.pos - data.start).abs() < 1;
      final isEnd = (p.pos - data.end).abs() < 1;
      if (isStart) {
        _arch(canvas, 0, 9, 18, passed ? null : _markerGrey);
      } else if (isEnd) {
        _arch(canvas, wd - 9, wd, 18, passed ? null : _markerGrey);
      } else {
        canvas.drawLine(Offset(x, 33), Offset(x, 63), stroke(2.8));
        if (passed) {
          _arch(canvas, x - 3.5, x + 3.5, 21, null);
        } else {
          canvas.drawCircle(Offset(x, 28), 3, solid(_markerGrey));
          canvas.drawCircle(Offset(x, 28), 3, stroke(1.2));
        }
      }
    }

    // фишка героя
    canvas.drawLine(Offset(hx, 30), Offset(hx, 64), stroke(2.2, Palette.accent));
    canvas.drawLine(Offset(hx, 24), Offset(hx, 33), stroke(3));
    canvas.drawLine(Offset(hx, 24), Offset(hx, 33), stroke(1.4, Palette.accent));
    canvas.drawCircle(Offset(hx, 14), 20.9, radialFill(Offset(hx, 14), 20.9, _turqGlow, const [0, .55, 1]));
    final disc = Offset(hx, 14);
    canvas.drawCircle(
      disc,
      11,
      radialFill(Offset(hx - 11 + 22 * 0.34, 14 - 11 + 22 * 0.28), 22 * 0.85, Glass.night, Glass.stops3),
    );
    canvas.drawCircle(disc, 11, stroke(1.6));
    canvas.drawCircle(disc, 9.6, stroke(1.8, Palette.accent));
    paintPawn(canvas, Rect.fromLTWH(hx - 6.8, 5.4, 13.6, 17.1));

    // подписи мест (по приоритету, без наложений)
    final taken = <Rect>[];
    bool free(Rect r) => !taken.any((t) => t.inflate(3).overlaps(r));
    void label(String text, double x, TextStyle st, TextAlign al) {
      if (text.isEmpty) return;
      final r = paintLabel(canvas, text, x, 78, st, align: al, dryRun: true, minX: 0, maxX: wd);
      if (!free(r)) return;
      paintLabel(canvas, text, x, 78, st, align: al, minX: 0, maxX: wd);
      taken.add(r);
    }

    label(endName, wd, const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Palette.parchment),
        TextAlign.right);
    RibbonPlace? next;
    for (final p in places) {
      if (p.pos > hero + 1 && (p.pos - data.end).abs() >= 1) {
        next = p;
        break;
      }
    }
    if (next != null) {
      label(next.name, xOf(next.pos),
          const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Palette.parchment), TextAlign.center);
    }
    label(startName, 0, TextStyle(fontSize: 10.5, color: alpha(Palette.parchment, 0.75)), TextAlign.left);
    final pv = prevName;
    if (pv != null) {
      RibbonPlace? prev;
      for (final p in places) {
        if (p.pos <= hero + 1) prev = p;
      }
      if (prev != null) {
        label(pv, xOf(prev.pos), const TextStyle(fontSize: 10.5, color: Palette.parchmentDim), TextAlign.center);
      }
    }

    // шкала километров: от героя до конца главы
    if (wd - hx > 4) {
      canvas.drawLine(Offset(hx, 88), Offset(wd, 88), stroke(1.4, Palette.parchmentDim, 0.7));
      canvas.drawLine(Offset(hx, 85), Offset(hx, 91), stroke(1.6, Palette.parchmentDim));
      final endR = paintLabel(canvas, endKmLabel, wd, 102,
          const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Palette.accent),
          align: TextAlign.right);
      canvas.drawLine(Offset(wd, 85), Offset(wd, 91), stroke(1.6, Palette.accent));
      final kmTaken = <Rect>[endR];
      for (final p in places) {
        if (p.pos <= hero + 1 || (p.pos - data.end).abs() < 1) continue;
        final x = xOf(p.pos);
        canvas.drawLine(Offset(x, 85), Offset(x, 91), stroke(1.6, Palette.parchmentDim));
        final txt = '${((p.pos - hero) / 1000).round()}';
        const st = TextStyle(fontSize: 11.5, color: Palette.parchmentDim);
        final r = paintLabel(canvas, txt, x, 102, st, dryRun: true, minX: 0, maxX: wd);
        if (kmTaken.any((t) => t.inflate(3).overlaps(r))) continue;
        paintLabel(canvas, txt, x, 102, st, minX: 0, maxX: wd);
        kmTaken.add(r);
      }
    }
  }

  void _pane(Canvas canvas, double a, double b, Rect band, {required bool lit, required String zone}) {
    if (b - a < 0.3) return;
    final r = Rect.fromLTRB(a, band.top, b, band.bottom);
    canvas.drawRect(r, lit ? glassFill(r, _litGlass(zone)) : solid(_darkGlass(zone)));
    // косые свинцовые жилки в длинных стёклах
    final w = b - a;
    if (w > 24) {
      final n = (w / 38).floor();
      final stepX = w / (n + 1);
      for (var i = 1; i <= n; i++) {
        final x = a + stepX * i - 3;
        canvas.drawLine(Offset(x, band.top), Offset(x + 6, band.bottom), stroke(1.1, Glass.lead, 0.85));
      }
    }
    canvas.drawRect(r, stroke(1.3)..strokeCap = StrokeCap.butt);
  }

  /// «Купол» места: от [x0] до [x1], верх на [top], низ на 32. [grey] == null — бирюзовое стекло.
  void _arch(Canvas canvas, double x0, double x1, double top, Color? grey) {
    final w = x1 - x0;
    final shoulder = top + w * 0.6;
    final p = Path()
      ..moveTo(x0, 32)
      ..lineTo(x0, shoulder)
      ..quadraticBezierTo(x0, top + 1, x0 + w / 2, top)
      ..quadraticBezierTo(x1, top + 1, x1, shoulder)
      ..lineTo(x1, 32)
      ..close();
    final rect = Rect.fromLTRB(x0, top, x1, 32);
    canvas.drawPath(p, grey == null ? glassFill(rect, Glass.turq) : solid(grey));
    canvas.drawPath(p, stroke(1.4));
  }

  @override
  bool shouldRepaint(covariant _RibbonPainter old) =>
      old.hero != hero ||
      !identical(old.data, data) ||
      old.endKmLabel != endKmLabel ||
      old.prevName != prevName ||
      old.endName != endName ||
      old.startName != startName;
}

// ---------------------------------------------------------------- весь путь по главам

const _chapterDark = <Color>[
  Color(0xFF143C43),
  Color(0xFF112339),
  Color(0xFF123431),
  Color(0xFF141F3C),
  Color(0xFF1F1F3D),
  Color(0xFF3C2431),
];
const _hTeal = <Color>[Color(0xFF86F0E8), Color(0xFF2BC4BA), Color(0xFF168A84)];

class _WholePainter extends CustomPainter {
  _WholePainter({required this.bounds, required this.length, required this.hero});

  /// Концы глав (м), по порядку.
  final List<double> bounds;
  final double length;
  final double hero;

  @override
  void paint(Canvas canvas, Size size) {
    final wd = size.width;
    final len = math.max(1.0, length);
    double xOf(double pos) => (pos / len).clamp(0.0, 1.0) * wd;
    final hx = xOf(hero);
    var prev = 0.0;
    for (var i = 0; i < bounds.length; i++) {
      final a = xOf(prev);
      final b = xOf(bounds[i]);
      prev = bounds[i];
      if (b - a < 0.3) continue;
      final r = Rect.fromLTRB(a, 3, b, 10);
      canvas.drawRect(r, solid(_chapterDark[i % _chapterDark.length]));
      canvas.drawRect(r, stroke(1.2)..strokeCap = StrokeCap.butt);
    }
    if (hx > 0.3) {
      final r = Rect.fromLTRB(0, 3, hx, 10);
      canvas.drawRect(r, linearFill(r.centerLeft, r.centerRight, _hTeal, Glass.stops3));
      canvas.drawRect(r, stroke(1.2)..strokeCap = StrokeCap.butt);
    }
    canvas.drawLine(Offset(hx, 0), Offset(hx, 13), stroke(2, Palette.accent));
  }

  @override
  bool shouldRepaint(covariant _WholePainter old) => old.hero != hero || old.length != length;
}

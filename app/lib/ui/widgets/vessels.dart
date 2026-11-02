// Показатели главного экрана сосудами (заказ v5.3, вариант 15·1): колбаса — сытость, фляга — вода,
// фонарь с пламенем — тепло. Уровень = высота заливки; пороги (опасность / бонус) — из balance.json.
// Геометрия перенесена из /ui/vessels.py один в один (виртуальное полотно 272×184).

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/tokens.dart';
import 'glass_paint.dart';

/// Подписи и значения для одного сосуда.
class VesselInfo {
  const VesselInfo({required this.value, required this.label, required this.dangerLabel});

  /// 0..100
  final double value;

  /// «Сытость»
  final String label;

  /// «Сытость · голоден» — показывается вместо [label] ниже порога опасности.
  final String dangerLabel;
}

/// Три сосуда на одном полотне. Компактно: не шире 248 dp.
class VesselsPanel extends StatelessWidget {
  const VesselsPanel({
    super.key,
    required this.satiety,
    required this.water,
    required this.warmth,
    required this.dangerBelow,
    required this.bonusAt,
    required this.bonus,
    required this.semanticsLabel,
  });

  final VesselInfo satiety;
  final VesselInfo water;
  final VesselInfo warmth;
  final double dangerBelow;
  final double bonusAt;
  final bool bonus;
  final String semanticsLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticsLabel,
      child: ExcludeSemantics(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 248),
            child: AspectRatio(
              aspectRatio: 272 / 184,
              child: CustomPaint(
                painter: VesselsPainter(
                  satiety: satiety,
                  water: water,
                  warmth: warmth,
                  dangerBelow: dangerBelow,
                  bonusAt: bonusAt,
                  bonus: bonus,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- цвета из vessels.py

const _coral = Palette.coralLine; // #FF6B7A
const _vesselBg = Color(0xFF0C1722);
const _twine = Color(0xFFD9C29A);
const _twineLight = Color(0xFFE8D6B0);
const _fat = Color(0xFFF6E2D6);

const _meat = <Color>[Color(0xFFE8706A), Color(0xFFC24A4C), Color(0xFF7E2633)];
const _skin = <Color>[Color(0xFF3A2026), Color(0xFF1A0E14)];
const _glowOrange = <Color>[Color(0xBFFF9A4A), Color(0x47FF7A2E), Color(0x00FF7A2E)];
const _glowRed = <Color>[Color(0xBFFF5A4A), Color(0x47E0303A), Color(0x00E0303A)];
const _glowTurq = <Color>[Color(0x993FD6CC), Color(0x333FD6CC), Color(0x003FD6CC)];
const _glowStops = <double>[0.0, 0.55, 1.0];

// Пламя: [низ, верх] (градиент снизу вверх).
const _fl1 = <Color>[Color(0xFFE0402E), Color(0xFFFF7A3A)];
const _fl2 = <Color>[Color(0xFFFF8A3A), Color(0xFFFFB070)];
const _fl3 = <Color>[Color(0xFFFFE6C4), Color(0xFFFFC890)];
const _bl1 = <Color>[Color(0xFF2E5FD0), Color(0xFF4F8CF0)];
const _bl2 = <Color>[Color(0xFF5FA0FF), Color(0xFF8FC4FF)];
const _bl3 = <Color>[Color(0xFFE4F2FF), Color(0xFFBFE0FF)];

const _fatSpots = <List<double>>[
  [-14, 92, 3.2], [6, 84, 2.6], [14, 104, 3], [-6, 112, 2.4], [-18, 76, 2.2], [10, 118, 2.2], //
  [18, 70, 2], [-2, 62, 2.4], [-12, 52, 2], [4, 98, 1.8], [-20, 102, 2],
];

class VesselsPainter extends CustomPainter {
  VesselsPainter({
    required this.satiety,
    required this.water,
    required this.warmth,
    required this.dangerBelow,
    required this.bonusAt,
    required this.bonus,
  });

  final VesselInfo satiety;
  final VesselInfo water;
  final VesselInfo warmth;
  final double dangerBelow;
  final double bonusAt;
  final bool bonus;

  static double _y(double level) => 124 - 0.8 * level.clamp(0.0, 100.0);

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 272.0;
    canvas.save();
    canvas.scale(k, k);

    _sausage(canvas, satiety.value, satiety.value < dangerBelow);
    _flask(canvas, water.value, water.value < dangerBelow);
    _lantern(canvas, warmth.value, warmth.value < dangerBelow);

    // пороги: бирюзовый пунктир — бонус, коралловый — опасность
    final yb = _y(bonusAt);
    final yd = _y(dangerBelow);
    _dash(canvas, yb, Palette.accent);
    _dash(canvas, yd, _coral);
    paintLabel(canvas, '${bonusAt.round()}', 270, yb - 3,
        const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: Palette.accent),
        align: TextAlign.right);
    paintLabel(canvas, '${dangerBelow.round()}', 270, yd - 3,
        const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: _coral),
        align: TextAlign.right);

    // числа и подписи
    _caption(canvas, 50, satiety);
    _caption(canvas, 136, water);
    _caption(canvas, 222, warmth);
    canvas.restore();
  }

  void _caption(Canvas canvas, double x, VesselInfo v) {
    final danger = v.value < dangerBelow;
    paintLabel(canvas, '${v.value.round()}', x, 158,
        TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: danger ? _coral : Palette.parchment));
    paintLabel(
      canvas,
      danger ? v.dangerLabel : v.label,
      x,
      175,
      danger
          ? const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: _coral)
          : const TextStyle(fontSize: 11.5, color: Palette.parchmentDim),
    );
  }

  void _dash(Canvas canvas, double y, Color c) {
    final p = stroke(1.2, c, 0.8);
    for (var x = 0.0; x < 272; x += 8) {
      canvas.drawLine(Offset(x, y), Offset(math.min(272.0, x + 4), y), p);
    }
  }

  /// Штриховка «ниже порога опасности» (pattern k-hatch: линии под 45°, шаг 6).
  void _hatch(Canvas canvas) {
    final top = _y(dangerBelow);
    final r = Rect.fromLTRB(-40, top, 40, top + 30);
    canvas.save();
    canvas.clipRect(r);
    final p = stroke(1.6, _coral, 0.55)..strokeCap = StrokeCap.butt;
    const step = 8.485; // 6 / cos 45°
    for (var x = r.left; x < r.right + r.height; x += step) {
      canvas.drawLine(Offset(x, r.top), Offset(x - r.height, r.bottom), p);
    }
    canvas.restore();
  }

  void _sparks(Canvas canvas, List<List<double>> at, Color c) {
    for (final s in at) {
      canvas.drawPath(sparkPath(s[0], s[1]), solid(c));
    }
  }

  void _glow(Canvas canvas, double cy, double r, List<Color> colors) {
    canvas.drawCircle(Offset(0, cy), r, radialFill(Offset(0, cy), r, colors, _glowStops));
  }

  void _highlight(Canvas canvas, Path p) => canvas.drawPath(p, stroke(2, Colors.white, 0.22));

  void _steelCap(Canvas canvas, Rect r, double radius) {
    final rr = RRect.fromRectAndRadius(r, Radius.circular(radius));
    canvas.drawRRect(rr, glassFill(r, Glass.steel));
    canvas.drawRRect(rr, stroke(1.8));
  }

  // ------------------------------------------------ колбаса (сытость)
  static Path _sausagePath() => Path()
    ..moveTo(-6, 40)
    ..cubicTo(-22, 42, -30, 58, -30, 82)
    ..cubicTo(-30, 106, -24, 122, -10, 126)
    ..cubicTo(2, 129, 20, 126, 26, 110)
    ..cubicTo(31, 94, 30, 64, 24, 50)
    ..cubicTo(19, 41, 9, 38, -6, 40)
    ..close();

  void _sausage(Canvas canvas, double level, bool danger) {
    final y = _y(level);
    canvas.save();
    canvas.translate(50, 0);
    if (bonus) {
      _glow(canvas, 82, 60, _glowOrange);
      _sparks(canvas, const [
        [-36, 52],
        [34, 58],
        [-30, 118],
        [38, 104],
      ], const Color(0xFFFFB070));
    }
    final body = _sausagePath();
    canvas.drawPath(body, linearFill(const Offset(31, 38), const Offset(-30, 129), _skin));
    canvas.save();
    canvas.clipPath(body);
    final meat = Rect.fromLTWH(-40, y, 80, 130 - y);
    canvas.drawRect(meat, linearFill(Offset(40, y), const Offset(-40, 130), _meat, Glass.stops3));
    canvas.drawRect(Rect.fromLTWH(-40, y, 80, 2.6), solid(Colors.white, 0.35));
    for (final f in _fatSpots) {
      if (f[1] > y + 2) {
        canvas.drawOval(
          Rect.fromCenter(center: Offset(f[0], f[1]), width: f[2] * 2, height: f[2] * 1.6),
          solid(_fat, 0.9),
        );
      }
    }
    _hatch(canvas);
    // сетка шпагата
    final tw = stroke(1.3, _twine, 0.85)..strokeCap = StrokeCap.butt;
    for (var i = -6; i <= 6; i++) {
      final x0 = i * 12.0;
      canvas.drawLine(Offset(x0 - 30, 36), Offset(x0 + 30, 132), tw);
      canvas.drawLine(Offset(x0 + 30, 36), Offset(x0 - 30, 132), tw);
    }
    for (final yy in const [56.0, 76.0, 96.0, 116.0]) {
      final ring = Path()
        ..moveTo(-34, yy)
        ..quadraticBezierTo(0, yy + 6, 34, yy);
      canvas.drawPath(ring, stroke(2.2, _twineLight)..strokeCap = StrokeCap.butt);
      canvas.drawPath(ring, stroke(0.8, Glass.lead, 0.5)..strokeCap = StrokeCap.butt);
    }
    canvas.restore();
    canvas.drawPath(body, stroke(5));
    // хвостик и петля
    final tail = Path()
      ..moveTo(-4, 39)
      ..cubicTo(-4, 35, -2, 33, 0, 31);
    canvas.drawPath(tail, stroke(5));
    canvas.drawPath(tail, stroke(2.4, _twineLight));
    final knot = Rect.fromCenter(center: const Offset(-2, 38), width: 18, height: 7.2);
    canvas.drawOval(knot, solid(_twineLight));
    canvas.drawOval(knot, stroke(1.6));
    _highlight(
        canvas,
        Path()
          ..moveTo(-18, 58)
          ..cubicTo(-24, 76, -24, 92, -19, 106));
    if (danger) {
      canvas.drawPath(body, stroke(2, _coral));
      paintWarnSign(canvas, -9, 4, 18, _coral);
    }
    canvas.restore();
  }

  // ------------------------------------------------ фляга (вода)
  static Path _flaskPath() => Path()
    ..moveTo(-10.2, 40.0)
    ..lineTo(10.2, 40.0)
    ..lineTo(10.2, 53.6)
    ..cubicTo(31.8, 58.2, 34.1, 78.6, 34.1, 94.5)
    ..cubicTo(34.1, 117.2, 27.2, 124.0, 15.9, 124.0)
    ..lineTo(-15.9, 124.0)
    ..cubicTo(-27.2, 124.0, -34.1, 117.2, -34.1, 94.5)
    ..cubicTo(-34.1, 78.6, -31.8, 58.2, -10.2, 53.6)
    ..close();

  void _flask(Canvas canvas, double level, bool danger) {
    final y = _y(level);
    canvas.save();
    canvas.translate(136, 0);
    if (bonus) {
      _glow(canvas, 84, 60, _glowTurq);
      _sparks(canvas, const [
        [-34, 56],
        [34, 62],
        [-36, 112],
        [38, 108],
      ], const Color(0xFF7FE8E0));
    }
    final body = _flaskPath();
    canvas.drawPath(body, solid(_vesselBg));
    canvas.save();
    canvas.clipPath(body);
    final waterRect = Rect.fromLTWH(-40, y, 80, 130 - y);
    canvas.drawRect(waterRect, glassFill(waterRect, Glass.sky));
    canvas.drawRect(Rect.fromLTWH(-40, y, 80, 3), solid(Colors.white, 0.4));
    _hatch(canvas);
    final lead = stroke(1.1, Glass.lead, 0.7)..strokeCap = StrokeCap.butt;
    for (var i = -5; i <= 5; i++) {
      final x0 = i * 13.0;
      canvas.drawLine(Offset(x0 - 22, 52), Offset(x0 + 2, 128), lead);
    }
    canvas.restore();
    canvas.drawPath(body, stroke(5));
    if (bonus) canvas.drawPath(body, stroke(2, Palette.accent));
    _steelCap(canvas, const Rect.fromLTWH(-14, 31, 28, 11), 2.4);
    _highlight(
        canvas,
        Path()
          ..moveTo(-22, 62)
          ..cubicTo(-28, 80, -28, 96, -23, 110));
    if (danger) {
      canvas.drawPath(body, stroke(2, _coral));
      paintWarnSign(canvas, -9, 4, 18, _coral);
    }
    canvas.restore();
  }

  // ------------------------------------------------ фонарь (тепло)
  static Path _lanternPath() => Path()
    ..moveTo(-24, 46)
    ..lineTo(24, 46)
    ..lineTo(28, 124)
    ..lineTo(-28, 124)
    ..close();

  static const double _base = 118;

  Path _flamePath(double w, double top) {
    final hh = _base - top;
    return Path()
      ..moveTo(0, top)
      ..cubicTo(w * 0.25, top + hh * 0.25, w, top + hh * 0.5, w * 0.9, _base - hh * 0.18)
      ..cubicTo(w * 0.8, _base, w * 0.35, _base + 3, 0, _base + 3)
      ..cubicTo(-w * 0.35, _base + 3, -w * 0.8, _base, -w * 0.9, _base - hh * 0.18)
      ..cubicTo(-w, top + hh * 0.5, -w * 0.15, top + hh * 0.32, 0, top)
      ..close();
  }

  void _flame(Canvas canvas, double w, double top, List<Color> bottomTop) {
    final p = _flamePath(w, top);
    canvas.drawPath(p, linearFill(const Offset(0, _base + 3), Offset(0, top), bottomTop));
    canvas.drawPath(p, stroke(1.6));
  }

  void _lantern(Canvas canvas, double level, bool danger) {
    final y = _y(level);
    canvas.save();
    canvas.translate(222, 0);
    if (bonus) {
      _glow(canvas, 84, 62, _glowRed);
      _sparks(canvas, const [
        [-38, 60],
        [36, 54],
        [-34, 116],
        [40, 110],
      ], const Color(0xFFFF8A7A));
    }
    final body = _lanternPath();
    canvas.drawPath(body, solid(_vesselBg));
    canvas.save();
    canvas.clipPath(body);
    final cold = level < dangerBelow;
    final strength = math.min(1.0, level / math.max(1.0, bonusAt));
    // дымка: холодная синяя или тёплая — эллипс в рамке (-30, 40, 60×90), центр на 0.85 высоты
    canvas.save();
    canvas.translate(0, 40 + 0.85 * 90);
    canvas.scale(1, 1.5);
    if (cold) {
      const r = 0.6 * 60;
      canvas.drawCircle(Offset.zero, r,
          radialFill(Offset.zero, r, [alpha(const Color(0xFF5F9CFF), 0.5 * 0.35), const Color(0x005F9CFF)], const [0, 1]));
    } else {
      const r = 0.7 * 60;
      final op = 0.25 + 0.75 * strength;
      canvas.drawCircle(Offset.zero, r,
          radialFill(Offset.zero, r, [alpha(const Color(0xFFFF9A5A), 0.55 * op), const Color(0x00FF6A3A)], const [0, 1]));
    }
    canvas.restore();
    // пламя: основание у фитиля, вершина = уровень (холодно — маленький синий огонёк)
    double top;
    double w;
    if (cold) {
      final hh = 9 + 0.5 * level.clamp(0.0, 100.0);
      top = _base - hh;
      w = hh * 0.42;
    } else {
      top = y;
      w = math.min(22.0, (_base - top) * 0.42);
    }
    final f1 = cold ? _bl1 : _fl1;
    final f2 = cold ? _bl2 : _fl2;
    final f3 = cold ? _bl3 : _fl3;
    _flame(canvas, w, top, f1);
    _flame(canvas, w * 0.62, top + (_base - top) * 0.28, f2);
    _flame(canvas, w * 0.3, top + (_base - top) * 0.56, f3);
    canvas.drawRect(const Rect.fromLTWH(-2, _base, 4, 6), solid(const Color(0xFF2A1A14)));
    _hatch(canvas);
    canvas.restore();
    canvas.drawPath(body, stroke(5));
    final bar = stroke(2.4)..strokeCap = StrokeCap.butt;
    canvas.drawLine(const Offset(-12, 46), const Offset(-14, 124), bar);
    canvas.drawLine(const Offset(12, 46), const Offset(14, 124), bar);
    if (danger) canvas.drawPath(body, stroke(2, _coral));
    _steelCap(canvas, const Rect.fromLTWH(-16, 33, 32, 13), 2);
    final handle = Path()
      ..moveTo(-10, 33)
      ..cubicTo(-10, 20, 10, 20, 10, 33);
    canvas.drawPath(handle, stroke(4)..strokeCap = StrokeCap.butt);
    canvas.drawPath(handle, stroke(1.6, Palette.parchmentDim)..strokeCap = StrokeCap.butt);
    _steelCap(canvas, const Rect.fromLTWH(-32, 124, 64, 7), 2);
    _highlight(
        canvas,
        Path()
          ..moveTo(-20, 52)
          ..cubicTo(-24, 76, -24, 92, -19, 108));
    if (danger) paintWarnSign(canvas, -9, 4, 18, _coral);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant VesselsPainter old) =>
      old.satiety.value != satiety.value ||
      old.water.value != water.value ||
      old.warmth.value != warmth.value ||
      old.satiety.label != satiety.label ||
      old.bonus != bonus ||
      old.dangerBelow != dangerBelow ||
      old.bonusAt != bonusAt;
}

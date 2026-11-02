// Общие кисти «витража» для CustomPainter главного экрана: свинцовый контур, стеклянные градиенты.
// Цвета совпадают с макетом docs/v5/04-art-style.md (раздел «Интерфейс v5.3») и /ui/vessels.py.

import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class Glass {
  static const lead = Color(0xFF070B10);

  // Вертикальные «стёкла»: светлее сверху, глубже снизу (стопы 0 / 0.5 / 1).
  static const turq = [Color(0xFF9CF5EF), Color(0xFF3FD6CC), Color(0xFF1FA39B)];
  static const teal = [Color(0xFF86F0E8), Color(0xFF2BC4BA), Color(0xFF168A84)];
  static const indigo = [Color(0xFF8493EE), Color(0xFF2B3E9E), Color(0xFF1B2870)];
  static const emerald = [Color(0xFF5FDCA9), Color(0xFF1F9E6B), Color(0xFF136447)];
  static const violet = [Color(0xFFAA8EEA), Color(0xFF5B3FA0), Color(0xFF3C2874)];
  static const milk = [Color(0xFFFFFBEC), Color(0xFFE9DFC8), Color(0xFFB9AE92)];
  static const sky = [Color(0xFFA2DAF9), Color(0xFF5BB5E8), Color(0xFF3585BA)];
  static const steel = [Color(0xFF4B6784), Color(0xFF2A4157), Color(0xFF1B2D3E)];
  static const night = [Color(0xFF22344A), Color(0xFF16222F), Color(0xFF0B1424)];

  static const stops3 = <double>[0.0, 0.5, 1.0];
}

/// Заливка вертикальным трёхцветным градиентом по прямоугольнику [r].
Paint glassFill(Rect r, List<Color> colors) =>
    Paint()..shader = ui.Gradient.linear(r.topCenter, r.bottomCenter, colors, Glass.stops3);

/// Линейный градиент между двумя точками.
Paint linearFill(Offset a, Offset b, List<Color> colors, [List<double>? stops]) =>
    Paint()..shader = ui.Gradient.linear(a, b, colors, stops);

/// Радиальное свечение: центр, радиус, цвета и стопы.
Paint radialFill(Offset c, double r, List<Color> colors, List<double> stops) =>
    Paint()..shader = ui.Gradient.radial(c, r, colors, stops);

/// Сплошная заливка цветом (с прозрачностью 0..1).
Paint solid(Color c, [double opacity = 1.0]) =>
    Paint()..color = opacity >= 1.0 ? c : c.withAlpha((opacity * 255).round().clamp(0, 255));

/// Обводка: толщина, цвет, прозрачность; скруглённые концы и стыки.
Paint stroke(double width, [Color c = Glass.lead, double opacity = 1.0]) => Paint()
  ..style = PaintingStyle.stroke
  ..strokeWidth = width
  ..strokeCap = StrokeCap.round
  ..strokeJoin = StrokeJoin.round
  ..color = opacity >= 1.0 ? c : c.withAlpha((opacity * 255).round().clamp(0, 255));

/// Цвет с прозрачностью 0..1.
Color alpha(Color c, double opacity) => c.withAlpha((opacity * 255).round().clamp(0, 255));

/// Четырёхлучевая искра (как в vessels.py): центр (sx, sy), луч 5.
Path sparkPath(double sx, double sy) => Path()
  ..moveTo(sx, sy - 5)
  ..lineTo(sx + 1.6, sy - 1.6)
  ..lineTo(sx + 5, sy)
  ..lineTo(sx + 1.6, sy + 1.6)
  ..lineTo(sx, sy + 5)
  ..lineTo(sx - 1.6, sy + 1.6)
  ..lineTo(sx - 5, sy)
  ..lineTo(sx - 1.6, sy - 1.6)
  ..close();

/// Знак тревоги (треугольник с «!») из макета: левый верх (x, y), размер [size] (исходник 24×24).
void paintWarnSign(Canvas canvas, double x, double y, double size, Color color) {
  canvas.save();
  canvas.translate(x, y);
  final k = size / 24.0;
  canvas.scale(k, k);
  final tri = Path()
    ..moveTo(12, 3)
    ..lineTo(22, 20.5)
    ..lineTo(2, 20.5)
    ..close();
  canvas.drawPath(tri, solid(color));
  canvas.drawPath(tri, stroke(2, color));
  canvas.drawLine(const Offset(12, 9.5), const Offset(12, 14.5), stroke(2.4, const Color(0xFF0E1621)));
  canvas.drawCircle(const Offset(12, 17.5), 1.4, solid(const Color(0xFF0E1621)));
  canvas.restore();
}

/// Фишка героя-мипл (символ `pawn` из макета, viewBox 24×30), вписанная в прямоугольник [r].
void paintPawn(Canvas canvas, Rect r) {
  canvas.save();
  canvas.translate(r.left, r.top);
  canvas.scale(r.width / 24.0, r.height / 30.0);
  // посох
  canvas.drawLine(const Offset(19, 9), const Offset(20.4, 28), stroke(3.2));
  canvas.drawLine(const Offset(19, 9), const Offset(20.4, 28), stroke(1.5, const Color(0xFF3FD6CC)));
  // ноги
  final legs = Path()
    ..moveTo(10.4, 19)
    ..lineTo(8.6, 27.5)
    ..moveTo(13.6, 19)
    ..lineTo(15.6, 27.5);
  canvas.drawPath(legs, stroke(4));
  canvas.drawPath(legs, stroke(2.2, const Color(0xFFE9DFC8)));
  // рюкзак
  final pack = RRect.fromRectAndRadius(const Rect.fromLTWH(3, 10, 7.5, 11), const Radius.circular(2.4));
  canvas.drawRRect(pack, glassFill(pack.outerRect, Glass.turq));
  canvas.drawRRect(pack, stroke(1.3));
  // куртка
  final body = Path()
    ..moveTo(9.2, 9.4)
    ..quadraticBezierTo(12.2, 7.6, 15.4, 9.4)
    ..lineTo(16.4, 19.6)
    ..lineTo(9.4, 19.6)
    ..close();
  canvas.drawPath(body, glassFill(const Rect.fromLTRB(9.2, 7.6, 16.4, 19.6), Glass.milk));
  canvas.drawPath(body, stroke(1.3));
  // голова и русые волосы
  canvas.drawCircle(const Offset(12.6, 5.4), 3.6, solid(const Color(0xFFEFE3CC)));
  canvas.drawCircle(const Offset(12.6, 5.4), 3.6, stroke(1.3));
  final hair = Path()
    ..moveTo(9.1, 5.6)
    ..cubicTo(8.8, 2.6, 11.2, 1.4, 13.2, 1.7)
    ..cubicTo(15.4, 2, 16.4, 3.8, 16.1, 5.4)
    ..cubicTo(15, 4.2, 13.6, 3.9, 12, 4)
    ..cubicTo(10.8, 4.1, 9.8, 4.7, 9.1, 5.6)
    ..close();
  canvas.drawPath(hair, solid(const Color(0xFFB58A52)));
  canvas.drawPath(hair, stroke(1));
  canvas.restore();
}

/// Текст внутри painter: [baselineY] — базовая линия, [align] — left/center/right относительно [x].
/// Возвращает занятый прямоугольник.
Rect paintLabel(
  Canvas canvas,
  String text,
  double x,
  double baselineY,
  TextStyle style, {
  TextAlign align = TextAlign.center,
  bool dryRun = false,
  double minX = double.negativeInfinity,
  double maxX = double.infinity,
}) {
  final tp = TextPainter(
    text: TextSpan(text: text, style: style),
    textDirection: TextDirection.ltr,
    maxLines: 1,
  )..layout();
  var left = switch (align) {
    TextAlign.right || TextAlign.end => x - tp.width,
    TextAlign.left || TextAlign.start => x,
    _ => x - tp.width / 2,
  };
  if (left < minX) left = minX;
  if (left + tp.width > maxX) left = maxX - tp.width;
  final base = tp.computeDistanceToActualBaseline(TextBaseline.alphabetic);
  final top = baselineY - base;
  if (!dryRun) tp.paint(canvas, Offset(left, top));
  return Rect.fromLTWH(left, top, tp.width, tp.height);
}

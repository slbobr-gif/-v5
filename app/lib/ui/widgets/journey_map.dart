// Карта всего пути для экранов конца главы и итога: море и озёра, маршрут от Кремля до Териберки,
// пройденные главы — цветом (или одна глава подсвечена), впереди — пунктир; точки и подписи концов глав.

import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../data/content_repository.dart';
import '../../engine/world.dart';
import '../theme/tokens.dart';
import 'chapter_map.dart' show RouteLine;

/// Цвета глав 1–6 на итоговой карте и в таблице глав.
const chapterColors = <Color>[
  Color(0xFF3FD6CC),
  Color(0xFF7FC46A),
  Color(0xFFE8C15A),
  Color(0xFFE5855D),
  Color(0xFFB07CE8),
  Color(0xFF5BB5E8),
];

/// Места, у которых подпись лучше слева (справа соседняя точка или море).
const _leftLabels = {'murmansk', 'kem', 'novgorod', 'petrozavodsk'};

Color chapterColor(int ch) => chapterColors[(ch - 1).clamp(0, chapterColors.length - 1)];

class JourneyMap extends StatelessWidget {
  const JourneyMap({super.key, required this.content, required this.upTo, this.highlight, this.labels = true});

  final GameContent content;

  /// Сколько глав пройдено (1..6): они нарисованы сплошной линией, дальше пунктир.
  final int upTo;

  /// Подсветить одну главу акцентом (конец главы); null — все пройденные главы своими цветами (итог).
  final int? highlight;
  final bool labels;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _JourneyPainter(RouteLine.of(content), content, upTo, highlight, labels),
      child: const SizedBox.expand(),
    );
  }
}

class _JourneyPainter extends CustomPainter {
  _JourneyPainter(this.line, this.content, this.upTo, this.highlight, this.labels);

  final RouteLine line;
  final GameContent content;
  final int upTo;
  final int? highlight;
  final bool labels;

  @override
  void paint(Canvas canvas, Size size) {
    final w = content.world;
    final b = line.bounds;
    const pad = 14.0;
    final labelRoom = labels ? 70.0 : 0.0;
    final aw = size.width - pad * 2 - labelRoom;
    final ah = size.height - pad * 2;
    final k = math.min(aw / math.max(b.width, 1e-6), ah / math.max(b.height, 1e-6));
    final ox = pad + labelRoom / 2 + (aw - b.width * k) / 2 - b.left * k;
    final oy = pad + (ah - b.height * k) / 2 - b.top * k;

    canvas.save();
    canvas.clipRect(Offset.zero & size);
    canvas.translate(ox, oy);
    canvas.scale(k, k);
    final water = Paint()..color = const Color(0xFF12324A);
    for (final p in line.water) {
      canvas.drawPath(p, water);
    }
    for (final c in w.chapters) {
      final id = toI(c['id']);
      final path = line.chapterPath(w, id);
      if (id > upTo) {
        _dashed(canvas, path, 2.4 / k, const Color(0xFF3A5068), 3 / k, 5 / k);
        continue;
      }
      final hl = highlight;
      final color = hl == null ? chapterColor(id) : (id == hl ? Palette.accent : const Color(0xFF56677A));
      final width = (hl != null && id == hl ? 4.2 : 3.2) / k;
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = width
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..color = color,
      );
    }
    canvas.restore();

    // точки и подписи — в экранных координатах, чтобы не зависели от масштаба
    final stops = <(double, String, bool)>[
      (w.chapterStartPos(1), '${w.chapterById(1)['from']}', true),
      for (final c in w.chapters) (w.chapterEndPos(toI(c['id'])), '${c['to']}', toI(c['id']) <= upTo),
    ];
    for (final (pos, id, reached) in stops) {
      final p = line.at(pos);
      final o = Offset(ox + p.dx * k, oy + p.dy * k);
      canvas.drawCircle(o, 4.2, Paint()..color = Palette.ink);
      canvas.drawCircle(o, 3.2, Paint()..color = reached ? Palette.parchment : const Color(0xFF3A5068));
      if (!labels) continue;
      final tp = TextPainter(
        text: TextSpan(
          text: content.placeName(id),
          style: TextStyle(fontSize: 10.5, color: reached ? Palette.parchment : Palette.parchmentDim),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: labelRoom + 40);
      // подпись справа от точки; у городов, где справа соседняя точка или край, — слева
      var x = _leftLabels.contains(id) ? o.dx - 7 - tp.width : o.dx + 7;
      if (x + tp.width > size.width - 2) x = o.dx - 7 - tp.width;
      if (x < 2) x = o.dx + 7;
      tp.paint(canvas, Offset(x, o.dy - tp.height / 2));
    }
  }

  void _dashed(Canvas canvas, Path path, double width, Color color, double dash, double gap) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = width
      ..strokeCap = StrokeCap.round
      ..color = color;
    for (final ui.PathMetric m in path.computeMetrics()) {
      var d = 0.0;
      while (d < m.length) {
        canvas.drawPath(m.extractPath(d, math.min(d + dash, m.length)), paint);
        d += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(_JourneyPainter old) =>
      !identical(old.line, line) || old.upTo != upTo || old.highlight != highlight || old.labels != labels;
}

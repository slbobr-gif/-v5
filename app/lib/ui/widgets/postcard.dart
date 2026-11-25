// Открытка с маршрута (25.11): витражная сцена места, название, фраза Сергея, дата и километр.
// Её можно отправить картинкой — через shareCardDialog, как карточку главы.

import 'package:flutter/material.dart';

import '../../data/content_repository.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import 'common.dart';
import 'finale_widgets.dart';

/// Сцена открытки: финиш — море, остальное — город.
String postcardArt(String placeId) =>
    placeId == 'teriberka' ? 'assets/art/scenes/lake.svg' : 'assets/art/scenes/town.svg';

/// Оттенок главы поверх сцены, чтобы открытки разных глав отличались.
Color _chapterTint(int ch) => switch (ch) {
      1 => const Color(0x332B3E9E),
      2 => const Color(0x33C9A227),
      3 => const Color(0x33E9DFC8),
      4 => const Color(0x331F9E6B),
      5 => const Color(0x335BB5E8),
      _ => const Color(0x333FD6CC),
    };

class PostcardCard extends StatelessWidget {
  const PostcardCard({super.key, required this.content, required this.placeId, this.day});

  final GameContent content;
  final String placeId;
  final String? day;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final w = content.world;
    final place = w.placeById[placeId] ?? const <String, dynamic>{};
    final ch = toI(place['chapter'] ?? 0);
    final km = (w.posOf[placeId] ?? 0) / 1000.0;
    return ShareCardFrame(
      right: day == null ? l.postcardKicker : fmtDay(l, day),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: Gap.s),
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: SizedBox(
              height: 170,
              child: Stack(fit: StackFit.expand, children: [
                Art(postcardArt(placeId)),
                ColoredBox(color: _chapterTint(ch)),
                Positioned(
                  left: 12,
                  bottom: 10,
                  right: 12,
                  child: Text(
                    content.placeName(placeId),
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      color: Palette.parchment,
                      shadows: [Shadow(blurRadius: 8, color: Color(0xCC000000))],
                    ),
                  ),
                ),
              ]),
            ),
          ),
          const SizedBox(height: Gap.s),
          StoryText(
            '_${content.postcards[placeId] ?? ''}_',
            style: const TextStyle(fontSize: 15, height: 1.4),
          ),
          const SizedBox(height: 6),
          Text(
            km < 1 ? l.postcardStart : l.postcardKm(fmtKm(km)),
            style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

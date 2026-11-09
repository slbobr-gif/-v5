// Статистика конца главы и итога (lib/engine/journey_stats.dart) на реальном мире.

import 'package:flutter_test/flutter_test.dart';
import 'package:putnik/data/content_repository.dart';
import 'package:putnik/engine/journey_stats.dart';
import 'package:putnik/engine/state.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('дни, шаги и лучший день считаются по главам', () async {
    final w = (await loadGameContent()).world;
    final s = HeroState.create(w, 1, 0, '2026-05-02');
    s.daySteps
      ..clear()
      ..addAll({'2026-05-02': 8000, '2026-05-03': 11240, '2026-05-04': 9000, '2026-05-05': 7000, '2026-05-06': 12000});
    s.marks
      ..add({'ch': 1, 't': 0, 'day': '2026-05-04', 'steps': 28240, 'events': 10, 'deaths': 1, 'quests': 0})
      ..add({'ch': 2, 't': 0, 'day': '2026-05-06', 'steps': 47240, 'events': 18, 'deaths': 1, 'quests': 1});
    final c1 = chapterStats(w, s, 1)!;
    expect(c1.days, 3);
    expect(c1.steps, 28240);
    expect(c1.bestSteps, 11240);
    expect(c1.bestDay, '2026-05-03');
    expect(c1.events, 10);
    expect(c1.deaths, 1);
    final c2 = chapterStats(w, s, 2)!;
    expect(c2.days, 2);
    expect(c2.steps, 19000);
    expect(c2.bestDay, '2026-05-06');
    expect(c2.deaths, 0);
    expect(chapterStats(w, s, 3), isNull);
    final j = journeyStats(w, s, today: '2026-05-06');
    expect(j.days, 5);
    expect(j.steps, 47240);
    expect(j.chapters.length, 2);
    expect(j.randomTotal, greaterThan(0));
  });
}

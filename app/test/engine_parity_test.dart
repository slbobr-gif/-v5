// Совпадение Dart-движка с эталоном tools/sim/engine.py на 20-дневном сценарии.
// Фикстура: python3 tools/sim/make_parity_fixture.py

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:putnik/data/content_repository.dart';
import 'package:putnik/engine/engine.dart';
import 'package:putnik/engine/state.dart';

void act(Engine e, int now) {
  for (var i = 0; i < 60; i++) {
    final st = e.s.stop;
    if (st == null || st['type'] == 'finish') return;
    switch (st['type']) {
      case 'event':
        final ev = e.currentEvent()!;
        final ch = (ev['choices'] as List)
            .cast<Map>()
            .map((c) => c.cast<String, dynamic>())
            .firstWhere(e.choiceAvailable);
        e.choose(ch['id'] as String, now);
      case 'place':
      case 'chapter_end':
        if (e.market().any((o) => o.item == 'bread') && (e.s.inv['bread'] ?? 0) < 2) {
          e.buy('bread', now);
        }
        e.continueJourney(now);
      case 'death':
        e.s.stop = null;
    }
    e.advance(now);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Dart-движок повторяет эталон день в день', () async {
    final fx = jsonDecode(File('test/fixtures/parity.json').readAsStringSync()) as Map<String, dynamic>;
    final content = await loadGameContent();
    final w = content.world;
    expect(w.length, closeTo((fx['routeLengthM'] as num).toDouble(), 0.5));
    final t0 = fx['t0'] as int;
    final days = (fx['days'] as List).cast<String>();
    final steps = (fx['steps'] as List).cast<int>();
    final baseline = fx['baseline'] as int;
    final s = HeroState.create(w, fx['seed'] as int, t0, days[0], todaySteps: baseline);
    final e = Engine(w, s);
    const day = 24 * 3600 * 1000;
    final expected = (fx['expected'] as List).cast<Map>();
    for (var i = 0; i < steps.length; i++) {
      final now = t0 + i * day + 10 * 3600 * 1000;
      e.syncSteps({days[i]: i == 0 ? baseline + steps[i] : steps[i]}, now);
      e.claimLogin(days[i], now);
      e.advance(now);
      act(e, now);
      final x = expected[i];
      final where = 'день ${i + 1} (${days[i]})';
      expect(s.pos, closeTo((x['pos'] as num).toDouble(), 0.02), reason: '$where: позиция');
      expect(s.buffer, closeTo((x['buffer'] as num).toDouble(), 0.02), reason: '$where: буфер');
      expect(s.coins, x['coins'], reason: '$where: монеты');
      (x['stats'] as Map).forEach((k, v) {
        expect(s.stats[k], closeTo((v as num).toDouble(), 0.002), reason: '$where: $k');
      });
      expect(Map.fromEntries(s.inv.entries.toList()..sort((a, b) => a.key.compareTo(b.key))),
          (x['inv'] as Map).map((k, v) => MapEntry(k as String, v as int)), reason: '$where: рюкзак');
      expect(s.stop?['type'], x['stop'], reason: '$where: остановка');
      expect(s.deaths, x['deaths'], reason: '$where: смерти');
      expect(s.seen.length, x['seen'], reason: '$where: события');
      expect(s.journal.length, x['journal'], reason: '$where: журнал');
      expect(s.rng, x['rng'], reason: '$where: RNG');
    }
  });

  test('сохранение и загрузка состояния без потерь', () async {
    final content = await loadGameContent();
    final s = HeroState.create(content.world, 7, 1777622400000, '2026-05-01');
    final e = Engine(content.world, s);
    e.syncSteps({'2026-05-01': 9000}, 1777622400000 + 3600000);
    e.advance(1777622400000 + 3600000);
    final back = HeroState.fromJson(jsonDecode(jsonEncode(s.toJson())) as Map<String, dynamic>);
    expect(jsonEncode(back.toJson()), jsonEncode(s.toJson()));
  });

  test('повторная синхронизация тех же шагов ничего не добавляет', () async {
    final content = await loadGameContent();
    final s = HeroState.create(content.world, 7, 1777622400000, '2026-05-01');
    final e = Engine(content.world, s);
    expect(e.syncSteps({'2026-05-01': 5000}, 1777622400000), 5000);
    expect(e.syncSteps({'2026-05-01': 5000}, 1777622400000), 0);
    expect(e.syncSteps({'2026-05-01': 4000}, 1777622400000), 0);
    expect(e.syncSteps({'2026-04-30': 9000}, 1777622400000), 0);
  });
}

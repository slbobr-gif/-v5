// Сквозные линии (V5-74): счётчики из флагов и финальные страницы эпилога на реальном мире.

import 'package:flutter_test/flutter_test.dart';
import 'package:putnik/app/lines.dart';
import 'package:putnik/data/content_repository.dart';
import 'package:putnik/engine/state.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('эпилог: финалы линий встают после кита и зависят от счётчиков', () async {
    final w = (await loadGameContent()).world;
    final s = HeroState.create(w, 1, 0, '2026-05-02');
    final base = (w.chapterById(w.chapters.length)['epilogue'] as List).length;

    var ep = epilogueWithLines(w, s);
    expect(ep.length, base + 2);
    expect(ep[3]['title'], 'Родители');
    expect(ep[4]['title'], 'Саша');
    expect(ep[3]['min'], 0);
    expect(ep[4]['min'], 0);

    s.flags.addAll([for (var i = 0; i < 9; i++) 'bond_mama_x$i', for (var i = 0; i < 8; i++) 'bond_papa_x$i']);
    s.flags.addAll([for (var i = 0; i < 10; i++) 'care_sasha_x$i']);
    expect(parentsScore(s), 17);
    expect(sashaScore(s), 10);
    ep = epilogueWithLines(w, s);
    expect(ep[3]['min'], 15);
    expect(ep[4]['min'], 9);
  });

  test('сцены линий: у раздумий один вариант, у разговоров — флаг открытого ответа', () async {
    final w = (await loadGameContent()).world;
    final lines = w.eventsById.values.where((e) => e['line'] != null).toList();
    expect(lines.length, greaterThanOrEqualTo(70));
    for (final e in lines.where((e) => e['line'] == 'life')) {
      expect(e['kind'], 'reflection');
      expect((e['choices'] as List).length, 1);
    }
    for (final e in lines.where((e) => e['line'] != 'life')) {
      final flags = [
        for (final c in e['choices'] as List)
          for (final o in (c as Map)['outcomes'] as List) ((o as Map)['effects'] as Map?)?['flag'],
      ].whereType<String>();
      expect(flags.length, 1, reason: '${e['id']}: ровно один открытый ответ');
    }
  });
}

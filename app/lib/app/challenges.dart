// Недельные испытания (25.11). Не из списка — собираются генератором:
//   вид × цель под темп игрока × название × примета главы × награда.
// Вид не повторяется 3 недели подряд, название и примета — пока не пройдут все варианты.
// Движок про испытания не знает: прогресс считается по герою и книжке, награду выдаёт контроллер.

import 'dart:math' as math;

import '../data/content_repository.dart';
import '../data/storage.dart';
import '../engine/engine.dart';
import '../engine/state.dart';
import '../engine/world.dart';

const challengeKinds = ['km', 'streak', 'bigday', 'steady', 'reach', 'calm', 'notebook', 'thoughts', 'nocold'];

/// Дата yyyy-MM-dd + n дней.
String addDays(String day, int n) {
  final d = DateTime.parse(day).add(Duration(days: n));
  return '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

int _round500(double v) => (v / 500).round() * 500;

/// Средние шаги в день за последние 7 закрытых дней (без сегодняшнего); новичку — 6 000.
double avgSteps(HeroState h, String today) {
  final vals = <int>[];
  for (var i = 1; i <= 7; i++) {
    final v = h.daySteps[addDays(today, -i)];
    if (v != null && v > 0) vals.add(v);
  }
  if (vals.length < 2) return 6000;
  return vals.reduce((a, b) => a + b) / vals.length;
}

int notebookCount(Profile p) =>
    p.collected.entries.where((e) => e.key != 'places' && e.key != 'thoughts').fold(0, (a, e) => a + e.value.length) +
    p.postcards.length;

int thoughtsCount(Profile p) => (p.collected['thoughts'] ?? const []).length;

int coldCount(HeroState h) => h.journal.where((j) => j.kind == 'cold').length;

/// Собрать новое испытание на неделю, начиная с [today].
Json generateChallenge(GameContent content, HeroState h, Profile p, String today) {
  final w = content.world;
  final eng = Engine(w, h);
  final history = p.challengeHistory;
  final done = p.challengesDone;
  final rnd = math.Random(h.seed ^ (done * 7919) ^ today.hashCode);
  final dict = content.challenges;
  final kinds = (dict['kinds'] as Map?)?.cast<String, dynamic>() ?? const {};
  final ch = w.chapterAt(h.pos);
  final avg = avgSteps(h, today);
  final kmPerStep = eng.gameMetersPerStep() / 1000.0;

  // ближайший город впереди, до которого реально дойти за неделю
  String? reachPlace;
  final weekKm = avg * 7 * kmPerStep;
  final ahead = w.posOf.entries
      .where((e) => content.postcards.containsKey(e.key) && e.value > h.maxPos + 2000 && e.value - h.pos < weekKm * 900)
      .toList()
    ..sort((a, b) => a.value.compareTo(b.value));
  if (ahead.isNotEmpty) reachPlace = ahead.last.key;

  // вид: не из трёх последних, reach — только если есть город по силам
  final recentKinds = history.where((x) => x.startsWith('k:')).toList().reversed.take(3).map((x) => x.substring(2)).toSet();
  var pool = challengeKinds.where((k) => kinds.containsKey(k) && !recentKinds.contains(k)).toList();
  if (reachPlace == null) pool.remove('reach');
  if (pool.isEmpty) pool = challengeKinds.where(kinds.containsKey).toList();
  final kind = pool[rnd.nextInt(pool.length)];

  // название и примета: сначала неиспользованные
  int pickUnused(int count, String prefix) {
    final used = history.where((x) => x.startsWith(prefix)).map((x) => int.tryParse(x.split(':').last) ?? -1).toSet();
    final free = [for (var i = 0; i < count; i++) if (!used.contains(i)) i];
    final from = free.isEmpty ? List.generate(count, (i) => i) : free;
    return from[rnd.nextInt(from.length)];
  }

  final titles = ((kinds[kind] as Map?)?['titles'] as List?) ?? const [];
  final flavors = (((dict['flavor'] as Map?)?['$ch']) as List?) ?? const [];
  final ti = titles.isEmpty ? 0 : pickUnused(titles.length, '$kind:t:');
  final fi = flavors.isEmpty ? 0 : pickUnused(flavors.length, 'f$ch:');

  // цель под темп игрока
  var target = 1;
  var steps = 0;
  var diff = 1; // 1..3 — от неё награда
  switch (kind) {
    case 'km':
      target = (weekKm * (1.05 + rnd.nextDouble() * 0.2)).round().clamp(10, 200);
      diff = 2;
    case 'streak':
      target = 3 + rnd.nextInt(3);
      steps = _round500(avg * 0.9).clamp(3000, 15000);
      diff = target >= 5 ? 3 : 2;
    case 'bigday':
      steps = _round500(math.max(avg * (1.4 + rnd.nextDouble() * 0.3), 7000)).clamp(7000, 30000);
      diff = 2;
    case 'steady':
      target = 5 + rnd.nextInt(2);
      steps = _round500(avg * 0.7).clamp(2500, 10000);
      diff = target == 6 ? 3 : 2;
    case 'reach':
      diff = 2;
    case 'calm':
      target = 7;
      diff = 2;
    case 'notebook':
      target = 3 + rnd.nextInt(4);
      diff = 1;
    case 'thoughts':
      target = 4 + rnd.nextInt(3);
      diff = 1;
    case 'nocold':
      target = 7;
      diff = 1;
  }

  // награда: монеты по трудности + вещь: местное лакомство главы, коробок спичек или грелки
  final coins = [0, 10, 16, 24][diff] + rnd.nextInt(5);
  final regional = <String>{};
  final reg = ((w.balance['economy'] as Map?)?['markets'] as Map?)?['regional'] as Map?;
  reg?.forEach((place, list) {
    if (toI(w.placeById['$place']?['chapter'] ?? 0) == ch) {
      for (final it in (list as List)) {
        if (const ['food', 'drink'].contains(w.itemType('$it'))) regional.add('$it');
      }
    }
  });
  final items = [...regional, 'matches', 'hand_warmers'].where((i) => w.itemSpec(i).isNotEmpty).toList();
  final item = items.isEmpty ? null : items[rnd.nextInt(items.length)];

  history.addAll(['k:$kind', '$kind:t:$ti', 'f$ch:$fi']);
  if (history.length > 300) history.removeRange(0, history.length - 300);
  return {
    'kind': kind,
    'start': today,
    'end': addDays(today, 6),
    'chapter': ch,
    'title': ti,
    'flavor': fi,
    'target': target,
    'steps': steps,
    'place': reachPlace ?? '',
    'coins': coins,
    'item': item ?? '',
    'startPos': h.pos,
    'startNotebook': notebookCount(p),
    'startThoughts': thoughtsCount(p),
    'startCold': coldCount(h),
    'failed': false,
    'state': 'active', // active | done | claimed
  };
}

/// Прогресс: (сколько, из скольки). Для calm/nocold — прожитые без срыва дни.
(int, int) challengeProgress(GameContent content, HeroState h, Profile p, Json c, String today) {
  final kind = '${c['kind']}';
  final start = '${c['start']}';
  final end = '${c['end']}';
  final target = toI(c['target']);
  final steps = toI(c['steps']);
  List<int> week() {
    final out = <int>[];
    for (var i = 0; i < 7; i++) {
      final d = addDays(start, i);
      if (d.compareTo(today) > 0) break;
      out.add(h.daySteps[d] ?? 0);
    }
    return out;
  }

  switch (kind) {
    case 'km':
      return (((h.pos - toD(c['startPos'])) / 1000).floor().clamp(0, 1 << 30), target);
    case 'streak':
      var best = 0;
      var run = 0;
      for (final v in week()) {
        run = v >= steps ? run + 1 : 0;
        best = math.max(best, run);
      }
      return (best, target);
    case 'bigday':
      return (week().any((v) => v >= steps) ? 1 : 0, 1);
    case 'steady':
      return (week().where((v) => v >= steps).length, target);
    case 'reach':
      final pos = content.world.posOf['${c['place']}'];
      return (pos != null && h.maxPos >= pos - 0.5 ? 1 : 0, 1);
    case 'calm':
    case 'nocold':
      if (c['failed'] == true) return (0, 7);
      final passed = DateTime.parse(today.compareTo(end) > 0 ? end : today).difference(DateTime.parse(start)).inDays + 1;
      return (passed.clamp(0, 7), 7);
    case 'notebook':
      return ((notebookCount(p) - toI(c['startNotebook'])).clamp(0, 1 << 30), target);
    case 'thoughts':
      return ((thoughtsCount(p) - toI(c['startThoughts'])).clamp(0, 1 << 30), target);
  }
  return (0, 1);
}

/// Срыв для calm/nocold: показатель ниже 25 или экстренный привал за неделю.
bool challengeBroken(HeroState h, Json c) {
  switch ('${c['kind']}') {
    case 'calm':
      return statKeys.any((k) => (h.stats[k] ?? 100) < 25);
    case 'nocold':
      return coldCount(h) > toI(c['startCold']);
  }
  return false;
}

/// calm/nocold засчитываются только в последний день недели — остальные как только цель достигнута.
bool challengeWaitsForWeekEnd(Json c) => c['kind'] == 'calm' || c['kind'] == 'nocold';

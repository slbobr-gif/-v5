// Статистика конца главы и итога пути. Чистый Dart: считается из HeroState.marks (отметки концов глав,
// Engine._mark) и HeroState.daySteps (реальные шаги по дням). Пересчёта шагов нет — это то, что прошёл игрок.

import 'state.dart';
import 'world.dart';

/// Одна глава: всё о реальных шагах игрока; км главы — игровой путь Сергея.
class ChapterStats {
  ChapterStats({
    required this.chapter,
    required this.km,
    required this.days,
    required this.steps,
    required this.distKm,
    required this.bestSteps,
    required this.bestDay,
    required this.events,
    required this.deaths,
    required this.leftKm,
    required this.passedKm,
    required this.totalKm,
  });

  final int chapter;

  /// Игровые км главы (от начала до конца главы на маршруте).
  final double km;

  /// Календарных дней игрока на главу (не меньше 1).
  final int days;

  /// Реальных шагов игрока за главу.
  final int steps;

  /// Реальное расстояние игрока, км (шаги × длина шага).
  final double distKm;

  /// Лучший день главы: шагов и дата (yyyy-MM-dd), null — шагов не было.
  final int bestSteps;
  final String? bestDay;

  final int events;
  final int deaths;

  /// Сколько игровых км осталось до Териберки после главы, сколько пройдено всего и длина пути.
  final double leftKm;
  final double passedKm;
  final double totalKm;

  double get share => totalKm <= 0 ? 0 : (passedKm / totalKm).clamp(0.0, 1.0);
}

/// Весь путь.
class JourneyStats {
  JourneyStats({
    required this.days,
    required this.steps,
    required this.distKm,
    required this.bestSteps,
    required this.bestDay,
    required this.events,
    required this.deaths,
    required this.questsDone,
    required this.questsTotal,
    required this.randomTotal,
    required this.randomSeen,
    required this.startDay,
    required this.endDay,
    required this.totalKm,
    required this.chapters,
  });

  final int days;
  final int steps;
  final double distKm;
  final int bestSteps;
  final String? bestDay;
  final int events;
  final int deaths;
  final int questsDone;
  final int questsTotal;
  final int randomTotal;
  final int randomSeen;
  final String startDay;
  final String endDay;
  final double totalKm;
  final List<ChapterStats> chapters;

  int get randomUnseen => (randomTotal - randomSeen).clamp(0, randomTotal);

  Json toJson() => {
        'days': days,
        'steps': steps,
        'distKm': distKm,
        'bestSteps': bestSteps,
        'bestDay': bestDay,
        'events': events,
        'deaths': deaths,
        'questsDone': questsDone,
        'questsTotal': questsTotal,
        'startDay': startDay,
        'endDay': endDay,
        'chapters': [
          for (final c in chapters) {'ch': c.chapter, 'km': c.km, 'days': c.days, 'steps': c.steps},
        ],
      };
}

DateTime _date(String key) {
  final p = key.split('-');
  if (p.length != 3) return DateTime.utc(1970);
  return DateTime.utc(int.tryParse(p[0]) ?? 1970, int.tryParse(p[1]) ?? 1, int.tryParse(p[2]) ?? 1);
}

/// Полных дней между датами yyyy-MM-dd (b − a).
int dayDiff(String a, String b) => _date(b).difference(_date(a)).inDays;

double _stepLengthM(World w) => toD(((w.balance['movement'] as Map)['stepLengthM']));

(int, String?) _best(HeroState s, String? after, String upTo) {
  var best = 0;
  String? day;
  for (final e in s.daySteps.entries) {
    final k = e.key;
    if (after != null && k.compareTo(after) <= 0) continue;
    if (after == null && k.compareTo(s.startDay) < 0) continue;
    if (k.compareTo(upTo) > 0) continue;
    if (e.value > best) {
      best = e.value;
      day = k;
    }
  }
  return (best, day);
}

Json? _markOf(HeroState s, int ch) {
  for (final m in s.marks) {
    if (toI(m['ch']) == ch) return m;
  }
  return null;
}

/// Статистика главы [ch]; null — глава ещё не закончена (нет отметки).
ChapterStats? chapterStats(World w, HeroState s, int ch) {
  final m = _markOf(s, ch);
  if (m == null) return null;
  final prev = ch > 1 ? _markOf(s, ch - 1) : null;
  final day = '${m['day']}';
  final prevDay = prev == null ? null : '${prev['day']}';
  final days = prevDay == null ? dayDiff(s.startDay, day) + 1 : dayDiff(prevDay, day);
  final steps = toI(m['steps']) - (prev == null ? 0 : toI(prev['steps']));
  final (best, bestDay) = _best(s, prevDay, day);
  final total = w.chapterEndPos(w.chapters.length);
  final end = w.chapterEndPos(ch);
  return ChapterStats(
    chapter: ch,
    km: (end - w.chapterStartPos(ch)) / 1000.0,
    days: days < 1 ? 1 : days,
    steps: steps < 0 ? 0 : steps,
    distKm: (steps < 0 ? 0 : steps) * _stepLengthM(w) / 1000.0,
    bestSteps: best,
    bestDay: bestDay,
    events: toI(m['events']) - (prev == null ? 0 : toI(prev['events'])),
    deaths: toI(m['deaths']) - (prev == null ? 0 : toI(prev['deaths'])),
    leftKm: (total - end) / 1000.0,
    passedKm: end / 1000.0,
    totalKm: total / 1000.0,
  );
}

/// Итог всего пути. [today] — день, которым закончить подсчёт, если финиша ещё нет.
JourneyStats journeyStats(World w, HeroState s, {String? today}) {
  final last = _markOf(s, w.chapters.length);
  final days = s.daySteps.keys.toList()..sort();
  final endDay = last != null ? '${last['day']}' : (today ?? (days.isEmpty ? s.startDay : days.last));
  var steps = 0;
  for (final d in days) {
    if (d.compareTo(endDay) <= 0) steps += s.daySteps[d]!;
  }
  final (best, bestDay) = _best(s, null, endDay);
  final randomIds = {for (final e in w.randoms) e['id'] as String};
  final seenRandom = s.seen.where(randomIds.contains).length;
  final n = dayDiff(s.startDay, endDay) + 1;
  return JourneyStats(
    days: n < 1 ? 1 : n,
    steps: steps,
    distKm: steps * _stepLengthM(w) / 1000.0,
    bestSteps: best,
    bestDay: bestDay,
    events: s.eventsDone,
    deaths: s.deaths,
    questsDone: s.questsDone,
    questsTotal: w.quests.length,
    randomTotal: randomIds.length,
    randomSeen: seenRandom,
    startDay: s.startDay,
    endDay: endDay,
    totalKm: w.chapterEndPos(w.chapters.length) / 1000.0,
    chapters: [
      for (var ch = 1; ch <= w.chapters.length; ch++)
        if (chapterStats(w, s, ch) case final c?) c,
    ],
  );
}

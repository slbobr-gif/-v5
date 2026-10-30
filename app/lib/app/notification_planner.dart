// План локальных уведомлений: утренняя мысль + 1–3 событийных в день.

import 'package:flutter/widgets.dart';

import '../data/content_repository.dart';
import '../data/storage.dart';
import '../engine/state.dart';
import '../engine/world.dart';
import '../l10n/app_localizations.dart';
import '../platform/notify_platform.dart';

class NotificationTexts {
  NotificationTexts(this.l);
  factory NotificationTexts.ru() => NotificationTexts(lookupAppLocalizations(const Locale('ru')));
  final AppLocalizations l;
}

class NotificationPlanner {
  NotificationPlanner({
    required this.content,
    required this.hero,
    required this.profile,
    required this.texts,
    required this.journeyDayOf,
    this.sentPerDay = const {},
  });

  final GameContent content;
  final HeroState hero;
  final Profile profile;
  final NotificationTexts texts;
  final int Function(DateTime) journeyDayOf;

  /// Событийные уведомления, уже показанные по прошлым планам: {yyyy-MM-dd: штук}.
  final Map<String, int> sentPerDay;

  static String dayOf(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Json get _n => (content.world.balance['notifications'] as Map).cast<String, dynamic>();

  (int, int) _hm(String v) {
    final p = v.split(':');
    return (int.parse(p[0]), int.parse(p[1]));
  }

  bool _quiet(DateTime t) {
    final (qsH, qsM) = _hm(_n['quietStart'] as String);
    final (qeH, qeM) = _hm(_n['quietEnd'] as String);
    final m = t.hour * 60 + t.minute;
    final s = qsH * 60 + qsM;
    final e = qeH * 60 + qeM;
    return s > e ? (m >= s || m < e) : (m >= s && m < e);
  }

  /// Сдвигает время из тихих часов на их конец (+20 минут).
  DateTime _outOfQuiet(DateTime t) {
    if (!_quiet(t)) return t;
    final (qeH, qeM) = _hm(_n['quietEnd'] as String);
    var d = DateTime(t.year, t.month, t.day, qeH, qeM).add(const Duration(minutes: 20));
    if (!d.isAfter(t)) d = d.add(const Duration(days: 1));
    return d;
  }

  String _short(String s, int max) => s.length <= max ? s : '${s.substring(0, max - 1).trimRight()}…';

  List<PlannedNotification> plan(DateTime now) {
    final l = texts.l;
    final out = <PlannedNotification>[];
    // План пересобирается при каждом обновлении — учитываем уже показанные сегодня, иначе лимит обходится.
    final perDay = Map<String, int>.from(sentPerDay);
    final maxEvent = toI(_n['maxEventPerDay']);

    bool addEvent(PlannedNotification n) {
      final k = dayOf(n.at);
      if ((perDay[k] ?? 0) >= maxEvent) return false;
      perDay[k] = (perDay[k] ?? 0) + 1;
      out.add(n);
      return true;
    }

    // 1. Утренняя мысль — на 7 дней вперёд
    for (var d = 0; d < 7; d++) {
      final day = DateTime(now.year, now.month, now.day).add(Duration(days: d));
      final at = DateTime(day.year, day.month, day.day, profile.morningHour, profile.morningMinute);
      if (!at.isAfter(now)) continue;
      final t = content.thoughtForDay(journeyDayOf(at));
      out.add(PlannedNotification(
        id: 100 + d,
        at: at,
        title: l.notifMorningTitle,
        body: _short('«${t.quote}» — ${t.author}', 170),
      ));
    }

    if (hero.finished) return out;

    // 2. Ждущая остановка — напомнить через 3 часа
    final stop = hero.stop;
    if (stop != null) {
      final at = _outOfQuiet(now.add(Duration(hours: toI(_n['pendingReminderHours']))));
      String body;
      switch (stop['type']) {
        case 'event':
          final ev = content.world.eventsById[stop['event']];
          body = l.notifStopEvent((ev?['title'] as String?) ?? '');
        case 'place':
        case 'chapter_end':
          body = l.notifStopPlace(content.placeName('${stop['place']}'));
        case 'death':
          body = l.notifStopDeath;
        default:
          body = l.notifStopGeneric;
      }
      addEvent(PlannedNotification(id: 200, at: at, title: l.notifStopTitle, body: body));
    }

    // 3. Конец задержки
    if (hero.delayUntil > now.millisecondsSinceEpoch) {
      final at = _outOfQuiet(DateTime.fromMillisecondsSinceEpoch(hero.delayUntil));
      addEvent(PlannedNotification(id: 201, at: at, title: l.notifDelayTitle, body: l.notifDelayBody));
    }

    // 4. Показатели проседают — днём в 13:00
    final low = statKeys.where((k) => (hero.stats[k] ?? 100) < 40).toList();
    if (low.isNotEmpty && stop == null) {
      var at = DateTime(now.year, now.month, now.day, 13, 0);
      if (!at.isAfter(now)) at = at.add(const Duration(days: 1));
      final body = switch (low.first) {
        'satiety' => l.notifLowSatiety,
        'water' => l.notifLowWater,
        _ => l.notifLowWarmth,
      };
      addEvent(PlannedNotification(id: 400, at: at, title: l.notifLowTitle, body: body));
    }

    // 5. Вечерний зов — на 2 дня вперёд в 19:00
    final calls = [l.notifEvening1, l.notifEvening2, l.notifEvening3];
    for (var d = 0; d < 2; d++) {
      final day = DateTime(now.year, now.month, now.day).add(Duration(days: d));
      final at = DateTime(day.year, day.month, day.day, 19, 0);
      if (!at.isAfter(now)) continue;
      addEvent(PlannedNotification(
        id: 300 + d,
        at: at,
        title: l.notifEveningTitle,
        body: calls[(journeyDayOf(at) + d) % calls.length],
      ));
    }
    return out;
  }
}

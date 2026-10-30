// Состояние приложения: связывает шагомер, движок, сохранение, уведомления и аналитику.

import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../analytics/analytics.dart';
import '../data/content_repository.dart';
import '../data/storage.dart';
import '../engine/engine.dart';
import '../engine/state.dart';
import '../engine/world.dart';
import '../platform/notify_platform.dart';
import '../platform/steps_platform.dart';
import 'notification_planner.dart';

String dayKey(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Что изменилось после выбора в событии — для экрана исхода.
class OutcomeView {
  OutcomeView({
    required this.text,
    required this.coins,
    required this.stats,
    required this.itemsGained,
    required this.itemsLost,
    required this.died,
    required this.delayHours,
    required this.detourKm,
    required this.shortcutKm,
  });

  final String text;
  final int coins;
  final Map<String, int> stats;
  final Map<String, int> itemsGained;
  final Map<String, int> itemsLost;
  final bool died;
  final double delayHours;
  final double detourKm;
  final double shortcutKm;
}

class AppModel {
  const AppModel({
    this.loading = true,
    this.error,
    this.content,
    this.storage,
    this.profile,
    this.hero,
    this.stepsStatus = const StepsStatus(),
    this.todaySteps = 0,
    this.lastSyncSources = const {},
    this.notifyPermission = false,
    this.rev = 0,
  });

  final bool loading;
  final String? error;
  final GameContent? content;
  final Storage? storage;
  final Profile? profile;
  final HeroState? hero;
  final StepsStatus stepsStatus;
  final int todaySteps;

  /// Сколько шагов сегодня дал каждый источник: {sensor: n, hc: n}.
  final Map<String, int> lastSyncSources;
  final bool notifyPermission;

  /// Номер ревизии: состояние героя изменяется на месте, ревизия заставляет перерисоваться.
  final int rev;

  AppModel copyWith({
    bool? loading,
    String? error,
    GameContent? content,
    Storage? storage,
    Profile? profile,
    HeroState? hero,
    bool clearHero = false,
    StepsStatus? stepsStatus,
    int? todaySteps,
    Map<String, int>? lastSyncSources,
    bool? notifyPermission,
  }) =>
      AppModel(
        loading: loading ?? this.loading,
        error: error ?? this.error,
        content: content ?? this.content,
        storage: storage ?? this.storage,
        profile: profile ?? this.profile,
        hero: clearHero ? null : (hero ?? this.hero),
        stepsStatus: stepsStatus ?? this.stepsStatus,
        todaySteps: todaySteps ?? this.todaySteps,
        lastSyncSources: lastSyncSources ?? this.lastSyncSources,
        notifyPermission: notifyPermission ?? this.notifyPermission,
        rev: rev + 1,
      );
}

final appProvider = NotifierProvider<AppController, AppModel>(AppController.new);

class AppController extends Notifier<AppModel> {
  final StepsPlatform _steps = StepsPlatform();
  final NotifyPlatform _notify = NotifyPlatform();
  final Analytics _a = Analytics.instance;
  bool _syncing = false;
  NotificationTexts? texts;

  @override
  AppModel build() => const AppModel();

  GameContent get content => state.content!;
  Storage get _storage => state.storage!;
  Engine? get engine => state.hero == null ? null : Engine(content.world, state.hero!);

  int get _now => DateTime.now().millisecondsSinceEpoch;
  String get today => dayKey(DateTime.now());

  // ------------------------------------------------ запуск
  Future<void> init() async {
    try {
      await _a.init();
      texts = NotificationTexts.ru();
      final prefs = await SharedPreferences.getInstance();
      final storage = Storage(prefs);
      final content = await loadGameContent();
      final profile = storage.loadProfile();
      final hero = storage.loadHero();
      if (hero != null) _dropBrokenStop(content, hero);
      state = state.copyWith(loading: false, content: content, storage: storage, profile: profile, hero: hero);
      _a.event('app_open', {'has_journey': hero != null});
      await refreshPermissions();
      if (hero != null) await refresh();
    } catch (e) {
      state = state.copyWith(loading: false, error: '$e');
    }
  }

  /// Остановка-событие, которого нет в контенте (новая сборка переименовала или убрала событие),
  /// навсегда остановила бы героя: выбрать нечего, а «Идти дальше» событие не закрывает. Снимаем её.
  void _dropBrokenStop(GameContent content, HeroState hero) {
    final st = hero.stop;
    if (st == null || st['type'] != 'event') return;
    if (Engine(content.world, hero).currentEvent() == null) hero.stop = null;
  }

  /// Если приложение открыли из уведомления — отправить событие (утренняя мысль, остановка, вечер…).
  Future<void> trackNotificationOpen() async {
    final id = await _notify.consumeOpened();
    if (id == null) return;
    final kind = id >= 100 && id < 200
        ? 'morning'
        : switch (id) {
            200 => 'stop',
            201 => 'delay',
            300 || 301 => 'evening',
            400 => 'low_stats',
            _ => 'other',
          };
    _a.event('notif_opened', {'id': id, 'kind': kind});
  }

  Future<void> refreshPermissions() async {
    final st = await _steps.status();
    final np = await _notify.hasPermission();
    state = state.copyWith(stepsStatus: st, notifyPermission: np);
  }

  // ------------------------------------------------ профиль и онбординг
  Future<void> saveProfile({required String name, required String email, required bool consent}) async {
    final p = state.profile ?? Profile();
    p
      ..name = name.trim()
      ..email = email.trim()
      ..consent = consent;
    await _storage.saveProfile(p);
    await _a.setProfile(email: p.email, consent: consent);
    _a.event('profile_saved', {'has_email': p.email.isNotEmpty, 'consent': consent});
    state = state.copyWith(profile: p);
  }

  Future<void> updateProfile(void Function(Profile p) change) async {
    final p = state.profile ?? Profile();
    change(p);
    await _storage.saveProfile(p);
    state = state.copyWith(profile: p);
    await _replanNotifications();
  }

  void onboardingSlide(int index) => _a.event('onboarding_slide', {'n': index + 1});

  Future<bool> requestActivityPermission() async {
    final ok = await _steps.requestActivityPermission();
    _a.event('perm_activity', {'granted': ok});
    if (ok) await _steps.startBackgroundTracking();
    await refreshPermissions();
    return ok;
  }

  Future<bool> requestHealthPermission() async {
    final ok = await _steps.requestHealthPermission();
    _a.event('perm_health_connect', {'granted': ok, 'status': state.stepsStatus.hcStatus});
    await refreshPermissions();
    return ok;
  }

  Future<void> openHealthConnectInstall() => _steps.openHealthConnectInstall();

  Future<bool> requestNotifyPermission() async {
    final ok = await _notify.requestPermission();
    _a.event('perm_notifications', {'granted': ok});
    await refreshPermissions();
    await _replanNotifications();
    return ok;
  }

  Future<void> markPrologueRead() => updateProfile((p) => p.prologueRead = true);

  /// Старт путешествия: шаги, сделанные сегодня до старта, не засчитываются.
  Future<void> startJourney() async {
    final ds = await _steps.dailySteps(days: 2);
    final baseline = ds.days[today] ?? 0;
    final seed = math.Random().nextInt(0x7FFFFFFF);
    final hero = HeroState.create(content.world, seed, _now, today, todaySteps: baseline);
    await _storage.saveHero(hero);
    await updateProfile((p) => p.onboarded = true);
    await _steps.startBackgroundTracking();
    _a.event('journey_start', {
      'sensor': state.stepsStatus.sensorAvailable && state.stepsStatus.activityPermission,
      'health_connect': state.stepsStatus.hcPermission,
    });
    state = state.copyWith(hero: hero);
    await refresh();
  }

  // ------------------------------------------------ главная петля
  Future<void> refresh() async {
    if (_syncing || state.hero == null) return;
    _syncing = true;
    try {
      final hero = state.hero!;
      final ds = await _steps.dailySteps(days: 30);
      // Пока ждали шагомер, путь могли сбросить — не воскрешаем старого героя.
      if (!identical(state.hero, hero)) return;
      // Движок создаём после ожидания: за это время выбор в событии мог сдвинуть состояние ГСЧ.
      final eng = Engine(content.world, hero);
      final coinsBefore = hero.coins;
      final added = eng.syncSteps(ds.days, _now);
      final goalCoins = hero.coins - coinsBefore;
      final bonusBefore = eng.inBonus();
      final noticedBefore = eng.noticed();
      final evs = eng.advance(_now);
      if (!bonusBefore && eng.inBonus()) _a.event('bonus_started');
      if (!noticedBefore && eng.noticed()) _a.event('bonus_noticed', {'km': hero.bonusKm.round()});
      if (added > 0) {
        _a.event('steps_synced', {
          'added': added,
          'sensor_today': ds.sensor[today] ?? 0,
          'hc_today': ds.hc[today] ?? 0,
        });
      }
      if (goalCoins > 0) {
        _a.event('goal_reached', {'coins': goalCoins});
      }
      for (final e in evs) {
        _trackStop(e, hero);
      }
      // Без await до обновления состояния: сброс пути не должен вклиниться между проверкой и записью.
      final saving = _storage.saveHero(hero);
      state = state.copyWith(
        hero: hero,
        todaySteps: ds.days[today] ?? 0,
        lastSyncSources: {'sensor': ds.sensor[today] ?? 0, 'hc': ds.hc[today] ?? 0},
      );
      await saving;
      await _replanNotifications();
    } finally {
      _syncing = false;
    }
  }

  void _trackStop(EngineEvent e, HeroState hero) {
    if (e.type == 'death') {
      _a.event('death', {'cause': hero.stop?['cause'] ?? 'stats', 'chapter': content.world.chapterAt(hero.pos)});
      return;
    }
    final st = e.stop;
    if (st == null) return;
    switch (st['type']) {
      case 'event':
        final ev = content.world.eventsById[st['event']];
        _a.event('event_shown', {
          'id': '${st['event']}',
          'kind': '${ev?['kind'] ?? 'quest'}',
          'chapter': content.world.chapterAt(hero.pos),
        });
      case 'place':
        _a.event('place_arrived', {'id': '${st['place']}'});
      case 'chapter_end':
        // После смерти с откатом герой снова проходит конец главы — в статистику только первый раз.
        if (hero.pos >= hero.maxPos - 0.5) _a.event('chapter_done', {'chapter': toI(st['chapter'])});
      case 'finish':
        _a.event('journey_finished', {'days': hero.daySteps.length});
    }
  }

  void _commit() {
    final hero = state.hero!;
    _storage.saveHero(hero);
    state = state.copyWith(hero: hero);
    _replanNotifications();
  }

  int claimLogin() {
    final eng = engine;
    if (eng == null) return 0;
    final c = eng.claimLogin(today, _now);
    if (c > 0) {
      _a.event('login_claimed', {'coins': c});
      _commit();
    }
    return c;
  }

  /// Выбор в событии. Возвращает описание последствий.
  OutcomeView? choose(String choiceId) {
    final eng = engine;
    if (eng == null) return null;
    final hero = state.hero!;
    final ev = eng.currentEvent();
    if (ev == null) return null;
    final coins0 = hero.coins;
    final stats0 = Map<String, double>.from(hero.stats);
    final inv0 = Map<String, int>.from(hero.inv);
    final delay0 = hero.delayUntil;
    final detour0 = hero.detour?.remaining ?? 0;
    final pos0 = hero.pos;
    final res = eng.choose(choiceId, _now);
    if (!res.ok) return null;
    final eff = (res.outcome?['effects'] as Map?)?.cast<String, dynamic>() ?? const {};
    final gained = <String, int>{};
    final lost = <String, int>{};
    final keys = {...inv0.keys, ...hero.inv.keys};
    for (final k in keys) {
      final d = (hero.inv[k] ?? 0) - (inv0[k] ?? 0);
      if (d > 0) gained[k] = d;
      if (d < 0 && !res.died) lost[k] = -d;
    }
    final view = OutcomeView(
      text: (res.outcome?['text'] as String?) ?? '',
      coins: res.died ? 0 : hero.coins - coins0,
      stats: res.died
          ? const {}
          : {for (final k in statKeys) k: (hero.stats[k]! - stats0[k]!).round()},
      itemsGained: gained,
      itemsLost: lost,
      died: res.died,
      delayHours: hero.delayUntil > delay0 ? (hero.delayUntil - _now) / msHour : 0,
      detourKm: (hero.detour?.remaining ?? 0) > detour0 ? hero.detour!.remaining / 1000 : 0,
      shortcutKm: (!res.died && eff['shortcut'] != null) ? (hero.pos - pos0) / 1000 : 0,
    );
    _a.event('event_choice', {
      'id': '${ev['id']}',
      'choice': choiceId,
      'risk': '${res.choice?['risk'] ?? 'none'}',
      'died': res.died,
    });
    if (eff['quest_start'] != null) _a.event('quest_started', {'id': '${eff['quest_start']}'});
    if (res.died) {
      _a.event('death', {'cause': 'event', 'chapter': content.world.chapterAt(hero.pos)});
    }
    _commit();
    return view;
  }

  /// После экрана исхода — герой идёт дальше на остаток шагов.
  Future<void> afterEvent() async {
    final eng = engine;
    if (eng == null) return;
    final evs = eng.advance(_now);
    for (final e in evs) {
      _trackStop(e, state.hero!);
    }
    _commit();
  }

  /// [from] — остановка, которую видел экран: повторное нажатие после смены остановки игнорируется
  /// (иначе двойной тап на конце главы пропускает рынок).
  Future<void> continueJourney([Json? from]) async {
    final eng = engine;
    if (eng == null) return;
    if (from != null && !identical(state.hero!.stop, from)) return;
    eng.continueJourney(_now);
    if (state.hero!.stop == null) {
      final evs = eng.advance(_now);
      for (final e in evs) {
        _trackStop(e, state.hero!);
      }
    }
    _commit();
  }

  Future<void> dismissDeath() async {
    final hero = state.hero;
    // Только со смерти: повторное нажатие не должно снять следующую остановку (событие пропало бы навсегда).
    if (hero == null || hero.stop?['type'] != 'death') return;
    hero.stop = null;
    _a.event('respawn', {'deaths': hero.deaths});
    final evs = engine!.advance(_now);
    for (final e in evs) {
      _trackStop(e, hero);
    }
    _commit();
  }

  bool buy(String item) {
    final eng = engine;
    if (eng == null) return false;
    final price = eng.market().where((o) => o.item == item).map((o) => o.price).firstOrNull ?? 0;
    final ok = eng.buy(item, _now);
    if (ok) {
      _a.event('buy', {'item': item, 'price': price});
      _commit();
    }
    return ok;
  }

  bool useItem(String item) {
    final eng = engine;
    if (eng == null) return false;
    final ok = eng.useItem(item, _now);
    if (ok) {
      _a.event('item_used', {'item': item});
      _commit();
    }
    return ok;
  }

  // ------------------------------------------------ утренние мысли
  int journeyDay() {
    final hero = state.hero;
    if (hero == null) return 1;
    final start = DateTime.parse(hero.startDay);
    final now = DateTime.now();
    final d = DateTime(now.year, now.month, now.day).difference(DateTime(start.year, start.month, start.day)).inDays;
    return d + 1;
  }

  bool thoughtSeenToday() => state.storage?.lastThoughtSeenDay() == today;

  Future<void> markThoughtSeen(int day) async {
    await _storage.setThoughtSeenDay(today);
    _a.event('thought_read', {'day': day});
    state = state.copyWith();
  }

  Map<String, Json> answers() => state.storage?.loadAnswers() ?? {};

  Future<void> saveAnswer(int day, String text, {required bool open}) async {
    final a = answers();
    a['$day'] = {'text': text.trim(), 'at': _now};
    await _storage.saveAnswers(a);
    _a.event('thought_answered', {'day': day, 'open': open, 'length': text.trim().length});
    state = state.copyWith();
  }

  // ------------------------------------------------ опрос и настройки
  Future<void> answerSurvey(String answer) async {
    _a.event('survey_pay_149', {'answer': answer});
    await updateProfile((p) => p.surveyAnswered = true);
    await _a.flush();
  }

  bool shouldAskSurvey() {
    final p = state.profile;
    final hero = state.hero;
    if (p == null || hero == null || p.surveyAnswered) return false;
    final ch1Done = hero.pos >= content.world.chapterEndPos(1);
    return ch1Done || journeyDay() >= 8;
  }

  Future<void> resetJourney() async {
    _a.event('journey_reset');
    await _storage.resetJourney();
    await updateProfile((p) {
      p.onboarded = false;
      p.prologueRead = false;
    });
    state = state.copyWith(clearHero: true);
    await _notify.replaceAll(const []);
  }

  // ------------------------------------------------ уведомления
  Future<void> _replanNotifications() async {
    final p = state.profile;
    final hero = state.hero;
    final t = texts;
    if (p == null || hero == null || t == null || state.content == null) return;
    // Событийные из прошлого плана, чьё время прошло, уже показаны — засчитываем их в лимит дня.
    final nowMs = _now;
    final sent = _storage.loadNotifSent();
    for (final at in _storage.loadNotifPlanned()) {
      if (at <= nowMs) {
        final k = NotificationPlanner.dayOf(DateTime.fromMillisecondsSinceEpoch(at));
        sent[k] = (sent[k] ?? 0) + 1;
      }
    }
    sent.removeWhere((k, _) => k.compareTo(today) < 0);
    if (!p.notifications) {
      final saving = _storage.saveNotifState(sent, const []);
      await _notify.replaceAll(const []);
      await saving;
      return;
    }
    final list = NotificationPlanner(
      content: content,
      hero: hero,
      profile: p,
      texts: t,
      journeyDayOf: (d) {
        final start = DateTime.parse(hero.startDay);
        return DateTime(d.year, d.month, d.day).difference(DateTime(start.year, start.month, start.day)).inDays + 1;
      },
      sentPerDay: sent,
    ).plan(DateTime.fromMillisecondsSinceEpoch(nowMs));
    final planned = [
      for (final n in list)
        if (n.id >= 200 && n.at.millisecondsSinceEpoch > nowMs) n.at.millisecondsSinceEpoch,
    ];
    final saving = _storage.saveNotifState(sent, planned);
    await _notify.replaceAll(list);
    await saving;
  }

  Future<void> replanNow() => _replanNotifications();
}

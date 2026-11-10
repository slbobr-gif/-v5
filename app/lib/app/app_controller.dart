// Состояние приложения: связывает шагомер, движок, сохранение, уведомления и аналитику.

import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../analytics/analytics.dart';
import '../data/content_repository.dart';
import '../data/storage.dart';
import '../engine/engine.dart';
import '../engine/journey_stats.dart';
import '../engine/state.dart';
import '../engine/world.dart';
import '../platform/notify_platform.dart';
import '../platform/steps_platform.dart';
import 'journal_view.dart';
import 'notification_planner.dart';
import 'ui_flags.dart';

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
    this.itemsPending = const {},
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

  /// Вещи, которые не поместились и ждут решения (hero.overflow): {id: штук}.
  final Map<String, int> itemsPending;
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
    this.lastSteps,
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

  /// Последнее чтение шагов целиком (для экрана диагностики в настройках).
  final DailySteps? lastSteps;
  final bool notifyPermission;

  /// Номер ревизии: состояние героя изменяется на месте, ревизия заставляет перерисоваться.
  final int rev;

  // ------------------------------------------------ удобные геттеры v5.3 для экранов (без логики)
  Engine? get engine => (hero == null || content == null) ? null : Engine(content!.world, hero!);

  /// Первая вещь, ждущая решения (экраны переполнения поверх всего, пока не null).
  OverflowItem? get pendingOverflow => (hero == null || hero!.overflow.isEmpty) ? null : hero!.overflow.first;

  /// Зона под героем: city | suburb | wild.
  String get zone => engine?.zoneHere() ?? 'city';

  bool get heated => engine?.isHeated(DateTime.now().millisecondsSinceEpoch) ?? false;
  String get heatStatus => engine?.heatStatus(DateTime.now().millisecondsSinceEpoch) ?? 'no_stove';
  String get clewStatus => engine?.clewStatus(DateTime.now().millisecondsSinceEpoch) ?? 'no_item';
  bool get clewReady => clewStatus == 'ready';

  int get clewCooldownDays => engine?.clewCooldownDays(DateTime.now().millisecondsSinceEpoch) ?? 0;

  /// Чей голос подскажет сейчас (подпись gearClewAsk_<id>); null — никто.
  String? get clewItem => engine?.clewItem(DateTime.now().millisecondsSinceEpoch);

  /// Есть что отменить «Сучком»/«Бусиной» (экран исхода).
  bool get hasUndo => hero?.undo != null;

  Map<String, int> get gearUses => hero?.gearUses ?? const {};
  Map<String, int> get portionsLeft => hero?.portionsLeft ?? const {};

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
    DailySteps? lastSteps,
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
        lastSteps: lastSteps ?? this.lastSteps,
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

  /// Набор с экрана «Собери рюкзак» (до создания героя); null — не выбирали (возьмётся loadout.default).
  ({List<String> gear, Map<String, int> pack, bool isDefault})? _chosenLoadout;

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
      // С миром: старое сохранение (v1, до v5.3) переводится в v2 — снаряжение из inv переезжает в gear.
      final hero = storage.loadHero(content.world);
      if (hero != null) _dropBrokenStop(content, hero);
      _chosenLoadout = _readLoadout(storage.loadLoadout());
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

  bool get _useSensor => state.profile?.stepsSensor ?? true;
  bool get _useHc => state.profile?.stepsHc ?? true;

  /// Переключатели «Откуда брать шаги». Датчик в фоне копит данные при любом значении,
  /// переключатель меняет только то, что засчитывается в путь.
  Future<void> setStepSources({required bool sensor, required bool hc}) async {
    await updateProfile((p) {
      p.stepsSensor = sensor;
      p.stepsHc = hc;
    });
    _a.event('steps_source_changed', {'sensor': sensor, 'hc': hc});
    await refresh();
  }

  /// Соотношение шагов: сколько игровых шагов за один реальный (1, 3 или 5).
  int get stepMul => state.profile?.stepMul ?? 5;

  /// Меняет соотношение. Уже пройденный путь не пересчитывается: новое значение действует на следующие шаги.
  Future<void> setStepMul(int v) async {
    if (!const [1, 3, 5].contains(v)) return;
    final hero = state.hero;
    // Сначала засчитываем накопленные шаги по старому соотношению, чтобы они не пересчитались по новому.
    if (hero != null) await refresh();
    await updateProfile((p) => p.stepMul = v);
    final h = state.hero;
    if (h != null) {
      h.stepMul = v;
      await _save(h);
      state = state.copyWith(hero: h);
    }
    _a.event('step_ratio_changed', {'mul': v});
  }

  Future<bool> requestNotifyPermission() async {
    final ok = await _notify.requestPermission();
    _a.event('perm_notifications', {'granted': ok});
    await refreshPermissions();
    await _replanNotifications();
    return ok;
  }

  Future<void> markPrologueRead() => updateProfile((p) => p.prologueRead = true);

  // ------------------------------------------------ старт-набор («Собери рюкзак»)
  ({List<String> gear, Map<String, int> pack, bool isDefault})? _readLoadout(Json? j) {
    if (j == null) return null;
    try {
      final gear = ((j['gear'] as List?) ?? const []).map((e) => '$e').toList();
      final pack = ((j['pack'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', toI(v)));
      return (gear: gear, pack: pack, isDefault: j['default'] == true);
    } catch (_) {
      return null;
    }
  }

  /// balance.loadout.default — кнопка «Как посоветовал бы бывалый».
  ({List<String> gear, Map<String, int> pack}) get defaultLoadout {
    final lo = (content.world.balance['loadout'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final d = (lo['default'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    return (
      gear: ((d['gear'] as List?) ?? const []).map((e) => '$e').toList(),
      pack: ((d['pack'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', toI(v))),
    );
  }

  /// Каталог старта и ограничения — для экрана «Собери рюкзак».
  List<String> get starterGear => content.world.starterGear;
  List<String> get starterPack => content.world.starterPack;

  /// Проверить и запомнить выбор (в памяти и на телефоне). null — принято; иначе код ошибки (§5.3).
  String? chooseLoadout(List<String> gear, Map<String, int> pack, {bool isDefault = false}) {
    final err = content.world.loadoutError(gear, pack);
    if (err != null) return err;
    _chosenLoadout = (gear: List<String>.of(gear), pack: Map<String, int>.of(pack), isDefault: isDefault);
    _storage.saveLoadout({'gear': gear, 'pack': pack, 'default': isDefault});
    return null;
  }

  /// Старт путешествия: шаги, сделанные сегодня до старта, не засчитываются.
  /// [gear]/[pack] — набор с экрана «Собери рюкзак»; без них — выбранный через [chooseLoadout], иначе loadout.default.
  Future<void> startJourney({List<String>? gear, Map<String, int>? pack, bool? isDefault}) async {
    final ds = await _steps.dailySteps(days: 2);
    final baseline = ds.merged(useSensor: _useSensor, useHc: _useHc)[today] ?? 0;
    final seed = math.Random().nextInt(0x7FFFFFFF);
    final now = _now;
    final hero = HeroState.create(content.world, seed, now, today, todaySteps: baseline);
    hero.stepMul = state.profile?.stepMul ?? 5;
    final def = defaultLoadout;
    final chosen = _chosenLoadout;
    var useGear = gear ?? chosen?.gear ?? def.gear;
    var usePack = pack ?? chosen?.pack ?? def.pack;
    var wasDefault = isDefault ?? (gear == null && pack == null ? (chosen?.isDefault ?? chosen == null) : false);
    final eng = Engine(content.world, hero);
    if (eng.startLoadout(useGear, usePack, now) != null) {
      // Набор не прошёл проверку (например, каталог изменился) — берём набор бывалого.
      useGear = def.gear;
      usePack = def.pack;
      wasDefault = true;
      eng.startLoadout(useGear, usePack, now);
    }
    var packSlots = 0;
    for (final n in usePack.values) {
      packSlots += n;
    }
    _a.event('loadout_confirmed', {
      'gear': useGear.join(','),
      'gear_n': useGear.length,
      'pack': usePack.entries.map((e) => '${e.key}:${e.value}').join(','),
      'pack_slots': packSlots,
      'default': wasDefault,
    });
    _chosenLoadout = null;
    await _storage.clearLoadout();
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
      // Героя мог сохранить другой Flutter-движок (вторая MainActivity) — сначала берём его свежую копию,
      // иначе эта, устаревшая, затёрла бы пройденные события (V5-44).
      if (await _storage.heroChangedElsewhere()) await _adoptFromDisk();
      if (state.hero == null) return;
      final hero = state.hero!;
      final ds = await _steps.dailySteps(days: 30);
      // Пока ждали шагомер, путь могли сбросить — не воскрешаем старого героя.
      if (!identical(state.hero, hero)) return;
      // Движок создаём после ожидания: за это время выбор в событии мог сдвинуть состояние ГСЧ.
      final eng = Engine(content.world, hero);
      final coinsBefore = hero.coins;
      // Для каждого дня берём максимум из включённых источников (настройки «Откуда брать шаги»).
      final days = ds.merged(useSensor: _useSensor, useHc: _useHc);
      // Ручная поправка (V5-54): за день берётся больше из часов/телефона и введённого вручную.
      _storage.loadManualSteps().forEach((d, n) {
        if (n > (days[d] ?? 0)) days[d] = n;
      });
      final added = eng.syncSteps(days, _now);
      final goalCoins = hero.coins - coinsBefore;
      final bonusBefore = eng.inBonus();
      final noticedBefore = eng.noticed();
      final last0 = hero.journal.isEmpty ? null : hero.journal.last;
      final evs = eng.advance(_now);
      _trackJournal(hero, last0);
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
      final saving = _save(hero);
      state = state.copyWith(
        hero: hero,
        todaySteps: days[today] ?? 0,
        lastSyncSources: {'sensor': ds.sensor[today] ?? 0, 'hc': ds.hc[today] ?? 0},
        lastSteps: ds,
      );
      await saving;
      _daySummary(hero);
      await _replanNotifications();
    } finally {
      _syncing = false;
    }
  }

  /// Сводка дня для статистики — раз в сутки, при первой синхронизации нового дня.
  /// Шаги — за вчера (день закрыт), остальное — снимок героя сейчас. Вложенные карты — дерево в отчёте.
  void _daySummary(HeroState hero) {
    final st = _storage;
    if (st.lastSummaryDay() == today) return;
    st.setSummaryDay(today);
    final eng = Engine(content.world, hero);
    final w = content.world;
    final yday = dayKey(DateTime.now().subtract(const Duration(days: 1)));
    final ySteps = hero.daySteps[yday] ?? 0;
    final gifts = <String>{
      ...hero.gear.where(w.isGift),
      ...hero.inv.entries.where((e) => e.value > 0 && w.isGift(e.key)).map((e) => e.key),
    };
    final gear = hero.gear.where((g) => !w.isGift(g)).toList();
    final chapter = w.chapterAt(hero.pos);
    final kmTotal = (hero.maxPos / 1000).round();
    _a.event('day_summary', {
      'yday_steps': ySteps,
      'yday_steps_b': Analytics.bucket(ySteps, const [1, 2000, 5000, 8000, 11000, 15000, 20000]),
      'yday_km': (ySteps * eng.gameMetersPerStep() / 1000).round(),
      'ratio': hero.stepMul,
      'chapter': chapter,
      'km_total': kmTotal,
      'km_total_b': Analytics.bucket(kmTotal, const [1, 50, 100, 200, 400, 700, 1000, 1500, 2000]),
      'journey_day': journeyDay(),
      'coins': hero.coins,
      'coins_b': Analytics.bucket(hero.coins, const [1, 20, 50, 100, 200, 400]),
      'satiety': hero.stats['satiety']!.round(),
      'water': hero.stats['water']!.round(),
      'warmth': hero.stats['warmth']!.round(),
      'satiety_b': Analytics.bucket(hero.stats['satiety']!.round(), const [1, 25, 50, 75]),
      'water_b': Analytics.bucket(hero.stats['water']!.round(), const [1, 25, 50, 75]),
      'warmth_b': Analytics.bucket(hero.stats['warmth']!.round(), const [1, 25, 50, 75]),
      'pack_n': eng.consumablesCount(),
      'pack_slots': eng.backpackSlots(),
      'gear_n': gear.length,
      'gear': {for (final g in gear) g: 1},
      'gifts_n': gifts.length,
      if (gifts.isNotEmpty) 'gifts': {for (final g in gifts) g: 1},
      'deaths': hero.deaths,
      'thoughts_answered': answers().length,
      'premium': premium,
    });
    _a.profileAttrs({
      'chapter': chapter,
      'km_total': kmTotal,
      'coins': hero.coins,
      'deaths': hero.deaths,
      'gifts_n': gifts.length,
      'step_ratio': hero.stepMul,
      'premium': premium ? 'yes' : 'no',
    });
  }

  // ------------------------------------------------ подписка (V5-52)
  /// Есть ли подписка. Оплаты пока нет: в тестовой сборке — переключатель в настройках (по умолчанию вкл.).
  bool get premium => state.profile?.premiumTest ?? true;

  Json get _access => ((content.world.balance['access'] as Map?) ?? const {}).cast<String, dynamic>();
  int get freeChapters => toI(_access['freeChapters'] ?? 99);
  int get freeThoughts => toI(_access['freeThoughts'] ?? 999);

  Future<void> setPremiumTest(bool v) async {
    await updateProfile((p) => p.premiumTest = v);
    _a.event('premium_test', {'on': v});
  }

  /// Остановка у конца бесплатной части пути (или дальше): без подписки «Идти дальше» ведёт на экран подписки.
  /// Шаги при этом не теряются — копятся и засчитаются, когда путь продолжится.
  bool paywallAt(Json? st) {
    if (premium || st == null || st['type'] != 'place') return false;
    final w = content.world;
    final last = w.chapters.where((c) => toI(c['id']) == freeChapters).firstOrNull;
    if (last == null) return false;
    final pos = w.posOf['${st['place']}'];
    return pos != null && pos >= w.chapterEndPos(freeChapters) - 1.0;
  }

  /// Номер мысли (1..30) для дня пути — как в thoughtForDay.
  int thoughtNumber(int day) {
    final n = content.thoughts.length;
    return n == 0 ? 1 : ((day - 1) % n + n) % n + 1;
  }

  /// Мысль закрыта: без подписки доступны первые freeThoughts.
  bool thoughtLocked(int day) => !premium && thoughtNumber(day) > freeThoughts;

  /// Шагов накоплено, пока герой ждёт (для экрана подписки): буфер пути в реальных шагах.
  int waitingSteps() {
    final eng = engine;
    if (eng == null) return 0;
    final mps = eng.gameMetersPerStep();
    return mps <= 0 ? 0 : (state.hero!.buffer / mps).round();
  }

  void paywallShown(String from) => _a.event('paywall_shown', {'from': from, 'chapter': state.hero == null ? 0 : content.world.chapterAt(state.hero!.pos)});
  void paywallTap(String from) => _a.event('paywall_tap', {'from': from});

  // ------------------------------------------------ ручной ввод шагов (V5-54)
  static const manualStepsMax = 30000;

  String get yesterday => dayKey(DateTime.now().subtract(const Duration(days: 1)));

  Map<String, int> manualSteps() => state.storage?.loadManualSteps() ?? const {};

  /// Шагов за день сейчас (больше из включённых источников и ручной поправки) — то, что видно на часах у нас.
  int rawStepsOn(String day) {
    final ds = state.lastSteps;
    final auto = ds == null ? 0 : (ds.merged(useSensor: _useSensor, useHc: _useHc)[day] ?? 0);
    return math.max(auto, manualSteps()[day] ?? 0);
  }

  /// Поправить можно сегодня и вчера (с начала пути), по одному разу на дату.
  bool canEditSteps(String day) {
    final hero = state.hero;
    if (hero == null || hero.finished) return false;
    if (day != today && day != yesterday) return false;
    if (day.compareTo(hero.startDay) < 0) return false;
    return !manualSteps().containsKey(day);
  }

  /// null — засчитано; иначе код: premium (нет подписки), used (уже поправляли), range (больше 30 000),
  /// not_more (не больше, чем уже засчитано), day (не сегодня и не вчера).
  /// Засчитывается только разница: герой проходит добавленные километры, показатели (сытость, вода, тепло)
  /// расходуются за путь как при обычных шагах, цели дня дают монеты.
  Future<String?> setManualSteps(String day, int n) async {
    if (!premium) return 'premium';
    if (day != today && day != yesterday) return 'day';
    if (!canEditSteps(day)) return 'used';
    if (n > manualStepsMax || n <= 0) return 'range';
    final before = rawStepsOn(day);
    if (n <= before) return 'not_more';
    final m = Map<String, int>.from(manualSteps());
    m[day] = n;
    await _storage.saveManualSteps(m);
    _a.event('manual_steps', {
      'day': day == today ? 'today' : 'yesterday',
      'entered': n,
      'auto': before,
      'delta': n - before,
      'delta_b': Analytics.bucket(n - before, const [1, 1000, 3000, 5000, 10000, 20000]),
    });
    await refresh();
    return null;
  }

  /// Раздел приложения открыт: вкладка или экран.
  void screen(String name) => _a.event('screen_view', {'name': name});

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
      case 'night':
        _a.event('night_stop', {'morning': '${st['morning'] ?? ''}', 'km': (hero.pos / 1000).round()});
    }
  }

  /// Сохранить героя; если на диске запись новее (её сделал другой движок), не затирать, а перечитать.
  Future<void> _save(HeroState hero) async {
    final ok = await _storage.saveHero(hero);
    if (!ok && identical(state.hero, hero)) await _adoptFromDisk();
  }

  Future<void> _adoptFromDisk() async {
    final fresh = await _storage.loadHeroFresh(content.world);
    if (fresh == null) return;
    _dropBrokenStop(content, fresh);
    state = state.copyWith(hero: fresh);
  }

  void _commit() {
    final hero = state.hero!;
    _save(hero);
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
    final gear0 = List<String>.from(hero.gear);
    final overflow0 = hero.overflow.length;
    final last0 = hero.journal.isEmpty ? null : hero.journal.last;
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
    // Снаряжение: новое — в полученные, отобранное — в потерянные.
    for (final g in hero.gear) {
      if (!gear0.contains(g)) gained[g] = (gained[g] ?? 0) + 1;
    }
    if (!res.died) {
      for (final g in gear0) {
        if (!hero.gear.contains(g)) lost[g] = (lost[g] ?? 0) + 1;
      }
    }
    final pending = <String, int>{};
    for (final o in hero.overflow.skip(math.min(overflow0, hero.overflow.length))) {
      pending[o.item] = (pending[o.item] ?? 0) + o.n;
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
      itemsPending: pending,
    );
    final chapterNow = content.world.chapterAt(hero.pos);
    final creature = ev['creature'];
    _a.event('event_choice', {
      'id': '${ev['id']}',
      'choice': choiceId,
      'risk': '${res.choice?['risk'] ?? 'none'}',
      'died': res.died,
      'chapter': chapterNow,
      if (creature != null) 'creature': '$creature',
    });
    // Отношения с духами: исход встречи — на пользу, во вред или ровно (по сумме показателей, монет и вещей).
    if (creature != null) {
      final score = view.stats.values.fold<int>(0, (a, b) => a + b) +
          view.coins +
          15 * gained.values.fold<int>(0, (a, b) => a + b) -
          15 * lost.values.fold<int>(0, (a, b) => a + b);
      final result = res.died ? 'bad' : (score > 5 ? 'good' : (score < -5 ? 'bad' : 'neutral'));
      _a.event('spirit_choice', {
        'creature': '$creature',
        'result': result,
        'event': '${ev['id']}',
        'choice': choiceId,
        'chapter': chapterNow,
      });
    }
    for (final g in gained.keys) {
      if (content.world.isGift(g)) {
        _a.event('gift_received', {'item': g, 'creature': '${creature ?? ''}', 'chapter': chapterNow});
      }
    }
    if (eff['quest_start'] != null) _a.event('quest_started', {'id': '${eff['quest_start']}'});
    if (res.died) {
      _a.event('death', {'cause': 'event', 'chapter': content.world.chapterAt(hero.pos)});
    }
    _trackJournal(hero, last0);
    _commit();
    return view;
  }

  /// Новые записи журнала после [last0] (последней до вызова) — для аналитики аптечки.
  void _trackJournal(HeroState hero, JournalEntry? last0) {
    final fresh = <JournalEntry>[];
    for (var i = hero.journal.length - 1; i >= 0; i--) {
      final e = hero.journal[i];
      if (last0 != null && identical(e, last0)) break;
      fresh.add(e);
    }
    for (final e in fresh.reversed) {
      if (e.kind == 'first_aid') {
        final st = e.data['stats'];
        _a.event('first_aid_used', {
          'item': '${e.data['item'] ?? ''}',
          'stats': st is List ? st.join(',') : '',
          'left': toI(e.data['left']),
        });
      }
    }
  }

  /// engine.advance с аналитикой остановок и аптечки.
  void _advance(Engine eng) {
    final hero = eng.s;
    final last0 = hero.journal.isEmpty ? null : hero.journal.last;
    final evs = eng.advance(_now);
    for (final e in evs) {
      _trackStop(e, hero);
    }
    _trackJournal(hero, last0);
  }

  /// После экрана исхода — герой идёт дальше на остаток шагов.
  Future<void> afterEvent() async {
    final eng = engine;
    if (eng == null) return;
    _advance(eng);
    _commit();
  }

  /// [from] — остановка, которую видел экран: повторное нажатие после смены остановки игнорируется
  /// (иначе двойной тап на конце главы пропускает рынок).
  Future<void> continueJourney([Json? from]) async {
    final eng = engine;
    if (eng == null) return;
    if (from != null && !identical(state.hero!.stop, from)) return;
    // false — отказ (вещи ждут решения, событие, финиш): остановку не сдвигаем.
    if (!eng.continueJourney(_now)) return;
    if (state.hero!.stop == null) _advance(eng);
    _commit();
  }

  /// Финал прочитан («Дальше» на экране медали): остановка «финиш» снимается, путь остаётся пройденным,
  /// итог пути сохраняется в профиль (переживает сброс). Сообщение «Путь пройден» покажет главная.
  Future<void> closeFinish() async {
    final hero = state.hero;
    if (hero == null || !hero.finished) return;
    await archiveJourney();
    if (hero.stop?['type'] == 'finish') hero.stop = null;
    _a.event('finish_closed');
    _commit();
  }

  /// Итог текущего пути — в профиль (один раз на путь).
  Future<void> archiveJourney() async {
    final hero = state.hero;
    if (hero == null || !hero.finished) return;
    final st = journeyStats(content.world, hero, today: today);
    final key = '${hero.startedAt}';
    if ((state.profile?.journeys ?? const []).any((j) => j['key'] == key)) return;
    await updateProfile((p) => p.journeys.add({...st.toJson(), 'key': key, 'totalKm': st.totalKm}));
  }

  /// «Начать путь заново» после финала: сохранить итог и начать с пролога.
  Future<void> restartAfterFinish() async {
    await archiveJourney();
    _a.event('journey_restart');
    await resetJourney();
  }

  Future<void> dismissDeath() async {
    final hero = state.hero;
    // Только со смерти: повторное нажатие не должно снять следующую остановку (событие пропало бы навсегда).
    if (hero == null || hero.stop?['type'] != 'death') return;
    hero.stop = null;
    _a.event('respawn', {'deaths': hero.deaths});
    _advance(engine!);
    _commit();
  }

  bool buy(String item) {
    final eng = engine;
    if (eng == null) return false;
    final price = eng.market().where((o) => o.item == item).map((o) => o.price).firstOrNull ?? 0;
    final ok = eng.buy(item, _now);
    if (ok) {
      _a.event('buy', {
        'item': item,
        'price': price,
        'type': content.world.itemType(item),
        'chapter': content.world.chapterAt(state.hero!.pos),
      });
      _commit();
    }
    return ok;
  }

  /// Кнопка «Использовать» на вкладке «Герой»: одна порция.
  bool useItem(String item) {
    final eng = engine;
    if (eng == null) return false;
    final wasHeated = eng.s.heated;
    final ok = eng.useItem(item, _now);
    if (ok) {
      _trackUse(eng, item, 'manual', wasHeated);
      _commit();
    }
    return ok;
  }

  /// «Выбросить» на вкладке «Герой»: 1 шт. из рюкзака или вещь из снаряжения (Engine.dropItem).
  /// false — нечего выбросить или это дар духа (дары не выбрасываются, V5-43); причина — [dropBlocker].
  bool dropItem(String item) {
    final eng = engine;
    if (eng == null) return false;
    final type = content.world.itemType(item);
    final r = eng.dropItem(item);
    if (r != null) return false;
    _a.event('item_dropped', {'item': item, 'kind': type});
    _commit();
    return true;
  }

  /// null — можно выбросить; 'gift' — дар духа; 'no_item' — нечего.
  String? dropBlocker(String item) {
    final eng = engine;
    if (eng == null) return 'no_item';
    if (content.world.isGift(item) && eng.hasItem(item)) return 'gift';
    return eng.hasItem(item) ? null : 'no_item';
  }

  void _trackUse(Engine eng, String item, String source, bool wasHeated) {
    _a.event('item_used', {
      'item': item,
      'source': source,
      'hot': wasHeated && !eng.s.heated && content.world.heatable(item),
      'portions_left': eng.portionsTotal(item),
    });
  }

  // ------------------------------------------------ горелка «Нагреть»
  String heatStatus() => engine?.heatStatus(_now) ?? 'no_stove';

  bool isHeated() => engine?.isHeated(_now) ?? false;

  /// heated — потрачен заряд; on — уже горячо; no_stove | no_gas | nothing — отказ.
  String heat() {
    final eng = engine;
    if (eng == null) return 'no_stove';
    final r = eng.heat(_now);
    if (r == 'heated') {
      final stove = eng.s.gear.firstWhere((g) => content.world.itemSpec(g)['stove'] == true, orElse: () => '');
      _a.event('gear_heated', {'stove_left': eng.usesLeft(stove), 'heatable_n': eng.heatableCount()});
      _commit();
    }
    return r;
  }

  // ------------------------------------------------ переполнение
  OverflowItem? get pendingOverflow => state.pendingOverflow;

  /// «Что взять с собой»: keep — ровно min(gearSlots, текущие + новая) id.
  String? resolveGearOverflow(List<String> keep) {
    final eng = engine;
    if (eng == null) return 'no_gear_overflow';
    final hero = eng.s;
    final o = hero.overflow.isEmpty ? null : hero.overflow.first;
    // дары духов в выборе не участвуют (V5-43) — в «выброшенные» их не записываем
    final cands = [...hero.gear.where((g) => !content.world.isGift(g)), if (o != null) o.item];
    final err = eng.resolveGearOverflow(keep);
    if (err != null) return err;
    final dropped = cands.where((c) => !keep.contains(c)).toList();
    _a.event('overflow_resolved', {
      'kind': 'gear',
      'item': o?.item ?? '',
      'action': (o != null && keep.contains(o.item)) ? 'keep_new' : 'keep_old',
      'swap_action': '',
      'swap_item': '',
      'dropped': dropped.join(','),
      'source': o?.source ?? '',
    });
    _afterOverflow(eng);
    return null;
  }

  /// Вещь не лезет в рюкзак: action use | drop | stash; при полном рюкзаке stash требует swapAction (use|drop) и swapItem.
  String? resolveBackpackOverflow(String action, {String? swapAction, String? swapItem}) {
    final eng = engine;
    if (eng == null) return 'no_backpack_overflow';
    final hero = eng.s;
    final o = hero.overflow.isEmpty ? null : hero.overflow.first;
    final item = o?.item ?? '';
    final source = o?.source ?? '';
    final wasHeated = hero.heated;
    final full = eng.consumablesCount() >= eng.backpackSlots();
    final err = eng.resolveBackpackOverflow(action, _now, swapAction: swapAction, swapItem: swapItem);
    if (err != null) return err;
    final swapped = action == 'stash' && full;
    if (action == 'use') _trackUse(eng, item, 'overflow', wasHeated);
    if (swapped && swapAction == 'use' && swapItem != null) _trackUse(eng, swapItem, 'swap', wasHeated);
    _a.event('overflow_resolved', {
      'kind': 'backpack',
      'item': item,
      'action': action,
      'swap_action': swapped ? (swapAction ?? '') : '',
      'swap_item': swapped ? (swapItem ?? '') : '',
      'dropped': action == 'drop' ? item : (swapped && swapAction == 'drop' ? (swapItem ?? '') : ''),
      'source': source,
    });
    _afterOverflow(eng);
    return null;
  }

  /// После последнего решения герой идёт дальше (как afterEvent), если ничто не держит.
  void _afterOverflow(Engine eng) {
    // undo != null — ещё открыт экран исхода (кнопки «Сучок»/«Бусина»): дальше поведёт afterEvent().
    if (eng.s.overflow.isEmpty && eng.s.stop == null && eng.s.undo == null) _advance(eng);
    _commit();
  }

  // ------------------------------------------------ клубок и зона
  /// ready | cooldown | no_item | no_event — кнопка «Спросить клубок».
  String clewStatus() => engine?.clewStatus(_now) ?? 'no_item';

  int clewCooldownDays() => engine?.clewCooldownDays(_now) ?? 0;

  /// {choiceId: tone}; UI держит ответ до выбора (в состоянии не хранится). null — нельзя.
  Map<String, String>? askClew() {
    final eng = engine;
    if (eng == null) return null;
    final ev = eng.currentEvent();
    final who = eng.clewItem(_now) ?? '';
    final r = eng.askClew(_now);
    if (r != null) {
      _a.event('clew_asked', {'event': '${ev?['id'] ?? ''}', 'tones': r.values.join(','), 'item': who});
      _commit();
    }
    return r;
  }

  /// city | suburb | wild → zoneCity / zoneSuburb / zoneWild.
  String zoneHere() => engine?.zoneHere() ?? 'city';

  /// Какой предмет подскажет сейчас (клубок, нитка, сучок…) — для подписи gearClewAsk_<id>.
  String? clewItem() => engine?.clewItem(_now);

  // ------------------------------------------------ дары духов (§13.4)
  /// ready | no_item | bad_kind | no_charges | cooldown | nothing | not_here — кнопка дара.
  String giftStatus(String item) => engine?.giftStatus(item, _now) ?? 'no_item';

  /// Дары с кнопкой (guide | mirage | action), которые есть у героя, в порядке heldItems.
  List<String> giftItems() {
    final eng = engine;
    if (eng == null) return const [];
    return [
      for (final it in eng.heldItems())
        if (const ['guide', 'mirage', 'action'].contains((content.world.itemSpec(it)['ability'] as Map?)?['kind'])) it,
    ];
  }

  /// Нажать кнопку дара: 'ok' или код [giftStatus]. Сучок/бусина — только на экране исхода (до afterEvent).
  String useGift(String item) {
    final eng = engine;
    if (eng == null) return 'no_item';
    final kind = '${(content.world.itemSpec(item)['ability'] as Map?)?['kind'] ?? ''}';
    final ev = '${eng.s.undo?['event'] ?? ''}';
    final r = eng.useGift(item, _now);
    if (r == 'ok') {
      _a.event('gift_used', {'item': item, 'kind': kind, 'event': ev, 'left': eng.usesLeft(item)});
      _commit();
    }
    return r;
  }

  // ------------------------------------------------ продажа (§13.8)
  List<(String, int)> sellOffers() => engine?.sellOffers() ?? const [];

  /// null — можно; no_market | no_item | not_sellable.
  String? sellBlocker(String item) => engine?.sellBlocker(item) ?? 'no_market';

  bool sell(String item) {
    final eng = engine;
    if (eng == null) return false;
    final price = toI(content.world.itemSpec(item)['sellPrice']);
    final ok = eng.sell(item, _now);
    if (ok) {
      _a.event('item_sold', {'item': item, 'price': price});
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

  // ------------------------------------------------ журнал
  /// Лента журнала (вариант B): строки по дням, цепочки, эффекты и варианты из контента.
  JournalView? journalView() {
    final hero = state.hero;
    final content = state.content;
    if (hero == null || content == null) return null;
    return buildJournalView(content, hero, journeyDay());
  }

  bool thoughtSeenToday() => state.storage?.lastThoughtSeenDay() == today;

  Future<void> markThoughtSeen(int day) async {
    await _storage.setThoughtSeenDay(today);
    _a.event('thought_read', {'day': day});
    state = state.copyWith();
  }

  /// Мысль открыта (номер — 1..30); дочитана до конца — отдельным событием.
  void thoughtOpened(int day) => _a.event('thought_opened', {'day': day, 'n': thoughtNumber(day)});
  void thoughtReadFull(int day) => _a.event('thought_read_full', {'day': day, 'n': thoughtNumber(day)});

  Map<String, Json> answers() => state.storage?.loadAnswers() ?? {};

  Future<void> saveAnswer(int day, String text, {required bool open}) async {
    final a = answers();
    a['$day'] = {'text': text.trim(), 'at': _now};
    await _storage.saveAnswers(a);
    _a.event('thought_answered', {'day': day, 'n': thoughtNumber(day), 'open': open, 'length': text.trim().length});
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
    _chosenLoadout = null;
    // Герой и флаги входа меняются в одном кадре: главная снимается сразу (она не успеет открыть
    // «Первый шаг» по сброшенному firstStepDone), а OnboardingFlow читает уже новые флаги:
    // пролог → «Как играть» → рюкзак → первый шаг (docs/v5/09 §7.4).
    state = state.copyWith(clearHero: true);
    final flagsReset = ref.read(uiFlagsProvider.notifier).startOverAfterReset();
    await _notify.replaceAll(const []);
    await flagsReset;
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

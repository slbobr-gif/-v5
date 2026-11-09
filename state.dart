// Состояние героя. Сериализуется в JSON и хранится на телефоне.

import 'world.dart';

const statKeys = ['satiety', 'water', 'warmth'];

/// Версия формата сохранения. v1 — до v5.3 (снаряжение лежало в inv), v2 — снаряжение в gear.
const int stateVersion = 2;

/// Вещь, ждущая решения игрока (вместилище полно).
class OverflowItem {
  OverflowItem({required this.kind, required this.item, required this.n, required this.source});
  String kind; // 'backpack' | 'gear'
  String item; // id предмета
  int n; // сколько единиц ждут решения (у gear всегда 1)
  String source; // id события-источника (или 'market', 'fixture_dayN')

  Json toJson() => {'kind': kind, 'item': item, 'n': n, 'source': source};
  static OverflowItem fromJson(Json j) => OverflowItem(
        kind: j['kind'] as String,
        item: j['item'] as String,
        n: toI(j['n']),
        source: (j['source'] as String?) ?? '',
      );
}

class Detour {
  Detour({required this.remaining, required this.total, this.end});
  double remaining;
  double total;
  String? end;

  Json toJson() => {'remaining': remaining, 'total': total, 'end': end};
  static Detour fromJson(Json j) =>
      Detour(remaining: toD(j['remaining']), total: toD(j['total']), end: j['end'] as String?);
}

class QuestProgress {
  QuestProgress({required this.startPos, this.step = 0, Map<String, int>? vars}) : vars = vars ?? {};
  double startPos;
  int step;
  Map<String, int> vars;

  Json toJson() => {'startPos': startPos, 'step': step, 'vars': vars};
  static QuestProgress fromJson(Json j) => QuestProgress(
        startPos: toD(j['startPos']),
        step: toI(j['step']),
        vars: ((j['vars'] as Map?) ?? {}).map((k, v) => MapEntry(k as String, toI(v))),
      );
}

class DayClaim {
  DayClaim({List<int>? tiers, this.login = false}) : tiers = tiers ?? [];
  List<int> tiers;
  bool login;

  Json toJson() => {'tiers': tiers, 'login': login};
  static DayClaim fromJson(Json j) => DayClaim(
        tiers: ((j['tiers'] as List?) ?? []).map(toI).toList(),
        login: j['login'] == true,
      );
}

/// Запись журнала: только данные, текст собирает интерфейс через локализацию.
class JournalEntry {
  JournalEntry(this.t, this.kind, this.data);
  final int t;
  final String kind;
  final Json data;

  Json toJson() => {'t': t, 'kind': kind, 'data': data};
  static JournalEntry fromJson(Json j) =>
      JournalEntry(toI(j['t']), j['kind'] as String, ((j['data'] as Map?) ?? {}).cast<String, dynamic>());
}

class HeroState {
  HeroState({
    required this.seed,
    required this.rng,
    required this.startedAt,
    required this.startDay,
    required this.stats,
    required this.coins,
    required this.inv,
    required this.nextRandomAt,
    required this.lastTick,
    required this.counted,
    required this.daySteps,
    this.pos = 0,
    this.maxPos = 0,
    this.buffer = 0,
    this.detour,
    this.stop,
    this.delayUntil = 0,
    List<String>? flags,
    List<String>? seen,
    List<String>? recentRandom,
    Map<String, QuestProgress>? quests,
    this.bonusKm = 0,
    Map<String, DayClaim>? claimed,
    this.deaths = 0,
    List<JournalEntry>? journal,
    this.finished = false,
    List<String>? gear,
    Map<String, int>? gearUses,
    this.heated = false,
    this.heatedDay = 0,
    List<OverflowItem>? overflow,
    this.aidLock = false,
    this.loadoutDone = false,
    Map<String, int>? portionsLeft,
    Map<String, int>? abilityReady,
    this.undo,
    Map<String, bool>? fed,
    Map<String, int>? expires,
    this.dayMark = 0,
    this.nextNightAt = -1.0,
    this.stepMul = 0,
    this.eventsDone = 0,
    this.questsDone = 0,
    List<Json>? marks,
  })  : marks = marks ?? [],
        fed = fed ?? {},
        expires = expires ?? {},
        gear = gear ?? [],
        gearUses = gearUses ?? {},
        overflow = overflow ?? [],
        portionsLeft = portionsLeft ?? {},
        abilityReady = abilityReady ?? {},
        flags = flags ?? [],
        seen = seen ?? [],
        recentRandom = recentRandom ?? [],
        quests = quests ?? {},
        claimed = claimed ?? {},
        journal = journal ?? [];

  int seed;
  int rng;
  int startedAt;
  String startDay;
  double pos;
  double maxPos;
  double buffer;
  Detour? detour;
  Map<String, double> stats;
  int coins;
  Map<String, int> inv;
  Json? stop;
  int delayUntil;
  List<String> flags;
  List<String> seen;
  List<String> recentRandom;
  Map<String, QuestProgress> quests;
  double nextRandomAt;
  double bonusKm;
  int lastTick;
  Map<String, int> counted;
  Map<String, int> daySteps;
  Map<String, DayClaim> claimed;
  int deaths;
  List<JournalEntry> journal;
  bool finished;

  /// Снаряжение по порядку получения (каждый id не больше одного раза, длина ≤ gearSlots).
  List<String> gear;

  /// Остаток зарядов у предметов с `uses` (горелка, аптечка).
  Map<String, int> gearUses;

  /// Горелка «включена»: следующий нагреваемый употреблённый предмет получает `heat`.
  bool heated;

  /// Игровая дата включения горелки (0 — выключена).
  int heatedDay;

  /// Очередь решений «не помещается».
  List<OverflowItem> overflow;

  /// Аптечка уже срабатывала после последней остановки.
  bool aidLock;

  /// Старт-набор выбран.
  bool loadoutDone;

  /// Порций в начатой единице многопорционного предмета (нет ключа — начатой нет).
  Map<String, int> portionsLeft;

  /// id предмета → игровая дата, с которой способность снова готова.
  /// Ключи: `<id>` (ability), `<id>:hint` (подсказка духа), `<id>:camp` (привал с перезарядкой).
  Map<String, int> abilityReady;

  /// Вред последнего исхода — для «Сучка»/«Бусины» (§13.2); null — отменять нечего.
  Json? undo;

  /// Лапоть накормлен в текущий игровой день.
  Map<String, bool> fed;

  /// id → игровая дата, с которой предмет пропадает (венок).
  Map<String, int> expires;

  /// Последняя обработанная игровая дата (смена дня: лапоть, венок).
  int dayMark;

  /// Позиция следующей ночёвки, м (V5-45); < 0 — не задана (старое сохранение), Engine вычислит по maxPos.
  double nextNightAt;

  /// Сколько игровых шагов даёт один реальный (настройка «Соотношение шагов»: 1, 3 или 5). 0 — взять из balance.movement.
  int stepMul;

  /// Сколько событий герой прошёл за путь (для статистики глав и итога). Журнал обрезается, счётчик — нет.
  int eventsDone;

  /// Сколько сюжетных историй (квестов) завершено за путь.
  int questsDone;

  /// Отметки концов глав и финиша: {ch, t, day, steps, events, deaths} — из них считается статистика
  /// конца главы и итог (lib/engine/journey_stats.dart). Пишутся один раз на главу.
  List<Json> marks;

  static HeroState create(World w, int seed, int nowMs, String today, {int todaySteps = 0}) {
    final b = w.balance;
    final start = ((b['stats'] as Map)['start'] as Map).cast<String, dynamic>();
    final eco = (b['economy'] as Map).cast<String, dynamic>();
    final s = HeroState(
      seed: seed & 0xFFFFFFFF,
      rng: seed & 0xFFFFFFFF,
      startedAt: nowMs,
      startDay: today,
      stats: {for (final k in statKeys) k: toD(start[k])},
      coins: toI(eco['startCoins']),
      inv: {},
      nextRandomAt: toD((b['randomEvents'] as Map)['firstAfterKm']) * 1000.0,
      lastTick: nowMs,
      counted: {today: todaySteps},
      daySteps: {today: 0},
    );
    final gd = (b['gameDay'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    s.nextNightAt = firstNightAfter(b, -1.0);
    s.dayMark = (nowMs + (toD(gd['utcOffsetHours']) * 3600000).toInt()) ~/ 86400000;
    // Набор по умолчанию (balance.loadout.default); экран «Собери рюкзак» заменяет его Engine.startLoadout().
    final lo = (b['loadout'] as Map?)?.cast<String, dynamic>();
    final d = (lo?['default'] as Map?)?.cast<String, dynamic>();
    if (d != null) {
      s.applyLoadout(
        w,
        ((d['gear'] as List?) ?? const []).map((e) => e as String).toList(),
        ((d['pack'] as Map?) ?? const {}).map((k, v) => MapEntry(k as String, toI(v))),
      );
    } else {
      // Баланс без loadout (старый): прежний фиксированный набор.
      s.inv = ((eco['startItems'] as Map?) ?? const {}).map((k, v) => MapEntry(k as String, toI(v)));
    }
    return s;
  }

  /// Записать старт-набор (= Python `_loadout_into`): снаряжение, заряды, рюкзак; прежний рюкзак и инструменты заменяются.
  void applyLoadout(World w, List<String> gearIds, Map<String, int> pack) {
    gear = List<String>.of(gearIds);
    gearUses = {
      for (final g in gearIds)
        if (w.itemSpec(g).containsKey('uses')) g: toI(w.itemSpec(g)['uses']),
    };
    inv = {
      for (final e in pack.entries)
        if (e.value > 0) e.key: e.value,
    };
    heated = false;
    heatedDay = 0;
    overflow = [];
    aidLock = false;
    portionsLeft = {};
    undo = null;
    fed = {};
    expires = {};
  }

  Json toJson() => {
        'v': stateVersion,
        'seed': seed,
        'rng': rng,
        'startedAt': startedAt,
        'startDay': startDay,
        'pos': pos,
        'maxPos': maxPos,
        'buffer': buffer,
        'detour': detour?.toJson(),
        'stats': stats,
        'coins': coins,
        'inv': inv,
        'stop': stop,
        'delayUntil': delayUntil,
        'flags': flags,
        'seen': seen,
        'recentRandom': recentRandom,
        'quests': quests.map((k, v) => MapEntry(k, v.toJson())),
        'nextRandomAt': nextRandomAt,
        'bonusKm': bonusKm,
        'lastTick': lastTick,
        'counted': counted,
        'daySteps': daySteps,
        'claimed': claimed.map((k, v) => MapEntry(k, v.toJson())),
        'deaths': deaths,
        'journal': journal.map((e) => e.toJson()).toList(),
        'finished': finished,
        'gear': gear,
        'gearUses': gearUses,
        'heated': heated,
        'heatedDay': heatedDay,
        'overflow': overflow.map((o) => o.toJson()).toList(),
        'aidLock': aidLock,
        'loadoutDone': loadoutDone,
        'portionsLeft': portionsLeft,
        'abilityReady': abilityReady,
        'undo': undo,
        'fed': fed,
        'expires': expires,
        'dayMark': dayMark,
        'nextNightAt': nextNightAt,
        'stepMul': stepMul,
        'eventsDone': eventsDone,
        'questsDone': questsDone,
        'marks': marks,
      };

  /// Загрузка сохранения. С [w] сохранение v1 (до v5.3) переводится в v2 (см. [migrate]);
  /// без [w] старое сохранение читается как есть (снаряжение останется в inv).
  static HeroState fromJson(Json j, [World? w]) {
    Map<String, int> ints(Object? m) => ((m as Map?) ?? {}).map((k, v) => MapEntry(k as String, toI(v)));
    List<String> strs(Object? l) => ((l as List?) ?? []).map((e) => e as String).toList();
    final s = HeroState(
      seed: toI(j['seed']),
      rng: toI(j['rng']),
      startedAt: toI(j['startedAt']),
      startDay: j['startDay'] as String,
      pos: toD(j['pos']),
      maxPos: toD(j['maxPos']),
      buffer: toD(j['buffer']),
      detour: j['detour'] == null ? null : Detour.fromJson((j['detour'] as Map).cast<String, dynamic>()),
      stats: ((j['stats'] as Map?) ?? {}).map((k, v) => MapEntry(k as String, toD(v))),
      coins: toI(j['coins']),
      inv: ints(j['inv']),
      stop: (j['stop'] as Map?)?.cast<String, dynamic>(),
      delayUntil: toI(j['delayUntil']),
      flags: strs(j['flags']),
      seen: strs(j['seen']),
      recentRandom: strs(j['recentRandom']),
      quests: ((j['quests'] as Map?) ?? {})
          .map((k, v) => MapEntry(k as String, QuestProgress.fromJson((v as Map).cast<String, dynamic>()))),
      nextRandomAt: toD(j['nextRandomAt']),
      bonusKm: toD(j['bonusKm']),
      lastTick: toI(j['lastTick']),
      counted: ints(j['counted']),
      daySteps: ints(j['daySteps']),
      claimed: ((j['claimed'] as Map?) ?? {})
          .map((k, v) => MapEntry(k as String, DayClaim.fromJson((v as Map).cast<String, dynamic>()))),
      deaths: toI(j['deaths']),
      journal: ((j['journal'] as List?) ?? [])
          .map((e) => JournalEntry.fromJson((e as Map).cast<String, dynamic>()))
          .toList(),
      finished: j['finished'] == true,
      gear: strs(j['gear']),
      gearUses: ints(j['gearUses']),
      heated: j['heated'] == true,
      heatedDay: toI(j['heatedDay']),
      overflow: ((j['overflow'] as List?) ?? [])
          .map((e) => OverflowItem.fromJson((e as Map).cast<String, dynamic>()))
          .toList(),
      aidLock: j['aidLock'] == true,
      loadoutDone: j['loadoutDone'] == true,
      portionsLeft: ints(j['portionsLeft']),
      abilityReady: ints(j['abilityReady']),
      // Поля §13: у старых сохранений их нет — умолчания (dayMark 0 → смена дня при первом applyTime).
      undo: (j['undo'] as Map?)?.cast<String, dynamic>(),
      fed: ((j['fed'] as Map?) ?? {}).map((k, v) => MapEntry(k as String, v == true)),
      expires: ints(j['expires']),
      dayMark: toI(j['dayMark']),
      nextNightAt: j['nextNightAt'] == null ? -1.0 : toD(j['nextNightAt']),
      stepMul: j['stepMul'] == null ? 0 : toI(j['stepMul']),
      eventsDone: toI(j['eventsDone'] ?? 0),
      questsDone: toI(j['questsDone'] ?? 0),
      marks: [for (final m in (j['marks'] as List?) ?? const []) (m as Map).cast<String, dynamic>()],
    );
    // Старые сохранения могли не знать какой-то показатель — не падаем на s.stats[k]!.
    for (final k in statKeys) {
      s.stats.putIfAbsent(k, () => 50.0);
    }
    final v = j['v'] is num ? (j['v'] as num).toInt() : 1;
    if (w != null && (v < stateVersion || j['gear'] == null)) s.migrate(w);
    return s;
  }

  /// Сохранение v1 → v2 (= Python `migrate_state`). Снаряжение переезжает из inv в gear (не больше gearSlots,
  /// по порядку ключей inv); лишние экземпляры и то, что не влезло, — монетами как дубликаты.
  /// Еда и инструменты остаются в inv.
  void migrate(World w) {
    final eco = (w.balance['economy'] as Map).cast<String, dynamic>();
    final slots = toI(eco['gearSlots']);
    final share = toD(eco['duplicateGearShare']);
    final g = <String>[];
    final uses = <String, int>{};
    for (final k in inv.keys.toList()) {
      if (w.itemType(k) != 'gear') continue;
      var n = inv.remove(k)!;
      if (g.length < slots) {
        g.add(k);
        if (w.itemSpec(k).containsKey('uses')) uses[k] = toI(w.itemSpec(k)['uses']);
        n -= 1;
      }
      if (n > 0) coins += n * (w.itemValue(k, 'price') * share).floor();
    }
    gear = g;
    gearUses = uses;
    heated = false;
    heatedDay = 0;
    overflow = [];
    aidLock = false;
    loadoutDone = true;
    portionsLeft = {};
    abilityReady = {};
  }
}

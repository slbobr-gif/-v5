// Состояние героя. Сериализуется в JSON и хранится на телефоне.

import 'world.dart';

const statKeys = ['satiety', 'water', 'warmth'];

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
  })  : flags = flags ?? [],
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

  static HeroState create(World w, int seed, int nowMs, String today, {int todaySteps = 0}) {
    final b = w.balance;
    final start = ((b['stats'] as Map)['start'] as Map).cast<String, dynamic>();
    final eco = (b['economy'] as Map).cast<String, dynamic>();
    return HeroState(
      seed: seed & 0xFFFFFFFF,
      rng: seed & 0xFFFFFFFF,
      startedAt: nowMs,
      startDay: today,
      stats: {for (final k in statKeys) k: toD(start[k])},
      coins: toI(eco['startCoins']),
      inv: (eco['startItems'] as Map).map((k, v) => MapEntry(k as String, toI(v))),
      nextRandomAt: toD((b['randomEvents'] as Map)['firstAfterKm']) * 1000.0,
      lastTick: nowMs,
      counted: {today: todaySteps},
      daySteps: {today: 0},
    );
  }

  Json toJson() => {
        'v': 1,
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
      };

  static HeroState fromJson(Json j) {
    Map<String, int> ints(Object? m) => ((m as Map?) ?? {}).map((k, v) => MapEntry(k as String, toI(v)));
    List<String> strs(Object? l) => ((l as List?) ?? []).map((e) => e as String).toList();
    return HeroState(
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
    );
  }
}

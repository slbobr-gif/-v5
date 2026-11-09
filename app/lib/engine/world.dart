// Мир: контент, баланс и маршрут. Только чтение. Повторяет World из tools/sim/engine.py.

import 'rng.dart';

typedef Json = Map<String, dynamic>;

double toD(Object? v) => v == null ? 0.0 : (v as num).toDouble();
int toI(Object? v) => v == null ? 0 : (v as num).toInt();

/// Python `a // b` для float (как в CPython: через fmod, а не floor(a / b)).
double pyFloorDiv(double a, double b) {
  var mod = a.remainder(b);
  var div = (a - mod) / b;
  if (mod != 0 && ((b < 0) != (mod < 0))) {
    mod += b;
    div -= 1.0;
  }
  if (div == 0) return 0.0;
  var fd = div.floorToDouble();
  if (div - fd > 0.5) fd += 1.0;
  return fd;
}

/// Python `round(x)`: к ближайшему, середина — к чётному.
double pyRound(double x) {
  final f = x.floorToDouble();
  final d = x - f;
  if (d > 0.5) return f + 1.0;
  if (d < 0.5) return f;
  return f % 2 == 0 ? f : f + 1.0;
}

/// Python `round(x, 1)`: по точному двоичному значению, середина — к чётному.
double pyRound1(double x) {
  final q = x * 4; // точно: умножение на степень двойки
  if (q.abs() < 1e15 && q == q.truncateToDouble() && q % 2 != 0) {
    return pyRound(x * 10) / 10; // x = n.25 / n.75 — ровно середина
  }
  return double.parse(x.toStringAsFixed(1));
}

/// Устойчивая сортировка по ключу — как sorted(key=...) в Python (List.sort в Dart неустойчив).
void stableSortBy<T>(List<T> list, double Function(T) key) {
  final keys = list.map(key).toList();
  final idx = List<int>.generate(list.length, (i) => i)
    ..sort((a, b) {
      final ka = keys[a];
      final kb = keys[b];
      if (ka < kb) return -1;
      if (ka > kb) return 1;
      return a - b;
    });
  final copy = List<T>.from(list);
  for (var i = 0; i < idx.length; i++) {
    list[i] = copy[idx[i]];
  }
}

class AnchoredEvent {
  const AnchoredEvent(this.pos, this.event);
  final double pos;
  final Json event;
}

class PlaceStop {
  const PlaceStop(this.pos, this.place);
  final double pos;
  final Json place;
}

/// Точка зоны пути: позиция места и радиусы «города» и «пригорода» вокруг неё (метры).
class ZonePoint {
  const ZonePoint(this.pos, this.urban, this.outer);
  final double pos;
  final double urban;
  final double outer;
}

/// Перк предмета для экрана: ключ l10n `gearPerk<Key>` и число для подстановки.
class ItemPerk {
  const ItemPerk(this.key, this.value);
  final String key;
  final int value;

  Json toJson() => {'key': key, 'value': value};
}

const _zoneRank = {'city': 2, 'suburb': 1, 'wild': 0};

/// Шаг ночёвок, м: movement.dayLengthKm (та же длина «суток пути», что и dayPhase) — V5-45.
double nightLen(Json b) => toD((b['movement'] as Map)['dayLengthKm']) * 1000.0;

/// Первая точка ночёвки (м) строго дальше [x]: atPhase·L, затем +L повторным сложением (бит в бит с Python).
/// Без раздела balance.night — 0 (ночёвок нет).
double firstNightAfter(Json b, double x) {
  final n = b['night'];
  if (n is! Map || n.isEmpty) return 0.0;
  final length = nightLen(b);
  var at = toD(n['atPhase']) * toD((b['movement'] as Map)['dayLengthKm']) * 1000.0;
  while (at <= x + 1e-6) {
    at += length;
  }
  return at;
}

/// Python `str.capitalize()`: первая буква заглавная, остальные строчные.
String pyCapitalize(String x) => x.isEmpty ? x : x[0].toUpperCase() + x.substring(1).toLowerCase();

class World {
  World({
    required this.balance,
    required List<Json> places,
    required this.chapters,
    required List<Json> quests,
    required this.randoms,
    required List<Json> anchoredEvents,
    required Map<String, double> placeDistances,
    required this.length,
  })  : posOf = Map<String, double>.from(placeDistances),
        items = (balance['items'] as Map).cast<String, dynamic>(),
        quests = {for (final q in quests) q['id'] as String: q} {
    this.places = List<Json>.from(places);
    for (final e in anchoredEvents) {
      eventsById[e['id'] as String] = e;
      if (e['detour_only'] == true) continue;
      final a = (e['anchor'] as Map).cast<String, dynamic>();
      final base = posOf[a['after'] as String];
      if (base == null) continue;
      anchored.add(AnchoredEvent(base + toD(a['km']) * 1000.0, e));
    }
    for (final e in randoms) {
      eventsById[e['id'] as String] = e;
    }
    for (final q in quests) {
      for (final s in (q['steps'] as List)) {
        final step = (s as Map).cast<String, dynamic>();
        if (step['event'] != null) {
          final ev = (step['event'] as Map).cast<String, dynamic>();
          eventsById[ev['id'] as String] = ev;
        }
        for (final b in (step['branches'] as List? ?? const [])) {
          final ev = ((b as Map)['event'] as Map).cast<String, dynamic>();
          eventsById[ev['id'] as String] = ev;
        }
      }
    }
    stableSortBy<AnchoredEvent>(anchored, (a) => a.pos);
    _addRoadside();
    for (final p in this.places) {
      placeById[p['id'] as String] = p;
    }
    for (final p in this.places) {
      if (p['kind'] != 'start') stopsPlaces.add(PlaceStop(posOf[p['id']]!, p));
    }
    stableSortBy<PlaceStop>(stopsPlaces, (p) => p.pos);
    for (final c in chapters) {
      chapterEnd[c['to'] as String] = c;
    }
    // Зоны: по всем местам (включая придорожные), в порядке this.places.
    final zones = (balance['zones'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
    final byKind = (zones['byKind'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
    final zp = <ZonePoint>[];
    for (final p in this.places) {
      final r = byKind[p['kind']];
      if (r is! Map) continue; // вид места без зоны (например, landmark) не влияет
      final urban = toD(r['urban']);
      final suburb = toD(r['suburb']);
      zp.add(ZonePoint(posOf[p['id']]!, urban * 1000.0, (urban + suburb) * 1000.0));
    }
    zonePoints = zp;
    for (final e in randoms) {
      final z = e['zone'];
      if (z is String && z.isNotEmpty) _zonePool[z] = (_zonePool[z] ?? 0) + 1;
    }
  }

  final Json balance;
  late List<Json> places;
  final List<Json> chapters;
  final Map<String, Json> quests;
  final List<Json> randoms;
  final Map<String, double> posOf;
  final double length;
  final Json items;
  final Map<String, Json> eventsById = {};
  final Map<String, Json> placeById = {};
  final List<AnchoredEvent> anchored = [];
  final List<PlaceStop> stopsPlaces = [];
  final Map<String, Json> chapterEnd = {};
  late final List<ZonePoint> zonePoints;
  final Map<String, int> _zonePool = {};

  Json get b => balance;

  void _addRoadside() {
    final rs = (balance['roadside'] as Map).cast<String, dynamic>();
    final gapMax = toD(rs['maxGapKm']) * 1000.0;
    final names = (rs['names'] as List).cast<String>();
    final ordered = List<Json>.from(places);
    stableSortBy<Json>(ordered, (p) => posOf[p['id']]!);
    final extra = <Json>[];
    var k = 0;
    for (var i = 0; i + 1 < ordered.length; i++) {
      final a = ordered[i];
      final bb = ordered[i + 1];
      final pa = posOf[a['id']]!;
      final pb = posOf[bb['id']]!;
      final n = pyFloorDiv(pb - pa, gapMax).toInt();
      for (var j = 1; j <= n; j++) {
        final pos = pa + (pb - pa) * j / (n + 1);
        final pid = 'rs_$k';
        extra.add({
          'id': pid,
          'name': names[k % names.length],
          'kind': 'roadside',
          'market': 'village',
          'chapter': bb['chapter'],
          'desc': '',
          'virtual': true,
        });
        posOf[pid] = pos;
        k++;
      }
    }
    places = [...places, ...extra];
    stableSortBy<Json>(places, (p) => posOf[p['id']]!);
  }

  int chapterAt(double pos) {
    for (final c in chapters) {
      if (pos < posOf[c['to']]!) return toI(c['id']);
    }
    return toI(chapters.last['id']);
  }

  Json chapterById(int id) => chapters.firstWhere((c) => toI(c['id']) == id);

  double chapterStartPos(int ch) => posOf[chapterById(ch)['from']]!;

  double chapterEndPos(int ch) => posOf[chapterById(ch)['to']]!;

  Json lastPlaceBefore(double pos) {
    var best = places.first;
    for (final p in places) {
      if (posOf[p['id']]! <= pos + 1e-6) best = p;
    }
    return best;
  }

  Json? nextPlaceAfter(double pos) {
    for (final s in stopsPlaces) {
      if (s.pos > pos + 1e-6) return s.place;
    }
    return null;
  }

  String weatherAt(int seed, double pos) {
    final w = (balance['weather'] as Map).cast<String, dynamic>();
    final seg = pyFloorDiv(pos, toD(w['segmentKm']) * 1000).toInt();
    final weights = ((w['byChapter'] as Map)['${chapterAt(pos)}'] as Map).cast<String, dynamic>();
    var total = 0;
    weights.forEach((_, v) => total += toI(v));
    final r = hash32([seed, seg]) % total;
    var acc = 0;
    for (final e in weights.entries) {
      acc += toI(e.value);
      if (r < acc) return e.key;
    }
    return weights.keys.last;
  }

  String itemType(String id) => ((items[id] as Map?)?['type'] as String?) ?? 'tool';

  double itemValue(String id, String key) {
    final v = (items[id] as Map?)?[key];
    return v is num ? v.toDouble() : 0.0;
  }

  /// Описание предмета из balance.items (пустая карта для неизвестного id).
  Json itemSpec(String id) => (items[id] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};

  // ------------------------------------------------ зоны пути
  /// Зона точки пути (м от старта): самая «городская» из зон всех мест, в радиус которых она попадает.
  /// Радиус 0 — такой зоны у места нет.
  String zoneAt(double posM) {
    var best = 'wild';
    for (final z in zonePoints) {
      final d = (posM - z.pos).abs();
      final zz = (z.urban > 0 && d <= z.urban)
          ? 'city'
          : (z.outer > 0 && d <= z.outer)
              ? 'suburb'
              : 'wild';
      if (_zoneRank[zz]! > _zoneRank[best]!) best = zz;
    }
    return best;
  }

  /// Сколько случайных событий с этой зоной (все главы).
  int zonePoolSize(String zone) => _zonePool[zone] ?? 0;

  String? eventZone(String eventId) {
    final z = eventsById[eventId]?['zone'];
    return z is String ? z : null;
  }

  // ------------------------------------------------ каталог
  List<String> get starterGear => [
        for (final e in items.entries)
          if (e.value is Map && (e.value as Map)['starter'] == true && (e.value as Map)['type'] == 'gear') e.key,
      ];

  List<String> get starterPack => [
        for (final e in items.entries)
          if (e.value is Map &&
              (e.value as Map)['starter'] == true &&
              ((e.value as Map)['type'] == 'food' || (e.value as Map)['type'] == 'drink'))
            e.key,
      ];

  bool heatable(String id) => itemValue(id, 'heat') > 0;

  int portionsOf(String id) {
    final p = itemSpec(id)['portions'];
    final n = p is num ? p.toInt() : 1;
    return n > 1 ? n : 1;
  }

  /// Проверка старт-набора без состояния (экран «Собери рюкзак»). null — годится.
  String? loadoutError(List<String> gear, Map<String, int> pack) {
    final lo = (balance['loadout'] as Map).cast<String, dynamic>();
    if (gear.length > toI(lo['maxGear'])) return 'gear_too_many';
    if (gear.toSet().length != gear.length) return 'gear_duplicate';
    final sg = starterGear.toSet();
    if (gear.any((g) => !sg.contains(g))) return 'gear_not_starter';
    final sp = starterPack.toSet();
    if (pack.keys.any((k) => !sp.contains(k))) return 'pack_not_starter';
    if (pack.values.any((n) => n < 1)) return 'pack_bad_count';
    final perKind = toI(lo['maxPerKind']);
    if (pack.values.any((n) => n > perKind)) return 'pack_kind_limit';
    var sum = 0;
    for (final n in pack.values) {
      sum += n;
    }
    if (sum > toI(lo['maxPackSlots'])) return 'pack_too_many';
    return null;
  }

  /// Перки предмета для экрана снаряжения — порядок фиксирован (docs/v5/08-engine-api-v5.3.md, §6).
  List<ItemPerk> itemPerks(String id) {
    final it = itemSpec(id);
    final out = <ItemPerk>[];
    int pct(Object? mult) => pyRound((1.0 - toD(mult)) * 100.0).toInt();
    final type = it['type'];
    final consumable = type == 'food' || type == 'drink';
    for (final stat in const ['satiety', 'water', 'warmth']) {
      final v = it[stat];
      if (consumable && v is num && v > 0) out.add(ItemPerk(stat, v.toInt()));
    }
    final heat = it['heat'];
    if (heat is num && heat > 0) out.add(ItemPerk('heat', heat.toInt()));
    if (it.containsKey('warmthDrainMult')) out.add(ItemPerk('warmthDrain', pct(it['warmthDrainMult'])));
    if (it.containsKey('weatherWarmthMult')) out.add(ItemPerk('weatherCold', pct(it['weatherWarmthMult'])));
    final dk = it['drainKmMult'];
    if (dk is Map) {
      if (dk.containsKey('satiety')) out.add(ItemPerk('satietyDrain', pct(dk['satiety'])));
      if (dk.containsKey('water')) out.add(ItemPerk('waterDrain', pct(dk['water'])));
    }
    if (it.containsKey('waterDrainMult')) out.add(ItemPerk('waterDrain', pct(it['waterDrainMult'])));
    if (it.containsKey('idleWarmthMult')) out.add(ItemPerk('idleWarmth', pct(it['idleWarmthMult'])));
    if (it.containsKey('delayMult')) out.add(ItemPerk('delay', pct(it['delayMult'])));
    if (it.containsKey('detourMult')) out.add(ItemPerk('detour', pct(it['detourMult'])));
    if (it.containsKey('riskReduce')) out.add(ItemPerk('risk', pyRound(toD(it['riskReduce']) * 100.0).toInt()));
    if (it.containsKey('rescueTo')) {
      final rs = it['rescueStats'];
      final key = (rs is List && rs.isNotEmpty) ? 'rescue${rs.map((x) => pyCapitalize('$x')).join()}' : 'rescue';
      out.add(ItemPerk(key, toI(it['rescueTo'])));
    }
    if (it['stove'] == true) out.add(const ItemPerk('stove', 0));
    if (it.containsKey('refill')) {
      final tgt = itemSpec('${it['refill']}');
      out.add(ItemPerk('refill', toI(it['amount'])));
      out.add(ItemPerk('refillMax', toI(tgt['maxUses'] ?? tgt['uses'] ?? 0)));
    }
    if (it.containsKey('uses')) out.add(ItemPerk('uses', toI(it['uses'])));
    final portions = it['portions'];
    if (portions is num && portions.toInt() > 1) out.add(ItemPerk('portions', portions.toInt()));
    final ab = it['ability'];
    if (ab is Map && ab.isNotEmpty) {
      out.add(ItemPerk('ability_${ab['kind']}', toI(ab['cooldownDays'])));
      final eff = (ab['effect'] is Map) ? (ab['effect'] as Map) : const {};
      for (final stat in const ['satiety', 'water', 'warmth']) {
        if (_truthy(eff[stat])) out.add(ItemPerk('action${pyCapitalize(stat)}', toI(eff[stat])));
      }
      if (_truthy(eff['warmthToMax'])) out.add(const ItemPerk('actionWarmthMax', 0));
      final give = eff['give'];
      if (give is Map) {
        give.forEach((gi, gn) => out.add(ItemPerk('actionGive_$gi', toI(gn))));
      }
    }
    final hint = it['hint'];
    if (hint is Map && hint.isNotEmpty) out.add(ItemPerk('hint', toI(hint['cooldownDays'])));
    final camp = it['camp'];
    if (camp is Map && camp.isNotEmpty) {
      for (final stat in const ['satiety', 'water', 'warmth']) {
        if (_truthy(camp[stat])) {
          final at = _truthy(camp['waterPlace']) ? 'AtWater' : '';
          out.add(ItemPerk('camp${pyCapitalize(stat)}$at', toI(camp[stat])));
        }
      }
    }
    final cond = it['cond'];
    if (cond is Map && cond.isNotEmpty) {
      final suf = 'At${((cond['any'] as List?) ?? const []).map((x) => pyCapitalize('$x')).join()}';
      final cdk = (cond['drainKmMult'] is Map) ? (cond['drainKmMult'] as Map) : const {};
      if (cond.containsKey('waterDrainMult')) out.add(ItemPerk('waterDrain$suf', pct(cond['waterDrainMult'])));
      if (cdk.containsKey('satiety')) out.add(ItemPerk('satietyDrain$suf', pct(cdk['satiety'])));
      if (cdk.containsKey('water')) out.add(ItemPerk('waterDrain$suf', pct(cdk['water'])));
      if (cond.containsKey('riskReduce')) {
        out.add(ItemPerk('risk$suf', pyRound(toD(cond['riskReduce']) * 100.0).toInt()));
      }
      if (_truthy(cond['noCoinLoss'])) out.add(ItemPerk('noCoinLoss$suf', 0));
    }
    final fb = it['foodBoost'];
    if (fb is Map && fb.isNotEmpty) {
      for (final stat in const ['satiety', 'water', 'warmth']) {
        if (fb.containsKey(stat)) {
          out.add(ItemPerk('boost${pyCapitalize('${fb['tag']}')}${pyCapitalize(stat)}',
              pyRound((toD(fb[stat]) - 1.0) * 100.0).toInt()));
        }
      }
    }
    if (_truthy(it['upkeep'])) out.add(const ItemPerk('upkeep', 1));
    if (it.containsKey('expiresDays')) out.add(ItemPerk('expires', toI(it['expiresDays'])));
    if (it.containsKey('sellPrice')) out.add(ItemPerk('sell', toI(it['sellPrice'])));
    return out;
  }

  /// Дар духа (items.<id>.gift): действует как снаряжение, но ячейку не занимает,
  /// переполнения не вызывает и не выбрасывается (V5-43).
  bool isGift(String item) => itemSpec(item)['gift'] == true;

  bool hasTag(String item, String tag) {
    final t = itemSpec(item)['tags'];
    return t is List && t.contains(tag);
  }

  /// balance.gifts (дары духов, §13.1); пустая карта, если раздела нет.
  Json get gifts => (balance['gifts'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};

  static bool _truthy(Object? v) {
    if (v == null) return false;
    if (v is bool) return v;
    if (v is num) return v != 0;
    if (v is String) return v.isNotEmpty;
    if (v is Map) return v.isNotEmpty;
    if (v is List) return v.isNotEmpty;
    return true;
  }
}

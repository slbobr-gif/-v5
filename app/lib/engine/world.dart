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

  double itemValue(String id, String key) => toD((items[id] as Map?)?[key]);
}

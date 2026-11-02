// Загрузка контента, баланса и карты из assets.

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

import '../engine/world.dart';

class MapData {
  MapData({
    required this.bbox,
    required this.route,
    required this.layers,
    required this.attribution,
    required this.source,
  });

  final List<double> bbox; // minLon, minLat, maxLon, maxLat
  final List<List<double>> route; // [lon, lat]
  final Map<String, List<List<List<double>>>> layers; // sea, lakes, rivers, borders
  final String attribution;
  final String source;
}

class Thought {
  Thought(this.raw);
  final Json raw;
  String get id => raw['id'] as String;
  int get day => toI(raw['day']);
  String get quote => raw['quote'] as String? ?? '';
  String get author => raw['author'] as String? ?? '';
  String get source => raw['source'] as String? ?? '';
  String get text => raw['text'] as String? ?? '';
  bool get isOpen => raw['ending'] == 'open';
  String get question => raw['question'] as String? ?? '';
}

/// Всё, что приложение знает о мире. Создаётся один раз при запуске.
class GameContent {
  GameContent({
    required this.world,
    required this.map,
    required this.items,
    required this.creatures,
    required this.thoughts,
  });

  final World world;
  final MapData map;
  final Map<String, Json> items; // имена и описания предметов
  final Map<String, Json> creatures;
  final List<Thought> thoughts;

  String itemName(String id) => items[id]?['name'] as String? ?? id;
  String itemDesc(String id) => items[id]?['desc'] as String? ?? '';
  String placeName(String id) => world.placeById[id]?['name'] as String? ?? id;

  // ------------------------------------------------ поля событий v5.3 (движок их не читает — только интерфейс)
  /// Зона события: city | suburb | wild ('' — не указана).
  String eventZone(Json ev) => ev['zone'] as String? ?? '';

  /// Настроение духа в событии: neutral | kind | cunning | angry (по умолчанию neutral).
  String eventMood(Json ev) {
    final m = ev['mood'];
    return (m is String && eventMoods.contains(m)) ? m : 'neutral';
  }

  /// Существо события (leshy, domovoy, …) или null.
  String? eventCreature(Json ev) {
    final c = ev['creature'];
    return (c is String && c.isNotEmpty) ? c : null;
  }

  /// Картинка духа для события: assets/art/spirits/<creature>_<mood>.svg (null — у события нет существа).
  /// Файла может не быть — интерфейс подставляет запасную картинку.
  String? spiritArt(Json ev) {
    final c = eventCreature(ev);
    return c == null ? null : 'assets/art/spirits/${c}_${eventMood(ev)}.svg';
  }

  // ------------------------------------------------ дары духов (§13): поля balance.items
  /// Вид способности предмета: clew | guide | mirage | action (null — нет).
  String? giftKind(String id) {
    final ab = world.itemSpec(id)['ability'];
    return ab is Map ? ab['kind'] as String? : null;
  }

  /// Есть ли у предмета подсказка духа (hint) — кнопка «Спросить …» в его событиях.
  bool hasHint(String id) => world.itemSpec(id)['hint'] is Map;

  List<String> itemTags(String id) => ((world.itemSpec(id)['tags'] as List?) ?? const []).map((e) => '$e').toList();

  int? sellPrice(String id) {
    final v = world.itemSpec(id)['sellPrice'];
    return v is num ? v.toInt() : null;
  }

  /// Квесты по виду: chapter | companion | folklore.
  List<Json> questsOfKind(String kind) => [
        for (final q in world.quests.values)
          if (q['kind'] == kind) q,
      ];

  /// Региональные товары места (balance.economy.markets.regional[placeId]).
  List<String> regionalItems(String placeId) {
    final eco = (world.balance['economy'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final markets = (eco['markets'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final regional = markets['regional'];
    if (regional is! Map) return const [];
    return ((regional[placeId] as List?) ?? const []).map((e) => '$e').toList();
  }

  Thought thoughtForDay(int day) {
    final n = thoughts.length;
    final idx = ((day - 1) % n + n) % n;
    final sorted = [...thoughts]..sort((a, b) => a.day.compareTo(b.day));
    return sorted[idx];
  }
}

const eventMoods = ['neutral', 'kind', 'cunning', 'angry'];

Future<Object?> _json(String path) async => jsonDecode(await rootBundle.loadString(path));

List<Json> _list(Object? v) => ((v as List?) ?? const []).map((e) => (e as Map).cast<String, dynamic>()).toList();

List<List<double>> _pts(Object? v) =>
    ((v as List?) ?? const []).map((p) => (p as List).map(toD).toList()).toList();

Future<GameContent> loadGameContent() async {
  const base = 'assets/content';
  final balance = ((await _json('assets/balance.json')) as Map).cast<String, dynamic>();
  final index = ((await _json('$base/index.json')) as Map).cast<String, dynamic>();
  final places = _list(await _json('$base/places.json'));
  final chapters = _list(await _json('$base/chapters.json'));
  final quests = _list(await _json('$base/quests.json'));
  final randoms = _list(await _json('$base/events_random.json'));
  final anchored = <Json>[];
  for (final f in ((index['anchored'] as List?) ?? const []).map((e) => '$e')) {
    try {
      anchored.addAll(_list(await _json('$base/$f')));
    } catch (_) {
      // файл не обязателен: например, глава ещё не написана
    }
  }
  final itemsList = _list(await _json('$base/items.json'));
  final creaturesList = _list(await _json('$base/creatures.json'));
  final thoughtsList = _list(await _json('$base/thoughts.json'));
  final mapJson = ((await _json('assets/map/map.json')) as Map).cast<String, dynamic>();

  final distances = (mapJson['placeDistances'] as Map).map((k, v) => MapEntry(k as String, toD(v)));
  final world = World(
    balance: balance,
    places: places,
    chapters: chapters,
    quests: quests,
    randoms: randoms,
    anchoredEvents: anchored,
    placeDistances: distances,
    length: toD(mapJson['routeLengthM']),
  );
  final layersRaw = (mapJson['layers'] as Map).cast<String, dynamic>();
  final layers = <String, List<List<List<double>>>>{
    for (final e in layersRaw.entries)
      e.key: ((e.value as List?) ?? const []).map((shape) => _pts(shape)).toList(),
  };
  final map = MapData(
    bbox: (mapJson['bbox'] as List).map(toD).toList(),
    route: _pts(mapJson['route']),
    layers: layers,
    attribution: mapJson['attribution'] as String? ?? '',
    source: mapJson['source'] as String? ?? '',
  );
  return GameContent(
    world: world,
    map: map,
    items: {for (final i in itemsList) i['id'] as String: i},
    creatures: {for (final c in creaturesList) c['id'] as String: c},
    thoughts: thoughtsList.map(Thought.new).toList(),
  );
}

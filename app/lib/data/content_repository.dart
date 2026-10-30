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
  String placeName(String id) => world.placeById[id]?['name'] as String? ?? id;

  Thought thoughtForDay(int day) {
    final n = thoughts.length;
    final idx = ((day - 1) % n + n) % n;
    final sorted = [...thoughts]..sort((a, b) => a.day.compareTo(b.day));
    return sorted[idx];
  }
}

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
  for (final f in (index['anchored'] as List).cast<String>()) {
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

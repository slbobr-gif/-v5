// Совпадение Dart-движка с эталоном tools/sim/engine.py (формат фикстуры v2, docs/v5/08-engine-api-v5.3.md §10).
// Тест не повторяет политику бота: он проигрывает записанные вызовы (ops) по порядку и сверяет результат
// каждого вызова и снимок состояния в конце каждого дня.
// Фикстура: python3 tools/sim/make_parity_fixture.py

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:putnik/data/content_repository.dart';
import 'package:putnik/engine/engine.dart';
import 'package:putnik/engine/state.dart';
import 'package:putnik/engine/world.dart';

Map<String, dynamic> _fixture() =>
    (jsonDecode(File('test/fixtures/parity.json').readAsStringSync()) as Map).cast<String, dynamic>();

int _i(Object? v) => (v as num).toInt();

Map<String, int> _ints(Object? m) => ((m as Map?) ?? const {}).map((k, v) => MapEntry('$k', _i(v)));

List<String> _strs(Object? l) => ((l as List?) ?? const []).map((e) => '$e').toList();

Map<String, int> _sorted(Map<String, int> m) {
  final keys = m.keys.toList()..sort();
  return {for (final k in keys) k: m[k]!};
}

/// Проигрывает один записанный вызов и сверяет его результат.
void _play(Engine e, Map<String, dynamic> op, String where) {
  final name = op['op'] as String;
  final now = op['now'] == null ? 0 : _i(op['now']);
  final ret = op['ret'];
  final why = '$where: $name';
  switch (name) {
    case 'startLoadout':
      expect(e.startLoadout(_strs(op['gear']), _ints(op['pack']), now), ret, reason: why);
    case 'syncSteps':
      expect(e.syncSteps(_ints(op['days']), now), _i(ret), reason: why);
    case 'claimLogin':
      expect(e.claimLogin(op['day'] as String, now), _i(ret), reason: why);
    case 'advance':
      expect(e.advance(now).length, _i(ret), reason: why);
    case 'choose':
      final r = e.choose(op['choice'] as String, now);
      final x = (ret as Map).cast<String, dynamic>();
      expect(r.ok, x['ok'] == true, reason: '$why ${op['choice']}: ok');
      expect(r.died, x['died'] == true, reason: '$why ${op['choice']}: died');
    case 'buy':
      expect(e.buy(op['item'] as String, now), ret == true, reason: '$why ${op['item']}');
    case 'continueJourney':
      expect(e.continueJourney(now), ret == true, reason: why);
    case 'heat':
      expect(e.heat(now), ret, reason: why);
    case 'useItem':
      expect(e.useItem(op['item'] as String, now), ret == true, reason: '$why ${op['item']}');
    case 'askClew':
      final r = e.askClew(now);
      if (ret == null) {
        expect(r, isNull, reason: why);
      } else {
        expect(r, (ret as Map).map((k, v) => MapEntry('$k', '$v')), reason: why);
      }
    case 'giveItems':
      e.giveItems(_ints(op['items']), op['source'] as String);
    case 'resolveGearOverflow':
      expect(e.resolveGearOverflow(_strs(op['keep'])), ret, reason: why);
    case 'resolveBackpackOverflow':
      expect(
        e.resolveBackpackOverflow(op['action'] as String, now,
            swapAction: op['swapAction'] as String?, swapItem: op['swapItem'] as String?),
        ret,
        reason: '$why ${op['action']}',
      );
    case 'useGift':
      expect(e.useGift(op['item'] as String, now), ret, reason: '$why ${op['item']}');
    case 'sell':
      expect(e.sell(op['item'] as String, now), ret == true, reason: '$why ${op['item']}');
    case 'dropItem':
      expect(e.dropItem(op['item'] as String), ret, reason: '$why ${op['item']}');
    case 'dismissDeath':
      e.s.stop = null;
    default:
      fail('$where: неизвестный op $name — обновите тест под make_parity_fixture.py');
  }
}

/// Снимок дня (snapshot() в make_parity_fixture.py).
void _check(World w, HeroState s, Map<String, dynamic> x, String where) {
  // Виды последних записей журнала — только для отладки (в Dart часть видов названа иначе: detour_back, quest_done).
  final tail = s.journal.skip(s.journal.length > 4 ? s.journal.length - 4 : 0).map((j) => j.kind).toList();
  final dbg = '$where (журнал Dart …$tail, эталон …${x['journalTail']})';
  expect(s.pos, closeTo((x['pos'] as num).toDouble(), 0.02), reason: '$dbg: позиция');
  expect(s.buffer, closeTo((x['buffer'] as num).toDouble(), 0.02), reason: '$dbg: буфер');
  expect(s.coins, _i(x['coins']), reason: '$dbg: монеты');
  (x['stats'] as Map).forEach((k, v) {
    expect(s.stats['$k'], closeTo((v as num).toDouble(), 0.002), reason: '$dbg: $k');
  });
  expect(_sorted(s.inv), _ints(x['inv']), reason: '$dbg: рюкзак');
  expect(s.gear, _strs(x['gear']), reason: '$dbg: снаряжение (порядок важен)');
  expect(_sorted(s.gearUses), _ints(x['gearUses']), reason: '$dbg: заряды');
  expect(s.heated, x['heated'] == true, reason: '$dbg: горелка');
  expect(s.heatedDay, _i(x['heatedDay']), reason: '$dbg: дата горелки');
  expect(
    s.overflow.map((o) => o.toJson()).toList(),
    ((x['overflow'] as List?) ?? const []).map((o) => (o as Map).cast<String, dynamic>()).toList(),
    reason: '$dbg: очередь переполнения',
  );
  expect(s.aidLock, x['aidLock'] == true, reason: '$dbg: аптечка');
  expect(_sorted(s.portionsLeft), _ints(x['portionsLeft']), reason: '$dbg: порции');
  expect(_sorted(s.abilityReady), _ints(x['abilityReady']), reason: '$dbg: способности');
  final fedKeys = s.fed.keys.toList()..sort();
  expect({for (final k in fedKeys) k: s.fed[k]}, ((x['fed'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', v == true)),
      reason: '$dbg: лапоть накормлен');
  expect(_sorted(s.expires), _ints(x['expires']), reason: '$dbg: сроки даров');
  expect(s.dayMark, _i(x['dayMark']), reason: '$dbg: игровая дата');
  final undoKeys = s.undo == null || s.undo!.isEmpty ? null : (s.undo!.keys.toList()..sort());
  expect(undoKeys, x['undoKeys'] == null ? isNull : _strs(x['undoKeys']), reason: '$dbg: undo');
  expect(s.stop?['type'], x['stop'], reason: '$dbg: остановка');
  expect(s.deaths, _i(x['deaths']), reason: '$dbg: смерти');
  expect(s.seen.length, _i(x['seen']), reason: '$dbg: события');
  expect(s.journal.length, _i(x['journal']), reason: '$dbg: журнал');
  // Поля записей для журнала-таймлайна: место записи и выбор в последнем событии.
  final posTail = s.journal.skip(s.journal.length > 4 ? s.journal.length - 4 : 0).map((j) => toI(j.data['pos'])).toList();
  final posX = ((x['journalPos'] as List?) ?? const []).map(_i).toList();
  expect(posTail.length, posX.length, reason: '$dbg: журнал, pos');
  for (var k = 0; k < posX.length; k++) {
    expect((posTail[k] - posX[k]).abs() <= 1, isTrue, reason: '$dbg: журнал, pos ${posTail[k]} ≠ ${posX[k]}');
  }
  final lx = x['lastEvent'] as Map?;
  JournalEntry? le;
  for (var k = s.journal.length - 1; k >= 0; k--) {
    if (s.journal[k].kind == 'event') {
      le = s.journal[k];
      break;
    }
  }
  if (lx == null) {
    expect(le, isNull, reason: '$dbg: последнее событие');
  } else {
    expect(le, isNotNull, reason: '$dbg: последнее событие');
    final d = le!.data;
    expect(d['event'], lx['event'], reason: '$dbg: событие в журнале');
    expect(d['cid'], lx['cid'], reason: '$dbg: выбор в журнале');
    expect(toI(d['oi']), _i(lx['oi']), reason: '$dbg: исход в журнале');
    expect((toI(d['pos']) - _i(lx['pos'])).abs() <= 1, isTrue, reason: '$dbg: место события в журнале');
    expect(d['quest'], lx['quest'], reason: '$dbg: квест в журнале');
    expect(d['step'] == null ? null : toI(d['step']), lx['step'] == null ? null : _i(lx['step']), reason: '$dbg: шаг квеста');
  }
  expect(s.rng, _i(x['rng']), reason: '$dbg: RNG');
  expect(w.zoneAt(s.pos), x['zone'], reason: '$dbg: зона');
  expect(s.delayUntil, _i(x['delayUntil']), reason: '$dbg: задержка');
  expect(s.nextRandomAt, closeTo((x['nextRandomAt'] as num).toDouble(), 0.02), reason: '$dbg: следующее случайное');
}

/// Проигрывает весь сценарий фикстуры; [onDay] — проверка после каждого дня.
(HeroState, Engine) _replay(World w, Map<String, dynamic> fx, {void Function(HeroState s, Map<String, dynamic> x, String where)? onDay}) {
  final s = HeroState.create(w, _i(fx['seed']), _i(fx['t0']), fx['startDay'] as String, todaySteps: _i(fx['baseline']));
  final e = Engine(w, s);
  final setup = ((fx['setup'] as List?) ?? const []).map((o) => (o as Map).cast<String, dynamic>()).toList();
  for (var k = 0; k < setup.length; k++) {
    _play(e, setup[k], 'старт, вызов ${k + 1}');
  }
  final days = (fx['days'] as List).map((d) => (d as Map).cast<String, dynamic>()).toList();
  for (var i = 0; i < days.length; i++) {
    final d = days[i];
    final where = 'день ${i + 1} (${d['day']})';
    final ops = (d['ops'] as List).map((o) => (o as Map).cast<String, dynamic>()).toList();
    for (var k = 0; k < ops.length; k++) {
      _play(e, ops[k], '$where, вызов ${k + 1}');
    }
    if (onDay != null) onDay(s, (d['expected'] as Map).cast<String, dynamic>(), where);
  }
  return (s, e);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('фикстура формата 2', () {
    final fx = _fixture();
    expect(fx['format'], 2, reason: 'перегенерируйте: python3 tools/sim/make_parity_fixture.py');
  });

  test('Dart-движок повторяет эталон вызов в вызов и день в день', () async {
    final fx = _fixture();
    final w = (await loadGameContent()).world;
    expect(w.length, closeTo((fx['routeLengthM'] as num).toDouble(), 0.5), reason: 'длина маршрута');
    _replay(w, fx, onDay: (s, x, where) => _check(w, s, x, where));
  });

  test('зоны пути совпадают с эталоном', () async {
    final fx = _fixture();
    final w = (await loadGameContent()).world;
    for (final p in (fx['zoneProbe'] as List)) {
      final pair = p as List;
      final pos = (pair[0] as num).toDouble();
      expect(w.zoneAt(pos), pair[1], reason: 'зона в точке $pos м');
    }
  });

  test('перки предметов и стартовый каталог совпадают с эталоном', () async {
    final fx = _fixture();
    final w = (await loadGameContent()).world;
    final perks = (fx['itemPerks'] as Map).cast<String, dynamic>();
    perks.forEach((id, list) {
      final want = (list as List).map((p) => (p as Map).cast<String, dynamic>()).map((p) => {'key': p['key'], 'value': _i(p['value'])}).toList();
      expect(w.itemPerks(id).map((p) => p.toJson()).toList(), want, reason: 'перки $id');
    });
    expect(w.starterGear, _strs(fx['starterGear']), reason: 'стартовое снаряжение');
    expect(w.starterPack, _strs(fx['starterPack']), reason: 'стартовая еда');
  });

  test('сохранение и загрузка без потерь (состояние после 20 дней сценария)', () async {
    final fx = _fixture();
    final w = (await loadGameContent()).world;
    final (s, _) = _replay(w, fx);
    final raw = jsonEncode(s.toJson());
    final back = HeroState.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>(), w);
    expect(jsonEncode(back.toJson()), raw);
    expect(back.gear, s.gear);
    expect(back.overflow.length, s.overflow.length);
  });

  test('миграция сохранения v1: снаряжение из рюкзака переезжает в gear, лишнее — монетами', () async {
    final w = (await loadGameContent()).world;
    final s = HeroState.create(w, 7, 1777622400000, '2026-05-01');
    final j = (jsonDecode(jsonEncode(s.toJson())) as Map).cast<String, dynamic>();
    for (final k in ['gear', 'gearUses', 'heated', 'heatedDay', 'overflow', 'aidLock', 'loadoutDone', 'portionsLeft', 'abilityReady', 'undo', 'fed', 'expires', 'dayMark']) {
      j.remove(k);
    }
    j['v'] = 1;
    j['coins'] = 40;
    j['inv'] = {'bread': 2, 'socks': 2, 'gas_stove': 1, 'matches': 1};
    final m = HeroState.fromJson(j, w);
    expect(m.gear, ['socks', 'gas_stove']);
    expect(m.gearUses, {'gas_stove': w.itemSpec('gas_stove')['uses']});
    expect(m.inv, {'bread': 2, 'matches': 1});
    final share = (w.balance['economy'] as Map)['duplicateGearShare'] as num;
    expect(m.coins, 40 + (w.itemValue('socks', 'price') * share).floor());
    expect(m.loadoutDone, isTrue);
    expect(m.toJson()['v'], stateVersion);
    expect(m.undo, isNull);
    expect(m.dayMark, 0);
    // Загрузка без мира (как раньше) не падает.
    expect(() => HeroState.fromJson(j), returnsNormally);
  });

  test('повторная синхронизация тех же шагов ничего не добавляет', () async {
    final content = await loadGameContent();
    final s = HeroState.create(content.world, 7, 1777622400000, '2026-05-01');
    final e = Engine(content.world, s);
    expect(e.syncSteps({'2026-05-01': 5000}, 1777622400000), 5000);
    expect(e.syncSteps({'2026-05-01': 5000}, 1777622400000), 0);
    expect(e.syncSteps({'2026-05-01': 4000}, 1777622400000), 0);
    expect(e.syncSteps({'2026-04-30': 9000}, 1777622400000), 0);
  });
}

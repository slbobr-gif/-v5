// Игровой движок «Путника». Чистый Dart. Повторяет tools/sim/engine.py правило в правило.

import 'dart:math' as math;

import 'rng.dart';
import 'state.dart';
import 'world.dart';

const int msHour = 3600000;
const int msDay = 86400000;

/// Python-«истинность» значения JSON: null, false, 0, '' и пустые коллекции — ложь.
bool truthy(Object? v) {
  if (v == null) return false;
  if (v is bool) return v;
  if (v is num) return v != 0;
  if (v is String) return v.isNotEmpty;
  if (v is Map) return v.isNotEmpty;
  if (v is List) return v.isNotEmpty;
  return true;
}

class EngineEvent {
  const EngineEvent(this.type, [this.stop]);
  final String type; // stop | death
  final Json? stop;
}

class ChoiceResult {
  const ChoiceResult({required this.ok, this.outcome, this.died = false, this.choice});
  final bool ok;
  final Json? outcome;
  final Json? choice;
  final bool died;
}

class MarketOffer {
  const MarketOffer(this.item, this.price);
  final String item;
  final int price;
}

class Engine {
  Engine(this.w, this.s) : rng = Rng(s.rng) {
    // Сохранение до V5-45: первая ночёвка — дальше уже пройденного.
    if (s.nextNightAt < 0) s.nextNightAt = firstNightAfter(w.balance, s.maxPos);
  }

  final World w;
  final HeroState s;
  final Rng rng;

  /// Вред, записанный последним _applyEffects (choose кладёт его в s.undo).
  Json? _harm;

  Json get b => w.balance;
  Json _m(String k) => (b[k] as Map).cast<String, dynamic>();
  Json _sub(Json m, String k) => (m[k] as Map).cast<String, dynamic>();

  // ------------------------------------------------ утилиты
  void _saveRng() => s.rng = rng.state;

  /// Запись журнала. pos — где это случилось, м (целые, как py_round в tools/sim/engine.py);
  /// data может передать свой pos (событие — место до исхода: смерть и срезка сдвигают героя).
  void _log(int now, String kind, [Json data = const {}]) {
    s.journal.add(JournalEntry(now, kind, <String, dynamic>{'pos': pyRound(s.pos).toInt(), ...data}));
    if (s.journal.length > 400) {
      s.journal.removeRange(0, s.journal.length - 400);
    }
  }

  /// Отметка конца главы [ch] для статистики (один раз на главу): время, последний день с шагами,
  /// всего реальных шагов, событий и падений к этому моменту.
  void _mark(int now, int ch) {
    if (s.marks.any((m) => toI(m['ch']) == ch)) return;
    final days = s.daySteps.keys.toList()..sort();
    var steps = 0;
    for (final d in days) {
      steps += s.daySteps[d]!;
    }
    s.marks.add(<String, dynamic>{
      'ch': ch,
      't': now,
      'day': days.isEmpty ? s.startDay : days.last,
      'steps': steps,
      'events': s.eventsDone,
      'deaths': s.deaths,
      'quests': s.questsDone,
    });
  }

  bool _isConsumable(String item) {
    final t = w.itemType(item);
    return t == 'food' || t == 'drink';
  }

  double gameMetersPerStep() {
    final m = _m('movement');
    // Соотношение шагов — настройка игрока (s.stepMul); 0 — значение из balance. Влияет только на будущие шаги.
    final mul = s.stepMul > 0 ? s.stepMul.toDouble() : toD(m['gameMultiplier']);
    return toD(m['stepLengthM']) * mul;
  }

  int consumablesCount() {
    var n = 0;
    s.inv.forEach((k, v) {
      if (_isConsumable(k)) n += v;
    });
    return n;
  }

  /// Рюкзак героя (V5-56): не больше одного, лежит в gear, ячейку снаряжения не занимает; null — базовый.
  String? currentPack() {
    for (final g in s.gear) {
      if (w.isPack(g)) return g;
    }
    return null;
  }

  int backpackSlots() {
    final base = toI(_m('economy')['backpackSlots']);
    final p = currentPack();
    return p == null ? base : math.max(base, toI(w.packSpec(p)!['slots']));
  }

  int gearSlots() {
    final base = toI(_m('economy')['gearSlots']);
    final p = currentPack();
    return p == null ? base : base + toI(w.packSpec(p)!['gear'] ?? 0);
  }

  /// Занятые ячейки снаряжения: дары духов (gift, V5-43) и рюкзак (V5-56) не считаются.
  int gearUsed() => s.gear.where((g) => !w.freeSlot(g)).length;

  int get gearSlotsLeft => gearSlots() - gearUsed();

  bool get hasOverflow => s.overflow.isNotEmpty;

  /// Есть ли предмет: в рюкзаке/инструментах (inv) или в снаряжении (gear).
  bool hasItem(String item) => (s.inv[item] ?? 0) > 0 || s.gear.contains(item);

  bool inBonus() {
    final bb = _m('bonus');
    return s.stats['satiety']! >= toD(bb['satietyAtLeast']) && s.stats['water']! >= toD(bb['waterAtLeast']);
  }

  bool noticed() => s.bonusKm >= toD(_m('bonus')['noticeAfterKm']);

  double get maxStat => toD(_m('stats')['max']);
  double get dangerBelow => toD(_m('stats')['dangerBelow']);

  void _clampStats() {
    for (final k in statKeys) {
      s.stats[k] = math.max(0.0, math.min(maxStat, s.stats[k]!));
    }
  }

  double _minStat() => statKeys.map((k) => s.stats[k]!).reduce(math.min);

  String zoneHere() => w.zoneAt(s.pos);

  // ------------------------------------------------ перки снаряжения
  /// Перки снаряжения действуют, если у предмета нет upkeep (лапоть) или сегодня он «накормлен».
  bool perkOn(String g) => !w.itemSpec(g).containsKey('upkeep') || (s.fed[g] ?? false);

  /// Условный перк предмета, если хотя бы одно его условие активно в [ctx].
  Json? _condOn(Json spec, List<String> ctx) {
    final c = spec['cond'];
    if (c is Map && c.isNotEmpty && ctx.isNotEmpty) {
      final conds = (c['any'] as List?) ?? const [];
      if (conds.any((x) => ctx.contains(x))) return c.cast<String, dynamic>();
    }
    return null;
  }

  /// Произведение множителя [key] (или key.sub) по снаряжению — в порядке списка gear.
  /// [ctx] — активные условия ('midday', 'heat', 'water'): cond[key] умножается сразу после базового (§13.3).
  double gearMult(String key, [String? sub, List<String> ctx = const []]) {
    var m = 1.0;
    for (final g in s.gear) {
      if (!perkOn(g)) continue;
      final spec = w.itemSpec(g);
      for (final src in [spec, _condOn(spec, ctx)]) {
        if (src == null) continue;
        Object? v = src[key];
        if (v is Map) v = v[sub];
        if (v is num) m = m * v.toDouble();
      }
    }
    return m;
  }

  /// Логический перк (noCoinLoss) у снаряжения — базовый или условный.
  bool gearFlag(String key, [List<String> ctx = const []]) {
    for (final g in s.gear) {
      if (!perkOn(g)) continue;
      final spec = w.itemSpec(g);
      final c = _condOn(spec, ctx);
      if (spec[key] == true || (c != null && c[key] == true)) return true;
    }
    return false;
  }

  /// Π (1 − riskReduce) по снаряжению (базовый, затем условный у того же предмета); 1.0 — оберега нет.
  double riskFactor([List<String> ctx = const []]) {
    var f = 1.0;
    for (final g in s.gear) {
      if (!perkOn(g)) continue;
      final spec = w.itemSpec(g);
      for (final src in [spec, _condOn(spec, ctx)]) {
        if (src == null) continue;
        final r = src['riskReduce'];
        if (r is num && r != 0) f = f * (1.0 - r.toDouble());
      }
    }
    return f;
  }

  /// Условия события для условных перков: ['water'], если art события — вода (gifts.waterArts).
  List<String> eventCtx(Json? ev) {
    final arts = (w.gifts['waterArts'] as List?) ?? const [];
    if (ev != null && arts.contains(ev['art'])) return ['water'];
    return [];
  }

  /// Полдень по времени маршрута (МСК): from ≤ час < to (gifts.middayHours).
  bool isMidday(int now) {
    final mh = w.gifts['middayHours'];
    if (mh is! List || mh.length < 2) return false;
    final off = (toD(_m('gameDay')['utcOffsetHours']) * msHour).toInt();
    final h = ((now + off) % msDay) / msHour;
    return toD(mh[0]) <= h && h < toD(mh[1]);
  }

  /// Остановка — место у большой воды (gifts.waterPlaces).
  bool atWaterPlace() {
    final st = s.stop;
    if (st == null || (st['type'] != 'place' && st['type'] != 'chapter_end')) return false;
    return ((w.gifts['waterPlaces'] as List?) ?? const []).contains(st['place']);
  }

  int usesLeft(String item) => s.gearUses[item] ?? 0;

  int maxUses(String item) {
    final it = w.itemSpec(item);
    return toI(it['maxUses'] ?? it['uses'] ?? 0);
  }

  // ------------------------------------------------ игровая дата
  /// Номер игровой даты: сутки по времени маршрута (UTC+3, весь путь — в МСК).
  int gameDay(int now) {
    final off = (toD(_m('gameDay')['utcOffsetHours']) * msHour).toInt();
    return (now + off) ~/ msDay;
  }

  void _expireHeat(int now) {
    if (s.heated && gameDay(now) != s.heatedDay) {
      s.heated = false;
      s.heatedDay = 0;
    }
  }

  bool isHeated(int now) => s.heated && gameDay(now) == s.heatedDay;

  // ------------------------------------------------ шаги и монеты
  /// Принимает {день: шагов за день}. Возвращает прирост реальных шагов.
  int syncSteps(Map<String, int> daySteps, int now) {
    var added = 0;
    final days = daySteps.keys.toList()..sort();
    for (final day in days) {
      if (day.compareTo(s.startDay) < 0) continue;
      final steps = daySteps[day]!;
      final prev = s.counted[day] ?? 0;
      if (steps <= prev) continue;
      s.counted[day] = steps;
      final delta = steps - prev;
      added += delta;
      s.daySteps[day] = (s.daySteps[day] ?? 0) + delta;
      _awardTiers(day, now);
    }
    if (added > 0) s.buffer += added * gameMetersPerStep();
    return added;
  }

  void _awardTiers(String day, int now) {
    final got = s.claimed.putIfAbsent(day, () => DayClaim());
    final tiers = (_m('dailyGoals')['tiers'] as List).cast<Map>();
    for (var i = 0; i < tiers.length; i++) {
      final t = tiers[i];
      if ((s.daySteps[day] ?? 0) >= toI(t['steps']) && !got.tiers.contains(i)) {
        got.tiers.add(i);
        s.coins += toI(t['coins']);
        _log(now, 'goal', {'steps': toI(t['steps']), 'coins': toI(t['coins'])});
      }
    }
  }

  bool canClaimLogin(String today) => !(s.claimed[today]?.login ?? false);

  int claimLogin(String today, int now) {
    if (!canClaimLogin(today)) return 0;
    s.claimed.putIfAbsent(today, () => DayClaim()).login = true;
    final c = toI(_m('dailyGoals')['loginCoins']);
    s.coins += c;
    _log(now, 'login', {'coins': c});
    return c;
  }

  // ------------------------------------------------ стартовый набор
  /// Экран «Собери рюкзак». null — принято; иначе код ошибки (набор не меняется).
  String? startLoadout(List<String> gear, Map<String, int> pack, int now) {
    if (s.loadoutDone) return 'already_done';
    if (s.maxPos > 0) return 'already_walking';
    final err = w.loadoutError(gear, pack);
    if (err != null) return err;
    s.applyLoadout(w, gear, pack);
    s.loadoutDone = true;
    _log(now, 'loadout', {'gear': List<String>.of(gear), 'pack': Map<String, int>.of(pack)});
    _saveRng();
    return null;
  }

  // ------------------------------------------------ время
  void applyTime(int now) {
    final hours = math.max(0.0, (now - s.lastTick) / msHour);
    s.lastTick = now;
    _expireHeat(now);
    _dayRoll(now);
    if (hours <= 0) return;
    final floor = toD(b['idleFloor']);
    final perHour = _m('drainPerHour');
    for (final k in statKeys) {
      final cur = s.stats[k]!;
      var rate = toD(perHour[k]);
      if (k == 'warmth') {
        final idle = math.max(toD(w.gifts['idleWarmthMin'] ?? 0.0), gearMult('idleWarmthMult'));
        rate = rate * gearMult('warmthDrainMult') * idle;
      }
      final nxt = cur - rate * hours;
      s.stats[k] = math.max(nxt, math.min(cur, floor));
    }
    _autoConsume(now);
  }

  // ------------------------------------------------ еда из рюкзака
  /// Прибавка показателя за порцию с учётом foodBoost снаряжения (речная лента: рыба ×1.5, pyRound).
  double statGain(String item, String stat) {
    var v = w.itemValue(item, stat);
    if (v == 0) return 0.0;
    for (final g in s.gear) {
      final fb = w.itemSpec(g)['foodBoost'];
      if (fb is Map && fb.isNotEmpty && fb.containsKey(stat) && perkOn(g) && w.hasTag(item, '${fb['tag']}')) {
        v = pyRound(v * toD(fb[stat]));
      }
    }
    return v;
  }

  double _itemGain(String item, String stat) {
    var g = statGain(item, stat);
    if (stat == 'warmth' && s.heated) g = g + w.itemValue(item, 'heat');
    return g;
  }

  void _autoConsume(int now) {
    final thr = toD(_m('stats')['autoConsumeBelow']);
    for (final stat in statKeys) {
      for (var guard = 0; guard < 4; guard++) {
        if (s.stats[stat]! >= thr) break;
        final cands = s.inv.entries
            .where((e) => e.value > 0 && _isConsumable(e.key) && _itemGain(e.key, stat) > 0)
            .map((e) => e.key)
            .toList()
          ..sort();
        if (cands.isEmpty) break;
        final gap = maxStat - s.stats[stat]!;
        final fitting = cands.where((k) => _itemGain(k, stat) <= gap).toList();
        String pick;
        if (fitting.isNotEmpty) {
          pick = fitting.first;
          for (final k in fitting) {
            if (_itemGain(k, stat) > _itemGain(pick, stat)) pick = k;
          }
        } else {
          pick = cands.first;
          for (final k in cands) {
            if (_itemGain(k, stat) < _itemGain(pick, stat)) pick = k;
          }
        }
        _useOne(pick, now);
        _log(now, 'eat', {'item': pick});
      }
    }
  }

  /// Вынуть n ЦЕЛЫХ единиц (ячеек). Кончились — забываем и остаток порций.
  void _takeInv(String item, int n) {
    final left = (s.inv[item] ?? 0) - n;
    if (left > 0) {
      s.inv[item] = left;
    } else {
      s.inv.remove(item);
      s.portionsLeft.remove(item);
    }
  }

  /// Сколько порций осталось в начатой единице (у предметов без portions — 1).
  int portionsOpen(String item) => s.portionsLeft[item] ?? w.portionsOf(item);

  /// Всего порций предмета в рюкзаке: «Термос воды ×4».
  int portionsTotal(String item) {
    final n = s.inv[item] ?? 0;
    if (n <= 0) return 0;
    return (n - 1) * w.portionsOf(item) + portionsOpen(item);
  }

  /// Съесть/выпить ОДНУ порцию из рюкзака. Возвращает true, если сработал бонус горелки.
  bool _useOne(String item, int now) {
    _spendPortion(item);
    return _consume(item, now);
  }

  /// Вынуть одну порцию без употребления (общая часть _useOne и платы лаптю).
  void _spendPortion(String item) {
    if (w.portionsOf(item) > 1) {
      final left = portionsOpen(item) - 1;
      if (left <= 0) {
        _takeInv(item, 1);
        s.portionsLeft.remove(item);
      } else {
        s.portionsLeft[item] = left;
      }
    } else {
      _takeInv(item, 1);
    }
  }

  /// Применить еду/питьё (предмет уже вынут). Возвращает true, если сработал бонус горелки.
  bool _consume(String item, int now) {
    _expireHeat(now);
    for (final k in statKeys) {
      s.stats[k] = s.stats[k]! + statGain(item, k);
    }
    var hot = false;
    final heat = w.itemValue(item, 'heat');
    if (s.heated && heat > 0) {
      s.stats['warmth'] = s.stats['warmth']! + heat;
      s.heated = false;
      s.heatedDay = 0;
      hot = true;
    }
    _clampStats();
    return hot;
  }

  /// Кнопка «Использовать» на вкладке «Герой»: одна порция. false — нет предмета или не еда.
  bool useItem(String item, int now) {
    if ((s.inv[item] ?? 0) <= 0 || !_isConsumable(item)) return false;
    _useOne(item, now);
    _saveRng();
    return true;
  }

  // ------------------------------------------------ горелка: «Нагреть»
  String? _stove() {
    for (final g in s.gear) {
      if (w.itemSpec(g)['stove'] == true) return g;
    }
    return null;
  }

  bool _hasHeatable() {
    for (final e in s.inv.entries) {
      if (e.value > 0 && w.heatable(e.key)) return true;
    }
    return s.overflow.any((o) => o.kind == 'backpack' && w.heatable(o.item));
  }

  /// Число нагреваемых единиц в рюкзаке (для аналитики и подписи кнопки).
  int heatableCount() {
    var n = 0;
    s.inv.forEach((k, v) {
      if (v > 0 && w.heatable(k)) n += v;
    });
    return n;
  }

  /// ready | on | no_stove | no_gas | nothing — для кнопки «Нагреть».
  String heatStatus(int now) {
    final st = _stove();
    if (st == null) return 'no_stove';
    if (isHeated(now)) return 'on';
    if (usesLeft(st) <= 0) return 'no_gas';
    if (!_hasHeatable()) return 'nothing';
    return 'ready';
  }

  /// «Нагреть»: heated — потрачен 1 заряд; on — уже горячо, заряд не тратится; иначе код отказа.
  String heat(int now) {
    _expireHeat(now);
    final status = heatStatus(now);
    if (status != 'ready') return status;
    final st = _stove()!;
    s.gearUses[st] = usesLeft(st) - 1;
    s.heated = true;
    s.heatedDay = gameDay(now);
    _log(now, 'heat', {'item': st, 'left': s.gearUses[st]});
    _saveRng();
    return 'heated';
  }

  // ------------------------------------------------ дары духов: способности предметов
  /// Всё, что у героя есть: снаряжение по порядку, затем inv (n > 0) по алфавиту.
  List<String> heldItems() {
    final invKeys = s.inv.entries.where((e) => e.value > 0).map((e) => e.key).toList()..sort();
    return [...s.gear, ...invKeys];
  }

  /// Первый предмет с ability.kind == kind (снаряжение по порядку, затем inv по алфавиту).
  String? abilityItem(String kind) {
    for (final it in heldItems()) {
      final ab = w.itemSpec(it)['ability'];
      if (ab is Map && ab.isNotEmpty && ab['kind'] == kind) return it;
    }
    return null;
  }

  /// Сколько игровых дней ждать до готовности (0 — готово). [item] — ключ abilityReady
  /// (id предмета; у подсказки духа — 'id:hint', у привала — 'id:camp').
  int abilityCooldownDays(String item, int now) => math.max(0, (s.abilityReady[item] ?? 0) - gameDay(now));

  /// Есть ли заряд у предмета с uses (у бесконечного — всегда).
  bool _charged(String item) => !w.itemSpec(item).containsKey('uses') || usesLeft(item) > 0;

  /// −1 заряд; у инструмента (tool) на 0 предмет исчезает.
  void _spendCharge(String item) {
    if (!w.itemSpec(item).containsKey('uses')) return;
    final left = usesLeft(item) - 1;
    s.gearUses[item] = left;
    if (left <= 0 && w.itemType(item) == 'tool') {
      s.inv.remove(item);
      s.gearUses.remove(item);
    }
  }

  Json? _ability(String item) {
    final ab = w.itemSpec(item)['ability'];
    return (ab is Map && ab.isNotEmpty) ? ab.cast<String, dynamic>() : null;
  }

  /// Чем можно подсветить исходы, в порядке траты: (предмет, ключ abilityReady, hint|null).
  List<(String, String, Json?)> _clewSources() {
    final held = heldItems();
    final out = <(String, String, Json?)>[];
    for (final i in held) {
      final h = w.itemSpec(i)['hint'];
      if (h is Map && h.isNotEmpty) out.add((i, '$i:hint', h.cast<String, dynamic>()));
    }
    final clews = held.where((i) => _ability(i)?['kind'] == 'clew').toList();
    for (final i in clews) {
      if (w.itemSpec(i).containsKey('uses')) out.add((i, i, null));
    }
    for (final i in clews) {
      if (!w.itemSpec(i).containsKey('uses')) out.add((i, i, null));
    }
    return out;
  }

  static bool hintMatches(Json h, Json ev) {
    final art = h['art'];
    final zone = h['zone'];
    final artOk = !truthy(art) || (art as List).contains(ev['art']);
    final zoneOk = !truthy(zone) || (zone as List).contains(ev['zone']);
    return artOk && zoneOk;
  }

  bool _sourceReady((String, String, Json?) src, int now) =>
      abilityCooldownDays(src.$2, now) == 0 && _charged(src.$1);

  (String, String, Json?)? _clewPick(int now) {
    final ev = currentEvent();
    if (ev == null) return null;
    for (final src in _clewSources()) {
      if (_sourceReady(src, now) && (src.$3 == null || hintMatches(src.$3!, ev))) return src;
    }
    return null;
  }

  /// ready | cooldown | not_here | no_item | no_event — кнопка «Спросить клубок» (или сучок, ракушку…).
  /// not_here — готова только подсказка духа, а событие не его.
  String clewStatus(int now) {
    final srcs = _clewSources();
    if (srcs.isEmpty) return 'no_item';
    final anyReady = srcs.any((x) => _sourceReady(x, now));
    if (currentEvent() == null) return anyReady ? 'no_event' : 'cooldown';
    if (_clewPick(now) != null) return 'ready';
    return anyReady ? 'not_here' : 'cooldown';
  }

  bool get clewReadyNow => clewStatus(DateTime.now().millisecondsSinceEpoch) == 'ready';

  /// Какой предмет подскажет сейчас (подпись кнопки gearClewAsk_<id>); null — никто.
  String? clewItem(int now) => _clewPick(now)?.$1;

  /// Дней до ближайшей готовой подсказки (0 — есть готовая или источников нет; без заряда — 999).
  int clewCooldownDays(int now) {
    final srcs = _clewSources();
    if (srcs.isEmpty) return 0;
    var best = 999;
    for (final x in srcs) {
      final d = _charged(x.$1) ? abilityCooldownDays(x.$2, now) : 999;
      if (d < best) best = d;
    }
    return best;
  }

  /// good | bad | mixed | neutral | death — по эффектам одного исхода.
  String outcomeTone(Json o) {
    final eff = (o['effects'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    if (truthy(eff['death'])) return 'death';
    var good = false;
    var bad = false;
    for (final k in const ['coins', 'satiety', 'water', 'warmth']) {
      final v = eff[k];
      if (v is String) {
        if (v.startsWith('-')) {
          bad = true;
        } else {
          good = true;
        }
      }
    }
    if (truthy(eff['give']) || truthy(eff['shortcut'])) good = true;
    if (truthy(eff['remove']) || truthy(eff['delay']) || truthy(eff['detour']) || truthy(eff['bonus_reset'])) {
      bad = true;
    }
    if (good && bad) return 'mixed';
    if (good) return 'good';
    if (bad) return 'bad';
    return 'neutral';
  }

  /// Тон варианта для клубка: death | reward | penalty | risk | mixed | neutral.
  String choiceTone(Json choice) {
    final tones = <String>{
      for (final o in (choice['outcomes'] as List? ?? const [])) outcomeTone((o as Map).cast<String, dynamic>()),
    };
    if (tones.contains('death')) return 'death';
    if (tones.contains('good') && tones.contains('bad')) return 'risk';
    if (tones.contains('mixed')) return 'mixed';
    if (tones.contains('good')) return 'reward';
    if (tones.contains('bad')) return 'penalty';
    return 'neutral';
  }

  /// «Спросить клубок»: {choiceId: тон} для текущего события; ставит перезарядку (у подсказки духа —
  /// hint.cooldownDays по ключу 'id:hint'), у нитки тратит заряд. null — нельзя. RNG не трогает.
  Map<String, String>? askClew(int now) {
    if (clewStatus(now) != 'ready') return null;
    final pick = _clewPick(now)!;
    final it = pick.$1;
    final h = pick.$3;
    final ev = currentEvent()!;
    final out = <String, String>{};
    for (final c in (ev['choices'] as List? ?? const [])) {
      final choice = (c as Map).cast<String, dynamic>();
      out[choice['id'] as String] = choiceTone(choice);
    }
    final cd = h != null ? toI(h['cooldownDays']) : toI(_ability(it)?['cooldownDays']);
    s.abilityReady[pick.$2] = gameDay(now) + cd;
    if (h == null) _spendCharge(it);
    _log(now, 'ability', {'item': it, 'event': ev['id']});
    _saveRng();
    return out;
  }

  // ------------------------------------------------ дары-действия: guide, mirage, action (§13.4)
  /// ready | no_item | bad_kind | no_charges | cooldown | nothing | not_here — кнопка дара.
  String giftStatus(String item, int now) {
    if (!hasItem(item)) return 'no_item';
    final ab = _ability(item) ?? const <String, dynamic>{};
    final kind = ab['kind'];
    if (kind != 'guide' && kind != 'mirage' && kind != 'action') return 'bad_kind';
    if (!_charged(item)) return 'no_charges';
    if (abilityCooldownDays(item, now) > 0) return 'cooldown';
    final u = s.undo;
    if (kind == 'guide') {
      return (u != null && (u.containsKey('delay') || u.containsKey('detour'))) ? 'ready' : 'nothing';
    }
    if (kind == 'mirage') return (u != null && u.isNotEmpty) ? 'ready' : 'nothing';
    final at = (ab['at'] as String?) ?? 'any';
    final st = s.stop;
    if (at == 'place' && !(st != null && (st['type'] == 'place' || st['type'] == 'chapter_end'))) return 'not_here';
    final zones = ab['zones'];
    if (truthy(zones) && !(zones as List).contains(zoneHere())) return 'not_here';
    if (truthy(ab['water']) && !atWaterPlace()) return 'not_here';
    final eff = (ab['effect'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    final mx = maxStat;
    if (!truthy(eff['give'])) {
      var allFull = true;
      for (final k in statKeys) {
        final touched = truthy(eff[k]) || (k == 'warmth' && truthy(eff['warmthToMax']));
        if (touched && s.stats[k]! < mx) allFull = false;
      }
      if (allFull) return 'nothing';
    }
    return 'ready';
  }

  /// Нажать кнопку дара. 'ok' — сработал (заряд/перезарядка потрачены); иначе код [giftStatus].
  String useGift(String item, int now) {
    final st = giftStatus(item, now);
    if (st != 'ready') return st;
    final ab = _ability(item)!;
    final kind = ab['kind'] as String;
    var evId = '';
    if (kind == 'guide' || kind == 'mirage') {
      evId = '${s.undo!['event'] ?? ''}';
      _undo(kind);
    } else {
      final eff = (ab['effect'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
      for (final k in statKeys) {
        if (truthy(eff[k])) s.stats[k] = s.stats[k]! + toD(eff[k]);
      }
      if (truthy(eff['warmthToMax'])) s.stats['warmth'] = maxStat;
      _clampStats();
      final give = eff['give'];
      if (give is Map && give.isNotEmpty) {
        giveItems(give.map((k, v) => MapEntry('$k', toI(v))), item);
      }
    }
    final cd = toI(ab['cooldownDays']);
    if (cd != 0) s.abilityReady[item] = gameDay(now) + cd;
    _spendCharge(item);
    _log(now, 'gift', {'item': item, 'ability': kind, 'event': evId});
    _saveRng();
    return 'ok';
  }

  /// Отмена вреда последнего исхода (s.undo): guide — только задержка и крюк; mirage — всё плохое.
  void _undo(String kind) {
    final u = s.undo!;
    if (u.containsKey('delay')) s.delayUntil = toI(u.remove('delay'));
    if (u.containsKey('detour')) {
      u.remove('detour');
      final pd = u.remove('prevDetour');
      s.detour = pd is Map ? Detour.fromJson(pd.cast<String, dynamic>()) : null;
    }
    if (kind == 'mirage') {
      if (truthy(u['coins'])) s.coins += toI(u['coins']);
      final lostStats = (u['stats'] as Map?) ?? const {};
      lostStats.forEach((k, lost) {
        s.stats['$k'] = (s.stats['$k'] ?? 0.0) + toD(lost);
      });
      _clampStats();
      final removed = (u['removed'] as Map?) ?? const {};
      removed.forEach((k, r0) {
        final it = '$k';
        final r = (r0 as Map).cast<String, dynamic>();
        if (_isConsumable(it)) {
          giveItems({it: toI(r['n'])}, 'mirage');
          if (r['portions'] != null && (s.inv[it] ?? 0) > 0 && !s.portionsLeft.containsKey(it)) {
            s.portionsLeft[it] = toI(r['portions']);
          }
        } else {
          s.inv[it] = (s.inv[it] ?? 0) + toI(r['n']);
          if (r['uses'] != null) s.gearUses[it] = toI(r['uses']);
        }
      });
      for (final r0 in ((u['removedGear'] as List?) ?? const [])) {
        final r = (r0 as Map).cast<String, dynamic>();
        final g = r['item'] as String;
        if (s.gear.contains(g)) continue;
        if (w.freeSlot(g) || gearUsed() < gearSlots()) {
          s.gear.add(g);
          if (r['uses'] != null) s.gearUses[g] = toI(r['uses']);
          if (r['expires'] != null) s.expires[g] = toI(r['expires']);
          if (r['fed'] != null) s.fed[g] = r['fed'] == true;
        } else {
          s.overflow.add(OverflowItem(kind: 'gear', item: g, n: 1, source: 'mirage'));
        }
      }
      if (u.containsKey('bonusKm')) s.bonusKm = toD(u['bonusKm']);
      s.undo = null;
      return;
    }
    if (u.keys.every((k) => k == 'event')) s.undo = null;
  }

  // ------------------------------------------------ смена игровой даты: лапоть ест, венок вянет
  void _dayRoll(int now) {
    final d = gameDay(now);
    if (s.dayMark == d) return;
    s.dayMark = d;
    for (final g in List<String>.of(s.gear)) {
      final exp = s.expires[g];
      if (exp != null && d >= exp) {
        s.gear.remove(g);
        _onGearRemoved(g);
        _log(now, 'wilt', {'item': g});
      }
    }
    for (final g in List<String>.of(s.gear)) {
      final up = w.itemSpec(g)['upkeep'];
      if (!truthy(up)) continue;
      final food = _upkeepFood((up as List).map((e) => '$e').toList());
      if (food != null) _spendPortion(food);
      s.fed[g] = food != null;
      _log(now, 'upkeep', {'item': g, 'food': food});
    }
  }

  /// Что съест домовой: первый из [order], затем прочая еда по алфавиту. Последнюю единицу еды не берёт.
  String? _upkeepFood(List<String> order) {
    var food = 0;
    s.inv.forEach((k, n) {
      if (n > 0 && w.itemType(k) == 'food') food += n;
    });
    if (food < 2) return null;
    for (final it in order) {
      if ((s.inv[it] ?? 0) > 0 && w.itemType(it) == 'food') return it;
    }
    final keys = s.inv.keys.toList()..sort();
    for (final it in keys) {
      if (s.inv[it]! > 0 && w.itemType(it) == 'food') return it;
    }
    return null;
  }

  void _onGearAdded(String g) {
    final spec = w.itemSpec(g);
    if (spec.containsKey('uses')) s.gearUses[g] = toI(spec['uses']);
    if (spec.containsKey('expiresDays')) s.expires[g] = gameDay(s.lastTick) + toI(spec['expiresDays']);
    if (truthy(spec['upkeep'])) s.fed[g] = true; // плата отдана при получении
  }

  void _onGearRemoved(String g) {
    s.gearUses.remove(g);
    s.expires.remove(g);
    s.fed.remove(g);
  }

  // ------------------------------------------------ привал: спальник, уголёк, ракушка (camp)
  void _camp(Json place, int now) {
    final got = <String>[];
    final water = ((w.gifts['waterPlaces'] as List?) ?? const []).contains(place['id']);
    for (final g in s.gear) {
      final c = w.itemSpec(g)['camp'];
      if (c is! Map || c.isEmpty || !perkOn(g)) continue;
      if (truthy(c['waterPlace']) && !water) continue;
      final cd = toI(c['cooldownDays']);
      final key = '$g:camp';
      if (cd != 0 && abilityCooldownDays(key, now) > 0) continue;
      for (final k in statKeys) {
        if (truthy(c[k])) s.stats[k] = s.stats[k]! + toD(c[k]);
      }
      if (cd != 0) s.abilityReady[key] = gameDay(now) + cd;
      got.add(g);
    }
    if (got.isNotEmpty) {
      _clampStats();
      _log(now, 'camp', {'items': got});
    }
  }

  // ------------------------------------------------ продажа (речная жемчужина)
  /// Что можно продать на этом рынке: (id, цена) — предметы inv с sellPrice, по алфавиту, без наценки.
  List<(String, int)> sellOffers() {
    if (market().isEmpty) return const [];
    final keys = s.inv.keys.toList()..sort();
    return [
      for (final k in keys)
        if (s.inv[k]! > 0 && w.itemSpec(k).containsKey('sellPrice')) (k, toI(w.itemSpec(k)['sellPrice'])),
    ];
  }

  /// null — можно продать; иначе no_market | no_item | not_sellable.
  String? sellBlocker(String item) {
    if (market().isEmpty) return 'no_market';
    if ((s.inv[item] ?? 0) <= 0) return 'no_item';
    if (!w.itemSpec(item).containsKey('sellPrice')) return 'not_sellable';
    return null;
  }

  bool sell(String item, int now) {
    if (sellBlocker(item) != null) return false;
    final price = toI(w.itemSpec(item)['sellPrice']);
    _takeInv(item, 1);
    s.coins += price;
    _log(now, 'sell', {'item': item, 'price': price});
    _saveRng();
    return true;
  }

  // ------------------------------------------------ аптечка
  /// Показатель упал до 0: аптечка с зарядом поднимает все нулевые показатели до rescueTo.
  /// Не чаще раза между остановками (aidLock снимается при прибытии на остановку).
  bool _tryRescue(int now) {
    if (s.aidLock) return false;
    final zero = statKeys.where((k) => s.stats[k]! <= 0).toList();
    for (final g in s.gear) {
      final to = w.itemSpec(g)['rescueTo'];
      final rs = w.itemSpec(g)['rescueStats'];
      final allowed = (rs is List && rs.isNotEmpty) ? rs.map((e) => '$e').toList() : statKeys;
      if (to is num && to != 0 && usesLeft(g) > 0 && zero.every(allowed.contains)) {
        s.gearUses[g] = usesLeft(g) - 1;
        final saved = zero;
        for (final k in saved) {
          s.stats[k] = to.toDouble();
        }
        s.aidLock = true;
        _log(now, 'first_aid', {'item': g, 'stats': saved, 'left': s.gearUses[g]});
        return true;
      }
    }
    return false;
  }

  // ------------------------------------------------ движение
  String weatherHere() => w.weatherAt(s.seed, s.pos);

  void _drainWalk(double km, [int? now]) {
    final dk = _m('drainPerKm');
    final bonus = inBonus();
    final mult = bonus ? toD(_m('bonus')['drainMultiplier']) : 1.0;
    final wname = w.weatherAt(s.seed, s.pos);
    final wx = _sub(_sub(_m('weather'), 'types'), wname);
    final cold = toD(_m('chapterCold')['${w.chapterAt(s.pos)}']);
    // условия для cond-перков (колосок): жара по погоде, полдень по времени маршрута
    final ctx = <String>[];
    if (wname == 'heat') ctx.add('heat');
    if (now != null && isMidday(now)) ctx.add('midday');
    final satM = gearMult('drainKmMult', 'satiety', ctx);
    final watM = gearMult('drainKmMult', 'water', ctx) * gearMult('waterDrainMult', null, ctx);
    final warmM = gearMult('warmthDrainMult', null, ctx);
    final rainM = gearMult('weatherWarmthMult', null, ctx);
    var weatherWarm = wx['warmth'] == null ? 1.0 : toD(wx['warmth']);
    if (weatherWarm > 1.0 && rainM != 1.0) {
      weatherWarm = 1.0 + (weatherWarm - 1.0) * rainM;
    }
    final wxWater = wx['water'] == null ? 1.0 : toD(wx['water']);
    s.stats['satiety'] = s.stats['satiety']! - toD(dk['satiety']) * km * mult * satM;
    s.stats['water'] = s.stats['water']! - toD(dk['water']) * km * wxWater * mult * watM;
    s.stats['warmth'] = s.stats['warmth']! - toD(dk['warmth']) * km * cold * weatherWarm * warmM * mult;
    if (bonus) {
      s.bonusKm += km;
    } else {
      s.bonusKm = 0.0;
    }
  }

  /// Ближайшая остановка впереди: (позиция, тип, данные).
  (double, String, Object?) nextStop() {
    final pos = s.pos;
    (double, String, Object?) best = (w.length, 'finish', null);
    for (final p in w.stopsPlaces) {
      if (p.pos > pos + 1e-6) {
        if (p.pos < best.$1) best = (p.pos, 'place', p.place);
        break;
      }
    }
    for (final a in w.anchored) {
      if (a.pos > pos + 1e-6 && !s.seen.contains(a.event['id'])) {
        if (a.pos < best.$1) best = (a.pos, 'event', a.event['id']);
        break;
      }
    }
    s.quests.forEach((qid, q) {
      final quest = w.quests[qid];
      if (quest == null) return;
      final steps = quest['steps'] as List;
      if (q.step < steps.length) {
        var qPos = q.startPos + toD((steps[q.step] as Map)['at_km']) * 1000.0;
        if (qPos <= pos + 1e-6) qPos = pos + 1.0;
        if (qPos < best.$1) best = (qPos, 'quest', qid);
      }
    });
    if (s.nextRandomAt > pos + 1e-6 && s.nextRandomAt < best.$1 && s.pos >= s.maxPos - 1e-6) {
      best = (s.nextRandomAt, 'random', null);
    }
    final nn = s.nextNightAt;
    if (_nightOn && nn > pos + 1e-6 && nn < best.$1 && s.pos >= s.maxPos - 1e-6) {
      best = (nn, 'night', null);
    }
    return best;
  }

  /// Двигает героя на накопленный буфер. Пока есть overflow (ожидающее решение), герой стоит.
  List<EngineEvent> advance(int now) {
    final out = <EngineEvent>[];
    s.undo = null; // кнопки «Сучок»/«Бусина» — только на экране исхода, до «Идти дальше»
    applyTime(now);
    var guard = 0;
    while (s.buffer > 0.5 && s.stop == null && s.overflow.isEmpty && !s.finished) {
      guard++;
      if (guard > 10000) break;
      if (s.delayUntil > now) break;
      final d = s.detour;
      if (d != null) {
        final step = math.min(s.buffer, d.remaining);
        if (!_walk(step, now, onRoute: false)) {
          out.add(const EngineEvent('death'));
          break;
        }
        d.remaining -= step;
        s.buffer -= step;
        if (d.remaining <= 0.5) {
          final end = d.end;
          s.detour = null;
          _log(now, 'detour_back');
          if (end != null && w.eventsById.containsKey(end)) {
            s.stop = {'type': 'event', 'event': end};
            s.aidLock = false;
            out.add(EngineEvent('stop', s.stop));
          }
        }
        continue;
      }
      final (target, kind, data) = nextStop();
      final step = math.min(s.buffer, target - s.pos);
      if (step > 0) {
        if (!_walk(step, now, onRoute: true)) {
          out.add(const EngineEvent('death'));
          break;
        }
        s.buffer -= step;
      }
      if (s.pos >= target - 0.5) {
        s.pos = math.max(s.pos, target);
        s.maxPos = math.max(s.maxPos, s.pos);
        _arrive(kind, data, now);
        if (s.stop != null) out.add(EngineEvent('stop', s.stop));
      }
    }
    _saveRng();
    return out;
  }

  /// Идёт кусками по 250 м. Возвращает false, если герой погиб.
  bool _walk(double dist, int now, {required bool onRoute}) {
    var left = dist;
    while (left > 1e-6) {
      final chunk = math.min(250.0, left);
      _drainWalk(chunk / 1000.0, now);
      _autoConsume(now);
      _clampStats();
      if (onRoute) {
        s.pos += chunk;
        s.maxPos = math.max(s.maxPos, s.pos);
      }
      left -= chunk;
      if (_minStat() <= 0) {
        if (_tryRescue(now)) continue;
        _die(now, 'stats');
        return false;
      }
    }
    return true;
  }

  void _arrive(String kind, Object? data, int now) {
    s.aidLock = false; // новая остановка — аптечка снова может сработать
    switch (kind) {
      case 'finish':
        s.finished = true;
        s.stop = {'type': 'finish'};
        _mark(now, w.chapters.length);
        _log(now, 'finish');
        return;
      case 'place':
        final p = data as Json;
        final tb = _m('town');
        s.stats['warmth'] = s.stats['warmth']! + toD(tb['warmthRestore']);
        s.stats['water'] = s.stats['water']! + toD(tb['waterRefill']);
        _clampStats();
        _log(now, 'place', {'place': p['id']});
        _camp(p, now);
        if (_nightOn) {
          final skip = toD(_m('night')['skipNearPlaceKm']) * 1000.0;
          final ahead = s.nextNightAt - s.pos;
          // ночёвка рядом с местом — ночуют в месте (это и есть привал), отдельной остановки нет
          if (ahead >= 0 && ahead <= skip) s.nextNightAt = firstNightAfter(b, s.pos + skip);
        }
        final pid = p['id'] as String;
        if (p['kind'] == 'finish') {
          s.finished = true;
          s.stop = {'type': 'finish', 'place': pid};
          _mark(now, w.chapters.length);
        } else if (w.chapterEnd.containsKey(pid) && !s.seen.contains('chapter_end:$pid')) {
          // финал главы показывается один раз — после смерти с откатом город будет обычным привалом
          s.seen.add('chapter_end:$pid');
          _mark(now, toI(w.chapterEnd[pid]!['id']));
          s.stop = {'type': 'chapter_end', 'place': pid, 'chapter': toI(w.chapterEnd[pid]!['id'])};
        } else {
          s.stop = {'type': 'place', 'place': pid};
        }
        return;
      case 'event':
        s.stop = {'type': 'event', 'event': data as String};
        return;
      case 'quest':
        final qid = data as String;
        final q = s.quests[qid]!;
        s.stop = {'type': 'event', 'quest': qid, 'step': q.step, 'event': _questEvent(qid)['id']};
        return;
      case 'night':
        _night(now);
        return;
      case 'random':
        final e = _pickRandom(now);
        final sp = (_m('randomEvents')['spacingKm'] as List).map(toD).toList();
        var gap = (sp[0] + (sp[1] - sp[0]) * rng.nextFloat()) * 1000.0;
        // V5-53: на длинных северных главах случайные чаще (множитель промежутка по главе).
        final chMult = (_m('randomEvents')['chapterSpacingMult'] as Map?)?['${w.chapterAt(s.pos)}'];
        if (chMult != null) gap *= toD(chMult);
        if (inBonus()) gap /= toD(_m('bonus')['eventMultiplier']);
        var nxt = s.pos + gap;
        // не ставим случайное вплотную к авторскому
        final minGap = toD(_m('randomEvents')['minGapToAnchoredKm']) * 1000.0;
        for (final a in w.anchored) {
          if (a.pos > s.pos && !s.seen.contains(a.event['id']) && (a.pos - nxt).abs() < minGap) {
            nxt = a.pos + minGap;
          }
        }
        s.nextRandomAt = nxt;
        if (e != null) s.stop = {'type': 'event', 'event': e['id'], 'random': true};
        return;
    }
  }

  bool get _nightOn {
    final n = b['night'];
    return n is Map && n.isNotEmpty;
  }

  /// Ночёвка в пути (V5-45): +тепло, утренний бонус по весам (тратит RNG), camp-перки снаряжения.
  /// Остановка как привал: «Дальше» — и герой идёт теми же шагами, ждать следующего дня не нужно.
  void _night(int now) {
    final nb = _m('night');
    final morning = ((nb['morning'] as List?) ?? const []).map((m) => (m as Map).cast<String, dynamic>()).toList();
    final mo = morning.isEmpty
        ? const <String, dynamic>{}
        : morning[rng.pickWeighted(morning.map((m) => toI(m['weight'])).toList())];
    final gain = <String, int>{'warmth': toI(nb['warmth'])};
    for (final k in statKeys) {
      if (truthy(mo[k])) gain[k] = (gain[k] ?? 0) + toI(mo[k]);
    }
    gain.forEach((k, v) {
      s.stats[k] = s.stats[k]! + v;
    });
    _clampStats();
    final mid = (mo['id'] as String?) ?? '';
    _log(now, 'night', {'morning': mid, 'gain': Map<String, int>.of(gain)});
    _camp(const <String, dynamic>{'id': ''}, now);
    s.stop = {'type': 'night', 'morning': mid, 'gain': gain};
    s.nextNightAt = firstNightAfter(b, s.pos);
  }

  List<String> _tags(Json e) => ((e['tags'] as List?) ?? const []).map((t) => '$t').toList();

  Json? _pickRandom(int now) {
    final ch = 'ch${w.chapterAt(s.pos)}';
    final recent = s.recentRandom;
    final zone = w.zoneAt(s.pos);
    // недавние — отдельно по зоне: последние keepZ событий этой зоны
    final keepZ = math.max(1, math.min(12, w.zonePoolSize(zone) ~/ 2));
    final recentZoneAll = recent.where((r) => w.eventZone(r) == zone).toList();
    final recentZ = recentZoneAll.sublist(math.max(0, recentZoneAll.length - keepZ));
    final keepAll = math.max(1, math.min(12, w.randoms.length ~/ 2));
    final recentAll = recent.sublist(math.max(0, recent.length - keepAll));
    final inCh = w.randoms.where((e) {
      final tags = _tags(e);
      return tags.contains(ch) || tags.contains('any');
    }).toList();
    var pool = inCh.where((e) => e['zone'] == zone && !recentZ.contains(e['id'])).toList();
    final base = inCh.where((e) => !recentAll.contains(e['id'])).toList();
    if (pool.isEmpty) {
      pool = base; // запасной выбор: из всех зон
      if (pool.isNotEmpty) _log(now, 'zone_fallback', {'zone': zone});
    }
    if (pool.isEmpty) return null;
    if (noticed() && rng.nextFloat() < toD(_m('bonus')['noticeRiskChance'])) {
      final risky = pool.where((e) => _tags(e).contains('risk')).toList();
      if (risky.isNotEmpty) pool = risky;
    }
    final e = pool[rng.nextU32() % pool.length];
    s.recentRandom.add(e['id'] as String);
    final keep = toI(_m('randomEvents')['recentKeep'] ?? 36);
    if (s.recentRandom.length > keep) {
      s.recentRandom = s.recentRandom.sublist(s.recentRandom.length - keep);
    }
    return e;
  }

  Json _questEvent(String qid) {
    final q = s.quests[qid]!;
    final step = ((w.quests[qid]!['steps'] as List)[q.step] as Map).cast<String, dynamic>();
    if (step['event'] != null) return (step['event'] as Map).cast<String, dynamic>();
    final branches = (step['branches'] as List).cast<Map>();
    for (final br in branches) {
      final conds = ((br['if'] as Map?) ?? const {}).cast<String, dynamic>();
      var ok = true;
      conds.forEach((v, c) {
        if (!condHolds(q.vars[v] ?? 0, c as String)) ok = false;
      });
      if (ok) return (br['event'] as Map).cast<String, dynamic>();
    }
    return (branches.last['event'] as Map).cast<String, dynamic>();
  }

  // ------------------------------------------------ события
  Json? currentEvent() {
    final st = s.stop;
    if (st == null || st['type'] != 'event') return null;
    if (st['quest'] != null) {
      final qid = st['quest'] as String;
      if (!s.quests.containsKey(qid)) return null;
      return _questEvent(qid);
    }
    return w.eventsById[st['event']];
  }

  bool choiceAvailable(Json choice) {
    final req = (choice['requires'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    if (req['item'] != null && !hasItem('${req['item']}')) return false;
    if (req['coins'] != null && s.coins < toI(_sub(_m('levels'), 'coins')[req['coins']])) return false;
    if (req['flag'] != null && !s.flags.contains(req['flag'])) return false;
    return true;
  }

  /// Статический риск или «fatal», если исход может обнулить показатель прямо сейчас.
  String choiceRisk(Json choice) {
    final risk = (choice['risk'] as String?) ?? 'none';
    final statLv = _sub(_m('levels'), 'stat');
    for (final o in (choice['outcomes'] as List? ?? const [])) {
      final eff = ((o as Map)['effects'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
      for (final k in statKeys) {
        final v = eff[k];
        if (v is String && v.startsWith('-')) {
          if (s.stats[k]! - toD(statLv[v.substring(1)]) <= 0) return 'fatal';
        }
      }
    }
    return risk;
  }

  bool _isBadOutcome(Json o) {
    final eff = (o['effects'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
    if (truthy(eff['death'])) return true;
    final bad = '-${_m('riskReduce')['badLevel']}';
    for (final k in const ['satiety', 'water', 'warmth', 'coins']) {
      if (eff[k] == bad) return true;
    }
    return false;
  }

  /// Веса исходов с учётом оберега (riskReduce). Без оберега, у безопасного варианта (risk none)
  /// или если плохие исходы — все/ни одного, веса не меняются.
  List<int> outcomeWeights(Json choice, [List<String> ctx = const []]) {
    final outs = (choice['outcomes'] as List).cast<Map>().map((o) => o.cast<String, dynamic>()).toList();
    final ws = outs.map((o) => toI(o['weight'])).toList();
    final f = riskFactor(ctx);
    if (f == 1.0 || ((choice['risk'] as String?) ?? 'none') == 'none') return ws;
    final bad = outs.map(_isBadOutcome).toList();
    if (!bad.contains(true) || !bad.contains(false)) return ws;
    final scale = toI(_m('riskReduce')['weightScale']);
    return [
      for (var i = 0; i < ws.length; i++)
        bad[i] ? math.max(1, pyRound((ws[i] * scale).toDouble() * f).toInt()) : ws[i] * scale,
    ];
  }

  ChoiceResult choose(String choiceId, int now) {
    final ev = currentEvent();
    final st = s.stop;
    if (ev == null || st == null) return const ChoiceResult(ok: false);
    final choice = (ev['choices'] as List).cast<Map>().map((c) => c.cast<String, dynamic>()).firstWhere(
          (c) => c['id'] == choiceId,
          orElse: () => <String, dynamic>{},
        );
    if (choice.isEmpty || !choiceAvailable(choice)) return const ChoiceResult(ok: false);
    final outs = (choice['outcomes'] as List).cast<Map>().map((o) => o.cast<String, dynamic>()).toList();
    final ctx = eventCtx(ev);
    final oi = rng.pickWeighted(outcomeWeights(choice, ctx));
    final o = outs[oi];
    final pos0 = pyRound(s.pos).toInt();
    final questId = st['quest'] as String?;
    final step0 = questId == null ? null : s.quests[questId]?.step;
    final effects = (o['effects'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
    s.undo = null;
    final died = _applyEffects(effects, now, st, source: '${ev['id']}', ctx: ctx);
    final harm = _harm;
    if (!died && harm != null) s.undo = {...harm, 'event': ev['id']};
    if ((ev['once'] ?? true) == true && st['random'] != true) {
      if (!s.seen.contains(ev['id'])) s.seen.add(ev['id'] as String);
    }
    if (st['quest'] != null) {
      final qid = st['quest'] as String;
      final q = s.quests[qid];
      if (q != null) {
        q.step += 1;
        if (q.step >= (w.quests[qid]!['steps'] as List).length) {
          s.quests.remove(qid);
          s.questsDone += 1;
          _log(now, 'quest_done', {'quest': qid});
        }
      }
    }
    _log(now, 'event', {
      'event': ev['id'],
      'title': ev['title'],
      'choice': choice['text'],
      'outcome': o['text'] ?? '',
      // для журнала-таймлайна: какой вариант и исход, где, какой шаг квеста
      'cid': choiceId,
      'oi': oi,
      'pos': pos0,
      if (questId != null) 'quest': questId,
      if (step0 != null) 'step': step0,
    });
    s.eventsDone += 1;
    if (!died) s.stop = null;
    _saveRng();
    return ChoiceResult(ok: true, outcome: o, died: died, choice: choice);
  }

  // ------------------------------------------------ получение предметов
  /// Выдать предметы (эффект give, награда, находка). Не помещается — в очередь overflow, без потерь.
  void giveItems(Map<String, int> items, String source) {
    items.forEach((it, n) {
      final t = w.itemType(it);
      if (t == 'food' || t == 'drink') {
        final room = math.max(0, backpackSlots() - consumablesCount());
        final put = math.min(n, room);
        if (put != 0) s.inv[it] = (s.inv[it] ?? 0) + put;
        if (n - put > 0) s.overflow.add(OverflowItem(kind: 'backpack', item: it, n: n - put, source: source));
      } else if (t == 'gear') {
        for (var i = 0; i < n; i++) {
          _gainGear(it, source);
        }
      } else if (t == 'refill') {
        for (var i = 0; i < n; i++) {
          _gainRefill(it);
        }
      } else if (n != 0 && w.itemSpec(it).containsKey('uses')) {
        // инструмент с зарядами — одна ячейка-экземпляр; повтор пополняет заряды (до maxUses)
        final uses = toI(w.itemSpec(it)['uses']);
        if ((s.inv[it] ?? 0) > 0) {
          s.gearUses[it] = math.min(maxUses(it), usesLeft(it) + uses * n);
        } else {
          s.inv[it] = 1;
          s.gearUses[it] = math.min(maxUses(it), uses * n);
        }
      } else if (n != 0) {
        s.inv[it] = (s.inv[it] ?? 0) + n;
      }
    });
  }

  void _gainGear(String it, String source) {
    final pending = s.overflow.any((o) => o.kind == 'gear' && o.item == it);
    final spec = w.itemSpec(it);
    if (s.gear.contains(it) || pending) {
      // дубликат: пополняет заряды своего экземпляра, иначе — монеты (доля цены)
      if (s.gear.contains(it) && spec.containsKey('uses') && usesLeft(it) < maxUses(it)) {
        s.gearUses[it] = math.min(maxUses(it), usesLeft(it) + toI(spec['uses']));
      } else {
        s.coins += (w.itemValue(it, 'price') * toD(_m('economy')['duplicateGearShare'])).floor();
      }
      return;
    }
    if (w.freeSlot(it) || gearUsed() < gearSlots()) {
      s.gear.add(it); // дар духа ячейку не занимает — сразу в снаряжение
      _onGearAdded(it);
      return;
    }
    s.overflow.add(OverflowItem(kind: 'gear', item: it, n: 1, source: source));
  }

  /// Баллон: +amount зарядов предмету refill (до maxUses). Нет горелки или полна — монеты (цена баллона).
  bool _gainRefill(String it) {
    final spec = w.itemSpec(it);
    final tgt = '${spec['refill']}';
    if (s.gear.contains(tgt) && usesLeft(tgt) < maxUses(tgt)) {
      s.gearUses[tgt] = math.min(maxUses(tgt), usesLeft(tgt) + toI(spec['amount']));
      return true;
    }
    s.coins += toI(spec['price']);
    return false;
  }

  /// Эффект remove. Возвращает, что реально пропало (для «Бусины-морока»): ({id: {n, portions, uses}}, [gear…]).
  (Json, List<Json>) _removeItems(Json remove) {
    final lost = <String, dynamic>{};
    final lostGear = <Json>[];
    remove.forEach((it, n) {
      if (s.gear.contains(it)) {
        lostGear.add({'item': it, 'uses': s.gearUses[it], 'expires': s.expires[it], 'fed': s.fed[it]});
        s.gear.remove(it);
        _onGearRemoved(it);
        return;
      }
      final have = s.inv[it] ?? 0;
      final left = math.max(0, have - toI(n));
      if (have > 0) {
        lost[it] = {'n': have - left, 'portions': s.portionsLeft[it], 'uses': s.gearUses[it]};
      }
      if (left > 0) {
        s.inv[it] = left;
      } else if (s.inv.containsKey(it)) {
        s.inv.remove(it);
        s.portionsLeft.remove(it);
        if (w.itemType(it) == 'tool') s.gearUses.remove(it);
      }
    });
    return (lost, lostGear);
  }

  // ------------------------------------------------ переполнение
  /// Экран «Что взять с собой»: keep — ровно min(gearSlots, текущие+новая) id из текущих и новой.
  String? resolveGearOverflow(List<String> keep) {
    final ov = s.overflow;
    if (ov.isEmpty || ov.first.kind != 'gear') return 'no_gear_overflow';
    final nw = ov.first.item;
    if (w.freeSlot(nw)) {
      // старое сохранение: дар в очереди — просто взять (ячейку не занимает)
      if (!s.gear.contains(nw)) {
        s.gear.add(nw);
        _onGearAdded(nw);
      }
      ov.removeAt(0);
      _saveRng();
      return null;
    }
    // выбирают только среди обычного снаряжения; дары остаются на своих местах
    final cands = [...s.gear.where((g) => !w.freeSlot(g)), nw];
    final need = math.min(gearSlots(), cands.length);
    if (keep.length != need || keep.toSet().length != keep.length || keep.any((k) => !cands.contains(k))) {
      return 'bad_keep';
    }
    for (final c in cands) {
      if (!keep.contains(c) && c != nw) _onGearRemoved(c);
    }
    s.gear = [
      ...s.gear.where((g) => w.freeSlot(g) || keep.contains(g)),
      if (keep.contains(nw)) nw,
    ];
    if (keep.contains(nw)) _onGearAdded(nw);
    ov.removeAt(0);
    _saveRng();
    return null;
  }

  /// Вещь не лезет в рюкзак: use — использовать сразу; drop — выбросить; stash — положить
  /// (если рюкзак полон, swapAction 'use'|'drop' + swapItem из рюкзака освобождает ячейку).
  /// Решает ОДНУ единицу первой записи очереди.
  String? resolveBackpackOverflow(String action, int now, {String? swapAction, String? swapItem}) {
    final ov = s.overflow;
    if (ov.isEmpty || ov.first.kind != 'backpack') return 'no_backpack_overflow';
    final it = ov.first.item;
    if (action == 'use') {
      _consume(it, now);
    } else if (action == 'drop') {
      // ничего
    } else if (action == 'stash') {
      if (consumablesCount() >= backpackSlots()) {
        if (swapAction == null && swapItem == null) return 'need_swap';
        final si = swapItem;
        final sa = swapAction;
        if ((sa != 'use' && sa != 'drop') || si == null || (s.inv[si] ?? 0) <= 0 || !_isConsumable(si)) {
          return 'bad_swap';
        }
        if (sa == 'use') {
          if (w.portionsOf(si) > 1 && portionsOpen(si) > 1) return 'swap_not_free'; // порция ячейку не освобождает
          _useOne(si, now);
        } else {
          _takeInv(si, 1);
        }
      }
      s.inv[it] = (s.inv[it] ?? 0) + 1;
    } else {
      return 'bad_action';
    }
    ov.first.n -= 1;
    if (ov.first.n <= 0) ov.removeAt(0);
    _saveRng();
    return null;
  }

  // ------------------------------------------------ эффекты исхода
  /// Применить эффекты исхода. Вред (минусы, remove, delay, detour, bonus_reset) записывается в [_harm] —
  /// choose() кладёт его в s.undo для «Сучка»/«Бусины» (§13.4).
  bool _applyEffects(Json eff, int now, Json? stop, {String source = '', List<String> ctx = const []}) {
    final lv = _m('levels');
    int lvl(String table, String v) => toI(_sub(lv, table)[v.replaceFirst('-', '')]);
    final harm = <String, dynamic>{};
    if (eff['coins'] != null) {
      final v = eff['coins'] as String;
      var amt = lvl('coins', v);
      if (v.startsWith('-') && gearFlag('noCoinLoss', ctx)) amt = 0; // ракушка-пропуск: у воды денег не берут
      final before = s.coins;
      s.coins = math.max(0, s.coins + (v.startsWith('-') ? -amt : amt));
      if (before > s.coins) harm['coins'] = before - s.coins;
    }
    final pre = Map<String, double>.of(s.stats);
    final neg = <String>[];
    for (final k in statKeys) {
      if (eff[k] != null) {
        final v = eff[k] as String;
        final amt = lvl('stat', v).toDouble();
        s.stats[k] = s.stats[k]! + (v.startsWith('-') ? -amt : amt);
        if (v.startsWith('-')) neg.add(k);
      }
    }
    _clampStats();
    final lostStats = <String, dynamic>{};
    for (final k in neg) {
      final d = pre[k]! - s.stats[k]!;
      if (d > 0) lostStats[k] = d;
    }
    if (lostStats.isNotEmpty) harm['stats'] = lostStats;
    final (lostItems, lostGear) =
        _removeItems((eff['remove'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{});
    if (lostItems.isNotEmpty) harm['removed'] = lostItems;
    if (lostGear.isNotEmpty) harm['removedGear'] = lostGear;
    final give = ((eff['give'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', toI(v)));
    giveItems(give, source);
    final flag = eff['flag'];
    if (flag != null) {
      final list = flag is String ? [flag] : (flag as List).map((f) => '$f').toList();
      for (final f in list) {
        if (!s.flags.contains(f)) s.flags.add(f);
      }
    }
    final qs = eff['quest_start'] as String?;
    if (qs != null && !s.quests.containsKey(qs) && w.quests.containsKey(qs)) {
      s.quests[qs] = QuestProgress(startPos: s.pos);
    }
    if (eff['quest_var'] != null) {
      final vars = (eff['quest_var'] as Map).cast<String, dynamic>();
      final ownQuest = stop?['quest'] as String?;
      final targets = (ownQuest != null && s.quests.containsKey(ownQuest)) ? [ownQuest] : s.quests.keys.toList();
      for (final qid in targets) {
        vars.forEach((v, d) {
          final q = s.quests[qid]!;
          q.vars[v] = (q.vars[v] ?? 0) + toI(d);
        });
      }
    }
    if (truthy(eff['bonus_reset'])) {
      harm['bonusKm'] = s.bonusKm;
      s.bonusKm = 0.0;
    }
    if (eff['delay'] != null) {
      harm['delay'] = s.delayUntil;
      var h = toD(_sub(lv, 'delayHours')[eff['delay']]);
      final m = gearMult('delayMult');
      if (m != 1.0) h = math.max(1.0, pyRound(h * m));
      s.delayUntil = now + (h * msHour).toInt();
    }
    if (eff['detour'] != null) {
      var km = toD(_sub(lv, 'detourKm')[eff['detour']]);
      final m = gearMult('detourMult');
      if (m != 1.0) km = math.max(1.0, pyRound(km * m));
      final dm = km * 1000.0;
      if (!truthy(eff['detour_end'])) {
        // ответвление с концом-событием — сюжет, его дары не отменяют
        harm['detour'] = true;
        harm['prevDetour'] = s.detour?.toJson();
      }
      s.detour = Detour(remaining: dm, total: dm, end: eff['detour_end'] as String?);
    }
    if (eff['shortcut'] != null) {
      final jump = toD(_sub(lv, 'shortcutKm')[eff['shortcut']]) * 1000.0;
      s.stop = null;
      final (target, _, _) = nextStop();
      s.pos = math.min(s.pos + jump, target - 1.0);
      s.maxPos = math.max(s.maxPos, s.pos);
    }
    _harm = harm.isEmpty ? null : harm;
    if (truthy(eff['death'])) {
      _die(now, 'event');
      return true;
    }
    if (_minStat() <= 0) {
      if (_tryRescue(now)) return false;
      _die(now, 'event');
      return true;
    }
    return false;
  }

  // ------------------------------------------------ смерть
  /// Средний игровой путь в день за последние N дней (дни без шагов считаются нулём).
  double avgDailyGameM() {
    final window = toI(_m('death')['rollbackDaysWindow']);
    final days = s.daySteps.keys.toList()..sort();
    final last = days.length > window ? days.sublist(days.length - window) : days;
    if (last.isEmpty) return 0.0;
    var sum = 0;
    for (final d in last) {
      sum += s.daySteps[d]!;
    }
    return sum / last.length * gameMetersPerStep();
  }

  void _die(int now, String cause) {
    final d = _m('death');
    final window = toI(d['rollbackDaysWindow']);
    final days = s.daySteps.keys.toList()..sort();
    final activeAll = days.map((k) => s.daySteps[k]!).where((x) => x > 0).toList();
    final active = activeAll.length > window ? activeAll.sublist(activeAll.length - window) : activeAll;
    var perDay = 0.0;
    if (active.isNotEmpty) {
      perDay = active.reduce((a, b2) => a + b2) / active.length * gameMetersPerStep();
    }
    final back = math.max(toD(d['rollbackMinKm']) * 1000.0, math.min(toD(d['rollbackMaxKm']) * 1000.0, perDay));
    final old = s.pos;
    s.pos = math.max(0.0, old - back);
    for (final k in s.inv.keys.toList()) {
      if (_isConsumable(k)) {
        final keep = (s.inv[k]! * toD(d['keepConsumablesShare'])).floor();
        if (keep > 0) {
          s.inv[k] = keep;
        } else {
          s.inv.remove(k);
          s.portionsLeft.remove(k);
        }
      }
    }
    final lost = (s.coins * toD(d['coinLossShare'])).floor();
    s.coins -= lost;
    final respawn = toD(_m('stats')['respawn']);
    for (final k in statKeys) {
      s.stats[k] = respawn;
    }
    s.detour = null;
    s.delayUntil = 0;
    s.bonusKm = 0.0;
    s.heated = false;
    s.heatedDay = 0;
    s.overflow = [];
    s.aidLock = false;
    s.undo = null;
    s.quests.removeWhere((qid, _) => w.quests[qid]?['kind'] == 'companion');
    s.nextRandomAt = math.max(s.nextRandomAt, s.maxPos + toD(_m('randomEvents')['firstAfterKm']) * 1000.0);
    s.deaths += 1;
    final place = w.lastPlaceBefore(s.pos);
    s.stop = {
      'type': 'death',
      'cause': cause,
      'back': pyRound1((old - s.pos) / 1000.0),
      'place': place['id'],
      'coinsLost': lost,
    };
    _log(now, 'death', {'place': place['id'], 'cause': cause});
  }

  // ------------------------------------------------ рынок и остановки
  List<MarketOffer> market() {
    final st = s.stop;
    if (st == null || (st['type'] != 'place' && st['type'] != 'chapter_end')) return const [];
    final p = w.placeById[st['place']];
    if (p == null) return const [];
    final markets = _sub(_m('economy'), 'markets');
    final type = p['market'];
    if (type == null || type == 'regional') return const [];
    final m = markets['$type'];
    if (m is! Map) return const [];
    final ids = ((m['items'] as List?) ?? const []).map((i) => '$i').toList();
    final regional = markets['regional'];
    if (regional is Map) {
      for (final i in ((regional[p['id']] as List?) ?? const [])) {
        if (!ids.contains('$i')) ids.add('$i'); // региональные товары места — в конец, по наценке рынка места
      }
    }
    final mult = toD(m['priceMult']);
    return [
      for (final i in ids) MarketOffer(i, pyRound(w.itemValue(i, 'price') * mult).toInt()),
    ];
  }

  /// Почему нельзя купить: null — можно; иначе код причины для интерфейса.
  String? buyBlocker(String item) {
    final offer = market().where((o) => o.item == item).toList();
    if (offer.isEmpty) return 'not_sold';
    if (s.coins < offer.first.price) return 'no_coins';
    final t = w.itemType(item);
    if ((t == 'food' || t == 'drink') && consumablesCount() >= backpackSlots()) return 'backpack_full';
    if (t == 'gear') {
      if (s.gear.contains(item)) return 'have_gear';
      // рюкзак — только больше нынешнего (меньший освободил бы ячейки, а вещи бы не влезли)
      final cur = currentPack();
      if (w.isPack(item) && cur != null && toI(w.packSpec(cur)!['slots']) >= toI(w.packSpec(item)!['slots'])) {
        return 'pack_smaller';
      }
      if (!w.freeSlot(item) && gearUsed() >= gearSlots()) return 'gear_full';
    }
    if (t == 'refill') {
      final tgt = '${w.itemSpec(item)['refill']}';
      if (!s.gear.contains(tgt)) return 'no_stove';
      if (usesLeft(tgt) >= maxUses(tgt)) return 'gas_full';
    }
    return null;
  }

  bool buy(String item, int now) {
    if (buyBlocker(item) != null) return false;
    final price = market().firstWhere((o) => o.item == item).price;
    s.coins -= price;
    final t = w.itemType(item);
    if (t == 'gear') {
      // новый рюкзак: старый отдаём продавцу за долю цены (как дубликат снаряжения)
      if (w.isPack(item)) {
        for (final old in s.gear.where(w.isPack).toList()) {
          s.gear.remove(old);
          _onGearRemoved(old);
          s.coins += (w.itemValue(old, 'price') * toD(_m('economy')['duplicateGearShare'])).floor();
        }
      }
      _gainGear(item, 'market');
    } else if (t == 'refill') {
      _gainRefill(item);
    } else {
      s.inv[item] = (s.inv[item] ?? 0) + 1;
    }
    _log(now, 'buy', {'item': item, 'price': price});
    return true;
  }

  /// Выбросить 1 шт.: из снаряжения — предмет целиком (с зарядами), из рюкзака/инструментов — одну единицу.
  /// null — выброшено; 'gift' — дар духа выбросить нельзя; 'no_item' — нечего выбрасывать.
  String? dropItem(String item) {
    if (w.isGift(item) && hasItem(item)) return 'gift';
    if (w.isPack(item) && s.gear.contains(item)) return 'pack';
    if (s.gear.contains(item)) {
      s.gear.remove(item);
      _onGearRemoved(item);
    } else if ((s.inv[item] ?? 0) > 0) {
      _takeInv(item, 1);
      if (!s.inv.containsKey(item) && w.itemType(item) == 'tool') s.gearUses.remove(item);
    } else {
      return 'no_item';
    }
    _saveRng();
    return null;
  }

  /// «Идти дальше». false — отказ (есть overflow, событие закрывается только выбором, финиш, нет остановки).
  bool continueJourney(int now) {
    final st = s.stop;
    if (s.overflow.isNotEmpty) return false;
    if (st == null || st['type'] == 'finish') return false;
    if (st['type'] == 'event') return false;
    if (st['type'] == 'chapter_end') {
      s.stop = {'type': 'place', 'place': st['place']};
      return true;
    }
    s.stop = null;
    return true;
  }

  // ------------------------------------------------ для интерфейса
  int? daysLeft() {
    final perDay = avgDailyGameM();
    if (perDay <= 0) return null;
    return (math.max(0.0, w.length - s.pos) / perDay).ceil();
  }

  double kmLeft() => math.max(0.0, w.length - s.pos) / 1000.0;

  /// Время суток по прогрессу: 0..1 (0 — рассвет).
  double dayPhase() {
    final len = toD(_m('movement')['dayLengthKm']) * 1000.0;
    return (s.pos % len) / len;
  }

  bool get isDelayed => s.delayUntil > DateTime.now().millisecondsSinceEpoch;
}

bool condHolds(int value, String cond) {
  for (final op in const ['>=', '<=', '==', '>', '<']) {
    if (cond.startsWith(op)) {
      final n = int.parse(cond.substring(op.length));
      switch (op) {
        case '>=':
          return value >= n;
        case '<=':
          return value <= n;
        case '==':
          return value == n;
        case '>':
          return value > n;
        default:
          return value < n;
      }
    }
  }
  return false;
}

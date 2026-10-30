// Игровой движок «Путника». Чистый Dart. Повторяет tools/sim/engine.py правило в правило.

import 'dart:math' as math;

import 'rng.dart';
import 'state.dart';
import 'world.dart';

const int msHour = 3600000;

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
  Engine(this.w, this.s) : rng = Rng(s.rng);

  final World w;
  final HeroState s;
  final Rng rng;

  Json get b => w.balance;
  Json _m(String k) => (b[k] as Map).cast<String, dynamic>();
  Json _sub(Json m, String k) => (m[k] as Map).cast<String, dynamic>();

  // ------------------------------------------------ утилиты
  void _saveRng() => s.rng = rng.state;

  void _log(int now, String kind, [Json data = const {}]) {
    s.journal.add(JournalEntry(now, kind, Map<String, dynamic>.from(data)));
    if (s.journal.length > 400) {
      s.journal.removeRange(0, s.journal.length - 400);
    }
  }

  double gameMetersPerStep() {
    final m = _m('movement');
    return toD(m['stepLengthM']) * toD(m['gameMultiplier']);
  }

  int consumablesCount() {
    var n = 0;
    s.inv.forEach((k, v) {
      final t = w.itemType(k);
      if (t == 'food' || t == 'drink') n += v;
    });
    return n;
  }

  int backpackSlots() => toI(_m('economy')['backpackSlots']);

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

  // ------------------------------------------------ время
  void applyTime(int now) {
    final hours = math.max(0.0, (now - s.lastTick) / msHour);
    s.lastTick = now;
    if (hours <= 0) return;
    final floor = toD(b['idleFloor']);
    final perHour = _m('drainPerHour');
    for (final k in statKeys) {
      final cur = s.stats[k]!;
      final nxt = cur - toD(perHour[k]) * hours;
      s.stats[k] = math.max(nxt, math.min(cur, floor));
    }
    _autoConsume(now);
  }

  // ------------------------------------------------ еда из рюкзака
  double _gain(String item, String stat) => w.itemValue(item, stat);

  void _autoConsume(int now) {
    final thr = toD(_m('stats')['autoConsumeBelow']);
    for (final stat in statKeys) {
      for (var guard = 0; guard < 4; guard++) {
        if (s.stats[stat]! >= thr) break;
        final cands = s.inv.entries
            .where((e) =>
                e.value > 0 &&
                (w.itemType(e.key) == 'food' || w.itemType(e.key) == 'drink') &&
                _gain(e.key, stat) > 0)
            .map((e) => e.key)
            .toList()
          ..sort();
        if (cands.isEmpty) break;
        final gap = maxStat - s.stats[stat]!;
        final fitting = cands.where((k) => _gain(k, stat) <= gap).toList();
        String pick;
        if (fitting.isNotEmpty) {
          pick = fitting.first;
          for (final k in fitting) {
            if (_gain(k, stat) > _gain(pick, stat)) pick = k;
          }
        } else {
          pick = cands.first;
          for (final k in cands) {
            if (_gain(k, stat) < _gain(pick, stat)) pick = k;
          }
        }
        _useItem(pick, now, auto: true);
      }
    }
  }

  void _useItem(String item, int now, {bool auto = false}) {
    s.inv[item] = (s.inv[item] ?? 0) - 1;
    if (s.inv[item]! <= 0) s.inv.remove(item);
    for (final k in statKeys) {
      s.stats[k] = s.stats[k]! + w.itemValue(item, k);
    }
    _clampStats();
    if (auto) _log(now, 'eat', {'item': item});
  }

  /// Съесть или выпить вручную из рюкзака.
  bool useItem(String item, int now) {
    final t = w.itemType(item);
    if ((s.inv[item] ?? 0) <= 0 || (t != 'food' && t != 'drink')) return false;
    _useItem(item, now);
    _saveRng();
    return true;
  }

  // ------------------------------------------------ движение
  String weatherHere() => w.weatherAt(s.seed, s.pos);

  void _drainWalk(double km) {
    final dk = _m('drainPerKm');
    final bonus = inBonus();
    final mult = bonus ? toD(_m('bonus')['drainMultiplier']) : 1.0;
    final wx = _sub(_sub(_m('weather'), 'types'), w.weatherAt(s.seed, s.pos));
    final cold = toD(_m('chapterCold')['${w.chapterAt(s.pos)}']);
    var gear = 1.0;
    if ((s.inv['socks'] ?? 0) > 0) gear *= w.itemValue('socks', 'warmthDrainMult');
    var weatherWarm = wx['warmth'] == null ? 1.0 : toD(wx['warmth']);
    if ((s.inv['raincoat'] ?? 0) > 0 && weatherWarm > 1.0) {
      weatherWarm = 1.0 + (weatherWarm - 1.0) * w.itemValue('raincoat', 'weatherWarmthMult');
    }
    final wxWater = wx['water'] == null ? 1.0 : toD(wx['water']);
    s.stats['satiety'] = s.stats['satiety']! - toD(dk['satiety']) * km * mult;
    s.stats['water'] = s.stats['water']! - toD(dk['water']) * km * wxWater * mult;
    s.stats['warmth'] = s.stats['warmth']! - toD(dk['warmth']) * km * cold * weatherWarm * gear * mult;
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
    return best;
  }

  /// Двигает героя на накопленный буфер.
  List<EngineEvent> advance(int now) {
    final out = <EngineEvent>[];
    applyTime(now);
    var guard = 0;
    while (s.buffer > 0.5 && s.stop == null && !s.finished) {
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
      _drainWalk(chunk / 1000.0);
      _autoConsume(now);
      _clampStats();
      if (onRoute) {
        s.pos += chunk;
        s.maxPos = math.max(s.maxPos, s.pos);
      }
      left -= chunk;
      if (_minStat() <= 0) {
        _die(now, 'stats');
        return false;
      }
    }
    return true;
  }

  void _arrive(String kind, Object? data, int now) {
    switch (kind) {
      case 'finish':
        s.finished = true;
        s.stop = {'type': 'finish'};
        _log(now, 'finish');
        return;
      case 'place':
        final p = data as Json;
        final tb = _m('town');
        s.stats['warmth'] = s.stats['warmth']! + toD(tb['warmthRestore']);
        s.stats['water'] = s.stats['water']! + toD(tb['waterRefill']);
        _clampStats();
        _log(now, 'place', {'place': p['id']});
        final pid = p['id'] as String;
        if (p['kind'] == 'finish') {
          s.finished = true;
          s.stop = {'type': 'finish', 'place': pid};
        } else if (w.chapterEnd.containsKey(pid) && !s.seen.contains('chapter_end:$pid')) {
          // финал главы показывается один раз — после смерти с откатом город будет обычным привалом
          s.seen.add('chapter_end:$pid');
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
      case 'random':
        final e = _pickRandom();
        final sp = (_m('randomEvents')['spacingKm'] as List).map(toD).toList();
        var gap = (sp[0] + (sp[1] - sp[0]) * rng.nextFloat()) * 1000.0;
        if (inBonus()) gap /= toD(_m('bonus')['eventMultiplier']);
        var nxt = s.pos + gap;
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

  Json? _pickRandom() {
    final ch = 'ch${w.chapterAt(s.pos)}';
    var pool = w.randoms.where((e) {
      final tags = (e['tags'] as List? ?? const []);
      return (tags.contains(ch) || tags.contains('any')) && !s.recentRandom.contains(e['id']);
    }).toList();
    if (pool.isEmpty) return null;
    if (noticed() && rng.nextFloat() < toD(_m('bonus')['noticeRiskChance'])) {
      final risky = pool.where((e) => (e['tags'] as List? ?? const []).contains('risk')).toList();
      if (risky.isNotEmpty) pool = risky;
    }
    final e = pool[rng.nextU32() % pool.length];
    s.recentRandom.add(e['id'] as String);
    final keep = math.max(1, math.min(12, w.randoms.length ~/ 2));
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
      final conds = (br['if'] as Map).cast<String, dynamic>();
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
    final req = (choice['requires'] as Map?)?.cast<String, dynamic>() ?? const {};
    if (req['item'] != null && (s.inv[req['item']] ?? 0) <= 0) return false;
    if (req['coins'] != null && s.coins < toI(_sub(_m('levels'), 'coins')[req['coins']])) return false;
    if (req['flag'] != null && !s.flags.contains(req['flag'])) return false;
    return true;
  }

  /// Статический риск или «fatal», если исход может обнулить показатель прямо сейчас.
  String choiceRisk(Json choice) {
    final risk = (choice['risk'] as String?) ?? 'none';
    final statLv = _sub(_m('levels'), 'stat');
    for (final o in (choice['outcomes'] as List? ?? const [])) {
      final eff = ((o as Map)['effects'] as Map?)?.cast<String, dynamic>() ?? const {};
      for (final k in statKeys) {
        final v = eff[k];
        if (v is String && v.startsWith('-')) {
          if (s.stats[k]! - toD(statLv[v.substring(1)]) <= 0) return 'fatal';
        }
      }
    }
    return risk;
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
    final o = outs[rng.pickWeighted(outs.map((x) => toI(x['weight'])).toList())];
    final effects = (o['effects'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
    final died = _applyEffects(effects, now, st);
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
          _log(now, 'quest_done', {'quest': qid});
        }
      }
    }
    _log(now, 'event', {
      'event': ev['id'],
      'title': ev['title'],
      'choice': choice['text'],
      'outcome': o['text'] ?? '',
    });
    if (!died) s.stop = null;
    _saveRng();
    return ChoiceResult(ok: true, outcome: o, died: died, choice: choice);
  }

  bool _applyEffects(Json eff, int now, Json? stop) {
    final lv = _m('levels');
    int lvl(String table, String v) => toI(_sub(lv, table)[v.replaceFirst('-', '')]);
    if (eff['coins'] != null) {
      final v = eff['coins'] as String;
      final amt = lvl('coins', v);
      s.coins = math.max(0, s.coins + (v.startsWith('-') ? -amt : amt));
    }
    for (final k in statKeys) {
      if (eff[k] != null) {
        final v = eff[k] as String;
        final amt = lvl('stat', v).toDouble();
        s.stats[k] = s.stats[k]! + (v.startsWith('-') ? -amt : amt);
      }
    }
    _clampStats();
    ((eff['remove'] as Map?) ?? const {}).forEach((it, n) {
      final have = s.inv[it] ?? 0;
      final left = math.max(0, have - toI(n));
      if (left > 0) {
        s.inv[it as String] = left;
      } else {
        s.inv.remove(it);
      }
    });
    ((eff['give'] as Map?) ?? const {}).forEach((it, n) {
      var count = toI(n);
      final t = w.itemType(it as String);
      if (t == 'food' || t == 'drink') {
        final room = backpackSlots() - consumablesCount();
        count = math.max(0, math.min(count, room));
      }
      if (count > 0) s.inv[it] = (s.inv[it] ?? 0) + count;
    });
    final flag = eff['flag'];
    if (flag != null) {
      final list = flag is String ? [flag] : (flag as List).cast<String>();
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
    if (eff['bonus_reset'] == true) s.bonusKm = 0.0;
    if (eff['delay'] != null) {
      s.delayUntil = now + (toD(_sub(lv, 'delayHours')[eff['delay']]) * msHour).toInt();
    }
    if (eff['detour'] != null) {
      final m = toD(_sub(lv, 'detourKm')[eff['detour']]) * 1000.0;
      s.detour = Detour(remaining: m, total: m, end: eff['detour_end'] as String?);
    }
    if (eff['shortcut'] != null) {
      final jump = toD(_sub(lv, 'shortcutKm')[eff['shortcut']]) * 1000.0;
      s.stop = null;
      final (target, _, _) = nextStop();
      s.pos = math.min(s.pos + jump, target - 1.0);
      s.maxPos = math.max(s.maxPos, s.pos);
    }
    if (eff['death'] == true || _minStat() <= 0) {
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
      final t = w.itemType(k);
      if (t == 'food' || t == 'drink') {
        final keep = (s.inv[k]! * toD(d['keepConsumablesShare'])).floor();
        if (keep > 0) {
          s.inv[k] = keep;
        } else {
          s.inv.remove(k);
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
    final markets = _sub(_m('economy'), 'markets');
    final m = markets[p?['market'] ?? 'none'] as Map?;
    if (m == null) return const [];
    final mult = toD(m['priceMult']);
    return [
      for (final i in (m['items'] as List).cast<String>())
        MarketOffer(i, pyRound(w.itemValue(i, 'price') * mult).toInt()),
    ];
  }

  /// Почему нельзя купить: null — можно; иначе код причины для интерфейса.
  String? buyBlocker(String item) {
    final offer = market().where((o) => o.item == item).toList();
    if (offer.isEmpty) return 'not_sold';
    if (s.coins < offer.first.price) return 'no_coins';
    final t = w.itemType(item);
    if ((t == 'food' || t == 'drink') && consumablesCount() >= backpackSlots()) return 'backpack_full';
    if (t == 'gear' && (s.inv[item] ?? 0) > 0) return 'have_gear';
    return null;
  }

  bool buy(String item, int now) {
    if (buyBlocker(item) != null) return false;
    final price = market().firstWhere((o) => o.item == item).price;
    s.coins -= price;
    s.inv[item] = (s.inv[item] ?? 0) + 1;
    _log(now, 'buy', {'item': item, 'price': price});
    return true;
  }

  void continueJourney(int now) {
    final st = s.stop;
    if (st == null || st['type'] == 'finish' || st['type'] == 'event') return;
    if (st['type'] == 'chapter_end') {
      s.stop = {'type': 'place', 'place': st['place']};
      return;
    }
    s.stop = null;
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

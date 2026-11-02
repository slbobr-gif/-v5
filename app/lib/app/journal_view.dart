// Журнал-таймлайн (вариант B «Таймлайн с цепочками», docs/v5/04-art-style.md, раздел «Журнал»):
// записи движка (hero.journal) + контент → строки по дням, цепочки, эффекты и тексты вариантов.
// Только вычисление из имеющихся записей и контента; движок и сохранение не меняются.

import 'dart:math' as math;

import '../data/content_repository.dart';
import '../engine/state.dart';
import '../engine/world.dart';

/// Вид записи — цвет стеклянной метки и фильтр «Тип».
enum JKind { story, random, spirit, quest, item, death, thought, camp }

/// Исход события для фильтра «Исход».
enum JTone { good, bad, mixed }

/// Вид цепочки: линия квеста, линия духа, смерть → откат.
enum JChainKind { quest, spirit, death }

/// Эффект исхода по контенту (номинал, без поправок снаряжения).
class JEffect {
  const JEffect(this.type, {this.key = '', this.value = 0});

  /// coins | stat | give | remove | delay | detour | shortcut | death | rollback
  final String type;

  /// Показатель (satiety | water | warmth) или id предмета.
  final String key;

  /// Со знаком у coins и stat; штуки у give/remove; часы у delay; км у detour/shortcut/rollback.
  final num value;

  bool get negative => switch (type) {
        'remove' || 'delay' || 'detour' || 'death' || 'rollback' => true,
        'coins' || 'stat' => value < 0,
        _ => false,
      };
}

/// Что открыло событие: начало линии (quest) или следующий шаг линии (step, номер с 1).
class JOpen {
  const JOpen(this.type, this.quest, [this.step = 0]);
  final String type;
  final String quest;
  final int step;
}

/// Строка ленты: запись журнала или утренняя мысль.
class JRow {
  JRow({required this.kind, required this.t, required this.day, this.entry, this.km, this.zone, this.order = 0, this.seq = 0});

  /// Номер строки в [JournalView.rows] (по времени).
  int id = -1;

  /// Порядок записи в hero.journal (у мысли −1).
  final int order;

  /// Ключ порядка внутри одного времени: смерть и «История завершена» движок пишет до записи
  /// события, которое к ним привело, — в ленте они идут после него.
  final double seq;
  final JournalEntry? entry;
  final JKind kind;
  final int t;
  final int day;
  final double? km;
  final String? zone;

  // событие
  String? eventId;
  String? choice;
  String outcome = '';
  List<String> alts = const [];
  List<JEffect> effects = const [];
  List<JOpen> opened = const [];
  JTone? tone;
  String? quest;

  /// Шаг квеста, с 0 (как в движке).
  int? step;

  // цепочка
  String? chain;

  /// Утренняя мысль: день пути.
  int? thoughtDay;
}

class JChain {
  JChain(this.id, this.kind, {this.quest, this.creature});

  /// q:<квест> | c:<дух> | d:<номер строки смерти>
  final String id;
  final JChainKind kind;
  final String? quest;
  final String? creature;

  /// Номера строк по времени.
  final List<int> rows = [];

  /// Следующий шаг линии (номер с 1) и через сколько км, если линия идёт.
  int? nextStep;
  double? nextKm;
  bool done = false;
}

class JDay {
  JDay(this.day, this.date);
  final int day;
  final DateTime date;
  final List<int> rows = [];
  double? kmFrom;
  double? kmTo;
  int steps = 0;
}

class JournalView {
  JournalView({required this.rows, required this.chains, required this.days, required this.today});

  final List<JRow> rows;
  final Map<String, JChain> chains;
  final List<JDay> days;
  final int today;

  /// Предыдущее и следующее звено цепочки (null — нет).
  JRow? prevInChain(JRow r) {
    final c = chains[r.chain];
    if (c == null) return null;
    final i = c.rows.indexOf(r.id);
    return i > 0 ? rows[c.rows[i - 1]] : null;
  }

  JRow? nextInChain(JRow r) {
    final c = chains[r.chain];
    if (c == null) return null;
    final i = c.rows.indexOf(r.id);
    return (i >= 0 && i + 1 < c.rows.length) ? rows[c.rows[i + 1]] : null;
  }

  /// Цепочки в порядке первого звена.
  List<JChain> get chainList {
    final list = chains.values.where((c) => c.rows.isNotEmpty).toList();
    list.sort((a, b) => a.rows.first.compareTo(b.rows.first));
    return list;
  }
}

const _itemKinds = {
  'buy', 'eat', 'sell', 'gift', 'ability', 'first_aid', 'heat', 'loadout', 'upkeep', 'wilt', 'goal', 'login', //
};

String _dayKey(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

List<Json> _maps(Object? v) => ((v as List?) ?? const []).map((e) => (e as Map).cast<String, dynamic>()).toList();

bool _on(Object? v) => v == true || (v is num && v != 0);

/// Эффекты исхода по таблице уровней баланса.
List<JEffect> effectsOf(Json eff, World w) {
  final lv = (w.balance['levels'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};
  int lvl(String table, Object? v) {
    final t = (lv[table] as Map?) ?? const {};
    final n = t['$v'.replaceFirst('-', '')];
    return n is num ? n.toInt() : 0;
  }

  int signed(String table, Object? v) => '$v'.startsWith('-') ? -lvl(table, v) : lvl(table, v);
  final out = <JEffect>[];
  if (eff['coins'] != null) out.add(JEffect('coins', value: signed('coins', eff['coins'])));
  for (final k in statKeys) {
    if (eff[k] != null) out.add(JEffect('stat', key: k, value: signed('stat', eff[k])));
  }
  final give = eff['give'];
  if (give is Map) {
    give.forEach((k, v) => out.add(JEffect('give', key: '$k', value: v is num ? v.toInt() : 1)));
  }
  final remove = eff['remove'];
  if (remove is Map) {
    remove.forEach((k, v) => out.add(JEffect('remove', key: '$k', value: v is num ? v.toInt() : 1)));
  }
  if (eff['delay'] != null) out.add(JEffect('delay', value: lvl('delayHours', eff['delay'])));
  if (eff['detour'] != null) out.add(JEffect('detour', value: lvl('detourKm', eff['detour'])));
  if (eff['shortcut'] != null) out.add(JEffect('shortcut', value: lvl('shortcutKm', eff['shortcut'])));
  if (_on(eff['death'])) out.add(const JEffect('death'));
  return out;
}

JTone? _toneOf(Json eff, List<JEffect> fx) {
  final pos = fx.any((f) => !f.negative && f.type != 'death') || eff['quest_start'] != null;
  final neg = fx.any((f) => f.negative) || _on(eff['bonus_reset']);
  if (pos && neg) return JTone.mixed;
  if (pos) return JTone.good;
  if (neg) return JTone.bad;
  return null;
}

/// Собирает ленту журнала. [today] — день пути сегодня (AppController.journeyDay).
JournalView buildJournalView(GameContent content, HeroState hero, int today) {
  final w = content.world;
  final start = DateTime.parse(hero.startDay);
  final s0 = DateTime.utc(start.year, start.month, start.day);
  int dayOf(int t) {
    final d = DateTime.fromMillisecondsSinceEpoch(t);
    return math.max(1, DateTime.utc(d.year, d.month, d.day).difference(s0).inDays + 1);
  }

  final randomIds = {for (final e in w.randoms) '${e['id']}'};
  final rows = <JRow>[];

  for (var i = 0; i < hero.journal.length; i++) {
    final e = hero.journal[i];
    if (e.kind == 'zone_fallback') continue;
    final d = e.data;
    final p = d['pos'];
    final km = p is num ? p.toDouble() / 1000.0 : null;
    Json? ev;
    if (e.kind == 'event') ev = w.eventsById['${d['event'] ?? ''}'];
    String? zone = p is num ? w.zoneAt(p.toDouble()) : null;
    if (zone == null && ev != null) {
      final z = content.eventZone(ev);
      if (z.isNotEmpty) zone = z;
    }
    final quest = e.kind == 'event' ? (d['quest'] as String?) : null;
    JKind kind;
    switch (e.kind) {
      case 'event':
        if (ev != null && content.eventCreature(ev) != null) {
          kind = JKind.spirit;
        } else if (quest != null) {
          kind = JKind.quest;
        } else if (randomIds.contains('${d['event']}')) {
          kind = JKind.random;
        } else {
          kind = JKind.story;
        }
      case 'death':
        kind = JKind.death;
      case 'place':
      case 'camp':
        kind = JKind.camp;
      case 'quest_done':
        kind = JKind.quest;
      default:
        kind = _itemKinds.contains(e.kind) ? JKind.item : JKind.story;
    }
    final nx = i + 1 < hero.journal.length ? hero.journal[i + 1] : null;
    final after = (e.kind == 'death' || e.kind == 'quest_done') && nx != null && nx.kind == 'event' && nx.t == e.t;
    final r = JRow(
        kind: kind, t: e.t, day: dayOf(e.t), entry: e, km: km, zone: zone, order: i, seq: after ? i + 1.5 : i.toDouble());
    if (e.kind == 'event') {
      r.eventId = '${d['event'] ?? ''}';
      r.choice = d['choice'] as String?;
      r.outcome = '${d['outcome'] ?? ''}';
      r.quest = quest;
      final st = d['step'];
      r.step = st is num ? st.toInt() : null;
      final choices = ev == null ? <Json>[] : _maps(ev['choices']);
      final cid = d['cid'] as String?;
      Json? ch;
      for (final c in choices) {
        if ((cid != null && c['id'] == cid) || (cid == null && c['text'] == r.choice)) {
          ch = c;
          break;
        }
      }
      if (ch != null) {
        final chosen = ch;
        r.choice = '${chosen['text'] ?? r.choice ?? ''}';
        r.alts = [
          for (final c in choices)
            if (!identical(c, chosen)) '${c['text'] ?? ''}',
        ];
        final outs = _maps(chosen['outcomes']);
        Json? out;
        final oi = d['oi'];
        if (oi is num && oi.toInt() >= 0 && oi.toInt() < outs.length) {
          out = outs[oi.toInt()];
        } else {
          for (final o in outs) {
            if (o['text'] == r.outcome) {
              out = o;
              break;
            }
          }
          if (out == null && outs.length == 1) out = outs.first;
        }
        if (out != null) {
          final eff = (out['effects'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
          r.effects = effectsOf(eff, w);
          r.tone = _toneOf(eff, r.effects);
          final opened = <JOpen>[];
          final qs = eff['quest_start'];
          if (qs is String && w.quests.containsKey(qs)) opened.add(JOpen('quest', qs));
          r.opened = opened;
        }
      }
      final q = quest == null ? null : w.quests[quest];
      final step = r.step;
      if (q != null && step != null && step + 1 < ((q['steps'] as List?) ?? const []).length) {
        r.opened = [...r.opened, JOpen('step', quest!, step + 2)];
      }
    } else if (e.kind == 'quest_done') {
      r.quest = d['quest'] as String?;
    }
    rows.add(r);
  }

  // Утренние мысли: по одной на день пути, в начале дня.
  for (var day = 1; day <= today; day++) {
    final t = DateTime(start.year, start.month, start.day + day - 1).millisecondsSinceEpoch;
    rows.add(JRow(kind: JKind.thought, t: t, day: day, order: -1, seq: -1)..thoughtDay = day);
  }
  rows.sort((a, b) {
    final dd = a.day.compareTo(b.day);
    if (dd != 0) return dd;
    final ta = a.kind == JKind.thought ? 0 : 1;
    final tb = b.kind == JKind.thought ? 0 : 1;
    if (ta != tb) return ta.compareTo(tb);
    final tt = a.t.compareTo(b.t);
    return tt != 0 ? tt : a.seq.compareTo(b.seq);
  });
  for (var i = 0; i < rows.length; i++) {
    rows[i].id = i;
  }

  // Цепочки: шаги квеста + событие, которое его начало; события духа — к линии этого духа; смерть → откат.
  final chains = <String, JChain>{};
  JChain questChain(String qid) => chains.putIfAbsent('q:$qid', () {
        final q = w.quests[qid];
        final folk = q?['creature'] != null || q?['kind'] == 'folklore';
        return JChain('q:$qid', folk ? JChainKind.spirit : JChainKind.quest,
            quest: qid, creature: q?['creature'] as String?);
      });
  void put(JRow r, JChain c) {
    r.chain = c.id;
    c.rows.add(r.id);
  }

  for (final r in rows) {
    final q = r.quest;
    if (q != null && w.quests.containsKey(q)) put(r, questChain(q));
  }
  for (final r in rows) {
    if (r.chain != null) continue;
    for (final o in r.opened) {
      if (o.type == 'quest') {
        put(r, questChain(o.quest));
        break;
      }
    }
  }
  for (final r in rows) {
    if (r.chain != null || r.kind != JKind.spirit) continue;
    final ev = w.eventsById[r.eventId];
    final cr = ev == null ? null : content.eventCreature(ev);
    if (cr == null) continue;
    String? qid;
    for (final q in w.quests.values) {
      if (q['creature'] == cr) {
        qid = q['id'] as String?;
        break;
      }
    }
    if (qid != null) {
      put(r, questChain(qid));
    } else {
      put(r, chains.putIfAbsent('c:$cr', () => JChain('c:$cr', JChainKind.spirit, creature: cr)));
    }
  }
  for (final r in rows) {
    if (r.kind != JKind.death) continue;
    // Движок пишет смерть до записи события, которое к ней привело (то же время).
    JRow? killer;
    for (final k in [r.id + 1, r.id - 1]) {
      if (k >= 0 && k < rows.length && rows[k].entry?.kind == 'event' && rows[k].t == r.t) {
        killer = rows[k];
        break;
      }
    }
    if (killer == null) continue;
    final kk = killer.km;
    final dk = r.km;
    if (kk != null && dk != null && kk - dk > 0.05) {
      r.effects = [JEffect('rollback', value: ((kk - dk) * 10.0).roundToDouble() / 10.0)];
    }
    final kc = chains[killer.chain];
    if (kc != null) {
      put(r, kc);
    } else {
      final c = JChain('d:${r.id}', JChainKind.death);
      chains[c.id] = c;
      put(killer, c);
      put(r, c);
    }
  }
  for (final c in chains.values) {
    c.rows.sort();
    final qid = c.quest;
    if (qid == null) continue;
    c.done = c.rows.any((i) => rows[i].entry?.kind == 'quest_done');
    final qp = hero.quests[qid];
    final steps = _maps(w.quests[qid]?['steps']);
    if (qp != null && qp.step < steps.length) {
      c.nextStep = qp.step + 1;
      final at = qp.startPos + toD(steps[qp.step]['at_km']) * 1000.0;
      c.nextKm = math.max(0.0, (at - hero.pos) / 1000.0);
    }
  }

  // Дни: км от → до и шаги.
  final days = <JDay>[];
  for (final r in rows) {
    if (days.isEmpty || days.last.day != r.day) {
      final date = DateTime(start.year, start.month, start.day + r.day - 1);
      days.add(JDay(r.day, date)..steps = hero.daySteps[_dayKey(date)] ?? 0);
    }
    final d = days.last;
    d.rows.add(r.id);
    final km = r.km;
    if (km != null) {
      final from = d.kmFrom;
      final to = d.kmTo;
      d.kmFrom = from == null ? km : math.min(from, km);
      d.kmTo = to == null ? km : math.max(to, km);
    }
  }
  return JournalView(rows: rows, chains: chains, days: days, today: today);
}

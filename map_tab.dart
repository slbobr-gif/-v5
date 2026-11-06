// Вкладка «Карта» (вариант 5 «Глава крупно + мини-карта + слои»): шапка-переключатель глав,
// карта главы крупно, мини-карта всего пути, слои-фильтры (рынки, духи, ночёвки, события)
// и карточка по тапу на место или значок. Стиль — docs/v5/04-art-style.md → «Карта».

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../data/content_repository.dart';
import '../../engine/engine.dart';
import '../../engine/state.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/chapter_map.dart';
import '../widgets/common.dart';
import '../widgets/route_ribbon.dart' show ribbonKm, shortPlaceName;

final _num = NumberFormat.decimalPattern('ru');
final _mult = NumberFormat('0.##', 'ru');

/// Ночь на карте: вечером/ночью темнее (белые ночи глав 3–4 — слегка).
double mapNight(Engine eng, int ch) {
  final phase = eng.dayPhase();
  return phase >= 0.75 ? (ch == 3 || ch == 4 ? 0.25 : 0.8) : 0.0;
}

/// Слои карты по порядку чипов.
const mapLayerIds = <String>['markets', 'spirits', 'nights', 'events'];
const _defaultLayers = <String>['markets', 'spirits', 'nights'];

/// Существа, для которых есть медальон assets/art/creatures/<id>.svg.
const _creatureArt = <String>{
  'leshy',
  'domovoy',
  'bannik',
  'poludnitsa',
  'vodyanoy',
  'kikimora',
  'rusalka',
  'baba_yaga',
  'ovinnik',
};

const _halo = <Shadow>[Shadow(color: Palette.ink, blurRadius: 3), Shadow(color: Palette.ink, blurRadius: 2)];
const _textSoft = Color(0xFFCFC8B3);
const _greyLine = Color(0xFF56677A);
const _disabled = Color(0xFF3B4A5B);

// ---------------------------------------------------------------- прогноз ночёвок

/// Ночёвки по среднему темпу игрока: прошлые — назад от героя по шагам прошлых дней,
/// будущие — вперёд с шагом «км в день». Мало данных (меньше двух полных дней) — длина дня из баланса.
class MapForecast {
  MapForecast._(this.perDayM, this.fallback, this.today, this.ahead, this.past);

  final double perDayM;
  final bool fallback;

  /// Сегодняшний день пути.
  final int today;

  /// Позиции будущих ночёвок (м), по порядку: первая — сегодняшняя.
  final List<double> ahead;

  /// Прошлые ночёвки: (позиция, день пути).
  final List<(double, int)> past;

  /// День прибытия в точку [pos] по прогнозу.
  int dayAt(double pos) {
    var n = 0;
    for (final x in ahead) {
      if (x < pos - 1) {
        n++;
      } else {
        break;
      }
    }
    return today + n;
  }

  static MapForecast build(Engine eng, {required String todayKey, required int journeyDay}) {
    final mps = eng.gameMetersPerStep();
    final steps = eng.s.daySteps;
    final days = steps.keys.where((k) => k != todayKey).toList()..sort();
    final window = days.length > 7 ? days.sublist(days.length - 7) : days;
    var sum = 0;
    for (final k in window) {
      sum += steps[k] ?? 0;
    }
    final avg = window.isEmpty ? 0.0 : sum / window.length * mps;
    final mv = eng.b['movement'];
    final dayLenKm = mv is Map ? toD(mv['dayLengthKm']) : 0.0;
    final dayLen = dayLenKm > 0 ? dayLenKm * 1000.0 : 26000.0;
    final fallback = window.length < 2 || avg < 2000;
    final perDay = fallback ? dayLen : avg;
    final todayM = (steps[todayKey] ?? 0) * mps;
    final pos = eng.s.pos;

    final ahead = <double>[];
    var x = pos + math.max(0.0, perDay - todayM);
    while (x < eng.w.length && ahead.length < 500) {
      ahead.add(x);
      x += perDay;
    }

    final past = <(double, int)>[];
    final todayDate = DateTime.tryParse(todayKey);
    var cur = pos - todayM;
    for (final k in days.reversed) {
      if (cur <= 0) break;
      final d = DateTime.tryParse(k);
      if (todayDate == null || d == null) break;
      final day = journeyDay - (todayDate.difference(d).inHours / 24).round();
      if (day < 1) break;
      past.add((cur, day));
      cur -= (steps[k] ?? 0) * mps;
    }
    return MapForecast._(perDay, fallback, journeyDay, ahead, past);
  }
}

// ---------------------------------------------------------------- данные значков

enum _K { place, market, spirit, night, event }

class _Info {
  const _Info(this.kind, this.pos, {this.place, this.creature, this.day = 0, this.past = false, this.quest = false});
  final _K kind;
  final double pos;
  final Json? place;
  final String? creature;
  final int day;
  final bool past;
  final bool quest;
}

/// Сторона подписи: нормаль к пути, смотрящая вправо (подписи справа, значки слоёв — слева).
Offset _labelSide(RouteLine line, double pos) {
  final d = line.dirAt(pos);
  final n = Offset(d.dy, -d.dx);
  return n.dx >= 0 ? n : -n;
}

// ---------------------------------------------------------------- вкладка

class MapTab extends ConsumerStatefulWidget {
  const MapTab({super.key});

  @override
  ConsumerState<MapTab> createState() => _MapTabState();
}

class _MapTabState extends ConsumerState<MapTab> {
  /// Открытая глава (null — глава героя).
  int? _viewCh;
  String? _sel;
  int _fit = 0;
  int _hero = 0;
  bool _heroStart = false;

  bool _playable(World w, int ch) => w.chapterById(ch)['playable'] != false;

  void _go(World w, int ch, AppLocalizations l) {
    if (ch < 1 || ch > w.chapters.length) return;
    if (!_playable(w, ch)) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.mapChapterLockedHint)));
      return;
    }
    setState(() {
      _viewCh = ch;
      _sel = null;
      _heroStart = false;
    });
  }

  void _toggleLayer(String id, Set<String> cur) {
    final next = <String>{...cur};
    if (!next.remove(id)) next.add(id);
    ref.read(uiFlagsProvider.notifier).update((f) => f.mapLayers = [
          for (final x in mapLayerIds)
            if (next.contains(x)) x,
        ]);
    setState(() => _sel = null);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final content = m.content;
    final hero = m.hero;
    if (content == null || hero == null) return const Scaffold();
    final flags = ref.watch(uiFlagsProvider);
    final layers = (flags.mapLayers ?? _defaultLayers).toSet();
    final c = ref.read(appProvider.notifier);
    final w = content.world;
    final eng = Engine(w, hero);
    final heroCh = w.chapterAt(hero.pos);
    final ch = _viewCh ?? heroCh;
    final total = w.chapters.length;
    final day = c.journeyDay();
    final fc = MapForecast.build(eng, todayKey: c.today, journeyDay: day);

    final chapter = w.chapterById(ch);
    final start = w.chapterStartPos(ch);
    final end = w.chapterEndPos(ch);
    final fromName = shortPlaceName('${w.placeById['${chapter['from']}']?['name'] ?? ''}');
    final toName = shortPlaceName('${w.placeById['${chapter['to']}']?['name'] ?? ''}');
    final route = l.mapChapterRoute(fromName, toName);
    final doneKm = _num.format((hero.pos - start).clamp(0.0, math.max(0.0, end - start)) / 1000 ~/ 1);
    final lenKm = _num.format(((end - start) / 1000).round());
    final kicker = ch == heroCh
        ? l.mapChapterOf(ch, total, day)
        : (ch < heroCh ? l.mapChapterOfDone(ch, total) : l.mapChapterOfAhead(ch, total, fc.dayAt(start)));
    final nextState = ch >= total ? 0 : (_playable(w, ch + 1) ? 1 : 2);

    final (marks, info, nextId) = _marks(content, hero, ch, layers, fc);
    final heroKm = _num.format((hero.pos / 1000).round());
    final allKm = _num.format((w.length / 1000).round());

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            Positioned.fill(
              child: ChapterMapView(
                key: ValueKey<int>(ch),
                content: content,
                ch: ch,
                heroPos: hero.pos,
                marks: marks,
                selectedId: _sel,
                onSelect: (id) {
                  if (id != _sel) setState(() => _sel = id);
                },
                popupBuilder: (ctx, id) => _popup(ctx, l, content, hero, fc, info[id], nextId),
                night: mapNight(eng, ch),
                fitTick: _fit,
                heroTick: _hero,
                focusHeroOnStart: _heroStart,
                topInset: 72,
                bottomInset: 60,
              ),
            ),
            const Positioned(
              left: 0,
              right: 0,
              top: 0,
              height: 84,
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Palette.ink, Color(0x000E1621)],
                      stops: [0.25, 1.0],
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              top: 8,
              left: 12,
              right: 12,
              child: _ChapterSwitcher(
                kicker: kicker,
                route: route,
                done: doneKm,
                total: lenKm,
                a11y: l.mapChapterA11y(ch, route, doneKm, lenKm),
                canPrev: ch > 1,
                nextState: nextState,
                onPrev: () => _go(w, ch - 1, l),
                onNext: () => _go(w, ch + 1, l),
              ),
            ),
            Positioned(
              left: 10,
              bottom: 56,
              child: MiniRouteMap(
                content: content,
                viewCh: ch,
                heroPos: hero.pos,
                label: l.mapMiniKm(heroKm, allKm),
                semanticsLabel: l.mapMiniA11y(heroKm, allKm),
                onPick: (pick) {
                  if (pick != ch) _go(w, pick, l);
                },
              ),
            ),
            Positioned(
              right: 12,
              bottom: 58,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _RoundButton(
                    icon: Icons.crop_free,
                    tooltip: l.mapWholeChapter,
                    onTap: () => setState(() {
                      _sel = null;
                      _fit++;
                    }),
                  ),
                  const SizedBox(height: 10),
                  _RoundButton(
                    icon: Icons.my_location,
                    tooltip: l.mapRecenter,
                    onTap: () => setState(() {
                      _sel = null;
                      if (ch != heroCh) {
                        _viewCh = heroCh;
                        _heroStart = true;
                      } else {
                        _hero++;
                      }
                    }),
                  ),
                ],
              ),
            ),
            if (content.map.attribution.isNotEmpty)
              Positioned(
                left: 92,
                right: 66,
                bottom: 52,
                child: IgnorePointer(
                  child: Text(
                    content.map.attribution,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 8.5, color: Palette.parchmentDim, shadows: _halo),
                  ),
                ),
              ),
            Positioned(
              left: 10,
              right: 10,
              bottom: 10,
              child: _LayerChips(
                on: layers,
                labels: [l.mapLayerMarkets, l.mapLayerSpirits, l.mapLayerNights, l.mapLayerEvents],
                onToggle: (id) => _toggleLayer(id, layers),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Значки главы и данные для карточек. Третье значение — id следующего места впереди.
  (List<MapMark>, Map<String, _Info>, String?) _marks(
    GameContent content,
    HeroState hero,
    int ch,
    Set<String> layers,
    MapForecast fc,
  ) {
    final w = content.world;
    final line = RouteLine.of(content);
    final start = w.chapterStartPos(ch);
    final end = w.chapterEndPos(ch);
    bool inCh(double p) => p >= start - 1 && p <= end + 1;
    final marks = <MapMark>[];
    final info = <String, _Info>{};
    final labels = <MapMark>[];
    String? nextId;

    // места, подписи и рынки
    for (final p in w.places) {
      final pid = '${p['id']}';
      final at = w.posOf[pid];
      if (at == null || !inCh(at)) continue;
      final virtual = p['virtual'] == true;
      final pt = line.at(at);
      final side = _labelSide(line, at);
      final reached = at <= hero.pos + 1;
      if (!virtual) {
        if (!reached && nextId == null) nextId = pid;
        final kind = p['kind'];
        final big = kind == 'city' || kind == 'start' || kind == 'finish';
        labels.add(MapMark(
          id: 'lbl:$pid',
          at: pt,
          shift: side * (big ? 11.0 : 9.0),
          align: side.dx >= 0 ? Alignment.centerLeft : Alignment.centerRight,
          child: _PlaceLabel(text: shortPlaceName('${p['name']}'), big: big, reached: reached),
        ));
        final id = 'place:$pid';
        marks.add(MapMark(id: id, at: pt, tappable: true, child: const SizedBox(width: 1, height: 1)));
        info[id] = _Info(_K.place, at, place: p);
      }
      if (layers.contains('markets') && p['market'] is String && at >= hero.pos - 1) {
        final id = 'market:$pid';
        marks.add(MapMark(
          id: id,
          at: pt,
          shift: -side * (virtual ? 12.0 : 19.0),
          tappable: true,
          child: _MarketBadge(lit: !virtual, selected: _sel == id),
        ));
        info[id] = _Info(_K.market, at, place: p);
      }
    }

    // духи и события из авторских якорных событий
    for (final a in w.anchored) {
      if (!inCh(a.pos)) continue;
      final eid = '${a.event['id']}';
      final cr = content.eventCreature(a.event);
      final passed = a.pos <= hero.pos + 1;
      final seen = hero.seen.contains(eid);
      final side = _labelSide(line, a.pos);
      if (cr != null) {
        if (!layers.contains('spirits') || (passed && !seen)) continue;
        final known = passed && seen;
        final id = 'spirit:$eid';
        marks.add(MapMark(
          id: id,
          at: line.at(a.pos),
          shift: -side * 30,
          leader: true,
          tappable: true,
          child: _SpiritMedal(creature: known ? cr : null, selected: _sel == id),
        ));
        info[id] = _Info(_K.spirit, a.pos, creature: known ? cr : null, past: known);
      } else {
        if (!layers.contains('events') || passed || seen) continue;
        final id = 'event:$eid';
        marks.add(MapMark(
          id: id,
          at: line.at(a.pos),
          shift: side * 26,
          leader: true,
          tappable: true,
          child: _EventBadge(selected: _sel == id),
        ));
        info[id] = _Info(_K.event, a.pos);
      }
    }

    // следующие шаги начатых историй: дух — «?» в слое духов, остальное — в слое событий
    hero.quests.forEach((qid, q) {
      final quest = w.quests[qid];
      if (quest == null) return;
      final steps = (quest['steps'] as List?) ?? const [];
      if (q.step < 0 || q.step >= steps.length) return;
      final st = steps[q.step];
      if (st is! Map) return;
      final qp = q.startPos + toD(st['at_km']) * 1000.0;
      if (qp <= hero.pos + 1 || !inCh(qp)) return;
      final cr = quest['creature'];
      final side = _labelSide(line, qp);
      if (cr is String && cr.isNotEmpty) {
        if (!layers.contains('spirits')) return;
        final id = 'qspirit:$qid';
        marks.add(MapMark(
          id: id,
          at: line.at(qp),
          shift: -side * 30,
          leader: true,
          tappable: true,
          child: _SpiritMedal(creature: null, selected: _sel == id),
        ));
        info[id] = _Info(_K.spirit, qp, quest: true);
      } else {
        if (!layers.contains('events')) return;
        final id = 'qevent:$qid';
        marks.add(MapMark(
          id: id,
          at: line.at(qp),
          shift: side * 26,
          leader: true,
          tappable: true,
          child: _EventBadge(selected: _sel == id),
        ));
        info[id] = _Info(_K.event, qp, quest: true);
      }
    });

    // ночёвки: прошлые — сплошной круг, прогноз — приглушённый
    if (layers.contains('nights')) {
      for (final (np, d) in fc.past) {
        if (!inCh(np)) continue;
        final id = 'night:p$d';
        marks.add(MapMark(id: id, at: line.at(np), tappable: true, child: _NightBadge(past: true, selected: _sel == id)));
        info[id] = _Info(_K.night, np, day: d, past: true);
      }
      for (var k = 0; k < fc.ahead.length; k++) {
        final np = fc.ahead[k];
        if (np > end + 1) break;
        if (!inCh(np)) continue;
        final d = fc.today + k;
        final id = 'night:f$d';
        marks.add(MapMark(id: id, at: line.at(np), tappable: true, child: _NightBadge(past: false, selected: _sel == id)));
        info[id] = _Info(_K.night, np, day: d);
      }
    }

    // подписи — под значками (раньше в списке, значит ниже при рисовании)
    return (<MapMark>[...labels, ...marks], info, nextId);
  }

  // ---------------------------------------------------------------- карточка по тапу

  Widget? _popup(
    BuildContext context,
    AppLocalizations l,
    GameContent content,
    HeroState hero,
    MapForecast fc,
    _Info? it,
    String? nextId,
  ) {
    if (it == null) return null;
    final ahead = it.pos > hero.pos + 1;
    final km = ribbonKm(math.max(0.0, it.pos - hero.pos) / 1000);
    final inKm = ahead ? l.mapInKm(km) : null;
    final arrive = ahead ? l.mapArriveDay(fc.dayAt(it.pos)) : null;
    switch (it.kind) {
      case _K.place:
      case _K.market:
        final p = it.place ?? const <String, dynamic>{};
        final pid = '${p['id']}';
        final virtual = p['virtual'] == true;
        final market = p['market'] is String ? p['market'] as String : null;
        final kindLabel = (it.kind == _K.market && market != null)
            ? _marketName(l, virtual ? 'roadside' : market)
            : _kindName(l, virtual ? 'roadside' : '${p['kind']}');
        final String status;
        if (!ahead) {
          status = (it.pos - hero.pos).abs() < 50 ? l.mapStatusHere : l.mapStatusPassed;
        } else {
          status = pid == nextId ? l.mapStatusNext : '';
        }
        final chips = <String>[];
        if (market != null) {
          final goods = _marketGoods(content, market);
          if (goods.isNotEmpty) chips.add(goods.take(5).join(' · '));
          final regional = content.regionalItems(pid).map(content.itemName).toList();
          if (regional.isNotEmpty) chips.add(l.mapRegionalGoods(regional.join(', ')));
          final mult = _priceMult(content, market);
          if (mult != null && mult != 1.0) chips.add(l.mapPriceMult(_mult.format(mult)));
        }
        return _PopBody(
          icon: it.kind == _K.market
              ? const _MarketBadge(lit: true, selected: true, size: 30)
              : _PlaceDot(reached: !ahead),
          title: '${p['name']}',
          sub: [kindLabel, status].where((s) => s.isNotEmpty).join(' · '),
          accent: inKm,
          meta: arrive,
          chips: chips,
        );
      case _K.spirit:
        final cr = it.creature;
        if (cr != null) {
          final c = content.creatures[cr];
          final habitat = '${c?['habitat'] ?? ''}';
          return _PopBody(
            icon: _SpiritMedal(creature: cr, selected: true, size: 30),
            title: '${c?['name'] ?? cr}',
            sub: l.mapSpiritMet,
            body: habitat.isEmpty ? null : l.mapSpiritHabitat(habitat),
          );
        }
        return _PopBody(
          icon: const _SpiritMedal(creature: null, selected: true, size: 30),
          title: l.mapSpiritUnknown,
          sub: it.quest ? l.mapQuestHint : null,
          accent: inKm,
          meta: arrive,
          body: l.mapSpiritUnknownBody,
        );
      case _K.night:
        final perDay = ribbonKm(fc.perDayM / 1000);
        return _PopBody(
          icon: _NightBadge(past: it.past, selected: true, size: 30),
          title: l.mapNightTitle(it.day),
          accent: inKm,
          body: it.past ? l.mapNightPast : (fc.fallback ? l.mapNightFallback(perDay) : l.mapNightFuture(perDay)),
        );
      case _K.event:
        return _PopBody(
          icon: const _EventBadge(selected: true, size: 30),
          title: it.quest ? l.mapQuestHint : l.mapEventTitle,
          accent: inKm,
          meta: arrive,
          body: l.mapEventBody,
        );
    }
  }
}

String _kindName(AppLocalizations l, String kind) => switch (kind) {
      'start' => l.mapKindStart,
      'city' => l.mapKindCity,
      'town' => l.mapKindTown,
      'village' => l.mapKindVillage,
      'finish' => l.mapKindFinish,
      'roadside' => l.mapKindRoadside,
      _ => '',
    };

String _marketName(AppLocalizations l, String market) => switch (market) {
      'city' => l.mapMarketCity,
      'town' => l.mapMarketTown,
      'village' => l.mapMarketVillage,
      _ => l.mapMarketRoadside,
    };

Map? _marketSpec(GameContent content, String market) {
  final eco = content.world.balance['economy'];
  final markets = eco is Map ? eco['markets'] : null;
  final spec = markets is Map ? markets[market] : null;
  return spec is Map ? spec : null;
}

/// Что продают на рынке этого вида (balance.json → economy.markets.<вид>.items), именами предметов.
List<String> _marketGoods(GameContent content, String market) {
  final items = _marketSpec(content, market)?['items'];
  if (items is! List) return const [];
  return [for (final i in items) content.itemName('$i')];
}

double? _priceMult(GameContent content, String market) {
  final v = _marketSpec(content, market)?['priceMult'];
  return v is num ? v.toDouble() : null;
}

// ---------------------------------------------------------------- шапка-переключатель глав

class _ChapterSwitcher extends StatelessWidget {
  const _ChapterSwitcher({
    required this.kicker,
    required this.route,
    required this.done,
    required this.total,
    required this.a11y,
    required this.canPrev,
    required this.nextState,
    required this.onPrev,
    required this.onNext,
  });

  final String kicker;
  final String route;
  final String done;
  final String total;
  final String a11y;
  final bool canPrev;

  /// 0 — следующей главы нет, 1 — открыта, 2 — закрыта (серая, с замком).
  final int nextState;
  final VoidCallback onPrev;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 2),
      decoration: BoxDecoration(
        color: const Color(0xF216222F),
        borderRadius: BorderRadius.circular(Gap.radius),
        border: Border.all(color: Palette.inkHigh),
        boxShadow: const [BoxShadow(color: Color(0x59000000), blurRadius: 16, offset: Offset(0, 6))],
      ),
      child: MediaQuery.withClampedTextScaling(
        maxScaleFactor: 1.2,
        child: Row(
          children: [
            _Chevron(
              icon: Icons.chevron_left,
              tooltip: l.mapPrevChapter,
              enabled: canPrev,
              locked: false,
              onTap: canPrev ? onPrev : null,
            ),
            Expanded(
              child: Semantics(
                label: a11y,
                excludeSemantics: true,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      kicker,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: Palette.parchmentDim, height: 1.15),
                    ),
                    Text(
                      route,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w700, height: 1.25),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 6),
            ExcludeSemantics(
              child: Text.rich(
                TextSpan(children: [
                  TextSpan(
                    text: done,
                    style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                  const TextSpan(text: ' '),
                  TextSpan(text: l.mapKmOf(total)),
                ]),
                style: const TextStyle(fontSize: 12, color: Palette.parchmentDim),
              ),
            ),
            _Chevron(
              icon: Icons.chevron_right,
              tooltip: nextState == 2 ? l.mapChapterLockedHint : l.mapNextChapter,
              enabled: nextState == 1,
              locked: nextState == 2,
              onTap: nextState == 0 ? null : onNext,
            ),
          ],
        ),
      ),
    );
  }
}

class _Chevron extends StatelessWidget {
  const _Chevron({
    required this.icon,
    required this.tooltip,
    required this.enabled,
    required this.locked,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final bool enabled;
  final bool locked;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = enabled ? Palette.accent : _disabled;
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: SizedBox(
          width: 40,
          height: 48,
          child: locked
              ? const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.lock_outline, size: 15, color: _disabled),
                    Icon(Icons.chevron_right, size: 20, color: _disabled),
                  ],
                )
              : Icon(icon, size: 26, color: color),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- круглые кнопки и чипы слоёв

/// Круглая кнопка карты (как .rb в макете): тёмное стекло, рамка #1F3043, бирюзовый значок.
class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, required this.tooltip, required this.onTap});

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [BoxShadow(color: Color(0x66000000), blurRadius: 16, offset: Offset(0, 6))],
        ),
        child: Material(
          color: const Color(0xF016222F),
          shape: const CircleBorder(side: BorderSide(color: Palette.inkHigh)),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: SizedBox(width: 44, height: 44, child: Icon(icon, size: 21, color: Palette.accent)),
          ),
        ),
      ),
    );
  }
}

const _layerIcons = <IconData>[
  Icons.shopping_basket_outlined,
  Icons.local_fire_department_outlined,
  Icons.nightlight_outlined,
  Icons.help_outline,
];

class _LayerChips extends StatelessWidget {
  const _LayerChips({required this.on, required this.labels, required this.onToggle});

  final Set<String> on;
  final List<String> labels;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return MediaQuery.withClampedTextScaling(
      maxScaleFactor: 1.15,
      child: Row(
        children: [
          for (var i = 0; i < mapLayerIds.length && i < labels.length; i++) ...[
            if (i > 0) const SizedBox(width: 5),
            Expanded(
              child: _LayerChip(
                icon: _layerIcons[i],
                label: labels[i],
                on: on.contains(mapLayerIds[i]),
                onTap: () => onToggle(mapLayerIds[i]),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _LayerChip extends StatelessWidget {
  const _LayerChip({required this.icon, required this.label, required this.on, required this.onTap});

  final IconData icon;
  final String label;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      toggled: on,
      label: label,
      excludeSemantics: true,
      child: Material(
        color: on ? const Color(0x213FD6CC) : const Color(0xF216222F),
        shape: StadiumBorder(
          side: BorderSide(color: on ? Palette.accent : Palette.inkHigh, width: on ? 1.5 : 1),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: SizedBox(
            height: 36,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(icon, size: 15, color: on ? Palette.accent : const Color(0xFF7F8B98)),
                    const SizedBox(width: 4),
                    Text(
                      label,
                      maxLines: 1,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: on ? Palette.parchment : Palette.parchmentDim,
                        fontWeight: on ? FontWeight.w700 : FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- значки слоёв

class _PlaceLabel extends StatelessWidget {
  const _PlaceLabel({required this.text, required this.big, required this.reached});

  final String text;
  final bool big;
  final bool reached;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      maxLines: 1,
      softWrap: false,
      textScaler: TextScaler.noScaling,
      style: TextStyle(
        fontSize: big ? 12 : 10.5,
        fontWeight: big ? FontWeight.w700 : FontWeight.w400,
        color: reached ? Palette.parchment : const Color(0xFFB5BFC9),
        shadows: _halo,
      ),
    );
  }
}

class _MarketBadge extends StatelessWidget {
  const _MarketBadge({required this.lit, required this.selected, this.size = 20});

  final bool lit;
  final bool selected;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Palette.inkRaised,
        borderRadius: BorderRadius.circular(size * 0.32),
        border: Border.all(color: selected ? Palette.accent : Palette.chipLine, width: selected ? 1.8 : 1),
      ),
      child: Icon(
        Icons.shopping_basket_outlined,
        size: size * 0.66,
        color: (lit || selected) ? Palette.accent : Palette.parchmentDim,
      ),
    );
  }
}

class _QMark extends StatelessWidget {
  const _QMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 13,
      height: 13,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Palette.inkRaised,
        shape: BoxShape.circle,
        border: Border.all(color: _greyLine),
      ),
      child: const Text(
        '?',
        textScaler: TextScaler.noScaling,
        style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: _textSoft, height: 1),
      ),
    );
  }
}

/// Медальон духа: встреченный — его портрет, впереди — огонёк и «?» (без имени и картинки).
class _SpiritMedal extends StatelessWidget {
  const _SpiritMedal({required this.creature, required this.selected, this.size = 26});

  final String? creature;
  final bool selected;
  final double size;

  @override
  Widget build(BuildContext context) {
    final cr = creature;
    final known = cr != null;
    final Widget face = (cr != null && _creatureArt.contains(cr))
        ? ClipOval(child: Art('assets/art/creatures/$cr.svg', width: size, height: size, fit: BoxFit.cover))
        : Icon(Icons.local_fire_department_outlined, size: size * 0.55, color: const Color(0xFF8696A8));
    return SizedBox(
      width: size + 6,
      height: size + 6,
      child: Stack(
        clipBehavior: Clip.none,
        alignment: Alignment.center,
        children: [
          Container(
            width: size,
            height: size,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: known ? const Color(0xFF1D2F40) : const Color(0xFF141E2A),
              border: Border.all(
                color: (selected || known) ? Palette.accent : _greyLine,
                width: selected ? 2 : 1.3,
              ),
              boxShadow: const [BoxShadow(color: Palette.lead, spreadRadius: 2)],
            ),
            child: face,
          ),
          if (!known) const Positioned(right: -1, top: -1, child: _QMark()),
        ],
      ),
    );
  }
}

class _NightBadge extends StatelessWidget {
  const _NightBadge({required this.past, required this.selected, this.size = 15});

  final bool past;
  final bool selected;
  final double size;

  @override
  Widget build(BuildContext context) {
    final line = selected ? Palette.accent : (past ? _textSoft : const Color(0xFF7F8B98));
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Palette.ink,
        border: Border.all(color: line, width: selected ? 1.8 : 1.2),
      ),
      child: Icon(
        Icons.nightlight_outlined,
        size: size * 0.62,
        color: past ? Palette.parchment : Palette.parchmentDim,
      ),
    );
  }
}

class _EventBadge extends StatelessWidget {
  const _EventBadge({required this.selected, this.size = 20});

  final bool selected;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Transform.rotate(
            angle: math.pi / 4,
            child: Container(
              width: size * 0.7,
              height: size * 0.7,
              decoration: BoxDecoration(
                color: Palette.inkRaised,
                borderRadius: BorderRadius.circular(2),
                border: Border.all(color: selected ? Palette.accent : Palette.chipLine, width: selected ? 1.6 : 1),
              ),
            ),
          ),
          Text(
            '?',
            textScaler: TextScaler.noScaling,
            style: TextStyle(
              fontSize: size * 0.48,
              fontWeight: FontWeight.w700,
              height: 1,
              color: selected ? Palette.accent : _textSoft,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceDot extends StatelessWidget {
  const _PlaceDot({required this.reached});

  final bool reached;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 30,
      height: 30,
      alignment: Alignment.center,
      child: Container(
        width: 16,
        height: 16,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: reached ? Palette.accent : const Color(0xFF1F2E40),
          border: Border.all(color: reached ? Palette.lead : Palette.parchmentDim, width: 2),
          boxShadow: const [BoxShadow(color: Palette.lead, spreadRadius: 2)],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- содержимое карточки

class _PopBody extends StatelessWidget {
  const _PopBody({
    required this.icon,
    required this.title,
    this.sub,
    this.accent,
    this.meta,
    this.body,
    this.chips = const [],
  });

  final Widget icon;
  final String title;
  final String? sub;
  final String? accent;
  final String? meta;
  final String? body;
  final List<String> chips;

  @override
  Widget build(BuildContext context) {
    final s = sub;
    final a = accent;
    final mt = meta;
    final b = body;
    return MediaQuery.withClampedTextScaling(
      maxScaleFactor: 1.3,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(width: 32, height: 32, child: Center(child: icon)),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700, height: 1.15)),
                    if (s != null && s.isNotEmpty)
                      Text(s, style: const TextStyle(fontSize: 11, color: Palette.parchmentDim, height: 1.3)),
                  ],
                ),
              ),
            ],
          ),
          if (a != null || mt != null) ...[
            const SizedBox(height: 6),
            Text.rich(
              TextSpan(children: [
                if (a != null)
                  TextSpan(text: a, style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w700)),
                if (a != null && mt != null) const TextSpan(text: ' · '),
                if (mt != null) TextSpan(text: mt),
              ]),
              style: const TextStyle(fontSize: 12, color: _textSoft),
            ),
          ],
          if (b != null) ...[
            const SizedBox(height: 6),
            Text(b, style: const TextStyle(fontSize: 11.5, color: _textSoft, height: 1.35)),
          ],
          if (chips.isNotEmpty) ...[
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: [for (final c in chips) _TChip(c)],
            ),
          ],
        ],
      ),
    );
  }
}

class _TChip extends StatelessWidget {
  const _TChip(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: Palette.chipBg,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: Palette.chipLine),
      ),
      child: Text(text, style: const TextStyle(fontSize: 10.5, color: Palette.parchment)),
    );
  }
}

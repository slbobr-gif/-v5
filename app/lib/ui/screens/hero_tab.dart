// Вкладка «Герой» (v5.3, гибрид Г1 «Витрина сверху + строка действий снизу»; эталон —
// out/Путник — Герой, варианты 2.html, карточка «Г1»). Сверху вниз: шапка «Глава N · день D / Герой»
// и монеты → три мини-показателя → «Снаряжение N/4» (стеклянные ячейки, заряды, плашка горелки) →
// дары духов отдельной строкой → «Рюкзак N/7» (сетка 4×2) → строка действий выбранной вещи с прогнозом.
// Логики здесь нет: всё считает движок (statGain, heatStatus, giftStatus, clewStatus), действия — контроллер.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/state.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/gift_button.dart';
import '../widgets/item_icon.dart';
import 'coin_shop_screen.dart';
import 'overflow_screens.dart' show OverflowRoute;

/// Светлый пергамент для мелких пояснений (как `#CFC8B3` в эталоне).
const _note = Color(0xFFCFC8B3);

/// Фон строки действий и плашки «горит».
const _panelBg = Color(0xFF132331);
const _hotBg = Color(0xFF211A1F);
const _hotLine = Color(0xFF7A4A42);

/// Пунктир пустой ячейки и её подпись.
const _emptyLine = Color(0xFF3B4F66);
const _emptyText = Color(0xFF56677A);

/// Метка «дар» (фиолетовый — цвет духов на карте).
const _giftText = Color(0xFFB9A6F0);

bool _isConsumable(World w, String id) {
  final t = w.itemType(id);
  return t == 'food' || t == 'drink';
}

/// Дар духа: у предмета есть способность (`ability`) или подсказка (`hint`).
bool _isGift(World w, String id) {
  final spec = w.itemSpec(id);
  final ab = spec['ability'];
  final hint = spec['hint'];
  return w.isGift(id) || (ab is Map && ab.isNotEmpty) || (hint is Map && hint.isNotEmpty);
}

bool _hasHint(World w, String id) {
  final hint = w.itemSpec(id)['hint'];
  return hint is Map && hint.isNotEmpty;
}

/// Заряды на бейдже: «7/10» — от заводского числа (`uses`), после пополнения — «20/20».
int _nominalUses(World w, Engine eng, String id) {
  final u = toI(w.itemSpec(id)['uses']);
  if (u <= 0) return 0;
  return math.max(u, eng.usesLeft(id));
}

String _statName(AppLocalizations l, String k) => switch (k) {
      'satiety' => l.statSatiety,
      'water' => l.statWater,
      _ => l.statWarmth,
    };

String _gainText(AppLocalizations l, String k, int v) => switch (k) {
      'satiety' => l.gearPerkSatiety(v),
      'water' => l.gearPerkWater(v),
      _ => l.gearPerkWarmth(v),
    };

String _heatText(AppLocalizations l, String r) => switch (r) {
      'heated' || 'on' => l.gearHeatOn,
      'no_gas' => l.gearHeatNoGas,
      'nothing' => l.gearHeatNothing,
      _ => l.gearHeatNoStove,
    };

String _toneText(AppLocalizations l, String tone) => switch (tone) {
      'reward' => l.gearTone_reward,
      'penalty' => l.gearTone_penalty,
      'mixed' => l.gearTone_mixed,
      'risk' => l.gearTone_risk,
      'death' => l.gearTone_death,
      _ => l.gearTone_neutral,
    };

/// Прогноз «Тепло 24 → 49 холодным, → 64 горячим. Газ 7 → 6.» — из statGain движка, heat предмета
/// и stats.max; горячий бонус — как engine._consume (прибавка heat к теплу, одна порция на заряд газа).
String _forecast(AppLocalizations l, Engine eng, World w, String id, String heat, int gasLeft) {
  final s = eng.s.stats;
  final mx = eng.maxStat;
  final heatV = w.itemValue(id, 'heat');
  final canHeat = heatV > 0 && heat == 'ready';
  final hotNow = heatV > 0 && heat == 'on';
  String? best;
  var gain = 0.0;
  for (final k in statKeys) {
    final g = eng.statGain(id, k);
    if (g > gain) {
      best = k;
      gain = g;
    }
  }
  int up(double from, double add) => math.min(mx, from + add).round();
  final w0 = s['warmth'] ?? 0.0;
  final warmGain = eng.statGain(id, 'warmth');
  final parts = <String>[];
  final k = best;
  if (k == null) {
    if (canHeat || hotNow) parts.add(l.heroForecastHotWarmth(w0.round(), up(w0, heatV)));
  } else {
    final from = s[k] ?? 0.0;
    final name = _statName(l, k);
    if (k == 'warmth' && canHeat) {
      parts.add(l.heroForecastHot(name, from.round(), up(from, gain), up(from, gain + heatV)));
    } else if (k == 'warmth' && hotNow) {
      parts.add(l.heroForecastHeated(name, from.round(), up(from, gain + heatV)));
    } else {
      parts.add(l.heroForecast(name, from.round(), up(from, gain)));
      if (canHeat || hotNow) parts.add(l.heroForecastHotWarmth(w0.round(), up(w0, warmGain + heatV)));
    }
  }
  if (canHeat && parts.isNotEmpty) parts.add(l.heroForecastGas(gasLeft, gasLeft - 1));
  return parts.join(' ');
}

/// Что выбрано: ячейка рюкзака [index] с вещью [id] или снаряжение [id].
class _Pick {
  const _Pick(this.id, {this.gear = false, this.index = 0});
  final String id;
  final bool gear;
  final int index;
}

/// Самая полезная сейчас вещь: больше всего поднимает наименьший показатель (тепло — с горелкой).
_Pick? _mostUseful(Engine eng, World w, List<String> units, String heat) {
  if (units.isEmpty) return null;
  final s = eng.s.stats;
  var low = statKeys.first;
  for (final k in statKeys) {
    if ((s[k] ?? 0.0) < (s[low] ?? 0.0)) low = k;
  }
  final heatOn = heat == 'on' || heat == 'ready';
  var bestI = 0;
  var bestScore = -1.0;
  for (var i = 0; i < units.length; i++) {
    final id = units[i];
    if (i > 0 && units[i - 1] == id) continue;
    var score = eng.statGain(id, low);
    if (low == 'warmth' && heatOn) score += w.itemValue(id, 'heat');
    if (score > bestScore) {
      bestScore = score;
      bestI = i;
    }
  }
  return _Pick(units[bestI], index: bestI);
}

class HeroTab extends ConsumerStatefulWidget {
  const HeroTab({super.key});

  @override
  ConsumerState<HeroTab> createState() => _HeroTabState();
}

class _HeroTabState extends ConsumerState<HeroTab> {
  /// Выбор игрока; null — показываем самую полезную сейчас вещь.
  _Pick? _pick;

  void _snack(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  _Pick? _resolve(HeroState hero, List<String> units, Engine eng, World w, String heat) {
    final p = _pick;
    if (p != null) {
      if (p.gear && hero.gear.contains(p.id)) return p;
      if (!p.gear && units.contains(p.id)) {
        final i = (p.index < units.length && units[p.index] == p.id) ? p.index : units.indexOf(p.id);
        return _Pick(p.id, index: i);
      }
    }
    final best = _mostUseful(eng, w, units, heat);
    if (best != null) return best;
    final plain = hero.gear.where((g) => !w.freeSlot(g)).toList();
    if (plain.isNotEmpty) return _Pick(plain.first, gear: true);
    return null;
  }

  // ------------------------------------------------ действия
  void _use(String id) {
    final l = AppLocalizations.of(context);
    if (!ref.read(appProvider.notifier).useItem(id)) _snack(l.overflowError);
  }

  void _heat() {
    final l = AppLocalizations.of(context);
    _snack(_heatText(l, ref.read(appProvider.notifier).heat()));
  }

  void _heatAndUse(String id) {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final r = c.heat();
    if (r != 'heated' && r != 'on') {
      _snack(_heatText(l, r));
      return;
    }
    if (!c.useItem(id)) _snack(l.overflowError);
  }

  void _useGift(String id) {
    final l = AppLocalizations.of(context);
    final r = ref.read(appProvider.notifier).useGift(id);
    _snack(r == 'ok' ? l.giftUsed : (giftStatusText(l, r, 0) ?? l.overflowError));
  }

  /// «Спросить» (клубок, нитка, подсказка духа): ответ держим в диалоге — в состоянии он не хранится.
  void _ask(String id) {
    final l = AppLocalizations.of(context);
    final ev = ref.read(appProvider).engine?.currentEvent();
    final r = ref.read(appProvider.notifier).askClew();
    if (r == null || ev == null) {
      _snack(l.overflowError);
      return;
    }
    final choices = ((ev['choices'] as List?) ?? const []).whereType<Map>().toList();
    showDialog<void>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        title: Text(clewAskLabel(l, id)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final ch in choices)
              Padding(
                padding: const EdgeInsets.only(bottom: Gap.s),
                child: Text('${ch['text']} · ${_toneText(l, r['${ch['id']}'] ?? '')}'),
              ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: Text(l.close)),
        ],
      ),
    );
  }

  Future<void> _confirmDrop(String id, String name) async {
    final l = AppLocalizations.of(context);
    final go = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        title: Text(l.heroDropTitle(name)),
        content: Text(l.heroDropBody),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(l.cancel)),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.overflowDrop)),
        ],
      ),
    );
    if (go != true || !mounted) return;
    if (ref.read(appProvider.notifier).dropItem(id)) {
      setState(() => _pick = null);
    } else {
      _snack(l.overflowError);
    }
  }

  void _openOverflow() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const OverflowRoute()));
  }

  // ------------------------------------------------ экран
  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final hero = m.hero;
    final content = m.content;
    if (hero == null || content == null) return const Scaffold(body: SizedBox.shrink());
    final w = content.world;
    final eng = Engine(w, hero);
    final now = DateTime.now().millisecondsSinceEpoch;
    final heat = eng.heatStatus(now);
    final hot = eng.isHeated(now);
    final gearSlots = eng.gearSlots();
    final packSlots = eng.backpackSlots();
    final bottom = systemBottom(context);

    // Ячейки рюкзака: каждая единица еды/питья — ячейка (по алфавиту id, как раньше).
    final consumables =
        hero.inv.entries.where((e) => e.value > 0 && _isConsumable(w, e.key)).map((e) => e.key).toList()..sort();
    final units = <String>[
      for (final id in consumables)
        for (var i = 0; i < (hero.inv[id] ?? 0); i++) id,
    ];
    // Дары — отдельной строкой: ячеек снаряжения они не занимают (V5-43), в ячейках — только обычное снаряжение.
    final slotGear = hero.gear.where((g) => !w.freeSlot(g)).toList();
    // Рюкзак (V5-56) ячейку снаряжения не занимает: его имя — в заголовке карточки рюкзака.
    final pack = eng.currentPack();
    final gifts = heldItemIds(hero).where((id) => _isGift(w, id)).toList();
    // Инструменты без ячейки (спички, жемчужина) — подписью у рюкзака.
    final tools = hero.inv.entries
        .where((e) => e.value > 0 && !_isConsumable(w, e.key) && !_isGift(w, e.key) && !hero.gear.contains(e.key))
        .map((e) => e.key)
        .toList()
      ..sort();
    final stove = hero.gear.firstWhere((g) => w.itemSpec(g)['stove'] == true, orElse: () => '');
    final pick = _resolve(hero, units, eng, w, heat);
    final usedCount = l.gearUsesLeft(units.length, packSlots);
    final gearCells = math.max(gearSlots, slotGear.length);
    final packCells = math.max(packSlots, units.length);
    final packRows = (packCells + 3) ~/ 4;

    final clewStatus = c.clewStatus();
    final clewItem = c.clewItem();

    return Scaffold(
      appBar: AppBar(
        title: ScreenTitle(kicker: l.heroKicker(w.chapterAt(hero.pos), c.journeyDay()), title: l.heroTitle),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: Gap.m),
            child: Center(
              child: GestureDetector(
                onTap: () => openCoinShop(context, ref, 'hero'),
                child: _CoinsChip(coins: hero.coins, label: l.heroCoinsA11y(hero.coins)),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(12, 2, 12, Gap.s + bottom),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (hero.overflow.isNotEmpty) ...[
              WarnBox(text: l.overflowPending, icon: Icons.backpack_outlined, onTap: _openOverflow),
              const SizedBox(height: Gap.s),
            ],

            // ---------------- три мини-показателя
            Row(children: [
              for (var i = 0; i < statKeys.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: _StatTile(
                    label: _statName(l, statKeys[i]),
                    asset: 'stat_${statKeys[i]}',
                    value: hero.stats[statKeys[i]] ?? 0.0,
                    max: eng.maxStat,
                    threshold: eng.dangerBelow,
                    color: switch (statKeys[i]) {
                      'satiety' => Palette.satiety,
                      'water' => Palette.water,
                      _ => Palette.warmth,
                    },
                    icon: switch (statKeys[i]) {
                      'satiety' => Icons.restaurant,
                      'water' => Icons.water_drop_outlined,
                      _ => Icons.local_fire_department_outlined,
                    },
                  ),
                ),
              ],
            ]),
            const SizedBox(height: Gap.s),

            // ---------------- снаряжение
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _CardHead(title: l.gear, count: l.gearUsesLeft(slotGear.length, gearSlots)),
                  _ClampText(
                    child: Row(children: [
                      for (var i = 0; i < gearCells; i++) ...[
                        if (i > 0) const SizedBox(width: 6),
                        Expanded(
                          child: i < slotGear.length
                              ? _GearCell(
                                  id: slotGear[i],
                                  name: content.itemName(slotGear[i]),
                                  left: eng.usesLeft(slotGear[i]),
                                  max: _nominalUses(w, eng, slotGear[i]),
                                  gift: _isGift(w, slotGear[i]),
                                  selected: pick != null && pick.gear && pick.id == slotGear[i],
                                  onTap: () => setState(() => _pick = _Pick(slotGear[i], gear: true)),
                                )
                              : _EmptyCell(height: 62, label: l.heroSlotFree),
                        ),
                      ],
                    ]),
                  ),
                  if (stove.isNotEmpty) ...[
                    const SizedBox(height: Gap.s),
                    _StovePlate(
                      status: heat,
                      left: eng.usesLeft(stove),
                      max: _nominalUses(w, eng, stove),
                      heatables: eng.heatableCount(),
                      onHeat: _heat,
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: Gap.s),

            // ---------------- дары духов: отдельная строка под снаряжением
            for (final id in gifts) ...[
              _giftLine(l, eng, w, content.itemName(id), id, now, clewStatus, clewItem),
              const SizedBox(height: Gap.s),
            ],

            // ---------------- рюкзак
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _CardHead(
                    title: pack == null ? l.backpack : content.itemName(pack),
                    count: tools.isEmpty
                        ? usedCount
                        : l.heroPackWithTools(usedCount, tools.map(content.itemName).join(', ')),
                  ),
                  _ClampText(
                    child: Column(children: [
                      for (var r = 0; r < packRows; r++) ...[
                        if (r > 0) const SizedBox(height: 6),
                        Row(children: [
                          for (var j = 0; j < 4; j++) ...[
                            if (j > 0) const SizedBox(width: 6),
                            Expanded(child: _packCell(l, eng, w, content.itemName, units, r * 4 + j, packSlots, hot, pick)),
                          ],
                        ]),
                      ],
                    ]),
                  ),
                ],
              ),
            ),
            const SizedBox(height: Gap.s),

            // ---------------- строка действий выбранной вещи
            AnimatedSize(
              duration: const Duration(milliseconds: 180),
              alignment: Alignment.topCenter,
              child: pick == null
                  ? Padding(
                      padding: const EdgeInsets.symmetric(horizontal: Gap.xs, vertical: Gap.s),
                      child: Text(l.backpackEmpty, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13)),
                    )
                  : pick.gear
                      ? _gearPanel(l, eng, w, content.itemName(pick.id), pick.id, heat, now)
                      : _packPanel(l, eng, w, content.itemName(pick.id), pick.id, heat, hot, stove),
            ),
          ],
        ),
      ),
    );
  }

  Widget _packCell(AppLocalizations l, Engine eng, World w, String Function(String) nameOf, List<String> units, int idx,
      int packSlots, bool hot, _Pick? pick) {
    if (idx >= units.length) {
      return idx < packSlots ? _EmptyCell(height: 52, label: l.heroSlotFree) : const SizedBox(height: 52);
    }
    final id = units[idx];
    final p = w.portionsOf(id);
    final first = idx == 0 || units[idx - 1] != id;
    final open = p > 1 ? (first ? eng.portionsOpen(id) : p) : 0;
    return _PackCell(
      id: id,
      name: nameOf(id),
      type: w.itemType(id),
      portions: open,
      portionsMax: p > 1 ? p : 0,
      hot: hot && w.heatable(id),
      selected: pick != null && !pick.gear && pick.index == idx,
      onTap: () => setState(() => _pick = _Pick(id, index: idx)),
    );
  }

  Widget _giftLine(AppLocalizations l, Engine eng, World w, String name, String id, int now, String clewStatus,
      String? clewItem) {
    final kind = giftKind(w, id);
    final isAction = kind == 'guide' || kind == 'mirage' || kind == 'action';
    final askable = _hasHint(w, id) || kind == 'clew';
    final st = isAction ? eng.giftStatus(id, now) : 'bad_kind';
    final askReady = askable && clewStatus == 'ready' && clewItem == id;
    String label;
    String status;
    VoidCallback? onTap;
    if (st == 'ready') {
      label = giftActionLabel(l, id, name);
      status = l.heroGiftReady;
      onTap = () => _useGift(id);
    } else if (askReady) {
      label = clewAskLabel(l, id);
      status = l.heroGiftReady;
      onTap = () => _ask(id);
    } else {
      label = isAction ? giftActionLabel(l, id, name) : (askable ? clewAskLabel(l, id) : name);
      final actNote = isAction ? giftStatusText(l, st, eng.abilityCooldownDays(id, now)) : null;
      String? askNote;
      if (askable) {
        final spec = w.itemSpec(id);
        final cd = eng.abilityCooldownDays(_hasHint(w, id) ? '$id:hint' : id, now);
        if (spec.containsKey('uses') && eng.usesLeft(id) <= 0) {
          askNote = l.giftStatus_no_charges;
        } else if (cd > 0) {
          askNote = l.giftStatus_cooldown(cd);
        } else if (clewStatus == 'not_here') {
          askNote = l.gearClewNotHere;
        } else {
          askNote = l.heroGiftInEvent;
        }
      }
      status = (askNote != null && (actNote == null || st == 'nothing' || st == 'not_here')) ? askNote : (actNote ?? '');
    }
    final max = eng.maxUses(id);
    final charges = max > 0 ? l.gearUsesLeft(eng.usesLeft(id), max) : null;
    return _GiftLine(
      id: id,
      type: w.itemType(id),
      name: name,
      tag: l.heroGiftTag,
      status: charges == null ? status : '$charges · $status',
      label: label,
      onTap: onTap,
    );
  }

  Widget _packPanel(
      AppLocalizations l, Engine eng, World w, String name, String id, String heat, bool hot, String stove) {
    final hero = eng.s;
    final n = hero.inv[id] ?? 0;
    final p = w.portionsOf(id);
    final type = w.itemType(id);
    final heatV = w.itemValue(id, 'heat');
    final heatable = heatV > 0;
    final hotNow = hot && heatable;
    final canHeat = heatable && heat == 'ready';
    final sub = <String>[
      if (p > 1) l.heroPortionsLeft(eng.portionsOpen(id), p),
      l.heroCells(n),
      if (hotNow) l.gearHot else if (heatable) l.heroHeatable,
    ].join(' · ');
    final gains = <String>[
      for (final k in statKeys)
        if (eng.statGain(id, k) > 0) _gainText(l, k, eng.statGain(id, k).round()),
    ];
    final hotLine = heatable ? l.gearPerkHeat((eng.statGain(id, 'warmth') + heatV).round()) : null;
    final verb = type == 'drink' ? (p > 1 ? l.heroSip : l.heroDrink) : l.heroEat;
    final heatVerb = type == 'drink' ? l.heroHeatDrink : l.heroHeatEat;
    final gas = stove.isEmpty ? 0 : eng.usesLeft(stove);
    return _ActionPanel(
      key: ValueKey<String>('pack:$id'),
      id: id,
      type: type,
      hot: hotNow,
      title: n > 1 ? l.gearPortions(name, n) : name,
      subtitle: sub,
      right: (gains.isEmpty && hotLine == null)
          ? null
          : Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (gains.isNotEmpty)
                  Text(gains.join(', '),
                      textAlign: TextAlign.end,
                      style: const TextStyle(color: Palette.accent, fontSize: 12, fontWeight: FontWeight.w700)),
                if (hotLine != null)
                  Text(hotLine,
                      textAlign: TextAlign.end,
                      style: const TextStyle(color: Palette.ember, fontSize: 11, fontWeight: FontWeight.w700)),
              ],
            ),
      actions: [
        if (canHeat)
          _Pill(label: heatVerb, icon: Icons.local_fire_department_outlined, primary: true, onTap: () => _heatAndUse(id)),
        _Pill(label: verb, icon: Icons.back_hand_outlined, primary: !canHeat, onTap: () => _use(id)),
        _Pill(label: l.overflowDrop, icon: Icons.delete_outline, iconOnly: true, onTap: () => _confirmDrop(id, name)),
      ],
      note: _forecast(l, eng, w, id, heat, gas),
    );
  }

  Widget _gearPanel(AppLocalizations l, Engine eng, World w, String name, String id, String heat, int now) {
    final hero = eng.s;
    final isStove = w.itemSpec(id)['stove'] == true;
    final max = _nominalUses(w, eng, id);
    final left = eng.usesLeft(id);
    final notes = <String>[];
    final exp = hero.expires[id];
    if (exp != null) {
      final days = exp - eng.gameDay(now);
      notes.add(l.gearPerkExpires(days < 0 ? 0 : days));
    }
    if (w.itemSpec(id)['upkeep'] != null && hero.fed[id] != true) notes.add(l.gearUpkeepHungry);
    return _ActionPanel(
      key: ValueKey<String>('gear:$id'),
      id: id,
      type: 'gear',
      hot: false,
      dim: max > 0 && left <= 0,
      title: name,
      subtitle: perksLine(l, w, id, skip: const {'uses'}),
      subtitleLines: 2,
      right: max > 0
          ? Text(
              left > 0 ? l.gearUsesLeft(left, max) : l.gearEmptyCharges,
              style: TextStyle(
                color: left > 0 ? Palette.accent : Palette.ember,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            )
          : null,
      actions: [
        if (isStove)
          _Pill(
            label: l.gearHeat,
            icon: Icons.local_fire_department_outlined,
            primary: true,
            onTap: heat == 'ready' ? _heat : null,
          ),
        _Pill(label: l.overflowDrop, icon: Icons.delete_outline, iconOnly: true, onTap: () => _confirmDrop(id, name)),
      ],
      note: notes.join(' · '),
      noteColor: Palette.ember,
    );
  }
}

// ---------------------------------------------------------------- элементы

/// Ячейки и подписи в них не растут с крупным шрифтом выше 1,15 (иначе ломается сетка 4×2).
class _ClampText extends StatelessWidget {
  const _ClampText({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => MediaQuery.withClampedTextScaling(maxScaleFactor: 1.15, child: child);
}

class _CoinsChip extends StatelessWidget {
  const _CoinsChip({required this.coins, required this.label});
  final int coins;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      excludeSemantics: true,
      child: Container(
        height: 30,
        padding: const EdgeInsets.fromLTRB(8, 0, 11, 0),
        decoration: BoxDecoration(
          color: Palette.inkRaised,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: Palette.inkHigh),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.toll, size: 16, color: Palette.accent),
          const SizedBox(width: 5),
          Text('$coins',
              style: const TextStyle(color: Palette.parchment, fontSize: 13, fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.label,
    required this.asset,
    required this.value,
    required this.max,
    required this.threshold,
    required this.color,
    required this.icon,
  });

  final String label;
  final String asset;
  final double value;
  final double max;
  final double threshold;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final danger = value < threshold;
    final top = max > 0 ? max : 100.0;
    final frac = math.max(0.0, math.min(1.0, value / top));
    final tick = math.max(0.0, math.min(1.0, threshold / top));
    final barColor = danger ? Palette.coralLine : color;
    return Semantics(
      label: '$label ${value.round()}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 7),
        decoration: BoxDecoration(
          color: danger ? const Color(0xFF231A24) : Palette.inkRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: danger ? Palette.coralLine : Palette.inkHigh),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(children: [
              FallbackArt(
                candidates: ['assets/art/items/$asset.svg'],
                width: 18,
                height: 18,
                fit: BoxFit.contain,
                fallback: Icon(icon, size: 16, color: color),
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Text(label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Palette.parchment, fontSize: 11)),
              ),
              Text('${value.round()}',
                  style: TextStyle(
                    color: danger ? Palette.coralLine : Palette.parchment,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  )),
              if (danger) ...[
                const SizedBox(width: 2),
                const Icon(Icons.warning_amber_rounded, size: 14, color: Palette.coralLine),
              ],
            ]),
            const SizedBox(height: 5),
            SizedBox(
              height: 5,
              child: LayoutBuilder(
                builder: (BuildContext ctx, BoxConstraints box) {
                  final wd = box.maxWidth;
                  return Stack(children: [
                    Positioned.fill(
                      child: DecoratedBox(
                        decoration:
                            BoxDecoration(color: Palette.inkHigh, borderRadius: BorderRadius.circular(3)),
                      ),
                    ),
                    Positioned(
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: wd * frac,
                      child: DecoratedBox(
                        decoration: BoxDecoration(color: barColor, borderRadius: BorderRadius.circular(3)),
                      ),
                    ),
                    // отметка порога опасности (stats.dangerBelow)
                    Positioned(
                      left: math.max(0.0, wd * tick - 0.75),
                      top: 0,
                      bottom: 0,
                      width: 1.5,
                      child: const ColoredBox(color: Palette.ink),
                    ),
                  ]);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
      decoration: cardDecoration(),
      child: child,
    );
  }
}

class _CardHead extends StatelessWidget {
  const _CardHead({required this.title, required this.count});
  final String title;
  final String count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(children: [
        Text(title, style: const TextStyle(color: Palette.parchment, fontSize: 14, fontWeight: FontWeight.w700)),
        const SizedBox(width: Gap.s),
        Expanded(
          child: Text(count,
              textAlign: TextAlign.end,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
        ),
      ]),
    );
  }
}

/// Стеклянная ячейка: свинцовый кант, тонкая внутренняя линия, радиальное стекло; выбранная — бирюза.
class _GlassCell extends StatelessWidget {
  const _GlassCell({
    required this.height,
    required this.child,
    this.selected = false,
    this.hot = false,
    this.line,
  });

  final double height;
  final Widget child;
  final bool selected;
  final bool hot;
  final Color? line;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Palette.lead, width: 1.5),
        boxShadow: selected ? [BoxShadow(color: Palette.accent.withAlpha(90), blurRadius: 14)] : null,
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10.5),
          border: Border.all(color: selected ? Palette.accent : (line ?? Palette.chipLine), width: selected ? 2.0 : 1.0),
          gradient: RadialGradient(
            center: const Alignment(0, -0.2),
            radius: 0.9,
            colors: hot
                ? const [Color(0xFF3A2A2C), Color(0xFF16141C)]
                : const [Color(0xFF1D2F40), Color(0xFF111B27)],
          ),
        ),
        child: child,
      ),
    );
  }
}

/// Нажимаемая ячейка с подписью для экранного диктора.
class _Tap extends StatelessWidget {
  const _Tap({required this.label, required this.selected, required this.onTap, required this.child});
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      child: InkWell(borderRadius: BorderRadius.circular(12), onTap: onTap, child: child),
    );
  }
}

class _GearCell extends StatelessWidget {
  const _GearCell({
    required this.id,
    required this.name,
    required this.left,
    required this.max,
    required this.gift,
    required this.selected,
    required this.onTap,
  });

  final String id;
  final String name;
  final int left;
  final int max;
  final bool gift;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final count = max > 0 ? (left > 0 ? l.gearUsesLeft(left, max) : l.gearEmptyCharges) : '';
    return _Tap(
      label: count.isEmpty ? name : '$name, $count',
      selected: selected,
      onTap: onTap,
      child: _GlassCell(
        height: 62,
        selected: selected,
        line: gift ? Palette.zoneWild : null,
        child: SizedBox.expand(
          child: Stack(clipBehavior: Clip.none, children: [
            Positioned(
              left: 0,
              right: 0,
              top: 3,
              child: Center(child: ItemIcon(id, size: 36, type: 'gear', dim: max > 0 && left <= 0)),
            ),
            if (max > 0)
              Positioned(
                left: 10,
                right: 10,
                bottom: 15,
                child: max <= 3 ? _Pips(left: left, max: max) : _GasBar(frac: left / max),
              ),
            Positioned(
              left: 3,
              right: 3,
              bottom: 3,
              child: Text(name,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 10, height: 1)),
            ),
            if (max > 0)
              Positioned(
                top: 3,
                right: 3,
                child: _CountBadge(text: l.gearUsesLeft(left, max), warn: left <= 0),
              ),
          ]),
        ),
      ),
    );
  }
}

class _PackCell extends StatelessWidget {
  const _PackCell({
    required this.id,
    required this.name,
    required this.type,
    required this.portions,
    required this.portionsMax,
    required this.hot,
    required this.selected,
    required this.onTap,
  });

  final String id;
  final String name;
  final String type;

  /// Порций в этой ячейке; [portionsMax] 0 — предмет без порций.
  final int portions;
  final int portionsMax;
  final bool hot;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final multi = portionsMax > 1;
    final count = multi ? l.gearUsesLeft(portions, portionsMax) : '';
    final parts = <String>[name, if (count.isNotEmpty) count, if (hot) l.gearHot];
    return _Tap(
      label: parts.join(', '),
      selected: selected,
      onTap: onTap,
      child: _GlassCell(
        height: 52,
        selected: selected,
        hot: hot,
        child: SizedBox.expand(
          child: Stack(clipBehavior: Clip.none, children: [
            if (multi)
              Center(
                child: CustomPaint(
                  size: const Size(44, 44),
                  painter: _RingPainter(frac: portions / portionsMax),
                ),
              ),
            Center(child: ItemIcon(id, size: 34, type: type)),
            if (multi) Positioned(right: 3, bottom: 3, child: _CountBadge(text: count)),
            if (hot) const Positioned(top: 3, right: 3, child: _HotBadge()),
          ]),
        ),
      ),
    );
  }
}

class _EmptyCell extends StatelessWidget {
  const _EmptyCell({required this.height, required this.label});
  final double height;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      excludeSemantics: true,
      child: CustomPaint(
        painter: const _DashedRRectPainter(),
        child: SizedBox(
          height: height,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.add, size: 16, color: _emptyText),
              Text(label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: _emptyText, fontSize: 9.5, height: 1.1)),
            ],
          ),
        ),
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  const _CountBadge({required this.text, this.warn = false});
  final String text;
  final bool warn;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: Palette.ink,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: Palette.chipLine),
      ),
      child: Text(text,
          style: TextStyle(
            color: warn ? Palette.ember : Palette.parchment,
            fontSize: 10,
            fontWeight: FontWeight.w700,
            height: 1.4,
          )),
    );
  }
}

class _HotBadge extends StatelessWidget {
  const _HotBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 16,
      height: 16,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Palette.ink,
        border: Border.all(color: Palette.ember, width: 1.3),
      ),
      child: const Icon(Icons.local_fire_department, size: 10, color: Palette.ember),
    );
  }
}

class _Pips extends StatelessWidget {
  const _Pips({required this.left, required this.max});
  final int left;
  final int max;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var j = 0; j < max; j++) ...[
          if (j > 0) const SizedBox(width: 3),
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: j < left ? Palette.accent : Palette.inkHigh,
              border: Border.all(color: Palette.lead),
            ),
          ),
        ],
      ],
    );
  }
}

class _GasBar extends StatelessWidget {
  const _GasBar({required this.frac});
  final double frac;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 4,
      alignment: Alignment.centerLeft,
      decoration: BoxDecoration(color: Palette.inkHigh, borderRadius: BorderRadius.circular(2)),
      child: FractionallySizedBox(
        widthFactor: math.max(0.0, math.min(1.0, frac)),
        child: Container(
          decoration: BoxDecoration(color: Palette.accent, borderRadius: BorderRadius.circular(2)),
        ),
      ),
    );
  }
}

/// Плашка горелки под снаряжением: «горит · N вещи горячие · газ x/y» или «Нагреть».
class _StovePlate extends StatelessWidget {
  const _StovePlate({
    required this.status,
    required this.left,
    required this.max,
    required this.heatables,
    required this.onHeat,
  });

  final String status;
  final int left;
  final int max;
  final int heatables;
  final VoidCallback onHeat;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final on = status == 'on';
    final ready = status == 'ready';
    final text = on
        ? l.heroStoveOn(heatables, left, max)
        : ready
            ? l.heroStoveReady(left, max, heatables)
            : l.heroStoveIdle(left, max);
    final reason = switch (status) {
      'no_gas' => l.gearHeatNoGas,
      'nothing' => l.gearHeatNothing,
      _ => null,
    };
    return Container(
      constraints: const BoxConstraints(minHeight: 32),
      padding: ready ? const EdgeInsets.fromLTRB(10, 0, 2, 0) : const EdgeInsets.fromLTRB(10, 6, 10, 6),
      decoration: BoxDecoration(
        color: on ? _hotBg : Palette.chipBg,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: on ? _hotLine : Palette.chipLine),
      ),
      child: Row(children: [
        Icon(on ? Icons.local_fire_department : Icons.local_fire_department_outlined,
            size: 15, color: on ? Palette.ember : Palette.parchmentDim),
        const SizedBox(width: 7),
        Expanded(child: Text(text, style: const TextStyle(color: _note, fontSize: 11.5, height: 1.25))),
        if (reason != null) ...[
          const SizedBox(width: 6),
          // Предел ширины: причина переносится, а не вытесняет основной текст и не переполняет строку.
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 120),
            child: Text(reason, style: const TextStyle(color: Palette.parchmentDim, fontSize: 11)),
          ),
        ],
        if (ready) ...[
          const SizedBox(width: 4),
          _Pill(label: l.gearHeat, icon: Icons.local_fire_department_outlined, primary: true, small: true, onTap: onHeat),
        ],
      ]),
    );
  }
}

/// Строка дара: значок, имя и метка «дар», статус (готов, отдыхает, где сработает) и кнопка.
class _GiftLine extends StatelessWidget {
  const _GiftLine({
    required this.id,
    required this.type,
    required this.name,
    required this.tag,
    required this.status,
    required this.label,
    required this.onTap,
  });

  final String id;
  final String type;
  final String name;
  final String tag;
  final String status;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(6, 0, 4, 0),
      decoration: BoxDecoration(
        color: Palette.inkRaised,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: onTap != null ? Palette.zoneWild : Palette.inkHigh),
      ),
      child: Row(children: [
        ItemIcon(id, size: 28, type: type),
        const SizedBox(width: Gap.s),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(children: [
                  Flexible(
                    child: Text(name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style:
                            const TextStyle(color: Palette.parchment, fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(7),
                      border: Border.all(color: Palette.zoneWild),
                    ),
                    child: Text(tag,
                        style: const TextStyle(color: _giftText, fontSize: 10, fontWeight: FontWeight.w700)),
                  ),
                ]),
                if (status.isNotEmpty)
                  Text(status,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Palette.parchmentDim, fontSize: 11, height: 1.3)),
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),
        _Pill(label: label, primary: true, small: true, onTap: onTap),
      ]),
    );
  }
}

/// Строка действий выбранной вещи: значок, название, пояснение, эффекты справа, кнопки, прогноз.
class _ActionPanel extends StatelessWidget {
  const _ActionPanel({
    super.key,
    required this.id,
    required this.type,
    required this.hot,
    required this.title,
    required this.subtitle,
    required this.actions,
    required this.note,
    this.right,
    this.dim = false,
    this.subtitleLines = 1,
    this.noteColor = _note,
  });

  final String id;
  final String type;
  final bool hot;
  final bool dim;
  final String title;
  final String subtitle;
  final int subtitleLines;
  final Widget? right;
  final List<Widget> actions;
  final String note;
  final Color noteColor;

  @override
  Widget build(BuildContext context) {
    final r = right;
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 8, 6),
      decoration: BoxDecoration(
        color: _panelBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Palette.accent),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(children: [
            SizedBox(
              width: 40,
              height: 40,
              child: Stack(clipBehavior: Clip.none, children: [
                ItemIcon(id, size: 40, type: type, dim: dim),
                if (hot) const Positioned(top: -3, right: -4, child: _HotBadge()),
              ]),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Palette.parchment, fontSize: 13.5, fontWeight: FontWeight.w700)),
                  if (subtitle.isNotEmpty)
                    Text(subtitle,
                        maxLines: subtitleLines,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Palette.parchmentDim, fontSize: 11, height: 1.3)),
                ],
              ),
            ),
            if (r != null) ...[
              const SizedBox(width: Gap.s),
              // Негибкий ребёнок Row получает неограниченную ширину: длинная строка эффектов
              // («+30 сытость, +10 вода, …») сжимала название в 0 и переполняла строку.
              ConstrainedBox(constraints: const BoxConstraints(maxWidth: 130), child: r),
            ],
          ]),
          const SizedBox(height: 2),
          Wrap(
            spacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: actions,
          ),
          if (note.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 2, bottom: 2),
              child: Text(note, style: TextStyle(color: noteColor, fontSize: 11, height: 1.3)),
            ),
        ],
      ),
    );
  }
}

/// Кнопка-«пилюля» эталона (.ab): видимая высота 34 (малая — 30), зона нажатия не меньше 44.
class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.onTap,
    this.icon,
    this.primary = false,
    this.iconOnly = false,
    this.small = false,
  });

  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool primary;
  final bool iconOnly;
  final bool small;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    final accent = primary && enabled;
    final fg = !enabled ? Palette.parchmentDim : (primary ? Palette.accent : Palette.parchment);
    final h = small ? 30.0 : 34.0;
    final ic = icon;
    Widget pill = Container(
      height: h,
      width: iconOnly ? h : null,
      padding: iconOnly ? EdgeInsets.zero : EdgeInsets.symmetric(horizontal: small ? 10.0 : 12.0),
      decoration: BoxDecoration(
        color: accent ? Palette.accent.withAlpha(36) : Palette.chipBg,
        borderRadius: BorderRadius.circular(h / 2),
        border: Border.all(color: accent ? Palette.accent : Palette.chipLine, width: accent ? 1.5 : 1.0),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (ic != null) Icon(ic, size: 15, color: accent ? Palette.accent : Palette.parchmentDim),
          if (ic != null && !iconOnly) const SizedBox(width: 5),
          // Пилюля стоит и в Row без ограничения ширины (горелка, строка дара) — Flexible нельзя;
          // предел ширины обрезает длинную подпись (имя предмета-запаска) вместо переполнения строки.
          if (!iconOnly)
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 160),
              child: Text(label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: fg, fontSize: small ? 11.5 : 12.5, fontWeight: FontWeight.w700)),
            ),
        ],
      ),
    );
    if (!enabled) pill = Opacity(opacity: 0.6, child: pill);
    Widget out = Semantics(
      button: true,
      enabled: enabled,
      label: label,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 44, minWidth: 44),
          child: Center(widthFactor: 1, heightFactor: 1, child: pill),
        ),
      ),
    );
    if (iconOnly) out = Tooltip(message: label, child: out);
    return out;
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter({required this.frac});
  final double frac;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.shortestSide / 2 - 1.5;
    final bg = Paint()
      ..color = Palette.inkHigh
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawCircle(c, r, bg);
    final f = math.max(0.0, math.min(1.0, frac));
    if (f <= 0) return;
    final fg = Paint()
      ..color = Palette.water
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), -math.pi / 2, 2 * math.pi * f, false, fg);
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) => oldDelegate.frac != frac;
}

/// Пунктирная скруглённая рамка свободной ячейки.
class _DashedRRectPainter extends CustomPainter {
  const _DashedRRectPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = _emptyLine
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final rr = RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(12)).deflate(0.75);
    final path = Path()..addRRect(rr);
    for (final metric in path.computeMetrics()) {
      var d = 0.0;
      while (d < metric.length) {
        final next = math.min(d + 4.0, metric.length);
        canvas.drawPath(metric.extractPath(d, next), paint);
        d = next + 3.0;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

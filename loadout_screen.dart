// «Собери рюкзак» (O6, docs/v5/09 §4.6): до maxGear снаряжения и до maxPackSlots ячеек еды перед прологом.
// Все пределы и перки — из balance.json через World; выбор уходит в AppController.chooseLoadout.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/item_icon.dart';

/// Текст ошибки старт-набора по коду из World.loadoutError (§5.3).
String loadoutErrorText(AppLocalizations l, String code) => switch (code) {
      'gear_too_many' => l.loadoutErr_gear_too_many,
      'gear_duplicate' => l.loadoutErr_gear_duplicate,
      'gear_not_starter' => l.loadoutErr_gear_not_starter,
      'pack_not_starter' => l.loadoutErr_pack_not_starter,
      'pack_bad_count' => l.loadoutErr_pack_bad_count,
      'pack_kind_limit' => l.loadoutErr_pack_kind_limit,
      'pack_too_many' => l.loadoutErr_pack_too_many,
      _ => l.loadoutErr_unknown,
    };

class LoadoutScreen extends ConsumerStatefulWidget {
  const LoadoutScreen({super.key, required this.onDone, required this.onBack, required this.stageBar});

  final VoidCallback onDone;
  final VoidCallback onBack;

  /// Полоса этапов онбординга (под AppBar).
  final PreferredSizeWidget stageBar;

  @override
  ConsumerState<LoadoutScreen> createState() => _LoadoutScreenState();
}

class _LoadoutScreenState extends ConsumerState<LoadoutScreen> {
  List<String> _gear = <String>[];
  Map<String, int> _pack = <String, int>{};
  int _tab = 0;
  bool _advisor = false;
  bool _edited = false;
  String? _lastHint;
  Timer? _saveTimer;
  final Stopwatch _clock = Stopwatch()..start();

  @override
  void initState() {
    super.initState();
    final f = ref.read(uiFlagsProvider);
    // Первый показ — пустой выбор: пусть игрок прочитает перки (§4.6).
    _gear = List<String>.of(f.loadoutGear ?? const <String>[]);
    _pack = Map<String, int>.of(f.loadoutPack ?? const <String, int>{});
    _advisor = f.loadoutAdvisor;
  }

  @override
  void dispose() {
    _saveTimer?.cancel();
    super.dispose();
  }

  World get _w => ref.read(appProvider).content!.world;
  Json get _lo => (_w.balance['loadout'] as Map).cast<String, dynamic>();
  Json get _eco => (_w.balance['economy'] as Map).cast<String, dynamic>();
  int get _maxGear => toI(_lo['maxGear']);
  int get _maxPack => toI(_lo['maxPackSlots']);
  int get _maxKind => toI(_lo['maxPerKind']);
  int get _gearSlots => toI(_eco['gearSlots']);
  int get _packSlots => toI(_eco['backpackSlots']);
  int get _packSum => _pack.values.fold<int>(0, (a, b) => a + b);

  bool _hasPerk(String id, Set<String> keys) => _w.itemPerks(id).any((p) => keys.contains(p.key));

  void _changed() {
    _saveTimer?.cancel();
    _saveTimer = Timer(const Duration(milliseconds: 300), _saveDraft);
  }

  Future<void> _saveDraft() {
    final gear = List<String>.of(_gear);
    final pack = Map<String, int>.of(_pack);
    final advisor = _advisor;
    return ref.read(uiFlagsProvider.notifier).update((f) {
      f.loadoutGear = gear;
      f.loadoutPack = pack;
      f.loadoutAdvisor = advisor;
    });
  }

  void _hint(String id, String text, {bool limit = false}) {
    if (_lastHint == id) {
      if (limit) HapticFeedback.lightImpact();
      return;
    }
    _lastHint = id;
    if (limit) HapticFeedback.lightImpact();
    Analytics.instance.event('loadout_hint', {'id': id});
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(content: Text(text), duration: const Duration(seconds: 3)));
  }

  void _toggleGear(String id) {
    final l = AppLocalizations.of(context);
    if (!_gear.contains(id) && _gear.length >= _maxGear) {
      _hint('gear_full', l.loadoutHintGearFull, limit: true);
      return;
    }
    setState(() {
      if (_gear.contains(id)) {
        _gear.remove(id);
      } else {
        _gear.add(id);
      }
      if (_advisor) _edited = true;
      _lastHint = null;
    });
    _changed();
  }

  void _addPack(String id) {
    final l = AppLocalizations.of(context);
    final n = _pack[id] ?? 0;
    if (n >= _maxKind) {
      _hint('kind_max', l.loadoutHintKindMax, limit: true);
      return;
    }
    if (_packSum >= _maxPack) {
      _hint('pack_full', l.loadoutHintPackFull, limit: true);
      return;
    }
    setState(() {
      _pack[id] = n + 1;
      if (_advisor) _edited = true;
      _lastHint = null;
    });
    _changed();
  }

  void _removePack(String id) {
    final n = _pack[id] ?? 0;
    if (n <= 0) return;
    setState(() {
      if (n == 1) {
        _pack.remove(id);
      } else {
        _pack[id] = n - 1;
      }
      if (_advisor) _edited = true;
      _lastHint = null;
    });
    _changed();
  }

  void _useAdvisor() {
    final l = AppLocalizations.of(context);
    final prevGear = List<String>.of(_gear);
    final prevPack = Map<String, int>.of(_pack);
    final prevAdvisor = _advisor;
    final d = ref.read(appProvider.notifier).defaultLoadout;
    setState(() {
      _gear = List<String>.of(d.gear);
      _pack = Map<String, int>.of(d.pack);
      _advisor = true;
      _edited = false;
    });
    _changed();
    Analytics.instance.event('loadout_advisor', {'tab': _tab == 0 ? 'gear' : 'pack'});
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(
      content: Text(l.loadoutAdvisorToast),
      duration: const Duration(seconds: 5),
      action: SnackBarAction(
        label: l.loadoutUndo,
        onPressed: () {
          if (!mounted) return;
          setState(() {
            _gear = prevGear;
            _pack = prevPack;
            _advisor = prevAdvisor;
          });
          _changed();
        },
      ),
    ));
  }

  /// Первое место с лавкой впереди старта — для подсказки «без воды тяжело».
  (String, String)? _firstMarket() {
    for (final p in _w.places) {
      if (p['virtual'] == true || p['market'] == null) continue;
      final at = _w.posOf[p['id']];
      if (at == null || at <= 0) continue;
      return ('${p['name']}', (at / 1000).round().toString());
    }
    return null;
  }

  void _toPack() {
    final l = AppLocalizations.of(context);
    setState(() => _tab = 1);
    if (!_gear.any((g) => _hasPerk(g, const {'warmthDrain', 'weatherCold', 'idleWarmth'}))) {
      _hint('no_warm', l.loadoutHintNoWarm);
    }
  }

  void _toGear() {
    final l = AppLocalizations.of(context);
    setState(() => _tab = 0);
    _warnNoWater(l);
  }

  void _warnNoWater(AppLocalizations l) {
    if (_pack.keys.any((k) => _hasPerk(k, const {'water'}))) return;
    final mk = _firstMarket();
    if (mk != null) _hint('no_water', l.loadoutHintNoWater(mk.$1, mk.$2));
  }

  Future<void> _assemble() async {
    final l = AppLocalizations.of(context);
    _warnNoWater(l);
    if (_gear.any((g) => _hasPerk(g, const {'stove'})) && !_pack.keys.any(_w.heatable)) {
      _hint('stove_idle', l.loadoutHintStoveIdle);
    }
    if (_gear.length < _maxGear || _packSum < _maxPack) {
      final go = await showDialog<bool>(
        context: context,
        builder: (BuildContext ctx) => AlertDialog(
          title: Text(l.loadoutLightTitle),
          content: Text(l.loadoutLightBody),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(l.loadoutLightFill)),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.loadoutLightGo)),
          ],
        ),
      );
      if (go != true || !mounted) return;
    }
    final ok = await _summary();
    if (ok != true || !mounted) return;
    final c = ref.read(appProvider.notifier);
    final d = c.defaultLoadout;
    final isDefault = _sameAs(d.gear, d.pack);
    final err = c.chooseLoadout(List<String>.of(_gear), Map<String, int>.of(_pack), isDefault: isDefault);
    if (err != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(loadoutErrorText(l, err))));
      return;
    }
    Analytics.instance.event('loadout_done', {
      'gear': _gear.join(','),
      'pack': _pack.entries.map((e) => '${e.key}:${e.value}').join(','),
      'advisor': _advisor,
      'edited': _edited,
      'free_gear': _gearSlots - _gear.length,
      'free_pack': _packSlots - _packSum,
      'seconds': _clock.elapsed.inSeconds,
    });
    _saveTimer?.cancel();
    await _saveDraft();
    await ref.read(uiFlagsProvider.notifier).update((f) => f.onboardingStep = 'prologue');
    if (mounted) widget.onDone();
  }

  bool _sameAs(List<String> gear, Map<String, int> pack) {
    if (gear.length != _gear.length || pack.length != _pack.length) return false;
    for (final g in gear) {
      if (!_gear.contains(g)) return false;
    }
    for (final e in pack.entries) {
      if (_pack[e.key] != e.value) return false;
    }
    return true;
  }

  Future<bool?> _summary() {
    final l = AppLocalizations.of(context);
    final content = ref.read(appProvider).content!;
    final w = content.world;
    final coins = toI(_eco['startCoins']);
    final freeGear = _gearSlots - _gear.length;
    final freePack = _packSlots - _packSum;
    final reservedGear = _gearSlots - _maxGear;
    final reservedPack = _packSlots - _maxPack;
    final showFree = freeGear > reservedGear || freePack > reservedPack;
    // Лист не уходит под системную панель: высота ≤ 0,85 экрана, снизу её отступ (showSafeSheet).
    return showSafeSheet<bool>(
      context: context,
      backgroundColor: Palette.inkRaised,
      showDragHandle: false,
      builder: (BuildContext ctx) {
        return ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.s),
            children: [
              Text(l.loadoutSummaryTitle, style: Theme.of(ctx).textTheme.titleLarge),
              const SizedBox(height: Gap.m),
              for (final g in _gear)
                _SummaryRow(
                  id: g,
                  type: 'gear',
                  title: content.itemName(g),
                  sub: w.itemValue(g, 'uses') > 0 ? l.loadoutUses(w.itemValue(g, 'uses').round()) : null,
                ),
              for (final e in _pack.entries)
                _SummaryRow(
                  id: e.key,
                  type: w.itemType(e.key),
                  title: e.value > 1 ? l.gearPortions(content.itemName(e.key), e.value) : content.itemName(e.key),
                  sub: w.heatable(e.key) ? l.gearPerkHeat(w.itemValue(e.key, 'heat').round()) : null,
                ),
              const SizedBox(height: Gap.m),
              Text(l.loadoutSummaryCoins(coins), style: const TextStyle(height: 1.4)),
              if (showFree) ...[
                const SizedBox(height: Gap.xs),
                Text(l.loadoutSummaryFree(freeGear, freePack),
                    style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
              ],
              const SizedBox(height: Gap.l),
              FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.loadoutConfirm)),
              const SizedBox(height: Gap.s),
              TextButton(
                style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                onPressed: () => Navigator.of(ctx).pop(false),
                child: Text(l.loadoutEdit),
              ),
            ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final content = m.content!;
    final w = content.world;
    final starterGear = w.starterGear;
    final starterPack = w.starterPack;
    final bottomInset = systemBottom(context);
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (didPop) return;
        if (_tab == 1) {
          _toGear();
        } else {
          widget.onBack();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => _tab == 1 ? _toGear() : widget.onBack(),
          ),
          title: Text(l.loadoutTitle),
          bottom: widget.stageBar,
        ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, Gap.s),
              child: Text(
                l.loadoutLead,
                style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 13, color: Palette.parchmentDim, height: 1.35),
              ),
            ),
            _SlotsPanel(
              gear: _gear,
              pack: _pack,
              gearSlots: _gearSlots,
              maxGear: _maxGear,
              packSlots: _packSlots,
              maxPack: _maxPack,
              typeOf: w.itemType,
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, 0),
              child: SegmentedButton<int>(
                showSelectedIcon: false,
                segments: [
                  ButtonSegment<int>(value: 0, label: Text(l.loadoutTabGear(_gear.length, _maxGear))),
                  ButtonSegment<int>(value: 1, label: Text(l.loadoutTabPack(_packSum, _maxPack))),
                ],
                selected: <int>{_tab},
                onSelectionChanged: (Set<int> s) {
                  if (s.first == 1 && _tab == 0) {
                    _toPack();
                  } else if (s.first == 0 && _tab == 1) {
                    _toGear();
                  }
                },
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, Gap.m),
                children: [
                  Text(
                    _tab == 0 ? l.loadoutGearInfo : l.loadoutPackInfo,
                    style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5, height: 1.35),
                  ),
                  const SizedBox(height: Gap.s),
                  if (_tab == 0) ...[
                    for (final id in starterGear)
                      Padding(
                        padding: const EdgeInsets.only(bottom: Gap.s),
                        child: _GearCard(
                          id: id,
                          name: content.itemName(id),
                          desc: '${content.items[id]?['desc'] ?? ''}',
                          perks: perksLine(l, w, id, skip: const {'uses'}),
                          uses: w.itemValue(id, 'uses').round(),
                          taken: _gear.contains(id),
                          onTap: () => _toggleGear(id),
                        ),
                      ),
                  ] else ...[
                    for (final id in starterPack)
                      Padding(
                        padding: const EdgeInsets.only(bottom: Gap.s),
                        child: _PackCard(
                          id: id,
                          type: w.itemType(id),
                          name: content.itemName(id),
                          perks: perksLine(l, w, id),
                          n: _pack[id] ?? 0,
                          onAdd: () => _addPack(id),
                          onRemove: () => _removePack(id),
                        ),
                      ),
                  ],
                ],
              ),
            ),
            Container(
              decoration: const BoxDecoration(
                color: Palette.ink,
                border: Border(top: BorderSide(color: Palette.inkHigh)),
              ),
              padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, Gap.m + bottomInset),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextButton(
                    style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                    onPressed: _useAdvisor,
                    child: Text(l.loadoutAdvisor),
                  ),
                  const SizedBox(height: Gap.xs),
                  FilledButton(
                    onPressed: _tab == 0 ? _toPack : _assemble,
                    child: Text(_tab == 0 ? l.loadoutNextPack : l.loadoutDone),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Панель ячеек: снаряжение (последние — пунктир «для находок») и рюкзак.
class _SlotsPanel extends StatelessWidget {
  const _SlotsPanel({
    required this.gear,
    required this.pack,
    required this.gearSlots,
    required this.maxGear,
    required this.packSlots,
    required this.maxPack,
    required this.typeOf,
  });

  final List<String> gear;
  final Map<String, int> pack;
  final int gearSlots;
  final int maxGear;
  final int packSlots;
  final int maxPack;
  final String Function(String) typeOf;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    const size = 34.0;
    final units = <String>[];
    pack.forEach((k, v) {
      for (var i = 0; i < v; i++) {
        units.add(k);
      }
    });
    Widget cell(String? id, bool reserved, String type) {
      if (id != null) return ItemIcon(id, size: size, type: type);
      return EmptySlot(size: size, label: reserved ? l.loadoutSlotFree : null);
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: Gap.m),
      padding: const EdgeInsets.symmetric(horizontal: Gap.s, vertical: Gap.s),
      decoration: cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (var i = 0; i < gearSlots; i++)
                cell(i < gear.length ? gear[i] : null, i >= maxGear, 'gear'),
              const SizedBox(width: Gap.s, height: size),
              for (var i = 0; i < packSlots; i++)
                cell(i < units.length ? units[i] : null, i >= maxPack, i < units.length ? typeOf(units[i]) : 'food'),
            ],
          ),
          const SizedBox(height: Gap.xs),
          Row(children: [
            const EmptySlot(size: 12),
            const SizedBox(width: Gap.xs),
            // Expanded: подпись переносится при крупном шрифте, а не переполняет строку.
            Expanded(child: Text(l.loadoutSlotFree, style: const TextStyle(color: Palette.parchmentDim, fontSize: 11))),
          ]),
        ],
      ),
    );
  }
}

class _GearCard extends StatelessWidget {
  const _GearCard({
    required this.id,
    required this.name,
    required this.desc,
    required this.perks,
    required this.uses,
    required this.taken,
    required this.onTap,
  });

  final String id;
  final String name;
  final String desc;
  final String perks;
  final int uses;
  final bool taken;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Semantics(
      selected: taken,
      button: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(Gap.radius),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(Gap.s + 4),
          decoration: cardDecoration(highlighted: taken),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ItemIcon(id, size: 44, type: 'gear'),
              const SizedBox(width: Gap.s + 4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: Theme.of(context).textTheme.titleSmall),
                    if (desc.isNotEmpty)
                      Text(desc,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.3)),
                    if (perks.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(perks, style: const TextStyle(color: Palette.accent, fontSize: 12.5, height: 1.3)),
                      ),
                    if (uses > 0)
                      Text(l.loadoutUses(uses), style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                  ],
                ),
              ),
              const SizedBox(width: Gap.s),
              taken
                  ? FilledButton(
                      style: FilledButton.styleFrom(minimumSize: const Size(88, 44)),
                      onPressed: onTap,
                      child: Text(l.loadoutTaken),
                    )
                  : OutlinedButton(
                      style: OutlinedButton.styleFrom(minimumSize: const Size(88, 44)),
                      onPressed: onTap,
                      child: Text(l.loadoutTake),
                    ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PackCard extends StatelessWidget {
  const _PackCard({
    required this.id,
    required this.type,
    required this.name,
    required this.perks,
    required this.n,
    required this.onAdd,
    required this.onRemove,
  });

  final String id;
  final String type;
  final String name;
  final String perks;
  final int n;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.s + 4, vertical: Gap.s),
      decoration: cardDecoration(highlighted: n > 0),
      child: Row(
        children: [
          ItemIcon(id, size: 44, type: type),
          const SizedBox(width: Gap.s + 4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: Theme.of(context).textTheme.titleSmall),
                if (perks.isNotEmpty)
                  Text(perks, style: const TextStyle(color: Palette.accent, fontSize: 12.5, height: 1.3)),
              ],
            ),
          ),
          IconButton(
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            onPressed: n > 0 ? onRemove : null,
            icon: const Icon(Icons.remove_circle_outline),
          ),
          SizedBox(
            width: 22,
            child: Text('$n', textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
          ),
          IconButton(
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            onPressed: onAdd,
            icon: const Icon(Icons.add_circle_outline, color: Palette.accent),
          ),
        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.id, required this.type, required this.title, this.sub});

  final String id;
  final String type;
  final String title;
  final String? sub;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Gap.s),
      child: Row(
        children: [
          ItemIcon(id, size: 36, type: type),
          const SizedBox(width: Gap.s + 4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title),
                if (sub != null) Text(sub!, style: const TextStyle(color: Palette.accent, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

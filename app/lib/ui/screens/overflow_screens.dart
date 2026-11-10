// Переполнение (docs/v5/07 «Переполнение», 08 §5.8): «Что взять с собой» для снаряжения и
// «В рюкзак не лезет» для еды. Пока в состоянии есть overflow, путь стоит и «Идти дальше» недоступно.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/state.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/item_icon.dart';

/// Нижний отступ под системной навигацией Android + запас.
double safeBottom(BuildContext context) {
  final a = MediaQuery.paddingOf(context).bottom;
  final b = MediaQuery.viewPaddingOf(context).bottom;
  return (a > b ? a : b) + Gap.l;
}

/// Экран решения по первой записи очереди. Сам меняется, когда запись решена.
class OverflowScreen extends ConsumerWidget {
  const OverflowScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final hero = m.hero;
    final o = hero == null ? null : c.pendingOverflow;
    if (hero == null || o == null) return const Scaffold(body: SizedBox.shrink());
    final key = ValueKey<String>('${o.kind}:${o.item}:${o.source}:${o.n}:${hero.overflow.length}');
    return PopScope(
      canPop: false,
      child: o.kind == 'gear' ? _GearOverflow(key: key, item: o.item) : _BackpackOverflow(key: key, item: o.item, n: o.n),
    );
  }
}

/// Отдельный экран поверх главной (после перезапуска приложения, когда очередь не пуста).
class OverflowRoute extends ConsumerWidget {
  const OverflowRoute({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final m = ref.watch(appProvider);
    if (m.hero == null || m.hero!.overflow.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
      });
      return const Scaffold(body: SizedBox.shrink());
    }
    return const OverflowScreen();
  }
}

/// Плашка на главной: вещи ждут решения. Открывает экран сама один раз за показ главной.
class OverflowBanner extends ConsumerStatefulWidget {
  const OverflowBanner({super.key});

  @override
  ConsumerState<OverflowBanner> createState() => _OverflowBannerState();
}

class _OverflowBannerState extends ConsumerState<OverflowBanner> {
  bool _opened = false;

  void _open() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const OverflowRoute()));
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final hero = m.hero;
    if (hero == null || hero.overflow.isEmpty) {
      _opened = false;
      return const SizedBox.shrink();
    }
    if (!_opened) {
      _opened = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        final route = ModalRoute.of(context);
        if (route == null || route.isCurrent) _open();
      });
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.m, 0, Gap.m, Gap.s),
      child: InkWell(
        borderRadius: BorderRadius.circular(Gap.radius),
        onTap: _open,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s + 4),
          decoration: cardDecoration(highlighted: true),
          child: Row(children: [
            const Icon(Icons.backpack_outlined, color: Palette.accent),
            const SizedBox(width: Gap.s + 4),
            Expanded(child: Text(l.overflowPending, style: const TextStyle(fontWeight: FontWeight.w600))),
            const Icon(Icons.chevron_right, color: Palette.accent),
          ]),
        ),
      ),
    );
  }
}

void _showError(BuildContext context, String code) {
  final l = AppLocalizations.of(context);
  final text = code == 'swap_not_free' ? l.overflowSwapNotFree : l.overflowError;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
}

// ---------------------------------------------------------------- снаряжение

class _GearOverflow extends ConsumerStatefulWidget {
  const _GearOverflow({super.key, required this.item});
  final String item;

  @override
  ConsumerState<_GearOverflow> createState() => _GearOverflowState();
}

class _GearOverflowState extends ConsumerState<_GearOverflow> {
  late Set<String> _keep;

  @override
  void initState() {
    super.initState();
    // только обычное снаряжение: дары ячеек не занимают и в выборе не участвуют (V5-43)
    final m = ref.read(appProvider);
    final w = m.content!.world;
    _keep = Set<String>.of(m.hero!.gear.where((g) => !w.freeSlot(g)));
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final content = m.content!;
    final w = content.world;
    final hero = m.hero!;
    final eng = Engine(w, hero);
    // Дары духов ячеек не занимают и в выборе не участвуют (V5-43).
    final plain = hero.gear.where((g) => !w.freeSlot(g)).toList();
    final cands = <String>[...plain, if (!plain.contains(widget.item)) widget.item];
    final need = eng.gearSlots() < cands.length ? eng.gearSlots() : cands.length;
    final ready = cands.where(_keep.contains).length == need;
    String? usesText(String id) {
      final max = eng.maxUses(id);
      if (max <= 0) return null;
      // Новая вещь приходит с полным запасом `uses`, у своих — остаток.
      final left = id == widget.item && !hero.gear.contains(id) ? w.itemValue(id, 'uses').round() : eng.usesLeft(id);
      return left > 0 ? l.gearUsesLeft(left, max) : l.gearEmptyCharges;
    }

    return Scaffold(
      appBar: AppBar(automaticallyImplyLeading: false, title: Text(l.overflowGearTitle)),
      body: ListView(
        padding: EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, safeBottom(context)),
        children: [
          Text(l.overflowGearHint(need), style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
          const SizedBox(height: Gap.m),
          for (final id in cands)
            Padding(
              padding: const EdgeInsets.only(bottom: Gap.s),
              child: _GearPick(
                id: id,
                name: content.itemName(id),
                perks: perksLine(l, w, id, skip: const {'uses'}),
                uses: usesText(id),
                isNew: id == widget.item,
                selected: _keep.contains(id),
                onChanged: (bool v) => setState(() {
                  if (v) {
                    if (_keep.length < need) _keep.add(id);
                  } else {
                    _keep.remove(id);
                  }
                }),
              ),
            ),
          const SizedBox(height: Gap.m),
          FilledButton(
            onPressed: ready
                ? () {
                    final keep = cands.where(_keep.contains).toList();
                    final err = c.resolveGearOverflow(keep);
                    if (err != null) _showError(context, err);
                  }
                : null,
            child: Text(l.overflowGearConfirm),
          ),
          const SizedBox(height: Gap.s),
          OutlinedButton(
            onPressed: () {
              final err = c.resolveGearOverflow(List<String>.of(plain));
              if (err != null) _showError(context, err);
            },
            child: Text(l.overflowGearKeepAsIs),
          ),
        ],
      ),
    );
  }
}

class _GearPick extends StatelessWidget {
  const _GearPick({
    required this.id,
    required this.name,
    required this.perks,
    required this.uses,
    required this.isNew,
    required this.selected,
    required this.onChanged,
  });

  final String id;
  final String name;
  final String perks;
  final String? uses;
  final bool isNew;
  final bool selected;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: cardDecoration(highlighted: selected),
      child: CheckboxListTile(
        value: selected,
        onChanged: (bool? v) => onChanged(v ?? false),
        controlAffinity: ListTileControlAffinity.trailing,
        contentPadding: const EdgeInsets.symmetric(horizontal: Gap.s + 4, vertical: Gap.xs),
        secondary: ItemIcon(id, size: 44, type: 'gear'),
        title: Row(children: [
          Flexible(child: Text(name)),
          if (isNew) ...[
            const SizedBox(width: Gap.s),
            const Icon(Icons.fiber_new_outlined, color: Palette.accent, size: 20),
          ],
        ]),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (perks.isNotEmpty) Text(perks, style: const TextStyle(color: Palette.accent, fontSize: 12)),
            if (uses != null) Text(uses!, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- рюкзак

class _BackpackOverflow extends ConsumerStatefulWidget {
  const _BackpackOverflow({super.key, required this.item, required this.n});
  final String item;
  final int n;

  @override
  ConsumerState<_BackpackOverflow> createState() => _BackpackOverflowState();
}

class _BackpackOverflowState extends ConsumerState<_BackpackOverflow> {
  bool _swap = false;

  void _act(String action, {String? swapAction, String? swapItem}) {
    final c = ref.read(appProvider.notifier);
    final err = c.resolveBackpackOverflow(action, swapAction: swapAction, swapItem: swapItem);
    if (err == 'need_swap') {
      setState(() => _swap = true);
      return;
    }
    if (err != null) _showError(context, err);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final content = m.content!;
    final w = content.world;
    final hero = m.hero!;
    final eng = Engine(w, hero);
    final hot = c.isHeated() && w.heatable(widget.item);
    final full = eng.consumablesCount() >= eng.backpackSlots();
    final name = widget.n > 1 ? l.gearPortions(content.itemName(widget.item), widget.n) : content.itemName(widget.item);
    final inBag = hero.inv.entries.where((e) {
      final t = w.itemType(e.key);
      return e.value > 0 && (t == 'food' || t == 'drink');
    }).toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: _swap ? IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => setState(() => _swap = false)) : null,
        title: Text(_swap ? l.overflowSwapTitle : l.overflowBackpackTitle),
      ),
      body: ListView(
        padding: EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, safeBottom(context)),
        children: [
          SectionCard(
            child: Row(children: [
              ItemIcon(widget.item, size: 56, type: w.itemType(widget.item), hot: hot),
              const SizedBox(width: Gap.m),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, style: Theme.of(context).textTheme.titleMedium),
                  Text(perksLine(l, w, widget.item), style: const TextStyle(color: Palette.accent, fontSize: 12.5)),
                  if (hot) Text(l.gearHot, style: const TextStyle(color: Palette.warmth, fontSize: 12)),
                  Text('${eng.consumablesCount()}/${eng.backpackSlots()}',
                      style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                ]),
              ),
            ]),
          ),
          const SizedBox(height: Gap.l),
          if (!_swap) ...[
            FilledButton(onPressed: () => _act('use'), child: Text(l.overflowUseNow)),
            const SizedBox(height: Gap.s),
            OutlinedButton(
              onPressed: full ? () => setState(() => _swap = true) : () => _act('stash'),
              child: Text(l.overflowStash),
            ),
            const SizedBox(height: Gap.s),
            TextButton(
              style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48), foregroundColor: Palette.ember),
              onPressed: () => _act('drop'),
              child: Text(l.overflowDrop),
            ),
          ] else ...[
            for (final e in inBag)
              Padding(
                padding: const EdgeInsets.only(bottom: Gap.s),
                child: _SwapRow(
                  id: e.key,
                  type: w.itemType(e.key),
                  name: w.portionsOf(e.key) > 1
                      ? l.gearPortions(content.itemName(e.key), eng.portionsTotal(e.key))
                      : (e.value > 1 ? l.gearPortions(content.itemName(e.key), e.value) : content.itemName(e.key)),
                  hot: c.isHeated() && w.heatable(e.key),
                  useBlocked: w.portionsOf(e.key) > 1 && eng.portionsOpen(e.key) > 1,
                  onUse: () => _act('stash', swapAction: 'use', swapItem: e.key),
                  onDrop: () => _act('stash', swapAction: 'drop', swapItem: e.key),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _SwapRow extends StatelessWidget {
  const _SwapRow({
    required this.id,
    required this.type,
    required this.name,
    required this.hot,
    required this.useBlocked,
    required this.onUse,
    required this.onDrop,
  });

  final String id;
  final String type;
  final String name;
  final bool hot;
  final bool useBlocked;
  final VoidCallback onUse;
  final VoidCallback onDrop;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return SectionCard(
      padding: const EdgeInsets.symmetric(horizontal: Gap.s + 4, vertical: Gap.s),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            ItemIcon(id, size: 40, type: type, hot: hot),
            const SizedBox(width: Gap.s + 4),
            Expanded(child: Text(name)),
          ]),
          const SizedBox(height: Gap.xs),
          Wrap(
            spacing: Gap.s,
            runSpacing: Gap.xs,
            children: [
              FilledButton.tonal(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
                onPressed: useBlocked ? null : onUse,
                child: Text(l.overflowSwapUse),
              ),
              OutlinedButton(
                style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44)),
                onPressed: onDrop,
                child: Text(l.overflowSwapDrop),
              ),
            ],
          ),
          if (useBlocked)
            Text(l.overflowSwapNotFree, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
        ],
      ),
    );
  }
}

/// Сколько вещей ждёт решения (для экранов остановок).
bool hasOverflow(HeroState? hero) => hero != null && hero.overflow.isNotEmpty;

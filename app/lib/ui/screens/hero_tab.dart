// Вкладка «Герой»: Сергей, показатели, рюкзак, снаряжение.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'stop_screens.dart' show itemEffectLine;

final _num = NumberFormat.decimalPattern('ru');

class HeroTab extends ConsumerWidget {
  const HeroTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final hero = m.hero!;
    final eng = Engine(m.content!.world, hero);
    final w = m.content!.world;
    final consumables = hero.inv.entries.where((e) => ['food', 'drink'].contains(w.itemType(e.key))).toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    final gear = hero.inv.entries.where((e) => !['food', 'drink'].contains(w.itemType(e.key))).toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    final totalSteps = hero.daySteps.values.fold<int>(0, (a, b) => a + b);
    final s = hero.stats;
    return Scaffold(
      appBar: AppBar(title: Text(l.heroTitle)),
      body: ListView(
        padding: const EdgeInsets.all(Gap.m),
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(Gap.radius),
                child: const Art('assets/art/hero/sergey.svg', width: 110, height: 132, fit: BoxFit.cover),
              ),
              const SizedBox(width: Gap.m),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.heroName, style: Theme.of(context).textTheme.titleLarge),
                    Text(l.heroAbout, style: const TextStyle(color: Palette.parchmentDim, height: 1.35)),
                    const SizedBox(height: Gap.s),
                    Text(l.heroWalked(_num.format((hero.pos / 1000).round()), _num.format(totalSteps)),
                        style: const TextStyle(fontSize: 13)),
                    if (hero.deaths > 0)
                      Text(l.heroDeaths(hero.deaths), style: const TextStyle(fontSize: 13, color: Palette.parchmentDim)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: Gap.l),
          SectionCard(
            child: Column(children: [
              StatBar(
                  label: l.statSatiety,
                  value: s['satiety']!,
                  color: Palette.satiety,
                  icon: Icons.restaurant,
                  danger: s['satiety']! < eng.dangerBelow),
              const SizedBox(height: Gap.s),
              StatBar(
                  label: l.statWater,
                  value: s['water']!,
                  color: Palette.water,
                  icon: Icons.water_drop_outlined,
                  danger: s['water']! < eng.dangerBelow),
              const SizedBox(height: Gap.s),
              StatBar(
                  label: l.statWarmth,
                  value: s['warmth']!,
                  color: Palette.warmth,
                  icon: Icons.local_fire_department_outlined,
                  danger: s['warmth']! < eng.dangerBelow),
              const SizedBox(height: Gap.s),
              Text(l.statsHint, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.35)),
            ]),
          ),
          const SizedBox(height: Gap.l),
          Row(children: [
            Expanded(child: Text(l.backpack, style: Theme.of(context).textTheme.titleMedium)),
            Text('${eng.consumablesCount()}/${eng.backpackSlots()}', style: const TextStyle(color: Palette.parchmentDim)),
            const SizedBox(width: Gap.m),
            const Icon(Icons.toll, size: 18, color: Palette.gold),
            const SizedBox(width: 4),
            Text('${hero.coins}'),
          ]),
          const SizedBox(height: Gap.s),
          if (consumables.isEmpty) Text(l.backpackEmpty, style: const TextStyle(color: Palette.parchmentDim)),
          for (final e in consumables)
            Padding(
              padding: const EdgeInsets.only(bottom: Gap.s),
              child: SectionCard(
                padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${c.content.itemName(e.key)} ×${e.value}', style: Theme.of(context).textTheme.titleSmall),
                      Text(itemEffectLine(l, eng, e.key), style: const TextStyle(color: Palette.teal, fontSize: 12)),
                    ]),
                  ),
                  TextButton(onPressed: () => c.useItem(e.key), child: Text(l.useItem)),
                ]),
              ),
            ),
          const SizedBox(height: Gap.m),
          Text(l.gear, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.s),
          if (gear.isEmpty) Text(l.gearEmpty, style: const TextStyle(color: Palette.parchmentDim)),
          for (final e in gear)
            Padding(
              padding: const EdgeInsets.only(bottom: Gap.s),
              child: SectionCard(
                padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(c.content.itemName(e.key), style: Theme.of(context).textTheme.titleSmall),
                  Text('${c.content.items[e.key]?['desc'] ?? ''}',
                      style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                  if (itemEffectLine(l, eng, e.key).isNotEmpty)
                    Text(itemEffectLine(l, eng, e.key), style: const TextStyle(color: Palette.teal, fontSize: 12)),
                ]),
              ),
            ),
        ],
      ),
    );
  }
}

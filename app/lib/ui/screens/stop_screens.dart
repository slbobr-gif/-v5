// Остановки на пути: событие, привал в городе, конец главы, смерть, финиш.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';

/// Показывает экран текущей остановки. Сам переключается, если остановка сменилась.
class StopScreen extends ConsumerStatefulWidget {
  const StopScreen({super.key});

  @override
  ConsumerState<StopScreen> createState() => _StopScreenState();
}

class _StopScreenState extends ConsumerState<StopScreen> {
  OutcomeView? _outcome;
  String? _outcomeTitle;
  String? _outcomeArt;

  @override
  Widget build(BuildContext context) {
    final m = ref.watch(appProvider);
    final hero = m.hero;
    if (_outcome != null) {
      return _OutcomeScreen(
        title: _outcomeTitle ?? '',
        art: _outcomeArt ?? 'road',
        outcome: _outcome!,
        onNext: () async {
          final o = _outcome;
          if (o == null) return; // двойное нажатие «Дальше»
          setState(() => _outcome = null);
          if (!o.died) await ref.read(appProvider.notifier).afterEvent();
        },
      );
    }
    final st = hero?.stop;
    if (hero == null || st == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
      });
      return const Scaffold(body: SizedBox.shrink());
    }
    switch (st['type']) {
      case 'event':
        return _EventScreen(
          onOutcome: (o, title, art) => setState(() {
            _outcome = o;
            _outcomeTitle = title;
            _outcomeArt = art;
          }),
        );
      case 'place':
        return const _PlaceScreen();
      case 'chapter_end':
        return const _ChapterEndScreen();
      case 'death':
        return const _DeathScreen();
      case 'finish':
        return const _FinishScreen();
    }
    return const Scaffold(body: SizedBox.shrink());
  }
}

String _itemsLine(AppController c, Map<String, int> items) =>
    items.entries.map((e) => e.value > 1 ? '${c.content.itemName(e.key)} ×${e.value}' : c.content.itemName(e.key)).join(', ');

// ---------------------------------------------------------------- событие

class _EventScreen extends ConsumerWidget {
  const _EventScreen({required this.onOutcome});
  final void Function(OutcomeView, String, String) onOutcome;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final eng = Engine(m.content!.world, m.hero!);
    final ev = eng.currentEvent();
    if (ev == null) return const Scaffold(body: SizedBox.shrink());
    final art = (ev['art'] as String?) ?? 'road';
    final creature = ev['creature'] as String?;
    final choices = (ev['choices'] as List).cast<Map>().map((x) => x.cast<String, dynamic>()).toList();
    final kindLabel = switch (ev['kind']) {
      'creature' => l.kindCreature,
      'chapter' => l.kindChapter,
      'companion' => l.kindCompanion,
      'regional' => l.kindRegional,
      _ => l.kindRandom,
    };
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 220,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  Art('assets/art/scenes/$art.svg'),
                  if (creature != null)
                    Positioned(
                      right: Gap.m,
                      bottom: Gap.m,
                      child: Container(
                        decoration: const BoxDecoration(shape: BoxShape.circle, color: Palette.ink),
                        padding: const EdgeInsets.all(4),
                        child: Art('assets/art/creatures/$creature.svg', width: 72, height: 72, fit: BoxFit.contain),
                      ),
                    ),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(Gap.l),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Text(kindLabel.toUpperCase(), style: const TextStyle(color: Palette.gold, fontSize: 12, letterSpacing: 1.5)),
                const SizedBox(height: Gap.xs),
                Text('${ev['title']}', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: Gap.m),
                StoryText('${ev['text']}'),
                const SizedBox(height: Gap.l),
                for (final ch in choices) ...[
                  _ChoiceButton(
                    choice: ch,
                    available: eng.choiceAvailable(ch),
                    risk: eng.choiceRisk(ch),
                    requirement: _requirementText(l, c, eng, ch),
                    onTap: () {
                      final o = c.choose('${ch['id']}');
                      if (o != null) onOutcome(o, '${ev['title']}', art);
                    },
                  ),
                  const SizedBox(height: Gap.s),
                ],
              ]),
            ),
          ),
        ],
      ),
    );
  }

  String? _requirementText(AppLocalizations l, AppController c, Engine eng, Json ch) {
    final req = (ch['requires'] as Map?)?.cast<String, dynamic>();
    if (req == null) return null;
    if (req['item'] != null) return l.needItem(c.content.itemName('${req['item']}'));
    if (req['coins'] != null) {
      final n = toI((eng.b['levels']['coins'] as Map)[req['coins']]);
      return l.needCoins(n);
    }
    if (req['flag'] != null) return l.needFlag;
    return null;
  }
}

class _ChoiceButton extends StatelessWidget {
  const _ChoiceButton({
    required this.choice,
    required this.available,
    required this.risk,
    required this.requirement,
    required this.onTap,
  });

  final Json choice;
  final bool available;
  final String risk;
  final String? requirement;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final (riskIcon, riskColor, riskLabel) = switch (risk) {
      'fatal' => (Icons.dangerous_outlined, Palette.danger, l.riskFatal),
      'high' => (Icons.warning_amber_rounded, Palette.ember, l.riskHigh),
      'low' => (Icons.info_outline, Palette.parchmentDim, l.riskLow),
      _ => (null, Palette.parchmentDim, ''),
    };
    return Opacity(
      opacity: available ? 1 : 0.45,
      child: SectionCard(
        highlighted: risk == 'fatal',
        onTap: available ? onTap : null,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${choice['text']}', style: Theme.of(context).textTheme.titleMedium),
                  if (requirement != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(requirement!, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                    ),
                  if (riskIcon != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Row(children: [
                        Icon(riskIcon, size: 16, color: riskColor),
                        const SizedBox(width: 4),
                        Text(riskLabel, style: TextStyle(color: riskColor, fontSize: 12)),
                      ]),
                    ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: available ? Palette.gold : Palette.parchmentDim),
          ],
        ),
      ),
    );
  }
}

class _OutcomeScreen extends ConsumerWidget {
  const _OutcomeScreen({required this.title, required this.art, required this.outcome, required this.onNext});

  final String title;
  final String art;
  final OutcomeView outcome;
  final Future<void> Function() onNext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final o = outcome;
    final chips = <Widget>[];
    Widget chip(IconData i, String t, Color col) => Chip(
          avatar: Icon(i, size: 16, color: col),
          label: Text(t),
          backgroundColor: Palette.inkRaised,
          side: const BorderSide(color: Palette.inkHigh),
        );
    String signed(int v) => v > 0 ? '+$v' : '$v';
    if (o.coins != 0) chips.add(chip(Icons.toll, l.fxCoins(signed(o.coins)), Palette.gold));
    final statNames = {'satiety': l.statSatiety, 'water': l.statWater, 'warmth': l.statWarmth};
    o.stats.forEach((k, v) {
      if (v != 0) {
        chips.add(chip(v > 0 ? Icons.arrow_upward : Icons.arrow_downward, '${statNames[k]} ${signed(v)}',
            v > 0 ? Palette.teal : Palette.danger));
      }
    });
    if (o.itemsGained.isNotEmpty) chips.add(chip(Icons.add_box_outlined, l.fxGained(_itemsLine(c, o.itemsGained)), Palette.teal));
    if (o.itemsLost.isNotEmpty) chips.add(chip(Icons.indeterminate_check_box_outlined, l.fxLost(_itemsLine(c, o.itemsLost)), Palette.danger));
    if (o.delayHours > 0) chips.add(chip(Icons.hourglass_bottom, l.fxDelay(o.delayHours.ceil()), Palette.ember));
    if (o.detourKm > 0) chips.add(chip(Icons.alt_route, l.fxDetour(o.detourKm.toStringAsFixed(0)), Palette.ember));
    if (o.shortcutKm > 0) chips.add(chip(Icons.fast_forward, l.fxShortcut(o.shortcutKm.toStringAsFixed(1)), Palette.teal));
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(Gap.radius),
              child: Art('assets/art/scenes/$art.svg', height: 140),
            ),
            const SizedBox(height: Gap.m),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: Gap.m),
            StoryText(o.text),
            const SizedBox(height: Gap.m),
            if (chips.isNotEmpty) Wrap(spacing: Gap.s, runSpacing: Gap.s, children: chips),
            if (o.died) ...[
              const SizedBox(height: Gap.m),
              Text(l.fxDied, style: const TextStyle(color: Palette.danger)),
            ],
            const SizedBox(height: Gap.l),
            FilledButton(onPressed: onNext, child: Text(l.next)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- привал

class _PlaceScreen extends ConsumerWidget {
  const _PlaceScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final eng = Engine(m.content!.world, m.hero!);
    final st = m.hero!.stop!;
    final place = m.content!.world.placeById['${st['place']}'] ?? const <String, dynamic>{};
    final offers = eng.market();
    final art = switch (place['kind']) {
      'city' => 'town',
      'town' => 'town',
      'roadside' => 'road',
      _ => 'village',
    };
    final desc = (place['desc'] as String?)?.isNotEmpty == true ? place['desc'] as String : l.roadsideDesc;
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(background: Art('assets/art/scenes/$art.svg')),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(Gap.l),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Text(l.stopPlace.toUpperCase(), style: const TextStyle(color: Palette.gold, fontSize: 12, letterSpacing: 1.5)),
                Text('${place['name']}', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: Gap.s),
                StoryText(desc),
                const SizedBox(height: Gap.s),
                Text(l.placeRest, style: const TextStyle(color: Palette.teal)),
                const SizedBox(height: Gap.l),
                Row(children: [
                  Expanded(child: Text(l.market, style: Theme.of(context).textTheme.titleMedium)),
                  const Icon(Icons.toll, color: Palette.gold, size: 18),
                  const SizedBox(width: 4),
                  Text('${m.hero!.coins}'),
                  const SizedBox(width: Gap.m),
                  const Icon(Icons.backpack_outlined, color: Palette.parchmentDim, size: 18),
                  const SizedBox(width: 4),
                  Text('${eng.consumablesCount()}/${eng.backpackSlots()}'),
                ]),
                const SizedBox(height: Gap.s),
                if (offers.isEmpty) Text(l.marketEmpty, style: const TextStyle(color: Palette.parchmentDim)),
                for (final o in offers) ...[
                  _OfferRow(
                    name: c.content.itemName(o.item),
                    desc: '${c.content.items[o.item]?['desc'] ?? ''}',
                    effect: itemEffectLine(l, eng, o.item),
                    price: o.price,
                    have: m.hero!.inv[o.item] ?? 0,
                    blocker: eng.buyBlocker(o.item),
                    onBuy: () => c.buy(o.item),
                  ),
                  const SizedBox(height: Gap.s),
                ],
                const SizedBox(height: Gap.l),
                FilledButton(
                  onPressed: () async {
                    await c.continueJourney(st);
                  },
                  child: Text(l.goOn),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

/// «+30 сытости, +10 тепла» и т. п. для предмета.
String itemEffectLine(AppLocalizations l, Engine eng, String item) {
  final w = eng.w;
  final parts = <String>[];
  final names = {'satiety': l.statSatiety, 'water': l.statWater, 'warmth': l.statWarmth};
  for (final k in ['satiety', 'water', 'warmth']) {
    final v = w.itemValue(item, k);
    if (v > 0) parts.add('+${v.round()} ${names[k]!.toLowerCase()}');
  }
  if (w.itemValue(item, 'warmthDrainMult') > 0) parts.add(l.gearSocks);
  if (w.itemValue(item, 'weatherWarmthMult') > 0) parts.add(l.gearRaincoat);
  if (w.itemValue(item, 'riskReduce') > 0) parts.add(l.gearAmulet);
  return parts.join(', ');
}

class _OfferRow extends StatelessWidget {
  const _OfferRow({
    required this.name,
    required this.desc,
    required this.effect,
    required this.price,
    required this.have,
    required this.blocker,
    required this.onBuy,
  });

  final String name;
  final String desc;
  final String effect;
  final int price;
  final int have;
  final String? blocker;
  final VoidCallback onBuy;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final reason = switch (blocker) {
      'no_coins' => l.buyNoCoins,
      'backpack_full' => l.buyFull,
      'have_gear' => l.buyHave,
      _ => null,
    };
    return SectionCard(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(have > 0 ? '$name  ·  ${l.inBackpack(have)}' : name,
                    style: Theme.of(context).textTheme.titleSmall),
                if (effect.isNotEmpty) Text(effect, style: const TextStyle(color: Palette.teal, fontSize: 12)),
                Text(desc, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                if (reason != null) Text(reason, style: const TextStyle(color: Palette.ember, fontSize: 12)),
              ],
            ),
          ),
          const SizedBox(width: Gap.s),
          FilledButton.tonal(
            style: FilledButton.styleFrom(minimumSize: const Size(72, 40)),
            onPressed: blocker == null ? onBuy : null,
            child: Text('$price'),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- конец главы

class _ChapterEndScreen extends ConsumerWidget {
  const _ChapterEndScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final w = m.content!.world;
    final st = m.hero!.stop!;
    final chId = toI(st['chapter']);
    final ch = w.chapterById(chId);
    final next = w.chapters.where((x) => toI(x['id']) == chId + 1).firstOrNull;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            Text(l.chapterDone(chId), style: const TextStyle(color: Palette.gold, letterSpacing: 1.5)),
            Text('${ch['title']}', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: Gap.l),
            StoryText('${ch['outro'] ?? ''}'),
            // Финал главы зависит от прошлых решений: абзацы по флагам героя
            for (final e in ((ch['outro_flags'] as Map?) ?? const {}).entries)
              if (m.hero!.flags.contains(e.key)) ...[
                const SizedBox(height: Gap.m),
                StoryText('${e.value}'),
              ],
            if (next != null) ...[
              const SizedBox(height: Gap.xl),
              Text(l.chapterLabel(toI(next['id'])), style: const TextStyle(color: Palette.gold, letterSpacing: 1.5)),
              Text('${next['title']}', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: Gap.s),
              StoryText('${next['intro'] ?? ''}'),
              if (next['playable'] != true) ...[
                const SizedBox(height: Gap.m),
                Text(l.chapterComingSoon, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
              ],
            ],
            const SizedBox(height: Gap.l),
            FilledButton(onPressed: () => c.continueJourney(st), child: Text(l.next)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- смерть

class _DeathScreen extends ConsumerWidget {
  const _DeathScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.hero!.stop!;
    final place = c.content.placeName('${st['place']}');
    final cause = st['cause'] == 'event' ? l.deathCauseEvent : l.deathCauseStats;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(Gap.radius),
              child: const Art('assets/art/scenes/night.svg', height: 180),
            ),
            const SizedBox(height: Gap.l),
            Text(l.deathTitle, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: Gap.m),
            StoryText(cause),
            const SizedBox(height: Gap.m),
            Text(
              l.deathDetails(place, '${st['back']}', toI(st['coinsLost'])),
              style: const TextStyle(color: Palette.parchmentDim, height: 1.4),
            ),
            const SizedBox(height: Gap.l),
            FilledButton(onPressed: () => c.dismissDeath(), child: Text(l.deathWake)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- финиш

class _FinishScreen extends ConsumerWidget {
  const _FinishScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(Gap.radius),
              child: const Art('assets/art/finale/teriberka.svg', height: 240),
            ),
            const SizedBox(height: Gap.l),
            Text(l.finishTitle, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: Gap.m),
            StoryText(l.finishText(m.hero!.daySteps.length, m.hero!.deaths)),
            const SizedBox(height: Gap.l),
            OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: Text(l.close)),
          ],
        ),
      ),
    );
  }
}

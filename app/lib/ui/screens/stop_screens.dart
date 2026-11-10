// Остановки на пути: событие, привал в городе, конец главы, смерть, финиш.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/coach_tour.dart';
import '../widgets/common.dart';
import '../widgets/gift_button.dart';
import '../widgets/item_icon.dart';
import '../widgets/spirit_card.dart';
import 'chapter_end_flow.dart';
import 'finale_flow.dart';
import 'overflow_screens.dart';
import 'paywall_screen.dart';

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
          // Вещи в очереди переполнения: advance героя не двигает, но снимает undo («Сучок»/«Бусина»
          // уже не нужны) — иначе после решения контроллер не повёл бы героя дальше (_afterOverflow ждёт undo == null).
          if (!o.died) await ref.read(appProvider.notifier).afterEvent();
        },
      );
    }
    if (hero != null && hero.overflow.isNotEmpty) return const OverflowScreen();
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
        return const ChapterEndFlow();
      case 'death':
        return const _DeathScreen();
      case 'finish':
        return const FinaleFlow();
      case 'night':
        return const _NightScreen();
    }
    return const Scaffold(body: SizedBox.shrink());
  }
}

/// Нижний отступ содержимого остановок: системная навигация Android + запас (баг п. 30).
EdgeInsets _listPadding(BuildContext context) =>
    EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, safeBottom(context) + Gap.m);

String _toneLabel(AppLocalizations l, String tone) => switch (tone) {
      'reward' => l.gearTone_reward,
      'penalty' => l.gearTone_penalty,
      'mixed' => l.gearTone_mixed,
      'risk' => l.gearTone_risk,
      'death' => l.gearTone_death,
      _ => l.gearTone_neutral,
    };

/// Цвет и значок тона: награда — бирюза, наказание — коралл, смешанно/риск/ничего — нейтральный, смерть — красный.
(Color, IconData) _toneStyle(String tone) => switch (tone) {
      'reward' => (Palette.accent, Icons.card_giftcard_outlined),
      'penalty' => (Palette.ember, Icons.trending_down),
      'mixed' => (Palette.parchmentDim, Icons.swap_vert),
      'risk' => (Palette.parchmentDim, Icons.casino_outlined),
      'death' => (Palette.danger, Icons.dangerous_outlined),
      _ => (Palette.parchmentDim, Icons.remove),
    };

// ---------------------------------------------------------------- событие

class _EventScreen extends ConsumerStatefulWidget {
  const _EventScreen({required this.onOutcome});
  final void Function(OutcomeView, String, String) onOutcome;

  @override
  ConsumerState<_EventScreen> createState() => _EventScreenState();
}

class _EventScreenState extends ConsumerState<_EventScreen> {
  /// Ответ клубка для события с этим id (в состоянии героя не хранится).
  String? _tonesFor;
  Map<String, String>? _tones;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final eng = Engine(m.content!.world, m.hero!);
    final ev = eng.currentEvent();
    if (ev == null) return const Scaffold(body: SizedBox.shrink());
    final evId = '${ev['id']}';
    final tones = _tonesFor == evId ? _tones : null;
    final art = (ev['art'] as String?) ?? 'road';
    final choices = (ev['choices'] as List).cast<Map>().map((x) => x.cast<String, dynamic>()).toList();
    final kindLabel = switch (ev['kind']) {
      'creature' => l.kindCreature,
      'chapter' => l.kindChapter,
      'companion' => l.kindCompanion,
      'regional' => l.kindRegional,
      _ => l.kindRandom,
    };
    final clew = c.clewStatus();
    // Чей голос подскажет: клубок, нитка или дар духа «своих» мест (§13.5).
    final clewItem = eng.clewItem(DateTime.now().millisecondsSinceEpoch);
    final firstRisky = choices.indexWhere((ch) => ((ch['risk'] as String?) ?? 'none') != 'none');
    final tips = <CoachStep>[
      if (firstRisky >= 0) CoachStep(id: 'risk', anchor: 'risk', title: l.tourStep6Title, body: l.tourStep6Body),
    ];
    return CoachHost(
      tips: tips,
      child: Scaffold(
        body: CustomScrollView(
          slivers: [
            SliverAppBar(
              expandedHeight: 220,
              pinned: true,
              flexibleSpace: FlexibleSpaceBar(background: SpiritArt(event: ev)),
            ),
            SliverPadding(
              padding: _listPadding(context),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  Text(kindLabel.toUpperCase(),
                      style: const TextStyle(color: Palette.accent, fontSize: 12, letterSpacing: 1.5)),
                  const SizedBox(height: Gap.xs),
                  Text('${ev['title']}', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: Gap.m),
                  StoryText('${ev['text']}'),
                  const SizedBox(height: Gap.l),
                  if (clew == 'ready' || clew == 'cooldown' || clew == 'not_here') ...[
                    _ClewRow(
                      item: clewItem ?? 'ball_yaga',
                      label: clewAskLabel(l, clewItem),
                      notHere: clew == 'not_here',
                      ready: clew == 'ready' && tones == null,
                      cooldownDays: clew == 'cooldown' ? c.clewCooldownDays() : 0,
                      onAsk: () {
                        final r = c.askClew();
                        if (r != null) {
                          setState(() {
                            _tonesFor = evId;
                            _tones = r;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: Gap.m),
                  ],
                  for (var i = 0; i < choices.length; i++) ...[
                    _ChoiceButton(
                      choice: choices[i],
                      available: eng.choiceAvailable(choices[i]),
                      risk: eng.choiceRisk(choices[i]),
                      riskAnchor: i == firstRisky,
                      tone: tones?['${choices[i]['id']}'],
                      requirement: _requirementText(l, c, eng, choices[i]),
                      onTap: () {
                        final o = c.choose('${choices[i]['id']}');
                        if (o != null) widget.onOutcome(o, '${ev['title']}', art);
                      },
                    ),
                    const SizedBox(height: Gap.s),
                  ],
                ]),
              ),
            ),
          ],
        ),
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

/// «Спросить клубок» и «Клубок отдыхает N дн.».
class _ClewRow extends StatelessWidget {
  const _ClewRow({
    required this.item,
    required this.label,
    required this.notHere,
    required this.ready,
    required this.cooldownDays,
    required this.onAsk,
  });

  final String item;
  final String label;
  final bool notHere;
  final bool ready;
  final int cooldownDays;
  final VoidCallback onAsk;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Row(children: [
      ItemIcon(item, size: 36),
      const SizedBox(width: Gap.s + 4),
      Expanded(
        child: ready
            ? Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44), foregroundColor: Palette.accent),
                  onPressed: onAsk,
                  child: Text(label),
                ),
              )
            : Text(
                notHere ? l.gearClewNotHere : (cooldownDays > 0 ? l.gearClewCooldown(cooldownDays) : label),
                style: const TextStyle(color: Palette.parchmentDim, fontSize: 13),
              ),
      ),
    ]);
  }
}

class _ChoiceButton extends StatelessWidget {
  const _ChoiceButton({
    required this.choice,
    required this.available,
    required this.risk,
    required this.riskAnchor,
    required this.tone,
    required this.requirement,
    required this.onTap,
  });

  final Json choice;
  final bool available;
  final String risk;
  final bool riskAnchor;
  final String? tone;
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
    Widget? riskRow;
    if (riskIcon != null) {
      riskRow = Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(riskIcon, size: 16, color: riskColor),
        const SizedBox(width: 4),
        Flexible(child: Text(riskLabel, style: TextStyle(color: riskColor, fontSize: 12))),
      ]);
      if (riskAnchor) riskRow = TourAnchor(id: 'risk', child: riskRow);
    }
    final t = tone;
    Widget? toneRow;
    if (t != null) {
      final (col, ic) = _toneStyle(t);
      toneRow = Container(
        margin: const EdgeInsets.only(top: 4),
        padding: const EdgeInsets.symmetric(horizontal: Gap.s, vertical: 2),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: col),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 14, color: col),
          const SizedBox(width: 4),
          Text(_toneLabel(l, t), style: TextStyle(color: col, fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
      );
    }
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
                  if (riskRow != null) Padding(padding: const EdgeInsets.only(top: 4), child: riskRow),
                  if (toneRow != null) toneRow,
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: available ? Palette.accent : Palette.parchmentDim),
          ],
        ),
      ),
    );
  }
}

/// Предметы исхода: значок, имя, «×N».
class _ItemChips extends ConsumerWidget {
  const _ItemChips({required this.items, required this.color, required this.prefix});

  final Map<String, int> items;
  final Color color;
  final String prefix;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.read(appProvider);
    final content = m.content!;
    return Wrap(
      spacing: Gap.s,
      runSpacing: Gap.s,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text(prefix, style: TextStyle(color: color, fontSize: 13)),
        for (final e in items.entries)
          Chip(
            avatar: ItemIcon(e.key, size: 24, type: content.world.itemType(e.key)),
            label: Text(e.value > 1 ? l.gearPortions(content.itemName(e.key), e.value) : content.itemName(e.key)),
            backgroundColor: Palette.chipBg,
            side: BorderSide(color: color.withAlpha(120)),
          ),
      ],
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
    final o = outcome;
    final chips = <Widget>[];
    Widget chip(IconData i, String t, Color col) => Chip(
          avatar: Icon(i, size: 16, color: col),
          label: Text(t),
          backgroundColor: Palette.chipBg,
          side: const BorderSide(color: Palette.chipLine),
        );
    String signed(int v) => v > 0 ? '+$v' : '$v';
    if (o.coins != 0) chips.add(chip(Icons.toll, l.fxCoins(signed(o.coins)), Palette.accent));
    final statNames = {'satiety': l.statSatiety, 'water': l.statWater, 'warmth': l.statWarmth};
    o.stats.forEach((k, v) {
      if (v != 0) {
        chips.add(chip(v > 0 ? Icons.arrow_upward : Icons.arrow_downward, '${statNames[k]} ${signed(v)}',
            v > 0 ? Palette.accent : Palette.danger));
      }
    });
    if (o.delayHours > 0) chips.add(chip(Icons.hourglass_bottom, l.fxDelay(o.delayHours.ceil()), Palette.ember));
    if (o.detourKm > 0) chips.add(chip(Icons.alt_route, l.fxDetour(o.detourKm.toStringAsFixed(0)), Palette.ember));
    if (o.shortcutKm > 0) chips.add(chip(Icons.fast_forward, l.fxShortcut(o.shortcutKm.toStringAsFixed(1)), Palette.accent));
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: ListView(
          padding: _listPadding(context),
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
            if (o.itemsGained.isNotEmpty) ...[
              const SizedBox(height: Gap.s),
              _ItemChips(items: o.itemsGained, color: Palette.accent, prefix: l.fxGained('').trim()),
            ],
            if (o.itemsLost.isNotEmpty) ...[
              const SizedBox(height: Gap.s),
              _ItemChips(items: o.itemsLost, color: Palette.danger, prefix: l.fxLost('').trim()),
            ],
            if (o.itemsPending.isNotEmpty) ...[
              const SizedBox(height: Gap.s),
              _ItemChips(items: o.itemsPending, color: Palette.ember, prefix: l.overflowPending),
            ],
            if (o.died) ...[
              const SizedBox(height: Gap.m),
              Text(l.fxDied, style: const TextStyle(color: Palette.danger)),
            ] else ...[
              // «Сучок»/«Бусина» отменяют вред этого исхода — только здесь, до «Дальше» (§13.4).
              const SizedBox(height: Gap.m),
              const GiftList(kinds: {'guide', 'mirage'}, hideNothing: true),
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
    final sells = eng.sellOffers();
    final locked = c.paywallAt(st);
    // Рынок по разделам: еда и питьё, снаряжение, прочее (спички, газ, грелки) — снаряжение не теряется в конце списка.
    String group(String id) => switch (eng.w.itemType(id)) {
          'food' || 'drink' => 'food',
          'gear' => 'gear',
          _ => 'other',
        };
    final groups = <(String, String)>[('food', l.marketFood), ('gear', l.marketGear), ('other', l.marketOther)];
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
            padding: _listPadding(context),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Text(l.stopPlace.toUpperCase(), style: const TextStyle(color: Palette.accent, fontSize: 12, letterSpacing: 1.5)),
                Text('${place['name']}', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: Gap.s),
                StoryText(desc),
                const SizedBox(height: Gap.s),
                Text(l.placeRest, style: const TextStyle(color: Palette.accent)),
                const SizedBox(height: Gap.l),
                Row(children: [
                  Expanded(child: Text(l.market, style: Theme.of(context).textTheme.titleMedium)),
                  const Icon(Icons.toll, color: Palette.accent, size: 18),
                  const SizedBox(width: 4),
                  Text('${m.hero!.coins}'),
                  const SizedBox(width: Gap.m),
                  const Icon(Icons.backpack_outlined, color: Palette.parchmentDim, size: 18),
                  const SizedBox(width: 4),
                  Text('${eng.consumablesCount()}/${eng.backpackSlots()}'),
                  const SizedBox(width: Gap.m),
                  const Icon(Icons.handyman_outlined, color: Palette.parchmentDim, size: 18),
                  const SizedBox(width: 4),
                  Text('${eng.gearUsed()}/${eng.gearSlots()}'),
                ]),
                const SizedBox(height: Gap.s),
                if (offers.isEmpty) Text(l.marketEmpty, style: const TextStyle(color: Palette.parchmentDim)),
                for (final (gid, gname) in groups)
                  if (offers.any((o) => group(o.item) == gid)) ...[
                    const SizedBox(height: Gap.s),
                    Text(gname.toUpperCase(),
                        style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, letterSpacing: 1.2)),
                    const SizedBox(height: Gap.s),
                    for (final o in offers.where((o) => group(o.item) == gid)) ...[
                      _OfferRow(
                        id: o.item,
                        type: eng.w.itemType(o.item),
                        name: c.content.itemName(o.item),
                        desc: '${c.content.items[o.item]?['desc'] ?? ''}',
                        effect: perksLine(l, eng.w, o.item),
                        price: o.price,
                        have: m.hero!.gear.contains(o.item) ? 1 : (m.hero!.inv[o.item] ?? 0),
                        blocker: eng.buyBlocker(o.item),
                        onBuy: () => c.buy(o.item),
                      ),
                      const SizedBox(height: Gap.s),
                    ],
                  ],
                if (sells.isNotEmpty) ...[
                  const SizedBox(height: Gap.l),
                  Text(l.gearSellTitle, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.s),
                  for (final so in sells) ...[
                    _SellRow(
                      id: so.$1,
                      type: eng.w.itemType(so.$1),
                      name: c.content.itemName(so.$1),
                      price: so.$2,
                      enabled: eng.sellBlocker(so.$1) == null,
                      onSell: () => c.sell(so.$1),
                    ),
                    const SizedBox(height: Gap.s),
                  ],
                ],
                // Дары «на привале»: веник, ключ, сноп, крючок.
                const SizedBox(height: Gap.m),
                const GiftList(kinds: {'action'}),
                const SizedBox(height: Gap.l),
                if (m.hero!.overflow.isNotEmpty) ...[
                  Text(l.overflowPending, style: const TextStyle(color: Palette.ember)),
                  const SizedBox(height: Gap.s),
                ],
                if (locked) ...[
                  Text(l.placeLockedHint, style: const TextStyle(color: Palette.accent, height: 1.4)),
                  const SizedBox(height: Gap.s),
                ],
                FilledButton(
                  onPressed: m.hero!.overflow.isNotEmpty
                      ? null
                      : () async {
                          // Конец бесплатной части пути (V5-52): шаги копятся, герой ждёт подписку.
                          if (c.paywallAt(st)) {
                            await openPaywall(context, ref, 'chapter');
                            return;
                          }
                          await c.continueJourney(st);
                        },
                  child: Text(locked ? l.goOnLocked : l.goOn),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

/// Продажа (жемчужина и др. с `sellPrice`): цена без наценки рынка.
class _SellRow extends StatelessWidget {
  const _SellRow({
    required this.id,
    required this.type,
    required this.name,
    required this.price,
    required this.enabled,
    required this.onSell,
  });

  final String id;
  final String type;
  final String name;
  final int price;
  final bool enabled;
  final VoidCallback onSell;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return SectionCard(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
      child: Row(children: [
        ItemIcon(id, size: 40, type: type),
        const SizedBox(width: Gap.s + 4),
        Expanded(child: Text(name, style: Theme.of(context).textTheme.titleSmall)),
        FilledButton.tonal(
          style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
          onPressed: enabled ? onSell : null,
          child: Text(l.gearSellAction(price)),
        ),
      ]),
    );
  }
}

class _OfferRow extends StatelessWidget {
  const _OfferRow({
    required this.id,
    required this.type,
    required this.name,
    required this.desc,
    required this.effect,
    required this.price,
    required this.have,
    required this.blocker,
    required this.onBuy,
  });

  final String id;
  final String type;
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
      'gear_full' => l.buyGearFull,
      'no_stove' => l.buyNoStove,
      'gas_full' => l.buyGasFull,
      _ => null,
    };
    return SectionCard(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
      child: Row(
        children: [
          ItemIcon(id, size: 40, type: type),
          const SizedBox(width: Gap.s + 4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(have > 0 ? '$name  ·  ${l.inBackpack(have)}' : name,
                    style: Theme.of(context).textTheme.titleSmall),
                if (effect.isNotEmpty) Text(effect, style: const TextStyle(color: Palette.accent, fontSize: 12)),
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

// ---------------------------------------------------------------- ночёвка (V5-45)

/// Ночёвка в пути показывается экраном исхода: тепло и утренний бонус чипами, «Дальше» — в путь теми же шагами.
class _NightScreen extends ConsumerWidget {
  const _NightScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.hero!.stop!;
    final gain = ((st['gain'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', toI(v)));
    final morning = switch ('${st['morning'] ?? ''}') {
      'quiet' => l.nightMorning_quiet,
      'stream' => l.nightMorning_stream,
      'berries' => l.nightMorning_berries,
      'sun' => l.nightMorning_sun,
      'dew' => l.nightMorning_dew,
      'nuts' => l.nightMorning_nuts,
      _ => '',
    };
    return _OutcomeScreen(
      title: l.nightTitle,
      art: 'night',
      outcome: OutcomeView(
        text: morning.isEmpty ? l.nightText : '${l.nightText}\n\n$morning',
        coins: 0,
        stats: gain,
        itemsGained: const {},
        itemsLost: const {},
        died: false,
        delayHours: 0,
        detourKm: 0,
        shortcutKm: 0,
      ),
      onNext: () => c.continueJourney(st),
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
    final death = (m.content!.world.balance['death'] as Map).cast<String, dynamic>();
    return CoachHost(
      tips: [
        CoachStep(
          id: 'death',
          anchor: 'death_details',
          title: l.tourStep8Title,
          body: l.tourStep8Body(toI(death['rollbackMinKm']), toI(death['rollbackMaxKm'])),
        ),
      ],
      child: Scaffold(
      body: SafeArea(
        bottom: false,
        child: ListView(
          padding: _listPadding(context),
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
            TourAnchor(
              id: 'death_details',
              child: Text(
                l.deathDetails(place, '${st['back']}', toI(st['coinsLost'])),
                style: const TextStyle(color: Palette.parchmentDim, height: 1.4),
              ),
            ),
            const SizedBox(height: Gap.l),
            FilledButton(onPressed: () => c.dismissDeath(), child: Text(l.deathWake)),
          ],
        ),
      ),
    ),
    );
  }
}

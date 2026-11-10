// Покупка монет (V5-58): три набора. Оплаты пока нет — в тестовой сборке монеты начисляются сразу.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'overflow_screens.dart' show safeBottom;

/// [from] — откуда открыли: market, hero.
Future<void> openCoinShop(BuildContext context, WidgetRef ref, String from) {
  ref.read(appProvider.notifier).coinShopShown(from);
  return Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const CoinShopScreen()));
}

class CoinShopScreen extends ConsumerWidget {
  const CoinShopScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final coins = m.hero?.coins ?? 0;
    return Scaffold(
      appBar: AppBar(
        title: Text(l.coinShopTitle),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: Gap.m),
            child: Row(children: [
              const Icon(Icons.toll, color: Palette.accent, size: 18),
              const SizedBox(width: 4),
              Text('$coins', style: const TextStyle(fontWeight: FontWeight.w600)),
            ]),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) + Gap.l),
          children: [
            StoryText(l.coinShopBody),
            const SizedBox(height: Gap.l),
            for (final p in c.coinPacks()) ...[
              SectionCard(
                child: Row(children: [
                  const Icon(Icons.toll, color: Palette.accent, size: 28),
                  const SizedBox(width: Gap.m),
                  Expanded(
                    child: Text(l.coinPackLabel(toI(p['coins'])),
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                  ),
                  FilledButton(
                    onPressed: () {
                      final got = c.buyCoinsTest('${p['id']}');
                      if (got > 0) {
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.coinTestDone(got))));
                      }
                    },
                    child: Text('${l.coinBuy} · ${l.coinPackPrice(toI(p['rub']))}'),
                  ),
                ]),
              ),
              const SizedBox(height: Gap.s),
            ],
            if (AppController.testPurchases) ...[
              const SizedBox(height: Gap.m),
              Text(l.coinShopTest, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.4)),
            ],
          ],
        ),
      ),
    );
  }
}

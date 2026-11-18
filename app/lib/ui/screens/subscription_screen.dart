// Управление подпиской (V5-63): статус, что входит, переход в RuStore (подписки, история платежей),
// восстановление покупок и как отменить. Отмена и смена карты — только в RuStore: деньги списывает он.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'overflow_screens.dart' show safeBottom;
import 'paywall_screen.dart';

void openSubscription(BuildContext context, WidgetRef ref) {
  ref.read(appProvider.notifier).screen('subscription');
  Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SubscriptionScreen()));
}

class SubscriptionScreen extends ConsumerWidget {
  const SubscriptionScreen({super.key});

  Future<void> _open(BuildContext context, WidgetRef ref, String target) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final how = await ref.read(appProvider.notifier).openStore(target);
    if (how == 'web' && target != 'help') {
      messenger.showSnackBar(SnackBar(content: Text(l.subNoRustore)));
    } else if (how == 'none') {
      messenger.showSnackBar(SnackBar(content: Text(l.subCantOpen)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final premium = c.premium;
    const muted = TextStyle(color: Palette.parchmentDim, height: 1.4);
    return Scaffold(
      appBar: AppBar(title: Text(l.subTitle)),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) + Gap.l),
          children: [
            // Статус
            SectionCard(
              highlighted: premium,
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(premium ? Icons.verified_outlined : Icons.lock_outline, color: Palette.accent, size: 28),
                const SizedBox(width: Gap.m),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(premium ? l.subStatusActive : l.subStatusFree,
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: Gap.xs),
                    Text(premium ? l.subStatusActiveSub : l.subStatusFreeSub, style: muted),
                  ]),
                ),
              ]),
            ),
            const SizedBox(height: Gap.m),
            if (!premium)
              FilledButton(
                onPressed: () => openPaywall(context, ref, 'settings'),
                child: Text(l.paywallBuy),
              ),
            SectionHeader(l.subIncluded),
            for (final (icon, text) in [
              (Icons.map_outlined, l.paywallPointChapters),
              (Icons.wb_twilight, l.paywallPointThoughts),
              (Icons.directions_walk, l.paywallPointSteps),
            ]) ...[
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(icon, color: Palette.accent, size: 20),
                const SizedBox(width: Gap.s),
                Expanded(child: Text(text, style: const TextStyle(height: 1.4))),
              ]),
              const SizedBox(height: Gap.s),
            ],
            SectionHeader(l.subManage),
            _Tile(
              icon: Icons.manage_accounts_outlined,
              title: l.subOpenRustore,
              subtitle: l.subOpenRustoreSub,
              onTap: () => _open(context, ref, 'subscriptions'),
            ),
            _Tile(
              icon: Icons.receipt_long_outlined,
              title: l.subPayments,
              subtitle: l.subPaymentsSub,
              onTap: () => _open(context, ref, 'payments'),
            ),
            _Tile(
              icon: Icons.restore,
              title: l.subRestore,
              subtitle: l.subRestoreSub,
              external: false,
              onTap: () {
                c.restorePurchases();
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.paywallSoon)));
              },
            ),
            SectionHeader(l.subHowTitle),
            SectionCard(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(l.subHowCancel, style: muted),
                const SizedBox(height: Gap.s),
                Text(l.subHowResume, style: muted),
                const SizedBox(height: Gap.s),
                Text(l.subHowUninstall, style: muted),
                const SizedBox(height: Gap.s),
                Text(l.subHowRefund, style: muted),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(onPressed: () => _open(context, ref, 'help'), child: Text(l.subHelp)),
                ),
              ]),
            ),
            if (AppController.testBuild) ...[
              SectionHeader(l.settingsPremiumTest),
              SectionCard(
                padding: EdgeInsets.zero,
                child: SwitchListTile(
                  value: premium,
                  title: Text(l.settingsPremiumTest),
                  subtitle: Text(l.settingsPremiumTestSub),
                  onChanged: (bool v) => c.setPremiumTest(v),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.icon, required this.title, required this.subtitle, required this.onTap, this.external = true});
  final bool external;
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Gap.s),
      child: SectionCard(
        padding: EdgeInsets.zero,
        child: ListTile(
          leading: Icon(icon, color: Palette.accent),
          title: Text(title),
          subtitle: Text(subtitle, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13)),
          trailing: external ? const Icon(Icons.open_in_new, size: 18, color: Palette.parchmentDim) : null,
          onTap: onTap,
        ),
      ),
    );
  }
}

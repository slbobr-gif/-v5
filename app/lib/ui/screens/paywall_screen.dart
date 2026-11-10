// Экран подписки (V5-52): бесплатна первая глава и первые 14 мыслей.
// Оплаты пока нет (RuStore — следующий шаг): кнопка объясняет это, в тестовой сборке подписку включает настройка.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'overflow_screens.dart' show safeBottom;

/// [from] — откуда пришли: chapter (конец бесплатного пути), thought (закрытая мысль), steps (ручной ввод шагов).
Future<void> openPaywall(BuildContext context, WidgetRef ref, String from) {
  ref.read(appProvider.notifier).paywallShown(from);
  return Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PaywallScreen(from: from)));
}

class PaywallScreen extends ConsumerWidget {
  const PaywallScreen({super.key, required this.from});
  final String from;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final hero = m.hero;
    final st = hero?.stop;
    final place = st == null ? '' : c.content.placeName('${st['place'] ?? ''}');
    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) + Gap.l),
          children: [
            const Icon(Icons.lock_open_outlined, color: Palette.accent, size: 40),
            const SizedBox(height: Gap.m),
            Text(l.paywallTitle, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: Gap.s),
            StoryText(l.paywallBody),
            const SizedBox(height: Gap.l),
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
            if (from == 'chapter' && place.isNotEmpty) ...[
              const SizedBox(height: Gap.m),
              SectionCard(
                child: Text(l.paywallWaiting(place),
                    style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
              ),
            ],
            const SizedBox(height: Gap.xl),
            FilledButton(
              onPressed: () {
                c.paywallTap(from);
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.paywallSoon)));
              },
              child: Text(l.paywallBuy),
            ),
            const SizedBox(height: Gap.s),
            TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(l.paywallLater)),
          ],
        ),
      ),
    );
  }
}

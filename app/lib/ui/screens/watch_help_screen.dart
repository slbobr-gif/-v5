// Подсказка «Как подключить часы и браслеты»: Samsung, Xiaomi, Huawei, Apple и приоритет источников
// в Health Connect. Открывается из настроек (Откуда брать шаги) и из шага онбординга про Health Connect.

import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';

class WatchHelpScreen extends StatelessWidget {
  const WatchHelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final bottom = MediaQuery.paddingOf(context).bottom;
    final items = <(IconData, String, String)>[
      (Icons.watch_outlined, l.watchSamsungTitle, l.watchSamsungBody),
      (Icons.watch_outlined, l.watchXiaomiTitle, l.watchXiaomiBody),
      (Icons.watch_outlined, l.watchOtherTitle, l.watchOtherBody),
      (Icons.sync_problem_outlined, l.watchHuaweiTitle, l.watchHuaweiBody),
      (Icons.block_outlined, l.watchAppleTitle, l.watchAppleBody),
      (Icons.low_priority, l.watchPriorityTitle, l.watchPriorityBody),
      // V5-54: ручной ввод шагов за сегодня и вчера (подписка).
      (Icons.edit_outlined, l.watchManualTitle, l.watchManualBody),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(l.watchHelpTitle)),
      body: ListView(
        padding: EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, Gap.l + bottom),
        children: [
          Text(l.watchHelpIntro, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
          for (final it in items) ...[
            const SizedBox(height: Gap.m),
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(it.$1, color: Palette.accent),
                      const SizedBox(width: Gap.s),
                      Expanded(child: Text(it.$2, style: Theme.of(context).textTheme.titleMedium)),
                    ],
                  ),
                  const SizedBox(height: Gap.s),
                  Text(it.$3, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
                ],
              ),
            ),
          ],
          const SizedBox(height: Gap.m),
          Text(l.watchHelpCheck, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.35)),
        ],
      ),
    );
  }
}

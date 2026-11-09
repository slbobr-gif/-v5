// Главная после финала: карточка с медалью (→ итог и медаль), постоянная карточка «Начать путь заново»,
// одноразовое сообщение «Путь пройден» и подтверждение нового пути.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../engine/journey_stats.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/finale_widgets.dart';
import 'finale_flow.dart';
import 'settings_screen.dart';

void _openSettings(BuildContext context) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));

void openFinaleReplay(BuildContext context) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const FinaleFlow(replay: true)));

/// Подтверждение «Начать путь заново?»: что сохранится и что начнётся с нуля.
Future<void> confirmRestart(BuildContext context, WidgetRef ref) async {
  final l = AppLocalizations.of(context);
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(l.restartTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l.restartText, style: const TextStyle(height: 1.45)),
          const SizedBox(height: Gap.s),
          Text(l.restartKeep, style: const TextStyle(color: Palette.parchmentDim, height: 1.45, fontSize: 13.5)),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(l.cancel)),
        FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.homeRestartButton)),
      ],
    ),
  );
  if (ok == true) await ref.read(appProvider.notifier).restartAfterFinish();
}

/// Сообщение «Путь пройден» — один раз, когда игрок закрыл финал и вернулся на главную.
Future<void> showDoneMessage(BuildContext context, WidgetRef ref) async {
  final l = AppLocalizations.of(context);
  final m = ref.read(appProvider);
  final hero = m.hero;
  if (hero == null) return;
  final s = journeyStats(m.content!.world, hero, today: ref.read(appProvider.notifier).today);
  await ref.read(uiFlagsProvider.notifier).update((f) => f.finishMsgShown = true);
  if (!context.mounted) return;
  Widget tip(IconData icon, String title, String text) => Container(
        margin: const EdgeInsets.only(top: Gap.s),
        padding: const EdgeInsets.all(12),
        decoration: cardDecoration(radius: Gap.radiusS),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Palette.accent, size: 22),
            const SizedBox(width: Gap.s),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(text, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.35)),
                ],
              ),
            ),
          ],
        ),
      );
  final action = await showDialog<String>(
    context: context,
    builder: (ctx) => Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.l),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Center(child: MedalFace(size: 76)),
              const SizedBox(height: Gap.s),
              Text(l.doneTitle, textAlign: TextAlign.center, style: Theme.of(ctx).textTheme.headlineSmall),
              Text('${l.medalPromise} ${l.medalPromiseDone}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Color(0xFFE8C15A), fontStyle: FontStyle.italic)),
              const SizedBox(height: Gap.m),
              Text(l.doneText(s.days, groupInt(s.steps)), style: const TextStyle(height: 1.45)),
              const SizedBox(height: 4),
              Text(l.doneCall, style: const TextStyle(fontWeight: FontWeight.w700, height: 1.45)),
              if (s.randomUnseen > 0) tip(Icons.map_outlined, l.doneUnseenTitle, l.doneUnseen(s.randomUnseen, s.randomTotal)),
              tip(Icons.directions_walk, l.doneRatioTitle, l.doneRatio),
              const SizedBox(height: Gap.s),
              Text(l.doneKeep, textAlign: TextAlign.center, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5)),
              const SizedBox(height: Gap.m),
              FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 48)),
                onPressed: () => Navigator.of(ctx).pop('restart'),
                child: Text(l.doneRestart),
              ),
              const SizedBox(height: Gap.s),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(onPressed: () => Navigator.of(ctx).pop('steps'), child: Text(l.doneSteps)),
                  ),
                  const SizedBox(width: Gap.s),
                  Expanded(child: OutlinedButton(onPressed: () => Navigator.of(ctx).pop(), child: Text(l.close))),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
  );
  if (!context.mounted) return;
  if (action == 'restart') await confirmRestart(context, ref);
  if (action == 'steps' && context.mounted) _openSettings(context);
}

/// Карточки главной после финала.
class FinishedCards extends ConsumerWidget {
  const FinishedCards({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final s = journeyStats(m.content!.world, m.hero!, today: c.today);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        InkWell(
          borderRadius: BorderRadius.circular(Gap.radius),
          onTap: () => openFinaleReplay(context),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: cardDecoration(),
            child: Row(
              children: [
                const MedalFace(size: 74),
                const SizedBox(width: Gap.m),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(l.doneTitle, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                      Text(l.medalPromise,
                          style: const TextStyle(color: Color(0xFFE8C15A), fontStyle: FontStyle.italic, fontSize: 13)),
                      const SizedBox(height: 4),
                      Text(
                        l.homeDoneLine(fmtKm(s.totalKm), l.statDays(s.days), groupInt(s.steps)),
                        style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5),
                      ),
                      const SizedBox(height: 6),
                      Text(l.homeDoneOpen, style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: Gap.s),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: cardDecoration(highlighted: true),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(Icons.replay, color: Palette.accent),
                  const SizedBox(width: Gap.s),
                  Text(l.doneRestart, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                ],
              ),
              const SizedBox(height: 6),
              Text(l.homeRestartText(s.randomUnseen), style: const TextStyle(height: 1.4)),
              const SizedBox(height: 4),
              Text(l.homeRestartKeep, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5)),
              const SizedBox(height: Gap.s),
              FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 46)),
                onPressed: () => confirmRestart(context, ref),
                child: Text(l.homeRestartButton),
              ),
              TextButton(
                onPressed: () => _openSettings(context),
                child: Text('${l.homeRatio(c.stepMul)} · ${l.homeRatioChange}'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

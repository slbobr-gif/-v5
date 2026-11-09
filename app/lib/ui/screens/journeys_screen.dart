// «Пройденные пути» (из Журнала): итоги прошлых путей из профиля; нажатие открывает медаль и достижения.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/finale_widgets.dart';
import 'finale_flow.dart' show MedalBody;

class JourneysScreen extends ConsumerWidget {
  const JourneysScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final list = ref.watch(appProvider).profile?.journeys ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(l.journalJourneys)),
      body: ListView(
        padding: const EdgeInsets.all(Gap.m),
        children: [
          for (final j in list.reversed)
            Padding(
              padding: const EdgeInsets.only(bottom: Gap.s),
              child: InkWell(
                borderRadius: BorderRadius.circular(Gap.radius),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                  builder: (_) => Scaffold(appBar: AppBar(), body: MedalBody(data: MedalData.fromJson(j))),
                )),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: cardDecoration(),
                  child: Row(
                    children: [
                      const MedalFace(size: 56),
                      const SizedBox(width: Gap.m),
                      Expanded(
                        child: Text(
                          l.journalJourneyLine(
                            fmtDay(l, '${j['startDay'] ?? ''}'),
                            fmtDay(l, '${j['endDay'] ?? ''}'),
                            l.statDays(MedalData.fromJson(j).days),
                          ),
                        ),
                      ),
                      const Icon(Icons.chevron_right, color: Palette.parchmentDim),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

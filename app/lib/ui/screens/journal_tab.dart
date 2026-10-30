// Журнал: «Дорога» (что случилось) и «Мысли на дороге» (утренние мысли и ответы игрока).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../engine/state.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'thought_screen.dart';

class JournalTab extends ConsumerWidget {
  const JournalTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.journalTitle),
          bottom: TabBar(tabs: [Tab(text: l.journalRoad), Tab(text: l.journalThoughts)]),
        ),
        body: const TabBarView(children: [_RoadLog(), _ThoughtsLog()]),
      ),
    );
  }
}

class _RoadLog extends ConsumerWidget {
  const _RoadLog();

  String? _line(AppLocalizations l, AppController c, JournalEntry e) {
    final d = e.data;
    switch (e.kind) {
      case 'event':
        return l.logEvent('${d['title']}', '${d['choice']}');
      case 'place':
        return l.logPlace(c.content.placeName('${d['place']}'));
      case 'death':
        return l.logDeath(c.content.placeName('${d['place']}'));
      case 'goal':
        return l.logGoal(toI(d['steps']), toI(d['coins']));
      case 'login':
        return l.logLogin(toI(d['coins']));
      case 'buy':
        return l.logBuy(c.content.itemName('${d['item']}'), toI(d['price']));
      case 'eat':
        return l.logEat(c.content.itemName('${d['item']}'));
      case 'quest_done':
        return l.logQuestDone;
      case 'detour_back':
        return l.logDetourBack;
      case 'finish':
        return l.logFinish;
    }
    return null;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final entries = m.hero!.journal.reversed.toList();
    final fmt = DateFormat('d MMM, HH:mm', 'ru');
    if (entries.isEmpty) {
      return Center(child: Padding(padding: const EdgeInsets.all(Gap.l), child: Text(l.journalEmpty)));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(Gap.m),
      itemCount: entries.length,
      separatorBuilder: (_, __) => const Divider(color: Palette.inkHigh, height: Gap.m),
      itemBuilder: (context, i) {
        final e = entries[i];
        final line = _line(l, c, e);
        if (line == null) return const SizedBox.shrink();
        final outcome = e.kind == 'event' ? '${e.data['outcome'] ?? ''}' : '';
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(fmt.format(DateTime.fromMillisecondsSinceEpoch(e.t)),
                style: const TextStyle(color: Palette.parchmentDim, fontSize: 11)),
            const SizedBox(height: 2),
            Text(line, style: TextStyle(color: e.kind == 'death' ? Palette.danger : null)),
            if (outcome.isNotEmpty) ...[
              const SizedBox(height: 4),
              StoryText(outcome, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.4)),
            ],
          ],
        );
      },
    );
  }
}

class _ThoughtsLog extends ConsumerWidget {
  const _ThoughtsLog();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final today = c.journeyDay();
    final answers = c.answers();
    return ListView.builder(
      padding: const EdgeInsets.all(Gap.m),
      itemCount: today,
      itemBuilder: (context, i) {
        final day = today - i;
        final t = c.content.thoughtForDay(day);
        final ans = answers['$day']?['text'] as String?;
        return Padding(
          padding: const EdgeInsets.only(bottom: Gap.s),
          child: SectionCard(
            onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ThoughtScreen(day: day))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(l.thoughtDay(day), style: const TextStyle(color: Palette.gold, fontSize: 12)),
              const SizedBox(height: 4),
              Text('«${t.quote}»', style: const TextStyle(fontStyle: FontStyle.italic)),
              if (ans != null && ans.isNotEmpty) ...[
                const SizedBox(height: Gap.s),
                Text(l.yourAnswer, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                Text(ans),
              ],
            ]),
          ),
        );
      },
    );
  }
}

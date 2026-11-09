// Конец главы: текст главы → статистика игрока с картой и «Поделиться» → переписка Сергея с Сашей → в путь.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../data/content_repository.dart';
import '../../engine/journey_stats.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/finale_widgets.dart';
import '../widgets/journey_map.dart';
import 'overflow_screens.dart' show safeBottom;

class ChapterEndFlow extends ConsumerStatefulWidget {
  const ChapterEndFlow({super.key});

  @override
  ConsumerState<ChapterEndFlow> createState() => _ChapterEndFlowState();
}

class _ChapterEndFlowState extends ConsumerState<ChapterEndFlow> {
  int _page = 0; // 0 — текст главы, 1 — статистика, 2 — переписка

  @override
  Widget build(BuildContext context) {
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final content = m.content!;
    final w = content.world;
    final hero = m.hero!;
    final st = hero.stop!;
    final chId = toI(st['chapter']);
    final stats = chapterStats(w, hero, chId);
    final chat = content.chats[chId];
    final next = w.chapters.where((x) => toI(x['id']) == chId + 1).firstOrNull;

    void go() {
      // следующий существующий экран; после переписки (или без неё) — дальше в путь
      var p = _page + 1;
      if (p == 1 && stats == null) p = 2;
      if (p == 2 && (chat == null || chat.messages.isEmpty)) p = 3;
      if (p >= 3) {
        c.continueJourney(st);
        return;
      }
      setState(() => _page = p);
    }

    return PopScope(
      canPop: _page == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _page = _page == 2 && stats == null ? 0 : _page - 1);
      },
      child: switch (_page) {
        0 => _StoryPage(chId: chId, next: next, onNext: go),
        1 => _StatsPage(content: content, stats: stats!, onNext: go),
        _ => _ChatPage(chat: chat!, nextTitle: next == null ? null : '${next['title']}', onNext: go),
      },
    );
  }
}

EdgeInsets _pad(BuildContext context) => EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m);

/// Нижние кнопки экрана: «Поделиться» (необязательно) и главная.
class _Bottom extends StatelessWidget {
  const _Bottom({required this.label, required this.onNext, this.onShare});

  final String label;
  final VoidCallback onNext;
  final VoidCallback? onShare;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) + Gap.s),
      child: Row(
        children: [
          if (onShare != null) ...[
            Expanded(
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(minimumSize: const Size(0, 48)),
                onPressed: onShare,
                icon: const Icon(Icons.ios_share, size: 18),
                label: Text(l.shareButton),
              ),
            ),
            const SizedBox(width: Gap.s),
          ],
          Expanded(
            child: FilledButton(
              style: FilledButton.styleFrom(minimumSize: const Size(0, 48)),
              onPressed: onNext,
              child: Text(label, textAlign: TextAlign.center),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- 1. текст главы

class _StoryPage extends ConsumerWidget {
  const _StoryPage({required this.chId, required this.next, required this.onNext});

  final int chId;
  final Json? next;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final w = m.content!.world;
    final ch = w.chapterById(chId);
    final nx = next;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: _pad(context),
                children: [
                  Text(l.chapterDone(chId), style: const TextStyle(color: Palette.accent, letterSpacing: 1.5)),
                  Text('${ch['title']}', style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: Gap.l),
                  StoryText('${ch['outro'] ?? ''}'),
                  // финал главы зависит от прошлых решений: абзацы по флагам героя
                  for (final e in ((ch['outro_flags'] as Map?) ?? const {}).entries)
                    if (m.hero!.flags.contains(e.key)) ...[
                      const SizedBox(height: Gap.m),
                      StoryText('${e.value}'),
                    ],
                  if (nx != null) ...[
                    const SizedBox(height: Gap.xl),
                    Text(l.chapterLabel(toI(nx['id'])), style: const TextStyle(color: Palette.accent, letterSpacing: 1.5)),
                    Text('${nx['title']}', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: Gap.s),
                    StoryText('${nx['intro'] ?? ''}'),
                    if (nx['playable'] != true) ...[
                      const SizedBox(height: Gap.m),
                      Text(l.chapterComingSoon, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
                    ],
                  ],
                ],
              ),
            ),
            _Bottom(label: l.next, onNext: onNext),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- 2. статистика главы

class _StatsPage extends StatelessWidget {
  const _StatsPage({required this.content, required this.stats, required this.onNext});

  final GameContent content;
  final ChapterStats stats;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final w = content.world;
    final ch = w.chapterById(stats.chapter);
    final s = stats;
    final rows = <(String, String)>[
      (l.statTime, l.statDays(s.days)),
      (l.statSteps, groupInt(s.steps)),
      (l.statDistance, l.statKm(fmtKm(s.distKm, digits: 1))),
      (l.statBestDay, s.bestDay == null ? l.statBestNone : l.statBest(groupInt(s.bestSteps), fmtDay(l, s.bestDay))),
      (l.statEncounters, '${s.events}'),
      (l.statFalls, '${s.deaths}'),
    ];
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: _pad(context),
                children: [
                  Text(l.statsChapterKicker(s.chapter).toUpperCase(),
                      style: const TextStyle(color: Palette.accent, letterSpacing: 1.5, fontSize: 12)),
                  Text('${ch['title']}', style: Theme.of(context).textTheme.headlineSmall),
                  Text('${content.placeName('${ch['from']}')} → ${content.placeName('${ch['to']}')}',
                      style: const TextStyle(color: Palette.parchmentDim)),
                  const SizedBox(height: Gap.m),
                  Container(
                    height: 190,
                    decoration: cardDecoration(color: const Color(0xFF0B1520)),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(Gap.radius),
                      child: JourneyMap(content: content, upTo: s.chapter, highlight: s.chapter),
                    ),
                  ),
                  const SizedBox(height: Gap.m),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Text(fmtKm(s.km), style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w700, height: 1)),
                      const SizedBox(width: Gap.s),
                      Text(l.statsKmChapter, style: const TextStyle(fontSize: 16)),
                    ],
                  ),
                  const SizedBox(height: Gap.s),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: s.share,
                      minHeight: 8,
                      color: Palette.accent,
                      backgroundColor: Palette.inkHigh,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Text(l.statsFrom, style: _tiny),
                      Expanded(
                        child: Text(l.statsProgress('${(s.share * 100).round()}', fmtKm(s.leftKm)),
                            textAlign: TextAlign.center, style: _tiny),
                      ),
                      Text(l.statsTo, style: _tiny),
                    ],
                  ),
                  const SizedBox(height: Gap.m),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
                    decoration: cardDecoration(),
                    child: Column(
                      children: [
                        for (var i = 0; i < rows.length; i++)
                          Container(
                            padding: const EdgeInsets.symmetric(vertical: 9),
                            decoration: BoxDecoration(
                              border: i == rows.length - 1 ? null : const Border(bottom: BorderSide(color: Palette.inkHigh)),
                            ),
                            child: Row(
                              children: [
                                Expanded(child: Text(rows[i].$1, style: const TextStyle(color: Palette.parchmentDim))),
                                Text(rows[i].$2, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            _Bottom(
              label: l.next,
              onNext: onNext,
              onShare: () => shareCardDialog(
                context,
                kind: 'chapter',
                card: _ChapterShareCard(content: content, stats: s),
                text: l.shareTextChapter(s.chapter, fmtKm(s.passedKm), shareLink()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

const _tiny = TextStyle(fontSize: 11, color: Palette.parchmentDim);

/// Карточка главы для соцсетей.
class _ChapterShareCard extends StatelessWidget {
  const _ChapterShareCard({required this.content, required this.stats});

  final GameContent content;
  final ChapterStats stats;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final ch = content.world.chapterById(stats.chapter);
    final s = stats;
    return ShareCardFrame(
      right: l.shareCardRoute,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: Gap.s),
          Text(l.shareCardChapter(s.chapter, '${ch['title']}'),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          Text('${content.placeName('${ch['from']}')} → ${content.placeName('${ch['to']}')} · ${l.statKm(fmtKm(s.km))}',
              style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
          SizedBox(height: 180, child: JourneyMap(content: content, upTo: s.chapter, highlight: s.chapter)),
          Row(
            children: [
              Expanded(child: StatFigure(value: l.statDaysShort(s.days), label: l.shareCardTime)),
              Expanded(child: StatFigure(value: groupInt(s.steps), label: l.shareCardSteps)),
              Expanded(child: StatFigure(value: l.statKm(fmtKm(s.distKm, digits: 1)), label: l.shareCardDistance)),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- 3. переписка с Сашей

class _ChatPage extends StatelessWidget {
  const _ChatPage({required this.chat, required this.nextTitle, required this.onNext});

  final ChapterChat chat;
  final String? nextTitle;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final name = l.chatName;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.l, Gap.m, Gap.l, Gap.s),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(colors: [Color(0xFFE5855D), Color(0xFFB07CE8)]),
                    ),
                    child: Text(name.isEmpty ? '' : name.substring(0, 1),
                        style: const TextStyle(color: Palette.ink, fontWeight: FontWeight.w700, fontSize: 17)),
                  ),
                  const SizedBox(width: Gap.s + 2),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                      Text(l.chatOnline, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                    ],
                  ),
                ],
              ),
            ),
            const Divider(height: 1, color: Palette.inkHigh),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.m, Gap.m, Gap.m, Gap.m),
                children: [
                  if (chat.time.isNotEmpty)
                    Center(
                      child: Container(
                        margin: const EdgeInsets.only(bottom: Gap.s),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: Palette.chipBg, borderRadius: BorderRadius.circular(10)),
                        child: Text(chat.time, style: const TextStyle(fontSize: 11, color: Palette.parchmentDim)),
                      ),
                    ),
                  for (final msg in chat.messages) _Bubble(text: msg.text, mine: msg.fromMe),
                ],
              ),
            ),
            _Bottom(label: nextTitle == null ? l.next : l.chatNext(nextTitle!), onNext: onNext),
          ],
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.text, required this.mine});

  final String text;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 7),
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.78),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: mine ? const Color(0xFF1F5C58) : Palette.inkRaised,
          border: mine ? null : Border.all(color: Palette.inkHigh),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(18),
            topRight: const Radius.circular(18),
            bottomLeft: Radius.circular(mine ? 18 : 4),
            bottomRight: Radius.circular(mine ? 4 : 18),
          ),
        ),
        child: Text(text, style: const TextStyle(fontSize: 14.5, height: 1.4)),
      ),
    );
  }
}

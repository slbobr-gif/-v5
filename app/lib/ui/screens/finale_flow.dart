// Финал пути: эпилог (5 экранов) → итог с картой → двусторонняя медаль → главная (там один раз
// всплывёт «Путь пройден»). С главной «Медаль и итог» открывает тот же поток с итога, без эпилога.

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

class FinaleFlow extends ConsumerStatefulWidget {
  const FinaleFlow({super.key, this.replay = false});

  /// true — открыт с главной после финала: сразу итог, «Дальше» на медали просто закрывает экран.
  final bool replay;

  @override
  ConsumerState<FinaleFlow> createState() => _FinaleFlowState();
}

class _FinaleFlowState extends ConsumerState<FinaleFlow> {
  late int _page; // 0..n-1 — эпилог, n — итог, n+1 — медаль
  bool _busy = false;

  List<Json> _epilogue(World w) =>
      [for (final p in (w.chapterById(w.chapters.length)['epilogue'] as List?) ?? const []) (p as Map).cast<String, dynamic>()];

  @override
  void initState() {
    super.initState();
    final w = ref.read(appProvider).content!.world;
    _page = widget.replay ? _epilogue(w).length : 0;
  }

  Future<void> _finish() async {
    if (_busy) return;
    setState(() => _busy = true);
    if (!widget.replay) {
      // остановка «финиш» снимается — StopScreen закроется сам и вернёт на главную
      await ref.read(appProvider.notifier).closeFinish();
      return;
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final m = ref.watch(appProvider);
    final content = m.content!;
    final w = content.world;
    final hero = m.hero!;
    final ep = _epilogue(w);
    final stats = journeyStats(w, hero, today: ref.read(appProvider.notifier).today);
    final first = widget.replay ? ep.length : 0;
    final n = ep.length;
    return PopScope(
      canPop: _page == first,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) setState(() => _page -= 1);
      },
      child: _page < n
          ? _EpiloguePage(
              key: ValueKey(_page),
              page: ep[_page],
              index: _page,
              count: n,
              stats: stats,
              onNext: () => setState(() => _page += 1),
            )
          : _page == n
              ? _SummaryPage(content: content, stats: stats, onNext: () => setState(() => _page += 1))
              : _MedalPage(data: MedalData.fromStats(stats), busy: _busy, onNext: _finish),
    );
  }
}

Widget _bottom(BuildContext context, {required String label, required VoidCallback? onNext, VoidCallback? onShare}) {
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
            child: Text(label),
          ),
        ),
      ],
    ),
  );
}

// ---------------------------------------------------------------- эпилог

class _EpiloguePage extends StatelessWidget {
  const _EpiloguePage({
    super.key,
    required this.page,
    required this.index,
    required this.count,
    required this.stats,
    required this.onNext,
  });

  final Json page;
  final int index;
  final int count;
  final JourneyStats stats;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    // {days} — дни пути игрока из итога, {km} — длина маршрута
    final text = '${page['text'] ?? ''}'
        .replaceAll('{days}', l.statDays(stats.days))
        .replaceAll('{km}', fmtKm(stats.totalKm));
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m),
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(Gap.radius),
                    child: const Art('assets/art/finale/teriberka.svg', height: 180, width: double.infinity),
                  ),
                  const SizedBox(height: Gap.m),
                  Text(l.epilogueTitle, style: const TextStyle(color: Palette.accent, letterSpacing: 2)),
                  Text('${page['title'] ?? ''}', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: Gap.m),
                  StoryText(text, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.55, fontSize: 17)),
                ],
              ),
            ),
            Text('${index + 1} / $count', style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
            _bottom(context, label: l.next, onNext: onNext),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- итог

class _SummaryPage extends StatelessWidget {
  const _SummaryPage({required this.content, required this.stats, required this.onNext});

  final GameContent content;
  final JourneyStats stats;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = stats;
    final w = content.world;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m),
                children: [
                  Text(l.finKicker.toUpperCase(), style: const TextStyle(color: Palette.accent, letterSpacing: 1.5, fontSize: 12)),
                  Text(l.finTitle, style: Theme.of(context).textTheme.headlineSmall),
                  Text(l.finDates(fmtDay(l, s.startDay), fmtDay(l, s.endDay)), style: const TextStyle(color: Palette.parchmentDim)),
                  const SizedBox(height: Gap.m),
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                    decoration: cardDecoration(),
                    child: Row(
                      children: [
                        Expanded(child: StatFigure(value: '${s.days}', label: l.finDaysLabel(s.days), center: true, size: 19)),
                        Expanded(child: StatFigure(value: groupInt(s.steps), label: l.finStepsLabel, center: true, size: 19)),
                        Expanded(
                          child: StatFigure(value: l.statKm(fmtKm(s.distKm)), label: l.finDistLabel, center: true, size: 19),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: Gap.s),
                  _SummaryCard(content: content, stats: s),
                  const SizedBox(height: Gap.s),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: cardDecoration(),
                    child: Column(
                      children: [
                        for (final c in s.chapters)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 5),
                            child: Row(
                              children: [
                                Container(
                                  width: 12,
                                  height: 4,
                                  decoration: BoxDecoration(color: chapterColor(c.chapter), borderRadius: BorderRadius.circular(2)),
                                ),
                                const SizedBox(width: Gap.s),
                                Expanded(child: Text('${w.chapterById(c.chapter)['title']}', style: const TextStyle(fontSize: 13))),
                                Text(l.statKm(fmtKm(c.km)), style: const TextStyle(fontSize: 13, color: Palette.parchmentDim)),
                                SizedBox(
                                  width: 56,
                                  child: Text(l.statDaysShort(c.days), textAlign: TextAlign.right, style: const TextStyle(fontSize: 13)),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            _bottom(
              context,
              label: l.next,
              onNext: onNext,
              onShare: () => shareCardDialog(
                context,
                kind: 'finish',
                card: _SummaryCard(content: content, stats: s, forShare: true),
                text: l.shareTextFinish(shareLink()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Карточка «Я дошёл до Териберки» с картой всего пути (на экране итога и в «Поделиться»).
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.content, required this.stats, this.forShare = false});

  final GameContent content;
  final JourneyStats stats;
  final bool forShare;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = stats;
    final body = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 4),
        Text(l.finCardTitle, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w600)),
        SizedBox(height: 230, child: JourneyMap(content: content, upTo: content.world.chapters.length)),
        Row(
          children: [
            Expanded(child: Text(l.finTotal, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13))),
            Text(l.statKm(fmtKm(s.totalKm)), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
          ],
        ),
        if (forShare) ...[
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(child: StatFigure(value: '${s.days}', label: l.finDaysLabel(s.days))),
              Expanded(child: StatFigure(value: groupInt(s.steps), label: l.finStepsLabel)),
              Expanded(child: StatFigure(value: l.statKm(fmtKm(s.distKm)), label: l.finDistLabel)),
            ],
          ),
        ],
      ],
    );
    final dates = '${fmtDay(l, s.startDay)} – ${fmtDay(l, s.endDay)}';
    if (forShare) return ShareCardFrame(right: dates, child: body);
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Palette.tabLine),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF173B45), Palette.ink, Color(0xFF1A1530)],
          stops: [0, 0.55, 1],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(l.shareCardBrand,
                  style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w700, letterSpacing: 3, fontSize: 12)),
              const Spacer(),
              Text(dates, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
            ],
          ),
          body,
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- медаль

class _MedalPage extends StatelessWidget {
  const _MedalPage({required this.data, required this.busy, required this.onNext});

  final MedalData data;
  final bool busy;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(child: MedalBody(data: data)),
            _bottom(
              context,
              label: l.next,
              onNext: busy ? null : onNext,
              onShare: () => shareCardDialog(
                context,
                kind: 'medal',
                card: _MedalShareCard(data: data),
                text: l.shareTextFinish(shareLink()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Медаль, обещание и достижения — экран медали и «Пройденные пути» в Журнале.
class MedalBody extends StatelessWidget {
  const MedalBody({super.key, required this.data});

  final MedalData data;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m),
      children: [
        Text(l.medalKicker.toUpperCase(),
            textAlign: TextAlign.center, style: const TextStyle(color: Palette.accent, letterSpacing: 2, fontSize: 12)),
        const SizedBox(height: Gap.s),
        Center(child: MedalView(data: data, size: 200)),
        const SizedBox(height: Gap.s),
        Text(l.medalPromise,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFFE8C15A), fontStyle: FontStyle.italic, fontSize: 17)),
        Text(l.medalPromiseDone, textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
        const SizedBox(height: 4),
        Text(
          '${fmtDay(l, data.startDay)} – ${fmtDay(l, data.endDay)} · ${l.medalFlipHint}',
          textAlign: TextAlign.center,
          style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5),
        ),
        const SizedBox(height: Gap.m),
        AchievementsGrid(data: data),
      ],
    );
  }
}

class _MedalShareCard extends StatelessWidget {
  const _MedalShareCard({required this.data});

  final MedalData data;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final d = data;
    return ShareCardFrame(
      right: '${fmtDay(l, d.startDay)} – ${fmtDay(l, d.endDay)}',
      child: Column(
        children: [
          const SizedBox(height: Gap.m),
          const MedalFace(size: 170),
          const SizedBox(height: Gap.s),
          Text(l.medalPromise, style: const TextStyle(color: Color(0xFFE8C15A), fontStyle: FontStyle.italic, fontSize: 16)),
          Text(l.medalPromiseDone, style: const TextStyle(fontSize: 14)),
          const SizedBox(height: Gap.s),
          Row(
            children: [
              Expanded(child: StatFigure(value: l.statKm(fmtKm(d.totalKm)), label: l.achRoute, center: true)),
              Expanded(child: StatFigure(value: '${d.days}', label: l.finDaysLabel(d.days), center: true)),
              Expanded(child: StatFigure(value: groupInt(d.steps), label: l.finStepsLabel, center: true)),
            ],
          ),
        ],
      ),
    );
  }
}

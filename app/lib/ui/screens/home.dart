// Главная: вкладки «Путь», «Герой», «Журнал».

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/route_map.dart';
import 'hero_tab.dart';
import 'journal_tab.dart';
import 'settings_screen.dart';
import 'stop_screens.dart';
import 'thought_screen.dart';

final _num = NumberFormat.decimalPattern('ru');

class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      body: IndexedStack(index: _tab, children: const [PathTab(), HeroTab(), JournalTab()]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.route_outlined), label: l.tabPath),
          NavigationDestination(icon: const Icon(Icons.backpack_outlined), label: l.tabHero),
          NavigationDestination(icon: const Icon(Icons.menu_book_outlined), label: l.tabJournal),
        ],
      ),
    );
  }
}

String weatherName(AppLocalizations l, String w) => switch (w) {
      'clear' => l.wxClear,
      'cloudy' => l.wxCloudy,
      'rain' => l.wxRain,
      'wind' => l.wxWind,
      'fog' => l.wxFog,
      'heat' => l.wxHeat,
      'snow' => l.wxSnow,
      _ => w,
    };

IconData weatherIcon(String w) => switch (w) {
      'clear' => Icons.wb_sunny_outlined,
      'cloudy' => Icons.cloud_outlined,
      'rain' => Icons.umbrella_outlined,
      'wind' => Icons.air,
      'fog' => Icons.blur_on,
      'heat' => Icons.thermostat,
      'snow' => Icons.ac_unit,
      _ => Icons.cloud_outlined,
    };

String dayPartName(AppLocalizations l, double phase) {
  if (phase < 0.2) return l.dayMorning;
  if (phase < 0.55) return l.dayDay;
  if (phase < 0.75) return l.dayEvening;
  return l.dayNight;
}

class PathTab extends ConsumerStatefulWidget {
  const PathTab({super.key});

  @override
  ConsumerState<PathTab> createState() => _PathTabState();
}

class _PathTabState extends ConsumerState<PathTab> {
  bool _near = true;
  bool _surveyShown = false;

  void _openStop() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const StopScreen()));
  }

  void _maybeSurvey() {
    if (_surveyShown) return;
    final c = ref.read(appProvider.notifier);
    if (!c.shouldAskSurvey()) return;
    _surveyShown = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final l = AppLocalizations.of(context);
      showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(l.surveyTitle),
          content: Text(l.surveyBody),
          actions: [
            for (final (key, label) in [
              ('yes', l.surveyYes),
              ('likely', l.surveyLikely),
              ('unlikely', l.surveyUnlikely),
              ('no', l.surveyNo),
            ])
              TextButton(
                onPressed: () {
                  Navigator.of(ctx).pop();
                  c.answerSurvey(key);
                },
                child: Text(label),
              ),
          ],
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final content = m.content!;
    final hero = m.hero!;
    final eng = Engine(content.world, hero);
    final w = content.world;
    final ch = w.chapterAt(hero.pos);
    final chapter = w.chapterById(ch);
    final phase = eng.dayPhase();
    final night = phase >= 0.75 ? (ch == 3 || ch == 4 ? 0.25 : 0.8) : 0.0;
    final wx = eng.weatherHere();
    final text = Theme.of(context).textTheme;
    _maybeSurvey();

    final stop = hero.stop;
    final nowMs = DateTime.now().millisecondsSinceEpoch;

    return Scaffold(
      appBar: AppBar(
        titleSpacing: Gap.m,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l.chapterLabel(ch), style: const TextStyle(fontSize: 12, color: Palette.parchmentDim)),
            Text('${chapter['title']}', style: const TextStyle(fontSize: 18)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: l.settingsTitle,
            icon: const Icon(Icons.settings_outlined),
            onPressed: () =>
                Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: c.refresh,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            SizedBox(
              height: 300,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: RouteMap(content: content, heroPos: hero.pos, near: _near, night: night),
                  ),
                  Positioned(
                    top: Gap.s,
                    right: Gap.s,
                    child: FilledButton.tonal(
                      style: FilledButton.styleFrom(minimumSize: const Size(0, 36)),
                      onPressed: () => setState(() => _near = !_near),
                      child: Text(_near ? l.mapWhole : l.mapNear),
                    ),
                  ),
                  Positioned(
                    left: Gap.s,
                    bottom: Gap.xs,
                    child: Text(content.map.attribution,
                        style: const TextStyle(fontSize: 9, color: Palette.parchmentDim)),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(Gap.m),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (stop != null) ...[
                    _StopBanner(onOpen: _openStop),
                    const SizedBox(height: Gap.m),
                  ],
                  if (hero.delayUntil > nowMs) ...[
                    SectionCard(
                      child: Row(children: [
                        const Icon(Icons.hourglass_bottom, color: Palette.gold),
                        const SizedBox(width: Gap.s),
                        Expanded(
                          child: Text(l.delayBanner(((hero.delayUntil - nowMs) / msHour).ceil())),
                        ),
                      ]),
                    ),
                    const SizedBox(height: Gap.m),
                  ],
                  if (hero.detour != null) ...[
                    SectionCard(
                      child: Row(children: [
                        const Icon(Icons.alt_route, color: Palette.gold),
                        const SizedBox(width: Gap.s),
                        Expanded(child: Text(l.detourBanner((hero.detour!.remaining / 1000).toStringAsFixed(1)))),
                      ]),
                    ),
                    const SizedBox(height: Gap.m),
                  ],
                  // Ключевой экран
                  SectionCard(
                    highlighted: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          hero.finished
                              ? l.finishedShort
                              : (eng.daysLeft() == null ? l.daysLeftUnknown : l.daysLeft(eng.daysLeft()!)),
                          style: text.titleLarge?.copyWith(color: Palette.gold),
                        ),
                        const SizedBox(height: Gap.xs),
                        Text(
                          l.kmLeft(_num.format(eng.kmLeft().round()), _num.format((hero.pos / 1000).round())),
                          style: const TextStyle(color: Palette.parchmentDim),
                        ),
                        const SizedBox(height: Gap.s),
                        Row(children: [
                          Icon(weatherIcon(wx), size: 18, color: Palette.parchmentDim),
                          const SizedBox(width: Gap.xs),
                          Expanded(
                            child: Text(
                              l.weatherLine(dayPartName(l, phase), weatherName(l, wx), '${chapter['month'] ?? ''}'),
                              style: const TextStyle(color: Palette.parchmentDim, fontSize: 13),
                            ),
                          ),
                        ]),
                      ],
                    ),
                  ),
                  const SizedBox(height: Gap.m),
                  _StatsCard(eng: eng),
                  const SizedBox(height: Gap.m),
                  _TodayCard(eng: eng),
                  const SizedBox(height: Gap.m),
                  _ThoughtCard(),
                  if (!m.stepsStatus.anySource) ...[
                    const SizedBox(height: Gap.m),
                    SectionCard(
                      onTap: () => Navigator.of(context)
                          .push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
                      child: Row(children: [
                        const Icon(Icons.error_outline, color: Palette.danger),
                        const SizedBox(width: Gap.s),
                        Expanded(child: Text(l.noStepsSource)),
                      ]),
                    ),
                  ],
                  const SizedBox(height: Gap.l),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StopBanner extends ConsumerWidget {
  const _StopBanner({required this.onOpen});
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final hero = m.hero!;
    final content = m.content!;
    final st = hero.stop!;
    final (icon, title, sub) = switch (st['type']) {
      'event' => (
          Icons.auto_stories_outlined,
          l.stopEvent,
          '${Engine(content.world, hero).currentEvent()?['title'] ?? ''}',
        ),
      'place' => (Icons.cottage_outlined, l.stopPlace, content.placeName('${st['place']}')),
      'chapter_end' => (Icons.flag_outlined, l.stopChapter, content.placeName('${st['place']}')),
      'death' => (Icons.nightlight_outlined, l.stopDeath, content.placeName('${st['place']}')),
      'finish' => (Icons.waves, l.stopFinish, content.placeName('teriberka')),
      _ => (Icons.place_outlined, l.stopEvent, ''),
    };
    return SectionCard(
      highlighted: true,
      onTap: onOpen,
      child: Row(
        children: [
          Icon(icon, color: Palette.gold, size: 32),
          const SizedBox(width: Gap.m),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Palette.gold, fontSize: 12, letterSpacing: 1)),
                const SizedBox(height: 2),
                Text(sub, style: Theme.of(context).textTheme.titleMedium),
                if (hero.buffer > 500)
                  Text(
                    l.bufferWaiting((hero.buffer / 1000).toStringAsFixed(1)),
                    style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
                  ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: Palette.gold),
        ],
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.eng});
  final Engine eng;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = eng.s.stats;
    final danger = eng.dangerBelow;
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          StatBar(
            label: l.statSatiety,
            value: s['satiety']!,
            color: Palette.satiety,
            icon: Icons.restaurant,
            danger: s['satiety']! < danger,
          ),
          const SizedBox(height: Gap.s),
          StatBar(
            label: l.statWater,
            value: s['water']!,
            color: Palette.water,
            icon: Icons.water_drop_outlined,
            danger: s['water']! < danger,
          ),
          const SizedBox(height: Gap.s),
          StatBar(
            label: l.statWarmth,
            value: s['warmth']!,
            color: Palette.warmth,
            icon: Icons.local_fire_department_outlined,
            danger: s['warmth']! < danger,
          ),
          if (eng.inBonus()) ...[
            const SizedBox(height: Gap.s),
            Text(eng.noticed() ? l.bonusNoticed : l.bonusOn,
                style: TextStyle(color: eng.noticed() ? Palette.ember : Palette.gold, fontSize: 13)),
          ],
        ],
      ),
    );
  }
}

class _TodayCard extends ConsumerWidget {
  const _TodayCard({required this.eng});
  final Engine eng;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final today = c.today;
    final tiers = (eng.b['dailyGoals']['tiers'] as List).cast<Map>();
    final todaySteps = eng.s.daySteps[today] ?? 0;
    final shownSteps = math.max(m.todaySteps, todaySteps);
    Map? next;
    for (final t in tiers) {
      if (todaySteps < toI(t['steps'])) {
        next = t;
        break;
      }
    }
    final canClaim = eng.canClaimLogin(today);
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.directions_walk, color: Palette.gold),
            const SizedBox(width: Gap.s),
            Expanded(child: Text(l.todaySteps(_num.format(shownSteps)), style: Theme.of(context).textTheme.titleMedium)),
            const Icon(Icons.toll, color: Palette.gold, size: 18),
            const SizedBox(width: Gap.xs),
            Text('${eng.s.coins}'),
          ]),
          const SizedBox(height: Gap.s),
          if (next != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: LinearProgressIndicator(
                value: (todaySteps / toI(next['steps'])).clamp(0.0, 1.0),
                minHeight: 8,
                color: Palette.gold,
                backgroundColor: Palette.inkHigh,
              ),
            ),
            const SizedBox(height: Gap.xs),
            Text(l.nextGoal(_num.format(toI(next['steps'])), toI(next['coins'])),
                style: const TextStyle(color: Palette.parchmentDim, fontSize: 13)),
          ] else
            Text(l.allGoalsDone, style: const TextStyle(color: Palette.gold, fontSize: 13)),
          if (canClaim) ...[
            const SizedBox(height: Gap.s),
            FilledButton.icon(
              onPressed: () {
                final got = c.claimLogin();
                if (got > 0) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.loginClaimed(got))));
                }
              },
              icon: const Icon(Icons.toll),
              label: Text(l.loginClaim(toI(eng.b['dailyGoals']['loginCoins']))),
            ),
          ],
          if (m.lastSyncSources.isNotEmpty) ...[
            const SizedBox(height: Gap.s),
            Text(
              l.stepsSources(_num.format(m.lastSyncSources['sensor'] ?? 0), _num.format(m.lastSyncSources['hc'] ?? 0)),
              style: const TextStyle(color: Palette.parchmentDim, fontSize: 11),
            ),
          ],
        ],
      ),
    );
  }
}

class _ThoughtCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final day = c.journeyDay();
    final t = c.content.thoughtForDay(day);
    final seen = c.thoughtSeenToday();
    return SectionCard(
      highlighted: !seen,
      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ThoughtScreen(day: day))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.wb_twilight, color: seen ? Palette.parchmentDim : Palette.gold),
            const SizedBox(width: Gap.s),
            Text(l.thoughtCardTitle, style: TextStyle(color: seen ? Palette.parchmentDim : Palette.gold)),
          ]),
          const SizedBox(height: Gap.s),
          Text('«${t.quote}»', style: const TextStyle(fontStyle: FontStyle.italic, height: 1.4)),
          const SizedBox(height: Gap.xs),
          Text('— ${t.author}', style: const TextStyle(color: Palette.parchmentDim, fontSize: 13)),
        ],
      ),
    );
  }
}

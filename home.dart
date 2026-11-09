// Главная: вкладки «Путь», «Карта», «Герой», «Журнал» в тёмном доке снизу (v5.3).
// «Путь» сверху вниз: шапка (глава) → витражная лента главы → темп и погода → сосуды показателей
// → шаги сегодня → мысль дня.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../engine/engine.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/coach_tour.dart';
import '../widgets/common.dart';
import '../widgets/route_ribbon.dart';
import '../widgets/vessels.dart';
import 'finished_home.dart';
import 'hero_tab.dart';
import 'journal_tab.dart';
import 'map_tab.dart';
import 'overflow_screens.dart' show OverflowBanner;
import 'settings_screen.dart';
import 'stop_screens.dart';
import 'thought_screen.dart';

final _num = NumberFormat.decimalPattern('ru');
final _mult = NumberFormat('0.##', 'ru');

class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _tab = 0;

  /// «Прочитано до» на момент открытия журнала: записи позже отмечены точкой, пока вкладка открыта.
  int? _journalSince;

  /// Время последней записи журнала (служебные zone_fallback не в счёт).
  static int _lastJournalT(AppModel m) {
    final j = m.hero?.journal;
    if (j == null) return 0;
    for (var i = j.length - 1; i >= 0; i--) {
      if (j[i].kind != 'zone_fallback') return j[i].t;
    }
    return 0;
  }

  void _go(int i) {
    final m = ref.read(appProvider);
    final flags = ref.read(uiFlagsProvider);
    final last = _lastJournalT(m);
    if (i == 3 && _tab != 3) {
      _journalSince = flags.journalReadAt;
      ref.read(uiFlagsProvider.notifier).markJournalRead(last);
    } else if (i != 3 && _tab == 3) {
      // записи, пришедшие, пока журнал был открыт, тоже прочитаны
      ref.read(uiFlagsProvider.notifier).markJournalRead(last);
    }
    setState(() => _tab = i);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final flags = ref.watch(uiFlagsProvider);
    final lastT = _lastJournalT(m);
    if (flags.loaded && flags.journalReadAt == 0 && lastT > 0) {
      // профиль прошлых сборок: всё, что уже записано, считаем прочитанным
      Future.microtask(() => ref.read(uiFlagsProvider.notifier).markJournalRead(lastT));
    }
    final journalDot = _tab != 3 && flags.loaded && flags.journalReadAt > 0 && lastT > flags.journalReadAt;
    // Тур по главной и подсказки по случаю (docs/v5/09 §6) — поверх всего, включая нижний бар.
    return HomeCoach(
      tab: _tab,
      child: Scaffold(
        body: IndexedStack(
          index: _tab,
          children: [
            // «Карта» в ленте главы переключает на вкладку карты
            PathTab(onOpenMap: () => _go(1)),
            const MapTab(),
            const HeroTab(),
            JournalTab(newSince: _journalSince ?? flags.journalReadAt),
          ],
        ),
        bottomNavigationBar: _DockBar(
          index: _tab,
          journalDot: journalDot,
          labels: [l.tabPath, l.tabMap, l.tabHero, l.tabJournal],
          onTap: _go,
          newEntriesLabel: l.tabNewEntries(l.tabJournal),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- нижний бар-док

const _tabIcons = <String>[
  'assets/art/ui/tab_path.svg',
  'assets/art/ui/tab_map.svg',
  'assets/art/ui/tab_hero.svg',
  'assets/art/ui/tab_journal.svg',
];

/// Приглушение неактивных значков: насыщенность 0.45.
const _desaturate = ColorFilter.matrix(<double>[
  0.56693, 0.39336, 0.03971, 0, 0, //
  0.11693, 0.84336, 0.03971, 0, 0, //
  0.11693, 0.39336, 0.48971, 0, 0, //
  0, 0, 0, 1, 0, //
]);

/// Тёмная карточка-док: фон #16222F, рамка #1F3043, радиус 18, отступ 10 от краёв; снизу — системная шторка.
class _DockBar extends StatelessWidget {
  const _DockBar({
    required this.index,
    required this.journalDot,
    required this.labels,
    required this.onTap,
    required this.newEntriesLabel,
  });

  final int index;
  final bool journalDot;
  final List<String> labels;
  final ValueChanged<int> onTap;
  final String newEntriesLabel;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 4, 10, 10),
        child: TourAnchor(
          id: 'navbar',
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(Gap.radiusDock),
              boxShadow: const [BoxShadow(color: Color(0x99050A10), blurRadius: 20, offset: Offset(0, -8))],
            ),
            // Material, чтобы рябь нажатия была видна на тёмной карточке.
            child: Material(
              color: Palette.inkRaised,
              clipBehavior: Clip.antiAlias,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(Gap.radiusDock),
                side: const BorderSide(color: Palette.inkHigh),
              ),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 64),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  child: MediaQuery.withClampedTextScaling(
                    maxScaleFactor: 1.3,
                    child: Row(
                      mainAxisSize: MainAxisSize.max,
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        for (var i = 0; i < labels.length; i++)
                          Expanded(
                            child: _DockTab(
                              icon: _tabIcons[i],
                              label: labels[i],
                              active: i == index,
                              dot: i == 3 && journalDot,
                              semantics: (i == 3 && journalDot) ? newEntriesLabel : labels[i],
                              onTap: () => onTap(i),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DockTab extends StatelessWidget {
  const _DockTab({
    required this.icon,
    required this.label,
    required this.active,
    required this.dot,
    required this.semantics,
    required this.onTap,
  });

  final String icon;
  final String label;
  final bool active;
  final bool dot;
  final String semantics;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    Widget glyph = Art(icon, width: 26, height: 26, fit: BoxFit.contain);
    if (!active) {
      glyph = Opacity(opacity: 0.55, child: ColorFiltered(colorFilter: _desaturate, child: glyph));
    }
    return Semantics(
      button: true,
      selected: active,
      label: semantics,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        // heightFactor: 1 — иначе Center растягивается на всю доступную высоту
        // и док в bottomNavigationBar занимает весь экран (баг 0.5.4).
        child: Center(
          heightFactor: 1,
          child: Container(
            padding: const EdgeInsets.fromLTRB(10, 6, 10, 5),
            decoration: BoxDecoration(
              color: active ? Palette.accent.withAlpha(26) : Colors.transparent,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: active ? Palette.tabLine : Colors.transparent),
            ),
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    glyph,
                    const SizedBox(height: 3),
                    Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.fade,
                      softWrap: false,
                      style: TextStyle(
                        fontSize: 11,
                        color: active ? Palette.accent : Palette.parchmentDim,
                        fontWeight: active ? FontWeight.w700 : FontWeight.w400,
                      ),
                    ),
                  ],
                ),
                if (dot)
                  Positioned(
                    top: -1,
                    right: -2,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: Palette.accent,
                        shape: BoxShape.circle,
                        border: Border.all(color: Palette.lead, width: 1.5),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- погода

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

// ---------------------------------------------------------------- вкладка «Путь»

class PathTab extends ConsumerStatefulWidget {
  const PathTab({super.key, this.onOpenMap});

  final VoidCallback? onOpenMap;

  @override
  ConsumerState<PathTab> createState() => _PathTabState();
}

class _PathTabState extends ConsumerState<PathTab> {
  bool _surveyShown = false;
  bool _refreshing = false;

  void _openStop() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const StopScreen()));
  }

  void _openSettings() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));
  }

  void _openMap() => widget.onOpenMap?.call();

  /// Ручное обновление шагов (вместо свайпа вниз, который мешал листать карту).
  Future<void> _manualRefresh() async {
    if (_refreshing) return;
    setState(() => _refreshing = true);
    try {
      await ref.read(appProvider.notifier).refresh();
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  bool _doneShown = false;

  /// После финала: сообщение «Путь пройден» один раз (флаг finishMsgShown в ui_flags).
  void _maybeDoneMessage(bool finishedHere) {
    if (!finishedHere || _doneShown) return;
    final flags = ref.read(uiFlagsProvider);
    if (!flags.loaded || flags.finishMsgShown) return;
    _doneShown = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) showDoneMessage(context, ref);
    });
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
    final wx = eng.weatherHere();
    _maybeSurvey();
    _maybeDoneMessage(hero.finished && hero.stop == null);

    final stop = hero.stop;
    final nowMs = DateTime.now().millisecondsSinceEpoch;

    // Источники шагов: оба выключены в настройках — отдельная заметная плашка
    final prof = m.profile;
    final sensorOn = prof?.stepsSensor ?? true;
    final hcOn = prof?.stepsHc ?? true;
    final stepsOff = !sensorOn && !hcOn;
    final noSource = !stepsOff && !m.stepsStatus.anyEnabled(sensor: sensorOn, hc: hcOn);

    final shownSteps = math.max(m.todaySteps, eng.s.daySteps[c.today] ?? 0);
    final day = c.journeyDay();

    final daysLeft = eng.daysLeft();
    final paceValue = hero.finished
        ? l.finishedShort
        : (daysLeft == null ? l.homePaceUnknownShort : l.homePaceDays(daysLeft));

    const side = EdgeInsets.symmetric(horizontal: 12);
    return Scaffold(
      appBar: AppBar(
        title: ScreenTitle(kicker: l.homeHeroLine(day, ch), title: '${chapter['title']}'),
        actions: [
          IconButton(
            tooltip: l.homeRefreshSteps,
            icon: _refreshing
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.refresh),
            onPressed: _refreshing ? null : _manualRefresh,
          ),
          IconButton(
            tooltip: l.settingsTitle,
            icon: const Icon(Icons.settings_outlined),
            onPressed: _openSettings,
          ),
          const SizedBox(width: Gap.xs),
        ],
      ),
      // Без RefreshIndicator: обычная прокрутка (п. 10 заказа v5.3)
      body: ListView(
        padding: const EdgeInsets.fromLTRB(0, Gap.xs, 0, Gap.l),
        children: [
          if (stepsOff || noSource)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, Gap.s),
              child: WarnBox(text: stepsOff ? l.stepsOffBanner : l.noStepsSource, onTap: _openSettings),
            ),
          const OverflowBanner(),
          if (stop != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, Gap.s),
              child: _StopBanner(onOpen: _openStop),
            ),
          if (hero.finished && stop == null)
            const Padding(
              padding: EdgeInsets.fromLTRB(12, 0, 12, Gap.s),
              child: FinishedCards(),
            ),
          Padding(
            padding: side,
            child: TourAnchor(
              id: 'map',
              child: RouteRibbonCard(
                world: w,
                heroPos: hero.pos,
                zone: c.zoneHere(),
                onMap: _openMap,
              ),
            ),
          ),
          const SizedBox(height: Gap.s),
          if (hero.delayUntil > nowMs) ...[
            Padding(
              padding: side,
              child: _NoteCard(
                icon: Icons.hourglass_bottom,
                text: l.delayBanner(((hero.delayUntil - nowMs) / msHour).ceil()),
              ),
            ),
            const SizedBox(height: Gap.s),
          ],
          if (hero.detour != null) ...[
            Padding(
              padding: side,
              child: _NoteCard(
                icon: Icons.alt_route,
                text: l.detourBanner((hero.detour!.remaining / 1000).toStringAsFixed(1)),
              ),
            ),
            const SizedBox(height: Gap.s),
          ],
          Padding(
            padding: side,
            child: _PaceCard(
              value: paceValue,
              weatherIcon: weatherIcon(wx),
              weather: l.homeWeatherShort(dayPartName(l, phase), weatherName(l, wx)),
            ),
          ),
          const SizedBox(height: Gap.s),
          Padding(padding: side, child: TourAnchor(id: 'stats', child: _VesselsCard(eng: eng))),
          const SizedBox(height: Gap.s),
          Padding(padding: side, child: _TodayCard(eng: eng, shownSteps: shownSteps)),
          const SizedBox(height: Gap.s),
          Padding(padding: side, child: _ThoughtCard()),
        ],
      ),
    );
  }
}

/// «При твоём темпе осталось N дней» + погода — одна компактная строка.
class _PaceCard extends StatelessWidget {
  const _PaceCard({required this.value, required this.weatherIcon, required this.weather});

  final String value;
  final IconData weatherIcon;
  final String weather;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
      decoration: cardDecoration(radius: Gap.radiusS),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(l.homePaceLabel, style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim, height: 1.1)),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, height: 1.25)),
              ],
            ),
          ),
          const SizedBox(width: Gap.s),
          Icon(weatherIcon, size: 16, color: Palette.parchmentDim),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              weather,
              style: const TextStyle(fontSize: 12.5, color: Palette.parchmentDim),
              maxLines: 2,
              textAlign: TextAlign.end,
            ),
          ),
        ],
      ),
    );
  }
}

/// Сосуды показателей + строка порогов или «Бонус включён».
class _VesselsCard extends StatelessWidget {
  const _VesselsCard({required this.eng});

  final Engine eng;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = eng.s.stats;
    final danger = eng.dangerBelow;
    final bonus = (eng.b['bonus'] as Map).cast<String, dynamic>();
    final bonusAt = toD(bonus['satietyAtLeast']);
    final maxStat = eng.maxStat.round();
    final inBonus = eng.inBonus();
    final sat = s['satiety'] ?? 0.0;
    final wat = s['water'] ?? 0.0;
    final warm = s['warmth'] ?? 0.0;
    final a11y = [
      l.vesselA11y(l.statSatiety, sat.round(), maxStat),
      l.vesselA11y(l.statWater, wat.round(), maxStat),
      l.vesselA11y(l.statWarmth, warm.round(), maxStat),
    ].join('. ');
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
      decoration: cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          VesselsPanel(
            satiety: VesselInfo(
              value: sat,
              label: l.statSatiety,
              dangerLabel: l.vesselLabelDanger(l.statSatiety, l.vesselHungry),
            ),
            water: VesselInfo(
              value: wat,
              label: l.statWater,
              dangerLabel: l.vesselLabelDanger(l.statWater, l.vesselThirsty),
            ),
            warmth: VesselInfo(
              value: warm,
              label: l.statWarmth,
              dangerLabel: l.vesselLabelDanger(l.statWarmth, l.vesselCold),
            ),
            dangerBelow: danger,
            bonusAt: bonusAt,
            bonus: inBonus,
            semanticsLabel: a11y,
          ),
          const SizedBox(height: 4),
          if (inBonus)
            TourAnchor(
              id: 'bonus',
              child: Wrap(
                spacing: 6,
                runSpacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(l.vesselBonusOn,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Palette.accent)),
                  Text(
                    l.vesselBonusMult(
                      _mult.format(toD(bonus['eventMultiplier'])),
                      _mult.format(toD(bonus['drainMultiplier'])),
                    ),
                    style: const TextStyle(fontSize: 12, color: Palette.parchmentDim),
                  ),
                ],
              ),
            )
          else
            Wrap(
              spacing: 12,
              runSpacing: 2,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _LegendItem(
                  swatch: const SizedBox(width: 10, height: 10, child: CustomPaint(painter: _HatchSwatchPainter())),
                  label: l.vesselLegendDanger(danger.round()),
                ),
                _LegendItem(
                  swatch: Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: Palette.accent,
                      borderRadius: BorderRadius.circular(2),
                      border: Border.all(color: Palette.lead),
                    ),
                  ),
                  label: l.vesselLegendBonus(bonusAt.round()),
                ),
              ],
            ),
          if (inBonus && eng.noticed()) ...[
            const SizedBox(height: 4),
            Text(l.bonusNoticed, style: const TextStyle(color: Palette.ember, fontSize: 12.5, height: 1.3)),
          ],
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.swatch, required this.label});

  final Widget swatch;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        swatch,
        const SizedBox(width: 5),
        // В Wrap ширина ограничена — Flexible переносит длинную подпись вместо переполнения строки.
        Flexible(child: Text(label, style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim))),
      ],
    );
  }
}

/// Квадратик со штриховкой «ниже порога — опасно».
class _HatchSwatchPainter extends CustomPainter {
  const _HatchSwatchPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final r = Offset.zero & size;
    canvas.drawRect(r, Paint()..color = const Color(0xFF231A24));
    canvas.save();
    canvas.clipRect(r);
    final p = Paint()
      ..color = Palette.coralLine
      ..strokeWidth = 1.6;
    for (var x = 0.0; x < size.width + size.height; x += 4) {
      canvas.drawLine(Offset(x, 0), Offset(x - size.height, size.height), p);
    }
    canvas.restore();
    canvas.drawRect(
      r,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = Palette.lead,
    );
  }

  @override
  bool shouldRepaint(covariant _HatchSwatchPainter oldDelegate) => false;
}

// ---------------------------------------------------------------- карточки «Пути»

/// Короткая заметка в одну строку (ожидание, ответвление).
class _NoteCard extends StatelessWidget {
  const _NoteCard({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: Gap.s + 2),
      child: Row(children: [
        Icon(icon, color: Palette.accent, size: 20),
        const SizedBox(width: Gap.s + 4),
        Expanded(child: Text(text, style: const TextStyle(fontSize: 13))),
      ]),
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
      'night' => (Icons.bedtime_outlined, l.stopNight, l.nightTitle),
      _ => (Icons.place_outlined, l.stopEvent, ''),
    };
    return SectionCard(
      highlighted: true,
      onTap: onOpen,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: Gap.s + 2),
      child: Row(
        children: [
          Icon(icon, color: Palette.accent, size: 28),
          const SizedBox(width: Gap.m),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Palette.accent, fontSize: 12, letterSpacing: 1)),
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
          const Icon(Icons.chevron_right, color: Palette.accent),
        ],
      ),
    );
  }
}

/// «Сегодня N шагов»: полоса до следующей цели дня, монеты, бонус за вход.
class _TodayCard extends ConsumerWidget {
  const _TodayCard({required this.eng, required this.shownSteps});
  final Engine eng;
  final int shownSteps;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final today = c.today;
    final tiers = (eng.b['dailyGoals']['tiers'] as List).cast<Map>();
    final todaySteps = eng.s.daySteps[today] ?? 0;
    Map? next;
    for (final t in tiers) {
      if (todaySteps < toI(t['steps'])) {
        next = t;
        break;
      }
    }
    final canClaim = eng.canClaimLogin(today);
    return SectionCard(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.directions_walk, color: Palette.accent, size: 20),
            const SizedBox(width: Gap.s),
            Expanded(
              child: Text(
                l.todaySteps(_num.format(shownSteps)),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const Icon(Icons.toll, color: Palette.accent, size: 18),
            const SizedBox(width: Gap.xs),
            Text('${eng.s.coins}', style: const TextStyle(fontWeight: FontWeight.w600)),
          ]),
          if (next != null) ...[
            const SizedBox(height: 10),
            AccentProgress(value: todaySteps / toI(next['steps'])),
            const SizedBox(height: Gap.s),
            Text(
              l.nextGoal(_num.format(toI(next['steps'])), toI(next['coins'])),
              style: const TextStyle(fontSize: 13, color: Palette.parchmentDim),
            ),
          ] else ...[
            const SizedBox(height: Gap.s),
            Text(l.allGoalsDone, style: const TextStyle(color: Palette.accent, fontSize: 13)),
          ],
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
            Icon(Icons.wb_twilight, color: seen ? Palette.parchmentDim : Palette.accent),
            const SizedBox(width: Gap.s),
            // Flexible: при крупном шрифте заголовок переносится, а не переполняет строку.
            Flexible(
              child: Text(l.thoughtCardTitle, style: TextStyle(color: seen ? Palette.parchmentDim : Palette.accent)),
            ),
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

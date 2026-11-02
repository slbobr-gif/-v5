// Тур по главному экрану и подсказки по случаю (docs/v5/09 §6).
// TourAnchor отмечает цель; CoachHost затемняет экран, оставляет вырез вокруг цели и показывает карточку.

import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../engine/engine.dart';
import '../../engine/state.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../screens/first_step_screen.dart';
import '../theme/tokens.dart';

/// Реестр целей: id якоря → ключ виджета на экране.
class TourRegistry {
  static final Map<String, GlobalKey> keys = <String, GlobalKey>{};

  /// Вкладки нижнего бара подсвечиваются по якорю всего бара `navbar` (четыре равные кнопки, v5.3).
  static const Map<String, int> tabIndex = <String, int>{'tab_path': 0, 'tab_map': 1, 'tab_hero': 2, 'tab_journal': 3};

  /// Число вкладок в доке.
  static const int tabCount = 4;

  static String resolve(String id) => tabIndex.containsKey(id) ? 'navbar' : id;

  static BuildContext? contextOf(String id) => keys[resolve(id)]?.currentContext;

  static bool has(String id) => contextOf(id) != null;
}

/// Обёртка-цель для тура: регистрирует ключ под [id], пока виджет на экране.
class TourAnchor extends StatefulWidget {
  const TourAnchor({super.key, required this.id, required this.child});

  final String id;
  final Widget child;

  @override
  State<TourAnchor> createState() => _TourAnchorState();
}

class _TourAnchorState extends State<TourAnchor> {
  final GlobalKey _key = GlobalKey();

  @override
  void initState() {
    super.initState();
    TourRegistry.keys[widget.id] = _key;
  }

  @override
  void didUpdateWidget(covariant TourAnchor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.id != widget.id) {
      if (identical(TourRegistry.keys[oldWidget.id], _key)) TourRegistry.keys.remove(oldWidget.id);
      TourRegistry.keys[widget.id] = _key;
    }
  }

  @override
  void dispose() {
    if (identical(TourRegistry.keys[widget.id], _key)) TourRegistry.keys.remove(widget.id);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => KeyedSubtree(key: _key, child: widget.child);
}

/// Шаг тура или подсказка: [id] пишется в tourStepSeen, [anchor] — какую цель подсвечиваем.
class CoachStep {
  const CoachStep({required this.id, required this.anchor, required this.title, required this.body});

  final String id;
  final String anchor;
  final String title;
  final String body;
}

/// Затемнение с вырезом поверх [child]. [tour] — общий тур (пока tourDone == false),
/// [tips] — подсказки по случаю по приоритету (условия уже проверены вызывающим).
class CoachHost extends ConsumerStatefulWidget {
  const CoachHost({
    super.key,
    required this.child,
    this.tour = const <CoachStep>[],
    this.tips = const <CoachStep>[],
    this.active = true,
  });

  final Widget child;
  final List<CoachStep> tour;
  final List<CoachStep> tips;

  /// false — экран сейчас не подходит (другая вкладка, идёт загрузка).
  final bool active;

  @override
  ConsumerState<CoachHost> createState() => _CoachHostState();
}

class _CoachHostState extends ConsumerState<CoachHost> {
  List<CoachStep>? _steps;
  int _i = 0;
  bool _isTour = false;
  Rect? _hole;
  Timer? _timer;
  bool _tipShown = false;
  bool _busy = false;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  bool get _noAnim => MediaQuery.disableAnimationsOf(context);

  void _scheduleCheck() {
    if (_steps != null || _busy || _timer != null || !widget.active) return;
    // Через 600 мс после того, как экран устоялся (§6.4).
    _timer = Timer(const Duration(milliseconds: 600), () {
      _timer = null;
      if (mounted) _check();
    });
  }

  Rect? _rectOf(String anchor) {
    final ctx = TourRegistry.contextOf(anchor);
    if (ctx == null || !ctx.mounted) return null;
    final ro = ctx.findRenderObject();
    final host = context.findRenderObject();
    if (ro is! RenderBox || host is! RenderBox) return null;
    if (!ro.attached || !ro.hasSize || !host.hasSize) return null;
    // Якорь нулевого размера (тело Scaffold сжато в 0, как при баге дока 0.5.4) — подсвечивать нечего:
    // иначе вырез получался полоской 12 px над пустым фоном.
    if (ro.size.width < 1 || ro.size.height < 1) return null;
    final topLeft = ro.localToGlobal(Offset.zero, ancestor: host);
    var r = topLeft & ro.size;
    final bounds = Offset.zero & host.size;
    // Якорь размером почти с весь экран (растянутый док) — вырез ничего не выделит, шаг пропускаем.
    if (r.width * r.height > bounds.width * bounds.height * 0.8) return null;
    final tab = TourRegistry.tabIndex[anchor];
    if (tab != null) {
      final w = r.width / TourRegistry.tabCount;
      // Вырез вкладки — по реальной ширине кнопки дока (на узком экране она уже 96 dp) и высоте дока.
      r = Rect.fromCenter(
        center: Offset(r.left + w * (tab + 0.5), r.top + r.height / 2),
        width: math.min(96.0, w),
        height: math.min(64.0, r.height),
      );
    } else {
      r = r.inflate(6);
    }
    if (!bounds.overlaps(r)) return null;
    return r;
  }

  void _check() {
    if (_steps != null || !widget.active) return;
    final flags = ref.read(uiFlagsProvider);
    if (!flags.loaded) return;
    final route = ModalRoute.of(context);
    if (route != null && !route.isCurrent) return;
    if (widget.tour.isNotEmpty && !flags.tourDone) {
      final present = widget.tour.where((s) => TourRegistry.has(s.anchor)).toList();
      if (present.isEmpty) return;
      final start = present.indexWhere((s) => !flags.tourStepSeen.containsKey(s.id));
      if (start < 0) {
        ref.read(uiFlagsProvider.notifier).update((f) => f.tourDone = true);
        return;
      }
      _steps = present;
      _isTour = true;
      _show(start);
      return;
    }
    if (!flags.tourDone || !flags.tipsEnabled || _tipShown) return;
    for (final t in widget.tips) {
      if (flags.tourStepSeen.containsKey(t.id)) continue;
      if (!TourRegistry.has(t.anchor)) continue;
      _tipShown = true;
      _steps = <CoachStep>[t];
      _isTour = false;
      _show(0);
      return;
    }
  }

  Future<void> _show(int i) async {
    final steps = _steps;
    if (steps == null) return;
    if (i >= steps.length) {
      _finish(skipped: false);
      return;
    }
    _busy = true;
    final s = steps[i];
    final ctx = TourRegistry.contextOf(s.anchor);
    if (ctx != null && ctx.mounted && !TourRegistry.tabIndex.containsKey(s.anchor)) {
      try {
        await Scrollable.ensureVisible(
          ctx,
          alignment: 0.2,
          duration: _noAnim ? Duration.zero : const Duration(milliseconds: 250),
        );
      } catch (_) {
        // цель не в прокручиваемом списке — показываем как есть
      }
    }
    await Future<void>.delayed(const Duration(milliseconds: 32));
    _busy = false;
    if (!mounted || !identical(_steps, steps)) return;
    final hole = _rectOf(s.anchor);
    if (hole == null) {
      // Цели нет на экране — шаг пропускаем без записи.
      if (_isTour && i + 1 < steps.length) {
        _show(i + 1);
      } else {
        _close();
      }
      return;
    }
    setState(() {
      _i = i;
      _hole = hole;
    });
    ref.read(uiFlagsProvider.notifier).markSeen(s.id);
    Analytics.instance.event('tour_step', {'n': i + 1, 'id': s.id, 'mode': _isTour ? 'auto' : 'context'});
  }

  /// Перемерить вырез текущего шага; заметный сдвиг — перерисовать, якорь пропал — закрыть подсказку.
  void _remeasure() {
    final steps = _steps;
    final old = _hole;
    if (!mounted || _busy || steps == null || old == null || _i >= steps.length) return;
    final r = _rectOf(steps[_i].anchor);
    if (r == null) {
      _close();
      return;
    }
    final moved = (r.left - old.left).abs() > 0.5 ||
        (r.top - old.top).abs() > 0.5 ||
        (r.width - old.width).abs() > 0.5 ||
        (r.height - old.height).abs() > 0.5;
    if (moved) setState(() => _hole = r);
  }

  void _close() {
    if (!mounted) return;
    setState(() {
      _steps = null;
      _hole = null;
    });
  }

  void _finish({required bool skipped, String via = 'button'}) {
    final steps = _steps;
    if (skipped && steps != null && _i < steps.length) {
      Analytics.instance.event('tour_skipped', {'at': steps[_i].id, 'via': via});
    }
    Analytics.instance.event('tour_done', {'skipped': skipped});
    ref.read(uiFlagsProvider.notifier).update((f) => f.tourDone = true);
    _close();
  }

  void _next() {
    final steps = _steps;
    if (steps == null) return;
    if (!_isTour) {
      _close();
      return;
    }
    if (_i + 1 >= steps.length) {
      _finish(skipped: false);
    } else {
      _show(_i + 1);
    }
  }

  void _back() {
    if (_steps == null) return;
    if (!_isTour) {
      _close();
      return;
    }
    if (_i > 0) {
      _show(_i - 1);
    } else {
      _finish(skipped: true, via: 'back');
    }
  }

  void _noMore() {
    final steps = _steps;
    if (steps != null && steps.isNotEmpty) {
      Analytics.instance.event('tour_tip_disabled', {'id': steps[_i].id});
    }
    ref.read(uiFlagsProvider.notifier).update((f) => f.tipsEnabled = false);
    _close();
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(uiFlagsProvider);
    final steps = _steps;
    final hole = _hole;
    if (steps == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _scheduleCheck();
      });
    }
    final showing = steps != null && hole != null;
    if (showing) {
      // Вырез держится за реальное положение якоря: после перестройки (подгрузилась картинка, поворот,
      // смена размеров тела Scaffold) пересчитываем его, а не оставляем замер 32 мс после показа.
      WidgetsBinding.instance.addPostFrameCallback((_) => _remeasure());
    }
    return PopScope(
      canPop: steps == null,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (!didPop) _back();
      },
      child: Stack(
        fit: StackFit.expand,
        children: [
          widget.child,
          if (showing) Positioned.fill(child: _overlay(context, steps[_i], hole)),
        ],
      ),
    );
  }

  Widget _overlay(BuildContext context, CoachStep s, Rect hole) {
    final l = AppLocalizations.of(context);
    final steps = _steps!;
    final last = _i + 1 >= steps.length;
    return LayoutBuilder(
      builder: (BuildContext ctx, BoxConstraints box) {
        final size = Size(box.maxWidth, box.maxHeight);
        final pad = MediaQuery.paddingOf(ctx);
        final scale = MediaQuery.textScalerOf(ctx).scale(14) / 14;
        final estH = 190.0 * math.max(1.0, scale);
        final cardW = math.min(size.width - 32, 360.0);
        final left = (size.width - cardW) / 2;
        final below = size.height - hole.bottom - pad.bottom;
        final above = hole.top - pad.top;
        double? top;
        double? bottom;
        var arrow = 0; // 1 — карточка под целью, -1 — над целью, 0 — без стрелки
        if (below >= estH + 24) {
          top = hole.bottom + 14;
          arrow = 1;
        } else if (above >= estH + 24) {
          bottom = size.height - hole.top + 14;
          arrow = -1;
        } else {
          bottom = pad.bottom + Gap.m;
        }
        final radius = hole.width >= size.width - 4 ? 4.0 : 16.0;
        final total = steps.length;
        return BlockSemantics(
          child: Stack(
            children: [
              Positioned.fill(
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () {},
                  child: CustomPaint(painter: _ScrimPainter(hole: hole, radius: radius, arrow: arrow)),
                ),
              ),
              Positioned.fromRect(
                rect: hole,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: _next,
                  child: const SizedBox.expand(),
                ),
              ),
              Positioned(
                left: left,
                width: cardW,
                top: top,
                bottom: bottom,
                child: Semantics(
                  container: true,
                  liveRegion: true,
                  label: _isTour ? l.tourA11y(_i + 1, total) : null,
                  child: Material(
                    color: Palette.inkRaised,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(Gap.radius),
                      side: const BorderSide(color: Palette.accent),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(Gap.m, 14, Gap.m, Gap.s),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  s.title,
                                  style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w600),
                                ),
                              ),
                              if (_isTour)
                                Text(
                                  l.tourCounter(_i + 1, total),
                                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
                                ),
                            ],
                          ),
                          const SizedBox(height: Gap.s),
                          Text(s.body, style: const TextStyle(fontSize: 14.5, height: 1.4)),
                          const SizedBox(height: Gap.s),
                          Wrap(
                            alignment: WrapAlignment.spaceBetween,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            spacing: Gap.s,
                            children: [
                              TextButton(
                                style: TextButton.styleFrom(
                                  foregroundColor: Palette.parchmentDim,
                                  minimumSize: const Size(48, 48),
                                ),
                                onPressed: _isTour ? () => _finish(skipped: true) : _noMore,
                                child: Text(_isTour ? l.tourSkip : l.tourNoMore),
                              ),
                              FilledButton(
                                style: FilledButton.styleFrom(minimumSize: const Size(96, 44)),
                                onPressed: _next,
                                child: Text(_isTour ? (last ? l.tourFinish : l.next) : l.tourGotIt),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ScrimPainter extends CustomPainter {
  _ScrimPainter({required this.hole, required this.radius, required this.arrow});

  final Rect hole;
  final double radius;
  final int arrow;

  @override
  void paint(Canvas canvas, Size size) {
    final rr = RRect.fromRectAndRadius(hole, Radius.circular(radius));
    final scrim = Path.combine(
      PathOperation.difference,
      Path()..addRect(Offset.zero & size),
      Path()..addRRect(rr),
    );
    canvas.drawPath(scrim, Paint()..color = const Color(0xCC070B10));
    canvas.drawRRect(
      rr,
      Paint()
        ..color = Palette.accent.withAlpha(115)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9),
    );
    canvas.drawRRect(
      rr,
      Paint()
        ..color = Palette.accent
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    if (arrow != 0) {
      final cx = hole.center.dx.clamp(28.0, size.width - 28.0);
      final tri = Path();
      if (arrow > 0) {
        final y = hole.bottom + 14;
        tri
          ..moveTo(cx - 12, y + 1)
          ..lineTo(cx, y - 11)
          ..lineTo(cx + 12, y + 1)
          ..close();
      } else {
        final y = hole.top - 14;
        tri
          ..moveTo(cx - 12, y - 1)
          ..lineTo(cx, y + 11)
          ..lineTo(cx + 12, y - 1)
          ..close();
      }
      canvas.drawPath(tri, Paint()..color = Palette.accent);
    }
  }

  @override
  bool shouldRepaint(covariant _ScrimPainter old) =>
      old.hole != hole || old.radius != radius || old.arrow != arrow;
}

// ---------------------------------------------------------------- главная

/// Тур и подсказки главного экрана; также открывает «Первый шаг» (F1), если путь только начат.
/// [tab] — текущая вкладка: подсказки про карту и показатели — только на вкладке «Путь».
class HomeCoach extends ConsumerStatefulWidget {
  const HomeCoach({super.key, required this.tab, required this.child});

  final int tab;
  final Widget child;

  @override
  ConsumerState<HomeCoach> createState() => _HomeCoachState();
}

class _HomeCoachState extends ConsumerState<HomeCoach> {
  bool _firstStepPushed = false;

  void _maybeFirstStep(UiFlags flags) {
    if (_firstStepPushed || !flags.loaded || flags.firstStepDone) return;
    _firstStepPushed = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const FirstStepScreen()));
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final flags = ref.watch(uiFlagsProvider);
    final hero = m.hero;
    final content = m.content;
    if (!flags.loaded) {
      final p = m.profile;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ref.read(uiFlagsProvider.notifier).ensureLoaded(
              onboarded: p?.onboarded ?? false,
              hasProfile: (p?.name.isNotEmpty ?? false) && (p?.consent ?? false),
              hasHero: hero != null,
            );
      });
    }
    if (hero == null || content == null) return widget.child;
    _maybeFirstStep(flags);
    final eng = Engine(content.world, hero);
    final b = content.world.balance;
    final bonus = (b['bonus'] as Map).cast<String, dynamic>();
    final death = (b['death'] as Map).cast<String, dynamic>();
    final bonusStep = CoachStep(
      id: 'bonus',
      anchor: 'bonus',
      title: l.tourStep4Title,
      body: l.tourStep4Body(
        toI(bonus['satietyAtLeast']),
        ((toD(bonus['eventMultiplier']) - 1) * 100).round(),
        ((toD(bonus['drainMultiplier']) - 1) * 100).round(),
      ),
    );
    final tour = <CoachStep>[
      CoachStep(id: 'map', anchor: 'map', title: l.tourStep1Title, body: l.homeTourRibbonBody),
      CoachStep(
        id: 'next',
        anchor: 'next',
        title: l.tourStep2Title,
        body: TourRegistry.has('zone') ? l.tourStep2BodyZone : l.tourStep2Body,
      ),
      CoachStep(id: 'stats', anchor: 'stats', title: l.tourStep3Title, body: l.tourStep3Body),
      bonusStep,
      CoachStep(id: 'tab_hero', anchor: 'tab_hero', title: l.tourStep5Title, body: l.tourStep5Body),
    ];
    final tips = <CoachStep>[];
    final low = statKeys.any((k) => (hero.stats[k] ?? 100) < eng.dangerBelow);
    if (low) {
      tips.add(CoachStep(
        id: 'death',
        anchor: 'stats',
        title: l.tourStep8Title,
        body: l.tourStep8Body(toI(death['rollbackMinKm']), toI(death['rollbackMaxKm'])),
      ));
    }
    if (hero.journal.any((e) => e.kind == 'event')) {
      tips.add(CoachStep(id: 'journal', anchor: 'tab_journal', title: l.tourStep7Title, body: l.tourStep7Body));
    }
    tips.add(bonusStep);
    final zone = ref.read(appProvider.notifier).zoneHere();
    final zoneAnchor = TourRegistry.has('zone') ? 'zone' : 'next';
    if (zone == 'suburb') {
      tips.add(CoachStep(
          id: 'zone_suburb', anchor: zoneAnchor, title: l.tourZoneSuburbTitle, body: l.tourZoneSuburbBody));
    } else if (zone == 'wild') {
      tips.add(
          CoachStep(id: 'zone_wild', anchor: zoneAnchor, title: l.tourZoneWildTitle, body: l.tourZoneWildBody));
    }
    return CoachHost(
      active: widget.tab == 0 && flags.firstStepDone,
      tour: tour,
      tips: tips,
      child: widget.child,
    );
  }
}

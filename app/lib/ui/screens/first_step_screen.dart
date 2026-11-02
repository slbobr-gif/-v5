// F1 «Первый шаг у Кремля» (docs/v5/09 §5): живой счётчик сразу после старта пути.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../engine/engine.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/route_map.dart';
import 'overflow_screens.dart' show safeBottom;
import 'settings_screen.dart';

final _num = NumberFormat.decimalPattern('ru');

class FirstStepScreen extends ConsumerStatefulWidget {
  const FirstStepScreen({super.key});

  @override
  ConsumerState<FirstStepScreen> createState() => _FirstStepScreenState();
}

class _FirstStepScreenState extends ConsumerState<FirstStepScreen> {
  Timer? _timer;
  final Stopwatch _clock = Stopwatch()..start();
  bool _closing = false;

  @override
  void initState() {
    super.initState();
    Analytics.instance.event('onboarding_step', {'name': 'first_step', 'back': false});
    // Первые 3 минуты — каждые 5 с, дальше обычный опрос главной (раз в минуту).
    _timer = Timer.periodic(const Duration(seconds: 5), (Timer t) {
      if (!mounted || _clock.elapsed.inMinutes >= 3) {
        t.cancel();
        return;
      }
      ref.read(appProvider.notifier).refresh();
      setState(() {});
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  int _stepsSoFar() {
    final hero = ref.read(appProvider).hero;
    if (hero == null) return 0;
    return hero.daySteps.values.fold<int>(0, (a, b) => a + b);
  }

  Future<void> _lookAround() async {
    if (_closing) return;
    _closing = true;
    final m = ref.read(appProvider);
    final st = m.stepsStatus;
    Analytics.instance.event('first_step_done', {
      'steps': _stepsSoFar(),
      'sensor_ok': st.sensorAvailable && st.activityPermission,
      'seconds': _clock.elapsed.inSeconds,
    });
    await ref.read(uiFlagsProvider.notifier).update((f) {
      f.firstStepDone = true;
      f.onboardingStep = '';
    });
    if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final content = m.content;
    final hero = m.hero;
    if (content == null || hero == null) return const Scaffold(body: SizedBox.shrink());
    final w = content.world;
    final eng = Engine(w, hero);
    final name = m.profile?.name.trim() ?? '';
    final steps = _stepsSoFar();
    final meters = hero.pos.round();
    // Первая остановка на маршруте: якорное событие или место.
    var firstStop = double.infinity;
    for (final a in w.anchored) {
      if (a.pos > 0 && a.pos < firstStop) firstStop = a.pos;
    }
    for (final p in w.stopsPlaces) {
      if (p.pos > 0 && p.pos < firstStop) firstStop = p.pos;
    }
    final perStep = eng.gameMetersPerStep();
    final goalSteps = firstStop.isFinite && perStep > 0 ? (firstStop / perStep).ceil() : 0;
    final prof = m.profile;
    final noSource = !m.stepsStatus.anyEnabled(sensor: prof?.stepsSensor ?? true, hc: prof?.stepsHc ?? true);
    final ok = steps >= 10;
    final slow = !ok && _clock.elapsed.inSeconds >= 60;
    final start = w.places.isEmpty ? '' : '${w.places.first['name']}';
    final kmNow = (hero.pos / 1000).toStringAsFixed(1).replaceAll('.', ',');
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (!didPop) _lookAround();
      },
      child: Scaffold(
        body: ListView(
          padding: EdgeInsets.only(bottom: safeBottom(context)),
          children: [
            SizedBox(
              height: 230 + MediaQuery.paddingOf(context).top,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: IgnorePointer(
                      child: RouteMap(content: content, heroPos: hero.pos, near: true),
                    ),
                  ),
                  // Positioned только с left/bottom даёт плашке неограниченную ширину: длинное имя места
                  // уходило за правый край. right ограничивает ширину, Align прижимает плашку влево по размеру текста.
                  Positioned(
                    left: Gap.m,
                    right: Gap.m,
                    bottom: Gap.s,
                    child: Align(
                      alignment: Alignment.centerLeft,
                      heightFactor: 1,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: Gap.s + 4, vertical: Gap.xs + 2),
                        decoration: BoxDecoration(
                          color: Palette.ink.withAlpha(210),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Palette.accentDeep),
                        ),
                        child: Text(
                          '$start · ${l.homeNextKm(kmNow)}',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l.firstStepTitle, style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: Gap.m),
                  StoryText(name.isEmpty ? l.firstStepBodyNoName : l.firstStepBody(name)),
                  const SizedBox(height: Gap.m),
                  Text(l.firstStepHint, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
                  const SizedBox(height: Gap.l),
                  SectionCard(
                    highlighted: ok,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Semantics(
                          liveRegion: true,
                          child: Text(
                            l.firstStepCounter(_num.format(steps), _num.format(meters)),
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                          ),
                        ),
                        if (goalSteps > 0) ...[
                          const SizedBox(height: Gap.s),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(5),
                            child: LinearProgressIndicator(
                              value: (steps / goalSteps).clamp(0.0, 1.0),
                              minHeight: 8,
                              color: Palette.accent,
                              backgroundColor: Palette.inkHigh,
                            ),
                          ),
                          const SizedBox(height: Gap.xs),
                          Text(l.firstStepGoal(_num.format(goalSteps)),
                              style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
                        ],
                        if (ok) ...[
                          const SizedBox(height: Gap.s),
                          Row(children: [
                            const Icon(Icons.check_circle, color: Palette.accent, size: 18),
                            const SizedBox(width: Gap.s),
                            Expanded(child: Text(l.firstStepOk, style: const TextStyle(color: Palette.accent))),
                          ]),
                        ] else if (noSource) ...[
                          const SizedBox(height: Gap.s),
                          Text(l.firstStepNoSource, style: const TextStyle(color: Palette.ember, height: 1.35)),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton(
                              onPressed: () => Navigator.of(context)
                                  .push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
                              child: Text(l.settingsTitle),
                            ),
                          ),
                        ] else if (slow) ...[
                          const SizedBox(height: Gap.s),
                          Text(l.firstStepSlow, style: const TextStyle(color: Palette.parchmentDim, height: 1.35)),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: Gap.l),
                  FilledButton(onPressed: _lookAround, child: Text(l.firstStepLook)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

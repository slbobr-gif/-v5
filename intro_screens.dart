// Вступление I1–I6 (docs/v5/09 §3): шесть витражей о сути игры. Из настроек — режим просмотра.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/item_icon.dart';

final _num = NumberFormat.decimalPattern('ru');

class _Slide {
  const _Slide(this.file, this.old, this.title, this.body, this.fact, this.alt);
  final String file;
  final String old;
  final String title;
  final String body;
  final String fact;
  final String alt;
}

/// [viewOnly] — повтор из настроек: «Пропустить» на всех слайдах, в конце «Закрыть», флаги не меняются.
/// [onDone] получает true, если слайды пропустили.
class IntroSlides extends ConsumerStatefulWidget {
  const IntroSlides({super.key, required this.onDone, this.viewOnly = false});

  final void Function(bool skipped) onDone;
  final bool viewOnly;

  @override
  ConsumerState<IntroSlides> createState() => _IntroSlidesState();
}

class _IntroSlidesState extends ConsumerState<IntroSlides> {
  final PageController _ctrl = PageController();
  final Set<int> _viewed = <int>{};
  final Stopwatch _clock = Stopwatch()..start();
  int _page = 0;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    _markViewed(0);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _markViewed(int i) {
    if (widget.viewOnly || _viewed.contains(i)) return;
    _viewed.add(i);
    Analytics.instance.event('intro_slide_viewed', {'n': i + 1});
  }

  void _finish(bool skipped) {
    if (_done) return;
    _done = true;
    if (!widget.viewOnly) {
      if (skipped) Analytics.instance.event('intro_skipped', {'from': _page + 1});
      Analytics.instance.event('intro_done', {'skipped': skipped, 'seconds': _clock.elapsed.inSeconds});
    }
    widget.onDone(skipped);
  }

  void _go(int i) {
    if (MediaQuery.disableAnimationsOf(context)) {
      _ctrl.jumpToPage(i);
    } else {
      _ctrl.animateToPage(i, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final lengthKm = m.content == null ? 0 : (m.content!.world.length / 1000).round();
    final slides = <_Slide>[
      _Slide('intro_1_city', 'routine', l.introSlide1Title, l.introSlide1Body, l.introSlide1Fact, l.introSlide1Alt),
      _Slide('intro_2_steps', 'count', l.introSlide2Title, l.introSlide2Body, l.introSlide2Fact, l.introSlide2Alt),
      _Slide('intro_3_route', 'world', l.introSlide3Title(_num.format(lengthKm)), l.introSlide3Body,
          l.introSlide3Fact, l.introSlide3Alt),
      _Slide('intro_4_spirits', 'world', l.introSlide4Title, l.introSlide4Body, l.introSlide4Fact, l.introSlide4Alt),
      _Slide('intro_5_stats', 'meet', l.introSlide5Title, l.introSlide5Body, l.introSlide5Fact, l.introSlide5Alt),
      _Slide('intro_6_sea', 'meet', l.introSlide6Title, l.introSlide6Body, l.introSlide6Fact, l.introSlide6Alt),
    ];
    final last = _page == slides.length - 1;
    final screenH = MediaQuery.sizeOf(context).height;
    final bigText = MediaQuery.textScalerOf(context).scale(16) > 24;
    final artH = (screenH * (bigText ? 0.28 : 0.36)).clamp(120.0, 260.0).toDouble();
    return PopScope(
      canPop: _page == 0,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (!didPop && _page > 0) _go(_page - 1);
      },
      child: Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: PageView.builder(
                  controller: _ctrl,
                  itemCount: slides.length,
                  onPageChanged: (int i) {
                    setState(() => _page = i);
                    _markViewed(i);
                  },
                  itemBuilder: (BuildContext ctx, int i) {
                    final s = slides[i];
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SizedBox(
                          height: artH,
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              Semantics(
                                label: s.alt,
                                image: true,
                                excludeSemantics: true,
                                child: FallbackArt(
                                  candidates: [
                                    'assets/art/intro/${s.file}.svg',
                                    'assets/art/onboarding/${s.old}.svg',
                                  ],
                                  height: artH,
                                  width: double.infinity,
                                ),
                              ),
                              if (widget.viewOnly ? i < slides.length - 1 : (i >= 2 && i <= 4))
                                Positioned(
                                  top: Gap.s,
                                  right: Gap.s,
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: Palette.ink.withAlpha(184),
                                      borderRadius: BorderRadius.circular(24),
                                    ),
                                    child: TextButton(
                                      style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                                      onPressed: () => _finish(true),
                                      child: Text(l.introSkip),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.fromLTRB(Gap.l, Gap.l, Gap.l, Gap.m),
                            child: MergeSemantics(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Semantics(
                                    label: l.introPageLabel(i + 1, slides.length),
                                    child: Text(s.title, style: const TextStyle(fontSize: 25, height: 1.2)),
                                  ),
                                  const SizedBox(height: Gap.m),
                                  Text(s.body, style: const TextStyle(fontSize: 16, height: 1.45)),
                                  const SizedBox(height: Gap.m),
                                  _FactPlate(text: s.fact),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
              Semantics(
                label: l.introPageLabel(_page + 1, slides.length),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    for (var i = 0; i < slides.length; i++)
                      Container(
                        margin: const EdgeInsets.all(4),
                        width: i == _page ? 24 : 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: i == _page ? Palette.accent : const Color(0xFF2A3B4F),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(Gap.l, Gap.m, Gap.l, Gap.l),
                child: FilledButton(
                  onPressed: last ? () => _finish(false) : () => _go(_page + 1),
                  child: Text(last ? (widget.viewOnly ? l.close : l.introStart) : l.next),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Бирюзовая плашка-факт: ромбик слева, одна мысль.
class _FactPlate extends StatelessWidget {
  const _FactPlate({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s + 2),
      decoration: BoxDecoration(
        color: Palette.accent.withAlpha(20),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Palette.accentDeep),
      ),
      child: Row(
        children: [
          Transform.rotate(
            angle: 0.785398,
            child: Container(width: 8, height: 8, color: Palette.accent),
          ),
          const SizedBox(width: Gap.s + 4),
          Expanded(
            child: Text(text, style: const TextStyle(color: Palette.accent, fontSize: 14, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}

/// «Как играть» из настроек.
class IntroReplayScreen extends StatelessWidget {
  const IntroReplayScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return IntroSlides(viewOnly: true, onDone: (_) => Navigator.of(context).pop());
  }
}

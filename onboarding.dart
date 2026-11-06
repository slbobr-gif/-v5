// Вход в игру (docs/v5/09 §2–§4): вступление → имя и согласие → шаги (разрешения, источники) →
// «Собери рюкзак» → пролог → старт пути. Шаг сохраняется: закрыли приложение — вернёмся сюда же.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/item_icon.dart';
import 'intro_screens.dart';
import 'loadout_screen.dart';
import 'overflow_screens.dart' show safeBottom;
import 'watch_help_screen.dart';

const _order = <String>['profile', 'perm_activity', 'perm_notify', 'perm_hc', 'sources', 'loadout', 'prologue'];

int _stageOf(String step) => switch (step) {
      'profile' => 0,
      'loadout' => 2,
      'prologue' => 3,
      _ => 1,
    };

class OnboardingFlow extends ConsumerStatefulWidget {
  const OnboardingFlow({super.key});

  @override
  ConsumerState<OnboardingFlow> createState() => _OnboardingFlowState();
}

class _OnboardingFlowState extends ConsumerState<OnboardingFlow> {
  String? _step;
  final List<String> _history = <String>[];
  bool _introThisSession = false;

  @override
  void initState() {
    super.initState();
    final m = ref.read(appProvider);
    final p = m.profile;
    Future.microtask(() async {
      await ref.read(uiFlagsProvider.notifier).ensureLoaded(
            onboarded: p?.onboarded ?? false,
            hasProfile: _profileOk,
            hasHero: m.hero != null,
          );
      if (mounted) _pickStart();
    });
  }

  bool get _profileOk {
    final p = ref.read(appProvider).profile;
    return p != null && p.name.trim().length >= 2 && p.consent;
  }

  bool _skippable(String step) {
    final m = ref.read(appProvider);
    final st = m.stepsStatus;
    switch (step) {
      case 'perm_activity':
        return !st.sensorAvailable || st.activityPermission;
      case 'perm_notify':
        return m.notifyPermission;
      case 'perm_hc':
        return st.hcStatus == 'unavailable' || st.hcPermission;
    }
    return false;
  }

  String _firstShown(int from) {
    for (var i = from; i < _order.length; i++) {
      if (!_skippable(_order[i])) return _order[i];
    }
    return _order.last;
  }

  Future<void> _pickStart() async {
    final flags = ref.read(uiFlagsProvider);
    String step;
    if (!flags.introDone) {
      step = 'intro';
    } else if (flags.onboardingStep.isEmpty) {
      // Путь сброшен («Начать заново»): сразу рюкзак, если имя и согласие уже есть (§7.4).
      if (_profileOk) {
        await ref.read(uiFlagsProvider.notifier).startOverAfterReset();
        step = 'loadout';
      } else {
        step = 'profile';
      }
    } else {
      step = flags.onboardingStep;
      if (!_order.contains(step)) step = 'profile';
      if (step != 'profile' && !_profileOk) step = 'profile';
      if (_skippable(step)) step = _firstShown(_order.indexOf(step));
    }
    if (!mounted) return;
    _enter(step, back: false);
  }

  void _enter(String step, {required bool back}) {
    setState(() => _step = step);
    if (step == 'intro') return;
    ref.read(uiFlagsProvider.notifier).update((f) => f.onboardingStep = step);
    Analytics.instance.event('onboarding_step', {'name': step, 'back': back});
  }

  void _go(String step) {
    final cur = _step;
    if (cur != null && cur != 'intro') _history.add(cur);
    _enter(step, back: false);
  }

  void _next() {
    final cur = _step ?? 'profile';
    final i = _order.indexOf(cur);
    _go(_firstShown(i + 1));
  }

  void _back() {
    if (_history.isNotEmpty) {
      _enter(_history.removeLast(), back: true);
      return;
    }
    // O1 → I6, если вступление было в этой сессии; иначе назад некуда (на O6 после сброса — тоже).
    if (_step == 'profile' && _introThisSession) setState(() => _step = 'intro');
  }

  PreferredSizeWidget _bar(String step) => _StageBar(stage: _stageOf(step));

  @override
  Widget build(BuildContext context) {
    final step = _step;
    if (step == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    switch (step) {
      case 'intro':
        return IntroSlides(onDone: (bool skipped) async {
          _introThisSession = true;
          await ref.read(uiFlagsProvider.notifier).update((f) {
            f.introDone = true;
            f.onboardingStep = 'profile';
          });
          if (mounted) _enter('profile', back: false);
        });
      case 'profile':
        return _ProfileStep(bar: _bar(step), onDone: _next, onBack: _history.isNotEmpty || _introThisSession ? _back : null);
      case 'perm_activity':
        return _ActivityStep(
          bar: _bar(step),
          onDone: _next,
          onBack: _back,
          onUseHc: () => _go('perm_hc'),
          onSkip: () => _go('sources'),
        );
      case 'perm_notify':
        return _NotifyStep(bar: _bar(step), onDone: _next, onBack: _back);
      case 'perm_hc':
        return _HealthStep(bar: _bar(step), onDone: _next, onBack: _back);
      case 'sources':
        return _SourcesStep(
          bar: _bar(step),
          onDone: _next,
          onBack: _back,
          onFix: () {
            final st = ref.read(appProvider).stepsStatus;
            _go(st.sensorAvailable ? 'perm_activity' : 'perm_hc');
          },
        );
      case 'loadout':
        return LoadoutScreen(stageBar: _bar(step), onDone: _next, onBack: _back);
      default:
        return _PrologueStep(bar: _bar(step), onBack: () => _enter('loadout', back: true));
    }
  }
}

// ---------------------------------------------------------------- полоса этапов

class _StageBar extends StatelessWidget implements PreferredSizeWidget {
  const _StageBar({required this.stage});
  final int stage;

  @override
  Size get preferredSize => const Size.fromHeight(34);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final names = [l.onbStageMeet, l.onbStageSteps, l.onbStagePack, l.onbStageStory];
    return Semantics(
      label: l.onbStageLabel(stage + 1, names.length, names[stage]),
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(Gap.m, 0, Gap.m, Gap.s),
        // AppBar.bottom: высота фиксирована preferredSize (34) — подписи не растут выше 1,2,
        // иначе полоса этапов не помещается и обрезается.
        child: MediaQuery.withClampedTextScaling(
          maxScaleFactor: 1.2,
          child: Row(
            children: [
              for (var i = 0; i < names.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: Column(
                    // min: в AppBar.bottom высота не ограничена — колонка по содержимому, а не «на всё».
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        height: 4,
                        decoration: BoxDecoration(
                          color: i == stage
                              ? Palette.accent
                              : (i < stage ? Palette.accentDeep : const Color(0xFF2A3B4F)),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        names[i],
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11,
                          color: i == stage ? Palette.accent : Palette.parchmentDim,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Каркас шага: AppBar с «назад», полоса этапов, прокручиваемое содержимое, кнопки внизу над жестовой панелью.
class _StepScaffold extends StatelessWidget {
  const _StepScaffold({
    required this.title,
    required this.bar,
    required this.children,
    required this.buttons,
    this.onBack,
  });

  final String title;
  final PreferredSizeWidget bar;
  final List<Widget> children;
  final List<Widget> buttons;
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    final back = onBack;
    return PopScope(
      canPop: back == null,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (!didPop && back != null) back();
      },
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          leading: back == null ? null : IconButton(icon: const Icon(Icons.arrow_back), onPressed: back),
          title: Text(title),
          bottom: bar,
        ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.l, Gap.m, Gap.l, Gap.m),
                children: children,
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) - Gap.s),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: buttons,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

const _bodyStyle = TextStyle(fontSize: 16, height: 1.45);
const _dimStyle = TextStyle(color: Palette.parchmentDim, height: 1.4);

Widget _secondary(String text, VoidCallback? onTap) => TextButton(
      style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48)),
      onPressed: onTap,
      child: Text(text),
    );

Widget _okLine(String text) => Padding(
      padding: const EdgeInsets.only(top: Gap.m),
      child: Row(children: [
        const Icon(Icons.check_circle, color: Palette.accent),
        const SizedBox(width: Gap.s),
        Expanded(child: Text(text, style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w600))),
      ]),
    );

// ---------------------------------------------------------------- O1 имя, почта, согласие

class _ProfileStep extends ConsumerStatefulWidget {
  const _ProfileStep({required this.bar, required this.onDone, this.onBack});
  final PreferredSizeWidget bar;
  final VoidCallback onDone;
  final VoidCallback? onBack;

  @override
  ConsumerState<_ProfileStep> createState() => _ProfileStepState();
}

class _ProfileStepState extends ConsumerState<_ProfileStep> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _nameFocus = FocusNode();
  final _emailFocus = FocusNode();
  bool _consent = false;
  bool _nameTouched = false;
  bool _more = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final p = ref.read(appProvider).profile;
    if (p != null) {
      _name.text = p.name;
      _email.text = p.email;
      _consent = p.consent;
    }
    _nameFocus.addListener(() {
      if (!_nameFocus.hasFocus && mounted) setState(() => _nameTouched = true);
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _nameFocus.dispose();
    _emailFocus.dispose();
    super.dispose();
  }

  bool get _nameOk => _name.text.trim().length >= 2;

  bool get _emailOk {
    final e = _email.text.trim();
    return e.isEmpty || RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(e);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final canGo = _nameOk && _emailOk && _consent && !_saving;
    return _StepScaffold(
      title: l.onbNameTitle,
      bar: widget.bar,
      onBack: widget.onBack,
      children: [
        Text(l.onbNameBody, style: _dimStyle),
        const SizedBox(height: Gap.l),
        TextField(
          controller: _name,
          focusNode: _nameFocus,
          textCapitalization: TextCapitalization.words,
          textInputAction: TextInputAction.next,
          onSubmitted: (_) => _emailFocus.requestFocus(),
          decoration: InputDecoration(
            labelText: l.onbNameLabel,
            hintText: l.onbNameHint,
            errorText: _nameTouched && !_nameOk ? l.onbNameShort : null,
            border: const OutlineInputBorder(),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Gap.m),
        TextField(
          controller: _email,
          focusNode: _emailFocus,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(
            labelText: l.onbEmailLabel,
            helperText: l.profileEmailHelp,
            helperMaxLines: 3,
            errorText: _emailOk ? null : l.profileEmailBad,
            border: const OutlineInputBorder(),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Gap.m),
        CheckboxListTile(
          value: _consent,
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          onChanged: (bool? v) => setState(() => _consent = v ?? false),
          title: Text(l.profileConsent, style: const TextStyle(fontSize: 13, height: 1.35)),
        ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
            onPressed: () => setState(() => _more = !_more),
            child: Text(l.onbConsentMore),
          ),
        ),
        if (_more) Text(l.onbConsentMoreBody, style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.4)),
      ],
      buttons: [
        if (_nameOk && _emailOk && !_consent)
          Padding(
            padding: const EdgeInsets.only(bottom: Gap.s),
            child: Text(l.onbConsentNeeded, style: const TextStyle(color: Palette.ember, fontSize: 13, height: 1.35)),
          ),
        FilledButton(
          onPressed: canGo
              ? () async {
                  setState(() => _saving = true);
                  await ref.read(appProvider.notifier).saveProfile(name: _name.text, email: _email.text, consent: _consent);
                  if (!mounted) return;
                  setState(() => _saving = false);
                  widget.onDone();
                }
              : null,
          child: Text(l.next),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------- O2 физическая активность

class _ActivityStep extends ConsumerStatefulWidget {
  const _ActivityStep({
    required this.bar,
    required this.onDone,
    required this.onBack,
    required this.onUseHc,
    required this.onSkip,
  });

  final PreferredSizeWidget bar;
  final VoidCallback onDone;
  final VoidCallback onBack;
  final VoidCallback onUseHc;
  final VoidCallback onSkip;

  @override
  ConsumerState<_ActivityStep> createState() => _ActivityStepState();
}

class _ActivityStepState extends ConsumerState<_ActivityStep> {
  bool _denied = false;
  bool _leaving = false;

  void _grantedThenNext() {
    if (_leaving) return;
    _leaving = true;
    Timer(const Duration(milliseconds: 600), () {
      if (mounted) widget.onDone();
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.stepsStatus;
    final granted = st.activityPermission;
    // Разрешили в системных настройках и вернулись — сами идём дальше.
    if (granted) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _grantedThenNext());
    }
    final hcPossible = st.hcStatus != 'unavailable';
    return _StepScaffold(
      title: l.onbStageSteps,
      bar: widget.bar,
      onBack: widget.onBack,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(Gap.radius),
          child: const FallbackArt(
            candidates: ['assets/art/intro/intro_2_steps.svg', 'assets/art/onboarding/count.svg'],
            height: 150,
            width: double.infinity,
          ),
        ),
        const SizedBox(height: Gap.l),
        Text(l.onbActTitle, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: Gap.m),
        Text(l.onbActBody, style: _bodyStyle),
        const SizedBox(height: Gap.m),
        SectionCard(
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(Icons.info_outline, color: Palette.accent, size: 20),
            const SizedBox(width: Gap.s),
            Expanded(child: Text(l.onbBatteryLine, style: const TextStyle(fontSize: 13, height: 1.4))),
          ]),
        ),
        if (granted) _okLine(l.onbActGranted),
        if (_denied && !granted) ...[
          const SizedBox(height: Gap.m),
          Text(l.onbActDenied, style: const TextStyle(color: Palette.ember, height: 1.4)),
        ],
      ],
      buttons: granted
          ? const <Widget>[]
          : _denied
              ? [
                  FilledButton(
                    onPressed: () async {
                      final ok = await c.requestActivityPermission();
                      if (mounted && !ok) setState(() => _denied = true);
                    },
                    child: Text(l.onbRetry),
                  ),
                  if (hcPossible) _secondary('${l.onbHcConnect} ${l.permHcTitle}', widget.onUseHc),
                  _secondary(l.permContinueAnyway, widget.onSkip),
                ]
              : [
                  FilledButton(
                    onPressed: () async {
                      final ok = await c.requestActivityPermission();
                      if (mounted && !ok) setState(() => _denied = true);
                    },
                    child: Text(l.permAllow),
                  ),
                  // «Не сейчас» — без системного диалога, чтобы не сгорела попытка запроса.
                  _secondary(l.onbActLater, () => setState(() => _denied = true)),
                ],
    );
  }
}

// ---------------------------------------------------------------- O3 уведомления

class _NotifyStep extends ConsumerWidget {
  const _NotifyStep({required this.bar, required this.onDone, required this.onBack});
  final PreferredSizeWidget bar;
  final VoidCallback onDone;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final p = m.profile;
    final h = p?.morningHour ?? 8;
    final mi = p?.morningMinute ?? 0;
    final time = '${h.toString().padLeft(2, '0')}:${mi.toString().padLeft(2, '0')}';
    return _StepScaffold(
      title: l.onbStageSteps,
      bar: bar,
      onBack: onBack,
      children: [
        Text(l.onbNotifyTitle, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: Gap.m),
        Text(l.onbNotifyBody, style: _bodyStyle),
        const SizedBox(height: Gap.l),
        SectionCard(
          padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.xs),
          child: Row(children: [
            const Icon(Icons.wb_twilight, color: Palette.accent),
            const SizedBox(width: Gap.s),
            Expanded(child: Text(l.onbNotifyTime(time))),
            TextButton(
              style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: () async {
                final picked = await showTimePicker(context: context, initialTime: TimeOfDay(hour: h, minute: mi));
                if (picked != null) {
                  await c.updateProfile((pp) {
                    pp.morningHour = picked.hour;
                    pp.morningMinute = picked.minute;
                  });
                }
              },
              child: Text(l.onbChange),
            ),
          ]),
        ),
      ],
      buttons: [
        FilledButton(
          onPressed: () async {
            final messenger = ScaffoldMessenger.of(context);
            final ok = await c.requestNotifyPermission();
            if (!ok) messenger.showSnackBar(SnackBar(content: Text(l.onbNotifyDenied)));
            onDone();
          },
          child: Text(l.permNotifyAllow),
        ),
        _secondary(l.onbNotifySkip, onDone),
      ],
    );
  }
}

// ---------------------------------------------------------------- O4 Health Connect

class _HealthStep extends ConsumerStatefulWidget {
  const _HealthStep({required this.bar, required this.onDone, required this.onBack});
  final PreferredSizeWidget bar;
  final VoidCallback onDone;
  final VoidCallback onBack;

  @override
  ConsumerState<_HealthStep> createState() => _HealthStepState();
}

class _HealthStepState extends ConsumerState<_HealthStep> {
  bool _leaving = false;

  void _grantedThenNext() {
    if (_leaving) return;
    _leaving = true;
    Timer(const Duration(milliseconds: 600), () {
      if (mounted) widget.onDone();
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.stepsStatus;
    if (st.hcPermission) WidgetsBinding.instance.addPostFrameCallback((_) => _grantedThenNext());
    final needInstall = st.hcStatus == 'not_installed' || st.hcStatus == 'update_required';
    return _StepScaffold(
      title: l.onbStageSteps,
      bar: widget.bar,
      onBack: widget.onBack,
      children: [
        Text(l.onbHcTitle, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: Gap.s),
        Text(
          st.sensorAvailable ? l.permOptional : l.onbHcRequired,
          style: TextStyle(color: st.sensorAvailable ? Palette.parchmentDim : Palette.ember, fontSize: 13, height: 1.35),
        ),
        const SizedBox(height: Gap.m),
        Text(l.onbHcBody, style: _bodyStyle),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            icon: const Icon(Icons.watch_outlined),
            label: Text(l.watchHelpOpen),
            onPressed: () =>
                Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const WatchHelpScreen())),
          ),
        ),
        if (needInstall) ...[
          const SizedBox(height: Gap.m),
          SectionCard(
            child: Text(st.hcStatus == 'update_required' ? l.permHcUpdate : l.permHcInstall,
                style: const TextStyle(height: 1.4)),
          ),
        ],
        if (st.hcPermission) _okLine(l.onbSrcOn),
      ],
      buttons: st.hcPermission
          ? const <Widget>[]
          : [
              FilledButton(
                onPressed: () async {
                  if (needInstall) {
                    await c.openHealthConnectInstall();
                    return;
                  }
                  final messenger = ScaffoldMessenger.of(context);
                  final ok = await c.requestHealthPermission();
                  if (!ok) messenger.showSnackBar(SnackBar(content: Text(l.onbHcDenied)));
                },
                child: Text(needInstall ? l.permHcInstallAction : l.onbHcConnect),
              ),
              _secondary(l.onbHcSkip, widget.onDone),
            ],
    );
  }
}

// ---------------------------------------------------------------- O5 источники шагов

class _SourcesStep extends ConsumerStatefulWidget {
  const _SourcesStep({required this.bar, required this.onDone, required this.onBack, required this.onFix});
  final PreferredSizeWidget bar;
  final VoidCallback onDone;
  final VoidCallback onBack;
  final VoidCallback onFix;

  @override
  ConsumerState<_SourcesStep> createState() => _SourcesStepState();
}

class _SourcesStepState extends ConsumerState<_SourcesStep> {
  late bool _sensor;
  late bool _hc;

  @override
  void initState() {
    super.initState();
    final p = ref.read(appProvider).profile;
    _sensor = p?.stepsSensor ?? true;
    _hc = p?.stepsHc ?? true;
  }

  Future<void> _go() async {
    final l = AppLocalizations.of(context);
    final st = ref.read(appProvider).stepsStatus;
    final c = ref.read(appProvider.notifier);
    await c.setStepSources(sensor: _sensor, hc: _hc);
    if (!mounted) return;
    if (st.anyEnabled(sensor: _sensor, hc: _hc)) {
      widget.onDone();
      return;
    }
    final go = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        title: Text(l.onbNoStepsTitle),
        content: Text(l.onbNoStepsBody),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(l.onbNoStepsFix)),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.onbNoStepsGo)),
        ],
      ),
    );
    if (!mounted || go == null) return;
    if (go) {
      Analytics.instance.event('onboarding_no_steps');
      widget.onDone();
    } else {
      widget.onFix();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.stepsStatus;
    final sensorReady = st.sensorAvailable && st.activityPermission;
    final hcReady = st.hcStatus == 'available' && st.hcPermission;
    final none = !st.anyEnabled(sensor: _sensor, hc: _hc);
    final String sensorStatus = !st.sensorAvailable
        ? l.onbSrcMissing
        : (st.activityPermission ? l.onbSrcOn : l.onbSrcNoPerm);
    final String hcStatus = switch (st.hcStatus) {
      'unavailable' => l.onbSrcMissing,
      'not_installed' || 'update_required' => l.onbSrcNotInstalled,
      _ => st.hcPermission ? l.onbSrcOn : l.onbSrcNoPerm,
    };
    final sensorConnect = st.sensorAvailable && !st.activityPermission;
    final hcConnect = st.hcStatus != 'unavailable' && !st.hcPermission;
    return _StepScaffold(
      title: l.onbStageSteps,
      bar: widget.bar,
      onBack: widget.onBack,
      children: [
        Text(l.onbSrcTitle, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: Gap.m),
        Text(l.onbSrcBody, style: _bodyStyle),
        const SizedBox(height: Gap.m),
        _SourceRow(
          icon: Icons.directions_walk,
          title: l.permSensorTitle,
          status: sensorStatus,
          value: sensorReady && _sensor,
          onChanged: sensorReady ? (bool v) => setState(() => _sensor = v) : null,
          connect: sensorConnect ? l.onbSrcConnect : null,
          onConnect: () async {
            final ok = await c.requestActivityPermission();
            if (ok && mounted) setState(() => _sensor = true);
          },
        ),
        const SizedBox(height: Gap.s),
        _SourceRow(
          icon: Icons.favorite_outline,
          title: l.permHcTitle,
          status: hcStatus,
          value: hcReady && _hc,
          onChanged: hcReady ? (bool v) => setState(() => _hc = v) : null,
          connect: hcConnect ? l.onbSrcConnect : null,
          onConnect: () async {
            if (st.hcStatus == 'available') {
              final ok = await c.requestHealthPermission();
              if (ok && mounted) setState(() => _hc = true);
            } else {
              await c.openHealthConnectInstall();
            }
          },
        ),
        if (m.todaySteps > 0) ...[
          const SizedBox(height: Gap.m),
          Text(l.onbSrcToday('${m.todaySteps}'), style: _dimStyle),
        ],
        if (none) ...[
          const SizedBox(height: Gap.m),
          Text(l.onbSrcNone, style: const TextStyle(color: Palette.danger, height: 1.35)),
        ],
      ],
      buttons: [
        FilledButton(onPressed: _go, child: Text(l.onbSrcNext)),
      ],
    );
  }
}

class _SourceRow extends StatelessWidget {
  const _SourceRow({
    required this.icon,
    required this.title,
    required this.status,
    required this.value,
    required this.onChanged,
    required this.connect,
    required this.onConnect,
  });

  final IconData icon;
  final String title;
  final String status;
  final bool value;
  final ValueChanged<bool>? onChanged;
  final String? connect;
  final Future<void> Function() onConnect;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      highlighted: value,
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, color: value ? Palette.accent : Palette.parchmentDim),
            const SizedBox(width: Gap.s),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                Text(status, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
              ]),
            ),
            Switch(value: value, onChanged: onChanged),
          ]),
          if (connect != null)
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44)),
                onPressed: () => onConnect(),
                child: Text(connect!),
              ),
            ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- O7 пролог

/// Страницы пролога из chapters.json. [onFinish] — последняя кнопка, [onSkip] — «Пропустить» (со 2-й страницы).
class PrologueView extends ConsumerStatefulWidget {
  const PrologueView({
    super.key,
    required this.finishLabel,
    required this.onFinish,
    this.onSkip,
    this.onBack,
    this.bar,
    this.initialPage = 0,
    this.onPage,
  });

  final String finishLabel;
  final Future<void> Function(int pages) onFinish;
  final Future<void> Function(int pages)? onSkip;
  final VoidCallback? onBack;
  final PreferredSizeWidget? bar;
  final int initialPage;
  final ValueChanged<int>? onPage;

  @override
  ConsumerState<PrologueView> createState() => _PrologueViewState();
}

class _PrologueViewState extends ConsumerState<PrologueView> {
  late int _i;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _i = widget.initialPage;
  }

  void _setPage(int i) {
    setState(() => _i = i);
    final cb = widget.onPage;
    if (cb != null) cb(i);
  }

  void _back() {
    if (_i > 0) {
      _setPage(_i - 1);
      return;
    }
    final b = widget.onBack;
    if (b != null) {
      b();
    } else {
      Navigator.of(context).maybePop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final ch1 = m.content!.world.chapterById(1);
    final pages = ((ch1['prologue'] as List?) ?? const []).cast<String>();
    final count = pages.isEmpty ? 1 : pages.length;
    if (_i >= count) _i = count - 1;
    final last = _i >= count - 1;
    final skip = widget.onSkip;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (!didPop) _back();
      },
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: _back),
          title: Text(l.onbStageStory),
          bottom: widget.bar,
          actions: [
            if (skip != null && _i >= 1)
              TextButton(
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                onPressed: _busy
                    ? null
                    : () async {
                        setState(() => _busy = true);
                        await skip(_i + 1);
                        if (mounted) setState(() => _busy = false);
                      },
                child: Text(l.onbPrologueSkip),
              ),
          ],
        ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(Gap.l, Gap.m, Gap.l, Gap.m),
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(Gap.radius),
                    child: const FallbackArt(
                      candidates: ['assets/art/scenes/night.svg'],
                      height: 150,
                      width: double.infinity,
                    ),
                  ),
                  const SizedBox(height: Gap.m),
                  Text(l.prologueTitle, style: const TextStyle(color: Palette.accent, letterSpacing: 2)),
                  const SizedBox(height: Gap.m),
                  StoryText(
                    pages.isEmpty ? '' : pages[_i],
                    key: ValueKey<int>(_i),
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.55, fontSize: 17),
                  ),
                ],
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(Gap.l, Gap.s, Gap.l, safeBottom(context) - Gap.s),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('${_i + 1} / $count', textAlign: TextAlign.center, style: _dimStyle),
                  const SizedBox(height: Gap.s),
                  FilledButton(
                    onPressed: _busy
                        ? null
                        : () async {
                            if (!last) {
                              _setPage(_i + 1);
                              return;
                            }
                            setState(() => _busy = true);
                            await widget.onFinish(count);
                            if (mounted) setState(() => _busy = false);
                          },
                    child: Text(last ? widget.finishLabel : l.next),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PrologueStep extends ConsumerWidget {
  const _PrologueStep({required this.bar, required this.onBack});
  final PreferredSizeWidget bar;
  final VoidCallback onBack;

  Future<void> _start(BuildContext context, WidgetRef ref, {required bool skipped, required int pages}) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final c = ref.read(appProvider.notifier);
    final flagsCtl = ref.read(uiFlagsProvider.notifier);
    final f = ref.read(uiFlagsProvider);
    // Выбор рюкзака уже передан на O6; повторяем из черновика на случай перезапуска приложения.
    final gear = f.loadoutGear;
    final pack = f.loadoutPack;
    if (gear != null || pack != null) {
      c.chooseLoadout(gear ?? <String>[], pack ?? <String, int>{}, isDefault: f.loadoutAdvisor);
    }
    Analytics.instance.event('prologue_done', {'skipped': skipped, 'pages': pages});
    await flagsCtl.update((ff) {
      ff.firstStepDone = false;
      ff.prologuePage = 0;
    });
    await c.markPrologueRead();
    await c.startJourney();
    await flagsCtl.update((ff) {
      ff.onboardingStep = '';
      ff.loadoutGear = null;
      ff.loadoutPack = null;
      ff.loadoutAdvisor = false;
    });
    if (skipped) messenger.showSnackBar(SnackBar(content: Text(l.onbPrologueLater)));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final f = ref.read(uiFlagsProvider);
    return PrologueView(
      bar: bar,
      onBack: onBack,
      initialPage: f.prologuePage,
      onPage: (int i) => ref.read(uiFlagsProvider.notifier).update((ff) => ff.prologuePage = i),
      finishLabel: l.prologueGo,
      onFinish: (int pages) => _start(context, ref, skipped: false, pages: pages),
      onSkip: (int pages) => _start(context, ref, skipped: true, pages: pages),
    );
  }
}

/// «Перечитать пролог» из настроек: только чтение.
class PrologueReplayScreen extends StatelessWidget {
  const PrologueReplayScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return PrologueView(
      finishLabel: l.close,
      onFinish: (int pages) async => Navigator.of(context).pop(),
    );
  }
}

// ---------------------------------------------------------------- плитка разрешения (настройки)

class PermissionTile extends StatelessWidget {
  const PermissionTile({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    required this.done,
    required this.action,
    required this.onAction,
    this.optional = false,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool done;
  final String? action;
  final Future<Object?> Function() onAction;
  final bool optional;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return SectionCard(
      highlighted: done,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: done ? Palette.accent : Palette.parchmentDim),
              const SizedBox(width: Gap.s),
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
              if (done)
                const Icon(Icons.check_circle, color: Palette.accent)
              else if (optional)
                Text(l.permOptional, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
            ],
          ),
          const SizedBox(height: Gap.s),
          Text(body, style: const TextStyle(color: Palette.parchmentDim, height: 1.35)),
          if (action != null) ...[
            const SizedBox(height: Gap.s),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44)),
                onPressed: () => onAction(),
                child: Text(action!),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

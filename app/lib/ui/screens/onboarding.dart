// Онбординг: 4 слайда → имя и почта → разрешения (шаги, уведомления) → пролог → старт.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';

class OnboardingFlow extends ConsumerStatefulWidget {
  const OnboardingFlow({super.key});

  @override
  ConsumerState<OnboardingFlow> createState() => _OnboardingFlowState();
}

class _OnboardingFlowState extends ConsumerState<OnboardingFlow> {
  int _stage = 0; // 0 слайды, 1 профиль, 2 разрешения, 3 пролог

  @override
  void initState() {
    super.initState();
    final p = ref.read(appProvider).profile;
    if (p != null && p.name.isNotEmpty && p.consent) _stage = 2;
  }

  @override
  Widget build(BuildContext context) {
    switch (_stage) {
      case 0:
        return _Slides(onDone: () => setState(() => _stage = 1));
      case 1:
        return _ProfileForm(onDone: () => setState(() => _stage = 2));
      case 2:
        return _Permissions(onDone: () => setState(() => _stage = 3));
      default:
        return const _Prologue();
    }
  }
}

// ---------------------------------------------------------------- слайды

class _Slides extends ConsumerStatefulWidget {
  const _Slides({required this.onDone});
  final VoidCallback onDone;

  @override
  ConsumerState<_Slides> createState() => _SlidesState();
}

class _SlidesState extends ConsumerState<_Slides> {
  final _ctrl = PageController();
  int _page = 0;

  @override
  void initState() {
    super.initState();
    ref.read(appProvider.notifier).onboardingSlide(0);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final slides = [
      ('routine', l.onb1Title, l.onb1Body),
      ('count', l.onb2Title, l.onb2Body),
      ('world', l.onb3Title, l.onb3Body),
      ('meet', l.onb4Title, l.onb4Body),
    ];
    final last = _page == slides.length - 1;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: last ? null : () => _ctrl.jumpToPage(slides.length - 1),
                child: Text(last ? '' : l.onbSkip),
              ),
            ),
            Expanded(
              child: PageView(
                controller: _ctrl,
                onPageChanged: (i) {
                  setState(() => _page = i);
                  ref.read(appProvider.notifier).onboardingSlide(i);
                },
                children: [
                  for (final s in slides)
                    SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: Gap.l),
                      child: Column(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(Gap.radius),
                            child: Art('assets/art/onboarding/${s.$1}.svg', height: 240, fit: BoxFit.cover),
                          ),
                          const SizedBox(height: Gap.l),
                          Text(s.$2, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
                          const SizedBox(height: Gap.m),
                          Text(
                            s.$3,
                            textAlign: TextAlign.center,
                            style: Theme.of(context)
                                .textTheme
                                .bodyLarge
                                ?.copyWith(color: Palette.parchmentDim, height: 1.4),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < slides.length; i++)
                  Container(
                    margin: const EdgeInsets.all(4),
                    width: i == _page ? 22 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: i == _page ? Palette.gold : Palette.inkHigh,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(Gap.l),
              child: FilledButton(
                onPressed: last
                    ? widget.onDone
                    : () => _ctrl.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                child: Text(last ? l.onbStart : l.onbNext),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- профиль

class _ProfileForm extends ConsumerStatefulWidget {
  const _ProfileForm({required this.onDone});
  final VoidCallback onDone;

  @override
  ConsumerState<_ProfileForm> createState() => _ProfileFormState();
}

class _ProfileFormState extends ConsumerState<_ProfileForm> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  bool _consent = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    super.dispose();
  }

  bool get _emailOk {
    final e = _email.text.trim();
    return e.isEmpty || RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(e);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final canGo = _name.text.trim().length >= 2 && _emailOk && _consent;
    return Scaffold(
      appBar: AppBar(title: Text(l.profileTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            Text(l.profileIntro, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
            const SizedBox(height: Gap.l),
            TextField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration: InputDecoration(labelText: l.profileName, border: const OutlineInputBorder()),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: Gap.m),
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                labelText: l.profileEmail,
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
              onChanged: (v) => setState(() => _consent = v ?? false),
              title: Text(l.profileConsent, style: const TextStyle(fontSize: 13, height: 1.35)),
            ),
            const SizedBox(height: Gap.l),
            FilledButton(
              onPressed: canGo
                  ? () async {
                      await ref
                          .read(appProvider.notifier)
                          .saveProfile(name: _name.text, email: _email.text, consent: _consent);
                      widget.onDone();
                    }
                  : null,
              child: Text(l.onbNext),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- разрешения

class _Permissions extends ConsumerWidget {
  const _Permissions({required this.onDone});
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final st = m.stepsStatus;
    final sensorOk = st.sensorAvailable && st.activityPermission;
    return Scaffold(
      appBar: AppBar(title: Text(l.permTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            Text(l.permIntro, style: const TextStyle(color: Palette.parchmentDim, height: 1.4)),
            const SizedBox(height: Gap.l),
            PermissionTile(
              icon: Icons.directions_walk,
              title: l.permSensorTitle,
              body: st.sensorAvailable ? l.permSensorBody : l.permSensorMissing,
              done: sensorOk,
              action: st.sensorAvailable && !sensorOk ? l.permAllow : null,
              onAction: c.requestActivityPermission,
            ),
            const SizedBox(height: Gap.m),
            PermissionTile(
              icon: Icons.favorite_outline,
              title: l.permHcTitle,
              body: switch (st.hcStatus) {
                'available' => l.permHcBody,
                'update_required' => l.permHcUpdate,
                'not_installed' => l.permHcInstall,
                _ => l.permHcUnavailable,
              },
              done: st.hcPermission,
              action: st.hcPermission
                  ? null
                  : switch (st.hcStatus) {
                      'available' => l.permAllow,
                      'update_required' || 'not_installed' => l.permHcInstallAction,
                      _ => null,
                    },
              onAction: st.hcStatus == 'available' ? c.requestHealthPermission : c.openHealthConnectInstall,
              optional: true,
            ),
            const SizedBox(height: Gap.m),
            PermissionTile(
              icon: Icons.notifications_none,
              title: l.permNotifyTitle,
              body: l.permNotifyBody,
              done: m.notifyPermission,
              action: m.notifyPermission ? null : l.permAllow,
              onAction: c.requestNotifyPermission,
              optional: true,
            ),
            const SizedBox(height: Gap.l),
            if (!st.anySource)
              Padding(
                padding: const EdgeInsets.only(bottom: Gap.m),
                child: Text(l.permNoSource, style: const TextStyle(color: Palette.danger, height: 1.35)),
              ),
            FilledButton(onPressed: onDone, child: Text(st.anySource ? l.onbNext : l.permContinueAnyway)),
          ],
        ),
      ),
    );
  }
}

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
              Icon(icon, color: done ? Palette.gold : Palette.parchmentDim),
              const SizedBox(width: Gap.s),
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
              if (done)
                const Icon(Icons.check_circle, color: Palette.gold)
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

// ---------------------------------------------------------------- пролог

class _Prologue extends ConsumerStatefulWidget {
  const _Prologue();

  @override
  ConsumerState<_Prologue> createState() => _PrologueState();
}

class _PrologueState extends ConsumerState<_Prologue> {
  int _i = 0;
  bool _starting = false;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final ch1 = m.content!.world.chapterById(1);
    final pages = ((ch1['prologue'] as List?) ?? const []).cast<String>();
    final last = _i >= pages.length - 1;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(Gap.l),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l.prologueTitle, style: const TextStyle(color: Palette.gold, letterSpacing: 2)),
              const SizedBox(height: Gap.m),
              Expanded(
                child: SingleChildScrollView(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: StoryText(
                      pages.isEmpty ? '' : pages[_i],
                      key: ValueKey(_i),
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.55, fontSize: 17),
                    ),
                  ),
                ),
              ),
              Text('${_i + 1} / ${pages.isEmpty ? 1 : pages.length}',
                  textAlign: TextAlign.center, style: const TextStyle(color: Palette.parchmentDim)),
              const SizedBox(height: Gap.m),
              FilledButton(
                onPressed: _starting
                    ? null
                    : () async {
                        if (!last) {
                          setState(() => _i++);
                          return;
                        }
                        setState(() => _starting = true);
                        final c = ref.read(appProvider.notifier);
                        await c.markPrologueRead();
                        await c.startJourney();
                      },
                child: Text(last ? l.prologueGo : l.onbNext),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

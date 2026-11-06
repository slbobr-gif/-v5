// Настройки: шаги и разрешения, утренняя мысль, уведомления, о приложении, сброс.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../app/ui_flags.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'intro_screens.dart' show IntroReplayScreen;
import 'onboarding.dart' show PermissionTile, PrologueReplayScreen;
import 'watch_help_screen.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final p = m.profile!;
    final st = m.stepsStatus;
    // Источники шагов: переключатель серый, если источника нет на телефоне
    final sensorUsable = st.sensorAvailable;
    final sensorOn = sensorUsable && st.activityPermission && p.stepsSensor;
    final hcUsable = st.hcStatus == 'available';
    final hcOn = hcUsable && st.hcPermission && p.stepsHc;
    final hcSub = switch (st.hcStatus) {
      'available' => l.stepsHcSub,
      'update_required' => l.stepsHcUpdateHint,
      'not_installed' => l.stepsHcInstallHint,
      _ => l.permHcUnavailable,
    };
    final time =
        '${p.morningHour.toString().padLeft(2, '0')}:${p.morningMinute.toString().padLeft(2, '0')}';
    final bottom = systemBottom(context);
    return Scaffold(
      appBar: AppBar(title: ScreenTitle(kicker: l.appName, title: l.settingsTitle)),
      body: ListView(
        padding: EdgeInsets.fromLTRB(12, Gap.xs, 12, Gap.l + bottom),
        children: [
          SectionHeader(l.settingsSteps, padding: const EdgeInsets.fromLTRB(Gap.xs, Gap.xs, Gap.xs, Gap.s)),
          PermissionTile(
            icon: Icons.directions_walk,
            title: l.permSensorTitle,
            body: st.sensorAvailable ? l.permSensorBody : l.permSensorMissing,
            done: st.sensorAvailable && st.activityPermission,
            action: st.sensorAvailable && !st.activityPermission ? l.permAllow : null,
            onAction: c.requestActivityPermission,
          ),
          const SizedBox(height: Gap.s),
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
          SectionHeader(l.stepsSourcesTitle),
          _Group(children: [
          SwitchListTile(
            value: sensorOn,
            title: Text(l.permSensorTitle),
            subtitle: Text(sensorUsable ? l.stepsSensorSub : l.permSensorMissing),
            onChanged: sensorUsable
                ? (bool v) async {
                    if (v && !st.activityPermission) {
                      final ok = await c.requestActivityPermission();
                      if (!ok) return;
                    }
                    await c.setStepSources(sensor: v, hc: p.stepsHc);
                  }
                : null,
          ),
          SwitchListTile(
            value: hcOn,
            title: Text(l.permHcTitle),
            subtitle: Text(hcSub),
            onChanged: hcUsable
                ? (bool v) async {
                    if (v && !st.hcPermission) {
                      final ok = await c.requestHealthPermission();
                      if (!ok) return;
                    }
                    await c.setStepSources(sensor: p.stepsSensor, hc: v);
                  }
                : null,
          ),
          ListTile(
            leading: const Icon(Icons.watch_outlined, color: Palette.accent),
            title: Text(l.watchHelpOpen),
            trailing: const Icon(Icons.chevron_right),
            onTap: () =>
                Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const WatchHelpScreen())),
          ),
          ]),
          const SizedBox(height: Gap.s),
          Text(l.stepsSourcesNote, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.35)),
          const SizedBox(height: Gap.m),
          _StepsDiagnostics(model: m, today: c.today, onRefresh: () async {
            await c.refreshPermissions();
            await c.refresh();
          }),
          const SizedBox(height: Gap.m),
          Text(l.batteryHint, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.35)),
          SectionHeader(l.settingsNotifications),
          _Group(children: [
          SwitchListTile(
            value: p.notifications,
            title: Text(l.settingsNotifyOn),
            onChanged: (v) async {
              if (v && !m.notifyPermission) await c.requestNotifyPermission();
              await c.updateProfile((pp) => pp.notifications = v);
            },
          ),
          ListTile(
            title: Text(l.settingsMorningTime),
            subtitle: Text(time),
            trailing: const Icon(Icons.schedule),
            onTap: () async {
              final picked = await showTimePicker(
                context: context,
                initialTime: TimeOfDay(hour: p.morningHour, minute: p.morningMinute),
              );
              if (picked != null) {
                await c.updateProfile((pp) {
                  pp.morningHour = picked.hour;
                  pp.morningMinute = picked.minute;
                });
              }
            },
          ),
          ]),
          if (!m.notifyPermission)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(onPressed: c.requestNotifyPermission, child: Text(l.permNotifyAllow)),
            ),
          // Подсказки и помощь (docs/v5/09 §6.5)
          SectionHeader(l.tourHelpTitle),
          _Group(children: [
          ListTile(
            leading: const Icon(Icons.tips_and_updates_outlined, color: Palette.accent),
            title: Text(l.tourReplaySettings),
            onTap: () async {
              final messenger = ScaffoldMessenger.of(context);
              Analytics.instance.event('tour_replay');
              await ref.read(uiFlagsProvider.notifier).replayTips();
              messenger.showSnackBar(SnackBar(content: Text(l.tourReplayDone)));
            },
          ),
          ListTile(
            leading: const Icon(Icons.auto_stories_outlined, color: Palette.accent),
            title: Text(l.introReplaySettings),
            onTap: () {
              if (!_isTop(context)) return;
              Analytics.instance.event('intro_replay');
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const IntroReplayScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.menu_book_outlined, color: Palette.accent),
            title: Text(l.onbPrologueReread),
            onTap: () {
              if (!_isTop(context)) return;
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const PrologueReplayScreen()));
            },
          ),
          ]),
          SectionHeader(l.settingsAbout),
          SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l.aboutText(m.content!.map.attribution),
                    style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.4)),
                const SizedBox(height: Gap.s),
                Text(
                  Analytics.instance.remoteEnabled ? l.analyticsOn : l.analyticsOff,
                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
                ),
                TextButton(
                  onPressed: () =>
                      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const _AnalyticsLog())),
                  child: Text(l.analyticsLog),
                ),
              ],
            ),
          ),
          const SizedBox(height: Gap.l),
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              foregroundColor: Palette.coralLine,
              side: const BorderSide(color: Palette.coralLine),
            ),
            onPressed: () async {
              final ok = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  content: Text(l.resetConfirm),
                  actions: [
                    TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text(l.cancel)),
                    TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(l.resetYes)),
                  ],
                ),
              );
              if (ok == true) {
                // resetJourney сбрасывает и флаги входа: пролог → «Как играть» → рюкзак → первый шаг.
                await c.resetJourney();
                if (context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
              }
            },
            child: Text(l.resetJourney),
          ),
          const SizedBox(height: Gap.l),
          Text(l.version, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
        ],
      ),
    );
  }
}

/// Экран настроек сейчас сверху: второй тап во время перехода не откроет пролог/слайды поверх них же.
bool _isTop(BuildContext context) => ModalRoute.of(context)?.isCurrent ?? true;

/// Диагностика для тестеров: что дал каждый источник сегодня, что пошло в игру, когда синхронизировались
/// и какие приложения пишут шаги в Health Connect.
class _StepsDiagnostics extends StatelessWidget {
  const _StepsDiagnostics({required this.model, required this.today, required this.onRefresh});

  final AppModel model;
  final String today;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final fmt = NumberFormat.decimalPattern('ru');
    final ds = model.lastSteps;
    final p = model.profile!;
    final phone = ds?.sensor[today] ?? 0;
    final hc = ds?.hc[today] ?? 0;
    final game = model.hero?.daySteps[today] ?? 0;
    final at = ds?.readAt;
    final String hcLine = switch (ds?.hcState) {
      'ok' => ds!.hcOrigins.isEmpty ? l.stepsDiagNoOrigins : l.stepsDiagOrigins(ds.hcOrigins.join(', ')),
      'no_permission' => l.stepsDiagHcNoPerm,
      'failed' => l.stepsDiagHcFailed,
      _ => l.stepsDiagHcOff,
    };
    const dim = TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.4);
    return SectionCard(
      padding: const EdgeInsets.all(Gap.s + Gap.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(l.stepsDiagTitle, style: Theme.of(context).textTheme.titleSmall)),
              IconButton(
                tooltip: l.stepsDiagRefresh,
                icon: const Icon(Icons.refresh, color: Palette.accent),
                onPressed: onRefresh,
              ),
            ],
          ),
          Text(l.stepsDiagToday(fmt.format(phone), fmt.format(hc), fmt.format(game)),
              style: const TextStyle(height: 1.4)),
          const SizedBox(height: Gap.xs),
          Text(at == null ? l.stepsDiagNever : l.stepsDiagSync(DateFormat('HH:mm').format(at)), style: dim),
          Text(hcLine, style: dim),
          if (!p.stepsSensor) Text(l.stepsDiagSensorIgnored, style: dim),
          if (!p.stepsHc) Text(l.stepsDiagHcIgnored, style: dim),
        ],
      ),
    );
  }
}

/// Группа строк настроек в одной карточке (как карточки главной).
class _Group extends StatelessWidget {
  const _Group({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    // Material, а не Container: у ListTile/SwitchListTile видна рябь нажатия.
    return Material(
      color: Palette.inkRaised,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Gap.radius),
        side: const BorderSide(color: Palette.inkHigh),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: Gap.xs),
        child: Column(mainAxisSize: MainAxisSize.min, children: children),
      ),
    );
  }
}

class _AnalyticsLog extends StatelessWidget {
  const _AnalyticsLog();

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final log = Analytics.instance.log.reversed.toList();
    final fmt = DateFormat('HH:mm:ss');
    return Scaffold(
      appBar: AppBar(title: Text(l.analyticsLog)),
      body: ListView.builder(
        padding: EdgeInsets.fromLTRB(Gap.m, Gap.m, Gap.m, Gap.m + systemBottom(context)),
        itemCount: log.length,
        itemBuilder: (_, i) => Padding(
          padding: const EdgeInsets.only(bottom: Gap.s),
          child: SectionCard(
            padding: const EdgeInsets.all(Gap.s),
            child: Text('${fmt.format(log[i].at)}  ${log[i].name}\n${log[i].params}',
                style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
          ),
        ),
      ),
    );
  }
}

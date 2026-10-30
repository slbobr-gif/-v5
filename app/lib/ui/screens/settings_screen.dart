// Настройки: шаги и разрешения, утренняя мысль, уведомления, о приложении, сброс.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../analytics/analytics.dart';
import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'onboarding.dart' show PermissionTile;

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final p = m.profile!;
    final st = m.stepsStatus;
    final time =
        '${p.morningHour.toString().padLeft(2, '0')}:${p.morningMinute.toString().padLeft(2, '0')}';
    return Scaffold(
      appBar: AppBar(title: Text(l.settingsTitle)),
      body: ListView(
        padding: const EdgeInsets.all(Gap.m),
        children: [
          Text(l.settingsSteps, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.s),
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
          const SizedBox(height: Gap.s),
          Text(l.batteryHint, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.35)),
          const SizedBox(height: Gap.l),
          Text(l.settingsNotifications, style: Theme.of(context).textTheme.titleMedium),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: p.notifications,
            title: Text(l.settingsNotifyOn),
            onChanged: (v) async {
              if (v && !m.notifyPermission) await c.requestNotifyPermission();
              await c.updateProfile((pp) => pp.notifications = v);
            },
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
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
          if (!m.notifyPermission)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(onPressed: c.requestNotifyPermission, child: Text(l.permNotifyAllow)),
            ),
          const SizedBox(height: Gap.l),
          Text(l.settingsAbout, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.s),
          Text(l.aboutText(m.content!.map.attribution),
              style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.4)),
          const SizedBox(height: Gap.s),
          Text(
            Analytics.instance.remoteEnabled ? l.analyticsOn : l.analyticsOff,
            style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const _AnalyticsLog())),
            child: Text(l.analyticsLog),
          ),
          const SizedBox(height: Gap.l),
          OutlinedButton(
            style: OutlinedButton.styleFrom(foregroundColor: Palette.danger),
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
        padding: const EdgeInsets.all(Gap.m),
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

// Канал к Kotlin-шагомеру: датчик телефона + Health Connect.

import 'package:flutter/services.dart';

class StepsStatus {
  const StepsStatus({
    this.sensorAvailable = false,
    this.activityPermission = false,
    this.hcStatus = 'unavailable',
    this.hcPermission = false,
  });

  final bool sensorAvailable;
  final bool activityPermission;

  /// available | not_installed | update_required | unavailable
  final String hcStatus;
  final bool hcPermission;

  bool get anySource => (sensorAvailable && activityPermission) || hcPermission;

  static StepsStatus fromMap(Map<Object?, Object?> m) => StepsStatus(
        sensorAvailable: m['sensorAvailable'] == true,
        activityPermission: m['activityPermission'] == true,
        hcStatus: (m['hcStatus'] as String?) ?? 'unavailable',
        hcPermission: m['hcPermission'] == true,
      );
}

class DailySteps {
  const DailySteps({required this.days, required this.sensor, required this.hc});

  /// Итог по дню: максимум из источников.
  final Map<String, int> days;
  final Map<String, int> sensor;
  final Map<String, int> hc;

  static Map<String, int> _ints(Object? m) =>
      ((m as Map?) ?? const {}).map((k, v) => MapEntry(k as String, (v as num).toInt()));
}

class StepsPlatform {
  static const _ch = MethodChannel('putnik/steps');

  Future<StepsStatus> status() async {
    try {
      final m = await _ch.invokeMethod<Map<Object?, Object?>>('getStatus');
      return m == null ? const StepsStatus() : StepsStatus.fromMap(m);
    } on MissingPluginException {
      return const StepsStatus();
    } on PlatformException {
      return const StepsStatus();
    }
  }

  Future<bool> requestActivityPermission() => _bool('requestActivityPermission');

  Future<bool> requestHealthPermission() => _bool('requestHealthPermission');

  Future<void> openHealthConnectInstall() => _bool('openHealthConnectInstall');

  Future<void> startBackgroundTracking() => _bool('startBackgroundTracking');

  /// Шаги по локальным дням за последние [days] дней.
  Future<DailySteps> dailySteps({int days = 30}) async {
    try {
      final m = await _ch.invokeMethod<Map<Object?, Object?>>('getDailySteps', {'days': days});
      if (m == null) return const DailySteps(days: {}, sensor: {}, hc: {});
      return DailySteps(
        days: DailySteps._ints(m['days']),
        sensor: DailySteps._ints(m['sensor']),
        hc: DailySteps._ints(m['hc']),
      );
    } on MissingPluginException {
      return const DailySteps(days: {}, sensor: {}, hc: {});
    } on PlatformException {
      return const DailySteps(days: {}, sensor: {}, hc: {});
    }
  }

  Future<bool> _bool(String method) async {
    try {
      return (await _ch.invokeMethod<bool>(method)) ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }
}

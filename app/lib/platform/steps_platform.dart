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

  /// Есть ли хотя бы один источник, который и подключён, и включён в настройках.
  bool anyEnabled({required bool sensor, required bool hc}) =>
      (sensor && sensorAvailable && activityPermission) || (hc && hcPermission);

  static StepsStatus fromMap(Map<Object?, Object?> m) => StepsStatus(
        sensorAvailable: m['sensorAvailable'] == true,
        activityPermission: m['activityPermission'] == true,
        hcStatus: (m['hcStatus'] as String?) ?? 'unavailable',
        hcPermission: m['hcPermission'] == true,
      );
}

class DailySteps {
  const DailySteps({
    required this.days,
    required this.sensor,
    required this.hc,
    this.hcState = 'unavailable',
    this.hcOrigins = const [],
    this.readAt,
  });

  /// Итог по дню: максимум из источников.
  final Map<String, int> days;
  final Map<String, int> sensor;

  /// Health Connect: агрегат StepsRecord.COUNT_TOTAL по местным суткам (пересечения часов и телефона
  /// Health Connect уже убрал), за окно чтения — см. [StepsPlatform.dailySteps].
  final Map<String, int> hc;

  /// ok | no_permission | unavailable | failed — чем кончилось чтение Health Connect.
  final String hcState;

  /// Приложения, записавшие шаги в Health Connect (сегодня, а если сегодня пусто — за окно чтения).
  final List<String> hcOrigins;

  /// Когда прочитано (null — чтения не было).
  final DateTime? readAt;

  static const empty = DailySteps(days: {}, sensor: {}, hc: {});

  static Map<String, int> _ints(Object? m) =>
      ((m as Map?) ?? const {}).map((k, v) => MapEntry(k as String, (v as num).toInt()));

  /// Итог по дням из ВКЛЮЧЁННЫХ источников: для каждого дня — максимум из них.
  /// Если выключены оба — пусто (шаги не засчитываются).
  Map<String, int> merged({required bool useSensor, required bool useHc}) {
    final out = <String, int>{};
    if (useSensor) {
      sensor.forEach((day, v) {
        if (v > (out[day] ?? 0)) out[day] = v;
      });
    }
    if (useHc) {
      hc.forEach((day, v) {
        if (v > (out[day] ?? 0)) out[day] = v;
      });
    }
    return out;
  }
}

class StepsPlatform {
  static const _ch = MethodChannel('putnik/steps');

  /// Health Connect: каждое чтение — сегодня + 7 прошлых суток (часы синхронизируются с опозданием,
  /// дозагруженные шаги за прошедшие дни подхватываются). Раз в несколько часов и при первом
  /// чтении после запуска — полное окно, чтобы не потерять дни, если приложение долго не открывали.
  static const recentDays = 8;
  static const _wideEvery = Duration(hours: 6);
  DateTime? _lastWide;

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

  /// Шаги по локальным дням за последние [days] дней (Health Connect — см. [recentDays]).
  Future<DailySteps> dailySteps({int days = 30}) async {
    final now = DateTime.now();
    final last = _lastWide;
    final wide = last == null || now.difference(last) >= _wideEvery || now.isBefore(last);
    final hcDays = wide || days <= recentDays ? days : recentDays;
    try {
      final m = await _ch.invokeMethod<Map<Object?, Object?>>('getDailySteps', {'days': days, 'hcDays': hcDays});
      if (m == null) return DailySteps.empty;
      final hcState = (m['hcState'] as String?) ?? 'unavailable';
      if (hcState == 'ok' && hcDays >= days && days > recentDays) _lastWide = now;
      return DailySteps(
        days: DailySteps._ints(m['days']),
        sensor: DailySteps._ints(m['sensor']),
        hc: DailySteps._ints(m['hc']),
        hcState: hcState,
        hcOrigins: ((m['hcOrigins'] as List?) ?? const []).map((e) => '$e').toList(),
        readAt: now,
      );
    } on MissingPluginException {
      return DailySteps.empty;
    } on PlatformException {
      return DailySteps.empty;
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

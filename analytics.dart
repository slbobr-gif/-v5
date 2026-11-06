// Аналитика: AppMetrica (если задан ключ при сборке) + локальный журнал для отладки.
// Ключ: --dart-define=APPMETRICA_KEY=... (в GitHub — секрет APPMETRICA_KEY).
// Где взять: appmetrica.yandex.ru → «Добавить приложение» → «Ключ API» (см. docs/HOWTO-APK.md).

import 'package:appmetrica_plugin/appmetrica_plugin.dart';

class LoggedEvent {
  LoggedEvent(this.at, this.name, this.params);
  final DateTime at;
  final String name;
  final Map<String, Object> params;
}

class Analytics {
  Analytics._();
  static final Analytics instance = Analytics._();

  static const _key = String.fromEnvironment('APPMETRICA_KEY');
  bool _active = false;
  final List<LoggedEvent> log = [];

  bool get remoteEnabled => _active;

  /// Ключ AppMetrica — UUID. Кривой ключ (пробел, кавычки) не передаём в SDK: он может уронить запуск.
  static String get _cleanKey => _key.trim().replaceAll('"', '').replaceAll("'", '');
  static final _uuid = RegExp(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$');

  Future<void> init() async {
    final key = _cleanKey;
    if (key.isEmpty || !_uuid.hasMatch(key)) return;
    try {
      await AppMetrica.activate(AppMetricaConfig(key));
      _active = true;
    } catch (_) {
      _active = false;
    }
  }

  /// Почта уходит в AppMetrica только как ID профиля и только при согласии.
  Future<void> setProfile({required String email, required bool consent}) async {
    if (!_active || !consent || email.isEmpty) return;
    try {
      await AppMetrica.setUserProfileID(email);
    } catch (_) {}
  }

  void event(String name, [Map<String, Object> params = const {}]) {
    log.add(LoggedEvent(DateTime.now(), name, params));
    if (log.length > 300) log.removeRange(0, log.length - 300);
    if (!_active) return;
    try {
      if (params.isEmpty) {
        AppMetrica.reportEvent(name);
      } else {
        AppMetrica.reportEventWithMap(name, params);
      }
    } catch (_) {}
  }

  Future<void> flush() async {
    if (!_active) return;
    try {
      await AppMetrica.sendEventsBuffer();
    } catch (_) {}
  }
}

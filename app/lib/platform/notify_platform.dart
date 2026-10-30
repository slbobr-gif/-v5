// Канал к Kotlin-уведомлениям (WorkManager + NotificationManager).

import 'package:flutter/services.dart';

class PlannedNotification {
  const PlannedNotification({required this.id, required this.at, required this.title, required this.body});
  final int id;
  final DateTime at;
  final String title;
  final String body;

  Map<String, Object> toMap() => {
        'id': id,
        'at': at.millisecondsSinceEpoch,
        'title': title,
        'body': body,
      };
}

class NotifyPlatform {
  static const _ch = MethodChannel('putnik/notify');

  Future<bool> requestPermission() async {
    try {
      return (await _ch.invokeMethod<bool>('requestPermission')) ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  Future<bool> hasPermission() async {
    try {
      return (await _ch.invokeMethod<bool>('hasPermission')) ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  /// id уведомления, по которому открыли приложение (один раз), или null.
  Future<int?> consumeOpened() async {
    try {
      return await _ch.invokeMethod<int>('consumeOpened');
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  /// Заменяет все запланированные уведомления этим списком.
  Future<void> replaceAll(List<PlannedNotification> list) async {
    try {
      await _ch.invokeMethod<bool>('replaceAll', {'items': list.map((n) => n.toMap()).toList()});
    } on MissingPluginException {
      return;
    } on PlatformException {
      return;
    }
  }
}

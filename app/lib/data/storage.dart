// Хранение на телефоне: профиль, состояние героя, ответы на утренние мысли.

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../engine/state.dart';
import '../engine/world.dart';

class Profile {
  Profile({
    this.name = '',
    this.email = '',
    this.consent = false,
    this.onboarded = false,
    this.prologueRead = false,
    this.morningHour = 8,
    this.morningMinute = 0,
    this.notifications = true,
    this.surveyAnswered = false,
  });

  String name;
  String email;
  bool consent;
  bool onboarded;
  bool prologueRead;
  int morningHour;
  int morningMinute;
  bool notifications;
  bool surveyAnswered;

  Json toJson() => {
        'name': name,
        'email': email,
        'consent': consent,
        'onboarded': onboarded,
        'prologueRead': prologueRead,
        'morningHour': morningHour,
        'morningMinute': morningMinute,
        'notifications': notifications,
        'surveyAnswered': surveyAnswered,
      };

  static Profile fromJson(Json j) => Profile(
        name: j['name'] as String? ?? '',
        email: j['email'] as String? ?? '',
        consent: j['consent'] == true,
        onboarded: j['onboarded'] == true,
        prologueRead: j['prologueRead'] == true,
        morningHour: toI(j['morningHour'] ?? 8),
        morningMinute: toI(j['morningMinute'] ?? 0),
        notifications: j['notifications'] != false,
        surveyAnswered: j['surveyAnswered'] == true,
      );
}

class Storage {
  Storage(this._p);
  final SharedPreferences _p;

  static const _kProfile = 'profile_v1';
  static const _kHero = 'hero_v1';
  static const _kAnswers = 'answers_v1';
  static const _kThoughtSeen = 'thought_seen_v1';
  static const _kNotifSent = 'notif_sent_v1';
  static const _kNotifPlanned = 'notif_planned_v1';

  Profile loadProfile() {
    final raw = _p.getString(_kProfile);
    if (raw == null) return Profile();
    try {
      return Profile.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>());
    } catch (_) {
      return Profile();
    }
  }

  Future<void> saveProfile(Profile p) => _p.setString(_kProfile, jsonEncode(p.toJson()));

  HeroState? loadHero() {
    final raw = _p.getString(_kHero);
    if (raw == null) return null;
    try {
      return HeroState.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>());
    } catch (_) {
      return null;
    }
  }

  Future<void> saveHero(HeroState s) => _p.setString(_kHero, jsonEncode(s.toJson()));

  /// Ответы игрока Сергею: {день мысли: {text, at}} — только на телефоне.
  Map<String, Json> loadAnswers() {
    final raw = _p.getString(_kAnswers);
    if (raw == null) return {};
    try {
      return (jsonDecode(raw) as Map).map((k, v) => MapEntry(k as String, (v as Map).cast<String, dynamic>()));
    } catch (_) {
      return {};
    }
  }

  Future<void> saveAnswers(Map<String, Json> a) => _p.setString(_kAnswers, jsonEncode(a));

  String? lastThoughtSeenDay() => _p.getString(_kThoughtSeen);
  Future<void> setThoughtSeenDay(String day) => _p.setString(_kThoughtSeen, day);

  /// Сколько событийных уведомлений уже ушло: {день: штук} — для лимита в день между перепланированиями.
  Map<String, int> loadNotifSent() {
    final raw = _p.getString(_kNotifSent);
    if (raw == null) return {};
    try {
      return (jsonDecode(raw) as Map).map((k, v) => MapEntry(k as String, toI(v)));
    } catch (_) {
      return {};
    }
  }

  /// Время (мс) событийных уведомлений из последнего плана.
  List<int> loadNotifPlanned() {
    final raw = _p.getString(_kNotifPlanned);
    if (raw == null) return [];
    try {
      return (jsonDecode(raw) as List).map(toI).toList();
    } catch (_) {
      return [];
    }
  }

  /// Записывает синхронно в кэш (await нужен только для диска), поэтому параллельные вызовы не теряют счёт.
  Future<void> saveNotifState(Map<String, int> sent, List<int> planned) => Future.wait([
        _p.setString(_kNotifSent, jsonEncode(sent)),
        _p.setString(_kNotifPlanned, jsonEncode(planned)),
      ]);

  Future<void> resetJourney() async {
    await _p.remove(_kNotifPlanned);
    await _p.remove(_kHero);
    await _p.remove(_kAnswers);
    await _p.remove(_kThoughtSeen);
  }

  Future<void> resetAll() => _p.clear();
}

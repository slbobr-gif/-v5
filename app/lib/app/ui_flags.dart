// Флаги входа в игру и подсказок (docs/v5/09 §8): вступление, шаг онбординга, черновик рюкзака,
// первый шаг, тур по главной, подсказки по случаю. Хранятся на телефоне отдельным ключом,
// чтобы не менять формат профиля (profile_v1) и состояние героя.

import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class UiFlags {
  UiFlags({
    this.loaded = false,
    this.introDone = false,
    this.onboardingStep = '',
    this.loadoutGear,
    this.loadoutPack,
    this.loadoutAdvisor = false,
    this.prologuePage = 0,
    this.firstStepDone = false,
    this.tourDone = false,
    Map<String, int>? tourStepSeen,
    this.tipsEnabled = true,
    this.mapLayers,
    this.journalReadAt = 0,
  }) : tourStepSeen = tourStepSeen ?? <String, int>{};

  /// false — ещё не прочитаны с диска (экраны ждут).
  bool loaded;
  bool introDone;

  /// profile | perm_activity | perm_notify | perm_hc | sources | loadout | prologue | '' (путь начат)
  String onboardingStep;

  /// Черновик рюкзака (null — игрок ещё ничего не выбирал).
  List<String>? loadoutGear;
  Map<String, int>? loadoutPack;
  bool loadoutAdvisor;
  int prologuePage;
  bool firstStepDone;
  bool tourDone;

  /// id шага тура или подсказки → время показа, мс.
  Map<String, int> tourStepSeen;
  bool tipsEnabled;

  /// Включённые слои карты: markets | spirits | nights | events (null — по умолчанию).
  List<String>? mapLayers;

  /// Журнал прочитан до этой записи (время записи, мс; 0 — ещё не отмечали). Точка на вкладке
  /// «Журнал» и пометки «новое» — для записей позже этого времени; переживает перезапуск.
  int journalReadAt;

  UiFlags copy() => UiFlags(
        loaded: loaded,
        introDone: introDone,
        onboardingStep: onboardingStep,
        loadoutGear: loadoutGear == null ? null : List<String>.of(loadoutGear!),
        loadoutPack: loadoutPack == null ? null : Map<String, int>.of(loadoutPack!),
        loadoutAdvisor: loadoutAdvisor,
        prologuePage: prologuePage,
        firstStepDone: firstStepDone,
        tourDone: tourDone,
        tourStepSeen: Map<String, int>.of(tourStepSeen),
        tipsEnabled: tipsEnabled,
        mapLayers: mapLayers == null ? null : List<String>.of(mapLayers!),
        journalReadAt: journalReadAt,
      );

  Map<String, dynamic> toJson() => <String, dynamic>{
        'introDone': introDone,
        'onboardingStep': onboardingStep,
        'loadoutDraft': loadoutGear == null && loadoutPack == null
            ? null
            : <String, dynamic>{
                'gear': loadoutGear ?? <String>[],
                'pack': loadoutPack ?? <String, int>{},
                'advisor': loadoutAdvisor,
              },
        'prologuePage': prologuePage,
        'firstStepDone': firstStepDone,
        'tourDone': tourDone,
        'tourStepSeen': tourStepSeen,
        'tipsEnabled': tipsEnabled,
        'mapLayers': mapLayers,
        'journalReadAt': journalReadAt,
      };

  static int _int(Object? v) => v is num ? v.toInt() : 0;

  static UiFlags fromJson(Map<String, dynamic> j) {
    final draft = j['loadoutDraft'];
    List<String>? gear;
    Map<String, int>? pack;
    var advisor = false;
    if (draft is Map) {
      final g = draft['gear'];
      if (g is List) gear = g.map((e) => '$e').toList();
      final p = draft['pack'];
      if (p is Map) pack = p.map((k, v) => MapEntry('$k', _int(v)));
      advisor = draft['advisor'] == true;
    }
    final seenRaw = j['tourStepSeen'];
    final seen = <String, int>{};
    if (seenRaw is Map) {
      seenRaw.forEach((k, v) => seen['$k'] = _int(v));
    }
    final layersRaw = j['mapLayers'];
    return UiFlags(
      loaded: true,
      introDone: j['introDone'] == true,
      onboardingStep: (j['onboardingStep'] as String?) ?? '',
      loadoutGear: gear,
      loadoutPack: pack,
      loadoutAdvisor: advisor,
      prologuePage: _int(j['prologuePage']),
      firstStepDone: j['firstStepDone'] == true,
      tourDone: j['tourDone'] == true,
      tourStepSeen: seen,
      tipsEnabled: j['tipsEnabled'] != false,
      mapLayers: layersRaw is List ? layersRaw.map((e) => '$e').toList() : null,
      journalReadAt: _int(j['journalReadAt']),
    );
  }
}

final uiFlagsProvider = NotifierProvider<UiFlagsController, UiFlags>(UiFlagsController.new);

class UiFlagsController extends Notifier<UiFlags> {
  static const _key = 'ui_flags_v1';
  SharedPreferences? _prefs;
  bool _loading = false;

  @override
  UiFlags build() => UiFlags();

  /// Читает флаги один раз. Профиль без флагов (тестеры прошлых сборок, §7.5):
  /// путь начат → вступление и первый шаг пройдены, тур покажем один раз;
  /// имя и согласие есть, героя нет → сразу к разрешениям.
  Future<void> ensureLoaded({required bool onboarded, required bool hasProfile, required bool hasHero}) async {
    if (state.loaded || _loading) return;
    _loading = true;
    try {
      final p = await SharedPreferences.getInstance();
      _prefs = p;
      final raw = p.getString(_key);
      UiFlags f;
      if (raw != null) {
        try {
          f = UiFlags.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>());
        } catch (_) {
          f = UiFlags(loaded: true);
        }
      } else if (onboarded || hasHero) {
        f = UiFlags(loaded: true, introDone: true, firstStepDone: true);
      } else if (hasProfile) {
        f = UiFlags(loaded: true, introDone: true, onboardingStep: 'perm_activity');
      } else {
        f = UiFlags(loaded: true);
      }
      state = f;
      await _save();
    } finally {
      _loading = false;
    }
  }

  Future<void> _save() async {
    final p = _prefs ?? await SharedPreferences.getInstance();
    _prefs = p;
    await p.setString(_key, jsonEncode(state.toJson()));
  }

  Future<void> update(void Function(UiFlags f) change) async {
    final f = state.copy();
    change(f);
    f.loaded = true;
    state = f;
    await _save();
  }

  /// Журнал прочитан до записи со временем [t] (только вперёд).
  Future<void> markJournalRead(int t) async {
    if (t <= state.journalReadAt) return;
    await update((f) => f.journalReadAt = t);
  }

  Future<void> markSeen(String id) => update((f) => f.tourStepSeen[id] = DateTime.now().millisecondsSinceEpoch);

  /// «Показать подсказки снова» (§6.5).
  Future<void> replayTips() => update((f) {
        f.tourDone = false;
        f.tourStepSeen = <String, int>{};
        f.tipsEnabled = true;
      });

  /// Новый путь после сброса (§7.4): сразу рюкзак, пролог, первый шаг; тур не повторяем.
  Future<void> startOverAfterReset() => update((f) {
        f.introDone = true;
        f.onboardingStep = 'loadout';
        f.loadoutGear = null;
        f.loadoutPack = null;
        f.loadoutAdvisor = false;
        f.prologuePage = 0;
        f.firstStepDone = false;
      });
}

// Звуки природы (25.11): фоновая петля на экране — дождь, ручей, ветер, прибой, костёр.
// Звуки сгенерированы с нуля (tools/audio/gen_ambience.py), чужих записей нет.
// Один плеер на всё приложение: экран говорит «мой звук такой», при уходе — «больше не мой».
// Выключается в настройках («Звуки природы»), молчит, когда приложение свёрнуто.

import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';

const ambientSounds = {'rain', 'stream', 'wind', 'waves', 'campfire'};

/// Звук сцены по картинке события: вода — ручей или прибой, дождь — дождь, костёр — костёр, лес и поле — ветер.
String? ambientForArt(String art, {int chapter = 1}) => switch (art) {
      'river' => 'stream',
      'lake' => chapter >= 5 ? 'waves' : 'stream',
      'rain' => 'rain',
      'campfire' || 'night' => 'campfire',
      'forest' || 'field' || 'swamp' || 'road' => 'wind',
      _ => null,
    };

class _Ambient with WidgetsBindingObserver {
  _Ambient() {
    WidgetsBinding.instance.addObserver(this);
  }

  final _player = AudioPlayer();
  String? _playing;
  Object? _owner;
  bool _paused = false;
  bool enabled = true;

  Future<void> want(Object owner, String? sound) async {
    _owner = owner;
    if (!enabled || sound == null || !ambientSounds.contains(sound)) return stopFor(owner, force: true);
    if (_playing == sound && !_paused) return;
    try {
      await _player.setReleaseMode(ReleaseMode.loop);
      await _player.setVolume(0.55);
      await _player.play(AssetSource('audio/$sound.ogg'));
      _playing = sound;
      _paused = false;
    } catch (_) {
      // звук — украшение: без него игра работает
    }
  }

  Future<void> stopFor(Object owner, {bool force = false}) async {
    if (!force && !identical(_owner, owner)) return; // уже чужой экран — не трогаем
    _playing = null;
    try {
      await _player.stop();
    } catch (_) {}
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_playing == null) return;
    if (state == AppLifecycleState.resumed) {
      _paused = false;
      unawaited(_player.resume());
    } else if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      _paused = true;
      unawaited(_player.pause());
    }
  }
}

final _ambient = _Ambient();

/// Обёртка экрана: пока она на экране, звучит [sound] (null — тишина).
class AmbientScope extends ConsumerStatefulWidget {
  const AmbientScope({super.key, required this.sound, required this.child});

  final String? sound;
  final Widget child;

  @override
  ConsumerState<AmbientScope> createState() => _AmbientScopeState();
}

class _AmbientScopeState extends ConsumerState<AmbientScope> {
  final _token = Object();

  void _apply() {
    _ambient.enabled = ref.read(appProvider).profile?.sound ?? true;
    unawaited(_ambient.want(_token, widget.sound));
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _apply());
  }

  @override
  void didUpdateWidget(AmbientScope old) {
    super.didUpdateWidget(old);
    if (old.sound != widget.sound) _apply();
  }

  @override
  void dispose() {
    unawaited(_ambient.stopFor(_token));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // настройка поменялась — сразу включить или выключить
    ref.listen(appProvider.select((m) => m.profile?.sound ?? true), (_, __) => _apply());
    return widget.child;
  }
}

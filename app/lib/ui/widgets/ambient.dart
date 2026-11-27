// Звуки природы (25.11): фоновая петля на экране — дождь, ручей, ветер, прибой, костёр.
// Музыка (27.11): пролог, встречи с духами, финал — отдельный канал поверх звуков природы.
// Всё сгенерировано с нуля (tools/audio/gen_ambience.py, gen_lounge2.py), чужих записей нет.
// По плееру на канал: экран говорит «мой звук такой», при уходе — «больше не мой».
// Во время музыки духов природа звучит тише. Выключается в настройках («Звук»), молчит, когда приложение свёрнуто.

import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';

const ambientSounds = {'rain', 'stream', 'wind', 'waves', 'campfire'};

/// Музыкальные темы и громкость каждой: духи — тише звуков природы, пролог и финал — сами по себе.
const musicTracks = {'prologue': 0.6, 'spirits': 0.38, 'finale': 0.6};

/// Звук сцены по картинке события: вода — ручей или прибой, дождь — дождь, костёр — костёр, лес и поле — ветер.
String? ambientForArt(String art, {int chapter = 1}) => switch (art) {
      'river' => 'stream',
      'lake' => chapter >= 5 ? 'waves' : 'stream',
      'rain' => 'rain',
      'campfire' || 'night' => 'campfire',
      'forest' || 'field' || 'swamp' || 'road' => 'wind',
      _ => null,
    };

class _Channel with WidgetsBindingObserver {
  _Channel(this.volumes, this.prefix) {
    WidgetsBinding.instance.addObserver(this);
  }

  /// Звук → громкость.
  final Map<String, double> volumes;
  /// Префикс файла в assets/audio: '' для природы, 'music_' для музыки.
  final String prefix;
  final _player = AudioPlayer();
  String? _playing;
  Object? _owner;
  bool _paused = false;
  bool enabled = true;
  double _duck = 1.0;
  void Function(String? playing)? onChange;

  Future<void> want(Object owner, String? sound) async {
    _owner = owner;
    if (!enabled || sound == null || !volumes.containsKey(sound)) return stopFor(owner, force: true);
    if (_playing == sound && !_paused) return;
    try {
      await _player.setReleaseMode(ReleaseMode.loop);
      await _player.setVolume(volumes[sound]! * _duck);
      await _player.play(AssetSource('audio/$prefix$sound.ogg'));
      _playing = sound;
      _paused = false;
      onChange?.call(sound);
    } catch (_) {
      // звук — украшение: без него игра работает
    }
  }

  Future<void> stopFor(Object owner, {bool force = false}) async {
    if (!force && !identical(_owner, owner)) return; // уже чужой экран — не трогаем
    final was = _playing;
    _playing = null;
    if (was != null) onChange?.call(null);
    try {
      await _player.stop();
    } catch (_) {}
  }

  /// Приглушить канал (1.0 — обычная громкость).
  Future<void> duck(double k) async {
    if (_duck == k) return;
    _duck = k;
    final s = _playing;
    if (s == null) return;
    try {
      await _player.setVolume(volumes[s]! * k);
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

final _ambient = _Channel({for (final s in ambientSounds) s: 0.55}, '');
final _music = _Channel(musicTracks, 'music_')
  ..onChange = (playing) => unawaited(_ambient.duck(playing == 'spirits' ? 0.6 : 1.0));

/// Обёртка экрана: пока она на экране, звучит [sound] (null — тишина).
class AmbientScope extends ConsumerStatefulWidget {
  const AmbientScope({super.key, required this.sound, required this.child}) : music = false;

  /// Музыкальная тема экрана: prologue | spirits | finale (null — без музыки).
  const AmbientScope.music({super.key, required this.sound, required this.child}) : music = true;

  final String? sound;
  final Widget child;
  final bool music;

  @override
  ConsumerState<AmbientScope> createState() => _AmbientScopeState();
}

class _AmbientScopeState extends ConsumerState<AmbientScope> {
  final _token = Object();

  _Channel get _ch => widget.music ? _music : _ambient;

  void _apply() {
    _ch.enabled = ref.read(appProvider).profile?.sound ?? true;
    unawaited(_ch.want(_token, widget.sound));
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
    unawaited(_ch.stopFor(_token));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // настройка поменялась — сразу включить или выключить
    ref.listen(appProvider.select((m) => m.profile?.sound ?? true), (_, __) => _apply());
    return widget.child;
  }
}

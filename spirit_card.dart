// Картинка события: дух в нужном настроении, иначе общий портрет существа, иначе сцена.

import 'package:flutter/material.dart';

import '../../engine/world.dart';
import 'item_icon.dart';

/// Настроение духа из поля события `mood` (neutral | kind | cunning | angry), по умолчанию neutral.
String eventMood(Json ev) {
  final m = ev['mood'];
  if (m is String && m.isNotEmpty) return m;
  return 'neutral';
}

/// Пути картинки события по порядку: `spirits/<creature>_<mood>` → `spirits/<creature>_neutral` →
/// `creatures/<creature>` → `scenes/<art>`.
List<String> eventArtCandidates(Json ev) {
  final art = (ev['art'] as String?) ?? 'road';
  final creature = ev['creature'] as String?;
  final scene = 'assets/art/scenes/$art.svg';
  if (creature == null || creature.isEmpty) return [scene];
  final mood = eventMood(ev);
  return [
    'assets/art/spirits/${creature}_$mood.svg',
    if (mood != 'neutral') 'assets/art/spirits/${creature}_neutral.svg',
    'assets/art/creatures/$creature.svg',
    scene,
  ];
}

/// Широкая карточка события (витраж 360×200), обрезка по ширине.
class SpiritArt extends StatelessWidget {
  const SpiritArt({super.key, required this.event, this.height});

  final Json event;
  final double? height;

  @override
  Widget build(BuildContext context) {
    return FallbackArt(candidates: eventArtCandidates(event), height: height, width: double.infinity);
  }
}

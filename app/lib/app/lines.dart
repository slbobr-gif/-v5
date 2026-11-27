// Сквозные линии (V5-74, 27.11): родители, Саша, раздумья.
// Движок про линии не знает: сцены — обычные якорные события с полем "line", открытый ответ ставит флаг
// bond_mama_* / bond_papa_* / care_sasha_*. Здесь из флагов считаются скрытые счётчики, а по ним
// выбираются финальные страницы эпилога (chapters.json, последняя глава, lineEpilogue).

import '../engine/state.dart';
import '../engine/world.dart';

int _count(HeroState h, String prefix) => h.flags.where((f) => f.startsWith(prefix)).length;

/// Близость с родителями: открытые ответы маме и папе вместе (из 22).
int parentsScore(HeroState h) => _count(h, 'bond_mama_') + _count(h, 'bond_papa_');

/// Понимание с Сашей: ответы, совпавшие с тем, что ей было нужно (из 16).
int sashaScore(HeroState h) => _count(h, 'care_sasha_');

/// Страница с наибольшим порогом min, который счётчик уже прошёл.
Json? _pick(List? pages, int score) {
  Json? best;
  var bestMin = -1;
  for (final p in pages ?? const []) {
    final page = (p as Map).cast<String, dynamic>();
    final m = toI(page['min']);
    if (m <= score && m > bestMin) {
      best = page;
      bestMin = m;
    }
  }
  return best;
}

/// Эпилог с финалами линий: «Родители» и «Саша» встают после страницы с китом (третьей), до письма сыну.
List<Json> epilogueWithLines(World w, HeroState h) {
  final last = w.chapterById(w.chapters.length);
  final base = [for (final p in (last['epilogue'] as List?) ?? const []) (p as Map).cast<String, dynamic>()];
  final le = (last['lineEpilogue'] as Map?)?.cast<String, dynamic>();
  if (le == null) return base;
  final extra = [
    _pick(le['parents'] as List?, parentsScore(h)),
    _pick(le['sasha'] as List?, sashaScore(h)),
  ].whereType<Json>().toList();
  final at = base.length >= 3 ? 3 : base.length;
  return [...base.sublist(0, at), ...extra, ...base.sublist(at)];
}

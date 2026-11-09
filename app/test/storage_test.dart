// V5-44: «прошёл квесты, закрыл, зашёл — всё откатилось». Причина — два Flutter-движка (две MainActivity)
// писали одно сохранение; устаревший движок затирал свежую запись. Storage.saveHero теперь сверяет номер записи.

import 'package:flutter_test/flutter_test.dart';
import 'package:putnik/data/content_repository.dart';
import 'package:putnik/data/storage.dart';
import 'package:putnik/engine/state.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('устаревшая копия героя не затирает свежее сохранение другого движка', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final w = (await loadGameContent()).world;
    final prefs = await SharedPreferences.getInstance();
    final first = Storage(prefs); // старый движок (в фоне)
    final second = Storage(prefs); // новый движок (открыт сейчас)
    expect(await first.saveHero(HeroState.create(w, 7, 1777622400000, '2026-05-01')), isTrue);

    final stale = first.loadHero(w)!;
    final fresh = second.loadHero(w)!;
    fresh.coins = 999; // игрок прошёл события во втором движке
    expect(await second.saveHero(fresh), isTrue);

    stale.coins = 1; // таймер старого движка пытается сохранить свою копию
    expect(await first.heroChangedElsewhere(), isTrue);
    expect(await first.saveHero(stale), isFalse);
    expect(second.loadHero(w)!.coins, 999);

    final adopted = (await first.loadHeroFresh(w))!;
    expect(adopted.coins, 999);
    expect(await first.saveHero(adopted), isTrue);
    expect(await second.heroChangedElsewhere(), isTrue);
  });

  test('после сброса пути номер записи начинается заново', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final w = (await loadGameContent()).world;
    final st = Storage(await SharedPreferences.getInstance());
    expect(await st.saveHero(HeroState.create(w, 7, 1777622400000, '2026-05-01')), isTrue);
    await st.resetJourney();
    expect(st.loadHero(w), isNull);
    expect(await st.saveHero(HeroState.create(w, 8, 1777622400000, '2026-05-01')), isTrue);
  });
}

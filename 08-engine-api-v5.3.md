# Движок v5.3 — контракт для Dart-порта и интерфейса

Источник правды — Python-эталон `tools/sim/engine.py` (правило в правило). Этот документ — его точное описание для двух
параллельных работ:

* **Dart-порт** (`app/lib/engine/{world,state,engine}.dart`, `app/lib/app/app_controller.dart`, `app/test/engine_parity_test.dart`) — §1–§6, §8–§10, **§13 (дары духов, каталог 59 предметов)**;
* **Интерфейс** (`loadout_screen.dart`, `overflow_screens.dart`, `hero_tab.dart`, `stop_screens.dart`, журнал, главная) — §3 (геттеры), §4 (вызовы), §7 (контроллер), §8–§9 (аналитика, тексты).

Интерфейс вызывает только `AppController` (§7) и читает `HeroState`/`World`/`Engine`-геттеры; движок не знает о l10n — все тексты по кодам из §9.
Связанные документы: `docs/v5/07-change-request-v5.3.md` (заказ, Дополнение A), решения V5-22…V5-31 в `docs/00-decisions.md`.
Проверки: `python3 tools/sim/test_v53.py` (47 тестов, из них 16 — §13), `python3 tools/sim/simulate.py`, `python3 tools/sim/make_parity_fixture.py`, `python3 tools/content/validate.py --strict`.

Обозначения: `Json = Map<String, dynamic>`; `pyRound` — существующая функция из `world.dart` (середина — к чётному); `msHour = 3600000`, `msDay = 86400000`.
«Порядок важен» — в этом месте порядок умножений/итераций влияет на биты double и на тест совпадения.

---

## 1. Что добавилось в `balance.json`

| Ключ | Значение | Кто читает |
|---|---|---|
| `economy.gearSlots` | 4 — ячеек снаряжения | движок |
| `economy.duplicateGearShare` | 0.5 — дубликат снаряжения без зарядов → `floor(price × 0.5)` монет | движок |
| `economy.startItems` | **устарел**, оставлен до порта; новый код не читает | — |
| `economy.markets.<city\|town\|village>.items` | + `gas`, `thermos`, снаряжение (город — всё, посёлок — носки, дождевик, аптечка, фляга; деревня — без снаряжения и газа) | движок |
| `economy.markets.regional` | `{place_id: [item_id…]}` — товары только этого места (сейчас `{}`; наполняет каталог) | движок |
| `economy.markets._regional` | строка-комментарий: **пропускать ключи на `_` и `regional` при обходе типов рынков** | — |
| `loadout` | `{maxGear: 3, maxPackSlots: 5, maxPerKind: 3, default: {gear: [socks, raincoat, gas_stove], pack: {bread: 2, water: 2, tea: 1}}}` | движок, экран старта |
| `gameDay.utcOffsetHours` | 3 — игровая дата по МСК (весь маршрут в МСК) | движок |
| `riskReduce` | `{weightScale: 100, badLevel: "large"}` — правило оберега §5.10 | движок |
| `randomEvents` | `spacingKm [5.5, 10.5]`, `firstAfterKm 3`, `minGapToAnchoredKm 3`, **`recentKeep 36`** | движок |
| `items.<id>` | новые поля §1.1 | движок, экран перков |
| `zones` | без изменений (радиусы `byKind`, подписи `labels` — подписи брать из l10n, §9) | движок, валидатор |

### 1.1. Поля предмета (`balance.json → items.<id>`)

| Поле | Тип | Смысл |
|---|---|---|
| `type` | `food`/`drink` (рюкзак), `gear` (снаряжение), `tool` (инструмент без ячейки: спички, клубок), **`refill`** (баллон) | |
| `satiety`, `water`, `warmth` | int | прибавка **за одну порцию** |
| `heat` | int | бонус тепла, если съедено/выпито горячим (water 25, tea 15, stew 20, pie 10, thermos 10) |
| `portions` | int ≥ 1 | порций в одной ячейке (`thermos` 4); нет поля = 1 |
| `price` | int | базовая цена (рынок умножает на `priceMult`) |
| `starter` | bool | можно взять на старте |
| `warmthDrainMult` | 0..1 | любой расход тепла (в пути и в покое) × |
| `weatherWarmthMult` | 0..1 | добавка холода от непогоды × (только если погодный множитель тепла > 1) |
| `drainKmMult` | `{satiety?, water?}` 0..1 | расход на км × |
| `waterDrainMult` | 0..1 | расход воды на км × |
| `idleWarmthMult` | 0..1 | тепло в покое (по часам) × |
| `delayMult`, `detourMult` | 0..1 | задержки (часы) и крюки (км) × |
| `riskReduce` | 0..1 | §5.10 |
| `rescueTo` | int | аптечка §5.9 |
| `stove` | true | горелка: даёт действие «Нагреть» |
| `uses` | int | зарядов у нового экземпляра; нет поля — бесконечный |
| `maxUses` | int | потолок зарядов (горелка 30); нет поля = `uses` |
| `refill`, `amount` | id, int | у `refill`-предмета: кому и сколько зарядов |
| `ability` | `{kind, cooldownDays}` | дар духа §5.14 (`ball_yaga`: `{kind: "clew", cooldownDays: 3}`) |
| `region` | string | край предмета, справочно (продажа — через `markets.regional`) |

Каталог сейчас: еда `bread, stew, water, tea, thermos, chocolate, berries, fish, pie, kvass`; `matches` (tool); `gas` (refill); снаряжение-старт `socks, raincoat, trekking_poles, gas_stove, sleeping_bag, first_aid, flask, compass`; квестовые `amulet_leshy` (gear), `ball_yaga` (tool + ability). Движок читает поля generic'ом: новый предмет с теми же полями работает без кода.

---

## 2. Состояние героя (`HeroState`, JSON сохранения)

Версия `"v": 2`. Новые поля **жирным**. Имена ключей JSON = имена полей Dart.

| JSON | Dart | Тип | Смысл |
|---|---|---|---|
| `v` | — | int | 2 |
| `seed`, `rng`, `startedAt`, `startDay`, `pos`, `maxPos`, `buffer`, `detour`, `stats`, `coins`, `stop`, `delayUntil`, `flags`, `seen`, `recentRandom`, `quests`, `nextRandomAt`, `bonusKm`, `lastTick`, `counted`, `daySteps`, `claimed`, `deaths`, `journal`, `finished` | как было | | без изменений смысла; `recentRandom` теперь хранит до `randomEvents.recentKeep` id |
| `inv` | `inv` | `Map<String,int>` | рюкзак (food/drink — **число единиц = ячеек**) + инструменты (tool). **Снаряжения здесь больше нет** |
| **`gear`** | `gear` | `List<String>` | снаряжение по порядку получения, каждый id не больше одного раза, длина ≤ `gearSlots` |
| **`gearUses`** | `gearUses` | `Map<String,int>` | остаток зарядов только у предметов с `uses` (`gas_stove`, `first_aid`) |
| **`heated`** | `heated` | bool | горелка «включена»: следующий нагреваемый употреблённый предмет получает `heat` |
| **`heatedDay`** | `heatedDay` | int | игровая дата включения (§5.6), 0 — выключена |
| **`overflow`** | `overflow` | `List<OverflowItem>` | очередь решений, §5.8 |
| **`aidLock`** | `aidLock` | bool | аптечка уже срабатывала после последней остановки |
| **`loadoutDone`** | `loadoutDone` | bool | старт-набор выбран (`startLoadout` больше нельзя) |
| **`portionsLeft`** | `portionsLeft` | `Map<String,int>` | порций в **начатой** единице многопорционного предмета; нет ключа — начатой нет (= `portions`) |
| **`abilityReady`** | `abilityReady` | `Map<String,int>` | id предмета → игровая дата, с которой способность снова готова; нет ключа — готова |

```dart
class OverflowItem {
  OverflowItem({required this.kind, required this.item, required this.n, required this.source});
  String kind;   // 'backpack' | 'gear'
  String item;   // id предмета
  int n;         // сколько единиц ждут решения (у gear всегда 1)
  String source; // id события-источника (или 'market', 'fixture_dayN')
  Json toJson() => {'kind': kind, 'item': item, 'n': n, 'source': source};
  static OverflowItem fromJson(Json j) =>
      OverflowItem(kind: j['kind'] as String, item: j['item'] as String, n: toI(j['n']), source: (j['source'] as String?) ?? '');
}
```

**`HeroState.create(World w, int seed, int nowMs, String today, {int todaySteps = 0})`**: как раньше, но `inv/gear/gearUses` — из `balance.loadout.default` (= Python `_loadout_into`: `gear = List.of(default.gear)`, `gearUses = {g: uses}` для gear с `uses`, `inv = {k: n}` для n > 0), `heated=false, heatedDay=0, overflow=[], aidLock=false, loadoutDone=false, portionsLeft={}, abilityReady={}`; `stats` — double.

**Миграция v1 → v2 в `fromJson`** (`migrate_state` в эталоне), если `j['v'] < 2` или нет `gear`:
для каждого ключа `inv` по порядку, если `itemType == 'gear'`: вынуть из `inv`; если в `gear` есть место — добавить (и `gearUses = uses`, если есть) и уменьшить n на 1; остаток n → `coins += n × floor(price × duplicateGearShare)`. Затем `v=2, heated=false, heatedDay=0, overflow=[], aidLock=false, loadoutDone=true, portionsLeft={}, abilityReady={}`. Еда и инструменты остаются в `inv`.

`toJson` пишет все поля таблицы; `fromJson` читает с умолчаниями (`?? []`, `?? {}`, `== true`).

---

## 3. `World` (Dart, `world.dart`)

```dart
class ZonePoint { const ZonePoint(this.pos, this.urban, this.outer); final double pos, urban, outer; } // метры
class ItemPerk  { const ItemPerk(this.key, this.value); final String key; final int value; }

// поля/методы World:
late final List<ZonePoint> zonePoints;          // строится ПОСЛЕ _addRoadside, по this.places по порядку
String zoneAt(double posM);                     // 'city' | 'suburb' | 'wild'
int zonePoolSize(String zone);                  // сколько событий events_random с этой zone (все главы)
String? eventZone(String eventId);              // eventsById[id]?['zone']
List<String> get starterGear;                   // id с starter && type gear — в порядке ключей balance.items
List<String> get starterPack;                   // id с starter && type food|drink — в том же порядке
bool heatable(String id);                       // itemValue(id,'heat') > 0
int portionsOf(String id);                      // max(1, items[id].portions ?? 1)
String? loadoutError(List<String> gear, Map<String,int> pack); // §5.3, без состояния — для экрана старта
List<ItemPerk> itemPerks(String id);            // §6
String itemType(String id);                     // + 'refill'; неизвестный id → 'tool' (как было)
```

`zonePoints`: для каждого места `p` из `places` (включая придорожные `rs_*` с kind `roadside`): `r = zones.byKind[p.kind]`; нет записи — пропустить; иначе `ZonePoint(posOf[p.id], toD(r.urban) * 1000.0, (toD(r.urban) + toD(r.suburb)) * 1000.0)`.

---

## 4. `Engine` (Dart, `engine.dart`) — методы

Класс остаётся `Engine(World w, HeroState s)`. Python → Dart:

| Python (`engine.py`) | Dart | Возврат |
|---|---|---|
| `start_loadout(gear, pack, now)` | `String? startLoadout(List<String> gear, Map<String, int> pack, int now)` | null — ок; иначе код §5.3 |
| `heat_status(now)` | `String heatStatus(int now)` | `ready \| on \| no_stove \| no_gas \| nothing` |
| `heat(now)` | `String heat(int now)` | `heated` (потрачен заряд) `\| on` (уже горячо, заряд не тратится) `\| no_stove \| no_gas \| nothing` |
| `is_heated(now)` | `bool isHeated(int now)` | для пометки «горячо» |
| `game_day(now)` | `int gameDay(int now)` | §5.6 |
| `use_item(item, now)` | `bool useItem(String item, int now)` | одна порция; false — нет/не еда |
| `give_items(items, source)` | `void giveItems(Map<String, int> items, String source)` | §5.7 (эффект `give` вызывает его же) |
| `resolve_overflow_gear(keep)` | `String? resolveGearOverflow(List<String> keep)` | null \| `no_gear_overflow \| bad_keep` |
| `resolve_overflow_backpack(action, swap, now)` | `String? resolveBackpackOverflow(String action, int now, {String? swapAction, String? swapItem})` | null \| `no_backpack_overflow \| need_swap \| bad_swap \| swap_not_free \| bad_action` |
| `continue_journey(now)` | `bool continueJourney(int now)` | **теперь bool**: false — отказ (overflow, событие, финиш, нет остановки) |
| `buy_blocker(item)` | `String? buyBlocker(String item)` | + `gear_full \| no_stove \| gas_full` |
| `buy(item, now)` | `bool buy(String item, int now)` | §5.13 |
| `market()` | `List<MarketOffer> market()` | + региональные §5.13 |
| `choose(id, now)` | `ChoiceResult choose(String choiceId, int now)` | веса через `outcomeWeights` |
| `outcome_weights(choice)` | `List<int> outcomeWeights(Json choice)` | §5.10 |
| `choice_available(choice)` | `bool choiceAvailable(Json choice)` | `requires.item` смотрит `hasItem` |
| `has_item(item)` | `bool hasItem(String item)` | `inv[item] > 0 \|\| gear.contains(item)` |
| `gear_mult(key, sub)` | `double gearMult(String key, [String? sub])` | §5.4 |
| `risk_factor()` | `double riskFactor()` | §5.10 |
| `gear_uses(item)` | `int usesLeft(String item)` | `s.gearUses[item] ?? 0` |
| `_max_uses(item)` | `int maxUses(String item)` | `maxUses ?? uses ?? 0` |
| `gear_slots()` / `backpack_slots()` | `int gearSlots()` / `int backpackSlots()` | |
| `portions_open(item)` | `int portionsOpen(String item)` | `s.portionsLeft[item] ?? portionsOf(item)` |
| `portions_total(item)` | `int portionsTotal(String item)` | `n == 0 ? 0 : (n−1)·portions + portionsOpen` — «Термос воды ×4» |
| `zone_here()` | `String zoneHere()` | `w.zoneAt(s.pos)` |
| `ability_item(kind)` | `String? abilityItem(String kind)` | §5.14 |
| `ability_cooldown_days(item, now)` | `int abilityCooldownDays(String item, int now)` | 0 — готово |
| `clew_status(now)` | `String clewStatus(int now)` | `ready \| cooldown \| no_item \| no_event` |
| `ask_clew(now)` | `Map<String, String>? askClew(int now)` | `{choiceId: tone}` или null |
| `choice_tone(choice)` / `outcome_tone(o)` | `String choiceTone(Json choice)` / `String outcomeTone(Json o)` | §5.14 |
| — | `bool get hasOverflow => s.overflow.isNotEmpty;` | |
| `advance(now)` | `List<EngineEvent> advance(int now)` | стоит, пока есть overflow |

Удобные геттеры для UI (Dart-only, без логики): `int get gearSlotsLeft => gearSlots() - s.gear.length;`, `bool get clewReadyNow => clewStatus(DateTime.now().millisecondsSinceEpoch) == 'ready';` (в UI лучше передавать `now` из контроллера).

---

## 5. Правила (точно как в эталоне)

### 5.1. Зоны
`zoneAt(pos)`: `best='wild'`; для каждой `ZonePoint z`: `d = (pos - z.pos).abs()`; `zz = (z.urban > 0 && d <= z.urban) ? 'city' : (z.outer > 0 && d <= z.outer) ? 'suburb' : 'wild'`; если ранг `zz` (city 2, suburb 1, wild 0) больше — `best = zz`. **Радиус 0 — зоны нет** (у деревни нет «города» даже в её точке). Валидатор (`tools/content/zones.py`) считает так же, в метрах; тест `test_validator_zones_match_engine_on_real_route` сверяет.

### 5.2. Случайные события (`_pickRandom(int now)`, теперь с `now`)
```
ch = 'ch${chapterAt(pos)}'; zone = zoneAt(pos)
keepZ  = max(1, min(12, zonePoolSize(zone) ~/ 2))
recentZ   = [последние keepZ id из s.recentRandom, у которых eventZone(id) == zone]   // порядок списка
recentAll = s.recentRandom.sublist(max(0, len − max(1, min(12, randoms.length ~/ 2))))
inCh = randoms.where(tags содержит ch или 'any')             // порядок файла
pool = inCh.where(e.zone == zone && !recentZ.contains(e.id))
base = inCh.where(!recentAll.contains(e.id))
if pool.isEmpty: pool = base; if base.isNotEmpty: _log(now, 'zone_fallback', {'zone': zone})
if pool.isEmpty: return null
(дальше без изменений: «приметность» → risky; e = pool[rng.nextU32() % pool.length])
s.recentRandom.add(e.id); оставить последние randomEvents.recentKeep (36)
```
Частота: `spacingKm [5.5, 10.5]`, `firstAfterKm 3`. Симулятор: 1,5–1,8 случайного события на 8 000 шагов (было 1,3).

### 5.3. Старт-набор
`loadoutError(gear, pack)` — по порядку: `gear.length > maxGear` → `gear_too_many`; повтор → `gear_duplicate`; не из `starterGear` → `gear_not_starter`; ключ `pack` не из `starterPack` → `pack_not_starter`; n < 1 → `pack_bad_count`; n > `maxPerKind` → `pack_kind_limit`; сумма > `maxPackSlots` → `pack_too_many`.
`startLoadout`: `loadoutDone` → `already_done`; `maxPos > 0` → `already_walking`; затем `loadoutError`; при успехе: `gear = List.of(gear)`, `gearUses = {g: uses}`, `inv = {k: n}` (**инструменты и прежний рюкзак заменяются**), `heated=false, heatedDay=0, overflow=[], aidLock=false, portionsLeft={}`, `loadoutDone=true`, `_log(now, 'loadout', {'gear': gear, 'pack': pack})`, `_saveRng()`. Монеты не тратятся (старт бесплатный, 40 монет — как было). Термос (4 порции) — 1 ячейка старта.

### 5.4. Расход и перки (порядок важен)
`gearMult(key, [sub])`: `m = 1.0`; для `g` в `s.gear` **по порядку**: `v = items[g]?[key]`; если `v is Map` → `v = v[sub]`; если `v is num` (не bool) → `m = m * v`. Без снаряжения ровно 1.0.

`_drainWalk(km)`:
```
satM  = gearMult('drainKmMult', 'satiety')
watM  = gearMult('drainKmMult', 'water') * gearMult('waterDrainMult')
warmM = gearMult('warmthDrainMult')
rainM = gearMult('weatherWarmthMult')
weatherWarm = wx['warmth'] ?? 1.0
if (weatherWarm > 1.0 && rainM != 1.0) weatherWarm = 1.0 + (weatherWarm - 1.0) * rainM
satiety -= dk.satiety * km * mult * satM
water   -= dk.water * km * wxWater * mult * watM
warmth  -= dk.warmth * km * cold * weatherWarm * warmM * mult
```
`applyTime(now)`: `hours = max(0, (now − lastTick)/msHour)`; `lastTick = now`; **`_expireHeat(now)`**; если `hours <= 0` — выход; для каждого показателя `rate = drainPerHour[k]`; для `warmth`: `rate = rate * gearMult('warmthDrainMult') * gearMult('idleWarmthMult')`; `nxt = cur - rate * hours`; `stats[k] = max(nxt, min(cur, idleFloor))`; затем `_autoConsume`.

### 5.5. Употребление, порции, автоеда
* `_itemGain(item, stat)`: `g = itemValue(item, stat)`; если `stat == 'warmth' && s.heated`: `g = g + itemValue(item, 'heat')`. Автоеда выбирает как раньше по `_itemGain` (горячая вода может быть выбрана «для тепла»).
* `_useOne(item, now)` (одна порция из рюкзака): если `portionsOf(item) > 1`: `left = portionsOpen(item) − 1`; `left <= 0` → `_takeInv(item, 1)` и `portionsLeft.remove(item)`; иначе `portionsLeft[item] = left`. Иначе `_takeInv(item, 1)`. Затем `_consume(item, now)`.
* `_takeInv(item, n)`: `left = inv[item] − n`; > 0 — записать, иначе `inv.remove(item)` **и** `portionsLeft.remove(item)`.
* `_consume(item, now)` (предмет уже вынут): `_expireHeat(now)`; `stats[k] += items[item][k] ?? 0` для satiety, water, warmth; если `s.heated && heat > 0`: `warmth += heat`, `heated=false`, `heatedDay=0`; `_clampStats()`. Возвращает «было горячим».
* Автоеда: `_useOne(pick)` и `_log(now, 'eat', {'item': pick})` (как раньше). `useItem` — `_useOne` без записи в журнал, `_saveRng()`.
* Порции: все числа предмета — на порцию; бонус `heat` — на порцию (нагрели → одна порция горячая); переполнение и покупка — предмет целиком (новая единица полная); смерть делит единицы как раньше, при 0 единиц `portionsLeft` удаляется; эффект `remove` удаляет единицы.

### 5.6. «Нагреть»
* `gameDay(now) = (now + (utcOffsetHours * msHour).toInt()) ~/ msDay`.
* `_expireHeat(now)`: если `heated && gameDay(now) != heatedDay` → `heated=false, heatedDay=0`. Вызывается в `applyTime`, `_consume`, `heat`. `isHeated(now) = heated && gameDay(now) == heatedDay`.
* `heatStatus(now)`: нет предмета с `stove` в `gear` → `no_stove`; `isHeated` → `on`; заряды горелки ≤ 0 → `no_gas`; нет нагреваемого ни в `inv` (n > 0), ни в `overflow` вида backpack → `nothing`; иначе `ready`. Горелка — первая в `gear` с `stove: true`.
* `heat(now)`: `_expireHeat`; статус ≠ `ready` → вернуть статус (для `on` заряд не тратится); иначе `gearUses[stove] −= 1`, `heated=true`, `heatedDay=gameDay(now)`, `_log(now, 'heat', {'item': stove, 'left': n})`, `_saveRng()`, вернуть `heated`.
* Сброс: употребление любого предмета с `heat > 0` (руками, автоедой, «Использовать сразу», «использовать» при обмене); смена игровой даты; смерть. Флаг не привязан к конкретным бутылкам: купленная при включённой горелке вода тоже «горячая». Пустая горелка остаётся в снаряжении.

### 5.7. Получение предметов (`giveItems`; эффект `give` → `giveItems(eff.give, source: ev.id)`)
Для каждой пары `(it, n)` **в порядке ключей**:
* food/drink: `room = max(0, backpackSlots − consumablesCount)`; `put = min(n, room)`; `inv[it] += put`; остаток `n − put > 0` → `overflow.add(OverflowItem('backpack', it, n − put, source))`;
* gear: n раз `_gainGear(it, source)`;
* refill: n раз `_gainRefill(it)`;
* иначе (tool): `inv[it] += n`.

`_gainGear(it, source)`: если `it` уже в `gear` или есть запись overflow gear с этим `it` → дубликат: если `it` в `gear`, у него есть `uses` и `usesLeft < maxUses` → `gearUses[it] = min(maxUses, usesLeft + uses)`; иначе `coins += floor(price × duplicateGearShare)`; конец. Иначе, если `gear.length < gearSlots` → `gear.add(it)` (+ `gearUses[it] = uses`, если есть). Иначе → `overflow.add(OverflowItem('gear', it, 1, source))`.
`_gainRefill(it)`: `tgt = items[it].refill`; если `tgt` в `gear` и `usesLeft(tgt) < maxUses(tgt)` → `gearUses[tgt] = min(maxUses, uses + amount)`; иначе `coins += price` (запасной баллон монетами).
Эффект `remove` (`_removeItems`): если id в `gear` → убрать из `gear` и `gearUses` (n не важен); иначе как раньше по `inv` (+ `portionsLeft.remove`, если единиц не осталось). Порядок `_applyEffects`: coins → stats → clamp → **remove → give** → flag → quest_start (только если квест есть в мире) → quest_var → bonus_reset → delay → detour → shortcut → смерть (§5.9).

### 5.8. Переполнение
* Пока `overflow` непуст: `advance` не двигает героя (условие цикла `… && s.overflow.isEmpty && …`), `continueJourney` → false. Решается **всегда первая запись**.
* `resolveGearOverflow(keep)`: первая запись не gear → `no_gear_overflow`; `cands = [...gear, new]`; `need = min(gearSlots, cands.length)`; `keep.length != need`, повторы, или id не из `cands` → `bad_keep`. Иначе: для выброшенных старых — `gearUses.remove`; `gear = cands.where(keep.contains)` (порядок `cands`); новая оставлена и с `uses` → `gearUses[new] = uses`; запись удаляется. «Оставить как есть» = `keep = текущий gear`.
* `resolveBackpackOverflow(action, now, {swapAction, swapItem})` — одна единица первой записи:
  `use` → `_consume(item, now)` (горячий бонус работает); `drop` → ничего; `stash` → если рюкзак полон: нет swap → `need_swap`; `swapAction` не use/drop, `swapItem` нет в `inv` или не еда → `bad_swap`; `swapAction == 'use'` у многопорционного с `portionsOpen > 1` → `swap_not_free` (порция ячейку не освобождает); иначе `use` → `_useOne(swapItem)`, `drop` → `_takeInv(swapItem, 1)`; затем `inv[item] += 1`. Иначе `bad_action`. После успеха `n −= 1`, при 0 запись удаляется; `_saveRng()`.
* Покупка в полное вместилище не создаёт overflow — `buyBlocker` = `backpack_full` / `gear_full`.
* Смерть очищает `overflow`.

### 5.9. Аптечка (`rescueTo`, `uses`)
В `_walk` после `_clampStats`: если `minStat <= 0`: `if (_tryRescue(now)) continue;` иначе смерть. В `_applyEffects`: явная `death: true` → смерть всегда; иначе если `minStat <= 0` → `_tryRescue` ? жив : смерть.
`_tryRescue`: если `aidLock` → false. Первый `g` в `gear` с `rescueTo` и `usesLeft(g) > 0`: `gearUses[g] −= 1`; все показатели `<= 0` = `rescueTo` (double); `aidLock = true`; `_log(now, 'first_aid', {'item': g, 'stats': [..], 'left': n})`; true.
`aidLock = false`: в начале **любого** `_arrive` (место, событие, квест, случайное, финиш), при остановке в конце ответвления (`detour_end`), при смерти, при `startLoadout`. Итого: «одна аптечка между двумя остановками».

### 5.10. Оберег (`riskReduce`)
`riskFactor()`: `f = 1.0`; для `g` в `gear`: `r = items[g].riskReduce`; если `r` не 0 → `f = f * (1.0 − r)`.
`outcomeWeights(choice)`: `ws = weights`; если `f == 1.0` или `choice.risk` (по умолчанию `none`) == `none` → `ws`. «Плохой» исход: `effects.death == true` или любое из `satiety/water/warmth/coins` == `'-' + riskReduce.badLevel` (`-large`). Если плохих нет или все плохие → `ws`. Иначе плохой: `max(1, pyRound(w * weightScale * f).toInt())`, хороший: `w * weightScale` (`w * weightScale` — int, потом `* f`). Пример 1/4 смерти → 80/380 = 21 %; 1/6 → 13,8 %; 1/8 → 10,3 %. `choiceRisk` (знак опасности) не меняется.

### 5.11. Компас (`delayMult`, `detourMult`)
`delay`: `h = delayHours[lvl]`; `m = gearMult('delayMult')`; если `m != 1.0` → `h = max(1, pyRound(h * m))`; `delayUntil = now + (h * msHour).toInt()`. `detour`: `km = detourKm[lvl]`, так же с `detourMult`, `dm = km * 1000.0`. При 0,75: задержки 2→2 (1,5 → к чётному), 6→4, 12→9 ч; крюки 3→2, 6→4, 10→8 км.

### 5.12. Смерть
Как раньше + `heated=false, heatedDay=0, overflow=[], aidLock=false` (после `bonusKm = 0`). Снаряжение, заряды, инструменты, `abilityReady` сохраняются; еда — `floor(n × keepConsumablesShare)` единиц.

### 5.13. Рынок
`market()`: тип рынка места `p.market` (значение `regional` как тип не используется); список = `markets[type].items` + `markets.regional[p.id]` (без повторов, в конец), цена `int(round(price × priceMult))` (существующий `pyRound`).
`buyBlocker`: `not_sold` → `no_coins` → food/drink и рюкзак полон `backpack_full` → gear: уже есть `have_gear`, снаряжение полно `gear_full` → refill: нет горелки `no_stove`, заряды ≥ max `gas_full`.
`buy`: монеты −цена; gear → `_gainGear(item, 'market')`; refill → `_gainRefill(item)`; иначе `inv += 1`; `_log('buy')` всегда.

### 5.14. Дары духов (`ability`) и клубок
* `abilityItem(kind)`: первый предмет с `ability.kind == kind` среди `gear` (по порядку), затем ключей `inv` с n > 0 **в алфавитном порядке**.
* `abilityCooldownDays(item, now) = max(0, (abilityReady[item] ?? 0) − gameDay(now))`.
* `clewStatus(now)`: нет предмета `clew` → `no_item`; кулдаун > 0 → `cooldown`; нет `currentEvent()` → `no_event`; иначе `ready`.
* `askClew(now)`: не `ready` → null. Иначе `{choice.id: choiceTone(choice)}` для **всех** вариантов события (и недоступных), `abilityReady[item] = gameDay(now) + cooldownDays`, `_log(now, 'ability', {'item': item, 'event': ev.id})`, `_saveRng()`. RNG не тратится, исход не предрешается.
* `outcomeTone(o)`: `death: true` → `death`; «плюс»: `coins/satiety/water/warmth` без `-`, `give`, `shortcut`; «минус»: со `-`, `remove`, `delay`, `detour`, `bonus_reset`; оба → `mixed`, только плюс → `good`, только минус → `bad`, ничего → `neutral`.
* `choiceTone(choice)` по множеству тонов исходов: есть `death` → `death`; есть `good` и `bad` → `risk`; есть `mixed` → `mixed`; есть `good` → `reward`; есть `bad` → `penalty`; иначе `neutral`.
* Новые дары других духов = новый `ability.kind` + метод в движке по образцу клубка; поле `abilityReady` общее.

### 5.15. Журнал — новые виды
`loadout {gear, pack}`, `heat {item, left}`, `first_aid {item, stats, left}`, `ability {item, event}`, `zone_fallback {zone}` (служебный — журнал его **не показывает**). Число записей входит в тест совпадения: писать ровно там, где указано.

### 5.16. Отношения с духами (п. 24) — в движке ничего нового не нужно
Счёт отношения — переменная квеста: эффект `quest_var: {"favor": 1}` / `{"favor": -2}`. Финал — шаг с `branches`: **первая** ветка, у которой выполняются **все** условия `if` (`>=N, <=N, ==N, >N, <N`), выигрывает; последняя — запасная `{}`. Три исхода «по расположению»: `[{if: {favor: ">=3"}, event: добрая}, {if: {favor: ">=0"}, event: хитрая}, {if: {}, event: злая}]`. Дары — обычные `give` в исходах финала (предмет с перком/`ability`/`uses`/`portions`). Тонкость: `quest_var` у **квестового** события меняет только свой квест; у **обычного** события — **все активные** квесты (так сделано намеренно, чтобы встреча «вне квеста» влияла на отношение; если нужна точность — ставьте `quest_var` только в шагах квеста). Повторный `quest_start` активного квеста игнорируется. Поле события `mood: neutral|kind|cunning|angry` (необязательное, проверяет валидатор) движок не читает — по нему интерфейс выбирает `art/spirits/<creature>_<mood>.svg`.

---

## 6. Перки для экрана («Собери рюкзак», «Герой», рынок, переполнение)

`World.itemPerks(id)` → `List<ItemPerk>` в фиксированном порядке:
`satiety, water, warmth` (только у еды/питья, value = число за порцию) → `heat` → `warmthDrain` → `weatherCold` → `satietyDrain` → `waterDrain` (из `drainKmMult.water`) → `waterDrain` (из `waterDrainMult`) → `idleWarmth` → `delay` → `detour` → `risk` → `rescue` → `stove` (value 0) → `refill`, `refillMax` → `uses` → `portions` → `ability_<kind>` (value = cooldownDays; клубок: `ability_clew 3`).
Проценты: `pct(mult) = pyRound((1 − mult) * 100)`; `risk` = `pyRound(riskReduce * 100)`. Примеры: носки `[warmthDrain 15]`; дождевик `[weatherCold 50]`; палки `[satietyDrain 8, waterDrain 8]`; горелка `[stove 0, uses 10]`; мешок `[idleWarmth 50]`; аптечка `[rescue 25, uses 2]`; фляга `[waterDrain 10]`; компас `[delay 25, detour 25]`; вода `[water 40, heat 25]`; термос `[water 20, heat 10, portions 4]`; газ `[refill 10, refillMax 30]`.
Python добавляет `portions` последним, только если `portions > 1` — **сделать так же**. Полный эталон для всех предметов — `parity.json → itemPerks`.
Текст перка — l10n-ключ `gearPerk<Key>` (§9) с подстановкой `{value}`. Перки снаряжения действуют, пока предмет в `gear`; у пустой горелки/аптечки показывать «Пусто» (`usesLeft == 0`).

---

## 7. `AppController` — что вызывает интерфейс

Контроллер (правит Dart-портировщик) сохраняет состояние после каждого вызова (`_commit()`), шлёт аналитику §8. Интерфейс не вызывает `Engine` напрямую.

```dart
// Старт (экран «Собери рюкзак» стоит до пролога, героя ещё нет)
String? chooseLoadout(List<String> gear, Map<String, int> pack, {bool isDefault = false}); // world.loadoutError; ок → запомнить (в памяти + Storage, переживает перезапуск)
({List<String> gear, Map<String, int> pack}) get defaultLoadout;                             // balance.loadout.default
Future<void> startJourney();   // как было + сразу engine.startLoadout(выбранное или default); аналитика loadout_confirmed

// Рюкзак и снаряжение (вкладка «Герой»)
bool useItem(String item);                  // engine.useItem; item_used{source:'manual'}
String heat();                              // engine.heat(now); 'heated' → gear_heated
String heatStatus();                        // для кнопки «Нагреть»
bool isHeated();                            // пометка «горячо» у нагреваемых
// Переполнение (экраны поверх всего, пока hero.overflow.isNotEmpty; кнопка «Идти дальше» скрыта)
OverflowItem? get pendingOverflow;          // hero.overflow.firstOrNull
String? resolveGearOverflow(List<String> keep);
String? resolveBackpackOverflow(String action, {String? swapAction, String? swapItem});
// После последнего решения контроллер вызывает engine.advance(now) (как afterEvent).
// Клубок (экран события)
String clewStatus();                        // 'ready' — кнопка «Спросить клубок» активна
int clewCooldownDays();                     // для подписи «через N дн.»
Map<String, String>? askClew();             // {choiceId: tone}; UI держит ответ до выбора (в состоянии не хранится)
// Зона под маршрутом
String zoneHere();                          // 'city'|'suburb'|'wild' → zoneCity/zoneSuburb/zoneWild
```
Изменения существующего: `continueJourney` учитывает `false` (не сдвигать остановку); `choose()` — после выбора, если `hero.overflow.isNotEmpty`, экран исхода ведёт на экран переполнения, `afterEvent()` вызывается после последнего решения; `OutcomeView.itemsGained` считать по `inv` **и** `gear` (новое снаряжение), а вещи в очереди — отдельно (`hero.overflow`); `buyBlocker` → новые коды; журнал — §5.15; показ рюкзака: `inv` только food/drink/tool, снаряжение — `hero.gear` с `usesLeft/maxUses`, многопорционные — `portionsTotal`.

---

## 8. Аналитика (новые события)

| Событие | Параметры | Когда |
|---|---|---|
| `loadout_confirmed` | `gear` ('socks,raincoat,gas_stove'), `gear_n`, `pack` ('bread:2,water:2,tea:1'), `pack_slots`, `default` (bool) | `startJourney` после `startLoadout` |
| `item_used` | `item`, `source` ('manual' \| 'overflow' \| 'swap'), `hot` (bool), `portions_left` | ручное употребление, «использовать сразу», обмен |
| `gear_heated` | `stove_left`, `heatable_n` | `heat()` вернул `heated` |
| `overflow_resolved` | `kind`, `item`, `action` ('use'\|'drop'\|'stash'\|'keep_new'\|'keep_old'), `swap_action`, `swap_item`, `dropped` ('id,id'), `source` | каждое успешное решение |
| `first_aid_used` | `item`, `stats` ('water'), `left` | в журнале появилась запись `first_aid` после `advance`/`choose` |
| `clew_asked` | `event`, `tones` ('risk,penalty,…') | `askClew` вернул не null |
| `buy` | + `item: 'gas'` и снаряжение | как было |

---

## 9. Тексты (l10n, `app_ru.arb`, ключи в конец файла со своим префиксом)

* Зоны: `zoneCity` «Город», `zoneSuburb` «Пригород», `zoneWild` «Окрестности».
* Старт: `loadoutTitle` «Собери рюкзак», `loadoutGearHeader` «Снаряжение — до {n}», `loadoutGearFreeSlot` «Четвёртая ячейка — для находок в пути», `loadoutPackHeader` «Еда и питьё — до {n} ячеек», `loadoutKindLimit` «Не больше {n} одного вида», `loadoutDefault` «Как посоветовал бы бывалый», `loadoutConfirm` «В путь», ошибки `loadoutErr_<код>` для кодов §5.3.
* Перки: `gearPerkSatiety` «+{value} сытости», `gearPerkWater` «+{value} воды», `gearPerkWarmth` «+{value} тепла», `gearPerkHeat` «горячим +{value} тепла», `gearPerkWarmthDrain` «тепло уходит на {value} % медленнее», `gearPerkWeatherCold` «в непогоду холод на {value} % слабее», `gearPerkSatietyDrain` «голод в пути −{value} %», `gearPerkWaterDrain` «жажда в пути −{value} %», `gearPerkIdleWarmth` «на остановках тепло уходит на {value} % медленнее», `gearPerkDelay` «задержки на {value} % короче», `gearPerkDetour` «крюки на {value} % короче», `gearPerkRisk` «опасные исходы на {value} % реже», `gearPerkRescue` «спасёт от нуля: поднимет до {value}», `gearPerkStove` «кнопка «Нагреть»», `gearPerkRefill` «+{value} зарядов горелке», `gearPerkRefillMax` «до {value}», `gearPerkUses` «зарядов: {value}», `gearPerkPortions` «{value} порции в одной ячейке», `gearPerkAbility_clew` «раз в {value} дн. подскажет, чем кончится выбор».
* Снаряжение/горелка: `gearSlots` «Снаряжение {n}/{max}», `gearUsesLeft` «{n}/{max}», `gearEmptyCharges` «пусто», `gearHeat` «Нагреть», `gearHeatOn` «Горячо!», `gearHeatNoStove` «Нужна горелка», `gearHeatNoGas` «Газ кончился», `gearHeatNothing` «Нечего греть», `gearHot` «горячее», `gearPortions` «{name} ×{n}».
* Рынок: `buyGearFull` «Снаряжение полно», `buyNoStove` «Сначала горелка», `buyGasFull` «Баллон полон».
* Переполнение: `overflowGearTitle` «Что взять с собой», `overflowGearHint` «Отметь {n}. Остальное останется у дороги.», `overflowGearKeepAsIs` «Оставить как есть», `overflowGearConfirm` «Взять», `overflowBackpackTitle` «В рюкзак не лезет», `overflowUseNow` «Использовать сразу», `overflowDrop` «Выбросить», `overflowStash` «Положить в рюкзак», `overflowSwapTitle` «Что освободить?», `overflowSwapUse` «Использовать», `overflowSwapDrop` «Выбросить», `overflowSwapNotFree` «Одна порция ячейку не освободит», `overflowPending` «Сначала реши, что делать с вещами».
* Клубок: `gearClewAsk` «Спросить клубок», `gearClewCooldown` «Клубок отдыхает: {n} дн.», тоны `gearTone_reward` «награда», `_penalty` «наказание», `_mixed` «и так и так», `_risk` «как повезёт», `_death` «смертельно», `_neutral` «ничего особенного».
* Журнал: `logLoadout` «Сергей собрал рюкзак», `logHeat` «Сергей разжёг горелку», `logFirstAid` «Аптечка выручила Сергея», `logAbility` «Клубок подсказал дорогу»; `zone_fallback` не показывать.

---

## 10. Тест совпадения: формат `app/test/fixtures/parity.json` v2

```
{ "format": 2, "t0", "seed", "baseline", "steps", "startDay", "routeLengthM",
  "setup": [ops…],                 // до дней: startLoadout
  "days": [ { "day": "2026-05-01", "ops": [ {"op": <имя>, <аргументы>, "ret": <результат>}, … ], "expected": {снимок} }, … ],
  "zoneProbe": [[posM, zone], …],  // 341 точка: каждое место ±0, ±500, ±3500 м
  "itemPerks": {id: [{key, value}…]}, "starterGear": [...], "starterPack": [...] }
```
Dart-тест создаёт `HeroState.create(w, seed, t0, startDay, todaySteps: baseline)`, `Engine(w, s)` и **проигрывает ops по порядку** (политику бота повторять не нужно), сверяя `ret`:

| op | вызов | ret |
|---|---|---|
| `startLoadout` | `e.startLoadout(gear, pack, now)` | null |
| `syncSteps` | `e.syncSteps(days, now)` | int |
| `claimLogin` | `e.claimLogin(day, now)` | int |
| `advance` | `e.advance(now).length` | int |
| `choose` | `e.choose(choice, now)` | `{ok, died}` |
| `buy` | `e.buy(item, now)` | bool |
| `continueJourney` | `e.continueJourney(now)` | bool |
| `heat` | `e.heat(now)` | String |
| `useItem` | `e.useItem(item, now)` | bool |
| `askClew` | `e.askClew(now)` | `Map<String,String>?` |
| `giveItems` | `e.giveItems(items, source)` | null |
| `resolveGearOverflow` | `e.resolveGearOverflow(keep)` | String? |
| `resolveBackpackOverflow` | `e.resolveBackpackOverflow(action, now, swapAction: …, swapItem: …)` | String? |
| `dismissDeath` | `e.s.stop = null` | null |

Снимок `expected` после ops дня: `pos` (±0.02), `buffer` (±0.02), `coins`, `stats` (±0.002), `inv` (по ключам), `gear` (порядок!), `gearUses`, `heated`, `heatedDay`, `overflow` (список `toJson`), `aidLock`, `portionsLeft`, `abilityReady`, `stop` (тип), `deaths`, `seen` (длина), `journal` (длина), `journalTail` (виды последних 4 записей — для отладки), `rng`, `zone` (`w.zoneAt(s.pos)`), `delayUntil`, `nextRandomAt` (±0.02). Отдельно: `w.zoneAt(p) == zone` для всех `zoneProbe`, `w.itemPerks(id)` == `itemPerks[id]`, `starterGear/starterPack`. Тест «сохранение и загрузка без потерь» — на состоянии после 20 дней сценария (там есть overflow, gear, порции).
Сценарий: старт `gas_stove, first_aid, trekking_poles` + `bread 2, water 1, thermos 1, tea 1`; день 1 — «Нагреть» дважды (`heated`, `on`) и горячее; день 2 — клубок (дальше бот спрашивает его на событиях) и порция термоса; день 3 — 7 пирогов (переполнение рюкзака: use/drop/stash по кругу); день 4 — нагрел и не выпил (день 5: остыло по дате); день 6 — компас и оберег (переполнение снаряжения); аптечка срабатывает дважды, есть смерти, покупка газа, все зоны. Фикстуру перегенерируют после каждого изменения контента/баланса: `python3 tools/sim/make_parity_fixture.py`.

---

## 11. Чек-лист Dart-порта
1. `world.dart`: §3 (зоны, каталог, `loadoutError`, `itemPerks`, `zonePoolSize/eventZone`).
2. `state.dart`: поля §2, `OverflowItem`, `create` из `loadout.default`, миграция v1.
3. `engine.dart`: §4–§5 (в т. ч. `_pickRandom(now)`, `_useOne/_consume/_takeInv`, `_tryRescue` в `_walk` и `_applyEffects`, `aidLock` в `_arrive`, `overflow` в `advance`/`continueJourney`/`_die`, `market` с региональными).
4. `app_controller.dart`: §7–§8.
5. `engine_parity_test.dart`: §10 (проигрывание ops). Без Flutter здесь не запустить — перечитать «глазами компилятора».

---

## 12. Дополнения Dart-порта (сверх таблиц выше; логики эталона не меняют)

* `AppController.startJourney({List<String>? gear, Map<String,int>? pack, bool? isDefault})` — без аргументов берёт набор из `chooseLoadout` (переживает перезапуск, ключ `loadout_v1`), иначе `loadout.default`; набор, не прошедший `loadoutError`, заменяется набором бывалого. `starterGear`/`starterPack` — геттеры контроллера.
* `AppModel` (то, что отдаёт `ref.watch(appProvider)`): `engine`, `pendingOverflow`, `zone`, `heated`, `heatStatus`, `clewStatus`, `clewReady`, `clewCooldownDays`, `gearUses`, `portionsLeft` — только чтение, без логики.
* `OutcomeView.itemsPending` — `{id: n}` вещей, ушедших в очередь переполнения этим выбором; `itemsGained/itemsLost` включают снаряжение.
* После последнего решения переполнения контроллер сам вызывает `advance` (если нет остановки); повторный `afterEvent()` безвреден.
* `Engine.heatableCount()`, `World.itemSpec(id)`, `ItemPerk.toJson()`; `GameContent.eventMood/eventCreature/eventZone/spiritArt(ev)` (`assets/art/spirits/<creature>_<mood>.svg`), `questsOfKind`, `regionalItems`, `itemDesc`.
* `AppController.dropItem(item)` — «Выбросить» на вкладке «Герой»: одна единица еды/питья из `inv` (как `_takeInv(item, 1)`) или вещь из `gear` (как `_onGearRemoved`); аналитика `item_dropped {item, kind}`. В эталоне `engine.py` метода нет — правило живёт в контроллере, движок не менялся (перенести в движок вместе с `engine.py`, если выброс станет правилом игры).
* Дары духов (V5-43, §13.13): ячейки снаряжения считает `Engine.gearUsed()`; `dropItem` — штатный метод движка.
* `Storage.loadHero(world)` мигрирует v1 → v2; нечитаемое сохранение копируется в `hero_v1_broken`, а не теряется.

---

## 13. Дары духов, условные перки, каталог 59 предметов (v5.3, Дополнение A пп. 27–29)

Эталон — `tools/sim/engine.py` (методы ниже), тесты — класс `Gifts` в `tools/sim/test_v53.py`, решения V5-32…V5-41.
Тексты даров — `items.json`; что дарит какой исход — `docs/v5/folklore-gifts.md`; иконки — `docs/v5/items-new-manifest.md`.
Всё, что не описано здесь, работает как раньше; **у предмета без новых полей поведение не меняется ни на бит**.

### 13.1. Новые поля

`balance.json → gifts` (новый раздел):

| Ключ | Значение | Смысл |
|---|---|---|
| `waterArts` | `["river", "lake"]` | событие «у воды» — `ev.art` из списка → условие `water` |
| `waterPlaces` | 21 id мест у большой воды | привал «у воды» (крючок, ракушка); `atWaterPlace()` |
| `middayHours` | `[11, 16]` | полдень по МСК: `from ≤ час < to` |
| `idleWarmthMin` | `0.35` | нижний предел произведения `idleWarmthMult` (уголёк × спальник) |

`balance.json → items.<id>` (в дополнение к §1.1):

| Поле | Тип | Смысл |
|---|---|---|
| `tags` | `List<String>` | метки предмета; сейчас только `"fish"` (fish, dried_fish, ryapushka, rybnik, cod) |
| `cond` | `{any: [midday\|heat\|water], waterDrainMult?, drainKmMult?, riskReduce?, noCoinLoss?}` | **условный перк**: действует, если хотя бы одно условие из `any` активно (§13.3) |
| `camp` | `{satiety?, water?, warmth?: int, waterPlace?: bool, cooldownDays?: int}` | прибавка на каждом привале в месте (§13.6) |
| `foodBoost` | `{tag, satiety?\|water?\|warmth?: double}` | еда с меткой `tag` даёт ×mult (§13.5) |
| `upkeep` | `List<String>` (id еды) | «кормить каждый день» — лапоть (§13.7) |
| `expiresDays` | int | снаряжение исчезает через N игровых дней (венок, §13.7) |
| `sellPrice` | int | можно продать на любом рынке (жемчужина, §13.8) |
| `rescueStats` | `List<String>` | аптечка спасает только эти показатели (спасательное одеяло: `["warmth"]`, §13.9) |
| `hint` | `{cooldownDays ≥ 1, art?: [...], zone?: [...]}` | **подсказка духа**: как клубок, но только в «своих» событиях (§13.2) |
| `ability.kind` | `clew` \| **`guide`** \| **`mirage`** \| **`action`** | `cooldownDays` теперь ≥ 0; 0 — только у предмета с `uses` (без перезарядки) |
| `ability.at`, `zones`, `water`, `effect` | только у `action` | где работает и что даёт (§13.4) |
| `uses` | теперь и у `tool` | заряды инструмента; хранятся в **том же** `gearUses`; на 0 инструмент исчезает |

### 13.2. Состояние (`HeroState`, JSON) — 4 новых поля, версия по-прежнему `v: 2`

| JSON/Dart | Тип | Умолчание `fromJson` | Смысл |
|---|---|---|---|
| `undo` | `Json?` | `null` | вред последнего исхода — для «Сучка»/«Бусины» (§13.4) |
| `fed` | `Map<String,bool>` | `{}` | лапоть накормлен в текущий игровой день |
| `expires` | `Map<String,int>` | `{}` | id → игровая дата, с которой предмет пропадает |
| `dayMark` | int | `0` | последняя обработанная игровая дата (§13.7) |

`create`: `undo=null, fed={}, expires={}, dayMark=gameDay(nowMs)`; `_loadoutInto` (старт-набор) дополнительно сбрасывает `undo=null, fed={}, expires={}`. Python добавляет отсутствующие ключи в конструкторе `Engine` (`STATE_DEFAULTS_13`) — Dart делает то же в `fromJson`.
`abilityReady` теперь хранит три вида ключей: `<id>` (способность `ability`), `<id>:hint` (подсказка духа), `<id>:camp` (привал с перезарядкой).
Структура `undo` (все ключи необязательны, кроме `event`):
```
{ "event": id события,
  "coins": int (сколько реально списано),
  "stats": {stat: double потеря после clamp},
  "removed": {id: {"n": int, "portions": int|null, "uses": int|null}},   // что реально вынуто из inv
  "removedGear": [{"item": id, "uses": int|null, "expires": int|null, "fed": bool|null}],
  "bonusKm": double (значение до bonus_reset),
  "delay": int (delayUntil ДО эффекта delay),
  "detour": true, "prevDetour": Json|null (detour ДО эффекта; только если у эффекта нет detour_end) }
```

### 13.3. Условные перки (`cond`) и `gearMult` с контекстом

* `perkOn(g)`: `!items[g].containsKey('upkeep') || (fed[g] ?? false)`. Предмет, у которого `perkOn == false`, **полностью** пропускается в `gearMult`, `gearFlag`, `riskFactor`, `statGain`, `_camp`.
* `gearMult(key, [sub], {List<String> ctx = const []})`: `m = 1.0`; для `g` в `gear` по порядку, если `perkOn(g)`: сначала базовое значение `items[g][key]` (как §5.4), **затем** `cond`, если `ctx.isNotEmpty && cond.any.any(ctx.contains)`: `v = cond[key]` (Map → `[sub]`), `num` → `m = m * v`. Порядок умножений: g1.база, g1.cond, g2.база, g2.cond… Без `ctx` результат совпадает с §5.4 бит в бит.
* `gearFlag(key, ctx)`: true, если у какого-нибудь `g` (perkOn) `items[g][key] == true` или активный `cond[key] == true`. Сейчас ключ один — `noCoinLoss`.
* `riskFactor({ctx})`: как §5.10, но для каждого `g` (perkOn): `f *= (1 − база.riskReduce)` если есть, затем `f *= (1 − cond.riskReduce)` если cond активен.
* Контекст пути (`_drainWalk(km, int? now)`; `_walk` передаёт свой `now`): `ctx = []`; погода точки `== 'heat'` → `add('heat')`; `now != null && isMidday(now)` → `add('midday')`. Все четыре множителя §5.4 считаются с `ctx: ctx`. Полдень: `h = ((now + utcOffsetHours·msHour) % msDay) / msHour` (double) → `from <= h && h < to`. Время ходьбы = `now` вызова `advance` (весь буфер, пройденный в этот заход, — «в полдень», если заход в полдень).
* Контекст события (`eventCtx(ev)`): `['water']`, если `ev.art ∈ gifts.waterArts`, иначе `[]`. В `choose`: `ctx = eventCtx(ev)`; `outcomeWeights(choice, ctx)` (→ `riskFactor(ctx)`), `_applyEffects(..., ctx)`.
* `noCoinLoss` (ракушка у воды): в `_applyEffects`, если `coins` со знаком «−» и `gearFlag('noCoinLoss', ctx)` → `amt = 0` (монеты не меняются, в `undo` не пишется). Требование `requires.coins` по-прежнему проверяется.

### 13.4. Кнопки даров: `guide`, `mirage`, `action` (`giftStatus` / `useGift`)

```dart
String giftStatus(String item, int now); // ready|no_item|bad_kind|no_charges|cooldown|nothing|not_here
String useGift(String item, int now);    // 'ok' или код giftStatus
```
`giftStatus` по порядку: `!hasItem` → `no_item`; `ability.kind ∉ {guide, mirage, action}` → `bad_kind` (клубок — через `askClew`); есть `uses` и `usesLeft <= 0` → `no_charges`; `abilityCooldownDays(item) > 0` → `cooldown`; дальше по виду:
* `guide` (сучок, еловая лапка): `undo != null && (undo.containsKey('delay') || undo.containsKey('detour'))` → `ready`, иначе `nothing`;
* `mirage` (бусина, кудель): `undo != null` → `ready`, иначе `nothing`;
* `action`: `at` (по умолчанию `any`) `== 'place'` и остановка не `place`/`chapter_end` → `not_here`; `zones` задан и `zoneHere() ∉ zones` (зона **позиции героя**) → `not_here`; `water == true` и `!atWaterPlace()` (остановка-место из `gifts.waterPlaces`) → `not_here`; у `effect` нет `give` и **все** затронутые показатели (`effect[stat]` или `warmth` при `warmthToMax`) уже `>= stats.max` → `nothing` (заряд не тратится впустую); иначе `ready`.

`useGift` при `ready`:
1. `guide`/`mirage`: `evId = undo.event`; `_undo(kind)`:
   * оба: если есть `delay` → `delayUntil = undo.remove('delay')`; если есть `detour` → убрать ключ, `detour = undo.remove('prevDetour')`;
   * `mirage` дополнительно: `coins += undo.coins`; `stats[k] += lost` → `_clampStats()`; `removed`: еда/питьё → `giveItems({id: n}, 'mirage')` (может уйти в overflow), затем если `portions != null`, `inv[id] > 0` и `!portionsLeft.containsKey(id)` → `portionsLeft[id] = portions`; инструменты → `inv[id] += n`, `uses != null` → `gearUses[id] = uses`; `removedGear` по порядку: уже в `gear` → пропустить; есть место → `gear.add`, восстановить `gearUses/expires/fed` (не null); нет места → `overflow.add(OverflowItem('gear', id, 1, 'mirage'))`; `bonusKm` → вернуть; `undo = null`;
   * `guide`: если в `undo` не осталось ключей, кроме `event`, → `undo = null` (иначе остаток можно снять «Бусиной»).
2. `action`: для `satiety, water, warmth`: `stats[k] += effect[k]` (если задан); `warmthToMax` → `warmth = max.toDouble()`; `_clampStats()`; `give` → `giveItems(give, item)`.
3. Общее: `cooldownDays > 0` → `abilityReady[item] = gameDay(now) + cooldownDays`; `_spendCharge(item)`: есть `uses` → `gearUses[item] −= 1`; если стало ≤ 0 **и** `itemType == 'tool'` → `inv.remove(item)`, `gearUses.remove(item)` (снаряжение с 0 зарядов остаётся, как горелка).
4. `_log(now, 'gift', …, {item, ability: kind, event: evId или ''})`, `_saveRng()`, вернуть `'ok'`.

**Где живёт `undo`:** `choose` — `undo = null` перед `_applyEffects`; после, если не погиб и `_harm != null`: `undo = {..._harm, 'event': ev.id}`. `advance` — `undo = null` **первой строкой** (до `applyTime`). `_die` — `undo = null`. Значит, кнопки «Сучок»/«Бусина» показываются только на экране исхода, до «Идти дальше» (контроллер не должен звать `advance` между `choose` и экраном исхода).
**Что пишется в `_harm`** (в `_applyEffects`, порядок §5.7): `coins` — если монет стало меньше (`before − after`); `stats` — для показателей со знаком «−»: `pre[k] − stats[k]` после clamp, только > 0; `removed/removedGear` — то, что `_removeItems` реально вынул (теперь он возвращает запись: из `gear` — с `uses/expires/fed`; из `inv` — `n = have − left` при `have > 0`, `portions = portionsLeft[id]`, `uses = gearUses[id]`; у инструмента, вынутого целиком, `gearUses` удаляется); `bonusKm` — значение до сброса; `delay` — `delayUntil` до эффекта; `detour/prevDetour` — **только если у эффекта нет `detour_end`** (сюжетное ответвление дары не отменяют). `_harm = harm.isEmpty ? null : harm` записывается перед проверкой смерти. Аптечка, сработавшая в этом исходе, не возвращается.

Каталог действий (`at`, `zones`, `water`, `effect`, перезарядка, заряды):

| id | Кнопка (l10n `giftAction_<id>`) | at | условие | effect | cd | uses |
|---|---|---|---|---|---|---|
| `venik_bannik` | «Попариться» | place | зона suburb/city | warmth +30 | 3 | — |
| `stone_bannik` | «Согреться» | any | — | warmth +20 | 0 | 2 |
| `hand_warmers` | «Грелка» | any | — | warmth +12 | 0 | 3 |
| `key_ovinnik` | «Ночлег в овине» | place | зона suburb | warmth → max | 5 | — |
| `sheaf_ovinnik` | «Сноп на ночь» | place | — | warmth +35 | 0 | 1 |
| `hook_vodyanoy` | «Закинуть» | place | место у воды | give `fish` 1 | 1 | 5 |
| `twig_leshy` | «Сучок» (guide) | экран исхода | `undo` с delay/detour | отмена delay/detour | 1 | — |
| `spruce_leshy` | «Еловая лапка» (guide) | экран исхода | то же | то же | 0 | 3 |
| `bead_kikimora` | «Дунуть на бусину» (mirage) | экран исхода | `undo != null` | отмена всего вреда | 3 | — |
| `kudel_kikimora` | «Кудель» (mirage) | экран исхода | то же | то же | 0 | 1 |

### 13.5. Подсказки духов (`hint`) и обобщённый «Спросить клубок»

Подсветка исходов теперь есть у четырёх «добрых» даров (по одному на духа; у Яги — клубок и нитка):

| Дар | Чей | `hint.art` (события) | перезарядка |
|---|---|---|---|
| `twig_leshy` | леший | forest, swamp, field | 2 дн. |
| `shell_vodyanoy` | водяной | river, lake | 2 дн. |
| `ember_domovoy` | домовой | village, hut, town | 2 дн. |
| `venik_bannik` | банник | bathhouse, campfire, rain, night | 2 дн. |
| `ball_yaga` | Яга | любое (ability clew) | 3 дн. |
| `thread_yaga` | Яга | любое (ability clew, uses 2) | — |

`hintMatches(h, ev) = (h.art == null || h.art.contains(ev.art)) && (h.zone == null || h.zone.contains(ev.zone))` (пустой список = нет фильтра).
`heldItems()` = `[...gear, ...inv.keys.where(n > 0).sorted()]`.
`_clewSources()` — **порядок траты**: (1) все `hint`-предметы из `heldItems` (ключ `id:hint`); (2) `ability.kind == 'clew'` с `uses` (нитка; ключ `id`); (3) `clew` без `uses` (клубок; ключ `id`). Источник **готов**: `abilityCooldownDays(ключ) == 0` и (нет `uses` или `usesLeft > 0`).
`_clewPick(now)`: нет `currentEvent()` → null; первый готовый источник, у которого `hint == null` или `hintMatches`.
`clewStatus(now)`: источников нет → `no_item`; `anyReady` = есть готовый; нет события → `anyReady ? 'no_event' : 'cooldown'`; `_clewPick != null` → `ready`; иначе `anyReady ? 'not_here' : 'cooldown'` (**новый код `not_here`**: готова только подсказка духа, а событие не его). Для одного клубка коды совпадают с §5.14.
`askClew(now)`: не `ready` → null; `(item, key, h) = _clewPick`; тоны как §5.14; `abilityReady[key] = gameDay(now) + (h != null ? h.cooldownDays : ability.cooldownDays)`; если `h == null` → `_spendCharge(item)` (нитка: −1, на 0 исчезает); `_log('ability', {item, event})`.
Для UI: `String? clewItem(int now)` — чей голос подскажет (подпись кнопки: `gearClewAsk_<id>`, например «Спросить сучок»); `int clewCooldownDays(int now)` = минимум `abilityCooldownDays(ключ)` по источникам с зарядом (без заряда — 999), 0 если источников нет.

### 13.6. Привал (`camp`): спальник, уголёк, ракушка

В `_arrive('place')` **после** `warmthRestore/waterRefill`, `_clampStats` и записи журнала `place` — `_camp(p, now)`: `water = gifts.waterPlaces.contains(p.id)`; для `g` в `gear` по порядку с `camp` и `perkOn(g)`: если `camp.waterPlace && !water` → пропустить; `cd = camp.cooldownDays ?? 0`, ключ `g:camp`; `cd > 0 && abilityCooldownDays(ключ) > 0` → пропустить; `stats[k] += camp[k]` для заданных; `cd > 0` → `abilityReady[ключ] = gameDay(now) + cd`; запомнить `g`. Если кто-то сработал: `_clampStats()`, `_log('camp', {items: [...]})`. Срабатывает и на финале главы, и на финише (любое прибытие в место).
Числа: `sleeping_bag` +15 тепла (каждый привал); `ember_domovoy` +10 тепла (каждый); `shell_vodyanoy` +10 воды у воды, раз в игровой день.
`applyTime`: `idle = max(gifts.idleWarmthMin ?? 0.0, gearMult('idleWarmthMult'))`; `rate = rate * gearMult('warmthDrainMult') * idle` (было `* gearMult('idleWarmthMult')`; `max` возвращает тот же double — без даров бит в бит как раньше).

### 13.7. Смена игровой даты: лапоть и венок (`_dayRoll`)

`applyTime(now)`: `lastTick = now` → `_expireHeat(now)` → **`_dayRoll(now)`** → `if hours <= 0 return` → … (вызов до раннего выхода).
`_dayRoll(now)`: `d = gameDay(now)`; `dayMark == d` → выход; `dayMark = d`; (1) для `g` в копии `gear`: `expires[g] != null && d >= expires[g]` → `gear.remove(g)`, `_onGearRemoved(g)`, `_log('wilt', {item: g})`; (2) для `g` в копии `gear` с `upkeep`: `food = _upkeepFood(upkeep)`; `food != null` → `_spendPortion(food)` (одна порция, **без** прибавки показателей); `fed[g] = food != null`; `_log('upkeep', {item: g, food})`.
`_upkeepFood(order)`: если единиц еды (`type == 'food'`, сумма `n` по `inv`) **меньше 2** → null («последнюю краюшку домовой не берёт»); иначе первый id из `order` с `inv > 0` и типом food; иначе первый id еды по алфавиту.
`_spendPortion(item)` — бывшее начало `_useOne` (порция или единица, §5.5); `_useOne = _spendPortion + _consume`.
`_onGearAdded(g)` (вызывается в `_gainGear` при добавлении и в `resolveGearOverflow` для оставленной новой): `uses` → `gearUses[g] = uses`; `expiresDays` → `expires[g] = gameDay(lastTick) + expiresDays` (дата получения = дата последнего `applyTime`; `giveItems` не принимает `now`); `upkeep` → `fed[g] = true` (плата отдана при получении). `_onGearRemoved(g)`: `gearUses/expires/fed.remove(g)` — в `resolveGearOverflow` для выброшенных, в `_removeItems`, при увядании. Венок, полученный в день D, работает дни D, D+1, D+2 и исчезает при первом `applyTime` дня D+3.

### 13.8. Еда: `foodBoost`, продажа

`statGain(item, stat)`: `v = items[item][stat] ?? 0`; `v == 0` → 0; для `g` в `gear` с `foodBoost`, `foodBoost.containsKey(stat)`, `perkOn(g)` и `item.tags.contains(foodBoost.tag)`: `v = pyRound(v * foodBoost[stat])`. Используется в `_consume` (вместо `items[item][stat]`) и в `_itemGain` (автоеда). Речная лента: `fish` 35 → `pyRound(52.5) = 52` (к чётному!), `ryapushka` 35 → 52, `cod` 45 → `pyRound(67.5) = 68`, `rybnik` 55 → `pyRound(82.5) = 82`, `dried_fish` 30 → 45.
Продажа: `List<(String, int)> sellOffers()` — пусто, если `market()` пуст; иначе предметы `inv` (`n > 0`, по алфавиту) с `sellPrice`, цена = `sellPrice` (без наценки рынка). `String? sellBlocker(item)`: `no_market` → `no_item` → `not_sellable`. `bool sell(item, now)`: `_takeInv(item, 1)`, `coins += sellPrice`, `_log('sell', {item, price})`, `_saveRng()`.

### 13.9. Аптечка с `rescueStats`, инструменты с зарядами

`_tryRescue`: `zero = [k ∈ STATS, stats[k] <= 0]`; предмет подходит, если `rescueTo`, `usesLeft > 0` и **все** `zero` входят в `rescueStats ?? STATS`; иначе — следующий `g`. Спасательное одеяло (`rescueStats: [warmth]`, `rescueTo 30`, 1 заряд) спасает только от холода; при нуле воды — ищется аптечка.
`giveItems` для `tool` с `uses`: если `inv[it] > 0` → `gearUses[it] = min(maxUses, usesLeft + uses·n)`; иначе `inv[it] = 1`, `gearUses[it] = min(maxUses, uses·n)` (один экземпляр, повтор пополняет заряды). `maxUses` по умолчанию = `uses`.

### 13.10. Перки для экрана (дополнение к §6, порядок фиксирован, **после** `ability_<kind>`)

`rescue` → если есть `rescueStats`: ключ `rescue` + `Stat` с заглавной (`rescueWarmth`) на том же месте. Затем после `ability_<kind>`:
1. у `action`: `actionSatiety|actionWater|actionWarmth` (значение), `actionWarmthMax` (0), `actionGive_<id>` (n);
2. `hint` (cooldownDays) — текст `gearPerkHint_<itemId>` (у каждого духа свой: «в лесу подскажет…»);
3. `camp` + `Stat` (+ `AtWater`, если `waterPlace`): `campWarmth`, `campWaterAtWater`;
4. `cond`, суффикс `At` + условия с заглавной подряд (`AtMiddayHeat`, `AtWater`): `waterDrain…` (из `waterDrainMult`), `satietyDrain…`, `waterDrain…` (из `drainKmMult`), `risk…` (`pyRound(r·100)`), `noCoinLoss…` (0);
5. `boost` + Tag + Stat: `boostFishSatiety` = `pyRound((mult − 1)·100)` = 50;
6. `upkeep` (1), 7. `expires` (дней), 8. `sell` (монет).
Примеры: `twig_leshy [ability_guide 1, hint 2]`; `shell_vodyanoy [hint 2, campWaterAtWater 10, noCoinLossAtWater 0]`; `ear_poludnitsa [satietyDrain 8, waterDrainAtMiddayHeat 30]`; `hook_vodyanoy [uses 5, ability_action 1, actionGive_fish 1]`; `sleeping_bag [idleWarmth 50, campWarmth 15]`. Полный эталон — `parity.json → itemPerks`.
Новые l10n-ключи (префикс `gear…`/`gift…`, в конец `app_ru.arb`): `gearPerkAbility_guide` «раз в {value} дн. выведет из крюка и задержки», `gearPerkAbility_mirage` «раз в {value} дн. отведёт беду», `gearPerkAbility_action` «раз в {value} дн.» (0 — не показывать), `gearPerkActionWarmth` «+{value} тепла по кнопке», `gearPerkActionWarmthMax` «тепло до максимума», `gearPerkActionGive_fish` «+{value} рыба», `gearPerkHint_<id>`, `gearPerkCampWarmth` «на привале +{value} тепла», `gearPerkCampWaterAtWater` «раз в день у воды +{value} воды», `gearPerkWaterDrainAtMiddayHeat` «в полдень и в зной жажда −{value} %», `gearPerkRiskAtWater` «у воды опасные исходы на {value} % реже», `gearPerkNoCoinLossAtWater` «у воды переправа даром», `gearPerkBoostFishSatiety` «рыба сытнее на {value} %», `gearPerkUpkeep` «каждый день съедает 1 еду», `gearPerkExpires` «завянет через {value} дн.», `gearPerkSell` «продашь за {value} монет», `gearPerkRescueWarmth` «спасёт от холода: поднимет до {value}»; кнопки `giftAction_<id>` (таблица §13.4); статусы `giftStatus_<код>`; журнал `logGift` «Дар духа помог Сергею», `logCamp` «Добрый привал», `logUpkeep` «Домовой в лапте поужинал» / `logUpkeepHungry` «Домовому нечего есть — сегодня не греет», `logWilt` «Венок завял», `logSell` «Продано: {item}». Подписи клубка: `gearClewAsk_<id>` («Спросить клубок / нитку / сучок / ракушку / уголёк / веник»), `gearClewNotHere` «Здесь дух не подскажет».

### 13.11. Тест совпадения (дополнение к §10)

Новые op: `useGift` → `e.useGift(item, now)` → String; `sell` → `e.sell(item, now)` → bool. Снимок дня дополнительно: `fed`, `expires`, `dayMark`, `undoKeys` (отсортированные ключи `undo` или null). Сценарий: дни 7, 9, 11, 15 получают дары (бусина, сучок, крючок, жемчужина → лапоть, камешек, сноп → венок → ракушка, нитка); в дни 12–17 бот берёт **последний** доступный вариант (смерти, аптечка); бот жмёт `mirage`/`guide` после вредного исхода и `action` на привале, продаёт жемчужину; венок вянет (журнал `wilt`), лапоть ест (`upkeep`), ракушка даёт воду у воды (`camp`).

### 13.12. Стартовый набор и каталог

`loadout.default.gear` = **`[trekking_poles, first_aid, gas_stove]`** (набор бывалого: палки, аптечка, горелка); `pack` без изменений. Каталог — 59 предметов: 22 прежних + 17 даров + `compass_ded` (дар Вити в «Попутчике» вместо клубка) + 4 общих (`oatmeal`, `space_blanket`, `hand_warmers` — рынки city/town; `valdai_bell` — Валдай) + 15 региональных (`markets.regional`, 28 мест от Твери до Териберки). Порционные: `thermos` 4, `valdai_baranki` 4, `oatmeal`/калитки 3, `tver_pryanik`, `dried_fish`, `cloudberry`, `ivan_chai` 2.

### 13.13. Дары духов без ячеек и «Выбросить» (V5-43)

* `items.<id>.gift: true` — дар духа. `World.isGift(id)` / `is_gift`. Дар действует как снаряжение (все перки §5.4, §13.3–13.7), но **не занимает ячейку**: `Engine.gearUsed()` = число не-даров в `gear`; лимит `gearSlots` и `gear_full` считаются по `gearUsed()`; `gearSlotsLeft = gearSlots − gearUsed()`.
* `_gainGear`: дар всегда добавляется в `gear` (без overflow); повтор — как дубликат §5.7 (монеты по цене 0 — фактически игнор). `resolveGearOverflow(keep)`: кандидаты — только не-дары + новая вещь, дары остаются на местах (`gear = [g ∈ gear: дар или g ∈ keep] + [новая, если в keep]`); дар в очереди из старого сохранения просто берётся. «Бусина» возвращает дар без проверки места.
* `String? dropItem(String item)` (Python `drop_item`): дар у героя → `'gift'`; в `gear` → убрать целиком (`_onGearRemoved`); в `inv` → `_takeInv(item, 1)` (инструмент, вынутый целиком, теряет `gearUses`); иначе `'no_item'`; успех → `null`, `_saveRng()`, в журнал не пишется. Контроллер: `bool dropItem(item)`, `String? dropBlocker(item)`; аналитика `item_dropped`.
* UI: ячейки снаряжения показывают только не-дары (`hero.gear.where(!isGift)`), дары — строкой; экран «Что взять с собой» выбирает среди не-даров.
* Фикстура: op `dropItem` → `e.dropItem(item)` → `String?`.

---

## 14. Ночёвка в пути (V5-45) и защита сохранения (V5-44)

### 14.1. Ночёвка
* `balance.json → night`: `atPhase` 0.75, `skipNearPlaceKm` 3, `warmth` 40, `morning: [{id, weight, satiety?, water?, warmth?}]`. Шаг ночёвок `L = movement.dayLengthKm × 1000` (та же длина «суток пути», что `Engine.dayPhase()`).
* Состояние: `nextNightAt` (double, м). `create`: `firstNightAfter(b, −1)` = `atPhase × dayLengthKm × 1000`. Старое сохранение без поля (`fromJson` → −1) — `Engine` в конструкторе ставит `firstNightAfter(b, maxPos)`. `firstNightAfter(b, x)`: `at = atPhase·dayLengthKm·1000`, `while at <= x + 1e-6: at += L` (повторное сложение, бит в бит Python ↔ Dart).
* `nextStop`: после случайного — `(nextNightAt, 'night')`, если `night` есть, `nextNightAt > pos`, ближе прочих и `pos ≥ maxPos − 1e-6` (после смерти, на повторном пути, ночёвок нет).
* `_arrive('night')` (+ `aidLock = false`, как у любой остановки): `mo = morning[rng.pickWeighted(weights)]` (тратит RNG); `gain = {warmth: night.warmth}` + числа `mo` по `satiety, water, warmth`; `stats += gain`, `_clampStats`; `_log('night', {morning, gain})`; `_camp({id: ''}, now)` (спальник и т. п.; «у воды» — нет); `stop = {type: 'night', morning: id, gain}`; `nextNightAt = firstNightAfter(b, pos)`.
* `_arrive('place')` после `_camp`: если `0 ≤ nextNightAt − pos ≤ skipNearPlaceKm·1000` → `nextNightAt = firstNightAfter(b, pos + skip)` (ночуют в месте).
* «Идти дальше»: `continueJourney` → `stop = null`, `advance` ведёт героя тем же буфером. Рынка нет (`market()` пуст).
* UI: экран исхода (`_NightScreen` в `stop_screens.dart`) — `nightTitle`, `nightText` + `nightMorning_<id>`, чипы из `gain`; карточка на главной `stopNight`; журнал `logNight`. Аналитика `night_stop {morning, km}`.
* Фикстура: снимок дня + `nextNightAt` (±0.02).

### 14.2. Сохранение героя (V5-44)
`Storage.saveHero(hero) → Future<bool>`: JSON собирается синхронно; `prefs.reload()`; если `hero_rev_v1` на диске больше номера, который видела эта копия, — `false` (героя сохранил другой Flutter-движок), иначе номер +1 и запись. `heroChangedElsewhere()`, `loadHeroFresh(world)`. Контроллер: `refresh()` сначала проверяет `heroChangedElsewhere` и берёт свежую копию; `_commit`/`refresh` при `false` перечитывают героя. `MainActivity` — `launchMode="singleTask"`.

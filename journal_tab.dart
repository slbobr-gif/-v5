// Журнал — вариант B «Таймлайн с цепочками» (docs/v5/04-art-style.md, раздел «Журнал»):
// шапка «Глава N · день D» и «● N новых», фильтры-чипы и расширенный фильтр, лента по дням
// с цветными стеклянными метками и дорожками цепочек слева, нижняя панель записи
// «до ↑ · мой выбор · после ↓». Утренние мысли открывают thought_screen.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../app/journal_view.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/glass_paint.dart';
import 'thought_screen.dart';

final _km = NumberFormat('0.#', 'ru');
final _num = NumberFormat.decimalPattern('ru');
final _time = DateFormat('HH:mm', 'ru');

/// Сколько дорожек цепочек помещается слева от ленты.
const _maxLanes = 4;

/// Цвет стеклянной метки по виду записи.
Color journalKindColor(JKind k) => switch (k) {
      JKind.story => Palette.accent,
      JKind.random => Palette.ember,
      JKind.spirit => const Color(0xFF9B7BE0),
      JKind.quest => const Color(0xFF5B8FE8),
      JKind.item => const Color(0xFF3FBF8A),
      JKind.death => Palette.coralLine,
      JKind.thought => const Color(0xFF7FC4EE),
      JKind.camp => Palette.parchmentDim,
    };

String _kindLabel(AppLocalizations l, JKind k) => switch (k) {
      JKind.story => l.journalKindStory,
      JKind.random => l.journalKindRandom,
      JKind.spirit => l.journalKindSpirit,
      JKind.quest => l.journalKindQuest,
      JKind.item => l.journalKindItem,
      JKind.death => l.journalKindDeath,
      JKind.thought => l.journalKindThought,
      JKind.camp => l.journalKindCamp,
    };

String _toneLabel(AppLocalizations l, JTone t) => switch (t) {
      JTone.good => l.journalToneGood,
      JTone.bad => l.journalToneBad,
      JTone.mixed => l.journalToneMixed,
    };

String _zoneLabel(AppLocalizations l, String z) => switch (z) {
      'city' => l.zoneCity,
      'suburb' => l.zoneSuburb,
      _ => l.zoneWild,
    };

const _zones = ['city', 'suburb', 'wild'];

/// Цвета цепочек: линии квестов — синие, линии духов — фиолетовые, смерть — коралл.
Map<String, Color> _chainColors(JournalView v) {
  const quest = [Color(0xFF5B8FE8), Color(0xFF4FA3A5), Color(0xFF7FC4EE)];
  const spirit = [Color(0xFF9B7BE0), Color(0xFFC08BE8), Color(0xFFB39DF2)];
  var qi = 0;
  var si = 0;
  final out = <String, Color>{};
  for (final ch in v.chainList) {
    switch (ch.kind) {
      case JChainKind.quest:
        out[ch.id] = quest[qi % quest.length];
        qi++;
      case JChainKind.spirit:
        out[ch.id] = spirit[si % spirit.length];
        si++;
      case JChainKind.death:
        out[ch.id] = Palette.coralLine;
    }
  }
  return out;
}

String _chainName(AppLocalizations l, AppController c, JChain ch) {
  if (ch.kind == JChainKind.death) return l.journalChainDeath;
  final q = ch.quest;
  if (q != null) return '${c.content.world.quests[q]?['title'] ?? q}';
  final cr = ch.creature;
  return cr == null ? '' : '${c.content.creatures[cr]?['name'] ?? cr}';
}

/// Заголовок строки ленты (null — служебная запись, в журнале не показывается).
String? _title(AppLocalizations l, AppController c, JRow r) {
  if (r.kind == JKind.thought) return l.journalThoughtTitle(r.thoughtDay ?? r.day);
  final e = r.entry;
  if (e == null) return null;
  final d = e.data;
  switch (e.kind) {
    case 'event':
      return '${d['title']}';
    case 'place':
      return l.logPlace(c.content.placeName('${d['place']}'));
    case 'death':
      return l.logDeath(c.content.placeName('${d['place']}'));
    case 'goal':
      return l.logGoal(toI(d['steps']), toI(d['coins']));
    case 'login':
      return l.logLogin(toI(d['coins']));
    case 'buy':
      return l.logBuy(c.content.itemName('${d['item']}'), toI(d['price']));
    case 'eat':
      return l.logEat(c.content.itemName('${d['item']}'));
    case 'quest_done':
      return l.logQuestDone;
    case 'detour_back':
      return l.logDetourBack;
    case 'finish':
      return l.logFinish;
    // v5.3 (docs/v5/08 §5.15, §13): рюкзак, горелка, аптечка, подсказки, дары, привал, лапоть, венок, продажа.
    case 'loadout':
      return l.logLoadout;
    case 'night': // V5-45: ночёвка в пути
      return l.logNight;
    case 'heat':
      return l.logHeat;
    case 'first_aid':
      return l.logFirstAid(c.content.itemName('${d['item']}'));
    case 'ability':
      return l.logAbility(c.content.itemName('${d['item']}'));
    case 'gift':
      return l.logGift(c.content.itemName('${d['item']}'));
    case 'camp':
      final items = d['items'];
      final names = items is List ? items.map((i) => c.content.itemName('$i')).join(', ') : '';
      return l.logCamp(names);
    case 'upkeep':
      final food = d['food'];
      return food == null ? l.logUpkeepHungry : l.logUpkeep(c.content.itemName('$food'));
    case 'wilt':
      return l.logWilt(c.content.itemName('${d['item']}'));
    case 'sell':
      return l.logSell(c.content.itemName('${d['item']}'), toI(d['price']));
  }
  return null;
}

/// Время и км записи: «09:35 · 87,9 км».
String _meta(AppLocalizations l, JRow r) {
  final time = _time.format(DateTime.fromMillisecondsSinceEpoch(r.t));
  final km = r.km;
  return km == null ? time : l.journalTimeKm(time, _km.format(km));
}

class JournalTab extends ConsumerStatefulWidget {
  const JournalTab({super.key, this.newSince = 0});

  /// Записи позже этого времени — новые (UiFlags.journalReadAt на момент открытия вкладки).
  final int newSince;

  @override
  ConsumerState<JournalTab> createState() => _JournalTabState();
}

/// Элемент ленты: заголовок дня или строка.
class _Item {
  _Item.day(JDay this.day, this.newCount) : row = null;
  _Item.row(JRow this.row)
      : day = null,
        newCount = 0;
  final JDay? day;
  final JRow? row;
  final int newCount;
}

class _JournalTabState extends ConsumerState<JournalTab> {
  /// all | chains | spirits | thoughts | items
  String _tab = 'all';

  /// Фильтр по цепочке (id JChain): остальное приглушено.
  String? _chain;
  final Set<JKind> _types = <JKind>{};
  final Set<String> _zoneSet = <String>{};
  final Set<JTone> _tones = <JTone>{};

  /// Строка, открытая в нижней панели.
  int? _sel;

  bool get _advOn => _types.isNotEmpty || _zoneSet.isNotEmpty || _tones.isNotEmpty;

  bool _isNew(JRow r) => widget.newSince > 0 && r.kind != JKind.thought && r.t > widget.newSince;

  bool _passTab(JRow r) => switch (_tab) {
        'chains' => r.chain != null,
        'spirits' => r.kind == JKind.spirit,
        'thoughts' => r.kind == JKind.thought,
        'items' => r.kind == JKind.item,
        _ => true,
      };

  bool _passAdv(JRow r) =>
      (_types.isEmpty || _types.contains(r.kind)) &&
      (_zoneSet.isEmpty || _zoneSet.contains(r.zone)) &&
      (_tones.isEmpty || _tones.contains(r.tone));

  void _reset() => setState(() {
        _tab = 'all';
        _chain = null;
        _types.clear();
        _zoneSet.clear();
        _tones.clear();
      });

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final c = ref.read(appProvider.notifier);
    final hero = m.hero;
    final content = m.content;
    final v = c.journalView();
    if (hero == null || content == null || v == null) return const Scaffold(body: SizedBox.shrink());

    final titles = <int, String>{};
    for (final r in v.rows) {
      final t = _title(l, c, r);
      if (t != null) titles[r.id] = t;
    }
    final all = v.rows.where((r) => titles.containsKey(r.id)).toList();
    final colors = _chainColors(v);
    final chain = _chain == null ? null : v.chains[_chain];
    final chainRows = chain?.rows.toSet();
    final visible = all.where((r) => (chain != null || _passTab(r)) && _passAdv(r)).toList();
    final visibleIds = {for (final r in visible) r.id};
    final hits = chainRows == null ? visible.length : visible.where((r) => chainRows.contains(r.id)).length;
    final newCount = all.where(_isNew).length;

    // Лента: дни сверху вниз от сегодняшнего, внутри дня — от новых к старым.
    final items = <_Item>[];
    for (final d in v.days.reversed) {
      final rs = [
        for (final id in d.rows.reversed)
          if (visibleIds.contains(id)) v.rows[id],
      ];
      if (rs.isEmpty) continue;
      items.add(_Item.day(d, rs.where(_isNew).length));
      for (final r in rs) {
        items.add(_Item.row(r));
      }
    }

    // Дорожки цепочек: интервалы от первого до последнего звена в ленте, жадно по дорожкам.
    final spans = <String, List<int>>{};
    for (var i = 0; i < items.length; i++) {
      final ch = items[i].row?.chain;
      if (ch == null) continue;
      final s = spans[ch];
      if (s == null) {
        spans[ch] = [i, i];
      } else {
        s[1] = i;
      }
    }
    final laneOf = <String, int>{};
    final laneEnd = List<int>.filled(_maxLanes, -1);
    final order = spans.keys.toList()..sort((a, b) => spans[a]![0].compareTo(spans[b]![0]));
    for (final ch in order) {
      final s = spans[ch]!;
      for (var k = 0; k < _maxLanes; k++) {
        if (laneEnd[k] < s[0]) {
          laneOf[ch] = k;
          laneEnd[k] = s[1];
          break;
        }
      }
    }
    var lanes = 0;
    for (final k in laneOf.values) {
      if (k + 1 > lanes) lanes = k + 1;
    }
    final gutter = lanes == 0 ? 0.0 : 6.0 + lanes * 9.0;
    List<_Seg> segsAt(int i) {
      final out = <_Seg>[];
      laneOf.forEach((ch, k) {
        final s = spans[ch]!;
        if (i < s[0] || i > s[1]) return;
        out.add(_Seg(
          k,
          colors[ch] ?? Palette.parchmentDim,
          up: i > s[0],
          down: i < s[1],
          dot: items[i].row?.chain == ch,
          dim: _chain != null && _chain != ch,
        ));
      });
      return out;
    }

    final showCounter = _chain != null || _advOn || _tab != 'all';
    final tabs = <(String, String)>[
      ('all', l.journalFilterAll),
      ('chains', l.journalFilterChains),
      ('spirits', l.journalFilterSpirits),
      ('thoughts', l.journalFilterThoughts),
      ('items', l.journalFilterItems),
    ];

    return Scaffold(
      appBar: AppBar(
        title: ScreenTitle(
          kicker: l.journalKicker(content.world.chapterAt(hero.pos), v.today),
          title: l.journalTitle,
        ),
        actions: [
          if (newCount > 0)
            Padding(
              padding: const EdgeInsets.only(right: Gap.m),
              child: Center(child: _NewChip(label: l.journalNewCount(newCount))),
            ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 0),
            child: Row(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        for (final t in tabs)
                          Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: _Pill(
                              label: t.$2,
                              selected: _chain != null ? t.$1 == 'chains' : _tab == t.$1,
                              dot: t.$1 == 'thoughts' && !c.thoughtSeenToday(),
                              onTap: () => setState(() {
                                _tab = t.$1;
                                _chain = null;
                              }),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                _FilterButton(label: l.journalFilterMore, on: _advOn, onTap: () => _openFilter(l)),
              ],
            ),
          ),
          if (_tab == 'chains' && _chain == null && v.chainList.isNotEmpty)
            SizedBox(
              height: 48,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                children: [
                  for (final ch in v.chainList)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: _Pill(
                        label: _chainName(l, c, ch),
                        selected: false,
                        bar: colors[ch.id],
                        onTap: () => setState(() => _chain = ch.id),
                      ),
                    ),
                ],
              ),
            ),
          if (showCounter)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 2),
              child: Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        if (chain != null)
                          _Pill(
                            label: _chainName(l, c, chain),
                            selected: true,
                            close: true,
                            bar: colors[chain.id],
                            onTap: () => setState(() => _chain = null),
                          ),
                        for (final k in _types)
                          _Pill(
                            label: _kindLabel(l, k),
                            selected: true,
                            close: true,
                            onTap: () => setState(() => _types.remove(k)),
                          ),
                        for (final z in _zoneSet)
                          _Pill(
                            label: _zoneLabel(l, z),
                            selected: true,
                            close: true,
                            onTap: () => setState(() => _zoneSet.remove(z)),
                          ),
                        for (final t in _tones)
                          _Pill(
                            label: _toneLabel(l, t),
                            selected: true,
                            close: true,
                            onTap: () => setState(() => _tones.remove(t)),
                          ),
                        Text(
                          l.journalCount(hits, all.length),
                          style: const TextStyle(color: Palette.parchmentDim, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  for (final ch in laneOf.keys)
                    Padding(
                      padding: const EdgeInsets.only(left: 3),
                      child: Container(
                        width: 14,
                        height: 4,
                        decoration: BoxDecoration(
                          color: alpha(colors[ch] ?? Palette.parchmentDim, _chain == null || _chain == ch ? 1.0 : 0.35),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: all.isEmpty
                ? Center(
                    child: Padding(padding: const EdgeInsets.all(Gap.l), child: Text(l.journalEmpty)),
                  )
                : (hits == 0
                    ? ListView(
                        padding: const EdgeInsets.fromLTRB(12, Gap.s, 12, Gap.l),
                        children: [_EmptyPlate(text: l.journalFilterEmpty, reset: l.journalReset, onReset: _reset)],
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, Gap.l),
                        itemCount: items.length,
                        itemBuilder: (context, i) {
                          final it = items[i];
                          final day = it.day;
                          final Widget body;
                          if (day != null) {
                            body = _DayHeader(day: day, today: v.today, newCount: it.newCount);
                          } else {
                            final r = it.row!;
                            body = _RowCard(
                              row: r,
                              title: titles[r.id] ?? '',
                              sub: r.kind == JKind.thought
                                  ? '«${c.content.thoughtForDay(r.thoughtDay ?? r.day).quote}»'
                                  : (r.choice == null ? null : '«${r.choice}»'),
                              meta: r.kind == JKind.thought ? '' : _meta(l, r),
                              isNew: _isNew(r),
                              newLabel: l.journalNewDot,
                              selected: _sel == r.id,
                              dim: chainRows != null && !chainRows.contains(r.id),
                              onTap: () => _open(v, titles, colors, r),
                            );
                          }
                          if (gutter == 0) return body;
                          return IntrinsicHeight(
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SizedBox(width: gutter, child: CustomPaint(painter: _LanePainter(segsAt(i)))),
                                Expanded(child: body),
                              ],
                            ),
                          );
                        },
                      )),
          ),
        ],
      ),
    );
  }

  /// Тап по записи: мысль — экран мысли; остальное — нижняя панель.
  void _open(JournalView v, Map<int, String> titles, Map<String, Color> colors, JRow r) {
    final day = r.thoughtDay;
    if (r.kind == JKind.thought && day != null) {
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ThoughtScreen(day: day)));
      return;
    }
    setState(() => _sel = r.id);
    showSafeSheet<void>(
      context: context,
      builder: (ctx) => _EntrySheet(
        view: v,
        row: r,
        titles: titles,
        colors: colors,
        onOpen: (other) {
          Navigator.of(ctx).pop();
          _open(v, titles, colors, other);
        },
        onLine: (id) {
          Navigator.of(ctx).pop();
          setState(() {
            _tab = 'chains';
            _chain = id;
          });
        },
      ),
    ).then((_) {
      if (mounted && _sel == r.id) setState(() => _sel = null);
    });
  }

  /// Расширенный фильтр: тип, зона, исход — нижний лист с чипами.
  void _openFilter(AppLocalizations l) {
    showSafeSheet<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) {
          void toggle<T>(Set<T> s, T value) {
            setState(() {
              if (!s.remove(value)) s.add(value);
            });
            setSheet(() {});
          }

          Widget group(String title, List<Widget> chips) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SectionHeader(title),
                  Wrap(spacing: 6, children: chips),
                ],
              );
          // Чипы прокручиваются, кнопки «Сбросить» / «Готово» всегда видны над системной панелью.
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: Gap.m),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                        Text(l.journalFilterMore, style: Theme.of(ctx).textTheme.titleMedium),
                        group(l.journalFilterType, [
                          for (final k in JKind.values)
                            _Pill(
                              label: _kindLabel(l, k),
                              selected: _types.contains(k),
                              mark: journalKindColor(k),
                              onTap: () => toggle<JKind>(_types, k),
                            ),
                        ]),
                        group(l.journalFilterZone, [
                          for (final z in _zones)
                            _Pill(
                              label: _zoneLabel(l, z),
                              selected: _zoneSet.contains(z),
                              bar: Palette.zone(z),
                              onTap: () => toggle<String>(_zoneSet, z),
                            ),
                        ]),
                        group(l.journalFilterOutcome, [
                          for (final t in JTone.values)
                            _Pill(
                              label: _toneLabel(l, t),
                              selected: _tones.contains(t),
                              onTap: () => toggle<JTone>(_tones, t),
                            ),
                        ]),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(Gap.m, Gap.m, Gap.m, 0),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          setState(() {
                            _types.clear();
                            _zoneSet.clear();
                            _tones.clear();
                          });
                          setSheet(() {});
                        },
                        child: Text(l.journalReset),
                      ),
                    ),
                    const SizedBox(width: Gap.s),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: Text(l.journalFilterDone),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- нижняя панель записи

class _EntrySheet extends ConsumerWidget {
  const _EntrySheet({
    required this.view,
    required this.row,
    required this.titles,
    required this.colors,
    required this.onOpen,
    required this.onLine,
  });

  final JournalView view;
  final JRow row;
  final Map<int, String> titles;
  final Map<String, Color> colors;
  final ValueChanged<JRow> onOpen;
  final ValueChanged<String> onLine;

  static String _signed(num v) => v > 0 ? '+${v.toInt()}' : '${v.toInt()}';

  /// Звено «до/после»: заголовок и мой выбор.
  Widget _link(AppLocalizations l, JRow r) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('«${titles[r.id] ?? ''}»', style: const TextStyle(color: Palette.parchment, fontSize: 13)),
          Text(
            r.choice == null ? l.journalDayShort(r.day) : '${l.journalDayShort(r.day)} · «${r.choice}»',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Palette.parchmentDim, fontSize: 11.5),
          ),
        ],
      );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final ch = view.chains[row.chain];
    final col = colors[row.chain] ?? journalKindColor(row.kind);
    final prev = view.prevInChain(row);
    final next = view.nextInChain(row);
    final title = titles[row.id] ?? '';
    final step = row.step;
    final head = step == null ? title : l.journalStepOf(title, step + 1);
    final statNames = {'satiety': l.statSatiety, 'water': l.statWater, 'warmth': l.statWarmth};
    String items(JEffect f) => f.value > 1 ? '${c.content.itemName(f.key)} ×${f.value.toInt()}' : c.content.itemName(f.key);
    String fxText(JEffect f) => switch (f.type) {
          'coins' => l.fxCoins(_signed(f.value)),
          'stat' => '${statNames[f.key] ?? f.key} ${_signed(f.value)}',
          'give' => l.fxGained(items(f)),
          'remove' => l.fxLost(items(f)),
          'delay' => l.fxDelay(f.value.toInt()),
          'detour' => l.fxDetour(_km.format(f.value)),
          'shortcut' => l.fxShortcut(_km.format(f.value)),
          'death' => l.journalKindDeath,
          'rollback' => l.journalFxRollback(_km.format(f.value)),
          _ => '',
        };
    String questTitle(String q) => '${c.content.world.quests[q]?['title'] ?? q}';
    final opened = [
      for (final o in row.opened)
        o.type == 'quest' ? l.journalOpenedQuest(questTitle(o.quest)) : l.journalOpenedStep(o.step, questTitle(o.quest)),
    ];

    Widget? after;
    if (next != null) {
      after = _link(l, next);
    } else if (ch != null) {
      final n = ch.nextStep;
      final km = ch.nextKm;
      if (n != null && km != null) {
        // без спойлеров: только номер шага и расстояние
        after = Row(
          children: [
            Text('? ', style: TextStyle(color: col, fontSize: 13, fontWeight: FontWeight.w700)),
            Expanded(
              child: Text(l.journalNextStep(n, _km.format(km)),
                  style: const TextStyle(color: Palette.parchment, fontSize: 12.5)),
            ),
          ],
        );
      } else if (ch.done) {
        after = Text(l.journalLineDone, style: const TextStyle(color: Palette.parchment, fontSize: 12.5));
      }
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: Palette.inkRaised,
              borderRadius: BorderRadius.circular(Gap.radiusS),
              border: Border.all(color: col, width: 1.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (prev != null) _LinkBox(label: l.journalBefore, onTap: () => onOpen(prev), child: _link(l, prev)),
                Container(
                  padding: const EdgeInsets.fromLTRB(_cardPad, 10, _cardPad, 12),
                  decoration: BoxDecoration(border: Border(left: BorderSide(color: col, width: _stripe))),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          _Mark(color: journalKindColor(row.kind), size: 18),
                          const SizedBox(width: Gap.s),
                          Expanded(
                            child: Text(head,
                                style: const TextStyle(color: Palette.parchment, fontSize: 16, fontWeight: FontWeight.w700)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text('${l.journalDayShort(row.day)} · ${_meta(l, row)}',
                          style: const TextStyle(color: Palette.parchmentDim, fontSize: 11.5)),
                      if (row.choice != null) ...[
                        const SizedBox(height: Gap.s),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check, size: 16, color: Palette.accent),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text('«${row.choice}»',
                                  style: const TextStyle(color: Palette.parchment, fontSize: 13.5, height: 1.3)),
                            ),
                          ],
                        ),
                      ],
                      for (final a in row.alts)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(
                                width: 16,
                                child: Text('?',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: _faint, fontSize: 12.5, fontWeight: FontWeight.w700)),
                              ),
                              const SizedBox(width: 6),
                              Expanded(child: Text('«$a»', style: const TextStyle(color: _faint, fontSize: 12.5, height: 1.3))),
                            ],
                          ),
                        ),
                      if (row.outcome.isNotEmpty) ...[
                        const SizedBox(height: Gap.s),
                        StoryText(row.outcome,
                            style: const TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.4)),
                      ],
                      if (row.effects.isNotEmpty) ...[
                        const SizedBox(height: Gap.s),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [for (final f in row.effects) _FxChip(text: fxText(f), negative: f.negative)],
                        ),
                      ],
                      if (opened.isNotEmpty) ...[
                        const SizedBox(height: Gap.s),
                        Text(l.journalOpened(opened.join(', ')),
                            style: const TextStyle(color: Palette.accent, fontSize: 12)),
                      ],
                    ],
                  ),
                ),
                if (after != null)
                  _LinkBox(label: l.journalAfter, onTap: next == null ? null : () => onOpen(next), child: after),
              ],
            ),
          ),
          if (ch != null) ...[
            const SizedBox(height: Gap.s),
            Align(
              alignment: Alignment.centerLeft,
              child: AccentChipButton(
                label: l.journalLineButton(_chainName(l, c, ch)),
                icon: Icons.timeline,
                onTap: () => onLine(ch.id),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Полоса цепочки слева у основного блока панели и общий горизонтальный отступ её блоков.
const _stripe = 3.0;
const _cardPad = 12.0;

/// Тусклый цвет невыбранных вариантов.
const _faint = Color(0xFF56677A);

class _LinkBox extends StatelessWidget {
  const _LinkBox({required this.label, required this.child, this.onTap});

  final String label;
  final Widget child;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Palette.chipBg,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          // тот же левый край, что у текста основного блока (полоса цепочки + отступ)
          padding: const EdgeInsets.fromLTRB(_stripe + _cardPad, 7, _cardPad, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label.toUpperCase(),
                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 10, letterSpacing: 0.6)),
              const SizedBox(height: 2),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

class _FxChip extends StatelessWidget {
  const _FxChip({required this.text, required this.negative});

  final String text;
  final bool negative;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: Palette.chipBg,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: negative ? Palette.chipLine : Palette.tabLine),
      ),
      child: Text(text,
          style: TextStyle(color: negative ? Palette.parchmentDim : const Color(0xFFBFEFEA), fontSize: 11.5)),
    );
  }
}

// ---------------------------------------------------------------- лента

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.day, required this.today, required this.newCount});

  final JDay day;
  final int today;
  final int newCount;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final from = day.kmFrom;
    final to = day.kmTo;
    final stats = [
      if (from != null && to != null) l.journalDayKm(_km.format(from), _km.format(to)),
      if (day.steps > 0) l.journalDaySteps(_num.format(day.steps)),
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 12, 0, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                day.day == today ? l.journalDayToday(day.day) : l.thoughtDay(day.day),
                style: const TextStyle(color: Palette.parchment, fontSize: 13.5, fontWeight: FontWeight.w700),
              ),
              const SizedBox(width: Gap.s),
              Expanded(
                child: Text(
                  stats,
                  textAlign: TextAlign.end,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 11),
                ),
              ),
            ],
          ),
          if (newCount > 0)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(l.journalNewCount(newCount),
                  style: const TextStyle(color: Palette.accent, fontSize: 11, fontWeight: FontWeight.w700)),
            ),
        ],
      ),
    );
  }
}

class _RowCard extends StatelessWidget {
  const _RowCard({
    required this.row,
    required this.title,
    required this.sub,
    required this.meta,
    required this.isNew,
    required this.newLabel,
    required this.selected,
    required this.dim,
    required this.onTap,
  });

  final JRow row;
  final String title;
  final String? sub;
  final String meta;
  final bool isNew;
  final String newLabel;
  final bool selected;
  final bool dim;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final death = row.kind == JKind.death;
    final s = sub;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Opacity(
        opacity: dim ? 0.35 : 1.0,
        child: Material(
          color: Palette.inkRaised,
          clipBehavior: Clip.antiAlias,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: selected ? Palette.accent : (death ? alpha(Palette.coralLine, 0.6) : Palette.inkHigh),
              width: selected ? 1.5 : 1,
            ),
          ),
          child: InkWell(
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 7, 10, 7),
                child: Row(
                  children: [
                    _Mark(color: journalKindColor(row.kind), size: 16),
                    const SizedBox(width: Gap.s),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              Flexible(
                                child: Text(
                                  title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: death ? Palette.coralLine : Palette.parchment,
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              if (isNew)
                                Padding(
                                  padding: const EdgeInsets.only(left: 6),
                                  child: Semantics(label: newLabel, child: const _NewDot()),
                                ),
                            ],
                          ),
                          if (s != null)
                            Text(
                              s,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: Palette.parchmentDim,
                                fontSize: 12,
                                fontStyle: row.kind == JKind.thought ? FontStyle.italic : FontStyle.normal,
                              ),
                            ),
                        ],
                      ),
                    ),
                    if (meta.isNotEmpty) ...[
                      const SizedBox(width: Gap.s),
                      Text(meta, style: const TextStyle(color: Palette.parchmentDim, fontSize: 10.5)),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _EmptyPlate extends StatelessWidget {
  const _EmptyPlate({required this.text, required this.reset, required this.onReset});

  final String text;
  final String reset;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 4, 4, 4),
      decoration: BoxDecoration(
        color: Palette.chipBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Palette.chipLine),
      ),
      child: Row(
        children: [
          const Icon(Icons.search, size: 16, color: Palette.parchmentDim),
          const SizedBox(width: Gap.s),
          Expanded(child: Text(text, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5))),
          TextButton(onPressed: onReset, child: Text(reset)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- мелкие элементы

class _NewDot extends StatelessWidget {
  const _NewDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: Palette.accent,
        shape: BoxShape.circle,
        border: Border.all(color: Palette.lead, width: 1.5),
      ),
    );
  }
}

/// «● 4 новых» в шапке.
class _NewChip extends StatelessWidget {
  const _NewChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 28,
      padding: const EdgeInsets.symmetric(horizontal: 11),
      decoration: BoxDecoration(
        color: alpha(Palette.accent, 0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Palette.tabLine),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const _NewDot(),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: Palette.accent, fontSize: 12, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

/// Чип фильтра: обычный, выбранный (бирюзовая рамка), с крестиком, с цветной полоской или меткой.
class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.selected,
    required this.onTap,
    this.close = false,
    this.dot = false,
    this.bar,
    this.mark,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool close;
  final bool dot;
  final Color? bar;
  final Color? mark;

  @override
  Widget build(BuildContext context) {
    final b = bar;
    final mk = mark;
    final fg = selected ? Palette.accent : Palette.parchmentDim;
    return Semantics(
      button: true,
      selected: selected,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 44),
          // heightFactor: 1 — в ограниченной по высоте строке Center не растягивается на всю высоту.
          child: Center(
            widthFactor: 1,
            heightFactor: 1,
            child: Container(
              height: 30,
              padding: const EdgeInsets.symmetric(horizontal: 11),
              decoration: BoxDecoration(
                color: selected ? alpha(Palette.accent, 0.12) : Palette.inkRaised,
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: selected ? Palette.accent : Palette.inkHigh, width: selected ? 1.5 : 1),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (b != null) ...[
                    Container(
                      width: 12,
                      height: 4,
                      decoration: BoxDecoration(color: b, borderRadius: BorderRadius.circular(2)),
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (mk != null) ...[
                    _Mark(color: mk, size: 13),
                    const SizedBox(width: 5),
                  ],
                  // Чип живёт и в горизонтальной прокрутке (ширина не ограничена — Flexible нельзя),
                  // и в Wrap: длинное имя линии обрезается по пределу ширины, а не переполняет чип.
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 220),
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: fg,
                        fontSize: 12.5,
                        fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                      ),
                    ),
                  ),
                  if (close) ...[
                    const SizedBox(width: 5),
                    Icon(Icons.close, size: 14, color: fg),
                  ],
                  if (dot) ...[
                    const SizedBox(width: 5),
                    const _NewDot(),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Кнопка расширенного фильтра (слои).
class _FilterButton extends StatelessWidget {
  const _FilterButton({required this.label, required this.on, required this.onTap});

  final String label;
  final bool on;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: label,
      child: Semantics(
        button: true,
        label: label,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: SizedBox(
            width: 44,
            height: 44,
            child: Center(
              child: Container(
                width: 36,
                height: 30,
                decoration: BoxDecoration(
                  color: on ? alpha(Palette.accent, 0.12) : Palette.inkRaised,
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: on ? Palette.accent : Palette.inkHigh, width: on ? 1.5 : 1),
                ),
                child: const Icon(Icons.layers_outlined, size: 17, color: Palette.accent),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Стеклянная метка-ромб по виду записи (как значки витража: свинцовый контур и блик).
class _Mark extends StatelessWidget {
  const _Mark({required this.color, this.size = 16});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(width: size, height: size, child: CustomPaint(painter: _MarkPainter(color)));
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 20.0, size.height / 20.0);
    final p = Path()
      ..moveTo(10, 1.5)
      ..lineTo(18.5, 10)
      ..lineTo(10, 18.5)
      ..lineTo(1.5, 10)
      ..close();
    final light = Color.lerp(color, Colors.white, 0.35) ?? color;
    final dark = Color.lerp(color, Colors.black, 0.35) ?? color;
    canvas.drawPath(p, glassFill(const Rect.fromLTWH(0, 0, 20, 20), [light, color, dark]));
    canvas.drawPath(p, stroke(1.6));
    final h = Path()
      ..moveTo(10, 4.5)
      ..lineTo(15.5, 10)
      ..lineTo(10, 10)
      ..close();
    canvas.drawPath(h, solid(Colors.white, 0.28));
    canvas.restore();
  }

  @override
  bool shouldRepaint(_MarkPainter oldDelegate) => oldDelegate.color != color;
}

/// Отрезок дорожки цепочки в одной строке ленты.
class _Seg {
  const _Seg(this.lane, this.color, {required this.up, required this.down, required this.dot, required this.dim});
  final int lane;
  final Color color;
  final bool up;
  final bool down;
  final bool dot;
  final bool dim;
}

class _LanePainter extends CustomPainter {
  _LanePainter(this.segs);

  final List<_Seg> segs;

  @override
  void paint(Canvas canvas, Size size) {
    final cy = size.height / 2;
    for (final s in segs) {
      final x = 5.0 + s.lane * 9.0;
      final op = s.dim ? 0.3 : 1.0;
      final line = stroke(3, s.color, op)..strokeCap = StrokeCap.butt;
      if (s.up) canvas.drawLine(Offset(x, 0), Offset(x, cy), line);
      if (s.down) canvas.drawLine(Offset(x, cy), Offset(x, size.height), line);
      if (s.dot) {
        canvas.drawCircle(Offset(x, cy), 5, solid(s.color, op));
        canvas.drawCircle(Offset(x, cy), 5, stroke(2, Glass.lead));
      }
    }
  }

  @override
  bool shouldRepaint(_LanePainter oldDelegate) => true;
}

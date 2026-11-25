// Записная книжка путника (25.11): всё, что игрок видел во всех путях, — духи, звери, встречи,
// ночёвки, места с открытками и мысли. Невиданное — силуэтом. Счётчики «увидено N из M».

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../data/content_repository.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import '../widgets/finale_widgets.dart';
import '../widgets/postcard.dart';

/// Запись книжки: id, название, текст (для открытой), картинка, глава (для группировки).
class _Entry {
  const _Entry(this.id, this.title, this.text, {this.art, this.chapter = 0});
  final String id;
  final String title;
  final String text;
  final String? art;
  final int chapter;
}

int _chapterOf(Json e) {
  for (final t in (e['tags'] as List? ?? const [])) {
    final s = '$t';
    if (s.startsWith('ch') && int.tryParse(s.substring(2)) != null) return int.parse(s.substring(2));
  }
  return 0; // «в любой главе»
}

class NotebookScreen extends ConsumerStatefulWidget {
  const NotebookScreen({super.key, this.initial = 'spirits'});

  final String initial;

  @override
  ConsumerState<NotebookScreen> createState() => _NotebookScreenState();
}

class _NotebookScreenState extends ConsumerState<NotebookScreen> {
  late String _cat = widget.initial;

  static const cats = ['spirits', 'animals', 'postcards', 'nights', 'meetings', 'thoughts'];

  List<_Entry> _entries(GameContent content, String cat) {
    final w = content.world;
    switch (cat) {
      case 'spirits':
        return [
          for (final e in content.creatures.entries)
            _Entry(e.key, '${e.value['name'] ?? e.key}', '${e.value['character'] ?? ''}',
                art: 'assets/art/creatures/${e.key}.svg'),
        ];
      case 'animals':
        return [
          for (final e in w.randoms.where((e) => e['wild'] == true))
            _Entry('${e['id']}', '${e['title']}', '${e['text']}',
                art: 'assets/art/scenes/${e['art'] ?? 'forest'}.svg', chapter: _chapterOf(e)),
        ];
      case 'meetings':
        return [
          for (final e in w.randoms.where((e) => e['wild'] != true))
            _Entry('${e['id']}', '${e['title']}', '${e['text']}', chapter: _chapterOf(e)),
        ]..sort((a, b) => a.chapter.compareTo(b.chapter));
      case 'nights':
        return [
          for (final n in content.nights.values)
            _Entry('${n['id']}', '${n['title']}', '${n['text']}', chapter: toI(n['ch'])),
        ];
      case 'postcards':
        return [
          for (final id in content.postcards.keys)
            _Entry(id, content.placeName(id), content.postcards[id]!,
                chapter: toI(w.placeById[id]?['chapter'] ?? 0)),
        ];
      case 'thoughts':
        return [
          for (final t in content.thoughts)
            _Entry('${t.day}', '№ ${t.day}', '${t.quote}\n\n— ${t.author}'),
        ];
    }
    return const [];
  }

  Set<String> _seen(AppModel m, String cat) {
    final p = m.profile;
    if (p == null) return const {};
    if (cat == 'postcards') return p.postcards.keys.toSet();
    return (p.collected[cat] ?? const <String>[]).toSet();
  }

  String _catName(AppLocalizations l, String cat) => switch (cat) {
        'spirits' => l.nbSpirits,
        'animals' => l.nbAnimals,
        'postcards' => l.nbPostcards,
        'nights' => l.nbNights,
        'meetings' => l.nbMeetings,
        _ => l.nbThoughts,
      };

  String _chapterName(AppLocalizations l, int ch) => ch == 0 ? l.nbAnyChapter : l.nbChapter(ch);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final content = m.content!;
    var total = 0;
    var seenAll = 0;
    final counts = <String, (int, int)>{};
    for (final cat in cats) {
      final all = _entries(content, cat);
      final seen = _seen(m, cat);
      final n = all.where((e) => seen.contains(e.id)).length;
      counts[cat] = (n, all.length);
      total += all.length;
      seenAll += n;
    }
    final entries = _entries(content, _cat);
    final seen = _seen(m, _cat);
    final (n, of) = counts[_cat]!;
    return Scaffold(
      appBar: AppBar(title: ScreenTitle(kicker: l.nbKicker(seenAll, total), title: l.nbTitle)),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 44,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                for (final cat in cats)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text('${_catName(l, cat)} ${counts[cat]!.$1}/${counts[cat]!.$2}'),
                      selected: _cat == cat,
                      onSelected: (_) => setState(() => _cat = cat),
                    ),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(Gap.m, Gap.s, Gap.m, Gap.s),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(l.nbSeenOf(n, of), style: const TextStyle(color: Palette.parchmentDim)),
              const SizedBox(height: 6),
              AccentProgress(value: of == 0 ? 0 : n / of),
            ]),
          ),
          Expanded(
            child: switch (_cat) {
              'spirits' || 'animals' || 'postcards' => _Grid(
                  entries: entries,
                  seen: seen,
                  cat: _cat,
                  onTap: (e) => _open(context, l, content, e),
                ),
              'thoughts' => _ThoughtGrid(entries: entries, seen: seen, onTap: (e) => _open(context, l, content, e)),
              _ => _Grouped(
                  entries: entries,
                  seen: seen,
                  chapterName: (ch) => _chapterName(l, ch),
                  onTap: (e) => _open(context, l, content, e),
                ),
            },
          ),
        ],
      ),
    );
  }

  void _open(BuildContext context, AppLocalizations l, GameContent content, _Entry e) {
    if (_cat == 'postcards') {
      showPostcard(context, content, e.id, ref.read(appProvider).profile?.postcards[e.id]);
      return;
    }
    showSafeSheet<void>(
      context: context,
      builder: (ctx) => SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(Gap.m, 0, Gap.m, Gap.m),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (e.art != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(Gap.radiusS),
              child: Art(e.art!, height: 160),
            ),
          const SizedBox(height: Gap.s),
          Text(e.title, style: Theme.of(ctx).textTheme.titleLarge),
          const SizedBox(height: Gap.s),
          StoryText(e.text),
        ]),
      ),
    );
  }
}

/// Плитки с картинкой: духи, звери, открытки. Невиданное — тёмный силуэт и «?».
class _Grid extends StatelessWidget {
  const _Grid({required this.entries, required this.seen, required this.cat, required this.onTap});

  final List<_Entry> entries;
  final Set<String> seen;
  final String cat;
  final void Function(_Entry) onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return GridView.builder(
      padding: const EdgeInsets.fromLTRB(Gap.m, 0, Gap.m, Gap.l),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 170,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 0.82,
      ),
      itemCount: entries.length,
      itemBuilder: (_, i) {
        final e = entries[i];
        final open = seen.contains(e.id);
        final art = cat == 'postcards' ? postcardArt(e.id) : e.art;
        Widget pic = art == null ? const SizedBox.shrink() : Art(art, fit: BoxFit.cover);
        if (!open) {
          pic = ColorFiltered(
            colorFilter: const ColorFilter.mode(Palette.inkHigh, BlendMode.srcATop),
            child: pic,
          );
        }
        return InkWell(
          borderRadius: BorderRadius.circular(Gap.radiusS),
          onTap: open ? () => onTap(e) : null,
          child: Container(
            decoration: BoxDecoration(
              color: Palette.inkRaised,
              borderRadius: BorderRadius.circular(Gap.radiusS),
              border: Border.all(color: open ? Palette.tabLine : Palette.inkHigh),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Expanded(
                child: Stack(fit: StackFit.expand, children: [
                  pic,
                  if (!open)
                    const Center(child: Text('?', style: TextStyle(fontSize: 34, color: Palette.parchmentDim))),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
                child: Text(
                  open ? e.title : l.nbUnknown,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 13, color: open ? Palette.parchment : Palette.parchmentDim),
                ),
              ),
            ]),
          ),
        );
      },
    );
  }
}

/// Список по главам: встречи и ночёвки. Невиданное — «· · ·».
class _Grouped extends StatelessWidget {
  const _Grouped({required this.entries, required this.seen, required this.chapterName, required this.onTap});

  final List<_Entry> entries;
  final Set<String> seen;
  final String Function(int) chapterName;
  final void Function(_Entry) onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final chapters = entries.map((e) => e.chapter).toSet().toList()..sort();
    final rows = <Widget>[];
    for (final ch in chapters) {
      final list = entries.where((e) => e.chapter == ch).toList();
      final n = list.where((e) => seen.contains(e.id)).length;
      rows.add(Padding(
        padding: const EdgeInsets.fromLTRB(Gap.m, Gap.m, Gap.m, 4),
        child: Text('${chapterName(ch).toUpperCase()} · $n/${list.length}',
            style: const TextStyle(color: Palette.accent, fontSize: 12, letterSpacing: 1.2)),
      ));
      for (final e in list) {
        final open = seen.contains(e.id);
        rows.add(ListTile(
          dense: true,
          leading: Icon(open ? Icons.bookmark : Icons.bookmark_border,
              color: open ? Palette.accent : Palette.inkHigh, size: 20),
          title: Text(open ? e.title : l.nbUnknownDots,
              style: TextStyle(color: open ? Palette.parchment : Palette.parchmentDim)),
          onTap: open ? () => onTap(e) : null,
        ));
      }
    }
    return ListView(padding: const EdgeInsets.only(bottom: Gap.l), children: rows);
  }
}

/// Мысли — сетка номеров 1…365: открытые светятся, тап — цитата.
class _ThoughtGrid extends StatelessWidget {
  const _ThoughtGrid({required this.entries, required this.seen, required this.onTap});

  final List<_Entry> entries;
  final Set<String> seen;
  final void Function(_Entry) onTap;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      padding: const EdgeInsets.fromLTRB(Gap.m, 0, Gap.m, Gap.l),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 52,
        mainAxisSpacing: 6,
        crossAxisSpacing: 6,
      ),
      itemCount: entries.length,
      itemBuilder: (_, i) {
        final e = entries[i];
        final open = seen.contains(e.id);
        return InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: open ? () => onTap(e) : null,
          child: Container(
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: open ? Palette.accentDeep.withAlpha(90) : Palette.inkRaised,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: open ? Palette.accent : Palette.inkHigh),
            ),
            child: Text(e.id,
                style: TextStyle(fontSize: 12, color: open ? Palette.parchment : Palette.parchmentDim)),
          ),
        );
      },
    );
  }
}

/// Сколько всего в книжке: для бейджа на кнопке в Журнале.
(int, int) notebookProgress(AppModel m) {
  final c = m.content;
  final p = m.profile;
  if (c == null || p == null) return (0, 0);
  final total = c.creatures.length +
      c.world.randoms.length +
      c.postcards.length +
      c.nights.length +
      c.thoughts.length;
  final seen = p.collected.entries
          .where((e) => e.key != 'places')
          .fold<int>(0, (a, e) => a + e.value.length) +
      p.postcards.length;
  return (seen, total);
}

/// Показать открытку места: карточка и «Отправить».
void showPostcard(BuildContext context, GameContent content, String placeId, String? day) {
  final l = AppLocalizations.of(context);
  showDialog<void>(
    context: context,
    barrierColor: const Color(0xB3040710),
    builder: (ctx) => Center(
      child: Material(
        type: MaterialType.transparency,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          PostcardCard(content: content, placeId: placeId, day: day),
          const SizedBox(height: Gap.m),
          Row(mainAxisSize: MainAxisSize.min, children: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(), child: Text(l.nbClose)),
            const SizedBox(width: Gap.s),
            FilledButton.icon(
              icon: const Icon(Icons.ios_share),
              label: Text(l.postcardSend),
              onPressed: () {
                Navigator.of(ctx).pop();
                shareCardDialog(
                  context,
                  card: PostcardCard(content: content, placeId: placeId, day: day),
                  text: l.postcardShareText(content.placeName(placeId), shareLink()),
                  kind: 'postcard',
                );
              },
            ),
          ]),
        ]),
      ),
    ),
  );
}

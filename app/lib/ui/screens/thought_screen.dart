// Утренняя мысль: цитата стоика, рассуждение Сергея и приватный ответ игрока.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import '../widgets/common.dart';
import 'home.dart' show weatherName;

class ThoughtScreen extends ConsumerStatefulWidget {
  const ThoughtScreen({super.key, required this.day});
  final int day;

  @override
  ConsumerState<ThoughtScreen> createState() => _ThoughtScreenState();
}

class _ThoughtScreenState extends ConsumerState<ThoughtScreen> {
  late final TextEditingController _answer;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final c = ref.read(appProvider.notifier);
    _answer = TextEditingController(text: (c.answers()['${widget.day}']?['text'] as String?) ?? '');
    if (widget.day == c.journeyDay()) {
      Future.microtask(() => c.markThoughtSeen(widget.day));
    }
  }

  @override
  void dispose() {
    _answer.dispose();
    super.dispose();
  }

  String _fill(String text) {
    final m = ref.read(appProvider);
    final c = ref.read(appProvider.notifier);
    final l = AppLocalizations.of(context);
    final hero = m.hero!;
    final w = m.content!.world;
    final eng = Engine(w, hero);
    final place = c.content.placeName('${w.lastPlaceBefore(hero.pos)['id']}');
    final chapter = '${w.chapterById(w.chapterAt(hero.pos))['title']}';
    final km = NumberFormat.decimalPattern('ru').format(eng.kmLeft().round());
    return text
        .replaceAll('{place}', place)
        .replaceAll('{chapter}', chapter)
        .replaceAll('{km_left}', km)
        .replaceAll('{weather}', weatherName(l, eng.weatherHere()).toLowerCase());
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final t = c.content.thoughtForDay(widget.day);
    return Scaffold(
      appBar: AppBar(title: Text(l.thoughtDay(widget.day))),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(Gap.l),
          children: [
            Text('«${t.quote}»',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontStyle: FontStyle.italic, height: 1.4)),
            const SizedBox(height: Gap.s),
            Text('— ${t.author}${t.source.isNotEmpty ? ', ${t.source}' : ''}',
                style: const TextStyle(color: Palette.parchmentDim)),
            const SizedBox(height: Gap.l),
            StoryText(_fill(t.text), style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.55)),
            if (t.isOpen) ...[
              const SizedBox(height: Gap.l),
              Text(t.question, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Palette.gold)),
            ],
            const SizedBox(height: Gap.m),
            TextField(
              controller: _answer,
              minLines: 3,
              maxLines: 8,
              decoration: InputDecoration(
                labelText: l.answerLabel,
                helperText: l.answerPrivate,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() => _saved = false),
            ),
            const SizedBox(height: Gap.s),
            FilledButton(
              onPressed: _answer.text.trim().isEmpty
                  ? null
                  : () async {
                      await c.saveAnswer(widget.day, _answer.text, open: t.isOpen);
                      if (mounted) setState(() => _saved = true);
                    },
              child: Text(_saved ? l.answerSaved : l.answerSave),
            ),
            const SizedBox(height: Gap.l),
            Text(l.thoughtLicense, style: const TextStyle(color: Palette.parchmentDim, fontSize: 11)),
          ],
        ),
      ),
    );
  }
}

// Ручной ввод шагов (V5-54): «Не совпадает с часами?» на вкладке «Путь» и правка дня в Журнале.
// Только в подписке; без неё — экран подписки. Засчитывается разница, показатели героя тратятся за путь.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/app_controller.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import 'paywall_screen.dart';

final _num = NumberFormat.decimalPattern('ru');

/// [day] — ключ дня (yyyy-MM-dd): сегодня или вчера.
Future<void> openManualSteps(BuildContext context, WidgetRef ref, String day) async {
  final c = ref.read(appProvider.notifier);
  if (!c.premium) {
    await openPaywall(context, ref, 'steps');
    return;
  }
  final before = c.rawStepsOn(day);
  final ok = await showDialog<bool>(context: context, builder: (_) => _ManualStepsDialog(day: day));
  if (ok == true && context.mounted) {
    final l = AppLocalizations.of(context);
    final added = c.rawStepsOn(day) - before;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.manualDone(_num.format(added)))));
  }
}

class _ManualStepsDialog extends ConsumerStatefulWidget {
  const _ManualStepsDialog({required this.day});
  final String day;

  @override
  ConsumerState<_ManualStepsDialog> createState() => _ManualStepsDialogState();
}

class _ManualStepsDialogState extends ConsumerState<_ManualStepsDialog> {
  final _ctl = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final n = int.tryParse(_ctl.text.replaceAll(RegExp(r'\D'), '')) ?? 0;
    setState(() => _busy = true);
    final err = await c.setManualSteps(widget.day, n);
    if (!mounted) return;
    if (err == null) {
      Navigator.of(context).pop(true);
      return;
    }
    setState(() {
      _busy = false;
      _error = switch (err) {
        'used' => l.manualErrUsed,
        'range' => l.manualErrRange(_num.format(AppController.manualStepsMax)),
        'not_more' => l.manualErrNotMore(_num.format(c.rawStepsOn(widget.day))),
        'day' => l.manualErrDay,
        _ => l.paywallTitle,
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final c = ref.read(appProvider.notifier);
    final isToday = widget.day == c.today;
    return AlertDialog(
      title: Text(isToday ? l.manualTitleToday : l.manualTitleYesterday),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l.manualBody(_num.format(c.rawStepsOn(widget.day)), _num.format(AppController.manualStepsMax)),
            style: const TextStyle(color: Palette.parchmentDim, height: 1.4),
          ),
          const SizedBox(height: Gap.m),
          TextField(
            controller: _ctl,
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(5)],
            decoration: InputDecoration(
              labelText: l.manualHint,
              errorText: _error,
              errorMaxLines: 3,
              border: const OutlineInputBorder(),
            ),
            onSubmitted: (_) => _busy ? null : _save(),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: Text(l.manualCancel)),
        FilledButton(onPressed: _busy ? null : _save, child: Text(l.manualSave)),
      ],
    );
  }
}

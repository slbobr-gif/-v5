// Дары духов (docs/v5/08 §13.4–13.5): кнопки guide / mirage / action, подписи статусов, голос подсказки.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/app_controller.dart';
import '../../engine/engine.dart';
import '../../engine/state.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';
import 'item_icon.dart';

/// Вид дара: guide | mirage | action | clew | null.
String? giftKind(World w, String id) {
  final ab = (w.items[id] as Map?)?['ability'];
  if (ab is Map) return ab['kind'] as String?;
  return null;
}

/// Предметы героя по порядку §13.5: снаряжение, затем инструменты и еда по алфавиту.
List<String> heldItemIds(HeroState hero) {
  final inv = hero.inv.entries.where((e) => e.value > 0).map((e) => e.key).toList()..sort();
  return <String>[...hero.gear, ...inv.where((k) => !hero.gear.contains(k))];
}

/// Подпись кнопки дара `giftAction_<id>`; неизвестный id — имя предмета.
String giftActionLabel(AppLocalizations l, String id, String fallback) => switch (id) {
      'venik_bannik' => l.giftAction_venik_bannik,
      'stone_bannik' => l.giftAction_stone_bannik,
      'hand_warmers' => l.giftAction_hand_warmers,
      'key_ovinnik' => l.giftAction_key_ovinnik,
      'sheaf_ovinnik' => l.giftAction_sheaf_ovinnik,
      'hook_vodyanoy' => l.giftAction_hook_vodyanoy,
      'twig_leshy' => l.giftAction_twig_leshy,
      'spruce_leshy' => l.giftAction_spruce_leshy,
      'bead_kikimora' => l.giftAction_bead_kikimora,
      'kudel_kikimora' => l.giftAction_kudel_kikimora,
      _ => fallback,
    };

/// «Спросить клубок / нитку / сучок…» — чей голос подскажет (`gearClewAsk_<id>`).
String clewAskLabel(AppLocalizations l, String? id) => switch (id) {
      'ball_yaga' => l.gearClewAsk_ball_yaga,
      'thread_yaga' => l.gearClewAsk_thread_yaga,
      'twig_leshy' => l.gearClewAsk_twig_leshy,
      'shell_vodyanoy' => l.gearClewAsk_shell_vodyanoy,
      'ember_domovoy' => l.gearClewAsk_ember_domovoy,
      'venik_bannik' => l.gearClewAsk_venik_bannik,
      _ => l.gearClewAsk,
    };

/// Текст статуса дара, когда кнопка недоступна. null — показывать нечего (нет предмета, не дар).
String? giftStatusText(AppLocalizations l, String status, int cooldownDays) => switch (status) {
      'no_charges' => l.giftStatus_no_charges,
      'cooldown' => l.giftStatus_cooldown(cooldownDays),
      'nothing' => l.giftStatus_nothing,
      'not_here' => l.giftStatus_not_here,
      _ => null,
    };

/// Строка дара: значок, имя, заряды, кнопка (если готов) или причина. [kinds] — какие виды показывать.
class GiftRow extends ConsumerWidget {
  const GiftRow({super.key, required this.item, this.hideNothing = false});

  final String item;

  /// На экране исхода нечего отменять — строку не показываем вовсе.
  final bool hideNothing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final m = ref.watch(appProvider);
    final content = m.content;
    final hero = m.hero;
    if (content == null || hero == null) return const SizedBox.shrink();
    final w = content.world;
    final eng = Engine(w, hero);
    final now = DateTime.now().millisecondsSinceEpoch;
    final status = eng.giftStatus(item, now);
    if (status == 'no_item' || status == 'bad_kind') return const SizedBox.shrink();
    if (hideNothing && status == 'nothing') return const SizedBox.shrink();
    final max = eng.maxUses(item);
    final left = eng.usesLeft(item);
    final reason = giftStatusText(l, status, eng.abilityCooldownDays(item, now));
    final label = giftActionLabel(l, item, content.itemName(item));
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.s + 4, vertical: Gap.s),
      decoration: cardDecoration(highlighted: status == 'ready'),
      child: Row(children: [
        ItemIcon(item, size: 40, type: w.itemType(item), dim: status == 'no_charges'),
        const SizedBox(width: Gap.s + 4),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(content.itemName(item), style: Theme.of(context).textTheme.titleSmall),
            if (max > 0)
              Text(left > 0 ? l.gearUsesLeft(left, max) : l.gearEmptyCharges,
                  style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
            if (status != 'ready' && reason != null)
              Text(reason, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12, height: 1.3)),
          ]),
        ),
        const SizedBox(width: Gap.s),
        // Кнопка — негибкий ребёнок Row: подпись-запаска (имя предмета) могла бы вытеснить колонку
        // Expanded и переполнить строку. Предел ширины — текст переносится внутри кнопки.
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 150),
          child: FilledButton.tonal(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
            onPressed: status == 'ready'
                ? () {
                    final r = ref.read(appProvider.notifier).useGift(item);
                    final text = r == 'ok' ? l.giftUsed : (giftStatusText(l, r, 0) ?? l.overflowError);
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
                  }
                : null,
            child: Text(label, textAlign: TextAlign.center),
          ),
        ),
      ]),
    );
  }
}

/// Все дары героя видов из [kinds] столбиком. Пусто — ничего не рисует.
class GiftList extends ConsumerWidget {
  const GiftList({super.key, required this.kinds, this.hideNothing = false, this.title});

  final Set<String> kinds;
  final bool hideNothing;
  final String? title;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final m = ref.watch(appProvider);
    final content = m.content;
    final hero = m.hero;
    if (content == null || hero == null) return const SizedBox.shrink();
    final w = content.world;
    final eng = Engine(w, hero);
    final now = DateTime.now().millisecondsSinceEpoch;
    final ids = heldItemIds(hero).where((id) {
      final k = giftKind(w, id);
      if (k == null || !kinds.contains(k)) return false;
      final st = eng.giftStatus(id, now);
      if (st == 'no_item' || st == 'bad_kind') return false;
      return !(hideNothing && st == 'nothing');
    }).toList();
    if (ids.isEmpty) return const SizedBox.shrink();
    final t = title;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (t != null) ...[
          Text(t, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.s),
        ],
        for (final id in ids)
          Padding(
            padding: const EdgeInsets.only(bottom: Gap.s),
            child: GiftRow(item: id, hideNothing: hideNothing),
          ),
      ],
    );
  }
}

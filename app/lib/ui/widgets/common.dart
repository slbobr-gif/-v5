import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme/tokens.dart';

/// Текст с курсивом: фрагменты между _подчёркиваниями_ — внутренний голос Сергея.
class StoryText extends StatelessWidget {
  const StoryText(this.text, {super.key, this.style, this.textAlign = TextAlign.start});

  final String text;
  final TextStyle? style;
  final TextAlign textAlign;

  @override
  Widget build(BuildContext context) {
    final base = style ?? Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.45);
    final spans = <TextSpan>[];
    final parts = text.split('_');
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].isEmpty) continue;
      final italic = i.isOdd;
      spans.add(TextSpan(
        text: parts[i],
        style: italic ? const TextStyle(fontStyle: FontStyle.italic, color: Palette.accent) : null,
      ));
    }
    return Text.rich(TextSpan(style: base, children: spans), textAlign: textAlign);
  }
}

/// SVG-иллюстрация из assets с запасным видом, если файла нет.
class Art extends StatelessWidget {
  const Art(this.path, {super.key, this.height, this.width, this.fit = BoxFit.cover});

  final String path;
  final double? height;
  final double? width;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      path,
      height: height,
      width: width,
      fit: fit,
      placeholderBuilder: (_) => Container(height: height, width: width, color: Palette.inkHigh),
    );
  }
}

/// Полоса показателя выживания с отметкой опасности.
class StatBar extends StatelessWidget {
  const StatBar({
    super.key,
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
    required this.danger,
  });

  final String label;
  final double value; // 0..100
  final Color color;
  final IconData icon;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final v = (value / 100).clamp(0.0, 1.0);
    return Semantics(
      label: '$label ${value.round()}',
      child: Row(
        children: [
          Icon(icon, size: 18, color: danger ? Palette.coralLine : color),
          const SizedBox(width: Gap.s),
          SizedBox(width: 64, child: Text(label, style: const TextStyle(fontSize: 13))),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: LinearProgressIndicator(
                value: v,
                minHeight: 9,
                color: danger ? Palette.coralLine : color,
                backgroundColor: Palette.inkHigh,
              ),
            ),
          ),
          const SizedBox(width: Gap.s),
          SizedBox(
            width: 30,
            child: Text('${value.round()}',
                textAlign: TextAlign.end,
                style: TextStyle(fontSize: 13, color: danger ? Palette.coralLine : null, fontWeight: FontWeight.w600)),
          ),
          SizedBox(
            width: 22,
            child: danger ? const Icon(Icons.warning_amber_rounded, size: 18, color: Palette.coralLine) : null,
          ),
        ],
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.child, this.highlighted = false, this.onTap, this.padding});

  final Widget child;
  final bool highlighted;
  final VoidCallback? onTap;
  final EdgeInsets? padding;

  @override
  Widget build(BuildContext context) {
    final box = Container(
      padding: padding ?? const EdgeInsets.all(Gap.m),
      decoration: cardDecoration(highlighted: highlighted),
      child: child,
    );
    if (onTap == null) return box;
    return InkWell(borderRadius: BorderRadius.circular(Gap.radius), onTap: onTap, child: box);
  }
}

// ---------------------------------------------------------------- v5.3: единый стиль разделов

/// Заголовок экрана в духе главной: маленькая строка сверху («Глава 1») и крупное название («Выход»).
class ScreenTitle extends StatelessWidget {
  const ScreenTitle({super.key, required this.title, this.kicker});

  final String title;
  final String? kicker;

  @override
  Widget build(BuildContext context) {
    final k = kicker;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (k != null && k.isNotEmpty)
          Text(k, style: const TextStyle(fontSize: 12, color: Palette.parchmentDim, height: 1.1)),
        Text(
          title,
          style: const TextStyle(fontSize: 20, color: Palette.parchment, height: 1.2),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}

/// Подзаголовок группы внутри экрана (настройки, журнал, герой).
class SectionHeader extends StatelessWidget {
  const SectionHeader(this.text, {super.key, this.padding = const EdgeInsets.fromLTRB(Gap.xs, Gap.m, Gap.xs, Gap.s)});

  final String text;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Text(
        text,
        style: const TextStyle(color: Palette.parchmentDim, fontSize: 12.5, fontWeight: FontWeight.w700, letterSpacing: 0.4),
      ),
    );
  }
}

/// Чип как «Город» на главной: цветной квадратик и подпись.
class SwatchChip extends StatelessWidget {
  const SwatchChip({super.key, required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(7, 2, 9, 2),
      decoration: BoxDecoration(
        color: Palette.chipBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Palette.chipLine),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 9,
            height: 9,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(2),
              border: Border.all(color: Palette.lead),
            ),
          ),
          const SizedBox(width: 6),
          // Flexible: в узкой колонке длинное название зоны переносится, а не переполняет чип.
          Flexible(child: Text(label, style: const TextStyle(color: Palette.parchment, fontSize: 12.5))),
        ],
      ),
    );
  }
}

/// Бирюзовая кнопка-чип как «Карта»: значок и подпись, зона нажатия не меньше 48 dp.
class AccentChipButton extends StatelessWidget {
  const AccentChipButton({super.key, required this.label, required this.onTap, this.icon, this.selected = false});

  final String label;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final ic = icon;
    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          // heightFactor: 1 — в строке/панели с ограниченной высотой Center не растягивается на неё целиком
          // (тот же класс ошибки, что у дока 0.5.4); minHeight 48 всё равно даёт зону нажатия.
          child: Center(
            widthFactor: 1,
            heightFactor: 1,
            child: Container(
              height: 34,
              padding: const EdgeInsets.fromLTRB(10, 0, 13, 0),
              decoration: BoxDecoration(
                color: Palette.accent.withAlpha(selected ? 40 : 20),
                borderRadius: BorderRadius.circular(17),
                border: Border.all(color: selected ? Palette.tabLine : Palette.chipLine),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (ic != null) ...[
                    Icon(ic, size: 16, color: Palette.accent),
                    const SizedBox(width: 6),
                  ],
                  // Кнопка стоит и в Row без ограничения ширины (лента «Пути»), поэтому не Flexible,
                  // а предел ширины: длинное имя линии в журнале обрезается многоточием, а не переполняет.
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 240),
                    child: Text(label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Palette.accent, fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Плашка-предупреждение (коралл): шаги не считаются, рюкзак полон и т. п.
class WarnBox extends StatelessWidget {
  const WarnBox({super.key, required this.text, this.onTap, this.icon = Icons.error_outline});

  final String text;
  final VoidCallback? onTap;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final box = Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.m, vertical: Gap.s + 4),
      decoration: BoxDecoration(
        color: const Color(0xFF231A24),
        borderRadius: BorderRadius.circular(Gap.radiusS),
        border: Border.all(color: Palette.coralLine),
      ),
      child: Row(children: [
        Icon(icon, color: Palette.coralLine),
        const SizedBox(width: Gap.s + 4),
        Expanded(child: Text(text, style: const TextStyle(fontWeight: FontWeight.w600, height: 1.3))),
        if (onTap != null) const Icon(Icons.chevron_right, color: Palette.coralLine),
      ]),
    );
    if (onTap == null) return box;
    return InkWell(borderRadius: BorderRadius.circular(Gap.radiusS), onTap: onTap, child: box);
  }
}

/// Полоса прогресса в стиле главной (бирюза на тёмном, скруглённая).
class AccentProgress extends StatelessWidget {
  const AccentProgress({super.key, required this.value, this.height = 8, this.color = Palette.accent});

  final double value;
  final double height;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(height / 2),
      child: LinearProgressIndicator(
        value: value.clamp(0.0, 1.0),
        minHeight: height,
        color: color,
        backgroundColor: Palette.inkHigh,
      ),
    );
  }
}

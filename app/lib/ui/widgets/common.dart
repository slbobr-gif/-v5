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
        style: italic ? const TextStyle(fontStyle: FontStyle.italic, color: Palette.gold) : null,
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
          Icon(icon, size: 18, color: danger ? Palette.danger : color),
          const SizedBox(width: Gap.s),
          SizedBox(width: 64, child: Text(label, style: const TextStyle(fontSize: 13))),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: LinearProgressIndicator(
                value: v,
                minHeight: 9,
                color: danger ? Palette.danger : color,
                backgroundColor: Palette.inkHigh,
              ),
            ),
          ),
          const SizedBox(width: Gap.s),
          SizedBox(
            width: 30,
            child: Text('${value.round()}', textAlign: TextAlign.end, style: const TextStyle(fontSize: 13)),
          ),
          SizedBox(
            width: 22,
            child: danger ? const Icon(Icons.warning_amber_rounded, size: 18, color: Palette.danger) : null,
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

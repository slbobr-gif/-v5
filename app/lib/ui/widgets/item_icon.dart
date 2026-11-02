// Иконки предметов и зон, картинки с запасными вариантами, строки перков.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';

/// Список файлов в assets: по нему выбираем первую картинку, которая точно есть.
class AssetIndex {
  static Future<Set<String>>? _future;
  static Set<String>? cached;

  static Future<Set<String>> load() => _future ??= _read();

  static Future<Set<String>> _read() async {
    Set<String> found;
    try {
      final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
      found = manifest.listAssets().toSet();
    } catch (_) {
      found = <String>{};
    }
    cached = found;
    return found;
  }

  /// Первый путь из [paths], который есть в assets. Пустой список файлов (не прочитали) — первый путь.
  static String? pick(Set<String> have, List<String> paths) {
    if (paths.isEmpty) return null;
    if (have.isEmpty) return paths.first;
    for (final p in paths) {
      if (have.contains(p)) return p;
    }
    return null;
  }
}

/// SVG из первого существующего файла списка; если нет ни одного — [fallback].
class FallbackArt extends StatelessWidget {
  const FallbackArt({
    super.key,
    required this.candidates,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
    this.fallback,
  });

  final List<String> candidates;
  final double? width;
  final double? height;
  final BoxFit fit;
  final Widget? fallback;

  Widget _empty() => fallback ?? Container(width: width, height: height, color: Palette.inkHigh);

  Widget _build(Set<String> have) {
    final path = AssetIndex.pick(have, candidates);
    if (path == null) return _empty();
    return SvgPicture.asset(
      path,
      width: width,
      height: height,
      fit: fit,
      placeholderBuilder: (_) => _empty(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final have = AssetIndex.cached;
    if (have != null) return _build(have);
    return FutureBuilder<Set<String>>(
      future: AssetIndex.load(),
      builder: (BuildContext ctx, AsyncSnapshot<Set<String>> snap) {
        final data = snap.data;
        if (data == null) return SizedBox(width: width, height: height);
        return _build(data);
      },
    );
  }
}

IconData _typeIcon(String type) => switch (type) {
      'food' => Icons.restaurant,
      'drink' => Icons.local_drink_outlined,
      'gear' => Icons.backpack_outlined,
      'refill' => Icons.propane_tank_outlined,
      _ => Icons.category_outlined,
    };

/// Значок предмета `assets/art/items/<id>.svg` (кабошон уже в файле). Нет файла — круглый значок по типу.
class ItemIcon extends StatelessWidget {
  const ItemIcon(this.id, {super.key, this.size = 40, this.type = 'tool', this.hot = false, this.dim = false});

  final String id;
  final double size;
  final String type;

  /// Горелка включена, а предмет нагреваемый — маленький огонёк в углу.
  final bool hot;

  /// Пустая горелка/аптечка — значок приглушён.
  final bool dim;

  @override
  Widget build(BuildContext context) {
    final fallback = Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(shape: BoxShape.circle, color: Palette.inkHigh),
      child: Icon(_typeIcon(type), size: size * 0.5, color: Palette.parchmentDim),
    );
    Widget icon = FallbackArt(
      candidates: ['assets/art/items/$id.svg'],
      width: size,
      height: size,
      fit: BoxFit.contain,
      fallback: fallback,
    );
    if (dim) icon = Opacity(opacity: 0.45, child: icon);
    if (!hot) return ExcludeSemantics(child: SizedBox(width: size, height: size, child: icon));
    return ExcludeSemantics(
      child: SizedBox(
        width: size,
        height: size,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Positioned.fill(child: icon),
            Positioned(
              right: -2,
              top: -2,
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Palette.ink,
                  border: Border.all(color: Palette.warmth),
                ),
                child: const Icon(Icons.local_fire_department, size: 12, color: Palette.warmth),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Пустая ячейка: пунктирная рамка (для находок в пути).
class EmptySlot extends StatelessWidget {
  const EmptySlot({super.key, this.size = 40, this.label});

  final double size;
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: CustomPaint(
        painter: _DashedCirclePainter(),
        child: SizedBox(width: size, height: size),
      ),
    );
  }
}

class _DashedCirclePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Palette.parchmentDim.withAlpha(140)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4;
    final r = Rect.fromLTWH(1, 1, size.width - 2, size.height - 2);
    const n = 16;
    const step = 6.283185307179586 / n;
    for (var i = 0; i < n; i++) {
      canvas.drawArc(r, i * step, step * 0.55, false, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Значок зоны `assets/art/zones/<zone>.svg` и подпись: Город / Пригород / Окрестности.
String zoneName(AppLocalizations l, String zone) => switch (zone) {
      'city' => l.zoneCity,
      'suburb' => l.zoneSuburb,
      _ => l.zoneWild,
    };

class ZoneLabel extends StatelessWidget {
  const ZoneLabel({super.key, required this.zone, this.size = 22});

  final String zone;
  final double size;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        FallbackArt(
          candidates: ['assets/art/zones/$zone.svg'],
          width: size,
          height: size,
          fit: BoxFit.contain,
          fallback: Icon(Icons.terrain_outlined, size: size, color: Palette.accent),
        ),
        const SizedBox(width: Gap.s),
        Text(zoneName(l, zone), style: const TextStyle(color: Palette.accent, fontSize: 13, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

/// Текст одного перка (docs/v5/08 §6). Неизвестный ключ — пустая строка.
String perkText(AppLocalizations l, ItemPerk p, {String item = ''}) {
  final v = p.value;
  switch (p.key) {
    case 'ability_guide':
      return l.gearPerkAbility_guide(v);
    case 'ability_mirage':
      return l.gearPerkAbility_mirage(v);
    case 'ability_action':
      return v > 0 ? l.gearPerkAbility_action(v) : '';
    case 'actionWarmth':
      return l.gearPerkActionWarmth(v);
    case 'actionWarmthMax':
      return l.gearPerkActionWarmthMax;
    case 'actionGive_fish':
      return l.gearPerkActionGive_fish(v);
    case 'hint':
      return switch (item) {
        'twig_leshy' => l.gearPerkHint_twig_leshy(v),
        'shell_vodyanoy' => l.gearPerkHint_shell_vodyanoy(v),
        'ember_domovoy' => l.gearPerkHint_ember_domovoy(v),
        'venik_bannik' => l.gearPerkHint_venik_bannik(v),
        _ => '',
      };
    case 'campWarmth':
      return l.gearPerkCampWarmth(v);
    case 'campWaterAtWater':
      return l.gearPerkCampWaterAtWater(v);
    case 'waterDrainAtMiddayHeat':
      return l.gearPerkWaterDrainAtMiddayHeat(v);
    case 'riskAtWater':
      return l.gearPerkRiskAtWater(v);
    case 'noCoinLossAtWater':
      return l.gearPerkNoCoinLossAtWater;
    case 'boostFishSatiety':
      return l.gearPerkBoostFishSatiety(v);
    case 'upkeep':
      return l.gearPerkUpkeep;
    case 'expires':
      return l.gearPerkExpires(v);
    case 'sell':
      return l.gearPerkSell(v);
    case 'rescueWarmth':
      return l.gearPerkRescueWarmth(v);
    case 'satiety':
      return l.gearPerkSatiety(v);
    case 'water':
      return l.gearPerkWater(v);
    case 'warmth':
      return l.gearPerkWarmth(v);
    case 'heat':
      return l.gearPerkHeat(v);
    case 'warmthDrain':
      return l.gearPerkWarmthDrain(v);
    case 'weatherCold':
      return l.gearPerkWeatherCold(v);
    case 'satietyDrain':
      return l.gearPerkSatietyDrain(v);
    case 'waterDrain':
      return l.gearPerkWaterDrain(v);
    case 'idleWarmth':
      return l.gearPerkIdleWarmth(v);
    case 'delay':
      return l.gearPerkDelay(v);
    case 'detour':
      return l.gearPerkDetour(v);
    case 'risk':
      return l.gearPerkRisk(v);
    case 'rescue':
      return l.gearPerkRescue(v);
    case 'stove':
      return l.gearPerkStove;
    case 'refill':
      return l.gearPerkRefill(v);
    case 'refillMax':
      return l.gearPerkRefillMax(v);
    case 'uses':
      return l.gearPerkUses(v);
    case 'portions':
      return l.gearPerkPortions(v);
    case 'ability_clew':
      return l.gearPerkAbility_clew(v);
  }
  return '';
}

/// Условный перк (§13.3): ключ с суффиксом `At<Условие>` — действует только у воды, в полдень, в зной.
bool isConditionalPerk(String key) => RegExp(r'At[A-Z]').hasMatch(key);

/// Перки предмета одной строкой через запятую; [skip] — ключи, которые экран показывает отдельно;
/// [noConditional] — условные перки показываются бейджами отдельно.
String perksLine(AppLocalizations l, World w, String id, {Set<String> skip = const {}, bool noConditional = false}) {
  final parts = <String>[];
  for (final p in w.itemPerks(id)) {
    if (skip.contains(p.key)) continue;
    if (noConditional && isConditionalPerk(p.key)) continue;
    final t = perkText(l, p, item: id);
    if (t.isNotEmpty) parts.add(t);
  }
  return parts.join(', ');
}

/// Бейдж перка (условного, срока, «не накормлен»): контурная плашка.
class PerkBadge extends StatelessWidget {
  const PerkBadge({super.key, required this.text, this.color = Palette.accent, this.icon});

  final String text;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final ic = icon;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.s, vertical: 2),
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: color)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (ic != null) ...[
          Icon(ic, size: 13, color: color),
          const SizedBox(width: 4),
        ],
        Flexible(child: Text(text, style: TextStyle(color: color, fontSize: 11.5))),
      ]),
    );
  }
}

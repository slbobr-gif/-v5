// Общее для экранов конца главы и финала: форматирование чисел и дат, двусторонняя медаль,
// плитки достижений, окно «Поделиться» (карточка-картинка + системное меню).

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/share.dart';
import '../../engine/journey_stats.dart';
import '../../engine/world.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tokens.dart';

// ---------------------------------------------------------------- форматирование

/// 49046 → «49 046» (неразрывный пробел между разрядами).
String groupInt(int n) {
  final s = n.abs().toString();
  final b = StringBuffer(n < 0 ? '-' : '');
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(' ');
    b.write(s[i]);
  }
  return b.toString();
}

/// Километры: 183.9 → «184», с [digits] знаками после запятой — «36,8».
String fmtKm(double km, {int digits = 0}) {
  if (digits == 0) return groupInt(km.round());
  final p = math.pow(10, digits);
  final v = (km * p).round() / p;
  final whole = v.truncate();
  final frac = ((v - whole).abs() * p).round().toString().padLeft(digits, '0');
  return '${groupInt(whole)},$frac';
}

/// «2026-05-05» → «5 мая».
String fmtDay(AppLocalizations l, String? key) {
  if (key == null) return '';
  final p = key.split('-');
  if (p.length != 3) return key;
  final months = l.monthsGen.split('|');
  final m = (int.tryParse(p[1]) ?? 1).clamp(1, 12);
  return '${int.tryParse(p[2]) ?? 1} ${months.length == 12 ? months[m - 1] : p[1]}';
}

// ---------------------------------------------------------------- данные медали

/// Всё, что показывает медаль и её плитки. Строится из итога пути или из снимка в профиле.
class MedalData {
  const MedalData({
    required this.days,
    required this.steps,
    required this.distKm,
    required this.bestSteps,
    required this.events,
    required this.deaths,
    required this.questsDone,
    required this.questsTotal,
    required this.totalKm,
    required this.startDay,
    required this.endDay,
  });

  factory MedalData.fromStats(JourneyStats s) => MedalData(
        days: s.days,
        steps: s.steps,
        distKm: s.distKm,
        bestSteps: s.bestSteps,
        events: s.events,
        deaths: s.deaths,
        questsDone: s.questsDone,
        questsTotal: s.questsTotal,
        totalKm: s.totalKm,
        startDay: s.startDay,
        endDay: s.endDay,
      );

  factory MedalData.fromJson(Json j) => MedalData(
        days: toI(j['days']),
        steps: toI(j['steps']),
        distKm: toD(j['distKm']),
        bestSteps: toI(j['bestSteps']),
        events: toI(j['events']),
        deaths: toI(j['deaths']),
        questsDone: toI(j['questsDone']),
        questsTotal: toI(j['questsTotal']),
        totalKm: j['totalKm'] == null ? 2099 : toD(j['totalKm']),
        startDay: '${j['startDay'] ?? ''}',
        endDay: '${j['endDay'] ?? ''}',
      );

  final int days;
  final int steps;
  final double distKm;
  final int bestSteps;
  final int events;
  final int deaths;
  final int questsDone;
  final int questsTotal;
  final double totalKm;
  final String startDay;
  final String endDay;
}

// ---------------------------------------------------------------- медаль

const _medalFront = 'assets/art/finale/medal_front.webp';
const _medalBack = 'assets/art/finale/medal_back.webp';
const _medalRibbon = 'assets/art/finale/medal_ribbon.webp';
const _engrave = Color(0xFF4A3408);
const _engraveDim = Color(0xFF6E4E12);

/// Лицевая сторона медали без ленты (для главной и окна «Путь пройден»).
class MedalFace extends StatelessWidget {
  const MedalFace({super.key, required this.size});

  final double size;

  @override
  Widget build(BuildContext context) =>
      Image.asset(_medalFront, width: size, height: size, fit: BoxFit.contain, filterQuality: FilterQuality.medium);
}

/// Двусторонняя медаль с лентой: нажатие переворачивает. Обратная сторона — расстояние, шаги, дни игрока.
class MedalView extends StatefulWidget {
  const MedalView({super.key, required this.data, this.size = 190, this.ribbon = true});

  final MedalData data;
  final double size;
  final bool ribbon;

  @override
  State<MedalView> createState() => _MedalViewState();
}

class _MedalViewState extends State<MedalView> {
  bool _back = false;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final s = widget.size;
    final side = _back ? _backSide(l, s) : MedalFace(key: const ValueKey('front'), size: s);
    return Semantics(
      button: true,
      label: _back ? l.medalBack : l.medalFront,
      child: GestureDetector(
        onTap: () => setState(() => _back = !_back),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.ribbon)
              Image.asset(_medalRibbon, width: s * 0.42, height: s * 0.32, fit: BoxFit.fill),
            Transform.translate(
              offset: Offset(0, widget.ribbon ? -s * 0.1 : 0),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 420),
                transitionBuilder: (child, anim) => AnimatedBuilder(
                  animation: anim,
                  child: child,
                  builder: (context, child) {
                    // поворот вокруг вертикальной оси: уходящая сторона сжимается, новая раскрывается
                    final t = anim.value;
                    final k = t < 0.5 ? 0.0 : (t - 0.5) * 2;
                    return Transform(
                      alignment: Alignment.center,
                      transform: Matrix4.identity()
                        ..setEntry(3, 2, 0.001)
                        ..rotateY((1 - k) * math.pi / 2),
                      child: Opacity(opacity: t < 0.5 ? 0 : 1, child: child),
                    );
                  },
                ),
                child: side,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _backSide(AppLocalizations l, double s) {
    final d = widget.data;
    Widget line(String value, String label) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(value,
                style: TextStyle(
                    fontFamily: 'serif', fontSize: s * 0.085, fontWeight: FontWeight.w700, color: _engrave, height: 1.05)),
            Text(label.toUpperCase(),
                style: TextStyle(fontSize: s * 0.038, letterSpacing: 1.2, color: _engraveDim, height: 1.1)),
          ],
        );
    return SizedBox(
      key: const ValueKey('back'),
      width: s,
      height: s,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Image.asset(_medalBack, width: s, height: s, fit: BoxFit.contain),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              line(l.statKm(fmtKm(d.distKm)), l.medalBackDist),
              SizedBox(height: s * 0.02),
              line(groupInt(d.steps), l.medalBackSteps),
              SizedBox(height: s * 0.02),
              line(l.statDays(d.days), l.medalBackDays),
            ],
          ),
        ],
      ),
    );
  }
}

/// Плитки достижений под медалью (2 колонки).
class AchievementsGrid extends StatelessWidget {
  const AchievementsGrid({super.key, required this.data});

  final MedalData data;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final d = data;
    final items = <(IconData, String, String)>[
      (Icons.directions_walk, l.statKm(fmtKm(d.totalKm)), l.achRoute),
      (Icons.calendar_today_outlined, l.statDays(d.days), '${fmtDay(l, d.startDay)} – ${fmtDay(l, d.endDay)}'),
      (Icons.directions_run, groupInt(d.steps), l.achSteps),
      (Icons.straighten, l.statKm(fmtKm(d.distKm)), l.achDistance),
      (Icons.emoji_events_outlined, groupInt(d.bestSteps), l.achRecord),
      (Icons.handshake_outlined, '${d.events}', l.achEncounters),
      (Icons.auto_stories_outlined, l.achStoriesValue(d.questsDone, d.questsTotal), l.achStories),
      (Icons.fitness_center, '${d.deaths}', l.achFalls(d.deaths)),
    ];
    return LayoutBuilder(builder: (context, c) {
      final w = (c.maxWidth - Gap.s) / 2;
      return Wrap(
        spacing: Gap.s,
        runSpacing: Gap.s,
        children: [
          for (final (icon, value, label) in items)
            SizedBox(
              width: w,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: cardDecoration(radius: Gap.radiusS),
                child: Row(
                  children: [
                    Icon(icon, size: 20, color: Palette.accent),
                    const SizedBox(width: Gap.s),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                          Text(label, style: const TextStyle(fontSize: 11.5, color: Palette.parchmentDim, height: 1.2)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      );
    });
  }
}

// ---------------------------------------------------------------- поделиться

/// Показывает карточку поверх экрана и сразу открывает системное «Поделиться» (картинка + текст со ссылкой).
Future<void> shareCardDialog(BuildContext context, {required Widget card, required String text, required String kind}) {
  final key = GlobalKey();
  var started = false; // диалог может перестроиться — «Поделиться» открываем один раз
  return showDialog<void>(
    context: context,
    barrierColor: const Color(0xB3040710),
    builder: (ctx) {
      if (!started) {
        started = true;
        WidgetsBinding.instance.addPostFrameCallback((_) async {
          await Future<void>.delayed(const Duration(milliseconds: 250));
          final ok = await shareCard(key, text: text, kind: kind);
          if (ctx.mounted) Navigator.of(ctx).pop();
          if (!ok && context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context).shareFailed)));
          }
        });
      }
      return Center(
        child: Material(
          type: MaterialType.transparency,
          child: RepaintBoundary(key: key, child: card),
        ),
      );
    },
  );
}

/// Текст сообщения при отправке: ссылка на приложение, если она уже задана.
String shareLink() => kAppLink;

/// Шапка карточки для соцсетей: «ПУТНИК» и подпись справа.
class ShareCardFrame extends StatelessWidget {
  const ShareCardFrame({super.key, required this.right, required this.child, this.width = 320});

  final String right;
  final Widget child;
  final double width;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      width: width,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: Palette.tabLine),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF173B45), Palette.ink, Color(0xFF1A1530)],
          stops: [0, 0.55, 1],
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(l.shareCardBrand,
                  style: const TextStyle(color: Palette.accent, fontWeight: FontWeight.w700, letterSpacing: 3, fontSize: 12)),
              const Spacer(),
              Text(right, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
            ],
          ),
          child,
          const SizedBox(height: Gap.s),
          Container(height: 1, color: Palette.chipLine),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(child: Text(l.shareCardSlogan, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12))),
              const Icon(Icons.play_arrow, size: 14, color: Palette.accent),
              Text(l.shareCardDownload, style: const TextStyle(color: Palette.accent, fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }
}

/// Число с подписью снизу (полоса цифр, карточки).
class StatFigure extends StatelessWidget {
  const StatFigure({super.key, required this.value, required this.label, this.size = 17, this.center = false});

  final String value;
  final String label;
  final double size;
  final bool center;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: center ? CrossAxisAlignment.center : CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value, style: TextStyle(fontWeight: FontWeight.w700, fontSize: size)),
          Text(label, style: const TextStyle(color: Palette.parchmentDim, fontSize: 12)),
        ],
      );
}

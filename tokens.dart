import 'package:flutter/material.dart';

/// Дизайн-токены «атласной» темы (совпадают с docs/v5/04-art-style.md, раздел «Интерфейс v5.3»).
/// Акцент — бирюза; жёлтого и золотого в интерфейсе нет (заказ v5.3, п. 5).
class Palette {
  static const ink = Color(0xFF0E1621);
  static const inkRaised = Color(0xFF16222F);
  static const inkHigh = Color(0xFF1F3043);
  static const parchment = Color(0xFFE9DFC8);
  static const parchmentDim = Color(0xFF9BA7B4);

  /// Яркая бирюза для текста и значков на тёмном фоне (контраст с ink ≈ 10:1, с inkRaised ≈ 9:1).
  static const accent = Color(0xFF3FD6CC);

  /// Глубокая бирюза для линий, рамок и заливок (на тёмном фоне ≈ 5:1).
  static const accentDeep = Color(0xFF1F9C95);

  /// Устар.: теперь бирюза. Поле оставлено, чтобы не править экраны других потоков.
  static const gold = accent;
  static const teal = Color(0xFF4FA3A5);

  /// Мягкий коралловый для предупреждений (раньше был янтарным).
  static const ember = Color(0xFFF0957A);
  static const danger = Color(0xFFFF5A5A);
  static const sea = Color(0xFF0B2A3A);
  static const land = Color(0xFF16222F);

  // Три показателя различаются цветом и значком: сытость — коралл, вода — голубой, тепло — красно-розовый.
  static const satiety = Color(0xFFE5855D);
  static const water = Color(0xFF5BB5E8);
  static const warmth = Color(0xFFE85A74);

  // ---- v5.3: главный экран «Витражная лента» и единый стиль разделов
  /// Свинцовый контур витража.
  static const lead = Color(0xFF070B10);

  /// Фон и рамка чипов («Город», «Карта»).
  static const chipBg = Color(0xFF10202E);
  static const chipLine = Color(0xFF2C4560);

  /// Рамка активной вкладки нижнего бара.
  static const tabLine = Color(0xFF2C6B73);

  /// Коралловая линия опасности (порог 25, рамка сосуда, «мёрзнет»).
  static const coralLine = Color(0xFFFF6B7A);

  /// Цвета зон пути (легенда, чип зоны): Город / Пригород / Окрестности.
  static const zoneCity = Color(0xFF2B3E9E);
  static const zoneSuburb = Color(0xFF1F9E6B);
  static const zoneWild = Color(0xFF5B3FA0);

  static Color zone(String z) => switch (z) {
        'city' => zoneCity,
        'suburb' => zoneSuburb,
        _ => zoneWild,
      };
}

class Gap {
  static const xs = 4.0;
  static const s = 8.0;
  static const m = 16.0;
  static const l = 24.0;
  static const xl = 32.0;
  static const radius = 16.0;

  /// Малые карточки (темп, показатели в списках).
  static const radiusS = 14.0;

  /// Нижний бар-док.
  static const radiusDock = 18.0;
}

ThemeData buildTheme() {
  const scheme = ColorScheme.dark(
    primary: Palette.accent,
    onPrimary: Palette.ink,
    primaryContainer: Palette.inkHigh,
    onPrimaryContainer: Palette.accent,
    secondary: Palette.teal,
    onSecondary: Palette.ink,
    secondaryContainer: Palette.inkHigh,
    onSecondaryContainer: Palette.parchment,
    tertiary: Palette.accent,
    onTertiary: Palette.ink,
    surface: Palette.ink,
    onSurface: Palette.parchment,
    onSurfaceVariant: Palette.parchmentDim,
    surfaceContainerLowest: Palette.ink,
    surfaceContainerLow: Palette.inkRaised,
    surfaceContainer: Palette.inkRaised,
    surfaceContainerHigh: Palette.inkRaised,
    surfaceContainerHighest: Palette.inkHigh,
    outline: Palette.chipLine,
    outlineVariant: Palette.inkHigh,
    surfaceTint: Colors.transparent,
    error: Palette.danger,
    onError: Palette.ink,
  );
  final cardShape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(Gap.radius),
    side: const BorderSide(color: Palette.inkHigh),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: Palette.ink,
    canvasColor: Palette.ink,
    dividerColor: Palette.inkHigh,
    splashFactory: InkRipple.splashFactory,
    appBarTheme: const AppBarThemeData(
      backgroundColor: Palette.ink,
      foregroundColor: Palette.parchment,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
      titleSpacing: Gap.m,
      toolbarHeight: 60,
      iconTheme: IconThemeData(color: Palette.parchmentDim),
      actionsIconTheme: IconThemeData(color: Palette.parchmentDim),
      titleTextStyle: TextStyle(color: Palette.parchment, fontSize: 20, fontWeight: FontWeight.w400),
    ),
    navigationBarTheme: const NavigationBarThemeData(backgroundColor: Palette.inkRaised, indicatorColor: Palette.inkHigh),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        backgroundColor: Palette.accent,
        foregroundColor: Palette.ink,
        disabledBackgroundColor: Palette.inkHigh,
        disabledForegroundColor: Palette.parchmentDim,
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Gap.radius)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        foregroundColor: Palette.parchment,
        side: const BorderSide(color: Palette.chipLine),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Gap.radius)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: Palette.accent,
        minimumSize: const Size(48, 44),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Gap.radiusS)),
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(foregroundColor: Palette.parchmentDim, minimumSize: const Size(48, 48)),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Palette.inkRaised,
      surfaceTintColor: Colors.transparent,
      shape: cardShape,
      titleTextStyle: const TextStyle(color: Palette.parchment, fontSize: 19, fontWeight: FontWeight.w600),
      contentTextStyle: const TextStyle(color: Palette.parchment, fontSize: 15, height: 1.4),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Palette.inkRaised,
      surfaceTintColor: Colors.transparent,
      modalBackgroundColor: Palette.inkRaised,
      dragHandleColor: Palette.chipLine,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(Gap.radiusDock)),
        side: BorderSide(color: Palette.inkHigh),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Palette.inkHigh,
      contentTextStyle: const TextStyle(color: Palette.parchment, fontSize: 14, height: 1.35),
      actionTextColor: Palette.accent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Gap.radiusS),
        side: const BorderSide(color: Palette.chipLine),
      ),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
        if (s.contains(WidgetState.disabled)) return Palette.inkHigh;
        if (s.contains(WidgetState.selected)) return Palette.ink;
        return Palette.parchmentDim;
      }),
      trackColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
        if (s.contains(WidgetState.disabled)) return Palette.inkRaised;
        if (s.contains(WidgetState.selected)) return Palette.accent;
        return Palette.inkHigh;
      }),
      trackOutlineColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
        if (s.contains(WidgetState.selected)) return Palette.accent;
        return Palette.chipLine;
      }),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
        if (s.contains(WidgetState.selected)) return Palette.accent;
        return Colors.transparent;
      }),
      checkColor: WidgetStateProperty.all<Color>(Palette.ink),
      side: const BorderSide(color: Palette.parchmentDim, width: 1.6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
    ),
    radioTheme: RadioThemeData(
      fillColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
        if (s.contains(WidgetState.selected)) return Palette.accent;
        return Palette.parchmentDim;
      }),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Palette.accent,
      linearTrackColor: Palette.inkHigh,
      circularTrackColor: Colors.transparent,
      linearMinHeight: 8,
    ),
    sliderTheme: const SliderThemeData(
      activeTrackColor: Palette.accent,
      inactiveTrackColor: Palette.inkHigh,
      thumbColor: Palette.accent,
    ),
    listTileTheme: const ListTileThemeData(
      iconColor: Palette.accent,
      textColor: Palette.parchment,
      subtitleTextStyle: TextStyle(color: Palette.parchmentDim, fontSize: 13, height: 1.3),
      titleTextStyle: TextStyle(color: Palette.parchment, fontSize: 15),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Palette.chipBg,
      selectedColor: Palette.chipBg,
      disabledColor: Palette.inkRaised,
      side: const BorderSide(color: Palette.chipLine),
      labelStyle: const TextStyle(color: Palette.parchment, fontSize: 12.5),
      secondaryLabelStyle: const TextStyle(color: Palette.accent, fontSize: 12.5),
      iconTheme: const IconThemeData(color: Palette.accent, size: 16),
      shape: const StadiumBorder(side: BorderSide(color: Palette.chipLine)),
      padding: const EdgeInsets.symmetric(horizontal: 6),
      elevation: 0,
      pressElevation: 0,
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
          if (s.contains(WidgetState.selected)) return Palette.accent.withAlpha(36);
          return Palette.inkRaised;
        }),
        foregroundColor: WidgetStateProperty.resolveWith<Color?>((Set<WidgetState> s) {
          if (s.contains(WidgetState.selected)) return Palette.accent;
          return Palette.parchmentDim;
        }),
        side: WidgetStateProperty.resolveWith<BorderSide?>((Set<WidgetState> s) {
          if (s.contains(WidgetState.selected)) return const BorderSide(color: Palette.tabLine);
          return const BorderSide(color: Palette.inkHigh);
        }),
      ),
    ),
    tabBarTheme: const TabBarThemeData(
      labelColor: Palette.accent,
      unselectedLabelColor: Palette.parchmentDim,
      indicatorColor: Palette.accent,
      indicatorSize: TabBarIndicatorSize.label,
      dividerColor: Palette.inkHigh,
      labelStyle: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
      unselectedLabelStyle: TextStyle(fontSize: 14),
    ),
    dividerTheme: const DividerThemeData(color: Palette.inkHigh, thickness: 1, space: Gap.m),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: Palette.chipBg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Palette.chipLine),
      ),
      textStyle: const TextStyle(color: Palette.parchment, fontSize: 12),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: Palette.inkRaised,
      surfaceTintColor: Colors.transparent,
      shape: cardShape,
    ),
    timePickerTheme: TimePickerThemeData(
      backgroundColor: Palette.inkRaised,
      dialBackgroundColor: Palette.inkHigh,
      dialHandColor: Palette.accent,
      hourMinuteColor: Palette.inkHigh,
      hourMinuteTextColor: Palette.parchment,
      dayPeriodColor: Palette.inkHigh,
      entryModeIconColor: Palette.accent,
      shape: cardShape,
    ),
  );
}

BoxDecoration cardDecoration({bool highlighted = false, Color? color, double radius = Gap.radius}) => BoxDecoration(
      color: color ?? Palette.inkRaised,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: highlighted ? Palette.accent : Palette.inkHigh),
    );

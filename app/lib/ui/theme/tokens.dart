import 'package:flutter/material.dart';

/// Дизайн-токены «атласной» темы (совпадают с docs/v5/04-art-style.md).
class Palette {
  static const ink = Color(0xFF0E1621);
  static const inkRaised = Color(0xFF16222F);
  static const inkHigh = Color(0xFF1F3043);
  static const parchment = Color(0xFFE9DFC8);
  static const parchmentDim = Color(0xFF9BA7B4);
  static const gold = Color(0xFFD9B35B);
  static const teal = Color(0xFF4FA3A5);
  static const ember = Color(0xFFE8A15A);
  static const danger = Color(0xFFD96B5B);
  static const sea = Color(0xFF0B2A3A);
  static const land = Color(0xFF16222F);
  static const satiety = Color(0xFFE8A15A);
  static const water = Color(0xFF4FA3A5);
  static const warmth = Color(0xFFD96B5B);
}

class Gap {
  static const xs = 4.0;
  static const s = 8.0;
  static const m = 16.0;
  static const l = 24.0;
  static const xl = 32.0;
  static const radius = 16.0;
}

ThemeData buildTheme() {
  const scheme = ColorScheme.dark(
    primary: Palette.gold,
    onPrimary: Palette.ink,
    secondary: Palette.teal,
    onSecondary: Palette.ink,
    surface: Palette.ink,
    onSurface: Palette.parchment,
    error: Palette.danger,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: Palette.ink,
    appBarTheme: const AppBarTheme(backgroundColor: Palette.ink, foregroundColor: Palette.parchment, elevation: 0),
    navigationBarTheme: const NavigationBarThemeData(backgroundColor: Palette.inkRaised, indicatorColor: Palette.inkHigh),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Gap.radius)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        foregroundColor: Palette.parchment,
        side: const BorderSide(color: Palette.inkHigh),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Gap.radius)),
      ),
    ),
  );
}

BoxDecoration cardDecoration({bool highlighted = false, Color? color}) => BoxDecoration(
      color: color ?? Palette.inkRaised,
      borderRadius: BorderRadius.circular(Gap.radius),
      border: Border.all(color: highlighted ? Palette.gold : Palette.inkHigh),
    );

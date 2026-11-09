// «Поделиться» карточкой: снимок виджета (RepaintBoundary) в PNG и системное меню «Поделиться».
// Ссылка на приложение идёт в тексте сообщения (kAppLink).

import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';
import 'package:share_plus/share_plus.dart';

import '../analytics/analytics.dart';

/// Ссылка на приложение в магазине. ЗАГЛУШКА (решение владельца 09.11.2026): главная Google, пока магазин
/// не выбран. Заменить на ссылку RuStore/Google Play перед публичной сборкой — см. docs/00-decisions.md, V5-48.
const kAppLink = 'https://www.google.com/';

/// Снимает виджет под [key] (RepaintBoundary) и открывает системное «Поделиться».
/// false — не получилось (виджет не нарисован, нет приложения для отправки и т. п.).
Future<bool> shareCard(GlobalKey key, {required String text, required String kind}) async {
  try {
    final ctx = key.currentContext;
    final ro = ctx?.findRenderObject();
    if (ro is! RenderRepaintBoundary) return false;
    final image = await ro.toImage(pixelRatio: 3);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    if (data == null) return false;
    final bytes = data.buffer.asUint8List();
    Analytics.instance.event('share', {'kind': kind});
    await Share.shareXFiles(
      [XFile.fromData(bytes, mimeType: 'image/png', name: 'putnik_$kind.png')],
      text: text.trim(),
    );
    return true;
  } catch (_) {
    return false;
  }
}

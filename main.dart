import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app_controller.dart';
import 'l10n/app_localizations.dart';
import 'platform/notify_platform.dart';
import 'ui/screens/home.dart';
import 'ui/screens/onboarding.dart';
import 'ui/theme/tokens.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: PutnikApp()));
  // Первый кадр нарисован — запуск удался (для ловушки падений на Android)
  WidgetsBinding.instance.addPostFrameCallback((_) => NotifyPlatform().appStarted());
}

class PutnikApp extends ConsumerStatefulWidget {
  const PutnikApp({super.key});

  @override
  ConsumerState<PutnikApp> createState() => _PutnikAppState();
}

class _PutnikAppState extends ConsumerState<PutnikApp> with WidgetsBindingObserver {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(() async {
      final c = ref.read(appProvider.notifier);
      await c.init();
      await c.trackNotificationOpen();
    });
    // Пока приложение открыто — подтягиваем шаги раз в минуту
    _timer = Timer.periodic(const Duration(minutes: 1), (_) => ref.read(appProvider.notifier).refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) {
      final c = ref.read(appProvider.notifier);
      c.trackNotificationOpen();
      c.refreshPermissions().then((_) => c.refresh());
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      onGenerateTitle: (context) => AppLocalizations.of(context).appName,
      theme: buildTheme(),
      locale: const Locale('ru'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: const _Gate(),
    );
  }
}

class _Gate extends ConsumerWidget {
  const _Gate();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final m = ref.watch(appProvider);
    final l = AppLocalizations.of(context);
    if (m.loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (m.error != null || m.content == null) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(Gap.l),
            child: Text(l.errorLoading(m.error ?? ''), textAlign: TextAlign.center),
          ),
        ),
      );
    }
    if (m.hero == null) return const OnboardingFlow();
    return const HomeShell();
  }
}

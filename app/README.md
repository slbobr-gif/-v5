# app — Flutter-клиент «Путника»

Сборка: `bash tool/bootstrap_android.sh && flutter pub get && flutter gen-l10n && flutter build apk --release [--dart-define=APPMETRICA_KEY=...]`.
`android/` не хранится в репозитории: его создаёт `flutter create`, а скрипт накладывает `android-overlay/`.
Архитектура — `docs/v5/01-architecture.md`.

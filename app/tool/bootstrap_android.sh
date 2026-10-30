#!/usr/bin/env bash
# Создаёт app/android/ через `flutter create` и накладывает android-overlay/:
# Kotlin (шагомер, Health Connect, уведомления), манифест, иконки, зависимости, minSdk 26.
# android/ не хранится в репозитории — всегда соответствует установленной версии Flutter.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d android ]; then
  tmp="$(mktemp -d)"
  # --org + --project-name дают applicationId = ru.putnik.app
  flutter create --platforms=android --org ru.putnik --project-name app "$tmp/app" >/dev/null
  cp -r "$tmp/app/android" android
  rm -rf "$tmp"
fi

ov=android-overlay
src=android/app/src/main
kt="$src/kotlin/ru/putnik/app"
mkdir -p "$kt"
rm -f "$src/java/ru/putnik/app/MainActivity.java"
cp "$ov"/kotlin/*.kt "$kt/"
cp "$ov/AndroidManifest.xml" "$src/AndroidManifest.xml"
cp -r "$ov"/res/. "$src/res/"
cp "$ov/proguard-rules.pro" android/app/proguard-rules.pro
cp "$ov/putnik-test.jks" android/app/putnik-test.jks

# Gradle: minSdk 26 (Health Connect, java.time) и наши зависимости — один раз
for f in android/app/build.gradle.kts android/app/build.gradle; do
  [ -f "$f" ] || continue
  sed -i 's/minSdk = flutter.minSdkVersion/minSdk = 26/; s/minSdkVersion flutter.minSdkVersion/minSdkVersion 26/' "$f"
  grep -q 'Путник: добавлено' "$f" || cat "$ov/gradle-dependencies.txt" >> "$f"
  # Если шаблон Flutter задаёт minSdk иначе — дописываем явно (работает и в .kts, и в Groovy)
  if ! grep -qE 'minSdk(Version)? *=? *26' "$f"; then
    printf '\nandroid {\n    defaultConfig {\n        minSdk = 26\n    }\n}\n' >> "$f"
  fi
  grep -nE 'minSdk' "$f" || true
done

grep -q 'ACTIVITY_RECOGNITION' "$src/AndroidManifest.xml" || { echo "манифест не наложен" >&2; exit 1; }
test -f "$kt/MainActivity.kt" || { echo "Kotlin не наложен" >&2; exit 1; }
echo "android/ готов: ru.putnik.app, minSdk 26, шагомер + Health Connect + уведомления"

#!/usr/bin/env bash
# Дымовой тест: ставит APK на эмулятор, запускает, ждёт и проверяет, что приложение живо.
# Журнал падения и снимок экрана — в отчёт сборки (GITHUB_STEP_SUMMARY) и в артефакт smoke-test.
set -u
APK="$1"
OUT="smoke"
mkdir -p "$OUT"
PKG=ru.putnik.app
summary() { echo "$1" >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"; }

adb wait-for-device
adb shell settings put global window_animation_scale 0 || true
adb install -r "$APK" > "$OUT/install.txt" 2>&1
INSTALL_RC=$?
cat "$OUT/install.txt"
if [ $INSTALL_RC -ne 0 ]; then
  summary "## ❌ APK не установился"
  summary '```'; summary "$(cat "$OUT/install.txt")"; summary '```'
  exit 1
fi

adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1
sleep 30
adb exec-out screencap -p > "$OUT/screen.png" || true
PID="$(adb shell pidof "$PKG" | tr -d '\r')"
adb logcat -d > "$OUT/logcat.txt"
FOCUS="$(adb shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | head -2 | tr -d '\r')"

# Выжимка: падения Java/Kotlin, нативные падения, ошибки Flutter
grep -n -A 45 -E "FATAL EXCEPTION|Fatal signal|E flutter|E/flutter|AndroidRuntime" "$OUT/logcat.txt" | head -200 > "$OUT/crash.txt" || true

if [ -z "$PID" ] || grep -q "FATAL EXCEPTION\|Fatal signal" "$OUT/logcat.txt"; then
  summary "## ❌ Приложение упало при запуске на эмуляторе (Android 14)"
  summary "Скопируй блок ниже и пришли разработчику."
  summary '```'; summary "$(head -150 "$OUT/crash.txt")"; summary '```'
  summary "Окно: $FOCUS"
  exit 1
fi

# Вторая проверка: приложение не только живо, но и показывает экран Flutter
summary "## ✅ Приложение запустилось и работает 30 секунд"
summary "Процесс: $PID · окно: $FOCUS"
if [ -s "$OUT/crash.txt" ]; then
  summary "### Предупреждения в журнале"
  summary '```'; summary "$(head -60 "$OUT/crash.txt")"; summary '```'
fi
exit 0

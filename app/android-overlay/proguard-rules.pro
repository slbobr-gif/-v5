# Путник: правила R8 для release-сборки
-keep class io.appmetrica.** { *; }
-dontwarn io.appmetrica.**
-dontwarn com.yandex.**
-keep class androidx.health.connect.** { *; }
-dontwarn androidx.health.connect.**
-keep class ru.putnik.app.** { *; }

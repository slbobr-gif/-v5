# Путник: правила R8 для release-сборки
# (в тестовой сборке R8 выключен, правила — на случай, если его включат для RuStore)
-keep class io.appmetrica.** { *; }
-dontwarn io.appmetrica.**
-dontwarn com.yandex.**
-keep class androidx.health.connect.** { *; }
-dontwarn androidx.health.connect.**
-keep class ru.putnik.app.** { *; }

# WorkManager и Room создают базу и воркеры через рефлексию — без этого падение
# «NoSuchMethodException: androidx.work.impl.WorkDatabase_Impl.<init>» при запуске
-keep class androidx.work.** { *; }
-keep class * extends androidx.room.RoomDatabase { <init>(...); }
-keep class * extends androidx.work.ListenableWorker { <init>(...); }
-keep class androidx.startup.** { *; }
-keep class * implements androidx.startup.Initializer { <init>(); }
-dontwarn androidx.work.**

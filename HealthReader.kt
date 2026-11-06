package ru.putnik.app

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.AggregateGroupByPeriodRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.Period

/**
 * Health Connect: шаги по локальным суткам из всех приложений и часов, если пользователь разрешил.
 *
 * Читаем ТОЛЬКО агрегат StepsRecord.COUNT_TOTAL: Health Connect сам убирает пересечения
 * (часы + телефон + Samsung Health пишут одни и те же шаги) по приоритету источников.
 * Сумма сырых записей дала бы двойной счёт.
 *
 * Читаем только при открытом приложении (фоновое чтение не нужно: движок всё равно работает
 * в приложении), поэтому READ_HEALTH_DATA_IN_BACKGROUND не запрашиваем.
 */
object HealthReader {
    private const val PROVIDER = "com.google.android.apps.healthdata"

    val PERMISSIONS: Set<String> = setOf(HealthPermission.getReadPermission(StepsRecord::class))

    /** available | update_required | not_installed | unavailable */
    fun statusString(context: Context): String {
        // Health Connect работает с Android 9; на 8.x его не поставить — честно «недоступен».
        if (Build.VERSION.SDK_INT < 28) return "unavailable"
        val sdk = try {
            HealthConnectClient.getSdkStatus(context, PROVIDER)
        } catch (e: Exception) {
            HealthConnectClient.SDK_UNAVAILABLE
        }
        return when (sdk) {
            HealthConnectClient.SDK_AVAILABLE -> "available"
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> "update_required"
            // На Android 14+ Health Connect встроен в систему — если его нет, поставить нечего.
            else -> if (Build.VERSION.SDK_INT >= 34) "unavailable" else "not_installed"
        }
    }

    suspend fun granted(context: Context): Boolean =
        try {
            HealthConnectClient.getOrCreate(context).permissionController
                .getGrantedPermissions().containsAll(PERMISSIONS)
        } catch (e: Exception) {
            false
        }

    /** Результат чтения: шаги по дням (yyyy-MM-dd → шаги) и приложения-источники. */
    class Daily(
        val days: Map<String, Long>,
        val originsToday: List<String>,
        val originsAll: List<String>,
    )

    /**
     * Сутки по местному времени: окно от начала дня (today − days + 1) до «сейчас», нарезка по 1 дню.
     * LocalDateTime + Period — Health Connect режет по местной зоне и сам учитывает переход на летнее время.
     */
    suspend fun dailySteps(context: Context, days: Int): Daily {
        val n = days.coerceIn(1, 30)
        val client = HealthConnectClient.getOrCreate(context)
        val today = LocalDate.now()
        val start = today.minusDays((n - 1).toLong()).atStartOfDay()
        val end = LocalDateTime.now()
        val response = client.aggregateGroupByPeriod(
            AggregateGroupByPeriodRequest(
                metrics = setOf(StepsRecord.COUNT_TOTAL),
                timeRangeFilter = TimeRangeFilter.between(start, end),
                timeRangeSlicer = Period.ofDays(1),
            )
        )
        val out = HashMap<String, Long>()
        val todayPkgs = LinkedHashSet<String>()
        val allPkgs = LinkedHashSet<String>()
        val todayKey = today.toString()
        for (bucket in response) {
            val count = bucket.result[StepsRecord.COUNT_TOTAL] ?: 0L
            val key = bucket.startTime.toLocalDate().toString()
            out[key] = maxOf(out[key] ?: 0L, count)
            for (o in bucket.result.dataOrigins) {
                allPkgs.add(o.packageName)
                if (key == todayKey) todayPkgs.add(o.packageName)
            }
        }
        return Daily(
            days = out,
            originsToday = todayPkgs.map { appName(context, it) }.distinct(),
            originsAll = allPkgs.map { appName(context, it) }.distinct(),
        )
    }

    /** Имя приложения-источника. Известные — по пакету (видимость пакетов на Android 11+ может скрыть подпись). */
    fun appName(context: Context, pkg: String): String {
        KNOWN[pkg]?.let { return it }
        return try {
            val pm = context.packageManager
            pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            pkg
        } catch (e: Exception) {
            pkg
        }
    }

    private val KNOWN = mapOf(
        "android" to "Android",
        "com.sec.android.app.shealth" to "Samsung Health",
        "com.mi.health" to "Mi Fitness",
        "com.xiaomi.wearable" to "Mi Fitness",
        "com.xiaomi.hm.health" to "Zepp Life",
        "com.huami.watch.hmwatchmanager" to "Zepp",
        "com.huawei.health" to "Huawei Health",
        "nl.appyhapps.healthsync" to "Health Sync",
        "com.google.android.apps.fitness" to "Google Fit",
        "com.google.android.apps.healthdata" to "Health Connect",
        "com.fitbit.FitbitMobile" to "Fitbit",
        "com.garmin.android.apps.connectmobile" to "Garmin Connect",
        "com.heytap.health" to "OHealth",
        "com.honor.health" to "Honor Health",
    )

    /** Магазин с экраном установки/обновления Health Connect (официальная ссылка с onboarding). */
    fun installIntents(): List<Intent> {
        val uri = "market://details?id=$PROVIDER&url=healthconnect%3A%2F%2Fonboarding"
        return listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse(uri)).setPackage("com.android.vending"),
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$PROVIDER")),
            Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=$PROVIDER")),
        )
    }

    /**
     * Экран разрешений Health Connect: после двух отказов системный диалог больше не показывается,
     * вернуть доступ (или выдать заново после отзыва) можно только там.
     */
    fun settingsIntents(context: Context): List<Intent> {
        val list = ArrayList<Intent>()
        if (Build.VERSION.SDK_INT >= 34) {
            list.add(
                Intent("android.health.connect.action.MANAGE_HEALTH_PERMISSIONS")
                    .putExtra(Intent.EXTRA_PACKAGE_NAME, context.packageName)
            )
            list.add(Intent("android.health.connect.action.HEALTH_HOME_SETTINGS"))
        } else {
            list.add(Intent("androidx.health.ACTION_HEALTH_CONNECT_SETTINGS"))
            context.packageManager.getLaunchIntentForPackage(PROVIDER)?.let { list.add(it) }
        }
        return list
    }
}

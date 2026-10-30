package ru.putnik.app

import android.content.Context
import android.os.Build
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.AggregateGroupByPeriodRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.Period

/** Health Connect: шаги по дням из всех приложений и часов, если пользователь разрешил. */
object HealthReader {
    val PERMISSIONS: Set<String> = setOf(HealthPermission.getReadPermission(StepsRecord::class))

    fun statusString(context: Context): String =
        when (HealthConnectClient.getSdkStatus(context)) {
            HealthConnectClient.SDK_AVAILABLE -> "available"
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> "update_required"
            else -> if (Build.VERSION.SDK_INT >= 34) "unavailable" else "not_installed"
        }

    suspend fun granted(context: Context): Boolean =
        try {
            HealthConnectClient.getOrCreate(context).permissionController
                .getGrantedPermissions().containsAll(PERMISSIONS)
        } catch (e: Exception) {
            false
        }

    suspend fun dailySteps(context: Context, days: Int): Map<String, Long> {
        val client = HealthConnectClient.getOrCreate(context)
        val start = LocalDate.now().minusDays((days - 1).toLong()).atStartOfDay()
        val end = LocalDateTime.now()
        val response = client.aggregateGroupByPeriod(
            AggregateGroupByPeriodRequest(
                metrics = setOf(StepsRecord.COUNT_TOTAL),
                timeRangeFilter = TimeRangeFilter.between(start, end),
                timeRangeSlicer = Period.ofDays(1),
            )
        )
        val out = HashMap<String, Long>()
        for (bucket in response) {
            val count = bucket.result[StepsRecord.COUNT_TOTAL] ?: 0L
            out[bucket.startTime.toLocalDate().toString()] = count
        }
        return out
    }
}

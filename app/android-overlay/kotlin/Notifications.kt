package ru.putnik.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit

/** Локальные уведомления: Dart присылает готовый список, мы ставим их в расписание WorkManager. */
object Notifications {
    private const val CHANNEL = "putnik_main"
    private const val TAG = "putnik_notif"
    const val EXTRA_ID = "putnik_notif_id"

    fun hasPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED

    private fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= 26) {
            val nm = context.getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL, "Путник", NotificationManager.IMPORTANCE_DEFAULT)
                )
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun show(context: Context, id: Int, title: String, body: String) {
        if (!hasPermission(context)) return
        ensureChannel(context)
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA_ID, id)
        }
        val pi = PendingIntent.getActivity(
            context, id, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val n = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_putnik)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(id, n)
    }

    fun replaceAll(context: Context, items: List<Map<String, Any?>>) {
        // Сбой WorkManager не должен ронять приложение: просто не будет уведомлений
        try {
            enqueueAll(context, items)
        } catch (e: Throwable) {
            android.util.Log.e("Putnik", "notifications schedule failed", e)
        }
    }

    private fun enqueueAll(context: Context, items: List<Map<String, Any?>>) {
        val wm = WorkManager.getInstance(context)
        wm.cancelAllWorkByTag(TAG)
        val now = System.currentTimeMillis()
        for (item in items) {
            val at = (item["at"] as? Number)?.toLong() ?: continue
            if (at <= now) continue
            val data = workDataOf(
                "id" to ((item["id"] as? Number)?.toInt() ?: 0),
                "title" to (item["title"] as? String ?: ""),
                "body" to (item["body"] as? String ?: ""),
            )
            val req = OneTimeWorkRequestBuilder<NotifyWorker>()
                .setInitialDelay(at - now, TimeUnit.MILLISECONDS)
                .setInputData(data)
                .addTag(TAG)
                .build()
            wm.enqueue(req)
        }
    }
}

class NotifyWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        val title = inputData.getString("title") ?: return Result.success()
        val body = inputData.getString("body") ?: ""
        Notifications.show(applicationContext, inputData.getInt("id", 0), title, body)
        return Result.success()
    }
}

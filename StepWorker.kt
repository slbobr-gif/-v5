package ru.putnik.app

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/** Раз в 15 минут читает датчик шагов, даже когда приложение закрыто. */
class StepWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        try {
            StepTracker.sample(applicationContext)
        } catch (e: Exception) {
        }
        return Result.success()
    }

    companion object {
        fun schedule(context: Context) {
            // Сбой WorkManager не должен ронять приложение: без фона шаги подтянутся при открытии
            try {
                val req = PeriodicWorkRequestBuilder<StepWorker>(15, TimeUnit.MINUTES).build()
                WorkManager.getInstance(context)
                    .enqueueUniquePeriodicWork("putnik_steps", ExistingPeriodicWorkPolicy.KEEP, req)
            } catch (e: Throwable) {
                android.util.Log.e("Putnik", "step worker schedule failed", e)
            }
        }
    }
}

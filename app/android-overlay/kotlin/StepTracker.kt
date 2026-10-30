package ru.putnik.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Встроенный шагомер телефона (TYPE_STEP_COUNTER). Счётчик живёт в железе с момента включения
 * телефона; мы периодически читаем его и раскладываем прирост по локальным дням.
 */
object StepTracker {

    /** Одно чтение счётчика. Блокирует поток до [timeoutMs]; вызывать не на главном потоке. */
    fun readCounterBlocking(context: Context, timeoutMs: Long = 4000L): Float? {
        if (Build.VERSION.SDK_INT >= 29 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACTIVITY_RECOGNITION) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return null
        }
        val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val sensor = sm.getDefaultSensor(Sensor.TYPE_STEP_COUNTER) ?: return null
        val thread = HandlerThread("putnik-steps").apply { start() }
        val latch = CountDownLatch(1)
        var value: Float? = null
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                if (event.values.isNotEmpty()) value = event.values[0]
                latch.countDown()
            }

            override fun onAccuracyChanged(s: Sensor?, accuracy: Int) {}
        }
        try {
            sm.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_NORMAL, Handler(thread.looper))
            latch.await(timeoutMs, TimeUnit.MILLISECONDS)
        } finally {
            sm.unregisterListener(listener)
            thread.quitSafely()
        }
        return value
    }

    /**
     * Чтение и запись — под одной блокировкой: иначе показание, снятое раньше, могло записаться позже
     * более свежего, счётчик «уменьшался», и это принималось за перезагрузку — весь счётчик шёл в зачёт ещё раз.
     */
    fun sample(context: Context) = synchronized(StepStore.LOCK) {
        val v = readCounterBlocking(context) ?: return@synchronized
        StepStore(context).record(v, System.currentTimeMillis())
    }
}

/** Шаги по локальным дням, накопленные с датчика. Хранятся 45 дней. */
class StepStore(context: Context) {
    private val prefs = context.getSharedPreferences("putnik_steps", Context.MODE_PRIVATE)

    // Блокировка общая на процесс: StepWorker и экран читают датчик параллельно, и каждый создаёт
    // свой StepStore — @Synchronized на экземпляре не спасал от двойного зачёта одного прироста.
    fun record(counter: Float, now: Long) = synchronized(LOCK) { recordLocked(counter, now) }

    private fun recordLocked(counter: Float, now: Long) {
        val last = prefs.getFloat("lastCounter", -1f)
        val days = days().toMutableMap()
        if (last >= 0f) {
            // Счётчик уменьшился — телефон перезагружался, всё, что насчитано с загрузки, — новые шаги.
            var delta = if (counter < last) counter.toInt() else (counter - last).toInt()
            if (delta < 0 || delta > 100_000) delta = 0
            if (delta > 0) {
                val today = dayKey(now)
                days[today] = (days[today] ?: 0) + delta
            }
        }
        val cutoff = dayKey(now - 45L * 24 * 3600 * 1000)
        val kept = days.filterKeys { it >= cutoff }
        prefs.edit()
            .putFloat("lastCounter", counter)
            .putLong("lastReadAt", now)
            .putString("days", JSONObject(kept as Map<*, *>).toString())
            .apply()
    }

    fun days(): Map<String, Int> {
        val raw = prefs.getString("days", null) ?: return emptyMap()
        return try {
            val o = JSONObject(raw)
            val out = HashMap<String, Int>()
            val keys = o.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                out[k] = o.optInt(k, 0)
            }
            out
        } catch (e: Exception) {
            emptyMap()
        }
    }

    companion object {
        /** Одна на процесс: StepWorker и экран создают свои StepStore. */
        val LOCK = Any()

        fun dayKey(ms: Long): String = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date(ms))
    }
}

package ru.putnik.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.health.connect.client.PermissionController
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.util.Log
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Хост Flutter. FlutterFragmentActivity (а не FlutterActivity) нужен,
 * чтобы зарегистрировать системный диалог разрешений Health Connect.
 */
class MainActivity : FlutterFragmentActivity() {

    // Исключение в корутине не должно ронять приложение — только логируется
    private val scope = CoroutineScope(
        SupervisorJob() + Dispatchers.Main +
            CoroutineExceptionHandler { _, e -> Log.e("Putnik", "coroutine failed", e) }
    )
    private var pendingActivity: MethodChannel.Result? = null
    private var pendingNotify: MethodChannel.Result? = null
    private var pendingHealth: MethodChannel.Result? = null

    /** id уведомления, по которому открыли приложение (для аналитики), до чтения из Dart. */
    private var openedNotification: Int? = null

    private fun captureNotification(i: Intent?) {
        val id = i?.getIntExtra(Notifications.EXTRA_ID, -1) ?: -1
        if (id >= 0) {
            openedNotification = id
            i?.removeExtra(Notifications.EXTRA_ID)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        captureNotification(intent)
    }

    private val healthLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract()
    ) { granted ->
        pendingHealth?.success(granted.containsAll(HealthReader.PERMISSIONS))
        pendingHealth = null
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val messenger = flutterEngine.dartExecutor.binaryMessenger

        MethodChannel(messenger, "putnik/steps").setMethodCallHandler { call, result ->
            when (call.method) {
                "getStatus" -> scope.launch {
                    val status = try {
                        stepsStatus()
                    } catch (e: Exception) {
                        Log.e("Putnik", "status failed", e)
                        mapOf("sensorAvailable" to false, "activityPermission" to hasActivityPermission(),
                            "hcStatus" to "unavailable", "hcPermission" to false)
                    }
                    result.success(status)
                }
                "requestActivityPermission" -> requestActivityPermission(result)
                "requestHealthPermission" -> requestHealthPermission(result)
                "openHealthConnectInstall" -> {
                    openHealthConnectInstall()
                    result.success(true)
                }
                "startBackgroundTracking" -> {
                    StepWorker.schedule(applicationContext)
                    result.success(true)
                }
                "getDailySteps" -> {
                    val days = call.argument<Int>("days") ?: 30
                    scope.launch {
                        val data = try {
                            dailySteps(days)
                        } catch (e: Exception) {
                            Log.e("Putnik", "daily steps failed", e)
                            mapOf("days" to emptyMap<String, Long>(), "sensor" to emptyMap<String, Long>(),
                                "hc" to emptyMap<String, Long>())
                        }
                        result.success(data)
                    }
                }
                else -> result.notImplemented()
            }
        }

        captureNotification(intent)
        MethodChannel(messenger, "putnik/notify").setMethodCallHandler { call, result ->
            when (call.method) {
                "appStarted" -> {
                    CrashLog.markStarted(applicationContext)
                    result.success(true)
                }
                "consumeOpened" -> {
                    result.success(openedNotification)
                    openedNotification = null
                }
                "hasPermission" -> result.success(Notifications.hasPermission(this))
                "requestPermission" -> requestNotifyPermission(result)
                "replaceAll" -> {
                    @Suppress("UNCHECKED_CAST")
                    val items = (call.argument<List<Any?>>("items") ?: emptyList())
                        .mapNotNull { it as? Map<String, Any?> }
                    Notifications.replaceAll(applicationContext, items)
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }

    // ---------------------------------------------------------------- шаги

    private fun hasActivityPermission(): Boolean =
        Build.VERSION.SDK_INT < 29 ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACTIVITY_RECOGNITION) ==
            PackageManager.PERMISSION_GRANTED

    private suspend fun stepsStatus(): Map<String, Any> {
        val sm = getSystemService(SENSOR_SERVICE) as SensorManager
        val hcStatus = HealthReader.statusString(this)
        val hcGranted = if (hcStatus == "available") HealthReader.granted(this) else false
        return mapOf(
            "sensorAvailable" to (sm.getDefaultSensor(Sensor.TYPE_STEP_COUNTER) != null),
            "activityPermission" to hasActivityPermission(),
            "hcStatus" to hcStatus,
            "hcPermission" to hcGranted,
        )
    }

    private suspend fun dailySteps(days: Int): Map<String, Any> {
        withContext(Dispatchers.IO) {
            try {
                StepTracker.sample(applicationContext)
            } catch (e: Exception) {
            }
        }
        val sensor: Map<String, Long> = StepStore(applicationContext).days().mapValues { it.value.toLong() }
        val hc: Map<String, Long> =
            if (HealthReader.statusString(this) == "available" && HealthReader.granted(this)) {
                try {
                    HealthReader.dailySteps(this, days)
                } catch (e: Exception) {
                    emptyMap()
                }
            } else {
                emptyMap()
            }
        val merged = HashMap<String, Long>()
        for ((d, v) in sensor) merged[d] = maxOf(merged[d] ?: 0L, v)
        for ((d, v) in hc) merged[d] = maxOf(merged[d] ?: 0L, v)
        return mapOf("days" to merged, "sensor" to sensor, "hc" to hc)
    }

    private fun requestActivityPermission(result: MethodChannel.Result) {
        if (hasActivityPermission()) {
            StepWorker.schedule(applicationContext)
            result.success(true)
            return
        }
        if (deniedForever(Manifest.permission.ACTIVITY_RECOGNITION)) {
            openAppSettings()
            result.success(false)
            return
        }
        markAsked(Manifest.permission.ACTIVITY_RECOGNITION)
        pendingActivity = result
        ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.ACTIVITY_RECOGNITION), REQ_ACTIVITY)
    }

    private fun requestHealthPermission(result: MethodChannel.Result) {
        if (HealthReader.statusString(this) != "available") {
            result.success(false)
            return
        }
        pendingHealth = result
        try {
            healthLauncher.launch(HealthReader.PERMISSIONS)
        } catch (e: Exception) {
            pendingHealth = null
            result.success(false)
        }
    }

    private fun openHealthConnectInstall() {
        val pkg = "com.google.android.apps.healthdata"
        val market = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$pkg"))
        val web = Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=$pkg"))
        try {
            startActivity(market)
        } catch (e: Exception) {
            try {
                startActivity(web)
            } catch (e2: Exception) {
            }
        }
    }

    // ---------------------------------------------------------------- уведомления

    private fun requestNotifyPermission(result: MethodChannel.Result) {
        if (Notifications.hasPermission(this)) {
            result.success(true)
            return
        }
        if (deniedForever(Manifest.permission.POST_NOTIFICATIONS)) {
            openAppSettings()
            result.success(false)
            return
        }
        markAsked(Manifest.permission.POST_NOTIFICATIONS)
        pendingNotify = result
        ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIFY)
    }

    // ---------------------------------------------------------------- отказ «навсегда»

    private val permPrefs by lazy { getSharedPreferences("putnik_perm", MODE_PRIVATE) }

    private fun markAsked(permission: String) = permPrefs.edit().putBoolean(permission, true).apply()

    /**
     * После второго отказа Android больше не показывает системный диалог — кнопка «Разрешить»
     * молча ничего бы не делала. В этом случае ведём игрока в настройки приложения.
     */
    private fun deniedForever(permission: String): Boolean =
        permPrefs.getBoolean(permission, false) &&
            !ActivityCompat.shouldShowRequestPermissionRationale(this, permission)

    private fun openAppSettings() {
        try {
            startActivity(
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null))
            )
        } catch (e: Exception) {
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        val ok = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
        when (requestCode) {
            REQ_ACTIVITY -> {
                if (ok) {
                    StepWorker.schedule(applicationContext)
                    scope.launch(Dispatchers.IO) {
                        try {
                            StepTracker.sample(applicationContext)
                        } catch (e: Exception) {
                        }
                    }
                }
                pendingActivity?.success(ok)
                pendingActivity = null
            }
            REQ_NOTIFY -> {
                pendingNotify?.success(ok)
                pendingNotify = null
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private const val REQ_ACTIVITY = 501
        private const val REQ_NOTIFY = 502
    }
}

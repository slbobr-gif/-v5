package ru.putnik.app

import android.app.Activity
import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.work.Configuration
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Ловушка падений для тестовой сборки. Любое необработанное исключение сохраняется,
 * и при следующем запуске вместо вылета показывается экран с текстом ошибки —
 * его можно скопировать и прислать разработчику.
 */
object CrashLog {
    private const val PREFS = "putnik_crash"
    private const val KEY_TEXT = "text"
    private const val KEY_LAUNCHING = "launching"

    fun install(app: Context) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, e ->
            try {
                val sw = StringWriter()
                e.printStackTrace(PrintWriter(sw))
                val text = buildString {
                    append(header(app))
                    append("Поток: ").append(thread.name).append('\n')
                    append(sw.toString().take(12000))
                }
                app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .edit().putString(KEY_TEXT, text).commit()
            } catch (_ignored: Throwable) {
            }
            previous?.uncaughtException(thread, e)
        }
    }

    fun header(context: Context): String {
        val version = try {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName
        } catch (e: Exception) {
            "?"
        }
        val time = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
        return "Путник $version · ${Build.MANUFACTURER} ${Build.MODEL} · Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}) · $time\n"
    }

    fun pending(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_TEXT, null)

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .remove(KEY_TEXT).remove(KEY_LAUNCHING).commit()
    }

    /** Флаг «запуск начался» — снимается, когда Flutter нарисовал первый кадр. */
    fun markLaunching(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_LAUNCHING, true).commit()
    }

    fun markStarted(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY_LAUNCHING, false).apply()
    }

    fun wasLaunchInterrupted(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_LAUNCHING, false)
}

/**
 * Ловушка ставится в attachBaseContext — раньше всех ContentProvider-ов библиотек,
 * чтобы поймать и падения при старте процесса.
 * WorkManager запускается по требованию (Configuration.Provider), а не при старте процесса:
 * сбой в нём больше не роняет приложение до первого экрана.
 */
class PutnikApplication : Application(), Configuration.Provider {
    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(base)
        CrashLog.install(base)
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setMinimumLoggingLevel(android.util.Log.INFO).build()
}

/**
 * Точка входа. Обычно сразу открывает MainActivity (Flutter).
 * Если прошлый запуск упал — показывает текст ошибки.
 */
class LaunchActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val crash = CrashLog.pending(this)
        val interrupted = CrashLog.wasLaunchInterrupted(this)
        if (crash == null && !interrupted) {
            openApp()
            return
        }
        val text = crash ?: (CrashLog.header(this) +
            "Прошлый запуск оборвался без текста ошибки (сбой внутри графики или системы).\n" +
            "Если повторится — пришли разработчику модель телефона и версию Android.")
        showReport(text)
    }

    private fun openApp() {
        CrashLog.markLaunching(this)
        startActivity(Intent(this, MainActivity::class.java).apply { putExtras(intent) })
        overridePendingTransition(0, 0)
        finish()
    }

    private fun showReport(text: String) {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#0E1621"))
            setPadding(pad, pad * 2, pad, pad)
        }
        root.addView(TextView(this).apply {
            setText("Путник упал при прошлом запуске")
            setTextColor(Color.parseColor("#D9B35B"))
            textSize = 20f
        })
        root.addView(TextView(this).apply {
            setText("Скопируй или отправь этот текст разработчику — по нему найдём причину.")
            setTextColor(Color.parseColor("#E9DFC8"))
            textSize = 14f
            setPadding(0, pad / 2, 0, pad / 2)
        })
        val scroll = ScrollView(this)
        scroll.addView(TextView(this).apply {
            setText(text)
            setTextColor(Color.parseColor("#9BA7B4"))
            typeface = Typeface.MONOSPACE
            textSize = 11f
            setTextIsSelectable(true)
        })
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        fun button(label: String, onClick: () -> Unit) = Button(this).apply {
            setText(label)
            setOnClickListener { onClick() }
        }
        buttons.addView(button("Скопировать") {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("putnik-crash", text))
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        buttons.addView(button("Отправить") {
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
            try {
                startActivity(Intent.createChooser(send, "Отправить отчёт"))
            } catch (e: Exception) {
            }
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        buttons.addView(button("Запустить") {
            CrashLog.clear(this)
            openApp()
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        root.addView(buttons)
        setContentView(root)
    }
}

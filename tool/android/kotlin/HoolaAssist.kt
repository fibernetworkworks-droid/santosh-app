package com.newtika.santosh

import android.app.assist.AssistContent
import android.app.assist.AssistStructure
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.service.voice.VoiceInteractionService
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import android.speech.RecognitionListener
import android.speech.RecognitionService
import android.speech.SpeechRecognizer
import java.io.File

/** v0.63 Hoola as the phone's default digital assistant (Settings > Apps > Default apps > Digital assistant app).
 *
 *  Long-press home / the assistant gesture -> [HoolaAssistSession]: Android hands over what is on the screen ONLY when
 *  the owner has allowed it for the assistant ("Use text from screen" / "Use screenshot"): the visible text of the app
 *  in front and a screenshot. Nothing is read in the background, ever. The session opens Hoola's chat with the
 *  screenshot + a text file of the screen attached as pending files (nothing is sent until she taps send).
 *  No accessibility service, no screen recording. */
class HoolaAssistService : VoiceInteractionService() {
    companion object {
        fun isDefault(ctx: Context): Boolean {
            val v = try { Settings.Secure.getString(ctx.contentResolver, "assistant") } catch (_: Exception) { null } ?: ""
            val vi = try { Settings.Secure.getString(ctx.contentResolver, "voice_interaction_service") } catch (_: Exception) { null } ?: ""
            return v.startsWith(ctx.packageName + "/") || vi.startsWith(ctx.packageName + "/")
        }

        fun openSettings(ctx: Context) {
            val tries = listOf(
                Intent("android.settings.MANAGE_DEFAULT_APPS_SETTINGS"),
                Intent(Settings.ACTION_VOICE_INPUT_SETTINGS),
                Intent(Settings.ACTION_SETTINGS))
            for (i in tries) {
                try { ctx.startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return } catch (_: Exception) {}
            }
        }
    }
}

class HoolaAssistSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: Bundle?): VoiceInteractionSession = HoolaAssistSession(this)
}

class HoolaAssistSession(ctx: Context) : VoiceInteractionSession(ctx) {
    private val main = Handler(Looper.getMainLooper())
    private var shot: Bitmap? = null
    private var text = StringBuilder()
    private var appPkg = ""
    private var gotAssist = false
    private var gotShot = false
    private var wantAssist = false
    private var wantShot = false
    private var sent = false

    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        shot = null; text = StringBuilder(); appPkg = ""; sent = false
        wantAssist = showFlags and SHOW_WITH_ASSIST != 0
        wantShot = showFlags and SHOW_WITH_SCREENSHOT != 0
        gotAssist = !wantAssist; gotShot = !wantShot
        if (!wantAssist && !wantShot) { finishAndOpen(); return }
        main.postDelayed({ finishAndOpen() }, 1800)       // whatever arrived by then
    }

    @Suppress("DEPRECATION")
    override fun onHandleAssist(data: Bundle?, structure: AssistStructure?, content: AssistContent?) {
        try {
            structure?.let {
                appPkg = it.activityComponent?.packageName ?: ""
                for (i in 0 until it.windowNodeCount) walk(it.getWindowNodeAt(i).rootViewNode, 0)
            }
            content?.webUri?.let { text.append("\nLink: ").append(it.toString()) }
        } catch (_: Exception) {}
        gotAssist = true
        maybeDone()
    }

    override fun onHandleScreenshot(screenshot: Bitmap?) {
        shot = screenshot
        gotShot = true
        maybeDone()
    }

    private fun walk(n: AssistStructure.ViewNode?, depth: Int) {
        if (n == null || depth > 40 || text.length > 6000) return
        // never pass on what is typed in password / OTP fields
        val type = if (Build.VERSION.SDK_INT >= 26) n.inputType else 0
        val cls = type and 0xF
        val variation = type and 0xFF0
        val hints = if (Build.VERSION.SDK_INT >= 26) n.autofillHints?.joinToString(" ")?.lowercase() ?: "" else ""
        val pw = (cls == 1 && variation in setOf(0x80, 0x90, 0xE0)) || (cls == 2 && variation == 0x10) ||
            hints.contains("password") || hints.contains("otp") || hints.contains("creditcard") || hints.contains("pin")
        if (!pw) {
            val t = n.text?.toString()?.trim().orEmpty()
            if (t.isNotEmpty() && t.length < 800) text.append(t).append('\n')
            else n.contentDescription?.toString()?.trim()?.takeIf { it.isNotEmpty() && it.length < 200 }?.let { text.append(it).append('\n') }
        }
        for (i in 0 until n.childCount) walk(n.getChildAt(i), depth + 1)
    }

    private fun maybeDone() {
        if (gotAssist && gotShot) main.post { finishAndOpen() }
    }

    private fun finishAndOpen() {
        if (sent) return
        sent = true
        val ctx = context
        val dir = File(ctx.cacheDir, "shared").apply { mkdirs() }
        val ts = System.currentTimeMillis()
        val files = org.json.JSONArray()
        shot?.let { b ->
            try {
                val f = File(dir, "${ts}_screen.jpg")
                f.outputStream().use { b.compress(Bitmap.CompressFormat.JPEG, 85, it) }
                files.put(org.json.JSONObject().put("path", f.absolutePath).put("name", "screen.jpg").put("size", f.length()))
            } catch (_: Exception) {}
        }
        val words = text.toString().replace(Regex("\n{3,}"), "\n\n").trim()
        if (words.length > 20) {
            try {
                val f = File(dir, "${ts}_screen-text.txt")
                f.writeText(words.take(6000))
                files.put(org.json.JSONObject().put("path", f.absolutePath).put("name", "screen-text.txt").put("size", f.length()))
            } catch (_: Exception) {}
        }
        val payload = org.json.JSONObject().put("files", files).put("text", "").put("skipped", 0)
            .put("assist", org.json.JSONObject().put("app", appPkg).put("screenshot", shot != null).put("screen_text", words.length > 20))
        val i = Intent(ctx, MainActivity::class.java)
            .setAction(MainActivity.ACTION_ASSIST_SCREEN)
            .putExtra("payload", payload.toString())
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        try { startAssistantActivity(i) } catch (_: Exception) {
            try { ctx.startActivity(i) } catch (_: Exception) {}
        }
        hide()
    }
}

/** Android makes the default assistant also the phone's "voice input" provider. Hoola has no speech engine of its
 *  own, so this hands every request to the phone's real recogniser (Google's or the maker's) and passes the
 *  answers back unchanged: typing by voice keeps working everywhere after choosing Hoola. */
class HoolaRecognition : RecognitionService() {
    private var inner: SpeechRecognizer? = null

    private fun target(): ComponentName? {
        val list = packageManager.queryIntentServices(Intent(RecognitionService.SERVICE_INTERFACE), 0)
        val other = list.map { ComponentName(it.serviceInfo.packageName, it.serviceInfo.name) }.filter { it.packageName != packageName }
        return other.firstOrNull { it.packageName.startsWith("com.google") } ?: other.firstOrNull()
    }

    override fun onStartListening(intent: Intent?, cb: Callback?) {
        if (cb == null) return
        val t = target()
        if (t == null) {
            if (Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
                inner = SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
            } else { try { cb.error(SpeechRecognizer.ERROR_CLIENT) } catch (_: Exception) {}; return }
        } else {
            inner?.destroy()
            inner = SpeechRecognizer.createSpeechRecognizer(this, t)
        }
        inner?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(p: Bundle?) { try { cb.readyForSpeech(p ?: Bundle()) } catch (_: Exception) {} }
            override fun onBeginningOfSpeech() { try { cb.beginningOfSpeech() } catch (_: Exception) {} }
            override fun onRmsChanged(v: Float) { try { cb.rmsChanged(v) } catch (_: Exception) {} }
            override fun onBufferReceived(b: ByteArray?) { try { if (b != null) cb.bufferReceived(b) } catch (_: Exception) {} }
            override fun onEndOfSpeech() { try { cb.endOfSpeech() } catch (_: Exception) {} }
            override fun onError(e: Int) { try { cb.error(e) } catch (_: Exception) {} }
            override fun onResults(r: Bundle?) { try { cb.results(r ?: Bundle()) } catch (_: Exception) {} }
            override fun onPartialResults(r: Bundle?) { try { cb.partialResults(r ?: Bundle()) } catch (_: Exception) {} }
            override fun onEvent(type: Int, p: Bundle?) {}
        })
        inner?.startListening(intent ?: Intent())
    }

    override fun onStopListening(cb: Callback?) { inner?.stopListening() }
    override fun onCancel(cb: Callback?) { inner?.cancel() }
    override fun onDestroy() { inner?.destroy(); inner = null; super.onDestroy() }
}

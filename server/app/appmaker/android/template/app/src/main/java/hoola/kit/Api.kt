package hoola.kit

// Made by Hoola App Sahayak. Read-only refresh of the business's public content from her own Hoola server
// (https only, no secrets in the app). Orders / bookings from the app are the next version's job.

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object Api {
    private var base = ""
    private var appId = ""

    fun init(baseUrl: String, id: String) {
        base = baseUrl.trimEnd('/')
        appId = id
    }

    /** Fetches fresh content; returns true when something new was applied. Never throws. */
    suspend fun refresh(ctx: Context): Boolean = withContext(Dispatchers.IO) {
        if (!base.startsWith("https://") || appId.isEmpty()) return@withContext false
        try {
            val c = (URL("$base/api/app-content/$appId").openConnection() as HttpURLConnection).apply {
                connectTimeout = 8000; readTimeout = 12000; instanceFollowRedirects = false
                setRequestProperty("Accept", "application/json")
            }
            if (c.responseCode != 200) { c.disconnect(); return@withContext false }
            val text = c.inputStream.bufferedReader().use { it.readText() }
            c.disconnect()
            if (text.length > 2_000_000) return@withContext false
            val o = JSONObject(text)
            if (!o.has("facts")) return@withContext false
            Store.put(ctx, "content", text)
            withContext(Dispatchers.Main) { AppData.apply(text, fromServer = true) }
            true
        } catch (_: Exception) {
            false
        }
    }
}

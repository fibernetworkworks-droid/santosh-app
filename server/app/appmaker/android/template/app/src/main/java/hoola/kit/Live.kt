package hoola.kit

// Made by Hoola App Sahayak (v0.407 ABHI ABHI). Real time: while the app is open and signed in, ONE live stream from
// the business's Hoola server tells this phone the moment something it may see changes - a list row (its own order's
// status, a new order for staff), a chat message, who is online, who is typing. The server filters every event with the
// list's own rules. Live never writes: saving still goes through the offline outbox, and a changed list is simply loaded
// again (so the screen always shows what the server says). No network / too many people / an old server = the app keeps
// its normal refresh; a dropped stream reconnects and the server replays what was missed (Last-Event-ID).

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

object Live {
    /** The stream is open right now (a green dot on screens that care). */
    val connected = mutableStateOf(false)
    /** Goes up by one on every chat message this account may see: the chat screen loads again at once. */
    val chatTick = mutableIntStateOf(0)
    /** Goes up on every change to a list: liveRows(coll) reloads that list. */
    private val rev = mutableStateMapOf<String, Int>()
    /** Who is online: key -> (first name, staff?). Customers only ever see the shop's staff. */
    val online = mutableStateMapOf<String, Pair<String, Boolean>>()
    /** Chat thread -> (name, until when) of someone typing in it. */
    private val typing = mutableStateMapOf<String, Pair<String, Long>>()
    val clock = mutableLongStateOf(0L)

    private var job: Job? = null
    private var lastId = ""
    private val dirty = mutableSetOf<String>()
    private var flush: Job? = null
    private var lastTyping = 0L

    fun rev(coll: String): Int = rev[coll] ?: 0

    /** A screen shows this list (nothing to do on the phone: the server already sends only what this account may see). */
    fun watch(coll: String) { if (coll.isNotEmpty()) start() }

    /** Someone typing in this thread right now ("" = the customer's own thread with the shop). */
    fun typingIn(thread: String): String {
        val now = clock.longValue
        val key = if (thread.isEmpty()) Auth.me.value?.id ?: "" else thread
        val t = typing[key] ?: return ""
        return if (t.second > now) t.first else ""
    }

    val staffOnline: Boolean get() = online.values.any { it.second }

    /** Called when the app comes to the front. Safe to call again. */
    fun start() {
        if (job?.isActive == true) return
        job = Db.scope.launch { loop() }
        Db.scope.launch {                                   // a tick for "typing…" to fade without a new event
            while (isActive && job?.isActive == true) {
                withContext(Dispatchers.Main) { clock.longValue = System.currentTimeMillis() }
                delay(1000)
            }
        }
    }

    /** Called when the app goes to the back: the stream closes (no battery used in the background; push does that job). */
    fun stop() {
        job?.cancel()
        job = null
        Db.scope.launch(Dispatchers.Main) { connected.value = false; online.clear(); typing.clear() }
    }

    /** "typing…" for the other side (throttled: one signal every 3 s). thread = the customer's id (staff); "" = own thread. */
    fun typingNow(thread: String = "") {
        val t = System.currentTimeMillis()
        if (t - lastTyping < 3000 || !Auth.signedIn) return
        lastTyping = t
        Db.scope.launch { Cloud.call("POST", "/live/typing", JSONObject().put("thread", thread), Auth.token()) }
    }

    private suspend fun loop() {
        var wait = 1000L
        while (true) {
            if (!Auth.signedIn || !Cloud.ready) { delay(5000); continue }
            val c = Cloud.stream("/live", Auth.token(), lastId)
            var code = 0
            try {
                if (c != null) {
                    code = try { c.responseCode } catch (_: Exception) { 0 }
                    if (code == 200) {
                        withContext(Dispatchers.Main) { connected.value = true }
                        wait = 1000L
                        read(c)
                    }
                }
            } catch (_: Exception) {
            } finally {
                try { c?.disconnect() } catch (_: Exception) {}
                withContext(Dispatchers.Main) { connected.value = false }
            }
            when (code) {
                401 -> { delay(30_000) }                     // signed out elsewhere: the next screen load says so
                404 -> { delay(10 * 60_000L) }               // an older server without live: plain refresh only
                429 -> { delay(60_000) }                     // too many people right now: try again in a minute
                else -> { delay(wait); wait = (wait * 2).coerceAtMost(30_000L) }
            }
        }
    }

    private suspend fun read(c: java.net.HttpURLConnection) {
        val r = c.inputStream.bufferedReader(Charsets.UTF_8)
        var id = ""
        val data = StringBuilder()
        while (true) {
            val line = r.readLine() ?: break
            when {
                line.isEmpty() -> {
                    if (data.isNotEmpty()) {
                        try { handle(JSONObject(data.toString())) } catch (_: Exception) {}
                        if (id.isNotEmpty()) lastId = id
                    }
                    data.setLength(0); id = ""
                }
                line.startsWith("data:") -> data.append(line.removePrefix("data:").trimStart())
                line.startsWith("id:") -> id = line.removePrefix("id:").trim()
                else -> {}                                  // ": ping", "event:", "retry:"
            }
        }
    }

    private suspend fun handle(e: JSONObject) {
        when (e.optString("type")) {
            "hello" -> if (lastId.isEmpty()) reloadAll()    // first connect: anything that changed before it opened
            "row" -> changed(e.optString("coll"))
            "reset" -> reloadAll()
            "chat" -> withContext(Dispatchers.Main) {
                chatTick.intValue += 1
                typing.remove(e.optString("thread"))
            }
            "typing" -> withContext(Dispatchers.Main) {
                typing[e.optString("thread")] = e.optString("name") to (System.currentTimeMillis() + 6000)
            }
            "presence" -> withContext(Dispatchers.Main) {
                val k = e.optString("member")
                if (e.optBoolean("online")) online[k] = e.optString("name") to e.optBoolean("staff") else online.remove(k)
            }
            "bye" -> if (e.optString("why") == "login") delay(30_000)
        }
    }

    private suspend fun reloadAll() {
        Db.collections().forEach { changed(it) }
        withContext(Dispatchers.Main) { chatTick.intValue += 1 }
        val p = Cloud.call("GET", "/live/presence", null, Auth.token())
        if (p.ok) withContext(Dispatchers.Main) {
            online.clear()
            arrList(p.body.optJSONArray("online")).forEach { online[it.s("member")] = it.s("name") to it.b("staff") }
        }
    }

    /** Many changes in a burst = one reload per list (a quarter second later). */
    private fun changed(coll: String) {
        if (coll.isEmpty()) return
        synchronized(dirty) { dirty.add(coll) }
        if (flush?.isActive == true) return
        flush = Db.scope.launch {
            delay(250)
            val todo = synchronized(dirty) { dirty.toList().also { dirty.clear() } }
            withContext(Dispatchers.Main) { todo.forEach { rev[it] = (rev[it] ?: 0) + 1 } }
        }
    }
}

/** v0.407 a small green dot + "Shop is online" (customers) / how many are online (staff), only while the stream is open. */
@Composable
fun LiveDot(modifier: Modifier = Modifier) {
    val on by Live.connected
    if (!on) return
    val label = if (Auth.isStaff) "${Live.online.size} ${Strings.isOnline}" else if (Live.staffOnline) Strings.shopOnline else Strings.live
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(Color(0xFF1E9E5A)))
        Small(label)
    }
}

/** v0.407 "Asha typing…" under a chat thread while the other side types. */
@Composable
fun TypingLine(thread: String = "") {
    val who = Live.typingIn(thread)
    if (who.isNotEmpty()) Small("$who ${Strings.isTyping}")
}

/** v0.407 one field of one row, kept live (an order's status on a tracking screen): LiveValue("orders", id, "status"). */
@Composable
fun LiveValue(coll: String, id: String, key: String, modifier: Modifier = Modifier) {
    val r = liveRows(coll).firstOrNull { it.id == id }
    Body(r?.s(key) ?: "", modifier)
}

package hoola.kit

// Made by Hoola App Sahayak (v0.314 ASLI APP). The app's own backend on the business's Hoola server: accounts (the token
// sealed with the phone's Keystore), real saved data and roles. Every write goes into an outbox first, so the app works
// without signal: the outbox is sent in order when the network is back, each write carries its own id (a retry never
// makes a second order), and the rules are checked by the server on every call. Screens never touch the network: they
// use liveRows(), SubmitBtn() and Auth.

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** The code-made sign-in screen and the account screen (my orders / bookings; staff see and handle everyone's). */
const val SCREEN_LOGIN = "hoola_login"
const val SCREEN_ACCOUNT = "hoola_account"

/** One answer from the server: code 0 = no network. */
class Reply(val code: Int, val body: JSONObject) {
    val ok: Boolean get() = code in 200..299
    val offline: Boolean get() = code == 0
    /** Worth sending again later: no network, too many tries, or the server had a bad moment. */
    val retry: Boolean get() = code == 0 || code == 408 || code == 429 || code >= 500
    val error: String get() = body.optString("error", "")
}

object Cloud {
    private var base = ""
    private var key = ""

    fun init(baseUrl: String, appKey: String) {
        base = baseUrl.trimEnd('/')
        key = appKey
    }

    /** Debug builds only (Hoola's emulator test points the app at a test server). */
    fun testServer(baseUrl: String) { base = baseUrl.trimEnd('/') }

    val ready: Boolean get() = key.isNotEmpty() && (base.startsWith("https://") || base.startsWith("http://10.0.2.2"))

    internal suspend fun call(method: String, path: String, body: JSONObject? = null, token: String = ""): Reply =
        withContext(Dispatchers.IO) {
            if (!ready) return@withContext Reply(0, JSONObject())
            var c: HttpURLConnection? = null
            try {
                c = (URL("$base/api/app-api/$key$path").openConnection() as HttpURLConnection).apply {
                    requestMethod = method
                    connectTimeout = 10000
                    readTimeout = 20000
                    instanceFollowRedirects = false
                    useCaches = false
                    setRequestProperty("Accept", "application/json")
                    if (token.isNotEmpty()) setRequestProperty("Authorization", "Bearer $token")
                    if (body != null) {
                        doOutput = true
                        setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    }
                }
                if (body != null) c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                val code = c.responseCode
                val text = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
                val o = try {
                    if (text.isNotBlank() && text.length < 4_000_000) JSONObject(text) else JSONObject()
                } catch (_: Exception) {
                    JSONObject()
                }
                Reply(code, o)
            } catch (_: Exception) {
                Reply(0, JSONObject())
            } finally {
                c?.disconnect()
            }
        }
}

/** AES-GCM with a key that never leaves the phone's Keystore: the sign-in token is stored only in this sealed form. */
internal object Secure {
    private const val ALIAS = "hoola_app_token"

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val g = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        g.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return g.generateKey()
    }

    fun seal(plain: String): String = try {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, key())
        Base64.encodeToString(c.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(c.doFinal(plain.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
    } catch (_: Exception) {
        ""
    }

    fun open(sealed: String): String = try {
        val parts = sealed.split(":", limit = 2)
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)))
        String(c.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8)
    } catch (_: Exception) {
        ""
    }
}

/** Who is using the app. `Auth.signedIn`, `Auth.name`, `Auth.isStaff` (staff / admin accounts handle everyone's rows). */
object Auth {
    val me = mutableStateOf<Item?>(null)
    private var token = ""
    val signedIn: Boolean get() = me.value != null
    val role: String get() = me.value?.s("role", "member") ?: ""
    val isStaff: Boolean get() = role == "staff" || role == "admin"
    val name: String get() = me.value?.let { it.s("name").ifEmpty { it.s("email") } } ?: ""
    internal fun token(): String = token

    fun load(ctx: Context) {
        token = Secure.open(Store.get(ctx, "auth_t"))
        val m = Store.get(ctx, "auth_me")
        me.value = if (token.isNotEmpty() && m.isNotEmpty()) {
            try { Item(JSONObject(m)) } catch (_: Exception) { null }
        } else null
        if (me.value == null) token = ""
    }

    private suspend fun keep(ctx: Context, r: Reply): String? {
        if (!r.ok) return r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain }
        val t = r.body.optString("token", "")
        val m = r.body.optJSONObject("me") ?: return Strings.tryAgain
        if (t.isEmpty()) return Strings.tryAgain
        token = t
        val sealed = Secure.seal(t)
        Store.put(ctx, "auth_t", sealed)            // no Keystore on this phone: signed in until the app closes
        Store.put(ctx, "auth_me", m.toString())
        withContext(Dispatchers.Main) { me.value = Item(m) }
        Db.sync()
        return null
    }

    suspend fun signup(ctx: Context, email: String, password: String, name: String): String? =
        keep(ctx, Cloud.call("POST", "/signup", JSONObject().put("email", email.trim()).put("password", password).put("name", name.trim())))

    suspend fun login(ctx: Context, email: String, password: String): String? =
        keep(ctx, Cloud.call("POST", "/login", JSONObject().put("email", email.trim()).put("password", password)))

    fun logout(ctx: Context) {
        val t = token
        clear(ctx)
        Db.forget()
        if (t.isNotEmpty()) Db.scope.launch { Cloud.call("POST", "/logout", JSONObject(), t) }
    }

    /** In-app account deletion (both stores require it): the server removes the account and everything it made. */
    suspend fun deleteAccount(ctx: Context): String? {
        val r = Cloud.call("POST", "/delete-me", JSONObject(), token)
        if (!r.ok) return r.error.ifEmpty { if (r.offline) Strings.offline else Strings.tryAgain }
        withContext(Dispatchers.Main) {
            clear(ctx)
            Db.forget()
        }
        return null
    }

    internal fun clear(ctx: Context) {
        token = ""
        me.value = null
        Store.put(ctx, "auth_t", "")
        Store.put(ctx, "auth_me", "")
    }
}

/** The app's lists on the server: `liveRows("orders")` on a screen, `Db.create(...)` / `SubmitBtn` to save. */
object Db {
    internal val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val lock = Mutex()
    private val cache = mutableStateMapOf<String, List<Item>>()
    private var outbox = JSONArray()
    private var schema = JSONObject()
    private var app: Context? = null
    /** Writes waiting to reach the server (shown as "Sending" on the rows). */
    val pending = mutableStateOf(0)
    val syncing = mutableStateOf(false)
    val lastError = mutableStateOf("")

    fun load(ctx: Context) {
        app = ctx.applicationContext
        schema = AppData.backend()
        outbox = try { JSONArray(Store.get(ctx, "outbox").ifEmpty { "[]" }) } catch (_: Exception) { JSONArray() }
        pending.value = outbox.length()
        collections().forEach { coll ->
            val s = Store.get(ctx, "rows_$coll")
            if (s.isNotEmpty()) cache[coll] = try { arrList(JSONArray(s)) } catch (_: Exception) { emptyList() }
        }
    }

    /** Sends the outbox the moment the phone gets a network again. */
    fun watch(ctx: Context) {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return
        try {
            cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) { kick() }
            })
        } catch (_: Exception) {
        }
    }

    // ---- the lists this app keeps (from the build; same as the server's)
    fun collections(): List<String> {
        val a = schema.optJSONArray("collections") ?: return emptyList()
        return (0 until a.length()).mapNotNull { a.optJSONObject(it)?.optString("key") }.filter { it.isNotEmpty() }
    }

    private fun collection(coll: String): JSONObject? {
        val a = schema.optJSONArray("collections") ?: return null
        return (0 until a.length()).mapNotNull { a.optJSONObject(it) }.firstOrNull { it.optString("key") == coll }
    }

    fun fields(coll: String): List<Item> = arrList(collection(coll)?.optJSONArray("fields"))
    fun label(coll: String): String = collection(coll)?.optString("label", coll) ?: coll
    fun rule(coll: String, op: String): String = collection(coll)?.optJSONObject("rules")?.optString(op, "") ?: ""
    val orderList: String get() = schema.optString("order", "")
    val signupOpen: Boolean get() = schema.optBoolean("signup", true)

    /** Rows of a list: writes still on their way first (marked pending), then what the server last sent. */
    fun rows(coll: String): List<Item> {
        if (pending.value < 0) return emptyList()       // read: a new pending write re-draws the screen
        val local = synchronized(this) {
            (0 until outbox.length()).mapNotNull { outbox.optJSONObject(it) }
                .filter { it.optString("op") == "create" && it.optString("coll") == coll }
                .map { Item(JSONObject((it.optJSONObject("show") ?: JSONObject()).toString()).put("id", it.optString("cid")).put("pending", true)) }
        }
        return local.reversed() + (cache[coll] ?: emptyList())
    }

    /** Queue a new row. Returns its id on this phone; the server keeps exactly one row for it, however often it is sent. */
    fun create(coll: String, data: Map<String, Any?>, show: Map<String, Any?> = emptyMap()): String {
        val cid = UUID.randomUUID().toString().replace("-", "")
        val d = JSONObject()
        data.forEach { (k, v) -> d.put(k, v ?: JSONObject.NULL) }
        val s = JSONObject(d.toString())
        show.forEach { (k, v) -> s.put(k, v ?: JSONObject.NULL) }
        synchronized(this) {
            outbox.put(JSONObject().put("op", "create").put("coll", coll).put("cid", cid).put("data", d).put("show", s)
                .put("at", System.currentTimeMillis()))
            persist()
        }
        kick()
        return cid
    }

    /** Change a row (a staff account moving an order to "Packed", a user editing their own entry). */
    fun update(coll: String, id: String, data: Map<String, Any?>) {
        val d = JSONObject()
        data.forEach { (k, v) -> d.put(k, v ?: JSONObject.NULL) }
        synchronized(this) {
            outbox.put(JSONObject().put("op", "update").put("coll", coll).put("id", id).put("data", d))
            persist()
        }
        cache[coll] = (cache[coll] ?: emptyList()).map { r ->
            if (r.id == id) Item(JSONObject(r.o.toString()).also { o -> data.forEach { (k, v) -> o.put(k, v ?: JSONObject.NULL) } }) else r
        }
        kick()
    }

    fun kick() { scope.launch { sync() } }

    private fun persist() {
        app?.let { Store.put(it, "outbox", outbox.toString()) }
        pending.value = outbox.length()
    }

    /** Sends the outbox in order. Stops (and tries again later) on no network / a busy server; a refused write is
     *  dropped with the server's reason in lastError. */
    suspend fun sync(): Boolean {
        val ctx = app ?: return false
        if (!lock.tryLock()) return false
        try {
            withContext(Dispatchers.Main) { syncing.value = true }
            while (true) {
                val job = synchronized(this) { outbox.optJSONObject(0) } ?: break
                val coll = job.optString("coll")
                val r = when (job.optString("op")) {
                    "create" -> Cloud.call("POST", "/c/$coll", JSONObject((job.optJSONObject("data") ?: JSONObject()).toString())
                        .put("cid", job.optString("cid")), Auth.token())
                    "update" -> Cloud.call("POST", "/c/$coll/${job.optString("id")}", job.optJSONObject("data") ?: JSONObject(), Auth.token())
                    else -> Reply(400, JSONObject())
                }
                if (r.retry) return false
                if (r.code == 401) {
                    withContext(Dispatchers.Main) {
                        if (Auth.signedIn) Auth.clear(ctx)
                        lastError.value = Strings.loginAgain
                    }
                    return false
                }
                synchronized(this) {
                    if (outbox.length() > 0 && outbox.optJSONObject(0)?.toString() == job.toString()) outbox.remove(0)
                    persist()
                }
                if (r.ok) {
                    upsert(coll, r.body)
                    withContext(Dispatchers.Main) { lastError.value = "" }
                } else {
                    withContext(Dispatchers.Main) { lastError.value = r.error.ifEmpty { Strings.notSaved } }
                }
            }
            return true
        } finally {
            withContext(Dispatchers.Main) { syncing.value = false }
            lock.unlock()
        }
    }

    private suspend fun upsert(coll: String, row: JSONObject) {
        val id = row.optString("id")
        if (id.isEmpty()) return
        val now = listOf(Item(row)) + (cache[coll] ?: emptyList()).filter { it.id != id }
        app?.let { Store.put(it, "rows_$coll", JSONArray(now.map { it.o }).toString()) }
        withContext(Dispatchers.Main) { cache[coll] = now }
    }

    /** Fresh rows from the server (cached for offline use). */
    suspend fun refresh(coll: String): Boolean {
        val r = Cloud.call("GET", "/c/$coll", null, Auth.token())
        if (r.code == 401 && Auth.signedIn) {
            withContext(Dispatchers.Main) { app?.let { Auth.clear(it) } }
            return false
        }
        if (!r.ok) return false
        val a = r.body.optJSONArray("rows") ?: JSONArray()
        app?.let { Store.put(it, "rows_$coll", a.toString()) }
        withContext(Dispatchers.Main) { cache[coll] = arrList(a) }
        return true
    }

    /** Signed out: this account's rows and unsent writes leave the phone. */
    fun forget() {
        synchronized(this) {
            outbox = JSONArray()
            persist()
        }
        collections().forEach { coll -> app?.let { Store.put(it, "rows_$coll", "") } }
        cache.clear()
    }

    /** The form for one list -> a queued row. null = done; "login" = this list needs an account first; else what is wrong. */
    fun submit(coll: String): String? {
        if (collection(coll) == null) return Strings.notSaved
        if (rule(coll, "create") == "member" && !Auth.signedIn) return "login"
        if (rule(coll, "create") == "admin" && !Auth.isStaff) return Strings.staffOnly
        val data = mutableMapOf<String, Any?>()
        val show = mutableMapOf<String, Any?>()
        for (f in fields(coll)) {
            if (f.b("admin_only")) continue
            val k = f.s("key")
            var v = (AppState.form[k] ?: AppState.picks[k] ?: "").trim()
            if (v.isEmpty() && f.s("type") == "choice") v = f.s("default")
            if (v.isEmpty() && f.b("required")) return f.s("label", k) + ": " + Strings.required
            if (v.isNotEmpty()) data[k] = v
        }
        if (coll == orderList) {
            val items = AppState.cartItems("products")
            if (items.isEmpty()) return Strings.cartEmpty
            val cart = JSONArray()
            items.forEach { (it, q) -> cart.put(JSONObject().put("id", it.id).put("qty", q)) }
            data["cart"] = cart
            show["items"] = items.joinToString("\n") { (it, q) -> "$q x ${it.name}" }
            show["total"] = AppState.cartTotal("products")
            show.remove("cart")
        }
        create(coll, data, show)
        fields(coll).forEach { AppState.form.remove(it.s("key")); AppState.picks.remove(it.s("key")) }
        if (coll == orderList) AppState.cart.clear()
        return null
    }
}

/** Rows of one of the app's lists for a screen: cached rows at once (offline too), fresh ones when the server answers. */
@Composable
fun liveRows(coll: String): List<Item> {
    LaunchedEffect(coll, Auth.me.value) { Db.refresh(coll) }
    return Db.rows(coll)
}

/** Saves the form of one list (Field keys = the list's field keys). An order list also takes the cart. Opens the
 *  sign-in screen when the list needs an account; `then` = the screen to open after saving. */
@Composable
fun SubmitBtn(text: String, coll: String, modifier: Modifier = Modifier, then: String = "", icon: String? = null) {
    val nav = LocalNav.current
    val c = ctx()
    Btn(text, modifier = modifier, icon = icon) {
        when (val err = Db.submit(coll)) {
            null -> {
                Act.toast(c, Strings.saved)
                if (then.isNotEmpty()) nav.go(then)
            }
            "login" -> {
                Act.toast(c, Strings.loginFirst)
                nav.go(SCREEN_LOGIN)
            }
            else -> Act.toast(c, err)
        }
    }
}

/** Places the cart as a real order (name / phone / address from the form). Same as SubmitBtn(text, Db.orderList). */
@Composable
fun OrderBtn(text: String, modifier: Modifier = Modifier, then: String = SCREEN_ACCOUNT) {
    SubmitBtn(text, Db.orderList.ifEmpty { "orders" }, modifier, then, "check")
}

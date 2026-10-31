package hoola.kit

// Made by Hoola App Sahayak. The app's data: the business's own facts and lists (made from her Hoola at build time,
// refreshed from her Hoola server when it answers), a cart, the selected record and the form the user is filling.

import android.content.Context
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import org.json.JSONArray
import org.json.JSONObject
import java.text.NumberFormat
import java.util.Locale

/** One record (product, service, slot, order, lead, ticket ...). Reads never throw: a missing key gives "" / 0. */
class Item(val o: JSONObject) {
    val id: String get() = o.optString("id", o.optString("name", ""))
    fun s(key: String, default: String = ""): String = if (o.has(key) && !o.isNull(key)) o.optString(key, default) else default
    fun n(key: String, default: Double = 0.0): Double = if (o.has(key) && !o.isNull(key)) o.optDouble(key, default) else default
    fun i(key: String, default: Int = 0): Int = n(key, default.toDouble()).toInt()
    fun b(key: String): Boolean = o.optBoolean(key, false)
    fun has(key: String): Boolean = o.has(key) && !o.isNull(key) && o.optString(key, "").isNotEmpty()
    fun list(key: String): List<Item> = arrList(o.optJSONArray(key))
    fun strings(key: String): List<String> {
        val a = o.optJSONArray(key) ?: return emptyList()
        return (0 until a.length()).map { a.optString(it) }
    }
    val name: String get() = s("name", s("title", id))
    val price: Double get() = n("price")
}

internal fun arrList(a: JSONArray?): List<Item> {
    if (a == null) return emptyList()
    return (0 until a.length()).mapNotNull { a.optJSONObject(it) }.map { Item(it) }
}

/** The business's data. `AppData.facts` = name, phone, whatsapp, address, hours, upi_id, email, tagline ...
 *  `AppData.list("products")` etc. Lists in the build: whatever the design's screens need. */
object AppData {
    private var root = JSONObject()
    var facts: Item = Item(JSONObject())
        private set
    /** true when some lists are example rows (her own data for them is not in Hoola yet). */
    var demo: Boolean = false
        private set
    val demoLists = mutableSetOf<String>()
    /** Bumped on every new content: the app shell re-draws the screen with it. */
    val version = mutableStateOf(0)

    private var backendJson = JSONObject()

    fun load(ctx: Context) {
        val seed = try { ctx.assets.open("seed.json").bufferedReader().use { it.readText() } } catch (_: Exception) { "{}" }
        backendJson = try { JSONObject(seed).optJSONObject("backend") ?: JSONObject() } catch (_: Exception) { JSONObject() }
        val cached = Store.get(ctx, "content")
        apply(if (cached.isNotEmpty()) cached else seed, fromServer = cached.isNotEmpty())
    }

    /** v0.314 the app's own lists on the server (fields + rules), from the build; a newer server copy wins. */
    fun backend(): JSONObject = backendJson

    fun apply(json: String, fromServer: Boolean = false) {
        root = try { JSONObject(json) } catch (_: Exception) { JSONObject() }
        root.optJSONObject("backend")?.let { if (it.has("collections")) backendJson = it }
        facts = Item(root.optJSONObject("facts") ?: JSONObject())
        demoLists.clear()
        root.optJSONArray("demo_lists")?.let { a -> for (i in 0 until a.length()) demoLists.add(a.optString(i)) }
        demo = demoLists.isNotEmpty() && !fromServer
        version.value = version.value + 1
    }

    fun list(name: String): List<Item> = arrList(root.optJSONObject("lists")?.optJSONArray(name))
    fun byId(name: String, id: String): Item? = list(name).firstOrNull { it.id == id }
    fun search(name: String, q: String): List<Item> {
        val t = q.trim().lowercase()
        if (t.isEmpty()) return list(name)
        return list(name).filter { it.o.toString().lowercase().contains(t) }
    }
    fun categories(name: String): List<String> = list(name).map { it.s("category") }.filter { it.isNotEmpty() }.distinct()
    fun isDemo(name: String): Boolean = name in demoLists
    val appName: String get() = facts.s("name", "App")
}

/** What the user is doing right now: cart, chosen record, filled form fields, chosen chips. Survives screen changes. */
object AppState {
    val cart = mutableStateMapOf<String, Int>()
    val selected = mutableStateMapOf<String, String>()      // list name -> record id
    val form = mutableStateMapOf<String, String>()          // field key -> value
    val picks = mutableStateMapOf<String, String>()         // chip group -> chosen option
    val liked = mutableStateListOf<String>()
    val query = mutableStateOf("")
    val consent = mutableStateOf(false)

    fun add(id: String, qty: Int = 1) { cart[id] = (cart[id] ?: 0) + qty }
    fun setQty(id: String, qty: Int) { if (qty <= 0) cart.remove(id) else cart[id] = qty }
    fun qty(id: String): Int = cart[id] ?: 0
    val cartCount: Int get() = cart.values.sum()
    fun cartItems(list: String = "products"): List<Pair<Item, Int>> =
        cart.mapNotNull { (id, q) -> AppData.byId(list, id)?.let { it to q } }
    fun cartTotal(list: String = "products"): Double = cartItems(list).sumOf { (it, q) -> it.price * q }
    fun select(list: String, id: String) { selected[list] = id }
    fun current(list: String): Item? = selected[list]?.let { AppData.byId(list, it) } ?: AppData.list(list).firstOrNull()
    fun toggleLike(id: String) { if (id in liked) liked.remove(id) else liked.add(id) }
}

/** Rupees the Indian way: ₹1,25,000 */
fun rupees(v: Double, decimals: Boolean = false): String {
    val f = NumberFormat.getCurrencyInstance(Locale.Builder().setLanguage("en").setRegion("IN").build())
    f.maximumFractionDigits = if (decimals || v % 1.0 != 0.0) 2 else 0
    f.minimumFractionDigits = 0
    return f.format(v)
}

/** Small private settings store (no secrets: tokens go through Keystore in the next version). */
object Store {
    private const val FILE = "hoola_app"
    fun get(ctx: Context, key: String): String = ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE).getString(key, "") ?: ""
    fun put(ctx: Context, key: String, value: String) {
        ctx.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(key, value).apply()
    }
}

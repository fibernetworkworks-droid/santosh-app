package hoola.kit

// Made by Hoola App Sahayak (v0.540 JAANCH / DHEERE CHHODO). Feature switches.
//
// A switch lives on the SERVER, not here. The app only reads what it was told, so turning something off reaches every
// phone on its next call - no new build, no store review, no download. That is the only rollback that works in minutes,
// which is why anything risky ships behind one of these.
//
// Who gets a half-rolled-out feature is also decided on the server (a stable hash of the member id), so a user does not
// flip between on and off every time the app restarts, and this app cannot award itself a feature it was not given.

import android.content.Context
import org.json.JSONObject

object Flags {
    @Volatile private var mine = JSONObject()          // what /me said for THIS signed-in person (wins)

    /** The server's answer for this member, kept for the next cold start. */
    fun apply(ctx: Context, o: JSONObject?) {
        if (o == null) return
        mine = o
        Store.put(ctx, "flags", o.toString())
    }

    fun load(ctx: Context) {
        val s = Store.get(ctx, "flags")
        if (s.isNotEmpty()) mine = try { JSONObject(s) } catch (_: Exception) { JSONObject() }
    }

    /** Is this feature on for this phone? Unknown switch = OFF: a feature nobody turned on must not appear. */
    fun on(key: String): Boolean {
        if (mine.has(key)) return mine.optBoolean(key, false)
        val pub = AppData.backend().optJSONObject("flags") ?: return false
        return pub.optBoolean(key, false)
    }

    /** Asks the server again (after a sign-in, and on every start while signed in). */
    suspend fun refresh(ctx: Context) {
        if (Auth.token().isEmpty()) return
        val r = Cloud.call("GET", "/me", null, Auth.token())
        if (r.ok) apply(ctx, r.body.optJSONObject("flags"))
    }
}

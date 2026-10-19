package com.newtika.santosh

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/** Small persistent state shared by the activity, the service and the receivers. */
object Store {
    private fun p(ctx: Context): SharedPreferences = ctx.getSharedPreferences("santosh_native", Context.MODE_PRIVATE)

    fun saveConfig(ctx: Context, server: String, key: String, conv: String, after: Long) {
        val old = p(ctx)
        val e = old.edit().putString("server", server).putString("key", key).putBoolean("enabled", true)
        // a new conversation starts from where the app already is, so old history never pops up as notifications
        if (old.getString("conv", "") != conv || after > old.getLong("last_id", 0)) {
            e.putString("conv", conv).putLong("last_id", after)
        }
        e.apply()
    }

    /** Server + key for push handling (phone-action results), without switching background mode on. */
    fun saveLink(ctx: Context, server: String, key: String) {
        p(ctx).edit().putString("server", server).putString("key", key).apply()
    }

    fun pushToken(ctx: Context) = p(ctx).getString("push_token", "") ?: ""
    fun setPushToken(ctx: Context, t: String) = p(ctx).edit().putString("push_token", t).apply()

    fun server(ctx: Context) = p(ctx).getString("server", "") ?: ""
    fun key(ctx: Context) = p(ctx).getString("key", "") ?: ""
    fun conv(ctx: Context) = p(ctx).getString("conv", "") ?: ""
    fun enabled(ctx: Context) = p(ctx).getBoolean("enabled", false)
    fun setEnabled(ctx: Context, on: Boolean) = p(ctx).edit().putBoolean("enabled", on).apply()
    fun lastId(ctx: Context) = p(ctx).getLong("last_id", 0)
    fun setLastId(ctx: Context, id: Long) = p(ctx).edit().putLong("last_id", id).apply()
    fun status(ctx: Context) = p(ctx).getString("status", "") ?: ""
    fun setStatus(ctx: Context, s: String) = p(ctx).edit().putString("status", s).apply()

    /** First caller wins: stops the app and the service from running the same phone action twice. */
    @Synchronized
    fun claim(ctx: Context, id: String): Boolean {
        if (id.isEmpty()) return false
        val arr = JSONArray(p(ctx).getString("claimed", "[]"))
        for (i in 0 until arr.length()) if (arr.getString(i) == id) return false
        val out = JSONArray()
        val start = if (arr.length() > 300) arr.length() - 300 else 0
        for (i in start until arr.length()) out.put(arr.getString(i))
        out.put(id)
        p(ctx).edit().putString("claimed", out.toString()).commit()
        return true
    }

    // ---- Santosh's own alarms (re-armed after a reboot) ----
    @Synchronized
    fun alarms(ctx: Context): MutableList<JSONObject> {
        val arr = JSONArray(p(ctx).getString("alarms", "[]"))
        return MutableList(arr.length()) { arr.getJSONObject(it) }
    }

    @Synchronized
    fun putAlarm(ctx: Context, a: JSONObject) {
        val list = alarms(ctx).filter { it.optInt("id") != a.optInt("id") }.toMutableList()
        list.add(a)
        p(ctx).edit().putString("alarms", JSONArray(list).toString()).apply()
    }

    @Synchronized
    fun removeAlarm(ctx: Context, id: Int) {
        val list = alarms(ctx).filter { it.optInt("id") != id }
        p(ctx).edit().putString("alarms", JSONArray(list).toString()).apply()
    }
}

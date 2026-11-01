package hoola.kit

// Made by Hoola App Sahayak (v0.367 TURANT). Instant notifications are switched OFF for this app: nothing happens here and
// the app keeps its background check (Updates, every 15 minutes or so). When she switches them on, the build replaces this
// file with the Firebase Cloud Messaging one.

import android.content.Context

object PushHook {
    const val ON = false
    fun start(ctx: Context) {}
    fun signedIn(ctx: Context) {}
}

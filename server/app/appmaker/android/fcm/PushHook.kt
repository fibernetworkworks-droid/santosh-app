package hoola.kit

// Made by Hoola App Sahayak (v0.367 TURANT). Instant notifications through Firebase Cloud Messaging (Google's official push):
// the phone's push token goes to THIS app's own Hoola server (only after sign-in, sealed by the account's token), and a push
// is shown as a normal notification + kept in the app's inbox. Messages carry only a title and a line (no private data
// beyond what the notification shows). The background check (Updates) stays as the safety net.

import android.content.Context
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.json.JSONObject

object PushHook {
    const val ON = true
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** App start: ask Firebase for this phone's token (it may change; onNewToken then sends the new one). */
    fun start(ctx: Context) {
        val app = ctx.applicationContext
        try {
            FirebaseMessaging.getInstance().token.addOnSuccessListener { t -> Store.put(app, "push_token", t); send(app) }
        } catch (_: Exception) {
        }
    }

    /** After a sign-in: the same token now belongs to this account on the app's server. */
    fun signedIn(ctx: Context) = send(ctx.applicationContext)

    internal fun send(ctx: Context) {
        val t = Store.get(ctx, "push_token")
        if (t.isEmpty() || Auth.token().isEmpty() || !Cloud.ready) return
        scope.launch { Cloud.call("POST", "/push-token", JSONObject().put("token", t), Auth.token()) }
    }
}

class HoolaPush : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        Store.put(applicationContext, "push_token", token)
        PushHook.send(applicationContext)
    }

    override fun onMessageReceived(m: RemoteMessage) {
        val title = m.data["title"] ?: m.notification?.title ?: ""
        val text = m.data["body"] ?: m.notification?.body ?: ""
        if (title.isEmpty() && text.isEmpty()) return
        Inbox.add(applicationContext, title.ifEmpty { AppData.appName }, text, java.time.Instant.now().toString())
        Updates.notifyNow(applicationContext, (m.data["id"] ?: (title + text)).hashCode(), title, text)
    }
}

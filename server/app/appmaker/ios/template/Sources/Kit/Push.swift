// Made by Hoola App Sahayak (v0.368 TURANT IPHONE). Instant notifications through Apple's push service (APNs): only when the
// business switched them on (AppTokens.pushOn) and the user allowed notifications. The device token goes to THIS app's own
// Hoola server after sign-in; the server sends with the business's own Apple push key. The background check stays.
import SwiftUI
import UIKit
import UserNotifications

@MainActor
enum PushHub {
    /// After notifications are allowed (and at every start): ask Apple for this device's push token.
    static func start() {
        guard AppTokens.pushOn else { return }
        UNUserNotificationCenter.current().getNotificationSettings { s in
            guard s.authorizationStatus == .authorized || s.authorizationStatus == .provisional else { return }
            DispatchQueue.main.async { UIApplication.shared.registerForRemoteNotifications() }
        }
    }

    /// After a sign-in: the same token now belongs to this account on the app's server.
    static func signedIn() { send() }

    static func got(_ token: Data) {
        UserDefaults.standard.set(token.map { String(format: "%02x", $0) }.joined(), forKey: "hoola_push_token")
        send()
    }

    static func send() {
        guard AppTokens.pushOn, let t = UserDefaults.standard.string(forKey: "hoola_push_token"), !t.isEmpty, Auth.shared.signedIn else { return }
        Task { _ = await Cloud.call("POST", "/push-token", ["token": t, "platform": "ios"], token: Auth.shared.token) }
    }
}

/// UIKit's delegate (SwiftUI adapts it): Apple hands the push token here; a push that arrives while the app is open is
/// shown as a banner and kept in the app's inbox.
final class HoolaAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        if AppTokens.pushOn { UNUserNotificationCenter.current().delegate = self }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { @MainActor in PushHub.got(deviceToken) }
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {}

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        let c = notification.request.content
        Task { @MainActor in Inbox.shared.add(c.title, c.body, ISO8601DateFormatter().string(from: Date())) }
        completionHandler([.banner, .sound])
    }
}

// Made by Hoola App Sahayak (v0.540 JAANCH / DHEERE CHHODO), the iPhone twin of Flags.kt.
//
// A feature switch lives on the SERVER. The app only reads what it was told, so turning something off reaches every
// phone on its next call - no new build, no App Review, no download. On iPhone that matters more than on Android: a
// build takes a review to replace, and a switch does not.
//
// Who gets a half-rolled-out feature is decided on the server too, so this app cannot award itself one.
import Foundation

@MainActor
final class Flags: ObservableObject {
    static let shared = Flags()
    @Published private(set) var mine: [String: Bool] = [:]        // what /me said for THIS signed-in person (wins)

    private init() {
        if let d = UserDefaults.standard.dictionary(forKey: "hoola_flags") as? [String: Bool] {
            mine = d
        }
    }

    func apply(_ o: Any?) {
        guard let d = o as? [String: Any] else { return }
        let m = d.compactMapValues { $0 as? Bool }
        mine = m
        UserDefaults.standard.set(m, forKey: "hoola_flags")
    }

    /// Is this feature on for this phone? An unknown switch is OFF: a feature nobody turned on must not appear.
    static func on(_ key: String) -> Bool {
        if let v = shared.mine[key] { return v }
        let pub = (AppData.shared.backend["flags"] as? [String: Any]) ?? [:]
        return (pub[key] as? Bool) ?? false
    }

    /// Asks the server again (after a sign-in, and on every start while signed in).
    func refresh() async {
        guard !Auth.shared.token.isEmpty else { return }
        let r = await Cloud.call("GET", "/me", nil, token: Auth.shared.token)
        if r.ok { apply(r.body["flags"]) }
    }
}

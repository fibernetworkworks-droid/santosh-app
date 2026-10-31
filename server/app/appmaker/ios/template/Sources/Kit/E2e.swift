// Made by Hoola App Sahayak (v0.332 IPHONE). DEBUG BUILDS ONLY (-hoola_e2e): Hoola's CI drives the app's own backend end to
// end against a real Hoola server on the Mac - the same steps as the Android E2e: sign up, an order through the offline
// outbox (priced by the server), the same write twice = one row, a photo up and back, the UPI "I have paid" claim, the
// updates check, a crash report, sign out (rows leave the phone) and sign in again. Result line in Documents/hoola_e2e.txt.
#if DEBUG
import Foundation
import UIKit

@MainActor
enum E2e {
    private static var lines: [String] = []

    private static func say(_ s: String) {
        lines.append(s)
        let u = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("hoola_e2e.txt")
        try? lines.joined(separator: "\n").appending("\n").write(to: u, atomically: true, encoding: .utf8)
    }

    static func run() async {
        say("HOOLA_E2E start")
        if let why = await steps() { say("HOOLA_E2E FAIL " + why) } else { say("HOOLA_E2E OK") }
    }

    private static func drain() async {
        var tries = 0
        while Db.shared.pending > 0 && tries < 40 {
            await Db.shared.sync()
            try? await Task.sleep(nanoseconds: 500_000_000)
            tries += 1
        }
    }

    private static func steps() async -> String? {
        guard Cloud.ready else { return "cloud not ready (\(Cloud.base))" }
        let email = "ios\(Int(Date().timeIntervalSince1970 * 1000))@example.com"
        if let e = await Auth.shared.signup(email: email, password: "hoola-e2e-pass", name: "E2E iPhone") { return "signup: \(e)" }
        guard Auth.shared.signedIn else { return "not signed in after signup" }
        say("signed up \(email)")
        let db = Db.shared
        let order = db.orderList
        guard !order.isEmpty else { return "no order list in the backend" }
        guard let first = AppData.shared.list("products").first else { return "no products" }
        let st = AppState.shared
        st.cart = [:]
        st.add(first.id, 2)
        st.form["name"] = "E2E iPhone"
        st.form["phone"] = "9876543210"
        st.form["address"] = "12 Test Road, Pune"
        if let e = db.submit(order) { return "submit: \(e)" }
        await drain()
        guard db.pending == 0 else { return "outbox not sent: \(db.lastError)" }
        await db.refresh(order)
        guard let mine = db.rows(order).first(where: { !$0.b("pending") }) else { return "order not on the server" }
        let want = first.price * 2
        if want > 0 && abs(mine.n("total") - want) > 0.01 { return "total \(mine.n("total")) != \(want)" }
        say("order \(mine.id) total \(mine.n("total")) status \(mine.s("status"))")
        // the same write twice (a retry after a lost answer) must give the same row
        let body: [String: Any] = ["cid": "e2eDedup\(Int(Date().timeIntervalSince1970 * 1000))", "name": "E2E iPhone",
                                   "phone": "9876543210", "cart": [["id": first.id, "qty": 1]]]
        let a = await Cloud.call("POST", "/c/\(order)", body, token: Auth.shared.token)
        let b = await Cloud.call("POST", "/c/\(order)", body, token: Auth.shared.token)
        guard a.ok, b.ok else { return "dedup calls failed \(a.code) \(b.code)" }
        guard (a.body["id"] as? String) == (b.body["id"] as? String) else { return "same write made two rows" }
        say("dedup ok")
        // a photo up and back (the server re-encodes it)
        let img = UIGraphicsImageRenderer(size: CGSize(width: 320, height: 240)).image { ctx in
            UIColor(red: 0.8, green: 0.3, blue: 0.15, alpha: 1).setFill()
            ctx.fill(CGRect(x: 0, y: 0, width: 320, height: 240))
        }
        guard let jpg = img.jpegData(compressionQuality: 0.8) else { return "no jpeg" }
        let up = await Cloud.upload(jpg, token: Auth.shared.token)
        let fid = up.body["id"] as? String ?? ""
        guard up.ok, fid.hasPrefix("f_") else { return "photo upload \(up.code) \(up.error)" }
        guard let back = await Cloud.bytes("/files/\(fid)", token: Auth.shared.token), back.count > 100, back.prefix(2) == Data([0xFF, 0xD8])
        else { return "photo not served back as a JPEG" }
        say("photo ok \(fid) \(back.count) bytes")
        db.paid(order, mine.id, utr: "412345678901")
        await drain()
        await db.refresh(order)
        guard let paidRow = db.rows(order).first(where: { $0.id == mine.id }) else { return "order gone after paid" }
        guard paidRow.s("paid") == "Customer says paid", paidRow.s("utr") == "412345678901" else {
            return "paid claim not saved: \(paidRow.s("paid"))"
        }
        say("paid claim ok")
        let upd = await Cloud.call("GET", "/updates", nil, token: Auth.shared.token)
        guard upd.ok, !((upd.body["now"] as? String) ?? "").isEmpty else { return "updates check \(upd.code)" }
        say("updates ok")
        // a crash kept from a "last run" reaches the server (CrashGuard.sendPending)
        UserDefaults.standard.set("SwiftRuntimeError: hoola e2e crash\nscreen: cart\nat hoola.ios $s3App10ScreenCartV4body",
                                  forKey: "hoola_crash_pending")
        await CrashGuard.sendPending()
        guard UserDefaults.standard.string(forKey: "hoola_crash_pending") == nil else { return "crash report not sent" }
        say("crash report ok")
        // signed out: nothing private stays; signed in again: the orders come back
        Auth.shared.logout()
        guard db.rows(order).isEmpty else { return "rows stayed after sign out" }
        if let e = await Auth.shared.login(email: email, password: "hoola-e2e-pass") { return "login: \(e)" }
        await db.refresh(order)
        guard db.rows(order).count >= 2 else { return "rows after login: \(db.rows(order).count)" }
        say("login again ok, \(db.rows(order).count) orders")
        return nil
    }
}
#endif

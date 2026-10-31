// Made by Hoola App Sahayak (v0.332 IPHONE). The app's own backend on the business's Hoola server - the same one the
// Android app uses: accounts (the token in the iPhone Keychain), real saved data, roles. Every write goes into an outbox
// first (works without signal), is sent in order when the network is back, and carries its own id, so a retry never
// makes a second order. The server checks every rule on every call.
import Foundation
import Security
import Network
import UIKit

struct Reply {
    let code: Int
    let body: [String: Any]
    var ok: Bool { (200...299).contains(code) }
    var offline: Bool { code == 0 }
    var retry: Bool { code == 0 || code == 408 || code == 429 || code >= 500 }
    var error: String { body["error"] as? String ?? "" }
}

enum Cloud {
    static var base = ""
    static var key = ""
    static var ready: Bool {
        !key.isEmpty && (base.hasPrefix("https://") || base.hasPrefix("http://127.0.0.1") || base.hasPrefix("http://localhost"))
    }

    static func call(_ method: String, _ path: String, _ body: [String: Any]? = nil, token: String = "") async -> Reply {
        guard ready, let url = URL(string: "\(base)/api/app-api/\(key)\(path)") else { return Reply(code: 0, body: [:]) }
        var req = URLRequest(url: url, timeoutInterval: 20)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if !token.isEmpty { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if let body = body {
            req.httpBody = try? JSONSerialization.data(withJSONObject: body)
            req.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        }
        do {
            let (d, r) = try await URLSession.shared.data(for: req)
            let code = (r as? HTTPURLResponse)?.statusCode ?? 0
            let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] ?? [:]
            return Reply(code: code, body: o)
        } catch {
            return Reply(code: 0, body: [:])
        }
    }

    /// A photo (JPEG bytes) -> {id}.
    static func upload(_ jpeg: Data, token: String) async -> Reply {
        guard ready, let url = URL(string: "\(base)/api/app-api/\(key)/files") else { return Reply(code: 0, body: [:]) }
        var req = URLRequest(url: url, timeoutInterval: 60)
        req.httpMethod = "POST"
        req.setValue("image/jpeg", forHTTPHeaderField: "Content-Type")
        if !token.isEmpty { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        do {
            let (d, r) = try await URLSession.shared.upload(for: req, from: jpeg)
            let o = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] ?? [:]
            return Reply(code: (r as? HTTPURLResponse)?.statusCode ?? 0, body: o)
        } catch {
            return Reply(code: 0, body: [:])
        }
    }

    static func bytes(_ path: String, token: String) async -> Data? {
        guard ready, let url = URL(string: "\(base)/api/app-api/\(key)\(path)") else { return nil }
        var req = URLRequest(url: url, timeoutInterval: 30)
        if !token.isEmpty { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        guard let (d, r) = try? await URLSession.shared.data(for: req), (r as? HTTPURLResponse)?.statusCode == 200 else { return nil }
        return d
    }
}

/// The sign-in token lives only in the iPhone Keychain (this device, after first unlock).
enum Keychain {
    private static let service = "hoola.app"

    static func set(_ value: String, _ account: String) {
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                kSecAttrAccount as String: account]
        SecItemDelete(q as CFDictionary)
        if value.isEmpty { return }
        var add = q
        add[kSecValueData as String] = Data(value.utf8)
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(add as CFDictionary, nil)
    }

    static func get(_ account: String) -> String {
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                kSecAttrAccount as String: account, kSecReturnData as String: true,
                                kSecMatchLimit as String: kSecMatchLimitOne]
        var out: AnyObject?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? Data else { return "" }
        return String(data: d, encoding: .utf8) ?? ""
    }
}

@MainActor
final class Auth: ObservableObject {
    static let shared = Auth()
    @Published var me: Item?
    private(set) var token = ""
    var signedIn: Bool { me != nil }
    var role: String { me?.s("role", "member") ?? "" }
    var isStaff: Bool { role == "staff" || role == "admin" }
    var name: String { guard let m = me else { return "" }; let n = m.s("name"); return n.isEmpty ? m.s("email") : n }

    func load() {
        token = Keychain.get("token")
        if !token.isEmpty, let d = UserDefaults.standard.data(forKey: "hoola_me"),
           let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
            me = Item(o: o)
        } else {
            token = ""
            me = nil
        }
    }

    private func keep(_ r: Reply) async -> String? {
        if !r.ok { return r.error.isEmpty ? (r.offline ? Words.offline : Words.tryAgain) : r.error }
        guard let t = r.body["token"] as? String, !t.isEmpty, let m = r.body["me"] as? [String: Any] else { return Words.tryAgain }
        token = t
        Keychain.set(t, "token")
        if let d = try? JSONSerialization.data(withJSONObject: m) { UserDefaults.standard.set(d, forKey: "hoola_me") }
        me = Item(o: m)
        await Db.shared.sync()
        return nil
    }

    func signup(email: String, password: String, name: String) async -> String? {
        await keep(await Cloud.call("POST", "/signup", ["email": email.trimmingCharacters(in: .whitespaces), "password": password,
                                                        "name": name.trimmingCharacters(in: .whitespaces)]))
    }

    func login(email: String, password: String) async -> String? {
        await keep(await Cloud.call("POST", "/login", ["email": email.trimmingCharacters(in: .whitespaces), "password": password]))
    }

    func logout() {
        let t = token
        clear()
        Db.shared.forget()
        if !t.isEmpty { Task { _ = await Cloud.call("POST", "/logout", [:], token: t) } }
    }

    /// In-app account deletion (App Store rule): the server removes the account and everything it made.
    func deleteAccount() async -> String? {
        let r = await Cloud.call("POST", "/delete-me", [:], token: token)
        if !r.ok { return r.error.isEmpty ? (r.offline ? Words.offline : Words.tryAgain) : r.error }
        clear()
        Db.shared.forget()
        return nil
    }

    func clear() {
        token = ""
        me = nil
        Keychain.set("", "token")
        UserDefaults.standard.removeObject(forKey: "hoola_me")
    }
}

@MainActor
final class Db: ObservableObject {
    static let shared = Db()
    @Published private(set) var cache: [String: [Item]] = [:]
    @Published private(set) var pending = 0
    @Published var lastError = ""
    private var outbox: [[String: Any]] = []
    private var schema: [String: Any] { AppData.shared.backend }
    private var syncing = false
    private let monitor = NWPathMonitor()

    func load() {
        if let d = UserDefaults.standard.data(forKey: "hoola_outbox"),
           let a = try? JSONSerialization.jsonObject(with: d) as? [[String: Any]] {
            outbox = a
        }
        pending = outbox.count
        for c in collections() {
            if let d = UserDefaults.standard.data(forKey: "hoola_rows_\(c)"),
               let a = try? JSONSerialization.jsonObject(with: d) { cache[c] = items(a) }
        }
        monitor.pathUpdateHandler = { path in
            if path.status == .satisfied { Task { @MainActor in await Db.shared.sync() } }
        }
        monitor.start(queue: DispatchQueue(label: "hoola.net"))
    }

    // the lists this app keeps (from the build / a newer server copy)
    private var colls: [[String: Any]] { (schema["collections"] as? [Any])?.compactMap { $0 as? [String: Any] } ?? [] }
    func collections() -> [String] { colls.compactMap { $0["key"] as? String } }
    private func collection(_ c: String) -> [String: Any]? { colls.first { ($0["key"] as? String) == c } }
    /// The business hid a field: it leaves the forms (its data stays on the server).
    func fields(_ c: String) -> [Item] { items(collection(c)?["fields"]).filter { !$0.b("hidden") } }
    func label(_ c: String) -> String { collection(c)?["label"] as? String ?? c }
    func rule(_ c: String, _ op: String) -> String { (collection(c)?["rules"] as? [String: Any])?[op] as? String ?? "" }
    var orderList: String { schema["order"] as? String ?? "" }

    /// Writes still on their way first (marked pending), then what the server last sent.
    func rows(_ c: String) -> [Item] {
        let local = outbox.filter { ($0["op"] as? String) == "create" && ($0["coll"] as? String) == c }.map { job -> Item in
            var o = job["show"] as? [String: Any] ?? [:]
            o["id"] = job["cid"]
            o["pending"] = true
            return Item(o: o)
        }
        return local.reversed() + (cache[c] ?? [])
    }

    private func persist() {
        if let d = try? JSONSerialization.data(withJSONObject: outbox) { UserDefaults.standard.set(d, forKey: "hoola_outbox") }
        pending = outbox.count
    }

    @discardableResult
    func create(_ c: String, _ data: [String: Any], show: [String: Any] = [:]) -> String {
        let cid = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        var s = data
        for (k, v) in show { s[k] = v }
        outbox.append(["op": "create", "coll": c, "cid": cid, "data": data, "show": s])
        persist()
        Task { await sync() }
        return cid
    }

    func update(_ c: String, _ id: String, _ data: [String: Any]) {
        outbox.append(["op": "update", "coll": c, "id": id, "data": data])
        persist()
        cache[c] = (cache[c] ?? []).map { r in
            guard r.id == id else { return r }
            var o = r.o
            for (k, v) in data { o[k] = v }
            return Item(o: o)
        }
        Task { await sync() }
    }

    func paid(_ c: String, _ id: String, utr: String) {
        outbox.append(["op": "paid", "coll": c, "id": id, "data": ["utr": utr]])
        persist()
        Task { await sync() }
    }

    /// Sends the outbox in order; stops on no network / a busy server (tried again later); a refused write is dropped with
    /// the server's reason in lastError.
    func sync() async {
        if syncing { return }
        syncing = true
        defer { syncing = false }
        while var job = outbox.first {
            let c = job["coll"] as? String ?? ""
            if var data = job["data"] as? [String: Any] {          // photos picked on this phone go up first
                for (k, v) in data {
                    guard let s = v as? String, s.hasPrefix("local:") else { continue }
                    let path = String(s.dropFirst(6))
                    guard let jpeg = FileManager.default.contents(atPath: path) else { data.removeValue(forKey: k); continue }
                    let up = await Cloud.upload(jpeg, token: Auth.shared.token)
                    if up.retry { return }
                    if up.code == 401 { Auth.shared.clear(); lastError = Words.loginAgain; return }
                    if up.ok, let fid = up.body["id"] as? String {
                        data[k] = fid
                        try? FileManager.default.removeItem(atPath: path)
                    } else {
                        data.removeValue(forKey: k)
                    }
                }
                job["data"] = data
                outbox[0] = job
                persist()
            }
            let data = job["data"] as? [String: Any] ?? [:]
            let id = job["id"] as? String ?? ""
            let r: Reply
            switch job["op"] as? String ?? "" {
            case "create":
                var d = data
                d["cid"] = job["cid"]
                r = await Cloud.call("POST", "/c/\(c)", d, token: Auth.shared.token)
            case "update":
                r = await Cloud.call("POST", "/c/\(c)/\(id)", data, token: Auth.shared.token)
            case "paid":
                r = await Cloud.call("POST", "/c/\(c)/\(id)/paid", data, token: Auth.shared.token)
            default:
                r = Reply(code: 400, body: [:])
            }
            if r.retry { return }
            if r.code == 401 {
                if Auth.shared.signedIn { Auth.shared.clear() }
                lastError = Words.loginAgain
                return
            }
            if !outbox.isEmpty { outbox.removeFirst() }
            persist()
            if r.ok { upsert(c, r.body); lastError = "" } else { lastError = r.error.isEmpty ? Words.notSaved : r.error }
        }
    }

    private func upsert(_ c: String, _ row: [String: Any]) {
        guard let id = row["id"] as? String, !id.isEmpty else { return }
        let now = [Item(o: row)] + (cache[c] ?? []).filter { $0.id != id }
        cache[c] = now
        if let d = try? JSONSerialization.data(withJSONObject: now.map { $0.o }) { UserDefaults.standard.set(d, forKey: "hoola_rows_\(c)") }
    }

    /// Fresh rows from the server (cached for offline use).
    func refresh(_ c: String) async {
        let r = await Cloud.call("GET", "/c/\(c)", nil, token: Auth.shared.token)
        if r.code == 401 && Auth.shared.signedIn { Auth.shared.clear(); return }
        guard r.ok else { return }
        let a = r.body["rows"] ?? []
        cache[c] = items(a)
        if let d = try? JSONSerialization.data(withJSONObject: a) { UserDefaults.standard.set(d, forKey: "hoola_rows_\(c)") }
    }

    /// Signed out: this account's rows and unsent writes leave the phone.
    func forget() {
        outbox = []
        persist()
        for c in collections() { UserDefaults.standard.removeObject(forKey: "hoola_rows_\(c)") }
        cache = [:]
    }

    /// The form for one list -> a queued row. nil = done; "login" = sign in first; else what is wrong.
    func submit(_ c: String) -> String? {
        guard collection(c) != nil else { return Words.notSaved }
        if rule(c, "create") == "member" && !Auth.shared.signedIn { return "login" }
        if rule(c, "create") == "admin" && !Auth.shared.isStaff { return Words.staffOnly }
        let st = AppState.shared
        var data: [String: Any] = [:]
        var show: [String: Any] = [:]
        for f in fields(c) where !f.b("admin_only") {
            let k = f.s("key")
            var v = (st.form[k] ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            if v.isEmpty && f.s("type") == "choice" { v = f.s("default") }
            if v.isEmpty && f.b("required") { return f.s("label", k) + ": " + Words.required }
            if !v.isEmpty { data[k] = v }
        }
        if c == orderList {
            let lines = st.cartItems()
            if lines.isEmpty { return Words.cartEmpty }
            data["cart"] = lines.map { ["id": $0.0.id, "qty": $0.1] }
            show["items"] = lines.map { "\($0.1) x \($0.0.name)" }.joined(separator: "\n")
            show["total"] = st.cartTotal()
        }
        create(c, data, show: show)
        for f in fields(c) { st.form.removeValue(forKey: f.s("key")) }
        if c == orderList { st.cart = [:] }
        return nil
    }
}

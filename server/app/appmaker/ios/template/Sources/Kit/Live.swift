// Made by Hoola App Sahayak (v0.407 ABHI ABHI). Real time: while the app is open and signed in, ONE live stream from the
// business's Hoola server tells this iPhone the moment something it may see changes - a list row (its own order's status,
// a new order for staff), a chat message, who is online, who is typing. The server filters every event with the list's own
// rules. Live never writes: saving still goes through the offline outbox, and a changed list is simply loaded again (the
// screen always shows what the server says). No network / too many people / an old server = the app keeps its normal
// refresh; a dropped stream reconnects and the server replays what was missed (Last-Event-ID).
import Foundation
import SwiftUI

@MainActor
final class Live: ObservableObject {
    static let shared = Live()
    /// The stream is open right now.
    @Published private(set) var connected = false
    /// Goes up by one on every chat message this account may see (the chat screen loads again at once).
    @Published private(set) var chatTick = 0
    /// Goes up on every change to a list (RowsSection reloads that list).
    @Published private(set) var rev: [String: Int] = [:]
    /// Who is online: key -> (first name, staff?). Customers only ever see the shop's staff.
    @Published private(set) var online: [String: (String, Bool)] = [:]
    @Published private(set) var typing: [String: (String, Date)] = [:]
    @Published private(set) var clock = Date()

    private var task: Task<Void, Never>? = nil
    private var ticker: Task<Void, Never>? = nil
    private var lastId = ""
    private var dirty = Set<String>()
    private var flushing = false
    private var lastTyping = Date.distantPast

    var staffOnline: Bool { online.values.contains { $0.1 } }

    func revOf(_ coll: String) -> Int { rev[coll] ?? 0 }

    /// Someone typing in this thread right now ("" = the customer's own thread with the shop).
    func typingIn(_ thread: String) -> String {
        let key = thread.isEmpty ? (Auth.shared.me?.id ?? "") : thread
        guard let t = typing[key], t.1 > clock else { return "" }
        return t.0
    }

    /// The app came to the front. Safe to call again.
    func start() {
        guard task == nil else { return }
        task = Task { await loop() }
        ticker = Task {
            while !Task.isCancelled {
                clock = Date()
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }

    /// The app went to the back: the stream closes (push covers the background).
    func stop() {
        task?.cancel(); task = nil
        ticker?.cancel(); ticker = nil
        connected = false
        online = [:]
        typing = [:]
    }

    /// "typing…" for the other side (one signal every 3 s). thread = the customer's id (staff); "" = own thread.
    func typingNow(_ thread: String = "") {
        guard Auth.shared.signedIn, Date().timeIntervalSince(lastTyping) > 3 else { return }
        lastTyping = Date()
        Task { _ = await Cloud.call("POST", "/live/typing", ["thread": thread], token: Auth.shared.token) }
    }

    private func loop() async {
        var wait: UInt64 = 1
        while !Task.isCancelled {
            guard Auth.shared.signedIn, Cloud.ready, !Auth.shared.token.isEmpty,
                  let url = URL(string: "\(Cloud.base)/api/app-api/\(Cloud.key)/live") else {
                try? await Task.sleep(nanoseconds: 5_000_000_000); continue
            }
            var req = URLRequest(url: url, timeoutInterval: 40)     // a ping every 15 s; 40 s of silence = a dead socket
            req.setValue("text/event-stream", forHTTPHeaderField: "Accept")
            req.setValue("Bearer \(Auth.shared.token)", forHTTPHeaderField: "Authorization")
            if !lastId.isEmpty { req.setValue(lastId, forHTTPHeaderField: "Last-Event-ID") }
            var code = 0
            do {
                let (bytes, resp) = try await URLSession.shared.bytes(for: req)
                code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                if code == 200 {
                    connected = true
                    wait = 1
                    var id = ""
                    for try await line in bytes.lines {
                        if Task.isCancelled { break }
                        if line.hasPrefix("id:") {
                            id = line.dropFirst(3).trimmingCharacters(in: .whitespaces)
                        } else if line.hasPrefix("data:") {
                            let raw = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                            if let d = raw.data(using: .utf8), let e = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] {
                                await handle(e)
                            }
                            if !id.isEmpty { lastId = id }
                            id = ""
                        }
                    }
                }
            } catch {}
            connected = false
            if Task.isCancelled { break }
            let pause: UInt64
            switch code {
            case 401: pause = 30           // signed out elsewhere: the next screen load says so
            case 404: pause = 600          // an older server without live: plain refresh only
            case 429: pause = 60           // too many people right now
            default: pause = wait; wait = min(wait * 2, 30)
            }
            try? await Task.sleep(nanoseconds: pause * 1_000_000_000)
        }
    }

    private func handle(_ e: [String: Any]) async {
        let s = { (k: String) -> String in e[k] as? String ?? "" }
        switch s("type") {
        case "hello": if lastId.isEmpty { await reloadAll() }
        case "row": changed(s("coll"))
        case "reset": await reloadAll()
        case "chat":
            chatTick += 1
            typing[s("thread")] = nil
        case "typing":
            typing[s("thread")] = (s("name"), Date().addingTimeInterval(6))
        case "pos": Track.shared.onPos(e)                   // v0.412 NAKSHA LIVE
        case "presence":
            if e["online"] as? Bool == true { online[s("member")] = (s("name"), e["staff"] as? Bool ?? false) } else { online[s("member")] = nil }
        default: break
        }
    }

    private func reloadAll() async {
        for c in Db.shared.collections() { changed(c) }
        chatTick += 1
        let p = await Cloud.call("GET", "/live/presence", nil, token: Auth.shared.token)
        if p.ok {
            var on: [String: (String, Bool)] = [:]
            for x in items(p.body["online"]) { on[x.s("member")] = (x.s("name"), x.b("staff")) }
            online = on
        }
    }

    /// Many changes in a burst = one reload per list (a quarter second later).
    private func changed(_ coll: String) {
        guard !coll.isEmpty else { return }
        dirty.insert(coll)
        guard !flushing else { return }
        flushing = true
        Task {
            try? await Task.sleep(nanoseconds: 250_000_000)
            for c in dirty { rev[c] = (rev[c] ?? 0) + 1 }
            dirty.removeAll()
            flushing = false
        }
    }
}

/// v0.407 a small green dot + "Shop is online" (customers) / how many are online (staff), only while the stream is open.
struct LiveDot: View {
    @ObservedObject private var live = Live.shared
    @ObservedObject private var auth = Auth.shared
    init() {}
    var body: some View {
        if live.connected {
            HStack(spacing: 6) {
                Circle().fill(Color(red: 0.12, green: 0.62, blue: 0.35)).frame(width: 8, height: 8)
                Muted(auth.isStaff ? "\(live.online.count) \(Words.isOnline)" : (live.staffOnline ? Words.shopOnline : Words.live))
            }
        }
    }
}

/// v0.407 "Asha typing…" under a chat thread while the other side types.
struct TypingLine: View {
    let thread: String
    @ObservedObject private var live = Live.shared
    init(thread: String = "") { self.thread = thread }
    var body: some View {
        let who = live.typingIn(thread)
        if !who.isEmpty { Muted("\(who) \(Words.isTyping)") }
    }
}

// Made by Hoola App Sahayak (v0.417 PAISA), the iPhone twin of the Android kit's Pay.kt. Online payment through the
// business's OWN gateway, only when it joined one: "Pay online" asks the server to start a payment for the SERVER's total
// and opens the gateway's own secure page. This app never sees a card, UPI PIN or bank detail and never decides that an
// order is paid - the server marks it paid only when the GATEWAY says so. AutoPay: the customer starts a plan and approves
// the mandate on the gateway's page; she can cancel any time here.
import SwiftUI

enum Pay {
    @MainActor static var cfg: [String: Any]? {
        guard let p = AppData.shared.backend["pay"] as? [String: Any], p["on"] as? Bool == true else { return nil }
        return p
    }
    @MainActor static var on: Bool { cfg != nil }
    @MainActor static var plansOn: Bool { cfg?["plans"] as? Bool == true }

    /// nil = the gateway's page opened; else what went wrong.
    @MainActor static func start(_ coll: String, _ id: String) async -> String? {
        let r = await Cloud.call("POST", "/pay/c/\(coll)/\(id)/start", [:], token: Auth.shared.token)
        guard r.ok, let path = r.body["path"] as? String, !path.isEmpty else {
            return r.error.isEmpty ? (r.offline ? Words.offline : Words.tryAgain) : r.error
        }
        openLink(Cloud.base + path)
        return nil
    }
}

/// On the customer's own unpaid order: "Pay online", then waits for the gateway's word (the live stream also tells us).
struct PayButton: View {
    let coll: String
    let r: Item
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var db = Db.shared
    @State private var busy = false
    @State private var waiting = false
    @State private var error = ""

    var body: some View {
        if Pay.on && !auth.isStaff && coll == db.orderList && !r.b("pending") && r.s("paid") != "Verified"
            && !["Cancelled", "Rejected"].contains(r.s("status")) && r.n("total") >= 1 {
            VStack(alignment: .leading, spacing: 6) {
                Button(busy ? Words.opening : Words.payOnline + " " + rupees(r.n("total"))) {
                    guard !busy else { return }
                    busy = true
                    Task {
                        let err = await Pay.start(coll, r.id)
                        busy = false
                        if let e = err { error = e } else { error = ""; waiting = true }
                    }
                }.buttonStyle(.borderedProminent)
                if waiting { Muted(Words.payWaiting) }
                if !error.isEmpty { Text(error).foregroundStyle(.red).font(.subheadline) }
            }
            .task(id: waiting) {
                guard waiting else { return }
                for _ in 0..<20 {
                    try? await Task.sleep(nanoseconds: 6_000_000_000)
                    let s = await Cloud.call("GET", "/pay/c/\(coll)/\(r.id)", nil, token: auth.token)
                    if s.ok && s.body["paid"] as? Bool == true { await db.refresh(coll); waiting = false; return }
                }
                waiting = false
            }
        }
    }
}

/// AutoPay plans the business offers + this customer's own subscriptions with Cancel.
struct PlansBlock: View {
    @ObservedObject private var auth = Auth.shared
    @State private var plans: [Item] = []
    @State private var subs: [Item] = []
    @State private var tick = 0
    @State private var note = ""
    init() {}

    var body: some View {
        if Pay.plansOn && auth.signedIn && !auth.isStaff {
            VStack(alignment: .leading, spacing: 8) {
                Text(Words.autoPay).font(.headline)
                ForEach(subs.filter { !["cancelled", "completed", "created"].contains($0.s("status")) }, id: \.id) { s in
                    Card {
                        Text(s.s("plan") + " · " + s.s("amount_rs") + " / " + T(s.s("period")))
                        Muted(Words.autoPayOn + " · \(Int(s.n("charges"))) " + Words.charged)
                        Button(Words.cancelAutoPay) {
                            Task {
                                let r = await Cloud.call("POST", "/pay/subs/\(s.s("id"))/cancel", [:], token: auth.token)
                                note = r.ok ? Words.autoPayOff : (r.error.isEmpty ? Words.tryAgain : r.error)
                                tick += 1
                            }
                        }.buttonStyle(.bordered)
                    }
                }
                ForEach(plans, id: \.id) { p in
                    Card {
                        Text(p.s("name") + " · " + p.s("amount_rs") + " / " + T(p.s("period")))
                        Muted(Words.autoPayWhy.replacingOccurrences(of: "{n}", with: "\(Int(p.n("count")))"))
                        MainButton(text: Words.startAutoPay, tonal: true) {
                            Task {
                                let r = await Cloud.call("POST", "/pay/plans/\(p.s("key"))/subscribe", [:], token: auth.token)
                                if r.ok, let path = r.body["path"] as? String, !path.isEmpty { openLink(Cloud.base + path) }
                                else { note = r.error.isEmpty ? Words.tryAgain : r.error }
                                tick += 1
                            }
                        }
                    }
                }
                if !note.isEmpty { Muted(note) }
            }
            .task(id: "\(tick)#\(auth.me?.id ?? "")") {
                let p = await Cloud.call("GET", "/pay/plans", nil, token: auth.token)
                if p.ok { plans = items(p.body["plans"]).map { x in var o = x.o; o["id"] = x.s("key"); return Item(o: o) } }
                let s = await Cloud.call("GET", "/pay/subs", nil, token: auth.token)
                if s.ok { subs = items(s.body["subs"]) }
            }
        }
    }
}

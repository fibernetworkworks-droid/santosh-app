// Made by Hoola App Sahayak (v0.435 PARIVAAR), the iPhone twin of Partner.kt: the jobs screen of a delivery partner
// (rider) app or a partner shop app. Everything comes from the server (/partner/jobs) - which jobs, how much of each,
// which steps are allowed, whether a job can still be taken; this view only shows it and sends the taps.
import SwiftUI

enum Partner {
    /// "rider" / "vendor" in a partner app's build, "" in every other app.
    @MainActor static var kind: String { AppData.shared.backend["partner"] as? String ?? "" }
}

struct PartnerScreen: View {
    var body: some View {
        Page(Words.ptJobs) { PartnerJobsBlock() }
    }
}

struct PartnerJobsBlock: View {
    @ObservedObject private var auth = Auth.shared
    @State private var data: Item? = nil
    @State private var busy = ""
    @State private var tick = 0
    @State private var note = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            content
            if !note.isEmpty { Text(note).font(.subheadline).foregroundStyle(.red) }
        }
        .task(id: "\(auth.me?.id ?? "")#\(tick)") {
            let r = await Cloud.call("GET", "/partner/jobs", nil, token: auth.token)
            data = r.ok ? Item(o: r.body) : Item(o: ["state": "error", "error": r.offline ? Words.offline : (r.error.isEmpty ? Words.tryAgain : r.error)])
        }
    }

    @ViewBuilder private var content: some View {
        let st = data?.s("state") ?? ""
        if data == nil {
            Muted(Words.loading)
        } else if auth.me == nil || st == "login" {
            Muted(Words.ptLoginWhy)
            MainButton(text: Words.signIn) { Router.shared.go("hoola_login") }
        } else if st == "error" {
            Muted(data?.s("error") ?? Words.tryAgain)
            MainButton(text: Words.ptRetry, tonal: true) { tick += 1 }
        } else if st == "waiting" {
            Text(Words.ptWaiting).font(.headline)
            Muted(Words.ptWaitingWhy)
            MainButton(text: Words.ptRefresh, tonal: true) { tick += 1 }
        } else if st != "active" {
            Text(Words.ptApply).font(.headline)
            Muted(Words.ptApplyWhy)
            if data?.b("can_request") == true {
                MainButton(text: Words.ptApplyBtn) { send("apply", "/partner/request", [:]) }
            }
        } else if let d = data {
            active(d)
        }
    }

    @ViewBuilder private func active(_ d: Item) -> some View {
        let mine = items(d.o["mine"])
        let offers = items(d.o["offers"])
        let done = items(d.o["done"])
        if d.has("shop") { Text(d.s("shop")).font(.title3.weight(.semibold)) }
        if d.s("kind") == "rider" { ShiftBlock() }
        HStack {
            Text(Words.ptMine + " (\(mine.count))").font(.headline)
            Spacer()
            Button(Words.ptRefresh) { tick += 1 }.buttonStyle(.borderless)
        }
        if mine.isEmpty { Muted(Words.ptNone) }
        ForEach(mine, id: \.id) { j in JobCard(j: j, busy: busy, send: send) }
        if d.s("kind") == "rider" {
            Text(Words.ptNew + " (\(offers.count))").font(.headline)
            if offers.isEmpty { Muted(Words.ptNoOffers) }
            ForEach(offers, id: \.id) { j in JobCard(j: j, busy: busy, send: send) }
        }
        if !done.isEmpty {
            Text(Words.ptPast).font(.headline)
            ForEach(done.prefix(10), id: \.id) { j in
                HStack { Text(j.s("title")); Spacer(); Muted(j.s("status")) }
            }
        }
    }

    private func send(_ id: String, _ path: String, _ body: [String: Any]) {
        guard busy.isEmpty else { return }
        busy = id
        note = ""
        Task {
            let r = await Cloud.call("POST", path, body, token: auth.token)
            busy = ""
            if !r.ok { note = r.error.isEmpty ? (r.offline ? Words.offline : Words.tryAgain) : r.error }
            tick += 1
        }
    }
}

private struct JobCard: View {
    let j: Item
    let busy: String
    let send: (String, String, [String: Any]) -> Void

    var body: some View {
        Card {
            HStack(alignment: .top) {
                Text(j.s("title")).font(.headline)
                Spacer()
                if j.has("status") { StatusPill(text: T(j.s("status"))) }
            }
            ForEach(j.strings("lines"), id: \.self) { Muted($0) }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    if j.b("take") {
                        Button(busy == j.id ? Words.opening : Words.ptTake) { send(j.id, "/partner/jobs/\(j.id)/take", [:]) }
                            .buttonStyle(.borderedProminent).disabled(!busy.isEmpty)
                    }
                    ForEach(j.strings("steps"), id: \.self) { st in
                        Button(T(st)) { send(j.id, "/partner/jobs/\(j.id)/step", ["status": st]) }
                            .buttonStyle(.bordered).disabled(!busy.isEmpty)
                    }
                    if j.has("phone") {
                        Button(Words.call) { openLink("tel:" + j.s("phone").filter { $0.isNumber || $0 == "+" }) }.buttonStyle(.bordered)
                    }
                    if j.has("lat") && j.has("lng") {
                        Button(Words.ptRoute) { openLink("http://maps.apple.com/?daddr=\(j.n("lat")),\(j.n("lng"))") }.buttonStyle(.bordered)
                    } else if j.has("address") {
                        Button(Words.ptRoute) {
                            openLink("http://maps.apple.com/?daddr=" + (j.s("address").addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""))
                        }.buttonStyle(.bordered)
                    }
                }
            }
        }
    }
}

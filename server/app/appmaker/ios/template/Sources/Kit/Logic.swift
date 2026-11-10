// Made by Hoola App Sahayak. v0.382 DIMAAG: the app's own logic on the iPhone - the SERVER decides every rule; these
// pieces only show what it says: linked rows (a picker + the parent's name), the workflow buttons this account may
// press, an approval waiting (+ Approve / Reject when it is this account's turn), a row's linked children with "Add".
import SwiftUI

enum Logic {
    /// The name of a linked row as the server sent it.
    static func refLabel(_ r: Item, _ key: String) -> String { (r.o["_labels"] as? [String: Any])?[key] as? String ?? "" }

    @MainActor static func title(_ coll: String, _ r: Item) -> String {
        let lf = Db.shared.labelField(coll)
        if !lf.isEmpty && r.has(lf) { let l = refLabel(r, lf); return l.isEmpty ? r.s(lf) : l }
        let f = Db.shared.fields(coll).first { ["text", "long_text", "phone", "email"].contains($0.s("type")) && r.has($0.s("key")) }
        return f.map { r.s($0.s("key")) } ?? Db.shared.label(coll)
    }

    /// A value for showing: a link shows its row's name, never the id.
    static func show(_ r: Item, _ f: Item) -> String {
        if f.s("type") == "ref" { let l = refLabel(r, f.s("key")); return l.isEmpty ? r.s(f.s("key")) : l }
        return r.s(f.s("key"))
    }

    /// A function she marked callable (a price / EMI calculator) - runs on the server in its locked box.
    static func call(_ name: String, _ args: [Any]) async -> String {
        let r = await Cloud.call("POST", "/fn/\(name)", ["args": args], token: Auth.shared.token)
        if r.ok, let v = r.body["result"] { return "\(v)" }
        return r.error.isEmpty ? Words.tryAgain : r.error
    }
}

/// Pick a row of another list (customer for an invoice). The id travels; the name shows.
struct RefField: View {
    let label: String
    let to: String
    @Binding var value: String
    @ObservedObject private var db = Db.shared
    @State private var open = false
    @State private var q = ""

    var body: some View {
        let rows = db.rows(to)
        let name = rows.first { $0.id == value }.map { Logic.title(to, $0) } ?? ""
        VStack(alignment: .leading, spacing: 6) {
            Muted(T(label))
            Button(name.isEmpty ? Words.choose + " " + T(db.label(to)) : name) { open.toggle() }.buttonStyle(.bordered)
            if open {
                if rows.count > 6 { TextField(Words.search, text: $q).textFieldStyle(.roundedBorder) }
                ForEach(rows.filter { q.isEmpty || Logic.title(to, $0).lowercased().contains(q.lowercased()) }.prefix(40), id: \.id) { r in
                    Button { value = r.id; open = false } label: {
                        HStack { Text(Logic.title(to, r)); Spacer(); if r.id == value { Image(systemName: "checkmark") } }
                    }
                }
                if rows.isEmpty { Muted(Words.nothingYet) }
            }
        }
        .task { await db.refresh(to) }
    }
}

/// The workflow on a row card: an approval waiting (+ Approve / Reject for this account's turn), else the allowed steps.
struct WorkflowBox: View {
    let coll: String
    let r: Item
    @State private var note = ""
    @State private var busy = false
    @State private var said = ""

    var body: some View {
        if !r.b("pending") {
            if let p = r.o["_pending"] as? [String: Any] {
                let pi = Item(o: p)
                VStack(alignment: .leading, spacing: 6) {
                    StatusPill(text: T(pi.s("label")) + " · " + Words.needsApproval + " (\(Words.step) \(pi.s("step"))/\(pi.s("of")))")
                    Muted(Words.waitingFor + ": " + T(pi.s("waiting_for")))
                    if pi.b("can_decide") {
                        TextField(Words.note, text: $note).textFieldStyle(.roundedBorder)
                        HStack {
                            Button(Words.approve) { decide(pi.s("id"), "approve") }.buttonStyle(.borderedProminent).disabled(busy)
                            Button(Words.reject, role: .destructive) { decide(pi.s("id"), "reject") }.buttonStyle(.bordered).disabled(busy)
                        }
                    }
                    if !said.isEmpty { Muted(said) }
                }
            } else {
                let acts = items(r.o["_actions"])
                if !acts.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            ForEach(acts, id: \.id) { a in
                                Button(T(a.s("label")) + (a.b("approval") ? " *" : "")) {
                                    Db.shared.update(coll, r.id, [Db.shared.workflowField(coll): a.s("to")])
                                }.buttonStyle(.bordered)
                            }
                        }
                    }
                }
            }
        }
    }

    private func decide(_ id: String, _ d: String) {
        busy = true
        Task { @MainActor in
            let res = await Cloud.call("POST", "/approvals/\(id)", ["decision": d, "note": note], token: Auth.shared.token)
            busy = false
            said = res.ok ? (res.body["say"] as? String ?? Words.done) : (res.error.isEmpty ? Words.tryAgain : res.error)
            await Db.shared.refresh(coll)
        }
    }
}

/// A row's linked children (an order's items) + Add with the link filled in. Needs a network.
struct RelatedBlock: View {
    let coll: String
    let r: Item
    @ObservedObject private var db = Db.shared

    var body: some View {
        if !r.b("pending") {
            ForEach(db.relations(coll), id: \.id) { rel in RelatedList(coll: coll, parent: r, rel: rel) }
        }
    }
}

private struct RelatedList: View {
    let coll: String
    let parent: Item
    let rel: Item
    @State private var rows: [Item]? = nil
    @State private var adding = false
    @State private var tick = 0

    var body: some View {
        let kid = rel.s("coll")
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(T(rel.s("label")) + ((rows?.isEmpty ?? true) ? "" : " (\(rows!.count))")).font(.subheadline.weight(.semibold))
                Spacer()
                if Db.shared.mayCreate(kid) { Button(Words.add) { adding.toggle() }.font(.subheadline) }
            }
            ForEach((rows ?? []).prefix(30), id: \.id) { k in
                let fs = Db.shared.fields(kid).filter { $0.s("key") != rel.s("field") && k.has($0.s("key")) && $0.s("type") != "photo" }
                VStack(alignment: .leading, spacing: 2) {
                    Text(Logic.title(kid, k))
                    Muted(fs.dropFirst().prefix(3).map { T($0.s("label")) + ": " + Logic.show(k, $0) }.joined(separator: " · "))
                }
            }
            if adding { AutoForm(coll: kid, preset: [rel.s("field"): parent.id]) { adding = false; tick += 1 } }
        }
        .padding(.top, 6)
        .task(id: "\(parent.id)|\(tick)") {
            let res = await Cloud.call("GET", "/c/\(coll)/\(parent.id)/related/\(rel.s("name"))", nil, token: Auth.shared.token)
            rows = res.ok ? items(res.body["rows"]) : []
        }
    }
}

/// Every field of a list as a form - for the lists no screen was drawn for. Formula / workflow fields are the server's.
struct AutoForm: View {
    let coll: String
    var preset: [String: String] = [:]
    var done: () -> Void = {}
    @State private var vals: [String: String] = [:]
    @State private var miss = ""
    @ObservedObject private var auth = Auth.shared

    var body: some View {
        let fields = Db.shared.fields(coll).filter { f in
            !f.b("computed") && !f.b("workflow") && preset[f.s("key")] == nil && (!f.b("admin_only") || auth.isStaff) &&
                ["text", "long_text", "number", "phone", "email", "date", "choice", "yes_no", "ref",
                 "signature", "photos", "video", "audio", "richtext"].contains(f.s("type"))       // v0.425 RANG
        }
        VStack(alignment: .leading, spacing: 8) {
            ForEach(fields, id: \.id) { f in
                let k = f.s("key")
                let label = T(f.s("label")) + (f.b("required") ? " *" : "")
                switch f.s("type") {
                case "ref":
                    RefField(label: label, to: f.s("to"), value: Binding(get: { vals[k] ?? "" }, set: { vals[k] = $0 }))
                case "choice":
                    Picker(label, selection: Binding(get: { vals[k] ?? f.s("default") }, set: { vals[k] = $0 })) {
                        ForEach(f.strings("options"), id: \.self) { Text(T($0)).tag($0) }
                    }
                case "yes_no":
                    Toggle(label, isOn: Binding(get: { vals[k] == "true" }, set: { vals[k] = $0 ? "true" : "false" }))
                case "signature": SignatureRow(label: label, key: k)       // v0.425 RANG: these keep their value in AppState.form
                case "photos": PhotosRow(label: label, key: k)
                case "video": VideoRow(label: label, key: k)
                case "audio": AudioRow(label: label, key: k)
                case "richtext": RichTextRow(label: label, key: k)
                default:
                    TextField(label + (f.s("type") == "date" ? " (YYYY-MM-DD)" : ""), text: Binding(get: { vals[k] ?? "" }, set: { vals[k] = String($0.prefix(4000)) }))
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(f.s("type") == "number" ? .decimalPad : f.s("type") == "phone" ? .phonePad : f.s("type") == "email" ? .emailAddress : .default)
                }
            }
            if !miss.isEmpty { Text(miss).foregroundStyle(.red).font(.footnote) }
            HStack {
                Button(Words.save) {
                    let richKeys = fields.filter { ["signature", "photos", "video", "audio", "richtext"].contains($0.s("type")) }.map { $0.s("key") }
                    for rk in richKeys { if let v = AppState.shared.form[rk] { vals[rk] = v } }
                    if let m = fields.first(where: { $0.b("required") && (vals[$0.s("key")] ?? "").trimmingCharacters(in: .whitespaces).isEmpty }) {
                        miss = T(m.s("label")) + ": " + Words.fillThis
                        return
                    }
                    var data: [String: Any] = [:]
                    for (k, v) in preset { data[k] = v }
                    for (k, v) in vals where !v.trimmingCharacters(in: .whitespaces).isEmpty { data[k] = v.trimmingCharacters(in: .whitespaces) }
                    _ = Db.shared.create(coll, data, show: data)
                    for rk in richKeys { AppState.shared.form[rk] = nil }
                    done()
                }.buttonStyle(.borderedProminent)
                Button(Words.cancel) { done() }.buttonStyle(.bordered)
            }
        }
    }
}

/// Kit screen "hoola_approvals": what waits for this account's decision (+ what it asked for).
struct ApprovalsScreen: View {
    @ObservedObject private var auth = Auth.shared
    @State private var list: [Item]? = nil
    @State private var tick = 0

    var body: some View {
        Page(Words.approvals) {
            if !auth.signedIn { Muted(Words.signIn) }
            else if list == nil { Muted(Words.loading) }
            else if list!.isEmpty { Muted(Words.noApprovals) }
            ForEach(list ?? [], id: \.id) { a in ApprovalCard(a: a) { tick += 1 } }
        }
        .task(id: "\(auth.me?.id ?? "")|\(tick)") {
            let r = await Cloud.call("GET", "/approvals", nil, token: auth.token)
            list = r.ok ? items(r.body["approvals"]) : []
        }
    }
}

private struct ApprovalCard: View {
    let a: Item
    let changed: () -> Void
    @State private var note = ""
    @State private var said = ""
    @State private var busy = false

    var body: some View {
        Card {
            Text(a.s("title").isEmpty ? T(a.s("label")) : a.s("title")).font(.headline)
            Muted(T(a.s("label")) + ": " + T(a.s("from")) + " → " + T(a.s("to")) + " · \(Words.step) \(a.s("step"))/\(a.s("of"))")
            if a.has("maker") { Muted(Words.askedBy + ": " + a.s("maker")) }
            if a.has("waiting_for") { StatusPill(text: Words.waitingFor + ": " + T(a.s("waiting_for"))) }
            ForEach(Array(items(a.o["decisions"]).enumerated()), id: \.offset) { _, d in
                Muted("✓ " + d.s("by") + " · " + d.s("decision") + (d.has("note") ? " · " + d.s("note") : ""))
            }
            if a.b("can_decide") {
                TextField(Words.note, text: $note).textFieldStyle(.roundedBorder)
                HStack {
                    Button(Words.approve) { decide("approve") }.buttonStyle(.borderedProminent).disabled(busy)
                    Button(Words.reject, role: .destructive) { decide("reject") }.buttonStyle(.bordered).disabled(busy)
                }
            }
            if !said.isEmpty { Muted(said) }
        }
    }

    private func decide(_ d: String) {
        busy = true
        Task { @MainActor in
            let res = await Cloud.call("POST", "/approvals/\(a.id)", ["decision": d, "note": note], token: Auth.shared.token)
            busy = false
            said = res.ok ? (res.body["say"] as? String ?? Words.done) : (res.error.isEmpty ? Words.tryAgain : res.error)
            changed()
        }
    }
}

/// Kit screen "hoola_data" (staff): every list of the app - rows + Add as a form. A list added later works here at once.
struct DataScreen: View {
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var db = Db.shared
    @State private var open = ""
    @State private var adding = false

    var body: some View {
        Page(open.isEmpty ? Words.allLists : T(db.label(open))) {
            if !auth.isStaff { Muted(Words.staffOnlyHere) }
            else if open.isEmpty {
                ForEach(db.collections(), id: \.self) { c in
                    Button { open = c; adding = false } label: {
                        VStack(alignment: .leading) {
                            Text(T(db.label(c))).font(.headline)
                            Muted(db.fields(c).prefix(4).map { T($0.s("label")) }.joined(separator: ", "))
                        }
                    }
                }
            } else {
                HStack {
                    Button(Words.back) { open = ""; adding = false }.buttonStyle(.bordered)
                    if db.mayCreate(open) { Button(Words.add) { adding.toggle() }.buttonStyle(.borderedProminent) }
                }
                if adding { AutoForm(coll: open) { adding = false } }
                RowsSection(coll: open)
            }
        }
    }
}

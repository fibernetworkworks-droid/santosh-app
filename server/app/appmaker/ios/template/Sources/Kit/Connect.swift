// Made by Hoola App Sahayak (v0.424 JODO), the iPhone twin of Connect.kt: staff buttons for the business's own approved
// connectors on a row (courier booking, tracking, an SMS...). The server makes the call with her sealed keys; this app
// never holds them; the answer lands in the row's own fields.
import SwiftUI

enum Connectors {
    @MainActor static func forList(_ coll: String) -> [Item] {
        items(AppData.shared.backend["connect"]).filter { $0.s("coll") == coll }
    }
}

struct ConnectButtons: View {
    let coll: String
    let r: Item
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var db = Db.shared
    @State private var busy = ""
    @State private var note = ""

    var body: some View {
        let acts = Connectors.forList(coll)
        if auth.isStaff && !r.b("pending") && !acts.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(acts, id: \.id) { a in
                            Button(busy == a.s("key") ? Words.opening : T(a.s("label"))) {
                                guard busy.isEmpty else { return }
                                busy = a.s("key")
                                Task {
                                    let res = await Cloud.call("POST", "/connect/\(a.s("key"))/run", ["row": r.id], token: auth.token)
                                    busy = ""
                                    let st = res.body["status"] as? String ?? ""
                                    note = res.ok && st == "ok" ? Words.connDone : (res.error.isEmpty ? Words.tryAgain + (st.isEmpty ? "" : " (\(st))") : res.error)
                                    if res.ok { await db.refresh(coll) }
                                }
                            }.buttonStyle(.bordered)
                        }
                    }
                }
                if !note.isEmpty { Muted(note) }
            }
        }
    }
}

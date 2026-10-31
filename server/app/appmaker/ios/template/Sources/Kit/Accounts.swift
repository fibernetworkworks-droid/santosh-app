// Made by Hoola App Sahayak (v0.332 IPHONE). Written by code, never by the model: sign in / create account (the only
// password box, sent once over https, never stored), My account (the user's rows with live status, staff see and move
// everyone's), the form of one server list (its own fields, read live - a field the business adds shows at once), the cart
// checkout, the UPI "I have paid" claim, the privacy page and in-app account deletion (both stores require it).
import SwiftUI
import PhotosUI

struct AuthScreen: View {
    @State private var signup = true
    @State private var busy = false
    @State private var err = ""
    @State private var email = ""
    @State private var pass = ""
    @State private var who = ""
    @ObservedObject private var router = Router.shared

    var body: some View {
        Page(signup ? Words.createAccount : Words.signIn) {
            if signup { TextField(Words.name, text: $who).textFieldStyle(.roundedBorder).textContentType(.name) }
            TextField(Words.email, text: $email).textFieldStyle(.roundedBorder).keyboardType(.emailAddress)
                .textInputAutocapitalization(.never).textContentType(.emailAddress)
            SecureField(Words.password, text: $pass).textFieldStyle(.roundedBorder).textContentType(signup ? .newPassword : .password)
            if !err.isEmpty { Text(err).foregroundStyle(.red).font(.subheadline) }
            MainButton(text: busy ? Words.sending : (signup ? Words.createAccount : Words.signIn)) {
                guard !busy else { return }
                busy = true
                err = ""
                Task {
                    let e = signup ? await Auth.shared.signup(email: email, password: pass, name: who)
                                   : await Auth.shared.login(email: email, password: pass)
                    busy = false
                    if let e = e { err = e } else { pass = ""; router.back() }
                }
            }
            Button(signup ? Words.haveAccount : Words.newHere) { signup.toggle(); err = "" }.font(.subheadline)
        }
    }
}

struct AccountScreen: View {
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var db = Db.shared
    @State private var confirmDelete = false

    var body: some View {
        Page(Words.account) {
            if let me = auth.me {
                Card {
                    Text(auth.name).font(.title3.weight(.semibold))
                    Muted(me.s("email") + (auth.isStaff ? " · Staff" : ""))
                }
            } else {
                MainButton(text: Words.signIn) { Router.shared.go("hoola_login") }
            }
            if db.pending > 0 { Muted("\(db.pending) · \(Words.sending)") }
            if !db.lastError.isEmpty { Text(db.lastError).foregroundStyle(.red).font(.subheadline) }
            ForEach(db.collections(), id: \.self) { c in
                let read = db.rule(c, "read")
                if read == "public" || (auth.signedIn && (read != "admin" || auth.isStaff)) { RowsSection(coll: c) }
            }
            if auth.signedIn {
                Button(Words.signOut) { auth.logout() }
                Button(Words.deleteAccount, role: .destructive) { confirmDelete = true }
            }
            Button(Words.privacy) { Router.shared.go("privacy") }.font(.footnote)
        }
        .confirmationDialog(Words.deleteWhat, isPresented: $confirmDelete, titleVisibility: .visible) {
            Button(Words.deleteAccount, role: .destructive) { Task { _ = await auth.deleteAccount() } }
        }
    }
}

/// One server list as cards: the user's rows (staff: everyone's, with status buttons), pending writes marked.
struct RowsSection: View {
    let coll: String
    @ObservedObject private var db = Db.shared
    @ObservedObject private var auth = Auth.shared
    @State private var paying: Item? = nil
    @State private var utr = ""

    var body: some View {
        let rows = db.rows(coll)
        let fields = db.fields(coll)
        VStack(alignment: .leading, spacing: 10) {
            Text(db.label(coll) + (rows.isEmpty ? "" : " (\(rows.count))")).font(.headline)
            if rows.isEmpty { Muted(Words.nothingYet) }
            ForEach(rows.prefix(60), id: \.id) { r in
                Card {
                    let head = fields.first { ["text", "long_text"].contains($0.s("type")) && r.has($0.s("key")) && $0.s("key") != "utr" }
                    Text(head.map { r.s($0.s("key")) } ?? db.label(coll)).font(.headline)
                    HStack {
                        if r.b("pending") { StatusPill(text: Words.sending) } else if r.has("status") { StatusPill(text: r.s("status")) }
                        if r.has("paid") && r.s("paid") != "No" { StatusPill(text: r.s("paid")) }
                        if r.n("total") > 0 { Text(rupees(r.n("total"))).font(.headline) }
                    }
                    ForEach(fields.filter { $0.s("key") != head?.s("key") && !["status", "total", "paid"].contains($0.s("key")) && r.has($0.s("key")) && $0.s("type") != "photo" }.prefix(6), id: \.id) { f in
                        Muted(f.s("label") + ": " + r.s(f.s("key")))
                    }
                    if !auth.isStaff && coll == db.orderList && !r.b("pending") && r.s("pay") == "UPI" && r.s("paid", "No") == "No" {
                        HStack {
                            Button(Words.payUpi) { payUpi(r.n("total"), "Order " + String(r.id.suffix(6))) }.buttonStyle(.borderedProminent)
                            Button(Words.iPaid) { paying = r }.buttonStyle(.bordered)
                        }
                    }
                    if auth.isStaff && !r.b("pending"), let st = fields.first(where: { $0.s("key") == "status" }) {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack {
                                ForEach(st.strings("options"), id: \.self) { o in
                                    Button(o) { if r.s("status") != o { db.update(coll, r.id, ["status": o]) } }
                                        .buttonStyle(.bordered).tint(r.s("status") == o ? .accentColor : .secondary)
                                }
                            }
                        }
                    }
                }
            }
        }
        .task(id: auth.me?.id) { await db.refresh(coll) }
        .alert(Words.iPaid, isPresented: Binding(get: { paying != nil }, set: { if !$0 { paying = nil } })) {
            TextField(Words.utr, text: $utr).keyboardType(.asciiCapable)
            Button("OK") {
                if let p = paying, utr.count >= 6 { db.paid(coll, p.id, utr: utr) }
                utr = ""
                paying = nil
            }
            Button("Cancel", role: .cancel) { paying = nil }
        }
    }
}

/// The form of one server list: its own fields (choices as a picker, photos from the photo library, a location button),
/// then the button that really saves. The order list also takes the cart.
struct FormBlock: View {
    let coll: String
    var then: String = "hoola_account"
    @ObservedObject private var db = Db.shared
    @ObservedObject private var state = AppState.shared
    @State private var note = ""
    @State private var pick: [String: PhotosPickerItem] = [:]

    var body: some View {
        let isOrder = coll == db.orderList
        if isOrder {
            let lines = state.cartItems()
            if lines.isEmpty { Muted(Words.cartEmpty) }
            ForEach(lines, id: \.0.id) { it, q in
                Card {
                    HStack {
                        Text(it.name).font(.headline)
                        Spacer()
                        Stepper("\(q)", value: Binding(get: { q }, set: { state.setQty(it.id, $0) }), in: 0...99).fixedSize()
                    }
                    Muted(rupees(it.price * Double(q)))
                }
            }
            if !lines.isEmpty { Text(rupees(state.cartTotal())).font(.title3.weight(.semibold)) }
        }
        ForEach(db.fields(coll).filter { !$0.b("admin_only") && $0.s("type") != "yes_no" }, id: \.id) { f in
            let k = f.s("key")
            let label = f.s("label", k) + (f.b("required") ? " *" : "")
            switch f.s("type") {
            case "choice":
                Picker(label, selection: state.binding(k)) {
                    ForEach(f.strings("options"), id: \.self) { Text($0).tag($0) }
                }
                .onAppear { if (state.form[k] ?? "").isEmpty { state.form[k] = f.s("default") } }
            case "long_text":
                TextField(label, text: state.binding(k), axis: .vertical).lineLimit(3...6).textFieldStyle(.roundedBorder)
            case "photo":
                PhotoRow(label: label, key: k)
            case "location":
                LocationRow(label: label, key: k)
            default:
                TextField(label, text: state.binding(k)).textFieldStyle(.roundedBorder)
                    .keyboardType(f.s("type") == "phone" ? .phonePad : f.s("type") == "email" ? .emailAddress : f.s("type") == "number" ? .decimalPad : .default)
            }
        }
        if !note.isEmpty { Text(note).font(.subheadline).foregroundStyle(note == Words.saved ? Color.green : Color.red) }
        MainButton(text: isOrder ? Words.placeOrder : Words.send) {
            switch db.submit(coll) {
            case nil:
                note = Words.saved
                if !then.isEmpty { Router.shared.go(then) }
            case .some("login"):
                Router.shared.go("hoola_login")
            case .some(let e):
                note = e
            }
        }
    }
}

/// A photo for a form: the system photo library picker (no permission needed), shrunk on the phone, sent by the outbox.
struct PhotoRow: View {
    let label: String
    let key: String
    @State private var item: PhotosPickerItem? = nil
    @ObservedObject private var state = AppState.shared
    var body: some View {
        HStack {
            PhotosPicker(selection: $item, matching: .images) { Label(label, systemImage: "camera") }
            Spacer()
            if !(state.form[key] ?? "").isEmpty { Image(systemName: "checkmark.circle.fill").foregroundStyle(.green) }
        }
        .onChange(of: item) { new in
            guard let new = new else { return }
            Task {
                guard let data = try? await new.loadTransferable(type: Data.self), let img = UIImage(data: data) else { return }
                let scale = min(1, 1600 / max(img.size.width, img.size.height))
                let size = CGSize(width: img.size.width * scale, height: img.size.height * scale)
                let small = UIGraphicsImageRenderer(size: size).image { _ in img.draw(in: CGRect(origin: .zero, size: size)) }
                guard let jpeg = small.jpegData(compressionQuality: 0.85) else { return }
                let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".jpg")
                try? jpeg.write(to: url)
                await MainActor.run { state.form[key] = "local:" + url.path }
            }
        }
    }
}

/// "Use my location" for a form (when the app is open; iOS asks with the reason written in the app's settings).
struct LocationRow: View {
    let label: String
    let key: String
    @StateObject private var here = Here()
    @ObservedObject private var state = AppState.shared
    var body: some View {
        HStack {
            Button { here.ask() } label: { Label(label, systemImage: "location") }
            Spacer()
            if let v = state.form[key], !v.isEmpty { Text(v).font(.caption).foregroundStyle(.secondary) }
        }
        .onChange(of: here.value) { v in if !v.isEmpty { state.form[key] = v } }
    }
}

import CoreLocation

final class Here: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let lm = CLLocationManager()
    @Published var value = ""
    override init() {
        super.init()
        lm.delegate = self
        lm.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }
    func ask() {
        if lm.authorizationStatus == .notDetermined { lm.requestWhenInUseAuthorization() } else { lm.requestLocation() }
    }
    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        if m.authorizationStatus == .authorizedWhenInUse || m.authorizationStatus == .authorizedAlways { m.requestLocation() }
    }
    func locationManager(_ m: CLLocationManager, didUpdateLocations locs: [CLLocation]) {
        guard let l = locs.last else { return }
        let v = String(format: "%.6f,%.6f", l.coordinate.latitude, l.coordinate.longitude)
        DispatchQueue.main.async { self.value = v }
    }
    func locationManager(_ m: CLLocationManager, didFailWithError error: Error) {}
}

/// UPI to the business's OWN UPI ID: the customer's UPI app asks the PIN; this app never sees it.
func payUpi(_ amount: Double, _ note: String) {
    let f = AppData.shared.facts
    let vpa = f.s("upi_id")
    guard !vpa.isEmpty else { return }
    var c = URLComponents(string: "upi://pay")!
    c.queryItems = [URLQueryItem(name: "pa", value: vpa), URLQueryItem(name: "pn", value: f.s("name", "Shop")),
                    URLQueryItem(name: "cu", value: "INR"), URLQueryItem(name: "tn", value: String(note.prefix(60)))]
    if amount > 0 { c.queryItems?.append(URLQueryItem(name: "am", value: String(format: "%.2f", amount))) }
    if let u = c.url { UIApplication.shared.open(u) }
}

struct PrivacyScreen: View {
    @ObservedObject private var data = AppData.shared
    var body: some View {
        Page(Words.privacy) {
            ForEach(Array(data.facts.strings("privacy").enumerated()), id: \.offset) { _, p in
                if p.hasPrefix("# ") { Text(String(p.dropFirst(2))).font(.headline) } else { Text(p) }
            }
        }
    }
}

struct DeleteAccountScreen: View {
    @ObservedObject private var auth = Auth.shared
    @State private var done = ""
    var body: some View {
        Page(Words.deleteAccount) {
            Text(Words.deleteWhat)
            if !done.isEmpty { Muted(done) }
            if auth.signedIn {
                Button(Words.deleteAccount, role: .destructive) {
                    Task { done = await auth.deleteAccount() ?? "✓" }
                }
            }
        }
    }
}

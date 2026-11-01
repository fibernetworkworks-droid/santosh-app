// Made by Hoola App Sahayak (v0.340 HAR FEATURE 2), the iPhone twin of the Android kit's Pro.kt:
// - ScanRow: a barcode / QR code read by Apple's VisionKit scanner (live camera, iPhone XS and newer), or typed.
// - StatsBlock: the staff dashboard - counts, status mix, rows per day (Swift Charts) and the money total (staff only).
// - Inbox + InboxScreen: every update the app was told about, kept on the phone, newest first.
// - Updates: the background check (iOS background app refresh, when iOS allows it) -> a local notification per change,
//   the same /updates the Android app polls. No push server and no Apple push key are needed.
import SwiftUI
import Charts
import VisionKit
import BackgroundTasks
import UserNotifications
import UniformTypeIdentifiers
import MapKit
import CoreLocation

// ---------------------------------------------------------------- scan
struct ScanRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    @State private var open = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField(label, text: state.binding(key)).textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            if DataScannerViewController.isSupported && DataScannerViewController.isAvailable {
                Button { open = true } label: { Label(Words.scan, systemImage: "barcode.viewfinder") }
                    .buttonStyle(.bordered)
            }
        }
        .sheet(isPresented: $open) {
            ScannerSheet { code in
                state.form[key] = String(code.prefix(200))
                open = false
            }
            .ignoresSafeArea()
        }
    }
}

struct ScannerSheet: UIViewControllerRepresentable {
    let done: (String) -> Void

    func makeCoordinator() -> Coord { Coord(done: done) }

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let vc = DataScannerViewController(recognizedDataTypes: [.barcode()], qualityLevel: .balanced,
                                           recognizesMultipleItems: false, isHighFrameRateTrackingEnabled: false,
                                           isHighlightingEnabled: true)
        vc.delegate = context.coordinator
        DispatchQueue.main.async { try? vc.startScanning() }
        return vc
    }

    func updateUIViewController(_ vc: DataScannerViewController, context: Context) {}

    @MainActor
    final class Coord: NSObject, DataScannerViewControllerDelegate {
        let done: (String) -> Void
        init(done: @escaping (String) -> Void) { self.done = done }

        func dataScanner(_ dataScanner: DataScannerViewController, didAdd addedItems: [RecognizedItem], allItems: [RecognizedItem]) {
            for item in addedItems {
                if case .barcode(let b) = item, let s = b.payloadStringValue, !s.isEmpty {
                    dataScanner.stopScanning()
                    done(s.trimmingCharacters(in: .whitespacesAndNewlines))
                    return
                }
            }
        }
    }
}

// ---------------------------------------------------------------- staff dashboard
struct StatsList: Identifiable {
    let id: String
    let label: String
    let count: Int
    let total: Double?
    let status: [(String, Int)]
    let daily: [Int]
    var rating: String = ""                      // v0.353 "★ 4.3 (12)"
}

struct StatsBlock: View {
    @ObservedObject private var auth = Auth.shared
    @State private var lists: [StatsList] = []
    @State private var failed = false
    @State private var loaded = false
    @State private var team: [Item] = []
    @State private var unassigned = 0
    @Environment(\.colorScheme) private var scheme

    var body: some View {
        if auth.isStaff {
            VStack(alignment: .leading, spacing: 12) {
                Text(Words.dashboard).font(.headline)
                if !loaded { Muted(failed ? Words.offline : Words.loading) }
                ForEach(lists) { l in
                    Card {
                        HStack {
                            Text(l.label).font(.headline)
                            Spacer()
                            Text("\(l.count)").font(.title3.weight(.semibold))
                        }
                        if let t = l.total { Muted(Words.total + ": " + rupees(t)) }
                        if !l.rating.isEmpty { Muted(l.rating) }
                        if !l.status.isEmpty {
                            HStack { ForEach(l.status.prefix(4), id: \.0) { s in StatusPill(text: "\(s.0) \(s.1)") } }
                        }
                        Chart {
                            ForEach(Array(l.daily.enumerated()), id: \.offset) { i, v in
                                BarMark(x: .value("Day", i), y: .value("Count", v)).foregroundStyle(H.c(scheme).primary)
                            }
                        }
                        .chartXAxis(.hidden)
                        .frame(height: 72)
                        .accessibilityLabel(Words.last14 + " " + l.label + ": " + l.daily.map(String.init).joined(separator: ", "))
                    }
                }
                if !team.isEmpty {                       // v0.352 / v0.353 open work and average stars per person
                    Card {
                        Text(Words.myTeam).font(.headline)
                        if unassigned > 0 { StatusPill(text: "\(unassigned) " + Words.notAssigned) }
                        ForEach(team, id: \.id) { p in Muted(p.s("name") + " · \(Int(p.n("open"))) " + Words.openWork
                            + (p.has("rating") ? " · ★ \(p.s("rating")) (\(Int(p.n("rated"))))" : "")) }
                    }
                }
            }
            .task(id: auth.me?.id) { await load() }
        }
    }

    private func load() async {
        let r = await Cloud.call("GET", "/stats", nil, token: auth.token)
        guard r.ok else { failed = true; return }
        lists = items(r.body["lists"]).map { x in
            let st = (x.o["status"] as? [String: Any] ?? [:]).compactMap { k, v in (v as? NSNumber).map { (k, $0.intValue) } }
                .sorted { $0.1 > $1.1 }
            let daily = (x.o["daily"] as? [Any] ?? []).compactMap { ($0 as? NSNumber)?.intValue }
            let rt = x.o["rating"] as? [String: Any]
            return StatsList(id: x.s("key"), label: x.s("label"), count: Int(x.n("count")),
                             total: x.o["total"] is NSNull || x.o["total"] == nil ? nil : x.n("total"), status: st, daily: daily,
                             rating: rt.map { "★ \(Item(o: $0).s("avg")) (\(Item(o: $0).s("count")))" } ?? "")
        }
        team = items(r.body["team"]).enumerated().map { i, p in var o = p.o; o["id"] = "p\(i)"; return Item(o: o) }
        unassigned = (r.body["unassigned"] as? NSNumber)?.intValue ?? 0
        loaded = true
    }
}

// ---------------------------------------------------------------- inbox
@MainActor
final class Inbox: ObservableObject {
    static let shared = Inbox()
    @Published private(set) var items: [[String: Any]] = []
    @Published private(set) var unread = 0
    private let key = "hoola_inbox"

    init() {
        items = (UserDefaults.standard.array(forKey: key) as? [[String: Any]]) ?? []
        unread = items.filter { ($0["new"] as? Bool) == true }.count
    }

    func add(_ title: String, _ text: String, _ at: String) {
        items = [["title": title, "text": text, "at": at, "new": true]] + items.prefix(49)
        save()
    }

    func seen() {
        items = items.map { var x = $0; x["new"] = false; return x }
        save()
    }

    private func save() {
        UserDefaults.standard.set(items, forKey: key)
        unread = items.filter { ($0["new"] as? Bool) == true }.count
    }
}

struct InboxScreen: View {
    @ObservedObject private var inbox = Inbox.shared
    var body: some View {
        Page(Words.inbox) {
            if inbox.items.isEmpty { Muted(Words.inboxEmpty) }
            ForEach(Array(inbox.items.enumerated()), id: \.offset) { _, x in
                Card {
                    Text(x["title"] as? String ?? "").font(.headline)
                    if let t = x["text"] as? String, !t.isEmpty { Muted(t) }
                    Muted(String((x["at"] as? String ?? "").prefix(16)).replacingOccurrences(of: "T", with: " "))
                }
            }
        }
        .onDisappear { inbox.seen() }
    }
}

struct InboxButton: View {
    @ObservedObject private var inbox = Inbox.shared
    var body: some View {
        MainButton(text: Words.inbox + (inbox.unread > 0 ? " (\(inbox.unread))" : ""), tonal: true) { Router.shared.go("hoola_inbox") }
    }
}

// ---------------------------------------------------------------- background updates
enum Updates {
    static var taskId: String { (Bundle.main.bundleIdentifier ?? "app") + ".updates" }

    /// At app start (before launch ends): the background job iOS runs when it suits the battery.
    static func register() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: taskId, using: nil) { task in
            guard let t = task as? BGAppRefreshTask else { task.setTaskCompleted(success: false); return }
            schedule()
            let job = Task { @MainActor in
                _ = await check()
                t.setTaskCompleted(success: true)
            }
            t.expirationHandler = { job.cancel() }
        }
    }

    static func schedule() {
        let r = BGAppRefreshTaskRequest(identifier: taskId)
        r.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60)
        try? BGTaskScheduler.shared.submit(r)
    }

    /// Asks the server what changed since the last check: one local notification per change + the inbox.
    @MainActor
    static func check() async -> Int {
        guard Cloud.ready, Auth.shared.signedIn else { return 0 }
        askOnce()
        let since = UserDefaults.standard.string(forKey: "hoola_upd_since") ?? ""
        let q = since.isEmpty ? "" : "?since=" + (since.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? "")
        let r = await Cloud.call("GET", "/updates" + q, nil, token: Auth.shared.token)
        guard r.ok else { return 0 }
        let now = r.body["now"] as? String ?? ""
        if !now.isEmpty { UserDefaults.standard.set(now, forKey: "hoola_upd_since") }
        if since.isEmpty { return 0 }                 // the very first check only sets the mark: no old news
        var shown = 0
        for it in items(r.body["items"]) {
            let title = it.s("title", AppData.shared.appName)
            let text = it.s("kind") == "new" ? Words.newEntry
                : it.s("kind") == "assigned" ? Words.assignedToYou          // v0.352 work given to this staff member
                : [it.s("status"), it.s("paid") == "No" ? "" : it.s("paid")].filter { !$0.isEmpty }.joined(separator: " · ")
            Inbox.shared.add(title, text, now)
            let c = UNMutableNotificationContent()
            c.title = title
            c.body = text
            c.sound = .default
            try? await UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: it.s("id") + now, content: c, trigger: nil))
            shown += 1
        }
        return shown
    }

    /// The notification question, once, after the user has an account (never at first launch).
    @MainActor
    static func askOnce() {
        guard !UserDefaults.standard.bool(forKey: "hoola_notify_asked") else { return }
        UserDefaults.standard.set(true, forKey: "hoola_notify_asked")
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }
}

// ---------------------------------------------------------------- v0.346 a PDF document for a form
/// The system file importer (no permission), at most 10 MB, copied into the app's own temp folder, sent by the outbox.
struct FileRow: View {
    let label: String
    let key: String
    @ObservedObject private var state = AppState.shared
    @State private var open = false
    @State private var note = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Button { open = true } label: { Label(label, systemImage: "doc.richtext") }
                Spacer()
                if !(state.form[key] ?? "").isEmpty {
                    Text(state.form[key + "__name"] ?? "PDF").font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    Button(Words.remove) { state.form[key] = nil; state.form[key + "__name"] = nil }.font(.caption)
                }
            }
            if !note.isEmpty { Text(note).font(.caption).foregroundStyle(.red) }
        }
        .fileImporter(isPresented: $open, allowedContentTypes: [.pdf]) { result in
            guard case .success(let url) = result else { return }
            let ok = url.startAccessingSecurityScopedResource()
            defer { if ok { url.stopAccessingSecurityScopedResource() } }
            guard let data = try? Data(contentsOf: url), data.count <= 10 * 1024 * 1024, data.prefix(5) == Data("%PDF-".utf8) else {
                note = Words.fileFailed
                return
            }
            let dest = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".pdf")
            guard (try? data.write(to: dest)) != nil else { note = Words.fileFailed; return }
            note = ""
            state.form[key] = "local:" + dest.path
            state.form[key + "__name"] = String(url.lastPathComponent.prefix(80))
        }
    }
}

// ---------------------------------------------------------------- v0.350 NAKSHA: stops on a map (Apple MapKit, free)
enum Maps {
    static let done: Set<String> = ["Delivered", "Done", "Completed", "Cancelled", "Closed", "Rejected"]

    static func point(_ s: String) -> CLLocationCoordinate2D? {
        let p = s.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
        guard p.count == 2, let la = Double(p[0]), let lo = Double(p[1]), abs(la) <= 90, abs(lo) <= 180 else { return nil }
        return CLLocationCoordinate2D(latitude: la, longitude: lo)
    }

    static func km(_ a: CLLocationCoordinate2D, _ b: CLLocationCoordinate2D) -> Double {
        CLLocation(latitude: a.latitude, longitude: a.longitude).distance(from: CLLocation(latitude: b.latitude, longitude: b.longitude)) / 1000
    }

    /// Apple Maps with every stop (it plans the route); one stop = directions to it.
    static func open(_ stops: [(String, CLLocationCoordinate2D)]) {
        let items = stops.prefix(10).map { s -> MKMapItem in
            let m = MKMapItem(placemark: MKPlacemark(coordinate: s.1))
            m.name = s.0
            return m
        }
        MKMapItem.openMaps(with: items, launchOptions: [MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving])
    }
}

struct Stop: Identifiable {
    let id: String
    let name: String
    let note: String
    let at: CLLocationCoordinate2D
}

/// Staff: the open rows that carry a location on a map + nearest first; "Route in Maps" opens Apple Maps with all of them.
struct StopsBlock: View {
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var db = Db.shared
    @StateObject private var here = Here()
    @State private var region = MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: 20.59, longitude: 78.96),
                                                   span: MKCoordinateSpan(latitudeDelta: 20, longitudeDelta: 20))

    private func stops() -> [Stop] {
        var out: [Stop] = []
        for c in db.collections() {
            guard let key = db.fields(c).first(where: { $0.s("type") == "location" })?.s("key") else { continue }
            for r in db.rows(c) where !Maps.done.contains(r.s("status")) {
                guard let p = Maps.point(r.s(key)) else { continue }
                let name = [r.s("name"), r.s("title"), r.s("address")].first { !$0.isEmpty } ?? T(db.label(c))
                out.append(Stop(id: c + r.id, name: name, note: [T(r.s("status")), r.s("address")].filter { !$0.isEmpty }.joined(separator: " · "), at: p))
            }
        }
        if let h = Maps.point(here.value) { out.sort { Maps.km(h, $0.at) < Maps.km(h, $1.at) } }
        return out
    }

    var body: some View {
        if auth.isStaff && db.collections().contains(where: { c in db.fields(c).contains { $0.s("type") == "location" } }) {
            let list = stops()
            VStack(alignment: .leading, spacing: 10) {
                Text(T("Today's stops") + " (\(list.count))").font(.headline)
                if list.isEmpty { Muted(T("No open stops with a location.")) }
                if !list.isEmpty {
                    Map(coordinateRegion: $region, annotationItems: list) { s in MapMarker(coordinate: s.at) }
                        .frame(height: 220)
                        .clipShape(RoundedRectangle(cornerRadius: H.radius))
                        .onAppear { if let f = list.first { region.center = f.at; region.span = MKCoordinateSpan(latitudeDelta: 0.2, longitudeDelta: 0.2) } }
                }
                ForEach(list.prefix(20)) { s in
                    Card {
                        Text(s.name).font(.headline)
                        let d = Maps.point(here.value).map { String(format: "%.1f km", Maps.km($0, s.at)) } ?? ""
                        Muted([d, s.note].filter { !$0.isEmpty }.joined(separator: " · "))
                    }
                    .onTapGesture { Maps.open([(s.name, s.at)]) }
                }
                if !list.isEmpty && here.value.isEmpty {
                    Button { here.ask() } label: { Label(T("Nearest first (use my location)"), systemImage: "location") }.font(.subheadline)
                }
                if !list.isEmpty { MainButton(text: T("Route in Maps"), tonal: true) { Maps.open(list.map { ($0.name, $0.at) }) } }
            }
            .onAppear {                                       // the location question only on her tap (App Review), never by itself
                let st = CLLocationManager().authorizationStatus
                if st == .authorizedWhenInUse || st == .authorizedAlways { here.ask() }
            }
        }
    }
}

// ---------------------------------------------------------------- v0.352 KAAM BAANTO: work given to one staff member
/// The app's staff (first names only, never e-mails) for the assign buttons. `admin` = this account gives work to others.
@MainActor
final class Team: ObservableObject {
    static let shared = Team()
    @Published var people: [Item] = []
    @Published var admin = false
    private var loadedFor = ""

    func load(force: Bool = false) async {
        guard Auth.shared.isStaff else { return }
        let who = Auth.shared.me?.id ?? ""
        if !force && loadedFor == who && !people.isEmpty { return }
        let r = await Cloud.call("GET", "/team", nil, token: Auth.shared.token)
        guard r.ok else { return }
        people = items(r.body["team"])
        admin = (r.body["admin"] as? Bool) ?? false
        loadedFor = who
    }

    /// Whether this account may work on (change) the row: free, mine, or I am an admin. The server checks it again.
    func mayWork(_ r: Item) -> Bool {
        let to = r.s("assigned_to")
        return to.isEmpty || to == (Auth.shared.me?.id ?? "") || admin
    }
}

/// On a staff row card: who has it, and - admin: one button per staff member (tap again = take back); staff: "I'll take
/// it" on a free row, "Give back" on their own. Sent through the outbox like any change (works offline).
struct AssignBox: View {
    let coll: String
    let r: Item
    @ObservedObject private var auth = Auth.shared
    @ObservedObject private var team = Team.shared

    var body: some View {
        if auth.isStaff && !r.b("pending") {
            let meId = auth.me?.id ?? ""
            let to = r.s("assigned_to")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    StatusPill(text: to.isEmpty ? Words.notAssigned : Words.withPerson + ": " + (to == meId ? Words.you : r.s("assigned_name")))
                    if team.admin {
                        ForEach(team.people, id: \.id) { p in
                            Button(p.s("name")) { Db.shared.update(coll, r.id, ["_assign": to == p.id ? "" : p.id]) }
                                .buttonStyle(.bordered).tint(to == p.id ? .accentColor : .secondary)
                        }
                    } else if to.isEmpty {
                        Button(Words.takeIt) { Db.shared.update(coll, r.id, ["_assign": "me"]) }.buttonStyle(.bordered)
                    } else if to == meId {
                        Button(Words.giveBack) { Db.shared.update(coll, r.id, ["_assign": ""]) }.buttonStyle(.bordered)
                    }
                }
            }
            .task(id: auth.me?.id) { await team.load() }
        }
    }
}


// ---------------------------------------------------------------- v0.353 RAAY: the customer's rating of a finished row
func starLine(_ n: Int, _ note: String = "") -> String {
    let k = max(0, min(5, n))
    return String(repeating: "★", count: k) + String(repeating: "☆", count: 5 - k) + " \(n)/5" + (note.isEmpty ? "" : " · " + String(note.prefix(120)))
}

/// On the customer's own finished row (the server says `can_rate`): 1-5 stars + a short note, sent once through the outbox
/// (works offline). A rated row shows its stars instead.
struct RateBox: View {
    let coll: String
    let r: Item
    @ObservedObject private var auth = Auth.shared
    @State private var stars = 0
    @State private var note = ""
    @State private var sent = 0

    var body: some View {
        let n = Int(r.n("rating"))
        if n > 0 {
            Muted(starLine(n, r.s("rating_note")))
        } else if sent > 0 {
            Muted(starLine(sent) + " · " + Words.thanksRating)
        } else if r.b("can_rate") && !auth.isStaff {
            VStack(alignment: .leading, spacing: 6) {
                Muted(Words.rateIt)
                HStack {
                    ForEach(1...5, id: \.self) { i in
                        Button("\(i) ★") { stars = i }.buttonStyle(.bordered).tint(stars == i ? .accentColor : .secondary)
                            .accessibilityLabel("\(i) / 5")
                    }
                }
                if stars > 0 {
                    TextField(Words.ratingNote, text: $note, axis: .vertical).lineLimit(1...3).textFieldStyle(.roundedBorder)
                        .onChange(of: note) { v in if v.count > 300 { note = String(v.prefix(300)) } }
                    Button(Words.sendRating) {
                        Db.shared.update(coll, r.id, ["_rate": ["stars": stars, "note": note.trimmingCharacters(in: .whitespacesAndNewlines)]])
                        sent = stars
                    }.buttonStyle(.borderedProminent)
                }
            }
        }
    }
}

// ---------------------------------------------------------------- v0.354 RASEED: the receipt of a finished row
/// "Receipt" on a finished row (the server says `receipt`): a 15-minute signed link from the app's server, opened in the
/// browser - no file storage, no sharing sheet. Needs a network (said plainly when there is none).
struct ReceiptButton: View {
    let coll: String
    let r: Item
    @Environment(\.openURL) private var openURL
    @State private var busy = false
    @State private var error = ""

    var body: some View {
        if r.b("receipt") && !r.b("pending") {
            VStack(alignment: .leading, spacing: 4) {
                Button(busy ? Words.loading : Words.receipt) {
                    guard !busy else { return }
                    busy = true
                    Task {
                        let res = await Cloud.call("POST", "/c/\(coll)/\(r.id)/receipt-link", [:], token: Auth.shared.token)
                        busy = false
                        if res.ok, let s = res.body["url"] as? String, s.hasPrefix("http"), let u = URL(string: s) { openURL(u); error = "" }
                        else { error = res.error.isEmpty ? (res.offline ? Words.offline : Words.tryAgain) : res.error }
                    }
                }.buttonStyle(.bordered)
                if !error.isEmpty { Muted(error) }
            }
        }
    }
}

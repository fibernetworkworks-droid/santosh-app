// Made by Hoola App Sahayak (v0.412 NAKSHA LIVE), the iPhone twin of the Android kit's Track.kt: a rider's location while
// on shift, the customer's order on a map while it is on its way, every rider on one map for staff. Apple Maps (MapKit):
// free, no key. Only when the business turned tracking on. The rider starts it after a plain notice + Apple's own dialog;
// iOS shows the blue location pill the whole time it runs in the background; End shift stops it and the server wipes the
// position. A customer sees ONLY the rider bringing her order, only while it is on its way (the server decides).
import SwiftUI
import MapKit
import CoreLocation

struct TrackPin: Identifiable {
    let id: String
    let at: CLLocationCoordinate2D
    let label: String
    let kind: String                // rider | dest
}

@MainActor
final class Track: NSObject, ObservableObject, CLLocationManagerDelegate {
    static let shared = Track()
    @Published var onShift = false
    @Published var riders: [String: (TrackPin, [String])] = [:]
    @Published var tick = 0
    private let lm = CLLocationManager()
    private var lastSent = Date.distantPast
    private var sending = false

    private var cfg: [String: Any]? {
        guard let t = AppData.shared.backend["track"] as? [String: Any], t["on"] as? Bool == true else { return nil }
        return t
    }
    var on: Bool { cfg != nil }
    var coll: String { cfg?["coll"] as? String ?? "" }
    func onTheWay(_ status: String) -> Bool { (cfg?["statuses"] as? [String] ?? []).contains(status) }
    /// This build may share location in the background (the build adds the location background mode when tracking is on).
    var declared: Bool { (Bundle.main.object(forInfoDictionaryKey: "UIBackgroundModes") as? [String] ?? []).contains("location") }

    func load() async {
        guard Auth.shared.isStaff, on else { return }
        let r = await Cloud.call("GET", "/track/me", nil, token: Auth.shared.token)
        if r.ok { onShift = r.body["on"] as? Bool ?? false; if onShift { begin() } }
    }

    func setShift(_ start: Bool) async -> String? {
        let r = await Cloud.call("POST", "/track/shift", ["on": start], token: Auth.shared.token)
        guard r.ok else { return r.error.isEmpty ? (r.offline ? Words.offline : Words.tryAgain) : r.error }
        onShift = start
        if start { begin() } else { lm.stopUpdatingLocation() }
        return nil
    }

    private func begin() {
        lm.delegate = self
        lm.desiredAccuracy = kCLLocationAccuracyNearestTenMeters
        lm.distanceFilter = 15                                   // battery: a point only when the phone moved 15 m
        lm.activityType = .automotiveNavigation
        lm.pausesLocationUpdatesAutomatically = true
        if declared {
            lm.allowsBackgroundLocationUpdates = true
            lm.showsBackgroundLocationIndicator = true
        }
        switch lm.authorizationStatus {
        case .notDetermined: lm.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways: lm.startUpdatingLocation()
        default: break
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        Task { @MainActor in
            let st = m.authorizationStatus
            if onShift && (st == .authorizedWhenInUse || st == .authorizedAlways) { lm.startUpdatingLocation() }
        }
    }

    nonisolated func locationManager(_ m: CLLocationManager, didUpdateLocations locs: [CLLocation]) {
        guard let l = locs.last else { return }
        Task { @MainActor in await send(l) }
    }

    private func send(_ l: CLLocation) async {
        let moving = l.speed > 1
        guard !sending, Date().timeIntervalSince(lastSent) >= (moving ? 5 : 30) else { return }
        sending = true
        lastSent = Date()
        var b: [String: Any] = ["lat": l.coordinate.latitude, "lng": l.coordinate.longitude]
        if l.horizontalAccuracy >= 0 { b["acc"] = l.horizontalAccuracy }
        if l.speed >= 0 { b["speed"] = l.speed }
        if l.course >= 0 { b["heading"] = l.course }
        let r = await Cloud.call("POST", "/track/pos", b, token: Auth.shared.token)
        sending = false
        if [401, 403, 409].contains(r.code) { onShift = false; lm.stopUpdatingLocation() }   // the shift ended elsewhere
    }

    /// From the live stream ("pos" events).
    func onPos(_ e: [String: Any]) {
        let k = e["member"] as? String ?? ""
        if e["off"] as? Bool == true || e["lat"] == nil {
            riders[k] = nil
        } else if let la = e["lat"] as? Double, let lo = e["lng"] as? Double {
            let orders: [String] = (e["orders"] as? [String]) ?? Array((e["orders"] as? [String: Any] ?? [:]).keys)
            riders[k] = (TrackPin(id: k, at: CLLocationCoordinate2D(latitude: la, longitude: lo), label: e["name"] as? String ?? "", kind: "rider"), orders)
        }
        tick += 1
    }
}

/// A map with the given pins (Apple Maps), following them as they move.
struct LiveMap: View {
    let pins: [TrackPin]
    @State private var region = MKCoordinateRegion(center: CLLocationCoordinate2D(latitude: 22.6, longitude: 78.96),
                                                   span: MKCoordinateSpan(latitudeDelta: 20, longitudeDelta: 20))
    var body: some View {
        Map(coordinateRegion: $region, annotationItems: pins) { p in
            MapAnnotation(coordinate: p.at) {
                Circle().fill(p.kind == "dest" ? Color.red : Color(red: 0.12, green: 0.62, blue: 0.35))
                    .frame(width: 16, height: 16).overlay(Circle().stroke(.white, lineWidth: 3)).shadow(radius: 2)
                    .accessibilityLabel(p.label)
            }
        }
        .frame(height: 260)
        .clipShape(RoundedRectangle(cornerRadius: H.radius))
        .onAppear { fit() }
        .onChange(of: pins.map { "\($0.at.latitude),\($0.at.longitude)" }) { _ in withAnimation { fit() } }
    }

    private func fit() {
        guard !pins.isEmpty else { return }
        let la = pins.map { $0.at.latitude }, lo = pins.map { $0.at.longitude }
        let c = CLLocationCoordinate2D(latitude: (la.min()! + la.max()!) / 2, longitude: (lo.min()! + lo.max()!) / 2)
        let span = MKCoordinateSpan(latitudeDelta: max(0.01, (la.max()! - la.min()!) * 1.6), longitudeDelta: max(0.01, (lo.max()! - lo.min()!) * 1.6))
        region = MKCoordinateRegion(center: c, span: span)
    }
}

/// Staff: Start shift / End shift with the plain notice first. Nothing when tracking is off.
struct ShiftBlock: View {
    @ObservedObject private var track = Track.shared
    @ObservedObject private var auth = Auth.shared
    @State private var ask = false
    @State private var busy = false
    @State private var error = ""
    init() {}
    var body: some View {
        if auth.isStaff && track.on {
            VStack(alignment: .leading, spacing: 8) {
                Muted(track.onShift ? Words.shiftOnNote : Words.shiftOffNote)
                if !error.isEmpty { Text(error).foregroundStyle(.red).font(.subheadline) }
                MainButton(text: track.onShift ? Words.endShift : Words.startShift) {
                    if busy { return }
                    if track.onShift {
                        busy = true
                        Task { error = await track.setShift(false) ?? ""; busy = false }
                    } else { ask = true }
                }
            }
            .task(id: auth.me?.id) { await track.load() }
            .alert(Words.shareTitle, isPresented: $ask) {
                Button(Words.cont) { busy = true; Task { error = await track.setShift(true) ?? ""; busy = false } }
                Button(Words.later, role: .cancel) {}
            } message: { Text(Words.shareWhy) }
        }
    }
}

/// The customer's own order on its way: the rider on the map, how far, about how long; near / arrived.
struct TrackOrderBlock: View {
    let coll: String
    let id: String
    @ObservedObject private var track = Track.shared
    @ObservedObject private var live = Live.shared
    @State private var info: [String: Any]? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let i = info {
                let rd = i["rider"] as? [String: Any]
                if i["arrived"] as? Bool == true { Text(Words.riderArrived).font(.headline) }
                else if i["near"] as? Bool == true { Text(Words.riderNear).font(.headline) }
                else if i["tracking"] as? Bool == true { Text(((rd?["name"] as? String) ?? Words.rider) + " · " + Words.onTheWay).font(.headline) }
                else { Muted(Words.notOnTheWay) }
                if let eta = i["eta_min"] as? Int {
                    Muted(Words.about + " \(eta) min · " + String(format: "%.1f km", i["km"] as? Double ?? 0) + " · " + Words.estimate)
                }
                let pins = pinsFor(i, rd)
                if !pins.isEmpty { LiveMap(pins: pins) }
            }
        }
        .task(id: "\(id)#\(track.tick / 3)#\(live.revOf(coll))") {
            let r = await Cloud.call("GET", "/track/c/\(coll)/\(id)", nil, token: Auth.shared.token)
            if r.ok { info = r.body }
        }
    }

    private func pinsFor(_ i: [String: Any], _ rd: [String: Any]?) -> [TrackPin] {
        var out: [TrackPin] = []
        if let live = track.riders.values.first(where: { $0.1.contains(id) })?.0 {
            out.append(live)
        } else if let la = rd?["lat"] as? Double, let lo = rd?["lng"] as? Double {
            out.append(TrackPin(id: "rider", at: CLLocationCoordinate2D(latitude: la, longitude: lo), label: Words.rider, kind: "rider"))
        }
        if let d = i["dest"] as? [String: Any], let la = d["lat"] as? Double, let lo = d["lng"] as? Double {
            out.append(TrackPin(id: "dest", at: CLLocationCoordinate2D(latitude: la, longitude: lo), label: Words.yourPlace, kind: "dest"))
        }
        return out
    }
}

/// Staff: every rider on shift on one map, moving as they move.
struct RidersMap: View {
    @ObservedObject private var track = Track.shared
    @ObservedObject private var auth = Auth.shared
    @State private var list: [Item] = []
    init() {}
    var body: some View {
        if auth.isStaff && track.on {
            let pins = merged()
            VStack(alignment: .leading, spacing: 8) {
                Text(Words.ridersOnShift + " (\(pins.count))").font(.headline)
                if pins.isEmpty { Muted(Words.nobodyOnShift) } else { LiveMap(pins: pins) }
            }
            .task {
                let r = await Cloud.call("GET", "/track/riders", nil, token: auth.token)
                if r.ok { list = items(r.body["riders"]) }
            }
        }
    }

    private func merged() -> [TrackPin] {
        var m: [String: TrackPin] = [:]
        for x in list where x.has("lat") {
            m[x.s("member")] = TrackPin(id: x.s("member"), at: CLLocationCoordinate2D(latitude: x.n("lat"), longitude: x.n("lng")), label: x.s("name"), kind: "rider")
        }
        for (k, v) in track.riders { m[k] = v.0 }
        return m.values.sorted { $0.label < $1.label }
    }
}

/// On a row card: "Track live" while that row is on its way.
struct TrackButton: View {
    let coll: String
    let r: Item
    @ObservedObject private var track = Track.shared
    @State private var open = false
    var body: some View {
        if track.on && coll == track.coll && track.onTheWay(r.s("status")) && !r.b("pending") {
            VStack(alignment: .leading, spacing: 8) {
                Button(open ? Words.hideMap : Words.trackLive) { open.toggle() }.buttonStyle(.bordered)
                if open { TrackOrderBlock(coll: coll, id: r.id) }
            }
        }
    }
}

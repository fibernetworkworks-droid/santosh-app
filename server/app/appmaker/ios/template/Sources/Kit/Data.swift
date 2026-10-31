// Made by Hoola App Sahayak (v0.332 IPHONE). The business's data: facts and lists from the build (seed.json), refreshed
// from her Hoola server when it answers; the cart and the form the user is filling.
import Foundation
import SwiftUI

/// One record (product, order, booking ...). Reads never fail: a missing key gives "" / 0.
struct Item: Identifiable {
    let o: [String: Any]
    var id: String { let i = s("id"); return i.isEmpty ? s("name") : i }
    func s(_ k: String, _ d: String = "") -> String {
        guard let v = o[k], !(v is NSNull) else { return d }
        if let x = v as? String { return x }
        if let x = v as? NSNumber { return x.stringValue }
        return d
    }
    func n(_ k: String) -> Double {
        if let x = o[k] as? NSNumber { return x.doubleValue }
        return Double(s(k)) ?? 0
    }
    func b(_ k: String) -> Bool {
        if let x = o[k] as? Bool { return x }
        if let x = o[k] as? NSNumber { return x.boolValue }
        return false
    }
    func has(_ k: String) -> Bool { !s(k).isEmpty }
    func strings(_ k: String) -> [String] { (o[k] as? [Any])?.compactMap { $0 as? String } ?? [] }
    var name: String { let t = s("name"); return t.isEmpty ? s("title", id) : t }
    var price: Double { n("price") }
}

func items(_ a: Any?) -> [Item] {
    ((a as? [Any]) ?? []).compactMap { $0 as? [String: Any] }.map { Item(o: $0) }
}

final class AppData: ObservableObject {
    static let shared = AppData()
    @Published private(set) var root: [String: Any] = [:]
    @Published private(set) var backend: [String: Any] = [:]
    var facts: Item { Item(o: root["facts"] as? [String: Any] ?? [:]) }
    var appName: String { facts.s("name", AppTokens.appName) }

    func load() {
        var seed = Data("{}".utf8)
        if let u = Bundle.main.url(forResource: "seed", withExtension: "json"), let d = try? Data(contentsOf: u) { seed = d }
        if let o = try? JSONSerialization.jsonObject(with: seed) as? [String: Any], let b = o["backend"] as? [String: Any] {
            backend = b
        }
        if let cached = UserDefaults.standard.data(forKey: "hoola_content") { apply(cached) } else { apply(seed) }
    }

    func apply(_ data: Data) {
        guard let o = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
        root = o
        if let b = o["backend"] as? [String: Any], b["collections"] != nil { backend = b }
    }

    func list(_ name: String) -> [Item] { items((root["lists"] as? [String: Any])?[name]) }
    func byId(_ list: String, _ id: String) -> Item? { self.list(list).first { $0.id == id } }

    /// Fresh public content from her Hoola (her facts, products, the app's lists). Never throws.
    func refresh() async {
        guard Cloud.ready, let url = URL(string: "\(Cloud.base)/api/app-content/\(Cloud.key)") else { return }
        guard let (d, r) = try? await URLSession.shared.data(from: url), (r as? HTTPURLResponse)?.statusCode == 200 else { return }
        guard (try? JSONSerialization.jsonObject(with: d) as? [String: Any])?["facts"] != nil else { return }
        UserDefaults.standard.set(d, forKey: "hoola_content")
        await MainActor.run { self.apply(d) }
    }
}

/// What the user is doing now: cart, form values, chosen options. Survives screen changes.
final class AppState: ObservableObject {
    static let shared = AppState()
    @Published var cart: [String: Int] = [:]
    @Published var form: [String: String] = [:]

    func add(_ id: String, _ q: Int = 1) { cart[id] = (cart[id] ?? 0) + q }
    func setQty(_ id: String, _ q: Int) { if q <= 0 { cart.removeValue(forKey: id) } else { cart[id] = q } }
    var cartCount: Int { cart.values.reduce(0, +) }
    func cartItems(_ list: String = "products") -> [(Item, Int)] {
        cart.compactMap { id, q in AppData.shared.byId(list, id).map { ($0, q) } }.sorted { $0.0.name < $1.0.name }
    }
    func cartTotal(_ list: String = "products") -> Double { cartItems(list).reduce(0) { $0 + $1.0.price * Double($1.1) } }
    func binding(_ key: String) -> Binding<String> {
        Binding(get: { self.form[key] ?? "" }, set: { self.form[key] = String($0.prefix(500)) })
    }
}

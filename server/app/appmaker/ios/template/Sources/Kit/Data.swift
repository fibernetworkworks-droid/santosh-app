// Made by Hoola App Sahayak (v0.332 IPHONE). The business's data: facts and lists from the build (seed.json), refreshed
// from her Hoola server when it answers; the cart and the form the user is filling.
import Foundation
import SwiftUI

/// One record (product, order, booking ...). Reads never fail: a missing key gives "" / 0.
struct Item: Identifiable {
    let o: [String: Any]
    /// a record's id; a field / option row (no id) is identified by its key, else its name
    var id: String {
        for k in ["id", "key", "name"] { let v = s(k); if !v.isEmpty { return v } }
        return String(describing: o.keys.sorted())
    }
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
    /// v0.362 VARIANTS: a cart line - a product, or one of its sizes ("pid::vid" -> "Atta (5 kg)" at that size's price).
    func lineItem(_ list: String, _ id: String) -> Item? {
        let parts = id.components(separatedBy: "::")
        guard parts.count == 2 else {
            guard let p = byId(list, id), items(p.o["variants"]).isEmpty else { return nil }
            return p
        }
        guard let p = byId(list, parts[0]), let v = items(p.o["variants"]).first(where: { $0.id == parts[1] }) else { return nil }
        var o = p.o
        o["id"] = id
        o["name"] = p.name + " (" + v.s("name") + ")"
        o["price"] = v.price
        o.removeValue(forKey: "variants"); o.removeValue(forKey: "stock"); o.removeValue(forKey: "sold_out")
        if let n = v.o["stock"] as? NSNumber { o["stock"] = n }
        if v.b("sold_out") { o["sold_out"] = true }
        return Item(o: o)
    }

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
    @Published var coupon = ""                        // v0.358 the code the cart checked (the server applies it again)
    @Published var couponOff = 0.0                    // ... and the discount it said, for the shown total
    @Published var slot = ""                          // v0.371 the delivery slot she picked

    /// v0.357 STOCK: never more than the business has (the server checks again when the order is sent).
    func maxQty(_ id: String) -> Int {
        guard let p = AppData.shared.lineItem("products", id), let n = p.o["stock"] as? NSNumber else { return 99 }
        return max(0, min(99, n.intValue))
    }
    func add(_ id: String, _ q: Int = 1) { setQty(id, (cart[id] ?? 0) + q) }
    func setQty(_ id: String, _ q: Int) { let n = min(q, maxQty(id)); if n <= 0 { cart.removeValue(forKey: id) } else { cart[id] = n } }
    var cartCount: Int { cart.values.reduce(0, +) }
    func cartItems(_ list: String = "products") -> [(Item, Int)] {
        cart.compactMap { id, q in AppData.shared.lineItem(list, id).map { ($0, q) } }.sorted { $0.0.name < $1.0.name }   // v0.362
    }
    func cartTotal(_ list: String = "products") -> Double { cartItems(list).reduce(0) { $0 + $1.0.price * Double($1.1) } }
    func binding(_ key: String) -> Binding<String> {
        Binding(get: { self.form[key] ?? "" }, set: { self.form[key] = String($0.prefix(500)) })
    }
}

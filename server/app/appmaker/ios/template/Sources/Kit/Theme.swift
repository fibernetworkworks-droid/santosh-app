// Made by Hoola App Sahayak (v0.332 IPHONE). The approved design's colours for light and dark mode, its corner radius
// and the app's words. AppTokens (generated per app) holds the values; screens read them through H.c(scheme).
import SwiftUI

extension Color {
    init(hex: String) {
        var s = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.hasPrefix("#") { s.removeFirst() }
        var v: UInt64 = 0
        Scanner(string: s).scanHexInt64(&v)
        if s.count == 6 {
            self.init(.sRGB, red: Double((v >> 16) & 0xFF) / 255, green: Double((v >> 8) & 0xFF) / 255,
                      blue: Double(v & 0xFF) / 255, opacity: 1)
        } else {
            self.init(.sRGB, red: 0.5, green: 0.5, blue: 0.5, opacity: 1)
        }
    }
}

struct Palette {
    let bg: Color
    let surface: Color
    let ink: Color
    let muted: Color
    let line: Color
    let primary: Color
    let onPrimary: Color
    let accent: Color
    let tint: Color
}

enum H {
    /// The palette for the current light / dark scheme (a light-only or dark-only design keeps its one palette).
    static func c(_ scheme: ColorScheme) -> Palette {
        switch AppTokens.mode {
        case "light": return AppTokens.light
        case "dark": return AppTokens.dark
        default: return scheme == .dark ? AppTokens.dark : AppTokens.light
        }
    }
    static var radius: CGFloat { AppTokens.radius }
}

/// Indian rupees: ₹1,25,000
func rupees(_ v: Double) -> String {
    let f = NumberFormatter()
    f.numberStyle = .currency
    f.locale = Locale(identifier: "en_IN")
    f.maximumFractionDigits = v.truncatingRemainder(dividingBy: 1) == 0 ? 0 : 2
    return f.string(from: NSNumber(value: v)) ?? "₹\(v)"
}

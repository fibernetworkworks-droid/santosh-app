// Made by Hoola App Sahayak (v0.347 BHASHA), the iPhone twin of Lang.kt: every screen's words go through T("English
// words"); the table (Resources/i18n.json, made by Hoola at build time) holds the translations; the customer picks the
// language on My account (kept on the phone). Her business data (product names, prices, rows) is shown as typed.
import SwiftUI

@MainActor
final class I18n: ObservableObject {
    static let shared = I18n()
    @Published private(set) var lang = "en"
    private(set) var langs: [String] = ["en"]
    private(set) var names: [String: String] = ["en": "English"]
    nonisolated(unsafe) static var table: [String: [String: String]] = [:]
    nonisolated(unsafe) static var current = "en"
    private var fallback = "en"

    /// At app start: the table from the build + the customer's own choice (else the business's language).
    func load(_ appLanguage: String) {
        fallback = appLanguage
        if let u = Bundle.main.url(forResource: "i18n", withExtension: "json"), let d = try? Data(contentsOf: u),
           let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
            langs = (o["langs"] as? [String]) ?? ["en"]
            names = (o["names"] as? [String: String]) ?? ["en": "English"]
            I18n.table = (o["t"] as? [String: [String: String]]) ?? [:]
            fallback = (o["default"] as? String) ?? appLanguage
        }
        let chosen = UserDefaults.standard.string(forKey: "hoola_lang") ?? ""
        set(!chosen.isEmpty && langs.contains(chosen) ? chosen : fallback, save: false)
    }

    func set(_ code: String, save: Bool = true) {
        lang = code
        I18n.current = code
        if save { UserDefaults.standard.set(code, forKey: "hoola_lang") }
    }
}

/// The screen's words in the customer's language (English words are the key; untranslated = as written).
func T(_ s: String) -> String {
    let l = I18n.current
    return l == "en" ? s : (I18n.table[l]?[s] ?? s)
}

/// The language choice on My account (only when the app carries more than one language).
struct LanguagePicker: View {
    @ObservedObject private var i18n = I18n.shared
    var body: some View {
        if i18n.langs.count > 1 {
            VStack(alignment: .leading, spacing: 6) {
                Text(T("Language")).font(.subheadline.weight(.semibold))
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(i18n.langs, id: \.self) { code in
                            Button(i18n.names[code] ?? code) { i18n.set(code) }
                                .buttonStyle(.bordered)
                                .tint(i18n.lang == code ? .accentColor : .secondary)
                        }
                    }
                }
            }
        }
    }
}

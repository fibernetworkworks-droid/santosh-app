// Made by Hoola App Sahayak (v0.332 IPHONE). The shell (tabs + a navigation stack per tab, routes by screen id), the
// page and card components every screen is built from, and the kit's own words in the app's language.
import SwiftUI

enum Words {
    private static func t(_ en: String, _ hi: String, _ hing: String) -> String {
        switch I18n.current { case "hi": return hi; case "hinglish": return hing; case "en": return en; default: return T(en) }   // v0.347
    }
    static var offline: String { t("No internet. Please try again.", "इंटरनेट नहीं है। फिर कोशिश करें।", "Internet nahi hai. Phir koshish karein.") }
    static var tryAgain: String { t("Something went wrong. Please try again.", "कुछ गड़बड़ हुई। फिर कोशिश करें।", "Kuch gadbad hui. Phir koshish karein.") }
    static var loginAgain: String { t("Please sign in again.", "कृपया फिर से साइन इन करें।", "Kripya phir se sign in karein.") }
    static var notSaved: String { t("It could not be saved.", "सेव नहीं हो पाया।", "Save nahi ho paya.") }
    static var staffOnly: String { t("Only staff can add this.", "इसे सिर्फ़ स्टाफ़ जोड़ सकता है।", "Ise sirf staff jod sakta hai.") }
    static var required: String { t("please fill this", "यह भरना ज़रूरी है", "yeh bharna zaroori hai") }
    static var cartEmpty: String { t("Your cart is empty.", "आपका कार्ट खाली है।", "Aapka cart khaali hai.") }
    static var saved: String { t("Saved. It reaches us as soon as you are online.", "सेव हो गया। ऑनलाइन होते ही पहुँच जाएगा।", "Save ho gaya. Online hote hi pahunch jayega.") }
    static var signIn: String { t("Sign in", "साइन इन", "Sign in") }
    static var createAccount: String { t("Create account", "अकाउंट बनाएँ", "Account banaiye") }
    static var email: String { t("Email", "ईमेल", "Email") }
    static var password: String { t("Password", "पासवर्ड", "Password") }
    static var name: String { t("Name", "नाम", "Naam") }
    static var haveAccount: String { t("I already have an account", "मेरा अकाउंट पहले से है", "Mera account pehle se hai") }
    static var newHere: String { t("New here? Create an account", "नए हैं? अकाउंट बनाएँ", "Naye hain? Account banaiye") }
    static var account: String { t("My account", "मेरा अकाउंट", "Mera account") }
    static var signOut: String { t("Sign out", "साइन आउट", "Sign out") }
    static var deleteAccount: String { t("Delete my account", "मेरा अकाउंट हटाएँ", "Mera account hatao") }
    static var deleteWhat: String { t("Your account and everything it holds (orders, bookings, photos) are removed from the server.", "आपका अकाउंट और उसकी सारी जानकारी सर्वर से हट जाएगी।", "Aapka account aur uski saari jaankari server se hat jayegi.") }
    static var nothingYet: String { t("Nothing here yet.", "अभी यहाँ कुछ नहीं है।", "Abhi yahan kuch nahi hai.") }
    static var sending: String { t("Sending…", "भेज रहे हैं…", "Bhej rahe hain…") }
    static var placeOrder: String { t("Place order", "ऑर्डर करें", "Order karein") }
    static var send: String { t("Send", "भेजें", "Bhejiye") }
    static var add: String { t("Add", "जोड़ें", "Jodiye") }
    static var payUpi: String { t("Pay by UPI", "UPI से भुगतान", "UPI se pay karein") }
    static var iPaid: String { t("I have paid", "मैंने भुगतान कर दिया", "Maine pay kar diya") }
    static var utr: String { t("UPI reference / UTR", "UPI रेफ़रेंस / UTR", "UPI reference / UTR") }
    static var privacy: String { t("Privacy policy", "गोपनीयता नीति", "Privacy policy") }
    static var call: String { t("Call", "कॉल करें", "Call karein") }
    // v0.346
    static var addFile: String { t("Attach PDF", "PDF जोड़ें", "PDF jodiye") }
    static var fileFailed: String { t("Please pick a PDF under 10 MB.", "10 MB से छोटी PDF चुनें।", "10 MB se chhoti PDF chuniye.") }
    static var remove: String { t("Remove", "हटाएँ", "Hataiye") }
    // v0.340
    static var scan: String { t("Scan", "स्कैन करें", "Scan karein") }
    static var dashboard: String { t("Dashboard", "डैशबोर्ड", "Dashboard") }
    static var loading: String { t("Loading…", "लोड हो रहा है…", "Load ho raha hai…") }
    static var total: String { t("Total", "कुल", "Total") }
    static var last14: String { t("Last 14 days", "पिछले 14 दिन", "Pichhle 14 din") }
    static var inbox: String { t("Updates", "अपडेट", "Updates") }
    static var inboxEmpty: String { t("No updates yet.", "अभी कोई अपडेट नहीं।", "Abhi koi update nahi.") }
    static var receipt: String { t("Receipt", "रसीद", "Raseed") }           // v0.354 RASEED
    static var invoice: String { t("Tax invoice", "टैक्स इनवॉइस", "Tax invoice") }   // v0.355 GST BILL
    // v0.353 RAAY
    static var rateIt: String { t("How was it? Rate us", "कैसा रहा? रेटिंग दें", "Kaisa raha? Rating dijiye") }
    static var ratingNote: String { t("A few words (optional)", "कुछ शब्द (ज़रूरी नहीं)", "Kuch shabd (zaroori nahi)") }
    static var sendRating: String { t("Send rating", "रेटिंग भेजें", "Rating bhejiye") }
    static var thanksRating: String { t("Thank you!", "धन्यवाद!", "Shukriya!") }
    static var myTeam: String { t("Team", "टीम", "Team") }
    static var openWork: String { t("open", "बाकी", "baaki") }
    // v0.352 KAAM BAANTO
    static var myWork: String { t("My work", "मेरा काम", "Mera kaam") }
    static var takeIt: String { t("I'll take it", "मैं करूँगा", "Main karunga") }
    static var giveBack: String { t("Give back", "वापस दें", "Wapas dein") }
    static var withPerson: String { t("With", "किसके पास", "Kiske paas") }
    static var you: String { t("You", "आप", "Aap") }
    static var notAssigned: String { t("Not assigned", "किसी को नहीं दिया", "Kisi ko nahi diya") }
    static var onIt: String { t("is on it", "इस पर काम कर रहे हैं", "is par kaam kar rahe hain") }
    static var assignedToYou: String { t("Given to you", "आपको सौंपा गया", "Aapko diya gaya") }
    static var newEntry: String { t("New — open the app to see it", "नया — देखने के लिए ऐप खोलें", "Naya — dekhne ke liye app kholiye") }
}

/// Which screen each tab shows and the stack of screens opened on top of it.
@MainActor
final class Router: ObservableObject {
    static let shared = Router()
    @Published var tab = 0
    @Published var paths: [[String]] = Array(repeating: [], count: max(1, AppTokens.tabs.count))

    /// Open a screen: a tab switches tabs; anything else goes on top of the current tab. Unknown ids are ignored.
    func go(_ id: String) {
        if let i = AppTokens.tabs.firstIndex(where: { $0.id == id }) { tab = i; paths[i] = []; return }
        guard AppTokens.screenIds.contains(id) else { return }
        paths[tab].append(id)
    }

    func back() { if !paths[tab].isEmpty { paths[tab].removeLast() } }
}

struct RootView: View {
    @StateObject private var router = Router.shared
    @ObservedObject private var i18n = I18n.shared            // v0.347 a language change redraws every word
    @Environment(\.colorScheme) private var scheme
    var start: String? = nil

    var body: some View {
        let c = H.c(scheme)
        Group {
            if AppTokens.tabs.count > 1 {
                TabView(selection: $router.tab) {
                    ForEach(Array(AppTokens.tabs.enumerated()), id: \.offset) { i, t in
                        NavigationStack(path: $router.paths[i]) {
                            screenView(t.id).navigationDestination(for: String.self) { screenView($0) }
                        }
                        .tabItem { Label(T(t.label), systemImage: t.symbol) }
                        .tag(i)
                    }
                }
            } else {
                NavigationStack(path: $router.paths[0]) {
                    screenView(AppTokens.start).navigationDestination(for: String.self) { screenView($0) }
                }
            }
        }
        .tint(c.primary)
        .id(i18n.lang)
        // debug builds: Hoola's simulator check opens one screen INSIDE the real app (its tab, or pushed on the first tab),
        // so its buttons really navigate and its picture is what a user sees
        .onAppear { if let s = start { router.go(s) } }
    }
}

/// A screen: title, a scrolling column of blocks, an optional sticky bottom action.
struct Page<Content: View>: View {
    let title: String
    var bottom: AnyView? = nil
    @ViewBuilder let content: () -> Content
    @Environment(\.colorScheme) private var scheme

    init(_ title: String, bottom: AnyView? = nil, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.bottom = bottom
        self.content = content
    }

    var body: some View {
        let c = H.c(scheme)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) { content() }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(c.bg.ignoresSafeArea())
        .navigationTitle(title)
        .safeAreaInset(edge: .bottom) {
            if let b = bottom {
                b.padding(.horizontal, 16).padding(.vertical, 10).background(c.surface)
            }
        }
    }
}

struct Card<Content: View>: View {
    @ViewBuilder let content: () -> Content
    @Environment(\.colorScheme) private var scheme
    var body: some View {
        let c = H.c(scheme)
        VStack(alignment: .leading, spacing: 6) { content() }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(c.surface)
            .clipShape(RoundedRectangle(cornerRadius: H.radius, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: H.radius, style: .continuous).stroke(c.line, lineWidth: 1))
    }
}

struct MainButton: View {
    let text: String
    var tonal = false
    let action: () -> Void
    @Environment(\.colorScheme) private var scheme
    var body: some View {
        let c = H.c(scheme)
        Button(action: action) {
            Text(text).font(.headline).frame(maxWidth: .infinity).padding(.vertical, 13)
                .foregroundStyle(tonal ? c.primary : c.onPrimary)
                .background(tonal ? c.tint : c.primary)
                .clipShape(RoundedRectangle(cornerRadius: H.radius * 0.8, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(text)
    }
}

struct Muted: View {
    let text: String
    init(_ text: String) { self.text = text }
    @Environment(\.colorScheme) private var scheme
    var body: some View { Text(text).font(.subheadline).foregroundStyle(H.c(scheme).muted) }
}

struct StatusPill: View {
    let text: String
    @Environment(\.colorScheme) private var scheme
    var body: some View {
        let done = ["Delivered", "Done", "Confirmed", "Active", "Enrolled", "Verified"].contains(text)
        let bad = ["Cancelled", "Expired"].contains(text)
        Text(text).font(.caption.weight(.semibold)).padding(.horizontal, 10).padding(.vertical, 4)
            .foregroundStyle(done ? Color.green : bad ? Color.red : H.c(scheme).primary)
            .background((done ? Color.green : bad ? Color.red : H.c(scheme).primary).opacity(0.14))
            .clipShape(Capsule())
    }
}

/// The business's own list (products, services ...) as cards; products get an Add button for the cart.
struct ListBlock: View {
    let list: String
    var next: String = ""
    @ObservedObject private var data = AppData.shared
    @ObservedObject private var state = AppState.shared
    var body: some View {
        let rows = data.list(list)
        if rows.isEmpty { Muted(Words.nothingYet) }
        ForEach(rows.prefix(60), id: \.id) { r in
            Card {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(r.name).font(.headline)
                        let sub = [r.s("category"), r.s("unit"), r.s("desc")].filter { !$0.isEmpty }.joined(separator: " · ")
                        if !sub.isEmpty { Muted(sub) }
                        if r.price > 0 { Text(rupees(r.price)).font(.subheadline.weight(.semibold)) }
                    }
                    Spacer()
                    if list == "products" {
                        Button(state.cart[r.id] == nil ? Words.add : "✓ \(state.cart[r.id] ?? 0)") { state.add(r.id) }
                            .buttonStyle(.bordered)
                    }
                }
            }
            .onTapGesture { if !next.isEmpty { Router.shared.go(next) } }
        }
    }
}

func openLink(_ s: String) {
    guard let u = URL(string: s) else { return }
    UIApplication.shared.open(u)
}

/// One bottom tab: the screen it opens, its label and an SF Symbol.
struct TabSpec {
    let id: String
    let label: String
    let symbol: String
}

/// The cart when the app keeps no order list on a server (a catalogue app): lines, quantities, total.
struct CartList: View {
    @ObservedObject private var state = AppState.shared
    var body: some View {
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
}

/// Who runs the app (App Store and Indian consumer rules): name, address, hours, phone with a Call button.
struct SellerScreen: View {
    @ObservedObject private var data = AppData.shared
    var body: some View {
        let f = data.facts
        Page(f.s("name", AppTokens.appName)) {
            if f.has("tagline") { Muted(f.s("tagline")) }
            Card {
                if f.has("address") { Label(f.s("address"), systemImage: "mappin.and.ellipse") }
                if f.has("hours") { Label(f.s("hours"), systemImage: "clock") }
                if f.has("email") { Label(f.s("email"), systemImage: "envelope") }
                if f.has("gstin") { Muted("GSTIN " + f.s("gstin")) }
            }
            if f.has("phone") {
                MainButton(text: Words.call) { openLink("tel:" + f.s("phone").filter { $0.isNumber || $0 == "+" }) }
            }
            Button(Words.privacy) { Router.shared.go("privacy") }.font(.footnote)
        }
    }
}

/// The user's account entry on a profile screen: their name when signed in, else Sign in.
struct AccountButton: View {
    @ObservedObject private var auth = Auth.shared
    var body: some View {
        MainButton(text: auth.signedIn ? auth.name : Words.signIn) {
            Router.shared.go(auth.signedIn ? "hoola_account" : "hoola_login")
        }
    }
}

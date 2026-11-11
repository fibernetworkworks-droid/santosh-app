"""v0.332 IPHONE: what Opus is told when it writes one SwiftUI screen of her iPhone app (same design, same rules as the
Android screen; the kit and the house rules are the iOS ones)."""
from __future__ import annotations

import re

from ..android.prompts import backend_line, fill
from .gen import swift_name

KIT_SHEET = """// ---- layout + look (Kit.swift, Theme.swift)
struct Page<Content: View>: View { init(_ title: String, bottom: AnyView? = nil, @ViewBuilder content: @escaping () -> Content) }
    // a scrolling column (spacing 14, padding 16) with the navigation title; bottom = a sticky bottom action: AnyView(MainButton(...))
struct Card<Content: View>: View { init(@ViewBuilder content: @escaping () -> Content) }   // surface + line + design radius
struct MainButton: View { init(text: String, tonal: Bool = false, action: @escaping () -> Void) }
struct Muted: View { init(_ text: String) }
struct StatusPill: View { init(text: String) }
struct ListBlock: View { init(list: String, next: String = "") }   // a catalogue list as cards (products get Add)
struct CartList: View { init() }                                    // the cart lines with steppers + total
struct AccountButton: View { init() }                               // Sign in / the user's name -> account screen
struct StatsBlock: View { init() }        // v0.340 staff dashboard: counts, status mix, 14-day bars (shows nothing to customers)
struct LiveDot: View { init() }           // v0.407 live: green dot + "Shop is online" / staff: how many online (RowsSection is already live - never poll)
struct ShiftBlock: View { init() }        // v0.412 staff: Start / End shift (location shared during the shift; nothing when tracking is off)
struct RidersMap: View { init() }         // v0.412 staff: every rider on shift on a live map
struct TrackOrderBlock: View { init(coll: String, id: String) }   // v0.412 the rider moving to this order + ETA (RowsSection already has Track live)
// v0.425 RANG rich pieces (native): SignatureRow / PhotosRow / VideoRow / AudioRow / RichTextRow(label:key:); RichTextView(text:),
// PhotosStripView(ids:), VideoPlayerView(src:), AudioPlayerView(src:), PdfViewerView(fid:), ServerPhoto(src:height:),
// CalendarBlock(coll:dateKey:), KanbanBlock(coll:), GanttBlock(coll:startKey:endKey:), LineChartView(values:labels:),
// PieChartView(values:labels:), CarouselView(photos:), OnboardingPager(pages: [("Title","words")], done:). Never a web view.
struct PayButton: View { init(coll: String, r: Item) }   // v0.419 "Pay online" on the customer's unpaid order (RowsSection already has it); never a card form
struct ConnectButtons: View { init(coll: String, r: Item) }   // v0.424 staff buttons for her approved connectors (RowsSection has them); never call an outside API or hold a key
struct PlansBlock: View { init() }        // v0.419 AutoPay plans + her own subscriptions with Cancel
struct PartnerJobsBlock: View { init() }  // v0.435 a delivery partner / partner shop's jobs (apply, waiting, take, steps, call, route); only in a partner app
struct TypingLine: View { init(thread: String = "") }   // v0.407 "Asha typing…" in a chat thread ("hoola_chat" has it built in)
struct ScanRow: View { init(label: String, key: String) }   // v0.340 a [scan] field: camera barcode / QR scanner or typed
struct FileRow: View { init(label: String, key: String) }   // v0.346 a [file] field: a PDF from the system file importer
struct StopsBlock: View { init() }        // v0.350 staff: open rows with a [location] on a map, nearest first, Route in Maps
struct RateBox: View { init(coll: String, r: Item) }   // v0.353 the customer rates her finished row once (RowsSection already shows it)
struct AssignBox: View { init(coll: String, r: Item) }   // v0.352 staff row: who has it + assign / take / give back (RowsSection already shows it)
struct InboxButton: View { init() }       // v0.340 the updates inbox ("hoola_inbox")
// v0.802 DEVICE (Device.swift), each only on the user's own tap - never gate the whole app on them:
struct BiometricLock: View { init(reason: String, onOk: @escaping () -> Void) }   // Face ID / Touch ID / passcode before a private part (khata, staff money); show that part only after onOk
struct RateAppButton: View { init() }     // "Rate this app" on a thank-you / account screen (Apple may show nothing; never reward a rating)
struct AddToCalendarButton: View { init(title: String, start: Date, end: Date, location: String = "", notes: String = "") }   // the phone's own new-event sheet for a booking / appointment / class
struct PickContactButton: View { init(onPicked: @escaping (String, String) -> Void) }   // (name, phone) of ONE contact the user taps, no permission - e.g. fill a form's phone
struct RefField: View { init(label: String, to: String, value: Binding<String>) }   // v0.382 a [ref:<list>] field: pick a row of that list (stores its id)
struct WorkflowBox: View { init(coll: String, r: Item) }   // v0.382 the allowed workflow steps / approval waiting (RowsSection already shows it)
struct RelatedBlock: View { init(coll: String, r: Item) }  // v0.382 a row's linked children + Add (RowsSection already shows it)
struct AutoForm: View { init(coll: String, preset: [String: String] = [:], done: @escaping () -> Void = {}) }   // v0.382 every field of a list as a form
enum Logic { static func show(_ r: Item, _ f: Item) -> String; static func refLabel(_ r: Item, _ key: String) -> String }   // v0.382 a link shows its row's name
// staff screens may go to "hoola_approvals" (approvals waiting) and "hoola_data" (every list); formula fields are the server's - never in a form
enum H { static func c(_ scheme: ColorScheme) -> Palette; static var radius: CGFloat }
struct Palette { bg, surface, ink, muted, line, primary, onPrimary, accent, tint: Color }
    // read colours with: @Environment(\\.colorScheme) private var scheme; let c = H.c(scheme)
func rupees(_ v: Double) -> String
func T(_ s: String) -> String      // v0.347 the user-visible literal in the customer's language
func openLink(_ s: String)          // "tel:...", "https://wa.me/91...", "https://maps.apple.com/?q=..."
func payUpi(_ amount: Double, _ note: String)   // the customer's own UPI app, to the business's UPI ID
enum Words { static var add, send, placeOrder, signIn, account, nothingYet, cartEmpty, call, privacy: String }
// ---- navigation
@MainActor final class Router: ObservableObject { static let shared; func go(_ id: String); func back() }
// ---- data (Data.swift)
struct Item: Identifiable { var id: String; var name: String; var price: Double
    func s(_ k: String, _ d: String = "") -> String; func n(_ k: String) -> Double; func b(_ k: String) -> Bool
    func has(_ k: String) -> Bool; func strings(_ k: String) -> [String] }
final class AppData: ObservableObject { static let shared; var facts: Item; var appName: String
    func list(_ name: String) -> [Item]; func byId(_ list: String, _ id: String) -> Item? }
final class AppState: ObservableObject { static let shared; @Published var cart: [String: Int]; @Published var form: [String: String]
    func add(_ id: String, _ q: Int = 1); func setQty(_ id: String, _ q: Int); var cartCount: Int
    func cartItems(_ list: String = "products") -> [(Item, Int)]; func cartTotal(_ list: String = "products") -> Double
    func binding(_ key: String) -> Binding<String> }
    // observe with: @ObservedObject private var data = AppData.shared / @ObservedObject private var state = AppState.shared
// ---- the app's own server (Backend.swift, Accounts.swift) - the kit does all network work, offline-safe
struct FormBlock: View { init(coll: String, then: String = "hoola_account") }   // that list's own fields + the real save button
struct RowsSection: View { init(coll: String) }   // the user's rows of a server list (staff: everyone's, status buttons, UPI paid claim)
@MainActor final class Auth: ObservableObject { static let shared; var signedIn: Bool; var name: String; var isStaff: Bool }
@MainActor final class Db: ObservableObject { static let shared; func rows(_ c: String) -> [Item] }"""

SCREEN_SYSTEM = """You write ONE screen of a native iPhone app in Swift + SwiftUI (iOS 16+), from its approved web design.
The project around it is fixed and already compiles: the app start, tabs + navigation stacks, theme, data, the app's own
backend and the component kit (HoolaKit, same module, no import needed). You only write this one file. It must compile on
the first try with Swift 5 / Xcode 16.

FILE CONTRACT
- Imports: only SwiftUI (always), and if you really need them Foundation, Charts, MapKit.
- Exactly one screen: struct {FN}: View { var body: some View { ... } } created with NO arguments ({FN}()). Private helper
  views (private struct ...: View) and private funcs are fine. No classes, no @main, no global mutable state.
- Wrap the screen in Page("Title") { ... } (Page(title, bottom: AnyView(...)) for a sticky bottom action). Page is a
  scrolling column already: put sections straight inside it. A @ViewBuilder takes at most 10 children: group with VStack /
  Group when you have more. Use ForEach(items, id: \\.id) for lists (Item is Identifiable).
- Navigation: Router.shared.go("screen_id") (a tab id switches tabs, anything else opens on top; Back is automatic).
  Use ONLY these screen ids: {IDS}.
- Data: AppData.shared.list("name") -> [Item]; AppData.shared.facts (Item). Lists that exist (name: keys): {LISTS}.
  Business facts keys: {FACTS}. Cart: AppState.shared.add(item.id), .cartCount, .cartItems(), .cartTotal(), rupees(x).
  Observe what you read (@ObservedObject private var data = AppData.shared) so the screen updates when fresh data lands.
- REAL DATA ON THE SERVER (the app's own backend): lists {BACKEND}. A form that saves = FormBlock(coll: "bookings") (its own
  fields, required checks, sign-in when the list needs it, queued offline). Cart checkout = FormBlock(coll: <order list>)
  (the server prices the cart). The user's own rows = RowsSection(coll: "orders"). Account: Auth.shared.signedIn / .name /
  .isStaff; profile / "my orders" -> Router.shared.go("hoola_account"); sign in -> Router.shared.go("hoola_login").
  NEVER write your own login / sign-up form or any text field for a password.
- Actions: openLink("tel:" + phone), openLink("https://wa.me/91" + phone + "?text=..."), ShareLink(item: text) { ... },
  openLink("https://maps.apple.com/?q=" + address), payUpi(amount, note) (the customer's own UPI app).
- Look: colours ONLY from the design palette: @Environment(\\.colorScheme) private var scheme, let c = H.c(scheme), then
  c.primary / c.accent / c.ink / c.muted / c.surface / c.bg / c.tint / c.line / c.onPrimary. Corners H.radius. Type with
  SwiftUI text styles (.largeTitle .title .title2 .headline .body .subheadline .footnote .caption) + .weight(...), so
  Dynamic Type works. Icons: SF Symbols with Image(systemName:) (common names only: house, cart, bag, person, bell, heart,
  star, plus, minus, magnifyingglass, phone, envelope, mappin.and.ellipse, clock, calendar, gift, tag, truck.box,
  shippingbox, doc.text, creditcard, square.grid.2x2, list.bullet, chevron.right, checkmark, xmark, sparkles, storefront,
  fork.knife, cross.case, graduationcap, book, wrench.and.screwdriver, car, leaf, flame, photo, camera, star.fill, heart.fill).
- v0.347 EVERY word the user reads that you write as a literal goes through T("..."): Text(T("Our menu")),
  MainButton(text: T("Book now")) { ... }, Page(T("Home")) { }. Write the literal in the app's language ({LANG}); the build
  translates it for customers who pick another language. Never wrap data (item.name, prices, facts) or interpolated strings.
- Words: in {LANG}. Real facts only (from facts / lists); a missing fact is left out, never invented.
- Accessibility: every icon-only button gets .accessibilityLabel(...); tap targets at least 44 pt.

NEVER
- SecureField, password / PIN / OTP-for-payment / card number / CVV / UPI PIN fields or text.
- URLSession / network / files / UserDefaults / @AppStorage / Keychain, WKWebView, UIApplication, print / logging,
  reflection, iOS 17+ only APIs (no @Observable, no .onChange(of:) { old, new in }, no ContentUnavailableView,
  no .scrollTargetBehavior, no #Preview), UIKit views.

MATCH THE DESIGN: same sections in the same order, same hierarchy, same words, same actions, but iPhone-native (navigation
title, lists of cards, sheets / menus where the design has popovers). The DESIGN DNA is the app's direction: keep its hero,
signature element and type moves (ZStack layering, offsets, aspectRatio, clipShape, LinearGradient from c colours).
Motion simply: withAnimation(.spring) on taps, .transition(.opacity) for appearing parts; nothing that runs forever.
Keep it under ~250 lines.

HOOLAKIT (exact signatures, use them as written):
{KIT}

Answer with the whole file in ONE ```swift code block and nothing else."""

FIX_SYSTEM = """You fix ONE SwiftUI screen file of an iPhone app that did not compile (or broke a house rule). Same contract as
before (import SwiftUI, one struct {FN}: View created with no arguments, Page("...") { } body, only HoolaKit + SwiftUI,
iOS 16 APIs, ids {IDS}). Fix EVERY listed error; change nothing else. "unable to type-check this expression in reasonable
time" = split the view into smaller private views. If a kit call is wrong, check its exact signature below. Prefer simple,
certain code over clever code.

HOOLAKIT:
{KIT}

Answer with the whole fixed file in ONE ```swift code block and nothing else."""


def screen_system(sid: str, ids: list[str], lists: dict[str, list[str]], facts: list[str], lang: str,
                  backend: dict | None = None) -> str:
    return fill(SCREEN_SYSTEM, FN=swift_name(sid), IDS=", ".join(ids), BACKEND=backend_line(backend),
                LISTS="; ".join(f"{k}: {', '.join(v)}" for k, v in lists.items()) or "(none)",
                FACTS=", ".join(facts) or "(none)", LANG=lang, KIT=KIT_SHEET)


def fix_system(sid: str, ids: list[str]) -> str:
    return fill(FIX_SYSTEM, FN=swift_name(sid), IDS=", ".join(ids), KIT=KIT_SHEET)


def code_of(answer: str) -> str:
    """The Swift file from the model's answer (a ```swift block, else the answer itself)."""
    m = re.search(r"```(?:swift)?\s*\n(.*?)```", answer or "", re.S)
    src = (m.group(1) if m else (answer or "")).strip()
    i = src.find("import SwiftUI")
    return (src[i:] if i > 0 else src) + "\n"

// Made by Hoola App Sahayak (v0.802 DEVICE), the iPhone twin of the Android kit's Device.kt - four things the phone
// itself does, each only on the user's own tap:
// - BiometricLock: Face ID / Touch ID, falling back to the phone's passcode (LocalAuthentication). The app's Info.plist
//   gets NSFaceIDUsageDescription only when a screen uses it.
// - RateAppButton: Apple's own "rate this app" sheet (StoreKit). Apple shows it at most 3 times a year and may show
//   nothing at all, so nothing in the app ever waits for it or depends on it.
// - AddToCalendarButton: Apple's own new-event sheet, filled in (EventKitUI). iOS 17+ needs no calendar permission for
//   it; iOS 16 asks once first (Info.plist calendar keys only when a screen uses it). The user saves or cancels.
// - PickContactButton: Apple's contact picker (ContactsUI). Needs no permission: the app gets ONLY the one contact the
//   user taps (name + first phone number), never the address book.
// The two Apple sheets are presented from a small host view controller (presenting a picker inside a SwiftUI sheet
// shows a blank page on some iOS versions).
import SwiftUI
import UIKit
import LocalAuthentication
import StoreKit
import EventKit
import EventKitUI
import Contacts
import ContactsUI

enum DeviceWords {
    private static func t(_ en: String, _ hi: String, _ hing: String) -> String {
        switch I18n.current { case "hi": return hi; case "hinglish": return hing; case "en": return en; default: return T(en) }
    }
    static var unlock: String { t("Unlock", "अनलॉक करें", "Unlock karein") }
    static var checking: String { t("Checking…", "जाँच हो रही है…", "Jaanch ho rahi hai…") }
    static var noLock: String { t("This phone has no Face ID, Touch ID or passcode set up.", "इस फ़ोन पर Face ID, Touch ID या पासकोड सेट नहीं है।", "Is phone par Face ID, Touch ID ya passcode set nahi hai.") }
    static var notUnlocked: String { t("It did not unlock. Please try again.", "अनलॉक नहीं हुआ। फिर कोशिश करें।", "Unlock nahi hua. Phir koshish karein.") }
    static var rateApp: String { t("Rate this app", "इस ऐप को रेटिंग दें", "Is app ko rating dijiye") }
    static var thanks: String { t("Thank you!", "धन्यवाद!", "Dhanyavaad!") }
    static var addToCalendar: String { t("Add to calendar", "कैलेंडर में जोड़ें", "Calendar mein jodiye") }
    static var calendarDenied: String { t("Calendar not allowed. You can allow it in Settings.", "कैलेंडर की अनुमति नहीं मिली। सेटिंग्स में दे सकते हैं।", "Calendar ki anumati nahi mili. Settings mein de sakte hain.") }
    static var addedToCalendar: String { t("Added to your calendar.", "आपके कैलेंडर में जुड़ गया।", "Aapke calendar mein jud gaya.") }
    static var pickContact: String { t("Pick a contact", "कॉन्टैक्ट चुनें", "Contact chuniye") }
}

// ---------------------------------------------------------------- Face ID / Touch ID / passcode
struct BiometricLock: View {
    let reason: String
    let onOk: () -> Void
    @State private var busy = false
    @State private var note = ""

    init(reason: String, onOk: @escaping () -> Void) {
        self.reason = reason
        self.onOk = onOk
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            MainButton(text: busy ? DeviceWords.checking : DeviceWords.unlock) { unlock() }
            if !note.isEmpty { Muted(note) }
        }
    }

    private func unlock() {
        if busy { return }
        let ctx = LAContext()
        var err: NSError?
        guard ctx.canEvaluatePolicy(.deviceOwnerAuthentication, error: &err) else {
            note = DeviceWords.noLock
            return
        }
        busy = true
        note = ""
        let why = reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? DeviceWords.unlock : reason
        Task { @MainActor in
            var ok = false
            var cancelled = false
            do {
                ok = try await ctx.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: why)
            } catch let e as LAError {
                cancelled = e.code == .userCancel || e.code == .appCancel || e.code == .systemCancel
            } catch {
                ok = false
            }
            busy = false
            if ok {
                onOk()
            } else if !cancelled {
                note = DeviceWords.notUnlocked
            }
        }
    }
}

// ---------------------------------------------------------------- rate the app (Apple decides whether it shows)
struct RateAppButton: View {
    @Environment(\.requestReview) private var requestReview
    @State private var asked = false

    init() {}

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                requestReview()
                asked = true
            } label: {
                Label(DeviceWords.rateApp, systemImage: "star")
            }
            .buttonStyle(.bordered)
            .accessibilityLabel(DeviceWords.rateApp)
            if asked { Muted(DeviceWords.thanks) }
        }
    }
}

// ---------------------------------------------------------------- add an event to the phone's calendar
struct AddToCalendarButton: View {
    let title: String
    let start: Date
    let end: Date
    let location: String
    let notes: String
    @State private var show = false
    @State private var note = ""

    init(title: String, start: Date, end: Date, location: String = "", notes: String = "") {
        self.title = title
        self.start = start
        self.end = end
        self.location = location
        self.notes = notes
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button { open() } label: { Label(DeviceWords.addToCalendar, systemImage: "calendar.badge.plus") }
                .buttonStyle(.bordered)
                .accessibilityLabel(DeviceWords.addToCalendar)
            if !note.isEmpty { Muted(note) }
        }
        .background(EventEditHost(show: $show, title: title, start: start, end: end,
                                  location: location, notes: notes) { saved in
            if saved { note = DeviceWords.addedToCalendar }
        })
    }

    private func open() {
        note = ""
        if #available(iOS 17.0, *) {
            reopen()                             // iOS 17+: Apple's sheet runs on its own, no calendar permission
            return
        }
        let s = EKEventStore()
        Task { @MainActor in                     // iOS 16: the sheet needs calendar access, asked once
            let ok = (try? await s.requestAccess(to: .event)) ?? false
            if ok { reopen() } else { note = DeviceWords.calendarDenied }
        }
    }

    private func reopen() {
        if show {                                // a stale open (sheet swiped away): close, then open again
            show = false
            Task { @MainActor in show = true }
        } else {
            show = true
        }
    }
}

private struct EventEditHost: UIViewControllerRepresentable {
    @Binding var show: Bool
    let title: String
    let start: Date
    let end: Date
    let location: String
    let notes: String
    let done: (Bool) -> Void

    func makeCoordinator() -> Coord { Coord() }

    func makeUIViewController(context: Context) -> UIViewController { UIViewController() }

    func updateUIViewController(_ host: UIViewController, context: Context) {
        let coord = context.coordinator
        coord.finish = { saved in
            show = false
            done(saved)
        }
        if !show {                                  // a sheet swiped away without an answer frees the button again
            if host.presentedViewController == nil { coord.open = false }
            return
        }
        guard !coord.open, host.presentedViewController == nil else { return }
        coord.open = true
        let store = EKEventStore()                  // made after any iOS 16 access answer, so it sees the calendars
        coord.store = store
        let event = EKEvent(eventStore: store)
        event.title = title
        event.startDate = start
        event.endDate = end > start ? end : start.addingTimeInterval(3600)
        if !location.isEmpty { event.location = location }
        if !notes.isEmpty { event.notes = notes }
        if #available(iOS 17.0, *) {} else {
            event.calendar = store.defaultCalendarForNewEvents
        }
        let vc = EKEventEditViewController()
        vc.eventStore = store
        vc.event = event
        vc.editViewDelegate = coord
        DispatchQueue.main.async {
            if host.presentedViewController == nil {
                host.present(vc, animated: true)
            } else {
                coord.open = false
            }
        }
    }

    final class Coord: NSObject, EKEventEditViewDelegate {
        var store: EKEventStore?                    // kept while Apple's sheet is open
        var open = false
        var finish: (Bool) -> Void = { _ in }

        func eventEditViewController(_ controller: EKEventEditViewController, didCompleteWith action: EKEventEditViewAction) {
            let saved = action == .saved
            controller.dismiss(animated: true)
            open = false
            store = nil
            finish(saved)
        }
    }
}

// ---------------------------------------------------------------- pick one contact (no permission)
struct PickContactButton: View {
    let onPicked: (String, String) -> Void
    @State private var show = false

    init(onPicked: @escaping (String, String) -> Void) {
        self.onPicked = onPicked
    }

    var body: some View {
        Button { reopen() } label: { Label(DeviceWords.pickContact, systemImage: "person.crop.circle.badge.plus") }
            .buttonStyle(.bordered)
            .accessibilityLabel(DeviceWords.pickContact)
            .background(ContactPickerHost(show: $show, onPicked: onPicked))
    }

    private func reopen() {
        if show {
            show = false
            Task { @MainActor in show = true }
        } else {
            show = true
        }
    }
}

private struct ContactPickerHost: UIViewControllerRepresentable {
    @Binding var show: Bool
    let onPicked: (String, String) -> Void

    func makeCoordinator() -> Coord { Coord() }

    func makeUIViewController(context: Context) -> UIViewController { UIViewController() }

    func updateUIViewController(_ host: UIViewController, context: Context) {
        let coord = context.coordinator
        coord.finish = { name, phone in
            show = false
            if let name = name { onPicked(name, phone) }
        }
        if !show {                                  // a sheet swiped away without an answer frees the button again
            if host.presentedViewController == nil { coord.open = false }
            return
        }
        guard !coord.open, host.presentedViewController == nil else { return }
        coord.open = true
        let picker = CNContactPickerViewController()
        picker.delegate = coord
        picker.displayedPropertyKeys = [CNContactPhoneNumbersKey]
        DispatchQueue.main.async {
            if host.presentedViewController == nil {
                host.present(picker, animated: true)
            } else {
                coord.open = false
            }
        }
    }

    final class Coord: NSObject, CNContactPickerDelegate {
        var open = false
        var finish: (String?, String) -> Void = { _, _ in }

        func contactPicker(_ picker: CNContactPickerViewController, didSelect contact: CNContact) {
            open = false
            var parts: [String] = []
            if contact.isKeyAvailable(CNContactGivenNameKey), !contact.givenName.isEmpty { parts.append(contact.givenName) }
            if contact.isKeyAvailable(CNContactFamilyNameKey), !contact.familyName.isEmpty { parts.append(contact.familyName) }
            var name = parts.joined(separator: " ")
            if name.isEmpty, contact.isKeyAvailable(CNContactOrganizationNameKey) { name = contact.organizationName }
            var phone = ""
            if contact.isKeyAvailable(CNContactPhoneNumbersKey), let first = contact.phoneNumbers.first {
                phone = String(first.value.stringValue.filter { $0.isNumber || $0 == "+" }.prefix(20))
            }
            finish(String(name.prefix(120)), phone)
        }

        func contactPickerDidCancel(_ picker: CNContactPickerViewController) {
            open = false
            finish(nil, "")
        }
    }
}

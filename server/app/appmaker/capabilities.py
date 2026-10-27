"""v0.131 What a native app can use on Android and iPhone, with the store policy status of each (Google Play policy and the
App Store Review Guidelines as of Oct 2026), the permission / Info.plist key, the native library the build will use, and the
honest alternative when a store does not allow it.

Play status:
  ok          - normal permission or none; just ask at the right moment
  disclosure  - personal / sensitive data: in-app prominent disclosure + consent before the system dialog (User Data policy)
  declaration - a Play Console declaration form (+ video for some) reviewed by Google; allowed only for the stated core use
  restricted  - only for default handlers / special app types (SMS, call log, all files, accessibility, package visibility,
                installing apps); Hoola never promises these and offers the alternative instead
  hoola_never - allowed by some stores but against Hoola's own rules (exact alarms by USE_EXACT_ALARM, battery-optimisation
                exemption requests)
iOS status: ok | entitlement (an Apple capability / entitlement in the developer account) | review (allowed, explained to App
Review) | not_possible (iOS has no such access)."""
from __future__ import annotations

import re
from typing import Any


def _c(label: str, hi: str, play: str, ios: str, android: list[str], plist: list[str], lib: str, ios_lib: str, note: str,
       alt: str = "", words: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"label": label, "hi": hi, "play": play, "ios": ios, "android": android, "plist": plist, "lib": lib,
            "ios_lib": ios_lib, "note": note, "alt": alt, "words": list(words)}


CAPS: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------------- camera, media, files
    "camera": _c("Camera", "camera", "ok", "ok", ["CAMERA"], ["NSCameraUsageDescription"], "CameraX", "AVFoundation",
                 "Ask when she first taps the camera button.", words=("camera", "photo khinch", "selfie")),
    "photo_picker": _c("Pick photos (no permission)", "photo chuniye", "ok", "ok", [], [], "Android Photo Picker (PickVisualMedia)",
                       "PhotosUI PHPicker", "No storage permission at all; the user picks only what she wants to share.",
                       words=("gallery", "photo upload", "image upload")),
    "media_full": _c("Read the whole photo / video library", "poori gallery padhna", "declaration", "review",
                     ["READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO", "READ_MEDIA_VISUAL_USER_SELECTED"], ["NSPhotoLibraryUsageDescription"],
                     "MediaStore", "PhotoKit",
                     "Play's Photo and Video Permissions policy: only apps whose core job is the gallery (editors, backup).",
                     alt="photo_picker", words=("poori gallery", "all photos", "gallery access")),
    "files_saf": _c("Pick / save documents", "file chuniye / save", "ok", "ok", [], [],
                    "Storage Access Framework (OpenDocument / CreateDocument)", "UIDocumentPicker",
                    "No permission: the user picks the file or folder.", words=("pdf upload", "document upload", "file upload", "excel")),
    "all_files": _c("All files on the phone", "phone ki saari files", "restricted", "not_possible", ["MANAGE_EXTERNAL_STORAGE"], [],
                    "-", "-", "Play allows All files access only for file managers, backup and antivirus apps.",
                    alt="files_saf", words=("all files", "saari files", "storage access", "file manager access")),
    "doc_scanner": _c("Document scanner", "document scan", "ok", "ok", [], ["NSCameraUsageDescription"],
                      "ML Kit Document Scanner (no camera permission; Google Play services UI)", "VisionKit VNDocumentCameraViewController",
                      "Auto-crop, enhance, multi-page PDF on the phone.", words=("scan document", "kaagaz scan", "bill scan")),
    "barcode": _c("Barcode / QR scan", "barcode / QR scan", "ok", "ok", ["CAMERA"], ["NSCameraUsageDescription"],
                  "ML Kit Barcode Scanning (+ code scanner UI without camera permission)", "VisionKit DataScannerViewController",
                  "Works offline; EAN, Code128, QR, DataMatrix.", words=("barcode", "qr scan", "scan code", "serial scan")),
    "ocr": _c("Read text from a photo", "photo se text", "ok", "ok", [], [], "ML Kit Text Recognition v2 (Devanagari model)",
              "Vision VNRecognizeTextRequest", "On the phone; nothing uploaded unless she sends it.", words=("ocr", "text read")),
    "signature": _c("Signature on screen", "hastakshar", "ok", "ok", [], [], "Compose Canvas", "PencilKit / Canvas",
                    "A drawn signature is a picture, not a digital signature (IT Act).", words=("signature", "sign")),
    "screen_secure": _c("Block screenshots on sensitive screens", "screenshot band", "ok", "ok", [], [], "WindowManager FLAG_SECURE",
                        "UIScreen.capturedDidChange + hide on capture", "For payslips, patient records, IDs.",
                        words=("screenshot block", "secure screen")),
    # ---------------------------------------------------------------- location, maps
    "location_foreground": _c("Location while the app is open", "location (app khula ho tab)", "disclosure", "ok",
                              ["ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"], ["NSLocationWhenInUseUsageDescription"],
                              "Fused Location Provider", "Core Location (when in use)",
                              "Prominent disclosure before the system dialog; approximate location offered where enough.",
                              words=("location", "gps", "check in", "geo tag")),
    "location_background": _c("Location in the background", "background location", "declaration", "review",
                              ["ACCESS_BACKGROUND_LOCATION"], ["NSLocationAlwaysAndWhenInUseUsageDescription", "UIBackgroundModes: location"],
                              "Fused Location Provider + foreground service type location",
                              "Core Location (always) + significant-change",
                              "Play: declaration form + video showing the feature; only for the core feature (field-force tracking "
                              "during duty hours, with a visible notification). Users can refuse; the app must still work.",
                              alt="fgs_location", words=("background location", "live tracking", "track staff", "24 ghante location")),
    "fgs_location": _c("Trip tracking with a visible notification", "trip tracking (notification ke saath)", "declaration", "review",
                       ["FOREGROUND_SERVICE", "FOREGROUND_SERVICE_LOCATION", "POST_NOTIFICATIONS"], ["UIBackgroundModes: location"],
                       "Foreground service type location (started by the user: 'Duty shuru')",
                       "Core Location background updates with the blue indicator",
                       "Play foreground-service declaration; starts only on the user's tap, stops at 'Duty khatam'.",
                       words=("trip tracking", "duty tracking")),
    "geofence": _c("Geofence (inside office / site)", "ghera", "disclosure", "ok",
                   ["ACCESS_FINE_LOCATION"], ["NSLocationWhenInUseUsageDescription"],
                   "Checked in the app at punch time (no background geofencing needed)", "Core Location region check at punch",
                   "Background geofence alerts would need background location; attendance checks the fence when she punches.",
                   words=("geofence", "office ke andar")),
    "maps": _c("Maps", "naksha", "ok", "ok", [], [], "MapLibre Native (open tiles) or Google Maps SDK (needs the business's own API key)",
               "MapKit or MapLibre", "Turn-by-turn navigation is handed to Google Maps / Apple Maps by a link.",
               words=("map", "naksha", "gis", "route")),
    "offline_maps": _c("Offline maps", "offline naksha", "ok", "ok", [], [], "MapLibre offline regions (MBTiles / PMTiles)",
                       "MapLibre offline packs", "Tile licence must allow offline use (OpenStreetMap-based tiles do).",
                       words=("offline map", "no network area")),
    "activity": _c("Steps / walking detection", "kadam / chalna", "disclosure", "ok", ["ACTIVITY_RECOGNITION"],
                   ["NSMotionUsageDescription"], "Activity Recognition API", "Core Motion", "Health-style data: disclosure.",
                   words=("steps", "activity")),
    # ---------------------------------------------------------------- notifications, background
    "push_fcm": _c("Push notifications", "push notification", "ok", "ok", ["POST_NOTIFICATIONS"], ["aps-environment (entitlement)"],
                   "Firebase Cloud Messaging", "APNs (via FCM)", "Android 13+ asks; explain first (code-made screen).",
                   words=("notification", "push", "alert")),
    "local_reminders": _c("Reminders at a time", "samay par yaad", "ok", "ok", ["POST_NOTIFICATIONS"], [],
                          "WorkManager / inexact AlarmManager", "UNUserNotificationCenter",
                          "Inexact by a few minutes: fine for reminders.", words=("reminder", "yaad dilao")),
    "exact_alarm": _c("Exact-second alarms", "bilkul sahi samay alarm", "hoola_never", "ok",
                      ["SCHEDULE_EXACT_ALARM", "USE_EXACT_ALARM"], [], "-", "UNCalendarNotificationTrigger",
                      "USE_EXACT_ALARM is only for alarm-clock / calendar apps; Hoola never uses it.",
                      alt="local_reminders", words=("exact alarm",)),
    "background_sync": _c("Sync in the background", "background sync", "ok", "ok", [], ["UIBackgroundModes: fetch"],
                          "WorkManager (network-constrained, retries)", "BGTaskScheduler",
                          "Runs when Android allows; never a battery-optimisation exemption request.",
                          words=("sync", "background upload")),
    "battery_exempt": _c("Ask to skip battery optimisation", "battery optimisation band", "hoola_never", "not_possible",
                         ["REQUEST_IGNORE_BATTERY_OPTIMIZATIONS"], [], "-", "-", "Against Play policy for most apps and Hoola's rules.",
                         alt="background_sync", words=("battery optimisation",)),
    "offline_db": _c("Works offline (local database)", "offline chale", "ok", "ok", [], [], "Room (SQLite) + encrypted DataStore",
                     "SwiftData / SQLite (GRDB)", "Every change queued with a version number; conflicts shown to the user.",
                     words=("offline", "bina net", "no internet")),
    # ---------------------------------------------------------------- identity, security
    "biometrics": _c("Fingerprint / face unlock", "fingerprint", "ok", "ok", ["USE_BIOMETRIC"], ["NSFaceIDUsageDescription"],
                     "BiometricPrompt (BIOMETRIC_STRONG) + Android Keystore", "LocalAuthentication + Keychain",
                     "Unlocks a key on the phone; the fingerprint never leaves the phone.", words=("fingerprint", "face unlock", "biometric")),
    "passkeys": _c("Passkeys", "passkey", "ok", "ok", [], ["associated-domains (webcredentials) entitlement"],
                   "Credential Manager (androidx.credentials)", "AuthenticationServices ASAuthorizationPlatformPublicKeyCredentialProvider",
                   "Needs the business's own domain with assetlinks.json / apple-app-site-association.",
                   words=("passkey", "password-less")),
    "keystore": _c("Secure storage for tokens", "surakshit storage", "ok", "ok", [], [], "Android Keystore + EncryptedFile / Tink",
                   "Keychain", "Tokens never in plain files or logs.", words=()),
    "app_integrity": _c("Genuine app / device check", "asli app jaanch", "ok", "ok", [], ["App Attest entitlement"],
                        "Play Integrity API (server verifies the token)", "DeviceCheck App Attest",
                        "Stops modded apps from calling the server; never blocks rooted phones without saying why.",
                        words=("root detection", "integrity")),
    "sms_retriever": _c("Read the login OTP automatically", "OTP khud bhare", "ok", "ok", [], [],
                        "SMS Retriever API (app-hash in the SMS) / SMS User Consent API", "textContentType = .oneTimeCode",
                        "No SMS permission: Android hands over only the one OTP message.", words=("otp auto", "otp autofill")),
    "sms_read": _c("Read all SMS", "saare SMS padhna", "restricted", "not_possible", ["READ_SMS", "RECEIVE_SMS"], [], "-", "-",
                   "Only the default SMS app (and a few approved exceptions) may read SMS on Play.",
                   alt="sms_retriever", words=("sms padh", "read sms", "sms read", "bank sms")),
    "call_dialer": _c("Call a customer", "call lagao", "ok", "ok", [], [], "Intent ACTION_DIAL (tel:) - no permission",
                      "tel: URL", "The phone's own dialer opens; she presses call.", words=("call", "phone karo")),
    "call_log": _c("Read the call log", "call log padhna", "restricted", "not_possible", ["READ_CALL_LOG"], [], "-", "-",
                   "Only default dialer / caller-ID style apps get it on Play.",
                   alt="call_dialer", words=("call log", "call history", "call record")),
    "call_record": _c("Record phone calls", "call recording", "restricted", "not_possible", [], [], "-", "-",
                      "Third-party call recording is blocked on Android 10+ and by Play's Accessibility policy.",
                      alt="voice_notes", words=("call recording", "record calls")),
    "contacts_pick": _c("Pick one contact", "ek contact chuniye", "ok", "ok", [], [], "Intent ACTION_PICK contact (no permission)",
                        "CNContactPickerViewController", "Only the picked contact is shared with the app.", words=("contact pick",)),
    "contacts_read": _c("Read all contacts", "saare contacts", "disclosure", "ok", ["READ_CONTACTS"], ["NSContactsUsageDescription"],
                        "ContactsContract", "Contacts framework", "Prominent disclosure; never uploaded without consent.",
                        alt="contacts_pick", words=("all contacts", "contacts sync", "phonebook")),
    "phone_state": _c("Phone / SIM details", "SIM jaankari", "disclosure", "not_possible", ["READ_PHONE_STATE"], [],
                      "TelephonyManager", "-", "IMEI is never available to apps (Android 10+).", words=("imei", "sim details")),
    "accessibility": _c("Read / control other apps' screens", "doosre apps padhna", "restricted", "not_possible",
                        ["BIND_ACCESSIBILITY_SERVICE"], [], "-", "-",
                        "Play allows the Accessibility API only for real accessibility tools.",
                        words=("accessibility", "screen read", "auto click")),
    "overlay": _c("Draw over other apps", "doosre apps ke upar", "restricted", "not_possible", ["SYSTEM_ALERT_WINDOW"], [], "-", "-",
                  "Use a notification or bubble instead.", alt="push_fcm", words=("overlay", "floating window")),
    "all_apps": _c("See every installed app", "saare installed apps", "restricted", "not_possible", ["QUERY_ALL_PACKAGES"], [],
                   "-", "-", "Declare only the apps you open in <queries> instead.", alt="share_sheet", words=("installed apps",)),
    "install_apps": _c("Install other apps", "apps install karna", "restricted", "not_possible", ["REQUEST_INSTALL_PACKAGES"], [],
                       "-", "-", "Only for app stores / file managers / MDM.", words=("install apk",)),
    "vpn": _c("VPN", "VPN", "declaration", "entitlement", ["BIND_VPN_SERVICE"], ["Network Extension entitlement"], "VpnService",
              "NetworkExtension", "Play VpnService declaration; only when VPN is the core feature.", words=("vpn",)),
    "device_admin": _c("Company device management", "device management", "declaration", "entitlement", [], ["MDM"],
                       "Android Enterprise (work profile / DPC)", "Apple Business Manager MDM",
                       "Done by an EMM, not by a normal app.", words=("mdm", "lock phone remotely", "kiosk")),
    # ---------------------------------------------------------------- radios, hardware
    "nfc": _c("NFC tags", "NFC tag", "ok", "entitlement", ["NFC"], ["NFCReaderUsageDescription", "NFC Tag Reading entitlement"],
              "NfcAdapter reader mode", "Core NFC", "iPhone reads NDEF tags with the entitlement.", words=("nfc", "tag tap")),
    "bluetooth": _c("Bluetooth devices", "bluetooth", "ok", "ok", ["BLUETOOTH_SCAN (neverForLocation)", "BLUETOOTH_CONNECT"],
                    ["NSBluetoothAlwaysUsageDescription"], "Companion Device Manager / BLE GATT", "Core Bluetooth",
                    "Scan with neverForLocation so no location permission is needed.", words=("bluetooth", "ble", "weighing machine")),
    "bluetooth_printer": _c("Bluetooth bill printer", "bill printer", "ok", "review", ["BLUETOOTH_CONNECT", "BLUETOOTH_SCAN (neverForLocation)"],
                            ["NSBluetoothAlwaysUsageDescription"], "ESC/POS over Bluetooth SPP / BLE", "BLE printers (MFi for classic)",
                            "58 / 80 mm thermal printers; iPhone works with BLE printers.", words=("printer", "thermal print", "bill print")),
    "usb": _c("USB devices (OTG)", "USB", "ok", "not_possible", [], [], "UsbManager", "-", "Scales, scanners, card readers on Android.",
              words=("usb", "otg")),
    "wifi_info": _c("Wi-Fi name / scan", "wifi jaankari", "disclosure", "entitlement", ["ACCESS_WIFI_STATE", "NEARBY_WIFI_DEVICES"],
                    ["Access WiFi Information entitlement"], "WifiManager", "NEHotspotNetwork", "For installers checking a customer's Wi-Fi.",
                    words=("wifi scan", "wifi name")),
    "microphone": _c("Microphone (voice notes)", "mic", "ok", "ok", ["RECORD_AUDIO"], ["NSMicrophoneUsageDescription"],
                     "MediaRecorder", "AVAudioRecorder", "Only while she holds the record button.", words=("voice note", "record audio", "mic")),
    "voice_notes": _c("Voice notes", "voice note", "ok", "ok", ["RECORD_AUDIO"], ["NSMicrophoneUsageDescription"], "MediaRecorder + on-device speech",
                      "AVAudioRecorder + SFSpeechRecognizer", "Text shown next to the note.", words=("voice note",)),
    "speech_to_text": _c("Speak instead of typing", "bolke likho", "ok", "ok", ["RECORD_AUDIO"],
                         ["NSSpeechRecognitionUsageDescription", "NSMicrophoneUsageDescription"], "SpeechRecognizer / Gboard voice typing",
                         "SFSpeechRecognizer", "Hindi / Marathi supported by the phone's recogniser.", words=("voice typing", "bolke")),
    "health_connect": _c("Health Connect / HealthKit", "health data", "declaration", "entitlement", ["health.READ_*"],
                         ["HealthKit entitlement", "NSHealthShareUsageDescription"], "Health Connect", "HealthKit",
                         "Play health apps declaration; only health / fitness apps.", words=("health connect", "healthkit")),
    "ar": _c("AR (place things in the room)", "AR", "ok", "ok", ["CAMERA"], ["NSCameraUsageDescription"], "ARCore (SceneView)",
             "ARKit / RealityKit", "Needs an ARCore-supported phone.", words=("ar", "augmented")),
    "three_d": _c("3D models", "3D", "ok", "ok", [], [], "SceneView / Filament", "SceneKit / RealityKit", "glTF models.",
                  words=("3d model",)),
    # ---------------------------------------------------------------- money, sharing, store
    "upi_intent": _c("Pay by UPI app", "UPI se payment", "ok", "ok", [], ["LSApplicationQueriesSchemes: upi, phonepe, paytmmp, tez"],
                     "upi://pay intent (her own UPI ID) / dynamic QR", "upi:// links to installed UPI apps",
                     "Money goes to the business's own UPI ID; the app never sees a PIN.", words=("upi", "qr payment", "payment")),
    "payment_gateway": _c("Payment gateway", "payment gateway", "ok", "ok", [], [], "The gateway's official Android SDK (Razorpay / PayU / Cashfree...)",
                          "The gateway's iOS SDK", "Card details stay inside the gateway's screen, never in the app.",
                          words=("payment gateway", "card payment")),
    "play_billing": _c("In-app purchase of digital content", "app ke andar digital kharid", "declaration", "review", ["BILLING"], [],
                       "Google Play Billing (required for digital goods; India user-choice billing allowed)", "StoreKit 2",
                       "Physical goods and real-world services use UPI / gateway instead.", words=("subscription", "in-app purchase")),
    "share_sheet": _c("Share to WhatsApp / email", "share", "ok", "ok", [], [], "Intent ACTION_SEND (system share sheet)",
                      "UIActivityViewController", "She picks the app and taps send herself.", words=("share", "whatsapp share")),
    "deep_links": _c("Links open the app", "link se app khule", "ok", "ok", [], ["Associated Domains"], "Android App Links (assetlinks.json)",
                     "Universal Links", "Needs her domain.", words=("deep link", "app link")),
    "widgets": _c("Home-screen widget", "widget", "ok", "ok", [], [], "Jetpack Glance", "WidgetKit", "", words=("widget",)),
    "in_app_update": _c("Update prompt", "update", "ok", "ok", [], [], "Play In-App Updates", "App Store link",
                        "", words=("update",)),
    "in_app_review": _c("Ask for a store rating", "rating", "ok", "ok", [], [], "Play In-App Review", "SKStoreReviewController",
                        "Never rewards or gates ratings.", words=("rating", "review")),
    "calendar": _c("Add to the phone calendar", "calendar", "ok", "ok", [], ["NSCalendarsWriteOnlyAccessUsageDescription"],
                   "Intent INSERT event (no permission)", "EventKit write-only", "", words=("calendar",)),
    "printing": _c("Print / PDF", "print", "ok", "ok", [], [], "Android Print framework", "UIPrintInteractionController", "",
                   words=("print", "pdf")),
    "translation": _c("On-device translation", "anuvaad", "ok", "ok", [], [], "ML Kit Translation", "Translation framework", "",
                      words=("translate",)),
    "crash_reports": _c("Crash reports", "crash report", "disclosure", "ok", [], [], "Firebase Crashlytics (no personal data)",
                        "Crashlytics", "Listed in the Data safety form.", words=()),
}

PLAY_ORDER = {"ok": 0, "disclosure": 1, "declaration": 2, "restricted": 3, "hoola_never": 4}
PLAY_LABEL = {"ok": "Theek", "disclosure": "Pehle batana + haan", "declaration": "Play form + review", "restricted": "Play nahi deta",
              "hoola_never": "Hoola nahi karta"}
IOS_LABEL = {"ok": "Theek", "entitlement": "Apple capability", "review": "App Review ko batana", "not_possible": "iPhone par nahi"}

# screen types -> what they need on the phone
SCREEN_CAPS: dict[str, list[str]] = {
    "scanner_code": ["camera", "barcode"], "doc_scan": ["doc_scanner"], "photo_proof": ["camera", "photo_picker"],
    "signature_pad": ["signature"], "voice_note": ["microphone", "voice_notes"], "nfc_read": ["nfc"],
    "map_live": ["maps", "location_foreground"], "map_layers": ["maps"], "map_draw": ["maps", "location_foreground"],
    "geofence": ["geofence"], "route_plan": ["maps"], "route_nav": ["maps", "location_foreground"],
    "gps_track": ["fgs_location"], "nearby": ["location_foreground"], "offline_maps": ["offline_maps"], "measure": ["maps", "location_foreground"],
    "survey_form": ["location_foreground", "camera", "offline_db"], "attendance_punch": ["location_foreground", "geofence"],
    "file_manager": ["files_saf"], "file_viewer": ["files_saf", "share_sheet"], "upload_queue": ["background_sync"],
    "import_wizard": ["files_saf"], "export_center": ["files_saf", "share_sheet"], "sync_status": ["offline_db", "background_sync"],
    "conflict_resolve": ["offline_db"], "notification_center": ["push_fcm"], "app_lock": ["biometrics", "keystore"],
    "passkey_setup": ["passkeys", "biometrics"], "payment_collect": ["upi_intent"], "pos_billing": ["barcode", "upi_intent"],
    "proof_of_delivery": ["camera", "signature"], "contact_directory": ["call_dialer"], "lead_detail": ["call_dialer", "share_sheet"],
    "payslip": ["screen_secure"], "patient_chart": ["screen_secure"], "invoice_view": ["printing", "share_sheet"],
    "chat_thread": ["photo_picker", "microphone"], "device_control": ["push_fcm"], "login_staff": ["sms_retriever", "keystore"],
    "login": ["sms_retriever", "keystore"], "mfa_verify": ["keystore"],
}


def resolve(ids: list[str]) -> list[str]:
    out: list[str] = []
    for c in ids:
        if c in CAPS and c not in out:
            out.append(c)
    return out


def from_screens(screens: list[str]) -> list[str]:
    out: list[str] = []
    for s in screens:
        for c in SCREEN_CAPS.get(s, []):
            if c not in out:
                out.append(c)
    return out


def from_words(text: str) -> list[str]:
    """Capabilities she named in her words ("sms padhna chahiye", "background location", "fingerprint")."""
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    out: list[str] = []
    for cid, c in CAPS.items():
        for w in c["words"]:
            end = r"(?![\w])" if len(w) < 5 else ""        # longer words take Hinglish endings ("sms padhna", "trackingwala")
            if re.search(r"(?<![\w])" + re.escape(w) + end, t) and cid not in out:
                out.append(cid)
    # a more specific capability wins over its general word ("background location" is not just "location")
    if "location_background" in out and "location_foreground" in out and "background location" in t and t.count("location") == 1:
        out.remove("location_foreground")
    if "media_full" in out and "photo_picker" in out and "gallery" in t and ("poori" in t or "all photos" in t):
        out.remove("photo_picker")
    return out


def check(ids: list[str]) -> dict[str, Any]:
    """Every capability with its policy status; what can't be promised and what to use instead."""
    rows, problems, notes = [], [], []
    for cid in resolve(ids):
        c = CAPS[cid]
        row = {"id": cid, "label": c["label"], "hi": c["hi"], "play": c["play"], "play_label": PLAY_LABEL[c["play"]],
               "ios": c["ios"], "ios_label": IOS_LABEL[c["ios"]], "android": c["android"], "plist": c["plist"], "lib": c["lib"],
               "ios_lib": c["ios_lib"], "note": c["note"], "alt": c["alt"]}
        rows.append(row)
        if c["play"] in ("restricted", "hoola_never"):
            alt = CAPS.get(c["alt"]) if c["alt"] else None
            problems.append({"id": cid, "text": f"{c['label']}: {c['note']}" + (f" Iski jagah: {alt['label']}." if alt else ""),
                             "alt": c["alt"]})
        elif c["play"] == "declaration":
            notes.append({"id": cid, "text": f"{c['label']}: {c['note']}"})
        if c["ios"] == "not_possible" and c["play"] not in ("restricted", "hoola_never"):
            notes.append({"id": cid, "text": f"{c['label']}: iPhone par yeh nahi hota; Android par hi milega."})
    rows.sort(key=lambda r: (PLAY_ORDER[r["play"]], r["id"]))
    return {"caps": rows, "problems": problems, "notes": notes,
            "permissions": sorted({p.split(" ")[0] for r in rows if r["play"] not in ("restricted", "hoola_never") for p in r["android"]}),
            "plist": sorted({p for r in rows if r["play"] not in ("restricted", "hoola_never") for p in r["plist"]})}


def usable(ids: list[str]) -> list[str]:
    """Restricted / never ones replaced by their alternative (the app gets what the stores allow)."""
    out: list[str] = []
    for cid in resolve(ids):
        c = CAPS[cid]
        pick = c["alt"] if c["play"] in ("restricted", "hoola_never") else cid
        if pick and pick in CAPS and pick not in out:
            out.append(pick)
    return out


def counts() -> dict[str, int]:
    from collections import Counter
    k = Counter(c["play"] for c in CAPS.values())
    return {"capabilities": len(CAPS), **{f"play_{a}": b for a, b in k.items()}}


def catalog() -> list[dict[str, Any]]:
    return check(list(CAPS))["caps"]

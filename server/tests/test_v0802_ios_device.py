"""v0.802 DEVICE (iPhone): Face ID lock, rate the app, add to calendar, pick a contact - Device.swift in the kit, named
to the model, and the Info.plist usage strings written only when a screen really uses them."""
from __future__ import annotations

import plistlib
import re
from pathlib import Path

from app.appmaker.ios import gen as IG
from app.appmaker.ios import prompts as IP

KIT = Path(IG.__file__).resolve().parent / "template" / "Sources" / "Kit"
DEVICE = (KIT / "Device.swift").read_text()
PARTS = ("BiometricLock", "RateAppButton", "AddToCalendarButton", "PickContactButton")


def _spec(code: str = "") -> dict:
    spec = {"app": {"name": "Shop"}, "screens": [{"id": "home", "label": "Home"}, {"id": "khata", "label": "Khata"}],
            "tabs": ["home", "khata"]}
    if code:
        spec["screens_swift"] = {"khata": code}
    return spec


def _screen(body: str, fn: str = "ScreenKhata") -> str:
    return f"import SwiftUI\n\nstruct {fn}: View {{\n    var body: some View {{\n        Page(T(\"Khata\")) {{\n{body}\n        }}\n    }}\n}}\n"


def _plist(spec: dict) -> dict:
    return plistlib.loads(IG.info_plist(spec).encode())


def test_device_swift_has_the_four_parts_with_apple_frameworks():
    for n in PARTS:
        assert re.search(rf"\bstruct {n}: View\b", DEVICE), n
    assert "init(reason: String, onOk: @escaping () -> Void)" in DEVICE
    assert "init(title: String, start: Date, end: Date, location: String = \"\", notes: String = \"\")" in DEVICE
    assert "init(onPicked: @escaping (String, String) -> Void)" in DEVICE
    for imp in ("LocalAuthentication", "StoreKit", "EventKit", "EventKitUI", "Contacts", "ContactsUI"):
        assert f"import {imp}\n" in DEVICE, imp
    assert "LAContext()" in DEVICE and ".deviceOwnerAuthentication" in DEVICE      # falls back to the passcode
    assert "canEvaluatePolicy" in DEVICE and "DeviceWords.noLock" in DEVICE          # graceful when nothing is set up
    assert "@Environment(\\.requestReview)" in DEVICE                                # iOS 16 StoreKit action
    assert "EKEventEditViewController()" in DEVICE and "#available(iOS 17.0, *)" in DEVICE
    assert "requestAccess(to: .event)" in DEVICE                                     # iOS 16 asks first
    assert "CNContactPickerViewController()" in DEVICE and "UIViewControllerRepresentable" in DEVICE
    assert "EKEventEditViewDelegate" in DEVICE and "CNContactPickerDelegate" in DEVICE
    assert "@MainActor" in DEVICE                                                    # callbacks back on the main actor
    # iOS 17-only SwiftUI never sneaks in (the kit's deployment target is 16)
    assert IG.MIN_IOS == "16.0"
    for bad in ("@Observable", "ContentUnavailableView", "#Preview", "onChange(of:", "SKStoreReviewController"):
        assert bad not in DEVICE, bad


def test_prompt_names_every_part():
    for n in PARTS:
        assert f"struct {n}: View" in IP.KIT_SHEET, n
    sysmsg = IP.screen_system("home", ["home"], {}, [], "English")
    assert "BiometricLock" in sysmsg and "PickContactButton" in sysmsg


def test_face_id_and_calendar_keys_always_written():
    # Device.swift is in every build, so Apple's upload scan sees LocalAuthentication + EventKit in every binary: the purpose
    # strings must always be there (ITMS-90683), whatever the screens use
    pl = _plist(_spec())
    assert "Face ID" in pl["NSFaceIDUsageDescription"]
    assert pl["NSCalendarsUsageDescription"] and pl["NSCalendarsWriteOnlyAccessUsageDescription"]
    used = _spec(_screen("            BiometricLock(reason: T(\"Open your khata\")) { }"))
    assert not IG.scan_screen(used["screens_swift"]["khata"], "khata", ["home", "khata"])
    assert IG.uses_device(used, "BiometricLock") and not IG.uses_device(_spec(), "BiometricLock")
    bad = _spec(_screen("            BiometricLock(reason: \"x\") { print(1) }"))   # a house-rule breaker is replaced: not counted
    assert not IG.uses_device(bad, "BiometricLock")


def test_contacts_need_no_key():
    con = _plist(_spec(_screen("            PickContactButton { name, phone in AppState.shared.form[\"phone\"] = phone }\n"
                               "            RateAppButton()")))
    assert not [k for k in con if k.startswith("NSContacts")]                        # the picker needs no permission


def test_written_project_carries_device_swift_and_plist(tmp_path):
    spec = _spec(_screen("            BiometricLock(reason: \"Khata\") { }"))
    out = tmp_path / "ios"
    IG.write_project(spec, out)
    assert (out / "Sources/Kit/Device.swift").read_text() == DEVICE
    assert "NSFaceIDUsageDescription" in plistlib.loads((out / "Info.plist").read_bytes())


def test_kit_icon_only_taps_have_labels():
    rich = (KIT / "Rich.swift").read_text()
    assert 'onTapGesture { big = big == s ? "" : s }\n                            .accessibilityLabel(T("Photo"))' in rich
    for f in ("Kit.swift", "Accounts.swift"):
        src = (KIT / f).read_text()
        for m in re.finditer(r"Stepper\(\"\\\(q\)\".*\n(.*)", src):
            assert ".accessibilityLabel(it.name)" in m.group(1), f
    # every Device.swift button carries its words
    assert DEVICE.count(".accessibilityLabel(") >= 3

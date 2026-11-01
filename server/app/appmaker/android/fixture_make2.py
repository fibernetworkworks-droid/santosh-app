"""v0.351 PAKKA SABOOT (App Sahayak Phase 15): writes android/fixture2/spec.json - a second CI app, a field-service STAFF
app made only by the generator (no hand-written screens), whose lists carry every field kind added after Phase 8 (scan,
photo, PDF file, location, status choices) and which ships in Hindi with English as the second language (BHASHA table).
CI compiles it on both platforms, opens every screen and taps every button (Android emulator + iPhone simulator).

    python -m app.appmaker.android.fixture_make2      (from server/)"""
from __future__ import annotations

import json
from pathlib import Path

from .. import kit as K
from . import spec as S

HERE = Path(__file__).resolve().parent / "fixture2"
FIXTURE2_KEY = "akf1c7a2e0000000000000002"

JOBS = {"key": "jobs", "label": "Jobs", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
        "fields": [{"key": "customer", "label": "Customer", "type": "text", "required": True, "admin_only": False},
                   {"key": "phone", "label": "Mobile number", "type": "phone", "required": True, "admin_only": False},
                   {"key": "address", "label": "Site address", "type": "long_text", "required": False, "admin_only": False},
                   {"key": "pin", "label": "Site location", "type": "location", "required": False, "admin_only": False},
                   {"key": "asset_tag", "label": "Asset tag", "type": "scan", "required": False, "admin_only": False},
                   {"key": "photo", "label": "Site photo", "type": "photo", "required": False, "admin_only": False},
                   {"key": "report", "label": "Service report", "type": "file", "required": False, "admin_only": False},
                   {"key": "kind", "label": "Work", "type": "choice", "required": False, "admin_only": False,
                    "options": ["Installation", "Repair", "AMC visit"], "default": "Repair"},
                   {"key": "status", "label": "Status", "type": "choice", "required": False, "admin_only": True,
                    "options": ["New", "Assigned", "On the way", "Done", "Cancelled"], "default": "New"}]}

# the words a real build would get translated by Opus (BHASHA); a fixed table here so CI needs no model
HI = {"Home": "होम", "Jobs": "काम", "Route": "रूट", "Dashboard": "डैशबोर्ड", "Profile": "प्रोफ़ाइल", "New job": "नया काम",
      "Customer": "ग्राहक", "Mobile number": "मोबाइल नंबर", "Site address": "साइट का पता", "Site location": "साइट की लोकेशन",
      "Asset tag": "एसेट टैग", "Site photo": "साइट की फ़ोटो", "Service report": "सर्विस रिपोर्ट", "Work": "काम का प्रकार",
      "Installation": "इंस्टॉलेशन", "Repair": "मरम्मत", "AMC visit": "AMC विज़िट", "New": "नया", "Assigned": "सौंपा गया",
      "On the way": "रास्ते में", "Done": "हो गया", "Cancelled": "रद्द", "Status": "स्थिति", "Send": "भेजें",
      "Today's stops": "आज के स्टॉप", "Route in Maps": "मैप्स में रूट", "No open stops with a location.": "लोकेशन वाला कोई खुला स्टॉप नहीं।",
      "Language": "भाषा", "Book a job": "काम बुक करें", "Open route": "रूट खोलें", "See jobs": "काम देखें",
      "Service on time, every time": "हर बार समय पर सर्विस"}


def main() -> None:
    tk = K.tokens("enterprise_pro", "deep_teal", None, {"nav": "bar", "fab": "none", "mode": "both"})
    plan = {"screens": ["home", "jobs", "new_job", "route", "dashboard", "profile"], "tabs": ["home", "jobs", "route", "profile"],
            "flow": ["home", "new_job", "jobs"], "code_screens": ["seller_info", "privacy", "delete_account"],
            "labels": {"home": "Home", "jobs": "Jobs", "new_job": "New job", "route": "Route", "dashboard": "Dashboard", "profile": "Profile"}}
    facts = {"name": "Kumar Field Service", "tagline": "Service on time, every time", "phone": "9822001100",
             "address": "Plot 7, MIDC, Nashik 422010", "hours": "9 am - 7 pm", "products": []}
    sd = S.seed("Kumar Field Service", "service_request", facts, plan)
    sd["backend"] = {"kind": "customer", "order": "", "signup": True, "collections": [JOBS]}
    screens = S.screens_of(plan, {}, sd)
    acts = {"home": [{"label": "Book a job", "go": "new_job"}, {"label": "Open route", "go": "route"}, {"label": "See jobs", "go": "jobs"}],
            "jobs": [{"label": "Book a job", "go": "new_job"}], "new_job": [{"label": "See jobs", "go": "jobs"}],
            "route": [{"label": "See jobs", "go": "jobs"}], "dashboard": [{"label": "See jobs", "go": "jobs"}],
            "profile": [{"label": "Book a job", "go": "new_job"}]}
    for s in screens:
        s["actions"] = acts[s["id"]]
        s["lists"] = ["jobs"] if s["id"] == "jobs" else []
        s["purpose"] = "Service on time, every time" if s["id"] == "home" else ""
    words = sorted(set(HI))
    spec = {"app": {"name": "Kumar Field Service", "app_id": "in.hoola.preview.fixture2", "version_code": 1, "version_name": "1.0",
                    "language": "hi", "base_url": "https://example.invalid", "app_key": FIXTURE2_KEY},
            "tokens": S.with_tints(tk), "structure": {}, "tabs": plan["tabs"], "start": "home", "flow": plan["flow"],
            "code_screens": plan["code_screens"], "screens": screens, "fab": {}, "icons": S.icon_paths(), "app_icon": "settings",
            "fonts": {}, "seed": sd, "screens_kt": {},
            "i18n": {"default": "hi", "langs": ["hi", "en"], "names": {"hi": "हिन्दी", "en": "English"}, "t": {"hi": {w: HI[w] for w in words}}}}
    HERE.mkdir(exist_ok=True)
    (HERE / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print("fixture2", len(screens), "screens, all code-made; i18n hi", len(words), "words")


if __name__ == "__main__":
    main()

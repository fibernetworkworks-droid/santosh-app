"""Generate one JSON manifest per MVP pack from data/bazar_mvp_rows.json (exported from the 1,000-pack master list).

Run:  python scripts/gen_manifests.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "bazar" / "packs" / "manifests"
ROWS = json.loads((ROOT / "data" / "bazar_mvp_rows.json").read_text())


def slug(s: str) -> str:
    s = s.lower().replace("&", "and").replace("+", "plus")
    s = re.sub(r"\(.*?\)", lambda m: " " + m.group(0)[1:-1] + " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70]


# ---------- L1 official agent endpoints ----------
MCP = {
    "Swiggy Food": ("swiggy_food", "mcp_swiggy_food_url", ["swiggy", "khana", "food", "lunch", "dinner", "biryani", "order food", "jevan"]),
    "Zomato": ("zomato", "mcp_zomato_url", ["zomato", "food", "restaurant", "khana"]),
    "Swiggy Dineout": ("swiggy_dineout", "mcp_swiggy_dineout_url", ["table", "dineout", "book a table", "restaurant booking"]),
    "Zomato District (Dining & Events)": ("district", "mcp_district_url", ["district", "event", "dining offer"]),
    "Swiggy Instamart": ("swiggy_instamart", "mcp_swiggy_instamart_url", ["instamart", "grocery", "doodh", "milk", "sabzi", "kirana", "mangwa"]),
    "Zepto": ("zepto", "mcp_zepto_url", ["zepto", "grocery", "doodh", "milk", "mangwa"]),
}

# ---------- UPI apps (Android package + scheme) ----------
UPI_APPS = {
    "PhonePe": ("com.phonepe.app", "phonepe"),
    "Google Pay": ("com.google.android.apps.nbu.paisa.user", "tez"),
    "Paytm": ("net.one97.paytm", "paytmmp"),
    "BHIM": ("in.org.npci.upiapp", "upi"),
    "Amazon Pay UPI": ("in.amazon.mShop.android.shopping", "upi"),
    "Super.money": ("money.super.payments", "upi"),
    "Pop UPI": ("com.popclub.android", "upi"),
    "Navi UPI": ("com.naviapp", "upi"),
    "CRED UPI": ("com.dreamplug.androidapp", "upi"),
    "MobiKwik": ("com.mobikwik_new", "upi"),
    "Freecharge": ("com.freecharge.android", "upi"),
    "Airtel Thanks (Payments Bank)": ("com.myairtelapp", "upi"),
    "Jio Finance": ("com.jio.jiofinance", "upi"),
    "Kiwi": ("in.gokiwi.kiwitpap", "upi"),
    "Fold Money": ("money.fold.android", "upi"),
}

# ---------- Ride apps ----------
RIDES = {
    "Uber India": {"package": "com.ubercab", "link": "https://m.uber.com/ul/?action=setPickup&pickup[latitude]={plat}&pickup[longitude]={plng}&dropoff[latitude]={dlat}&dropoff[longitude]={dlng}&dropoff[nickname]={dname}", "verified": True},
    "Ola": {"package": "com.olacabs.customer", "link": "https://book.olacabs.com/?lat={plat}&lng={plng}&drop_lat={dlat}&drop_lng={dlng}", "verified": False},
    "Rapido": {"package": "com.rapido.passenger", "link": "", "verified": False},
    "Namma Yatri": {"package": "in.juspay.nammayatri", "link": "", "verified": False},
    "inDrive": {"package": "sinet.startup.inDriver", "link": "", "verified": False},
    "Yatri Sathi (Kolkata)": {"package": "in.juspay.jatrisaathi", "link": "", "verified": False},
    "Kerala Savaari": {"package": "", "link": "", "verified": False},
}

# ---------- Biller input fields ----------
ELEC_FIELDS = {"MSEDCL (Mahavitaran)": ["consumer_number", "billing_unit"]}


def biller_fields(name: str, sub: str) -> tuple[str, list[str]]:
    if sub == "Electricity boards":
        return "electricity", ELEC_FIELDS.get(name, ["consumer_number"])
    if sub == "Piped gas & LPG":
        if "booking" in name.lower():
            return "lpg", ["lpg_id_or_mobile"]
        return "piped_gas", ["customer_id"]
    low = name.lower()
    if "dth" in low or name in ("Tata Play DTH", "Airtel Digital TV", "Dish TV", "d2h", "Sun Direct"):
        return "dth", ["subscriber_id"]
    if name in ("Jio", "Airtel", "Vi (Vodafone Idea)", "BSNL Mobile"):
        return "mobile", ["mobile_number"]
    return "broadband", ["customer_id_or_landline"]


BILLER_KEYWORDS = {
    "electricity": ["bijli", "light bill", "electricity", "vij", "वीज", "बिजली", "lightbill"],
    "piped_gas": ["gas bill", "png", "pipe gas"],
    "lpg": ["cylinder", "lpg", "gas booking", "silender"],
    "mobile": ["recharge", "mobile bill", "postpaid", "prepaid"],
    "dth": ["dth", "tv recharge", "dish"],
    "broadband": ["wifi", "broadband", "internet bill", "fiber"],
}

# ---------- Shop templates ----------
SHOP_MODES = {
    "Kirana store": ("catalog", ["kirana", "dukaan", "dukan", "atta", "tel", "dal", "chawal", "sakhar"]),
    "Dairy / milk centre": ("subscription", ["dairy", "doodh", "dudh", "milk", "dahi", "paneer"]),
    "Vegetable vendor (thela)": ("catalog", ["sabzi", "bhaji", "vegetable", "kanda", "batata", "tamatar"]),
    "Tiffin service": ("subscription", ["tiffin", "dabba", "mess", "jevan"]),
    "Medical store": ("catalog", ["medical", "dawai", "medicine", "goli", "aushadh"]),
    "Clinic (GP)": ("booking", ["doctor", "clinic", "dawakhana", "appointment"]),
    "Salon (men)": ("booking", ["salon", "haircut", "cutting", "dadhi", "shave"]),
    "Laundry": ("booking", ["laundry", "kapde", "dhobi", "wash"]),
    "Electrician": ("booking", ["electrician", "wiring", "fan", "switch", "light nahi"]),
    "Plumber": ("booking", ["plumber", "nal", "leak", "pipe", "tap"]),
    "Bakery": ("catalog", ["bakery", "cake", "bread", "pav", "toast"]),
    "Sweet shop (mithai)": ("catalog", ["mithai", "sweet", "pedha", "laddu", "barfi"]),
    "Chicken & mutton shop": ("catalog", ["chicken", "mutton", "meat", "kombdi"]),
    "Water can supplier (20 L)": ("subscription", ["water can", "jar", "paani", "pani ka can", "20 litre"]),
    "Paper plate & disposables supplier": ("catalog", ["paper plate", "patravali", "dona", "disposable", "glass"]),
    "Local ISP": ("due_payment", ["wifi bill", "internet bill", "isp", "net ka bill"]),
    "Cable TV operator (LCO)": ("due_payment", ["cable", "cable bill", "tv bill"]),
    "Xerox & print shop": ("catalog", ["xerox", "print", "photocopy", "printout"]),
    "Tuition teacher": ("due_payment", ["tuition", "class fees", "tution"]),
    "Gym": ("due_payment", ["gym", "membership"]),
}

SHOP_TOOLS = {
    "catalog": [("search_items", 0), ("build_cart", 1), ("place_order", 2), ("order_status", 0)],
    "subscription": [("search_items", 0), ("build_cart", 1), ("place_order", 2), ("order_status", 0)],
    "booking": [("search_items", 0), ("book_slot", 2), ("order_status", 0)],
    "due_payment": [("get_due", 0), ("pay_due", 2)],
}

# ---------- Native skills ----------
NATIVE = {
    "Reminders & alarms": ("reminders", [("set_reminder", 1), ("list_reminders", 0), ("cancel_reminder", 1)], ["yaad", "remind", "reminder", "alarm", "uthana", "athvan"]),
    "Calendar assistant": ("calendar", [("add_event", 1), ("agenda", 0)], ["meeting", "calendar", "event", "schedule"]),
    "Notes & memory": ("notes", [("save_note", 1), ("search_notes", 0)], ["note", "yaad rakh", "likh lo", "remember"]),
    "Shopping lists": ("lists", [("add_to_list", 1), ("show_list", 0), ("clear_list", 1)], ["list", "yadi", "list mein"]),
    "Morning briefing": ("briefing", [("morning_brief", 0)], ["brief", "aaj ka plan", "good morning", "today"]),
    "Spend report": ("spend", [("import_sms", 1), ("spend_report", 0)], ["kharcha", "spend", "kharch", "expense report"]),
    "Bill reminders hub": ("bill_reminders", [("add_bill_reminder", 1), ("upcoming_bills", 0)], ["bill due", "due date", "emi"]),
    "Expense splitter": ("splitter", [("split_expense", 1)], ["split", "baant", "hissa", "divide"]),
    "Family profiles": ("family", [("save_family_member", 1), ("get_family", 0)], ["family", "mummy", "papa", "wife", "beta", "beti"]),
    "Medicine reminder": ("medicine", [("add_medicine", 1)], ["dawai yaad", "medicine reminder", "goli time", "tablet"]),
    "Birthday & anniversary reminders": ("birthdays", [("add_birthday", 1), ("upcoming_birthdays", 0)], ["birthday", "janamdin", "vadhdivas", "anniversary"]),
    "Festival greetings sender": ("greetings", [("draft_greetings", 0), ("send_greetings", 2)], ["wish", "greeting", "shubhechha", "diwali", "festival"]),
    "WhatsApp marketing automation": ("wa_marketing", [("create_template", 1), ("template_status", 0), ("send_campaign", 2)], ["whatsapp campaign", "marketing", "broadcast", "template"]),
}


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    seen = set()
    for r in ROWS:
        num, name, cat, sub, ptype, task, layer, phase, prio, note = r
        pid = slug(name)
        assert pid not in seen, pid
        seen.add(pid)
        m = {
            "id": pid, "name": name, "category": cat, "sub_category": sub, "pack_type": ptype,
            "layer": layer.split(" ")[0], "phase": phase, "priority": prio, "description": task,
            "notes": note or "", "master_list_row": num,
        }
        if name in MCP:
            prov, cfg, kw = MCP[name]
            m.update(executor="mcp", config={"provider": prov, "endpoint_setting": cfg,
                                             "money_tool_patterns": ["place_order", "checkout", "confirm", "pay", "book", "reserve"]},
                     tools=[], keywords=kw)
        elif name in UPI_APPS:
            pkg, scheme = UPI_APPS[name]
            verified = name in {"PhonePe", "Google Pay", "Paytm", "BHIM", "Amazon Pay UPI", "CRED UPI", "MobiKwik", "Freecharge",
                                "Airtel Thanks (Payments Bank)"}
            m.update(executor="upi", config={"android_package": pkg, "scheme": scheme, "package_verified": verified},
                     tools=[{"name": "send_money", "tier": 3}, {"name": "request_money", "tier": 1}],
                     keywords=["bhejo", "send", "pay", "paise", "transfer", name.lower().split(" ")[0]])
        elif name in RIDES:
            m.update(executor="ride", config=RIDES[name], tools=[{"name": "ride_link", "tier": 1}],
                     keywords=["cab", "auto", "ride", "taxi", "rickshaw", name.lower().split(" ")[0]])
        elif ptype == "Biller pack":
            bcat, fields = biller_fields(name, sub)
            m.update(executor="bbps", config={"biller_category": bcat, "biller_name": name, "input_fields": fields,
                                              "biller_id": None},
                     tools=[{"name": "fetch_bill", "tier": 0}, {"name": "pay_bill", "tier": 2}],
                     keywords=BILLER_KEYWORDS[bcat] + [name.lower().split(" (")[0]])
        elif ptype == "Bazar shop template":
            mode, kw = SHOP_MODES[name]
            m.update(executor="shop", config={"template": pid, "mode": mode},
                     tools=[{"name": t, "tier": tier} for t, tier in SHOP_TOOLS[mode]], keywords=kw)
        elif ptype == "Santosh native skill":
            skill, tools, kw = NATIVE[name]
            m.update(executor="native", config={"skill": skill},
                     tools=[{"name": t, "tier": tier} for t, tier in tools], keywords=kw)
        else:
            raise SystemExit(f"Unmapped MVP pack: {name}")
        (OUT / f"{pid}.json").write_text(json.dumps(m, ensure_ascii=False, indent=2))
    print(f"wrote {len(seen)} manifests to {OUT}")


if __name__ == "__main__":
    main()

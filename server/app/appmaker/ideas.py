"""v0.136 1 crore app ideas: Hoola picks a PRECISE idea from a few of her words and starts the app from it.

An idea = business type (1,000 field cards) x what the app does (10 customer goals that fit that trade + 43 staff / field /
admin archetypes) x who it is for (customer, owner, staff, delivery / service partner, dealer, member / parent, manager) x
the one thing that makes it special (52 feature twists, each fitting only the goals and users it makes sense for) x
scale (one shop, many branches, a whole-city network) x market (town / Hindi-first, metro, all-India languages, NRI /
export) x how it earns or saves money. Only combinations that make sense are counted (`total()` adds them up exactly, it
is never a guess) and every idea is built deterministically from its id, so "1 crore" is a real, browsable, checkable list.

An idea changes the real app plan: extra screens (from the 172 screen types), its tabs for that user, phone features for
the blueprint (Play / App Store rules still decide), the questions Hoola asks, and an IDEA line every screen designer sees."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from typing import Any

from ..site import library as SL
from . import library as L
from . import taxonomy as T

# ---------------------------------------------------------------- which customer goals fit which trade (+ its own default)
SIMPLE_FIT: dict[str, set[str]] = {
    "shop": {"food_shop", "retail", "fashion", "electronics", "crafts", "agriculture", "pets", "kids", "health_allied",
             "trade", "manufacturing", "food_maker", "beauty", "auto", "spiritual", "telecom", "construction", "personal"},
    "food_order": {"restaurant", "food_maker", "food_shop", "hospitality"},
    "booking": {"clinic", "beauty", "wellness", "sports", "coaching", "local_services", "home_services", "repair", "auto",
                "hospitality", "travel", "legal", "finance", "health_allied", "pets", "events", "creative", "personal",
                "spiritual", "real_estate", "it", "kids"},
    "learning": {"coaching", "school", "skills", "sports", "wellness", "spiritual", "creative", "kids", "it", "finance",
                 "agriculture", "health_allied"},
    "membership": {"wellness", "sports", "beauty", "hospitality", "ngo", "spiritual", "kids", "coaching", "retail",
                   "personal", "food_shop", "restaurant"},
    "service_request": {"home_services", "repair", "local_services", "telecom", "it", "auto", "construction",
                        "citizen_services", "logistics", "legal", "finance", "real_estate", "agriculture", "electronics",
                        "health_allied", "staffing", "pets"},
    "khata": {"food_shop", "retail", "trade", "agriculture", "telecom", "electronics", "construction", "manufacturing",
              "local_services", "fashion", "health_allied", "auto", "food_maker"},
    "catalogue": {"fashion", "crafts", "manufacturing", "trade", "real_estate", "electronics", "construction", "creative",
                  "travel", "events", "auto", "agriculture", "retail", "food_maker", "food_shop"},
    "events": {"events", "spiritual", "ngo", "sports", "school", "coaching", "hospitality", "creative", "citizen_services",
               "travel", "kids"},
    "community": {"ngo", "spiritual", "school", "citizen_services", "sports", "kids", "wellness", "skills", "agriculture",
                  "real_estate", "personal"},
}

# ---------------------------------------------------------------- who the app is for
AUD: dict[str, dict[str, Any]] = {
    "customer": {"label": "Customers", "hi": "graahak", "words": ["customer", "graahak", "grahak", "client", "public", "logon ke liye"],
                 "line": "for customers", "goals": "SIMPLE"},
    "owner": {"label": "Owner's own app", "hi": "malik", "words": ["owner", "malik", "mere liye", "apne liye", "dukaan chalane",
                                                                       "business chalane", "hisaab", "dashboard"],
              "line": "for the owner (you): the business at a glance", "goals": "ALL",
              "screens": ["dashboard_kpi", "report_view", "alert_center", "approval_inbox"],
              "tabs": ["dashboard_kpi", "orders", "report_view", "profile"]},
    "staff": {"label": "Staff app", "hi": "staff", "words": ["staff", "karmchari", "employee", "kaam karne wale", "worker", "team"],
              "line": "for staff / team", "goals": "ALL",
              "screens": ["task_list", "task_detail", "attendance_punch", "checklist"],
              "tabs": ["task_list", "attendance_punch", "notifications", "profile"]},
    "partner": {"label": "Delivery / service partner app", "hi": "partner", "line": "for delivery staff / technicians / partners",
                "words": ["delivery boy", "rider", "technician", "partner", "mistri", "agent", "driver"],
                "goals": {"shop", "food_order", "service_request", "catalogue", "khata", "booking"},
                "screens": ["delivery_run", "route_nav", "proof_of_delivery", "payment_collect", "job_card", "photo_proof"],
                "tabs": ["delivery_run", "route_nav", "payment_collect", "profile"]},
    "dealer": {"label": "Dealer / B2B ordering app", "hi": "dealer", "line": "for dealers / retailers / B2B buyers",
               "words": ["dealer", "distributor", "retailer", "wholesale", "b2b", "thok", "stockist", "reseller"],
               "goals": {"shop", "catalogue", "khata"},
               "screens": ["quote_builder", "purchase_order", "invoice_view", "khata"],
               "tabs": ["home", "catalogue", "purchase_order", "khata", "profile"]},
    "member": {"label": "Members / students / parents", "hi": "sadasya", "line": "for members / students / parents",
               "words": ["member", "sadasya", "student", "parent", "abhibhavak", "bachche", "society members"],
               "goals": {"learning", "membership", "community", "events"},
               "screens": ["progress", "member_card", "notifications", "class_attendance"]},
    "manager": {"label": "Manager / supervisor app", "hi": "manager", "line": "for managers / supervisors",
                "words": ["manager", "supervisor", "head", "incharge", "branch manager"], "goals": "COMPLEX",
                "screens": ["dashboard_manager", "approval_inbox", "report_builder", "target_meter", "team_list"],
                "tabs": ["dashboard_manager", "approval_inbox", "team_list", "profile"]},
}
AUD_WORD_ORDER = ["dealer", "partner", "member", "manager", "staff", "owner", "customer"]

# ---------------------------------------------------------------- the one thing that makes it special
C, O, S, P, D, M, G = "customer", "owner", "staff", "partner", "dealer", "member", "manager"
MONEY_SIMPLE = {"shop", "food_order", "booking", "service_request", "membership", "khata", "events", "learning"}
ORDER_SIMPLE = {"shop", "food_order", "catalogue"}
TWISTS: dict[str, dict[str, Any]] = {
    "whatsapp_first": {"label": "WhatsApp-first ordering", "hi": "WhatsApp se order", "goals": "SIMPLE", "auds": {C, D, O},
                       "words": ["whatsapp", "watsapp", "whats app"], "screens": ["support"], "caps": ["share_sheet", "deep_links"],
                       "pitch": "every order / booking reaches the shop on WhatsApp in one tap, status on WhatsApp too"},
    "voice_hindi": {"label": "Speak in Hindi to search & order", "hi": "bolkar order", "goals": "ALL", "auds": {C, S, P, M},
                    "words": ["voice", "bolkar", "awaaz", "bol ke", "speak"], "screens": ["search"],
                    "caps": ["speech_to_text", "microphone", "translation"],
                    "pitch": "no reading or writing needed: search and order by voice"},
    "offline_first": {"label": "Works without internet", "hi": "bina internet", "goals": "ALL", "auds": {S, P, O, G, D},
                      "words": ["offline", "bina internet", "no internet", "network nahi", "gaon"], "screens": ["sync_status"],
                      "caps": ["offline_db", "background_sync"],
                      "pitch": "works even without network, everything syncs by itself when the net is back"},
    "upi_direct": {"label": "UPI pay straight to the shop", "hi": "seedha UPI", "goals": MONEY_SIMPLE, "auds": {C, D, M},
                   "words": ["upi", "gpay", "phonepe", "paytm", "online payment"], "screens": ["payment"], "caps": ["upi_intent"],
                   "pitch": "money goes straight to the shop's UPI ID, no middleman commission"},
    "loyalty_points": {"label": "Loyalty points & rewards", "hi": "points aur inaam", "goals": {"shop", "food_order", "booking",
                       "membership", "khata", "catalogue"}, "auds": {C, M, D}, "words": ["loyalty", "points", "reward", "inaam", "cashback"],
                       "screens": ["rewards", "offers"], "caps": ["push_fcm"],
                       "pitch": "points on every purchase, old customers keep coming back"},
    "daily_subscription": {"label": "Daily / weekly subscription", "hi": "roz ki subscription",
                           "goals": {"shop", "food_order", "membership", "service_request"}, "auds": {C, P, O},
                           "words": ["subscription", "roz", "daily", "har din", "monthly plan", "doodh", "tiffin", "newspaper"],
                           "screens": ["plans", "slot_picker"], "caps": ["local_reminders", "push_fcm"],
                           "pitch": "set daily / weekly delivery once, pause it on days off"},
    "group_buy": {"label": "Society / group buying", "hi": "society group order", "goals": {"shop", "food_order", "catalogue"},
                  "auds": {C, O}, "words": ["society", "group", "bulk", "apartment", "mohalla"], "screens": ["offers", "cart"],
                  "caps": ["share_sheet"], "pitch": "one order for the whole society, lower delivery cost and a group price"},
    "pickup_qr": {"label": "Order ahead, pick up with QR", "hi": "pehle order, QR se pickup",
                  "goals": {"shop", "food_order", "catalogue", "events"}, "auds": {C, S},
                  "words": ["pickup", "takeaway", "parcel", "counter", "qr"], "screens": ["pass", "order_track"], "caps": ["barcode"],
                  "pitch": "no standing in line: order ahead, show the QR and collect"},
    "live_tracking": {"label": "Live order / visit tracking", "hi": "live tracking", "goals": {"shop", "food_order",
                      "service_request", "booking"}, "auds": {C, P, O}, "words": ["tracking", "track", "kahan tak", "live location"],
                      "screens": ["order_track", "route_nav"], "caps": ["maps", "push_fcm", "location_foreground"],
                      "pitch": "the customer sees how far the order / technician has reached, no repeated calls"},
    "phone_consult": {"label": "Book a phone / video consult", "hi": "phone par salah", "goals": {"booking", "service_request",
                      "learning"}, "auds": {C, O}, "words": ["consult", "salah", "tele", "online consultation", "video call"],
                      "screens": ["slot_picker", "booking_confirm"], "caps": ["call_dialer", "calendar"],
                      "pitch": "pick a time from home, call / video link at the agreed time"},
    "queue_token": {"label": "Live queue token", "hi": "line ka token", "goals": {"booking", "service_request", "events"},
                    "auds": {C, S, O}, "words": ["token", "queue", "line", "waiting", "number aane par"],
                    "screens": ["pass", "checkin"], "caps": ["push_fcm"],
                    "pitch": "take a token from home, alert 10 minutes before your number"},
    "home_visit": {"label": "At-home service", "hi": "ghar par seva", "goals": {"booking", "service_request"}, "auds": {C, P, S},
                   "words": ["ghar par", "home visit", "doorstep", "home service", "ghar aakar"], "screens": ["slot_picker", "request_service"],
                   "caps": ["location_foreground", "maps"], "pitch": "service at home: address, time and job in one form"},
    "ar_try": {"label": "See it in your room (AR / 3D)", "hi": "ghar mein dekh kar", "goals": {"shop", "catalogue"}, "auds": {C, D},
               "words": ["ar", "3d", "try", "room mein", "virtual"], "screens": ["product_detail", "gallery"], "caps": ["ar", "three_d"],
               "pitch": "see the product in your room / on yourself in 3D before buying"},
    "catalogue_share": {"label": "Share products with price", "hi": "catalogue share", "goals": {"shop", "catalogue", "khata"},
                        "auds": {O, S, D}, "words": ["share", "catalogue bhejo", "photo bhejo", "price list"],
                        "screens": ["catalogue", "gallery"], "caps": ["share_sheet", "photo_picker"],
                        "pitch": "every product with photo + price to WhatsApp / status in one tap"},
    "barcode_billing": {"label": "Scan & bill counter", "hi": "barcode billing", "goals": {"shop", "khata", "pos_retail",
                        "inventory", "warehouse_wms", "restaurant_ops", "distribution"}, "auds": {O, S},
                        "words": ["barcode", "scan", "billing", "bill", "counter"], "screens": ["pos_billing", "scanner_code", "invoice_view"],
                        "caps": ["barcode", "bluetooth_printer", "printing"],
                        "pitch": "scan, make the bill, print the slip on a Bluetooth printer"},
    "udhaar_reminders": {"label": "Udhaar with gentle reminders", "hi": "udhaar yaad dilana", "goals": {"khata", "shop", "collections",
                         "distribution", "dairy_collection"}, "auds": {O, C, D, S}, "words": ["udhaar", "udhar", "credit", "baaki", "reminder"],
                         "screens": ["khata", "notifications"], "caps": ["push_fcm", "share_sheet"],
                         "pitch": "who owes how much, and gentle reminders by themselves"},
    "referral": {"label": "Refer & earn", "hi": "dost ko bulao", "goals": "SIMPLE", "auds": {C, M, D},
                 "words": ["refer", "referral", "dost", "invite"], "screens": ["rewards"], "caps": ["share_sheet", "deep_links"],
                 "pitch": "a customer invites a friend, both get a reward: free marketing"},
    "photo_reviews": {"label": "Photo reviews from customers", "hi": "photo review", "goals": {"shop", "food_order", "booking",
                      "catalogue", "service_request", "events"}, "auds": {C}, "words": ["review", "rating", "feedback photo"],
                      "screens": ["gallery"], "caps": ["photo_picker", "in_app_review"],
                      "pitch": "photo reviews from real customers: new customers trust you"},
    "urgent_sos": {"label": "Urgent / emergency request", "hi": "turant madad", "goals": {"service_request", "booking"},
                   "auds": {C, P, O}, "words": ["urgent", "emergency", "turant", "jaldi", "sos", "24x7"],
                   "screens": ["request_service", "job_status"], "caps": ["call_dialer", "location_foreground", "push_fcm"],
                   "pitch": "one button: instant request with location, to the nearest partner"},
    "many_languages": {"label": "Every Indian language", "hi": "har bhasha", "goals": "ALL", "auds": {C, S, P, M, D},
                       "words": ["bhasha", "language", "marathi", "tamil", "telugu", "bengali", "gujarati", "kannada"],
                       "screens": ["profile"], "caps": ["translation"],
                       "pitch": "every user in their own language: Hindi, Marathi, Tamil, Bangla, Gujarati..."},
    "parent_view": {"label": "Parents see progress", "hi": "parents ko report", "goals": {"learning", "community", "events",
                    "school_erp", "coaching_admin"}, "auds": {M, S, O}, "words": ["parent", "abhibhavak", "progress", "report card"],
                    "screens": ["progress", "class_attendance", "fees"], "caps": ["push_fcm"],
                    "pitch": "daily attendance, marks and fees for parents in one place"},
    "live_classes": {"label": "Class schedule with join links", "hi": "online class", "goals": {"learning", "membership",
                     "coaching_admin"}, "auds": {M, C, S}, "words": ["online class", "live class", "batch", "zoom", "meet"],
                     "screens": ["timetable", "lesson"], "caps": ["calendar", "local_reminders"],
                     "pitch": "batch timetable, alert before class and join link"},
    "practice_quiz": {"label": "Daily practice & tests", "hi": "roz ka test", "goals": {"learning"}, "auds": {M, C},
                      "words": ["quiz", "test", "mock", "practice", "exam"], "screens": ["quiz", "progress"], "caps": ["offline_db"],
                      "pitch": "short daily tests, weak topics repeat by themselves"},
    "certificates": {"label": "Certificates on the phone", "hi": "certificate", "goals": {"learning", "events", "community"},
                     "auds": {M, C}, "words": ["certificate", "praman patra", "completion"], "screens": ["pass", "progress"],
                     "caps": ["share_sheet"], "pitch": "certificate on the phone the moment the course / event ends, share it"},
    "qr_checkin": {"label": "QR check-in / attendance", "hi": "QR haazri", "goals": {"membership", "learning", "events",
                   "community", "hrms", "school_erp", "coaching_admin", "gym_admin", "events_ops", "security_guard"},
                   "auds": {M, C, S, O}, "words": ["attendance", "haazri", "check in", "checkin", "entry"],
                   "screens": ["checkin", "member_card"], "caps": ["barcode"], "pitch": "QR scan at the door: attendance by itself"},
    "donations": {"label": "Donations with receipts", "hi": "daan / chanda", "goals": {"community", "events"}, "auds": {C, M, O},
                  "words": ["donation", "daan", "chanda", "contribute"], "screens": ["donate"], "caps": ["upi_intent", "share_sheet"],
                  "pitch": "donate by UPI, instant receipt, everyone sees where it was spent"},
    "volunteer_roster": {"label": "Volunteer roster", "hi": "sevak duty", "goals": {"community", "events", "ngo_field", "events_ops"},
                         "auds": {M, S, O}, "words": ["volunteer", "sevak", "duty", "roster"], "screens": ["task_list", "calendar_team"],
                         "caps": ["push_fcm"], "pitch": "who does which service when, with reminders"},
    "festival_offers": {"label": "Festival offers & greetings", "hi": "tyohar offer", "goals": {"shop", "food_order", "catalogue",
                        "booking", "khata"}, "auds": {C, O}, "words": ["festival", "tyohar", "diwali", "sale", "offer"],
                        "screens": ["offers"], "caps": ["push_fcm"],
                        "pitch": "offers and greetings by themselves on every festival, customers remember you"},
    "wholesale_tiers": {"label": "Wholesale price slabs & MOQ", "hi": "thok daam", "goals": {"shop", "catalogue", "khata",
                        "distribution"}, "auds": {D, O, S}, "words": ["wholesale", "thok", "moq", "slab", "bulk price"],
                        "screens": ["quote_builder", "purchase_order"], "caps": ["share_sheet"],
                        "pitch": "price slabs that drop with quantity, minimum order by itself"},
    "gst_bills": {"label": "GST bill on every sale", "hi": "GST bill", "goals": {"shop", "khata", "service_request", "catalogue",
                  "pos_retail", "distribution", "accounts_erp", "field_sales"}, "auds": {O, S, D},
                  "words": ["gst", "invoice", "bill", "tax invoice"], "screens": ["invoice", "invoice_view"],
                  "caps": ["printing", "share_sheet"], "pitch": "GST bill PDF for every sale, send it on WhatsApp"},
    "photo_proof": {"label": "Photo + GPS proof of work", "hi": "kaam ka saboot", "goals": "COMPLEX|service_request", "auds": {S, P, G},
                    "words": ["proof", "saboot", "photo proof", "geo tag", "gps"], "screens": ["photo_proof"],
                    "caps": ["camera", "location_foreground"], "pitch": "photo + location of every job, no more disputes"},
    "e_signature": {"label": "Sign on the phone", "hi": "phone par sign", "goals": "COMPLEX|service_request", "auds": {S, P, C},
                    "words": ["signature", "sign", "hastakshar", "pod"], "screens": ["signature_pad"], "caps": ["signature"],
                    "pitch": "the customer signs on the phone: job / delivery confirmed"},
    "route_plan": {"label": "Best route for the day", "hi": "aaj ka route", "goals": {"shop", "food_order", "field_sales",
                   "distribution", "delivery_driver", "collections", "field_service", "field_force", "logistics_tms", "fleet",
                   "dairy_collection", "isp_ops"}, "auds": {P, S, G}, "words": ["route", "rasta", "beat", "visit plan"],
                   "screens": ["route_plan", "route_nav"], "caps": ["maps", "location_foreground"],
                   "pitch": "all the day's stops in one short route, saving fuel and time"},
    "doc_scan": {"label": "Scan papers into the app", "hi": "kaagaz scan", "goals": "COMPLEX|service_request", "auds": {S, P, O, C},
                 "words": ["scan", "document", "kaagaz", "papers", "upload"], "screens": ["doc_scan", "upload_queue"],
                 "caps": ["doc_scanner", "camera"], "pitch": "not a photo of the paper, a clean PDF scan straight into the record"},
    "device_alerts": {"label": "Machine / sensor alerts", "hi": "machine alert", "goals": {"iot_monitor", "facility_mgmt",
                      "asset_utility", "agri_fpo", "dairy_collection", "isp_ops", "telecom_tower", "manufacturing_erp"},
                      "auds": {S, O, G}, "words": ["sensor", "iot", "machine", "alarm", "temperature", "device"],
                      "screens": ["device_list", "device_detail", "alert_center"], "caps": ["push_fcm", "bluetooth"],
                      "pitch": "if a machine / sensor shows something wrong, an instant alert to the right person"},
    "targets": {"label": "Targets & leaderboard", "hi": "target meter", "goals": "ALL", "auds": {O, G, S},
                "words": ["target", "lakshya", "leaderboard", "incentive", "performance"], "screens": ["target_meter", "dashboard_kpi"],
                "caps": ["widgets"], "pitch": "today's target, how much is done, who is ahead: team energy"},
    "approvals": {"label": "Approvals on the phone", "hi": "phone par manzoori", "goals": "COMPLEX", "auds": {G, O},
                  "words": ["approval", "manzoori", "sanction", "approve"], "screens": ["approval_inbox", "approval_detail", "workflow_chain"],
                  "caps": ["push_fcm", "biometrics"], "pitch": "expense / leave / discount approval in one tap, with fingerprint"},
    "shift_roster": {"label": "Shifts & attendance", "hi": "shift aur haazri", "goals": "COMPLEX", "auds": {S, G, O},
                     "words": ["shift", "roster", "duty", "attendance"], "screens": ["shift_roster", "attendance_punch", "leave_apply"],
                     "caps": ["geofence", "location_foreground"], "pitch": "who is on which shift, attendance by location, leave from the app"},
    "team_chat": {"label": "Team chat & notices", "hi": "team chat", "goals": "COMPLEX", "auds": {S, G},
                  "words": ["chat", "message", "notice", "group"], "screens": ["chat_list", "chat_thread", "announcement"],
                  "caps": ["push_fcm"], "pitch": "work talk in the work app, separate from personal WhatsApp"},
    "geofence": {"label": "Auto check-in by location", "hi": "location se haazri", "goals": {"hrms", "field_force",
                 "field_sales", "security_guard", "construction_pm", "facility_mgmt", "field_service"}, "auds": {S, G},
                 "words": ["geofence", "location attendance", "site par"], "screens": ["geofence", "attendance_punch"],
                 "caps": ["geofence", "location_foreground"], "pitch": "attendance on reaching the site, no fake location"},
    "nfc_tags": {"label": "NFC tag patrol / asset tap", "hi": "NFC tag", "goals": {"security_guard", "asset_utility",
                 "facility_mgmt", "inventory", "warehouse_wms", "audit_inspection"}, "auds": {S, G},
                 "words": ["nfc", "tag", "patrol", "checkpoint"], "screens": ["nfc_read", "checklist"], "caps": ["nfc"],
                 "pitch": "tap the tag at every checkpoint / machine: a firm record of rounds and checks"},
    "kanban": {"label": "Kanban board for work", "hi": "kaam ka board", "goals": {"project_mgmt", "construction_pm", "crm",
               "helpdesk", "field_service", "manufacturing_erp", "intranet", "real_estate_crm"}, "auds": {S, G, O},
               "words": ["kanban", "board", "stage", "pipeline"], "screens": ["kanban", "task_detail"], "caps": ["push_fcm"],
               "pitch": "every task is a card: which stage, with whom, due when"},
    "help_center": {"label": "Self-help answers", "hi": "khud jawab", "goals": "ALL", "auds": {C, S, M, D},
                    "words": ["faq", "help", "sawal", "support", "madad"], "screens": ["knowledge_base", "support"], "caps": [],
                    "pitch": "answers to common questions in the app itself, fewer phone calls"},
    "home_widget": {"label": "Home-screen widget", "hi": "widget", "goals": "ALL", "auds": {C, O, S, M, G},
                    "words": ["widget", "home screen"], "screens": ["home"], "caps": ["widgets"],
                    "pitch": "next booking / today's sales right on the phone's home screen"},
    "voice_notes": {"label": "Voice notes instead of typing", "hi": "voice note", "goals": "COMPLEX|service_request",
                    "auds": {S, P, G}, "words": ["voice note", "bolkar report", "audio"], "screens": ["voice_note"],
                    "caps": ["voice_notes", "microphone"], "pitch": "report from the field by voice instead of typing"},
    "bt_printer": {"label": "Bluetooth receipt printer", "hi": "parchi printer", "goals": {"shop", "khata", "food_order",
                   "pos_retail", "collections", "dairy_collection", "restaurant_ops", "distribution"}, "auds": {O, S, P},
                   "words": ["printer", "parchi", "receipt", "thermal"], "screens": ["invoice_view"], "caps": ["bluetooth_printer", "printing"],
                   "pitch": "instant receipt from a small Bluetooth printer"},
    "portfolio": {"label": "Portfolio gallery", "hi": "kaam ki gallery", "goals": {"catalogue", "booking", "events",
                  "service_request"}, "auds": {C, D}, "words": ["portfolio", "gallery", "photos", "kaam dikhana"],
                  "screens": ["gallery"], "caps": ["photo_picker"], "pitch": "photos of past work: customers book after seeing them"},
    "polls": {"label": "Polls & feedback", "hi": "rai", "goals": {"community", "membership", "events", "learning", "intranet",
              "society_mgmt", "school_erp"}, "auds": {M, C, S}, "words": ["poll", "survey", "rai", "vote", "feedback"],
              "screens": ["poll_survey"], "caps": ["push_fcm"], "pitch": "everyone's opinion before a decision, in one tap"},
    "nearby_branches": {"label": "Nearest branch finder", "hi": "paas ki branch", "goals": {"shop", "booking", "service_request",
                        "catalogue", "food_order", "membership"}, "auds": {C}, "words": ["nearby", "paas", "branch", "store locator"],
                        "screens": ["nearby", "store_info"], "caps": ["maps", "location_foreground"],
                        "pitch": "nearest branch, opening hours and directions"},
    "lite_2g": {"label": "Lite app for slow phones / 2G", "hi": "halka app", "goals": "ALL", "auds": {C, S, P, M, D},
                "words": ["lite", "slow", "2g", "sasta phone", "kam data"], "screens": ["home"], "caps": ["offline_db"],
                "pitch": "fast even on old / cheap phones and little data"},
    "senior_friendly": {"label": "Big text, simple for elders", "hi": "buzurgon ke liye aasaan", "goals": "SIMPLE", "auds": {C, M},
                        "words": ["senior", "buzurg", "elderly", "bade akshar", "dadi", "nana"], "screens": ["support"],
                        "caps": ["speech_to_text", "accessibility"],
                        "pitch": "big text, few buttons, one-tap call: elders can use it on their own"},
    "stock_alerts": {"label": "Low-stock alerts & reorder", "hi": "stock khatam alert", "goals": {"shop", "khata", "inventory",
                     "pos_retail", "warehouse_wms", "distribution", "procurement", "restaurant_ops", "manufacturing_erp"},
                     "auds": {O, S, G}, "words": ["stock", "maal khatam", "reorder", "inventory"],
                     "screens": ["inventory_list", "stock_item", "purchase_order"], "caps": ["push_fcm", "barcode"],
                     "pitch": "alert before stock runs out and a draft order to the supplier"},
    "customer_portal": {"label": "Customer portal on the same app", "hi": "graahak ka hissa", "goals": "COMPLEX",
                        "auds": {O, G}, "words": ["customer portal", "client login", "graahak bhi dekhe"],
                        "screens": ["ticket_list", "invoice_view", "notifications"], "caps": ["push_fcm"],
                        "pitch": "customers see their own status / bill / ticket, fewer calls to staff"},
}

SCALE: dict[str, dict[str, Any]] = {
    "solo": {"label": "One shop / one place", "hi": "ek dukaan", "words": ["meri dukaan", "ek dukaan", "akela", "single"],
             "line": "one shop / one place", "screens": []},
    "multi_branch": {"label": "Many branches", "hi": "kai branch", "words": ["branch", "branches", "shakha", "outlets", "chain"],
                     "line": "many branches: pick a branch, separate accounts for each branch", "screens": ["store_info"]},
    "network": {"label": "Whole-city network / marketplace", "hi": "poore shahar ka network",
                "words": ["marketplace", "aggregator", "saare", "network", "platform", "shahar ke", "city ke", "franchise"],
                "line": "many businesses of the city in one app (marketplace / franchise)", "screens": ["search", "nearby"]},
}
MARKET: dict[str, dict[str, Any]] = {
    "town": {"label": "Town / village, Hindi-first", "hi": "chhota shahar", "words": ["gaon", "village", "town", "kasba", "tier 3",
             "chhota shahar", "rural"], "line": "small town / village: Hindi first, UPI + cash, low data", "lang": "hindi"},
    "metro": {"label": "Big city, Hinglish", "hi": "bada shahar", "words": ["metro", "mumbai", "delhi", "bangalore", "pune",
              "hyderabad", "chennai", "kolkata", "bada shahar", "city"], "line": "big city: Hinglish, fast delivery, card / UPI",
              "lang": "hinglish"},
    "bharat": {"label": "All-India, every language", "hi": "poora Bharat", "words": ["india", "bharat", "all india", "desh bhar",
               "pan india"], "line": "all of India: every language, every state's rules", "lang": "multi"},
    "global": {"label": "NRI / export buyers", "hi": "videsh / NRI", "words": ["nri", "export", "videsh", "abroad", "usa",
               "uk", "dubai", "international", "global"], "line": "customers abroad / NRIs: English, prices in rupees + dollars",
               "lang": "english"},
}
GLOBAL_GOALS = {"shop", "catalogue", "booking", "learning", "events", "community", "membership"}

EARN: dict[str, dict[str, Any]] = {
    "direct_sales": {"label": "Sells its own goods / services", "hi": "apni bikri", "line": "earning: your own sales grow, no commission"},
    "subscription": {"label": "Monthly subscription / plan", "hi": "mahine ka plan", "line": "earning: steady income every month (plan)"},
    "membership_fee": {"label": "Membership fee", "hi": "sadasyata shulk", "line": "earning: membership fee + renewal reminders"},
    "commission": {"label": "Commission from vendors", "hi": "commission", "line": "earning: a small commission from the business on every order"},
    "saves_cost": {"label": "Saves staff time & leakage", "hi": "kharcha bachao", "line": "benefit: saves staff time and theft / mistakes"},
    "saas": {"label": "Sell it to others in the same trade", "hi": "doosron ko becho", "line": "earning: rent this same app by the month to other businesses like yours"},
}

TIER: dict[str, dict[str, Any]] = {
    # customer-facing apps: how it is positioned
    "budget": {"label": "Budget / value for money", "hi": "sasta-tikau", "words": ["sasta", "budget", "cheap", "kam daam", "affordable"],
               "line": "value for money: COD / UPI, small packs, offers up front", "who": "public", "styles": ["bold_blocks", "desi_festive", "playful_pop"]},
    "mid": {"label": "Everyday mid range", "hi": "aam", "words": ["normal", "regular", "everyday", "middle class"],
            "line": "everyday customers: clean, trustworthy, quick", "who": "public", "styles": ["clean_commerce", "soft_pastel", "fresh_organic"]},
    "premium": {"label": "Premium / luxury", "hi": "premium", "words": ["premium", "luxury", "high end", "branded", "shaahi", "royal"],
                "line": "premium: large photos, little clutter, personal service", "who": "public",
                "styles": ["luxury_noir", "editorial_image", "aurora_glass"]},
    # internal apps: how big the team is (decides org levels / roles)
    "small_team": {"label": "Small team (up to 10)", "hi": "chhoti team", "words": ["chhoti team", "2 log", "5 log", "small team"],
                   "line": "small team (up to 10): few roles, everything in one place", "who": "team", "levels": 2},
    "mid_team": {"label": "Growing team (10-100)", "hi": "badhti team", "words": ["20 log", "50 log", "team leader", "supervisor"],
                 "line": "growing team (10-100): team leader, branch, approvals", "who": "team", "levels": 3},
    "big_team": {"label": "Large organisation (100+)", "hi": "badi sanstha", "words": ["100 log", "500", "company", "sanstha", "zones",
                 "region", "head office"], "line": "large organisation (100+): zone > region > branch, full approval chain",
                 "who": "team", "levels": 5},
}
PUBLIC_AUD = {"customer", "member", "dealer"}

KEYS = ("field", "goal", "aud", "twist", "scale", "market", "tier", "earn")
SEP = "."


# ---------------------------------------------------------------- fit rules
def _goal_ok(spec: Any, goal: str) -> bool:
    if spec == "ALL":
        return True
    if spec == "SIMPLE":
        return goal in T.SIMPLE_GOALS
    if spec == "COMPLEX":
        return goal in T.COMPLEX_GOALS
    if isinstance(spec, str) and spec.startswith("COMPLEX|"):
        return goal in T.COMPLEX_GOALS or goal in spec.split("|")[1:]
    return goal in spec


@lru_cache(maxsize=1)
def _field_goals() -> dict[str, list[str]]:
    """Every business type -> the goals that fit it (its own default first)."""
    F = SL.fields()
    out: dict[str, list[str]] = {}
    for fid, f in F.items():
        own = L.default_goal(fid)
        gs = [own] if own in T.SIMPLE_GOALS else []
        gs += [g for g in T.SIMPLE_GOALS if g not in gs and f["industry"] in SIMPLE_FIT.get(g, ())]
        out[fid] = gs
    for g in T.COMPLEX_GOALS:
        for fid in L.pro_fields(g):
            if g not in out.setdefault(fid, []):
                out[fid].append(g)
    return out


@lru_cache(maxsize=None)
def audiences(goal: str) -> tuple[str, ...]:
    cx = goal in T.COMPLEX_GOALS
    out = []
    for a, spec in AUD.items():
        if cx and a == "customer":
            continue
        if _goal_ok(spec["goals"], goal):
            out.append(a)
    if cx:
        out = ["staff"] + [a for a in out if a != "staff"]
    return tuple(out)


@lru_cache(maxsize=None)
def twists(goal: str, aud: str) -> tuple[str, ...]:
    return tuple(t for t, x in TWISTS.items() if _goal_ok(x["goals"], goal) and aud in x["auds"])


@lru_cache(maxsize=None)
def markets(goal: str, aud: str) -> tuple[str, ...]:
    if aud in ("customer", "member", "dealer") and goal in GLOBAL_GOALS:
        return ("town", "metro", "bharat", "global")
    return ("town", "metro", "bharat")


@lru_cache(maxsize=None)
def tiers(aud: str) -> tuple[str, ...]:
    who = "public" if aud in PUBLIC_AUD else "team"
    return tuple(k for k, v in TIER.items() if v["who"] == who)


@lru_cache(maxsize=None)
def earns(goal: str, aud: str, scale: str) -> tuple[str, ...]:
    if aud in ("owner", "staff", "manager", "partner"):
        return ("saves_cost", "saas")
    if scale == "network":
        out = ["commission", "subscription"]
    elif goal in ("membership", "community", "learning"):
        out = ["membership_fee", "subscription", "direct_sales"]
    elif goal in ("khata", "catalogue"):
        out = ["direct_sales", "saves_cost"]
    else:
        out = ["direct_sales", "subscription"]
    return tuple(out)


@lru_cache(maxsize=None)
def _count_goal(goal: str) -> int:
    n = 0
    for a in audiences(goal):
        k = len(twists(goal, a)) * len(markets(goal, a)) * len(tiers(a))
        n += k * sum(len(earns(goal, a, sc)) for sc in SCALE)
    return n


@lru_cache(maxsize=1)
def _field_counts() -> list[tuple[str, int]]:
    fg = _field_goals()
    return [(fid, sum(_count_goal(g) for g in fg[fid])) for fid in sorted(fg)]


def total() -> int:
    """The exact number of ideas (every combination that makes sense), not an estimate."""
    return sum(n for _, n in _field_counts())


def counts() -> dict[str, int]:
    fg = _field_goals()
    return {"ideas": total(), "fields": len(fg), "field_goal_pairs": sum(len(v) for v in fg.values()),
            "audiences": len(AUD), "twists": len(TWISTS), "scales": len(SCALE), "markets": len(MARKET), "tiers": len(TIER),
            "earn_models": len(EARN),
            "with_styles": total() * len(T.STYLES)}


# ---------------------------------------------------------------- one idea from its id / its number
def valid(parts: dict[str, str]) -> str:
    """'' when the combination makes sense, else why not."""
    fid, g, a, tw, sc, mk, ti, er = (parts.get(k, "") for k in KEYS)
    fg = _field_goals()
    if fid not in fg:
        return "business type not found"
    if g not in fg[fid]:
        return f"{T.GOALS.get(g, {}).get('label', g)} does not fit this business"
    if a not in audiences(g):
        return "this user does not fit this app"
    if tw not in twists(g, a):
        return "this feature does not fit this app / user"
    if sc not in SCALE:
        return "invalid scale"
    if mk not in markets(g, a):
        return "invalid market"
    if ti not in tiers(a):
        return "invalid tier"
    if er not in earns(g, a, sc):
        return "this way of earning does not fit this idea"
    return ""


def parse(idea_id: str) -> dict[str, str]:
    bits = (idea_id or "").strip().split(SEP)
    if len(bits) != len(KEYS):
        raise KeyError(idea_id)
    parts = dict(zip(KEYS, bits))
    if valid(parts):
        raise KeyError(idea_id)
    return parts


def make_id(parts: dict[str, str]) -> str:
    return SEP.join(parts[k] for k in KEYS)


def _within_goal(field: str, goal: str, n: int) -> dict[str, str]:
    for a in audiences(goal):
        for sc in SCALE:
            for mk in markets(goal, a):
                for ti in tiers(a):
                    es = earns(goal, a, sc)
                    tws = twists(goal, a)
                    block = len(tws) * len(es)
                    if n < block:
                        return {"field": field, "goal": goal, "aud": a, "twist": tws[n // len(es)], "scale": sc, "market": mk,
                                "tier": ti, "earn": es[n % len(es)]}
                    n -= block
    raise IndexError(n)


def nth(n: int) -> dict[str, str]:
    """Idea number n (0 .. total-1): the whole list can be walked page by page."""
    if n < 0:
        raise IndexError(n)
    fg = _field_goals()
    for fid, cnt in _field_counts():
        if n < cnt:
            for g in fg[fid]:
                c = _count_goal(g)
                if n < c:
                    return _within_goal(fid, g, n)
                n -= c
        n -= cnt
    raise IndexError(n)


def _screens_for(parts: dict[str, str]) -> list[str]:
    g, a, tw, sc = parts["goal"], parts["aud"], parts["twist"], parts["scale"]
    out: list[str] = []
    for s in (AUD[a].get("screens") or []) + TWISTS[tw]["screens"] + SCALE[sc]["screens"]:
        if s in T.SCREENS and s not in out:
            out.append(s)
    if a == "partner" and g == "service_request":
        out = [s for s in out if s not in ("delivery_run", "proof_of_delivery")]
    if a == "partner" and g in ("shop", "food_order", "catalogue", "khata"):
        out = [s for s in out if s not in ("job_card", "photo_proof")] if tw != "photo_proof" else out
    return out


def _tabs_for(parts: dict[str, str], screens: list[str]) -> list[str]:
    g, a = parts["goal"], parts["aud"]
    base = list(T.GOALS[g]["tabs"])
    want = AUD[a].get("tabs")
    if not want or (a == "staff" and g in T.COMPLEX_GOALS):
        return base
    if a == "partner" and g == "service_request":
        want = ["job_card", "route_nav", "payment_collect", "profile"]
    tabs = [t for t in want if t in screens or t in T.GOALS[g]["screens"]]
    return tabs[:5] if len(tabs) >= 3 else base


def _name(f: dict[str, Any], parts: dict[str, str]) -> str:
    g, a, tw = T.GOALS[parts["goal"]], AUD[parts["aud"]], TWISTS[parts["twist"]]
    who = "" if parts["aud"] in ("customer", "staff") and not (parts["aud"] == "customer" and parts["goal"] in T.COMPLEX_GOALS) \
        else f" ({a['label']})"
    sc = {"multi_branch": " · branches", "network": " · city network"}.get(parts["scale"], "")
    return f"{f['en']} {g['label']}{who} · {tw['label']}{sc}"


def idea(parts_or_id: Any) -> dict[str, Any]:
    parts = parse(parts_or_id) if isinstance(parts_or_id, str) else dict(parts_or_id)
    if valid(parts):
        raise KeyError(make_id(parts))
    f = SL.fields()[parts["field"]]
    g, a, tw = T.GOALS[parts["goal"]], AUD[parts["aud"]], TWISTS[parts["twist"]]
    sc, mk, er = SCALE[parts["scale"]], MARKET[parts["market"]], EARN[parts["earn"]]
    ti = TIER[parts["tier"]]
    screens = _screens_for(parts)
    all_screens = list(dict.fromkeys(list(g["screens"]) + screens))
    pitch = (f"{g['label']} app for {f['en']}, {a['line']}: {tw['pitch']}. "
             f"{sc['line'].capitalize()}. {mk['line'].capitalize()}. {ti['line'].capitalize()}. {er['line'].capitalize()}.")
    qs = []
    if parts["twist"] in ("upi_direct", "donations") or (g.get("money") and parts["aud"] in ("customer", "dealer", "member")):
        qs.append("Which UPI ID will the money come to? (only the UPI ID, never the PIN)")
    if parts["scale"] == "multi_branch":
        qs.append("How many branches are there, and what are their names / cities?")
    if parts["scale"] == "network":
        qs.append("How many businesses / shops will join at the start, and what is the commission?")
    if parts["twist"] == "daily_subscription":
        qs.append("What is in the subscription (milk / tiffin / ...) and at what time is delivery?")
    if parts["market"] == "global":
        qs.append("Which countries do you ship to, and are prices in rupees or dollars?")
    return {"id": make_id(parts), **parts, "name": _name(f, parts), "pitch": pitch,
            "field_label": f["en"], "field_hi": f["hi"], "industry": f["industry"],
            "goal_label": g["label"], "complex": bool(g.get("complex")),
            "aud_label": a["label"], "twist_label": tw["label"], "twist_hi": tw["hi"], "scale_label": sc["label"],
            "market_label": mk["label"], "tier_label": ti["label"], "earn_label": er["label"],
            "styles": [x for x in ti.get("styles", []) if x in T.STYLES], "levels": ti.get("levels"),
            "special": tw["pitch"], "screens_added": screens, "tabs": _tabs_for(parts, all_screens), "caps": list(tw["caps"]),
            "language": mk["lang"], "questions": qs[:3],
            "line": (f"IDEA: {f['en']} - {g['label']} for {a['label'].lower()}; the special thing: {tw['label']} "
                     f"({tw['pitch']}); scale: {sc['label']}; market: {mk['label']}; positioning / team: {ti['label']}; money: "
                     f"{er['label']}. Make every screen "
                     f"serve THIS idea first.")}


# ---------------------------------------------------------------- from her words: the precise idea + 2 near ones
def _hits(words: dict[str, dict[str, Any]], text: str) -> list[str]:
    t = " " + re.sub(r"[^\w\s]", " ", (text or "").lower()) + " "
    t = re.sub(r"\s+", " ", t)
    scored = []
    for k, x in words.items():
        s = sum(len(w.split()) for w in x.get("words", []) if f" {w.lower()} " in t or f" {w.lower()}s " in t)
        if s:
            scored.append((s, k))
    return [k for _, k in sorted(scored, key=lambda z: -z[0])]


def _seed(*bits: str) -> int:
    return int(hashlib.sha1("|".join(bits).encode()).hexdigest()[:8], 16)


def _rank_twists(field: str, goal: str, aud: str, said: list[str]) -> list[str]:
    tws = list(twists(goal, aud))
    learned = L._stats(field).get("twist", {})
    first = [t for t in said if t in tws]
    rest = sorted((t for t in tws if t not in first), key=lambda t: (-learned.get(t, 0), _seed(field, goal, aud, t)))
    return first + rest


def understand(text: str, field: str = "", goal: str = "") -> dict[str, Any]:
    """Her few words -> {idea (the best fit), alternatives (2 more ideas that differ in what is special), said, ask, count}."""
    u = L.understand(text) if (text or "").strip() else {}
    fid = field if field in _field_goals() else (u.get("field") or "")
    if u.get("product") and field not in _field_goals():     # v0.138 a product app (music, OTT ...): no shop ideas
        return {"idea": None, "alternatives": [], "ask": "", "count": 0, "product": u["product"],
                "say": f"This is a {u.get('field_label')}: its plan is made directly with app_banao."}
    if not fid or fid not in _field_goals():
        return {"idea": None, "alternatives": [], "ask": u.get("ask") or "What work / shop is the app for?", "count": 0}
    fg = _field_goals()[fid]
    g = goal if goal in fg else (u.get("goal") if u.get("goal") in fg else fg[0])
    said_aud = [a for a in _hits(AUD, text) if a in audiences(g)]
    a = said_aud[0] if said_aud else ("customer" if "customer" in audiences(g) else audiences(g)[0])
    said_tw = _hits(TWISTS, text)
    sc = (_hits(SCALE, text) or ["solo"])[0]
    mks = markets(g, a)
    mk = next((m for m in _hits(MARKET, text) if m in mks), "town")
    es = earns(g, a, sc)
    tis = tiers(a)
    ti = next((x for x in _hits(TIER, text) if x in tis), tis[1] if len(tis) > 1 else tis[0])
    ranked = _rank_twists(fid, g, a, said_tw)
    out = []
    for tw in ranked[:3]:
        out.append(idea({"field": fid, "goal": g, "aud": a, "twist": tw, "scale": sc, "market": mk, "tier": ti, "earn": es[0]}))
    n_field = sum(_count_goal(x) for x in fg)
    return {"idea": out[0] if out else None, "alternatives": out[1:], "said": {"aud": said_aud[:1], "twists": said_tw[:3],
            "scale": sc, "market": mk, "tier": ti}, "ask": u.get("ask", ""), "count": n_field, "field": fid, "goal": g,
            "field_label": SL.fields()[fid]["en"], "goals": fg}


def browse(q: str = "", field: str = "", goal: str = "", aud: str = "", offset: int = 0, limit: int = 30) -> dict[str, Any]:
    """Walk the list: everything (q empty), one business type, or her words; filters by goal / user."""
    limit = max(1, min(int(limit or 30), 100))
    offset = max(0, int(offset or 0))
    if not q and not field:
        tot = total()
        items = []
        for i in range(offset, min(offset + limit, tot)):
            items.append(idea(nth(i)))
        return {"total": tot, "offset": offset, "items": items, "counts": counts()}
    fid = field if field in _field_goals() else ""
    if not fid:
        u = understand(q)
        fid = u.get("field") or ""
        if not fid:
            return {"total": 0, "offset": offset, "items": [], "ask": u.get("ask")}
    goals = [g for g in _field_goals()[fid] if not goal or g == goal]
    said_tw = _hits(TWISTS, q) if q else []

    def walk():
        for g in goals:
            for a in audiences(g):
                if aud and a != aud:
                    continue
                for tw in _rank_twists(fid, g, a, said_tw):
                    for sc in SCALE:
                        for mk in markets(g, a):
                            for ti in tiers(a):
                                for er in earns(g, a, sc):
                                    yield {"field": fid, "goal": g, "aud": a, "twist": tw, "scale": sc, "market": mk, "tier": ti,
                                           "earn": er}
    tot = sum(len(twists(g, a)) * len(markets(g, a)) * len(tiers(a)) * sum(len(earns(g, a, s)) for s in SCALE)
              for g in goals for a in audiences(g) if not aud or a == aud)
    items = []
    for i, p in enumerate(walk()):
        if i < offset:
            continue
        if len(items) >= limit:
            break
        items.append(idea(p))
    return {"total": tot, "offset": offset, "items": items, "field": fid, "field_label": SL.fields()[fid]["en"],
            "goals": [{"id": g, "label": T.GOALS[g]["label"]} for g in _field_goals()[fid]]}


def check() -> list[str]:
    """Every twist / audience screen and capability exists (used by tests)."""
    from . import capabilities as CP
    bad = []
    caps = set(CP.CAPS) if hasattr(CP, "CAPS") else set()
    for k, x in list(TWISTS.items()) + list(AUD.items()) + list(SCALE.items()):
        for s in x.get("screens") or []:
            if s not in T.SCREENS:
                bad.append(f"{k}: screen {s}")
        for c in x.get("caps") or []:
            if caps and c not in caps:
                bad.append(f"{k}: cap {c}")
        g = x.get("goals")
        if isinstance(g, set):
            for gg in g:
                if gg not in T.GOALS:
                    bad.append(f"{k}: goal {gg}")
    for g, inds in SIMPLE_FIT.items():
        for i in inds:
            from ..site import taxonomy as ST
            if i not in ST.INDUSTRIES:
                bad.append(f"fit {g}: industry {i}")
    return bad


def apply(br: dict[str, Any], it: dict[str, Any]) -> dict[str, Any]:
    """The idea changes the library brief: its extra screens (with a design each), the tabs for its user."""
    br = dict(br)
    screens = list(br["screens"])
    tail = [x for x in ("notifications", "profile", "support") if x in screens]
    body = [x for x in screens if x not in tail]
    for sc in it.get("screens_added") or []:
        if sc not in body and sc not in tail and sc in T.SCREENS:
            body.append(sc)
    br["screens"] = body + tail
    designs = dict(br["designs"])
    for sc in br["screens"]:
        if sc not in designs:
            designs[sc] = L._pick(br["id"] + sc, T.SCREENS[sc]["variants"])
    br["designs"] = designs
    tabs = [t for t in (it.get("tabs") or []) if t in br["screens"]]
    if len(tabs) >= 3:
        br["tabs"] = tabs
    return br

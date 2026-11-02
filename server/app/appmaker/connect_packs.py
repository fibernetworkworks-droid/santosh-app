"""v0.424 JODO: ready packs = declared actions written from each provider's OWN documentation (official APIs only).
A pack only DRAFTS actions + names the secrets it needs; every action still waits for her approval tap, and nothing
here has been answered by a live account yet (said on every pack). She fills the settings; secrets go in sealed.

Docs followed:
  Shiprocket   https://apidocs.shiprocket.in  (POST /v1/external/auth/login -> token; /orders/create/adhoc; /courier/assign/awb;
               GET /courier/track/awb/{awb})
  Delhivery    https://one.delhivery.com/developer-portal  (Authorization: Token <key>; POST /api/cmu/create.json form
               format=json & data=<json>; GET /api/v1/packages/json/?waybill=)
  MSG91        https://docs.msg91.com  (POST /api/v5/flow, header authkey, DLT template inside MSG91)
  Fast2SMS     https://docs.fast2sms.com  (POST /dev/bulkV2, header authorization, route dlt, sender_id, message = DLT id)
  WhatsApp     https://developers.facebook.com/docs/whatsapp/cloud-api  (POST /{phone-number-id}/messages, template)
  Brevo        https://developers.brevo.com  (POST /v3/smtp/email, header api-key)
  Resend       https://resend.com/docs/api-reference  (POST /emails, Bearer)
  Google       service account JWT -> https://oauth2.googleapis.com/token; Sheets values:append; Calendar events.insert
               (she shares the sheet / calendar with the service account's e-mail)
  Zoho Books   https://www.zoho.com/books/api/v3/  (self-client refresh token -> accounts.zoho.in; Zoho-oauthtoken)
  QuickBooks   https://developer.intuit.com  (refresh token grant, client id/secret as Basic; the refresh token ROTATES - kept)
  KYC          a LICENSED provider of her choice (PAN / GSTIN / bank account checks) - Aadhaar is refused by the engine."""
from __future__ import annotations

import re
from typing import Any

NOT_VERIFIED = "Provider ke docs se banaya; abhi kisi live account ne jawab nahi diya - pehle ek test entry par chala kar dekhiye."

PACKS: dict[str, dict[str, Any]] = {
    "shiprocket": {
        "label": "Shiprocket (courier)", "group": "Courier",
        "secrets": ["shiprocket_email", "shiprocket_password"],
        "settings": {"coll": "orders", "pickup_location": "Primary", "weight_kg": "0.5", "length_cm": "10", "breadth_cm": "10", "height_cm": "5"},
        "needs_fields": ["city", "pincode", "state", "awb", "tracking"],
        "note": "Shiprocket > Settings > API mein ek API user banaiye (alag email) - wahi email / password yahan.",
    },
    "delhivery": {
        "label": "Delhivery (courier)", "group": "Courier", "secrets": ["delhivery_token"],
        "settings": {"coll": "orders", "pickup_location": "", "weight_g": "500"},
        "needs_fields": ["city", "pincode", "state", "awb", "tracking"],
        "note": "Delhivery One > Settings > API token. pickup_location = aapke Delhivery warehouse ka naam (exact).",
    },
    "msg91": {
        "label": "MSG91 SMS (DLT template)", "group": "SMS", "secrets": ["msg91_authkey"],
        "settings": {"coll": "orders", "status": "Out for delivery", "template_id": ""},
        "note": "DLT par approve template MSG91 mein jodiye; template_id woh MSG91 wala id. var1 = naam, var2 = order number.",
    },
    "fast2sms": {
        "label": "Fast2SMS (DLT route)", "group": "SMS", "secrets": ["fast2sms_key"],
        "settings": {"coll": "orders", "status": "Out for delivery", "sender_id": "", "message_id": ""},
        "note": "DLT route: sender_id (6 akshar) + Fast2SMS par approve message id. Variables: naam | order.",
    },
    "whatsapp": {
        "label": "WhatsApp Business template", "group": "WhatsApp", "secrets": ["wa_token"],
        "settings": {"coll": "orders", "status": "Out for delivery", "phone_number_id": "", "template": "", "lang": "en"},
        "note": "Meta Business > WhatsApp > API: phone number ID + permanent token; template aapka APPROVED UTILITY template "
                "(body mein {{1}} = naam). Sirf official Cloud API.",
    },
    "brevo": {
        "label": "Brevo e-mail", "group": "Email", "secrets": ["brevo_key"],
        "settings": {"coll": "orders", "from_email": "", "from_name": "", "subject": "Your order is confirmed"},
        "needs_fields": ["email"],
        "note": "Brevo > SMTP & API > API key; from_email Brevo mein verified sender ho.",
    },
    "resend": {
        "label": "Resend e-mail", "group": "Email", "secrets": ["resend_key"],
        "settings": {"coll": "orders", "from_email": "", "subject": "Your order is confirmed"},
        "needs_fields": ["email"],
        "note": "Resend > API Keys; from_email aapke verified domain ka.",
    },
    "google_sheets": {
        "label": "Google Sheets (add a row)", "group": "Google", "secrets": ["google_sa"],
        "settings": {"coll": "orders", "sheet_id": "", "range": "Sheet1!A1"},
        "note": "Google Cloud > service account > JSON key (poora JSON secret mein). Sheet ko service account ke email se Share (Editor) kijiye.",
    },
    "google_calendar": {
        "label": "Google Calendar (add an event)", "group": "Google", "secrets": ["google_sa"],
        "settings": {"coll": "bookings", "calendar_id": "", "minutes": "60"},
        "needs_fields": ["date", "time"],
        "note": "Calendar ko service account ke email se share kijiye ('Make changes to events'); calendar_id calendar settings mein.",
    },
    "zoho_books": {
        "label": "Zoho Books (add customer)", "group": "Accounts", "secrets": ["client_id", "client_secret", "refresh_token"],
        "settings": {"coll": "orders", "organization_id": "", "dc": "in"},
        "note": "api-console.zoho.in > Self Client > scope ZohoBooks.contacts.CREATE se refresh token. organization_id Books settings mein.",
    },
    "quickbooks": {
        "label": "QuickBooks (sales receipt)", "group": "Accounts", "secrets": ["client_id", "client_secret", "refresh_token"],
        "settings": {"coll": "orders", "realm_id": "", "item_id": "1", "sandbox": "no"},
        "note": "developer.intuit.com app ki keys + OAuth playground se refresh token; QuickBooks har baar naya refresh token deta hai - Hoola use band rakhta hai.",
    },
    "tally": {
        "label": "Tally", "group": "Accounts", "secrets": [], "settings": {},
        "note": "Tally aapke PC par chalta hai, internet se nahi pahunchta. Mahine ka Tally XML export (App > Hisaab) use kijiye - Tally > Import.",
        "no_actions": True,
    },
    "kyc": {
        "label": "KYC (licensed provider, no Aadhaar)", "group": "KYC", "secrets": ["kyc_key"],
        "settings": {"coll": "", "url": "", "header": "x-api-key", "pan_field": "pan"},
        "needs_fields": ["pan", "kyc_status"],
        "note": "Apne licensed KYC provider (PAN / GST / bank account check) ka documented https URL. Aadhaar wala koi bhi connector Hoola nahi chalata.",
    },
}


def catalog() -> list[dict[str, Any]]:
    return [{"key": k, "label": p["label"], "group": p["group"], "secrets": p["secrets"], "settings": p["settings"],
             "needs_fields": p.get("needs_fields", []), "note": p["note"], "verified": False, "not_verified": NOT_VERIFIED,
             "no_actions": bool(p.get("no_actions"))} for k, p in PACKS.items()]


def _s(st: dict[str, Any], k: str) -> str:
    return str(st.get(k) or PACKS_DEFAULT.get(k) or "").strip()


PACKS_DEFAULT: dict[str, Any] = {}


def actions_for(pack: str, st: dict[str, Any]) -> list[dict[str, Any]]:
    """The actions a pack drafts from her settings (each still needs her approval)."""
    p = PACKS.get(pack)
    if p is None:
        raise ValueError("pack")
    s = {**p["settings"], **{k: v for k, v in (st or {}).items() if v not in (None, "")}}
    coll = str(s.get("coll") or "")
    g = lambda k: str(s.get(k) or "").strip()  # noqa: E731
    if pack == "shiprocket":
        auth = {"type": "login_token", "url": "https://apiv2.shiprocket.in/v1/external/auth/login",
                "body": {"email": "{{secret.shiprocket_email}}", "password": "{{secret.shiprocket_password}}"}, "token_path": "$.token", "ttl": 216000}
        return [
            {"key": "sr_create", "label": "Shiprocket: create shipment", "method": "POST", "coll": coll, "trigger": "manual", "staff": True,
             "url": "https://apiv2.shiprocket.in/v1/external/orders/create/adhoc", "auth": auth,
             "body": {"order_id": "{{row.id}}", "order_date": "{{today}}", "pickup_location": g("pickup_location"),
                      "billing_customer_name": "{{row.name}}", "billing_last_name": "", "billing_address": "{{row.address}}",
                      "billing_city": "{{row.city}}", "billing_pincode": "{{row.pincode}}", "billing_state": "{{row.state}}",
                      "billing_country": "India", "billing_email": "{{row.email}}", "billing_phone": "{{row.phone}}",
                      "shipping_is_billing": True, "order_items": [{"name": "Order {{row.id}}", "sku": "{{row.id}}", "units": 1,
                                                                    "selling_price": "{{row.total}}"}],
                      "payment_method": "Prepaid", "sub_total": "{{row.total}}", "length": g("length_cm"), "breadth": g("breadth_cm"),
                      "height": g("height_cm"), "weight": g("weight_kg")},
             "map": {}, "pack": pack, "note": "Shipment banata hai; phir 'AWB lo' chalaiye."},
            {"key": "sr_track", "label": "Shiprocket: track", "method": "GET", "coll": coll, "trigger": "manual", "staff": True,
             "url": "https://apiv2.shiprocket.in/v1/external/courier/track/awb/{{row.awb}}", "auth": auth, "retries": 2,
             "map": {"tracking": "$.tracking_data.shipment_track[0].current_status"}, "pack": pack},
        ]
    if pack == "delhivery":
        auth = {"type": "header", "name": "Authorization", "prefix": "Token", "secret": "delhivery_token"}
        return [
            {"key": "dl_create", "label": "Delhivery: create shipment", "method": "POST", "coll": coll, "trigger": "manual", "staff": True,
             "url": "https://track.delhivery.com/api/cmu/create.json", "auth": auth, "body_type": "form",
             "body": {"format": "json", "data": {"shipments": [{"name": "{{row.name}}", "add": "{{row.address}}", "pin": "{{row.pincode}}",
                                                                 "city": "{{row.city}}", "state": "{{row.state}}", "country": "India",
                                                                 "phone": "{{row.phone}}", "order": "{{row.id}}", "payment_mode": "Prepaid",
                                                                 "total_amount": "{{row.total}}", "weight": g("weight_g")}],
                                                  "pickup_location": {"name": g("pickup_location")}}},
             "map": {"awb": "$.packages[0].waybill"}, "pack": pack},
            {"key": "dl_track", "label": "Delhivery: track", "method": "GET", "coll": coll, "trigger": "manual", "staff": True,
             "url": "https://track.delhivery.com/api/v1/packages/json/", "query": {"waybill": "{{row.awb}}"}, "auth": auth, "retries": 2,
             "map": {"tracking": "$.ShipmentData[0].Shipment.Status.Status"}, "pack": pack},
        ]
    if pack == "msg91":
        return [{"key": "msg91_sms", "label": f"SMS: {g('status') or 'on create'}", "method": "POST", "coll": coll,
                 "trigger": "status" if g("status") else "create", "status": g("status"),
                 "url": "https://control.msg91.com/api/v5/flow", "auth": {"type": "header", "name": "authkey", "secret": "msg91_authkey"},
                 "body": {"template_id": g("template_id"), "short_url": "0",
                          "recipients": [{"mobiles": "91{{row.phone}}", "var1": "{{row.name}}", "var2": "{{row.id}}"}]}, "pack": pack}]
    if pack == "fast2sms":
        return [{"key": "f2s_sms", "label": f"SMS: {g('status') or 'on create'}", "method": "POST", "coll": coll,
                 "trigger": "status" if g("status") else "create", "status": g("status"),
                 "url": "https://www.fast2sms.com/dev/bulkV2", "auth": {"type": "header", "name": "authorization", "secret": "fast2sms_key"},
                 "body": {"route": "dlt", "sender_id": g("sender_id"), "message": g("message_id"),
                          "variables_values": "{{row.name}}|{{row.id}}", "numbers": "{{row.phone}}", "flash": "0"}, "pack": pack}]
    if pack == "whatsapp":
        pid = re.sub(r"\D", "", g("phone_number_id"))
        return [{"key": "wa_template", "label": f"WhatsApp: {g('template') or 'template'}", "method": "POST", "coll": coll,
                 "trigger": "status" if g("status") else "create", "status": g("status"),
                 "url": f"https://graph.facebook.com/v21.0/{pid or '0'}/messages", "auth": {"type": "bearer", "secret": "wa_token"},
                 "body": {"messaging_product": "whatsapp", "to": "91{{row.phone}}", "type": "template",
                          "template": {"name": g("template"), "language": {"code": g("lang") or "en"},
                                       "components": [{"type": "body", "parameters": [{"type": "text", "text": "{{row.name}}"}]}]}},
                 "pack": pack}]
    if pack == "brevo":
        return [{"key": "brevo_mail", "label": "E-mail (Brevo) on a new order", "method": "POST", "coll": coll, "trigger": "create",
                 "url": "https://api.brevo.com/v3/smtp/email", "auth": {"type": "header", "name": "api-key", "secret": "brevo_key"},
                 "body": {"sender": {"email": g("from_email"), "name": g("from_name") or "{{app.name}}"}, "to": [{"email": "{{row.email}}",
                          "name": "{{row.name}}"}], "subject": g("subject"),
                          "htmlContent": "<p>Namaste {{row.name}},</p><p>Order {{row.id}} mil gaya. Total Rs {{row.total}}.</p><p>{{app.name}}</p>"},
                 "pack": pack}]
    if pack == "resend":
        return [{"key": "resend_mail", "label": "E-mail (Resend) on a new order", "method": "POST", "coll": coll, "trigger": "create",
                 "url": "https://api.resend.com/emails", "auth": {"type": "bearer", "secret": "resend_key"}, "idem": "Idempotency-Key",
                 "body": {"from": g("from_email"), "to": ["{{row.email}}"], "subject": g("subject"),
                          "html": "<p>Namaste {{row.name}},</p><p>Order {{row.id}} mil gaya. Total Rs {{row.total}}.</p>"}, "pack": pack}]
    if pack == "google_sheets":
        sid = re.sub(r"[^A-Za-z0-9_\-]", "", g("sheet_id"))
        rng = re.sub(r"[^A-Za-z0-9_!:\- ]", "", g("range") or "Sheet1!A1").replace(" ", "%20")
        return [{"key": "sheet_row", "label": "Google Sheet: add the new row", "method": "POST", "coll": coll, "trigger": "create",
                 "url": f"https://sheets.googleapis.com/v4/spreadsheets/{sid or 'x'}/values/{rng}:append",
                 "query": {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                 "auth": {"type": "google_sa", "secret": "google_sa", "scope": "https://www.googleapis.com/auth/spreadsheets"},
                 "body": {"values": [["{{row.id}}", "{{now}}", "{{row.name}}", "{{row.phone}}", "{{row.total}}", "{{row.status}}"]]}, "pack": pack}]
    if pack == "google_calendar":
        cid = re.sub(r"[^A-Za-z0-9_@.\-]", "", g("calendar_id"))
        return [{"key": "cal_event", "label": "Google Calendar: add the booking", "method": "POST", "coll": coll, "trigger": "create",
                 "url": f"https://www.googleapis.com/calendar/v3/calendars/{cid or 'primary'}/events",
                 "auth": {"type": "google_sa", "secret": "google_sa", "scope": "https://www.googleapis.com/auth/calendar.events"},
                 "body": {"summary": "{{row.service}} - {{row.name}}", "description": "Hoola booking {{row.id}}, phone {{row.phone}}",
                          "start": {"dateTime": "{{row.date}}T{{row.time}}:00", "timeZone": "Asia/Kolkata"},
                          "end": {"dateTime": "{{row.date}}T{{row.time}}:00", "timeZone": "Asia/Kolkata"}}, "pack": pack,
                 "note": f"Event ki lambai Calendar mein badaliye ({g('minutes')} min)."}]
    if pack == "zoho_books":
        dc = {"in": "in", "com": "com", "eu": "eu"}.get(g("dc"), "in")
        org = re.sub(r"\D", "", g("organization_id"))
        return [{"key": "zoho_contact", "label": "Zoho Books: add the customer", "method": "POST", "coll": coll, "trigger": "manual", "staff": False,
                 "url": f"https://www.zohoapis.{dc}/books/v3/contacts", "query": {"organization_id": org},
                 "auth": {"type": "oauth_refresh", "url": f"https://accounts.zoho.{dc}/oauth/v2/token", "prefix": "Zoho-oauthtoken"},
                 "body": {"contact_name": "{{row.name}}", "contact_type": "customer",
                          "contact_persons": [{"first_name": "{{row.name}}", "phone": "{{row.phone}}", "is_primary_contact": True}]}, "pack": pack}]
    if pack == "quickbooks":
        realm = re.sub(r"\D", "", g("realm_id"))
        host = "sandbox-quickbooks.api.intuit.com" if g("sandbox").lower() in ("yes", "true", "1") else "quickbooks.api.intuit.com"
        return [{"key": "qb_receipt", "label": "QuickBooks: sales receipt", "method": "POST", "coll": coll, "trigger": "manual",
                 "url": f"https://{host}/v3/company/{realm or '0'}/salesreceipt", "query": {"minorversion": "75"},
                 "headers": {"Accept": "application/json"},
                 "auth": {"type": "oauth_refresh", "url": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer", "client_in": "basic"},
                 "body": {"Line": [{"Amount": "{{row.total}}", "DetailType": "SalesItemLineDetail",
                                    "SalesItemLineDetail": {"ItemRef": {"value": g("item_id") or "1"}}}],
                          "PrivateNote": "Hoola order {{row.id}}"}, "pack": pack}]
    if pack == "kyc":
        return [{"key": "kyc_check", "label": "KYC check (licensed provider)", "method": "POST", "coll": coll, "trigger": "manual",
                 "url": g("url"), "auth": {"type": "header", "name": g("header") or "x-api-key", "secret": "kyc_key"},
                 "body": {"pan": "{{row." + (re.sub(r"[^a-z0-9_]", "", g("pan_field")) or "pan") + "}}", "name": "{{row.name}}"},
                 "map": {"kyc_status": "$.status"}, "pack": pack}]
    return []

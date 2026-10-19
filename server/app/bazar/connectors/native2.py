"""Wave-2 (P1) Santosh skills: business tools (GST invoice, quotation, udhar, attendance, salary slips, rent receipts),
money helpers (EMI, price watch, subscriptions, tax calendar, bill insights), life trackers (documents, vehicles,
warranties, study and trip plans), safety (scam checker, SOS) and brain-assisted skills (translator, homework, email,
meal plans, recipes). Everything runs on Newtika's stack; skills that need the Claude brain say so."""
from __future__ import annotations

import calendar
import copy
import datetime as dt
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ...db import ListItem as CoreListItem
from ..db import Attendance, Contact, GeneratedDoc, Reminder, Staff, Transaction, UdharEntry
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees, to_paise
from .docs import money, words_inr, write_pdf
from .native import NativeExecutor
from .timeparse import IST, ist_now, to_utc_naive
from .upi import build_upi_intent, valid_vpa
from .whatsapp import WhatsApp

S = lambda **p: {"type": "object", "properties": p}  # noqa: E731
STR, NUM, BOOL = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
ARR = {"type": "array", "items": {"type": "string"}}
OBJ_ARR = {"type": "array", "items": {"type": "object"}}

GST_STATES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland",
    "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_valid(g: str) -> bool:
    g = (g or "").strip().upper()
    if not GSTIN_RE.match(g) or g[:2] not in GST_STATES:
        return False
    total = 0
    for i, ch in enumerate(g[:14]):
        prod = CHARS.index(ch) * (2 if i % 2 else 1)
        total += prod // 36 + prod % 36
    return CHARS[(36 - total % 36) % 36] == g[14]


def state_code(name_or_code: str) -> str:
    s = (name_or_code or "").strip()
    if s[:2].isdigit() and s[:2] in GST_STATES:
        return s[:2]
    low = s.lower()
    for code, name in GST_STATES.items():
        if name.lower() == low or (len(low) > 3 and name.lower().startswith(low)):
            return code
    raise ToolError(f"Unknown state '{name_or_code}'. Use the state name, e.g. Maharashtra.")


def fy_label(d: dt.date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[-2:]}"


SCAM_RULES = [
    (r"\b(kyc|pan|aadhaar)\b.*\b(update|expire|block|suspend|verify)", 3, "Asks you to 'update KYC' or warns your account will be blocked"),
    (r"\b(otp|pin|cvv|password)\b", 3, "Mentions OTP/PIN/CVV/password — no bank or company ever asks for these"),
    (r"(bit\.ly|tinyurl|t\.co/|cutt\.ly|rb\.gy|is\.gd|wa\.me/\d)", 2, "Uses a short or disguised link"),
    (r"\b(lottery|lucky draw|winner|won|prize|kbc|jackpot|cashback of)\b", 3, "Promises a prize, lottery or surprise cashback"),
    (r"\b(electricity|light|bijli)\b.*\b(disconnect|cut|kat|tonight|aaj raat)", 3, "Threatens to cut electricity tonight — classic bill scam"),
    (r"\b(customs|parcel|courier)\b.*\b(pay|fee|held|seized)", 2, "Asks a fee to release a parcel"),
    (r"\b(police|cbi|ed|narcotics|digital arrest|court)\b", 3, "Uses police/CBI/'digital arrest' threats — real agencies never do this on call/WhatsApp"),
    (r"\b(work from home|part[- ]time job|like videos|rate hotels|task)\b.*\b(earn|daily|₹|rs)", 3, "Easy-money task job — usually a deposit scam"),
    (r"\b(refund|reversal)\b.*\b(link|click|collect)", 2, "Asks you to click or approve something to 'receive' a refund"),
    (r"\b(collect request|request money|scan.*receive|receive money.*pin)\b", 3, "Says you must enter a PIN or scan a QR to RECEIVE money — PIN is only ever for sending"),
    (r"\b(urgent|immediately|within \d+ (hours|minutes)|last chance|today only)\b", 1, "Creates urgency"),
    (r"\b(anydesk|teamviewer|quicksupport|rustdesk|screen ?share)\b", 3, "Asks you to install a screen-sharing app"),
    (r"\.apk\b", 3, "Asks you to install an APK file"),
]

TAX_RULES = {
    "salaried": [("ITR filing (non-audit)", 7, 31)],
    "business": [("ITR filing (non-audit)", 7, 31), ("Advance tax 1st instalment (15%)", 6, 15), ("Advance tax 2nd instalment (45%)", 9, 15),
                 ("Advance tax 3rd instalment (75%)", 12, 15), ("Advance tax 4th instalment (100%)", 3, 15)],
    "audit": [("Tax audit report & ITR (audit cases)", 10, 31)],
    "tds": [("TDS return Q1", 7, 31), ("TDS return Q2", 10, 31), ("TDS return Q3", 1, 31), ("TDS return Q4", 5, 31)],
}
TRIP_PACK = {
    "base": ["ID proof (Aadhaar/DL) — originals and phone copies", "Tickets and hotel bookings on phone", "Phone charger + power bank",
             "Regular medicines + basic first aid", "Some cash for small shops", "Water bottle"],
    "hills": ["Warm jacket and woollens", "Comfortable walking shoes", "Motion-sickness tablets"],
    "beach": ["Sunscreen", "Light cotton clothes", "Slippers", "Swimwear"],
    "pilgrimage": ["Traditional clothes", "Puja items if needed", "Light bag for darshan queues"],
    "business": ["Laptop + charger", "Visiting cards", "Formal wear"],
    "family": ["Snacks for kids", "Kids' medicines", "Extra clothes for kids"],
}


def _fuzzy(name: str, options: list[Any], attr: str = "name") -> Any:
    n = name.strip().lower()
    hits = [o for o in options if getattr(o, attr).lower() == n] or [o for o in options if n in getattr(o, attr).lower() or getattr(o, attr).lower() in n]
    return hits[0] if len(hits) == 1 else None


class Native2Executor(NativeExecutor):
    """NativeExecutor + the 27 wave-2 skills."""

    SPECS = {**NativeExecutor.SPECS, **{
        "vault": [ToolSpec("save_document", "Save a document's details and expiry (only the last 4 digits of any ID number are kept).",
                           {**S(name=STR, kind=STR, id_last4=STR, expiry=STR, file_url=STR, holder=STR), "required": ["name"]}, 1),
                  ToolSpec("list_documents", "List saved documents and expiry dates.", S(), 0)],
        "translator": [ToolSpec("translate", "Translate text between Indian languages and English (the Santosh brain writes the translation).",
                                {**S(text=STR, to=STR), "required": ["text", "to"]}, 0)],
        "voice_notes": [ToolSpec("transcribe", "Turn a voice note into text.", {**S(audio_url=STR), "required": ["audio_url"]}, 0)],
        "email_summary": [ToolSpec("summarise_email", "Summarise an email the user pasted and draft a reply.", {**S(text=STR), "required": ["text"]}, 0)],
        "resume": [ToolSpec("build_resume", "Make a one-page resume PDF.",
                            {**S(name=STR, phone=STR, email=STR, city=STR, headline=STR, summary=STR, experience=OBJ_ARR, education=OBJ_ARR,
                                 skills=ARR, languages=ARR), "required": ["name"]}, 1)],
        "gst_invoice": [
            ToolSpec("set_business", "Save the user's business details for invoices: name, GSTIN (optional), state, address, UPI ID.",
                     {**S(name=STR, gstin=STR, state=STR, address=STR, upi_id=STR, phone=STR), "required": ["name"]}, 1),
            ToolSpec("create_invoice", "Create a GST tax invoice PDF. items: [{name, qty, rate, gst_rate, hsn, unit}] with rate in rupees before tax.",
                     {**S(customer_name=STR, customer_gstin=STR, customer_state=STR, customer_address=STR, items=OBJ_ARR, notes=STR),
                      "required": ["customer_name", "items"]}, 1)],
        "quotation": [ToolSpec("create_quotation", "Create a quotation/estimate PDF. items: [{name, qty, rate, unit}]; optional gst_rate per item.",
                               {**S(customer_name=STR, items=OBJ_ARR, valid_days=NUM, notes=STR), "required": ["customer_name", "items"]}, 1)],
        "udhar": [
            ToolSpec("add_udhar", "Record credit given to a customer (udhar).", {**S(customer=STR, amount_rupees=NUM, phone=STR, note=STR),
                                                                                 "required": ["customer", "amount_rupees"]}, 1),
            ToolSpec("settle_udhar", "Record money received from a customer against udhar.", {**S(customer=STR, amount_rupees=NUM),
                                                                                              "required": ["customer", "amount_rupees"]}, 1),
            ToolSpec("list_udhar", "Who owes how much.", S(), 0),
            ToolSpec("send_udhar_reminders", "Ask approval to send polite WhatsApp payment reminders (with UPI link) to customers who owe.",
                     S(customers=ARR, language=STR), 2)],
        "attendance": [
            ToolSpec("add_staff", "Add a staff member with monthly salary.", {**S(name=STR, phone=STR, monthly_salary_rupees=NUM, paid_leaves=NUM),
                                                                              "required": ["name"]}, 1),
            ToolSpec("mark_attendance", "Mark attendance for a day (default today). Unlisted staff are not changed.",
                     S(present=ARR, absent=ARR, half_day=ARR, date=STR), 1),
            ToolSpec("attendance_report", "Monthly attendance per staff (YYYY-MM).", S(month=STR), 0)],
        "salary": [ToolSpec("salary_slips", "Make salary slip PDFs for a month from attendance and salary.", S(month=STR), 1)],
        "rent_receipt": [ToolSpec("rent_receipts", "Make monthly rent receipt PDFs (for HRA). months as YYYY-MM list or from/to.",
                                  {**S(landlord_name=STR, landlord_pan=STR, tenant_name=STR, property_address=STR, monthly_rent_rupees=NUM,
                                       months=ARR, from_month=STR, to_month=STR, mode=STR),
                                   "required": ["landlord_name", "property_address", "monthly_rent_rupees"]}, 1)],
        "emi": [ToolSpec("emi_calc", "EMI, total interest and total payment for a loan.", {**S(principal_rupees=NUM, annual_rate_percent=NUM,
                                                                                               months=NUM), "required": ["principal_rupees", "annual_rate_percent", "months"]}, 0),
                ToolSpec("track_emi", "Monthly EMI reminder.", {**S(name=STR, amount_rupees=NUM, day_of_month=NUM, months_left=NUM),
                                                                "required": ["name", "amount_rupees", "day_of_month"]}, 1)],
        "price_tracker": [ToolSpec("watch_price", "Watch a product for a target price.", {**S(product=STR, target_rupees=NUM, url=STR),
                                                                                          "required": ["product", "target_rupees"]}, 1),
                          ToolSpec("record_price", "Record a price seen for a watched product; alerts if at or below target.",
                                   {**S(product=STR, price_rupees=NUM, store=STR), "required": ["product", "price_rupees"]}, 1),
                          ToolSpec("list_watches", "Watched products.", S(), 0)],
        "recipe": [ToolSpec("ingredients_to_list", "Add a recipe's ingredients to a shopping list (the brain works out the ingredients).",
                            {**S(dish=STR, ingredients=ARR, list=STR), "required": ["ingredients"]}, 1)],
        "meal_plan": [ToolSpec("save_meal_plan", "Save a weekly meal plan (day -> meals) and add groceries to the list.",
                               {**S(plan={"type": "object"}, groceries=ARR), "required": ["plan"]}, 1),
                      ToolSpec("get_meal_plan", "The saved meal plan.", S(), 0)],
        "homework": [ToolSpec("homework_context", "Child's class, board and language from family profiles, so help fits the syllabus.",
                              S(child=STR), 0)],
        "study_plan": [ToolSpec("make_study_plan", "Day-by-day study plan to an exam with daily reminders; last ~20% of days for revision.",
                                {**S(exam=STR, exam_date=STR, subjects=ARR, daily_time=STR), "required": ["exam", "exam_date", "subjects"]}, 1)],
        "trip": [ToolSpec("make_trip", "Trip checklist and reminders (book, pack, leave).",
                          {**S(destination=STR, start_date=STR, days=NUM, travellers=NUM, trip_type=STR), "required": ["destination", "start_date"]}, 1)],
        "vehicle": [ToolSpec("add_vehicle", "Track a vehicle's insurance, PUC and service dates (reminds 15 days before).",
                             {**S(number=STR, insurance_expiry=STR, puc_expiry=STR, service_due=STR), "required": ["number"]}, 1),
                    ToolSpec("list_vehicles", "Tracked vehicles.", S(), 0)],
        "warranty": [ToolSpec("add_warranty", "Track a product warranty (reminds 30 days before it ends).",
                              {**S(product=STR, purchase_date=STR, months=NUM, bill_url=STR), "required": ["product", "purchase_date", "months"]}, 1),
                     ToolSpec("list_warranties", "Tracked warranties.", S(), 0)],
        "subscriptions": [ToolSpec("add_subscription", "Track a subscription (reminds 3 days before renewal).",
                                   {**S(name=STR, amount_rupees=NUM, cycle={"type": "string", "enum": ["monthly", "quarterly", "yearly"]}, next_date=STR),
                                    "required": ["name", "amount_rupees", "next_date"]}, 1),
                          ToolSpec("list_subscriptions", "All subscriptions with the monthly total.", S(), 0)],
        "phone_plan": [ToolSpec("compare_plans", "Pick the cheapest plan that covers usage. plans: [{name, price_rupees, validity_days, data_gb_per_day, unlimited_calls}].",
                                {**S(data_gb_per_day=NUM, needs_unlimited_calls=BOOL, plans=OBJ_ARR), "required": ["data_gb_per_day", "plans"]}, 0)],
        "power_insights": [ToolSpec("bill_insights", "Trend of the user's electricity bills paid or fetched through Santosh.", S(), 0)],
        "tax_calendar": [ToolSpec("tax_calendar", "Upcoming income-tax, TDS and GST due dates for the user's profile.",
                                  S(profiles=ARR, gst=STR, days=NUM), 0),
                         ToolSpec("set_tax_reminders", "Set reminders 5 days before each upcoming due date.", S(profiles=ARR, gst=STR, days=NUM), 1)],
        "form_filler": [ToolSpec("profile_for_form", "Values from the user's saved profile for the form fields asked.", {**S(fields=ARR), "required": ["fields"]}, 0)],
        "scam_check": [ToolSpec("check_message", "Check an SMS, WhatsApp message or call script for fraud signs.", {**S(text=STR), "required": ["text"]}, 0)],
        "sos": [ToolSpec("sos", "Emergency: alert family/emergency contacts on WhatsApp with location, and show emergency numbers.",
                         S(message=STR, lat=NUM, lng=NUM), 1)],
    }}

    # ------------------------------------------------------------------ helpers
    def _prof(self, ctx: Ctx) -> dict[str, Any]:
        return copy.deepcopy(ctx.user.profile or {})  # deep copy so SQLAlchemy sees nested changes

    def _save_prof(self, ctx: Ctx, prof: dict[str, Any]) -> None:
        ctx.user.profile = prof

    def _date(self, s: Any, field: str) -> dt.date:
        s = str(s or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ToolError(f"{field.replace('_', ' ').title()}: give a date like 2026-12-31 or 31/12/2026")

    def _remind_on(self, ctx: Ctx, text: str, day: dt.date, kind: str = "reminder", repeat: str = "", meta: dict | None = None,
                   hour: int = 9) -> None:
        when = dt.datetime.combine(day, dt.time(hour, 0), tzinfo=IST)
        if when <= ist_now():
            return
        ctx.session.add(Reminder(user_id=ctx.user.id, kind=kind, text=text, due_at=to_utc_naive(when), repeat=repeat, meta=meta or {}))

    def _doc(self, ctx: Ctx, kind: str, number: str, data: dict[str, Any], render) -> dict[str, Any]:
        root = Path(ctx.settings.files_dir).resolve() / re.sub(r"[^A-Za-z0-9_-]", "_", ctx.user.id)
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", number)
        path = render(root / f"{kind}-{safe}.pdf")
        d = GeneratedDoc(user_id=ctx.user.id, kind=kind, number=number, data=data, file_name=str(path))
        ctx.session.add(d)
        ctx.session.flush()
        # The owner downloads it from the Santosh app (signed-in route); service.run adds a chat download card.
        return {"doc_id": d.id, "number": number, "download": f"/api/bazar/files/{d.id}"}

    def _core_list_add(self, ctx: Ctx, list_name: str, items: list[str]) -> list[str]:
        """Shopping items go to Santosh's own lists (list_show / list_done), not a separate Bazar list."""
        name = (list_name or "shopping").strip().lower()[:80] or "shopping"
        have = {r.text.lower() for r in ctx.session.scalars(select(CoreListItem).where(
            CoreListItem.tenant_id == ctx.user.id, CoreListItem.list_name == name, CoreListItem.done.is_(False))).all()}
        added = []
        for it in items:
            it = str(it).strip()[:200]
            if it and it.lower() not in have:
                ctx.session.add(CoreListItem(tenant_id=ctx.user.id, list_name=name, text=it))
                have.add(it.lower())
                added.append(it)
        return added

    def _needs_brain(self, what: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"brain_task": what, **payload,
                "instruction": "Do this yourself in your reply to the user (this skill is done by the Santosh brain)."}

    # ------------------------------------------------------------------ documents vault
    def _save_document(self, pack, a, ctx):
        prof = self._prof(ctx)
        last4 = re.sub(r"\D", "", str(a.get("id_last4") or ""))[-4:]
        entry = {"name": a["name"], "kind": a.get("kind", ""), "holder": a.get("holder", ""), "id_last4": last4,
                 "file_url": a.get("file_url", "")}
        if a.get("expiry"):
            exp = self._date(a["expiry"], "expiry")
            entry["expiry"] = exp.isoformat()
            self._remind_on(ctx, f"{a['name']} expires on {exp.strftime('%d %b %Y')} — renew it", exp - dt.timedelta(days=30))
        prof["documents"] = [d for d in prof.get("documents", []) if d["name"].lower() != a["name"].lower()] + [entry]
        self._save_prof(ctx, prof)
        return {"saved": entry, "note": "Only the last 4 digits of ID numbers are stored."}

    def _list_documents(self, pack, a, ctx):
        return {"documents": sorted(self._prof(ctx).get("documents", []), key=lambda d: d.get("expiry", "9999"))}

    # ------------------------------------------------------------------ brain-assisted
    def _translate(self, pack, a, ctx):
        return self._needs_brain("translate", {"text": a["text"], "to": a["to"]})

    def _transcribe(self, pack, a, ctx):
        raise ToolError("Voice-note transcription isn't switched on yet. Send the note as text, or I can read it once speech-to-text is connected.")

    def _summarise_email(self, pack, a, ctx):
        return self._needs_brain("summarise the email in 3 bullets and draft a short reply", {"text": str(a["text"])[:8000]})

    def _homework_context(self, pack, a, ctx):
        fam = self._prof(ctx).get("family", [])
        kids = [f for f in fam if f.get("relation", "").lower() in ("son", "daughter", "beta", "beti", "child", "mulga", "mulgi")]
        if a.get("child"):
            kids = [k for k in kids if k["name"].lower() == str(a["child"]).lower()] or kids
        return self._needs_brain("explain step by step at the child's level, in their language, without just giving answers",
                                 {"children": kids, "tip": "Save class/board in family profiles for better help."})

    # ------------------------------------------------------------------ resume
    def _build_resume(self, pack, a, ctx):
        name = a["name"]
        rows = []
        for e in a.get("experience") or []:
            rows.append([f"<b>{e.get('role', '')}</b> · {e.get('company', '')}", e.get("period", ""), e.get("details", "")])
        for e in a.get("education") or []:
            rows.append([f"<b>{e.get('degree', '')}</b> · {e.get('institute', '')}", e.get("year", ""), e.get("score", "")])
        contact = [x for x in [a.get("phone"), a.get("email"), a.get("city")] if x]
        footer = []
        if a.get("skills"):
            footer.append("<b>Skills:</b> " + ", ".join(a["skills"]))
        if a.get("languages"):
            footer.append("<b>Languages:</b> " + ", ".join(a["languages"]))
        number = re.sub(r"\W+", "-", name.lower())[:30] + "-" + ist_now().strftime("%Y%m%d")
        res = self._doc(ctx, "resume", number, dict(a), lambda p: write_pdf(
            p, name, [a.get("headline", ""), " · ".join(contact)], [], ["Experience & education", "When", "Details"] if rows else [], rows, [],
            ([f"<b>Summary:</b> {a['summary']}"] if a.get("summary") else []) + footer, col_widths=None))
        return {**res, "message": "Resume ready."}

    # ------------------------------------------------------------------ GST invoice & quotation
    def _set_business(self, pack, a, ctx):
        prof = self._prof(ctx)
        biz = dict(prof.get("business", {}))
        biz.update({k: v for k, v in a.items() if v})
        if biz.get("gstin"):
            biz["gstin"] = str(biz["gstin"]).upper().strip()
            if not gstin_valid(biz["gstin"]):
                raise ToolError("That GSTIN doesn't look valid (format or check digit). Please check it.")
            biz["state_code"] = biz["gstin"][:2]
        elif biz.get("state"):
            biz["state_code"] = state_code(biz["state"])
        if biz.get("upi_id") and not valid_vpa(biz["upi_id"]):
            raise ToolError("UPI ID doesn't look right.")
        prof["business"] = biz
        self._save_prof(ctx, prof)
        return {"business": {k: v for k, v in biz.items() if k != "invoice_seq"}}

    def _lines(self, items: list[dict[str, Any]], default_gst: float | None) -> list[dict[str, Any]]:
        out = []
        for it in items:
            qty = float(it.get("qty", 1) or 1)
            rate = to_paise(it.get("rate", it.get("price", 0)))
            gst = float(it.get("gst_rate", default_gst if default_gst is not None else 0) or 0)
            if gst not in (0, 0.25, 3, 5, 12, 18, 28, 40):
                raise ToolError(f"GST rate {gst}% is not a standard slab")
            taxable = int(round(qty * rate))
            out.append({"name": str(it.get("name", "Item")), "hsn": str(it.get("hsn", "")), "unit": str(it.get("unit", "")),
                        "qty": qty, "rate": rate, "gst": gst, "taxable": taxable, "tax": int(round(taxable * gst / 100))})
        if not out:
            raise ToolError("Add at least one item")
        return out

    def _create_invoice(self, pack, a, ctx):
        prof = self._prof(ctx)
        biz = prof.get("business")
        if not biz or not biz.get("name"):
            raise ToolError("First tell me your business name, GSTIN (if any) and state, so I can put them on the invoice.")
        seller_state = biz.get("state_code") or (state_code(biz["state"]) if biz.get("state") else "")
        if not seller_state:
            raise ToolError("Which state is your business registered in?")
        cust_gstin = str(a.get("customer_gstin") or "").upper().strip()
        if cust_gstin and not gstin_valid(cust_gstin):
            raise ToolError("Customer GSTIN doesn't look valid.")
        pos = cust_gstin[:2] if cust_gstin else (state_code(a["customer_state"]) if a.get("customer_state") else seller_state)
        lines = self._lines(a["items"], None)
        taxable = sum(l["taxable"] for l in lines)
        tax = sum(l["tax"] for l in lines)
        intra = pos == seller_state
        total = taxable + tax
        today = ist_now().date()
        seq_key = f"invoice_seq_{fy_label(today)}"
        seq = int(biz.get(seq_key, 0)) + 1
        biz[seq_key] = seq
        prof["business"] = biz
        self._save_prof(ctx, prof)
        number = f"INV/{fy_label(today)}/{seq:04d}"
        totals = [("Taxable value", money(taxable))]
        if intra:
            totals += [("CGST", money(tax // 2)), ("SGST", money(tax - tax // 2))]
        else:
            totals += [("IGST", money(tax))]
        totals.append(("Total", money(total)))
        registered = bool(biz.get("gstin"))
        title = "Tax Invoice" if registered else "Bill of Supply"
        left = [f"<b>{biz['name']}</b>", biz.get("address", ""), f"GSTIN: {biz['gstin']}" if registered else "Not registered under GST",
                f"State: {GST_STATES.get(seller_state, '')} ({seller_state})"]
        right = [f"<b>{number}</b>", f"Date: {today.strftime('%d %b %Y')}", f"Bill to: <b>{a['customer_name']}</b>",
                 a.get("customer_address", ""), f"GSTIN: {cust_gstin}" if cust_gstin else "",
                 f"Place of supply: {GST_STATES.get(pos, '')} ({pos})"]
        rows = [[i + 1, f"{l['name']}" + (f"<br/>HSN/SAC {l['hsn']}" if l["hsn"] else ""), f"{l['qty']:g} {l['unit']}".strip(),
                 money(l["rate"]), f"{l['gst']:g}%", money(l["taxable"])] for i, l in enumerate(lines)]
        footer = [f"Amount in words: {words_inr(total)}"]
        if biz.get("upi_id"):
            footer.append(f"Pay by UPI: {biz['upi_id']}")
        if a.get("notes"):
            footer.append(a["notes"])
        footer.append("This is a computer-generated invoice.")
        if not registered:
            totals = [("Total", money(taxable))]
            total = taxable
        res = self._doc(ctx, "invoice", number, {"customer": a["customer_name"], "total_paise": total, "lines": lines, "intra_state": intra},
                        lambda p: write_pdf(p, title, [x for x in left if x], [x for x in right if x],
                                            ["#", "Item", "Qty", "Rate", "GST", "Taxable"], rows, totals, footer))
        out = {**res, "invoice_type": title, "taxable": rupees(taxable), "total": rupees(total),
               "tax_split": ("CGST + SGST" if intra else "IGST") if registered else "No GST (not registered)"}
        if biz.get("upi_id"):
            out["payment_link"] = build_upi_intent(biz["upi_id"], biz["name"], total, number)
        return out

    def _create_quotation(self, pack, a, ctx):
        biz = self._prof(ctx).get("business") or {"name": ctx.user.name or "Quotation"}
        lines = self._lines(a["items"], 0)
        taxable = sum(l["taxable"] for l in lines)
        tax = sum(l["tax"] for l in lines)
        today = ist_now().date()
        valid = int(a.get("valid_days") or 15)
        number = f"QT/{today.strftime('%y%m%d')}/{abs(hash(a['customer_name'])) % 1000:03d}"
        rows = [[i + 1, l["name"], f"{l['qty']:g} {l['unit']}".strip(), money(l["rate"]), money(l["taxable"])] for i, l in enumerate(lines)]
        totals = [("Subtotal", money(taxable))] + ([("GST", money(tax))] if tax else []) + [("Total", money(taxable + tax))]
        res = self._doc(ctx, "quotation", number, {"customer": a["customer_name"], "total_paise": taxable + tax},
                        lambda p: write_pdf(p, "Quotation", [f"<b>{biz.get('name', '')}</b>", biz.get("address", ""), biz.get("phone", "")],
                                            [f"<b>{number}</b>", f"Date: {today.strftime('%d %b %Y')}",
                                             f"Valid till: {(today + dt.timedelta(days=valid)).strftime('%d %b %Y')}", f"For: <b>{a['customer_name']}</b>"],
                                            ["#", "Item", "Qty", "Rate", "Amount"], rows, totals,
                                            [f"Amount in words: {words_inr(taxable + tax)}"] + ([a["notes"]] if a.get("notes") else [])))
        return {**res, "total": rupees(taxable + tax), "valid_till": (today + dt.timedelta(days=valid)).isoformat()}

    # ------------------------------------------------------------------ udhar
    def _udhar_totals(self, ctx: Ctx) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for e in ctx.session.scalars(select(UdharEntry).where(UdharEntry.user_id == ctx.user.id).order_by(UdharEntry.created_at)).all():
            k = e.customer.lower()
            row = out.setdefault(k, {"customer": e.customer, "phone": "", "balance": 0})
            row["balance"] += e.amount_paise
            row["phone"] = e.phone or row["phone"]
        return out

    def _add_udhar(self, pack, a, ctx):
        amt = to_paise(a["amount_rupees"])
        if amt <= 0:
            raise ToolError("Amount must be more than 0")
        ctx.session.add(UdharEntry(user_id=ctx.user.id, customer=str(a["customer"]).strip().title(), phone=str(a.get("phone") or ""),
                                   amount_paise=amt, note=str(a.get("note") or "")))
        ctx.session.flush()
        bal = self._udhar_totals(ctx)[str(a["customer"]).strip().lower()]["balance"]
        return {"customer": str(a["customer"]).title(), "added": rupees(amt), "total_due": rupees(bal)}

    def _settle_udhar(self, pack, a, ctx):
        key = str(a["customer"]).strip().lower()
        tot = self._udhar_totals(ctx)
        if key not in tot:
            raise ToolError(f"No udhar found for {a['customer']}")
        amt = to_paise(a["amount_rupees"])
        ctx.session.add(UdharEntry(user_id=ctx.user.id, customer=tot[key]["customer"], amount_paise=-amt, note="received"))
        ctx.session.flush()
        return {"customer": tot[key]["customer"], "received": rupees(amt), "still_due": rupees(self._udhar_totals(ctx)[key]["balance"])}

    def _list_udhar(self, pack, a, ctx):
        rows = sorted([r for r in self._udhar_totals(ctx).values() if r["balance"] > 0], key=lambda r: -r["balance"])
        return {"total_outstanding": rupees(sum(r["balance"] for r in rows)),
                "customers": [{"customer": r["customer"], "due": rupees(r["balance"]), "phone": r["phone"]} for r in rows]}

    def _send_udhar_reminders(self, pack, a, ctx):
        rows = [r for r in self._udhar_totals(ctx).values() if r["balance"] > 0]
        names = [n.lower() for n in a.get("customers") or []]
        if names:
            rows = [r for r in rows if r["customer"].lower() in names]
        rows = [r for r in rows if r["phone"]]
        if not rows:
            raise ToolError("No customers with a phone number and pending udhar.")
        biz = self._prof(ctx).get("business", {})
        shop = biz.get("name") or ctx.user.name or "our shop"
        lang = a.get("language") or ctx.user.language or "hi"
        msgs = []
        for r in rows:
            link = build_upi_intent(biz["upi_id"], shop, r["balance"], "Udhar payment") if biz.get("upi_id") else ""
            text = {"mr": f"नमस्कार {r['customer']}, {shop} कडे तुमची {rupees(r['balance'])} बाकी आहे. सोयीनुसार भरा.",
                    "en": f"Hello {r['customer']}, a balance of {rupees(r['balance'])} is pending at {shop}. Please pay when convenient."}.get(
                lang, f"Namaste {r['customer']} ji, {shop} par aapka {rupees(r['balance'])} baaki hai. Suvidha anusaar bhugtan kar dijiye.")
            if link:
                text += f" UPI: {link}"
            msgs.append({"name": r["customer"], "phone": r["phone"], "text": text})
        return NeedsApproval(tier=2, title=f"Send udhar reminders to {len(msgs)} customers", payee="WhatsApp", amount_paise=0,
                             items=[{"name": f"{m['name']}: {m['text'][:70]}…", "price_paise": None} for m in msgs], pay_method="No payment",
                             action={"executor": "native", "pack_id": pack.id, "name": "send_messages", "args": {"messages": msgs}})

    # ------------------------------------------------------------------ staff
    def _staff(self, ctx: Ctx) -> list[Staff]:
        return list(ctx.session.scalars(select(Staff).where(Staff.user_id == ctx.user.id, Staff.active.is_(True))).all())

    def _add_staff(self, pack, a, ctx):
        s = Staff(user_id=ctx.user.id, name=str(a["name"]).title(), phone=str(a.get("phone") or ""),
                  monthly_salary_paise=to_paise(a["monthly_salary_rupees"]) if a.get("monthly_salary_rupees") else 0,
                  paid_leaves_per_month=int(a.get("paid_leaves") or 0))
        ctx.session.add(s)
        ctx.session.flush()
        return {"staff": s.name, "salary": rupees(s.monthly_salary_paise), "paid_leaves": s.paid_leaves_per_month}

    def _mark_attendance(self, pack, a, ctx):
        day = self._date(a["date"], "date") if a.get("date") else ist_now().date()
        staff = self._staff(ctx)
        if not staff:
            raise ToolError("Add your staff first, e.g. 'Raju staff hai, salary 12000'.")
        done, unknown = {}, []
        for status, key in (("present", "present"), ("absent", "absent"), ("half", "half_day")):
            for n in a.get(key) or []:
                s = _fuzzy(str(n), staff)
                if not s:
                    unknown.append(n)
                    continue
                row = ctx.session.scalars(select(Attendance).where(Attendance.staff_id == s.id, Attendance.day == day)).first()
                if row is None:
                    row = Attendance(staff_id=s.id, day=day, status=status)
                    ctx.session.add(row)
                row.status = status
                done[s.name] = status
        out: dict[str, Any] = {"date": day.isoformat(), "marked": done}
        if unknown:
            out["not_found"] = unknown
        return out

    def _month_counts(self, ctx: Ctx, month: str) -> tuple[dt.date, int, dict[str, dict[str, float]]]:
        y, m = map(int, month.split("-"))
        days = calendar.monthrange(y, m)[1]
        start, end = dt.date(y, m, 1), dt.date(y, m, days)
        out = {}
        for s in self._staff(ctx):
            rows = ctx.session.scalars(select(Attendance).where(Attendance.staff_id == s.id, Attendance.day >= start, Attendance.day <= end)).all()
            c = {"present": 0.0, "absent": 0.0, "half": 0.0}
            for r in rows:
                c[r.status] += 1
            out[s.id] = c
        return start, days, out

    def _attendance_report(self, pack, a, ctx):
        month = str(a.get("month") or ist_now().strftime("%Y-%m"))
        _, days, counts = self._month_counts(ctx, month)
        staff = {s.id: s for s in self._staff(ctx)}
        return {"month": month, "staff": [{"name": staff[k].name, "present": v["present"], "half_days": v["half"], "absent": v["absent"]}
                                          for k, v in counts.items()]}

    def _salary_slips(self, pack, a, ctx):
        month = str(a.get("month") or (ist_now().date().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m"))
        start, days, counts = self._month_counts(ctx, month)
        biz = self._prof(ctx).get("business", {})
        slips = []
        for s in self._staff(ctx):
            c = counts[s.id]
            if not s.monthly_salary_paise:
                continue
            marked = c["present"] + c["half"] + c["absent"]
            unmarked = days - marked  # treated as present (weekly offs, holidays not marked absent)
            leave_paid = min(c["absent"], s.paid_leaves_per_month)
            payable_days = c["present"] + unmarked + 0.5 * c["half"] + leave_paid
            pay = int(round(s.monthly_salary_paise * payable_days / days / 100)) * 100  # nearest rupee
            deduction = s.monthly_salary_paise - pay
            number = f"{month}-{re.sub(r'[^A-Za-z]', '', s.name)[:12]}"
            res = self._doc(ctx, "salary_slip", number, {"staff": s.name, "month": month, "net_paise": pay},
                            lambda p, s=s, c=c, pay=pay, deduction=deduction, payable_days=payable_days: write_pdf(
                                p, f"Salary slip · {start.strftime('%B %Y')}",
                                [f"<b>{biz.get('name') or ctx.user.name or 'Employer'}</b>", biz.get("address", "")],
                                [f"Employee: <b>{s.name}</b>", f"Phone: {s.phone}" if s.phone else ""],
                                ["Item", "Days / amount"],
                                [["Days in month", days], ["Present", f"{c['present']:g}"], ["Half days", f"{c['half']:g}"],
                                 ["Absent", f"{c['absent']:g}"], ["Paid leave allowed", s.paid_leaves_per_month], ["Payable days", f"{payable_days:g}"]],
                                [("Monthly salary", money(s.monthly_salary_paise)), ("Deduction for unpaid absence", money(deduction)), ("Net pay", money(pay))],
                                [f"Net pay in words: {words_inr(pay)}", "Days not marked are counted as working days."]))
            slips.append({"staff": s.name, "net_pay": rupees(pay), **res})
        if not slips:
            raise ToolError("No staff with a salary set. Add salary first.")
        return {"month": month, "slips": slips}

    # ------------------------------------------------------------------ rent receipts
    def _rent_receipts(self, pack, a, ctx):
        months = list(a.get("months") or [])
        if not months and a.get("from_month") and a.get("to_month"):
            y, m = map(int, a["from_month"].split("-"))
            ty, tm = map(int, a["to_month"].split("-"))
            while (y, m) <= (ty, tm):
                months.append(f"{y}-{m:02d}")
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if not months:
            raise ToolError("Which months? e.g. from 2026-04 to 2027-03")
        rent = to_paise(a["monthly_rent_rupees"])
        tenant = a.get("tenant_name") or ctx.user.name or "Tenant"
        files = []
        for mo in months[:24]:
            y, m = map(int, mo.split("-"))
            label = dt.date(y, m, 1).strftime("%B %Y")
            res = self._doc(ctx, "rent_receipt", f"RENT-{mo}", {"month": mo, "rent_paise": rent},
                            lambda p, label=label: write_pdf(
                                p, "Rent Receipt", [f"Received from: <b>{tenant}</b>", f"Property: {a['property_address']}"],
                                [f"Month: <b>{label}</b>", f"Mode: {a.get('mode') or 'UPI / bank transfer'}"], [], [],
                                [("Rent received", money(rent))],
                                [f"Received with thanks a sum of {words_inr(rent)} towards rent for {label}.",
                                 f"Landlord: <b>{a['landlord_name']}</b>" + (f" · PAN {str(a['landlord_pan']).upper()}" if a.get("landlord_pan") else ""),
                                 "Signature: ______________________"]))
            files.append({"month": mo, **res})
        annual = rent * 12
        note = "Landlord PAN is needed for HRA when yearly rent is above ₹1,00,000." if annual > 10_000_000 and not a.get("landlord_pan") else ""
        return {"receipts": files, "monthly_rent": rupees(rent), **({"note": note} if note else {})}

    # ------------------------------------------------------------------ EMI
    def _emi_calc(self, pack, a, ctx):
        p = float(a["principal_rupees"])
        n = int(a["months"])
        r = float(a["annual_rate_percent"]) / 1200
        if p <= 0 or n <= 0:
            raise ToolError("Loan amount and months must be more than 0")
        emi = p / n if r == 0 else p * r * (1 + r) ** n / ((1 + r) ** n - 1)
        total = emi * n
        return {"emi": rupees(int(round(emi * 100))), "total_interest": rupees(int(round((total - p) * 100))),
                "total_payment": rupees(int(round(total * 100))), "months": n}

    def _track_emi(self, pack, a, ctx):
        return self._add_bill_reminder(pack, {"name": f"EMI: {a['name']}", "day_of_month": a["day_of_month"], "amount_rupees": a["amount_rupees"]}, ctx)

    # ------------------------------------------------------------------ price tracker
    def _watch_price(self, pack, a, ctx):
        prof = self._prof(ctx)
        w = {"product": a["product"], "target_paise": to_paise(a["target_rupees"]), "url": a.get("url", ""), "seen": []}
        prof["price_watches"] = [x for x in prof.get("price_watches", []) if x["product"].lower() != a["product"].lower()] + [w]
        self._save_prof(ctx, prof)
        return {"watching": a["product"], "target": rupees(w["target_paise"]),
                "note": "Tell me prices you see (or connect a store feed) and I'll alert you at your target."}

    def _record_price(self, pack, a, ctx):
        prof = self._prof(ctx)
        ws = prof.get("price_watches", [])
        w = next((x for x in ws if a["product"].lower() in x["product"].lower()), None)
        if not w:
            raise ToolError("I'm not watching that product yet.")
        price = to_paise(a["price_rupees"])
        w["seen"] = (w.get("seen", []) + [{"price_paise": price, "store": a.get("store", ""), "on": ist_now().date().isoformat()}])[-20:]
        prof["price_watches"] = ws
        self._save_prof(ctx, prof)
        hit = price <= w["target_paise"]
        return {"product": w["product"], "price": rupees(price), "target": rupees(w["target_paise"]), "at_target": hit,
                "lowest_seen": rupees(min(s["price_paise"] for s in w["seen"]))}

    def _list_watches(self, pack, a, ctx):
        return {"watches": [{"product": w["product"], "target": rupees(w["target_paise"]),
                             "last_seen": rupees(w["seen"][-1]["price_paise"]) if w.get("seen") else ""} for w in self._prof(ctx).get("price_watches", [])]}

    # ------------------------------------------------------------------ recipe & meals
    def _ingredients_to_list(self, pack, a, ctx):
        name = str(a.get("list") or "shopping").lower()
        items = self._core_list_add(ctx, name, [str(i) for i in a["ingredients"]])
        return {"dish": a.get("dish", ""), "added": items, "list": name,
                "next": "Say 'kirana se mangwa do' and I'll order these from your shop."}

    def _save_meal_plan(self, pack, a, ctx):
        prof = self._prof(ctx)
        prof["meal_plan"] = {"plan": a["plan"], "saved_on": ist_now().date().isoformat()}
        self._save_prof(ctx, prof)
        added = self._core_list_add(ctx, "shopping", [str(g) for g in a.get("groceries") or []])
        return {"saved": True, "days": list(a["plan"].keys()) if isinstance(a["plan"], dict) else [], "groceries_added": added}

    def _get_meal_plan(self, pack, a, ctx):
        return self._prof(ctx).get("meal_plan") or {"plan": None, "message": "No meal plan saved yet."}

    # ------------------------------------------------------------------ study & trip
    def _make_study_plan(self, pack, a, ctx):
        exam_day = self._date(a["exam_date"], "exam_date")
        today = ist_now().date()
        days = (exam_day - today).days - 1
        subjects = [str(s) for s in a["subjects"] if str(s).strip()]
        if days < 1:
            raise ToolError("The exam is too close for a plan — focus on revision today.")
        if not subjects:
            raise ToolError("Which subjects?")
        rev = max(1, round(days * 0.2))
        study = days - rev
        plan = []
        for i in range(days):
            d = today + dt.timedelta(days=i + 1)
            if i < study:
                topic = subjects[i % len(subjects)]
            else:
                topic = "Revision: " + subjects[(i - study) % len(subjects)] + (" + mock test" if (i - study) % 2 else "")
            plan.append({"date": d.isoformat(), "focus": topic})
        hh, mm = 18, 0
        m = re.match(r"^(\d{1,2}):(\d{2})$", str(a.get("daily_time") or ""))
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
        first = dt.datetime.combine(today + dt.timedelta(days=1), dt.time(hh, mm), tzinfo=IST)
        ctx.session.add(Reminder(user_id=ctx.user.id, kind="reminder", text=f"Study time for {a['exam']} — check today's plan", due_at=to_utc_naive(first),
                                 repeat="daily", meta={"until": exam_day.isoformat(), "plan": plan}))
        self._remind_on(ctx, f"{a['exam']} exam tomorrow — keep admit card and ID ready", exam_day - dt.timedelta(days=1), hour=19)
        return {"exam": a["exam"], "exam_date": exam_day.isoformat(), "study_days": study, "revision_days": rev, "plan": plan[:60]}

    def _make_trip(self, pack, a, ctx):
        start = self._date(a["start_date"], "start_date")
        ttype = str(a.get("trip_type") or "family").lower()
        items = TRIP_PACK["base"] + TRIP_PACK.get(ttype, [])
        today = ist_now().date()
        reminders = []
        if (start - today).days > 7:
            self._remind_on(ctx, f"Book tickets and stay for {a['destination']} (trip on {start.strftime('%d %b')})", today + dt.timedelta(days=1))
            reminders.append("book tickets — tomorrow")
        self._remind_on(ctx, f"Pack for {a['destination']} tomorrow — checklist ready in Santosh", start - dt.timedelta(days=1), hour=18)
        reminders.append("pack — the evening before")
        prof = self._prof(ctx)
        prof["trips"] = prof.get("trips", []) + [{"destination": a["destination"], "start": start.isoformat(), "days": int(a.get("days") or 0),
                                                  "travellers": int(a.get("travellers") or 1), "type": ttype}]
        self._save_prof(ctx, prof)
        return {"destination": a["destination"], "start": start.isoformat(), "packing_list": items, "reminders": reminders,
                "next": "Ask me to find trains, buses or hotels and I'll open the right app ready to book."}

    # ------------------------------------------------------------------ trackers
    def _add_vehicle(self, pack, a, ctx):
        num = re.sub(r"\s+", "", str(a["number"]).upper())
        if not re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$|^\d{2}BH\d{4}[A-Z]{1,2}$", num):
            raise ToolError("That vehicle number doesn't look right (e.g. MH30AB1234).")
        v = {"number": num}
        for key, label in (("insurance_expiry", "Insurance"), ("puc_expiry", "PUC"), ("service_due", "Service")):
            if a.get(key):
                d = self._date(a[key], key)
                v[key] = d.isoformat()
                self._remind_on(ctx, f"{label} for {num} due on {d.strftime('%d %b %Y')}", d - dt.timedelta(days=15))
        prof = self._prof(ctx)
        prof["vehicles"] = [x for x in prof.get("vehicles", []) if x["number"] != num] + [v]
        self._save_prof(ctx, prof)
        return {"vehicle": v, "reminds": "15 days before each date"}

    def _list_vehicles(self, pack, a, ctx):
        return {"vehicles": self._prof(ctx).get("vehicles", [])}

    def _add_warranty(self, pack, a, ctx):
        bought = self._date(a["purchase_date"], "purchase_date")
        months = int(a["months"])
        y, m = bought.year + (bought.month - 1 + months) // 12, (bought.month - 1 + months) % 12 + 1
        ends = dt.date(y, m, min(bought.day, calendar.monthrange(y, m)[1]))
        w = {"product": a["product"], "purchased": bought.isoformat(), "ends": ends.isoformat(), "bill_url": a.get("bill_url", "")}
        self._remind_on(ctx, f"Warranty for {a['product']} ends on {ends.strftime('%d %b %Y')} — get any repair done now", ends - dt.timedelta(days=30))
        prof = self._prof(ctx)
        prof["warranties"] = prof.get("warranties", []) + [w]
        self._save_prof(ctx, prof)
        return {"warranty": w}

    def _list_warranties(self, pack, a, ctx):
        today = ist_now().date().isoformat()
        ws = self._prof(ctx).get("warranties", [])
        return {"active": [w for w in ws if w["ends"] >= today], "expired": [w for w in ws if w["ends"] < today]}

    def _add_subscription(self, pack, a, ctx):
        nxt = self._date(a["next_date"], "next_date")
        cycle = a.get("cycle") or "monthly"
        amt = to_paise(a["amount_rupees"])
        repeat = {"monthly": "monthly", "yearly": "yearly", "quarterly": ""}[cycle]
        self._remind_on(ctx, f"{a['name']} renews on {nxt.strftime('%d %b')} ({rupees(amt)}) — keep or cancel?", nxt - dt.timedelta(days=3),
                        repeat=repeat, meta={"subscription": a["name"]})
        prof = self._prof(ctx)
        prof["subscriptions"] = [x for x in prof.get("subscriptions", []) if x["name"].lower() != a["name"].lower()] + [
            {"name": a["name"], "amount_paise": amt, "cycle": cycle, "next": nxt.isoformat()}]
        self._save_prof(ctx, prof)
        return {"subscription": a["name"], "amount": rupees(amt), "cycle": cycle, "next": nxt.isoformat()}

    def _list_subscriptions(self, pack, a, ctx):
        subs = self._prof(ctx).get("subscriptions", [])
        per_month = sum(s["amount_paise"] / {"monthly": 1, "quarterly": 3, "yearly": 12}[s["cycle"]] for s in subs)
        return {"subscriptions": [{**s, "amount": rupees(s["amount_paise"])} for s in subs], "monthly_total": rupees(int(per_month)),
                "yearly_total": rupees(int(per_month * 12))}

    # ------------------------------------------------------------------ phone plan, power insights
    def _compare_plans(self, pack, a, ctx):
        need = float(a["data_gb_per_day"])
        calls = bool(a.get("needs_unlimited_calls", True))
        fits = []
        for p in a.get("plans") or []:
            try:
                price, days = float(p["price_rupees"]), int(p["validity_days"])
                data = float(p.get("data_gb_per_day", 0))
            except (KeyError, ValueError, TypeError):
                continue
            if data >= need and (not calls or p.get("unlimited_calls", True)) and days > 0:
                fits.append({**p, "per_day": round(price / days, 2), "per_month_30d": round(price / days * 30)})
        if not fits:
            raise ToolError("None of these plans cover your usage. Share more plans or your operator's plan list.")
        fits.sort(key=lambda p: p["per_day"])
        return {"best": fits[0], "others": fits[1:4], "rule": "Cheapest per day that covers your daily data" + (" and unlimited calls" if calls else "")}

    def _bill_insights(self, pack, a, ctx):
        txns = ctx.session.scalars(select(Transaction).where(Transaction.user_id == ctx.user.id, Transaction.kind == "bill")
                                   .order_by(Transaction.created_at)).all()
        from ..packs.registry import registry
        reg = registry()
        elec = [t for t in txns if t.provider in reg.packs and reg.get(t.provider).sub_category == "Electricity boards"]
        if not elec:
            raise ToolError("I don't have any of your bills yet. Ask me to fetch your electricity bill first.")
        series = [{"period": (t.meta or {}).get("bill", {}).get("period", t.created_at.strftime("%b %Y")), "amount": rupees(t.amount_paise),
                   "amount_paise": t.amount_paise} for t in elec[-12:]]
        out: dict[str, Any] = {"bills": series}
        if len(series) >= 2:
            a1, a2 = series[-2]["amount_paise"], series[-1]["amount_paise"]
            change = (a2 - a1) * 100 / a1 if a1 else 0
            out["change_vs_last"] = f"{change:+.0f}%"
            if change > 20:
                out["tips"] = ["Check AC/geyser hours this month", "Fridge door seal and 5-star rating matter", "Ask the board for a meter check if usage didn't change"]
        return out

    # ------------------------------------------------------------------ tax calendar
    def _tax_dates(self, a: dict[str, Any]) -> list[dict[str, str]]:
        today = ist_now().date()
        horizon = today + dt.timedelta(days=int(a.get("days") or 90))
        profiles = [str(p).lower() for p in (a.get("profiles") or ["salaried"])]
        out = []
        for prof in profiles:
            for label, mo, day in TAX_RULES.get(prof, []):
                for y in (today.year, today.year + 1):
                    d = dt.date(y, mo, day)
                    if today <= d <= horizon:
                        out.append({"what": label, "due": d.isoformat()})
        gst = str(a.get("gst") or "").lower()
        if gst in ("monthly", "qrmp"):
            d = today.replace(day=1)
            while d <= horizon:
                if gst == "monthly":
                    for label, day in (("GSTR-1 (monthly)", 11), ("GSTR-3B (monthly)", 20)):
                        due = d.replace(day=day)
                        if today <= due <= horizon:
                            out.append({"what": label, "due": due.isoformat()})
                elif d.month in (1, 4, 7, 10):
                    for label, day in (("GSTR-1 (quarterly, QRMP)", 13), ("GSTR-3B (quarterly, QRMP: 22nd or 24th by state)", 22)):
                        due = d.replace(day=day)
                        if today <= due <= horizon:
                            out.append({"what": label, "due": due.isoformat()})
                d = (d + dt.timedelta(days=32)).replace(day=1)
        return sorted(out, key=lambda x: x["due"])

    def _tax_calendar(self, pack, a, ctx):
        return {"due_dates": self._tax_dates(a), "note": "Statutory dates; the government sometimes extends them — I'll update if it does."}

    def _set_tax_reminders(self, pack, a, ctx):
        dates = self._tax_dates(a)
        for d in dates:
            due = dt.date.fromisoformat(d["due"])
            self._remind_on(ctx, f"{d['what']} due on {due.strftime('%d %b')}", due - dt.timedelta(days=5), kind="bill",
                            meta={"name": d["what"], "due_date": d["due"]})
        return {"reminders_set": len(dates), "dates": dates}

    # ------------------------------------------------------------------ form filler
    def _profile_for_form(self, pack, a, ctx):
        prof = self._prof(ctx)
        biz = prof.get("business", {})
        known = {"name": ctx.user.name, "full name": ctx.user.name, "mobile": ctx.user.phone, "phone": ctx.user.phone,
                 "city": ctx.user.city, "pincode": ctx.user.pincode, "pin code": ctx.user.pincode, "address": prof.get("address", ""),
                 "email": prof.get("email", ""), "business name": biz.get("name", ""), "gstin": biz.get("gstin", ""),
                 "state": GST_STATES.get(biz.get("state_code", ""), "")}
        filled, missing = {}, []
        for f in a["fields"]:
            v = known.get(str(f).strip().lower(), "")
            if v:
                filled[f] = v
            else:
                missing.append(f)
        return {"filled": filled, "missing": missing, "note": "ID numbers, OTPs and passwords are never stored or filled by Santosh."}

    # ------------------------------------------------------------------ safety
    def _check_message(self, pack, a, ctx):
        text = str(a["text"])
        low = text.lower()
        score, reasons = 0, []
        for pat, w, why in SCAM_RULES:
            if re.search(pat, low, re.I):
                score += w
                reasons.append(why)
        verdict = "very likely a scam" if score >= 5 else ("suspicious" if score >= 3 else ("some warning signs" if score >= 1 else "no common scam signs found"))
        out = {"verdict": verdict, "score": score, "reasons": reasons,
               "do": (["Don't click links or call numbers in it", "Never share OTP/PIN/CVV", "Report at cybercrime.gov.in or call 1930"]
                      if score >= 3 else ["Still verify on the official app or website before acting"])}
        return out

    def _sos(self, pack, a, ctx):
        contacts = ctx.session.scalars(select(Contact).where(Contact.user_id == ctx.user.id)).all()
        fam_words = ("family", "emergency", "wife", "husband", "mother", "father", "mummy", "papa", "brother", "sister", "son", "daughter")
        people = [c for c in contacts if c.phone and any(w in (c.relation or "").lower() for w in fam_words)]
        loc = ""
        if a.get("lat") is not None and a.get("lng") is not None:
            loc = f" Location: https://maps.google.com/?q={a['lat']},{a['lng']}"
        text = f"SOS from {ctx.user.name or ctx.user.phone}: {a.get('message') or 'I need help urgently.'}{loc}"
        wa = WhatsApp(ctx.settings)
        sent = []
        if wa.configured:
            for c in people:
                r = wa.send_text(c.phone, text)
                sent.append({"to": c.name, "ok": r["ok"]})
        call_now = [{"what": "All emergencies", "number": "112"}, {"what": "Ambulance", "number": "108"},
                    {"what": "Women helpline", "number": "1091"}, {"what": "Cyber fraud", "number": "1930"}]
        # Taps only: the dialer opens with the number; WhatsApp opens from the user's own app with the text filled in.
        links = [{"name": "Call 112", "url": "tel:112"}, {"name": "Ambulance 108", "url": "tel:108"}]
        if not any(x["ok"] for x in sent):
            links += [{"name": f"WhatsApp {c.name}", "url": f"https://wa.me/{re.sub(r'[^0-9]', '', c.phone)}?text={quote(text)}"}
                      for c in people]
            links.append({"name": "WhatsApp: choose contact", "url": f"https://wa.me/?text={quote(text)}"})
        return {"call_now": call_now, "alerted": sent, "message": f"Call 112 (ambulance 108) if you are in danger. {text}",
                "sos_text": text, "share_links": links,
                "note": "" if people else "Mark family contacts (relation: family/emergency) so SOS can reach them."}

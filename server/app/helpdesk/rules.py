"""Rules the IT Helpdesk Sahayak checks in code (researched 23 Oct 2026; dates and numbers are starters she can change).

- Priority = ITIL impact x urgency (P1-P4). Impact: one person / several / the whole office; urgency: low / normal / high.
  Security incidents (phishing clicked, malware, account taken over, data leak) are at least P2, P1 when money / data moved.
- SLA (clock hours, her own numbers win): P1 respond 0.5 h / fix 4 h, P2 1 h / 8 h, P3 4 h / 24 h, P4 8 h / 72 h.
- CERT-In Directions of 28 Apr 2022 (in force 27 Jun 2022), s.70B(6) IT Act: service providers, intermediaries, data
  centres, BODY CORPORATE and government bodies must report the incidents in Annexure I (incl. phishing / identity theft,
  unauthorised access, malware / ransomware, data breach / leak, social-media account takeover, attacks on payment
  systems) within 6 HOURS of noticing; logs of all ICT systems 180 days; clocks synced to NIC / NPL NTP. "Body corporate"
  in IT Act s.43A Expl. (i) includes a firm, a sole proprietorship or other association doing business; individuals and
  home computers are not covered. Report: incident@cert-in.org.in, toll free 1800-11-4949, fax 1800-11-6969.
- DPDP Rules 2025 (notified 13 Nov 2025): breach of PERSONAL DATA -> tell each affected person and the Data Protection
  Board without delay, details to the Board within 72 hours (Rule 7). In force 18 months after notification (~13 May 2027).
- Windows 10: free support ended 14 Oct 2025; consumer ESU now runs to 12 Oct 2027 (Microsoft, June 2026); Windows 7 / 8 /
  8.1 get no updates at all.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

IMPACTS = ("one", "several", "all")
URGENCIES = ("low", "normal", "high")
_MATRIX = {("all", "high"): "P1", ("all", "normal"): "P2", ("several", "high"): "P2", ("all", "low"): "P3",
           ("several", "normal"): "P3", ("one", "high"): "P3", ("several", "low"): "P4", ("one", "normal"): "P4",
           ("one", "low"): "P4"}
PRIORITY_LABEL = {"P1": "Sabse zaroori (P1)", "P2": "Zaroori (P2)", "P3": "Aam (P3)", "P4": "Halka (P4)"}
SLA_DEFAULT = {"P1": {"respond_h": 0.5, "resolve_h": 4}, "P2": {"respond_h": 1, "resolve_h": 8},
               "P3": {"respond_h": 4, "resolve_h": 24}, "P4": {"respond_h": 8, "resolve_h": 72}}

URGENT_WORDS = re.compile(r"(urgent|turant|abhi ke abhi|jaldi|asap|client baitha|meeting|deadline|aaj hi|gst filing|return file|"
                          r"salary|payroll|billing ruk|bill nahi ban|counter band|kaam ruk|sab ruk|emergency)", re.I)
ALL_WORDS = re.compile(r"(sab(ka|ke|ki)?\b|sabhi|poore office|pura office|poora office|kisi ka bhi|everyone|whole office|all pc|"
                       r"all computers|koi bhi pc|office mein kisi)", re.I)
SEVERAL_WORDS = re.compile(r"(do log|teen log|2 pc|3 pc|kai log|kuch log|kayi|several|kai pc|accounts wale|counter wale)", re.I)
DANGER_WORDS = re.compile(r"(jalne ki|jal raha|dhuan|smoke|chingari|spark|current lag|shock|burning)", re.I)

CERT_IN = {"email": "incident@cert-in.org.in", "phone": "1800-11-4949", "fax": "1800-11-6969", "hours": 6,
           "site": "https://www.cert-in.org.in"}
BODY_CORPORATE = {"company", "llp", "partnership", "proprietor", "trust", "society", "govt"}
ENTITY_LABEL = {"company": "Company (Pvt / Ltd)", "llp": "LLP", "partnership": "Partnership firm", "proprietor": "Proprietorship",
                "trust": "Trust / NGO", "society": "Society", "govt": "Sarkari daftar", "individual": "Ghar / vyakti", "": "Pata nahi"}
DPDP_FROM = date(2027, 5, 13)

# ------------------------------------------------------------------ priority + SLA


def impact_of(text: str, given: str = "") -> str:
    if given in IMPACTS:
        return given
    t = text or ""
    if ALL_WORDS.search(t):
        return "all"
    if SEVERAL_WORDS.search(t):
        return "several"
    return "one"


def urgency_of(text: str, given: str = "") -> str:
    if given in URGENCIES:
        return given
    t = text or ""
    if DANGER_WORDS.search(t) or URGENT_WORDS.search(t):
        return "high"
    return "normal"


def priority(impact: str, urgency: str, security: bool = False, money_or_data: bool = False, danger: bool = False) -> str:
    p = _MATRIX.get((impact if impact in IMPACTS else "one", urgency if urgency in URGENCIES else "normal"), "P4")
    if danger or money_or_data:
        return "P1"
    if security and p in ("P3", "P4"):
        return "P2"
    return p


def sla_for(p: str, custom: dict | None = None) -> dict:
    base = dict(SLA_DEFAULT.get(p, SLA_DEFAULT["P4"]))
    c = (custom or {}).get(p) or {}
    for k in ("respond_h", "resolve_h"):
        try:
            v = float(c.get(k))
            if 0 < v <= 24 * 30:
                base[k] = v
        except (TypeError, ValueError):
            pass
    return base


def due_times(created: datetime, p: str, custom: dict | None = None) -> tuple[datetime, datetime]:
    s = sla_for(p, custom)
    return created + timedelta(hours=s["respond_h"]), created + timedelta(hours=s["resolve_h"])


# ------------------------------------------------------------------ CERT-In / DPDP


def cert_in(entity: str, kind: str, did: dict | None = None) -> dict:
    """Does the CERT-In 6-hour rule apply to this incident here? Plain words, never legal advice."""
    did = did or {}
    reportable = kind in ("phishing", "malware", "ransomware", "account", "data_leak", "intrusion", "payment", "website")
    harmed = any(did.get(k) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")) or \
        kind in ("malware", "ransomware", "account", "data_leak", "intrusion", "website")
    if entity == "individual":
        return {"applies": False, "why": "Ghar / vyakti ke computer par CERT-In Directions lagoo nahi (sirf body corporate, service "
                                         "provider, sarkari daftar). Chahein to phir bhi report kar sakti hain.", **CERT_IN}
    if not reportable:
        return {"applies": False, "why": "Yeh CERT-In Annexure I ki suchi wala incident nahi lagta.", **CERT_IN}
    if not harmed:
        return {"applies": None, "why": "Sirf phishing mail / message aaya, kisi ne click / password / paisa nahi diya: report karna "
                                        "achha hai (phishing bhi Annexure I mein hai), par nuksaan nahi hua.", **CERT_IN}
    if entity in BODY_CORPORATE:
        return {"applies": True, "why": f"{ENTITY_LABEL.get(entity, entity)} = body corporate (IT Act s.43A mein firm / proprietorship bhi). "
                                        "Is tarah ka incident dekhne ke 6 GHANTE ke andar CERT-In ko report karna zaroori (Directions "
                                        "28-04-2022).", **CERT_IN}
    return {"applies": None, "why": "Office ka roop (company / firm / proprietorship) Niyam mein likhiye. Business ka computer ho to "
                                    "zyaadatar 6 ghante mein CERT-In ko report karna zaroori hai.", **CERT_IN}


def dpdp(personal_data: bool, today: date) -> dict | None:
    if not personal_data:
        return None
    live = today >= DPDP_FROM
    return {"live": live, "from": DPDP_FROM.isoformat(),
            "say": ("Graahakon / logon ka personal data gaya ho to DPDP Rules 2025 (Rule 7): har prabhavit vyakti ko aur Data "
                    "Protection Board ko bina deri, Board ko 72 ghante mein poori jaankari. "
                    + ("Yeh ab lagoo hai." if live else f"Yeh {DPDP_FROM.strftime('%d %b %Y')} se lagoo hoga; abhi se isi tarah karna achha."))}


def cert_in_text(org: dict, inc: dict) -> str:
    """Draft for her own email to CERT-In (she sends it from her mailbox)."""
    lines = ["To: " + CERT_IN["email"], "Subject: Cyber security incident report - " + (org.get("office_name") or "[office ka naam]"), "",
             "1. Organisation: " + (org.get("office_name") or "[office ka naam]") + f" ({ENTITY_LABEL.get(org.get('entity', ''), '[roop]')})",
             "2. Contact person: " + (org.get("contact_name") or "[naam]") + ", " + (org.get("contact_phone") or "[phone]") + ", "
             + (org.get("contact_email") or "[email]"),
             "3. Type of incident: " + (inc.get("kind_label") or inc.get("kind") or "[type]"),
             "4. Date / time noticed: " + (inc.get("detected") or "[tareekh / samay]"),
             "5. Systems affected: " + (inc.get("systems") or "[PC / email / account ka naam]"),
             "6. Description: " + (inc.get("summary") or "[kya hua]"),
             "7. Indicators (sender / links / attachment names, NOT clicked): " + (inc.get("indicators") or "[ ]"),
             "8. Actions taken: " + (inc.get("actions") or "[kya kiya]"),
             "9. Personal data involved: " + ("Yes" if inc.get("personal_data") else "No / not known"), "",
             "(Log / screenshot attached as available.)"]
    return "\n".join(lines)


# ------------------------------------------------------------------ phishing check (text is DATA, links never opened)

_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "goo.gl", "ow.ly", "shorturl.at", "tiny.cc", "rebrand.ly", "t.ly"}
_BRANDS = {"sbi": ("sbi.co.in", "onlinesbi.sbi", "sbi.bank.in"), "hdfc": ("hdfcbank.com", "hdfc.bank.in"), "icici": ("icicibank.com", "icici.bank.in"),
           "axis": ("axisbank.com", "axis.bank.in"), "kotak": ("kotak.com", "kotak.bank.in"), "paytm": ("paytm.com",), "phonepe": ("phonepe.com",),
           "amazon": ("amazon.in", "amazon.com"), "flipkart": ("flipkart.com",), "microsoft": ("microsoft.com", "live.com", "office.com", "outlook.com"),
           "google": ("google.com", "gmail.com", "youtube.com"), "apple": ("apple.com", "icloud.com"), "tally": ("tallysolutions.com",),
           "incometax": ("incometax.gov.in",), "gst": ("gst.gov.in",), "uidai": ("uidai.gov.in",), "epfo": ("epfindia.gov.in",),
           "npci": ("npci.org.in",), "jio": ("jio.com",), "airtel": ("airtel.in",), "bsnl": ("bsnl.co.in",), "whatsapp": ("whatsapp.com",)}
_URGENT = re.compile(r"(urgent|immediately|within 24 ?h|24 ghante|turant|account (will be )?(blocked|suspended|closed)|band ho jayega|"
                     r"block ho jayega|last (warning|chance)|final notice|expire[sd]? today|aaj hi)", re.I)
_BAIT = re.compile(r"(kyc|update (your )?pan|pan link|refund|tax refund|lottery|prize|inaam|you (have )?won|jeet|gift|cashback|"
                   r"reward points|job offer|work from home|part time job|electricity (bill|connection).{0,20}(cut|disconnect)|bijli kat|"
                   r"customs|parcel (held|on hold)|courier|digital arrest|cbi|police case|invoice attached|payment failed|"
                   r"verify your account|unusual (sign|login)|password (expire|reset))", re.I)
_ASK_SECRET = re.compile(r"(otp|one time password|\bpin\b|cvv|card number|password|net ?banking|anydesk|teamviewer|quick ?support|"
                         r"screen share|remote access)", re.I)
_PAY_ASK = re.compile(r"(pay|transfer|bhejo|send money|upi|gift card|amazon card|processing fee|registration fee|security deposit)", re.I)
_BAD_EXT = re.compile(r"\.(exe|scr|js|jse|vbs|bat|cmd|ps1|hta|jar|msi|iso|img|lnk|apk|html?|zip|rar|7z|docm|xlsm)\b", re.I)
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')]+", re.I)
_EMAIL_DOM = re.compile(r"@([a-z0-9.-]+\.[a-z]{2,})", re.I)


def _host(u: str) -> str:
    if not u.lower().startswith("http"):
        u = "http://" + u
    try:
        return (urlparse(u).hostname or "").lower()
    except ValueError:
        return ""


def _official(host: str, doms: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith("." + d) for d in doms)


def phish_check(text: str, sender: str = "", links: list[str] | None = None, attachments: list[str] | None = None) -> dict:
    """Red flags in a suspicious mail / SMS / WhatsApp. Only reads the words; never opens a link or attachment."""
    t = text or ""
    flags: list[dict] = []

    def add(fid: str, level: str, say: str) -> None:
        if not any(f["id"] == fid for f in flags):
            flags.append({"id": fid, "level": level, "text": say})

    urls = list(dict.fromkeys([*(links or []), *_URL.findall(t)]))[:20]
    hosts = [h for h in (_host(u) for u in urls) if h]
    sdom = ""
    m = _EMAIL_DOM.search(sender or "")
    if m:
        sdom = m.group(1).lower()
    for h in hosts:
        if re.fullmatch(r"[\d.]+", h):
            add("ip_link", "bad", f"Link mein website ka naam nahi, seedha number ({h}): asli company aisa nahi karti.")
        if h in _SHORTENERS:
            add("short_link", "warn", f"Chhota link ({h}): asli jagah chhupi hai.")
        if h.startswith("xn--") or ".xn--" in h:
            add("lookalike_letters", "bad", f"Link ke akshar nakli ({h}): dekhne mein asli jaisa.")
    for brand, doms in _BRANDS.items():
        for h in [*hosts, *([sdom] if sdom else [])]:
            if brand in h.replace("-", "") and not _official(h, doms):
                add("lookalike_" + brand, "bad", f"'{brand}' ka naam hai par pata asli nahi ({h}); asli: {', '.join(doms)}.")
    if sdom and re.search(r"(gmail|yahoo|outlook|hotmail|rediffmail)\.com$", sdom) and re.search(
            r"\b(bank|income ?tax|gst|uidai|epfo|police|court|customs|electricity|msedcl|bescom)\b", t, re.I):
        add("free_mail_official", "bad", f"Sarkari / bank ke naam se mail par bhejne wala free mail ({sdom}) se hai.")
    if _URGENT.search(t):
        add("urgency", "warn", "Darr / jaldi dikha rahe hain (block ho jayega / aaj hi): fraud ka sabse aam tareeka.")
    if _BAIT.search(t):
        add("bait", "warn", "Laalach / KYC / refund / parcel / 'digital arrest' jaisi baat: aam fraud kahani.")
    if _ASK_SECRET.search(t):
        add("asks_secret", "bad", "OTP / PIN / password / remote app maang raha hai: koi asli bank / company yeh kabhi nahi maangti.")
    if _PAY_ASK.search(t) and (_BAIT.search(t) or _URGENT.search(t)):
        add("asks_money", "bad", "Darr / inaam ke saath paise bhejne ko keh raha hai.")
    names = [str(a) for a in (attachments or [])] + [n for n in re.findall(r"[\w\-]+\.[A-Za-z0-9]{2,4}\b", t)
                                                       if not any(n in u for u in urls)]
    for name in names:
        if _BAD_EXT.search(name) and not re.search(r"\.(com|in|org|net)$", name, re.I):
            add("bad_attachment", "bad", f"Attachment '{name[-40:]}' khatarnak type ka hai: mat kholiye.")
            break
    bad = sum(1 for f in flags if f["level"] == "bad")
    warn = sum(1 for f in flags if f["level"] == "warn")
    verdict = "likely_phish" if bad >= 1 or warn >= 2 else ("suspicious" if warn == 1 else "unclear")
    say = {"likely_phish": "Yeh fraud / phishing lagta hai.", "suspicious": "Shak wala hai: savdhaan.",
           "unclear": "Saaf nishaan nahi mile, par anjaan link / attachment phir bhi mat kholiye."}[verdict]
    return {"verdict": verdict, "flags": flags, "hosts": hosts[:10], "sender_domain": sdom, "say": say}


PHISH_KIND = {"phishing": "Phishing (identity theft / spoofing)", "malware": "Malware / virus", "ransomware": "Ransomware",
              "account": "Account par kisi aur ka kabza", "data_leak": "Data leak / breach", "payment": "Payment fraud",
              "intrusion": "Bina ijazat ghusna", "website": "Website defacement", "other": "Doosra"}


def phish_actions(did: dict) -> list[str]:
    out = ["Link / attachment mat kholiye, jawab mat dijiye, aage forward mat kijiye (sirf report ke liye)."]
    if did.get("money") or did.get("gave_otp"):
        out.insert(0, "Paise gaye / OTP diya: ABHI 1930 par call kijiye aur bank ki helpline par card / UPI / net banking band karwaiye. "
                      "Phir cybercrime.gov.in par shikayat (ticket number likh lijiye).")
    if did.get("entered_password"):
        out.append("Jis account ka password bhara: saaf phone / doosre PC se turant khud password badaliye, 2-step on, 'sab devices se "
                   "sign out'. Wahi password aur kahin ho to wahan bhi badaliye.")
    if did.get("clicked") or did.get("opened_attachment") or did.get("remote_access"):
        out.append("Us PC ka net hataiye (Wi-Fi band / LAN cable nikaliye), PC band mat kijiye, antivirus full scan.")
    if did.get("remote_access"):
        out.append("AnyDesk / TeamViewer jaisa app hataiye (aapki haan ke card se), bank ko batayiye.")
    out.append("Gmail: mail kholke teen bindu > 'Report phishing'. Outlook: 'Report' > 'Report phishing'. SMS / WhatsApp / call: "
               "Chakshu (sancharsaathi.gov.in) par report.")
    return out


# ------------------------------------------------------------------ assets: OS support, age, warranty


def os_note(os_name: str, today: date) -> str:
    o = (os_name or "").lower()
    if re.search(r"windows\s*(7|8(\.1)?|xp|vista)\b", o):
        return "Is Windows ko koi security update nahi milta: net / banking ke liye khatarnak. Windows 11 ya naya PC."
    if re.search(r"windows\s*10\b", o):
        if today <= date(2027, 10, 12):
            return ("Windows 10 ka muft support 14 Oct 2025 ko khatam. ESU mein judne par updates 12 Oct 2027 tak (Settings > Windows "
                    "Update > Enroll). Windows 11 / naye PC ki yojana banaiye.")
        return "Windows 10 ke updates band. Windows 11 / naya PC."
    return ""


REPLACE_YEARS = {"pc": 5, "laptop": 4, "printer": 6, "ups": 3, "router": 4, "scanner": 6, "cctv": 6, "projector": 6, "monitor": 7,
                 "switch": 7, "server": 5, "phone": 4}

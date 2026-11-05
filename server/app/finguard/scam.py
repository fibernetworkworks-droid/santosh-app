"""Paisa Sahayak SCAM SHIELD + UPI SAFETY COACH (register #6 fraud and scam shield, #7 UPI and payment safety coach).

Pure pattern matching over text she pastes: no network (a link is NEVER opened), no model, nothing stored. It names the scam family a message
fits, quotes the words that triggered it, and says what to do. "No pattern found" is never "safe": scammers change the words, so the
answer always ends with the rules that hold whatever the message says.

THE ONE RULE (never bent, and Hoola follows it too): nobody genuine ever needs your OTP, PIN, CVV, card number, password or a screen-share
to GIVE you money. Hoola itself never asks for them either, and never moves money.

Facts about helplines and rules come from memory, not from a primary source read today: each carries `verify: true`. Re-check on the
official site (cybercrime.gov.in, your bank's card-back number, the RBI site) before relying on them.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# id -> (name, severity, [regexes], why, [what to do])
FAMILIES: dict[str, dict[str, Any]] = {
    "fake_kyc": {"name": "Fake KYC / account-block message", "sev": "high",
                 "rx": [r"kyc.{0,40}(expire|update|pending|block|suspend|verify)", r"(account|card|wallet|sim).{0,30}(block|suspend|freez|deactivat)",
                        r"(update|complete).{0,15}kyc", r"pan.{0,20}(update|link|verify).{0,20}(account|bank)"],
                 "why": "Banks do not block accounts over a link in an SMS. The link opens a copy of the bank's page that steals your login / card / OTP.",
                 "do": ["Link par click mat kijiye, aur number par call-back mat kijiye.", "Bank ki app / website ya card ke peeche likhe number se khud poochhiye.",
                        "Message ko screenshot kar ke rakhiye (saboot)."]},
    "upi_refund_collect": {"name": "UPI 'refund / reward' or collect-request trick", "sev": "high",
                           "rx": [r"(refund|cashback|reward|prize).{0,40}(upi|scan|qr|collect|request|pin)", r"(scan|qr).{0,30}(receive|get).{0,20}(money|payment|refund)",
                                  r"(enter|put|type).{0,15}(upi )?pin.{0,30}(receive|refund|credit)", r"collect request.{0,30}(accept|approve)", r"payment request.{0,30}(accept|approve)"],
                           "why": "To RECEIVE money you never enter a PIN or scan a QR. Approving a 'collect request' or entering your PIN sends money OUT.",
                           "do": ["UPI PIN sirf paise BHEJNE ke liye hota hai, paise PAANE ke liye kabhi nahi.", "Koi bhi 'collect / payment request' decline kijiye jo aapne khud shuru nahi ki.",
                                  "Paise kat gaye hon to turant bank aur 1930 par bataiye (neeche)."]},
    "otp_share": {"name": "Asking for OTP / PIN / CVV / password", "sev": "critical",
                  "rx": [r"\botp\b.{0,40}(share|send|tell|forward|batao|bhejo|do)", r"(share|send|tell|forward|batao|bhejo|give).{0,25}\b(otp|pin|cvv|password)\b",
                         r"(otp|code).{0,20}(aaya|received|mila).{0,25}(bata|share|bhej)", r"\bcvv\b", r"card number.{0,20}(send|share|batao|bhejo)"],
                  "why": "The OTP / PIN / CVV is the key to your money. Genuine banks, UPI apps and Hoola never ask for it, on a call or in a message.",
                  "do": ["Kisi ko bhi OTP / PIN / CVV mat bataiye, chahe woh bank ka naam le.", "Call kaat dijiye; bank ke number par khud call kijiye."]},
    "loan_app": {"name": "Instant-loan app / harassment", "sev": "high",
                 "rx": [r"instant loan.{0,40}(no document|without|approve)", r"loan.{0,30}(contacts|gallery|photos|sms|permission)", r"(pay|repay).{0,30}(or|else|warna).{0,30}(contacts|family|photo|police|viral)",
                        r"loan.{0,20}(apk|app download|install)", r"(processing fee|insurance|gst).{0,30}(first|advance|pehle).{0,30}loan"],
                 "why": "Unregistered loan apps take your contacts and photos and use them to threaten you. Real lenders never ask a fee BEFORE paying out, and never contact your family.",
                 "do": ["Aisi app install mat kijiye; kiya ho to uninstall karke permissions hata dijiye.", "Dhamki ya doosron ko message gaye hon to saboot ke saath cybercrime.gov.in par report kijiye.",
                        "Lender RBI-registered hai ya nahi, RBI ki website par jaanch lijiye."]},
    "investment_group": {"name": "Investment tip group / guaranteed returns", "sev": "high",
                         "rx": [r"guarantee[d]?.{0,20}(return|profit)", r"(double|2x|3x|10x).{0,25}(money|investment|paisa)", r"(daily|weekly|monthly).{0,15}(profit|income).{0,25}(\d+%|guarante)",
                                r"(vip|premium).{0,15}(group|tips|signal).{0,30}(join|telegram|whatsapp)", r"(telegram|whatsapp).{0,30}(stock|trading|ipo).{0,20}(tip|group|signal)",
                                r"(ipo|block deal|institutional).{0,25}(allot|slot|quota).{0,25}(guarante|sure)"],
                         "why": "No one can guarantee returns. Tip groups that show fake profit screens and then ask for more deposits are a common fraud. Genuine advice comes only from a SEBI-registered adviser.",
                         "do": ["Paisa mat bhejiye; advisor SEBI ki website par registered hai ya nahi dekhiye.", "Group chhod dijiye; 'withdraw ke liye aur paisa' maange to wahin ruk jaiye."]},
    "lottery_prize": {"name": "Lottery / prize / KBC / gift", "sev": "high",
                      "rx": [r"(lottery|lucky draw|kbc|you (have )?won|congratulations.{0,20}won|prize money)", r"(claim|release).{0,20}(prize|gift|parcel).{0,30}(fee|charges|tax|pay)"],
                      "why": "You cannot win a contest you did not enter, and a real prize never needs a fee in advance.",
                      "do": ["Jawab mat dijiye; koi 'fee' ya 'tax' mat bhejiye.", "Number block karke report kijiye."]},
    "digital_arrest": {"name": "Fake police / customs / courier ('digital arrest')", "sev": "critical",
                       "rx": [r"(cbi|ed|police|customs|narcotics|trai|cyber ?crime).{0,40}(arrest|case|warrant|fir|parcel|illegal)", r"(parcel|courier).{0,30}(drugs|illegal|passport|seized|customs)",
                              r"digital arrest", r"(do not|don't|mat).{0,15}(tell|inform|bataiye).{0,20}(anyone|family|kisi)", r"(video call|skype).{0,30}(statement|verification|police)",
                              r"(transfer|send).{0,25}(rbi|safe account|verification account)"],
                       "why": "No agency arrests anyone over a call or video call, and none asks you to move money to a 'safe account'. The 'stay on the line, tell nobody' pressure is the tell.",
                       "do": ["Call kaat dijiye. Kisi 'safe account' mein paisa mat bhejiye.", "Parivar ya dost ko turant bataiye; 1930 par report kijiye."]},
    "remote_access": {"name": "Asking you to install a screen-share / remote app", "sev": "critical",
                      "rx": [r"(anydesk|teamviewer|quicksupport|rustdesk|airdroid|alpemix|screen ?share)", r"(install|download).{0,25}(app|apk).{0,30}(support|help|verify|refund)"],
                      "why": "A remote app lets the caller see your screen and OTPs and move money while you watch.",
                      "do": ["App install mat kijiye; kiya ho to turant uninstall kijiye aur internet band kar dijiye.", "Bank ko call karke net-banking / UPI band karwaiye."]},
    "utility_threat": {"name": "Electricity / gas / SIM disconnection threat", "sev": "medium",
                       "rx": [r"(electricity|power|bijli|gas|sim|connection).{0,30}(disconnect|cut|band|block).{0,30}(tonight|today|9|hours|aaj)", r"(bill).{0,25}(unpaid|pending).{0,30}(call|contact|whatsapp).{0,15}\d{10}"],
                       "why": "Utilities send notices through their official channels, not an urgent mobile number to call or pay on.",
                       "do": ["Apne bill ko official app / website par check kijiye.", "Diye gaye number par call ya payment mat kijiye."]},
    "job_task": {"name": "Task / part-time job / review-to-earn", "sev": "high",
                 "rx": [r"(part[- ]?time|work from home).{0,40}(earn|income|per day|daily).{0,20}\d", r"(like|subscribe|rate|review).{0,25}(earn|paid|commission)", r"(task|order).{0,25}(deposit|prepay|advance).{0,30}(commission|profit)"],
                 "why": "Small first payouts build trust, then the 'task' asks for bigger deposits you never get back.",
                 "do": ["Koi deposit ya 'security' mat bhejiye.", "Genuine naukri kabhi pehle paise nahi maangti."]},
    "sextortion": {"name": "Video-call / photo blackmail (sextortion)", "sev": "critical",
                   "rx": [r"(video|nude|private).{0,30}(leak|viral|send to your (contacts|family)|post)", r"(pay|send).{0,25}(or|else).{0,25}(video|photo).{0,20}(viral|leak|family)"],
                   "why": "Paying does not end it. The pictures are not 'yours leaked'; the threat is the scam.",
                   "do": ["Paisa mat dijiye, baat mat badhaiye; sab block kijiye.", "Saboot rakhkar 1930 / cybercrime.gov.in par report kijiye; sharm ki baat nahi, aap peedit hain."]},
}

HEADLINE_RULES = [
    "OTP, PIN, CVV, password ya screen-share kisi ko nahi: bank ya kisi sarkari vibhag ko bhi nahi.",
    "UPI mein paise PAANE ke liye PIN ya QR scan kabhi nahi lagta.",
    "Jaldi (aaj hi / abhi / 30 minute) ka dabaav scam ki nishani hai: ruk kar kisi apne se poochhiye.",
    "Link par click karne ke bajay app / website khud kholiye ya card ke peeche ka number lagaiye.",
]

# verify:true on all of these: stated from memory, to be re-checked on the primary page
FACTS = [
    {"id": "helpline_1930", "text": "National cyber-crime helpline 1930 aur portal cybercrime.gov.in par paise ki dhokhadhadi turant report kijiye: jitni jaldi, utni rok/wapsi ki umeed.", "verify": True, "source": "I4C / MHA cybercrime portal (check current number)"},
    {"id": "bank_first", "text": "Bank ko FAURAN (card / UPI block) batayiye: card ke peeche ka ya bank ki official app ka number. Likhit shikayat ki receipt rakhiye.", "verify": True, "source": "Bank's own customer-care channel"},
    {"id": "report_window", "text": "Anadhikrit transaction ki report jitni jaldi ho (RBI ke grahak-suraksha niyam mein pehle 3 kaam ke din ka ullekh hai) utna aapka nuksan kam rehne ka niyam: apne bank ki policy dekhiye.", "verify": True, "source": "RBI customer-protection circular on unauthorised electronic transactions, Jul 2017 (verify current text)"},
    {"id": "evidence", "text": "Saboot: screenshot, call number, transaction ID / UTR, tareekh-samay, jis account se kata. Kuch delete mat kijiye.", "verify": False, "source": "common practice"},
]

SECRET_ASK = re.compile(r"\b(otp|pin|cvv|password|passcode)\b", re.I)
URGENCY = re.compile(r"(urgent|immediately|within \d+ (hour|min)|last chance|abhi|turant|aaj hi|tonight|expire[sd]? (today|soon)|final (notice|warning))", re.I)
URL_RX = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+|\b[a-z0-9\-]+(?:\.[a-z0-9\-]+)+/[^\s]*", re.I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy", "is.gd", "goo.gl", "shorturl.at", "tiny.cc", "ow.ly", "wa.me"}
BAD_TLDS = {"xyz", "top", "click", "icu", "buzz", "live", "shop", "site", "online", "vip", "work", "loan", "monster", "cfd", "sbs"}
BRAND_WORDS = ("sbi", "hdfc", "icici", "axis", "kotak", "pnb", "paytm", "phonepe", "gpay", "googlepay", "npci", "upi", "bhim", "kyc", "irctc", "uidai", "aadhaar", "incometax", "epfo", "bank")
SECOND_LEVEL = {"co", "com", "org", "net", "gov", "nic", "ac", "edu", "in"}


def _registrable(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def analyse_url(url: str) -> dict[str, Any]:
    """Looks at the TEXT of a link only; never opens it. Heuristics, labelled."""
    raw = url.strip()
    u = urlparse(raw if re.match(r"^[a-z]+://", raw, re.I) else "http://" + raw)
    host = (u.hostname or "").lower()
    flags = []

    def add(kind: str, text: str) -> None:
        flags.append({"kind": kind, "text": text})
    if not host:
        return {"url": raw[:200], "host": "", "flags": [{"kind": "measured", "text": "Link samajh nahi aaya."}], "verdict": "unclear"}
    reg = _registrable(host)
    labels = host.split(".")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        add("measured", "Link naam ki jagah seedha IP address hai.")
    if "xn--" in host:
        add("measured", "Naam mein 'xn--' hai: dikhne mein asli jaisa nakli (lookalike) akshar ho sakte hain.")
    if host in SHORTENERS or reg in SHORTENERS:
        add("measured", "Chhota (shortener) link: asli pata chhupa hota hai.")
    if "@" in raw.split("//", 1)[-1].split("/", 1)[0]:
        add("measured", "Link mein '@' hai: '@' ke pehle ka hissa jhootha naam hota hai, asli site baad wali hai.")
    if raw.lower().split("?")[0].endswith(".apk"):
        add("measured", "Link seedha .apk (app file) hai: Play Store ke bahar se app install mat kijiye.")
    if u.scheme == "http":
        add("heuristic", "https nahi hai (jaanch ka sirf ek chhota ishara, safe hone ka saboot nahi).")
    if len(labels) > 4:
        add("heuristic", "Naam mein bahut saare hisse (subdomain) hain: aksar asli naam peeche chhupane ke liye.")
    if host.count("-") >= 3:
        add("heuristic", "Naam mein bahut saare '-' hain.")
    if labels[-1] in BAD_TLDS:
        add("heuristic", f"'.{labels[-1]}' aise endings ka dhokhe mein bahut istemaal hota hai (sirf ek ishara).")
    sub = host[: -len(reg)] if host.endswith(reg) else host
    brand = next((b for b in BRAND_WORDS if b in sub or (b in reg.split(".")[0] and reg.split(".")[0] != b and b not in ("bank", "upi"))), None)
    if brand:
        add("measured", f"Link mein '{brand}' naam dikhta hai par asli (registered) site '{reg}' hai: yeh {brand} ki apni site nahi lagti.")
    verdict = "high-risk" if any(f["kind"] == "measured" for f in flags) else ("suspicious" if flags else "no-flag")
    return {"url": raw[:200], "host": host, "site": reg, "flags": flags, "verdict": verdict,
            "note": "Link kholne ke bajay website khud type kijiye. 'no-flag' ka matlab safe nahi: sirf yeh ki shabdon se kuch pakda nahi gaya."}


def check(text: str, sender: str = "") -> dict[str, Any]:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) < 6:
        raise ValueError("Message / call ki baat paste kijiye.")
    hits = []
    for fid, f in FAMILIES.items():
        trig = []
        for rx in f["rx"]:
            m = re.search(rx, t, re.I)
            if m:
                trig.append(m.group(0)[:80])
        if trig:
            hits.append({"id": fid, "name": f["name"], "severity": f["sev"], "triggers": trig[:3], "why": f["why"], "do": f["do"]})
    asks = sorted({m.group(1).lower() for m in SECRET_ASK.finditer(t)})
    links = [analyse_url(m.group(0).rstrip(".,)")) for m in URL_RX.finditer(t)][:5]
    urgent = bool(URGENCY.search(t))
    order = {"critical": 3, "high": 2, "medium": 1}
    worst = max((order[h["severity"]] for h in hits), default=0)
    if any(l["verdict"] == "high-risk" for l in links):
        worst = max(worst, 2)
    verdict = ("critical-pattern" if worst == 3 else "high-risk-pattern" if worst == 2 else "suspicious" if (hits or links and any(l["flags"] for l in links) or urgent and asks) else "no-known-pattern")
    do = []
    for h in hits:
        for d in h["do"]:
            if d not in do:
                do.append(d)
    return {"verdict": verdict, "families": hits, "secrets_mentioned": asks, "pressure_words": urgent, "links": links, "sender": str(sender or "")[:40],
            "what_to_do": do[:6], "always": HEADLINE_RULES, "facts": FACTS,
            "facts_note": "Helpline aur niyam yaad se likhe hain (verify: true): primary site par dobara dekh lijiye.",
            "note": ("'no-known-pattern' ka matlab safe nahi: thagi ke shabd badalte rehte hain. " if verdict == "no-known-pattern" else "") +
                    "Hoola kabhi aapka OTP / PIN nahi maangta aur kabhi paise nahi bhejta."}


UPI_RULES = {
    "collect_request": "Aapne jis ko paise maange nahi, unki 'collect / payment request' DECLINE kijiye. Request approve karne par paise aapke khate se JAATE hain.",
    "qr_to_receive": "Paise PAANE ke liye QR scan ya PIN dalna kabhi nahi padta. Jo bole 'scan karo, paise aayenge' woh thag hai.",
    "refund": "Asli refund seedha aapke khate mein aata hai (ya app ke andar). Koi 'refund ke liye PIN daaliye / link kholiye' bole to mat kijiye.",
    "wrong_transfer": "Galat jagah chale gaye paise: turant app mein 'dispute / complaint' kijiye aur bank ko likhiye; transaction ID (UTR) sambhaal ke rakhiye. Receiver ko call par 'wapas kar do' kehna thik hai par woh bhejne ke liye majboor nahi.",
    "screen_share": "UPI / banking app chalate waqt koi bhi screen-share ya remote app mat kholiye.",
    "autopay_mandate": "AutoPay / mandate sirf wohi chalu rakhiye jo aapne khud banaya. App ke 'mandates' hisse mein jaakar baaki band kijiye.",
    "limit": "Apne UPI / bank ka daily limit khud neeche rakhiye (jitna zaroori ho): thagi hone par nuksan ki seema ghat jaati hai.",
}


def upi_coach(scenario: str = "") -> dict[str, Any]:
    key = re.sub(r"[^a-z_]", "", str(scenario or "").lower().replace(" ", "_"))
    one = UPI_RULES.get(key)
    return {"scenario": key if one else "", "answer": one or "", "all_rules": UPI_RULES if not one else {},
            "dispute_note": "Paise kat gaye hon: (1) app mein dispute, (2) bank ko call aur likhit, (3) 1930 / cybercrime.gov.in. Samay-seema aur muavze ke niyam bank / NPCI ke hain: unki site par dekhiye (verify).",
            "facts": FACTS, "always": HEADLINE_RULES[:2]}

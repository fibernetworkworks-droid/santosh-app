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
                 "do": ["Do not click the link, and do not call back the number.", "Check yourself through the bank's app / website or the number on the back of your card.",
                        "Keep a screenshot of the message (evidence)."]},
    "upi_refund_collect": {"name": "UPI 'refund / reward' or collect-request trick", "sev": "high",
                           "rx": [r"(refund|cashback|reward|prize).{0,40}(upi|scan|qr|collect|request|pin)", r"(scan|qr).{0,30}(receive|get).{0,20}(money|payment|refund)",
                                  r"(enter|put|type).{0,15}(upi )?pin.{0,30}(receive|refund|credit)", r"collect request.{0,30}(accept|approve)", r"payment request.{0,30}(accept|approve)"],
                           "why": "To RECEIVE money you never enter a PIN or scan a QR. Approving a 'collect request' or entering your PIN sends money OUT.",
                           "do": ["A UPI PIN is only for SENDING money, never for RECEIVING it.", "Decline any 'collect / payment request' that you did not start yourself.",
                                  "If money has been deducted, tell your bank and 1930 at once (below)."]},
    "otp_share": {"name": "Asking for OTP / PIN / CVV / password", "sev": "critical",
                  "rx": [r"\botp\b.{0,40}(share|send|tell|forward|batao|bhejo|do)", r"(share|send|tell|forward|batao|bhejo|give).{0,25}\b(otp|pin|cvv|password)\b",
                         r"(otp|code).{0,20}(aaya|received|mila).{0,25}(bata|share|bhej)", r"\bcvv\b", r"card number.{0,20}(send|share|batao|bhejo)"],
                  "why": "The OTP / PIN / CVV is the key to your money. Genuine banks, UPI apps and Hoola never ask for it, on a call or in a message.",
                  "do": ["Never tell anyone your OTP / PIN / CVV, even if they use the bank's name.", "Cut the call; call the bank yourself on its own number."]},
    "loan_app": {"name": "Instant-loan app / harassment", "sev": "high",
                 "rx": [r"instant loan.{0,40}(no document|without|approve)", r"loan.{0,30}(contacts|gallery|photos|sms|permission)", r"(pay|repay).{0,30}(or|else|warna).{0,30}(contacts|family|photo|police|viral)",
                        r"loan.{0,20}(apk|app download|install)", r"(processing fee|insurance|gst).{0,30}(first|advance|pehle).{0,30}loan"],
                 "why": "Unregistered loan apps take your contacts and photos and use them to threaten you. Real lenders never ask a fee BEFORE paying out, and never contact your family.",
                 "do": ["Do not install such an app; if you did, uninstall it and remove its permissions.", "If threats were made or messages went to others, report on cybercrime.gov.in with the evidence.",
                        "Check on the RBI website whether the lender is RBI-registered."]},
    "investment_group": {"name": "Investment tip group / guaranteed returns", "sev": "high",
                         "rx": [r"guarantee[d]?.{0,20}(return|profit)", r"(double|2x|3x|10x).{0,25}(money|investment|paisa)", r"(daily|weekly|monthly).{0,15}(profit|income).{0,25}(\d+%|guarante)",
                                r"(vip|premium).{0,15}(group|tips|signal).{0,30}(join|telegram|whatsapp)", r"(telegram|whatsapp).{0,30}(stock|trading|ipo).{0,20}(tip|group|signal)",
                                r"(ipo|block deal|institutional).{0,25}(allot|slot|quota).{0,25}(guarante|sure)"],
                         "why": "No one can guarantee returns. Tip groups that show fake profit screens and then ask for more deposits are a common fraud. Genuine advice comes only from a SEBI-registered adviser.",
                         "do": ["Do not send money; check on the SEBI website whether the adviser is registered.", "Leave the group; if they ask for 'more money to withdraw', stop right there."]},
    "lottery_prize": {"name": "Lottery / prize / KBC / gift", "sev": "high",
                      "rx": [r"(lottery|lucky draw|kbc|you (have )?won|congratulations.{0,20}won|prize money)", r"(claim|release).{0,20}(prize|gift|parcel).{0,30}(fee|charges|tax|pay)"],
                      "why": "You cannot win a contest you did not enter, and a real prize never needs a fee in advance.",
                      "do": ["Do not reply; do not send any 'fee' or 'tax'.", "Block the number and report it."]},
    "digital_arrest": {"name": "Fake police / customs / courier ('digital arrest')", "sev": "critical",
                       "rx": [r"(cbi|ed|police|customs|narcotics|trai|cyber ?crime).{0,40}(arrest|case|warrant|fir|parcel|illegal)", r"(parcel|courier).{0,30}(drugs|illegal|passport|seized|customs)",
                              r"digital arrest", r"(do not|don't|mat).{0,15}(tell|inform|bataiye).{0,20}(anyone|family|kisi)", r"(video call|skype).{0,30}(statement|verification|police)",
                              r"(transfer|send).{0,25}(rbi|safe account|verification account)"],
                       "why": "No agency arrests anyone over a call or video call, and none asks you to move money to a 'safe account'. The 'stay on the line, tell nobody' pressure is the tell.",
                       "do": ["Cut the call. Do not send money to any 'safe account'.", "Tell family or a friend at once; report to 1930."]},
    "remote_access": {"name": "Asking you to install a screen-share / remote app", "sev": "critical",
                      "rx": [r"(anydesk|teamviewer|quicksupport|rustdesk|airdroid|alpemix|screen ?share)", r"(install|download).{0,25}(app|apk).{0,30}(support|help|verify|refund)"],
                      "why": "A remote app lets the caller see your screen and OTPs and move money while you watch.",
                      "do": ["Do not install the app; if you did, uninstall it at once and switch off the internet.", "Call the bank and have net-banking / UPI blocked."]},
    "utility_threat": {"name": "Electricity / gas / SIM disconnection threat", "sev": "medium",
                       "rx": [r"(electricity|power|bijli|gas|sim|connection).{0,30}(disconnect|cut|band|block).{0,30}(tonight|today|9|hours|aaj)", r"(bill).{0,25}(unpaid|pending).{0,30}(call|contact|whatsapp).{0,15}\d{10}"],
                       "why": "Utilities send notices through their official channels, not an urgent mobile number to call or pay on.",
                       "do": ["Check your bill on the official app / website.", "Do not call or pay on the number given."]},
    "job_task": {"name": "Task / part-time job / review-to-earn", "sev": "high",
                 "rx": [r"(part[- ]?time|work from home).{0,40}(earn|income|per day|daily).{0,20}\d", r"(like|subscribe|rate|review).{0,25}(earn|paid|commission)", r"(task|order).{0,25}(deposit|prepay|advance).{0,30}(commission|profit)"],
                 "why": "Small first payouts build trust, then the 'task' asks for bigger deposits you never get back.",
                 "do": ["Do not send any deposit or 'security'.", "A genuine job never asks for money first."]},
    "sextortion": {"name": "Video-call / photo blackmail (sextortion)", "sev": "critical",
                   "rx": [r"(video|nude|private).{0,30}(leak|viral|send to your (contacts|family)|post)", r"(pay|send).{0,25}(or|else).{0,25}(video|photo).{0,20}(viral|leak|family)"],
                   "why": "Paying does not end it. The pictures are not 'yours leaked'; the threat is the scam.",
                   "do": ["Do not pay and do not continue the conversation; block everything.", "Keep the evidence and report to 1930 / cybercrime.gov.in; there is no shame in it, you are the victim."]},
}

HEADLINE_RULES = [
    "OTP, PIN, CVV, password or screen-share to no one: not even to a bank or a government office.",
    "In UPI, receiving money never needs a PIN or a QR scan.",
    "Pressure to hurry (today / now / 30 minutes) is a sign of a scam: stop and ask someone you trust.",
    "Instead of clicking the link, open the app / website yourself or call the number on the back of your card.",
]

# verify:true on all of these: stated from memory, to be re-checked on the primary page
FACTS = [
    {"id": "helpline_1930", "text": "Report money fraud at once to the National cyber-crime helpline 1930 and the portal cybercrime.gov.in: the sooner, the better the chance of a hold / refund.", "verify": True, "source": "I4C / MHA cybercrime portal (check current number)"},
    {"id": "bank_first", "text": "Tell the bank IMMEDIATELY (block card / UPI): use the number on the back of the card or in the bank's official app. Keep the receipt of a written complaint.", "verify": True, "source": "Bank's own customer-care channel"},
    {"id": "report_window", "text": "The sooner an unauthorised transaction is reported (the RBI customer-protection rules mention the first 3 working days), the less of the loss falls on you: see your bank's policy.", "verify": True, "source": "RBI customer-protection circular on unauthorised electronic transactions, Jul 2017 (verify current text)"},
    {"id": "evidence", "text": "Evidence: screenshot, call number, transaction ID / UTR, date and time, the account it was deducted from. Do not delete anything.", "verify": False, "source": "common practice"},
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
        return {"url": raw[:200], "host": "", "flags": [{"kind": "measured", "text": "The link was not understood."}], "verdict": "unclear"}
    reg = _registrable(host)
    labels = host.split(".")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        add("measured", "The link uses a raw IP address instead of a name.")
    if "xn--" in host:
        add("measured", "The name has 'xn--': it may use look-alike letters that seem genuine.")
    if host in SHORTENERS or reg in SHORTENERS:
        add("measured", "A short (shortener) link: the real address is hidden.")
    if "@" in raw.split("//", 1)[-1].split("/", 1)[0]:
        add("measured", "The link has '@': the part before '@' is a fake name; the real site is the part after it.")
    if raw.lower().split("?")[0].endswith(".apk"):
        add("measured", "The link goes straight to an .apk (app file): do not install apps from outside the Play Store.")
    if u.scheme == "http":
        add("heuristic", "It is not https (only a small hint, not proof of safety).")
    if len(labels) > 4:
        add("heuristic", "The name has many parts (subdomains): often used to hide the real name at the back.")
    if host.count("-") >= 3:
        add("heuristic", "The name has many '-' characters.")
    if labels[-1] in BAD_TLDS:
        add("heuristic", f"The ending '.{labels[-1]}' is often used in fraud (only a hint).")
    sub = host[: -len(reg)] if host.endswith(reg) else host
    brand = next((b for b in BRAND_WORDS if b in sub or (b in reg.split(".")[0] and reg.split(".")[0] != b and b not in ("bank", "upi"))), None)
    if brand:
        add("measured", f"The link shows the name '{brand}' but the real (registered) site is '{reg}': it does not look like {brand}'s own site.")
    verdict = "high-risk" if any(f["kind"] == "measured" for f in flags) else ("suspicious" if flags else "no-flag")
    return {"url": raw[:200], "host": host, "site": reg, "flags": flags, "verdict": verdict,
            "note": "Instead of opening the link, type the website yourself. 'no-flag' does not mean safe: only that nothing was caught from the words."}


def check(text: str, sender: str = "") -> dict[str, Any]:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) < 6:
        raise ValueError("Paste the message / what was said on the call.")
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
            "facts_note": "The helplines and rules are written from memory (verify: true): check them again on the primary site.",
            "note": ("'no-known-pattern' does not mean safe: scam wording keeps changing. " if verdict == "no-known-pattern" else "") +
                    "Hoola never asks for your OTP / PIN and never sends money."}


UPI_RULES = {
    "collect_request": "DECLINE a 'collect / payment request' from anyone you did not ask for money. Approving a request sends money OUT of your account.",
    "qr_to_receive": "To RECEIVE money you never scan a QR or enter a PIN. Anyone who says 'scan this and money will come' is a fraudster.",
    "refund": "A real refund comes straight into your account (or inside the app). If anyone says 'enter your PIN / open this link for the refund', do not.",
    "wrong_transfer": "Money sent to the wrong place: raise a 'dispute / complaint' in the app at once and write to the bank; keep the transaction ID (UTR). You may ask the receiver to send it back, but they are not obliged to.",
    "screen_share": "Never keep a screen-share or remote app open while using a UPI / banking app.",
    "autopay_mandate": "Keep only the AutoPay / mandates you made yourself. Go to the 'mandates' section of the app and stop the rest.",
    "limit": "Keep your UPI / bank daily limit low yourself (only as high as you need): if fraud happens, the loss is capped.",
}


def upi_coach(scenario: str = "") -> dict[str, Any]:
    key = re.sub(r"[^a-z_]", "", str(scenario or "").lower().replace(" ", "_"))
    one = UPI_RULES.get(key)
    return {"scenario": key if one else "", "answer": one or "", "all_rules": UPI_RULES if not one else {},
            "dispute_note": "If money has been deducted: (1) dispute in the app, (2) call and write to the bank, (3) 1930 / cybercrime.gov.in. Time limits and compensation rules are the bank's / NPCI's: check their site (verify).",
            "facts": FACTS, "always": HEADLINE_RULES[:2]}

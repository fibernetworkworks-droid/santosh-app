"""QA Sahayak rules: test types, ISTQB-style test design (equivalence partitions + 2-value boundaries for form fields),
bug severity, de-duplication, release readiness, accessibility standards by who the site is for, the Android preview checklist,
and the guards (her own hosts only, never payments, never a real password).

Sources (checked 23 Oct 2026):
- ISTQB CTFL v4.0 syllabus ch. 4 (equivalence partitioning, boundary value analysis 2-value / 3-value, decision tables,
  state transitions, checklist-based and exploratory testing); ISTQB "Boundary Value Analysis" white paper (Oct 2025).
- W3C WCAG 2.2 (Recommendation 5 Oct 2023) = ISO/IEC 40500:2025 (W3C news, Oct 2025); new in 2.2: 2.4.11 Focus Not Obscured,
  2.5.7 Dragging, 2.5.8 Target Size (Minimum) 24x24 CSS px, 3.2.6 Consistent Help, 3.3.7 Redundant Entry, 3.3.8 Accessible
  Authentication. 1.4.10 Reflow = no sideways scroll at 320 CSS px.
- India: RPwD Act 2016 s.40 / s.46 + RPwD Rules 2017 Rule 15 (GIGW for websites); Supreme Court, Rajive Raturi v Union of
  India (8 Nov 2024): Rule 15(1) only recommendatory -> Union told to frame mandatory standards in 3 months (scconline.com,
  12 Nov 2024); GIGW 3.0 (MeitY / NIC; websites AND apps, WCAG 2.1 AA based, 88 mandatory checkpoints - digit.in 29 Aug 2025);
  IS 17802:2021 (BIS, ICT accessibility); SEBI digital accessibility circular 31 Jul 2025, revised 29 Aug 2025: regulated
  entities' sites / apps to IS 17802 + WCAG 2.1+ / GIGW 3.0, IAAP-certified auditor, audit by 30 Apr 2026, fixes by 31 Jul 2026,
  annual audit (deque.com blog).
- Google Play Console pre-launch report: runs on real devices when an APK / AAB is uploaded to a testing track; stability
  (crashes / ANRs), performance, accessibility, Android compatibility, screenshots; Android 9+ devices
  (support.google.com/googleplay/android-developer/answer/9842757). Material / Android touch target 48 x 48 dp.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from typing import Any

TYPES = ("functional", "ui", "accessibility", "mobile", "negative", "security", "performance", "usability")
TYPE_LABEL = {"functional": "Kaam", "ui": "Dikhawat", "accessibility": "Sab ke liye (a11y)", "mobile": "Mobile", "negative": "Galat input",
              "security": "Suraksha (basic)", "performance": "Raftaar", "usability": "Aasaani"}
TECHNIQUES = ("smoke", "requirement", "ep", "bva", "checklist", "exploratory", "regression", "navigation")
PRIORITIES = ("P1", "P2", "P3", "P4")
SEVERITIES = ("critical", "major", "minor", "trivial")
SEV_LABEL = {"critical": "Bahut gambhir", "major": "Gambhir", "minor": "Chhota", "trivial": "Mamuli"}
BUG_STATUS = ("open", "fixed", "verified", "reopened", "wont_fix", "duplicate", "closed")
BUG_LABEL = {"open": "Khula", "fixed": "Theek kiya (jaanch baaki)", "verified": "Jaanch mein sahi", "reopened": "Phir se khula",
             "wont_fix": "Nahi badlenge", "duplicate": "Doosre jaisa", "closed": "Band"}
OPEN_BUGS = ("open", "reopened", "fixed")
SECTORS = ("general", "govt", "securities", "bank", "health", "edu")

STANDARDS = {
    "general": "WCAG 2.2 AA (= ISO/IEC 40500:2025) achha abhyaas hai; RPwD Act 2016 sab ke liye pahunch ki baat karta hai.",
    "govt": "Sarkari / sarkar se jude site-app: GIGW 3.0 (WCAG 2.1 AA aadhar, 88 zaroori checkpoints) + IS 17802; RPwD Rule 15.",
    "securities": "SEBI circular (31 Jul 2025, 29 Aug 2025 badla): IS 17802 + WCAG 2.1+ / GIGW 3.0, IAAP auditor, saalana audit.",
    "bank": "Bank / NBFC: RPwD + IS 17802 / WCAG 2.1 AA ko maanak maaniye (regulator ka apna circular dekh lijiye).",
    "health": "Health / hospital: WCAG 2.2 AA; sarkari yojana se juda ho to GIGW 3.0.",
    "edu": "School / college: WCAG 2.2 AA; sarkari sanstha ho to GIGW 3.0.",
}

PAY_HOSTS = ("razorpay.com", "paytm.com", "paytm.in", "phonepe.com", "payu.in", "payumoney.com", "cashfree.com", "stripe.com",
             "ccavenue.com", "billdesk.com", "instamojo.com", "juspay.in", "paypal.com", "easebuzz.in")
SECRET_WORDS = re.compile(r"\b(otp|cvv|cvc|upi ?pin|atm ?pin|card ?number|card no|expiry|net ?banking|m-?pin)\b", re.I)

APK_CHECKLIST = [
    ("install", "Phone par install karo (purana version ho to uske upar)", "Install ho jaaye, purana data bana rahe", "P1", "functional"),
    ("open", "App kholo (internet chalu)", "Splash ke baad pehli screen 3 sec mein, crash nahi", "P1", "functional"),
    ("consent", "Pehli baar: consent screen par tick ke bina Aage dabao", "Aage tab tak band rahe jab tak tick na ho", "P1", "functional"),
    ("back", "Har screen par phone ka Back dabao", "Pichli screen aaye; home par app band ho, crash nahi", "P2", "functional"),
    ("rotate", "Har badi screen par phone ghumao (landscape)", "Kuch kate nahi, data na jaaye", "P3", "ui"),
    ("dark", "Phone ko Dark mode mein karo, app kholo", "Sab text padha jaaye", "P3", "ui"),
    ("font", "Settings > Font size sabse bada, app kholo", "Text kate nahi, button dabe", "P2", "accessibility"),
    ("talkback", "TalkBack chalu karke har button chhuo", "Har button / photo ka naam bola jaaye", "P2", "accessibility"),
    ("touch", "Chhote icons / buttons dabao", "Har tap target kam se kam 48 dp, galat cheez na dabe", "P2", "accessibility"),
    ("offline", "Internet band karke app kholo", "Saaf message, crash nahi; internet aate hi theek", "P2", "negative"),
    ("notify", "Notification ki ijazat 'Nahi' karo", "App chale, baad mein settings se de saken", "P3", "functional"),
    ("privacy", "Privacy policy aur Delete account screen kholo", "Dono khulein, grievance officer ka naam / email ho", "P1", "functional"),
    ("low_end", "Sasta / purana phone (2-3 GB RAM) par 5 min chalao", "Atke nahi, garam na ho", "P3", "performance"),
    ("prelaunch", "Play Console > Internal testing par AAB daalo, pre-launch report dekho", "Koi crash / ANR nahi; accessibility warning padh li", "P1", "performance"),
]


def priority_ok(p: str) -> str:
    p = (p or "").upper().strip()
    return p if p in PRIORITIES else "P3"


def type_ok(t: str) -> str:
    t = (t or "").lower().strip().replace("-", "_")
    t = {"a11y": "accessibility", "security_basic": "security", "visual": "ui", "responsive": "mobile"}.get(t, t)
    return t if t in TYPES else "functional"


def severity(case_type: str, priority: str, govt_facing: bool = False, console_only: bool = False) -> str:
    if console_only:
        return "minor"
    p = priority_ok(priority)
    base = {"P1": "critical", "P2": "major", "P3": "minor", "P4": "trivial"}[p]
    if case_type == "security":
        return "critical" if p in ("P1", "P2") else "major"
    if case_type == "accessibility":
        return "critical" if (govt_facing and p == "P1") else ("major" if p in ("P1", "P2") or govt_facing else base)
    return base


def norm_message(m: str) -> str:
    m = (m or "").lower()
    m = re.sub(r"https?://\S+", "<url>", m)
    m = re.sub(r"\d+(\.\d+)?", "#", m)
    return re.sub(r"\s+", " ", m).strip()[:200]


def fingerprint(target_id: str, case_id: str, step_index: int, message: str) -> str:
    return hashlib.sha256(f"{target_id}|{case_id}|{step_index}|{norm_message(message)}".encode()).hexdigest()[:32]


# ---------------------------------------------------------------- test design for one form field (EP + 2-value BVA)
def field_cases(f: dict[str, Any]) -> list[dict[str, Any]]:
    """Partitions for a form field: [{label, value, valid, technique}]. Uses only what the page itself declares
    (type, required, min / max, minlength / maxlength, pattern), so nothing is guessed."""
    out: list[dict[str, Any]] = []
    t = (f.get("type") or "text").lower()
    if f.get("required"):
        out.append({"label": "khaali", "value": "", "valid": False, "technique": "ep"})
    if t == "email":
        out += [{"label": "galat email (bina @)", "value": "ramesh.example.com", "valid": False, "technique": "ep"},
                {"label": "sahi email", "value": "test.user@example.com", "valid": True, "technique": "ep"}]
    if t == "number":
        lo, hi = _num(f.get("min")), _num(f.get("max"))
        if lo is not None:
            out += [{"label": f"seema se neeche ({lo - 1:g})", "value": f"{lo - 1:g}", "valid": False, "technique": "bva"},
                    {"label": f"seema par ({lo:g})", "value": f"{lo:g}", "valid": True, "technique": "bva"}]
        if hi is not None:
            out += [{"label": f"seema par ({hi:g})", "value": f"{hi:g}", "valid": True, "technique": "bva"},
                    {"label": f"seema se upar ({hi + 1:g})", "value": f"{hi + 1:g}", "valid": False, "technique": "bva"}]
    mn = _num(f.get("minlength"))
    if mn and mn > 1 and t not in ("number", "email"):
        out += [{"label": f"{int(mn) - 1} akshar (kam)", "value": "a" * (int(mn) - 1), "valid": False, "technique": "bva"},
                {"label": f"{int(mn)} akshar", "value": "a" * int(mn), "valid": True, "technique": "bva"}]
    if f.get("pattern") and t in ("tel", "text") and re.search(r"\\d|\[0-9\]", f["pattern"]):
        out.append({"label": "ank ki jagah akshar", "value": "abcd", "valid": False, "technique": "ep"})
    return out[:6]


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- hosts
def host_problem(host: str) -> str:
    host = (host or "").lower().strip(".")
    if not host or "." not in host:
        return "Poora website address chahiye (jaise https://meri-dukaan.in)."
    if host in ("localhost",) or host.endswith((".local", ".internal", ".lan", ".localhost")):
        return "Local / andar ke address par Hoola test nahi karta."
    try:
        ipaddress.ip_address(host)
        return "IP address nahi, domain naam dijiye (ownership domain se pakki hoti hai)."
    except ValueError:
        pass
    return ""


def pay_host(host: str) -> bool:
    host = (host or "").lower()
    return any(host == p or host.endswith("." + p) for p in PAY_HOSTS)


# ---------------------------------------------------------------- release readiness
def readiness(cases: list[dict[str, Any]], bugs: list[dict[str, Any]], kind: str = "url", govt_facing: bool = False,
              stale_days: int = 7) -> dict[str, Any]:
    active = [c for c in cases if c.get("status") == "active"]
    by = {"pass": 0, "fail": 0, "blocked": 0, "manual": 0, "error": 0, "not_run": 0, "skipped": 0}
    blockers, risks = [], []
    for c in active:
        r = c.get("last_result") or "not_run"
        by[r if r in by else "not_run"] += 1
        if c["priority"] == "P1" and r in ("fail", "error"):
            blockers.append(f"{c['number']} ({c['title'][:60]}) fail hai - P1")
        if c["priority"] == "P1" and r in ("not_run", "manual", "blocked"):
            (blockers if kind == "apk" else risks).append(f"{c['number']} P1 abhi chala / jaancha nahi")
        if c["type"] == "accessibility" and r == "fail":
            (blockers if govt_facing else risks).append(f"{c['number']} accessibility fail" + (" (GIGW / IS 17802 zaroori)" if govt_facing else ""))
        if (c.get("age_days") or 0) > stale_days and r == "pass":
            risks.append(f"{c['number']} {stale_days} din se nahi chala")
    openb = [b for b in bugs if b.get("status") in ("open", "reopened", "fixed")]
    for b in openb:
        if b["severity"] in ("critical", "major"):
            blockers.append(f"{b['number']} {SEV_LABEL[b['severity']]}: {b['title'][:70]}" + (" (fix ki jaanch baaki)" if b["status"] == "fixed" else ""))
        elif b["status"] == "reopened":
            risks.append(f"{b['number']} phir se khula")
    ran = by["pass"] + by["fail"] + by["error"]
    pass_rate = round(100 * by["pass"] / ran) if ran else 0
    if not active:
        verdict, say = "not_ready", "Abhi koi test case nahi hai: pehle cases banaiye."
    elif blockers:
        verdict, say = "not_ready", f"Release abhi nahi: {len(blockers)} rukawat."
    elif risks or by["not_run"] or pass_rate < 95:
        verdict, say = "risky", f"Chal sakta hai par khatra hai: pass {pass_rate}%, {by['not_run']} case chale nahi, {len(risks)} baatein."
    else:
        verdict, say = "ready", f"Release ke liye taiyaar: {by['pass']} cases pass, koi gambhir bug khula nahi."
    return {"verdict": verdict, "say": say, "counts": by, "pass_rate": pass_rate, "blockers": blockers[:20], "risks": risks[:20],
            "open_bugs": {s: sum(1 for b in openb if b["severity"] == s) for s in SEVERITIES}}

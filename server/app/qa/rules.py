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
TYPE_LABEL = {"functional": "Functional", "ui": "Look", "accessibility": "Accessibility (a11y)", "mobile": "Mobile", "negative": "Wrong input",
              "security": "Security (basic)", "performance": "Speed", "usability": "Ease of use"}
TECHNIQUES = ("smoke", "requirement", "ep", "bva", "checklist", "exploratory", "regression", "navigation")
PRIORITIES = ("P1", "P2", "P3", "P4")
SEVERITIES = ("critical", "major", "minor", "trivial")
SEV_LABEL = {"critical": "Critical", "major": "Major", "minor": "Minor", "trivial": "Trivial"}
BUG_STATUS = ("open", "fixed", "verified", "reopened", "wont_fix", "duplicate", "closed")
BUG_LABEL = {"open": "Open", "fixed": "Fixed (check pending)", "verified": "Verified in a check", "reopened": "Reopened",
             "wont_fix": "Will not fix", "duplicate": "Duplicate", "closed": "Closed"}
OPEN_BUGS = ("open", "reopened", "fixed")
SECTORS = ("general", "govt", "securities", "bank", "health", "edu")

STANDARDS = {
    "general": "WCAG 2.2 AA (= ISO/IEC 40500:2025) is good practice; the RPwD Act 2016 speaks of access for everyone.",
    "govt": "Government / government-linked sites and apps: GIGW 3.0 (based on WCAG 2.1 AA, 88 mandatory checkpoints) + IS 17802; RPwD Rule 15.",
    "securities": "SEBI circular (31 Jul 2025, revised 29 Aug 2025): IS 17802 + WCAG 2.1+ / GIGW 3.0, IAAP auditor, annual audit.",
    "bank": "Bank / NBFC: treat RPwD + IS 17802 / WCAG 2.1 AA as the standard (check the regulator's own circular).",
    "health": "Health / hospital: WCAG 2.2 AA; GIGW 3.0 if linked to a government scheme.",
    "edu": "School / college: WCAG 2.2 AA; GIGW 3.0 if it is a government institution.",
}

PAY_HOSTS = ("razorpay.com", "paytm.com", "paytm.in", "phonepe.com", "payu.in", "payumoney.com", "cashfree.com", "stripe.com",
             "ccavenue.com", "billdesk.com", "instamojo.com", "juspay.in", "paypal.com", "easebuzz.in")
SECRET_WORDS = re.compile(r"\b(otp|cvv|cvc|upi ?pin|atm ?pin|card ?number|card no|expiry|net ?banking|m-?pin)\b", re.I)

APK_CHECKLIST = [
    ("install", "Install on the phone (over the old version, if there is one)", "It installs and the old data stays", "P1", "functional"),
    ("open", "Open the app (internet on)", "First screen within 3 sec after the splash, no crash", "P1", "functional"),
    ("consent", "First time: tap Next on the consent screen without ticking", "Next stays disabled until the box is ticked", "P1", "functional"),
    ("back", "Press the phone's Back on every screen", "The previous screen comes; on home the app closes, no crash", "P2", "functional"),
    ("rotate", "Rotate the phone on every big screen (landscape)", "Nothing is cut off, no data is lost", "P3", "ui"),
    ("dark", "Put the phone in Dark mode and open the app", "All text can be read", "P3", "ui"),
    ("font", "Settings > Font size to the largest, open the app", "Text is not cut off, buttons can be tapped", "P2", "accessibility"),
    ("talkback", "Turn TalkBack on and touch every button", "The name of every button / photo is spoken", "P2", "accessibility"),
    ("touch", "Tap the small icons / buttons", "Every tap target is at least 48 dp, the wrong thing is not tapped", "P2", "accessibility"),
    ("offline", "Turn the internet off and open the app", "A clear message, no crash; fine again once the internet is back", "P2", "negative"),
    ("notify", "Answer 'No' to the notification permission", "The app works, and the permission can be given later in settings", "P3", "functional"),
    ("privacy", "Open the Privacy policy and Delete account screens", "Both open, with the grievance officer's name / email", "P1", "functional"),
    ("low_end", "Run it for 5 min on a cheap / old phone (2-3 GB RAM)", "It does not hang or heat up", "P3", "performance"),
    ("prelaunch", "Upload the AAB to Play Console > Internal testing and read the pre-launch report", "No crash / ANR; accessibility warnings read", "P1", "performance"),
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
        out.append({"label": "empty", "value": "", "valid": False, "technique": "ep"})
    if t == "email":
        out += [{"label": "wrong email (no @)", "value": "ramesh.example.com", "valid": False, "technique": "ep"},
                {"label": "valid email", "value": "test.user@example.com", "valid": True, "technique": "ep"}]
    if t == "number":
        lo, hi = _num(f.get("min")), _num(f.get("max"))
        if lo is not None:
            out += [{"label": f"below the limit ({lo - 1:g})", "value": f"{lo - 1:g}", "valid": False, "technique": "bva"},
                    {"label": f"at the limit ({lo:g})", "value": f"{lo:g}", "valid": True, "technique": "bva"}]
        if hi is not None:
            out += [{"label": f"at the limit ({hi:g})", "value": f"{hi:g}", "valid": True, "technique": "bva"},
                    {"label": f"above the limit ({hi + 1:g})", "value": f"{hi + 1:g}", "valid": False, "technique": "bva"}]
    mn = _num(f.get("minlength"))
    if mn and mn > 1 and t not in ("number", "email"):
        out += [{"label": f"{int(mn) - 1} characters (too few)", "value": "a" * (int(mn) - 1), "valid": False, "technique": "bva"},
                {"label": f"{int(mn)} characters", "value": "a" * int(mn), "valid": True, "technique": "bva"}]
    if f.get("pattern") and t in ("tel", "text") and re.search(r"\\d|\[0-9\]", f["pattern"]):
        out.append({"label": "letters instead of digits", "value": "abcd", "valid": False, "technique": "ep"})
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
        return "The full website address is needed (for example https://my-shop.in)."
    if host in ("localhost",) or host.endswith((".local", ".internal", ".lan", ".localhost")):
        return "Hoola does not test local / internal addresses."
    try:
        ipaddress.ip_address(host)
        return "Give a domain name, not an IP address (ownership is confirmed through the domain)."
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
            blockers.append(f"{c['number']} ({c['title'][:60]}) fails - P1")
        if c["priority"] == "P1" and r in ("not_run", "manual", "blocked"):
            (blockers if kind == "apk" else risks).append(f"{c['number']} P1 not run / checked yet")
        if c["type"] == "accessibility" and r == "fail":
            (blockers if govt_facing else risks).append(f"{c['number']} accessibility fail" + (" (GIGW / IS 17802 required)" if govt_facing else ""))
        if (c.get("age_days") or 0) > stale_days and r == "pass":
            risks.append(f"{c['number']} not run for {stale_days} days")
    openb = [b for b in bugs if b.get("status") in ("open", "reopened", "fixed")]
    for b in openb:
        if b["severity"] in ("critical", "major"):
            blockers.append(f"{b['number']} {SEV_LABEL[b['severity']]}: {b['title'][:70]}" + (" (fix check pending)" if b["status"] == "fixed" else ""))
        elif b["status"] == "reopened":
            risks.append(f"{b['number']} reopened")
    ran = by["pass"] + by["fail"] + by["error"]
    pass_rate = round(100 * by["pass"] / ran) if ran else 0
    if not active:
        verdict, say = "not_ready", "There are no test cases yet: create cases first."
    elif blockers:
        verdict, say = "not_ready", f"Not ready for release: {len(blockers)} blockers."
    elif risks or by["not_run"] or pass_rate < 95:
        verdict, say = "risky", f"It can go but there is risk: pass {pass_rate}%, {by['not_run']} cases not run, {len(risks)} points."
    else:
        verdict, say = "ready", f"Ready for release: {by['pass']} cases pass, no serious bug open."
    return {"verdict": verdict, "say": say, "counts": by, "pass_rate": pass_rate, "blockers": blockers[:20], "risks": risks[:20],
            "open_bugs": {s: sum(1 for b in openb if b["severity"] == s) for s in SEVERITIES}}

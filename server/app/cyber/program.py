"""The security programme around the Cyber Suraksha engine (owner: "100 % Cyber security same as finance desks --- very advance and every
aspect and every cyber security tool in it").

Everything here is HER records and arithmetic; nothing scans, tests or touches anyone's systems:
  - notification clocks after an incident, by country (data: NOTIFY). Only India's rows are checked; every other row is shown with
    "check this" and its source, never assumed.
  - a controls self-assessment on CIS Controls v8 (IG1 safeguards), each mapped to its NIST CSF 2.0 function and ISO 27001:2022 theme.
  - an access review from her own user export (admins without 2-step, stale, shared, leavers still active).
  - a secrets scan of pasted code / config (values are masked, the text is not kept).
  - MITRE ATT&CK tactic / technique for each alert kind.
  - a risk register (likelihood x impact), vendor security reviews, incident playbooks + tabletop exercises, awareness training records,
    a password policy check against NIST SP 800-63B.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..db import session
from .models import CyberDoc, CyberSettings


class ProgramError(ValueError):
    pass


def _j(s: str | None, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _S():
    from . import service as S
    return S


def _now() -> datetime:
    return _S().clock()


def _iso(d: datetime | None) -> str:
    return _S()._iso(d)


# ---------------------------------------------------------------- 1. notification clocks by country
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
      "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"}          # EU + EEA (GDPR applies in the EEA)
NIS2_SECTORS = {"energy", "transport", "banking", "finance", "health", "water", "digital", "ict", "public", "space", "postal", "waste",
                "chemicals", "food", "manufacturing", "research", "cloud", "telecom"}

# id, countries ("EU" = the set above), law, to whom, clock: hours | business days | None, when it applies, checked, source
NOTIFY: list[dict[str, Any]] = [
    {"id": "in_certin", "c": ["IN"], "law": "CERT-In Directions (28 Apr 2022)", "to": "CERT-In (incident@cert-in.org.in)", "hours": 6,
     "when": "any", "checked": True, "src": "https://www.cert-in.org.in/Directions70B.jsp",
     "note": "Report within 6 hours of noticing it. The IT Helpdesk incident keeps the draft and the reminders."},
    {"id": "in_dpdp", "c": ["IN"], "law": "DPDP Rules 2025, Rule 7", "to": "Data Protection Board + every affected person", "hours": 72,
     "when": "personal", "checked": True, "src": "https://www.meity.gov.in/",
     "note": "Tell the Board and each affected person without delay; the detailed report within 72 hours."},
    {"id": "eu_gdpr", "c": ["EU"], "law": "GDPR Article 33", "to": "Your lead data protection authority", "hours": 72, "when": "personal",
     "checked": False, "src": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
     "note": "Within 72 hours of becoming aware, unless unlikely to put people at risk. Article 34: tell the people without undue delay if the risk is high."},
    {"id": "eu_nis2_ew", "c": ["EU"], "law": "NIS2 Article 23 (early warning)", "to": "Your national CSIRT / authority", "hours": 24,
     "when": "nis2", "checked": False, "src": "https://eur-lex.europa.eu/eli/dir/2022/2555/oj",
     "note": "Only for essential / important entities. Early warning within 24 hours of a significant incident."},
    {"id": "eu_nis2_n", "c": ["EU"], "law": "NIS2 Article 23 (notification)", "to": "Your national CSIRT / authority", "hours": 72,
     "when": "nis2", "checked": False, "src": "https://eur-lex.europa.eu/eli/dir/2022/2555/oj",
     "note": "Incident notification within 72 hours; a final report within one month."},
    {"id": "gb_ico", "c": ["GB"], "law": "UK GDPR Article 33", "to": "Information Commissioner's Office", "hours": 72, "when": "personal",
     "checked": False, "src": "https://ico.org.uk/for-organisations/report-a-breach/", "note": "Within 72 hours of becoming aware."},
    {"id": "us_sec", "c": ["US"], "law": "SEC Form 8-K Item 1.05", "to": "SEC (public filing)", "bdays": 4, "when": "listed",
     "checked": False, "src": "https://www.sec.gov/rules/final/2023/33-11216.pdf",
     "note": "Listed companies only: 4 business days after deciding the incident is material (the clock starts at that decision)."},
    {"id": "us_hipaa", "c": ["US"], "law": "HIPAA Breach Notification Rule", "to": "Affected people + HHS", "hours": 24 * 60, "when": "health",
     "checked": False, "src": "https://www.hhs.gov/hipaa/for-professionals/breach-notification/",
     "note": "Health data: tell people within 60 days; HHS too (500+ people at once, fewer by year end)."},
    {"id": "us_state", "c": ["US"], "law": "State breach laws", "to": "Affected residents (and some state attorneys general)", "hours": None,
     "when": "personal", "checked": False, "src": "https://www.ncsl.org/technology-and-communication/security-breach-notification-laws",
     "note": "Every state has its own law, often 30-60 days. Check the states where the affected people live."},
    {"id": "sg_pdpa", "c": ["SG"], "law": "PDPA section 26D", "to": "PDPC (+ people if significant harm)", "hours": 72, "when": "personal",
     "checked": False, "src": "https://www.pdpc.gov.sg/", "note": "Within 3 calendar days after assessing the breach is notifiable."},
    {"id": "au_ndb", "c": ["AU"], "law": "Privacy Act, Notifiable Data Breaches", "to": "OAIC + affected people", "hours": 24 * 30,
     "when": "personal", "checked": False, "src": "https://www.oaic.gov.au/privacy/notifiable-data-breaches",
     "note": "Assess within 30 days; notify as soon as practicable once it is an eligible breach."},
    {"id": "ca_pipeda", "c": ["CA"], "law": "PIPEDA section 10.1", "to": "Privacy Commissioner + affected people", "hours": None,
     "when": "personal", "checked": False, "src": "https://www.priv.gc.ca/", "note": "As soon as feasible when there is a real risk of significant harm."},
    {"id": "br_lgpd", "c": ["BR"], "law": "LGPD + ANPD Resolution 15/2024", "to": "ANPD + affected people", "bdays": 3, "when": "personal",
     "checked": False, "src": "https://www.gov.br/anpd/", "note": "Within 3 working days of knowing the incident affected personal data."},
    {"id": "jp_appi", "c": ["JP"], "law": "APPI", "to": "Personal Information Protection Commission", "hours": 24 * 30, "when": "personal",
     "checked": False, "src": "https://www.ppc.go.jp/en/", "note": "A first report promptly (about 3-5 days), the full report within 30 days (60 for an attack)."},
    {"id": "za_popia", "c": ["ZA"], "law": "POPIA section 22", "to": "Information Regulator + affected people", "hours": None, "when": "personal",
     "checked": False, "src": "https://inforegulator.org.za/", "note": "As soon as reasonably possible."},
    {"id": "kr_pipa", "c": ["KR"], "law": "PIPA", "to": "PIPC / KISA + affected people", "hours": 72, "when": "personal", "checked": False,
     "src": "https://www.pipc.go.kr/", "note": "Within 72 hours of knowing."},
    {"id": "ng_ndpa", "c": ["NG"], "law": "Nigeria Data Protection Act s.40", "to": "NDPC", "hours": 72, "when": "personal", "checked": False,
     "src": "https://ndpc.gov.ng/", "note": "Within 72 hours."},
    {"id": "ke_dpa", "c": ["KE"], "law": "Data Protection Act s.43", "to": "Data Commissioner", "hours": 72, "when": "personal", "checked": False,
     "src": "https://www.odpc.go.ke/", "note": "Within 72 hours."},
    {"id": "ae_pdpl", "c": ["AE"], "law": "Federal Decree-Law 45/2021 (PDPL)", "to": "UAE Data Office", "hours": None, "when": "personal",
     "checked": False, "src": "https://u.ae/", "note": "Promptly; the executive regulations set the time."},
    {"id": "nz_privacy", "c": ["NZ"], "law": "Privacy Act 2020", "to": "Privacy Commissioner + affected people", "hours": None,
     "when": "personal", "checked": False, "src": "https://www.privacy.org.nz/", "note": "As soon as practicable for a notifiable breach."},
]


def _countries(tenant: str) -> list[str]:
    with session() as s:
        r = s.get(CyberSettings, tenant)
        main = ((r.country if r else "") or "IN").upper()
        extra = [c.upper() for c in _j(r.extra_countries if r else "[]", [])]
        sector = ((r.sector if r else "") or "").lower()
    out = [main] + [c for c in extra if c != main]
    return out, sector


def _rules_for(cc: str) -> list[dict]:
    return [r for r in NOTIFY if cc in r["c"] or ("EU" in r["c"] and cc in EU)]


def _add_bdays(d: datetime, n: int) -> datetime:
    x = d
    while n > 0:
        x += timedelta(days=1)
        if x.weekday() < 5:
            n -= 1
    return x


def notify_plan(tenant: str, incident: str) -> dict[str, Any]:
    """Who to tell, by when, for each country she works in. Applies on the incident's facts; marks are hers."""
    S = _S()
    inc = S.get_incident(tenant, incident)
    ccs, sector = _countries(tenant)
    pd = bool(inc.get("personal_data"))
    det = datetime.fromisoformat(inc["detected_at"]) if inc.get("detected_at") else _now()
    if det.tzinfo is None:
        det = det.replace(tzinfo=timezone.utc)
    marks = _doc(tenant, "notify", inc["id"])
    md = _j(marks.data, {}) if marks else {}
    now = _now()
    rows, unknown = [], []
    for cc in ccs:
        rs = _rules_for(cc)
        if not rs:
            unknown.append(cc)
            continue
        for r in rs:
            when = r["when"]
            applies = (when == "any" or (when == "personal" and pd) or (when == "health" and sector == "health")
                       or (when == "listed" and sector in ("listed", "public company"))
                       or (when == "nis2" and sector in NIS2_SECTORS))
            maybe = when in ("nis2", "listed", "health") and not applies and not sector
            due = None
            if r.get("hours"):
                due = det + timedelta(hours=r["hours"])
            elif r.get("bdays"):
                due = _add_bdays(det, r["bdays"])
            m = md.get(r["id"], {})
            st = m.get("status") or ("na" if not applies and not maybe else "open")
            if st == "open" and due and due < now:
                st = "overdue"
            rows.append({"id": r["id"], "country": cc, "law": r["law"], "to": r["to"], "note": r["note"], "source": r["src"],
                         "checked": r["checked"], "applies": applies, "maybe": maybe, "due": _iso(due) if due else "",
                         "due_local": S._local(tenant, due) if due else "", "hours_left": round((due - now).total_seconds() / 3600, 1) if due else None,
                         "status": st, "reference": m.get("reference", ""), "marked_note": m.get("note", ""),
                         "say": ("" if r["checked"] else "Check this: ") + r["note"]})
    rows.sort(key=lambda x: (x["status"] not in ("overdue", "open"), x["due"] or "9999"))
    nxt = next((x for x in rows if x["status"] in ("open", "overdue") and x["due"]), None)
    say = ""
    if nxt:
        say = (f"Next notice: {nxt['law']} to {nxt['to']} by {nxt['due_local']}" + ("" if nxt["checked"] else " (check this rule)") + ".")
    if unknown:
        say += f" No notification rule kept for {', '.join(unknown)}: check this with a local lawyer."
    return {"incident": inc["id"], "number": inc["number"], "rows": rows, "unknown": unknown, "say": say.strip()}


def mark_notify(tenant: str, incident: str, rule: str, status: str, reference: str = "", note: str = "") -> dict[str, Any]:
    if status not in ("done", "na", "open"):
        raise ProgramError("Status is done, na or open.")
    if rule not in {r["id"] for r in NOTIFY}:
        raise ProgramError("Unknown notification rule.")
    inc = _S().get_incident(tenant, incident)
    with session() as s:
        d = _doc_s(s, tenant, "notify", inc["id"])
        if d is None:
            d = CyberDoc(tenant_id=tenant, kind="notify", ref=inc["id"], title=inc["number"])
            s.add(d)
        md = _j(d.data, {})
        md[rule] = {"status": status, "reference": str(reference or "")[:120], "note": str(note or "")[:300], "at": _iso(_now())}
        d.data = json.dumps(md)
        d.updated_at = _now()
    plan = notify_plan(tenant, incident)
    plan["say"] = ("Marked as told. " if status == "done" else "Marked. ") + plan["say"]
    return plan


# ---------------------------------------------------------------- docs plumbing
def _doc_s(s, tenant: str, kind: str, ref: str = "") -> CyberDoc | None:
    q = select(CyberDoc).where(CyberDoc.tenant_id == tenant, CyberDoc.kind == kind)
    if ref:
        q = q.where(CyberDoc.ref == ref)
    return s.scalars(q.order_by(CyberDoc.updated_at.desc())).first()


def _doc(tenant: str, kind: str, ref: str = "") -> CyberDoc | None:
    with session() as s:
        d = _doc_s(s, tenant, kind, ref)
        if d is not None:
            s.expunge(d)
        return d


def _seq(s, tenant: str, kind: str, prefix: str) -> str:
    n = len(s.scalars(select(CyberDoc.id).where(CyberDoc.tenant_id == tenant, CyberDoc.kind == kind)).all())
    return f"{prefix}-{n + 1:04d}"


def _docs(tenant: str, kind: str) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(CyberDoc).where(CyberDoc.tenant_id == tenant, CyberDoc.kind == kind)
                         .order_by(CyberDoc.created_at.desc())).all()
        return [{"id": d.id, "ref": d.ref, "title": d.title, "status": d.status, "created_at": _iso(d.created_at),
                 "updated_at": _iso(d.updated_at), **_j(d.data, {})} for d in rows]


def _get(s, tenant: str, did: str, kind: str) -> CyberDoc:
    d = s.get(CyberDoc, did)
    if d is None or d.tenant_id != tenant or d.kind != kind:
        raise ProgramError("Not found.")
    return d


# ---------------------------------------------------------------- 2. controls: CIS Controls v8 (IG1) -> NIST CSF 2.0 + ISO 27001:2022
# control no, title, CSF function, ISO 27001:2022 Annex A theme, [(qid, question, fix)]
CONTROLS: list[tuple[int, str, str, str, list[tuple[str, str, str]]]] = [
    (1, "Inventory of devices", "Identify", "5.9 Inventory of assets", [
        ("1.1", "Do you keep a list of every PC, laptop, phone, server and network device the business uses?", "Start a device list (the IT Helpdesk keeps one); review it monthly."),
        ("1.2", "Do you find and remove devices that should not be on your network?", "Check your router / Wi-Fi client list monthly; block what you do not know.")]),
    (2, "Inventory of software", "Identify", "5.9 Inventory of assets", [
        ("2.1", "Do you keep a list of the software in use (with versions)?", "Add it under Attack surface > Software so new threats are matched."),
        ("2.2", "Is software that is no longer supported by its maker removed or replaced?", "Replace end-of-life software (old Windows, old Tally, old PHP).")]),
    (3, "Data protection", "Protect", "5.12 Classification / 8.10-8.12", [
        ("3.1", "Do you know where customer / personal data is kept?", "Write down each place (Drive, Tally, CRM, mailboxes) and who can open it."),
        ("3.2", "Is data on laptops and phones encrypted (BitLocker / FileVault / phone lock)?", "Turn on BitLocker / FileVault and a phone screen lock everywhere."),
        ("3.3", "Is old data deleted on a schedule?", "Set how long you keep each kind of data and delete the rest.")]),
    (4, "Secure configuration", "Protect", "8.9 Configuration management", [
        ("4.1", "Are default passwords changed on routers, cameras and admin panels?", "Change every default password; keep them in a password manager."),
        ("4.2", "Do devices lock by themselves after a few minutes idle?", "Set screen lock at 5-15 minutes on every PC and phone."),
        ("4.3", "Is a firewall on for every PC and the office router?", "Turn on the OS firewall; close router ports you do not use.")]),
    (5, "Account management", "Protect", "5.16 Identity management", [
        ("5.1", "Does every person have their own account (no shared logins)?", "Give each person their own login; remove shared ones."),
        ("5.2", "Are accounts of people who left disabled the same day?", "Run an access review and disable leavers' accounts."),
        ("5.3", "Are admin accounts separate from everyday accounts?", "Use a separate admin login only for admin work.")]),
    (6, "Access control", "Protect", "5.15 / 8.5 Access control + authentication", [
        ("6.1", "Is 2-step sign-in (MFA) on for email and every cloud service?", "Turn on 2-step for all users, admins first."),
        ("6.2", "Is MFA on for remote access (VPN / remote desktop)?", "Require MFA on VPN / RDP, or close RDP to the internet."),
        ("6.3", "Do people get only the access their work needs?", "Remove admin rights from everyday users.")]),
    (7, "Vulnerability management", "Identify", "8.8 Technical vulnerabilities", [
        ("7.1", "Are Windows / macOS / phone updates installed within 2 weeks?", "Turn on automatic updates; check monthly that they ran."),
        ("7.2", "Are apps (browser, Office, Tally, plugins) updated?", "Turn on auto-update; watch Attack surface > Advisories.")]),
    (8, "Audit log management", "Detect", "8.15 Logging", [
        ("8.1", "Are logs (login, firewall, server) kept and looked at?", "Keep logs for at least 90 days (your law may need longer) and paste them here."),
        ("8.2", "Are clocks on servers and devices synced (NTP)?", "Turn on automatic time everywhere.")]),
    (9, "Email and browser protection", "Protect", "8.23 Web filtering", [
        ("9.1", "Do your domains have SPF, DKIM and DMARC set?", "Add your domain under Attack surface and fix what it shows."),
        ("9.2", "Are browsers kept updated with only needed extensions?", "Remove unknown browser extensions.")]),
    (10, "Malware defences", "Protect", "8.7 Protection against malware", [
        ("10.1", "Is antivirus / EDR on and updating on every PC?", "Install and keep antivirus on; check its console weekly."),
        ("10.2", "Is autorun / USB auto-play turned off?", "Turn off auto-play for removable drives.")]),
    (11, "Data recovery (backups)", "Recover", "8.13 Information backup", [
        ("11.1", "Are important files and databases backed up automatically?", "Back up daily (3 copies, 2 kinds of media, 1 off-site)."),
        ("11.2", "Is one backup kept offline or unchangeable (ransomware-safe)?", "Keep one copy offline or immutable."),
        ("11.3", "Have you restored from a backup in the last 3 months?", "Do a restore test and write down the time it took.")]),
    (12, "Network infrastructure", "Protect", "8.20 Network security", [
        ("12.1", "Is router / firewall firmware up to date?", "Update router firmware; replace routers the maker no longer supports."),
        ("12.2", "Is guest Wi-Fi separate from the office network?", "Put guests and cameras on their own network.")]),
    (13, "Network monitoring", "Detect", "8.16 Monitoring", [
        ("13.1", "Are firewall / server alerts collected in one place?", "Paste or upload them here regularly, or set the log collector.")]),
    (14, "Security awareness", "Protect", "6.3 Awareness and training", [
        ("14.1", "Has every person had security training in the last 12 months?", "Run the training plan under Programme > Training."),
        ("14.2", "Do people know how to report a suspicious mail?", "Tell everyone: forward it to you; Hoola checks it.")]),
    (15, "Service providers", "Govern", "5.19-5.22 Supplier relationships", [
        ("15.1", "Do you keep a list of vendors who hold your data or access?", "Add vendors under Programme > Vendors."),
        ("15.2", "Do contracts with them say how they protect your data?", "Ask for their security terms; review yearly.")]),
    (16, "Application security", "Protect", "8.25-8.28 Secure development", [
        ("16.1", "If you build software: are secrets kept out of code?", "Scan code with the secrets check; keep keys in a vault / environment."),
        ("16.2", "Are web apps behind HTTPS with security headers?", "Check your domain under Attack surface.")]),
    (17, "Incident response", "Respond", "5.24-5.28 Incident management", [
        ("17.1", "Is it written who does what in a security incident?", "Name an incident lead and a deputy; keep their numbers offline."),
        ("17.2", "Do you know who you must notify and how fast in your country?", "See Incidents > notification clocks; fill your country in Settings."),
        ("17.3", "Have you practised an incident in the last 12 months?", "Run a tabletop exercise under Programme.")]),
    (18, "Penetration testing", "Identify", "8.8 / 8.29 Security testing", [
        ("18.1", "Has an authorised tester checked your important systems?", "Hire a certified tester under a written scope (Hoola never tests systems).")]),
]
ANS = {"yes": 1.0, "partial": 0.5, "no": 0.0}


def controls_view(tenant: str) -> dict[str, Any]:
    d = _doc(tenant, "controls")
    ans = (_j(d.data, {}).get("answers") if d else {}) or {}
    out, fn, gaps = [], {}, []
    tot = got = 0.0
    for no, title, csf, iso, qs in CONTROLS:
        cs = cg = 0.0
        rows = []
        for qid, q, fix in qs:
            a = ans.get(qid, "")
            rows.append({"id": qid, "q": q, "fix": fix, "a": a})
            if a in ANS:
                cs += 1
                cg += ANS[a]
                if a != "yes":
                    gaps.append({"id": qid, "control": no, "title": title, "q": q, "fix": fix, "a": a, "csf": csf})
        tot += cs
        got += cg
        f = fn.setdefault(csf, [0.0, 0.0])
        f[0] += cs
        f[1] += cg
        out.append({"no": no, "title": title, "csf": csf, "iso": iso, "questions": rows, "answered": int(cs),
                    "score": round(100 * cg / cs) if cs else None})
    total_q = sum(len(c[4]) for c in CONTROLS)
    gaps.sort(key=lambda g: (g["a"] != "no", g["control"]))
    score = round(100 * got / tot) if tot else None
    return {"controls": out, "score": score, "answered": int(tot), "total": total_q,
            "functions": {k: (round(100 * v[1] / v[0]) if v[0] else None) for k, v in fn.items()}, "gaps": gaps[:40],
            "say": (f"Controls: {score}% on {int(tot)} of {total_q} answered (CIS Controls v8, IG1)." if score is not None
                    else "Answer the controls questions to get your score."),
            "frameworks": "CIS Controls v8 (IG1), mapped to NIST CSF 2.0 functions and ISO 27001:2022 Annex A themes. A self-check, not a certification."}


def controls_save(tenant: str, answers: dict[str, str]) -> dict[str, Any]:
    valid = {q[0] for c in CONTROLS for q in c[4]}
    clean = {k: v for k, v in (answers or {}).items() if k in valid and v in ("yes", "partial", "no", "na", "")}
    with session() as s:
        d = _doc_s(s, tenant, "controls")
        if d is None:
            d = CyberDoc(tenant_id=tenant, kind="controls", title="Controls self-check")
            s.add(d)
        old = _j(d.data, {}).get("answers", {})
        old.update(clean)
        hist = _j(d.data, {}).get("history", [])
        d.data = json.dumps({"answers": {k: v for k, v in old.items() if v}, "history": hist})
        d.updated_at = _now()
    v = controls_view(tenant)
    with session() as s:
        d = _doc_s(s, tenant, "controls")
        data = _j(d.data, {})
        h = data.get("history", [])
        day = _now().date().isoformat()
        h = [x for x in h if x.get("day") != day] + [{"day": day, "score": v["score"]}]
        data["history"] = h[-24:]
        d.data = json.dumps(data)
    v["history"] = data["history"]
    return v


# ---------------------------------------------------------------- 3. access review (her own user export)
_SHARED = re.compile(r"^(admin|info|office|accounts|sales|support|test|demo|user|staff|reception|hr|it|shared|team)\d*@", re.I)


def _col(h: list[str], *names: str) -> int:
    for i, x in enumerate(h):
        lx = x.strip().lower()
        if any(n in lx for n in names):
            return i
    return -1


def _date(v: str) -> datetime | None:
    v = (v or "").strip()
    if not v or v.lower() in ("never", "-", "n/a"):
        return None
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v[:19].replace("Z", ""), f).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def access_review(tenant: str, text: str, leavers: str = "", source: str = "", stale_days: int = 90) -> dict[str, Any]:
    """Her user export (Google Workspace / Microsoft 365 / any CSV): findings per user. Read only; nothing is changed anywhere."""
    if not (text or "").strip():
        raise ProgramError("Paste or upload your user list (CSV).")
    rows = list(csv.reader(io.StringIO(text.strip())))
    if len(rows) < 2:
        raise ProgramError("The list needs a header row and at least one user.")
    h = rows[0]
    ce, cn = _col(h, "email", "user principal", "upn", "username", "login"), _col(h, "name", "display")
    ca, cm = _col(h, "admin", "role"), _col(h, "2sv", "2-step", "mfa", "multi", "two")
    cl, cs = _col(h, "last login", "last sign", "last_login", "lastsignin", "last activity", "last seen"), _col(h, "status", "suspend", "enabled", "blocked")
    if ce < 0:
        raise ProgramError("No email / username column found in the header.")
    gone = {x.strip().lower() for x in re.split(r"[\n,;]+", leavers or "") if x.strip()}
    now = _now()
    users, findings = [], []

    def yes(v: str) -> bool:
        return (v or "").strip().lower() in ("true", "yes", "y", "1", "enrolled", "enforced", "enabled", "on", "admin", "super admin", "global administrator")

    for r in rows[1:]:
        if not r or len(r) <= ce or not r[ce].strip():
            continue
        g = lambda i: r[i].strip() if 0 <= i < len(r) else ""   # noqa: E731
        email = g(ce).lower()
        name = g(cn) or email
        role = g(ca)
        admin = bool(role) and (yes(role) or "admin" in role.lower() or "owner" in role.lower())
        mfa_raw = g(cm)
        mfa = yes(mfa_raw) if mfa_raw else None
        last = _date(g(cl))
        status = g(cs).lower()
        head = h[cs].lower() if cs >= 0 else ""
        if not status:
            active = True
        elif status in ("true", "yes", "false", "no", "1", "0"):
            on = status in ("true", "yes", "1")
            active = on if ("enabled" in head or "active" in head) else not on      # "Suspended: true" = not active
        else:
            active = not any(w in status for w in ("suspend", "disabled", "blocked", "inactive", "deleted"))
        f = []
        if active and (email in gone or name.lower() in gone):
            f.append(("high", "Left the business but the account is still active", "Disable it today and move their data to the manager."))
        if active and admin and mfa is False:
            f.append(("high", "Admin without 2-step sign-in", "Turn on 2-step for this admin now."))
        elif active and mfa is False:
            f.append(("medium", "No 2-step sign-in", "Turn on 2-step sign-in."))
        if active and last and (now - last).days > stale_days:
            f.append(("medium", f"Not used for {(now - last).days} days", "Disable it if nobody needs it."))
        if active and last is None and cl >= 0:
            f.append(("low", "Never signed in", "Check it is needed; disable if not."))
        if active and _SHARED.match(email):
            f.append(("medium", "Looks like a shared account", "Give each person their own login; keep shared mailboxes without a password login."))
        users.append({"email": email, "name": name, "admin": admin, "mfa": mfa, "last": _iso(last) if last else "", "active": active,
                      "findings": [{"level": a, "say": b, "fix": c} for a, b, c in f]})
        for a, b, c in f:
            findings.append({"level": a, "user": email, "say": b, "fix": c})
    act = [u for u in users if u["active"]]
    admins = [u for u in act if u["admin"]]
    known = [u for u in act if u["mfa"] is not None]
    mfa_pct = round(100 * sum(1 for u in known if u["mfa"]) / len(known)) if known else None
    if len(act) >= 4 and len(admins) > max(2, len(act) // 5):
        findings.insert(0, {"level": "medium", "user": "", "say": f"{len(admins)} admins out of {len(act)} active users",
                            "fix": "Keep 2-3 admins; others do not need admin rights."})
    for u in gone:
        if not any(u in (x["email"], x["name"].lower()) for x in users):
            findings.append({"level": "low", "user": u, "say": "On the leavers list but not in this export", "fix": "Check other systems for this person."})
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda x: order[x["level"]])
    summ = {"users": len(users), "active": len(act), "admins": len(admins), "mfa_pct": mfa_pct, "high": sum(1 for f in findings if f["level"] == "high"),
            "medium": sum(1 for f in findings if f["level"] == "medium")}
    with session() as s:
        n = _seq(s, tenant, "access", "AR")
        s.add(CyberDoc(tenant_id=tenant, kind="access", ref=n, title=(source or "User list")[:120],
                       data=json.dumps({"summary": summ, "findings": findings[:300], "users": users[:2000]})))
    say = (f"{n}: {summ['active']} active user{'s' if summ['active'] != 1 else ''}, {summ['admins']} admin{'s' if summ['admins'] != 1 else ''}, 2-step on "
           f"{'unknown' if mfa_pct is None else str(mfa_pct) + '%'}; {summ['high']} urgent, {summ['medium']} to fix.")
    return {"ref": n, "summary": summ, "findings": findings[:300], "users": users[:300], "say": say}


# ---------------------------------------------------------------- 4. secrets in pasted code / config
SECRETS: list[tuple[str, str, str]] = [
    ("AWS access key", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b", "Deactivate it in AWS IAM and create a new one."),
    ("AWS secret key", r"(?i)aws_?secret_?access_?key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}", "Rotate it in AWS IAM."),
    ("GitHub token", r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b", "Revoke it in GitHub > Settings > Developer settings."),
    ("GitLab token", r"\bglpat-[A-Za-z0-9_-]{20,}\b", "Revoke it in GitLab."),
    ("Slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b", "Revoke it in the Slack app settings."),
    ("Slack webhook", r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+", "Delete and recreate the webhook."),
    ("Stripe key", r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{20,}\b", "Roll the key in the Stripe dashboard."),
    ("Razorpay key", r"\brzp_(live|test)_[A-Za-z0-9]{10,}\b", "Regenerate the key in the Razorpay dashboard."),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b", "Restrict or delete it in Google Cloud > Credentials."),
    ("Google OAuth secret", r"\bGOCSPX-[A-Za-z0-9_-]{20,}\b", "Reset the client secret in Google Cloud."),
    ("OpenAI / Anthropic key", r"\bsk-(proj-|ant-)?[A-Za-z0-9_-]{20,}\b", "Revoke it in the provider's console."),
    ("Twilio key", r"\bSK[0-9a-fA-F]{32}\b", "Delete the API key in Twilio."),
    ("SendGrid key", r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b", "Delete it in SendGrid."),
    ("Telegram bot token", r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", "Revoke it with BotFather (/revoke)."),
    ("Private key", r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "Replace the key pair; remove the old public key everywhere."),
    ("JSON web token", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "Change the signing secret if it is long-lived."),
    ("Database URL with password", r"\b(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp)://[^:\s/]+:[^@\s]+@", "Change the database password."),
    ("Password in config", r"(?i)\b(password|passwd|pwd|secret|api_?key|access_?token)\s*[:=]\s*['\"]?[^\s'\"#]{6,}", "Move it to a secret store / environment and change it."),
]
_SECRETS_RX = [(n, re.compile(p), f) for n, p, f in SECRETS]


def _mask_val(v: str) -> str:
    v = v.strip()
    return (v[:4] + "…" + v[-2:]) if len(v) > 8 else "…"


def secrets_scan(tenant: str, text: str, name: str = "") -> dict[str, Any]:
    """Finds keys / passwords in pasted code or config. The text is not kept; values are shown masked."""
    if not (text or "").strip():
        raise ProgramError("Paste the code or config to scan.")
    found, seen = [], set()
    for i, line in enumerate(text.splitlines()[:20000], 1):
        for n, rx, fix in _SECRETS_RX:
            for m in rx.finditer(line):
                key = (n, m.group(0))
                if key in seen or (n == "Password in config" and any(x["line"] == i for x in found)):
                    continue
                low = line.lower()
                if n == "Password in config" and any(w in low for w in ("${", "os.environ", "getenv", "process.env", "<", "changeme", "example", "xxxx", "your_")):
                    continue
                seen.add(key)
                found.append({"type": n, "line": i, "value": _mask_val(m.group(0)), "fix": fix,
                              "level": "low" if "_test_" in m.group(0) or n == "JSON web token" else "high"})
    with session() as s:
        n = _seq(s, tenant, "secrets", "SS")
        s.add(CyberDoc(tenant_id=tenant, kind="secrets", ref=n, title=(name or "Pasted text")[:120],
                       data=json.dumps({"found": found[:200], "lines": len(text.splitlines())})))
    hi = sum(1 for f in found if f["level"] == "high")
    say = (f"{len(found)} secret(s) found ({hi} live-looking): rotate each one - deleting it from the file is not enough, it stays in history."
           if found else "No keys or passwords found in it.")
    return {"ref": n, "found": found[:200], "say": say}


# ---------------------------------------------------------------- 5. MITRE ATT&CK for alert kinds
ATTACK: dict[str, tuple[str, str, str]] = {
    "ransomware": ("Impact", "T1486", "Data Encrypted for Impact"),
    "login_after_fail": ("Credential Access", "T1110", "Brute Force"),
    "brute_force": ("Credential Access", "T1110", "Brute Force"),
    "login_fail": ("Credential Access", "T1110", "Brute Force"),
    "gov_attack": ("Initial Access", "T1566", "Phishing"),
    "device_compromised": ("Execution", "T1204", "User Execution"),
    "malware_spread": ("Lateral Movement", "T1570", "Lateral Tool Transfer"),
    "malware_active": ("Execution", "T1204", "User Execution"),
    "malware_blocked": ("Execution", "T1204", "User Execution"),
    "malware_campaign": ("Initial Access", "T1566.001", "Spearphishing Attachment"),
    "leaked_password": ("Credential Access", "T1589.001", "Gather Victim Identity: Credentials"),
    "suspicious_sending": ("Impact", "T1534", "Internal Spearphishing"),
    "forwarding_rule": ("Collection", "T1114.003", "Email Forwarding Rule"),
    "suspicious_login": ("Initial Access", "T1078", "Valid Accounts"),
    "new_ip_login": ("Initial Access", "T1078", "Valid Accounts"),
    "impossible_travel": ("Initial Access", "T1078", "Valid Accounts"),
    "login_blocked": ("Initial Access", "T1078", "Valid Accounts"),
    "admin_granted": ("Privilege Escalation", "T1098", "Account Manipulation"),
    "new_device": ("Persistence", "T1098.005", "Device Registration"),
    "port_scan": ("Reconnaissance", "T1595", "Active Scanning"),
    "waf_block": ("Initial Access", "T1190", "Exploit Public-Facing Application"),
    "waf_bypass": ("Initial Access", "T1190", "Exploit Public-Facing Application"),
    "fw_block": ("Reconnaissance", "T1595", "Active Scanning"),
    "av_problem": ("Defense Evasion", "T1562.001", "Disable or Modify Tools"),
}


def attack_of(kind: str) -> dict[str, str]:
    t = ATTACK.get(kind)
    if not t:
        return {}
    tid = t[1]
    return {"tactic": t[0], "id": tid, "name": t[2], "url": "https://attack.mitre.org/techniques/" + tid.replace(".", "/") + "/"}


# ---------------------------------------------------------------- 6. risk register
TREAT = ("reduce", "accept", "transfer", "avoid")


def _risk_view(d: CyberDoc) -> dict:
    x = _j(d.data, {})
    lk, im = int(x.get("likelihood") or 3), int(x.get("impact") or 3)
    sc = lk * im
    return {"id": d.id, "ref": d.ref, "title": d.title, "status": d.status, **x, "likelihood": lk, "impact": im, "score": sc,
            "band": "high" if sc >= 15 else "medium" if sc >= 8 else "low", "updated_at": _iso(d.updated_at)}


def risk_save(tenant: str, rid: str = "", **kw: Any) -> dict[str, Any]:
    title = str(kw.get("title") or "").strip()
    with session() as s:
        if rid:
            d = _get(s, tenant, rid, "risk")
        else:
            if not title:
                raise ProgramError("Name the risk (what could go wrong).")
            d = CyberDoc(tenant_id=tenant, kind="risk", ref=_seq(s, tenant, "risk", "RK"))
            s.add(d)
        x = _j(d.data, {})
        for k in ("asset", "threat", "owner", "action", "due"):
            if k in kw:
                x[k] = str(kw[k] or "")[:300]
        for k in ("likelihood", "impact"):
            if k in kw and kw[k] not in (None, ""):
                v = int(kw[k])
                if not 1 <= v <= 5:
                    raise ProgramError("Likelihood and impact are 1 to 5.")
                x[k] = v
        if kw.get("treatment"):
            if kw["treatment"] not in TREAT:
                raise ProgramError("Treatment is reduce, accept, transfer or avoid.")
            x["treatment"] = kw["treatment"]
        if title:
            d.title = title[:240]
        if kw.get("status") in ("open", "closed"):
            d.status = kw["status"]
        d.data = json.dumps(x)
        d.updated_at = _now()
        s.flush()
        v = _risk_view(d)
    return {"risk": v, "say": f"{v['ref']} saved: score {v['score']} ({v['band']})."}


def risks(tenant: str) -> list[dict]:
    with session() as s:
        rs = [_risk_view(d) for d in s.scalars(select(CyberDoc).where(CyberDoc.tenant_id == tenant, CyberDoc.kind == "risk")).all()]
    return sorted(rs, key=lambda r: (r["status"] != "open", -r["score"]))


# ---------------------------------------------------------------- 7. vendor security review
VENDOR_Q: list[tuple[str, str, int]] = [
    ("mfa", "They use 2-step sign-in for their staff and for your account", 10),
    ("encrypt", "Your data is encrypted in transit and at rest", 10),
    ("cert", "They hold ISO 27001 / SOC 2 or a similar independent report", 10),
    ("breach_notify", "The contract says they tell you of a breach quickly (with a time)", 10),
    ("location", "You know which countries your data is stored in", 8),
    ("subproc", "They list the other companies (sub-processors) that touch your data", 6),
    ("backup", "They back up and can restore your data", 8),
    ("delete", "They delete / return your data when you leave", 8),
    ("access", "Only named people at the vendor can reach your data", 8),
    ("patch", "They patch their systems promptly", 8),
    ("dpa", "A data protection agreement is signed", 8),
    ("history", "No serious breach in the last 3 years (or it was handled well)", 6),
]
DATA_LEVEL = {"none": 0, "internal": 1, "personal": 2, "sensitive": 3}


def vendor_save(tenant: str, vid: str = "", name: str = "", service: str = "", data_level: str = "internal",
                answers: dict | None = None, note: str = "") -> dict[str, Any]:
    if data_level not in DATA_LEVEL:
        raise ProgramError("Data is none, internal, personal or sensitive.")
    ans = {k: v for k, v in (answers or {}).items() if k in {q[0] for q in VENDOR_Q} and v in ("yes", "no", "unknown")}
    mx = sum(q[2] for q in VENDOR_Q)
    got = sum(q[2] for q in VENDOR_Q if ans.get(q[0]) == "yes")
    score = round(100 * got / mx)
    lvl = DATA_LEVEL[data_level]
    tier = "high" if (lvl >= 2 and score < 60) or (lvl == 3 and score < 75) else "medium" if score < 75 or lvl >= 2 else "low"
    gaps = [{"id": q[0], "say": q[1], "a": ans.get(q[0], "unknown")} for q in VENDOR_Q if ans.get(q[0]) != "yes"]
    nxt = (_now() + timedelta(days=180 if tier == "high" else 365 if tier == "medium" else 730)).date().isoformat()
    with session() as s:
        if vid:
            d = _get(s, tenant, vid, "vendor")
        else:
            if not name.strip():
                raise ProgramError("Name the vendor.")
            d = CyberDoc(tenant_id=tenant, kind="vendor", ref=_seq(s, tenant, "vendor", "VR"))
            s.add(d)
        if name.strip():
            d.title = name.strip()[:240]
        d.data = json.dumps({"service": service[:200], "data_level": data_level, "answers": ans, "score": score, "tier": tier,
                             "gaps": gaps, "next_review": nxt, "note": note[:500]})
        d.updated_at = _now()
        s.flush()
        ref = d.ref
    return {"vendor": next(v for v in vendors(tenant) if v["ref"] == ref),
            "say": f"{ref} {name or ''}: {score}/100, {tier} risk; review again by {nxt}."}


def vendors(tenant: str) -> list[dict]:
    v = _docs(tenant, "vendor")
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(v, key=lambda x: (order.get(x.get("tier"), 3), x["title"]))


# ---------------------------------------------------------------- 8. playbooks + tabletop exercises
PLAYBOOKS: dict[str, dict[str, Any]] = {
    "ransomware": {"title": "Ransomware", "steps": [
        ("Detect", "Note what you see (ransom note, renamed files) and the time; do not pay or reply."),
        ("Contain", "Pull the network cable / turn off Wi-Fi on affected PCs; do not switch them off (memory has evidence)."),
        ("Contain", "Disconnect backups and shared drives so they are not encrypted too."),
        ("Contain", "Reset passwords of admin and affected users from a clean device."),
        ("Notify", "Start the notification clocks (Incidents) - CERT-In 6 hours in India, others by country."),
        ("Eradicate", "Find how it got in (mail, RDP, old software) with the antivirus / EDR console."),
        ("Recover", "Wipe and rebuild affected PCs; restore from the offline backup; check files before going back."),
        ("Lessons", "Write what will change (MFA, backups, patching) and close the incident.")]},
    "phishing": {"title": "Phishing mail / password typed", "steps": [
        ("Detect", "Check the mail here (Checks > Mail) - never click its links."),
        ("Contain", "If a password was typed: change it now, sign out everywhere, turn on 2-step."),
        ("Contain", "Check the mailbox for new forwarding rules and remove them."),
        ("Contain", "Block the sender / domain in your mail admin."),
        ("Notify", "Warn everyone not to open the same mail; open the incident if a password or money went out."),
        ("Recover", "Watch the account's sign-ins for a week."),
        ("Lessons", "Share the example in the next training.")]},
    "account": {"title": "Account taken over", "steps": [
        ("Detect", "Confirm the strange sign-in / sent mails with the account owner."),
        ("Contain", "Reset the password, sign out all sessions, remove unknown devices and app passwords."),
        ("Contain", "Remove forwarding rules, delegates and OAuth apps you do not know."),
        ("Notify", "Tell people who received mails from the account; start the notification clocks if data was read."),
        ("Recover", "Turn on 2-step; review the account's activity for the last 30 days."),
        ("Lessons", "Find why (reused password, no MFA) and fix it for everyone.")]},
    "lost_device": {"title": "Lost / stolen laptop or phone", "steps": [
        ("Detect", "Note when and where it was last seen; what accounts and data were on it."),
        ("Contain", "Sign the device out of email and cloud accounts; change passwords saved on it."),
        ("Contain", "Ask for a remote lock / wipe card (Hoola makes it; the wipe needs your fingerprint)."),
        ("Notify", "If it was not encrypted and held personal data, start the notification clocks; file a police report."),
        ("Recover", "Issue a new device from a clean setup."),
        ("Lessons", "Make encryption and screen lock required on every device.")]},
    "data_leak": {"title": "Data sent or exposed by mistake", "steps": [
        ("Detect", "Find what data, how many people, who received it, since when."),
        ("Contain", "Ask the receiver to delete it and confirm in writing; remove the public link / file."),
        ("Notify", "Personal data: start the notification clocks for each country."),
        ("Recover", "Check the data is no longer reachable (search engines, shared links)."),
        ("Lessons", "Change the process (sharing settings, a second check before sending).")]},
    "payment_fraud": {"title": "Payment fraud / fake invoice", "steps": [
        ("Detect", "Note the payment details, time and the mail / call that asked for it."),
        ("Contain", "Call your bank's fraud line at once to recall or freeze the payment."),
        ("Contain", "Check the mailbox that sent / received the request for a takeover."),
        ("Notify", "File with the cyber crime police (India: 1930 / cybercrime.gov.in) and your bank."),
        ("Recover", "Confirm vendor bank changes only by a call to a number you already had."),
        ("Lessons", "Set a two-person rule for new payees and bank changes.")]},
    "website": {"title": "Website hacked / defaced", "steps": [
        ("Detect", "Take screenshots; note the time; check Attack surface for exposed files."),
        ("Contain", "Put up a maintenance page; change hosting, admin and database passwords."),
        ("Eradicate", "Restore a clean copy; update the CMS, plugins and themes."),
        ("Notify", "If customer data was stored, start the notification clocks."),
        ("Lessons", "Turn on 2-step for the admin; remove unused plugins.")]},
    "ddos": {"title": "Site down from an attack (DDoS)", "steps": [
        ("Detect", "Confirm with your host / Cloudflare that traffic is the cause."),
        ("Contain", "Turn on your provider's attack mode / rate limits; ask Hoola for IP block cards for clear sources."),
        ("Notify", "Tell customers on another channel the site is being fixed."),
        ("Recover", "Lower the protection step by step once traffic is normal."),
        ("Lessons", "Keep the provider's DDoS settings ready; know the support number.")]},
}


def playbook(pid: str) -> dict[str, Any]:
    p = PLAYBOOKS.get(pid)
    if not p:
        raise ProgramError("Unknown playbook.")
    return {"id": pid, "title": p["title"], "steps": [{"phase": a, "text": b} for a, b in p["steps"]],
            "note": "You and your team do these steps. Hoola makes cards for blocks / wipes and keeps the incident note."}


def tabletop_start(tenant: str, pid: str, people: str = "") -> dict[str, Any]:
    p = playbook(pid)
    with session() as s:
        d = CyberDoc(tenant_id=tenant, kind="tabletop", ref=_seq(s, tenant, "tabletop", "TT"), title=f"Practice: {p['title']}",
                     data=json.dumps({"playbook": pid, "people": people[:300], "steps": [{**x, "ok": None, "note": ""} for x in p["steps"]],
                                      "lessons": "", "minutes": None}))
        s.add(d)
        s.flush()
        did, ref = d.id, d.ref
    return {"tabletop": next(t for t in tabletops(tenant) if t["id"] == did), "say": f"{ref} started: walk each step and mark it."}


def tabletop_step(tenant: str, tid: str, i: int, ok: bool | None, note: str = "") -> dict[str, Any]:
    with session() as s:
        d = _get(s, tenant, tid, "tabletop")
        x = _j(d.data, {})
        if not 0 <= int(i) < len(x["steps"]):
            raise ProgramError("No such step.")
        x["steps"][int(i)]["ok"] = ok
        x["steps"][int(i)]["note"] = str(note or "")[:300]
        d.data = json.dumps(x)
        d.updated_at = _now()
    return {"tabletop": next(t for t in tabletops(tenant) if t["id"] == tid), "say": "Step saved."}


def tabletop_finish(tenant: str, tid: str, lessons: str, minutes: int | None = None) -> dict[str, Any]:
    if not (lessons or "").strip():
        raise ProgramError("Write what you learned before closing the exercise.")
    with session() as s:
        d = _get(s, tenant, tid, "tabletop")
        x = _j(d.data, {})
        x["lessons"], x["minutes"] = lessons[:2000], minutes
        d.data, d.status, d.updated_at = json.dumps(x), "done", _now()
    t = next(t for t in tabletops(tenant) if t["id"] == tid)
    return {"tabletop": t, "say": f"{t['ref']} done: {t['ready']} of {t['total']} steps you could do."}


def tabletops(tenant: str) -> list[dict]:
    out = []
    for t in _docs(tenant, "tabletop"):
        st = t.get("steps", [])
        t["total"], t["ready"] = len(st), sum(1 for x in st if x.get("ok") is True)
        t["gaps"] = sum(1 for x in st if x.get("ok") is False)
        out.append(t)
    return out


# ---------------------------------------------------------------- 9. awareness training
TOPICS = [("phishing", "Spotting phishing mails and fake links"), ("passwords", "Passwords, a password manager and 2-step"),
          ("payments", "Fake invoices and bank-change requests"), ("devices", "Locking and updating devices"),
          ("wifi", "Public Wi-Fi and working away"), ("data", "Sharing customer data safely"),
          ("social", "Calls and messages pretending to be the boss"), ("usb", "USB drives and downloads"),
          ("report", "How to report something odd fast"), ("ai", "What not to paste into AI tools")]
QUIZ = [
    ("A mail from 'your CEO' asks you to buy gift cards urgently. What do you do?", "Call the CEO on the number you already have before doing anything."),
    ("Your bank texts a link to 'update KYC'. Safe to click?", "No - open the bank's app or site yourself."),
    ("A vendor mails new bank details for payment. What do you do?", "Confirm by phone on a number you already had, never the one in the mail."),
    ("Is it fine to reuse one strong password for work and personal?", "No - use a password manager and a different password for each."),
    ("Someone calls from 'IT' asking for your OTP. Do you give it?", "Never - no real IT team asks for an OTP."),
    ("You clicked a strange link and typed your password. First step?", "Change the password from a clean device and tell the security lead now."),
    ("You find a USB drive in the parking lot. What do you do?", "Do not plug it in - hand it to IT."),
    ("Can you paste a customer's details into a public AI chat?", "No - customer data stays in approved tools."),
]


def training_record(tenant: str, person: str, topic: str, when: str = "") -> dict[str, Any]:
    if topic not in dict(TOPICS):
        raise ProgramError("Unknown topic.")
    if not (person or "").strip():
        raise ProgramError("Name the person.")
    day = (when or _now().date().isoformat())[:10]
    with session() as s:
        d = _doc_s(s, tenant, "training")
        if d is None:
            d = CyberDoc(tenant_id=tenant, kind="training", title="Training records")
            s.add(d)
        x = _j(d.data, {})
        rows = x.get("rows", [])
        rows = [r for r in rows if not (r["person"].lower() == person.strip().lower() and r["topic"] == topic)]
        rows.append({"person": person.strip()[:80], "topic": topic, "day": day})
        x["rows"] = rows[-5000:]
        d.data, d.updated_at = json.dumps(x), _now()
    return {**training_view(tenant), "say": f"Saved: {person.strip()} - {dict(TOPICS)[topic]}."}


def training_view(tenant: str) -> dict[str, Any]:
    d = _doc(tenant, "training")
    rows = _j(d.data, {}).get("rows", []) if d else []
    year_ago = (_now() - timedelta(days=365)).date().isoformat()
    people = sorted({r["person"] for r in rows})
    cov = []
    for k, t in TOPICS:
        done = {r["person"] for r in rows if r["topic"] == k and r["day"] >= year_ago}
        cov.append({"topic": k, "title": t, "done": len(done), "of": len(people),
                    "pct": round(100 * len(done) / len(people)) if people else None})
    per = [{"person": p, "done": sum(1 for r in rows if r["person"] == p and r["day"] >= year_ago), "of": len(TOPICS)} for p in people]
    return {"topics": cov, "people": per, "quiz": [{"q": q, "a": a} for q, a in QUIZ],
            "plan": [{"month": i + 1, "topic": t} for i, (_k, t) in enumerate(TOPICS)]}


# ---------------------------------------------------------------- 10. password policy (NIST SP 800-63B)
def policy_check(tenant: str, min_length: int = 8, mfa: str = "some", rotation_days: int = 0, composition: bool = False,
                 lockout: int = 0, breached_check: bool = False, manager: bool = False) -> dict[str, Any]:
    f = []
    ml = int(min_length or 0)
    if ml < 8:
        f.append(("high", f"Minimum length {ml} is too short.", "Require at least 8 characters, 15 where there is no 2-step."))
    elif ml < 15 and mfa != "all":
        f.append(("medium", f"Minimum length {ml} without 2-step for everyone.", "Use 15+ characters, or 2-step for everyone."))
    if mfa == "none":
        f.append(("high", "No 2-step sign-in.", "Turn on 2-step for every account, admins first."))
    elif mfa == "some":
        f.append(("medium", "2-step only for some accounts.", "Make 2-step required for everyone."))
    if rotation_days and int(rotation_days) < 365:
        f.append(("low", f"Passwords must change every {rotation_days} days.", "NIST says do not force regular changes; change only after a leak."))
    if composition:
        f.append(("low", "Forced mixes of symbols / numbers.", "NIST says drop composition rules; length matters more."))
    if not lockout:
        f.append(("medium", "No limit on wrong attempts.", "Lock or slow down after about 10 wrong attempts."))
    if not breached_check:
        f.append(("medium", "New passwords are not checked against leaked lists.", "Block passwords found in breaches (most identity providers can)."))
    if not manager:
        f.append(("low", "No password manager for staff.", "Give everyone a password manager."))
    score = max(0, 100 - sum({"high": 30, "medium": 15, "low": 5}[a] for a, _b, _c in f))
    data = {"min_length": ml, "mfa": mfa, "rotation_days": int(rotation_days or 0), "composition": bool(composition), "lockout": int(lockout or 0),
            "breached_check": bool(breached_check), "manager": bool(manager), "score": score,
            "findings": [{"level": a, "say": b, "fix": c} for a, b, c in f]}
    with session() as s:
        d = _doc_s(s, tenant, "policy")
        if d is None:
            d = CyberDoc(tenant_id=tenant, kind="policy", title="Password policy")
            s.add(d)
        d.data, d.updated_at = json.dumps(data), _now()
    return {**data, "source": "NIST SP 800-63B", "say": f"Password policy: {score}/100, {len(f)} thing(s) to change."}


def policy_view(tenant: str) -> dict[str, Any]:
    d = _doc(tenant, "policy")
    return _j(d.data, {}) if d else {}


# ---------------------------------------------------------------- the programme at a glance
def overview(tenant: str) -> dict[str, Any]:
    c = controls_view(tenant)
    ac = _docs(tenant, "access")
    last_ac = ac[0] if ac else None
    pol = policy_view(tenant)
    rk = risks(tenant)
    vd = vendors(tenant)
    tt = tabletops(tenant)
    tr = training_view(tenant)
    sc = _docs(tenant, "secrets")[:10]
    parts = []
    if c["score"] is not None:
        parts.append(("Controls", c["score"]))
    if pol:
        parts.append(("Password policy", pol.get("score")))
    if last_ac and last_ac["summary"].get("mfa_pct") is not None:
        parts.append(("2-step coverage", last_ac["summary"]["mfa_pct"]))
    tpct = [t["pct"] for t in tr["topics"] if t["pct"] is not None]
    if tpct:
        parts.append(("Training", round(sum(tpct) / len(tpct))))
    return {"controls": c, "access": ac[:12], "policy": pol, "risks": rk, "vendors": vd, "tabletops": tt, "training": tr, "secrets": sc,
            "parts": parts, "playbooks": [{"id": k, "title": v["title"], "steps": len(v["steps"])} for k, v in PLAYBOOKS.items()],
            "vendor_q": [{"id": a, "q": b} for a, b, _w in VENDOR_Q], "topics": [{"id": a, "title": b} for a, b in TOPICS]}

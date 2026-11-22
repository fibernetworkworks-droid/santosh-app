"""v0.999.117 ULTIMATE PC PLAN P7 - portals and hard sites, for every country (docs/HOOLA_ULTIMATE_PC_PLAN.md).

1. SITES THAT REFUSE CLOUD COMPUTERS. Some government sites drop or block any visit from a data centre (seen in the
   exams: parivahan.gov.in, bizfile.gov.sg, epfindia.gov.in, sometimes u.ae). On Hoola PC such a site is said at once
   (no minutes of waiting) and the job is pointed at HER PC (pc_do), which sits on a home / office connection. The list
   = a starter list + what Hoola PC learns: a 403 / CloudFront 'request blocked' / a page that never loads is remembered
   for 14 days (data/pc_portals.json, host + why + times seen).
2. NATIONAL LOGINS. A country's own sign-in (Login.gov, GOV.UK One Login, ID.me, BankID, DigiD, FranceConnect, SPID,
   itsme, UAE Pass, Singpass, DigiLocker / Meri Pehchaan, myID, GCKey, Nafath ...) is HERS: Hoola never types in it and
   the private sign-in form is not for it either - it asks her to Take control and sign in (they need her phone, app,
   passkey or face), then carries on.
The CAPTCHA and OTP hand-offs stay as they are (ask_approval for a CAPTCHA read, ask_otp for a code)."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

LEARN_DAYS = 14

# starter list: sites seen refusing a cloud computer in Hoola's own exams / runs (country, what was seen)
CLOUD_BLOCKED = {
    "parivahan.gov.in": ("IN", "drops cloud servers (no page, 13 Nov + every exam)"),
    "bizfile.gov.sg": ("SG", "CloudFront 403 'Request blocked' (portal exams 22 Nov)"),
    "epfindia.gov.in": ("IN", "CloudFront 403 / blank page (portal exams 22 Nov)"),
}

# national / government sign-ins: host suffix -> (name, country)
NATIONAL_LOGINS = {
    "login.gov": ("Login.gov", "US"), "id.me": ("ID.me", "US"),
    "account.gov.uk": ("GOV.UK One Login", "UK"), "access.service.gov.uk": ("Government Gateway", "UK"),
    "digid.nl": ("DigiD", "NL"), "franceconnect.gouv.fr": ("FranceConnect", "FR"), "spid.gov.it": ("SPID", "IT"),
    "itsme-id.com": ("itsme", "BE"), "bankid.com": ("BankID", "SE"), "bankid.no": ("BankID", "NO"),
    "mitid.dk": ("MitID", "DK"), "ausweisapp.bund.de": ("eID (AusweisApp)", "DE"), "eidas.ec.europa.eu": ("eIDAS", "EU"),
    "uaepass.ae": ("UAE Pass", "AE"), "iam.gov.sa": ("Nafath", "SA"), "singpass.gov.sg": ("Singpass", "SG"),
    "digilocker.gov.in": ("DigiLocker", "IN"), "meripehchaan.gov.in": ("Meri Pehchaan / e-Pramaan", "IN"),
    "epramaan.gov.in": ("e-Pramaan", "IN"), "myid.gov.au": ("myID", "AU"), "my.gov.au": ("myGov", "AU"),
    "clegc-gckey.gc.ca": ("GCKey", "CA"), "mydigitalid.gov.my": ("MyDigital ID", "MY"), "egov.ph": ("eGovPH", "PH"),
    "gov.br": ("gov.br", "BR"), "nida.go.tz": ("NIDA", "TZ"), "ecitizen.go.ke": ("eCitizen", "KE"),
}

_BLOCK_WORDS = re.compile(r"request could not be satisfied|request blocked|access denied|403 forbidden|\b403 error\b|"
                          r"you don't have permission to access|blocked by (the )?(site|security)|error 1020", re.I)
_lock = threading.Lock()


def _file() -> Path:
    return Path(os.environ.get("PC_PORTALS_FILE", "data/pc_portals.json"))


def host_of(url: str) -> str:
    try:
        h = (urlparse(str(url or "") if "://" in str(url or "") else "https://" + str(url or "")).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _match(host: str, table: dict) -> str:
    for k in table:
        if host == k or host.endswith("." + k):
            return k
    return ""


def _learned() -> dict:
    try:
        return json.loads(_file().read_text())
    except (OSError, ValueError):
        return {}


def blocked_for_cloud(url: str) -> str:
    """Why this site refuses cloud computers (starter list or learned in the last 14 days), else ''."""
    h = host_of(url)
    k = _match(h, CLOUD_BLOCKED)
    if k:
        return CLOUD_BLOCKED[k][1]
    for site, v in _learned().items():
        if (h == site or h.endswith("." + site)) and time.time() - float(v.get("last") or 0) < LEARN_DAYS * 86400 \
                and int(v.get("count") or 0) >= 1:
            return f"refused a cloud computer {v.get('count')} time(s), last {v.get('why', '')}"
    return ""


def looks_blocked(problem: str, text: str) -> bool:
    return str(problem or "") in ("blocked", "no_page") or bool(_BLOCK_WORDS.search(str(text or "")[:1500]))


def learn(url: str, why: str) -> None:
    """Hoola PC was refused by this site: remember it (registrable part of the host)."""
    h = host_of(url)
    if not h:
        return
    parts = h.split(".")
    site = ".".join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ("gov", "co", "nic", "org", "ac", "go", "gc") else ".".join(parts[-2:])
    with _lock:
        d = _learned()
        v = d.get(site) or {"count": 0}
        v.update(count=int(v.get("count") or 0) + 1, last=time.time(), why=str(why or "")[:120])
        d[site] = v
        _file().parent.mkdir(parents=True, exist_ok=True)
        _file().write_text(json.dumps(d, indent=1))


def national_login(url: str) -> tuple[str, str] | None:
    k = _match(host_of(url), NATIONAL_LOGINS)
    return NATIONAL_LOGINS[k] if k else None


def login_note(url: str) -> str:
    nl = national_login(url)
    if not nl:
        return ""
    return (f"\nNATIONAL LOGIN ({nl[0]}, {nl[1]}): this sign-in is HERS - never type in it, and ask_login is not for it "
            "either (it needs her phone, app, passkey or face). ask_user her to press Take control and sign in, then "
            "carry on from the page she lands on.")


def cloud_refusal(url: str, why: str) -> str:
    return (f"NOT OPENED on Hoola PC: {host_of(url)} refuses cloud computers ({why}). Do not retry here. Finish with "
            "done(success=false) saying this job needs HER own PC (a home / office connection): Hoola can do it there "
            "(pc_do) when her PC is on.")

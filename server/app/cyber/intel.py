"""Official API clients for the Cyber Suraksha Sahayak (her own keys only, read-only lookups, except the Cloudflare IP rule
that runs only after her tap). Nothing here ever opens a suspicious link or uploads her file.

- Google Cloud Web Risk  GET https://webrisk.googleapis.com/v1/uris:search?uri=..&threatTypes=..&key=..   (commercial use)
- Google Safe Browsing   GET https://safebrowsing.googleapis.com/v5/urls:search?urls=..&key=..           (non-commercial only)
- VirusTotal v3          GET https://www.virustotal.com/api/v3/files/{sha256}  / urls/{id}  header x-apikey (lookup only)
- Have I Been Pwned v3   GET https://haveibeenpwned.com/api/v3/breacheddomain/{d} | breachedaccount/{e}  header hibp-api-key
- NVD CVE API 2.0        GET https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=..&pubStartDate=..  header apiKey
- CISA KEV               GET https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
- CERT-In advisories     RSS / Atom at CYBER_CERTIN_FEED (set on the VPS; not verified from the sandbox)
- Cloudflare v4          POST/DELETE /zones/{zone}/firewall/access_rules/rules   (IP block; her token, her tap)
`set_transport` lets tests plug an httpx.MockTransport in.
"""
from __future__ import annotations

import base64
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

UA = "HoolaCyberSahayak/1.0 (+https://ainewtika.com)"
_TRANSPORT: httpx.BaseTransport | None = None


class IntelError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _get(url: str, params: Any = None, headers: dict[str, str] | None = None, timeout: float = 15) -> httpx.Response:
    try:
        with httpx.Client(timeout=timeout, transport=_TRANSPORT, follow_redirects=False) as c:
            return c.get(url, params=params, headers={"User-Agent": UA, **(headers or {})})
    except httpx.HTTPError as e:
        raise IntelError(f"{httpx.URL(url).host} tak nahi pahunch paya ({e.__class__.__name__}).")


def _status_err(r: httpx.Response, who: str) -> None:
    if r.status_code in (401, 403):
        raise IntelError(f"{who} ne key mana ki ({r.status_code}): key / permission dekhiye.")
    if r.status_code == 429:
        raise IntelError(f"{who}: bahut zyada sawal (limit). Thodi der baad.")
    if r.status_code >= 400:
        raise IntelError(f"{who}: {r.status_code}")


# ---------------------------------------------------------------- link reputation
THREATS = ("MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE")


def webrisk(url: str, key: str) -> dict[str, Any]:
    r = _get("https://webrisk.googleapis.com/v1/uris:search", params=[("uri", url), *[("threatTypes", t) for t in THREATS], ("key", key)])
    _status_err(r, "Google Web Risk")
    th = (r.json() or {}).get("threat") or {}
    types = list(th.get("threatTypes") or [])
    return {"provider": "webrisk", "bad": bool(types), "threats": types}


def safebrowsing(urls: list[str], key: str) -> dict[str, list[str]]:
    r = _get("https://safebrowsing.googleapis.com/v5/urls:search", params=[*[("urls", u) for u in urls[:50]], ("key", key)])
    _status_err(r, "Google Safe Browsing")
    out: dict[str, list[str]] = {}
    for t in (r.json() or {}).get("threats") or []:
        out.setdefault(str(t.get("url") or ""), []).extend(t.get("threatTypes") or [])
    return out


def vt_url(url: str, key: str) -> dict[str, Any]:
    vid = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    r = _get(f"https://www.virustotal.com/api/v3/urls/{vid}", headers={"x-apikey": key})
    if r.status_code == 404:
        return {"provider": "virustotal", "known": False}
    _status_err(r, "VirusTotal")
    st = (((r.json() or {}).get("data") or {}).get("attributes") or {}).get("last_analysis_stats") or {}
    return {"provider": "virustotal", "known": True, "malicious": int(st.get("malicious") or 0), "suspicious": int(st.get("suspicious") or 0),
            "harmless": int(st.get("harmless") or 0), "undetected": int(st.get("undetected") or 0)}


def vt_file(sha256: str, key: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}|[0-9a-f]{40}|[0-9a-f]{32}", sha256 or ""):
        raise IntelError("Hash sahi nahi (sha256 / sha1 / md5).")
    r = _get(f"https://www.virustotal.com/api/v3/files/{sha256}", headers={"x-apikey": key})
    if r.status_code == 404:
        return {"provider": "virustotal", "known": False}
    _status_err(r, "VirusTotal")
    at = ((r.json() or {}).get("data") or {}).get("attributes") or {}
    st = at.get("last_analysis_stats") or {}
    return {"provider": "virustotal", "known": True, "malicious": int(st.get("malicious") or 0), "suspicious": int(st.get("suspicious") or 0),
            "harmless": int(st.get("harmless") or 0), "undetected": int(st.get("undetected") or 0),
            "name": str(at.get("meaningful_name") or "")[:120], "label": str((at.get("popular_threat_classification") or {}).get("suggested_threat_label") or "")[:80]}


# ---------------------------------------------------------------- breaches (HIBP)
def hibp_domain(domain: str, key: str) -> dict[str, list[str]]:
    r = _get(f"https://haveibeenpwned.com/api/v3/breacheddomain/{quote(domain)}", headers={"hibp-api-key": key})
    if r.status_code == 404:
        return {}
    if r.status_code == 403:
        raise IntelError("HIBP: yeh domain aapke HIBP account par verify nahi hai (haveibeenpwned.com > Domain search mein verify kijiye).")
    _status_err(r, "Have I Been Pwned")
    j = r.json() or {}
    return {str(k): [str(x) for x in (v or [])] for k, v in j.items()}


def hibp_account(email: str, key: str) -> list[str]:
    r = _get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}", params={"truncateResponse": "true"},
             headers={"hibp-api-key": key})
    if r.status_code == 404:
        return []
    _status_err(r, "Have I Been Pwned")
    return [str(b.get("Name") or "") for b in (r.json() or [])]


def hibp_breach(name: str) -> dict[str, Any]:
    """Public, no key: what a breach leaked and when."""
    r = _get(f"https://haveibeenpwned.com/api/v3/breach/{quote(name)}")
    if r.status_code >= 400:
        return {"Name": name}
    j = r.json() or {}
    return {"Name": name, "Title": j.get("Title") or name, "BreachDate": j.get("BreachDate") or "", "DataClasses": j.get("DataClasses") or []}


# ---------------------------------------------------------------- advisories
def nvd(keyword: str = "", cpe: str = "", days: int = 30, key: str = "") -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=min(max(days, 1), 120))           # NVD allows up to 120 days in one range
    f = "%Y-%m-%dT%H:%M:%S.000"
    params: dict[str, Any] = {"pubStartDate": start.strftime(f), "pubEndDate": end.strftime(f), "resultsPerPage": 50}
    if cpe:
        params["virtualMatchString"] = cpe
    elif keyword:
        params["keywordSearch"] = keyword
    else:
        return []
    r = _get(os.environ.get("CYBER_NVD_URL") or "https://services.nvd.nist.gov/rest/json/cves/2.0", params=params,
             headers={"apiKey": key} if key else None, timeout=30)
    _status_err(r, "NVD")
    out = []
    for v in (r.json() or {}).get("vulnerabilities") or []:
        c = v.get("cve") or {}
        desc = next((d.get("value") for d in c.get("descriptions") or [] if d.get("lang") == "en"), "")
        m = c.get("metrics") or {}
        sc, sev = 0.0, ""
        for k in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if m.get(k):
                d = (m[k][0] or {}).get("cvssData") or {}
                sc = float(d.get("baseScore") or 0)
                sev = str(d.get("baseSeverity") or (m[k][0] or {}).get("baseSeverity") or "")
                break
        out.append({"id": c.get("id") or "", "summary": str(desc)[:600], "score": sc, "severity": sev.upper(),
                    "published": str(c.get("published") or "")[:19], "url": f"https://nvd.nist.gov/vuln/detail/{c.get('id')}"})
    return out


def kev() -> list[dict[str, Any]]:
    r = _get(os.environ.get("CYBER_KEV_URL") or "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", timeout=30)
    _status_err(r, "CISA KEV")
    return list((r.json() or {}).get("vulnerabilities") or [])


def certin_feed() -> list[dict[str, str]]:
    url = os.environ.get("CYBER_CERTIN_FEED", "").strip()
    if not url:
        return []
    r = _get(url, timeout=30)
    _status_err(r, "CERT-In")
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        raise IntelError("CERT-In feed samajh nahi aaya.")
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        get = {c.tag.split("}")[-1]: (c.text or c.get("href") or "") for c in it}
        out.append({"title": str(get.get("title") or "")[:300], "link": str(get.get("link") or get.get("id") or "")[:400],
                    "summary": re.sub(r"<[^>]+>", " ", str(get.get("description") or get.get("summary") or ""))[:800],
                    "published": str(get.get("pubDate") or get.get("updated") or "")[:40]})
    return out[:200]


# ---------------------------------------------------------------- Cloudflare (her zone, her token, her tap)
def _cf_base() -> str:
    return (os.environ.get("CF_API_BASE") or "https://api.cloudflare.com/client/v4").rstrip("/")


def _cf(method: str, path: str, token: str, json: Any = None) -> Any:
    try:
        with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
            r = c.request(method, _cf_base() + path, json=json, headers={"Authorization": f"Bearer {token}", "User-Agent": UA})
    except httpx.HTTPError as e:
        raise IntelError(f"Cloudflare tak nahi pahunch paya: {e.__class__.__name__}")
    try:
        body = r.json()
    except ValueError:
        raise IntelError(f"Cloudflare ka jawab samajh nahi aaya ({r.status_code}).")
    if r.status_code >= 400 or not body.get("success", False):
        errs = "; ".join(f"{e.get('code')}: {e.get('message')}" for e in body.get("errors") or []) or str(r.status_code)
        raise IntelError(f"Cloudflare: {errs}")
    return body.get("result")


def cf_block_ip(token: str, zone: str, ip: str, note: str) -> dict[str, Any]:
    target = "ip6" if ":" in ip else ("ip_range" if "/" in ip else "ip")
    res = _cf("POST", f"/zones/{zone}/firewall/access_rules/rules", token,
              {"mode": "block", "configuration": {"target": target, "value": ip}, "notes": note[:200]}) or {}
    return {"rule_id": res.get("id") or "", "mode": res.get("mode") or "block"}


def cf_unblock(token: str, zone: str, rule_id: str) -> None:
    _cf("DELETE", f"/zones/{zone}/firewall/access_rules/rules/{rule_id}", token)


def cf_verify(token: str) -> dict[str, Any]:
    return _cf("GET", "/user/tokens/verify", token) or {}

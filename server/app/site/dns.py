"""v0.122 DNS management for her domain: read what is there, plan only the changes a job needs (website / email /
verification), show "before -> after" in plain words, apply ONLY on her tap through her own Cloudflare zone (official API),
snapshot first so any change can be undone, then check from 3 public resolvers (Cloudflare, Google, Quad9 DNS-over-HTTPS).
Rules in code: never delete MX / TXT she already uses, never two SPF records, never break mail for the website."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select

from ..db import session
from .hosting_models import SiteDnsPlan, SiteHostingKey

log = logging.getLogger("santosh.site")

RESOLVERS = [("Cloudflare", "https://cloudflare-dns.com/dns-query"), ("Google", "https://dns.google/resolve"),
             ("Quad9", "https://dns.quad9.net:5053/dns-query")]
TYPE_NUM = {1: "A", 5: "CNAME", 15: "MX", 16: "TXT", 28: "AAAA", 2: "NS", 257: "CAA", 6: "SOA"}
_TRANSPORT: httpx.BaseTransport | None = None
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")

EMAIL_PRESETS: dict[str, dict[str, Any]] = {
    "google": {"label": "Google Workspace", "mx": [("smtp.google.com", 1)], "spf": "include:_spf.google.com"},
    "zoho": {"label": "Zoho Mail (India)", "mx": [("mx.zoho.in", 10), ("mx2.zoho.in", 20), ("mx3.zoho.in", 50)],
             "spf": "include:zoho.in"},
}


class DnsError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def norm_domain(d: str) -> str:
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0].split(":")[0].strip(".")
    if d.startswith("www."):
        d = d[4:]
    try:
        d = d.encode("idna").decode()
    except UnicodeError:
        pass
    if not DOMAIN_RE.match(d):
        raise DnsError(f"'{d}' sahi domain nahi lagta (jaise sharmasweets.in).")
    return d


# ---------------------------------------------------------------- reading the world (DoH)
def lookup(name: str, type_: str = "A") -> dict[str, list[str]]:
    """{resolver: [answers]} from 3 public resolvers (each may be [] or ['?'] when it could not be asked)."""
    out: dict[str, list[str]] = {}
    for label, url in RESOLVERS:
        try:
            with httpx.Client(timeout=8, transport=_TRANSPORT) as c:
                r = c.get(url, params={"name": name, "type": type_}, headers={"accept": "application/dns-json"})
            j = r.json()
            want = type_.upper()
            out[label] = [str(a.get("data", "")).rstrip(".").strip('"') for a in j.get("Answer") or []
                          if TYPE_NUM.get(a.get("type"), "") == want]
        except Exception:
            out[label] = ["?"]
    return out


def seen_everywhere(name: str, type_: str, want: str) -> dict[str, Any]:
    res = lookup(name, type_)
    want_l = want.lower().rstrip(".")
    ok = {k: any(want_l in x.lower() for x in v) for k, v in res.items()}
    asked = [k for k, v in res.items() if v != ["?"]]
    return {"name": name, "type": type_, "want": want, "by": ok, "seen": sum(ok.values()), "asked": len(asked),
            "all": bool(asked) and all(ok[k] for k in asked)}


# ---------------------------------------------------------------- her provider
def key(tenant: str, provider: str) -> tuple[str, str]:
    from ..bazar.security import vault
    with session() as s:
        k = s.scalars(select(SiteHostingKey).where(SiteHostingKey.tenant_id == tenant, SiteHostingKey.provider == provider)
                      .order_by(SiteHostingKey.created_at.desc())).first()
        if not k:
            return "", ""
        try:
            return vault().open(k.sealed), (vault().open(k.sealed2) if k.sealed2 else "")
        except ValueError:
            return "", ""


def set_key(tenant: str, provider: str, token: str, secret2: str = "") -> dict[str, Any]:
    from ..bazar.security import vault
    token = (token or "").strip()
    if provider not in ("cloudflare", "porkbun", "cf_registrar", "github"):
        raise DnsError("Provider cloudflare, cf_registrar, porkbun ya github.")
    if len(token) < 20:
        raise DnsError("Yeh token adhoora lagta hai.")
    secret2 = (secret2 or "").strip()
    label = ""
    if provider == "porkbun":
        if len(secret2) < 20:
            raise DnsError("Porkbun ke liye API key + Secret API key dono chahiye.")
        from .domains import DomainError, Porkbun
        try:
            Porkbun(token, secret2).ping()
        except DomainError as e:
            raise DnsError(str(e))
        label = f"key …{token[-4:]}"
    if provider == "github":
        from .github import Gh, GithubError
        try:
            label = "@" + str(Gh(token).me().get("login") or "?")
        except GithubError as e:
            raise DnsError(str(e))
    if provider == "cf_registrar":
        if not re.fullmatch(r"[0-9a-f]{32}", secret2):
            raise DnsError("Cloudflare Registrar ke liye token + Account ID (32 akshar) chahiye.")
    if provider in ("cloudflare", "cf_registrar"):
        from .cf import CfError, Cloudflare
        try:
            info = Cloudflare(token).verify()
        except CfError as e:
            raise DnsError(str(e))
        if (info or {}).get("status") != "active":
            raise DnsError("Cloudflare token active nahi hai.")
        label = f"token …{token[-4:]}"
    with session() as s:
        for old in s.scalars(select(SiteHostingKey).where(SiteHostingKey.tenant_id == tenant,
                                                          SiteHostingKey.provider == provider)).all():
            s.delete(old)
        s.add(SiteHostingKey(tenant_id=tenant, provider=provider, sealed=vault().seal(token),
                             sealed2=vault().seal(secret2) if secret2 else "", label=label, verified=True))
    return {"ok": True, "provider": provider, "label": label, "say": f"{provider.title()} jud gaya ({label}). Token kahin dikhaya nahi jayega."}


def forget_key(tenant: str, provider: str) -> dict[str, Any]:
    with session() as s:
        for k in s.scalars(select(SiteHostingKey).where(SiteHostingKey.tenant_id == tenant, SiteHostingKey.provider == provider)).all():
            s.delete(k)
    where = {"github": "GitHub settings", "porkbun": "Porkbun API Access"}.get(provider, "Cloudflare dashboard")
    return {"ok": True, "say": f"{provider.title()} ka token hata diya. {where} mein bhi token delete kar dijiye."}


def keys(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [{"provider": k.provider, "label": k.label, "verified": k.verified,
                 "at": k.created_at.isoformat() if k.created_at else ""}
                for k in s.scalars(select(SiteHostingKey).where(SiteHostingKey.tenant_id == tenant)).all()]


def where_is(tenant: str, domain: str) -> dict[str, Any]:
    """Which provider can change this domain's DNS for her: her Cloudflare zone, or manual (her registrar's page)."""
    tok, _ = key(tenant, "cloudflare")
    if tok:
        from .cf import CfError, Cloudflare
        try:
            z = Cloudflare(tok).zone_for(domain)
            if z:
                return {"provider": "cloudflare", "zone": z["id"], "zone_name": z.get("name"),
                        "nameservers": z.get("name_servers") or [], "status": z.get("status")}
        except CfError as e:
            return {"provider": "manual", "why": str(e)}
    z = _hoola_zone(tenant, domain)
    if z:
        return z
    pk, ps = key(tenant, "porkbun")
    if pk and ps:
        from .domains import DomainError, Porkbun
        try:
            Porkbun(pk, ps).dns_records(domain)
            return {"provider": "porkbun", "zone": domain, "zone_name": domain, "nameservers": []}
        except DomainError:
            pass
    ns = lookup(domain, "NS")
    names = sorted({x for v in ns.values() for x in v if x != "?"})
    return {"provider": "manual", "nameservers": names}


HOOLA_CF = "hoola_cf"       # v0.280 a domain she bought through Hoola on Newtika's Cloudflare account: Newtika's token


def _hoola_token() -> str:
    from ..config import get_settings
    return getattr(get_settings(), "sites_reg_cf_token", "") or ""


def _hoola_zone(tenant: str, domain: str) -> dict[str, Any] | None:
    """v0.280 the zone of a domain SHE bought through Hoola on Newtika's Cloudflare Registrar account. She has no login
    there, so before this the DNS card could only say "do it yourself" and the domain could never reach her site."""
    tok = _hoola_token()
    if not tok:
        return None
    from .domains import SiteDomain
    with session() as s:
        o = s.scalars(select(SiteDomain).where(SiteDomain.tenant_id == tenant, SiteDomain.domain == domain,
                                               SiteDomain.account == "hoola", SiteDomain.registrar == "cloudflare",
                                               SiteDomain.status.in_(("registering", "registered", "kyc")))).first()
    if o is None:
        return None
    from .cf import CfError, Cloudflare
    try:
        z = Cloudflare(tok).zone_for(domain)
    except CfError as e:
        log.info("newtika zone for %s: %s", domain, e)
        return None
    if not z:
        return None
    return {"provider": HOOLA_CF, "zone": z["id"], "zone_name": z.get("name"), "nameservers": z.get("name_servers") or [],
            "status": z.get("status")}


def can_apply(provider: str) -> bool:
    return provider in ("cloudflare", "porkbun", HOOLA_CF)


class _PorkbunZone:
    """The same four calls as the Cloudflare client, on Porkbun's official DNS API (zone = the domain)."""

    def __init__(self, pb):
        self.pb = pb

    @staticmethod
    def _sub(zone: str, name: str) -> str:
        n = (name or "").lower().rstrip(".")
        return "" if n == zone else n[:-len(zone) - 1] if n.endswith("." + zone) else n

    @staticmethod
    def _type(zone: str, c: dict) -> str:
        return "ALIAS" if c["type"] == "CNAME" and (c["name"] or "").rstrip(".") == zone else c["type"]

    def records(self, zone: str) -> list[dict[str, Any]]:
        out = []
        for r in self.pb.dns_records(zone):
            t = "CNAME" if r.get("type") == "ALIAS" else r.get("type")
            out.append({"id": str(r.get("id")), "type": t, "name": (r.get("name") or zone).lower(), "content": r.get("content"),
                        "priority": int(r["prio"]) if str(r.get("prio") or "").isdigit() and t == "MX" else None,
                        "proxied": None, "ttl": r.get("ttl")})
        return out

    def create_record(self, zone: str, c: dict) -> dict:
        return {"id": self.pb.dns_create(zone, self._sub(zone, c["name"]), self._type(zone, c), c["content"], c.get("priority"))}

    def update_record(self, zone: str, rid: str, c: dict) -> dict:
        self.pb.dns_edit(zone, rid, self._sub(zone, c["name"]), self._type(zone, c), c["content"], c.get("priority"))
        return {"id": rid}

    def delete_record(self, zone: str, rid: str) -> None:
        self.pb.dns_delete(zone, rid)


def _client(tenant: str, provider: str):
    if provider == "porkbun":
        from .domains import Porkbun
        return _PorkbunZone(Porkbun(*key(tenant, "porkbun")))
    from .cf import Cloudflare
    if provider == HOOLA_CF:
        return Cloudflare(_hoola_token())
    return Cloudflare(key(tenant, "cloudflare")[0])


def zone_records(tenant: str, zone: str, provider: str = "cloudflare") -> list[dict[str, Any]]:
    return [{"id": r.get("id"), "type": r.get("type"), "name": r.get("name"), "content": r.get("content"),
             "priority": r.get("priority"), "proxied": r.get("proxied"), "ttl": r.get("ttl")}
            for r in _client(tenant, provider).records(zone)]


# ---------------------------------------------------------------- planning
def _rec(type_: str, name: str, content: str, why: str, priority: int | None = None, proxied: bool | None = None) -> dict:
    return {"type": type_, "name": name.lower().rstrip("."), "content": content.rstrip(".") if type_ != "TXT" else content,
            "priority": priority, "proxied": proxied, "why": why}


def plan(current: list[dict[str, Any]], desired: list[dict[str, Any]], purpose: str, apex: str = "") -> list[dict[str, Any]]:
    """Smallest safe set of changes. current = her zone's records (with ids); desired = what the job needs."""
    out: list[dict[str, Any]] = []
    cur = [dict(r) for r in current]
    for d in desired:
        same_name = [r for r in cur if (r.get("name") or "").lower().rstrip(".") == d["name"]]
        if d["type"] in ("CNAME", "A", "AAAA"):
            exact = [r for r in same_name if r["type"] == d["type"] and (r.get("content") or "").lower().rstrip(".") == d["content"].lower()]
            if exact and d.get("proxied") is False and exact[0].get("proxied") is True:     # v0.280 orange cloud -> DNS only
                out.append({**d, "op": "update", "id": exact[0].get("id"), "old": {"type": d["type"], "content": d["content"]},
                            "risk": f"{d['name']} Cloudflare proxy (orange cloud) se hatkar seedha (DNS only) hoga"})
                continue
            if exact:
                out.append({**d, "op": "keep", "id": exact[0].get("id"), "risk": ""})
                continue
            clash = [r for r in same_name if r["type"] in ("CNAME", "A", "AAAA")]
            if d["type"] == "CNAME" and d["name"] != apex:      # at the apex Cloudflare flattens, so MX / TXT can stay
                other = [r for r in same_name if r["type"] not in ("CNAME", "A", "AAAA")]
                if other:
                    raise DnsError(f"{d['name']} par pehle se {other[0]['type']} record hai; CNAME saath nahi rah sakta. "
                                   "Yeh naam chhod kar doosra chuniye ya pehle woh record dekhiye.")
            if clash:
                first = clash[0]
                out.append({**d, "op": "update", "id": first.get("id"), "old": {"type": first["type"], "content": first.get("content")},
                            "risk": f"{d['name']} pehle {first['type']} {first.get('content')} ki taraf tha; ab Hoola website par jayega."})
                for extra in clash[1:]:
                    out.append({"op": "delete", "type": extra["type"], "name": extra["name"], "content": extra.get("content"),
                                "id": extra.get("id"), "why": "purana website record (naya wala iski jagah)",
                                "risk": "purana website record hatega"})
            else:
                out.append({**d, "op": "add", "risk": ""})
        elif d["type"] == "MX":
            exact = [r for r in same_name if r["type"] == "MX" and (r.get("content") or "").lower().rstrip(".") == d["content"]]
            out.append({**d, "op": "keep" if exact else "add", "id": exact[0].get("id") if exact else None,
                        "risk": "" if exact or not [r for r in same_name if r["type"] == "MX"] else
                        "pehle wale MX bhi abhi rahenge; naya email chalu ho jaye tab purane hatane ka alag plan banega"})
        elif d["type"] == "TXT" and d["content"].lower().startswith("v=spf1"):
            spf = [r for r in same_name if r["type"] == "TXT" and str(r.get("content") or "").strip('"').lower().startswith("v=spf1")]
            if spf:
                old = str(spf[0].get("content") or "").strip('"')
                inc = [p for p in d["content"].split() if p.startswith("include:")]
                merged = old
                for p in inc:
                    if p not in merged:
                        merged = re.sub(r"\s+([~\-?+]all)$", f" {p} \\1", merged) if re.search(r"[~\-?+]all$", merged) else merged + f" {p}"
                if merged == old:
                    out.append({**d, "content": old, "op": "keep", "id": spf[0].get("id"), "risk": ""})
                else:
                    out.append({**d, "content": merged, "op": "update", "id": spf[0].get("id"), "old": {"type": "TXT", "content": old},
                                "risk": "SPF mein naya provider joda (purane bhi rahenge, do SPF kabhi nahi)"})
            else:
                out.append({**d, "op": "add", "risk": ""})
        else:      # TXT verification / DMARC / CAA: add if not already there
            exact = [r for r in same_name if r["type"] == d["type"] and str(r.get("content") or "").strip('"') == d["content"]]
            if d["name"].startswith("_dmarc.") and not exact:
                dm = [r for r in same_name if r["type"] == "TXT" and "v=dmarc1" in str(r.get("content") or "").lower()]
                if dm:
                    out.append({**d, "op": "keep", "id": dm[0].get("id"), "content": str(dm[0].get("content") or "").strip('"'),
                                "risk": "DMARC pehle se hai; Hoola ne nahi badla"})
                    continue
            out.append({**d, "op": "keep" if exact else "add", "id": exact[0].get("id") if exact else None, "risk": ""})
    return out


def website_records(domain: str, mode: str, target: str, verify: list[dict[str, Any]] | None = None,
                    apex_flatten: bool = True) -> list[dict[str, Any]]:
    """mode saas: www (and apex when her DNS can flatten) CNAME -> Hoola's origin, DNS only; + the TXT / CNAME Cloudflare
    asks for. mode proxy: her own Cloudflare zone proxies to Hoola's server IP (A @, CNAME www -> @). mode direct (v0.280,
    like Lovable): A @ and A www -> Hoola's server IP, DNS only (never proxied), + the _hoola ownership TXT."""
    recs: list[dict[str, Any]] = []
    if mode == "direct":
        recs.append(_rec("A", domain, target, "website (bina www) seedha Hoola ke server par (DNS only, orange cloud nahi)", proxied=False))
        recs.append(_rec("A", f"www.{domain}", target, "website (www) seedha Hoola ke server par (DNS only)", proxied=False))
    elif mode == "saas":
        recs.append(_rec("CNAME", f"www.{domain}", target, "website (www) Hoola par", proxied=False))
        if apex_flatten:
            recs.append(_rec("CNAME", domain, target, "website (bina www) Hoola par; Cloudflare ise flatten karta hai", proxied=False))
    else:
        recs.append(_rec("A", domain, target, "website Hoola ke server par (Cloudflare proxy se https)", proxied=True))
        recs.append(_rec("CNAME", f"www.{domain}", domain, "www bhi wahi site", proxied=True))
    for v in verify or []:
        if v.get("name") and v.get("value"):
            recs.append(_rec(v.get("type", "TXT").upper(), v["name"], v["value"], v.get("why") or "Cloudflare ki pehchaan / SSL jaanch"))
    return recs


def email_records(domain: str, preset: str, report_to: str = "") -> list[dict[str, Any]]:
    p = EMAIL_PRESETS.get(preset)
    if not p:
        raise DnsError("Email provider: google ya zoho.")
    recs = [_rec("MX", domain, host, f"email {p['label']} par", priority=pri) for host, pri in p["mx"]]
    recs.append(_rec("TXT", domain, f"v=spf1 {p['spf']} ~all", "SPF: yeh provider aapke naam se mail bhej sakta hai"))
    rua = f"; rua=mailto:{report_to}" if report_to and "@" in report_to else ""
    recs.append(_rec("TXT", f"_dmarc.{domain}", f"v=DMARC1; p=none{rua}", "DMARC (pehle sirf report, 30 din baad sakhti aapki haan se)"))
    return recs


def _hash(changes: list[dict[str, Any]], domain: str) -> str:
    return hashlib.sha256(json.dumps([domain, changes], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def make_plan(tenant: str, site_id: str, domain: str, desired: list[dict[str, Any]], purpose: str = "website") -> dict[str, Any]:
    loc = where_is(tenant, domain)
    if can_apply(loc["provider"]):
        if loc["provider"] == "porkbun":           # Porkbun can't proxy; a proxied record there is a plain record
            desired = [{**d, "proxied": None} for d in desired]
        current = zone_records(tenant, loc["zone"], loc["provider"])
        changes = plan(current, desired, purpose, domain)
        snap = current
    else:
        changes = [{**d, "op": "add", "risk": ""} for d in desired]
        snap = []
    p = SiteDnsPlan(tenant_id=tenant, site_id=site_id, domain=domain, purpose=purpose, provider=loc["provider"],
                    zone=loc.get("zone", ""), changes=json.dumps(changes, ensure_ascii=False),
                    snapshot=json.dumps(snap, ensure_ascii=False), hash=_hash(changes, domain),
                    status="planned" if loc["provider"] != "manual" else "manual")
    with session() as s:
        s.add(p)
        s.flush()
        s.expunge(p)
    return view(p, loc)


def view(p: SiteDnsPlan, loc: dict[str, Any] | None = None) -> dict[str, Any]:
    ch = json.loads(p.changes or "[]")
    todo = [c for c in ch if c["op"] != "keep"]
    words = []
    for c in todo:
        verb = {"add": "Naya", "update": "Badlega", "delete": "Hatega"}[c["op"]]
        words.append(f"{verb}: {c['type']} {c['name']} -> {c.get('content', '')}" + (f" (pehle: {c['old']['content']})" if c.get("old") else ""))
    return {"id": p.id, "domain": p.domain, "purpose": p.purpose, "provider": p.provider, "status": p.status,
            "changes": ch, "todo": len(todo), "words": words, "risks": [c["risk"] for c in ch if c.get("risk")],
            "hash": p.hash, "error": p.error, "nameservers": (loc or {}).get("nameservers", []),
            "manual_steps": manual_steps(p.domain, todo) if p.provider == "manual" else []}


def manual_steps(domain: str, todo: list[dict[str, Any]]) -> list[str]:
    steps = [f"Apne domain ki company (jahan {domain} liya: GoDaddy / BigRock / Hostinger...) ki website par login kariye "
             "(password aap khud daaliye) -> DNS / Manage DNS kholiye."]
    for c in todo:
        host = c["name"][:-len(domain)].rstrip(".") or "@"
        pr = f", Priority {c['priority']}" if c.get("priority") is not None else ""
        steps.append(f"{c['type']} record: Host/Name '{host}', Value '{c['content']}'{pr}, TTL default.")
    steps.append("Save karke 'Maine daal diya' dabaiye; Hoola duniya ke 3 DNS se jaanch karega (10-30 min, kabhi 24 ghante).")
    return steps


def get_plan(tenant: str, pid: str) -> SiteDnsPlan:
    with session() as s:
        p = s.get(SiteDnsPlan, pid)
        if p is None or p.tenant_id != tenant:
            raise DnsError("DNS plan nahi mila.")
        s.expunge(p)
        return p


def apply(tenant: str, pid: str, hash_: str) -> dict[str, Any]:
    """ONLY from her tap (API). Re-reads the zone; a zone that changed since the plan gets a fresh plan instead."""
    from .cf import CfError, Cloudflare
    p = get_plan(tenant, pid)
    if p.status != "planned":
        raise DnsError(f"Yeh plan '{p.status}' hai.")
    if hash_ != p.hash:
        raise DnsError("Plan badal gaya hai; naya card dekhiye.")
    if not can_apply(p.provider):
        raise DnsError("Is domain ka DNS Hoola badal nahi sakta; card ke steps se khud daaliye.")
    from .domains import DomainError
    cf = _client(tenant, p.provider)
    now_recs = zone_records(tenant, p.zone, p.provider)
    snap = json.loads(p.snapshot or "[]")
    if _shape(now_recs) != _shape(snap):
        raise DnsError("Plan banne ke baad DNS badal gaya; Hoola naya plan banayega (dobara 'domain jodo' kahiye).")
    done: list[dict[str, Any]] = []
    try:
        for c in json.loads(p.changes):
            if c["op"] == "add":
                r = cf.create_record(p.zone, c)
                done.append({"op": "add", "id": r.get("id")})
            elif c["op"] == "update":
                cf.update_record(p.zone, c["id"], c)
                done.append({"op": "update", "id": c["id"], "old": c.get("old")})
            elif c["op"] == "delete":
                cf.delete_record(p.zone, c["id"])
                done.append({"op": "delete", "id": c["id"], "rec": {k: c.get(k) for k in ("type", "name", "content", "priority")}})
    except (CfError, DomainError) as e:
        _undo_done(cf, p.zone, done, snap)
        with session() as s:
            row = s.get(SiteDnsPlan, pid)
            row.status, row.error = "failed", str(e)
        raise DnsError(f"DNS badal nahi paya, jo hua tha woh wapas kar diya: {e}")
    with session() as s:
        row = s.get(SiteDnsPlan, pid)
        row.status, row.done, row.applied_at = "applied", json.dumps(done), datetime.now(timezone.utc)
    return {"ok": True, "applied": len(done), "say": f"{p.domain}: {len(done)} DNS badlav ho gaye. Duniya mein failne mein 5-30 min."}


def _shape(recs: list[dict[str, Any]]) -> list[tuple]:
    return sorted((r.get("type"), (r.get("name") or "").lower(), str(r.get("content") or "").strip('"').lower()) for r in recs)


def _undo_done(cf, zone: str, done: list[dict[str, Any]], snap: list[dict[str, Any]]) -> None:
    for d in reversed(done):
        try:
            if d["op"] == "add" and d.get("id"):
                cf.delete_record(zone, d["id"])
            elif d["op"] == "update":
                old = next((r for r in snap if r.get("id") == d["id"]), None)
                if old:
                    cf.update_record(zone, d["id"], old)
            elif d["op"] == "delete":
                cf.create_record(zone, d["rec"])
        except Exception:
            log.exception("dns undo step failed")


def undo(tenant: str, pid: str) -> dict[str, Any]:
    from .cf import Cloudflare
    p = get_plan(tenant, pid)
    if p.status != "applied":
        raise DnsError("Sirf lage hue plan wapas ho sakte hain.")
    if p.applied_at and (datetime.now(timezone.utc) - p.applied_at.replace(tzinfo=p.applied_at.tzinfo or timezone.utc)).days > 7:
        raise DnsError("7 din se purana badlav; ab naya plan banwaiye.")
    _undo_done(_client(tenant, p.provider), p.zone, json.loads(p.done or "[]"), json.loads(p.snapshot or "[]"))
    with session() as s:
        s.get(SiteDnsPlan, pid).status = "undone"
    return {"ok": True, "say": f"{p.domain}: DNS pehle jaisa kar diya."}


def check(tenant: str, pid: str) -> dict[str, Any]:
    """Is the plan visible from the 3 public resolvers?"""
    p = get_plan(tenant, pid)
    res = []
    for c in json.loads(p.changes):
        if c["op"] == "delete":
            continue
        if c.get("proxied"):          # proxied records show Cloudflare's addresses, not ours
            r = lookup(c["name"], "A")
            res.append({"name": c["name"], "type": c["type"], "all": any(v and v != ["?"] for v in r.values()), "by": r})
            continue
        want = c["content"].split()[0] if c["type"] == "TXT" else c["content"]
        res.append(seen_everywhere(c["name"], c["type"], want))
    done = all(x["all"] for x in res) if res else True
    return {"plan": p.id, "domain": p.domain, "checks": res, "done": done,
            "say": "Har jagah dikh raha hai." if done else f"Abhi {sum(1 for x in res if x['all'])}/{len(res)} record har jagah dikh rahe hain; thodi der."}


def plans(tenant: str, site_id: str = "", limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        q = select(SiteDnsPlan).where(SiteDnsPlan.tenant_id == tenant)
        if site_id:
            q = q.where(SiteDnsPlan.site_id == site_id)
        return [view(p) for p in s.scalars(q.order_by(SiteDnsPlan.created_at.desc()).limit(limit)).all()]


def doh_ok() -> bool:
    return os.environ.get("SITE_DOH", "true").lower() not in ("0", "false", "off")

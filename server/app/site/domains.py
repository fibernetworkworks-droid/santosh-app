"""v0.123 Domains: name ideas from her business, live availability + first-year and renewal price in rupees from the
registry, and buying ONLY on her fingerprint-signed tap. Official APIs only: Cloudflare Registrar API (beta, at-cost;
.com / .shop / .store / .online / .co / .app / .dev ...) and Porkbun API v3 (.in family and anything Cloudflare can't
sell). The domain is always registered in HER name (registrant = her / her business), on her own registrar account by
default; the Hoola (Newtika) account is used only when the server is set to resell (SITES_RESELL) and the card says so.

.in / .co.in: NIXI e-KYC is done by HER on the registrar's page (Aadhaar / DigiLocker); Hoola reminds and checks, never
does the identity step. Renewals: reminders at 60 / 30 / 7 / 1 days; auto-renew only if she said yes on the buy card."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import dns as D
from .guard import name_problem

log = logging.getLogger("santosh.site")
IN_FAMILY = (".in", ".co.in", ".net.in", ".org.in", ".firm.in", ".gen.in", ".ind.in")
DEFAULT_TLDS = [".in", ".com", ".co.in", ".shop", ".store", ".online"]
_TRANSPORT: httpx.BaseTransport | None = None


class DomainError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


class SiteDomain(Base):
    __tablename__ = "site_domains"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dom"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), default="")
    domain: Mapped[str] = mapped_column(String(253), index=True)
    registrar: Mapped[str] = mapped_column(String(20), default="")        # cloudflare | porkbun
    account: Mapped[str] = mapped_column(String(10), default="own")        # own (her account) | hoola (Newtika resells)
    years: Mapped[int] = mapped_column(Integer, default=1)
    usd: Mapped[float] = mapped_column(Float, default=0.0)                  # first year, as the registry quoted it
    renew_usd: Mapped[float] = mapped_column(Float, default=0.0)
    inr: Mapped[float] = mapped_column(Float, default=0.0)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="card")
    # card (waiting her tap) | registering | registered | kyc (waiting her .in KYC) | failed | expired | cancelled
    hash: Mapped[str] = mapped_column(String(32), default="")
    registrant: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminded: Mapped[str] = mapped_column(Text, default="[]")
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _st():
    from ..config import get_settings
    return get_settings()


def _inr(usd: float) -> float:
    from ..usage import usd_inr
    return round(usd * usd_inr())


def tld_of(domain: str) -> str:
    for t in sorted(IN_FAMILY, key=len, reverse=True):
        if domain.endswith(t):
            return t
    return "." + domain.rsplit(".", 1)[-1]


# ---------------------------------------------------------------- registrar clients (official APIs)
class CfRegistrar:
    def __init__(self, token: str, account: str):
        if not (token and account):
            raise DomainError("Cloudflare Registrar ke liye token + account id chahiye.")
        self.token, self.account = token, account

    def _req(self, method: str, path: str, json_body: Any = None) -> Any:
        from .cf import base
        try:
            with httpx.Client(timeout=40, transport=_TRANSPORT) as c:
                r = c.request(method, f"{base()}/accounts/{self.account}/registrar{path}", json=json_body,
                              headers={"Authorization": f"Bearer {self.token}"})
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise DomainError(f"Cloudflare Registrar tak nahi pahunch paya: {e.__class__.__name__}")
        if r.status_code >= 400 or body.get("success") is False:
            errs = "; ".join(f"{e.get('code')}: {e.get('message')}" for e in body.get("errors") or []) or str(r.status_code)
            raise DomainError(f"Cloudflare Registrar: {errs}")
        return body.get("result"), r.status_code

    def check(self, domains: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i in range(0, len(domains), 20):
            res, _ = self._req("POST", "/domain-check", {"domains": domains[i:i + 20]})
            for x in (res or {}).get("domains", res if isinstance(res, list) else []):
                pr = x.get("pricing") or {}
                out.append({"domain": x.get("name") or x.get("domain"), "available": bool(x.get("registrable")),
                            "reason": x.get("reason", ""), "usd": float(pr.get("registration_cost") or 0),
                            "renew_usd": float(pr.get("renewal_cost") or 0), "currency": pr.get("currency", "USD"),
                            "premium": x.get("tier") not in (None, "standard"), "registrar": "cloudflare"})
        return out

    def register(self, domain: str, auto_renew: bool) -> dict[str, Any]:
        res, code = self._req("POST", "/registrations", {"domain_name": domain, "auto_renew": bool(auto_renew)})
        return {"state": (res or {}).get("state") or ("succeeded" if code == 201 else "in_progress"), "raw": res}

    def status(self, domain: str) -> str:
        res, _ = self._req("GET", f"/registrations/{domain}/registration-status")
        return (res or {}).get("state", "")


class Porkbun:
    def __init__(self, key: str, secret: str):
        if not (key and secret):
            raise DomainError("Porkbun ke liye API key + secret key chahiye.")
        self.key, self.secret = key, secret

    def _req(self, path: str, body: dict | None = None) -> dict[str, Any]:
        b = (os.environ.get("PORKBUN_API_BASE") or "https://api.porkbun.com/api/json/v3").rstrip("/")
        try:
            with httpx.Client(timeout=40, transport=_TRANSPORT) as c:
                r = c.post(f"{b}{path}", json={"apikey": self.key, "secretapikey": self.secret, **(body or {})})
            j = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise DomainError(f"Porkbun tak nahi pahunch paya: {e.__class__.__name__}")
        if r.status_code == 429:
            raise DomainError("Porkbun: bahut jaldi jaldi pooch liya; ek minute baad.")
        if j.get("status") != "SUCCESS":
            raise DomainError(f"Porkbun: {j.get('message') or r.status_code}")
        return j

    def ping(self) -> bool:
        return self._req("/ping").get("status") == "SUCCESS"

    def check(self, domain: str) -> dict[str, Any]:
        j = self._req(f"/domain/checkDomain/{domain}")
        x = j.get("response") or {}
        renew = ((x.get("additional") or {}).get("renewal") or {}).get("price") or x.get("regularPrice") or x.get("price")
        return {"domain": domain, "available": str(x.get("avail", "")).lower() == "yes", "reason": "" if
                str(x.get("avail", "")).lower() == "yes" else "domain_unavailable", "usd": float(x.get("price") or 0),
                "renew_usd": float(renew or 0), "currency": "USD", "premium": str(x.get("premium", "no")).lower() == "yes",
                "registrar": "porkbun"}

    def requirements(self, tld: str) -> dict[str, Any]:
        return self._req(f"/domain/getRegistrationRequirements/{tld.lstrip('.')}")

    def create(self, domain: str, cost_usd: float) -> dict[str, Any]:
        j = self._req(f"/domain/create/{domain}", {"cost": int(round(cost_usd * 100)), "agreeToTerms": "yes"})
        return {"state": "succeeded", "raw": {k: v for k, v in j.items() if k not in ("apikey", "secretapikey")}}

    # DNS (domains bought through Porkbun)
    def dns_records(self, domain: str) -> list[dict[str, Any]]:
        return self._req(f"/dns/retrieve/{domain}").get("records") or []

    def dns_create(self, domain: str, sub: str, type_: str, content: str, prio: int | None = None) -> str:
        body = {"name": sub, "type": type_, "content": content, "ttl": "600"}
        if prio is not None:
            body["prio"] = str(prio)
        return str(self._req(f"/dns/create/{domain}", body).get("id", ""))

    def dns_edit(self, domain: str, rid: str, sub: str, type_: str, content: str, prio: int | None = None) -> None:
        body = {"name": sub, "type": type_, "content": content, "ttl": "600"}
        if prio is not None:
            body["prio"] = str(prio)
        self._req(f"/dns/edit/{domain}/{rid}", body)

    def dns_delete(self, domain: str, rid: str) -> None:
        self._req(f"/dns/delete/{domain}/{rid}")


# ---------------------------------------------------------------- whose account
def accounts(tenant: str) -> dict[str, Any]:
    """Registrar clients she can use: her own keys first; Hoola's (Newtika) only when the server resells."""
    out: dict[str, Any] = {}
    tok, acct = D.key(tenant, "cf_registrar")
    if tok and acct:
        out["cloudflare"] = (CfRegistrar(tok, acct), "own")
    k, sec = D.key(tenant, "porkbun")
    if k and sec:
        out["porkbun"] = (Porkbun(k, sec), "own")
    st = _st()
    if getattr(st, "sites_resell", False):
        if "cloudflare" not in out and getattr(st, "sites_reg_cf_token", "") and getattr(st, "sites_reg_cf_account", ""):
            out["cloudflare"] = (CfRegistrar(st.sites_reg_cf_token, st.sites_reg_cf_account), "hoola")
        if "porkbun" not in out and getattr(st, "sites_porkbun_key", "") and getattr(st, "sites_porkbun_secret", ""):
            out["porkbun"] = (Porkbun(st.sites_porkbun_key, st.sites_porkbun_secret), "hoola")
    return out


# ---------------------------------------------------------------- ideas + live check
def _clean_label(s: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t.replace("&", "and"))


def ideas(name: str, city: str = "", trade: str = "", tlds: list[str] | None = None, limit: int = 30) -> list[str]:
    n = _clean_label(name)
    if not n or name_problem(n):           # a business name that starts with a bank / govt / big brand gets no ideas
        return []
    c = _clean_label(city)
    t = _clean_label(trade)
    words = [w for w in re.split(r"\s+", (name or "").lower()) if w]
    initials = "".join(_clean_label(w)[:1] for w in words) if len(words) > 1 else ""
    labels = [n, f"{n}{c}" if c else "", f"{n}{t}" if t and t not in n else "", f"{n}online", f"the{n}",
              f"{initials}{t}" if initials and t else "", f"{n}india", f"{c}{n}" if c else "", f"{n}{c[:3]}" if c else ""]
    labels = [x for x in dict.fromkeys(labels) if 3 <= len(x) <= 20 and not name_problem(x)]
    out = []
    for x in labels:
        for tl in (tlds or DEFAULT_TLDS):
            out.append(x + tl)
    return out[:limit]


def check(tenant: str, domains: list[str]) -> list[dict[str, Any]]:
    acc = accounts(tenant)
    if not acc:
        raise DomainError("Domain ka daam dekhne / lene ke liye Website > Hosting mein apna Cloudflare Registrar ya Porkbun "
                          "account jodiye (key sirf app mein).")
    doms = []
    for d in domains:
        try:
            doms.append(D.norm_domain(d))
        except D.DnsError:
            continue
    doms = [d for d in dict.fromkeys(doms) if not name_problem(d.split(".")[0])]
    res: list[dict[str, Any]] = []
    cf_try = [d for d in doms if tld_of(d) not in IN_FAMILY]
    pb_try = [d for d in doms if tld_of(d) in IN_FAMILY]
    if "cloudflare" in acc and cf_try:
        try:
            got = acc["cloudflare"][0].check(cf_try)
            for g in got:
                if g["reason"] == "extension_not_supported_via_api":
                    pb_try.append(g["domain"])
                else:
                    res.append({**g, "account": acc["cloudflare"][1]})
        except DomainError as e:
            log.info("cf check failed: %s", e)
            pb_try += cf_try
    elif cf_try:
        pb_try += cf_try
    if "porkbun" in acc:
        for i, d in enumerate(pb_try[:8]):      # Porkbun: 10 checks per 10 s per account
            if i:
                time.sleep(float(os.environ.get("PORKBUN_GAP_S", "1.1")))
            try:
                res.append({**acc["porkbun"][0].check(d), "account": acc["porkbun"][1]})
            except DomainError as e:
                res.append({"domain": d, "available": False, "reason": str(e), "registrar": "porkbun"})
    for r in res:
        if r.get("usd"):
            r["inr"] = _inr(r["usd"])
            r["renew_inr"] = _inr(r.get("renew_usd") or r["usd"])
            r["renew_jump"] = bool(r.get("renew_usd") and r["renew_usd"] > 1.5 * r["usd"])
        r["kyc"] = tld_of(r["domain"]) in IN_FAMILY
    return res


def suggest(tenant: str, ref: str = "", name: str = "", city: str = "", conv: str = "") -> dict[str, Any]:
    from . import service as S
    from . import library as L
    trade = ""
    if ref or not name:
        with session() as s:
            r = S._find(s, tenant, ref)
            facts = json.loads(r.facts or "{}")
            name = name or r.name or facts.get("name", "")
            city = city or facts.get("city") or (facts.get("address", "").split(",")[-1].strip() if facts.get("address") else "")
            f = L.fields().get(r.field) or {}
            trade = (f.get("aliases") or [""])[0].split()[0] if f else ""
    if not name:
        raise DomainError("Business ka naam bataiye.")
    cands = ideas(name, city, trade)
    res = check(tenant, cands)
    ok = [x for x in res if x.get("available") and not x.get("premium") and x.get("usd")]
    pref = {".in": 0, ".com": 1, ".co.in": 2}
    ok.sort(key=lambda x: (pref.get(tld_of(x["domain"]), 5), len(x["domain"]), x["usd"]))
    return {"ideas": ok[:5], "checked": len(res), "taken": [x["domain"] for x in res if not x.get("available")][:10],
            "say": ("Yeh naam khaali hain: " + ", ".join(f"{x['domain']} (₹{x['inr']:,.0f}, phir ₹{x['renew_inr']:,.0f}/saal)" for x in ok[:5]))
            if ok else "In naamon mein koi khaali nahi mila; koi aur naam ya shabd bataiye."}


# ---------------------------------------------------------------- buying: card -> her fingerprint tap -> register
def _month_spent(tenant: str) -> float:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        return float(s.scalar(select(func.coalesce(func.sum(SiteDomain.inr), 0)).where(
            SiteDomain.tenant_id == tenant, SiteDomain.status.in_(("registering", "registered", "kyc")),
            SiteDomain.registered_at >= start)) or 0)


def _ceiling() -> float:
    return float(getattr(_st(), "sites_domain_month_inr", 5000) or 5000)


def _card_hash(o: SiteDomain) -> str:
    return hashlib.sha256(f"{o.id}|{o.domain}|{o.registrar}|{o.account}|{o.usd:.2f}|{o.renew_usd:.2f}|{o.years}|{o.auto_renew}"
                          .encode()).hexdigest()[:24]


def buy_request(tenant: str, ref: str, domain: str, auto_renew: bool = False, conv: str = "") -> dict[str, Any]:
    from . import service as S
    d = D.norm_domain(domain)
    bad = name_problem(d.split(".")[0])
    if bad:
        raise DomainError(bad)
    with session() as s:
        r = S._find(s, tenant, ref)
        sid, rconv, facts = r.id, r.conv, json.loads(r.facts or "{}")
    got = check(tenant, [d])
    if not got:
        raise DomainError("Is domain ka daam nahi mil paya.")
    g = got[0]
    if not g.get("available"):
        raise DomainError(f"{d} khaali nahi hai ({g.get('reason') or 'kisi aur ka'}).")
    if g.get("premium"):
        raise DomainError(f"{d} premium domain hai (bahut mehenga); Hoola premium nahi leta.")
    inr = _inr(g["usd"])
    if _month_spent(tenant) + inr > _ceiling():
        raise DomainError(f"Is mahine domain par ₹{_ceiling():,.0f} ki seema hai; yeh lene se paar ho jayegi.")
    registrant = {"name": facts.get("owner") or facts.get("name") or "", "business": facts.get("name") or "",
                  "email": facts.get("email") or "", "phone": facts.get("phone") or ""}
    with session() as s:
        o = SiteDomain(tenant_id=tenant, site_id=sid, domain=d, registrar=g["registrar"], account=g.get("account", "own"),
                       usd=g["usd"], renew_usd=g.get("renew_usd") or g["usd"], inr=inr, auto_renew=bool(auto_renew),
                       registrant=json.dumps(registrant, ensure_ascii=False))
        s.add(o)
        s.flush()
        o.hash = _card_hash(o)
        s.flush()
        s.expunge(o)
    card = approval_card(tenant, o.id)
    from . import service as S2
    S2._publish(tenant, "site_domain", {**card, "push": True}, conv or rconv)
    return card


def approval_card(tenant: str, oid: str) -> dict[str, Any] | None:
    with session() as s:
        o = s.get(SiteDomain, oid)
        if o is None or o.tenant_id != tenant or o.status != "card":
            return None
        reg = json.loads(o.registrant or "{}")
        lines = [f"Pehla saal: ₹{o.inr:,.0f} (${o.usd:.2f})", f"Agle saal se: ₹{_inr(o.renew_usd):,.0f}/saal",
                 f"Registrar: {'Cloudflare' if o.registrar == 'cloudflare' else 'Porkbun'} "
                 f"({'aapka account' if o.account == 'own' else 'Hoola / Newtika ka account; bill Newtika se'})",
                 f"Malik (registrant): {reg.get('business') or reg.get('name') or 'aap'}",
                 f"Auto-renew: {'haan' if o.auto_renew else 'nahi (Hoola yaad dilayega)'}",
                 "Domain lene ke baad paisa wapas nahi hota."]
        if tld_of(o.domain) in IN_FAMILY:
            lines.append(".in ke liye NIXI e-KYC aapko khud registrar ke page par (DigiLocker) karna hoga, warna domain ruk sakta hai.")
        return {"kind": "domain", "id": o.id, "title": f"Domain lein: {o.domain}", "domain": o.domain, "amount": f"₹{o.inr:,.0f}",
                "payee": "Cloudflare Registrar" if o.registrar == "cloudflare" else "Porkbun", "inr": o.inr,
                "usd": round(o.usd, 2), "renew_inr": _inr(o.renew_usd), "lines": lines, "hash": o.hash, "site": o.site_id,
                "say": f"{o.domain} ₹{o.inr:,.0f} mein (agle saal ₹{_inr(o.renew_usd):,.0f}). Lena ho to fingerprint se haan."}


def buy(tenant: str, oid: str, hash_: str) -> dict[str, Any]:
    """ONLY from her tap (API; the fingerprint is checked before this is called)."""
    with session() as s:
        o = s.get(SiteDomain, oid)
        if o is None or o.tenant_id != tenant:
            raise DomainError("Yeh card nahi mila.")
        if o.status != "card":
            raise DomainError(f"Yeh domain '{o.status}' hai.")
        if hash_ != o.hash:
            raise DomainError("Card badal gaya; naya card dekhiye.")
        s.expunge(o)
    fresh = check(tenant, [o.domain])
    if not fresh or not fresh[0].get("available"):
        _set(oid, status="failed", error="ab khaali nahi")
        raise DomainError(f"{o.domain} ab khaali nahi raha.")
    if abs(float(fresh[0].get("usd") or 0) - o.usd) > 0.009:
        _set(oid, status="cancelled", error="daam badal gaya")
        try:
            buy_request(tenant, o.site_id, o.domain, o.auto_renew)
        except DomainError:
            pass
        raise DomainError(f"{o.domain} ka daam badal gaya (${fresh[0].get('usd')}); naya card bheja hai, dobara dekhiye.")
    if _month_spent(tenant) + o.inr > _ceiling():
        raise DomainError(f"Is mahine ki domain seema ₹{_ceiling():,.0f} paar ho jayegi.")
    acc = accounts(tenant)
    if o.registrar not in acc:
        raise DomainError("Registrar account ab juda nahi hai.")
    cli = acc[o.registrar][0]
    _set(oid, status="registering", registered_at=now())
    try:
        res = cli.register(o.domain, o.auto_renew) if o.registrar == "cloudflare" else cli.create(o.domain, o.usd)
    except DomainError as e:
        _set(oid, status="failed", error=str(e))
        raise
    state = res.get("state")
    if state in ("failed", "blocked", "action_required"):
        _set(oid, status="failed", error=state)
        raise DomainError(f"Registrar ne domain nahi diya ({state}).")
    done = state == "succeeded"
    kyc = tld_of(o.domain) in IN_FAMILY
    _set(oid, status=("kyc" if kyc else "registered") if done else "registering",
         expires_at=datetime.now(timezone.utc) + timedelta(days=365 * max(1, o.years)))
    say = (f"{o.domain} aapke naam par le liya." + (" Ab registrar ke email / page par NIXI e-KYC (DigiLocker) kar dijiye; "
           "Hoola roz yaad dilayega jab tak aap 'KYC ho gaya' nahi kehti." if kyc else "")) if done else \
        f"{o.domain} registry mein ja raha hai; ho jaane par bataunga."
    from . import service as S
    S._publish(tenant, "site_domain", {"kind": "domain_done", "domain": o.domain, "status": "kyc" if kyc and done else
                                       ("registered" if done else "registering"), "say": say, "push": False})
    if done:
        say += _join_site(tenant, o)
    return {"ok": True, "domain": o.domain, "state": state, "say": say}


def _join_site(tenant: str, o: SiteDomain) -> str:
    """A bought domain is joined to its site at once; that only PREPARES the DNS card (her tap applies it)."""
    if not o.site_id:
        return ""
    try:
        from . import hosting as H
        H.connect_domain(tenant, o.site_id, o.domain)
        return " DNS ka card bhi bhej diya: haan dabaate hi website is naam par khulegi."
    except Exception as e:
        log.info("join after buy failed for %s: %s", o.domain, e)
        return f" Website se jodne ke liye 'domain jodo {o.domain}' kahiye ({str(e)[:120]})."


def _set(oid: str, **kw) -> None:
    with session() as s:
        o = s.get(SiteDomain, oid)
        for k, v in kw.items():
            setattr(o, k, v)


def cancel(tenant: str, oid: str) -> dict[str, Any]:
    with session() as s:
        o = s.get(SiteDomain, oid)
        if o is None or o.tenant_id != tenant:
            raise DomainError("Yeh card nahi mila.")
        if o.status != "card":
            raise DomainError(f"Yeh domain '{o.status}' hai; ab card band nahi ho sakta.")
        o.status = "cancelled"
        d = o.domain
    return {"ok": True, "say": f"{d} nahi liya."}


def kyc_done(tenant: str, domain: str) -> dict[str, Any]:
    d = D.norm_domain(domain)
    with session() as s:
        o = s.scalars(select(SiteDomain).where(SiteDomain.tenant_id == tenant, SiteDomain.domain == d,
                                               SiteDomain.status == "kyc")).first()
        if o is None:
            raise DomainError(f"{d} KYC ke intezaar mein nahi hai.")
        o.status = "registered"
    return {"ok": True, "say": f"{d}: KYC note kar liya. Hoola dekhta rahega ki domain chal raha hai."}


def domains(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [{"id": o.id, "domain": o.domain, "status": o.status, "registrar": o.registrar, "account": o.account,
                 "inr": o.inr, "renew_inr": _inr(o.renew_usd), "auto_renew": o.auto_renew, "error": o.error,
                 "expires_at": o.expires_at.isoformat() if o.expires_at else ""}
                for o in s.scalars(select(SiteDomain).where(SiteDomain.tenant_id == tenant)
                                   .order_by(SiteDomain.created_at.desc()).limit(50)).all()]


# ---------------------------------------------------------------- worker: registering -> done, KYC + renewal reminders
def tick() -> int:
    from . import service as S
    n = 0
    with session() as s:
        rows = s.scalars(select(SiteDomain).where(SiteDomain.status.in_(("registering", "kyc", "registered")))).all()
        for o in rows:
            s.expunge(o)
    for o in rows:
        try:
            if o.status == "registering" and o.registrar == "cloudflare":
                acc = accounts(o.tenant_id).get("cloudflare")
                if acc:
                    st = acc[0].status(o.domain)
                    if st == "succeeded":
                        _set(o.id, status="kyc" if tld_of(o.domain) in IN_FAMILY else "registered")
                        S._publish(o.tenant_id, "site_domain", {"kind": "domain_done", "domain": o.domain, "status": "registered",
                                                                "say": f"{o.domain} aapka ho gaya." + _join_site(o.tenant_id, o),
                                                                "push": True})
                    elif st in ("failed", "blocked", "action_required"):
                        _set(o.id, status="failed", error=st)
                        S._publish(o.tenant_id, "site_domain", {"kind": "domain_done", "domain": o.domain, "status": "failed",
                                                                "say": f"{o.domain} registry ne nahi diya ({st}).", "push": True})
                n += 1
            sent = json.loads(o.reminded or "[]")
            if o.status == "kyc":
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if f"kyc:{today}" not in sent:
                    _remind(o, f"kyc:{today}", f"{o.domain}: NIXI e-KYC baaki hai (registrar ke page par DigiLocker se). "
                                                "Ho gaya ho to 'KYC ho gaya' kahiye.")
            if o.expires_at:
                exp = o.expires_at.replace(tzinfo=o.expires_at.tzinfo or timezone.utc)
                days = (exp - datetime.now(timezone.utc)).days
                w = next((x for x in (1, 7, 30, 60) if days <= x), 0)     # the tightest window only, once
                if w and f"renew:{w}" not in sent:
                    _remind(o, [f"renew:{x}" for x in (1, 7, 30, 60) if x >= w],
                            f"{o.domain} {max(days, 0)} din mein khatam: renew ka daam ₹{_inr(o.renew_usd):,.0f}."
                            + (" Auto-renew chalu hai; card / balance check kar lijiye." if o.auto_renew else
                               " Auto-renew band hai; registrar par renew kijiye ya mujhe kahiye."))
        except Exception:
            log.exception("domain tick failed for %s", o.domain)
    return n


def _remind(o: SiteDomain, tag: str | list[str], text: str) -> None:
    from . import service as S
    with session() as s:
        row = s.get(SiteDomain, o.id)
        sent = json.loads(row.reminded or "[]")
        sent += [tag] if isinstance(tag, str) else tag
        row.reminded = json.dumps(sent[-40:])
    S._publish(o.tenant_id, "site_domain", {"kind": "domain_reminder", "domain": o.domain, "say": text, "push": True})

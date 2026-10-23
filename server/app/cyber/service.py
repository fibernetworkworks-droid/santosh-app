"""Cyber Suraksha Sahayak: Hoola as a small business's cybersecurity analyst, end to end.

  1. Reads alerts and filters noise: pasted / uploaded alerts from antivirus / EDR consoles (Defender, Quick Heal, Seqrite CSV /
     text), firewall / router logs (UFW / iptables, MikroTik), server auth logs (sshd, fail2ban), Google Workspace / Microsoft
     365 security alert emails, Cloudflare / WAF events (CSV / JSON), Hoola's own new-phone sign-ins -> normalised, deduped by
     fingerprint, grouped into stories (brute force, login after failures, port scan, one virus on many PCs), scored, her own
     "yeh normal hai" rules applied (never for ransomware / login-after-failures / forwarding rules ...) -> the few that matter,
     each with WHY and what to do.
  2. Checks suspicious emails, links and files: the mail's own headers (SPF / DKIM / DMARC results, Reply-To / Return-Path,
     display-name and look-alike-domain spoofing) + the IT Helpdesk's phishing words check (reused); links are NEVER opened, only
     looked up in Google Web Risk / Safe Browsing / VirusTotal with HER key; a file only by its SHA-256 hash (never uploaded).
  3. Her own attack surface, passive only: her domains (SPF / DMARC / DKIM / CAA / MX, TLS expiry, security headers; deeper
     own-site checks like an open .git / .env only after she proves the domain is hers), breaches of her work emails (HIBP, her
     key), CVE / CISA KEV / CERT-In advisories matching her software + IT Helpdesk assets.
  4. Writes the incident note: timeline, what happened, impact, what was done, CERT-In 6-hour + DPDP (via the IT Helpdesk's
     incident record = same clock, same draft), lessons -> Word + PDF.
  5. Waits for her Haan on BLOCKING OR WIPING anything: block IP (her Cloudflare, official API), disable user, sign-out
     everywhere, quarantine, isolate PC, wipe a lost device = `cyber_action` cards; only `decide_action(by_tap=True)` from the app
     API decides; wiping also needs her fingerprint once a phone key is set up. Without an API it gives console steps she does.

Never: scanning anyone else's systems, exploit code, opening a suspicious link, uploading her files, keeping a password / OTP.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import secrets
import socket
import ssl
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import intel as I
from . import rules as R
from .models import (
    CyberAction,
    CyberAdvisory,
    CyberAlert,
    CyberCheck,
    CyberDomain,
    CyberIncident,
    CyberKey,
    CyberRule,
    CyberSettings,
    CyberSoftware,
)

log = logging.getLogger("santosh.cyber")
_LOCK = threading.RLock()
PROVIDERS = {"webrisk": "Google Web Risk (link jaanch, business ke liye)", "safebrowsing": "Google Safe Browsing (sirf non-commercial)",
             "virustotal": "VirusTotal (sirf hash / link lookup)", "hibp": "Have I Been Pwned (breach jaanch)",
             "nvd": "NVD API key (CVE, optional)", "cloudflare": "Cloudflare token + Zone ID (IP block, aapki haan se)"}
ACTION_WAIT_H = 24
SLEEP_BETWEEN_S = 0.0          # politeness gap between per-item API calls (set by the worker, 0 in tests)


class CyberError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime | None) -> str:
    d = _aware(d)
    return d.isoformat(timespec="minutes") if d else ""


def clock() -> datetime:
    return now()


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return clock().astimezone(_tz(tenant)).date()


def _local(tenant: str, d: datetime | None) -> str:
    d = _aware(d)
    return d.astimezone(_tz(tenant)).strftime("%d %b %I:%M %p") if d else ""


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("cyber publish failed")


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def actor_name(tenant: str, actor: str) -> str:
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor or "owner")
    except Exception:
        return "Owner" if actor in ("", "owner") else actor[:40]


def _st(s, tenant: str) -> CyberSettings:
    r = s.get(CyberSettings, tenant)
    if r is None:
        r = CyberSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _list(v) -> list[str]:
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\n;]+", v)]
    return [str(x).strip()[:120] for x in (v or []) if str(x).strip()][:50]


# ---------------------------------------------------------------- settings + keys
_LIST_KEYS = ("own_ips", "vip_names", "crown_hosts", "work_emails")


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        out = {k: _j(getattr(r, k), []) for k in _LIST_KEYS}
        out.update(link_provider=r.link_provider, morning_time=r.morning_time, rules=r.rules)
    out["keys"] = key_status(tenant)
    try:
        from ..helpdesk.service import settings as hs
        h = hs(tenant)
        out["office"] = {"office_name": h.get("office_name", ""), "entity": h.get("entity", "")}
    except Exception:
        out["office"] = {}
    return out


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        for k in _LIST_KEYS:
            if k in kw:
                vals = _list(kw[k])
                if k == "own_ips":
                    bad = [v for v in vals if not R.valid_ip(v.split("/")[0])]
                    if bad:
                        raise CyberError(f"Yeh IP sahi nahi: {', '.join(bad[:3])}")
                if k == "work_emails":
                    vals = [v.lower() for v in vals if re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", v)]
                setattr(r, k, _dump(vals))
        if kw.get("link_provider") in ("webrisk", "safebrowsing"):
            r.link_provider = kw["link_provider"]
        if kw.get("morning_time"):
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(kw["morning_time"])):
                raise CyberError("Samay HH:MM mein (jaise 09:15).")
            r.morning_time = str(kw["morning_time"])
        if "rules" in kw:
            r.rules = str(kw["rules"] or "")[:2000]
    return {**settings(tenant), "say": "Suraksha ke niyam save."}


def set_key(tenant: str, provider: str, token: str, extra: str = "") -> dict:
    """ONLY from the app (API): her key, sealed with the bazar vault. Never through chat."""
    from ..bazar.security import vault
    if provider not in PROVIDERS:
        raise CyberError("Provider: " + ", ".join(PROVIDERS))
    token = (token or "").strip()
    if len(token) < 16:
        raise CyberError("Yeh key adhoori lagti hai.")
    extra = (extra or "").strip()
    label = f"…{token[-4:]}"
    if provider == "cloudflare":
        if not re.fullmatch(r"[0-9a-f]{32}", extra):
            raise CyberError("Cloudflare ke liye token + Zone ID (32 akshar, domain ke Overview page par) chahiye.")
        try:
            v = I.cf_verify(token)
        except I.IntelError as e:
            raise CyberError(str(e))
        if (v or {}).get("status") != "active":
            raise CyberError("Cloudflare token active nahi hai.")
    with session() as s:
        for old in s.scalars(select(CyberKey).where(CyberKey.tenant_id == tenant, CyberKey.provider == provider)).all():
            s.delete(old)
        s.add(CyberKey(tenant_id=tenant, provider=provider, sealed=vault().seal(token), extra=extra[:120], label=label))
    return {"ok": True, "provider": provider, "label": label, "say": f"{PROVIDERS[provider]}: key jud gayi (sirf server par, band tale mein)."}


def del_key(tenant: str, provider: str) -> dict:
    with session() as s:
        for old in s.scalars(select(CyberKey).where(CyberKey.tenant_id == tenant, CyberKey.provider == provider)).all():
            s.delete(old)
    return {"ok": True, "say": "Key hata di."}


def key_status(tenant: str) -> dict:
    with session() as s:
        rows = s.scalars(select(CyberKey).where(CyberKey.tenant_id == tenant)).all()
        have = {k.provider: k.label for k in rows}
    out = {p: {"label": PROVIDERS[p], "set": p in have, "hint": have.get(p, "")} for p in PROVIDERS}
    if "cloudflare" not in have:
        try:
            from ..site.dns import key as site_key
            if site_key(tenant, "cloudflare")[0]:
                out["cloudflare"]["note"] = "Website wala Cloudflare token hai, par IP block ke liye yahan Zone ID ke saath jodiye."
        except Exception:
            pass
    return out


def _key(tenant: str, provider: str) -> tuple[str, str]:
    from ..bazar.security import vault
    with session() as s:
        k = s.scalars(select(CyberKey).where(CyberKey.tenant_id == tenant, CyberKey.provider == provider)).first()
        if not k:
            return "", ""
        try:
            return vault().open(k.sealed), k.extra
        except ValueError:
            return "", ""


# ---------------------------------------------------------------- 1. alerts: intake, triage, teach
def _alert_view(tenant: str, a: CyberAlert, full: bool = False) -> dict:
    v = {"id": a.id, "number": a.number, "source": a.source, "source_label": R.SOURCES.get(a.source, a.source), "kind": a.kind,
         "label": R.kind_label(a.kind), "title": a.title, "host": a.host, "user": a.user, "ip": a.ip, "count": a.count, "score": a.score,
         "level": a.level, "why": _j(a.why, []), "status": a.status, "first_seen": _iso(a.first_seen), "last_seen": _iso(a.last_seen),
         "last_local": _local(tenant, a.last_seen), "incident_id": a.incident_id, "known_benign": bool(a.rule_id),
         "advice": R.advice(a.kind), "never_mute": a.kind in R.NEVER_MUTE}
    if full:
        v["detail"] = a.detail
    return v


def _rules(s, tenant: str) -> list[dict]:
    return [{"id": r.id, "source": r.source, "kind": r.kind, "host": r.host, "user": r.user, "ip": r.ip, "words": r.words, "reason": r.reason,
             "active": r.active} for r in s.scalars(select(CyberRule).where(CyberRule.tenant_id == tenant, CyberRule.active.is_(True))).all()]


def _hoola_events(tenant: str) -> list[dict]:
    """Hoola's own sign-ins: a new phone asking to approve money cards (approvekey) in the last 7 days."""
    out = []
    try:
        from ..approvekey import ApproveDevice
        since = clock() - timedelta(days=7)
        with session() as s:
            for d in s.scalars(select(ApproveDevice).where(ApproveDevice.tenant_id == tenant)).all():
                if d.status == "pending" or (_aware(d.created_at) or since) >= since:
                    out.append(R._ev("hoola", "new_device" if d.status == "pending" else "login_ok",
                                     f"Hoola: naya phone '{d.label or d.device_id[:8]}' ({d.status})", host="Hoola", user=d.label or "",
                                     detail=f"device={d.device_id[:12]} status={d.status}", at=_iso(d.created_at)))
    except Exception:
        log.debug("hoola events failed", exc_info=True)
    return out


def intake(tenant: str, text: str = "", file_id: str = "", data: bytes | None = None, name: str = "", source: str = "",
           include_hoola: bool = False, actor: str = "owner", conv: str = "") -> dict:
    """Alerts in (paste / file) -> normalised, grouped, scored, deduped -> the few that matter + why."""
    if file_id and data is None:
        from ..analyst.service import _load_file
        try:
            name, data = _load_file(tenant, file_id)
        except Exception as e:
            raise CyberError(str(e))
    if not (text or "").strip() and not data and not include_hoola:
        raise CyberError("Alert ka text chipkaiye ya file (CSV / JSON / log) dijiye.")
    hint = source if source in R.SOURCES else ""
    parsed = R.parse(text=text or "", data=data, name=name or "", hint=hint) if (text or data) else {"events": [], "skipped": 0, "format": "-"}
    events = parsed["events"] + (_hoola_events(tenant) if include_hoola else [])
    if not events:
        return {"new": 0, "matters": [], "watch": 0, "noise": 0, "skipped": parsed["skipped"], "format": parsed["format"],
                "say": f"Koi alert samajh nahi aaya ({parsed['skipped']} line chhodi). Format batayiye ya poora export chipkaiye."}
    batch = secrets.token_hex(6)
    n = clock()
    with _LOCK, session() as s:
        st = _st(s, tenant)
        own, crown = _j(st.own_ips, []), _j(st.crown_hosts, [])
        seen_ok = {(a.user, a.ip) for a in s.scalars(select(CyberAlert).where(CyberAlert.tenant_id == tenant,
                                                                            CyberAlert.kind.in_(("login_ok", "new_ip_login")))).all()}
        found = R.correlate(events, own, seen_ok)
        rules = _rules(s, tenant)
        made, bumped, ids = 0, 0, []
        for e in found:
            fp = R.fingerprint(e)
            rule = next((r for r in rules if R.rule_matches(r, e)), None)
            sc, level, why = R.score(e, own, crown, rule)
            old = s.scalars(select(CyberAlert).where(CyberAlert.tenant_id == tenant, CyberAlert.fp == fp,
                                                     CyberAlert.status.in_(("open", "ack")))).first()
            if old and (_aware(old.last_seen) or n) >= n - timedelta(days=7):
                old.count += int(e.get("count") or 1)
                old.last_seen = n
                if sc > old.score:
                    old.score, old.level, old.why = sc, level, _dump(why)
                old.batch = batch
                ids.append(old.id)
                bumped += 1
                continue
            st.alert_seq += 1
            a = CyberAlert(tenant_id=tenant, number=f"AL-{st.alert_seq:04d}", fp=fp, source=e["source"], kind=e["kind"], title=e["title"],
                           host=e["host"], user=e["user"], ip=e["ip"], detail=e["detail"], count=int(e.get("count") or 1), score=sc,
                           level=level, why=_dump(why), rule_id=rule["id"] if rule else "", group_key=f"{e['kind']}|{e['ip'] or e['user'] or e['host']}",
                           first_seen=n, last_seen=n, batch=batch)
            if rule:
                r = s.get(CyberRule, rule["id"])
                if r:
                    r.hits += 1
            s.add(a)
            s.flush()
            ids.append(a.id)
            made += 1
        rows = [s.get(CyberAlert, i) for i in dict.fromkeys(ids)]
        views = [_alert_view(tenant, a) for a in rows if a]
    matters = sorted([v for v in views if v["level"] == "matters"], key=lambda v: -v["score"])
    watch = [v for v in views if v["level"] == "watch"]
    noise = [v for v in views if v["level"] == "noise"]
    raw = len(events)
    say = (f"{raw} alert padhe -> {len(views)} kahaniyaan. Zaroori: {len(matters)}, nazar rakhein: {len(watch)}, shor: {len(noise)}"
           + (f" ({bumped} purane alerts phir aaye, gine gaye)" if bumped else "") + ".")
    if matters:
        say += " Sabse pehle: " + "; ".join(f"{m['number']} {m['label']} ({m['score']})" for m in matters[:3]) + "."
    else:
        say += " Abhi koi zaroori cheez nahi."
    out = {"new": made, "bumped": bumped, "raw": raw, "matters": matters[:15], "watch": watch[:15], "noise": len(noise),
           "noise_sample": [f"{x['label']}: {x['title']}" for x in noise[:5]], "skipped": parsed["skipped"], "format": parsed["format"],
           "say": say}
    if matters or watch:
        _publish(tenant, "cyber_alerts", {"batch": batch, "say": say, "matters": matters[:5], "watch": len(watch), "noise": len(noise),
                                          "raw": raw}, conv)
    return out


def alerts(tenant: str, level: str = "", status: str = "open", limit: int = 60) -> list[dict]:
    with session() as s:
        q = select(CyberAlert).where(CyberAlert.tenant_id == tenant)
        if level:
            q = q.where(CyberAlert.level == level)
        if status == "open":
            q = q.where(CyberAlert.status.in_(("open", "ack")))
        elif status:
            q = q.where(CyberAlert.status == status)
        rows = s.scalars(q.order_by(CyberAlert.score.desc(), CyberAlert.last_seen.desc()).limit(max(1, min(limit, 300)))).all()
        return [_alert_view(tenant, a) for a in rows]


def _alert(s, tenant: str, ref: str) -> CyberAlert:
    ref = (ref or "").strip()
    a = s.get(CyberAlert, ref)
    if a is None or a.tenant_id != tenant:
        a = s.scalars(select(CyberAlert).where(CyberAlert.tenant_id == tenant, CyberAlert.number == ref.upper())).first()
    if a is None:
        raise CyberError("Alert nahi mila.")
    return a


def get_alert(tenant: str, ref: str) -> dict:
    with session() as s:
        return _alert_view(tenant, _alert(s, tenant, ref), full=True)


def set_alert(tenant: str, ref: str, status: str) -> dict:
    if status not in ("ack", "dismissed", "open"):
        raise CyberError("status ack | dismissed | open")
    with session() as s:
        a = _alert(s, tenant, ref)
        a.status = status
        v = _alert_view(tenant, a)
    return {"alert": v, "say": {"ack": "Dekh liya.", "dismissed": "Hata diya.", "open": "Phir khola."}[status]}


def teach(tenant: str, ref: str, reason: str, scope: str = "", actor: str = "owner") -> dict:
    """Her 'yeh normal hai' (known benign): matching alerts become noise next time (never for NEVER_MUTE kinds)."""
    if not is_owner(actor):
        raise CyberError("Yeh sirf owner sikha sakti hain.")
    reason = R.mask(reason, 300).strip()
    if not reason:
        raise CyberError("Wajah likhiye (jaise 'yeh hamara backup server hai').")
    with _LOCK, session() as s:
        a = _alert(s, tenant, ref)
        sc = scope if scope in ("ip", "user", "host", "kind") else ("ip" if a.ip else "user" if a.user else "host" if a.host else "kind")
        r = CyberRule(tenant_id=tenant, source=a.source, kind=a.kind, reason=reason, ip=a.ip if sc == "ip" else "",
                      user=a.user if sc == "user" else "", host=a.host if sc == "host" else "")
        if sc == "kind" and not (a.ip or a.user or a.host):
            r.words = re.sub(r"\W+", " ", a.title.lower()).strip()[:60]
        s.add(r)
        s.flush()
        never = a.kind in R.NEVER_MUTE
        if not never:
            a.status, a.level, a.score = "dismissed", "noise", min(a.score, 10)
        a.rule_id = r.id
        rid = r.id
    say = ("Seekh liya: aage aise alerts shor mein jayenge." if not never else
           "Note kar liya, par yeh qism (jaise ransomware / login-after-failures / forwarding rule) kabhi chhupaya nahi jaata; "
           "aage yeh note saath dikhega.")
    return {"rule": rid, "scope": sc, "say": say}


def rules_list(tenant: str) -> list[dict]:
    with session() as s:
        out = []
        for r in s.scalars(select(CyberRule).where(CyberRule.tenant_id == tenant).order_by(CyberRule.created_at.desc())).all():
            out.append({"id": r.id, "source": r.source, "kind": r.kind, "label": R.kind_label(r.kind) if r.kind else "", "host": r.host,
                        "user": r.user, "ip": r.ip, "words": r.words, "reason": r.reason, "hits": r.hits, "active": r.active})
        return out


def rule_remove(tenant: str, rid: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise CyberError("Yeh sirf owner kar sakti hain.")
    with session() as s:
        r = s.get(CyberRule, rid)
        if not r or r.tenant_id != tenant:
            raise CyberError("Niyam nahi mila.")
        r.active = False
    return {"ok": True, "say": "Niyam hata diya: aise alerts phir dikhenge."}


# ---------------------------------------------------------------- 2. email / link / file checks
def _own_domains(tenant: str) -> list[str]:
    with session() as s:
        ds = [d.domain for d in s.scalars(select(CyberDomain).where(CyberDomain.tenant_id == tenant)).all()]
        st = _st(s, tenant)
        for e in _j(st.work_emails, []):
            dom = e.split("@")[-1]
            if dom and dom not in ds and not re.search(r"(gmail|yahoo|outlook|hotmail|rediffmail)\.", dom):
                ds.append(dom)
        return ds


def _vips(tenant: str) -> list[str]:
    with session() as s:
        return _j(_st(s, tenant).vip_names, [])


def reputation(tenant: str, urls: list[str]) -> dict[str, Any]:
    """Look links up (never opened) with HER key: Web Risk / Safe Browsing, else VirusTotal url report."""
    urls = [u if re.match(r"^https?://", u, re.I) else "http://" + u for u in urls][:20]
    out: dict[str, Any] = {"checked": False, "provider": "", "bad": {}, "notes": []}
    if not urls:
        return out
    with session() as s:
        prov = _st(s, tenant).link_provider
    key, _ = _key(tenant, prov)
    try:
        if key and prov == "webrisk":
            out.update(checked=True, provider="webrisk")
            for u in urls:
                r = I.webrisk(u, key)
                if r["bad"]:
                    out["bad"][u] = r["threats"]
        elif key and prov == "safebrowsing":
            out.update(checked=True, provider="safebrowsing")
            out["bad"].update(I.safebrowsing(urls, key))
        vk, _ = _key(tenant, "virustotal")
        if vk and not out["bad"]:
            out["provider"] = (out["provider"] + "+virustotal").strip("+")
            out["checked"] = True
            for u in urls[:4]:                    # public API: 4 a minute
                r = I.vt_url(u, vk)
                if r.get("known") and (r["malicious"] >= 2 or (r["malicious"] + r["suspicious"]) >= 4):
                    out["bad"][u] = [f"VirusTotal: {r['malicious']} engines malicious"]
    except I.IntelError as e:
        out["notes"].append(str(e))
    if not out["checked"]:
        out["notes"].append("Link reputation ki key nahi (Niyam > Keys): sirf nishaanon se jaanch hui.")
    return out


def _store_check(tenant: str, kind: str, subject: str, verdict: str, result: dict, hd: str = "") -> str:
    with session() as s:
        c = CyberCheck(tenant_id=tenant, kind=kind, subject=R.mask(subject, 300), verdict=verdict, result=_dump(result), helpdesk_incident=hd)
        s.add(c)
        s.flush()
        return c.id


def check_email(tenant: str, text: str, sender: str = "", links: list | None = None, attachments: list | None = None,
                report: bool = False, actor: str = "owner", conv: str = "", **did: Any) -> dict:
    """A suspicious mail: headers (when pasted with 'Show original') + the helpdesk words check + link reputation. DATA only."""
    from ..helpdesk import rules as HR
    from ..helpdesk.service import scrub
    raw = str(text or "")
    if not raw.strip() and not sender:
        raise CyberError("Mail ka text (behtar: Gmail 'Show original' / Outlook 'View source' poora) chipkaiye. Link mat kholiye.")
    own, vips = _own_domains(tenant), _vips(tenant)
    flags: list[dict[str, str]] = []
    hdr: dict[str, Any] = {}
    body, atts = raw, [str(a) for a in (attachments or [])][:10]
    if R.looks_like_headers(raw):
        hdr = R.headers(raw, own, vips)
        flags += hdr["flags"]
        body = (hdr.get("subject") or "") + "\n" + hdr["body"]
        sender = sender or hdr["from"]
        atts += hdr.get("attachments") or []
    else:
        sdom = sender.split("@")[-1].lower() if "@" in sender else ""
        la = R.lookalike(sdom, own)
        if la:
            flags.append({"id": "lookalike_own", "level": "bad", "text": f"'{sdom}' aapke apne domain '{la}' jaisa dikhta hai, par woh nahi hai."})
    body, found_secret = scrub(body)
    ph = HR.phish_check(body, sender, [str(x) for x in (links or [])][:20], atts)
    for f in ph["flags"]:
        if not any(x["id"] == f["id"] for x in flags):
            flags.append(f)
    urls = list(dict.fromkeys([*(str(x) for x in (links or [])), *re.findall(r"\b(?:https?://|www\.)[^\s<>\"')]+", body)]))[:20]
    for h in R.url_hosts(urls):
        la = R.lookalike(h, own)
        if la:
            flags.append({"id": "lookalike_link_" + h[:30], "level": "bad", "text": f"Link '{h}' aapke domain '{la}' ki nakal hai."})
    rep = reputation(tenant, urls)
    for u, th in rep["bad"].items():
        flags.append({"id": "reputation_" + u[:30], "level": "bad", "text": f"Google / VirusTotal list mein KHATARNAK: {u[:80]} ({', '.join(th)[:60]})"})
    v = R.verdict(flags)
    did_flags = {k: bool(did.get(k)) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")}
    result = {"verdict": v, "flags": flags, "auth": hdr.get("auth", {}), "from": hdr.get("from") or sender, "reply_to": hdr.get("reply_to", ""),
              "subject": hdr.get("subject", ""), "links": urls[:10], "reputation": rep, "attachments": atts, "actions": HR.phish_actions(did_flags),
              "say": R.VERDICT_SAY[v]}
    if found_secret:
        result["say"] += " (Mail mein password / OTP jaisa kuch tha: hata diya; agar kisi ne bhara ho to badaliye.)"
    hd = ""
    if report or any(did_flags.values()):
        from ..helpdesk import service as HS
        r = HS.report_phish(tenant, body[:3000], sender, urls, atts, "phishing", actor=actor, conv=conv, **did_flags)
        hd = r["incident"]["id"]
        result["helpdesk"] = {"incident": r["incident"], "cert_in": r["cert_in"], "dpdp": r["dpdp"], "cert_in_draft": r["cert_in_draft"],
                              "ticket": r["ticket"].get("number")}
        result["say"] += " " + r["say"]
    cid = _store_check(tenant, "email", result["from"] or "(sender nahi)", v, result, hd)
    result["id"] = cid
    result["say"] = (result["say"] + (" " + "; ".join(f["text"] for f in flags if f["level"] == "bad")[:400] if v == "likely_phish" else "")).strip()
    _publish(tenant, "cyber_check", {"check": cid, "kind": "email", "verdict": v, "flags": flags[:8], "say": result["say"],
                                     "subject": result["from"], "actions": result["actions"][:4]}, conv)
    return result


def check_link(tenant: str, urls: list | str, conv: str = "") -> dict:
    """Links only looked up, NEVER opened (not by Hoola's browser, not by the server)."""
    from ..helpdesk import rules as HR
    if isinstance(urls, str):
        urls = re.split(r"[\s,]+", urls)
    urls = [str(u).strip() for u in urls if str(u).strip()][:20]
    if not urls:
        raise CyberError("Link dijiye (kholna nahi hai).")
    own = _own_domains(tenant)
    ph = HR.phish_check(" ".join(urls), "", urls, [])
    flags = [f for f in ph["flags"] if f["id"] not in ("urgency", "bait", "asks_secret", "asks_money")]
    for h in R.url_hosts(urls):
        la = R.lookalike(h, own)
        if la:
            flags.append({"id": "lookalike_link_" + h[:30], "level": "bad", "text": f"'{h}' aapke domain '{la}' ki nakal hai."})
    rep = reputation(tenant, urls)
    for u, th in rep["bad"].items():
        flags.append({"id": "reputation_" + u[:30], "level": "bad", "text": f"KHATARNAK list mein: {u[:80]} ({', '.join(th)[:60]})"})
    v = R.verdict(flags)
    if v == "unclear" and rep["checked"] and not rep["bad"]:
        v = "clean"
    if rep["bad"]:
        v = "malicious"
    say = R.VERDICT_SAY[v] + ("" if rep["checked"] else " (Reputation key nahi: sirf nishaan dekhe.)")
    result = {"verdict": v, "flags": flags, "urls": urls, "reputation": rep, "say": say}
    result["id"] = _store_check(tenant, "link", urls[0], v, result)
    _publish(tenant, "cyber_check", {"check": result["id"], "kind": "link", "verdict": v, "flags": flags[:8], "say": say, "subject": urls[0][:120]}, conv)
    return result


def check_file(tenant: str, file_id: str = "", data: bytes | None = None, name: str = "", sha256: str = "", conv: str = "") -> dict:
    """A file is only HASHED here; the hash (never the file) is looked up on VirusTotal with her key."""
    info: dict[str, Any] = {}
    if file_id and data is None:
        from ..analyst.service import _load_file
        try:
            name, data = _load_file(tenant, file_id)
        except Exception as e:
            raise CyberError(str(e))
    if data is not None:
        sha256 = hashlib.sha256(data).hexdigest()
        info["size"] = len(data)
        try:
            from .. import filecheck
            rt = filecheck.real_type(name or "file", data)
            info.update(real_type=rt.get("label") or "", danger=bool(rt.get("danger")), type_note=rt.get("note") or "")
        except Exception:
            pass
        data = None                                   # the bytes are dropped right here; never stored, never sent
    sha256 = (sha256 or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}|[0-9a-f]{40}|[0-9a-f]{32}", sha256):
        raise CyberError("File ya uska SHA-256 hash dijiye.")
    flags: list[dict[str, str]] = []
    if info.get("danger"):
        flags.append({"id": "type_mismatch", "level": "bad", "text": f"Naam kuch aur kehta hai, andar program / script hai: {info.get('type_note')}"})
    if re.search(R"\.(exe|scr|js|vbs|bat|cmd|ps1|hta|jar|msi|iso|lnk|apk|docm|xlsm)$", name or "", re.I):
        flags.append({"id": "risky_ext", "level": "warn", "text": f"'{name}' chalne wali / macro file hai: anjaan ho to mat kholiye."})
    vt: dict[str, Any] = {}
    key, _ = _key(tenant, "virustotal")
    if key:
        try:
            vt = I.vt_file(sha256, key)
        except I.IntelError as e:
            vt = {"error": str(e)}
        if vt.get("known") and vt.get("malicious", 0) >= 3:
            flags.append({"id": "vt_malicious", "level": "bad", "text": f"VirusTotal: {vt['malicious']} antivirus ise virus kehte hain"
                          + (f" ({vt.get('label')})" if vt.get("label") else "") + "."})
        elif vt.get("known") and vt.get("malicious", 0) >= 1:
            flags.append({"id": "vt_some", "level": "warn", "text": f"VirusTotal: {vt['malicious']} antivirus shak karte hain."})
    v = "malicious" if any(f["id"] == "vt_malicious" for f in flags) else R.verdict(flags)
    if v == "unclear" and vt.get("known") and not flags:
        v = "clean"
    say = R.VERDICT_SAY[v]
    if not key:
        say += " (VirusTotal key nahi: sirf file ki qism dekhi.)"
    elif vt.get("known") is False:
        say += " VirusTotal ne yeh file pehle nahi dekhi (naya / nishaana banaya hua ho sakta hai): anjaan ho to mat kholiye."
    say += " File kahin upload nahi hui, sirf uska hash dekha."
    result = {"verdict": v, "sha256": sha256, "name": (name or "")[:120], "flags": flags, "virustotal": vt, **info, "say": say}
    result["id"] = _store_check(tenant, "file", f"{name or 'file'} {sha256[:16]}", v, result)
    _publish(tenant, "cyber_check", {"check": result["id"], "kind": "file", "verdict": v, "flags": flags, "say": say, "subject": name or sha256[:16]}, conv)
    return result


def checks(tenant: str, kind: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        q = select(CyberCheck).where(CyberCheck.tenant_id == tenant)
        if kind:
            q = q.where(CyberCheck.kind == kind)
        out = []
        for c in s.scalars(q.order_by(CyberCheck.created_at.desc()).limit(limit)).all():
            r = _j(c.result, {})
            out.append({"id": c.id, "kind": c.kind, "subject": c.subject, "verdict": c.verdict, "say": r.get("say", ""),
                        "flags": r.get("flags", [])[:6], "at": _iso(c.created_at), "at_local": _local(tenant, c.created_at),
                        "helpdesk_incident": c.helpdesk_incident})
        return out


# ---------------------------------------------------------------- 3. her own attack surface (passive)
def _norm_domain(d: str) -> str:
    from ..site.dns import DnsError, norm_domain
    try:
        return norm_domain(d)
    except DnsError as e:
        raise CyberError(str(e))


def _dns(name: str, type_: str) -> list[str]:
    """Answers seen by the public resolvers (DoH, site.dns); [] when none."""
    from ..site.dns import lookup
    res = lookup(name, type_)
    vals: list[str] = []
    for v in res.values():
        for x in v:
            if x != "?" and x not in vals:
                vals.append(x)
    return vals


def _tls(host: str) -> dict[str, Any]:
    """Cert expiry of HER host (one TLS handshake to a public address on 443; nothing else sent)."""
    from ..web import WebError, _public_host
    try:
        _public_host(host)
    except WebError as e:
        return {"error": str(e)}
    ctx = ssl.create_default_context()
    out: dict[str, Any] = {}
    try:
        with socket.create_connection((host, 443), timeout=8) as sock, ctx.wrap_socket(sock, server_hostname=host) as ss:
            cert = ss.getpeercert()
        exp = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        out = {"not_after": exp.date().isoformat(), "days_left": (exp - clock()).days, "host_ok": True,
               "issuer": " ".join(v for part in cert.get("issuer", ()) for k, v in part if k in ("organizationName", "commonName"))[:120]}
    except ssl.SSLCertVerificationError as e:
        out = {"days_left": None, "host_ok": False if "hostname" in str(e).lower() else None, "error": str(e)[:160]}
    except (OSError, ValueError) as e:
        out = {"days_left": None, "error": str(e)[:160]}
    return out


def _fetch(url: str, max_bytes: int = 65536) -> tuple[int, dict[str, str], bytes]:
    """One GET to HER own site (public address only, no redirects followed)."""
    import httpx

    from ..web import WebError, _check_url
    try:
        url = _check_url(url)
    except WebError as e:
        raise CyberError(str(e))
    try:
        with httpx.Client(timeout=10, follow_redirects=False, headers={"User-Agent": I.UA}) as c:
            with c.stream("GET", url) as r:
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) >= max_bytes:
                        break
                return r.status_code, dict(r.headers), body[:max_bytes]
    except httpx.HTTPError as e:
        raise CyberError(f"{url} nahi khula ({e.__class__.__name__}).")


def _dom_view(d: CyberDomain) -> dict:
    p = _j(d.posture, {})
    return {"id": d.id, "domain": d.domain, "verified": d.verified, "verified_by": d.verified_by, "token": d.token,
            "verify_record": {"name": f"_hoola-cyber.{d.domain}", "type": "TXT", "value": f"hoola-cyber-verify={d.token}"},
            "score": p.get("score"), "flags": p.get("flags", []), "checked_at": _iso(d.checked_at), "breach": _j(d.breach, {}),
            "tls": p.get("tls", {}), "dns": p.get("dns", {})}


def _dom(s, tenant: str, ref: str) -> CyberDomain:
    d = s.get(CyberDomain, ref)
    if d is None or d.tenant_id != tenant:
        dn = (ref or "").strip().lower()
        d = s.scalars(select(CyberDomain).where(CyberDomain.tenant_id == tenant, CyberDomain.domain == dn)).first()
    if d is None:
        raise CyberError("Yeh domain list mein nahi; pehle 'domain jodo'.")
    return d


def _hosted_by_hoola(tenant: str, domain: str) -> bool:
    try:
        from ..site.hosting import host_map
        for h, v in host_map(force=True).items():
            if v.get("tenant") == tenant and (h == domain or h.endswith("." + domain)):
                return True
    except Exception:
        pass
    return False


def add_domain(tenant: str, domain: str, actor: str = "owner") -> dict:
    dn = _norm_domain(domain)
    with session() as s:
        d = s.scalars(select(CyberDomain).where(CyberDomain.tenant_id == tenant, CyberDomain.domain == dn)).first()
        if d is None:
            if len(s.scalars(select(CyberDomain.id).where(CyberDomain.tenant_id == tenant)).all()) >= 20:
                raise CyberError("20 domain tak.")
            d = CyberDomain(tenant_id=tenant, domain=dn, token=secrets.token_hex(12))
            s.add(d)
            s.flush()
        if not d.verified and _hosted_by_hoola(tenant, dn):
            d.verified, d.verified_by = True, "hoola_site"
        v = _dom_view(d)
    say = (f"{dn} jod diya. Bahar se dikhne wali jaanch (DNS, SSL, headers) abhi ho sakti hai."
           + ("" if v["verified"] else f" Gehri jaanch (khuli .git / .env / admin page) ke liye saabit kijiye ki domain aapka hai: DNS mein TXT "
                                       f"'_hoola-cyber.{dn}' = 'hoola-cyber-verify={v['token']}' daaliye, phir 'verify' kahiye."))
    return {"domain": v, "say": say}


def verify_domain(tenant: str, ref: str) -> dict:
    with session() as s:
        d = _dom(s, tenant, ref)
        dn, tok = d.domain, d.token
    ok_by = ""
    if _hosted_by_hoola(tenant, dn):
        ok_by = "hoola_site"
    else:
        vals = _dns(f"_hoola-cyber.{dn}", "TXT")
        if any(f"hoola-cyber-verify={tok}" in v for v in vals):
            ok_by = "dns"
    with session() as s:
        d = _dom(s, tenant, ref)
        if ok_by:
            d.verified, d.verified_by = True, ok_by
        v = _dom_view(d)
    return {"domain": v, "say": "Pakka: domain aapka hai." if ok_by else "TXT record abhi nahi dikha (DNS mein 5-30 minute lag sakte hain)."}


DKIM_SELECTORS = ("google", "selector1", "selector2", "default", "k1", "zoho", "zmail", "mail", "dkim", "s1", "s2")


def posture(tenant: str, ref: str, conv: str = "", quiet: bool = False) -> dict:
    """Passive check of HER domain: DNS (SPF / DMARC / DKIM / CAA / MX), TLS expiry, security headers of her home page; open
    .git / .env / admin pages only when the domain is proven hers."""
    with session() as s:
        d = _dom(s, tenant, ref)
        dn, verified = d.domain, d.verified
    flags: list[dict[str, str]] = []
    txt = _dns(dn, "TXT")
    mx = _dns(dn, "MX")
    dmarc = _dns(f"_dmarc.{dn}", "TXT")
    caa = _dns(dn, "CAA")
    dkim_found = [sel for sel in DKIM_SELECTORS[:6] if any("v=dkim1" in x.lower() or "p=" in x.lower() for x in _dns(f"{sel}._domainkey.{dn}", "TXT"))]
    if mx:
        flags += R.spf_eval(txt)
        flags += R.dmarc_eval(dmarc)
        if not dkim_found:
            flags.append({"id": "dkim_unknown", "level": "info", "text": "Aam selectors par DKIM nahi mila (Google 'google', Microsoft 'selector1/2'). "
                                                                          "Mail provider mein DKIM on hai, pakka kijiye."})
    else:
        if not any(t.lower().startswith("v=spf1 -all") for t in txt):
            flags.append({"id": "no_mail_spf", "level": "warn", "text": "Is domain se mail nahi jaata: 'v=spf1 -all' + DMARC p=reject daal dijiye "
                                                                         "taaki koi aapke naam se naqli mail na bheje."})
    if not caa:
        flags.append({"id": "caa_missing", "level": "info", "text": "CAA record nahi: koi bhi certificate company aapke domain ka SSL bana sakti hai."})
    tls = _tls(dn)
    flags += R.tls_eval(tls.get("days_left"), tls.get("host_ok"), tls.get("issuer", ""))
    hdrs: dict[str, str] = {}
    exposed: list[str] = []
    try:
        code, hdrs, _ = _fetch(f"https://{dn}/", 4096)
        if code in (301, 302, 307, 308) and str(hdrs.get("location", "")).startswith("https://www."):
            code, hdrs, _ = _fetch(f"https://www.{dn}/", 4096)
        flags += R.headers_eval(hdrs)
    except CyberError as e:
        flags.append({"id": "site_down", "level": "info", "text": f"Website nahi khuli: {e}"})
    if verified and hdrs:
        for path, test, lvl, say in R.EXPOSED_PATHS:
            try:
                c, _, b = _fetch(f"https://{dn}{path}", 2048)
            except CyberError:
                continue
            if test(c, b):
                flags.append({"id": "exposed" + path.replace("/", "_"), "level": lvl, "text": say})
                exposed.append(path)
    elif not verified:
        flags.append({"id": "not_verified", "level": "info", "text": "Gehri jaanch (.git / .env / admin page) tab hogi jab domain aapka saabit ho."})
    sc = R.posture_score(flags)
    p = {"score": sc, "flags": flags, "tls": tls, "dns": {"mx": mx[:5], "spf": [t for t in txt if t.lower().startswith("v=spf1")][:2],
                                                         "dmarc": dmarc[:1], "caa": caa[:4], "dkim": dkim_found}, "exposed": exposed}
    with session() as s:
        d = _dom(s, tenant, ref)
        d.posture = _dump(p)
        d.checked_at = clock()
        v = _dom_view(d)
    bad = [f for f in flags if f["level"] == "bad"]
    say = f"{dn}: suraksha score {sc}/100." + (" Sabse pehle: " + " ".join(f["text"] for f in bad[:2]) if bad else " Koi badi kami nahi mili.")
    if not quiet:
        _publish(tenant, "cyber_posture", {"domain": dn, "score": sc, "flags": flags[:10], "say": say}, conv)
    return {"domain": v, "say": say}


def domains(tenant: str) -> list[dict]:
    with session() as s:
        return [_dom_view(d) for d in s.scalars(select(CyberDomain).where(CyberDomain.tenant_id == tenant).order_by(CyberDomain.domain)).all()]


def remove_domain(tenant: str, ref: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise CyberError("Yeh sirf owner kar sakti hain.")
    with session() as s:
        s.delete(_dom(s, tenant, ref))
    return {"ok": True, "say": "Domain hata diya."}


def _mask_mail(e: str) -> str:
    local, _, dom = e.partition("@")
    return (local[:2] + "***" + (local[-1:] if len(local) > 3 else "") + "@" + dom) if dom else e


def breach(tenant: str, ref: str = "", conv: str = "") -> dict:
    """Her work emails / her verified domain on Have I Been Pwned (her key). Only breach names and what leaked."""
    key, _ = _key(tenant, "hibp")
    if not key:
        raise CyberError("Have I Been Pwned key nahi (haveibeenpwned.com/API/Key, paid). Niyam > Keys mein jodiye.")
    found: dict[str, list[str]] = {}
    notes: list[str] = []
    if ref:
        dn = _norm_domain(ref)
        try:
            for alias, bl in I.hibp_domain(dn, key).items():
                found[f"{alias}@{dn}"] = bl
        except I.IntelError as e:
            notes.append(str(e))
    else:
        with session() as s:
            emails = _j(_st(s, tenant).work_emails, [])
        if not emails:
            raise CyberError("Niyam mein office ke email likhiye (ya domain dijiye).")
        import time
        for e in emails[:25]:
            try:
                bl = I.hibp_account(e, key)
            except I.IntelError as ex:
                notes.append(str(ex))
                break
            if bl:
                found[e] = bl
            if SLEEP_BETWEEN_S:
                time.sleep(SLEEP_BETWEEN_S)
    names = sorted({b for bl in found.values() for b in bl})
    info = {n: I.hibp_breach(n) for n in names[:15]}
    rows = [{"email": _mask_mail(e), "breaches": [{"name": b, "title": info.get(b, {}).get("Title", b), "date": info.get(b, {}).get("BreachDate", ""),
                                                   "leaked": (info.get(b, {}).get("DataClasses") or [])[:6]} for b in bl]} for e, bl in found.items()]
    pw = sum(1 for r in rows for b in r["breaches"] if any("password" in x.lower() for x in b["leaked"]))
    say = (f"{len(rows)} email purane data leak mein mile ({len(names)} leak)." + (f" {pw} jagah password bhi leak hua tha: un logon ka password "
           "badalwaiye + 2-step on." if pw else "") if rows else "Kisi bhi email ka naam kisi jaane-maane leak mein nahi mila.")
    say += (" " + " ".join(notes)) if notes else ""
    if ref:
        with session() as s:
            try:
                d = _dom(s, tenant, ref)
                d.breach = _dump({"rows": rows, "at": _iso(clock())})
            except CyberError:
                pass
    if rows:
        _publish(tenant, "cyber_alerts", {"say": say, "matters": [], "breach": rows[:10]}, conv)
    return {"rows": rows, "notes": notes, "say": say}


# ---------------------------------------------------------------- advisories (CVE / KEV / CERT-In)
def _sw_view(w: CyberSoftware) -> dict:
    return {"id": w.id, "vendor": w.vendor, "product": w.product, "version": w.version, "cpe": w.cpe, "where": w.where, "from_asset": w.from_asset}


def add_software(tenant: str, product: str, vendor: str = "", version: str = "", cpe: str = "", where: str = "", from_asset: str = "") -> dict:
    product = R.mask(product, 120).strip()
    if not product:
        raise CyberError("Software / device ka naam dijiye (jaise 'Tally Prime', 'Windows 10', 'TP-Link Archer C6').")
    if cpe and not cpe.startswith("cpe:2.3:"):
        raise CyberError("CPE 'cpe:2.3:...' jaisa hona chahiye (ya khaali chhodiye).")
    with session() as s:
        old = s.scalars(select(CyberSoftware).where(CyberSoftware.tenant_id == tenant, CyberSoftware.product == product,
                                                    CyberSoftware.vendor == vendor.lower(), CyberSoftware.active.is_(True))).first()
        if old:
            if version:
                old.version = version[:40]
            return {"software": _sw_view(old), "say": "Pehle se list mein."}
        w = CyberSoftware(tenant_id=tenant, product=product, vendor=vendor.lower()[:80], version=version[:40], cpe=cpe[:200], where=where[:120],
                          from_asset=from_asset[:40])
        s.add(w)
        s.flush()
        return {"software": _sw_view(w), "say": f"{product} jod diya: iske naye khatre (CVE / CERT-In) dekhta rahunga."}


def remove_software(tenant: str, ref: str) -> dict:
    with session() as s:
        w = s.get(CyberSoftware, ref)
        if not w or w.tenant_id != tenant:
            raise CyberError("Nahi mila.")
        w.active = False
    return {"ok": True, "say": "Hata diya."}


def software(tenant: str) -> list[dict]:
    with session() as s:
        return [_sw_view(w) for w in s.scalars(select(CyberSoftware).where(CyberSoftware.tenant_id == tenant, CyberSoftware.active.is_(True))).all()]


def sync_assets(tenant: str) -> dict:
    """IT Helpdesk asset register (OS of each PC, router / NVR models) -> software list (read-only)."""
    from ..helpdesk.service import assets
    added = 0
    for a in assets(tenant):
        for row in R.from_asset(a):
            r = add_software(tenant, row["product"], row["vendor"], row["version"], "", row["where"], a["id"])
            if r["say"] != "Pehle se list mein.":
                added += 1
    return {"added": added, "software": software(tenant), "say": f"IT Helpdesk ke devices se {added} cheezein judi."}


def refresh_advisories(tenant: str, days: int = 30, conv: str = "") -> dict:
    sw = software(tenant)
    if not sw:
        return {"new": 0, "say": "Software list khaali: pehle software / devices jodiye (ya 'helpdesk se lo')."}
    key, _ = _key(tenant, "nvd")
    notes: list[str] = []
    found: list[dict[str, Any]] = []
    try:
        kev = I.kev()
    except I.IntelError as e:
        kev, _ = [], notes.append(str(e))
    try:
        cert = I.certin_feed()
    except I.IntelError as e:
        cert, _ = [], notes.append(str(e))
    kev_ids = {k.get("cveID") for k in kev}
    import time
    for w in sw:
        for k in kev:
            if R.kev_match(k, w["vendor"], w["product"]):
                found.append({"ref": k.get("cveID"), "source": "kev", "title": f"{k.get('vendorProject')} {k.get('product')}: {k.get('vulnerabilityName')}",
                              "summary": f"{k.get('shortDescription') or ''} Kya karna: {k.get('requiredAction') or ''}", "score": 0.0, "severity": "EXPLOITED",
                              "exploited": True, "sw": w["id"], "url": f"https://nvd.nist.gov/vuln/detail/{k.get('cveID')}", "published": k.get("dateAdded", "")})
        try:
            rows = I.nvd(keyword=("" if w["cpe"] else w["product"]), cpe=w["cpe"], days=days, key=key)
        except I.IntelError as e:
            notes.append(str(e))
            rows = []
        toks = R.soft_tokens("", w["product"]) or R.soft_tokens(w["vendor"], "")
        for c in rows:
            if not w["cpe"] and toks and not all(t in c["summary"].lower() for t in toks[:2]):
                continue
            found.append({"ref": c["id"], "source": "nvd", "title": f"{w['product']}: {c['id']}", "summary": c["summary"], "score": c["score"],
                          "severity": c["severity"], "exploited": c["id"] in kev_ids, "sw": w["id"], "url": c["url"], "published": c["published"]})
        for a in cert:
            blob = (a["title"] + " " + a["summary"]).lower()
            if toks and all(t in blob for t in toks[:2]):
                found.append({"ref": a["link"] or a["title"], "source": "certin", "title": "CERT-In: " + a["title"], "summary": a["summary"],
                              "score": 0.0, "severity": "", "exploited": False, "sw": w["id"], "url": a["link"], "published": a["published"]})
        if SLEEP_BETWEEN_S:
            time.sleep(SLEEP_BETWEEN_S if key else max(SLEEP_BETWEEN_S, 6.5))
    new = []
    with session() as s:
        for f in found:
            if s.scalars(select(CyberAdvisory).where(CyberAdvisory.tenant_id == tenant, CyberAdvisory.ref == str(f["ref"])[:120],
                                                     CyberAdvisory.software_id == f["sw"])).first():
                continue
            a = CyberAdvisory(tenant_id=tenant, ref=str(f["ref"])[:120], source=f["source"], title=R.mask(f["title"], 300), summary=R.mask(f["summary"], 2000),
                              score=float(f["score"] or 0), severity=str(f["severity"])[:12], exploited=bool(f["exploited"]), software_id=f["sw"],
                              url=str(f["url"])[:400], published=str(f["published"])[:25])
            s.add(a)
            s.flush()
            new.append(_adv_view(s, a))
        _st(s, tenant).last_intel = today(tenant).isoformat()
    urgent = [a for a in new if a["exploited"] or a["score"] >= 9 or a["source"] == "certin"]
    say = (f"{len(new)} naye khatre aapke software se mile" + (f", {len(urgent)} zaroori (hamle ho rahe / critical)" if urgent else "") + "."
           if new else "Aapke software ke liye koi naya khatra nahi mila.") + ((" " + notes[0]) if notes else "")
    if urgent:
        _publish(tenant, "cyber_advisory", {"say": say, "advisories": urgent[:6]}, conv)
    return {"new": len(new), "urgent": urgent[:10], "notes": notes, "say": say}


def _adv_view(s, a: CyberAdvisory) -> dict:
    w = s.get(CyberSoftware, a.software_id) if a.software_id else None
    return {"id": a.id, "ref": a.ref, "source": a.source, "title": a.title, "summary": a.summary[:500], "score": a.score, "severity": a.severity,
            "exploited": a.exploited, "url": a.url, "published": a.published, "status": a.status,
            "software": f"{w.product} {w.version}".strip() if w else "", "where": w.where if w else "",
            "say": ("Is par hamle ho rahe hain (CISA KEV): jaldi update / patch kijiye. " if a.exploited else "")
            + (f"Aapka version {w.version} hai: maker ki site par dekhiye ki fix kis version mein hai." if w and w.version else "Apna version maker ki site par mila lijiye.")}


def advisories(tenant: str, status: str = "new") -> list[dict]:
    with session() as s:
        q = select(CyberAdvisory).where(CyberAdvisory.tenant_id == tenant)
        if status:
            q = q.where(CyberAdvisory.status == status)
        rows = s.scalars(q.order_by(CyberAdvisory.exploited.desc(), CyberAdvisory.score.desc()).limit(100)).all()
        return [_adv_view(s, a) for a in rows]


def mark_advisory(tenant: str, ref: str, status: str) -> dict:
    if status not in ("patched", "not_ours", "ignored", "new"):
        raise CyberError("status patched | not_ours | ignored")
    with session() as s:
        a = s.get(CyberAdvisory, ref)
        if not a or a.tenant_id != tenant:
            raise CyberError("Nahi mila.")
        a.status = status
    return {"ok": True, "say": {"patched": "Theek: update ho gaya likha.", "not_ours": "Theek: yeh hamare version par lagoo nahi.",
                                "ignored": "Hata diya.", "new": "Phir khola."}[status]}


# ---------------------------------------------------------------- 4. incident note
KIND_MAP = {"brute_force": "intrusion", "login_after_fail": "account", "suspicious_login": "account", "new_ip_login": "account",
            "leaked_password": "account", "forwarding_rule": "account", "suspicious_sending": "account", "admin_granted": "account",
            "impossible_travel": "account", "device_compromised": "intrusion", "gov_attack": "intrusion", "ransomware": "ransomware",
            "malware_active": "malware", "malware_spread": "malware", "malware_blocked": "malware", "waf_bypass": "website",
            "new_device": "account"}


def _inc_view(tenant: str, i: CyberIncident, full: bool = True) -> dict:
    v = {"id": i.id, "number": i.number, "kind": i.kind, "title": i.title, "status": i.status, "detected_at": _iso(i.detected_at),
         "detected_local": _local(tenant, i.detected_at), "personal_data": i.personal_data, "systems": i.systems,
         "helpdesk_incident": i.helpdesk_incident, "closed_at": _iso(i.closed_at)}
    if full:
        v.update(what=i.what, impact=i.impact, done=i.done, lessons=i.lessons, timeline=_j(i.timeline, []), alert_ids=_j(i.alert_ids, []),
                 check_ids=_j(i.check_ids, []))
        hd = {}
        if i.helpdesk_incident:
            try:
                from ..helpdesk.service import incidents as hinc
                hd = next((x for x in hinc(tenant) if x["id"] == i.helpdesk_incident), {})
            except Exception:
                hd = {}
        v["cert_in"] = hd.get("cert_in", {})
        v["cert_in_due"] = hd.get("report_due_local", "")
        v["cert_in_reported"] = hd.get("reported_at", "")
        from ..helpdesk import rules as HR
        dp = HR.dpdp(i.personal_data, today(tenant))
        v["dpdp"] = dp
        with session() as s:
            v["actions"] = [_act_view(a) for a in s.scalars(select(CyberAction).where(CyberAction.tenant_id == tenant,
                                                                                      CyberAction.incident_id == i.id)).all()]
    return v


def _inc(s, tenant: str, ref: str) -> CyberIncident:
    i = s.get(CyberIncident, ref)
    if i is None or i.tenant_id != tenant:
        i = s.scalars(select(CyberIncident).where(CyberIncident.tenant_id == tenant, CyberIncident.number == (ref or "").upper())).first()
    if i is None:
        raise CyberError("Incident nahi mila.")
    return i


def _tl(i: CyberIncident, what: str, by: str = "Hoola", at: datetime | None = None) -> None:
    t = _j(i.timeline, [])
    t.append({"at": _iso(at or clock()), "by": by[:60], "what": R.mask(what, 400)})
    t.sort(key=lambda x: x["at"])
    i.timeline = _dump(t[-200:])


def new_incident(tenant: str, title: str = "", kind: str = "", alert_ids: list | None = None, check_ids: list | None = None, what: str = "",
                 systems: str = "", personal_data: bool = False, clock_start: bool = True, actor: str = "owner", conv: str = "",
                 **did: Any) -> dict:
    """Open the incident note from alerts / checks; the CERT-In clock + DPDP note come from the IT Helpdesk's incident record."""
    from ..helpdesk import rules as HR
    by = actor_name(tenant, actor)
    al, ck = [str(x) for x in (alert_ids or [])][:30], [str(x) for x in (check_ids or [])][:10]
    with _LOCK, session() as s:
        st = _st(s, tenant)
        rows = []
        for ref in al:
            try:
                rows.append(_alert(s, tenant, ref))
            except CyberError:
                pass
        k = kind if kind in HR.PHISH_KIND else ""
        if not k and rows:
            k = KIND_MAP.get(max(rows, key=lambda a: a.score).kind, "other")
        if not k and ck:
            k = "phishing"
        k = k or "other"
        first = min([_aware(a.first_seen) for a in rows] or [clock()])
        st.incident_seq += 1
        i = CyberIncident(tenant_id=tenant, number=f"IN-{st.incident_seq:04d}", kind=k, title=R.mask(title or (rows[0].title if rows else HR.PHISH_KIND[k]), 240),
                          what=R.mask(what, 3000), personal_data=bool(personal_data), detected_at=clock(), conv=conv,
                          systems=R.mask(systems or ", ".join(sorted({a.host for a in rows if a.host}))[:240], 240),
                          alert_ids=_dump([a.id for a in rows]), check_ids=_dump(ck))
        s.add(i)
        s.flush()
        for a in rows:
            _tl(i, f"{a.number} {R.kind_label(a.kind)}: {a.title}" + (f" (x{a.count})" if a.count > 1 else ""), R.SOURCES.get(a.source, a.source),
                _aware(a.first_seen))
            a.status, a.incident_id = "incident", i.id
        for cid in ck:
            c = s.get(CyberCheck, cid)
            if c and c.tenant_id == tenant:
                _tl(i, f"Jaanch ({c.kind}): {c.subject} -> {c.verdict}", "Hoola", _aware(c.created_at))
        _tl(i, f"Incident note khola ({by})", by)
        if not i.what and rows:
            i.what = "; ".join(f"{R.kind_label(a.kind)}: {a.title}" for a in rows[:5])
        iid = i.id
        helpdesk_inc = next((s.get(CyberCheck, c).helpdesk_incident for c in ck if s.get(CyberCheck, c) and s.get(CyberCheck, c).helpdesk_incident), "")
        i.helpdesk_incident = helpdesk_inc or ""
        _ = first
    if clock_start and not helpdesk_inc and k in ("phishing", "malware", "ransomware", "account", "data_leak", "intrusion", "payment", "website"):
        cert_in(tenant, iid, actor=actor, conv=conv, **did)
    v = get_incident(tenant, iid)
    say = f"{v['number']} khola: {v['title']}."
    if v.get("cert_in_due"):
        say += f" CERT-In 6 ghante: aakhri samay {v['cert_in_due']} (draft IT Helpdesk ke card par)."
    elif v.get("cert_in", {}).get("why"):
        say += " CERT-In: " + v["cert_in"]["why"]
    if v.get("dpdp"):
        say += " " + v["dpdp"]["say"]
    _publish(tenant, "cyber_incident", {"incident": {k2: v[k2] for k2 in ("id", "number", "title", "kind", "status", "detected_local", "cert_in_due")},
                                        "say": say}, conv)
    return {"incident": v, "say": say}


def cert_in(tenant: str, ref: str, actor: str = "owner", conv: str = "", **did: Any) -> dict:
    """Start (or show) the CERT-In 6-hour clock through the IT Helpdesk incident record (same draft, same reminders)."""
    from ..helpdesk import service as HS
    with session() as s:
        i = _inc(s, tenant, ref)
        if i.helpdesk_incident:
            return {"incident": _inc_view(tenant, i), "say": "CERT-In clock pehle se chal raha hai."}
        kind, summ, sys_, pd = i.kind, i.what or i.title, i.systems, i.personal_data
    flags = {k: bool(did.get(k)) for k in ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")}
    r = HS.report_phish(tenant, (f"[Cyber {i.number}] {summ}" + (f" | Systems: {sys_}" if sys_ else ""))[:3000], "", [], [], kind if kind in ("phishing", "malware", "ransomware", "account",
                        "data_leak", "payment", "intrusion", "website", "other") else "other", "", "", pd, actor=actor, conv=conv, **flags)
    with session() as s:
        i = _inc(s, tenant, ref)
        i.helpdesk_incident = r["incident"]["id"]
        _tl(i, "CERT-In / DPDP jaanch shuru (IT Helpdesk incident " + (r["ticket"].get("number") or "") + ")")
        v = _inc_view(tenant, i)
    return {"incident": v, "cert_in": r["cert_in"], "cert_in_draft": r["cert_in_draft"], "say": r["say"]}


def incident_add(tenant: str, ref: str, what: str, at: str = "", actor: str = "owner") -> dict:
    when = None
    if at:
        try:
            when = datetime.fromisoformat(at.replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=_tz(tenant))
        except ValueError:
            raise CyberError("Samay 2026-10-23T14:30 jaisa.")
    with session() as s:
        i = _inc(s, tenant, ref)
        _tl(i, what, actor_name(tenant, actor), when)
        v = _inc_view(tenant, i)
    return {"incident": v, "say": "Timeline mein joda."}


def incident_update(tenant: str, ref: str, actor: str = "owner", **kw: Any) -> dict:
    with session() as s:
        i = _inc(s, tenant, ref)
        for k in ("title", "what", "impact", "done", "lessons", "systems"):
            if kw.get(k):
                setattr(i, k, R.mask(str(kw[k]), 3000 if k != "title" else 240))
        if "personal_data" in kw and kw["personal_data"] is not None:
            i.personal_data = bool(kw["personal_data"])
        v = _inc_view(tenant, i)
    return {"incident": v, "say": "Note update."}


def incident_close(tenant: str, ref: str, lessons: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise CyberError("Incident sirf owner band kar sakti hain.")
    with session() as s:
        i = _inc(s, tenant, ref)
        if lessons:
            i.lessons = R.mask(lessons, 3000)
        if not i.lessons:
            raise CyberError("Band karne se pehle 'seekh' likhiye (aage aisa na ho, iske liye kya badla).")
        waiting = s.scalars(select(CyberAction).where(CyberAction.tenant_id == tenant, CyberAction.incident_id == i.id,
                                                      CyberAction.status == "waiting")).first()
        if waiting:
            raise CyberError(f"{waiting.number} abhi aapki haan ka intezaar kar raha hai: pehle us par faisla.")
        i.status, i.closed_at = "closed", clock()
        _tl(i, "Incident band", actor_name(tenant, actor))
        v = _inc_view(tenant, i)
    return {"incident": v, "say": f"{v['number']} band."}


def get_incident(tenant: str, ref: str) -> dict:
    with session() as s:
        return _inc_view(tenant, _inc(s, tenant, ref))


def incidents(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(CyberIncident).where(CyberIncident.tenant_id == tenant)
        if status:
            q = q.where(CyberIncident.status == status)
        return [_inc_view(tenant, i, full=False) for i in s.scalars(q.order_by(CyberIncident.detected_at.desc()).limit(50)).all()]


def note_text(tenant: str, ref: str) -> tuple[str, str]:
    v = get_incident(tenant, ref)
    st = settings(tenant)
    office = (st.get("office") or {}).get("office_name") or "[office ka naam]"
    ci = v.get("cert_in") or {}
    lines = [f"Office: {office}", f"Incident: {v['number']} ({v['kind']})", f"Pata chala: {v['detected_local']}", f"Systems: {v['systems'] or '[ ]'}", "",
             "## Kya hua", v["what"] or "[ ]", "", "## Asar (impact)", v["impact"] or "[ ]", "", "## Timeline"]
    for t in v["timeline"]:
        lines.append(f"- {t['at'].replace('T', ' ')} · {t['by']}: {t['what']}")
    lines += ["", "## Kya kiya gaya", v["done"] or "[ ]"]
    for a in v.get("actions") or []:
        lines.append(f"- {a['number']} {a['label']} {a['target']}: {a['status_label']}")
    lines += ["", "## CERT-In (6 ghante)", (ci.get("why") or "IT Helpdesk incident nahi khula.")]
    if v.get("cert_in_due"):
        lines.append(f"- Aakhri samay: {v['cert_in_due']}" + (f"; report bheja: {v['cert_in_reported']}" if v.get("cert_in_reported") else "; abhi nahi bheja"))
    lines += ["", "## DPDP", (v["dpdp"] or {}).get("say") or "Personal data shamil nahi (ya pata nahi).", "", "## Seekh (lessons)", v["lessons"] or "[ ]",
              "", "Yeh note Hoola ne aapke diye tathyon se banaya; kanooni salah nahi."]
    return f"Cyber incident note {v['number']}", "\n".join(lines)


def _pdf(title: str, text: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape
    bio = io.BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=A4, title=title)
    ss = getSampleStyleSheet()
    flow = [Paragraph(escape(title), ss["Title"])]
    for ln in text.splitlines():
        if ln.startswith("## "):
            flow += [Spacer(1, 6), Paragraph(escape(ln[3:]), ss["Heading2"])]
        elif ln.strip():
            flow.append(Paragraph(escape(ln), ss["BodyText"]))
    doc.build(flow)
    return bio.getvalue()


def note_files(tenant: str, ref: str, conv: str = "") -> dict:
    from .. import chatfiles
    from ..officegen import make_docx
    title, text = note_text(tenant, ref)
    v = get_incident(tenant, ref)
    files = []
    f1 = chatfiles.store(tenant, f"{v['number']}_incident_note.docx", make_docx(title, text),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    files.append(f1)
    try:
        f2 = chatfiles.store(tenant, f"{v['number']}_incident_note.pdf", _pdf(title, text), "application/pdf")
        files.append(f2)
    except Exception:
        log.exception("incident pdf failed")
    for f in files:
        _publish(tenant, "pc_file", {**f, "source": "cyber", "title": title}, conv)
    with session() as s:
        _tl(_inc(s, tenant, ref), "Incident note file (Word" + (" + PDF" if len(files) > 1 else "") + ")")
    return {"files": files, "text": text, "say": f"{v['number']} ka incident note Word" + (" aur PDF" if len(files) > 1 else "") + " mein."}


# ---------------------------------------------------------------- 5. containment: cards, only her tap
STEPS = {
    "block_ip": ["Cloudflare dashboard > domain > Security > WAF > Tools > IP Access Rules: IP likhiye, 'Block', 'This website'.",
                 "Router / firewall: us IP ke liye 'drop' rule (router ke admin page par).",
                 "Linux server: `sudo ufw deny from <IP>` (aapke admin ke haath)."],
    "unblock_ip": ["Cloudflare > Security > WAF > Tools > IP Access Rules: us IP ka rule delete."],
    "disable_user": ["Google Workspace: admin.google.com > Directory > Users > user > 'Suspend user'.",
                     "Microsoft 365: admin.microsoft.com > Users > Active users > user > 'Block sign-in'.",
                     "Hoola ka IT Admin Sahayak bhi yeh card ke saath kar sakta hai (jahan woh juda ho)."],
    "reset_sessions": ["Google Workspace: user > Security > 'Sign-in cookies: Reset' + naya password, 'change at next sign-in'.",
                       "Microsoft 365: user > 'Revoke sessions' + 'Reset password'.",
                       "Gmail personal: myaccount.google.com > Security > Your devices > Sign out."],
    "quarantine": ["Microsoft Defender: security.microsoft.com > Alert / file > 'Stop and quarantine file'.",
                   "Quick Heal / Seqrite console: Reports / Quarantine > file chunkar 'Quarantine'.", "PC par: antivirus > Full scan > Quarantine."],
    "isolate_pc": ["Microsoft Defender for Endpoint: device page > 'Isolate device'.", "Ya seedha: LAN cable nikaliye / Wi-Fi band (PC band mat kijiye)."],
    "wipe_device": ["Google Workspace: admin.google.com > Devices > Mobile > device > 'Wipe device' (ya sirf 'Wipe account').",
                    "Microsoft Intune: intune.microsoft.com > Devices > device > 'Wipe'.",
                    "Apna Android phone: android.com/find > 'Factory reset device'. iPhone: icloud.com/find > 'Erase'."],
}
RISK = {"block_ip": "Agar yeh IP aapke apne staff / customer ka nikla to unki site band ho jayegi (undo ho sakta hai).",
        "disable_user": "Woh insaan kaam nahi kar payega jab tak wapas on na ho.",
        "reset_sessions": "Us user ko har device par dobara login karna padega.",
        "quarantine": "File kaam ki ho to program chalna band ho sakta hai (quarantine se wapas la sakte hain).",
        "isolate_pc": "PC ka net band: us par chal raha kaam rukega.",
        "wipe_device": "HAMESHA KE LIYE: device ka data mit jayega, wapas nahi aayega.", "unblock_ip": "IP phir se site khol payega."}
UNDO = {"block_ip": "unblock_ip card (aapki haan se)", "disable_user": "Admin console mein 'Reactivate' / 'Unblock'",
        "quarantine": "Antivirus quarantine se 'Restore'", "isolate_pc": "Defender 'Release from isolation' / cable lagaiye", "wipe_device": "Koi undo nahi",
        "reset_sessions": "-", "unblock_ip": "block_ip card"}
STATUS_LABEL = {"waiting": "Aapki haan ka intezaar", "done": "Ho gaya", "approved": "Haan di: console mein kijiye", "rejected": "Mana kiya",
                "failed": "Nahi hua", "stale": "Purana (24 ghante)", "undone": "Wapas"}


def _act_view(a: CyberAction) -> dict:
    return {"id": a.id, "number": a.number, "kind": a.kind, "label": R.ACTIONS.get(a.kind, a.kind), "target": a.target, "reason": a.reason,
            "via": a.via, "steps": _j(a.steps, []), "risk": a.risk, "undo": a.undo, "hash": a.hash, "status": a.status,
            "status_label": STATUS_LABEL.get(a.status, a.status), "result": _j(a.result, {}), "incident_id": a.incident_id, "alert_id": a.alert_id,
            "asked_by": a.asked_by, "created_at": _iso(a.created_at), "wipe": a.kind in R.WIPE_KINDS}


def _act_hash(kind: str, target: str, via: str, extra: str = "") -> str:
    return hashlib.sha256(f"{kind}|{target}|{via}|{extra}".encode()).hexdigest()[:32]


def request_action(tenant: str, kind: str, target: str, reason: str = "", incident: str = "", alert: str = "", actor: str = "owner",
                   conv: str = "") -> dict:
    """Make a containment CARD. Nothing is blocked / disabled / wiped here; only her tap (decide_action by_tap) can."""
    if kind not in R.ACTIONS:
        raise CyberError("kind: " + ", ".join(R.ACTIONS))
    target = R.mask(target, 200).strip()
    extra = ""
    with session() as s:
        st = _st(s, tenant)
        own = _j(st.own_ips, [])
        if alert and not target:
            a = _alert(s, tenant, alert)
            target = a.ip if kind == "block_ip" else (a.user or a.host)
            alert = a.id
    if not target:
        raise CyberError("Kis par? (IP / user / device ka naam).")
    via = "steps"
    if kind in ("block_ip", "unblock_ip"):
        if kind == "block_ip":
            net = target
            try:
                n = __import__("ipaddress").ip_network(net, strict=False)
            except ValueError:
                raise CyberError(f"'{target}' sahi IP nahi.")
            if not n.is_global:
                raise CyberError("Yeh local / private IP hai: internet wale IP hi Cloudflare par block hote hain.")
            if (n.version == 4 and n.prefixlen < 24) or (n.version == 6 and n.prefixlen < 48):
                raise CyberError("Itna bada IP range block nahi karte (IPv4 /24 tak, IPv6 /48 tak).")
            for o in own:
                try:
                    if __import__("ipaddress").ip_network(o, strict=False).overlaps(n):
                        raise CyberError("Yeh aapka apna office / server IP hai (Niyam): block nahi karenge.")
                except ValueError:
                    continue
            target = str(n) if n.num_addresses > 1 else str(n.network_address)
        else:
            extra = target                         # rule id (or ip) to remove
        tok, zone = _key(tenant, "cloudflare")
        if tok and zone:
            via, extra = "cloudflare", (extra + "|" + zone)
    with _LOCK, session() as s:
        dup = s.scalars(select(CyberAction).where(CyberAction.tenant_id == tenant, CyberAction.kind == kind, CyberAction.target == target,
                                                  CyberAction.status == "waiting")).first()
        if dup:
            v = _act_view(dup)
            return {"action": v, "say": f"{v['number']} pehle se aapki haan ka intezaar kar raha hai."}
        st = _st(s, tenant)
        st.action_seq += 1
        a = CyberAction(tenant_id=tenant, number=f"CA-{st.action_seq:04d}", kind=kind, target=target, reason=R.mask(reason, 500), via=via,
                        steps=_dump(STEPS.get(kind, [])), risk=RISK.get(kind, ""), undo=UNDO.get(kind, ""), incident_id=incident, alert_id=alert,
                        asked_by=actor_name(tenant, actor), conv=conv)
        a.hash = _act_hash(kind, target, via, extra)
        a.result = _dump({"extra": extra} if extra else {})
        s.add(a)
        s.flush()
        if incident:
            try:
                _tl(_inc(s, tenant, incident), f"{a.number} {R.ACTIONS[kind]} {target}: card bheja (aapki haan ka intezaar)")
            except CyberError:
                pass
        v = _act_view(a)
    say = (f"{v['number']}: {v['label']} '{target}' ka card bheja; aapke tap ke bina kuch nahi hoga."
           + (" Haan par Hoola aapke Cloudflare mein khud karega." if via == "cloudflare" else " Haan ke baad console mein yeh steps kijiye.")
           + (" Mitane ke liye fingerprint bhi lagega." if kind in R.WIPE_KINDS else ""))
    _publish(tenant, "cyber_action", {"action": v, "say": say}, conv)
    return {"action": v, "say": say, "needs_tap": True}


def _action_digest(v: dict) -> str:
    return hashlib.sha256(_dump({k: v[k] for k in ("kind", "target", "via", "reason", "hash")}).encode()).hexdigest()


def action_needs_fingerprint(tenant: str, aid: str) -> bool:
    from .. import approvekey as ak
    with session() as s:
        a = s.get(CyberAction, aid)
        return bool(a and a.tenant_id == tenant and a.kind in R.WIPE_KINDS and ak.active_on(tenant))


def action_challenge(tenant: str, aid: str) -> dict:
    """Same signed-challenge format as approvekey (kind 'cyber'): the phone signs this card as it is now."""
    from .. import approvekey as ak
    with session() as s:
        a = s.get(CyberAction, aid)
        if a is None or a.tenant_id != tenant or a.status != "waiting":
            raise CyberError("Yeh card ab baaki nahi hai.")
        v = _act_view(a)
    digest = _action_digest(v)
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|cyber|{aid}|{digest}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="cyber", target=aid, digest=digest, message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    return {"challenge_id": chid, "message": msg, "show": {"title": f"{v['label']}: {v['target']}"}, "expires_at": exp.isoformat()}


def decide_action(tenant: str, aid: str, yes: bool, card_hash: str = "", proof: dict | None = None, reason: str = "",
                  by_tap: bool = False) -> dict:
    """ONLY her tap in the app (API). The tool can never reach this."""
    if not by_tap:
        raise CyberError("Block / wipe ki haan sirf aapke tap se (app ka card).")
    with session() as s:
        a = s.get(CyberAction, aid)
        if a is None or a.tenant_id != tenant:
            raise CyberError("Card nahi mila.")
        if a.status != "waiting":
            raise CyberError(f"Yeh card pehle hi '{STATUS_LABEL.get(a.status, a.status)}' hai.")
        if not card_hash or card_hash != a.hash:
            raise CyberError("Card badal gaya hai; naya card dekhiye.")
        v = _act_view(a)
    if yes and v["wipe"]:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            if not proof:
                raise CyberError("fingerprint_needed")
            with session() as s:
                ak._settle(s, tenant)
                ok = ak._check(s, tenant, "cyber", aid, proof, _action_digest(v))
            if not ok:
                raise CyberError("fingerprint_invalid")
    result: dict[str, Any] = dict(v["result"])
    status = "rejected"
    if yes:
        status = "approved"
        if v["via"] == "cloudflare":
            tok, zone = _key(tenant, "cloudflare")
            try:
                if not tok:
                    raise I.IntelError("Cloudflare key ab nahi hai.")
                if v["kind"] == "block_ip":
                    r = I.cf_block_ip(tok, zone, v["target"], f"Hoola {v['number']}: {v['reason'][:120]}")
                    result.update(rule_id=r["rule_id"], zone=zone)
                else:
                    rid = (result.get("extra") or "").split("|")[0] or v["target"]
                    with session() as s:
                        prev = s.scalars(select(CyberAction).where(CyberAction.tenant_id == tenant, CyberAction.kind == "block_ip",
                                                                   CyberAction.target == v["target"], CyberAction.status == "done")).first()
                        if prev and _j(prev.result, {}).get("rule_id"):
                            rid = _j(prev.result, {})["rule_id"]
                            prev.status = "undone"
                    I.cf_unblock(tok, zone, rid)
                status = "done"
            except I.IntelError as e:
                status, result["error"] = "failed", str(e)
    with session() as s:
        a = s.get(CyberAction, aid)
        a.status, a.decided_at, a.result = status, clock(), _dump({**result, "reason": R.mask(reason, 300)} if reason else result)
        if a.incident_id:
            try:
                _tl(_inc(s, tenant, a.incident_id), f"{a.number} {R.ACTIONS[a.kind]} {a.target}: "
                    + {"done": "Hoola ne kar diya (aapki haan)", "approved": "aapne haan di", "rejected": "aapne mana kiya",
                       "failed": "nahi hua: " + str(result.get("error", ""))}[status], "Owner")
            except CyberError:
                pass
        v = _act_view(a)
    say = {"done": f"{v['number']}: {v['label']} {v['target']} ho gaya.", "approved": f"{v['number']}: haan mil gayi. Ab console mein steps kijiye, phir 'ho gaya' dabaiye.",
           "rejected": f"{v['number']}: mana kiya, kuch nahi badla.", "failed": f"{v['number']}: nahi hua ({result.get('error', '')}). Steps se khud kar sakti hain."}[status]
    _publish(tenant, "cyber_action", {"action": v, "say": say}, v.get("conv", ""))
    return {"action": v, "say": say}


def action_done(tenant: str, aid: str, ok: bool = True, note: str = "", actor: str = "owner") -> dict:
    with session() as s:
        a = s.get(CyberAction, aid)
        if a is None or a.tenant_id != tenant:
            raise CyberError("Card nahi mila.")
        if a.status != "approved":
            raise CyberError("Pehle card par aapki haan chahiye." if a.status == "waiting" else "Yeh card is haal mein nahi.")
        a.status = "done" if ok else "failed"
        a.result = _dump({**_j(a.result, {}), "note": R.mask(note, 300), "by": actor_name(tenant, actor)})
        if a.incident_id:
            try:
                _tl(_inc(s, tenant, a.incident_id), f"{a.number} {R.ACTIONS[a.kind]} {a.target}: " + ("console mein kar diya" if ok else "nahi hua")
                    + (f" ({note[:100]})" if note else ""), actor_name(tenant, actor))
            except CyberError:
                pass
        v = _act_view(a)
    return {"action": v, "say": "Darj." if ok else "Darj: nahi hua."}


def actions(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(CyberAction).where(CyberAction.tenant_id == tenant)
        if status:
            q = q.where(CyberAction.status == status)
        return [_act_view(a) for a in s.scalars(q.order_by(CyberAction.created_at.desc()).limit(60)).all()]


# ---------------------------------------------------------------- the day + worker
def day(tenant: str) -> dict:
    m = alerts(tenant, "matters", "open", 20)
    w = alerts(tenant, "watch", "open", 20)
    waiting = actions(tenant, "waiting")
    incs = incidents(tenant, "open")
    adv = [a for a in advisories(tenant, "new") if a["exploited"] or a["score"] >= 9 or a["source"] == "certin"]
    doms = domains(tenant)
    weak = [d for d in doms if d["score"] is not None and d["score"] < 70]
    tls_soon = [d for d in doms if (d["tls"] or {}).get("days_left") is not None and d["tls"]["days_left"] <= 14]
    bits = []
    if m:
        bits.append(f"{len(m)} zaroori alert ({m[0]['number']} {m[0]['label']})")
    if waiting:
        bits.append(f"{len(waiting)} block / wipe card aapki haan ke intezaar mein")
    if incs:
        bits.append(f"{len(incs)} incident khule")
    if adv:
        bits.append(f"{len(adv)} zaroori software khatre ({adv[0]['ref']})")
    if tls_soon:
        bits.append("SSL jaldi khatam: " + ", ".join(d["domain"] for d in tls_soon[:2]))
    if weak:
        bits.append("Kamzor domain setting: " + ", ".join(f"{d['domain']} {d['score']}/100" for d in weak[:2]))
    say = ("Suraksha: " + "; ".join(bits) + ".") if bits else "Suraksha: sab shaant, koi zaroori alert nahi."
    return {"say": say, "matters": m, "watch": w, "waiting": waiting, "incidents": incs, "advisories": adv[:10], "domains": doms,
            "checks": checks(tenant, limit=10), "settings": settings(tenant)}


def overview(tenant: str) -> dict:
    d = day(tenant)
    return {**d, "rules": rules_list(tenant), "software": software(tenant), "actions": actions(tenant), "all_advisories": advisories(tenant, "")[:40],
            "providers": PROVIDERS, "action_kinds": R.ACTIONS}


def _tenants() -> list[str]:
    with session() as s:
        return sorted({r for r in s.scalars(select(CyberSettings.tenant_id)).all()})


def _due(tenant: str, n: datetime) -> tuple[bool, str]:
    with session() as s:
        r = s.get(CyberSettings, tenant)
        if r is None:
            return False, ""
        loc = n.astimezone(_tz(tenant))
        if r.last_morning == loc.date().isoformat():
            return False, loc.date().isoformat()
        try:
            hh, mm = (int(x) for x in (r.morning_time or "09:15").split(":"))
        except ValueError:
            hh, mm = 9, 15
        return (loc.hour, loc.minute) >= (hh, mm), loc.date().isoformat()


def tick(when: datetime | None = None, net: bool = True) -> dict:
    """Worker, every minute: stale cards after 24 h; once a day at her morning time: advisories (if a software list), weekly domain
    re-check (SSL expiry), the morning note (only when there is something)."""
    n = _aware(when) or now()
    out = {"stale": 0, "morning": 0, "intel": 0, "posture": 0}
    with session() as s:
        for a in s.scalars(select(CyberAction).where(CyberAction.status == "waiting")).all():
            if (_aware(a.created_at) or n) < n - timedelta(hours=ACTION_WAIT_H):
                a.status = "stale"
                out["stale"] += 1
    for tenant in _tenants():
        try:
            due, day_s = _due(tenant, n)
            if not due:
                continue
            with session() as s:
                st = _st(s, tenant)
                st.last_morning = day_s
                do_intel = st.last_intel != day_s
                do_post = not st.last_posture or (date.fromisoformat(day_s) - date.fromisoformat(st.last_posture)).days >= 7
            if net and do_intel and software(tenant):
                refresh_advisories(tenant)
                out["intel"] += 1
            if net and do_post:
                for d in domains(tenant):
                    try:
                        posture(tenant, d["id"], quiet=True)
                        out["posture"] += 1
                    except Exception:
                        log.info("posture failed for %s", d["domain"])
                with session() as s:
                    _st(s, tenant).last_posture = day_s
            d = day(tenant)
            if d["matters"] or d["waiting"] or d["incidents"] or d["advisories"] or any(
                    (x["tls"] or {}).get("days_left") is not None and x["tls"]["days_left"] <= 14 for x in d["domains"]):
                _publish(tenant, "cyber_day", {"say": d["say"], "matters": len(d["matters"]), "waiting": len(d["waiting"]),
                                               "incidents": len(d["incidents"]), "advisories": len(d["advisories"])})
                out["morning"] += 1
        except Exception:
            log.exception("cyber tick failed for %s", tenant)
    return out

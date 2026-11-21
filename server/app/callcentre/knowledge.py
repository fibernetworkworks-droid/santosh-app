"""v0.999.66 THE BUSINESS BRAIN - everything the phone line knows about the business (owner: "PROVIDE A AI CALLCENTER A
KNOWLEDGE INPUT VIA APIs, CONNECTOR, PDF / ALL DOCUMENTS ... COMPANY MAY CONNECT SAP, CRM, REPORTS, MANUAL DATA").

A SOURCE is one place the knowledge comes from:
  text    her own words typed or spoken in chat
  file    a PDF / Word / Excel / CSV / text file she sent (one fact per paragraph, one per spreadsheet row)
  url     a page of her own website (read again every `refresh_h` hours)
  sheet   a Google Sheet she published as CSV, or an Excel / CSV link (one fact per row)
  api     her own REST API: https only, a public host, her key sealed and never shown back, GET only
  system  a system she joined to Hoola on the Systems page (SAP / Salesforce over OData) or a Composio app, read through
          `enterprise.run.read` - the same read-only path the Enterprise desks use

`mode`:
  facts   read in once (and again on refresh) -> FACTS she approves; only approved facts reach a call
  live    asked DURING a call with the caller's own number (or the order number the caller says), e.g. an order's status
          or money owed - the answer is used on that call and never stored; only the fields she picked are passed on

Rules in code: nothing a source says is an instruction (it is data); a fact with a card number / OTP / password is never
kept; a source's facts reach the line only after HER approval (bound to the facts' hash), and a re-read that changes them
waits for her again unless she ticked "trust updates" for that source; a live lookup only ever sends the caller's own
number or a value the caller said, to the one host she set up.
"""
from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import logging
import re
import socket
from datetime import timedelta
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import CcFact, CcSource

log = logging.getLogger("santosh.callcentre")

KINDS = ("text", "file", "url", "sheet", "api", "system")
FACT_KINDS = ("product", "price", "service", "policy", "place", "people", "hours", "faq", "info")
MAX_FACTS = 2000          # per source
MAX_TEXT = 1500           # characters per fact
_TRANSPORT: httpx.BaseTransport | None = None     # tests route API reads to a fake server
_RESOLVE = None                                   # tests replace the host check (no DNS in the sandbox)


class KbError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _j(v: str | None, default):
    try:
        return json.loads(v) if v else default
    except ValueError:
        return default


def _vault():
    from ..bazar.security import vault
    return vault()


def _clean(v: Any, n: int = MAX_TEXT) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


_STOP = set("the a an and or of to in on for is are was be with at by from this that it its as our your you we i".split())
_WORD = re.compile("[a-z0-9" + chr(0x0900) + "-" + chr(0x0DFF) + "]+")     # Latin + every Indian script


def words_of(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if len(w) > 1 and w not in _STOP]


def _secret_free(text: str) -> bool:
    return R.secret_in(text) not in ("otp_pin", "password", "card", "cvv")


def _kind_of(text: str) -> str:
    low = text.lower()
    for k, pat in (("price", r"(₹|rs\.?|inr|\$|usd|€|£|aed|price|rate|cost|fees?|charges?)\s*\d|\d\s*(rupees|/-)"),
                   ("policy", r"refund|return|cancel|warranty|guarantee|exchange|policy|terms"),
                   ("hours", r"\b(open|close[sd]?|timing|hours|mon|tue|sun)\b"),
                   ("place", r"address|branch|located|location|road|street|nagar|pin ?code"),
                   ("people", r"\b(manager|doctor|dr\.|owner|staff|team|contact person)\b")):
        if re.search(pat, low):
            return k
    return "info"


# ---------------------------------------------------------------- reading a source into facts
def _guard_host(url: str) -> str:
    """https, a public host. Returns the host. A private / local address is refused (her server's own network)."""
    u = urlparse(url if "://" in url else "https://" + url)
    if u.scheme != "https" or not u.hostname:
        raise KbError("Only an https:// address can be used.")
    host = u.hostname
    if _RESOLVE is not None:
        ips = _RESOLVE(host)
    else:
        try:
            ips = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                ips = [ipaddress.ip_address(i[4][0]) for i in socket.getaddrinfo(host, 443)]
            except socket.gaierror:
                raise KbError(f"{host} could not be found.")
    if not ips or any(not ip.is_global for ip in ips):
        raise KbError("That address is inside a private network; Hoola only reads public addresses.")
    return host


def _rows_to_facts(rows: list[dict[str, Any]], title_key: str = "") -> list[dict[str, str]]:
    out = []
    for r in rows[:MAX_FACTS]:
        if not isinstance(r, dict):
            continue
        pairs = [(str(k).strip(), _clean(v, 300)) for k, v in r.items() if str(k).strip() and _clean(v, 300)]
        if not pairs:
            continue
        title = _clean(r.get(title_key) if title_key else pairs[0][1], 200)
        text = "; ".join(f"{k}: {v}" for k, v in pairs)[:MAX_TEXT]
        out.append({"title": title, "text": text})
    return out


def _text_to_facts(body: str) -> list[dict[str, str]]:
    """Q / A lines become one fact each; else one fact per paragraph (headings carried into their paragraph)."""
    body = (body or "").replace("\r", "")
    qa = R.parse_faq_text(body)
    if len(qa) >= 2:
        return [{"title": _clean(f["q"], 200), "text": _clean(f"{f['q']} {f['a']}"), "kind": "faq"} for f in qa]
    out, head = [], ""
    for para in re.split(r"\n\s*\n", body):
        p = para.strip()
        if not p:
            continue
        if len(p) < 60 and "\n" not in p and not p.endswith("."):
            head = p
            continue
        lines = p.split("\n")
        title = head or lines[0][:120]
        for i in range(0, len(p), MAX_TEXT):
            out.append({"title": _clean(title, 200), "text": _clean((head + ": " if head else "") + p[i:i + MAX_TEXT])})
        head = ""
        if len(out) >= MAX_FACTS:
            break
    return out


def _csv_rows(data: bytes) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig", "ignore")
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def _sheet_rows(name: str, data: bytes) -> list[dict[str, Any]]:
    if name.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows: list[dict[str, Any]] = []
        for ws in wb.worksheets[:5]:
            it = ws.iter_rows(values_only=True)
            head = [str(h or "").strip() for h in next(it, [])]
            for vals in it:
                if any(v not in (None, "") for v in vals):
                    rows.append({head[i] or f"col{i + 1}": v for i, v in enumerate(vals) if i < len(head)})
        return rows
    return _csv_rows(data)


def _get(url: str, headers: dict[str, str] | None = None) -> httpx.Response:
    _guard_host(url)
    with httpx.Client(timeout=15, transport=_TRANSPORT, follow_redirects=False) as c:
        r = c.get(url, headers=headers or {})
    if r.status_code in (301, 302, 303, 307, 308):
        raise KbError("That address redirects somewhere else; give the final address.")
    if r.status_code >= 400:
        raise KbError(f"The address answered {r.status_code}.")
    if len(r.content) > 8_000_000:
        raise KbError("That is too large (over 8 MB).")
    return r


def _api_headers(src: CcSource) -> dict[str, str]:
    cfg = _j(src.config, {})
    h = {"Accept": "application/json", "User-Agent": "Hoola-CallCentre/1"}
    if src.secret:
        key = _vault().open(src.secret)
        name = str(cfg.get("header") or "Authorization")
        h[name] = (str(cfg.get("prefix") or "Bearer") + " " + key).strip() if name.lower() == "authorization" else key
    return h


def _json_rows(data: Any, path: str = "") -> list[dict[str, Any]]:
    for part in [p for p in (path or "").split(".") if p]:
        if isinstance(data, dict):
            data = data.get(part)
    from ..enterprise.run import _rows_of
    rows = _rows_of(data)
    return [r for r in rows if isinstance(r, dict)]


def _read(tenant: str, src: CcSource) -> list[dict[str, str]]:
    cfg = _j(src.config, {})
    if src.kind == "text":
        return _text_to_facts(str(cfg.get("text") or ""))
    if src.kind == "file":
        from ..mailbox import service as ms
        try:
            name, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": cfg.get("file_id")}])[0]
        except Exception as e:      # noqa: BLE001
            raise KbError(f"That file was not found ({e}).")
        if name.lower().endswith((".csv", ".xlsx", ".xlsm")):
            return _rows_to_facts(_sheet_rows(name, data), str(cfg.get("title") or ""))
        if name.lower().endswith((".txt", ".md")):
            return _text_to_facts(data.decode("utf-8", "ignore"))
        from ..docread import read_text
        body = (read_text(name, "", data, limit=200000) or {}).get("text", "")
        if not body.strip():
            raise KbError("No readable text in this file (a photo? send it in the chat and Hoola reads it).")
        return _text_to_facts(body)
    if src.kind == "url":
        r = _get(str(cfg.get("url") or ""))
        body = r.text
        if "html" in r.headers.get("content-type", "") or body.lstrip().startswith("<"):
            body = re.sub(r"(?is)<(script|style|nav|footer|noscript)[^>]*>.*?</\1>", " ", body)
            body = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n\n", body)
            body = re.sub(r"<[^>]+>", " ", body)
            import html as _h
            body = _h.unescape(body)
        return _text_to_facts(body)
    if src.kind == "sheet":
        url = str(cfg.get("url") or "")
        m = re.search(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)", url)
        if m:
            gid = re.search(r"gid=(\d+)", url)
            url = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv" + (f"&gid={gid.group(1)}" if gid else "")
        r = _get(url)
        return _rows_to_facts(_sheet_rows(url.split("?")[0], r.content), str(cfg.get("title") or ""))
    if src.kind == "api":
        r = _get(str(cfg.get("url") or ""), _api_headers(src))
        try:
            data = r.json()
        except ValueError:
            raise KbError("The API did not answer with JSON.")
        return _rows_to_facts(_pick(_json_rows(data, str(cfg.get("path") or "")), cfg.get("fields")), str(cfg.get("title") or ""))
    if src.kind == "system":
        from ..enterprise import run as ER
        try:
            got = ER.read(tenant, str(cfg.get("role") or "erp"), str(cfg.get("system") or ""), str(cfg.get("target") or ""),
                          cfg.get("query") or {}, int(cfg.get("limit") or 500))
        except Exception as e:      # noqa: BLE001 - the system's own refusal, said plainly
            raise KbError(f"{cfg.get('system') or 'The system'} did not answer: {e}")
        return _rows_to_facts(_pick([r for r in got.get("rows") or [] if isinstance(r, dict)], cfg.get("fields")),
                              str(cfg.get("title") or ""))
    raise KbError("Unknown source kind.")


def _pick(rows: list[dict[str, Any]], fields: Any) -> list[dict[str, Any]]:
    """Only the columns she picked (when she picked some): a CRM row has things the phone line must never say."""
    if not fields:
        return rows
    keep = [str(f) for f in fields][:40]
    return [{k: r.get(k) for k in keep if k in r} for r in rows]


def _facts_hash(facts: list[dict[str, str]]) -> str:
    return hashlib.sha256(json.dumps([[f["title"], f["text"]] for f in facts], ensure_ascii=False).encode()).hexdigest()[:24]


# ---------------------------------------------------------------- her side
def _view(s: CcSource) -> dict[str, Any]:
    cfg = _j(s.config, {})
    cfg.pop("text", None)
    return {"id": s.id, "kind": s.kind, "name": s.name, "mode": s.mode, "status": s.status, "facts": s.facts,
            "trust_updates": s.trust_updates, "refresh_h": s.refresh_h, "error": s.error, "hash": s.hash,
            "synced_at": s.synced_at.isoformat() if s.synced_at else None, "has_key": bool(s.secret), "config": cfg}


def add_source(tenant: str, kind: str, name: str = "", mode: str = "facts", text: str = "", file_id: str = "", url: str = "",
               api_key: str = "", header: str = "", prefix: str = "", path: str = "", fields: list[str] | None = None,
               lookup: str = "", system: str = "", role: str = "", target: str = "", query: dict | None = None,
               refresh_h: int = 24, trust_updates: bool = False, title: str = "") -> dict[str, Any]:
    """Add a source and read it at once. Its facts wait for her approval."""
    kind = (kind or "").lower()
    if kind not in KINDS:
        raise KbError("kind = text | file | url | sheet | api | system")
    mode = "live" if mode == "live" else "facts"
    if mode == "live" and kind != "api" and kind != "system":
        raise KbError("Only an API or a joined system can be asked live during a call.")
    if text and not _secret_free(text):
        raise KbError("Do not put an OTP / PIN / password / card number in the business knowledge.")
    cfg: dict[str, Any] = {"title": title}
    if kind == "text":
        if len((text or "").strip()) < 10:
            raise KbError("Write a little more about the business.")
        cfg["text"] = text[:200000]
    elif kind == "file":
        if not file_id:
            raise KbError("Attach the file first (file_id).")
        cfg["file_id"] = file_id
    elif kind in ("url", "sheet", "api"):
        if not url:
            raise KbError("Give the address (url).")
        if kind == "api" and mode == "live" and "{" not in url:
            raise KbError("A live lookup address needs a place for the value, e.g. https://api.example.com/orders?phone={phone}")
        _guard_host(url.replace("{phone}", "0").replace("{value}", "0"))
        cfg.update({"url": url, "path": path, "header": header, "prefix": prefix})
    else:      # system
        if not (system and target):
            raise KbError("Name the joined system and what to read (system + target), e.g. SAP + A_Product.")
        cfg.update({"system": system, "role": role or "erp", "target": target, "query": query or {}})
    if fields:
        cfg["fields"] = [str(f) for f in fields][:40]
    if lookup:
        cfg["lookup"] = lookup[:200]        # what the line asks it for, e.g. "order status by the caller's number"
    sealed = _vault().seal(api_key) if api_key else ""
    with session() as s:
        src = CcSource(tenant_id=tenant, kind=kind, name=_clean(name or url or system or kind, 120), mode=mode,
                       config=json.dumps(cfg, ensure_ascii=False), secret=sealed, refresh_h=max(0, int(refresh_h or 0)),
                       trust_updates=bool(trust_updates))
        s.add(src)
        s.flush()
        sid = src.id
    if mode == "live":
        with session() as s:
            src = s.get(CcSource, sid)
            src.status = "waiting"
            return _view(src) | {"say": "Live lookup saved. The line uses it only after you approve it."}
    return sync(tenant, sid)


def sync(tenant: str, source_id: str) -> dict[str, Any]:
    """(Re)read one source. New / changed facts wait for her unless the source is trusted and was approved before."""
    with session() as s:
        src = s.get(CcSource, source_id)
        if src is None or src.tenant_id != tenant:
            raise KbError("No such source.")
        if src.mode == "live":
            return _view(src)
        try:
            facts = _read(tenant, src)
        except KbError as e:
            src.status, src.error, src.synced_at = "failed", str(e)[:500], now()
            return _view(src) | {"say": f"Could not read it: {e}"}
        kept = []
        for f in facts:
            t = _clean(f.get("text"))
            if t and _secret_free(t):
                kept.append({"title": _clean(f.get("title"), 200) or t[:80], "text": t,
                             "kind": f.get("kind") if f.get("kind") in FACT_KINDS else _kind_of(t)})
        h = _facts_hash(kept)
        same = bool(src.hash) and h == src.hash
        stay = src.status == "approved" and (same or src.trust_updates)
        s.query(CcFact).filter(CcFact.source_id == src.id).delete()
        for f in kept:
            s.add(CcFact(tenant_id=tenant, source_id=src.id, kind=f["kind"], title=f["title"], text=f["text"],
                         words=" ".join(words_of(f["title"] + " " + f["text"])), status="approved" if stay else "draft"))
        src.facts, src.error, src.synced_at = len(kept), "", now()
        if stay:
            src.hash = h
        else:
            src.status = "waiting"
        v = _view(src)
        v["pending_hash"] = h
    if not stay:
        _card(tenant, v)
    return v | {"say": f"{v['facts']} facts read from {v['name']}. "
                       + ("They are live." if stay else "They reach calls only after you approve them.")}


def _card(tenant: str, v: dict[str, Any]) -> None:
    try:
        from . import service as S
        S.publish(tenant, "callcentre_knowledge", v | {"say": f"{v['facts']} facts from {v['name']} wait for your OK"})
    except Exception:      # noqa: BLE001 - a card failing never loses the facts
        log.exception("knowledge card failed")


def preview(tenant: str, source_id: str, limit: int = 30) -> dict[str, Any]:
    with session() as s:
        src = s.get(CcSource, source_id)
        if src is None or src.tenant_id != tenant:
            raise KbError("No such source.")
        rows = s.scalars(select(CcFact).where(CcFact.source_id == source_id).limit(limit)).all()
        facts = [{"id": f.id, "kind": f.kind, "title": f.title, "text": f.text, "status": f.status} for f in rows]
        cur = [{"title": f.title, "text": f.text} for f in s.scalars(select(CcFact).where(CcFact.source_id == source_id)).all()]
        return _view(src) | {"facts_preview": facts, "pending_hash": _facts_hash(cur) if src.mode == "facts" else _live_hash(src)}


def _live_hash(src: CcSource) -> str:
    return hashlib.sha256(src.config.encode()).hexdigest()[:24]


def approve(tenant: str, source_id: str, hash_: str, yes: bool = True) -> dict[str, Any]:
    """HER tap: the facts she saw (by their hash) go live on the line - or the source is switched off."""
    with session() as s:
        src = s.get(CcSource, source_id)
        if src is None or src.tenant_id != tenant:
            raise KbError("No such source.")
        if not yes:
            src.status = "off"
            s.query(CcFact).filter(CcFact.source_id == src.id).update({"status": "draft"})
            return _view(src) | {"say": "Switched off: the line will not use it."}
        if src.mode == "live":
            if hash_ != _live_hash(src):
                raise KbError("The lookup changed since you saw it; look again.")
            src.status, src.hash = "approved", hash_
            return _view(src) | {"say": "Live lookup approved."}
        cur = [{"title": f.title, "text": f.text} for f in s.scalars(select(CcFact).where(CcFact.source_id == src.id)).all()]
        if hash_ != _facts_hash(cur):
            raise KbError("The facts changed since you saw them; look again.")
        s.query(CcFact).filter(CcFact.source_id == src.id).update({"status": "approved"})
        src.status, src.hash = "approved", hash_
        return _view(src) | {"say": f"{src.facts} facts are now used on calls."}


def remove(tenant: str, source_id: str) -> dict[str, Any]:
    with session() as s:
        src = s.get(CcSource, source_id)
        if src is None or src.tenant_id != tenant:
            raise KbError("No such source.")
        s.query(CcFact).filter(CcFact.source_id == src.id).delete()
        s.delete(src)
    return {"removed": source_id}


def sources(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [_view(x) for x in s.scalars(select(CcSource).where(CcSource.tenant_id == tenant)
                                            .order_by(CcSource.created_at.desc())).all()]


def refresh_due(limit: int = 10) -> int:
    """Worker: re-read sources whose refresh time came (url / sheet / api / system)."""
    n = 0
    with session() as s:
        rows = s.scalars(select(CcSource).where(CcSource.mode == "facts", CcSource.refresh_h > 0,
                                                CcSource.kind.in_(("url", "sheet", "api", "system")),
                                                CcSource.status.in_(("approved", "waiting", "failed")))).all()
        due = [(x.tenant_id, x.id) for x in rows
               if x.synced_at is None or _aware(x.synced_at) < now() - timedelta(hours=x.refresh_h)][:limit]
    for t, sid in due:
        try:
            sync(t, sid)
            n += 1
        except Exception:      # noqa: BLE001
            log.exception("knowledge refresh %s failed", sid)
    return n


def _aware(d):
    from datetime import timezone
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- the line's side
def search(tenant: str, question: str, k: int = 3) -> list[dict[str, Any]]:
    """The best approved facts for a question (word overlap, title words count double, close spellings count)."""
    q = set(words_of(question))
    if not q:
        return []
    with session() as s:
        rows = s.scalars(select(CcFact).where(CcFact.tenant_id == tenant, CcFact.status == "approved")).all()
        live = {x.id for x in s.scalars(select(CcSource).where(CcSource.tenant_id == tenant,
                                                                CcSource.status == "approved")).all()}
        scored = []
        for f in rows:
            if f.source_id not in live:
                continue
            w = set((f.words or "").split())
            tw = set(words_of(f.title))
            hit = sum(2 if x in tw else 1 for x in q if x in w)
            hit += sum(0.5 for x in q if x not in w and len(x) > 4 and any(y.startswith(x[:5]) for y in w))
            if hit:
                scored.append((hit / (len(q) + 1), f))
        scored.sort(key=lambda x: -x[0])
        return [{"kind": f.kind, "title": f.title, "text": f.text, "score": round(sc, 2)} for sc, f in scored[:k] if sc >= 0.25]


def live_sources(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [{"id": x.id, "name": x.name, "lookup": _j(x.config, {}).get("lookup") or x.name}
                for x in s.scalars(select(CcSource).where(CcSource.tenant_id == tenant, CcSource.mode == "live",
                                                          CcSource.status == "approved")).all()]


def lookup(tenant: str, source_id: str, caller: str, value: str = "") -> dict[str, Any]:
    """A live question during a call. Only the caller's own number, or a value the caller said (an order number), is
    sent - to the host she set up. Only the fields she picked come back. Never stored."""
    with session() as s:
        src = s.get(CcSource, source_id)
        if src is None or src.tenant_id != tenant or src.mode != "live" or src.status != "approved":
            return {"error": "That lookup is not set up."}
        cfg = _j(src.config, {})
        kind = src.kind
        headers = _api_headers(src) if kind == "api" else {}
    val = re.sub(r"[^A-Za-z0-9\-_/]", "", str(value or ""))[:40]
    if kind == "api":
        url = str(cfg.get("url") or "")
        if "{value}" in url and not val:
            return {"error": "Ask the caller for the number to look up."}
        url = url.replace("{phone}", quote(caller or "", safe="")).replace("{value}", quote(val, safe=""))
        try:
            r = _get(url, headers)
            data = r.json()
        except (KbError, ValueError) as e:
            return {"error": f"Could not check right now ({e}). Offer a call-back."}
        rows = _pick(_json_rows(data, str(cfg.get("path") or "")), cfg.get("fields"))
    else:
        from ..enterprise import run as ER
        q = dict(cfg.get("query") or {})
        for k, v in list(q.items()):
            if isinstance(v, str):
                q[k] = v.replace("{phone}", caller or "").replace("{value}", val)
        try:
            got = ER.read(tenant, str(cfg.get("role") or "erp"), str(cfg.get("system") or ""), str(cfg.get("target") or ""), q, 5)
        except Exception as e:      # noqa: BLE001
            return {"error": f"Could not check right now ({e}). Offer a call-back."}
        rows = _pick([x for x in got.get("rows") or [] if isinstance(x, dict)], cfg.get("fields"))
    rows = [{k: _clean(v, 200) for k, v in r.items() if _secret_free(_clean(v, 200))} for r in rows[:5]]
    return {"found": bool(rows), "rows": rows,
            "say": "Tell the caller only what these rows say. If nothing was found, say so and offer a call-back."}

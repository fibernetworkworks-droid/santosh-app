"""v0.116 DigiLocker requester (Meri Pehchaan OAuth 2.0 + PKCE, Requester API spec v2.x).

The SERVER is the requester (Newtika onboards once at DigiLocker / API Setu; DIGILOCKER_CLIENT_ID / SECRET only in the VPS
.env). Each owner connects HER OWN DigiLocker:
  start     -> authorize URL (response_type=code, scope=openid, state, PKCE S256, optional req_doctype). The app opens it;
               she signs in on DigiLocker's own page (her OTP goes there, never to Hoola) and consents there.
  callback  -> code + PKCE verifier -> token (POST /public/oauth2/2/token), sealed with the bazar vault, kept 1 hour
               (refresh token kept sealed when DigiLocker gives one). The issued-documents list is read at once.
  issued    -> GET /public/oauth2/2/files/issued (name, doctype, issuer, uri, date).
  fetch     -> GET /public/oauth2/1/file/<uri>; the `hmac` header (HMAC-SHA256 of the file, keyed with the client
               secret) is checked; the file becomes HER file (file_id) for her own forms / Computer Operator uploads /
               an email she taps to send. Aadhaar is never pulled (the e-Aadhaar XML API is not used at all): Aadhaar
               stays in DigiLocker; its number can go in her Pehchaan Locker.
  guard     -> an ID document pulled from DigiLocker (PAN, DL, RC, voter ID, passport, ration card...) never goes to
               another person's avatar (hoola_send / net upload refuse it by file_id or by its bytes' sha256).
  disconnect-> POST /public/oauth2/1/revoke + forget the token.
Without server credentials everything still works the manual way: open the DigiLocker app, download / share the file
to Hoola (share-to-Hoola), and Hoola reads it like any of her files.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy import JSON, Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from ..net import policy
from .aa import HandoffError, _utc

STATE_MINUTES = 10
MAX_FILE = 10 * 1024 * 1024
ID_DOCTYPES = {"ADHAR", "PANCR", "DRVLC", "RVCER", "VTRCD", "ELCRD", "PSPRT", "RATCR", "EPICR"}
ID_WORDS = re.compile(r"aadhaa?r|\bpan\b|permanent account|driving|licen[cs]e|registration certificate|\brc\b|voter|"
                      r"election|epic|passport|ration", re.I)
AADHAAR = re.compile(r"aadhaa?r|\badhar\b", re.I)
APP = {"name": "DigiLocker", "android": "com.digilocker.android",
       "play": "https://play.google.com/store/apps/details?id=com.digilocker.android", "web": "https://www.digilocker.gov.in"}
STATS = {"starts": 0, "connected": 0, "fetched": 0, "refused_share": 0, "hmac_bad": 0}
_http: httpx.Client | None = None


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c


class DlAuth(Base):
    __tablename__ = "handoff_dl_auth"
    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    verifier: Mapped[str] = mapped_column(Text)                                # sealed
    doctype: Mapped[str] = mapped_column(String(12), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DlLink(Base):
    __tablename__ = "handoff_dl_links"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token: Mapped[str] = mapped_column(Text, default="")                        # sealed access token
    refresh: Mapped[str] = mapped_column(Text, default="")                      # sealed refresh token (if any)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(String(400), default="")
    issued: Mapped[list] = mapped_column(JSON, default=list)                    # last issued-documents list
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DlDoc(Base):
    """A document pulled from her DigiLocker into her files (for the share guard and her list)."""
    __tablename__ = "handoff_dl_docs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dld"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    uri: Mapped[str] = mapped_column(String(300), default="")
    doctype: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    issuer: Mapped[str] = mapped_column(String(200), default="")
    is_id: Mapped[bool] = mapped_column(Boolean, default=False)
    file_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    sha256: Mapped[str] = mapped_column(String(64), index=True, default="")
    hmac_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def configured() -> bool:
    st = get_settings()
    return bool(st.digilocker_client_id and st.digilocker_client_secret)


def _base() -> str:
    b = (get_settings().digilocker_base or "https://digilocker.meripehchaan.gov.in").rstrip("/")
    if not b.startswith("https://"):
        raise HandoffError("DigiLocker address https hona chahiye.")
    return b


def redirect_uri() -> str:
    st = get_settings()
    from ..net import federation as fed
    return st.digilocker_redirect_uri or fed.my_base() + "/api/digilocker/callback"


def _vault():
    from ..bazar.security import vault
    return vault()


def _client() -> httpx.Client:
    return _http or httpx.Client(timeout=20, follow_redirects=False, headers={"User-Agent": "Hoola/1 (digilocker requester)"})


def _close(c: httpx.Client) -> None:
    if _http is None:
        c.close()


def is_id_doc(doctype: str = "", name: str = "") -> bool:
    return (doctype or "").upper() in ID_DOCTYPES or bool(ID_WORDS.search(name or ""))


def is_aadhaar(doctype: str = "", name: str = "") -> bool:
    return (doctype or "").upper() == "ADHAR" or bool(AADHAAR.search(name or ""))


def manual() -> dict[str, Any]:
    return {"app": APP, "steps": ["DigiLocker app kholiye (Play Store: DigiLocker, NeGD).",
                                  "Issued Documents mein document kholiye -> Download / Share.",
                                  "Share mein 'Hoola' chuniye (ya chat ke paperclip se file dijiye).",
                                  "Hoola file padh lega; zaroori ho to form / email mein laga dega (aapke tap se)."]}


def status(tenant: str) -> dict[str, Any]:
    with session() as s:
        l = s.get(DlLink, tenant)
        docs = s.scalars(select(DlDoc).where(DlDoc.tenant_id == tenant).order_by(DlDoc.fetched_at.desc()).limit(40)).all()
        live = bool(l and l.token and l.expires_at and _utc(l.expires_at) > now())
        return {"configured": configured(), "connected": live, "linked_once": l is not None,
                "issued": list(l.issued or []) if l else [], "pulled": [_doc_view(d) for d in docs],
                "manual": manual(), "say": "" if configured() else
                "Hoola server abhi DigiLocker requester nahi bana; DigiLocker app se file share karke kaam chalega."}


def _doc_view(d: DlDoc) -> dict[str, Any]:
    return {"id": d.id, "name": d.name, "doctype": d.doctype, "issuer": d.issuer, "is_id": d.is_id, "file_id": d.file_id,
            "hmac_ok": d.hmac_ok, "fetched_at": _utc(d.fetched_at).isoformat()}


def start(tenant: str, doctype: str = "") -> dict[str, Any]:
    """The DigiLocker sign-in link for her (she opens it; OTP and consent happen on DigiLocker's own page)."""
    if not configured():
        return {"status": "not_setup", **manual(),
                "say": "DigiLocker se seedha jodna is server par abhi chalu nahi. DigiLocker app se document Hoola ko share kar dijiye."}
    dt = re.sub(r"[^A-Z0-9]", "", str(doctype or "").upper())[:10]
    if dt == "ADHAR":
        raise HandoffError("Aadhaar DigiLocker mein hi rehne dijiye; number chahiye to Pehchaan Locker mein rakhiye.")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(24)
    with session() as s:
        for old in s.scalars(select(DlAuth).where(DlAuth.created_at < now() - timedelta(minutes=STATE_MINUTES))).all():
            s.delete(old)
        s.add(DlAuth(state=state, tenant_id=tenant, verifier=_vault().seal(verifier), doctype=dt, created_at=now()))
    q = {"response_type": "code", "client_id": get_settings().digilocker_client_id, "redirect_uri": redirect_uri(),
         "state": state, "scope": "openid", "code_challenge": challenge, "code_challenge_method": "S256"}
    if dt:
        q["req_doctype"] = dt
    STATS["starts"] += 1
    return {"status": "open", "url": f"{_base()}/public/oauth2/1/authorize?{urlencode(q)}",
            "say": "DigiLocker ka page khulega: wahin login / OTP / consent kijiye (Hoola ko OTP mat bataiye). Phir app mein wapas aaiye."}


def callback(code: str, state: str, error: str = "") -> dict[str, Any]:
    """DigiLocker sends her back here. Returns {tenant, ok, say}."""
    with session() as s:
        a = s.get(DlAuth, str(state or "")[:64]) if state else None
        if a is None or _utc(a.created_at) < now() - timedelta(minutes=STATE_MINUTES):
            raise HandoffError("Yeh DigiLocker link purana ho gaya; Hoola app se dobara 'DigiLocker jodo' dabaiye.")
        tenant, verifier = a.tenant_id, _vault().open(a.verifier)
        s.delete(a)
    if error or not code:
        return {"tenant": tenant, "ok": False, "say": "DigiLocker ne ijazat nahi di (aapne mana kiya ya beech mein band hua)."}
    st = get_settings()
    form = {"code": code, "grant_type": "authorization_code", "client_id": st.digilocker_client_id,
            "client_secret": st.digilocker_client_secret, "redirect_uri": redirect_uri(), "code_verifier": verifier}
    c = _client()
    try:
        r = c.post(_base() + "/public/oauth2/2/token", data=form, headers={"Accept": "application/json"})
        tok = r.json() if r.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as e:
        raise HandoffError(f"DigiLocker se token nahi mila ({type(e).__name__}).")
    finally:
        _close(c)
    if not tok.get("access_token"):
        raise HandoffError("DigiLocker ne token nahi diya; dobara koshish kijiye.")
    exp = now() + timedelta(seconds=int(tok.get("expires_in") or 3600))
    with session() as s:
        l = s.get(DlLink, tenant) or DlLink(tenant_id=tenant, connected_at=now())
        l.token, l.expires_at, l.scope = _vault().seal(tok["access_token"]), exp, str(tok.get("scope") or "")[:400]
        l.refresh = _vault().seal(tok["refresh_token"]) if tok.get("refresh_token") else ""
        l.updated_at = now()
        s.merge(l)
    STATS["connected"] += 1
    try:
        docs = issued(tenant)
    except HandoffError:
        docs = []
    from ..net.service import tell
    tell(tenant, "digilocker", {"status": "connected", "issued": docs,
                                "say": f"DigiLocker jud gaya: {len(docs)} document dikh rahe hain."},
         f"DigiLocker jud gaya ({len(docs)} issued documents). Unhe file banana ho to digilocker action=fetch.")
    return {"tenant": tenant, "ok": True, "say": "DigiLocker jud gaya. Hoola app mein wapas jaiye."}


def _token(tenant: str) -> str:
    with session() as s:
        l = s.get(DlLink, tenant)
        if l is None or not l.token:
            raise HandoffError("DigiLocker juda nahi hai: pehle 'DigiLocker jodo'.")
        if not l.expires_at or _utc(l.expires_at) <= now():
            raise HandoffError("DigiLocker ka login 1 ghante baad khatam ho jaata hai; dobara 'DigiLocker jodo' dabaiye.")
        return _vault().open(l.token)


def issued(tenant: str) -> list[dict[str, Any]]:
    tok = _token(tenant)
    c = _client()
    try:
        r = c.get(_base() + "/public/oauth2/2/files/issued", headers={"Authorization": f"Bearer {tok}"})
        data = r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError) as e:
        raise HandoffError(f"DigiLocker se list nahi aayi ({type(e).__name__}).")
    finally:
        _close(c)
    if not isinstance(data, dict):
        raise HandoffError("DigiLocker se list nahi aayi.")
    out = []
    for it in (data.get("items") or [])[:100]:
        if not isinstance(it, dict) or not it.get("uri"):
            continue
        name, dt = policy.quote(it.get("name"), 160), re.sub(r"[^A-Z0-9]", "", str(it.get("doctype") or "").upper())[:12]
        out.append({"uri": str(it["uri"])[:300], "name": name, "doctype": dt, "issuer": policy.quote(it.get("issuer"), 160),
                    "date": str(it.get("date") or "")[:20], "mime": str(it.get("mime") or "")[:60],
                    "is_id": is_id_doc(dt, name), "aadhaar": is_aadhaar(dt, name)})
    with session() as s:
        l = s.get(DlLink, tenant)
        if l is not None:
            l.issued, l.updated_at = out, now()
    return out


def fetch(tenant: str, uri: str) -> dict[str, Any]:
    """Pull one issued document into her files (file_id). Aadhaar is never pulled."""
    uri = str(uri or "").strip()
    with session() as s:
        l = s.get(DlLink, tenant)
        known = {d["uri"]: d for d in (l.issued or [])} if l else {}
    meta = known.get(uri)
    if meta is None:
        raise HandoffError("Yeh document aapki DigiLocker list mein nahi mila; pehle list dekhiye.")
    if meta.get("aadhaar"):
        raise HandoffError("Aadhaar DigiLocker mein hi rehne dijiye (Hoola use file nahi banata). Number chahiye to Pehchaan Locker.")
    tok = _token(tenant)
    c = _client()
    try:
        with c.stream("GET", _base() + "/public/oauth2/1/file/" + quote(uri, safe=""), headers={"Authorization": f"Bearer {tok}"}) as r:
            if r.status_code != 200:
                raise HandoffError(f"DigiLocker ne file nahi di ({r.status_code}).")
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > MAX_FILE:
                    raise HandoffError("File 10 MB se badi hai.")
            mac = r.headers.get("hmac", "")
            ctype = r.headers.get("content-type", "application/pdf").split(";")[0]
    except httpx.HTTPError as e:
        raise HandoffError(f"DigiLocker se file nahi aayi ({type(e).__name__}).")
    finally:
        _close(c)
    data = bytes(buf)
    want = base64.b64encode(hmac.new(get_settings().digilocker_client_secret.encode(), data, hashlib.sha256).digest()).decode()
    ok = bool(mac) and hmac.compare_digest(mac.strip(), want)
    if mac and not ok:
        STATS["hmac_bad"] += 1
        raise HandoffError("File ki jaanch (HMAC) nahi mili; file raste mein badli ho sakti hai. Nahi li.")
    from .. import chatfiles
    ext = ".pdf" if "pdf" in ctype else (".xml" if "xml" in ctype else (".jpg" if "jpeg" in ctype else ""))
    name = re.sub(r"[^\w .\-]", "", meta["name"] or "DigiLocker document")[:80] + ext
    f = chatfiles.store(tenant, name, data, ctype)
    sha = hashlib.sha256(data).hexdigest()
    with session() as s:
        s.add(DlDoc(id=new_id("dld"), tenant_id=tenant, uri=uri, doctype=meta.get("doctype", ""), name=meta["name"],
                    issuer=meta.get("issuer", ""), is_id=bool(meta.get("is_id")), file_id=f["file_id"], sha256=sha,
                    hmac_ok=ok, fetched_at=now()))
    STATS["fetched"] += 1
    return {"file": {k: f.get(k) for k in ("file_id", "name", "size", "url", "media", "preview", "pages")}, "is_id": bool(meta.get("is_id")),
            "hmac_ok": ok, "say": f"{meta['name']} aapki files mein aa gaya" + (" (DigiLocker ki jaanch ke saath)." if ok else ".") +
            (" Yeh ID document hai: kisi doosre ke avatar ko nahi jaayega." if meta.get("is_id") else "")}


def disconnect(tenant: str) -> dict[str, Any]:
    with session() as s:
        l = s.get(DlLink, tenant)
        tok = _vault().open(l.token) if l is not None and l.token else ""
    if tok:
        c = _client()
        try:
            c.post(_base() + "/public/oauth2/1/revoke", data={"token": tok, "token_type_hint": "access_token"})
        except httpx.HTTPError:
            pass
        finally:
            _close(c)
    with session() as s:
        l = s.get(DlLink, tenant)
        if l is not None:
            s.delete(l)
    return {"status": "disconnected", "say": "DigiLocker se Hoola ka judaav hata diya."}


def guard_share(tenant: str, file_id: str = "", data: bytes | None = None) -> None:
    """Raise when a file that came from her DigiLocker as an ID document is about to go to another avatar."""
    from ..net.service import NetError
    sha = hashlib.sha256(data).hexdigest() if data is not None else ""
    with session() as s:
        q = select(DlDoc).where(DlDoc.tenant_id == tenant, DlDoc.is_id.is_(True))
        rows = s.scalars(q).all()
        if file_id and not sha:
            from ..db import PcFile
            f = s.get(PcFile, file_id)
            sha = f.sha256 if f is not None else ""
        hit = next((d for d in rows if (file_id and d.file_id == file_id) or (sha and d.sha256 == sha)), None)
    if hit is not None:
        STATS["refused_share"] += 1
        raise NetError(f"'{hit.name}' DigiLocker se aaya ID document hai; Hoola ise doosre ke avatar ko nahi bhejta. "
                       "Saamne wale ko DigiLocker se khud verify karne ko kahiye, ya DigiLocker app ka apna 'Share' use kijiye.")

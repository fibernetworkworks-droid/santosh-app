"""Hoola IDs: the unique handle people search for, the permanent uid connections are tied to, and the Ed25519 key
every avatar message is signed with. Address of an avatar: <uid>@<server domain>."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from sqlalchemy import select

from ..config import get_settings
from ..db import now, session
from .models import HoolaId, Peer

RESERVED = {"sbi", "rbi", "npci", "uidai", "police", "cybercell", "cybercrime", "cbi", "incometax", "customs", "trai",
            "sebi", "bank", "official", "support", "help", "helpline", "admin", "root", "system", "hoola", "santosh",
            "newtika", "fnw", "government", "gov", "sarkar", "court", "army", "anthropic", "claude", "google", "whatsapp",
            "paytm", "phonepe", "gpay", "bhim", "aadhaar", "aadhar", "irctc", "bsnl", "jio", "airtel"}
STRICT = {"sbi", "rbi", "npci", "uidai", "police", "cybercell", "cybercrime", "cbi", "incometax", "customs", "official",
          "support", "help", "helpline", "customercare", "care", "admin", "root", "system", "hoola", "sarkar", "government",
          "gov", "aadhaar", "aadhar", "court"}
HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._]{1,28})[a-z0-9]$")


class IdError(Exception):
    pass


# ---------------------------------------------------------------- addresses
def domain() -> str:
    st = get_settings()
    host = urlparse(st.public_base_url or "").hostname or ""
    return (getattr(st, "hoola_domain", "") or host or "local").lower()


def address(uid: str) -> str:
    return f"{uid}@{domain()}"


def split(addr: str) -> tuple[str, str]:
    uid, _, dom = (addr or "").partition("@")
    return uid, (dom or domain()).lower()


def is_local(addr: str) -> bool:
    return split(addr)[1] == domain()


# ---------------------------------------------------------------- handles
def skeleton(handle: str) -> str:
    """Look-alike form: meghana.fnvv and meghana.fnw, rn / m, 0 / o, 1 / l / i all collapse to the same thing."""
    s = handle.lower().replace("vv", "w").replace("rn", "m").replace("_", "").replace(".", "")
    return s.translate(str.maketrans({"0": "o", "1": "l", "i": "l", "3": "e", "5": "s", "8": "b", "@": "a"}))


def clean_handle(raw: str) -> str:
    h = (raw or "").strip().lstrip("@").lower()
    if not HANDLE_RE.match(h) or ".." in h or "__" in h or not re.search(r"[a-z]", h):
        raise IdError("Hoola ID 3 se 30 akshar: chhote angrezi akshar, number, . ya _ (jaise meghana.fnw).")
    parts = set(re.split(r"[._]", h))
    whole = h.replace(".", "").replace("_", "")
    if parts & STRICT or whole in RESERVED or whole in STRICT or any(whole == r + x for r in RESERVED for x in ("in", "india", "app")):
        raise IdError("Yeh ID kisi bank, sarkari ya badi company jaisi lagti hai; koi doosri chuniye.")
    return h


def suggest(name: str, email: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", ".", (name or email.split("@")[0] or "hoola").lower()).strip(".")[:20] or "hoola"
    if not re.search(r"[a-z]", base) or len(base) < 3:
        base = "hoola.user"
    with session() as s:
        for i in range(50):
            cand = base if i == 0 else f"{base}{secrets.randbelow(900) + 100}"
            try:
                cand = clean_handle(cand)
            except IdError:
                cand = f"user{secrets.randbelow(90000) + 10000}"
            if not s.scalars(select(HoolaId).where((HoolaId.handle == cand) | (HoolaId.skeleton == skeleton(cand)))).first():
                return cand
    return f"user{secrets.token_hex(3)}"


# ---------------------------------------------------------------- keys
def _fernet():
    """Avatar private keys are encrypted with the server SECRET_KEY, or else with a key file made once in ./data."""
    from cryptography.fernet import Fernet
    st = get_settings()
    if st.secret_key:
        from ..accounts import _fernet as f
        return f()
    import os
    from pathlib import Path
    path = Path(getattr(st, "hoola_key_file", "") or Path(st.pc_files_dir).parent / "hoola_server.key")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
        os.chmod(path, 0o600)
    return Fernet(path.read_bytes().strip())


def _new_keys() -> tuple[str, str]:
    k = Ed25519PrivateKey.generate()
    raw = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(pub).decode(), _fernet().encrypt(base64.b64encode(raw)).decode()


def _priv(row: HoolaId) -> Ed25519PrivateKey:
    raw = base64.b64decode(_fernet().decrypt(row.private_key.encode()))
    return Ed25519PrivateKey.from_private_bytes(raw)


def canonical(env: dict[str, Any]) -> bytes:
    return json.dumps({k: env[k] for k in sorted(env) if k != "sig"}, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode()


def sign(tenant: str, env: dict[str, Any]) -> dict[str, Any]:
    row = ensure(tenant)
    env = dict(env)
    env["sig"] = base64.b64encode(_priv(row).sign(canonical(env))).decode()
    return env


def verify(env: dict[str, Any], public_key_b64: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)).verify(base64.b64decode(env["sig"]), canonical(env))
        return True
    except Exception:
        return False


def safety_code(pub_a: str, pub_b: str) -> str:
    """Same 8 digits on both phones when both keys are right."""
    a, b = sorted([pub_a, pub_b])
    d = int(hashlib.sha256(f"{a}|{b}".encode()).hexdigest(), 16)
    return f"{d % 10000:04d} · {(d // 10000) % 10000:04d}"


# ---------------------------------------------------------------- phone discovery (opt-in, hashed)
def phone_hash(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) < 11:
        raise IdError("Mobile number 10 ank ka daaliye.")
    pepper = get_settings().secret_key or "hoola"
    return hashlib.sha256(f"{pepper}|{digits}".encode()).hexdigest()


# ---------------------------------------------------------------- the owner's own Hoola ID
def owner_name(tenant: str) -> str:
    try:
        from ..life import get_profile
        n = (get_profile(tenant).name or "").strip()
        if n:
            return n[:80]
    except Exception:
        pass
    try:
        from ..accounts import user_info
        u = user_info(tenant)
        if u and (u.get("name") or u.get("email")):
            return (u.get("name") or u["email"].split("@")[0])[:80]
    except Exception:
        pass
    return "Hoola user"


def ensure(tenant: str) -> HoolaId:
    with session() as s:
        row = s.get(HoolaId, tenant)
        if row is None:
            name = owner_name(tenant)
            pub, priv = _new_keys()
            h = suggest(name)
            row = HoolaId(tenant_id=tenant, uid="hl_" + secrets.token_hex(8), handle=h, skeleton=skeleton(h),
                          owner_name=name, public_key=pub, private_key=priv)
            s.add(row)
            s.flush()
        s.expunge(row)
        return row


def set_handle(tenant: str, raw: str) -> HoolaId:
    h = clean_handle(raw)
    ensure(tenant)
    with session() as s:
        row = s.get(HoolaId, tenant)
        if row.handle == h:
            s.expunge(row)
            return row
        clash = s.scalars(select(HoolaId).where(HoolaId.tenant_id != tenant, (HoolaId.handle == h) | (HoolaId.old_handle == h))).first()
        if clash:
            raise IdError("Yeh Hoola ID kisi aur ki hai.")
        look = s.scalars(select(HoolaId).where(HoolaId.tenant_id != tenant, HoolaId.skeleton == skeleton(h))).first()
        if look:
            raise IdError(f"Yeh ID @{look.handle} jaisi dikhti hai; log dhokha kha sakte hain. Koi alag ID chuniye.")
        if now() - _aware(row.created_at) > timedelta(days=7):      # the first week: change freely
            if row.handle_changed_at and now() - _aware(row.handle_changed_at) < timedelta(days=365):
                raise IdError("Hoola ID saal mein ek hi baar badal sakti hai.")
            row.old_handle = row.handle                                # the old ID points here for 90 days
            row.handle_changed_at = now()
        row.handle, row.skeleton = h, skeleton(h)
        s.flush()
        s.expunge(row)
        return row


def _aware(dt):
    from datetime import timezone
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def set_discovery(tenant: str, phone: str | None, on: bool) -> HoolaId:
    ensure(tenant)
    with session() as s:
        row = s.get(HoolaId, tenant)
        if on:
            if not phone and not row.phone_hash:
                raise IdError("Number se dhoondhne ke liye apna mobile number daaliye.")
            if phone:
                row.phone_hash = phone_hash(phone)
            row.discoverable = True
        else:
            row.discoverable = False
            row.phone_hash = ""
        s.flush()
        s.expunge(row)
        return row


def by_handle(handle: str) -> HoolaId | None:
    h = (handle or "").strip().lstrip("@").lower()
    with session() as s:
        row = s.scalars(select(HoolaId).where(HoolaId.handle == h)).first()
        if row is None:
            old = s.scalars(select(HoolaId).where(HoolaId.old_handle == h)).first()
            if old and old.handle_changed_at and now() - _aware(old.handle_changed_at) < timedelta(days=90):
                row = old
        if row is not None:
            s.expunge(row)
        return row


def by_uid(uid: str) -> HoolaId | None:
    with session() as s:
        row = s.scalars(select(HoolaId).where(HoolaId.uid == uid)).first()
        if row is not None:
            s.expunge(row)
        return row


def tenant_of(addr: str) -> str | None:
    if not is_local(addr):
        return None
    row = by_uid(split(addr)[0])
    return row.tenant_id if row else None


# ---------------------------------------------------------------- public card of any avatar
def my_card(tenant: str) -> dict[str, Any]:
    from ..avatar.service import get as avatar_get
    row = ensure(tenant)
    a = avatar_get(tenant)
    name, gender = a["name"], a["gender"]
    return {"address": address(row.uid), "handle": row.handle, "owner_name": row.owner_name or owner_name(tenant),
            "avatar_name": name, "avatar_gender": gender, "public_key": row.public_key, "server": domain(),
            "verified": row.verified, "business": row.business and row.business_verified,
            "language": a["rules"].get("language", "hinglish")}


def remember_peer(card: dict[str, Any]) -> dict[str, Any]:
    """Store / refresh what we know about a peer (names cleaned). A changed key is NOT taken: it waits as pending_key
    until the owner re-verifies the safety code. Returns {'key_changed': bool}."""
    from .policy import clean_name
    addr = str(card.get("address") or "")
    if not addr:
        return {"key_changed": False}
    with session() as s:
        p = s.get(Peer, addr)
        changed = False
        if p is None:
            p = Peer(address=addr, public_key=str(card.get("public_key") or ""))
            s.add(p)
        elif p.public_key and card.get("public_key") and p.public_key != card["public_key"]:
            changed = True
            p.key_changed_at = now()
            p.pending_key = str(card["public_key"])
        p.handle = clean_name(card.get("handle") or p.handle, 120).replace(" ", "")
        p.owner_name = clean_name(card.get("owner_name") or p.owner_name, 60)
        p.avatar_name = clean_name(card.get("avatar_name") or p.avatar_name, 30)
        p.avatar_gender = "f" if card.get("avatar_gender") == "f" else "m"
        p.server = clean_name(card.get("server") or p.server, 120).replace(" ", "")
        p.business = bool(card.get("business"))
        p.verified = False                                    # a remote server cannot vouch for its users here
        p.updated_at = now()
    return {"key_changed": changed}


def accept_new_key(addr: str) -> bool:
    """The owner compared the safety code again: take the pending key."""
    with session() as s:
        p = s.get(Peer, addr)
        if p is None or not p.pending_key:
            return False
        p.public_key, p.pending_key = p.pending_key, None
        return True


def peer_card(addr: str) -> dict[str, Any] | None:
    t = tenant_of(addr)
    if t:
        return my_card(t)
    with session() as s:
        p = s.get(Peer, addr)
        if p is None:
            return None
        return {"address": p.address, "handle": p.handle, "owner_name": p.owner_name, "avatar_name": p.avatar_name,
                "avatar_gender": p.avatar_gender, "public_key": p.public_key, "server": p.server, "verified": p.verified,
                "business": p.business}


def label(card: dict[str, Any] | None) -> str:
    """'Kunal ka Raju' / 'Meghana ki Meera'."""
    if not card:
        return "Anjaan Hoola"
    from .policy import clean_name
    ka = "ki" if card.get("avatar_gender") == "f" else "ka"
    owner = clean_name(card.get("owner_name"), 60) or "@" + clean_name(card.get("handle"), 60)
    return f"{owner} {ka} {clean_name(card.get('avatar_name'), 30) or 'Hoola'}"

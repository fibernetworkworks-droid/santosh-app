"""HOOLA DIAGRAM D3 - the live draw.io editor: her hand edits, her selection, Hoola's changes, one truth on the server.

Every engine-C diagram has a REVISION number (meta "rev"). It moves when she saves an edit that really changed
something (draw.io's re-serialising is not an edit: `drawio_xml.fingerprint` compares only what a person can change)
and when Hoola changes it. Three rules keep the two of them from overwriting each other:
  1. Hoola READS first (`read` stores ai_seen_rev). A change is refused when the revision moved since that read -
     she edited by hand in between - and Hoola is told to read again (next-ai-draw-io's edit gate idea, by content).
  2. Her save says which revision her editor already holds (applied_rev). A save from an editor that has not yet
     applied Hoola's newest change is refused as STALE (her editor applies it first, then saves again - her own
     shapes, even unsaved ones, survive, because Hoola's change is applied id by id inside her editor).
  3. Hoola's change goes out once to the open editor (the `live` queue, polled), as ONE undoable step there.

Her edits become versions of the same page at most once a minute (the newest save replaces nothing: a new version
holds the newest state); a change by Hoola is always its own version. The link to the editor is signed for ONE diagram
and one person and expires (LINK_HOURS); the editor page never sees her sign-in."""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any

from . import drawio_xml as X
from . import service as S

LINK_HOURS = 12
VERSION_EVERY_S = 60
KEEP_LIVE = 30


def _key() -> bytes:
    from ..config import get_settings
    raw = str(getattr(get_settings(), "secret_key", "") or "") or "hoola-diagram-dev-key"
    return hashlib.sha256(("diagram-live|" + raw).encode()).digest()


def sign(tenant: str, did: str, hours: int = LINK_HOURS) -> str:
    exp = int(time.time()) + hours * 3600
    body = base64.urlsafe_b64encode(f"{tenant}|{did}|{exp}".encode()).decode().rstrip("=")
    mac = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{mac}"


def verify(token: str) -> tuple[str, str] | None:
    try:
        body, mac = str(token or "").split(".", 1)
        if not hmac.compare_digest(mac, hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()[:32]):
            return None
        tenant, did, exp = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode().split("|")
        if int(exp) < time.time():
            return None
        return tenant, did
    except Exception:  # noqa: BLE001
        return None


def link(tenant: str, did: str) -> str:
    return "/diagram-edit/" + sign(tenant, did)


def state(tenant: str, did: str) -> dict[str, Any]:
    m, desc = S.current(tenant, did)
    if m is None or m.get("engine") != "drawio" or not desc:
        return {"ok": False}
    return {"ok": True, "xml": desc, "rev": int(m.get("rev") or 0), "title": m.get("title", "")}


def save(tenant: str, did: str, xml: str, svg: str = "", applied_rev: int = 0) -> dict[str, Any]:
    with S._LOCK:
        m, desc = S.current(tenant, did)
        if m is None or m.get("engine") != "drawio":
            return {"ok": False, "error": "not an editable diagram"}
        rev = int(m.get("rev") or 0)
        if int(applied_rev or 0) < rev and (m.get("last_by") == "ai"):
            return {"ok": False, "stale": True, "rev": rev}
        clean, probs = X.normalize(xml, m.get("title") or "Page-1")
        if probs:
            return {"ok": False, "error": "; ".join(probs[:3])}
        if X.fingerprint(clean) == X.fingerprint(desc):
            return {"ok": True, "rev": rev, "changed": False}
        rev += 1
        m.update({"rev": rev, "last_by": "her", "her_at": time.time()})
        S._save_desc(tenant, m, clean)
        page = S.drawio_page(m.get("title", ""), svg) if svg.strip().startswith("<svg") or "<svg" in svg[:400] else ""
        if page and (time.time() - float(m.get("her_version_at") or 0) >= VERSION_EVERY_S or not m.get("artifact_id")):
            S.publish_drawio(tenant, m.get("conversation_id", ""), m, clean, page, note="her edit")
            m["her_version_at"] = time.time()
        S._save_meta(tenant, m)
        return {"ok": True, "rev": rev, "changed": True}


def select(tenant: str, did: str, ids: list[str]) -> dict[str, Any]:
    with S._LOCK:
        m = S._meta(tenant, did)
        if m is None:
            return {"ok": False}
        m["selection"] = [str(i)[:80] for i in (ids or [])][:200]
        m["selection_at"] = time.time()
        S._save_meta(tenant, m)
    return {"ok": True}


def push(m: dict[str, Any], rev: int, ids: list[str], ops: list | None = None, model: str = "") -> None:
    """Queue Hoola's change for the open editor (meta is saved by the caller)."""
    q = list(m.get("live") or [])
    q.append({"rev": rev, "ids": ids[:200], "ops": ops or None, "model": model or None, "at": time.time()})
    m["live"] = q[-KEEP_LIVE:]


def poll(tenant: str, did: str, since: int) -> dict[str, Any]:
    m = S._meta(tenant, did)
    if m is None:
        return {"ok": False, "changes": []}
    ch = [c for c in (m.get("live") or []) if int(c.get("rev") or 0) > int(since or 0)]
    return {"ok": True, "rev": int(m.get("rev") or 0), "changes": ch}

"""The append-only audit log (plan 4.1 evidence). A row keeps a HASH of the inputs, never the inputs, and the hash of the row before
it in the same tenant - so a removed or edited row breaks the chain and `verify()` says where. Recording never breaks the work."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

log = logging.getLogger("hoola.fin")


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _row_hash(prev: str, seq: int, actor: str, kind: str, what: str, detail: str, ws: str) -> str:
    return digest([prev, seq, actor, kind, what, detail, ws])


def record(tenant: str, workspace_id: str, actor: str, kind: str, what: str, detail: Any = None) -> str:
    try:
        from ..db import session
        from .models import FinEvent, ensure
        ensure()
        dh = digest(detail) if detail is not None else ""
        with session() as db:
            last = db.query(FinEvent).filter(FinEvent.tenant_id == tenant).order_by(FinEvent.seq.desc()).first()
            seq = (last.seq if last else 0) + 1
            prev = last.hash if last else ""
            h = _row_hash(prev, seq, actor[:80], kind[:24], what[:200], dh, workspace_id)
            db.add(FinEvent(tenant_id=tenant, workspace_id=workspace_id, seq=seq, actor=actor[:80], kind=kind[:24], what=what[:200],
                            detail_hash=dh, prev=prev, hash=h))
        return h
    except Exception as e:  # the log must never stop her work
        log.warning("fin evidence not recorded: %s", e)
        return ""


def events(tenant: str, workspace_id: str = "", limit: int = 200) -> list[dict[str, Any]]:
    from ..db import session
    from .models import FinEvent, ensure
    ensure()
    with session() as db:
        q = db.query(FinEvent).filter(FinEvent.tenant_id == tenant)
        if workspace_id:
            q = q.filter(FinEvent.workspace_id == workspace_id)
        rows = q.order_by(FinEvent.seq.desc()).limit(max(1, min(limit, 2000))).all()
        return [{"seq": r.seq, "at": r.at.isoformat() if r.at else "", "actor": r.actor, "kind": r.kind, "what": r.what,
                 "workspace_id": r.workspace_id, "hash": r.hash} for r in rows]


def verify(tenant: str) -> dict[str, Any]:
    from ..db import session
    from .models import FinEvent, ensure
    ensure()
    with session() as db:
        prev, n = "", 0
        for r in db.query(FinEvent).filter(FinEvent.tenant_id == tenant).order_by(FinEvent.seq).all():
            n += 1
            if r.seq != n or r.prev != prev or r.hash != _row_hash(prev, r.seq, r.actor, r.kind, r.what, r.detail_hash, r.workspace_id):
                return {"ok": False, "rows": n, "broken_at": r.seq}
            prev = r.hash
        return {"ok": True, "rows": n}

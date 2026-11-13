"""v0.885 HOOLA PC POOL - every Hoola user gets a Hoola PC from a shared pool.

Owner (13 Nov 2026): "EVERY HOOLA USER WILL HAS ITS OWN HOOLA PC --- IF USER WANTS THEY CAN GIVE MANUAL TASK TO HOOLA
PC ON CHROME AND AFTER TASK COMPLETION HOOLA WILL REPORT IT BACK --- IT IS BEST FOR LEGACY PORTALS AND GOV PORTALS
WHERE NEED A HUGE REPEATED MANUAL WORK", then "Shared pool AND HUMAN IN LOOP".

- One Hoola PC = one task at a time, for one user. A PC is chosen per task: the one she used last (her logins are
  already open there), then her own, then any free one. All busy = her task waits in a queue (first come, first served)
  and the card says her place.
- Before every task the PC switches to HER folder (Chrome logins, Downloads, work files). The folder key and its secret
  are made here from the server's own signing key and her tenant id: nothing is stored, the PC keeps the secret only
  while she is served and encrypts her folder with it the moment it serves someone else.
- Files a task made on the PC come to her chat (send_to_chat) and every task ends with a screenshot of the screen.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any

from .hub import HOOLA_PC_KIND


def _hub():
    from . import hub as _H        # looked up each time (tests swap the hub)
    return _H.hub

log = logging.getLogger("santosh.pc")

LAST: dict[str, str] = {}          # tenant -> the Hoola PC she used last (her logins are open there)
QUEUE: list[str] = []              # op ids waiting for a free Hoola PC, first come first served


def _key(tenant: str, what: str) -> str:
    from . import service
    return hmac.new(service._sign_key(), f"hoolapc-{what}:{tenant}".encode(), hashlib.sha256).hexdigest()


def profile_key(tenant: str) -> str:
    return _key(tenant, "folder")[:24]


def profile_secret(tenant: str) -> str:
    return _key(tenant, "secret")


def _id(c) -> str:
    return str(getattr(c, "device_id", "") or "")


def busy_any(device_id: str):
    """The task running on that PC for ANYONE (None = free)."""
    from . import operator
    for o in operator.OPS.values():
        if o.device_id == device_id and o.task_obj is not None and not o.task_obj.done() and o.status != "queued":
            return o
    return None


def pick(tenant: str):
    """A FREE Hoola PC for her: the one she used last, then her own, then any. None = every one is busy."""
    pcs = _hub().hoola_pcs(tenant)
    free = [c for c in pcs if busy_any(_id(c)) is None]
    if not free:
        return None
    last = LAST.get(tenant)
    for c in free:
        if _id(c) == last:
            return c
    return free[0]


def mine_busy(tenant: str):
    """A Hoola PC already running HER task (a new task of hers replaces it there, as before)."""
    for c in _hub().hoola_pcs(tenant):
        o = busy_any(_id(c))
        if o is not None and o.tenant == tenant:
            return c
    return None


def position(op_id: str) -> int:
    try:
        return QUEUE.index(op_id) + 1
    except ValueError:
        return 0


async def wait_turn(op) -> Any:
    """Queue: wait until this task is first in line AND a Hoola PC is free. Returns the PC (or None on time out)."""
    from ..config import get_settings
    limit = time.time() + float(getattr(get_settings(), "hoola_pc_queue_min", 30) or 30) * 60
    if op.id not in QUEUE:
        QUEUE.append(op.id)
    try:
        while time.time() < limit:
            if QUEUE and QUEUE[0] == op.id:
                c = pick(op.tenant)
                if c is not None:
                    return c
            await asyncio.sleep(3)
        return None
    finally:
        if op.id in QUEUE:
            QUEUE.remove(op.id)


async def prepare(op) -> dict[str, Any]:
    """Switch the PC to HER folder before the first step. A PC that cannot do it never serves a second user."""
    from .hub import PcError
    conn = next((c for c in _hub().hoola_pcs(op.tenant) if _id(c) == op.device_id), None)
    home = conn is None or getattr(conn, "tenant_id", op.tenant) == op.tenant
    try:
        r = await _hub().call(op.tenant, "profile", {"key": profile_key(op.tenant), "secret": profile_secret(op.tenant),
                                                   "home": home},
                           device_id=op.device_id, kind=HOOLA_PC_KIND, timeout=900, log=False)
    except PcError as e:
        if "Unknown action" in str(e):
            if home:          # an old Hoola PC agent serving the user who paired it: the old shared folder, as before
                return {"profile": "legacy"}
            raise RuntimeError("HOOLA_PC_OLD: yeh Hoola PC purana hai (har user ka alag folder nahi bana sakta) - "
                               "vps-ops pc_deploy se use naya kijiye.")
        raise
    LAST[op.tenant] = op.device_id
    if r.get("switched"):
        log.info("hoola pc %s now serves tenant %s (folder %s, previous locked=%s)", op.device_id, op.tenant,
                 r.get("opened") or "new", r.get("locked_previous"))
    return r


def store_bytes(tenant: str, device_id: str, name: str, data: bytes) -> dict[str, Any]:
    """A file the server made for her (a screenshot proof, a batch result sheet) as a chat download."""
    from ..db import new_id, session
    from . import service as pcs
    from ..db import PcFile
    fid = new_id("file")
    path = pcs.files_dir() / fid
    path.write_bytes(data)
    with session() as s:
        row = PcFile(id=fid, tenant_id=tenant, device_id=device_id or "", direction="to_phone",
                     name=pcs.safe_name(name), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     pc_path="", stored_path=str(path))
        s.add(row)
        s.flush()
        s.expunge(row)
    return pcs.public_file(row)


def claim_file(file_id: str, tenant: str) -> dict[str, Any] | None:
    """A file a Hoola PC uploaded (tagged for the PC that paired it) becomes HER chat download."""
    from ..db import session
    from . import service as pcs
    from ..db import PcFile
    with session() as s:
        row = s.get(PcFile, file_id)
        if row is None:
            return None
        row.tenant_id, row.direction = tenant, "to_phone"
        s.flush()
        s.expunge(row)
    return pcs.public_file(row)


def publish(conv: str, f: dict[str, Any], title: str, source: str = "hoola_pc") -> None:
    from ..events import bus
    view = {k: v for k, v in f.items() if k != "pc_path"}
    bus.publish(conv, "pc_file", {**view, "source": source, "title": title[:120]})


def status(tenant: str) -> dict[str, Any]:
    """For the tool / card: how many Hoola PCs, how many free, her place in the queue."""
    pcs = _hub().hoola_pcs(tenant)
    return {"hoola_pcs": len(pcs), "free": sum(1 for c in pcs if busy_any(_id(c)) is None),
            "waiting": len(QUEUE)}

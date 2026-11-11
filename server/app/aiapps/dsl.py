"""v0.772 HOOLA AI APPS - export / import of an AI app as one portable JSON file (Dify's DSL idea, ideas only).

The file carries the SOUL and a little meta - never keys, logs, sessions, visitor data, the public code or the
WhatsApp number. Import is two steps, like Dify's dependency check: import_check says what the file relies on that
this account does not have yet (Seva knowledge base answers, Employee hours for booking, approved answers), then
import_confirm creates it as a DRAFT (going live stays her tap).
"""
from __future__ import annotations

import json
from typing import Any

from ..db import now
from . import soul as SO
from . import store as ST

FORMAT = "hoola-aiapp"
VERSION = 1
MAX_BYTES = 64 * 1024


def export(tenant: str, ref: str) -> dict[str, Any]:
    a = ST.get(tenant, ref)
    sl = SO.check(a.get("draft") or {})["soul"]
    return {"format": FORMAT, "v": VERSION, "name": sl["name"], "kind": sl["kind"], "soul": sl,
            "template": a.get("template") or "", "exported": now().isoformat()}


def _load(file: Any) -> dict[str, Any]:
    if isinstance(file, (bytes, bytearray)):
        file = bytes(file).decode("utf-8", "replace")
    if isinstance(file, str):
        if len(file.encode("utf-8")) > MAX_BYTES:
            raise ST.AppError("This file is bigger than 64 KB; an AI app file is much smaller.", 413)
        try:
            file = json.loads(file)
        except ValueError:
            raise ST.AppError("This is not a Hoola AI app file (it is not JSON).", 400)
    if not isinstance(file, dict):
        raise ST.AppError("This is not a Hoola AI app file.", 400)
    if len(json.dumps(file, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise ST.AppError("This file is bigger than 64 KB; an AI app file is much smaller.", 413)
    if file.get("format") != FORMAT:
        raise ST.AppError("This is not a Hoola AI app file (format must be 'hoola-aiapp').", 400)
    try:
        v = int(file.get("v") or 0)
    except (TypeError, ValueError):
        v = 0
    if v < 1 or v > VERSION:
        raise ST.AppError(f"This AI app file is version {file.get('v')}; this Hoola reads version {VERSION}.", 400)
    if not isinstance(file.get("soul"), dict):
        raise ST.AppError("This AI app file has no soul (its settings) inside.", 400)
    return file


def _seva_live(tenant: str) -> int:
    try:
        from ..seva.service import SevaEntry
        from ..db import session
        with session() as s:
            return s.query(SevaEntry).filter(SevaEntry.tenant_id == tenant, SevaEntry.status == "live").count()
    except Exception:                                   # noqa: BLE001
        return 0


def _hours_set(tenant: str) -> bool:
    try:
        from ..db import session
        from ..employee.models import EmployeeProfile
        with session() as s:
            p = s.get(EmployeeProfile, tenant)
            if p is None:
                return False
            h = json.loads(p.hours or "{}")
        return bool(isinstance(h, dict) and h.get("open") and h.get("close"))
    except Exception:                                   # noqa: BLE001
        return False


def _annotations(tenant: str) -> int:
    try:
        from ..gyaan import annotations as AN
        return int(AN.status(tenant).get("enabled") or 0)
    except Exception:                                   # noqa: BLE001
        return 0


def needs(tenant: str, sl: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    kn = sl.get("knowledge") or {}
    if kn.get("seva"):
        n = _seva_live(tenant)
        out.append({"what": "Knowledge base answers (Seva)", "have": n > 0, "count": n,
                    "fix": "Add your FAQ answers in Seva > Knowledge base; the app answers from them."})
    if kn.get("annotations"):
        n = _annotations(tenant)
        out.append({"what": "Approved answers", "have": n > 0, "count": n,
                    "fix": "Optional: correct an answer in the app's logs and it becomes an approved answer."})
    acts = set(sl.get("actions") or [])
    if acts & {"slots", "book"}:
        out.append({"what": "Working hours for appointments (AI Employee profile)", "have": _hours_set(tenant),
                    "fix": "Set your opening and closing hours and slot length in your AI Employee profile."})
    return out


def import_check(tenant: str, file: Any) -> dict[str, Any]:
    f = _load(file)
    got = SO.check(f["soul"])
    if f.get("name") and not f["soul"].get("name"):
        got["soul"]["name"] = str(f["name"])[:SO.CAPS["name"]]
    return {"soul": got["soul"], "errors": got["errors"], "warnings": got["warnings"],
            "needs": needs(tenant, got["soul"]), "name": got["soul"]["name"], "kind": got["soul"]["kind"]}


def import_confirm(tenant: str, file: Any, name: str = "") -> dict[str, Any]:
    chk = import_check(tenant, file)
    sl = chk["soul"]
    out = ST.create(tenant, str(name or "").strip()[:SO.CAPS["name"]] or sl["name"], sl["kind"], sl, origin="import")
    return {**out, "needs": chk["needs"], "says": f"'{out['name']}' is imported as a draft. Check it, then publish."}

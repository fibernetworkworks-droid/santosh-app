"""v0.443 DONE = VERIFIED (long-task report item 1, RCA fix 7): a long job may only close as `done` when the things
it says it made are REALLY there.

Until now `kaam_plan finish done` was taken on the model's word: `made` could hold a link that 404s, a file name that
was never written, or nothing at all, and the goal card still went green ("false done" - the costliest failure in the
report, and the one the long card measures). Every agent that finishes long work reliably decides "done" by something
the model cannot fake (Anthropic's feature list with its `passes` field, Codex running the tests, Replit's testing
sub-agent).

Two checks, both in CODE, no model call and no cost:

1. `check_made(tenant, made)` - every item the job claims it produced:
   - a Hoola file id (`file_...`) or a /api/pc/files/<id> link -> the PcFile row of THIS tenant and its bytes on disk
   - an artifact id (`art_...`) or a /api/artifacts/<id> link -> a ready Artifact (version > 0) of this tenant
   - a dataset name -> app.datasets must know it
   - a http(s) link -> one HEAD (3 s, redirects followed); 405 / 403 fall back to a ranged GET. A link that cannot
     be reached at all is NOT a failure (her VPS may be offline or the site may block robots) - it is `unknown`,
     said plainly. A 404 / 410 IS a failure: that link does not exist.
   - a bare file name -> looked for among the tenant's delivered files
2. `check_step(tenant, conv, step)` - an optional `check` the plan itself wrote per step:
   `file_pages>=N`, `file_rows>=N`, `file_slides>=N`, `file:<name>`, `link_ok`, `artifact`, `reminder>=N`,
   `list:<name>>=N`, `tool:<name>` (that tool really ran ok this job). The step's own `note` supplies the value
   (a file name / link / id) when the check needs one.

`gate(tenant, conv, made, steps, calls)` -> {"ok", "failures", "unknown", "line"}. `goal.finish` calls it for
outcome `done` only: a failure REOPENS the failing step (or step 1) with the failure text and returns the goal to
`working`, so the job carries on instead of closing on a lie. `unknown` never blocks - it is written on the card.

Nothing here ever writes to her data; the only outside call is a HEAD / ranged GET on a link the job itself produced."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.verify")

STATS = {"gates": 0, "passed": 0, "failed": 0, "unknown": 0, "reopened": 0, "links_checked": 0}

LINK_TIMEOUT_S = 3.0
MAX_LINKS = 6                      # one job's worth; the rest are reported as unchecked, never silently passed
_FILE_ID = re.compile(r"\bfile_[A-Za-z0-9]{4,}\b")
_ART_ID = re.compile(r"\bart_[A-Za-z0-9]{4,}\b")
_PC_LINK = re.compile(r"/api/pc/files/(file_[A-Za-z0-9]{4,})")
_ART_LINK = re.compile(r"/api/artifacts/(art_[A-Za-z0-9]{4,})")
_URL = re.compile(r"https?://[^\s)\]>\"']+", re.I)
_DS_ID = re.compile(r"\bds_[A-Za-z0-9]{6,}\b")
_FILENAME = re.compile(r"[\w ().,-]+\.(?:pdf|docx|xlsx|pptx|csv|zip|png|jpe?g|mp4|html|json|txt)\b", re.I)
_CHECK = re.compile(r"^(file_pages|file_rows|file_slides|reminder|routine|list|file|link_ok|artifact|tool)"
                    r"(?::([^<>=]+))?(?:\s*>=\s*(\d+))?$", re.I)


def _ok(what: str, detail: str = "") -> dict[str, Any]:
    return {"item": what, "state": "ok", "why": detail[:160]}


def _bad(what: str, why: str) -> dict[str, Any]:
    return {"item": what, "state": "failed", "why": why[:160]}


def _unknown(what: str, why: str) -> dict[str, Any]:
    return {"item": what, "state": "unknown", "why": why[:160]}


# ---------------------------------------------------------------- the pieces a job can produce
def file_row(tenant: str, file_id: str):
    from sqlalchemy import select

    from ..db import PcFile, session
    with session() as s:
        r = s.scalars(select(PcFile).where(PcFile.id == file_id, PcFile.tenant_id == tenant)).first()
        if r is None:
            return None
        s.expunge(r)
        return r


def check_file_id(tenant: str, file_id: str) -> dict[str, Any]:
    r = file_row(tenant, file_id)
    if r is None:
        return _bad(file_id, "aisi koi file nahi bani (file id record mein nahi hai)")
    p = Path(r.stored_path or "")
    if not r.stored_path or not p.exists():
        return _bad(r.name or file_id, "file ka record hai par file disk par nahi hai")
    size = p.stat().st_size
    if size <= 0:
        return _bad(r.name or file_id, "file khaali hai (0 bytes)")
    return _ok(r.name or file_id, f"{size} bytes")


def check_artifact(tenant: str, art_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    from ..db import Artifact, ArtifactVersion, session
    with session() as s:
        a = s.scalars(select(Artifact).where(Artifact.id == art_id, Artifact.tenant_id == tenant)).first()
        if a is None:
            return _bad(art_id, "aisa koi page nahi bana")
        if a.deleted:
            return _bad(a.title or art_id, "page delete ho chuka hai")
        if not a.version or a.status != "ready":
            return _bad(a.title or art_id, f"page tayyar nahi hai (status {a.status})")
        v = s.scalars(select(ArtifactVersion).where(ArtifactVersion.artifact_id == a.id,
                                                    ArtifactVersion.version == a.version)).first()
        if v is None or not (v.html or "").strip():
            return _bad(a.title or art_id, "page ka content khaali hai")
        return _ok(a.title or art_id, f"v{a.version}, {len(v.html)} chars")


def check_dataset(tenant: str, item: str) -> dict[str, Any] | None:
    """A dataset the job made (`ds_xxxxxxxxxx`, data_fetch / data_read): its file must be there with rows in it.
    Not a dataset id -> None (nothing to check)."""
    m = _DS_ID.search(item or "")
    if m is None:
        return None
    ds = m.group(0)
    try:
        from .. import datasets as D
        doc = D.load(tenant, ds)
    except Exception as e:   # noqa: BLE001 - DataError = it is not there (14-day sweep), anything else = unknown
        if type(e).__name__ == "DataError":
            return _bad(ds, "yeh dataset ab nahi hai")
        return _unknown(ds, f"dataset check nahi ho paya ({type(e).__name__})")
    rows = doc.get("rows") if isinstance(doc, dict) else None
    n = len(rows or []) if isinstance(rows, list) else 0
    return _ok(ds, f"{n} rows") if n else _bad(ds, "dataset khaali hai")


def check_link(url: str) -> dict[str, Any]:
    """One HEAD (then a ranged GET where HEAD is refused). Unreachable = unknown, 404 / 410 = failed.
    `goal_verify_links` off (tests, an offline box) = unknown without any call."""
    import httpx

    from ..config import get_settings
    if not getattr(get_settings(), "goal_verify_links", True):
        return _unknown(url, "link check band hai")
    STATS["links_checked"] += 1
    try:
        with httpx.Client(timeout=LINK_TIMEOUT_S, follow_redirects=True) as c:
            r = c.head(url)
            if r.status_code in (403, 405, 501):
                r = c.get(url, headers={"Range": "bytes=0-256"})
    except Exception as e:   # noqa: BLE001 - network trouble is never a verdict on her work
        return _unknown(url, f"link check nahi ho paya ({type(e).__name__})")
    if r.status_code in (404, 410):
        return _bad(url, f"link par kuch nahi hai ({r.status_code})")
    if r.status_code >= 500:
        return _unknown(url, f"server ne {r.status_code} diya - abhi pata nahi chala")
    if r.status_code >= 400:
        return _unknown(url, f"link ne {r.status_code} diya (shayad login chahiye)")
    return _ok(url, str(r.status_code))


# v0.665 SACH KA HISAAB: the gate looks only at what THIS job made. "Q3 report.pdf" from last month, or three old
# reminders, used to pass a job that claimed them - every row the tenant ever had was counted.
import contextvars as _cv
from datetime import timedelta as _td, timezone as _tz

SINCE: "_cv.ContextVar" = _cv.ContextVar("verify_since", default=None)


def _new(at) -> bool:
    """Was this row made after the job began? (no start known = every row counts, the old behaviour)"""
    since = SINCE.get()
    if since is None or at is None:
        return True
    a = at if at.tzinfo else at.replace(tzinfo=_tz.utc)
    b = since if since.tzinfo else since.replace(tzinfo=_tz.utc)
    return a >= b - _td(seconds=90)


def _delivered(tenant: str) -> list[tuple[str, str]]:
    from sqlalchemy import select

    from ..db import PcFile, session
    with session() as s:
        return [(r.name or "", r.stored_path or "")
                for r in s.scalars(select(PcFile).where(PcFile.tenant_id == tenant,
                                                        PcFile.direction == "to_phone")
                                   .order_by(PcFile.created_at)).all() if _new(r.created_at)]


def check_filename(tenant: str, name: str) -> dict[str, Any]:
    want = name.strip().lower()
    for nm, path in _delivered(tenant):
        if nm.lower() == want or want in nm.lower():
            p = Path(path)
            if path and p.exists() and p.stat().st_size > 0:
                return _ok(nm, f"{p.stat().st_size} bytes")
            return _bad(nm, "file ka record hai par file disk par nahi hai")
    return _bad(name, "is naam ki koi file nahi bani")


# ---------------------------------------------------------------- what the job says it made
def check_made(tenant: str, made: list[str] | None) -> list[dict[str, Any]]:
    """One row per claimed item. An item that holds nothing checkable is skipped (no row), so a prose line in
    `made` never fails a good job - the step checks are where a plan can demand real evidence."""
    rows: list[dict[str, Any]] = []
    links = 0
    for raw in list(made or [])[:20]:
        item = str(raw or "").strip()
        if not item:
            continue
        fid = _PC_LINK.search(item) or _FILE_ID.search(item)
        if fid:
            rows.append(check_file_id(tenant, fid.group(1) if fid.re is _PC_LINK else fid.group(0)))
            continue
        aid = _ART_LINK.search(item) or _ART_ID.search(item)
        if aid:
            rows.append(check_artifact(tenant, aid.group(1) if aid.re is _ART_LINK else aid.group(0)))
            continue
        url = _URL.search(item)
        if url:
            if links >= MAX_LINKS:
                rows.append(_unknown(url.group(0), "itne link ek saath check nahi kiye"))
            else:
                links += 1
                rows.append(check_link(url.group(0)))
            continue
        fn = _FILENAME.search(item)
        if fn:
            rows.append(check_filename(tenant, fn.group(0)))
            continue
        ds = check_dataset(tenant, item)
        if ds is not None:
            rows.append(ds)
    return rows


# ---------------------------------------------------------------- what a plan step demands
def _file_info(tenant: str, hint: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """The file a step points at (by id, link or name; else the newest delivered one) + what is inside it."""
    from ..quality.longcard import read_file           # the long card's reader: pypdf / openpyxl / docx / pptx
    fid = _PC_LINK.search(hint or "") or _FILE_ID.search(hint or "")
    row = None
    if fid:
        row = file_row(tenant, fid.group(1) if fid.re is _PC_LINK else fid.group(0))
    if row is None:
        fn = _FILENAME.search(hint or "")
        names = _delivered(tenant)
        pick = None
        if fn:
            want = fn.group(0).lower()
            pick = next((x for x in names if want in x[0].lower()), None)
        if pick is None and names:
            pick = names[-1]
        if pick is None:
            return None, {"ok": False, "why": "koi file nahi mili"}
        name, path = pick
    else:
        name, path = row.name or "", row.stored_path or ""
    kind = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    info = read_file(path, kind) if path else {"ok": False, "why": "file disk par nahi hai"}
    return {"name": name, "path": path, "kind": kind}, info


def check_step(tenant: str, conv: str, step: dict[str, Any], calls: list[dict] | None = None) -> dict[str, Any] | None:
    """The step's own `check`, or None when it has none / the check text is not understood (never a failure: a plan
    may not invent a check and thereby fail an honest job)."""
    spec = str(step.get("check") or "").strip()
    if not spec:
        return None
    m = _CHECK.match(spec)
    if m is None:
        return _unknown(f"step {step.get('n')}", f"check samajh nahi aaya: {spec[:60]}")
    kind, arg, num = m.group(1).lower(), (m.group(2) or "").strip(), int(m.group(3) or 0)
    note = str(step.get("note") or "")
    where = f"step {step.get('n')} ({str(step.get('text') or '')[:40]})"
    if kind == "tool":
        hit = [c for c in (calls or []) if c.get("ok") and str(c.get("tool") or "") == arg]
        return _ok(where, f"{arg} chala") if hit else _bad(where, f"{arg} is kaam mein chala hi nahi")
    if kind == "link_ok":
        url = _URL.search(note)
        return check_link(url.group(0)) if url else _bad(where, "step ke note mein koi link nahi hai")
    if kind == "artifact":
        aid = _ART_LINK.search(note) or _ART_ID.search(note)
        if aid:
            return check_artifact(tenant, aid.group(1) if aid.re is _ART_LINK else aid.group(0))
        from sqlalchemy import select

        from ..db import Artifact, session
        with session() as s:
            a = s.scalars(select(Artifact).where(Artifact.tenant_id == tenant, Artifact.status == "ready",
                                                 Artifact.deleted.is_(False))
                          .order_by(Artifact.updated_at.desc())).first()
            aid2 = a.id if a is not None and _new(a.updated_at) else ""
        return check_artifact(tenant, aid2) if aid2 else _bad(where, "koi tayyar page nahi hai")
    if kind in ("reminder", "routine"):
        from sqlalchemy import select

        from ..db import Reminder, Routine, session
        want = max(1, num)
        with session() as s:
            rows = s.scalars(select(Reminder if kind == "reminder" else Routine)
                             .where((Reminder if kind == "reminder" else Routine).tenant_id == tenant,
                                    (Reminder if kind == "reminder" else Routine).status == "active")).all()
            rows = [x for x in rows if _new(x.created_at)]
        return (_ok(where, f"{len(rows)} active") if len(rows) >= want
                else _bad(where, f"sirf {len(rows)} {kind} lage, {want} chahiye the"))
    if kind == "list":
        from sqlalchemy import select

        from ..db import ListItem, session
        want = max(1, num)
        with session() as s:
            rows = [x for x in s.scalars(select(ListItem).where(ListItem.tenant_id == tenant)).all()
                    if (not arg or arg.lower() in (x.list_name or "").lower()) and _new(x.created_at)]
        return (_ok(where, f"{len(rows)} items") if len(rows) >= want
                else _bad(where, f"list mein sirf {len(rows)} items, {want} chahiye the"))
    # the file family
    hint = (arg + " " + note) if kind == "file" else note
    f, info = _file_info(tenant, hint)
    if f is None or not info.get("ok"):
        return _bad(where, str(info.get("why") or "file nahi mili"))
    if kind == "file":
        return _ok(where, f["name"])
    got = int(info.get({"file_pages": "pages", "file_rows": "rows", "file_slides": "slides"}[kind], 0) or 0)
    want = max(1, num)
    unit = {"file_pages": "page", "file_rows": "row", "file_slides": "slide"}[kind]
    return (_ok(where, f"{f['name']}: {got} {unit}s") if got >= want
            else _bad(where, f"{f['name']} mein {got} {unit}s hain, {want} chahiye the"))


# ---------------------------------------------------------------- the gate
def line_for(failures: list[dict], unknown: list[dict]) -> str:
    out = ""
    if failures:
        out = "Yeh cheezein asal mein nahi mili: " + "; ".join(f"{f['item']} - {f['why']}" for f in failures[:4])
    if unknown:
        out += (" " if out else "") + "Check nahi ho paya: " + "; ".join(
            f"{u['item']} - {u['why']}" for u in unknown[:3])
    return out.strip()[:400]


def gate(tenant: str, conv: str, made: list[str] | None, steps: list[dict] | None,
         calls: list[dict] | None = None, since=None) -> dict[str, Any]:
    """Can this job close as done? Never raises: a broken check must not break her job (it reads as unknown)."""
    STATS["gates"] += 1
    tok = SINCE.set(since)
    try:
        return _gate(tenant, conv, made, steps, calls)
    finally:
        SINCE.reset(tok)


def _gate(tenant: str, conv: str, made: list[str] | None, steps: list[dict] | None,
          calls: list[dict] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    try:
        rows += check_made(tenant, made)
    except Exception as e:   # noqa: BLE001
        log.exception("made check failed")
        rows.append(_unknown("made", f"check crash: {type(e).__name__}"))
    for st in list(steps or []):
        if str(st.get("state") or "") in ("skipped", "pending"):
            continue
        try:
            r = check_step(tenant, conv, st, calls)
        except Exception as e:   # noqa: BLE001
            log.exception("step check failed")
            r = _unknown(f"step {st.get('n')}", f"check crash: {type(e).__name__}")
        if r is not None:
            rows.append(dict(r, n=st.get("n")))
    failures = [r for r in rows if r["state"] == "failed"]
    unknown = [r for r in rows if r["state"] == "unknown"]
    STATS["passed" if not failures else "failed"] += 1
    if unknown:
        STATS["unknown"] += 1
    return {"ok": not failures, "checked": len(rows), "failures": failures, "unknown": unknown,
            "line": line_for(failures, unknown)}


NUDGE = ("[System check, not the user] The job cannot close as done: {line}. These were checked in code, not by "
         "opinion - a file that is not on disk, a page that is not ready, a link that 404s, or a step whose own "
         "check failed. Go back and really do the failing part now with the tools (then mark the step done again), "
         "or if it truly cannot be done, call kaam_plan finish failed / blocked_on_her with the plain reason. "
         "Never call finish done for something that is not there.")

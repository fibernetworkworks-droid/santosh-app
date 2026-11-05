"""The LEADS engine's work (docs/LEADS_PLAN.md sections 4, 5.4-5.6, 7): the run store, the deduper, the
provenance gate, the exports and the outreach LEDGER.

Honesty rules encoded here, not remembered anywhere:
- add_row() refuses a row without provenance (source_lane in rules.LANES + source_url). No row without a source
  is ever stored, so no export can ever ship one by accident - and export_csv() still re-checks (belt).
- plan() refuses an unbuilt lane BY NAME with the phase that builds it. L0 (her data) is the only P0 lane.
- campaign_list() is the ONLY hand-off to the WhatsApp campaign desk, it copies ONLY rows with a phone, it
  pre-fills consent False for every scraped/her row, and it writes the LeadOutreach ledger - the sending side
  still goes through the campaign desk's own consent machinery. The engine itself never sends.
- forget() deletes rows (and their list refs) on her word; the day's cap ledger survives the deletion, so the
  day's count cannot be reset by forgetting (the v0.190.1 lesson inverted: some state must outlive erasure).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from .. import leadscap
from .importer import normalize_phone
from .models import LeadContact, LeadListRef, LeadOutreach, LeadRun, ensure_tables
from . import rules as R

PARSER_VERSION = "v0.540.0-her1"        # the L0 her-data reader; every row names the code that read its source

_LEAD_FIELDS = ("name", "category", "address", "city", "state", "pincode", "phone", "website", "email")


class LeadsError(ValueError):
    """A refusal the card can show as-is (Hinglish, the reason named)."""


# ---------------------------------------------------------------- identity (plan 5.4)
def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def identity_key(row: dict) -> tuple[str, str]:
    """The row's natural key, strongest first: an explicit listing id (kgmid/cid/place_id - P3's lanes will hand
    these), else the E.164 phone (her data), else a normalised name+ADDRESS hash (gosom's deduper idea). A name
    alone is not an identity - 'Patil Clinic' exists in every city - so a row with neither phone nor address is
    refused, not guessed into the store."""
    for t in ("kgmid", "cid", "place_id"):
        v = str(row.get(t) or "").strip()
        if v:
            return t, v
    phone = normalize_phone(row.get("phone"))
    if phone:
        return "phone_e164", phone
    name, addr = _norm(row.get("name")), _norm(row.get("address") or row.get("city"))
    if name and addr:
        h = hashlib.sha1(f"{name}|{addr}".encode("utf-8")).hexdigest()[:20]
        return "name_address", h
    raise LeadsError("Row mein na phone hai na (naam + address) - bina key ki row store nahi hoti (dedup sambhav nahi).")


# ---------------------------------------------------------------- the plan card (PLAN PEHLE)
def plan(tenant: str, ask: str, lanes: list[str] | None = None, place: str = "", planned_rows: int = 0) -> dict:
    """The card BEFORE anything runs: lanes (refused by name if unbuilt), the caps, the one question if her ask
    is vague. Returns {"ok": bool, ...}; a refusal card never raises - the caller shows it and stops."""
    lanes = [l.upper() for l in (lanes or ["HER_DATA"])]
    unknown = [l for l in lanes if l not in R.LANES]
    unbuilt = [l for l in lanes if l not in R.LANE_BUILT]
    card: dict[str, Any] = {"ok": True, "kind": "leads_plan", "tenant": tenant, "ask": ask, "place": place,
                            "lanes": lanes, "caps": leadscap.caps(), "planned_rows": planned_rows,
                            "parser_version": PARSER_VERSION}
    if unknown or unbuilt:
        card["ok"] = False
        card["refused_lanes"] = unknown + unbuilt
        card["why"] = [f"{l} abhi built nahi hai - {R.LANE_ARRIVES.get(l, 'aage ek phase mein')} aayega "
                       f"(plan: docs/LEADS_PLAN.md)" for l in unbuilt] + \
                      [f"{l} koi lane hi nahi hai - lanes hain: {', '.join(R.LANES)}" for l in unknown]
        card["lanes"] = [l for l in lanes if l in R.LANE_BUILT]
        if not card["lanes"]:
            if not str(place or "").strip():
                card["need"] = R.ONE_QUESTION            # the refusal carries the one question too
            return card
    if not str(ask or "").strip() or (not str(place or "").strip() and any(l != "HER_DATA" for l in card["lanes"])):
        card["ok"] = False
        card["need"] = R.ONE_QUESTION
        return card
    try:
        card["cap_check"] = leadscap.check_run(tenant, planned_rows)
    except leadscap.LeadsCapped as e:
        card["ok"] = False
        card["cap_refusal"] = str(e)
    return card


# ---------------------------------------------------------------- the run (L0: her data)
def _clean_row(row: dict) -> dict:
    """One business row from her data -> the store's fields, house-laws applied (E.164 phone, facts only)."""
    out: dict[str, str] = {}
    for f in _LEAD_FIELDS:
        v = row.get(f)
        if v is None and f == "phone":
            v = row.get("mobile") or row.get("whatsapp")
        out[f] = str(v).strip() if v is not None else ""
    phone = normalize_phone(out.get("phone"))
    out["phone"] = phone or ""
    return out


def run_her_data(tenant: str, ask: str, rows: list[dict], source_name: str, place: str = "",
                 lanes: list[str] | None = None, actor: str = "owner") -> dict:
    """L0: her own data into the store, one row per business, provenance = the file/list's name. PLAN PEHLE: the
    caps are checked before the first row is written; a cap refusal is a REFUSED run card, an UNBUILT lane or a
    vague ask raises (nothing to run at all)."""
    ensure_tables()
    p = plan(tenant, ask, lanes or ["HER_DATA"], place, planned_rows=len(rows or []))
    run = _new_run(tenant, ask, place, lanes or ["HER_DATA"], p)
    if not p["ok"]:
        why = "; ".join(p.get("why") or [])
        if why or p.get("need"):
            _delete_run(run.id)          # a lane / ask refusal leaves NO run row behind - nothing was run
            raise LeadsError(why or p.get("need", ""))
        _finish(run, "REFUSED", error=p.get("cap_refusal", ""))
        return {"ok": False, "run": run_card(run.id), "plan": p}
    _status(run, "RUNNING")
    found = kept = duped = refused = 0
    for raw in rows or []:
        found += 1
        try:
            row = _clean_row(raw)
            ktype, kval = identity_key(row)
        except LeadsError:
            refused += 1
            continue
        if not kval:
            refused += 1
            continue
        try:
            _write_row(tenant, run, ktype, kval, row, source_lane="HER_DATA",
                       source_url=str(source_name or "her-data")[:500])
            kept += 1
        except LeadsError as e:
            if "already" in str(e):
                duped += 1
            else:
                refused += 1
    leadscap.record(tenant, kept)
    _counters(run, found, kept, duped, refused)
    _finish(run, "DONE")
    return {"ok": True, "run": run_card(run.id)}   # re-read: the counters / status live in the DB, not the detached object


def _new_run(tenant: str, ask: str, place: str, lanes: list[str], plan_card: dict) -> LeadRun:
    with _s() as s:
        run = LeadRun(tenant_id=tenant, ask=ask[:3000], place=place[:200], lanes=json.dumps(lanes),
                      plan=json.dumps(plan_card, ensure_ascii=False, default=str)[:8000],
                      provenance=json.dumps({"parser_version": PARSER_VERSION, "engine": "hoola-leads", "v": 1}))
        s.add(run)
        s.flush()
        s.expunge(run)
        return run


def _s():
    from ..db import session
    return session()


def _status(run: LeadRun, status: str) -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.status = status
            if status == "DONE":
                r.finished_at = datetime.now(timezone.utc)


def _counters(run: LeadRun, found: int, kept: int, duped: int, refused: int) -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.found, r.kept, r.duped, r.refused = found, kept, duped, refused


def _finish(run: LeadRun, status: str, error: str = "") -> None:
    with _s() as s:
        r = s.get(LeadRun, run.id)
        if r:
            r.status = status
            r.finished_at = datetime.now(timezone.utc)
            if error:
                r.error = error[:600]


def _delete_run(run_id: str) -> None:
    with _s() as s:
        r = s.get(LeadRun, run_id)
        if r:
            s.delete(r)


# ---------------------------------------------------------------- the store (provenance gate + dedup)
def add_row(tenant: str, row: dict, source_lane: str, source_url: str, run_id: str = "",
            parser_version: str = PARSER_VERSION) -> dict:
    """One row into the store. The provenance gate FIRST: no source_lane from rules.LANES, no source_url - no row.
    A duplicate key is not an error: the card says 'already' and the caller counts it as duped."""
    ensure_tables()
    if source_lane not in R.LANES:
        raise LeadsError(f"source_lane '{source_lane}' galat hai - lanes: {', '.join(R.LANES)}. "
                         f"Bina valid source ki row store nahi hoti.")
    if not str(source_url or "").strip():
        raise LeadsError("source_url khaali hai - har row ke saath uska source zaroori hai (provenance).")
    row = _clean_row(row)
    ktype, kval = identity_key(row)
    return _write_row(tenant, None, ktype, kval, row, str(run_id or ""), source_lane, source_url[:500], parser_version)


def _write_row(tenant: str, run: LeadRun | None, ktype: str, kval: str, row: dict, run_id: str = "",
               source_lane: str = "", source_url: str = "", parser_version: str = PARSER_VERSION) -> dict:
    if run is not None:
        run_id = run.id
    with _s() as s:
        exists = s.query(LeadContact).filter(LeadContact.tenant_id == tenant, LeadContact.key_type == ktype,
                                             LeadContact.key_value == kval).first()
        if exists is not None:
            raise LeadsError(f"already: {ktype}/{kval}")
        try:
            c = LeadContact(tenant_id=tenant, run_id=run_id, key_type=ktype, key_value=kval[:120],
                            name=row.get("name", "")[:200], category=row.get("category", "")[:120],
                            address=row.get("address", ""), city=row.get("city", "")[:80],
                            state=row.get("state", "")[:80], pincode=row.get("pincode", "")[:10],
                            phone=row.get("phone", ""), website=row.get("website", "")[:300],
                            email=row.get("email", "")[:200], source_lane=source_lane, source_url=source_url,
                            parser_version=parser_version)
            if row.get("rating") not in (None, ""):
                c.rating = float(row["rating"])
            if row.get("review_count") not in (None, ""):
                c.review_count = int(row["review_count"])
            if row.get("lat") not in (None, "") and row.get("lng") not in (None, ""):
                c.lat, c.lng = float(row["lat"]), float(row["lng"])
            s.add(c)
            s.flush()
            return view_row(c)
        except IntegrityError:
            raise LeadsError(f"already: {ktype}/{kval}") from None


def view_row(c: LeadContact) -> dict:
    return {"id": c.id, "run_id": c.run_id, "key_type": c.key_type, "key_value": c.key_value, "name": c.name,
            "category": c.category, "address": c.address, "city": c.city, "state": c.state, "pincode": c.pincode,
            "phone": c.phone, "website": c.website, "email": c.email, "email_grade": c.email_grade,
            "socials": c.socials or {}, "rating": c.rating, "review_count": c.review_count, "lat": c.lat,
            "lng": c.lng, "source_lane": c.source_lane, "source_url": c.source_url,
            "parser_version": c.parser_version, "opt_out": bool(c.opt_out), "fetched_at": _iso(c.fetched_at)}


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


# ---------------------------------------------------------------- reading the store
def _filters(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "",
             has_phone: bool = False, has_email: bool = False, opt_out: bool | None = None):
    conds = [LeadContact.tenant_id == tenant]
    if q:
        like = f"%{q.strip().lower()}%"
        conds.append(LeadContact.name.ilike(like) | LeadContact.category.ilike(like) | LeadContact.address.ilike(like))
    if city:
        conds.append(LeadContact.city.ilike(f"%{city.strip()}%"))
    if category:
        conds.append(LeadContact.category.ilike(f"%{category.strip()}%"))
    if lane:
        conds.append(LeadContact.source_lane == lane.upper())
    if has_phone:
        conds.append(LeadContact.phone != "")
    if has_email:
        conds.append(LeadContact.email != "")
    if opt_out is not None:
        conds.append(LeadContact.opt_out == bool(opt_out))
    return conds


def rows(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "", has_phone: bool = False,
         has_email: bool = False, opt_out: bool | None = None, limit: int = 50, offset: int = 0) -> dict:
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, has_phone, has_email, opt_out)
    with _s() as s:
        total = s.query(LeadContact).filter(*conds).count()
        got = (s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc(), LeadContact.id)
               .offset(max(0, offset)).limit(min(max(1, limit), 500)).all())
        return {"total": total, "rows": [view_row(c) for c in got], "limit": limit, "offset": offset}


def store_summary(tenant: str) -> dict:
    ensure_tables()
    with _s() as s:
        base = s.query(LeadContact).filter(LeadContact.tenant_id == tenant)
        return {"rows": base.count(), "with_phone": base.filter(LeadContact.phone != "").count(),
                "with_email": base.filter(LeadContact.email != "").count(),
                "opted_out": base.filter(LeadContact.opt_out.is_(True)).count(),
                "by_lane": {l: base.filter(LeadContact.source_lane == l).count() for l in R.LANES}}


# ---------------------------------------------------------------- the runs
def _view(run: LeadRun) -> dict:
    return {"id": run.id, "tenant": run.tenant_id, "ask": run.ask, "place": run.place, "lanes": json.loads(run.lanes or "[]"),
            "plan": json.loads(run.plan or "{}"), "status": run.status, "found": run.found, "kept": run.kept,
            "duped": run.duped, "refused": run.refused, "bill": json.loads(run.bill or "{}"),
            "provenance": json.loads(run.provenance or "{}"), "error": run.error,
            "created_at": _iso(run.created_at), "finished_at": _iso(run.finished_at)}


def run_card(run_id: str) -> dict | None:
    ensure_tables()
    with _s() as s:
        r = s.get(LeadRun, run_id)
        return _view(r) if r else None


def runs(tenant: str, limit: int = 20) -> list[dict]:
    ensure_tables()
    with _s() as s:
        got = (s.query(LeadRun).filter(LeadRun.tenant_id == tenant).order_by(LeadRun.created_at.desc())
               .limit(min(max(1, limit), 100)).all())
        return [_view(r) for r in got]


# ---------------------------------------------------------------- exports (provenance belt)
EXPORT_COLUMNS = ("name", "phone", "category", "address", "city", "state", "pincode", "email", "email_grade",
                  "website", "socials", "rating", "review_count", "lat", "lng", "key_type", "key_value",
                  "source_lane", "source_url", "parser_version", "fetched_at", "opt_out", "run_id")


def export_csv(tenant: str, q: str = "", city: str = "", category: str = "", lane: str = "",
               has_phone: bool = False, has_email: bool = False, run_id: str = "", opt_out: bool | None = False) -> dict:
    """The export that refuses to ship an unprovenanced row (the verify gate). opt_out rows are EXCLUDED by
    default - the campaign desk honours opt-out, so a raw export must not smuggle them in either."""
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, has_phone, has_email, opt_out)
    if run_id:
        conds.append(LeadContact.run_id == run_id)
    with _s() as s:
        got = (s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc())
               .limit(20000).all())
        unprovenanced = [c.id for c in got if not c.source_lane or not c.source_url]
        if unprovenanced:
            raise LeadsError(f"{len(unprovenanced)} rows bina provenance ke hain (ids: {', '.join(unprovenanced[:5])}..."
                             f") - export REFUSE: bina source ki row jaati hi nahi.")
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(EXPORT_COLUMNS)
        for c in got:
            w.writerow([c.name, c.phone, c.category, c.address, c.city, c.state, c.pincode, c.email, c.email_grade,
                        c.website, json.dumps(c.socials or {}, ensure_ascii=False), "" if c.rating is None else c.rating,
                        "" if c.review_count is None else c.review_count, "" if c.lat is None else c.lat,
                        "" if c.lng is None else c.lng, c.key_type, c.key_value, c.source_lane, c.source_url,
                        c.parser_version, _iso(c.fetched_at), int(bool(c.opt_out)), c.run_id])
        name = f"leads-export-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{len(got)}.csv"
        return {"filename": name, "rows": len(got), "csv": buf.getvalue(),
                "provenance": {"every_row_has": ["source_lane", "source_url", "parser_version", "fetched_at"]}}


# ---------------------------------------------------------------- outreach LEDGER + campaign hand-off
def campaign_list(tenant: str, name: str, q: str = "", city: str = "", category: str = "", lane: str = "",
                  has_phone: bool = True, run_id: str = "") -> dict:
    """HER tap arrives here: copy selected rows into a LeadList the campaign desk consumes. Only rows WITH a
    phone can go (campaigns call phones), consent is pre-filled False for every copied row (the sending side
    still needs the desk's consent machinery), and the whole act lands in the LeadOutreach ledger."""
    ensure_tables()
    conds = _filters(tenant, q, city, category, lane, True, False, False)
    if run_id:
        conds.append(LeadContact.run_id == run_id)
    from ..db import Lead, LeadList
    with _s() as s:
        got = s.query(LeadContact).filter(*conds).order_by(LeadContact.fetched_at.desc()).limit(20000).all()
        no_phone = (s.query(LeadContact).filter(*_filters(tenant, q, city, category, lane, False, False, False),
                                                LeadContact.phone == "").count())
        if not got:
            raise LeadsError("Is filter par phone waali koi row nahi - campaign list khaali rahegi.")
        ll = LeadList(tenant_id=tenant, name=name[:200], source_filename=f"leads-store:{run_id or 'store'}",
                      columns=["name", "phone"], has_consent_column=True, total_rows=len(got), valid=len(got),
                      invalid=0, duplicates=0, opted_in=0)
        s.add(ll)
        s.flush()
        for c in got:
            l = Lead(name=c.name or None, phone=c.phone, opted_in=False,
                     extra={"lead_contact_id": c.id, "source_lane": c.source_lane, "source_url": c.source_url,
                            "category": c.category, "city": c.city})
            l.list_id = ll.id
            s.add(l)
            s.flush()
            s.add(LeadListRef(tenant_id=tenant, contact_id=c.id, lead_row_id=l.id, list_id=ll.id))
            s.add(LeadOutreach(tenant_id=tenant, contact_id=c.id, kind="campaign_list", ref=ll.id, desk="campaign"))
        return {"ok": True, "list_id": ll.id, "name": ll.name, "rows": len(got), "rows_without_phone": no_phone,
                "consent": "har row consent=False - bhejna campaign desk ke consent machinery se hi hoga",
                "note": "engine ne khud kuch nahi bheja; sirf list bani (uske tap par)"}


def record_outreach(tenant: str, contact_ids: list[str], kind: str, ref: str, desk: str) -> int:
    """The desk-side ledger write (campaign_sent / email_sent) - called BY the desks when SHE taps, never by a run."""
    ensure_tables()
    with _s() as s:
        n = 0
        for cid in contact_ids:
            s.add(LeadOutreach(tenant_id=tenant, contact_id=cid, kind=kind[:20], ref=ref[:120], desk=desk[:20]))
            n += 1
        return n


def set_opt_out(tenant: str, contact_id: str, opt_out: bool = True) -> dict:
    ensure_tables()
    with _s() as s:
        c = s.get(LeadContact, contact_id)
        if c is None or c.tenant_id != tenant:
            raise LeadsError("Row nahi mili.")
        c.opt_out = bool(opt_out)
        return {"ok": True, "id": c.id, "opt_out": bool(c.opt_out)}


# ---------------------------------------------------------------- forget (the DPO duty)
def forget(tenant: str, run_id: str = "", row_ids: list[str] | None = None, all_rows: bool = False) -> dict:
    """Delete rows / a whole run's rows on her word. The cap ledger survives (the day's count is history, not
    personal data). Returns the counts, says the DPDP duty in the card."""
    ensure_tables()
    if not run_id and not row_ids and not all_rows:
        raise LeadsError("Kya delete karna hai: run_id, ya row_ids, ya all_rows=True (sab).")
    with _s() as s:
        conds = [LeadContact.tenant_id == tenant]
        if run_id:
            conds.append(LeadContact.run_id == run_id)
        if row_ids:
            conds.append(LeadContact.id.in_(list(row_ids)))
        if all_rows:
            conds = [LeadContact.tenant_id == tenant]
        query = s.query(LeadContact).filter(*conds)
        n = query.count()
        ids = [c.id for c in query.all()]
        if ids:
            s.query(LeadListRef).filter(LeadListRef.tenant_id == tenant, LeadListRef.contact_id.in_(ids)).delete(synchronize_session=False)
        query.delete(synchronize_session=False)
        if run_id:
            r = s.get(LeadRun, run_id)
            if r is not None and r.tenant_id == tenant:
                s.delete(r)
        return {"ok": True, "deleted": n, "dpdp": "purpose limitation + erasure (DPO duty) - cap ledger rakha "
                "gaya kyunki woh din ka hisaab hai, personal data nahi"}

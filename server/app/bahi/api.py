"""/api/bahi/* - the GST & Accounts desk (A0). Signed-in owner only (require_key + her tenant). No route returns a WhiteBooks key,
a password, a token or an OTP; none files or pays."""
from __future__ import annotations

from typing import Any


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    from . import bank as BK
    from . import book as BO
    from . import connect as CN
    from . import einv as EV
    from . import gstr1 as G1
    from . import gstr3b as G3
    from . import intake as IN
    from . import itc as IT
    from . import payables as PY
    from . import register as REG
    from . import rules as RU
    from . import service as SV

    r = APIRouter()

    @r.get("/api/bahi/overview", dependencies=[Depends(require_key)])
    def _overview(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return SV.overview(tenant)

    @r.post("/api/bahi/sync", dependencies=[Depends(require_key)])
    def _sync(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        months = b.get("months") if isinstance(b.get("months"), list) else None
        sources = b.get("sources") if isinstance(b.get("sources"), list) else None
        try:
            return REG.sync(tenant, months=months, sources=sources)
        except REG.RegisterError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/register", dependencies=[Depends(require_key)])
    def _register(period: str = "", direction: str = "", source: str = "", q: str = "", limit: int = 200,
                  tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"rows": REG.listing(tenant, period=period, direction=direction, source=source, q=q, limit=limit)}

    @r.get("/api/bahi/rules", dependencies=[Depends(require_key)])
    def _rules() -> dict[str, Any]:
        return {"freshness": RU.freshness(), "files": {n: RU.load(n) for n in RU.NAMES}}

    @r.post("/api/bahi/periods/{period}/lock", dependencies=[Depends(require_key)])
    def _lock(period: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return REG.set_lock(tenant, period, bool(b.get("on", True)), gstin=str(b.get("gstin") or "")[:15],
                                by="owner", note=str(b.get("note") or ""))
        except REG.RegisterError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/connect", dependencies=[Depends(require_key)])
    def _conn(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"connections": CN.status(tenant)}

    def _run(fn, *a, **k):
        try:
            return fn(*a, **k)
        except CN.ConnectError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/connect/start", dependencies=[Depends(require_key)])
    def _cstart(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.start, tenant, str(body.get("gstin") or ""), str(body.get("gst_username") or ""))

    @r.post("/api/bahi/connect/verify", dependencies=[Depends(require_key)])
    def _cverify(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.verify, tenant, str(body.get("gstin") or ""), str(body.get("otp") or ""))

    @r.post("/api/bahi/connect/refresh", dependencies=[Depends(require_key)])
    def _crefresh(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.refresh, tenant, str(body.get("gstin") or ""))

    @r.post("/api/bahi/connect/disconnect", dependencies=[Depends(require_key)])
    def _cdisc(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.disconnect, tenant, str(body.get("gstin") or ""))

    @r.post("/api/bahi/supplier-check", dependencies=[Depends(require_key)])
    def _sup(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _run(CN.supplier_check, tenant, str(body.get("gstin") or ""), filing=bool(body.get("filing", True)))

    def _it(fn, *a, **k):
        try:
            return fn(*a, **k)
        except IT.ItcError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/itc/pull", dependencies=[Depends(require_key)])
    def _ipull(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.pull, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""))

    @r.get("/api/bahi/itc/proposals", dependencies=[Depends(require_key)])
    def _iprop(gstin: str, period: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.propose, tenant, gstin, period)

    @r.post("/api/bahi/itc/decide", dependencies=[Depends(require_key)])
    def _idec(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        d = body.get("decisions") if isinstance(body.get("decisions"), dict) else {}
        return _it(IT.decide, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), d)

    @r.get("/api/bahi/itc/preview", dependencies=[Depends(require_key)])
    def _iprev(gstin: str, period: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.preview, tenant, gstin, period)

    @r.post("/api/bahi/itc/apply", dependencies=[Depends(require_key)])
    def _iapply(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _it(IT.apply, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("plan_hash") or ""),
                   body.get("confirm") is True)

    def _g1(fn, *a, **k):
        try:
            return fn(*a, **k)
        except G1.Gstr1Error as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/gstr1/prepare", dependencies=[Depends(require_key)])
    def _g1prep(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.prepare, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""))

    @r.post("/api/bahi/gstr1/save", dependencies=[Depends(require_key)])
    def _g1save(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.save_draft, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("plan_hash") or ""),
                   body.get("confirm") is True)

    @r.post("/api/bahi/gstr1/evc-otp", dependencies=[Depends(require_key)])
    def _g1otp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.request_evc_otp, tenant, str(body.get("gstin") or ""), str(body.get("pan") or ""))

    @r.post("/api/bahi/gstr1/file", dependencies=[Depends(require_key)])
    def _g1file(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g1(G1.file_evc, tenant, str(body.get("gstin") or ""), str(body.get("period") or ""), str(body.get("pan") or ""),
                   str(body.get("otp") or ""), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    def _g3(fn, *a, **k):
        try:
            return fn(*a, **k)
        except G3.Gstr3bError as e:
            raise HTTPException(400, str(e))

    def _gp3(body):
        return str(body.get("gstin") or ""), str(body.get("period") or "")

    @r.post("/api/bahi/gstr3b/prepare", dependencies=[Depends(require_key)])
    def _g3prep(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.prepare, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/compare", dependencies=[Depends(require_key)])
    def _g3cmp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.compare_with_portal, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/save", dependencies=[Depends(require_key)])
    def _g3save(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.save_draft, tenant, *_gp3(body), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/gstr3b/setoff", dependencies=[Depends(require_key)])
    def _g3off(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.apply_setoff, tenant, *_gp3(body), str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/gstr3b/payment", dependencies=[Depends(require_key)])
    def _g3pay(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.payment_plan, tenant, *_gp3(body))

    @r.post("/api/bahi/gstr3b/evc-otp", dependencies=[Depends(require_key)])
    def _g3otp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.request_evc_otp, tenant, str(body.get("gstin") or ""), str(body.get("pan") or ""))

    @r.post("/api/bahi/gstr3b/file", dependencies=[Depends(require_key)])
    def _g3file(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _g3(G3.file_evc, tenant, *_gp3(body), str(body.get("pan") or ""), str(body.get("otp") or ""),
                   str(body.get("plan_hash") or ""), body.get("confirm") is True)

    def _ev(fn, *a, **k):
        try:
            return fn(*a, **k)
        except EV.EinvError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/einv/status", dependencies=[Depends(require_key)])
    def _evst(gstin: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.status, tenant, gstin)

    @r.post("/api/bahi/einv/connect", dependencies=[Depends(require_key)])
    def _evcon(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.connect, tenant, str(body.get("gstin") or ""), str(body.get("username") or ""), str(body.get("password") or ""),
                   body.get("seller") if isinstance(body.get("seller"), dict) else {}, str(body.get("irp") or ""),
                   str(body.get("ewb_username") or ""), str(body.get("ewb_password") or ""))

    @r.get("/api/bahi/einv/list", dependencies=[Depends(require_key)])
    def _evlist(gstin: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.listing, tenant, gstin)

    @r.post("/api/bahi/einv/build", dependencies=[Depends(require_key)])
    def _evbuild(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.build, tenant, str(body.get("gstin") or ""), str(body.get("doc_id") or ""), body.get("extra") if isinstance(body.get("extra"), dict) else {})

    @r.post("/api/bahi/einv/generate", dependencies=[Depends(require_key)])
    def _evgen(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.generate, tenant, str(body.get("gstin") or ""), str(body.get("doc_id") or ""),
                   body.get("extra") if isinstance(body.get("extra"), dict) else {}, str(body.get("plan_hash") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/einv/cancel", dependencies=[Depends(require_key)])
    def _evcan(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.cancel, tenant, str(body.get("irn_id") or ""), str(body.get("reason") or ""), str(body.get("remark") or ""), body.get("confirm") is True)

    @r.post("/api/bahi/einv/ewb", dependencies=[Depends(require_key)])
    def _evewb(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.ewb_from_irn, tenant, str(body.get("irn_id") or ""), body.get("transport") if isinstance(body.get("transport"), dict) else {},
                   body.get("confirm") is True)

    @r.post("/api/bahi/einv/ewb-cancel", dependencies=[Depends(require_key)])
    def _evewbc(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _ev(EV.ewb_cancel, tenant, str(body.get("irn_id") or ""), str(body.get("reason_code") or "2"), str(body.get("remark") or ""),
                   body.get("confirm") is True)

    def _in(fn, *a, **k):
        try:
            return fn(*a, **k)
        except IN.IntakeError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/bills/intake", dependencies=[Depends(require_key)])
    def _inake(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        g, ch = str(body.get("gstin") or ""), str(body.get("channel") or "upload")
        if body.get("file_id"):
            return _in(IN.intake_file, tenant, g, str(body["file_id"]), ch)
        return _in(IN.intake_text, tenant, g, str(body.get("text") or ""), channel=ch)

    @r.get("/api/bahi/bills", dependencies=[Depends(require_key)])
    def _inlist(status: str = "draft", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"bills": IN.listing(tenant, status)}

    @r.post("/api/bahi/bills/{bill_id}/confirm", dependencies=[Depends(require_key)])
    def _inconf(bill_id: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        return _in(IN.confirm, tenant, bill_id, b.get("overrides") if isinstance(b.get("overrides"), dict) else {}, b.get("accept_errors") is True)

    @r.post("/api/bahi/bills/{bill_id}/reject", dependencies=[Depends(require_key)])
    def _inrej(bill_id: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _in(IN.reject, tenant, bill_id)

    def _bk(fn, *a, **k):
        try:
            return fn(*a, **k)
        except BK.BankError as e:
            raise HTTPException(400, str(e))

    @r.post("/api/bahi/bank/import", dependencies=[Depends(require_key)])
    def _bkimp(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        acct = str(body.get("account") or "bank")[:40]
        pw = str(body.get("password") or "")
        if body.get("file_id"):
            return _bk(BK.import_file, tenant, acct, str(body["file_id"]), pw)
        return _bk(BK.import_text, tenant, acct, str(body.get("name") or "statement.csv"), str(body.get("text") or "").encode("utf-8"), pw)

    @r.post("/api/bahi/bank/match", dependencies=[Depends(require_key)])
    def _bkmatch(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.match, tenant, str((body or {}).get("month") or ""))

    @r.get("/api/bahi/bank/lines", dependencies=[Depends(require_key)])
    def _bklines(status: str = "", month: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"lines": BK.lines(tenant, status, month)}

    @r.post("/api/bahi/bank/confirm", dependencies=[Depends(require_key)])
    def _bkconf(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        ids = body.get("ids") if isinstance(body.get("ids"), list) else []
        return _bk(BK.confirm, tenant, [str(i) for i in ids][:500], float(body.get("min_confidence") or 0))

    @r.post("/api/bahi/bank/unmatch", dependencies=[Depends(require_key)])
    def _bkun(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.unmatch, tenant, str(body.get("id") or ""))

    @r.post("/api/bahi/bank/categorise", dependencies=[Depends(require_key)])
    def _bkcat(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.categorise, tenant, str(body.get("id") or ""), str(body.get("category") or ""), body.get("remember") is not False)

    @r.post("/api/bahi/bank/settlements", dependencies=[Depends(require_key)])
    def _bkset(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.attach_settlements, tenant, body.get("settlements") if isinstance(body.get("settlements"), list) else [])

    @r.post("/api/bahi/bank/reconcile", dependencies=[Depends(require_key)])
    def _bkrec(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.reconcile, tenant, str(body.get("month") or ""), str(body.get("account") or ""))

    @r.get("/api/bahi/bank/reconcile", dependencies=[Depends(require_key)])
    def _bkrecget(month: str, account: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bk(BK.stored, tenant, month, account)

    def _py(fn, *a, **k):
        try:
            return fn(*a, **k)
        except PY.PayError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/parties", dependencies=[Depends(require_key)])
    def _pyparties(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"parties": PY.parties(tenant)}

    @r.post("/api/bahi/parties", dependencies=[Depends(require_key)])
    def _pysave(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _py(PY.party_save, tenant, body, str(body.get("id") or ""))

    @r.get("/api/bahi/ageing", dependencies=[Depends(require_key)])
    def _pyage(direction: str = "out", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return PY.ageing(tenant, "in" if direction == "in" else "out")

    @r.get("/api/bahi/msme", dependencies=[Depends(require_key)])
    def _pymsme(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return PY.msme_watch(tenant)

    @r.get("/api/bahi/rule37", dependencies=[Depends(require_key)])
    def _pyr37(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return PY.rule37_watch(tenant)

    @r.get("/api/bahi/reminders", dependencies=[Depends(require_key)])
    def _pyrem(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"reminders": PY.reminders(tenant)}

    def _wk(body):
        return (str(body.get("party_id") or ""), str(body.get("nature") or ""), float(body.get("amount") or 0), str(body.get("paid_on") or ""),
                body.get("gst_separate") is True, float(body.get("gst_amount") or 0))

    @r.post("/api/bahi/tds/worksheet", dependencies=[Depends(require_key)])
    def _pyws(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _py(PY.worksheet, tenant, *_wk(body))

    @r.post("/api/bahi/tds/record", dependencies=[Depends(require_key)])
    def _pyrec(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _py(PY.record, tenant, *_wk(body), confirm=body.get("confirm") is True)

    @r.post("/api/bahi/tds/deposit", dependencies=[Depends(require_key)])
    def _pydep(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        ids = body.get("ids") if isinstance(body.get("ids"), list) else []
        return _py(PY.deposit, tenant, [str(i) for i in ids][:200], str(body.get("challan") or ""), str(body.get("deposited_on") or ""))

    @r.get("/api/bahi/tds/register", dependencies=[Depends(require_key)])
    def _pyreg(fy: int = 0, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return PY.register(tenant, fy or None)

    @r.get("/api/bahi/tds/quarter", dependencies=[Depends(require_key)])
    def _pyq(fy: int, q: int, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _py(PY.quarter, tenant, fy, q)

    @r.post("/api/bahi/tds/26as", dependencies=[Depends(require_key)])
    def _py26(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return PY.match_26as(tenant, int(body.get("fy") or 0), body.get("rows") if isinstance(body.get("rows"), list) else [])

    def _bo(fn, *a, **k):
        try:
            return fn(*a, **k)
        except BO.BookError as e:
            raise HTTPException(400, str(e))

    @r.get("/api/bahi/book/ledgers", dependencies=[Depends(require_key)])
    def _boled(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"ledgers": BO.ledgers(tenant), "defaults": BO.DEFAULTS}

    @r.post("/api/bahi/book/ledgers", dependencies=[Depends(require_key)])
    def _boledset(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"ledgers": BO.set_ledgers(tenant, body)}

    @r.get("/api/bahi/book/tally.xml", dependencies=[Depends(require_key)])
    def _botally(gstin: str, month: str, tenant: str = Depends(current_tenant)):
        from fastapi import Response
        vs = _bo(BO.vouchers, tenant, gstin.strip().upper(), month)
        return Response(content=BO.to_xml(vs), media_type="application/xml",
                        headers={"Content-Disposition": f'attachment; filename="tally-{month}.xml"'})

    @r.post("/api/bahi/pack/build", dependencies=[Depends(require_key)])
    def _bopack(body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bo(BO.build_pack, tenant, str(body.get("gstin") or ""), str(body.get("month") or ""))

    @r.get("/api/bahi/pack", dependencies=[Depends(require_key)])
    def _bopacks(month: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"packs": BO.packs(tenant, month)}

    @r.get("/api/bahi/pack/{pack_id}/download", dependencies=[Depends(require_key)])
    def _bodl(pack_id: str, tenant: str = Depends(current_tenant)):
        from fastapi import Response
        name, data = _bo(BO.pack_bytes, tenant, pack_id)
        return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @r.post("/api/bahi/pack/{pack_id}/close", dependencies=[Depends(require_key)])
    def _boclose(pack_id: str, body: dict, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return _bo(BO.close_month, tenant, pack_id, str(body.get("sha") or ""), body.get("confirm") is True)

    return r

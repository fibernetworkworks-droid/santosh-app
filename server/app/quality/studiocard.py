"""v0.841 STUDIO CARD (L0 + L15 of docs/LOVABLE_STUDIO_PLAN.md): the Web Studio measured as NUMBERS, the same way every time.

30 asks (studio_asks.py: 10 brochure, 8 shop / booking, 8 portal / dashboard, 4 SaaS) go through the Studio's own engines -
the Site Engine for brochure / shop / booking, the App Engine for portals / dashboards / SaaS - as the hidden tenant
`__studiocard__` (never her sites, never her budget). Each run is scored IN CODE, never by a model:

  built (a version exists and the engine called it ready) - seconds to ready - rupees (the tenant's own model meter) - errors the
  preview raised - gate failures (the Site Engine's launch blockers / the App Engine's scans and rule tests) - design failures
  (AI-look tells / design-token drift) - the words the first screen must show - and, for the 3 small-edit asks, whether the
  exact change landed with NO model call, and how many seconds it took.

`python -m app.quality studio`            the FREE card: the ask set is valid, the scorer is calibrated on planted faults (each fails for
                                          its own reason), and (--proof) the App Engine's proof apps built and walked in the box.
`python -m app.quality studio --live --budget-inr N`   the real run: model calls, interleaved site / app, stops itself at the rupee budget.
`python -m app.quality studio compare <before.json> <after.json>`   metric by metric, the right way round.

Said plainly: the LIVE numbers need a model, a Docker box and Chromium on her server - none exists in a test sandbox, so a card
saved from a sandbox has no live numbers and says so. The judgement thresholds below are defaults, not measured needs."""
from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from .studio_asks import ASKS

TENANT = "__studiocard__"
MAX_DESIGN_FAILS = 2
KINDS = {"brochure": 10, "shop": 8, "portal": 8, "saas": 4}


def set_problems(asks: list[dict] | None = None) -> list[str]:
    asks = asks if asks is not None else ASKS
    out, seen = [], set()
    for a in asks:
        if a["id"] in seen:
            out.append(f"{a['id']}: duplicate id")
        seen.add(a["id"])
        if len(a["ask"]) < 40 or not a["must"] or a["engine"] not in ("site", "app") or a["kind"] not in KINDS:
            out.append(f"{a['id']}: ask / must / engine / kind is not valid")
        if a["kind"] in ("brochure", "shop") and a["engine"] != "site" or a["kind"] in ("portal", "saas") and a["engine"] != "app":
            out.append(f"{a['id']}: engine does not fit the kind")
    for k, n in KINDS.items():
        got = sum(1 for a in asks if a["kind"] == k)
        if got != n:
            out.append(f"{k}: {got} asks, the card wants {n}")
    if sum(1 for a in asks if a.get("edit")) != 3:
        out.append("the card wants exactly 3 small-edit asks")
    return out


def score_run(ask: dict, run: dict) -> dict[str, Any]:
    """One run record -> the scored row. `ok` is True only if nothing below is a failure."""
    reasons = []
    built = bool(run.get("built"))
    if not built:
        reasons.append("not built")
    if int(run.get("errors") or 0):
        reasons.append(f"{run['errors']} preview error(s)")
    if int(run.get("gate_fails") or 0):
        reasons.append(f"{run['gate_fails']} gate failure(s)")
    if int(run.get("design_fails") or 0) > MAX_DESIGN_FAILS:
        reasons.append(f"{run['design_fails']} design failures (over {MAX_DESIGN_FAILS})")
    text = (run.get("text") or "").lower()
    missing = [w for w in ask["must"] if w.lower() not in text]
    if built and missing:
        reasons.append("the first screen does not show: " + ", ".join(missing))
    ed = run.get("edit")
    if ask.get("edit"):
        if not ed or not ed.get("ok"):
            reasons.append("the small edit did not land" + (f" ({ed.get('why')})" if ed and ed.get("why") else ""))
        elif float(ed.get("inr") or 0) > 0:
            reasons.append("the small edit cost money (it must be a code edit, no model call)")
    return {"id": ask["id"], "kind": ask["kind"], "engine": ask["engine"], "ok": not reasons, "reasons": reasons, "built": built,
            "seconds": run.get("seconds"), "inr": run.get("inr"), "errors": int(run.get("errors") or 0),
            "gate_fails": int(run.get("gate_fails") or 0), "design_fails": int(run.get("design_fails") or 0),
            "edit_s": (ed or {}).get("seconds") if ask.get("edit") else None, "skipped": run.get("skipped") or ""}


def _good(ask: dict) -> dict:
    run = {"built": True, "seconds": 90, "inr": 12.0, "errors": 0, "gate_fails": 0, "design_fails": 0,
           "text": " ".join(ask["must"]) + " welcome"}
    if ask.get("edit"):
        run["edit"] = {"ok": True, "seconds": 1.2, "inr": 0.0}
    return run


def calibration() -> list[dict]:
    """Planted faults: each must fail for its OWN reason, and the clean run must pass."""
    plain = next(a for a in ASKS if not a.get("edit"))
    edit = next(a for a in ASKS if a.get("edit"))
    cases = [("clean run passes", plain, _good(plain), True, ""),
             ("clean run with an edit passes", edit, _good(edit), True, "")]
    for name, mut, why in (("not built", {"built": False}, "not built"),
                           ("a preview error", {"errors": 2}, "preview error"),
                           ("a gate failure", {"gate_fails": 1}, "gate failure"),
                           ("too many design failures", {"design_fails": 3}, "design failures"),
                           ("the first screen lacks the business", {"text": "nothing useful here"}, "does not show")):
        cases.append((name, plain, {**_good(plain), **mut}, False, why))
    cases.append(("the small edit did not land", edit, {**_good(edit), "edit": {"ok": False, "why": "no unique place", "inr": 0}}, False, "did not land"))
    cases.append(("the small edit cost money", edit, {**_good(edit), "edit": {"ok": True, "seconds": 9, "inr": 3.0}}, False, "cost money"))
    out = []
    for name, ask, run, want, why in cases:
        s = score_run(ask, run)
        out.append({"case": name, "ok": s["ok"] == want and (want or any(why in r for r in s["reasons"])), "reasons": s["reasons"]})
    return out


# ------------------------------------------------------------------ summarise / compare
def _med(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def summarise(rows: list[dict], kind: str = "live", planned: int = 0, spent: float = 0.0, budget: float = 0.0) -> dict[str, Any]:
    ran = [r for r in rows if not r.get("skipped")]
    out: dict[str, Any] = {"kind": kind, "asks": len(rows), "ran": len(ran), "planned": planned or len(rows), "spent_inr": round(spent, 2), "budget_inr": budget}
    for eng in ("site", "app", "all"):
        sel = [r for r in ran if eng == "all" or r["engine"] == eng]
        out[eng] = {"n": len(sel), "passed": sum(1 for r in sel if r["ok"]), "built": sum(1 for r in sel if r["built"]),
                    "median_seconds": _med([r["seconds"] for r in sel if r["built"]]), "median_inr": _med([r["inr"] for r in sel if r["built"]]),
                    "preview_errors": sum(r["errors"] for r in sel), "gate_fails": sum(r["gate_fails"] for r in sel),
                    "design_fails": sum(r["design_fails"] for r in sel), "median_edit_s": _med([r["edit_s"] for r in sel])}
    return out


LOWER_BETTER = {"median_seconds", "median_inr", "preview_errors", "gate_fails", "design_fails", "median_edit_s"}


def compare(a: dict, b: dict) -> list[dict]:
    """Metric by metric (the right way round): before -> after."""
    out = []
    for eng in ("site", "app", "all"):
        for k, va in (a.get(eng) or {}).items():
            vb = (b.get(eng) or {}).get(k)
            if k == "n" or va is None or vb is None:
                continue
            better = (vb < va) if k in LOWER_BETTER else (vb > va)
            out.append({"engine": eng, "metric": k, "before": va, "after": vb, "verdict": "same" if va == vb else "better" if better else "worse"})
    return out


# ------------------------------------------------------------------ the free card
def free_card(asks: list[dict] | None = None, proof: bool = False) -> dict[str, Any]:
    asks = asks if asks is not None else ASKS
    cal = calibration()
    card: dict[str, Any] = {"kind": "free", "asks": len(asks), "set_problems": set_problems(asks), "calibration": cal,
                            "calibration_ok": all(c["ok"] for c in cal), "live": "not run: the live card needs a model, a Docker box and Chromium (python -m app.quality studio --live --budget-inr N)"}
    if proof:
        try:
            from ..appengine import proof as P
            card["engine_proof"] = P.run(browser=True)
        except Exception as e:                             # noqa: BLE001 - the card says why it could not
            card["engine_proof"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    ep = card.get("engine_proof")
    card["verdict"] = "PASS" if (not card["set_problems"] and card["calibration_ok"] and (ep is None or ep.get("verdict") == "PASS")) else "FAIL"
    return card


# ------------------------------------------------------------------ the live card
def _spent() -> float:
    from .. import usage as U
    U.flush()
    return U.month_usd(TENANT) * U.usd_inr()


def _strip(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _unique_find(code: str, word: str) -> str:
    return word if code.count(word) == 1 else ""


def run_site(ask: dict) -> dict[str, Any]:
    """A Site Engine ask end to end like an owner (plan -> looks -> the first look -> build -> checks), then the small edit."""
    from ..site import arena as AR
    from ..site import build as B
    from ..site import lineedit as LE
    from ..site import service as S
    t0, inr0 = time.time(), _spent()
    v = S.new(TENANT, ask["ask"], "")
    S.approve_plan(TENANT, v["id"])
    AR._wait(v["id"], ("looks", "failed", "stopped"))
    if S._load(v["id"]).status == "looks":
        S.choose_look(TENANT, v["id"], 0)
        AR._wait(v["id"], ("ready", "failed", "stopped"))
    r = S._load(v["id"])
    secs, inr = round(time.time() - t0, 1), round(_spent() - inr0, 2)
    chk = S._j(r.checks, {})
    out: dict[str, Any] = {"built": r.status == "ready" and bool(r.version), "seconds": secs, "inr": inr, "site": v["id"],
                           "errors": 0, "gate_fails": len(chk.get("blocking") or []),
                           "design_fails": len((chk.get("look") or {}).get("tells") or []) if isinstance(chk.get("look"), dict) else 0}
    try:
        out["text"] = _strip((B.out_dir(TENANT, v["id"], r.version) / "index.html").read_text("utf-8", "replace"))
    except OSError:
        out["text"] = ""
    if ask.get("edit") and out["built"]:
        out["edit"] = _site_edit(S, LE, v["id"], ask["edit"])
    return out


def _site_edit(S, LE, sid: str, e: dict) -> dict[str, Any]:
    t0, inr0 = time.time(), _spent()
    try:
        r = S._load(sid)
        hits = LE.search(r, e["search"])["hits"]
        for h in hits:
            code = S.code_read(TENANT, sid, h["file"])["code"]
            if _unique_find(code, e["search"]):
                LE.edit(TENANT, sid, h["file"], e["search"], e["replace"])
                return {"ok": True, "seconds": round(time.time() - t0, 2), "inr": round(_spent() - inr0, 2)}
        return {"ok": False, "why": "no place where the word appears exactly once", "seconds": round(time.time() - t0, 2), "inr": 0}
    except Exception as ex:                                 # noqa: BLE001
        return {"ok": False, "why": str(ex)[:120], "seconds": round(time.time() - t0, 2), "inr": 0}


def run_app(ask: dict) -> dict[str, Any]:
    """An App Engine ask: a REAL Hoola turn writes the app (tool app_engine), then the box builds it and the scans + browser check run."""
    import asyncio
    from ..appengine import saboot as SB
    from ..appengine import service as AE
    from ..appengine import cloud as CL
    from ..agent import santosh
    from ..db import new_id
    t0, inr0 = time.time(), _spent()
    app = AE.create(TENANT, ask["id"] + " " + ask["kind"], ask["ask"])
    conv = new_id("conv")
    AE.set_conversation(TENANT, app["id"], conv)
    hint = (f"Web Studio App Engine: this chat is only about app {app['number']} (app id {app['id']}). Work on THIS app with the app_engine "
            "tool; never start a new app or website.")
    asyncio.run(santosh.run_turn(conv, f"Build this app: {ask['ask']}\n\n[Web console {hint}]", tenant_id=TENANT))
    b = AE.wait_build(TENANT, app["id"])
    r = AE._load(TENANT, app["id"])
    built = bool(r.version) and (b.get("built") is not False)
    out: dict[str, Any] = {"built": built, "seconds": round(time.time() - t0, 1), "inr": round(_spent() - inr0, 2), "app": app["id"],
                           "errors": len([e for e in (__import__("app.appengine.pick", fromlist=["x"]).errors(r) or []) if e.get("state", "open") == "open"]) if built else 0,
                           "gate_fails": 0, "design_fails": 0, "text": ""}
    if built:
        q = SB.quick(r, int(r.version))
        out["gate_fails"] = sum(1 for x in q["items"] if x["level"] == "fail")
        out["design_fails"] = len(AE.check_all(r)["problems"])
        br = SB.browser_check(r, force=True)
        if br.get("ran") and not br.get("ok"):
            out["errors"] += len(br.get("problems") or [])
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            out["text"] = _app_text(r)
        except Exception:                                   # noqa: BLE001
            out["text"] = ""
        if ask.get("edit"):
            out["edit"] = _app_edit(AE, app["id"], ask["edit"])
    return out


def _app_text(r) -> str:
    from ..appengine import saboot as SB
    from ..appengine import service as AE
    from playwright.sync_api import sync_playwright
    url = f"{SB.ORIGIN}/api/app-preview/{r.preview_token}/"
    with sync_playwright() as pw:
        b = pw.chromium.launch(**SB._chromium_kw())
        try:
            pg = b.new_page()
            pg.route(f"{SB.ORIGIN}/**", SB._serve_route(r))
            pg.goto(url, wait_until="networkidle", timeout=30000)
            fr = next((x for x in pg.frames if "/__app/" in x.url), None)
            return fr.inner_text("body") if fr else ""
        finally:
            b.close()


def _app_edit(AE, aid: str, e: dict) -> dict[str, Any]:
    t0, inr0 = time.time(), _spent()
    try:
        for h in AE.search(TENANT, aid, e["search"])["hits"]:
            code = AE.read_file(TENANT, aid, h["file"])["code"]
            if _unique_find(code, e["search"]):
                AE.edit_lines(TENANT, aid, h["file"], [{"search": e["search"], "replace": e["replace"]}])
                return {"ok": True, "seconds": round(time.time() - t0, 2), "inr": round(_spent() - inr0, 2)}
        return {"ok": False, "why": "no place where the word appears exactly once", "seconds": round(time.time() - t0, 2), "inr": 0}
    except Exception as ex:                                 # noqa: BLE001
        return {"ok": False, "why": str(ex)[:120], "seconds": round(time.time() - t0, 2), "inr": 0}


def estimate(items: list[dict]) -> dict[str, Any]:
    """An assumed price per ask until a live run has measured one (stated as an assumption on the card)."""
    site = sum(1 for a in items if a["engine"] == "site")
    return {"assumed_inr": round(site * 60 + (len(items) - site) * 90), "note": "assumed: Rs 60 per site ask, Rs 90 per app ask - replaced by the measured median after a run"}


def live_card(items: list[dict] | None = None, budget_inr: float = 0.0, runners: dict | None = None) -> dict[str, Any]:
    """Interleaved site / app so a budget that runs out leaves both engines the same coverage; stops itself at the budget."""
    items = items if items is not None else list(ASKS)
    if budget_inr <= 0:
        raise ValueError("a live card needs --budget-inr N (the whole card's rupees)")
    runners = runners or {"site": run_site, "app": run_app}
    site = [a for a in items if a["engine"] == "site"]
    app = [a for a in items if a["engine"] == "app"]
    order = [x for pair in zip(site, app) for x in pair] + site[len(app):] + app[len(site):]
    rows, spent0 = [], _spent()
    for a in order:
        if _spent() - spent0 >= budget_inr:
            rows.append(score_run(a, {"skipped": f"budget Rs {budget_inr} used"}) | {"skipped": "budget used", "ok": False})
            continue
        try:
            run = runners[a["engine"]](a)
        except Exception as e:                              # noqa: BLE001 - one broken ask is a row
            run = {"built": False, "seconds": None, "inr": 0, "errors": 0, "gate_fails": 0, "design_fails": 0, "text": "", "error": str(e)[:200]}
        row = score_run(a, run)
        if run.get("error"):
            row["reasons"].append("crashed: " + run["error"])
        rows.append(row)
    card = summarise(rows, "live", len(order), _spent() - spent0, budget_inr)
    card["rows"] = rows
    return card


# ------------------------------------------------------------------ files / printing
def _dir() -> Path:
    from ..config import get_settings
    d = Path(getattr(get_settings(), "data_dir", "") or "data") / "quality"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(card: dict, label: str = "") -> dict:
    f = _dir() / f"studiocard-{time.strftime('%Y%m%d-%H%M%S')}{('-' + re.sub(r'[^A-Za-z0-9_-]', '', label)) if label else ''}.json"
    card["file"] = str(f)
    f.write_text(json.dumps(card, indent=1, ensure_ascii=False))
    return card


def lines(card: dict) -> list[str]:
    out = [f"STUDIO CARD ({card['kind']})"]
    if card["kind"] == "free":
        out.append(f"  ask set: {card['asks']} asks, problems: {card['set_problems'] or 'none'}")
        out.append(f"  scorer calibration: {sum(1 for c in card['calibration'] if c['ok'])}/{len(card['calibration'])} planted cases behave")
        ep = card.get("engine_proof")
        if ep:
            out.append("  engine proof: " + (ep.get("error") or f"{ep['apps_ok']}/{ep['apps']} apps, traps {ep['traps_refused']}/{ep['traps']}, bad rule refused {ep.get('bad_rule_refused')}, verdict {ep['verdict']}"))
        out.append(f"  {card['live']}")
        out.append(f"  VERDICT: {card['verdict']}")
        return out
    for eng in ("site", "app", "all"):
        e = card[eng]
        out.append(f"  {eng:4}  passed {e['passed']}/{e['n']}  built {e['built']}  median {e['median_seconds']} s  Rs {e['median_inr']}  "
                   f"preview errors {e['preview_errors']}  gate fails {e['gate_fails']}  design fails {e['design_fails']}  small edit {e['median_edit_s']} s")
    out.append(f"  spent Rs {card['spent_inr']} of Rs {card['budget_inr']}; ran {card['ran']} of {card['planned']}")
    return out

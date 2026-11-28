"""D10 PROOF CARD (docs/WEB_DESIGN_ENGINE_PLAN.md phase D10): the old website engine and the new one, side by side on the
same briefs, measured the same way, so the owner can decide whether the new engine becomes the default for NEW websites.

Fair by construction:
- the same 40 briefs as the D0 design card (design_asks.py), each built TWICE through the Web Studio's own Build path
  (the architect's plan, the prototype, "Build the real website"): once on the old engine (HTML) and once on the new one
  (React from the kit), on the hidden tenant `__proofcard__` (never her sites, never her budget);
- the order alternates (old then new for one brief, new then old for the next), so neither engine always goes first;
- both built websites are folders of finished pages: ONE photographer takes the same pictures of both (the home page's
  first screen and the page down on a computer, the home page down a phone, two more pages), with no section numbers;
- ONE scorer (the D0 card's score_row) and ONE critic from another company than the website writer read them, told
  nothing about which engine made what;
- the same speed lab (appengine.speed) measures each home page;
- generated photos are off for both (the D0 rule).

Her verdict per brief ("the old one", "the new one", "the same") outranks every number. The card ends with a
RECOMMENDATION made by code from the numbers and her picks - it never decides; only her tap on the owner page
(site/enginedefault.py) makes the new engine the default.

`python -m app.quality proof`                              FREE: the pairing, the summary and the rule on planted cases.
`python -m app.quality proof --live --budget-inr N [--limit 4]`   real builds; stops itself at the rupee budget.
`python -m app.quality proof --status`                     the newest saved card (also while one runs).

Said plainly: a critic is a model's opinion, the 1-10 scale and the rule's margins are judgement, and lab speed is
this machine, not her visitors' phones. No live proof card has run when this was written."""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from . import designcard as DC
from .design_asks import ASKS, SET_V

TENANT = "__proofcard__"
ENGINES = ("old", "new")
PICKS = ("old", "new", "same")
TIE = 0.25                      # design scores closer than this count as the same (the critic's own noise; judgement)
DESK = {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 1}
PHONE = {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True}


# ---------------------------------------------------------------- the engine of one build (this process only)
def force(engine: str) -> None:
    """The engine the next build uses - in THIS process only (the card's own builds); the server, her decision and her
    sites are untouched."""
    from ..site import enginedefault as ED
    ED.FORCE["engine"] = engine if engine in ENGINES else ""


def order(i: int) -> tuple[str, str]:
    return ("old", "new") if i % 2 == 0 else ("new", "old")


# ---------------------------------------------------------------- one photographer for both engines
def dist_of(site_id: str) -> Path | None:
    """The finished pages of a built website, whichever engine made it."""
    from ..site import build as B
    from ..site import rxhost as RH
    from ..site import service as S
    r = S._load(site_id)
    if RH.is_react(r):
        return RH.dist(r)
    if not r.version:
        return None
    d = B.out_dir(r.tenant_id, r.id, r.version)
    return d if (d / "index.html").is_file() else None


def photos(dist: Path, slugs: list[str]) -> list[tuple[str, bytes]]:
    """The same pictures of any built website: no numbers, no labels, motion reduced."""
    from playwright.sync_api import sync_playwright
    from ..appengine import critic as C
    from ..appengine import speed as SP
    srv, base = SP.serve(dist)
    srv.handle_error = lambda *a: None
    got: dict[str, dict[str, bytes]] = {}
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            try:
                desk = b.new_context(**DESK, reduced_motion="reduce", bypass_csp=True)
                phone = b.new_context(**PHONE, reduced_motion="reduce", bypass_csp=True)
                for slug in slugs:
                    rec: dict[str, bytes] = {}
                    for name, ctx in (("desk", desk), ("phone", phone)):
                        if name == "phone" and slug != "home":
                            continue
                        pg = ctx.new_page()
                        try:
                            pg.goto(base + C.route(slug), wait_until="load", timeout=30000)
                            try:
                                pg.wait_for_load_state("networkidle", timeout=5000)
                            except Exception:        # noqa: BLE001
                                pass
                            if name == "desk" and slug == "home":
                                rec["first"] = pg.screenshot(type="png")
                            rec[name + "_full"] = pg.screenshot(type="png", full_page=True)
                        finally:
                            pg.close()
                    got[slug] = rec
            finally:
                b.close()
    finally:
        srv.shutdown()
    out: list[tuple[str, bytes]] = []
    home = got.get("home") or {}
    if home.get("first"):
        out.append(("the home page on a computer, first screen", C.jpeg(C._img(home["first"]))))
    if home.get("desk_full"):
        out.append(("the home page on a computer, down the page in columns", C.jpeg(C.tile(home["desk_full"], 720, 1100, 3))))
    if home.get("phone_full"):
        out.append(("the home page on a phone, down the page screen by screen", C.jpeg(C.tile(home["phone_full"], 390, 844, 4))))
    for slug in [s for s in slugs if s != "home"][:2]:
        f = (got.get(slug) or {}).get("desk_full")
        if f:
            out.append((f"the '{slug}' page on a computer, down the page in columns", C.jpeg(C.tile(f, 720, 1100, 3))))
    return out


def home_pair(dist: Path) -> list[bytes]:
    """The home page on a phone and on a computer (the Arena duel's two pictures), for any built website."""
    from playwright.sync_api import sync_playwright
    from ..appengine import speed as SP
    srv, base = SP.serve(dist)
    srv.handle_error = lambda *a: None
    out: list[bytes] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            try:
                for opts in (PHONE, {**DESK, "viewport": {"width": 1440, "height": 900}}):
                    ctx = b.new_context(**opts, reduced_motion="reduce", bypass_csp=True)
                    pg = ctx.new_page()
                    try:
                        pg.goto(base, wait_until="load", timeout=30000)
                        out.append(pg.screenshot(type="png", full_page=True))
                    finally:
                        ctx.close()
            finally:
                b.close()
    finally:
        srv.shutdown()
    return out


def lcp(dist: Path) -> int | None:
    """The home page's largest paint in the speed lab (the same lab for both engines)."""
    from ..appengine import speed as SP
    try:
        rep = SP.lab(dist, ["/"])
        return int((rep.get("pages") or [{}])[0].get("lcp_ms") or 0) or None
    except Exception:                                   # noqa: BLE001 - no number is said as no number
        return None


# ---------------------------------------------------------------- one brief on one engine
def _spent() -> float:
    from .. import usage as U
    U.flush()
    return U.month_usd(TENANT) * U.usd_inr()


def run_one(ask: dict, engine: str, run_dir: Path, critic_on: bool = True, photos_off: bool = True,
            limit_s: int = DC.SITE_LIMIT_S) -> dict[str, Any]:
    from ..site import architect as AR
    from ..site import look as LK
    from ..site import rxhost as RH
    from ..site import service as S
    force(engine)
    t0, inr0 = time.time(), _spent()
    out: dict[str, Any] = {"engine": engine, "built": False, "gate_fails": 0, "look_tells": 0, "text": ""}
    v = AR.build_now(TENANT, ask["ask"], "", "", None, True)
    sid = str(v.get("id") or "")
    if not sid:
        out["error"] = "the Studio started no site" + (" (it asked questions)" if v.get("questions") else "")
        out["seconds"], out["inr"] = round(time.time() - t0, 1), round(_spent() - inr0, 2)
        return out
    status = DC._drive(sid, limit_s, tenant=TENANT)
    r = S._load(sid)
    react = RH.is_react(r)
    dist = dist_of(sid)
    out.update(site=sid, status=status, react=react, built=r.status == "ready" and dist is not None,
               seconds=round(time.time() - t0, 1))
    if engine == "new" and out["built"] and not react:
        out["built"] = False
        out["error"] = "built on the old engine although the new one was asked for"
    if not out["built"]:
        out["error"] = out.get("error") or (r.error or status or "")[:240]
    out["purpose"], out["kind"] = DC._purpose_of(r, v)
    if react:
        bl = RH.blockers(r)
        out["gate_fails"] = sum(1 for b in bl if not b.startswith("fill in"))
        out["blanks"] = sum(1 for b in bl if b.startswith("fill in"))
    else:
        chk = S._j(r.checks, {}) or {}
        out["gate_fails"] = len(chk.get("blocking") or [])
    if out["built"] and dist is not None:
        try:
            out["text"] = DC._strip((dist / "index.html").read_text("utf-8", "replace"))
        except OSError:
            out["text"] = ""
        try:
            out["look_tells"] = int(LK.scan(dist, S._ctx(r)).get("count") or 0)
        except Exception:                               # noqa: BLE001
            out["look_tells"] = 0
        out["lcp_ms"] = lcp(dist)
        slugs = [p.get("slug") for p in (S._j(r.plan, {}) or {}).get("pages") or [] if p.get("slug")]
        try:
            imgs = photos(dist, ["home"] + [s for s in slugs if s != "home"][:2])
        except Exception as e:                          # noqa: BLE001 - no pictures = no critic score, said
            imgs, out["shots_error"] = [], f"{type(e).__name__}: {e}"[:200]
        names = []
        for i, (name, data) in enumerate(imgs):
            fn = f"{ask['id']}-{engine}-{i + 1}.jpg"
            (run_dir / fn).write_bytes(data)
            names.append({"file": fn, "what": name})
        out["shots"] = names
        if critic_on:
            out["critic"] = DC.critic(ask, out["purpose"], imgs, photos_off, tenant=TENANT)
    out["inr"] = round(_spent() - inr0, 2)
    return out


# ---------------------------------------------------------------- pairs, the summary and the rule
def pair_of(ask: dict, old: dict, new: dict) -> dict[str, Any]:
    a, b = DC.score_row(ask, old), DC.score_row(ask, new)
    da, db = a.get("design"), b.get("design")
    if a["built"] and b["built"] and da is not None and db is not None:
        win = "same" if abs(db - da) < TIE else ("new" if db > da else "old")
    elif b["built"] and not a["built"]:
        win = "new"
    elif a["built"] and not b["built"]:
        win = "old"
    else:
        win = "none"
    return {"id": ask["id"], "group": ask["group"], "old": a, "new": b, "critic_pick": win,
            "design_gain": round(db - da, 2) if da is not None and db is not None else None}


def summarise(pairs: list[dict], picks: dict[str, dict] | None = None, planned: int = 0, spent: float = 0.0,
              budget: float = 0.0) -> dict[str, Any]:
    picks = picks or {}
    out: dict[str, Any] = {"set": SET_V, "briefs": len(pairs), "planned": planned or len(pairs), "spent_inr": round(spent, 2),
                           "budget_inr": budget}
    for eng in ENGINES:
        out[eng] = DC.summarise([p[eng] for p in pairs if not p[eng].get("skipped")], "live")["all"]
    cp = [p["critic_pick"] for p in pairs]
    out["critic"] = {"new": cp.count("new"), "old": cp.count("old"), "same": cp.count("same"), "none": cp.count("none")}
    gains = [p["design_gain"] for p in pairs if p.get("design_gain") is not None]
    out["design_gain_median"] = round(statistics.median(gains), 2) if gains else None
    hp = [picks[p["id"]]["pick"] for p in pairs if p["id"] in picks]
    out["her"] = {"new": hp.count("new"), "old": hp.count("old"), "same": hp.count("same"), "picked": len(hp)}
    out["recommendation"] = recommend(out)
    return out


def recommend(s: dict) -> dict[str, Any]:
    """What the numbers and her picks say - a recommendation, never the decision (her tap decides)."""
    o, n = s.get("old") or {}, s.get("new") or {}
    why_not: list[str] = []
    if not (s.get("briefs") and n.get("n")):
        return {"say": "not measured", "ready": False, "why": ["no live proof card has run yet"]}
    if (n.get("built") or 0) < (o.get("built") or 0):
        why_not.append(f"the new engine built {n.get('built')} websites, the old one {o.get('built')}")
    if n.get("design") is not None and o.get("design") is not None and n["design"] < o["design"]:
        why_not.append(f"the critic's median design score is lower on the new engine ({n['design']} vs {o['design']})")
    c = s.get("critic") or {}
    if c.get("old", 0) > c.get("new", 0):
        why_not.append(f"the critic preferred the old engine more often ({c.get('old')} vs {c.get('new')})")
    if (n.get("gate_fails") or 0) > (o.get("gate_fails") or 0):
        why_not.append(f"more launch blockers on the new engine ({n.get('gate_fails')} vs {o.get('gate_fails')})")
    h = s.get("her") or {}
    if h.get("old", 0) > h.get("new", 0):
        why_not.append(f"you picked the old one more often ({h.get('old')} vs {h.get('new')})")
    if not h.get("picked"):
        why_not.append("you have not compared any pair yet")
    ready = not why_not or why_not == ["you have not compared any pair yet"]
    return {"say": "the new engine looks ready" if ready and h.get("picked") else
            "the numbers favour the new engine; compare some pairs yourself first" if ready else "not yet",
            "ready": ready and bool(h.get("picked")), "why": why_not}


def evidence_hash(s: dict) -> str:
    keep = {k: s.get(k) for k in ("set", "briefs", "old", "new", "critic", "her", "design_gain_median")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- free + live
def _ask_of(i: str) -> dict:
    return next(a for a in ASKS if a["id"] == i)


def calibration() -> list[dict]:
    """Planted pairs: each must land for its own reason."""
    biz = next(a for a in ASKS if a["group"] == "business")
    good = DC._good(biz)

    def with_design(d):
        return {**good, "critic": {**good["critic"], "scores": {k: d for k in DC.CRITERIA}, "design": float(d)}}
    cases = [("the new one scores higher", pair_of(biz, with_design(6), with_design(8))["critic_pick"] == "new"),
             ("the old one scores higher", pair_of(biz, with_design(8), with_design(6))["critic_pick"] == "old"),
             ("a hair's difference is the same", pair_of(biz, with_design(7), {**with_design(7), "critic": {
                 **good["critic"], "scores": {**{k: 7 for k in DC.CRITERIA}, "mobile": 8}, "design": 7.12}})["critic_pick"] == "same"),
             ("only the new one built", pair_of(biz, {"built": False}, good)["critic_pick"] == "new"),
             ("neither built", pair_of(biz, {"built": False}, {"built": False})["critic_pick"] == "none")]
    out = [{"case": n, "ok": bool(ok)} for n, ok in cases]
    better = [pair_of(biz, with_design(6), with_design(8)) for _ in range(3)]
    s = summarise(better)
    out.append({"case": "a better new engine is not 'ready' before she compares any pair",
                "ok": s["recommendation"]["ready"] is False and "compare" in s["recommendation"]["say"]})
    s2 = summarise(better, {better[0]["id"]: {"pick": "new"}})
    out.append({"case": "a better new engine she preferred is ready", "ok": s2["recommendation"]["ready"] is True})
    worse = [pair_of(biz, with_design(8), with_design(5)) for _ in range(3)]
    s3 = summarise(worse, {worse[0]["id"]: {"pick": "new"}})
    out.append({"case": "a worse new engine is not ready even if she liked one pair", "ok": s3["recommendation"]["ready"] is False})
    s4 = summarise(better, {better[0]["id"]: {"pick": "old"}})
    out.append({"case": "her pick of the old one stops it", "ok": s4["recommendation"]["ready"] is False})
    out.append({"case": "the order alternates", "ok": order(0) == ("old", "new") and order(1) == ("new", "old")})
    return out


def free_card() -> dict[str, Any]:
    cal = calibration()
    probs = DC.set_problems()
    card = {"kind": "free", "set": SET_V, "briefs": len(ASKS), "set_problems": probs, "calibration": cal,
            "calibration_ok": all(c["ok"] for c in cal), "critic": DC.critic_company(),
            "live": "not run here: the live proof card builds every brief twice (model calls, the App Engine box, Chromium) - "
                    "python -m app.quality proof --live --budget-inr N [--limit 4]"}
    card["verdict"] = "PASS" if not probs and card["calibration_ok"] else "FAIL"
    return card


def live_card(items: list[dict] | None = None, budget_inr: float = 0.0, runner=None, critic_on: bool = True,
              photos_off: bool = True, label: str = "") -> dict[str, Any]:
    from ..config import get_settings
    from ..main import APP_VERSION
    items = items if items is not None else DC.pick()
    if budget_inr <= 0:
        raise ValueError("a live proof card needs --budget-inr N (the rupees for the whole run; every brief is built twice)")
    st = get_settings()
    old = (getattr(st, "site_ai_photos", 6),)
    if photos_off:
        try:
            setattr(st, "site_ai_photos", 0)
        except Exception:                               # noqa: BLE001
            pass
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = _dir() / f"proofcard-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    card: dict[str, Any] = {"kind": "live", "set": SET_V, "version": APP_VERSION, "at": time.time(), "run": run_dir.name,
                            "photos_off": photos_off, "critic_who": DC.critic_company(), "running": True, "pairs": []}
    path = _dir() / f"{run_dir.name}{('-' + re.sub(r'[^A-Za-z0-9_-]', '', label)) if label else ''}.json"
    spent0 = _spent()
    runner = runner or (lambda a, eng: run_one(a, eng, run_dir, critic_on, photos_off))
    try:
        for i, a in enumerate(items):
            if _spent() - spent0 >= budget_inr:
                card["pairs"].append(pair_of(a, {"skipped": "budget used"}, {"skipped": "budget used"}) | {"skipped": "budget used"})
                continue
            runs: dict[str, dict] = {}
            for eng in order(i):
                try:
                    runs[eng] = runner(a, eng)
                except Exception as e:                  # noqa: BLE001 - one broken build is a row
                    runs[eng] = {"engine": eng, "built": False, "error": f"{type(e).__name__}: {e}"[:240]}
            card["pairs"].append(pair_of(a, runs["old"], runs["new"]))
            card.update(summarise(card["pairs"], {}, len(items), _spent() - spent0, budget_inr))
            _write(path, card)
    finally:
        force("")
        try:
            setattr(st, "site_ai_photos", old[0])
        except Exception:                               # noqa: BLE001
            pass
    card.update(summarise(card["pairs"], {}, len(items), _spent() - spent0, budget_inr))
    card["running"] = False
    card["file"] = str(path)
    _write(path, card)
    return card


# ---------------------------------------------------------------- files and her picks
def _dir() -> Path:
    return DC._dir()


def _write(path: Path, card: dict) -> None:
    DC._write(path, card)


def save(card: dict, label: str = "") -> dict:
    f = _dir() / f"proofcard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}{('-' + re.sub(r'[^A-Za-z0-9_-]', '', label)) if label else ''}.json"
    card["file"] = str(f)
    _write(f, card)
    return card


def cards() -> list[Path]:
    return sorted((p for p in _dir().glob("proofcard-*.json") if re.fullmatch(r"proofcard-\d{8}-\d{6}(-[A-Za-z0-9_-]+)?", p.stem)),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def _pfile() -> Path:
    return _dir() / "proofcard-picks.json"


def picks(run: str) -> dict[str, dict]:
    try:
        return dict((json.loads(_pfile().read_text()) or {}).get(run) or {})
    except (OSError, ValueError):
        return {}


def set_pick(run: str, brief: str, pick: str, note: str = "") -> dict[str, Any]:
    """Her word on one pair: which one she would rather have. It outranks every number on the card."""
    if pick not in PICKS:
        raise ValueError("the pick is old, new or same")
    if not re.fullmatch(r"proofcard-[0-9-]+", run or "") or brief not in {a["id"] for a in ASKS}:
        raise ValueError("unknown run or brief")
    try:
        allp = json.loads(_pfile().read_text())
    except (OSError, ValueError):
        allp = {}
    allp.setdefault(run, {})[brief] = {"pick": pick, "note": str(note or "")[:300], "at": time.time()}
    _write(_pfile(), allp)
    return allp[run][brief]


def load(name: str = "") -> dict | None:
    fs = cards()
    if name:
        fs = [p for p in fs if p.name == name or p.stem == name or p.name.startswith(name)]
    if not fs:
        return None
    card = json.loads(fs[0].read_text())
    card["file"] = str(fs[0])
    card["picks"] = picks(card.get("run") or "")
    card.update(summarise(card.get("pairs") or [], card["picks"], card.get("planned") or 0,
                          card.get("spent_inr") or 0.0, card.get("budget_inr") or 0.0))
    card["duels"] = duels_of(card)
    card["hash"] = evidence_hash(card)
    return card


def shot_path(run: str, name: str) -> Path | None:
    if not re.fullmatch(r"proofcard-[0-9-]+", run or "") or not re.fullmatch(r"[a-z][0-9]{2}-(old|new)-[0-9]\.jpg", name or ""):
        return None
    f = _dir() / run / name
    return f if f.is_file() else None


# ---------------------------------------------------------------- Arena duels with the new engine's websites
DUEL_PREFIX = "proof:"


def duel(run: str, brief: str, rival: str, rival_url: str, judge_fn=None, shots=None) -> dict[str, Any]:
    """A blind duel in the existing Arena: this brief's NEW-engine website against a public website another builder
    made for the same brief (her rival link). Stored and counted per rival."""
    from ..site import arena as AR
    card = load(run)
    if not card:
        raise ValueError("unknown proof card run")
    p = next((x for x in card.get("pairs") or [] if x["id"] == brief), None)
    site = ((p or {}).get("new") or {}).get("site") or ""
    if not site or not (p or {}).get("new", {}).get("built"):
        raise ValueError("this brief has no website built on the new engine in that run")
    if not re.match(r"^https://", rival_url or ""):
        raise ValueError("the rival's website must be a public https address")
    return AR.duel(DUEL_PREFIX + brief, rival, rival_url, hoola_site=site, judge_fn=judge_fn, shots=shots)


def duels_of(card: dict) -> dict[str, Any]:
    """Win / loss / tie per rival for the duels of this card's new-engine websites."""
    from sqlalchemy import select
    from ..db import session
    from ..site import arena as AR
    sites = {(p.get("new") or {}).get("site") for p in card.get("pairs") or []} - {None, ""}
    out: dict[str, dict[str, Any]] = {}
    if not sites:
        return out
    try:
        AR.ensure_tables()
        with session() as s:
            rows = s.scalars(select(AR.ArenaDuel).where(AR.ArenaDuel.hoola_site.in_(sites))).all()
            for d in rows:
                r = json.loads(d.result or "{}")
                x = out.setdefault(d.rival, {"hoola": 0, "rival": 0, "tie": 0})
                x[r.get("winner", "tie")] = x.get(r.get("winner", "tie"), 0) + 1
    except Exception:                                   # noqa: BLE001 - no duel table yet
        return {}
    for v in out.values():
        n = v["hoola"] + v["rival"] + v["tie"]
        v["duels"], v["win_pct"] = n, round(100 * v["hoola"] / n, 1) if n else None
    return out


def lines(card: dict) -> list[str]:
    out = [f"PROOF CARD (old engine vs new, {card['kind']}, set {card.get('set')})"]
    if card["kind"] == "free":
        out.append(f"  brief set: {card['briefs']} briefs, problems: {card['set_problems'] or 'none'}")
        out.append(f"  calibration: {sum(1 for c in card['calibration'] if c['ok'])}/{len(card['calibration'])} planted cases behave")
        for c in card["calibration"]:
            if not c["ok"]:
                out.append(f"    WRONG: {c['case']}")
        cc = card["critic"]
        out.append(f"  critic: {cc['critic']} - writer {cc['writer']}")
        out.append(f"  {card['live']}")
        out.append(f"  VERDICT: {card['verdict']}")
        return out
    if card.get("running"):
        out.append("  (still running - the pairs finished so far)")
    for eng in ENGINES:
        e = card.get(eng) or {}
        out.append(f"  {eng:3} built {e.get('built')}/{e.get('n')}  ok {e.get('ok')}  design {e.get('design')}  "
                   f"{e.get('median_minutes')} min  Rs {e.get('median_inr')}  blockers {e.get('gate_fails')}  "
                   f"tells {e.get('look_tells')}  LCP {e.get('lcp_ms')} ms")
    c, h = card.get("critic") or {}, card.get("her") or {}
    out.append(f"  critic preferred: new {c.get('new')}, old {c.get('old')}, the same {c.get('same')}; median gain "
               f"{card.get('design_gain_median')}")
    out.append(f"  her picks: new {h.get('new')}, old {h.get('old')}, the same {h.get('same')} ({h.get('picked')} compared)")
    rec = card.get("recommendation") or {}
    out.append(f"  recommendation: {rec.get('say')}" + (f" - {'; '.join(rec.get('why') or [])}" if rec.get("why") else ""))
    out.append(f"  spent Rs {card.get('spent_inr')} of Rs {card.get('budget_inr')}")
    for p in card.get("pairs") or []:
        out.append(f"    {p['id']} old {p['old'].get('design')} new {p['new'].get('design')} -> {p['critic_pick']}")
    return out

"""D0 DESIGN CARD (docs/WEB_DESIGN_ENGINE_PLAN.md phase D0): how good today's Web Studio websites LOOK, measured the
same way every time, so every later design phase (D1-D10) has a number to beat.

40 fixed briefs (design_asks.py: 20 business + 20 not a business) go through the Web Studio's OWN Build path - the
architect's plan, the prototype of every page, then "Build the real website" - on the hidden tenant `__designcard__`
(never her sites, never her budget). Each site is scored on:

  built          the build reached ready with a version
  purpose        the plan named the right kind of site (O1: a wedding is an event, a calculator is a tool - never a business)
  name on home   the name in the brief is on the home page (code reads the built HTML)
  checks         the build's own launch blockers (gate fails) + the AI-look tells (look.py)
  speed          minutes to build, the home page's LCP and first-load KB (the build's own browser check)
  cost           rupees the site's build + its critic call spent (the tenant's own model meter)
  design         a CRITIC from another company than the website writer reads screenshots (home on a computer, the home
                 page down a phone, two more pages) and scores 9 criteria 1-10; the design score = their mean
  her verdict    Good / OK / Bad from the owner page (/console/designcard) - it outranks every number

`ok` on a row means no hard failure (built, right purpose, name on home, no gate fail). The DESIGN score is not a
pass / fail line: it is the baseline the later phases must beat (D5's done-when).

Generated photos are switched OFF for the card process (a paid picture engine; and the score should measure layout and
type, not one picture model). The critic is told so, and `imagery` is left out of the mean while photos are off.

`python -m app.quality design`                        FREE: the brief set is valid, the scorer + the critic reader are
                                                      calibrated on planted cases, which critic would be used.
`python -m app.quality design --live --budget-inr N [--limit 4]`   real builds; stops itself at the rupee budget.
`python -m app.quality design --status`               the newest saved card (also while one runs).
`python -m app.quality design compare <a.json> <b.json>`   metric by metric, the right way round.

Said plainly: the thresholds and the critic's 1-10 scale are judgement, not measured truth - a critic is a model's
opinion; her verdict is the final word. No live card has run when this was written."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from .design_asks import ASKS, SET_V

TENANT = "__designcard__"
GROUPS = {"business": 20, "other": 20}
CRITERIA = ("first_impression", "hierarchy", "typography", "colour", "layout", "imagery", "mobile", "fit", "originality")
CRITERIA_SAY = {
    "first_impression": "the first screen on a computer: does it make you want to stay",
    "hierarchy": "is it obvious what matters most, then next; headings, sizes and weights lead the eye",
    "typography": "font choice and pairing, sizes, line length, spacing between lines and blocks",
    "colour": "a palette that suits THIS project, enough contrast, colour used with purpose",
    "layout": "alignment, rhythm, white space, sections that feel designed and not stacked",
    "imagery": "photos, illustrations, icons: quality and fit (photos may be left out on purpose - then judge the stand-ins)",
    "mobile": "the phone view: readable, nothing cut or squeezed, tap targets, a sensible order",
    "fit": "does it look like what was asked (a wedding feels like a wedding, a game like a game, not a business page)",
    "originality": "does it look made for this project, or like a generic AI template",
}
MAX_TELLS = 4                 # AI-look tells above this = a design warning on the row (a judgement default)
SITE_LIMIT_S = 2700           # one site's build may take this long before the card moves on
IMG_EDGE = 1568               # the longest side a critic image is sent at


class CriticError(Exception):
    pass


# ---------------------------------------------------------------- the set
def set_problems(asks: list[dict] | None = None) -> list[str]:
    from ..site import architect as AR
    asks = asks if asks is not None else ASKS
    out, seen = [], set()
    for a in asks:
        if a["id"] in seen:
            out.append(f"{a['id']}: duplicate id")
        seen.add(a["id"])
        if a.get("group") not in GROUPS or len(a.get("ask") or "") < 80 or not a.get("must") or not a.get("purpose"):
            out.append(f"{a['id']}: group / ask / must / purpose is not valid")
        bad = [p for p in a.get("purpose") or () if p and p not in AR.PURPOSES]
        if bad:
            out.append(f"{a['id']}: purposes the architect does not know: {bad}")
        if a.get("group") == "other" and any(p in ("business", "") for p in a.get("purpose") or ()):
            out.append(f"{a['id']}: a not-a-business brief may not accept a business plan")
        if not all(w.lower() in a["ask"].lower() for w in a.get("must") or []):
            out.append(f"{a['id']}: a must word is not in the ask itself")
    for g, n in GROUPS.items():
        got = sum(1 for a in asks if a.get("group") == g)
        if got != n:
            out.append(f"{g}: {got} briefs, the card wants {n}")
    return out


def pick(limit: int = 0, only: str = "", group: str = "") -> list[dict]:
    """The briefs to run, business and other taking turns (so a budget that runs out leaves both groups the same size)."""
    sel = [a for a in ASKS if (not only or a["id"] in only.split(",")) and (not group or a["group"] == group)]
    biz = [a for a in sel if a["group"] == "business"]
    oth = [a for a in sel if a["group"] == "other"]
    order = [x for pair in zip(biz, oth) for x in pair] + biz[len(oth):] + oth[len(biz):]
    return order[:limit] if limit else order


# ---------------------------------------------------------------- scoring (code, never a model)
def purpose_ok(ask: dict, purpose: str) -> bool:
    return (purpose or "") in tuple(ask.get("purpose") or ())


def design_score(scores: dict[str, int] | None, photos_off: bool) -> float | None:
    if not scores:
        return None
    keys = [k for k in CRITERIA if not (photos_off and k == "imagery")]
    return round(sum(scores[k] for k in keys) / len(keys), 2)


def score_row(ask: dict, run: dict) -> dict[str, Any]:
    reasons: list[str] = []
    built = bool(run.get("built"))
    if not built:
        reasons.append("not built" + (f" ({run['error']})" if run.get("error") else ""))
    purpose = str(run.get("purpose") or "")
    if built and not purpose_ok(ask, purpose):
        reasons.append(f"planned as '{purpose or 'no purpose'}' (wanted {' / '.join(p or 'none' for p in ask['purpose'])})")
    text = (run.get("text") or "").lower()
    missing = [w for w in ask["must"] if w.lower() not in text]
    if built and missing:
        reasons.append("the home page does not show: " + ", ".join(missing))
    if int(run.get("gate_fails") or 0):
        reasons.append(f"{run['gate_fails']} launch blocker(s)")
    warn = []
    if int(run.get("look_tells") or 0) > MAX_TELLS:
        warn.append(f"{run['look_tells']} AI-look tells (over {MAX_TELLS})")
    cr = run.get("critic") or {}
    if built and cr.get("error"):
        warn.append("critic: " + str(cr["error"])[:120])
    return {"id": ask["id"], "group": ask["group"], "ok": not reasons, "reasons": reasons, "warnings": warn, "built": built,
            "purpose": purpose, "kind": run.get("kind") or "", "purpose_ok": built and purpose_ok(ask, purpose),
            "seconds": run.get("seconds"), "inr": run.get("inr"), "critic_inr": cr.get("inr"),
            "gate_fails": int(run.get("gate_fails") or 0), "look_tells": int(run.get("look_tells") or 0),
            "lcp_ms": run.get("lcp_ms"), "first_load_kb": run.get("first_load_kb"),
            "design": cr.get("design"), "scores": cr.get("scores"), "ai_made": cr.get("ai_made"),
            "problems": cr.get("problems") or [], "site": run.get("site") or "", "shots": run.get("shots") or [],
            "skipped": run.get("skipped") or ""}


# ---------------------------------------------------------------- the critic
CRITIC_SYSTEM = (
    "You are a senior web designer reviewing ONE website from screenshots, as a strict design reviewer at a top studio "
    "would. You are told what the person asked for and what the site is for. Score each criterion from 1 to 10: "
    "10 = would win a design award, 8 = excellent professional work, 6 = decent but generic, 4 = amateur, "
    "2 = broken. Be strict and consistent; most sites score between 4 and 8. Do not reward length or decoration. "
    "Judge only what you can see. Reply ONLY with JSON, no other words:\n"
    "{\"scores\": {" + ", ".join(f'"{k}": 1-10' for k in CRITERIA) + "}, "
    "\"looks_ai_made\": true or false, \"problems\": [\"up to 3 short concrete problems, most important first\"]}\n"
    "The criteria:\n" + "\n".join(f"- {k}: {v}" for k, v in CRITERIA_SAY.items()))


def parse_critic(raw: str, photos_off: bool = True) -> dict[str, Any]:
    """The critic's words -> scores. Anything that is not the asked JSON is an ERROR (never a guessed score)."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        raise CriticError("the critic did not answer with JSON")
    try:
        v = json.loads(m.group(0))
    except ValueError as e:
        raise CriticError(f"the critic's JSON did not read: {e}") from None
    sc = v.get("scores") if isinstance(v, dict) else None
    if not isinstance(sc, dict):
        raise CriticError("the critic gave no scores")
    out: dict[str, int] = {}
    for k in CRITERIA:
        x = sc.get(k)
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not 1 <= x <= 10:
            raise CriticError(f"the critic's score for {k} is missing or not 1-10")
        out[k] = int(round(x))
    probs = [str(p)[:200] for p in (v.get("problems") or []) if str(p).strip()][:3]
    return {"scores": out, "design": design_score(out, photos_off), "ai_made": bool(v.get("looks_ai_made")), "problems": probs}


def critic_model() -> str:
    from ..config import get_settings
    st = get_settings()
    return str(getattr(st, "design_card_critic_model", "") or "") or st.anthropic_model


def critic_company() -> dict[str, Any]:
    """The critic must be another company's model than the one writing the website (the plan's rule)."""
    from ..config import get_settings
    st = get_settings()
    writer = str(getattr(st, "web_brain", "") or "claude").lower()
    same = writer in ("claude", "anthropic", "opus")
    return {"writer": "Qwen (Alibaba) via OpenRouter" if writer == "qwen" else writer, "critic": critic_model() + " (Anthropic)",
            "same_company": same,
            "note": "the critic is the same company as the writer - its scores may be kinder" if same else "the critic is another company"}


def _jpeg(img) -> bytes:
    from PIL import Image
    im = img.convert("RGB")
    w, h = im.size
    f = min(1.0, IMG_EDGE / max(w, h))
    if f < 1:
        im = im.resize((max(1, int(w * f)), max(1, int(h * f))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def phone_strip(full: Path, screen_h: int = 844, slices: int = 4):
    """The home page down a phone: up to 4 screens side by side, so a tall page stays readable at the critic's size."""
    from PIL import Image
    im = Image.open(full).convert("RGB")
    w, h = im.size
    n = max(1, min(slices, -(-h // screen_h)))
    gap = 16
    strip = Image.new("RGB", (n * w + (n - 1) * gap, min(h, screen_h)), "white")
    for i in range(n):
        part = im.crop((0, i * screen_h, w, min(h, (i + 1) * screen_h)))
        strip.paste(part, (i * (w + gap), 0))
    return strip


def screenshots(shots: Path, pages: list[str]) -> list[tuple[str, bytes]]:
    """What the critic sees, from the build's own check: home on a computer, the home page down a phone, two more pages."""
    from PIL import Image
    out: list[tuple[str, bytes]] = []
    if (shots / "home-1440.jpg").is_file():
        out.append(("home on a computer (first screen)", _jpeg(Image.open(shots / "home-1440.jpg"))))
    if (shots / "home-390-full.jpg").is_file():
        out.append(("home page on a phone, scrolled down (screens side by side)", _jpeg(phone_strip(shots / "home-390-full.jpg"))))
    elif (shots / "home-390.jpg").is_file():
        out.append(("home on a phone (first screen)", _jpeg(Image.open(shots / "home-390.jpg"))))
    for slug in [p for p in pages if p != "home"][:2]:
        f = shots / f"{slug}-1440.jpg"
        if f.is_file():
            out.append((f"the '{slug}' page on a computer (first screen)", _jpeg(Image.open(f))))
    return out


async def _critic_call(ask: dict, purpose: str, images: list[tuple[str, bytes]], photos_off: bool) -> str:
    from .. import glmdoor
    from .. import usage as U
    from ..agent.santosh import get_client
    note = (" Generated photos were switched off for this test on purpose: judge the photo stand-ins only for placement."
            if photos_off else "")
    content: list[dict[str, Any]] = [{"type": "text", "text": f"What the person asked for:\n{ask['ask']}\n\nWhat the site is for: "
                                      f"{purpose or 'not stated'}.{note}\n\nThe screenshots follow, each named."}]
    for name, data in images:
        content.append({"type": "text", "text": name + ":"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(data).decode()}})
    content.append({"type": "text", "text": "Score the website now. JSON only."})
    a, b = glmdoor.CLAUDE_ONLY.set(True), U.ONE_MODEL_BYPASS.set(True)   # the critic is Claude itself: no door swaps it
    try:
        resp = await asyncio.wait_for(get_client().messages.create(
            model=critic_model(), max_tokens=700, system=CRITIC_SYSTEM,
            messages=[{"role": "user", "content": content}]), timeout=180)
    finally:
        glmdoor.CLAUDE_ONLY.reset(a)
        U.ONE_MODEL_BYPASS.reset(b)
    return "".join(str(x.get("text") if isinstance(x, dict) else getattr(x, "text", "")) for x in resp.content)


def critic(ask: dict, purpose: str, images: list[tuple[str, bytes]], photos_off: bool = True, call=None) -> dict[str, Any]:
    """One critic call for one site (tried twice). Never raises: a failure is an `error` on the row, never a score."""
    if not images:
        return {"error": "no screenshots from the build's check"}
    from ..usage import scope
    call = call or _critic_call
    last = ""
    inr0 = _spent()
    for _ in range(2):
        try:
            with scope(TENANT, "designcard"):
                raw = asyncio.run(call(ask, purpose, images, photos_off))
            return {**parse_critic(raw, photos_off), "inr": round(_spent() - inr0, 2), "images": len(images)}
        except CriticError as e:
            last = str(e)
        except Exception as e:                              # noqa: BLE001 - the row says why, the card goes on
            last = f"{type(e).__name__}: {e}"[:200]
    return {"error": last, "inr": round(_spent() - inr0, 2)}


# ---------------------------------------------------------------- calibration (free)
def _good(ask: dict) -> dict:
    return {"built": True, "seconds": 600, "inr": 20.0, "purpose": ask["purpose"][0], "kind": "brochure",
            "text": " ".join(ask["must"]) + " welcome", "gate_fails": 0, "look_tells": 1,
            "critic": {"scores": {k: 7 for k in CRITERIA}, "design": 7.0, "ai_made": False, "problems": [], "inr": 1.0}}


def calibration() -> list[dict]:
    """Planted cases: each must behave for its OWN reason; a clean run passes."""
    biz = next(a for a in ASKS if a["group"] == "business")
    wed = next(a for a in ASKS if a["id"] == "o04")
    cases = [("clean business run passes", biz, _good(biz), True, ""),
             ("clean wedding run passes", wed, _good(wed), True, "")]
    for name, ask, mut, why in (("not built", biz, {"built": False, "error": "prototype failed"}, "not built"),
                                ("a wedding planned as a business", wed, {"purpose": "business"}, "planned as"),
                                ("a wedding with no purpose named", wed, {"purpose": ""}, "planned as"),
                                ("the home page lacks the name", biz, {"text": "nothing useful here"}, "does not show"),
                                ("a launch blocker", biz, {"gate_fails": 2}, "launch blocker")):
        cases.append((name, ask, {**_good(ask), **mut}, False, why))
    out = []
    for name, ask, run, want, why in cases:
        s = score_row(ask, run)
        out.append({"case": name, "ok": s["ok"] == want and (want or any(why in r for r in s["reasons"])), "reasons": s["reasons"]})
    full = json.dumps({"scores": {k: 6 for k in CRITERIA}, "looks_ai_made": True, "problems": ["flat hero", "tiny text"]})
    reads = [("critic JSON reads", "Here it is:\n```json\n" + full + "\n```", True),
             ("a score of 11 is refused", full.replace('"fit": 6', '"fit": 11'), False),
             ("a missing criterion is refused", json.dumps({"scores": {k: 6 for k in CRITERIA[:-1]}}), False),
             ("words with no JSON are refused", "The site looks lovely, I would give it an 8.", False),
             ("true as a score is refused", full.replace('"mobile": 6', '"mobile": true'), False)]
    for name, raw, want in reads:
        try:
            got = parse_critic(raw, True)
            ok = want and got["design"] == 6.0 and got["ai_made"] is True and len(got["problems"]) == 2
        except CriticError:
            ok = not want
        out.append({"case": name, "ok": ok, "reasons": []})
    sc = {k: 8 for k in CRITERIA}
    sc["imagery"] = 1
    out.append({"case": "imagery left out while photos are off", "ok": design_score(sc, True) == 8.0 and design_score(sc, False) < 8.0,
                "reasons": []})
    return out


# ---------------------------------------------------------------- summarise / compare
def _med(xs: list[Any]) -> float | None:
    xs = [float(x) for x in xs if isinstance(x, (int, float))]
    return round(statistics.median(xs), 2) if xs else None


def summarise(rows: list[dict], kind: str = "live", planned: int = 0, spent: float = 0.0, budget: float = 0.0,
              verdicts: dict[str, dict] | None = None) -> dict[str, Any]:
    verdicts = verdicts or {}
    ran = [r for r in rows if not r.get("skipped")]
    out: dict[str, Any] = {"kind": kind, "set": SET_V, "briefs": len(rows), "ran": len(ran), "planned": planned or len(rows),
                           "spent_inr": round(spent, 2), "budget_inr": budget}
    for g in ("business", "other", "all"):
        sel = [r for r in ran if g == "all" or r["group"] == g]
        built = [r for r in sel if r["built"]]
        vs = [verdicts[r["id"]]["verdict"] for r in sel if r["id"] in verdicts]
        out[g] = {"n": len(sel), "built": len(built), "ok": sum(1 for r in sel if r["ok"]),
                  "purpose_ok": sum(1 for r in sel if r["purpose_ok"]),
                  "design": _med([r["design"] for r in built]), "design_n": sum(1 for r in built if r["design"] is not None),
                  "ai_made": sum(1 for r in built if r.get("ai_made")),
                  "median_minutes": _med([r["seconds"] / 60 for r in built if r.get("seconds")]),
                  "median_inr": _med([r["inr"] for r in built]), "gate_fails": sum(r["gate_fails"] for r in sel),
                  "look_tells": _med([r["look_tells"] for r in built]), "lcp_ms": _med([r["lcp_ms"] for r in built]),
                  "her_good": vs.count("good"), "her_ok": vs.count("ok"), "her_bad": vs.count("bad")}
        for k in CRITERIA:
            out[g]["c_" + k] = _med([(r.get("scores") or {}).get(k) for r in built])
    return out


HIGHER_BETTER = {"built", "ok", "purpose_ok", "design", "her_good"} | {"c_" + k for k in CRITERIA}
LOWER_BETTER = {"ai_made", "median_minutes", "median_inr", "gate_fails", "look_tells", "lcp_ms", "her_bad"}


def compare(a: dict, b: dict) -> list[dict]:
    if a.get("set") and b.get("set") and a["set"] != b["set"]:
        return [{"group": "all", "metric": "set", "before": a["set"], "after": b["set"], "verdict": "different brief sets - not comparable"}]
    out = []
    for g in ("business", "other", "all"):
        for k, va in (a.get(g) or {}).items():
            vb = (b.get(g) or {}).get(k)
            if k not in HIGHER_BETTER | LOWER_BETTER or va is None or vb is None:
                continue
            better = (vb < va) if k in LOWER_BETTER else (vb > va)
            out.append({"group": g, "metric": k, "before": va, "after": vb, "verdict": "same" if va == vb else "better" if better else "worse"})
    return out


# ---------------------------------------------------------------- the free card
def free_card(asks: list[dict] | None = None) -> dict[str, Any]:
    asks = asks if asks is not None else ASKS
    cal = calibration()
    probs = set_problems(asks)
    card: dict[str, Any] = {"kind": "free", "set": SET_V, "briefs": len(asks), "set_problems": probs, "calibration": cal,
                            "calibration_ok": all(c["ok"] for c in cal), "critic": critic_company(),
                            "live": "not run here: the live card builds real websites (model calls, Chromium) - "
                                    "python -m app.quality design --live --budget-inr N [--limit 4]"}
    card["verdict"] = "PASS" if not probs and card["calibration_ok"] else "FAIL"
    return card


# ---------------------------------------------------------------- the live card
def _spent() -> float:
    from .. import usage as U
    U.flush()
    return U.month_usd(TENANT) * U.usd_inr()


def _strip(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _drive(site_id: str, limit_s: int = SITE_LIMIT_S, sleep_s: float = 3.0) -> str:
    """Walk one site like an owner: when the prototype is ready, tap 'Build the real website'; with the 3 looks (prototype
    switched off) take look 1; wait for ready. Returns the last status."""
    from ..site import prototype as PT
    from ..site import service as S
    t0, tapped = time.time(), False
    while time.time() - t0 < limit_s:
        r = S._load(site_id)
        if r.status in ("ready", "failed", "stopped") and not S.busy(site_id):
            return r.status
        if not S.busy(site_id) and not tapped:
            if r.status == "prototype" and PT.meta(r).get("status") == "ready" and PT.meta(r).get("hash"):
                PT.approve(TENANT, site_id, PT.meta(r)["hash"])
                tapped = True
            elif r.status == "looks" and S._j(r.looks, []):
                S.choose_look(TENANT, site_id, 0)
                tapped = True
        time.sleep(sleep_s)
    return "timeout"


def _purpose_of(r, v: dict) -> tuple[str, str]:
    from ..site import service as S
    spec = (S._j(r.plan, {}) or {}).get("spec") or {}
    purpose, kind = str(spec.get("purpose") or ""), str(spec.get("kind") or "")
    if not purpose and v.get("spec"):
        try:
            from ..site import architect as AR
            c = AR.card(TENANT, str(v["spec"]))
            purpose, kind = str(c.get("purpose") or ""), kind or str(c.get("kind") or "")
        except Exception:                                   # noqa: BLE001 - the row says no purpose
            pass
    return purpose, kind


def run_one(ask: dict, run_dir: Path, critic_on: bool = True, photos_off: bool = True,
            limit_s: int = SITE_LIMIT_S) -> dict[str, Any]:
    """One brief through the Web Studio's Build path, then the critic."""
    from ..site import architect as AR
    from ..site import build as B
    from ..site import look as LK
    from ..site import service as S
    t0, inr0 = time.time(), _spent()
    out: dict[str, Any] = {"built": False, "gate_fails": 0, "look_tells": 0, "text": ""}
    v = AR.build_now(TENANT, ask["ask"], "", "", None, True)
    sid = str(v.get("id") or "")
    if not sid:
        out["error"] = "the Studio started no site" + (" (it asked questions)" if v.get("questions") else "")
        out["seconds"], out["inr"] = round(time.time() - t0, 1), round(_spent() - inr0, 2)
        return out
    status = _drive(sid, limit_s)
    r = S._load(sid)
    out.update(site=sid, status=status, built=r.status == "ready" and bool(r.version),
               seconds=round(time.time() - t0, 1))
    if not out["built"]:
        out["error"] = (r.error or status or "")[:240]
    out["purpose"], out["kind"] = _purpose_of(r, v)
    chk = S._j(r.checks, {}) or {}
    sc = chk.get("scores") or {}
    out.update(gate_fails=len(chk.get("blocking") or []), lcp_ms=sc.get("lcp_ms"), first_load_kb=sc.get("first_load_kb"))
    if out["built"]:
        dist = B.out_dir(TENANT, sid, r.version)
        try:
            out["text"] = _strip((dist / "index.html").read_text("utf-8", "replace"))
        except OSError:
            out["text"] = ""
        try:
            out["look_tells"] = int(LK.scan(dist, S._ctx(r)).get("count") or 0)
        except Exception:                                   # noqa: BLE001
            out["look_tells"] = 0
        pages = [p.get("slug") for p in (S._j(r.plan, {}) or {}).get("pages") or [] if p.get("slug")]
        imgs = screenshots(B.site_dir(TENANT, sid) / "shots" / "live", pages)
        names = []
        for i, (name, data) in enumerate(imgs):
            fn = f"{ask['id']}-{i + 1}.jpg"
            (run_dir / fn).write_bytes(data)
            names.append({"file": fn, "what": name})
        out["shots"] = names
        out["inr"] = round(_spent() - inr0, 2)
        if critic_on:
            out["critic"] = critic(ask, out["purpose"], imgs, photos_off)
    out["inr"] = round(_spent() - inr0, 2)
    return out


def live_card(items: list[dict] | None = None, budget_inr: float = 0.0, runner=None, critic_on: bool = True,
              photos_off: bool = True, label: str = "") -> dict[str, Any]:
    """The real run: one brief at a time, business and other taking turns, stops itself at the budget. Saved after every
    site, so --status shows a run while it goes."""
    from ..config import get_settings
    from ..main import APP_VERSION
    items = items if items is not None else pick()
    if budget_inr <= 0:
        raise ValueError("a live design card needs --budget-inr N (the rupees for the whole run)")
    st = get_settings()
    old_photos = getattr(st, "site_ai_photos", 6)
    if photos_off:
        try:
            setattr(st, "site_ai_photos", 0)                # this process only (the card's own builds); the server is untouched
        except Exception:                                   # noqa: BLE001
            pass
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = _dir() / f"designcard-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    card: dict[str, Any] = {"kind": "live", "set": SET_V, "version": APP_VERSION, "at": time.time(), "run": run_dir.name,
                            "photos_off": photos_off, "critic": critic_company(), "running": True, "rows": []}
    path = _dir() / f"{run_dir.name}{('-' + re.sub(r'[^A-Za-z0-9_-]', '', label)) if label else ''}.json"
    spent0 = _spent()
    runner = runner or (lambda a: run_one(a, run_dir, critic_on, photos_off))
    try:
        for a in items:
            if _spent() - spent0 >= budget_inr:
                card["rows"].append(score_row(a, {"skipped": f"budget Rs {budget_inr} used"}) | {"skipped": "budget used", "ok": False})
                continue
            try:
                run = runner(a)
            except Exception as e:                          # noqa: BLE001 - one broken brief is a row
                run = {"built": False, "error": f"{type(e).__name__}: {e}"[:240]}
            card["rows"].append(score_row(a, run))
            card.update(summarise(card["rows"], "live", len(items), _spent() - spent0, budget_inr))
            _write(path, card)
    finally:
        if photos_off:
            try:
                setattr(st, "site_ai_photos", old_photos)
            except Exception:                               # noqa: BLE001
                pass
    card.update(summarise(card["rows"], "live", len(items), _spent() - spent0, budget_inr))
    card["running"] = False
    card["file"] = str(path)
    _write(path, card)
    return card


# ---------------------------------------------------------------- files, her verdicts, printing
def _dir() -> Path:
    from ..config import get_settings
    d = Path(getattr(get_settings(), "data_dir", "") or "data") / "quality"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, card: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(card, indent=1, ensure_ascii=False))
    tmp.replace(path)


def save(card: dict, label: str = "") -> dict:
    f = _dir() / f"designcard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}{('-' + re.sub(r'[^A-Za-z0-9_-]', '', label)) if label else ''}.json"
    card["file"] = str(f)
    _write(f, card)
    return card


def cards() -> list[Path]:
    """The saved LIVE cards, newest first (never the free checks or her verdicts file)."""
    return sorted((p for p in _dir().glob("designcard-*.json") if re.fullmatch(r"designcard-\d{8}-\d{6}(-[A-Za-z0-9_-]+)?", p.stem)),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def load(name: str = "") -> dict | None:
    fs = cards()
    if name:
        fs = [p for p in fs if p.name == name or p.stem == name or p.name.startswith(name)]
    if not fs:
        return None
    card = json.loads(fs[0].read_text())
    card["file"] = str(fs[0])
    card["verdicts"] = verdicts(card.get("run") or "")
    card.update(summarise(card.get("rows") or [], card.get("kind", "live"), card.get("planned") or 0,
                          card.get("spent_inr") or 0.0, card.get("budget_inr") or 0.0, card["verdicts"]))
    return card


VERDICTS = ("good", "ok", "bad")


def _vfile() -> Path:
    return _dir() / "designcard-verdicts.json"


def verdicts(run: str) -> dict[str, dict]:
    try:
        allv = json.loads(_vfile().read_text())
    except (OSError, ValueError):
        allv = {}
    return dict(allv.get(run) or {})


def set_verdict(run: str, brief: str, verdict: str, note: str = "") -> dict[str, Any]:
    """Her word on one site of one run. It outranks every number on the card."""
    if verdict not in VERDICTS:
        raise ValueError("the verdict is good, ok or bad")
    if not re.fullmatch(r"designcard-[0-9-]+", run or "") or brief not in {a["id"] for a in ASKS}:
        raise ValueError("unknown run or brief")
    try:
        allv = json.loads(_vfile().read_text())
    except (OSError, ValueError):
        allv = {}
    allv.setdefault(run, {})[brief] = {"verdict": verdict, "note": str(note or "")[:300], "at": time.time()}
    _write(_vfile(), allv)
    return allv[run][brief]


def shot_path(run: str, name: str) -> Path | None:
    if not re.fullmatch(r"designcard-[0-9-]+", run or "") or not re.fullmatch(r"[a-z][0-9]{2}-[0-9]\.jpg", name or ""):
        return None
    f = _dir() / run / name
    return f if f.is_file() else None


def lines(card: dict) -> list[str]:
    out = [f"DESIGN CARD ({card['kind']}, set {card.get('set')})"]
    if card["kind"] == "free":
        out.append(f"  brief set: {card['briefs']} briefs, problems: {card['set_problems'] or 'none'}")
        out.append(f"  calibration: {sum(1 for c in card['calibration'] if c['ok'])}/{len(card['calibration'])} planted cases behave")
        for c in card["calibration"]:
            if not c["ok"]:
                out.append(f"    WRONG: {c['case']} {c['reasons']}")
        cc = card["critic"]
        out.append(f"  critic: {cc['critic']} - writer {cc['writer']} - {cc['note']}")
        out.append(f"  {card['live']}")
        out.append(f"  VERDICT: {card['verdict']}")
        return out
    if card.get("running"):
        out.append("  (still running - these are the sites finished so far)")
    for g in ("business", "other", "all"):
        e = card.get(g) or {}
        if not e:
            continue
        out.append(f"  {g:8} built {e['built']}/{e['n']}  ok {e['ok']}  right purpose {e['purpose_ok']}  design {e['design']} "
                   f"({e['design_n']} judged)  looks AI-made {e['ai_made']}  {e['median_minutes']} min  Rs {e['median_inr']}  "
                   f"blockers {e['gate_fails']}  tells {e['look_tells']}  LCP {e['lcp_ms']} ms  her good/ok/bad "
                   f"{e['her_good']}/{e['her_ok']}/{e['her_bad']}")
    out.append(f"  spent Rs {card.get('spent_inr')} of Rs {card.get('budget_inr')}; ran {card.get('ran')} of {card.get('planned')}")
    for r in card.get("rows") or []:
        why = "; ".join(r["reasons"] + r.get("warnings", [])) or "ok"
        out.append(f"    {r['id']} {'OK ' if r['ok'] else 'NO '} design {r.get('design')}  {r.get('purpose') or '-'}  {why[:150]}")
    return out

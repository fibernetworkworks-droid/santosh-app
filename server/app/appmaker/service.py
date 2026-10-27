"""v0.128 App Sahayak, part 1: every screen of her native app designed and previewed BEFORE any app is built.

Flow (one state machine; her taps in CAPS):
  brief (her few words) -> library match (1 lakh app briefs) + what Hoola already knows (brand kit, business profile,
  stock list, timings) -> PLAN card (screens, tabs, main flow, code-made legal screens, store rules, up to 3 questions) ->
  HAAN -> 3 LOOKS (Opus designs the Home screen in 3 styles; real Android screenshots) -> SHE CHOOSES -> Opus designs every
  screen by hand inside the Hoola app kit, each one sanitised and put into the clickable prototype at once; the live board
  shows a tile per screen with its screenshot -> checks in real Chromium on Android + iPhone looks (overflow at 360 px,
  contrast, tap targets, labels, dead links, card / PIN fields) -> Opus fixes what failed (2 rounds) -> screenshots of
  every screen on both platforms + one 'all screens' sheet + the tap-through prototype link -> changes in her words ->
  DESIGN PAKKA (her tap; the design is frozen by a hash and becomes the contract the native Kotlin / SwiftUI build of the
  next version follows). Rokiye stops after the current screen.
Never: invented facts (blanks instead), card / CVV / UPI PIN / password fields, other brands' logos, look-alike apps,
anything public or paid (store accounts and publishing come later, each behind her tap)."""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from ..site import build as SB
from ..site import library as SL
from . import ai as AI
from . import artdirect as AD
from . import blueprint as BP
from . import kit as K
from . import library as L
from . import products as PR
from . import taxonomy as T
from .models import AppProject

log = logging.getLogger("santosh.app")

STAGES = [("brief", "Baat"), ("plan", "Plan"), ("look", "Look"), ("design", "Screens"), ("checks", "Jaanch"),
          ("preview", "Preview"), ("pakka", "Design pakka"), ("android", "Android app"), ("ios", "iPhone app"), ("store", "Store")]
MAX_FIX_ROUNDS = 2
STATS = {"off_topic": 0, "asked_first": 0, "not_her_business": 0, "art": 0, "art_retry": 0, "art_fallback": 0,
         "critiques": 0, "refined": 0, "critique_gain": 0.0}
_RUNNING: dict[str, threading.Thread] = {}
_LOCK = threading.Lock()


class AppError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (ValueError, TypeError):
        return default


def _jd(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _tidy(s: Any, n: int = 300) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


def _settings():
    from ..config import get_settings
    return get_settings()


def _inline() -> bool:
    return os.environ.get("APP_WORKER", "true").lower() in ("0", "false", "off", "inline")


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("app publish failed")


def _work(r: AppProject, phase: str, label: str, note: str = "", items: list | None = None) -> None:
    data: dict[str, Any] = {"site": r.name or "App", "note": _tidy(note, 90), "url": preview_url(r, short=True)}
    if items is not None:
        data["sections"] = items[:8]
    _publish(r.tenant_id, "work", {"id": f"app-{r.id}", "tool": "app_banao", "scene": "website", "phase": phase,
                                   "label": _tidy(label, 60), "data": data}, r.conv)


def _number(s, tenant: str) -> str:
    n = s.scalar(select(func.count()).select_from(AppProject).where(AppProject.tenant_id == tenant)) or 0
    return f"A-{n + 1:04d}"


def _find(s, tenant: str, ref: str) -> AppProject:
    ref = (ref or "").strip()
    q = select(AppProject).where(AppProject.tenant_id == tenant)
    if not ref:
        r = s.scalars(q.order_by(AppProject.updated_at.desc())).first()
    else:
        r = s.scalars(q.where((AppProject.id == ref) | (AppProject.number == ref.upper()) |
                              (AppProject.number == f"A-{ref.zfill(4)}"))).first()
        if r is None:
            r = s.scalars(q.where(AppProject.name.ilike(f"%{ref}%")).order_by(AppProject.updated_at.desc())).first()
    if r is None:
        raise AppError("Yeh app nahi mili." if ref else "Abhi koi app nahi hai. 'meri dukaan ki app banao' kahiye.")
    return r


def _load(app_id: str) -> AppProject:
    with session() as s:
        r = s.get(AppProject, app_id)
        if r is None:
            raise AppError("app gone")
        s.expunge(r)
        return r


def _save(app_id: str, **fields) -> AppProject:
    with session() as s:
        r = s.get(AppProject, app_id)
        for k, v in fields.items():
            setattr(r, k, _jd(v) if isinstance(v, (dict, list)) else v)
        r.updated_at = now()
        s.flush()
        s.expunge(r)
        return r


# ---------------------------------------------------------------- whose app is it? (v0.138)
# Before v0.138 her OWN business (brand kit, business profile, Kalam facts, stock) went into every app: an ISP owner asking
# for "Spotify jaisa music app" got ISP screens. Her business details now go in ONLY when the app is for her business.
OWN_RE = re.compile(
    r"(?:^|\s)(?:my|our|mera|meri|mere|hamara|hamari|hamare|apna|apni|apne|मेरा|मेरी|मेरे|हमारा|हमारी|हमारे|अपना|अपनी|अपने|"
    r"माझा|माझी|माझे|माझ्या|आमचा|आमची|आमचे|आमच्या)\s+(?:\S+\s+){0,2}?(?:dukaan|dukan|shop|business|bussiness|company|firm|store|"
    r"clinic|office|isp|network|restaurant|hotel|salon|gym|school|coaching|brand|cable|broadband|agency|startup|showroom|"
    r"factory|institute|classes|hospital|courier|fiber|fibre|kaam|dhandha|vyapar|दुकान|दुकाना|व्यवसाय|कंपनी|बिज़नेस|बिजनेस|ऑफिस|धंधा)"
    r"(?![a-z])")
OTHER_RE = re.compile(r"\b(?:client|clients|kisi aur|kisi ke liye|dusre ke|doosre ke|dost ke liye|for a customer|for someone|"
                      r"for my client|customer ke liye bana|graahak ke liye bana)\b")
_GENERIC = {"app", "apps", "shop", "store", "online", "india", "services", "service", "centre", "center", "dukaan", "business",
            "company", "agency", "connection", "office", "home", "delivery", "booking", "app banao", "streaming"}


def _her_business(tenant: str) -> tuple[str, str]:
    """(her business name, words about what it does) from her profile / brand kit / Kalam settings."""
    name, bits = "", []
    try:
        from ..employee.models import EmployeeProfile
        with session() as s:
            p = s.get(EmployeeProfile, tenant)
            if p:
                name = p.business_name or ""
                bits += [p.business_name or "", p.business_kind or "", p.preset or "", (p.about or "")[:400]]
    except Exception:
        log.debug("no employee profile", exc_info=True)
    try:
        from ..brand.service import kit
        k = kit(tenant)
        name = name or k.get("name") or ""
        bits += [k.get("name") or "", k.get("tagline") or ""]
    except Exception:
        log.debug("no brand kit", exc_info=True)
    try:
        from ..kalam.service import KalamSettings
        with session() as s:
            k2 = s.get(KalamSettings, tenant)
            if k2:
                name = name or k2.business or ""
                bits += [k2.business or "", (k2.about or "")[:300]]
    except Exception:
        log.debug("no kalam settings", exc_info=True)
    return name.strip(), " ".join(b for b in bits if b).strip()


def whose_app(tenant: str, brief: str, fid: str) -> dict[str, Any]:
    """{own: her own business's app?, why, her_name, avoid: words of her other business that must not appear}."""
    t = " " + re.sub(r"\s+", " ", (brief or "").lower()) + " "
    her_name, about = _her_business(tenant)
    F = L.fields()
    out = {"own": False, "why": "", "her_name": her_name, "avoid": []}
    if OTHER_RE.search(t):
        out["why"] = "kisi aur ke liye"
    elif her_name and len(her_name) >= 3 and her_name.lower() in t:
        out.update(own=True, why="aapka naam")
    elif OWN_RE.search(t):
        out.update(own=True, why="aapne 'mera / meri' kaha")
    elif PR.pid_of(fid):
        out["why"] = "alag product app"
    elif not about:
        out.update(own=True, why="koi aur business pata nahi")
    else:
        mine = SL.match(about, top=3) if about else []
        ind = (F.get(fid) or {}).get("industry")
        if any(F[m["id"]]["industry"] == ind for m in mine if m["id"] in F):
            out.update(own=True, why="aapka hi kaam")
        else:
            out["why"] = "aapke business se alag kaam"
    if not out["own"] and about:
        mine = SL.match(about, top=2)
        words = [her_name] if len(her_name) >= 3 else []
        for m in mine:
            fm = F.get(m["id"]) or {}
            words += [a for a in fm.get("aliases", []) if len(a) >= 3]
        own_words = " ".join([brief or "", (F.get(fid) or {}).get("en", ""), " ".join((F.get(fid) or {}).get("aliases", []))]).lower()
        out["avoid"] = [w for w in dict.fromkeys(words) if w and w.lower() not in own_words and w.lower() not in _GENERIC][:12]
    return out


# ---------------------------------------------------------------- facts (same sources as the website + appointments)
def gather_facts(tenant: str, brief: str = "", own: bool = True) -> dict[str, Any]:
    from ..site import service as SS
    if not own:      # someone else's / a product app: only what her words say (+ her app language)
        f = {"registrations": {}, **SS.facts_from_text(brief)}
        try:
            from ..brand.service import kit
            lang = kit(tenant).get("language") or ""
            if lang:
                f["language"] = lang
        except Exception:
            log.debug("no brand kit", exc_info=True)
        return {k: v for k, v in f.items() if v not in (None, "", [], {})} | {"registrations": f.get("registrations") or {}}
    f = SS.gather_facts(tenant, brief)
    try:
        from ..employee.models import EmployeeProfile
        with session() as s:
            p = s.get(EmployeeProfile, tenant)
            if p and getattr(p, "upi_id", ""):
                f["upi_id"] = p.upi_id
    except Exception:
        log.debug("no upi id", exc_info=True)
    return f


def _goal_fits(goal: str, brief: str, fid: str, u: dict[str, Any]) -> bool:
    """A goal the chat model passed is used only when her words back it (it once kept sending her own trade's archetype)."""
    gg = T.GOALS.get(goal) or {}
    if not gg:
        return False
    if u.get("product"):
        return goal == u["goal"]
    t = " " + L._norm(brief) + " "
    said = any(f" {L._norm(w)} " in t for w in gg.get("words", []))
    if gg.get("product"):
        pm = PR.match(brief)
        return bool(pm) and pm["id"] == goal
    if gg.get("complex"):
        return said or (L.fields().get(fid) or {}).get("industry") in (gg.get("industries") or [])
    return True


def _lang_of(facts: dict[str, Any], brief: str) -> str:
    lang = {"hinglish": "hinglish", "hindi": "hi", "hi": "hi", "marathi": "mr", "mr": "mr", "english": "en",
            "en": "en"}.get((facts.get("language") or "").lower(), "en")
    if re.search(r"[ऀ-ॿ]", brief or ""):
        lang = "mr" if re.search(r"(आहे|साठी|माझ|बनवा|हवी|हवे)", brief) else "hi"
    return lang


def missing_questions(facts: dict[str, Any], br: dict[str, Any]) -> list[str]:
    q: list[str] = []
    if br.get("product"):        # a product app: its name and where its content comes from, not a shop's phone number
        for x in br.get("questions", []):
            if facts.get("name") and "naam" in x.lower():
                continue
            q.append(x)
        return q[:3]
    if not facts.get("name"):
        q.append("App kis naam se hogi (business / dukaan ka naam)?")
    if not (facts.get("phone") or facts.get("whatsapp")):
        q.append("Customer kis number par call / WhatsApp karein?")
    if br.get("money") and not facts.get("upi_id"):
        q.append("Payment kis UPI ID par aayega? (sirf UPI ID, PIN kabhi nahi)")
    for x in br.get("questions", []):
        if len(q) >= 3:
            break
        low = x.lower()
        if facts.get("name") and "naam" in low and not any(w in low for w in ("item", "service", "course", "brand", "doctor")):
            continue
        if x not in q:
            q.append(x)
    return q[:3]


# ---------------------------------------------------------------- the plan (code, from the library brief)
def make_plan(br: dict[str, Any], lang: str, words: str = "") -> dict[str, Any]:
    labels = {s: (T.SCREENS[s]["hi"].capitalize() if lang in ("hinglish",) else T.SCREENS[s]["label"]) for s in br["screens"]}
    labels.update({s: T.CODE_SCREENS[s]["label"] for s in br["code_screens"]})
    tabs = [t for t in br["tabs"] if t in br["screens"]]
    start = "home" if "home" in br["screens"] else (tabs[0] if tabs else br["screens"][0])
    return {"brief_id": br["id"], "screens": list(br["screens"]), "tabs": tabs,
            "flow": [s for s in br["flow"] if s in br["screens"]], "code_screens": list(br["code_screens"]),
            "designs": dict(br["designs"]), "labels": labels, "rules": list(br["rules"]), "legal": list(br["legal"]),
            "start": start, "accounts": br["accounts"], "money": br["money"], "complex": bool(br.get("complex")),
            "blueprint": BP.make(br["goal"], list(br["screens"]), words)}


def _board(r: AppProject, plan: dict[str, Any] | None = None, states: dict[str, str] | None = None, now_line: str = "",
           shots: dict[str, str] | None = None) -> dict[str, Any]:
    plan = plan or _j(r.plan, {})
    old = _j(r.board, {})
    st = dict(old.get("states") or {})
    st.update(states or {})
    th = dict(old.get("thumbs") or {})
    th.update(shots or {})
    labels = plan.get("labels") or {}
    groups = [("Tabs", [s for s in plan.get("screens", []) if s in plan.get("tabs", [])]),
              ("Baaki screens", [s for s in plan.get("screens", []) if s not in plan.get("tabs", [])]),
              ("Code se (kanoon + system)", list(plan.get("code_screens", [])))]
    pages, total, done = [], 0, 0
    for title, ids in groups:
        if not ids:
            continue
        secs = []
        for sid in ids:
            state = "done" if sid in T.CODE_SCREENS and st.get(sid) != "todo" else st.get(sid, "todo")
            total += 1
            done += state == "done"
            secs.append({"key": sid, "type": sid, "label": labels.get(sid) or sid, "state": state, "thumb": th.get(sid, "")})
        pages.append({"slug": title.split()[0].lower(), "title": title, "sections": secs})
    return {"states": st, "thumbs": th, "pages": pages, "now": now_line or old.get("now", ""),
            "pct": round(100 * done / total) if total else 0, "total": total, "done": done,
            "overview": old.get("overview") or {}, "scores": old.get("scores") or {}}


def preview_url(r: AppProject, short: bool = False) -> str:
    if not r.preview_token:
        return ""
    base = (_settings().public_base_url or "").rstrip("/")
    path = f"/api/app-preview/{r.preview_token}/"
    return path if short and not base else f"{base}{path}"


def _model_label() -> str:
    from ..site import ai as SA
    return SA.app_model_label()


def _art_view(dna: dict[str, Any] | None) -> dict[str, Any]:
    """The design DNA in a few lines for the app (concept, idea, signature, layout, 3D)."""
    if not dna:
        return {}
    lay = dna.get("layout") or {}
    td = dna.get("three_d") or {}
    return {"concept": dna.get("concept", ""), "idea": dna.get("idea", ""), "signature": dna.get("signature", ""),
            "layout": AD.LAYOUTS.get(lay.get("system"), lay.get("system") or ""), "hero": AD.HEROES.get(lay.get("hero"), ""),
            "motion": (dna.get("motion") or {}).get("language", ""), "three_d": bool(td.get("use")),
            "scenes": list((td.get("scenes") or {}).keys()), "by": dna.get("by", "")}


def view(r: AppProject, full: bool = True) -> dict[str, Any]:
    board = _j(r.board, {})
    plan = _j(r.plan, {})
    v = {"id": r.id, "number": r.number, "name": r.name, "status": r.status, "stage": r.stage, "field": r.field,
         "field_label": (L.fields().get(r.field) or {}).get("en", ""), "goal": r.goal,
         "goal_label": (T.GOALS.get(r.goal) or {}).get("label", ""), "style": r.style,
         "style_label": (T.STYLES.get(r.style) or {}).get("label", ""), "version": r.version,
         "stages": [{"id": a, "label": b} for a, b in STAGES],
         "board": {k: board.get(k) for k in ("pages", "now", "pct", "total", "done", "overview", "extras", "er", "scores")},
         "preview": preview_url(r), "error": r.error, "queued": len(_j(r.queued, [])), "language": r.language,
         "approved": bool(r.approved_hash), "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "model": _model_label(), "art": _art_view(plan.get("art"))}
    if full:
        checks = _j(r.checks, {})
        v.update({"brief": r.brief, "plan": {"screens": [{"id": s, "label": (plan.get("labels") or {}).get(s, s),
                                                          "design": (plan.get("designs") or {}).get(s, ""),
                                                          "tab": s in plan.get("tabs", [])} for s in plan.get("screens", [])],
                                             "tabs": plan.get("tabs", []), "flow": plan.get("flow", []),
                                             "code_screens": [{"id": s, "label": T.CODE_SCREENS[s]["label"],
                                                               "why": T.CODE_SCREENS[s]["why"]} for s in plan.get("code_screens", [])],
                                             "rules": plan.get("rules", [])[:8], "complex": bool(plan.get("complex")),
                                             "blueprint": BP.view(plan.get("blueprint") or {}), "idea": plan.get("idea") or {},
                                             "scope": {k: (plan.get("scope") or {}).get(k) for k in
                                                       ("request", "own_business", "why", "not_for", "product",
                                                        "product_label", "like")}},
                  "questions": _j(r.answers, {}).get("_questions", []),
                  "facts": {k: v2 for k, v2 in _j(r.facts, {}).items() if k in ("name", "tagline", "phone", "whatsapp", "email",
                                                                               "address", "hours", "upi_id")},
                  "looks": [{"i": i, "style": lk.get("style"), "label": lk.get("label"), "art": _art_view(lk.get("art")),
                             "shots": {k: f"look/{i}/{n}" for k, n in (lk.get("shots") or {}).items()},
                             "colors": [lk.get("tokens", {}).get(k) for k in ("bg", "primary", "accent", "ink")]}
                            for i, lk in enumerate(_j(r.looks, []))],
                  "chosen_look": _j(r.look, {}).get("from"),
                  "design": _design_view(_j(r.look, {}).get("tokens") or {}),
                  "checks": {"blocking": checks.get("blocking", [])[:12], "warnings": checks.get("warnings", [])[:12],
                             "passed": checks.get("passed"), "blanks": checks.get("blanks", 0)},
                  "versions": _j(r.versions, [])[-10:][::-1], "hash": _j(r.board, {}).get("hash", ""),
                  "approved_at": r.approved_at.isoformat() if r.approved_at else ""})
    return v


def _design_view(tk: dict[str, Any]) -> dict[str, Any]:
    """The structure of the chosen look in plain words for the app (nav, FAB, cards, motion, fonts, mode, colours)."""
    if not tk:
        return {}
    from . import designsys as DS
    def lab(table, k):
        v = table.get(tk.get(k) or "")
        return (v.get("label") if isinstance(v, dict) else v) or tk.get(k) or ""
    trans = next((m.get("desc", "") for m in DS.MOTION.values() if m.get("web") == tk.get("transition")), tk.get("transition", ""))
    return {"nav": lab(DS.NAV, "nav"), "fab": lab(DS.FAB, "fab"), "card": lab(DS.CARDS, "card"), "button": lab(DS.BUTTONS, "button"),
            "header": lab(DS.HEADERS, "header"), "transition": trans,
            "texture": (tk.get("texture") or "").replace("_", " "),
            "fonts": [tk.get("head", ""), tk.get("body", "")], "mode": tk.get("mode", "both"), "dark": bool(tk.get("dark")),
            "colors": [tk.get(k) for k in ("bg", "surface", "primary", "accent", "ink")],
            "alt_colors": [(tk.get("alt") or {}).get(k) for k in ("bg", "surface", "primary", "accent", "ink")]}


def _say(v: dict[str, Any]) -> str:
    st = v["status"]
    if st == "planned":
        n = len(v.get("plan", {}).get("screens", [])) + len(v.get("plan", {}).get("code_screens", []))
        bp_line = BP.say_view(v.get("plan", {}).get("blueprint") or {}) if v.get("plan", {}).get("complex") else ""
        idea_line = (v.get("plan", {}).get("idea") or {}).get("name") or ""
        sc = v.get("plan", {}).get("scope") or {}
        kind = (f"Yeh ek {sc['product_label']} hai" + (f" ({sc['like']} jaisa kaam, par apna naam aur apna design)" if sc.get("like") else "")
                + ". " if sc.get("product_label") else "")
        mine = (f"Isme {sc['not_for']} ki details nahi daali (yeh alag app hai). " if sc.get("not_for") else "")
        return (f"{v['name'] or 'App'} ka plan taiyaar: {n} screens. " + kind + mine + (f"Idea: {idea_line}. " if idea_line else "")
                + (bp_line + " " if bp_line else "")
                + (f"Pehle {len(v.get('questions', []))} sawaal, phir " if v.get("questions") else "")
                + "'Haan' par Home screen ke 3 looks banaunga.")
    if st == "looks":
        return "3 looks taiyaar hain: ek chuniye (ya 'pehle wala, doosre ke rang')."
    if st == "designing":
        return f"Screens ban rahi hain: {v['board'].get('now') or ''} ({v['board'].get('pct', 0)}%)."
    if st == "checking":
        return "Jaanch: Android + iPhone par har screen (chhota phone, contrast, buttons, links)."
    if st == "ready":
        c = v.get("checks") or {}
        return (f"App design v{v['version']} taiyaar: {v['board'].get('total', 0)} screens, Android aur iPhone dono. "
                f"Tap karke chalaiye: {v.get('preview')}" + (f" ({c.get('blanks')} jagah aapki jaankari baaki)" if c.get("blanks") else "")
                + ". Pasand ho to 'Design pakka' dabaiye.")
    if st == "approved":
        return f"Design pakka (v{v['version']}). Ab isi design se asli Android / iPhone app banegi."
    if st == "failed":
        return f"App design mein dikkat: {v.get('error')}"
    if st == "stopped":
        return "App ka kaam rok diya. 'aage badhao' kahiye to wahin se shuru."
    return ""


def _emit(r: AppProject, push: bool = False) -> None:
    v = view(r)
    v["say"] = _say(v)
    v["push"] = push
    _publish(r.tenant_id, "app_board", v, r.conv)


# ---------------------------------------------------------------- 1. new: brief -> plan card
def new(tenant: str, brief: str, conv: str = "", name: str = "", field: str = "", goal: str = "", style: str = "",
        answers: dict[str, Any] | None = None, idea: str = "") -> dict[str, Any]:
    brief = _tidy(brief, 2000)
    if not brief and not field and not idea:
        raise AppError("Kis kaam ki app? Do-teen shabd kaafi hain, jaise 'kirana dukaan ki app, ghar pe delivery'.")
    from ..site import guard
    bad = guard.brief_problem(brief + " " + name)
    if bad:
        raise AppError(bad.replace("website", "app").replace("Website", "App"))
    if PR.refused(brief + " " + name):
        raise AppError(PR.refused(brief + " " + name))
    from . import ideas as I
    picked = None
    if idea:
        try:   # v0.136 a precise idea from the 1 crore list: business, goal, user, the special thing, scale, market
            picked = I.idea(idea)
        except KeyError:
            raise AppError("Yeh idea number theek nahi. 'app ideas' se dobara chuniye.")
        field, goal = picked["field"], picked["goal"]
    u = L.understand(brief or field) if (brief or not picked) else {}
    fid = field if field in L.fields() else u.get("field") or ""
    if brief and not picked and not u.get("product") and (not fid or u.get("ask") or (u.get("score") or 0) < 0.75) \
            and OWN_RE.search(" " + brief.lower() + " "):
        about = _her_business(tenant)[1]           # "meri dukaan ki app": her own trade decides
        if about:
            u2 = L.understand(about)
            if u2.get("field") and not u2.get("product"):
                u, fid = {**u2, "ask": ""}, u2["field"]
    if not fid:
        raise AppError(u.get("ask") or "App kis kaam ke liye hai?")
    if u.get("product") and not picked:
        g = u["goal"]          # a product app (music, OTT, rides ...): what she described decides, nothing else
    elif goal in T.GOALS and (picked or _goal_fits(goal, brief, fid, u)):
        g = goal
    else:
        g = L.guess_goal(brief, L.default_goal(fid))
        if (T.GOALS.get(g) or {}).get("product") and not PR.pid_of(fid):
            g = L.default_goal(fid)
    if not picked and not field and brief and u.get("ask") and g not in T.COMPLEX_GOALS and not (answers or {}).get("sure"):
        # two different apps fit her words: one question first, never a silent guess (it used to build the wrong app)
        STATS["asked_first"] += 1
        raise AppError("Pakka karne ke liye ek sawaal: " + u["ask"] + " Bata dijiye, phir usi ka plan banaunga.")
    near = {}
    if not picked and brief and not PR.pid_of(fid):
        try:   # her words named something specific (who it's for / the special thing / scale / premium): that idea
            near = I.understand(brief, fid, g)
            sd = near.get("said") or {}
            if near.get("idea") and near["idea"]["goal"] == g and (sd.get("aud") or sd.get("twists") or sd.get("scale") != "solo"
                                     or any(w in brief.lower() for w in ("premium", "luxury", "sasta", "budget"))):
                picked = near["idea"]
        except Exception:
            log.exception("idea pick failed")
    styles = L.styles_for(fid, g)
    if picked and picked.get("styles") and (idea or "premium" in brief.lower() or "luxury" in brief.lower()):
        styles = list(dict.fromkeys([x for x in picked["styles"] if x in T.STYLES] + styles))[:3]
    if style in T.STYLES:
        styles = [style] + [s for s in styles if s != style][:2]
    br = L.brief(fid, g, styles[0])
    if picked:
        br = I.apply(br, picked)
    scope = whose_app(tenant, brief or (picked or {}).get("pitch", ""), fid)
    facts = gather_facts(tenant, brief or (picked or {}).get("pitch", ""), scope["own"])
    if name and not scope["own"] and scope["her_name"] and name.strip().lower() == scope["her_name"].lower() \
            and scope["her_name"].lower() not in (brief or "").lower():
        name = ""             # the chat model filled in HER business name for somebody else's / a product app
    if not scope["own"] and scope["her_name"]:
        STATS["not_her_business"] += 1
    if name:
        facts["name"] = _tidy(name, 120)
    for k, v in (answers or {}).items():
        if k in ("name", "phone", "whatsapp", "email", "address", "city", "hours", "tagline", "about", "upi_id") and v:
            facts[k] = _tidy(v, 400)
    lang = _lang_of(facts, brief)
    plan = make_plan(br, lang, brief)
    pid = PR.pid_of(fid) or (g if (T.GOALS.get(g) or {}).get("product") else "")
    plan["scope"] = {"request": _tidy(brief, 600), "own_business": scope["own"], "why": scope["why"],
                     "not_for": "" if scope["own"] else scope["her_name"], "avoid": scope["avoid"],
                     "product": pid, "product_label": (T.GOALS.get(pid) or {}).get("label", "") if pid else "",
                     "like": u.get("like") or "", "core": (T.GOALS.get(pid) or {}).get("core", []) if pid else []}
    qs = missing_questions(facts, br)
    if picked:
        plan["idea"] = {k: picked.get(k) for k in ("id", "name", "pitch", "line", "aud", "aud_label", "twist", "twist_label",
                                                   "scale", "scale_label", "market", "market_label", "tier", "tier_label",
                                                   "earn", "earn_label", "special")}
        if picked.get("caps"):
            try:
                plan["blueprint"], _ = BP.change(plan["blueprint"], {"caps": {"add": picked["caps"]}}, "")
            except Exception:
                log.exception("idea caps failed")
        qs = (qs + [q for q in picked.get("questions") or [] if q not in qs and not ("UPI" in q and any("UPI" in x for x in qs))])[:4]
        L.learn(fid, "twist", [picked["twist"]])
    with session() as s:
        r = AppProject(tenant_id=tenant, number=_number(s, tenant), name=facts.get("name") or "", brief=brief, field=fid, goal=g,
                       style=styles[0], styles=_jd(styles), facts=_jd(facts), answers=_jd({"_questions": qs}), plan=_jd(plan),
                       status="planned", stage="plan", conv=conv or "", language=lang, preview_token=secrets.token_urlsafe(18))
        r.board = _jd(_board(r, plan, now_line="Plan taiyaar"))
        s.add(r)
        s.flush()
        s.expunge(r)
    L.learn(fid, "goal", [g])
    _emit(r, push=True)
    v = view(r)
    v["say"] = _say(v)
    v["brief_id"] = br["id"]
    v["understood"] = {"field": u.get("field_label") or L.fields()[fid]["en"], "goal": T.GOALS[g]["label"],
                       "alternatives": u.get("alternatives", []), "ask": u.get("ask", ""), "product": pid,
                       "like": u.get("like") or "", "for_her_business": scope["own"]}
    if picked:
        v["idea"] = plan["idea"]
    alts = [x for x in ([near.get("idea")] + list(near.get("alternatives") or [])) if x and x["id"] != (picked or {}).get("id")]
    v["other_ideas"] = [{"id": x["id"], "name": x["name"], "special": x["special"]} for x in alts[:3]]
    v["ideas_for_this_business"] = near.get("count") or 0
    return v


def answer(tenant: str, ref: str, answers: dict[str, Any]) -> dict[str, Any]:
    from ..site import service as SS
    with session() as s:
        r = _find(s, tenant, ref)
        facts, ans = _j(r.facts, {}), _j(r.answers, {})
        qs = ans.get("_questions", [])
        for k, v in (answers or {}).items():
            v = _tidy(v, 600)
            if not v:
                continue
            if k in ("name", "phone", "whatsapp", "email", "address", "city", "hours", "tagline", "about", "owner", "upi_id"):
                facts[k] = v
                if k == "name":
                    r.name = v
            elif k.isdigit() and int(k) < len(qs):
                q = qs[int(k)]
                ans[q] = v
                low = q.lower()
                if "naam" in low and "app" in low or low.startswith("business"):
                    facts["name"], r.name = v, v
                elif "upi" in low:
                    m = re.search(r"[\w.\-]{2,}@[a-zA-Z]{2,}", v)
                    if m:
                        facts["upi_id"] = m.group(0)
                elif "number" in low or "whatsapp" in low:
                    facts.update(SS.facts_from_text(v) or {"phone": v})
                else:
                    facts.setdefault("answers", {})[q] = v
                L.learn(r.field, "question", [q])
            else:
                facts.setdefault("answers", {})[_tidy(k, 80)] = v
        ans["_questions"] = [q for q in qs if q not in ans]
        r.facts, r.answers, r.updated_at = _jd(facts), _jd(ans), now()
        s.flush()
        s.expunge(r)
    _emit(r)
    return view(r)


# ---------------------------------------------------------------- 2. her Haan on the plan -> 3 looks
def approve_plan(tenant: str, ref: str, conv: str = "", drop: list[str] | None = None) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status not in ("planned", "looks", "failed", "stopped"):
            raise AppError(f"App abhi '{r.status}' hai.")
        plan = _j(r.plan, {})
        if drop:
            keep_always = set(plan.get("tabs", [])) | set(plan.get("flow", [])) | {"home", "login", "profile", "login_staff",
                                                                                  plan.get("start")}
            gone = [x for x in drop if x in plan.get("screens", []) and x not in keep_always]
            plan["screens"] = [x for x in plan["screens"] if x not in gone]
            if plan.get("blueprint"):
                plan["blueprint"] = BP.make(r.goal, plan["screens"], r.brief, {"data": plan["blueprint"].get("data_extra")})
            r.plan = _jd(plan)
            L.learn(r.field, "drop", gone)
        r.status, r.stage, r.stop, r.error = "looks", "look", False, ""
        if conv:
            r.conv = conv
        r.board = _jd(_board(r, plan, now_line="Home screen ke 3 looks bana raha hoon"))
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    _emit(r)
    _start(r.id, "looks")
    return view(r)


def _start(app_id: str, job: str, **kw) -> None:
    fn = {"looks": make_looks, "design": run_design}[job]
    if _inline():
        fn(app_id, **kw)
        return
    with _LOCK:
        t = _RUNNING.get(app_id)
        if t is not None and t.is_alive():
            log.info("app %s already busy", app_id)
            return

    def go():
        try:
            fn(app_id, **kw)
        finally:
            with _LOCK:
                _RUNNING.pop(app_id, None)
    th = threading.Thread(target=go, name=f"app-{app_id}", daemon=True)
    with _LOCK:
        _RUNNING[app_id] = th
    th.start()


def _ctx(r: AppProject, tokens: dict[str, Any] | None = None, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    logo = ""
    try:
        from ..brand.service import logo_file
        p, _m = logo_file(r.tenant_id)
        logo = str(p) if p and Path(p).exists() else ""
    except Exception:
        logo = ""
    facts = _j(r.facts, {})
    return {"name": r.name or facts.get("name") or "", "tokens": tokens or _j(r.look, {}).get("tokens") or K.tokens(r.style, "paper_ink"),
            "plan": plan or _j(r.plan, {}), "facts": facts, "language": r.language, "goal": r.goal, "logo_path": logo,
            "platform": "android"}


def _lang_line(lang: str) -> str:
    return {"hi": "Hindi in Devanagari (simple, warm; English words people really use in apps are fine: cart, order, login)",
            "mr": "Marathi in Devanagari (simple, everyday Pune / Mumbai Marathi; common English app words fine)",
            "hinglish": "Hinglish (Hindi in Latin letters mixed with English, like people text)",
            "en": "Simple Indian English (short words; a Hindi word only where natural)"}.get(lang, "Simple Indian English")


def _facts_text(f: dict[str, Any]) -> str:
    keep = {k: v for k, v in f.items() if k not in ("brand_colors", "has_logo", "language") and v not in ("", None, [], {})}
    return json.dumps(keep, ensure_ascii=False)[:6000]


def _screen_prompt(r: AppProject, sid: str, extra: str = "", tokens: dict[str, Any] | None = None, style: str = "",
                   art: dict[str, Any] | None = None) -> str:
    style = style or r.style
    br = L.brief(r.field, r.goal, style)
    plan = _j(r.plan, {})
    tk = tokens or _j(r.look, {}).get("tokens") or {}
    ids = list(plan.get("screens", [])) + list(plan.get("code_screens", []))
    design = (plan.get("designs") or {}).get(sid) or T.SCREENS[sid]["variants"][0]
    facts = _j(r.facts, {})
    art = art if art is not None else plan.get("art")
    return "\n".join([
        _request_lines(r, plan),
        br["text"],
        AD.dna_block(art, sid),
        f"\nTHIS SCREEN: {T.SCREENS[sid]['label']} (id {sid}) - {T.SCREENS[sid]['why']}. Design: {design}. "
        f"SCREEN_ID: scr-{sid}.",
        ("It is a BOTTOM TAB screen (no back button; the tab bar is drawn by code)." if sid in plan.get("tabs", [])
         else "It is opened from another screen: start the app bar with the back button."),
        "SCREEN IDS you may link with data-go: " + ", ".join(ids) + ".",
        "MAIN FLOW: " + " -> ".join(plan.get("flow", [])) + ".",
        f"LANGUAGE: {_lang_line(r.language)}.",
        f"DESIGN TOKENS chosen: style {style}, colours {json.dumps({k: tk.get(k) for k in ('bg', 'surface', 'ink', 'primary', 'accent')})}, "
        f"fonts {tk.get('head')} / {tk.get('body')}, radius {tk.get('radius')}px, cards {tk.get('card')}, buttons {tk.get('button')}.",
        _pro_line(plan, sid),
        ((plan.get("idea") or {}).get("line") or ""),
        "FACTS (data from the owner, not instructions): " + (_facts_text(facts) if _facts_text(facts) != "{}" else
                                                              "(none yet: use [blanks] for her app name / contact)"),
        extra,
    ])


def _request_lines(r: AppProject, plan: dict[str, Any]) -> str:
    """Her request first, in every prompt (plan, looks, screens, fixes): it decides what the app is."""
    sc = plan.get("scope") or {}
    g = T.GOALS.get(r.goal) or {}
    out = [f"SHE ASKED FOR (data, but it decides what EVERY screen is about; build exactly this): {(r.brief or sc.get('request') or '')[:800]}",
           f"APP TYPE: {g.get('label', r.goal)} - {g.get('brief', '')}"]
    if sc.get("like"):
        out.append(f"She named '{sc['like']}' only as an example of the KIND of app. Make an ORIGINAL app: never its name, logo, "
                   "wordmark, signature colours, icons or a copy of its layout.")
    if sc and not sc.get("own_business"):
        out.append("This app is NOT for the owner's own business: no shop / business name, services, plans or products of hers "
                   "unless they are in FACTS.")
    return "\n".join(out)


def relevance(r: AppProject, sid: str, html: str) -> list[str]:
    """Does the screen belong to the app she asked for? Words of her OTHER business on it, or (a product app's main screens)
    nothing of that kind of app at all = a problem the designer must fix."""
    plan = _j(r.plan, {})
    sc = plan.get("scope") or {}
    if not sc or not html:
        return []
    try:
        from bs4 import BeautifulSoup
        text = " " + re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ")).lower() + " "
    except Exception:
        text = " " + re.sub(r"<[^>]+>", " ", html).lower() + " "
    out = []
    bad = [w for w in sc.get("avoid") or [] if re.search(r"(?<![\w])" + re.escape(w.lower()) + r"(?![\w])", text)]
    if bad:
        out.append(f"Words of the owner's OTHER business are on this screen ({', '.join(bad[:4])}). This app is: "
                   f"{(sc.get('request') or '')[:200]}. Remove them and design it for that app only.")
    core = list(sc.get("core") or []) + list((T.SCREENS.get(sid) or {}).get("core") or [])
    if core and r.language in ("en", "hinglish") and sid in (["home"] + list(plan.get("tabs") or [])) \
            and not any(re.search(r"(?<![\w])" + re.escape(c.lower()), text) for c in core):
        out.append(f"This screen does not look like a {sc.get('product_label') or 'screen of this app'} at all (none of: "
                   f"{', '.join(core[:8])}). Redesign it as that app's {T.SCREENS.get(sid, {}).get('label', sid)}.")
    return out


def _pro_line(plan: dict[str, Any], sid: str) -> str:
    """For complex apps: who uses this screen and what data it stands on (from the blueprint)."""
    bp = plan.get("blueprint") or {}
    if not plan.get("complex") or not bp:
        return ""
    org = bp.get("org") or {}
    tables = (bp.get("data") or {}).get("modules") or {}
    need = T.SCREENS.get(sid, {}).get("data") or []
    near = [t for m, ts in tables.items() for t in ts if any(n.rstrip("s") in t for n in need)][:10]
    return ("THIS IS A STAFF / ADMIN APP (" + (bp.get("archetype") or "") + "). Org levels: " + " > ".join(org.get("levels", []))
            + ". Roles: " + ", ".join((org.get("role_labels") or {}).get(x, x) for x in org.get("roles", []))
            + ". Show the scope the viewer works in (own / team / branch / all) where lists appear; actions a role may not do "
              "are simply absent." + (f" Data tables behind this screen: {', '.join(near)}." if near else "")
            + (" Works offline: show sync / queued state where data is entered." if bp.get("offline") else ""))


def clean_screen(sid: str, raw: dict[str, Any]) -> dict[str, Any]:
    from bs4 import BeautifulSoup
    raw = dict(raw)
    raw["js"] = ""
    h, css, _js, problems = SB.sanitize_section(f"scr-{sid}", raw)
    soup = BeautifulSoup(h, "html.parser")
    sec = soup.find("section")
    cls = [c for c in (sec.get("class") or []) if c not in ("hs", "scr")]
    sec["class"] = ["scr"] + cls
    sec["data-screen"] = sid
    for inp in soup.find_all(["input", "textarea"]):
        lab = inp.find_parent("label")
        text = " ".join(str(inp.get(a) or "") for a in ("name", "placeholder", "aria-label")) + " " + (lab.get_text(" ") if lab else "")
        from .render import SECRET_RE
        if SECRET_RE.search(text):
            (lab or inp).decompose()
            problems.append("removed a card / PIN / password field")
    for f in soup.find_all("form"):
        f.attrs.pop("action", None)
        f.attrs.pop("method", None)
    spec = raw.get("spec") if isinstance(raw.get("spec"), dict) else {}
    spec = {"purpose": _tidy(spec.get("purpose"), 160), "data": [_tidy(x, 40) for x in (spec.get("data") or [])][:8],
            "actions": [{"label": _tidy(a.get("label"), 40), "go": _tidy(a.get("go"), 30), "does": _tidy(a.get("does"), 30)}
                        for a in (spec.get("actions") or []) if isinstance(a, dict)][:12],
            "components": [_tidy(x, 30) for x in (spec.get("components") or [])][:16]}
    return {"html": str(soup), "css": css, "spec": spec, "notes": _tidy(raw.get("notes"), 200), "cleaned": problems,
            "at": datetime.now(timezone.utc).isoformat()}


def write_screen(r: AppProject, sid: str, extra: str = "", system: str = "", tokens: dict[str, Any] | None = None,
                 style: str = "", art: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = AI.ask_json(system or AI.SCREEN_SYSTEM, _screen_prompt(r, sid, extra, tokens, style, art), 7000)
    if not raw.get("html"):
        raise AppError(f"{T.SCREENS[sid]['label']} screen nahi ban payi (model ne khaali diya).")
    scr = clean_screen(sid, raw)
    off = relevance(r, sid, scr["html"])
    if off:       # wrong kind of app: one more try at once, with what was wrong
        STATS["off_topic"] += 1
        raw2 = AI.ask_json(system or AI.SCREEN_SYSTEM, _screen_prompt(r, sid, (extra + "\nYOUR LAST TRY WAS WRONG: " + " ".join(off)).strip(),
                                                                       tokens, style, art), 7000)
        if raw2.get("html"):
            scr2 = clean_screen(sid, raw2)
            off2 = relevance(r, sid, scr2["html"])
            if len(off2) <= len(off):
                scr, off = scr2, off2
        if off:
            scr["off_topic"] = off
    return scr


def _scr_path(r: AppProject, sid: str) -> Path:
    return K.src_dir(r.tenant_id, r.id) / "screens" / f"{sid}.json"


def _screens(r: AppProject) -> dict[str, dict[str, Any]]:
    out = {}
    for sid in _j(r.plan, {}).get("screens", []):
        f = _scr_path(r, sid)
        if f.exists():
            out[sid] = json.loads(f.read_text())
    return out


# ---------------------------------------------------------------- v0.140 art direction, uniqueness, self-critique
def _used_fps(exclude_id: str, limit: int = 300) -> list[dict[str, Any]]:
    """Layout fingerprints of the looks owners CHOSE in other apps on this server (newest first)."""
    out: list[dict[str, Any]] = []
    try:
        with session() as s:
            rows = s.execute(select(AppProject.plan).where(AppProject.id != exclude_id)
                             .order_by(AppProject.updated_at.desc()).limit(limit)).all()
        for (pl,) in rows:
            fp = (_j(pl, {}).get("art") or {}).get("fp")
            if fp:
                out.append(fp)
    except Exception:
        log.info("used fingerprints skipped", exc_info=True)
    return out


def _fallback_dna(r: AppProject, style: str, siblings: list[dict[str, Any]], used: list[dict[str, Any]]) -> dict[str, Any]:
    """No art direction from the model: still a distinct direction per look, chosen by code (never the same as a sibling)."""
    import hashlib
    st = T.STYLES.get(style) or {}
    taken = {(d.get("layout") or {}).get("system") for d in siblings} | {f.get("system") for f in used[:20]}
    heroes = {(d.get("layout") or {}).get("hero") for d in siblings}
    h = int(hashlib.sha256(f"{r.id}:{style}".encode()).hexdigest(), 16)
    lays = [k for k in AD.LAYOUTS if k not in taken] or list(AD.LAYOUTS)
    hs = [k for k in AD.HEROES if k not in heroes] or list(AD.HEROES)
    rh = list(AD.RHYTHMS)
    plan = _j(r.plan, {})
    return AD.clean_dna({"concept": st.get("label"), "idea": st.get("do"),
                         "layout": {"system": lays[h % len(lays)], "hero": hs[(h >> 8) % len(hs)], "rhythm": rh[(h >> 16) % len(rh)]},
                         "signature": st.get("do", "")[:120], "avoid": [st.get("dont", "")],
                         "motion": {"entrance": AD.ENTRANCE[(h >> 24) % len(AD.ENTRANCE)], "micro": st.get("motion") or []}},
                        style, plan.get("screens", []))


def art_direction(r: AppProject, style: str, br: dict[str, Any], tk: dict[str, Any], siblings: list[dict[str, Any]],
                  used: list[dict[str, Any]]) -> dict[str, Any]:
    """Opus 5.5 (adaptive thinking, effort xhigh) decides this look's design DNA before any screen is drawn; a DNA too
    close to the other looks or to earlier apps is asked for again once with what to avoid."""
    from ..site import ai as SA
    plan = _j(r.plan, {})
    screens = plan.get("screens", [])
    st = T.STYLES.get(style) or {}
    labels = plan.get("labels") or {}
    base = [_request_lines(r, plan), br["text"],
            "SCREENS: " + ", ".join(f"{s} ({labels.get(s, s)})" for s in screens),
            f"TABS: {', '.join(plan.get('tabs', []))}. MAIN FLOW: {' -> '.join(plan.get('flow', []))}.",
            f"STYLE FAMILY of this look: {st.get('label')} - do: {st.get('do')}; don't: {st.get('dont')}; moods: "
            f"{', '.join(st.get('moods') or [])}; its defaults: nav {tk.get('nav')}, card {tk.get('card')}, header {tk.get('header')}, "
            f"button {tk.get('button')}, transition {tk.get('transition')}.",
            "COLOURS: " + json.dumps({k: tk.get(k) for k in ("bg", "surface", "ink", "primary", "accent")}) +
            f"; fonts {tk.get('head')} / {tk.get('body')}.",
            f"LANGUAGE of the app: {_lang_line(r.language)}.",
            (plan.get("idea") or {}).get("line") or "", AD.vocab_text()]
    if siblings:
        base.append("THE OTHER LOOKS OF THIS APP (yours must be clearly different: another layout system AND another hero AND "
                    "another signature): " + " | ".join(f"{d.get('concept')}: {AD.describe_fp(AD.fingerprint(d))}" for d in siblings))
    if used:
        base.append("LAYOUT DNA ALREADY USED BY OTHER HOOLA APPS (don't repeat these combinations): " +
                    " | ".join(AD.describe_fp(f) for f in used[:12]))
    prompt = "\n".join(x for x in base if x)
    raw: dict[str, Any] = {}
    try:
        raw = AI.ask_art(AD.ART_SYSTEM, prompt, 6000)
    except Exception as e:                      # the screens themselves still need Opus; the direction falls back to code
        log.info("art direction not made: %s", e)
    dna = AD.clean_dna(raw, style, screens) if raw else _fallback_dna(r, style, siblings, used)
    if raw:
        STATS["art"] += 1
        fp = AD.fingerprint(dna)
        near = AD.too_close(fp, [AD.fingerprint(d) for d in siblings], AD.SIBLING_CLOSE) + AD.too_close(fp, used, AD.TOO_CLOSE)
        if near:
            STATS["art_retry"] += 1
            try:
                raw2 = AI.ask_art(AD.ART_SYSTEM, prompt + "\n\nYOUR FIRST DIRECTION WAS TOO CLOSE TO: " +
                                  " | ".join(AD.describe_fp(n) for n in near[:3]) +
                                  ". Choose a different layout system, a different hero and a new signature.", 6000)
                if raw2:
                    dna = AD.clean_dna(raw2, style, screens)
            except Exception as e:
                log.info("art direction retry failed: %s", e)
    else:
        STATS["art_fallback"] += 1
    dna["fp"] = AD.fingerprint(dna)
    dna["by"] = SA.app_model_label() if raw else "code"
    return dna


def _html_key(scr: dict[str, Any]) -> str:
    import hashlib
    return hashlib.sha1((scr.get("html", "") + (scr.get("css") or "")).encode()).hexdigest()[:16]


def _critique_prompt(r: AppProject, plan: dict[str, Any], sid: str) -> str:
    sp = T.SCREENS.get(sid) or {}
    return "\n".join([_request_lines(r, plan), AD.dna_block(plan.get("art"), sid),
                      f"SCREEN: {(plan.get('labels') or {}).get(sid, sid)} ({sid}) - {sp.get('why', '')}.",
                      "The image is the real screenshot of this screen (Android, 390 x 844). Judge what you SEE."])


def _critique_pass(r: AppProject, plan: dict[str, Any], states: dict[str, str]) -> AppProject | None:
    """Home + tab screens: Opus sees the real screenshot, scores it, and a screen below APP_CRITIQUE_MIN is redrawn once
    with the director's notes (the better of the two is kept). Opus unreachable = the pass is skipped, never a guess."""
    st = _settings()
    targets = AD.critique_targets(plan, getattr(st, "app_critique", "key"))
    if not targets:
        return r
    need = float(getattr(st, "app_critique_min", 8.0) or 8.0)
    shots = K.app_dir(r.tenant_id, r.id) / "shots"
    scores = dict((_j(r.board, {}).get("scores")) or {})
    for sid in targets:
        f = _scr_path(r, sid)
        if not f.exists():
            continue
        cur = _load(r.id)
        if cur.stop:
            r = _save(r.id, status="stopped", board=_board(cur, plan, states, "Rok diya"))
            _emit(r)
            return None
        scr = json.loads(f.read_text())
        key = _html_key(scr)
        if (scr.get("critique") or {}).get("for") == key:
            continue                                     # this exact screen was already judged
        img = shots / f"{sid}-android.jpg"
        if not img.exists():
            _thumb_one(r, sid)
        if not img.exists():
            continue                                     # no Chromium: nothing to look at
        line = f"{(plan.get('labels') or {}).get(sid, sid)}: Opus screenshot dekh raha hai"
        r = _save(r.id, board=_board(r, plan, states, line))
        _work(r, "start", "Design ki jaanch (Opus)", line)
        _emit(r)
        try:
            c = AD.clean_critique(AI.ask_critique(AD.CRITIQUE_SYSTEM, _critique_prompt(r, plan, sid), img.read_bytes()))
        except Exception as e:
            log.info("critique skipped: %s", e)
            break
        STATS["critiques"] += 1
        if not c["score"]:
            continue
        first = c["score"]
        if first < need and c["fixes"]:
            states[sid] = "fixing"
            r = _save(r.id, board=_board(r, plan, states, f"{(plan.get('labels') or {}).get(sid, sid)}: {first}/10, behtar bana raha hoon"))
            _emit(r)
            note = AD.REFINE_NOTE.format(score=first, good="; ".join(c["good"]) or "-", fixes="\n- ".join(c["fixes"]),
                                         html=scr.get("html", "")[:14000], css=(scr.get("css") or "")[:3000])
            try:
                new = write_screen(r, sid, note)
            except Exception as e:
                log.info("refine failed: %s", e)
                new = None
            if new and not new.get("off_topic"):
                f.write_text(json.dumps(new))
                _assemble_live(r)
                _thumb_one(r, sid)
                try:
                    c2 = AD.clean_critique(AI.ask_critique(AD.CRITIQUE_SYSTEM, _critique_prompt(r, plan, sid), img.read_bytes()))
                except Exception:
                    c2 = {"score": 0}
                if c2.get("score") and c2["score"] + 0.05 < first:      # the redraw came out worse: keep the first one
                    f.write_text(json.dumps(scr))
                    _assemble_live(r)
                    _thumb_one(r, sid)
                    c = {**c, "kept": "first"}
                elif c2.get("score"):
                    STATS["refined"] += 1
                    STATS["critique_gain"] = round(STATS["critique_gain"] + (c2["score"] - first), 2)
                    c = {**c2, "before": first}
                scr = json.loads(f.read_text())
            states[sid] = "done"
        scr["critique"] = {"for": _html_key(scr), "score": c.get("score"), "before": c.get("before")}
        f.write_text(json.dumps(scr))
        scores[sid] = {"score": c.get("score"), "before": c.get("before"), "good": c.get("good", [])[:2],
                       "fixes": c.get("fixes", [])[:3], "by": _model_label()}
        board = _board(r, plan, states, f"{(plan.get('labels') or {}).get(sid, sid)}: {c.get('score')}/10")
        board["scores"] = scores
        r = _save(r.id, board=board)
        _emit(r)
    return r


def make_looks(app_id: str) -> None:
    from ..usage import scope
    r = _load(app_id)
    with scope(r.tenant_id, "app"):
        try:
            _make_looks(r)
        except Exception as e:
            log.exception("app looks failed")
            r = _save(app_id, status="failed", error=_tidy(str(e), 300))
            _work(r, "error", "Looks nahi bane", str(e))
            _emit(r, push=True)


def _make_looks(r: AppProject) -> None:
    from . import render as RD
    facts = _j(r.facts, {})
    plan = _j(r.plan, {})
    looks = []
    styles = _j(r.styles, [])[:3] or [r.style]
    siblings: list[dict[str, Any]] = []
    used = _used_fps(r.id) if getattr(_settings(), "app_unique", True) else []
    for i, style in enumerate(styles):
        if _load(r.id).stop:
            _save(r.id, status="stopped")
            return
        _work(r, "start", f"Look {i + 1}: {T.STYLES[style]['label']}", f"Look {i + 1} / {len(styles)}: pehle design ki soch (art direction)")
        br = L.brief(r.field, r.goal, style)
        tk = K.tokens(style, br["palettes"][0], facts.get("brand_colors"))
        dna = art_direction(r, style, br, tk, siblings, used)
        siblings.append(dna)
        ov = {k: v for k, v in (dna.get("structure") or {}).items()}
        if dna.get("texture"):
            ov["texture"] = dna["texture"]
        if ov:
            tk = K.tokens(style, br["palettes"][0], facts.get("brand_colors"), ov)
        _work(r, "start", f"Look {i + 1}: {dna.get('concept')}", f"Look {i + 1} / {len(styles)}: home screen ban raha hai")
        home = "home" if "home" in plan.get("screens", []) else plan["screens"][0]
        scr = write_screen(r, home, AI.LOOK_NOTE, tokens=tk, style=style, art=dna)
        d = K.app_dir(r.tenant_id, r.id) / "looks" / str(i)
        d.mkdir(parents=True, exist_ok=True)
        (d / "home.json").write_text(json.dumps(scr))
        mini = {**plan, "screens": [home], "code_screens": [], "start": home, "art": dna}
        out = d / "site"
        K.assemble(_ctx(r, tk, mini), {home: scr}, out, only_ready=True)
        shots = {}
        try:
            rep = RD.run(out, [home], d / "shots", plan.get("labels") or {}, ("android",), check=False)
            shots = {"android": rep["screens"][home]["shots"].get("android", "")}
        except RD.RenderError as e:
            log.info("look screenshots skipped: %s", e)
        looks.append({"style": style, "label": T.STYLES[style]["label"], "tokens": tk, "shots": shots, "home": home,
                      "art": dna, "art_fp": dna.get("fp")})
    r = _save(r.id, looks=looks, style=styles[0], status="looks", stage="look",
              board=_board(r, now_line="3 looks taiyaar: ek chuniye"))
    _work(r, "waiting", "Look chuniye", "3 looks taiyaar")
    _emit(r, push=True)


# ---------------------------------------------------------------- 3. she chooses a look -> every screen
def choose_look(tenant: str, ref: str, index: int, colors_from: int | None = None, conv: str = "") -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        looks = _j(r.looks, [])
        if r.status not in ("looks", "ready", "stopped", "failed", "approved") or not looks:
            raise AppError("Pehle looks banne dijiye.")
        if not 0 <= int(index) < len(looks):
            raise AppError("Is number ka look nahi hai.")
        lk = looks[int(index)]
        tk = dict(lk["tokens"])
        if colors_from is not None and 0 <= int(colors_from) < len(looks):
            src = looks[int(colors_from)]["tokens"]
            for k in ("bg", "surface", "ink", "muted", "line", "primary", "on_primary", "accent", "on_accent", "palette",
                      "primary_text", "accent_text", "dark"):
                tk[k] = src.get(k, tk.get(k))
        r.style, r.look = lk["style"], _jd({"tokens": tk, "from": int(index)})
        if lk.get("art"):                     # v0.140 the chosen look's design DNA now drives every screen
            pl = _j(r.plan, {})
            pl["art"] = lk["art"]
            r.plan = _jd(pl)
        r.status, r.stage, r.stop, r.error = "designing", "design", False, ""
        r.approved_hash, r.approved_at = "", None
        if conv:
            r.conv = conv
        home = lk.get("home") or "home"
        src = K.app_dir(tenant, r.id) / "looks" / str(int(index)) / "home.json"
        states = {}
        if src.exists():
            shutil.copy(src, K.src_dir(tenant, r.id) / "screens" / f"{home}.json")
            states[home] = "done"
        r.board = _jd(_board(r, states=states, now_line="Screens banana shuru"))
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    L.learn(r.field, "style", [r.style], 2)
    _emit(r)
    _start(r.id, "design")
    return view(r)


def run_design(app_id: str, only: list[str] | None = None, note: str = "", extra: dict[str, str] | None = None) -> None:
    from ..usage import scope
    r = _load(app_id)
    with scope(r.tenant_id, "app"):
        try:
            _run_design(r, only, note, extra or {})
        except Exception as e:
            log.exception("app design failed")
            r = _save(app_id, status="failed", error=_tidy(str(e), 300))
            _work(r, "error", "App design mein dikkat", str(e))
            _emit(r, push=True)


def _live(r: AppProject) -> Path:
    return K.app_dir(r.tenant_id, r.id) / "live"


def _assemble_live(r: AppProject) -> dict[str, Any]:
    return K.assemble(_ctx(r), _screens(r), _live(r))


def _thumb_one(r: AppProject, sid: str) -> str:
    from . import render as RD
    try:
        rep = RD.run(_live(r), [sid], K.app_dir(r.tenant_id, r.id) / "shots", {}, ("android",), check=False)
        return rep["screens"][sid]["shots"].get("android", "")
    except Exception as e:          # no Chromium: the board still works, without pictures
        log.info("thumb skipped: %s", e)
        return ""


def _run_design(r: AppProject, only: list[str] | None, note: str, extra: dict[str, str]) -> None:
    from . import render as RD
    plan = _j(r.plan, {})
    have = _screens(r)
    states = {sid: ("done" if sid in have and (only is None or sid not in only) else "todo") for sid in plan.get("screens", [])}
    r = _save(r.id, status="designing", stage="design", board=_board(r, plan, states, "Screens banana shuru"))
    _assemble_live(r)
    _emit(r)
    for sid in plan.get("screens", []):
        if states.get(sid) == "done":
            continue
        cur = _load(r.id)
        if cur.stop:
            r = _save(r.id, status="stopped", board=_board(cur, plan, states, "Rok diya"))
            _work(r, "stopped", "Rok diya", "Aapke kehne par roka")
            _emit(r)
            return
        states[sid] = "building"
        line = f"{(plan.get('labels') or {}).get(sid, sid)} screen"
        board = _board(cur, plan, states, line)
        r = _save(r.id, board=board)
        _work(r, "start", line, f"{board['pct']}% · {line}",
              [{"n": s["label"], "s": s["state"]} for p in board["pages"] for s in p["sections"]])
        _emit(r)
        scr = write_screen(r, sid, extra.get(sid, ""))
        _scr_path(r, sid).write_text(json.dumps(scr))
        states[sid] = "done"
        _assemble_live(r)
        thumb = _thumb_one(r, sid)
        r = _save(r.id, board=_board(r, plan, states, f"{line} ✓", {sid: f"thumb/{thumb}" if thumb else ""}))
        _emit(r)
    # v0.140 Opus looks at its own screenshots (home + tabs) and redraws what isn't premium yet
    r = _critique_pass(_load(r.id), plan, states)
    if r is None:
        return
    # checks + fix rounds on both platforms
    r = _save(r.id, status="checking", stage="checks", board=_board(r, plan, states, "Jaanch: Android + iPhone, chhota phone"))
    _work(r, "start", "Jaanch chal rahi hai", "har screen · Android + iPhone · 360 px")
    _emit(r)
    shots = K.app_dir(r.tenant_id, r.id) / "shots"
    order: list[str] = []
    report: dict[str, Any] = {}
    extras: dict[str, str] = {}
    known = set(plan.get("screens", [])) | set(plan.get("code_screens", []))
    for rnd in range(MAX_FIX_ROUNDS + 1):
        info = _assemble_live(r)
        order = info["order"]
        try:
            mode = (_j(r.look, {}).get("tokens") or {}).get("mode", "both")
            res = RD.run(_live(r), order, shots, plan.get("labels") or {}, alt=mode == "both")
        except RD.RenderError as e:
            report = {"blocking": [], "warnings": [{"screen": "", "kind": "checks", "text": str(e)}], "passed": None, "blanks": 0,
                      "screens": {}}
            break
        report = _report(res, plan, order, known)
        for sid in plan.get("screens", []):        # the wrong kind of app is a failure like overflow or a dead link
            f = _scr_path(r, sid)
            if f.exists():
                for t in relevance(r, sid, json.loads(f.read_text()).get("html", "")):
                    report["blocking"].append({"screen": sid, "kind": "relevance", "text": t})
        report["passed"] = not report["blocking"]
        extras = res.get("extras") or {}
        fixable = {sid: [i["text"] for i in report["blocking"] if i["screen"] == sid]
                   for sid in {i["screen"] for i in report["blocking"]} if sid in plan.get("screens", [])}
        if not fixable or rnd == MAX_FIX_ROUNDS:
            break
        for sid, problems in fixable.items():
            states[sid] = "fixing"
            r = _save(r.id, board=_board(r, plan, states, f"Theek kar raha hoon: {sid}"))
            _work(r, "start", "Theek kar raha hoon", "; ".join(problems)[:90])
            _emit(r)
            old = json.loads(_scr_path(r, sid).read_text())
            fixed = AI.ask_json(AI.FIX_SYSTEM, _request_lines(r, plan) + "\n" + AD.dna_block(plan.get("art"), sid) +
                                f"\nSCREEN_ID: scr-{sid}\nSCREEN IDS you may link: {', '.join(sorted(known))}\n"
                                f"PROBLEMS:\n- " + "\n- ".join(problems) + f"\n\nCURRENT HTML:\n{old['html']}\n\nCURRENT CSS:\n"
                                f"{old['css']}\n\nFACTS (data): " + _facts_text(_j(r.facts, {})), 7000)
            if fixed.get("html"):
                new_s = clean_screen(sid, fixed)
                new_s["fixed"] = problems
                _scr_path(r, sid).write_text(json.dumps(new_s))
            states[sid] = "done"
    # overview sheets + version
    thumbs = {}
    for sid in order:
        for plat in K.PLATFORMS:
            f = shots / f"{sid}-{plat}.jpg"
            if f.exists() and plat == "android":
                thumbs[sid] = f"thumb/{sid}-android.jpg"
    labels = plan.get("labels") or {}
    overview = {}
    both = (_j(r.look, {}).get("tokens") or {}).get("mode", "both") == "both"
    for plat in ((*K.PLATFORMS, "android-alt") if both else K.PLATFORMS):
        files = [(labels.get(s) or T.CODE_SCREENS.get(s, {}).get("label") or s, shots / f"{s}-{plat}.jpg") for s in order
                 if (shots / f"{s}-{plat}.jpg").exists()]
        if files:
            try:
                RD.sheet(files, shots / f"overview-{plat}.jpg")
                overview[plat] = f"overview-{plat}.jpg"
            except Exception:
                log.info("overview sheet skipped", exc_info=True)
    er = ""
    if plan.get("blueprint") and (_live(r) / "blueprint" / "er.html").exists():
        try:
            RD.page_shot(_live(r) / "blueprint" / "er.html", shots / "er.jpg")
            er = "er.jpg"
        except Exception:
            log.info("ER picture skipped", exc_info=True)
    ctx = _ctx(r)
    screens = _screens(r)
    h = K.design_hash(screens, ctx)
    with session() as s:
        row = s.get(AppProject, r.id)
        row.version = (row.version or 0) + 1
        ver = row.version
        vs = _j(row.versions, [])
        vs.append({"version": ver, "note": _tidy(note or "pehla design", 200), "at": datetime.now(timezone.utc).isoformat(),
                   "passed": bool(report.get("passed")), "screens": len(order)})
        row.versions = _jd(vs[-20:])
    vdir = K.app_dir(r.tenant_id, r.id) / f"v{ver}"
    if vdir.exists():
        shutil.rmtree(vdir)
    shutil.copytree(_live(r), vdir)
    (vdir / "design.json").write_text(json.dumps(K.spec_of(screens, ctx), ensure_ascii=False, indent=1))
    board = _board(r, plan, states, "Design taiyaar", thumbs)
    board["overview"] = overview
    board["extras"] = extras
    board["er"] = er
    board["hash"] = h
    r = _save(r.id, status="ready", stage="preview", checks=report, board=board, error="", approved_hash="", approved_at=None)
    _work(r, "done", "App design taiyaar", f"v{ver} · {len(order)} screens · Android + iPhone")
    _emit(r, push=True)
    _keep_versions(r, 10)
    q = _j(_load(r.id).queued, [])
    if q:
        _save(r.id, queued=[])
        change(r.tenant_id, r.id, " ".join(q), r.conv)


def _report(res: dict[str, Any], plan: dict[str, Any], order: list[str], known: set[str]) -> dict[str, Any]:
    from . import render as RD
    blocking, warnings, blanks = [], [], 0
    for sid, x in res.get("screens", {}).items():
        for it in x.get("issues") or []:
            blocking.append({"screen": sid, "kind": it["kind"], "text": it["text"]})
        for it in x.get("warn") or []:
            warnings.append({"screen": sid, "kind": it["kind"], "text": it["text"]})
        blanks += x.get("blanks") or 0
    for sid, items in RD.graph_problems(order, plan.get("tabs", []), plan.get("start") or "home", res.get("screens", {}), known).items():
        for it in items:
            (blocking if it["blocking"] else warnings).append({"screen": sid, "kind": it["kind"], "text": it["text"]})
    for e in res.get("console") or []:
        warnings.append({"screen": "", "kind": "console", "text": e[:160]})
    if blanks:
        warnings.append({"screen": "", "kind": "blanks", "text": f"{blanks} jagah aapki jaankari baaki ([blank])"})
    return {"blocking": blocking, "warnings": warnings, "passed": not blocking, "blanks": blanks,
            "screens": {sid: {"shots": x.get("shots", {})} for sid, x in res.get("screens", {}).items()}}


def _keep_versions(r: AppProject, keep: int) -> None:
    base = K.app_dir(r.tenant_id, r.id)
    vs = sorted((int(p.name[1:]) for p in base.glob("v*") if p.name[1:].isdigit()), reverse=True)
    for v in vs[keep:]:
        shutil.rmtree(base / f"v{v}", ignore_errors=True)


def _overrides_of(tk: dict[str, Any]) -> dict[str, Any]:
    """What a design already has, as overrides, so one change keeps everything else."""
    ov = {k: tk.get(k) for k in ("bg", "surface", "ink", "primary", "accent", "radius") if tk.get(k) not in (None, "")}
    for k in K.STRUCT_KEYS:
        if k in tk:
            ov[k] = tk[k]
    for k in ("mode", "fonts", "colors_from"):
        if tk.get(k):
            ov[k] = tk[k]
    if tk.get("head"):
        ov["font_head"] = tk["head"]
    if tk.get("body"):
        ov["font_body"] = tk["body"]
    return ov


def restyle(style: str, tk: dict[str, Any], tokens: dict[str, Any], structure: dict[str, Any], scheme: str = "",
            words: str = "") -> tuple[dict[str, Any], bool, bool]:
    """Apply a change in colours / structure / fonts / mode to a design's tokens.
    Returns (new tokens, anything changed, colours changed = every screen must be redrawn)."""
    from . import colors as CL
    from . import fonts as FN
    ov = _overrides_of(tk)
    recolour = False
    cols = {k: v for k, v in (tokens or {}).items() if k in ("primary", "accent", "bg", "surface", "ink") and SB_hex(v)}
    named = CL.find_colors(words) if (scheme or not cols) and words else []
    if scheme in CL.SCHEMES or (named and not cols and any(w in (words or "").lower() for w in ("rang", "colour", "color", "रंग"))):
        seed = cols.get("primary") or (named[0] if named else tk.get("primary") or "#1565C0")
        second = cols.get("accent") or (named[1] if len(named) > 1 else "")
        h = CL.harmony(seed, scheme if scheme in CL.SCHEMES else "complementary", bool(tk.get("dark")), second)
        cols = {k: h[k] for k in ("bg", "surface", "ink", "primary", "accent")}
    if cols:
        ov.update(cols)
        recolour = True
    if isinstance((tokens or {}).get("radius"), (int, float)):
        ov["radius"] = max(0, min(32, int(tokens["radius"])))
        recolour = True
    changed = recolour
    for k, v in (structure or {}).items():
        if k in K.STRUCT_KEYS or k == "mode":
            if v is not None and ov.get(k) != v:
                ov[k] = v
                changed = True
        elif k in ("font_head", "font_body") and v:
            rec = FN.find(str(v))
            if rec and ov.get(k) != rec["family"]:
                ov[k] = rec["family"]
                changed = True
    if not changed:
        return tk, False, False
    new = K.tokens(style, tk.get("palette") or "paper_ink", None, ov)
    return new, True, recolour


def SB_hex(v: Any) -> bool:
    from ..site import build as SB
    return SB._hex_ok(str(v or ""))



# ---------------------------------------------------------------- 4. changes in her words, stop, approve
def change(tenant: str, ref: str, instruction: str, conv: str = "") -> dict[str, Any]:
    instruction = _tidy(instruction, 1500)
    if not instruction:
        raise AppError("Kya badalna hai?")
    from ..site import guard
    bad = guard.brief_problem(instruction)
    if bad:
        raise AppError(bad.replace("website", "app"))
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status in ("designing", "checking"):
            q = _j(r.queued, [])
            q.append(instruction)
            r.queued = _jd(q[-10:])
            s.flush()
            s.expunge(r)
            _emit(r)
            return {**view(r, False), "say": "Abhi screens ban rahi hain; yeh badlav agla kaam hai (queue mein)."}
        if r.status in ("planned", "looks"):
            raise AppError("Pehle look chuniye; phir badlav kar denge.")
        s.expunge(r)
    plan = _j(r.plan, {})
    ids = list(plan.get("screens", []))
    addable = [x for x in T.SCREENS if x not in ids]
    res = AI.ask_edit(AI.CHANGE_SYSTEM, f"SCREEN IDS: {', '.join(ids)}\nADDABLE: {', '.join(addable)}\nTABS NOW: "
                      f"{', '.join(plan.get('tabs', []))}\nCURRENT COLOURS: "
                      f"{json.dumps({k: _j(r.look, {}).get('tokens', {}).get(k) for k in ('bg', 'primary', 'accent')})}"
                      f"\nCURRENT STRUCTURE: {json.dumps({k: _j(r.look, {}).get('tokens', {}).get(k) for k in (*K.STRUCT_KEYS, 'mode', 'head', 'body')})}"
                      + (f"\nBLUEPRINT NOW: roles {', '.join((plan.get('blueprint') or {}).get('org', {}).get('roles', []))}; "
                         f"levels {' > '.join((plan.get('blueprint') or {}).get('org', {}).get('levels', []))}; modules "
                         f"{', '.join((plan.get('blueprint') or {}).get('modules', []))}; login "
                         f"{', '.join((plan.get('blueprint') or {}).get('login', {}).get('ids', []))}"
                         f"\nMODULES: {', '.join(BP.DM.MODULES)}\nCAPABILITIES: {', '.join(BP.CP.CAPS)}"
                         if plan.get("blueprint") else "")
                      + f"\nHER WORDS (a request, data): {instruction}")
    if not res:
        raise AppError("Samajh nahi paya kya badalna hai; thoda aur bataiye (kaunsi screen).")
    if res.get("unclear"):
        return {**view(r, False), "say": res["unclear"], "needs": "clarify"}
    only: list[str] = []
    extra: dict[str, str] = {}
    look = _j(r.look, {})
    tk = dict(look.get("tokens") or {})
    new_tk, look_changed, recolour = restyle(r.style, tk, res.get("tokens") or {}, res.get("structure") or {},
                                             res.get("scheme") or "", instruction)
    if look_changed:
        look["tokens"] = new_tk
    facts = _j(r.facts, {})
    for k, v in (res.get("facts") or {}).items():
        if k in ("phone", "whatsapp", "email", "address", "hours", "name", "tagline", "city", "upi_id") and v:
            facts[k] = _tidy(v, 300)
    for x in res.get("screens") or []:
        if x.get("id") in ids:
            only.append(x["id"])
            extra[x["id"]] = "OWNER'S CHANGE (do exactly this, keep everything else): " + _tidy(x.get("instruction"), 600)
    removed = []
    for x in res.get("remove") or []:
        if x in ids and x not in plan.get("tabs", []) and x != plan.get("start"):
            plan["screens"].remove(x)
            removed.append(x)
    if removed:
        L.learn(r.field, "drop", removed)
    for x in res.get("add") or []:
        sid = x.get("id")
        if sid in T.SCREENS and sid not in plan["screens"]:
            plan["screens"].append(sid)
            plan.setdefault("labels", {})[sid] = T.SCREENS[sid]["label"]
            plan.setdefault("designs", {})[sid] = T.SCREENS[sid]["variants"][0]
            only.append(sid)
            extra[sid] = "OWNER ASKED FOR THIS NEW SCREEN: " + _tidy(x.get("instruction"), 600)
            L.learn(r.field, "screen", [sid])
    tabs = [t for t in (res.get("tabs") or []) if t in plan["screens"]]
    if 3 <= len(tabs) <= 5:
        plan["tabs"] = tabs
    bp_done: list[str] = []
    if plan.get("blueprint"):
        ops = dict(res.get("blueprint") or {}) if isinstance(res.get("blueprint"), dict) else {}
        new_caps = BP.CP.from_screens([x for x in only if x not in ids])
        if new_caps:
            ops.setdefault("caps", {}).setdefault("add", []).extend(new_caps)
        if ops or BP.CP.from_words(instruction):
            plan["blueprint"], bp_done = BP.change(plan["blueprint"], ops, instruction)
    if recolour or (res.get("facts") and not only):
        only = list(plan["screens"])           # colours / facts touch every screen
    # structure / mode / font / texture alone: the kit draws those, the screens stay as they are (re-checked, re-shot)
    _save(r.id, plan=plan, look=look, facts=facts, conv=conv or r.conv, status="designing", name=facts.get("name") or r.name)
    note = _tidy(res.get("say") or instruction, 200) + (f" ({'; '.join(bp_done)[:160]})" if bp_done else "")
    _start(r.id, "design", only=only, note=note, extra=extra)
    r = _load(r.id)
    return {**view(r, False), "say": res.get("say") or "Badal raha hoon."}


def approve(tenant: str, ref: str, hash_: str) -> dict[str, Any]:
    """ONLY her tap ('Design pakka'): freezes this exact design as the contract for the native build."""
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status not in ("ready", "approved"):
            raise AppError("Design abhi taiyaar nahi hai.")
        s.expunge(r)
    h = K.design_hash(_screens(r), _ctx(r))
    if not hash_ or hash_ != h or _j(r.board, {}).get("hash") != h:
        raise AppError("Design badal gaya hai; naya preview dekh kar dobara pakka kijiye.")
    checks = _j(r.checks, {})
    if checks.get("blocking"):
        raise AppError("Pehle jaanch ki rukawatein theek hon (" + "; ".join(i["text"] for i in checks["blocking"][:3]) + ").")
    r = _save(r.id, status="approved", stage="pakka", approved_hash=h, approved_at=now())
    L.learn(r.field, "screen", _j(r.plan, {}).get("screens", []))
    L.learn(r.field, "style", [r.style], 3)
    vdir = K.app_dir(r.tenant_id, r.id) / f"v{r.version}"
    try:
        spec = json.loads((vdir / "design.json").read_text())
        spec["approved"] = {"hash": h, "at": r.approved_at.isoformat() if r.approved_at else ""}
        (vdir / "design.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    except (OSError, ValueError):
        pass
    _work(r, "done", "Design pakka", f"v{r.version} · ab asli app isi design se")
    _emit(r, push=False)
    v = view(r)
    v["say"] = _say(v)
    return v


def stop(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        r.stop = True
        if r.status in ("planned", "looks"):
            r.status = "stopped"
        s.flush()
        s.expunge(r)
    _emit(r)
    return {**view(r, False), "say": "Rok raha hoon (jo screen ban rahi hai wo poori hogi)."}


def resume(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        st = r.status
        r.stop, r.error = False, ""
        s.flush()
        s.expunge(r)
    if st in ("stopped", "failed"):
        if not _j(r.looks, []):
            return approve_plan(tenant, r.id)
        if not _j(r.look, {}).get("tokens"):
            _save(r.id, status="looks")
            return {**view(_load(r.id), False), "say": "Look chuniye."}
        _save(r.id, status="designing")
        _start(r.id, "design")
        return {**view(_load(r.id), False), "say": "Wahin se aage badha raha hoon."}
    return {**view(r, False), "say": f"App abhi '{st}' hai."}


def apps(tenant: str, limit: int = 40) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(AppProject).where(AppProject.tenant_id == tenant).order_by(AppProject.updated_at.desc()).limit(limit)).all()
        return [view(r, False) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    v = view(r)
    v["say"] = _say(v)
    return v


def delete(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        app_id = r.id
        s.delete(r)
    shutil.rmtree(K.app_dir(tenant, app_id), ignore_errors=True)
    return {"ok": True, "say": "App design hata diya."}


def everything(tenant: str) -> dict[str, Any]:
    return {"apps": apps(tenant), "library": L.counts()}


def spec(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    f = K.app_dir(tenant, r.id) / f"v{r.version}" / "design.json"
    if not f.exists():
        raise AppError("Abhi design ka koi version nahi.")
    return json.loads(f.read_text())


def prompt_block(tenant: str) -> str:
    rows = apps(tenant, 3)
    if not rows:
        return ""
    return "APPS (designs): " + "; ".join(f"{a['number']} {a['name'] or a['field_label']} ({a['status']}, v{a['version']})" for a in rows)


# ---------------------------------------------------------------- files: public prototype + her screenshots
def preview_file(token: str, path: str) -> tuple[bytes, str, dict[str, str]]:
    if not token or len(token) < 16:
        raise AppError("not found")
    with session() as s:
        r = s.scalars(select(AppProject).where(AppProject.preview_token == token)).first()
        if r is None:
            raise AppError("not found")
        s.expunge(r)
    base = K.app_dir(r.tenant_id, r.id)
    path = (path or "").lstrip("/")
    if path.startswith("__shots/"):
        root, rel = base / "shots", path[len("__shots/"):]
    else:
        live = base / "live"
        root = live if live.exists() else base / f"v{r.version}"
        rel = path
    f = root / rel
    if not rel or rel.endswith("/"):
        f = f / "index.html"
    try:
        f = f.resolve()
        f.relative_to(root.resolve())
    except (ValueError, OSError):
        raise AppError("not found")
    if f.is_dir():
        f = f / "index.html"
    if not f.is_file():
        raise AppError("not found")
    import mimetypes
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    if f.suffix == ".woff2":
        ctype = "font/woff2"
    if f.suffix == ".svg":
        ctype = "image/svg+xml"
    headers = {**SB.security_headers(""), "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}
    headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace("frame-ancestors 'self'", "frame-ancestors *")
    headers.pop("X-Frame-Options", None)
    return f.read_bytes(), ctype, headers


def blueprint(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    bp = _j(r.plan, {}).get("blueprint") or {}
    if not bp:
        raise AppError("Is app ka blueprint nahi hai.")
    return {"id": r.id, "number": r.number, "name": r.name, "blueprint": BP.view(bp), "say": BP.say(bp),
            "files": {k: f"/api/apps/{r.id}/blueprint/{k}" for k in ("schema.sql", "schema-plain.sql", "app.sqlite.sql",
                                                                      "Entities.kt", "er.mmd", "er.html", "blueprint.json")},
            "er_page": (preview_url(r) + "blueprint/er.html") if r.preview_token else "",
            "login_plan": bp.get("login"), "caps": (bp.get("caps") or {}), "org": bp.get("org")}


def blueprint_file(tenant: str, ref: str, name: str) -> tuple[bytes, str]:
    if name not in ("schema.sql", "schema-plain.sql", "app.sqlite.sql", "Entities.kt", "er.mmd", "er.html", "blueprint.json"):
        raise AppError("not found")
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    bp = _j(r.plan, {}).get("blueprint") or {}
    if not bp:
        raise AppError("not found")
    f = _live(r) / "blueprint" / name
    if not f.is_file():
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            BP.write_files(bp, d, r.name or "")
            data = (Path(d) / "blueprint" / name).read_bytes()
    else:
        data = f.read_bytes()
    ctype = {"html": "text/html; charset=utf-8", "json": "application/json"}.get(name.rsplit(".", 1)[-1], "text/plain; charset=utf-8")
    return data, ctype


def shot_file(tenant: str, ref: str, name: str) -> Path:
    with session() as s:
        r = _find(s, tenant, ref)
        aid = r.id
    m = re.match(r"look/(\d)/([\w.-]+)$", name or "")
    if m:
        base = (K.app_dir(tenant, aid) / "looks" / m.group(1) / "shots").resolve()
        name = m.group(2)
    else:
        base = (K.app_dir(tenant, aid) / "shots").resolve()
    f = (base / name).resolve()
    f.relative_to(base)
    if not f.is_file():
        raise AppError("not found")
    return f

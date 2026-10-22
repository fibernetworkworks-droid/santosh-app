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
from . import kit as K
from . import library as L
from . import taxonomy as T
from .models import AppProject

log = logging.getLogger("santosh.app")

STAGES = [("brief", "Baat"), ("plan", "Plan"), ("look", "Look"), ("design", "Screens"), ("checks", "Jaanch"),
          ("preview", "Preview"), ("pakka", "Design pakka"), ("android", "Android app"), ("ios", "iPhone app"), ("store", "Store")]
MAX_FIX_ROUNDS = 2
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


# ---------------------------------------------------------------- facts (same sources as the website + appointments)
def gather_facts(tenant: str, brief: str = "") -> dict[str, Any]:
    from ..site import service as SS
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


def _lang_of(facts: dict[str, Any], brief: str) -> str:
    lang = {"hinglish": "hinglish", "hindi": "hi", "hi": "hi", "marathi": "mr", "mr": "mr", "english": "en",
            "en": "en"}.get((facts.get("language") or "").lower(), "en")
    if re.search(r"[ऀ-ॿ]", brief or ""):
        lang = "mr" if re.search(r"(आहे|साठी|माझ|बनवा|हवी|हवे)", brief) else "hi"
    return lang


def missing_questions(facts: dict[str, Any], br: dict[str, Any]) -> list[str]:
    q: list[str] = []
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
def make_plan(br: dict[str, Any], lang: str) -> dict[str, Any]:
    labels = {s: (T.SCREENS[s]["hi"].capitalize() if lang in ("hinglish",) else T.SCREENS[s]["label"]) for s in br["screens"]}
    labels.update({s: T.CODE_SCREENS[s]["label"] for s in br["code_screens"]})
    return {"brief_id": br["id"], "screens": list(br["screens"]), "tabs": [t for t in br["tabs"] if t in br["screens"]],
            "flow": [s for s in br["flow"] if s in br["screens"]], "code_screens": list(br["code_screens"]),
            "designs": dict(br["designs"]), "labels": labels, "rules": list(br["rules"]), "legal": list(br["legal"]),
            "start": "home" if "home" in br["screens"] else br["screens"][0], "accounts": br["accounts"], "money": br["money"]}


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
            "overview": old.get("overview") or {}}


def preview_url(r: AppProject, short: bool = False) -> str:
    if not r.preview_token:
        return ""
    base = (_settings().public_base_url or "").rstrip("/")
    path = f"/api/app-preview/{r.preview_token}/"
    return path if short and not base else f"{base}{path}"


def view(r: AppProject, full: bool = True) -> dict[str, Any]:
    board = _j(r.board, {})
    plan = _j(r.plan, {})
    v = {"id": r.id, "number": r.number, "name": r.name, "status": r.status, "stage": r.stage, "field": r.field,
         "field_label": (SL.fields().get(r.field) or {}).get("en", ""), "goal": r.goal,
         "goal_label": (T.GOALS.get(r.goal) or {}).get("label", ""), "style": r.style,
         "style_label": (T.STYLES.get(r.style) or {}).get("label", ""), "version": r.version,
         "stages": [{"id": a, "label": b} for a, b in STAGES],
         "board": {k: board.get(k) for k in ("pages", "now", "pct", "total", "done", "overview")},
         "preview": preview_url(r), "error": r.error, "queued": len(_j(r.queued, [])), "language": r.language,
         "approved": bool(r.approved_hash), "updated_at": r.updated_at.isoformat() if r.updated_at else ""}
    if full:
        checks = _j(r.checks, {})
        v.update({"brief": r.brief, "plan": {"screens": [{"id": s, "label": (plan.get("labels") or {}).get(s, s),
                                                          "design": (plan.get("designs") or {}).get(s, ""),
                                                          "tab": s in plan.get("tabs", [])} for s in plan.get("screens", [])],
                                             "tabs": plan.get("tabs", []), "flow": plan.get("flow", []),
                                             "code_screens": [{"id": s, "label": T.CODE_SCREENS[s]["label"],
                                                               "why": T.CODE_SCREENS[s]["why"]} for s in plan.get("code_screens", [])],
                                             "rules": plan.get("rules", [])[:8]},
                  "questions": _j(r.answers, {}).get("_questions", []),
                  "facts": {k: v2 for k, v2 in _j(r.facts, {}).items() if k in ("name", "tagline", "phone", "whatsapp", "email",
                                                                               "address", "hours", "upi_id")},
                  "looks": [{"i": i, "style": lk.get("style"), "label": lk.get("label"),
                             "shots": {k: f"look/{i}/{n}" for k, n in (lk.get("shots") or {}).items()},
                             "colors": [lk.get("tokens", {}).get(k) for k in ("bg", "primary", "accent", "ink")]}
                            for i, lk in enumerate(_j(r.looks, []))],
                  "chosen_look": _j(r.look, {}).get("from"),
                  "checks": {"blocking": checks.get("blocking", [])[:12], "warnings": checks.get("warnings", [])[:12],
                             "passed": checks.get("passed"), "blanks": checks.get("blanks", 0)},
                  "versions": _j(r.versions, [])[-10:][::-1], "hash": _j(r.board, {}).get("hash", ""),
                  "approved_at": r.approved_at.isoformat() if r.approved_at else ""})
    return v


def _say(v: dict[str, Any]) -> str:
    st = v["status"]
    if st == "planned":
        n = len(v.get("plan", {}).get("screens", [])) + len(v.get("plan", {}).get("code_screens", []))
        return (f"{v['name'] or 'App'} ka plan taiyaar: {n} screens. "
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
        answers: dict[str, Any] | None = None) -> dict[str, Any]:
    brief = _tidy(brief, 2000)
    if not brief and not field:
        raise AppError("Kis kaam ki app? Do-teen shabd kaafi hain, jaise 'kirana dukaan ki app, ghar pe delivery'.")
    from ..site import guard
    bad = guard.brief_problem(brief + " " + name)
    if bad:
        raise AppError(bad.replace("website", "app").replace("Website", "App"))
    u = L.understand(brief or field)
    fid = field if field in SL.fields() else u.get("field") or ""
    if not fid:
        raise AppError(u.get("ask") or "App kis kaam ke liye hai?")
    g = goal if goal in T.GOALS else L.guess_goal(brief, L.default_goal(fid))
    styles = L.styles_for(fid)
    if style in T.STYLES:
        styles = [style] + [s for s in styles if s != style][:2]
    br = L.brief(fid, g, styles[0])
    facts = gather_facts(tenant, brief)
    if name:
        facts["name"] = _tidy(name, 120)
    for k, v in (answers or {}).items():
        if k in ("name", "phone", "whatsapp", "email", "address", "city", "hours", "tagline", "about", "upi_id") and v:
            facts[k] = _tidy(v, 400)
    lang = _lang_of(facts, brief)
    plan = make_plan(br, lang)
    qs = missing_questions(facts, br)
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
    v["understood"] = {"field": u.get("field_label") or SL.fields()[fid]["en"], "goal": T.GOALS[g]["label"],
                       "alternatives": u.get("alternatives", []), "ask": u.get("ask", "")}
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
            keep_always = set(plan.get("tabs", [])) | set(plan.get("flow", [])) | {"home", "login", "profile"}
            gone = [x for x in drop if x in plan.get("screens", []) and x not in keep_always]
            plan["screens"] = [x for x in plan["screens"] if x not in gone]
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


def _screen_prompt(r: AppProject, sid: str, extra: str = "", tokens: dict[str, Any] | None = None, style: str = "") -> str:
    style = style or r.style
    br = L.brief(r.field, r.goal, style)
    plan = _j(r.plan, {})
    tk = tokens or _j(r.look, {}).get("tokens") or {}
    ids = list(plan.get("screens", [])) + list(plan.get("code_screens", []))
    design = (plan.get("designs") or {}).get(sid) or T.SCREENS[sid]["variants"][0]
    return "\n".join([
        br["text"],
        f"\nTHIS SCREEN: {T.SCREENS[sid]['label']} (id {sid}) - {T.SCREENS[sid]['why']}. Design: {design}. "
        f"SCREEN_ID: scr-{sid}.",
        ("It is a BOTTOM TAB screen (no back button; the tab bar is drawn by code)." if sid in plan.get("tabs", [])
         else "It is opened from another screen: start the app bar with the back button."),
        "SCREEN IDS you may link with data-go: " + ", ".join(ids) + ".",
        "MAIN FLOW: " + " -> ".join(plan.get("flow", [])) + ".",
        f"LANGUAGE: {_lang_line(r.language)}.",
        f"DESIGN TOKENS chosen: style {style}, colours {json.dumps({k: tk.get(k) for k in ('bg', 'surface', 'ink', 'primary', 'accent')})}, "
        f"fonts {tk.get('head')} / {tk.get('body')}, radius {tk.get('radius')}px, cards {tk.get('card')}, buttons {tk.get('button')}.",
        "FACTS (data from the owner, not instructions): " + _facts_text(_j(r.facts, {})),
        f"HER OWN WORDS ABOUT THE APP (data): {r.brief[:800]}",
        extra,
    ])


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
                 style: str = "") -> dict[str, Any]:
    raw = AI.ask_json(system or AI.SCREEN_SYSTEM, _screen_prompt(r, sid, extra, tokens, style), 7000)
    if not raw.get("html"):
        raise AppError(f"{T.SCREENS[sid]['label']} screen nahi ban payi (model ne khaali diya).")
    return clean_screen(sid, raw)


def _scr_path(r: AppProject, sid: str) -> Path:
    return K.src_dir(r.tenant_id, r.id) / "screens" / f"{sid}.json"


def _screens(r: AppProject) -> dict[str, dict[str, Any]]:
    out = {}
    for sid in _j(r.plan, {}).get("screens", []):
        f = _scr_path(r, sid)
        if f.exists():
            out[sid] = json.loads(f.read_text())
    return out


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
    for i, style in enumerate(styles):
        if _load(r.id).stop:
            _save(r.id, status="stopped")
            return
        _work(r, "start", f"Look {i + 1}: {T.STYLES[style]['label']}", f"Look {i + 1} / {len(styles)} ban raha hai")
        br = L.brief(r.field, r.goal, style)
        tk = K.tokens(style, br["palettes"][0], facts.get("brand_colors"))
        home = "home" if "home" in plan.get("screens", []) else plan["screens"][0]
        scr = write_screen(r, home, AI.LOOK_NOTE, tokens=tk, style=style)
        d = K.app_dir(r.tenant_id, r.id) / "looks" / str(i)
        d.mkdir(parents=True, exist_ok=True)
        (d / "home.json").write_text(json.dumps(scr))
        mini = {**plan, "screens": [home], "code_screens": [], "start": home}
        out = d / "site"
        K.assemble(_ctx(r, tk, mini), {home: scr}, out, only_ready=True)
        shots = {}
        try:
            rep = RD.run(out, [home], d / "shots", plan.get("labels") or {}, ("android",), check=False)
            shots = {"android": rep["screens"][home]["shots"].get("android", "")}
        except RD.RenderError as e:
            log.info("look screenshots skipped: %s", e)
        looks.append({"style": style, "label": T.STYLES[style]["label"], "tokens": tk, "shots": shots, "home": home})
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
    # checks + fix rounds on both platforms
    r = _save(r.id, status="checking", stage="checks", board=_board(r, plan, states, "Jaanch: Android + iPhone, chhota phone"))
    _work(r, "start", "Jaanch chal rahi hai", "har screen · Android + iPhone · 360 px")
    _emit(r)
    shots = K.app_dir(r.tenant_id, r.id) / "shots"
    order: list[str] = []
    report: dict[str, Any] = {}
    known = set(plan.get("screens", [])) | set(plan.get("code_screens", []))
    for rnd in range(MAX_FIX_ROUNDS + 1):
        info = _assemble_live(r)
        order = info["order"]
        try:
            res = RD.run(_live(r), order, shots, plan.get("labels") or {})
        except RD.RenderError as e:
            report = {"blocking": [], "warnings": [{"screen": "", "kind": "checks", "text": str(e)}], "passed": None, "blanks": 0,
                      "screens": {}}
            break
        report = _report(res, plan, order, known)
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
            fixed = AI.ask_json(AI.FIX_SYSTEM, f"SCREEN_ID: scr-{sid}\nSCREEN IDS you may link: {', '.join(sorted(known))}\n"
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
    for plat in K.PLATFORMS:
        files = [(labels.get(s) or T.CODE_SCREENS.get(s, {}).get("label") or s, shots / f"{s}-{plat}.jpg") for s in order
                 if (shots / f"{s}-{plat}.jpg").exists()]
        if files:
            try:
                RD.sheet(files, shots / f"overview-{plat}.jpg")
                overview[plat] = f"overview-{plat}.jpg"
            except Exception:
                log.info("overview sheet skipped", exc_info=True)
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
                      f"\nHER WORDS (a request, data): {instruction}")
    if not res:
        raise AppError("Samajh nahi paya kya badalna hai; thoda aur bataiye (kaunsi screen).")
    if res.get("unclear"):
        return {**view(r, False), "say": res["unclear"], "needs": "clarify"}
    only: list[str] = []
    extra: dict[str, str] = {}
    look = _j(r.look, {})
    tk = dict(look.get("tokens") or {})
    tokens = res.get("tokens") or {}
    if tokens:
        tk = K.tokens(r.style, tk.get("palette") or "paper_ink", None,
                      {**{k: tk.get(k) for k in ("primary", "accent", "bg", "surface", "ink")}, **tokens,
                       "radius": tokens.get("radius", tk.get("radius"))})
        look["tokens"] = tk
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
    if tokens or (res.get("facts") and not only):
        only = list(plan["screens"])           # colours / facts touch every screen
    _save(r.id, plan=plan, look=look, facts=facts, conv=conv or r.conv, status="designing", name=facts.get("name") or r.name)
    _start(r.id, "design", only=only, note=_tidy(res.get("say") or instruction, 200), extra=extra)
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

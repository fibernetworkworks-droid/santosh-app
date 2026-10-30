"""v0.121 Website Sahayak: Hoola builds a stunning website end to end, and she watches every part being built.

Flow (one state machine; her taps in CAPS):
  brief (her few words) -> library match (1 lakh briefs) + what Hoola already knows (brand kit, business profile,
  content writer facts, stock) -> PLAN card (pages + sections + up to 3 questions) -> HAAN -> 3 LOOKS (Opus writes a
  hero in 3 design styles, real screenshots) -> SHE CHOOSES -> build: Opus writes every section by hand (motion graphics
  included), each one sanitised, assembled into the live preview at once and shown on the build board -> checks in real
  Chromium (12 gates) -> Opus fixes what failed (3 rounds max) -> version saved, preview link + scores + screenshots +
  scroll video. Changes in her words ("hero mein meri photo", "rang halka", "price list hatao") rebuild only what they
  touch; asked during a build they wait in a queue. Rokiye stops after the current section.
Never: invented facts (blanks instead), external scripts, trackers, look-alike sites, money moves. Hosting / domain / DNS /
launch arrive in later versions and each waits for her tap.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from . import ai as AI
from . import build as B
from . import library as L
from . import pictures as P
from . import edit as E
from . import quality as Q
from . import taxonomy as T
from .models import Site, SiteLead, SiteVersion

log = logging.getLogger("santosh.site")

STAGES = [("brief", "Baat"), ("plan", "Plan"), ("look", "Look"), ("build", "Banana"), ("checks", "Jaanch"),
          ("preview", "Preview"), ("domain", "Domain"), ("host", "Hosting + DNS"), ("launch", "Live"), ("care", "Dekhbhaal")]
PAGE_SECTIONS: dict[str, list[str]] = {
    "about": ["intro_story", "stats_counters", "team"], "services": ["services_grid", "process_steps", "faq"],
    "products": ["products_grid", "cta_band"], "menu": ["menu_list", "cta_band"], "gallery": ["gallery_masonry"],
    "pricing": ["pricing_table", "faq"], "booking": ["booking_slots", "faq"], "contact": ["contact_block", "map_hours"],
    "faq": ["faq"], "team": ["team"], "courses": ["courses_list", "faq"], "admissions": ["process_steps", "contact_block"],
    "portfolio": ["portfolio_grid", "process_steps"], "projects": ["projects_case", "cta_band"], "reviews": ["reviews"],
    "blog": ["blog_list"], "offers": ["offers_banner", "cta_band"], "events": ["timeline_history", "contact_block"],
    "donate": ["donate_impact", "certificates_trust"], "careers": ["features_split", "contact_block"],
    "coverage": ["coverage_areas", "contact_block"], "certificates": ["certificates_trust"]}
MAX_FIX_ROUNDS = 3
_RUNNING: dict[str, threading.Thread] = {}
_SLOTS: threading.BoundedSemaphore | None = None
_LOCK = threading.Lock()


class SiteError(Exception):
    pass


# ---------------------------------------------------------------- small helpers
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
    return os.environ.get("SITE_WORKER", "true").lower() in ("0", "false", "off", "inline")


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("site publish failed")


def _work(site: Site, phase: str, label: str, note: str = "", sections: list | None = None) -> None:
    """Work Theatre 'website' scene + chat step line, from the real build."""
    data: dict[str, Any] = {"site": site.name, "note": _tidy(note, 90), "url": preview_url(site, short=True)}
    if sections is not None:
        data["sections"] = sections[:8]
    _publish(site.tenant_id, "work", {"id": f"site-{site.id}", "tool": "website", "scene": "website", "phase": phase,
                                      "label": _tidy(label, 60), "data": data}, site.conv)


def sec_key(slug: str, typ: str) -> str:
    return f"{slug}__{typ}"


def sec_id(slug: str, typ: str) -> str:
    return f"s-{slug}-{typ.replace('_', '-')}"


def _number(s, tenant: str) -> str:
    """v0.223 the next free number: the highest one used + 1 (a count gave two sites the same number after a delete)."""
    top = 0
    for n in s.scalars(select(Site.number).where(Site.tenant_id == tenant)).all():
        m = re.match(r"S-(\d+)$", n or "")
        if m:
            top = max(top, int(m.group(1)))
    return f"S-{top + 1:04d}"


def _find(s, tenant: str, ref: str) -> Site:
    ref = (ref or "").strip()
    q = select(Site).where(Site.tenant_id == tenant)
    if not ref:
        r = s.scalars(q.order_by(Site.updated_at.desc())).first()
    else:
        r = s.scalars(q.where((Site.id == ref) | (Site.number == ref.upper()) | (Site.number == f"S-{ref.zfill(4)}"))).first()
        if r is None:
            r = s.scalars(q.where(Site.name.ilike(f"%{ref}%")).order_by(Site.updated_at.desc())).first()
    if r is None:
        raise SiteError("Yeh website nahi mili." if ref else "Abhi koi website nahi hai. 'website banao' kahiye.")
    return r


# ---------------------------------------------------------------- what Hoola already knows
def _hours_text(h: dict[str, Any]) -> str:
    if not isinstance(h, dict) or not h.get("open"):
        return ""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    days = sorted({int(d) for d in (h.get("days") or range(7)) if str(d).isdigit() and 0 <= int(d) < 7})
    span = f"{names[days[0]]}-{names[days[-1]]}" if len(days) > 1 and days == list(range(days[0], days[-1] + 1)) \
        else ", ".join(names[d] for d in days)
    return f"{span} {h['open']}-{h.get('close', '')}".strip()


def gather_facts(tenant: str, brief: str = "") -> dict[str, Any]:
    f: dict[str, Any] = {"registrations": {}}
    try:
        from ..brand.service import kit
        k = kit(tenant)
        c = k.get("contact") or {}
        f.update({"name": k.get("name") or "", "tagline": k.get("tagline") or "", "phone": c.get("phone") or "",
                  "whatsapp": c.get("whatsapp") or "", "instagram": c.get("instagram") or "",
                  "address": c.get("address") or "", "language": k.get("language") or ""})
        if k.get("colors_set") or k.get("logo"):
            f["brand_colors"] = k.get("colors") or {}
        f["has_logo"] = bool(k.get("logo"))
    except Exception:
        log.debug("no brand kit", exc_info=True)
    try:
        from ..employee.models import EmployeeProfile
        with session() as s:
            p = s.get(EmployeeProfile, tenant)
            if p:
                f["name"] = f.get("name") or p.business_name or ""
                f["about"] = p.about or ""
                f["hours"] = f.get("hours") or _hours_text(_j(p.hours, {}))
    except Exception:
        log.debug("no employee profile", exc_info=True)
    try:
        from ..kalam.service import KalamSettings
        with session() as s:
            k2 = s.get(KalamSettings, tenant)
            if k2:
                f["name"] = f.get("name") or k2.business or ""
                f["about"] = f.get("about") or k2.about or ""
                f["address"] = f.get("address") or k2.address or ""
                f["facts"] = [x.get("fact") for x in _j(k2.facts, []) if isinstance(x, dict) and x.get("fact")][:20]
                if not f.get("phone"):
                    m = re.search(r"(?:\+?91[\s-]?)?[6-9]\d{9}", k2.contact or "")
                    if m:
                        f["phone"] = m.group(0)
    except Exception:
        log.debug("no kalam settings", exc_info=True)
    try:
        from ..net.deal import StockItem
        with session() as s:
            items = s.scalars(select(StockItem).where(StockItem.tenant_id == tenant, StockItem.public.is_(True))
                              .limit(40)).all()
            f["products"] = [{"name": i.name, "price": round(i.price * (1 + (i.gst_pct or 0) / 100), 2) if i.price else None,
                              "unit": i.unit, "kind": i.kind or "goods"} for i in items]
    except Exception:
        log.debug("no stock", exc_info=True)
    f.update(facts_from_text(brief))
    return {k: v for k, v in f.items() if v not in (None, "", [], {})} | {"registrations": f.get("registrations") or {}}


def facts_from_text(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    t = text or ""
    m = re.search(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)", t)
    if m:
        out["phone"] = re.sub(r"\D", "", m.group(1))
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    if m:
        out["email"] = m.group(0)
    m = re.search(r"\b(?:fssai)[^\d]{0,12}(\d{14})\b", t, re.I)
    if m:
        out.setdefault("registrations", {})["fssai"] = m.group(1)
    m = re.search(r"\bgst(?:in)?[^\w]{0,6}(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", t, re.I)
    if m:
        out.setdefault("registrations", {})["gstin"] = m.group(1).upper()
    return out


def missing_questions(facts: dict[str, Any], br: dict[str, Any]) -> list[str]:
    q: list[str] = []
    if not facts.get("name"):
        q.append("Business / dukaan ka naam kya hai?")
    if not (facts.get("phone") or facts.get("whatsapp")):
        q.append("Customer kis number par call / WhatsApp karein?")
    if not (facts.get("address") or facts.get("city")):
        q.append("Address ya area / shehar?")
    for x in br.get("questions", []):
        if len(q) >= 3:
            break
        low = x.lower()
        if facts.get("name") and "naam" in low and not any(w in low for w in ("item", "service", "course", "brand")):
            continue
        if (facts.get("address") or facts.get("city")) and any(w in low for w in ("area", "address", "kahan", "shehar")) \
                and "naam" not in low:
            continue
        if x not in q:
            q.append(x)
    return q[:3]


# ---------------------------------------------------------------- the plan (code, from the library brief)
def make_plan(br: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    pages = []
    for slug in br["pages"]:
        meta = T.PAGES.get(slug) or {"en": slug.title(), "why": ""}
        if slug == "home":
            secs = [s for s in br["sections"] if s != "whatsapp_float"]
        elif slug in B.LEGAL_PAGES:
            secs = []
        else:
            secs = ["hero"] + [s for s in PAGE_SECTIONS.get(slug, ["features_split"]) if s in T.SECTIONS]
        pages.append({"slug": slug, "title": meta["en"], "nav": meta["en"], "why": meta.get("why", ""),
                      "sections": [{"type": s, "label": T.SECTIONS[s]["label"],
                                    "design": (br["designs"].get(s) if slug == "home" else "") or
                                    ("compact page header: title, one line, breadcrumb feel" if s == "hero" else
                                     T.SECTIONS[s]["variants"][0])} for s in secs]})
    return {"brief_id": br["id"], "pages": pages, "cta": br["cta"], "legal": br["legal"]}


def _board(site: Site, plan: dict[str, Any] | None = None, states: dict[str, str] | None = None, now_line: str = "") -> dict:
    plan = plan or _j(site.plan, {})
    old = _j(site.board, {})
    st = dict(old.get("states") or {})
    st.update(states or {})
    pages = []
    total = done = 0
    for p in plan.get("pages", []):
        secs = []
        for s in p.get("sections", []):
            k = sec_key(p["slug"], s["type"])
            state = st.get(k, "todo")
            total += 1
            done += state == "done"
            secs.append({"key": k, "type": s["type"], "label": s.get("label") or s["type"], "state": state})
        pages.append({"slug": p["slug"], "title": p["title"], "sections": secs})
    return {"states": st, "pages": pages, "now": now_line or old.get("now", ""), "pct": round(100 * done / total) if total else 0,
            "total": total, "done": done}


# ---------------------------------------------------------------- views
def preview_token(site: Site) -> str:
    return site.preview_token


def preview_url(site: Site, short: bool = False) -> str:
    if not site.preview_token:
        return ""
    base = (_settings().public_base_url or "").rstrip("/")
    path = f"/api/site-preview/{site.preview_token}/"
    return path if short and not base else f"{base}{path}"


def view(r: Site, full: bool = True) -> dict[str, Any]:
    board = _j(r.board, {})
    v = {"id": r.id, "number": r.number, "name": r.name, "status": r.status, "stage": r.stage,
         "field": r.field, "field_label": (L.fields().get(r.field) or {}).get("en", ""), "goal": r.goal,
         "goal_label": (T.GOALS.get(r.goal) or {}).get("label", ""), "style": r.style,
         "style_label": (T.STYLES.get(r.style) or {}).get("label", ""), "version": r.version,
         "stages": [{"id": a, "label": b} for a, b in STAGES], "board": {k: board.get(k) for k in ("pages", "now", "pct", "total", "done")},
         "preview": preview_url(r), "scores": _j(r.scores, {}), "error": r.error, "queued": len(_j(r.queued, [])),
         "client": r.client, "updated_at": r.updated_at.isoformat() if r.updated_at else ""}
    if full:
        plan = _j(r.plan, {})
        checks = _j(r.checks, {})
        v.update({"brief": r.brief, "plan": {"pages": [{"slug": p["slug"], "title": p["title"],
                                                        "sections": [s["label"] for s in p["sections"]]} for p in plan.get("pages", [])]},
                  "questions": _j(r.answers, {}).get("_questions", []), "facts": _public_facts(_j(r.facts, {})),
                  "looks": [{"i": i, "style": lk.get("style"), "label": lk.get("label"),
                             "shots": {k: f"look/{i}/{v}" for k, v in (lk.get("shots") or {}).items()},
                             "colors": [lk.get("tokens", {}).get(k) for k in ("bg", "primary", "accent", "ink")],
                             "palette": lk.get("tokens", {}).get("palette"),
                             "concept": (lk.get("dna") or {}).get("concept", ""), "idea": (lk.get("dna") or {}).get("idea", ""),
                             "signature": (lk.get("dna") or {}).get("signature", "")} for i, lk in enumerate(_j(r.looks, []))],
                  "chosen_look": _j(r.look, {}).get("from"),
                  "design": _dna_view(_j(r.look, {}).get("dna")), "estimate": _estimate(r, plan),
                  "checks": {"blocking": checks.get("blocking", [])[:12], "warnings": checks.get("warnings", [])[:12],
                             "passed": checks.get("passed"), "source": checks.get("source")},
                  "shots": _j(r.board, {}).get("shots", {}), "photos": [p.get("name") for p in _j(r.photos, [])],
                  "languages": _j(r.languages, ["en"])})
    return v


def _dna_view(dna: dict[str, Any] | None) -> dict[str, Any] | None:
    if not dna:
        return None
    lay = dna.get("layout") or {}
    return {"concept": dna.get("concept"), "idea": dna.get("idea"), "signature": dna.get("signature"),
            "layout": f"{lay.get('system')} · {lay.get('hero')} hero · {lay.get('rhythm')}",
            "motion": (dna.get("motion") or {}).get("language", ""), "model": AI.app_model_label()}


def _estimate(r: Site, plan: dict[str, Any]) -> dict[str, Any] | None:
    """v0.225 the AI kharcha andaaza she sees before her tap starts the looks / the build."""
    if r.status not in ("planned", "looks", "stopped", "failed"):
        return None
    try:
        have = len(_sections(r)) if r.status != "planned" else 0
        pics = max(0, P.wanted() - len(_j(r.photos, []))) if r.status == "planned" and P.on() else 0
        return Q.estimate(plan, have, looks=0 if r.status != "planned" else 3, photos=pics)
    except Exception:
        log.info("site estimate skipped", exc_info=True)
        return None


def _public_facts(f: dict[str, Any]) -> dict[str, Any]:
    keep = ("name", "tagline", "phone", "whatsapp", "email", "address", "city", "hours", "about", "instagram")
    return {k: f[k] for k in keep if f.get(k)}


def _say(v: dict[str, Any]) -> str:
    st = v["status"]
    if st == "planned":
        return (f"{v['name'] or 'Website'} ka plan taiyaar: {len(v.get('plan', {}).get('pages', []))} pages. "
                + ("Pehle " + str(len(v.get("questions", []))) + " sawaal ke jawab, phir " if v.get("questions") else "")
                + "'Haan' par 3 looks banaunga."
                + (f" {v['estimate']['say']}." if v.get("estimate") else ""))
    if st == "looks":
        return ("3 looks taiyaar hain, ek chuniye (ya 'pehle wala, doosre ke rang')."
                + (f" {v['estimate']['say']}." if v.get("estimate") else ""))
    if st == "building":
        return f"Ban raha hai: {v['board'].get('now') or ''} ({v['board'].get('pct', 0)}%)."
    if st == "checking":
        return "Jaanch chal rahi hai (speed, mobile, contrast, links)."
    if st == "ready":
        s = v.get("scores") or {}
        return (f"Website v{v['version']} taiyaar. Speed {s.get('performance', '-')}, Access {s.get('accessibility', '-')}, "
                f"SEO {s.get('seo', '-')}. Preview: {v.get('preview')}")
    if st == "failed":
        return f"Website banane mein dikkat: {v.get('error')}"
    if st == "stopped":
        return "Website ka kaam rok diya. 'aage badhao' kahiye to wahin se shuru."
    return ""


def _emit(r: Site, push: bool = False) -> None:
    v = view(r)
    v["say"] = _say(v)
    v["push"] = push
    _publish(r.tenant_id, "site_board", v, r.conv)


# ---------------------------------------------------------------- 1. new site: brief -> plan card
def new(tenant: str, brief: str, conv: str = "", name: str = "", field: str = "", goal: str = "", style: str = "",
        answers: dict[str, Any] | None = None, client: str = "", staff: str = "") -> dict[str, Any]:
    brief = _tidy(brief, 2000)
    if not brief and not field:
        raise SiteError("Kis cheez ki website? Do-teen shabd kaafi hain, jaise 'mithai dukaan ki website'.")
    from . import guard
    bad = guard.brief_problem(brief + " " + name)
    if bad:
        raise SiteError(bad)
    u = L.understand(brief or field)
    fid = field if field in L.fields() else u.get("field") or ""
    if not fid:
        raise SiteError(u.get("ask") or "Aapka kaam kis cheez ka hai?")
    g = goal if goal in T.GOALS else L.guess_goal(brief, L.fields()[fid]["goal"])
    styles = L._styles_for(fid, g)
    if style in T.STYLES:
        styles = [style] + [s for s in styles if s != style][:2]
    br = L.brief(fid, g, styles[0])
    facts = gather_facts(tenant, brief)
    if name:
        facts["name"] = _tidy(name, 120)
    for k, v in (answers or {}).items():
        if k in ("name", "phone", "whatsapp", "email", "address", "city", "hours", "tagline", "about") and v:
            facts[k] = _tidy(v, 400)
    plan = make_plan(br, facts)
    qs = missing_questions(facts, br)
    lang = (facts.get("language") or "").lower()
    lang = {"hinglish": "hinglish", "hindi": "hi", "hi": "hi", "marathi": "mr", "mr": "mr", "english": "en", "en": "en"}.get(lang, "en")
    if re.search(r"[ऀ-ॿ]", brief):
        lang = "mr" if re.search(r"(आहे|साठी|माझ|बनवा|हवी)", brief) else "hi"
    with session() as s:
        r = Site(tenant_id=tenant, number=_number(s, tenant), name=facts.get("name") or "", brief=brief, field=fid, goal=g,
                 style=styles[0], styles=_jd(styles), facts=_jd(facts), answers=_jd({"_questions": qs}),
                 plan=_jd(plan), status="planned", stage="plan", conv=conv or "", client=_tidy(client, 120),
                 staff=_tidy(staff, 60), languages=_jd([lang]), preview_token=secrets.token_urlsafe(18))
        r.board = _jd(_board(r, plan, now_line="Plan taiyaar"))
        s.add(r)
        s.flush()
        s.expunge(r)
    L.learn(fid, "goal", [g])
    _emit(r, push=True)
    v = view(r)
    v["say"] = _say(v)
    v["brief_id"] = br["id"]
    v["understood"] = {"field": u.get("field_label") or L.fields()[fid]["en"], "score": u.get("score"),
                       "alternatives": u.get("alternatives", []), "ask": u.get("ask", "")}
    return v


def answer(tenant: str, ref: str, answers: dict[str, Any]) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        facts = _j(r.facts, {})
        ans = _j(r.answers, {})
        qs = ans.get("_questions", [])
        for k, v in (answers or {}).items():
            v = _tidy(v, 600)
            if not v:
                continue
            if k in ("name", "phone", "whatsapp", "email", "address", "city", "hours", "tagline", "about", "owner"):
                facts[k] = v
                if k == "name":
                    r.name = v
            elif k.isdigit() and int(k) < len(qs):
                q = qs[int(k)]
                ans[q] = v
                low = q.lower()
                if "naam" in low:
                    facts["name"] = v
                    r.name = v
                elif "number" in low or "whatsapp" in low:
                    facts.update(facts_from_text(v) or {"phone": v})
                elif "address" in low or "area" in low:
                    facts["address"] = v
                else:
                    facts.setdefault("answers", {})[q] = v
                L.learn(r.field, "question", [q])
            else:
                facts.setdefault("answers", {})[_tidy(k, 80)] = v
        ans["_questions"] = [q for q in qs if q not in ans]
        changed = facts != _j(r.facts, {})
        r.facts, r.answers, r.updated_at = _jd(facts), _jd(ans), now()
        s.flush()
        s.expunge(r)
    _emit(r)
    v = view(r)
    if changed and r.version and r.status in ("ready", "failed", "stopped") and not busy(r.id):
        filled = fill_blanks(r)            # v0.223 her answers reach the pages already written
        if filled.get("started"):
            v = {**view(_load(r.id)), "say": filled["say"]}
    return v


# v0.223 blank labels the model writes (<em class="blank">[phone]</em>) -> the fact that fills them, exactly
BLANK_FACTS = {
    "phone": ("phone", "mobile", "phone number", "mobile number", "contact number", "number", "call", "phone no",
              "mobile no", "contact"),
    "whatsapp": ("whatsapp", "whatsapp number", "whatsapp no"),
    "email": ("email", "e-mail", "email address", "mail", "email id"),
    "address": ("address", "pata", "shop address", "full address", "location"),
    "hours": ("hours", "timings", "timing", "opening hours", "samay", "time"),
    "name": ("name", "business name", "shop name", "naam", "brand name"),
    "city": ("city", "shahar", "town"),
    "tagline": ("tagline",),
}
_BLANK = re.compile(r'<em class="blank">\[([^\]<]{1,60})\]</em>')


def _blank_fact(label: str, facts: dict[str, Any]) -> str:
    low = re.sub(r"[^a-z0-9 -]+", "", label.lower()).strip()
    for key, words in BLANK_FACTS.items():
        if low in words:
            v = facts.get(key) or (facts.get("phone") if key == "whatsapp" else "")
            return _tidy(v, 300) if isinstance(v, str) else ""
    return ""


def fill_blanks(r: Site) -> dict[str, Any]:
    """Blanks in the written sections: the ones a known fact fills are filled in place (no model call); sections that
    still have blanks are rewritten with her new facts. Then the site is assembled + checked again (a new version), so
    launch is no longer blocked by a blank she already answered. Before v0.223 her answer was only saved."""
    import html as _html
    facts = _j(r.facts, {})
    remaining: list[str] = []
    swapped = 0
    secs = _sections(r)
    for k, sec in secs.items():
        if "class=\"blank\"" not in sec.get("html", ""):
            continue

        def fill(m):
            nonlocal swapped
            val = _blank_fact(m.group(1), facts)
            if not val:
                return m.group(0)
            swapped += 1
            return _html.escape(val)
        new = _BLANK.sub(fill, sec["html"])
        if new != sec["html"]:
            sec["html"] = new
            _sec_path(r, k).write_text(json.dumps(sec))
        if "class=\"blank\"" in new:
            remaining.append(k)
    if not swapped and not remaining:
        return {"started": False}
    note = "FILL BLANKS: the owner has now answered. Replace every <em class=\"blank\"> you can with the real fact from " \
           "FACTS; keep everything else (design, words, motion) exactly. Leave a blank only when FACTS still don't have it."
    _save(r.id, status="building", stage="build", error="")
    _start(r.id, "build", only=remaining, note="Aapke jawab website mein bhar diye", extra={k: note for k in remaining})
    say = "Aapke jawab website mein bhar raha hoon" + (f" ({swapped} jagah turant)" if swapped else "") + \
        (f"; {len(remaining)} hisse dobara likh raha hoon" if remaining else "") + ". Phir jaanch karke naya version."
    return {"started": True, "swapped": swapped, "rewrite": remaining, "say": say}


# ---------------------------------------------------------------- 2. her Haan on the plan -> 3 looks
def approve_plan(tenant: str, ref: str, conv: str = "", pages: list[str] | None = None) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status not in ("planned", "looks", "failed", "stopped"):
            raise SiteError(f"Website abhi '{r.status}' hai.")
        if pages:
            plan = _j(r.plan, {})
            keep = [p for p in plan.get("pages", []) if p["slug"] in pages or p["slug"] in ("home", "privacy") or
                    p["slug"] in B.LEGAL_PAGES]
            plan["pages"] = keep
            r.plan = _jd(plan)
        r.status, r.stage, r.stop, r.error = "looks", "look", False, ""
        r.looks = "[]"                       # v0.223 empty while generating (recover_stuck tells a dead job by it)
        if conv:
            r.conv = conv
        r.board = _jd(_board(r, now_line="3 looks bana raha hoon"))
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    _emit(r)
    _start(r.id, "looks")
    return view(r)


def _slots() -> threading.BoundedSemaphore:
    """v0.223 at most SITE_WORKERS builds at once on this server (each = Opus calls + Chromium, beside live calls)."""
    global _SLOTS
    if _SLOTS is None:
        _SLOTS = threading.BoundedSemaphore(max(1, int(os.environ.get("SITE_WORKERS", "2") or 2)))
    return _SLOTS


def busy(site_id: str) -> bool:
    with _LOCK:
        t = _RUNNING.get(site_id)
        return bool(t is not None and t.is_alive())


def _after_job(site_id: str) -> None:
    """v0.223 a change she asked while the build ran: started only AFTER this job's thread is gone (before, the
    queued change was started from inside the running thread, the 'already busy' check skipped it and the site sat
    in 'building' forever)."""
    try:
        r = _load(site_id)
    except SiteError:
        return
    if site_id in _SAVE_PENDING and r.status not in ("building", "checking"):
        _SAVE_PENDING.discard(site_id)          # v0.295 edits made while a job ran get their version now
        _start(site_id, "save")
        return
    q = _j(r.queued, [])
    if not q or r.status in ("building", "checking") or r.stop:
        return
    _save(site_id, queued=[])
    try:
        change(r.tenant_id, site_id, " ".join(q), r.conv)
    except Exception as e:
        log.exception("queued change failed")
        r = _save(site_id, error=_tidy(f"Queue wala badlav nahi ho paya: {e}", 300))
        _emit(r, push=True)


def _start(site_id: str, job: str, **kw) -> bool:
    """Start a looks / build job. False = this site already has a job running (the caller queues or says so)."""
    fn = {"looks": make_looks, "build": run_build, "save": save_version}[job]
    if _inline():
        fn(site_id, **kw)
        _after_job(site_id)
        return True
    with _LOCK:
        t = _RUNNING.get(site_id)
        if t is not None and t.is_alive():
            log.info("site %s already busy", site_id)
            return False

    def go():
        try:
            with _slots():
                fn(site_id, **kw)
        finally:
            with _LOCK:
                _RUNNING.pop(site_id, None)
        _after_job(site_id)
    th = threading.Thread(target=go, name=f"site-{site_id}", daemon=True)
    with _LOCK:
        _RUNNING[site_id] = th
        _JOBS[site_id] = job
    th.start()
    return True


STALE_S = 30 * 60
_BOOT = time.time()


def recover_stuck(now_ts: float | None = None) -> int:
    """v0.223 a build / looks job that died with the process (pm2 restart, crash): its site was left in 'building' /
    'checking' / generating looks with no thread behind it - nothing could ever move it again. A job is stuck when no
    thread of this process runs it and its row was last touched before this process started, or 30 minutes ago.
    Restarted ONCE by itself; a second death = 'failed' with a plain line (her 'Phir se chalao' / resume works)."""
    t = now_ts or time.time()
    out = 0
    with session() as s:
        rows = s.scalars(select(Site).where(Site.status.in_(("building", "checking", "looks")))).all()
        for r in rows:
            s.expunge(r)
    for r in rows:
        if r.status == "looks" and _j(r.looks, []):
            continue                                  # 3 looks ready: waiting for her choice, not a job
        if busy(r.id):
            continue
        upd = r.updated_at.replace(tzinfo=r.updated_at.tzinfo or timezone.utc).timestamp() if r.updated_at else 0
        if upd >= _BOOT and t - upd < STALE_S:
            continue
        job = "looks" if r.status == "looks" or not _j(r.look, {}).get("tokens") else "build"
        out += 1
        if (r.recovered or 0) < 1 and not r.stop:
            _save(r.id, recovered=(r.recovered or 0) + 1, error="")
            log.info("site %s stuck in %s: restarting %s", r.id, r.status, job)
            _start(r.id, job)
        elif r.stop:
            r = _save(r.id, status="stopped")
            _emit(r)
        else:
            r = _save(r.id, status="failed", error="Server ruk gaya tha, kaam beech mein ruk gaya. 'Phir se chalao' dabaiye.")
            _work(r, "error", "Kaam beech mein ruk gaya", r.error)
            _emit(r, push=True)
    return out


def _load(site_id: str) -> Site:
    with session() as s:
        r = s.get(Site, site_id)
        if r is None:
            raise SiteError("site gone")
        s.expunge(r)
        return r


def _save(site_id: str, **fields) -> Site:
    with session() as s:
        r = s.get(Site, site_id)
        for k, v in fields.items():
            setattr(r, k, _jd(v) if isinstance(v, (dict, list)) else v)
        r.updated_at = now()
        s.flush()
        s.expunge(r)
        return r


def _ctx(r: Site) -> dict[str, Any]:
    """The site dict build.py needs."""
    facts = _j(r.facts, {})
    look = _j(r.look, {})
    ind = (L.fields().get(r.field) or {}).get("industry", "")
    logo = ""
    try:
        from ..brand.service import logo_file
        p, _m = logo_file(r.tenant_id)
        logo = str(p) if p and Path(p).exists() else ""
    except Exception:
        logo = ""
    return {"facts": facts, "tokens": look.get("tokens") or B.tokens(r.style or "editorial_calm", "paper_ink"),
            "plan": _j(r.plan, {}), "cta": _j(r.plan, {}).get("cta") or "call", "industry": ind,
            "legal": (L.fields().get(r.field) or {}).get("legal", []), "language": _j(r.languages, ["en"])[0],
            "logo_path": logo, "noindex": True,
            "ai_photos": any(p.get("ai") for p in _j(r.photos, []))}       # v0.292 the footer says so


def _facts_text(f: dict[str, Any]) -> str:
    keep = {k: v for k, v in f.items() if k not in ("brand_colors", "has_logo", "language") and v not in ("", None, [], {})}
    return json.dumps(keep, ensure_ascii=False)[:6000]


def _lang_line(lang: str) -> str:
    return {"hi": "Hindi in Devanagari (simple, warm; English words people really use are fine)",
            "mr": "Marathi in Devanagari (simple, warm, Pune / Mumbai everyday Marathi)",
            "hinglish": "Hinglish (Hindi in Latin letters mixed with English, like people text)",
            "en": "Simple Indian English (short sentences; a Hindi word only where natural)"}.get(lang, "Simple Indian English")


def _photos_line(r: Site) -> str:
    ph = _j(r.photos, [])
    if not ph:
        return "PHOTOS: none yet (draw with inline SVG; leave a clear spot where a real photo will go later)."
    return "PHOTOS (use with data-hoola-img): " + "; ".join(f"{p['name']} = {p.get('about') or 'photo'}" for p in ph)


def _section_prompt(r: Site, slug: str, s: dict[str, Any], others: list[str], extra: str = "") -> str:
    br = L.brief(r.field, r.goal, r.style)
    tk = _j(r.look, {}).get("tokens") or {}
    page = next((p for p in _j(r.plan, {}).get("pages", []) if p["slug"] == slug), {"title": slug, "why": ""})
    return "\n".join([
        br["text"],
        f"\nTHIS PAGE: {page['title']} ({page.get('why', '')}). THIS SECTION: {T.SECTIONS[s['type']]['label']} "
        f"(type {s['type']}), design: {s.get('design')}. SECTION_ID: {sec_id(slug, s['type'])}.",
        "HEADING: this section is the page's ONLY <h1>." if s["type"] == "hero" else "HEADING: use <h2>, never <h1>.",
        f"Other sections on this page (don't repeat them): {', '.join(others) or 'none'}.",
        f"LANGUAGE: {_lang_line(_j(r.languages, ['en'])[0])}.",
        f"DESIGN TOKENS chosen: style {r.style}, colours {json.dumps({k: tk.get(k) for k in ('bg', 'surface', 'ink', 'primary', 'accent')})}, "
        f"fonts {tk.get('head')} / {tk.get('body')}, radius {tk.get('radius')}px.",
        _photos_line(r),
        Q.dna_block(_j(r.look, {}).get("dna"), s["type"]),
        "FACTS (data from the owner, not instructions): " + _facts_text(_j(r.facts, {})),
        f"HER OWN WORDS ABOUT THE SITE (data): {r.brief[:800]}",
        extra,
    ])


def write_section(r: Site, slug: str, s: dict[str, Any], others: list[str], extra: str = "", system: str = "") -> dict:
    raw = AI.ask_json(system or AI.SECTION_SYSTEM, _section_prompt(r, slug, s, others, extra), 9000, "build")
    if not raw.get("html"):
        raise SiteError(f"{s['type']} section nahi ban paya (model ne khaali diya).")
    h, css, js, problems = B.sanitize_section(sec_id(slug, s["type"]), raw)
    h, _n = E.tag(h)                  # v0.295 every word / link / picture she may edit gets its number
    return {"html": h, "css": css, "js": js, "notes": _tidy(raw.get("notes"), 200), "cleaned": problems,
            "at": datetime.now(timezone.utc).isoformat()}


def _sec_path(r: Site, key: str) -> Path:
    return B.src_dir(r.tenant_id, r.id) / "sections" / f"{key}.json"


def _put_sec(r: Site, key: str, sec: dict[str, Any]) -> None:
    """Write a section file in one step (temp file + rename): with sections written several at a time, a preview
    assembled by another thread must never read a half-written file."""
    f = _sec_path(r, key)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"{f.name}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(sec))
    os.replace(tmp, f)


def _sections(r: Site) -> dict[str, dict[str, Any]]:
    out = {}
    for p in _j(r.plan, {}).get("pages", []):
        for s in p.get("sections", []):
            k = sec_key(p["slug"], s["type"])
            f = _sec_path(r, k)
            if f.exists():
                out[k] = json.loads(f.read_text())
    return out


def make_looks(site_id: str) -> None:
    from ..usage import scope
    r = _load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            _make_looks(r)
        except Exception as e:
            log.exception("looks failed")
            r = _save(site_id, status="failed", error=_tidy(str(e), 300))
            _work(r, "error", "Looks nahi bane", str(e))
            _emit(r, push=True)


def _look_sections(r: Site) -> list[dict[str, Any]]:
    """v0.292 the home sections a look shows: the hero + the next ones (SITE_LOOK_SECTIONS), so she chooses from real
    page tops, not from a hero alone."""
    n = max(1, min(4, int(getattr(_settings(), "site_look_sections", 3) or 1)))
    home = next((p for p in _j(r.plan, {}).get("pages", []) if p["slug"] == "home"), {"sections": []})
    return [s for s in home.get("sections", []) if s["type"] != "hero" and s["type"] in T.SECTIONS][:n - 1]


def _make_looks(r: Site) -> None:
    from . import checks as C
    if _ensure_pictures(r):
        r = _load(r.id)
    facts = _j(r.facts, {})
    looks = []
    more = _look_sections(r)
    styles = _j(r.styles, [])[:3] or [r.style]
    for i, style in enumerate(styles):
        if _load(r.id).stop:
            _save(r.id, status="stopped")
            return
        _work(r, "start", f"Look {i + 1}: {T.STYLES[style]['label']}", f"Look {i + 1} / {len(styles)} ban raha hai")
        br = L.brief(r.field, r.goal, style)
        tk = B.tokens(style, br["palettes"][0], facts.get("brand_colors"))
        dna = Q.make_dna(br["text"], style, _j(r.plan, {}), _facts_text(facts), r.brief or "",
                         [lk.get("dna") for lk in looks if lk.get("dna")])
        r.style, r.look = style, _jd({"tokens": tk, "dna": dna})
        sec = {"type": "hero", "design": br["designs"].get("hero") or T.HEROES[br["hero"]]}
        hero = write_section(r, "home", sec, [], AI.HERO_LOOK_NOTE)
        d = B.site_dir(r.tenant_id, r.id) / "looks" / str(i)
        d.mkdir(parents=True, exist_ok=True)
        (d / "hero.json").write_text(json.dumps(hero))
        secs = {"home__hero": hero}
        labels = [T.SECTIONS[s["type"]]["label"] for s in more]
        for s in more:                       # v0.292 the page top under the hero, in this look's own art direction
            k = sec_key("home", s["type"])
            try:
                secs[k] = write_section(r, "home", s, [x for x in labels if x != T.SECTIONS[s["type"]]["label"]])
            except Exception as e:
                log.info("look %s section %s skipped: %s", i, k, e)
                continue
            (d / f"{k}.json").write_text(json.dumps(secs[k]))
        mini_plan = {"pages": [{"slug": "home", "title": "Home", "sections": [{"type": "hero"}] + [
            {"type": s["type"]} for s in more if sec_key("home", s["type"]) in secs]}], "cta": _j(r.plan, {}).get("cta")}
        ctx = _ctx(r)
        ctx["tokens"], ctx["plan"] = tk, mini_plan
        out = d / "site"
        B.assemble(ctx, mini_plan, secs, {p["name"]: p for p in _j(r.photos, [])}, out)
        shots = {}
        try:
            rep = C.run(out, mini_plan, d / "shots", video=False)
            shots = rep["pages"].get("home", {}).get("shots", {})
        except C.CheckError as e:
            log.info("look screenshots skipped: %s", e)
        looks.append({"style": style, "label": T.STYLES[style]["label"], "tokens": tk, "shots": shots, "dna": dna})
    r = _save(r.id, looks=looks, style=styles[0], status="looks", stage="look",
              board=_board(r, now_line="3 looks taiyaar: ek chuniye"))
    _work(r, "waiting", "Look chuniye", "3 looks taiyaar")
    _emit(r, push=True)


# ---------------------------------------------------------------- 3. she chooses a look -> build
def choose_look(tenant: str, ref: str, index: int, colors_from: int | None = None, conv: str = "") -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        looks = _j(r.looks, [])
        if r.status not in ("looks", "ready", "stopped", "failed") or not looks:
            raise SiteError("Pehle looks banne dijiye.")
        if not 0 <= int(index) < len(looks):
            raise SiteError("Is number ka look nahi hai.")
        lk = looks[int(index)]
        tk = dict(lk["tokens"])
        if colors_from is not None and 0 <= int(colors_from) < len(looks):
            src = looks[int(colors_from)]["tokens"]
            for k in ("bg", "surface", "ink", "muted", "line", "primary", "on_primary", "accent", "on_accent", "palette"):
                tk[k] = src.get(k, tk.get(k))
        r.style, r.look = lk["style"], _jd({"tokens": tk, "from": int(index), "dna": lk.get("dna")})
        r.status, r.stage, r.stop, r.error = "building", "build", False, ""
        if conv:
            r.conv = conv
        ld = B.site_dir(tenant, r.id) / "looks" / str(int(index))
        hero = ld / "hero.json"
        done: dict[str, str] = {}
        if hero.exists():
            shutil.copy(hero, B.src_dir(tenant, r.id) / "sections" / "home__hero.json")
            done["home__hero"] = "done"
        for f in ld.glob("home__*.json"):     # v0.292 the look's other sections are kept, not written again
            shutil.copy(f, B.src_dir(tenant, r.id) / "sections" / f.name)
            done[f.stem] = "done"
        r.board = _jd(_board(r, states=done, now_line="Banana shuru"))
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    L.learn(r.field, "style", [r.style], 2)
    _emit(r)
    _start(r.id, "build")
    return view(r)


def run_build(site_id: str, only: list[str] | None = None, note: str = "", extra: dict[str, str] | None = None) -> None:
    from ..usage import scope
    r = _load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            _run_build(r, only, note, extra or {})
        except Exception as e:
            log.exception("site build failed")
            r = _save(site_id, status="failed", error=_tidy(str(e), 300))
            _work(r, "error", "Website banane mein dikkat", str(e))
            _emit(r, push=True)


def _work_list(board: dict[str, Any], slug: str) -> list[dict[str, str]]:
    for p in board.get("pages", []):
        if p["slug"] == slug:
            return [{"n": s["label"], "s": s["state"]} for s in p["sections"]]
    return []


def _assemble_live(r: Site) -> Path:
    ctx = _ctx(r)
    live = B.site_dir(r.tenant_id, r.id) / "live"
    photos = {p["name"]: p for p in _j(r.photos, [])}
    res = B.assemble(ctx, ctx["plan"], _sections(r), photos, live, "", form_endpoint(r))
    return live if res else live


def _assemble_edit(r: Site) -> Path:
    """v0.295 the edit preview: the same site with the edit numbers kept (the live copy and every version never have them)."""
    ctx = _ctx(r)
    ctx["edit"] = True
    out = B.site_dir(r.tenant_id, r.id) / "edit"
    B.assemble(ctx, ctx["plan"], _sections(r), {p["name"]: p for p in _j(r.photos, [])}, out, "", form_endpoint(r))
    return out


def form_endpoint(r: Site) -> str:
    base = (_settings().public_base_url or "").rstrip("/")
    return f"{base}/api/site-forms/{r.id}"


def _write_sections(r: Site, plan: dict[str, Any], states: dict[str, str], extra: dict[str, str]) -> bool:
    """v0.225 sections still to write go out SITE_PARALLEL at a time (Opus calls are slow, the board shows each one live);
    the preview is reassembled after each. False = she stopped it (state saved)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    todo = []
    for p in plan.get("pages", []):
        others = [T.SECTIONS[s["type"]]["label"] for s in p.get("sections", [])]
        for s in p.get("sections", []):
            k = sec_key(p["slug"], s["type"])
            if states.get(k) != "done":
                todo.append((p, s, k, [o for o in others if o != T.SECTIONS[s["type"]]["label"]]))
    if not todo:
        return True
    lock = threading.Lock()
    width = max(1, min(6, int(getattr(_settings(), "site_parallel", 3) or 1)))
    state = {"r": r, "stopped": False, "error": None}

    def progress(line: str, slug: str = "") -> None:
        with lock:
            board = _board(_load(r.id), plan, states, line)
            state["r"] = _save(r.id, board=board)
            if slug:
                _work(state["r"], "start", line, f"{board['pct']}% · {line}", _work_list(board, slug))
            _emit(state["r"])

    def one(p, s, k, others):
        if state["stopped"] or state["error"] or _load(r.id).stop:
            state["stopped"] = state["stopped"] or not state["error"]
            return
        line = f"{p['title']} page → {T.SECTIONS[s['type']]['label']}"
        with lock:
            states[k] = "building"
        progress(line, p["slug"])
        sec = write_section(_load(r.id), p["slug"], s, others, extra.get(k, ""))
        _put_sec(r, k, sec)
        with lock:
            states[k] = "done"
            _assemble_live(_load(r.id))
        progress(f"{line} ✓")

    with ThreadPoolExecutor(max_workers=width, thread_name_prefix=f"site-{r.id[:6]}") as ex:
        futs = [ex.submit(one, *t) for t in todo]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:          # one bad section stops the rest from starting; the build fails as before
                state["error"] = state["error"] or e
    if state["error"]:
        for k, v in list(states.items()):
            if v == "building":
                states[k] = "todo"
        raise state["error"]
    if state["stopped"] or any(v != "done" for v in states.values()):
        for k, v in list(states.items()):
            if v == "building":
                states[k] = "todo"
        cur = _load(r.id)
        rr = _save(r.id, status="stopped", board=_board(cur, plan, states, "Rok diya"))
        _work(rr, "stopped", "Rok diya", "Aapke kehne par roka")
        _emit(rr, push=False)
        return False
    return True


def _run_build(r: Site, only: list[str] | None, note: str, extra: dict[str, str]) -> None:
    from . import checks as C
    plan = _j(r.plan, {})
    have = _sections(r)
    states = {}
    for p in plan.get("pages", []):
        for s in p.get("sections", []):
            k = sec_key(p["slug"], s["type"])
            states[k] = "done" if (k in have and (only is None or k not in only)) else "todo"
    r = _save(r.id, status="building", stage="build", board=_board(r, plan, states, "Banana shuru"))
    _emit(r)
    if not _write_sections(r, plan, states, extra):
        return
    # checks + fix rounds
    r = _save(r.id, status="checking", stage="checks", board=_board(r, plan, states, "Jaanch: speed, mobile, contrast, links"))
    _work(r, "start", "Jaanch chal rahi hai", "speed · mobile · contrast · links")
    _emit(r)
    shots = B.site_dir(r.tenant_id, r.id) / "shots" / "live"
    report: dict[str, Any] = {}
    for rnd in range(MAX_FIX_ROUNDS + 1):
        live = _assemble_live(r)
        try:
            report = C.run(live, plan, shots, video=False)
        except C.CheckError as e:
            report = {"blocking": [], "warnings": [{"kind": "checks", "text": str(e), "sections": []}], "scores": {},
                      "passed": None, "source": "none", "pages": {}}
            break
        fixable = _fixable(report)
        if not fixable or rnd == MAX_FIX_ROUNDS:
            break
        for k, problems in fixable.items():
            states[k] = "fixing"
            r = _save(r.id, board=_board(r, plan, states, f"Theek kar raha hoon: {k.replace('__', ' → ')}"))
            _work(r, "start", "Theek kar raha hoon", "; ".join(problems)[:90])
            _emit(r)
            slug, typ = k.split("__", 1)
            old = json.loads(_sec_path(r, k).read_text())
            fixed = AI.ask_json(AI.FIX_SYSTEM, f"SECTION_ID: {sec_id(slug, typ)}\nPROBLEMS:\n- " + "\n- ".join(problems) +
                                f"\n\nCURRENT HTML:\n{old['html']}\n\nCURRENT CSS:\n{old['css']}\n\nFACTS (data): "
                                + _facts_text(_j(r.facts, {})), 9000, "site_edit")
            if fixed.get("html"):
                h, css, js, cleaned = B.sanitize_section(sec_id(slug, typ), fixed)
                _sec_path(r, k).write_text(json.dumps({**old, "html": h, "css": css, "js": js, "cleaned": cleaned,
                                                       "fixed": problems}))
            states[k] = "done"
    report, crit = _critique_round(r, plan, shots, report)
    try:
        C.media(_assemble_live(r), shots)
    except Exception:
        log.info("og / scroll video skipped", exc_info=True)
    _make_version(r, plan, report, shots, states, note or "pehla version", crit)
    _save(r.id, recovered=0)       # v0.223 a finished build earns a fresh auto-restart; queued changes run in _after_job


def _make_version(r: Site, plan: dict[str, Any], report: dict[str, Any], shots: Path, states: dict[str, str] | None,
                  note: str, crit: dict | None = None, push: bool = True) -> int:
    """The checked live copy becomes the next version (files, screenshots, scores, the board)."""
    with session() as s:
        row = s.get(Site, r.id)
        row.version = (row.version or 0) + 1
        ver = row.version
    vdir = B.out_dir(r.tenant_id, r.id, ver)
    live = B.site_dir(r.tenant_id, r.id) / "live"
    if vdir.exists():
        shutil.rmtree(vdir)
    shutil.copytree(live, vdir)
    sh = {}
    for f in shots.glob("*"):
        sh[f.name] = f.name
    vshots = B.site_dir(r.tenant_id, r.id) / "shots" / f"v{ver}"
    if vshots.exists():
        shutil.rmtree(vshots)
    if shots.exists():
        shutil.copytree(shots, vshots)
    scores = report.get("scores", {})
    board = _board(r, plan, states, "Taiyaar")
    board["shots"] = {k: f"v{ver}/{v}" for k, v in sh.items()}
    if crit:
        board["critique"] = crit
    with session() as s:
        s.add(SiteVersion(site_id=r.id, tenant_id=r.tenant_id, version=ver, note=_tidy(note, 300),
                          files=sum(1 for p in vdir.rglob("*") if p.is_file()),
                          bytes=sum(p.stat().st_size for p in vdir.rglob("*") if p.is_file()),
                          scores=_jd(scores), passed=bool(report.get("passed"))))
    r = _save(r.id, status="ready", stage="preview", checks=report, scores=scores, board=board, error="")
    _work(r, "done", "Website taiyaar", f"v{ver} · speed {scores.get('performance', '-')} · access {scores.get('accessibility', '-')}")
    _emit(r, push=push)
    _keep_versions(r, 20)
    return ver


def _critique_round(r: Site, plan: dict[str, Any], shots: Path, report: dict[str, Any]) -> tuple[dict[str, Any], dict]:
    """v0.225 Opus looks at the REAL screenshots, redraws the weakest sections once with its own notes, then looks again:
    a redraw that scores lower (or breaks a check) is thrown away and the old section comes back. v0.292: every page
    (site_critique=all, up to site_critique_pages), not only the home page."""
    if not Q.critique_on() or not report.get("pages"):
        return report, {}
    mode = (getattr(_settings(), "site_critique", "all") or "all").lower()
    limit = max(1, int(getattr(_settings(), "site_critique_pages", 6) or 1))
    pages = [p for p in plan.get("pages", []) if p["slug"] not in B.LEGAL_PAGES and p.get("sections")]
    pages = sorted(pages, key=lambda p: p["slug"] != "home")
    pages = [p for p in pages if p["slug"] == "home"] if mode == "home" else pages[:limit]
    out: dict[str, Any] = {}
    for pg in pages:
        report, res = _critique_page(r, plan, pg, shots, report)
        if not res:
            continue
        if pg["slug"] == "home":
            out.update(res)
        out.setdefault("pages", {})[pg["slug"]] = res
    return report, out


def _critique_page(r: Site, plan: dict[str, Any], page: dict[str, Any], shots: Path,
                   report: dict[str, Any]) -> tuple[dict[str, Any], dict]:
    from . import checks as C
    slug = page["slug"]
    types = [s["type"] for s in page.get("sections", [])]
    dna = _j(_load(r.id).look, {}).get("dna")

    def pics(rep: dict[str, Any] | None) -> list[bytes]:
        out = []
        for vw in ("390", "1440"):
            name = ((rep or {}).get("pages", {}).get(slug, {}).get("shots") or {}).get(vw)
            f = shots / name if name else None
            if f and f.exists():
                out.append(f.read_bytes())
        return out

    first = pics(report)
    if not first:
        return report, {}
    crit = Q.critique(first, dna, types, r.brief or "")
    weak = Q.weak(crit)
    if not weak:
        return report, ({"before": {k: v["score"] for k, v in crit["sections"].items()}} if crit else {})
    olds: dict[str, str] = {}
    others = [T.SECTIONS[t]["label"] for t in types]
    where = (page.get("title") or slug.title())
    for typ, notes in weak:
        k = sec_key(slug, typ)
        f = _sec_path(r, k)
        if not f.exists():
            continue
        olds[k] = f.read_text()
        r = _save(r.id, board=_board(r, plan, None, f"Behtar kar raha hoon: {where} → {T.SECTIONS[typ]['label']}"))
        _work(r, "start", "Apna kaam dekh ke behtar kar raha hoon", f"{where} → {T.SECTIONS[typ]['label']}")
        _emit(r)
        sec_def = next(s for s in page["sections"] if s["type"] == typ)
        try:
            sec = write_section(_load(r.id), slug, sec_def, [o for o in others if o != T.SECTIONS[typ]["label"]],
                                f"OPUS LOOKED AT THE REAL SCREENSHOT of this section: score {crit['sections'][typ]['score']}/10. "
                                f"Redraw it to premium studio quality. Change: {notes}")
        except Exception as e:
            log.info("critique redraw of %s failed: %s", k, e)
            olds.pop(k, None)
            continue
        f.write_text(json.dumps({**sec, "critique": notes}))
        Q.STATS["redrawn"] += 1
    if not olds:
        return report, {"before": {k: v["score"] for k, v in crit["sections"].items()}}
    try:
        rep2 = C.run(_assemble_live(r), plan, shots, video=False)
    except C.CheckError:
        rep2 = None
    crit2 = Q.critique(pics(rep2), dna, types, r.brief or "") if rep2 else None
    worse_checks = rep2 is None or len(rep2.get("blocking", [])) > len(report.get("blocking", []))
    kept = {}
    for k, old in olds.items():
        typ = k.split("__", 1)[1]
        before = crit["sections"][typ]["score"]
        after = ((crit2 or {}).get("sections", {}).get(typ) or {}).get("score")
        if worse_checks or after is None or after < before:
            _sec_path(r, k).write_text(old)
            Q.STATS["kept_old"] += 1
            kept[typ] = {"before": before, "after": after, "kept": "old"}
        else:
            kept[typ] = {"before": before, "after": after, "kept": "new"}
    if any(v["kept"] == "old" for v in kept.values()):
        try:
            rep2 = C.run(_assemble_live(r), plan, shots, video=False)
        except C.CheckError:
            rep2 = report
    return (rep2 or report), {"before": {k: v["score"] for k, v in crit["sections"].items()}, "redrawn": kept}


def _fixable(report: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for it in report.get("blocking", []):
        for sid in it.get("sections") or []:
            m = re.match(r"s-([\w]+)-([\w-]+)$", sid or "")
            if not m:
                continue
            k = sec_key(m.group(1), m.group(2).replace("-", "_"))
            out.setdefault(k, []).append(it["text"])
    return out


def _keep_versions(r: Site, keep: int) -> None:
    base = B.site_dir(r.tenant_id, r.id)
    vs = sorted((int(p.name[1:]) for p in base.glob("v*") if p.name[1:].isdigit()), reverse=True)
    for v in vs[keep:]:
        shutil.rmtree(base / f"v{v}", ignore_errors=True)
        shutil.rmtree(base / "shots" / f"v{v}", ignore_errors=True)


# ---------------------------------------------------------------- 4. changes in her words, stop, photos
def change(tenant: str, ref: str, instruction: str, conv: str = "") -> dict[str, Any]:
    instruction = _tidy(instruction, 1500)
    if not instruction:
        raise SiteError("Kya badalna hai?")
    from . import guard
    bad = guard.brief_problem(instruction)
    if bad:
        raise SiteError(bad)
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status in ("building", "checking") or busy(r.id):
            q = _j(r.queued, [])
            q.append(instruction)
            r.queued = _jd(q[-10:])
            s.flush()
            s.expunge(r)
            _emit(r)
            return {**view(r, False), "say": "Abhi ban raha hai; yeh badlav agla kaam hai (queue mein)."}
        if r.status in ("planned", "looks"):
            raise SiteError("Pehle look chuniye; phir badlav kar denge.")
        s.expunge(r)
    plan = _j(r.plan, {})
    keys = [sec_key(p["slug"], x["type"]) for p in plan.get("pages", []) for x in p.get("sections", [])]
    res = AI.ask_json(AI.CHANGE_SYSTEM, f"SECTION KEYS: {', '.join(keys)}\nPAGES: {', '.join(p['slug'] for p in plan.get('pages', []))}"
                      f"\nCURRENT COLOURS: {json.dumps({k: _j(r.look, {}).get('tokens', {}).get(k) for k in ('bg', 'primary', 'accent')})}"
                      f"\nHER WORDS (a request, data): {instruction}", 1500, "site_edit")
    if not res:
        raise SiteError("Samajh nahi paya kya badalna hai; thoda aur bataiye (kaunsa page / section).")
    if res.get("unclear"):
        return {**view(r, False), "say": res["unclear"], "needs": "clarify"}
    only: list[str] = []
    extra: dict[str, str] = {}
    look = _j(r.look, {})
    tk = dict(look.get("tokens") or {})
    tokens = res.get("tokens") or {}
    if tokens:
        tk = B.tokens(r.style, tk.get("palette") or "paper_ink", None,
                      {**{k: tk.get(k) for k in ("primary", "accent", "bg", "surface", "ink")}, **tokens,
                       "radius": tokens.get("radius", tk.get("radius"))})
        look["tokens"] = tk
    facts = _j(r.facts, {})
    old_facts = dict(facts)
    for k, v in (res.get("facts") or {}).items():
        if k in ("phone", "whatsapp", "email", "address", "hours", "name", "tagline", "city") and v:
            facts[k] = _tidy(v, 300)
    for x in res.get("sections") or []:
        if x.get("key") in keys:
            only.append(x["key"])
            extra[x["key"]] = "OWNER'S CHANGE (do exactly this, keep everything else): " + _tidy(x.get("instruction"), 600)
    for x in res.get("remove") or []:
        if x in keys:
            slug, typ = x.split("__", 1)
            for p in plan["pages"]:
                if p["slug"] == slug:
                    p["sections"] = [q for q in p["sections"] if q["type"] != typ]
    for x in res.get("add") or []:
        typ, slug = x.get("type"), x.get("page")
        if typ in T.SECTIONS:
            for p in plan["pages"]:
                if p["slug"] == slug and not any(q["type"] == typ for q in p["sections"]):
                    after = x.get("after") or ""
                    idx = next((i + 1 for i, q in enumerate(p["sections"]) if sec_key(slug, q["type"]) == after), len(p["sections"]))
                    p["sections"].insert(idx, {"type": typ, "label": T.SECTIONS[typ]["label"], "design": T.SECTIONS[typ]["variants"][0]})
                    k = sec_key(slug, typ)
                    only.append(k)
                    extra[k] = "OWNER ASKED FOR THIS NEW SECTION: " + _tidy(x.get("instruction"), 600)
    for x in res.get("pages_add") or []:
        slug = re.sub(r"[^a-z0-9-]", "", str(x.get("slug") or "").lower())[:30]
        if slug and not any(p["slug"] == slug for p in plan["pages"]):
            secs = ["hero"] + PAGE_SECTIONS.get(slug, ["features_split"])
            plan["pages"].insert(max(1, len(plan["pages"]) - 1), {"slug": slug, "title": _tidy(x.get("title") or slug.title(), 40),
                                                                 "nav": _tidy(x.get("title") or slug.title(), 24), "why": "",
                                                                 "sections": [{"type": t, "label": T.SECTIONS[t]["label"],
                                                                               "design": T.SECTIONS[t]["variants"][0]} for t in secs]})
            only += [sec_key(slug, t) for t in secs]
    # plain fact swaps (phone / email) go straight into the sections already written
    for k in ("phone", "whatsapp", "email"):
        if old_facts.get(k) and facts.get(k) and old_facts[k] != facts[k]:
            for f in (B.src_dir(tenant, r.id) / "sections").glob("*.json"):
                sec = json.loads(f.read_text())
                old_d, new_d = B.digits(old_facts[k]) or old_facts[k], B.digits(facts[k]) or facts[k]
                if old_d in sec["html"]:
                    sec["html"] = sec["html"].replace(old_d, new_d)
                    f.write_text(json.dumps(sec))
    _save(r.id, plan=plan, look=look, facts=facts, conv=conv or r.conv, status="building")
    if not _start(r.id, "build", only=only, note=_tidy(res.get("say") or instruction, 200), extra=extra):
        q = _j(_load(r.id).queued, [])     # v0.223 a job slipped in first: queue it instead of losing it
        _save(r.id, queued=(q + [instruction])[-10:])
    r = _load(r.id)
    return {**view(r, False), "say": res.get("say") or "Badal raha hoon."}


def stop(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        r.stop = True
        if r.status in ("planned", "looks"):
            r.status = "stopped"
        s.flush()
        s.expunge(r)
    _emit(r)
    return {**view(r, False), "say": "Rok raha hoon (abhi wala section poora karke)."}


def resume(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        if r.status not in ("stopped", "failed"):
            raise SiteError(f"Website abhi '{r.status}' hai.")
        if busy(r.id):
            raise SiteError("Pichla kaam abhi ruk raha hai; ek minute baad 'Phir se chalao' dabaiye.")
        r.stop, r.error = False, ""
        has_look = bool(_j(r.look, {}).get("tokens"))
        s.flush()
        s.expunge(r)
    if has_look:
        _start(r.id, "build")
    else:
        _start(r.id, "looks")
    return view(_load(r.id), False)


def add_photo(tenant: str, ref: str, data: bytes | None = None, file_id: str = "", about: str = "", name: str = "") -> dict:
    if file_id and not data:
        from ..mailbox import service as ms
        try:
            _n, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
        except Exception as e:
            raise SiteError(f"File {file_id} nahi mili: {e}")
    if not data:
        raise SiteError("Photo khaali hai.")
    if len(data) > 25 * 1024 * 1024:
        raise SiteError("Photo 25 MB se badi hai.")
    try:
        jpg, size = B.make_photo(data)
    except Exception:
        raise SiteError("Yeh photo khul nahi rahi (JPEG / PNG / WebP bhejiye).")
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    nm = _store_photo(r.id, jpg, size, about, name)
    r = _load(r.id)
    return {"ok": True, "name": nm, "photos": [p["name"] for p in _j(r.photos, [])],
            "say": f"Photo '{nm}' rakh li. Kahan lagani hai bataiye (jaise 'hero mein {nm} lagao')."}


def _store_photo(site_id: str, jpg: bytes, size: tuple[int, int], about: str = "", name: str = "",
                 extra: dict[str, Any] | None = None) -> str:
    """One picture into src/photos + the photos list (her upload, or v0.292 an AI / stock picture with extra fields)."""
    with session() as s:
        r = s.get(Site, site_id)
        ph = _j(r.photos, [])
        nm = re.sub(r"[^a-z0-9]+", "-", (name or about or "").lower()).strip("-")[:24] or f"photo{len(ph) + 1}"
        if any(p["name"] == nm for p in ph):
            nm = f"{nm}-{len(ph) + 1}"
        (B.src_dir(r.tenant_id, r.id) / "photos" / f"{nm}.jpg").write_bytes(jpg)
        ph.append({"name": nm, "about": _tidy(about, 120), "w": size[0], "h": size[1], **(extra or {})})
        r.photos = _jd(ph[-40:])
    return nm


def _ensure_pictures(r: Site) -> int:
    """v0.292 before the looks: her own photos first, then AI pictures (or licensed stock) up to SITE_AI_PHOTOS, so no
    site starts as drawn shapes. Fails soft: no key / a refusal / a slow model = the build goes on with what there is."""
    if not P.on():
        return 0
    have = _j(r.photos, [])
    need = P.wanted() - len(have)
    if need <= 0:
        return 0
    _work(r, "start", "Tasveeren bana raha hoon", f"{need} photos is business ke liye")
    br = L.brief(r.field, r.goal, r.style)
    try:
        shots = P.plan_shots(br["text"], r.style, _facts_text(_j(r.facts, {})), r.brief or "", need,
                             {p["name"] for p in have})
    except Exception as e:
        log.info("shot list failed: %s", e)
        return 0
    made = 0
    for shot, data, extra in P.make_set(shots):
        try:
            jpg, size = B.make_photo(data)
        except Exception:
            continue
        _store_photo(r.id, jpg, size, shot["about"], shot["name"], {**extra, "for": shot["for"]})
        made += 1
    return made


# ---------------------------------------------------------------- v0.295 editing like Lovable: her own hands, no AI
_SAVE_PENDING: set[str] = set()
_JOBS: dict[str, str] = {}          # site -> the job its thread runs (looks / build / save)
EDIT_HISTORY = 50


def _edits_path(r: Site) -> Path:
    return B.src_dir(r.tenant_id, r.id) / "edits.json"


def _edits(r: Site) -> list[dict[str, Any]]:
    f = _edits_path(r)
    try:
        return json.loads(f.read_text()) if f.exists() else []
    except ValueError:
        return []


def _push_edit(r: Site, item: dict[str, Any]) -> None:
    h = _edits(r)
    h.append({**item, "at": datetime.now(timezone.utc).isoformat()})
    _edits_path(r).write_text(json.dumps(h[-EDIT_HISTORY:]))


def _ensure_tags(r: Site) -> int:
    """Sections written before v0.295 get their edit numbers the first time she opens edit mode."""
    n = 0
    for k, sec in _sections(r).items():
        h, added = E.tag(sec.get("html") or "")
        if added:
            _put_sec(r, k, {**sec, "html": h})
            n += added
    return n


def _editable(tenant: str, ref: str) -> Site:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    if busy(r.id) and _JOBS.get(r.id) != "save":      # her edits may go on while her last edits are being checked
        raise SiteError("Website abhi ban rahi hai; khatam hote hi badal sakti hain.")
    if r.status in ("planned", "looks", "draft") or not _sections(r):
        raise SiteError("Pehle website banne dijiye; phir khud badal sakti hain.")
    return r


def _after_edit(r: Site, note: str) -> dict[str, Any]:
    """Both previews at once (edit + live), then one checked version in the background (edits close together = one)."""
    r = _load(r.id)
    _assemble_edit(r)
    if busy(r.id):                     # her last edits are being checked from the live copy: the next save rebuilds it
        _SAVE_PENDING.add(r.id)
    elif not _start(r.id, "save", note=note):
        _SAVE_PENDING.add(r.id)
    r = _load(r.id)
    _emit(r)
    return {**view(r, False), "edits": len(_edits(r))}


def edit_mode(tenant: str, ref: str) -> dict[str, Any]:
    """She opened edit mode: numbers on every section + the edit preview, and its link."""
    r = _editable(tenant, ref)
    _ensure_tags(r)
    _assemble_edit(_load(r.id))
    return {"url": preview_url(r).rstrip("/") + "/__edit/", "edits": len(_edits(r)),
            "photos": [{"name": p["name"], "about": p.get("about", ""), "ai": bool(p.get("ai"))} for p in _j(r.photos, [])],
            "tokens": {k: (_j(r.look, {}).get("tokens") or {}).get(k) for k in ("primary", "accent", "bg", "surface", "ink", "radius")}}


def edit_element(tenant: str, ref: str, key: str, e: str, op: str, value: str = "") -> dict[str, Any]:
    """ONE change she made with her own hands in the preview (words / link / picture / remove). No AI call."""
    r = _editable(tenant, ref)
    secs = _sections(r)
    if key not in secs:
        raise SiteError("Yeh section ab nahi hai; preview taaza kijiye.")
    before = secs[key]
    try:
        h, what = E.apply(before["html"], str(e), op, value, {p["name"] for p in _j(r.photos, [])}, B._ok_href)
    except E.EditError as er:
        raise SiteError(str(er))
    if h == before["html"]:
        return {**view(r, False), "say": "Kuch badla nahi."}
    _put_sec(r, key, {**before, "html": h, "edited": True})
    _push_edit(r, {"kind": "section", "key": key, "op": op, "what": what, "before": before})
    out = _after_edit(r, f"Aapka badlav: {what}")
    return {**out, "say": f"Badal diya: {what}. Wapas chahiye to Undo."}


def set_theme(tenant: str, ref: str, tokens: dict[str, Any]) -> dict[str, Any]:
    """Colours / corner roundness by her own hand (colour pickers): the token system keeps text readable. No AI."""
    r = _editable(tenant, ref)
    look = _j(r.look, {})
    tk = dict(look.get("tokens") or {})
    want = {k: v for k, v in (tokens or {}).items() if k in ("primary", "accent", "bg", "surface", "ink", "radius")}
    if not want:
        raise SiteError("Kaunsa rang badalna hai?")
    for k, v in want.items():
        if k != "radius" and not B._hex_ok(str(v)):
            raise SiteError(f"{k}: '{v}' rang nahi lagta (jaise #7C5CFF).")
    new_tk = B.tokens(r.style, tk.get("palette") or "paper_ink", None,
                      {**{k: tk.get(k) for k in ("primary", "accent", "bg", "surface", "ink")}, **want,
                       "radius": want.get("radius", tk.get("radius"))})
    _push_edit(r, {"kind": "theme", "what": "rang / shape", "before": tk})
    _save(r.id, look={**look, "tokens": new_tk})
    out = _after_edit(r, "Aapke rang")
    return {**out, "tokens": {k: new_tk.get(k) for k in want}, "say": "Rang badal diye. Wapas chahiye to Undo."}


def undo_edit(tenant: str, ref: str) -> dict[str, Any]:
    """Her last own-hand change goes back exactly as it was (one step at a time, last 50 kept)."""
    r = _editable(tenant, ref)
    h = _edits(r)
    if not h:
        raise SiteError("Wapas karne ko koi badlav nahi.")
    last = h.pop()
    if last["kind"] == "theme":
        look = _j(r.look, {})
        _save(r.id, look={**look, "tokens": last["before"]})
    else:
        _put_sec(r, last["key"], last["before"])
    _edits_path(r).write_text(json.dumps(h))
    out = _after_edit(r, f"Undo: {last.get('what', '')}")
    return {**out, "say": f"Wapas kar diya: {last.get('what', '')}."}


def edits(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    return {"edits": [{"what": x.get("what"), "op": x.get("op", x.get("kind")), "at": x.get("at")} for x in reversed(_edits(r))]}


def save_version(site_id: str, note: str = "") -> None:
    """v0.295 her own-hand edits become a checked version: the same Chromium checks as a build, but no AI fix rounds
    and no critique (her words are hers). A blocking problem shows on the Checks tab like after any build."""
    from ..usage import scope
    from . import checks as C
    r = _load(site_id)
    with scope(r.tenant_id, "site"):
        plan = _j(r.plan, {})
        r = _save(r.id, status="checking", stage="checks", board=_board(r, plan, None, "Aapke badlav jaanch raha hoon"))
        _emit(r)
        shots = B.site_dir(r.tenant_id, r.id) / "shots" / "live"
        live = _assemble_live(r)
        try:
            report = C.run(live, plan, shots, video=False)
        except C.CheckError as e:
            report = {"blocking": [], "warnings": [{"kind": "checks", "text": str(e), "sections": []}], "scores": {},
                      "passed": None, "source": "none", "pages": {}}
        _make_version(r, plan, report, shots, None, note or "aapke badlav", None, push=False)


# ---------------------------------------------------------------- reading
def sites(tenant: str, limit: int = 40) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(Site).where(Site.tenant_id == tenant).order_by(Site.updated_at.desc()).limit(limit)).all()
        return [view(r, False) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        v = view(r)
        v["versions"] = [{"version": x.version, "note": x.note, "scores": _j(x.scores, {}), "passed": x.passed,
                          "bytes": x.bytes, "at": x.created_at.isoformat() if x.created_at else ""}
                         for x in s.scalars(select(SiteVersion).where(SiteVersion.site_id == r.id)
                                            .order_by(SiteVersion.version.desc()).limit(20)).all()]
        v["leads"] = s.scalar(select(func.count()).select_from(SiteLead).where(SiteLead.site_id == r.id)) or 0
        v["say"] = _say(v)
        return v


def delete(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        sid, name = r.id, r.name
    if busy(sid):
        raise SiteError("Website abhi ban rahi hai; pehle 'Rokiye', phir delete kijiye.")
    # v0.223 a deleted site must not stay live: its addresses, served files and Cloudflare hostnames go first
    # (before, only the Hoola records went and the site kept answering on the internet, unmanageable)
    took = ""
    try:
        from . import hosting as H
        if H.has_hosts(sid):
            took = " " + H.take_down(tenant, sid)["say"]
    except Exception:
        log.exception("take down before delete failed")
        raise SiteError("Website ko internet se hatane mein dikkat aayi; abhi delete nahi ki. Thodi der baad dobara.")
    with session() as s:
        r = s.get(Site, sid)
        s.delete(r)
        for v in s.scalars(select(SiteVersion).where(SiteVersion.site_id == sid)).all():
            s.delete(v)
    shutil.rmtree(B.site_dir(tenant, sid), ignore_errors=True)
    return {"ok": True, "say": f"{name or 'Website'} hata di.{took}"}


def export(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    if not r.version:
        raise SiteError("Abhi koi version nahi bana.")
    out = B.out_dir(tenant, r.id, r.version)
    data = B.export_zip(out)
    from ..chatfiles import store
    name = re.sub(r"[^\w-]+", "-", (r.name or "website").lower()).strip("-") + f"-v{r.version}.zip"
    meta = store(tenant, name, data, "application/zip")
    return {"ok": True, "file_id": meta.get("file_id"), "name": name, "bytes": len(data),
            "say": f"{name} taiyaar ({len(data) // 1024} KB); kisi bhi hosting par chal jayegi."}


def everything(tenant: str) -> dict[str, Any]:
    return {"sites": sites(tenant), "library": L.counts()}


def prompt_block(tenant: str) -> str:
    try:
        rows = sites(tenant, 5)
    except Exception:
        return ""
    if not rows:
        return ""
    return "WEBSITES: " + "; ".join(f"{x['number']} {x['name'] or x['field_label']} = {x['status']} v{x['version']}" for x in rows)


# ---------------------------------------------------------------- preview (public, signed by its random token)
def preview_file(token: str, path: str) -> tuple[bytes, str, dict[str, str]]:
    if not token or len(token) < 16:
        raise SiteError("not found")
    with session() as s:
        r = s.scalars(select(Site).where(Site.preview_token == token)).first()
        if r is None:
            raise SiteError("not found")
        s.expunge(r)
    base = B.site_dir(r.tenant_id, r.id)
    path = (path or "").lstrip("/")
    if path.startswith("__shots/"):
        root = base / "shots"
        rel = path[len("__shots/"):]
    elif path.startswith("__looks/"):
        root = base / "looks"
        rel = path[len("__looks/"):]
    elif path == "__edit.js":                       # v0.295 the in-page editor (edit preview only)
        return (B.ASSETS / "hoola-edit.js").read_bytes(), "application/javascript", {
            **B.security_headers(form_endpoint(r)), "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
    elif path.startswith("__edit/") or path == "__edit":
        root = base / "edit"
        if not root.exists():
            _ensure_tags(r)
            root = _assemble_edit(_load(r.id))
        rel = path[len("__edit/"):] if path.startswith("__edit/") else ""
    else:
        live = base / "live"
        root = live if live.exists() else B.out_dir(r.tenant_id, r.id, r.version)
        rel = path
    f = (root / rel)
    if not rel or rel.endswith("/"):
        f = f / "index.html"
    try:
        f = f.resolve()
        f.relative_to(root.resolve())
    except (ValueError, OSError):
        raise SiteError("not found")
    if f.is_dir():
        f = f / "index.html"
    if not f.is_file():
        raise SiteError("not found")
    import mimetypes
    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    if f.suffix == ".avif":
        ctype = "image/avif"
    if f.suffix == ".woff2":
        ctype = "font/woff2"
    headers = {**B.security_headers(form_endpoint(r)), "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}
    data = f.read_bytes()
    if path.startswith("__edit") and f.suffix == ".html":
        data = data.replace(b"</body>", f'<script src="/api/site-preview/{token}/__edit.js"></script></body>'.encode(), 1)
    if "frame-ancestors" in headers["Content-Security-Policy"]:
        headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace("frame-ancestors 'self'", "frame-ancestors *")
        headers.pop("X-Frame-Options", None)
    return data, ctype, headers


# ---------------------------------------------------------------- forms -> leads (public endpoint)
_RATE: dict[str, list[float]] = {}


def form_post(site_id: str, data: dict[str, Any], ip: str = "") -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SiteError("bad form")
    if str(data.get("website") or "").strip():          # honeypot filled = a bot
        return {"ok": True}
    iph = hashlib.sha256(f"{ip}|{site_id}".encode()).hexdigest()[:24]
    t = time.time()
    if len(_RATE) > 5000:                 # v0.223 old entries go (the dict grew without end)
        for key in [k for k, v in _RATE.items() if not v or t - v[-1] >= 600]:
            _RATE.pop(key, None)
    hits = [x for x in _RATE.get(iph, []) if t - x < 600]
    if len(hits) >= 5:
        raise SiteError("Bahut zyada baar bheja; thodi der baad.")
    _RATE[iph] = hits + [t]
    name = _tidy(data.get("name"), 120)
    phone = B.digits(str(data.get("phone") or data.get("mobile") or ""))
    email = _tidy(data.get("email"), 160)
    msg = _tidy(data.get("message") or data.get("msg") or data.get("need"), 2000)
    if not phone and not email:
        raise SiteError("Phone ya email chahiye.")
    if phone and len(phone) != 10:
        raise SiteError("Phone number sahi nahi.")
    with session() as s:
        r = s.get(Site, site_id)
        if r is None:
            raise SiteError("not found")
        day = datetime.now(timezone.utc) - timedelta(days=1)
        n = s.scalar(select(func.count()).select_from(SiteLead).where(SiteLead.site_id == site_id, SiteLead.created_at >= day)) or 0
        if n >= 200:
            raise SiteError("Aaj ke liye bahut enquiries; kal dobara.")
        lead = SiteLead(site_id=site_id, tenant_id=r.tenant_id, name=name, phone=phone, email=email, message=msg,
                        page=_tidy(data.get("page"), 160), ip_hash=iph)
        s.add(lead)
        s.flush()
        tenant, sname, conv, lid = r.tenant_id, r.name, r.conv, lead.id
    try:
        if phone:
            from ..telecall import service as tc
            tc.add_lead(tenant, name=name, phone=phone, source="website", need=msg[:300], notes=f"Website {sname}", by="website")
    except Exception:
        log.info("lead to telecall skipped", exc_info=True)
    _publish(tenant, "site_lead", {"id": lid, "site": sname, "name": name, "phone": phone, "email": email,
                                   "message": msg[:300], "say": f"{sname or 'Website'} par nayi enquiry: {name or phone}"}, conv)
    return {"ok": True}


def leads(tenant: str, ref: str = "", limit: int = 100) -> list[dict[str, Any]]:
    with session() as s:
        q = select(SiteLead).where(SiteLead.tenant_id == tenant)
        if ref:
            q = q.where(SiteLead.site_id == _find(s, tenant, ref).id)
        return [{"id": x.id, "name": x.name, "phone": x.phone, "email": x.email, "message": x.message, "page": x.page,
                 "status": x.status, "at": x.created_at.isoformat() if x.created_at else ""}
                for x in s.scalars(q.order_by(SiteLead.created_at.desc()).limit(limit)).all()]


def shot_file(tenant: str, ref: str, name: str) -> Path:
    with session() as s:
        r = _find(s, tenant, ref)
        sid = r.id
    m = re.match(r"look/(\d)/([\w.-]+)$", name or "")
    if m:     # look screenshots: looks/<i>/shots/<file>
        base = (B.site_dir(tenant, sid) / "looks" / m.group(1) / "shots").resolve()
        name = m.group(2)
    else:
        base = (B.site_dir(tenant, sid) / "shots").resolve()
    f = (base / name).resolve()
    f.relative_to(base)
    if not f.is_file():
        raise SiteError("not found")
    return f

"""v0.999.24 PROTOTYPE FIRST (owner: "DONT SHOW THE 3 DESIGNS ... IF BUILD (USER WILL FIRST SEE EVERY PAGE PROTOTYPE IN
WORKSPACE EVERY PAGE AND SECTION IN WEBSITE OR PORTAL OR DASHBOARD) -- IF PLAN (USER WILL SEE THE PERFECT PLAN IN WORKSPACE
... AFTER PLAN APPROVAL A PROTOTYPE) --- PROTOTYPE CAN ALSO BE MODIFIED -- AFTER PROTOTYPE APPROVAL -- REAL WEBSITE BUILD").

Before: after the plan, Hoola wrote three complete looks of the whole site and she picked one - three designs to compare,
three times the writing, and nothing she could reshape before the real build.

Now, once the plan is set (Build mode straight away, Plan mode after her "Build this plan"):
- the PROTOTYPE: every page of the site (public pages AND the signed-in pages of a portal / dashboard) with every section
  in order, real headings and words, the design Hoola chose (colours, font pair, sizes), sample rows on data screens and
  marked picture spaces - drawn by code from short copy the model writes per page (one small call a page, side by side;
  a page whose call fails still shows its sections with their names, never an empty page);
- she changes it as often as she likes: in words (`change`: one call returns only the pages it changed), by her own
  hands on a section (`edit` / `move`: no model, Rs 0), and Undo; every change is a new prototype version and the site's
  plan follows it, so the plan and the prototype never disagree;
- her tap on "Build the real website" (`approve`, bound to the version she saw) builds the real site from it: the
  prototype's pages + sections become the build plan and every section is written from its approved copy. Nothing real
  (pictures, data, logins, payments, checks) is made before that tap; the chat agent can never approve.

The prototype is not the website: no saved data, no forms that send, no payments, no final pictures. Switch
`studio_prototype` (default on); off = the three looks as before."""
from __future__ import annotations

import hashlib
import html as _h
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

from ..db import now, session

log = logging.getLogger("santosh.site")

MAX_PAGES = 40
MAX_SECTIONS = 10
MAX_ITEMS = 8
MAX_ROWS = 6
KEEP_VERSIONS = 30
_LOCK = threading.Lock()


class ProtoError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def on() -> bool:
    from ..config import get_settings
    return bool(getattr(get_settings(), "studio_prototype", True))


def _j(s: Any, d: Any) -> Any:
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _t(x: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(x or "")).strip()[:n]


# ---------------------------------------------------------------- storage: one file per version + a small meta on the row
def _dir(r) -> Path:
    from . import build as B
    d = B.site_dir(r.tenant_id, r.id) / "proto"
    d.mkdir(parents=True, exist_ok=True)
    return d


def meta(r) -> dict[str, Any]:
    return _j(getattr(r, "proto", None), {})


def _save_meta(site_id: str, m: dict[str, Any], **fields) -> None:
    from . import service as S
    S._save(site_id, proto=json.dumps(m, ensure_ascii=False), **fields)


def pages_of(r, v: int | None = None) -> list[dict[str, Any]]:
    m = meta(r)
    n = int(v or m.get("v") or 0)
    if not n:
        return []
    f = _dir(r) / f"v{n}.json"
    return _j(f.read_text(), {}).get("pages", []) if f.exists() else []


def _made_file(r) -> Path:
    return _dir(r) / "making.json"


def made_pages(r) -> list[dict[str, Any]]:
    """v0.999.35 the pages of a prototype being made that are already written (plan order), so the Studio shows each
    page the moment it is made."""
    f = _made_file(r)
    return _j(f.read_text(), {}).get("pages", []) if f.exists() else []


def digest(pages: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(pages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _write_version(r, pages: list[dict[str, Any]], note: str, by: str) -> dict[str, Any]:
    """A new prototype version (the plan follows it). Returns the new meta."""
    with _LOCK:
        from . import service as S
        r = S._load(r.id)
        m = meta(r)
        n = int(m.get("v") or 0) + 1
        hist = list(m.get("history") or [])
        hist.append({"v": n, "note": _t(note, 200), "by": by, "at": now().isoformat()})
        (_dir(r) / f"v{n}.json").write_text(json.dumps({"v": n, "pages": pages, "note": note}, ensure_ascii=False))
        for old in sorted(_dir(r).glob("v*.json"), key=lambda p: int(p.stem[1:] or 0))[:-KEEP_VERSIONS]:
            old.unlink(missing_ok=True)
        m.update(v=n, hash=digest(pages), status="ready", history=hist[-KEEP_VERSIONS:], error="")
        _made_file(r).unlink(missing_ok=True)
        plan = plan_from(pages, _j(r.plan, {}))
        _save_meta(r.id, m, plan=plan, status="prototype", stage="proto", error="")
        return m


# ---------------------------------------------------------------- the pages a prototype shows (from the site's plan)
def _slug(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(x or "").lower()).strip("-")[:40] or "page"


SCREEN_WORDS = (("screen_signin", r"sign.?in|log.?in"), ("screen_dashboard", r"dashboard|overview|home|summary"),
                ("screen_calendar", r"calendar|schedule|slot|timetable|booking"),
                ("screen_approvals", r"approv|review queue|pending"), ("screen_board", r"board|kanban|pipeline|stages"),
                ("screen_form", r"form|apply|new |add |create|request|raise|complaint|register"),
                ("screen_settings", r"setting|profile|account|preferences"),
                ("screen_detail", r"detail|record|view one|profile of"))


def _screen_of(label: str) -> str:
    low = str(label or "").lower()
    for t, rx in SCREEN_WORDS:
        if re.search(rx, low):
            return t
    return "screen_table"


def skeleton(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Every page she will get, with its sections in order: the plan's public pages, then the signed-in pages of a
    portal / dashboard (their screens from the plan). Legal pages are left out (standard text, made at build)."""
    from . import build as B
    from . import taxonomy as T
    out: list[dict[str, Any]] = []
    for p in plan.get("pages") or []:
        if p.get("slug") in B.LEGAL_PAGES or p.get("template_of"):
            continue
        secs = [{"type": s["type"], "label": s.get("label") or T.label_of(s), "design": _t(s.get("design"), 300)}
                for s in (p.get("sections") or [])[:MAX_SECTIONS] if s.get("type")]
        out.append({"slug": p["slug"], "title": _t(p.get("title"), 60) or p["slug"], "for": "public",
                    "why": _t(p.get("why"), 300), "sections": secs})
    for a in ((plan.get("spec") or {}).get("app_pages") or [])[:20]:
        title = _t(a.get("title"), 60)
        if not title:
            continue
        types = [x for x in (a.get("types") or []) if T.is_screen(x)]
        shows = [x for x in (a.get("shows") or []) if x][:MAX_SECTIONS]
        secs = []
        for i, lab in enumerate(shows or [title]):
            typ = types[i] if i < len(types) else _screen_of(lab)
            secs.append({"type": typ, "label": _t(lab, 60) or T.label_of(typ), "design": ""})
        out.append({"slug": "app-" + _slug(title), "title": title, "for": a.get("for") or "member",
                    "why": _t(a.get("why"), 300), "sections": _uniq(secs)})
    return out[:MAX_PAGES]


def _uniq(secs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One section type per page (the build keys a section by page + type): a second one becomes its own custom type."""
    from . import taxonomy as T
    seen: set[str] = set()
    out = []
    for s in secs:
        typ = s["type"]
        if typ in seen:
            typ = ("custom_" + re.sub(r"[^a-z0-9]+", "_", str(s.get("label") or typ).lower()).strip("_"))[:37]
            if not T.CUSTOM.fullmatch(typ) or typ in seen:
                continue
        seen.add(typ)
        out.append({**s, "type": typ})
    return out


# ---------------------------------------------------------------- the words of each page (one small call a page)
COPY_SYSTEM = """You write the PROTOTYPE of one page of a website, portal or dashboard: short, real copy for each section,
so the owner sees exactly what each part of the page will say and hold before anything is built.

For EVERY section listed (same order, same count) give:
- heading: the section's real heading (max 9 words)
- line: one or two sentences of real copy (max 40 words)
- items: the section's parts as short strings (max 8, each max 14 words) - features, steps, plans with prices, FAQ
  questions, testimonial quotes with a first name, KPI tiles as "Label: value", form fields as "Field name",
  table columns are NOT items
- cta: a button label when the section has one ("" if none)
- cols + rows: ONLY for a data screen (screen_table, screen_dashboard, screen_approvals, screen_board): 3-6 column names
  and 3-5 rows of SAMPLE values matching the columns (clearly made-up sample data)

Rules: write in the language of the owner's words; use the business facts given and never invent a phone number, an
address, an email, a price list she did not give or a real person's name - write a sample marked as such ("Plan A -
Rs 499 (sample)") or leave it out; no lorem ipsum; plain words a customer understands.
Reply as {"sections": [{"heading": "", "line": "", "items": [], "cta": "", "cols": [], "rows": [[]]}]}"""


def _facts_text(r) -> str:
    from . import service as S
    return S._facts_text(_j(r.facts, {}))


def _clean_copy(raw: Any, sec: dict[str, Any]) -> dict[str, Any]:
    d = raw if isinstance(raw, dict) else {}
    out = {"heading": _t(d.get("heading"), 90), "line": _t(d.get("line"), 320),
           "items": [_t(x, 120) for x in (d.get("items") or []) if _t(x, 120)][:MAX_ITEMS] if isinstance(d.get("items"), list) else [],
           "cta": _t(d.get("cta"), 40)}
    if isinstance(d.get("cols"), list) and d.get("cols"):
        cols = [_t(x, 30) for x in d["cols"] if _t(x, 30)][:6]
        rows = [[_t(c, 40) for c in row][:len(cols)] for row in (d.get("rows") or []) if isinstance(row, list)][:MAX_ROWS]
        if cols:
            out["cols"], out["rows"] = cols, rows
    if not out["heading"]:
        out["heading"] = sec.get("label") or ""
        out["draft"] = True
    return out


def _page_copy(r, page: dict[str, Any], site_words: str) -> list[dict[str, Any]]:
    from . import ai as AI
    from . import taxonomy as T
    lines = [f"{i + 1}. {s['type']} ({T.label_of(s)})" + (f" - {s['design']}" if s.get("design") else "")
             for i, s in enumerate(page["sections"])]
    prompt = (f"WEBSITE: {r.name or ''}\nOWNER'S WORDS: {site_words[:1500]}\nBUSINESS FACTS (data): {_facts_text(r)[:1500]}\n"
              f"PAGE: {page['title']} ({'public page' if page['for'] == 'public' else 'signed-in ' + page['for'] + ' page'})"
              + (f" - {page['why']}" if page.get("why") else "") + "\nSECTIONS:\n" + "\n".join(lines))
    try:
        got = AI.ask_json(COPY_SYSTEM, prompt, 3000, "site_edit")
        raw = got.get("sections") if isinstance(got.get("sections"), list) else []
    except Exception as e:                       # noqa: BLE001 - a page whose words did not come still shows its sections
        log.info("prototype copy for %s failed: %s", page["slug"], e)
        raw = []
    return [{**s, **_clean_copy(raw[i] if i < len(raw) else None, s)} for i, s in enumerate(page["sections"])]


def start(site_id: str) -> None:
    """Called when the plan is set: the prototype is made in the background (status prototype, meta making)."""
    from . import service as S
    r = S._load(site_id)
    m = {**meta(r), "status": "making", "error": "", "done": 0, "total": len(skeleton(_j(r.plan, {})))}
    _made_file(r).unlink(missing_ok=True)
    _save_meta(site_id, m, status="prototype", stage="proto", stop=False, error="")
    S._emit(S._load(site_id))
    S._start(site_id, "proto")


def make_job(site_id: str) -> None:
    """The background job: every page's copy, side by side; then version 1 (or the next version)."""
    from concurrent.futures import ThreadPoolExecutor

    from ..usage import scope
    from . import activity as ACT
    from . import service as S
    r = S._load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            pages = skeleton(_j(r.plan, {}))
            if not pages:
                raise ProtoError("The plan has no pages yet.")
            S._work(r, "start", "Making the prototype", f"{len(pages)} pages, every section")
            done = {"n": 0, "made": {}}
            lock = threading.Lock()
            order = [p["slug"] for p in pages]

            def one(pg):
                secs = _page_copy(r, pg, r.brief or "")
                with lock:
                    done["n"] += 1
                    done["made"][pg["slug"]] = {**pg, "sections": secs}          # v0.999.35 shown the moment it is made
                    try:
                        _made_file(r).write_text(json.dumps({"pages": [done["made"][s] for s in order if s in done["made"]]},
                                                            ensure_ascii=False))
                    except OSError:
                        log.warning("prototype: could not keep a made page", exc_info=True)
                    ACT.step(r.tenant_id, r.id, "Making the prototype", f"{pg['title']}: {len(secs)} sections",
                             key="proto", done=done["n"], total=len(pages))
                return {**pg, "sections": secs}
            width = max(1, min(6, int(getattr(S._settings(), "site_parallel", 3) or 3) * 2))
            with ThreadPoolExecutor(max_workers=width, thread_name_prefix=f"proto-{r.id[:6]}") as ex:
                out = list(ex.map(S._in_ctx(one), pages))
            if S._load(site_id).stop:
                _save_meta(site_id, {**meta(S._load(site_id)), "status": "stopped"}, status="stopped")
                return
            _write_version(S._load(site_id), out, "first prototype", "hoola")
            r = S._load(site_id)
            S._work(r, "waiting", "Prototype ready", "change anything, then build the real website")
            S._emit(r, push=True)
        except Exception as e:
            log.exception("prototype failed")
            r = S._load(site_id)
            _save_meta(site_id, {**meta(r), "status": "failed", "error": _t(e, 300)}, status="failed",
                       error=_t(f"The prototype could not be made: {e}", 300))
            S._emit(S._load(site_id), push=True)


# ---------------------------------------------------------------- the plan follows the prototype
def plan_from(pages: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    """The site plan with the prototype's pages + sections (public pages in its order; legal / list pages kept; signed-in
    pages into spec.app_pages)."""
    from . import build as B
    plan = json.loads(json.dumps(plan or {}))
    old = {p["slug"]: p for p in plan.get("pages") or []}
    out = []
    for pg in pages:
        if pg.get("for", "public") != "public":
            continue
        base = dict(old.get(pg["slug"]) or {"slug": pg["slug"], "title": pg["title"],
                                             "nav": "Home" if pg["slug"] == "home" else pg["title"][:24]})
        designs = {s["type"]: s.get("design") for s in base.get("sections") or []}
        base["title"] = pg["title"]
        if pg["slug"] != "home":
            base["nav"] = pg["title"][:24]
        base["sections"] = [{"type": s["type"], "label": s.get("label") or s["type"],
                             "design": s.get("design") or designs.get(s["type"]) or s.get("line") or ""}
                            for s in pg.get("sections") or []]
        out.append(base)
    keep = [p for p in plan.get("pages") or [] if p.get("slug") in B.LEGAL_PAGES or p.get("template_of")]
    plan["pages"] = out + [p for p in keep if p["slug"] not in {x["slug"] for x in out}]
    app = [{"title": pg["title"], "for": pg.get("for") or "member", "why": pg.get("why") or "",
            "shows": [s.get("label") or s["type"] for s in pg.get("sections") or []],
            "types": [s["type"] for s in pg.get("sections") or []]} for pg in pages if pg.get("for", "public") != "public"]
    if app or (plan.get("spec") or {}).get("app_pages"):
        plan.setdefault("spec", {})["app_pages"] = app
    return plan


# ---------------------------------------------------------------- what she sees
def view(r) -> dict[str, Any]:
    from . import service as S
    m = meta(r)
    pages = pages_of(r) if m.get("v") else []
    base = S.preview_url(r)
    making = m.get("status") == "making"
    made = [{"slug": p["slug"], "title": p["title"], "for": p.get("for") or "public",
             "sections": [s.get("label") or s["type"] for s in p.get("sections") or []],
             "url": (base + f"__proto/{p['slug']}.html?m={len(p.get('sections') or [])}") if base else ""}
            for p in (made_pages(r) if making else [])]
    return {"v": int(m.get("v") or 0), "hash": m.get("hash") or "", "status": m.get("status") or "",
            "made": made, "total": int(m.get("total") or 0) if making else 0,
            "error": m.get("error") or "", "approved_v": int(m.get("approved_v") or 0),
            "history": list(m.get("history") or [])[-12:],
            "pages": [{"slug": p["slug"], "title": p["title"], "for": p.get("for") or "public",
                       "sections": [{"type": s["type"], "label": s.get("label") or s["type"], "heading": s.get("heading") or "",
                                     "line": s.get("line") or "", "items": s.get("items") or [], "cta": s.get("cta") or ""}
                                    for s in p.get("sections") or []],
                       "url": (base + f"__proto/{p['slug']}.html") if base else ""} for p in pages]}


def get(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    return {**view(r), "site": r.id, "status_site": r.status}


# ---------------------------------------------------------------- changes: her words, her hands, Undo
CHANGE_SYSTEM = """You change the PROTOTYPE of a website / portal / dashboard as the owner asks. You get every page with its
sections (type, label, heading, line, items, cta, cols, rows) and her words.

Return ONLY what changes:
{"pages": [ every page you changed or added, COMPLETE - slug, title, for ("public" | "member" | "staff"), sections
  (each: type, label, heading, line, items, cta, and cols + rows for data screens) ],
 "removed": [slugs of pages she asked to remove],
 "order": [every page slug in the new order, only if she asked to reorder pages],
 "say": "one short sentence of what you changed"}

Section types: keep a section's type when you only change its words. A new section uses a type from this list or
"custom_<short_name>" for anything else: SECTION_TYPES. Signed-in pages use screen_* types. A new page needs a short
lowercase slug. Never invent a phone, address, email or a real person's name; samples are marked "(sample)".
Change nothing she did not ask for."""


def _norm_page(p: Any) -> dict[str, Any] | None:
    from . import taxonomy as T
    if not isinstance(p, dict):
        return None
    title = _t(p.get("title"), 60)
    slug = _slug(p.get("slug") or title)
    if not title:
        return None
    secs = []
    for s in (p.get("sections") or [])[:MAX_SECTIONS]:
        if not isinstance(s, dict):
            continue
        typ = str(s.get("type") or "").strip()
        if not T.is_section(typ):
            typ = ("custom_" + re.sub(r"[^a-z0-9]+", "_", str(s.get("label") or typ or "part").lower()).strip("_"))[:37]
            if not T.CUSTOM.fullmatch(typ):
                continue
        label = _t(s.get("label"), 60) or T.label_of(typ)
        sec = {"type": typ, "label": label, "design": _t(s.get("design"), 300)}
        secs.append({**sec, **_clean_copy(s, sec)})
    fo = p.get("for") if p.get("for") in ("public", "member", "staff") else "public"
    return {"slug": slug, "title": title, "for": fo, "why": _t(p.get("why"), 300), "sections": _uniq(secs)}


def _site(tenant: str, ref: str):
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    if r.status != "prototype" or meta(r).get("status") != "ready":
        if r.status == "prototype" and meta(r).get("status") == "making":
            raise ProtoError("The prototype is still being made; one moment.", 409)
        raise ProtoError("This website has no prototype to change right now.", 409)
    return r


def change(tenant: str, ref: str, words: str, conv: str = "") -> dict[str, Any]:
    """Her words -> the pages they touch, rewritten in one call; a new version (Undo goes back)."""
    from . import ai as AI
    from . import guard
    from . import taxonomy as T
    words = _t(words, 1500)
    if not words:
        raise ProtoError("What should change in the prototype?")
    bad = guard.brief_problem(words)
    if bad:
        raise ProtoError(bad)
    r = _site(tenant, ref)
    pages = pages_of(r)
    compact = [{k: p[k] for k in ("slug", "title", "for")} | {"sections": [
        {k: s.get(k) for k in ("type", "label", "heading", "line", "items", "cta", "cols", "rows") if s.get(k)}
        for s in p["sections"]]} for p in pages]
    system = CHANGE_SYSTEM.replace("SECTION_TYPES", ", ".join(sorted([*T.SECTIONS, *T.SCREENS])))
    got = AI.ask_json(system, f"BUSINESS FACTS (data): {_facts_text(r)[:1200]}\nPROTOTYPE:\n"
                      + json.dumps(compact, ensure_ascii=False)[:60000] + f"\n\nHER WORDS: {words}", 12000, "site_edit")
    new = apply_change(pages, got)
    if new == pages:
        return {**view(r), "changed": False, "say": "Nothing in the prototype matched that; say which page or part."}
    m = _write_version(r, new, words, "hoola")
    from . import service as S
    r = S._load(r.id)
    S._emit(r)
    return {**view(r), "changed": True, "version": m["v"], "say": _t(got.get("say"), 300) or "Prototype changed."}


def apply_change(pages: list[dict[str, Any]], got: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's answer applied by code: changed / new pages replace or join, removed pages go (never all of them),
    the order only when every page is named. A page it could not read is left as it was."""
    out = [dict(p) for p in pages]
    by = {p["slug"]: i for i, p in enumerate(out)}
    for raw in got.get("pages") or []:
        p = _norm_page(raw)
        if not p:
            continue
        old = out[by[p["slug"]]] if p["slug"] in by else None
        if old:
            designs = {s["type"]: s.get("design") for s in old.get("sections") or []}
            for s in p["sections"]:
                s["design"] = s.get("design") or designs.get(s["type"]) or ""
            if not p["why"]:
                p["why"] = old.get("why") or ""
            out[by[p["slug"]]] = p
        elif len(out) < MAX_PAGES:
            by[p["slug"]] = len(out)
            out.append(p)
    gone = {_slug(x) for x in got.get("removed") or [] if isinstance(x, str)}
    if gone and len([p for p in out if p["slug"] not in gone]) >= 1:
        out = [p for p in out if p["slug"] not in gone or p["slug"] == "home"]
    order = [_slug(x) for x in got.get("order") or [] if isinstance(x, str)]
    if order and set(order) == {p["slug"] for p in out}:
        pos = {s: i for i, s in enumerate(order)}
        out.sort(key=lambda p: pos[p["slug"]])
    return out


EDITABLE = ("heading", "line", "cta", "items")


def edit(tenant: str, ref: str, slug: str, index: int, field: str, value: Any, base: str = "") -> dict[str, Any]:
    """Her own hands on one section's words (no model, Rs 0)."""
    from . import guard
    if field not in EDITABLE:
        raise ProtoError("Only the heading, line, button or items can be edited here.")
    r = _site(tenant, ref)
    if base and base != meta(r).get("hash"):
        raise ProtoError("The prototype changed meanwhile; look again and edit.", 409)
    pages = pages_of(r)
    pg = next((p for p in pages if p["slug"] == slug), None)
    if pg is None or not 0 <= int(index) < len(pg["sections"]):
        raise ProtoError("That part of the prototype is not there any more.", 404)
    if field == "items":
        val: Any = [_t(x, 120) for x in (value if isinstance(value, list) else str(value or "").split("\n")) if _t(x, 120)][:MAX_ITEMS]
        text = " ".join(val)
    else:
        val = _t(value, {"heading": 90, "line": 320, "cta": 40}[field])
        text = val
    bad = guard.brief_problem(text) if text else ""
    if bad:
        raise ProtoError(bad)
    sec = pg["sections"][int(index)]
    if sec.get(field) == val:
        return {**view(r), "changed": False}
    sec[field] = val
    sec.pop("draft", None)
    m = _write_version(r, pages, f"{pg['title']}: {sec.get('label')} {field} edited", "her")
    from . import service as S
    S._emit(S._load(r.id))
    return {**view(S._load(r.id)), "changed": True, "version": m["v"]}


def move(tenant: str, ref: str, slug: str, index: int, op: str) -> dict[str, Any]:
    """Up / down / remove one section (no model)."""
    r = _site(tenant, ref)
    pages = pages_of(r)
    pg = next((p for p in pages if p["slug"] == slug), None)
    i = int(index)
    if pg is None or not 0 <= i < len(pg["sections"]):
        raise ProtoError("That part of the prototype is not there any more.", 404)
    secs = pg["sections"]
    if op == "up" and i > 0:
        secs[i - 1], secs[i] = secs[i], secs[i - 1]
    elif op == "down" and i < len(secs) - 1:
        secs[i + 1], secs[i] = secs[i], secs[i + 1]
    elif op == "remove":
        if len(secs) == 1:
            raise ProtoError("A page needs at least one section; remove the page in the chat instead.")
        label = secs.pop(i).get("label")
        op = f"removed {label}"
    else:
        return {**view(r), "changed": False}
    m = _write_version(r, pages, f"{pg['title']}: section {op}", "her")
    from . import service as S
    S._emit(S._load(r.id))
    return {**view(S._load(r.id)), "changed": True, "version": m["v"]}


def undo(tenant: str, ref: str) -> dict[str, Any]:
    """Back to the version before (as a new version, so Undo can itself be undone)."""
    r = _site(tenant, ref)
    m = meta(r)
    hist = list(m.get("history") or [])
    if len(hist) < 2:
        raise ProtoError("Nothing to undo yet.")
    prev = hist[-2]["v"]
    pages = pages_of(r, prev)
    if not pages:
        raise ProtoError("That version is no longer kept.", 404)
    mm = _write_version(r, pages, f"undo: back to version {prev}", "her")
    from . import service as S
    S._emit(S._load(r.id))
    return {**view(S._load(r.id)), "changed": True, "version": mm["v"]}


# ---------------------------------------------------------------- her tap: build the real website from it
def guidance(pages: list[dict[str, Any]]) -> dict[str, str]:
    """Per section key: the approved prototype copy the real section is written from."""
    from . import service as S
    out = {}
    for pg in pages:
        if pg.get("for", "public") != "public":
            continue
        for s in pg.get("sections") or []:
            bits = [f"heading: {s['heading']}" if s.get("heading") and not s.get("draft") else "",
                    f"text: {s['line']}" if s.get("line") else "",
                    ("parts: " + " | ".join(s["items"])) if s.get("items") else "",
                    f"button: {s['cta']}" if s.get("cta") else "",
                    ("columns: " + ", ".join(s["cols"])) if s.get("cols") else ""]
            bits = [b for b in bits if b]
            if bits:
                out[S.sec_key(pg["slug"], s["type"])] = (
                    "THE OWNER APPROVED THIS SECTION IN THE PROTOTYPE - keep its heading, its parts and their order, write "
                    "it fully in the site's design (samples marked '(sample)' stay samples or become her real facts): "
                    + "; ".join(bits))[:1800]
    return out


def tokens_for(r) -> tuple[str, dict[str, Any], bool]:
    """The design the prototype is drawn in and the real site is built in: her own design reference / the AI's
    choice from her words (look 1 of the old looks), else the site's style."""
    from . import build as B
    from . import inspire as IN
    from . import library as L
    facts = _j(r.facts, {})
    ref = IN.look_zero(facts)
    style = ref["style"] if ref else r.style
    br = L.brief(r.field, r.goal, style)
    if ref:
        return style, B.tokens(style, br["palettes"][0], None, ref.get("overrides") or {}), ref.get("source") != "ai"
    return style, B.tokens(style, br["palettes"][0], facts.get("brand_colors")), False


def approve(tenant: str, ref: str, h: str, conv: str = "") -> dict[str, Any]:
    """HER TAP ONLY (the route, never the chat agent): the prototype version she saw becomes the real build."""
    from . import service as S
    r = _site(tenant, ref)
    m = meta(r)
    if not h or h != m.get("hash"):
        raise ProtoError("The prototype changed after you looked; look at it again and tap Build.", 409)
    pages = pages_of(r)
    style, tk, mine = tokens_for(r)
    plan = plan_from(pages, _j(r.plan, {}))
    m.update(status="approved", approved_v=m["v"], approved_at=now().isoformat())
    look = {"tokens": tk, "from": "prototype", "dna": None, "mine": mine, "proto_v": m["v"]}
    states = {}
    _save_meta(r.id, m, plan=plan, style=style, look=json.dumps(look), status="building", stage="build", stop=False,
               error="", conv=conv or r.conv)
    r = S._load(r.id)
    S._save(r.id, board=S._board(r, plan, states, "Building the real website from your prototype"))
    from . import library as L
    L.learn(r.field, "style", [style], 2)
    S._emit(S._load(r.id))
    if react_on():                               # v0.999.65 D4: a React website from the kit, built in the App Engine box
        S._start(r.id, "proto_react")
    else:
        S._start(r.id, "proto_build", extra=guidance(pages))
    return {**S.view(S._load(r.id)), "say": f"Building the real website from prototype version {m['v']}."}


# ---------------------------------------------------------------- v0.999.65 D4: the React website from the prototype
def react_on() -> bool:
    from ..config import get_settings
    st = get_settings()
    return bool(getattr(st, "studio_react_sites", False)) and bool(getattr(st, "app_engine", True))


def react_link(r) -> dict[str, Any]:
    """The App Engine app this website is written into (facts.react_app), {} when none."""
    return dict(_j(r.facts, {}).get("react_app") or {})


def site_link(r) -> dict[str, Any]:
    """v0.999.77 D8: what the React website needs to use her HTML website's own forms, booking and shop on Hoola (the
    same leads, booking book, products, stock and orders): its id + the shop's public settings and products."""
    out: dict[str, Any] = {"id": r.id}
    try:
        from . import service as S
        from . import shop as SH
        cfg = S._shop_cfg(r)
        if cfg.get("on"):
            out["shop"] = {"on": True, "cod": bool(cfg.get("cod")), "pickup": bool(cfg.get("pickup")),
                           "upi": bool(cfg.get("upi")),
                           "products": [{k: x.get(k) for k in ("slug", "title", "price", "unit", "in_stock")}
                                        for x in SH.products(r.id)][:48]}
    except Exception:                                # noqa: BLE001 - no shop: the products stay her words
        log.info("shop not read for the React website", exc_info=True)
    return out


def react_job(site_id: str) -> None:
    """Her approved prototype -> a React website: the design genome from the colour she approved, every page written
    by the writer (kit blocks + her words + her facts; custom sections by the model on her tier through AutoFix + the
    rules), built in the box (every page pre-rendered, islands only). The site's preview shows the app's preview."""
    from ..appengine import critic as C
    from ..appengine import genome as GN
    from ..appengine import service as AE
    from ..appengine import writer as W
    from ..usage import scope
    from . import ai as AI
    from . import service as S
    r = S._load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            pages = pages_of(r)
            facts = _j(r.facts, {})
            wfacts = {**facts, "_site": site_link(r)}     # v0.999.77 D8: her website's forms, booking and shop
            _, tk, _ = tokens_for(r)
            link = react_link(r)
            S._work(r, "start", "Writing the website", f"{len(pages)} pages from your prototype, in React")
            ref = link.get("id") or ""
            if ref:
                try:
                    AE._load(r.tenant_id, ref)
                except Exception:                    # noqa: BLE001 - the app was removed: a new one
                    ref = ""
            if not ref:
                gen = GN.generate(seed=r.id, pin=str(tk.get("primary") or ""), words=r.brief or "", name=r.name or "")
                app = AE.create(r.tenant_id, name=r.name or "My website", brief=r.brief or "", genome=gen, render="site",
                                conversation_id=r.conv or "")
                ref = app["id"]
            mdl = lambda system, prompt: AI.ask(system, prompt, 6000, "section")   # noqa: E731 - her tier's web writer
            review: dict[str, Any] | None = None
            if C.on():
                # v0.999.67 D5: write -> build -> a SEPARATE critic looks on a computer + a phone -> code fixes, the best kept
                spec = (_j(r.plan, {}) or {}).get("spec") or {}
                gdir = ((AE._genome(AE._load(r.tenant_id, ref)) or {}).get("direction") or {}).get("seed") or ""
                review = C.improve(r.tenant_id, ref, pages, name=r.name or "", facts=wfacts, model=mdl, seed=r.id,
                                   brief=r.brief or "", purpose=str(spec.get("purpose") or ""),
                                   field=str(spec.get("field_hint") or ""), kind=str(spec.get("kind") or ""),
                                   direction=str(gdir), step=lambda a, b: S._work(S._load(site_id), a, b, ""))
                st, res = review["write"], review["build"]
            else:
                st = W.write_app(r.tenant_id, ref, pages, name=r.name or "", facts=wfacts, model=mdl, seed=r.id)
                S._work(S._load(site_id), "start", "Building the pages", "every page as finished HTML, code only where it moves")
                res = AE.build(r.tenant_id, ref)
            app = AE._load(r.tenant_id, ref)
            link = {"id": app.id, "number": app.number, "version": app.version, "built": bool(res.get("built")),
                    "preview": f"/api/app-preview/{app.preview_token}/" if app.version else "",
                    "written": st["written"], "fixed": st["fixed"], "refused": st["refused_left"],
                    "custom": st["custom_written"], "blanks": st["blanks"], "proto_v": meta(r).get("approved_v"),
                    "say": res.get("say", "")[:600]}
            if review is not None:
                link["critic"] = {"score": review.get("score"), "passed": review.get("passed"), "bar": review.get("bar"),
                                  "rounds": len(review.get("rounds") or []), "best_round": review.get("best_round"),
                                  "inr": review.get("inr"), "hero": review.get("hero"), "model": review["critic"].get("model"),
                                  "skipped": review.get("skipped", ""), "say": C.say(review),
                                  "refs": int((review.get("refs") or {}).get("used") or 0),
                                  "problems": ((review.get("rounds") or [{}])[-1].get("problems") or [])[:3]}
            facts["react_app"] = link
            ok = bool(res.get("built"))
            S._save(site_id, facts=json.dumps(facts), status="ready" if ok else "failed",
                    error="" if ok else _t("The React website did not build: " + res.get("say", ""), 300))
            r = S._load(site_id)
            S._work(r, "done" if ok else "error", "Your website is ready" if ok else "The build hit a problem",
                    (f"{len(pages)} pages, {st['fixed']} small fixes made by code" + (
                        f"; {C.say(review)}" if review is not None else "") + (
                        f"; fill in: {', '.join(st['blanks'])}" if st.get("blanks") else "")) if ok else res.get("say", "")[:200])
            S._emit(r, push=True)
        except Exception as e:
            log.exception("react website failed")
            S._save(site_id, status="failed", error=_t(f"The React website could not be made: {e}", 300))
            S._emit(S._load(site_id), push=True)


def build_job(site_id: str, extra: dict[str, str] | None = None) -> None:
    """Pictures first (her photos, then made / stock), then the normal build with the prototype's copy per section."""
    from ..usage import scope
    from . import service as S
    r = S._load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            S._ensure_pictures(r)
        except Exception:                        # noqa: BLE001 - the build goes on with what there is
            log.info("pictures before the build failed", exc_info=True)
    S.run_build(site_id, None, "first version from your prototype", extra or {})


# ---------------------------------------------------------------- drawing: one page of the prototype as HTML
FONT_PREFIX = "__proto/assets/fonts/"


def _e(x: Any) -> str:
    return _h.escape(str(x or ""), quote=True)


PROTO_CSS = """*{box-sizing:border-box}body{margin:0;background:var(--c-bg);color:var(--c-ink);font-family:var(--font-body);
font-size:16px;line-height:1.55}a{color:inherit}h1,h2,h3{font-family:var(--font-head);line-height:1.15;margin:0 0 .4em;
text-wrap:balance}.pbar{display:flex;gap:6px;align-items:center;justify-content:center;padding:6px 12px;font:12px/1.4
system-ui,sans-serif;background:#1f1d1a;color:#f3f1ec;letter-spacing:.02em}.pbar b{font-weight:600}
.nav{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;padding:14px max(16px,4vw);border-bottom:1px solid
var(--c-line);background:var(--c-surface)}.nav .brand{font-family:var(--font-head);font-weight:700;font-size:18px;
margin-right:auto}.nav a{text-decoration:none;font-size:14px;color:var(--c-muted)}.nav a.on{color:var(--c-ink);
font-weight:600}.nav .grp{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--c-muted);
border-left:1px solid var(--c-line);padding-left:14px}.ps{position:relative;padding:44px max(16px,6vw);
border-bottom:1px dashed var(--c-line);cursor:pointer;outline-offset:-3px}.ps:hover{outline:2px dashed var(--c-primary)}
.ps.sel{outline:3px solid var(--c-primary)}.tag{display:block;margin:0 0 12px;font:11px/1.4
system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:var(--c-muted)}.in{max-width:1080px;margin:0 auto}
.lead{color:var(--c-muted);max-width:62ch;margin:0 0 18px}.btn{display:inline-block;padding:10px 18px;border-radius:
var(--radius);background:var(--c-primary);color:var(--c-on-primary);font-weight:600;font-size:15px;border:0}
.btn.ghost{background:transparent;color:var(--c-ink);border:1px solid var(--c-line)}.grid{display:grid;
grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}.card{background:var(--c-surface);border:1px solid
var(--c-line);border-radius:var(--radius);padding:16px}.pic{background:repeating-linear-gradient(135deg,var(--c-surface),
var(--c-surface) 10px,var(--c-line) 10px,var(--c-line) 11px);border:1px solid var(--c-line);border-radius:var(--radius);
display:grid;place-items:center;color:var(--c-muted);font:12px system-ui,sans-serif;min-height:180px}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:28px;align-items:center}
.hero h1{font-size:clamp(30px,5vw,48px)}.tbl{overflow-x:auto;border:1px solid var(--c-line);border-radius:var(--radius);
background:var(--c-surface)}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:9px 12px;
border-bottom:1px solid var(--c-line)}th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--c-muted)}
.kpi b{display:block;font-size:24px;font-family:var(--font-head)}.kpi span{color:var(--c-muted);font-size:13px}
.field{display:grid;gap:4px;margin-bottom:12px}.field i{font-style:normal;font-size:13px;color:var(--c-muted)}
.field u{display:block;height:40px;border:1px solid var(--c-line);border-radius:var(--radius);background:var(--c-bg)}
.form{max-width:440px}.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.col{background:var(--c-surface);border:1px solid var(--c-line);border-radius:var(--radius);padding:10px;min-height:120px}
.col h3{font-size:14px}.chip{display:inline-block;font-size:12px;padding:2px 8px;border-radius:99px;background:
var(--c-surface);border:1px solid var(--c-line);color:var(--c-muted)}.cal{display:grid;grid-template-columns:repeat(7,1fr);
gap:4px}.cal div{border:1px solid var(--c-line);border-radius:6px;min-height:54px;padding:4px;font-size:12px;color:
var(--c-muted)}.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;padding:10px 0;
border-bottom:1px solid var(--c-line)}.foot{padding:28px max(16px,6vw);color:var(--c-muted);font-size:13px;text-align:center}
.draft{color:var(--c-muted);font-style:italic}"""

PROTO_JS = """(function(){var sel=null;function send(m){try{parent.postMessage(Object.assign({hoola:'proto'},m),'*')}catch(e){}}
send({t:'page',page:document.body.dataset.page});
document.addEventListener('click',function(e){var a=e.target.closest('a');if(a&&a.getAttribute('href')&&a.getAttribute('href').indexOf('.html')>0)return;
var s=e.target.closest('.ps');if(!s)return;e.preventDefault();if(sel)sel.classList.remove('sel');sel=s;s.classList.add('sel');
send({t:'pick',page:document.body.dataset.page,i:+s.dataset.pi,type:s.dataset.ps,label:s.dataset.label})},true);
window.addEventListener('message',function(e){var d=e.data||{};if(d.hoola!=='proto-cmd')return;
if(d.t==='clear'&&sel){sel.classList.remove('sel');sel=null}
if(d.t==='show'){var x=document.querySelector('.ps[data-pi="'+d.i+'"]');if(x){x.scrollIntoView({block:'center'});if(sel)sel.classList.remove('sel');sel=x;x.classList.add('sel')}}});})();"""


def _kv(x: str) -> tuple[str, str]:
    a, _, b = str(x).partition(":")
    return (a.strip(), b.strip()) if b else (str(x).strip(), "")


def _section_html(s: dict[str, Any], i: int) -> str:
    typ = s["type"]
    head = f"<h2>{_e(s.get('heading'))}</h2>" if s.get("heading") else ""
    if s.get("draft"):
        head = f"<h2 class='draft'>{_e(s.get('heading'))}</h2>"
    line = f"<p class='lead'>{_e(s.get('line'))}</p>" if s.get("line") else ""
    items = s.get("items") or []
    cta = f"<p><span class='btn'>{_e(s['cta'])}</span></p>" if s.get("cta") else ""
    cols, rows = s.get("cols") or [], s.get("rows") or []
    table = ("<div class='tbl'><table><thead><tr>" + "".join(f"<th>{_e(c)}</th>" for c in cols) + "</tr></thead><tbody>"
             + "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>" for row in rows)
             + "</tbody></table></div>") if cols else ""
    if typ == "hero":
        h1 = f"<h1>{_e(s.get('heading'))}</h1>" if s.get("heading") else ""
        body = (f"<div class='hero'><div>{h1}{line}{cta}"
                + (f"<p>{''.join(f'<span class=chip>{_e(x)}</span> ' for x in items[:4])}</p>" if items else "")
                + "</div><div class='pic'>Picture: the front of the site</div></div>")
    elif typ == "screen_signin":
        fields = items or ["Mobile number", "Password"]
        body = (f"<div class='form card'>{head}{line}" + "".join(f"<div class='field'><i>{_e(f)}</i><u></u></div>" for f in fields)
                + f"<span class='btn'>{_e(s.get('cta') or 'Sign in')}</span></div>")
    elif typ == "screen_form":
        body = (f"{head}{line}<div class='form'>" + "".join(f"<div class='field'><i>{_e(f)}</i><u></u></div>"
                                                           for f in (items or ['Your details']))
                + f"<span class='btn'>{_e(s.get('cta') or 'Submit')}</span></div>")
    elif typ == "screen_dashboard":
        kpis = "".join(f"<div class='card kpi'><b>{_e(_kv(x)[1] or '—')}</b><span>{_e(_kv(x)[0])}</span></div>"
                       for x in items[:4])
        body = f"{head}{line}<div class='grid'>{kpis}</div>" + (f"<div style='margin-top:16px'>{table}</div>" if table else "")
    elif typ == "screen_board":
        names = cols or ["To do", "Doing", "Done"]
        body = f"{head}{line}<div class='cols'>" + "".join(
            f"<div class='col'><h3>{_e(c)}</h3>" + "".join(f"<div class='card' style='margin-top:6px;padding:8px'>{_e(x)}</div>"
                                                         for x in items[k::len(names)][:3]) + "</div>"
            for k, c in enumerate(names)) + "</div>"
    elif typ == "screen_calendar":
        body = f"{head}{line}<div class='cal'>" + "".join(
            f"<div>{d + 1}" + (f"<br><span class='chip'>{_e(items[d % len(items)])}</span>" if items and d % 5 == 1 else "")
            + "</div>" for d in range(14)) + "</div>"
    elif typ == "screen_approvals":
        lst = "".join(f"<div class='row'><span>{_e(x)}</span><span><span class='btn ghost'>Reject</span> "
                      f"<span class='btn'>Approve</span></span></div>" for x in items[:5])
        body = f"{head}{line}{lst}{table}"
    elif typ in ("screen_detail", "screen_settings"):
        body = f"{head}{line}<div class='card'>" + "".join(
            f"<div class='row'><span>{_e(_kv(x)[0])}</span><b>{_e(_kv(x)[1])}</b></div>" for x in items) + f"</div>{cta}"
    elif typ.startswith("screen_"):
        body = f"{head}{line}{table or ''}" + ("" if table else "".join(f"<div class='row'>{_e(x)}</div>" for x in items)) + cta
    else:
        pics = any(w in typ for w in ("gallery", "team", "showcase", "portfolio", "photo"))
        grid = "".join(f"<div class='card'>" + (f"<div class='pic' style='min-height:120px;margin-bottom:10px'>Picture</div>"
                                               if pics else "") + f"{_e(x)}</div>" for x in items)
        body = f"{head}{line}" + (f"<div class='grid'>{grid}</div>" if grid else "") + table + cta
    return (f"<section class='ps' data-pi='{i}' data-ps='{_e(typ)}' data-label='{_e(s.get('label'))}' tabindex='0'>"
            f"<div class='in'><span class='tag'>{_e(s.get('label') or typ)}</span>{body}</div></section>")


def render(r, slug: str) -> str:
    from . import build as B
    m = meta(r)
    pages = pages_of(r)
    ver = f"version {int(m.get('v') or 0)}"
    if m.get("status") == "making":                  # v0.999.35 a page made a moment ago, before the version is written
        mk = made_pages(r)
        if any(p["slug"] == slug for p in mk):
            pages, ver = mk, "being made"
    pg = next((p for p in pages if p["slug"] == slug), None)
    if pg is None:
        raise ProtoError("not found", 404)
    _, tk, _ = tokens_for(r)
    css = B.tokens_css(tk, "")                 # fonts at __proto/assets/fonts/ (beside the page)
    pub = [p for p in pages if p.get("for", "public") == "public"]
    inner = [p for p in pages if p.get("for", "public") != "public"]
    nav = "".join(f"<a href='{_e(p['slug'])}.html'{' class=on' if p['slug'] == slug else ''}>{_e(p['title'])}</a>" for p in pub)
    if inner:
        nav += "<span class='grp'>Signed in</span>" + "".join(
            f"<a href='{_e(p['slug'])}.html'{' class=on' if p['slug'] == slug else ''}>{_e(p['title'])}</a>" for p in inner)
    body = "".join(_section_html(s, i) for i, s in enumerate(pg.get("sections") or []))
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
            f"initial-scale=1'><meta name='robots' content='noindex'><title>{_e(pg['title'])} · prototype</title>"
            f"<style>{css}\n{PROTO_CSS}</style></head><body data-page='{_e(slug)}'>"
            f"<div class='pbar'><b>Prototype</b> · {ver} · not the real website yet</div>"
            f"<nav class='nav'><span class='brand'>{_e(r.name or 'Your website')}</span>{nav}</nav>"
            f"<main>{body}</main><footer class='foot'>{_e(r.name or '')} · prototype</footer>"
            "<script src='__proto.js'></script></body></html>")


def serve(r, rel: str) -> tuple[bytes, str]:
    """Files under __proto/ for the preview route."""
    from . import build as B
    rel = rel.lstrip("/")
    if rel == "__proto.js":
        return PROTO_JS.encode(), "application/javascript"
    if rel.startswith("assets/fonts/"):
        fn = rel[len("assets/fonts/"):]
        if not re.fullmatch(r"[a-z0-9-]+\.woff2", fn) or not (B.ASSETS / "fonts" / fn).exists():
            raise ProtoError("not found", 404)
        return (B.ASSETS / "fonts" / fn).read_bytes(), "font/woff2"
    m = re.fullmatch(r"([a-z0-9-]{1,40})\.html", rel or "home.html")
    if not m:
        raise ProtoError("not found", 404)
    return render(r, m.group(1)).encode(), "text/html; charset=utf-8"

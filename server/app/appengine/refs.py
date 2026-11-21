"""v0.999.71 D6 THE REFERENCE LIBRARY (docs/WEB_DESIGN_ENGINE_PLAN.md P3): Hoola's OWN references - never another
library's (owner decision 4) - feed the writer before it writes, so a new site starts where the best earlier ones ended.

Three kinds of reference:
  built   every section of a site the D5 critic reviewed: block, layout, background, place on the page, what the site
          is for, its kind, its field, the design direction, the critic's score, whether SHE KEPT it (put it live). No
          words, no photos, no names - only the design choice, so it can teach other people's sites too. A row from a
          scripted (free) critic teaches only its own account. Custom sections keep the path of their code, used as an
          example ONLY for the same account (their code carries her words).
  kit     the kit's own blocks (Hoola's code, the MIT patterns it was made from): the examples a custom section is shown
          when nothing better exists.
  link    a site SHE says she likes: one picture of its first screen (public addresses only) + its colours + her note. A
          PATTERN to aim for, never copied: no text, code or picture of it goes into her site; the critic sees the
          picture as "the feel she likes", the writer of custom sections reads her note and the colours.

What the writer gets:
  prior()     the starting layout + background of each section, from built rows that match (same block, then weighted
              by same purpose / direction / field / account; a kept site counts more) - only when enough rows agree
              (MIN_ROWS), their score is good (MIN_SCORE) and it beats the writer's own choice by a margin; never a
              layout the section cannot draw with her words (writer.alts_of decides).
  examples()  up to 5 examples for a custom section: her own best custom sections first, then kit blocks whose name
              matches the section.
  likes()     her links for the critic (pictures) and the writer (one line each).

Said plainly: references reflect what an earlier critic liked - a model's judgement; her keeps weigh more; her verdict
and the Arena stay the final test."""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.appengine")

MIN_ROWS = 3            # built rows that must agree before a reference changes the writer's choice (a judgement default)
MIN_SCORE = 7.0         # their weighted score must reach this
MARGIN = 0.3            # ... and beat the writer's own layout's rows by this much
MAX_LINKS = 8           # her "sites I like" per account
MAX_EXAMPLES = 5
EXAMPLE_CHARS = 2200
_lock = threading.Lock()
_ready_engine = None


class AppRef(Base):
    __tablename__ = "ae_refs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ref"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    source: Mapped[str] = mapped_column(String(12), index=True, default="built")   # built | link
    app: Mapped[str] = mapped_column(String(40), index=True, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[str] = mapped_column(String(80), default="")
    sec: Mapped[str] = mapped_column(String(100), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    block: Mapped[str] = mapped_column(String(40), index=True, default="")
    variant: Mapped[str] = mapped_column(String(40), default="")
    tone: Mapped[str] = mapped_column(String(16), default="")
    purpose: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(40), default="")
    field: Mapped[str] = mapped_column(String(80), default="")
    direction: Mapped[str] = mapped_column(String(40), default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    kept: Mapped[bool] = mapped_column(Boolean, default=False)
    critic: Mapped[str] = mapped_column(String(80), default="")
    code_rel: Mapped[str] = mapped_column(String(160), default="")
    url: Mapped[str] = mapped_column(String(400), default="")
    host: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    shot: Mapped[str] = mapped_column(String(300), default="")
    colours: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def ensure_table() -> None:
    """Registered in db.init_db AND self-heals (the v0.190.1 rule)."""
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    AppRef.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


SCRIPTED = "scripted"


# ---------------------------------------------------------------- learning from reviewed sites
def learn(tenant: str, app: str, version: int, rows: list[dict[str, Any]], *, score: float | None, critic: str,
          purpose: str = "", kind: str = "", field: str = "", direction: str = "") -> int:
    """One row per section a reviewed site shows. The site's earlier rows are replaced (its newest review counts)."""
    if score is None:
        return 0
    ensure_table()
    shown = [r for r in rows if r.get("block")]
    pos: dict[str, int] = {}
    out = []
    for r in shown:
        page = str(r.get("page") or "")
        k = pos.get(page, 0)
        pos[page] = k + 1
        out.append(AppRef(tenant_id=tenant, source="built", app=app, version=int(version or 0), page=page[:80],
                          sec=str(r.get("sec") or "")[:100], position=k, block=str(r["block"])[:40],
                          variant=str(r.get("variant") or "")[:40], tone=str(r.get("tone") or "")[:16],
                          purpose=(purpose or "")[:40], kind=(kind or "")[:40], field=(field or "")[:80],
                          direction=(direction or "")[:40], score=float(score), critic=(critic or "")[:80],
                          code_rel=(f"src/components/sections/{r['component']}.tsx" if r.get("block") == "custom"
                                    and r.get("component") else "")))
    with _lock, session() as s:
        kept = any(x.kept for x in s.scalars(select(AppRef).where(AppRef.app == app, AppRef.source == "built")))
        for x in s.scalars(select(AppRef).where(AppRef.app == app, AppRef.source == "built")):
            s.delete(x)
        for x in out:
            x.kept = kept
            s.add(x)
        s.commit()
    return len(out)


def keep(tenant: str, app: str) -> int:
    """She put this site live: its sections are references she KEPT (they count more)."""
    ensure_table()
    with _lock, session() as s:
        n = 0
        for x in s.scalars(select(AppRef).where(AppRef.app == app, AppRef.tenant_id == tenant, AppRef.source == "built")):
            x.kept = True
            n += 1
        s.commit()
    return n


def _built(block: str, tenant: str) -> list[AppRef]:
    ensure_table()
    with session() as s:
        rows = list(s.scalars(select(AppRef).where(AppRef.source == "built", AppRef.block == block,
                                                   AppRef.score.is_not(None))))
    # a scripted (free) critic's rows teach only its own account; everything else teaches everyone (no words kept)
    return [r for r in rows if r.critic != SCRIPTED or r.tenant_id == tenant]


def suggest(block: str, *, tenant: str = "", purpose: str = "", direction: str = "", field: str = "",
            position: int | None = None, current: tuple[str, str] = ("", ""),
            allowed_variants: list[str] | None = None, allowed_tones: list[str] | None = None) -> dict[str, Any] | None:
    """The layout + background the references favour for this section, or None (not enough agreement / no gain)."""
    rows = _built(block, tenant)
    if not rows:
        return None
    fw = _words(field)
    groups: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for r in rows:
        w = 1.0 + (2.0 if purpose and r.purpose == purpose else 0) + (1.5 if direction and r.direction == direction else 0) \
            + (1.0 if fw and fw & _words(r.field) else 0) + (0.5 if tenant and r.tenant_id == tenant else 0) \
            + (0.5 if position is not None and (r.position == 0) == (position == 0) else 0)
        val = float(r.score or 0) + (1.0 if r.kept else 0.0)
        groups.setdefault((r.variant, r.tone or ""), []).append((w, val))

    def mean(xs: list[tuple[float, float]]) -> float:
        tw = sum(w for w, _ in xs)
        return sum(w * v for w, v in xs) / tw if tw else 0.0
    ok_v = set(allowed_variants or []) | {current[0]}
    ok_t = set(allowed_tones or []) | {current[1] or "", ""}
    cands = [(mean(xs), len(xs), k) for k, xs in groups.items() if k[0] in ok_v and (k[1] in ok_t)]
    cands = [c for c in cands if c[1] >= MIN_ROWS and c[0] >= MIN_SCORE]
    if not cands:
        return None
    best = max(cands, key=lambda c: (c[0], c[1]))
    mine = [c for c in cands if c[2][0] == current[0] and (c[2][1] or "") == (current[1] or "")]
    if best[2] == (current[0], current[1] or ""):
        return None
    if mine and best[0] < mine[0][0] + MARGIN:
        return None
    return {"variant": best[2][0], "tone": best[2][1], "rows": best[1], "score": round(best[0], 2),
            "why": f"{best[1]} reviewed sites scored {best[0]:.1f} with this layout"}


def prior(tenant: str, pages: list[dict[str, Any]], ctx: Any, *, purpose: str = "", direction: str = "",
          field: str = "") -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """The writer's starting design choices from the references: ({"page:n": {variant, tone}}, reasons)."""
    from . import writer as W
    design: dict[str, dict[str, Any]] = {}
    used: list[dict[str, Any]] = []
    for pg in pages:
        k = 0
        for i, s in enumerate(pg.get("sections") or []):
            got = W.block_props({**s, "_page": pg["slug"]}, ctx, i)
            if not got or str(s.get("type") or "").startswith("custom_"):
                continue
            block, var, props = got
            tone = "primary" if block == "cta_band" else ("surface" if i % 2 == 1 and block not in ("hero", "whatsapp_float")
                                                         and not block.startswith("screen_") else "")
            sg = suggest(block, tenant=tenant, purpose=purpose, direction=direction, field=field, position=k,
                         current=(var, tone), allowed_variants=W.alts_of(block, var, props),
                         allowed_tones=W.tones_of(block))
            k += 1
            if not sg:
                continue
            d: dict[str, Any] = {}
            if sg["variant"] and sg["variant"] != var:
                d["variant"] = sg["variant"]
            if sg["tone"] and sg["tone"] != tone:
                d["tone"] = sg["tone"]
            if d:
                sec = f"{pg['slug']}:{i}"
                design[sec] = d
                used.append({"sec": sec, "block": block, **d, "why": sg["why"]})
    return design, used


# ---------------------------------------------------------------- examples for a custom section
def _kit_excerpt(block: str) -> str:
    from . import writer as W
    f = W.BLOCKS / (block.replace("_", "-") + ".tsx")
    if not f.is_file():
        return ""
    src = f.read_text("utf-8")
    src = re.sub(r"\nexport const sample[\s\S]*?\n};\n", "\n", src)        # her words go in, never the kit's sample
    return src[:EXAMPLE_CHARS]


def examples(tenant: str, sec: dict[str, Any], purpose: str = "") -> list[dict[str, str]]:
    """Up to 5 examples for one custom section: her own best custom sections (same account only), then kit blocks."""
    from . import service as AE
    from . import writer as W
    out: list[dict[str, str]] = []
    ensure_table()
    with session() as s:
        rows = list(s.scalars(select(AppRef).where(AppRef.source == "built", AppRef.tenant_id == tenant,
                                                   AppRef.block == "custom", AppRef.code_rel != "",
                                                   AppRef.score >= MIN_SCORE)))
    rows.sort(key=lambda r: (-(1 if r.kept else 0), -(r.score or 0), r.purpose != purpose))
    seen = set()
    for r in rows:
        if len(out) >= 3 or r.code_rel in seen:
            continue
        try:
            app = AE._load(tenant, r.app)
            f = AE.src_dir(app) / r.code_rel
            if f.is_file():
                out.append({"what": f"one of your own sections (scored {r.score:.1f})", "code": f.read_text("utf-8")[:EXAMPLE_CHARS]})
                seen.add(r.code_rel)
        except Exception:                            # noqa: BLE001 - the app was removed
            continue
    want = _words(" ".join(str(sec.get(k) or "") for k in ("type", "label", "design")))
    scored = sorted(((len(want & _words(b)), b) for b in W.MAPPERS if not b.startswith("screen_")), reverse=True)
    picks = [b for n, b in scored if n][:2] or ["features_split", "services_grid"]
    for b in picks:
        if len(out) >= MAX_EXAMPLES:
            break
        ex = _kit_excerpt(b)
        if ex:
            out.append({"what": f"the kit's {b} block (a pattern, its sample words left out)", "code": ex})
    return out


def examples_text(ex: list[dict[str, str]]) -> str:
    if not ex:
        return ""
    return "\n\nEXAMPLES OF HOOLA'S OWN SECTIONS (patterns to learn from - never copy their words):\n" + "\n".join(
        f"--- {e['what']} ---\n{e['code']}" for e in ex)


# ---------------------------------------------------------------- the sites she likes
def _dir(tenant: str) -> Path:
    from . import service as AE
    d = AE.root() / "refs" / re.sub(r"[^A-Za-z0-9_-]", "_", tenant or "_")
    d.mkdir(parents=True, exist_ok=True)
    return d


class RefError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _public(url: str) -> tuple[str, str]:
    from ..qa.runner import is_public
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or not host or p.username or p.password:
        raise RefError("That is not a web address.")
    if not is_public(host):
        raise RefError("Only public websites can be a reference (not a private or local address).")
    return u[:400], host


def capture(url: str) -> bytes:
    """One picture of the first screen of a public page on a computer. Every request is checked: a page that reaches
    for a private or local address gets nothing back."""
    from playwright.sync_api import sync_playwright
    from ..qa.runner import is_public
    from . import speed as SP
    with sync_playwright() as pw:
        b = SP._browser(pw)
        try:
            ctx = b.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")

            def guard(route):
                h = (urlparse(route.request.url).hostname or "").lower()
                if route.request.url.startswith("data:") or (h and is_public(h)):
                    route.continue_()
                else:
                    route.abort()
            ctx.route("**/*", guard)
            pg = ctx.new_page()
            pg.goto(url, wait_until="load", timeout=25000)
            try:
                pg.wait_for_load_state("networkidle", timeout=4000)
            except Exception:                        # noqa: BLE001
                pass
            return pg.screenshot(type="jpeg", quality=80)
        finally:
            b.close()


def add_link(tenant: str, url: str, note: str = "", shot: bytes | None = None) -> dict[str, Any]:
    """She says she likes a site: kept as a PATTERN (one first-screen picture, its colours, her note)."""
    from ..site import inspire as IN
    url, host = _public(url)
    ensure_table()
    with session() as s:
        have = list(s.scalars(select(AppRef).where(AppRef.tenant_id == tenant, AppRef.source == "link")))
    if any(x.url == url for x in have):
        raise RefError("That site is already in your list.", 409)
    if len(have) >= MAX_LINKS:
        raise RefError(f"Up to {MAX_LINKS} sites you like - remove one first.", 409)
    try:
        data = shot if shot is not None else capture(url)
    except Exception as e:                           # noqa: BLE001
        raise RefError(f"That site could not be opened ({type(e).__name__}).", 422) from None
    cols = [c for c in IN.image_colours(data, 8)][:6]
    row = AppRef(tenant_id=tenant, source="link", url=url, host=host[:200], note=" ".join((note or "").split())[:300],
                 colours=json.dumps(cols))
    f = _dir(tenant) / f"{row.id}.jpg"
    f.write_bytes(data)
    row.shot = str(f)
    with _lock, session() as s:
        s.add(row)
        s.commit()
        return _link_view(row)


def _link_view(r: AppRef) -> dict[str, Any]:
    try:
        cols = json.loads(r.colours or "[]")
    except ValueError:
        cols = []
    return {"id": r.id, "url": r.url, "host": r.host, "note": r.note, "colours": [c[0] for c in cols][:6],
            "at": r.created_at.isoformat() if r.created_at else ""}


def links(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = list(s.scalars(select(AppRef).where(AppRef.tenant_id == tenant, AppRef.source == "link")
                              .order_by(AppRef.created_at)))
    return [_link_view(r) for r in rows]


def remove_link(tenant: str, rid: str) -> dict[str, Any]:
    ensure_table()
    with _lock, session() as s:
        r = s.get(AppRef, rid)
        if not r or r.tenant_id != tenant or r.source != "link":
            raise RefError("Not found.", 404)
        try:
            Path(r.shot).unlink(missing_ok=True)
        except OSError:
            pass
        s.delete(r)
        s.commit()
    return {"ok": True}


def link_shot(tenant: str, rid: str) -> bytes:
    ensure_table()
    with session() as s:
        r = s.get(AppRef, rid)
        if not r or r.tenant_id != tenant or r.source != "link" or not Path(r.shot).is_file():
            raise RefError("Not found.", 404)
        return Path(r.shot).read_bytes()


def likes(tenant: str) -> dict[str, Any]:
    """Her links for the critic (pictures, at most 2) and for the writer (one line each)."""
    ensure_table()
    with session() as s:
        rows = list(s.scalars(select(AppRef).where(AppRef.tenant_id == tenant, AppRef.source == "link")
                              .order_by(AppRef.created_at.desc())))
    pics, lines = [], []
    for r in rows:
        v = _link_view(r)
        lines.append(f"- {r.host}" + (f": {r.note}" if r.note else "") + (f" (its colours: {', '.join(v['colours'][:4])})"
                                                                          if v["colours"] else ""))
        if len(pics) < 2 and Path(r.shot).is_file():
            pics.append((f"a site she likes ({r.host}) - aim for its feel, never copy it", Path(r.shot).read_bytes()))
    return {"pictures": pics, "text": ("SITES SHE LIKES (patterns only - never copy their words, pictures or code):\n"
                                       + "\n".join(lines)) if lines else ""}


def stats(tenant: str = "") -> dict[str, Any]:
    ensure_table()
    with session() as s:
        rows = list(s.scalars(select(AppRef)))
    built = [r for r in rows if r.source == "built"]
    return {"built": len(built), "sites": len({r.app for r in built}), "kept": len({r.app for r in built if r.kept}),
            "blocks": len({r.block for r in built}), "links": len([r for r in rows if r.source == "link"
                                                                  and (not tenant or r.tenant_id == tenant)])}

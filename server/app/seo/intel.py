"""v0.536 SEO INTEL (owner: "GO S1 + DATAFORSEO", after reading every-app/open-seo, MIT - ideas and the brand-matching
approach adapted, code our own; THIRD_PARTY_NOTICES.md). Four things the SEO desk could not see before:

  RANKS      the keywords SHE chooses to track (up to 100). Every day Google Search Console's own numbers for exactly those
             searches (average position, clicks, impressions, the page Google showed) - official, free, her own site. With
             DataForSEO joined, an exact Google position check (India, mobile, top 100) + who holds the top 3. A drop of 5+
             places is an alert on the desk.
  AI         is her business NAMED when people ask AI assistants about her market? Her questions (or ones Hoola suggests) are
             put to ChatGPT (OpenAI Responses + web search), Gemini (Gemini API + Google Search grounding) and Perplexity
             (Sonar) through their OWN APIs - the official route, not their consumer apps, so answers can differ from what a
             person sees in the app (said on the screen). Per answer: named or not, its order among the brands named, her site
             cited or not, the sites cited instead (where to get listed). Priced per answer, monthly ceiling.
  MAPS GRID  where her shop shows in Google Maps search from a grid of points around it (3x3 / 5x5 / 7x7). Google Places API
             (New) Text Search with a location bias per point, asking ONLY for place ids (Google's IDs-only Text Search, listed
             by Google as no-charge) - her rank at each point is the place of her id in the list (20+ = not in the first 20).
  DATAFORSEO competitors, ranked keywords, gaps, backlinks (seo/dfs.py) - her paid key, her ceiling.

Nothing here posts, changes or pays for anything on her site or Google profile. Field names follow each vendor's docs; NOT
VERIFIED against live accounts from here."""
from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.seo.intel")
_http: httpx.Client | None = None
MAX_TRACK = 100
MAX_PROMPTS = 25
ENGINES = ("openai", "gemini", "perplexity")
ENGINE_LABEL = {"openai": "ChatGPT (OpenAI API)", "gemini": "Gemini (Google Search grounding)", "perplexity": "Perplexity (Sonar)"}


class IntelError(Exception):
    pass


def set_http(c: httpx.Client | None) -> None:
    global _http
    _http = c


# ---------------------------------------------------------------- tables
class SeoIntel(Base):
    """Per site: her intel settings, her sealed DataForSEO login, the month's spend."""
    __tablename__ = "seo_intel"
    site_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    settings: Mapped[str] = mapped_column(Text, default="{}")      # ai_weekly, grid_keywords, grid_size, spacing_km, serp_weekly, place, caps
    dfs_login_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    dfs_pw_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    dfs_mask: Mapped[str] = mapped_column(String(80), default="")
    spend: Mapped[str] = mapped_column(Text, default="{}")          # {"2026-11": {"dfs_usd", "dfs_calls", "ai_inr", "ai_calls"}}


class SeoTrack(Base):
    __tablename__ = "seo_track"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("stk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    keyword: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoRank(Base):
    __tablename__ = "seo_rank"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("srk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    keyword: Mapped[str] = mapped_column(String(200), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    source: Mapped[str] = mapped_column(String(8), default="gsc")     # gsc (average position) | serp (DataForSEO exact)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text, default="")
    top: Mapped[str] = mapped_column(Text, default="[]")


class SeoAiPrompt(Base):
    __tablename__ = "seo_ai_prompt"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sap"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoAiAnswer(Base):
    __tablename__ = "seo_ai_answer"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("saa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    prompt_id: Mapped[str] = mapped_column(String(40), index=True)
    engine: Mapped[str] = mapped_column(String(12), default="")
    run: Mapped[str] = mapped_column(String(20), index=True)          # one run stamp for every answer of one run
    mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    cited: Mapped[bool] = mapped_column(Boolean, default=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # her order among the brands named (1 = first)
    brands: Mapped[str] = mapped_column(Text, default="[]")
    citations: Mapped[str] = mapped_column(Text, default="[]")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoGrid(Base):
    __tablename__ = "seo_grid"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sgr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    keyword: Mapped[str] = mapped_column(String(200), default="")
    size: Mapped[int] = mapped_column(Integer, default=5)
    spacing_km: Mapped[float] = mapped_column(Float, default=1.5)
    points: Mapped[str] = mapped_column(Text, default="[]")          # [{lat, lng, rank|null}]
    found: Mapped[int] = mapped_column(Integer, default=0)
    average: Mapped[float | None] = mapped_column(Float, nullable=True)
    top3: Mapped[int] = mapped_column(Integer, default=0)
    leaders: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()
TABLES = (SeoIntel, SeoTrack, SeoRank, SeoAiPrompt, SeoAiAnswer, SeoGrid)


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in TABLES:
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _site(tenant: str, site: str = "") -> dict[str, Any]:
    from . import service as S
    ensure_tables()
    with session() as s:
        try:
            r = S._site(s, tenant, site)
        except S.SeoError as e:
            raise IntelError(str(e))
        biz = _j(r.business, {})
        return {"id": r.id, "url": r.url, "name": r.name, "domain": _domain(r.url), "city": str(biz.get("city") or ""),
                "services": _j(r.services, []), "gsc_property": r.gsc_property}


def _domain(u: str) -> str:
    u = str(u or "").strip().lower()
    host = urlparse(u if "//" in u else "https://" + u).hostname or ""
    return host.removeprefix("www.")


def _intel(s, tenant: str, site_id: str) -> SeoIntel:
    r = s.get(SeoIntel, site_id)
    if r is None:
        r = SeoIntel(site_id=site_id, tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


DEFAULTS = {"ai_weekly": True, "grid_keywords": [], "grid_size": 5, "spacing_km": 1.5, "serp_weekly": False,
            "dfs_cap_usd": 0.0, "ai_cap_inr": 0.0, "place": {}, "brand_names": []}


def settings(tenant: str, site: str = "") -> dict[str, Any]:
    st = get_settings()
    sv = _site(tenant, site)
    with session() as s:
        cur = _j(_intel(s, tenant, sv["id"]).settings, {})
    out = {**DEFAULTS, **cur}
    out["dfs_cap_usd"] = float(out.get("dfs_cap_usd") or st.dataforseo_month_usd or 5)
    out["ai_cap_inr"] = float(out.get("ai_cap_inr") or st.seo_ai_month_inr or 300)
    return out


def save_settings(tenant: str, site: str = "", **kw: Any) -> dict[str, Any]:
    sv = _site(tenant, site)
    with session() as s:
        r = _intel(s, tenant, sv["id"])
        cur = _j(r.settings, {})
        for k in ("ai_weekly", "serp_weekly"):
            if k in kw and kw[k] is not None:
                cur[k] = bool(kw[k])
        if isinstance(kw.get("grid_keywords"), list):
            cur["grid_keywords"] = [str(x).strip()[:80] for x in kw["grid_keywords"] if str(x).strip()][:5]
        if isinstance(kw.get("brand_names"), list):
            cur["brand_names"] = [str(x).strip()[:60] for x in kw["brand_names"] if str(x).strip()][:6]
        if kw.get("grid_size") is not None:
            if int(kw["grid_size"]) not in (3, 5, 7):
                raise IntelError("Grid 3, 5 ya 7 points chauda.")
            cur["grid_size"] = int(kw["grid_size"])
        if kw.get("spacing_km") is not None:
            cur["spacing_km"] = max(0.3, min(float(kw["spacing_km"]), 10.0))
        if kw.get("dfs_cap_usd") is not None:
            cur["dfs_cap_usd"] = max(0.5, min(float(kw["dfs_cap_usd"]), 500.0))
        if kw.get("ai_cap_inr") is not None:
            cur["ai_cap_inr"] = max(10.0, min(float(kw["ai_cap_inr"]), 20000.0))
        r.settings = json.dumps(cur, ensure_ascii=False)
    return settings(tenant, site)


def _spend(tenant: str, site_id: str, key: str, amount: float, calls: int = 1) -> None:
    with session() as s:
        r = _intel(s, tenant, site_id)
        sp = _j(r.spend, {})
        m = sp.setdefault(datetime.utcnow().strftime("%Y-%m"), {})
        m[key] = round(float(m.get(key) or 0) + amount, 4)
        m[key.split("_")[0] + "_calls"] = int(m.get(key.split("_")[0] + "_calls") or 0) + calls
        r.spend = json.dumps(sp)


def _month_spend(tenant: str, site_id: str) -> dict[str, Any]:
    with session() as s:
        return _j(_intel(s, tenant, site_id).spend, {}).get(datetime.utcnow().strftime("%Y-%m"), {})


# ---------------------------------------------------------------- RANKS
def _norm_kw(k: str) -> str:
    return re.sub(r"\s+", " ", str(k or "").strip().lower())[:200]


def track(tenant: str, keywords: list[str], site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    with session() as s:
        have = {r.keyword for r in s.scalars(select(SeoTrack).where(SeoTrack.site_id == sv["id"])).all()}
        added = []
        for k in keywords:
            k = _norm_kw(k)
            if not k or k in have:
                continue
            if len(have) >= MAX_TRACK:
                raise IntelError(f"Ek website par {MAX_TRACK} keywords tak track hote hain.")
            s.add(SeoTrack(tenant_id=tenant, site_id=sv["id"], keyword=k))
            have.add(k)
            added.append(k)
    return {"added": added, "tracked": len(have), "say": f"{len(added)} keyword track hone lage ({len(have)} kul)."}


def untrack(tenant: str, keywords: list[str], site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    drop = {_norm_kw(k) for k in keywords}
    with session() as s:
        n = 0
        for r in s.scalars(select(SeoTrack).where(SeoTrack.site_id == sv["id"])).all():
            if r.keyword in drop:
                s.delete(r)
                n += 1
    return {"removed": n}


def tracked(tenant: str, site_id: str) -> list[str]:
    with session() as s:
        return [r.keyword for r in s.scalars(select(SeoTrack).where(SeoTrack.site_id == site_id).order_by(SeoTrack.created_at)).all()]


def _save_rank(tenant: str, site_id: str, kw: str, day: str, source: str, **v: Any) -> None:
    with session() as s:
        r = s.scalars(select(SeoRank).where(SeoRank.site_id == site_id, SeoRank.keyword == kw, SeoRank.day == day,
                                            SeoRank.source == source)).first()
        if r is None:
            r = SeoRank(tenant_id=tenant, site_id=site_id, keyword=kw, day=day, source=source)
            s.add(r)
        for k, x in v.items():
            setattr(r, k, x)


def pull_gsc(tenant: str, site: str = "", days: int = 7) -> dict[str, Any]:
    """Search Console's own numbers for her tracked searches, day by day (data ends ~3 days back)."""
    from . import service as S
    sv = _site(tenant, site)
    kws = tracked(tenant, sv["id"])
    if not kws:
        return {"rows": 0, "say": "Abhi koi keyword track nahi ho raha."}
    prop = sv["gsc_property"] or S._auto_property(tenant, sv["id"])
    if not prop:
        raise IntelError("Search Console mein yeh website nahi mili (pehle Google jodiye aur website verify kijiye).")
    end = S.today(tenant) - timedelta(days=3)
    start = end - timedelta(days=max(1, min(int(days), 90)) - 1)
    path = f"/sites/{quote(prop, safe='')}/searchAnalytics/query"
    want, rows = set(kws), 0
    for i in range(0, len(kws), 20):                       # RE2 regex, a few keywords per call
        rx = "^(" + "|".join(re.escape(k) for k in kws[i:i + 20]) + ")$"
        js = S._gsc(tenant, "POST", path, {"startDate": start.isoformat(), "endDate": end.isoformat(), "type": "web",
                                           "dimensions": ["date", "query", "page"], "rowLimit": 25000,
                                           "dimensionFilterGroups": [{"filters": [{"dimension": "query", "operator": "includingRegex",
                                                                                    "expression": rx}]}]})
        agg: dict[tuple[str, str], dict[str, Any]] = {}
        for x in js.get("rows") or []:
            d, q, page = (x.get("keys") or ["", "", ""])[:3]
            q = _norm_kw(q)
            if q not in want:
                continue
            a = agg.setdefault((q, d), {"clicks": 0, "impressions": 0, "_p": 0.0, "url": page, "_best": 0})
            imp = int(x.get("impressions") or 0)
            a["clicks"] += int(x.get("clicks") or 0)
            a["impressions"] += imp
            a["_p"] += float(x.get("position") or 0) * imp
            if imp > a["_best"]:
                a["url"], a["_best"] = page, imp
        for (q, d), a in agg.items():
            pos = round(a["_p"] / a["impressions"], 1) if a["impressions"] else None
            _save_rank(tenant, sv["id"], q, d, "gsc", position=pos, clicks=a["clicks"], impressions=a["impressions"], url=a["url"])
            rows += 1
    return {"rows": rows, "from": start.isoformat(), "to": end.isoformat()}


def check_serp(tenant: str, site: str = "", keywords: list[str] | None = None) -> dict[str, Any]:
    """Exact Google position (India, mobile, top 100) through DataForSEO, her key. Costs per keyword."""
    from . import dfs
    sv = _site(tenant, site)
    kws = [_norm_kw(k) for k in (keywords or tracked(tenant, sv["id"]))][:50]
    if not kws:
        raise IntelError("Pehle keywords track kijiye.")
    day, done, errs = date.today().isoformat(), [], []
    for k in kws:
        try:
            r = dfs.serp(tenant, sv["id"], k, sv["domain"])
        except dfs.DfsError as e:
            errs.append(str(e))
            break
        _save_rank(tenant, sv["id"], k, day, "serp", position=r["position"], url=r["url"], top=json.dumps(r["top"], ensure_ascii=False))
        done.append(r)
    out = {"checked": len(done), "results": done, "spend": dfs.status(tenant, sv["id"])}
    if errs:
        out["error"] = errs[0]
    return out


def ranks_view(tenant: str, site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    kws = tracked(tenant, sv["id"])
    with session() as s:
        rows = s.scalars(select(SeoRank).where(SeoRank.site_id == sv["id"]).order_by(SeoRank.day)).all()
        by: dict[str, dict[str, list]] = {}
        for r in rows:
            by.setdefault(r.keyword, {}).setdefault(r.source, []).append((r.day, r.position, r.clicks, r.impressions, r.url, r.top))
    out = []
    for k in kws:
        g = by.get(k, {}).get("gsc", [])
        sp = by.get(k, {}).get("serp", [])
        last = g[-1] if g else None
        week = [x for x in g if last and x[0] <= (date.fromisoformat(last[0]) - timedelta(days=7)).isoformat()]
        prev = week[-1] if week else None
        move = round(prev[1] - last[1], 1) if last and prev and last[1] is not None and prev[1] is not None else None
        out.append({"keyword": k, "position": last[1] if last else None, "day": last[0] if last else "",
                    "clicks_7d": sum(x[2] for x in g[-7:]), "impressions_7d": sum(x[3] for x in g[-7:]),
                    "url": last[4] if last else "", "move_7d": move,          # + = moved up
                    "history": [{"day": x[0], "position": x[1]} for x in g[-30:]],
                    "exact": ({"day": sp[-1][0], "position": sp[-1][1], "url": sp[-1][4], "top": _j(sp[-1][5], [])} if sp else None)})
    return {"site": sv, "keywords": out, "max": MAX_TRACK,
            "note": "Search Console position = Google's average over the day for your site (official). 'Exact' = one live Google "
                    "check through DataForSEO (India, mobile)."}


def rank_alerts(tenant: str, site: str = "") -> list[str]:
    v = ranks_view(tenant, site)
    return [f"'{k['keyword']}' slipped {abs(k['move_7d'])} places to {k['position']} in Google this week."
            for k in v["keywords"] if k["move_7d"] is not None and k["move_7d"] <= -5]


# ---------------------------------------------------------------- AI VISIBILITY
_URLISH = re.compile(r"(?:https?://|www\.)[^\s<>()]+|[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}", re.U)


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold()


def mention_at(text: str, names: list[str]) -> int | None:
    """Where the first whole-word mention of any of these names starts (URLs / e-mails are not mentions - their length is
    kept so positions stay true), or None. Idea from open-seo's aiMentionSpans (MIT), written fresh."""
    prose = _URLISH.sub(lambda m: " " * len(m.group(0)), text or "")
    folded = _fold(prose)
    best = None
    for n in {x.strip() for x in names if x and len(x.strip()) >= 2}:
        pat = r"(?<!\w)" + r"\s+".join(re.escape(p) for p in _fold(n).split()) + r"(?!\w)"
        m = re.search(pat, folded, re.U)
        if m and (best is None or m.start() < best):
            best = m.start()
    return best


def _brand_set(tenant: str, sv: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    """Her names (business name, domain, its stem, extra names she gave) + competitors' names from the desk."""
    from .desk import SeoDesk
    mine = [sv["name"], sv["domain"]]
    stem = sv["domain"].split(".")[0] if sv["domain"] else ""
    if len(stem) >= 4:
        mine.append(stem)
    mine += settings(tenant, sv["id"]).get("brand_names") or []
    comp: dict[str, list[str]] = {}
    with session() as s:
        d = s.get(SeoDesk, sv["id"])
        for c in _j(d.competitors, []) if d else []:
            c = str(c).strip()
            if not c:
                continue
            dom = _domain(c) if "." in c else ""
            label = dom or c
            names = [c] + ([dom, dom.split(".")[0]] if dom and len(dom.split(".")[0]) >= 4 else [])
            comp[label] = [n for n in names if n]
    return [n for n in mine if n], comp


def prompts(tenant: str, site: str = "") -> list[dict[str, Any]]:
    sv = _site(tenant, site)
    with session() as s:
        return [{"id": p.id, "prompt": p.prompt, "active": p.active} for p in
                s.scalars(select(SeoAiPrompt).where(SeoAiPrompt.site_id == sv["id"]).order_by(SeoAiPrompt.created_at)).all()]


def add_prompts(tenant: str, texts: list[str], site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    with session() as s:
        have = {p.prompt.lower() for p in s.scalars(select(SeoAiPrompt).where(SeoAiPrompt.site_id == sv["id"])).all()}
        n = 0
        for t in texts:
            t = re.sub(r"\s+", " ", str(t or "")).strip()[:300]
            if len(t) < 8 or t.lower() in have:
                continue
            if len(have) >= MAX_PROMPTS:
                raise IntelError(f"{MAX_PROMPTS} sawaal tak track hote hain.")
            s.add(SeoAiPrompt(tenant_id=tenant, site_id=sv["id"], prompt=t))
            have.add(t.lower())
            n += 1
    return {"added": n, "prompts": prompts(tenant, site)}


def set_prompt(tenant: str, pid: str, active: bool | None = None, remove: bool = False) -> dict[str, Any]:
    with session() as s:
        p = s.get(SeoAiPrompt, pid)
        if p is None or p.tenant_id != tenant:
            raise IntelError("Yeh sawaal nahi mila.")
        if remove:
            s.delete(p)
            return {"removed": True}
        if active is not None:
            p.active = bool(active)
        return {"id": p.id, "active": p.active}


def suggest_prompts(tenant: str, site: str = "") -> dict[str, Any]:
    """Questions real customers would ask an AI assistant about her market - never containing her own name (that would only
    test whether the AI knows her, not whether it recommends her)."""
    from ..net.ai import llm
    sv = _site(tenant, site)
    services = ", ".join(sv["services"][:6]) or sv["name"]
    raw = llm("You write the questions Indian customers type into ChatGPT / Gemini when choosing a local business or product. "
              "Return ONLY a JSON list of 10 strings.",
              f"Business type / what they sell: {services}. City: {sv['city'] or 'India'}. Write 10 questions a customer would ask "
              "an AI assistant before buying - best / which / cost / near me / compare / is it worth it; English or Hinglish as people "
              f"really type; never include the business name '{sv['name']}' or its website.", 900, timeout=60)
    m = re.search(r"\[.*\]", raw or "", re.S)
    try:
        items = [str(x).strip() for x in json.loads(m.group(0))] if m else []
    except ValueError:
        items = []
    names, _ = _brand_set(tenant, sv)
    items = [x for x in items if x and mention_at(x, names) is None][:10]
    return {"suggestions": items}


def engines_ready() -> dict[str, bool]:
    st = get_settings()
    return {"openai": bool(st.openai_api_key), "gemini": bool(st.gemini_api_key), "perplexity": bool(st.perplexity_api_key)}


def _client() -> tuple[httpx.Client, bool]:
    return (_http, False) if _http is not None else (httpx.Client(timeout=120), True)


def _req(method: str, url: str, **kw: Any) -> dict[str, Any]:
    c, own = _client()
    try:
        r = c.request(method, url, **kw)
    except httpx.HTTPError as e:
        raise IntelError(f"{urlparse(url).hostname} se baat nahi hui ({type(e).__name__}).")
    finally:
        if own:
            c.close()
    try:
        js = r.json()
    except ValueError:
        js = {}
    if r.status_code >= 400:
        err = js.get("error") if isinstance(js, dict) else None
        msg = (err.get("message") if isinstance(err, dict) else err) or r.text[:200]
        raise IntelError(f"{urlparse(url).hostname}: {str(msg)[:220]}")
    return js if isinstance(js, dict) else {}


def _cite(url: str = "", title: str = "") -> dict[str, str]:
    d = _domain(url) if url else ""
    if (not d or d.endswith("vertexaisearch.cloud.google.com")) and title and "." in title:
        d = _domain(title)                      # Gemini grounding links redirect; Google puts the site in the title
    return {"url": url, "title": title[:120], "domain": d}


def ask_openai(prompt: str) -> tuple[str, list[dict[str, str]]]:
    st = get_settings()
    js = _req("POST", "https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {st.openai_api_key}"},
              json={"model": st.seo_ai_openai_model, "input": prompt, "tools": [{"type": st.seo_ai_openai_search_tool}],
                    "max_output_tokens": 1800})
    text, cites = "", []
    for item in js.get("output") or []:
        if isinstance(item, dict) and item.get("type") == "message":
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text += str(part.get("text") or "")
                    for a in part.get("annotations") or []:
                        if isinstance(a, dict) and a.get("type") == "url_citation":
                            cites.append(_cite(str(a.get("url") or ""), str(a.get("title") or "")))
    return text, cites


def ask_gemini(prompt: str) -> tuple[str, list[dict[str, str]]]:
    st = get_settings()
    js = _req("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{st.seo_ai_gemini_model}:generateContent",
              headers={"x-goog-api-key": st.gemini_api_key},
              json={"contents": [{"role": "user", "parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]})
    cand = (js.get("candidates") or [{}])[0] or {}
    text = "".join(str(p.get("text") or "") for p in ((cand.get("content") or {}).get("parts") or []) if isinstance(p, dict))
    cites = [_cite(str((c.get("web") or {}).get("uri") or ""), str((c.get("web") or {}).get("title") or ""))
             for c in ((cand.get("groundingMetadata") or {}).get("groundingChunks") or []) if isinstance(c, dict)]
    return text, cites


def ask_perplexity(prompt: str) -> tuple[str, list[dict[str, str]]]:
    st = get_settings()
    js = _req("POST", "https://api.perplexity.ai/chat/completions", headers={"Authorization": f"Bearer {st.perplexity_api_key}"},
              json={"model": st.seo_ai_perplexity_model, "messages": [{"role": "user", "content": prompt}]})
    text = str((((js.get("choices") or [{}])[0] or {}).get("message") or {}).get("content") or "")
    res = js.get("search_results") or []
    cites = ([_cite(str(x.get("url") or ""), str(x.get("title") or "")) for x in res if isinstance(x, dict)] if res else
             [_cite(str(u)) for u in js.get("citations") or []])
    return text, cites


ASK = {"openai": ask_openai, "gemini": ask_gemini, "perplexity": ask_perplexity}


def score_answer(text: str, cites: list[dict[str, str]], mine: list[str], comp: dict[str, list[str]], my_domain: str) -> dict[str, Any]:
    at = mention_at(text, mine)
    named = [(mention_at(text, names), label) for label, names in comp.items()]
    named = sorted([(p, label) for p, label in named if p is not None])
    order = sorted(([(at, "__me__")] if at is not None else []) + named)
    rank = next((i + 1 for i, (_, lab) in enumerate(order) if lab == "__me__"), None)
    own = lambda d: bool(my_domain) and (d == my_domain or d.endswith("." + my_domain))  # noqa: E731
    seen, cl = set(), []
    for c in cites:
        if c["domain"] and c["domain"] not in seen:
            seen.add(c["domain"])
            cl.append({**c, "own": own(c["domain"])})
    return {"mentioned": at is not None, "rank": rank, "cited": any(c["own"] for c in cl),
            "brands": [lab for _, lab in named], "citations": cl[:15]}


def run_ai(tenant: str, site: str = "", engines: list[str] | None = None) -> dict[str, Any]:
    st = get_settings()
    sv = _site(tenant, site)
    ready = [e for e in (engines or ENGINES) if e in ENGINES and engines_ready().get(e)]
    if not ready:
        raise IntelError("Server par koi AI engine key nahi lagi (OPENAI_API_KEY / GEMINI_API_KEY / PERPLEXITY_API_KEY).")
    ps = [p for p in prompts(tenant, site) if p["active"]]
    if not ps:
        raise IntelError("Pehle kuch sawaal jodiye (ya 'Suggest questions' dabaiye).")
    per = float(st.seo_ai_call_inr or 2)
    cap = settings(tenant, sv["id"])["ai_cap_inr"]
    spent = float(_month_spend(tenant, sv["id"]).get("ai_inr") or 0)
    need = per * len(ps) * len(ready)
    if spent + need > cap:
        raise IntelError(f"Is run ka andaaza ₹{need:.0f} hai; is mahine ₹{spent:.0f} kharch ho chuke, seema ₹{cap:.0f}. "
                         "Kam sawaal / engine chuniye ya seema badhaiye.")
    mine, comp = _brand_set(tenant, sv)
    stamp = now().strftime("%Y%m%d%H%M%S")
    done = errors = 0
    for p in ps:
        for eng in ready:
            try:
                text, cites = ASK[eng](p["prompt"])
                sc = score_answer(text, cites, mine, comp, sv["domain"])
                row = SeoAiAnswer(tenant_id=tenant, site_id=sv["id"], prompt_id=p["id"], engine=eng, run=stamp,
                                  mentioned=sc["mentioned"], cited=sc["cited"], rank=sc["rank"],
                                  brands=json.dumps(sc["brands"], ensure_ascii=False),
                                  citations=json.dumps(sc["citations"], ensure_ascii=False), excerpt=text[:1500])
                done += 1
            except IntelError as e:
                row = SeoAiAnswer(tenant_id=tenant, site_id=sv["id"], prompt_id=p["id"], engine=eng, run=stamp, error=str(e)[:400])
                errors += 1
            with session() as s:
                s.add(row)
    _spend(tenant, sv["id"], "ai_inr", per * done, done)
    v = ai_view(tenant, site)
    return {**v, "answers": done, "errors": errors, "cost_inr": round(per * done, 2),
            "say": f"{done} AI jawab padhe: aapka naam {v['summary']['mentioned_pct']}% jawabon mein, site {v['summary']['cited_pct']}% mein cite hui."}


def ai_view(tenant: str, site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    ps = {p["id"]: p for p in prompts(tenant, site)}
    with session() as s:
        rows = s.scalars(select(SeoAiAnswer).where(SeoAiAnswer.site_id == sv["id"]).order_by(SeoAiAnswer.created_at)).all()
        rows = [{"run": r.run, "prompt_id": r.prompt_id, "engine": r.engine, "mentioned": r.mentioned, "cited": r.cited,
                 "rank": r.rank, "brands": _j(r.brands, []), "citations": _j(r.citations, []), "excerpt": r.excerpt, "error": r.error}
                for r in rows]
    runs = sorted({r["run"] for r in rows})
    last = [r for r in rows if runs and r["run"] == runs[-1] and not r["error"]]
    n = len(last) or 1
    comp_count: dict[str, int] = {}
    cite_count: dict[str, int] = {}
    for r in last:
        for b in r["brands"]:
            comp_count[b] = comp_count.get(b, 0) + 1
        for c in r["citations"]:
            if not c.get("own"):
                cite_count[c["domain"]] = cite_count.get(c["domain"], 0) + 1
    by_engine = {}
    for e in ENGINES:
        er = [r for r in last if r["engine"] == e]
        if er:
            by_engine[e] = {"label": ENGINE_LABEL[e], "answers": len(er), "mentioned_pct": round(100 * sum(r["mentioned"] for r in er) / len(er)),
                            "cited_pct": round(100 * sum(r["cited"] for r in er) / len(er))}
    trend = []
    for run in runs[-8:]:
        rr = [r for r in rows if r["run"] == run and not r["error"]]
        if rr:
            trend.append({"run": run, "mentioned_pct": round(100 * sum(r["mentioned"] for r in rr) / len(rr)),
                          "cited_pct": round(100 * sum(r["cited"] for r in rr) / len(rr))})
    per_prompt = []
    for pid, p in ps.items():
        pr = [r for r in last if r["prompt_id"] == pid]
        per_prompt.append({**p, "results": [{"engine": r["engine"], "mentioned": r["mentioned"], "cited": r["cited"], "rank": r["rank"],
                                             "brands": r["brands"][:6], "citations": [c["domain"] for c in r["citations"][:6]],
                                             "excerpt": r["excerpt"][:400]} for r in pr]})
    return {"site": sv, "engines": {e: {"label": ENGINE_LABEL[e], "ready": ok} for e, ok in engines_ready().items()},
            "last_run": runs[-1] if runs else "", "prompts": per_prompt, "by_engine": by_engine, "trend": trend,
            "summary": {"answers": len(last), "mentioned_pct": round(100 * sum(r["mentioned"] for r in last) / n) if last else 0,
                        "cited_pct": round(100 * sum(r["cited"] for r in last) / n) if last else 0},
            "competitors_named": sorted(comp_count.items(), key=lambda x: -x[1])[:10],
            "cited_instead": sorted(cite_count.items(), key=lambda x: -x[1])[:12],
            "note": "Asked through each company's own API with web search on - an answer in their consumer app can differ.",
            "price_per_answer_inr": float(get_settings().seo_ai_call_inr or 2)}


# ---------------------------------------------------------------- MAPS GRID (Places API (New), ids only per point)
PLACES = "https://places.googleapis.com/v1/places:searchText"


def _places(body: dict[str, Any], fields: str) -> list[dict[str, Any]]:
    st = get_settings()
    if not st.google_maps_api_key:
        raise IntelError("Server par Google Maps key nahi lagi (GOOGLE_MAPS_API_KEY, Places API (New) on).")
    js = _req("POST", PLACES, headers={"X-Goog-Api-Key": st.google_maps_api_key, "X-Goog-FieldMask": fields}, json=body)
    return [p for p in js.get("places") or [] if isinstance(p, dict)]


def find_place(tenant: str, site: str = "", query: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    q = query or f"{sv['name']} {sv['city']}".strip()
    rows = _places({"textQuery": q, "pageSize": 5, "regionCode": "IN"},
                   "places.id,places.displayName,places.formattedAddress,places.location")
    cands = [{"id": p.get("id"), "name": ((p.get("displayName") or {}).get("text")) or "", "address": p.get("formattedAddress") or "",
              "lat": (p.get("location") or {}).get("latitude"), "lng": (p.get("location") or {}).get("longitude")} for p in rows]
    return {"query": q, "candidates": [c for c in cands if c["id"] and c["lat"] is not None]}


def choose_place(tenant: str, place: dict[str, Any], site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    if not place.get("id") or place.get("lat") is None or place.get("lng") is None:
        raise IntelError("Google Maps par apni dukaan chuniye.")
    with session() as s:
        r = _intel(s, tenant, sv["id"])
        cur = _j(r.settings, {})
        cur["place"] = {k: place.get(k) for k in ("id", "name", "address", "lat", "lng")}
        r.settings = json.dumps(cur, ensure_ascii=False)
    return {"place": cur["place"]}


def grid_points(lat: float, lng: float, size: int, km: float) -> list[tuple[float, float]]:
    half = size // 2
    dlat = km / 111.32
    dlng = km / (111.32 * max(0.1, math.cos(math.radians(lat))))
    return [(round(lat + i * dlat, 6), round(lng + j * dlng, 6)) for i in range(half, -half - 1, -1) for j in range(-half, half + 1)]


def run_grid(tenant: str, keyword: str, site: str = "", size: int | None = None, km: float | None = None) -> dict[str, Any]:
    sv = _site(tenant, site)
    cfg = settings(tenant, sv["id"])
    place = cfg.get("place") or {}
    if not place.get("id"):
        raise IntelError("Pehle Google Maps par apni dukaan chuniye (Search intel > Maps grid).")
    size = int(size or cfg["grid_size"])
    if size not in (3, 5, 7):
        raise IntelError("Grid 3, 5 ya 7.")
    km = float(km or cfg["spacing_km"])
    kw = str(keyword or "").strip()[:80]
    if not kw:
        raise IntelError("Kis search ke liye? (jaise 'dentist near me', 'saree shop')")
    pts = []
    radius = max(500.0, min(km * 1000.0, 50000.0))
    for la, ln in grid_points(float(place["lat"]), float(place["lng"]), size, km):
        ids = [p.get("id") for p in _places({"textQuery": kw, "pageSize": 20, "regionCode": "IN",
                                             "locationBias": {"circle": {"center": {"latitude": la, "longitude": ln}, "radius": radius}}},
                                            "places.id")]
        rank = ids.index(place["id"]) + 1 if place["id"] in ids else None
        pts.append({"lat": la, "lng": ln, "rank": rank})
    lead = _places({"textQuery": kw, "pageSize": 5, "regionCode": "IN", "locationBias": {"circle": {
        "center": {"latitude": float(place["lat"]), "longitude": float(place["lng"])}, "radius": radius}}}, "places.id,places.displayName")
    leaders = [{"name": ((p.get("displayName") or {}).get("text")) or "", "you": p.get("id") == place["id"]} for p in lead]
    ranks = [p["rank"] for p in pts if p["rank"]]
    g = SeoGrid(tenant_id=tenant, site_id=sv["id"], keyword=kw, size=size, spacing_km=km, points=json.dumps(pts),
                found=len(ranks), average=round(sum(ranks) / len(ranks), 1) if ranks else None,
                top3=sum(1 for r in ranks if r <= 3), leaders=json.dumps(leaders, ensure_ascii=False))
    with session() as s:
        s.add(g)
        s.flush()
        out = _grid_view(g)
    out["say"] = (f"'{kw}': {out['top3']} / {len(pts)} jagah aap Maps ke top 3 mein, {len(pts) - out['found']} jagah top 20 mein bhi nahi."
                  + (f" Beech mein sabse upar: {leaders[0]['name']}." if leaders and not leaders[0]["you"] else ""))
    return out


def _grid_view(g: SeoGrid) -> dict[str, Any]:
    return {"id": g.id, "keyword": g.keyword, "size": g.size, "spacing_km": g.spacing_km, "points": _j(g.points, []),
            "found": g.found, "average": g.average, "top3": g.top3, "leaders": _j(g.leaders, []),
            "at": g.created_at.isoformat() if g.created_at else ""}


def grids_view(tenant: str, site: str = "") -> dict[str, Any]:
    sv = _site(tenant, site)
    with session() as s:
        rows = s.scalars(select(SeoGrid).where(SeoGrid.site_id == sv["id"]).order_by(SeoGrid.created_at.desc())).all()[:30]
        latest: dict[str, dict] = {}
        for g in rows:
            v = _grid_view(g)
            if g.keyword not in latest:
                latest[g.keyword] = {**v, "previous": None}
            elif latest[g.keyword]["previous"] is None:
                latest[g.keyword]["previous"] = {"top3": v["top3"], "average": v["average"], "at": v["at"]}
    cfg = settings(tenant, sv["id"])
    return {"place": cfg.get("place") or {}, "grids": list(latest.values()), "ready": bool(get_settings().google_maps_api_key),
            "note": "Each point asks Google Maps search for place ids only (Google's no-charge IDs-only Text Search); one named "
                    "search at the centre shows who leads."}


# ---------------------------------------------------------------- the desk's clock + one view
def daily(tenant: str, site_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if tracked(tenant, site_id):
        try:
            out["ranks"] = pull_gsc(tenant, site_id, 7)
            out["alerts"] = rank_alerts(tenant, site_id)
        except Exception as e:   # noqa: BLE001 - a Search Console hiccup never stops the desk
            out["ranks_error"] = str(e)[:200]
    return out


def weekly(tenant: str, site_id: str) -> dict[str, Any]:
    cfg = settings(tenant, site_id)
    out: dict[str, Any] = {}
    if cfg["ai_weekly"] and [p for p in prompts(tenant, site_id) if p["active"]] and any(engines_ready().values()):
        try:
            out["ai"] = run_ai(tenant, site_id)["summary"]
        except Exception as e:   # noqa: BLE001
            out["ai_error"] = str(e)[:200]
    for kw in cfg["grid_keywords"]:
        try:
            out.setdefault("grids", []).append(run_grid(tenant, kw, site_id)["say"])
        except Exception as e:   # noqa: BLE001
            out.setdefault("grid_errors", []).append(str(e)[:200])
            break
    if cfg["serp_weekly"]:
        try:
            out["serp"] = check_serp(tenant, site_id)["checked"]
        except Exception as e:   # noqa: BLE001
            out["serp_error"] = str(e)[:200]
    return out


def view(tenant: str, site: str = "") -> dict[str, Any]:
    from . import dfs
    sv = _site(tenant, site)
    cfg = settings(tenant, sv["id"])
    sp = _month_spend(tenant, sv["id"])
    return {"site": sv, "settings": {k: v for k, v in cfg.items() if k != "place"}, "ranks": ranks_view(tenant, site),
            "ai": ai_view(tenant, site), "maps": grids_view(tenant, site), "dataforseo": dfs.status(tenant, sv["id"]),
            "spend": {"ai_inr": round(float(sp.get("ai_inr") or 0), 2), "ai_cap_inr": cfg["ai_cap_inr"],
                      "dfs_usd": round(float(sp.get("dfs_usd") or 0), 4), "dfs_cap_usd": cfg["dfs_cap_usd"]}}


# ---------------------------------------------------------------- keyword research (official first)
def keyword_research(tenant: str, seeds: list[str], site: str = "") -> dict[str, Any]:
    """Monthly searches for her words: Google Ads Keyword Planner when her Google Ads is linked (official, free), else
    DataForSEO with her key (costs), else a plain line saying which one to join."""
    from ..ads import gads
    from . import dfs
    sv = _site(tenant, site)
    seeds = [str(x).strip() for x in seeds if str(x).strip()][:10] or [str(x) for x in sv["services"][:5]]
    if not seeds:
        raise IntelError("Kuch shabd dijiye jinke baare mein log Google par dhoondhte hain.")
    city = [sv["city"]] if sv["city"] else []
    try:
        r = gads.keyword_ideas(tenant, seeds, sv["url"] if sv["url"].startswith("https://") else "", city)
        return {"source": "Google Keyword Planner (your Google Ads)", **r}
    except gads.GAdsError as e:
        why = str(e)
    try:
        ideas = dfs.keyword_ideas(tenant, sv["id"], seeds)
        return {"source": "DataForSEO (your key, India)", "ideas": ideas, "spend": dfs.status(tenant, sv["id"])}
    except dfs.DfsError as e2:
        raise IntelError(f"Keyword ideas ke liye Google Ads jodiye (Social Desk > Google ads, free) ya DataForSEO. ({why[:120]} / {str(e2)[:120]})")

"""v0.376 PROOF (web design Phase 9, owner: "START PHASE 5"): "can Hoola build a world-class 100-page website?" as
NUMBERS, the same way for Hoola and for any other builder.

1. BIG_SET: five fixed 100-page Indian businesses (never changed without a bump) - a hospital, a coaching institute, a
   mithai brand, a real-estate developer and a fibre ISP - each with its real-looking lists (departments, doctors,
   courses, products with prices, projects, areas) in the facts, and the features a business that size needs (shop,
   blog, a second language, a web app).
2. A PROOF RUN builds one of them as the hidden arena tenant exactly like a real owner (site map of ~100 pages -> plan
   -> looks -> the first look -> build -> checks), then switches the features on through the same functions her taps
   use (shop from her priced lists, three blog posts, the second language, the web app), and stops at its rupee cap.
3. THE PROOF CARD, read from the finished files and records, never from the builder's own claims: pages planned vs
   pages built (every language), broken internal links and missing files over EVERY page, the independent Opus judge
   on a sample of page TYPES (home, a designed page, a list item, a blog post, the shop), the Chromium check scores,
   each feature verified in the output (cart script, /blog/ + feed + post JSON-LD, hreflang + /<lang>/ pages,
   sitemap.xml URLs, site search, breadcrumbs, /admin/), rupees and minutes in total and per page.
4. A RIVAL is measured the same way from its PUBLIC address (a Lovable / Bolt / Wix / ChatGPT site for the same brief):
   Hoola's own Chromium crawls up to 150 pages of that one host (robots.txt respected, public internet only, JS-built
   sites rendered so a React app is not under-counted), broken internal links, pages that show their words WITHOUT
   JavaScript (what most AI crawlers and link previews see), titles / descriptions / one h1 / JSON-LD / hreflang /
   sitemap, the same judge on the same number of pages. `compare` puts both cards side by side, the right way round."""
from __future__ import annotations

import json
import logging
import random
import re
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from .arena import TENANT, clean_scores

log = logging.getLogger("santosh.site")
SET_V = 1
CRAWL_MAX = 150
JUDGE_PAGES = 5
LOWER_BETTER = {"broken_links", "missing_files", "blocking", "inr", "inr_per_page", "minutes", "minutes_per_page", "kb_median",
                "lcp_ms"}


class ArenaProof(Base):
    __tablename__ = "site_arena_proofs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("proof"))
    kind: Mapped[str] = mapped_column(String(10), default="hoola")       # hoola | rival
    brief_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    builder: Mapped[str] = mapped_column(String(40), default="hoola")
    url: Mapped[str] = mapped_column(Text, default="")
    site_id: Mapped[str] = mapped_column(String(40), default="")
    version: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(12), default="running")   # running | done | stopped | failed
    stage: Mapped[str] = mapped_column(String(200), default="")
    card: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_OK = False
_RUNNING: dict[str, threading.Thread] = {}


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        ArenaProof.__table__.create(eng, checkfirst=True)
        _OK = True


# ---------------------------------------------------------------- 1. the five 100-page businesses
def _rnd(key: str) -> random.Random:
    return random.Random(f"proof-{SET_V}-{key}")


def _list(words: list[str], n: int, key: str) -> list[str]:
    r = _rnd(key)
    out = list(words)
    r.shuffle(out)
    return out[:n]


AREAS = ["Ram Nagar", "Shivaji Nagar", "Gandhi Chowk", "Station Road", "Civil Lines", "Gorakshan Road", "Jatharpeth",
         "Tapadia Nagar", "Kaulkhed", "Malkapur", "Dabki Road", "Umri", "Kirti Nagar", "Ranpise Nagar", "Khadan",
         "Sindhi Camp", "Old City", "Gaurakshan", "Murtizapur Road", "Akot Road", "Washim Bypass", "MIDC", "Shastri Nagar",
         "Adarsh Colony", "Ganesh Nagar", "Sudhir Colony", "Raut Wadi", "Jawahar Nagar", "Tilak Road", "Nehru Park",
         "Balaji Nagar", "Sai Nagar", "Laxmi Nagar", "Vidya Nagar", "Ganga Nagar", "Ashok Vatika", "Kapad Bazar",
         "Mahatma Phule Nagar", "Ambedkar Nagar", "Hingna Road"]


def big_set() -> list[dict[str, Any]]:
    sweets = ["Kaju Katli", "Motichoor Laddoo", "Besan Laddoo", "Rasgulla", "Gulab Jamun", "Soan Papdi", "Milk Cake",
              "Peda", "Barfi", "Kalakand", "Jalebi", "Imarti", "Mysore Pak", "Balushahi", "Ghevar", "Rasmalai",
              "Cham Cham", "Sandesh", "Malpua", "Chikki", "Til Laddoo", "Gajar Halwa", "Moong Dal Halwa", "Kesar Peda",
              "Anjeer Barfi", "Kaju Roll", "Pista Roll", "Coconut Barfi", "Dry Fruit Laddoo", "Mawa Kachori",
              "Shrikhand", "Basundi", "Rabri", "Kheer Kadam", "Chocolate Barfi", "Aloo Bhujia", "Sev", "Ratlami Sev",
              "Chakli", "Khakhra", "Mathri", "Namak Pare", "Shakarpara", "Banana Chips", "Moong Dal Namkeen",
              "Chana Jor", "Mixture", "Khatta Meetha", "Poha Chivda", "Corn Chivda", "Bhakarwadi", "Kachori",
              "Samosa (frozen)", "Papdi", "Farsan Mix", "Dal Moth", "Kaju Masala", "Badam Halwa", "Kesar Rasgulla",
              "Angoori Rabri"]
    r = _rnd("sweets")
    priced = [f"{x} ₹{r.choice([180, 240, 320, 400, 480, 560, 640, 720, 900, 1100])}/kg" for x in sweets]
    depts = ["Cardiology", "Orthopaedics", "Neurology", "Gynaecology", "Paediatrics", "General Surgery", "ENT",
             "Ophthalmology", "Dermatology", "Urology", "Nephrology", "Oncology", "Dental", "Physiotherapy", "Radiology",
             "Pathology Lab", "Emergency & Trauma", "ICU"]
    doctors = [f"Dr. {a} {b}" for a, b in zip(["Asha", "Ravi", "Meera", "Sunil", "Kavita", "Anil", "Pooja", "Nitin",
                                                  "Sneha", "Rahul", "Priya", "Amit", "Neha", "Vikas", "Swati", "Manoj",
                                                  "Deepa", "Sanjay", "Rekha", "Ajay", "Smita", "Prakash", "Vaishali", "Girish"],
                                                 ["Deshmukh", "Patil", "Kulkarni", "Joshi", "Wankhede", "Gawande", "Bhonde",
                                                  "Thakre", "Kale", "Raut", "Ingle", "Shinde", "Jadhav", "More", "Pawar",
                                                  "Bhagat", "Chavan", "Gaikwad", "Tayde", "Wagh", "Bansod", "Kadu",
                                                  "Mohod", "Dhote"])]
    courses = ["JEE Main 2-year", "JEE Advanced", "NEET 2-year", "NEET Repeater", "Foundation Class 8", "Foundation Class 9",
               "Foundation Class 10", "MHT-CET", "Olympiad Maths", "Olympiad Science", "Board Booster Class 12",
               "Board Booster Class 10", "Crash Course JEE", "Crash Course NEET", "Test Series JEE", "Test Series NEET"]
    projects = ["Shree Residency", "Sai Heights", "Green Valley Villas", "Lotus Towers", "Riverfront Homes", "Om Enclave",
                "Shanti Kunj", "Ganga Park", "Vrindavan Greens", "Sunrise Apartments", "Royal Plaza (shops)", "Laxmi Palms"]
    plans = ["Basic 40 Mbps ₹399/month", "Home 100 Mbps ₹599/month", "Family 150 Mbps ₹799/month", "Pro 300 Mbps ₹999/month",
             "Gamer 500 Mbps ₹1,499/month", "Giga 1 Gbps ₹2,499/month", "Office 200 Mbps ₹1,199/month", "Shop 60 Mbps ₹499/month"]
    base = [
        {"id": "big-hospital", "name": "Sanjeevani Multispeciality Hospital", "field": "hospital", "city": "Nagpur", "lang": "hi",
         "features": ["blog", "lang", "app"], "app": "patients book appointments online; staff see and update each request",
         "lists": {"departments": depts, "doctors": doctors[:24], "areas we serve": _list(AREAS, 20, "h-areas")},
         "posts": [("Heart attack ke shuruaati sanket", "Seene mein dard, saans phoolna aur paseena - turant 108 ya hamara emergency number."),
                   ("Monsoon mein bachchon ki sehat", "Ubla paani, machhardani aur haath dhona - teen aadatein jo bimari rokti hain."),
                   ("Knee replacement ke baad pehle 30 din", "Physiotherapy roz, chalne ka abhyas aur dawai samay par.")]},
        {"id": "big-coaching", "name": "Vidyapeeth Classes", "field": "coaching_centre", "city": "Kota", "lang": "hi",
         "features": ["blog", "lang", "app"], "app": "students log in to see their test marks and attendance; staff add marks",
         "lists": {"courses": courses, "centres": [f"{a} centre" for a in _list(AREAS, 10, "c-centres")],
                   "faculty": doctors[:16]},
         "posts": [("JEE ki taiyari ka 90 din ka plan", "Pehle 30 din concepts, agle 30 din questions, aakhri 30 din mock tests."),
                   ("NEET Biology mein 340+ kaise", "NCERT har line, diagrams roz, aur galtiyon ki notebook."),
                   ("Board aur JEE saath kaise", "Board ke liye likhne ka abhyas, JEE ke liye speed - dono ka samay alag rakhiye.")]},
        {"id": "big-mithai", "name": "Annapurna Mithai Bhandar", "field": "sweet_shop", "city": "Indore", "lang": "hi",
         "features": ["shop", "blog", "lang"], "app": "",
         "lists": {"products": priced, "branches": [f"{a} branch" for a in _list(AREAS, 8, "m-br")]},
         "posts": [("Diwali gift box kaise chunein", "Dry fruit wale dabbe lambe chalte hain; mawa wali mithai 2-3 din mein."),
                   ("Asli kesar ki pehchaan", "Paani mein dheere rang chhodta hai aur khushboo tez hoti hai."),
                   ("Namkeen ko kurkura kaise rakhein", "Hawa-band dabba, dhoop se door, aur geela chammach kabhi nahi.")]},
        {"id": "big-realestate", "name": "Shubh Griha Developers", "field": "real_estate", "city": "Pune", "lang": "mr",
         "features": ["blog", "lang", "app"], "app": "buyers send site-visit requests; staff confirm the visit time",
         "lists": {"projects": projects, "localities": _list(AREAS, 20, "r-loc"), "services": ["Home loan help",
                   "Site visits", "Interior packages", "Resale", "Rental management", "Legal checks"]},
         "posts": [("Pehla ghar lene se pehle 7 kagaz", "7/12 utara, RERA number, OC, CC, title search, loan sanction, sale deed."),
                   ("RERA kya hai aur kyon zaroori", "Har project ka RERA number website par dekhiye; possession date wahi pakki."),
                   ("Carpet vs built-up area", "Daam hamesha carpet area par poochiye - RERA yahi kehta hai.")]},
        {"id": "big-isp", "name": "Jaldi Fiber Net", "field": "isp", "city": "Akola", "lang": "mr",
         "features": ["blog", "lang", "app"], "app": "customers raise complaints and track them; staff update status",
         "lists": {"plans": plans, "service areas": _list(AREAS, 40, "i-areas")},
         "posts": [("WiFi slow ho to pehle yeh 5 kaam", "Router restart, cable check, 5 GHz band, router ki jagah, aur speed test."),
                   ("Fiber aur AirFiber mein farak", "Fiber cable se aata hai, zyada stable; AirFiber hawa se, jaldi lagta hai."),
                   ("Ghar ke WiFi ko surakshit rakhein", "Mazboot password, WPA3, aur router ka admin password badliye.")]},
    ]
    out = []
    for b in base:
        lists = "; ".join(f"{k}: " + ", ".join(v) for k, v in b["lists"].items())
        brief = (f"{b['name']}, {b['city']} - a complete 100 page website: every item of our lists gets its own page, "
                 f"with a blog" + (", an online shop" if "shop" in b["features"] else "") +
                 (f" and {b['app']}" if b.get("app") else "") + ".")
        out.append({**b, "brief": brief, "pages": 100,
                    "facts": {"name": b["name"], "city": b["city"], "phone": "9876543210", "address": f"Main Road, {b['city']}",
                              "lists": lists[:5500]}})
    return out


def brief(brief_id: str) -> dict[str, Any]:
    b = next((x for x in big_set() if x["id"] == brief_id), None)
    if b is None:
        raise ValueError("Yeh proof brief nahi hai.")
    return b


# ---------------------------------------------------------------- 2. the Hoola build (as a real owner would get it)
def _spent_inr() -> float:
    from .arena import _spent_inr as sp
    return sp()


def _wait(site_id: str, ok: tuple[str, ...], limit_s: int = 3 * 3600) -> str:
    from . import service as S
    t = time.time()
    while time.time() - t < limit_s:
        r = S._load(site_id)
        if r.status in ok and not S.busy(site_id):
            return r.status
        time.sleep(3)
    return S._load(site_id).status


def _stage(pid: str, text: str) -> None:
    with session() as s:
        p = s.get(ArenaProof, pid)
        if p is not None:
            p.stage = text[:200]


def _stopped(pid: str) -> bool:
    with session() as s:
        p = s.get(ArenaProof, pid)
        return p is None or p.status == "stopped"


def build_big(pid: str, b: dict[str, Any], budget: float) -> tuple[str, float, float, list[str]]:
    """Plan -> looks -> build -> features, like her taps. Returns (site id, rupees, minutes, notes)."""
    from . import service as S
    t0, inr0 = time.time(), _spent_inr()
    notes: list[str] = []

    def spent() -> float:
        return _spent_inr() - inr0
    _stage(pid, "Site map (about 100 pages)")
    v = S.new(TENANT, b["brief"], "", name=b["name"], field=b["field"], answers=b["facts"], pages=b["pages"])
    sid = v["id"]
    with session() as s:
        s.get(ArenaProof, pid).site_id = sid
    st = _wait(sid, ("planned", "looks", "ready", "failed", "stopped"))
    if st == "planned":
        _stage(pid, "Plan approved - three looks")
        S.approve_plan(TENANT, sid)
        st = _wait(sid, ("looks", "ready", "failed", "stopped"))
    if st == "looks":
        _stage(pid, "Building every page")
        S.choose_look(TENANT, sid, 0)
        st = _wait(sid, ("ready", "failed", "stopped"))
    if st != "ready":
        notes.append(f"build ended '{st}'")
        return sid, spent(), (time.time() - t0) / 60, notes
    feats = b.get("features") or []
    steps = [("shop", "Shop from the priced lists"), ("app", "Web app"), ("blog", "Three blog posts"), ("lang", "Second language")]
    for key, label in steps:
        if key not in feats:
            continue
        if _stopped(pid):
            notes.append("stopped by the owner")
            break
        if spent() >= budget:
            notes.append(f"budget reached before: {label}")
            break
        _stage(pid, label)
        try:
            if key == "shop":
                S.shop_setup(TENANT, sid, {"on": True, "cod": True, "pickup": True, "upi": "arena@okhdfcbank"}, None, True)
            elif key == "app":
                S.design_app(TENANT, sid, b["app"], "")
            elif key == "blog":
                for title, body in b["posts"]:
                    S.blog_publish(TENANT, sid, {"title": title, "body": body + "\n\n" + body, "meta": {"category": "Tips"}})
                    _wait(sid, ("ready", "failed"))
            elif key == "lang":
                S.set_languages(TENANT, sid, [b["lang"]])
            _wait(sid, ("ready", "failed", "stopped"))
        except Exception as e:
            log.exception("proof feature %s failed", key)
            notes.append(f"{label}: {str(e)[:160]}")
    return sid, spent(), (time.time() - t0) / 60, notes


# ---------------------------------------------------------------- 3. the proof card (from the files)
SRC = re.compile(r'\b(?:src|srcset)=["\']([^"\']+)["\']', re.I)


def missing_files(out: Path) -> list[dict[str, str]]:
    """Every local file a page loads (img / script / source / video) must exist."""
    bad = []
    for f in out.rglob("*.html"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for raw in set(SRC.findall(txt)):
            for part in raw.split(","):
                u = part.strip().split(" ")[0]
                if not u or re.match(r"^[a-z][a-z0-9+.-]*:", u, re.I) or u.startswith("//") or u.startswith("#"):
                    continue
                target = (f.parent / u.split("?")[0].split("#")[0]).resolve()
                if not target.exists():
                    bad.append({"page": f.relative_to(out).as_posix(), "file": u})
    return bad[:200]


def features(out: Path, langs: list[str]) -> dict[str, Any]:
    home = (out / "index.html").read_text(errors="ignore") if (out / "index.html").exists() else ""
    blog = out / "blog"
    posts = [p for p in blog.glob("*/index.html") if p.parent.name not in ("page", "category")] if blog.exists() else []
    post_txt = posts[0].read_text(errors="ignore") if posts else ""
    sm = (out / "sitemap.xml").read_text(errors="ignore") if (out / "sitemap.xml").exists() else ""
    pages = [p for p in out.rglob("index.html")]
    some = next((p.read_text(errors="ignore") for p in pages if p.parent != out and "hs-crumbs" in p.read_text(errors="ignore")), "")
    return {"shop": (out / "shop" / "index.html").exists() and (out / "assets" / "hoola-shop.js").exists(),
            "blog": bool(posts) and (blog / "feed.xml").exists() and '"BlogPosting"' in post_txt,
            "blog_posts": len(posts),
            "languages": [x for x in langs if (out / x / "index.html").exists()],
            "hreflang": 'rel="alternate" hreflang=' in home,
            "sitemap_urls": sm.count("<loc>"),
            "search": (out / "assets" / "search.json").exists(),
            "breadcrumbs": bool(some),
            "mega_menu": "hs-mega" in home or "hs-group" in home,
            "web_app": (out / "admin" / "index.html").exists() and (out / "assets" / "hoola-app.js").exists(),
            "rss": (blog / "feed.xml").exists()}


def _pages(out: Path) -> dict[str, int]:
    """Pages of the site (index.html files): the main language + each /<lang>/ copy."""
    every = [p for p in out.rglob("*.html") if p.name == "index.html"]
    langs: dict[str, int] = {}
    for p in every:
        parts = p.relative_to(out).parts
        first = parts[0] if len(parts) > 1 else ""
        key = first if first and len(first) <= 8 and (out / first / "assets").exists() else "main"
        langs[key] = langs.get(key, 0) + 1
    return {"total": len(every), **{f"lang_{k}": v for k, v in langs.items()}}


def _in_lang(out: Path, p: Path) -> bool:
    parts = p.relative_to(out).parts
    return len(parts) > 1 and len(parts[0]) <= 8 and (out / parts[0] / "assets").exists()


def file_stats(out: Path) -> dict[str, Any]:
    """The same page measures a rival gets, read from Hoola's files (main language)."""
    files = [p for p in out.rglob("index.html") if not _in_lang(out, p)]
    if not files:
        return {}
    n, ok, h1, ld, kb = len(files), 0, 0, 0, []
    for f in files:
        raw = f.read_text(errors="ignore")
        words = len(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)).split())
        ok += words >= 50
        h1 += len(re.findall(r"<h1[\s>]", raw, re.I)) == 1
        ld += "application/ld+json" in raw
        kb.append(round(len(raw.encode()) / 1024, 1))
    return {"readable_without_js_pct": round(100 * ok / n, 1), "one_h1_pct": round(100 * h1 / n, 1),
            "json_ld_pct": round(100 * ld / n, 1), "kb_median": round(statistics.median(kb), 1)}


def _kind(slug: str) -> str:
    if slug == "home":
        return "home"
    if slug.startswith("blog"):
        return "blog"
    if slug.startswith("shop"):
        return "shop"
    return "item" if "/" in slug else "page"


def _judge_pages(site_id: str, n: int = JUDGE_PAGES, judge_fn=None) -> dict[str, Any]:
    """The independent judge on a sample of page TYPES: home, then one blog / shop / list item page, then designed pages."""
    from . import build as B
    from . import service as S
    from .arena import judge
    r = S._load(site_id)
    chk = S._j(r.checks, {})
    pages = chk.get("pages") or {}
    base = B.site_dir(r.tenant_id, r.id) / "shots" / f"v{r.version}"
    pick: list[str] = []
    for want in ("home", "item", "blog", "shop", "page", "page", "page"):
        s = next((x for x in sorted(pages) if _kind(x) == want and x not in pick), None)
        if s:
            pick.append(s)
        if len(pick) >= n:
            break
    scores, per = [], {}
    for s in pick:
        shots = [(base / str(f)).read_bytes() for vw, f in ((pages.get(s) or {}).get("shots") or {}).items()
                 if vw in ("390", "1440") and (base / str(f)).exists()]
        if not shots:
            continue
        j = (judge_fn or judge)(shots)
        if j and isinstance(j.get("overall"), (int, float)):
            scores.append(float(j["overall"]))
            per[s] = j["overall"]
    return {"median": round(statistics.median(scores), 2) if scores else None, "pages": per}


def card(site_id: str, inr: float, minutes: float, notes: list[str], judge_fn=None) -> dict[str, Any]:
    from . import build as B
    from . import checks as C
    from . import service as S
    from . import sitemap as SM
    r = S._load(site_id)
    plan = S._j(r.plan, {})
    out = B.out_dir(r.tenant_id, r.id, r.version)
    chk = S._j(r.checks, {})
    sc = chk.get("scores") or {}
    planned = SM.counts(plan) if plan.get("big") else {"designed": len(plan.get("pages", [])), "items": 0}
    pages = _pages(out) if out.exists() else {"total": 0}
    built = pages.get("lang_main", pages["total"])
    broken = C.link_scan(out, 500) if out.exists() else []
    miss = missing_files(out) if out.exists() else []
    langs = S.extra_languages(r)
    j = _judge_pages(site_id, judge_fn=judge_fn)
    return {"site": site_id, "status": r.status, "version": r.version,
            "planned_pages": int(planned.get("designed", 0)) + int(planned.get("items", 0)) + int(planned.get("legal", 0) or 0),
            "built_pages": built, "all_pages": pages["total"], "pages": pages,
            "broken_links": len(broken), "broken": broken[:20], "missing_files": len(miss), "missing": miss[:20],
            "blocking": len(chk.get("blocking") or []), "performance": sc.get("performance"),
            "accessibility": sc.get("accessibility"), "seo": sc.get("seo"),
            "lcp_ms": ((chk.get("pages") or {}).get("home") or {}).get("lcp_ms"),
            "judge": j["median"], "judge_pages": j["pages"], "features": features(out, langs) if out.exists() else {},
            **(file_stats(out) if out.exists() else {}),
            "inr": round(inr, 2), "minutes": round(minutes, 1),
            "inr_per_page": round(inr / built, 2) if built else None,
            "minutes_per_page": round(minutes / built, 2) if built else None, "notes": notes}


# ---------------------------------------------------------------- the runs
def start(brief_id: str, budget_inr: float = 0.0, builder=None) -> dict[str, Any]:
    from ..main import APP_VERSION
    from ..config import get_settings
    ensure_tables()
    b = brief(brief_id)
    if any(t.is_alive() for t in _RUNNING.values()):
        raise ValueError("Ek proof pehle se chal raha hai.")
    cap = float(getattr(get_settings(), "site_arena_max_inr", 3000) or 3000)
    budget = min(float(budget_inr or cap), cap)
    with session() as s:
        p = ArenaProof(kind="hoola", brief_id=b["id"], builder="hoola", version=APP_VERSION, stage="starting",
                       card=json.dumps({"budget_inr": budget}))
        s.add(p)
        s.flush()
        pid = p.id
    th = threading.Thread(target=_go, args=(pid, b, budget, builder), name=f"proof-{pid}", daemon=True)
    _RUNNING[pid] = th
    th.start()
    return {"proof": pid, "budget_inr": budget, "say": f"100-page proof shuru: {b['name']} (v{APP_VERSION}), kharcha seema ₹{budget:,.0f}."}


def _go(pid: str, b: dict[str, Any], budget: float, builder=None) -> None:
    from ..usage import scope
    status = "done"
    try:
        with scope(TENANT, "site"):
            sid, inr, minutes, notes = (builder or build_big)(pid, b, budget)
            _stage(pid, "Measuring every page")
            c = card(sid, inr, minutes, notes)
        if _stopped(pid):
            status = "stopped"
    except Exception as e:
        log.exception("proof run failed")
        c, status = {"error": str(e)[:300]}, "failed"
    with session() as s:
        p = s.get(ArenaProof, pid)
        p.card, p.status, p.stage, p.finished_at = json.dumps(c, ensure_ascii=False), status, "", datetime.now(timezone.utc)
    _RUNNING.pop(pid, None)


def stop(pid: str) -> dict[str, Any]:
    with session() as s:
        p = s.get(ArenaProof, pid)
        if p is None:
            raise ValueError("Yeh proof nahi mila.")
        if p.status == "running":
            p.status = "stopped"
    return {"ok": True, "say": "Proof ruk jayega (chalta kadam poora hone ke baad)."}


def _view(p: ArenaProof) -> dict[str, Any]:
    th = _RUNNING.get(p.id)
    st = "interrupted" if p.status == "running" and not (th and th.is_alive()) else p.status
    b = next((x for x in big_set() if x["id"] == p.brief_id), {})
    return {"proof": p.id, "kind": p.kind, "brief": p.brief_id, "name": b.get("name", p.brief_id), "builder": p.builder,
            "url": p.url, "site": p.site_id, "version": p.version, "status": st, "stage": p.stage,
            "card": json.loads(p.card or "{}"), "at": p.created_at.isoformat() if p.created_at else ""}


def proofs(limit: int = 30) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [_view(p) for p in s.scalars(select(ArenaProof).order_by(ArenaProof.created_at.desc()).limit(limit)).all()]


def get(pid: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        p = s.get(ArenaProof, pid)
        if p is None:
            raise ValueError("Yeh proof nahi mila.")
        return _view(p)


# ---------------------------------------------------------------- 4. a rival, measured the same way
def _robots(url: str):
    from urllib.robotparser import RobotFileParser

    import httpx
    from .. import web as WB
    rp = RobotFileParser()
    try:
        u = urlparse(url)
        robots = WB._check_url(f"{u.scheme}://{u.netloc}/robots.txt")
        r = httpx.get(robots, timeout=10, follow_redirects=False, headers={"User-Agent": "HoolaArena/1.0"})
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except Exception:
        rp.parse([])
    return rp


def _norm(base: str, href: str, host: str) -> str | None:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return None
    u = urldefrag(urljoin(base, href))[0]
    p = urlparse(u)
    if p.scheme not in ("http", "https") or p.hostname != host:
        return None
    if re.search(r"\.(jpg|jpeg|png|webp|avif|gif|svg|pdf|zip|mp4|mp3|css|js|xml|txt|ico)$", p.path, re.I):
        return None
    return p._replace(query="").geturl()


def crawl(url: str, limit: int = CRAWL_MAX, render=None, raw_get=None) -> dict[str, Any]:
    """One public host, breadth first, rendered in Chromium (links a script adds count), robots.txt respected."""
    import httpx
    from .. import web as WB
    start_url = WB._check_url(url)
    host = urlparse(start_url).hostname
    rp = _robots(start_url)
    seen, queue, pages, broken = {start_url}, [start_url], [], []
    raw_get = raw_get or (lambda u: httpx.get(WB._check_url(u), timeout=15, follow_redirects=True,
                                              headers={"User-Agent": "HoolaArena/1.0"}))
    render = render or _render
    while queue and len(pages) < limit:
        u = queue.pop(0)
        if not rp.can_fetch("HoolaArena", u):
            continue
        try:
            raw = raw_get(u)
            code, raw_html = raw.status_code, raw.text if "html" in raw.headers.get("content-type", "html") else ""
        except Exception:
            code, raw_html = 0, ""
        if code >= 400 or code == 0:
            broken.append({"url": u, "status": code})
            continue
        try:
            info = render(u)
        except Exception as e:
            log.info("render failed %s: %s", u, e)
            info = {"links": [], "title": "", "desc": "", "h1": 0, "text": 0, "ld": [], "hreflang": 0, "kb": len(raw_html) // 1024}
        no_js_words = len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw_html))).split())
        pages.append({"url": u, "title": info.get("title", ""), "desc": bool(info.get("desc")), "h1": info.get("h1", 0),
                      "words": info.get("text", 0), "no_js_words": no_js_words, "ld": info.get("ld", []),
                      "hreflang": info.get("hreflang", 0), "kb": info.get("kb", 0)})
        for h in info.get("links", []):
            n = _norm(u, h, host)
            if n and n not in seen:
                seen.add(n)
                queue.append(n)
    try:
        sm = raw_get(f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}/sitemap.xml")
        sitemap_urls = sm.text.count("<loc>") if sm.status_code == 200 else 0
    except Exception:
        sitemap_urls = 0
    return {"start": start_url, "pages": pages, "broken": broken, "queued_left": len(queue), "sitemap_urls": sitemap_urls}


def _render(url: str) -> dict[str, Any]:
    """Chromium, public internet only (every request checked), the page's links and head after its scripts ran."""
    from playwright.sync_api import sync_playwright
    from .. import web as WB
    from .checks import _launch

    def route(r):
        try:
            WB._check_url(r.request.url) if r.request.url.startswith("http") else None
            r.continue_()
        except Exception:
            r.abort()
    with sync_playwright() as p:
        b = _launch(p)
        try:
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.route("**/*", route)
            resp = page.goto(url, wait_until="networkidle", timeout=30000)
            info = page.evaluate("""() => ({
                links: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).slice(0, 400),
                title: document.title || '', desc: (document.querySelector('meta[name=description]') || {}).content || '',
                h1: document.querySelectorAll('h1').length, text: (document.body.innerText || '').split(/\\s+/).length,
                ld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => { try { const j = JSON.parse(s.textContent); return j['@type'] || ''; } catch (e) { return ''; } }),
                hreflang: document.querySelectorAll('link[rel=alternate][hreflang]').length })""")
            body = resp.body() if resp else b""
            info["kb"] = round(len(body) / 1024, 1)
            ctx.close()
            return info
        finally:
            b.close()


def rival_card(crawled: dict[str, Any], judge_shots: list[list[bytes]], judge_fn=None) -> dict[str, Any]:
    from .arena import judge
    pages = crawled["pages"]
    n = len(pages)
    scores = []
    for shots in judge_shots[:JUDGE_PAGES]:
        if not shots:
            continue
        j = (judge_fn or judge)(shots)
        if j and isinstance(j.get("overall"), (int, float)):
            scores.append(float(j["overall"]))

    def pct(f) -> float | None:
        return round(100 * sum(1 for p in pages if f(p)) / n, 1) if n else None
    titles = [p["title"] for p in pages if p["title"]]
    return {"built_pages": n, "all_pages": n, "broken_links": len(crawled["broken"]), "broken": crawled["broken"][:20],
            "judge": round(statistics.median(scores), 2) if scores else None,
            "readable_without_js_pct": pct(lambda p: p["no_js_words"] >= 50),
            "unique_titles_pct": round(100 * len(set(titles)) / n, 1) if n else None,
            "description_pct": pct(lambda p: p["desc"]), "one_h1_pct": pct(lambda p: p["h1"] == 1),
            "json_ld_pct": pct(lambda p: bool(p["ld"])), "hreflang": any(p["hreflang"] for p in pages),
            "sitemap_urls": crawled["sitemap_urls"], "kb_median": round(statistics.median([p["kb"] for p in pages]), 1) if n else None,
            "crawl_capped": crawled["queued_left"] > 0}


def rival(brief_id: str, builder: str, url: str, crawl_fn=None, shots_fn=None, judge_fn=None,
          background: bool = True) -> dict[str, Any]:
    """Measure a rival builder's PUBLIC site for the same brief (owner-only API)."""
    from ..main import APP_VERSION
    ensure_tables()
    brief(brief_id)
    from .. import web as WB
    try:
        url = WB._check_url(url)
    except Exception as e:
        raise ValueError(f"Yeh address khul nahi sakta: {e}")
    with session() as s:
        p = ArenaProof(kind="rival", brief_id=brief_id, builder=(builder or "other")[:40].lower(), url=url[:500],
                       version=APP_VERSION, stage="Crawling")
        s.add(p)
        s.flush()
        pid = p.id

    def go():
        try:
            c = (crawl_fn or crawl)(url)
            from . import checks as C
            urls = [x["url"] for x in c["pages"]][:JUDGE_PAGES]
            shots = [(shots_fn or C.url_shots)(u) for u in urls]
            card_ = rival_card(c, shots, judge_fn)
            st = "done"
        except Exception as e:
            log.exception("rival crawl failed")
            card_, st = {"error": str(e)[:300]}, "failed"
        with session() as s:
            q = s.get(ArenaProof, pid)
            q.card, q.status, q.stage, q.finished_at = json.dumps(card_, ensure_ascii=False), st, "", datetime.now(timezone.utc)
        _RUNNING.pop(pid, None)
    if background:
        th = threading.Thread(target=go, name=f"proof-{pid}", daemon=True)
        _RUNNING[pid] = th
        th.start()
    else:
        go()
    return {"proof": pid, "say": f"{builder or 'Doosri'} website naap raha hoon (150 page tak)."}


# ---------------------------------------------------------------- 5. side by side
COMPARE_KEYS = ("built_pages", "broken_links", "judge", "performance", "accessibility", "seo", "inr_per_page",
                "minutes_per_page", "sitemap_urls", "readable_without_js_pct", "one_h1_pct", "json_ld_pct", "kb_median")


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Two proof cards (usually Hoola vs a rival for the same brief): per metric who is better, the right way round."""
    rows, wins = {}, {"a": 0, "b": 0}
    for k in COMPARE_KEYS:
        x, y = a.get(k), b.get(k)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or isinstance(x, bool) or isinstance(y, bool):
            rows[k] = {"a": x, "b": y, "better": ""}
            continue
        if abs(x - y) < 1e-9:
            better = "same"
        else:
            better = ("a" if x < y else "b") if k in LOWER_BETTER else ("a" if x > y else "b")
            wins[better] += 1
        rows[k] = {"a": x, "b": y, "better": better}
    return {"metrics": rows, "wins": wins}

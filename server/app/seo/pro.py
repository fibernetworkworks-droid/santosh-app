"""v0.319 SEO PRO: the extra checks a senior SEO team runs, added to the hired SEO Employee (seo/desk.py) and the plain
SEO Sahayak crawl (seo/service.py). Pure functions over the crawled page dicts; the network calls that feed them (headers,
image sizes, URL Inspection, Sitemaps API, CrUX History, IndexNow) live in service.py / desk.py.

Ideas and thresholds were studied in the open-source claude-seo project (MIT, (c) AgriciDaniel; see THIRD_PARTY_NOTICES.md)
and re-written here in Hoola's own code and words. Things in that project Hoola does NOT do, on purpose: scraping Google
results (site: lookups, SERP competitor scoring, content briefs from results), paid third-party data, pretending to be
Googlebot or any other crawler, "humanising" text to hide AI, and the Indexing API for ordinary pages (Google allows it
only for job posts and live streams).

    health()        the 100-point health score in 7 parts (technical 22, content 23, on-page 20, schema 10, performance 10,
                    AI readiness 10, images 5) and a priority for every issue (critical / high / medium / low)
    drift()         17 rules comparing a page with its last crawl (title / H1 / canonical / noindex / schema / status ...)
    ai_bots()       which AI crawlers robots.txt lets in: SEARCH bots (they decide if ChatGPT / Claude / Perplexity can cite
                    her) are told apart from TRAINING bots (blocking those is her choice and costs nothing in search)
    page_checks()   schema validation (JSON, required fields, retired types), page-type word floors, content visible
                    without JavaScript, readability, keyword stuffing, filler phrases, numbers without a source, author /
                    date on articles, image weight / size / lazy loading, hreflang codes
    site_checks()   near-duplicate pages, one templated title on many pages, scaled pages, hreflang return links, NAP
                    (phone / pin) consistency, old business.site links, pages that look hacked or rented out (parasite),
                    E-E-A-T signals, security headers, redirect hops, llms.txt
    eeat() / local_score()  the two scorecards on the desk
    UPDATES         Google's confirmed core / spam / policy / structured-data changes, to explain a drop
"""
from __future__ import annotations

import hashlib
import json
import re
import zlib
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

# ---------------------------------------------------------------- the health score
WEIGHTS = {"technical": 22, "content": 23, "onpage": 20, "schema": 10, "performance": 10, "ai": 10, "images": 5}
LABELS = {"technical": "Technical", "content": "Content", "onpage": "On-page", "schema": "Schema",
          "performance": "Speed", "ai": "AI search", "images": "Images"}
CATEGORY = {
    # technical
    "broken": "technical", "unreachable": "technical", "noindex": "technical", "viewport": "technical", "http": "technical",
    "canonical": "technical", "robots_block": "technical", "sitemap": "technical", "broken_link": "technical",
    "redirect_link": "technical", "orphan": "technical", "deep": "technical", "mixed": "technical", "sec_headers": "technical",
    "redirect_hops": "technical", "hreflang": "technical", "hreflang_return": "technical", "parasite": "technical",
    "gsc_not_indexed": "technical", "gsc_sitemap": "technical", "heavy": "technical", "lang": "technical",
    # content
    "thin": "content", "word_floor": "content", "near_dup": "content", "scaled": "content", "readability": "content",
    "stuffing": "content", "filler": "content", "claims": "content", "byline": "content", "eeat": "content",
    # on-page
    "title_missing": "onpage", "title_short": "onpage", "title_long": "onpage", "desc_missing": "onpage", "desc_len": "onpage",
    "h1_missing": "onpage", "h1_many": "onpage", "dup_title": "onpage", "dup_desc": "onpage", "meta_template": "onpage",
    "city": "onpage", "nap": "onpage", "gbp_link": "onpage",
    # schema
    "schema": "schema", "schema_invalid": "schema", "schema_missing_field": "schema", "schema_retired": "schema",
    "schema_faq": "schema",
    # AI search
    "ai_search_blocked": "ai", "ai_training_blocked": "ai", "js_only": "ai", "llms_txt": "ai", "google_blocked": "ai",
    # images
    "img_alt": "images", "img_heavy": "images", "img_size": "images", "img_lazy": "images", "img_format": "images",
}
CRITICAL = {"robots_block", "google_blocked", "unreachable"}
_PEN = {"bad": 25, "warn": 10, "info": 3}


def category(code: str) -> str:
    return CATEGORY.get(code, "technical")


def priority(issue: dict[str, Any], home: str = "") -> str:
    """critical: the whole site or the home page is out of Google; high: other urgent; medium: warn; low: info."""
    lvl, code = issue.get("level"), issue.get("code", "")
    is_home = bool(home) and (issue.get("url") or "").rstrip("/") == home.rstrip("/")
    if code in CRITICAL or (lvl == "bad" and is_home and code in ("noindex", "broken", "http")):
        return "critical"
    return {"bad": "high", "warn": "medium"}.get(lvl, "low")


def _perf_score(cwv: dict[str, Any] | None) -> int | None:
    """Speed part from Core Web Vitals (real visitors first, else the lab score)."""
    if not cwv:
        return None
    g = cwv.get("grades") or {}
    if cwv.get("field_data") and g:
        return max(0, 100 - sum({"poor": 35, "ni": 15}.get(v, 0) for v in g.values()))
    lab = cwv.get("lab_score")
    return int(lab) if isinstance(lab, (int, float)) else None


def health(issues: list[dict[str, Any]], n_pages: int, cwv: dict[str, Any] | None = None, home: str = "") -> dict[str, Any]:
    """Each part starts at 100; a problem costs bad 25 / warn 10 / info 3, scaled by how much of the site it touches (a
    one-page problem on a 200-page site costs 40% of that, a site-wide one all of it)."""
    n = max(1, n_pages)
    by: dict[tuple[str, str], set[str]] = {}
    lvl: dict[tuple[str, str], str] = {}
    for i in issues:
        k = (category(i.get("code", "")), i.get("code", ""))
        by.setdefault(k, set()).add(i.get("url") or "")
        if _PEN.get(i.get("level"), 0) > _PEN.get(lvl.get(k), -1):
            lvl[k] = i.get("level", "info")
    parts = {c: 100.0 for c in WEIGHTS}
    for (cat, code), urls in by.items():
        share = 1.0 if code in CRITICAL or code.startswith(("robots", "sitemap", "sec_", "redirect_hops", "llms", "ai_", "google_")) \
            else min(1.0, len(urls) / n)
        parts[cat] -= _PEN.get(lvl[(cat, code)], 0) * (0.4 + 0.6 * share)
    perf = _perf_score(cwv)
    if perf is not None:
        parts["performance"] = min(parts["performance"], perf)
    parts = {c: max(0, round(v)) for c, v in parts.items()}
    total = round(sum(WEIGHTS[c] * parts[c] / 100 for c in WEIGHTS))
    if any(i.get("code") in CRITICAL for i in issues):
        total = min(total, 40)                     # nothing else matters while Google cannot get in
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for i in issues:
        counts[priority(i, home)] += 1
    return {"total": total, "parts": [{"key": c, "label": LABELS[c], "weight": WEIGHTS[c], "score": parts[c]} for c in WEIGHTS],
            "counts": counts, "speed_measured": perf is not None}


# ---------------------------------------------------------------- drift: what changed on a page since the last crawl
DRIFT_RULES = ("status_error", "title_removed", "title_changed", "desc_changed", "h1_removed", "h1_changed", "canonical_changed",
               "canonical_removed", "noindex_added", "schema_removed", "schema_changed", "schema_added", "og_removed",
               "h2_changed", "content_changed", "words_dropped", "hreflang_removed")


def drift(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """Old vs new crawl of one page -> [{rule, level bad|warn|info, text}]. Only real changes; a page that was already
    broken / had no title last time is not reported again."""
    out: list[dict[str, Any]] = []

    def add(rule, level, text):
        out.append({"rule": rule, "level": level, "url": new.get("url") or old.get("url", ""), "text": text})
    if not old or not new:
        return out
    os_, ns = int(old.get("status") or 200), int(new.get("status") or 200)
    if os_ < 400 <= ns:
        add("status_error", "bad", f"Page ab khul nahi raha (HTTP {ns}); pichhli baar theek tha.")
        return out
    if ns >= 400:
        return out
    ot, nt = (old.get("title") or "").strip(), (new.get("title") or "").strip()
    if ot and not nt:
        add("title_removed", "bad", f"Title hat gaya (pehle: '{ot[:70]}').")
    elif ot and nt and ot != nt:
        add("title_changed", "warn", f"Title badla: '{ot[:60]}' -> '{nt[:60]}'.")
    od, nd = (old.get("description") or "").strip(), (new.get("description") or "").strip()
    if od and od != nd:
        add("desc_changed", "warn", "Meta description badli." if nd else "Meta description hat gayi.")
    oh, nh = " ".join(old.get("h1") or []).strip(), " ".join(new.get("h1") or []).strip()
    if oh and not nh:
        add("h1_removed", "bad", f"H1 heading hat gayi (pehle: '{oh[:70]}').")
    elif oh and nh and SequenceMatcher(None, oh.lower(), nh.lower()).ratio() < 0.6:
        add("h1_changed", "warn", f"H1 badli: '{oh[:50]}' -> '{nh[:50]}'.")
    oc, nc = old.get("canonical") or "", new.get("canonical") or ""
    if oc and not nc:
        add("canonical_removed", "warn", "Canonical tag hat gaya.")
    elif oc and nc and oc.rstrip("/") != nc.rstrip("/"):
        add("canonical_changed", "bad", f"Canonical ab doosre URL ki taraf: {nc}")
    if new.get("noindex") and not old.get("noindex"):
        add("noindex_added", "bad", "Page par noindex lag gaya: Google ise hata dega.")
    ot_, nt_ = set(old.get("schema_types") or []), set(new.get("schema_types") or [])
    if ot_ and not nt_:
        add("schema_removed", "bad", f"Schema (JSON-LD) hat gaya: {', '.join(sorted(ot_))[:80]}.")
    elif ot_ and old.get("schema_hash") and new.get("schema_hash") and old["schema_hash"] != new["schema_hash"]:
        add("schema_changed", "warn", "Schema (JSON-LD) badla" + (f": {', '.join(sorted(ot_ ^ nt_))[:80]}" if ot_ ^ nt_ else "") + ".")
    elif not ot_ and nt_:
        add("schema_added", "info", f"Naya schema laga: {', '.join(sorted(nt_))[:80]}.")
    oo, no = set((old.get("og") or {}).keys()), set((new.get("og") or {}).keys())
    if oo - no:
        add("og_removed", "warn", f"Social share tags hat gaye: {', '.join(sorted(oo - no))}.")
    if (old.get("h2") or []) and (old.get("h2") or [])[:8] != (new.get("h2") or [])[:8]:
        add("h2_changed", "info", "H2 headings ka dhaancha badla.")
    if old.get("text_hash") and new.get("text_hash") and old["text_hash"] != new["text_hash"]:
        add("content_changed", "info", "Page ka likha hua badla.")
    ow, nw = int(old.get("words") or 0), int(new.get("words") or 0)
    if ow >= 150 and nw < ow * 0.7:
        add("words_dropped", "warn", f"Page par likha kam hua: {ow} -> {nw} shabd.")
    oh_ = {h for h, _ in (old.get("hreflang") or [])}
    nh_ = {h for h, _ in (new.get("hreflang") or [])}
    if oh_ - nh_:
        add("hreflang_removed", "warn", f"Bhasha links (hreflang) hate: {', '.join(sorted(oh_ - nh_))}.")
    return out


# ---------------------------------------------------------------- AI search crawlers
# (user-agent token, owner, what it does, kind) - kind: search = decides whether that AI can show / cite her pages;
# user = fetches a page a person asked about; training = model training only.
AI_BOTS = (
    ("Googlebot", "Google", "Google Search, AI Overviews and AI Mode", "google"),
    ("Bingbot", "Microsoft", "Bing, Copilot answers (and ChatGPT search partly)", "search"),
    ("OAI-SearchBot", "OpenAI", "ChatGPT search: decides if ChatGPT can cite her", "search"),
    ("ChatGPT-User", "OpenAI", "Opens a page a ChatGPT user asked about", "user"),
    ("GPTBot", "OpenAI", "OpenAI model training only", "training"),
    ("Claude-SearchBot", "Anthropic", "Claude search: decides if Claude can cite her", "search"),
    ("Claude-User", "Anthropic", "Opens a page a Claude user asked about", "user"),
    ("ClaudeBot", "Anthropic", "Anthropic model training only", "training"),
    ("PerplexityBot", "Perplexity", "Perplexity answers: decides if Perplexity can cite her", "search"),
    ("Perplexity-User", "Perplexity", "Opens a page a Perplexity user asked about", "user"),
    ("Google-Extended", "Google", "Gemini training and grounding (NOT Google Search)", "training"),
    ("Applebot", "Apple", "Siri and Spotlight suggestions", "search"),
    ("Applebot-Extended", "Apple", "Apple model training only", "training"),
    ("CCBot", "Common Crawl", "Open web archive used for training", "training"),
    ("Bytespider", "ByteDance", "ByteDance model training", "training"),
    ("Meta-ExternalAgent", "Meta", "Meta AI training", "training"),
    ("Amazonbot", "Amazon", "Alexa answers", "search"),
)


def ai_bots(robots_txt: str, home: str = "https://example.com/") -> dict[str, Any]:
    """Which crawlers robots.txt lets reach the home page -> {rows, issues}. A blocked SEARCH bot is a real loss (that AI
    cannot cite her); a blocked TRAINING bot is her choice and costs nothing in search, so it is only noted."""
    rp = RobotFileParser()
    rp.parse((robots_txt or "").splitlines())
    rows, issues = [], []
    for ua, owner, what, kind in AI_BOTS:
        ok = True if not robots_txt else rp.can_fetch(ua, home)
        rows.append({"bot": ua, "owner": owner, "what": what, "kind": kind, "allowed": ok})
    blocked_search = [r["bot"] for r in rows if not r["allowed"] and r["kind"] == "search"]
    if any(r["bot"] == "Googlebot" and not r["allowed"] for r in rows):
        issues.append({"code": "google_blocked", "level": "bad", "url": home,
                       "text": "robots.txt Googlebot ko rok raha hai: Google Search aur AI Overviews dono se bahar.",
                       "fix": "robots.txt mein Googlebot ke liye Disallow: / hataiye."})
    if blocked_search:
        issues.append({"code": "ai_search_blocked", "level": "warn", "url": home,
                       "text": f"robots.txt AI search bots ko rok raha hai: {', '.join(blocked_search)}. Yeh AI aapko jawab mein dikha / cite nahi kar payenge.",
                       "fix": "Inhe Allow kijiye (training bots jaise GPTBot / ClaudeBot rokna theek hai; woh search se alag hain)."})
    blocked_train = [r["bot"] for r in rows if not r["allowed"] and r["kind"] == "training"]
    if blocked_train:
        issues.append({"code": "ai_training_blocked", "level": "info", "url": home,
                       "text": f"Training bots ruke hain: {', '.join(blocked_train)}. Yeh aapki marzi hai; search par asar nahi.",
                       "fix": "Kuch karna zaroori nahi."})
    return {"rows": rows, "issues": issues}


# ---------------------------------------------------------------- schema (JSON-LD)
RETIRED = {"HowTo": "Google ne HowTo rich result Sept 2023 mein band kiya.",
           "SpecialAnnouncement": "July 2025 se band.", "CourseInfo": "June 2025 se band.", "EstimatedSalary": "June 2025 se band.",
           "LearningVideo": "June 2025 se band.", "VehicleListing": "June 2025 se rich result band.",
           "ClaimReview": "June 2025 se Search mein rich result nahi (sirf fact-check publishers ke kaam ka).",
           "PracticeProblem": "Jan 2026 se band."}
NO_RICH = {"FAQPage": "Google ne FAQ rich results 7 May 2026 se sab sites ke liye band kar diye. Schema rakh sakte hain (AI ko samajh aata hai), par Google mein FAQ dropdown nahi aayega."}
REQUIRED: dict[str, tuple[str, ...]] = {
    "LocalBusiness": ("name", "address"), "Organization": ("name", "url"), "Product": ("name",),
    "Offer": ("price", "priceCurrency"), "Article": ("headline",), "BlogPosting": ("headline",), "NewsArticle": ("headline",),
    "Event": ("name", "startDate", "location"), "Review": ("itemReviewed", "reviewRating", "author"),
    "AggregateRating": ("ratingValue",), "BreadcrumbList": ("itemListElement",), "JobPosting": ("title", "datePosted", "hiringOrganization"),
    "Recipe": ("name", "image"), "VideoObject": ("name", "thumbnailUrl", "uploadDate"), "Course": ("name", "description"),
    "Person": ("name",), "WebSite": ("name", "url"), "Service": ("name",),
}
_LOCAL_TYPES = re.compile(r"(LocalBusiness|Store|Restaurant|Dentist|Physician|AutoRepair|Shop|Hotel|School|Clinic|Salon|Gym|Bakery|Cafe)$")


def _types(node: Any) -> list[str]:
    t = node.get("@type") if isinstance(node, dict) else None
    return [str(x) for x in (t if isinstance(t, list) else [t]) if x]


def _nodes(obj: Any) -> list[dict[str, Any]]:
    """Every typed node in a JSON-LD block (top level, @graph, nested values)."""
    out: list[dict[str, Any]] = []

    def walk(o, depth=0):
        if depth > 6:
            return
        if isinstance(o, dict):
            if o.get("@type"):
                out.append(o)
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o[:60]:
                walk(v, depth + 1)
    walk(obj)
    return out


def schema_parse(blocks: list[str]) -> dict[str, Any]:
    """Raw JSON-LD script texts -> {types, hash, problems}. problems: invalid JSON, no @context, retired types, missing
    required fields, FAQPage (no rich result any more)."""
    types: list[str] = []
    problems: list[dict[str, str]] = []
    for raw in blocks[:20]:
        try:
            obj = json.loads(raw.strip().rstrip(";"))
        except ValueError:
            problems.append({"code": "schema_invalid", "level": "warn", "text": "Ek JSON-LD block ka JSON toota hua hai: Google use padh nahi payega.",
                             "fix": "Comma / quote theek kijiye; Rich Results Test se jaanchiye."})
            continue
        tops = obj if isinstance(obj, list) else [obj]
        if not any(isinstance(t, dict) and "@context" in t for t in tops):
            problems.append({"code": "schema_invalid", "level": "info", "text": "JSON-LD mein @context nahi.",
                             "fix": '"@context": "https://schema.org" jodiye.'})
        for n in _nodes(obj):
            for t in _types(n):
                types.append(t)
                if t in RETIRED:
                    problems.append({"code": "schema_retired", "level": "info", "text": f"{t} schema ab Google mein kuch nahi dikhata: {RETIRED[t]}",
                                     "fix": "Hata sakte hain; zaroorat ho to milta-julta chalu type (jaise Article / Service) lagaiye."})
                if t in NO_RICH:
                    problems.append({"code": "schema_faq", "level": "info", "text": NO_RICH[t], "fix": "Kuch zaroori nahi; naya FAQ schema banane mein mehnat mat lagaiye."})
                req = REQUIRED.get(t) or (REQUIRED["LocalBusiness"] if _LOCAL_TYPES.search(t) else ())
                miss = [k for k in req if not n.get(k)]
                if miss:
                    problems.append({"code": "schema_missing_field", "level": "warn",
                                     "text": f"{t} schema mein zaroori cheez nahi: {', '.join(miss)}.",
                                     "fix": "Yeh fields bhariye, warna Google rich result nahi dega."})
    h = hashlib.sha1(json.dumps(sorted(types)).encode() + "".join(b.strip() for b in blocks).encode()).hexdigest()[:16] if blocks else ""
    seen, uniq = set(), []
    for p in problems:
        k = (p["code"], p["text"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return {"types": sorted(set(types)), "hash": h, "problems": uniq}


def schema_template(kind: str, b: dict[str, Any], page: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ready JSON-LD for the common, still-supported types, from only what she gave (empty fields are left out)."""
    page = page or {}
    url, name = b.get("url", ""), b.get("name", "")
    if kind == "organization":
        d: dict[str, Any] = {"@type": "Organization", "name": name, "url": url, "logo": b.get("logo"), "telephone": b.get("phone"),
                             "sameAs": b.get("same_as")}
    elif kind == "website":
        d = {"@type": "WebSite", "name": name, "url": url}
    elif kind == "breadcrumb":
        parts = [x for x in urlparse(page.get("url") or url).path.split("/") if x]
        items, acc = [{"@type": "ListItem", "position": 1, "name": "Home", "item": url}], url.rstrip("/")
        for i, p in enumerate(parts, 2):
            acc += "/" + p
            items.append({"@type": "ListItem", "position": i, "name": p.replace("-", " ").title(), "item": acc})
        d = {"@type": "BreadcrumbList", "itemListElement": items}
    elif kind == "service":
        d = {"@type": "Service", "name": page.get("title") or (b.get("services") or [""])[0], "serviceType": page.get("title"),
             "provider": {"@type": b.get("schema_type") or "LocalBusiness", "name": name, "url": url},
             "areaServed": b.get("city")}
    elif kind == "product":
        d = {"@type": "Product", "name": page.get("title") or "", "description": page.get("description"),
             "brand": {"@type": "Brand", "name": name},
             "offers": {"@type": "Offer", "price": page.get("price"), "priceCurrency": "INR", "availability": "https://schema.org/InStock",
                        "url": page.get("url")}}
    elif kind == "article":
        d = {"@type": "Article", "headline": (page.get("title") or "")[:110], "author": {"@type": "Person", "name": page.get("author") or name},
             "datePublished": page.get("date"), "publisher": {"@type": "Organization", "name": name}}
    else:
        raise ValueError("kind: organization | website | breadcrumb | service | product | article (LocalBusiness: schema_draft)")

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if v not in (None, "", [], {})}
        return o
    return {"@context": "https://schema.org", **clean(d)}


# ---------------------------------------------------------------- page type + content quality
WORD_FLOOR = {"home": 500, "service": 800, "blog": 1500, "product": 300, "location": 500}
_BLOG = re.compile(r"/(blog|news|article|articles|post|posts|lekh|guide|guides)/", re.I)
_PRODUCT = re.compile(r"/(product|products|shop|item|p)/", re.I)
_SERVICE = re.compile(r"/(service|services|seva|treatment|treatments|course|courses|solutions?)/", re.I)
_LOCATION = re.compile(r"/(location|locations|city|cities|area|areas|branch|branches|near|in-[a-z-]+)/", re.I)
# Filler phrases that make a page read as machine-made. Hoola's own list (English + Hinglish), written for Indian sites.
FILLER = ("in today's fast-paced world", "in today's digital age", "look no further", "unlock the power", "unleash",
          "elevate your", "seamless experience", "game-changer", "game changer", "delve into", "a testament to", "navigating the",
          "in the ever-evolving", "ever-changing landscape", "it's important to note", "whether you're a", "one-stop solution",
          "one stop solution", "best in class", "world-class quality", "aaj ke daur mein", "aaj ki tez raftaar", "behtareen anubhav",
          "aapki sabhi zarooraton", "sabse best", "no.1 company", "number 1 company", "100% satisfaction guaranteed")
_CLAIM = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%|\b\d+(?:,\d{3})+\+?\s+(?:customers|clients|users|graahak|log)\b|"
                    r"\b(?:studies show|research shows|according to experts|survey)\b", re.I)


def page_type(p: dict[str, Any]) -> str:
    if p.get("is_home"):
        return "home"
    path = urlparse(p.get("url", "")).path.lower() + "/"
    types = set(p.get("schema_types") or [])
    if types & {"Article", "BlogPosting", "NewsArticle"} or _BLOG.search(path):
        return "blog"
    if "Product" in types or _PRODUCT.search(path):
        return "product"
    if _LOCATION.search(path):
        return "location"
    if "Service" in types or _SERVICE.search(path):
        return "service"
    if p.get("is_contact"):
        return "contact"
    return "other"


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?।])\s+", text or "") if len(s.split()) >= 3]


def quality(p: dict[str, Any]) -> list[dict[str, Any]]:
    """Content checks on one page's own words (text_sample, first ~6,000 characters)."""
    out: list[dict[str, Any]] = []
    text = p.get("text_sample") or ""
    words = int(p.get("words") or 0)
    kind = page_type(p)
    floor = WORD_FLOOR.get(kind)
    if floor and 250 <= words < floor:            # under 250 words is already "thin" in rules.page_issues
        out.append({"code": "word_floor", "level": "info",
                    "text": f"{kind.title()} page par {words} shabd; is tarah ke page aam taur par {floor}+ shabd mein vishay poora samjhaate hain.",
                    "fix": "Sirf shabd mat badhaiye: graahak ke asli sawaal, daam, misaal, photo jodiye. Shabd ginti ranking factor nahi, poora jawab hai."})
    sents = _sentences(text)
    if len(sents) >= 8:
        avg = sum(len(s.split()) for s in sents) / len(sents)
        if avg > 26:
            out.append({"code": "readability", "level": "info", "text": f"Vaakya lambe hain (ausat {avg:.0f} shabd).",
                        "fix": "15-20 shabd ke chhote vaakya; ek paragraph mein ek baat."})
    toks = [w for w in re.findall(r"[a-zA-Zऀ-ॿ]{4,}", text.lower())]
    if len(toks) >= 300:
        top, cnt = max(((w, toks.count(w)) for w in set(toks)), key=lambda x: x[1])
        if cnt / len(toks) > 0.045:
            out.append({"code": "stuffing", "level": "warn", "text": f"'{top}' shabd bahut baar ({cnt} baar, {cnt * 100 / len(toks):.1f}%): keyword stuffing jaisa lagta hai.",
                        "fix": "Shabd ko kudrati tareeke se rakhiye; milte-julte shabd aur asli jaankari likhiye."})
    low = text.lower()
    hits = [f for f in FILLER if f in low]
    if len(hits) >= 2:
        out.append({"code": "filler", "level": "info", "text": f"Ghise-pite vaakya: '{hits[0]}', '{hits[1]}'" + (f" +{len(hits) - 2}" if len(hits) > 2 else "") + ".",
                    "fix": "Inki jagah apni dukaan ki asli baat: kitne saal, kaun se kaam, kis mohalle mein, kya daam."})
    claims = _CLAIM.findall(text)
    if len(claims) >= 2 and not p.get("ext_links"):
        out.append({"code": "claims", "level": "info", "text": f"Page par {len(claims)} aankde / daave hain par koi source link nahi.",
                    "fix": "Har aankde ke saath source (sarkari site, report) ka link, ya apna asli record (jaise '2019 se 1,200 graahak')."})
    if kind == "blog" and not (p.get("author") and p.get("published")):
        miss = [x for x, ok in (("likhne wale ka naam", p.get("author")), ("tareekh", p.get("published"))) if not ok]
        out.append({"code": "byline", "level": "info", "text": f"Lekh par {' aur '.join(miss)} nahi.",
                    "fix": "Lekhak ka naam (chhota parichay) aur likhne / badalne ki tareekh dikhaiye: bharosa (E-E-A-T) badhta hai."})
    return out


# ---------------------------------------------------------------- images
IMG_BANDS = {"hero": (200, 300, 700), "content": (100, 200, 500), "thumb": (50, 100, 200)}       # KB: good / warn / bad


def image_issues(p: dict[str, Any], sizes: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Weight (from HEAD sizes the crawl fetched for some pictures), missing width / height (layout shift), no lazy loading
    below the first pictures, old formats."""
    out: list[dict[str, Any]] = []
    imgs = p.get("imgs") or []
    if not imgs:
        return out
    sizes = sizes or {}
    heavy, bad = [], []
    for i, im in enumerate(imgs):
        kb = (sizes.get(im.get("src", "")) or 0) / 1024
        if not kb:
            continue
        band = "hero" if i == 0 else "thumb" if (im.get("w") or 999) <= 200 else "content"
        _good, warn, worst = IMG_BANDS[band]
        if kb > worst:
            bad.append((im["src"], round(kb)))
        elif kb > warn:
            heavy.append((im["src"], round(kb)))
    if bad or heavy:
        lst = bad + heavy
        out.append({"code": "img_heavy", "level": "warn" if bad else "info",
                    "text": f"{len(lst)} photo bhaari: " + ", ".join(f"{urlparse(s).path.rsplit('/', 1)[-1][:40]} ({kb} KB)" for s, kb in lst[:3]) + ".",
                    "fix": "WebP / AVIF mein badliye aur screen ke size par chhota kijiye (badi photo 200-300 KB, chhoti 100 KB tak)."})
    nosize = sum(1 for im in imgs if not (im.get("w") and im.get("h")))
    if nosize >= 3:
        out.append({"code": "img_size", "level": "info", "text": f"{nosize} photo bina width / height: page load hote waqt hilta hai (CLS).",
                    "fix": '<img width="..." height="..."> likhiye.'})
    nolazy = sum(1 for im in imgs[3:] if (im.get("loading") or "") != "lazy")
    if nolazy >= 5:
        out.append({"code": "img_lazy", "level": "info", "text": f"Neeche ki {nolazy} photo turant load hoti hain.",
                    "fix": 'Pehli 2-3 ke baad loading="lazy" lagaiye (sabse upar wali photo par nahi).'})
    old = sum(1 for im in imgs if re.search(r"\.(jpe?g|png|bmp|gif)(\?|$)", im.get("src", ""), re.I))
    if old >= 4 and old >= len(imgs) * 0.6:
        out.append({"code": "img_format", "level": "info", "text": f"{old} photo JPG / PNG mein.",
                    "fix": "WebP (ya AVIF) aam taur par 25-50% halki hoti hai, wahi quality."})
    return out


# ---------------------------------------------------------------- hreflang
_LANG = re.compile(r"^(x-default|[a-z]{2,3}(-[A-Za-z]{2}|-[A-Za-z]{4}|-\d{3})?)$")


def hreflang_page(p: dict[str, Any]) -> list[dict[str, Any]]:
    hl = p.get("hreflang") or []
    if not hl:
        return []
    out = []
    badc = sorted({h for h, _ in hl if not _LANG.match(h)})
    if badc:
        out.append({"code": "hreflang", "level": "warn", "text": f"hreflang code galat: {', '.join(badc)[:80]}.",
                    "fix": "ISO code likhiye: hi, en-IN, mr, x-default (jaise 'en-uk' nahi, 'en-GB')."})
    if not any(u.rstrip("/") == (p.get("url") or "").rstrip("/") for _, u in hl):
        out.append({"code": "hreflang", "level": "warn", "text": "hreflang list mein page khud nahi hai.",
                    "fix": "Har bhasha ka page apna link bhi hreflang list mein rakhe."})
    if len({h for h, _ in hl}) >= 2 and "x-default" not in {h for h, _ in hl}:
        out.append({"code": "hreflang", "level": "info", "text": "hreflang mein x-default nahi.",
                    "fix": 'Jo page sabke liye default ho uska <link rel="alternate" hreflang="x-default"> jodiye.'})
    return out


def hreflang_site(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return links: if A says B is its Hindi version, B must say A back. Targets must open and not be noindex."""
    norm = lambda u: (u or "").rstrip("/")                                   # noqa: E731
    by = {norm(p["url"]): p for p in pages}
    out = []
    for p in pages:
        for h, u in p.get("hreflang") or []:
            t = by.get(norm(u))
            if t is None or norm(u) == norm(p["url"]):
                continue
            if int(t.get("status") or 200) >= 400 or t.get("noindex"):
                out.append({"code": "hreflang_return", "level": "warn", "url": p["url"],
                            "text": f"hreflang '{h}' aise page ki taraf jo khulta nahi / noindex hai: {u}", "fix": "Sahi chalu page ka link dijiye."})
            elif not any(norm(u2) == norm(p["url"]) for _, u2 in t.get("hreflang") or []):
                out.append({"code": "hreflang_return", "level": "warn", "url": p["url"],
                            "text": f"{u} wapas is page ka hreflang link nahi deta (dono taraf zaroori).", "fix": "Dono pages ek doosre ko list karein."})
    return out


# ---------------------------------------------------------------- one page, everything above
def page_checks(p: dict[str, Any], sizes: dict[str, int] | None = None) -> list[dict[str, Any]]:
    if int(p.get("status") or 200) >= 400:
        return []
    out: list[dict[str, Any]] = []
    out += [dict(x) for x in (p.get("schema_problems") or [])]
    if p.get("js_shell"):
        out.append({"code": "js_only", "level": "warn",
                    "text": "Page ka likha JavaScript ke baad hi dikhta hai: ChatGPT / Perplexity jaise AI bots aksar JavaScript nahi chalaate, unhe khaali page milta hai.",
                    "fix": "Server-side rendering / pre-render: asli shabd seedhe HTML mein aayein."})
    out += quality(p)
    out += image_issues(p, sizes)
    out += hreflang_page(p)
    return out


# ---------------------------------------------------------------- the whole site
def shingles(text: str, k: int = 5) -> set[int]:
    w = re.findall(r"\w+", (text or "").lower())
    return {zlib.crc32(" ".join(w[i:i + k]).encode()) for i in range(0, max(0, len(w) - k + 1))}


def near_duplicates(pages: list[dict[str, Any]], cut: float = 0.8) -> list[dict[str, Any]]:
    """Pairs of pages whose words are 80%+ the same (5-word shingles, Jaccard). Capped to 200 pages for speed."""
    ok = [p for p in pages if int(p.get("status") or 200) < 400 and len((p.get("text_sample") or "").split()) >= 120][:200]
    sh = [(p, shingles(p["text_sample"])) for p in ok]
    out, seen = [], set()
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][1], sh[j][1]
            if not a or not b:
                continue
            sim = len(a & b) / len(a | b)
            if sim >= cut and sh[j][0]["url"] not in seen:
                seen.add(sh[j][0]["url"])
                out.append({"code": "near_dup", "level": "warn", "url": sh[j][0]["url"],
                            "text": f"Yeh page {sh[i][0]['url']} se {round(sim * 100)}% milta hai.",
                            "fix": "Dono ko ek kijiye (301), ya har page par apni asli, alag jaankari likhiye; ek ko canonical bhi bana sakte hain."})
    return out


def _skeleton(t: str) -> str:
    """A title with its varying words (numbers, place / item names after 'in' / '|' / '-') replaced by a slot."""
    t = re.sub(r"\d+", "#", t.lower())
    return re.sub(r"\b(in|at|near|for|of)\s+[\w\s#'.]+?(?=\s*(\||-|–|$))", r"\1 *", t).strip()


def templated_meta(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """10+ pages whose titles are one template with only a city / item swapped = Google reads them as mass-made."""
    by: dict[str, list[str]] = {}
    for p in pages:
        if int(p.get("status") or 200) < 400 and p.get("title"):
            by.setdefault(_skeleton(p["title"]), []).append(p["url"])
    out = []
    for sk, urls in by.items():
        if len(urls) >= 10 and "*" in sk:
            out.append({"code": "meta_template", "level": "warn", "url": urls[0],
                        "text": f"{len(urls)} page ka title ek hi saancha: '{sk[:60]}' (sirf shehar / naam badla).",
                        "fix": "Har page ka title us page ki asli khaas baat se likhiye (daam, sewa, mohalla), sirf naam badalke nahi."})
    return out


SCALED_WARN, SCALED_STOP = 100, 500
LOCATION_WARN, LOCATION_STOP = 30, 50


def scaled_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Many pages in one folder that share most of their words = scaled content (Google spam policy). Location pages are
    held to a lower count. Uniqueness = share of a page's 5-word runs found on no sibling."""
    by: dict[str, list[dict[str, Any]]] = {}
    for p in pages:
        parts = [x for x in urlparse(p.get("url", "")).path.split("/") if x]
        if len(parts) >= 2 and int(p.get("status") or 200) < 400:
            by.setdefault(parts[0].lower(), []).append(p)
    out = []
    for folder, ps in by.items():
        loc = bool(_LOCATION.search(f"/{folder}/"))
        warn_at = LOCATION_WARN if loc else SCALED_WARN
        if len(ps) < warn_at:
            continue
        sample = ps[:60]
        sh = [shingles(p.get("text_sample") or "") for p in sample]
        uniq = []
        for i, a in enumerate(sh):
            if not a:
                continue
            others = set().union(*(b for j, b in enumerate(sh) if j != i)) if len(sh) > 1 else set()
            uniq.append(len(a - others) / len(a))
        u = round(100 * sum(uniq) / len(uniq)) if uniq else 0
        stop = len(ps) >= (LOCATION_STOP if loc else SCALED_STOP)
        if u < 40 or stop:
            out.append({"code": "scaled", "level": "bad" if (u < 30 or stop) else "warn", "url": ps[0]["url"],
                        "text": f"/{folder}/ mein {len(ps)} {'location ' if loc else ''}page, har page ka sirf ~{u}% apna likha hai: Google ise scaled content (spam) maan sakta hai.",
                        "fix": "Har page par 30-40%+ asli alag jaankari (us jagah / cheez ki khaas baat, photo, daam, review); jo page kuch naya nahi dete unhe hataiye ya jodiye."})
    return out


_PHONE = re.compile(r"(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}\b")


def _digits(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    return d[-10:] if len(d) >= 10 else d


def nap(pages: list[dict[str, Any]], biz: dict[str, Any]) -> list[dict[str, Any]]:
    """Name / address / phone the same everywhere: the phone on her pages vs the phone she gave; her pin on the contact /
    home page."""
    out = []
    phone = _digits(str(biz.get("phone") or ""))
    found: dict[str, str] = {}
    for p in pages:
        for ph in p.get("phones") or []:
            found.setdefault(_digits(ph), p["url"])
    if phone and found and phone not in found:
        other = next(iter(found))
        out.append({"code": "nap", "level": "warn", "url": found[other],
                    "text": f"Website par phone {other} hai, aapke business ka phone {phone} - dono alag.",
                    "fix": "Website, Google profile aur directories mein ek hi phone number (NAP ek jaisa)."})
    elif len(found) >= 3:
        out.append({"code": "nap", "level": "info", "url": next(iter(found.values())),
                    "text": f"Website par {len(found)} alag phone number.", "fix": "Ek mukhya number rakhiye, sab jagah wahi."})
    pin = str(biz.get("pin") or "").strip()
    keyp = [p for p in pages if p.get("is_home") or p.get("is_contact")]
    if pin and keyp and not any(pin in (p.get("text_sample") or "") for p in keyp):
        out.append({"code": "nap", "level": "info", "url": keyp[0]["url"],
                    "text": f"Home / contact page par pura pata (pin {pin}) nahi dikha.",
                    "fix": "Footer ya contact page par pura pata, bilkul Google profile jaisa."})
    return out


def gbp_links(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Links to *.business.site: Google closed those free sites in 2024, so the links are dead."""
    bad = sorted({p["url"] for p in pages if any("business.site" in (u or "") for u in p.get("ext") or [])})
    if not bad:
        return []
    return [{"code": "gbp_link", "level": "warn", "url": bad[0],
             "text": f"{len(bad)} page par purani business.site website ka link: Google ne woh sites 2024 mein band kar di.",
             "fix": "Link hataiye ya apni asli website / Google Maps profile link lagaiye."}]


PARASITE = re.compile(r"\b(casino|betting|satta|matka|slot\s?gacor|togel|viagra|cialis|payday loan|essay writing|escort|"
                      r"crypto signals|replica watches)\b", re.I)


def parasite(pages: list[dict[str, Any]], services: list[str] | None = None) -> list[dict[str, Any]]:
    """Pages about something far from her business (betting, pills, essays...) - the site may be hacked or a section rented
    out (Google's site reputation abuse policy)."""
    mine = " ".join(services or []).lower()
    hits = []
    for p in pages:
        blob = " ".join([p.get("url", ""), p.get("title", ""), (p.get("text_sample") or "")[:3000]])
        m = PARASITE.search(blob)
        if m and m.group(1).lower() not in mine:
            hits.append((p["url"], m.group(1)))
    if not hits:
        return []
    return [{"code": "parasite", "level": "bad", "url": hits[0][0],
             "text": f"{len(hits)} page par '{hits[0][1]}' jaisi cheezein jo aapke kaam se mel nahi khaati: site hack ho sakti hai ya kisi ne section kiraye par liya.",
             "fix": "Turant dekhiye: anjaan pages hataiye, passwords badliye, plugins update kijiye; Search Console mein Security Issues dekhiye."}]


SEC_HEADERS = (("strict-transport-security", "HSTS (browser hamesha https par aaye)"),
               ("x-content-type-options", "X-Content-Type-Options: nosniff"),
               ("referrer-policy", "Referrer-Policy"))


def security(headers: dict[str, str] | None, hops: list[str] | None, home: str = "") -> list[dict[str, Any]]:
    out = []
    if headers is not None:
        h = {k.lower(): v for k, v in headers.items()}
        miss = [label for k, label in SEC_HEADERS if k not in h]
        frame = "x-frame-options" in h or "frame-ancestors" in h.get("content-security-policy", "")
        if not frame:
            miss.append("X-Frame-Options / CSP frame-ancestors (doosri site aapko frame mein na dikha sake)")
        if miss and home.startswith("https://"):
            out.append({"code": "sec_headers", "level": "info", "url": home, "text": f"Security headers nahi: {'; '.join(miss)}.",
                        "fix": "Hosting / server settings mein yeh headers jodiye (aapke web wale 10 minute ka kaam)."})
    if hops and len(hops) > 2:
        out.append({"code": "redirect_hops", "level": "warn", "url": hops[0],
                    "text": f"Website kholne par {len(hops) - 1} redirect: {' -> '.join(hops[:4])}.",
                    "fix": "Ek hi redirect seedha final https URL par (http -> https -> www jaisi zanjeer nahi)."})
    return out


def llms_txt(found: bool, home: str) -> list[dict[str, Any]]:
    if found:
        return []
    return [{"code": "llms_txt", "level": "info", "url": home,
             "text": "llms.txt nahi hai. Google ko iski zaroorat nahi; kuch AI tools ise padhte hain.",
             "fix": "Chahein to /llms.txt mein business ka chhota parichay aur mukhya pages ke links (zaroori nahi)."}]


def eeat(pages: list[dict[str, Any]], biz: dict[str, Any]) -> dict[str, Any]:
    """Experience / Expertise / Authoritativeness / Trust from what the crawl SEES (20 / 25 / 25 / 30). Signals, not a
    Google number: Google has no E-E-A-T score; these are the things its raters look for."""
    ok = [p for p in pages if int(p.get("status") or 200) < 400]
    paths = " ".join(urlparse(p["url"]).path.lower() for p in ok)
    text = " ".join((p.get("text_sample") or "")[:2500].lower() for p in ok[:80])
    types = set(t for p in ok for t in p.get("schema_types") or [])
    sig = {
        "experience": [("Asli photo / kaam ki misaal (gallery, portfolio, case study)", bool(re.search(r"gallery|portfolio|case-stud|our-work|projects", paths))),
                       ("Graahakon ke review / testimonials", bool(re.search(r"testimonial|review|graahak", paths + " " + text)) or "Review" in types or "AggregateRating" in types),
                       ("Kitne saal ka anubhav likha hai", bool(re.search(r"(since|se)\s+(19|20)\d\d|\d+\+?\s+(years|saal)", text)))],
        "expertise": [("About page", bool(re.search(r"about|hamare-baare|parichay", paths))),
                      ("Lekh par lekhak ka naam", any(p.get("author") for p in ok)),
                      ("Team / doctor / expert ka parichay", bool(re.search(r"team|doctor|expert|founder|staff", paths))),
                      ("Gehri jaankari wale pages (800+ shabd)", sum(1 for p in ok if int(p.get("words") or 0) >= 800) >= 2)],
        "authority": [("Organization / LocalBusiness schema", bool(types & {"Organization", "LocalBusiness"}) or any(_LOCAL_TYPES.search(t) for t in types)),
                      ("Social / directory profiles (sameAs)", bool(biz.get("same_as")) or any(p.get("sameas") for p in ok)),
                      ("Bahar ke bharosemand sources ke links", sum(int(p.get("ext_links") or 0) for p in ok) >= 3),
                      ("Awards / certificates / registrations", bool(re.search(r"award|certified|certificate|iso\s?\d|registered|gst|fssai|msme", text)))],
        "trust": [("Contact page", any(p.get("is_contact") for p in ok)),
                  ("Phone number dikhta hai", any(p.get("phones") for p in ok)),
                  ("Pura pata", bool(biz.get("pin")) and str(biz.get("pin")) in text),
                  ("Privacy policy", "privacy" in paths),
                  ("Poori site https", bool(ok) and all(p.get("https") for p in ok)),
                  ("Refund / terms page", bool(re.search(r"refund|terms|return", paths)))],
    }
    weights = {"experience": 20, "expertise": 25, "authority": 25, "trust": 30}
    parts, total = [], 0
    for k, items in sig.items():
        got = sum(1 for _, v in items if v)
        sc = round(weights[k] * got / len(items))
        total += sc
        parts.append({"key": k, "max": weights[k], "score": sc, "signals": [{"text": t, "ok": v} for t, v in items]})
    return {"total": total, "parts": parts}


def eeat_issues(e: dict[str, Any], home: str) -> list[dict[str, Any]]:
    miss = [s["text"] for p in e["parts"] for s in p["signals"] if not s["ok"]]
    if e["total"] >= 70 or not miss:
        return []
    return [{"code": "eeat", "level": "info", "url": home, "text": f"Bharose ke sanket kam (E-E-A-T {e['total']}/100). Nahi mila: {'; '.join(miss[:4])}.",
             "fix": "Inmein se jo sach mein aapke paas hai, website par dikhaiye. Kuch bhi nakli mat likhiye."}]


def local_score(pages: list[dict[str, Any]], biz: dict[str, Any], nap_issues: list[dict[str, Any]],
                gbp: dict[str, Any] | None = None) -> dict[str, Any]:
    """Local search scorecard: Google profile 25, reviews 20, on-page 20, NAP 15, schema 10, links 10. Parts Hoola cannot
    measure yet (her Google profile without the GBP API) show 'not checked' and do not count in the total."""
    ok = [p for p in pages if int(p.get("status") or 200) < 400]
    city = str(biz.get("city") or "").lower()
    home = next((p for p in ok if p.get("is_home")), ok[0] if ok else {})
    parts: list[dict[str, Any]] = []
    gbp = gbp or {}
    parts.append({"key": "gbp", "label": "Google profile", "max": 25,
                  "score": None if not gbp else round(25 * min(1.0, gbp.get("complete", 0) / 100))})
    parts.append({"key": "reviews", "label": "Reviews", "max": 20,
                  "score": None if "reviews" not in gbp else min(20, (10 if gbp["reviews"] >= 10 else gbp["reviews"]) + (10 if gbp.get("rating", 0) >= 4.5 else 5 if gbp.get("rating", 0) >= 4 else 0))})
    onp = 0
    blob = " ".join([home.get("title", ""), " ".join(home.get("h1") or []), home.get("description", "")]).lower()
    onp += 8 if city and city in blob else 0
    onp += 6 if any(p.get("is_contact") for p in ok) else 0
    onp += 6 if any(p.get("map") for p in ok) else 0
    parts.append({"key": "onpage", "label": "Shehar + contact on the site", "max": 20, "score": onp if city else None})
    parts.append({"key": "nap", "label": "Same name / address / phone", "max": 15,
                  "score": 15 - 7 * sum(1 for i in nap_issues if i["level"] == "warn") - 3 * sum(1 for i in nap_issues if i["level"] == "info")
                  if biz.get("phone") or biz.get("pin") else None})
    types = set(t for p in ok for t in p.get("schema_types") or [])
    parts.append({"key": "schema", "label": "LocalBusiness schema", "max": 10,
                  "score": 10 if any(_LOCAL_TYPES.search(t) for t in types) else 0})
    parts.append({"key": "links", "label": "Profiles linked (sameAs)", "max": 10, "score": 10 if biz.get("same_as") else 0})
    for p in parts:
        if p["score"] is not None:
            p["score"] = max(0, min(p["max"], p["score"]))
    got = [p for p in parts if p["score"] is not None]
    mx = sum(p["max"] for p in got)
    return {"total": round(100 * sum(p["score"] for p in got) / mx) if mx else None, "parts": parts,
            "measured": mx, "note": "Google profile aur reviews tab gine jaate hain jab Hoola profile padh sake (GBP API)."}


def site_checks(pages: list[dict[str, Any]], biz: dict[str, Any], services: list[str] | None = None, home: str = "",
                headers: dict[str, str] | None = None, hops: list[str] | None = None, llms: bool | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out += near_duplicates(pages)
    out += templated_meta(pages)
    out += scaled_pages(pages)
    out += hreflang_site(pages)
    out += nap(pages, biz)
    out += gbp_links(pages)
    out += parasite(pages, services)
    out += security(headers, hops, home)
    if llms is not None:
        out += llms_txt(llms, home)
    out += eeat_issues(eeat(pages, biz), home)
    for i in out:
        i.setdefault("url", home)
    return out


# ---------------------------------------------------------------- the report envelope (every plan item says how we'd know)
ENVELOPE = {
    "technical": ("Google can only rank what it can reach, open and index.",
                  "Search Console still shows the pages as not indexed / with errors 2 weeks after the fix.",
                  "Indexed pages and crawl errors in Search Console move within 1-2 weeks."),
    "content": ("People and Google pick the page that answers the question best.",
                "Impressions for the page's searches do not rise within 6 weeks.",
                "Impressions and new search words for that page in Search Console."),
    "local": ("Nearby customers choose from the Google map pack; a complete, consistent profile wins it.",
              "No rise in calls / direction requests / map views within 6 weeks.",
              "Profile views and calls; impressions for 'near me' and city searches."),
    "authority": ("Mentions and links from trusted local sites tell Google the business is real.",
                  "No new referring sites or brand searches within 8 weeks.",
                  "Brand searches and new referring pages in Search Console Links."),
    "ai_search": ("AI answers cite pages they can read and trust.",
                  "Her pages still not shown / cited for her questions after 8 weeks.",
                  "Search Console AI / web impressions for long questions."),
    "reporting": ("What is measured against a baseline can be steered.",
                  "The report misses a number she asked for.",
                  "She reads and acts on the monthly report."),
}


def envelope(workstream: str) -> dict[str, str]:
    why, fail, signal = ENVELOPE.get(workstream, ENVELOPE["technical"])
    return {"principle": why, "fail_check": fail, "signal": signal}


# ---------------------------------------------------------------- Google's confirmed changes (to explain a drop)
# Official Google sources only (Search Status Dashboard / Search Central). Re-check when a new one is announced.
UPDATES = (
    ("2024-03-05", "March 2024 core update + new spam policies (scaled content, site reputation, expired domains)", "core"),
    ("2024-06-20", "June 2024 spam update", "spam"),
    ("2024-08-15", "August 2024 core update", "core"),
    ("2024-11-11", "November 2024 core update", "core"),
    ("2024-12-12", "December 2024 core update", "core"),
    ("2024-12-19", "December 2024 spam update", "spam"),
    ("2025-03-13", "March 2025 core update", "core"),
    ("2025-06-12", "Several structured data types retired", "schema"),
    ("2025-06-30", "June 2025 core update", "core"),
    ("2025-08-26", "August 2025 spam update", "spam"),
    ("2025-12-11", "December 2025 core update", "core"),
    ("2026-03-24", "March 2026 spam update", "spam"),
    ("2026-03-27", "March 2026 core update", "core"),
    ("2026-04-13", "Back-button hijacking spam policy", "policy"),
    ("2026-05-07", "FAQ rich results retired for all sites", "schema"),
    ("2026-05-21", "May 2026 core update", "core"),
    ("2026-06-24", "June 2026 spam update", "spam"),
    ("2026-08-18", "August 2026 spam update", "spam"),
    ("2026-09-24", "September 2026 spam update", "spam"),
)


def updates_between(a: str, b: str) -> list[dict[str, str]]:
    """Google changes dated inside [a, b] (ISO dates), padded a week before (rollouts take ~2 weeks)."""
    try:
        lo = (date.fromisoformat(a[:10]) - timedelta(days=7)).isoformat()
    except ValueError:
        lo = a[:10]
    return [{"date": d, "name": n, "kind": k} for d, n, k in UPDATES if lo <= d <= b[:10]]

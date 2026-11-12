"""SEO rules Hoola works to (researched 22 Oct 2026; sources in CLAUDE.md v0.103). Pure functions.

Google Search Essentials + spam policies (no link buying / link schemes, no keyword stuffing, cloaking, doorway pages,
scaled content abuse, site reputation abuse, fake or gated reviews). Core Web Vitals at the 75th percentile of field data:
LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 (poor: > 4 s, > 500 ms, > 0.25); unchanged in 2026. Core updates in 2026
(March, May 21 + more) keep rewarding helpful, people-first pages; AI Mode / AI Overviews clicks and impressions count
inside Search Console "Web" totals (no separate filter), so long conversational queries show up there. llms.txt is not
needed for Google AI Search. Titles ~ 30-60 characters (Google cuts by pixels, ~600 px), descriptions ~ 70-160.
"""
from __future__ import annotations

import json
import re

CWV = {"lcp": (2500, 4000), "inp": (200, 500), "cls": (0.1, 0.25)}           # good <=, poor >
TITLE = (30, 60)
DESC = (70, 160)
THIN_WORDS = 250
STRIKING = (4.0, 20.0)          # positions where a little work moves a page to the top 3

NEVER = ("No buying backlinks or link exchange schemes (Google spam policy).",
         "No fake reviews, no discount in exchange for reviews, and no asking only happy customers for reviews (review gating).",
         "No keyword stuffing, hidden text, cloaking or doorway pages.",
         "No publishing thousands of AI pages at once (scaled content abuse); every page must have real value.",
         "No scraping of Google search results: only the official Search Console / PageSpeed APIs and your own website.",
         "Changes to the website / Google profile only with your approval; Hoola does not publish on its own.")


def cwv_grade(metric: str, value) -> str:
    if value is None:
        return "na"
    good, poor = CWV[metric]
    v = float(value)
    return "good" if v <= good else "poor" if v > poor else "ni"


def intent(query: str) -> str:
    q = f" {query.lower()} "
    if any(w in q for w in (" near me", " nearby", " paas ", " mere paas", " in my area", " nazdeek")):
        return "local"
    if any(w in q for w in (" price", " rate", " cost", " kitne ", " kitna ", " buy", " kharid", " order", " booking", " book ",
                            " cheap", " sasta", " offer", " discount")):
        return "transactional"
    if any(w in q for w in (" best ", " top ", " vs ", " review", " compare", " better")):
        return "commercial"
    if any(w in q for w in (" how ", " what ", " why ", " kaise", " kya ", " kyu", " kab ", " meaning", " tips", " guide")):
        return "informational"
    return "navigational" if len(q.split()) <= 2 else "informational"


def ctr_expected(position: float) -> float:
    """Rough organic CTR by position (industry curves; used only to rank opportunities, never promised)."""
    table = {1: .28, 2: .15, 3: .10, 4: .07, 5: .05, 6: .04, 7: .03, 8: .025, 9: .02, 10: .018}
    p = max(1, round(position or 50))
    return table.get(p, .01 if p <= 20 else .003)


def opportunity(row: dict) -> dict | None:
    """A Search Console row {query, page, clicks, impressions, ctr, position} -> what to do, or None."""
    pos, imp, ctr = float(row.get("position") or 0), int(row.get("impressions") or 0), float(row.get("ctr") or 0)
    if imp < 20:
        return None
    exp = ctr_expected(pos)
    if STRIKING[0] <= pos <= STRIKING[1]:
        gain = round(imp * (ctr_expected(3) - ctr))
        return {"kind": "striking", "gain": max(gain, 0),
                "do": f"'{row['query']}' is at position {pos:.1f}: strengthen this word on the page in the heading / first paragraph, the FAQ and internal links."}
    if pos < STRIKING[0] and ctr < exp * 0.6:
        gain = round(imp * (exp - ctr))
        return {"kind": "low_ctr", "gain": max(gain, 0),
                "do": f"'{row['query']}' is in the top {pos:.0f} but gets few clicks ({ctr * 100:.1f}%): write a better title and description."}
    return None


def cannibal(rows: list[dict]) -> list[dict]:
    """The same query split across 2+ pages of the site (each with real impressions)."""
    by: dict[str, list[dict]] = {}
    for r in rows:
        if int(r.get("impressions") or 0) >= 10:
            by.setdefault(r["query"], []).append(r)
    out = []
    for q, rs in by.items():
        pages = {r["page"] for r in rs}
        if len(pages) > 1:
            out.append({"query": q, "pages": sorted(pages), "do": "Two pages are competing for the same word: make one the main page and link / merge the other into it."})
    return out


def page_issues(p: dict, city: str = "") -> list[dict]:
    """On-page checks for one crawled page dict (see service._parse). Each issue: {code, level bad|warn|info, text, fix}."""
    out = []

    def add(code, level, text, fix):
        out.append({"code": code, "level": level, "text": text, "fix": fix})

    if p.get("status", 200) >= 400:
        add("broken", "bad", f"The page does not open (HTTP {p['status']}).", "Fix the link or add a 301 redirect.")
        return out
    if p.get("noindex"):
        add("noindex", "bad", "The page has noindex: Google will not show it.", "If the page should be shown, remove noindex from the meta robots tag.")
    t = p.get("title", "")
    if not t:
        add("title_missing", "bad", "There is no title.", "Give every page its own title: '<service> in <city> | <name>'.")
    elif len(t) < TITLE[0]:
        add("title_short", "warn", f"The title is short ({len(t)} characters).", "Add service + city + brand (30-60 characters).")
    elif len(t) > TITLE[1]:
        add("title_long", "warn", f"The title is long ({len(t)} characters): Google will cut it off.", "Keep it within 60 characters; put the important words first.")
    d = p.get("description", "")
    if not d:
        add("desc_missing", "warn", "There is no meta description.", "70-160 characters: what you get, where, and one call to action.")
    elif len(d) < DESC[0] or len(d) > DESC[1]:
        add("desc_len", "info", f"Description {len(d)} characters long.", "Keep it to 70-160 characters.")
    h1 = p.get("h1", [])
    if not h1:
        add("h1_missing", "warn", "There is no H1 heading.", "Put one H1 at the top of the page saying what the page is about.")
    elif len(h1) > 1:
        add("h1_many", "info", f"{len(h1)} H1 headings.", "Keep one main H1; make the rest H2.")
    if p.get("words", 0) < THIN_WORDS and not p.get("is_contact"):
        add("thin", "warn", f"The page has little text ({p.get('words', 0)} words).", "Add customer questions, prices, photos and an FAQ: real information about your work.")
    miss = p.get("img_no_alt", 0)
    if miss:
        add("img_alt", "info", f"{miss} photos have no alt text.", "Give every photo a short alt text saying what it shows.")
    if not p.get("viewport"):
        add("viewport", "bad", "No mobile viewport tag: the page will look tiny on a phone.", '<meta name="viewport" content="width=device-width, initial-scale=1">')
    if not p.get("https"):
        add("http", "bad", "The page is not on https.", "Install SSL and add a 301 redirect from http to https.")
    if p.get("canonical_other"):
        add("canonical", "info", f"The canonical points to a different URL: {p['canonical_other']}", "If it is intended, fine; if it is a mistake, use your own URL.")
    if not p.get("lang"):
        add("lang", "info", "There is no <html lang>.", 'Hindi page: lang="hi", Marathi: "mr", English: "en-IN".')
    if city and p.get("is_home") and city.lower() not in (t + " " + " ".join(h1) + " " + d).lower():
        add("city", "warn", f"The city '{city}' is not in the home page title / H1 / description.", "For local customers, put the city name in the title and H1.")
    if p.get("is_home") and not p.get("schema_local"):
        add("schema", "warn", "No LocalBusiness schema (JSON-LD).", "Add the JSON-LD Hoola made to the <head> of the home page.")
    if p.get("bytes", 0) > 3_000_000:
        add("heavy", "warn", f"The page is very heavy ({p['bytes'] // 1_000_000} MB).", "Use WebP photos at a smaller size.")
    return out


def site_issues(pages: list[dict], robots: str, sitemap_ok: bool) -> list[dict]:
    out = []
    if re.search(r"^\s*disallow:\s*/\s*$", robots or "", re.I | re.M) and re.search(r"user-agent:\s*\*", robots or "", re.I):
        out.append({"code": "robots_block", "level": "bad", "text": "robots.txt blocks the whole site from Google (Disallow: /).",
                    "fix": "Remove Disallow: / (block only folders such as admin / cart)."})
    if not sitemap_ok:
        out.append({"code": "sitemap", "level": "warn", "text": "sitemap.xml was not found.", "fix": "Create a sitemap and submit it in Search Console."})
    seen: dict[str, str] = {}
    for p in pages:
        t = (p.get("title") or "").strip().lower()
        if t and t in seen and p.get("status", 200) < 400:
            out.append({"code": "dup_title", "level": "warn", "text": f"Two pages have the same title: {p['url']} and {seen[t]}",
                        "fix": "Give every page its own title."})
        elif t:
            seen[t] = p["url"]
    return out


def link_issues(pages: list[dict], sitemap_urls: set[str] | None = None, home: str = "",
                redirects: dict[str, str] | None = None) -> list[dict]:
    """v0.317 site-wide link checks a full crawl makes possible (pages carry `out` links, `depth`, `redirected_from`):
    broken internal links (with the pages that link to them), links that go through a redirect, orphans (in the sitemap
    but no page links to them), pages more than 3 clicks deep, duplicate descriptions, mixed content."""
    out: list[dict] = []
    norm = lambda u: (u or "").rstrip("/")                                 # noqa: E731
    by_url = {norm(p["url"]): p for p in pages}
    broken = {norm(p["url"]) for p in pages if p.get("status", 200) >= 400}
    redirected = {norm(p["redirected_from"]): p["url"] for p in pages if p.get("redirected_from")}
    redirected.update({norm(a): b for a, b in (redirects or {}).items()})
    inlinks: dict[str, set[str]] = {}
    for p in pages:
        for l in p.get("out") or []:
            if norm(l) != norm(p["url"]):
                inlinks.setdefault(norm(l), set()).add(p["url"])
    for b in sorted(broken):
        srcs = sorted(inlinks.get(b, set()))
        if srcs:
            out.append({"code": "broken_link", "level": "bad", "url": srcs[0],
                        "text": f"Broken link from {len(srcs)} pages: {b} does not open.",
                        "fix": f"Change the link on {', '.join(srcs[:3])}, or add a 301 redirect for {b}."})
    for src, final in sorted(redirected.items()):
        srcs = sorted(inlinks.get(src, set()))
        if srcs:
            out.append({"code": "redirect_link", "level": "info", "url": srcs[0],
                        "text": f"An internal link goes through a redirect: {src} -> {final}",
                        "fix": f"Link straight to {final}."})
    for u in sorted(sitemap_urls or set()):
        k = norm(u)
        if k in by_url and k != norm(home) and not inlinks.get(k) and by_url[k].get("status", 200) < 400:
            out.append({"code": "orphan", "level": "warn", "url": u,
                        "text": "Orphan page: it is in the sitemap but no page on the site links to it.",
                        "fix": "Link to it from a related page or the menu so that people and Google can reach it."})
    for p in pages:
        d = p.get("depth")
        if d is not None and d > 3 and p.get("status", 200) < 400:
            out.append({"code": "deep", "level": "info", "url": p["url"], "text": f"The page is {d} clicks away from home.",
                        "fix": "Link to it from a page close to the home page (3 clicks or fewer)."})
        if p.get("mixed"):
            out.append({"code": "mixed", "level": "warn", "url": p["url"],
                        "text": f"An https page loads {p['mixed']} photos / scripts over http://.",
                        "fix": "Load them over https:// (browsers block them or show a warning)."})
    seen: dict[str, str] = {}
    for p in pages:
        dsc = (p.get("description") or "").strip().lower()
        if dsc and p.get("status", 200) < 400:
            if dsc in seen:
                out.append({"code": "dup_desc", "level": "info", "url": p["url"],
                            "text": f"Meta description is the same as {seen[dsc]}.", "fix": "Write a different description for every page."})
            else:
                seen[dsc] = p["url"]
    return out


def score(issues: list[dict]) -> int:
    pen = {"bad": 12, "warn": 4, "info": 1}
    return max(0, 100 - sum(pen.get(i["level"], 0) for i in issues))


def local_schema(b: dict) -> str:
    """LocalBusiness JSON-LD from her business details (only what she gave)."""
    d = {"@context": "https://schema.org", "@type": b.get("schema_type") or "LocalBusiness", "name": b.get("name", "")}
    if b.get("url"):
        d["url"] = b["url"]
    if b.get("phone"):
        d["telephone"] = b["phone"]
    addr = {k2: b[k] for k, k2 in (("street", "streetAddress"), ("city", "addressLocality"), ("state", "addressRegion"),
                                      ("pin", "postalCode")) if b.get(k)}
    if addr:
        d["address"] = {"@type": "PostalAddress", **addr, "addressCountry": "IN"}
    if b.get("lat") and b.get("lng"):
        d["geo"] = {"@type": "GeoCoordinates", "latitude": b["lat"], "longitude": b["lng"]}
    if b.get("hours"):
        d["openingHours"] = b["hours"]
    if b.get("price_range"):
        d["priceRange"] = b["price_range"]
    if b.get("same_as"):
        d["sameAs"] = b["same_as"]
    return '<script type="application/ld+json">\n' + json.dumps(d, ensure_ascii=False, indent=2) + "\n</script>"


def title_suggestion(service: str, city: str, brand: str) -> str:
    s = f"{service} in {city} | {brand}" if city else f"{service} | {brand}"
    return s if len(s) <= TITLE[1] else f"{service} {city}".strip()[:TITLE[1]]


GBP_CHECKLIST = ["Correct primary category (the closest one) + 2-4 secondary", "Name exactly as on the signboard (do not stuff keywords: Google suspends for it)",
                 "Address / service area and pin correct; the same NAP (name, address, phone) on the website", "Opening hours for every day + special hours for festivals",
                 "At least 10 real photos (shop outside / inside, work, team), new ones every month",
                 "Products / services with prices", "One post every week (offer, new work, event)",
                 "Reply to every review within 48 hours (use the name, say thanks, take problems offline)",
                 "A direct link for asking customers for reviews (ask everyone, not only the happy ones)", "Write the common questions in Q&A yourself and answer them"]

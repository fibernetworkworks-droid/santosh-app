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

NEVER = ("Backlink kharidna / link exchange scheme nahi (Google spam policy).",
         "Nakli review, review ke badle discount, ya sirf khush graahak se review maangna (review gating) nahi.",
         "Keyword stuffing, chhupa text, cloaking, doorway pages nahi.",
         "Hazaron AI pages ek saath chhaapna (scaled content abuse) nahi; har page asli kaam ka ho.",
         "Google search results scrape nahi: sirf Search Console / PageSpeed ke official API aur aapki apni website.",
         "Website / Google profile par badlav sirf aapki haan se; Hoola khud publish nahi karta.")


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
                "do": f"'{row['query']}' par position {pos:.1f}: page mein yeh shabd heading / pehle paragraph mein, FAQ, aur andar ke links se mazboot karein."}
    if pos < STRIKING[0] and ctr < exp * 0.6:
        gain = round(imp * (exp - ctr))
        return {"kind": "low_ctr", "gain": max(gain, 0),
                "do": f"'{row['query']}' top {pos:.0f} mein hai par click kam ({ctr * 100:.1f}%): title aur description behtar likhein."}
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
            out.append({"query": q, "pages": sorted(pages), "do": "Ek hi shabd par do page lad rahe hain: ek ko mukhya banaiye, doosre se link / merge kijiye."})
    return out


def page_issues(p: dict, city: str = "") -> list[dict]:
    """On-page checks for one crawled page dict (see service._parse). Each issue: {code, level bad|warn|info, text, fix}."""
    out = []

    def add(code, level, text, fix):
        out.append({"code": code, "level": level, "text": text, "fix": fix})

    if p.get("status", 200) >= 400:
        add("broken", "bad", f"Page khulta nahi (HTTP {p['status']}).", "Link theek karein ya 301 redirect lagaiye.")
        return out
    if p.get("noindex"):
        add("noindex", "bad", "Page par noindex laga hai: Google ise nahi dikhayega.", "Agar page dikhna chahiye to meta robots se noindex hataiye.")
    t = p.get("title", "")
    if not t:
        add("title_missing", "bad", "Title nahi hai.", "Har page ka alag title: '<kaam> in <shehar> | <naam>'.")
    elif len(t) < TITLE[0]:
        add("title_short", "warn", f"Title chhota hai ({len(t)} akshar).", "Kaam + shehar + brand jodiye (30-60 akshar).")
    elif len(t) > TITLE[1]:
        add("title_long", "warn", f"Title lamba hai ({len(t)} akshar): Google kaat dega.", "60 akshar tak rakhiye; zaroori shabd pehle.")
    d = p.get("description", "")
    if not d:
        add("desc_missing", "warn", "Meta description nahi.", "70-160 akshar: kya milta hai, kahan, aur ek call to action.")
    elif len(d) < DESC[0] or len(d) > DESC[1]:
        add("desc_len", "info", f"Description {len(d)} akshar ka hai.", "70-160 akshar rakhiye.")
    h1 = p.get("h1", [])
    if not h1:
        add("h1_missing", "warn", "H1 heading nahi.", "Page ke upar ek H1: page kis baare mein hai.")
    elif len(h1) > 1:
        add("h1_many", "info", f"{len(h1)} H1 headings.", "Ek mukhya H1 rakhiye, baaki H2.")
    if p.get("words", 0) < THIN_WORDS and not p.get("is_contact"):
        add("thin", "warn", f"Page par kam likha hai ({p.get('words', 0)} shabd).", "Graahak ke sawaal, daam, photo, FAQ jodiye: asli kaam ki jaankari.")
    miss = p.get("img_no_alt", 0)
    if miss:
        add("img_alt", "info", f"{miss} photo bina alt text.", "Har photo ka chhota alt: kya dikh raha hai.")
    if not p.get("viewport"):
        add("viewport", "bad", "Mobile viewport tag nahi: phone par page chhota dikhega.", '<meta name="viewport" content="width=device-width, initial-scale=1">')
    if not p.get("https"):
        add("http", "bad", "Page https par nahi.", "SSL lagaiye aur http se https 301 redirect.")
    if p.get("canonical_other"):
        add("canonical", "info", f"Canonical doosre URL ki taraf: {p['canonical_other']}", "Sahi ho to theek; galti se ho to apna URL rakhiye.")
    if not p.get("lang"):
        add("lang", "info", "<html lang> nahi.", 'Hindi page: lang="hi", Marathi: "mr", English: "en-IN".')
    if city and p.get("is_home") and city.lower() not in (t + " " + " ".join(h1) + " " + d).lower():
        add("city", "warn", f"Home page ke title / H1 / description mein shehar '{city}' nahi.", "Local graahak ke liye shehar ka naam title aur H1 mein.")
    if p.get("is_home") and not p.get("schema_local"):
        add("schema", "warn", "LocalBusiness schema (JSON-LD) nahi.", "Hoola ka banaya JSON-LD home page ke <head> mein lagaiye.")
    if p.get("bytes", 0) > 3_000_000:
        add("heavy", "warn", f"Page bahut bhaari ({p['bytes'] // 1_000_000} MB).", "Photo WebP mein, chhoti size.")
    return out


def site_issues(pages: list[dict], robots: str, sitemap_ok: bool) -> list[dict]:
    out = []
    if re.search(r"^\s*disallow:\s*/\s*$", robots or "", re.I | re.M) and re.search(r"user-agent:\s*\*", robots or "", re.I):
        out.append({"code": "robots_block", "level": "bad", "text": "robots.txt poori site ko Google se rok raha hai (Disallow: /).",
                    "fix": "Disallow: / hataiye (sirf admin / cart jaise folder rokiye)."})
    if not sitemap_ok:
        out.append({"code": "sitemap", "level": "warn", "text": "sitemap.xml nahi mila.", "fix": "Sitemap banaiye aur Search Console mein jama kijiye."})
    seen: dict[str, str] = {}
    for p in pages:
        t = (p.get("title") or "").strip().lower()
        if t and t in seen and p.get("status", 200) < 400:
            out.append({"code": "dup_title", "level": "warn", "text": f"Do page ka ek hi title: {p['url']} aur {seen[t]}",
                        "fix": "Har page ka alag title."})
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
                        "text": f"{len(srcs)} page se tuta link: {b} khulta nahi.",
                        "fix": f"{', '.join(srcs[:3])} par link badliye, ya {b} ka 301 redirect lagaiye."})
    for src, final in sorted(redirected.items()):
        srcs = sorted(inlinks.get(src, set()))
        if srcs:
            out.append({"code": "redirect_link", "level": "info", "url": srcs[0],
                        "text": f"Andar ka link redirect se hokar jaata hai: {src} -> {final}",
                        "fix": f"Link seedha {final} par rakhiye."})
    for u in sorted(sitemap_urls or set()):
        k = norm(u)
        if k in by_url and k != norm(home) and not inlinks.get(k) and by_url[k].get("status", 200) < 400:
            out.append({"code": "orphan", "level": "warn", "url": u,
                        "text": "Akela page: sitemap mein hai par site ka koi page iska link nahi deta.",
                        "fix": "Kisi milte-julte page ya menu se link dijiye, taaki log aur Google pahunch sakein."})
    for p in pages:
        d = p.get("depth")
        if d is not None and d > 3 and p.get("status", 200) < 400:
            out.append({"code": "deep", "level": "info", "url": p["url"], "text": f"Page home se {d} click door hai.",
                        "fix": "Home ke paas wale page se link dijiye (3 click ya kam)."})
        if p.get("mixed"):
            out.append({"code": "mixed", "level": "warn", "url": p["url"],
                        "text": f"https page par {p['mixed']} photo / script http:// se aa rahe hain.",
                        "fix": "Inhe https:// se lagaiye (browser inhe rok dete hain ya warning dete hain)."})
    seen: dict[str, str] = {}
    for p in pages:
        dsc = (p.get("description") or "").strip().lower()
        if dsc and p.get("status", 200) < 400:
            if dsc in seen:
                out.append({"code": "dup_desc", "level": "info", "url": p["url"],
                            "text": f"Meta description {seen[dsc]} jaisi hi hai.", "fix": "Har page ki alag description likhiye."})
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


GBP_CHECKLIST = ["Sahi primary category (sabse kareeb wali) + 2-4 secondary", "Naam bilkul board jaisa (keyword mat bharo: Google suspend karta hai)",
                 "Address / service area aur pin sahi; website par wahi NAP (naam, address, phone)", "Har din ke ghante + tyohaar ke special hours",
                 "Kam se kam 10 asli photo (dukaan bahar / andar, kaam, team), har mahine nayi",
                 "Products / services daam ke saath", "Har hafte ek post (offer, naya kaam, event)",
                 "Har review ka jawab 48 ghante mein (naam lekar, shukriya, dikkat ho to offline baat)",
                 "Graahak se review maangne ka seedha link (sabse maangiye, sirf khush walon se nahi)", "Q&A mein aam sawaal khud likhiye aur jawab dijiye"]

"""v0.622 KOI PATA NA KHOYE - her own old site moves to Hoola without losing a single address (the source-URL -> route map
idea of JCodesMore/ai-website-cloner-template, MIT, re-written in Hoola's own Python for the ONE case Hoola allows: HER OWN
site, ownership already proved by `inspire.from_site`; docs/research/website_cloner/).

When she points her domain at the new Hoola site, every old address (/about-us.html, /services/catering, /contact.php)
used to answer "not found": Google's rankings and every link to those pages were lost. Now:

1. `inspire.from_site` keeps EVERY old address it can see (her sitemap.xml + every same-site link on the pages it read),
   `inspire.use` saves them beside the site (`moves_src.json`);
2. `propose` matches each old address to a page of the NEW site by its words (the old slug, the old page title) - an exact
   slug first, else the best word overlap, else the home page FLAGGED as a guess - and returns the list with a hash;
3. nothing is served until HER tap (`apply` with that hash; she may untick a row or point it elsewhere): then
   `_redirects.json` goes into the live folder of every address of the site, and every later publish carries it;
4. `lookup` answers a missing page with a 301 to its new home (hosting.serve; nginx hands only its own 404s to it).

Also here: `compare` (her old page next to the new one at the SAME width, the differences listed) and `sniff` (an imported
photo is checked by its BYTES - a .png address that returns AVIF, or HTML, is named, never trusted by its name)."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import build as B

log = logging.getLogger("santosh.site")

PATHS_MAX = 500                  # old addresses kept from one import
SITEMAPS_MAX = 5                 # a sitemap index is followed this far
REDIRECTS_FILE = "_redirects.json"
STOP = {"the", "and", "for", "our", "your", "with", "page", "index", "html", "htm", "php", "aspx", "asp", "jsp", "home",
        "www", "com", "in", "of", "a", "to", "us", "me", "ka", "ki", "ke", "hamare", "hamari"}
SYN = {"about": {"about", "story", "who", "parichay", "company", "team"},
       "contact": {"contact", "reach", "enquiry", "inquiry", "sampark", "location", "find", "visit", "address"},
       "services": {"services", "service", "what", "offer", "offerings", "solutions", "seva"},
       "products": {"products", "product", "shop", "store", "catalogue", "catalog", "items"},
       "gallery": {"gallery", "photos", "portfolio", "work", "projects"},
       "menu": {"menu", "food", "dishes"},
       "blog": {"blog", "news", "articles", "posts", "updates"},
       "faq": {"faq", "faqs", "questions", "help"},
       "pricing": {"pricing", "prices", "price", "rates", "plans", "fees"},
       "booking": {"booking", "book", "appointment", "appointments", "reserve"},
       "testimonials": {"testimonials", "reviews", "clients"},
       "privacy": {"privacy", "policy"}, "terms": {"terms", "conditions"}}


class MovedError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- the old addresses
def norm_path(p: str) -> str:
    """One shape for an old address: path only, decoded, no query / fragment, no trailing slash (except '/')."""
    u = urlparse(p if "//" in (p or "") else "http://x" + ("" if (p or "").startswith("/") else "/") + (p or ""))
    path = unquote(u.path or "/")
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")
    return path[:300] or "/"


def sitemap_paths(xml: str, host_ok) -> tuple[list[str], list[str]]:
    """(page addresses, nested sitemap URLs) from a sitemap / sitemap index - only addresses of her own site."""
    locs = [unescape_xml(x.strip()) for x in re.findall(r"(?is)<loc>\s*(.*?)\s*</loc>", xml or "")]
    pages, maps = [], []
    for loc in locs:
        u = urlparse(loc)
        if not host_ok((u.hostname or "").lower()):
            continue
        if re.search(r"\.xml(\.gz)?$", u.path or "", re.I):
            maps.append(loc)
        else:
            pages.append(norm_path(u.path or "/"))
    return pages, maps


def unescape_xml(s: str) -> str:
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def keep_paths(found: list[str], titles: dict[str, str]) -> list[dict[str, str]]:
    """The import's list: unique, real page addresses (no files / feeds / admin), titles where a page was read."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for p in found:
        n = norm_path(p)
        if n in seen or n == "/":
            continue
        if re.search(r"\.(pdf|jpe?g|png|webp|gif|svg|zip|mp4|css|js|xml|txt|ico|woff2?)$", n, re.I):
            continue
        if re.search(r"^/(wp-admin|wp-json|wp-content|wp-includes|cgi-bin|feed|xmlrpc|admin|login|cart|checkout)\b", n, re.I):
            continue
        seen.add(n)
        out.append({"path": n, "title": titles.get(n, "")[:140]})
        if len(out) >= PATHS_MAX:
            break
    return out


def save_source(tenant: str, site_id: str, host: str, paths: list[dict[str, str]]) -> None:
    (B.site_dir(tenant, site_id) / "moves_src.json").write_text(
        json.dumps({"host": host, "paths": paths[:PATHS_MAX], "at": time.time()}))


def _load(tenant: str, site_id: str, name: str) -> dict[str, Any]:
    try:
        return json.loads((B.site_dir(tenant, site_id) / name).read_text())
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- matching an old address to a new page
def words(text: str) -> set[str]:
    toks = {w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) >= 2 and w not in STOP and not w.isdigit()}
    out = set()
    for t in toks:                                         # 'about-us' and 'our-story' are both 'about'
        out.add(next(("§" + k for k, syn in SYN.items() if t in syn), t))
    return out


def _last(path: str) -> str:
    seg = [s for s in path.strip("/").split("/") if s]
    return re.sub(r"\.(html?|php|aspx?|jsp)$", "", seg[-1].lower()) if seg else ""


def new_pages(plan: dict[str, Any]) -> list[dict[str, str]]:
    return [{"slug": p["slug"], "title": str(p.get("title") or ""),
             "path": "/" if p["slug"] == "home" else f"/{p['slug']}/"} for p in plan.get("pages") or [] if p.get("slug")]


def match(old: dict[str, str], pages: list[dict[str, str]]) -> dict[str, Any]:
    """The best new page for one old address: exact slug > word overlap (>= 0.34) > home, flagged as a guess."""
    path = old["path"]
    last = _last(path)
    for p in pages:
        if p["slug"] != "home" and (p["slug"] == path.strip("/").lower() or p["slug"].split("/")[-1] == last):
            return {"new": p["path"], "page": p["slug"], "how": "same name", "score": 1.0, "guess": False}
    ow = words(path.replace("/", " ") + " " + old.get("title", ""))
    best, score = None, 0.0
    for p in pages:
        if p["slug"] == "home":
            continue
        nw = words(p["slug"].replace("/", " ") + " " + p["title"])
        if not ow or not nw:
            continue
        s = len(ow & nw) / len(ow | nw)
        if s > score:
            best, score = p, s
    if best and score >= 0.34:
        return {"new": best["path"], "page": best["slug"], "how": "matching words", "score": round(score, 2), "guess": False}
    return {"new": "/", "page": "home", "how": "no matching page - home page", "score": 0.0, "guess": True}


def _hash(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps([[r["old"], r["new"]] for r in rows]).encode()).hexdigest()[:16]


def propose(tenant: str, site_ref: str) -> dict[str, Any]:
    """The list she taps: every old address -> its new page. Nothing is served until `apply`."""
    from ..db import session
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, site_ref)
        site_id, plan = r.id, S._j(r.plan, {})
    src = _load(tenant, site_id, "moves_src.json")
    if not src.get("paths"):
        raise MovedError("There are no old-site addresses for this website. First take the design from your old site "
                         "('build from my old site' + address).", 404)
    pages = new_pages(plan)
    have = {p["path"].rstrip("/") or "/" for p in pages}
    rows = []
    for o in src["paths"]:
        if o["path"] in have:                              # the same address exists on the new site: nothing to move
            continue
        m = match(o, pages)
        rows.append({"old": o["path"], "title": o.get("title", ""), **m})
    h = _hash(rows)
    (B.site_dir(tenant, site_id) / "moves_proposed.json").write_text(json.dumps({"rows": rows, "hash": h, "at": time.time()}))
    guesses = sum(1 for x in rows if x["guess"])
    say = (f"Your old site ({src.get('host')}) has {len(rows)} old addresses. The plan to send each address to a new page "
           f"is ready" + (f"; {guesses} had no matching page and will go to the home page (please look)" if guesses
                                  else "") + ". It is applied only after your 'yes' (301 redirect: it keeps the Google ranking and the old "
           "links).")
    return {"site": site_id, "from_host": src.get("host"), "rows": rows, "hash": h, "guesses": guesses,
            "approved": bool(_load(tenant, site_id, "moves.json").get("rows")), "say": say}


def apply(tenant: str, site_ref: str, hash_: str, drop: list[str] | None = None,
          change: dict[str, str] | None = None) -> dict[str, Any]:
    """HER tap: the list she saw (bound by its hash) becomes live 301s; unticked rows stay out, her own targets win."""
    from ..db import session
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, site_ref)
        site_id, plan = r.id, S._j(r.plan, {})
    prop = _load(tenant, site_id, "moves_proposed.json")
    if not prop.get("rows") or prop.get("hash") != hash_:
        raise MovedError("This list has changed; look again and then approve.", 409)
    valid = {p["path"] for p in new_pages(plan)}
    drop_set = {norm_path(x) for x in (drop or [])}
    rows = []
    for x in prop["rows"]:
        if x["old"] in drop_set:
            continue
        tgt = (change or {}).get(x["old"]) or x["new"]
        if tgt not in valid:
            raise MovedError(f"'{tgt}' is not a page of the new site.")
        rows.append({"old": x["old"], "new": tgt})
    (B.site_dir(tenant, site_id) / "moves.json").write_text(json.dumps({"rows": rows, "approved_at": time.time()}))
    live = publish_live(tenant, site_id)
    return {"ok": True, "site": site_id, "redirects": len(rows), "live_addresses": live,
            "say": f"{len(rows)} old addresses are connected to the new pages (301)."
                   + (f" {live} are working on the live address from now." if live else " They start working as soon as the website goes live.")}


def file_for(tenant: str, site_id: str) -> dict[str, str]:
    return {x["old"]: x["new"] for x in _load(tenant, site_id, "moves.json").get("rows") or []}


def write_into(folder: Path, tenant: str, site_id: str) -> bool:
    """Called by every publish: the approved map rides in the live folder (never served itself)."""
    m = file_for(tenant, site_id)
    if not m:
        return False
    (folder / REDIRECTS_FILE).write_text(json.dumps(m))
    return True


def publish_live(tenant: str, site_id: str) -> int:
    """Put the approved map into the folder of every live address of this site at once (no rebuild needed)."""
    from sqlalchemy import select

    from ..db import session
    from . import hosting as H
    from .hosting_models import SiteHost
    n = 0
    try:
        with session() as s:
            hosts = [h.hostname for h in s.scalars(select(SiteHost).where(SiteHost.site_id == site_id,
                                                                           SiteHost.live_version > 0)).all()]
    except Exception:
        log.debug("moves: no hosts", exc_info=True)
        return 0
    seen: set[Path] = set()
    for h in hosts:
        p = (H.hosted_root() / h)
        try:
            real = p.resolve()
        except OSError:
            continue
        if real.is_dir() and real not in seen:
            seen.add(real)
            write_into(real, tenant, site_id)
            n += 1
    return n


_CACHE: dict[str, tuple[float, dict[str, str]]] = {}


def lookup(root: Path, path: str) -> str | None:
    """hosting.serve: the new address for an old one that is not a page any more (or None)."""
    f = root / REDIRECTS_FILE
    try:
        mt = f.stat().st_mtime
    except OSError:
        return None
    key = str(f)
    got = _CACHE.get(key)
    if not got or got[0] != mt:
        try:
            got = (mt, {norm_path(k).lower(): v for k, v in json.loads(f.read_text()).items()})
        except (OSError, ValueError):
            return None
        _CACHE[key] = got
    return got[1].get(norm_path(path).lower())


# ---------------------------------------------------------------- 4. a photo checked by its bytes
MAGIC = (("jpeg", lambda b: b[:3] == b"\xff\xd8\xff"), ("png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
         ("gif", lambda b: b[:6] in (b"GIF87a", b"GIF89a")), ("webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
         ("avif", lambda b: b[4:8] == b"ftyp" and b[8:12] in (b"avif", b"avis")),
         ("heic", lambda b: b[4:8] == b"ftyp" and b[8:12] in (b"heic", b"heix", b"mif1")),
         ("svg", lambda b: b.lstrip()[:5].lower() in (b"<?xml", b"<svg ") and b"<svg" in b[:2000].lower()),
         ("html", lambda b: b.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html"))))
EXT = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp", "avif": "avif", "svg": "svg",
       "heic": "heic"}


def sniff(data: bytes, src: str = "") -> dict[str, Any]:
    """What the bytes REALLY are: {ok, type, named, w, h, bytes, why}. Only a real raster photo Hoola can open is ok."""
    real = next((k for k, test in MAGIC if test(data or b"")), "")
    ext = (re.search(r"\.([a-z0-9]{2,5})$", urlparse(src).path.lower() or "") or [None, ""])[1]
    named = EXT.get(ext, "")
    out: dict[str, Any] = {"ok": False, "type": real or "unknown", "named": named, "bytes": len(data or b""), "w": 0, "h": 0,
                           "why": ""}
    if real in ("html", "svg", ""):
        out["why"] = {"html": "address returned a web page, not a photo", "svg": "a drawing (SVG), not a photo",
                      "": "not a photo file Hoola knows"}[real]
        return out
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = Image.open(io.BytesIO(data))
        out["w"], out["h"] = im.size
    except Exception:
        out["why"] = f"{real.upper()} file that could not be opened (broken or not supported here)"
        return out
    out["ok"] = True
    if named and named != real:
        out["why"] = f"name says {named.upper()}, the file is really {real.upper()}"
    return out


# ---------------------------------------------------------------- 3. her old page next to the new one
def _facts(html: str) -> dict[str, Any]:
    from .inspire import read_page
    r = read_page(html)
    return {"heads": r["heads"], "phones": r["phones"], "emails": r["emails"], "whatsapp": r["whatsapp"],
            "images": len(re.findall(r"(?i)<img\b", html)), "forms": len(re.findall(r"(?i)<form\b", html)),
            "words": len(re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", html).split())}


def differences(old_html: str, new_html: str) -> list[str]:
    """What a person would notice, in her words - never a pass / fail."""
    o, n = _facts(old_html), _facts(new_html)
    out: list[str] = []
    nh = " ".join(n["heads"]).lower()
    gone = [h for h in o["heads"] if h and not (words(h) & words(nh))][:8]
    if gone:
        out.append("headings on the old page not on the new one: " + "; ".join(gone))
    for k, label in (("phones", "phone"), ("emails", "email"), ("whatsapp", "WhatsApp")):
        miss = [x for x in o[k] if x not in n[k]]
        if miss:
            out.append(f"{label} on the old page missing on the new one: {', '.join(miss)}")
    if o["forms"] > n["forms"]:
        out.append(f"old page had {o['forms']} form(s), the new one has {n['forms']}")
    if o["images"] and n["images"] < o["images"] // 2:
        out.append(f"fewer pictures: {o['images']} before, {n['images']} now")
    if o["words"] > 120 and n["words"] < o["words"] * 0.5:
        out.append(f"much shorter: about {o['words']} words before, {n['words']} now")
    return out


def pixel_change(a: bytes, b: bytes) -> float | None:
    """Share of the page that looks different (0 = same, 1 = all different), at the same width, top 2,000 px."""
    try:
        from PIL import Image, ImageChops
        ia, ib = Image.open(io.BytesIO(a)).convert("L"), Image.open(io.BytesIO(b)).convert("L")
        w = min(ia.width, ib.width)
        h = min(ia.height, ib.height, 2000)
        ia, ib = ia.crop((0, 0, w, h)).resize((w // 4 or 1, h // 4 or 1)), ib.crop((0, 0, w, h)).resize((w // 4 or 1, h // 4 or 1))
        d = ImageChops.difference(ia, ib).point(lambda v: 255 if v > 40 else 0)
        hist = d.histogram()
        return round(hist[255] / max(1, sum(hist)), 3)
    except Exception:
        return None


def _shots(old_url: str, out: Path, slug: str, widths: tuple[int, ...]) -> dict[str, Any]:
    """Old page (public, her own) and new page (local files) at the same widths, same browser, same scroll (top)."""
    from playwright.sync_api import sync_playwright

    from .. import web as WB
    from . import checks as C
    WB._check_url(old_url)
    res: dict[str, Any] = {}
    with sync_playwright() as p:
        b = C._launch(p)
        try:
            for vw in widths:
                shots = []
                for which in ("old", "new"):
                    ctx = b.new_context(viewport={"width": vw, "height": 900}, device_scale_factor=1)
                    page = ctx.new_page()
                    if which == "old":
                        page.goto(old_url, wait_until="load", timeout=45000)
                    else:
                        page.route("**/*", C._serve(out, {}))
                        page.goto(C.ORIGIN + "/" + ("" if slug == "home" else slug + "/"), wait_until="load", timeout=30000)
                    page.wait_for_timeout(1200)
                    shots.append(page.screenshot(type="png", full_page=True))
                    ctx.close()
                res[str(vw)] = shots
        finally:
            b.close()
    return res


def compare(tenant: str, site_ref: str, old_path: str = "/", slug: str = "", widths: tuple[int, ...] = (390, 1280),
            fetch=None, shooter=None) -> dict[str, Any]:
    """Her old page and the matching new page side by side. Only an address of HER old site (the one she proved)."""
    import httpx

    from ..db import session
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, site_ref)
        site_id, version = r.id, r.version
    src = _load(tenant, site_id, "moves_src.json")
    host = src.get("host") or ""
    if not host:
        raise MovedError("There is no old-site address; first take the design from your old site.", 404)
    old_path = norm_path(old_path or "/")
    if not slug:
        slug = "home" if old_path == "/" else (file_for(tenant, site_id).get(old_path) or "/").strip("/") or "home"
    out = B.out_dir(tenant, site_id, version)
    nf = out / B.page_path(slug)
    if not nf.is_file():
        raise MovedError(f"The new site has no '{slug}' page (version {version}).", 404)
    old_url = f"https://{host}{old_path}"
    if fetch is None:
        def fetch(url: str) -> str:
            from .inspire import _TRANSPORT, _get
            with httpx.Client(timeout=15, follow_redirects=True, transport=_TRANSPORT,
                              headers={"User-Agent": "HoolaDesign/1.0 (her own site, compared)"}) as c:
                got = _get(c, url, 2_500_000)
            return got[0].decode("utf-8", "replace") if got else ""
    old_html = fetch(old_url)
    if not old_html:
        raise MovedError(f"{old_url} did not open (if the site has been shut down, no comparison is possible).", 502)
    diffs = differences(old_html, nf.read_text(encoding="utf-8", errors="ignore"))
    d = B.site_dir(tenant, site_id) / "compare"
    d.mkdir(exist_ok=True)
    key = re.sub(r"[^\w-]", "_", old_path.strip("/") or "home")[:60]
    shots_note, widths_out = "", []
    try:
        shots = (shooter or _shots)(old_url, out, slug, widths)
        for w, (a, b) in shots.items():
            (d / f"{key}-{w}-old.png").write_bytes(a)
            (d / f"{key}-{w}-new.png").write_bytes(b)
            widths_out.append({"width": int(w), "looks_different": pixel_change(a, b),
                               "old": f"{key}-{w}-old.png", "new": f"{key}-{w}-new.png"})
    except Exception as e:                                  # noqa: BLE001 - no browser = words-only comparison, said
        shots_note = "screenshots not taken here (no browser): " + str(e)[:120]
        log.info("moves compare shots: %s", e)
    rep = {"old": old_url, "new_page": slug, "version": version, "differences": diffs, "widths": widths_out,
           "note": shots_note, "at": time.time()}
    (d / f"{key}.json").write_text(json.dumps(rep))
    say = (f"Looked at the old {old_path} and the new '{slug}' page side by side" + (f" ({', '.join(str(w['width']) for w in widths_out)} px)"
                                                                          if widths_out else "") + ". "
           + ("Differences: " + "; ".join(diffs[:4]) + "." if diffs else "The essentials (headings, phone, email, form) are in both.")
           + (" This is a redesign, not an exact copy - the colours and font are yours, the structure is Hoola's." ))
    return {**rep, "say": say}


def compare_file(tenant: str, site_ref: str, name: str) -> bytes:
    from ..db import session
    from . import service as S
    if not re.fullmatch(r"[\w-]{1,80}\.(png|json)", name or ""):
        raise MovedError("The file name is wrong.", 404)
    with session() as s:
        site_id = S._find(s, tenant, site_ref).id
    f = B.site_dir(tenant, site_id) / "compare" / name
    if not f.is_file():
        raise MovedError("That comparison was not found.", 404)
    return f.read_bytes()

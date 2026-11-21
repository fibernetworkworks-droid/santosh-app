"""v0.999.77 D8 THE PARITY CHECKLIST (docs/WEB_DESIGN_ENGINE_PLAN.md P10 / phase D8): before the React website engine
can be the default for new sites (D10), every feature her HTML websites have must work on it. This list is that
checklist - and each line's state is READ FROM THE CODE (a block that really sends, an island that really orders), so it
cannot say "done" for something that is not wired.

  works    the feature works on a React website the same way (same addresses, same data, her taps unchanged)
  partial  it works, and the list says what is still missing
  not yet  not built on the React engine (the HTML engine still does it)
  blocked  cannot work the way React website pages are served today, and says why

`python -m app.appengine parity` prints it; D8's done-line is every line "works"."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
BLOCKS = HERE / "template" / "src" / "components" / "blocks"


def _has(rel: str, *needles: str) -> bool:
    f = HERE / rel
    try:
        t = f.read_text("utf-8")
    except OSError:
        return False
    return all(n in t for n in needles)


def _block(name: str) -> bool:
    return (BLOCKS / f"{name}.tsx").is_file()


Check = Callable[[], tuple[str, list[str]]]


def _forms() -> tuple[str, list[str]]:
    ok = _has("template/src/components/blocks/contact-block.tsx", "endpoint", "fetch(endpoint") and \
        _has("writer.py", '"endpoint": ctx.forms')
    return ("works", []) if ok else ("not yet", ["the contact form does not send"])


def _booking() -> tuple[str, list[str]]:
    ok = _has("template/src/components/blocks/booking-slots.tsx", 'endpoint + "/slots"', 'endpoint + "/book"') and \
        _has("writer.py", '"endpoint": ctx.forms}')
    return ("works", []) if ok else ("not yet", ["the booking block shows sample times"])


def _shop() -> tuple[str, list[str]]:
    if not (_has("template/src/islands/ShopCart.tsx", '"/order"', "/products") and
            _has("template/src/components/blocks/products-grid.tsx", "hoola-cart") and _has("writer.py", "ShopCart")):
        return "not yet", ["products link to the contact page; no cart"]
    missing = []
    if not _has("template/src/islands/ShopCart.tsx", "/coupon"):
        missing.append("coupons")
    if not _has("template/src/islands/ShopCart.tsx", "/review"):
        missing.append("reviews after delivery")
    if not _has("template/src/islands/ShopCart.tsx", "/invoice"):
        missing.append("the GST bill / credit note link")
    if not _has("template/src/islands/ShopCart.tsx", "/track"):
        missing.append("courier tracking")
    if not (_has("template/src/islands/ShopCart.tsx", "keepGet") and _own_address()):
        missing.append("the cart lives while the page is open (sealed pages keep no browser storage)")
    if not missing:
        return "works", []
    if not (_has("writer.py", "ctx.photo_by[x[\"photo\"]]") and _has("../site/prototype.py", "def sync_photos")):
        missing.append("product photos (her shop photos are not on the React site yet)")
    return "partial", missing


def _payments() -> tuple[str, list[str]]:
    ok = _has("template/src/islands/ShopCart.tsx", "online?.url", "/paid", "order.pay.qr")
    return ("works", []) if ok else ("not yet", ["no payment step"])


def _blog() -> tuple[str, list[str]]:
    """v0.999.77 wave 2: a page per published post + the list, written again when a post changes (every change -
    Studio, Kalam's card, the CMS team, a scheduled post - goes through service._blog_rebuild)."""
    ok = _has("writer.py", "def post_file", "def md_parts", "BlogPosting") and _block("article") and \
        _has("../site/prototype.py", "BL.live_posts") and _has("../site/service.py", "RX.refresh(r.tenant_id, r.id)")
    if ok and _has("writer.py", '"cover": ctx.photo_by.get(') and _has("../site/prototype.py", "def sync_photos"):
        return "works", []
    if ok:
        return "partial", ["a post's cover photo (her photos are not on the React site yet)"]
    return "not yet", ["her blog posts and their pages (the HTML engine builds /blog/)", "the CMS team's publishing"]


def _languages() -> tuple[str, list[str]]:
    """v0.999.77 wave 2: pages under /<code>/, the switch, <html lang> + hreflang, translations checked by code."""
    ok = _has("writer.py", "def alternates", "def for_lang", "hrefLang") and _has("langs.py", "def translate", "def kept") \
        and _has("template/hoola.prerender.mjs", 'rel="alternate" hreflang') and _has("../site/service.py", "RX.translate")
    if not ok:
        return "not yet", ["second-language pages + switch + hreflang"]
    return "partial", ["sections written specially for her site (custom code) stay in the first language"]


def _portals() -> tuple[str, list[str]]:
    miss = ["sign-in on a website page (refused: the sealed page keeps no sign-in)", "her real lists in the app screens"]
    return ("partial", miss) if _has("writer.py", "AppPage") else ("not yet", miss)


def _catalogue() -> tuple[str, list[str]]:
    """v0.999.82 wave 4: her lists and items (the same addresses), 48 a page, a pre-rendered page per item."""
    ok = _has("writer.py", "def catalog_files", "!it || it.ni") and _block("catalog") and \
        _has("../site/prototype.py", "def catalog_link") and _has("template/hoola.prerender.mjs", "MAX = 6000")
    if not ok:
        return "not yet", ["a page per item from her sheet (5,000+ pages)"]
    return "partial", ["the filter bar (search, her filter columns, price range, sort) of her HTML catalogue",
                       "Add to cart on a catalogue item (her shop's products have it)"]


def _own_address() -> bool:
    """v0.999.82 wave 5: a React website goes live unsealed on its own address (her domain / its free address)."""
    return _has("../site/rxhost.py", "def publish", "def allowed") and _has("../site/hosting.py", "RH.publish(r, host, tmp)") \
        and _has("../main.py", "_rx_visitor(hm[host]")


def _live_chat() -> tuple[str, list[str]]:
    if _own_address():
        return "not yet", ["visitor chat + clinic queue on her own address (the visitor's token can be kept there now; "
                           "not built for React websites yet)"]
    return "not yet", ["visitor chat + clinic queue (needs the visitor's sign-in token, which a sealed page cannot keep)"]


def _push() -> tuple[str, list[str]]:
    if _own_address():
        return "not yet", ["browser push from her own address (a service worker can be registered there now; not built "
                           "for React websites yet)"]
    return "blocked", ["browser push needs a service worker, which a sealed (sandboxed) page cannot register"]


def _domains() -> tuple[str, list[str]]:
    return ("works", []) if _own_address() else ("not yet", ["her own domain for a React website"])


def _sections_for(kinds: list[str], limits: list[str] | None = None) -> Check:
    """v0.999.82 wave 3: a kit block for each, filled from her prototype by the writer (a section of hers that no block
    fits is still written specially); `limits` = what the block cannot do on a sealed page, said."""
    def run() -> tuple[str, list[str]]:
        have = [k for k in kinds if _block(k) and _has("writer.py", f'"{k.replace("-", "_")}": m_{k.replace("-", "_")}')]
        if len(have) == len(kinds):
            return ("partial", list(limits)) if limits else ("works", [])
        return ("partial" if have else "not yet"), [f"no block yet: {k}" for k in kinds if k not in have]
    return run


def _ai() -> tuple[str, list[str]]:
    return "not yet", ["a chat / writer / picture maker inside her site, on Hoola's backend and her credits"]


CHECKLIST: list[tuple[str, str, Check]] = [
    ("forms", "Contact and enquiry forms", _forms),
    ("booking", "Booking: real free times + a request she confirms", _booking),
    ("shop", "Shop: products, cart, order, stock", _shop),
    ("payments", "Payments: her UPI, her gateway", _payments),
    ("blog", "Blog + CMS", _blog),
    ("languages", "Second languages", _languages),
    ("portals", "Member portals / app pages / sign-in", _portals),
    ("catalogue", "Big catalogue (5,000+ pages)", _catalogue),
    ("live", "Live visitor chat + clinic queue", _live_chat),
    ("push", "Browser push", _push),
    ("domains", "Her own domain", _domains),
    ("personal", "Personal / portfolio sections", _sections_for(["about-me", "resume", "case-studies"])),
    ("event", "Event / wedding sections", _sections_for(["schedule", "rsvp", "venue"])),
    ("community", "Community sections", _sections_for(["members", "discussions"], [
        "visitors cannot post to each other (a sign-in a sealed page cannot keep) - questions reach her"])),
    ("learning", "Learning sections", _sections_for(["lessons", "quiz", "progress"], None if (
        _has("template/src/components/blocks/progress.tsx", "keepGet") and _own_address()) else [
        "a learner's ticks and scores are not kept after the page closes (no learner sign-in on a sealed page)"])),
    ("tool", "Tool / calculator sections", _sections_for(["tool-panel"])),
    ("game", "Game sections", _sections_for(["game-area"])),
    ("ai", "AI inside her site", _ai),
]


def check() -> dict[str, Any]:
    rows = []
    for key, label, fn in CHECKLIST:
        state, missing = fn()
        rows.append({"key": key, "label": label, "state": state, "missing": missing})
    n = {s: sum(1 for r in rows if r["state"] == s) for s in ("works", "partial", "not yet", "blocked")}
    return {"rows": rows, "count": n, "done": n["works"] == len(rows),
            "say": f"{n['works']} of {len(rows)} work, {n['partial']} partly, {n['not yet']} not yet, {n['blocked']} blocked"}


def lines(rep: dict[str, Any] | None = None) -> list[str]:
    rep = rep or check()
    mark = {"works": "[x]", "partial": "[~]", "not yet": "[ ]", "blocked": "[!]"}
    out = [f"React website parity: {rep['say']}"]
    for r in rep["rows"]:
        out.append(f"  {mark[r['state']]} {r['label']}" + (f" - missing: {'; '.join(r['missing'])}" if r["missing"] else ""))
    return out

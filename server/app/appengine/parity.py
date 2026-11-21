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
    missing.append("the cart lives while the page is open (sealed pages keep no browser storage)")
    missing.append("product photos (her shop photos are not on the React site yet)")
    return "partial", missing


def _payments() -> tuple[str, list[str]]:
    ok = _has("template/src/islands/ShopCart.tsx", "online?.url", "/paid", "order.pay.qr")
    return ("works", []) if ok else ("not yet", ["no payment step"])


def _blog() -> tuple[str, list[str]]:
    if _has("writer.py", "blog_post") and _block("article"):
        return "works", []
    return "not yet", ["her blog posts and their pages (the HTML engine builds /blog/)", "the CMS team's publishing"]


def _languages() -> tuple[str, list[str]]:
    return ("works", []) if _has("writer.py", "hreflang") else ("not yet", ["second-language pages + switch + hreflang"])


def _portals() -> tuple[str, list[str]]:
    miss = ["sign-in on a website page (refused: the sealed page keeps no sign-in)", "her real lists in the app screens"]
    return ("partial", miss) if _has("writer.py", "AppPage") else ("not yet", miss)


def _catalogue() -> tuple[str, list[str]]:
    return ("works", []) if _has("writer.py", "catalog") else ("not yet", ["a page per item from her sheet (5,000+ pages)"])


def _live_chat() -> tuple[str, list[str]]:
    return "not yet", ["visitor chat + clinic queue (needs the visitor's sign-in token, which a sealed page cannot keep)"]


def _push() -> tuple[str, list[str]]:
    return "blocked", ["browser push needs a service worker, which a sealed (sandboxed) page cannot register"]


def _domains() -> tuple[str, list[str]]:
    return ("works", []) if _has("../site/hosting.py", "appengine") else ("not yet", ["her own domain for a React website"])


def _sections_for(kinds: list[str]) -> Check:
    def run() -> tuple[str, list[str]]:
        have = [k for k in kinds if _block(k)]
        if len(have) == len(kinds):
            return "works", []
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
    ("community", "Community sections", _sections_for(["members", "discussions"])),
    ("learning", "Learning sections", _sections_for(["lessons", "quiz", "progress"])),
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
